"""
Sync Abyssia asset icons to Discord application emoji bank.

This script uploads weapon, passive, and other asset icons as Discord application emojis.
It reads from the data/assets directory and uploads missing emojis.

Usage:
    python scripts/sync_emojis.py

Environment variables:
    DISCORD_TOKEN - Bot token (required)
    EMOJI_GUILD_ID - Guild ID for emoji upload (optional, defaults to application emojis)

The script will:
1. Scan data/assets for PNG files
2. Check which emojis already exist
3. Upload missing emojis
4. Print a summary of what was uploaded/skipped/failed
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from PIL import Image
from io import BytesIO

# Discord API limits
EMOJI_IMAGE_SIZE = 128
MAX_EMOJI_IMAGE_BYTES = 256 * 1024  # 256KB

# Asset directory
ASSET_DIR = ROOT_DIR / "data" / "assets"

# Emoji name prefix mapping
PREFIX_MAP = {
    "weapons": "weapon",
    "passives": "passive",
    "status": "status",
    "creatures": "cr",
    "rarity": "rarity",
    "materials": "material",
    "currency": "currency",
    "ui": "ui",
    "consumable": "item",
    "equipment": "eq",
    "buffs": "buff",
    "crate": "crate",
    "zones": "zone",
    "bosses": "boss",
}


def safe_key(key: str) -> str:
    """Normalize key for emoji name."""
    return key.strip().lower().replace("'", "").replace(" ", "_").replace("-", "_")[:80]


def prepared_emoji_png(path: Path) -> bytes:
    """Prepare emoji PNG for Discord upload."""
    with Image.open(path) as source:
        image = source.convert("RGBA")
    
    # Crop to bounding box
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    
    # Resize to fit
    image.thumbnail((EMOJI_IMAGE_SIZE, EMOJI_IMAGE_SIZE), Image.Resampling.LANCZOS)
    
    # Center on transparent canvas
    canvas = Image.new("RGBA", (EMOJI_IMAGE_SIZE, EMOJI_IMAGE_SIZE), (0, 0, 0, 0))
    x = (EMOJI_IMAGE_SIZE - image.width) // 2
    y = (EMOJI_IMAGE_SIZE - image.height) // 2
    canvas.alpha_composite(image, (x, y))
    
    # Save as PNG
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    raw = output.getvalue()
    
    # If too large, quantize
    if len(raw) > MAX_EMOJI_IMAGE_BYTES:
        compact = canvas.quantize(colors=256, method=Image.Quantize.FASTOCTREE).convert("RGBA")
        output = BytesIO()
        compact.save(output, format="PNG", optimize=True)
        raw = output.getvalue()
    
    return raw


def emoji_image_data_url(path: Path) -> str:
    """Create data URL for emoji image."""
    encoded = base64.b64encode(prepared_emoji_png(path)).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def emoji_asset_name(kind: str, key: str) -> str:
    """Generate emoji name."""
    prefix = PREFIX_MAP.get(kind, kind)
    safe = safe_key(key).lower()
    max_key_length = 32 - len(prefix) - 1
    return f"{prefix}_{safe[:max_key_length]}"


async def sync_emojis():
    """Main sync function."""
    import aiohttp
    
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable not set")
        print("Set it with: $env:DISCORD_TOKEN = 'your-bot-token-here'")
        sys.exit(1)
    
    guild_id = os.environ.get("EMOJI_GUILD_ID")
    
    # Get application ID
    async with aiohttp.ClientSession() as session:
        # Get current application info
        async with session.get(
            "https://discord.com/api/v10/oauth2/applications/@me",
            headers={"Authorization": f"Bot {token}"}
        ) as resp:
            if resp.status != 200:
                print(f"ERROR: Failed to get application info: {resp.status}")
                print(await resp.text())
                sys.exit(1)
            app_data = await resp.json()
            app_id = app_data["id"]
            print(f"Application ID: {app_id}")
        
        # Get existing emojis
        if guild_id:
            emoji_url = f"https://discord.com/api/v10/guilds/{guild_id}/emojis"
        else:
            emoji_url = f"https://discord.com/api/v10/applications/{app_id}/emojis"
        
        async with session.get(
            emoji_url,
            headers={"Authorization": f"Bot {token}"}
        ) as resp:
            if resp.status != 200:
                print(f"ERROR: Failed to get existing emojis: {resp.status}")
                print(await resp.text())
                sys.exit(1)
            existing_emojis = await resp.json()
            if isinstance(existing_emojis, list):
                existing_by_name = {e["name"]: e for e in existing_emojis}
            else:
                existing_by_name = {e["name"]: e for e in existing_emojis.get("items", [])}
        
        print(f"Existing emojis: {len(existing_by_name)}")
        
        # Scan for assets to upload
        uploaded = 0
        skipped = 0
        failed = 0
        failed_list = []
        
        for kind in PREFIX_MAP.keys():
            kind_dir = ASSET_DIR / kind
            if not kind_dir.exists():
                continue
            
            for png_path in sorted(kind_dir.glob("*.png")):
                key = png_path.stem
                emoji_name = emoji_asset_name(kind, key)
                
                # Check if already exists
                if emoji_name in existing_by_name:
                    skipped += 1
                    continue
                
                # Upload emoji
                try:
                    image_data = emoji_image_data_url(png_path)
                    
                    if guild_id:
                        # Guild emoji upload
                        payload = {"name": emoji_name, "image": image_data}
                        async with session.post(
                            emoji_url,
                            headers={"Authorization": f"Bot {token}"},
                            json=payload
                        ) as resp:
                            if resp.status not in (200, 201):
                                error_text = await resp.text()
                                print(f"  FAILED: {emoji_name} - {resp.status}: {error_text[:100]}")
                                failed += 1
                                failed_list.append(emoji_name)
                            else:
                                print(f"  Uploaded: {emoji_name}")
                                uploaded += 1
                    else:
                        # Application emoji upload
                        payload = {"name": emoji_name, "image": image_data}
                        async with session.post(
                            emoji_url,
                            headers={"Authorization": f"Bot {token}"},
                            json=payload
                        ) as resp:
                            if resp.status not in (200, 201):
                                error_text = await resp.text()
                                print(f"  FAILED: {emoji_name} - {resp.status}: {error_text[:100]}")
                                failed += 1
                                failed_list.append(emoji_name)
                            else:
                                print(f"  Uploaded: {emoji_name}")
                                uploaded += 1
                
                except Exception as e:
                    print(f"  ERROR: {emoji_name} - {e}")
                    failed += 1
                    failed_list.append(emoji_name)
        
        # Summary
        print(f"\n{'='*50}")
        print(f"Sync Complete:")
        print(f"  Uploaded: {uploaded}")
        print(f"  Skipped (already exists): {skipped}")
        print(f"  Failed: {failed}")
        if failed_list:
            print(f"\nFailed emojis:")
            for name in failed_list[:20]:
                print(f"  - {name}")
            if len(failed_list) > 20:
                print(f"  ... and {len(failed_list) - 20} more")


if __name__ == "__main__":
    print("Abyssia Emoji Sync")
    print(f"Asset directory: {ASSET_DIR}")
    print(f"Token set: {'Yes' if os.environ.get('DISCORD_TOKEN') else 'No'}")
    print(f"Guild ID: {os.environ.get('EMOJI_GUILD_ID', 'Not set (using application emojis)')}")
    print()
    
    asyncio.run(sync_emojis())
