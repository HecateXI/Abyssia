import discord
from discord.ext import commands

from core.checks import is_staff, send_ok
from core.discord_assets import APP_EMOJI_CACHE, asset_emoji_targets, refresh_application_emojis, upload_application_asset_emojis
from core.theme import dark_embed, status_embed


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_group(name="config", invoke_without_command=True)
    @is_staff()
    async def config(self, ctx: commands.Context) -> None:
        """Show configurable server settings."""
        assert ctx.guild is not None
        rows = await self.bot.db.fetchall("SELECT key, value FROM guild_settings WHERE guild_id = ? ORDER BY key", (ctx.guild.id,))
        if not rows:
            await ctx.reply(embed=status_embed("Server Settings", "No settings configured yet."), mention_author=False)
            return
        body = "\n".join(f"`{row['key']}` = `{row['value']}`" for row in rows)
        await ctx.reply(embed=dark_embed("Server Settings", body), mention_author=False)

    @config.command(name="prefix")
    @commands.has_guild_permissions(manage_guild=True)
    async def prefix(self, ctx: commands.Context, prefix: str) -> None:
        """Set the text command prefix."""
        assert ctx.guild is not None
        if len(prefix) > 5:
            raise commands.BadArgument("Prefix must be 5 characters or fewer.")
        await self.bot.db.set_setting(ctx.guild.id, "prefix", prefix)
        await send_ok(ctx, f"prefix set to `{prefix}`")

    @config.command(name="modlog")
    @commands.has_guild_permissions(manage_guild=True)
    async def modlog(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        """Set or clear the moderation log channel."""
        assert ctx.guild is not None
        await self.bot.db.set_setting(ctx.guild.id, "modlog_channel_id", None if channel is None else str(channel.id))
        await send_ok(ctx, "mod log disabled" if channel is None else f"mod log set to {channel.mention}")

    @config.command(name="welcome")
    @commands.has_guild_permissions(manage_guild=True)
    async def welcome(self, ctx: commands.Context, channel: discord.TextChannel | None = None) -> None:
        """Set or clear the welcome channel."""
        assert ctx.guild is not None
        await self.bot.db.set_setting(ctx.guild.id, "welcome_channel_id", None if channel is None else str(channel.id))
        await send_ok(ctx, "welcome messages disabled" if channel is None else f"welcome channel set to {channel.mention}")

    @config.command(name="booster-base")
    @commands.has_guild_permissions(manage_guild=True)
    async def booster_base(self, ctx: commands.Context, role: discord.Role | None = None) -> None:
        """Set the role that marks users allowed to own custom booster roles."""
        assert ctx.guild is not None
        await self.bot.db.set_setting(ctx.guild.id, "booster_base_role_id", None if role is None else str(role.id))
        await send_ok(ctx, "booster base role cleared; Discord boost status will be used" if role is None else f"booster base role set to {role.mention}")

    @config.command(name="setup-emojis")
    @is_staff()
    async def setup_emojis(self, ctx: commands.Context, replace_existing: bool = False) -> None:
        """Upload generated PNG assets as application emojis."""
        assert ctx.guild is not None
        await ctx.defer()

        result = await upload_application_asset_emojis(self.bot, replace_existing=replace_existing)
        uploaded = int(result["uploaded"])
        existing = int(result["existing"])
        replaced = int(result["replaced"])
        failed = list(result["failed"])

        embed = dark_embed("Application Emoji Setup Complete")
        embed.add_field(name="Uploaded", value=f"**{uploaded}** app emojis", inline=True)
        embed.add_field(name="Existing", value=f"**{existing}** already configured", inline=True)
        embed.add_field(name="Replaced", value=f"**{replaced}** refreshed", inline=True)
        creature_count = next((len(keys) for kind, keys in asset_emoji_targets() if kind == "creatures"), 0)
        embed.add_field(name="Creature Bank", value=f"**{creature_count}** creature emojis included", inline=True)
        if failed:
            embed.add_field(name="Failed or Skipped", value="\n".join(failed[:15]), inline=False)
        else:
            embed.add_field(name="Ready", value="All configured PNG assets are active as application emojis.", inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @config.command(name="reload-emojis")
    @is_staff()
    async def reload_emojis(self, ctx: commands.Context) -> None:
        """Refresh the bot's in-memory application emoji cache."""
        assert ctx.guild is not None
        await ctx.defer()
        cache = await refresh_application_emojis(self.bot)
        channel = ctx.channel
        permission_text = "Unknown"
        if isinstance(channel, discord.abc.GuildChannel) and ctx.guild.me is not None:
            permissions = channel.permissions_for(ctx.guild.me)
            permission_text = "Allowed" if permissions.use_external_emojis else "Blocked"

        sample = cache.get("ui_battle") or cache.get("rarity_legendary") or ""
        embed = dark_embed("Application Emoji Cache Reloaded")
        embed.add_field(name="Cached Emojis", value=f"**{len(APP_EMOJI_CACHE)}** app emojis", inline=True)
        embed.add_field(name="External Emoji Permission", value=permission_text, inline=True)
        if sample:
            embed.add_field(name="Render Test", value=f"{sample} If this still shows as text, grant the bot role **Use External Emojis** in this channel.", inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        channel_id = await self.bot.db.get_setting(member.guild.id, "welcome_channel_id")
        if not channel_id:
            return
        channel = member.guild.get_channel(int(channel_id))
        if isinstance(channel, discord.TextChannel):
            await channel.send(f"Welcome {member.mention}.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
