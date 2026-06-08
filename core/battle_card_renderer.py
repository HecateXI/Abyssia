from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

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

W, H = 1600, 900


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
        side_margin = 36
        header_h = 38
        card_gap = 10
        col_w = 620
        col_left_x = side_margin
        col_right_x = W - side_margin - col_w
        center_x = col_left_x + col_w + 16
        center_w = col_right_x - center_x - 16
        usable_h = H - top_margin - bottom_margin - header_h
        card_h = (usable_h - card_gap * 2) // 3
        card_start_y = top_margin + header_h

        img = self._get_zone_bg(str(data.get("zone_key", "bloodmoon_forest")), W, H)
        darken = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.blend(img, darken, 0.66)
        vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        vd.rectangle((0, 0, W, H), outline=(0, 0, 0, 180), width=14)
        img.paste(vignette, (0, 0), vignette)
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
        left_name = _fit_name(draw, player_name, 400, name_font)
        right_name = _fit_name(draw, enemy_name, 400, name_font)
        draw.text((col_left_x, top_margin), left_name, font=name_font, fill=_TEXT_BRIGHT if left_leading else _TEXT)
        draw.text((col_right_x + col_w - _tw(draw, right_name, name_font), top_margin), right_name, font=name_font, fill=_TEXT_BRIGHT if not left_leading else _TEXT)
        player_rank = str(data.get("player_rank", ""))[:34]
        enemy_rank = str(data.get("enemy_rank", ""))[:34]
        draw.text((col_left_x, top_margin + 22), player_rank, font=rank_font, fill=_TEXT_MUTED)
        draw.text((col_right_x + col_w - _tw(draw, enemy_rank, rank_font), top_margin + 22), enemy_rank, font=rank_font, fill=_TEXT_MUTED)

        bar_y = top_margin + 24
        side_w = col_w - 20
        def team_bar(x: int, cur: int, mx: int, color: tuple[int, int, int], align_right: bool = False) -> None:
            draw.rounded_rectangle((x, bar_y, x + side_w, bar_y + 12), radius=6, fill=(30, 18, 22), outline=(80, 55, 58))
            ratio = max(0.0, min(1.0, cur / max(1, mx)))
            fw = int(side_w * ratio)
            if fw > 0:
                if align_right:
                    draw.rounded_rectangle((x + side_w - fw, bar_y + 1, x + side_w - 1, bar_y + 11), radius=5, fill=color)
                else:
                    draw.rounded_rectangle((x + 1, bar_y + 1, x + fw, bar_y + 11), radius=5, fill=color)
            txt = f"{cur:,}/{mx:,}"
            font = _font(10, bold=True)
            tx = x + side_w - _tw(draw, txt, font) - 6 if not align_right else x + 6
            _shadow_text(draw, tx, bar_y - 1, txt, font, _WHITE, offset=1)

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

        center_top = card_start_y
        center_bottom = card_start_y + 3 * card_h + 2 * card_gap
        draw.rounded_rectangle((center_x, center_top, center_x + center_w, center_bottom), radius=10,
                               fill=(10, 9, 16, 180), outline=(64, 58, 76), width=1)

        rating_change = data.get("rating_change")
        rewards = data.get("rewards") or {}
        mvp = data.get("mvp") or {}
        win_streak = int(data.get("win_streak", 0))
        cy = center_top + 18
        draw.text((center_x + 18, cy), "BATTLE STATUS", font=_font(14, bold=True), fill=_TEXT_MUTED)
        cy += 26
        draw.text((center_x + 18, cy), _fit_name(draw, player_name, center_w - 36, _font(18, bold=True)),
                  font=_font(18, bold=True), fill=_TEXT)
        cy += 24
        draw.text((center_x + 18, cy), "versus", font=_font(13, bold=True), fill=_TEXT_MUTED)
        cy += 18
        draw.text((center_x + 18, cy), _fit_name(draw, enemy_name, center_w - 36, _font(18, bold=True)),
                  font=_font(18, bold=True), fill=_GOLD)
        cy += 34
        if rating_change is not None:
            sign = "+" if int(rating_change) > 0 else ""
            color = _GREEN if int(rating_change) >= 0 else _RED
            draw.text((center_x + 18, cy), "RATING", font=_font(12), fill=_TEXT_MUTED)
            cy += 18
            draw.text((center_x + 18, cy), f"{sign}{int(rating_change)}", font=_font(24, bold=True), fill=color)
            cy += 32
        if win_streak >= 3:
            from core.rpg_data import get_streak_tier
            tier = get_streak_tier(win_streak)
            if tier.label:
                draw.line((center_x + 18, cy, center_x + center_w - 18, cy), fill=(54, 48, 66), width=1)
                cy += 12
                streak_text = f"{tier.emoji} {win_streak}x STREAK"
                draw.text((center_x + 18, cy), "STREAK", font=_font(12), fill=_TEXT_MUTED)
                cy += 16
                draw.text((center_x + 18, cy), streak_text, font=_font(16, bold=True), fill=_ORANGE)
                cy += 22
                bonus_parts = []
                if tier.xp_boost > 0:
                    bonus_parts.append(f"+{tier.xp_boost:.0%} XP")
                if tier.gold_boost > 0:
                    bonus_parts.append(f"+{tier.gold_boost:.0%} Gold")
                if tier.catch_boost > 0:
                    bonus_parts.append(f"+{tier.catch_boost:.0%} Catch")
                if bonus_parts:
                    draw.text((center_x + 18, cy), " / ".join(bonus_parts), font=_font(13, bold=True), fill=_GREEN)
                    cy += 18
        draw.line((center_x + 18, cy, center_x + center_w - 18, cy), fill=(54, 48, 66), width=1)
        cy += 14
        if mvp:
            draw.text((center_x + 18, cy), "MVP", font=_font(12), fill=_TEXT_MUTED)
            cy += 18
            draw.text((center_x + 18, cy), _fit_name(draw, str(mvp.get("name", "")), center_w - 36, _font(16, bold=True)),
                      font=_font(16, bold=True), fill=_GOLD)
        elif isinstance(rewards, dict) and rewards:
            gold = int(rewards.get("gold", 0))
            gems = int(rewards.get("gems", 0))
            draw.text((center_x + 18, cy), "REWARDS", font=_font(12), fill=_TEXT_MUTED)
            cy += 18
            draw.text((center_x + 18, cy), f"{gold:,} souls  /  {gems} gems", font=_font(15, bold=True), fill=_GOLD)

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
        stat_spd = computed.get("SPD", 0)
        stat_crit = computed.get("Crit", 5)

        pw = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pw)
        fill_col = _lerp(_PANEL_DARK, rc, 0.035)
        alpha = 148 if dead else 218
        outline = _lerp(rc, _BORDER, 0.24 if not dead else 0.65)
        pd.rounded_rectangle((0, 0, w - 1, h - 1), radius=12, fill=(*fill_col, alpha), outline=(*outline, 210), width=2)
        pd.rectangle((1, 1, w - 2, 6), fill=(*rc, 190 if not dead else 70))
        img.paste(pw, (x, y), pw)

        ps = min(180, h - 24)
        pad = 14
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
            pdd.rounded_rectangle((2, 2, ps - 2, ps - 2), radius=12, fill=(*_PANEL_DARK, 255), outline=_BORDER)

        mask = Image.new("L", (ps, ps), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, ps - 1, ps - 1), radius=12, fill=255)
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

        draw.rounded_rectangle((p_x - 4, p_y - 4, p_x + ps + 4, p_y + ps + 4),
                               radius=12, fill=(8, 7, 12), outline=outline, width=2)
        img.paste(portrait, (p_x, p_y), portrait)

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
        rw = _tw(draw, rarity_text, rarity_font) + 14
        draw.rounded_rectangle((info_x + info_w - rw, y + 16, info_x + info_w, y + 38), radius=5,
                               fill=(12, 10, 18), outline=rc if not dead else _BORDER)
        draw.text((info_x + info_w - rw + 7, y + 21), rarity_text, font=rarity_font, fill=rc if not dead else _TEXT_MUTED)

        bar_x = info_x
        bar_y = y + 46
        bar_w = info_w
        bar_h = 28
        ratio = max(0.0, min(1.0, cur_hp / max(1, max_hp)))

        draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=7,
                               fill=(27, 17, 20), outline=(68, 42, 46))

        if dead:
            hp_color = (60, 60, 60)
        elif ratio > 0.5:
            hp_color = (74, 222, 128)
        elif ratio > 0.2:
            hp_color = (250, 204, 21)
        else:
            hp_color = (235, 80, 90)

        fw = int((bar_w - 2) * ratio)
        if fw > 0:
            draw.rounded_rectangle((bar_x + 1, bar_y + 1, bar_x + 1 + fw, bar_y + bar_h - 1), radius=6, fill=hp_color)

        font_hp = _font(15, bold=True)
        hp_text = f"{cur_hp:,}/{max_hp:,}"
        hw = _tw(draw, hp_text, font_hp)
        _shadow_text(draw, bar_x + bar_w - hw - 8, bar_y + 5, hp_text, font_hp, _WHITE, offset=1)
        pct_text = f"{int(ratio*100)}%"
        _shadow_text(draw, bar_x + 8, bar_y + 5, pct_text, font_hp, _WHITE, offset=1)

        # Mana bar
        mp_bar_y = bar_y + bar_h + 6
        mp_ratio = max(0.0, min(1.0, cur_mp / max(1, max_mp)))
        draw.rounded_rectangle((bar_x, mp_bar_y, bar_x + bar_w, mp_bar_y + bar_h), radius=7,
                               fill=(18, 18, 30), outline=(42, 42, 68))

        if mp_ratio > 0.5:
            mp_color = (80, 140, 235)
        elif mp_ratio > 0.2:
            mp_color = (120, 100, 220)
        else:
            mp_color = (60, 80, 180)

        mp_fw = int((bar_w - 2) * mp_ratio)
        if mp_fw > 0:
            draw.rounded_rectangle((bar_x + 1, mp_bar_y + 1, bar_x + 1 + mp_fw, mp_bar_y + bar_h - 1), radius=6, fill=mp_color)

        font_mp = _font(14, bold=True)
        mp_text = f"{cur_mp:,}/{max_mp:,}"
        mp_w = _tw(draw, mp_text, font_mp)
        _shadow_text(draw, bar_x + bar_w - mp_w - 8, mp_bar_y + 5, mp_text, font_mp, _WHITE, offset=1)
        mp_pct_text = f"{int(mp_ratio*100)}%"
        _shadow_text(draw, bar_x + 8, mp_bar_y + 5, mp_pct_text, font_mp, _WHITE, offset=1)

        stat_y = mp_bar_y + bar_h + 12
        font_stat_val = _font(14, bold=True)
        icon_size = 18
        stat_pairs = [
            ("hp", max_hp, _GREEN),
            ("mana", stat_mana, (80, 140, 235)),
            ("str", stat_str, _GOLD),
            ("mag", stat_mag, (255, 165, 55)),
            ("def", stat_def, _BLUE),
            ("res", stat_res, (130, 180, 235)),
            ("spd", stat_spd, (180, 130, 255)),
        ]
        stat_col_w = info_w / 2
        for idx, (key, value, color) in enumerate(stat_pairs):
            row = idx // 2
            col = idx % 2
            sx = info_x + col * int(stat_col_w)
            sy = stat_y + row * 22
            val_text = f"{value:,}{'%' if key in ('def','res') else ''}"
            icon = self._load_asset("stats", key, (icon_size, icon_size))
            if is_left:
                if icon:
                    img.paste(icon, (sx, sy), icon)
                    draw.text((sx + icon_size + 6, sy - 1), val_text,
                             font=font_stat_val, fill=_TEXT_MUTED if dead else color)
                else:
                    lbl = key.upper()
                    draw.text((sx, sy), lbl, font=_font(11, bold=True), fill=_TEXT_MUTED if dead else color)
                    draw.text((sx + 30, sy), val_text,
                             font=font_stat_val, fill=_TEXT_MUTED if dead else color)
            else:
                val_w = _tw(draw, val_text, font_stat_val)
                if icon:
                    icon_x = sx + int(stat_col_w) - icon_size
                    draw.text((icon_x - 6 - val_w, sy - 1), val_text,
                             font=font_stat_val, fill=_TEXT_MUTED if dead else color)
                    img.paste(icon, (icon_x, sy), icon)
                else:
                    lbl = key.upper()
                    draw.text((sx + int(stat_col_w) - 30 - val_w, sy), val_text,
                             font=font_stat_val, fill=_TEXT_MUTED if dead else color)
                    draw.text((sx + int(stat_col_w) - 30, sy), lbl,
                             font=_font(11, bold=True), fill=_TEXT_MUTED if dead else color)
        # Crit on its own line
        crit_y = stat_y + 4 * 22
        if dead:
            crit_text = f"Crit {stat_crit}%"
            if is_left:
                draw.text((info_x, crit_y), crit_text, font=_font(11, bold=True), fill=_TEXT_MUTED)
            else:
                cw = _tw(draw, crit_text, _font(11, bold=True))
                draw.text((info_x + int(stat_col_w) * 2 - cw, crit_y), crit_text, font=_font(11, bold=True), fill=_TEXT_MUTED)
        else:
            if is_left:
                draw.text((info_x, crit_y), "Crit", font=_font(11, bold=True), fill=_TEXT_MUTED)
                draw.text((info_x + 30, crit_y), f"{stat_crit}%", font=font_stat_val, fill=(236, 201, 75))
            else:
                pct_text = f"{stat_crit}%"
                pct_w = _tw(draw, pct_text, font_stat_val)
                label_w = _tw(draw, "Crit", _font(11, bold=True))
                draw.text((info_x + int(stat_col_w) * 2 - label_w - 6 - pct_w, crit_y), pct_text, font=font_stat_val, fill=(236, 201, 75))
                draw.text((info_x + int(stat_col_w) * 2 - label_w, crit_y), "Crit", font=_font(11, bold=True), fill=_TEXT_MUTED)

        w_data = cr.get("_weapon") if isinstance(cr.get("_weapon"), dict) else None
        if w_data:
            w_rarity = str(w_data.get("rarity", "Common"))
            w_rc = _col(w_rarity)
            w_sz = 48
            if is_left:
                wi_x = info_x + info_w - w_sz
            else:
                wi_x = info_x
            wi_y = stat_y + 48

            w_bg = Image.new("RGBA", (w_sz, w_sz), (0, 0, 0, 0))
            w_d = ImageDraw.Draw(w_bg)
            w_d.rounded_rectangle((0, 0, w_sz - 1, w_sz - 1), radius=6, fill=(*_PANEL, 200), outline=w_rc, width=2)
            img.paste(w_bg, (wi_x, wi_y), w_bg)

            weapon_type = str(w_data.get("weapon_type", "sword") or "sword")
            weapon_icon = self._load_asset("weapons", weapon_type, (w_sz - 10, w_sz - 10))
            if weapon_icon:
                img.paste(weapon_icon, (wi_x + 5, wi_y + 5), weapon_icon)
            else:
                draw.line((wi_x + 14, wi_y + 36, wi_x + 32, wi_y + 12), fill=w_rc, width=4)
                draw.line((wi_x + 12, wi_y + 34, wi_x + 26, wi_y + 42), fill=w_rc, width=3)

            passive_raw = w_data.get("passive")
            if passive_raw:
                try:
                    passive = json.loads(str(passive_raw))
                    passive_key = str(passive.get("key", "")) if isinstance(passive, dict) else ""
                except Exception:
                    passive_key = ""
                if passive_key:
                    passive_icon = self._load_asset("passives", passive_key, (28, 28))
                    if passive_icon:
                        if is_left:
                            img.paste(passive_icon, (wi_x - 32, wi_y + 10), passive_icon)
                        else:
                            img.paste(passive_icon, (wi_x + w_sz + 4, wi_y + 10), passive_icon)

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
        else:
            path = get_asset_file_path(kind, key)
        if path and path.exists():
            try:
                a = Image.open(path).convert("RGBA")
                if kind == "creatures":
                    bbox = a.getbbox()
                    if bbox:
                        a = a.crop(bbox)
                    a = a.resize(size, Image.Resampling.NEAREST)
                else:
                    a.thumbnail(size, Image.Resampling.LANCZOS)
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
