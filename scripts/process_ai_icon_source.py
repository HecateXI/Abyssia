"""Process AI-generated weapon/passive icon sources into Abyssia icon masters."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "tmp" / "imagegen" / "icons_ai" / "raw"
MASTER_DIR = ROOT_DIR / "assets" / "icons"
MASTER_SIZE = 512
PIXEL_CANVAS = 128
FIT_RATIO = 0.90


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def border_key_color(image: Image.Image) -> tuple[int, int, int]:
    rgba = image.convert("RGBA")
    samples: list[tuple[int, int, int]] = []
    width, height = rgba.size
    step = max(1, min(width, height) // 32)
    for x in range(0, width, step):
        samples.append(rgba.getpixel((x, 0))[:3])
        samples.append(rgba.getpixel((x, height - 1))[:3])
    for y in range(0, height, step):
        samples.append(rgba.getpixel((0, y))[:3])
        samples.append(rgba.getpixel((width - 1, y))[:3])
    if not samples:
        return rgba.getpixel((0, 0))[:3]
    channels = []
    for index in range(3):
        ordered = sorted(sample[index] for sample in samples)
        channels.append(ordered[len(ordered) // 2])
    return tuple(channels)  # type: ignore[return-value]


def chroma_cut(image: Image.Image, *, threshold: int = 150, spill_threshold: int = 265) -> Image.Image:
    rgba = image.convert("RGBA")
    key = border_key_color(rgba)
    key_channel = max(range(3), key=lambda index: key[index])
    high_key_channels = [index for index, value in enumerate(key) if value > 200]
    low_key_channels = [index for index, value in enumerate(key) if value < 90]
    single_channel_key = len(high_key_channels) == 1
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            rgb = (r, g, b)
            distance = color_distance(rgb, key)
            key_dominates = single_channel_key and key[key_channel] > 220 and rgb[key_channel] > 160
            multi_channel_key_match = (
                not single_channel_key
                and all(rgb[index] > 145 for index in high_key_channels)
                and all(rgb[index] < 130 for index in low_key_channels)
            )
            if distance <= threshold or (key_dominates and distance <= spill_threshold) or (
                multi_channel_key_match and distance <= spill_threshold
            ):
                pixels[x, y] = (0, 0, 0, 0)
            elif key_dominates and distance <= spill_threshold + 90:
                channels = [r, g, b]
                channels[key_channel] = min(channels[key_channel], max(channels[(key_channel + 1) % 3], channels[(key_channel + 2) % 3]) + 24)
                pixels[x, y] = (channels[0], channels[1], channels[2], a)
            elif multi_channel_key_match and distance <= spill_threshold + 90:
                channels = [r, g, b]
                for index in high_key_channels:
                    channels[index] = min(channels[index], max(channels[low] for low in low_key_channels) + 48)
                pixels[x, y] = (channels[0], channels[1], channels[2], a)
    return rgba


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.convert("RGBA").getchannel("A").getbbox()


def remove_tiny_alpha_components(image: Image.Image, *, min_component_area: int = 96) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    width, height = rgba.size
    seen = bytearray(width * height)
    keep = bytearray(width * height)
    pixels = alpha.load()
    components: list[list[int]] = []

    for y in range(height):
        row_offset = y * width
        for x in range(width):
            index = row_offset + x
            if seen[index] or pixels[x, y] <= 0:
                continue
            stack = [(x, y)]
            seen[index] = 1
            component: list[int] = []
            while stack:
                cx, cy = stack.pop()
                cindex = cy * width + cx
                component.append(cindex)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    nindex = ny * width + nx
                    if seen[nindex] or pixels[nx, ny] <= 0:
                        continue
                    seen[nindex] = 1
                    stack.append((nx, ny))
            components.append(component)

    if not components:
        return rgba

    largest = max(len(component) for component in components)
    cutoff = max(min_component_area, int(largest * 0.002))
    for component in components:
        if len(component) >= cutoff:
            for index in component:
                keep[index] = 1

    data = rgba.load()
    for y in range(height):
        for x in range(width):
            if not keep[y * width + x]:
                data[x, y] = (0, 0, 0, 0)
    return rgba


def normalize_master(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    bbox = alpha_bbox(rgba)
    if bbox:
        pad = max(8, max(bbox[2] - bbox[0], bbox[3] - bbox[1]) // 16)
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(rgba.width, bbox[2] + pad)
        bottom = min(rgba.height, bbox[3] + pad)
        rgba = rgba.crop((left, top, right, bottom))

    side = max(rgba.width, rgba.height)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.alpha_composite(rgba, ((side - rgba.width) // 2, (side - rgba.height) // 2))

    fit = max(1, int(PIXEL_CANVAS * FIT_RATIO))
    square.thumbnail((fit, fit), Image.Resampling.LANCZOS)
    pixel = Image.new("RGBA", (PIXEL_CANVAS, PIXEL_CANVAS), (0, 0, 0, 0))
    pixel.alpha_composite(square, ((PIXEL_CANVAS - square.width) // 2, (PIXEL_CANVAS - square.height) // 2))

    alpha = pixel.getchannel("A")
    quantized = pixel.convert("RGB").quantize(colors=48, method=Image.Quantize.FASTOCTREE).convert("RGBA")
    quantized.putalpha(alpha)
    return quantized.resize((MASTER_SIZE, MASTER_SIZE), Image.Resampling.NEAREST)


def process_source(source: Path, category: str, key: str) -> Path:
    if category not in {"weapons", "passives"}:
        raise ValueError("category must be weapons or passives")
    if not source.exists():
        raise FileNotFoundError(source)

    raw_path = RAW_DIR / category / f"{key}_source{source.suffix.lower() or '.png'}"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, raw_path)

    master = normalize_master(remove_tiny_alpha_components(chroma_cut(Image.open(source))))
    out = MASTER_DIR / category / f"{key}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    master.save(out, "PNG", optimize=True)
    print(f"{category}/{key}: {source} -> {out}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--category", choices=("weapons", "passives"), required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()
    process_source(args.source, args.category, args.key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
