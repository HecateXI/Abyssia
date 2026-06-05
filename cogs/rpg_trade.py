"""Player-to-player trading system for weapons, creatures, and currency."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import discord
from discord.ext import commands

from core.rpg import (
    add_item,
    award_currency,
    ensure_player,
    get_quantity,
    inventory_rows,
    player_weapons,
    team_creatures,
    weapon_display_name,
    weapon_for_creature,
)
from core.rpg_data import MATERIALS, RARITY_INDEX
from core.theme import GOLD_COLOR, creature_label, dark_embed, rarity_label, status_embed


def _int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


# ══════════════════════════════════════════════════════════════════
#  TRADE SESSION
# ══════════════════════════════════════════════════════════════════

@dataclass
class TradeOffer:
    weapons: list[int] = field(default_factory=list)
    creatures: list[int] = field(default_factory=list)
    souls: int = 0
    gems: int = 0
    confirmed: bool = False


@dataclass
class TradeSession:
    guild_id: int
    player_a: discord.Member
    player_b: discord.Member
    offer_a: TradeOffer = field(default_factory=TradeOffer)
    offer_b: TradeOffer = field(default_factory=TradeOffer)
    message: discord.Message | None = None
    expired: bool = False


def _offer_summary(offer: TradeOffer, label: str) -> str:
    parts: list[str] = []
    if offer.souls > 0:
        parts.append(f"**{offer.souls:,}** Souls")
    if offer.gems > 0:
        parts.append(f"**{offer.gems}** Gems")
    if offer.weapons:
        parts.append(f"{len(offer.weapons)} weapon(s)")
    if offer.creatures:
        parts.append(f"{len(offer.creatures)} creature(s)")
    if not parts:
        return f"*{label} has added nothing yet.*"
    return " + ".join(parts)


def _trade_embed(session: TradeSession) -> discord.Embed:
    embed = discord.Embed(title="🤝 Trade", color=GOLD_COLOR)
    a_name = session.player_a.display_name
    b_name = session.player_b.display_name
    a_check = " ✅" if session.offer_a.confirmed else ""
    b_check = " ✅" if session.offer_b.confirmed else ""
    embed.add_field(name=f"{a_name}{a_check}", value=_offer_summary(session.offer_a, a_name), inline=False)
    embed.add_field(name=f"{b_name}{b_check}", value=_offer_summary(session.offer_b, b_name), inline=False)
    embed.set_footer(text="Both players must confirm to complete the trade.")
    return embed


# ══════════════════════════════════════════════════════════════════
#  TRADE VIEW
# ══════════════════════════════════════════════════════════════════

class TradeView(discord.ui.View):
    def __init__(self, session: TradeSession) -> None:
        super().__init__(timeout=120)
        self.session = session

    def _is_participant(self, user_id: int) -> bool:
        return user_id in (self.session.player_a.id, self.session.player_b.id)

    def _get_offer(self, user_id: int) -> TradeOffer:
        if user_id == self.session.player_a.id:
            return self.session.offer_a
        return self.session.offer_b

    def _get_other_offer(self, user_id: int) -> TradeOffer:
        if user_id == self.session.player_a.id:
            return self.session.offer_b
        return self.session.offer_a

    async def _refresh(self) -> None:
        if self.session.message:
            await self.session.message.edit(embed=_trade_embed(self.session), view=self)

    @discord.ui.button(label="⚔️ Add Weapon", style=discord.ButtonStyle.primary, row=0)
    async def add_weapon(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self._is_participant(interaction.user.id):
            await interaction.response.send_message("This is not your trade.", ephemeral=True)
            return
        offer = self._get_offer(interaction.user.id)
        if offer.confirmed:
            await interaction.response.send_message("You already confirmed. Unconfirm to change your offer.", ephemeral=True)
            return
        db = interaction.client.db
        weapons = await player_weapons(db, interaction.user.id)
        unequipped = [w for w in weapons if not w["equipped_creature_id"] and int(w["id"]) not in offer.weapons]
        if not unequipped:
            await interaction.response.send_message("No unequipped weapons available.", ephemeral=True)
            return
        options = []
        for w in unequipped[:25]:
            wname = weapon_display_name(w)
            options.append(discord.SelectOption(
                label=wname[:100],
                value=str(w["id"]),
                description=f"{rarity_label(str(w['rarity']))} ATK+{w['attack_bonus']} DEF+{w['defense_bonus']}",
                emoji="⚔️",
            ))
        view = WeaponSelectView(self.session, interaction.user.id, unequipped)
        await interaction.response.send_message("Select a weapon to add:", view=view, ephemeral=True)

    @discord.ui.button(label="🐾 Add Creature", style=discord.ButtonStyle.primary, row=0)
    async def add_creature(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self._is_participant(interaction.user.id):
            await interaction.response.send_message("This is not your trade.", ephemeral=True)
            return
        offer = self._get_offer(interaction.user.id)
        if offer.confirmed:
            await interaction.response.send_message("You already confirmed. Unconfirm to change your offer.", ephemeral=True)
            return
        db = interaction.client.db
        creatures = await team_creatures(db, interaction.user.id)
        all_creatures = await db.fetchall(
            "SELECT id, name, rarity, level, attack, defense FROM rpg_creatures WHERE user_id = ? ORDER BY rarity DESC, level DESC",
            (interaction.user.id,),
        )
        team_ids = {int(c["id"]) for c in creatures}
        available = [c for c in all_creatures if int(c["id"]) not in team_ids and int(c["id"]) not in offer.creatures]
        if not available:
            await interaction.response.send_message("No creatures available to trade.", ephemeral=True)
            return
        options = []
        for c in available[:25]:
            options.append(discord.SelectOption(
                label=f"{creature_label(str(c['name']), str(c['rarity']))[:70]} Lv.{c['level']}",
                value=str(c["id"]),
                description=f"{rarity_label(str(c['rarity']))} ATK {c['attack']} DEF {c['defense']}",
                emoji="🐾",
            ))
        view = CreatureSelectView(self.session, interaction.user.id, available)
        await interaction.response.send_message("Select a creature to add:", view=view, ephemeral=True)

    @discord.ui.button(label="💰 Add Souls", style=discord.ButtonStyle.secondary, row=1)
    async def add_souls(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self._is_participant(interaction.user.id):
            await interaction.response.send_message("This is not your trade.", ephemeral=True)
            return
        offer = self._get_offer(interaction.user.id)
        if offer.confirmed:
            await interaction.response.send_message("You already confirmed. Unconfirm to change your offer.", ephemeral=True)
            return
        modal = CurrencyModal(self.session, interaction.user.id, "souls")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💎 Add Gems", style=discord.ButtonStyle.secondary, row=1)
    async def add_gems(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self._is_participant(interaction.user.id):
            await interaction.response.send_message("This is not your trade.", ephemeral=True)
            return
        offer = self._get_offer(interaction.user.id)
        if offer.confirmed:
            await interaction.response.send_message("You already confirmed. Unconfirm to change your offer.", ephemeral=True)
            return
        modal = CurrencyModal(self.session, interaction.user.id, "gems")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Removed Materials", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def add_material(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self._is_participant(interaction.user.id):
            await interaction.response.send_message("This is not your trade.", ephemeral=True)
            return
        offer = self._get_offer(interaction.user.id)
        if offer.confirmed:
            await interaction.response.send_message("You already confirmed. Unconfirm to change your offer.", ephemeral=True)
            return
        await interaction.response.send_message("Crafting materials were removed. Trade weapons, creatures, Souls, or Gems.", ephemeral=True)
        return
        db = interaction.client.db
        inv = await inventory_rows(db, interaction.user.id)
        mats = [r for r in inv if r["item_type"] == "material" and r["quantity"] > 0]
        if not mats:
            await interaction.response.send_message("No materials to trade.", ephemeral=True)
            return
        options = []
        for m in mats[:25]:
            name = MATERIALS.get(m["item_key"], m["item_key"].replace("_", " ").title())
            options.append(discord.SelectOption(
                label=name[:100],
                value=m["item_key"],
                description=f"Qty: {m['quantity']}",
                emoji="📦",
            ))
        view = MaterialSelectView(self.session, interaction.user.id, mats)
        await interaction.response.send_message("Select a material to add:", view=view, ephemeral=True)

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success, row=2)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self._is_participant(interaction.user.id):
            await interaction.response.send_message("This is not your trade.", ephemeral=True)
            return
        offer = self._get_offer(interaction.user.id)
        other = self._get_other_offer(interaction.user.id)
        offer.confirmed = True
        await interaction.response.send_message("✅ You confirmed the trade.", ephemeral=True)
        if other.confirmed:
            await self._execute_trade(interaction)
        else:
            await self._refresh()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, row=2)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self._is_participant(interaction.user.id):
            await interaction.response.send_message("This is not your trade.", ephemeral=True)
            return
        self.session.expired = True
        self.stop()
        embed = dark_embed("Trade Cancelled", "The trade has been cancelled.", color=discord.Color.dark_red())
        if self.session.message:
            await self.session.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Trade cancelled.", ephemeral=True)

    async def _execute_trade(self, interaction: discord.Interaction) -> None:
        self.stop()
        db = interaction.client.db
        a_id = self.session.player_a.id
        b_id = self.session.player_b.id
        ga = self.session.guild_id
        gb = self.session.guild_id
        a = self.session.offer_a
        b = self.session.offer_b
        errors: list[str] = []

        # Validate and transfer weapons
        for wid in a.weapons:
            row = await db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (wid, a_id))
            if not row or row["equipped_creature_id"]:
                errors.append(f"Weapon #{wid} no longer available.")
                continue
            await db.execute("UPDATE weapons SET user_id = ? WHERE id = ?", (b_id, wid))
        for wid in b.weapons:
            row = await db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (wid, b_id))
            if not row or row["equipped_creature_id"]:
                errors.append(f"Weapon #{wid} no longer available.")
                continue
            await db.execute("UPDATE weapons SET user_id = ? WHERE id = ?", (a_id, wid))

        # Validate and transfer creatures
        for cid in a.creatures:
            row = await db.fetchone("SELECT id FROM rpg_creatures WHERE id = ? AND user_id = ?", (cid, a_id))
            team_check = await db.fetchone("SELECT creature_id FROM rpg_teams WHERE creature_id = ?", (cid,))
            if not row or team_check:
                errors.append(f"Creature #{cid} no longer available.")
                continue
            await db.execute("UPDATE rpg_creatures SET user_id = ? WHERE id = ?", (b_id, cid))
        for cid in b.creatures:
            row = await db.fetchone("SELECT id FROM rpg_creatures WHERE id = ? AND user_id = ?", (cid, b_id))
            team_check = await db.fetchone("SELECT creature_id FROM rpg_teams WHERE creature_id = ?", (cid,))
            if not row or team_check:
                errors.append(f"Creature #{cid} no longer available.")
                continue
            await db.execute("UPDATE rpg_creatures SET user_id = ? WHERE id = ?", (a_id, cid))

        # Validate and transfer materials
        for mk, mq in getattr(a, "materials", {}).items():
            have = await get_quantity(db, a_id, "material", mk)
            if have < mq:
                errors.append(f"Not enough {MATERIALS.get(mk, mk)}.")
                continue
            await add_item(db, a_id, "material", mk, -mq)
            await add_item(db, b_id, "material", mk, mq)
        for mk, mq in getattr(b, "materials", {}).items():
            have = await get_quantity(db, b_id, "material", mk)
            if have < mq:
                errors.append(f"Not enough {MATERIALS.get(mk, mk)}.")
                continue
            await add_item(db, b_id, "material", mk, -mq)
            await add_item(db, a_id, "material", mk, mq)

        # Validate and transfer currency
        pa = await ensure_player(db, a_id, "")
        pb = await ensure_player(db, b_id, "")
        if a.souls > 0:
            if _int(pa["gold"]) < a.souls:
                errors.append("Not enough Souls for trade.")
            else:
                await award_currency(db, a_id, gold=-a.souls)
                await award_currency(db, b_id, gold=a.souls)
        if a.gems > 0:
            if _int(pa["gems"]) < a.gems:
                errors.append("Not enough Gems for trade.")
            else:
                await award_currency(db, a_id, gems=-a.gems)
                await award_currency(db, b_id, gems=a.gems)
        if b.souls > 0:
            if _int(pb["gold"]) < b.souls:
                errors.append("Not enough Souls for trade.")
            else:
                await award_currency(db, b_id, gold=-b.souls)
                await award_currency(db, a_id, gold=b.souls)
        if b.gems > 0:
            if _int(pb["gems"]) < b.gems:
                errors.append("Not enough Gems for trade.")
            else:
                await award_currency(db, b_id, gems=-b.gems)
                await award_currency(db, a_id, gems=b.gems)

        if errors:
            embed = dark_embed("⚠️ Trade Completed with Issues", "\n".join(errors), color=discord.Color.orange())
        else:
            embed = dark_embed("✅ Trade Complete", f"{self.session.player_a.mention} and {self.session.player_b.mention} have completed their trade!", color=discord.Color.green())
        if self.session.message:
            await self.session.message.edit(embed=embed, view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return self._is_participant(interaction.user.id)

    async def on_timeout(self) -> None:
        self.session.expired = True
        embed = dark_embed("⏱️ Trade Expired", "The trade has timed out.", color=discord.Color.dark_red())
        if self.session.message:
            await self.session.message.edit(embed=embed, view=None)


# ══════════════════════════════════════════════════════════════════
#  SUB-VIEWS
# ══════════════════════════════════════════════════════════════════

class WeaponSelectView(discord.ui.View):
    def __init__(self, session: TradeSession, user_id: int, weapons: list) -> None:
        super().__init__(timeout=60)
        self.session = session
        self.user_id = user_id
        self.weapons = weapons
        self.add_item(WeaponSelect(session, user_id, weapons))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Cancelled.", view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id


class WeaponSelect(discord.ui.Select):
    def __init__(self, session: TradeSession, user_id: int, weapons: list) -> None:
        super().__init__(placeholder="Select a weapon...", options=[
            discord.SelectOption(label=weapon_display_name(w)[:100], value=str(w["id"]),
                                description=f"{rarity_label(str(w['rarity']))} ATK+{w['attack_bonus']} DEF+{w['defense_bonus']}")
            for w in weapons[:25]
        ])
        self.session = session
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction) -> None:
        wid = int(self.values[0])
        offer = self.session.offer_a if self.user_id == self.session.player_a.id else self.session.offer_b
        if wid not in offer.weapons:
            offer.weapons.append(wid)
        offer.confirmed = False
        other_offer = self.session.offer_b if self.user_id == self.session.player_a.id else self.session.offer_a
        other_offer.confirmed = False
        await interaction.response.edit_message(content=f"✅ Added weapon #{wid}.", view=None)
        if self.session.message:
            await self.session.message.edit(embed=_trade_embed(self.session))


class CreatureSelectView(discord.ui.View):
    def __init__(self, session: TradeSession, user_id: int, creatures: list) -> None:
        super().__init__(timeout=60)
        self.session = session
        self.user_id = user_id
        self.add_item(CreatureSelect(session, user_id, creatures))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Cancelled.", view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id


class CreatureSelect(discord.ui.Select):
    def __init__(self, session: TradeSession, user_id: int, creatures: list) -> None:
        super().__init__(placeholder="Select a creature...", options=[
            discord.SelectOption(label=f"{creature_label(str(c['name']), str(c['rarity']))[:70]} Lv.{c['level']}", value=str(c["id"]),
                                description=f"{rarity_label(str(c['rarity']))} ATK {c['attack']} DEF {c['defense']}")
            for c in creatures[:25]
        ])
        self.session = session
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction) -> None:
        cid = int(self.values[0])
        offer = self.session.offer_a if self.user_id == self.session.player_a.id else self.session.offer_b
        if cid not in offer.creatures:
            offer.creatures.append(cid)
        offer.confirmed = False
        other_offer = self.session.offer_b if self.user_id == self.session.player_a.id else self.session.offer_a
        other_offer.confirmed = False
        await interaction.response.edit_message(content=f"✅ Added creature #{cid}.", view=None)
        if self.session.message:
            await self.session.message.edit(embed=_trade_embed(self.session))


class MaterialSelectView(discord.ui.View):
    def __init__(self, session: TradeSession, user_id: int, materials: list) -> None:
        super().__init__(timeout=60)
        self.session = session
        self.user_id = user_id
        self.add_item(MaterialSelect(session, user_id, materials))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Cancelled.", view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id


class MaterialSelect(discord.ui.Select):
    def __init__(self, session: TradeSession, user_id: int, materials: list) -> None:
        super().__init__(placeholder="Select a material...", options=[
            discord.SelectOption(label=MATERIALS.get(m["item_key"], m["item_key"].replace("_", " ").title())[:100],
                                value=m["item_key"],
                                description=f"Qty: {m['quantity']}")
            for m in materials[:25]
        ])
        self.session = session
        self.user_id = user_id
        self._materials = {m["item_key"]: m["quantity"] for m in materials}

    async def callback(self, interaction: discord.Interaction) -> None:
        mk = self.values[0]
        max_qty = self._materials.get(mk, 0)
        modal = MaterialAmountModal(self.session, self.user_id, mk, max_qty)
        await interaction.response.send_modal(modal)


class MaterialAmountModal(discord.ui.Modal, title="Material Amount"):
    amount = discord.ui.TextInput(label="Quantity", placeholder="How many?", style=discord.TextStyle.short)

    def __init__(self, session: TradeSession, user_id: int, material_key: str, max_qty: int) -> None:
        super().__init__()
        self.session = session
        self.user_id = user_id
        self.material_key = material_key
        self.max_qty = max_qty

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            qty = int(self.amount.value)
        except (TypeError, ValueError):
            await interaction.response.send_message("Invalid number.", ephemeral=True)
            return
        qty = max(1, min(qty, self.max_qty))
        offer = self.session.offer_a if self.user_id == self.session.player_a.id else self.session.offer_b
        offer.materials[self.material_key] = offer.materials.get(self.material_key, 0) + qty
        offer.confirmed = False
        other_offer = self.session.offer_b if self.user_id == self.session.player_a.id else self.session.offer_a
        other_offer.confirmed = False
        name = MATERIALS.get(self.material_key, self.material_key.replace("_", " ").title())
        await interaction.response.send_message(f"✅ Added {qty}x {name}.", ephemeral=True)
        if self.session.message:
            await self.session.message.edit(embed=_trade_embed(self.session))


class CurrencyModal(discord.ui.Modal, title="Add Currency"):
    amount = discord.ui.TextInput(label="Amount", placeholder="How many?", style=discord.TextStyle.short)

    def __init__(self, session: TradeSession, user_id: int, currency: str) -> None:
        super().__init__()
        self.session = session
        self.user_id = user_id
        self.currency = currency

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            qty = int(self.amount.value)
        except (TypeError, ValueError):
            await interaction.response.send_message("Invalid number.", ephemeral=True)
            return
        qty = max(0, qty)
        offer = self.session.offer_a if self.user_id == self.session.player_a.id else self.session.offer_b
        if self.currency == "souls":
            offer.souls = qty
        else:
            offer.gems = qty
        offer.confirmed = False
        other_offer = self.session.offer_b if self.user_id == self.session.player_a.id else self.session.offer_a
        other_offer.confirmed = False
        label = "Souls" if self.currency == "souls" else "Gems"
        await interaction.response.send_message(f"✅ Set {label} offer to **{qty:,}**.", ephemeral=True)
        if self.session.message:
            await self.session.message.edit(embed=_trade_embed(self.session))


# ══════════════════════════════════════════════════════════════════
#  ACTIVE TRADES TRACKING
# ══════════════════════════════════════════════════════════════════

_active_trades: dict[int, TradeSession] = {}


# ══════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════

class RPGTrade(commands.Cog):
    """Player-to-player trading."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="exchange", aliases=["ptrade", "xchange"])
    async def trade(self, ctx: commands.Context, target: discord.Member | None = None) -> None:
        """Trade weapons, creatures, and currency with another hunter."""
        assert ctx.guild is not None
        if target is None:
            await ctx.reply(embed=status_embed("Trade", "Usage: `b trade @player`"), mention_author=False)
            return
        if target.bot:
            raise commands.BadArgument("You cannot trade with bots.")
        if target.id == ctx.author.id:
            raise commands.BadArgument("You cannot trade with yourself.")
        if target.id in _active_trades:
            raise commands.BadArgument("That player is already in a trade.")
        if ctx.author.id in _active_trades:
            raise commands.BadArgument("You are already in a trade.")

        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        await ensure_player(self.bot.db, target.id, target.display_name)

        session = TradeSession(guild_id=ctx.guild.id, player_a=ctx.author, player_b=target)
        _active_trades[ctx.author.id] = session
        _active_trades[target.id] = session

        embed = _trade_embed(session)
        embed.description = f"{ctx.author.mention} wants to trade with {target.mention}!\n\nBoth players add items, then confirm."
        view = TradeView(session)
        msg = await ctx.reply(embed=embed, view=view, mention_author=False)
        session.message = msg

        timed_out = await view.wait()
        if not session.expired and timed_out:
            session.expired = True
            embed = dark_embed("⏱️ Trade Expired", "The trade has timed out.", color=discord.Color.dark_red())
            await msg.edit(embed=embed, view=None)

        _active_trades.pop(ctx.author.id, None)
        _active_trades.pop(target.id, None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGTrade(bot))
