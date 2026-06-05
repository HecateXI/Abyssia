from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from PIL import Image, ImageDraw, ImageFilter
from core.content_config import ASSET_DIR, get_asset_file_path, load_config, save_config, safe_key
from core.rpg_data import ZONES


SIZE = 1920, 1080

ZONE_STYLES: dict[str, dict] = {
    "forgotten_woods": {
        "colors": [(30, 50, 30), (10, 25, 12), (20, 40, 20)],
        "trees": 40, "fog": 0.3,
    },
    "grave_marsh": {
        "colors": [(35, 40, 25), (15, 18, 10), (25, 30, 18)],
        "fog": 0.4, "murk": 0.2,
    },
    "bloodmoon_forest": {
        "colors": [(55, 15, 18), (30, 8, 10), (45, 12, 14)],
        "trees": 30, "fog": 0.2, "glow": (120, 20, 25),
    },
    "ashen_wastes": {
        "colors": [(55, 50, 38), (30, 28, 20), (45, 40, 30)],
        "fog": 0.5,
    },
    "infernal_catacombs": {
        "colors": [(60, 22, 14), (35, 12, 6), (50, 18, 10)],
        "glow": (180, 50, 20),
    },
    "void_realm": {
        "colors": [(15, 10, 35), (5, 3, 18), (10, 6, 28)],
        "stars": 200, "fog": 0.6,
    },
    "abyssal_depths": {
        "colors": [(10, 8, 32), (3, 2, 14), (6, 4, 24)],
        "stars": 100, "fog": 0.7,
    },
    "cursed_sanctum": {
        "colors": [(40, 20, 42), (20, 10, 22), (30, 15, 32)],
        "fog": 0.4, "glow": (100, 30, 120),
    },
    "starless_menagerie": {
        "colors": [(14, 14, 38), (6, 5, 20), (10, 10, 30)],
        "stars": 150, "fog": 0.5,
    },
    "throne_of_teeth": {
        "colors": [(42, 26, 32), (22, 12, 16), (34, 18, 24)],
        "fog": 0.3,
    },
    "black_sun_gate": {
        "colors": [(8, 6, 26), (2, 1, 12), (5, 3, 20)],
        "stars": 250, "fog": 0.8,
    },
}


def _lerp_color(a, b, t):
    t = max(0, min(1, t))
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _generate_background(zone_key: str, style: dict) -> Image.Image:
    W, H = SIZE
    colors = style["colors"]
    img = Image.new("RGB", (W, H))

    for y in range(H):
        frac = y / H
        if frac < 0.5:
            t = frac * 2
            c = _lerp_color(colors[0], colors[1], t)
        else:
            t = (frac - 0.5) * 2
            c = _lerp_color(colors[1], colors[2], t)
        draw = ImageDraw.Draw(img)
        draw.line((0, y, W, y), fill=c)

    draw = ImageDraw.Draw(img)

    if "trees" in style:
        rng = __import__("random").Random(hash(zone_key))
        for _ in range(style["trees"]):
            x = rng.randint(0, W)
            h = rng.randint(80, 250)
            w = rng.randint(20, 50)
            color = (
                rng.randint(15, 40),
                rng.randint(20, 45),
                rng.randint(10, 30),
            )
            draw.rectangle((x, H - h, x + w, H), fill=color)
            crown_r = rng.randint(30, 70)
            crown_color = (
                rng.randint(10, 35),
                rng.randint(15, 40),
                rng.randint(8, 25),
            )
            draw.ellipse(
                (x - crown_r, H - h - crown_r, x + w + crown_r, H - h + crown_r),
                fill=crown_color,
            )

    if "stars" in style:
        rng = __import__("random").Random(hash(zone_key) + 42)
        for _ in range(style["stars"]):
            x = rng.randint(0, W)
            y = rng.randint(0, H // 2)
            b = rng.randint(120, 220)
            s = rng.randint(1, 3)
            draw.ellipse((x, y, x + s, y + s), fill=(b, b, b + 10))

    if "fog" in style:
        fog = Image.new("RGB", (W, H), colors[1])
        fog = fog.filter(ImageFilter.GaussianBlur(radius=120))
        img = Image.blend(img, fog, style["fog"])

    if "glow" in style:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gc = style["glow"]
        cx, cy = W // 2, H // 3
        for r in range(300, 0, -10):
            a = max(1, 60 - r // 6)
            gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*gc, a))
        img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"))

    if "murk" in style:
        murk = Image.new("RGB", (W, H), (0, 0, 0))
        murk = murk.filter(ImageFilter.GaussianBlur(radius=60))
        img = Image.blend(img, murk, style["murk"])

    return img


def main():
    config = load_config()
    for zone_key in ZONES:
        style = ZONE_STYLES.get(zone_key)
        if not style:
            continue
        img = _generate_background(zone_key, style)
        safe = safe_key(zone_key)
        path = ASSET_DIR / "zones" / f"{safe}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, "PNG")
        config["assets"].setdefault("zones", {})[safe] = {
            "file": f"zones/{safe}.png",
            "generated": True,
        }
        print(f"Generated {path.name}")
    save_config(config)
    print("Zone backgrounds generated!")


if __name__ == "__main__":
    main()
