"""Weapon equip/unequip and creature detail commands."""
from __future__ import annotations

import json
from typing import Any, Optional

import discord
from discord.ext import commands

from core.battle_engine import Ability
from core.card_controls import shortcut_view
from core.card_layout import AbyssiaLayoutView
from core.card_ui import run_render
from core.cards import render_weapon_detail_card, render_weapons_card
from core.discord_assets import ensure_application_emojis
from core.rpg import (
    OWO_REROLL_COST,
    add_item,
    ensure_player,
    equip_weapon_to_creature,
    get_quantity,
    owo_reroll_passive,
    owo_reroll_stat,
    player_weapons,
    row_get,
    unequip_weapon,
    WEAPON_QUALITY_RARITY_TIERS,
    weapon_display_name,
    weapon_effects,
    weapon_quality_rarity,
    weapon_for_creature,
    weapon_salvage_shards,
    weapon_stats,
)
from core.rpg_data import RARITY_BY_NAME, WEAPON_AFFIXES, WEAPON_BASE_STATS, WEAPON_PASSIVES, WEAPON_PASSIVE_CHANCE, WEAPON_SHARD_KEY, WEAPON_TYPES, normalize_key
from core.theme import (
    creature_emoji,
    creature_label,
    material_label,
    passive_emoji,
    passive_label,
    rarity_emoji,
    rarity_label,
    stat_emoji,
    weapon_emoji,
    weapon_label,
)


def _embed(title: str, desc: str, color=discord.Color.dark_purple()) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=color)


def _int(v: Any) -> int:
    try: return int(v)
    except (TypeError, ValueError): return 0


def _stat_icon(key: str, fallback: str) -> str:
    return stat_emoji(key) or fallback


WEAPONS_PER_PAGE = 15
WEAPON_CARD_PAGE_SIZE = 5
STATUS_ICON_KEYS = {"bleed", "burn", "poison", "stun", "shield", "heal", "crit"}


PASSIVE_EXACT_EFFECTS: dict[str, str] = {
    "strength": "Increases STR by +{roll}%.",
    "magic": "Increases MAG by +{roll}%.",
    "hp": "Increases max HP by +{roll}%.",
    "wp": "Increases max MANA by +{roll}%.",
    "pr": "Increases DEF by +{roll}%.",
    "mr": "Increases RES by +{roll}%.",
    "thorns": "Reflects {roll}% of incoming damage as true damage.",
    "safeguard": "Reduces heavy hits above 20% max HP by {roll}%.",
    "regeneration": "Restores {roll}% max HP after each turn.",
    "adaptation": "After being hit, adds value/1000 to DEF and RES.",
    "sacrifice": "On death, living allies gain {roll}% of this creature's max HP and max MANA.",
    "bleed": "On hit chance to apply Bleed. Bleed deals 2.5% max HP per stack each turn.",
    "burn": "On hit chance to apply Burn. Burn deals 3.0% max HP per stack each turn.",
    "poison": "On hit chance to apply Poison. Poison deals 2.2% max HP per stack each turn.",
    "stun": "On hit chance to Stun. Stun skips the target's next action.",
    "shield": "On hit chance to gain Shield. Shield reduces incoming damage by 30% for 2 turns.",
    "heal": "After dealing damage, heals for {roll}% of damage dealt.",
    "crit": "Increases crit chance by +{crit_chance}% and crit damage by +{crit_dmg}%.",
    "life_steal": "Heals for {roll}% of damage dealt.",
    "mana_tap": "Restores MANA equal to {roll}% of damage dealt.",
    "soul_gain": "Increases souls gained by +{roll}%.",
    "gem_finder": "Increases infused gem find chance by +{roll}%.",
    "xp_boost": "Increases battle XP by +{roll}%.",
    "rare_finder": "Increases rare find chance by +{roll}%.",
    "energize": "Restores {roll} MANA after each turn.",
    "fear": "On hit chance to apply Fear, reducing target damage by 25%.",
}


AFFIX_EXACT_EFFECTS: dict[str, str] = {
    "strength": "Final STR percent bonus.",
    "magic": "Final MAG percent bonus.",
    "hp": "Max HP percent bonus.",
    "wp": "Max MANA percent bonus.",
    "pr": "Physical resistance bonus toward the 80% cap.",
    "mr": "Magical resistance bonus toward the 80% cap.",
    "thorns": "Reflects incoming damage by this percent, capped at 30%.",
    "regeneration": "Turn-start healing. Value 10 means 1.0% max HP.",
    "safeguard": "Reduces heavy hits above 20% max HP by this percent.",
    "adaptation": "After being hit, adds value/1000 to DEF and RES.",
    "crit": "Adds crit chance percentage points.",
    "life_steal": "Heals for this percent of damage dealt, capped at 35% in battle.",
    "bleed": "On-hit Bleed chance. Bleed deals 2.5% max HP per stack each turn.",
    "burn": "On-hit Burn chance. Burn deals 3.0% max HP per stack each turn.",
    "poison": "On-hit Poison chance. Poison deals 2.2% max HP per stack each turn.",
    "stun": "On-hit Stun chance. Stun skips the target's next action.",
    "shield": "On-hit Shield chance. Shield reduces incoming damage by 30% for 2 turns.",
        "attack_pct": "Legacy STR percent boost; now treated as STR% in battle.",
        "defense_pct": "Legacy DEF percent boost; now treated as DEF% in battle.",
        "attack_flat": "Legacy flat STR boost.",
        "defense_flat": "Legacy flat DEF boost.",
    "soul_gain": "Soul reward modifier outside direct battle damage.",
    "gem_finder": "Gem reward modifier outside direct battle damage.",
    "xp_boost": "XP reward modifier outside direct battle damage.",
    "rare_finder": "Rare-find modifier outside direct battle damage.",
}


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


def _weapon_quality_pct(weapon: Any) -> int:
    return max(0, min(150, _int(row_get(weapon, "quality_pct", 50))))


def _weapon_tier(weapon: Any) -> str:
    return weapon_quality_rarity(_weapon_quality_pct(weapon))


def _weapon_quality_label(weapon: Any) -> str:
    quality_pct = _weapon_quality_pct(weapon)
    tier = _weapon_tier(weapon)
    return f"{_rarity_badge(tier)} **{quality_pct}%** ({tier})"


def _weapon_icon_stack(weapon: Any) -> str:
    icons: list[str] = []
    wtype = str(row_get(weapon, "weapon_type", "sword"))
    wemoji = weapon_emoji(wtype)
    if wemoji:
        icons.append(wemoji)

    if _int(row_get(weapon, "is_favorite", 0)):
        icons.append("\u2B50")

    return " ".join(icons)


def _weapon_list_line(weapon: Any, creature_name: str | None = None, creature_emoji_str: str | None = None) -> str:
    quality_pct = _weapon_quality_pct(weapon)
    tier = _weapon_tier(weapon)
    tier_badge = _rarity_badge(tier)
    icons = _weapon_icon_stack(weapon)
    name = weapon_display_name(weapon)
    prefix = f"{creature_emoji_str} → " if creature_emoji_str else ""
    return f"{prefix}`{_weapon_id(weapon)}` {tier_badge} {icons} **{name}** **{quality_pct}%**"


def _weapon_passive_label_short(weapon: Any) -> str:
    passive = _json_obj(row_get(weapon, "passive"), {})
    if not isinstance(passive, dict) or not passive.get("key"):
        return "`No passive`"
    key = str(passive.get("key", ""))
    emoji = passive_emoji(key)
    chance = _int(passive.get("chance", 0))
    chance_str = f" `{chance}%`" if chance > 0 else ""
    return f"{emoji}{chance_str}" if emoji else f"`{key}`{chance_str}"


def _weapon_card_page_weapons(weapons: list, page: int) -> list:
    start = (max(1, page) - 1) * WEAPON_CARD_PAGE_SIZE
    return list(weapons or [])[start:start + WEAPON_CARD_PAGE_SIZE]


def _weapon_vault_summary_lines(
    weapons: list,
    page: int,
    *,
    creature_map: dict[int, tuple[str, str]] | None = None,
) -> list[str]:
    lines: list[str] = []
    for idx, weapon in enumerate(_weapon_card_page_weapons(weapons, page)):
        wtype = str(row_get(weapon, "weapon_type", "sword"))
        type_data = WEAPON_TYPES.get(wtype, {})
        type_name = str(type_data.get("name", wtype.replace("_", " ").title()))
        icons = _weapon_icon_stack(weapon)
        rarity = _weapon_tier(weapon)
        name = weapon_display_name(weapon)
        passive = _weapon_passive_label_short(weapon)
        quality_pct = _weapon_quality_pct(weapon)
        equipped_text = ""
        equipped_id = _int(row_get(weapon, "equipped_creature_id", 0))
        if creature_map and equipped_id in creature_map:
            cname, crarity = creature_map[equipped_id]
            equipped_text = f" -> {creature_emoji(cname, crarity)}"
        featured = "**Featured** " if idx == 0 else ""
        lines.append(
            f"{featured}`{_weapon_id(weapon)}` {_rarity_badge(rarity)} {icons} "
            f"**{name}** `{quality_pct}%` - {passive}{equipped_text}"
        )
    if not lines:
        lines.append("No weapons match these filters.")
    return lines


def _weapon_filter_text(type_filter: str, tier_filter: str, *, fav_only: bool = False, sort_filter: str = "quality") -> str:
    type_text = "All Types"
    if type_filter != "all":
        type_data = WEAPON_TYPES.get(type_filter, {})
        type_text = str(type_data.get("name", type_filter.replace("_", " ").title()))
    tier_text = "All Tiers" if tier_filter == "all" else tier_filter
    sort_text = "Recently Added" if sort_filter == "recent" else "Best Quality"
    parts = [f"Type `{type_text}`", f"Tier `{tier_text}`", f"Sort `{sort_text}`"]
    if fav_only:
        parts.append("\u2B50 Favorites")
    return " | ".join(parts)


def _weapon_list_embed(display_name: str, avatar_url: str, weapons: list, page: int, total_pages: int, *, type_filter: str = "all", tier_filter: str = "all", fav_only: bool = False, creature_map: dict[int, tuple[str, str]] | None = None) -> discord.Embed:
    start = (page - 1) * WEAPONS_PER_PAGE
    page_weapons = weapons[start:start + WEAPONS_PER_PAGE]
    title_icon = weapon_emoji("dagger") or weapon_emoji("sword")
    title = f"{title_icon} {display_name}'s Weapons" if title_icon else f"{display_name}'s Weapons"
    lines = [f"**Weapon Filters:** {_weapon_filter_text(type_filter, tier_filter, fav_only=fav_only)}", "**Sort:** `Quality, newest`", ""]
    if page_weapons:
        for weapon in page_weapons:
            wid = _int(row_get(weapon, "equipped_creature_id"))
            if creature_map and wid and wid in creature_map:
                cname, cr = creature_map[wid]
                cemoji = creature_emoji(cname, cr)
            else:
                cemoji = None
            lines.append(_weapon_list_line(weapon, creature_emoji_str=cemoji))
    else:
        lines.append("No weapons match these filters.")
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
        roll = min(100, _int(passive.get("roll", 50)))
        chance = _int(passive.get("chance", 0))
        desc = str(passive.get("desc") or "This passive can trigger during battle.")
        lines.append(desc)
        lines.append(f"{passive_label(key, name, roll)}")
        if chance > 0:
            lines.append(f"  Trigger: {chance}%")
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
            lines.append(f"**{name}** - {fmt}")
    return lines


def _range_text(values: object) -> str:
    try:
        lo, hi = values  # type: ignore[misc]
        return f"{int(lo)}-{int(hi)}"
    except Exception:
        return "0-0"


def _mult_text(lo: float, hi: float) -> str:
    return f"{lo * 100:.0f}-{hi * 100:.0f}%"


def _weapon_type_lines(key: str) -> list[str]:
    data = WEAPON_TYPES[key]
    ability = Ability.for_weapon_type(key)
    passive_slots = 0 if key == "rune" else (2 if key == "orb" else 1)
    _STAT_LABELS = {
        "str_stat": "STR", "pr_stat": "DEF", "hp": "HP",
        "wp_stat": "MANA", "mag_stat": "MAG", "mr_stat": "RES", "spd": "SPD",
    }
    allowed = WEAPON_BASE_STATS.get(key, [])
    stat_ranges = []
    atk_min, atk_max = data.get("atk_range", (0, 0))
    def_min, def_max = data.get("def_range", (0, 0))
    for s in allowed:
        label = _STAT_LABELS.get(s, s.upper())
        if s in ("str_stat", "mag_stat"):
            stat_ranges.append(f"{label} `{atk_min}-{atk_max}`")
        else:
            stat_ranges.append(f"{label} `{def_min}-{def_max}`")
    base_text = " | ".join(stat_ranges) if stat_ranges else "None"
    lines = [
        f"**Type:** {weapon_label(key, str(data.get('name', key.title())))}",
        f"**Base Stat Rolls:** {base_text}",
        f"**Scaling:** `{ability.scale_stat}` | **Damage Type:** `{ability.damage_type}` | **Passive Slots:** `{passive_slots}`",
        f"**MANA Cost:** `{ability.wp_cost_min}-{ability.wp_cost_max}`",
    ]
    if ability.mode == "purity":
        lines.append("**Active:** remove enemy oldest buff, deal `50-100% MAG` magical damage; remove ally oldest debuff, heal `50-100% STR`.")
    elif ability.mode == "heal":
        lines.append(f"**Active:** heal weakest damaged ally for `{_mult_text(ability.multiplier_min, ability.multiplier_max)}` MAG; if no ally is damaged, deal MAG magical damage.")
    elif ability.mode == "guard":
        lines.append(f"**Active:** deal `{_mult_text(ability.multiplier_min, ability.multiplier_max)}` HP true damage, gain Shield, and taunt for the turn.")
    else:
        lines.append(f"**Active:** deal `{_mult_text(ability.multiplier_min, ability.multiplier_max)}` {ability.scale_stat} {ability.damage_type} damage.")
    pool = [str(item) for item in data.get("passive_pool", [])]
    lines.append("**Passive Pool:** " + (", ".join(pool) if pool else "None"))
    return lines


def format_passive_description(key: str, roll: int, *, index_mode: bool = False) -> str:
    """Format passive description with actual numbers or ranges.
    
    Args:
        key: Passive key (e.g., "strength", "crit")
        roll: The actual roll value (0-100) for this weapon instance
        index_mode: If True, show ranges for index/base info. If False, show actual numbers.
    """
    if index_mode:
        roll_range = WEAPON_PASSIVE_CHANCE.get(key, {"min": 0, "max": 0})
        roll_min = int(roll_range.get("min", 0))
        roll_max = int(roll_range.get("max", 0))
        roll_text = f"{roll_min}-{roll_max}"
    else:
        effective = min(100, roll)
        roll_min = roll_max = effective
        roll_text = str(effective)

    if key == "strength":
        return f"Increases STR by +{roll_text}%."
    elif key == "magic":
        return f"Increases MAG by +{roll_text}%."
    elif key == "hp":
        return f"Increases max HP by +{roll_text}%."
    elif key == "wp":
        return f"Increases max MANA by +{roll_text}%."
    elif key == "pr":
        return f"Increases DEF by +{roll_text}%."
    elif key == "mr":
        return f"Increases RES by +{roll_text}%."
    elif key == "thorns":
        return f"Reflects {roll_text}% of incoming damage as true damage."
    elif key == "safeguard":
        return f"Reduces heavy hits above 20% max HP by {roll_text}%."
    elif key == "regeneration":
        return f"Restores {roll_text}% max HP at the end of each turn."
    elif key == "adaptation":
        if index_mode:
            return f"After being hit, gains +{roll_min/1000:.3f}-{roll_max/1000:.3f} DEF and RES."
        return f"After being hit, gains +{roll_min/1000:.3f} DEF and RES."
    elif key == "sacrifice":
        return f"On death, living allies gain {roll_text}% of this creature's max HP and MANA."
    elif key == "bleed":
        return f"On hit, applies Bleed (2.5% max HP per stack each turn for 3 turns)."
    elif key == "burn":
        return f"On hit, applies Burn (3.0% max HP per stack each turn for 3 turns)."
    elif key == "poison":
        return f"On hit, applies Poison (2.2% max HP per stack each turn for 3 turns)."
    elif key == "stun":
        return f"On hit, applies Stun (target skips next action)."
    elif key == "shield":
        return f"On hit, gains Shield (reduces damage by 30% for 2 turns)."
    elif key == "heal":
        return f"Heals for {roll_text}% of damage dealt."
    elif key == "crit":
        if index_mode:
            return f"Increases crit chance by +{roll_min / 10.0:.1f}-{roll_max / 10.0:.1f}% and crit damage by +{roll_min / 5.0:.1f}-{roll_max / 5.0:.1f}%."
        crit_chance = roll_min / 10.0
        crit_dmg = roll_min / 5.0
        return f"Increases crit chance by +{crit_chance:.1f}% and crit damage by +{crit_dmg:.1f}%."
    elif key == "life_steal":
        return f"Heals for {roll_text}% of damage dealt."
    elif key == "mana_tap":
        return f"Restores MANA equal to {roll_text}% of damage dealt."
    elif key == "soul_gain":
        return f"Increases souls gained after battle by +{roll_text}%."
    elif key == "gem_finder":
        return f"Increases infused gem find chance by +{roll_text}%."
    elif key == "xp_boost":
        return f"Increases battle XP gained by +{roll_text}%."
    elif key == "rare_finder":
        return f"Increases rare creature and loot odds by +{roll_text}%."
    elif key == "energize":
        return f"Restores {roll_text} MANA after each turn."
    elif key == "fear":
        return f"On hit, applies Fear (reduces target damage by 25% for 2 turns)."
    else:
        return f"Passive effect ({roll_text}%)."


def _get_ability_param(stat_rolls: dict, param_key: str, min_val: float, max_val: float) -> float:
    """Derive an ability parameter from stat_rolls deterministically."""
    if not stat_rolls:
        return (min_val + max_val) / 2
    
    base_roll = stat_rolls.get("active", 50)
    wp_roll = stat_rolls.get("wp_cost", 50)
    key_hash = sum(ord(c) for c in param_key) % 100
    
    combined = (base_roll * 0.5 + wp_roll * 0.3 + key_hash * 0.2)
    combined = max(0, min(100, combined))
    
    return min_val + (max_val - min_val) * combined / 100.0


def _format_active_ability(wtype: str, stat_rolls: dict, ability) -> list[str]:
    """Format active ability description with actual rolled values."""
    lines = []
    
    if not stat_rolls:
        lines.append(f"**Active:** deal `{ability.multiplier_min*100:.0f}-{ability.multiplier_max*100:.0f}%` {ability.scale_stat} {ability.damage_type} damage")
        return lines
    
    active_roll = stat_rolls.get("active", 50)
    actual_mult = ability.multiplier_min + (ability.multiplier_max - ability.multiplier_min) * active_roll / 100.0
    wp_roll = stat_rolls.get("wp_cost", 50)
    actual_wp = round(ability.wp_cost_max - (ability.wp_cost_max - ability.wp_cost_min) * wp_roll / 100.0)
    
    mode = ability.mode
    
    if mode == "heal":
        lines.append(f"**Active: Void Resonance**")
        lines.append(f"Heals weakest damaged ally for `{actual_mult*100:.0f}%` MAG.")
        lines.append(f"If no ally is damaged, deals MAG magic damage instead.")
    elif mode in ("passive_only", "rune_empowerment"):
        if mode == "rune_empowerment":
            lines.append(f"**Passive:** Basic attacks become hybrid true damage (60% STR + 60% MAG)")
    elif mode == "execute":
        lines.append(f"**Active: Gravecut**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` STR physical damage.")
        bonus = _get_ability_param(stat_rolls, "execute_bonus", 15, 35)
        lines.append(f"If target is below 35% HP, deals +`{bonus:.0f}%` bonus damage.")
    elif mode == "double_strike":
        lines.append(f"**Active: Black Arrow**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` STR physical damage.")
        chance = _get_ability_param(stat_rolls, "double_chance", 20, 40)
        second_hit = _get_ability_param(stat_rolls, "second_hit", 35, 55)
        lines.append(f"If faster than target, `{chance:.0f}%` chance to strike again for `{second_hit:.0f}%` damage.")
    elif mode == "cleave":
        lines.append(f"**Active: Butcher Sweep**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` STR physical damage to ALL enemies.")
        bonus = _get_ability_param(stat_rolls, "cleave_bonus", 20, 45)
        lines.append(f"Bleeding enemies take +`{bonus:.0f}%` bonus damage.")
    elif mode == "bleed_apply":
        lines.append(f"**Active: Vein Pierce**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` STR physical damage.")
        lines.append(f"Applies Bleed for 3 turns (2.5% max HP per stack).")
        lines.append(f"If target is already bleeding, refreshes and triggers instant tick.")
    elif mode == "charge":
        lines.append(f"**Active: Coffin Nail**")
        lines.append(f"2-turn charge attack.")
        lines.append(f"Turn 1: Load Heavy Bolt (0 MANA)")
        lines.append(f"Turn 2: Fire for `{actual_mult*100:.0f}%` STR + Exposed debuff.")
    elif mode == "burn_detonate":
        lines.append(f"**Active: Witchflame**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` MAG magic damage.")
        lines.append(f"Applies Burn for 3 turns (3.0% max HP per stack).")
        detonate = _get_ability_param(stat_rolls, "detonate", 90, 130)
        lines.append(f"If target is already burning, detonates for +`{detonate:.0f}%` MAG bonus damage.")
    elif mode == "cleanse_ward":
        lines.append(f"**Active: Black Benediction**")
        lines.append(f"Removes 1 debuff from target ally.")
        lines.append(f"Heals ally for `{actual_mult*100:.0f}%` MAG.")
        lines.append(f"Applies Sacred Ward for 2 turns.")
    elif mode == "taunt_shield":
        lines.append(f"**Active: Oath of the Last Wall**")
        lines.append(f"Applies Taunt for 2 turns.")
        phys_reduce = _get_ability_param(stat_rolls, "taunt_phys", 20, 45)
        mag_reduce = _get_ability_param(stat_rolls, "taunt_mag", 10, 30)
        lines.append(f"While taunting: -`{phys_reduce:.0f}%` physical damage, -`{mag_reduce:.0f}%` magic damage.")
        shield_pct = _get_ability_param(stat_rolls, "taunt_shield", 50, 100)
        lines.append(f"If below 40% HP, gains Shield equal to `{shield_pct:.0f}%` DEF.")
    elif mode == "stagger_stun":
        lines.append(f"**Active: Bellringer**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` STR physical damage.")
        lines.append(f"Applies Stagger.")
        lines.append(f"If target already has Stagger, consumes it to apply Stun for 1 turn.")
    elif mode == "mortality":
        lines.append(f"**Active: Mortal Harvest**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` STR physical damage.")
        mortality = _get_ability_param(stat_rolls, "mortality", 45, 75)
        lines.append(f"Applies Mortality for 2 turns (-`{mortality:.0f}%` healing received).")
        hp_heal = _get_ability_param(stat_rolls, "mortality_hp", 10, 25)
        wp_heal = _get_ability_param(stat_rolls, "mortality_wp", 10, 25)
        lines.append(f"On kill: heal `{hp_heal:.0f}%` max HP and restore `{wp_heal:.0f}%` max MANA.")
    elif mode == "tether":
        lines.append(f"**Active: Thorn Tether**")
        lines.append(f"Links user to all allies for 2 turns.")
        absorb = _get_ability_param(stat_rolls, "tether_absorb", 25, 50)
        lines.append(f"User absorbs `{absorb:.0f}%` of damage allies would take.")
        death_dmg = _get_ability_param(stat_rolls, "tether_death", 20, 40)
        lines.append(f"If user dies while tethered, all enemies take `{death_dmg:.0f}%` user max HP true damage.")
    elif mode == "poison_spread":
        lines.append(f"**Active: Rotten Communion**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` MAG magic damage.")
        lines.append(f"Applies Poison for 3 turns (2.2% max HP per stack).")
        lines.append(f"If poisoned target dies, Poison spreads to random enemy.")
    elif mode == "team_buff":
        lines.append(f"**Active: War Under No Dawn**")
        buff1 = _get_ability_param(stat_rolls, "team_buff1", 15, 25)
        lines.append(f"All allies gain +`{buff1:.0f}%` damage for 2 turns.")
        lines.append(f"Can escalate to +25-35% or +40-50% with consecutive casts.")
    elif mode == "force_attack":
        lines.append(f"**Active: Witness Madness**")
        lines.append(f"Costs 10-20% max HP instead of MANA.")
        effectiveness = _get_ability_param(stat_rolls, "force_effectiveness", 35, 55)
        lines.append(f"Forces random enemy to attack ally at `{effectiveness:.0f}%` effectiveness.")
        solo_dmg = _get_ability_param(stat_rolls, "force_solo", 150, 210)
        lines.append(f"If only one enemy remains, deals `{solo_dmg:.0f}%` MAG magic damage instead.")
    elif mode == "stack_consumption":
        lines.append(f"**Active: Sin and Sentence**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` STR/MAG damage.")
        lines.append(f"Gains Sin stacks when allies deal damage.")
        lines.append(f"Gains Virtue stacks when allies heal or restore MANA.")
        lines.append(f"Consumes all stacks for bonus damage on use.")
    elif mode == "mana_drain":
        lines.append(f"**Active: Light That Starves**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` MAG magic damage.")
        steal = _get_ability_param(stat_rolls, "mana_steal", 15, 35)
        lines.append(f"Steals `{steal:.0f}%` of target's current MANA.")
        bonus = _get_ability_param(stat_rolls, "low_mana_bonus", 50, 90)
        lines.append(f"If target is below 20% MANA, deals +`{bonus:.0f}%` bonus damage.")
    elif mode == "reflect_debuff":
        lines.append(f"**Active: Reflected Curse**")
        lines.append(f"Applies Mirror Ward for 2 turns.")
        reflect = _get_ability_param(stat_rolls, "reflect_effectiveness", 60, 100)
        lines.append(f"First debuff is reflected at `{reflect:.0f}%` effectiveness.")
        mana_restore = _get_ability_param(stat_rolls, "reflect_mana", 10, 25)
        lines.append(f"On reflect, restores `{mana_restore:.0f}%` max MANA.")
        heal = _get_ability_param(stat_rolls, "reflect_heal", 50, 90)
        lines.append(f"If no debuff reflected, heals for `{heal:.0f}%` RES.")
    elif mode == "doom_bell":
        lines.append(f"**Active: Toll the End**")
        lines.append(f"Deals `{actual_mult*100:.0f}%` STR physical damage.")
        lines.append(f"Applies Doom Bell for 3 turns.")
        doom_pct = _get_ability_param(stat_rolls, "doom_pct", 12, 25)
        lines.append(f"On expiry, target takes true damage equal to `{doom_pct:.0f}%` of missing HP.")
        lines.append(f"If target dies early, bell jumps to another enemy.")
    else:
        lines.append(f"**Active:** deal `{actual_mult*100:.0f}%` {ability.scale_stat} {ability.damage_type} damage")
    
    if ability.status and mode not in ("bleed_apply", "burn_detonate", "poison_spread", "stagger_stun"):
        lines[-1] += f" +`{ability.status.upper()}`"
    
    if mode not in ("passive_only", "rune_empowerment"):
        if actual_wp > 0:
            lines.append(f"**MANA Cost:** `{actual_wp}`")
    
    return lines


def _passive_index_lines() -> list[str]:
    lines: list[str] = []
    for key, data in WEAPON_PASSIVES.items():
        icon = passive_label(key, str(data.get("name", key.title())), show_rarity=False)
        effect = format_passive_description(key, 0, index_mode=True)
        lines.append(f"{icon} - {effect}")
    return lines


def _affix_index_lines() -> list[str]:
    lines: list[str] = []
    for key, data in WEAPON_AFFIXES.items():
        name = str(data.get("name", key.replace("_", " ").title()))
        effect = AFFIX_EXACT_EFFECTS.get(key, str(data.get("fmt", "")))
        lines.append(f"**{name}** `{data['min']}-{data['max']}` - {effect}")
    return lines


def _chunk_lines(lines: list[str], *, limit: int = 950) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in lines:
        candidate = f"{current}\n{line}".strip()
        if len(candidate) > limit and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _weapon_index_embeds() -> list[discord.Embed]:
    weapon_lines: list[str] = []
    for key in WEAPON_TYPES:
        data = WEAPON_TYPES[key]
        ability = Ability.for_weapon_type(key)
        weapon_lines.append(
            f"{weapon_label(key, str(data.get('name', key.title())))} - STR `{_range_text(data.get('atk_range', (0, 0)))}` "
            f"DEF `{_range_text(data.get('def_range', (0, 0)))}` MANA `{ability.wp_cost_min}-{ability.wp_cost_max}` "
            f"Scale `{ability.scale_stat}` `{_mult_text(ability.multiplier_min, ability.multiplier_max)}`"
        )
    base_embed = _embed("Weapon Dex - Base Weapons", "\n".join(weapon_lines), discord.Color.dark_gray())
    tier_lines = []
    for low, high, rarity in WEAPON_QUALITY_RARITY_TIERS:
        range_text = f"{low}%" if low == high else f"{low}-{high}%"
        tier_lines.append(f"**{rarity}** - `{range_text}` quality")
    base_embed.add_field(name="Quality Tiers", value="\n".join(tier_lines), inline=False)
    embeds = [base_embed]
    passive_embed = _embed("Weapon Dex - Passives", "", discord.Color.dark_gray())
    for idx, chunk in enumerate(_chunk_lines(_passive_index_lines()), start=1):
        passive_embed.add_field(name=f"Passives {idx}", value=chunk, inline=False)
    embeds.append(passive_embed)
    affix_embed = _embed("Weapon Dex - Affixes", "", discord.Color.dark_gray())
    for idx, chunk in enumerate(_chunk_lines(_affix_index_lines()), start=1):
        affix_embed.add_field(name=f"Affixes {idx}", value=chunk, inline=False)
    embeds.append(affix_embed)
    return embeds


def _sections_from_embeds(embeds: list[discord.Embed]) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    for embed in embeds:
        title = str(embed.title or "Info")
        desc = str(embed.description or "").strip()
        if desc:
            sections.append((title, desc[:3900]))
        for field in embed.fields:
            sections.append((str(field.name), str(field.value)[:3900]))
    return sections


def _weapon_type_sections(matched_key: str) -> list[tuple[str, str]]:
    data = WEAPON_TYPES[matched_key]
    passive_lines = [
        (
            f"{passive_label(key, str(WEAPON_PASSIVES[key]['name']), show_rarity=False)} "
            f"`{WEAPON_PASSIVE_CHANCE.get(key, {'min': 0, 'max': 0})['min']}-"
            f"{WEAPON_PASSIVE_CHANCE.get(key, {'min': 0, 'max': 0})['max']}` - "
            f"{format_passive_description(key, 0, index_mode=True)}"
        )
        for key in data.get("passive_pool", [])
    ]
    return [
        ("Weapon Type", "\n".join(_weapon_type_lines(matched_key))),
        ("Passive Pool", "\n".join(passive_lines) or "None"),
    ]


def _weapon_identity_lines(weapon: Any, owner: discord.abc.User | discord.Member | discord.User, *, include_owner: bool = True) -> list[str]:
    wdisplay = weapon_display_name(weapon)
    wtype = str(row_get(weapon, "weapon_type", "sword"))
    type_data = WEAPON_TYPES.get(wtype, {})
    type_name = str(type_data.get("name", wtype.replace("_", " ").title()))
    wear = str(row_get(weapon, "wear", "Unknown"))
    lines = [f"**Name:** {wdisplay}", f"**Type:** {weapon_label(wtype, type_name)}"]
    if include_owner:
        lines.append(f"**Owner:** {owner.mention}")
    lines.extend([
        f"**ID:** `{_weapon_id(weapon)}`",
        f"**Sell Value:** {material_label(WEAPON_SHARD_KEY)} **{weapon_salvage_shards(weapon):,}**",
        f"**Quality:** {_weapon_quality_label(weapon)}",
        f"**Wear:** `{wear.upper()}`",
        "**Kills:** `0`",
    ])
    return lines


def _weapon_desc_text(weapon: Any, owner: discord.abc.User | discord.Member | discord.User) -> str:
    """Build the full weapon description text (same format as _weapon_detail_embed description)."""
    wtype = str(row_get(weapon, "weapon_type", "sword"))
    quality_pct = _weapon_quality_pct(weapon)
    quality_tier = _weapon_tier(weapon)
    ability = Ability.for_weapon_type(wtype)

    desc = "\n".join(_weapon_identity_lines(weapon, owner))

    stat_rolls_raw = row_get(weapon, "stat_rolls", "")
    stat_rolls: dict = {}
    if stat_rolls_raw:
        try:
            stat_rolls = json.loads(str(stat_rolls_raw)) if isinstance(stat_rolls_raw, str) else stat_rolls_raw
        except (json.JSONDecodeError, TypeError):
            pass

    ws = weapon_stats(weapon)
    stat_parts = []
    labels = [
        ("str_stat", "str"), ("pr_stat", "def"), ("hp", "hp"),
        ("wp_stat", "mana"), ("mag_stat", "mag"), ("mr_stat", "res"),
    ]
    label_names = {"str_stat": "STR", "pr_stat": "DEF", "hp": "HP", "wp_stat": "MANA", "mag_stat": "MAG", "mr_stat": "RES"}
    for key, icon_key in labels:
        val = ws.get(key, 0)
        if val:
            stat_parts.append(f"{_stat_icon(icon_key, label_names[key])} `+{val}`")
    if stat_parts:
        mid = len(stat_parts) // 2
        stats = [" ".join(stat_parts[:mid]), " ".join(stat_parts[mid:])]
    else:
        stats = ["*(no base stats)*"]
    
    # Use _format_active_ability to show actual rolled values
    active_lines = _format_active_ability(wtype, stat_rolls, ability)
    
    if ability.mode not in ("passive_only", "rune_empowerment"):
        stats.append(f"**Quality:** {_rarity_badge(quality_tier)} `{quality_pct}%` ({quality_tier})")
    
    # Build description with active section in blockquote
    desc += "\n\n__**Stats**__\n" + "\n".join("> " + s for s in stats)
    
    # Add active ability in its own blockquote section
    if active_lines:
        desc += "\n\n" + "\n".join("> " + line for line in active_lines)

    # Passive section
    passive = _json_obj(row_get(weapon, "passive"), {})
    if isinstance(passive, dict) and passive.get("key"):
        key = str(passive.get("key", ""))
        name = str(passive.get("name") or key.replace("_", " ").title())
        roll = passive.get("roll", 50)
        roll = min(100, _int(roll) if roll else 50)
        p_chance = _int(passive.get("chance", 0))
        effect = format_passive_description(key, roll, index_mode=False)
        desc += f"\n\n__**Passive: {passive_label(key, name, roll)}**__\n> {effect}"
        if p_chance > 0:
            desc += f"\n> Trigger: {p_chance}%"
    else:
        desc += "\n\n__**Passive**__\n> None"

    # Affixes section
    affixes = _weapon_affix_lines(weapon)
    if affixes:
        desc += f"\n\n__**Affixes ({len(affixes)})**__\n" + "\n".join("> " + a for a in affixes)

    return desc


async def _weapon_detail_embed(owner: discord.abc.User | discord.Member | discord.User, weapon: Any) -> tuple[discord.Embed, discord.File | None]:
    wr = _weapon_tier(weapon)
    title = f"{owner.display_name}'s {weapon_display_name(weapon)} [0]"
    rarity = RARITY_BY_NAME.get(wr)

    embed = _embed(title, _weapon_desc_text(weapon, owner), discord.Color(rarity.color) if rarity else discord.Color.dark_gray())
    embed.set_author(name=owner.display_name, icon_url=owner.display_avatar.url)
    embed.set_footer(text="Reroll Changes: 0 | Reroll Attempts: 0")
    card_file = discord.File(await run_render(render_weapon_detail_card, owner.display_name, weapon), filename="abyssia_weapon_detail.png")
    embed.set_image(url="attachment://abyssia_weapon_detail.png")
    return embed, card_file


def _weapon_snapshot(weapon: Any) -> dict[str, Any]:
    quality_pct = _weapon_quality_pct(weapon)
    return {
        "name": str(row_get(weapon, "name", "")),
        "rarity": weapon_quality_rarity(quality_pct),
        "weapon_type": str(row_get(weapon, "weapon_type", "sword")),
        "quality": weapon_quality_rarity(quality_pct),
        "quality_pct": quality_pct,
        "mana_cost": _int(row_get(weapon, "mana_cost", 3)),
        "wear": str(row_get(weapon, "wear", "Unknown")),
        "attack_bonus": _int(row_get(weapon, "attack_bonus", 0)),
        "defense_bonus": _int(row_get(weapon, "defense_bonus", 0)),
        "passive": row_get(weapon, "passive"),
        "affixes": row_get(weapon, "affixes", "[]"),
        "stat_rolls": row_get(weapon, "stat_rolls"),
    }


async def _restore_weapon_snapshot(db, user_id: int, weapon_id: int, snapshot: dict[str, Any]) -> None:
    from core.rpg import invalidate_player_weapons_cache
    invalidate_player_weapons_cache(user_id)
    await db.execute(
        """UPDATE weapons
           SET name = ?, rarity = ?, weapon_type = ?, quality = ?, quality_pct = ?, mana_cost = ?, wear = ?,
               attack_bonus = ?, defense_bonus = ?, passive = ?, affixes = ?, stat_rolls = ?
           WHERE id = ? AND user_id = ?""",
        (
            snapshot["name"], snapshot["rarity"], snapshot["weapon_type"], snapshot["quality"], snapshot["quality_pct"],
            snapshot["mana_cost"], snapshot["wear"], snapshot["attack_bonus"], snapshot["defense_bonus"],
            snapshot["passive"], snapshot["affixes"], snapshot.get("stat_rolls"), weapon_id, user_id,
        ),
    )


async def _weapon_reroll_embed(owner: discord.Member | discord.User, before: Any, after: Any, *, cost: int, mode: str, attempts: int, remaining: int, color=discord.Color.dark_gray()) -> tuple[discord.Embed, discord.File | None]:
    title = f"{owner.display_name}'s {weapon_display_name(before)} Reroll"
    wear_before = str(row_get(before, "wear", "Unknown"))
    wear_after = str(row_get(after, "wear", "Unknown"))

    before_desc = _weapon_desc_text(before, owner)
    after_desc = _weapon_desc_text(after, owner)
    before_quality = _weapon_quality_pct(before)
    after_quality = _weapon_quality_pct(after)
    before_tier = _weapon_tier(before)
    after_tier = _weapon_tier(after)
    desc = (
        f"**{owner.display_name}** spent **{cost}** {material_label(WEAPON_SHARD_KEY)} to reroll **{mode}**!\n"
        f"Quality {_rarity_badge(before_tier)} **{before_quality}%** ({before_tier}) -> "
        f"{_rarity_badge(after_tier)} **{after_quality}%** ({after_tier})"
    )
    if wear_before != wear_after:
        desc += f"\n\nWear changes from `{wear_before}` -> `{wear_after}`"
    desc += "\n\n**BEFORE**\n\n" + before_desc
    desc += "\n\n**AFTER**\n\n" + after_desc
    embed = _embed(title, desc, color if color else discord.Color.dark_gray())
    embed.set_author(name=owner.display_name, icon_url=owner.display_avatar.url)
    embed.set_footer(text=f"Reroll Attempts: {attempts} | Shards left: {remaining:,}")
    card_file = discord.File(await run_render(render_weapon_detail_card, owner.display_name, after), filename="abyssia_weapon_reroll.png")
    embed.set_image(url="attachment://abyssia_weapon_reroll.png")
    return embed, card_file


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

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅", row=0)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self._disable()
        embed, asset_file = await _weapon_reroll_embed(self.author, self.before_row, self.after_row, cost=self.cost, mode=self.mode, attempts=self.attempts, remaining=self.remaining, color=discord.Color.dark_green())
        kwargs = {"embed": embed, "view": self}
        if asset_file:
            kwargs["attachments"] = [asset_file]
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="✖️", row=0)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await _restore_weapon_snapshot(self.cog.bot.db, self.author.id, self.weapon_id, self.before_snapshot)
        self._disable()
        embed, asset_file = await _weapon_reroll_embed(self.author, self.before_row, self.after_row, cost=self.cost, mode=self.mode, attempts=self.attempts, remaining=self.remaining, color=discord.Color.dark_red())
        embed.title = "Weapon Reroll Cancelled"
        kwargs = {"embed": embed, "view": self}
        if asset_file:
            kwargs["attachments"] = [asset_file]
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.primary, emoji="🔁", row=0)
    async def reroll_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        before = await self.cog.bot.db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (self.weapon_id, self.author.id))
        if before is None:
            await interaction.response.send_message("Weapon not found.", ephemeral=True)
            return
        try:
            if self.mode == "passive":
                after = await owo_reroll_passive(self.cog.bot.db, self.author.id, self.weapon_id)
            else:
                after = await owo_reroll_stat(self.cog.bot.db, self.author.id, self.weapon_id)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        remaining = await get_quantity(self.cog.bot.db, self.author.id, "material", WEAPON_SHARD_KEY)
        self.before_row = before
        self.after_row = after
        self.cost = OWO_REROLL_COST
        self.attempts += 1
        self.remaining = remaining
        self.before_snapshot = _weapon_snapshot(before)
        embed, asset_file = await _weapon_reroll_embed(self.author, before, after, cost=OWO_REROLL_COST, mode=self.mode, attempts=self.attempts, remaining=remaining)
        kwargs = {"embed": embed, "view": self}
        if asset_file:
            kwargs["attachments"] = [asset_file]
        await interaction.response.edit_message(**kwargs)


def _weapon_reroll_summary(weapon: Any) -> str:
    wtype = str(row_get(weapon, "weapon_type", "sword"))
    quality_pct = _weapon_quality_pct(weapon)
    tier = _weapon_tier(weapon)
    wear = str(row_get(weapon, "wear", "Unknown"))
    stats = weapon_stats(weapon)
    stat_bits: list[str] = []
    stat_meta = (
        ("hp", "hp", "HP"),
        ("str_stat", "str", "STR"),
        ("pr_stat", "def", "DEF"),
        ("wp_stat", "mana", "MANA"),
        ("mag_stat", "mag", "MAG"),
        ("mr_stat", "res", "RES"),
    )
    for key, icon_key, label in stat_meta:
        value = _int(stats.get(key, 0))
        if value:
            stat_bits.append(f"{_stat_icon(icon_key, label)} `+{value}`")
    passive = _json_obj(row_get(weapon, "passive"), {})
    if isinstance(passive, dict) and passive.get("key"):
        p_key = str(passive.get("key", ""))
        p_name = str(passive.get("name") or p_key.replace("_", " ").title())
        p_roll = min(100, _int(passive.get("roll", passive.get("chance", 0)) or 0))
        p_chance = _int(passive.get("chance", 0))
        p_icon = passive_emoji(p_key)
        passive_text = f"{p_icon} **{p_name}**".strip()
        if p_roll:
            passive_text += f" `{p_roll}%`"
        if p_chance:
            passive_text += f" | Trigger `{p_chance}%`"
        p_desc = format_passive_description(p_key, p_roll)
        if p_desc:
            passive_text += f"\n_{p_desc}_"
    else:
        passive_text = "No passive"
    if stat_bits:
        stat_lines = ["  ".join(stat_bits[i:i + 3]) for i in range(0, len(stat_bits), 3)]
        stat_text = "\n".join(stat_lines)
    else:
        stat_text = "No rolled stat bonuses"
    rarity_icon = rarity_emoji(tier) or tier
    weapon_icon = weapon_emoji(wtype) or ""
    return (
        f"`{_weapon_id(weapon)}` {rarity_icon} {weapon_icon} **{weapon_display_name(weapon)}**\n"
        f"Quality `{quality_pct}%` | Wear `{wear}`\n"
        f"Stats: {stat_text}\n"
        f"Passive: {passive_text}"
    )


class WeaponRerollActionButton(discord.ui.Button):
    def __init__(self, action: str, *, disabled: bool = False) -> None:
        labels = {"confirm": "Keep", "cancel": "Restore", "reroll": "Reroll Again"}
        emojis = {"confirm": "\u2705", "cancel": "\u21a9\ufe0f", "reroll": "\U0001f501"}
        styles = {
            "confirm": discord.ButtonStyle.success,
            "cancel": discord.ButtonStyle.danger,
            "reroll": discord.ButtonStyle.primary,
        }
        super().__init__(label=labels[action], emoji=emojis[action], style=styles[action], disabled=disabled)
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, WeaponRerollView):
            await interaction.response.send_message("This reroll view expired.", ephemeral=True)
            return
        if self.action == "confirm":
            view.completed = True
            view.notice = "Kept the current roll."
            await view._edit(interaction, color=discord.Color.dark_green())
            return
        if self.action == "cancel":
            await _restore_weapon_snapshot(view.cog.bot.db, view.author.id, view.weapon_id, view.before_snapshot)
            restored = await view.cog.bot.db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (view.weapon_id, view.author.id))
            if restored is not None:
                view.after_row = restored
            view.completed = True
            view.notice = "Restored the original weapon roll."
            await view._edit(interaction, color=discord.Color.dark_red())
            return

        try:
            if view.mode == "passive":
                after = await owo_reroll_passive(view.cog.bot.db, view.author.id, view.weapon_id)
            else:
                after = await owo_reroll_stat(view.cog.bot.db, view.author.id, view.weapon_id)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        view.after_row = after
        view.cost = OWO_REROLL_COST
        view.attempts += 1
        view.remaining = await get_quantity(view.cog.bot.db, view.author.id, "material", WEAPON_SHARD_KEY)
        view.notice = None
        await view._edit(interaction)


class WeaponRerollView(discord.ui.LayoutView):
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
        self.completed = False
        self.notice: str | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author.id:
            return True
        await interaction.response.send_message("This reroll belongs to another hunter.", ephemeral=True)
        return False

    def _refresh_layout(self, *, filename: str = "abyssia_weapon_reroll.png", color: discord.Color | None = None) -> None:
        self.clear_items()
        accent = color or discord.Color.dark_gray()
        mode_label = "Passive" if self.mode == "passive" else "Stats"
        container = discord.ui.Container(accent_colour=accent)
        container.add_item(
            discord.ui.TextDisplay(
                f"## Weapon {mode_label} Reroll\n"
                f"{self.author.display_name} | Attempts `{self.attempts}` | Shards `{self.remaining:,}`"
            )
        )
        container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    f"attachment://{filename}",
                    description=f"{self.author.display_name}'s rerolled weapon",
                )
            )
        )
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"**Before**\n{_weapon_reroll_summary(self.before_row)}"))
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"**After**\n{_weapon_reroll_summary(self.after_row)}"))
        footer = f"Cost `{self.cost}` {material_label(WEAPON_SHARD_KEY)}"
        if self.notice:
            footer += f" | {self.notice}"
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(footer))
        row = discord.ui.ActionRow()
        row.add_item(WeaponRerollActionButton("confirm", disabled=self.completed))
        row.add_item(WeaponRerollActionButton("reroll", disabled=self.completed))
        row.add_item(WeaponRerollActionButton("cancel", disabled=self.completed))
        container.add_item(row)
        self.add_item(container)

    async def _render(self, *, color: discord.Color | None = None) -> tuple[list[discord.File], "WeaponRerollView"]:
        file = discord.File(
            await run_render(render_weapon_detail_card, self.author.display_name, self.after_row),
            filename="abyssia_weapon_reroll.png",
        )
        self._refresh_layout(filename=file.filename, color=color)
        return [file], self

    async def _edit(self, interaction: discord.Interaction, *, color: discord.Color | None = None) -> None:
        await interaction.response.defer()
        files, _ = await self._render(color=color)
        if interaction.message is not None:
            await interaction.message.edit(content=None, embed=None, attachments=files, view=self)


class WeaponTypeFilterSelect(discord.ui.Select):
    def __init__(self, parent: "WeaponPageView") -> None:
        options = [discord.SelectOption(label="All Types", value="all", description="Show every weapon type.")]
        for key, data in WEAPON_TYPES.items():
            label = str(data.get("name", key.replace("_", " ").title()))
            options.append(discord.SelectOption(label=label[:100], value=key, description=f"Only show {label} weapons."[:100]))
        super().__init__(placeholder="Filter by weapon type...", min_values=1, max_values=1, options=options[:25], row=1)
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.type_filter = self.values[0]
        self.parent_view.page = 1
        self.parent_view._update_buttons()
        await self.parent_view._edit(interaction)


class WeaponTierFilterSelect(discord.ui.Select):
    def __init__(self, parent: "WeaponPageView") -> None:
        options = [discord.SelectOption(label="All Tiers", value="all", description="Show every quality tier.")]
        for low, high, rarity in WEAPON_QUALITY_RARITY_TIERS:
            if low == high:
                range_text = f"{low}%"
            else:
                range_text = f"{low}-{high}%"
            options.append(discord.SelectOption(label=rarity[:100], value=rarity, description=f"Quality {range_text}"[:100]))
        super().__init__(placeholder="Filter by quality tier...", min_values=1, max_values=1, options=options[:25], row=2)
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.tier_filter = self.values[0]
        self.parent_view.page = 1
        self.parent_view._update_buttons()
        await self.parent_view._edit(interaction)


class WeaponSortSelect(discord.ui.Select):
    def __init__(self, parent: "WeaponPageView") -> None:
        options = [
            discord.SelectOption(label="Best Quality", value="quality", description="Highest quality first.", default=parent.sort_filter == "quality"),
            discord.SelectOption(label="Recently Added", value="recent", description="Newest weapon IDs first.", default=parent.sort_filter == "recent"),
        ]
        super().__init__(placeholder="Sort weapons...", min_values=1, max_values=1, options=options, row=3)
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.sort_filter = self.values[0]
        self.parent_view.page = 1
        self.parent_view._update_buttons()
        await self.parent_view._edit(interaction)


class WeaponPageButton(discord.ui.Button):
    def __init__(self, direction: int, *, disabled: bool = False) -> None:
        super().__init__(
            label="Prev" if direction < 0 else "Next",
            style=discord.ButtonStyle.secondary,
            emoji="\u25c0\ufe0f" if direction < 0 else "\u25b6\ufe0f",
            disabled=disabled,
        )
        self.direction = direction

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, WeaponPageView):
            await interaction.response.send_message("This weapon vault expired.", ephemeral=True)
            return
        view.page = max(1, min(view._total_pages(), view.page + self.direction))
        await view._edit(interaction)


class WeaponFavoriteButton(discord.ui.Button):
    def __init__(self, active: bool = False) -> None:
        super().__init__(
            label="Favorites",
            style=discord.ButtonStyle.primary if active else discord.ButtonStyle.secondary,
            emoji="\u2b50",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, WeaponPageView):
            await interaction.response.send_message("This weapon vault expired.", ephemeral=True)
            return
        view.fav_only = not view.fav_only
        view.page = 1
        await view._edit(interaction)


class WeaponPageView(discord.ui.LayoutView):
    def __init__(self, author_id: int, display_name: str, avatar_url: str, weps: list, page: int, creature_map: dict[int, tuple[str, str]] | None = None) -> None:
        super().__init__(timeout=120)
        self.author_id = author_id
        self.display_name = display_name
        self.avatar_url = avatar_url
        self.weps = weps
        self.page = page
        self.creature_map = creature_map or {}
        self.type_filter = "all"
        self.tier_filter = "all"
        self.sort_filter = "quality"
        self.fav_only = False

    def _filtered_weps(self) -> list:
        filtered = list(self.weps)
        if self.type_filter != "all":
            filtered = [weapon for weapon in filtered if str(row_get(weapon, "weapon_type", "sword")) == self.type_filter]
        if self.tier_filter != "all":
            filtered = [weapon for weapon in filtered if _weapon_tier(weapon) == self.tier_filter]
        if self.fav_only:
            filtered = [weapon for weapon in filtered if _int(row_get(weapon, "is_favorite", 0))]
        if self.sort_filter == "recent":
            filtered = sorted(filtered, key=lambda row: (_int(row_get(row, "created_at", 0)), _int(row_get(row, "id", 0))), reverse=True)
        else:
            filtered = sorted(filtered, key=lambda row: (_weapon_quality_pct(row), _int(row_get(row, "id", 0))), reverse=True)
        return filtered

    def _total_pages(self) -> int:
        total = len(self._filtered_weps())
        return max(1, (total + WEAPON_CARD_PAGE_SIZE - 1) // WEAPON_CARD_PAGE_SIZE)

    def _update_buttons(self):
        self.page = max(1, min(self.page, self._total_pages()))

    def _refresh_layout(self, *, total_pages: int, filtered: list) -> None:
        self.clear_items()
        title_icon = weapon_emoji("sword") or ""
        title = f"{title_icon} Weapon Vault".strip()
        filter_text = _weapon_filter_text(self.type_filter, self.tier_filter, fav_only=self.fav_only, sort_filter=self.sort_filter)
        container = discord.ui.Container(accent_colour=discord.Color.gold())
        container.add_item(
            discord.ui.TextDisplay(
                f"## {title}\n"
                f"{self.display_name} • Page `{self.page}/{total_pages}` • `{len(filtered)}` weapons"
            )
        )
        container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    "attachment://abyssia_weapons.png",
                    description=f"{self.display_name}'s weapon vault page {self.page}",
                )
            )
        )
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"**Filters**\n{filter_text}"))
        summary = "\n".join(_weapon_vault_summary_lines(filtered, self.page, creature_map=self.creature_map))
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"**Featured Weapons**\n{summary}"))
        type_row = discord.ui.ActionRow()
        type_row.add_item(WeaponTypeFilterSelect(self))
        container.add_item(type_row)
        tier_row = discord.ui.ActionRow()
        tier_row.add_item(WeaponTierFilterSelect(self))
        container.add_item(tier_row)
        sort_row = discord.ui.ActionRow()
        sort_row.add_item(WeaponSortSelect(self))
        container.add_item(sort_row)
        button_row = discord.ui.ActionRow()
        button_row.add_item(WeaponPageButton(-1, disabled=self.page <= 1))
        button_row.add_item(WeaponPageButton(1, disabled=self.page >= total_pages))
        button_row.add_item(WeaponFavoriteButton(self.fav_only))
        container.add_item(button_row)
        self.add_item(container)

    async def _render(self) -> tuple[list[discord.File], "WeaponPageView"]:
        filtered = self._filtered_weps()
        total_pages = self._total_pages()
        self.page = max(1, min(self.page, total_pages))
        image = await run_render(render_weapons_card, self.display_name, filtered, page=self.page, total_pages=total_pages)
        file = discord.File(image, filename="abyssia_weapons.png")
        self._refresh_layout(total_pages=total_pages, filtered=filtered)
        return [file], self

    async def _edit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        files, _ = await self._render()
        if interaction.message is not None:
            await interaction.message.edit(content=None, embed=None, attachments=files, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message("This weapon vault belongs to another hunter.", ephemeral=True)
        return False


class RPGEquipment(commands.Cog):
    """Weapon and creature detail commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _reply_weapon_detail(
        self,
        ctx: commands.Context,
        embed: discord.Embed,
        asset_file: discord.File | None,
        weapon_id: int,
    ) -> None:
        filename = getattr(asset_file, "filename", "abyssia_weapon_detail.png") if asset_file else None
        view = AbyssiaLayoutView(
            owner_id=ctx.author.id,
            title=str(embed.title or "Weapon Detail"),
            subtitle="Inspect • equip • favorite",
            image_filename=filename,
            image_description=str(embed.title or "Weapon Detail"),
            sections=[("Weapon", str(embed.description or "No details."))],
            shortcuts=[
                ("Equip Slot 1", f"b w {weapon_id} 1"),
                ("Equip Slot 2", f"b w {weapon_id} 2"),
                ("Equip Slot 3", f"b w {weapon_id} 3"),
                ("Favorite", f"b favorite {weapon_id}"),
                ("Vault", "b weapons"),
            ],
            accent=embed.color or discord.Color.dark_gray(),
        )
        if asset_file:
            await ctx.reply(file=asset_file, view=view, mention_author=False)
        else:
            await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="weapons", aliases=["weps", "armory"])
    async def weapons(self, ctx: commands.Context, selector: str | None = None, filter_type: str = "all") -> None:
        """View your weapon vault, or inspect one weapon by ID. Use filter: recent, favorites"""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=600.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        if selector and selector.lstrip("#").isdigit():
            weapon_id = int(selector.lstrip("#"))
            row = await self.bot.db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, ctx.author.id))
            if row is not None:
                embed, asset_file = await _weapon_detail_embed(ctx.author, row)
                await self._reply_weapon_detail(ctx, embed, asset_file, weapon_id)
                return
        
        # Get all weapons
        all_weps = await player_weapons(self.bot.db, ctx.author.id)
        
        requested_filter = filter_type.lower()
        if selector and not selector.lstrip("#").isdigit():
            requested_filter = selector.lower()

        weps = list(all_weps)
        creature_ids = list({_int(row_get(w, "equipped_creature_id")) for w in weps if row_get(w, "equipped_creature_id")})
        creature_map: dict[int, tuple[str, str]] = {}
        if creature_ids:
            placeholders = ",".join("?" for _ in creature_ids)
            cre_rows = await self.bot.db.fetchall(
                f"SELECT id, name, rarity FROM rpg_creatures WHERE id IN ({placeholders})", creature_ids,
            )
            creature_map = {int(r["id"]): (str(r["name"]), str(r["rarity"])) for r in cre_rows}
        if not all_weps:
            msg = "No weapons yet. Open crates to find them."
            await ctx.reply(embed=_embed("Weapon Vault", msg), mention_author=False)
            return
        page = 1
        if selector and selector.isdigit():
            page = int(selector)
        page = max(1, page)
        view = WeaponPageView(ctx.author.id, ctx.author.display_name, ctx.author.display_avatar.url, weps, page, creature_map)
        if requested_filter in ("recent", "new"):
            view.sort_filter = "recent"
        elif requested_filter in ("favorites", "fav", "starred"):
            view.fav_only = True
        files, _ = await view._render()
        await ctx.reply(files=files, view=view, mention_author=False)
        return

    @commands.hybrid_command(name="favorite", aliases=["fav", "star"])
    async def favorite(self, ctx: commands.Context, weapon_id: int) -> None:
        """Toggle favorite status of a weapon. Favorited weapons are protected from salvage."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        row = await self.bot.db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, ctx.author.id))
        if row is None:
            await ctx.reply(embed=_embed("Favorite", "Weapon not found."), mention_author=False, ephemeral=True)
            return
        
        current_fav = _int(row_get(row, "is_favorite", 0))
        new_fav = 1 if current_fav == 0 else 0
        from core.rpg import invalidate_player_weapons_cache
        invalidate_player_weapons_cache(ctx.author.id)
        await self.bot.db.execute("UPDATE weapons SET is_favorite = ? WHERE id = ?", (new_fav, weapon_id))
        
        wdisplay = weapon_display_name(row)
        if new_fav:
            await ctx.reply(embed=_embed("Favorite", f"  **{wdisplay}** added to favorites. It will be protected from salvage."), mention_author=False)
        else:
            await ctx.reply(embed=_embed("Favorite", f"  **{wdisplay}** removed from favorites."), mention_author=False)

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
        weapon_display = weapon_label(wtype, wdisplay)
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
        await ctx.reply(embed=_embed("Unequip", f"**{weapon_label(wtype, wdisplay)}** returned to vault."), mention_author=False)

    @commands.hybrid_command(name="w", aliases=[])
    async def w_shortcut(self, ctx: commands.Context, weapon_id: Optional[int] = None, slot: Optional[int] = None) -> None:
        """Weapon vault, inspect, or equip. bw = vault, bw <id> = inspect, bw <id> <slot> = equip to team slot."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=600.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        if weapon_id is None:
            await self.weapons(ctx, None)
            return
        row = await self.bot.db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, ctx.author.id))
        if not row:
            await ctx.reply(embed=_embed("Weapon", f"No weapon with ID `{weapon_id}`."), mention_author=False, ephemeral=True)
            return
        if slot is None:
            embed, asset_file = await _weapon_detail_embed(ctx.author, row)
            await self._reply_weapon_detail(ctx, embed, asset_file, weapon_id)
            return
        if slot not in {1, 2, 3}:
            await ctx.reply(embed=_embed("Equip", "Slot must be 1, 2, or 3."), mention_author=False, ephemeral=True)
            return
        team_row = await self.bot.db.fetchone(
            "SELECT t.creature_id, c.name, c.rarity, c.level FROM rpg_teams t JOIN rpg_creatures c ON c.id = t.creature_id WHERE t.user_id = ? AND t.slot = ?",
            (ctx.author.id, slot),
        )
        if not team_row:
            await ctx.reply(embed=_embed("Equip", f"No creature in team slot **{slot}**."), mention_author=False, ephemeral=True)
            return
        target_id = int(team_row["creature_id"])
        target_name = str(team_row["name"])
        target_rarity = str(team_row["rarity"])
        target_level = int(team_row["level"])
        old_weapon = await weapon_for_creature(self.bot.db, target_id)
        if old_weapon:
            await unequip_weapon(self.bot.db, old_weapon["id"])
        await equip_weapon_to_creature(self.bot.db, weapon_id, target_id)
        weapon_display = weapon_display_name(row)
        wtype = str(row_get(row, "weapon_type", "sword"))
        await ctx.reply(embed=_embed("Equip", f"**{weapon_label(wtype, weapon_display)}** -> **{creature_label(target_name, target_rarity)}** Lv.{target_level} (Slot {slot})"), mention_author=False)

    @commands.hybrid_command(name="wu", aliases=[])
    async def wu_shortcut(self, ctx: commands.Context, weapon_id: int) -> None:
        """Unequip a weapon. Usage: bwu <weapon_id>"""
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
        await ctx.reply(embed=_embed("Unequip", f"**{weapon_label(wtype, wdisplay)}** returned to vault."), mention_author=False)

    @commands.hybrid_command(name="wdex", aliases=["weapondex", "weaponindex"])
    async def wdex(self, ctx: commands.Context, *, weapon: str | None = None) -> None:
        """Inspect weapon rules, passives, affixes, or one owned weapon by ID."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=600.0)
        if not weapon:
            embeds = _weapon_index_embeds()
            view = AbyssiaLayoutView(
                owner_id=ctx.author.id,
                title="Weapon Dex",
                subtitle="Base weapons | quality tiers | passives | affixes",
                sections=_sections_from_embeds(embeds),
                shortcuts=[("Vault", "b weapons")],
                accent=discord.Color.gold(),
            )
            await ctx.reply(view=view, mention_author=False)
            return
        if not weapon.lstrip("#").isdigit():
            key = normalize_key(weapon)
            matched_key = None
            for candidate, data in WEAPON_TYPES.items():
                if candidate == key or normalize_key(str(data.get("name", candidate))) == key or key in candidate:
                    matched_key = candidate
                    break
            if matched_key is None:
                raise commands.BadArgument(f"Unknown weapon type: `{weapon}`")
            data = WEAPON_TYPES[matched_key]
            title = f"Weapon Dex - {weapon_label(matched_key, str(data.get('name', matched_key.title())))}"
            view = AbyssiaLayoutView(
                owner_id=ctx.author.id,
                title=title,
                subtitle="Weapon rules and passive pool",
                sections=_weapon_type_sections(matched_key),
                shortcuts=[("Vault", "b weapons")],
                accent=discord.Color.dark_gray(),
            )
            await ctx.reply(view=view, mention_author=False)
            return

        weapon_id = int(weapon.lstrip("#"))
        rows = await self.bot.db.fetchall(
            "SELECT * FROM weapons WHERE id = ? AND user_id = ?",
            (weapon_id, ctx.author.id),
        )
        if not rows:
            await ctx.reply(embed=_embed("Weapon Dex", f"No weapon with ID `{weapon_id}`."), mention_author=False, ephemeral=True)
            return
        w = rows[0]
        embed, asset_file = await _weapon_detail_embed(ctx.author, w)
        await self._reply_weapon_detail(ctx, embed, asset_file, weapon_id)
        return

    @commands.hybrid_command(name="weaponinfo", aliases=["wi"])
    async def weaponinfo(self, ctx: commands.Context, *, weapon_type: str) -> None:
        """Show detailed info about a weapon type (base stats, scaling, active, passives)."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=600.0)
        key = normalize_key(weapon_type)
        matched_key = None
        for candidate, data in WEAPON_TYPES.items():
            if candidate == key or normalize_key(str(data.get("name", candidate))) == key or key in candidate:
                matched_key = candidate
                break
        if matched_key is None:
            raise commands.BadArgument(f"Unknown weapon type: `{weapon_type}`")
        data = WEAPON_TYPES[matched_key]
        title = f"Weapon Info - {weapon_label(matched_key, str(data.get('name', matched_key.title())))}"
        view = AbyssiaLayoutView(
            owner_id=ctx.author.id,
            title=title,
            subtitle="Weapon rules and passive pool",
            sections=_weapon_type_sections(matched_key),
            shortcuts=[("Vault", "b weapons")],
            accent=discord.Color.dark_gray(),
        )
        await ctx.reply(view=view, mention_author=False)

    @commands.group(name="wr", aliases=["wreroll", "wrr"], invoke_without_command=True)
    async def wr_group(self, ctx: commands.Context) -> None:
        """Reroll a weapon using Weapon Shards. Subcommands: stat, passive."""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @wr_group.command(name="stat", aliases=["stats", "s"])
    async def wr_stat(self, ctx: commands.Context, weapon_id: int) -> None:
        """Reroll all stats on a weapon. Cost: 100 Weapon Shards."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=600.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        before = await self.bot.db.fetchone(
            "SELECT * FROM weapons WHERE id = ? AND user_id = ?",
            (weapon_id, ctx.author.id),
        )
        if before is None:
            await ctx.reply(embed=_embed("Weapon Stat Reroll", f"No weapon with ID `{weapon_id}`."), mention_author=False, ephemeral=True)
            return
        try:
            updated = await owo_reroll_stat(self.bot.db, ctx.author.id, weapon_id)
        except ValueError as exc:
            await ctx.reply(embed=_embed("Weapon Stat Reroll", str(exc)), mention_author=False, ephemeral=True)
            return

        remaining = await get_quantity(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY)
        view = WeaponRerollView(
            self,
            ctx.author,
            weapon_id,
            "stat",
            _weapon_snapshot(before),
            before,
            updated,
            OWO_REROLL_COST,
            1,
            remaining,
        )
        files, _ = await view._render()
        await ctx.reply(files=files, view=view, mention_author=False)

    @wr_group.command(name="passive", aliases=["pass", "p"])
    async def wr_passive(self, ctx: commands.Context, weapon_id: int) -> None:
        """Reroll the passive on a weapon. Cost: 100 Weapon Shards."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=600.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        before = await self.bot.db.fetchone(
            "SELECT * FROM weapons WHERE id = ? AND user_id = ?",
            (weapon_id, ctx.author.id),
        )
        if before is None:
            await ctx.reply(embed=_embed("Weapon Passive Reroll", f"No weapon with ID `{weapon_id}`."), mention_author=False, ephemeral=True)
            return
        try:
            updated = await owo_reroll_passive(self.bot.db, ctx.author.id, weapon_id)
        except ValueError as exc:
            await ctx.reply(embed=_embed("Weapon Passive Reroll", str(exc)), mention_author=False, ephemeral=True)
            return

        remaining = await get_quantity(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY)
        view = WeaponRerollView(
            self,
            ctx.author,
            weapon_id,
            "passive",
            _weapon_snapshot(before),
            before,
            updated,
            OWO_REROLL_COST,
            1,
            remaining,
        )
        files, _ = await view._render()
        await ctx.reply(files=files, view=view, mention_author=False)

    @commands.hybrid_group(name="weaponshards", aliases=["wshards", "shards"], invoke_without_command=True)
    async def weapon_shards(self, ctx: commands.Context) -> None:
        """Show your Weapon Shard balance."""
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        qty = await get_quantity(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY)
        await ctx.reply(embed=_embed("Weapon Shards", f"You have {material_label(WEAPON_SHARD_KEY)} **{qty:,}**."), mention_author=False)

    @weapon_shards.command(name="give")
    async def shards_give(self, ctx: commands.Context, target: discord.Member, amount: int) -> None:
        """Give Weapon Shards to another player."""
        if target.bot:
            await ctx.reply(embed=_embed("Error", "You can't give shards to a bot."), mention_author=True)
            return
        if target.id == ctx.author.id:
            await ctx.reply(embed=_embed("Error", "You can't give shards to yourself."), mention_author=True)
            return
        if amount <= 0:
            await ctx.reply(embed=_embed("Error", "Amount must be at least 1."), mention_author=True)
            return
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        await ensure_player(self.bot.db, target.id, target.display_name)
        owned = await get_quantity(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY)
        if owned < amount:
            await ctx.reply(embed=_embed("Error", f"You only have **{owned:,}** {material_label(WEAPON_SHARD_KEY)}."), mention_author=True)
            return
        await add_item(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY, -amount)
        await add_item(self.bot.db, target.id, "material", WEAPON_SHARD_KEY, amount)
        await ctx.reply(embed=_embed("Shards Given", f"Gave **{amount:,}** {material_label(WEAPON_SHARD_KEY)} to {target.mention}."), mention_author=False)

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
        from core.battle_engine import compute_display_stats
        bstats = compute_display_stats(cr)
        lines = [
            f"**{creature_label(str(cr['name']), str(cr['rarity']))}** - {rarity_label(str(cr['rarity']))}",
            f"Level {cr['level']}",
            "",
            f"HP {bstats['HP']}  •  STR {bstats['STR']}  •  MANA {bstats['MANA']}  •  MAG {bstats['MAG']}",
        ]
        if weapon:
            ws = weapon_stats(weapon)
            se = weapon_effects(weapon)
            wtype = str(row_get(weapon, "weapon_type", "sword"))
            quality_pct = _weapon_quality_pct(weapon)
            tier = _weapon_tier(weapon)
            wear = str(row_get(weapon, "wear", "Unknown"))
            wdisplay = weapon_display_name(weapon)
            ability = Ability.for_weapon_type(wtype)
            sr_raw = row_get(weapon, "stat_rolls")
            sr = {}
            if sr_raw:
                try:
                    sr = json.loads(str(sr_raw)) if isinstance(sr_raw, str) else sr_raw
                except Exception:
                    pass
            wp_roll = _int(sr.get("wp_cost", 50))
            actual_wp = round(ability.wp_cost_max - (ability.wp_cost_max - ability.wp_cost_min) * wp_roll / 100.0)
            lines.append("")
            lines.append(f"Weapon: **{weapon_label(wtype, wdisplay)}**")
            lines.append(f"  Quality {quality_pct}% ({tier}) - MANA {actual_wp} - Wear {wear}")
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
                        p_roll = min(100, max(0, _int(passive.get("roll", 50))))
                        p_chance = _int(passive.get("chance", 0))
                        p_desc = passive.get("desc", "")
                        trigger_line = f" (Trigger: {p_chance}%)" if p_chance > 0 else ""
                        lines.append(f"  {passive_label(p_key, str(p_name), p_roll)} - {p_desc}{trigger_line}")
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
