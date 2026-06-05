"""Weapon equip/unequip and creature detail commands."""
from __future__ import annotations

import json
from typing import Any

import discord
from discord.ext import commands

from core.discord_assets import embed_asset, ensure_application_emojis
from core.rpg import (
    add_item,
    creature_weapons,
    ensure_player,
    equip_weapon_to_creature,
    get_quantity,
    player_weapons,
    reroll_weapon,
    row_get,
    team_creatures,
    unequip_weapon,
    weapon_display_name,
    weapon_effects,
    weapon_for_creature,
    weapon_reroll_cost,
    weapon_salvage_shards,
    weapon_stats,
)
from core.rpg_data import RARITY_BY_NAME, WEAPON_SHARD_KEY, WEAPON_TYPES
from core.theme import (
    asset_emoji,
    creature_label,
    material_label,
    passive_emoji,
    passive_label,
    rarity_emoji,
    rarity_label,
    status_effect_emoji,
    status_effect_label,
    ui_label,
    weapon_emoji,
    weapon_label,
)


def _embed(title: str, desc: str, color=discord.Color.dark_purple()) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=color)


def _int(v: Any) -> int:
    try: return int(v)
    except (TypeError, ValueError): return 0


WEAPONS_PER_PAGE = 15
STATUS_ICON_KEYS = {"bleed", "burn", "poison", "stun", "shield", "heal", "crit"}


def _json_obj(raw: Any, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(str(raw))
    except Exception:
        return fallback


def _weapon_id(weapon: Any) -> str:
    return f"#{_int(row_get(weapon, 'id', 0)):05d}"


def _rarity_badge(rarity: str) -> str:
    emoji = rarity_emoji(rarity)
    if emoji:
        return emoji
    return f"`{rarity[:1].upper()}`" if rarity else "`?`"


def _weapon_icon_stack(weapon: Any) -> str:
    icons: list[str] = []
    rarity = str(row_get(weapon, "rarity", "Common"))
    wtype = str(row_get(weapon, "weapon_type", "sword"))
    for icon in (_rarity_badge(rarity), weapon_emoji(wtype)):
        if icon and icon not in icons:
            icons.append(icon)

    passive = _json_obj(row_get(weapon, "passive"), {})
    if isinstance(passive, dict):
        key = str(passive.get("key", ""))
        if key:
            icon = passive_emoji(key)
            if icon and icon not in icons:
                icons.append(icon)

    affixes = _json_obj(row_get(weapon, "affixes", "[]"), [])
    if isinstance(affixes, list):
        for affix in affixes:
            if not isinstance(affix, dict):
                continue
            key = str(affix.get("stat") or affix.get("key") or "")
            if not key:
                continue
            icon = status_effect_emoji(key) if key in STATUS_ICON_KEYS else asset_emoji("passives", key)
            if icon and icon not in icons:
                icons.append(icon)
            if len(icons) >= 5:
                break
    return " ".join(icons)


def _weapon_list_line(weapon: Any) -> str:
    quality_pct = _int(row_get(weapon, "quality_pct", 50))
    icons = _weapon_icon_stack(weapon)
    name = weapon_display_name(weapon)
    return f"`{_weapon_id(weapon)}` {icons} **{name}** **{quality_pct}%**"


def _weapon_list_embed(display_name: str, avatar_url: str, weapons: list, page: int, total_pages: int) -> discord.Embed:
    start = (page - 1) * WEAPONS_PER_PAGE
    page_weapons = weapons[start:start + WEAPONS_PER_PAGE]
    title_icon = weapon_emoji("dagger") or weapon_emoji("sword")
    title = f"{title_icon} {display_name}'s Weapons" if title_icon else f"{display_name}'s Weapons"
    lines = ["**Weapon Filters:** `None`", "**Sort:** `Weapon ID`", ""]
    lines.extend(_weapon_list_line(weapon) for weapon in page_weapons)
    embed = discord.Embed(title=title, description="\n".join(lines), color=discord.Color.dark_gray())
    embed.set_author(name=display_name, icon_url=avatar_url)
    embed.set_footer(text=f"Page {page}/{total_pages} | {len(weapons)} weapon(s) | b weapons <id> | b salvage <id|rarity|all>")
    return embed


def _weapon_passive_lines(weapon: Any) -> list[str]:
    lines: list[str] = []
    passive = _json_obj(row_get(weapon, "passive"), {})
    if isinstance(passive, dict) and passive.get("key"):
        key = str(passive.get("key", ""))
        name = str(passive.get("name") or key.replace("_", " ").title())
        chance = _int(passive.get("chance", 0))
        desc = str(passive.get("desc") or "This passive can trigger during battle.")
        lines.append(desc)
        lines.append(f"{passive_label(key, name)} - **{chance}%** trigger")
    else:
        lines.append("This weapon has no active ability, but comes with passive stats.")
    return lines


def _weapon_affix_lines(weapon: Any) -> list[str]:
    lines: list[str] = []
    affixes = _json_obj(row_get(weapon, "affixes", "[]"), [])
    if isinstance(affixes, list):
        for affix in affixes:
            if not isinstance(affix, dict):
                continue
            key = str(affix.get("stat") or affix.get("key") or "")
            name = str(affix.get("name") or key.replace("_", " ").title())
            fmt = str(affix.get("fmt") or "").strip()
            if not key or not fmt:
                continue
            if key in STATUS_ICON_KEYS:
                lines.append(f"{status_effect_label(key, name)} - {fmt}")
            else:
                lines.append(f"**{name}** - {fmt}")
    return lines


def _weapon_identity_lines(weapon: Any, owner: discord.abc.User | discord.Member | discord.User, *, include_owner: bool = True) -> list[str]:
    wdisplay = weapon_display_name(weapon)
    wtype = str(row_get(weapon, "weapon_type", "sword"))
    wr = str(row_get(weapon, "rarity", "Common"))
    wear = str(row_get(weapon, "wear", "Unknown"))
    mana_cost = _int(row_get(weapon, "mana_cost", 0))
    quality_pct = _int(row_get(weapon, "quality_pct", 50))
    lines = [f"**Name:** {row_get(weapon, 'name', wdisplay)}"]
    if include_owner:
        lines.append(f"**Owner:** {owner.mention}")
    lines.extend([
        f"**ID:** `{_weapon_id(weapon)}`",
        f"**Sell Value:** {material_label(WEAPON_SHARD_KEY)} **{weapon_salvage_shards(weapon):,}**",
        f"**Quality:** {rarity_label(wr)} **{quality_pct}%**",
        f"**Wear:** `{wear.upper()}`",
        "**Kills:** `0`",
        f"**Weapon Cost:** **{mana_cost}** {asset_emoji('ui', 'mana') or 'Mana'}",
    ])
    return lines


def _weapon_detail_embed(owner: discord.abc.User | discord.Member | discord.User, weapon: Any) -> discord.Embed:
    wtype = str(row_get(weapon, "weapon_type", "sword"))
    wr = str(row_get(weapon, "rarity", "Common"))
    title = f"{_rarity_badge(wr)} {owner.display_name}'s {weapon_display_name(weapon)} [0]"
    rarity = RARITY_BY_NAME.get(wr)
    desc = "\n".join(_weapon_identity_lines(weapon, owner))
    desc += "\n\n__**Description**__\n"
    desc += "\n".join(_weapon_passive_lines(weapon))
    affixes = _weapon_affix_lines(weapon)
    if affixes:
        desc += "\n\n" + "\n\n".join(affixes[:5])
    embed = _embed(title, desc, discord.Color(rarity.color) if rarity else discord.Color.dark_gray())
    embed.set_author(name=owner.display_name, icon_url=owner.display_avatar.url)
    embed.set_footer(text="Reroll Changes: 0 | Reroll Attempts: 0")
    asset_url, _ = embed_asset("weapons", wtype)
    if asset_url:
        embed.set_thumbnail(url=asset_url)
    return embed


def _weapon_snapshot(weapon: Any) -> dict[str, Any]:
    return {
        "name": str(row_get(weapon, "name", "")),
        "weapon_type": str(row_get(weapon, "weapon_type", "sword")),
        "quality": str(row_get(weapon, "quality", "Normal")),
        "quality_pct": _int(row_get(weapon, "quality_pct", 50)),
        "mana_cost": _int(row_get(weapon, "mana_cost", 3)),
        "wear": str(row_get(weapon, "wear", "Unknown")),
        "attack_bonus": _int(row_get(weapon, "attack_bonus", 0)),
        "defense_bonus": _int(row_get(weapon, "defense_bonus", 0)),
        "passive": row_get(weapon, "passive"),
        "affixes": row_get(weapon, "affixes", "[]"),
    }


async def _restore_weapon_snapshot(db, user_id: int, weapon_id: int, snapshot: dict[str, Any]) -> None:
    await db.execute(
        """UPDATE weapons
           SET name = ?, weapon_type = ?, quality = ?, quality_pct = ?, mana_cost = ?, wear = ?,
               attack_bonus = ?, defense_bonus = ?, passive = ?, affixes = ?
           WHERE id = ? AND user_id = ?""",
        (
            snapshot["name"], snapshot["weapon_type"], snapshot["quality"], snapshot["quality_pct"],
            snapshot["mana_cost"], snapshot["wear"], snapshot["attack_bonus"], snapshot["defense_bonus"],
            snapshot["passive"], snapshot["affixes"], weapon_id, user_id,
        ),
    )


def _reroll_weapon_block(label: str, weapon: Any) -> str:
    wdisplay = weapon_display_name(weapon)
    quality_pct = _int(row_get(weapon, "quality_pct", 50))
    wear = str(row_get(weapon, "wear", "Unknown"))
    mana_cost = _int(row_get(weapon, "mana_cost", 3))
    wr = str(row_get(weapon, "rarity", "Common"))
    wtype = str(row_get(weapon, "weapon_type", "sword"))
    header_icons = " ".join(icon for icon in (_rarity_badge(wr), weapon_emoji(wtype)) if icon)
    lines = [
        f"{header_icons} **[{label}] {wdisplay}**",
        "",
        f"**ID:** `{_weapon_id(weapon)}`",
        f"**Quality:** {rarity_label(str(row_get(weapon, 'rarity', 'Common')))} **{quality_pct}%**",
        f"**Wear:** `{wear.upper()}`",
        f"**Weapon Cost:** {mana_cost} {asset_emoji('ui', 'mana') or 'Mana'}",
        "",
        "__**Description**__",
        "\n".join(_weapon_passive_lines(weapon)[:2]),
    ]
    affixes = _weapon_affix_lines(weapon)
    if affixes:
        lines.extend(["", affixes[0]])
    return "\n".join(lines)


def _weapon_reroll_embed(owner: discord.Member | discord.User, before: Any, after: Any, *, cost: int, mode: str, attempts: int, remaining: int) -> discord.Embed:
    wear_before = str(row_get(before, "wear", "Unknown"))
    wear_after = str(row_get(after, "wear", "Unknown"))
    desc = f"**{owner.display_name}** spent **{cost}** {material_label(WEAPON_SHARD_KEY)} to reroll!"
    if wear_before != wear_after:
        desc += f"\n\n⚠️ Your wear will change from `{wear_before}` to `{wear_after}`!"
    desc += "\n\n" + _reroll_weapon_block("CURRENT", before)
    desc += "\n\n" + "─" * 24 + "\n\n"
    desc += _reroll_weapon_block("NEW", after)
    embed = _embed("", desc, discord.Color.dark_gray())
    embed.set_author(name=owner.display_name, icon_url=owner.display_avatar.url)
    embed.set_footer(text=f"Reroll Changes: 0 | Reroll Attempts: {attempts} | Shards left: {remaining:,}")
    return embed


class WeaponRerollView(discord.ui.View):
    def __init__(self, cog: "RPGEquipment", author: discord.Member | discord.User, weapon_id: int, mode: str, before_snapshot: dict[str, Any], before_row: Any, after_row: Any, cost: int, attempts: int, remaining: int) -> None:
        super().__init__(timeout=120)
        self.cog = cog
        self.author = author
        self.weapon_id = weapon_id
        self.mode = mode
        self.before_snapshot = before_snapshot
        self.before_row = before_row
        self.after_row = after_row
        self.cost = cost
        self.attempts = attempts
        self.remaining = remaining

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author.id

    def _disable(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, row=0)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self._disable()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=0)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await _restore_weapon_snapshot(self.cog.bot.db, self.author.id, self.weapon_id, self.before_snapshot)
        await add_item(self.cog.bot.db, self.author.id, "material", WEAPON_SHARD_KEY, self.cost)
        self._disable()
        embed = _embed("Weapon Reroll Cancelled", f"Restored the original weapon and refunded {material_label(WEAPON_SHARD_KEY)} **{self.cost}**.", discord.Color.dark_red())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.primary, row=0)
    async def reroll_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        before = await self.cog.bot.db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (self.weapon_id, self.author.id))
        if before is None:
            await interaction.response.send_message("Weapon not found.", ephemeral=True)
            return
        try:
            cost = weapon_reroll_cost(before, self.mode)
            after = await reroll_weapon(self.cog.bot.db, self.author.id, self.weapon_id, self.mode)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        remaining = await get_quantity(self.cog.bot.db, self.author.id, "material", WEAPON_SHARD_KEY)
        self.before_row = before
        self.after_row = after
        self.cost = cost
        self.attempts += 1
        self.remaining = remaining
        await interaction.response.edit_message(embed=_weapon_reroll_embed(self.author, before, after, cost=cost, mode=self.mode, attempts=self.attempts, remaining=remaining), view=self)


class WeaponPageView(discord.ui.View):
    def __init__(self, author_id: int, display_name: str, avatar_url: str, weps: list, page: int, total_pages: int) -> None:
        super().__init__(timeout=120)
        self.author_id = author_id
        self.display_name = display_name
        self.avatar_url = avatar_url
        self.weps = weps
        self.page = page
        self.total_pages = total_pages
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.page <= 1
        self.next_btn.disabled = self.page >= self.total_pages

    def _render(self):
        return _weapon_list_embed(self.display_name, self.avatar_url, self.weps, self.page, self.total_pages)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(1, self.page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self._render(), view=self)
        return
        file = self._render()
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=self.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_image(url="attachment://abyssia_weapons.png")
        embed.set_footer(text=f"Page {self.page}/{self.total_pages} • Abyssia RPG")
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, row=0)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(self.total_pages, self.page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self._render(), view=self)
        return
        file = self._render()
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=self.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_image(url="attachment://abyssia_weapons.png")
        embed.set_footer(text=f"Page {self.page}/{self.total_pages} • Abyssia RPG")
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id


class RPGEquipment(commands.Cog):
    """Weapon and creature detail commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="weapons", aliases=["weps", "armory"])
    async def weapons(self, ctx: commands.Context, selector: str | None = None) -> None:
        """View your weapon vault, or inspect one weapon by ID."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        if selector and selector.lstrip("#").isdigit():
            weapon_id = int(selector.lstrip("#"))
            row = await self.bot.db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, ctx.author.id))
            if row is not None:
                embed = _weapon_detail_embed(ctx.author, row)
                wtype = str(row_get(row, "weapon_type", "sword"))
                _, asset_file = embed_asset("weapons", wtype)
                if asset_file:
                    await ctx.reply(embed=embed, file=asset_file, mention_author=False)
                else:
                    await ctx.reply(embed=embed, mention_author=False)
                return
        weps = sorted(await player_weapons(self.bot.db, ctx.author.id), key=lambda row: _int(row_get(row, "id", 0)), reverse=True)
        if not weps:
            await ctx.reply(embed=_embed("Weapon Vault", "No weapons yet. Open crates to find them."), mention_author=False)
            return
        total_pages = max(1, (len(weps) + WEAPONS_PER_PAGE - 1) // WEAPONS_PER_PAGE)
        page = 1
        if selector and selector.isdigit():
            page = int(selector)
        page = max(1, min(total_pages, page))
        view = WeaponPageView(ctx.author.id, ctx.author.display_name, ctx.author.display_avatar.url, weps, page, total_pages)
        await ctx.reply(embed=view._render(), view=view, mention_author=False)
        return
        total_pages = max(1, (len(weps) + 3) // 4)
        page = max(1, min(total_pages, page))
        view = WeaponPageView(ctx.author.id, ctx.author.display_name, weps, page, total_pages)
        file = view._render()
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url="attachment://abyssia_weapons.png")
        embed.set_footer(text=f"Page {page}/{total_pages} • Abyssia RPG")
        await ctx.reply(embed=embed, file=file, view=view, mention_author=False)

    @commands.hybrid_command(name="weaponequip", aliases=["wpequip"])
    async def equip(self, ctx: commands.Context, weapon_id: int, *, creature_name: str | None = None) -> None:
        """Equip a weapon to a creature. Leave name blank to unequip."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        rows = await self.bot.db.fetchall(
            "SELECT * FROM weapons WHERE id = ? AND user_id = ?",
            (weapon_id, ctx.author.id),
        )
        if not rows:
            await ctx.reply(embed=_embed("Equip", "Weapon not found."), mention_author=False, ephemeral=True)
            return
        weapon = rows[0]
        wdisplay = weapon_display_name(weapon)
        wtype = str(row_get(weapon, "weapon_type", "sword"))
        wr = str(row_get(weapon, "rarity", "Common"))
        weapon_display = f"{_rarity_badge(wr)} {weapon_label(wtype, wdisplay)}"
        if creature_name is None:
            await unequip_weapon(self.bot.db, weapon_id)
            await ctx.reply(embed=_embed("Equip", f"**{weapon_display}** unequipped."), mention_author=False)
            return
        creatures = await self.bot.db.fetchall(
            "SELECT * FROM rpg_creatures WHERE user_id = ? AND LOWER(name) LIKE ? ORDER BY level DESC",
            (ctx.author.id, f"%{creature_name.lower()}%"),
        )
        if not creatures:
            await ctx.reply(embed=_embed("Equip", f"No creature found matching `{creature_name}`."), mention_author=False, ephemeral=True)
            return
        target = creatures[0]
        old_weapon = await weapon_for_creature(self.bot.db, target["id"])
        if old_weapon:
            await unequip_weapon(self.bot.db, old_weapon["id"])
        await equip_weapon_to_creature(self.bot.db, weapon_id, target["id"])
        await ctx.reply(embed=_embed("Equip", f"**{weapon_display}** -> **{creature_label(str(target['name']), str(target['rarity']))}** Lv.{target['level']}"), mention_author=False)

    @commands.hybrid_command(name="weaponunequip", aliases=["wpunequip", "unwep"])
    async def unequip(self, ctx: commands.Context, weapon_id: int) -> None:
        """Unequip a weapon from its creature."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        rows = await self.bot.db.fetchall(
            "SELECT * FROM weapons WHERE id = ? AND user_id = ?",
            (weapon_id, ctx.author.id),
        )
        if not rows:
            await ctx.reply(embed=_embed("Unequip", "Weapon not found."), mention_author=False, ephemeral=True)
            return
        await unequip_weapon(self.bot.db, weapon_id)
        weapon = rows[0]
        wdisplay = weapon_display_name(weapon)
        wtype = str(row_get(weapon, "weapon_type", "sword"))
        wr = str(row_get(weapon, "rarity", "Common"))
        await ctx.reply(embed=_embed("Unequip", f"**{_rarity_badge(wr)} {weapon_label(wtype, wdisplay)}** returned to vault."), mention_author=False)

    @commands.hybrid_command(name="wdex", aliases=["weaponinfo", "winfo"])
    async def wdex(self, ctx: commands.Context, weapon_id: int) -> None:
        """Inspect a weapon by its ID."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        rows = await self.bot.db.fetchall(
            "SELECT * FROM weapons WHERE id = ? AND user_id = ?",
            (weapon_id, ctx.author.id),
        )
        if not rows:
            await ctx.reply(embed=_embed("Weapon Dex", f"No weapon with ID `{weapon_id}`."), mention_author=False, ephemeral=True)
            return
        w = rows[0]
        embed = _weapon_detail_embed(ctx.author, w)
        wtype = str(row_get(w, "weapon_type", "sword"))
        _, asset_file = embed_asset("weapons", wtype)
        if asset_file:
            await ctx.reply(embed=embed, file=asset_file, mention_author=False)
        else:
            await ctx.reply(embed=embed, mention_author=False)
        return
        ws = weapon_stats(w)
        se = weapon_effects(w)
        wdisplay = weapon_display_name(w)
        wtype = str(row_get(w, "weapon_type", "sword"))
        wq = str(row_get(w, "quality", "Normal"))
        wr = str(row_get(w, "rarity", "Common"))
        quality_pct = _int(row_get(w, "quality_pct", 50))
        mana_cost = _int(row_get(w, "mana_cost", 3))
        wear = str(row_get(w, "wear", "Unknown"))
        atk = ws.get("attack", 0)
        dfn = ws.get("defense", 0)

        equipped = row_get(w, "equipped_creature_id")
        equipped_text = "Vault"
        if equipped:
            cr = await self.bot.db.fetchone("SELECT name, rarity, level FROM rpg_creatures WHERE id = ?", (int(equipped),))
            if cr:
                equipped_text = f"{creature_label(str(cr['name']), str(cr['rarity']))} Lv.{cr['level']}"

        passive_lines: list[str] = []
        passive = _json_obj(row_get(w, "passive"), {})
        if isinstance(passive, dict) and passive.get("key"):
            p_key = str(passive.get("key", ""))
            p_name = str(passive.get("name") or p_key.replace("_", " ").title())
            p_chance = passive.get("chance", 0)
            p_desc = str(passive.get("desc") or "")
            if p_desc:
                passive_lines.append(p_desc)
            passive_lines.append(f"{passive_label(p_key, p_name)} - **{p_chance}%** trigger")
        else:
            passive_lines.append("This weapon has no active ability.")

        affix_lines: list[str] = []
        affixes = _json_obj(row_get(w, "affixes", "[]"), [])
        if isinstance(affixes, list):
            for affix in affixes:
                if not isinstance(affix, dict):
                    continue
                key = str(affix.get("key", ""))
                name = str(affix.get("name") or key.replace("_", " ").title())
                fmt = str(affix.get("fmt") or "").strip()
                if not fmt:
                    continue
                if key in STATUS_ICON_KEYS:
                    affix_lines.append(f"{status_effect_label(key, name)} - {fmt}")
                else:
                    affix_lines.append(f"**{name}** - {fmt}")
        if se:
            for key, value in se.items():
                if not value or key in STATUS_ICON_KEYS:
                    continue
                label = key.replace("_", " ").title()
                affix_lines.append(f"**{label}** - +{value}%")

        rarity = RARITY_BY_NAME.get(wr)
        title = f"{ctx.author.display_name}'s {wdisplay}"
        identity = [
            f"**Name:** {row_get(w, 'name', wdisplay)}",
            f"**Owner:** {ctx.author.mention}",
            f"**ID:** `{_weapon_id(w)}`",
            f"**Sell Value:** {material_label(WEAPON_SHARD_KEY)} **{weapon_salvage_shards(w):,}**",
            f"**Quality:** {rarity_label(wr)} **{quality_pct}%**",
            f"**Wear:** `{wear}`",
            f"**Type:** {weapon_label(wtype)}",
            f"**Weapon Cost:** **{mana_cost}** Mana",
            f"**Equipped:** {equipped_text}",
            f"**Stats:** ATK **+{atk}** | DEF **+{dfn}**",
        ]
        embed = _embed(title, "\n".join(identity), discord.Color(rarity.color) if rarity else discord.Color.dark_gray())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Description", value="\n\n".join(passive_lines[:3]), inline=False)
        if affix_lines:
            embed.add_field(name="Buff Stats", value="\n\n".join(affix_lines[:6]), inline=False)
        embed.set_footer(text=f"Reroll Changes: 0 | Stat Cost: {weapon_reroll_cost(w, 'stat')} shards | Passive Cost: {weapon_reroll_cost(w, 'passive')} shards")
        asset_url, asset_file = embed_asset("weapons", wtype)
        if asset_url:
            embed.set_thumbnail(url=asset_url)
        if asset_file:
            await ctx.reply(embed=embed, file=asset_file, mention_author=False)
        else:
            await ctx.reply(embed=embed, mention_author=False)
        return

        identity = [
            f"**Name:** {wdisplay}",
            f"**Owner:** {ctx.author.mention}",
            f"**ID:** `#{weapon_id}`",
            f"**Sell Value:** {material_label(WEAPON_SHARD_KEY)} **{weapon_salvage_shards(w)}**",
            f"**Quality:** {rarity_label(wr)} **{quality_pct}%** ({wq})",
            f"**Wear:** `{wear}`",
            f"**Type:** {weapon_label(wtype)}",
            f"**Weapon Cost:** Mana **{mana_cost}**",
            f"**Stats:** ATK **+{atk}** | DEF **+{dfn}**",
            f"**Equipped:** {equipped_text}",
        ]

        passive_lines: list[str] = []
        passive_raw = row_get(w, "passive")
        if passive_raw:
            try:
                passive = json.loads(str(passive_raw))
                if isinstance(passive, dict) and passive.get("key"):
                    p_key = str(passive.get("key", ""))
                    p_name = str(passive.get("name", ""))
                    p_chance = passive.get("chance", 0)
                    p_desc = passive.get("desc", "")
                    passive_lines.append(f"{passive_label(p_key, p_name)} - **{p_chance}%** trigger")
                    if p_desc:
                        passive_lines.append(str(p_desc))
            except Exception:
                pass

        affix_lines: list[str] = []
        try:
            affixes = json.loads(str(row_get(w, "affixes", "[]")))
        except Exception:
            affixes = []
        if isinstance(affixes, list):
            for affix in affixes:
                if not isinstance(affix, dict):
                    continue
                key = str(affix.get("key", ""))
                name = str(affix.get("name") or key.replace("_", " ").title())
                fmt = str(affix.get("fmt") or "").strip()
                if not fmt:
                    continue
                if key in {"bleed", "burn", "poison", "stun", "shield", "heal", "crit"}:
                    affix_lines.append(f"{status_effect_label(key, name)} - {fmt}")
                else:
                    affix_lines.append(f"**{name}** - {fmt}")

        if se:
            sparts = [f"{k.replace('_', ' ').title()}: +{v}%" for k, v in se.items() if v and k not in ("bleed", "burn", "poison", "stun", "shield", "heal", "crit")]
            if sparts:
                affix_lines.extend(f"**{part.split(':', 1)[0]}** - {part.split(':', 1)[1].strip()}" for part in sparts[:6])

        rarity = RARITY_BY_NAME.get(wr)
        icon = weapon_emoji(wtype)
        title = f"{icon} {wdisplay}" if icon else wdisplay
        embed = _embed(title, "\n".join(identity), discord.Color(rarity.color) if rarity else discord.Color.default())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(
            name="Description",
            value="\n".join(passive_lines) if passive_lines else "This weapon has no passive ability.",
            inline=False,
        )
        if affix_lines:
            embed.add_field(name="Buff Stats", value="\n".join(affix_lines[:8]), inline=False)
        embed.set_footer(text=f"Reroll Costs: stat {weapon_reroll_cost(w, 'stat')} shards | passive {weapon_reroll_cost(w, 'passive')} shards")

        asset_url, asset_file = embed_asset("weapons", wtype)
        if asset_url:
            embed.set_thumbnail(url=asset_url)
        if asset_file:
            await ctx.reply(embed=embed, file=asset_file, mention_author=False)
        else:
            await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="weaponreroll", aliases=["wreroll", "wrr"])
    async def weapon_reroll(self, ctx: commands.Context, weapon_id: int, mode: str = "stat") -> None:
        """Reroll a weapon using Weapon Shards. Modes: stat, passive, full."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        before = await self.bot.db.fetchone(
            "SELECT * FROM weapons WHERE id = ? AND user_id = ?",
            (weapon_id, ctx.author.id),
        )
        if before is None:
            await ctx.reply(embed=_embed("Weapon Reroll", f"No weapon with ID `{weapon_id}`."), mention_author=False, ephemeral=True)
            return
        try:
            cost = weapon_reroll_cost(before, mode)
            updated = await reroll_weapon(self.bot.db, ctx.author.id, weapon_id, mode)
        except ValueError as exc:
            await ctx.reply(embed=_embed("Weapon Reroll", str(exc)), mention_author=False, ephemeral=True)
            return

        remaining = await get_quantity(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY)
        view = WeaponRerollView(
            self,
            ctx.author,
            weapon_id,
            mode,
            _weapon_snapshot(before),
            before,
            updated,
            cost,
            1,
            remaining,
        )
        await ctx.reply(embed=_weapon_reroll_embed(ctx.author, before, updated, cost=cost, mode=mode, attempts=1, remaining=remaining), view=view, mention_author=False)
        return
        ws = weapon_stats(updated)
        quality_pct = _int(row_get(updated, "quality_pct", 50))
        mana_cost = _int(row_get(updated, "mana_cost", 3))
        wear = str(row_get(updated, "wear", "Unknown"))
        wr = str(row_get(updated, "rarity", "Common"))
        passive_text = "None"
        passive_raw = row_get(updated, "passive")
        if passive_raw:
            try:
                passive = json.loads(str(passive_raw))
                if isinstance(passive, dict) and passive.get("name"):
                    p_key = str(passive.get("key", ""))
                    passive_text = f"{passive_label(p_key, str(passive.get('name')))} {passive.get('chance', 0)}%"
            except Exception:
                pass
        lines = [
            f"Rerolled **{weapon_display_name(updated)}** with {material_label(WEAPON_SHARD_KEY)} **{cost}**.",
            f"Quality **{quality_pct}%** - Mana **{mana_cost}** - Wear **{wear}**",
            f"ATK +{ws.get('attack', 0)} - DEF +{ws.get('defense', 0)}",
            f"Passive: **{passive_text}**",
            f"Shards left: {material_label(WEAPON_SHARD_KEY)} **{remaining}**",
        ]
        rarity = RARITY_BY_NAME.get(wr)
        embed = _embed("Weapon Reroll", "\n".join(lines), discord.Color(rarity.color) if rarity else discord.Color.gold())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="weaponshards", aliases=["wshards", "shards"])
    async def weapon_shards(self, ctx: commands.Context) -> None:
        """Show your Weapon Shard balance."""
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        qty = await get_quantity(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY)
        await ctx.reply(embed=_embed("Weapon Shards", f"You have {material_label(WEAPON_SHARD_KEY)} **{qty}**."), mention_author=False)

    @commands.hybrid_command(name="creature", aliases=["monster", "details"])
    async def creature(self, ctx: commands.Context, *, creature_name: str) -> None:
        """View detailed creature info including equipment."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        creatures = await self.bot.db.fetchall(
            "SELECT * FROM rpg_creatures WHERE user_id = ? AND LOWER(name) LIKE ? ORDER BY rarity DESC, level DESC",
            (ctx.author.id, f"%{creature_name.lower()}%"),
        )
        if not creatures:
            await ctx.reply(embed=_embed("Info", f"No creature: `{creature_name}`."), mention_author=False, ephemeral=True)
            return
        cr = creatures[0]
        weapon = await weapon_for_creature(self.bot.db, cr["id"])
        lines = [
            f"**{creature_label(str(cr['name']), str(cr['rarity']))}** - {rarity_label(str(cr['rarity']))}",
            f"Level {cr['level']}",
            "",
            f"HP {cr['hp']}  •  ATK {cr['attack']}  •  DEF {cr['defense']}  •  SPD {cr['speed']}",
            f"Crit {cr['crit']}%  •  Mana {cr['mana']}  •  {cr['ability']}",
        ]
        if weapon:
            ws = weapon_stats(weapon)
            se = weapon_effects(weapon)
            wq = str(row_get(weapon, "quality", "Normal"))
            wn = str(row_get(weapon, "name", "?"))
            wtype = str(row_get(weapon, "weapon_type", "sword"))
            quality_pct = _int(row_get(weapon, "quality_pct", 50))
            mana_cost = _int(row_get(weapon, "mana_cost", 3))
            wear = str(row_get(weapon, "wear", "Unknown"))
            if wq != "Normal":
                wdisplay = f"{wq} {wn}"
            else:
                wdisplay = wn
            lines.append("")
            lines.append(f"Weapon: **{weapon_label(wtype, wdisplay)}** ({rarity_label(str(weapon['rarity']))})")
            lines.append(f"  Quality {quality_pct}% ({wq}) - Mana {mana_cost} - Wear {wear}")
            parts = []
            for k, v in ws.items():
                if v: parts.append(f"{k.upper()}+{v}")
            if parts: lines.append("  " + "  ".join(parts))
            passive_raw = row_get(weapon, "passive")
            if passive_raw:
                try:
                    passive = json.loads(str(passive_raw))
                    if isinstance(passive, dict) and passive.get("key"):
                        p_key = str(passive.get("key", ""))
                        p_name = passive.get("name", "")
                        p_chance = passive.get("chance", 0)
                        p_desc = passive.get("desc", "")
                        lines.append(f"  {passive_label(p_key, str(p_name))} - {p_chance}% - {p_desc}")
                except Exception:
                    pass
            if se:
                sparts = [f"{k.replace('_', ' ').title()}: +{v}%" for k, v in se.items() if v and k not in ("bleed", "burn", "poison", "stun", "shield", "heal", "crit")]
                if sparts:
                    lines.append("  " + " | ".join(sparts[:4]))
        rarity = RARITY_BY_NAME.get(str(cr["rarity"]))
        embed = _embed(f"Creature: {creature_label(str(cr['name']), str(cr['rarity']))}", "\n".join(lines), discord.Color(rarity.color) if rarity else discord.Color.default())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGEquipment(bot))
