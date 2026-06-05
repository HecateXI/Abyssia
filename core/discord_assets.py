from __future__ import annotations

import asyncio
import base64
import time

import discord
from discord.http import Route

from core.content_config import ASSET_DIR, get_asset_file_path, get_public_asset_url, safe_key


CURRENCY_KEYS = ("gold", "gems", "souls", "corrupted_essence", "void_crystals")
UI_KEYS = (
    "hunt",
    "autohunt",
    "battle",
    "inventory",
    "crafting",
    "marketplace",
    "quest",
    "boss_raid",
    "leaderboard",
    "profile",
)

APP_EMOJI_CACHE: dict[str, str] = {}
APP_EMOJI_REFRESHED_AT = 0.0
_APP_EMOJI_REFRESH_LOCK: asyncio.Lock | None = None


def emoji_asset_name(kind: str, key: str) -> str:
    prefix = {
        "creatures": "cr",
        "rarity": "rarity",
        "materials": "material",
        "currency": "currency",
        "ui": "ui",
        "consumable": "item",
        "equipment": "eq",
        "buffs": "buff",
        "weapons": "weapon",
        "passives": "passive",
        "status": "status",
        "crate": "crate",
        "zones": "zone",
        "bosses": "boss",
    }.get(kind, kind)
    safe = safe_key(key).lower()
    max_key_length = 32 - len(prefix) - 1
    return f"{prefix}_{safe[:max_key_length]}"


async def application_id_for(bot: discord.Client) -> int:
    app_id = getattr(bot, "application_id", None)
    if app_id:
        return int(app_id)
    info = await bot.application_info()
    return int(info.id)


def _emoji_items(payload) -> list[dict]:
    if isinstance(payload, dict):
        items = payload.get("items", [])
        return items if isinstance(items, list) else []
    if isinstance(payload, list):
        return payload
    return []


async def refresh_application_emojis(bot: discord.Client | None) -> dict[str, str]:
    global APP_EMOJI_REFRESHED_AT
    if bot is None or not hasattr(bot, "http"):
        APP_EMOJI_CACHE.clear()
        APP_EMOJI_REFRESHED_AT = time.monotonic()
        return APP_EMOJI_CACHE
    app_id = await application_id_for(bot)
    payload = await bot.http.request(Route("GET", "/applications/{application_id}/emojis", application_id=app_id))
    refreshed: dict[str, str] = {}
    for item in _emoji_items(payload):
        name = str(item.get("name", ""))
        emoji_id = item.get("id")
        if name and emoji_id:
            refreshed[name] = f"<:{name}:{emoji_id}>"
    APP_EMOJI_CACHE.clear()
    APP_EMOJI_CACHE.update(refreshed)
    APP_EMOJI_REFRESHED_AT = time.monotonic()
    return APP_EMOJI_CACHE


async def ensure_application_emojis(bot: discord.Client | None, *, max_age: float = 120.0) -> dict[str, str]:
    global _APP_EMOJI_REFRESH_LOCK
    if bot is None:
        return APP_EMOJI_CACHE
    age = time.monotonic() - APP_EMOJI_REFRESHED_AT
    if APP_EMOJI_CACHE and age <= max_age:
        return APP_EMOJI_CACHE
    if _APP_EMOJI_REFRESH_LOCK is None:
        _APP_EMOJI_REFRESH_LOCK = asyncio.Lock()
    async with _APP_EMOJI_REFRESH_LOCK:
        age = time.monotonic() - APP_EMOJI_REFRESHED_AT
        if APP_EMOJI_CACHE and age <= max_age:
            return APP_EMOJI_CACHE
        return await refresh_application_emojis(bot)


async def upload_application_asset_emojis(bot: discord.Client, *, replace_existing: bool = False) -> dict[str, object]:
    app_id = await application_id_for(bot)
    await refresh_application_emojis(bot)
    existing_by_name = dict(APP_EMOJI_CACHE)
    uploaded = 0
    existing = 0
    replaced = 0
    failed: list[str] = []

    for kind, keys in asset_emoji_targets():
        for key in keys:
            emoji_name = emoji_asset_name(kind, key)
            current = existing_by_name.get(emoji_name)
            if current and not replace_existing:
                existing += 1
                continue

            path = asset_file_path(kind, key)
            if path is None:
                failed.append(f"{emoji_name} (file not found)")
                continue

            try:
                if current and replace_existing:
                    emoji_id = current.rsplit(":", 1)[-1].rstrip(">")
                    await bot.http.request(
                        Route("DELETE", "/applications/{application_id}/emojis/{emoji_id}", application_id=app_id, emoji_id=emoji_id)
                    )
                    replaced += 1
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                await bot.http.request(
                    Route("POST", "/applications/{application_id}/emojis", application_id=app_id),
                    json={"name": emoji_name, "image": f"data:image/png;base64,{encoded}"},
                )
                uploaded += 1
            except Exception as exc:
                failed.append(f"{emoji_name} ({exc})")

    await refresh_application_emojis(bot)
    return {"uploaded": uploaded, "existing": existing, "replaced": replaced, "failed": failed}


def custom_asset_emoji(bot: discord.Client | None, kind: str, key: str) -> str:
    app_emoji = APP_EMOJI_CACHE.get(emoji_asset_name(kind, key))
    if app_emoji:
        return app_emoji
    if bot is None:
        return ""
    emoji = discord.utils.get(bot.emojis, name=emoji_asset_name(kind, key))
    return str(emoji) if emoji else ""


def asset_file_path(kind: str, key: str):
    path = get_asset_file_path(kind, key)
    if path is not None:
        return path
    direct_path = ASSET_DIR / kind / f"{safe_key(key)}.png"
    return direct_path if direct_path.exists() and direct_path.is_file() else None


def embed_asset(kind: str, key: str) -> tuple[str | None, discord.File | None]:
    public_url = get_public_asset_url(kind, key)
    if public_url:
        return public_url, None

    path = asset_file_path(kind, key)
    if path is None:
        return None, None

    filename = f"{kind}_{safe_key(key)}.png"
    return f"attachment://{filename}", discord.File(path, filename=filename)


def asset_emoji_targets() -> list[tuple[str, list[str]]]:
    from core.rpg_data import (
        BOSSES,
        CHARMS,
        CREATURES,
        CRATE_TYPES,
        EQUIPMENT,
        MATERIALS,
        RARITIES,
        SIGILS,
        STATUS_EFFECTS,
        WEAPON_PASSIVES,
        WEAPON_TYPES,
        ZONES,
    )

    def merge_keys(kind: str, keys: list[str]) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []
        for key in keys:
            safe = safe_key(str(key))
            if safe not in seen:
                seen.add(safe)
                merged.append(safe)
        directory = ASSET_DIR / kind
        if directory.exists():
            for path in sorted(directory.glob("*.png")):
                safe = safe_key(path.stem)
                if safe not in seen:
                    seen.add(safe)
                    merged.append(safe)
        return merged

    targets = [
        ("weapons", list(WEAPON_TYPES.keys())),
        ("passives", list(WEAPON_PASSIVES.keys())),
        ("status", [effect.key for effect in STATUS_EFFECTS]),
        ("creatures", [creature.name for creature in CREATURES]),
        ("crate", list(CRATE_TYPES.keys())),
        ("consumable", ["hunt_sword"]),
        ("currency", list(CURRENCY_KEYS)),
        ("materials", list(MATERIALS.keys())),
        ("rarity", [rarity.name.lower() for rarity in RARITIES]),
        ("ui", list(UI_KEYS)),
        ("equipment", list(EQUIPMENT.keys())),
        ("buffs", [sigil.key for sigil in SIGILS] + [charm.key for charm in CHARMS]),
        ("zones", list(ZONES.keys())),
        ("bosses", [boss.key for boss in BOSSES]),
    ]
    return [(kind, merge_keys(kind, keys)) for kind, keys in targets]
