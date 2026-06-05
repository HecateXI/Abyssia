from __future__ import annotations

import discord
from discord.ext import commands
from typing import Optional

from core.cards import render_creature_card
from core.rpg import ensure_player
from core.rpg_data import CREATURES, catch_rate_for_rarity


class Bestiary(commands.Cog):
    """Bestiary and creature inspection commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="dex")
    async def dex(self, ctx: commands.Context, *, creature_name: str = "") -> None:
        """View a creature's stats and info."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)

        if not creature_name.strip():
            raise commands.BadArgument("Usage: `b dex [creature_name]` — e.g., `b dex Bloodmoon Drake`")

        search_lower = creature_name.lower().replace("_", " ").replace("-", " ")
        creature = None
        for ct in CREATURES:
            nm = ct.name.lower()
            if nm == search_lower or search_lower in nm:
                creature = ct
                break

        if not creature:
            raise commands.BadArgument(f"Creature not found: {creature_name}")

        catch_rate = catch_rate_for_rarity(creature.rarity)

        caught_row = await self.bot.db.fetchone(
            "SELECT id, level, xp FROM rpg_creatures WHERE user_id = ? AND name = ? LIMIT 1",
            (ctx.author.id, creature.name),
        )

        file = render_creature_card(
            creature_name=creature.name,
            rarity=creature.rarity,
            attack=creature.attack,
            defense=creature.defense,
            hp=creature.hp,
            speed=creature.speed,
            ability=creature.ability,
            level=int(caught_row["level"]) if caught_row else 1,
            xp=int(caught_row["xp"]) if caught_row else 0,
            caught=caught_row is not None,
            player_name=ctx.author.display_name,
            catch_rate=catch_rate,
        )

        await ctx.reply(file=discord.File(file, "creature.png"), mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Bestiary(bot))
