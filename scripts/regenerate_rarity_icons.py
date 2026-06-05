"""
Regenerate Rarity Icons - Dark Fantasy Themed 32x32 Pixel Art
=============================================================
Generates 10 stunning rarity letter icons with dramatic effects:
glowing auras, inner gradients, sparkle particles, and bold lettering.
"""

import math
import random
import os
from PIL import Image, ImageDraw

# ── Output directory ──────────────────────────────────────────────────────────
OUTPUT_DIR = r"c:\Users\HomeAdmin\Downloads\bot\data\assets\rarity"
os.makedirs(OUTPUT_DIR, exist_ok=True)

random.seed(42)  # reproducible sparkle positions

# ── Thick Blocky Pixel Font (each letter on a ~12-wide x 16-tall grid) ────────
# 1 = filled, 0 = empty.  These are chunky, bold letterforms.

FONT = {
    "C": [
        [0,0,1,1,1,1,1,1,1,1,0,0],
        [0,1,1,1,1,1,1,1,1,1,1,0],
        [1,1,1,1,0,0,0,0,1,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,1,0,0,0,0,0,1,1,1],
        [1,1,1,1,0,0,0,0,1,1,1,1],
        [0,1,1,1,1,1,1,1,1,1,1,0],
        [0,0,1,1,1,1,1,1,1,1,0,0],
    ],
    "U": [
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,1,0,0,0,0,1,1,1,1],
        [0,1,1,1,1,0,0,1,1,1,1,0],
        [0,0,1,1,1,1,1,1,1,1,0,0],
        [0,0,0,1,1,1,1,1,1,0,0,0],
    ],
    "R": [
        [1,1,1,1,1,1,1,1,1,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,0,0],
        [1,1,1,0,0,0,0,1,1,1,1,0],
        [1,1,1,0,0,0,0,0,1,1,1,0],
        [1,1,1,0,0,0,0,0,1,1,1,0],
        [1,1,1,0,0,0,0,1,1,1,1,0],
        [1,1,1,1,1,1,1,1,1,1,0,0],
        [1,1,1,1,1,1,1,1,1,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,0,0],
        [1,1,1,0,0,0,0,1,1,1,0,0],
        [1,1,1,0,0,0,0,0,1,1,1,0],
        [1,1,1,0,0,0,0,0,1,1,1,0],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
    ],
    "E": [
        [1,1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,0,0],
        [1,1,1,1,1,1,1,1,1,1,0,0],
        [1,1,1,1,1,1,1,1,1,1,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1,1],
    ],
    "L": [
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1,1],
    ],
    "M": [
        [1,1,0,0,0,0,0,0,0,0,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,1,0,0,0,0,1,1,1,1],
        [1,1,1,1,1,0,0,1,1,1,1,1],
        [1,1,0,1,1,1,1,1,1,0,1,1],
        [1,1,0,0,1,1,1,1,0,0,1,1],
        [1,1,0,0,0,1,1,0,0,0,1,1],
        [1,1,0,0,0,0,0,0,0,0,1,1],
        [1,1,0,0,0,0,0,0,0,0,1,1],
        [1,1,0,0,0,0,0,0,0,0,1,1],
        [1,1,0,0,0,0,0,0,0,0,1,1],
        [1,1,0,0,0,0,0,0,0,0,1,1],
        [1,1,0,0,0,0,0,0,0,0,1,1],
        [1,1,0,0,0,0,0,0,0,0,1,1],
        [1,1,0,0,0,0,0,0,0,0,1,1],
        [1,1,0,0,0,0,0,0,0,0,1,1],
    ],
    "A": [
        [0,0,0,0,1,1,1,1,0,0,0,0],
        [0,0,0,1,1,1,1,1,1,0,0,0],
        [0,0,1,1,1,0,0,1,1,1,0,0],
        [0,1,1,1,0,0,0,0,1,1,1,0],
        [0,1,1,1,0,0,0,0,1,1,1,0],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
    ],
    "D": [
        [1,1,1,1,1,1,1,1,0,0,0,0],
        [1,1,1,1,1,1,1,1,1,0,0,0],
        [1,1,1,0,0,0,1,1,1,1,0,0],
        [1,1,1,0,0,0,0,0,1,1,1,0],
        [1,1,1,0,0,0,0,0,1,1,1,0],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,0,1,1,1],
        [1,1,1,0,0,0,0,0,1,1,1,0],
        [1,1,1,0,0,0,0,0,1,1,1,0],
        [1,1,1,0,0,0,1,1,1,1,0,0],
        [1,1,1,1,1,1,1,1,1,0,0,0],
        [1,1,1,1,1,1,1,1,0,0,0,0],
    ],
}


# ── Helper: get letter pixel positions (scaled onto 32×32 canvas) ─────────────
def get_letter_pixels(letter_grid):
    """Return set of (x, y) pixel coords for the letter on a 32×32 canvas."""
    rows = len(letter_grid)
    cols = len(letter_grid[0])
    # Center the letter on the canvas with some padding
    # Scale: each grid cell → ~1.5-2 px, letter should be ~20 px tall
    scale_y = 20 / rows  # ≈1.25
    scale_x = 20 / cols  # ≈1.67
    scale = min(scale_y, scale_x)
    h_px = int(rows * scale)
    w_px = int(cols * scale)
    off_x = (32 - w_px) // 2
    off_y = (32 - h_px) // 2

    pixels = set()
    for gr in range(rows):
        for gc in range(cols):
            if letter_grid[gr][gc]:
                # map grid cell to pixel coords
                px_start_x = int(gc * scale) + off_x
                px_end_x = int((gc + 1) * scale) + off_x
                px_start_y = int(gr * scale) + off_y
                px_end_y = int((gr + 1) * scale) + off_y
                for py in range(px_start_y, px_end_y):
                    for px in range(px_start_x, px_end_x):
                        if 0 <= px < 32 and 0 <= py < 32:
                            pixels.add((px, py))
    return pixels


def get_outline_pixels(letter_pixels, radius=1):
    """Get pixels within `radius` of the letter but NOT in the letter itself."""
    outline = set()
    for (x, y) in letter_pixels:
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < 32 and 0 <= ny < 32 and (nx, ny) not in letter_pixels:
                    outline.add((nx, ny))
    return outline


def dist_to_set(x, y, pixel_set):
    """Minimum distance from (x,y) to any pixel in the set."""
    min_d = 999
    for (px, py) in pixel_set:
        d = math.sqrt((x - px) ** 2 + (y - py) ** 2)
        if d < min_d:
            min_d = d
    return min_d


def lerp_color(c1, c2, t):
    """Linear interpolate between two RGB tuples."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ── Core rendering function ──────────────────────────────────────────────────
def render_icon(
    letter_key,        # key into FONT dict
    filename,          # output filename
    color_top,         # RGB tuple – top of gradient on letter
    color_bottom,      # RGB tuple – bottom of gradient on letter
    glow_color,        # RGB tuple – glow / aura color
    outline_color,     # RGB tuple – dark outline
    sparkle_color,     # RGB tuple – sparkle dots
    glow_radius=3,     # how far the glow extends
    glow_intensity=180,# max alpha of glow at letter edge
    num_sparkles=4,    # number of sparkle particles
    highlight_color=None,  # optional bright highlight on letter top
    inner_shadow=True,     # darken bottom of letter
    extra_glow_layers=0,   # additional glow passes for higher rarities
    sparkle_size=1,        # size of sparkle dots
    secondary_glow_color=None,  # second glow color for dual-tone effects
    add_cross_sparkles=False,   # cross-shaped sparkles
):
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    letter_pixels = get_letter_pixels(FONT[letter_key])

    # Bounding box of letter for gradient calculation
    min_y = min(y for _, y in letter_pixels)
    max_y = max(y for _, y in letter_pixels)
    min_x = min(x for x, _ in letter_pixels)
    max_x = max(x for x, _ in letter_pixels)

    # ── Layer 1: Outer glow / aura ────────────────────────────────────────
    for gy in range(32):
        for gx in range(32):
            if (gx, gy) in letter_pixels:
                continue
            d = dist_to_set(gx, gy, letter_pixels)
            if d <= glow_radius:
                t = 1.0 - (d / glow_radius)
                alpha = int(glow_intensity * t * t)  # quadratic falloff
                gc = glow_color
                if secondary_glow_color and (gx + gy) % 3 == 0:
                    gc = secondary_glow_color
                img.putpixel((gx, gy), (*gc, alpha))

    # Extra glow layers for higher rarities (additive-like)
    for layer in range(extra_glow_layers):
        radius = glow_radius + layer + 1
        intensity = max(40, glow_intensity - 50 * (layer + 1))
        for gy in range(32):
            for gx in range(32):
                if (gx, gy) in letter_pixels:
                    continue
                d = dist_to_set(gx, gy, letter_pixels)
                if d <= radius:
                    t = 1.0 - (d / radius)
                    alpha = int(intensity * t * t)
                    existing = img.getpixel((gx, gy))
                    gc = secondary_glow_color if secondary_glow_color and layer % 2 == 1 else glow_color
                    new_alpha = min(255, existing[3] + alpha)
                    # blend color
                    if existing[3] > 0:
                        blend = alpha / max(1, new_alpha)
                        r = int(existing[0] * (1 - blend) + gc[0] * blend)
                        g = int(existing[1] * (1 - blend) + gc[1] * blend)
                        b = int(existing[2] * (1 - blend) + gc[2] * blend)
                        img.putpixel((gx, gy), (r, g, b, new_alpha))
                    else:
                        img.putpixel((gx, gy), (*gc, alpha))

    # ── Layer 2: Dark outline (1 px) ──────────────────────────────────────
    outline_px = get_outline_pixels(letter_pixels, radius=1)
    for (ox, oy) in outline_px:
        existing = img.getpixel((ox, oy))
        # Blend outline on top
        img.putpixel((ox, oy), (*outline_color, 255))

    # ── Layer 3: Letter body with vertical gradient ───────────────────────
    y_range = max(1, max_y - min_y)
    for (lx, ly) in letter_pixels:
        t = (ly - min_y) / y_range
        base_color = lerp_color(color_top, color_bottom, t)

        # Inner shadow – darken bottom-right pixels
        if inner_shadow:
            # Check if pixel is near bottom-right edge of letter
            is_edge_right = (lx + 1, ly) not in letter_pixels
            is_edge_bottom = (lx, ly + 1) not in letter_pixels
            if is_edge_right or is_edge_bottom:
                base_color = lerp_color(base_color, (0, 0, 0), 0.3)

        # Highlight – brighten top-left pixels
        if highlight_color:
            is_edge_left = (lx - 1, ly) not in letter_pixels
            is_edge_top = (lx, ly - 1) not in letter_pixels
            if is_edge_left or is_edge_top:
                base_color = lerp_color(base_color, highlight_color, 0.5)

        img.putpixel((lx, ly), (*base_color, 255))

    # ── Layer 4: Inner bevel / specular highlight ─────────────────────────
    # Add a subtle bright line on the top edge of the letter
    for (lx, ly) in letter_pixels:
        if (lx, ly - 1) not in letter_pixels and (lx, ly - 2) not in letter_pixels:
            # This is a top-edge pixel
            existing = img.getpixel((lx, ly))
            bright = lerp_color(existing[:3], (255, 255, 255), 0.25)
            img.putpixel((lx, ly), (*bright, 255))

    # ── Layer 5: Sparkle particles ────────────────────────────────────────
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    placed_sparkles = 0
    attempts = 0
    sparkle_positions = []

    while placed_sparkles < num_sparkles and attempts < 200:
        attempts += 1
        # Random position biased toward glow area
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(8, 14)
        sx = int(center_x + math.cos(angle) * dist)
        sy = int(center_y + math.sin(angle) * dist)

        if 0 <= sx < 32 and 0 <= sy < 32 and (sx, sy) not in letter_pixels:
            # Check not too close to another sparkle
            too_close = False
            for (px, py) in sparkle_positions:
                if abs(px - sx) < 3 and abs(py - sy) < 3:
                    too_close = True
                    break
            if too_close:
                continue

            sparkle_positions.append((sx, sy))

            if add_cross_sparkles and placed_sparkles % 2 == 0:
                # Cross-shaped sparkle
                img.putpixel((sx, sy), (*sparkle_color, 255))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = sx + dx, sy + dy
                    if 0 <= nx < 32 and 0 <= ny < 32 and (nx, ny) not in letter_pixels:
                        img.putpixel((nx, ny), (*sparkle_color, 140))
            else:
                # Dot sparkle with subtle glow
                img.putpixel((sx, sy), (*sparkle_color, 255))
                if sparkle_size > 1:
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = sx + dx, sy + dy
                            if 0 <= nx < 32 and 0 <= ny < 32 and (nx, ny) not in letter_pixels:
                                existing = img.getpixel((nx, ny))
                                a = max(existing[3], 80)
                                img.putpixel((nx, ny), (*sparkle_color, a))

            placed_sparkles += 1

    # ── Save ──────────────────────────────────────────────────────────────
    path = os.path.join(OUTPUT_DIR, filename)
    img.save(path, "PNG")
    print(f"  ✓ Saved {filename} ({len(letter_pixels)} letter pixels, {placed_sparkles} sparkles)")
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Generate all 10 rarity icons
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("  Regenerating Rarity Icons – Dark Fantasy Theme")
print("=" * 60)

# 1. Common – Slate gray, understated
print("\n[1/10] Common (C) – Slate gray stone")
render_icon(
    letter_key="C",
    filename="common.png",
    color_top=(160, 170, 180),
    color_bottom=(90, 95, 105),
    glow_color=(120, 130, 140),
    outline_color=(30, 30, 35),
    sparkle_color=(200, 210, 220),
    glow_radius=2,
    glow_intensity=80,
    num_sparkles=2,
    highlight_color=(200, 210, 220),
    sparkle_size=1,
)

# 2. Uncommon – Emerald green glow
print("\n[2/10] Uncommon (U) – Emerald green")
render_icon(
    letter_key="U",
    filename="uncommon.png",
    color_top=(80, 230, 120),
    color_bottom=(30, 140, 60),
    glow_color=(50, 200, 80),
    outline_color=(10, 40, 15),
    sparkle_color=(150, 255, 180),
    glow_radius=2,
    glow_intensity=120,
    num_sparkles=3,
    highlight_color=(180, 255, 200),
    sparkle_size=1,
)

# 3. Rare – Vibrant blue with cyan sparkles
print("\n[3/10] Rare (R) – Vibrant blue")
render_icon(
    letter_key="R",
    filename="rare.png",
    color_top=(80, 160, 255),
    color_bottom=(30, 80, 200),
    glow_color=(60, 140, 255),
    outline_color=(10, 20, 60),
    sparkle_color=(130, 220, 255),
    glow_radius=3,
    glow_intensity=140,
    num_sparkles=4,
    highlight_color=(180, 220, 255),
    sparkle_size=1,
    extra_glow_layers=1,
)

# 4. Epic – Rich purple, magenta glow
print("\n[4/10] Epic (E) – Rich purple")
render_icon(
    letter_key="E",
    filename="epic.png",
    color_top=(190, 80, 255),
    color_bottom=(120, 30, 180),
    glow_color=(180, 60, 255),
    outline_color=(40, 10, 60),
    sparkle_color=(230, 160, 255),
    glow_radius=3,
    glow_intensity=150,
    num_sparkles=4,
    highlight_color=(230, 180, 255),
    sparkle_size=1,
    extra_glow_layers=1,
    secondary_glow_color=(255, 80, 200),
)

# 5. Legendary – Brilliant gold with warm glow
print("\n[5/10] Legendary (L) – Brilliant gold")
render_icon(
    letter_key="L",
    filename="legendary.png",
    color_top=(255, 230, 80),
    color_bottom=(200, 150, 30),
    glow_color=(255, 200, 50),
    outline_color=(60, 40, 5),
    sparkle_color=(255, 255, 180),
    glow_radius=3,
    glow_intensity=160,
    num_sparkles=5,
    highlight_color=(255, 250, 200),
    sparkle_size=1,
    extra_glow_layers=1,
    add_cross_sparkles=True,
)

# 6. Mythic – Fiery crimson red with orange flame glow
print("\n[6/10] Mythic (M) – Fiery crimson")
render_icon(
    letter_key="M",
    filename="mythic.png",
    color_top=(255, 100, 40),
    color_bottom=(180, 20, 20),
    glow_color=(255, 60, 20),
    outline_color=(50, 5, 5),
    sparkle_color=(255, 200, 80),
    glow_radius=3,
    glow_intensity=170,
    num_sparkles=5,
    highlight_color=(255, 180, 100),
    sparkle_size=2,
    extra_glow_layers=2,
    secondary_glow_color=(255, 140, 30),
    add_cross_sparkles=True,
)

# 7. Ancient – Burnt orange with ancient rune glow
print("\n[7/10] Ancient (A) – Burnt orange rune")
render_icon(
    letter_key="A",
    filename="ancient.png",
    color_top=(230, 160, 60),
    color_bottom=(160, 80, 20),
    glow_color=(200, 120, 30),
    outline_color=(40, 20, 5),
    sparkle_color=(255, 200, 100),
    glow_radius=3,
    glow_intensity=160,
    num_sparkles=5,
    highlight_color=(255, 220, 150),
    sparkle_size=2,
    extra_glow_layers=2,
    secondary_glow_color=(180, 80, 10),
    add_cross_sparkles=True,
)

# 8. Divine – Radiant white/gold celestial halo
print("\n[8/10] Divine (D) – Celestial white-gold")
render_icon(
    letter_key="D",
    filename="divine.png",
    color_top=(255, 255, 240),
    color_bottom=(230, 210, 140),
    glow_color=(255, 240, 180),
    outline_color=(80, 70, 30),
    sparkle_color=(255, 255, 255),
    glow_radius=4,
    glow_intensity=180,
    num_sparkles=6,
    highlight_color=(255, 255, 255),
    sparkle_size=2,
    extra_glow_layers=2,
    secondary_glow_color=(255, 255, 200),
    add_cross_sparkles=True,
)

# 9. Eldritch – Eerie teal/cyan with alien wisps
print("\n[9/10] Eldritch (E) – Eerie teal-cyan")
render_icon(
    letter_key="E",
    filename="eldritch.png",
    color_top=(60, 240, 220),
    color_bottom=(20, 140, 160),
    glow_color=(40, 220, 200),
    outline_color=(5, 40, 45),
    sparkle_color=(150, 255, 240),
    glow_radius=4,
    glow_intensity=170,
    num_sparkles=6,
    highlight_color=(180, 255, 245),
    sparkle_size=2,
    extra_glow_layers=2,
    secondary_glow_color=(80, 180, 255),
    add_cross_sparkles=True,
)

# 10. Abyssal – Void black core with magenta/purple rim energy
print("\n[10/10] Abyssal (A) – Void energy")
render_icon(
    letter_key="A",
    filename="abyssal.png",
    color_top=(80, 20, 100),
    color_bottom=(20, 5, 30),
    glow_color=(200, 50, 255),
    outline_color=(180, 40, 220),
    sparkle_color=(255, 120, 255),
    glow_radius=4,
    glow_intensity=200,
    num_sparkles=7,
    highlight_color=(160, 60, 200),
    sparkle_size=2,
    extra_glow_layers=3,
    secondary_glow_color=(255, 50, 180),
    add_cross_sparkles=True,
)

print("\n" + "=" * 60)
print("  All 10 rarity icons regenerated successfully!")
print(f"  Output: {OUTPUT_DIR}")
print("=" * 60)
