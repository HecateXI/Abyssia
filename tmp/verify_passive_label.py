import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.theme import passive_label, rarity_emoji
from core.rpg_data import WEAPON_PASSIVES, RARITIES

print("=== passive_label tests ===")
print(f"  strength (no chance): {passive_label('strength')}")
print(f"  strength (20%): {passive_label('strength', None, 20)}")
print(f"  rare_finder (5%): {passive_label('rare_finder', None, 5)}")
print(f"  sacrifice (35%): {passive_label('sacrifice', None, 35)}")

print()
print("=== Rarity emojis ===")
for r in RARITIES:
    emoji = rarity_emoji(r.name)
    print(f"  {r.name}: {repr(emoji)}")

print()
print("=== Import check ===")
import core.theme
import cogs.rpg_equipment
print("  All imports OK")

print()
print("ALL CHECKS PASSED")
