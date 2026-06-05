from __future__ import annotations

import random

import discord
from discord.ext import commands

from core.discord_assets import embed_asset
from core.rpg import (
    award_currency,
    choose_creature_template,
    choose_rarity,
    create_creature,
    ensure_player,
    get_zone,
    progress_quest,
    roll_creature_stats,
    unlock_achievement,
)
from core.rpg_data import RARITY_INDEX, ZONES, normalize_key
from core.theme import creature_line, dark_embed, rarity_color


class RPGSummoning(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="summon", aliases=["ritual"])
    async def summon(self, ctx: commands.Context, pulls: int = 1) -> None:
        """Spend gems on summoning rituals for rare monsters."""
        assert ctx.guild is not None
        if pulls not in {1, 5, 10}:
            raise commands.BadArgument("Pulls must be 1, 5, or 10.")
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        cost = pulls * 25
        if int(player["gems"]) < cost:
            raise commands.BadArgument(f"You need {cost} gems.")
        await award_currency(self.bot.db, ctx.author.id, gems=-cost)
        zone = ZONES["void_realm"] if int(player["level"]) >= 30 else get_zone(None, player["current_zone"])
        results: list[dict[str, object]] = []
        for _ in range(pulls):
            boosted_luck = int(player["luck"]) + 12
            rarity = choose_rarity(zone, boosted_luck, 0.18)
            template = choose_creature_template(rarity)
            stats = roll_creature_stats(template, int(player["level"]) + random.randint(0, 3))
            creature_id = await create_creature(self.bot.db, ctx.author.id, stats)
            results.append({"id": creature_id, **stats})
            await progress_quest(self.bot.db, ctx.author.id, "daily_catches")
            await unlock_achievement(self.bot.db, ctx.author.id, "first_blood")
            if rarity not in {"Common", "Uncommon"}:
                await unlock_achievement(self.bot.db, ctx.author.id, "rare_keeper")
        best = max(results, key=lambda item: RARITY_INDEX.get(str(item["rarity"]), 0))
        embed = dark_embed("Summoning Ritual", color=rarity_color(str(best["rarity"])))
        embed.description = "The circle cracks open. Something answers.\n\n" + "\n".join(creature_line(item, show_stats=False) for item in results)
        asset_url, file = embed_asset("creatures", normalize_key(str(best["name"])))
        if asset_url:
            embed.set_thumbnail(url=asset_url)
        await ctx.reply(embed=embed, file=file, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGSummoning(bot))
