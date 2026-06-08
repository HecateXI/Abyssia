"""Check emoji names in Discord."""
import asyncio
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Load .env
env_path = ROOT_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

import aiohttp

NEW_WEAPONS = ["soulreaper", "final_bell_scythe", "briar_relic", "rot_chalice", "banner", "eye", "judgement_blade", "lantern", "mirror_relic"]
NEW_PASSIVES = ["life_steal", "mana_tap", "soul_gain", "gem_finder", "xp_boost", "rare_finder", "energize", "fear"]
NEW_STATS = ["hp", "str", "def", "mana", "mag", "res", "spd"]

async def main():
    token = os.environ.get("DISCORD_TOKEN")
    async with aiohttp.ClientSession() as session:
        async with session.get("https://discord.com/api/v10/oauth2/applications/@me", headers={"Authorization": f"Bot {token}"}) as resp:
            app = await resp.json()
            app_id = app["id"]
        
        emoji_url = f"https://discord.com/api/v10/applications/{app_id}/emojis"
        async with session.get(emoji_url, headers={"Authorization": f"Bot {token}"}) as resp:
            emojis = await resp.json()
            emoji_list = emojis if isinstance(emojis, list) else emojis.get("items", [])
            
            print("=== WEAPON EMOJIS ===")
            for w in NEW_WEAPONS:
                name = f"weapon_{w}"
                found = [e for e in emoji_list if e["name"] == name]
                if found:
                    e = found[0]
                    emoji_str = f"<:{name}:{e['id']}>"
                    print(f"{name}: {emoji_str}")
                else:
                    print(f"{name}: NOT FOUND")
            
            print()
            print("=== PASSIVE EMOJIS ===")
            for p in NEW_PASSIVES:
                name = f"passive_{p}"
                found = [e for e in emoji_list if e["name"] == name]
                if found:
                    e = found[0]
                    emoji_str = f"<:{name}:{e['id']}>"
                    print(f"{name}: {emoji_str}")
                else:
                    print(f"{name}: NOT FOUND")
            
            print()
            print("=== STAT EMOJIS ===")
            for s in NEW_STATS:
                name = f"stat_{s}"
                found = [e for e in emoji_list if e["name"] == name]
                if found:
                    e = found[0]
                    emoji_str = f"<:{name}:{e['id']}>"
                    print(f"{name}: {emoji_str}")
                else:
                    print(f"{name}: NOT FOUND")

if __name__ == "__main__":
    asyncio.run(main())
