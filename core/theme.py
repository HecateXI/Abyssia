from __future__ import annotations

import discord

from core.discord_assets import custom_asset_emoji
from core.rpg_data import (
    CHARMS,
    CRATE_TYPES,
    MATERIALS,
    RARITY_BY_NAME,
    RARITY_INDEX,
    SIGILS,
    STATUS_EFFECTS_BY_KEY,
    WEAPON_PASSIVES,
    WEAPON_TYPES,
    ZONES,
    normalize_key,
)


DARK_COLOR = 0x2B172F
BLOOD_COLOR = 0x8F1D2C
GOLD_COLOR = 0xD7A84B
VOID_COLOR = 0x17131F

BOT: discord.Client | None = None

CURRENCY_ASSET_KEYS = {
    "gold": "souls",
    "gems": "gems",
}

CURRENCY_NAMES = {
    "gold": "Souls",
    "gems": "Void Gems",
}

STAT_EMOJIS = {
    "attack": "ATK",
    "defense": "DEF",
    "hp": "HP",
    "speed": "SPD",
    "strength": "STR",
    "dexterity": "DEX",
    "luck": "LCK",
    "wisdom": "WIS",
    "endurance": "END",
}


def _label_with_emoji(kind: str, key: str, fallback: str) -> str:
    emoji = custom_asset_emoji(BOT, kind, key)
    return f"{emoji} {fallback}" if emoji else fallback


def asset_emoji(kind: str, key: str) -> str:
    return custom_asset_emoji(BOT, kind, key)


def rarity_emoji(rarity: str) -> str:
    return asset_emoji("rarity", rarity.lower())


def rarity_label(rarity: str) -> str:
    return _label_with_emoji("rarity", rarity.lower(), rarity)


def creature_emoji(name: str, rarity: str | None = None) -> str:
    return asset_emoji("creatures", normalize_key(name))


def creature_label(name: str, rarity: str | None = None) -> str:
    emoji = creature_emoji(name, rarity)
    if not emoji and rarity:
        emoji = rarity_emoji(rarity)
    return f"{emoji} {name}" if emoji else name


def material_emoji(key: str) -> str:
    return asset_emoji("materials", key.lower())


def material_label(key: str) -> str:
    return _label_with_emoji("materials", key.lower(), MATERIALS.get(key, key.replace("_", " ").title()))


def currency_emoji(key: str) -> str:
    return asset_emoji("currency", CURRENCY_ASSET_KEYS.get(key.lower(), key.lower()))


def currency_label(key: str) -> str:
    safe = key.lower()
    asset_key = CURRENCY_ASSET_KEYS.get(safe, safe)
    return _label_with_emoji("currency", asset_key, CURRENCY_NAMES.get(safe, key.replace("_", " ").title()))


def zone_emoji(key: str) -> str:
    return asset_emoji("zones", key.lower())


def zone_label(key: str) -> str:
    zone = ZONES.get(key)
    return _label_with_emoji("zones", key.lower(), zone.name if zone else key.replace("_", " ").title())


def ui_emoji(key: str) -> str:
    return asset_emoji("ui", key)


def ui_label(key: str, fallback: str) -> str:
    return _label_with_emoji("ui", key, fallback)


def equipment_label(key: str, fallback: str) -> str:
    return _label_with_emoji("equipment", key, fallback)


def weapon_emoji(key: str) -> str:
    return asset_emoji("weapons", key.lower())


def weapon_label(key: str, fallback: str | None = None) -> str:
    data = WEAPON_TYPES.get(key.lower())
    name = fallback or (str(data.get("name")) if data else key.replace("_", " ").title())
    return _label_with_emoji("weapons", key.lower(), name)


def passive_emoji(key: str) -> str:
    return asset_emoji("passives", key.lower())


def passive_label(key: str, fallback: str | None = None) -> str:
    data = WEAPON_PASSIVES.get(key.lower())
    name = fallback or (str(data.get("name")) if data else key.replace("_", " ").title())
    return _label_with_emoji("passives", key.lower(), name)


def status_effect_emoji(key: str) -> str:
    return asset_emoji("status", key.lower())


def status_effect_label(key: str, fallback: str | None = None) -> str:
    data = STATUS_EFFECTS_BY_KEY.get(key.lower())
    name = fallback or (data.name if data else key.replace("_", " ").title())
    return _label_with_emoji("status", key.lower(), name)


def crate_emoji(key: str) -> str:
    return asset_emoji("crate", key.lower())


def crate_label(key: str, fallback: str | None = None) -> str:
    data = CRATE_TYPES.get(key.lower())
    name = fallback or (str(data.get("name")) if data else key.replace("_", " ").title())
    return _label_with_emoji("crate", key.lower(), name)


def consumable_label(key: str, fallback: str) -> str:
    return _label_with_emoji("consumable", key.lower(), fallback)


def buff_label(key: str, fallback: str | None = None) -> str:
    sigil = next((item for item in SIGILS if item.key == key), None)
    charm = next((item for item in CHARMS if item.key == key), None)
    item = sigil or charm
    name = fallback or (item.name if item else key.replace("_", " ").title())
    return _label_with_emoji("buffs", key.lower(), name)


def boss_label(key: str, fallback: str) -> str:
    return _label_with_emoji("bosses", key, fallback)


def dark_embed(title: str, description: str | None = None, *, color: int | discord.Color = DARK_COLOR) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Abyssia RPG - Dark Fantasy Monster Collector")
    return embed


def status_embed(title: str, description: str | None = None, *, color: int | discord.Color = GOLD_COLOR) -> discord.Embed:
    return dark_embed(title, description, color=color)


def rarity_rank(rarity: str) -> int:
    return RARITY_INDEX.get(rarity, 0)


def rarity_color(rarity: str) -> discord.Color:
    record = RARITY_BY_NAME.get(rarity)
    return discord.Color(record.color if record else DARK_COLOR)


def rarity_level_badge(rarity: str, level: int | str | None = None) -> str:
    if level is None:
        return rarity_label(rarity)
    return f"{rarity_label(rarity)} Lv.`{level}`"


def progress_bar(current: int, needed: int, *, width: int = 10) -> str:
    needed = max(1, needed)
    filled = max(0, min(width, round((current / needed) * width)))
    return "#" * filled + "-" * (width - filled)


def creature_line(creature, *, show_id: bool = True, show_stats: bool = False) -> str:
    prefix = f"`#{creature['id']}` " if show_id and "id" in creature.keys() else ""
    stats = ""
    if show_stats:
        stats = (
            f" | ATK `{creature['attack']}`"
            f" DEF `{creature['defense']}`"
            f" HP `{creature['hp']}`"
            f" SPD `{creature['speed']}`"
        )
    return (
        f"{prefix}{creature_label(str(creature['name']), str(creature['rarity']))} "
        f"{rarity_level_badge(str(creature['rarity']), creature['level'])} - {creature['ability']}{stats}"
    )
