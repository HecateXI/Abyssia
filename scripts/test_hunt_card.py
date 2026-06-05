"""Quick test script for hunt card renderer."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.hunt_card_renderer import HuntCardRenderer
from core.rpg_data import normalize_key


def main():
    renderer = HuntCardRenderer()

    test_data = {
        "hunter_name": "Darren",
        "hunter_rank": "Rank 42 Hunter",
        "hunt_streak": 187,
        "zone_name": "Bloodmoon Forest",
        "zone_key": "bloodmoon_forest",
        "monster": {
            "name": "Shadow Drake",
            "level": 37,
            "rarity": "Epic",
            "trait": "Ancient",
            "value": 2450,
        },
        "collection_status": "NEW DISCOVERY",
        "rewards": [
            {"label": "Souls", "amount": 125, "icon_key": "souls", "color": (235, 195, 80)},
            {"label": "Corrupted Essence", "amount": 2, "icon_key": "corrupted_essence", "color": (80, 210, 120)},
            {"label": "Void Crystal", "amount": 1, "icon_key": "void_crystals", "color": (70, 160, 235)},
            {"label": "XP", "amount": 350, "color": (55, 225, 210)},
        ],
        "special_drop": {
            "type": "weapon",
            "name": "Soulreaper",
            "rarity": "Legendary",
        },
        "catch_chance": 100.0,
        "rarity_chance": 0.08,
    }

    buf = renderer.render_hunt_card(test_data)

    out_path = ROOT_DIR / "test_hunt_card_output.png"
    out_path.write_bytes(buf.getvalue())
    print(f"Standard card saved to: {out_path}")

    ultra_data = dict(test_data)
    ultra_data["monster"] = {
        "name": "Void Emperor",
        "level": 99,
        "rarity": "Abyssal",
        "trait": "Primordial",
        "value": 50000,
        "encounter_rate": "0.0001",
    }
    ultra_data["zone_name"] = "Void Realm"
    ultra_data["zone_key"] = "void_realm"
    ultra_data["collection_status"] = "NEW DISCOVERY"
    ultra_data["catch_chance"] = 0.01

    buf2 = renderer.render_hunt_card(ultra_data)

    out_path2 = ROOT_DIR / "test_hunt_card_abyssal.png"
    out_path2.write_bytes(buf2.getvalue())
    print(f"Abyssal card saved to: {out_path2}")

    epic_data = dict(test_data)
    epic_data["monster"] = {
        "name": "Soulreaper Wyvern",
        "level": 45,
        "rarity": "Mythic",
        "trait": "Eternal",
        "value": 12000,
    }
    epic_data["collection_status"] = "NEW DISCOVERY"
    epic_data["special_drop"] = {
        "type": "relic",
        "name": "Ancient Relic Cache",
        "rarity": "Mythic",
    }

    buf3 = renderer.render_hunt_card(epic_data)
    out_path3 = ROOT_DIR / "test_hunt_card_mythic.png"
    out_path3.write_bytes(buf3.getvalue())
    print(f"Mythic card saved to: {out_path3}")

    boss_test = dict(test_data)
    boss_test["monster"] = {
        "name": "The Hollow King",
        "level": 60,
        "rarity": "Legendary",
        "trait": "Sovereign",
        "value": 25000,
    }
    buf4 = renderer.render_boss_variant(boss_test)
    out_path4 = ROOT_DIR / "test_hunt_card_boss.png"
    out_path4.write_bytes(buf4.getvalue())
    print(f"Boss card saved to: {out_path4}")


if __name__ == "__main__":
    main()
