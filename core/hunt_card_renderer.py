from __future__ import annotations

import json
import math
import random
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from core.content_config import ASSET_DIR, get_asset_file_path, get_creature_asset_path
from core.rpg_data import normalize_key


class CollectionStatus(Enum):
    NEW = "NEW DISCOVERY"
    DUPLICATE = "DUPLICATE"
    COMPLETE = "COLLECTION COMPLETE"


_RARITY_COLORS: dict[str, tuple[int, int, int]] = {
    "Common": (139, 148, 158), "Uncommon": (74, 222, 128),
    "Rare": (56, 189, 248), "Epic": (167, 139, 250),
    "Legendary": (250, 204, 21), "Mythic": (251, 113, 133),
    "Ancient": (249, 115, 22), "Divine": (254, 243, 199),
    "Eldritch": (34, 211, 238), "Abyssal": (130, 90, 200),
    "Prismatic": (16, 185, 129), "Ethereal": (96, 165, 250),
}

_RARITY_GLOW_COLORS: dict[str, tuple[int, int, int]] = {
    "Common": (60, 65, 75), "Uncommon": (30, 140, 70),
    "Rare": (20, 100, 170), "Epic": (100, 60, 180),
    "Legendary": (180, 140, 10), "Mythic": (180, 50, 70),
    "Ancient": (180, 80, 10), "Divine": (200, 180, 120),
    "Eldritch": (10, 140, 160), "Abyssal": (80, 40, 140),
}

_ULTRA_RARITIES = {"Divine", "Eldritch", "Abyssal"}

_PANEL = (22, 18, 32)
_PANEL2 = (14, 11, 24)
_PANEL3 = (28, 23, 40)
_BORDER = (48, 40, 62)
_TEXT = (235, 228, 218)
_TEXT_BRIGHT = (255, 252, 245)
_TEXT_MUTED = (135, 124, 116)
_GOLD = (235, 195, 80)
_RED = (220, 60, 75)
_GREEN = (80, 210, 120)
_BLUE = (70, 160, 235)
_PURPLE = (170, 95, 245)
_CYAN = (55, 225, 210)
_ORANGE = (245, 145, 45)

_ZONE_BG_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "forgotten_woods": ((20, 28, 18), (8, 14, 10)),
    "grave_marsh": ((22, 26, 18), (10, 12, 8)),
    "bloodmoon_forest": ((40, 12, 14), (18, 6, 8)),
    "ashen_wastes": ((38, 34, 26), (18, 16, 12)),
    "infernal_catacombs": ((44, 16, 10), (22, 8, 4)),
    "void_realm": ((12, 8, 24), (4, 2, 12)),
    "abyssal_depths": ((8, 6, 22), (2, 1, 10)),
    "cursed_sanctum": ((28, 14, 30), (14, 6, 16)),
    "starless_menagerie": ((10, 10, 26), (4, 3, 14)),
    "throne_of_teeth": ((30, 18, 22), (14, 8, 12)),
    "black_sun_gate": ((6, 4, 18), (1, 1, 8)),
}


_FONT_CACHE: dict[str, ImageFont.ImageFont] = {}

def _load_font(path: str, size: int) -> ImageFont.ImageFont | None:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return None

def _font(size: int, *, bold: bool = False, fantasy: bool = False) -> ImageFont.ImageFont:
    k = f"{size}_{bold}_{fantasy}"
    if k in _FONT_CACHE:
        return _FONT_CACHE[k]
    candidates = []
    if fantasy:
        candidates.extend([
            "OLDENGL.TTF", "GOUDYSTO.TTF", "AGENCYB.TTF",
            "ALGER.TTF", "FORTE.TTF",
        ])
    candidates.extend([
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "consolab.ttf" if bold else "consola.ttf",
        "courbd.ttf" if bold else "cour.ttf",
    ])
    if fantasy and not bold:
        candidates.insert(0, "AGENCYR.TTF")
    candidates.append("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    candidates.append("NotoSans-Bold.ttf" if bold else "NotoSans.ttf")
    font_dir = Path("C:/Windows/Fonts")
    for name in candidates:
        path = font_dir / name
        f = _load_font(str(path), size)
        if f is not None:
            _FONT_CACHE[k] = f
            return f
    f = ImageFont.load_default()
    _FONT_CACHE[k] = f
    return f


def _tw(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_w: int, font: ImageFont.ImageFont) -> str:
    s = str(text)
    if _tw(draw, s, font) <= max_w:
        return s
    for i in range(len(s), 0, -1):
        out = s[:i] + "..."
        if _tw(draw, out, font) <= max_w:
            return out
    return "..."


def _col(rarity: str | None) -> tuple[int, int, int]:
    return _RARITY_COLORS.get(str(rarity or "Common"), (139, 148, 158))


def _glow_col(rarity: str | None) -> tuple[int, int, int]:
    return _RARITY_GLOW_COLORS.get(str(rarity or "Common"), (60, 65, 75))


def _lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _shadow_text(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font: ImageFont.ImageFont,
                 color: tuple[int, int, int], shadow_color: tuple[int, int, int] = (0, 0, 0),
                 offset: int = 2) -> None:
    draw.text((x + offset, y + offset), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=color)


# ── Rarity ordering for priority comparisons ──────────────────
_RARITY_ORDER: dict[str, int] = {
    "Common": 0, "Uncommon": 1, "Rare": 2, "Epic": 3, "Legendary": 4,
    "Mythic": 5, "Ancient": 6, "Divine": 7, "Eldritch": 8, "Abyssal": 9,
    "Prismatic": 10, "Ethereal": 11, "Void Lord": 12, "Hidden": 13,
}

# ── Layout configs per multi-hunt tier ────────────────────────
_LOOT_GRID_LAYOUT = {
    "card_width": 1600,
    "header_height": 130,
    "title_font": 34, "subtitle_font": 20, "count_font": 28,
    "cell_normal": {"width": 260, "height": 320, "sprite_size": 100, "name_font": 18, "val_font": 16, "rarity_font": 13},
    "cell_hero": {"width": 340, "height": 400, "sprite_size": 150, "name_font": 24, "val_font": 20, "rarity_font": 16},
    "grid_cols": 3, "grid_pad_x": 60, "grid_pad_y": 24, "gap_x": 36, "gap_y": 28,
    "summary_pad": 20, "summary_font": 22, "summary_label_font": 16,
    "footer_height": 60,
}

_COMPACT_GRID_LAYOUT = {
    "card_width": 1600,
    "header_height": 110,
    "title_font": 30, "subtitle_font": 18, "count_font": 24,
    "cell_normal": {"width": 210, "height": 250, "sprite_size": 75, "name_font": 15, "val_font": 14, "rarity_font": 12},
    "cell_hero": {"width": 270, "height": 320, "sprite_size": 110, "name_font": 20, "val_font": 17, "rarity_font": 14},
    "grid_cols": 5, "grid_pad_x": 50, "grid_pad_y": 18, "gap_x": 24, "gap_y": 20,
    "summary_pad": 16, "summary_font": 20, "summary_label_font": 14,
    "footer_height": 50,
}

_MASS_HUNT_LAYOUT = {
    "card_width": 1600,
    "header_height": 100,
    "title_font": 28, "subtitle_font": 16, "count_font": 22,
    "row_height": 56, "icon_size": 44, "row_pad_x": 60,
    "name_font": 18, "val_font": 16, "rarity_font": 14,
    "hero_row_height": 72, "hero_icon_size": 60,
    "hero_name_font": 22, "hero_val_font": 18, "hero_rarity_font": 16,
    "summary_pad": 16, "summary_font": 20, "summary_label_font": 14,
    "footer_height": 50,
    "max_height": 1200,
}


class HuntCardRenderer:

    def __init__(self, layout_config_path: str | Path | None = None) -> None:
        self.layout = self._load_layout(layout_config_path)

    def _load_layout(self, path: str | Path | None) -> dict[str, Any]:
        default = str(ASSET_DIR / "hunt_card_layout.json")
        p = Path(path or default)
        if p.exists():
            return json.loads(p.read_text("utf-8"))
        return {
            "card": {"width": 1920, "height": 1080},
            "background": {"darken_factor": 0.55, "blur_radius": 8, "vignette_strength": 0.75, "vignette_radius": 1.2},
            "top_section": {"height": 90, "title_font_size": 32, "title_color": [255, 252, 245], "zone_icon_size": [40, 40], "separator_color": [90, 70, 110]},
            "monster_portrait": {"x_center": 960, "y_center": 460, "size": 420, "border_width": 4, "glow_spread": 60, "shadow_offset": 8, "depth_layers": 3},
            "monster_info": {"x": 960, "y": 680, "name_font_size": 36, "label_font_size": 16, "value_font_size": 28, "line_spacing": 36},
            "collection_status": {"x": 960, "y": 860, "font_size": 24, "glow_radius": 30},
            "rewards_section": {"x": 60, "y": 200, "width": 380, "header_font_size": 20, "item_font_size": 16, "icon_size": [24, 24], "line_spacing": 30, "panel_padding": 16, "panel_radius": 10},
            "special_drop": {"x": 60, "y": 550, "width": 380, "height": 160, "header_font_size": 18, "item_font_size": 24, "panel_radius": 12, "border_width": 3, "glow_color": [250, 204, 21]},
            "player_section": {"x": 60, "y": 920, "name_font_size": 24, "rank_font_size": 16, "streak_font_size": 16, "line_spacing": 28},
            "drop_info": {"x": 1480, "y": 920, "width": 380, "label_font_size": 14, "value_font_size": 18, "line_spacing": 24, "panel_padding": 14, "panel_radius": 8},
            "ultra_rare": {"vignette_strength": 0.9, "vignette_radius": 1.5, "distortion_amount": 4, "energy_particle_count": 60, "banner_y": 140, "banner_height": 70, "banner_font_size": 28, "encounter_font_size": 20, "encounter_y": 210},
        }

    # ── Public API ─────────────────────────────────────────────

    def render_hunt_card(self, data: dict[str, Any]) -> BytesIO:
        monster = data.get("monster")
        if not monster:
            return self._render_failed_hunt(data)
            
        rarity = str(monster.get("rarity", "Common"))
        if rarity in _ULTRA_RARITIES:
            return self._render_ultra_rare(data)
        return self._render_standard(data)

    def _render_failed_hunt(self, data: dict[str, Any]) -> BytesIO:
        cfg = self.layout["card"]
        W, H = cfg["width"], cfg["height"]
        img = self._build_background(str(data.get("zone_key", "bloodmoon_forest")))
        draw = ImageDraw.Draw(img)
        
        self._draw_top_section(draw, str(data.get("zone_name", "Unknown Zone")), str(data.get("zone_key", "forgotten_woods")), img, "Common")
        
        font_main = _font(48, bold=True)
        text = "Nothing was found in the shadows..."
        tw = _tw(draw, text, font_main)
        draw.text((W//2 - tw//2, H//2 - 24), text, font=font_main, fill=_TEXT_MUTED)
        
        self._draw_player_section(draw, str(data.get("hunter_name", "")), str(data.get("hunter_rank", "Unknown")))
        
        return self._save(img)

    def render_rare_variant(self, data: dict[str, Any]) -> BytesIO:
        return self._render_standard(data, rare_variant=True)

    def render_event_variant(self, data: dict[str, Any]) -> BytesIO:
        return self._render_standard(data, event_variant=True)

    def render_boss_variant(self, data: dict[str, Any]) -> BytesIO:
        return self._render_standard(data, boss_variant=True)

    def render_multi_hunt_card(self, data: dict[str, Any]) -> BytesIO:
        monsters = data.get("monsters", [])
        count = len(monsters)
        if count <= 0:
            # Fallback: render single hunt if no monsters list
            return self.render_hunt_card(data)
        if count <= 5:
            return self._render_loot_grid(data)
        if count <= 10:
            return self._render_compact_grid(data)
        return self._render_mass_hunt(data)

    # ── Background ─────────────────────────────────────────────

    def _build_background(self, zone_key: str, *, ultra: bool = False) -> Image.Image:
        cfg = self.layout["card"]
        W, H = cfg["width"], cfg["height"]
        bg_cfg = self.layout["background"]
        bg = self._get_zone_background(zone_key, W, H)
        darken = Image.new("RGB", (W, H), (0, 0, 0))
        factor = bg_cfg["darken_factor"]
        if ultra:
            factor = min(1.0, factor + 0.25)
        bg = Image.blend(bg, darken, factor)
        blur_r = bg_cfg["blur_radius"]
        if ultra:
            blur_r = blur_r * 2
        if blur_r > 0:
            bg = bg.filter(ImageFilter.GaussianBlur(radius=blur_r))
        vignette = self._make_vignette(W, H,
            strength=bg_cfg["vignette_strength"] * (1.3 if ultra else 1.0),
            radius=bg_cfg["vignette_radius"] * (1.4 if ultra else 1.0),
        )
        bg.paste(vignette, (0, 0), vignette)
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fd = ImageDraw.Draw(frame)
        fd.rectangle((0, 0, W - 1, H - 1), outline=(0, 0, 0, 60), width=3)
        bg.paste(frame, (0, 0), frame)
        return bg

    def _get_zone_background(self, zone_key: str, W: int, H: int) -> Image.Image:
        path = get_asset_file_path("zones", zone_key)
        if path and path.exists():
            try:
                img = Image.open(path).convert("RGB")
                return img.resize((W, H), Image.Resampling.LANCZOS)
            except OSError:
                pass
        return self._generate_gradient_bg(zone_key, W, H)

    def _generate_gradient_bg(self, zone_key: str, W: int, H: int) -> Image.Image:
        colors = _ZONE_BG_COLORS.get(zone_key, ((16, 12, 28), (8, 6, 14)))
        top_color, bot_color = colors
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)
        for y in range(H):
            t = y / max(1, H - 1)
            draw.line((0, y, W, y), fill=_lerp_color(top_color, bot_color, t))
        noise = Image.effect_noise((W, H), 20).convert("L")
        noise = noise.point(lambda p: p // 14)
        noise_rgb = Image.merge("RGB", (noise, noise, noise))
        img = Image.blend(img, noise_rgb, 0.12)
        return img

    def _make_vignette(self, W: int, H: int, *, strength: float = 0.75, radius: float = 1.2) -> Image.Image:
        pad = 200
        v = Image.new("RGBA", (W + pad * 2, H + pad * 2), (0, 0, 0, 0))
        vd = ImageDraw.Draw(v)
        cx, cy = (W + pad * 2) // 2, (H + pad * 2) // 2
        max_r = math.sqrt(cx * cx + cy * cy) * radius
        for i in range(60):
            t = i / 60
            r = int(max_r * t)
            a = int(min(255, t * strength * 255 * 1.5))
            if a <= 0:
                continue
            vd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(0, 0, 0, a), width=20)
        v = v.crop((pad, pad, W + pad, H + pad))
        return v

    # ── Top Section ────────────────────────────────────────────

    def _draw_top_section(self, draw: ImageDraw.ImageDraw, zone_name: str, zone_key: str, img: Image.Image, rarity: str) -> None:
        cfg = self.layout["top_section"]
        W = self.layout["card"]["width"]
        y = cfg["y_offset"]
        h = cfg["height"]
        rc = _col(rarity)
        bg_rect = Image.new("RGBA", (W, h), (0, 0, 0, 0))
        brd = ImageDraw.Draw(bg_rect)
        for i in range(h):
            t = i / max(1, h - 1)
            alpha = int(max(0, 50 - i * 2) * (1 - t * 0.5))
            color = _lerp_color((0, 0, 0), rc, 0.06)
            brd.line((0, i, W, i), fill=(*color, alpha))
        img.paste(bg_rect, (0, y), bg_rect)

    # ── Encounter Text ─────────────────────────────────────────

    def _draw_encounter_text(self, draw: ImageDraw.ImageDraw, rarity: str) -> None:
        cfg = self.layout.get("encounter_text", {})
        W = self.layout["card"]["width"]
        y = cfg.get("y_offset", 72)
        fsize = cfg.get("font_size", 18)
        color = tuple(cfg.get("color", (200, 195, 185)))
        if rarity in _ULTRA_RARITIES:
            flavor = "A legendary presence emerges..."
        elif rarity in ("Legendary", "Mythic", "Ancient"):
            flavor = "A powerful creature reveals itself..."
        elif rarity in ("Rare", "Epic"):
            flavor = "An unusual presence stirs..."
        else:
            flavor = ""
        if not flavor:
            return
        font = _font(fsize, bold=False, fantasy=False)
        tw = _tw(draw, flavor, font)
        x = (W - tw) // 2
        _shadow_text(draw, x, y, flavor, font, color)

    # ── Rarity Display (above monster, always visible) ─────────

    def _draw_rarity_display(self, draw: ImageDraw.ImageDraw, img: Image.Image, rarity: str) -> None:
        cfg = self.layout["rarity_section"]
        W = self.layout["card"]["width"]
        y = cfg["y_offset"]
        rc = _col(rarity)
        text = rarity.upper()
        font = _font(cfg["font_size"], bold=True, fantasy=False)
        tw = _tw(draw, text, font)
        x = (W - tw) // 2
        sym_size = 12
        sym_gap = 16
        sym_y = y + 14
        left_sym_x = x - sym_gap - sym_size
        right_sym_x = x + tw + sym_gap
        for cx in (left_sym_x, right_sym_x):
            draw.ellipse((cx, sym_y, cx + sym_size, sym_y + sym_size), fill=rc)
        _shadow_text(draw, x, y + 8, text, font, _TEXT_BRIGHT, shadow_color=(0, 0, 0), offset=3)
        bar_color = _lerp_color(rc, (255, 255, 255), 0.3)
        bar_y = y + cfg["banner_height"]
        for i in range(3):
            draw.rectangle((x - 20 + i, bar_y + i, x + tw + 20 - i, bar_y + i + 1),
                          fill=(*bar_color, max(1, 80 - i * 25)))

    # ── Monster Portrait ───────────────────────────────────────

    def _draw_radial_glow(self, img: Image.Image, cx: int, cy: int, radius: int, color: tuple[int, int, int], layers: int = 2) -> None:
        for layer in range(layers):
            r = radius + layer * 40
            glow = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            for i in range(r, 0, -10):
                t = i / r
                a = int(max(0, 25 - layer * 8) * (1 - t * t))
                gd.ellipse((r - i, r - i, r + i, r + i), fill=(*color, a))
            glow = glow.filter(ImageFilter.GaussianBlur(radius=15 + layer * 8))
            img.paste(glow, (cx - r, cy - r), glow)

    def _draw_monster_portrait(self, draw: ImageDraw.ImageDraw, img: Image.Image, monster_key: str, rarity: str) -> None:
        cfg = self.layout["monster_portrait"]
        cx, cy = cfg["x_center"], cfg["y_center"]
        size = cfg["size"]
        rc = _col(rarity)
        gc = _glow_col(rarity)
        self._draw_radial_glow(img, cx, cy, cfg.get("radial_glow_radius", 200),
                               gc, cfg.get("radial_glow_layers", 2))
        portrait = self._load_creature_asset(monster_key, size)
        if portrait is None:
            portrait = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            pd = ImageDraw.Draw(portrait)
            pd.rounded_rectangle((4, 4, size - 4, size - 4), radius=16,
                                fill=_PANEL2, outline=(*_BORDER, 255))
        depth = cfg["depth_layers"]
        for i in range(depth - 1, -1, -1):
            offset = (depth - i) * cfg["shadow_offset"]
            alpha = 35 - i * 10
            shadow = Image.new("RGBA", (size + 10, size + 10), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            sd.rounded_rectangle((5, 5, size + 5, size + 5), radius=16, fill=(0, 0, 0, alpha))
            img.paste(shadow, (cx - size // 2 - 5 + offset, cy - size // 2 - 5 + offset), shadow)
        glow = Image.new("RGBA", (size + cfg["glow_spread"] * 2, size + cfg["glow_spread"] * 2), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for r in range(cfg["glow_spread"], 0, -6):
            a = max(1, 35 - int(r * 0.5))
            gd.ellipse(
                (cfg["glow_spread"] - r, cfg["glow_spread"] - r,
                 cfg["glow_spread"] + size + r, cfg["glow_spread"] + size + r),
                fill=(*gc, a),
            )
        img.paste(glow, (cx - size // 2 - cfg["glow_spread"], cy - size // 2 - cfg["glow_spread"]), glow)
        border_w = cfg["border_width"]
        for w in range(border_w, 0, -1):
            a = 255 - (border_w - w) * 80
            draw.rounded_rectangle(
                (cx - size // 2 - w, cy - size // 2 - w, cx + size // 2 + w, cy + size // 2 + w),
                radius=16, outline=(*rc, a), width=w)
        portrait_padded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        mask = Image.new("L", (size, size), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle((2, 2, size - 2, size - 2), radius=14, fill=255)
        portrait_padded.paste(portrait, (0, 0), mask if portrait.mode == "RGBA" else None)
        inner_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        isd = ImageDraw.Draw(inner_shadow)
        for r in range(15, 0, -2):
            isd.rounded_rectangle((r, r, size - r, size - r), radius=14, outline=(0, 0, 0, max(1, 25 - r)))
        portrait_padded = Image.alpha_composite(portrait_padded, inner_shadow)
        img.paste(portrait_padded, (cx - size // 2, cy - size // 2), portrait_padded)

    # ── Monster Name (2nd largest element) ─────────────────────

    def _draw_monster_name(self, draw: ImageDraw.ImageDraw, name: str, rarity: str) -> None:
        cfg = self.layout["monster_info"]
        x = cfg["x"]
        y = cfg["y"]
        rc = _col(rarity)
        font_name = _font(cfg["name_font_size"], bold=True)
        name_text = name.upper()
        nw = _tw(draw, name_text, font_name)
        for dx, dy in [(3, 3), (2, 2), (1, 1)]:
            draw.text((x - nw // 2 + dx, y + dy), name_text, font=font_name, fill=(0, 0, 0, 160 - dx * 40))
        draw.text((x - nw // 2, y), name_text, font=font_name, fill=_TEXT_BRIGHT)

    # ── Stat Panel (Level / Trait / Value) ─────────────────────

    def _draw_stat_panel(self, draw: ImageDraw.ImageDraw, level: int, trait: str, value: int, rarity: str) -> None:
        cfg = self.layout.get("stat_panel", {})
        xc = cfg.get("x_center", 960)
        y = cfg.get("y", 740)
        spacing = cfg.get("spacing", 160)
        rc = _col(rarity)
        font_label = _font(cfg.get("label_font_size", 20), bold=True)
        font_value = _font(cfg.get("value_font_size", 26), bold=True)
        labels = [("LEVEL", str(level), _TEXT_BRIGHT),
                  ("TRAIT", trait if trait else "--", rc if trait else _TEXT_MUTED),
                  ("VALUE", f"{value:,}", _GOLD)]
        for i, (label, val, vc) in enumerate(labels):
            lx = xc - spacing + i * spacing
            lw = _tw(draw, label, font_label)
            draw.text((lx - lw // 2, y), label, font=font_label, fill=_TEXT_MUTED)
            vw = _tw(draw, val, font_value)
            _shadow_text(draw, lx - vw // 2, y + 26, val, font_value, vc)

    # ── Collection Status (below name + stats) ─────────────────

    def _draw_collection_status(self, draw: ImageDraw.ImageDraw, img: Image.Image, status: str, rarity: str) -> None:
        cfg = self.layout["collection_status"]
        x = cfg["x"]
        y = cfg["y"]
        rc = _col(rarity)
        if status == CollectionStatus.NEW.value:
            text = "NEW DISCOVERY"
            font = _font(cfg["font_size"], bold=True, fantasy=False)
            tw = _tw(draw, text, font)
            gx = x - tw // 2 - 20
            gy = y - 8
            glow_img = Image.new("RGBA", (tw + 60, 60), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_img)
            for r in range(20, 0, -3):
                a = max(1, 25 - r)
                gd.rounded_rectangle((30 - r, 8 - r, tw + 30 + r, 52 + r), radius=r + 5, fill=(*rc, a))
            img.paste(glow_img, (gx - 10, gy - 8), glow_img)
            draw.rounded_rectangle((gx - 5, gy, gx + tw + 50, gy + 44), radius=8,
                                  fill=(*rc, 30), outline=(*rc, 200), width=2)
            _shadow_text(draw, x - tw // 2, y + 6, text, font, _TEXT_BRIGHT, offset=2)
            for _ in range(8):
                px = x + random.randint(-80, 80)
                py = y + random.randint(-15, 40)
                s = random.randint(2, 4)
                a = random.randint(60, 160)
                p = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0))
                pd = ImageDraw.Draw(p)
                pd.ellipse((0, 0, s * 2, s * 2), fill=(*rc, a))
                img.paste(p, (px, py), p)
        elif status == CollectionStatus.DUPLICATE.value:
            text = "DUPLICATE"
            font = _font(cfg["font_size"], bold=True)
            tw = _tw(draw, text, font)
            pad_h = 6
            pad_w = 16
            bw = tw + pad_w * 2 + 4
            bh = cfg["font_size"] + pad_h * 2 + 4
            badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            bd = ImageDraw.Draw(badge)
            bd.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=6, fill=(*_PANEL2, 220), outline=(80, 75, 70), width=1)
            img.paste(badge, (x - bw // 2, y), badge)
            draw.text((x - tw // 2, y + pad_h), text, font=font, fill=_TEXT_MUTED)
        else:
            text = "COLLECTION COMPLETE"
            font = _font(cfg["font_size"], bold=True)
            tw = _tw(draw, text, font)
            _shadow_text(draw, x - tw // 2, y + 6, text, font, _GOLD)

    # ── Rewards Section ────────────────────────────────────────

    def _draw_rewards(self, draw: ImageDraw.ImageDraw, img: Image.Image, rewards: list[dict[str, Any]]) -> None:
        cfg = self.layout["rewards_section"]
        x, y = cfg["x"], cfg["y"]
        w = cfg["width"]
        pad = cfg["panel_padding"]
        r = cfg["panel_radius"]
        if not rewards:
            return
        item_h = cfg["line_spacing"]
        header_h = 36
        total_h = header_h + len(rewards) * item_h + pad * 2
        panel = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(panel)
        pd.rounded_rectangle((0, 0, w - 1, total_h - 1), radius=r, fill=(*_PANEL, 200), outline=_BORDER)
        img.paste(panel, (x, y), panel)
        font_header = _font(cfg["header_font_size"], bold=True)
        draw.text((x + pad, y + pad), "REWARDS", font=font_header, fill=_GOLD)
        cy = y + pad + header_h
        icon_size = tuple(cfg["icon_size"])
        souls_icon_size = tuple(cfg.get("souls_icon_size", (34, 34)))
        souls_fsize = cfg.get("souls_font_size", 22)
        for reward in rewards:
            label = str(reward.get("label", ""))
            amount = reward.get("amount", 0)
            color = tuple(reward.get("color", _TEXT))
            icon_key = str(reward.get("icon_key", ""))
            icon_kind = str(reward.get("kind", "currency"))
            is_souls = "soul" in label.lower()
            item_font = _font(souls_fsize, bold=True) if is_souls else _font(cfg["item_font_size"])
            cur_icon_size = souls_icon_size if is_souls else icon_size
            line = f"+{amount:,} {label}" if amount else label
            if icon_key:
                icon = self._load_asset(icon_kind, icon_key, cur_icon_size)
                if icon:
                    img.paste(icon, (x + pad, cy + 2), icon)
                    draw.text((x + pad + cur_icon_size[0] + 8, cy + 2), line, font=item_font, fill=color)
                else:
                    draw.text((x + pad, cy + 2), line, font=item_font, fill=color)
            else:
                draw.text((x + pad, cy + 2), line, font=item_font, fill=color)
            cy += item_h

    # ── Special Drop ───────────────────────────────────────────

    def _draw_special_drop(self, draw: ImageDraw.ImageDraw, img: Image.Image, drop: dict[str, Any] | None) -> None:
        if not drop:
            return
        cfg = self.layout["special_drop"]
        x, y = cfg["x"], cfg["y"]
        w, h = cfg["width"], cfg["height"]
        drop_type = str(drop.get("type", ""))
        drop_name = str(drop.get("name", ""))
        drop_rarity = str(drop.get("rarity", "Legendary"))
        rc = _col(drop_rarity)
        panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(panel)
        pd.rounded_rectangle((0, 0, w - 1, h - 1), radius=cfg["panel_radius"],
                            fill=(*_PANEL2, 230), outline=rc, width=cfg["border_width"])
        img.paste(panel, (x, y), panel)
        font_h = _font(cfg["header_font_size"], bold=True)
        font_n = _font(cfg["item_font_size"], bold=True, fantasy=False)
        if drop_type == "weapon":
            header = "LEGENDARY WEAPON FOUND"
        elif drop_type == "relic":
            header = "RELIC CACHE FOUND"
        else:
            header = "SPECIAL DROP"
        hw = _tw(draw, header, font_h)
        draw.text((x + (w - hw) // 2, y + 14), header, font=font_h, fill=rc)
        nw = _tw(draw, drop_name, font_n)
        draw.text((x + (w - nw) // 2, y + 60), drop_name, font=font_n, fill=_TEXT_BRIGHT)

    # ── Player Section ─────────────────────────────────────────

    def _draw_player_section(self, draw: ImageDraw.ImageDraw, name: str, rank: str) -> None:
        cfg = self.layout["player_section"]
        x, y = cfg["x"], cfg["y"]
        font_name = _font(cfg["name_font_size"], bold=True)
        font_other = _font(cfg["rank_font_size"])
        _shadow_text(draw, x, y, name, font_name, _TEXT_BRIGHT)
        _shadow_text(draw, x, y + cfg["line_spacing"], rank, font_other, _GOLD)

    # ── Streak Badge ───────────────────────────────────────────

    def _draw_streak_badge(self, draw: ImageDraw.ImageDraw, img: Image.Image, streak: int) -> None:
        cfg = self.layout.get("streak_badge", {})
        if streak <= 0:
            return
        x, y = cfg.get("x", 430), cfg.get("y", 930)
        fsize = cfg.get("font_size", 20)
        if streak >= 50:
            label = "LEGENDARY"
            fg = (255, 200, 50); bg = (80, 50, 10); border = (255, 200, 50)
        elif streak >= 25:
            label = "EPIC"; fg = (255, 180, 60); bg = (60, 40, 10); border = (255, 180, 60)
        elif streak >= 10:
            label = "RARE"; fg = (255, 160, 80); bg = (50, 30, 10); border = (200, 130, 40)
        else:
            label = ""; fg = (200, 150, 100); bg = (35, 25, 15); border = (150, 110, 60)
        text = f"{streak}x STREAK" if not label else f"{label} {streak}x"
        font = _font(fsize, bold=True)
        tw = _tw(draw, text, font)
        pad = 10
        bw = tw + pad * 2 + 4
        bh = fsize + pad + 6
        rr = cfg.get("panel_radius", 6)
        shadow = Image.new("RGBA", (bw + 4, bh + 4), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle((2, 2, bw + 2, bh + 2), radius=rr, fill=(0, 0, 0, 80))
        img.paste(shadow, (x - 2, y - 2), shadow)
        badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=rr, fill=(*bg, 210), outline=border, width=1)
        img.paste(badge, (x, y), badge)
        draw.text((x + pad, y + pad // 2), text, font=font, fill=fg)

    # ── Drop Info ──────────────────────────────────────────────

    def _draw_drop_info(self, draw: ImageDraw.ImageDraw, img: Image.Image,
                       catch_chance: float, rarity: str, zone_name: str) -> None:
        cfg = self.layout["drop_info"]
        x, y = cfg["x"], cfg["y"]
        w = cfg["width"]
        pad = cfg["panel_padding"]
        r = cfg["panel_radius"]
        rc = _col(rarity)
        items = [
            ("Catch Chance", f"{catch_chance:.0f}%", _GREEN),
            ("Rarity", rarity, rc),
            ("Zone", zone_name, _TEXT_MUTED),
        ]
        total_h = pad * 2 + len(items) * cfg["line_spacing"] + 10
        panel = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(panel)
        pd.rounded_rectangle((0, 0, w - 1, total_h - 1), radius=r, fill=(*_PANEL, 200), outline=_BORDER)
        img.paste(panel, (x, y), panel)
        font_label = _font(cfg["label_font_size"])
        font_value = _font(cfg["value_font_size"], bold=True)
        cy = y + pad
        for label, value, color in items:
            draw.text((x + pad, cy), label, font=font_label, fill=_TEXT_MUTED)
            vw = _tw(draw, value, font_value)
            draw.text((x + w - pad - vw, cy), value, font=font_value, fill=color)
            cy += cfg["line_spacing"]

    # ── Ambient Effects (reduced intensity) ────────────────────

    def _draw_ambient_effects(self, draw: ImageDraw.ImageDraw, img: Image.Image, zone_key: str) -> None:
        acfg = self.layout.get("ambient_effects", {})
        if not acfg.get("enabled", True):
            return
        W, H = self.layout["card"]["width"], self.layout["card"]["height"]
        pc = acfg.get("particle_count", 30)
        fw = acfg.get("fog_wisps", 6)
        fo = acfg.get("fog_opacity", 25)
        zone_palettes = {
            "forgotten_woods": {"part": [(60, 120, 60)], "fog": (25, 40, 20)},
            "grave_marsh": {"part": [(90, 95, 40), (130, 150, 55)], "fog": (25, 30, 15)},
            "bloodmoon_forest": {"part": [(170, 35, 20), (140, 25, 15)], "fog": (40, 12, 8)},
            "ashen_wastes": {"part": [(110, 100, 85)], "fog": (30, 28, 22)},
            "infernal_catacombs": {"part": [(210, 75, 20), (180, 55, 15)], "fog": (35, 10, 5)},
            "void_realm": {"part": [(55, 25, 95), (75, 35, 115)], "fog": (8, 4, 20)},
            "abyssal_depths": {"part": [(40, 20, 85)], "fog": (5, 3, 18)},
            "cursed_sanctum": {"part": [(115, 45, 125)], "fog": (22, 10, 26)},
            "starless_menagerie": {"part": [(50, 50, 115)], "fog": (8, 8, 22)},
            "throne_of_teeth": {"part": [(135, 65, 55)], "fog": (26, 14, 18)},
            "black_sun_gate": {"part": [(30, 20, 75)], "fog": (4, 2, 15)},
        }
        pal = zone_palettes.get(zone_key, zone_palettes["forgotten_woods"])
        fog = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fd = ImageDraw.Draw(fog)
        fog_c = pal["fog"]
        for _ in range(fw):
            fx = random.randint(-200, W + 200)
            fy = random.randint(100, 800)
            fw2 = random.randint(300, 600)
            fh = random.randint(30, 100)
            a = random.randint(5, fo)
            fd.ellipse((fx, fy, fx + fw2, fy + fh), fill=(*fog_c, a))
        img.paste(fog, (0, 0), fog)
        for _ in range(pc):
            px = random.randint(50, W - 50)
            py = random.randint(50, H - 50)
            s = random.randint(2, 5)
            col = random.choice(pal["part"])
            a = random.randint(10, 70)
            p = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0))
            pd = ImageDraw.Draw(p)
            pd.ellipse((0, 0, s * 2, s * 2), fill=(*col, a))
            img.paste(p, (px, py), p)

    # ── Rarity Effects (text-friendly) ─────────────────────────

    def _apply_rarity_effects(self, draw: ImageDraw.ImageDraw, img: Image.Image, rarity: str) -> None:
        W, H = self.layout["card"]["width"], self.layout["card"]["height"]
        cx, cy = W // 2, H // 2
        rc = _col(rarity)
        gc = _glow_col(rarity)
        if rarity == "Common":
            return
        if rarity == "Rare":
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            for r in range(300, 0, -20):
                a = max(1, 15 - r // 30)
                gd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*gc, a), width=4)
            img.paste(glow, (0, 0), glow)
        elif rarity == "Epic":
            aura = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(aura)
            for r in range(400, 0, -15):
                a = max(1, 20 - r // 25)
                ad.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*rc, a), width=8)
            img.paste(aura, (0, 0), aura)
        elif rarity == "Legendary":
            aura = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(aura)
            for r in range(400, 0, -12):
                a = max(1, 25 - r // 20)
                ad.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*rc, a), width=10)
            img.paste(aura, (0, 0), aura)
            self._add_particles_simple(img, W, H, rc, count=20)
        elif rarity == "Mythic":
            aura = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(aura)
            for r in range(400, 0, -10):
                a = max(1, 30 - r // 18)
                ad.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(80, 20, 30, a), width=12)
            img.paste(aura, (0, 0), aura)
            self._add_particles_simple(img, W, H, _RED, count=20)
        elif rarity == "Ancient":
            self._add_particles_simple(img, W, H, _GOLD, count=20)
        elif rarity == "Divine":
            aura = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(aura)
            for r in range(500, 0, -10):
                a = max(1, 20 - r // 35)
                ad.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(200, 200, 220, a), width=10)
            img.paste(aura, (0, 0), aura)
        elif rarity == "Eldritch":
            aura = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(aura)
            for r in range(400, 0, -12):
                a = max(1, 25 - r // 20)
                ad.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(60, 20, 80, a), width=8)
            img.paste(aura, (0, 0), aura)
        elif rarity == "Abyssal":
            void = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vd = ImageDraw.Draw(void)
            for r in range(500, 0, -10):
                a = max(1, 50 - r // 14)
                vd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(20, 10, 50, a), width=6)
            img.paste(void, (0, 0), void)
            self._add_particles_simple(img, W, H, _PURPLE, count=15)

    def _add_particles_simple(self, img: Image.Image, W: int, H: int, color: tuple[int, int, int],
                             count: int = 20) -> None:
        for _ in range(count):
            px = random.randint(100, W - 100)
            py = random.randint(100, H - 100)
            s = random.randint(2, 4)
            a = random.randint(40, 140)
            p = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0))
            pd = ImageDraw.Draw(p)
            pd.ellipse((0, 0, s * 2, s * 2), fill=(*color, a))
            img.paste(p, (px, py), p)

    def _add_tentacle_effect(self, img: Image.Image, draw: ImageDraw.ImageDraw, W: int, H: int, color: tuple[int, int, int]) -> None:
        for _ in range(8):
            x0 = random.randint(0, W)
            y0 = random.randint(0, H)
            points = [(x0, y0)]
            x, y = x0, y0
            for _ in range(6):
                x += random.randint(-60, 60)
                y += random.randint(20, 60)
                points.append((x, y))
            if len(points) > 1:
                for i in range(len(points) - 1):
                    a = max(10, 50 - i * 8)
                    draw.line(points[i:i + 2], fill=(*color, a), width=max(1, 6 - i))

    # ── Ultra Rare ─────────────────────────────────────────────

    def _render_premium_discovery(self, data: dict[str, Any], *, ultra: bool = False,
                                  rare_variant: bool = False, event_variant: bool = False,
                                  boss_variant: bool = False) -> BytesIO:
        cfg = self.layout["card"]
        W, H = cfg["width"], cfg["height"]
        monster = data.get("monster", {})
        rarity = str(monster.get("rarity", "Common"))
        zone_key = str(data.get("zone_key", "bloodmoon_forest"))
        zone_name = str(data.get("zone_name", "Unknown Zone"))
        rc = _col("Abyssal" if boss_variant else rarity)
        img = self._build_background(zone_key, ultra=ultra or rarity in _ULTRA_RARITIES)
        draw = ImageDraw.Draw(img)

        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        sd.rectangle((0, 0, W, H), fill=(0, 0, 0, 38 if ultra else 22))
        sd.rectangle((0, 0, 520, H), fill=(0, 0, 0, 68))
        sd.rectangle((W - 430, 0, W, H), fill=(0, 0, 0, 50))
        img.paste(shade, (0, 0), shade)

        frame_w = 4 if _RARITY_ORDER.get(rarity, 0) >= 5 else 2
        draw.rectangle((28, 28, W - 28, H - 28), outline=(*rc, 150), width=frame_w)
        draw.line((W // 2 - 260, 116, W // 2 + 260, 116), fill=(*rc, 120), width=2)

        status = str(data.get("collection_status", CollectionStatus.DUPLICATE.value))
        title = rarity.upper() + (" DISCOVERY" if status == CollectionStatus.NEW.value or ultra else " ENCOUNTER")
        title_font = _font(34 if ultra else 28, bold=True, fantasy=False)
        title_w = _tw(draw, title, title_font)
        _shadow_text(draw, (W - title_w) // 2, 58, title, title_font, rc, offset=2)
        zone_font = _font(17, bold=True)
        zone_text = zone_name.upper()
        zone_w = _tw(draw, zone_text, zone_font)
        draw.text(((W - zone_w) // 2, 100), zone_text, font=zone_font, fill=_TEXT_MUTED)

        art_size = 560 if ultra or _RARITY_ORDER.get(rarity, 0) >= 5 else 500
        art_x = W // 2 - art_size // 2
        art_y = 178 if ultra else 205
        glow = Image.new("RGBA", (art_size + 180, art_size + 180), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        max_r = (art_size + 150) // 2
        for r in range(max_r, 40, -24):
            t = r / max(1, max_r)
            a = int((34 if ultra else 24) * (1 - t))
            gd.ellipse(((art_size + 180) // 2 - r, (art_size + 180) // 2 - r,
                        (art_size + 180) // 2 + r, (art_size + 180) // 2 + r),
                       fill=(*rc, max(0, a)))
        glow = glow.filter(ImageFilter.GaussianBlur(18))
        img.paste(glow, (W // 2 - glow.width // 2, art_y - 72), glow)
        portrait = self._load_creature_asset(normalize_key(str(monster.get("name", ""))), art_size)
        if portrait:
            img.paste(portrait, (art_x, art_y), portrait)

        name = str(monster.get("name", "Unknown Spirit")).upper()
        name_font = _font(46 if len(name) < 18 else 38, bold=True, fantasy=False)
        if _tw(draw, name, name_font) > W - 520:
            name = name[:24] + "..."
        name_w = _tw(draw, name, name_font)
        name_y = 760
        _shadow_text(draw, (W - name_w) // 2, name_y, name, name_font, _TEXT_BRIGHT, offset=3)

        trait = str(monster.get("trait", ""))
        level = int(monster.get("level", 1))
        value = int(monster.get("value", 0))
        meta_font = _font(16, bold=True)
        meta = [f"LEVEL {level}", trait.upper() if trait else "WILD", f"{value:,} SOULS"]
        meta_y = name_y + 62
        total_w = sum(_tw(draw, m, meta_font) for m in meta) + 52 * (len(meta) - 1)
        meta_x = W // 2 - total_w // 2
        for idx, item in enumerate(meta):
            draw.text((meta_x, meta_y), item, font=meta_font, fill=rc if idx == 1 else _TEXT_MUTED)
            meta_x += _tw(draw, item, meta_font) + 52

        status_color = _GREEN if status == CollectionStatus.NEW.value else _TEXT_MUTED
        status_font = _font(20, bold=True)
        status_text = status.upper()
        sw = _tw(draw, status_text, status_font)
        draw.rounded_rectangle((W // 2 - sw // 2 - 18, meta_y + 40, W // 2 + sw // 2 + 18, meta_y + 72),
                               radius=8, fill=(10, 9, 16), outline=status_color)
        draw.text((W // 2 - sw // 2, meta_y + 46), status_text, font=status_font, fill=status_color)

        rewards = list(data.get("rewards", []))[:5]
        panel_x, panel_y, panel_w = 62, 190, 360
        if rewards:
            draw.text((panel_x, panel_y), "REWARDS", font=_font(17, bold=True), fill=_TEXT_MUTED)
            cy = panel_y + 34
            for rw in rewards:
                label = str(rw.get("label", "Reward"))
                amount = rw.get("amount", 0)
                color = tuple(rw.get("color", _GOLD))
                text = f"+{amount:,} {label}" if isinstance(amount, int) else f"+{amount} {label}"
                draw.text((panel_x, cy), _fit_text(draw, text, panel_w, _font(16, bold=True)), font=_font(16, bold=True), fill=color)
                cy += 30

        drop = data.get("special_drop")
        if drop:
            drop_y = 515
            drop_rarity = str(drop.get("rarity", rarity))
            dc = _col(drop_rarity)
            draw.rounded_rectangle((panel_x, drop_y, panel_x + panel_w, drop_y + 112), radius=10,
                                   fill=(10, 9, 16), outline=dc, width=2)
            draw.text((panel_x + 18, drop_y + 18), "SPECIAL DROP", font=_font(13, bold=True), fill=dc)
            drop_name = str(drop.get("name", "Unknown Drop"))
            draw.text((panel_x + 18, drop_y + 50), _fit_text(draw, drop_name, panel_w - 36, _font(19, bold=True)),
                      font=_font(19, bold=True), fill=_TEXT_BRIGHT)

        right_x, right_y = W - 376, 782
        info = [
            ("Catch", f"{float(data.get('catch_chance', 100)):.0f}%"),
            ("Rarity", rarity),
            ("Zone", zone_name),
        ]
        draw.rounded_rectangle((right_x, right_y, W - 62, right_y + 118), radius=8, fill=(10, 9, 16), outline=(54, 48, 66))
        cy = right_y + 18
        for label, value in info:
            draw.text((right_x + 18, cy), label, font=_font(13), fill=_TEXT_MUTED)
            value_font = _font(14, bold=True)
            value_text = _fit_text(draw, value, 170, value_font)
            draw.text((W - 80 - _tw(draw, value_text, value_font), cy), value_text,
                      font=value_font, fill=rc if label == "Rarity" else _TEXT_BRIGHT)
            cy += 32

        hunter = str(data.get("hunter_name", ""))
        rank = str(data.get("hunter_rank", "Hunter"))
        draw.text((62, H - 112), hunter, font=_font(19, bold=True), fill=_TEXT_BRIGHT)
        draw.text((62, H - 84), rank, font=_font(13), fill=_TEXT_MUTED)
        streak = int(data.get("hunt_streak", 0))
        if streak:
            streak_text = f"STREAK {streak}"
            draw.text((W // 2 - _tw(draw, streak_text, _font(14, bold=True)) // 2, H - 82),
                      streak_text, font=_font(14, bold=True), fill=_GOLD)
        return self._save(img)

    def _render_ultra_rare(self, data: dict[str, Any]) -> BytesIO:
        return self._render_premium_discovery(data, ultra=True)

    # ── Standard Render ────────────────────────────────────────

    def _render_standard(self, data: dict[str, Any], *, rare_variant: bool = False,
                        event_variant: bool = False, boss_variant: bool = False) -> BytesIO:
        return self._render_premium_discovery(data, rare_variant=rare_variant, event_variant=event_variant, boss_variant=boss_variant)

    # ── Multi-Hunt Shared Helpers ───────────────────────────────

    def _multi_bg(self, zone_key: str, W: int, H: int) -> Image.Image:
        """Create a blurred, darkened zone background for multi-hunt cards."""
        img = self._get_zone_background(zone_key, W, H)
        darken = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.blend(img, darken, 0.58)
        img = img.filter(ImageFilter.GaussianBlur(radius=6))
        # Subtle vignette
        vignette = self._make_vignette(W, H, strength=0.5, radius=1.3)
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, vignette)
        img = img.convert("RGB")
        return img

    def _sort_by_rarity(self, monsters: list[dict]) -> list[dict]:
        """Sort monsters by rarity (highest first), preserving order for ties."""
        return sorted(monsters, key=lambda m: _RARITY_ORDER.get(str(m.get("rarity", "Common")), 0), reverse=True)

    def _find_hero(self, monsters: list[dict]) -> int:
        """Find the index of the rarest monster (hero/focal point)."""
        best_idx = 0
        best_rank = -1
        for i, m in enumerate(monsters):
            rank = _RARITY_ORDER.get(str(m.get("rarity", "Common")), 0)
            if rank > best_rank:
                best_rank = rank
                best_idx = i
        return best_idx

    def _draw_multi_header(self, draw: ImageDraw.ImageDraw, img: Image.Image,
                           W: int, zone_name: str, count: int, lcfg: dict) -> int:
        """Draw zone title + monster count header. Returns y position after header."""
        hh = lcfg["header_height"]
        # Header background bar
        header_bg = Image.new("RGBA", (W, hh), (0, 0, 0, 0))
        hd = ImageDraw.Draw(header_bg)
        for y in range(hh):
            t = y / max(1, hh - 1)
            a = int(max(0, 80 * (1 - t)))
            hd.line((0, y, W, y), fill=(0, 0, 0, a))
        img.paste(header_bg, (0, 0), header_bg)

        # Zone name
        font_title = _font(lcfg["title_font"], bold=True, fantasy=False)
        zone_text = zone_name.upper()
        tw = _tw(draw, zone_text, font_title)
        _shadow_text(draw, (W - tw) // 2, 20, zone_text, font_title, _TEXT_BRIGHT, offset=2)

        # Separator line
        sep_y = 58
        draw.line((W // 4, sep_y, W * 3 // 4, sep_y), fill=(*_GOLD, 120), width=1)

        # Monster count
        font_count = _font(lcfg["count_font"], bold=True)
        count_text = f"{count} MONSTER{'S' if count != 1 else ''} FOUND"
        cw = _tw(draw, count_text, font_count)
        _shadow_text(draw, (W - cw) // 2, 68, count_text, font_count, _GOLD, offset=2)

        # Subtitle separator
        sep_y2 = 102
        draw.line((W // 3, sep_y2, W * 2 // 3, sep_y2), fill=(*_BORDER, 100), width=1)

        return hh + 10

    def _draw_monster_cell(self, draw: ImageDraw.ImageDraw, img: Image.Image,
                           cx: int, cy: int, mon: dict, cell_cfg: dict,
                           is_hero: bool = False) -> None:
        """Draw a single monster cell at the given center position."""
        cell_w = cell_cfg["width"]
        cell_h = cell_cfg["height"]
        sprite_sz = cell_cfg["sprite_size"]
        rarity = str(mon.get("rarity", "Common"))
        name = str(mon.get("name", "Unknown"))
        value = mon.get("value", 0)
        status = str(mon.get("collection_status", "DUPLICATE"))
        rc = _col(rarity)
        gc = _glow_col(rarity)
        rarity_rank = _RARITY_ORDER.get(rarity, 0)

        # ── Glow behind cell for Epic+ ──
        if rarity_rank >= 3:  # Epic+
            glow_size = cell_w + 40 + (rarity_rank - 3) * 16
            glow_img = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_img)
            for r in range(glow_size // 2, 0, -8):
                t = r / (glow_size // 2)
                a = int(max(1, (30 + (rarity_rank - 3) * 8) * (1 - t * t)))
                gd.ellipse((glow_size // 2 - r, glow_size // 2 - r,
                           glow_size // 2 + r, glow_size // 2 + r),
                          fill=(*gc, a))
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=12))
            img.paste(glow_img, (cx - glow_size // 2, cy - glow_size // 2), glow_img)

        # ── Cell background panel ──
        border_w = 2 if rarity_rank < 4 else 3 if rarity_rank < 7 else 4
        cell = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))
        cd = ImageDraw.Draw(cell)
        # Fill with slightly tinted panel
        fill_r = _lerp_color(_PANEL, rc, 0.06)
        cd.rounded_rectangle((0, 0, cell_w - 1, cell_h - 1), radius=12,
                            fill=(*fill_r, 210), outline=rc, width=border_w)

        # Inner highlight at top
        for i in range(min(20, cell_h // 4)):
            a = max(0, 20 - i * 2)
            cd.line((4, i + 4, cell_w - 4, i + 4), fill=(*rc, a))

        img.paste(cell, (cx - cell_w // 2, cy - cell_h // 2), cell)

        # ── Particles for Legendary+ ──
        if rarity_rank >= 4:
            pcount = min(12, 3 + (rarity_rank - 4) * 2)
            for _ in range(pcount):
                px = cx + random.randint(-cell_w // 2, cell_w // 2)
                py = cy + random.randint(-cell_h // 2, cell_h // 2)
                s = random.randint(1, 3)
                a = random.randint(40, 130)
                p = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0))
                pd = ImageDraw.Draw(p)
                pd.ellipse((0, 0, s * 2, s * 2), fill=(*rc, a))
                img.paste(p, (px, py), p)

        # ── Sprite ──
        sprite = self._load_creature_asset(normalize_key(name), sprite_sz)
        if sprite:
            s_x = cx - sprite_sz // 2
            s_y = cy - sprite_sz // 2 - (cell_h // 8)
            img.paste(sprite, (s_x, s_y), sprite)
        else:
            # Placeholder silhouette
            ph = Image.new("RGBA", (sprite_sz, sprite_sz), (0, 0, 0, 0))
            phd = ImageDraw.Draw(ph)
            phd.rounded_rectangle((8, 8, sprite_sz - 8, sprite_sz - 8), radius=12,
                                 fill=(*_PANEL2, 180), outline=(*_BORDER, 100))
            phd.text((sprite_sz // 2 - 4, sprite_sz // 2 - 8), "?",
                    font=_font(sprite_sz // 3, bold=True), fill=_TEXT_MUTED)
            s_x = cx - sprite_sz // 2
            s_y = cy - sprite_sz // 2 - (cell_h // 8)
            img.paste(ph, (s_x, s_y), ph)

        # ── Name ──
        font_name = _font(cell_cfg["name_font"], bold=True)
        display_name = name[:18] if len(name) > 18 else name
        nw = _tw(draw, display_name, font_name)
        name_y = cy + sprite_sz // 2 - (cell_h // 12)
        _shadow_text(draw, cx - nw // 2, name_y, display_name, font_name, _TEXT_BRIGHT, offset=1)

        # ── Value ──
        font_val = _font(cell_cfg["val_font"], bold=True)
        val_text = f"+{value:,} Souls"
        vw = _tw(draw, val_text, font_val)
        draw.text((cx - vw // 2, name_y + cell_cfg["name_font"] + 6), val_text,
                 font=font_val, fill=_GOLD)

        # ── Rarity tag ──
        font_rarity = _font(cell_cfg["rarity_font"], bold=True)
        rarity_text = rarity.upper()
        rw = _tw(draw, rarity_text, font_rarity)
        rarity_y = name_y + cell_cfg["name_font"] + cell_cfg["val_font"] + 12
        # Rarity pill background
        pill_w = rw + 16
        pill_h = cell_cfg["rarity_font"] + 8
        pill_x = cx - pill_w // 2
        pill = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
        pld = ImageDraw.Draw(pill)
        pld.rounded_rectangle((0, 0, pill_w - 1, pill_h - 1), radius=pill_h // 2,
                             fill=(*rc, 40), outline=(*rc, 150), width=1)
        img.paste(pill, (pill_x, rarity_y), pill)
        draw.text((cx - rw // 2, rarity_y + 3), rarity_text, font=font_rarity, fill=rc)

        # ── Collection status badge ──
        badge_y = rarity_y + pill_h + 8
        if status == "NEW DISCOVERY" or status == "NEW":
            badge_text = "✨ NEW"
            badge_font = _font(cell_cfg["rarity_font"], bold=True)
            bw = _tw(draw, badge_text, badge_font)
            # Sparkle badge with glow
            badge_bg = Image.new("RGBA", (bw + 14, cell_cfg["rarity_font"] + 10), (0, 0, 0, 0))
            bd = ImageDraw.Draw(badge_bg)
            bd.rounded_rectangle((0, 0, bw + 13, cell_cfg["rarity_font"] + 9), radius=6,
                                fill=(*_GREEN, 50), outline=(*_GREEN, 180), width=1)
            img.paste(badge_bg, (cx - (bw + 14) // 2, badge_y), badge_bg)
            draw.text((cx - bw // 2, badge_y + 4), badge_text, font=badge_font, fill=_GREEN)
        else:
            badge_text = "DUPLICATE"
            badge_font = _font(max(10, cell_cfg["rarity_font"] - 1), bold=False)
            bw = _tw(draw, badge_text, badge_font)
            draw.text((cx - bw // 2, badge_y + 2), badge_text, font=badge_font, fill=_TEXT_MUTED)

    def _draw_summary_panel(self, draw: ImageDraw.ImageDraw, img: Image.Image,
                            W: int, y: int, data: dict[str, Any], lcfg: dict) -> int:
        """Draw the summary panel with totals, rewards, and special drops. Returns height used."""
        pad = lcfg["summary_pad"]
        font_header = _font(lcfg["summary_font"], bold=True)
        font_label = _font(lcfg["summary_label_font"], bold=False)
        font_val = _font(lcfg["summary_label_font"], bold=True)

        total_souls = data.get("total_souls", 0)
        rewards = data.get("rewards", [])
        special_drop = data.get("special_drop")

        # Calculate panel height
        line_h = lcfg["summary_label_font"] + 10
        reward_lines = len(rewards) if rewards else 0
        special_lines = 3 if special_drop else 0
        content_h = 40 + reward_lines * line_h + special_lines * line_h + pad * 2
        panel_w = min(W - 80, 800)
        panel_x = (W - panel_w) // 2

        # Panel background
        panel = Image.new("RGBA", (panel_w, content_h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(panel)
        pd.rounded_rectangle((0, 0, panel_w - 1, content_h - 1), radius=12,
                            fill=(*_PANEL, 220), outline=_BORDER, width=1)
        # Top accent line
        pd.line((12, 3, panel_w - 12, 3), fill=(*_GOLD, 80), width=1)
        img.paste(panel, (panel_x, y), panel)

        # Header
        header = "TOTAL REWARDS"
        hw = _tw(draw, header, font_header)
        _shadow_text(draw, (W - hw) // 2, y + pad, header, font_header, _GOLD, offset=1)

        # Rewards list
        cy = y + pad + 34
        if rewards:
            for rw in rewards:
                label = str(rw.get("label", ""))
                amount = rw.get("amount", 0)
                color = tuple(rw.get("color", _TEXT))
                line = f"+{amount:,} {label}" if amount else label
                lw = _tw(draw, line, font_val)
                draw.text(((W - lw) // 2, cy), line, font=font_val, fill=color)
                cy += line_h
        else:
            # Fallback: just show souls
            souls_text = f"+{total_souls:,} Souls"
            sw = _tw(draw, souls_text, font_val)
            draw.text(((W - sw) // 2, cy), souls_text, font=font_val, fill=_GOLD)
            cy += line_h

        # Special drop section
        if special_drop:
            cy += 6
            sep_w = panel_w // 2
            draw.line(((W - sep_w) // 2, cy, (W + sep_w) // 2, cy),
                     fill=(*_BORDER, 120), width=1)
            cy += 8

            drop_type = str(special_drop.get("type", ""))
            drop_name = str(special_drop.get("name", ""))
            drop_rarity = str(special_drop.get("rarity", "Legendary"))
            drc = _col(drop_rarity)

            if drop_type == "weapon":
                drop_header = "⚔️ SPECIAL DROP"
            elif drop_type == "relic":
                drop_header = "📦 RELIC CACHE FOUND"
            else:
                drop_header = "⭐ SPECIAL DROP"

            dhw = _tw(draw, drop_header, font_val)
            draw.text(((W - dhw) // 2, cy), drop_header, font=font_val, fill=drc)
            cy += line_h

            dnw = _tw(draw, drop_name, font_header)
            _shadow_text(draw, (W - dnw) // 2, cy, drop_name, font_header, _TEXT_BRIGHT, offset=1)
            cy += line_h

        return content_h

    # ── Loot Grid (2-5 monsters) ──────────────────────────────

    def _render_loot_grid(self, data: dict[str, Any]) -> BytesIO:
        lcfg = _LOOT_GRID_LAYOUT
        W = lcfg["card_width"]
        monsters: list[dict] = data.get("monsters", [])
        count = len(monsters)
        zone_key = str(data.get("zone_key", "forgotten_woods"))
        zone_name = str(data.get("zone_name", zone_key.replace("_", " ").title()))

        # Determine hero (rarest) monster
        hero_idx = self._find_hero(monsters)
        hero_rarity_rank = _RARITY_ORDER.get(str(monsters[hero_idx].get("rarity", "Common")), 0)
        has_hero = hero_rarity_rank >= 2  # Rare+ gets hero treatment

        # Calculate grid dimensions
        cell_n = lcfg["cell_normal"]
        cell_h_cfg = lcfg["cell_hero"]
        cols = lcfg["grid_cols"]
        gap_x = lcfg["gap_x"]
        gap_y = lcfg["gap_y"]

        # Build row structure
        rows: list[list[tuple[int, bool]]] = []  # list of rows, each row = list of (monster_idx, is_hero)
        current_row: list[tuple[int, bool]] = []
        for i in range(count):
            is_hero = (i == hero_idx and has_hero)
            current_row.append((i, is_hero))
            if len(current_row) >= cols:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)

        # Calculate total height
        header_y = lcfg["header_height"] + 10
        grid_h = 0
        for row in rows:
            row_has_hero = any(h for _, h in row)
            rh = cell_h_cfg["height"] if row_has_hero else cell_n["height"]
            grid_h += rh + gap_y
        grid_h -= gap_y  # remove last gap

        # Tight fit around the grid
        total_h = header_y + lcfg["grid_pad_y"] + grid_h + lcfg["grid_pad_y"]
        H = min(1800, total_h)

        img = self._multi_bg(zone_key, W, H)
        draw = ImageDraw.Draw(img)

        # Ambient particles
        self._draw_ambient_effects(draw, img, zone_key)

        # Header
        self._draw_multi_header(draw, img, W, zone_name, count, lcfg)

        # Draw monster grid
        cy = header_y + lcfg["grid_pad_y"]
        for row in rows:
            row_has_hero = any(h for _, h in row)
            cfg = cell_h_cfg if row_has_hero else cell_n
            rh = cfg["height"]

            # Center this row
            row_width = sum(
                (cell_h_cfg["width"] if h else cell_n["width"]) for _, h in row
            ) + gap_x * (len(row) - 1)
            rx = (W - row_width) // 2

            for mi, is_hero in row:
                c = cell_h_cfg if is_hero else cell_n
                cw = c["width"]
                ccx = rx + cw // 2
                ccy = cy + rh // 2
                self._draw_monster_cell(draw, img, ccx, ccy, monsters[mi], c, is_hero)
                rx += cw + gap_x

            cy += rh + gap_y

        return self._save(img)

    # ── Compact Grid (6-10 monsters) ──────────────────────────

    def _render_compact_grid(self, data: dict[str, Any]) -> BytesIO:
        lcfg = _COMPACT_GRID_LAYOUT
        W = lcfg["card_width"]
        monsters: list[dict] = data.get("monsters", [])
        count = len(monsters)
        zone_key = str(data.get("zone_key", "forgotten_woods"))
        zone_name = str(data.get("zone_name", zone_key.replace("_", " ").title()))

        hero_idx = self._find_hero(monsters)
        hero_rarity_rank = _RARITY_ORDER.get(str(monsters[hero_idx].get("rarity", "Common")), 0)
        has_hero = hero_rarity_rank >= 2

        cell_n = lcfg["cell_normal"]
        cell_h_cfg = lcfg["cell_hero"]
        cols = lcfg["grid_cols"]
        gap_x = lcfg["gap_x"]
        gap_y = lcfg["gap_y"]

        # Build rows
        rows: list[list[tuple[int, bool]]] = []
        current_row: list[tuple[int, bool]] = []
        for i in range(count):
            is_hero = (i == hero_idx and has_hero)
            current_row.append((i, is_hero))
            if len(current_row) >= cols:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)

        header_y = lcfg["header_height"] + 10
        grid_h = 0
        for row in rows:
            row_has_hero = any(h for _, h in row)
            rh = cell_h_cfg["height"] if row_has_hero else cell_n["height"]
            grid_h += rh + gap_y
        grid_h -= gap_y

        total_h = header_y + lcfg["grid_pad_y"] + grid_h + lcfg["grid_pad_y"]
        H = min(1600, total_h)

        img = self._multi_bg(zone_key, W, H)
        draw = ImageDraw.Draw(img)
        self._draw_ambient_effects(draw, img, zone_key)
        self._draw_multi_header(draw, img, W, zone_name, count, lcfg)

        cy = header_y + lcfg["grid_pad_y"]
        for row in rows:
            row_has_hero = any(h for _, h in row)
            cfg = cell_h_cfg if row_has_hero else cell_n
            rh = cfg["height"]

            row_width = sum(
                (cell_h_cfg["width"] if h else cell_n["width"]) for _, h in row
            ) + gap_x * (len(row) - 1)
            rx = (W - row_width) // 2

            for mi, is_hero in row:
                c = cell_h_cfg if is_hero else cell_n
                cw = c["width"]
                ccx = rx + cw // 2
                ccy = cy + rh // 2
                self._draw_monster_cell(draw, img, ccx, ccy, monsters[mi], c, is_hero)
                rx += cw + gap_x

            cy += rh + gap_y

        return self._save(img)

    # ── Mass Hunt / Inventory Summary (10+ monsters) ──────────

    def _render_mass_hunt(self, data: dict[str, Any]) -> BytesIO:
        lcfg = _MASS_HUNT_LAYOUT
        W = lcfg["card_width"]
        monsters: list[dict] = data.get("monsters", [])
        count = len(monsters)
        zone_key = str(data.get("zone_key", "forgotten_woods"))
        zone_name = str(data.get("zone_name", zone_key.replace("_", " ").title()))

        hero_idx = self._find_hero(monsters)

        # Calculate height
        header_h = lcfg["header_height"] + 10
        row_h = lcfg["row_height"]
        hero_h = lcfg["hero_row_height"]
        rows_h = (count - 1) * row_h + hero_h + 16  # 16 for hero separator
        
        # Remove summary space
        total_h = header_h + 20 + rows_h + 20
        H = min(lcfg["max_height"], total_h)

        img = self._multi_bg(zone_key, W, H)
        draw = ImageDraw.Draw(img)
        self._draw_ambient_effects(draw, img, zone_key)
        self._draw_multi_header(draw, img, W, zone_name, count, lcfg)

        # Sort by rarity for display
        sorted_monsters = self._sort_by_rarity(monsters)
        pad_x = lcfg["row_pad_x"]
        list_w = W - pad_x * 2

        cy = header_h + 20
        for idx, mon in enumerate(sorted_monsters):
            is_hero = (mon is monsters[hero_idx])
            rarity = str(mon.get("rarity", "Common"))
            name = str(mon.get("name", "Unknown"))
            value = mon.get("value", 0)
            status = str(mon.get("collection_status", "DUPLICATE"))
            rc = _col(rarity)
            gc = _glow_col(rarity)
            rarity_rank = _RARITY_ORDER.get(rarity, 0)

            if is_hero:
                rh = lcfg["hero_row_height"]
                icon_sz = lcfg["hero_icon_size"]
                fn = _font(lcfg["hero_name_font"], bold=True)
                fv = _font(lcfg["hero_val_font"], bold=True)
                fr = _font(lcfg["hero_rarity_font"], bold=True)
            else:
                rh = lcfg["row_height"]
                icon_sz = lcfg["icon_size"]
                fn = _font(lcfg["name_font"], bold=True)
                fv = _font(lcfg["val_font"], bold=True)
                fr = _font(lcfg["rarity_font"], bold=True)

            if cy + rh > H - 20:
                # Overflow: draw "and X more..." line
                remaining = count - idx
                more_font = _font(lcfg["name_font"], bold=True)
                more_text = f"... and {remaining} more monsters"
                mw = _tw(draw, more_text, more_font)
                draw.text(((W - mw) // 2, cy + 8), more_text, font=more_font, fill=_TEXT_MUTED)
                cy += rh
                break

            # Row background
            row_bg = Image.new("RGBA", (list_w, rh), (0, 0, 0, 0))
            rd = ImageDraw.Draw(row_bg)
            fill_alpha = 180 if is_hero else 140
            fill_color = _lerp_color(_PANEL, rc, 0.08 if is_hero else 0.03)
            rd.rounded_rectangle((0, 0, list_w - 1, rh - 1), radius=8,
                                fill=(*fill_color, fill_alpha),
                                outline=(*rc, 120 if is_hero else 50),
                                width=2 if is_hero else 1)

            # Glow for hero row
            if is_hero and rarity_rank >= 3:
                for i in range(4, 0, -1):
                    a = max(5, 25 - i * 6)
                    rd.rounded_rectangle((i, i, list_w - 1 - i, rh - 1 - i), radius=8 + i,
                                        outline=(*rc, a), width=2)

            img.paste(row_bg, (pad_x, cy), row_bg)

            # Rarity color bar (left edge)
            bar_w = 4 if not is_hero else 6
            draw.rounded_rectangle((pad_x, cy + 4, pad_x + bar_w, cy + rh - 4),
                                  radius=2, fill=rc)

            # Monster icon
            icon_x = pad_x + 16
            icon_y_center = cy + rh // 2
            sprite = self._load_creature_asset(normalize_key(name), icon_sz)
            if sprite:
                img.paste(sprite, (icon_x, icon_y_center - icon_sz // 2), sprite)

            # Name
            name_x = icon_x + icon_sz + 14
            display_name = name[:24] if len(name) > 24 else name
            nw = _tw(draw, display_name, fn)
            _shadow_text(draw, name_x, icon_y_center - fn.size // 2 - 2,
                        display_name, fn, _TEXT_BRIGHT, offset=1)

            # Rarity tag
            rarity_x = name_x + nw + 16
            rarity_text = rarity.upper()
            rw_text = _tw(draw, rarity_text, fr)
            # Small pill
            pill_w = rw_text + 12
            pill_h = fr.size + 6
            pill_y = icon_y_center - pill_h // 2
            pill = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
            pld = ImageDraw.Draw(pill)
            pld.rounded_rectangle((0, 0, pill_w - 1, pill_h - 1), radius=pill_h // 2,
                                 fill=(*rc, 35), outline=(*rc, 120), width=1)
            img.paste(pill, (rarity_x, pill_y), pill)
            draw.text((rarity_x + 6, pill_y + 2), rarity_text, font=fr, fill=rc)

            # Value (right-aligned)
            val_text = f"+{value:,}"
            vw = _tw(draw, val_text, fv)
            val_x = pad_x + list_w - vw - 16
            draw.text((val_x, icon_y_center - fv.size // 2 - 2), val_text, font=fv, fill=_GOLD)

            # Collection status (right of value area, small)
            if status in ("NEW DISCOVERY", "NEW"):
                stat_text = "✨"
                stat_font = _font(max(10, lcfg["rarity_font"] - 2), bold=True)
                stw = _tw(draw, stat_text, stat_font)
                draw.text((val_x - stw - 10, icon_y_center - stat_font.size // 2),
                         stat_text, font=stat_font, fill=_GREEN)

            cy += rh + 3

        return self._save(img)

    # ── Asset Loading ──────────────────────────────────────────

    def _load_asset(self, kind: str, key: str, size: tuple[int, int]) -> Image.Image | None:
        path = get_asset_file_path(kind, key)
        if path and path.exists():
            try:
                a = Image.open(path).convert("RGBA")
                a.thumbnail(size, Image.Resampling.LANCZOS)
                c = Image.new("RGBA", size, (0, 0, 0, 0))
                c.alpha_composite(a, ((size[0] - a.width) // 2, (size[1] - a.height) // 2))
                return c
            except OSError:
                pass
        return None

    def _load_creature_asset(self, key: str, target_size: int) -> Image.Image | None:
        path = get_creature_asset_path(key)
        if path and path.exists():
            try:
                a = Image.open(path).convert("RGBA")
                default_scale = int(self.layout["monster_portrait"].get("nearest_scale", 4))
                scale_factor = max(default_scale, max(1, target_size // max(1, max(a.width, a.height))))
                nearest_w = a.width * scale_factor
                nearest_h = a.height * scale_factor
                if nearest_w > target_size * 2:
                    scale_factor = max(1, target_size // max(a.width, a.height))
                    nearest_w = a.width * scale_factor
                    nearest_h = a.height * scale_factor
                upscaled = a.resize((nearest_w, nearest_h), Image.NEAREST)
                c = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
                ox = (target_size - upscaled.width) // 2
                oy = (target_size - upscaled.height) // 2
                c.alpha_composite(upscaled, (ox, oy))
                return c
            except OSError:
                pass
        return None

    # ── Output ─────────────────────────────────────────────────

    def _save(self, img: Image.Image) -> BytesIO:
        b = BytesIO()
        img.save(b, format="PNG")
        b.seek(0)
        return b
