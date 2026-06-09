from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
    PTZ = ZoneInfo("America/Los_Angeles")
except (Exception,):
    PTZ = timezone(timedelta(hours=-7))

import discord
from discord.ext import commands

from core.rpg import (
    add_item,
    award_currency,
    ensure_daily_checklist,
    ensure_player,
    now_ts,
    today_key,
)
from core.rpg_data import WEAPON_SHARD_KEY
from core.theme import GOLD_COLOR, crate_label, currency_label, dark_embed, material_label, status_embed

log = logging.getLogger(__name__)

TOPGG_BOT_ID = os.getenv("TOPGG_BOT_ID", "")
TOPGG_TOKEN = os.getenv("TOPGG_TOKEN", "")
TOPGG_WEBHOOK_AUTH = os.getenv("TOPGG_WEBHOOK_AUTH", "")
VOTE_LOG_CHANNEL_ID = (
    int(os.getenv("VOTE_LOG_CHANNEL_ID", "0")) if os.getenv("VOTE_LOG_CHANNEL_ID") else 0
)
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))

VOTE_COOLDOWN_HOURS = 12


def _is_weekend() -> bool:
    return datetime.now(PTZ).weekday() >= 5


def _vote_link() -> str:
    return f"https://top.gg/bot/{TOPGG_BOT_ID}/vote"


async def _check_topgg_api(user_id: int) -> bool:
    if not TOPGG_TOKEN or not TOPGG_BOT_ID:
        return False
    import aiohttp
    url = f"https://top.gg/api/bots/{TOPGG_BOT_ID}/check"
    headers = {"Authorization": TOPGG_TOKEN}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"userId": user_id}, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    log.warning("Top.gg API returned %s for user %s", resp.status, user_id)
                    return False
                data = await resp.json()
                return bool(data.get("voted", 0))
    except Exception:
        log.exception("Top.gg API check failed for user %s", user_id)
        return False


async def _get_vote_status(db, user_id: int) -> dict:
    row = await db.fetchone("SELECT * FROM topgg_votes WHERE user_id = ?", (user_id,))
    if row is None:
        return {"voted": False, "vote_count": 0, "vote_streak": 0, "can_vote": True}
    last_vote = int(row["last_vote_at"])
    elapsed = now_ts() - last_vote
    can_vote = elapsed >= VOTE_COOLDOWN_HOURS * 3600
    return {
        "voted": not can_vote,
        "vote_count": int(row["vote_count"]),
        "vote_streak": int(row["vote_streak"]),
        "can_vote": can_vote,
        "last_vote_at": last_vote,
    }


async def _grant_vote_rewards(db, user_id: int) -> dict[str, int | str | None]:
    row = await db.fetchone("SELECT vote_count FROM topgg_votes WHERE user_id = ?", (user_id,))
    vote_count = int(row["vote_count"]) if row else 1
    souls = 500 + vote_count * 10
    shards = 25
    if _is_weekend():
        souls *= 2
    await award_currency(db, user_id, gold=souls)
    await add_item(db, user_id, "material", WEAPON_SHARD_KEY, shards)
    crate_key = None
    roll = random.random()
    if roll < 0.01:
        crate_key = "treasure"
    elif roll < 0.06:
        crate_key = "relic"
    elif roll < 0.56:
        crate_key = "cache"
    if crate_key:
        await add_item(db, user_id, "crate", crate_key, 1)
    now = now_ts()
    await db.execute(
        "UPDATE topgg_votes SET last_claimed_vote_at = ? WHERE user_id = ?",
        (now, user_id),
    )
    return {"souls": souls, "shards": shards, "crate": crate_key}


async def _record_vote(db, user_id: int) -> dict[str, int | str | None]:
    ts = now_ts()
    existing = await db.fetchone("SELECT last_vote_at FROM topgg_votes WHERE user_id = ?", (user_id,))
    if existing and ts - int(existing["last_vote_at"]) < 3600:
        log.warning("Duplicate vote within 1h for user %s – skipping", user_id)
        return {"souls": 0, "shards": 0, "crate": None}
    await db.execute(
        """INSERT INTO topgg_votes (user_id, last_vote_at, vote_count, vote_streak, last_claimed_vote_at, weekend_bonus_count)
           VALUES (?, ?, 1, 1, 0, 0)
           ON CONFLICT(user_id) DO UPDATE SET
               last_vote_at = ?,
               vote_count = vote_count + 1,
               vote_streak = CASE WHEN ? - last_vote_at < 86400 THEN vote_streak + 1 ELSE 1 END
               """,
        (user_id, ts, ts, ts),
    )
    await _mark_checklist_voted(db, user_id)
    return await _grant_vote_rewards(db, user_id)


async def _mark_checklist_voted(db, user_id: int) -> None:
    await ensure_daily_checklist(db, user_id)
    await db.execute(
        "UPDATE rpg_daily_checklists SET voted = 1, updated_at = ? WHERE user_id = ? AND period_key = ?",
        (now_ts(), user_id, today_key()),
    )


class TopGGVotes(commands.Cog):
    """Top.gg voting and rewards."""

    def __init__(self, b: commands.Bot) -> None:
        self.bot = b
        self._web_runner = None
        self._web_task = None

    async def cog_load(self) -> None:
        if TOPGG_WEBHOOK_AUTH:
            self._web_task = asyncio.create_task(self._run_web_server())
            log.info("Top.gg webhook server scheduled")
        else:
            log.info("TOPGG_WEBHOOK_AUTH not set – webhook server disabled")

    async def cog_unload(self) -> None:
        if self._web_runner:
            try:
                await self._web_runner.cleanup()
            except Exception:
                pass
        if self._web_task:
            self._web_task.cancel()

    async def _run_web_server(self) -> None:
        from aiohttp import web
        app = web.Application()
        app.router.add_post("/webhooks/topgg", self._handle_webhook)
        self._web_runner = web.AppRunner(app)
        await self._web_runner.setup()
        site = web.TCPSite(self._web_runner, WEBHOOK_HOST, WEBHOOK_PORT)
        await site.start()
        log.info("Top.gg webhook listening on %s:%s", WEBHOOK_HOST, WEBHOOK_PORT)

    async def _notify_vote_log(self, user_id: int) -> None:
        if not VOTE_LOG_CHANNEL_ID:
            return
        channel = self.bot.get_channel(VOTE_LOG_CHANNEL_ID)
        if channel:
            try:
                await channel.send(f"<@{user_id}> voted on Top.gg!")
            except Exception:
                pass

    async def _handle_webhook(self, request):
        from aiohttp import web
        auth = request.headers.get("Authorization", "")
        if auth != TOPGG_WEBHOOK_AUTH:
            log.warning("Webhook auth mismatch (got %r)", auth)
            return web.Response(status=401, text="Unauthorized")
        try:
            payload = await request.json()
        except Exception:
            log.exception("Webhook bad payload")
            return web.Response(status=400, text="Bad JSON")
        user_id = int(payload.get("user") or payload.get("user_id", 0))
        if not user_id:
            return web.Response(status=400, text="Missing user")
        log.info("Webhook vote from user %s", user_id)
        await _record_vote(self.bot.db, user_id)
        await self._notify_vote_log(user_id)
        return web.json_response({"ok": True})

    @commands.hybrid_group(name="vote", aliases=["v", "topgg"], invoke_without_command=True)
    async def vote(self, ctx: commands.Context) -> None:
        """View your Top.gg vote status and claim rewards."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        status = await _get_vote_status(self.bot.db, ctx.author.id)
        lines = [
            f"Vote Count: **{status['vote_count']}**",
            f"Streak: **{status['vote_streak']}**",
            f"Status: **{'Voted!' if status['voted'] else 'Can Vote'}**",
        ]
        if _is_weekend():
            lines.append("\n**Weekend Bonus!** Double Souls on your next vote.")
        embed = dark_embed("🗳️ Top.gg Vote", "\n".join(lines), color=GOLD_COLOR)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(
            name="Rewards",
            value=(
                f"{currency_label('gold')} **500** base + **10** per lifetime vote\n"
                f"{material_label(WEAPON_SHARD_KEY)} **25**\n"
                f"Chance at Void Cache (50%), Eldritch Relic (5%), Abyssal Treasure (1%)"
            ),
            inline=False,
        )
        view = discord.ui.View(timeout=60)
        view.add_item(discord.ui.Button(label="Vote on Top.gg", url=_vote_link()))
        await ctx.reply(embed=embed, view=view, mention_author=False)

    @vote.command(name="claim")
    async def vote_claim(self, ctx: commands.Context) -> None:
        """Manually check Top.gg API for a recent vote and claim rewards."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        row = await self.bot.db.fetchone(
            "SELECT last_vote_at, last_claimed_vote_at FROM topgg_votes WHERE user_id = ?",
            (ctx.author.id,),
        )
        if row:
            last_vote = int(row["last_vote_at"])
            last_claimed = int(row["last_claimed_vote_at"])
            if last_vote > last_claimed:
                rewards = await _grant_vote_rewards(self.bot.db, ctx.author.id)
                await self._notify_vote_log(ctx.author.id)
                lines = [
                    f"{currency_label('gold')} **{rewards['souls']}**",
                    f"{material_label(WEAPON_SHARD_KEY)} **{rewards['shards']}**",
                ]
                if rewards.get("crate"):
                    key = str(rewards["crate"])
                    label = crate_label(key, key.replace("_", " ").title())
                    lines.append(f"{label} **1**")
                await ctx.reply(embed=status_embed("Vote Rewards Claimed", "\n".join(lines)), mention_author=False)
                return
        voted = await _check_topgg_api(ctx.author.id)
        if not voted:
            await ctx.reply(
                embed=status_embed("Vote Check", "No recent vote found on Top.gg. Vote first!"),
                mention_author=False,
            )
            return
        rewards = await _record_vote(self.bot.db, ctx.author.id)
        await self._notify_vote_log(ctx.author.id)
        lines = [
            f"{currency_label('gold')} **{rewards['souls']}**",
            f"{material_label(WEAPON_SHARD_KEY)} **{rewards['shards']}**",
        ]
        if rewards.get("crate"):
            key = str(rewards["crate"])
            label = crate_label(key, key.replace("_", " ").title())
            lines.append(f"{label} **1**")
        await ctx.reply(
            embed=status_embed("Vote Rewards Claimed", "\n".join(lines)),
            mention_author=False,
        )


    @commands.command(name="debugvote", aliases=["dv"], hidden=True)
    @commands.is_owner()
    async def debug_vote(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        """[Bot Owner] Show vote debug info for a user."""
        target = member or ctx.author
        status = await _get_vote_status(self.bot.db, target.id)
        pieces = [f"**{target}** (`{target.id}`)"]
        for k, v in status.items():
            pieces.append(f"`{k}` = `{v}`")
        embed = dark_embed("Vote Debug", "\n".join(pieces), color=GOLD_COLOR)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(b: commands.Bot) -> None:
    await b.add_cog(TopGGVotes(b))
