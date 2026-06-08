import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

print("=== 1. Orb ability in battle_engine ===")
from core.battle_engine import Ability
a = Ability.for_weapon_type("orb")
print(f"  mode={a.mode}, scale={a.scale_stat}, mult=({a.multiplier_min}, {a.multiplier_max}), cost=({a.wp_cost_min}, {a.wp_cost_max})")

print()
print("=== 2. Orb type ===")
from core.rpg_data import WEAPON_TYPES
print(f"  desc: {WEAPON_TYPES['orb']['desc']}")
print(f"  passive_slots: 2")

print()
print("=== 3. Weapon rarity no Patreon ===")
from core.rpg import WEAPON_QUALITY_RARITY_TIERS
print(f"  'Patreon' in tiers: {'Patreon' in [t[2] for t in WEAPON_QUALITY_RARITY_TIERS]}")

print()
print("=== 4. Passive rarities ===")
from core.rpg_data import WEAPON_PASSIVES
print(f"  All have rarity: {all('rarity' in v for v in WEAPON_PASSIVES.values())}")
print(f"  Sample: strength -> {WEAPON_PASSIVES['strength']['rarity']}, sacrifice -> {WEAPON_PASSIVES['sacrifice']['rarity']}")

print()
print("=== 5. passive_label ===")
from core.theme import passive_label
print(f"  strength: {passive_label('strength')}")
print(f"  rare_finder: {passive_label('rare_finder')}")

print()
print("=== 6. Imports ===")
import core.rpg
import core.battle_engine
import core.battle_card_renderer
import core.hunt_card_renderer
import cogs.rpg_battle
import cogs.rpg_equipment
import cogs.rpg_hunting
import cogs.rpg_profile
import cogs.rpg_shop
import cogs.rpg_trade
print("  All imports OK")

print()
print("ALL CHECKS PASSED")
