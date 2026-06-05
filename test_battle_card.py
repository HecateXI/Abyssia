import json
from pathlib import Path
from core.battle_card_renderer import BattleCardRenderer

renderer = BattleCardRenderer()

def create_test_battle():
    player_team = [
        {"name": "Shadow Fiend", "rarity": "Epic", "level": 32, "attack": 45, "defense": 30, "speed": 40, "hp": 1200, "_weapon": {"name": "Demon Blade", "rarity": "Rare"}},
        {"name": "Void Stalker", "rarity": "Legendary", "level": 30, "attack": 60, "defense": 20, "speed": 65, "hp": 900, "_weapon": {"name": "Shadow Dagger", "rarity": "Epic"}},
    ]
    enemy_team = [
        {"name": "Abyssal Horror", "rarity": "Mythic", "level": 35, "attack": 70, "defense": 50, "speed": 35, "hp": 2500, "_weapon": {"name": "Bone Crusher", "rarity": "Legendary"}},
        {"name": "Corrupted Wolf", "rarity": "Common", "level": 30, "attack": 30, "defense": 20, "speed": 50, "hp": 800},
        {"name": "Corrupted Wolf", "rarity": "Common", "level": 30, "attack": 30, "defense": 20, "speed": 50, "hp": 800},
    ]
    player_hp = [450, 0] # Second one dead
    enemy_hp = [2100, 300, 800]
    
    return {
        "zone_key": "abyssal_depths",
        "has_ultra_rare": False,
        "player_team": player_team,
        "enemy_team": enemy_team,
        "player_hp": player_hp,
        "enemy_hp": enemy_hp,
    }

if __name__ == "__main__":
    data = create_test_battle()
    img_data = renderer.render_battle_result(data)
    
    out_path = Path("test_battle_compact.png")
    out_path.write_bytes(img_data.getvalue())
    print("Saved to", out_path)
