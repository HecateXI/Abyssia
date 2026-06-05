import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args, **kwargs):
        return False

from core.database import BotDatabase
from core.discord_assets import ensure_application_emojis, refresh_application_emojis
from core.rpg import ensure_weapon_passives


COGS = (
    "cogs.admin",
    "cogs.boosters",
    "cogs.moderation",
    "cogs.rpg_help",
    "cogs.rpg_profile",
    "cogs.rpg_bestiary",
    "cogs.rpg_hunting",
    "cogs.rpg_summoning",
    "cogs.rpg_battle",
    "cogs.rpg_economy",
    "cogs.rpg_equipment",
    "cogs.rpg_shop",
    "cogs.rpg_trade",
    "cogs.rpg_buffs",
    "cogs.utility",
)

BOT_UPDATES_CHANNEL_ID = int(os.getenv("BOT_UPDATES_CHANNEL_ID", "1511768079950938112"))
BOT_STATUS_CHANNEL_ID = int(os.getenv("BOT_STATUS_CHANNEL_ID", "1511768495405269072"))
PENDING_UPDATE_LOG = Path(os.getenv("BOT_PENDING_UPDATE_LOG", "data/pending_update.md"))


class AbyssiaBot(commands.Bot):
    def __init__(self) -> None:
        load_dotenv(Path(__file__).with_name(".env"))
        self.db = BotDatabase(os.getenv("BOT_DB_PATH", "data/bot.sqlite3"))
        self._ready_notice_sent = False
        self._offline_notice_sent = False

        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        intents.moderation = True

        super().__init__(
            command_prefix=self._prefix_for,
            intents=intents,
            help_command=None,
            strip_after_prefix=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def _prefix_for(self, bot: commands.Bot, message: discord.Message):
        if message.guild is None:
            base_prefix = os.getenv("BOT_PREFIX", "b") or "b"
            prefixes = [base_prefix]
            if base_prefix.lower() == "b":
                prefixes.extend(["b", "B"])
            return prefixes
        prefix = await self.db.get_setting(message.guild.id, "prefix")
        base_prefix = prefix or os.getenv("BOT_PREFIX", "b") or "b"
        prefixes = [base_prefix]
        if base_prefix.lower() == "b":
            prefixes.extend(["b", "B"])
        return commands.when_mentioned_or(*dict.fromkeys(prefixes))(bot, message)

    async def setup_hook(self) -> None:
        await self.db.connect()
        await ensure_weapon_passives(self.db)
        for cog in COGS:
            await self.load_extension(cog)
        self.before_invoke(self._claim_command_invocation)
        synced = await self.tree.sync()
        logging.info("Synced %d app commands", len(synced))

    async def _claim_command_invocation(self, ctx: commands.Context) -> None:
        if ctx.guild is not None:
            try:
                await ensure_application_emojis(self, max_age=60.0)
            except discord.HTTPException:
                logging.exception("Could not refresh application emoji cache before command")
        command_name = ctx.command.qualified_name if ctx.command else "unknown"
        if ctx.interaction is not None:
            dedupe_key = f"interaction:{ctx.interaction.id}"
        elif ctx.message is not None:
            dedupe_key = f"message:{ctx.message.id}:{command_name}"
        else:
            dedupe_key = f"fallback:{ctx.author.id}:{command_name}:{datetime.now(timezone.utc).timestamp()}"
        claimed = await self.db.claim_command_invocation(
            dedupe_key,
            ctx.author.id,
            command_name,
            int(datetime.now(timezone.utc).timestamp()),
        )
        if not claimed:
            raise commands.CheckFailure("duplicate-invocation")

    async def process_commands(self, message: discord.Message) -> None:
        if message.guild is not None and not message.author.bot:
            try:
                await ensure_application_emojis(self, max_age=60.0)
            except discord.HTTPException:
                logging.exception("Could not refresh application emoji cache before command")
        await super().process_commands(message)

    async def close(self) -> None:
        await self._post_status("Offline", discord.Color.dark_red())
        self._offline_notice_sent = True
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        assert self.user is not None
        logging.info("Logged in as %s (%s)", self.user, self.user.id)
        import core.theme
        core.theme.BOT = self
        try:
            await refresh_application_emojis(self)
        except discord.HTTPException:
            logging.exception("Could not refresh application emoji cache")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Abyssia hunts"))
        if not self._ready_notice_sent:
            self._ready_notice_sent = True
            await self._post_status("Online", discord.Color.green())
            await self._post_pending_update_log()

    async def _send_channel_embed(self, channel_id: int, embed: discord.Embed) -> bool:
        channel = self.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(channel_id)
            except discord.HTTPException:
                logging.exception("Could not fetch notification channel %s", channel_id)
                return False
        if not hasattr(channel, "send"):
            logging.warning("Notification target %s is not a sendable channel", channel_id)
            return False
        try:
            await channel.send(embed=embed)
            return True
        except discord.HTTPException:
            logging.exception("Could not send notification to channel %s", channel_id)
            return False

    async def _post_status(self, state: str, color: discord.Color) -> None:
        if state == "Offline" and self._offline_notice_sent:
            return
        embed = discord.Embed(
            title="Abyssia Bot Status",
            description=f"Status: **{state}**",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        if self.user is not None:
            embed.set_author(name=str(self.user), icon_url=self.user.display_avatar.url)
        embed.add_field(name="Environment", value="Production", inline=True)
        embed.add_field(name="Latency", value=f"{round(self.latency * 1000)}ms" if self.latency else "Starting", inline=True)
        embed.set_footer(text="Automated status notification")
        await self._send_channel_embed(BOT_STATUS_CHANNEL_ID, embed)

    async def _post_pending_update_log(self) -> None:
        if not PENDING_UPDATE_LOG.exists():
            return
        content = PENDING_UPDATE_LOG.read_text(encoding="utf-8").strip()
        if not content:
            PENDING_UPDATE_LOG.unlink(missing_ok=True)
            return
        lines = content.splitlines()
        title = lines[0].lstrip("# ").strip() or "Bot Update"
        body = "\n".join(lines[1:]).strip()
        if len(body) > 3800:
            body = body[:3797].rstrip() + "..."
        embed = discord.Embed(
            title=title,
            description=body,
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Abyssia update log")
        if await self._send_channel_embed(BOT_UPDATES_CHANNEL_ID, embed):
            PENDING_UPDATE_LOG.unlink(missing_ok=True)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    Path("data").mkdir(exist_ok=True)

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        env_path = Path(__file__).with_name(".env")
        load_dotenv(env_path)
        token = os.getenv("DISCORD_TOKEN")
    if not token:
        env_path = Path(__file__).with_name(".env")
        raise RuntimeError(f"DISCORD_TOKEN is missing. Create {env_path} from .env.example and add your token.")

    bot = AbyssiaBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
