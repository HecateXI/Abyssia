"""Generate all missing icons for weapons, passives, status effects, and UI."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

ASSET_DIR = ROOT_DIR / "data" / "assets"
SIZE = 64
BG = (18, 14, 28, 255)
BORDER = (48, 40, 62, 255)


def _save(img: Image.Image, kind: str, key: str) -> None:
    out = ASSET_DIR / kind
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{key}.png"
    img.save(path, "PNG")
    print(f"  {kind}/{key}.png")


def _circle_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill, outline=None):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline)


def _diamond_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill, outline=None):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    draw.polygon(pts, fill=fill, outline=outline)


def _triangle_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill, outline=None, up=True):
    if up:
        pts = [(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    else:
        pts = [(cx, cy + r), (cx + r, cy - r), (cx - r, cy - r)]
    draw.polygon(pts, fill=fill, outline=outline)


def _base() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    return img, draw


# ── Weapon Type Icons ────────────────────────────────────────────

def _sword():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    d.line((cx, 8, cx, 48), fill=(180, 190, 210, 255), width=4)
    d.line((cx, 8, cx + 2, 14), fill=(220, 230, 240, 255), width=3)
    d.line((cx - 10, 28, cx + 10, 28), fill=(140, 100, 60, 255), width=4)
    d.ellipse((cx - 3, 46, cx + 3, 52), fill=(200, 180, 60, 255))
    _save(img, "weapons", "sword")


def _axe():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    d.line((cx, 8, cx, 50), fill=(120, 90, 50, 255), width=4)
    d.polygon([(cx - 2, 10), (cx - 18, 22), (cx - 2, 30)], fill=(160, 170, 185, 255), outline=(200, 210, 220, 255))
    d.polygon([(cx + 2, 10), (cx + 18, 22), (cx + 2, 30)], fill=(160, 170, 185, 255), outline=(200, 210, 220, 255))
    _save(img, "weapons", "axe")


def _dagger():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    d.line((cx, 12, cx, 42), fill=(190, 200, 215, 255), width=3)
    d.line((cx, 12, cx + 1, 16), fill=(230, 235, 245, 255), width=2)
    d.line((cx - 8, 30, cx + 8, 30), fill=(100, 70, 40, 255), width=3)
    d.ellipse((cx - 2, 40, cx + 2, 46), fill=(180, 160, 50, 255))
    _save(img, "weapons", "dagger")


def _staff():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    d.line((cx, 14, cx, 52), fill=(100, 70, 140, 255), width=4)
    d.ellipse((cx - 8, 6, cx + 8, 22), fill=(120, 80, 200, 255), outline=(180, 140, 255, 255))
    d.ellipse((cx - 4, 10, cx + 4, 18), fill=(200, 170, 255, 255))
    _save(img, "weapons", "staff")


def _shield():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    pts = [(cx, 8), (cx + 18, 16), (cx + 16, 38), (cx, 52), (cx - 16, 38), (cx - 18, 16)]
    d.polygon(pts, fill=(60, 80, 120, 255), outline=(100, 130, 180, 255))
    d.polygon([(cx, 14), (cx + 10, 20), (cx + 8, 36), (cx, 44), (cx - 8, 36), (cx - 10, 20)],
              fill=(40, 55, 85, 255), outline=(80, 110, 160, 255))
    _save(img, "weapons", "shield")


def _hammer():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    d.line((cx, 18, cx, 50), fill=(120, 90, 50, 255), width=5)
    d.rounded_rectangle((cx - 16, 8, cx + 16, 22), radius=4, fill=(140, 150, 165, 255), outline=(180, 190, 200, 255))
    _save(img, "weapons", "hammer")


# ── Passive Type Icons ───────────────────────────────────────────

_PASSIVE_COLORS = {
    "bleed": (194, 24, 91),
    "burn": (255, 111, 0),
    "poison": (123, 31, 162),
    "stun": (253, 216, 53),
    "shield": (2, 119, 189),
    "heal": (46, 125, 50),
    "crit": (156, 39, 176),
}


def _passive_icon(key: str, letter: str, color: tuple):
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    r = 24
    glow = tuple(min(255, c + 80) for c in color) + (60,)
    _circle_icon(d, cx, cy, r + 4, fill=glow)
    _circle_icon(d, cx, cy, r, fill=color + (200,), outline=color + (255,))
    try:
        f = ImageFont.truetype("arialbd.ttf", 28)
    except OSError:
        try:
            f = ImageFont.truetype("arial.ttf", 28)
        except OSError:
            f = ImageFont.load_default()
    bb = d.textbbox((0, 0), letter, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw // 2, cy - th // 2 - 2), letter, font=f, fill=(255, 255, 255, 255))
    _save(img, "passives", key)


# ── Status Effect Icons ──────────────────────────────────────────

def _status_bleed():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    _circle_icon(d, cx, cy, 20, fill=(194, 24, 91, 180))
    d.ellipse((cx - 6, cy - 14, cx + 2, cy + 6), fill=(220, 40, 100, 255))
    d.ellipse((cx - 4, cy + 8, cx + 4, cy + 18), fill=(180, 20, 80, 255))
    _save(img, "status", "bleed")


def _status_burn():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    pts_outer = [(cx, 6), (cx + 10, 20), (cx + 6, 18), (cx + 14, 34), (cx + 2, 26),
                 (cx + 4, 40), (cx - 4, 40), (cx - 2, 26), (cx - 14, 34), (cx - 6, 18), (cx - 10, 20)]
    d.polygon(pts_outer, fill=(255, 140, 0, 255))
    pts_inner = [(cx, 16), (cx + 6, 26), (cx + 2, 24), (cx + 8, 36), (cx - 2, 30),
                 (cx, 40), (cx - 8, 30), (cx - 2, 36), (cx - 6, 24), (cx - 6, 26)]
    d.polygon(pts_inner, fill=(255, 220, 50, 255))
    _save(img, "status", "burn")


def _status_poison():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    _circle_icon(d, cx, cy + 4, 16, fill=(123, 31, 162, 200))
    d.ellipse((cx - 6, cy - 10, cx + 6, cy + 4), fill=(160, 60, 200, 255))
    d.line((cx - 2, cy - 6, cx + 2, cy - 12), fill=(100, 20, 140, 255), width=2)
    _save(img, "status", "poison")


def _status_curse():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    _circle_icon(d, cx, cy, 20, fill=(26, 35, 126, 200))
    d.ellipse((cx - 10, cy - 6, cx + 10, cy + 6), fill=(40, 50, 160, 255))
    d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(200, 200, 255, 255))
    d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(10, 10, 40, 255))
    _save(img, "status", "curse")


def _status_fear():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    _triangle_icon(d, cx, cy, 22, fill=(66, 66, 66, 200), outline=(120, 120, 120, 255), up=False)
    d.ellipse((cx - 6, cy - 4, cx - 2, cy + 2), fill=(255, 255, 255, 200))
    d.ellipse((cx + 2, cy - 4, cx + 6, cy + 2), fill=(255, 255, 255, 200))
    _save(img, "status", "fear")


def _status_shield():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    pts = [(cx, 6), (cx + 20, 16), (cx + 18, 38), (cx, 54), (cx - 18, 38), (cx - 20, 16)]
    d.polygon(pts, fill=(2, 119, 189, 200), outline=(30, 160, 230, 255))
    _save(img, "status", "shield")


def _status_stun():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    for i in range(3):
        pts = [(cx, cy - 18 + i * 2), (cx + 6, cy + i * 2), (cx - 6, cy + i * 2)]
        d.polygon(pts, fill=(253, 216, 53, 255 - i * 40))
    _save(img, "status", "stun")


def _status_heal():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    _circle_icon(d, cx, cy, 20, fill=(46, 125, 50, 180))
    d.rectangle((cx - 3, cy - 12, cx + 3, cy + 12), fill=(120, 220, 130, 255))
    d.rectangle((cx - 12, cy - 3, cx + 12, cy + 3), fill=(120, 220, 130, 255))
    _save(img, "status", "heal")


# ── UI Icons (extra commands) ────────────────────────────────────

def _ui_sell():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    _circle_icon(d, cx, cy, 20, fill=(180, 50, 50, 200))
    d.line((cx - 10, cy, cx + 10, cy), fill=(255, 200, 200, 255), width=3)
    _save(img, "ui", "sell")


def _ui_market():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    d.rectangle((cx - 16, cy - 12, cx + 16, cy + 12), fill=(60, 50, 40, 255), outline=(140, 120, 80, 255))
    d.line((cx - 16, cy - 4, cx + 16, cy - 4), fill=(100, 80, 50, 255), width=1)
    d.line((cx - 16, cy + 4, cx + 16, cy + 4), fill=(100, 80, 50, 255), width=1)
    _save(img, "ui", "market")


def _ui_team():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    for ox, oy in [(-10, -4), (10, -4), (0, 8)]:
        _circle_icon(d, cx + ox, cy + oy, 8, fill=(100, 140, 200, 200), outline=(150, 190, 240, 255))
    _save(img, "ui", "team")


def _ui_daily():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    d.rectangle((cx - 14, cy - 16, cx + 14, cy + 16), fill=(40, 35, 55, 255), outline=(180, 160, 60, 255))
    d.rectangle((cx - 14, cy - 16, cx + 14, cy - 8), fill=(180, 160, 60, 255))
    try:
        f = ImageFont.truetype("arialbd.ttf", 16)
    except OSError:
        f = ImageFont.load_default()
    d.text((cx - 6, cy - 2), "D", font=f, fill=(255, 255, 200, 255))
    _save(img, "ui", "daily")


def _ui_forge():
    img, d = _base()
    cx, cy = SIZE // 2, SIZE // 2
    d.polygon([(cx, 6), (cx + 18, 26), (cx + 12, 26), (cx + 12, 48), (cx - 12, 48), (cx - 12, 26), (cx - 18, 26)],
              fill=(100, 80, 60, 255), outline=(160, 130, 80, 255))
    d.rectangle((cx - 6, cy - 4, cx + 6, cy + 4), fill=(255, 140, 40, 255))
    _save(img, "ui", "forge")


# ── Run All ──────────────────────────────────────────────────────

def main():
    print("Generating weapon type icons...")
    _sword(); _axe(); _dagger(); _staff(); _shield(); _hammer()

    print("Generating passive icons...")
    _PASSIVE_MAP = {"bleed": ("B", (194, 24, 91)), "burn": ("B", (255, 111, 0)),
                    "poison": ("P", (123, 31, 162)), "stun": ("S", (253, 216, 53)),
                    "shield": ("A", (2, 119, 189)), "heal": ("H", (46, 125, 50)),
                    "crit": ("C", (156, 39, 176))}
    for key, (letter, color) in _PASSIVE_MAP.items():
        _passive_icon(key, letter, color)

    print("Generating status effect icons...")
    _status_bleed(); _status_burn(); _status_poison(); _status_curse()
    _status_fear(); _status_shield(); _status_stun(); _status_heal()

    print("Generating extra UI icons...")
    _ui_sell(); _ui_market(); _ui_team(); _ui_daily(); _ui_forge()

    print("Done.")


if __name__ == "__main__":
    main()
