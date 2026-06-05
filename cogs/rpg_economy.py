from __future__ import annotations

from dataclasses import dataclass
import random

import discord
from discord.ext import commands

from core.rpg import add_item, award_currency, daily_reset_text, ensure_player, get_quantity, now_ts, today_key
from core.items import HUNT_SWORD_KEY, HUNT_SWORD_NAME
from core.rpg_data import EQUIPMENT, normalize_key
from core.theme import GOLD_COLOR, asset_emoji, creature_label, currency_label, dark_embed, equipment_label, status_embed


@dataclass(frozen=True)
class ShopItem:
    item_type: str
    item_key: str
    price: int
    description: str


SHOP_POOL: dict[str, ShopItem] = {
    HUNT_SWORD_KEY: ShopItem("consumable", HUNT_SWORD_KEY, 95, "Temporary charge for extra `b hunt` rolls."),
}

SHOP_ROTATION_SLOTS = 8

def _today_key() -> str:
    return today_key()


async def _ensure_shop_rotation(db, guild_id: int) -> list[tuple[int, str, str, int]]:
    today = _today_key()
    existing = await db.fetchall(
        "SELECT slot, item_type, item_key, price FROM rpg_shop_rotation WHERE guild_id = ? AND date = ? ORDER BY slot",
        (guild_id, today),
    )
    if existing:
        return [(row["slot"], row["item_type"], row["item_key"], row["price"]) for row in existing]

    always_include = {HUNT_SWORD_KEY: ShopItem("consumable", HUNT_SWORD_KEY, 95, "")}
    pool = {k: v for k, v in SHOP_POOL.items() if k not in always_include}
    keys = list(pool.keys())
    rng = random.Random(f"supply_shop:{guild_id}:{today}")
    chosen = rng.sample(keys, min(SHOP_ROTATION_SLOTS - len(always_include), len(keys)))
    rotation = list(always_include.items()) + [(k, pool[k]) for k in chosen]
    rotation = rotation[:SHOP_ROTATION_SLOTS]

    for slot, (key, item) in enumerate(rotation):
        price = max(5, item.price)
        await db.execute(
            "INSERT INTO rpg_shop_rotation (guild_id, slot, item_type, item_key, price, date) VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, slot, item.item_type, item.item_key, price, today),
        )
        existing.append((slot, item.item_type, item.item_key, price))
    return existing


def normalize_item_type(value: str) -> str:
    key = normalize_key(value)
    if key in {"equipment", "gear", "weapon", "charm"}:
        return "equipment"
    raise commands.BadArgument("Item type must be equipment.")


def display_item(item_type: str, item_key: str) -> str:
    if item_type == "equipment":
        equipment = EQUIPMENT.get(item_key)
        return equipment_label(item_key, equipment.name if equipment else item_key.replace("_", " ").title())
    if item_type == "consumable" and item_key == HUNT_SWORD_KEY:
        emoji = asset_emoji("consumable", item_key)
        return f"{emoji} {HUNT_SWORD_NAME}" if emoji else HUNT_SWORD_NAME
    return item_key.replace("_", " ").title()


def resolve_item_key(item_type: str, value: str) -> str:
    key = normalize_key(value)
    if item_type == "equipment":
        if key in EQUIPMENT:
            return key
        for equipment in EQUIPMENT.values():
            if normalize_key(equipment.name) == key:
                return equipment.key
        raise commands.BadArgument("Unknown equipment.")
    raise commands.BadArgument("Unknown item type.")


def equipment_sell_value(item_key: str) -> int:
    equipment = EQUIPMENT.get(item_key)
    if equipment is None:
        return 50
    craft_gold = int(equipment.cost.get("gold", 0))
    return max(75, craft_gold // 2 + equipment.tier * 90)


class TradeView(discord.ui.View):
    def __init__(self, target_id: int) -> None:
        super().__init__(timeout=60)
        self.target_id = target_id
        self.accepted = False

    def _disable(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def _check_user(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("Only the trade target can answer this offer.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_user(interaction):
            return
        self.accepted = True
        self._disable()
        await interaction.response.edit_message(content="Trade accepted. Finalizing transfer...", view=self)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_user(interaction):
            return
        self._disable()
        await interaction.response.edit_message(content="Trade declined.", view=self)
        self.stop()


class RPGEconomy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="souls", aliases=["bsouls", "wallet", "balance"])
    async def souls(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        """Show your Soul and Gem balance."""
        assert ctx.guild is not None
        target = member or ctx.author
        player = await ensure_player(self.bot.db, target.id, target.display_name)
        embed = dark_embed(
            f"{target.display_name}'s Wallet",
            f"{currency_label('gold')} **{int(player['gold']):,}**\n{currency_label('gems')} **{int(player['gems']):,}**",
            color=GOLD_COLOR,
        )
        embed.set_author(name=str(target), icon_url=target.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="give", aliases=["bgive", "givesouls", "pay"])
    async def give_souls(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        """Give Souls to another player."""
        assert ctx.guild is not None
        if member.bot:
            raise commands.BadArgument("You cannot give Souls to bots.")
        if member.id == ctx.author.id:
            raise commands.BadArgument("You cannot give Souls to yourself.")
        if amount <= 0:
            raise commands.BadArgument("Amount must be greater than zero.")
        if amount > 1_000_000_000:
            raise commands.BadArgument("That transfer amount is too large.")

        sender = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        await ensure_player(self.bot.db, member.id, member.display_name)
        if int(sender["gold"]) < amount:
            raise commands.BadArgument(f"You only have {currency_label('gold')} **{int(sender['gold']):,}**.")

        await award_currency(self.bot.db, ctx.author.id, gold=-amount)
        await award_currency(self.bot.db, member.id, gold=amount)
        embed = status_embed(
            "Souls Sent",
            f"{ctx.author.mention} gave {member.mention} {currency_label('gold')} **{amount:,}**.",
        )
        await ctx.reply(embed=embed, mention_author=False)

    async def _has_inventory(self, user_id: int, item_type: str, item_key: str, quantity: int) -> bool:
        return await get_quantity(self.bot.db, user_id, item_type, item_key) >= quantity

    async def _remove_inventory(self, user_id: int, item_type: str, item_key: str, quantity: int) -> None:
        await add_item(self.bot.db, user_id, item_type, item_key, -quantity)

    async def _assert_can_move_equipment(self, user_id: int, item_key: str, quantity: int) -> None:
        player = await ensure_player(self.bot.db, user_id, "Hunter")
        owned = await get_quantity(self.bot.db, user_id, "equipment", item_key)
        equipped_count = 1 if item_key in {player["equipped_weapon"], player["equipped_charm"]} else 0
        if owned - equipped_count < quantity:
            raise commands.BadArgument("You cannot move your currently equipped copy of that item.")

    @commands.hybrid_group(name="shop", invoke_without_command=True)
    async def shop(self, ctx: commands.Context) -> None:
        """Browse the daily rotating Abyssia supply shop."""
        assert ctx.guild is not None
        rotation = await _ensure_shop_rotation(self.bot.db, ctx.guild.id)
        today = _today_key()
        lines = []
        for slot, item_type, item_key, price in rotation:
            item = SHOP_POOL.get(item_key)
            display = display_item(item_type, item_key)
            desc = f" - {item.description}" if item and item.description else ""
            lines.append(f"`#{slot}` {display} — {currency_label('gold')} **{price}**{desc}")
        embed = dark_embed("Abyssia Shop — Daily Rotation", "\n".join(lines), color=GOLD_COLOR)
        embed.set_footer(text=f"Refreshes daily at {daily_reset_text()} for everyone - Use b shop buy <slot> [quantity]")
        await ctx.reply(embed=embed, mention_author=False)

    @shop.command(name="buy")
    async def shop_buy(self, ctx: commands.Context, slot_or_item: str, quantity: int = 1) -> None:
        """Buy an item from the daily shop by slot number or name."""
        assert ctx.guild is not None
        if quantity < 1 or quantity > 99:
            raise commands.BadArgument("Quantity must be between 1 and 99.")
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        today = _today_key()
        rotation = await _ensure_shop_rotation(self.bot.db, ctx.guild.id)

        shop_item_data = None
        item_key_found = None
        item_type_found = None
        price_found = None

        if slot_or_item.isdigit():
            slot = int(slot_or_item)
            for s, it, ik, pr in rotation:
                if s == slot:
                    shop_item_data = (it, ik, pr)
                    item_key_found = ik
                    item_type_found = it
                    price_found = pr
                    break
        else:
            search_key = normalize_key(slot_or_item)
            for s, it, ik, pr in rotation:
                if ik == search_key or normalize_key(display_item(it, ik)) == search_key:
                    shop_item_data = (it, ik, pr)
                    item_key_found = ik
                    item_type_found = it
                    price_found = pr
                    break

        if shop_item_data is None:
            raise commands.BadArgument("That item is not in today's shop rotation. Use `b shop` to see what's available.")

        if item_type_found == "equipment":
            quantity = 1
            if await get_quantity(self.bot.db, ctx.author.id, "equipment", item_key_found) > 0:
                raise commands.BadArgument("You already own that equipment.")
        cost = price_found * quantity
        if int(player["gold"]) < cost:
            raise commands.BadArgument(f"You need {cost} Souls.")
        await award_currency(self.bot.db, ctx.author.id, gold=-cost)
        await add_item(self.bot.db, ctx.author.id, item_type_found, item_key_found, quantity)
        await ctx.reply(embed=status_embed("Purchase Complete", f"Bought {display_item(item_type_found, item_key_found)} x`{quantity}` for {currency_label('gold')} **{cost}**."), mention_author=False)

    @commands.hybrid_command(name="sell")
    async def sell(self, ctx: commands.Context, item: str, quantity: int = 1) -> None:
        """Sell a creature id or legacy equipment for Souls."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        if quantity < 1:
            raise commands.BadArgument("Quantity must be at least 1.")
        if item.isdigit():
            creature_id = int(item)
            creature = await self.bot.db.fetchone(
                "SELECT * FROM rpg_creatures WHERE user_id = ? AND id = ?",
                (ctx.author.id, creature_id),
            )
            if creature is None:
                raise commands.BadArgument("That monster id is not in your collection.")
            value = int(creature["value"]) if "value" in creature.keys() else max(25, int(creature["level"]) * 10)
            await self.bot.db.execute("DELETE FROM rpg_teams WHERE user_id = ? AND creature_id = ?", (ctx.author.id, creature_id))
            await self.bot.db.execute("DELETE FROM rpg_creatures WHERE user_id = ? AND id = ?", (ctx.author.id, creature_id))
            await award_currency(self.bot.db, ctx.author.id, gold=value)
            await ctx.reply(embed=status_embed("Monster Released", f"Released **{creature_label(str(creature['name']), str(creature['rarity']))}** for {currency_label('gold')} **{value}**."), mention_author=False)
            return

        item_type = "equipment"
        item_key = resolve_item_key(item_type, item)
        quantity = 1
        await self._assert_can_move_equipment(ctx.author.id, item_key, quantity)
        if not await self._has_inventory(ctx.author.id, item_type, item_key, quantity):
            raise commands.BadArgument("You do not own that equipment.")
        value = equipment_sell_value(item_key)

        await self._remove_inventory(ctx.author.id, item_type, item_key, quantity)
        await award_currency(self.bot.db, ctx.author.id, gold=value)
        await ctx.reply(embed=status_embed("Sale Complete", f"Sold {display_item(item_type, item_key)} x`{quantity}` for {currency_label('gold')} **{value}**."), mention_author=False)

    @commands.hybrid_group(name="market", invoke_without_command=True)
    async def market(self, ctx: commands.Context) -> None:
        """Browse player market listings."""
        assert ctx.guild is not None
        rows = await self.bot.db.fetchall(
            "SELECT * FROM rpg_market_listings WHERE guild_id = ? AND item_type != 'material' ORDER BY created_at DESC LIMIT 12",
            (ctx.guild.id,),
        )
        if not rows:
            await ctx.reply(embed=status_embed("Market", "No listings yet. Use `b market sell equipment lucky_charm 1 250`."), mention_author=False)
            return
        lines = []
        for row in rows:
            lines.append(
                f"`#{row['id']}` {display_item(row['item_type'], row['item_key'])} x`{row['quantity']}` "
                f"for {currency_label('gold')} **{row['price']}** by <@{row['seller_id']}>"
            )
        await ctx.reply(embed=dark_embed("Player Market", "\n".join(lines), color=GOLD_COLOR), mention_author=False)

    @market.command(name="sell")
    async def market_sell(self, ctx: commands.Context, item_type: str, item: str, quantity: int, price: int) -> None:
        """List legacy equipment on the market."""
        assert ctx.guild is not None
        if quantity < 1:
            raise commands.BadArgument("Quantity must be at least 1.")
        if price < 1:
            raise commands.BadArgument("Price must be at least 1 Soul.")
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        kind = normalize_item_type(item_type)
        item_key = resolve_item_key(kind, item)
        if kind == "equipment":
            quantity = 1
            await self._assert_can_move_equipment(ctx.author.id, item_key, quantity)
        if not await self._has_inventory(ctx.author.id, kind, item_key, quantity):
            raise commands.BadArgument("You do not have enough quantity to list.")
        await self._remove_inventory(ctx.author.id, kind, item_key, quantity)
        listing_id = await self.bot.db.insert(
            """
            INSERT INTO rpg_market_listings (guild_id, seller_id, item_type, item_key, quantity, price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ctx.guild.id, ctx.author.id, kind, item_key, quantity, price, now_ts()),
        )
        await ctx.reply(embed=status_embed("Market Listing Created", f"`#{listing_id}` {display_item(kind, item_key)} x`{quantity}` listed for {currency_label('gold')} **{price}**."), mention_author=False)

    @market.command(name="buy")
    async def market_buy(self, ctx: commands.Context, listing_id: int) -> None:
        """Buy a player market listing."""
        assert ctx.guild is not None
        buyer = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        listing = await self.bot.db.fetchone("SELECT * FROM rpg_market_listings WHERE guild_id = ? AND id = ?", (ctx.guild.id, listing_id))
        if listing is None:
            raise commands.BadArgument("Listing not found.")
        if int(listing["seller_id"]) == ctx.author.id:
            raise commands.BadArgument("You cannot buy your own listing.")
        if int(buyer["gold"]) < int(listing["price"]):
            raise commands.BadArgument("You do not have enough Souls.")
        await ensure_player(self.bot.db, int(listing["seller_id"]), "Market Seller")
        await award_currency(self.bot.db, ctx.author.id, gold=-int(listing["price"]))
        await award_currency(self.bot.db, int(listing["seller_id"]), gold=int(listing["price"]))
        await add_item(self.bot.db, ctx.author.id, str(listing["item_type"]), str(listing["item_key"]), int(listing["quantity"]))
        await self.bot.db.execute("DELETE FROM rpg_market_listings WHERE guild_id = ? AND id = ?", (ctx.guild.id, listing_id))
        await ctx.reply(embed=status_embed("Market Purchase Complete", f"Bought {display_item(listing['item_type'], listing['item_key'])} x`{listing['quantity']}`."), mention_author=False)

    @market.command(name="cancel")
    async def market_cancel(self, ctx: commands.Context, listing_id: int) -> None:
        """Cancel your market listing and reclaim the item."""
        assert ctx.guild is not None
        listing = await self.bot.db.fetchone(
            "SELECT * FROM rpg_market_listings WHERE guild_id = ? AND id = ? AND seller_id = ?",
            (ctx.guild.id, listing_id, ctx.author.id),
        )
        if listing is None:
            raise commands.BadArgument("Your listing was not found.")
        await add_item(self.bot.db, ctx.author.id, str(listing["item_type"]), str(listing["item_key"]), int(listing["quantity"]))
        await self.bot.db.execute("DELETE FROM rpg_market_listings WHERE guild_id = ? AND id = ?", (ctx.guild.id, listing_id))
        await ctx.reply(embed=status_embed("Listing Cancelled", f"Returned {display_item(listing['item_type'], listing['item_key'])} x`{listing['quantity']}`."), mention_author=False)

    @commands.hybrid_command(name="trade")
    async def trade(
        self,
        ctx: commands.Context,
        member: discord.Member,
        offer_type: str,
        offer_item: str,
        offer_quantity: int,
        request_type: str,
        request_item: str,
        request_quantity: int,
    ) -> None:
        """Offer an item trade to another hunter."""
        assert ctx.guild is not None
        if member.bot or member.id == ctx.author.id:
            raise commands.BadArgument("Choose another non-bot hunter.")
        if offer_quantity < 1 or request_quantity < 1:
            raise commands.BadArgument("Quantities must be at least 1.")
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        await ensure_player(self.bot.db, member.id, member.display_name)
        offer_kind = normalize_item_type(offer_type)
        request_kind = normalize_item_type(request_type)
        offer_key = resolve_item_key(offer_kind, offer_item)
        request_key = resolve_item_key(request_kind, request_item)
        if offer_kind == "equipment":
            offer_quantity = 1
            await self._assert_can_move_equipment(ctx.author.id, offer_key, offer_quantity)
        if request_kind == "equipment":
            request_quantity = 1
            await self._assert_can_move_equipment(member.id, request_key, request_quantity)
        if not await self._has_inventory(ctx.author.id, offer_kind, offer_key, offer_quantity):
            raise commands.BadArgument("You do not have the offered item.")
        if not await self._has_inventory(member.id, request_kind, request_key, request_quantity):
            raise commands.BadArgument("The target does not have the requested item.")

        trade_id = await self.bot.db.insert(
            """
            INSERT INTO rpg_trades (
                guild_id, proposer_id, target_id, offer_type, offer_key, offer_quantity,
                request_type, request_key, request_quantity, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (ctx.author.id, member.id, offer_kind, offer_key, offer_quantity, request_kind, request_key, request_quantity, now_ts()),
        )
        embed = dark_embed(
            "Trade Offer",
            f"{ctx.author.mention} offers {display_item(offer_kind, offer_key)} x`{offer_quantity}`\n"
            f"for {member.mention}'s {display_item(request_kind, request_key)} x`{request_quantity}`.\n\n"
            "This offer expires in 60 seconds.",
            color=GOLD_COLOR,
        )
        view = TradeView(member.id)
        message = await ctx.reply(embed=embed, view=view, mention_author=False)
        timed_out = await view.wait()
        if timed_out:
            view._disable()
            await self.bot.db.execute("UPDATE rpg_trades SET status = 'expired' WHERE id = ?", (trade_id,))
            await message.edit(content="Trade offer expired.", view=view)
            return
        if not view.accepted:
            await self.bot.db.execute("UPDATE rpg_trades SET status = 'declined' WHERE id = ?", (trade_id,))
            return

        if not await self._has_inventory(ctx.author.id, offer_kind, offer_key, offer_quantity):
            raise commands.BadArgument("The offered item is no longer available.")
        if not await self._has_inventory(member.id, request_kind, request_key, request_quantity):
            raise commands.BadArgument("The requested item is no longer available.")
        await self._remove_inventory(ctx.author.id, offer_kind, offer_key, offer_quantity)
        await self._remove_inventory(member.id, request_kind, request_key, request_quantity)
        await add_item(self.bot.db, member.id, offer_kind, offer_key, offer_quantity)
        await add_item(self.bot.db, ctx.author.id, request_kind, request_key, request_quantity)
        await self.bot.db.execute("UPDATE rpg_trades SET status = 'accepted' WHERE id = ?", (trade_id,))
        await ctx.reply(embed=status_embed("Trade Complete", f"{ctx.author.mention} and {member.mention} exchanged items."), mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGEconomy(bot))
