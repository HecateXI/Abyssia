from __future__ import annotations

import base64
import json
import mimetypes
import os
import sqlite3
import urllib.error
import urllib.request
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args, **kwargs):
        return False

from core.content_config import (
    ASSET_DIR,
    CONFIG_PATH,
    DEFAULT_PATREON_TIERS,
    ROOT_DIR,
    asset_preview_url,
    clear_asset,
    clear_override,
    get_balancing,
    get_asset_file_path,
    load_config,
    safe_key,
    save_config,
    set_balancing,
    set_asset_from_data_url,
    set_asset_url,
    set_override,
    set_public_asset_base_url,
    set_setting,
)
from core.discord_assets import emoji_asset_name
from core.rpg_data import (
    BOSSES, CRATE_TYPES, CREATURES, EQUIPMENT, MATERIALS, RARITIES,
    CHARMS, RARITY_CATCH_RATES, SIGILS, STATUS_EFFECTS, WEAPON_PASSIVES,
    WEAPON_TYPES, ZONES, normalize_key,
)


STATIC_DIR = ROOT_DIR / "web"
_APPLICATION_ID_CACHE: str | None = None


def patreon_tiers() -> list[dict[str, Any]]:
    configured = get_balancing().get("patreon", {}).get("tiers", DEFAULT_PATREON_TIERS)
    if not isinstance(configured, list):
        configured = DEFAULT_PATREON_TIERS
    tiers: list[dict[str, Any]] = []
    for index, row in enumerate(configured, start=1):
        if not isinstance(row, dict):
            continue
        tier = int(row.get("tier") or index)
        tiers.append({
            "tier": tier,
            "name": str(row.get("name") or f"Patron {tier}"),
            "description": str(row.get("description") or ""),
        })
    return tiers or list(DEFAULT_PATREON_TIERS)


def patreon_role_setting_keys() -> tuple[str, ...]:
    return tuple(f"patreon_tier_{row['tier']}_role_id" for row in patreon_tiers())


def db_path() -> Path:
    configured = os.getenv("BOT_DB_PATH", "data/bot.sqlite3")
    path = Path(configured)
    return path if path.is_absolute() else ROOT_DIR / path


def ensure_settings_table() -> None:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY (guild_id, key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patreon_members (
                guild_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                tier INTEGER NOT NULL DEFAULT 1,
                note TEXT NOT NULL DEFAULT '',
                updated_at INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, member_id)
            )
            """
        )


def read_guild_settings(guild_id: int) -> dict[str, str]:
    ensure_settings_table()
    with sqlite3.connect(db_path()) as conn:
        rows = conn.execute("SELECT key, value FROM guild_settings WHERE guild_id = ? ORDER BY key", (guild_id,)).fetchall()
    return {str(key): "" if value is None else str(value) for key, value in rows}


def write_guild_settings(guild_id: int, settings: dict[str, Any]) -> dict[str, str]:
    ensure_settings_table()
    allowed = {"prefix", "modlog_channel_id", "welcome_channel_id", "booster_base_role_id", *patreon_role_setting_keys()}
    with sqlite3.connect(db_path()) as conn:
        for key, value in settings.items():
            if key not in allowed:
                continue
            text = str(value).strip()
            if text:
                conn.execute(
                    """
                    INSERT INTO guild_settings (guild_id, key, value)
                    VALUES (?, ?, ?)
                    ON CONFLICT(guild_id, key) DO UPDATE SET value = excluded.value
                    """,
                    (guild_id, key, text),
                )
            else:
                conn.execute("DELETE FROM guild_settings WHERE guild_id = ? AND key = ?", (guild_id, key))
    return read_guild_settings(guild_id)


def read_patreon_members(guild_id: int) -> list[dict[str, Any]]:
    ensure_settings_table()
    with sqlite3.connect(db_path()) as conn:
        rows = conn.execute(
            "SELECT member_id, tier, note, updated_at FROM patreon_members WHERE guild_id = ? ORDER BY tier DESC, member_id ASC",
            (guild_id,),
        ).fetchall()
    return [
        {"member_id": str(member_id), "tier": int(tier), "note": str(note or ""), "updated_at": int(updated_at or 0)}
        for member_id, tier, note, updated_at in rows
    ]


def save_patreon_member(guild_id: int, member_id: int, tier: int, note: str) -> dict[str, Any]:
    ensure_settings_table()
    allowed_tiers = {row["tier"] for row in patreon_tiers()}
    if tier not in allowed_tiers:
        raise ValueError(f"tier must be one of: {', '.join(str(t) for t in sorted(allowed_tiers))}")
    with sqlite3.connect(db_path()) as conn:
        conn.execute(
            """
            INSERT INTO patreon_members (guild_id, member_id, tier, note, updated_at)
            VALUES (?, ?, ?, ?, strftime('%s', 'now'))
            ON CONFLICT(guild_id, member_id) DO UPDATE SET
                tier = excluded.tier,
                note = excluded.note,
                updated_at = excluded.updated_at
            """,
            (guild_id, member_id, tier, note.strip()),
        )
    return {"member_id": str(member_id), "tier": tier, "note": note.strip()}


def delete_patreon_member(guild_id: int, member_id: int) -> None:
    ensure_settings_table()
    with sqlite3.connect(db_path()) as conn:
        conn.execute("DELETE FROM patreon_members WHERE guild_id = ? AND member_id = ?", (guild_id, member_id))


def _scan_asset_dir(kind: str) -> list[str]:
    """Scan data/assets/<kind>/ for PNG files and return sorted keys."""
    asset_dir = ASSET_DIR / kind
    if not asset_dir.is_dir():
        return []
    return sorted(f.stem for f in asset_dir.glob("*.png"))


def asset_info(kind: str, key: str) -> dict[str, Any]:
    config = load_config()
    record = config.get("assets", {}).get(kind, {}).get(safe_key(key)) or {}
    preview = asset_preview_url(kind, key)
    return {"record": record, "preview": preview}


def _discord_token() -> str:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if token.lower().startswith("bot "):
        token = token[4:].strip()
    return token


def _discord_json(method: str, path: str, token: str, payload: dict[str, Any] | None = None) -> Any:
    raw = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        data=raw,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "AbyssiaAdmin (web_admin.py)",
            **({"Content-Type": "application/json"} if payload is not None else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read()
    return json.loads(body.decode("utf-8")) if body else {}


def _discord_error(exc: urllib.error.HTTPError) -> str:
    try:
        data = json.loads(exc.read().decode("utf-8") or "{}")
        message = data.get("message")
        if message:
            return str(message)
    except Exception:
        pass
    return f"Discord API returned HTTP {exc.code}."


def _application_id(token: str) -> str | None:
    global _APPLICATION_ID_CACHE
    if _APPLICATION_ID_CACHE:
        return _APPLICATION_ID_CACHE
    configured = (
        os.getenv("DISCORD_APPLICATION_ID")
        or os.getenv("APPLICATION_ID")
        or os.getenv("CLIENT_ID")
        or os.getenv("BOT_APPLICATION_ID")
        or ""
    ).strip()
    if configured:
        _APPLICATION_ID_CACHE = configured
        return configured
    app = _discord_json("GET", "/oauth2/applications/@me", token)
    app_id = str(app.get("id") or "")
    _APPLICATION_ID_CACHE = app_id or None
    return _APPLICATION_ID_CACHE


def sync_uploaded_png_emoji(kind: str, key: str) -> dict[str, Any]:
    settings = load_config().get("settings", {})
    if settings.get("auto_sync_application_emojis") is False:
        return {"status": "disabled", "message": "Application emoji sync is disabled."}
    token = _discord_token()
    if not token:
        return {"status": "skipped", "message": "DISCORD_TOKEN is not configured for emoji sync."}
    path = get_asset_file_path(kind, key)
    if path is None:
        return {"status": "skipped", "message": "Uploaded PNG was saved locally, but no asset file was found for emoji sync."}
    try:
        app_id = _application_id(token)
        if not app_id:
            return {"status": "skipped", "message": "Discord application ID could not be resolved."}
        emoji_name = emoji_asset_name(kind, key)
        emojis = _discord_json("GET", f"/applications/{app_id}/emojis", token)
        items = emojis.get("items", emojis) if isinstance(emojis, dict) else emojis
        existing = None
        if isinstance(items, list):
            existing = next((item for item in items if str(item.get("name")) == emoji_name), None)
        if existing and existing.get("id"):
            _discord_json("DELETE", f"/applications/{app_id}/emojis/{existing['id']}", token)
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        _discord_json(
            "POST",
            f"/applications/{app_id}/emojis",
            token,
            {"name": emoji_name, "image": f"data:image/png;base64,{encoded}"},
        )
        return {
            "status": "updated" if existing else "created",
            "name": emoji_name,
            "message": f"Application emoji {emoji_name} was {'updated' if existing else 'created'}.",
        }
    except urllib.error.HTTPError as exc:
        return {"status": "failed", "message": _discord_error(exc)}
    except Exception as exc:
        return {"status": "failed", "message": str(exc)}


def merged_record(kind: str, key: str, base: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    override = config["overrides"][kind].get(key, {})
    if not isinstance(override, dict):
        override = {}
    row = {**base, **{field: value for field, value in override.items() if field != "deleted"}}
    row["key"] = key
    row["asset"] = asset_info(kind, key)
    row["override"] = override
    row["deleted"] = bool(override.get("deleted"))
    return row


def custom_rows(kind: str, config: dict[str, Any], existing_keys: set[str]) -> list[dict[str, Any]]:
    rows = []
    for key, override in sorted(config["overrides"][kind].items()):
        if key in existing_keys or not isinstance(override, dict):
            continue
        row = {field: value for field, value in override.items() if field != "deleted"}
        row.setdefault("name", key.replace("_", " ").title())
        rows.append(merged_record(kind, key, row, config))
    return rows


def catalog() -> dict[str, Any]:
    config = load_config()
    creatures = []
    for creature in CREATURES:
        key = normalize_key(creature.name)
        creatures.append(merged_record("creatures", key, asdict(creature), config))
    creatures.extend(custom_rows("creatures", config, {row["key"] for row in creatures}))

    equipment = []
    for key, item in EQUIPMENT.items():
        equipment.append(merged_record("equipment", key, asdict(item), config))
    equipment.extend(custom_rows("equipment", config, {row["key"] for row in equipment}))

    zones = []
    for key, zone in ZONES.items():
        zones.append(merged_record("zones", key, asdict(zone), config))
    zones.extend(custom_rows("zones", config, {row["key"] for row in zones}))

    bosses = []
    for boss in BOSSES:
        bosses.append(merged_record("bosses", boss.key, asdict(boss), config))
    bosses.extend(custom_rows("bosses", config, {row["key"] for row in bosses}))

    materials = []
    for key, name in MATERIALS.items():
        materials.append(merged_record("materials", key, {"name": name}, config))
    materials.extend(custom_rows("materials", config, {row["key"] for row in materials}))

    weapons = []
    for key, data in WEAPON_TYPES.items():
        weapons.append(merged_record("weapons", key, {
            "name": data["name"], "desc": data["desc"],
            "atk_range": list(data["atk_range"]), "def_range": list(data["def_range"]),
            "passive_pool": list(data["passive_pool"]),
        }, config))
    weapons.extend(custom_rows("weapons", config, {row["key"] for row in weapons}))

    passives = []
    for key, data in WEAPON_PASSIVES.items():
        passives.append(merged_record("passives", key, {"name": data["name"]}, config))
    passives.extend(custom_rows("passives", config, {row["key"] for row in passives}))

    status = []
    for effect in STATUS_EFFECTS:
        status.append(merged_record("status", effect.key, {"name": effect.name, "desc": effect.description}, config))
    status.extend(custom_rows("status", config, {row["key"] for row in status}))

    currency = []
    for key in _scan_asset_dir("currency"):
        currency.append(merged_record("currency", key, {"name": key.replace("_", " ").title()}, config))
    currency.extend(custom_rows("currency", config, {row["key"] for row in currency}))

    crate = []
    for key, data in CRATE_TYPES.items():
        crate.append(merged_record("crate", key, {"name": data["name"], "desc": data["desc"]}, config))
    crate.extend(custom_rows("crate", config, {row["key"] for row in crate}))

    buffs = []
    for key in _scan_asset_dir("buffs"):
        buffs.append(merged_record("buffs", key, {"name": key.replace("_", " ").title()}, config))
    buffs.extend(custom_rows("buffs", config, {row["key"] for row in buffs}))

    rarity_icons = []
    for key in _scan_asset_dir("rarity"):
        rarity_icons.append(merged_record("rarity", key, {"name": key.replace("_", " ").title()}, config))
    rarity_icons.extend(custom_rows("rarity", config, {row["key"] for row in rarity_icons}))

    ui_icons = []
    for key in _scan_asset_dir("ui"):
        ui_icons.append(merged_record("ui", key, {"name": key.replace("_", " ").title()}, config))
    ui_icons.extend(custom_rows("ui", config, {row["key"] for row in ui_icons}))

    consumable = []
    for key in _scan_asset_dir("consumable"):
        consumable.append(merged_record("consumable", key, {"name": key.replace("_", " ").title()}, config))
    consumable.extend(custom_rows("consumable", config, {row["key"] for row in consumable}))

    return {
        "creatures": creatures,
        "equipment": equipment,
        "zones": zones,
        "bosses": bosses,
        "materials": materials,
        "weapons": weapons,
        "passives": passives,
        "status": status,
        "currency": currency,
        "crate": crate,
        "buffs": buffs,
        "rarity": rarity_icons,
        "ui": ui_icons,
        "consumable": consumable,
        "rarities": [
            {**asdict(rarity), "key": normalize_key(rarity.name), "catch_rate": RARITY_CATCH_RATES.get(rarity.name, 0)}
            for rarity in RARITIES
        ],
        "sigils": [asdict(sigil) for sigil in SIGILS],
        "charms": [asdict(charm) for charm in CHARMS],
        "patreon_tiers": patreon_tiers(),
        "balancing": get_balancing(),
        "settings": config.get("settings", {}),
        "paths": {
            "config": str(CONFIG_PATH),
            "assets": str(ASSET_DIR),
            "database": str(db_path()),
        },
    }


class AdminHandler(BaseHTTPRequestHandler):
    server_version = "AbyssiaAdmin/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    @property
    def admin_password(self) -> str:
        return os.getenv("ADMIN_PASSWORD", "admin")

    def is_authorized(self) -> bool:
        return self.headers.get("X-Admin-Password", "") == self.admin_password

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        raw = b""
        remaining = length
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                break
            raw += chunk
            remaining -= len(chunk)
        if len(raw) > 12 * 1024 * 1024:
            raise ValueError("Request body is too large.")
        data = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object.")
        return data

    def send_json(self, payload: Any, status: int = 200) -> None:
        raw = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"error": message}, status)

    def require_auth(self) -> bool:
        if self.is_authorized():
            return True
        self.send_error_json(HTTPStatus.UNAUTHORIZED, "Invalid admin password.")
        return False

    def serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        raw = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.serve_file(STATIC_DIR / "index.html")
            return
        if path in {"/app.js", "/styles.css"}:
            self.serve_file(STATIC_DIR / path.removeprefix("/"))
            return
        if path.startswith("/assets/"):
            relative = Path(unquote(path.removeprefix("/assets/")))
            target = (ASSET_DIR / relative).resolve()
            if ASSET_DIR.resolve() in target.parents:
                self.serve_file(target)
                return
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if path.startswith("/static/"):
            relative = Path(unquote(path.removeprefix("/static/")))
            target = (STATIC_DIR / relative).resolve()
            if STATIC_DIR.resolve() in target.parents:
                self.serve_file(target)
                return
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if path == "/api/session":
            self.send_json({"ok": self.is_authorized(), "default_password": self.admin_password == "admin"})
            return
        if not self.require_auth():
            return
        if path == "/api/catalog":
            self.send_json(catalog())
            return
        if path == "/api/guild-settings":
            query = parse_qs(parsed.query)
            guild_id = int((query.get("guild_id") or ["0"])[0])
            if guild_id <= 0:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "guild_id is required.")
                return
            self.send_json({"guild_id": guild_id, "settings": read_guild_settings(guild_id)})
            return
        if path == "/api/patreon-members":
            query = parse_qs(parsed.query)
            guild_id = int((query.get("guild_id") or ["0"])[0])
            if guild_id <= 0:
                self.send_error_json(HTTPStatus.BAD_REQUEST, "guild_id is required.")
                return
            self.send_json({"guild_id": guild_id, "members": read_patreon_members(guild_id)})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not self.require_auth():
            return
        try:
            data = self.read_json()
            if parsed.path == "/api/content":
                kind = str(data.get("kind") or "")
                key = safe_key(str(data.get("key") or ""))
                patch = data.get("patch") or {}
                if not isinstance(patch, dict):
                    raise ValueError("patch must be an object.")
                record = set_override(kind, key, patch)
                self.send_json({"key": key, "override": record})
                return
            if parsed.path == "/api/content/clear":
                clear_override(str(data.get("kind") or ""), str(data.get("key") or ""))
                self.send_json({"ok": True})
                return
            if parsed.path == "/api/asset":
                kind = str(data.get("kind") or "")
                key = safe_key(str(data.get("key") or ""))
                if data.get("clear"):
                    clear_asset(kind, key)
                    self.send_json({"ok": True})
                    return
                if data.get("data_url"):
                    record = set_asset_from_data_url(kind, key, str(data["data_url"]))
                    emoji_sync = sync_uploaded_png_emoji(kind, key)
                elif data.get("url"):
                    record = set_asset_url(kind, key, str(data["url"]))
                    emoji_sync = {"status": "skipped", "message": "External URLs are not uploaded as application emojis."}
                else:
                    raise ValueError("Provide a PNG upload or URL.")
                self.send_json({"key": key, "asset": record, "preview": asset_preview_url(kind, key), "emoji_sync": emoji_sync})
                return
            if parsed.path == "/api/settings":
                if "public_asset_base_url" in data:
                    set_public_asset_base_url(str(data.get("public_asset_base_url") or ""))
                if "auto_sync_application_emojis" in data:
                    set_setting("auto_sync_application_emojis", bool(data.get("auto_sync_application_emojis")))
                self.send_json({"settings": load_config().get("settings", {})})
                return
            if parsed.path == "/api/balancing":
                patch = data.get("balancing") or data.get("patch") or {}
                if not isinstance(patch, dict):
                    raise ValueError("balancing must be an object.")
                self.send_json({"balancing": set_balancing(patch)})
                return
            if parsed.path == "/api/guild-settings":
                guild_id = int(data.get("guild_id") or 0)
                if guild_id <= 0:
                    raise ValueError("guild_id is required.")
                settings = data.get("settings") or {}
                if not isinstance(settings, dict):
                    raise ValueError("settings must be an object.")
                self.send_json({"guild_id": guild_id, "settings": write_guild_settings(guild_id, settings)})
                return
            if parsed.path == "/api/patreon-members":
                guild_id = int(data.get("guild_id") or 0)
                member_id = int(data.get("member_id") or 0)
                if guild_id <= 0 or member_id <= 0:
                    raise ValueError("guild_id and member_id are required.")
                if data.get("delete"):
                    delete_patreon_member(guild_id, member_id)
                    self.send_json({"ok": True, "members": read_patreon_members(guild_id)})
                    return
                tier = int(data.get("tier") or 1)
                note = str(data.get("note") or "")
                save_patreon_member(guild_id, member_id, tier, note)
                self.send_json({"ok": True, "members": read_patreon_members(guild_id)})
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    host = os.getenv("ADMIN_HOST", "127.0.0.1")
    port = int(os.getenv("ADMIN_PORT", "8080"))
    ensure_settings_table()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    save_config(load_config())
    if os.getenv("ADMIN_PASSWORD") is None:
        print("ADMIN_PASSWORD is not set; using default password: admin")
    print(f"Dashboard running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), AdminHandler).serve_forever()


if __name__ == "__main__":
    main()
