"""Normalize Abyssia card UI assets and create manifest-tracked placeholders."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.generate_card_asset_prompts import REQUIRED_FOLDERS, all_records  # noqa: E402

PROMPTS_PATH = ROOT_DIR / "data" / "card_asset_prompts.json"
MANIFEST_PATH = ROOT_DIR / "data" / "card_asset_manifest.json"
THUMB_DIR = ROOT_DIR / "tmp" / "card_previews" / "card_asset_thumbnails"
CONTACT_SHEET = ROOT_DIR / "tmp" / "card_previews" / "card_asset_contact_sheet.png"

Color = tuple[int, int, int]
ColorA = tuple[int, int, int, int]

RARITY_COLORS: dict[str, Color] = {
    "common": (139, 148, 158),
    "uncommon": (74, 222, 128),
    "rare": (56, 189, 248),
    "epic": (167, 139, 250),
    "legendary": (250, 204, 21),
    "mythic": (251, 113, 133),
    "ancient": (249, 115, 22),
    "patreon": (255, 66, 77),
    "divine": (254, 243, 199),
    "eldritch": (34, 211, 238),
    "abyssal": (130, 90, 200),
    "prismatic": (16, 185, 129),
    "ethereal": (96, 165, 250),
    "void_lord": (30, 80, 130),
    "hidden": (147, 51, 234),
}

KEY_COLORS: dict[str, Color] = {
    "hp": (221, 61, 78),
    "mana": (125, 92, 255),
    "xp": (80, 212, 126),
    "quality": (238, 196, 82),
    "souls": (238, 196, 82),
    "gold": (238, 196, 82),
    "cyan": (58, 218, 232),
    "green": (80, 212, 126),
    "purple": (158, 91, 236),
    "blood": (221, 61, 78),
    "defeat": (221, 61, 78),
    "victory": (238, 196, 82),
    "tie": (139, 148, 158),
    "locked": (130, 124, 145),
    "owned": (80, 212, 126),
}


def rgba(color: Color | ColorA, alpha: int) -> ColorA:
    return (int(color[0]), int(color[1]), int(color[2]), max(0, min(255, int(alpha))))


def lerp(a: Color, b: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))  # type: ignore[return-value]


def accent_for(record: dict[str, Any]) -> Color:
    key = str(record["key"])
    lower = key.lower()
    for rarity, color in RARITY_COLORS.items():
        if lower == rarity or lower.endswith(f"_{rarity}") or f"_{rarity}_" in lower:
            return color
    for token, color in KEY_COLORS.items():
        if token in lower:
            return color
    if "void" in lower or "abyss" in lower:
        return (92, 82, 190)
    if "battle" in lower or "infernal" in lower:
        return (221, 61, 78)
    if "vault" in lower or "weapon" in lower:
        return (238, 196, 82)
    if "hunt" in lower or "forest" in lower:
        return (80, 172, 104)
    return (58, 218, 232)


def cut_points(box: tuple[int, int, int, int], cut: int) -> list[tuple[int, int]]:
    x1, y1, x2, y2 = box
    cut = max(0, min(cut, (x2 - x1) // 3, (y2 - y1) // 3))
    return [
        (x1 + cut, y1),
        (x2 - cut, y1),
        (x2, y1 + cut),
        (x2, y2 - cut),
        (x2 - cut, y2),
        (x1 + cut, y2),
        (x1, y2 - cut),
        (x1, y1 + cut),
    ]


def draw_cut_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: ColorA,
    outline: ColorA | None,
    *,
    cut: int,
    width: int = 2,
) -> None:
    points = cut_points(box, cut)
    draw.polygon(points, fill=fill)
    if outline is None:
        return
    for offset in range(max(1, width)):
        inner = (box[0] + offset, box[1] + offset, box[2] - offset, box[3] - offset)
        pts = cut_points(inner, max(0, cut - offset))
        draw.line(pts + [pts[0]], fill=outline, width=1)


def font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = ("segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    source = image.convert("RGBA")
    target_w, target_h = size
    scale = max(target_w / source.width, target_h / source.height)
    resized = source.resize((max(1, math.ceil(source.width * scale)), max(1, math.ceil(source.height * scale))), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - target_w) // 2)
    top = max(0, (resized.height - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


def contain_resize(image: Image.Image, size: tuple[int, int], *, padding: float = 0.08) -> Image.Image:
    source = image.convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox:
        source = source.crop(bbox)
    fit = (max(1, int(size[0] * (1 - padding))), max(1, int(size[1] * (1 - padding))))
    source.thumbnail(fit, Image.Resampling.LANCZOS)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.alpha_composite(source, ((size[0] - source.width) // 2, (size[1] - source.height) // 2))
    return out


def tint_asset(image: Image.Image, accent: Color, *, strength: float = 0.34) -> Image.Image:
    rgba_image = image.convert("RGBA")
    gray = ImageOps.grayscale(rgba_image)
    tint = Image.merge(
        "RGBA",
        (
            gray.point(lambda p: int((p * (1 - strength)) + accent[0] * strength)),
            gray.point(lambda p: int((p * (1 - strength)) + accent[1] * strength)),
            gray.point(lambda p: int((p * (1 - strength)) + accent[2] * strength)),
            rgba_image.getchannel("A"),
        ),
    )
    return Image.alpha_composite(rgba_image, tint.putalpha(rgba_image.getchannel("A")) or tint)


def generate_background(record: dict[str, Any]) -> Image.Image:
    width, height = record["size"]
    key = str(record["key"])
    accent = accent_for(record)
    rng = random.Random(key)
    top = lerp((12, 8, 22), accent, 0.12)
    bottom = lerp((2, 2, 8), accent, 0.06)
    img = Image.new("RGBA", (width, height), bottom)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line((0, y, width, y), fill=(*lerp(top, bottom, t), 255))

    # Background architecture silhouettes.
    for idx in range(9):
        x = int(width * idx / 8) + rng.randint(-36, 36)
        h = rng.randint(height // 5, height // 2)
        w = rng.randint(42, 118)
        y = height - h + rng.randint(-18, 28)
        draw.rectangle((x, y, x + w, height), fill=rgba(lerp(bottom, (0, 0, 0), 0.35), 70))
        if rng.random() < 0.55:
            draw.polygon(((x - 18, y), (x + w // 2, y - rng.randint(32, 86)), (x + w + 18, y)), fill=rgba((0, 0, 0), 48))

    for _ in range(34):
        x = rng.randint(0, width)
        y = rng.randint(height // 5, height - 80)
        length = rng.randint(44, 180)
        draw.line((x, y, x + length, y + rng.randint(-10, 10)), fill=rgba(accent, rng.randint(10, 34)), width=rng.choice((1, 1, 2)))

    fog = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fog)
    for _ in range(18):
        x = rng.randint(-width // 4, width)
        y = rng.randint(height // 3, height)
        rx = rng.randint(width // 6, width // 2)
        ry = rng.randint(30, 120)
        fd.ellipse((x, y, x + rx, y + ry), fill=rgba(lerp(accent, (230, 240, 255), 0.2), rng.randint(8, 22)))
    fog = fog.filter(ImageFilter.GaussianBlur(24))
    img.alpha_composite(fog)

    for _ in range(max(40, width * height // 18000)):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        r = rng.choice((1, 1, 2))
        draw.rectangle((x, y, x + r, y + r), fill=rgba(lerp(accent, (255, 255, 255), 0.42), rng.randint(20, 80)))

    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(28):
        t = i / 27
        pad_x = int(width * 0.02 * i)
        pad_y = int(height * 0.025 * i)
        if width - pad_x <= pad_x or height - pad_y <= pad_y:
            continue
        vd.rectangle((pad_x, pad_y, width - pad_x, height - pad_y), outline=(0, 0, 0, int(5 + 12 * t)), width=18)
    img.alpha_composite(vignette)
    return img.convert("RGB")


def generate_panel(record: dict[str, Any]) -> Image.Image:
    width, height = record["size"]
    accent = accent_for(record)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cut = max(8, min(width, height) // 12)
    gd.polygon(cut_points((10, 10, width - 10, height - 10), cut), fill=rgba(accent, 58))
    glow = glow.filter(ImageFilter.GaussianBlur(max(8, min(width, height) // 18)))
    img.alpha_composite(glow)
    draw = ImageDraw.Draw(img)
    draw_cut_box(draw, (14, 14, width - 15, height - 15), rgba((8, 7, 15), 220), rgba(accent, 180), cut=cut, width=3)
    draw_cut_box(draw, (24, 24, width - 25, height - 25), rgba((18, 14, 28), 92), rgba(lerp(accent, (255, 255, 255), 0.22), 80), cut=max(4, cut - 8), width=1)
    for y in range(34, height - 32, 18):
        draw.line((34, y, width - 34, y), fill=rgba(accent, 12), width=1)
    draw.line((30, 24, width - 30, 24), fill=rgba((255, 255, 255), 42), width=2)
    draw.line((30, height - 26, width - 30, height - 26), fill=rgba((0, 0, 0), 92), width=2)
    return img


def generate_effect(record: dict[str, Any]) -> Image.Image:
    width, height = record["size"]
    key = str(record["key"])
    accent = accent_for(record)
    rng = random.Random(key)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if "fog" in key:
        for _ in range(16):
            x = rng.randint(-width // 3, width)
            y = rng.randint(0, height)
            draw.ellipse((x, y, x + rng.randint(width // 4, width), y + rng.randint(40, 160)), fill=rgba((200, 220, 235), rng.randint(12, 35)))
        return img.filter(ImageFilter.GaussianBlur(22))
    if "scanline" in key:
        for y in range(0, height, 4):
            draw.rectangle((0, y, width, y + 1), fill=(255, 255, 255, 18))
        return img
    if "vignette" in key:
        for i in range(34):
            pad_x = int(width * i / 68)
            pad_y = int(height * i / 68)
            draw.rectangle((pad_x, pad_y, width - pad_x, height - pad_y), outline=(0, 0, 0, 12), width=16)
        return img
    if "spotlight" in key or "glow" in key:
        draw.ellipse((width // 8, height // 8, width * 7 // 8, height * 7 // 8), fill=rgba(accent, 120))
        return img.filter(ImageFilter.GaussianBlur(max(18, min(width, height) // 9)))
    for _ in range(max(45, width * height // 9000)):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        r = rng.choice((1, 1, 2, 3))
        draw.rectangle((x, y, x + r, y + r), fill=rgba(lerp(accent, (255, 255, 255), 0.35), rng.randint(40, 150)))
    return img


def generate_placeholder(record: dict[str, Any]) -> Image.Image:
    category = str(record["category"])
    transparent = bool(record["transparent"])
    if not transparent:
        return generate_background(record)
    if category in {"effects", "overlays"} or "glow" in str(record["key"]):
        return generate_effect(record)
    if category in {"bars", "dividers"} and "frame" not in str(record["key"]):
        width, height = record["size"]
        accent = accent_for(record)
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cut = max(2, height // 4)
        draw_cut_box(draw, (4, 4, width - 5, height - 5), rgba(accent, 210), rgba(lerp(accent, (255, 255, 255), 0.32), 160), cut=cut, width=1)
        for x in range(12, width - 12, 18):
            draw.rectangle((x, 8, x + 8, max(9, height // 2)), fill=rgba((255, 255, 255), 42))
        return img
    return generate_panel(record)


def load_records() -> list[dict[str, Any]]:
    if PROMPTS_PATH.exists():
        payload = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
        records = payload.get("records", [])
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    return all_records()


def previous_placeholder_state(record: dict[str, Any]) -> bool:
    if not MANIFEST_PATH.exists():
        return False
    try:
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    categories = payload.get("categories", {}) if isinstance(payload, dict) else {}
    category = categories.get(str(record.get("category", "")), {}) if isinstance(categories, dict) else {}
    entry = category.get(str(record.get("key", "")), {}) if isinstance(category, dict) else {}
    return bool(entry.get("placeholder", False)) if isinstance(entry, dict) else False


def normalize_record(record: dict[str, Any], *, force: bool, create_placeholders: bool) -> dict[str, Any]:
    out_path = ROOT_DIR / str(record["output_path"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    size = tuple(int(v) for v in record["size"])
    transparent = bool(record.get("transparent", False))
    accent = accent_for(record)
    placeholder = False
    source_label = ""

    if out_path.exists() and not force:
        image = Image.open(out_path).convert("RGBA")
        placeholder = previous_placeholder_state(record)
        source_label = "existing"
    else:
        source_path = str(record.get("source_path") or "")
        source = ROOT_DIR / source_path if source_path else None
        if source and source.exists():
            image = Image.open(source).convert("RGBA")
            source_label = source_path
        elif create_placeholders:
            image = generate_placeholder(record).convert("RGBA")
            placeholder = True
            source_label = "generated_placeholder"
        else:
            image = Image.new("RGBA", size, (0, 0, 0, 0))
            placeholder = True
            source_label = "missing"

    if transparent:
        normalized = contain_resize(tint_asset(image, accent, strength=0.18 if not placeholder else 0.0), size)
    else:
        normalized = cover_resize(image, size).convert("RGB")
    normalized.save(out_path, "PNG", optimize=True)

    thumb_path = THUMB_DIR / str(record["category"]) / f"{record['key']}.png"
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    thumb = contain_resize(normalized.convert("RGBA"), (160, 96) if not transparent else (128, 128), padding=0.04)
    thumb.save(thumb_path, "PNG", optimize=True)

    return {
        "key": record["key"],
        "path": str(record["output_path"]).replace("\\", "/"),
        "size": list(size),
        "transparent": transparent,
        "placeholder": placeholder,
        "source": source_label,
        "purpose": record.get("purpose", ""),
        "prompt": record.get("prompt", ""),
        "thumbnail": str(thumb_path.relative_to(ROOT_DIR)).replace("\\", "/"),
    }


def write_manifest(entries: list[dict[str, Any]]) -> None:
    grouped: dict[str, dict[str, Any]] = {}
    for entry in entries:
        manifest_entry = dict(entry)
        category = str(manifest_entry.pop("category"))
        key = str(manifest_entry["key"])
        grouped.setdefault(category, {})[key] = manifest_entry
    payload = {
        "version": 1,
        "root": "assets/ui",
        "placeholder_mode": True,
        "categories": grouped,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_contact_sheet(entries: list[dict[str, Any]]) -> None:
    cols = 5
    cell_w = 260
    cell_h = 178
    title_h = 56
    rows = math.ceil(len(entries) / cols)
    sheet = Image.new("RGB", (cols * cell_w + 24, rows * cell_h + title_h + 24), (10, 8, 16))
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 16), "Abyssia Card UI Asset Pack", font=font(28, bold=True), fill=(236, 229, 218))
    draw.rectangle((0, title_h - 4, sheet.width, title_h), fill=(238, 196, 82))
    for idx, entry in enumerate(entries):
        col = idx % cols
        row = idx // cols
        x = 12 + col * cell_w
        y = title_h + 12 + row * cell_h
        box = (x, y, x + cell_w - 12, y + cell_h - 10)
        draw.rounded_rectangle(box, radius=8, fill=(23, 19, 32), outline=(62, 53, 78))
        path = ROOT_DIR / str(entry["path"])
        try:
            icon = Image.open(path).convert("RGBA")
            icon.thumbnail((112, 86), Image.Resampling.LANCZOS)
            sheet.paste(icon, (x + 16 + (112 - icon.width) // 2, y + 18 + (86 - icon.height) // 2), icon)
        except OSError:
            pass
        key = str(entry["key"])
        category = str(entry["category"])
        name_font = font(14, bold=True)
        small_font = font(11)
        draw.text((x + 142, y + 24), key[:24], font=name_font, fill=(236, 229, 218))
        draw.text((x + 142, y + 50), category, font=small_font, fill=(150, 137, 128))
        state = "placeholder" if entry["placeholder"] else "asset"
        fill = (238, 196, 82) if not entry["placeholder"] else (221, 61, 78)
        draw.text((x + 142, y + 72), state, font=small_font, fill=fill)
    CONTACT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(CONTACT_SHEET, "PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-normalize", action="store_true", help="Recreate outputs from source aliases or placeholders.")
    parser.add_argument("--no-placeholders", action="store_true", help="Do not create placeholder PNGs for missing assets.")
    args = parser.parse_args()

    for folder in REQUIRED_FOLDERS:
        (ROOT_DIR / folder).mkdir(parents=True, exist_ok=True)

    records = load_records()
    entries: list[dict[str, Any]] = []
    for record in records:
        entry = normalize_record(record, force=args.force_normalize, create_placeholders=not args.no_placeholders)
        entry["category"] = record["category"]
        entries.append(entry)
        status = "placeholder" if entry["placeholder"] else "asset"
        print(f"{status}: {entry['path']}")
    write_manifest(entries)
    build_contact_sheet(entries)
    print(f"Wrote {MANIFEST_PATH.relative_to(ROOT_DIR)}")
    print(f"Wrote {CONTACT_SHEET.relative_to(ROOT_DIR)}")
    print(f"Processed {len(entries)} card UI assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
