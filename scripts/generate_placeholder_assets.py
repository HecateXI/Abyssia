from __future__ import annotations

import hashlib
import struct
import sys
import zlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from core.content_config import ASSET_DIR, load_config, save_config, safe_key
from core.rpg_data import BOSSES, CREATURES, EQUIPMENT, MATERIALS, ZONES, normalize_key


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SIZE = 256


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def color_for(value: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return 70 + digest[0] % 140, 45 + digest[1] % 120, 75 + digest[2] % 130


def write_png(path: Path, label: str, accent: tuple[int, int, int]) -> None:
    bg = (18, 15, 20)
    line = (48, 36, 54)
    pixels = bytearray()
    for y in range(SIZE):
        pixels.append(0)
        for x in range(SIZE):
            cx = abs(x - SIZE // 2)
            cy = abs(y - SIZE // 2)
            if 42 < cx + cy < 96:
                color = accent
            elif (x // 16 + y // 16) % 2 == 0:
                color = line
            else:
                color = bg
            pixels.extend(color)

    raw = zlib.compress(bytes(pixels), level=9)
    png = (
        PNG_SIGNATURE
        + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
        + chunk(b"tEXt", f"Title\0{label}".encode("latin-1", "replace"))
        + chunk(b"IDAT", raw)
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def entries() -> dict[str, dict[str, str]]:
    return {
        "creatures": {normalize_key(creature.name): creature.name for creature in CREATURES},
        "equipment": {key: item.name for key, item in EQUIPMENT.items()},
        "materials": dict(MATERIALS),
        "zones": {key: zone.name for key, zone in ZONES.items()},
        "bosses": {boss.key: boss.name for boss in BOSSES},
    }


def main() -> None:
    config = load_config()
    for kind, values in entries().items():
        for key, label in values.items():
            safe = safe_key(key)
            path = ASSET_DIR / kind / f"{safe}.png"
            if not path.exists():
                write_png(path, label, color_for(f"{kind}:{key}"))
            config["assets"][kind].setdefault(safe, {"file": f"{kind}/{safe}.png", "placeholder": True})
    save_config(config)
    print(f"Generated placeholder assets in {ASSET_DIR}")


if __name__ == "__main__":
    main()
