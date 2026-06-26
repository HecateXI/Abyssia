"""Validate Abyssia card UI assets, manifest, and preview rendering."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPTS_PATH = ROOT_DIR / "data" / "card_asset_prompts.json"
MANIFEST_PATH = ROOT_DIR / "data" / "card_asset_manifest.json"
PREVIEW_DIR = ROOT_DIR / "tmp" / "card_previews"

REQUIRED_PREVIEWS = (
    "weapon_vault.png",
    "hunt_result_6.png",
    "hunt_result_15.png",
    "crate_shop.png",
    "weapon_detail.png",
    "battle_card.png",
    "bestiary_page.png",
    "profile_card.png",
    "all_cards_contact_sheet.png",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_manifest(manifest: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    categories = manifest.get("categories", {})
    if not isinstance(categories, dict):
        return out
    for category, records in categories.items():
        if not isinstance(records, dict):
            continue
        for key, record in records.items():
            if isinstance(record, dict):
                out[(str(category), str(key))] = record
    return out


def validate_assets() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not PROMPTS_PATH.exists():
        errors.append(f"missing {PROMPTS_PATH.relative_to(ROOT_DIR)}")
        return errors, warnings
    if not MANIFEST_PATH.exists():
        errors.append(f"missing {MANIFEST_PATH.relative_to(ROOT_DIR)}")
        return errors, warnings

    prompts = load_json(PROMPTS_PATH)
    manifest = load_json(MANIFEST_PATH)
    records = [item for item in prompts.get("records", []) if isinstance(item, dict)]
    index = flatten_manifest(manifest)

    for folder in prompts.get("required_folders", []):
        path = ROOT_DIR / str(folder)
        if not path.is_dir():
            errors.append(f"missing required folder {folder}")

    for record in records:
        category = str(record.get("category", ""))
        key = str(record.get("key", ""))
        expected_size = tuple(int(v) for v in record.get("size", [0, 0]))
        expected_transparent = bool(record.get("transparent", False))
        manifest_entry = index.get((category, key))
        if manifest_entry is None:
            errors.append(f"missing manifest entry {category}/{key}")
            continue
        path = ROOT_DIR / str(manifest_entry.get("path", ""))
        if not path.exists():
            errors.append(f"missing asset file {manifest_entry.get('path')}")
            continue
        try:
            with Image.open(path) as image:
                image.load()
                if image.size != expected_size:
                    errors.append(f"{category}/{key} has size {image.size}, expected {expected_size}")
                if expected_transparent and image.mode not in {"RGBA", "LA"}:
                    errors.append(f"{category}/{key} expected alpha but mode is {image.mode}")
                if expected_transparent and image.convert("RGBA").getchannel("A").getextrema()[0] >= 255:
                    warnings.append(f"{category}/{key} is marked transparent but has no transparent pixels")
        except OSError as exc:
            errors.append(f"cannot open {path.relative_to(ROOT_DIR)}: {exc}")

    source = (ROOT_DIR / "core" / "cards.py").read_text(encoding="utf-8")
    if "if value != 0" not in source:
        warnings.append("could not confirm zero weapon stat boxes are filtered")
    if "draw_text_fit" not in source:
        warnings.append("could not confirm fitted text helpers are used")
    return errors, warnings


def validate_previews(*, render: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if render:
        result = subprocess.run(
            [sys.executable, "scripts/render_card_previews.py"],
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append("render_card_previews.py failed")
            errors.extend(line for line in result.stdout.splitlines()[-20:] if line.strip())
            return errors, warnings
    for name in REQUIRED_PREVIEWS:
        path = PREVIEW_DIR / name
        if not path.exists():
            errors.append(f"missing preview {path.relative_to(ROOT_DIR)}")
            continue
        try:
            with Image.open(path) as image:
                image.verify()
        except OSError as exc:
            errors.append(f"invalid preview {name}: {exc}")
    if not (PREVIEW_DIR / "long_name_truncation_test.png").exists():
        warnings.append("long-name truncation preview missing")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-previews", action="store_true", help="Run scripts/render_card_previews.py before checking previews.")
    args = parser.parse_args()

    errors, warnings = validate_assets()
    preview_errors, preview_warnings = validate_previews(render=args.render_previews)
    errors.extend(preview_errors)
    warnings.extend(preview_warnings)

    print("Card asset validation")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    for error in errors:
        print(f"ERROR: {error}")
    for warning in warnings:
        print(f"WARN: {warning}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
