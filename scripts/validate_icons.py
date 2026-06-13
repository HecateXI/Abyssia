"""Validate Abyssia icon prompts, local icon files, emoji names, and fallback loading."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPTS_PATH = ROOT_DIR / "data" / "icon_prompts.json"
EMOJI_MAP_PATH = ROOT_DIR / "data" / "emoji_map.json"
DISCORD_NAME_RE = re.compile(r"^[A-Za-z0-9_]{2,32}$")
DISCORD_CUSTOM_RE = re.compile(r"^<a?:[A-Za-z0-9_]{2,32}:[0-9]{15,25}>$")


def _load_prompts() -> list[dict[str, Any]]:
    if not PROMPTS_PATH.exists():
        return []
    payload = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    records = payload.get("records", []) if isinstance(payload, dict) else []
    return [item for item in records if isinstance(item, dict)]


def _load_emoji_map() -> dict[str, str]:
    if not EMOJI_MAP_PATH.exists():
        return {}
    try:
        payload = json.loads(EMOJI_MAP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            result[str(key)] = value
        elif isinstance(value, dict):
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, str):
                    result[str(nested_key)] = nested_value
    return result


def _png_size(path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as image:
            if image.format != "PNG":
                return None
            return image.size
    except OSError:
        return None


def _has_transparent_corners(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            rgba = image.convert("RGBA")
            corners = (
                rgba.getpixel((0, 0))[3],
                rgba.getpixel((rgba.width - 1, 0))[3],
                rgba.getpixel((0, rgba.height - 1))[3],
                rgba.getpixel((rgba.width - 1, rgba.height - 1))[3],
            )
            return all(alpha == 0 for alpha in corners)
    except OSError:
        return False


def _expected_keys() -> dict[str, set[str]]:
    sys.path.insert(0, str(ROOT_DIR))
    from core.rpg_data import WEAPON_PASSIVES, WEAPON_TYPES

    return {
        "weapons": set(WEAPON_TYPES.keys()),
        "passives": set(WEAPON_PASSIVES.keys()),
    }


def _check_fallback(errors: list[str]) -> None:
    sys.path.insert(0, str(ROOT_DIR))
    try:
        from core.theme import emoji_for
    except Exception as exc:
        errors.append(f"Could not import core.theme.emoji_for: {exc}")
        return
    if emoji_for("__missing_icon__", fallback="") != "":
        errors.append("emoji_for missing-key empty fallback did not return an empty string.")
    if emoji_for("__missing_icon__", fallback="?") != "?":
        errors.append("emoji_for missing-key explicit fallback did not return the fallback.")


def validate(*, strict_assets: bool, strict_map: bool, strict_transparency: bool) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    records = _load_prompts()
    if not records:
        errors.append("data/icon_prompts.json is missing or has no records. Run scripts/generate_icon_prompts.py.")
        print_report(errors, warnings)
        return 1

    by_category: dict[str, dict[str, dict[str, Any]]] = {"weapons": {}, "passives": {}}
    for record in records:
        category = str(record.get("category", ""))
        key = str(record.get("key", ""))
        if category in by_category and key:
            by_category[category][key] = record

    for category, expected in _expected_keys().items():
        present = set(by_category[category])
        for missing in sorted(expected - present):
            errors.append(f"Missing prompt record for {category}/{missing}.")
        for extra in sorted(present - expected):
            warnings.append(f"Prompt record has no matching bot key: {category}/{extra}.")

    emoji_map = _load_emoji_map()
    if not emoji_map:
        warnings.append("data/emoji_map.json is empty or missing. Run scripts/sync_emojis.py after Discord upload.")

    for record in records:
        category = str(record.get("category", ""))
        key = str(record.get("key", ""))
        emoji_name = str(record.get("emoji_name", ""))
        display_name = str(record.get("display_name", key))
        expected_prefix = "weapon" if category == "weapons" else "passive"
        expected_emoji_name = f"{expected_prefix}_{key}"

        for required_field in ("key", "display_name", "category", "concept", "palette", "output_path", "emoji_name", "prompt", "negative_prompt"):
            if not record.get(required_field):
                errors.append(f"{category}/{key} is missing field {required_field}.")

        if emoji_name != expected_emoji_name:
            errors.append(f"{category}/{key} emoji_name is {emoji_name}, expected {expected_emoji_name}.")
        if not DISCORD_NAME_RE.match(emoji_name):
            errors.append(f"{category}/{key} emoji name is invalid for Discord: {emoji_name}.")

        master_path = ROOT_DIR / "assets" / "icons" / category / f"{key}.png"
        emoji_path = ROOT_DIR / "assets" / "emojis" / category / f"{key}.png"
        master_exists = master_path.exists()

        if not master_exists:
            message = f"Missing 512x512 master icon for {display_name}: {master_path.relative_to(ROOT_DIR)}"
            if strict_assets:
                errors.append(message)
            else:
                warnings.append(message)
        else:
            size = _png_size(master_path)
            if size != (512, 512):
                errors.append(f"Master icon {master_path.relative_to(ROOT_DIR)} is {size}, expected (512, 512).")
            if not _has_transparent_corners(master_path):
                message = f"Master icon may not have transparent corners: {master_path.relative_to(ROOT_DIR)}"
                if strict_transparency:
                    errors.append(message)
                else:
                    warnings.append(message)

        if not emoji_path.exists():
            message = f"Missing 128x128 emoji file for {display_name}: {emoji_path.relative_to(ROOT_DIR)}"
            if strict_assets or master_exists:
                errors.append(message)
            else:
                warnings.append(message)
        else:
            size = _png_size(emoji_path)
            if size != (128, 128):
                errors.append(f"Emoji PNG {emoji_path.relative_to(ROOT_DIR)} is {size}, expected (128, 128).")

        map_value = emoji_map.get(emoji_name, "")
        if not map_value:
            message = f"emoji_map is missing {emoji_name}; run scripts/sync_emojis.py after upload."
            if strict_map:
                errors.append(message)
            else:
                warnings.append(message)
        elif not DISCORD_CUSTOM_RE.match(map_value):
            errors.append(f"emoji_map value for {emoji_name} is not a Discord custom emoji string.")

    _check_fallback(errors)
    print_report(errors, warnings)
    return 1 if errors else 0


def print_report(errors: list[str], warnings: list[str]) -> None:
    print("Icon validation")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    for label, items in (("ERROR", errors), ("WARN", warnings)):
        for item in items[:80]:
            print(f"{label}: {item}")
        if len(items) > 80:
            print(f"{label}: ... and {len(items) - 80} more")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-assets", action="store_true", help="Fail when any master or emoji PNG is missing.")
    parser.add_argument("--strict-map", action="store_true", help="Fail when any emoji_map entry is missing.")
    parser.add_argument("--strict-transparency", action="store_true", help="Fail when master PNG corners are opaque.")
    args = parser.parse_args()
    return validate(strict_assets=args.strict_assets, strict_map=args.strict_map, strict_transparency=args.strict_transparency)


if __name__ == "__main__":
    raise SystemExit(main())
