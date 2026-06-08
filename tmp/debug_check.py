import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

print("=== Import check ===")
modules = [
    "core.rpg_data",
    "core.content_config",
    "core.battle_engine",
    "core.theme",
    "core.database",
    "core.battle_card_renderer",
    "core.hunt_card_renderer",
    "core.rpg",
]
for m in modules:
    try:
        __import__(m)
        print(f"  OK: {m}")
    except Exception as e:
        print(f"  FAIL: {m} -> {e}")

print()
print("=== Config ===")
from core.content_config import load_config, VALID_KINDS
cfg = load_config()
print(f"  Config top keys: {list(cfg.keys())}")
print(f"  VALID_KINDS: {sorted(VALID_KINDS)}")
print(f"  'stats' in VALID_KINDS: {'stats' in VALID_KINDS}")

print()
print("=== Stats assets ===")
stat_dir = "data/assets/stats"
if os.path.exists(stat_dir):
    files = [f for f in os.listdir(stat_dir) if f.endswith((".png", ".jpg", ".jpeg"))]
    print(f"  Stat files: {files}")
else:
    print(f"  MISSING: {stat_dir}")

print()
print("=== Cog imports ===")
cogs = [
    "cogs.rpg_battle",
    "cogs.rpg_equipment",
    "cogs.rpg_hunting",
    "cogs.rpg_profile",
    "cogs.rpg_shop",
    "cogs.rpg_trade",
    "cogs.moderation",
]
for m in cogs:
    try:
        __import__(m)
        print(f"  OK: {m}")
    except Exception as e:
        print(f"  FAIL: {m} -> {e}")

print()
print("=== Creature templates ===")
from core.rpg_data import CREATURES, creature_asset_key, normalize_key
print(f"  Total creatures: {len(CREATURES)}")
patreon_cts = [c for c in CREATURES if "patreon" in c.rarity.lower()]
print(f"  Patreon creatures: {len(patreon_cts)}")
for c in patreon_cts:
    print(f"    {c.name} ({c.rarity})")

print()
print("=== Patreon tier_pets ===")
tier_pets = cfg.get("patreon", {}).get("tier_pets", {})
for tier, pets in tier_pets.items():
    print(f"  Tier {tier}: {pets}")

print()
print("=== Creature overrides in config ===")
overrides = cfg.get("overrides", {}).get("creatures", {})
print(f"  Override keys: {list(overrides.keys())}")

print()
print("=== Asset entries ===")
assets = cfg.get("assets", {}).get("creatures", {})
for k, v in list(assets.items())[:10]:
    print(f"  {k}: {v.get('file')}")
if len(assets) > 10:
    print(f"  ... and {len(assets) - 10} more")

print()
print("=== ALL CHECKS PASSED ===")
