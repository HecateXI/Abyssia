from datetime import timedelta

import discord
from discord.ext import commands

from core.checks import send_ok
from core.theme import status_embed


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _case(self, guild: discord.Guild, actor: discord.abc.User, target: discord.abc.User, action: str, reason: str | None) -> None:
        await self.bot.db.execute(
            "INSERT INTO mod_cases (guild_id, actor_id, target_id, action, reason) VALUES (?, ?, ?, ?, ?)",
            (guild.id, actor.id, target.id, action, reason),
        )
        channel_id = await self.bot.db.get_setting(guild.id, "modlog_channel_id")
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"`{action}` {target.mention} by {actor.mention}: {reason or 'No reason provided'}")

    @commands.hybrid_command()
    @commands.has_guild_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str | None = None) -> None:
        """Kick a member."""
        assert ctx.guild is not None
        await member.kick(reason=reason)
        await self._case(ctx.guild, ctx.author, member, "kick", reason)
        await send_ok(ctx, f"kicked {member}")

    @commands.hybrid_command()
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str | None = None) -> None:
        """Ban a member."""
        assert ctx.guild is not None
        await member.ban(reason=reason, delete_message_days=0)
        await self._case(ctx.guild, ctx.author, member, "ban", reason)
        await send_ok(ctx, f"banned {member}")

    @commands.hybrid_command()
    @commands.has_guild_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str | None = None) -> None:
        """Unban a user by id."""
        assert ctx.guild is not None
        user = discord.Object(id=user_id)
        await ctx.guild.unban(user, reason=reason)
        await self._case(ctx.guild, ctx.author, user, "unban", reason)
        await send_ok(ctx, f"unbanned `{user_id}`")

    @commands.hybrid_command(aliases=["mute"])
    @commands.has_guild_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str | None = None) -> None:
        """Timeout a member."""
        assert ctx.guild is not None
        if minutes < 1 or minutes > 40320:
            raise commands.BadArgument("Minutes must be between 1 and 40320.")
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await self._case(ctx.guild, ctx.author, member, "timeout", reason)
        await send_ok(ctx, f"timed out {member} for {minutes} minute(s)")

    @commands.hybrid_command(aliases=["unmute"])
    @commands.has_guild_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, member: discord.Member, *, reason: str | None = None) -> None:
        """Remove a member timeout."""
        assert ctx.guild is not None
        await member.timeout(None, reason=reason)
        await self._case(ctx.guild, ctx.author, member, "untimeout", reason)
        await send_ok(ctx, f"removed timeout from {member}")

    @commands.hybrid_command()
    @commands.has_guild_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int) -> None:
        """Bulk delete recent messages."""
        if amount < 1 or amount > 100:
            raise commands.BadArgument("Amount must be between 1 and 100.")
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(embed=status_embed("Done", f"Deleted **{max(len(deleted) - 1, 0)}** message(s)."), delete_after=5)

    @commands.hybrid_command()
    @commands.has_guild_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int) -> None:
        """Set channel slowmode."""
        if not isinstance(ctx.channel, discord.TextChannel):
            raise commands.BadArgument("Use this in a text channel.")
        if seconds < 0 or seconds > 21600:
            raise commands.BadArgument("Seconds must be between 0 and 21600.")
        await ctx.channel.edit(slowmode_delay=seconds)
        await send_ok(ctx, f"slowmode set to {seconds}s")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
