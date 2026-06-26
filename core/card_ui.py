from __future__ import annotations

import asyncio
import functools
import json
import logging
import math
import random
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from core.content_config import ASSET_DIR, ROOT_DIR, get_asset_file_path, get_creature_asset_path, safe_key

Color = tuple[int, int, int]
ColorA = tuple[int, int, int, int]

BG_TOP: Color = (14, 9, 22)
BG_BOTTOM: Color = (4, 3, 8)
PANEL: ColorA = (25, 20, 30, 232)
PANEL_DARK: ColorA = (9, 7, 12, 236)
PANEL_SOFT: ColorA = (39, 30, 44, 214)
BORDER: Color = (82, 68, 64)
TEXT: Color = (238, 230, 216)
TEXT_BRIGHT: Color = (255, 248, 232)
TEXT_MUTED: Color = (172, 154, 136)
GOLD: Color = (225, 176, 72)
CYAN: Color = (78, 178, 190)
BLUE: Color = (86, 128, 184)
PURPLE: Color = (142, 82, 198)
RED: Color = (188, 52, 62)
GREEN: Color = (76, 178, 112)
ORANGE: Color = (210, 112, 44)

# Shared thread pool for CPU-heavy image rendering so the Discord event loop stays responsive.
_RENDER_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="abyssia-render")


async def run_render(fn, *args, **kwargs):
    """Run a synchronous image/card render function in a thread pool."""
    start = asyncio.get_running_loop().time()
    result = await asyncio.get_running_loop().run_in_executor(
        _RENDER_EXECUTOR, functools.partial(fn, *args, **kwargs)
    )
    elapsed = asyncio.get_running_loop().time() - start
    if elapsed > 0.5:
        logging.getLogger("abyssia.render").info("Slow render %s: %.3fs", fn.__name__, elapsed)
    return result


RARITY_COLORS: dict[str, Color] = {
    "Common": (139, 148, 158),
    "Uncommon": (74, 222, 128),
    "Rare": (56, 189, 248),
    "Epic": (167, 139, 250),
    "Legendary": (250, 204, 21),
    "Mythic": (251, 113, 133),
    "Ancient": (249, 115, 22),
    "Patreon": (255, 66, 77),
    "Divine": (254, 243, 199),
    "Eldritch": (34, 211, 238),
    "Abyssal": (130, 90, 200),
    "Prismatic": (16, 185, 129),
    "Ethereal": (96, 165, 250),
    "Void Lord": (30, 80, 130),
    "Hidden": (147, 51, 234),
}

STAT_COLORS: dict[str, Color] = {
    "HP": RED,
    "STR": GOLD,
    "DEF": BLUE,
    "PR": BLUE,
    "MANA": PURPLE,
    "WP": PURPLE,
    "MAG": ORANGE,
    "RES": CYAN,
    "MR": CYAN,
}

_FONT_CACHE: dict[tuple[int, bool], ImageFont.ImageFont] = {}
_BG_CACHE: Image.Image | None = None
_UI_ASSET_CACHE: dict[Path, Image.Image | None] = {}
_CARD_ASSET_CACHE: dict[str, Image.Image | None] = {}
_CARD_ASSET_INDEX: dict[str, dict[str, Any]] | None = None
CARD_ASSET_MANIFEST = ROOT_DIR / "data" / "card_asset_manifest.json"
PIXEL_CARD_BG = ASSET_DIR / "ui" / "card_bg_abyssia_pixel.png"
PIXEL_FRAME_WINDOW = ASSET_DIR / "ui" / "frame_window_abyssia_pixel.png"
PIXEL_FRAME_CARD = ASSET_DIR / "ui" / "frame_card_abyssia_pixel.png"
PIXEL_FRAME_ICON = ASSET_DIR / "ui" / "frame_icon_abyssia_pixel.png"
PIXEL_FRAME_BADGE = ASSET_DIR / "ui" / "frame_badge_abyssia_pixel.png"


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def lerp_color(a: Color, b: Color, t: float) -> Color:
    t = clamp(t)
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))  # type: ignore[return-value]


def rgba(color: Color | ColorA, alpha: int) -> ColorA:
    return (color[0], color[1], color[2], max(0, min(255, alpha)))


def color_alpha(color: Color | ColorA, fallback_alpha: int = 255) -> ColorA:
    alpha = color[3] if len(color) > 3 else fallback_alpha
    return (int(color[0]), int(color[1]), int(color[2]), max(0, min(255, int(alpha))))


def cut_box_points(box: tuple[int, int, int, int], cut: int = 10) -> list[tuple[int, int]]:
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


def draw_pixel_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: Color | ColorA,
    outline: Color | ColorA | None = None,
    *,
    cut: int = 10,
    width: int = 2,
) -> None:
    points = cut_box_points(box, cut)
    draw.polygon(points, fill=color_alpha(fill))
    if outline is None:
        return
    outline_color = color_alpha(outline)
    for offset in range(max(1, width)):
        inner = (box[0] + offset, box[1] + offset, box[2] - offset, box[3] - offset)
        pts = cut_box_points(inner, max(0, cut - offset))
        draw.line(pts + [pts[0]], fill=outline_color, width=1)


def draw_pixel_glow(
    image: Image.Image,
    box: tuple[int, int, int, int],
    color: Color,
    *,
    steps: int = 5,
    step: int = 5,
    opacity: int = 72,
    cut: int = 10,
) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for idx in range(steps, 0, -1):
        pad = idx * step
        alpha = int(opacity * (idx / max(1, steps)) ** 1.7)
        draw_pixel_box(
            draw,
            (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad),
            rgba(color, max(5, alpha // 5)),
            rgba(color, alpha),
            cut=cut + pad // 2,
            width=1,
        )
    image.alpha_composite(layer)


def pixel_box_mask(size: tuple[int, int], cut: int = 10) -> Image.Image:
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(cut_box_points((0, 0, width - 1, height - 1), cut), fill=255)
    return mask


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    source = image.convert("RGB")
    target_w, target_h = size
    scale = max(target_w / source.width, target_h / source.height)
    resized = source.resize(
        (max(1, math.ceil(source.width * scale)), max(1, math.ceil(source.height * scale))),
        Image.Resampling.NEAREST,
    )
    left = max(0, (resized.width - target_w) // 2)
    top = max(0, (resized.height - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


def load_ui_asset(path: Path) -> Image.Image | None:
    if path not in _UI_ASSET_CACHE:
        try:
            asset = Image.open(path).convert("RGBA") if path.exists() else None
            if asset is not None:
                bbox = asset.getchannel("A").getbbox()
                if bbox:
                    asset = asset.crop(bbox)
            _UI_ASSET_CACHE[path] = asset
        except OSError:
            _UI_ASSET_CACHE[path] = None
    cached = _UI_ASSET_CACHE.get(path)
    return cached.copy() if cached is not None else None


def _load_card_asset_index() -> dict[str, dict[str, Any]]:
    global _CARD_ASSET_INDEX
    if _CARD_ASSET_INDEX is not None:
        return _CARD_ASSET_INDEX
    index: dict[str, dict[str, Any]] = {}
    if CARD_ASSET_MANIFEST.exists():
        try:
            payload = json.loads(CARD_ASSET_MANIFEST.read_text(encoding="utf-8"))
            categories = payload.get("categories", {}) if isinstance(payload, dict) else {}
            if isinstance(categories, dict):
                for category, records in categories.items():
                    if not isinstance(records, dict):
                        continue
                    for key, record in records.items():
                        if not isinstance(record, dict):
                            continue
                        normalized = dict(record)
                        normalized["category"] = category
                        index[str(key)] = normalized
                        index[f"{category}/{key}"] = normalized
        except json.JSONDecodeError:
            index = {}
    _CARD_ASSET_INDEX = index
    return index


def get_asset(key: str, size: tuple[int, int] | None = None) -> Image.Image | None:
    """Load a card UI asset by manifest key, returning a copy suitable for drawing."""
    lookup = str(key)
    record = _load_card_asset_index().get(lookup)
    if not record:
        return None
    cache_key = f"{lookup}|{size or ''}"
    if cache_key not in _CARD_ASSET_CACHE:
        path = ROOT_DIR / str(record.get("path", ""))
        try:
            asset = Image.open(path).convert("RGBA") if path.exists() else None
            if asset is not None and size is not None:
                transparent = bool(record.get("transparent", False))
                asset = _resize_icon(asset, size, pixel=False) if transparent else cover_resize(asset, size).convert("RGBA")
            _CARD_ASSET_CACHE[cache_key] = asset
        except OSError:
            _CARD_ASSET_CACHE[cache_key] = None
    cached = _CARD_ASSET_CACHE.get(cache_key)
    return cached.copy() if cached is not None else None


def draw_background(image: Image.Image, key: str, accent: Color | None = None) -> bool:
    asset = get_asset(key, image.size)
    if asset is None:
        if accent is not None:
            draw_depth_background(image, image.width, image.height, accent)
        return False
    image.alpha_composite(asset.convert("RGBA"))
    return True


def draw_panel_from_asset(
    image: Image.Image,
    key: str,
    box: tuple[int, int, int, int],
    accent: Color | ColorA | None = None,
    *,
    opacity: int = 255,
) -> bool:
    asset = get_asset(key)
    if asset is None:
        return False
    panel = nine_slice_resize(asset, (box[2] - box[0], box[3] - box[1]), _asset_borders(Path(str(key)), asset))
    panel = tint_ui_asset(panel, accent, 0.22)
    if opacity < 255:
        panel.putalpha(panel.getchannel("A").point(lambda p: int(p * clamp(opacity / 255))))
    image.alpha_composite(panel, (box[0], box[1]))
    return True


def _asset_borders(path: Path, asset: Image.Image) -> tuple[int, int, int, int]:
    width, height = asset.size
    if path == PIXEL_FRAME_BADGE:
        return (max(24, width // 4), max(14, height // 3), max(24, width // 4), max(14, height // 3))
    if path == PIXEL_FRAME_ICON:
        side = max(26, min(width, height) // 4)
        return (side, side, side, side)
    if path == PIXEL_FRAME_CARD:
        return (max(42, width // 5), max(30, height // 4), max(42, width // 5), max(30, height // 4))
    return (max(58, width // 5), max(42, height // 4), max(58, width // 5), max(42, height // 4))


def nine_slice_resize(asset: Image.Image, size: tuple[int, int], borders: tuple[int, int, int, int]) -> Image.Image:
    target_w, target_h = size
    if target_w <= 0 or target_h <= 0:
        return Image.new("RGBA", (max(1, target_w), max(1, target_h)), (0, 0, 0, 0))
    source_w, source_h = asset.size
    left, top, right, bottom = borders
    left = max(1, min(left, source_w // 2 - 1, target_w // 2))
    right = max(1, min(right, source_w - left - 1, target_w - left))
    top = max(1, min(top, source_h // 2 - 1, target_h // 2))
    bottom = max(1, min(bottom, source_h - top - 1, target_h - top))
    if target_w < left + right + 2 or target_h < top + bottom + 2:
        return asset.resize((target_w, target_h), Image.Resampling.NEAREST)

    out = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    def paste(src_box: tuple[int, int, int, int], dst_box: tuple[int, int, int, int]) -> None:
        x1, y1, x2, y2 = dst_box
        if x2 <= x1 or y2 <= y1:
            return
        piece = asset.crop(src_box)
        if not piece.getbbox():
            return
        dst_w, dst_h = x2 - x1, y2 - y1
        for yy in range(y1, y2, piece.height):
            for xx in range(x1, x2, piece.width):
                crop_w = min(piece.width, x2 - xx)
                crop_h = min(piece.height, y2 - yy)
                out.alpha_composite(piece.crop((0, 0, crop_w, crop_h)), (xx, yy))

    sx_mid_1, sx_mid_2 = left, source_w - right
    sy_mid_1, sy_mid_2 = top, source_h - bottom
    dx_mid_1, dx_mid_2 = left, target_w - right
    dy_mid_1, dy_mid_2 = top, target_h - bottom

    paste((0, 0, left, top), (0, 0, left, top))
    paste((sx_mid_1, 0, sx_mid_2, top), (dx_mid_1, 0, dx_mid_2, top))
    paste((source_w - right, 0, source_w, top), (target_w - right, 0, target_w, top))
    paste((0, sy_mid_1, left, sy_mid_2), (0, dy_mid_1, left, dy_mid_2))
    paste((sx_mid_1, sy_mid_1, sx_mid_2, sy_mid_2), (dx_mid_1, dy_mid_1, dx_mid_2, dy_mid_2))
    paste((source_w - right, sy_mid_1, source_w, sy_mid_2), (target_w - right, dy_mid_1, target_w, dy_mid_2))
    paste((0, source_h - bottom, left, source_h), (0, target_h - bottom, left, target_h))
    paste((sx_mid_1, source_h - bottom, sx_mid_2, source_h), (dx_mid_1, target_h - bottom, dx_mid_2, target_h))
    paste(
        (source_w - right, source_h - bottom, source_w, source_h),
        (target_w - right, target_h - bottom, target_w, target_h),
    )
    return out


def tint_ui_asset(asset: Image.Image, accent: Color | ColorA | None = None, strength: float = 0.34) -> Image.Image:
    if accent is None:
        return asset
    accent_rgb = color_alpha(accent)[:3]
    alpha = asset.getchannel("A")
    tint = Image.new("RGBA", asset.size, rgba(accent_rgb, 0))
    tint.putalpha(alpha.point(lambda p: int(p * clamp(strength))))
    return Image.alpha_composite(asset, tint)


def paste_ai_frame(
    image: Image.Image,
    box: tuple[int, int, int, int],
    asset_path: Path,
    accent: Color | ColorA | None = None,
    *,
    strength: float = 0.34,
    opacity: int = 255,
) -> bool:
    asset = load_ui_asset(asset_path)
    if asset is None:
        return False
    frame = nine_slice_resize(asset, (box[2] - box[0], box[3] - box[1]), _asset_borders(asset_path, asset))
    frame = tint_ui_asset(frame, accent, strength)
    if opacity < 255:
        frame.putalpha(frame.getchannel("A").point(lambda p: int(p * clamp(opacity / 255))))
    image.alpha_composite(frame, (box[0], box[1]))
    return True


def draw_generated_panel_fill(
    image: Image.Image,
    box: tuple[int, int, int, int],
    fill: Color | ColorA,
    accent: Color | ColorA,
    cut: int,
    texture_alpha: int = 34,
) -> None:
    width, height = box[2] - box[0], box[3] - box[1]
    if width <= 0 or height <= 0:
        return
    fill_rgba = color_alpha(fill)
    mask = pixel_box_mask((width, height), cut)
    global _BG_CACHE
    if _BG_CACHE is None and PIXEL_CARD_BG.exists():
        try:
            _BG_CACHE = Image.open(PIXEL_CARD_BG).convert("RGB")
        except OSError:
            _BG_CACHE = None
    if _BG_CACHE is not None and texture_alpha > 0:
        base = cover_resize(_BG_CACHE, (width, height)).convert("RGBA")
        # Keep the generated art visible inside panels, but tint it enough for text readability.
        tint_alpha = max(82, min(fill_rgba[3], 150))
        base.alpha_composite(Image.new("RGBA", (width, height), (*fill_rgba[:3], tint_alpha)))
    else:
        base = Image.new("RGBA", (width, height), fill_rgba)
    edge = Image.new("RGBA", (width, height), rgba(color_alpha(accent)[:3], 0))
    edge.putalpha(mask.filter(ImageFilter.FIND_EDGES).point(lambda p: int(p * 24 / 255)))
    base.alpha_composite(edge)
    panel_alpha = 248 if _BG_CACHE is not None and texture_alpha > 0 else fill_rgba[3]
    base.putalpha(mask.point(lambda p: int(p * panel_alpha / 255)))
    image.alpha_composite(base, (box[0], box[1]))


def draw_ai_box(
    image: Image.Image,
    box: tuple[int, int, int, int],
    fill: Color | ColorA,
    border: Color | ColorA,
    asset_path: Path,
    *,
    cut: int = 10,
    texture_alpha: int = 34,
    tint_strength: float = 0.32,
) -> bool:
    draw_generated_panel_fill(image, box, fill, border, cut, texture_alpha=texture_alpha)
    return paste_ai_frame(image, box, asset_path, border, strength=tint_strength)


def rarity_color(rarity: str | None) -> Color:
    return RARITY_COLORS.get(str(rarity or "Common"), RARITY_COLORS["Common"])


def load_fonts() -> None:
    for size in (18, 20, 22, 24, 26, 28, 32, 36, 42, 48, 56):
        get_font(size)
        get_font(size, bold=True)


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    names = [
        str(ROOT_DIR / "assets" / "fonts" / "alagard.ttf"),
        "CascadiaMono.ttf",
        "consolab.ttf" if bold else "consola.ttf",
        "AGENCYB.TTF" if bold else "AGENCYR.TTF",
        "bahnschrift.ttf",
        "courbd.ttf" if bold else "cour.ttf",
        "consolab.ttf" if bold else "consola.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "NotoSans-Bold.ttf" if bold else "NotoSans.ttf",
    ]
    font_dir = Path("C:/Windows/Fonts")
    for name in names:
        for path in (font_dir / name, Path(name)):
            try:
                font = ImageFont.truetype(str(path), size)
                _FONT_CACHE[key] = font
                return font
            except OSError:
                continue
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), str(text), font=font)
    return box[2] - box[0], box[3] - box[1]


def text_bounds(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), str(text), font=font)


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    return text_size(draw, text, font)[0]


def truncate_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, font: ImageFont.ImageFont) -> str:
    text = str(text)
    if text_width(draw, text, font) <= max_width:
        return text
    ellipsis = "..."
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if text_width(draw, text[:mid] + ellipsis, font) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + ellipsis if lo > 0 else ellipsis


def wrap_text(
    draw: ImageDraw.ImageDraw, text: str, max_width: int, font: ImageFont.ImageFont, max_lines: int
) -> list[str]:
    words = str(text).replace("\n", " ").split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and words:
        lines[-1] = truncate_text(draw, lines[-1], max_width, font)
    return lines


def draw_text_fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
    fill: Color | ColorA,
    min_size: int = 16,
    align: str = "left",
    bold: bool | None = None,
) -> ImageFont.ImageFont:
    draw.fontmode = "1"
    text = str(text).upper()
    x1, y1, x2, y2 = box
    chosen = font
    inferred_bold = bool(bold) if bold is not None else False
    max_width = max(1, x2 - x1)
    max_height = max(1, y2 - y1)
    while chosen.size > min_size:
        raw_box = text_bounds(draw, str(text), chosen)
        raw_w = raw_box[2] - raw_box[0]
        raw_h = raw_box[3] - raw_box[1]
        if raw_w <= max_width and raw_h <= max_height:
            break
        chosen = get_font(chosen.size - 1, bold=inferred_bold)
    rendered = truncate_text(draw, str(text), max_width, chosen)
    tb = text_bounds(draw, rendered, chosen)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    if align == "center":
        x = x1 + (max_width - tw) // 2 - tb[0]
    elif align == "right":
        x = x2 - tw - tb[0]
    else:
        x = x1 - tb[0]
    y = y1 + max(0, (max_height - th) // 2) - tb[1]
    draw.text((x, y), rendered, font=chosen, fill=fill)
    return chosen


def draw_multiline_text_fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
    fill: Color | ColorA,
    min_size: int = 16,
    line_spacing: int = 6,
    max_lines: int | None = None,
) -> ImageFont.ImageFont:
    draw.fontmode = "1"
    text = str(text).upper()
    x1, y1, x2, y2 = box
    chosen = font
    max_lines = max_lines or max(1, (y2 - y1) // max(1, font.size + line_spacing))
    while chosen.size > min_size:
        lines = wrap_text(draw, text, x2 - x1, chosen, max_lines)
        total_h = len(lines) * chosen.size + max(0, len(lines) - 1) * line_spacing
        if total_h <= y2 - y1:
            break
        chosen = get_font(chosen.size - 1)
    lines = wrap_text(draw, text, x2 - x1, chosen, max_lines)
    y = y1
    for line in lines:
        draw.text((x1, y), line, font=chosen, fill=fill)
        y += chosen.size + line_spacing
    return chosen


CARD_OUTPUT_MAX_SIZE = (1280, 900)
CARD_OUTPUT_COLORS = 256


def _prepare_card_output(
    image: Image.Image,
    *,
    max_size: tuple[int, int] | None = None,
    colors: int | None = None,
) -> Image.Image:
    max_size = max_size or CARD_OUTPUT_MAX_SIZE
    colors = colors or CARD_OUTPUT_COLORS
    prepared = image.convert("RGBA")
    if prepared.width > max_size[0] or prepared.height > max_size[1]:
        prepared.thumbnail(max_size, Image.Resampling.LANCZOS)
    opaque = Image.new("RGBA", prepared.size, (*BG_BOTTOM, 255))
    opaque.alpha_composite(prepared)
    try:
        return opaque.quantize(colors=colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    except (OSError, ValueError):
        return opaque.convert("RGB")


def save_png(
    image: Image.Image,
    *,
    max_size: tuple[int, int] | None = None,
    colors: int | None = None,
    compress_level: int = 3,
) -> BytesIO:
    output = BytesIO()
    _prepare_card_output(image, max_size=max_size, colors=colors).save(
        output,
        "PNG",
        optimize=False,
        compress_level=compress_level,
    )
    output.seek(0)
    return output


def draw_depth_shadow(
    layer: Image.Image, offset: tuple[int, int] = (0, 10), blur: int = 18, opacity: int = 120
) -> Image.Image:
    alpha = layer.convert("RGBA").split()[-1].point(lambda p: int(p * opacity / 255))
    shadow = Image.new(
        "RGBA", (layer.width + blur * 4 + abs(offset[0]), layer.height + blur * 4 + abs(offset[1])), (0, 0, 0, 0)
    )
    x = blur * 2 + max(0, offset[0])
    y = blur * 2 + max(0, offset[1])
    shadow.paste((0, 0, 0, opacity), (x, y), alpha)
    return shadow.filter(ImageFilter.GaussianBlur(blur))


def draw_shadow(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    radius: int = 18,
    blur: int = 18,
    offset: tuple[int, int] = (0, 10),
    opacity: int = 120,
) -> None:
    layer = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    mask = Image.new("L", layer.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, layer.width - 1, layer.height - 1), radius=radius, fill=255)
    layer.putalpha(mask)
    shadow = draw_depth_shadow(layer, offset=offset, blur=blur, opacity=opacity)
    image.alpha_composite(shadow, (box[0] - blur * 2, box[1] - blur * 2))


def draw_glow(
    image: Image.Image, box: tuple[int, int, int, int], color: Color, blur: int = 28, opacity: int = 80
) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle(box, radius=max(10, min(box[2] - box[0], box[3] - box[1]) // 8), fill=rgba(color, opacity))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    image.alpha_composite(layer)


def draw_rim_light(image: Image.Image, mask: Image.Image, color: Color, blur: int = 8) -> Image.Image:
    alpha = mask.convert("L")
    expanded = ImageOps.expand(alpha, border=blur * 2, fill=0).filter(ImageFilter.MaxFilter(blur * 2 + 1))
    original = ImageOps.expand(alpha, border=blur * 2, fill=0)
    rim = Image.new("L", expanded.size, 0)
    rim = ImageChops_subtract(expanded, original).filter(ImageFilter.GaussianBlur(blur))
    light = Image.new("RGBA", expanded.size, rgba(color, 145))
    light.putalpha(rim)
    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    out.alpha_composite(light, (-blur * 2, -blur * 2))
    return out


def ImageChops_subtract(a: Image.Image, b: Image.Image) -> Image.Image:
    return ImageChops.subtract(a, b)


def draw_vignette(image: Image.Image, strength: float = 0.78) -> None:
    width, height = image.size
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = width // 2, height // 2
    max_r = int(math.hypot(cx, cy))
    for i in range(42):
        t = i / 41
        r = int(max_r * (0.38 + t * 0.72))
        alpha = int(255 * strength * (t**2) / 5)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(0, 0, 0, alpha), width=30)
    image.alpha_composite(layer)


def draw_particles(image: Image.Image, color: Color = CYAN, count: int = 70, seed: int = 137) -> None:
    rng = random.Random(seed)
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for _ in range(count):
        x = rng.randint(24, width - 24)
        y = rng.randint(24, height - 24)
        radius = rng.choice((1, 1, 2, 3))
        alpha = rng.randint(18, 80)
        draw.rectangle((x, y, x + radius, y + radius), fill=rgba(lerp_color(color, TEXT_BRIGHT, 0.25), alpha))


def draw_abyssia_background(
    image: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int, theme: Any = None
) -> None:
    accent = theme.get("accent", PURPLE) if isinstance(theme, dict) else PURPLE
    draw_depth_background(image, width, height, accent)


def draw_depth_background(image: Image.Image, width: int, height: int, accent: Color = PURPLE) -> None:
    image_rgba = image.convert("RGBA")
    draw = ImageDraw.Draw(image_rgba)
    global _BG_CACHE
    if _BG_CACHE is None:
        manifest_bg = get_asset("abyssia_dark_base")
        if manifest_bg is not None:
            _BG_CACHE = manifest_bg.convert("RGB")
    if _BG_CACHE is None and PIXEL_CARD_BG.exists():
        try:
            _BG_CACHE = Image.open(PIXEL_CARD_BG).convert("RGB")
        except OSError:
            _BG_CACHE = None
    if _BG_CACHE is not None:
        image_rgba.alpha_composite(cover_resize(_BG_CACHE, (width, height)).convert("RGBA"))
        draw.rectangle((0, 0, width, height), fill=(0, 0, 0, 8))
        draw.rectangle((0, 0, width - 1, height - 1), outline=rgba(lerp_color(accent, TEXT_BRIGHT, 0.18), 44), width=2)
    else:
        band = 6
        for y in range(0, height, band):
            t = y / max(1, height - 1)
            draw.rectangle((0, y, width, min(height, y + band)), fill=lerp_color(BG_TOP, BG_BOTTOM, t))

    wash = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wash)
    wd.rectangle((0, 0, width, height), fill=rgba(lerp_color(accent, BG_BOTTOM, 0.84), 10))
    wd.rectangle((0, height - 28, width, height), fill=rgba(lerp_color(accent, CYAN, 0.35), 18))
    image_rgba.alpha_composite(wash)

    rune = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rune)
    rng = random.Random(width * 1009 + height * 37 + sum(accent))
    for _ in range(14):
        x = rng.randint(40, width - 40)
        y = rng.randint(90, height - 70)
        length = rng.randint(10, 42)
        if rng.random() < 0.55:
            rd.rectangle((x, y, x + length, y + 2), fill=rgba(accent, rng.randint(8, 22)))
            rd.rectangle((x + length // 2, y - 4, x + length // 2 + 2, y + 8), fill=rgba(accent, rng.randint(6, 18)))
        else:
            pts = [(x, y - 8), (x + 8, y), (x, y + 8), (x - 8, y)]
            rd.polygon(pts, outline=rgba(accent, rng.randint(8, 24)))
    image_rgba.alpha_composite(rune)
    draw_particles(image_rgba, accent, count=max(20, width * height // 36000))
    for step, alpha in ((0, 120), (8, 46)):
        draw.rectangle((step, step, width - step - 1, height - step - 1), outline=(0, 0, 0, alpha), width=6)
    image.paste(image_rgba.convert(image.mode))


def new_card(width: int = 1200, height: int = 720, accent: Color = PURPLE) -> Image.Image:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_abyssia_background(image, draw, width, height, {"accent": accent})
    return image


def draw_beveled_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: ColorA = PANEL,
    border: Color | ColorA = BORDER,
    highlight: Color | ColorA = (255, 255, 255, 42),
    shadow: Color | ColorA = (0, 0, 0, 76),
    radius: int = 22,
) -> None:
    x1, y1, x2, y2 = box
    cut = max(7, min(radius, 18, (x2 - x1) // 8, (y2 - y1) // 6))
    border_rgb = color_alpha(border)[:3]
    draw_pixel_box(draw, box, fill, rgba((0, 0, 0), 230), cut=cut, width=3)
    draw_pixel_box(draw, (x1 + 2, y1 + 2, x2 - 2, y2 - 2), (0, 0, 0, 0), border, cut=max(4, cut - 2), width=2)
    texture = lerp_color(border_rgb, TEXT_BRIGHT, 0.16)
    for y in range(y1 + 14, y2 - 12, 18):
        draw.line((x1 + cut + 8, y, x2 - cut - 8, y), fill=rgba(texture, 12), width=1)
    rng = random.Random((x2 - x1) * 917 + (y2 - y1) * 313 + sum(border_rgb))
    for _ in range(max(2, (x2 - x1) * (y2 - y1) // 52000)):
        px = rng.randint(x1 + cut + 8, max(x1 + cut + 8, x2 - cut - 12))
        py = rng.randint(y1 + 10, max(y1 + 10, y2 - 14))
        draw.rectangle((px, py, px + 2, py + 2), fill=rgba(texture, rng.randint(18, 34)))
    inner = (x1 + 5, y1 + 5, x2 - 5, y2 - 5)
    draw_pixel_box(draw, inner, (0, 0, 0, 0), rgba(border, 76), cut=max(4, cut - 4), width=1)
    draw.line((x1 + cut + 4, y1 + 4, x2 - cut - 4, y1 + 4), fill=color_alpha(highlight), width=2)
    draw.line((x1 + 4, y1 + cut + 4, x1 + 4, y2 - cut - 4), fill=color_alpha(highlight), width=2)
    draw.line((x1 + cut + 4, y2 - 5, x2 - cut - 4, y2 - 5), fill=color_alpha(shadow), width=2)
    draw.line((x2 - 5, y1 + cut + 4, x2 - 5, y2 - cut - 4), fill=color_alpha(shadow), width=2)
    for px, py in ((x1 + 9, y1 + 9), (x2 - 13, y1 + 9), (x1 + 9, y2 - 13), (x2 - 13, y2 - 13)):
        draw.rectangle((px, py, px + 4, py + 4), fill=rgba(border, 130))


def draw_pixel_plaque(
    image: Image.Image,
    box: tuple[int, int, int, int],
    fill: ColorA = PANEL,
    border: Color | ColorA = BORDER,
    *,
    radius: int = 18,
    shadow: bool = True,
    glow: bool | Color = False,
) -> None:
    x1, y1, x2, y2 = box
    width, height = x2 - x1, y2 - y1
    if width <= 0 or height <= 0:
        return
    cut = max(6, min(radius, 18, width // 8, height // 5))
    border_rgba = color_alpha(border)
    border_rgb = border_rgba[:3]
    if glow:
        glow_color = border_rgb if glow is True else glow
        draw_pixel_glow(image, box, glow_color, opacity=44, cut=cut, steps=3, step=4)
    if shadow:
        shadow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        draw_pixel_box(
            sd,
            (x1 + 7, y1 + 9, x2 + 7, y2 + 9),
            (0, 0, 0, 112),
            None,
            cut=cut,
        )
        image.alpha_composite(shadow_layer)

    draw = ImageDraw.Draw(image)
    fill_rgba = color_alpha(fill)
    panel_fill = lerp_color(fill_rgba[:3], BG_BOTTOM, 0.28)
    draw_pixel_box(draw, box, (*panel_fill, fill_rgba[3]), rgba((0, 0, 0), 238), cut=cut, width=3)
    draw_pixel_box(
        draw,
        (x1 + 3, y1 + 3, x2 - 3, y2 - 3),
        (0, 0, 0, 0),
        rgba(border_rgb, min(235, max(150, border_rgba[3]))),
        cut=max(3, cut - 3),
        width=2,
    )
    draw_pixel_box(
        draw,
        (x1 + 8, y1 + 8, x2 - 8, y2 - 8),
        (0, 0, 0, 0),
        rgba(lerp_color(border_rgb, TEXT_BRIGHT, 0.24), 68),
        cut=max(2, cut - 8),
        width=1,
    )

    top_color = rgba(lerp_color(border_rgb, TEXT_BRIGHT, 0.18), 78)
    bot_color = rgba((0, 0, 0), 120)
    draw.line((x1 + cut + 8, y1 + 7, x2 - cut - 8, y1 + 7), fill=top_color, width=2)
    draw.line((x1 + cut + 10, y2 - 8, x2 - cut - 10, y2 - 8), fill=bot_color, width=2)
    draw.line((x1 + 7, y1 + cut + 8, x1 + 7, y2 - cut - 8), fill=top_color, width=2)
    draw.line((x2 - 8, y1 + cut + 8, x2 - 8, y2 - cut - 8), fill=bot_color, width=2)

    rng = random.Random(width * 1009 + height * 131 + sum(border_rgb))
    speckle = lerp_color(border_rgb, TEXT_BRIGHT, 0.12)
    for _ in range(max(2, width * height // 42000)):
        px = rng.randint(x1 + cut + 8, max(x1 + cut + 8, x2 - cut - 12))
        py = rng.randint(y1 + 10, max(y1 + 10, y2 - 12))
        draw.rectangle((px, py, px + 1, py + 1), fill=rgba(speckle, rng.randint(18, 34)))
    for py in range(y1 + 14, y2 - 12, 12):
        draw.line((x1 + cut + 10, py, x2 - cut - 10, py), fill=rgba(border_rgb, 8), width=1)

    rivet = rgba(lerp_color(border_rgb, TEXT_BRIGHT, 0.2), 150)
    for px, py in (
        (x1 + cut - 1, y1 + 6),
        (x2 - cut - 5, y1 + 6),
        (x1 + cut - 1, y2 - 10),
        (x2 - cut - 5, y2 - 10),
    ):
        draw.rectangle((px, py, px + 4, py + 4), fill=rivet)
        draw.point((px + 1, py + 1), fill=rgba(TEXT_BRIGHT, 95))


def draw_pixel_platform(
    image: Image.Image,
    center: tuple[int, int],
    width: int,
    height: int,
    accent: Color | None = None,
    *,
    alpha: int = 130,
) -> None:
    cx, cy = center
    accent = accent or GOLD
    draw = ImageDraw.Draw(image)
    half_h = max(6, height // 2)
    for row in range(-half_h, half_h + 1, 3):
        t = abs(row) / max(1, half_h)
        row_w = int(width * (1 - t * t * 0.72))
        if row_w <= 0:
            continue
        y = cy + row
        shade = max(20, alpha - int(t * 64))
        draw.rectangle((cx - row_w // 2, y, cx + row_w // 2, y + 2), fill=(0, 0, 0, shade))
    rim_w = int(width * 0.76)
    draw.line((cx - rim_w // 2, cy - half_h + 3, cx + rim_w // 2, cy - half_h + 3), fill=rgba(accent, 52), width=2)
    draw.line((cx - int(width * 0.42), cy + half_h - 2, cx + int(width * 0.42), cy + half_h - 2), fill=rgba((0, 0, 0), 150), width=2)


def draw_panel(
    image: Image.Image,
    box: tuple[int, int, int, int],
    fill: ColorA = PANEL,
    border: Color | ColorA = BORDER,
    radius: int = 18,
    glow: bool | Color = False,
) -> None:
    draw_pixel_plaque(image, box, fill=fill, border=border, radius=radius, glow=glow)


def draw_header(
    image: Image.Image,
    title: str,
    subtitle: str | None = None,
    right_label: str = "ABYSSIA",
    accent: Color | None = None,
) -> int:
    accent = accent or PURPLE
    width, _ = image.size
    layer = Image.new("RGBA", (width, 104), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.fontmode = "1"
    shadow_w = min(width - 64, 680)
    draw_pixel_box(draw, (30, 14, 54 + shadow_w, 92), (0, 0, 0, 104), rgba(accent, 60), cut=12, width=1)
    draw.rectangle((46, 84, min(width - 220, 420), 88), fill=rgba(accent, 210))
    for x in range(46, min(width - 220, 420), 18):
        draw.rectangle((x, 84, x + 7, 87), fill=rgba(TEXT_BRIGHT, 54))
    font_title = get_font(44, bold=True)
    font_sub = get_font(22)
    title_text = truncate_text(draw, title.upper(), width - 360, font_title)
    draw.text((45, 25), title_text, font=font_title, fill=(0, 0, 0, 190))
    draw.text((42, 22), truncate_text(draw, title.upper(), width - 360, font_title), font=font_title, fill=TEXT_BRIGHT)
    if subtitle:
        sub = truncate_text(draw, subtitle, width - 360, font_sub)
        draw.text((47, 70), sub, font=font_sub, fill=(0, 0, 0, 160))
        draw.text((44, 68), truncate_text(draw, subtitle, width - 360, font_sub), font=font_sub, fill=TEXT_MUTED)
    font_right = get_font(22, bold=True)
    rw = text_width(draw, right_label, font_right)
    right_box = (width - rw - 76, 28, width - 34, 64)
    draw_pixel_box(draw, right_box, (0, 0, 0, 96), rgba(accent, 94), cut=9, width=1)
    draw.text((width - rw - 54, 36), right_label.upper(), font=font_right, fill=GOLD)
    image.alpha_composite(layer)
    return 104


def draw_footer(image: Image.Image, text: str, accent: Color = BORDER) -> None:
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"
    width, height = image.size
    box = (38, height - 48, width - 38, height - 24)
    draw_pixel_box(draw, box, (0, 0, 0, 82), rgba(accent, 70), cut=8, width=1)
    draw.rectangle((box[0] + 22, box[1] + 3, box[0] + 160, box[1] + 5), fill=rgba(accent, 100))
    draw.rectangle((box[2] - 160, box[1] + 3, box[2] - 22, box[1] + 5), fill=rgba(accent, 100))
    font = get_font(20)
    draw_text_fit(draw, text, (box[0] + 18, box[1], box[2] - 18, box[3]), font, TEXT_MUTED, min_size=18, align="center")


def draw_progress_bar(
    image: Image.Image,
    box: tuple[int, int, int, int],
    value: int | float,
    maximum: int | float,
    color: Color = GREEN,
    label: str | None = None,
) -> None:
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"
    x1, y1, x2, y2 = box
    ratio = clamp(float(value) / max(1.0, float(maximum)))
    cut = max(3, min(8, (y2 - y1) // 3))
    draw_generated_panel_fill(image, box, (8, 7, 15, 245), rgba(BORDER, 190), cut, texture_alpha=10)
    fill_w = max(0, int((x2 - x1 - 6) * ratio))
    if fill_w:
        fill_box = (x1 + 3, y1 + 3, min(x2 - 3, x1 + 3 + fill_w), y2 - 3)
        draw_pixel_box(draw, fill_box, rgba(color, 224), None, cut=max(1, cut - 2))
        for sx in range(fill_box[0] + 4, fill_box[2] - 4, 10):
            draw.rectangle((sx, fill_box[1] + 3, sx + 4, fill_box[1] + 5), fill=rgba(TEXT_BRIGHT, 72))
    if not paste_ai_frame(image, box, PIXEL_FRAME_BADGE, color, strength=0.28):
        draw_pixel_box(draw, box, (0, 0, 0, 0), rgba(BORDER, 190), cut=cut, width=2)
    if label:
        font = get_font(max(18, min(24, y2 - y1 - 8)), bold=True)
        draw_text_fit(draw, label, (x1 + 10, y1, x2 - 10, y2), font, TEXT_BRIGHT, min_size=16, align="center")


def draw_rarity_badge(image: Image.Image, box: tuple[int, int, int, int], rarity: str) -> None:
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"
    color = rarity_color(rarity)
    cut = max(4, (box[3] - box[1]) // 4)
    if not draw_ai_box(
        image,
        box,
        rgba(color, 68),
        rgba(color, 235),
        PIXEL_FRAME_BADGE,
        cut=cut,
        texture_alpha=0,
        tint_strength=0.46,
    ):
        draw_pixel_box(draw, box, rgba(color, 54), rgba(color, 230), cut=cut, width=2)
    text_fill = lerp_color(color, TEXT_BRIGHT, 0.52)
    draw_text_fit(
        draw,
        rarity.upper(),
        (box[0] + 12, box[1], box[2] - 12, box[3]),
        get_font(18, bold=True),
        text_fill,
        11,
        "center",
        True,
    )


def draw_rarity_frame(image: Image.Image, box: tuple[int, int, int, int], rarity: str) -> None:
    key = safe_key(rarity).replace("_lord", "_lord")
    color = rarity_color(rarity)
    if not draw_panel_from_asset(image, f"rarity_frames/{key}", box, color):
        draw_icon_frame(image, box, color, color)


def draw_tag(image: Image.Image, box: tuple[int, int, int, int], label: str, color: Color) -> None:
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"
    cut = max(4, (box[3] - box[1]) // 4)
    if not draw_ai_box(
        image,
        box,
        rgba(color, 58),
        rgba(color, 220),
        PIXEL_FRAME_BADGE,
        cut=cut,
        texture_alpha=0,
        tint_strength=0.42,
    ):
        draw_pixel_box(draw, box, rgba(color, 46), rgba(color, 220), cut=cut, width=2)
    text_fill = TEXT_BRIGHT if color == TEXT_MUTED else lerp_color(color, TEXT_BRIGHT, 0.45)
    draw_text_fit(
        draw,
        label.upper(),
        (box[0] + 10, box[1], box[2] - 10, box[3]),
        get_font(18, bold=True),
        text_fill,
        11,
        "center",
        True,
    )


def draw_stat_pill(image: Image.Image, box: tuple[int, int, int, int], label: str, value: str, color: Color) -> None:
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"
    if not draw_ai_box(
        image,
        box,
        (8, 7, 15, 224),
        rgba(color, 190),
        PIXEL_FRAME_BADGE,
        cut=8,
        texture_alpha=10,
        tint_strength=0.36,
    ):
        draw_pixel_box(draw, box, (8, 7, 15, 224), rgba(color, 180), cut=8, width=2)
    draw.line((box[0] + 10, box[1] + 4, box[2] - 10, box[1] + 4), fill=rgba(TEXT_BRIGHT, 40), width=1)
    draw_text_fit(
        draw,
        label.upper(),
        (box[0] + 14, box[1] + 6, box[2] - 14, box[1] + 28),
        get_font(18),
        TEXT_MUTED,
        min_size=11,
    )
    draw_text_fit(
        draw,
        str(value),
        (box[0] + 14, box[1] + 28, box[2] - 14, box[3] - 8),
        get_font(28, bold=True),
        color,
        min_size=14,
        bold=True,
    )


def draw_stat_grid(
    image: Image.Image,
    stats: Iterable[tuple[str, int | str, Color | None]],
    box: tuple[int, int, int, int],
    columns: int = 4,
    hide_zero: bool = False,
) -> None:
    items = [(label, value, color or STAT_COLORS.get(label.upper(), TEXT_BRIGHT)) for label, value, color in stats]
    if hide_zero:
        items = [(label, value, color) for label, value, color in items if str(value) not in {"0", "+0", "0%"}]
    if not items:
        return
    x1, y1, x2, y2 = box
    gap = 10
    rows = math.ceil(len(items) / columns)
    cell_w = (x2 - x1 - gap * (columns - 1)) // columns
    cell_h = min(72, (y2 - y1 - gap * (rows - 1)) // max(1, rows))
    for idx, (label, value, color) in enumerate(items):
        col = idx % columns
        row = idx // columns
        sx = x1 + col * (cell_w + gap)
        sy = y1 + row * (cell_h + gap)
        draw_stat_pill(image, (sx, sy, sx + cell_w, sy + cell_h), label, str(value), color)


def draw_icon_frame(
    image: Image.Image, box: tuple[int, int, int, int], accent: Color, rarity_color_: Color | None = None
) -> None:
    rarity_color_ = rarity_color_ or accent
    draw_pixel_glow(image, box, accent, opacity=58, cut=13)
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    draw_pixel_box(sd, (box[0] + 5, box[1] + 7, box[2] + 5, box[3] + 7), (0, 0, 0, 82), None, cut=13)
    image.alpha_composite(shadow)
    if not draw_ai_box(
        image,
        box,
        PANEL_DARK,
        rgba(rarity_color_, 220),
        PIXEL_FRAME_ICON,
        cut=14,
        texture_alpha=18,
        tint_strength=0.4,
    ):
        draw_panel(image, box, fill=PANEL_DARK, border=rarity_color_, radius=14, glow=accent)
    draw = ImageDraw.Draw(image)
    draw_pixel_box(
        draw,
        (box[0] + 10, box[1] + 10, box[2] - 10, box[3] - 10),
        (4, 4, 10, 165),
        rgba(accent, 90),
        cut=9,
        width=1,
    )


def draw_floating_frame(
    image: Image.Image, box: tuple[int, int, int, int], accent_color: Color, rarity_color: Color | None = None
) -> None:
    draw_glow(image, box, rarity_color or accent_color, blur=34, opacity=58)
    draw_icon_frame(image, box, accent_color, rarity_color)


def _resize_icon(icon: Image.Image, size: tuple[int, int], pixel: bool = False) -> Image.Image:
    icon = icon.convert("RGBA")
    bbox = icon.getbbox()
    if bbox:
        icon = icon.crop(bbox)
    resample = Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS
    icon.thumbnail(size, resample)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(icon, ((size[0] - icon.width) // 2, (size[1] - icon.height) // 2))
    return canvas


@functools.lru_cache(maxsize=512)
def load_asset_icon(kind: str, key: str, size: tuple[int, int], pixel: bool | None = None) -> Image.Image:
    if kind == "stats_battle":
        path = ASSET_DIR / "stats_battle" / f"{safe_key(key)}.png"
        path = path if path.exists() else None
    else:
        path = get_creature_asset_path(safe_key(key)) if kind == "creatures" else get_asset_file_path(kind, key)
    if path is None:
        direct = ASSET_DIR / kind / f"{safe_key(key)}.png"
        path = direct if direct.exists() else None
    if path and path.exists():
        try:
            return _resize_icon(
                Image.open(path),
                size,
                pixel=bool(pixel if pixel is not None else kind in {"creatures", "weapons", "passives"}),
            )
        except OSError:
            pass
    fallback = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(fallback)
    accent = CYAN if kind in {"weapons", "passives"} else BORDER
    if not draw_ai_box(
        fallback,
        (4, 4, size[0] - 4, size[1] - 4),
        rgba(PANEL_DARK, 230),
        rgba(accent, 190),
        PIXEL_FRAME_ICON,
        cut=max(6, min(size) // 7),
        texture_alpha=12,
        tint_strength=0.34,
    ):
        draw_pixel_box(
            draw,
            (4, 4, size[0] - 4, size[1] - 4),
            rgba(PANEL_DARK, 230),
            rgba(accent, 170),
            cut=max(6, min(size) // 7),
            width=2,
        )
    draw.text(
        (size[0] // 2 - 6, size[1] // 2 - 12), "?", font=get_font(max(22, min(size) // 3), bold=True), fill=TEXT_MUTED
    )
    return fallback


def paste_icon_fit(image: Image.Image, icon: Image.Image, box: tuple[int, int, int, int], pixel: bool = False) -> None:
    resized = _resize_icon(icon, (box[2] - box[0], box[3] - box[1]), pixel=pixel)
    image.alpha_composite(resized, (box[0], box[1]))


def paste_pixel_art_fit(image: Image.Image, icon: Image.Image, box: tuple[int, int, int, int]) -> None:
    paste_icon_fit(image, icon, box, pixel=True)


def paste_icon_3d(
    image: Image.Image,
    icon: Image.Image,
    center: tuple[int, int],
    size: int,
    glow_color: Color,
    *,
    glow_alpha: int = 76,
    rim_light: bool = True,
) -> None:
    icon = _resize_icon(icon, (size, size), pixel=True)
    x = center[0] - size // 2
    y = center[1] - size // 2 - 8
    shadow_blur = max(2, int(size * 0.023))
    glow_blur = max(4, int(size * 0.055))
    shadow = Image.new("RGBA", (size, size // 3), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((12, 4, size - 12, size // 3 - 2), fill=(0, 0, 0, 95))
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
    image.alpha_composite(shadow, (x, center[1] + size // 3))
    if glow_alpha > 0:
        glow = Image.new("RGBA", (size + 90, size + 90), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((20, 20, size + 70, size + 70), fill=rgba(glow_color, glow_alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(glow_blur))
        image.alpha_composite(glow, (center[0] - glow.width // 2, center[1] - glow.height // 2 - 8))
    if rim_light:
        mask = icon.split()[-1]
        rim = draw_rim_light(icon, mask, lerp_color(glow_color, TEXT_BRIGHT, 0.25), blur=max(2, glow_blur // 5))
        image.alpha_composite(rim, (x, y))
    image.alpha_composite(icon, (x, y))


def paste_portrait_3d(image: Image.Image, portrait: Image.Image, center: tuple[int, int], size: int, glow_color: Color) -> None:
    paste_icon_3d(image, portrait, center, size, glow_color)


def paste_icon_3d_clipped(
    image: Image.Image,
    icon: Image.Image,
    center: tuple[int, int],
    size: int,
    glow_color: Color,
    clip_box: tuple[int, int, int, int],
    clip_radius: int = 8,
) -> None:
    icon = _resize_icon(icon, (size, size), pixel=True)
    x = center[0] - size // 2
    y = center[1] - size // 2 - 8
    shadow_blur = max(2, int(size * 0.023))
    glow_blur = max(4, int(size * 0.055))
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", (size, size // 3), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((12, 4, size - 12, size // 3 - 2), fill=(0, 0, 0, 95))
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
    layer.alpha_composite(shadow, (x, center[1] + size // 3))
    glow = Image.new("RGBA", (size + 90, size + 90), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((20, 20, size + 70, size + 70), fill=rgba(glow_color, 76))
    glow = glow.filter(ImageFilter.GaussianBlur(glow_blur))
    layer.alpha_composite(glow, (center[0] - glow.width // 2, center[1] - glow.height // 2 - 8))
    mask = icon.split()[-1]
    rim = draw_rim_light(icon, mask, lerp_color(glow_color, TEXT_BRIGHT, 0.25), blur=max(2, glow_blur // 5))
    layer.alpha_composite(rim, (x, y))
    layer.alpha_composite(icon, (x, y))
    clip_mask = Image.new("L", image.size, 0)
    cmd = ImageDraw.Draw(clip_mask)
    cmd.rounded_rectangle(clip_box, radius=clip_radius, fill=255)
    layer_alpha = layer.split()[-1]
    clipped_alpha = ImageChops.multiply(layer_alpha, clip_mask)
    layer.putalpha(clipped_alpha)
    image.alpha_composite(layer)


def draw_reward_pill(
    image: Image.Image,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    color: Color,
    icon: Image.Image | None = None,
) -> None:
    if not draw_ai_box(
        image,
        box,
        (9, 8, 16, 222),
        rgba(color, 210),
        PIXEL_FRAME_BADGE,
        cut=11,
        texture_alpha=12,
        tint_strength=0.36,
    ):
        draw_panel(image, box, fill=(9, 8, 16, 222), border=color, radius=11, glow=False)
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"
    x = box[0] + 18
    if icon:
        icon = _resize_icon(icon, (42, 42), pixel=True)
        image.alpha_composite(icon, (x, box[1] + (box[3] - box[1] - 42) // 2))
        x += 52
    text_box = (x, box[1] + 8, box[2] - 16, box[3] - 8)
    draw_text_fit(
        draw,
        label.upper(),
        (text_box[0], text_box[1], text_box[2], text_box[1] + 24),
        get_font(18),
        TEXT_MUTED,
        min_size=11,
    )
    draw_text_fit(
        draw,
        str(value),
        (text_box[0], text_box[1] + 25, text_box[2], text_box[3]),
        get_font(28, bold=True),
        color,
        min_size=14,
        bold=True,
    )
