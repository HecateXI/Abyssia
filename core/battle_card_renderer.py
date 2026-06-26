from __future__ import annotations

import json
import functools
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from core import card_ui as cui
from core.battle_engine import compute_display_stats
from core.content_config import ASSET_DIR, ROOT_DIR, get_asset_file_path, get_creature_asset_path
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
_BATTLE_SCENE_BG = ROOT_DIR / "assets" / "ui" / "backgrounds" / "battle_3v3_gothic_arena.png"
_BATTLE_BACKDROP_DIR = ROOT_DIR / "assets" / "ui" / "battle_backdrops"
_GENERATED_ZONE_BACKDROP_DIR = ROOT_DIR / "assets" / "ui" / "generated_zone_backdrops"


def _load_texture(path: Path) -> Image.Image | None:
    if path not in _TEXTURE_CACHE:
        try:
            _TEXTURE_CACHE[path] = Image.open(path).convert("RGB") if path.exists() else None
        except OSError:
            _TEXTURE_CACHE[path] = None
    cached = _TEXTURE_CACHE.get(path)
    return cached.copy() if cached is not None else None


def _backdrop_dirs() -> tuple[Path, ...]:
    return (_BATTLE_BACKDROP_DIR, _GENERATED_ZONE_BACKDROP_DIR)


def battle_backdrop_keys() -> list[str]:
    keys: list[str] = []
    for directory in _backdrop_dirs():
        try:
            keys.extend(path.stem for path in directory.glob("*.png") if path.is_file())
        except OSError:
            continue
    return sorted(dict.fromkeys(keys))


def _battle_backdrop_path(key: str | None) -> Path | None:
    if not key:
        return None
    safe = normalize_key(str(key))
    for directory in _backdrop_dirs():
        path = directory / f"{safe}.png"
        if path.exists():
            return path
    return None


def _battle_background(w: int, h: int, backdrop_key: str | None = None) -> Image.Image:
    generated = None
    backdrop_path = _battle_backdrop_path(backdrop_key)
    if backdrop_path is not None:
        generated = _load_texture(backdrop_path)
    if generated is None:
        generated = _load_texture(_BATTLE_SCENE_BG)
    if generated is not None:
        bg = cui.cover_resize(generated, (w, h)).convert("RGBA")
        shade = Image.new("RGBA", (w, h), (0, 0, 0, 54))
        bg.alpha_composite(shade)
        cui.draw_vignette(bg, 0.78)
        return bg

    bg = Image.new("RGBA", (w, h), (5, 4, 8, 255))
    draw = ImageDraw.Draw(bg)
    top = (26, 16, 22)
    bottom = (4, 3, 7)
    for y in range(h):
        t = y / max(1, h - 1)
        draw.line((0, y, w, y), fill=(*_lerp(top, bottom, t), 255))
    noise = Image.effect_noise((w, h), 34).convert("L")
    grain = Image.new("RGBA", (w, h), (160, 130, 95, 0))
    grain.putalpha(noise.point(lambda p: 18 if p > 136 else 0))
    bg.alpha_composite(grain)

    arena = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ad = ImageDraw.Draw(arena)
    for cx in (w // 2 - 430, w // 2, w // 2 + 430):
        ad.rounded_rectangle((cx - 150, 95, cx + 150, h + 120), radius=150, outline=(92, 70, 52, 70), width=12)
    ad.ellipse((w // 2 - 420, h - 235, w // 2 + 420, h + 55), fill=(18, 10, 12, 122), outline=(128, 86, 52, 82), width=4)
    ad.line((w // 2, 110, w // 2, h - 85), fill=(225, 176, 72, 38), width=3)
    bg.alpha_composite(arena)

    mist = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    md = ImageDraw.Draw(mist)
    md.ellipse((-120, h // 2, w + 120, h // 2 + 240), fill=(115, 104, 130, 26))
    bg.alpha_composite(mist.filter(ImageFilter.GaussianBlur(40)))
    cui.draw_vignette(bg, 0.94)
    return bg


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
    cui.draw_pixel_plaque(
        img,
        box,
        fill=fill,
        border=(*border, 225),
        radius=cut,
        shadow=shadow,
        glow=False,
    )


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    k = f"f_{size}_{bold}"
    if k in _FONT_CACHE:
        return _FONT_CACHE[k]
    candidates = [
        str(ROOT_DIR / "assets" / "fonts" / "alagard.ttf"),
        "CascadiaMono.ttf",
        "consolab.ttf" if bold else "consola.ttf",
        "AGENCYB.TTF" if bold else "AGENCYR.TTF",
        "bahnschrift.ttf",
        "courbd.ttf" if bold else "cour.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
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
    text = str(text).upper()
    draw.text((x + offset, y + offset), text, font=font, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=font, fill=color)


def _fit_name(draw: ImageDraw.ImageDraw, text: str, max_w: int, font: ImageFont.ImageFont) -> str:
    text = str(text).upper()
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
    radius = max(8, (y2 - y1) // 2)
    draw.rounded_rectangle(box, radius=radius, fill=(7, 6, 13, 236), outline=(*_BORDER, 190), width=2)
    ratio = max(0.0, min(1.0, cur / max(1, mx)))
    fill_w = int(max(0, x2 - x1 - 8) * ratio)
    if fill_w > 0:
        fill = (x1 + 4, y1 + 4, min(x2 - 4, x1 + 4 + fill_w), y2 - 4)
        draw.rounded_rectangle(fill, radius=max(5, radius - 4), fill=(*color, 226))
        draw.line((fill[0] + 10, fill[1] + 4, max(fill[0] + 11, fill[2] - 10), fill[1] + 4), fill=(*_WHITE, 58), width=2)
    font = _fit_font(draw, label, x2 - x1 - 12, max(11, y2 - y1 - 7), bold=True, min_size=8)
    tw = _tw(draw, label, font)
    tx = x1 + (x2 - x1 - tw) // 2
    ty = y1 + max(0, (y2 - y1 - font.size) // 2) - 1
    _shadow_text(draw, tx, ty, label, font, _WHITE, offset=1)


def _draw_battle_icon_bar(
    img: Image.Image,
    box: tuple[int, int, int, int],
    cur: int,
    mx: int,
    color: tuple[int, int, int],
    icon_key: str,
    *,
    dead: bool = False,
) -> None:
    draw = ImageDraw.Draw(img)
    x1, y1, x2, y2 = box
    icon_size = max(20, min(30, (y2 - y1) + 5))
    icon = cui.load_asset_icon("stats_battle", icon_key, (icon_size, icon_size), pixel=True)
    if dead:
        alpha = icon.getchannel("A").point(lambda p: int(p * 0.45))
        icon = icon.convert("L").convert("RGBA")
        icon.putalpha(alpha)
    ix = x1
    iy = y1 + (y2 - y1 - icon_size) // 2
    img.alpha_composite(icon, (ix, iy))

    bx1 = x1 + icon_size + 8
    radius = max(8, (y2 - y1) // 2)
    bar_box = (bx1, y1, x2, y2)
    draw.rounded_rectangle(bar_box, radius=radius, fill=(7, 6, 13, 236), outline=(*_BORDER, 190), width=2)
    ratio = max(0.0, min(1.0, cur / max(1, mx)))
    fill_w = int(max(0, x2 - bx1 - 8) * ratio)
    if fill_w > 0:
        fill = (bx1 + 4, y1 + 4, min(x2 - 4, bx1 + 4 + fill_w), y2 - 4)
        draw.rounded_rectangle(fill, radius=max(5, radius - 4), fill=(*color, 226))
        draw.line((fill[0] + 10, fill[1] + 4, max(fill[0] + 11, fill[2] - 10), fill[1] + 4), fill=(*_WHITE, 58), width=2)
    label = f"{_compact_num(cur)}/{_compact_num(mx)}"
    font = _fit_font(draw, label, x2 - bx1 - 14, max(13, y2 - y1 - 5), bold=True, min_size=9)
    tx = bx1 + 10
    ty = y1 + max(0, (y2 - y1 - font.size) // 2) - 1
    _shadow_text(draw, tx, ty, label, font, _WHITE, offset=1)


def _draw_battle_badge(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    color: tuple[int, int, int],
) -> None:
    draw.rounded_rectangle(box, radius=8, fill=(4, 4, 9, 216), outline=(*color, 205), width=2)
    font = _fit_font(draw, label, box[2] - box[0] - 14, max(16, box[3] - box[1] - 9), bold=True, min_size=11)
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
        return self._render_battle_scene(data)

    def render_battle_frame(self, data: dict[str, Any]) -> BytesIO:
        return self._render_battle_scene(data)

    def _render_battle_scene(self, data: dict[str, Any]) -> BytesIO:
        

        left_team = list(data.get("player_team", []) or [])[:3]
        right_team = list(data.get("enemy_team", []) or [])[:3]
        left_hp = list(data.get("player_hp", []) or [])
        right_hp = list(data.get("enemy_hp", []) or [])
        left_wp = list(data.get("player_wp", []) or [])
        right_wp = list(data.get("enemy_wp", []) or [])

        W, H = 1600, 900
        img = _battle_background(W, H, str(data.get("battle_bg_key") or data.get("zone_key") or ""))
        draw = ImageDraw.Draw(img)
        draw.fontmode = "1"

        if data.get("has_ultra_rare"):
            self._apply_ultra_border_custom(img, W, H)

        player_name = str(data.get("player_name", "Hunter"))
        enemy_name = str(data.get("enemy_name", "Opponent"))
        won = data.get("won")
        result = "VICTORY" if won is True else ("DEFEAT" if won is False else "ROUND")
        if data.get("tied"):
            result = "DRAW"
        result_color = _GOLD if won is True else (_RED if won is False else _PURPLE)

        def state_for(team: list[Any], hp_rows: list[Any], mp_rows: list[Any], index: int) -> tuple[int, int, int, int]:
            cr = team[index]
            computed = compute_display_stats(cr)
            max_hp = max(1, int(computed.get("HP", int(cr.get("hp", 1)))))
            max_mp = max(1, int(computed.get("MANA", int(cr.get("mana", 200)))))
            cur_hp = max(0, int(hp_rows[index] if index < len(hp_rows) else max_hp))
            cur_mp = max(0, int(mp_rows[index] if index < len(mp_rows) else max_mp))
            return cur_hp, max(max_hp, cur_hp), cur_mp, max(max_mp, cur_mp)

        def team_total(team: list[Any], hp_rows: list[Any]) -> tuple[int, int]:
            cur = 0
            total = 0
            for idx in range(len(team)):
                cur_hp, max_hp, _, _ = state_for(team, hp_rows, [], idx)
                cur += cur_hp
                total += max_hp
            return cur, max(1, total)

        left_cur, left_max = team_total(left_team, left_hp)
        right_cur, right_max = team_total(right_team, right_hp)
        self._draw_scene_header(
            img,
            player_name,
            str(data.get("player_rank", "")),
            left_cur,
            left_max,
            enemy_name,
            str(data.get("enemy_rank", "")),
            right_cur,
            right_max,
            result,
            result_color,
            int(data.get("turn", data.get("turns", 0)) or 0),
        )

        left_slots = [(470, 548, 270, 0), (265, 690, 226, -10), (625, 720, 232, 12)]
        right_slots = [(1130, 548, 270, 0), (1335, 690, 226, 10), (975, 720, 232, -12)]
        turn = int(data.get("turn", data.get("turns", 0)) or 0)
        entries: list[tuple[int, bool, int, Any, tuple[int, int, int, int]]] = []
        for idx, cr in enumerate(left_team):
            entries.append((left_slots[idx][1], True, idx, cr, left_slots[idx]))
        for idx, cr in enumerate(right_team):
            entries.append((right_slots[idx][1], False, idx, cr, right_slots[idx]))
        for _, is_left, idx, cr, slot in sorted(entries, key=lambda item: item[0]):
            hp_rows = left_hp if is_left else right_hp
            mp_rows = left_wp if is_left else right_wp
            team = left_team if is_left else right_team
            cur_hp, max_hp, cur_mp, max_mp = state_for(team, hp_rows, mp_rows, idx)
            self._draw_battle_actor(img, cr, slot, cur_hp, max_hp, cur_mp, max_mp, is_left=is_left, index=idx, turn=turn)

        if data.get("preview_card"):
            return self._save(img, max_size=(960, 540), colors=192)
        return self._save(img)

    def _draw_scene_header(
        self,
        img: Image.Image,
        left_name: str,
        left_rank: str,
        left_cur: int,
        left_max: int,
        right_name: str,
        right_rank: str,
        right_cur: int,
        right_max: int,
        result: str,
        result_color: tuple[int, int, int],
        turn: int,
    ) -> None:
        draw = ImageDraw.Draw(img)
        left_box = (48, 28, 600, 118)
        right_box = (1000, 28, 1552, 118)
        center_box = (690, 26, 910, 120)
        _draw_battle_panel(img, left_box, _lerp(_GREEN, _GOLD, 0.18), fill=(5, 4, 8, 190), texture_alpha=0)
        _draw_battle_panel(img, right_box, _lerp(_RED, _GOLD, 0.18), fill=(5, 4, 8, 190), texture_alpha=0)
        _draw_battle_panel(img, center_box, result_color, fill=(7, 5, 8, 218), texture_alpha=0)
        draw = ImageDraw.Draw(img)

        name_font = _font(35, bold=True)
        rank_font = _font(18)
        left_title = _fit_name(draw, left_name, left_box[2] - left_box[0] - 48, name_font)
        right_title = _fit_name(draw, right_name, right_box[2] - right_box[0] - 48, name_font)
        _shadow_text(draw, left_box[0] + 24, left_box[1] + 13, left_title, name_font, _TEXT_BRIGHT)
        draw.text((left_box[0] + 26, left_box[1] + 52), left_rank[:42], font=rank_font, fill=_TEXT_MUTED)
        _shadow_text(draw, right_box[2] - _tw(draw, right_title, name_font) - 24, right_box[1] + 13, right_title, name_font, _TEXT_BRIGHT)
        rank_text = right_rank[:42]
        draw.text((right_box[2] - _tw(draw, rank_text, rank_font) - 26, right_box[1] + 52), rank_text, font=rank_font, fill=_TEXT_MUTED)
        _draw_battle_icon_bar(img, (left_box[0] + 24, left_box[3] - 35, left_box[2] - 24, left_box[3] - 10), left_cur, left_max, _GREEN if left_cur / max(1, left_max) > 0.35 else _RED, "hp")
        _draw_battle_icon_bar(img, (right_box[0] + 24, right_box[3] - 35, right_box[2] - 24, right_box[3] - 10), right_cur, right_max, _GREEN if right_cur / max(1, right_max) > 0.35 else _RED, "hp")

        result_font = _font(33, bold=True)
        _shadow_text(draw, center_box[0] + (center_box[2] - center_box[0] - _tw(draw, result, result_font)) // 2, center_box[1] + 15, result, result_font, result_color)
        round_text = f"Round {turn}" if turn else "Battle"
        round_font = _font(20, bold=True)
        draw.text((center_box[0] + (center_box[2] - center_box[0] - _tw(draw, round_text, round_font)) // 2, center_box[1] + 56), round_text, font=round_font, fill=_TEXT_MUTED)

    def _draw_battle_actor(
        self,
        img: Image.Image,
        cr: dict[str, Any],
        slot: tuple[int, int, int, int],
        cur_hp: int,
        max_hp: int,
        cur_mp: int,
        max_mp: int,
        *,
        is_left: bool,
        index: int,
        turn: int,
    ) -> None:
        cx, base_y, size, stance = slot
        rarity = str(cr.get("rarity", "Common"))
        rc = _col(rarity)
        name = str(cr.get("name", "?"))
        level = int(cr.get("level", 1))
        dead = cur_hp <= 0
        phase = ((turn + index * 2) % 4) - 1.5
        bob = 0 if dead else int(phase * 4)
        lean = -1 if is_left else 1
        center = (cx + int(stance * 2) + (0 if dead else int(phase * lean * 5)), base_y - size // 2 + bob)

        draw = ImageDraw.Draw(img)
        cui.draw_pixel_platform(img, (cx, base_y + 6), int(size * 1.16), 58, rc if not dead else _BORDER, alpha=124)

        portrait = None
        for asset_key in _creature_asset_candidates(cr, name, rarity):
            portrait = self._load_asset("creatures", asset_key, (size, size))
            if portrait is not None:
                break
        if portrait is None:
            portrait = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        if is_left:
            portrait = portrait.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if dead:
            alpha = portrait.getchannel("A").point(lambda p: int(p * 0.42))
            portrait = portrait.convert("L").convert("RGBA")
            portrait.putalpha(alpha)
        cui.paste_icon_3d(img, portrait, center, size, rc if not dead else _BORDER, glow_alpha=0, rim_light=False)

        self._draw_actor_weapon(img, cr, center, size, rc, is_left=is_left, dead=dead)
        self._draw_actor_bars(img, name, rarity, level, cx, base_y, size, cur_hp, max_hp, cur_mp, max_mp, is_left=is_left, dead=dead)

    def _draw_actor_weapon(
        self,
        img: Image.Image,
        cr: dict[str, Any],
        center: tuple[int, int],
        size: int,
        rc: tuple[int, int, int],
        *,
        is_left: bool,
        dead: bool,
    ) -> None:
        w_data = cr.get("_weapon") if isinstance(cr.get("_weapon"), dict) else None
        if not w_data:
            return
        weapon_type = str(w_data.get("weapon_type", "sword") or "sword")
        weapon_size = max(90, int(size * 0.54))
        weapon = self._load_asset("weapons", weapon_type, (weapon_size, weapon_size))
        if weapon is None:
            return
        if is_left:
            weapon = weapon.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if dead:
            alpha = weapon.getchannel("A").point(lambda p: int(p * 0.45))
            weapon = weapon.convert("L").convert("RGBA")
            weapon.putalpha(alpha)
        weapon = weapon.rotate(-18 if is_left else 18, resample=Image.Resampling.BICUBIC, expand=True)
        forward = 1 if is_left else -1
        held_center = (
            center[0] + forward * int(size * 0.20),
            center[1] + int(size * 0.20),
        )
        wx = held_center[0] - weapon.width // 2
        wy = held_center[1] - weapon.height // 2
        img.alpha_composite(weapon, (wx, wy))

    def _draw_actor_bars(
        self,
        img: Image.Image,
        name: str,
        rarity: str,
        level: int,
        cx: int,
        base_y: int,
        size: int,
        cur_hp: int,
        max_hp: int,
        cur_mp: int,
        max_mp: int,
        *,
        is_left: bool,
        dead: bool,
    ) -> None:
        draw = ImageDraw.Draw(img)
        box_w = 330 if size >= 250 else 292
        x1 = cx - box_w // 2
        y1 = base_y - size - 102 + (10 if not is_left else 0)
        box = (x1, y1, x1 + box_w, y1 + 106)
        border = _col(rarity) if not dead else _BORDER
        _draw_battle_panel(img, box, border, fill=(4, 4, 8, 196), texture_alpha=0, shadow=True)
        draw = ImageDraw.Draw(img)
        title = _fit_name(draw, name, box_w - 96, _font(22, bold=True))
        draw.text((box[0] + 14, box[1] + 10), title, font=_font(22, bold=True), fill=_TEXT_BRIGHT if not dead else _TEXT_MUTED)
        level_text = f"Lv.{level}"
        draw.text((box[2] - _tw(draw, level_text, _font(18, bold=True)) - 14, box[1] + 13), level_text, font=_font(18, bold=True), fill=border)
        hp_ratio = cur_hp / max(1, max_hp)
        hp_color = (74, 222, 128) if hp_ratio > 0.5 else ((250, 204, 21) if hp_ratio > 0.2 else _RED)
        if dead:
            hp_color = (70, 64, 64)
        _draw_battle_icon_bar(img, (box[0] + 14, box[1] + 43, box[2] - 14, box[1] + 69), cur_hp, max_hp, hp_color, "hp", dead=dead)
        _draw_battle_icon_bar(img, (box[0] + 14, box[1] + 73, box[2] - 14, box[1] + 98), cur_mp, max_mp, _BLUE if not dead else (60, 60, 70), "mana", dead=dead)

    def _draw_scene_log_hint(self, img: Image.Image, lines: list[str]) -> None:
        if not lines:
            return
        draw = ImageDraw.Draw(img)
        box = (462, 792, 1138, 872)
        _draw_battle_panel(img, box, _lerp(_PURPLE, _GOLD, 0.18), fill=(3, 3, 7, 168), texture_alpha=0, shadow=True)
        draw = ImageDraw.Draw(img)
        y = box[1] + 14
        for line in lines[:2]:
            text = _fit_name(draw, line, box[2] - box[0] - 34, _font(20))
            draw.text((box[0] + 18, y), text, font=_font(20), fill=_TEXT_MUTED)
            y += 28

    def _portrait_battle_card(self, scene: Image.Image, data: dict[str, Any]) -> Image.Image:
        W, H = 900, 1100
        bg = cui.cover_resize(scene.convert("RGBA"), (W, H)).convert("RGBA").filter(ImageFilter.GaussianBlur(10))
        bg.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 132)))
        cui.draw_vignette(bg, 0.84)
        draw = ImageDraw.Draw(bg)
        draw.fontmode = "1"

        won = data.get("won")
        if data.get("tied"):
            result = "DRAW"
            result_color = _GOLD
        elif won is True:
            result = "VICTORY"
            result_color = _GREEN
        elif won is False:
            result = "DEFEAT"
            result_color = _RED
        else:
            result = "BATTLE"
            result_color = _PURPLE
        player = str(data.get("player_name", "Hunter"))
        enemy = str(data.get("enemy_name", "Opponent"))

        title_box = (34, 26, W - 34, 104)
        cui.draw_pixel_plaque(bg, title_box, fill=(5, 4, 8, 205), border=result_color, radius=8, shadow=True)
        cui.draw_text_fit(draw, result, (title_box[0] + 24, title_box[1] + 8, title_box[2] - 24, title_box[1] + 50), cui.get_font(40, bold=True), result_color, 24, "center", True)
        matchup = f"{player} vs {enemy}"
        cui.draw_text_fit(draw, matchup, (title_box[0] + 24, title_box[1] + 48, title_box[2] - 24, title_box[3] - 8), cui.get_font(20, bold=True), _TEXT_MUTED, 12, "center", True)

        scene_img = scene.convert("RGBA")
        scene_img.thumbnail((842, 474), Image.Resampling.LANCZOS)
        scene_box = (29, 122, W - 29, 122 + scene_img.height + 26)
        cui.draw_pixel_plaque(bg, scene_box, fill=(3, 3, 7, 218), border=_BORDER, radius=8, shadow=True)
        bg.alpha_composite(scene_img, ((W - scene_img.width) // 2, scene_box[1] + 13))

        y = scene_box[3] + 24
        stat_box = (38, y, W - 38, y + 112)
        cui.draw_pixel_plaque(bg, stat_box, fill=(5, 4, 8, 205), border=result_color, radius=8, shadow=True)
        turns = int(data.get("turn", data.get("turns", 0)) or 0)
        xp = int(data.get("xp_reward", 0) or 0)
        rating_change = data.get("rating_change")
        stats = [
            ("TURN", str(turns or "-"), _GOLD),
            ("XP", f"+{xp:,}" if xp else "-", _GREEN),
            ("RATING", f"{int(rating_change):+d}" if rating_change is not None else "-", _CYAN),
        ]
        cell_w = (stat_box[2] - stat_box[0] - 44) // 3
        for idx, (label, value, color) in enumerate(stats):
            x = stat_box[0] + 18 + idx * (cell_w + 4)
            draw.text((x + 8, stat_box[1] + 18), label, font=_font(15, bold=True), fill=_TEXT_MUTED)
            cui.draw_text_fit(draw, value, (x + 8, stat_box[1] + 42, x + cell_w - 8, stat_box[3] - 14), cui.get_font(31, bold=True), color, 18, "left", True)

        log_box = (38, y + 134, W - 38, H - 34)
        cui.draw_pixel_plaque(bg, log_box, fill=(5, 4, 8, 210), border=_lerp(_PURPLE, _GOLD, 0.18), radius=8, shadow=True)
        draw.text((log_box[0] + 24, log_box[1] + 18), "BATTLE LOG", font=_font(22, bold=True), fill=_GOLD)
        lines = list(data.get("compact_log") or data.get("log") or data.get("full_log") or [])
        shown = [str(line) for line in lines[-7:]]
        ly = log_box[1] + 58
        for line in shown:
            text = _fit_name(draw, line, log_box[2] - log_box[0] - 48, _font(18))
            draw.text((log_box[0] + 24, ly), text, font=_font(18), fill=_TEXT_BRIGHT)
            ly += 31
        if not shown:
            draw.text((log_box[0] + 24, ly), "No battle log recorded.", font=_font(18), fill=_TEXT_MUTED)
        return bg

    def _render_cards_only(self, data: dict[str, Any]) -> BytesIO:
        left_team = data.get("player_team", [])[:3]
        right_team = data.get("enemy_team", [])[:3]
        left_hp = data.get("player_hp", [])
        right_hp = data.get("enemy_hp", [])
        left_wp = data.get("player_wp", [])
        right_wp = data.get("enemy_wp", [])

        W, H = 1600, 1000
        top_margin = 28
        bottom_margin = 34
        side_margin = 58
        header_h = 126
        card_gap = 26
        team_gap = 126
        col_w = (W - side_margin * 2 - team_gap) // 2
        col_left_x = side_margin
        col_right_x = col_left_x + col_w + team_gap
        usable_h = H - top_margin - bottom_margin - header_h
        card_h = (usable_h - card_gap * 2) // 3
        card_start_y = top_margin + header_h + 8

        img = _battle_background(W, H, str(data.get("battle_bg_key") or data.get("zone_key") or ""))
        draw = ImageDraw.Draw(img)

        if data.get("has_ultra_rare"):
            self._apply_ultra_border_custom(img, W, H)

        player_name = str(data.get("player_name", "Hunter"))
        enemy_name = str(data.get("enemy_name", "Opponent"))
        won = data.get("won")

        

        def team_totals(team: list[dict[str, Any]], hp_rows: list[Any]) -> tuple[int, int]:
            cur_total = 0
            max_total = 0
            for idx, cr in enumerate(team):
                computed = compute_display_stats(cr)
                baseline = max(1, int(computed.get("HP", int(cr.get("hp", 1)))))
                current = max(0, int(hp_rows[idx] if idx < len(hp_rows) else baseline))
                cur_total += current
                max_total += max(baseline, current)
            return cur_total, max_total

        left_cur_total, left_max_total = team_totals(left_team, left_hp)
        right_cur_total, right_max_total = team_totals(right_team, right_hp)
        left_ratio = left_cur_total / max(1, left_max_total)
        right_ratio = right_cur_total / max(1, right_max_total)
        left_leading = left_ratio >= right_ratio

        def header_panel(box: tuple[int, int, int, int], title: str, rank: str, cur: int, mx: int, color: tuple[int, int, int], align: str) -> None:
            x1, y1, x2, y2 = box
            _draw_battle_panel(img, box, _lerp(color, _GOLD, 0.18), fill=(8, 6, 10, 202), cut=12, texture_alpha=0)
            panel_draw = ImageDraw.Draw(img)
            name_font = _font(36, bold=True)
            rank_font = _font(20)
            if align == "right":
                fitted = _fit_name(panel_draw, title, x2 - x1 - 44, name_font)
                panel_draw.text((x2 - _tw(panel_draw, fitted, name_font) - 24, y1 + 16), fitted, font=name_font, fill=_TEXT_BRIGHT)
                panel_draw.text((x2 - _tw(panel_draw, rank, rank_font) - 26, y1 + 58), rank, font=rank_font, fill=_TEXT_MUTED)
            else:
                fitted = _fit_name(panel_draw, title, x2 - x1 - 44, name_font)
                panel_draw.text((x1 + 24, y1 + 16), fitted, font=name_font, fill=_TEXT_BRIGHT)
                panel_draw.text((x1 + 26, y1 + 58), rank, font=rank_font, fill=_TEXT_MUTED)
            _draw_battle_bar(panel_draw, (x1 + 24, y2 - 42, x2 - 24, y2 - 12), cur, mx, color, f"{_compact_num(cur)}/{_compact_num(mx)} HP")

        header_panel((col_left_x, top_margin, col_left_x + col_w, top_margin + 116), player_name, str(data.get("player_rank", ""))[:34], left_cur_total, left_max_total, _GREEN if left_ratio > 0.35 else _RED, "left")
        header_panel((col_right_x, top_margin, col_right_x + col_w, top_margin + 116), enemy_name, str(data.get("enemy_rank", ""))[:34], right_cur_total, right_max_total, _GREEN if right_ratio > 0.35 else _RED, "right")

        result = "VICTORY" if won is True else ("DEFEAT" if won is False else "ROUND")
        result_color = _GOLD if won is True else (_RED if won is False else _PURPLE)
        result_box = (W // 2 - 86, top_margin + 20, W // 2 + 86, top_margin + 100)
        _draw_battle_panel(img, result_box, result_color, fill=(8, 5, 8, 218), cut=10, texture_alpha=0)
        draw = ImageDraw.Draw(img)
        _shadow_text(draw, result_box[0] + (result_box[2] - result_box[0] - _tw(draw, result, _font(27, bold=True))) // 2, result_box[1] + 13, result, _font(27, bold=True), result_color, offset=2)
        round_text = f"Round {data.get('turn', 0)}"
        draw.text((result_box[0] + (result_box[2] - result_box[0] - _tw(draw, round_text, _font(20, bold=True))) // 2, result_box[1] + 50), round_text, font=_font(20, bold=True), fill=_TEXT_MUTED)

        for i, cr in enumerate(left_team):
            y = card_start_y + i * (card_h + card_gap)
            
            computed = compute_display_stats(cr)
            max_hp = int(computed.get("HP", int(cr.get("hp", 1))))
            max_mp = computed.get("MANA", int(cr.get("mana", 200)))
            cur_hp = left_hp[i] if i < len(left_hp) else max_hp
            cur_mp = left_wp[i] if i < len(left_wp) else max_mp
            max_hp = max(max_hp, int(cur_hp))
            self._draw_compact_creature_card(draw, img, col_left_x, y, col_w, card_h, cr, cur_hp, max_hp, cur_mp, max_mp, is_left=True)

        for i, cr in enumerate(right_team):
            y = card_start_y + i * (card_h + card_gap)
            
            computed = compute_display_stats(cr)
            max_hp = int(computed.get("HP", int(cr.get("hp", 1))))
            max_mp = computed.get("MANA", int(cr.get("mana", 200)))
            cur_hp = right_hp[i] if i < len(right_hp) else max_hp
            cur_mp = right_wp[i] if i < len(right_wp) else max_mp
            max_hp = max(max_hp, int(cur_hp))
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

        fill_col = _lerp(_PANEL_DARK, rc, 0.05)
        alpha = 170 if dead else 156
        outline = _lerp(rc, _BORDER, 0.24 if not dead else 0.65)
        _draw_battle_panel(img, (x, y, x + w, y + h), outline, fill=(*fill_col, alpha), cut=14, texture_alpha=0)
        draw = ImageDraw.Draw(img)

        ps = min(172, max(148, h - 58))
        pad = 22
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
        a = ImageChops.multiply(a, mask)
        portrait = Image.merge("RGBA", (r, g, b, a))

        if dead:
            portrait = portrait.convert("L").convert("RGBA")

        if not dead:
            glow = Image.new("RGBA", (ps + 28, ps + 28), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            gd.ellipse((0, 0, ps + 27, ps + 27), fill=(*rc, 62))
            glow = glow.filter(ImageFilter.GaussianBlur(10))
            img.paste(glow, (p_x - 14, p_y - 14), glow)

        portrait_frame = (p_x - 8, p_y - 8, p_x + ps + 8, p_y + ps + 8)
        _draw_clean_portrait_frame(img, draw, portrait_frame, outline, rc if not dead else _BORDER, cut=10)
        img.paste(portrait, (p_x, p_y), portrait)
        _draw_cut_outline(draw, portrait_frame, (*outline, 230), cut=10, width=1)
        _draw_cut_outline(draw, (p_x - 2, p_y - 2, p_x + ps + 2, p_y + ps + 2), (*rc, 150 if not dead else 75), cut=6, width=1)

        info_x = x + ps + pad * 2 if is_left else x + pad
        info_w = w - ps - pad * 3

        font_name = _font(30, bold=True)
        nc = _TEXT_MUTED if dead else _TEXT_BRIGHT
        display_name = _fit_name(draw, name, info_w - 132, font_name)
        nw = _tw(draw, display_name, font_name)
        draw.text((info_x + 2, y + 24), display_name, font=font_name, fill=(0, 0, 0, 180))
        draw.text((info_x, y + 21), display_name, font=font_name, fill=nc)

        font_lv = _font(22, bold=True)
        lv_text = f"Lv.{level}"
        draw.text((info_x + nw + 14, y + 28), lv_text, font=font_lv, fill=rc if not dead else _TEXT_MUTED)

        rarity_text = rarity.upper()
        rarity_font = _font(16, bold=True)
        rw = min(info_w - 18, max(112, _tw(draw, rarity_text, rarity_font) + 34))
        _draw_battle_badge(
            draw,
            (info_x + info_w - rw, y + 22, info_x + info_w, y + 52),
            rarity_text,
            rc if not dead else _BORDER,
        )

        bar_x = info_x
        bar_y = y + 76
        bar_w = info_w
        bar_h = 38
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
        _draw_battle_bar(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), cur_hp, max_hp, hp_color, f"HP {pct_text}   {hp_text}")

        # Mana bar
        mp_bar_y = bar_y + bar_h + 10
        mp_ratio = max(0.0, min(1.0, cur_mp / max(1, max_mp)))

        if mp_ratio > 0.5:
            mp_color = (80, 140, 235)
        elif mp_ratio > 0.2:
            mp_color = (120, 100, 220)
        else:
            mp_color = (60, 80, 180)

        mp_pct_text = f"{int(mp_ratio*100)}%"
        mp_text = f"{_compact_num(cur_mp)}/{_compact_num(max_mp)}"
        _draw_battle_bar(draw, (bar_x, mp_bar_y, bar_x + bar_w, mp_bar_y + bar_h - 4), cur_mp, max_mp, mp_color, f"MANA {mp_pct_text}   {mp_text}")

        status_text = "DEFEATED" if dead else "READY"
        status_color = _RED if dead else _GREEN
        _draw_battle_badge(draw, (bar_x, y + h - 48, bar_x + 150, y + h - 18), status_text, status_color)

        w_data = cr.get("_weapon") if isinstance(cr.get("_weapon"), dict) else None
        if w_data:
            w_rarity = str(w_data.get("rarity", "Common"))
            w_rc = _col(w_rarity)
            w_sz = 74
            wi_x = info_x + info_w - w_sz
            wi_y = y + h - 66

            cui.draw_pixel_box(draw, (wi_x, wi_y, wi_x + w_sz, wi_y + w_sz), (4, 5, 11, 178), (*w_rc, 190), cut=8, width=1)

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

    @functools.lru_cache(maxsize=24)
    def _get_zone_bg(self, zone_key: str, w: int, h: int) -> Image.Image:
        generated_path = _GENERATED_ZONE_BACKDROP_DIR / f"{normalize_key(zone_key)}.png"
        if generated_path.exists():
            try:
                with Image.open(generated_path) as raw:
                    img = raw.convert("RGB")
                return cui.cover_resize(img, (w, h)).convert("RGB")
            except OSError:
                pass
        path = get_asset_file_path("zones", zone_key)
        if path and path.exists():
            try:
                with Image.open(path) as raw:
                    img = raw.convert("RGB")
                return cui.cover_resize(img, (w, h)).convert("RGB")
            except OSError:
                pass
        return self._gradient_bg(zone_key, w, h)

    @functools.lru_cache(maxsize=24)
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

    @functools.lru_cache(maxsize=768)
    def _load_asset(self, kind: str, key: str, size: tuple[int, int]) -> Image.Image | None:
        if kind == "creatures":
            path = get_creature_asset_path(key)
        elif kind == "stats_battle":
            path = ASSET_DIR / "stats_battle" / f"{normalize_key(key)}.png"
        else:
            path = get_asset_file_path(kind, key)
        if path and path.exists():
            try:
                return cui.load_asset_icon(
                    kind,
                    key,
                    size,
                    pixel=kind in ("creatures", "weapons", "passives", "stats", "stats_battle"),
                ).copy()
            except OSError:
                pass
        return None

    def _save(
        self,
        img: Image.Image,
        *,
        max_size: tuple[int, int] | None = None,
        colors: int | None = None,
    ) -> BytesIO:
        return cui.save_png(img, max_size=max_size, colors=colors)
