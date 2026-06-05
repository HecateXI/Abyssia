from __future__ import annotations

import math
import random
import sys
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.content_config import ASSET_DIR, safe_key
from core.discord_assets import asset_emoji_targets
from core.rpg_data import RARITY_BY_NAME


SIZE = 64
EXPORT_SIZE = 128
INK = (4, 5, 9, 255)
BLACK = (2, 2, 5, 255)
WHITE = (255, 246, 220, 255)
SILVER = (176, 166, 156, 255)
GOLD = (236, 174, 52, 255)
RED = (202, 28, 38, 255)
PURPLE = (116, 46, 210, 255)
CYAN = (40, 210, 220, 255)
GREEN = (50, 205, 125, 255)
BLUE = (62, 150, 235, 255)


PALETTE = {
    "common": (142, 153, 166, 255),
    "uncommon": GREEN,
    "rare": BLUE,
    "epic": (156, 80, 235, 255),
    "legendary": (247, 205, 48, 255),
    "mythic": (242, 72, 94, 255),
    "ancient": (238, 121, 34, 255),
    "divine": (255, 235, 174, 255),
    "eldritch": (48, 220, 205, 255),
    "abyssal": (128, 58, 205, 255),
    "prismatic": (44, 205, 160, 255),
    "ethereal": (98, 168, 250, 255),
    "void_lord": (50, 92, 145, 255),
    "hidden": (148, 62, 235, 255),
    "bleed": (214, 32, 62, 255),
    "burn": (245, 105, 30, 255),
    "poison": (102, 205, 76, 255),
    "curse": (84, 62, 166, 255),
    "fear": (112, 108, 122, 255),
    "shield": (56, 145, 225, 255),
    "stun": (246, 216, 54, 255),
    "heal": (72, 210, 120, 255),
}

MATERIAL_COLORS = {
    "bone_fragments": (232, 220, 184, 255),
    "corrupted_essence": (128, 45, 160, 255),
    "demon_horns": (202, 45, 54, 255),
    "void_crystals": (112, 84, 220, 255),
    "ancient_relics": (197, 143, 48, 255),
    "abyssal_ichor": (27, 164, 150, 255),
    "darksteel_ingot": (90, 92, 115, 255),
    "soul_shard": (70, 210, 230, 255),
    "shadow_essence": (84, 38, 126, 255),
    "cursed_fabric": (156, 56, 67, 255),
    "void_silk": (26, 68, 136, 255),
    "phantom_core": (160, 100, 220, 255),
    "weapon_shards": (130, 125, 155, 255),
}


def _mix(a, b, t: float):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(4))


def _rgb(color):
    return color[:3]


def _hash(key: str) -> int:
    return int(sha256(key.encode("utf-8")).hexdigest()[:12], 16)


def _star(cx: int, cy: int, outer: int, inner: int, points: int = 8, rot: float = -90):
    pts = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = math.radians(rot + i * 180 / points)
        pts.append((round(cx + math.cos(a) * r), round(cy + math.sin(a) * r)))
    return pts


def _diamond(cx: int, cy: int, r: int):
    return [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]


def _new_icon(accent) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (SIZE, SIZE), BLACK)
    draw = ImageDraw.Draw(img)
    for y in range(SIZE):
        shade = 4 + int(y * 10 / max(1, SIZE - 1))
        draw.line((0, y, SIZE, y), fill=(shade, shade + 1, shade + 5, 255))
    # vignette
    for i in range(14):
        alpha = int(20 - i)
        color = (0, 0, 0, max(0, alpha))
        draw.rectangle((i, i, SIZE - 1 - i, SIZE - 1 - i), outline=color)

    frame = _mix(accent, (70, 12, 16, 255), 0.22)
    dark = _mix(frame, INK, 0.35)
    draw.rectangle((1, 1, 62, 62), outline=dark, width=2)
    draw.rectangle((3, 3, 60, 60), outline=frame, width=1)
    draw.rectangle((6, 6, 57, 57), outline=_mix(frame, WHITE, 0.16), width=1)
    for x, y, sx, sy in (
        (5, 5, 10, 0), (5, 5, 0, 10), (58, 5, -10, 0), (58, 5, 0, 10),
        (5, 58, 10, 0), (5, 58, 0, -10), (58, 58, -10, 0), (58, 58, 0, -10),
    ):
        draw.line((x, y, x + sx, y + sy), fill=frame, width=2)
    return img, draw


def _glow(draw, cx: int, cy: int, r: int, color, strength: float = 0.42):
    for i in range(6, 0, -1):
        rr = r + i * 3
        alpha = int(color[3] * strength * i / 8)
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(*_rgb(color), alpha))


def _sparks(draw, color, seed: int, count: int = 14, avoid: tuple[int, int, int, int] = (18, 16, 46, 48)):
    rng = random.Random(seed)
    for _ in range(count):
        for _attempt in range(8):
            x = rng.randint(8, 56)
            y = rng.randint(8, 56)
            if not (avoid[0] <= x <= avoid[2] and avoid[1] <= y <= avoid[3]):
                break
        size = rng.choice((1, 1, 2))
        fill = _mix(color, WHITE, rng.random() * 0.35)
        draw.rectangle((x, y, x + size, y + size), fill=fill)


def _outline(img: Image.Image, passes: int = 1) -> Image.Image:
    out = img.copy()
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


def _save(img: Image.Image, kind: str, key: str):
    out = ASSET_DIR / kind
    out.mkdir(parents=True, exist_ok=True)
    img = _outline(img, 1)
    img = img.resize((EXPORT_SIZE, EXPORT_SIZE), Image.Resampling.NEAREST)
    img.save(out / f"{safe_key(key)}.png", "PNG")
    print(f"{kind}/{safe_key(key)}.png")


def _orb(draw, cx: int, cy: int, r: int, color, *, eye: bool = False):
    _glow(draw, cx, cy, r, color)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=_mix(color, INK, 0.26), outline=INK, width=2)
    draw.arc((cx - r + 2, cy - r + 1, cx + r - 1, cy + r - 2), 205, 322, fill=_mix(color, WHITE, 0.62), width=3)
    draw.ellipse((cx - r // 3, cy - r // 2, cx + r // 4, cy - r // 5), fill=_mix(color, WHITE, 0.55))
    draw.ellipse((cx + r // 4, cy + r // 4, cx + r // 2, cy + r // 2), fill=_mix(color, INK, 0.25))
    if eye:
        draw.ellipse((cx - r + 6, cy - 6, cx + r - 6, cy + 6), fill=_mix(color, WHITE, 0.2), outline=INK, width=1)
        draw.ellipse((cx - 4, cy - 7, cx + 4, cy + 7), fill=BLACK, outline=_mix(color, WHITE, 0.55), width=1)


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _skull(draw, color):
    bone = (242, 218, 166, 255)
    blood = _mix(color, RED, 0.25)
    _glow(draw, 32, 34, 22, blood, 0.3)
    for x, y in ((12, 28), (50, 28), (20, 16), (44, 16), (18, 48), (46, 48)):
        draw.line((32, 32, x, y), fill=blood, width=4)
    draw.ellipse((17, 13, 47, 41), fill=bone, outline=INK, width=2)
    draw.rectangle((23, 35, 41, 52), fill=bone, outline=INK)
    draw.ellipse((22, 25, 30, 34), fill=BLACK)
    draw.ellipse((34, 25, 42, 34), fill=BLACK)
    draw.polygon([(32, 31), (36, 39), (28, 39)], fill=BLACK)
    for x in (25, 30, 35, 40):
        draw.line((x, 42, x, 52), fill=INK, width=1)
    for x in (16, 48, 22, 42):
        draw.line((x, 41, x, 58), fill=blood, width=2)


def _drop(draw, cx: int, cy: int, color, r: int = 16):
    pts = [(cx, cy - r), (cx + r // 2, cy - 1), (cx + r, cy + 8), (cx + 5, cy + r), (cx - 5, cy + r), (cx - r, cy + 8), (cx - r // 2, cy - 1)]
    _glow(draw, cx, cy + 3, r, color, 0.3)
    draw.polygon(pts, fill=_mix(color, INK, 0.08), outline=INK)
    draw.line((cx - 3, cy - r + 5, cx - 6, cy + 6), fill=_mix(color, WHITE, 0.58), width=2)
    draw.ellipse((cx - 5, cy + 5, cx + 5, cy + 13), fill=_mix(color, WHITE, 0.22))


def _swirl(draw, cx: int, cy: int, color):
    _glow(draw, cx, cy, 22, color, 0.42)
    for w in (8, 5, 3):
        draw.arc((cx - 24 + w, cy - 24 + w, cx + 24 - w, cy + 24 - w), 35, 330, fill=_mix(color, WHITE, 0.15), width=max(1, w // 2))
    draw.arc((cx - 15, cy - 15, cx + 15, cy + 15), 210, 570, fill=_mix(color, WHITE, 0.48), width=4)
    draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=_mix(color, INK, 0.15))


def _weapon_shape(draw, key: str, color):
    metal = _mix(color, WHITE, 0.5) if key in {"staff", "shield"} else (200, 206, 214, 255)
    wood = (118, 72, 42, 255)
    _glow(draw, 32, 34, 23, color, 0.28)
    if key == "sword":
        draw.polygon([(32, 6), (39, 32), (34, 48), (30, 48), (25, 32)], fill=metal, outline=INK)
        draw.line((34, 11, 36, 31), fill=WHITE, width=2)
        draw.rounded_rectangle((13, 35, 51, 41), radius=2, fill=GOLD, outline=INK)
        draw.rectangle((28, 40, 36, 57), fill=wood, outline=INK)
        draw.ellipse((26, 53, 38, 63), fill=GOLD, outline=INK)
    elif key == "axe":
        draw.line((34, 12, 28, 58), fill=wood, width=6)
        draw.polygon([(31, 11), (10, 23), (13, 42), (33, 31)], fill=metal, outline=INK)
        draw.polygon([(35, 11), (56, 23), (53, 42), (33, 31)], fill=metal, outline=INK)
        draw.line((17, 25, 30, 18), fill=WHITE, width=2)
    elif key == "dagger":
        draw.polygon([(32, 8), (39, 37), (32, 50), (25, 37)], fill=metal, outline=INK)
        draw.line((34, 13, 36, 34), fill=WHITE, width=2)
        draw.rounded_rectangle((15, 38, 49, 43), radius=2, fill=GOLD, outline=INK)
        draw.rectangle((28, 42, 36, 58), fill=wood, outline=INK)
    elif key == "staff":
        draw.line((33, 18, 28, 60), fill=(110, 72, 150, 255), width=6)
        draw.polygon(_star(33, 18, 22, 9, 6), fill=_mix(color, WHITE, 0.18), outline=INK)
        _orb(draw, 33, 18, 10, color)
    elif key == "shield":
        pts = [(32, 6), (54, 16), (49, 42), (32, 59), (15, 42), (10, 16)]
        draw.polygon(pts, fill=_mix(color, INK, 0.1), outline=INK)
        draw.polygon([(32, 13), (43, 20), (40, 38), (32, 48), (24, 38), (21, 20)], fill=_mix(color, WHITE, 0.12), outline=_mix(color, WHITE, 0.52))
        draw.line((32, 12, 32, 49), fill=_mix(color, WHITE, 0.42), width=2)
    elif key == "hammer":
        draw.line((33, 22, 30, 59), fill=wood, width=7)
        draw.rounded_rectangle((12, 9, 52, 27), radius=4, fill=metal, outline=INK, width=2)
        draw.rectangle((20, 12, 43, 17), fill=WHITE)
        draw.polygon([(50, 13), (60, 18), (50, 24)], fill=_mix(metal, INK, 0.2), outline=INK)
    else:
        _orb(draw, 32, 32, 18, color)


def draw_rarity(key: str):
    key = safe_key(key)
    row = RARITY_BY_NAME.get(key.replace("_", " ").title()) or RARITY_BY_NAME.get(" ".join(p.title() for p in key.split("_")))
    color = PALETTE.get(key, ((row.color >> 16) & 255, (row.color >> 8) & 255, row.color & 255, 255) if row else SILVER)
    letter = {
        "common": "C",
        "uncommon": "U",
        "rare": "R",
        "epic": "E",
        "legendary": "L",
        "mythic": "M",
        "ancient": "A",
        "divine": "D",
        "eldritch": "E",
        "abyssal": "A",
        "prismatic": "P",
        "ethereal": "E",
        "void_lord": "V",
        "hidden": "H",
    }.get(key, key[:1].upper())

    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font(46 if len(letter) == 1 else 36)
    bbox = draw.textbbox((0, 0), letter, font=font, stroke_width=0)
    x = (SIZE - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (SIZE - (bbox[3] - bbox[1])) // 2 - bbox[1] - 1

    for radius, alpha in ((5, 70), (3, 115), (1, 170)):
        for ox in range(-radius, radius + 1):
            for oy in range(-radius, radius + 1):
                if ox * ox + oy * oy <= radius * radius:
                    draw.text((x + ox, y + oy), letter, font=font, fill=(*_rgb(color), alpha))

    draw.text((x + 2, y + 3), letter, font=font, fill=(0, 0, 0, 180), stroke_width=3, stroke_fill=(0, 0, 0, 210))
    draw.text((x, y), letter, font=font, fill=_mix(color, WHITE, 0.16), stroke_width=3, stroke_fill=INK)

    mask = Image.new("L", (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((x, y), letter, font=font, fill=255)
    gradient = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gradient_pixels = gradient.load()
    top = _mix(color, WHITE, 0.55)
    bottom = _mix(color, BLACK, 0.18)
    for py in range(SIZE):
        t = py / max(1, SIZE - 1)
        base = _mix(top, bottom, t)
        for px in range(SIZE):
            gradient_pixels[px, py] = base
    img.alpha_composite(Image.composite(gradient, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask))

    if key == "prismatic":
        rainbow = [RED, GOLD, GREEN, CYAN, BLUE, PURPLE]
        prism = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(prism)
        stripe_w = max(1, SIZE // len(rainbow))
        for idx, stripe in enumerate(rainbow):
            pdraw.rectangle((idx * stripe_w, 0, (idx + 1) * stripe_w + 2, SIZE), fill=stripe)
        img.alpha_composite(Image.composite(prism, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask))

    shine = _mix(color, WHITE, 0.72)
    draw.line((x + 5, y + 8, x + 18, y + 4), fill=shine, width=2)
    _sparks(draw, color, _hash("rarity-letter:" + key), count=5, avoid=(16, 11, 48, 53))
    return img


def draw_material(key: str):
    key = safe_key(key)
    color = MATERIAL_COLORS.get(key, (125, 110, 150, 255))
    img, draw = _new_icon(color)
    _sparks(draw, color, _hash("material:" + key), count=12)
    if "bone" in key:
        for ox, oy, rot in ((0, 0, 0), (5, -4, 1)):
            draw.rounded_rectangle((14 + ox, 29 + oy, 50 + ox, 38 + oy), radius=4, fill=color, outline=INK, width=2)
            draw.ellipse((7 + ox, 25 + oy, 23 + ox, 41 + oy), fill=color, outline=INK)
            draw.ellipse((43 + ox, 25 + oy, 59 + ox, 41 + oy), fill=color, outline=INK)
    elif "horn" in key:
        draw.polygon([(15, 51), (28, 8), (39, 51)], fill=color, outline=INK)
        draw.polygon([(36, 52), (51, 13), (58, 51)], fill=_mix(color, WHITE, 0.25), outline=INK)
        draw.line((24, 22, 35, 47), fill=_mix(color, WHITE, 0.36), width=2)
    elif "crystal" in key or "shard" in key:
        draw.polygon([(31, 6), (48, 25), (42, 56), (27, 62), (14, 37)], fill=_mix(color, INK, 0.08), outline=INK)
        draw.polygon([(31, 6), (34, 37), (27, 62), (14, 37)], fill=_mix(color, WHITE, 0.18))
        draw.line((31, 7, 48, 25, 42, 56), fill=_mix(color, WHITE, 0.55), width=2)
    elif "silk" in key or "fabric" in key:
        draw.rounded_rectangle((14, 16, 50, 50), radius=5, fill=_mix(color, INK, 0.05), outline=INK, width=2)
        for i in range(5):
            y = 21 + i * 6
            draw.arc((10, y - 8, 55, y + 14), 0, 180, fill=_mix(color, WHITE, 0.25), width=2)
        draw.line((18, 16, 46, 50), fill=_mix(color, INK, 0.25), width=2)
    elif "ingot" in key:
        draw.polygon([(15, 24), (48, 18), (56, 40), (22, 48)], fill=_mix(color, WHITE, 0.12), outline=INK)
        draw.polygon([(20, 26), (46, 22), (50, 34), (24, 39)], fill=_mix(color, WHITE, 0.32))
        draw.line((17, 42, 53, 35), fill=_mix(color, INK, 0.25), width=2)
    elif "ichor" in key or "essence" in key:
        _drop(draw, 32, 29, color, 18)
        draw.ellipse((18, 45, 47, 55), fill=_mix(color, INK, 0.12), outline=INK)
    elif "relic" in key:
        draw.polygon(_star(32, 29, 24, 11, 7), fill=color, outline=INK)
        _orb(draw, 32, 31, 10, _mix(color, WHITE, 0.22))
    elif "core" in key:
        _orb(draw, 32, 32, 18, color)
        draw.ellipse((22, 22, 42, 42), outline=_mix(color, WHITE, 0.45), width=3)
    else:
        _orb(draw, 32, 32, 18, color)
    return img


def draw_status_like(key: str, kind: str):
    key = safe_key(key)
    color = PALETTE.get(key, MATERIAL_COLORS.get(key, PURPLE))
    img, draw = _new_icon(color)
    _sparks(draw, color, _hash(kind + ":" + key), count=13)
    if key in {"bleed", "burn", "poison", "heal"}:
        _drop(draw, 32, 28, color, 17)
        if key == "burn":
            draw.polygon([(32, 9), (44, 31), (38, 28), (43, 49), (32, 40), (24, 53), (26, 35), (17, 40), (24, 25)], fill=_mix(color, WHITE, 0.16), outline=INK)
        elif key == "heal":
            draw.rectangle((28, 16, 36, 49), fill=WHITE)
            draw.rectangle((16, 28, 49, 36), fill=WHITE)
    elif key == "shield":
        _weapon_shape(draw, "shield", color)
    elif key == "stun":
        draw.polygon([(36, 7), (20, 34), (32, 32), (28, 58), (48, 24), (36, 28)], fill=color, outline=INK)
        draw.line((35, 11, 27, 29, 35, 27), fill=WHITE, width=2)
    elif key == "crit":
        draw.polygon(_star(32, 32, 24, 9, 8), fill=color, outline=INK)
        draw.line((32, 12, 32, 52), fill=WHITE, width=2)
        draw.line((12, 32, 52, 32), fill=WHITE, width=2)
    elif key == "curse":
        _orb(draw, 32, 32, 17, color, eye=True)
    elif key == "fear":
        draw.polygon([(32, 10), (52, 46), (32, 58), (12, 46)], fill=_mix(color, INK, 0.1), outline=INK)
        draw.ellipse((23, 32, 30, 39), fill=WHITE)
        draw.ellipse((34, 32, 41, 39), fill=WHITE)
    else:
        _orb(draw, 32, 32, 18, color)
    return img


def draw_crate(key: str):
    colors = {
        "cache": ((126, 88, 48, 255), GOLD),
        "relic": ((62, 72, 148, 255), PURPLE),
        "treasure": ((162, 92, 28, 255), CYAN),
    }
    body, jewel = colors.get(safe_key(key), ((120, 90, 60, 255), GOLD))
    img, draw = _new_icon(jewel)
    _sparks(draw, jewel, _hash("crate:" + key), count=10)
    _glow(draw, 32, 34, 20, jewel, 0.25)
    draw.rounded_rectangle((11, 20, 53, 52), radius=4, fill=body, outline=INK, width=2)
    draw.rectangle((11, 28, 53, 35), fill=_mix(body, INK, 0.25))
    draw.line((20, 20, 20, 52), fill=_mix(body, WHITE, 0.28), width=2)
    draw.line((45, 20, 45, 52), fill=_mix(body, INK, 0.22), width=2)
    draw.polygon(_diamond(32, 28, 9), fill=jewel, outline=INK)
    return img


def draw_currency(key: str):
    key = safe_key(key)
    color = MATERIAL_COLORS.get(key, {"souls": GOLD, "gold": GOLD, "gems": CYAN, "void_crystals": PURPLE, "corrupted_essence": (130, 48, 150, 255)}.get(key, GOLD))
    img, draw = _new_icon(color)
    _sparks(draw, color, _hash("currency:" + key), count=11)
    if key in {"gems", "void_crystals"}:
        return draw_material("void_crystals" if key == "void_crystals" else "soul_shard")
    if key == "corrupted_essence":
        return draw_material("corrupted_essence")
    _orb(draw, 32, 32, 19, color)
    draw.ellipse((20, 20, 44, 44), outline=_mix(color, WHITE, 0.5), width=3)
    draw.polygon(_star(32, 32, 10, 5, 6), fill=_mix(color, WHITE, 0.18), outline=INK)
    return img


def draw_buff(key: str):
    key = safe_key(key)
    sigil = "blood" in key or "dread" in key or "sovereign" in key
    color = RED if sigil else PURPLE
    accent = GOLD if sigil else CYAN
    img, draw = _new_icon(color)
    _sparks(draw, accent, _hash("buff:" + key), count=17)
    if sigil:
        if "sovereign" in key:
            draw.polygon(_star(32, 31, 25, 10, 8), fill=GOLD, outline=INK)
            _drop(draw, 32, 31, RED, 10)
        elif "dread" in key or "abyssal" in key:
            _skull(draw, RED)
        else:
            draw.ellipse((13, 13, 51, 51), outline=RED, width=5)
            _drop(draw, 32, 31, RED, 13)
    else:
        if "singularity" in key:
            _swirl(draw, 32, 32, CYAN)
            _orb(draw, 32, 32, 9, PURPLE)
        elif "eldritch" in key or "deep" in key:
            _orb(draw, 32, 32, 17, CYAN, eye=True)
        else:
            _swirl(draw, 32, 32, PURPLE)
    return img


def draw_equipment(key: str):
    k = safe_key(key)
    if any(s in k for s in ("sword", "blade", "cleaver", "soulreaper")):
        img, draw = _new_icon(RED if "blood" in k or "abyssal" in k else GOLD)
        _sparks(draw, RED, _hash("eq:" + k), count=12)
        _weapon_shape(draw, "sword", RED if "blood" in k or "abyssal" in k else GOLD)
        return img
    if any(s in k for s in ("charm", "talisman", "eye", "crown", "sigil")):
        img, draw = _new_icon(PURPLE)
        _sparks(draw, CYAN, _hash("eq:" + k), count=14)
        if "eye" in k:
            _orb(draw, 32, 32, 18, CYAN, eye=True)
        elif "crown" in k:
            draw.polygon([(13, 45), (18, 20), (28, 35), (32, 13), (38, 35), (48, 20), (53, 45)], fill=GOLD, outline=INK)
            _orb(draw, 32, 38, 8, PURPLE)
        else:
            _swirl(draw, 32, 32, PURPLE)
        return img
    img, draw = _new_icon(SILVER)
    _orb(draw, 32, 32, 18, SILVER)
    return img


def draw_ui(key: str):
    key = safe_key(key)
    color = {
        "battle": RED, "hunt": GREEN, "shop": GOLD, "inventory": CYAN,
        "crafting": GOLD, "forge": RED, "leaderboard": GOLD,
        "profile": PURPLE, "market": GREEN, "marketplace": GREEN,
        "quest": BLUE, "boss_raid": RED, "settings": SILVER,
        "daily": GOLD, "team": BLUE, "sell": RED,
    }.get(key, CYAN)
    img, draw = _new_icon(color)
    _sparks(draw, color, _hash("ui:" + key), count=9)
    if key in {"battle", "hunt"}:
        _weapon_shape(draw, "sword", color)
    elif key in {"shop", "market", "marketplace"}:
        draw.rounded_rectangle((14, 21, 50, 48), radius=4, fill=_mix(color, INK, 0.1), outline=INK, width=2)
        draw.line((17, 29, 47, 29), fill=_mix(color, WHITE, 0.4), width=2)
        _orb(draw, 32, 42, 7, GOLD)
    elif key in {"inventory", "crate"}:
        return draw_crate("cache")
    elif key == "leaderboard":
        for i, h in enumerate((18, 28, 38)):
            draw.rectangle((16 + i * 12, 52 - h, 24 + i * 12, 52), fill=_mix(color, WHITE, i * 0.12), outline=INK)
    elif key == "team":
        for cx, cy in ((23, 26), (41, 26), (32, 42)):
            _orb(draw, cx, cy, 9, color)
    elif key == "settings":
        draw.polygon(_star(32, 32, 22, 15, 10), fill=color, outline=INK)
        draw.ellipse((23, 23, 41, 41), fill=BLACK, outline=_mix(color, WHITE, 0.5), width=2)
    else:
        _orb(draw, 32, 32, 18, color)
    return img


def draw_zone_or_boss(kind: str, key: str):
    color = RED if kind == "bosses" else BLUE
    if "void" in key or "abyss" in key:
        color = PURPLE
    if "blood" in key or "infernal" in key or "boss" in key:
        color = RED
    img, draw = _new_icon(color)
    _sparks(draw, color, _hash(kind + ":" + key), count=14)
    if kind == "bosses":
        _skull(draw, color)
    else:
        draw.polygon(_diamond(32, 32, 24), fill=_mix(color, INK, 0.12), outline=INK)
        draw.arc((12, 12, 52, 52), 215, 35, fill=_mix(color, WHITE, 0.38), width=3)
        draw.polygon([(32, 12), (42, 32), (32, 54), (22, 32)], fill=_mix(color, WHITE, 0.12), outline=INK)
    return img


def draw_icon(kind: str, key: str) -> Image.Image:
    k = safe_key(key)
    if kind == "rarity":
        return draw_rarity(k)
    if kind == "materials":
        return draw_material(k)
    if kind == "weapons":
        img, draw = _new_icon({"staff": PURPLE, "shield": BLUE, "hammer": GOLD, "axe": RED, "dagger": CYAN}.get(k, RED))
        _sparks(draw, {"staff": PURPLE, "shield": BLUE, "hammer": GOLD, "axe": RED, "dagger": CYAN}.get(k, RED), _hash("weapon:" + k), count=12)
        _weapon_shape(draw, k, {"staff": PURPLE, "shield": BLUE, "hammer": GOLD, "axe": RED, "dagger": CYAN}.get(k, RED))
        return img
    if kind in {"passives", "status"}:
        return draw_status_like(k, kind)
    if kind == "crate":
        return draw_crate(k)
    if kind == "currency":
        return draw_currency(k)
    if kind == "buffs":
        return draw_buff(k)
    if kind == "equipment":
        return draw_equipment(k)
    if kind == "ui":
        return draw_ui(k)
    if kind == "consumable":
        img, draw = _new_icon(CYAN)
        _sparks(draw, CYAN, _hash("consumable:" + k), count=12)
        _weapon_shape(draw, "sword", CYAN)
        draw.polygon(_star(48, 14, 7, 3, 5), fill=CYAN, outline=INK)
        return img
    if kind in {"zones", "bosses"}:
        return draw_zone_or_boss(kind, k)
    img, draw = _new_icon(PURPLE)
    _orb(draw, 32, 32, 18, PURPLE)
    return img


def main() -> None:
    for kind, keys in asset_emoji_targets():
        if kind == "creatures":
            continue
        for key in keys:
            _save(draw_icon(kind, key), kind, key)


if __name__ == "__main__":
    main()
