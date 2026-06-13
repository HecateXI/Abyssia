"""Generate premium Abyssia weapon/passive icon masters.

The output is deterministic raster art: transparent 512x512 PNG masters with a
dark fantasy, crisp pixel-art game-icon look. The follow-up processor creates
128x128 Discord emoji PNGs and mirrors them into data/assets for card renderers.
"""
from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

from generate_icon_prompts import all_records
from PIL import Image, ImageChops, ImageDraw

ROOT_DIR = Path(__file__).resolve().parents[1]


LOW_SIZE = 128
MASTER_SIZE = 512
OUTLINE = (5, 6, 12, 255)
BLACK = (4, 4, 8, 255)
WHITE = (246, 246, 236, 255)
BONE = (218, 205, 174, 255)
STEEL = (152, 166, 180, 255)
DARK_STEEL = (42, 48, 58, 255)
GOLD = (222, 165, 56, 255)
CYAN = (52, 220, 238, 255)
BLUE = (66, 146, 230, 255)
PURPLE = (132, 74, 225, 255)
GREEN = (80, 205, 112, 255)
RED = (204, 34, 52, 255)
ORANGE = (238, 105, 30, 255)

Color = tuple[int, int, int, int]
DrawFn = Callable[[ImageDraw.ImageDraw, str, Color], None]


PALETTE: dict[str, Color] = {
    "sword": CYAN,
    "bow": BLUE,
    "axe": RED,
    "dagger": (86, 220, 98, 255),
    "crossbow": BONE,
    "staff": PURPLE,
    "staff_of_purity": (185, 232, 255, 255),
    "shield": BLUE,
    "hammer": GOLD,
    "orb": CYAN,
    "rune": (48, 224, 204, 255),
    "soulreaper": (170, 225, 238, 255),
    "briar_relic": GREEN,
    "rot_chalice": (111, 214, 72, 255),
    "banner": (162, 54, 70, 255),
    "eye": PURPLE,
    "judgement_blade": (238, 228, 190, 255),
    "lantern": (78, 178, 240, 255),
    "mirror_relic": (178, 210, 230, 255),
    "final_bell_scythe": (218, 224, 206, 255),
    "strength": RED,
    "magic": PURPLE,
    "hp": (218, 36, 62, 255),
    "wp": BLUE,
    "pr": STEEL,
    "mr": (62, 215, 196, 255),
    "thorns": GREEN,
    "safeguard": BLUE,
    "regeneration": GREEN,
    "adaptation": (170, 150, 92, 255),
    "sacrifice": RED,
    "bleed": RED,
    "burn": ORANGE,
    "poison": (102, 218, 72, 255),
    "stun": (242, 218, 58, 255),
    "heal": GREEN,
    "crit": GOLD,
    "life_steal": RED,
    "mana_tap": BLUE,
    "soul_gain": GOLD,
    "gem_finder": (70, 220, 170, 255),
    "xp_boost": GOLD,
    "rare_finder": (205, 174, 82, 255),
    "energize": CYAN,
    "fear": (156, 120, 190, 255),
}


def _hash(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16)


def _mix(a: Color, b: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(4))  # type: ignore[return-value]


def _rgb(color: Color) -> tuple[int, int, int]:
    return color[:3]


def _star(cx: int, cy: int, outer: int, inner: int, points: int = 8, rot: float = -90) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        angle = math.radians(rot + i * 180 / points)
        out.append((round(cx + math.cos(angle) * r), round(cy + math.sin(angle) * r)))
    return out


def _diamond(cx: int, cy: int, r: int) -> list[tuple[int, int]]:
    return [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (LOW_SIZE, LOW_SIZE), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def _soft_glow(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: Color, *, strength: float = 0.35) -> None:
    for i in range(8, 0, -1):
        rr = r + i * 4
        alpha = max(0, min(125, round(color[3] * strength * i / 8)))
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(*_rgb(color), alpha))


def _sparkles(draw: ImageDraw.ImageDraw, seed: str, color: Color, *, count: int = 12) -> None:
    salt = _hash(seed)
    for i in range(count):
        x = 14 + ((salt >> (i % 16)) + i * 19) % 100
        y = 14 + ((salt >> ((i + 5) % 16)) + i * 13) % 100
        if 38 <= x <= 90 and 30 <= y <= 96:
            continue
        size = 1 + ((salt >> (i + 2)) & 1)
        draw.rectangle((x, y, x + size, y + size), fill=_mix(color, WHITE, 0.35))


def _line(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: Color, width: int = 3) -> None:
    draw.line(xy, fill=OUTLINE, width=width + 3)
    draw.line(xy, fill=fill, width=width)


def _poly(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill: Color, *, outline: Color = OUTLINE) -> None:
    draw.polygon(points, fill=outline)
    inner = []
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    for x, y in points:
        inner.append((round(cx + (x - cx) * 0.9), round(cy + (y - cy) * 0.9)))
    draw.polygon(inner, fill=fill)


def _ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: Color, *, width: int = 3) -> None:
    draw.ellipse(box, fill=fill, outline=OUTLINE, width=width)


def _rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: Color, *, radius: int = 3, width: int = 3) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=OUTLINE, width=width)


def _mist(draw: ImageDraw.ImageDraw, seed: str, color: Color) -> None:
    salt = _hash(seed)
    for i in range(5):
        x = 18 + ((salt >> i) + i * 15) % 78
        y = 76 + ((salt >> (i + 4)) + i * 7) % 28
        draw.arc((x - 18, y - 8, x + 28, y + 12), 185, 350, fill=(*_rgb(color), 80), width=2)


def _passive_plate(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    salt = _hash(f"plate:{key}")
    fill = _mix(BLACK, accent, 0.16)
    edge = _mix(accent, WHITE, 0.18)
    draw.rounded_rectangle((13, 16, 116, 118), radius=10, fill=(0, 0, 0, 96))
    draw.rounded_rectangle((12, 12, 116, 116), radius=9, fill=fill, outline=OUTLINE, width=5)
    draw.rounded_rectangle((19, 19, 109, 109), radius=6, outline=edge, width=3)
    for x, y, sx, sy in ((21, 21, 1, 1), (107, 21, -1, 1), (21, 107, 1, -1), (107, 107, -1, -1)):
        draw.line((x, y, x + sx * 16, y), fill=(*_rgb(edge), 180), width=3)
        draw.line((x, y, x, y + sy * 16), fill=(*_rgb(edge), 180), width=3)
    for i in range(4):
        y = 35 + ((salt >> (i * 3)) % 58)
        draw.line((23, y, 105, y + (i % 2) * 6 - 3), fill=(*_rgb(accent), 24), width=2)


def _finish(image: Image.Image, key: str, accent: Color) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _sparkles(draw, f"sparks:{key}", accent, count=13)
    _mist(draw, key, accent)
    image.alpha_composite(overlay)
    return image.resize((MASTER_SIZE, MASTER_SIZE), Image.Resampling.NEAREST)


def _finish_passive(image: Image.Image, key: str, accent: Color) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _sparkles(draw, f"passive-sparks:{key}", accent, count=7)
    image.alpha_composite(overlay)

    mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((10, 10, 118, 118), radius=10, fill=255)
    image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((11, 11, 117, 117), radius=9, outline=_mix(accent, WHITE, 0.24), width=4)
    draw.rounded_rectangle((17, 17, 111, 111), radius=6, outline=(*_rgb(accent), 130), width=2)
    return image.resize((MASTER_SIZE, MASTER_SIZE), Image.Resampling.NEAREST)


def _save(image: Image.Image, category: str, key: str) -> Path:
    path = ROOT_DIR / "assets" / "icons" / category / f"{key}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    return path


def _sword(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 62, 34, accent)
    _poly(draw, [(64, 9), (77, 60), (70, 91), (58, 91), (51, 60)], DARK_STEEL)
    draw.line((68, 16, 73, 59), fill=_mix(accent, WHITE, 0.35), width=3)
    draw.line((59, 18, 55, 60), fill=(16, 17, 22, 255), width=3)
    _rect(draw, (35, 83, 93, 93), _mix(BONE, GOLD, 0.12), radius=4)
    _rect(draw, (57, 91, 71, 116), _mix(BONE, BLACK, 0.25), radius=3)
    _ellipse(draw, (52, 108, 76, 126), _mix(GOLD, BONE, 0.18), width=2)


def _bow(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 66, 63, 36, accent)
    draw.arc((31, 13, 95, 114), 260, 100, fill=OUTLINE, width=10)
    draw.arc((35, 16, 91, 111), 260, 100, fill=_mix(BONE, BLACK, 0.1), width=6)
    draw.arc((44, 17, 102, 109), 80, 280, fill=(36, 25, 42, 255), width=4)
    _line(draw, (81, 19, 81, 109), _mix(accent, WHITE, 0.15), width=2)
    _line(draw, (31, 65, 91, 57), _mix(accent, WHITE, 0.35), width=3)
    _poly(draw, [(91, 57), (106, 50), (98, 64)], _mix(accent, WHITE, 0.28))
    _poly(draw, [(32, 65), (43, 59), (43, 70)], (220, 232, 245, 255))


def _axe(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 65, 64, 34, accent)
    _line(draw, (67, 21, 57, 116), (108, 72, 42, 255), width=7)
    _poly(draw, [(62, 18), (23, 36), (20, 66), (62, 54)], _mix(STEEL, RED, 0.12))
    _poly(draw, [(69, 18), (108, 36), (111, 66), (69, 54)], _mix(STEEL, RED, 0.15))
    draw.line((31, 39, 58, 27), fill=WHITE, width=3)
    draw.line((99, 41, 72, 27), fill=_mix(WHITE, RED, 0.2), width=3)
    draw.line((32, 63, 48, 58), fill=accent, width=3)


def _dagger(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 65, 62, 32, accent)
    _poly(draw, [(63, 11), (81, 55), (67, 91), (57, 91), (45, 56)], _mix(STEEL, accent, 0.18))
    draw.line((68, 18, 75, 55), fill=_mix(accent, WHITE, 0.45), width=3)
    _rect(draw, (37, 85, 91, 94), _mix(BONE, BLACK, 0.1), radius=4)
    _rect(draw, (57, 92, 72, 117), (25, 18, 25, 255), radius=3)
    draw.line((54, 102, 75, 96), fill=accent, width=2)


def _crossbow(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 35, accent)
    _line(draw, (63, 31, 63, 112), (96, 62, 40, 255), width=6)
    _line(draw, (29, 48, 99, 48), _mix(BONE, BLACK, 0.05), width=7)
    draw.arc((21, 30, 65, 78), 195, 345, fill=_mix(STEEL, BONE, 0.2), width=5)
    draw.arc((63, 30, 107, 78), 195, 345, fill=_mix(STEEL, BONE, 0.2), width=5)
    _poly(draw, [(64, 15), (72, 42), (64, 72), (56, 42)], _mix(DARK_STEEL, BONE, 0.25))
    _poly(draw, [(64, 8), (76, 23), (64, 35), (52, 23)], _mix(BONE, WHITE, 0.08))
    _line(draw, (31, 47, 98, 47), accent, width=2)


def _staff(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 49, 36, accent)
    _line(draw, (68, 32, 53, 120), (74, 48, 98, 255), width=7)
    draw.arc((44, 20, 84, 62), 30, 330, fill=_mix(accent, WHITE, 0.1), width=5)
    _ellipse(draw, (47, 12, 81, 46), _mix(accent, BLACK, 0.05), width=3)
    _poly(draw, _star(64, 28, 24, 10, 7), _mix(accent, WHITE, 0.1))
    draw.ellipse((57, 20, 71, 34), fill=_mix(WHITE, accent, 0.25))


def _staff_purity(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 48, 38, accent)
    _line(draw, (67, 35, 55, 120), (220, 225, 210, 255), width=7)
    draw.ellipse((37, 10, 91, 64), outline=OUTLINE, width=6)
    draw.ellipse((41, 14, 87, 60), outline=(20, 20, 28, 255), width=4)
    _poly(draw, [(64, 9), (80, 34), (64, 58), (48, 34)], _mix(accent, WHITE, 0.2))
    draw.rectangle((50, 29, 78, 39), fill=WHITE)
    draw.rectangle((59, 20, 69, 48), fill=WHITE)


def _shield(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 65, 36, accent)
    _poly(draw, [(64, 10), (104, 28), (94, 78), (64, 116), (34, 78), (24, 28)], _mix(accent, BLACK, 0.25))
    _poly(draw, [(64, 22), (87, 35), (81, 72), (64, 95), (47, 72), (41, 35)], _mix(accent, WHITE, 0.08), outline=_mix(accent, WHITE, 0.25))
    draw.line((64, 20, 64, 96), fill=_mix(accent, WHITE, 0.45), width=3)
    draw.arc((49, 33, 79, 57), 205, 335, fill=GOLD, width=3)
    draw.line((52, 43, 76, 43), fill=GOLD, width=3)


def _hammer(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 62, 34, accent)
    _line(draw, (66, 38, 55, 119), (102, 65, 42, 255), width=8)
    _rect(draw, (24, 19, 101, 49), _mix(STEEL, BLACK, 0.12), radius=7)
    draw.rectangle((36, 25, 83, 33), fill=_mix(WHITE, STEEL, 0.2))
    _poly(draw, [(93, 25), (116, 34), (93, 45)], _mix(STEEL, BLACK, 0.25))
    draw.arc((50, 50, 78, 82), 0, 180, fill=GOLD, width=4)
    draw.ellipse((57, 66, 72, 82), fill=GOLD, outline=OUTLINE, width=2)


def _orb(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 42, accent)
    _ellipse(draw, (34, 34, 94, 94), (5, 8, 18, 255), width=4)
    draw.ellipse((45, 45, 83, 83), fill=_mix(accent, PURPLE, 0.25), outline=_mix(accent, WHITE, 0.2), width=3)
    draw.arc((18, 43, 110, 85), 10, 185, fill=_mix(accent, WHITE, 0.15), width=4)
    draw.arc((20, 48, 108, 80), 190, 355, fill=_mix(PURPLE, accent, 0.25), width=3)
    for x, y in ((35, 25), (95, 38), (86, 99), (29, 91)):
        _poly(draw, _diamond(x, y, 8), _mix(accent, WHITE, 0.1))


def _rune(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 37, accent)
    _poly(draw, [(64, 10), (101, 34), (91, 103), (39, 109), (26, 44)], (75, 76, 82, 255))
    _poly(draw, _diamond(64, 60, 29), _mix(accent, PURPLE, 0.16), outline=OUTLINE)
    draw.line((64, 29, 64, 91), fill=_mix(accent, WHITE, 0.4), width=4)
    draw.line((37, 60, 91, 60), fill=_mix(accent, WHITE, 0.32), width=4)
    draw.line((48, 44, 80, 76), fill=_mix(accent, WHITE, 0.18), width=3)
    draw.line((80, 44, 48, 76), fill=_mix(accent, WHITE, 0.18), width=3)


def _soulreaper(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 62, 66, 36, accent)
    _line(draw, (76, 18, 48, 120), (48, 36, 48, 255), width=7)
    draw.arc((26, 10, 102, 92), 260, 85, fill=OUTLINE, width=12)
    draw.arc((31, 15, 98, 84), 260, 85, fill=_mix(STEEL, accent, 0.2), width=8)
    draw.arc((30, 38, 82, 102), 80, 250, fill=_mix(accent, WHITE, 0.15), width=3)
    for x, y in ((34, 76), (45, 93), (55, 83)):
        draw.ellipse((x - 3, y - 8, x + 3, y + 6), fill=(*_rgb(accent), 145))


def _briar_relic(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 36, accent)
    _poly(draw, [(64, 25), (82, 45), (75, 82), (64, 100), (53, 82), (46, 45)], (105, 22, 45, 255))
    _poly(draw, _diamond(64, 61, 21), _mix(accent, WHITE, 0.05))
    for offset in (-22, -10, 4, 16):
        draw.arc((30 + offset, 31, 98 + offset, 94), 40, 240, fill=(20, 70, 33, 255), width=5)
    for x, y in ((35, 52), (86, 45), (43, 86), (91, 77), (59, 34)):
        _poly(draw, [(x, y), (x + 9, y + 4), (x + 1, y + 8)], _mix(accent, BLACK, 0.1))


def _rot_chalice(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 62, 36, accent)
    _poly(draw, [(39, 31), (89, 31), (79, 75), (49, 75)], (143, 101, 43, 255))
    _rect(draw, (54, 73, 74, 102), (120, 82, 34, 255), radius=3)
    _rect(draw, (39, 101, 89, 112), (150, 108, 44, 255), radius=4)
    draw.ellipse((41, 21, 87, 40), fill=_mix(accent, WHITE, 0.03), outline=OUTLINE, width=3)
    for x, h in ((48, 17), (60, 13), (73, 19)):
        draw.ellipse((x, h, x + 10, h + 13), fill=accent, outline=OUTLINE, width=2)
    draw.line((48, 72, 44, 91), fill=accent, width=4)
    draw.line((79, 69, 86, 91), fill=(12, 12, 12, 255), width=4)


def _banner(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 63, 62, 34, accent)
    _line(draw, (43, 13, 43, 119), (94, 65, 42, 255), width=7)
    _poly(draw, [(43, 17), (101, 24), (94, 72), (43, 66)], (40, 26, 38, 255))
    _poly(draw, [(51, 27), (90, 32), (85, 62), (51, 58)], _mix(accent, BLACK, 0.35))
    draw.ellipse((58, 36, 82, 60), fill=(1, 1, 3, 255), outline=OUTLINE, width=2)
    draw.arc((54, 32, 86, 64), 225, 315, fill=GOLD, width=4)
    draw.line((62, 59, 56, 75), fill=accent, width=3)


def _eye(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 62, 38, accent)
    _rect(draw, (35, 24, 93, 105), (52, 54, 62, 255), radius=6)
    draw.rectangle((46, 35, 82, 102), fill=(6, 8, 15, 255))
    draw.arc((44, 27, 84, 54), 180, 360, fill=(96, 98, 112, 255), width=6)
    draw.ellipse((33, 47, 95, 79), fill=(206, 190, 225, 255), outline=OUTLINE, width=3)
    draw.ellipse((50, 45, 78, 81), fill=accent, outline=OUTLINE, width=3)
    draw.ellipse((58, 54, 70, 72), fill=(10, 8, 18, 255))
    draw.ellipse((62, 56, 66, 60), fill=WHITE)


def _judgement_blade(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 63, 36, accent)
    _poly(draw, [(64, 8), (79, 56), (69, 91), (59, 91), (49, 56)], _mix(STEEL, accent, 0.18))
    draw.line((68, 14, 75, 56), fill=WHITE, width=3)
    _rect(draw, (36, 83, 92, 94), GOLD, radius=4)
    _rect(draw, (57, 92, 71, 118), (55, 39, 38, 255), radius=3)
    draw.arc((45, 31, 83, 58), 205, 335, fill=GOLD, width=4)
    draw.line((48, 44, 80, 44), fill=GOLD, width=3)
    draw.line((43, 72, 28, 88), fill=GOLD, width=2)
    draw.line((85, 72, 100, 88), fill=GOLD, width=2)


def _lantern(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 65, 38, accent)
    draw.arc((46, 11, 82, 39), 180, 360, fill=OUTLINE, width=6)
    draw.arc((50, 15, 78, 35), 180, 360, fill=(126, 88, 42, 255), width=4)
    _rect(draw, (39, 36, 89, 92), (33, 34, 38, 255), radius=7)
    _rect(draw, (47, 43, 81, 84), (7, 10, 18, 255), radius=5, width=2)
    _soft_glow(draw, 64, 63, 18, accent, strength=0.52)
    _poly(draw, [(64, 44), (77, 65), (66, 83), (56, 70), (52, 83), (53, 61)], _mix(accent, WHITE, 0.2))
    _rect(draw, (46, 92, 82, 104), (70, 58, 43, 255), radius=3)


def _mirror_relic(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 35, accent)
    _ellipse(draw, (29, 20, 99, 98), (56, 58, 70, 255), width=5)
    _ellipse(draw, (39, 30, 89, 88), (165, 188, 206, 255), width=3)
    draw.line((51, 40, 74, 63), fill=WHITE, width=4)
    draw.line((77, 43, 55, 76), fill=(230, 238, 245, 255), width=2)
    draw.ellipse((52, 48, 76, 72), fill=(220, 220, 232, 255), outline=OUTLINE, width=2)
    draw.ellipse((60, 51, 68, 69), fill=accent)
    for x, y in ((38, 22), (90, 31), (87, 91), (32, 82)):
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=_mix(accent, WHITE, 0.15), outline=OUTLINE)


def _final_bell_scythe(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 66, 38, accent)
    _line(draw, (76, 15, 45, 120), (48, 36, 48, 255), width=7)
    draw.arc((28, 10, 104, 92), 260, 80, fill=OUTLINE, width=12)
    draw.arc((34, 16, 99, 82), 260, 80, fill=_mix(STEEL, accent, 0.12), width=8)
    _line(draw, (62, 45, 62, 76), GOLD, width=3)
    draw.arc((49, 70, 75, 94), 180, 360, fill=GOLD, width=5)
    draw.ellipse((55, 84, 70, 101), fill=GOLD, outline=OUTLINE, width=2)
    draw.ellipse((60, 93, 65, 98), fill=_mix(WHITE, GOLD, 0.2))


WEAPON_DRAWERS: dict[str, DrawFn] = {
    "axe": _axe,
    "banner": _banner,
    "bow": _bow,
    "briar_relic": _briar_relic,
    "crossbow": _crossbow,
    "dagger": _dagger,
    "eye": _eye,
    "final_bell_scythe": _final_bell_scythe,
    "hammer": _hammer,
    "judgement_blade": _judgement_blade,
    "lantern": _lantern,
    "mirror_relic": _mirror_relic,
    "orb": _orb,
    "rot_chalice": _rot_chalice,
    "rune": _rune,
    "shield": _shield,
    "soulreaper": _soulreaper,
    "staff": _staff,
    "staff_of_purity": _staff_purity,
    "sword": _sword,
}


def _skull(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: Color = BONE) -> None:
    _ellipse(draw, (cx - 17, cy - 21, cx + 17, cy + 12), color, width=3)
    _rect(draw, (cx - 11, cy + 6, cx + 11, cy + 25), color, radius=2, width=2)
    draw.ellipse((cx - 10, cy - 6, cx - 2, cy + 4), fill=BLACK)
    draw.ellipse((cx + 2, cy - 6, cx + 10, cy + 4), fill=BLACK)
    draw.polygon([(cx, cy + 2), (cx + 5, cy + 12), (cx - 5, cy + 12)], fill=BLACK)
    for x in (cx - 7, cx - 2, cx + 3, cx + 8):
        draw.line((x, cy + 12, x, cy + 24), fill=OUTLINE, width=1)


def _heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: Color) -> None:
    _soft_glow(draw, cx, cy, 20, color)
    _ellipse(draw, (cx - 25, cy - 24, cx - 1, cy), color, width=2)
    _ellipse(draw, (cx + 1, cy - 24, cx + 25, cy), color, width=2)
    _poly(draw, [(cx - 28, cy - 8), (cx + 28, cy - 8), (cx, cy + 34)], color)
    draw.line((cx - 10, cy - 14, cx - 16, cy + 8), fill=_mix(color, WHITE, 0.45), width=3)


def _shield_shape(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: Color) -> None:
    _poly(draw, [(cx, cy - 34), (cx + 32, cy - 18), (cx + 24, cy + 22), (cx, cy + 43), (cx - 24, cy + 22), (cx - 32, cy - 18)], color)
    draw.line((cx, cy - 25, cx, cy + 30), fill=_mix(color, WHITE, 0.35), width=3)


def _passive_strength(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 62, 35, accent)
    _poly(draw, [(45, 50), (58, 36), (82, 44), (87, 72), (75, 91), (51, 84)], (68, 55, 58, 255))
    for x in (47, 58, 69, 80):
        _rect(draw, (x - 5, 28, x + 6, 55), _mix(DARK_STEEL, accent, 0.15), radius=4, width=2)
    _rect(draw, (43, 54, 86, 84), _mix(DARK_STEEL, accent, 0.12), radius=6)
    _line(draw, (20, 64, 48, 64), BONE, width=5)
    _line(draw, (82, 64, 108, 64), BONE, width=5)
    draw.line((61, 62, 71, 49), fill=_mix(accent, WHITE, 0.2), width=3)


def _passive_magic(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 38, accent)
    draw.ellipse((29, 29, 99, 99), outline=OUTLINE, width=6)
    draw.ellipse((34, 34, 94, 94), outline=accent, width=4)
    draw.polygon(_star(64, 64, 31, 13, 6), outline=OUTLINE, fill=(0, 0, 0, 0))
    draw.line((64, 33, 91, 80), fill=_mix(accent, WHITE, 0.2), width=4)
    draw.line((37, 80, 91, 80), fill=_mix(accent, WHITE, 0.15), width=4)
    draw.line((64, 33, 37, 80), fill=_mix(accent, WHITE, 0.2), width=4)
    for x, y in ((40, 30), (93, 43), (82, 99), (27, 86)):
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=_mix(accent, WHITE, 0.35))


def _passive_hp(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _heart(draw, 64, 62, accent)
    _poly(draw, _diamond(64, 59, 18), _mix(accent, BLACK, 0.1))
    draw.line((55, 47, 72, 75), fill=_mix(WHITE, accent, 0.15), width=3)


def _passive_wp(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 38, accent)
    for x1, y1, x2, y2 in ((28, 85, 51, 57), (51, 57, 64, 88), (64, 88, 90, 37), (50, 34, 90, 37), (36, 99, 64, 88)):
        _line(draw, (x1, y1, x2, y2), _mix(accent, WHITE, 0.2), width=4)
    for x, y, r in ((28, 85, 10), (51, 57, 12), (64, 88, 11), (90, 37, 13), (50, 34, 9), (36, 99, 8)):
        _poly(draw, _diamond(x, y, r), _mix(accent, WHITE, 0.08))


def _passive_pr(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 30, accent)
    for row, y in enumerate((30, 50, 70)):
        for col in range(3):
            x = 36 + col * 20 - (10 if row % 2 else 0)
            _poly(draw, [(x, y - 13), (x + 16, y - 5), (x + 12, y + 13), (x - 4, y + 13), (x - 8, y - 5)], _mix(STEEL, BLACK, 0.08))
    draw.line((31, 37, 88, 86), fill=(24, 26, 32, 255), width=4)
    draw.line((35, 40, 82, 81), fill=_mix(WHITE, STEEL, 0.2), width=2)


def _passive_mr(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 63, 38, accent)
    _shield_shape(draw, 64, 68, (28, 36, 48, 255))
    draw.ellipse((32, 30, 96, 94), outline=accent, width=4)
    draw.arc((39, 38, 89, 86), 210, 30, fill=_mix(accent, WHITE, 0.2), width=4)
    draw.arc((39, 38, 89, 86), 30, 210, fill=_mix(PURPLE, accent, 0.2), width=3)


def _passive_thorns(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 34, accent)
    _heart(draw, 64, 69, RED)
    draw.ellipse((27, 25, 101, 99), outline=(22, 82, 34, 255), width=6)
    for x, y, _rot in ((39, 32, 0), (91, 47, 1), (36, 89, 2), (87, 88, 3), (63, 24, 0)):
        _poly(draw, [(x, y), (x + 13, y + 5), (x + 1, y + 12)], accent)


def _passive_safeguard(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 67, 36, accent)
    _skull(draw, 64, 72, BONE)
    draw.arc((21, 19, 107, 105), 200, 340, fill=OUTLINE, width=9)
    draw.arc((25, 23, 103, 101), 200, 340, fill=_mix(accent, WHITE, 0.15), width=6)
    draw.line((26, 64, 102, 64), fill=_mix(accent, WHITE, 0.08), width=3)


def _passive_regeneration(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 66, 36, accent)
    _line(draw, (36, 96, 92, 80), BONE, width=7)
    _poly(draw, [(64, 19), (81, 51), (72, 48), (82, 84), (64, 72), (50, 95), (53, 61), (42, 68), (51, 42)], accent)
    _poly(draw, [(64, 35), (73, 56), (65, 52), (69, 75), (58, 61), (57, 78), (52, 57)], _mix(WHITE, accent, 0.32), outline=accent)


def _passive_adaptation(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 34, accent)
    _shield_shape(draw, 64, 65, (76, 78, 78, 255))
    _poly(draw, [(64, 31), (93, 47), (86, 80), (64, 101)], _mix(PURPLE, BLUE, 0.2))
    draw.line((64, 30, 64, 102), fill=OUTLINE, width=4)
    draw.arc((34, 39, 94, 93), 30, 300, fill=_mix(CYAN, WHITE, 0.15), width=3)


def _passive_sacrifice(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 65, 60, 36, accent)
    _rect(draw, (38, 62, 83, 94), (14, 12, 16, 255), radius=11)
    for x in (42, 52, 62, 72):
        _rect(draw, (x, 34, x + 9, 68), (12, 10, 14, 255), radius=5, width=2)
    _heart(draw, 68, 39, accent)
    draw.line((30, 91, 45, 103), fill=OUTLINE, width=5)
    draw.line((83, 91, 98, 103), fill=OUTLINE, width=5)


def _passive_bleed(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 34, accent)
    for y in (39, 58, 77):
        _line(draw, (31, y, 94, y - 16), (220, 224, 225, 255), width=5)
        draw.line((52, y + 2, 49, y + 18), fill=accent, width=4)
    draw.ellipse((46, 85, 55, 102), fill=accent)
    draw.ellipse((75, 74, 84, 92), fill=accent)


def _passive_burn(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 65, 38, accent)
    _poly(draw, [(64, 12), (83, 45), (75, 41), (88, 91), (66, 78), (51, 108), (53, 68), (37, 78), (50, 42)], (26, 8, 10, 255))
    _poly(draw, [(64, 29), (75, 53), (69, 51), (76, 84), (63, 72), (55, 91), (55, 61), (48, 66), (55, 45)], accent)
    _poly(draw, [(63, 44), (69, 60), (64, 78), (58, 62)], _mix(WHITE, ORANGE, 0.2), outline=accent)


def _passive_poison(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 65, 34, accent)
    _rect(draw, (48, 32, 82, 94), (36, 45, 38, 255), radius=8)
    draw.rectangle((53, 22, 77, 38), fill=(55, 62, 52, 255), outline=OUTLINE, width=3)
    draw.ellipse((45, 57, 85, 97), fill=accent, outline=OUTLINE, width=3)
    _skull(draw, 65, 71, BONE)
    for x, y in ((38, 36), (90, 43), (32, 72), (92, 88)):
        draw.arc((x - 14, y - 8, x + 14, y + 8), 190, 340, fill=(*_rgb(accent), 120), width=3)


def _passive_stun(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 35, accent)
    draw.arc((42, 28, 86, 72), 180, 360, fill=GOLD, width=8)
    _poly(draw, [(46, 55), (82, 55), (89, 92), (39, 92)], _mix(GOLD, BLACK, 0.05))
    draw.line((45, 58, 88, 87), fill=OUTLINE, width=4)
    _poly(draw, [(87, 15), (66, 51), (82, 48), (72, 104), (105, 44), (87, 48)], _mix(accent, WHITE, 0.16))


def _passive_shield(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 38, accent)
    _shield_shape(draw, 64, 65, _mix(accent, BLACK, 0.1))
    draw.arc((30, 29, 98, 97), 200, 340, fill=_mix(accent, WHITE, 0.3), width=5)
    draw.line((42, 51, 86, 51), fill=WHITE, width=3)


def _passive_heal(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 38, accent)
    _heart(draw, 64, 70, RED)
    draw.arc((24, 31, 104, 101), 210, 40, fill=_mix(accent, WHITE, 0.15), width=6)
    draw.arc((24, 31, 104, 101), 40, 210, fill=accent, width=5)
    draw.rectangle((58, 34, 70, 77), fill=WHITE)
    draw.rectangle((43, 49, 85, 61), fill=WHITE)


def _passive_crit(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 34, accent)
    draw.ellipse((31, 47, 97, 81), fill=(220, 215, 200, 255), outline=OUTLINE, width=3)
    draw.ellipse((50, 43, 78, 85), fill=(18, 15, 20, 255), outline=OUTLINE, width=3)
    draw.ellipse((58, 54, 70, 74), fill=accent)
    draw.line((64, 24, 64, 105), fill=(170, 40, 45, 255), width=3)
    draw.line((23, 64, 105, 64), fill=(170, 40, 45, 255), width=3)
    draw.polygon(_star(88, 36, 11, 4, 5), fill=GOLD, outline=OUTLINE)


def _passive_life_steal(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 66, 36, accent)
    _poly(draw, [(42, 23), (56, 73), (43, 102), (32, 69)], BONE)
    _poly(draw, [(86, 23), (72, 73), (85, 102), (96, 69)], BONE)
    draw.arc((36, 56, 92, 100), 0, 180, fill=(12, 8, 12, 255), width=8)
    for x in (57, 68, 79):
        draw.line((x, 58, x - 8, 102), fill=accent, width=4)


def _passive_mana_tap(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 38, accent)
    for w in (9, 6, 4):
        draw.arc((27 + w, 27 + w, 101 - w, 101 - w), 30, 330, fill=_mix(accent, WHITE, 0.08), width=max(2, w // 2))
    draw.arc((42, 42, 86, 86), 210, 570, fill=_mix(accent, WHITE, 0.35), width=6)
    for x, y in ((31, 42), (90, 39), (86, 88)):
        _poly(draw, [(x, y - 12), (x + 9, y + 4), (x, y + 15), (x - 9, y + 4)], _mix(accent, WHITE, 0.1))


def _passive_soul_gain(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 60, 64, 34, accent)
    _ellipse(draw, (35, 35, 86, 86), GOLD, width=4)
    draw.ellipse((46, 46, 75, 75), outline=_mix(WHITE, GOLD, 0.2), width=4)
    draw.polygon(_star(61, 61, 12, 5, 6), fill=_mix(WHITE, GOLD, 0.35), outline=OUTLINE)
    draw.arc((70, 28, 112, 82), 90, 270, fill=(190, 240, 238, 150), width=4)
    draw.ellipse((91, 30, 104, 48), fill=(205, 250, 245, 155))


def _passive_gem_finder(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 35, accent)
    _poly(draw, _diamond(64, 60, 29), _mix(accent, WHITE, 0.18))
    draw.line((64, 31, 50, 60, 64, 89, 78, 60, 64, 31), fill=WHITE, width=3)
    for x, y in ((36, 51), (92, 51), (44, 83), (84, 83)):
        _poly(draw, [(x, y), (x + 15, y + 6), (x + 2, y + 14)], (11, 10, 12, 255))


def _passive_xp_boost(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 34, accent)
    _poly(draw, [(29, 42), (62, 33), (62, 95), (29, 105)], (205, 190, 150, 255))
    _poly(draw, [(66, 33), (99, 42), (99, 105), (66, 95)], (225, 212, 172, 255))
    draw.line((64, 34, 64, 98), fill=OUTLINE, width=3)
    _poly(draw, [(66, 10), (79, 39), (70, 36), (76, 62), (63, 49), (56, 67), (57, 40)], _mix(accent, ORANGE, 0.2))


def _passive_rare_finder(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 32, accent)
    draw.ellipse((30, 28, 84, 82), fill=(50, 70, 76, 150), outline=OUTLINE, width=5)
    draw.ellipse((36, 34, 78, 76), outline=_mix(CYAN, WHITE, 0.15), width=4)
    _line(draw, (75, 76, 101, 102), (110, 78, 42, 255), width=7)
    _poly(draw, _diamond(57, 55, 13), PURPLE)
    draw.polygon(_star(79, 37, 8, 3, 5), fill=GOLD, outline=OUTLINE)


def _passive_energize(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 38, accent)
    _rect(draw, (41, 35, 87, 92), (22, 34, 48, 255), radius=7)
    draw.rectangle((53, 25, 75, 38), fill=(22, 34, 48, 255), outline=OUTLINE, width=3)
    _poly(draw, [(68, 42), (50, 69), (65, 66), (58, 93), (82, 57), (67, 60)], _mix(accent, WHITE, 0.2))
    draw.arc((27, 46, 105, 104), 210, 340, fill=_mix(accent, WHITE, 0.1), width=4)


def _passive_fear(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 65, 35, accent)
    _poly(draw, [(64, 18), (91, 41), (86, 88), (64, 108), (42, 88), (37, 41)], (205, 198, 190, 255))
    draw.ellipse((50, 52, 59, 64), fill=(6, 6, 9, 255))
    draw.ellipse((69, 52, 78, 64), fill=(6, 6, 9, 255))
    draw.arc((53, 74, 75, 92), 180, 360, fill=(6, 6, 9, 255), width=4)
    for x, y in ((35, 38), (95, 50), (32, 83), (92, 93)):
        draw.arc((x - 12, y - 9, x + 12, y + 9), 180, 350, fill=(*_rgb(accent), 125), width=3)


PASSIVE_DRAWERS: dict[str, DrawFn] = {
    "adaptation": _passive_adaptation,
    "bleed": _passive_bleed,
    "burn": _passive_burn,
    "crit": _passive_crit,
    "energize": _passive_energize,
    "fear": _passive_fear,
    "gem_finder": _passive_gem_finder,
    "heal": _passive_heal,
    "hp": _passive_hp,
    "life_steal": _passive_life_steal,
    "magic": _passive_magic,
    "mana_tap": _passive_mana_tap,
    "mr": _passive_mr,
    "poison": _passive_poison,
    "pr": _passive_pr,
    "rare_finder": _passive_rare_finder,
    "regeneration": _passive_regeneration,
    "sacrifice": _passive_sacrifice,
    "safeguard": _passive_safeguard,
    "shield": _passive_shield,
    "soul_gain": _passive_soul_gain,
    "strength": _passive_strength,
    "stun": _passive_stun,
    "thorns": _passive_thorns,
    "wp": _passive_wp,
    "xp_boost": _passive_xp_boost,
}


def _generic(draw: ImageDraw.ImageDraw, key: str, accent: Color) -> None:
    _soft_glow(draw, 64, 64, 35, accent)
    _poly(draw, _star(64, 64, 32, 14, 8), _mix(accent, BLACK, 0.08))
    draw.ellipse((48, 48, 80, 80), fill=_mix(accent, WHITE, 0.18), outline=OUTLINE, width=3)


def generate_record(record: dict[str, Any]) -> Path:
    key = str(record["key"])
    category = str(record["category"])
    accent = PALETTE.get(key, PURPLE)
    image, draw = _canvas()
    drawer = WEAPON_DRAWERS.get(key) if category == "weapons" else PASSIVE_DRAWERS.get(key)
    if category == "passives":
        _passive_plate(draw, key, accent)
    (drawer or _generic)(draw, key, accent)
    finished = _finish_passive(image, key, accent) if category == "passives" else _finish(image, key, accent)
    return _save(finished, category, key)


def main() -> int:
    paths = []
    for record in all_records():
        paths.append(generate_record(record))
    for path in paths:
        print(path.relative_to(ROOT_DIR).as_posix())
    print(f"Generated {len(paths)} premium icon masters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
