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


def parse_icon(value: str | None) -> str | None:
    """Parse an icon argument. Accepts emoji or None."""
    if value is None:
        return None
    # Check if it's a valid emoji
    try:
        # Try to parse as emoji
        if value.startswith("<") and value.endswith(">"):
            # Custom emoji format <name:id>
            return value
        # Try to decode as unicode emoji
        value.encode('ascii')  # Will fail for unicode emojis
        return value
    except (UnicodeEncodeError, ValueError):
        return value


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
            try:
                role = member.guild.get_role(int(role_id))
                if role is None:
                    # Role doesn't exist anymore
                    return False
                has_role = role in member.roles
                return has_role
            except (ValueError, TypeError):
                return False
        return has_boosted(member)

    async def _get_role_record(self, guild_id: int, member_id: int):
        return await self.bot.db.fetchone(
            "SELECT role_id, name, color, color2, icon FROM booster_roles WHERE guild_id = ? AND member_id = ?",
            (guild_id, member_id),
        )

    @commands.hybrid_group(name="booster", aliases=["br"], invoke_without_command=True)
    async def booster(self, ctx: commands.Context) -> None:
        """Manage your custom booster role."""
        await ctx.reply(embed=status_embed("Booster Roles", "Commands: `booster create <name> <#hex> [icon]`, `booster name <name>`, `booster color <#hex> [color2]`, `booster icon <emoji>`, `booster delete`, `booster sync`"), mention_author=False)

    @booster.command(name="create")
    async def create(self, ctx: commands.Context, name: str, color: str = "#ff73b7", icon: str | None = None) -> None:
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

        # Parse icon if provided
        role_icon = parse_icon(icon)

        role = await ctx.guild.create_role(
            name=name,
            color=discord_color,
            reason=f"Custom booster role for {ctx.author} ({ctx.author.id})",
        )
        
        # Set icon if provided and supported
        if role_icon and hasattr(role, 'edit'):
            try:
                await role.edit(display_icon=role_icon)
            except Exception:
                pass  # Icon not supported or invalid

        await ctx.author.add_roles(role, reason="Assigned custom booster role")
        await self.bot.db.execute(
            "INSERT INTO booster_roles (guild_id, member_id, role_id, name, color, icon) VALUES (?, ?, ?, ?, ?, ?)",
            (ctx.guild.id, ctx.author.id, role.id, role.name, role.color.value, role_icon),
        )
        await send_ok(ctx, f"created {role.mention}")

    @booster.command(name="name")
    async def name(self, ctx: commands.Context, *, name: str) -> None:
        """Rename your booster role."""
        await self._edit_role(ctx, name=name)

    @booster.command(name="color")
    async def color(self, ctx: commands.Context, color: str, color2: str | None = None) -> None:
        """Change your booster role color."""
        await self._edit_role(ctx, color=parse_hex_color(color), color2=parse_hex_color(color2) if color2 else None)

    @booster.command(name="icon")
    async def icon(self, ctx: commands.Context, emoji: str | None = None) -> None:
        """Set or remove your booster role icon."""
        await self._edit_role(ctx, icon=emoji)

    async def _edit_role(self, ctx: commands.Context, *, name: str | None = None, color: discord.Color | None = None, color2: discord.Color | None = None, icon: str | None = None) -> None:
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

        # Update role properties
        edit_kwargs = {}
        if name is not None:
            edit_kwargs["name"] = name
        if color is not None:
            edit_kwargs["color"] = color
        if icon is not None:
            try:
                edit_kwargs["display_icon"] = icon
            except Exception:
                pass

        if edit_kwargs:
            await role.edit(**edit_kwargs, reason=f"Booster role edit by {ctx.author}")

        # Update database
        new_name = name or role.name
        new_color = color.value if color else role.color.value
        new_color2 = color2.value if color2 else row["color2"]
        new_icon = icon if icon is not None else row["icon"]

        await self.bot.db.execute(
            "UPDATE booster_roles SET name = ?, color = ?, color2 = ?, icon = ? WHERE guild_id = ? AND member_id = ?",
            (new_name, new_color, new_color2, new_icon, ctx.guild.id, ctx.author.id),
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

    @commands.hybrid_command(name="giveboosterrole", aliases=["gbr"])
    async def give_booster_role(self, ctx: commands.Context, member: discord.Member) -> None:
        """Offer your saved custom booster role to a member (requires acceptance)."""
        assert ctx.guild is not None
        row = await self._get_role_record(ctx.guild.id, ctx.author.id)
        if row is None:
            raise commands.BadArgument("You have no saved booster role.")
        role = ctx.guild.get_role(row["role_id"])
        if role is None:
            raise commands.BadArgument("The saved role no longer exists.")

        # Try to send DM acceptance request
        dm_sent = False
        try:
            embed = discord.Embed(
                title="Booster Role Offer",
                description=f"**{ctx.author.mention}** is offering you the booster role **{role.mention}**.\n\nReact with ✅ to accept or ❌ to decline.",
                color=role.color,
            )
            embed.set_footer(text="This request will expire in 5 minutes.")
            
            msg = await member.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            dm_sent = True

            def check(reaction, user):
                return user == member and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=300.0, check=check)
                if str(reaction.emoji) == "✅":
                    await member.add_roles(role, reason=f"Booster role accepted from offer by {ctx.author}")
                    await send_ok(ctx, f"{member.mention} accepted {role.mention}")
                    await msg.edit(embed=discord.Embed(
                        title="Booster Role Accepted",
                        description=f"You accepted the booster role **{role.mention}**!",
                        color=discord.Color.green(),
                    ))
                else:
                    await send_ok(ctx, f"{member.mention} declined the booster role offer.")
                    await msg.edit(embed=discord.Embed(
                        title="Booster Role Declined",
                        description="You declined the booster role offer.",
                        color=discord.Color.red(),
                    ))
            except TimeoutError:
                await send_ok(ctx, f"Offer to {member.mention} expired (no response within 5 minutes).")
                await msg.edit(embed=discord.Embed(
                    title="Booster Role Offer Expired",
                    description="The offer expired due to no response.",
                    color=discord.Color.orange(),
                ))
        except discord.Forbidden:
            dm_sent = False
        
        # If DM failed, assign role directly
        if not dm_sent:
            await member.add_roles(role, reason=f"Booster role assigned by {ctx.author} (DM failed)")
            await send_ok(ctx, f"assigned {role.mention} to {member.mention} (couldn't send DM)")

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
