"""Normalize Abyssia master icons and export Discord emoji PNGs."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPTS_PATH = ROOT_DIR / "data" / "icon_prompts.json"
MANIFEST_PATH = ROOT_DIR / "data" / "icon_manifest.json"
MASTER_SIZE = 512
EMOJI_SIZE = 128
PREVIEW_SIZE = 64


def _load_records() -> list[dict[str, Any]]:
    if PROMPTS_PATH.exists():
        payload = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
        records = payload.get("records", []) if isinstance(payload, dict) else []
        return [item for item in records if isinstance(item, dict)]
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_icon_prompts import all_records

    return all_records()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _looks_like_pixel_art(image: Image.Image) -> bool:
    probe = image.convert("RGBA")
    max_edge = max(probe.size)
    if max_edge <= 128:
        return True
    small = probe.resize((96, 96), Image.Resampling.NEAREST)
    colors = small.getcolors(maxcolors=4096)
    return bool(colors is not None and len(colors) <= 192)


def _resampling(image: Image.Image, mode: str) -> Image.Resampling:
    if mode == "pixel":
        return Image.Resampling.NEAREST
    if mode == "smooth":
        return Image.Resampling.LANCZOS
    return Image.Resampling.NEAREST if _looks_like_pixel_art(image) else Image.Resampling.LANCZOS


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    return image.getchannel("A").getbbox()


def normalize_icon(image: Image.Image, size: int, *, mode: str, trim: bool = True, fit_ratio: float = 0.875) -> Image.Image:
    source = image.convert("RGBA")
    bbox = _alpha_bbox(source) if trim else None
    if bbox:
        source = source.crop(bbox)

    if not source.getbbox():
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))

    fit = max(1, int(size * fit_ratio))
    resample = _resampling(source, mode)
    source.thumbnail((fit, fit), resample)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - source.width) // 2
    y = (size - source.height) // 2
    canvas.alpha_composite(source, (x, y))
    return canvas


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)


def validate_png(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        if opened.format != "PNG":
            raise ValueError("not a PNG file")
        opened.load()
        return opened.convert("RGBA")


def process_record(
    record: dict[str, Any],
    *,
    source_root: Path,
    emoji_root: Path,
    mode: str,
    write_masters: bool,
    write_preview: bool,
    write_data_assets: bool,
) -> dict[str, Any]:
    key = str(record["key"])
    category = str(record["category"])
    master_path = source_root / category / f"{key}.png"
    emoji_path = emoji_root / category / f"{key}.png"
    preview_path = emoji_root / category / "64" / f"{key}.png"
    data_asset_path = ROOT_DIR / "data" / "assets" / category / f"{key}.png"

    entry: dict[str, Any] = {
        "key": key,
        "display_name": record.get("display_name", key),
        "category": category,
        "emoji_name": record.get("emoji_name"),
        "master_path": master_path.relative_to(ROOT_DIR).as_posix(),
        "emoji_path": emoji_path.relative_to(ROOT_DIR).as_posix(),
        "preview_path": preview_path.relative_to(ROOT_DIR).as_posix() if write_preview else "",
        "data_asset_path": data_asset_path.relative_to(ROOT_DIR).as_posix() if write_data_assets else "",
        "status": "missing_master",
    }

    if not master_path.exists():
        return entry

    source = validate_png(master_path)
    compact_category = category in {"weapons", "passives"}
    master = normalize_icon(source, MASTER_SIZE, mode=mode, fit_ratio=0.96 if compact_category else 0.94)
    if write_masters:
        save_png(master, master_path)
        source_for_emoji = master
    else:
        source_for_emoji = master

    emoji = normalize_icon(source_for_emoji, EMOJI_SIZE, mode=mode, fit_ratio=0.92 if compact_category else 0.94)
    save_png(emoji, emoji_path)
    if write_data_assets:
        save_png(emoji, data_asset_path)

    if write_preview:
        preview = normalize_icon(source_for_emoji, PREVIEW_SIZE, mode=mode, fit_ratio=0.80 if compact_category else 0.875)
        save_png(preview, preview_path)

    entry.update(
        {
            "status": "processed",
            "master_size": list(master.size),
            "emoji_size": list(emoji.size),
            "master_sha256": _sha256(master_path),
            "emoji_sha256": _sha256(emoji_path),
        }
    )
    if write_data_assets:
        entry["data_asset_sha256"] = _sha256(data_asset_path)
    if write_preview:
        entry["preview_sha256"] = _sha256(preview_path)
    return entry


def write_manifest(entries: list[dict[str, Any]]) -> None:
    payload = {
        "version": 1,
        "master_size": MASTER_SIZE,
        "emoji_size": EMOJI_SIZE,
        "preview_size": PREVIEW_SIZE,
        "entries": entries,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT_DIR / "assets" / "icons")
    parser.add_argument("--emoji-root", type=Path, default=ROOT_DIR / "assets" / "emojis")
    parser.add_argument("--mode", choices=("auto", "pixel", "smooth"), default="auto")
    parser.add_argument("--no-write-normalized-masters", action="store_true")
    parser.add_argument("--no-data-assets", action="store_true", help="Do not mirror processed weapon/passive emojis into data/assets.")
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--fail-on-missing", action="store_true")
    args = parser.parse_args()

    records = _load_records()
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    missing: list[str] = []

    for record in records:
        try:
            entry = process_record(
                record,
                source_root=args.source_root,
                emoji_root=args.emoji_root,
                mode=args.mode,
                write_masters=not args.no_write_normalized_masters,
                write_preview=not args.no_preview,
                write_data_assets=not args.no_data_assets,
            )
            entries.append(entry)
            if entry["status"] == "missing_master":
                missing.append(f"{entry['category']}/{entry['key']}")
                print(f"MISSING master: {entry['master_path']}")
            else:
                print(f"Processed: {entry['emoji_path']}")
        except Exception as exc:
            label = f"{record.get('category', '?')}/{record.get('key', '?')}"
            errors.append(f"{label}: {exc}")
            print(f"ERROR {label}: {exc}")

    write_manifest(entries)
    print(f"Wrote {MANIFEST_PATH.relative_to(ROOT_DIR)}")
    print(f"Processed {sum(1 for item in entries if item['status'] == 'processed')} of {len(entries)} icons")
    if missing:
        print(f"Missing masters: {len(missing)}")
    if errors:
        print(f"Errors: {len(errors)}")
    if errors or (args.fail_on_missing and missing):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
