from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def chroma_cut(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    key = pixels[0, 0][:3]
    max_channel = max(range(3), key=lambda idx: key[idx])
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            distance = color_distance((r, g, b), key)
            key_like = distance < 150
            dominant_key_spill = (
                key[max_channel] > 220
                and (r, g, b)[max_channel] > 170
                and distance < 260
            )
            if key_like or dominant_key_spill:
                pixels[x, y] = (0, 0, 0, 0)
            elif distance < 330:
                channels = [r, g, b]
                channels[max_channel] = min(channels[max_channel], 92)
                pixels[x, y] = (*channels, a)
    return rgba


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return (0, 0, image.width, image.height)
    return bbox


def process_sprite(source: Path, out: Path, sprite_size: int, output_size: int, colors: int) -> None:
    image = chroma_cut(Image.open(source))
    left, top, right, bottom = alpha_bbox(image)
    pad = max(right - left, bottom - top) // 12
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(image.width, right + pad)
    bottom = min(image.height, bottom + pad)
    cropped = image.crop((left, top, right, bottom))

    side = max(cropped.width, cropped.height)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.alpha_composite(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2))

    core_size = max(8, int(sprite_size * 0.86))
    core = square.resize((core_size, core_size), Image.Resampling.NEAREST)
    sprite = Image.new("RGBA", (sprite_size, sprite_size), (0, 0, 0, 0))
    sprite.alpha_composite(core, ((sprite_size - core_size) // 2, (sprite_size - core_size) // 2))
    alpha = sprite.getchannel("A")
    quantized = sprite.convert("RGB").quantize(colors=colors, method=Image.Quantize.FASTOCTREE).convert("RGBA")
    quantized.putalpha(alpha)

    final = quantized.resize((output_size, output_size), Image.Resampling.NEAREST)
    out.parent.mkdir(parents=True, exist_ok=True)
    final.save(out)


def make_contact_sheet(paths: list[Path], labels: list[str], out: Path) -> None:
    cell_w, cell_h = 210, 250
    columns = min(5, len(paths))
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell_w, rows * cell_h), (18, 16, 25, 255))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for row in range(rows):
        for col in range(columns):
            idx = row * columns + col
            if idx >= len(paths):
                break
            x0 = col * cell_w
            y0 = row * cell_h
            for yy in range(y0, y0 + cell_h, 20):
                for xx in range(x0, x0 + cell_w, 20):
                    if ((xx - x0) // 20 + (yy - y0) // 20) % 2 == 0:
                        draw.rectangle((xx, yy, xx + 19, yy + 19), fill=(24, 22, 34, 255))
            sprite = Image.open(paths[idx]).convert("RGBA")
            preview = sprite.resize((128, 128), Image.Resampling.NEAREST)
            tiny = sprite.resize((56, 56), Image.Resampling.NEAREST)
            emoji = sprite.resize((36, 36), Image.Resampling.NEAREST)
            sheet.alpha_composite(preview, (x0 + 16, y0 + 18))
            sheet.alpha_composite(tiny, (x0 + 148, y0 + 42))
            sheet.alpha_composite(emoji, (x0 + 158, y0 + 112))
            draw.text((x0 + 12, y0 + 206), labels[idx], fill=(238, 233, 222, 255), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def latest_generated(root: Path, count: int) -> list[Path]:
    files = [p for p in root.rglob("*.png") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime)
    if len(files) < count:
        raise RuntimeError(f"Only found {len(files)} generated PNG(s), need {count}.")
    return files[-count:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keys", nargs="+", required=True)
    parser.add_argument("--manifest", default="tmp/imagegen/creature_pixel_manifest.json")
    parser.add_argument("--generated-root", default=str(Path.home() / ".codex" / "generated_images"))
    parser.add_argument("--raw-dir", default="tmp/imagegen/creatures_ai/raw")
    parser.add_argument("--out-dir", default="data/assets/creatures")
    parser.add_argument("--proof", default="")
    parser.add_argument("--sprite-size", type=int, default=112)
    parser.add_argument("--output-size", type=int, default=256)
    parser.add_argument("--colors", type=int, default=22)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    names_by_key = {row["key"]: row["name"] for row in manifest}
    sources = latest_generated(Path(args.generated_root), len(args.keys))

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    labels: list[str] = []

    for key, source in zip(args.keys, sources):
        raw_path = raw_dir / f"{key}_source.png"
        shutil.copy2(source, raw_path)
        output = out_dir / f"{key}.png"
        process_sprite(raw_path, output, args.sprite_size, args.output_size, args.colors)
        outputs.append(output)
        labels.append(key)
        print(f"{key}: {names_by_key.get(key, key)} -> {output}")

    if args.proof:
        make_contact_sheet(outputs, labels, Path(args.proof))
        print(f"proof -> {args.proof}")


if __name__ == "__main__":
    main()
