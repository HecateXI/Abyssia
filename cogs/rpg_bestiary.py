from __future__ import annotations

import discord
from discord.ext import commands
from typing import Optional

from core.cards import render_creature_card
from core.rpg import ensure_player
from core.rpg_data import CREATURES, RARITY_BY_NAME, catch_rate_for_rarity, derive_7stats, determine_role, dex_mana_for_rarity


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

        # Normalize search: lowercase, replace underscores and hyphens with spaces
        search_lower = creature_name.lower().replace("_", " ").replace("-", " ")
        creature = None
        for ct in CREATURES:
            # Normalize creature name for comparison
            nm = ct.name.lower().replace("_", " ").replace("-", " ")
            if nm == search_lower or search_lower in nm or nm in search_lower:
                creature = ct
                break

        if not creature:
            raise commands.BadArgument(f"Creature not found: {creature_name}")

        catch_rate = catch_rate_for_rarity(creature.rarity)
        rarity_data = RARITY_BY_NAME.get(creature.rarity)
        mana = dex_mana_for_rarity(creature.rarity)

        s7 = derive_7stats(creature)
        role = determine_role(creature)

        caught_row = await self.bot.db.fetchone(
            "SELECT id, level, xp FROM rpg_creatures WHERE user_id = ? AND name = ? LIMIT 1",
            (ctx.author.id, creature.name),
        )

        file = render_creature_card(
            creature_name=creature.name,
            rarity=creature.rarity,
            hp=s7["hp"], str_stat=s7["str"], pr_stat=s7["pr"],
            wp_stat=s7["wp"], mag_stat=s7["mag"], mr_stat=s7["mr"],
            speed=s7["spd"],
            role=role,
            ability=creature.ability,
            level=int(caught_row["level"]) if caught_row else 1,
            xp=int(caught_row["xp"]) if caught_row else 0,
            caught=caught_row is not None,
            player_name=ctx.author.display_name,
            catch_rate=catch_rate,
            mana=mana,
            weight=rarity_data.weight if rarity_data else None,
        )

        await ctx.reply(file=discord.File(file, "creature.png"), mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Bestiary(bot))
