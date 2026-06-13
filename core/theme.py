from __future__ import annotations

import json
import re
from pathlib import Path

import discord

from core.discord_assets import custom_asset_emoji, emoji_asset_name
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
ROOT_DIR = Path(__file__).resolve().parents[1]
EMOJI_MAP_PATH = ROOT_DIR / "data" / "emoji_map.json"
CUSTOM_EMOJI_RE = re.compile(r"^<a?:[A-Za-z0-9_]{2,32}:[0-9]{15,25}>$")
RAW_EMOJI_NAME_RE = re.compile(r"^:[A-Za-z0-9_]{2,32}:$")
_EMOJI_MAP_CACHE: dict[str, str] = {}
_EMOJI_MAP_MTIME_NS: int | None = None

CURRENCY_ASSET_KEYS = {
    "gold": "souls",
    "gems": "gems",
}

CURRENCY_NAMES = {
    "gold": "Souls",
    "gems": "Void Gems",
}

STAT_EMOJIS = {
    "hp": "HP",
    "str_stat": "STR",
    "pr_stat": "DEF",
    "wp_stat": "MANA",
    "mag_stat": "MAG",
    "mr_stat": "RES",
    "spd": "SPD",
    "strength": "STR",
    "dexterity": "DEX",
    "luck": "LCK",
    "wisdom": "WIS",
    "endurance": "END",
}


def _flatten_emoji_map(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    flat: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            flat[str(key)] = value
        elif isinstance(value, dict):
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, str):
                    flat[str(nested_key)] = nested_value
    return flat


def _load_emoji_map() -> dict[str, str]:
    global _EMOJI_MAP_CACHE, _EMOJI_MAP_MTIME_NS
    try:
        stat = EMOJI_MAP_PATH.stat()
    except OSError:
        _EMOJI_MAP_CACHE = {}
        _EMOJI_MAP_MTIME_NS = None
        return _EMOJI_MAP_CACHE

    if stat.st_mtime_ns == _EMOJI_MAP_MTIME_NS:
        return _EMOJI_MAP_CACHE

    try:
        payload = json.loads(EMOJI_MAP_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _EMOJI_MAP_CACHE = {}
    else:
        _EMOJI_MAP_CACHE = _flatten_emoji_map(payload)
    _EMOJI_MAP_MTIME_NS = stat.st_mtime_ns
    return _EMOJI_MAP_CACHE


def _safe_emoji_value(value: str) -> str:
    value = str(value or "").strip()
    if not value or RAW_EMOJI_NAME_RE.match(value):
        return ""
    if CUSTOM_EMOJI_RE.match(value):
        return value
    # Allow Unicode or short plain-text fallback labels, but never raw :emoji_name: strings.
    return value if not value.startswith(":") else ""


def emoji_for(key: str, fallback: str = "") -> str:
    mapped = _load_emoji_map().get(str(key).strip())
    if mapped:
        safe = _safe_emoji_value(mapped)
        if safe:
            return safe
    return _safe_emoji_value(fallback)


def _label_with_emoji(kind: str, key: str, fallback: str) -> str:
    emoji = asset_emoji(kind, key)
    return f"{emoji} {fallback}" if emoji else fallback


def asset_emoji(kind: str, key: str) -> str:
    mapped = emoji_for(emoji_asset_name(kind, key))
    if mapped:
        return mapped
    return custom_asset_emoji(BOT, kind, key)


def rarity_emoji(rarity: str) -> str:
    return asset_emoji("rarity", normalize_key(rarity))


def rarity_label(rarity: str) -> str:
    return _label_with_emoji("rarity", rarity.lower(), rarity)


def creature_emoji(name: str, rarity: str | None = None) -> str:
    from core.rpg_data import creature_asset_key
    return asset_emoji("creatures", creature_asset_key(name))


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


def emoji_health_bar(current: int, maximum: int, *, width: int = 12) -> str:
    maximum = max(1, int(maximum))
    current = max(0, min(maximum, int(current)))
    width = max(4, min(20, int(width)))
    filled = max(0, min(width, round((current / maximum) * width)))
    full = asset_emoji("ui", "hp_full") or "🟥"
    empty = asset_emoji("ui", "hp_empty") or "⬛"
    return f"{full * filled}{empty * (width - filled)}"


def equipment_label(key: str, fallback: str) -> str:
    return _label_with_emoji("equipment", key, fallback)


def _strip_prefixed_key(key: str, prefix: str) -> str:
    safe = normalize_key(str(key))
    expected = f"{prefix}_"
    return safe[len(expected):] if safe.startswith(expected) else safe


_WEAPON_TEXT_FALLBACKS: dict[str, str] = {
    "sword": "SWD",
    "bow": "BOW",
    "axe": "AXE",
    "dagger": "DAG",
    "crossbow": "XBW",
    "staff": "STF",
    "staff_of_purity": "PUR",
    "shield": "SHD",
    "hammer": "HAM",
    "orb": "ORB",
    "rune": "RUN",
    "soulreaper": "REP",
    "briar_relic": "BRI",
    "rot_chalice": "ROT",
    "banner": "BAN",
    "eye": "EYE",
    "judgement_blade": "JDG",
    "lantern": "LAN",
    "mirror_relic": "MIR",
    "final_bell_scythe": "BELL",
}


def weapon_emoji(key: str) -> str:
    safe = _strip_prefixed_key(key, "weapon")
    emoji = asset_emoji("weapons", safe)
    if emoji:
        return emoji
    return _WEAPON_TEXT_FALLBACKS.get(safe, safe[:3].upper())


def weapon_label(key: str, fallback: str | None = None) -> str:
    data = WEAPON_TYPES.get(key.lower())
    name = fallback or (str(data.get("name")) if data else key.replace("_", " ").title())
    emoji = weapon_emoji(key)
    return f"{emoji} {name}" if emoji else name


_ROLL_RARITY_TIERS: list[tuple[int, int, str]] = [
    (0, 10, "Common"), (11, 20, "Uncommon"), (21, 30, "Rare"),
    (31, 40, "Epic"), (41, 50, "Legendary"), (51, 60, "Mythic"),
    (61, 70, "Ancient"), (71, 80, "Divine"), (81, 85, "Eldritch"),
    (86, 90, "Abyssal"), (91, 120, "Prismatic"), (121, 135, "Ethereal"),
    (136, 145, "Void Lord"), (146, 999, "Hidden"),
]

_PASSIVE_TEXT_FALLBACKS: dict[str, str] = {
    "strength": "STR",
    "magic": "MAG",
    "hp": "HP",
    "wp": "MANA",
    "pr": "DEF",
    "mr": "RES",
    "thorns": "TH",
    "safeguard": "SG",
    "regeneration": "RG",
    "adaptation": "AD",
    "sacrifice": "SF",
    "bleed": "BLD",
    "burn": "BRN",
    "poison": "PSN",
    "stun": "STN",
    "shield": "SHD",
    "heal": "HEAL",
    "crit": "CRIT",
    "life_steal": "LS",
    "mana_tap": "MT",
    "soul_gain": "SOUL",
    "gem_finder": "GEM",
    "xp_boost": "XP",
    "rare_finder": "LUCK",
    "energize": "EN",
    "fear": "FEAR",
}


def _roll_rarity(roll: int) -> str:
    for low, high, rarity in _ROLL_RARITY_TIERS:
        if low <= roll <= high:
            return rarity
    return "Common"


def passive_emoji(key: str) -> str:
    safe = _strip_prefixed_key(key, "passive")
    emoji = asset_emoji("passives", safe)
    if emoji:
        return emoji
    return _PASSIVE_TEXT_FALLBACKS.get(safe, "")


def passive_label(key: str, fallback: str | None = None, chance: int | None = None, show_rarity: bool = True) -> str:
    data = WEAPON_PASSIVES.get(key.lower())
    name = fallback or (str(data.get("name")) if data else key.replace("_", " ").title())
    rarity = _roll_rarity(chance) if chance is not None else (data.get("rarity") if data else None)
    rarity_str = f"{rarity_emoji(rarity)} " if rarity and show_rarity else ""
    emoji = passive_emoji(key)
    label = f"{emoji} {name}" if emoji else name
    chance_str = f" `{chance}%`" if chance is not None else ""
    return f"{rarity_str}{label}{chance_str}"


def status_effect_emoji(key: str) -> str:
    return asset_emoji("status", key.lower())


def status_effect_label(key: str, fallback: str | None = None) -> str:
    data = STATUS_EFFECTS_BY_KEY.get(key.lower())
    name = fallback or (data.name if data else key.replace("_", " ").title())
    return _label_with_emoji("status", key.lower(), name)


def stat_emoji(key: str) -> str:
    return asset_emoji("stats", key.lower())


def stat_label(key: str, fallback: str | None = None) -> str:
    name = fallback or key.upper()
    return _label_with_emoji("stats", key.lower(), name)


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
    prefix = f"`#{creature['id']}` " if show_id and "id" in creature else ""
    stats = ""
    if show_stats:
        stats = (
            f" | STR `{creature.get('str_stat', creature.get('attack', 0))}`"
            f" DEF `{creature.get('pr_stat', creature.get('defense', 0))}`"
            f" HP `{creature['hp']}`"
        )
    return (
        f"{prefix}{creature_label(str(creature['name']), str(creature['rarity']))} "
        f"{rarity_level_badge(str(creature['rarity']), creature['level'])} - {creature['ability']}{stats}"
    )
