from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.rpg_data import CREATURES, RARITIES, normalize_key


ASSET_DIR = ROOT_DIR / "data" / "assets"
EXPECTED_SIZE = (64, 64)


def required_files() -> list[tuple[str, str]]:
    files = [(f"rarity/{rarity.name.lower()}.png", f"Rarity: {rarity.name}") for rarity in RARITIES]
    files.extend((f"creatures/{normalize_key(creature.name)}.png", f"Creature: {creature.name}") for creature in CREATURES)
    return files


def verify_assets() -> bool:
    errors: list[str] = []
    success_count = 0

    print("Verifying 64x64 rarity and creature assets...")
    for rel_path, label in required_files():
        path = ASSET_DIR / rel_path
        if not path.exists():
            errors.append(f"MISSING: {label} ({rel_path})")
            continue

        try:
            with Image.open(path) as img:
                if img.size != EXPECTED_SIZE:
                    errors.append(f"INVALID SIZE {img.size}: {label} ({rel_path})")
                    continue
                if img.format != "PNG":
                    errors.append(f"INVALID FORMAT {img.format}: {label} ({rel_path})")
                    continue
                if img.mode != "RGBA":
                    errors.append(f"INVALID MODE {img.mode}: {label} ({rel_path})")
                    continue
                if not img.getbbox():
                    errors.append(f"BLANK IMAGE: {label} ({rel_path})")
                    continue
                success_count += 1
        except Exception as exc:
            errors.append(f"ERROR OPENING: {label} ({rel_path}) - {exc}")

    print(f"\nVerification Results: {success_count}/{len(required_files())} passed.")
    if errors:
        print("\nERRORS FOUND:")
        for error in errors:
            print(f" - {error}")
        return False

    print("ALL RARITY AND CREATURE ICONS VERIFIED: 64x64 transparent PNGs.")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if verify_assets() else 1)
