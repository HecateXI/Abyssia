"""Upload Abyssia asset emojis to Discord application emoji bank."""
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

from core.discord_assets import upload_application_asset_emojis
import discord

async def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERROR: No DISCORD_TOKEN found in .env")
        sys.exit(1)
    
    intents = discord.Intents.default()
    bot = discord.Client(intents=intents)
    
    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
        result = await upload_application_asset_emojis(bot, replace_existing=True)
        print(f"\nUpload results:")
        print(f"  Uploaded: {result.get('uploaded', 0)}")
        print(f"  Existing: {result.get('existing', 0)}")
        print(f"  Replaced: {result.get('replaced', 0)}")
        failed = result.get('failed', [])
        if failed:
            print(f"  Failed: {len(failed)}")
            for f in failed[:20]:
                print(f"    - {f}")
        await bot.close()
    
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
