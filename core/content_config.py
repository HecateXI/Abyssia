from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / os.getenv("BOT_CONTENT_CONFIG_PATH", "data/content_config.json")
ASSET_DIR = ROOT_DIR / os.getenv("BOT_ASSET_DIR", "data/assets")
VALID_KINDS = {"creatures", "equipment", "materials", "zones", "bosses", "rarity", "currency", "crate", "ui", "buffs", "weapons", "passives", "status", "consumable", "stats"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
MAX_IMAGE_BYTES = 8 * 1024 * 1024

DEFAULT_PATREON_TIERS: list[dict[str, Any]] = [
    {"tier": 1, "name": "Patron I", "description": "Entry supporter tier."},
    {"tier": 2, "name": "Patron II", "description": "Supporter tier."},
    {"tier": 3, "name": "Patron III", "description": "Premium supporter tier."},
    {"tier": 4, "name": "Patron IV", "description": "Top supporter tier."},
]

DEFAULT_BALANCING: dict[str, Any] = {
    "hunt": {
        "base_catch_rate": 0.60,
        "luck_catch_bonus": 0.015,
        "max_catch_rate": 0.95,
        "base_cooldown_seconds": 15,
        "level_cooldown_reduction": 0.10,
        "min_cooldown_seconds": 10,
        "base_crate_chance": 0.04,
        "zone_level_crate_bonus": 0.003,
        "luck_crate_bonus": 0.002,
        "max_crate_chance": 0.20,
        "autohunt_rolls_per_hour": 3,
        "autohunt_max_rolls": 48,
        "hunt_sword_duration_seconds": 1200,
        "hunt_sword_extra_rolls": 1,
        "checklist_hunt_lootbox_chance": 0.05,
        "checklist_battle_crate_chance": 0.05,
        "checklist_hunt_lootbox_target": 3,
        "checklist_battle_crate_target": 3,
    },
    "rarity": {
        "catch_rates": {
            "Common": 0.90,
            "Uncommon": 0.45,
            "Rare": 0.15,
            "Epic": 0.05,
            "Legendary": 0.02,
            "Mythic": 0.01,
            "Ancient": 0.005,
            "Patreon": 0.005,
            "Divine": 0.002,
            "Eldritch": 0.001,
            "Abyssal": 0.0005,
            "Prismatic": 0.0001,
            "Ethereal": 0.0002,
            "Void Lord": 0.00003,
            "Hidden": 0.00001,
        },
        "weights": {},
        "stat_multipliers": {},
    },
    "buffs": {
        "sigils": {},
        "charms": {},
    },
    "patreon": {
        "tiers": DEFAULT_PATREON_TIERS,
        "tier_pets": {"1": [], "2": [], "3": [], "4": []},
    },
    "weapons": {
        "quality_chances": {},
        "passive_chance": {},
        "affix_counts": [],
        "base_attack": [],
        "base_defense": [],
    },
    "economy": {
        "quests": {},
        "crate_shop": {},
    },
}


def safe_key(value: str) -> str:
    key = value.strip().lower().replace("'", "")
    key = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
    if not key:
        raise ValueError("Key cannot be empty.")
    return key[:80]


def empty_config() -> dict[str, Any]:
    return {
        "version": 1,
        "settings": {
            "public_asset_base_url": os.getenv("PUBLIC_ASSET_BASE_URL", ""),
            "auto_sync_application_emojis": True,
        },
        "balancing": copy.deepcopy(DEFAULT_BALANCING),
        "assets": {kind: {} for kind in sorted(VALID_KINDS)},
        "overrides": {kind: {} for kind in sorted(VALID_KINDS)},
        "updated_at": int(time.time()),
    }


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config() -> dict[str, Any]:
    config = empty_config()
    if CONFIG_PATH.exists():
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config.update({key: value for key, value in loaded.items() if key not in {"assets", "overrides", "settings", "balancing"}})
                config["settings"].update(loaded.get("settings") or {})
                loaded_balancing = loaded.get("balancing") or {}
                if isinstance(loaded_balancing, dict):
                    config["balancing"] = _deep_merge(config["balancing"], loaded_balancing)
                for group in ("assets", "overrides"):
                    for kind, values in (loaded.get(group) or {}).items():
                        if kind in VALID_KINDS and isinstance(values, dict):
                            config[group][kind].update(values)
        except json.JSONDecodeError:
            backup = CONFIG_PATH.with_suffix(".invalid.json")
            CONFIG_PATH.replace(backup)
    return config


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config["updated_at"] = int(time.time())
    tmp_path = CONFIG_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(CONFIG_PATH)


def validate_kind(kind: str) -> str:
    if kind not in VALID_KINDS:
        raise ValueError(f"Unsupported kind: {kind}")
    return kind


def set_override(kind: str, key: str, patch: dict[str, Any]) -> dict[str, Any]:
    kind = validate_kind(kind)
    key = safe_key(key)
    config = load_config()
    current = config["overrides"][kind].get(key, {})
    if not isinstance(current, dict):
        current = {}
    current.update(patch)
    config["overrides"][kind][key] = current
    save_config(config)
    return current


def clear_override(kind: str, key: str) -> None:
    kind = validate_kind(kind)
    key = safe_key(key)
    config = load_config()
    config["overrides"][kind].pop(key, None)
    save_config(config)


def set_public_asset_base_url(value: str) -> None:
    config = load_config()
    config["settings"]["public_asset_base_url"] = value.strip().rstrip("/")
    save_config(config)


def set_setting(key: str, value: Any) -> dict[str, Any]:
    config = load_config()
    config["settings"][str(key)] = value
    save_config(config)
    return config["settings"]


def get_balancing() -> dict[str, Any]:
    return load_config().get("balancing", copy.deepcopy(DEFAULT_BALANCING))


def set_balancing(patch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(patch, dict):
        raise ValueError("balancing patch must be an object.")
    config = load_config()
    config["balancing"] = _deep_merge(config.get("balancing", {}), patch)
    save_config(config)
    return config["balancing"]


def balancing_value(path: str, fallback: Any) -> Any:
    current: Any = get_balancing()
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return fallback
        current = current[part]
    return current


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _asset_file(kind: str, key: str, ext: str = ".png") -> Path:
    return ASSET_DIR / validate_kind(kind) / f"{safe_key(key)}{ext}"


def set_asset_from_data_url(kind: str, key: str, data_url: str) -> dict[str, Any]:
    kind = validate_kind(kind)
    key = safe_key(key)
    if "," not in data_url:
        raise ValueError("Invalid data URL.")
    header, encoded = data_url.split(",", 1)
    if not header.lower().startswith("data:") or "base64" not in header.lower():
        raise ValueError("Upload must be a base64 data URL.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid image upload data.") from exc
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 8 MB or smaller.")
    if raw.startswith(PNG_SIGNATURE):
        ext = ".png"
    elif raw[:3] == JPEG_SIGNATURE:
        ext = ".jpg"
    else:
        raise ValueError("Uploaded file is not a valid PNG or JPEG.")

    path = _asset_file(kind, key, ext)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)

    config = load_config()
    record = {
        "file": f"{kind}/{path.name}",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "updated_at": int(time.time()),
    }
    config["assets"][kind][key] = record
    save_config(config)
    return record


def set_asset_url(kind: str, key: str, url: str) -> dict[str, Any]:
    kind = validate_kind(kind)
    key = safe_key(key)
    if not (url.startswith("https://") or url.startswith("http://")):
        raise ValueError("Asset URL must start with http:// or https://.")
    config = load_config()
    record = {"url": url.strip(), "updated_at": int(time.time())}
    config["assets"][kind][key] = record
    save_config(config)
    return record


def clear_asset(kind: str, key: str) -> None:
    kind = validate_kind(kind)
    key = safe_key(key)
    config = load_config()
    record = config["assets"][kind].pop(key, None)
    if isinstance(record, dict) and record.get("file"):
        path = ASSET_DIR / str(record["file"])
        if path.exists() and path.is_file() and ASSET_DIR in path.resolve().parents:
            path.unlink()
    save_config(config)


def get_asset_record(kind: str, key: str) -> dict[str, Any] | None:
    config = load_config()
    record = config["assets"].get(kind, {}).get(safe_key(key))
    return record if isinstance(record, dict) else None


def get_asset_file_path(kind: str, key: str) -> Path | None:
    kind = validate_kind(kind)
    safe = safe_key(key)
    record = get_asset_record(kind, key)
    if record and record.get("file"):
        path = (ASSET_DIR / str(record["file"])).resolve()
        if path.exists() and path.is_file() and ASSET_DIR.resolve() in path.parents:
            return path
    for ext in (".png", ".jpg", ".jpeg"):
        direct = (ASSET_DIR / kind / f"{safe}{ext}").resolve()
        if direct.exists() and direct.is_file() and ASSET_DIR.resolve() in direct.parents:
            return direct
    return None


INFUSED_PREFIXES = ("Ruby", "Emerald", "Sapphire", "Diamond", "Abyssal")


def get_creature_asset_path(key: str) -> Path | None:
    """Look up a creature asset, falling back to base name for infused variants."""
    path = get_asset_file_path("creatures", key)
    if path:
        return path
    for prefix in INFUSED_PREFIXES:
        if key.startswith(prefix.lower() + "_"):
            base_key = key[len(prefix) + 1:]
            path = get_asset_file_path("creatures", base_key)
            if path:
                return path
            base_file = ASSET_DIR / "creatures" / f"{base_key}.png"
            if base_file.exists():
                return base_file
            break
    for ext in (".png", ".jpg", ".jpeg"):
        direct = ASSET_DIR / "creatures" / f"{key}{ext}"
        if direct.exists():
            return direct
    return None


def get_public_asset_url(kind: str, key: str) -> str | None:
    record = get_asset_record(kind, key)
    if not record:
        return None
    if record.get("url"):
        return str(record["url"])
    if not record.get("file"):
        return None
    config = load_config()
    base_url = str(config.get("settings", {}).get("public_asset_base_url") or os.getenv("PUBLIC_ASSET_BASE_URL", "")).strip().rstrip("/")
    if not base_url:
        return None
    url = f"{base_url}/assets/{record['file']}"
    updated_at = record.get("updated_at")
    return f"{url}?v={updated_at}" if updated_at else url


def asset_preview_url(kind: str, key: str) -> str | None:
    record = get_asset_record(kind, key)
    if record and record.get("url"):
        return str(record["url"])
    if record and record.get("file"):
        updated_at = record.get("updated_at")
        url = f"/assets/{record['file']}"
        return f"{url}?v={updated_at}" if updated_at else url
    path = get_asset_file_path(kind, key)
    if path:
        try:
            relative = path.resolve().relative_to(ASSET_DIR.resolve()).as_posix()
        except ValueError:
            return None
        updated_at = int(path.stat().st_mtime)
        return f"/assets/{relative}?v={updated_at}"
    return None
