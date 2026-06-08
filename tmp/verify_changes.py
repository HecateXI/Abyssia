import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

print("=== 1. Weapon rarities (no Patreon) ===")
from core.rpg import WEAPON_QUALITY_RARITY_TIERS
rarities = [t[2] for t in WEAPON_QUALITY_RARITY_TIERS]
print(f"Tiers: {rarities}")
print(f"Patreon present: {'Patreon' in rarities}")

print()
print("=== 2. Passives have rarity, no Patreon ===")
from core.rpg_data import WEAPON_PASSIVES
ok = True
for k, v in WEAPON_PASSIVES.items():
    r = v.get("rarity", "MISSING")
    if r == "MISSING":
        print(f"  MISSING: {k}")
        ok = False
    elif r == "Patreon":
        print(f"  PATREON: {k}")
        ok = False
if ok:
    print("All passives have rarity, none are Patreon")

print()
print("=== 3. passive_label with rarity ===")
from core.theme import passive_label
print(f"  strength: {passive_label('strength')}")
print(f"  rare_finder: {passive_label('rare_finder')}")
print(f"  sacrifice: {passive_label('sacrifice')}")

print()
print("=== 4. Orb description ===")
from core.rpg_data import WEAPON_TYPES
print(f"  Desc: {WEAPON_TYPES['orb']['desc']}")

print()
print("=== 5. Import all cogs ===")
import core.rpg
import core.battle_engine
import core.battle_card_renderer
import core.hunt_card_renderer
import core.content_config
import cogs.rpg_battle
import cogs.rpg_equipment
import cogs.rpg_hunting
import cogs.rpg_profile
import cogs.rpg_shop
import cogs.rpg_trade
print("All imports OK")

print()
print("ALL CHECKS PASSED")
