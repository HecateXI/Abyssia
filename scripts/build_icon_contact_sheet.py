"""Build contact sheets for Abyssia weapon and passive icons."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPTS_PATH = ROOT_DIR / "data" / "icon_prompts.json"
OUT_DIR = ROOT_DIR / "tmp" / "icon_contact_sheets"

BG = (12, 10, 18)
PANEL = (23, 19, 32)
BORDER = (62, 53, 78)
TEXT = (236, 229, 218)
MUTED = (150, 137, 128)
GOLD = (215, 168, 75)
RED = (143, 29, 44)


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = _font(28, bold=True)
F_NAME = _font(15, bold=True)
F_KEY = _font(11)


def _load_records() -> list[dict[str, Any]]:
    if PROMPTS_PATH.exists():
        payload = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
        records = payload.get("records", []) if isinstance(payload, dict) else []
        return [item for item in records if isinstance(item, dict)]
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_icon_prompts import all_records

    return all_records()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, font: ImageFont.ImageFont) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    suffix = "..."
    for length in range(len(text), 0, -1):
        candidate = text[:length].rstrip() + suffix
        if draw.textlength(candidate, font=font) <= max_width:
            return candidate
    return suffix


def _icon_source(category: str, key: str) -> tuple[Path | None, str]:
    candidates = (
        (ROOT_DIR / "assets" / "emojis" / category / f"{key}.png", "processed emoji"),
        (ROOT_DIR / "assets" / "icons" / category / f"{key}.png", "premium master"),
        (ROOT_DIR / "data" / "assets" / category / f"{key}.png", "legacy fallback"),
    )
    for path, label in candidates:
        if path.exists():
            return path, label
    return None, "missing art"


def _icon_path(category: str, key: str) -> Path | None:
    return _icon_source(category, key)[0]


def _load_icon(category: str, key: str, size: int) -> Image.Image:
    path = _icon_path(category, key)
    if path:
        try:
            icon = Image.open(path).convert("RGBA")
            icon.thumbnail((size, size), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            canvas.alpha_composite(icon, ((size - icon.width) // 2, (size - icon.height) // 2))
            return canvas
        except OSError:
            pass

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((2, 2, size - 3, size - 3), radius=8, fill=(32, 27, 42, 255), outline=(92, 80, 110, 255))
    draw.line((18, size // 2, size - 18, size // 2), fill=(130, 116, 140, 255), width=3)
    return canvas


def build_sheet(records: list[dict[str, Any]], category: str) -> Path:
    category_records = [record for record in records if record.get("category") == category]
    cols = 4
    cell_w = 270
    cell_h = 190
    pad = 24
    title_h = 72
    rows = max(1, (len(category_records) + cols - 1) // cols)
    width = pad * 2 + cols * cell_w
    height = title_h + pad + rows * cell_h + pad
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    title = "Abyssia Weapon Icons" if category == "weapons" else "Abyssia Passive Icons"
    draw.rectangle((0, 0, width, title_h), fill=(16, 12, 24))
    draw.rectangle((0, title_h - 4, width, title_h), fill=RED if category == "weapons" else GOLD)
    draw.text((pad, 20), title, font=F_TITLE, fill=TEXT)

    for idx, record in enumerate(category_records):
        col = idx % cols
        row = idx // cols
        x = pad + col * cell_w
        y = title_h + pad + row * cell_h
        draw.rounded_rectangle((x, y, x + cell_w - 14, y + cell_h - 14), radius=8, fill=PANEL, outline=BORDER)
        icon = _load_icon(category, str(record["key"]), 96)
        image.paste(icon, (x + 18, y + 18), icon)
        text_x = x + 126
        name = _fit_text(draw, str(record["display_name"]), cell_w - 150, F_NAME)
        key = _fit_text(draw, str(record["key"]), cell_w - 150, F_KEY)
        emoji = _fit_text(draw, str(record["emoji_name"]), cell_w - 150, F_KEY)
        draw.text((text_x, y + 24), name, font=F_NAME, fill=TEXT)
        draw.text((text_x, y + 52), key, font=F_KEY, fill=MUTED)
        draw.text((text_x, y + 74), emoji, font=F_KEY, fill=GOLD)
        _, source_label = _icon_source(category, str(record["key"]))
        if source_label == "missing art":
            draw.text((x + 18, y + 126), "missing art", font=F_KEY, fill=(238, 110, 110))
        else:
            draw.text((x + 18, y + 126), source_label, font=F_KEY, fill=MUTED)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{category}.png"
    image.save(path, "PNG", optimize=True)
    return path


def build_combined(paths: list[Path]) -> Path | None:
    images = [Image.open(path).convert("RGB") for path in paths if path.exists()]
    if not images:
        return None
    width = max(image.width for image in images)
    height = sum(image.height for image in images)
    combined = Image.new("RGB", (width, height), BG)
    y = 0
    for image in images:
        combined.paste(image, (0, y))
        y += image.height
    path = OUT_DIR / "combined.png"
    combined.save(path, "PNG", optimize=True)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-combined", action="store_true")
    args = parser.parse_args()

    records = _load_records()
    outputs = [build_sheet(records, "weapons"), build_sheet(records, "passives")]
    if not args.no_combined:
        combined = build_combined(outputs)
        if combined:
            outputs.append(combined)
    for path in outputs:
        print(f"Wrote {path.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
