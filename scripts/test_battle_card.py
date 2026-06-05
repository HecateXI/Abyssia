"""Test script for the new BattleCardRenderer."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.battle_card_renderer import BattleCardRenderer


def make_creature(name, rarity, attack, defense, hp, speed=20, crit=10, mana=50, ability="Blood Pact", level=30, value=1000):
    return {
        "name": name, "rarity": rarity, "attack": attack, "defense": defense,
        "hp": hp, "speed": speed, "crit": crit, "mana": mana,
        "ability": ability, "level": level, "value": value,
    }


def main():
    renderer = BattleCardRenderer()

    left_team = [
        make_creature("Soulreaper Wyvern", "Mythic", 580, 320, 4200, ability="Soul Drain", level=45, mana=80),
        make_creature("Bloodmoon Drake", "Epic", 420, 280, 3400, ability="Infernal Rage", level=38),
        make_creature("Bone Stalker", "Rare", 310, 220, 2600, ability="Shadow Cloak", level=32),
    ]
    right_team = [
        make_creature("Void Emperor", "Abyssal", 720, 440, 5800, ability="Abyssal Howl", level=60, mana=100),
        make_creature("Abyssal Godling", "Abyssal", 640, 380, 4900, ability="Void Corruption", level=52),
        make_creature("Black Chalice Hydra", "Mythic", 560, 360, 5100, ability="Soul Drain", level=48),
    ]

    # ── Standard victory ──
    std_data = {
        "won": True,
        "winner_name": "Darren",
        "loser_name": "VoidLord",
        "player_name": "Darren",
        "enemy_name": "VoidLord",
        "player_team": left_team,
        "enemy_team": right_team,
        "player_hp": [1800, 1200, 800],
        "enemy_hp": [0, 0, 900],
        "player_rating": 1560,
        "enemy_rating": 1420,
        "player_rank": "Gold Hunter",
        "enemy_rank": "Silver Hunter",
        "rating_change": 24,
        "win_streak": 12,
        "zone_key": "bloodmoon_forest",
        "has_ultra_rare": True,
        "damage_stats": {
            "player_damage_dealt": 12582,
            "player_damage_taken": 7340,
            "player_crits": 18,
            "player_status_applied": 9,
        },
        "mvp": {"name": "Soulreaper Wyvern", "damage": 7221, "kills": 2},
        "player_weapons": [
            {"name": "Soulreaper", "rarity": "Legendary"},
            {"name": "Abyssal Cleaver", "rarity": "Abyssal"},
            {"name": "Bloodfang Greatsword", "rarity": "Epic"},
        ],
        "log": [
            "Turn 1: Soulreaper Wyvern used Skill CRIT for 823 damage.",
            "Turn 2: Void Emperor used Ultimate on Soulreaper for 1450 damage.",
            "Turn 3: Abyssal Godling inflicted Bleed on Bloodmoon Drake.",
            "Turn 7: Soulreaper Wyvern activated Ultimate CRIT for 2100 damage.",
            "Turn 12: Soulreaper Wyvern defeated Void Emperor.",
            "Turn 15: Enemy team defeated. Victory!",
        ],
    }

    buf = renderer.render_battle_result(std_data)
    out = ROOT_DIR / "test_battle_result.png"
    out.write_bytes(buf.getvalue())
    print(f"Battle result saved: {out}")

    # ── Defeat (no ultra) ──
    defeat_data = dict(std_data)
    defeat_data["won"] = False
    defeat_data["winner_name"] = "VoidLord"
    defeat_data["loser_name"] = "Darren"
    defeat_data["player_hp"] = [0, 0, 100]
    defeat_data["enemy_hp"] = [1500, 800, 2400]
    defeat_data["rating_change"] = -18
    defeat_data["win_streak"] = 0
    defeat_data["has_ultra_rare"] = False
    defeat_data["mvp"] = {"name": "Bone Stalker", "damage": 3200, "kills": 1}

    buf2 = renderer.render_battle_result(defeat_data)
    out2 = ROOT_DIR / "test_battle_defeat.png"
    out2.write_bytes(buf2.getvalue())
    print(f"Battle defeat saved: {out2}")

    # ── Animation frame ──
    frame_data = {
        "turn": 5,
        "player_name": "Darren",
        "enemy_name": "VoidLord",
        "player_team": left_team,
        "enemy_team": right_team,
        "player_hp": [2800, 1500, 900],
        "enemy_hp": [3100, 0, 1800],
        "zone_key": "bloodmoon_forest",
        "log": [
            "Turn 4: Soulreaper Wyvern used Ultimate on Void Emperor for 1850 damage.",
            "Turn 5: Void Emperor used Skill CRIT on Bloodmoon Drake for 1200 damage.",
        ],
    }

    buf3 = renderer.render_battle_frame(frame_data)
    out3 = ROOT_DIR / "test_battle_frame.png"
    out3.write_bytes(buf3.getvalue())
    print(f"Battle frame saved: {out3}")


if __name__ == "__main__":
    main()
