import json
from pathlib import Path
from core.hunt_card_renderer import HuntCardRenderer

renderer = HuntCardRenderer()

def create_test_data(count, title="Test"):
    monsters = []
    rarities = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]
    for i in range(count):
        rarity = rarities[min(i, len(rarities)-1)]
        monsters.append({
            "name": f"Test Monster {i+1}",
            "rarity": rarity,
            "value": (i+1) * 100,
            "collection_status": "NEW DISCOVERY" if i % 2 == 0 else "DUPLICATE"
        })
        
    # shuffle so rarest isn't always first or last
    import random
    random.shuffle(monsters)

    return {
        "hunter_name": "Test Hunter",
        "hunter_rank": "Grandmaster Hunter",
        "zone_name": "Bloodmoon Forest",
        "zone_key": "bloodmoon_forest",
        "monsters": monsters,
        "total_souls": sum(m["value"] for m in monsters),
        "rewards": [
            {"label": "Souls", "amount": 1500, "color": (235, 195, 80)},
            {"label": "Corrupted Essence", "amount": 14, "color": (80, 210, 120)},
            {"label": "Void Crystals", "amount": 3, "color": (80, 210, 120)}
        ],
        "special_drop": {
            "type": "weapon",
            "name": "Soulreaper",
            "rarity": "Legendary"
        }
    }

for count in [3, 8, 15]:
    print(f"Rendering {count} monsters...")
    data = create_test_data(count)
    buf = renderer.render_multi_hunt_card(data)
    with open(f"test_multihunt_{count}.png", "wb") as f:
        f.write(buf.read())
        
print("Done!")
