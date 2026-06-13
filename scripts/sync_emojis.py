"""Sync processed Abyssia weapon/passive PNGs to a Discord guild emoji bank."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
EMOJI_ROOT = ROOT_DIR / "assets" / "emojis"
EMOJI_MAP_PATH = ROOT_DIR / "data" / "emoji_map.json"
DISCORD_API = "https://discord.com/api/v10"
MAX_EMOJI_BYTES = 256 * 1024
DISCORD_NAME_RE = re.compile(r"^[A-Za-z0-9_]{2,32}$")


@dataclass(frozen=True)
class EmojiTarget:
    category: str
    key: str
    name: str
    path: Path


def _load_dotenv() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _setup_message() -> None:
    print("DISCORD_TOKEN and EMOJI_GUILD_ID are required to sync guild emojis.")
    print("PowerShell example:")
    print("  $env:DISCORD_TOKEN = 'your-bot-token'")
    print("  $env:EMOJI_GUILD_ID = '123456789012345678'")
    print("  python scripts/sync_emojis.py")
    print("No emojis were uploaded and data/emoji_map.json was not changed.")


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "AbyssiaIconSync/1.0",
    }


def _request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=_headers(token), method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"message": body}
        message = parsed.get("message", body) if isinstance(parsed, dict) else body
        if exc.code == 401:
            raise RuntimeError("Discord rejected DISCORD_TOKEN (401 Unauthorized).") from exc
        if exc.code == 403:
            raise RuntimeError("Missing Discord permission. The bot needs Manage Expressions in the emoji guild.") from exc
        if exc.code == 429 and isinstance(parsed, dict):
            retry_after = float(parsed.get("retry_after", 1.0))
            time.sleep(min(10.0, retry_after))
            return _request(method, url, token, payload)
        raise RuntimeError(f"Discord API error {exc.code}: {message}") from exc


def _emoji_data_url(path: Path) -> str:
    with Image.open(path) as image:
        if image.format != "PNG":
            raise ValueError(f"{path} is not a PNG")
        if image.size != (128, 128):
            raise ValueError(f"{path} is {image.size}, expected 128x128. Run scripts/process_icons.py.")
        image.load()
    raw = path.read_bytes()
    if len(raw) > MAX_EMOJI_BYTES:
        raise ValueError(f"{path} is {len(raw)} bytes, over Discord's 256 KB emoji limit")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _load_emoji_map() -> dict[str, str]:
    if not EMOJI_MAP_PATH.exists():
        return {}
    try:
        payload = json.loads(EMOJI_MAP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            result[str(key)] = value
        elif isinstance(value, dict):
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, str):
                    result[str(nested_key)] = nested_value
    return result


def _save_emoji_map(mapping: dict[str, str]) -> None:
    EMOJI_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    EMOJI_MAP_PATH.write_text(json.dumps(dict(sorted(mapping.items())), indent=2) + "\n", encoding="utf-8")


def _scan_targets() -> list[EmojiTarget]:
    targets: list[EmojiTarget] = []
    for category, prefix in (("weapons", "weapon"), ("passives", "passive")):
        directory = EMOJI_ROOT / category
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.png")):
            key = path.stem
            name = f"{prefix}_{key}"
            targets.append(EmojiTarget(category, key, name, path))
    return targets


def _existing_by_name(guild_id: str, token: str) -> dict[str, dict[str, Any]]:
    payload = _request("GET", f"{DISCORD_API}/guilds/{guild_id}/emojis", token)
    if not isinstance(payload, list):
        raise RuntimeError("Discord returned an unexpected emoji list payload.")
    return {str(item.get("name")): item for item in payload if item.get("name") and item.get("id")}


def _custom_emoji_string(item: dict[str, Any]) -> str:
    name = str(item["name"])
    emoji_id = str(item["id"])
    animated = bool(item.get("animated"))
    prefix = "a" if animated else ""
    return f"<{prefix}:{name}:{emoji_id}>"


def _warn_capacity(existing_count: int, target_count: int, missing_count: int) -> None:
    if target_count > 50 or existing_count + missing_count > 50:
        print("WARNING: This sync may exceed the base 50 static emoji guild limit.")
        print("Consider splitting icons into emoji servers/packs if Discord rejects uploads for capacity.")


def sync(*, token: str, guild_id: str, delete_missing: bool, dry_run: bool) -> int:
    targets = _scan_targets()
    if not targets:
        print("No processed emoji PNGs found under assets/emojis/weapons or assets/emojis/passives.")
        print("Run python scripts/process_icons.py after adding 512x512 master icons.")
        return 0

    invalid = [target.name for target in targets if not DISCORD_NAME_RE.match(target.name)]
    if invalid:
        print("Invalid Discord emoji names:")
        for name in invalid:
            print(f"  - {name}")
        return 1

    existing = _existing_by_name(guild_id, token)
    target_names = {target.name for target in targets}
    missing = [target for target in targets if target.name not in existing]
    _warn_capacity(len(existing), len(targets), len(missing))

    emoji_map = _load_emoji_map()
    for target in targets:
        item = existing.get(target.name)
        if item:
            emoji_map[target.name] = _custom_emoji_string(item)

    uploaded = 0
    skipped = len(targets) - len(missing)
    failed: list[str] = []

    for target in missing:
        try:
            image = _emoji_data_url(target.path)
            if dry_run:
                print(f"DRY RUN upload: {target.name}")
                continue
            item = _request(
                "POST",
                f"{DISCORD_API}/guilds/{guild_id}/emojis",
                token,
                {"name": target.name, "image": image},
            )
            if isinstance(item, dict) and item.get("id"):
                emoji_map[target.name] = _custom_emoji_string(item)
                uploaded += 1
                print(f"Uploaded: {target.name} ({item['id']})")
            else:
                failed.append(f"{target.name}: unexpected upload response")
        except Exception as exc:
            failed.append(f"{target.name}: {exc}")
            print(f"FAILED: {target.name} - {exc}")

    deleted = 0
    if delete_missing:
        extra = [item for name, item in existing.items() if name.startswith(("weapon_", "passive_")) and name not in target_names]
        for item in extra:
            name = str(item.get("name"))
            emoji_id = str(item.get("id"))
            try:
                if dry_run:
                    print(f"DRY RUN delete: {name}")
                    continue
                _request("DELETE", f"{DISCORD_API}/guilds/{guild_id}/emojis/{emoji_id}", token)
                emoji_map.pop(name, None)
                deleted += 1
                print(f"Deleted: {name}")
            except Exception as exc:
                failed.append(f"{name}: {exc}")
                print(f"FAILED delete: {name} - {exc}")

    if not dry_run:
        _save_emoji_map(emoji_map)
        print(f"Wrote {EMOJI_MAP_PATH.relative_to(ROOT_DIR)}")

    print("Sync complete:")
    print(f"  Uploaded: {uploaded}")
    print(f"  Skipped existing: {skipped}")
    print(f"  Deleted: {deleted}")
    print(f"  Failed: {len(failed)}")
    if failed:
        for line in failed[:20]:
            print(f"  - {line}")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delete-missing", action="store_true", help="Delete weapon_/passive_ guild emojis missing from local processed files.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _load_dotenv()
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    guild_id = os.environ.get("EMOJI_GUILD_ID", "").strip()
    if not token or not guild_id:
        _setup_message()
        return 0
    return sync(token=token, guild_id=guild_id, delete_missing=args.delete_missing, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
