"""Generate placeholder icon assets for all game items."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "data" / "assets"

_KINDS = {
    "materials": [
        "bone_fragments", "corrupted_essence", "demon_horns", "void_crystals",
        "ancient_relics", "abyssal_ichor", "darksteel_ingot", "soul_shard",
        "shadow_essence", "cursed_fabric", "void_silk", "phantom_core",
    ],
    "currency": ["souls", "gems"],
    "consumable": ["hunt_sword"],
    "crate": ["cache", "relic", "treasure"],
    "rarity": [
        "common", "uncommon", "rare", "epic", "legendary", "mythic", "ancient",
        "divine", "eldritch", "abyssal", "prismatic", "ethereal", "void_lord", "hidden",
    ],
    "ui": ["battle", "hunt", "shop", "profile", "leaderboard", "settings"],
    "buffs": [
        "lesser_blood", "greater_blood", "abyssal_blood",
        "lesser_void", "greater_void", "eldritch_void",
    ],
}

_COLORS = {
    "bone_fragments": (200, 190, 170),
    "corrupted_essence": (100, 40, 120),
    "demon_horns": (180, 40, 40),
    "void_crystals": (60, 40, 140),
    "ancient_relics": (180, 140, 60),
    "abyssal_ichor": (30, 120, 100),
    "darksteel_ingot": (80, 80, 100),
    "soul_shard": (100, 200, 220),
    "shadow_essence": (50, 30, 70),
    "cursed_fabric": (120, 50, 60),
    "void_silk": (40, 60, 100),
    "phantom_core": (160, 100, 200),
    "souls": (235, 195, 80),
    "gems": (55, 225, 210),
    "hunt_sword": (180, 180, 200),
    "cache": (120, 100, 60),
    "relic": (60, 80, 140),
    "treasure": (180, 120, 40),
    "common": (139, 148, 158),
    "uncommon": (74, 222, 128),
    "rare": (56, 189, 248),
    "epic": (167, 139, 250),
    "legendary": (250, 204, 21),
    "mythic": (251, 113, 133),
    "ancient": (249, 115, 22),
    "divine": (254, 243, 199),
    "eldritch": (34, 211, 238),
    "abyssal": (130, 90, 200),
    "prismatic": (16, 185, 129),
    "ethereal": (96, 165, 250),
    "void_lord": (30, 80, 130),
    "hidden": (147, 51, 234),
    "battle": (220, 60, 75),
    "hunt": (80, 210, 120),
    "shop": (235, 195, 80),
    "profile": (170, 95, 245),
    "leaderboard": (235, 195, 80),
    "settings": (135, 124, 116),
    "lesser_blood": (180, 60, 70),
    "greater_blood": (220, 40, 55),
    "abyssal_blood": (140, 20, 40),
    "lesser_void": (120, 70, 200),
    "greater_void": (160, 80, 230),
    "eldritch_void": (90, 40, 180),
}

_SHAPES = {
    "bone_fragments": "cross", "corrupted_essence": "drop", "demon_horns": "triangle",
    "void_crystals": "diamond", "ancient_relics": "circle", "abyssal_ichor": "wave",
    "darksteel_ingot": "rect", "soul_shard": "star", "shadow_essence": "cloud",
    "cursed_fabric": "rect", "void_silk": "wave", "phantom_core": "circle",
    "souls": "circle", "gems": "diamond", "hunt_sword": "cross",
    "cache": "rect", "relic": "diamond", "treasure": "star",
    "lesser_blood": "drop", "greater_blood": "cross", "abyssal_blood": "star",
    "lesser_void": "circle", "greater_void": "diamond", "eldritch_void": "star",
}


def _font(size: int = 14) -> ImageFont.ImageFont:
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_shape(draw: ImageDraw, cx: int, cy: int, shape: str, color: tuple, size: int = 10) -> None:
    if shape == "circle":
        draw.ellipse([cx - size, cy - size, cx + size, cy + size], fill=color, outline=(255, 255, 255, 60))
    elif shape == "diamond":
        draw.polygon([(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)], fill=color, outline=(255, 255, 255, 60))
    elif shape == "triangle":
        draw.polygon([(cx, cy - size), (cx + size, cy + size // 2), (cx - size, cy + size // 2)], fill=color, outline=(255, 255, 255, 60))
    elif shape == "cross":
        w = size // 2
        draw.rectangle([cx - w, cy - size, cx + w, cy + size], fill=color)
        draw.rectangle([cx - size, cy - w, cx + size, cy + w], fill=color)
    elif shape == "star":
        pts = []
        for i in range(10):
            r = size if i % 2 == 0 else size // 2
            a = i * 36 - 90
            pts.append((cx + r * __import__("math").cos(__import__("math").radians(a)), cy + r * __import__("math").sin(__import__("math").radians(a))))
        draw.polygon(pts, fill=color, outline=(255, 255, 255, 60))
    elif shape == "drop":
        draw.ellipse([cx - size, cy, cx + size, cy + size], fill=color)
        draw.polygon([(cx, cy - size), (cx + size // 2, cy + size // 2), (cx - size // 2, cy + size // 2)], fill=color)
    elif shape == "wave":
        for i in range(-size, size, 4):
            y = cy + int(__import__("math").sin(i * 0.5) * size // 3)
            draw.ellipse([cx + i - 3, y - 3, cx + i + 3, y + 3], fill=color)
    elif shape == "cloud":
        for dx, dy in [(0, 0), (-6, -4), (6, -4), (-4, 4), (4, 4)]:
            draw.ellipse([cx + dx - 6, cy + dy - 5, cx + dx + 6, cy + dy + 5], fill=color)
    else:
        draw.rounded_rectangle([cx - size, cy - size, cx + size, cy + size], radius=4, fill=color, outline=(255, 255, 255, 60))


def generate() -> None:
    fnt = _font(11)
    for kind, keys in _KINDS.items():
        kind_dir = ASSETS / kind
        kind_dir.mkdir(parents=True, exist_ok=True)
        for key in keys:
            path = kind_dir / f"{key}.png"
            if path.exists():
                continue
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            color = _COLORS.get(key, (100, 100, 120))
            shape = _SHAPES.get(key, "circle")
            bg = tuple(c // 3 for c in color)
            draw.rounded_rectangle([1, 1, 30, 30], radius=5, fill=bg + (200,), outline=color + (220,), width=2)
            draw_shape(draw, 16, 16, shape, color)
            img.save(path, "PNG")
            print(f"  {kind}/{key}.png")

    # Generate creature icons (colored circles with first letter)
    creatures_dir = ASSETS / "creatures"
    creatures_dir.mkdir(parents=True, exist_ok=True)
    from core.rpg_data import CREATURES
    for ct in CREATURES:
        key = ct.name.lower().replace("'", "").replace(" ", "_")
        path = creatures_dir / f"{key}.png"
        if path.exists():
            continue
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        rc = _COLORS.get(ct.rarity.lower(), (100, 100, 120))
        bg = tuple(c // 3 for c in rc)
        draw.ellipse([1, 1, 30, 30], fill=bg + (200,), outline=rc + (220,), width=2)
        letter = ct.name[0].upper() if ct.name else "?"
        bbox = draw.textbbox((0, 0), letter, font=fnt)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((16 - tw // 2, 16 - th // 2), letter, font=fnt, fill=rc + (255,))
        img.save(path, "PNG")
        print(f"  creatures/{key}.png")

    # Generate boss icons
    bosses_dir = ASSETS / "bosses"
    bosses_dir.mkdir(parents=True, exist_ok=True)
    from core.rpg_data import BOSSES
    for boss in BOSSES:
        path = bosses_dir / f"{boss.key}.png"
        if path.exists():
            continue
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([1, 1, 30, 30], radius=8, fill=(40, 20, 50, 200), outline=(180, 50, 60, 220), width=2)
        draw_shape(draw, 16, 16, "star", (180, 50, 60))
        img.save(path, "PNG")
        print(f"  bosses/{boss.key}.png")

    # Generate zone icons
    zones_dir = ASSETS / "zones"
    zones_dir.mkdir(parents=True, exist_ok=True)
    from core.rpg_data import ZONES
    for zk in ZONES:
        path = zones_dir / f"{zk}.png"
        if path.exists():
            continue
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([1, 1, 30, 30], radius=5, fill=(30, 40, 50, 200), outline=(80, 140, 180, 220), width=2)
        draw_shape(draw, 16, 16, "circle", (80, 140, 180))
        img.save(path, "PNG")
        print(f"  zones/{zk}.png")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    generate()
    print("Done!")
