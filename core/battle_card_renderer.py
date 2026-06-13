from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from core import card_ui as cui
from core.content_config import ASSET_DIR, get_asset_file_path, get_creature_asset_path
from core.rpg_data import normalize_key


_RARITY_COLORS: dict[str, tuple[int, int, int]] = {
    "Common": (139, 148, 158), "Uncommon": (74, 222, 128),
    "Rare": (56, 189, 248), "Epic": (167, 139, 250),
    "Legendary": (250, 204, 21), "Mythic": (251, 113, 133),
    "Ancient": (249, 115, 22), "Patreon": (255, 66, 77),
    "Divine": (254, 243, 199),
    "Eldritch": (34, 211, 238), "Abyssal": (130, 90, 200),
}

_ULTRA_RARITIES = {"Divine", "Eldritch", "Abyssal"}

_PANEL = (30, 28, 44)
_PANEL_DARK = (22, 20, 36)
_BORDER = (55, 50, 72)
_TEXT = (220, 215, 208)
_TEXT_BRIGHT = (255, 255, 255)
_TEXT_MUTED = (130, 125, 120)
_GOLD = (255, 215, 80)
_GOLD_BRIGHT = (255, 230, 130)
_RED = (235, 80, 90)
_GREEN = (90, 225, 130)
_BLUE = (80, 175, 245)
_CYAN = (34, 211, 238)
_PURPLE = (180, 110, 255)
_ORANGE = (255, 165, 55)
_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)

_ZONE_BGS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
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

_NPC_CREATURE_FALLBACKS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("hound", "wolf"), "ribcage_hound"),
    (("wraith", "spirit", "phantom"), "lost_soul"),
    (("reaper", "stalker"), "bone_stalker"),
    (("knight", "soldier", "blade"), "spectre_knight"),
    (("leech", "watcher"), "mire_wisp"),
    (("golem", "behemoth", "tyrant"), "ghostlight_behemoth"),
    (("terror", "monarch", "sovereign"), "void_lord_asterion"),
    (("herald", "void"), "void_thread_spider"),
)

_RARITY_FALLBACK_ASSET: dict[str, str] = {
    "Common": "skeleton",
    "Uncommon": "bone_stalker",
    "Rare": "grave_warden",
    "Epic": "spectre_knight",
    "Legendary": "abyssal_hound",
    "Mythic": "soulreaper_wyvern",
    "Ancient": "ancient_starved_dragon",
    "Patreon": "ancient_starved_dragon",
    "Divine": "celestial_judge",
    "Eldritch": "eater_beneath_names",
    "Abyssal": "abyssal_godling",
}

_FONT_CACHE: dict[str, ImageFont.ImageFont] = {}
_TEXTURE_CACHE: dict[Path, Image.Image | None] = {}

W, H = 1600, 900
_BATTLE_BG = ASSET_DIR / "ui" / "battle_bg_abyssia_pixel.png"
_BATTLE_PANEL_BG = ASSET_DIR / "ui" / "battle_panel_bg_abyssia_pixel.png"


def _load_texture(path: Path) -> Image.Image | None:
    if path not in _TEXTURE_CACHE:
        try:
            _TEXTURE_CACHE[path] = Image.open(path).convert("RGB") if path.exists() else None
        except OSError:
            _TEXTURE_CACHE[path] = None
    cached = _TEXTURE_CACHE.get(path)
    return cached.copy() if cached is not None else None


def _battle_background(w: int, h: int) -> Image.Image:
    texture = _load_texture(_BATTLE_BG)
    if texture is not None:
        bg = cui.cover_resize(texture, (w, h)).convert("RGBA")
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 8))
        bg.alpha_composite(overlay)
        return bg
    return Image.new("RGBA", (w, h), (7, 6, 13, 255))


def _draw_cut_outline(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int, int],
    *,
    cut: int = 14,
    width: int = 2,
) -> None:
    for offset in range(max(1, width)):
        inner = (box[0] + offset, box[1] + offset, box[2] - offset, box[3] - offset)
        pts = cui.cut_box_points(inner, max(0, cut - offset))
        draw.line(pts + [pts[0]], fill=color, width=1)


def _fill_cut_box(
    img: Image.Image,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    *,
    cut: int = 10,
) -> None:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.polygon(cui.cut_box_points(box, cut), fill=fill)
    img.alpha_composite(layer)


def _draw_clean_portrait_frame(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    border: tuple[int, int, int],
    accent: tuple[int, int, int],
    *,
    cut: int = 10,
) -> None:
    x1, y1, x2, y2 = box
    _fill_cut_box(img, (x1 + 3, y1 + 4, x2 + 3, y2 + 4), (0, 0, 0, 120), cut=cut)
    _fill_cut_box(img, box, (4, 5, 11, 210), cut=cut)
    _draw_cut_outline(draw, box, (*border, 225), cut=cut, width=1)
    inner = (x1 + 5, y1 + 5, x2 - 5, y2 - 5)
    _draw_cut_outline(draw, inner, (*accent, 130), cut=max(3, cut - 5), width=1)


def _draw_battle_panel(
    img: Image.Image,
    box: tuple[int, int, int, int],
    border: tuple[int, int, int],
    *,
    fill: tuple[int, int, int, int] = (6, 6, 12, 202),
    cut: int = 14,
    texture_alpha: int = 255,
    shadow: bool = True,
) -> None:
    x1, y1, x2, y2 = box
    width, height = x2 - x1, y2 - y1
    if width <= 0 or height <= 0:
        return
    draw = ImageDraw.Draw(img)
    if shadow:
        cui.draw_pixel_box(draw, (x1 + 5, y1 + 6, x2 + 5, y2 + 6), (0, 0, 0, 82), None, cut=cut)

    mask = cui.pixel_box_mask((width, height), cut=cut)
    texture = _load_texture(_BATTLE_PANEL_BG)
    if texture is not None and texture_alpha > 0:
        panel = cui.cover_resize(texture, (width, height)).convert("RGBA")
        panel = ImageEnhance.Brightness(panel).enhance(1.08)
        panel = ImageEnhance.Contrast(panel).enhance(0.92)
        panel.putalpha(mask.point(lambda p: int(p * texture_alpha / 255)))
        tint = Image.new("RGBA", (width, height), fill)
        tint.putalpha(mask.point(lambda p: int(p * fill[3] / 255)))
        panel.alpha_composite(tint)
    else:
        panel = Image.new("RGBA", (width, height), fill)
        panel.putalpha(mask.point(lambda p: int(p * fill[3] / 255)))
    img.alpha_composite(panel, (x1, y1))
    _draw_cut_outline(draw, box, (*border, 185), cut=cut, width=1)


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    k = f"f_{size}_{bold}"
    if k in _FONT_CACHE:
        return _FONT_CACHE[k]
    candidates = [
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "consolab.ttf" if bold else "consola.ttf",
        "courbd.ttf" if bold else "cour.ttf",
    ]
    candidates.append("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    font_dir = Path("C:/Windows/Fonts")
    for name in candidates:
        try:
            f = ImageFont.truetype(str(font_dir / name), size)
            _FONT_CACHE[k] = f
            return f
        except OSError:
            continue
    f = ImageFont.load_default()
    _FONT_CACHE[k] = f
    return f


def _tw(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def _col(r: str | None) -> tuple[int, int, int]:
    return _RARITY_COLORS.get(str(r or "Common"), (139, 148, 158))


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _shadow_text(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font: ImageFont.ImageFont,
                 color: tuple[int, int, int], offset: int = 2) -> None:
    draw.text((x + offset, y + offset), text, font=font, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=font, fill=color)


def _fit_name(draw: ImageDraw.ImageDraw, text: str, max_w: int, font: ImageFont.ImageFont) -> str:
    if _tw(draw, text, font) <= max_w:
        return text
    for i in range(len(text), 0, -1):
        s = text[:i] + "..."
        if _tw(draw, s, font) <= max_w:
            return s
    return "..."


def _compact_num(value: int | float | str) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000_000:
        text = f"{number / 1_000_000_000:.1f}B"
    elif number >= 1_000_000:
        text = f"{number / 1_000_000:.1f}M"
    elif number >= 10_000:
        text = f"{number / 1_000:.1f}K"
    else:
        return f"{sign}{int(number):,}"
    return sign + text.replace(".0", "")


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int, size: int, *, bold: bool = True, min_size: int = 9) -> ImageFont.ImageFont:
    chosen = _font(size, bold=bold)
    while getattr(chosen, "size", size) > min_size and _tw(draw, text, chosen) > max_w:
        chosen = _font(chosen.size - 1, bold=bold)
    return chosen


def _draw_battle_bar(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    cur: int,
    mx: int,
    color: tuple[int, int, int],
    label: str,
) -> None:
    x1, y1, x2, y2 = box
    cut = max(3, min(7, (y2 - y1) // 3))
    cui.draw_pixel_box(draw, box, (7, 6, 14, 236), (*_BORDER, 190), cut=cut, width=1)
    ratio = max(0.0, min(1.0, cur / max(1, mx)))
    fill_w = int(max(0, x2 - x1 - 6) * ratio)
    if fill_w > 0:
        fill = (x1 + 3, y1 + 3, min(x2 - 3, x1 + 3 + fill_w), y2 - 3)
        cui.draw_pixel_box(draw, fill, (*color, 224), None, cut=max(1, cut - 2))
        for sx in range(fill[0] + 5, fill[2] - 3, 14):
            draw.rectangle((sx, fill[1] + 2, sx + 5, fill[1] + 4), fill=(*_WHITE, 60))
    font = _fit_font(draw, label, x2 - x1 - 12, max(11, y2 - y1 - 7), bold=True, min_size=8)
    tw = _tw(draw, label, font)
    tx = x1 + (x2 - x1 - tw) // 2
    ty = y1 + max(0, (y2 - y1 - font.size) // 2) - 1
    _shadow_text(draw, tx, ty, label, font, _WHITE, offset=1)


def _draw_battle_badge(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    color: tuple[int, int, int],
) -> None:
    cui.draw_pixel_box(draw, box, (3, 4, 9, 208), (*color, 190), cut=5, width=1)
    font = _fit_font(draw, label, box[2] - box[0] - 14, 12, bold=True, min_size=8)
    tw = _tw(draw, label, font)
    tx = box[0] + (box[2] - box[0] - tw) // 2
    ty = box[1] + max(0, (box[3] - box[1] - font.size) // 2) - 1
    _shadow_text(draw, tx, ty, label, font, _TEXT_BRIGHT, offset=1)


def _creature_asset_candidates(cr: dict[str, Any], name: str, rarity: str) -> list[str]:
    candidates: list[str] = []
    for field in ("image_key", "asset_key", "image"):
        value = str(cr.get(field, "") or "").strip()
        if value:
            candidates.append(normalize_key(Path(value).stem))
    candidates.append(normalize_key(name))
    lowered = name.lower()
    for needles, fallback in _NPC_CREATURE_FALLBACKS:
        if any(needle in lowered for needle in needles):
            candidates.append(fallback)
            break
    candidates.append(_RARITY_FALLBACK_ASSET.get(rarity, "skeleton"))
    unique: list[str] = []
    for key in candidates:
        if key and key not in unique:
            unique.append(key)
    return unique


class BattleCardRenderer:

    def __init__(self, layout_config_path: str | Path | None = None) -> None:
        self.layout = self._load_layout(layout_config_path)

    def _load_layout(self, path: str | Path | None) -> dict[str, Any]:
        default = str(ASSET_DIR / "battle_card_layout.json")
        p = Path(path or default)
        if p.exists():
            return json.loads(p.read_text("utf-8"))
        return {}

    # ── Main render methods ────────────────────────────

    def render_battle_result(self, data: dict[str, Any]) -> BytesIO:
        return self._render_cards_only(data)

    def render_battle_frame(self, data: dict[str, Any]) -> BytesIO:
        return self._render_cards_only(data)

    def _render_cards_only(self, data: dict[str, Any]) -> BytesIO:
        left_team = data.get("player_team", [])[:3]
        right_team = data.get("enemy_team", [])[:3]
        left_hp = data.get("player_hp", [])
        right_hp = data.get("enemy_hp", [])
        left_wp = data.get("player_wp", [])
        right_wp = data.get("enemy_wp", [])

        W, H = 1600, 900
        top_margin = 16
        bottom_margin = 16
        side_margin = 32
        header_h = 38
        card_gap = 10
        team_gap = 24
        col_w = (W - side_margin * 2 - team_gap) // 2
        col_left_x = side_margin
        col_right_x = col_left_x + col_w + team_gap
        usable_h = H - top_margin - bottom_margin - header_h
        card_h = (usable_h - card_gap * 2) // 3
        card_start_y = top_margin + header_h

        img = _battle_background(W, H)
        vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        vd.rectangle((0, 0, W, H), outline=(0, 0, 0, 150), width=14)
        img.alpha_composite(vignette)
        draw = ImageDraw.Draw(img)

        if data.get("has_ultra_rare"):
            self._apply_ultra_border_custom(img, W, H)

        player_name = str(data.get("player_name", "Hunter"))
        enemy_name = str(data.get("enemy_name", "Opponent"))
        won = data.get("won")

        from core.battle_engine import compute_display_stats
        left_max_total = sum(max(1, compute_display_stats(cr).get("HP", int(cr.get("hp", 1)))) for cr in left_team)
        right_max_total = sum(max(1, compute_display_stats(cr).get("HP", int(cr.get("hp", 1)))) for cr in right_team)
        left_cur_total = sum(max(0, int(left_hp[i] if i < len(left_hp) else compute_display_stats(left_team[i]).get("HP", int(left_team[i].get("hp", 1))))) for i in range(len(left_team)))
        right_cur_total = sum(max(0, int(right_hp[i] if i < len(right_hp) else compute_display_stats(right_team[i]).get("HP", int(right_team[i].get("hp", 1))))) for i in range(len(right_team)))
        left_ratio = left_cur_total / max(1, left_max_total)
        right_ratio = right_cur_total / max(1, right_max_total)
        left_leading = left_ratio >= right_ratio

        name_font = _font(18, bold=True)
        rank_font = _font(11)
        left_name = _fit_name(draw, player_name, col_w - 120, name_font)
        right_name = _fit_name(draw, enemy_name, col_w - 120, name_font)
        draw.text((col_left_x, top_margin), left_name, font=name_font, fill=_TEXT_BRIGHT if left_leading else _TEXT)
        draw.text((col_right_x + col_w - _tw(draw, right_name, name_font), top_margin), right_name, font=name_font, fill=_TEXT_BRIGHT if not left_leading else _TEXT)
        player_rank = str(data.get("player_rank", ""))[:34]
        enemy_rank = str(data.get("enemy_rank", ""))[:34]
        draw.text((col_left_x, top_margin + 22), player_rank, font=rank_font, fill=_TEXT_MUTED)
        draw.text((col_right_x + col_w - _tw(draw, enemy_rank, rank_font), top_margin + 22), enemy_rank, font=rank_font, fill=_TEXT_MUTED)

        bar_y = top_margin + 24
        side_w = col_w - 8
        def team_bar(x: int, cur: int, mx: int, color: tuple[int, int, int], align_right: bool = False) -> None:
            txt = f"{_compact_num(cur)}/{_compact_num(mx)}"
            _draw_battle_bar(draw, (x, bar_y, x + side_w, bar_y + 14), cur, mx, color, txt)

        team_bar(col_left_x, left_cur_total, left_max_total, _GREEN if left_ratio > 0.35 else _RED)
        team_bar(col_right_x, right_cur_total, right_max_total, _GREEN if right_ratio > 0.35 else _RED, align_right=True)

        for i, cr in enumerate(left_team):
            y = card_start_y + i * (card_h + card_gap)
            from core.battle_engine import compute_display_stats
            computed = compute_display_stats(cr)
            max_hp = computed.get("HP", int(cr.get("hp", 1)))
            max_mp = computed.get("MANA", int(cr.get("mana", 200)))
            cur_hp = left_hp[i] if i < len(left_hp) else max_hp
            cur_mp = left_wp[i] if i < len(left_wp) else max_mp
            self._draw_compact_creature_card(draw, img, col_left_x, y, col_w, card_h, cr, cur_hp, max_hp, cur_mp, max_mp, is_left=True)

        for i, cr in enumerate(right_team):
            y = card_start_y + i * (card_h + card_gap)
            from core.battle_engine import compute_display_stats
            computed = compute_display_stats(cr)
            max_hp = computed.get("HP", int(cr.get("hp", 1)))
            max_mp = computed.get("MANA", int(cr.get("mana", 200)))
            cur_hp = right_hp[i] if i < len(right_hp) else max_hp
            cur_mp = right_wp[i] if i < len(right_wp) else max_mp
            self._draw_compact_creature_card(draw, img, col_right_x, y, col_w, card_h, cr, cur_hp, max_hp, cur_mp, max_mp, is_left=False)

        return self._save(img)

    def _apply_ultra_border_custom(self, img: Image.Image, W: int, H: int) -> None:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for i in range(3, 0, -1):
            m = i * 4
            od.rectangle((m, m, W - m, H - m), outline=(*_PURPLE, max(30, 80 - i * 15)), width=2)
        img.paste(overlay, (0, 0), overlay)

    # ── Compact Creature Card ─────────────────────────────────

    def _draw_compact_creature_card(self, draw: ImageDraw.ImageDraw, img: Image.Image,
                                    x: int, y: int, w: int, h: int, cr: dict[str, Any],
                                    cur_hp: int, max_hp: int, cur_mp: int, max_mp: int, is_left: bool) -> None:
        rarity = str(cr.get("rarity", "Common"))
        rc = _col(rarity)
        name = str(cr.get("name", "?"))
        level = int(cr.get("level", 1))
        dead = cur_hp <= 0

        from core.battle_engine import compute_display_stats
        computed = compute_display_stats(cr)
        stat_str = computed.get("STR", 0)
        stat_def = computed.get("DEF", 0)
        stat_mana = computed.get("MANA", 0)
        stat_mag = computed.get("MAG", 0)
        stat_res = computed.get("RES", 0)
        fill_col = _lerp(_PANEL_DARK, rc, 0.05)
        alpha = 102 if dead else 62
        outline = _lerp(rc, _BORDER, 0.24 if not dead else 0.65)
        _draw_battle_panel(img, (x, y, x + w, y + h), outline, fill=(*fill_col, alpha), cut=14, texture_alpha=255)
        draw = ImageDraw.Draw(img)

        ps = min(218, max(156, h - 34))
        pad = 18
        p_x = x + pad if is_left else x + w - ps - pad
        p_y = y + (h - ps) // 2

        portrait = None
        for asset_key in _creature_asset_candidates(cr, name, rarity):
            portrait = self._load_asset("creatures", asset_key, (ps, ps))
            if portrait is not None:
                break
        if portrait is None:
            portrait = Image.new("RGBA", (ps, ps), (0, 0, 0, 0))
            pdd = ImageDraw.Draw(portrait)
            cui.draw_pixel_box(pdd, (2, 2, ps - 2, ps - 2), (*_PANEL_DARK, 255), (*_BORDER, 255), cut=12, width=2)

        mask = cui.pixel_box_mask((ps, ps), cut=12)
        r, g, b, a = portrait.split()
        from PIL import ImageChops
        a = ImageChops.multiply(a, mask)
        portrait = Image.merge("RGBA", (r, g, b, a))

        if dead:
            portrait = portrait.convert("L").convert("RGBA")

        if not dead:
            glow = Image.new("RGBA", (ps + 28, ps + 28), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            gd.ellipse((0, 0, ps + 27, ps + 27), fill=(*rc, 50))
            glow = glow.filter(ImageFilter.GaussianBlur(6))
            img.paste(glow, (p_x - 14, p_y - 14), glow)

        portrait_frame = (p_x - 8, p_y - 8, p_x + ps + 8, p_y + ps + 8)
        _draw_clean_portrait_frame(img, draw, portrait_frame, outline, rc if not dead else _BORDER, cut=10)
        img.paste(portrait, (p_x, p_y), portrait)
        _draw_cut_outline(draw, portrait_frame, (*outline, 230), cut=10, width=1)
        _draw_cut_outline(draw, (p_x - 2, p_y - 2, p_x + ps + 2, p_y + ps + 2), (*rc, 150 if not dead else 75), cut=6, width=1)

        info_x = x + ps + pad * 2 if is_left else x + pad
        info_w = w - ps - pad * 3

        font_name = _font(22, bold=True)
        nc = _TEXT_MUTED if dead else _TEXT_BRIGHT
        display_name = _fit_name(draw, name, info_w - 100, font_name)
        nw = _tw(draw, display_name, font_name)
        draw.text((info_x, y + 14), display_name, font=font_name, fill=nc)

        font_lv = _font(16, bold=True)
        lv_text = f"L.{level}"
        draw.text((info_x + nw + 10, y + 17), lv_text, font=font_lv, fill=rc if not dead else _TEXT_MUTED)

        rarity_text = rarity.upper()
        rarity_font = _font(11, bold=True)
        rw = min(info_w - 18, max(78, _tw(draw, rarity_text, rarity_font) + 24))
        _draw_battle_badge(
            draw,
            (info_x + info_w - rw, y + 15, info_x + info_w, y + 39),
            rarity_text,
            rc if not dead else _BORDER,
        )

        bar_x = info_x
        bar_y = y + 46
        bar_w = info_w
        bar_h = 28
        ratio = max(0.0, min(1.0, cur_hp / max(1, max_hp)))

        if dead:
            hp_color = (60, 60, 60)
        elif ratio > 0.5:
            hp_color = (74, 222, 128)
        elif ratio > 0.2:
            hp_color = (250, 204, 21)
        else:
            hp_color = (235, 80, 90)

        pct_text = f"{int(ratio*100)}%"
        hp_text = f"{_compact_num(cur_hp)}/{_compact_num(max_hp)}"
        _draw_battle_bar(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), cur_hp, max_hp, hp_color, f"{pct_text}   {hp_text}")

        # Mana bar
        mp_bar_y = bar_y + bar_h + 6
        mp_ratio = max(0.0, min(1.0, cur_mp / max(1, max_mp)))

        if mp_ratio > 0.5:
            mp_color = (80, 140, 235)
        elif mp_ratio > 0.2:
            mp_color = (120, 100, 220)
        else:
            mp_color = (60, 80, 180)

        mp_pct_text = f"{int(mp_ratio*100)}%"
        mp_text = f"{_compact_num(cur_mp)}/{_compact_num(max_mp)}"
        _draw_battle_bar(draw, (bar_x, mp_bar_y, bar_x + bar_w, mp_bar_y + bar_h), cur_mp, max_mp, mp_color, f"{mp_pct_text}   {mp_text}")

        stat_y = mp_bar_y + bar_h + 12
        font_stat_val = _font(20, bold=True)
        icon_size = 32
        stat_pairs = [
            ("hp", max_hp, _GREEN),
            ("mana", stat_mana, (80, 140, 235)),
            ("str", stat_str, _GOLD),
            ("mag", stat_mag, (255, 165, 55)),
            ("def", stat_def, _BLUE),
            ("res", stat_res, (130, 180, 235)),
        ]
        w_data = cr.get("_weapon") if isinstance(cr.get("_weapon"), dict) else None
        w_sz = 96 if w_data else 0
        weapon_gap = 18 if w_data else 0
        stat_area_x = info_x
        stat_area_w = info_w - (w_sz + weapon_gap if w_data else 0)
        if w_data and not is_left:
            stat_area_x = info_x + w_sz + weapon_gap
        stat_col_w = stat_area_w / 2
        for idx, (key, value, color) in enumerate(stat_pairs):
            row = idx // 2
            col = idx % 2
            sx = stat_area_x + col * int(stat_col_w)
            sy = stat_y + row * 35
            val_text = f"{_compact_num(value)}{'%' if key in ('def','res') else ''}"
            chip_w = max(92, int(stat_col_w) - 8)
            chip = (int(sx), sy - 2, int(sx) + chip_w, sy + 32)
            cui.draw_pixel_box(draw, chip, (3, 4, 9, 150), (*color, 92 if not dead else 48), cut=5, width=1)
            icon = self._load_asset("stats_battle", key, (icon_size, icon_size)) or self._load_asset("stats", key, (icon_size, icon_size))
            text_color = _TEXT_MUTED if dead else color
            if icon:
                img.paste(icon, (int(sx) + 4, sy - 1), icon)
                draw.text((int(sx) + icon_size + 12, sy + 4), val_text, font=font_stat_val, fill=text_color)
            else:
                draw.text((int(sx) + 8, sy + 4), key.upper(), font=_font(12, bold=True), fill=text_color)
                draw.text((int(sx) + 44, sy + 4), val_text, font=font_stat_val, fill=text_color)
        if w_data:
            w_rarity = str(w_data.get("rarity", "Common"))
            w_rc = _col(w_rarity)
            if is_left:
                wi_x = info_x + info_w - w_sz
            else:
                wi_x = info_x
            wi_y = stat_y + 12

            cui.draw_pixel_box(draw, (wi_x, wi_y, wi_x + w_sz, wi_y + w_sz), (4, 5, 11, 180), (*w_rc, 190), cut=10, width=1)

            weapon_type = str(w_data.get("weapon_type", "sword") or "sword")
            weapon_icon = self._load_asset("weapons", weapon_type, (w_sz - 14, w_sz - 14))
            if weapon_icon:
                img.paste(weapon_icon, (wi_x + 7, wi_y + 7), weapon_icon)
            else:
                draw.line((wi_x + 22, wi_y + 58, wi_x + 56, wi_y + 18), fill=w_rc, width=6)
                draw.line((wi_x + 20, wi_y + 56, wi_x + 46, wi_y + 68), fill=w_rc, width=4)

    # ── Background ─────────────────────────────────────

    def _build_background(self, zone_key: str) -> Image.Image:
        img = self._get_zone_bg(zone_key, W, H)
        darken = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.blend(img, darken, 0.44)
        return img

    def _get_zone_bg(self, zone_key: str, w: int, h: int) -> Image.Image:
        path = get_asset_file_path("zones", zone_key)
        if path and path.exists():
            try:
                return Image.open(path).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
            except OSError:
                pass
        return self._gradient_bg(zone_key, w, h)

    def _gradient_bg(self, zone_key: str, w: int, h: int) -> Image.Image:
        colors = _ZONE_BGS.get(zone_key, ((16, 12, 28), (8, 6, 14)))
        top, bot = colors
        top = tuple(min(255, c + 20) for c in top)
        bot = tuple(min(255, c + 15) for c in bot)
        img = Image.new("RGB", (w, h))
        d = ImageDraw.Draw(img)
        for y in range(h):
            t = y / max(1, h - 1)
            d.line((0, y, w, y), fill=_lerp(top, bot, t))
        return img

    def _apply_ultra_border(self, img: Image.Image) -> None:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for i in range(3, 0, -1):
            m = i * 10
            od.rectangle((m, m, W - m, H - m), outline=(*_PURPLE, max(30, 80 - i * 15)), width=3)
        img.paste(overlay, (0, 0), overlay)

    # ── Asset Loading ─────────────────────────────────

    def _load_asset(self, kind: str, key: str, size: tuple[int, int]) -> Image.Image | None:
        if kind == "creatures":
            path = get_creature_asset_path(key)
        elif kind == "stats_battle":
            path = ASSET_DIR / "stats_battle" / f"{normalize_key(key)}.png"
        else:
            path = get_asset_file_path(kind, key)
        if path and path.exists():
            try:
                a = Image.open(path).convert("RGBA")
                bbox = a.getbbox()
                if bbox:
                    a = a.crop(bbox)
                resample = Image.Resampling.NEAREST if kind in ("creatures", "weapons", "passives", "stats", "stats_battle") else Image.Resampling.LANCZOS
                a.thumbnail(size, resample)
                c = Image.new("RGBA", size, (0, 0, 0, 0))
                c.alpha_composite(a, ((size[0] - a.width) // 2, (size[1] - a.height) // 2))
                return c
            except OSError:
                pass
        return None

    def _save(self, img: Image.Image) -> BytesIO:
        b = BytesIO()
        img.save(b, format="PNG")
        b.seek(0)
        return b
