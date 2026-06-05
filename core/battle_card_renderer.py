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
    "Ancient": (249, 115, 22), "Divine": (254, 243, 199),
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

        W, H = 1600, 900
        header_h = 150
        card_h = 166
        card_gap = 16
        col_w = 600
        col_left_x = 58
        col_right_x = W - 58 - col_w
        center_x = col_left_x + col_w + 24
        center_w = col_right_x - center_x - 24
        card_start_y = header_h + 26

        img = self._get_zone_bg(str(data.get("zone_key", "bloodmoon_forest")), W, H)
        darken = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.blend(img, darken, 0.82)
        vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        vd.rectangle((0, 0, W, H), outline=(0, 0, 0, 180), width=18)
        vd.rectangle((0, 0, W, 180), fill=(0, 0, 0, 72))
        img.paste(vignette, (0, 0), vignette)
        draw = ImageDraw.Draw(img)

        if data.get("has_ultra_rare"):
            self._apply_ultra_border_custom(img, W, H)

        player_name = str(data.get("player_name", "Hunter"))
        enemy_name = str(data.get("enemy_name", "Opponent"))
        won = data.get("won")
        if won is True:
            result_text = "VICTORY"
            result_color = _GREEN
        elif won is False:
            result_text = "DEFEAT"
            result_color = _RED
        elif data.get("turn"):
            result_text = f"TURN {int(data.get('turn', 0))}"
            result_color = _GOLD
        else:
            result_text = "ARENA BATTLE"
            result_color = _GOLD

        left_max_total = sum(max(1, int(cr.get("hp", 1))) for cr in left_team)
        right_max_total = sum(max(1, int(cr.get("hp", 1))) for cr in right_team)
        left_cur_total = sum(max(0, int(left_hp[i] if i < len(left_hp) else left_team[i].get("hp", 1))) for i in range(len(left_team)))
        right_cur_total = sum(max(0, int(right_hp[i] if i < len(right_hp) else right_team[i].get("hp", 1))) for i in range(len(right_team)))
        left_ratio = left_cur_total / max(1, left_max_total)
        right_ratio = right_cur_total / max(1, right_max_total)
        left_leading = left_ratio >= right_ratio

        draw.rounded_rectangle((42, 28, W - 42, 128), radius=12, fill=(10, 9, 16), outline=(72, 66, 86), width=1)
        draw.line((58, 128, W - 58, 128), fill=(*result_color, 120), width=2)
        name_font = _font(30, bold=True)
        rank_font = _font(13)
        left_name = _fit_name(draw, player_name, 360, name_font)
        right_name = _fit_name(draw, enemy_name, 360, name_font)
        draw.text((72, 42), left_name, font=name_font, fill=_TEXT_BRIGHT if left_leading else _TEXT)
        draw.text((72, 78), str(data.get("player_rank", ""))[:34], font=rank_font, fill=_TEXT_MUTED)
        draw.text((W - 72 - _tw(draw, right_name, name_font), 42), right_name, font=name_font, fill=_TEXT_BRIGHT if not left_leading else _TEXT)
        enemy_rank = str(data.get("enemy_rank", ""))[:34]
        draw.text((W - 72 - _tw(draw, enemy_rank, rank_font), 78), enemy_rank, font=rank_font, fill=_TEXT_MUTED)

        bar_y = 106
        side_w = 500
        def team_bar(x: int, cur: int, mx: int, color: tuple[int, int, int], align_right: bool = False) -> None:
            draw.rounded_rectangle((x, bar_y, x + side_w, bar_y + 16), radius=8, fill=(30, 18, 22), outline=(80, 55, 58))
            ratio = max(0.0, min(1.0, cur / max(1, mx)))
            fw = int(side_w * ratio)
            if fw > 0:
                if align_right:
                    draw.rounded_rectangle((x + side_w - fw, bar_y + 1, x + side_w - 1, bar_y + 15), radius=7, fill=color)
                else:
                    draw.rounded_rectangle((x + 1, bar_y + 1, x + fw, bar_y + 15), radius=7, fill=color)
            txt = f"{cur:,}/{mx:,}"
            font = _font(12, bold=True)
            tx = x + side_w - _tw(draw, txt, font) - 8 if not align_right else x + 8
            _shadow_text(draw, tx, bar_y, txt, font, _WHITE, offset=1)

        team_bar(72, left_cur_total, left_max_total, _GREEN if left_ratio > 0.35 else _RED)
        team_bar(W - 72 - side_w, right_cur_total, right_max_total, _GREEN if right_ratio > 0.35 else _RED, align_right=True)

        badge_w, badge_h = 186, 72
        badge_x = W // 2 - badge_w // 2
        badge_y = 38
        draw.rounded_rectangle((badge_x, badge_y, badge_x + badge_w, badge_y + badge_h), radius=12,
                               fill=(16, 13, 24), outline=result_color, width=2)
        result_font = _font(25, bold=True)
        result_w = _tw(draw, result_text, result_font)
        draw.text((W // 2 - result_w // 2, badge_y + 15), result_text, font=result_font, fill=result_color)
        sub = "VS" if won is not None else f"Frame {data.get('turn', 0)}"
        sub_font = _font(12, bold=True)
        draw.text((W // 2 - _tw(draw, sub, sub_font) // 2, badge_y + 48), sub, font=sub_font, fill=_TEXT_MUTED)

        draw.text((col_left_x, header_h + 2), "YOUR TEAM", font=_font(14, bold=True), fill=_TEXT_MUTED)
        right_label = "OPPONENT"
        draw.text((col_right_x + col_w - _tw(draw, right_label, _font(14, bold=True)), header_h + 2),
                  right_label, font=_font(14, bold=True), fill=_TEXT_MUTED)

        for i, cr in enumerate(left_team):
            y = card_start_y + i * (card_h + card_gap)
            cur_hp = left_hp[i] if i < len(left_hp) else int(cr.get("hp", 1))
            max_hp = int(cr.get("hp", 1))
            self._draw_compact_creature_card(draw, img, col_left_x, y, col_w, card_h, cr, cur_hp, max_hp, is_left=True)

        for i, cr in enumerate(right_team):
            y = card_start_y + i * (card_h + card_gap)
            cur_hp = right_hp[i] if i < len(right_hp) else int(cr.get("hp", 1))
            max_hp = int(cr.get("hp", 1))
            self._draw_compact_creature_card(draw, img, col_right_x, y, col_w, card_h, cr, cur_hp, max_hp, is_left=False)

        center_top = card_start_y
        center_bottom = card_start_y + 3 * card_h + 2 * card_gap
        draw.rounded_rectangle((center_x, center_top, center_x + center_w, center_bottom), radius=12,
                               fill=(10, 9, 16), outline=(64, 58, 76), width=1)
        draw.text((center_x + 22, center_top + 20), "BATTLE STATUS", font=_font(14, bold=True), fill=_TEXT_MUTED)
        draw.text((center_x + 22, center_top + 56), _fit_name(draw, player_name, center_w - 44, _font(18, bold=True)),
                  font=_font(18, bold=True), fill=_TEXT)
        draw.text((center_x + 22, center_top + 84), "versus", font=_font(12, bold=True), fill=_TEXT_MUTED)
        draw.text((center_x + 22, center_top + 108), _fit_name(draw, enemy_name, center_w - 44, _font(18, bold=True)),
                  font=_font(18, bold=True), fill=_GOLD)

        rating_change = data.get("rating_change")
        rewards = data.get("rewards") or {}
        mvp = data.get("mvp") or {}
        stat_y = center_bottom - 146
        draw.line((center_x + 22, stat_y - 18, center_x + center_w - 22, stat_y - 18), fill=(54, 48, 66), width=1)
        if rating_change is not None:
            sign = "+" if int(rating_change) > 0 else ""
            color = _GREEN if int(rating_change) >= 0 else _RED
            draw.text((center_x + 22, stat_y), "RATING", font=_font(11), fill=_TEXT_MUTED)
            draw.text((center_x + 22, stat_y + 20), f"{sign}{int(rating_change)}", font=_font(24, bold=True), fill=color)
        if mvp:
            draw.text((center_x + 22, stat_y + 62), "MVP", font=_font(11), fill=_TEXT_MUTED)
            draw.text((center_x + 22, stat_y + 82), _fit_name(draw, str(mvp.get("name", "")), center_w - 44, _font(17, bold=True)),
                      font=_font(17, bold=True), fill=_GOLD)
        elif isinstance(rewards, dict) and rewards:
            gold = int(rewards.get("gold", 0))
            gems = int(rewards.get("gems", 0))
            draw.text((center_x + 22, stat_y + 62), "REWARDS", font=_font(11), fill=_TEXT_MUTED)
            draw.text((center_x + 22, stat_y + 82), f"{gold:,} souls  /  {gems} gems", font=_font(15, bold=True), fill=_GOLD)

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
                                    cur_hp: int, max_hp: int, is_left: bool) -> None:
        rarity = str(cr.get("rarity", "Common"))
        rc = _col(rarity)
        name = str(cr.get("name", "?"))
        level = int(cr.get("level", 1))
        attack = int(cr.get("attack", 0))
        defense = int(cr.get("defense", 0))
        speed = int(cr.get("speed", 1))
        dead = cur_hp <= 0

        pw = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pw)
        fill_col = _lerp(_PANEL_DARK, rc, 0.035)
        alpha = 148 if dead else 218
        outline = _lerp(rc, _BORDER, 0.24 if not dead else 0.65)
        pd.rounded_rectangle((0, 0, w - 1, h - 1), radius=12, fill=(*fill_col, alpha), outline=(*outline, 210), width=2)
        pd.rectangle((1, 1, w - 2, 7), fill=(*rc, 190 if not dead else 70))
        img.paste(pw, (x, y), pw)

        ps = 132
        pad = 16
        p_x = x + pad if is_left else x + w - ps - pad
        p_y = y + (h - ps) // 2

        portrait = self._load_asset("creatures", normalize_key(name), (ps, ps))
        if portrait is None:
            portrait = Image.new("RGBA", (ps, ps), (0, 0, 0, 0))
            pdd = ImageDraw.Draw(portrait)
            pdd.rounded_rectangle((2, 2, ps - 2, ps - 2), radius=12, fill=(*_PANEL_DARK, 255), outline=_BORDER)

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

        font_name = _font(24, bold=True)
        nc = _TEXT_MUTED if dead else _TEXT_BRIGHT
        display_name = _fit_name(draw, name, info_w - 94, font_name)
        nw = _tw(draw, display_name, font_name)
        draw.text((info_x, y + 20), display_name, font=font_name, fill=nc)

        font_lv = _font(16, bold=True)
        lv_text = f"L.{level}"
        draw.text((info_x + nw + 12, y + 25), lv_text, font=font_lv, fill=rc if not dead else _TEXT_MUTED)

        bar_x = info_x
        bar_y = y + 62
        bar_w = info_w
        bar_h = 28
        ratio = max(0.0, min(1.0, cur_hp / max(1, max_hp)))

        draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=8,
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
            draw.rounded_rectangle((bar_x + 1, bar_y + 1, bar_x + 1 + fw, bar_y + bar_h - 1), radius=7, fill=hp_color)

        font_hp = _font(15, bold=True)
        hp_text = f"{cur_hp}/{max_hp}"
        hw = _tw(draw, hp_text, font_hp)
        _shadow_text(draw, bar_x + bar_w - hw - 10, bar_y + 4, hp_text, font_hp, _WHITE, offset=1)
        pct_text = f"{int(ratio*100)}%"
        _shadow_text(draw, bar_x + 10, bar_y + 4, pct_text, font_hp, _WHITE, offset=1)

        stat_y = bar_y + bar_h + 18
        font_stat_lbl = _font(12)
        font_stat_val = _font(17, bold=True)
        stats = (("ATK", attack, _RED), ("DEF", defense, _BLUE))
        for idx, (label, value, color) in enumerate(stats):
            sx = info_x + idx * 118
            draw.text((sx, stat_y), label, font=font_stat_lbl, fill=_TEXT_MUTED)
            draw.text((sx + 34, stat_y - 3), str(value), font=font_stat_val, fill=color if not dead else _TEXT_MUTED)

        rarity_text = rarity.upper()
        rarity_font = _font(11, bold=True)
        rw = _tw(draw, rarity_text, rarity_font) + 18
        draw.rounded_rectangle((info_x + info_w - rw, y + 23, info_x + info_w, y + 47), radius=6,
                               fill=(12, 10, 18), outline=rc if not dead else _BORDER)
        draw.text((info_x + info_w - rw + 9, y + 28), rarity_text, font=rarity_font, fill=rc if not dead else _TEXT_MUTED)

        w_data = cr.get("_weapon") if isinstance(cr.get("_weapon"), dict) else None
        if w_data and not dead:
            w_rarity = str(w_data.get("rarity", "Common"))
            w_rc = _col(w_rarity)
            w_sz = 40
            wi_x = info_x + info_w - w_sz
            wi_y = stat_y - 10

            w_bg = Image.new("RGBA", (w_sz, w_sz), (0, 0, 0, 0))
            w_d = ImageDraw.Draw(w_bg)
            w_d.rounded_rectangle((0, 0, w_sz - 1, w_sz - 1), radius=6, fill=(*_PANEL, 200), outline=w_rc, width=2)
            img.paste(w_bg, (wi_x, wi_y), w_bg)

            weapon_type = str(w_data.get("weapon_type", "sword") or "sword")
            weapon_icon = self._load_asset("weapons", weapon_type, (w_sz - 8, w_sz - 8))
            if weapon_icon:
                img.paste(weapon_icon, (wi_x + 4, wi_y + 4), weapon_icon)
            else:
                draw.line((wi_x + 12, wi_y + 30, wi_x + 28, wi_y + 10), fill=w_rc, width=4)
                draw.line((wi_x + 10, wi_y + 28, wi_x + 24, wi_y + 38), fill=w_rc, width=3)

            passive_raw = w_data.get("passive")
            if passive_raw:
                try:
                    passive = json.loads(str(passive_raw))
                    passive_key = str(passive.get("key", "")) if isinstance(passive, dict) else ""
                except Exception:
                    passive_key = ""
                if passive_key:
                    passive_icon = self._load_asset("passives", passive_key, (22, 22))
                    if passive_icon:
                        img.paste(passive_icon, (wi_x - 26, wi_y + 9), passive_icon)
            return
            
            # Since we don't have distinct weapon icons, just draw a little sword symbol
            w_font = _font(16)
            ws_w = _tw(draw, "⚔", w_font)
            draw.text((wi_x + (w_sz-ws_w)//2, wi_y + 4), "⚔", font=w_font, fill=w_rc)

    # ── Background ─────────────────────────────────────

    def _build_background(self, zone_key: str) -> Image.Image:
        img = self._get_zone_bg(zone_key, W, H)
        darken = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.blend(img, darken, 0.60)
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
                if kind == "creatures" and max(a.size) < min(size):
                    scale = max(1, min(size) // max(1, max(a.size)))
                    a = a.resize((a.width * scale, a.height * scale), Image.Resampling.NEAREST)
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
