from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "assets" / "bosses"
SIZE = 256


def rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        alpha,
    )


def glow(base: Image.Image, color: tuple[int, int, int, int], box: tuple[int, int, int, int], blur: int) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(box, fill=color)
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def soft_poly(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill, outline=None, width: int = 1) -> None:
    draw.polygon(points, fill=fill)
    if outline:
        draw.line(points + [points[0]], fill=outline, width=width, joint="curve")


def save(name: str, image: Image.Image) -> None:
    image = image.filter(ImageFilter.UnsharpMask(radius=1.1, percent=105, threshold=3))
    image.save(OUT / f"{name}.png")


def hollow_king() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    glow(img, rgba("b9d8ff", 80), (20, 12, 236, 246), 22)
    glow(img, rgba("ffffff", 42), (58, 38, 198, 226), 24)
    for off, alpha in ((10, 70), (18, 42), (26, 26)):
        d.arc((42 - off, 38 - off, 214 + off, 232 + off), 198, 342, fill=rgba("dcecff", alpha), width=3)
    d.polygon([(64, 70), (88, 40), (116, 58), (128, 28), (140, 58), (168, 40), (192, 70), (178, 88), (76, 88)],
              fill=rgba("c5a653"), outline=rgba("fff1a4"))
    for x, h in ((76, 42), (104, 34), (128, 20), (152, 34), (180, 42)):
        d.polygon([(x - 10, 72), (x, h), (x + 10, 72)], fill=rgba("f2d36b"), outline=rgba("fff7be"))
    d.polygon([(72, 78), (98, 64), (128, 72), (158, 64), (184, 78), (176, 180), (146, 216), (110, 216), (80, 180)],
              fill=rgba("d7e4ee"), outline=rgba("eff8ff"))
    d.polygon([(80, 64), (96, 104), (64, 118), (48, 72)], fill=rgba("96adc2"), outline=rgba("edf7ff"))
    d.polygon([(176, 64), (160, 104), (192, 118), (208, 72)], fill=rgba("96adc2"), outline=rgba("edf7ff"))
    d.polygon([(78, 130), (42, 154), (58, 190), (86, 166)], fill=rgba("5f7088", 210), outline=rgba("cfe7ff"))
    d.polygon([(178, 130), (214, 154), (198, 190), (170, 166)], fill=rgba("5f7088", 210), outline=rgba("cfe7ff"))
    soft_poly(
        d,
        [(92, 146), (112, 132), (128, 152), (144, 132), (164, 146), (154, 184), (102, 184)],
        rgba("73869a"),
        rgba("eef8ff"),
        2,
    )
    for x in (94, 140):
        d.ellipse((x, 104, x + 28, 132), fill=rgba("121725"))
        d.ellipse((x + 10, 114, x + 18, 122), fill=rgba("ffe670"))
    d.polygon([(128, 126), (116, 154), (140, 154)], fill=rgba("6e8194"), outline=rgba("eff8ff"))
    for x in range(96, 164, 14):
        d.rounded_rectangle((x, 166, x + 8, 190), radius=2, fill=rgba("121725"), outline=rgba("d7e4ee", 120))
    for x in (88, 108, 148, 168):
        d.line((x, 88, x - 12, 126), fill=rgba("ffffff", 70), width=2)
    d.arc((68, 54, 188, 214), 205, 335, fill=rgba("6f879f", 230), width=8)
    d.line((92, 206, 164, 206), fill=rgba("f2f8ff", 220), width=4)
    return img


def mother_of_rot() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    glow(img, rgba("45ff89", 86), (18, 14, 238, 244), 24)
    glow(img, rgba("bb3043", 52), (72, 20, 220, 134), 18)
    body = [(54, 112), (68, 82), (98, 76), (126, 92), (156, 76), (190, 92), (204, 128),
            (196, 176), (166, 220), (118, 232), (74, 208), (48, 166)]
    soft_poly(d, body, rgba("173e28"), rgba("8cff9d"), 4)
    d.polygon([(58, 126), (92, 108), (126, 122), (164, 106), (198, 128), (188, 164), (72, 170)],
              fill=rgba("254b32", 210), outline=rgba("6eff8f", 125))
    cap = [(76, 70), (98, 34), (134, 28), (172, 36), (210, 66), (196, 108), (154, 104), (122, 116), (80, 106)]
    soft_poly(d, cap, rgba("a62238"), rgba("ff8b89"), 4)
    for box, col in [((82, 44, 130, 94), "d8ed9c"), ((138, 46, 194, 94), "f7d8ad"), ((112, 62, 160, 116), "84304f")]:
        d.ellipse(box, fill=rgba(col, 205), outline=rgba("fff4c4", 190), width=2)
    for x, y, r in ((98, 130, 14), (144, 122, 10), (166, 138, 13), (116, 158, 8)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=rgba("08120d"), outline=rgba("b2ff81", 150), width=2)
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=rgba("b2ff81"))
    for idx, x in enumerate((62, 78, 184, 200)):
        bend = -32 if x < 128 else 32
        d.line((x, 160, x + bend, 206), fill=rgba("35d56f"), width=7)
        d.line((x + 8, 162, x + bend + (12 if x < 128 else -12), 214), fill=rgba("85ffa2", 160), width=3)
        d.ellipse((x + bend - 14, 198, x + bend + 16, 226), fill=rgba("6cff90"), outline=rgba("0d3d22"))
    d.arc((82, 142, 172, 204), 22, 158, fill=rgba("08120d"), width=8)
    for x, y in ((92, 58), (154, 62), (180, 78), (108, 92), (138, 82), (190, 96)):
        d.ellipse((x, y, x + 7, y + 7), fill=rgba("fff2c4", 210))
    return img


def void_leviathan() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    glow(img, rgba("4aa8ff", 92), (14, 12, 242, 244), 20)
    for off, width, color in ((0, 28, "4fd8ff"), (18, 18, "11345d"), (34, 9, "8ff6ff")):
        d.arc((24 + off, 44 + off, 232 - off, 254 - off), 194, 505, fill=rgba(color), width=width)
    for i in range(6):
        x = 54 + i * 24
        d.polygon([(x, 184 - i * 7), (x + 18, 170 - i * 4), (x + 8, 202 - i * 6)], fill=rgba("77efff", 150))
    soft_poly(
        d,
        [(78, 96), (124, 42), (178, 54), (214, 100), (200, 150), (150, 178), (88, 154), (62, 124)],
        rgba("1c5f9b"),
        rgba("a8f3ff"),
        4,
    )
    d.polygon([(78, 108), (34, 72), (66, 136)], fill=rgba("26b9e8"), outline=rgba("9ef4ff"))
    d.polygon([(170, 64), (222, 28), (194, 100)], fill=rgba("2ac7f0"), outline=rgba("9ef4ff"))
    d.polygon([(186, 118), (232, 124), (198, 150)], fill=rgba("11345d"), outline=rgba("9ef4ff"))
    for x, y in ((108, 98), (156, 92), (184, 118)):
        d.ellipse((x, y, x + 24, y + 24), fill=rgba("071525"), outline=rgba("78f5ff", 130), width=2)
        d.ellipse((x + 8, y + 8, x + 15, y + 15), fill=rgba("bffcff"))
    d.line((104, 140, 178, 130), fill=rgba("03101c"), width=8)
    for x in (112, 132, 152, 172):
        d.polygon([(x, 135), (x + 9, 134), (x + 5, 158)], fill=rgba("e9fbff"))
    for x1, y1, x2, y2 in ((84, 166, 52, 220), (148, 176, 138, 232), (174, 166, 210, 220)):
        d.line((x1, y1, x2, y2), fill=rgba("58dfff"), width=8)
        d.line((x1 + 4, y1, x2 + 4, y2), fill=rgba("d7ffff", 100), width=2)
    return img


def nameless_god() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    glow(img, rgba("ffd24c", 105), (14, 12, 242, 244), 26)
    glow(img, rgba("8f55ff", 54), (44, 38, 212, 218), 24)
    for r, a in ((108, 78), (88, 96), (66, 130), (42, 155)):
        d.ellipse((128 - r, 128 - r, 128 + r, 128 + r), outline=rgba("ffe58a", a), width=4)
    for i in range(12):
        angle = i * 30
        x = 128 + int((78 + (i % 2) * 18) * math.cos(math.radians(angle)))
        y = 128 + int((78 + (i % 2) * 18) * math.sin(math.radians(angle)))
        d.line((128, 128, x, y), fill=rgba("ffe58a", 72 if i % 2 else 110), width=3 if i % 2 else 4)
    soft_poly(
        d,
        [(128, 34), (176, 62), (208, 112), (192, 168), (156, 220), (100, 220), (64, 168), (48, 112), (80, 62)],
        rgba("43225f"),
        rgba("ffe58a"),
        5,
    )
    for x, y in ((76, 96), (172, 96), (86, 172), (166, 172)):
        d.polygon([(x, y - 14), (x + 14, y), (x, y + 14), (x - 14, y)], fill=rgba("ffe58a", 120), outline=rgba("fff7cf"))
    d.ellipse((74, 92, 182, 160), fill=rgba("0d0d18"), outline=rgba("fff1a4"), width=5)
    d.ellipse((98, 104, 158, 150), fill=rgba("ffd84f"), outline=rgba("fff7cf"), width=2)
    d.ellipse((118, 112, 140, 144), fill=rgba("06060a"))
    d.ellipse((126, 120, 134, 130), fill=rgba("fff7cf"))
    d.arc((82, 154, 174, 204), 194, 346, fill=rgba("0f0a18"), width=9)
    for x in (96, 114, 132, 150):
        d.line((x, 166, x + 8, 192), fill=rgba("ffe58a"), width=4)
    for i in range(8):
        angle = i * math.tau / 8
        x = 128 + math.cos(angle) * 58
        y = 130 + math.sin(angle) * 44
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=rgba("fff7cf", 190))
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    save("hollow_king", hollow_king())
    save("mother_of_rot", mother_of_rot())
    save("void_leviathan", void_leviathan())
    save("nameless_god", nameless_god())
    print(f"Wrote boss assets to {OUT}")


if __name__ == "__main__":
    main()
