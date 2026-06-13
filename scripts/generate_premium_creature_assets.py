# ruff: noqa: E402,I001
from __future__ import annotations

import hashlib
import json
import math
import random
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PIL import Image, ImageDraw, ImageFont

from core.content_config import ASSET_DIR, load_config, safe_key, save_config
from core.rpg_data import CREATURES, RARITY_BY_NAME, creature_asset_key, normalize_key

CANVAS = 96
OUT_SIZE = 512
OUT_DIR = ASSET_DIR / "creatures"
PREVIEW_DIR = ROOT_DIR / "tmp" / "creature_asset_previews"
DB_PATH = ROOT_DIR / "data" / "bot.sqlite3"

INFUSED_PREFIXES = ("Ruby", "Emerald", "Sapphire", "Diamond", "Abyssal")

RARITY_FALLBACKS: dict[str, tuple[int, int, int]] = {
    "Common": (145, 154, 166),
    "Uncommon": (70, 216, 132),
    "Rare": (58, 174, 242),
    "Epic": (168, 112, 246),
    "Legendary": (242, 196, 66),
    "Mythic": (244, 86, 112),
    "Ancient": (242, 122, 54),
    "Patreon": (255, 78, 92),
    "Divine": (246, 236, 196),
    "Eldritch": (44, 218, 226),
    "Abyssal": (136, 76, 214),
    "Prismatic": (74, 222, 170),
    "Ethereal": (114, 180, 248),
    "Void Lord": (54, 112, 184),
    "Hidden": (164, 74, 232),
}

KEYWORD_PALETTES: tuple[tuple[tuple[str, ...], tuple[int, int, int], tuple[int, int, int]], ...] = (
    (("blood", "crimson", "red", "ribcage"), (190, 28, 58), (255, 128, 78)),
    (("moon", "pale", "ivory", "wax", "bone", "skeleton"), (196, 198, 184), (255, 246, 196)),
    (("ash", "cinder", "ember", "fire", "infernal", "hell", "phoenix"), (222, 78, 34), (255, 190, 70)),
    (("void", "abyss", "black", "night", "dusk", "hollow"), (34, 44, 108), (106, 86, 240)),
    (("grave", "crypt", "sepulcher", "mourning"), (128, 116, 112), (226, 212, 174)),
    (("rot", "plague", "mire", "bog", "thorn", "briar", "root"), (66, 150, 82), (188, 220, 78)),
    (("glass", "mirror", "prism", "opal", "spectrum", "rainbow", "aurora"), (42, 214, 222), (236, 96, 248)),
    (("star", "sun", "celestial", "halo", "orbit", "gilded"), (236, 194, 66), (120, 216, 255)),
    (("bell", "lantern", "dream", "wisp"), (236, 174, 64), (86, 226, 232)),
)


@dataclass
class CreatureTarget:
    name: str
    key: str
    rarity: str
    aliases: set[str] = field(default_factory=set)
    source: str = "runtime"


@dataclass(frozen=True)
class Palette:
    ink: tuple[int, int, int]
    shadow: tuple[int, int, int]
    dark: tuple[int, int, int]
    mid: tuple[int, int, int]
    light: tuple[int, int, int]
    accent: tuple[int, int, int]
    glow: tuple[int, int, int]
    bone: tuple[int, int, int]


def _hash_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)


def _clamp(value: float) -> int:
    return max(0, min(255, round(value)))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(_clamp(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _darken(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return _mix(color, (0, 0, 0), amount)


def _lighten(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return _mix(color, (255, 255, 255), amount)


def _rarity_color(rarity: str) -> tuple[int, int, int]:
    data = RARITY_BY_NAME.get(rarity)
    if data is None:
        return RARITY_FALLBACKS.get(rarity, RARITY_FALLBACKS["Common"])
    raw = int(data.color)
    return ((raw >> 16) & 255, (raw >> 8) & 255, raw & 255)


def _palette(name: str, rarity: str, seed: int) -> Palette:
    base = _rarity_color(rarity)
    lower = name.lower()
    primary = base
    accent = _lighten(base, 0.36)
    for words, keyword_primary, keyword_accent in KEYWORD_PALETTES:
        if any(word in lower for word in words):
            primary = _mix(base, keyword_primary, 0.56)
            accent = _mix(keyword_accent, _lighten(base, 0.2), 0.28)
            break

    rng = random.Random(seed ^ 0xA66E551A)
    drift = (rng.randint(42, 230), rng.randint(42, 230), rng.randint(42, 230))
    mid = _mix(primary, drift, 0.22)
    dark = _darken(mid, 0.42)
    light = _lighten(mid, 0.34)
    glow = _lighten(_mix(accent, light, 0.32), 0.2)
    return Palette(
        ink=(5, 5, 9),
        shadow=(0, 0, 0),
        dark=dark,
        mid=mid,
        light=light,
        accent=accent,
        glow=glow,
        bone=_mix((226, 214, 178), accent, 0.12),
    )


def _strip_infused(name: str) -> str:
    clean = name.strip()
    for prefix in INFUSED_PREFIXES:
        needle = prefix + " "
        if clean.startswith(needle):
            return clean[len(needle) :]
    return clean


def _ranked_db_creatures() -> list[sqlite3.Row]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return list(
            conn.execute(
                """
                SELECT image, name, rarity, COUNT(*) AS count
                FROM rpg_creatures
                WHERE image IS NOT NULL AND TRIM(image) != ''
                GROUP BY image, name, rarity
                ORDER BY count DESC, name ASC
                """
            )
        )
    finally:
        conn.close()


def _display_name_from_key(key: str) -> str:
    special = {
        "10000": "Subaru",
        "1": "Trix's Grumpy Cat",
        "hound": "Abyssal Hound",
    }
    return special.get(key, key.replace("_", " ").replace("-", " ").title())


def _collect_targets() -> list[CreatureTarget]:
    targets: list[CreatureTarget] = []
    by_key: dict[str, CreatureTarget] = {}
    by_name: dict[str, CreatureTarget] = {}

    def add_target(name: str, rarity: str, aliases: set[str], source: str) -> CreatureTarget:
        key = safe_key(name)
        target = by_key.get(key)
        if target is None:
            target = CreatureTarget(name=name, key=key, rarity=rarity, source=source)
            targets.append(target)
            by_key[key] = target
            by_name[normalize_key(name)] = target
        target.aliases.update(alias for alias in aliases if alias)
        target.aliases.add(key)
        for alias in target.aliases:
            by_key.setdefault(alias, target)
        return target

    for creature in CREATURES:
        aliases = {safe_key(creature.name), creature_asset_key(creature.name)}
        add_target(creature.name, creature.rarity, aliases, "runtime")

    for row in _ranked_db_creatures():
        image_key = safe_key(str(row["image"]))
        raw_name = str(row["name"])
        existing = by_name.get(normalize_key(raw_name))
        clean_name = raw_name
        if existing is None:
            clean_name = _strip_infused(raw_name)
            existing = by_name.get(normalize_key(clean_name))
        if existing is not None:
            existing.aliases.add(image_key)
            by_key[image_key] = existing
            continue
        if image_key in by_key:
            by_key[image_key].aliases.add(image_key)
            continue
        add_target(clean_name, str(row["rarity"] or "Common"), {image_key}, "database")

    config = load_config()
    asset_records = config.get("assets", {}).get("creatures", {})
    if isinstance(asset_records, dict):
        for raw_key in sorted(asset_records):
            key = safe_key(str(raw_key))
            if key in by_key:
                by_key[key].aliases.add(key)
                continue
            add_target(_display_name_from_key(key), "Common", {key}, "content")

    return targets


def _family(name: str, key: str) -> str:
    lower = f"{name} {key}".lower()
    if "crawling_hand" in lower or "crawling hand" in lower:
        return "hand"
    if any(word in lower for word in ("minnow", "angler")):
        return "fish"
    if any(word in lower for word in ("hunger", "devours", "beneath", "maw", "choir of teeth", "chaos")):
        return "maw"
    if any(word in lower for word in ("newt", "lizard")):
        return "lizard"
    if any(word in lower for word in ("chimera", "manticore", "ravager", "familiar", "stalker")):
        return "chimera"
    if any(word in lower for word in ("orbit", "horizon", "eye", "oblivion", "stars", "whisper", "between", "quiet graves")):
        return "orbit"
    if any(word in lower for word in ("dragon", "drake", "wyvern", "wyrm")):
        return "dragon"
    if any(word in lower for word in ("serpent", "eel", "leviathan", "kraken", "hydra", "basilisk", "sunwyrm")):
        return "serpent"
    if any(word in lower for word in ("moth", "swan", "harrier", "roc", "phoenix", "seraph", "valkyr", "gryphon", "crow", "bat")):
        return "winged"
    if any(
        word in lower
        for word in ("rat", "hound", "pup", "lynx", "cat", "jackal", "stag", "hart", "kirin", "toad", "subaru", "night that hunts")
    ):
        return "beast"
    if any(word in lower for word in ("spider", "skitter", "beetle", "angler")):
        return "insect"
    if any(word in lower for word in ("slime", "wisp", "soul", "shade", "ghast", "wraith", "spectre", "ghost")):
        return "ghost"
    if any(word in lower for word in ("reliquary", "bell", "lantern", "crown", "teeth", "eye", "heart", "chalice")):
        return "relic"
    if any(word in lower for word in ("titan", "colossus", "behemoth", "godling", "archon", "sovereign", "event horizon")):
        return "titan"
    if any(
        word in lower
        for word in (
            "king",
            "void lord",
            "monarch",
            "emperor",
            "knight",
            "paladin",
            "warden",
            "saint",
            "judge",
            "oracle",
            "doctor",
            "executioner",
            "warlord",
            "skeleton",
            "zombie",
            "imp",
            "revenant",
            "demon",
            "apostle",
            "daughter",
            "reaver",
            "siren",
            "martyr",
            "choirmaster",
        )
    ):
        return "humanoid"
    return "cosmic"


def _shift(points: list[tuple[int, int]], dx: int, dy: int) -> list[tuple[int, int]]:
    return [(x + dx, y + dy) for x, y in points]


def _outline_offsets(width: int = 2) -> list[tuple[int, int]]:
    offsets: list[tuple[int, int]] = []
    for dy in range(-width, width + 1):
        for dx in range(-width, width + 1):
            if dx == 0 and dy == 0:
                continue
            if dx * dx + dy * dy <= width * width + 1:
                offsets.append((dx, dy))
    return offsets


def _poly(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill: tuple[int, int, int], outline: tuple[int, int, int]) -> None:
    for dx, dy in _outline_offsets(2):
        draw.polygon(_shift(points, dx, dy), fill=outline)
    draw.polygon(points, fill=fill)


def _ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int], outline: tuple[int, int, int]) -> None:
    x1, y1, x2, y2 = box
    for dx, dy in _outline_offsets(2):
        draw.ellipse((x1 + dx, y1 + dy, x2 + dx, y2 + dy), fill=outline)
    draw.ellipse(box, fill=fill)


def _rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int], outline: tuple[int, int, int]) -> None:
    x1, y1, x2, y2 = box
    draw.rectangle((x1 - 2, y1 - 2, x2 + 2, y2 + 2), fill=outline)
    draw.rectangle(box, fill=fill)


def _line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    fill: tuple[int, int, int],
    width: int,
    outline: tuple[int, int, int],
) -> None:
    draw.line(points, fill=outline, width=width + 4, joint="curve")
    draw.line(points, fill=fill, width=width, joint="curve")


def _eye(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, pal: Palette, glow: bool = True) -> None:
    _ellipse(draw, (x - size, y - size, x + size, y + size), pal.ink, pal.ink)
    if glow:
        draw.rectangle((x - size // 3, y - size // 2, x + size // 3, y + size // 2), fill=pal.glow)
    else:
        draw.rectangle((x - size // 2, y - size // 2, x + size // 2, y + size // 2), fill=pal.bone)


def _teeth(draw: ImageDraw.ImageDraw, x: int, y: int, count: int, pal: Palette) -> None:
    start = x - count * 2
    for i in range(count):
        px = start + i * 4
        draw.polygon([(px, y), (px + 3, y), (px + 1, y + 5)], fill=pal.bone)


def _horns(draw: ImageDraw.ImageDraw, x: int, y: int, spread: int, pal: Palette, seed: int) -> None:
    rng = random.Random(seed ^ 0xA1E)
    for side in (-1, 1):
        h = 12 + rng.randint(0, 7)
        _poly(draw, [(x + side * spread, y + 4), (x + side * (spread + 12), y - h), (x + side * (spread - 4), y)], pal.bone, pal.ink)


def _crown(draw: ImageDraw.ImageDraw, x: int, y: int, width: int, pal: Palette) -> None:
    half = width // 2
    points = [
        (x - half, y + 9),
        (x - half + 8, y - 4),
        (x - 8, y + 5),
        (x, y - 10),
        (x + 8, y + 5),
        (x + half - 8, y - 4),
        (x + half, y + 9),
        (x + half, y + 15),
        (x - half, y + 15),
    ]
    _poly(draw, points, pal.accent, pal.ink)
    draw.rectangle((x - half + 5, y + 10, x + half - 5, y + 12), fill=pal.light)


def _wing(draw: ImageDraw.ImageDraw, cx: int, cy: int, side: int, pal: Palette, seed: int, bird: bool) -> None:
    rng = random.Random(seed ^ (0x51A2 + side))
    span = 28 + rng.randint(-4, 9)
    if bird:
        points = [(cx + side * 5, cy - 7), (cx + side * span, cy - 19), (cx + side * 34, cy + 1), (cx + side * 18, cy + 20)]
    else:
        points = [(cx + side * 4, cy - 4), (cx + side * span, cy - 16), (cx + side * 37, cy + 18), (cx + side * 14, cy + 10)]
    _poly(draw, points, _mix(pal.mid, pal.accent, 0.34), pal.ink)
    draw.line((cx + side * 9, cy - 4, cx + side * (span - 2), cy - 14), fill=pal.light, width=1)
    draw.line((cx + side * 10, cy + 1, cx + side * 30, cy + 14), fill=pal.dark, width=2)


def _draw_shadow(draw: ImageDraw.ImageDraw, seed: int) -> None:
    rng = random.Random(seed ^ 0x5A5A)
    draw.ellipse((20 + rng.randint(-4, 4), 76, 78 + rng.randint(-3, 6), 90), fill=(0, 0, 0, 116))


def _sparkles(draw: ImageDraw.ImageDraw, pal: Palette, seed: int, count: int) -> None:
    rng = random.Random(seed ^ 0x5051)
    for _ in range(count):
        x = rng.randint(14, 82)
        y = rng.randint(12, 78)
        color = rng.choice([pal.accent, pal.glow, pal.light])
        draw.point((x, y), fill=color)
        if rng.random() < 0.35:
            draw.point((x + 1, y), fill=color)
            draw.point((x, y + 1), fill=color)


def _draw_beast(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    rng = random.Random(seed)
    squat = "toad" in lower or "slime" in lower
    rat = "rat" in lower
    stag = any(word in lower for word in ("stag", "hart", "kirin"))
    cat = any(word in lower for word in ("cat", "lynx"))
    body_w = 36 + rng.randint(-6, 10)
    body_h = 22 + rng.randint(-5, 8)
    if squat:
        body_w += 10
        body_h += 6
    body = (32 - body_w // 2, 46 - body_h // 2, 32 + body_w // 2, 46 + body_h // 2)
    _ellipse(draw, body, pal.mid, pal.ink)
    head_x = 57 + rng.randint(-3, 4)
    head_y = 36 + rng.randint(-4, 5)
    head_size = 13 if not rat else 10
    _ellipse(draw, (head_x - head_size, head_y - head_size, head_x + head_size, head_y + head_size), pal.dark, pal.ink)
    ear_h = 12 if cat else 8
    for side in (-1, 1):
        _poly(draw, [(head_x + side * 4, head_y - 9), (head_x + side * 11, head_y - ear_h - 7), (head_x + side * 13, head_y - 1)], pal.dark, pal.ink)
    for lx in (21, 35, 49):
        leg_len = 18 + rng.randint(-3, 4)
        _line(draw, [(lx, 55), (lx + rng.randint(-2, 2), 55 + leg_len)], pal.dark, 5, pal.ink)
    if rat:
        tail = [(15, 47), (4, 39), (3, 28), (8, 22)]
    elif cat:
        tail = [(14, 43), (5, 33), (9, 22), (17, 18)]
    else:
        tail = [(14, 47), (4, 51), (0, 43)]
    _line(draw, tail, pal.accent, 4, pal.ink)
    _eye(draw, head_x - 4, head_y - 2, 2, pal)
    _eye(draw, head_x + 4, head_y - 2, 2, pal)
    _teeth(draw, head_x, head_y + 6, 3, pal)
    if stag:
        _horns(draw, head_x, head_y - 9, 7, pal, seed)
    if "lantern" in lower:
        _rect(draw, (8, 28, 17, 40), pal.accent, pal.ink)
        draw.rectangle((11, 31, 14, 36), fill=pal.glow)
    if "ribcage" in lower or "bone" in lower:
        for i in range(4):
            draw.line((27 + i * 5, 38, 25 + i * 5, 50), fill=pal.bone, width=1)
    if key == "subaru" or "subaru" in lower:
        _poly(draw, [(39, 19), (48, 9), (57, 19), (51, 26), (45, 26)], pal.accent, pal.ink)


def _draw_humanoid(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    rng = random.Random(seed)
    x = 48 + rng.randint(-3, 3)
    robe = any(word in lower for word in ("oracle", "saint", "wraith", "doctor", "king", "monarch", "regent"))
    if robe:
        _poly(draw, [(x - 14, 36), (x + 13, 36), (x + 21, 75), (x - 20, 75)], pal.mid, pal.ink)
    else:
        _ellipse(draw, (x - 13, 35, x + 13, 65), pal.mid, pal.ink)
        _rect(draw, (x - 11, 62, x + 11, 75), pal.dark, pal.ink)
    _ellipse(draw, (x - 11, 17, x + 11, 39), pal.dark, pal.ink)
    for side in (-1, 1):
        arm = [(x + side * 12, 44), (x + side * (24 + rng.randint(-2, 4)), 55), (x + side * 20, 66)]
        _line(draw, arm, pal.mid, 5, pal.ink)
        _line(draw, [(x + side * 7, 74), (x + side * 10, 86)], pal.dark, 5, pal.ink)
    _eye(draw, x - 4, 26, 2, pal)
    _eye(draw, x + 4, 26, 2, pal)
    if "skeleton" in lower:
        for i in range(4):
            draw.line((x - 7 + i * 5, 43, x - 8 + i * 5, 58), fill=pal.bone, width=1)
        draw.rectangle((x - 5, 33, x + 5, 35), fill=pal.bone)
    if any(word in lower for word in ("king", "monarch", "regent", "crown")):
        _crown(draw, x, 15, 26, pal)
    elif any(word in lower for word in ("demon", "imp", "revenant", "warlord")):
        _horns(draw, x, 18, 8, pal, seed)
    if any(word in lower for word in ("knight", "paladin", "executioner", "warlord", "warden")):
        _line(draw, [(x + 24, 34), (x + 35, 72)], pal.accent, 4, pal.ink)
    if "doctor" in lower:
        _poly(draw, [(x + 7, 25), (x + 24, 30), (x + 8, 35)], pal.bone, pal.ink)
    if "zombie" in lower:
        draw.rectangle((x - 10, 52, x - 3, 59), fill=_mix(pal.mid, (86, 150, 82), 0.55))


def _draw_winged(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    bird = any(word in lower for word in ("swan", "roc", "harrier", "phoenix", "gryphon", "crow"))
    cx = 48
    cy = 45
    _wing(draw, cx, cy, -1, pal, seed, bird)
    _wing(draw, cx, cy, 1, pal, seed, bird)
    body_fill = pal.mid if bird else pal.dark
    _ellipse(draw, (38, 31, 58, 65), body_fill, pal.ink)
    _ellipse(draw, (39, 19, 57, 37), pal.dark, pal.ink)
    if bird:
        _poly(draw, [(56, 26), (72, 31), (57, 35)], pal.accent, pal.ink)
    else:
        _horns(draw, 48, 22, 6, pal, seed)
    _eye(draw, 45, 27, 2, pal)
    _eye(draw, 52, 27, 2, pal)
    _line(draw, [(43, 63), (38, 80)], pal.dark, 4, pal.ink)
    _line(draw, [(53, 63), (61, 80)], pal.dark, 4, pal.ink)
    if any(word in lower for word in ("seraph", "saint", "halo", "divine")):
        draw.ellipse((31, 10, 65, 20), outline=pal.glow, width=2)
    if any(word in lower for word in ("phoenix", "cinder", "fire", "ash")):
        for px in (29, 38, 57, 67):
            _poly(draw, [(px, 25), (px + 4, 10), (px + 8, 25), (px + 3, 33)], pal.accent, pal.ink)


def _draw_serpent(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    rng = random.Random(seed)
    hydra = "hydra" in lower
    leviathan = any(word in lower for word in ("leviathan", "kraken", "eel"))
    points: list[tuple[int, int]] = []
    for i in range(7):
        x = 16 + i * 11
        y = 55 + round(math.sin(i * 1.25 + (seed % 7)) * (9 + seed % 5))
        points.append((x, y))
    _line(draw, points, pal.mid, 12 + seed % 5, pal.ink)
    head_x, head_y = points[-1]
    _ellipse(draw, (head_x - 11, head_y - 10, head_x + 14, head_y + 10), pal.dark, pal.ink)
    _eye(draw, head_x - 3, head_y - 2, 2, pal)
    _eye(draw, head_x + 5, head_y - 2, 2, pal)
    _teeth(draw, head_x + 2, head_y + 5, 4, pal)
    for i in range(5):
        sx, sy = points[1 + i]
        _poly(draw, [(sx, sy - 8), (sx + 4, sy - 18), (sx + 7, sy - 7)], pal.accent, pal.ink)
    if hydra:
        for side in (-1, 1):
            nx = head_x - 15
            ny = head_y + side * 17
            _line(draw, [(head_x - 8, head_y), (nx, ny)], pal.mid, 8, pal.ink)
            _ellipse(draw, (nx - 8, ny - 7, nx + 10, ny + 7), pal.dark, pal.ink)
            _eye(draw, nx + 2, ny - 1, 2, pal)
    if leviathan:
        for i in range(4):
            sx = 35 + i * 8
            _line(draw, [(sx, 57), (sx + rng.randint(-10, 10), 80 + rng.randint(-4, 6))], pal.accent, 4, pal.ink)


def _draw_insect(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    spider = "spider" in lower or "skitter" in lower
    if not spider:
        _wing(draw, 45, 42, -1, pal, seed, False)
        _wing(draw, 51, 42, 1, pal, seed, False)
    _ellipse(draw, (38, 22, 58, 45), pal.dark, pal.ink)
    _ellipse(draw, (34, 42, 62, 70), pal.mid, pal.ink)
    leg_count = 8 if spider else 6
    for i in range(leg_count):
        side = -1 if i < leg_count // 2 else 1
        slot = i % (leg_count // 2)
        y = 36 + slot * 8
        _line(draw, [(48 + side * 8, y), (48 + side * (25 + slot * 2), y + (slot - 1) * 8)], pal.accent, 3, pal.ink)
    _eye(draw, 43, 31, 2, pal)
    _eye(draw, 53, 31, 2, pal)
    if "beetle" in lower:
        draw.line((48, 44, 48, 68), fill=pal.light, width=1)


def _draw_ghost(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    rng = random.Random(seed)
    points = [(30, 72), (30, 37), (39, 22), (52, 18), (66, 30), (68, 70)]
    for i in range(4):
        points.append((64 - i * 9, 72 + (i % 2) * 8))
    _poly(draw, points, pal.mid, pal.ink)
    _ellipse(draw, (36, 20, 62, 47), pal.dark, pal.ink)
    _eye(draw, 43, 31, 3, pal)
    _eye(draw, 55, 31, 3, pal)
    if any(word in lower for word in ("wisp", "soul", "shade")):
        _poly(draw, [(50, 13), (60, 32), (49, 47), (39, 31)], pal.accent, pal.ink)
    if any(word in lower for word in ("briar", "thorn")):
        for _ in range(5):
            x = rng.randint(29, 67)
            y = rng.randint(42, 72)
            _poly(draw, [(x, y), (x + rng.randint(-5, 5), y - 11), (x + rng.randint(-3, 5), y + 3)], pal.accent, pal.ink)


def _draw_relic(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    if any(word in lower for word in ("eye", "heart", "event horizon")):
        _ellipse(draw, (23, 24, 73, 66), pal.mid, pal.ink)
        _eye(draw, 48, 45, 12, pal)
    elif "crown" in lower:
        _crown(draw, 48, 31, 48, pal)
        _rect(draw, (27, 46, 69, 68), pal.dark, pal.ink)
        _teeth(draw, 48, 56, 8, pal)
    elif "lantern" in lower or "bell" in lower:
        _rect(draw, (35, 26, 61, 65), pal.dark, pal.ink)
        draw.rectangle((41, 33, 55, 53), fill=pal.glow)
        _line(draw, [(48, 18), (48, 26)], pal.accent, 3, pal.ink)
    else:
        _poly(draw, [(48, 13), (69, 28), (65, 64), (48, 80), (30, 64), (27, 28)], pal.mid, pal.ink)
        _poly(draw, [(48, 24), (60, 35), (58, 56), (48, 66), (37, 56), (36, 35)], pal.dark, pal.ink)
    if any(word in lower for word in ("teeth", "maw", "hunger", "chalice")):
        _teeth(draw, 48, 62, 8, pal)
    if any(word in lower for word in ("glass", "prism", "mirror", "spectrum", "rainbow", "opal")):
        for x, y in ((33, 30), (62, 37), (43, 67), (55, 59)):
            _poly(draw, [(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)], pal.accent, pal.ink)


def _draw_titan(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    _poly(draw, [(32, 23), (62, 20), (76, 47), (68, 83), (30, 83), (19, 48)], pal.mid, pal.ink)
    _ellipse(draw, (34, 11, 61, 35), pal.dark, pal.ink)
    for side in (-1, 1):
        _ellipse(draw, (48 + side * 19 - 10, 34, 48 + side * 19 + 10, 53), pal.accent, pal.ink)
        _line(draw, [(48 + side * 24, 49), (48 + side * 33, 75)], pal.mid, 7, pal.ink)
        _line(draw, [(40 + side * 9, 79), (39 + side * 12, 91)], pal.dark, 8, pal.ink)
    _eye(draw, 42, 22, 3, pal)
    _eye(draw, 54, 22, 3, pal)
    if any(word in lower for word in ("star", "orbit", "horizon", "godling")):
        draw.ellipse((16, 18, 80, 72), outline=pal.accent, width=2)
        draw.arc((10, 34, 86, 70), 185, 350, fill=pal.glow, width=2)
    if "rust" in lower:
        for x in (34, 47, 61):
            draw.rectangle((x, 46, x + 3, 64), fill=pal.accent)


def _draw_cosmic(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    spikes = 8 + seed % 5
    points: list[tuple[int, int]] = []
    for i in range(spikes * 2):
        angle = -math.pi / 2 + i * math.tau / (spikes * 2)
        radius = 34 if i % 2 == 0 else 20 + seed % 6
        points.append((48 + round(math.cos(angle) * radius), 47 + round(math.sin(angle) * radius)))
    _poly(draw, points, pal.mid, pal.ink)
    _ellipse(draw, (29, 28, 67, 66), pal.dark, pal.ink)
    _eye(draw, 48, 47, 11, pal)
    for r in (28, 37):
        draw.arc((48 - r, 47 - r // 2, 48 + r, 47 + r // 2), 195, 345, fill=pal.accent, width=2)
    if any(word in lower for word in ("hunger", "god", "apocalypse", "devours", "unwritten")):
        _teeth(draw, 48, 61, 7, pal)


def _draw_maw(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    rng = random.Random(seed)
    _ellipse(draw, (16, 25, 80, 70), pal.dark, pal.ink)
    _ellipse(draw, (24, 32, 72, 62), pal.ink, pal.ink)
    top_teeth = 7 + seed % 4
    for i in range(top_teeth):
        x = 27 + i * 6
        draw.polygon([(x, 33), (x + 5, 33), (x + 2, 44)], fill=pal.bone)
    for i in range(top_teeth - 1):
        x = 31 + i * 6
        draw.polygon([(x, 62), (x + 5, 62), (x + 2, 51)], fill=pal.bone)
    for i in range(5):
        start = (30 + i * 8, 63)
        end = (start[0] + rng.randint(-18, 18), 86 + rng.randint(-3, 5))
        _line(draw, [start, ((start[0] + end[0]) // 2, 75 + rng.randint(-4, 4)), end], pal.accent, 4, pal.ink)
    if "choir" in lower:
        for i in range(3):
            hx = 30 + i * 16
            _ellipse(draw, (hx - 6, 14, hx + 7, 28), pal.mid, pal.ink)
            _eye(draw, hx, 21, 2, pal)
    if any(word in lower for word in ("god", "apocalypse", "unwritten")):
        _crown(draw, 48, 18, 38, pal)


def _draw_orbit(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    rng = random.Random(seed)
    center_x = 48 + rng.randint(-3, 3)
    center_y = 45 + rng.randint(-4, 4)
    draw.ellipse((16, 30, 80, 62), outline=pal.accent, width=2)
    draw.arc((8, 20, 88, 72), 20, 170, fill=pal.light, width=2)
    draw.arc((8, 20, 88, 72), 200, 345, fill=pal.dark, width=2)
    if "eye" in lower:
        _ellipse(draw, (center_x - 20, center_y - 13, center_x + 20, center_y + 13), pal.mid, pal.ink)
        _eye(draw, center_x, center_y, 8, pal)
    else:
        _ellipse(draw, (center_x - 14, center_y - 14, center_x + 14, center_y + 14), pal.mid, pal.ink)
        draw.rectangle((center_x - 5, center_y - 5, center_x + 5, center_y + 5), fill=pal.glow)
    for i in range(3 + seed % 3):
        angle = i * math.tau / (3 + seed % 3) + (seed % 19)
        sx = center_x + round(math.cos(angle) * (25 + i * 4))
        sy = center_y + round(math.sin(angle) * (13 + i * 3))
        _ellipse(draw, (sx - 4, sy - 4, sx + 4, sy + 4), rng.choice([pal.accent, pal.light, pal.dark]), pal.ink)
    if any(word in lower for word in ("crown", "lord", "monarch")):
        _crown(draw, center_x, 20, 30, pal)


def _draw_chimera(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    rng = random.Random(seed)
    _ellipse(draw, (22, 38, 63, 65), pal.mid, pal.ink)
    head_count = 2 if any(word in lower for word in ("chimera", "manticore")) else 1
    for i in range(head_count):
        hx = 62 + i * 10
        hy = 34 + i * 8
        _ellipse(draw, (hx - 9, hy - 8, hx + 10, hy + 8), pal.dark, pal.ink)
        _eye(draw, hx - 3, hy - 1, 2, pal)
        _eye(draw, hx + 4, hy - 1, 2, pal)
        _teeth(draw, hx + 1, hy + 5, 3, pal)
    if any(word in lower for word in ("manticore", "chimera", "ravager")):
        _wing(draw, 38, 42, -1, pal, seed, False)
        _wing(draw, 43, 42, 1, pal, seed, False)
    for lx in (29, 42, 55):
        _line(draw, [(lx, 61), (lx + rng.randint(-2, 3), 82)], pal.dark, 5, pal.ink)
    if any(word in lower for word in ("manticore", "thorn", "ravager")):
        _line(draw, [(22, 44), (9, 31), (12, 18)], pal.accent, 5, pal.ink)
        _poly(draw, [(12, 17), (18, 26), (7, 25)], pal.bone, pal.ink)
    else:
        _line(draw, [(22, 48), (10, 50), (4, 43)], pal.accent, 5, pal.ink)
    if "stalker" in lower or "bone" in lower:
        for x in (32, 41, 50):
            draw.line((x, 43, x - 2, 57), fill=pal.bone, width=1)


def _draw_lizard(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    rng = random.Random(seed)
    _ellipse(draw, (20, 42, 64, 63), pal.mid, pal.ink)
    _ellipse(draw, (58, 35, 78, 52), pal.dark, pal.ink)
    _line(draw, [(21, 50), (8, 46), (2, 39)], pal.accent, 5, pal.ink)
    for lx in (27, 43, 59):
        _line(draw, [(lx, 59), (lx + rng.randint(-3, 3), 77)], pal.dark, 4, pal.ink)
    for i in range(5):
        x = 30 + i * 7
        _poly(draw, [(x, 42), (x + 4, 32), (x + 8, 43)], pal.accent, pal.ink)
    _eye(draw, 65, 42, 2, pal)
    _eye(draw, 72, 42, 2, pal)


def _draw_fish(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    _ellipse(draw, (24, 36, 68, 58), pal.mid, pal.ink)
    _poly(draw, [(24, 47), (10, 34), (10, 61)], pal.accent, pal.ink)
    _poly(draw, [(47, 36), (57, 22), (61, 38)], pal.light, pal.ink)
    _poly(draw, [(44, 58), (56, 72), (61, 56)], pal.dark, pal.ink)
    _eye(draw, 61, 43, 2, pal)
    if "angler" in lower:
        _line(draw, [(58, 36), (65, 24), (73, 21)], pal.accent, 2, pal.ink)
        draw.rectangle((73, 19, 77, 23), fill=pal.glow)
    if "grave" in lower:
        for x in (33, 42, 51):
            draw.line((x, 41, x - 2, 55), fill=pal.bone, width=1)


def _draw_hand(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    _ellipse(draw, (33, 42, 63, 73), pal.mid, pal.ink)
    fingers = [(35, 43, 25, 19), (42, 39, 37, 14), (49, 38, 50, 12), (56, 41, 63, 17), (61, 48, 77, 34)]
    for x1, y1, x2, y2 in fingers:
        _line(draw, [(x1, y1), (x2, y2)], pal.dark, 6, pal.ink)
        _ellipse(draw, (x2 - 3, y2 - 3, x2 + 3, y2 + 3), pal.bone, pal.ink)
    _eye(draw, 45, 55, 2, pal)
    _eye(draw, 54, 55, 2, pal)


DRAWERS = {
    "beast": _draw_beast,
    "humanoid": _draw_humanoid,
    "winged": _draw_winged,
    "serpent": _draw_serpent,
    "dragon": _draw_serpent,
    "insect": _draw_insect,
    "ghost": _draw_ghost,
    "relic": _draw_relic,
    "titan": _draw_titan,
    "cosmic": _draw_cosmic,
    "maw": _draw_maw,
    "orbit": _draw_orbit,
    "chimera": _draw_chimera,
    "lizard": _draw_lizard,
    "fish": _draw_fish,
    "hand": _draw_hand,
}


def _name_fx(draw: ImageDraw.ImageDraw, name: str, key: str, pal: Palette, seed: int) -> None:
    lower = name.lower()
    rng = random.Random(seed ^ 0xF00D)
    if any(word in lower for word in ("thorn", "briar", "root", "petal")):
        for _ in range(8):
            x = rng.randint(16, 78)
            y = rng.randint(28, 79)
            _poly(draw, [(x, y), (x + rng.randint(-4, 4), y - rng.randint(7, 15)), (x + rng.randint(-2, 5), y + 3)], pal.accent, pal.ink)
    if any(word in lower for word in ("fire", "ash", "ember", "cinder", "infernal", "hell", "phoenix")):
        for _ in range(6):
            x = rng.randint(22, 74)
            y = rng.randint(12, 42)
            _poly(draw, [(x, y - rng.randint(5, 11)), (x + 5, y + 5), (x, y + 10), (x - 5, y + 5)], pal.accent, pal.ink)
    if any(word in lower for word in ("glass", "mirror", "prism", "opal", "spectrum", "aurora", "rainbow")):
        for _ in range(5):
            x = rng.randint(20, 76)
            y = rng.randint(18, 74)
            _poly(draw, [(x, y - 4), (x + 5, y), (x, y + 5), (x - 5, y)], pal.glow, pal.ink)
    if any(word in lower for word in ("king", "monarch", "sovereign", "regent")) and "crown" not in lower:
        _crown(draw, 48, 11, 32, pal)


def render_creature_asset(name: str, key: str, rarity: str) -> Image.Image:
    seed = _hash_int(f"{key}:{name}:{rarity}")
    pal = _palette(name, rarity, seed)
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    _draw_shadow(draw, seed)
    _sparkles(draw, pal, seed, 20 if rarity in {"Prismatic", "Abyssal", "Void Lord", "Hidden"} else 10)
    family = _family(name, key)
    DRAWERS[family](draw, name, key, pal, seed)
    _name_fx(draw, name, key, pal, seed)

    bbox = image.getbbox()
    if bbox:
        pad = 5
        crop = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(CANVAS, bbox[2] + pad),
            min(CANVAS, bbox[3] + pad),
        )
        image = image.crop(crop)
    square = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    image.thumbnail((84, 84), Image.Resampling.NEAREST)
    square.alpha_composite(image, ((CANVAS - image.width) // 2, (CANVAS - image.height) // 2))
    return square.resize((OUT_SIZE, OUT_SIZE), Image.Resampling.NEAREST)


def _make_contact_sheet(entries: list[dict[str, Any]]) -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    cols = 8
    cell = 142
    label_h = 38
    rows = math.ceil(len(entries) / cols)
    sheet = Image.new("RGBA", (cols * cell, rows * (cell + label_h)), (34, 32, 38, 255))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 12)
        font_bold = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
        font_bold = ImageFont.load_default()

    for idx, entry in enumerate(entries):
        col = idx % cols
        row = idx // cols
        x = col * cell
        y = row * (cell + label_h)
        rarity_color = _rarity_color(str(entry["rarity"]))
        draw.rectangle((x + 4, y + 4, x + cell - 4, y + cell - 6), outline=(7, 7, 10), width=4)
        draw.rectangle((x + 7, y + 7, x + cell - 7, y + cell - 9), outline=rarity_color, width=2)
        img = Image.open(entry["path"]).convert("RGBA")
        img.thumbnail((112, 112), Image.Resampling.NEAREST)
        sheet.alpha_composite(img, (x + (cell - img.width) // 2, y + 14))
        name = str(entry["name"])
        label = name if len(name) <= 19 else name[:16] + "..."
        draw.text((x + 8, y + cell - 4), label, font=font_bold, fill=(242, 238, 230, 255))
        draw.text((x + 8, y + cell + 13), str(entry["rarity"]), font=font, fill=rarity_color)

    path = PREVIEW_DIR / "creature_contact_sheet.png"
    sheet.convert("RGB").save(path, "PNG", optimize=True)
    return path


def _write_asset(target: CreatureTarget, config: dict[str, Any]) -> dict[str, Any]:
    path = OUT_DIR / f"{target.key}.png"
    image = render_creature_asset(target.name, target.key, target.rarity)
    image.save(path, "PNG", optimize=True)
    raw = path.read_bytes()
    relative_path = str(path.relative_to(ASSET_DIR)).replace("\\", "/")
    record = {
        "file": relative_path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "updated_at": int(time.time()),
        "generated_style": "unique_pixel_sprite_v2",
    }
    creature_records = config.setdefault("assets", {}).setdefault("creatures", {})
    for alias in sorted(target.aliases | {target.key}):
        if not alias:
            continue
        existing = creature_records.get(alias, {})
        if not isinstance(existing, dict):
            existing = {}
        existing.update(record)
        existing.pop("url", None)
        existing.pop("placeholder", None)
        creature_records[alias] = existing
    return {
        "name": target.name,
        "key": target.key,
        "aliases": sorted(target.aliases | {target.key}),
        "rarity": target.rarity,
        "family": _family(target.name, target.key),
        "source": target.source,
        "path": str(path.relative_to(ROOT_DIR)),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    manifest: list[dict[str, Any]] = []
    targets = _collect_targets()
    for target in targets:
        manifest.append(_write_asset(target, config))

    contact = _make_contact_sheet(
        [{"name": row["name"], "rarity": row["rarity"], "path": ROOT_DIR / row["path"]} for row in manifest]
    )
    save_config(config)
    manifest_path = PREVIEW_DIR / "creature_asset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} unique pixel creature assets in {OUT_DIR}")
    print(f"Contact sheet: {contact}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
