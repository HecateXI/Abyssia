from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import random
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from PIL import Image, ImageDraw, ImageFilter

from core.content_config import ASSET_DIR, load_config, safe_key, save_config
from core.rpg_data import ZONES


SIZE = (1920, 1080)


def _seed(key: str) -> int:
    return int(sha256(key.encode("utf-8")).hexdigest()[:16], 16)


def _rng(key: str) -> random.Random:
    return random.Random(_seed(key))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _gradient(top: tuple[int, int, int], mid: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    w, h = SIZE
    img = Image.new("RGB", SIZE)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        f = y / max(1, h - 1)
        if f < 0.55:
            c = _mix(top, mid, f / 0.55)
        else:
            c = _mix(mid, bottom, (f - 0.55) / 0.45)
        draw.line((0, y, w, y), fill=c)
    return img


def _overlay(img: Image.Image, overlay: Image.Image, alpha: float = 1.0) -> None:
    if alpha < 1.0:
        overlay = overlay.copy()
        overlay.putalpha(overlay.getchannel("A").point(lambda p: int(p * alpha)))
    img.paste(overlay, (0, 0), overlay)


def _soft_glow(img: Image.Image, xy: tuple[int, int], radius: int, color: tuple[int, int, int], strength: int) -> None:
    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = xy
    for r in range(radius, 0, -16):
        a = max(0, int(strength * (1 - r / radius) ** 1.8))
        gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color, a))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    _overlay(img, glow)


def _stars(draw: ImageDraw.ImageDraw, rng: random.Random, count: int, color: tuple[int, int, int]) -> None:
    w, h = SIZE
    for _ in range(count):
        x = rng.randrange(w)
        y = rng.randrange(max(1, h // 2))
        s = rng.choice((1, 1, 1, 2, 2, 3))
        b = rng.randrange(90, 210)
        fill = _mix(color, (255, 255, 255), b / 255)
        draw.rectangle((x, y, x + s, y + s), fill=fill)


def _noise(img: Image.Image, opacity: float = 0.07) -> None:
    noise = Image.effect_noise(SIZE, 18).convert("L")
    noise = noise.point(lambda p: max(0, min(255, int((p - 128) * 0.55 + 128))))
    rgba = Image.merge("RGBA", (noise, noise, noise, Image.new("L", SIZE, int(255 * opacity))))
    _overlay(img, rgba)


def _vignette(img: Image.Image, strength: int = 210) -> None:
    w, h = SIZE
    v = Image.new("L", SIZE, 0)
    draw = ImageDraw.Draw(v)
    for i in range(110):
        t = i / 109
        inset_x = int(w * 0.48 * (1 - t))
        inset_y = int(h * 0.46 * (1 - t))
        alpha = int(strength * t * t)
        draw.rectangle((inset_x, inset_y, w - inset_x, h - inset_y), outline=alpha, width=10)
    v = v.filter(ImageFilter.GaussianBlur(34))
    _overlay(img, Image.merge("RGBA", (Image.new("L", SIZE, 0), Image.new("L", SIZE, 0), Image.new("L", SIZE, 0), v)))


def _fog(img: Image.Image, rng: random.Random, color: tuple[int, int, int], bands: int = 9, alpha: int = 50) -> None:
    w, h = SIZE
    fog = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fog)
    for i in range(bands):
        y = int(h * (0.35 + i * 0.075)) + rng.randrange(-40, 40)
        amp = rng.randrange(20, 70)
        pts = []
        for x in range(-80, w + 120, 80):
            yy = y + int(rng.uniform(-amp, amp))
            pts.append((x, yy))
        lower = [(x, y + rng.randrange(50, 145)) for x, y in reversed(pts)]
        fd.polygon(pts + lower, fill=(*color, alpha))
    fog = fog.filter(ImageFilter.GaussianBlur(30))
    _overlay(img, fog)


def _ground(draw: ImageDraw.ImageDraw, color: tuple[int, int, int], y: int, rough: int, rng: random.Random) -> None:
    w, h = SIZE
    pts = [(0, h), (0, y)]
    for x in range(0, w + 80, 80):
        pts.append((x, y + rng.randrange(-rough, rough + 1)))
    pts.extend([(w, h), (0, h)])
    draw.polygon(pts, fill=color)


def _trees(img: Image.Image, rng: random.Random, count: int, color: tuple[int, int, int], y_base: int, tall: bool = False) -> None:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    w, h = SIZE
    for _ in range(count):
        x = rng.randrange(-80, w + 80)
        trunk_w = rng.randrange(14, 42 if tall else 28)
        height = rng.randrange(230, 650 if tall else 430)
        top = y_base - height
        lean = rng.randrange(-46, 46)
        col = (*_mix(color, (0, 0, 0), rng.random() * 0.28), rng.randrange(175, 235))
        draw.polygon([(x, y_base + 40), (x + trunk_w, y_base + 40), (x + trunk_w + lean, top), (x + lean, top)], fill=col)
        for _b in range(rng.randrange(3, 7)):
            by = rng.randrange(max(0, top + 40), y_base - 30)
            length = rng.randrange(70, 180)
            side = -1 if rng.random() < 0.5 else 1
            draw.line((x + trunk_w // 2, by, x + trunk_w // 2 + length * side, by - rng.randrange(30, 130)), fill=col, width=rng.randrange(5, 12))
    layer = layer.filter(ImageFilter.GaussianBlur(1.2))
    _overlay(img, layer)


def _vertical_arches(img: Image.Image, rng: random.Random, color: tuple[int, int, int], count: int) -> None:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    w, h = SIZE
    spacing = w // max(1, count)
    for i in range(-1, count + 1):
        x = i * spacing + rng.randrange(-35, 36)
        arch_w = rng.randrange(150, 230)
        top = rng.randrange(170, 260)
        bottom = h + 80
        col = (*color, rng.randrange(145, 210))
        draw.rectangle((x - arch_w // 2, top + arch_w // 2, x - arch_w // 2 + 42, bottom), fill=col)
        draw.rectangle((x + arch_w // 2 - 42, top + arch_w // 2, x + arch_w // 2, bottom), fill=col)
        draw.arc((x - arch_w // 2, top, x + arch_w // 2, top + arch_w), 180, 360, fill=col, width=42)
    layer = layer.filter(ImageFilter.GaussianBlur(1.5))
    _overlay(img, layer)


def _floating_rocks(img: Image.Image, rng: random.Random, color: tuple[int, int, int], count: int) -> None:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(count):
        cx = rng.randrange(80, SIZE[0] - 80)
        cy = rng.randrange(120, 660)
        r = rng.randrange(22, 90)
        pts = []
        for i in range(rng.randrange(5, 8)):
            angle = i * 6.283 / 7 + rng.random() * 0.5
            rr = r * rng.uniform(0.55, 1.15)
            pts.append((int(cx + rr * __import__("math").cos(angle)), int(cy + rr * __import__("math").sin(angle))))
        draw.polygon(pts, fill=(*color, rng.randrange(115, 185)))
    layer = layer.filter(ImageFilter.GaussianBlur(1.0))
    _overlay(img, layer)


def _forgotten_woods(rng: random.Random) -> Image.Image:
    img = _gradient((32, 48, 38), (12, 25, 19), (5, 10, 8))
    _soft_glow(img, (1480, 230), 360, (135, 195, 155), 52)
    _trees(img, rng, 34, (7, 18, 13), 980, tall=True)
    draw = ImageDraw.Draw(img)
    _ground(draw, (8, 16, 10), 835, 42, rng)
    for _ in range(110):
        x, y = rng.randrange(60, 1860), rng.randrange(260, 870)
        c = rng.choice(((110, 190, 110), (170, 220, 145), (90, 150, 125)))
        draw.rectangle((x, y, x + 2, y + 2), fill=c)
    _fog(img, rng, (116, 144, 118), 8, 32)
    return img


def _grave_marsh(rng: random.Random) -> Image.Image:
    img = _gradient((38, 42, 30), (15, 20, 15), (5, 8, 7))
    draw = ImageDraw.Draw(img)
    _ground(draw, (13, 17, 12), 780, 58, rng)
    draw.rectangle((0, 825, SIZE[0], SIZE[1]), fill=(7, 13, 12))
    for x in range(-80, SIZE[0] + 120, 95):
        top = rng.randrange(620, 790)
        draw.line((x, 930, x + rng.randrange(-60, 60), top), fill=(25, 32, 22), width=rng.randrange(5, 10))
    for _ in range(18):
        x = rng.randrange(0, SIZE[0])
        y = rng.randrange(820, 980)
        draw.ellipse((x, y, x + rng.randrange(80, 230), y + rng.randrange(8, 22)), fill=(17, 28, 25))
    _trees(img, rng, 16, (7, 12, 9), 900)
    _fog(img, rng, (110, 126, 104), 11, 42)
    return img


def _bloodmoon_forest(rng: random.Random) -> Image.Image:
    img = _gradient((70, 18, 24), (28, 7, 10), (8, 3, 4))
    _soft_glow(img, (1380, 230), 430, (180, 28, 38), 95)
    draw = ImageDraw.Draw(img)
    draw.ellipse((1270, 120, 1510, 360), fill=(150, 35, 42), outline=(60, 10, 14), width=5)
    _trees(img, rng, 36, (10, 5, 7), 1005, tall=True)
    _ground(draw, (14, 5, 7), 835, 36, rng)
    _fog(img, rng, (105, 28, 34), 7, 46)
    return img


def _ashen_wastes(rng: random.Random) -> Image.Image:
    img = _gradient((80, 72, 55), (34, 30, 24), (13, 11, 10))
    draw = ImageDraw.Draw(img)
    for x in range(-160, SIZE[0] + 200, 220):
        top = rng.randrange(360, 520)
        draw.polygon([(x, 800), (x + 160, top), (x + 330, 820)], fill=(28, 25, 22))
        draw.line((x + 160, top, x + 205, 830), fill=(116, 58, 32), width=8)
    _ground(draw, (31, 28, 24), 790, 75, rng)
    for _ in range(90):
        x, y = rng.randrange(SIZE[0]), rng.randrange(130, 900)
        draw.rectangle((x, y, x + 2, y + 2), fill=(190, 104, 54))
    _fog(img, rng, (126, 106, 82), 9, 50)
    return img


def _infernal_catacombs(rng: random.Random) -> Image.Image:
    img = _gradient((70, 26, 14), (28, 9, 5), (8, 3, 2))
    _vertical_arches(img, rng, (25, 12, 9), 9)
    draw = ImageDraw.Draw(img)
    for x in range(0, SIZE[0], 220):
        draw.rectangle((x + 70, 630, x + 145, SIZE[1]), fill=(34, 14, 9))
    draw.rectangle((0, 870, SIZE[0], SIZE[1]), fill=(18, 6, 3))
    for x in range(-80, SIZE[0] + 100, 160):
        draw.polygon([(x, 930), (x + 90, 850), (x + 250, 930), (x + 170, 990)], fill=(165, 52, 18))
    _soft_glow(img, (930, 820), 760, (220, 64, 20), 82)
    _fog(img, rng, (125, 42, 22), 6, 34)
    return img


def _abyssal_depths(rng: random.Random) -> Image.Image:
    img = _gradient((9, 42, 60), (4, 17, 33), (1, 4, 13))
    draw = ImageDraw.Draw(img)
    for _ in range(70):
        x, y = rng.randrange(SIZE[0]), rng.randrange(80, 860)
        r = rng.randrange(2, 8)
        draw.ellipse((x, y, x + r, y + r), outline=(85, 170, 190))
    for x in range(-80, SIZE[0] + 80, 150):
        draw.polygon([(x, SIZE[1]), (x + rng.randrange(20, 80), rng.randrange(700, 940)), (x + 120, SIZE[1])], fill=(4, 12, 19))
    _soft_glow(img, (960, 520), 520, (45, 170, 190), 52)
    for _ in range(44):
        x, y = rng.randrange(60, 1860), rng.randrange(760, 1030)
        c = rng.choice(((40, 190, 165), (55, 120, 210), (130, 70, 210)))
        draw.line((x, y, x + rng.randrange(-20, 20), y - rng.randrange(30, 110)), fill=c, width=rng.randrange(2, 5))
    _fog(img, rng, (37, 96, 120), 10, 36)
    return img


def _void_realm(rng: random.Random) -> Image.Image:
    img = _gradient((22, 12, 55), (8, 4, 26), (2, 1, 9))
    draw = ImageDraw.Draw(img)
    _stars(draw, rng, 260, (140, 160, 255))
    for _ in range(7):
        x1, y1 = rng.randrange(150, 1750), rng.randrange(120, 520)
        x2 = x1 + rng.randrange(-220, 220)
        y2 = y1 + rng.randrange(180, 380)
        draw.line((x1, y1, x2, y2), fill=(75, 225, 205), width=rng.randrange(2, 5))
        _soft_glow(img, (x1, y1), rng.randrange(70, 140), (82, 190, 230), 28)
    _floating_rocks(img, rng, (15, 12, 32), 22)
    _fog(img, rng, (72, 52, 118), 8, 32)
    return img


def _cursed_sanctum(rng: random.Random) -> Image.Image:
    img = _gradient((54, 25, 62), (24, 11, 30), (8, 4, 12))
    _vertical_arches(img, rng, (18, 10, 24), 7)
    draw = ImageDraw.Draw(img)
    for x in range(220, SIZE[0], 300):
        draw.polygon([(x, 230), (x + 70, 500), (x - 70, 500)], fill=(95, 45, 120))
        draw.rectangle((x - 55, 500, x + 55, 780), fill=(20, 8, 28))
    for x in range(120, SIZE[0], 135):
        draw.rectangle((x, 850, x + 8, 965), fill=(90, 65, 55))
        draw.ellipse((x - 8, 825, x + 16, 850), fill=(230, 170, 72))
    _soft_glow(img, (960, 420), 650, (120, 50, 155), 52)
    _fog(img, rng, (106, 72, 118), 8, 34)
    return img


def _starless_menagerie(rng: random.Random) -> Image.Image:
    img = _gradient((18, 20, 48), (7, 8, 24), (2, 2, 8))
    draw = ImageDraw.Draw(img)
    _stars(draw, rng, 120, (90, 100, 170))
    for x in range(80, SIZE[0], 185):
        y = rng.randrange(260, 520)
        w = rng.randrange(80, 130)
        h = rng.randrange(210, 380)
        draw.rectangle((x, y, x + w, y + h), outline=(45, 48, 70), width=8)
        for bx in range(x + 18, x + w, 22):
            draw.line((bx, y + 8, bx, y + h - 8), fill=(35, 38, 56), width=3)
        draw.line((x + w // 2, 0, x + w // 2, y), fill=(38, 40, 60), width=3)
    _floating_rocks(img, rng, (10, 12, 28), 14)
    _fog(img, rng, (65, 70, 105), 9, 30)
    return img


def _throne_of_teeth(rng: random.Random) -> Image.Image:
    img = _gradient((58, 34, 38), (25, 13, 18), (7, 4, 6))
    draw = ImageDraw.Draw(img)
    for x in range(-60, SIZE[0] + 120, 95):
        h = rng.randrange(160, 420)
        draw.polygon([(x, 860), (x + 35, 860 - h), (x + 75, 860)], fill=(176, 158, 130))
    throne = [(760, 880), (810, 410), (900, 620), (960, 290), (1020, 620), (1110, 410), (1160, 880)]
    draw.polygon(throne, fill=(58, 44, 40), outline=(180, 160, 120))
    draw.rectangle((760, 760, 1160, 980), fill=(42, 30, 30), outline=(150, 120, 92), width=5)
    for x in range(780, 1140, 55):
        draw.polygon([(x, 760), (x + 20, 650), (x + 42, 760)], fill=(204, 184, 142), outline=(40, 28, 25))
    _soft_glow(img, (960, 600), 560, (165, 65, 55), 56)
    _fog(img, rng, (100, 70, 66), 7, 34)
    return img


def _black_sun_gate(rng: random.Random) -> Image.Image:
    img = _gradient((12, 8, 35), (4, 3, 18), (0, 0, 5))
    draw = ImageDraw.Draw(img)
    _stars(draw, rng, 360, (120, 130, 210))
    _soft_glow(img, (960, 290), 520, (95, 66, 150), 70)
    draw.ellipse((820, 150, 1100, 430), fill=(1, 1, 3), outline=(80, 62, 120), width=5)
    for x in (550, 1220):
        draw.polygon([(x, 900), (x + 80, 220), (x + 180, 900)], fill=(8, 8, 18), outline=(52, 42, 82))
    draw.rectangle((630, 760, 1290, 960), fill=(5, 5, 13), outline=(55, 45, 86), width=6)
    draw.arc((630, 360, 1290, 1160), 180, 360, fill=(55, 45, 86), width=12)
    _floating_rocks(img, rng, (8, 7, 20), 18)
    _fog(img, rng, (56, 48, 95), 8, 34)
    return img


GENERATORS = {
    "forgotten_woods": _forgotten_woods,
    "grave_marsh": _grave_marsh,
    "bloodmoon_forest": _bloodmoon_forest,
    "ashen_wastes": _ashen_wastes,
    "infernal_catacombs": _infernal_catacombs,
    "abyssal_depths": _abyssal_depths,
    "void_realm": _void_realm,
    "cursed_sanctum": _cursed_sanctum,
    "starless_menagerie": _starless_menagerie,
    "throne_of_teeth": _throne_of_teeth,
    "black_sun_gate": _black_sun_gate,
}


def _finish(zone_key: str, img: Image.Image) -> Image.Image:
    _noise(img, 0.055)
    _vignette(img, 230)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=115, threshold=4))
    return img


def main() -> None:
    config = load_config()
    zone_assets = config.setdefault("assets", {}).setdefault("zones", {})

    for zone_key in ZONES:
        generator = GENERATORS.get(zone_key)
        if generator is None:
            generator = _forgotten_woods
        img = _finish(zone_key, generator(_rng(zone_key)))
        safe = safe_key(zone_key)
        path = ASSET_DIR / "zones" / f"{safe}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, "PNG", optimize=True)
        zone_assets[safe] = {"file": f"zones/{safe}.png", "generated": True, "usage": "card_background"}
        print(f"zones/{safe}.png {img.size[0]}x{img.size[1]}")

    save_config(config)


if __name__ == "__main__":
    main()
