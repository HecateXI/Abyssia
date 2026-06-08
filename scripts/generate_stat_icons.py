"""Generate stat icons for HP, STR, DEF, MANA, MAG, RES, SPD."""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from PIL import Image, ImageDraw, ImageFont

ASSET_DIR = ROOT_DIR / "data" / "assets"
SIZE = 64
EXPORT_SIZE = 128

# Stat colors matching Abyssia theme
STAT_COLORS = {
    "hp": (220, 60, 75, 255),       # Red
    "str": (245, 195, 72, 255),     # Gold/Yellow
    "def": (70, 160, 235, 255),     # Blue
    "mana": (170, 95, 245, 255),    # Purple
    "mag": (245, 145, 45, 255),     # Orange
    "res": (55, 225, 210, 255),     # Cyan
    "spd": (80, 210, 120, 255),     # Green
}

STAT_LETTERS = {
    "hp": "H",
    "str": "S",
    "def": "D",
    "mana": "M",
    "mag": "G",
    "res": "R",
    "spd": "P",
}


def _font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_stat_icon(key: str) -> Path:
    color = STAT_COLORS[key]
    letter = STAT_LETTERS[key]
    
    # Create base image
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw rounded square background
    margin = 4
    draw.rounded_rectangle(
        (margin, margin, SIZE - margin - 1, SIZE - margin - 1),
        radius=8,
        fill=color,
        outline=(0, 0, 0, 255),
        width=2
    )
    
    # Draw inner highlight
    draw.rounded_rectangle(
        (margin + 2, margin + 2, SIZE - margin - 3, SIZE - margin - 3),
        radius=6,
        outline=(255, 255, 255, 80),
        width=1
    )
    
    # Draw letter
    font = _font(32, bold=True)
    bbox = draw.textbbox((0, 0), letter, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (SIZE - tw) // 2
    y = (SIZE - th) // 2 - 2
    
    # Shadow
    draw.text((x + 2, y + 2), letter, font=font, fill=(0, 0, 0, 180))
    # Main text
    draw.text((x, y), letter, font=font, fill=(255, 255, 255, 255))
    
    # Export at 2x size
    out_dir = ASSET_DIR / "stats"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if img.size != (EXPORT_SIZE, EXPORT_SIZE):
        img = img.resize((EXPORT_SIZE, EXPORT_SIZE), Image.Resampling.NEAREST)
    
    out_path = out_dir / f"{key}.png"
    img.save(out_path, "PNG")
    print(f"Generated: stats/{key}.png")
    return out_path


if __name__ == "__main__":
    for key in STAT_COLORS.keys():
        generate_stat_icon(key)
    print(f"\nGenerated {len(STAT_COLORS)} stat icons in {ASSET_DIR / 'stats'}")
