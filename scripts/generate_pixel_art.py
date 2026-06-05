from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.rpg_data import CREATURES, RARITIES, normalize_key


SIZE = 64
ASSET_DIR = ROOT_DIR / "data" / "assets"
OUTLINE = (9, 10, 16, 255)
WHITE = (255, 255, 255, 255)
VOID = (15, 12, 22, 255)

RARITY_STYLE = {
    "Common": {"base": (126, 137, 151, 255), "dark": (58, 65, 75, 255), "light": (220, 230, 240, 255), "accent": (190, 200, 210, 255), "letter": "C"},
    "Uncommon": {"base": (48, 190, 115, 255), "dark": (19, 92, 58, 255), "light": (180, 255, 205, 255), "accent": (75, 255, 155, 255), "letter": "U"},
    "Rare": {"base": (48, 145, 220, 255), "dark": (17, 60, 125, 255), "light": (190, 235, 255, 255), "accent": (75, 210, 255, 255), "letter": "R"},
    "Epic": {"base": (150, 82, 220, 255), "dark": (70, 30, 118, 255), "light": (235, 200, 255, 255), "accent": (205, 105, 255, 255), "letter": "E"},
    "Legendary": {"base": (245, 194, 55, 255), "dark": (145, 95, 8, 255), "light": (255, 250, 190, 255), "accent": (255, 225, 75, 255), "letter": "L"},
    "Mythic": {"base": (236, 70, 88, 255), "dark": (138, 21, 40, 255), "light": (255, 186, 190, 255), "accent": (255, 95, 125, 255), "letter": "M"},
    "Ancient": {"base": (235, 124, 35, 255), "dark": (132, 54, 8, 255), "light": (255, 205, 130, 255), "accent": (255, 150, 55, 255), "letter": "A"},
    "Divine": {"base": (255, 240, 190, 255), "dark": (200, 140, 45, 255), "light": WHITE, "accent": (255, 255, 150, 255), "letter": "D"},
    "Eldritch": {"base": (30, 195, 175, 255), "dark": (8, 92, 95, 255), "light": (170, 255, 245, 255), "accent": (75, 255, 225, 255), "letter": "E"},
    "Abyssal": {"base": (42, 38, 68, 255), "dark": (6, 5, 14, 255), "light": (220, 120, 255, 255), "accent": (190, 55, 255, 255), "letter": "A"},
    "Prismatic": {"base": (16, 185, 129, 255), "dark": (6, 95, 70, 255), "light": (167, 243, 208, 255), "accent": (52, 211, 153, 255), "letter": "P"},
    "Ethereal": {"base": (96, 165, 250, 255), "dark": (30, 78, 175, 255), "light": (191, 219, 254, 255), "accent": (147, 197, 253, 255), "letter": "E"},
    "Void Lord": {"base": (30, 58, 95, 255), "dark": (10, 25, 45, 255), "light": (100, 140, 180, 255), "accent": (60, 100, 150, 255), "letter": "V"},
    "Hidden": {"base": (147, 51, 234, 255), "dark": (75, 20, 140, 255), "light": (216, 180, 254, 255), "accent": (192, 132, 252, 255), "letter": "H"},
}

BLOCK_FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "01010"],
}


def ensure_dirs() -> None:
    for sub in ("rarity", "creatures"):
        (ASSET_DIR / sub).mkdir(parents=True, exist_ok=True)


def img64() -> Image.Image:
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def put(draw: ImageDraw.ImageDraw, box, fill) -> None:
    draw.rectangle(tuple(int(v) for v in box), fill=fill)


def poly(draw: ImageDraw.ImageDraw, points, fill) -> None:
    draw.polygon([(int(x), int(y)) for x, y in points], fill=fill)


def mix(a, b, t: float):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)) + (255,)


def outline(img: Image.Image, passes: int = 2) -> Image.Image:
    out = img
    for _ in range(passes):
        src = out.copy()
        out = src.copy()
        spx = src.load()
        opx = out.load()
        for y in range(SIZE):
            for x in range(SIZE):
                if spx[x, y][3]:
                    continue
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < SIZE and 0 <= ny < SIZE and spx[nx, ny][3]:
                        opx[x, y] = OUTLINE
                        break
    return out


def shine(img: Image.Image, style, rng: random.Random) -> None:
    px = img.load()
    for y in range(2, SIZE - 2):
        for x in range(2, SIZE - 2):
            current = px[x, y]
            if not current[3]:
                continue
            if not px[x - 1, y - 1][3] and (x + y) % 3 == 0:
                px[x, y] = mix(current, style["light"], 0.72)
            elif px[x + 1, y + 1][3] and (x * 5 + y * 7) % 29 == 0:
                px[x, y] = mix(current, style["accent"], 0.55)
    for _ in range(7):
        sparkle(px, rng.randint(7, 56), rng.randint(6, 56), style["light"], style["accent"])


def sparkle(px, x: int, y: int, light, accent) -> None:
    for dx, dy, color in ((0, 0, WHITE), (-1, 0, light), (1, 0, light), (0, -1, light), (0, 1, accent), (-2, 0, accent), (2, 0, accent)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < SIZE and 0 <= ny < SIZE:
            px[nx, ny] = color


def draw_letter(draw: ImageDraw.ImageDraw, letter: str, x: int, y: int, scale: int, style) -> None:
    rows = BLOCK_FONT[letter]
    for ry, row in enumerate(rows):
        for rx, value in enumerate(row):
            if value != "1":
                continue
            left = x + rx * scale
            top = y + ry * scale
            put(draw, (left + 2, top + 2, left + scale + 1, top + scale + 1), style["dark"])
            put(draw, (left, top, left + scale - 1, top + scale - 1), style["base"])
            put(draw, (left, top, left + scale - 1, top + 1), style["light"])


def make_rarity_icon(rarity_name: str) -> None:
    style = RARITY_STYLE[rarity_name]
    rng = random.Random(f"rarity:{rarity_name}")
    img = img64()
    draw = ImageDraw.Draw(img)

    draw.ellipse((8, 8, 56, 56), fill=style["dark"])
    draw.ellipse((12, 12, 52, 52), fill=style["base"])
    draw.arc((6, 6, 58, 58), 200, 35, fill=style["light"], width=3)
    draw.arc((10, 10, 54, 54), 30, 210, fill=style["accent"], width=2)

    if rarity_name in {"Legendary", "Ancient", "Divine"}:
        poly(draw, [(15, 15), (20, 6), (25, 15), (32, 5), (39, 15), (44, 6), (49, 15)], style["accent"])
    if rarity_name in {"Mythic", "Abyssal"}:
        for x, y in ((16, 16), (48, 18), (18, 48), (48, 46)):
            draw.line((32, 32, x, y), fill=style["accent"], width=2)
    if rarity_name == "Eldritch":
        for box in ((5, 36, 22, 60), (42, 36, 59, 60), (24, 5, 40, 20)):
            draw.arc(box, 180, 360, fill=style["accent"], width=3)
    if rarity_name == "Prismatic":
        poly(draw, [(32, 8), (48, 20), (48, 44), (32, 56), (16, 44), (16, 20)], style["accent"])
        draw.line((32, 8, 32, 56), fill=style["light"], width=1)
        draw.line((16, 20, 48, 20), fill=style["light"], width=1)
    if rarity_name == "Ethereal":
        draw.rectangle((18, 12, 46, 52), fill=style["dark"], outline=style["accent"])
        draw.rectangle((22, 16, 42, 48), fill=style["base"])
        draw.line((26, 24, 38, 24), fill=style["light"], width=2)
        draw.line((26, 30, 38, 30), fill=style["light"], width=2)
        draw.line((26, 36, 34, 36), fill=style["light"], width=2)
    if rarity_name == "Void Lord":
        for i in range(4):
            y = 14 + i * 10
            dx = 2 if i % 2 == 0 else -2
            draw.line((16 + dx, y, 48 + dx, y), fill=style["accent"], width=3)
        draw.ellipse((24, 24, 40, 40), outline=style["light"], width=2)
    if rarity_name == "Hidden":
        draw.text((24, 16), "?", font=ImageFont.truetype("arialbd.ttf", 24), fill=style["accent"])

    draw_letter(draw, style["letter"], 17 if style["letter"] != "M" else 14, 18, 6, style)
    shine(img, style, rng)
    img = outline(img, 2)
    img.save(ASSET_DIR / "rarity" / f"{rarity_name.lower()}.png")


def creature_kind(name: str) -> str:
    n = name.lower()
    checks = [
        ("winged", ("dragon", "wyvern", "drake", "phoenix", "moth", "swan", "harrier", "roc", "bat", "gryphon", "seraph", "valkyr", "sunwyrm", "crow")),
        ("aquatic", ("eel", "kraken", "leviathan", "minnow", "angler", "siren")),
        ("serpent", ("serpent", "basilisk", "hydra", "newt", "snake")),
        ("beast", ("hound", "lynx", "jackal", "pup", "hexcat", "cat", "manticore", "stag", "hart", "kirin", "chimera", "rat", "hunt", "star beast")),
        ("insect", ("skitter", "beetle", "spider")),
        ("armored", ("knight", "paladin", "executioner", "king", "warden", "saint", "colossus", "emperor", "doctor", "judge", "warlord", "titan")),
        ("spirit", ("wisp", "wraith", "oracle", "choir", "lullaby", "familiar", "soul", "shade", "sprite", "whisper", "martyr")),
        ("god", ("godling", "hunger", "grave that breathes", "night that hunts", "eye behind", "crown", "daughter", "eater", "apostle", "chaos", "oblivion")),
        ("undead", ("skeleton", "zombie", "lich", "revenant", "bone")),
    ]
    for kind, words in checks:
        if any(word in n for word in words):
            return kind
    return "slime"


def eyes(draw: ImageDraw.ImageDraw, style, y: int = 28) -> None:
    put(draw, (24, y, 28, y + 4), style["light"])
    put(draw, (38, y, 42, y + 4), style["light"])
    put(draw, (26, y + 2, 27, y + 5), VOID)
    put(draw, (40, y + 2, 41, y + 5), VOID)


def draw_winged(draw, style) -> None:
    poly(draw, [(30, 16), (10, 8), (4, 28), (10, 50), (26, 42), (31, 30)], style["dark"])
    poly(draw, [(34, 16), (54, 8), (60, 28), (54, 50), (38, 42), (33, 30)], style["dark"])
    poly(draw, [(12, 18), (7, 30), (20, 28), (27, 36)], style["base"])
    poly(draw, [(52, 18), (57, 30), (44, 28), (37, 36)], style["base"])
    poly(draw, [(32, 12), (41, 28), (38, 50), (32, 57), (26, 50), (23, 28)], style["base"])
    poly(draw, [(27, 13), (30, 4), (32, 15)], style["light"])
    poly(draw, [(37, 13), (34, 4), (32, 15)], style["light"])
    eyes(draw, style, 28)


def draw_beast(draw, style) -> None:
    poly(draw, [(19, 18), (13, 5), (27, 15)], style["dark"])
    poly(draw, [(45, 18), (51, 5), (37, 15)], style["dark"])
    draw.rounded_rectangle((14, 16, 50, 49), radius=7, fill=style["base"])
    poly(draw, [(32, 30), (45, 38), (32, 55), (19, 38)], style["dark"])
    eyes(draw, style, 27)
    poly(draw, [(27, 43), (30, 50), (24, 47)], WHITE)
    poly(draw, [(37, 43), (34, 50), (40, 47)], WHITE)


def draw_serpent(draw, style) -> None:
    draw.arc((8, 13, 55, 58), 20, 335, fill=style["dark"], width=10)
    draw.arc((11, 16, 52, 55), 25, 330, fill=style["base"], width=6)
    draw.ellipse((27, 12, 49, 30), fill=style["base"])
    poly(draw, [(47, 18), (60, 14), (52, 27)], style["dark"])
    put(draw, (34, 19, 37, 22), style["light"])
    put(draw, (43, 19, 46, 22), style["light"])
    draw.line((52, 22, 59, 24), fill=style["accent"], width=2)


def draw_aquatic(draw, style) -> None:
    poly(draw, [(7, 33), (18, 20), (43, 19), (58, 32), (43, 45), (18, 44)], style["base"])
    poly(draw, [(7, 33), (2, 20), (2, 46)], style["dark"])
    poly(draw, [(31, 19), (39, 7), (38, 21)], style["dark"])
    poly(draw, [(31, 45), (39, 57), (38, 43)], style["dark"])
    put(draw, (45, 29, 49, 33), style["light"])
    draw.line((50, 18, 58, 8), fill=style["accent"], width=2)
    draw.ellipse((56, 5, 61, 10), fill=style["light"])


def draw_insect(draw, style) -> None:
    draw.ellipse((23, 8, 41, 25), fill=style["base"])
    draw.ellipse((18, 23, 46, 53), fill=style["dark"])
    draw.line((20, 25, 5, 12), fill=style["dark"], width=4)
    draw.line((44, 25, 59, 12), fill=style["dark"], width=4)
    draw.line((18, 36, 4, 36), fill=style["dark"], width=4)
    draw.line((46, 36, 60, 36), fill=style["dark"], width=4)
    draw.line((20, 48, 7, 59), fill=style["dark"], width=4)
    draw.line((44, 48, 57, 59), fill=style["dark"], width=4)
    draw.line((32, 9, 32, 54), fill=style["light"], width=2)
    eyes(draw, style, 19)


def draw_armored(draw, style) -> None:
    poly(draw, [(32, 5), (48, 16), (45, 42), (32, 57), (19, 42), (16, 16)], style["base"])
    put(draw, (23, 22, 45, 42), style["dark"])
    draw.line((32, 7, 32, 55), fill=style["light"], width=3)
    poly(draw, [(19, 15), (10, 6), (15, 28)], style["accent"])
    poly(draw, [(45, 15), (54, 6), (49, 28)], style["accent"])
    eyes(draw, style, 27)


def draw_spirit(draw, style) -> None:
    draw.ellipse((15, 7, 49, 43), fill=style["base"])
    poly(draw, [(16, 35), (22, 59), (32, 42), (42, 59), (48, 35)], style["dark"])
    draw.arc((6, 15, 29, 54), 90, 270, fill=style["accent"], width=4)
    draw.arc((35, 15, 58, 54), 270, 90, fill=style["accent"], width=4)
    put(draw, (24, 25, 28, 29), style["light"])
    put(draw, (36, 25, 40, 29), style["light"])
    draw.ellipse((29, 32, 35, 39), fill=VOID)


def draw_god(draw, style) -> None:
    draw.ellipse((9, 9, 55, 55), fill=style["dark"])
    draw.ellipse((17, 17, 47, 47), fill=style["base"])
    for point in ((32, 2), (10, 7), (54, 7), (4, 33), (60, 33), (15, 58), (49, 58)):
        draw.line((32, 32, point[0], point[1]), fill=style["accent"], width=4)
    draw.ellipse((24, 20, 40, 43), fill=VOID)
    put(draw, (31, 23, 34, 39), style["light"])


def draw_imp(draw, style) -> None:
    poly(draw, [(20, 20), (10, 5), (27, 16)], style["dark"])
    poly(draw, [(44, 20), (54, 5), (37, 16)], style["dark"])
    draw.ellipse((15, 15, 49, 50), fill=style["base"])
    poly(draw, [(32, 34), (44, 48), (32, 57), (20, 48)], style["dark"])
    eyes(draw, style, 28)
    put(draw, (31, 38, 34, 42), VOID)


def draw_undead(draw, style) -> None:
    draw.ellipse((14, 8, 50, 45), fill=style["base"])
    poly(draw, [(32, 8), (8, 28), (18, 56), (46, 56), (56, 28)], style["dark"])
    put(draw, (20, 14, 28, 30), VOID)
    put(draw, (36, 14, 44, 30), VOID)
    put(draw, (26, 22, 28, 26), style["light"])
    put(draw, (38, 22, 40, 26), style["light"])
    poly(draw, [(28, 38), (36, 38), (32, 48)], WHITE)


def draw_slime(draw, style) -> None:
    draw.ellipse((12, 18, 52, 56), fill=style["base"])
    draw.ellipse((18, 10, 46, 32), fill=style["dark"])
    put(draw, (24, 28, 28, 32), style["light"])
    put(draw, (36, 28, 40, 32), style["light"])
    draw.ellipse((29, 34, 35, 40), VOID)
    draw.ellipse((16, 50, 28, 58), fill=style["accent"])
    draw.ellipse((36, 52, 48, 58), fill=style["accent"])


DRAWERS = {
    "winged": draw_winged,
    "beast": draw_beast,
    "serpent": draw_serpent,
    "aquatic": draw_aquatic,
    "insect": draw_insect,
    "armored": draw_armored,
    "spirit": draw_spirit,
    "god": draw_god,
    "imp": draw_imp,
    "undead": draw_undead,
    "slime": draw_slime,
}


def silhouette_variant(draw: ImageDraw.ImageDraw, name: str, kind: str, style, rng: random.Random) -> None:
    """Add name-stable silhouette changes so species do not read as recolors."""
    variant = rng.randrange(8)
    accent = style["accent"]
    dark = style["dark"]
    light = style["light"]

    if kind == "winged":
        if variant % 2 == 0:
            poly(draw, [(4, 18), (0, 6), (16, 16)], dark)
            poly(draw, [(60, 18), (64, 6), (48, 16)], dark)
        if variant in {1, 5}:
            draw.line((32, 48, 23, 63), fill=accent, width=4)
            draw.line((32, 48, 41, 63), fill=accent, width=4)
        if variant in {2, 6}:
            poly(draw, [(28, 13), (32, 0), (36, 13)], light)
        if variant in {3, 7}:
            draw.arc((3, 4, 61, 36), 190, 340, fill=accent, width=3)
    elif kind == "beast":
        if variant in {0, 4}:
            draw.line((20, 14, 7, 3), fill=accent, width=4)
            draw.line((44, 14, 57, 3), fill=accent, width=4)
            draw.line((12, 6, 5, 12), fill=accent, width=2)
            draw.line((52, 6, 59, 12), fill=accent, width=2)
        if variant in {1, 5}:
            draw.line((48, 38, 62, 48), fill=dark, width=6)
            draw.line((57, 46, 62, 39), fill=accent, width=3)
        if variant in {2, 6}:
            poly(draw, [(18, 22), (4, 29), (18, 34)], dark)
            poly(draw, [(46, 22), (60, 29), (46, 34)], dark)
        if variant in {3, 7}:
            draw.arc((14, 2, 50, 30), 200, 340, fill=accent, width=4)
    elif kind == "serpent":
        if variant in {0, 5}:
            draw.ellipse((8, 18, 24, 34), fill=dark)
            put(draw, (13, 23, 16, 26), light)
        if variant in {1, 6}:
            for x in (18, 27, 36, 45):
                poly(draw, [(x, 16), (x + 4, 5), (x + 8, 16)], accent)
        if variant in {2, 7}:
            draw.line((18, 47, 6, 58), fill=accent, width=4)
        if variant in {3, 4}:
            draw.arc((6, 4, 58, 40), 15, 155, fill=accent, width=3)
    elif kind == "aquatic":
        if variant in {0, 4}:
            poly(draw, [(28, 18), (32, 0), (38, 19)], accent)
        if variant in {1, 5}:
            draw.line((49, 27, 63, 15), fill=accent, width=3)
            draw.ellipse((60, 12, 64, 16), fill=light)
        if variant in {2, 6}:
            poly(draw, [(20, 44), (24, 61), (33, 45)], dark)
        if variant in {3, 7}:
            draw.line((16, 22, 8, 8), fill=accent, width=3)
            draw.line((20, 21, 24, 5), fill=accent, width=3)
    elif kind == "insect":
        if variant in {0, 4}:
            draw.line((23, 8, 12, 0), fill=accent, width=3)
            draw.line((41, 8, 52, 0), fill=accent, width=3)
        if variant in {1, 5}:
            poly(draw, [(17, 25), (2, 21), (16, 34)], dark)
            poly(draw, [(47, 25), (62, 21), (48, 34)], dark)
        if variant in {2, 6}:
            for y in (28, 36, 44):
                draw.line((22, y, 46, y + 3), fill=accent, width=2)
        if variant in {3, 7}:
            draw.rectangle((25, 4, 39, 13), fill=dark)
    elif kind == "armored":
        if variant in {0, 4}:
            poly(draw, [(18, 15), (23, 2), (28, 15), (32, 3), (36, 15), (41, 2), (46, 15)], accent)
        if variant in {1, 5}:
            draw.rectangle((7, 25, 18, 50), fill=dark)
            draw.line((11, 27, 15, 46), fill=accent, width=2)
        if variant in {2, 6}:
            draw.line((49, 18, 62, 5), fill=accent, width=5)
            draw.line((55, 4, 63, 12), fill=light, width=2)
        if variant in {3, 7}:
            poly(draw, [(17, 39), (3, 58), (26, 52)], dark)
            poly(draw, [(47, 39), (61, 58), (38, 52)], dark)
    elif kind == "spirit":
        if variant in {0, 4}:
            draw.ellipse((10, 2, 54, 18), outline=accent, width=3)
        if variant in {1, 5}:
            draw.line((22, 43, 12, 63), fill=dark, width=4)
            draw.line((42, 43, 52, 63), fill=dark, width=4)
        if variant in {2, 6}:
            draw.arc((2, 18, 62, 62), 200, 340, fill=accent, width=3)
        if variant in {3, 7}:
            poly(draw, [(32, 8), (38, 21), (32, 34), (26, 21)], accent)
    elif kind == "god":
        if variant in {0, 4}:
            draw.ellipse((4, 4, 60, 60), outline=accent, width=3)
        if variant in {1, 5}:
            for x, y in ((32, 0), (63, 32), (32, 63), (0, 32)):
                draw.line((32, 32, x, y), fill=light, width=3)
        if variant in {2, 6}:
            draw.rectangle((16, 8, 48, 56), outline=accent, width=3)
        if variant in {3, 7}:
            poly(draw, [(32, 1), (45, 18), (63, 32), (45, 46), (32, 63), (18, 46), (1, 32), (18, 18)], accent)
    elif kind == "undead":
        if variant in {0, 4}:
            draw.line((14, 52, 2, 62), fill=dark, width=4)
            draw.line((50, 52, 62, 62), fill=dark, width=4)
        if variant in {1, 5}:
            poly(draw, [(16, 12), (9, 0), (25, 8)], accent)
            poly(draw, [(48, 12), (55, 0), (39, 8)], accent)
        if variant in {2, 6}:
            draw.arc((8, 2, 56, 34), 190, 350, fill=accent, width=3)
        if variant in {3, 7}:
            draw.rectangle((27, 3, 37, 14), fill=dark)
    else:
        if variant in {0, 4}:
            poly(draw, [(16, 18), (8, 4), (24, 13)], dark)
            poly(draw, [(48, 18), (56, 4), (40, 13)], dark)
        if variant in {1, 5}:
            draw.line((20, 46, 8, 60), fill=accent, width=4)
            draw.line((44, 46, 56, 60), fill=accent, width=4)
        if variant in {2, 6}:
            draw.ellipse((6, 28, 20, 45), fill=dark)
            draw.ellipse((44, 28, 58, 45), fill=dark)
        if variant in {3, 7}:
            draw.arc((6, 6, 58, 58), 210, 330, fill=accent, width=4)


def signature(draw: ImageDraw.ImageDraw, px, name: str, style) -> None:
    n = name.lower()
    if any(word in n for word in ("crown", "king", "queen", "emperor")):
        poly(draw, [(18, 14), (22, 5), (32, 14), (42, 5), (46, 14), (46, 20), (18, 20)], (255, 220, 80, 255))
    if any(word in n for word in ("halo", "divine", "saint", "celestial", "radiant")):
        draw.ellipse((12, 4, 52, 18), outline=(255, 255, 210, 255), width=3)
    if any(word in n for word in ("thorn", "briar", "root")):
        draw.line((6, 56, 20, 40, 34, 55, 56, 34), fill=(90, 255, 140, 255), width=3)
    if any(word in n for word in ("bone", "ribcage", "teeth", "skeleton")):
        for x in range(22, 44, 5):
            put(draw, (x, 39, x + 2, 49), WHITE)
    if any(word in n for word in ("moon", "dusk", "night", "dawnless")):
        draw.arc((5, 5, 58, 58), 95, 260, fill=(140, 185, 255, 255), width=3)
    if any(word in n for word in ("blood", "crimson")):
        draw.ellipse((49, 46, 56, 57), fill=(255, 40, 65, 255))
    if any(word in n for word in ("glass", "mirror", "ivory", "pale")):
        poly(draw, [(18, 8), (32, 2), (46, 8), (40, 19), (24, 19)], (185, 240, 255, 255))
    if any(word in n for word in ("lantern", "wax", "tallow")):
        draw.rectangle((27, 4, 37, 18), outline=(255, 230, 110, 255), width=2)
        put(draw, (31, 8, 34, 13), (255, 255, 160, 255))
    if any(word in n for word in ("void", "abyss", "black")):
        draw.line((9, 9, 25, 24, 20, 40, 42, 55, 56, 35), fill=(210, 70, 255, 255), width=3)
    if any(word in n for word in ("fire", "phoenix", "cinder", "ember", "ash", "infernal")):
        for x in (12, 28, 45):
            poly(draw, [(x, 56), (x + 5, 42), (x + 10, 56)], (255, 95, 35, 255))
    if "door" in n:
        draw.rectangle((23, 19, 41, 53), outline=style["accent"], width=3)
        put(draw, (36, 35, 39, 38), style["light"])
    if any(word in n for word in ("oracle", "eye")):
        draw.ellipse((20, 20, 44, 42), outline=style["accent"], width=3)
        put(draw, (31, 28, 35, 36), style["light"])
    if any(word in n for word in ("hydra", "kraken")):
        for x in (18, 32, 46):
            draw.line((32, 34, x, 12), fill=style["accent"], width=3)
            draw.ellipse((x - 3, 9, x + 3, 15), fill=style["light"])
    if any(word in n for word in ("zombie", "rot", "plague")):
        for x in (10, 25, 40, 52):
            put(draw, (x, 50, x + 3, 54), (100, 200, 80, 255))
    if any(word in n for word in ("slime", "ooze")):
        put(draw, (20, 52, 24, 58), style["accent"])
        put(draw, (40, 50, 44, 58), style["accent"])
    if any(word in n for word in ("lich", "warlord", "titan")):
        draw.ellipse((10, 10, 54, 54), outline=(255, 180, 50, 255), width=3)
    if any(word in n for word in ("chaos", "whisper", "beyond")):
        draw.ellipse((5, 5, 59, 59), outline=(200, 50, 200, 255), width=2)
        draw.line((32, 5, 32, 59), fill=(200, 50, 200, 255), width=2)
    if any(word in n for word in ("frozen", "winter")):
        poly(draw, [(8, 10), (18, 4), (28, 10), (36, 4), (46, 10), (56, 4)], (180, 220, 255, 255))
    if any(word in n for word in ("heart", "oblivion")):
        draw.ellipse((20, 22, 44, 46), fill=(255, 40, 80, 255))
        draw.ellipse((28, 28, 36, 38), fill=VOID)
    if any(word in n for word in ("spectre", "ghost", "frozen")):
        draw.ellipse((10, 8, 54, 50), outline=(200, 220, 255, 180), width=3)


def make_creature_icon(creature) -> None:
    style = RARITY_STYLE[creature.rarity]
    rng = random.Random(f"{creature.name}:{creature.rarity}")
    img = img64()
    draw = ImageDraw.Draw(img)
    kind = creature_kind(creature.name)

    DRAWERS[kind](draw, style)
    silhouette_variant(draw, creature.name, kind, style, rng)
    signature(draw, img.load(), creature.name, style)

    # Unique small emblem so same-archetype creatures still read differently.
    emblem = rng.randrange(6)
    if emblem == 0:
        draw.arc((8, 8, 56, 56), 210, 330, fill=style["accent"], width=2)
    elif emblem == 1:
        draw.line((8, 32, 56, 32), fill=style["accent"], width=2)
    elif emblem == 2:
        draw.line((32, 7, 32, 57), fill=style["accent"], width=2)
    elif emblem == 3:
        draw.rectangle((8, 8, 17, 17), outline=style["accent"], width=2)
    elif emblem == 4:
        draw.ellipse((47, 8, 57, 18), outline=style["accent"], width=2)
    else:
        poly(draw, [(32, 6), (36, 13), (32, 20), (28, 13)], style["accent"])

    shine(img, style, rng)
    img = outline(img, 2)
    img.save(ASSET_DIR / "creatures" / f"{normalize_key(creature.name)}.png")


def main() -> None:
    ensure_dirs()
    print("Generating 64x64 rarity icons...")
    for rarity in RARITIES:
        make_rarity_icon(rarity.name)
    print("Generating 64x64 creature icons...")
    for creature in CREATURES:
        make_creature_icon(creature)
    print(f"Generated {len(RARITIES)} rarity icons and {len(CREATURES)} creature icons in {ASSET_DIR}.")


if __name__ == "__main__":
    main()
