"""Upload only NEW weapon and passive emojis to Discord."""
import asyncio
import base64
import os
import sys
from pathlib import Path
from io import BytesIO

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

from PIL import Image
import aiohttp

ASSET_DIR = ROOT_DIR / "data" / "assets"
EMOJI_SIZE = 128

NEW_WEAPONS = [
    "soulreaper", "final_bell_scythe", "briar_relic", "rot_chalice",
    "banner", "eye", "judgement_blade", "lantern", "mirror_relic"
]

NEW_PASSIVES = [
    "life_steal", "mana_tap", "soul_gain", "gem_finder",
    "xp_boost", "rare_finder", "energize", "fear"
]

def prepare_emoji(path: Path) -> str:
    """Prepare emoji as base64 data URL."""
    with Image.open(path) as img:
        img = img.convert("RGBA")
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        img.thumbnail((EMOJI_SIZE, EMOJI_SIZE), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (EMOJI_SIZE, EMOJI_SIZE), (0, 0, 0, 0))
        x = (EMOJI_SIZE - img.width) // 2
        y = (EMOJI_SIZE - img.height) // 2
        canvas.alpha_composite(img, (x, y))
        buf = BytesIO()
        canvas.save(buf, format="PNG", optimize=True)
        raw = buf.getvalue()
        if len(raw) > 256 * 1024:
            compact = canvas.quantize(colors=256, method=Image.Quantize.FASTOCTREE).convert("RGBA")
            buf = BytesIO()
            compact.save(buf, format="PNG", optimize=True)
            raw = buf.getvalue()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{encoded}"

async def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERROR: No DISCORD_TOKEN")
        sys.exit(1)
    
    async with aiohttp.ClientSession() as session:
        # Get application ID
        async with session.get(
            "https://discord.com/api/v10/oauth2/applications/@me",
            headers={"Authorization": f"Bot {token}"}
        ) as resp:
            if resp.status != 200:
                print(f"Failed to get app info: {resp.status}")
                print(await resp.text())
                sys.exit(1)
            app_data = await resp.json()
            app_id = app_data["id"]
            print(f"Application ID: {app_id}")
        
        # Get existing emojis
        emoji_url = f"https://discord.com/api/v10/applications/{app_id}/emojis"
        async with session.get(emoji_url, headers={"Authorization": f"Bot {token}"}) as resp:
            existing = await resp.json()
            existing_names = {e["name"] for e in existing} if isinstance(existing, list) else {e["name"] for e in existing.get("items", [])}
            print(f"Existing emojis: {len(existing_names)}")
        
        # Upload new weapons
        uploaded = 0
        skipped = 0
        failed = 0
        
        print("\n=== WEAPONS ===")
        for key in NEW_WEAPONS:
            path = ASSET_DIR / "weapons" / f"{key}.png"
            emoji_name = f"weapon_{key}"
            if not path.exists():
                print(f"  MISSING: {path}")
                failed += 1
                continue
            if emoji_name in existing_names:
                print(f"  SKIP: {emoji_name} (exists)")
                skipped += 1
                continue
            try:
                image_data = prepare_emoji(path)
                async with session.post(
                    emoji_url,
                    headers={"Authorization": f"Bot {token}"},
                    json={"name": emoji_name, "image": image_data}
                ) as resp:
                    if resp.status in (200, 201):
                        print(f"  OK: {emoji_name}")
                        uploaded += 1
                    else:
                        text = await resp.text()
                        print(f"  FAIL: {emoji_name} - {resp.status}: {text[:100]}")
                        failed += 1
            except Exception as e:
                print(f"  ERROR: {emoji_name} - {e}")
                failed += 1
        
        print("\n=== PASSIVES ===")
        for key in NEW_PASSIVES:
            path = ASSET_DIR / "passives" / f"{key}.png"
            emoji_name = f"passive_{key}"
            if not path.exists():
                print(f"  MISSING: {path}")
                failed += 1
                continue
            if emoji_name in existing_names:
                print(f"  SKIP: {emoji_name} (exists)")
                skipped += 1
                continue
            try:
                image_data = prepare_emoji(path)
                async with session.post(
                    emoji_url,
                    headers={"Authorization": f"Bot {token}"},
                    json={"name": emoji_name, "image": image_data}
                ) as resp:
                    if resp.status in (200, 201):
                        print(f"  OK: {emoji_name}")
                        uploaded += 1
                    else:
                        text = await resp.text()
                        print(f"  FAIL: {emoji_name} - {resp.status}: {text[:100]}")
                        failed += 1
            except Exception as e:
                print(f"  ERROR: {emoji_name} - {e}")
                failed += 1
        
        print(f"\n=== SUMMARY ===")
        print(f"Uploaded: {uploaded}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(main())
