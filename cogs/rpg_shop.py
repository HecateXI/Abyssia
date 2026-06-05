from typing import Any

import discord
from discord.ext import commands

from core.cards import render_crate_open_card, render_shop_card
from core.rpg import (
    add_item,
    award_currency,
    ensure_player,
    get_quantity,
    open_crate,
    row_get,
    weapon_display_name,
    weapon_salvage_shards,
)
from core.rpg_data import CRATE_TYPES, RARITY_INDEX, WEAPON_SHARD_KEY, normalize_key, normalize_rarity
from core.theme import crate_emoji, crate_label, creature_label, material_label, rarity_label


SHARD_CRATE_COSTS: dict[str, int] = {
    "cache": 35,
    "relic": 180,
    "treasure": 700,
}


def _embed(title: str, desc: str, color=discord.Color.dark_purple()) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=color)


def _int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _crate_key(value: str) -> str | None:
    key = normalize_key(value)
    if key in CRATE_TYPES:
        return key
    for crate_key, crate in CRATE_TYPES.items():
        if key == normalize_key(str(crate.get("name", ""))):
            return crate_key
    return None


def shard_crate_deals() -> list[dict[str, object]]:
    deals: list[dict[str, object]] = []
    for slot, (key, cost) in enumerate(SHARD_CRATE_COSTS.items()):
        crate = CRATE_TYPES[key]
        rarities = ", ".join(str(r) for r in crate.get("weapon_rarities", ()))
        deals.append(
            {
                "slot": slot,
                "item_key": key,
                "item_name": str(crate["name"]),
                "desc": str(crate.get("desc", "")),
                "rarities": rarities,
                "shard_cost": cost,
                "bundle_size": 1,
                "deal_type": "crate",
                "purchased": 0,
            }
        )
    return deals


async def _buy_and_open_shard_crate(bot: commands.Bot, user: Any, display_name: str, crate_key: str) -> tuple[dict[str, object], int]:
    key = _crate_key(crate_key)
    if key is None or key not in SHARD_CRATE_COSTS:
        valid = ", ".join(SHARD_CRATE_COSTS.keys())
        raise ValueError(f"Unknown shard crate. Use one of: {valid}.")
    await ensure_player(bot.db, user.id, display_name)
    cost = SHARD_CRATE_COSTS[key]
    owned = await get_quantity(bot.db, user.id, "material", WEAPON_SHARD_KEY)
    if owned < cost:
        raise ValueError(f"Need {material_label(WEAPON_SHARD_KEY)} **{cost}**. You have **{owned}**.")
    await add_item(bot.db, user.id, "material", WEAPON_SHARD_KEY, -cost)
    return await open_crate(bot.db, user.id, key), cost


class CrateOpenView(discord.ui.View):
    def __init__(self, ctx: commands.Context) -> None:
        super().__init__(timeout=60)
        self.ctx = ctx

    @discord.ui.select(
        placeholder="Select an owned weapon crate...",
        options=[
            discord.SelectOption(
                label=str(crate["name"]),
                value=ck,
                description=str(crate["desc"])[:50],
            )
            for ck, crate in CRATE_TYPES.items()
        ],
    )
    async def crate_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        crate_key = select.values[0]
        ctx = self.ctx
        db = ctx.bot.db
        crate = CRATE_TYPES[crate_key]
        await ensure_player(db, ctx.author.id, ctx.author.display_name)
        owned = await get_quantity(db, ctx.author.id, "crate", crate_key)
        if owned < 1:
            cost = SHARD_CRATE_COSTS.get(crate_key, 0)
            await interaction.followup.send(
                f"You do not own {crate_label(crate_key, str(crate['name']))}. Use `{ctx.prefix}shardcrate {crate_key}` to buy and open one for {material_label(WEAPON_SHARD_KEY)} **{cost}**.",
                ephemeral=True,
            )
            return

        await add_item(db, ctx.author.id, "crate", crate_key, -1)
        result = await open_crate(db, ctx.author.id, crate_key)
        image = render_crate_open_card(ctx.author.display_name, crate["name"], result, weapons=result.get("weapons"))
        file = discord.File(image, filename="abyssia_crate.png")
        embed = discord.Embed(color=discord.Color.orange())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url="attachment://abyssia_crate.png")
        self.crate_select.disabled = True
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id


class ShardCrateShopView(discord.ui.View):
    def __init__(self, ctx: commands.Context, deals: list[dict[str, object]]) -> None:
        super().__init__(timeout=90)
        self.ctx = ctx
        self.deals = deals

    @discord.ui.select(placeholder="Buy and open with Weapon Shards...", options=[])
    async def buy_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        crate_key = select.values[0]
        try:
            result, cost = await _buy_and_open_shard_crate(self.ctx.bot, interaction.user, interaction.user.display_name, crate_key)
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        crate = CRATE_TYPES[crate_key]
        image = render_crate_open_card(interaction.user.display_name, crate["name"], result, weapons=result.get("weapons"))
        file = discord.File(image, filename="abyssia_crate.png")
        embed = discord.Embed(color=discord.Color.orange())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_image(url="attachment://abyssia_crate.png")
        embed.set_footer(text=f"Bought with {cost} Weapon Shards")
        await interaction.edit_original_response(embed=embed, attachments=[file], view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id

    def add_options(self) -> None:
        self.buy_select.options = [
            discord.SelectOption(
                label=str(deal["item_name"]),
                value=str(deal["item_key"]),
                description=f"{deal['shard_cost']} Weapon Shards",
                emoji=discord.PartialEmoji.from_str(crate_emoji(str(deal["item_key"]))) if crate_emoji(str(deal["item_key"])) else None,
            )
            for deal in self.deals
        ]


class RPGShop(commands.Cog):
    """Weapon crate and sell commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="crateshop", aliases=["crates", "store"])
    async def crateshop(self, ctx: commands.Context) -> None:
        """Browse shard-priced weapon crates."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        deals = shard_crate_deals()
        image = render_shop_card(ctx.author.display_name, deals, page=1, total_pages=1)
        file = discord.File(image, filename="abyssia_shop.png")
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url="attachment://abyssia_shop.png")
        view = ShardCrateShopView(ctx, deals)
        view.add_options()
        await ctx.reply(embed=embed, file=file, view=view, mention_author=False)

    @commands.hybrid_command(name="open", aliases=["unbox", "wc"])
    async def open_crate_cmd(self, ctx: commands.Context, crate_key: str | None = None) -> None:
        """Open an owned weapon crate."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        if crate_key is None:
            view = CrateOpenView(ctx)
            embed = _embed("Open Crate", f"Choose an owned crate, or use `b shardcrate <crate>` to buy one with {material_label(WEAPON_SHARD_KEY)}.", discord.Color.orange())
            await ctx.reply(embed=embed, view=view, mention_author=False)
            return

        key = _crate_key(crate_key)
        if key is None:
            await ctx.reply(embed=_embed("Open", f"Unknown crate. Use `{ctx.prefix}crateshop`."), mention_author=False, ephemeral=True)
            return
        crate = CRATE_TYPES[key]
        owned = await get_quantity(self.bot.db, ctx.author.id, "crate", key)
        if owned < 1:
            cost = SHARD_CRATE_COSTS.get(key, 0)
            await ctx.reply(
                embed=_embed("Open", f"You do not own {crate_label(key, str(crate['name']))}. Use `{ctx.prefix}shardcrate {key}` to buy and open one for {material_label(WEAPON_SHARD_KEY)} **{cost}**."),
                mention_author=False,
            )
            return

        await add_item(self.bot.db, ctx.author.id, "crate", key, -1)
        result = await open_crate(self.bot.db, ctx.author.id, key)
        image = render_crate_open_card(ctx.author.display_name, crate["name"], result, weapons=result.get("weapons"))
        file = discord.File(image, filename="abyssia_crate.png")
        embed = discord.Embed(color=discord.Color.orange())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url="attachment://abyssia_crate.png")
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.hybrid_command(name="shardcrate", aliases=["buywc", "wcbuy"])
    async def shard_crate(self, ctx: commands.Context, crate_key: str = "cache") -> None:
        """Buy and open a weapon crate with Weapon Shards."""
        assert ctx.guild is not None
        try:
            result, cost = await _buy_and_open_shard_crate(self.bot, ctx.author, ctx.author.display_name, crate_key)
        except ValueError as exc:
            await ctx.reply(embed=_embed("Shard Crate", str(exc)), mention_author=False, ephemeral=True)
            return
        key = _crate_key(crate_key) or "cache"
        crate = CRATE_TYPES[key]
        image = render_crate_open_card(ctx.author.display_name, crate["name"], result, weapons=result.get("weapons"))
        file = discord.File(image, filename="abyssia_crate.png")
        embed = discord.Embed(color=discord.Color.orange())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url="attachment://abyssia_crate.png")
        embed.set_footer(text=f"Bought with {cost} Weapon Shards")
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.hybrid_command(name="sellall", aliases=["massrelease"])
    async def sellall(self, ctx: commands.Context, rarity: str | None = None) -> None:
        """Sell all creatures of a rarity, or keep top 3 of each rarity."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)

        rarity_clean = normalize_rarity(rarity) if rarity else None
        if rarity and rarity_clean is None:
            valid = ", ".join(RARITY_INDEX.keys())
            return await ctx.reply(embed=_embed("Sell All", f"Unknown rarity `{rarity}`.\nValid rarities: {valid}."), mention_author=False)

        if rarity_clean:
            creatures = await self.bot.db.fetchall(
                "SELECT * FROM rpg_creatures WHERE user_id = ? AND rarity = ? ORDER BY level DESC",
                (ctx.author.id, rarity_clean),
            )
        else:
            creatures = await self.bot.db.fetchall(
                "SELECT * FROM rpg_creatures WHERE user_id = ? ORDER BY rarity, level DESC",
                (ctx.author.id,),
            )
        if not creatures:
            return await ctx.reply(embed=_embed("Sell All", "No creatures to sell."), mention_author=False)

        equipped_ids = {
            int(row["equipped_creature_id"])
            for row in await self.bot.db.fetchall(
                "SELECT equipped_creature_id FROM weapons WHERE equipped_creature_id IS NOT NULL AND user_id = ?",
                (ctx.author.id,),
            )
        }
        team_ids = {
            int(row["creature_id"])
            for row in await self.bot.db.fetchall(
                "SELECT creature_id FROM rpg_teams WHERE user_id = ?",
                (ctx.author.id,),
            )
        }

        keep_remaining: dict[str, int] = {}
        if not rarity_clean:
            counts: dict[str, int] = {}
            for cr in creatures:
                r = str(cr["rarity"])
                counts[r] = counts.get(r, 0) + 1
            keep_remaining = {r: 3 for r in counts}

        total_value = 0
        sold_count = 0
        for cr in creatures:
            r = str(cr["rarity"])
            cid = int(cr["id"])
            if cid in equipped_ids or cid in team_ids:
                continue
            if keep_remaining.get(r, 0) > 0:
                keep_remaining[r] -= 1
                continue
            total_value += _int(cr["value"])
            sold_count += 1
            await self.bot.db.execute("DELETE FROM rpg_creatures WHERE id = ?", (cid,))

        if sold_count == 0:
            return await ctx.reply(embed=_embed("Sell All", "No creatures eligible to sell."), mention_author=False)
        await award_currency(self.bot.db, ctx.author.id, gold=total_value)
        scope = f" {rarity_label(rarity_clean)}" if rarity_clean else ""
        return await ctx.reply(embed=_embed("Sell All", f"Sold **{sold_count}**{scope} creature(s) for **{total_value:,}** souls."), mention_author=False)

    @commands.hybrid_command(name="release", aliases=["sellcreature"])
    async def release(self, ctx: commands.Context, *, creature_name: str) -> None:
        """Sell/release a creature for souls."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        creatures = await self.bot.db.fetchall(
            "SELECT * FROM rpg_creatures WHERE user_id = ? AND LOWER(name) LIKE ? ORDER BY value DESC, level DESC",
            (ctx.author.id, f"%{creature_name.lower()}%"),
        )
        if not creatures:
            return await ctx.reply(embed=_embed("Release", f"No creature: `{creature_name}`."), mention_author=False, ephemeral=True)
        cr = creatures[0]
        weapon = await self.bot.db.fetchone("SELECT id FROM weapons WHERE equipped_creature_id = ?", (cr["id"],))
        if weapon:
            return await ctx.reply(embed=_embed("Release", "Unequip weapons from this creature first."), mention_author=False)
        value = _int(cr["value"])
        await self.bot.db.execute("DELETE FROM rpg_creatures WHERE id = ?", (cr["id"],))
        await award_currency(self.bot.db, ctx.author.id, gold=value)
        return await ctx.reply(embed=_embed("Release", f"Released **{creature_label(str(cr['name']), str(cr['rarity']))}** Lv.{cr['level']} for **{value:,}** souls."), mention_author=False)

    @commands.hybrid_command(name="salvage", aliases=["scrap", "dismantle"])
    async def salvage(self, ctx: commands.Context, target: str) -> None:
        """Dismantle one weapon, all weapons, or all weapons of a rarity into Weapon Shards."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        target_clean = target.strip()

        if target_clean.lower() in {"all", "*"}:
            weapons = await self.bot.db.fetchall(
                "SELECT * FROM weapons WHERE user_id = ? AND equipped_creature_id IS NULL ORDER BY rarity, id",
                (ctx.author.id,),
            )
            skipped = await self.bot.db.fetchone(
                "SELECT COUNT(*) AS total FROM weapons WHERE user_id = ? AND equipped_creature_id IS NOT NULL",
                (ctx.author.id,),
            )
            if not weapons:
                skip_count = _int(skipped["total"]) if skipped else 0
                msg = "No unequipped weapons to salvage."
                if skip_count:
                    msg += f" Skipped **{skip_count}** equipped weapon(s)."
                return await ctx.reply(embed=_embed("Salvage All", msg), mention_author=False)

            total_shards = sum(weapon_salvage_shards(weapon) for weapon in weapons)
            weapon_ids = [int(row_get(weapon, "id", 0)) for weapon in weapons]
            placeholders = ",".join("?" for _ in weapon_ids)
            await add_item(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY, total_shards)
            await self.bot.db.execute(f"DELETE FROM weapons WHERE user_id = ? AND id IN ({placeholders})", (ctx.author.id, *weapon_ids))
            skip_count = _int(skipped["total"]) if skipped else 0
            extra = f" Skipped **{skip_count}** equipped weapon(s)." if skip_count else ""
            return await ctx.reply(
                embed=_embed("Salvage All", f"Dismantled **{len(weapons)}** weapon(s) into {material_label(WEAPON_SHARD_KEY)} **{total_shards}**.{extra}"),
                mention_author=False,
            )

        rarity_clean = normalize_rarity(target_clean)
        if rarity_clean is not None:
            weapons = await self.bot.db.fetchall(
                "SELECT * FROM weapons WHERE user_id = ? AND rarity = ? AND equipped_creature_id IS NULL ORDER BY id",
                (ctx.author.id, rarity_clean),
            )
            skipped = await self.bot.db.fetchone(
                "SELECT COUNT(*) AS total FROM weapons WHERE user_id = ? AND rarity = ? AND equipped_creature_id IS NOT NULL",
                (ctx.author.id, rarity_clean),
            )
            if not weapons:
                skip_count = _int(skipped["total"]) if skipped else 0
                msg = f"No unequipped **{rarity_clean}** weapons to salvage."
                if skip_count:
                    msg += f" Skipped **{skip_count}** equipped weapon(s)."
                return await ctx.reply(embed=_embed("Salvage", msg), mention_author=False)

            total_shards = sum(weapon_salvage_shards(weapon) for weapon in weapons)
            weapon_ids = [int(row_get(weapon, "id", 0)) for weapon in weapons]
            placeholders = ",".join("?" for _ in weapon_ids)
            await add_item(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY, total_shards)
            await self.bot.db.execute(f"DELETE FROM weapons WHERE user_id = ? AND id IN ({placeholders})", (ctx.author.id, *weapon_ids))
            skip_count = _int(skipped["total"]) if skipped else 0
            extra = f" Skipped **{skip_count}** equipped weapon(s)." if skip_count else ""
            return await ctx.reply(
                embed=_embed("Salvage", f"Dismantled **{len(weapons)}** {rarity_label(rarity_clean)} weapon(s) into {material_label(WEAPON_SHARD_KEY)} **{total_shards}**.{extra}"),
                mention_author=False,
            )

        if not target_clean.isdigit():
            valid = ", ".join(RARITY_INDEX.keys())
            return await ctx.reply(embed=_embed("Salvage", f"Use a weapon ID, `all`, or a rarity.\nValid rarities: {valid}."), mention_author=False)

        weapon_id = int(target_clean)
        weapon = await self.bot.db.fetchone(
            "SELECT * FROM weapons WHERE id = ? AND user_id = ?",
            (weapon_id, ctx.author.id),
        )
        if weapon is None:
            return await ctx.reply(embed=_embed("Salvage", "Weapon not found."), mention_author=False, ephemeral=True)
        if row_get(weapon, "equipped_creature_id") is not None:
            return await ctx.reply(embed=_embed("Salvage", "Unequip this weapon before dismantling it."), mention_author=False)
        shards = weapon_salvage_shards(weapon)
        display = weapon_display_name(weapon)
        await add_item(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY, shards)
        await self.bot.db.execute("DELETE FROM weapons WHERE id = ?", (weapon_id,))
        return await ctx.reply(embed=_embed("Salvage", f"Dismantled **{display}** into {material_label(WEAPON_SHARD_KEY)} **{shards}**."), mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGShop(bot))
