import re

import discord
from discord.ext import commands

from core.checks import has_boosted, is_staff, send_ok
from core.theme import status_embed


HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")
PATREON_TIER_ROLE_KEYS = (
    "patreon_tier_1_role_id",
    "patreon_tier_2_role_id",
    "patreon_tier_3_role_id",
    "patreon_tier_4_role_id",
)


def parse_hex_color(value: str) -> discord.Color:
    if not HEX_RE.match(value):
        raise commands.BadArgument("Use a hex color like `#ff66aa`.")
    return discord.Color(int(value.removeprefix("#"), 16))


class Boosters(commands.Cog):
    """Custom role management for boosters."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _eligible(self, member: discord.Member) -> bool:
        manual = await self.bot.db.fetchone(
            "SELECT tier FROM patreon_members WHERE guild_id = ? AND member_id = ? AND tier > 0",
            (member.guild.id, member.id),
        )
        if manual is not None:
            return True
        for key in PATREON_TIER_ROLE_KEYS:
            role_id = await self.bot.db.get_setting(member.guild.id, key)
            if not role_id:
                continue
            role = member.guild.get_role(int(role_id))
            if role and role in member.roles:
                return True
        role_id = await self.bot.db.get_setting(member.guild.id, "booster_base_role_id")
        if role_id:
            role = member.guild.get_role(int(role_id))
            return role in member.roles if role else False
        return has_boosted(member)

    async def _get_role_record(self, guild_id: int, member_id: int):
        return await self.bot.db.fetchone(
            "SELECT role_id, name, color FROM booster_roles WHERE guild_id = ? AND member_id = ?",
            (guild_id, member_id),
        )

    @commands.hybrid_group(name="booster", aliases=["br"], invoke_without_command=True)
    async def booster(self, ctx: commands.Context) -> None:
        """Manage your custom booster role."""
        await ctx.reply(embed=status_embed("Booster Roles", "Commands: `booster create <name> <#hex>`, `booster name <name>`, `booster color <#hex>`, `booster delete`, `booster sync`"), mention_author=False)

    @booster.command(name="create")
    async def create(self, ctx: commands.Context, name: str, color: str = "#ff73b7") -> None:
        """Create your personal booster role."""
        assert ctx.guild is not None and isinstance(ctx.author, discord.Member)
        if not await self._eligible(ctx.author):
            raise commands.BadArgument("You must be boosting or have the configured booster base role.")
        if await self._get_role_record(ctx.guild.id, ctx.author.id):
            raise commands.BadArgument("You already have a booster role. Use `booster name` or `booster color`.")

        discord_color = parse_hex_color(color)
        bot_member = ctx.guild.me
        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            raise commands.BadArgument("I need Manage Roles permission.")

        role = await ctx.guild.create_role(
            name=name,
            color=discord_color,
            reason=f"Custom booster role for {ctx.author} ({ctx.author.id})",
        )
        await ctx.author.add_roles(role, reason="Assigned custom booster role")
        await self.bot.db.execute(
            "INSERT INTO booster_roles (guild_id, member_id, role_id, name, color) VALUES (?, ?, ?, ?, ?)",
            (ctx.guild.id, ctx.author.id, role.id, role.name, role.color.value),
        )
        await send_ok(ctx, f"created {role.mention}")

    @booster.command(name="name")
    async def name(self, ctx: commands.Context, *, name: str) -> None:
        """Rename your booster role."""
        await self._edit_role(ctx, name=name)

    @booster.command(name="color")
    async def color(self, ctx: commands.Context, color: str) -> None:
        """Change your booster role color."""
        await self._edit_role(ctx, color=parse_hex_color(color))

    async def _edit_role(self, ctx: commands.Context, *, name: str | None = None, color: discord.Color | None = None) -> None:
        assert ctx.guild is not None and isinstance(ctx.author, discord.Member)
        row = await self._get_role_record(ctx.guild.id, ctx.author.id)
        if row is None:
            raise commands.BadArgument("You do not have a booster role yet.")
        role = ctx.guild.get_role(row["role_id"])
        if role is None:
            await self.bot.db.execute("DELETE FROM booster_roles WHERE guild_id = ? AND member_id = ?", (ctx.guild.id, ctx.author.id))
            raise commands.BadArgument("Your saved role no longer exists. Create it again.")
        if not await self._eligible(ctx.author):
            raise commands.BadArgument("You are no longer eligible to edit a booster role.")

        await role.edit(name=name or role.name, color=color or role.color, reason=f"Booster role edit by {ctx.author}")
        await self.bot.db.execute(
            "UPDATE booster_roles SET name = ?, color = ? WHERE guild_id = ? AND member_id = ?",
            (role.name, role.color.value, ctx.guild.id, ctx.author.id),
        )
        await send_ok(ctx, f"updated {role.mention}")

    @booster.command(name="delete")
    async def delete(self, ctx: commands.Context) -> None:
        """Delete your custom booster role."""
        assert ctx.guild is not None and isinstance(ctx.author, discord.Member)
        await self._delete_member_role(ctx.guild, ctx.author.id, "Booster role deleted by owner")
        await send_ok(ctx, "deleted your booster role")

    @booster.command(name="sync")
    @is_staff()
    async def sync(self, ctx: commands.Context) -> None:
        """Remove custom roles from members who are no longer eligible."""
        assert ctx.guild is not None
        removed = await self._sync_guild(ctx.guild)
        await send_ok(ctx, f"removed {removed} ineligible booster role(s)")

    @commands.hybrid_command(name="giveboosterrole")
    @is_staff()
    async def give_booster_role(self, ctx: commands.Context, member: discord.Member) -> None:
        """Reassign a saved custom booster role to its owner."""
        assert ctx.guild is not None
        row = await self._get_role_record(ctx.guild.id, member.id)
        if row is None:
            raise commands.BadArgument("That member has no saved booster role.")
        role = ctx.guild.get_role(row["role_id"])
        if role is None:
            raise commands.BadArgument("The saved role no longer exists.")
        await member.add_roles(role, reason=f"Booster role reassigned by {ctx.author}")
        await send_ok(ctx, f"assigned {role.mention} to {member.mention}")

    async def _delete_member_role(self, guild: discord.Guild, member_id: int, reason: str) -> bool:
        row = await self._get_role_record(guild.id, member_id)
        if row is None:
            return False
        role = guild.get_role(row["role_id"])
        if role is not None:
            await role.delete(reason=reason)
        await self.bot.db.execute("DELETE FROM booster_roles WHERE guild_id = ? AND member_id = ?", (guild.id, member_id))
        return True

    async def _sync_guild(self, guild: discord.Guild) -> int:
        rows = await self.bot.db.fetchall("SELECT member_id FROM booster_roles WHERE guild_id = ?", (guild.id,))
        removed = 0
        for row in rows:
            member = guild.get_member(row["member_id"])
            if member is None or not await self._eligible(member):
                if await self._delete_member_role(guild, row["member_id"], "Booster role cleanup"):
                    removed += 1
        return removed

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.premium_since == after.premium_since:
            return
        if before.premium_since is not None and after.premium_since is None and not await self._eligible(after):
            await self._delete_member_role(after.guild, after.id, "Member stopped boosting")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await self._delete_member_role(member.guild, member.id, "Member left server")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Boosters(bot))
