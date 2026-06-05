from __future__ import annotations

import argparse
import math
import os
import sqlite3
import sys
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.content_config import safe_key
from core.rpg_data import CHARMS, CREATURES, MATERIALS, RARITY_BY_NAME, SIGILS


ASSET_DIR = ROOT_DIR / "data" / "assets"
SIZE = 64
EXPORT_SIZE = 128
INK = (8, 9, 14, 255)
WHITE = (255, 255, 255, 255)
GOLD = (245, 195, 72, 255)
CYAN = (55, 225, 210, 255)
RED = (222, 54, 72, 255)
PURPLE = (158, 88, 235, 255)
FRAME_NEUTRAL = (92, 86, 105, 255)

RARITY_FALLBACK = (139, 148, 158, 255)
INFUSED_COLORS = {
    "Ruby": (235, 60, 80, 255),
    "Emerald": (60, 210, 120, 255),
    "Sapphire": (60, 140, 235, 255),
    "Diamond": (220, 230, 245, 255),
    "Abyssal": (130, 65, 210, 255),
}


def _mix(a: tuple[int, int, int, int], b: tuple[int, int, int, int], t: float) -> tuple[int, int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(4))


def _img(frame_color: tuple[int, int, int, int] = FRAME_NEUTRAL) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (SIZE, SIZE), (2, 3, 6, 255))
    draw = ImageDraw.Draw(image)
    for y in range(SIZE):
        shade = 8 + int(y / max(1, SIZE - 1) * 9)
        draw.line((0, y, SIZE - 1, y), fill=(shade, shade + 1, shade + 5, 255))
    draw.rectangle((1, 1, SIZE - 2, SIZE - 2), outline=_mix(frame_color, INK, 0.28), width=2)
    draw.rectangle((3, 3, SIZE - 4, SIZE - 4), outline=frame_color, width=1)
    draw.rectangle((6, 6, SIZE - 7, SIZE - 7), outline=_mix(frame_color, WHITE, 0.15), width=1)
    for sx, sy, dx, dy in ((6, 6, 1, 0), (6, 6, 0, 1), (SIZE - 7, 6, -1, 0), (SIZE - 7, 6, 0, 1),
                           (6, SIZE - 7, 1, 0), (6, SIZE - 7, 0, -1), (SIZE - 7, SIZE - 7, -1, 0), (SIZE - 7, SIZE - 7, 0, -1)):
        draw.line((sx, sy, sx + dx * 5, sy + dy * 5), fill=frame_color, width=2)
    return image, draw


def _save(image: Image.Image, kind: str, key: str) -> None:
    out = ASSET_DIR / kind
    out.mkdir(parents=True, exist_ok=True)
    if image.size != (EXPORT_SIZE, EXPORT_SIZE):
        image = image.resize((EXPORT_SIZE, EXPORT_SIZE), Image.Resampling.NEAREST)
    image.save(out / f"{key}.png", "PNG")
    print(f"{kind}/{key}.png")


def _soft_disc(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple[int, int, int, int]) -> None:
    for i in range(5, 0, -1):
        alpha = int(color[3] * i / 16)
        rr = r + i * 3
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(*color[:3], alpha))


def _pixel_sparkles(draw: ImageDraw.ImageDraw, color: tuple[int, int, int, int], salt: int) -> None:
    for i in range(10):
        x = 9 + ((salt >> (i % 8)) + i * 11) % 46
        y = 9 + ((salt >> ((i + 3) % 8)) + i * 7) % 46
        if 20 <= x <= 44 and 18 <= y <= 48:
            continue
        size = 1 + ((salt >> i) & 1)
        draw.rectangle((x, y, x + size, y + size), fill=_mix(color, WHITE, 0.12))


def _outline(image: Image.Image, passes: int = 2) -> Image.Image:
    out = image.copy()
    for _ in range(passes):
        src = out.copy()
        spx = src.load()
        opx = out.load()
        for y in range(SIZE):
            for x in range(SIZE):
                if spx[x, y][3]:
                    continue
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < SIZE and 0 <= ny < SIZE and spx[nx, ny][3]:
                        opx[x, y] = INK
                        break
    return out


def _star_points(cx: int, cy: int, outer: int, inner: int, points: int = 5) -> list[tuple[int, int]]:
    coords = []
    for i in range(points * 2):
        radius = outer if i % 2 == 0 else inner
        angle = math.radians(-90 + i * 180 / points)
        coords.append((round(cx + math.cos(angle) * radius), round(cy + math.sin(angle) * radius)))
    return coords


def _diamond(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill, outline=INK, width: int = 2) -> None:
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    draw.polygon(pts, fill=fill)
    for i in range(width):
        pts_i = [(cx, cy - r + i), (cx + r - i, cy), (cx, cy + r - i), (cx - r + i, cy)]
        draw.line(pts_i + [pts_i[0]], fill=outline, width=1)


def _sword(draw: ImageDraw.ImageDraw, cx: int, cy: int, color=(194, 205, 222, 255)) -> None:
    draw.polygon([(cx, 7), (cx + 7, 30), (cx + 2, 47), (cx - 2, 47), (cx - 7, 30)], fill=color)
    draw.line((cx + 2, 12, cx + 4, 29), fill=WHITE, width=2)
    draw.rounded_rectangle((cx - 18, 32, cx + 18, 38), radius=2, fill=(132, 88, 48, 255), outline=INK)
    draw.rectangle((cx - 4, 37, cx + 4, 54), fill=(92, 55, 36, 255), outline=INK)
    draw.ellipse((cx - 6, 50, cx + 6, 62), fill=GOLD, outline=INK)


def _axe(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    draw.line((cx, 10, cx, 58), fill=(132, 88, 48, 255), width=6)
    draw.polygon([(cx - 2, 11), (cx - 26, 21), (cx - 23, 39), (cx - 2, 32)], fill=(168, 178, 194, 255), outline=INK)
    draw.polygon([(cx + 2, 11), (cx + 25, 21), (cx + 23, 39), (cx + 2, 32)], fill=(168, 178, 194, 255), outline=INK)
    draw.line((cx - 18, 24, cx - 4, 19), fill=WHITE, width=2)


def _dagger(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    draw.polygon([(cx, 8), (cx + 6, 37), (cx, 48), (cx - 6, 37)], fill=(210, 218, 232, 255), outline=INK)
    draw.line((cx + 1, 13, cx + 3, 35), fill=WHITE, width=2)
    draw.rounded_rectangle((cx - 15, 36, cx + 15, 41), radius=2, fill=(116, 72, 48, 255), outline=INK)
    draw.rectangle((cx - 3, 40, cx + 3, 56), fill=(82, 48, 36, 255), outline=INK)


def _staff(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    draw.line((cx, 18, cx, 58), fill=(100, 65, 136, 255), width=6)
    _soft_disc(draw, cx, 16, 13, PURPLE)
    draw.ellipse((cx - 13, 3, cx + 13, 29), fill=(116, 72, 210, 255), outline=INK, width=2)
    draw.ellipse((cx - 6, 9, cx + 6, 21), fill=(218, 184, 255, 255))


def _shield(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    pts = [(cx, 5), (cx + 23, 15), (cx + 19, 42), (cx, 60), (cx - 19, 42), (cx - 23, 15)]
    draw.polygon(pts, fill=(50, 80, 130, 255), outline=INK)
    inner = [(cx, 12), (cx + 13, 20), (cx + 10, 38), (cx, 48), (cx - 10, 38), (cx - 13, 20)]
    draw.polygon(inner, fill=(92, 145, 205, 255), outline=(175, 220, 255, 255))


def _hammer(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    draw.line((cx, 20, cx, 58), fill=(132, 88, 48, 255), width=7)
    draw.rounded_rectangle((cx - 23, 8, cx + 23, 25), radius=4, fill=(145, 156, 172, 255), outline=INK, width=2)
    draw.rectangle((cx - 16, 11, cx + 16, 15), fill=(195, 205, 218, 255))


def make_weapon(key: str) -> None:
    image, draw = _img((176, 154, 112, 255))
    _soft_disc(draw, 32, 34, 22, (95, 110, 150, 255))
    _pixel_sparkles(draw, (190, 205, 225, 255), _hash_int(key))
    {"sword": _sword, "axe": _axe, "dagger": _dagger, "staff": _staff, "shield": _shield, "hammer": _hammer}[key](draw, 32, 32)
    _save(_outline(image), "weapons", key)


def make_buff(key: str, sigil: bool, rank: int) -> None:
    base = RED if sigil else PURPLE
    accent = GOLD if sigil else CYAN
    image, draw = _img(base)
    _soft_disc(draw, 32, 32, 24, base)
    _pixel_sparkles(draw, accent, _hash_int(key))
    if sigil:
        if rank == 1:
            draw.line((6, 32, 58, 32), fill=base, width=3)
            draw.line((32, 6, 32, 58), fill=base, width=3)
            draw.ellipse((16, 16, 48, 48), outline=base, width=4)
            draw.ellipse((23, 23, 41, 41), outline=INK, width=2)
            draw.polygon([(32, 21), (40, 36), (32, 50), (24, 36)], fill=base, outline=INK)
            draw.arc((10, 10, 54, 54), 25, 155, fill=_mix(base, WHITE, 0.15), width=2)
        elif rank == 2:
            draw.ellipse((13, 9, 51, 48), fill=base, outline=INK, width=2)
            for x, y in ((10, 31), (16, 17), (48, 17), (54, 31)):
                draw.polygon([(32, 32), (x, y), (x + (1 if x < 32 else -1) * 7, y + 6)], fill=base, outline=INK)
            bone = (230, 214, 176, 255)
            draw.ellipse((21, 15, 43, 38), fill=bone, outline=INK, width=2)
            _eyes(draw, (27, 26), (37, 26), (10, 5, 7, 255))
            draw.rectangle((25, 36, 39, 49), fill=bone, outline=INK)
            for tx in (27, 32, 37):
                draw.line((tx, 39, tx, 49), fill=INK, width=1)
            for dx in (17, 47, 55):
                draw.line((dx, 43, dx, 56), fill=base, width=3)
        elif rank == 3:
            draw.polygon([(18, 13), (46, 13), (41, 36), (23, 36)], fill=(140, 95, 34, 255), outline=INK)
            draw.arc((18, 7, 46, 25), 180, 360, fill=accent, width=3)
            draw.ellipse((23, 15, 41, 31), fill=(120, 8, 18, 255), outline=INK, width=2)
            draw.rectangle((29, 34, 35, 51), fill=(150, 103, 38, 255), outline=INK)
            draw.rectangle((21, 51, 43, 56), fill=(170, 120, 45, 255), outline=INK)
            for x in (16, 48, 25, 39):
                draw.polygon([(x, 33), (x + 3, 42), (x, 49), (x - 3, 42)], fill=base, outline=INK)
        elif rank == 4:
            pts = _star_points(32, 32, 27, 9, 8)
            draw.polygon(pts, fill=(185, 120, 36, 255), outline=INK)
            draw.polygon(_star_points(32, 32, 20, 7, 8), fill=accent, outline=INK)
            draw.ellipse((24, 24, 40, 40), fill=base, outline=INK, width=2)
            draw.ellipse((28, 28, 36, 36), fill=_mix(base, WHITE, 0.18))
            draw.line((6, 32, 58, 32), fill=base, width=2)
            draw.line((32, 6, 32, 58), fill=base, width=2)
        else:
            draw.ellipse((14, 13, 50, 49), outline=base, width=6)
            draw.arc((12, 10, 52, 52), 260, 40, fill=_mix(base, WHITE, 0.18), width=3)
            draw.polygon([(32, 19), (42, 37), (32, 53), (22, 37)], fill=base, outline=INK)
            draw.ellipse((25, 25, 39, 40), fill=_mix(base, WHITE, 0.10))
            for x, y in ((15, 47), (50, 46), (21, 17), (45, 18)):
                draw.polygon([(x, y), (x + 3, y + 8), (x, y + 14), (x - 3, y + 8)], fill=base, outline=INK)
    else:
        metal = (150, 142, 132, 255)
        if rank == 1:
            draw.ellipse((25, 5, 39, 17), outline=metal, width=3)
            draw.ellipse((15, 18, 49, 52), fill=(18, 12, 30, 255), outline=metal, width=3)
            draw.arc((22, 24, 43, 46), 110, 430, fill=base, width=4)
            draw.polygon([(32, 48), (38, 58), (32, 63), (26, 58)], fill=accent, outline=INK)
            draw.line((17, 37, 8, 47), fill=base, width=3)
            draw.line((47, 37, 56, 47), fill=base, width=3)
        elif rank == 2:
            draw.line((13, 33, 51, 33), fill=metal, width=4)
            draw.line((20, 22, 12, 45), fill=metal, width=3)
            draw.line((44, 22, 52, 45), fill=metal, width=3)
            draw.polygon(_star_points(32, 28, 18, 8, 6), fill=metal, outline=INK)
            draw.ellipse((21, 17, 43, 39), fill=(6, 5, 12, 255), outline=INK, width=2)
            draw.ellipse((28, 24, 36, 32), fill=base)
            draw.polygon([(32, 41), (38, 55), (32, 62), (26, 55)], fill=accent, outline=INK)
        elif rank == 3:
            draw.polygon([(22, 9), (42, 9), (51, 35), (32, 58), (13, 35)], fill=(72, 68, 78, 255), outline=INK)
            draw.polygon([(26, 18), (38, 18), (44, 34), (32, 52), (20, 34)], fill=(16, 12, 26, 255), outline=metal)
            _diamond(draw, 32, 34, 16, fill=base, outline=INK, width=2)
            draw.line((32, 22, 32, 47), fill=_mix(accent, WHITE, 0.2), width=2)
            draw.polygon([(32, 52), (37, 62), (32, 64), (27, 62)], fill=accent, outline=INK)
        elif rank == 4:
            draw.ellipse((18, 7, 34, 23), outline=metal, width=3)
            draw.arc((14, 14, 52, 52), 35, 325, fill=metal, width=4)
            draw.ellipse((19, 20, 49, 50), fill=(8, 6, 18, 255), outline=INK, width=2)
            draw.arc((25, 27, 44, 45), 115, 430, fill=base, width=4)
            for x in (18, 46):
                draw.polygon([(x, 43), (x + 4, 53), (x, 61), (x - 4, 53)], fill=accent, outline=INK)
            draw.polygon([(33, 49), (38, 58), (33, 64), (28, 58)], fill=base, outline=INK)
        else:
            draw.line((8, 32, 56, 32), fill=metal, width=4)
            draw.line((32, 8, 32, 58), fill=metal, width=4)
            draw.polygon(_star_points(32, 31, 25, 10, 8), fill=metal, outline=INK)
            draw.ellipse((17, 19, 47, 43), fill=(8, 6, 18, 255), outline=INK, width=2)
            draw.ellipse((24, 22, 40, 40), fill=accent, outline=INK, width=2)
            draw.ellipse((29, 27, 35, 35), fill=(6, 4, 12, 255))
            draw.polygon([(32, 45), (38, 57), (32, 64), (26, 57)], fill=accent, outline=INK)
    for i in range(rank):
        x = 14 + i * 9
        draw.polygon(_star_points(x, 54, 4, 2), fill=accent)
    _save(_outline(image), "buffs", key)


def make_currency(key: str, color: tuple[int, int, int, int], shape: str) -> None:
    image, draw = _img(color)
    _soft_disc(draw, 32, 32, 22, color)
    _pixel_sparkles(draw, color, _hash_int(key))
    if shape == "coin":
        draw.ellipse((13, 13, 51, 51), fill=color, outline=INK, width=2)
        draw.ellipse((20, 20, 44, 44), outline=_mix(color, WHITE, 0.45), width=3)
        draw.arc((17, 15, 48, 48), 210, 320, fill=WHITE, width=2)
    elif shape == "gem":
        _diamond(draw, 32, 32, 25, fill=color, outline=INK, width=2)
        draw.line((32, 7, 24, 32, 32, 57, 40, 32, 32, 7), fill=_mix(color, WHITE, 0.55), width=2)
    else:
        draw.polygon(_star_points(32, 32, 24, 11, 6), fill=color, outline=INK)
    _save(_outline(image), "currency", key)


def make_material(key: str, color: tuple[int, int, int, int]) -> None:
    image, draw = _img(color)
    _soft_disc(draw, 32, 32, 20, color)
    _pixel_sparkles(draw, color, _hash_int(key))
    if "bone" in key:
        draw.rounded_rectangle((16, 27, 48, 37), radius=4, fill=(222, 214, 190, 255), outline=INK)
        draw.ellipse((10, 23, 24, 37), fill=(222, 214, 190, 255), outline=INK)
        draw.ellipse((40, 23, 54, 37), fill=(222, 214, 190, 255), outline=INK)
    elif "horn" in key:
        draw.polygon([(16, 48), (29, 9), (38, 46)], fill=color, outline=INK)
        draw.polygon([(36, 48), (48, 13), (54, 46)], fill=_mix(color, WHITE, 0.2), outline=INK)
    elif "crystal" in key or "relic" in key:
        _diamond(draw, 32, 31, 24, fill=color, outline=INK, width=2)
    else:
        draw.ellipse((15, 13, 49, 51), fill=color, outline=INK, width=2)
        draw.arc((18, 18, 46, 48), 210, 320, fill=WHITE, width=2)
    _save(_outline(image), "materials", key)


def make_consumable() -> None:
    image, draw = _img(CYAN)
    _soft_disc(draw, 32, 32, 23, CYAN)
    _pixel_sparkles(draw, CYAN, _hash_int("hunt_sword"))
    _sword(draw, 32, 32, color=(210, 238, 255, 255))
    draw.polygon(_star_points(48, 14, 7, 3), fill=CYAN)
    _save(_outline(image), "consumable", "hunt_sword")


def make_crate(key: str, color: tuple[int, int, int, int], jewel: tuple[int, int, int, int]) -> None:
    image, draw = _img(jewel)
    _soft_disc(draw, 32, 32, 22, color)
    _pixel_sparkles(draw, jewel, _hash_int(key))
    draw.rounded_rectangle((12, 19, 52, 50), radius=4, fill=color, outline=INK, width=2)
    draw.rectangle((12, 27, 52, 34), fill=_mix(color, INK, 0.25))
    _diamond(draw, 32, 27, 8, fill=jewel, outline=INK, width=1)
    draw.line((19, 19, 19, 50), fill=_mix(color, WHITE, 0.28), width=2)
    draw.line((45, 19, 45, 50), fill=_mix(color, INK, 0.22), width=2)
    _save(_outline(image), "crate", key)


def make_passive(key: str, color: tuple[int, int, int, int]) -> None:
    image, draw = _img(color)
    _soft_disc(draw, 32, 32, 23, color)
    _pixel_sparkles(draw, color, _hash_int(key))
    draw.ellipse((12, 12, 52, 52), fill=color, outline=INK, width=2)
    if key == "crit":
        draw.polygon(_star_points(32, 32, 20, 8), fill=WHITE)
    elif key == "shield":
        _shield(draw, 32, 32)
    elif key == "heal":
        draw.rectangle((28, 15, 36, 49), fill=WHITE)
        draw.rectangle((15, 28, 49, 36), fill=WHITE)
    elif key == "stun":
        draw.polygon([(35, 8), (21, 34), (33, 32), (28, 56), (46, 25), (34, 28)], fill=WHITE)
    else:
        draw.ellipse((24, 18, 40, 42), fill=WHITE)
        draw.polygon([(32, 9), (41, 30), (32, 56), (23, 30)], fill=_mix(color, WHITE, 0.35))
    _save(_outline(image), "passives", key)


def make_status(key: str, color: tuple[int, int, int, int]) -> None:
    image, draw = _img(color)
    _soft_disc(draw, 32, 32, 21, color)
    _pixel_sparkles(draw, color, _hash_int(key))
    draw.ellipse((13, 13, 51, 51), fill=color, outline=INK, width=2)
    if key in {"bleed", "burn", "poison"}:
        draw.polygon([(32, 10), (45, 34), (32, 55), (19, 34)], fill=WHITE)
        draw.ellipse((26, 29, 38, 41), fill=_mix(color, INK, 0.35))
    elif key == "shield":
        _shield(draw, 32, 32)
    elif key == "heal":
        draw.rectangle((28, 16, 36, 48), fill=WHITE)
        draw.rectangle((16, 28, 48, 36), fill=WHITE)
    elif key == "stun":
        draw.polygon([(35, 8), (22, 34), (33, 32), (29, 55), (46, 25), (34, 28)], fill=WHITE)
    else:
        draw.ellipse((20, 24, 44, 38), outline=WHITE, width=4)
        draw.ellipse((28, 28, 36, 36), fill=WHITE)
    _save(_outline(image), "status", key)


def _hash_int(text: str) -> int:
    return int(sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def _rarity_color(rarity: str) -> tuple[int, int, int, int]:
    row = RARITY_BY_NAME.get(rarity)
    if not row:
        return RARITY_FALLBACK
    return ((row.color >> 16) & 255, (row.color >> 8) & 255, row.color & 255, 255)


def _infused_base(name: str) -> tuple[str, tuple[int, int, int, int] | None]:
    for prefix, color in INFUSED_COLORS.items():
        marker = prefix + " "
        if name.startswith(marker) and len(name) > len(marker):
            return name[len(marker):], color
    return name, None


def _creature_kind(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ("skeleton", "bone", "marrow", "ribcage", "glassbone", "choirbone")):
        return "skeleton"
    if any(k in n for k in ("zombie", "rotting", "plague")):
        return "zombie"
    if any(k in n for k in ("wraith", "soul", "spirit", "shade", "ghast", "revenant", "phantom", "spectre", "ghost")):
        return "ghost"
    if any(k in n for k in ("moth", "skitter", "beetle", "spider")):
        return "insect"
    if "hand" in n:
        return "hand"
    if any(k in n for k in ("crow", "bat", "harrier", "roc", "gryphon", "swan", "phoenix", "seraph", "valkyr")):
        return "winged"
    if any(k in n for k in ("dragon", "drake", "hydra", "serpent", "wyrm", "wyvern", "leviathan", "kraken", "eel", "newt", "basilisk", "angler")):
        return "reptile"
    if any(k in n for k in ("hound", "rat", "wolf", "pup", "lynx", "cat", "jackal", "stag", "hart", "kirin", "manticore", "chimera", "beast")):
        return "beast"
    if any(k in n for k in ("slime", "toad", "minnow", "imp")):
        return "blob"
    return "humanoid"


def _eyes(draw: ImageDraw.ImageDraw, left: tuple[int, int], right: tuple[int, int], color=WHITE) -> None:
    for x, y in (left, right):
        draw.ellipse((x - 3, y - 2, x + 3, y + 3), fill=INK)
        draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=color)


def _draw_skeleton_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    bone = (225, 218, 195, 255)
    draw.ellipse((20, 7, 44, 30), fill=bone, outline=INK, width=2)
    _eyes(draw, (27, 18), (37, 18), accent)
    draw.rectangle((29, 27, 35, 48), fill=bone, outline=INK)
    for y in (32, 38, 44):
        draw.line((21, y, 43, y), fill=bone, width=4)
        draw.line((21, y, 43, y), fill=INK, width=1)
    draw.line((20, 34, 10, 48), fill=bone, width=4)
    draw.line((44, 34, 54, 48), fill=bone, width=4)
    draw.line((30, 48, 23, 60), fill=bone, width=4)
    draw.line((34, 48, 42, 60), fill=bone, width=4)
    draw.arc((18, 22, 46, 38), 25, 155, fill=INK, width=1)


def _draw_zombie_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    skin = _mix((95, 150, 92, 255), accent, 0.18)
    draw.rounded_rectangle((20, 11, 44, 33), radius=8, fill=skin, outline=INK, width=2)
    draw.polygon([(19, 16), (26, 7), (39, 10), (45, 17), (37, 15), (31, 18)], fill=(42, 38, 40, 255), outline=INK)
    _eyes(draw, (27, 23), (37, 22), (255, 170, 150, 255))
    draw.rounded_rectangle((17, 32, 47, 55), radius=5, fill=shade, outline=INK, width=2)
    draw.line((18, 38, 6, 47), fill=skin, width=5)
    draw.line((46, 38, 58, 45), fill=skin, width=5)
    draw.rectangle((24, 54, 30, 62), fill=(55, 50, 62, 255), outline=INK)
    draw.rectangle((35, 54, 41, 62), fill=(55, 50, 62, 255), outline=INK)
    if h % 2:
        draw.line((24, 30, 40, 34), fill=accent, width=2)


def _draw_ghost_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    body = _mix(shade, (240, 240, 255, 255), 0.28)
    pts = [(19, 54), (19, 24), (24, 13), (32, 8), (41, 13), (46, 25), (46, 54),
           (40, 49), (35, 57), (30, 50), (24, 57)]
    draw.polygon(pts, fill=body, outline=INK)
    _eyes(draw, (28, 29), (37, 29), accent)
    draw.arc((24, 33, 42, 45), 10, 170, fill=INK, width=2)
    draw.arc((11, 15, 55, 57), 190, 345, fill=accent, width=2)


def _draw_insect_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    wing = (*accent[:3], 140)
    draw.ellipse((5, 14, 31, 45), fill=wing, outline=INK, width=2)
    draw.ellipse((33, 14, 59, 45), fill=wing, outline=INK, width=2)
    draw.ellipse((23, 12, 41, 53), fill=shade, outline=INK, width=2)
    draw.line((31, 12, 28, 4), fill=INK, width=2)
    draw.line((34, 12, 40, 4), fill=INK, width=2)
    _eyes(draw, (29, 24), (36, 24), WHITE)
    for y in (31, 38, 45):
        draw.line((24, y, 40, y), fill=_mix(accent, WHITE, 0.2), width=2)


def _draw_hand_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    skin = _mix((190, 170, 145, 255), accent, 0.12)
    for x, top in ((19, 15), (26, 8), (33, 10), (40, 17)):
        draw.rounded_rectangle((x, top, x + 7, 39), radius=4, fill=skin, outline=INK)
    draw.rounded_rectangle((18, 33, 48, 55), radius=9, fill=skin, outline=INK, width=2)
    draw.polygon([(21, 38), (8, 31), (11, 45), (23, 47)], fill=skin, outline=INK)
    draw.line((23, 48, 38, 39), fill=accent, width=2)


def _draw_winged_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    draw.polygon([(29, 29), (3, 11), (13, 47)], fill=_mix(accent, INK, 0.15), outline=INK)
    draw.polygon([(35, 29), (61, 11), (51, 47)], fill=_mix(accent, INK, 0.15), outline=INK)
    draw.ellipse((22, 16, 42, 48), fill=shade, outline=INK, width=2)
    draw.polygon([(32, 8), (39, 20), (25, 20)], fill=shade, outline=INK)
    _eyes(draw, (29, 24), (36, 24), GOLD)
    draw.polygon([(31, 27), (35, 27), (33, 32)], fill=GOLD, outline=INK)
    draw.line((28, 48, 24, 59), fill=INK, width=2)
    draw.line((36, 48, 41, 59), fill=INK, width=2)


def _draw_reptile_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    draw.ellipse((14, 20, 48, 48), fill=shade, outline=INK, width=2)
    draw.polygon([(43, 26), (62, 18), (55, 35)], fill=shade, outline=INK)
    draw.polygon([(15, 35), (2, 47), (19, 44)], fill=shade, outline=INK)
    for x in (24, 31, 38):
        draw.polygon([(x, 18), (x + 4, 8), (x + 8, 20)], fill=accent, outline=INK)
    _eyes(draw, (46, 27), (54, 25), (255, 240, 160, 255))
    if h % 3 == 0:
        draw.polygon([(21, 47), (27, 59), (31, 48)], fill=accent, outline=INK)


def _draw_beast_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    draw.ellipse((14, 27, 48, 50), fill=shade, outline=INK, width=2)
    draw.ellipse((34, 14, 55, 35), fill=shade, outline=INK, width=2)
    draw.polygon([(38, 16), (42, 5), (46, 17)], fill=shade, outline=INK)
    draw.polygon([(49, 18), (57, 9), (55, 22)], fill=shade, outline=INK)
    _eyes(draw, (43, 25), (51, 25), accent)
    draw.line((14, 34, 5, 27), fill=shade, width=5)
    for x in (20, 37):
        draw.line((x, 47, x - 3, 60), fill=shade, width=5)
    if h % 2 == 0:
        draw.arc((8, 18, 26, 38), 130, 300, fill=accent, width=3)


def _draw_blob_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    draw.ellipse((12, 19, 52, 54), fill=shade, outline=INK, width=2)
    draw.arc((16, 12, 48, 42), 200, 340, fill=_mix(accent, WHITE, 0.25), width=3)
    _eyes(draw, (27, 35), (38, 35), WHITE)
    draw.arc((25, 38, 42, 48), 10, 170, fill=INK, width=2)
    if h % 3:
        draw.ellipse((45, 14, 55, 24), fill=accent, outline=INK)


def _draw_humanoid_creature(draw: ImageDraw.ImageDraw, accent, shade, h: int) -> None:
    draw.ellipse((21, 9, 43, 31), fill=shade, outline=INK, width=2)
    if h % 2:
        draw.polygon([(22, 14), (14, 3), (28, 12)], fill=accent, outline=INK)
        draw.polygon([(42, 14), (50, 3), (36, 12)], fill=accent, outline=INK)
    else:
        draw.polygon([(20, 14), (32, 3), (44, 14)], fill=accent, outline=INK)
    _eyes(draw, (27, 21), (37, 21), WHITE)
    draw.rounded_rectangle((18, 30, 46, 56), radius=5, fill=shade, outline=INK, width=2)
    draw.line((18, 38, 8, 50), fill=shade, width=5)
    draw.line((46, 38, 56, 50), fill=shade, width=5)
    draw.line((28, 55, 24, 62), fill=INK, width=3)
    draw.line((36, 55, 40, 62), fill=INK, width=3)


CREATURE_DRAWERS = {
    "skeleton": _draw_skeleton_creature,
    "zombie": _draw_zombie_creature,
    "ghost": _draw_ghost_creature,
    "insect": _draw_insect_creature,
    "hand": _draw_hand_creature,
    "winged": _draw_winged_creature,
    "reptile": _draw_reptile_creature,
    "beast": _draw_beast_creature,
    "blob": _draw_blob_creature,
    "humanoid": _draw_humanoid_creature,
}


def make_creature(name: str, rarity: str) -> None:
    base_name, infused = _infused_base(name)
    accent = infused or _rarity_color(rarity)
    h = _hash_int(name)
    shade_seed = (
        58 + h % 38,
        48 + (h >> 4) % 36,
        70 + (h >> 8) % 46,
        255,
    )
    shade = _mix(shade_seed, accent, 0.22)
    image, draw = _img(accent)
    _soft_disc(draw, 32, 33, 23, accent)
    _pixel_sparkles(draw, accent, h)
    CREATURE_DRAWERS[_creature_kind(base_name)](draw, accent, shade, h)
    if infused:
        draw.polygon(_star_points(50, 14, 6, 3), fill=infused, outline=INK)
        draw.arc((8, 8, 56, 56), 210, 340, fill=infused, width=2)
    else:
        draw.ellipse((49, 49, 58, 58), fill=accent, outline=INK)
    _save(_outline(image), "creatures", safe_key(name))


def _db_creatures() -> list[tuple[str, str]]:
    db_path = ROOT_DIR / os.getenv("BOT_DB_PATH", "data/bot.sqlite3")
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            return [
                (str(row[0]), str(row[1] or "Common"))
                for row in conn.execute(
                    "SELECT name, COALESCE(MAX(rarity), 'Common') FROM rpg_creatures GROUP BY name"
                ).fetchall()
            ]
    except sqlite3.Error:
        return []


def main(*, include_creatures: bool = True) -> None:
    for key in ("sword", "axe", "dagger", "staff", "shield", "hammer"):
        make_weapon(key)

    for rank, sigil in enumerate(SIGILS, start=1):
        make_buff(sigil.key, True, min(rank, 5))
    for rank, charm in enumerate(CHARMS, start=1):
        make_buff(charm.key, False, min(rank, 5))

    make_currency("souls", GOLD, "coin")
    make_currency("gold", GOLD, "coin")
    make_currency("gems", CYAN, "gem")
    make_currency("void_crystals", PURPLE, "gem")
    make_currency("corrupted_essence", (112, 45, 135, 255), "star")

    material_colors = {
        "bone_fragments": (218, 210, 188, 255),
        "corrupted_essence": (112, 45, 135, 255),
        "demon_horns": (184, 52, 56, 255),
        "void_crystals": (105, 82, 210, 255),
        "ancient_relics": (186, 142, 62, 255),
        "abyssal_ichor": (28, 142, 128, 255),
    }
    for key in MATERIALS:
        make_material(key, material_colors.get(key, (130, 120, 150, 255)))

    make_consumable()
    make_crate("cache", (120, 88, 56, 255), GOLD)
    make_crate("relic", (64, 78, 145, 255), PURPLE)
    make_crate("treasure", (152, 95, 34, 255), CYAN)

    passive_colors = {
        "bleed": (194, 24, 91, 255),
        "burn": (245, 110, 24, 255),
        "poison": (108, 190, 72, 255),
        "stun": (236, 210, 54, 255),
        "shield": (45, 140, 220, 255),
        "heal": (70, 190, 100, 255),
        "crit": (178, 82, 230, 255),
    }
    for key, color in passive_colors.items():
        make_passive(key, color)

    status_colors = {
        "bleed": (194, 24, 91, 255),
        "burn": (245, 110, 24, 255),
        "poison": (108, 190, 72, 255),
        "curse": (72, 58, 155, 255),
        "fear": (78, 78, 86, 255),
        "shield": (45, 140, 220, 255),
        "stun": (236, 210, 54, 255),
        "heal": (70, 190, 100, 255),
    }
    for key, color in status_colors.items():
        make_status(key, color)

    if include_creatures:
        seen_creatures: set[str] = set()
        for creature in CREATURES:
            seen_creatures.add(safe_key(creature.name))
            make_creature(creature.name, creature.rarity)
        for name, rarity in _db_creatures():
            key = safe_key(name)
            if key in seen_creatures:
                continue
            seen_creatures.add(key)
            make_creature(name, rarity)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Abyssia pixel asset icons.")
    parser.add_argument("--skip-creatures", action="store_true", help="Regenerate only non-creature icon assets.")
    args = parser.parse_args()
    main(include_creatures=not args.skip_creatures)
