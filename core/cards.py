from __future__ import annotations

import functools
import json
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from core import card_ui as cui
from core.content_config import ASSET_DIR, ROOT_DIR, get_asset_file_path, get_creature_asset_path, safe_key
from core.render_cache import cached_render
from core.rpg_data import CHARMS, RARITY_INDEX, SIGILS, WEAPON_PASSIVES, WEAPON_TYPES, ZONES, normalize_key


# ── Palette ──────────────────────────────────────────────────────
_BG_TOP = (16, 12, 28)
_BG_BOT = (8, 6, 14)
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
_DIM_CAUGHT = (40, 36, 50)
_LOCKED_TEXT = (60, 55, 75)

_RARITY = {
    "Common": (139, 148, 158), "Uncommon": (74, 222, 128),
    "Rare": (56, 189, 248), "Epic": (167, 139, 250),
    "Legendary": (250, 204, 21), "Mythic": (251, 113, 133),
    "Ancient": (249, 115, 22), "Patreon": (255, 66, 77),
    "Divine": (254, 243, 199),
    "Eldritch": (34, 211, 238), "Abyssal": (130, 90, 200),
    "Prismatic": (16, 185, 129), "Ethereal": (96, 165, 250),
    "Void Lord": (30, 80, 130), "Hidden": (147, 51, 234),
}


# ── Fonts ────────────────────────────────────────────────────────
_FONT_CACHE: dict[str, ImageFont.ImageFont] = {}

def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    k = f"{size}_{bold}"
    if k in _FONT_CACHE:
        return _FONT_CACHE[k]
    names = (
        str(ROOT_DIR / "assets" / "fonts" / "alagard.ttf"),
        "CascadiaMono.ttf",
        "consolab.ttf" if bold else "consola.ttf",
        "AGENCYB.TTF" if bold else "AGENCYR.TTF",
        "bahnschrift.ttf",
        "courbd.ttf" if bold else "cour.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "DejaVuSans.ttf", "LiberationSans-Bold.ttf" if bold else "LiberationSans.ttf",
        "NotoSans-Bold.ttf" if bold else "NotoSans.ttf",
    )
    for n in names:
        try:
            font_dir = Path("C:/Windows/Fonts")
            f = ImageFont.truetype(str(font_dir / n), size)
            _FONT_CACHE[k] = f
            return f
        except OSError:
            try:
                f = ImageFont.truetype(n, size)
                _FONT_CACHE[k] = f
                return f
            except OSError:
                continue
    f = ImageFont.load_default()
    _FONT_CACHE[k] = f
    return f

F10 = _font(10); F11 = _font(11); F12 = _font(12); F13 = _font(13)
F14 = _font(14); F15 = _font(15); F16 = _font(16)
F18 = _font(18, bold=True); F20 = _font(20, bold=True); F22 = _font(22, bold=True)
F24 = _font(24, bold=True); F26 = _font(26, bold=True); F28 = _font(28, bold=True)
F30 = _font(30, bold=True); F32 = _font(32, bold=True); F36 = _font(36, bold=True)


def _get(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None: return fallback
    if isinstance(row, dict): return row.get(key, fallback)
    try: return row[key]
    except (KeyError, IndexError, TypeError): return fallback

def _col(rarity: str | None) -> tuple[int, int, int]:
    return _RARITY.get(str(rarity or "Common"), (139, 148, 158))

def _rank(rarity: str | None) -> int:
    return RARITY_INDEX.get(str(rarity or "Common"), 0)

def _tw(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]

def _fit(draw, text: str, mw: int, font):
    s = str(text).upper()
    if _tw(draw, s, font) <= mw: return s
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _tw(draw, s[:mid] + "...", font) <= mw: lo = mid
        else: hi = mid - 1
    return s[:lo] + "..." if lo > 0 else "..."

def _lerp_color(a, b, t):
    t = max(0, min(1, t))
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))

def _bg(w: int, h: int, *, particle_count: int = 0) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    gradient = Image.new("RGB", (1, 256))
    gd = ImageDraw.Draw(gradient)
    for y in range(256):
        t = y / 255
        gd.point((0, y), _lerp_color(_BG_TOP, _BG_BOT, t))
    img = gradient.resize((w, h), Image.Resampling.BILINEAR)
    noise = Image.effect_noise((w, h), 14).convert("L")
    noise = noise.point(lambda p: p // 12)
    noise_rgb = Image.merge("RGB", (noise, noise, noise))
    img = Image.blend(img, noise_rgb, 0.18)
    if particle_count > 0:
        rng = __import__("random").Random(42)
        for _ in range(particle_count):
            px, py = rng.randint(0, w - 1), rng.randint(0, h - 1)
            b = rng.randint(25, 65)
            img.putpixel((px, py), (b, b, b + 5))
    draw = ImageDraw.Draw(img)
    return img, draw

def _shadow(base, box, r=10, blur=8, dy=4, opacity=50):
    sw, sh = box[2] - box[0] + blur * 2, box[3] - box[1] + blur * 2
    sh_img = Image.new("L", (sw, sh), 0)
    sd = ImageDraw.Draw(sh_img)
    sd.rounded_rectangle((blur, blur, sw - blur, sh - blur), radius=r, fill=opacity)
    sh_img = sh_img.filter(ImageFilter.GaussianBlur(blur))
    shadow_rgba = Image.merge("RGBA", (sh_img, sh_img, sh_img, sh_img))
    base.paste(shadow_rgba, (box[0] - blur, box[1] - blur + dy), shadow_rgba)

def _header(draw, title: str, subtitle: str | None, w: int, accent=_RED) -> int:
    hh = 80
    draw.rectangle((0, 0, w, hh), fill=(14, 11, 22))
    for i in range(6):
        a = max(0, 35 - i * 6)
        draw.rectangle((0, hh - 8 + i, w, hh - 8 + i + 1), fill=(*_lerp_color(accent, (0, 0, 0), i / 6), a))
    glow = _lerp_color(accent, (255, 255, 255), 0.6)
    draw.rectangle((0, hh - 3, w, hh), fill=accent)
    draw.rectangle((0, hh - 1, w, hh), fill=glow)
    draw.text((28, 14), title, font=F26, fill=_TEXT_BRIGHT)
    if subtitle:
        draw.text((30, 46), subtitle, font=F14, fill=_TEXT_MUTED)
    lw = _tw(draw, "ABYSSIA", F18)
    draw.text((w - lw - 28, 18), "ABYSSIA", font=F18, fill=_GOLD)
    return hh + 14

def _panel(img, draw, box, *, fill=_PANEL, r=12, outline=None):
    _shadow(img, box, r=r, blur=10, dy=5, opacity=55)
    oc = outline or _BORDER
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=oc)
    for i in range(2):
        draw.rounded_rectangle((box[0] + i, box[1] + i, box[2] - i, box[3] - i), radius=max(0, r - i),
            outline=(*_lerp_color(oc, (255, 255, 255), 0.08), max(0, 18 - i * 8)))

def _bar(draw, x: int, y: int, w: int, h: int, cur: int, mx: int, color):
    mx = max(1, mx); r = max(0.0, min(1.0, cur / mx)); hr = h // 2
    draw.rounded_rectangle((x, y, x + w, y + h), radius=hr, fill=(16, 13, 24), outline=(38, 32, 48))
    fw = max(h, int(w * r))
    if fw > 0:
        for i in range(h):
            lc = _lerp_color(color, _lerp_color(color, (0, 0, 0), 0.3), i / max(1, h - 1))
            draw.line((x + 2, y + i, x + fw - 2, y + i), fill=lc)
        draw.rounded_rectangle((x + 1, y + 1, x + fw - 1, y + h - 1), radius=hr, outline=_lerp_color(color, (255, 255, 255), 0.3))

@functools.lru_cache(maxsize=512)
def _art(kind: str, key: str, size, *, colorize: tuple[int, int, int] | None = None):
    if kind == "creatures":
        path = get_creature_asset_path(safe_key(key))
    else:
        path = get_asset_file_path(kind, key) or (ASSET_DIR / kind / f"{safe_key(key)}.png")
    path = path if path and path.exists() else None
    if path is not None:
        try:
            a = Image.open(path).convert("RGBA")
            if kind == "creatures" and max(a.size) < min(size):
                scale = max(1, min(size) // max(1, max(a.size)))
                a = a.resize((a.width * scale, a.height * scale), Image.Resampling.NEAREST)
            if colorize:
                r, g, b = colorize
                alpha = a.split()[-1] if a.mode == "RGBA" else None
                gray = ImageOps.grayscale(a)
                a = ImageOps.colorize(gray, (0, 0, 0), (r, g, b)).convert("RGBA")
                if alpha:
                    a.putalpha(alpha)
            a.thumbnail(size, Image.Resampling.LANCZOS)
            c = Image.new("RGBA", size, (0, 0, 0, 0))
            c.alpha_composite(a, ((size[0] - a.width) // 2, (size[1] - a.height) // 2))
            return c
        except OSError:
            pass
    fb = Image.new("RGBA", size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fb)
    fd.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=6, fill=(*_PANEL2, 255), outline=(*_BORDER, 255))
    return fb

def _paste(base, art, xy, r=6):
    if art.mode == "RGBA":
        art_rgb = Image.new("RGB", art.size, _PANEL2)
        art_rgb.paste(art, (0, 0), art)
        art = art_rgb
    m = Image.new("L", art.size, 0)
    md = ImageDraw.Draw(m)
    md.rounded_rectangle((0, 0, art.width, art.height), radius=r, fill=255)
    base.paste(art, xy, m)

def _save(img):
    b = BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b

def _metric_box(img, draw, x, y, w, h, label, value, icon_key=None, accent=None):
    _shadow(img, (x, y, x + w, y + h), r=8, blur=6, dy=3, opacity=40)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=_PANEL2, outline=_BORDER)
    fs = max(11, min(14, 11 + h // 20))
    fv = max(18, min(28, 18 + h // 15))
    draw.text((x + 12, y + 6), label, font=_font(fs), fill=_TEXT_MUTED)
    draw.text((x + 12, y + 6 + fs + 8), value, font=_font(fv), fill=accent or _TEXT_BRIGHT)
    if icon_key:
        icon = _art("currency", icon_key, (22, 22))
        img.paste(icon, (x + w - 32, y + 12), icon)

def _rarity_badge(draw, x, y, rarity):
    rc = _col(rarity)
    label = rarity.upper()[:3]
    tw = _tw(draw, label, F10) + 12
    draw.rounded_rectangle((x, y, x + tw, y + 18), radius=4, fill=(*rc, 40), outline=rc)
    draw.text((x + 6, y + 3), label, font=F10, fill=rc)
    return tw


def _center_text(draw, box, text: str, font, fill) -> None:
    x1, y1, x2, y2 = box
    b = draw.textbbox((0, 0), text, font=font)
    tw, th = b[2] - b[0], b[3] - b[1]
    draw.text((x1 + (x2 - x1 - tw) // 2, y1 + (y2 - y1 - th) // 2), text, font=font, fill=fill)


def _pill(draw, x: int, y: int, text: str, color, font=F11, *, pad_x: int = 9, h: int = 22) -> int:
    w = _tw(draw, text, font) + pad_x * 2
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=(*color, 38), outline=color)
    draw.text((x + pad_x, y + (h - 12) // 2 - 1), text, font=font, fill=color)
    return w


def _icon_text(img, draw, x: int, y: int, kind: str, key: str, text: str, color, *,
               icon_size: int = 24, font=F14) -> int:
    icon = _art(kind, key, (icon_size, icon_size))
    img.paste(icon, (x, y), icon)
    tx = x + icon_size + 8
    draw.text((tx, y + max(0, (icon_size - 16) // 2)), text, font=font, fill=color)
    return icon_size + 8 + _tw(draw, text, font)


def _draw_stat_tile(img, draw, x: int, y: int, w: int, h: int, label: str, value: str,
                    color, icon: tuple[str, str] | None = None) -> None:
    _shadow(img, (x, y, x + w, y + h), r=8, blur=6, dy=3, opacity=32)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=_PANEL2, outline=(*color, 130))
    draw.text((x + 12, y + 8), label, font=F11, fill=_TEXT_MUTED)
    if icon:
        icon_img = _art(icon[0], icon[1], (28, 28))
        img.paste(icon_img, (x + w - 42, y + 14), icon_img)
    draw.text((x + 12, y + 28), value, font=F20, fill=color)


def _weapon_icon_key(row: Any) -> str:
    return str(_get(row, "weapon_type", "sword") or "sword")


def _deal_icon_key(deal: dict[str, Any]) -> str:
    key = str(deal.get("item_key") or "cache")
    if key == "mixed_cache":
        return "relic"
    if key == "mixed_relic":
        return "treasure"
    if key in {"cache", "relic", "treasure"}:
        return key
    return "cache"


# ══════════════════════════════════════════════════════════════════
#  HUNT CARD
# ══════════════════════════════════════════════════════════════════
def render_hunt_card(
    hunter_name, zone_name, *, rolls, souls, gems, xp=0,
    materials: dict[str, int], monsters: list[dict[str, Any]],
    swords_spent, swords_found, levels=0,
):
    W, H = 3000, 2400
    img, draw = _bg(W, H, particle_count=400)
    top = _header(draw, "HUNT RESULT", f"{hunter_name}  |  {zone_name}", W, _RED)
    cx = 40
    cy = top + 24

    if levels:
        draw.text((cx, cy), f"LEVEL UP x{levels}!", font=F32, fill=_GOLD)
        cy += 60

    if monsters:
        for idx, mon in enumerate(monsters):
            if idx >= 16:
                break
            cols = 4 if len(monsters) > 4 else (2 if len(monsters) > 2 else 1)
            cw = (W - 110) // cols - 6
            col = idx % cols
            row = idx // cols
            bx = cx + col * (cw + 14)
            by = cy + row * (cw + 30)

            rc = _col(str(_get(mon, "rarity", "Common")))
            _shadow(img, (bx, by, bx + cw, by + cw), r=12, blur=10, dy=5, opacity=50)
            draw.rounded_rectangle((bx, by, bx + cw, by + cw), radius=12, fill=_PANEL2, outline=rc, width=4)

            nm = str(_get(mon, "name", "?"))
            a = _art("creatures", normalize_key(nm), (cw - 32, cw - 32))
            _paste(img, a, (bx + 16, by + 16), r=8)

            rl = str(_get(mon, "rarity", ""))[:3].upper()
            draw.text((bx + (cw - _tw(draw, rl, F12)) // 2, by + cw - 30), rl, font=F12, fill=rc)

    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  TEAM CARD
# ══════════════════════════════════════════════════════════════════
def render_team_card(display_name: str, team: Iterable[Any], *, team_power: int,
                     weapons: dict[int, Any] | None = None) -> BytesIO:
    W, H = 1180, 560
    img, draw = _bg(W, H, particle_count=260)
    top = _header(draw, "BATTLE TEAM", display_name, W, _PURPLE)
    mx, my = 28, top
    _panel(img, draw, (mx, my, W - mx, H - 22), r=10, outline=_PURPLE)
    cx = mx + 22
    members = list(team)[:3]

    draw.text((cx, my + 20), "TEAM POWER", font=F13, fill=_TEXT_MUTED)
    draw.text((cx + 120, my + 12), f"{team_power:,}", font=F30, fill=_GOLD)
    draw.text((W - 270, my + 20), f"{len(members)}/3 slots locked", font=F14, fill=_TEXT_MUTED)

    gap = 18
    card_w = (W - 2 * mx - 44 - gap * 2) // 3
    card_h = 370
    base_y = my + 76

    for idx, cr in enumerate(members):
        gx = cx + idx * (card_w + gap)
        gy = base_y
        gw = card_w
        rc = _col(str(_get(cr, "rarity", "Common")))
        _shadow(img, (gx, gy, gx + gw, gy + card_h), r=10, blur=8, dy=4, opacity=45)
        draw.rounded_rectangle((gx, gy, gx + gw, gy + card_h), radius=10,
                               fill=_lerp_color(_PANEL2, rc, 0.05), outline=rc, width=2)
        draw.rectangle((gx + 1, gy + 1, gx + gw - 1, gy + 8), fill=rc)
        _pill(draw, gx + 16, gy + 18, f"SLOT {idx + 1}", rc, F11)
        _rarity_badge(draw, gx + gw - 80, gy + 20, str(_get(cr, "rarity", "Common")))

        art_size = 126
        a = _art("creatures", normalize_key(str(_get(cr, "name", "?"))), (art_size, art_size))
        glow = Image.new("RGBA", (art_size + 28, art_size + 28), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((0, 0, art_size + 27, art_size + 27), fill=(*rc, 42))
        glow = glow.filter(ImageFilter.GaussianBlur(8))
        img.paste(glow, (gx + gw // 2 - (art_size + 28) // 2, gy + 44), glow)
        img.paste(a, (gx + gw // 2 - art_size // 2, gy + 58), a)

        nm = str(_get(cr, "name", "?"))
        name = _fit(draw, nm, gw - 24, F20)
        draw.text((gx + gw // 2 - _tw(draw, name, F20) // 2, gy + 190), name, font=F20, fill=_TEXT_BRIGHT)
        lv = int(_get(cr, "level", 1))
        draw.text((gx + gw // 2 - _tw(draw, f"Lv.{lv}", F14) // 2, gy + 218), f"Lv.{lv}", font=F14, fill=_TEXT_MUTED)

        stats_y = gy + 252
        stat_w = (gw - 44) // 3
        from core.battle_engine import compute_display_stats
        bstats = compute_display_stats(cr)
        for si, (lab, val, sc) in enumerate([("HP", bstats["HP"], _RED), ("STR", bstats["STR"], _GOLD), ("MANA", bstats["MANA"], _PURPLE)]):
            sx = gx + 14 + si * (stat_w + 8)
            draw.rounded_rectangle((sx, stats_y, sx + stat_w, stats_y + 50), radius=7, fill=_PANEL, outline=(*sc, 120))
            draw.text((sx + 9, stats_y + 7), lab, font=F10, fill=_TEXT_MUTED)
            draw.text((sx + 9, stats_y + 22), str(val), font=F16, fill=sc)

        if weapons:
            cid = int(_get(cr, "id", 0))
            w = weapons.get(cid)
            if w:
                wx, wy = gx + 16, gy + card_h - 52
                w_icon = _art("weapons", _weapon_icon_key(w), (34, 34), colorize=_col(str(_get(w, "rarity", "Common"))))
                img.paste(w_icon, (wx, wy), w_icon)
                wn = str(_get(w, "name", "?"))
                wq = str(_get(w, "quality", "Normal"))
                if wq != "Normal":
                    wdisplay = f"{wq} {wn}"
                else:
                    wdisplay = wn
                draw.text((wx + 44, wy + 2), _fit(draw, wdisplay, gw - 70, F12), font=F12, fill=_col(str(_get(w, "rarity", "Common"))))
                passive_raw = _get(w, "passive", None)
                if passive_raw:
                    try:
                        passive = json.loads(str(passive_raw))
                        if isinstance(passive, dict) and passive.get("key"):
                            p_chance = passive.get("chance", 0)
                            p_key = str(passive.get("key", ""))
                            p_icon = _art("passives", p_key, (18, 18))
                            img.paste(p_icon, (wx + 44, wy + 21), p_icon)
                            draw.text((wx + 66, wy + 22), f"{p_chance}%", font=F10, fill=_GOLD)
                    except Exception:
                        pass
    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  BATTLE CARD
# ══════════════════════════════════════════════════════════════════
def render_battle_card(left_name, right_name, left_team, right_team, *, left_hp=None, right_hp=None, log=None, winner=None, rating_change=None, rewards=None):
    W, H = 1500, 1100
    img, draw = _bg(W, H, particle_count=400)
    top = _header(draw, "ARENA BATTLE", f"{left_name}  vs  {right_name}", W, _RED)
    left, right = list(left_team)[:3], list(right_team)[:3]
    pw, ph = 640, 740
    py = top
    _panel(img, draw, (22, py, 22 + pw, py + ph))
    draw.text((36, py + 14), left_name, font=F20, fill=_TEXT_BRIGHT)
    rpx = W - 22 - pw
    _panel(img, draw, (rpx, py, rpx + pw, py + ph))
    draw.text((rpx + 16, py + 14), right_name, font=F20, fill=_TEXT_BRIGHT)
    vs_cx, vs_y, vs_s = W // 2, py + ph // 2 - 42, 52
    for i in range(4):
        s, a = vs_s + i * 3, max(0, 40 - i * 12)
        diamond = [(vs_cx, vs_y - i), (vs_cx + s, vs_y + s - i), (vs_cx, vs_y + s * 2 - i), (vs_cx - s, vs_y + s - i)]
        draw.polygon(diamond, outline=(*_RED, a))
    diamond = [(vs_cx, vs_y), (vs_cx + vs_s, vs_y + vs_s), (vs_cx, vs_y + vs_s * 2), (vs_cx - vs_s, vs_y + vs_s)]
    draw.polygon(diamond, fill=(18, 14, 26), outline=_RED, width=3)
    vs_t = "VS"
    draw.text((vs_cx - _tw(draw, vs_t, F26) // 2, vs_y + vs_s - 16), vs_t, font=F26, fill=_GOLD)

    def draw_team(team, start_x, start_y, hp_list):
        y = start_y
        for idx, cr in enumerate(team):
            hp = hp_list[idx] if hp_list and idx < len(hp_list) else int(_get(cr, "hp", 1))
            rh = 200
            rc = _col(str(_get(cr, "rarity", "Common")))
            _shadow(img, (start_x, y, start_x + pw - 22, y + rh), r=8, blur=6, dy=3, opacity=40)
            draw.rounded_rectangle((start_x, y, start_x + pw - 22, y + rh), radius=8, fill=_PANEL2, outline=rc)
            a = _art("creatures", normalize_key(str(_get(cr, "name", "?"))), (120, 120))
            _paste(img, a, (start_x + 10, y + 30), r=6)
            tx = start_x + 150
            nm = str(_get(cr, "name", "?"))
            lv = int(_get(cr, "level", 1))
            mhp = int(_get(cr, "hp", 1))
            draw.text((tx, y + 16), _fit(draw, nm, pw - 200, F22), font=F22, fill=_TEXT_BRIGHT)
            _rarity_badge(draw, tx, y + 44, str(_get(cr, "rarity", "Common")))
            rl = str(_get(cr, "rarity", ""))[:3].upper()
            draw.text((tx + _tw(draw, rl, F10) + 18, y + 44), f"Lv.{lv}  |  {_get(cr, 'ability', '')}", font=F14, fill=_TEXT_MUTED)
            draw.text((tx, y + 76), f"STR {_get(cr, 'str_stat', 0)}", font=F15, fill=_GOLD)
            draw.text((tx + 100, y + 76), f"DEF {_get(cr, 'pr_stat', 0)}", font=F15, fill=_BLUE)
            _bar(draw, tx, y + 106, pw - 220, 20, max(0, hp), mhp, _RED)
            y += rh + 16
        return y

    draw_team(left, 34, py + 50, left_hp)
    draw_team(right, rpx + 12, py + 50, right_hp)
    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  PROFILE CARD
# ══════════════════════════════════════════════════════════════════
_PROFILE_ZONE_STYLES: dict[str, dict[str, Any]] = {
    "forgotten_woods": {"sky": (84, 133, 168), "mid": (37, 78, 76), "ground": (42, 103, 49), "accent": (86, 190, 106), "trees": True},
    "grave_marsh": {"sky": (99, 117, 111), "mid": (47, 63, 58), "ground": (66, 82, 49), "accent": (130, 168, 92), "fog": True},
    "bloodmoon_forest": {"sky": (99, 34, 46), "mid": (45, 19, 28), "ground": (51, 70, 42), "accent": (230, 74, 74), "trees": True, "moon": True},
    "ashen_wastes": {"sky": (123, 111, 89), "mid": (66, 62, 54), "ground": (104, 91, 63), "accent": (221, 165, 91), "fog": True},
    "infernal_catacombs": {"sky": (104, 43, 30), "mid": (45, 17, 13), "ground": (75, 43, 27), "accent": (245, 112, 56), "glow": True},
    "abyssal_depths": {"sky": (29, 54, 89), "mid": (8, 18, 38), "ground": (16, 42, 58), "accent": (55, 225, 210), "stars": True, "fog": True},
    "void_realm": {"sky": (41, 31, 83), "mid": (13, 9, 35), "ground": (32, 21, 54), "accent": (170, 95, 245), "stars": True},
    "cursed_sanctum": {"sky": (71, 43, 93), "mid": (25, 15, 45), "ground": (54, 33, 66), "accent": (192, 108, 230), "glow": True},
    "starless_menagerie": {"sky": (40, 55, 106), "mid": (12, 17, 47), "ground": (26, 33, 73), "accent": (96, 165, 250), "stars": True},
    "throne_of_teeth": {"sky": (103, 74, 78), "mid": (42, 25, 31), "ground": (82, 58, 50), "accent": (235, 195, 80), "fog": True},
    "black_sun_gate": {"sky": (27, 24, 67), "mid": (6, 5, 25), "ground": (20, 20, 42), "accent": (250, 204, 21), "stars": True, "gate": True},
}


def _profile_color(raw: Any, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    text = str(raw or "").strip().lstrip("#")
    if len(text) == 6:
        try:
            return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
    return fallback


def _profile_seed(text: str) -> int:
    return sum((idx + 1) * ord(ch) for idx, ch in enumerate(text)) or 17


def _profile_panel(img: Image.Image, box, fill, *, radius: int = 0, outline=None, width: int = 1) -> None:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if radius:
        d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    else:
        d.rectangle(box, fill=fill, outline=outline, width=width)
    img.alpha_composite(layer)


def _profile_text(draw: ImageDraw.ImageDraw, xy, text: str, font, fill,
                  *, shadow=(0, 0, 0, 150), offset: int = 2) -> None:
    x, y = xy
    draw.text((x + offset, y + offset), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def _profile_background(W: int, H: int, zone_key: str, accent: tuple[int, int, int]) -> Image.Image:
    style = _PROFILE_ZONE_STYLES.get(zone_key, _PROFILE_ZONE_STYLES["void_realm"])
    sky = tuple(style["sky"])
    mid = tuple(style["mid"])
    ground = tuple(style["ground"])
    horizon = int(H * 0.55)
    img = Image.new("RGB", (W, H), sky)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        if y < horizon:
            t = y / max(1, horizon)
            color = _lerp_color(sky, mid, t)
        else:
            t = (y - horizon) / max(1, H - horizon)
            color = _lerp_color(mid, ground, min(1, t * 1.3))
        draw.line((0, y, W, y), fill=color)

    rng = __import__("random").Random(_profile_seed(zone_key))
    if style.get("stars"):
        for _ in range(110):
            x = rng.randint(0, W - 1)
            y = rng.randint(10, horizon - 35)
            b = rng.randint(130, 238)
            r = 1 if rng.random() < 0.82 else 2
            draw.ellipse((x, y, x + r, y + r), fill=(b, b, min(255, b + 16)))

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    glow_color = tuple(style.get("accent", accent))
    if style.get("moon"):
        gd.ellipse((W - 195, 38, W - 92, 141), fill=(*glow_color, 82))
        gd.ellipse((W - 176, 55, W - 110, 121), fill=(245, 214, 196, 115))
    elif style.get("glow") or style.get("stars"):
        cx, cy = W - 150, 80
        for r in range(170, 12, -18):
            gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*glow_color, max(2, 44 - r // 5)))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    ridge = []
    for x in range(-40, W + 80, 90):
        y = horizon - rng.randint(10, 86)
        ridge.append((x, y))
    draw.polygon([(0, horizon + 34), *ridge, (W, horizon + 60), (W, H), (0, H)],
                 fill=_lerp_color(mid, (0, 0, 0), 0.28))

    if style.get("gate"):
        gx = W - 210
        draw.rectangle((gx, horizon - 108, gx + 28, horizon + 42), fill=(7, 7, 18))
        draw.rectangle((gx + 112, horizon - 108, gx + 140, horizon + 42), fill=(7, 7, 18))
        draw.rectangle((gx + 22, horizon - 108, gx + 118, horizon - 82), fill=(7, 7, 18))
        draw.ellipse((gx + 42, horizon - 65, gx + 98, horizon - 9), outline=(*accent, 150), width=4)

    if style.get("trees"):
        for _ in range(26):
            x = rng.randint(-30, W)
            h = rng.randint(70, 170)
            trunk_w = rng.randint(6, 14)
            base = horizon + rng.randint(-10, 54)
            trunk = _lerp_color(ground, (0, 0, 0), 0.55)
            leaf = _lerp_color(ground, tuple(style.get("accent", accent)), 0.16)
            draw.rectangle((x, base - h, x + trunk_w, H), fill=trunk)
            draw.ellipse((x - 32, base - h - 34, x + trunk_w + 34, base - h + 46), fill=leaf)

    for _ in range(130):
        x = rng.randint(0, W - 1)
        y = rng.randint(horizon + 35, H - 8)
        h = rng.randint(10, 38)
        blade = _lerp_color(ground, tuple(style.get("accent", accent)), rng.random() * 0.38)
        draw.line((x, y, x + rng.randint(-5, 5), max(horizon, y - h)), fill=blade, width=1)

    if style.get("fog"):
        fog = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fd = ImageDraw.Draw(fog)
        fog_color = _lerp_color(tuple(style.get("accent", accent)), (230, 230, 230), 0.55)
        for _ in range(9):
            fx = rng.randint(-180, W - 80)
            fy = rng.randint(horizon - 30, H - 80)
            fw = rng.randint(180, 380)
            fh = rng.randint(34, 72)
            fd.ellipse((fx, fy, fx + fw, fy + fh), fill=(*fog_color, rng.randint(18, 34)))
        fog = fog.filter(ImageFilter.GaussianBlur(18))
        img = Image.alpha_composite(img.convert("RGBA"), fog).convert("RGB")

    noise = Image.effect_noise((W, H), 13).convert("L").point(lambda p: p // 18)
    img = Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.10)
    return img


def _profile_avatar(display_name: str, avatar_bytes: bytes | None, size: int,
                    accent: tuple[int, int, int]) -> Image.Image:
    if avatar_bytes:
        try:
            avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
            return ImageOps.fit(avatar, (size, size), Image.Resampling.LANCZOS)
        except Exception:
            pass
    avatar = Image.new("RGBA", (size, size), (*_lerp_color(accent, (255, 255, 255), 0.18), 255))
    d = ImageDraw.Draw(avatar)
    for y in range(size):
        t = y / max(1, size - 1)
        d.line((0, y, size, y), fill=(*_lerp_color(accent, (12, 16, 24), t), 255))
    initials = "".join(part[:1] for part in str(display_name).split()[:2]).upper()[:2] or "A"
    font = _font(max(32, size // 3), bold=True)
    b = d.textbbox((0, 0), initials, font=font)
    d.text(((size - (b[2] - b[0])) // 2, (size - (b[3] - b[1])) // 2 - 4),
           initials, font=font, fill=(255, 255, 255, 235))
    return avatar


def _profile_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int,
                 current: int, needed: int, color: tuple[int, int, int]) -> None:
    needed = max(1, int(needed))
    pct = max(0.0, min(1.0, int(current) / needed))
    draw.rectangle((x, y, x + w, y + h), fill=(46, 53, 58, 210))
    fill_w = max(2, int(w * pct))
    for i in range(fill_w):
        t = i / max(1, fill_w - 1)
        draw.line((x + i, y + 1, x + i, y + h - 1), fill=_lerp_color(color, (225, 244, 255), t * 0.32))
    draw.rectangle((x, y, x + w, y + h), outline=(220, 232, 235, 100), width=1)


def _profile_metric(img: Image.Image, draw: ImageDraw.ImageDraw, x: int, y: int, w: int,
                    label: str, value: str, icon: tuple[str, str], color) -> None:
    icon_img = _art(icon[0], icon[1], (30, 30))
    img.paste(icon_img, (x + 2, y + 2), icon_img)
    draw.text((x + 38, y - 2), _fit(draw, value, w - 50, F22), font=F22, fill=color)
    draw.text((x + 38, y + 27), label, font=F12, fill=(224, 229, 230, 205))
    draw.line((x + w - 4, y + 3, x + w - 4, y + 46), fill=(255, 255, 255, 36))


def _profile_lines(draw: ImageDraw.ImageDraw, text: str, max_w: int, font, max_lines: int) -> list[str]:
    words = str(text or "").replace("\n", " ").split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if _tw(draw, candidate, font) <= max_w:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if words and len(lines) == max_lines:
        joined = " ".join(lines)
        if len(joined) < len(" ".join(words)):
            lines[-1] = _fit(draw, lines[-1] + "...", max_w, font)
    return [_fit(draw, line, max_w, font) for line in lines]


def render_profile_card(display_name, player, *, collection_count, weapon_name, xp_needed,
                        active_buffs: dict[str, int] | None = None,
                        profile_cosmetics: dict[str, Any] | None = None,
                        avatar_bytes: bytes | None = None,
                        win_streak: int = 0, best_streak: int = 0):
    W, H = 900, 540
    cosmetics = profile_cosmetics or {}
    zone_key = str(cosmetics.get("background_key") or _get(player, "current_zone", "void_realm") or "void_realm")
    if zone_key not in ZONES:
        zone_key = "void_realm"
    zone = ZONES.get(zone_key)
    zone_style = _PROFILE_ZONE_STYLES.get(zone_key, _PROFILE_ZONE_STYLES["void_realm"])
    accent = _profile_color(cosmetics.get("accent_color"), tuple(zone_style.get("accent", _PURPLE)))
    about = str(cosmetics.get("about") or (zone.flavor if zone else "No bio set yet.")).strip()[:140]

    bg = _profile_background(W, H, zone_key, accent).convert("RGBA")
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, W - 1, H - 1), radius=14, fill=255)
    img.paste(bg, (0, 0), mask)

    _profile_panel(img, (0, 0, W, H), (0, 0, 0, 28))
    _profile_panel(img, (0, 160, W, 324), (18, 24, 30, 170))
    _profile_panel(img, (0, 324, W, H), (13, 17, 21, 105))
    _profile_panel(img, (0, 0, W - 1, H - 1), (0, 0, 0, 0), radius=14, outline=(*accent, 185), width=2)
    draw = ImageDraw.Draw(img)

    avatar_size = 152
    avatar_x, avatar_y = 42, 35
    draw.rounded_rectangle((avatar_x - 5, avatar_y - 5, avatar_x + avatar_size + 5, avatar_y + avatar_size + 5),
                           radius=5, fill=(0, 0, 0, 72))
    draw.rounded_rectangle((avatar_x - 2, avatar_y - 2, avatar_x + avatar_size + 2, avatar_y + avatar_size + 2),
                           radius=3, fill=(255, 255, 255, 245))
    avatar = _profile_avatar(str(display_name), avatar_bytes, avatar_size, accent)
    img.paste(avatar, (avatar_x, avatar_y), avatar)

    name_x = avatar_x + avatar_size + 28
    nm = str(_get(player, "hunter_name", display_name))
    title = str(_get(player, "title", "Void Hunter"))
    name_font = _font(43)
    subtitle_font = _font(22)
    _profile_text(draw, (name_x, 47), _fit(draw, nm, W - name_x - 36, name_font),
                  name_font, (255, 255, 255, 245), offset=2)
    subtitle = _fit(draw, f"An Abyssia Hunter - {title}", W - name_x - 36, subtitle_font)
    _profile_text(draw, (name_x + 3, 96), subtitle,
                  subtitle_font, (229, 236, 238, 210), offset=1)

    brand = "ABYSSIA"
    draw.text((W - 34 - _tw(draw, brand, F16), 23), brand, font=F16, fill=(*accent, 235))
    if zone:
        zone_label = _fit(draw, zone.name.upper(), 210, F12)
        draw.text((W - 34 - _tw(draw, zone_label, F12), 47), zone_label, font=F12, fill=(235, 240, 242, 160))

    level = int(_get(player, "level", 1))
    xp = int(_get(player, "xp", 0))
    draw.text((62, 224), "Level", font=F16, fill=(229, 236, 238, 190))
    draw.text((132, 203), str(level), font=_font(54, bold=True), fill=(255, 255, 255, 245))

    rank_text = "Hunter Progress"
    xp_text = f"XP: {xp:,}/{int(xp_needed):,}"
    bar_x, bar_y = 252, 226
    draw.text((bar_x, bar_y - 26), _fit(draw, rank_text, 260, F16), font=F16, fill=(235, 240, 242, 215))
    draw.text((bar_x + 470 - _tw(draw, xp_text, F16), bar_y - 26), xp_text, font=F16, fill=(235, 240, 242, 215))
    _profile_bar(draw, bar_x, bar_y + 2, 470, 15, xp, int(xp_needed), accent)
    draw.text((bar_x + 210, bar_y + 24), f"level {level}", font=F12, fill=(226, 232, 235, 155))

    metrics = [
        ("Souls", f"{int(_get(player, 'gold', 0)):,}", ("currency", "souls"), _GOLD),
        ("Gems", f"{int(_get(player, 'gems', 0)):,}", ("currency", "gems"), _CYAN),
        ("Zoo", f"{int(collection_count):,}", ("ui", "inventory"), accent),
        ("Hunts", f"{int(_get(player, 'hunts_done', 0)):,}", ("ui", "hunt"), _GREEN),
    ]
    metric_y = 278
    for idx, metric in enumerate(metrics):
        _profile_metric(img, draw, 66 + idx * 205, metric_y, 178, *metric)

    about_x, about_y = 44, 358
    draw.text((about_x, about_y), "About me", font=F24, fill=(255, 255, 255, 238))
    for idx, line in enumerate(_profile_lines(draw, about, 510, F16, 3)):
        draw.text((about_x, about_y + 34 + idx * 23), line, font=F16, fill=(235, 240, 242, 218))

    info_x, info_y = 598, 355
    _profile_panel(img, (info_x, info_y, W - 36, H - 32), (13, 18, 24, 138),
                   radius=10, outline=(255, 255, 255, 42))
    draw = ImageDraw.Draw(img)
    draw.text((info_x + 18, info_y + 16), "Featured weapon", font=F12, fill=(235, 240, 242, 150))
    weapon_icon = _art("weapons", "sword", (44, 44), colorize=accent)
    img.paste(weapon_icon, (info_x + 18, info_y + 40), weapon_icon)
    draw.text((info_x + 72, info_y + 48), _fit(draw, weapon_name or "None", 216, F18),
              font=F18, fill=(255, 255, 255, 235))

    draw.text((info_x + 18, info_y + 98), "Active buffs", font=F12, fill=(235, 240, 242, 150))
    buff_x = info_x + 18
    buff_y = info_y + 121
    drawn = 0
    if active_buffs:
        for bk, charges in active_buffs.items():
            if drawn >= 4:
                break
            sigil = next((x for x in SIGILS if x.key == bk), None)
            charm = next((x for x in CHARMS if x.key == bk), None)
            if not (sigil or charm):
                continue
            icon = _art("buffs", bk, (28, 28))
            img.paste(icon, (buff_x, buff_y), icon)
            label = f"x{charges}"
            draw.text((buff_x + 32, buff_y + 6), label, font=F12, fill=(255, 255, 255, 220))
            buff_x += 62
            drawn += 1
    if drawn == 0:
        draw.text((buff_x, buff_y + 6), "None active", font=F14, fill=(235, 240, 242, 165))

    streak_y = max(buff_y + 38, info_y + 150)
    draw.text((info_x + 18, streak_y), "Battle Streak", font=F12, fill=(235, 240, 242, 150))
    draw.text((info_x + 110, streak_y), str(win_streak), font=F16, fill=_GOLD)
    draw.text((info_x + 110, streak_y + 22), f"Best: {best_streak}", font=F11, fill=(235, 240, 242, 165))

    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  COLLECTION CARD  (POKEDEX-STYLE)
# ══════════════════════════════════════════════════════════════════
@cached_render(ttl=300)
def render_collection_card(
    display_name: str,
    entries: Iterable[dict[str, Any]],
    caught_count: int,
    total_templates: int,
    page: int,
    total_pages: int,
) -> BytesIO:
    W, H = 1180, 820
    img, draw = _bg(W, H, particle_count=180)
    top = _header(draw, "SPIRIT INDEX", display_name, W, _CYAN)
    mx, my = 28, top
    mw, mh = W - 56, H - top - 24
    _panel(img, draw, (mx, my, mx + mw, my + mh), r=10, outline=_lerp_color(_CYAN, _BORDER, 0.55))
    cx = mx + 24

    pct = round(caught_count / max(1, total_templates) * 100, 1)
    draw.text((cx, my + 18), f"{caught_count} / {total_templates}", font=F32, fill=_TEXT_BRIGHT)
    draw.text((cx + 190, my + 28), "spirits discovered", font=F15, fill=_TEXT_MUTED)
    draw.text((W - mx - 170, my + 28), f"{pct}% complete", font=F16, fill=_CYAN)
    _bar(draw, cx, my + 66, mw - 48, 14, caught_count, total_templates, _CYAN)

    entries_list = list(entries)
    COLS = 7
    cell_w = (mw - 40) // COLS
    cell_h = 196

    for idx, entry in enumerate(entries_list):
        col, row = idx % COLS, idx // COLS
        gx = cx + col * cell_w
        gy = my + 104 + row * cell_h
        rc = _col(entry["rarity"])
        caught = entry["caught"]

        box = (gx + 4, gy + 2, gx + cell_w - 8, gy + cell_h - 12)
        fill = _lerp_color(_PANEL2, rc, 0.04) if caught else (24, 22, 32)
        outline = _lerp_color(rc, _BORDER, 0.28) if caught else (38, 35, 48)
        _shadow(img, box, r=8, blur=5, dy=3, opacity=22 if caught else 10)
        draw.rounded_rectangle(box, radius=8, fill=fill, outline=outline, width=2 if caught else 1)
        draw.line((box[0] + 12, box[1] + 8, box[2] - 12, box[1] + 8),
                  fill=rc if caught else (50, 46, 62), width=2)

        art_size = 92
        if caught:
            a = _art("creatures", normalize_key(entry["name"]), (art_size, art_size))
        else:
            a = _art("creatures", normalize_key(entry["name"]), (art_size, art_size), colorize=(36, 34, 46))
        img.paste(a, (gx + cell_w // 2 - art_size // 2, gy + 22), a)

        nm = entry["name"] if caught else "???"
        name = _fit(draw, nm, cell_w - 22, F13)
        draw.text((gx + cell_w // 2 - _tw(draw, name, F13) // 2, gy + 104),
            name, font=F13, fill=_TEXT_BRIGHT if caught else _LOCKED_TEXT)

        if caught:
            cnt = entry["total"]
            max_lv = int(entry.get("max_level", 0))
            _rarity_badge(draw, gx + 14, gy + 130, entry["rarity"])
            draw.text((gx + 14, gy + 160), f"x{cnt}", font=F12, fill=_TEXT_MUTED)
            lv = f"Lv.{max_lv}"
            draw.text((gx + cell_w - 16 - _tw(draw, lv, F12), gy + 160), lv, font=F12, fill=_GOLD)
        else:
            draw.text((gx + cell_w // 2 - _tw(draw, "Silhouette locked", F11) // 2, gy + 134),
                      "Silhouette locked", font=F11, fill=_LOCKED_TEXT)

    ft = f"Page {page}/{total_pages}"
    draw.text((W - 42 - _tw(draw, ft, F14), my + mh - 34), ft, font=F14, fill=_TEXT_MUTED)

    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  AUTOHUNT CARD
# ══════════════════════════════════════════════════════════════════
def render_autohunt_card(zone_name, *, hours, souls, gems, xp, materials, creatures, levels=0):
    W, H = 940, 540
    img, draw = _bg(W, H, particle_count=250)
    top = _header(draw, "EXPEDITION REPORT", f"{hours}h  through  {zone_name}", W, _ORANGE)
    mx, my = 22, top
    _panel(img, draw, (mx, my, mx + W - 44, my + H - top - 18))
    cx = mx + 22

    y = my + 18
    gap = 10
    bw = (W - 88 - gap * 3) // 4
    _metric_box(img, draw, cx, y, bw, 56, "SOULS", f"{souls:,}", "souls", _GOLD)
    _metric_box(img, draw, cx + bw + gap, y, bw, 56, "GEMS", f"{gems:,}", "gems", _CYAN)
    _metric_box(img, draw, cx + (bw + gap) * 2, y, bw, 56, "XP", f"{xp:,}", accent=_GREEN)
    _metric_box(img, draw, cx + (bw + gap) * 3, y, bw, 56, "LEVELS", str(levels) if levels else "0", accent=_GOLD if levels else None)

    cy = y + 72
    draw.line((cx, cy, cx + W - 88, cy), fill=_BORDER, width=1)
    cy += 10
    rx = cx
    draw.text((rx, cy), "MONSTERS FOUND", font=F15, fill=_GOLD)
    for i, line in enumerate(list(creatures)[:8]):
        draw.text((rx + 8, cy + 26 + i * 22), _fit(draw, line, W - 112, F14), font=F14, fill=_TEXT_BRIGHT)
    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  ARENA CARD
# ══════════════════════════════════════════════════════════════════
@cached_render()
def render_arena_card(display_name, player, *, rank, last_match=None):
    W, H = 780, 400
    img, draw = _bg(W, H, particle_count=120)
    top = _header(draw, "ARENA LEDGER", display_name, W, _ORANGE)
    mx, my = 22, top
    _panel(img, draw, (mx, my, mx + W - 44, my + H - top - 18))
    cx = mx + 24
    draw.text((cx, my + 20), rank, font=F36, fill=_GOLD)
    draw.line((cx, my + 62, cx + W - 88, my + 62), fill=_BORDER, width=1)
    draw.text((cx, my + 72), "Rating", font=F14, fill=_TEXT_MUTED)
    draw.text((cx + 80, my + 68), f"{int(_get(player, 'arena_rating', 1000)):,}", font=F24, fill=_TEXT_BRIGHT)
    draw.text((cx, my + 106), f"Hunter Level  {int(_get(player, 'level', 1))}", font=F15, fill=_TEXT_MUTED)
    draw.text((cx, my + 134), "Battle team uses selected or strongest 3 monsters.", font=F13, fill=_TEXT_MUTED)
    if last_match:
        draw.line((cx, my + 158, cx + W - 88, my + 158), fill=_BORDER, width=1)
        for i, line in enumerate(last_match.split("\n")[:3]):
            draw.text((cx, my + 170 + i * 24), line, font=F14, fill=_TEXT_BRIGHT)
    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  WEAPONS INVENTORY CARD
# ══════════════════════════════════════════════════════════════════
@cached_render()
def render_weapons_card(display_name: str, weapons: list, *, page: int = 1,
                        total_pages: int = 1) -> BytesIO:
    W, H = 1920, 1080
    img, draw = _bg(W, H, particle_count=200)
    top = _header(draw, "WEAPON VAULT", display_name, W, _GOLD)
    mx, my = 36, top
    _panel(img, draw, (mx, my, mx + W - 72, my + H - top - 18), r=10, outline=_lerp_color(_GOLD, _BORDER, 0.55))
    cx = mx + 24
    cy = my + 24
    items_per_page = 4
    start = (page - 1) * items_per_page
    for wi, w in enumerate(weapons[start:start + items_per_page]):
        wid = _get(w, "id", 0)
        wr = _weapon_rarity(w)
        rc = _col(wr)
        bw = W - 120
        rh = 190
        _shadow(img, (cx, cy, cx + bw, cy + rh), r=10, blur=7, dy=4, opacity=34)
        draw.rounded_rectangle((cx, cy, cx + bw, cy + rh), radius=10,
                               fill=_lerp_color(_PANEL2, rc, 0.035),
                               outline=_lerp_color(rc, _BORDER, 0.25), width=2)
        for si in range(1, 3):
            draw.rounded_rectangle(
                (cx + si, cy + si, cx + bw - si, cy + rh - si), radius=max(0, 10 - si),
                outline=(*_lerp_color(rc, (255, 255, 255), 0.12), max(0, 30 - si * 10)))
        draw.rectangle((cx + 1, cy + 1, cx + bw - 1, cy + 8), fill=rc)
        type_icon_key = _get(w, "weapon_type", "sword")
        icon_size = 130
        icon_box = (cx + 24, cy + 28, cx + 24 + icon_size, cy + 28 + icon_size)
        draw.rounded_rectangle(icon_box, radius=10, fill=(10, 9, 16), outline=_lerp_color(rc, _BORDER, 0.2), width=2)
        type_icon = _art("weapons", type_icon_key, (icon_size - 18, icon_size - 18), colorize=rc)
        img.paste(type_icon, (icon_box[0] + 9, icon_box[1] + 9), type_icon)
        name_x = cx + 154
        wn = str(_get(w, "name", "?"))
        q_pct = int(_get(w, "quality_pct", 50))
        wq = _weapon_quality_label(q_pct)
        mana_cost = int(_get(w, "mana_cost", 3))
        wear = str(_get(w, "wear", "Unknown"))
        wtype = str(_get(w, "weapon_type", "sword"))
        type_label = wtype.title()
        draw.text((name_x, cy + 22), _fit(draw, wn, bw - 560, F24), font=F24, fill=_TEXT_BRIGHT)
        id_text = f"#{wid}"
        id_w = _tw(draw, id_text, F18)
        draw.rounded_rectangle((name_x + _tw(draw, wn, F24) + 14, cy + 18, name_x + _tw(draw, wn, F24) + 14 + id_w + 18, cy + 48), radius=8, fill=(30, 26, 40), outline=_GOLD, width=2)
        draw.text((name_x + _tw(draw, wn, F24) + 23, cy + 20), id_text, font=F18, fill=_GOLD)
        q_colors = {
            "Normal": _TEXT_MUTED, "Magic": _BLUE, "Rare": (56, 189, 248),
            "Epic": _PURPLE, "Legendary": _GOLD, "Mythic": (251, 113, 133),
            "Fine": _BLUE, "Superior": _PURPLE, "Masterwork": _GOLD, "Ancient": _ORANGE,
        }
        q_color = _col(wq) if wq in _RARITY else q_colors.get(wq, _TEXT_MUTED)
        tag_y = cy + 58
        used = _pill(draw, name_x, tag_y, wr.upper(), rc, F13, h=26)
        used += _pill(draw, name_x + used + 10, tag_y, f"Q {q_pct}%", q_color, F13, h=26) + 10
        used += _pill(draw, name_x + used + 10, tag_y, f"MANA {mana_cost}", _CYAN, F13, h=26) + 10
        used += _pill(draw, name_x + used + 10, tag_y, type_label.upper(), _TEXT_MUTED, F13, h=26) + 10
        _pill(draw, name_x + used + 10, tag_y, wear.upper(), _TEXT_MUTED, F13, h=26)
        from core.rpg import weapon_stats as _weapon_stats
        _ws = _weapon_stats(w)
        _stat_items = [(lab, f"+{_ws.get(k, 0)}", clr) for k, lab, clr in (
            ("str_stat", "STR", _GOLD), ("pr_stat", "DEF", _BLUE), ("hp", "HP", (220, 80, 80)),
            ("wp_stat", "MANA", _CYAN), ("mag_stat", "MAG", (180, 100, 220)),
            ("mr_stat", "RES", (100, 180, 200)),
        ) if _ws.get(k, 0)]
        stat_x = cx + bw - 320
        for si, (lab, val, color) in enumerate(_stat_items[:2]):
            sx = stat_x + si * 140
            draw.rounded_rectangle((sx, cy + 28, sx + 118, cy + 95), radius=8,
                                   fill=(12, 10, 18), outline=_lerp_color(color, _BORDER, 0.35))
            draw.text((sx + 14, cy + 38), lab, font=F12, fill=_TEXT_MUTED)
            draw.text((sx + 14, cy + 58), val, font=F24, fill=color)
        equipped_id = _get(w, "equipped_creature_id", None)
        if equipped_id is not None:
            _pill(draw, stat_x, cy + 102, "EQUIPPED", _GREEN, F14, h=28)
        passive_raw = _get(w, "passive", None)
        py = cy + 100
        if passive_raw:
            try:
                passive = json.loads(str(passive_raw))
                if isinstance(passive, dict) and passive.get("key"):
                    p_name = passive.get("name", "")
                    p_chance = passive.get("chance", 0)
                    p_icon = _art("passives", passive.get("key", ""), (32, 32))
                    img.paste(p_icon, (name_x, py), p_icon)
                    draw.text((name_x + 40, py + 5), _fit(draw, f"{p_name} - {p_chance}% trigger", 420, F15),
                              font=F15, fill=_GOLD)
            except Exception:
                pass
        try:
            affixes = json.loads(str(_get(w, "affixes", "[]")))
        except Exception:
            affixes = []
        affix_texts = [str(a.get("fmt", "")) for a in affixes if a.get("fmt")][:2]
        if affix_texts:
            aff_line = "  •  ".join(affix_texts[:4])
            draw.text((name_x, py + 36), _fit(draw, aff_line, bw - 380, F13),
                      font=F13, fill=_TEXT_MUTED)
            if len(affix_texts) > 4:
                aff_line2 = "  •  ".join(affix_texts[4:8])
                draw.text((name_x, py + 56), _fit(draw, aff_line2, bw - 380, F13),
                          font=F13, fill=_TEXT_MUTED)
        cy += rh + 20
    ft = f"Page {page}/{total_pages}  •  {len(weapons)} weapon(s)"
    draw.text((cx, H - 48), ft, font=F18, fill=_TEXT_MUTED)
    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  CRATE OPENING CARD
# ══════════════════════════════════════════════════════════════════
def render_crate_open_card(display_name: str, crate_name: str, result: dict,
                           *, weapons: list = None, compact: bool = False) -> BytesIO:
    weapon_list = list(weapons or [])
    compact_rows = len(weapon_list) if compact else 0
    ROW_C = 38
    MIN_H = 740
    if compact:
        H = max(MIN_H, 370 + compact_rows * (ROW_C + 6))
    else:
        H = MIN_H
    W = 860
    img, draw = _bg(W, H, particle_count=120)
    top = _header(draw, "CRATE OPENING", crate_name, W, _ORANGE)
    mx, my = 26, top
    _panel(img, draw, (mx, my, W - mx, H - 22), r=10, outline=_lerp_color(_ORANGE, _BORDER, 0.45))
    cx = mx + 24
    cy = my + 22
    gold = int(result.get("gold", 0))
    gems = int(result.get("gems", 0))
    swords = int(result.get("swords", 0))

    if not compact:
        featured = max(weapon_list, key=lambda row: _card_int(_get(row, "quality_pct", 50), 50), default=None)
        if featured:
            wr = _weapon_rarity(featured)
            rc = _col(wr)
            wtype = str(_get(featured, "weapon_type", "sword"))
            q_pct = int(_get(featured, "quality_pct", 50))
            wq = _weapon_quality_label(q_pct)
            mana_cost = int(_get(featured, "mana_cost", 3))
            wear = str(_get(featured, "wear", "Unknown"))
            name = str(_get(featured, "name", "?"))
            title = f"{wq} {name}" if wq != "Common" else name
            hero = (cx, cy, W - mx - 24, cy + 246)
            _shadow(img, hero, r=12, blur=10, dy=5, opacity=42)
            draw.rounded_rectangle(hero, radius=12, fill=_lerp_color(_PANEL2, rc, 0.055), outline=rc, width=3)
            draw.rectangle((hero[0] + 2, hero[1] + 2, hero[2] - 2, hero[1] + 10), fill=rc)
            icon_size = 156
            icon = _art("weapons", wtype, (icon_size, icon_size), colorize=rc)
            glow = Image.new("RGBA", (icon_size + 50, icon_size + 50), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            gd.ellipse((0, 0, icon_size + 49, icon_size + 49), fill=(*rc, 46))
            glow = glow.filter(ImageFilter.GaussianBlur(12))
            img.paste(glow, (hero[0] + 42, hero[1] + 36), glow)
            img.paste(icon, (hero[0] + 67, hero[1] + 61), icon)
            tx = hero[0] + 250
            draw.text((tx, hero[1] + 48), "FEATURED PULL", font=F13, fill=_TEXT_MUTED)
            draw.text((tx, hero[1] + 76), _fit(draw, title, 470, F28), font=F28, fill=_TEXT_BRIGHT)
            used = _pill(draw, tx, hero[1] + 118, wr.upper(), rc, F12, h=26)
            used += _pill(draw, tx + used + 10, hero[1] + 118, f"Q {q_pct}%", _GOLD, F12, h=26) + 10
            used += _pill(draw, tx + used + 10, hero[1] + 118, f"MANA {mana_cost}", _CYAN, F12, h=26) + 10
            _pill(draw, tx + used + 10, hero[1] + 118, wear.upper(), _TEXT_MUTED, F12, h=26)
            passive_raw = _get(featured, "passive", None)
            if passive_raw:
                try:
                    passive = json.loads(str(passive_raw))
                    if isinstance(passive, dict) and passive.get("name"):
                        draw.text((tx, hero[1] + 158),
                                  _fit(draw, f"{passive.get('name')} - {passive.get('chance', 0)}% trigger", 460, F15),
                                  font=F15, fill=_GOLD)
                except Exception:
                    pass
            cy += 270

    tile_gap = 12
    tile_w = (W - 2 * mx - 48 - tile_gap * 2) // 3
    _draw_stat_tile(img, draw, cx, cy, tile_w, 72, "SOULS", f"{gold:,}", _GOLD, ("currency", "souls"))
    _draw_stat_tile(img, draw, cx + tile_w + tile_gap, cy, tile_w, 72, "GEMS", f"{gems:,}", _CYAN, ("currency", "gems"))
    _draw_stat_tile(img, draw, cx + (tile_w + tile_gap) * 2, cy, tile_w, 72, "SWORDS", f"{swords:,}", _GREEN, ("consumable", "hunt_sword"))
    cy += 92

    if weapon_list:
        if compact:
            label = "ACQUIRED WEAPONS"
        else:
            label = "OTHER DROPS"
            weapon_list = [w for w in weapon_list if w is not featured]
        draw.text((cx, cy), label, font=F13, fill=_TEXT_MUTED)
        cy += 24
        for w in weapon_list:
            wr = _weapon_rarity(w)
            rc = _col(wr)
            wid = _get(w, "id", 0)
            wn = str(_get(w, "name", "?"))
            q_pct = int(_get(w, "quality_pct", 50))
            wq = _weapon_quality_label(q_pct)
            wtype = str(_get(w, "weapon_type", "sword"))
            display = f"{wq} {wn}" if wq != "Common" else wn
            if compact:
                y0 = cy
                _shadow(img, (cx, y0, W - 54, y0 + ROW_C), r=6, blur=4, dy=2, opacity=18)
                draw.rounded_rectangle((cx, y0, W - 54, y0 + ROW_C), radius=6, fill=_PANEL2, outline=_lerp_color(rc, _BORDER, 0.15), width=1)
                w_icon = _art("weapons", wtype, (26, 26), colorize=rc)
                img.paste(w_icon, (cx + 8, y0 + 6), w_icon)
                draw.text((cx + 42, y0 + 4), _fit(draw, f"#{wid}", 80, F11), font=F11, fill=_TEXT_MUTED)
                draw.text((cx + 90, y0 + 4), _fit(draw, display, 280, F13), font=F13, fill=rc)
                draw.text((cx + 380, y0 + 4), _fit(draw, wtype.replace("_", " ").title(), 110, F11), font=F11, fill=_TEXT_MUTED)
                draw.text((cx + 500, y0 + 4), f"Q{q_pct}%", font=F12, fill=_GOLD)
                passive_raw = _get(w, "passive", None)
                if passive_raw:
                    try:
                        passive = json.loads(str(passive_raw))
                        if isinstance(passive, dict) and passive.get("name"):
                            draw.text((cx + 560, y0 + 5), _fit(draw, f"{passive.get('name')} {passive.get('chance', 0)}%", 250, F11), font=F11, fill=_GOLD)
                    except Exception:
                        pass
                cy += ROW_C + 6
            else:
                row_h = 72
                _shadow(img, (cx, cy, W - 54, cy + row_h), r=8, blur=5, dy=3, opacity=24)
                draw.rounded_rectangle((cx, cy, W - 54, cy + row_h), radius=8, fill=_PANEL2, outline=_lerp_color(rc, _BORDER, 0.25), width=2)
                w_icon = _art("weapons", wtype, (46, 46), colorize=rc)
                img.paste(w_icon, (cx + 16, cy + 13), w_icon)
                draw.text((cx + 78, cy + 12), _fit(draw, display, 430, F18), font=F18, fill=rc)
                draw.text((cx + 78, cy + 42), f"#{wid} - {wtype.title()} - Q{q_pct}% {wq}", font=F11, fill=_TEXT_MUTED)
                passive_raw = _get(w, "passive", None)
                if passive_raw:
                    try:
                        passive = json.loads(str(passive_raw))
                        if isinstance(passive, dict) and passive.get("key"):
                            p_name = passive.get("name", "")
                            p_chance = passive.get("chance", 0)
                            draw.text((W - 300, cy + 27), _fit(draw, f"{p_name} {p_chance}%", 230, F11), font=F11, fill=_GOLD)
                    except Exception:
                        pass
                cy += row_h + 10
    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  CREATURE DEX CARD
# ══════════════════════════════════════════════════════════════════
def _format_rate(rate_pct: float) -> str:
    if rate_pct >= 1:
        return f"~{rate_pct:.1f}%"
    if rate_pct >= 0.01:
        return f"~{rate_pct:.2f}%"
    return f"~{rate_pct:.4f}%"


def _render_creature_card_legacy(
    creature_name: str, rarity: str, attack: int, defense: int, hp: int,
    ability: str, level: int = 1, xp: int = 0, caught: bool = False,
    player_name: str = "", catch_rate: float = 0.0, mana: int = 200, weight: float | int | None = None,
) -> BytesIO:
    W, H = 750, 520
    img, draw = _bg(W, H, particle_count=150)
    top = _header(draw, "BESTIARY", creature_name, W, _BLUE)
    mx, my = 22, top
    _panel(img, draw, (mx, my, mx + W - 44, my + H - top - 18))
    cx = mx + 24
    cy = my + 16

    # Creature art
    art_size = 130
    a = _art("creatures", normalize_key(creature_name), (art_size, art_size))
    _paste(img, a, (cx + (art_size - a.width) // 2, cy + (art_size - a.height) // 2), r=8)

    # Name centered below art
    nm = _fit(draw, creature_name, art_size, F13)
    nw = _tw(draw, nm, F13)
    draw.text((cx + (art_size - nw) // 2, cy + art_size + 10), nm, font=F13, fill=_TEXT_BRIGHT)

    # Rarity badge centered below name
    _rarity_badge(draw, cx + (art_size - _tw(draw, rarity[:3].upper(), F10)) // 2 - 6, cy + art_size + 28, rarity)

    # Separator
    sep_x = cx + art_size + 24
    draw.line((sep_x, cy, sep_x, cy + H - top - my - 40), fill=_BORDER, width=1)

    # Right side: stats
    rx = sep_x + 20
    ry = cy

    # Ability
    draw.text((rx, ry), "ABILITY", font=F11, fill=_TEXT_MUTED)
    draw.text((rx, ry + 16), _fit(draw, ability, W - rx - 40, F14), font=F14, fill=_TEXT_BRIGHT)
    ry += 52

    # Level and XP
    draw.text((rx, ry), f"LEVEL {level}", font=F20, fill=_GOLD)
    if caught:
        ry += 32
        _bar(draw, rx, ry, 250, 12, xp, 100, _GOLD)
        draw.text((rx + 256, ry - 2), f"{xp}/100", font=F10, fill=_TEXT_MUTED)
    ry += 30

    # Stat grid (2x2)
    stats = [
        ("HP", hp, _RED), ("STR", attack, _GOLD),
        ("DEF", defense, _BLUE), ("MANA", mana, _PURPLE),
    ]
    sw = 120
    sh = 48
    sg = 6

    cols = 2
    for idx, (label, value, color) in enumerate(stats):
        col, row = idx % cols, idx // cols
        sx = rx + col * (sw + sg)
        sy = ry + row * (sh + sg)
        _shadow(img, (sx, sy, sx + sw, sy + sh), r=6, blur=4, dy=2, opacity=25)
        draw.rounded_rectangle((sx, sy, sx + sw, sy + sh), radius=6, fill=_PANEL2, outline=_BORDER)
        draw.text((sx + 8, sy + 6), label, font=F10, fill=_TEXT_MUTED)
        draw.text((sx + 8, sy + 20), str(value), font=F18, fill=color)

    # Catch rate
    ry += sh * 2 + sg + 8
    draw.text((rx, ry), "CATCH RATE", font=F11, fill=_TEXT_MUTED)
    ry += 16
    rate_pct = max(0.0, catch_rate * 100)
    pct_text = _format_rate(rate_pct)
    rate_color = _GREEN if rate_pct >= 30 else (_GOLD if rate_pct >= 1 else _RED)
    draw.text((rx, ry), pct_text, font=F28, fill=rate_color)
    bar_x = rx + 80
    _bar(draw, bar_x, ry + 4, 160, 18, max(1, int(rate_pct * 100)), 10000, rate_color)
    if weight is not None:
        draw.text((rx, ry + 34), f"Weight {weight:g}", font=F11, fill=_TEXT_MUTED)

    # Caught status at bottom
    bottom_y = H - 44
    status_color = _GREEN if caught else _RED
    status_text = f"✓ Caught  •  {player_name}" if caught else "Not yet caught"
    draw.text((cx, bottom_y), status_text, font=F12, fill=status_color)
    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  SIGILS & CHARMS CARD
# ══════════════════════════════════════════════════════════════════
@cached_render()
def render_creature_card(
    creature_name: str, rarity: str, hp: int, str_stat: int, pr_stat: int,
    wp_stat: int, mag_stat: int, mr_stat: int,
    role: str, ability: str, level: int = 1, xp: int = 0, caught: bool = False,
    player_name: str = "", catch_rate: float = 0.0, mana: int = 200, weight: float | int | None = None,
) -> BytesIO:
    W, H = 900, 620
    img, draw = _bg(W, H, particle_count=220)
    rc = _col(rarity)
    top = _header(draw, "BESTIARY", creature_name, W, rc)
    mx, my = 26, top
    _panel(img, draw, (mx, my, W - mx, H - 22), r=10, outline=rc)
    cx = mx + 28
    cy = my + 26

    art_size = 210
    art_box = (cx, cy, cx + 260, cy + 330)
    _shadow(img, art_box, r=10, blur=8, dy=4, opacity=42)
    draw.rounded_rectangle(art_box, radius=10, fill=_PANEL2, outline=rc, width=2)
    draw.rectangle((art_box[0] + 1, art_box[1] + 1, art_box[2] - 1, art_box[1] + 8), fill=rc)
    art = _art("creatures", normalize_key(creature_name), (art_size, art_size))
    glow = Image.new("RGBA", (art_size + 36, art_size + 36), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((0, 0, art_size + 35, art_size + 35), fill=(*rc, 46))
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    img.paste(glow, (cx + 130 - (art_size + 36) // 2, cy + 30), glow)
    img.paste(art, (cx + 130 - art_size // 2, cy + 48), art)

    name = _fit(draw, creature_name, 228, F20)
    draw.text((cx + 130 - _tw(draw, name, F20) // 2, cy + 270), name, font=F20, fill=_TEXT_BRIGHT)
    _rarity_badge(draw, cx + 22, cy + 306, rarity)
    draw.text((cx + 102, cy + 306), f"Lv.{level}", font=F12, fill=_GOLD)

    role_badge_w = 200
    role_badge_h = 34
    role_badge_x = cx + 130 - role_badge_w // 2
    role_badge_y = cy + 340
    role_bg = Image.new("RGBA", (role_badge_w, role_badge_h), (0, 0, 0, 0))
    rbg = ImageDraw.Draw(role_bg)
    rbg.rounded_rectangle((0, 0, role_badge_w - 1, role_badge_h - 1), radius=17, fill=(*rc, 90), outline=rc, width=2)
    role_bg = role_bg.filter(ImageFilter.GaussianBlur(4))
    img.paste(role_bg, (role_badge_x, role_badge_y), role_bg)
    draw.rounded_rectangle((role_badge_x, role_badge_y, role_badge_x + role_badge_w, role_badge_y + role_badge_h),
                           radius=17, fill=(*rc, 50), outline=rc, width=2)
    draw.text((role_badge_x + role_badge_w // 2 - _tw(draw, role, F16) // 2, role_badge_y + 6),
              role, font=F16, fill=_TEXT_BRIGHT)

    rx = cx + 292
    ry = cy
    draw.text((rx, ry), "ABILITY", font=F11, fill=_TEXT_MUTED)
    draw.text((rx, ry + 18), _fit(draw, ability, W - rx - 60, F22), font=F22, fill=_TEXT_BRIGHT)
    ry += 70

    draw.text((rx, ry), f"LEVEL {level}", font=F20, fill=_GOLD)
    if caught:
        ry += 32
        _bar(draw, rx, ry, 360, 16, xp, 100, _GOLD)
        draw.text((rx + 368, ry - 1), f"{xp}/100", font=F11, fill=_TEXT_MUTED)
    ry += 42

    stat_items = [
        ("HP", hp, _RED), ("STR", str_stat, _GOLD), ("DEF", pr_stat, _BLUE),
        ("MANA", wp_stat, _PURPLE), ("MAG", mag_stat, _ORANGE), ("RES", mr_stat, _CYAN),
    ]
    sw = 110
    sh = 50
    sg = 8
    cols = 4
    for idx, (label, value, color) in enumerate(stat_items):
        col, row = idx % cols, idx // cols
        sx = rx + col * (sw + sg)
        sy = ry + row * (sh + sg)
        _shadow(img, (sx, sy, sx + sw, sy + sh), r=6, blur=4, dy=2, opacity=24)
        draw.rounded_rectangle((sx, sy, sx + sw, sy + sh), radius=6, fill=_PANEL2, outline=color)
        draw.text((sx + 8, sy + 6), label, font=F10, fill=_TEXT_MUTED)
        draw.text((sx + 8, sy + 20), str(value), font=F18, fill=color)

    ry += sh * 2 + sg + 10
    draw.text((rx, ry), "CATCH RATE", font=F11, fill=_TEXT_MUTED)
    ry += 16
    rate_pct = max(0.0, catch_rate * 100)
    pct_text = _format_rate(rate_pct)
    rate_color = _GREEN if rate_pct >= 30 else (_GOLD if rate_pct >= 1 else _RED)
    draw.text((rx, ry), pct_text, font=F30, fill=rate_color)
    _bar(draw, rx + 150, ry + 9, 246, 18, max(1, int(rate_pct * 100)), 10000, rate_color)
    if weight is not None:
        draw.text((rx, ry + 42), f"Weight {weight:g}", font=F12, fill=_TEXT_MUTED)

    status_color = _GREEN if caught else _RED
    status_text = f"Caught - {player_name}" if caught else "Not yet caught"
    _pill(draw, cx, H - 62, status_text, status_color, F13, h=26)
    return _save(img)


def _diamond(draw, x: int, y: int, size: int, fill, outline=None):
    hs = size // 2
    pts = [(x + hs, y), (x + size, y + hs), (x + hs, y + size), (x, y + hs)]
    draw.polygon(pts, fill=fill, outline=outline)


def render_buffs_card(display_name: str, buff_type: str, items: list, active: dict[str, int]) -> BytesIO:
    is_sigil = buff_type == "sigils"
    title = "BLOOD SIGILS" if is_sigil else "VOID CHARMS"
    accent = _RED if is_sigil else _PURPLE
    W, H = 1180, 650
    img, draw = _bg(W, H, particle_count=260)
    top = _header(draw, title, f"{display_name} - 5 daily hunt boosters", W, accent)
    mx, my = 28, top
    _panel(img, draw, (mx, my, W - mx, H - 22), r=10, outline=accent)

    items = list(items)
    cols = max(1, min(5, len(items)))
    gap = 14
    bw = (W - mx * 2 - 36 - gap * (cols - 1)) // cols
    bh = H - my - 92
    base_x = mx + 18
    base_y = my + 20

    for idx, item in enumerate(items):
        bx = base_x + idx * (bw + gap)
        by = base_y
        charges = int(active.get(item.key, 0))
        active_text = f"{charges} active" if charges else "Inactive"
        rank_text = f"Tier {idx + 1}"
        item_color = _lerp_color(accent, _GOLD if is_sigil else _CYAN, idx / max(1, len(items) - 1))

        _shadow(img, (bx, by, bx + bw, by + bh), r=10, blur=8, dy=4, opacity=45)
        draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=10,
                               fill=_lerp_color(_PANEL2, item_color, 0.04), outline=item_color, width=2)
        draw.rectangle((bx + 1, by + 1, bx + bw - 1, by + 8), fill=item_color)

        _pill(draw, bx + 14, by + 18, rank_text, item_color, F11)
        if charges:
            _pill(draw, bx + bw - _tw(draw, active_text, F11) - 30, by + 18, active_text, _GREEN, F11)

        icon_size = 112
        icon = _art("buffs", item.key, (icon_size, icon_size))
        glow = Image.new("RGBA", (icon_size + 34, icon_size + 34), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((0, 0, icon_size + 33, icon_size + 33), fill=(*item_color, 44))
        glow = glow.filter(ImageFilter.GaussianBlur(8))
        img.paste(glow, (bx + bw // 2 - (icon_size + 34) // 2, by + 54), glow)
        img.paste(icon, (bx + bw // 2 - icon_size // 2, by + 70), icon)

        name = _fit(draw, item.name, bw - 24, F18)
        draw.text((bx + bw // 2 - _tw(draw, name, F18) // 2, by + 198), name, font=F18, fill=_TEXT_BRIGHT)
        if is_sigil:
            effect = f"+{item.extra_monsters} monsters"
        else:
            effect = f"+{item.extra_monsters} monsters / +{int(item.rarity_bonus * 100)}% rarity"
        draw.text((bx + bw // 2 - _tw(draw, effect, F16) // 2, by + 228), effect, font=F16, fill=item_color)
        draw.text((bx + bw // 2 - _tw(draw, f"{item.charges} hunts", F13) // 2, by + 252), f"{item.charges} hunts", font=F13, fill=_TEXT_MUTED)

        desc = _fit(draw, item.desc, bw - 28, F12)
        draw.text((bx + 14, by + 286), desc, font=F12, fill=_TEXT_MUTED)

        price_y = by + bh - 86
        draw.line((bx + 14, price_y - 12, bx + bw - 14, price_y - 12), fill=(*item_color, 120), width=1)
        _icon_text(img, draw, bx + 16, price_y, "currency", "souls", f"{item.cost_souls:,}", _GOLD, icon_size=24, font=F14)
        if item.cost_gems:
            _icon_text(img, draw, bx + 16, price_y + 30, "currency", "gems", f"{item.cost_gems:,}", _CYAN, icon_size=24, font=F14)
        else:
            draw.text((bx + 16, price_y + 33), "No gem cost", font=F12, fill=_TEXT_MUTED)

        status_color = _GREEN if charges else _TEXT_MUTED
        draw.text((bx + 16, by + bh - 26), active_text, font=F12, fill=status_color)

    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  DAILY CRATE SHOP CARD (paginated)
# ══════════════════════════════════════════════════════════════════
_PER_PAGE = 4


def render_shop_card(display_name: str, deals: list, *, page: int = 1, total_pages: int = 1) -> BytesIO:
    W, H = 1040, 760
    img, draw = _bg(W, H, particle_count=140)
    top = _header(draw, "DAILY CRATE SHOP", f"{display_name} - shared deals reset at 00:00 UTC", W, _GOLD)
    mx, my = 26, top
    _panel(img, draw, (mx, my, W - mx, H - 22), r=10, outline=_lerp_color(_GOLD, _BORDER, 0.45))

    start = (page - 1) * _PER_PAGE
    page_deals = deals[start:start + _PER_PAGE]
    gap = 20
    bw = (W - mx * 2 - 40 - gap) // 2
    bh = 250
    base_x = mx + 20
    base_y = my + 24

    for local_idx, deal in enumerate(page_deals):
        col, row = local_idx % 2, local_idx // 2
        cx = base_x + col * (bw + gap)
        cy = base_y + row * (bh + gap)
        purchased = bool(deal.get("purchased", False))
        discount = int(deal.get("discount_pct", 0))
        is_bundle = deal.get("deal_type") == "bundle"
        outline = _CYAN if is_bundle else _GOLD

        _shadow(img, (cx, cy, cx + bw, cy + bh), r=10, blur=7, dy=4, opacity=32)
        draw.rounded_rectangle((cx, cy, cx + bw, cy + bh), radius=10,
                               fill=_lerp_color(_PANEL2, outline, 0.025),
                               outline=_lerp_color(outline, _BORDER, 0.18), width=2)
        draw.rectangle((cx + 1, cy + 1, cx + bw - 1, cy + 8), fill=outline)

        if purchased:
            overlay = Image.new("RGBA", (bw, bh), (8, 7, 12, 178))
            mask = Image.new("L", (bw, bh), 0)
            md = ImageDraw.Draw(mask)
            md.rounded_rectangle((0, 0, bw, bh), radius=10, fill=255)
            img.paste(overlay, (cx, cy), mask)

        label = "BUNDLE" if is_bundle else "CRATE"
        draw.text((cx + 22, cy + 22), label, font=F11, fill=outline)
        if not purchased and discount > 0:
            badge = f"-{discount}%"
            draw.rounded_rectangle((cx + bw - 80, cy + 16, cx + bw - 16, cy + 42), radius=6, fill=_RED)
            _center_text(draw, (cx + bw - 80, cy + 16, cx + bw - 16, cy + 42), badge, F14, _TEXT_BRIGHT)

        icon_size = 118
        icon = _art("crate", _deal_icon_key(deal), (icon_size, icon_size))
        img.paste(icon, (cx + 24, cy + 68), icon)

        tx = cx + 158
        name = _fit(draw, str(deal["item_name"]), bw - 180, F22)
        draw.text((tx, cy + 72), name, font=F22, fill=_TEXT_BRIGHT)
        desc = str(deal.get("desc") or "")
        if desc:
            draw.text((tx, cy + 108), _fit(draw, desc, bw - 188, F12), font=F12, fill=_TEXT_MUTED)

        orig_s = int(deal.get("original_souls", 0))
        orig_g = int(deal.get("original_gems", 0))
        disc_s = int(deal.get("discounted_souls", 0))
        disc_g = int(deal.get("discounted_gems", 0))
        price_x = cx + 22
        price_y = cy + 188

        if disc_s > 0:
            if discount > 0 and orig_s > disc_s:
                old = f"{orig_s:,}"
                _icon_text(img, draw, price_x, price_y, "currency", "souls", old, _TEXT_MUTED, icon_size=22, font=F12)
                draw.line((price_x + 30, price_y + 12, price_x + 30 + _tw(draw, old, F12), price_y + 12), fill=_RED, width=2)
                price_x += 104
            price_x += _icon_text(img, draw, price_x, price_y - 2, "currency", "souls", f"{disc_s:,}", _GOLD, icon_size=26, font=F16) + 16

        if disc_g > 0:
            if discount > 0 and orig_g > disc_g:
                old = f"{orig_g}"
                _icon_text(img, draw, price_x, price_y, "currency", "gems", old, _TEXT_MUTED, icon_size=22, font=F12)
                draw.line((price_x + 30, price_y + 12, price_x + 30 + _tw(draw, old, F12), price_y + 12), fill=_RED, width=2)
                price_x += 78
            _icon_text(img, draw, price_x, price_y - 2, "currency", "gems", f"{disc_g}", _CYAN, icon_size=26, font=F16)

        if purchased:
            draw.rounded_rectangle((cx + bw - 108, cy + bh - 48, cx + bw - 18, cy + bh - 18), radius=6, fill=(42, 14, 20), outline=_RED)
            _center_text(draw, (cx + bw - 108, cy + bh - 48, cx + bw - 18, cy + bh - 18), "SOLD", F16, _RED)

    ft = f"Page {page}/{total_pages} - deals refresh at 00:00 UTC for everyone"
    draw.text((mx + 24, H - 48), ft, font=F14, fill=_TEXT_MUTED)
    return _save(img)


def _render_shop_card_legacy(display_name: str, deals: list, *, page: int = 1, total_pages: int = 1) -> BytesIO:
    W, H = 900, 820
    img, draw = _bg(W, H, particle_count=300)
    top = _header(draw, "DAILY CRATE SHOP", f"{display_name} — Deals refresh daily", W, _GOLD)
    mx, my = 22, top
    _panel(img, draw, (mx, my, mx + W - 44, my + H - top - 18))
    cx = mx + 24
    cy = my + 16

    start = (page - 1) * _PER_PAGE
    page_deals = deals[start:start + _PER_PAGE]
    bw = W - 88

    for deal in page_deals:
        _shadow(img, (cx, cy, cx + bw, cy + 88), r=8, blur=6, dy=3, opacity=40)
        purchased = deal.get("purchased", False)
        discount = int(deal.get("discount_pct", 0))
        is_bundle = deal.get("deal_type") == "bundle"
        outline = _CYAN if is_bundle else _GOLD
        draw.rounded_rectangle((cx, cy, cx + bw, cy + 88), radius=8, fill=_PANEL2, outline=outline)

        if purchased:
            draw.rounded_rectangle((cx, cy, cx + bw, cy + 88), radius=8, fill=(20, 18, 28, 200))

        if is_bundle:
            draw.ellipse((cx + 16, cy + 10, cx + 44, cy + 38), fill=(*_CYAN, 40), outline=_CYAN)
            draw.text((cx + 24, cy + 12), "B", font=F14, fill=_CYAN)
        else:
            draw.ellipse((cx + 16, cy + 10, cx + 44, cy + 38), fill=(*_GOLD, 40), outline=_GOLD)
            draw.text((cx + 24, cy + 12), "C", font=F14, fill=_GOLD)
        draw.text((cx + 54, cy + 10), deal["item_name"], font=F16, fill=_TEXT_BRIGHT)

        label = "Bundle" if is_bundle else "Crate"
        lc = _CYAN if is_bundle else _BLUE
        lw = _tw(draw, label, F11) + 14
        draw.rounded_rectangle((cx + 54, cy + 33, cx + 54 + lw, cy + 48), radius=4, fill=(*lc, 40), outline=lc)
        draw.text((cx + 61, cy + 34), label, font=F11, fill=lc)

        if is_bundle:
            desc = deal.get("desc", "")
            if desc:
                dx = cx + 60 + lw
                draw.text((dx, cy + 34), _fit(draw, desc, bw - dx + cx - 170, F11), font=F11, fill=_TEXT_MUTED)

        if not purchased and discount > 0:
            badge_w = 52
            draw.rounded_rectangle((cx + bw - badge_w - 16, cy + 8, cx + bw - 16, cy + 30), radius=4, fill=_RED)
            draw.text((cx + bw - badge_w - 10, cy + 10), f"-{discount}%", font=F14, fill=_TEXT_BRIGHT)

        orig_s = int(deal.get("original_souls", 0))
        orig_g = int(deal.get("original_gems", 0))
        disc_s = int(deal.get("discounted_souls", 0))
        disc_g = int(deal.get("discounted_gems", 0))

        price_x = cx + 54
        price_y = cy + 52

        if disc_s > 0:
            if discount > 0 and orig_s > disc_s:
                ow = _tw(draw, f"{orig_s:,}", F12)
                draw.text((price_x, price_y + 2), f"{orig_s:,}", font=F12, fill=_TEXT_MUTED)
                draw.line((price_x, price_y + 8, price_x + ow, price_y + 8), fill=_RED, width=1)
                price_x += ow + 12
            draw.text((price_x, price_y), f"{disc_s:,} Souls", font=F14, fill=_GOLD)
            price_x += _tw(draw, f"{disc_s:,} Souls", F14) + 16

        if disc_g > 0:
            if discount > 0 and orig_g > disc_g:
                ow = _tw(draw, f"{orig_g}", F12)
                draw.text((price_x, price_y + 2), f"{orig_g}", font=F12, fill=_TEXT_MUTED)
                draw.line((price_x, price_y + 8, price_x + ow, price_y + 8), fill=_RED, width=1)
                price_x += ow + 12
            draw.text((price_x, price_y), f"{disc_g} Gems", font=F14, fill=_CYAN)

        if purchased:
            draw.text((cx + bw - 100, cy + 58), "SOLD", font=F20, fill=_RED)

        cy += 100

    draw.text((cx, H - 36), f"Page {page}/{total_pages}  •  Deals refresh at midnight UTC", font=F12, fill=_TEXT_MUTED)
    return _save(img)


# Clean weapon-loop card renderers. These are defined last to override the older layouts above.
def _card_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _compact_card_num(value: Any) -> str:
    number = _card_int(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000_000:
        text = f"{number / 1_000_000_000:.1f}B"
    elif number >= 1_000_000:
        text = f"{number / 1_000_000:.1f}M"
    elif number >= 10_000:
        text = f"{number / 1_000:.1f}K"
    else:
        return f"{sign}{number:,}"
    return sign + text.replace(".0", "")


def _card_json(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value in (None, ""):
        return default
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _weapon_quality_label(quality_pct: int) -> str:
    from core.rpg import WEAPON_QUALITY_RARITY_TIERS as _WQRT
    quality = max(0, min(150, int(quality_pct)))
    for low, high, rarity in _WQRT:
        if low <= quality <= high:
            return rarity
    return "Common"


def _weapon_rarity(row: Any) -> str:
    return _weapon_quality_label(_card_int(_get(row, "quality_pct", 50), 50))


def _passive_summary(row: Any) -> str:
    passive = _card_json(_get(row, "passive", None), {})
    if not isinstance(passive, dict) or not passive:
        return "Passive: None"
    name = str(passive.get("name") or passive.get("key") or "Passive").replace("_", " ").title()
    chance = _card_int(passive.get("chance", 0))
    return f"Passive: {name} - {chance}% trigger"


def _affix_summary(row: Any, limit: int = 3) -> str:
    affixes = _card_json(_get(row, "affixes", "[]"), [])
    if not isinstance(affixes, list) or not affixes:
        return "Affixes: None"
    labels: list[str] = []
    for affix in affixes:
        if not isinstance(affix, dict):
            continue
        label = str(affix.get("fmt") or affix.get("name") or affix.get("key") or "").strip()
        if label:
            labels.append(label)
    if not labels:
        return "Affixes: None"
    suffix = "" if len(labels) <= limit else f" +{len(labels) - limit} more"
    return "Affixes: " + " | ".join(labels[:limit]) + suffix


def _weapon_type_label(row: Any) -> str:
    key = _weapon_icon_key(row)
    data = WEAPON_TYPES.get(key, {})
    return str(data.get("name") or key.replace("_", " ").title())


@cached_render()
def render_weapons_card(display_name: str, weapons: list, *, page: int = 1, total_pages: int = 1) -> BytesIO:
    W, H = 1600, 980
    img, draw = _bg(W, H, particle_count=180)
    top = _header(draw, "WEAPON VAULT", f"{display_name} | quality, wear, passives, rerolls", W, _GOLD)

    margin = 28
    panel = (margin, top, W - margin, H - 24)
    _panel(img, draw, panel, r=8, outline=_GOLD)

    items_per_page = 4
    page = max(1, page)
    start = (page - 1) * items_per_page
    page_weapons = list(weapons or [])[start:start + items_per_page]

    x = panel[0] + 24
    y = panel[1] + 22
    row_w = panel[2] - panel[0] - 48
    row_h = 176
    gap = 18

    if not page_weapons:
        empty = (x, y, x + row_w, y + row_h)
        draw.rounded_rectangle(empty, radius=8, fill=_PANEL2, outline=_BORDER)
        _center_text(draw, empty, "No weapons on this page", F24, _TEXT_MUTED)
    for weapon in page_weapons:
        rarity = _weapon_rarity(weapon)
        rc = _col(rarity)
        row_box = (x, y, x + row_w, y + row_h)
        row_fill = _lerp_color(_PANEL2, rc, 0.08)
        _shadow(img, row_box, r=8, blur=8, dy=4, opacity=35)
        draw.rounded_rectangle(row_box, radius=8, fill=row_fill, outline=rc, width=2)
        draw.rectangle((x, y, x + 6, y + row_h), fill=rc)

        icon_box = (x + 22, y + 24, x + 132, y + 134)
        draw.rounded_rectangle(icon_box, radius=8, fill=(9, 8, 15), outline=rc, width=2)
        icon = _art("weapons", _weapon_icon_key(weapon), (92, 92), colorize=rc)
        img.paste(icon, (x + 31, y + 33), icon)

        name_x = x + 158
        stat_x = x + row_w - 270
        name = _weapon_type_label(weapon)
        weapon_id = _get(weapon, "id", "?")
        draw.text((name_x, y + 22), _fit(draw, name, stat_x - name_x - 40, F24), font=F24, fill=_TEXT_BRIGHT)
        id_text = f"#{weapon_id}"
        id_w = _tw(draw, id_text, F14) + 20
        draw.rounded_rectangle((name_x, y + 56, name_x + id_w, y + 82), radius=4, fill=(10, 9, 15), outline=rc)
        _center_text(draw, (name_x, y + 56, name_x + id_w, y + 82), id_text, F14, rc)

        quality_pct = _card_int(_get(weapon, "quality_pct", 50), 50)
        quality = _weapon_quality_label(quality_pct)
        mana_cost = _card_int(_get(weapon, "mana_cost", 3), 3)
        wear = str(_get(weapon, "wear", "Unknown") or "Unknown")
        meta = f"{_weapon_type_label(weapon)} | Quality {quality_pct}% ({quality}) | Mana {mana_cost} | Wear {wear}"
        draw.text((name_x + id_w + 12, y + 61), _fit(draw, meta, stat_x - name_x - id_w - 28, F14), font=F14, fill=_TEXT_MUTED)

        passive_line = _passive_summary(weapon)
        draw.text((name_x, y + 96), _fit(draw, passive_line, stat_x - name_x - 18, F16), font=F16, fill=_GOLD)
        affix_line = _affix_summary(weapon, limit=3)
        draw.text((name_x, y + 124), _fit(draw, affix_line, stat_x - name_x - 18, F13), font=F13, fill=_TEXT_MUTED)

        equipped = _get(weapon, "equipped_creature_id", None)
        status = "Equipped" if equipped is not None else "Vault"
        draw.text((name_x, y + 148), status, font=F12, fill=_GREEN if equipped is not None else _TEXT_MUTED)

        from core.rpg import weapon_stats as _ws_fn
        _wsd = _ws_fn(weapon)
        _si = [(lab, f"+{_wsd.get(k, 0)}", clr) for k, lab, clr in (
            ("str_stat", "STR", _GOLD), ("pr_stat", "DEF", _BLUE), ("hp", "HP", (220, 80, 80)),
            ("wp_stat", "MANA", _CYAN), ("mag_stat", "MAG", (180, 100, 220)),
            ("mr_stat", "RES", (100, 180, 200)),
        ) if _wsd.get(k, 0)]
        _draw_stat_tile(img, draw, stat_x, y + 34, 112, 74, _si[0][0], _si[0][1], _si[0][2])
        if len(_si) > 1:
            _draw_stat_tile(img, draw, stat_x + 134, y + 34, 112, 74, _si[1][0], _si[1][1], _si[1][2])
        draw.text((stat_x, y + 126), "Reroll: b wrr <id> stat/passive", font=F13, fill=_TEXT_MUTED)

        y += row_h + gap

    return _save(img)


def render_crate_open_card(display_name: str, crate_name: str, result: dict, *, weapons: list = None, compact: bool = False) -> BytesIO:
    weapon_list = list(weapons or [])
    ROW_C = 38
    MIN_H = 720
    if compact and weapon_list:
        H = max(MIN_H, 420 + len(weapon_list) * (ROW_C + 6))
    else:
        H = MIN_H
    W = 1000
    img, draw = _bg(W, H, particle_count=150)
    top = _header(draw, "WEAPON CRATE", f"{display_name} opened {crate_name}", W, _ORANGE)

    panel = (28, top, W - 28, H - 22)
    _panel(img, draw, panel, r=8, outline=_ORANGE)

    if compact:
        cy = top + 20
        reward_w = 284
        rewards = [
            ("SOULS", f"{_card_int(result.get('gold', 0)):,}", "currency", "souls", _GOLD),
            ("GEMS", f"{_card_int(result.get('gems', 0)):,}", "currency", "gems", _CYAN),
            ("SWORDS", f"{_card_int(result.get('swords', 0)):,}", "consumable", "hunt_sword", _GREEN),
        ]
        for idx, (label, value, kind, key, color) in enumerate(rewards):
            bx = 52 + idx * (reward_w + 18)
            by = cy
            draw.rounded_rectangle((bx, by, bx + reward_w, by + 72), radius=8, fill=_PANEL2, outline=color, width=1)
            draw.text((bx + 18, by + 10), label, font=F12, fill=_TEXT_MUTED)
            draw.text((bx + 18, by + 30), value, font=F22, fill=color)
            icon = _art(kind, key, (36, 36))
            img.paste(icon, (bx + reward_w - 52, by + 20), icon)
        cy += 90

        if weapon_list:
            draw.text((52, cy), f"ACQUIRED WEAPONS ({len(weapon_list)})", font=F13, fill=_TEXT_MUTED)
            cy += 22
            for w in weapon_list:
                rarity = _weapon_rarity(w)
                rc = _col(rarity)
                y0 = cy
                draw.rounded_rectangle((52, y0, W - 52, y0 + ROW_C), radius=6, fill=_PANEL2, outline=_lerp_color(rc, _BORDER, 0.15), width=1)
                icon = _art("weapons", _weapon_icon_key(w), (26, 26), colorize=rc)
                img.paste(icon, (60, y0 + 6), icon)
                draw.text((94, y0 + 4), _fit(draw, str(_get(w, "name", "?")), 320, F13), font=F13, fill=rc)
                quality_pct = _card_int(_get(w, "quality_pct", 50), 50)
                draw.text((430, y0 + 4), _fit(draw, _weapon_type_label(w), 130, F11), font=F11, fill=_TEXT_MUTED)
                draw.text((570, y0 + 4), f"Q{quality_pct}%", font=F12, fill=_GOLD)
                passive = _passive_summary(w)
                if passive:
                    draw.text((640, y0 + 5), _fit(draw, passive, 330, F11), font=F11, fill=_GOLD)
                cy += ROW_C + 6
        return _save(img)

    featured = weapon_list[0] if weapon_list else None

    hero = (52, top + 28, W - 52, top + 254)
    draw.rounded_rectangle(hero, radius=8, fill=_PANEL2, outline=_CYAN, width=2)
    draw.rectangle((hero[0], hero[1], hero[0] + 6, hero[3]), fill=_CYAN)

    if featured:
        rarity = _weapon_rarity(featured)
        rc = _col(rarity)
        icon_box = (hero[0] + 34, hero[1] + 38, hero[0] + 184, hero[1] + 188)
        draw.rounded_rectangle(icon_box, radius=8, fill=(9, 8, 15), outline=rc, width=2)
        icon = _art("weapons", _weapon_icon_key(featured), (126, 126), colorize=rc)
        img.paste(icon, (hero[0] + 46, hero[1] + 50), icon)

        tx = hero[0] + 216
        draw.text((tx, hero[1] + 42), "ACQUIRED WEAPON", font=F13, fill=_TEXT_MUTED)
        draw.text((tx, hero[1] + 72), _fit(draw, _weapon_type_label(featured), 470, F28), font=F28, fill=_TEXT_BRIGHT)
        quality_pct = _card_int(_get(featured, "quality_pct", 50), 50)
        quality = _weapon_quality_label(quality_pct)
        mana_cost = _card_int(_get(featured, "mana_cost", 3), 3)
        wear = str(_get(featured, "wear", "Unknown") or "Unknown")
        meta = f"{_weapon_type_label(featured)} | Quality {quality_pct}% ({quality}) | Mana {mana_cost} | Wear {wear}"
        draw.text((tx, hero[1] + 114), _fit(draw, meta, 580, F15), font=F15, fill=rc)
        draw.text((tx, hero[1] + 146), _fit(draw, _passive_summary(featured), 570, F16), font=F16, fill=_GOLD)
        draw.text((tx, hero[1] + 176), _fit(draw, _affix_summary(featured, limit=3), 570, F13), font=F13, fill=_TEXT_MUTED)

        from core.rpg import weapon_stats as _wfs
        _wfd = _wfs(featured)
        _sf = [(lab, f"+{_wfd.get(k, 0)}", clr) for k, lab, clr in (
            ("str_stat", "STR", _GOLD), ("pr_stat", "DEF", _BLUE), ("hp", "HP", (220, 80, 80)),
            ("wp_stat", "MANA", _CYAN), ("mag_stat", "MAG", (180, 100, 220)),
            ("mr_stat", "RES", (100, 180, 200)),
        ) if _wfd.get(k, 0)]
        stat_x = hero[2] - 232
        _draw_stat_tile(img, draw, stat_x, hero[1] + 58, 96, 68, _sf[0][0], _sf[0][1], _sf[0][2])
        if len(_sf) > 1:
            _draw_stat_tile(img, draw, stat_x + 112, hero[1] + 58, 96, 68, _sf[1][0], _sf[1][1], _sf[1][2])
    else:
        _center_text(draw, hero, "Crate opened", F28, _TEXT_BRIGHT)

    reward_y = hero[3] + 28
    reward_w = 284
    rewards = [
        ("SOULS", f"{_card_int(result.get('gold', 0)):,}", "currency", "souls", _GOLD),
        ("GEMS", f"{_card_int(result.get('gems', 0)):,}", "currency", "gems", _CYAN),
        ("SWORDS", f"{_card_int(result.get('swords', 0)):,}", "consumable", "hunt_sword", _GREEN),
    ]
    for idx, (label, value, kind, key, color) in enumerate(rewards):
        bx = 52 + idx * (reward_w + 18)
        by = reward_y
        draw.rounded_rectangle((bx, by, bx + reward_w, by + 86), radius=8, fill=_PANEL2, outline=color, width=1)
        draw.text((bx + 18, by + 14), label, font=F12, fill=_TEXT_MUTED)
        draw.text((bx + 18, by + 38), value, font=F26, fill=color)
        icon = _art(kind, key, (42, 42))
        img.paste(icon, (bx + reward_w - 58, by + 24), icon)

    if len(weapon_list) > 1:
        draw.text((52, H - 58), f"+{len(weapon_list) - 1} more weapon(s) opened", font=F14, fill=_TEXT_MUTED)
    return _save(img)


def render_shop_card(display_name: str, deals: list, *, page: int = 1, total_pages: int = 1) -> BytesIO:
    W, H = 1040, 620
    img, draw = _bg(W, H, particle_count=130)
    top = _header(draw, "WEAPON CRATE SHOP", f"{display_name} | Weapon Shards only", W, _CYAN)

    panel = (28, top, W - 28, H - 24)
    _panel(img, draw, panel, r=8, outline=_CYAN)
    draw.text((52, top + 24), "Buy crates with Weapon Shards. Souls are not used for weapon crates.", font=F16, fill=_TEXT)

    card_y = top + 68
    card_w = 296
    card_h = 372
    gap = 22
    for idx, deal in enumerate(list(deals or [])[:3]):
        cx = 52 + idx * (card_w + gap)
        crate_key = str(deal.get("item_key") or "cache")
        cost = _card_int(deal.get("shard_cost", 0))
        name = str(deal.get("item_name") or crate_key.replace("_", " ").title())
        desc = str(deal.get("desc") or "")
        rarities = str(deal.get("rarities") or "")
        accent = (_CYAN, _GOLD, _PURPLE)[idx % 3]
        card = (cx, card_y, cx + card_w, card_y + card_h)
        _shadow(img, card, r=8, blur=8, dy=4, opacity=38)
        draw.rounded_rectangle(card, radius=8, fill=_PANEL2, outline=accent, width=2)
        draw.rectangle((cx, card_y, cx + card_w, card_y + 6), fill=accent)

        icon = _art("crate", _deal_icon_key({"item_key": crate_key}), (118, 118))
        img.paste(icon, (cx + 28, card_y + 38), icon)
        draw.text((cx + 28, card_y + 172), _fit(draw, name, card_w - 56, F22), font=F22, fill=_TEXT_BRIGHT)
        if desc:
            draw.text((cx + 28, card_y + 210), _fit(draw, desc, card_w - 56, F13), font=F13, fill=_TEXT_MUTED)
        if rarities:
            draw.text((cx + 28, card_y + 246), "Drops", font=F11, fill=_TEXT_MUTED)
            draw.text((cx + 28, card_y + 268), _fit(draw, rarities, card_w - 56, F13), font=F13, fill=accent)

        price = f"{cost:,} Weapon Shards" if cost > 0 else "Weapon Shards"
        price_box = (cx + 24, card_y + card_h - 76, cx + card_w - 24, card_y + card_h - 26)
        draw.rounded_rectangle(price_box, radius=6, fill=(10, 9, 15), outline=accent)
        _center_text(draw, price_box, price, F18, accent)

    return _save(img)


# Premium Abyssia card system overrides. These final definitions intentionally
# replace the older renderers above while keeping their public signatures stable.


def _premium_draw_title(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], accent: tuple[int, int, int]) -> None:
    cui.draw_text_fit(draw, text, box, cui.get_font(34, bold=True), cui.TEXT_BRIGHT, min_size=22, align="left", bold=True)
    draw.line((box[0], box[3] - 2, min(box[2], box[0] + 260), box[3] - 2), fill=cui.rgba(accent, 170), width=2)


def _premium_asset(kind: str, key: str, size: int | tuple[int, int]) -> Image.Image:
    if isinstance(size, int):
        size = (size, size)
    return cui.load_asset_icon(kind, key, size, pixel=kind in {"creatures", "weapons", "passives", "stats_battle"})


_PREMIUM_ICON_FRAME_DIR = ROOT_DIR / "assets" / "ui" / "icon_frames"
_PREMIUM_FRAME_CACHE: dict[tuple[str, int], Image.Image] = {}


def _premium_frame_key(rarity: str | None) -> str:
    key = safe_key(str(rarity or "neutral"))
    if (_PREMIUM_ICON_FRAME_DIR / f"{key}.png").exists():
        return key
    return "neutral" if (_PREMIUM_ICON_FRAME_DIR / "neutral.png").exists() else "common"


def _premium_frame_asset(rarity: str | None, size: int) -> Image.Image | None:
    key = _premium_frame_key(rarity)
    cache_key = (key, size)
    cached = _PREMIUM_FRAME_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()
    path = _PREMIUM_ICON_FRAME_DIR / f"{key}.png"
    if not path.exists():
        return None
    frame = Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    _PREMIUM_FRAME_CACHE[cache_key] = frame.copy()
    return frame


def _premium_framed_asset(
    kind: str,
    key: str,
    size: int,
    rarity: str | None,
    *,
    inner_scale: float = 0.72,
) -> Image.Image:
    if kind == "passives" and size <= 96:
        inner_scale = max(inner_scale, 0.82)
    icon_size = max(1, int(size * inner_scale))
    icon = _premium_asset(kind, key, icon_size)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    inset = max(3, int(size * (0.09 if size <= 96 else 0.13)))
    accent = cui.rarity_color(str(rarity or "Common"))
    draw.rounded_rectangle(
        (inset, inset, size - inset, size - inset),
        radius=max(5, size // 12),
        fill=(3, 3, 7, 144),
        outline=cui.rgba(accent, 80),
        width=max(1, size // 90),
    )
    canvas.alpha_composite(icon, ((size - icon.width) // 2, (size - icon.height) // 2))
    frame = _premium_frame_asset(rarity, size)
    if frame is not None:
        canvas.alpha_composite(frame, (0, 0))
    return canvas


def _premium_passive_rarity(key: str) -> str:
    data = WEAPON_PASSIVES.get(safe_key(key), {})
    return str(data.get("rarity") or "Common") if isinstance(data, dict) else "Common"


_STAT_ICON_KEYS = {
    "HP": "hp",
    "STR": "str",
    "DEF": "def",
    "PR": "def",
    "MANA": "mana",
    "WP": "mana",
    "MAG": "mag",
    "RES": "res",
    "MR": "res",
}


def _stat_icon_key(label: str) -> str:
    return _STAT_ICON_KEYS.get(str(label).upper(), normalize_key(str(label)))


def _draw_premium_icon_chip(
    img: Image.Image,
    box: tuple[int, int, int, int],
    value: Any,
    color: tuple[int, int, int],
    *,
    kind: str = "stats_battle",
    key: str = "hp",
    icon_size: int = 34,
    font_size: int = 28,
    min_size: int = 15,
    fill: tuple[int, int, int, int] = (7, 6, 10, 205),
) -> None:
    _relic_panel(img, box, color, fill=fill, radius=8)
    icon = _premium_asset(kind, key, icon_size)
    iy = box[1] + (box[3] - box[1] - icon_size) // 2
    img.alpha_composite(icon, (box[0] + 14, iy))
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    cui.draw_text_fit(
        draw,
        str(value),
        (box[0] + 14 + icon_size + 10, box[1] + 6, box[2] - 12, box[3] - 6),
        cui.get_font(font_size, bold=True),
        color,
        min_size,
        "left",
        True,
    )


def _draw_premium_stat_chip(
    img: Image.Image,
    box: tuple[int, int, int, int],
    label: str,
    value: Any,
    color: tuple[int, int, int],
    *,
    icon_size: int = 34,
    font_size: int = 28,
) -> None:
    _draw_premium_icon_chip(
        img,
        box,
        value,
        color,
        kind="stats_battle",
        key=_stat_icon_key(label),
        icon_size=icon_size,
        font_size=font_size,
    )


def _draw_inline_icon_value(
    img: Image.Image,
    xy: tuple[int, int],
    kind: str,
    key: str,
    value: Any,
    color: tuple[int, int, int],
    *,
    icon_size: int = 30,
    font_size: int = 28,
) -> int:
    icon = _premium_asset(kind, key, icon_size)
    img.alpha_composite(icon, xy)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    text = str(value)
    x = xy[0] + icon_size + 8
    y = xy[1] + max(0, (icon_size - font_size) // 2) - 2
    draw.text((x + 2, y + 2), text, font=cui.get_font(font_size, bold=True), fill=(0, 0, 0, 170))
    draw.text((x, y), text, font=cui.get_font(font_size, bold=True), fill=color)
    return icon_size + 8 + cui.text_width(draw, text, cui.get_font(font_size, bold=True))


def _premium_weapon_name(row: Any) -> str:
    return _weapon_type_label(row)


def _premium_weapon_rarity(row: Any) -> str:
    return _weapon_rarity(row)


def _premium_passive_items(row: Any) -> list[dict[str, Any]]:
    passive = _card_json(_get(row, "passive", None), {})
    items: list[dict[str, Any]] = []
    if isinstance(passive, dict) and passive.get("key"):
        items.append(passive)
        extra = passive.get("extra", [])
        if isinstance(extra, list):
            items.extend(item for item in extra if isinstance(item, dict) and item.get("key"))
    return items


def _premium_passive_summary(row: Any, *, limit: int = 2) -> str:
    items = _premium_passive_items(row)
    if not items:
        return "Passive: None"
    labels: list[str] = []
    for item in items[:limit]:
        name = str(item.get("name") or item.get("key") or "Passive").replace("_", " ").title()
        roll = _card_int(item.get("roll", 0))
        value = _card_int(item.get("chance", item.get("value", 0)))
        suffix = f"{value}%" if value else (f"roll {roll}" if roll else "")
        labels.append(f"{name} {suffix}".strip())
    if len(items) > limit:
        labels.append(f"+{len(items) - limit} more")
    return "Passive: " + " | ".join(labels)


def _premium_affix_labels(row: Any, *, limit: int = 3) -> list[str]:
    affixes = _card_json(_get(row, "affixes", "[]"), [])
    if not isinstance(affixes, list):
        return []
    labels: list[str] = []
    for affix in affixes:
        if not isinstance(affix, dict):
            continue
        label = str(affix.get("fmt") or affix.get("name") or affix.get("key") or "").strip()
        if label:
            labels.append(label)
    return labels[:limit]


def _premium_weapon_stats(row: Any) -> list[tuple[str, str, tuple[int, int, int]]]:
    from core.rpg import weapon_stats
    ws = weapon_stats(row)
    mapping = [
        ("str_stat", "STR", cui.GOLD),
        ("pr_stat", "DEF", cui.BLUE),
        ("hp", "HP", (220, 80, 80)),
        ("wp_stat", "MANA", cui.PURPLE),
        ("mag_stat", "MAG", (180, 100, 220)),
        ("mr_stat", "RES", (100, 180, 200)),
    ]
    return [(label, f"+{value}", color) for key, label, color in mapping if (value := ws.get(key, 0))]


_WEAPON_VAULT_BG = ASSET_DIR / "ui" / "weapon_vault_bg_abyssia_pixel.png"
_ZOO_ARCHIVE_BG = ASSET_DIR / "ui" / "zoo_archive_bg_abyssia_pixel.png"
_WEAPON_ROOM_BG = ROOT_DIR / "assets" / "ui" / "backgrounds" / "weapon_vault_room_background.png"
_TEAM_SCENE_BG = ROOT_DIR / "assets" / "ui" / "backgrounds" / "battle_3v3_gothic_arena.png"
_HUNT_SCENE_BG = ROOT_DIR / "assets" / "ui" / "backgrounds" / "hunt_gothic_wilds.png"
_ZOO_SCENE_BG = ROOT_DIR / "assets" / "ui" / "backgrounds" / "zoo_gothic_menagerie.png"


def _generated_bg(path, size: tuple[int, int], accent: tuple[int, int, int]) -> Image.Image:
    manifest_key = {
        "weapon_vault_bg_abyssia_pixel.png": "weapon_vault_room_background",
        "zoo_archive_bg_abyssia_pixel.png": "abyssia_void_base",
    }.get(Path(path).name)
    if manifest_key:
        asset = cui.get_asset(manifest_key, size)
        if asset is not None:
            return asset.convert("RGBA")
    try:
        if path.exists():
            return cui.cover_resize(Image.open(path).convert("RGB"), size).convert("RGBA")
    except OSError:
        pass
    return cui.new_card(size[0], size[1], accent)


def _cover_scene_bg(path: Path, size: tuple[int, int], accent: tuple[int, int, int], *, darken: int = 84) -> Image.Image:
    return _cover_scene_bg_cached(str(path), size, darken).copy()


@functools.lru_cache(maxsize=24)
def _cover_scene_bg_cached(path_text: str, size: tuple[int, int], darken: int) -> Image.Image:
    path = Path(path_text)
    try:
        if path.exists():
            img = cui.cover_resize(Image.open(path).convert("RGBA"), size).convert("RGBA")
        else:
            img = cui.new_card(size[0], size[1], cui.CYAN)
    except OSError:
        img = cui.new_card(size[0], size[1], cui.CYAN)
    img.alpha_composite(Image.new("RGBA", size, (0, 0, 0, darken)))
    cui.draw_vignette(img, 0.88)
    return img


def _fill_cut_box(
    img: Image.Image,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    *,
    cut: int = 10,
) -> None:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.polygon(cui.cut_box_points(box, cut), fill=fill)
    img.alpha_composite(layer)


def _draw_cut_outline(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int, int],
    *,
    cut: int = 10,
    width: int = 1,
) -> None:
    for offset in range(max(1, width)):
        inner = (box[0] + offset, box[1] + offset, box[2] - offset, box[3] - offset)
        pts = cui.cut_box_points(inner, max(0, cut - offset))
        draw.line(pts + [pts[0]], fill=color, width=1)


def _clean_pixel_panel(
    img: Image.Image,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    border: tuple[int, int, int],
    *,
    cut: int = 10,
    width: int = 1,
    shadow: bool = True,
) -> None:
    if shadow:
        _fill_cut_box(img, (box[0] + 4, box[1] + 5, box[2] + 4, box[3] + 5), (0, 0, 0, 96), cut=cut)
    _fill_cut_box(img, box, fill, cut=cut)
    draw = ImageDraw.Draw(img)
    _draw_cut_outline(draw, box, (*border, 195), cut=cut, width=width)


def _shadowed_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    *,
    offset: int = 3,
) -> None:
    x, y = xy
    draw.text((x + offset, y + offset), text, font=font, fill=(0, 0, 0, 185))
    draw.text((x, y), text, font=font, fill=fill)


def _relic_background(width: int, height: int, accent: tuple[int, int, int], *, scene: str = "altar") -> Image.Image:
    img = Image.new("RGBA", (width, height), (5, 4, 8, 255))
    draw = ImageDraw.Draw(img)
    top = (24, 17, 24)
    bottom = (4, 3, 8)
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line((0, y, width, y), fill=(*cui.lerp_color(top, bottom, t), 255))

    noise = Image.effect_noise((width, height), 34).convert("L")
    noise_alpha = noise.point(lambda p: 22 if p > 134 else 0)
    marble = Image.new("RGBA", (width, height), (190, 170, 140, 0))
    marble.putalpha(noise_alpha)
    img.alpha_composite(marble)

    if scene in {"vault", "altar"}:
        arch = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ad = ImageDraw.Draw(arch)
        cx = width // 2
        ad.rounded_rectangle((cx - 430, 120, cx + 430, height + 180), radius=350, outline=(70, 58, 54, 155), width=18)
        ad.rounded_rectangle((cx - 360, 168, cx + 360, height + 160), radius=300, outline=(18, 14, 18, 220), width=58)
        for x in (cx - 500, cx + 500):
            ad.rectangle((x - 34, 210, x + 34, height - 60), fill=(18, 14, 17, 170), outline=(78, 64, 54, 120), width=3)
            for yy in range(245, height - 120, 80):
                ad.line((x - 26, yy, x + 26, yy + 22), fill=(118, 88, 52, 80), width=2)
        img.alpha_composite(arch)
    if scene == "shop":
        table_y = int(height * 0.74)
        draw.polygon(
            [(80, table_y), (width - 80, table_y), (width - 16, height + 60), (16, height + 60)],
            fill=(23, 14, 14, 215),
            outline=(102, 72, 42, 140),
        )
        for x in (110, width - 140):
            draw.rectangle((x, table_y - 96, x + 18, table_y + 8), fill=(96, 76, 54, 190))
            draw.ellipse((x - 8, table_y - 116, x + 26, table_y - 82), fill=(190, 118, 60, 70))
    if scene == "profile":
        draw.ellipse((width - 440, 110, width - 40, 510), outline=(120, 84, 160, 48), width=10)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((width // 2 - 330, height // 2 - 250, width // 2 + 330, height // 2 + 300), fill=cui.rgba(accent, 34))
    glow = glow.filter(ImageFilter.GaussianBlur(24))
    img.alpha_composite(glow)

    mist = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    md = ImageDraw.Draw(mist)
    for idx, alpha in enumerate((30, 22, 18)):
        y = int(height * (0.50 + idx * 0.12))
        md.ellipse((-120, y, width + 160, y + 210), fill=(116, 104, 132, alpha))
    mist = mist.filter(ImageFilter.GaussianBlur(16))
    img.alpha_composite(mist)

    for step, alpha in ((0, 190), (10, 80), (24, 36)):
        draw.rectangle((step, step, width - step - 1, height - step - 1), outline=(0, 0, 0, alpha), width=7)
    for x1, y1, x2, y2 in (
        (26, 26, 140, 26),
        (26, 26, 26, 140),
        (width - 140, 26, width - 26, 26),
        (width - 26, 26, width - 26, 140),
        (26, height - 26, 140, height - 26),
        (26, height - 140, 26, height - 26),
        (width - 140, height - 26, width - 26, height - 26),
        (width - 26, height - 140, width - 26, height - 26),
    ):
        draw.line((x1, y1, x2, y2), fill=cui.rgba(cui.GOLD, 105), width=3)
    cui.draw_vignette(img, 0.92)
    return img


def _relic_panel(
    img: Image.Image,
    box: tuple[int, int, int, int],
    border: tuple[int, int, int],
    *,
    fill: tuple[int, int, int, int] = (13, 10, 16, 222),
    radius: int = 8,
    glow: bool = False,
) -> None:
    cui.draw_pixel_plaque(img, box, fill=fill, border=border, radius=radius, shadow=True, glow=border if glow else False)


def _relic_header(
    img: Image.Image,
    title: str,
    subtitle: str | None,
    accent: tuple[int, int, int],
    *,
    right_label: str | None = None,
) -> int:
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    width, _ = img.size
    plaque = (42, 28, min(width - 42, 920), 116)
    _relic_panel(img, plaque, cui.lerp_color(accent, cui.GOLD, 0.25), fill=(6, 5, 9, 190), radius=8)
    cui.draw_text_fit(draw, title.upper(), (plaque[0] + 28, plaque[1] + 8, plaque[2] - 28, plaque[1] + 62), cui.get_font(54, bold=True), cui.TEXT_BRIGHT, 34, "left", True)
    if subtitle:
        cui.draw_text_fit(draw, subtitle, (plaque[0] + 30, plaque[1] + 62, plaque[2] - 30, plaque[3] - 12), cui.get_font(24), cui.TEXT_MUTED, 18)
    if right_label:
        badge_w = max(150, cui.text_width(draw, right_label.upper(), cui.get_font(22, bold=True)) + 48)
        badge = (width - badge_w - 44, 42, width - 44, 88)
        _relic_panel(img, badge, accent, fill=(8, 6, 10, 178), radius=8, glow=True)
        cui.draw_text_fit(draw, right_label.upper(), (badge[0] + 16, badge[1], badge[2] - 16, badge[3]), cui.get_font(22, bold=True), cui.GOLD, 14, "center", True)
    draw.line((62, 132, width - 62, 132), fill=cui.rgba(cui.GOLD, 96), width=2)
    return 150


def _draw_relic_pedestal(
    img: Image.Image,
    center_x: int,
    base_y: int,
    width: int,
    accent: tuple[int, int, int],
    *,
    height: int = 95,
) -> None:
    draw = ImageDraw.Draw(img)
    shadow = (center_x - width // 2, base_y - 36, center_x + width // 2, base_y + 22)
    draw.ellipse(shadow, fill=(2, 2, 5, 220))
    draw.ellipse((shadow[0] + 10, shadow[1] + 8, shadow[2] - 10, shadow[3] - 8), outline=cui.rgba(accent, 105), width=2)
    top_w = int(width * 0.70)
    lip = (center_x - top_w // 2, base_y - height // 2 - 18, center_x + top_w // 2, base_y - height // 2 + 28)
    draw.ellipse(lip, fill=(16, 12, 18, 232), outline=cui.rgba(accent, 145), width=3)
    draw.line((lip[0] + 20, lip[1] + 10, lip[2] - 20, lip[1] + 10), fill=cui.rgba(cui.TEXT_BRIGHT, 24), width=1)
    draw.line((lip[0] + 24, lip[3] - 9, lip[2] - 24, lip[3] - 9), fill=(0, 0, 0, 132), width=2)


def _draw_rarity_gems(
    img: Image.Image,
    box: tuple[int, int, int, int],
    labels: list[str],
    accent: tuple[int, int, int],
) -> None:
    draw = ImageDraw.Draw(img)
    x1, y1, x2, y2 = box
    count = max(1, len(labels))
    step = (x2 - x1) // count
    for idx, label in enumerate(labels):
        cx = x1 + step * idx + step // 2
        color = cui.rarity_color(label)
        if label not in cui.RARITY_COLORS:
            color = cui.lerp_color(accent, cui.GOLD, idx / max(1, count - 1))
        icon_size = min(52, max(34, y2 - y1 - 6))
        icon = _premium_asset("rarity", safe_key(label), icon_size)
        img.alpha_composite(icon, (cx - icon_size // 2, y1 + (y2 - y1 - icon_size) // 2))
        draw.ellipse((cx - icon_size // 2, y1 + 2, cx + icon_size // 2, y2 - 2), outline=cui.rgba(color, 90), width=1)


def _rarity_labels_from_text(text: str) -> list[str]:
    ordered = ["Rare", "Epic", "Legendary", "Mythic", "Ancient", "Divine", "Eldritch", "Abyssal"]
    lower = text.lower()
    labels = [name for name in ordered if name.lower() in lower]
    if "legendary+" in lower and "Legendary" not in labels:
        labels = ["Legendary", "Mythic", "Ancient", "Eldritch"]
    if "rare to mythic" in lower:
        labels = ["Rare", "Epic", "Legendary", "Mythic"]
    if "epic to abyssal" in lower:
        labels = ["Epic", "Legendary", "Mythic", "Abyssal"]
    return labels or ["Rare", "Epic", "Legendary"]


def _premium_reward_items(result: dict[str, Any]) -> list[tuple[str, str, str, str, tuple[int, int, int]]]:
    rewards: list[tuple[str, str, str, str, tuple[int, int, int]]] = []
    gold = _card_int(result.get("gold", result.get("souls", 0)))
    gems = _card_int(result.get("gems", 0))
    swords = _card_int(result.get("swords", 0))
    if gold:
        rewards.append(("Souls", f"{gold:,}", "currency", "souls", cui.GOLD))
    if gems:
        rewards.append(("Gems", f"{gems:,}", "currency", "gems", cui.CYAN))
    if swords:
        rewards.append(("Hunt Sword", f"{swords:,}", "consumable", "hunt_sword", cui.GREEN))
    materials = result.get("materials", {})
    if isinstance(materials, dict):
        for key, amount in list(materials.items())[:3]:
            qty = _card_int(amount)
            if qty:
                rewards.append((str(key).replace("_", " ").title(), f"{qty:,}", "materials", str(key), cui.GREEN))
    return rewards


def render_hunt_card(
    hunter_name,
    zone_name,
    *,
    rolls,
    souls,
    gems,
    xp=0,
    materials: dict[str, int],
    monsters: list[dict[str, Any]],
    swords_spent,
    swords_found,
    levels=0,
):
    W, H = 1200, 720
    accent = cui.RED
    img = cui.new_card(W, H, accent)
    draw = ImageDraw.Draw(img)
    total = len(monsters)
    shown = min(total, 9)
    subtitle = f"{hunter_name} | {zone_name} | {total} monster{'s' if total != 1 else ''} found"
    top = cui.draw_header(img, "Hunt Result", subtitle, accent=accent)
    cols = 3
    gap = 16
    tile_w = (W - 96 - gap * (cols - 1)) // cols
    tile_h = 158
    base_x, base_y = 48, top + 8
    for idx, mon in enumerate(monsters[:shown]):
        col, row = idx % cols, idx // cols
        x = base_x + col * (tile_w + gap)
        y = base_y + row * (tile_h + gap)
        rarity = str(_get(mon, "rarity", "Common"))
        rc = cui.rarity_color(rarity)
        box = (x, y, x + tile_w, y + tile_h)
        cui.draw_panel(img, box, fill=cui.rgba(cui.lerp_color((18, 14, 26), rc, 0.08), 224), border=rc, radius=18, glow=idx == 0)
        icon = _premium_asset("creatures", normalize_key(str(_get(mon, "name", "unknown"))), 96)
        cui.paste_icon_3d_clipped(img, icon, (x + 72, y + 72), 98, rc, box, 18)
        name = str(_get(mon, "name", "Unknown"))
        cui.draw_text_fit(draw, name, (x + 136, y + 22, x + tile_w - 18, y + 56), cui.get_font(26, bold=True), cui.TEXT_BRIGHT, 18, bold=True)
        cui.draw_rarity_badge(img, (x + 136, y + 60, x + 254, y + 92), rarity)
        status = str(_get(mon, "collection_status", "DUPLICATE")).replace(" DISCOVERY", "")
        if status.upper() == "DUPLICATE":
            status = "OWNED"
        status_color = cui.GREEN if "NEW" in status.upper() else cui.TEXT_MUTED
        cui.draw_tag(img, (x + 258, y + 60, x + tile_w - 18, y + 92), status, status_color)
        value = _card_int(_get(mon, "value", 0))
        draw.text((x + 136, y + 110), f"{value:,} Souls", font=cui.get_font(24, bold=True), fill=cui.GOLD)
    reward_y = H - 100
    reward_w = 230
    rewards = [
        ("Souls", f"{_card_int(souls):,}", "currency", "souls", cui.GOLD),
        ("Gems", f"{_card_int(gems):,}", "currency", "gems", cui.CYAN),
        ("XP", f"{_card_int(xp):,}", "ui", "profile", cui.GREEN),
        ("Hunt Sword", f"+{_card_int(swords_found) - _card_int(swords_spent):,}", "consumable", "hunt_sword", cui.ORANGE),
    ]
    for idx, (label, value, kind, key, color) in enumerate(rewards):
        x = 48 + idx * (reward_w + 18)
        cui.draw_reward_pill(img, (x, reward_y, x + reward_w, reward_y + 68), label, value, color, _premium_asset(kind, key, 42))
    return cui.save_png(img)


@cached_render()
def render_creature_card(
    creature_name: str,
    rarity: str,
    hp: int,
    str_stat: int,
    pr_stat: int,
    wp_stat: int,
    mag_stat: int,
    mr_stat: int,
    role: str,
    ability: str,
    level: int = 1,
    xp: int = 0,
    caught: bool = False,
    player_name: str = "",
    catch_rate: float = 0.0,
    mana: int = 200,
    weight: float | int | None = None,
) -> BytesIO:
    W, H = 1400, 900
    rc = cui.rarity_color(rarity)
    img = _cover_scene_bg(_ZOO_SCENE_BG, (W, H), rc, darken=76)
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    vd.rectangle((0, 340, W, H), fill=(0, 0, 0, 46))
    vd.rectangle((0, 630, W, H), fill=(0, 0, 0, 62))
    img.alpha_composite(veil)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    top = _relic_header(img, "Bestiary", f"{role} | Lv.{level}", rc, right_label=rarity)

    left = (64, top + 24, 620, H - 60)
    right = (660, top + 24, W - 64, H - 60)
    _relic_panel(img, left, rc, fill=(8, 7, 12, 204), glow=True)
    _relic_panel(img, right, cui.lerp_color(rc, cui.GOLD, 0.2), fill=(11, 8, 14, 220))

    portrait_size = 500
    _draw_relic_pedestal(img, (left[0] + left[2]) // 2, left[3] - 126, 430, rc, height=96)
    art = _premium_asset("creatures", normalize_key(creature_name), portrait_size)
    cui.paste_icon_3d_clipped(img, art, ((left[0] + left[2]) // 2, left[1] + 298), portrait_size, rc, left, 8)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    cui.draw_text_fit(draw, creature_name, (left[0] + 34, left[3] - 134, left[2] - 34, left[3] - 78), cui.get_font(46, bold=True), cui.TEXT_BRIGHT, 26, "center", True)
    status = f"Caught by {player_name}" if caught and player_name else ("Caught" if caught else "Uncaught")
    cui.draw_tag(img, (left[0] + 102, left[3] - 60, left[2] - 102, left[3] - 24), status, cui.GREEN if caught else cui.RED)

    draw.text((right[0] + 42, right[1] + 34), "ABILITY", font=cui.get_font(24, bold=True), fill=cui.TEXT_MUTED)
    cui.draw_text_fit(draw, ability, (right[0] + 42, right[1] + 68, right[2] - 42, right[1] + 126), cui.get_font(42, bold=True), cui.TEXT_BRIGHT, 24, "left", True)

    stats = [
        ("HP", hp, cui.RED),
        ("STR", str_stat, cui.GOLD),
        ("DEF", pr_stat, cui.BLUE),
        ("MANA", wp_stat or mana, cui.PURPLE),
        ("MAG", mag_stat, cui.ORANGE),
        ("RES", mr_stat, cui.CYAN),
    ]
    stat_x = right[0] + 42
    stat_y = right[1] + 168
    stat_w = (right[2] - right[0] - 108 - 22) // 2
    stat_h = 76
    for idx, (label, value, color) in enumerate(stats):
        col = idx % 2
        row = idx // 2
        sx = stat_x + col * (stat_w + 22)
        sy = stat_y + row * (stat_h + 18)
        _draw_premium_stat_chip(img, (sx, sy, sx + stat_w, sy + stat_h), label, _compact_card_num(value), color, icon_size=42, font_size=34)

    rate_pct = max(0.0, catch_rate * 100)
    rate_color = cui.GREEN if rate_pct >= 30 else (cui.GOLD if rate_pct >= 1 else cui.RED)
    info_y = right[1] + 464
    draw = ImageDraw.Draw(img)
    draw.text((right[0] + 42, info_y), "CATCH RATE", font=cui.get_font(24, bold=True), fill=cui.TEXT_MUTED)
    draw.text((right[0] + 42, info_y + 34), _format_rate(rate_pct), font=cui.get_font(54, bold=True), fill=rate_color)
    xp_label = f"XP {xp}/100" if caught else "Not Caught"
    cui.draw_progress_bar(img, (right[0] + 328, info_y + 48, right[2] - 42, info_y + 90), xp if caught else 0, 100, rc if caught else cui.RED, xp_label)

    source = f"Weight {weight:g}" if weight is not None else "Weight unknown"
    cui.draw_text_fit(draw, source, (right[0] + 42, right[3] - 78, right[2] - 42, right[3] - 34), cui.get_font(30, bold=True), cui.TEXT_MUTED, 20, "left", True)
    return cui.save_png(img)


@cached_render()
def render_weapon_detail_card(owner_name: str, weapon: Any) -> BytesIO:
    W, H = 1400, 850
    rarity = _premium_weapon_rarity(weapon)
    rc = cui.rarity_color(rarity)
    img = _cover_scene_bg(_WEAPON_ROOM_BG, (W, H), rc, darken=96)
    draw = ImageDraw.Draw(img)
    weapon_name = _premium_weapon_name(weapon)
    quality_pct = _card_int(_get(weapon, "quality_pct", 50), 50)
    quality_tier = _weapon_quality_label(quality_pct)
    quality_color = cui.rarity_color(quality_tier)
    top = _relic_header(img, "Weapon Relic", owner_name, rc, right_label=f"{quality_tier} {quality_pct}%")
    icon_panel = (64, top + 26, 610, H - 60)
    info_panel = (650, top + 26, W - 64, H - 60)
    _relic_panel(img, icon_panel, rc, fill=(8, 6, 11, 204), glow=True)
    _relic_panel(img, info_panel, cui.lerp_color(rc, cui.GOLD, 0.22), fill=(12, 9, 15, 224))

    _draw_relic_pedestal(img, (icon_panel[0] + icon_panel[2]) // 2, icon_panel[3] - 104, 390, rc, height=96)
    icon = _premium_framed_asset("weapons", _weapon_icon_key(weapon), 430, rarity, inner_scale=0.70)
    cui.paste_icon_3d_clipped(img, icon, ((icon_panel[0] + icon_panel[2]) // 2, icon_panel[1] + 276), 440, rc, icon_panel, 8)
    cui.draw_rarity_badge(img, (icon_panel[0] + 112, icon_panel[3] - 82, icon_panel[2] - 112, icon_panel[3] - 40), quality_tier)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

    cui.draw_text_fit(draw, weapon_name, (info_panel[0] + 42, info_panel[1] + 34, info_panel[2] - 42, info_panel[1] + 96), cui.get_font(58, bold=True), cui.TEXT_BRIGHT, 34, "left", True)
    draw.text((info_panel[0] + 46, info_panel[1] + 108), str(_get(weapon, "wear", "Pristine")), font=cui.get_font(30, bold=True), fill=quality_color)
    _draw_inline_icon_value(img, (info_panel[0] + 236, info_panel[1] + 104), "stats_battle", "mana", _compact_card_num(_get(weapon, "mana_cost", 0)), cui.PURPLE, icon_size=34, font_size=29)

    stats = _premium_weapon_stats(weapon)
    stat_items = stats + [
        ("MANA", str(_card_int(_get(weapon, "mana_cost", 0))), cui.PURPLE),
        ("QUAL", f"{quality_pct}%", quality_color),
    ]
    stat_items = stat_items[:4]
    stat_y = info_panel[1] + 166
    stat_w = (info_panel[2] - info_panel[0] - 112 - 18 * (len(stat_items) - 1)) // max(1, len(stat_items))
    for idx, (label, value, color) in enumerate(stat_items):
        x = info_panel[0] + 42 + idx * (stat_w + 18)
        chip = (x, stat_y, x + stat_w, stat_y + 92)
        if label == "QUAL":
            _relic_panel(img, chip, color, fill=(6, 5, 10, 205), radius=8)
            draw = ImageDraw.Draw(img)
            cui.draw_text_fit(draw, quality_tier.upper(), (chip[0] + 14, chip[1] + 12, chip[2] - 14, chip[1] + 38), cui.get_font(18, bold=True), cui.TEXT_MUTED, 11, "center", True)
            cui.draw_text_fit(draw, value, (chip[0] + 14, chip[1] + 38, chip[2] - 14, chip[3] - 10), cui.get_font(34, bold=True), color, 18, "center", True)
        else:
            _draw_premium_stat_chip(img, chip, label, value, color, icon_size=42, font_size=34)

    passive_line = _premium_passive_summary(weapon, limit=2).replace("Passive: ", "")
    passive_box = (info_panel[0] + 42, stat_y + 134, info_panel[2] - 42, stat_y + 242)
    _relic_panel(img, passive_box, cui.GOLD, fill=(7, 5, 9, 198), radius=8)
    draw = ImageDraw.Draw(img)
    draw.text((passive_box[0] + 24, passive_box[1] + 16), "PASSIVE", font=cui.get_font(22, bold=True), fill=cui.TEXT_MUTED)
    passives = _premium_passive_items(weapon)
    text_x = passive_box[0] + 24
    if passives:
        for idx, passive in enumerate(passives[:2]):
            p_key = str(passive.get("key", ""))
            p_icon = _premium_framed_asset("passives", p_key, 64, _premium_passive_rarity(p_key), inner_scale=0.84)
            img.alpha_composite(p_icon, (passive_box[0] + 22 + idx * 70, passive_box[1] + 38))
        text_x += min(2, len(passives)) * 70 + 18
    cui.draw_text_fit(draw, passive_line, (text_x, passive_box[1] + 45, passive_box[2] - 24, passive_box[3] - 14), cui.get_font(30, bold=True), cui.GOLD, 22, "left", True)

    affixes = _premium_affix_labels(weapon, limit=4)
    draw.text((info_panel[0] + 42, passive_box[3] + 36), "AFFIXES", font=cui.get_font(22, bold=True), fill=cui.TEXT_MUTED)
    if affixes:
        tag_w = (info_panel[2] - info_panel[0] - 104 - 18) // 2
        for idx, label in enumerate(affixes):
            col = idx % 2
            row = idx // 2
            x = info_panel[0] + 42 + col * (tag_w + 18)
            y = passive_box[3] + 74 + row * 52
            cui.draw_tag(img, (x, y, x + tag_w, y + 38), label, rc if idx == 0 else cui.TEXT_MUTED)
    else:
        draw.text((info_panel[0] + 42, passive_box[3] + 78), "None", font=cui.get_font(28), fill=cui.TEXT_MUTED)
    return cui.save_png(img)


@cached_render()
def render_weapons_card(display_name: str, weapons: list, *, page: int = 1, total_pages: int = 1) -> BytesIO:
    W, H = 1400, 1000
    img = _cover_scene_bg(_WEAPON_ROOM_BG, (W, H), cui.GOLD, darken=86)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    top = _relic_header(img, "Weapon Vault", display_name, cui.GOLD, right_label="Relic Vault")

    page_weapons = list(weapons or [])[(max(1, page) - 1) * 5:(max(1, page) - 1) * 5 + 5]
    if not page_weapons:
        empty = (360, 360, W - 360, 640)
        _relic_panel(img, empty, cui.GOLD, fill=(7, 6, 10, 210), glow=True)
        draw = ImageDraw.Draw(img)
        cui.draw_text_fit(draw, "No weapons in this vault", empty, cui.get_font(42, bold=True), cui.TEXT_MUTED, 24, "center", True)
        return cui.save_png(img)

    featured = page_weapons[0]
    rarity = _premium_weapon_rarity(featured)
    rc = cui.rarity_color(rarity)
    quality_pct = _card_int(_get(featured, "quality_pct", 50), 50)
    quality_tier = _weapon_quality_label(quality_pct)
    quality_color = cui.rarity_color(quality_tier)
    weapon_name = _premium_weapon_name(featured)

    center_x = W // 2
    _draw_relic_pedestal(img, center_x, 660, 520, rc, height=118)
    icon = _premium_framed_asset("weapons", _weapon_icon_key(featured), 530, rarity, inner_scale=0.70)
    cui.paste_icon_3d(img, icon, (center_x, 414), 520, rc)
    draw = ImageDraw.Draw(img)
    draw.ellipse((center_x - 270, 612, center_x + 270, 730), outline=cui.rgba(rc, 126), width=3)
    draw.ellipse((center_x - 190, 638, center_x + 190, 704), outline=cui.rgba(cui.GOLD, 90), width=2)

    info = (335, 692, W - 335, 890)
    _relic_panel(img, info, rc, fill=(8, 6, 10, 214), glow=True)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, weapon_name, (info[0] + 34, info[1] + 18, info[2] - 34, info[1] + 78), cui.get_font(54, bold=True), cui.TEXT_BRIGHT, 32, "center", True)
    meta_box = (info[0] + 150, info[1] + 84, info[2] - 150, info[1] + 128)
    _relic_panel(img, meta_box, quality_color, fill=(6, 5, 10, 168), radius=8)
    draw = ImageDraw.Draw(img)
    q_text = f"{quality_pct}%"
    q_w = cui.text_width(draw, q_text, cui.get_font(27, bold=True))
    draw.text((meta_box[0] + 34, meta_box[1] + 8), q_text, font=cui.get_font(27, bold=True), fill=quality_color)
    _draw_inline_icon_value(img, (meta_box[0] + 58 + q_w, meta_box[1] + 6), "stats_battle", "mana", _compact_card_num(_get(featured, "mana_cost", 0)), cui.PURPLE, icon_size=31, font_size=25)
    passive = _premium_passive_summary(featured, limit=1).replace("Passive: ", "")
    passive_items = _premium_passive_items(featured)
    if passive_items:
        p_key = str(passive_items[0].get("key", ""))
        p_icon = _premium_framed_asset("passives", p_key, 36, _premium_passive_rarity(p_key), inner_scale=0.88)
        img.alpha_composite(p_icon, (meta_box[2] - 50, meta_box[1] + 4))
    passive_text = (info[0] + 42, info[1] + 138, info[2] - 42, info[1] + 178)
    if passive_items:
        p_key = str(passive_items[0].get("key", ""))
        p_icon = _premium_framed_asset("passives", p_key, 50, _premium_passive_rarity(p_key), inner_scale=0.84)
        icon_x = info[0] + 68
        img.alpha_composite(p_icon, (icon_x, info[1] + 132))
        passive_text = (icon_x + 64, info[1] + 136, info[2] - 54, info[1] + 178)
    cui.draw_text_fit(draw, passive, passive_text, cui.get_font(28, bold=True), cui.GOLD, 20, "left" if passive_items else "center", True)

    def draw_side_slot(weapon: Any, box: tuple[int, int, int, int]) -> None:
        rarity = _premium_weapon_rarity(weapon)
        rc = cui.rarity_color(rarity)
        quality_pct = _card_int(_get(weapon, "quality_pct", 50), 50)
        _relic_panel(img, box, rc, fill=cui.rgba(cui.lerp_color((7, 6, 10), rc, 0.035), 192), radius=8)
        box_h = box[3] - box[1]
        icon_size = min(164, max(126, box_h - 132))
        icon = _premium_framed_asset("weapons", _weapon_icon_key(weapon), icon_size, rarity, inner_scale=0.68)
        cui.paste_icon_3d_clipped(img, icon, ((box[0] + box[2]) // 2, box[1] + max(86, box_h // 3)), icon_size, rc, box, 8)
        sd = ImageDraw.Draw(img)
        name = _premium_weapon_name(weapon)
        name_y = box[3] - 112
        cui.draw_text_fit(sd, name, (box[0] + 20, name_y, box[2] - 20, name_y + 42), cui.get_font(27, bold=True), cui.TEXT_BRIGHT, 18, "center", True)
        meta_box = (box[0] + 28, name_y + 48, box[2] - 28, name_y + 84)
        _relic_panel(img, meta_box, rc, fill=(5, 5, 9, 154), radius=6)
        sd = ImageDraw.Draw(img)
        sd.text((meta_box[0] + 16, meta_box[1] + 7), f"{quality_pct}%", font=cui.get_font(18, bold=True), fill=rc)
        _draw_inline_icon_value(img, (meta_box[0] + 80, meta_box[1] + 4), "stats_battle", "mana", _compact_card_num(_get(weapon, "mana_cost", 0)), cui.PURPLE, icon_size=25, font_size=17)
        passives = _premium_passive_items(weapon)
        if passives:
            p_key = str(passives[0].get("key", ""))
            p_icon = _premium_framed_asset("passives", p_key, 36, _premium_passive_rarity(p_key), inner_scale=0.88)
            img.alpha_composite(p_icon, (meta_box[2] - 46, meta_box[1]))

    slots = [
        (70, 215, 330, 535),
        (W - 330, 215, W - 70, 535),
        (92, 590, 318, 860),
        (W - 318, 590, W - 92, 860),
    ]
    for weapon, box in zip(page_weapons[1:], slots):
        draw_side_slot(weapon, box)
    return cui.save_png(img)


def render_crate_open_card(display_name: str, crate_name: str, result: dict, *, weapons: list = None, compact: bool = False) -> BytesIO:
    weapon_list = list(weapons or [])
    featured = max(weapon_list, key=lambda row: _card_int(_get(row, "quality_pct", 50), 50), default=None)
    rarity = _premium_weapon_rarity(featured) if featured else "Rare"
    rc = cui.rarity_color(rarity)
    W, H = (1400, 1040) if compact and len(weapon_list) > 4 else (1400, 940)
    img = _cover_scene_bg(_WEAPON_ROOM_BG, (W, H), rc, darken=92)
    draw = ImageDraw.Draw(img)
    top = _relic_header(img, "Weapon Crate", f"{display_name} | {crate_name}", rc, right_label="Loot")
    icon_panel = (64, top + 24, 570, H - 118)
    info_panel = (610, top + 24, W - 64, H - 118)
    _relic_panel(img, icon_panel, rc, fill=(8, 6, 11, 204), glow=True)
    _relic_panel(img, info_panel, cui.lerp_color(rc, cui.GOLD, 0.2), fill=(12, 9, 15, 224))
    if featured:
        _draw_relic_pedestal(img, (icon_panel[0] + icon_panel[2]) // 2, icon_panel[3] - 116, 370, rc, height=92)
        icon = _premium_framed_asset("weapons", _weapon_icon_key(featured), 420, rarity, inner_scale=0.70)
        cui.paste_icon_3d_clipped(img, icon, ((icon_panel[0] + icon_panel[2]) // 2, icon_panel[1] + 270), 430, rc, icon_panel, 8)
        q_pct = _card_int(_get(featured, "quality_pct", 50), 50)
        quality_tier = _weapon_quality_label(q_pct)
        quality_color = cui.rarity_color(quality_tier)
        cui.draw_rarity_badge(img, (icon_panel[0] + 112, icon_panel[3] - 88, icon_panel[2] - 112, icon_panel[3] - 46), quality_tier)
        draw = ImageDraw.Draw(img)
        draw.fontmode = "1"
        cui.draw_text_fit(draw, _premium_weapon_name(featured), (info_panel[0] + 42, info_panel[1] + 34, info_panel[2] - 42, info_panel[1] + 96), cui.get_font(58, bold=True), cui.TEXT_BRIGHT, 32, "left", True)
        draw.text((info_panel[0] + 46, info_panel[1] + 110), str(_get(featured, "wear", "Pristine")), font=cui.get_font(29, bold=True), fill=quality_color)
        _draw_inline_icon_value(img, (info_panel[0] + 232, info_panel[1] + 106), "stats_battle", "mana", _compact_card_num(_get(featured, "mana_cost", 0)), cui.PURPLE, icon_size=34, font_size=28)
        stats = _premium_weapon_stats(featured)
        stat_items = (stats + [("MANA", str(_card_int(_get(featured, "mana_cost", 0))), cui.PURPLE)])[:3]
        stat_y = info_panel[1] + 166
        stat_w = (info_panel[2] - info_panel[0] - 108 - 18 * 2) // 3
        for idx, (label, value, color) in enumerate(stat_items):
            x = info_panel[0] + 42 + idx * (stat_w + 18)
            _draw_premium_stat_chip(img, (x, stat_y, x + stat_w, stat_y + 82), label, value, color, icon_size=38, font_size=31)

        passive_line = _premium_passive_summary(featured, limit=2).replace("Passive: ", "")
        passive_box = (info_panel[0] + 42, stat_y + 122, info_panel[2] - 42, stat_y + 226)
        _relic_panel(img, passive_box, cui.GOLD, fill=(7, 5, 9, 198), radius=8)
        draw = ImageDraw.Draw(img)
        draw.text((passive_box[0] + 24, passive_box[1] + 14), "PASSIVE", font=cui.get_font(22, bold=True), fill=cui.TEXT_MUTED)
        passives = _premium_passive_items(featured)
        text_x = passive_box[0] + 24
        for idx, passive in enumerate(passives[:2]):
            p_key = str(passive.get("key", ""))
            p_icon = _premium_framed_asset("passives", p_key, 62, _premium_passive_rarity(p_key), inner_scale=0.84)
            img.alpha_composite(p_icon, (passive_box[0] + 22 + idx * 68, passive_box[1] + 38))
        if passives:
            text_x += min(2, len(passives)) * 68 + 16
        cui.draw_text_fit(draw, passive_line, (text_x, passive_box[1] + 45, passive_box[2] - 24, passive_box[3] - 12), cui.get_font(29, bold=True), cui.GOLD, 20, "left", True)

        affixes = _premium_affix_labels(featured, limit=4)
        draw.text((info_panel[0] + 42, passive_box[3] + 32), "AFFIXES", font=cui.get_font(22, bold=True), fill=cui.TEXT_MUTED)
        if affixes:
            tag_w = (info_panel[2] - info_panel[0] - 104 - 18) // 2
            for idx, label in enumerate(affixes):
                col = idx % 2
                row = idx // 2
                x = info_panel[0] + 42 + col * (tag_w + 18)
                y = passive_box[3] + 70 + row * 50
                cui.draw_tag(img, (x, y, x + tag_w, y + 36), label, rc if idx == 0 else cui.TEXT_MUTED)
    else:
        cui.draw_text_fit(draw, "Crate opened", info_panel, cui.get_font(42, bold=True), cui.TEXT_BRIGHT, 24, "center", True)
    reward_items = _premium_reward_items(result)
    if not reward_items:
        reward_items = [("Loot", "Collected", "crate", "cache", cui.GOLD)]
    reward_y = H - 92
    reward_w = (W - 128 - 18 * 3) // 4
    for idx, (label, value, kind, key, color) in enumerate(reward_items[:4]):
        x = 64 + idx * (reward_w + 18)
        _draw_premium_icon_chip(img, (x, reward_y, x + reward_w, reward_y + 58), value, color, kind=kind, key=key, icon_size=38, font_size=27, min_size=15, fill=(6, 5, 10, 190))
    list_y = reward_y - 66
    remaining_weapons = [w for w in weapon_list if w is not featured] if featured and not compact else weapon_list
    if remaining_weapons:
        badge = (info_panel[0] + 42, list_y, info_panel[2] - 42, list_y + 42)
        _relic_panel(img, badge, rc, fill=(5, 4, 8, 166), radius=8)
        draw = ImageDraw.Draw(img)
        x = badge[0] + 18
        for w in remaining_weapons[:5]:
            w_rarity = _premium_weapon_rarity(w)
            w_rc = cui.rarity_color(w_rarity)
            icon = _premium_framed_asset("weapons", _weapon_icon_key(w), 36, w_rarity, inner_scale=0.62)
            img.alpha_composite(icon, (x, badge[1] + 3))
            x += 46
            draw.ellipse((x - 8, badge[1] + 17, x - 4, badge[1] + 21), fill=w_rc)
            x += 8
        text = f"+{len(remaining_weapons)} added"
        cui.draw_text_fit(draw, text, (x + 8, badge[1], badge[2] - 18, badge[3]), cui.get_font(20, bold=True), rc, 12, "left", True)
    return cui.save_png(img)
    return cui.save_png(img)


def render_shop_card(display_name: str, deals: list, *, page: int = 1, total_pages: int = 1) -> BytesIO:
    W, H = 1400, 850
    shop_scene = ROOT_DIR / "assets" / "ui" / "generated" / "crateshop_vault.png"
    img = _cover_scene_bg(shop_scene, (W, H), cui.GOLD, darken=42)
    draw = ImageDraw.Draw(img)
    top = _relic_header(img, "Crate Shop", f"{display_name} | Weapon Shards", cui.GOLD, right_label="Merchant")
    accents = {"cache": cui.CYAN, "relic": cui.GREEN, "treasure": cui.PURPLE}
    names = {"cache": "Void Cache", "relic": "Eldritch Relic", "treasure": "Abyssal Treasure"}
    card_w, card_h, gap = 392, 590, 32
    base_x = (W - card_w * 3 - gap * 2) // 2
    y = top + 34
    for idx, deal in enumerate(list(deals or [])[:3]):
        crate_key = str(deal.get("item_key") or "cache")
        accent = accents.get(crate_key, (cui.CYAN, cui.GREEN, cui.PURPLE)[idx % 3])
        box = (base_x + idx * (card_w + gap), y, base_x + idx * (card_w + gap) + card_w, y + card_h)
        _relic_panel(img, box, accent, fill=cui.rgba(cui.lerp_color((10, 7, 11), accent, 0.045), 218), radius=8, glow=True)
        _draw_relic_pedestal(img, (box[0] + box[2]) // 2, box[1] + 300, 270, accent, height=58)
        icon = _premium_asset("crate", _deal_icon_key({"item_key": crate_key}), 236)
        cui.paste_icon_3d_clipped(img, icon, ((box[0] + box[2]) // 2, box[1] + 190), 246, accent, box, 8)
        name = str(deal.get("item_name") or names.get(crate_key, crate_key.replace("_", " ").title()))
        draw = ImageDraw.Draw(img)
        cui.draw_text_fit(draw, name, (box[0] + 28, box[1] + 318, box[2] - 28, box[1] + 370), cui.get_font(38, bold=True), cui.TEXT_BRIGHT, 24, "center", True)
        desc = str(deal.get("desc") or "A sealed Abyssia weapon cache.")
        cui.draw_text_fit(draw, desc, (box[0] + 34, box[1] + 378, box[2] - 34, box[1] + 414), cui.get_font(22), cui.TEXT_MUTED, 18, "center")
        rarities = str(deal.get("rarities") or "Rare+ weapons")
        _draw_rarity_gems(img, (box[0] + 36, box[1] + 426, box[2] - 36, box[1] + 488), _rarity_labels_from_text(rarities), accent)
        cost = _card_int(deal.get("shard_cost", 0))
        price = f"{cost:,} Shards" if cost else "Weapon Shards"
        _relic_panel(img, (box[0] + 40, box[3] - 78, box[2] - 40, box[3] - 20), accent, fill=cui.rgba(accent, 54), radius=8)
        shard_icon = _premium_asset("materials", "weapon_shards", 42)
        img.alpha_composite(shard_icon, (box[0] + 72, box[3] - 70))
        draw = ImageDraw.Draw(img)
        cui.draw_text_fit(draw, price, (box[0] + 126, box[3] - 78, box[2] - 58, box[3] - 20), cui.get_font(30, bold=True), cui.TEXT_BRIGHT, 20, "center", True)
    return cui.save_png(img)


@cached_render(ttl=300)
def render_team_card(display_name: str, team: Iterable[Any], *, team_power: int, weapons: dict[int, Any] | None = None) -> BytesIO:
    W, H = 1600, 1000
    img = _cover_scene_bg(_TEAM_SCENE_BG, (W, H), cui.PURPLE, darken=74)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    _relic_header(img, "Battle Team", display_name, cui.PURPLE, right_label=f"Power {team_power:,}")
    members = list(team)[:3]
    from core.battle_engine import compute_display_stats

    summary = (1124, 148, 1552, 202)
    _relic_panel(img, summary, cui.GOLD, fill=(5, 4, 8, 178), radius=8, glow=True)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, f"{len(members)}/3 ARMED", (summary[0] + 22, summary[1], summary[2] - 22, summary[3]), cui.get_font(26, bold=True), cui.GOLD, 16, "center", True)

    slots = [(800, 585, 430), (320, 735, 340), (1280, 735, 340)]

    def draw_weapon(row: Any, center: tuple[int, int], size: int, accent: tuple[int, int, int], *, side: int) -> None:
        weapon_size = max(132, int(size * 0.44))
        icon = _premium_asset("weapons", _weapon_icon_key(row), weapon_size)
        if side < 0:
            icon = icon.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        icon = icon.rotate(-20 if side >= 0 else 20, resample=Image.Resampling.BICUBIC, expand=True)
        held = (center[0] + side * int(size * 0.30), center[1] + int(size * 0.16))
        x = held[0] - icon.width // 2
        y = held[1] - icon.height // 2
        img.alpha_composite(icon, (x, y))

    def draw_actor(idx: int, cr: Any, slot: tuple[int, int, int]) -> None:
        cx, base_y, size = slot
        rarity = str(_get(cr, "rarity", "Common"))
        rc = cui.rarity_color(rarity)
        name = str(_get(cr, "name", "?"))
        actor_draw = ImageDraw.Draw(img)
        cui.draw_pixel_platform(img, (cx, base_y + 6), int(size * 1.04), 58, rc, alpha=124)

        art = _premium_asset("creatures", normalize_key(name), size)
        if cx < W // 2:
            art = art.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        cui.paste_icon_3d(img, art, (cx, base_y - size // 2), size, rc, glow_alpha=0, rim_light=False)

        w_row = weapons.get(_card_int(_get(cr, "id", 0))) if weapons else None
        side = 1 if cx <= W // 2 else -1
        if w_row:
            draw_weapon(w_row, (cx, base_y - size // 2), size, cui.rarity_color(_premium_weapon_rarity(w_row)), side=side)

        plaque_w = 440 if size >= 400 else 430
        plaque_h = 210 if size >= 400 else 200
        plaque = (cx - plaque_w // 2, base_y + 42, cx + plaque_w // 2, base_y + 42 + plaque_h)
        _relic_panel(img, plaque, rc, fill=(5, 4, 8, 196), radius=8, glow=False)
        actor_draw = ImageDraw.Draw(img)
        cui.draw_text_fit(actor_draw, name, (plaque[0] + 20, plaque[1] + 8, plaque[2] - 20, plaque[1] + 44), cui.get_font(31, bold=True), cui.TEXT_BRIGHT, 20, "center", True)
        meta = f"Slot {idx + 1} | Lv.{_get(cr, 'level', 1)} | {rarity}"
        cui.draw_text_fit(actor_draw, meta, (plaque[0] + 22, plaque[1] + 46, plaque[2] - 22, plaque[1] + 74), cui.get_font(19, bold=True), rc, 12, "center", True)
        stats = compute_display_stats(cr)
        stat_rows = [
            [("HP", stats.get("HP", 0), cui.RED),  ("STR", stats.get("STR", 0), cui.GOLD), ("DEF", stats.get("DEF", 0), cui.BLUE)],
            [("MAG", stats.get("MAG", 0), cui.ORANGE), ("MANA", stats.get("MANA", 0), cui.PURPLE), ("RES", stats.get("RES", 0), cui.CYAN)],
        ]
        x = plaque[0] + 22
        stat_w = (plaque_w - 60) // 3
        for row_idx, stat_items in enumerate(stat_rows):
            stat_y = plaque[1] + 78 + row_idx * 46
            for s_idx, (label, value, color) in enumerate(stat_items):
                box = (x + s_idx * stat_w, stat_y, x + s_idx * stat_w + stat_w - 8, stat_y + 40)
                _draw_premium_stat_chip(img, box, label, _compact_card_num(value), color, icon_size=24, font_size=18)

        if w_row:
            weapon_text = f"#{_get(w_row, 'id', '?')} {_premium_weapon_name(w_row)}"
            passive = _premium_passive_summary(w_row, limit=1).replace("Passive: ", "")
            if passive:
                weapon_text += f" | {passive}"
            actor_draw = ImageDraw.Draw(img)
            cui.draw_text_fit(actor_draw, weapon_text, (plaque[0] + 22, plaque[1] + 172, plaque[2] - 22, plaque[3] - 10), cui.get_font(18, bold=True), cui.GOLD, 12, "center", True)
        else:
            actor_draw = ImageDraw.Draw(img)
            cui.draw_text_fit(actor_draw, "No weapon equipped", (plaque[0] + 22, plaque[1] + 172, plaque[2] - 22, plaque[3] - 10), cui.get_font(18), cui.TEXT_MUTED, 12, "center")

    layered_members = sorted(enumerate(zip(slots, members)), key=lambda item: item[1][0][1], reverse=True)
    for idx, pair in layered_members:
        draw_actor(idx, pair[1], pair[0])
    return cui.save_png(img)


@cached_render(ttl=300)
def render_collection_card(
    display_name: str,
    entries: Iterable[dict[str, Any]],
    caught_count: int,
    total_templates: int,
    page: int,
    total_pages: int,
    *,
    next_entries: Iterable[dict[str, Any]] | None = None,
    layout_version: int = 3,
) -> BytesIO:
    W, H = 1600, 1000
    img = _cover_scene_bg(_ZOO_SCENE_BG, (W, H), cui.CYAN, darken=58)
    stage = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd_stage = ImageDraw.Draw(stage)
    sd_stage.rectangle((0, 320, W, H), fill=(0, 0, 0, 42))
    sd_stage.rectangle((0, 670, W, H), fill=(0, 0, 0, 72))
    img.alpha_composite(stage)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

    _relic_header(img, "Spirit Index", f"{display_name} | Page {page}/{total_pages}", cui.CYAN, right_label=f"{caught_count}/{total_templates}")
    pct = caught_count / max(1, total_templates)
    entries_list = list(entries)
    next_entries_list = list(next_entries or [])

    progress_box = (1046, 148, 1538, 196)
    _relic_panel(img, progress_box, cui.CYAN, fill=(3, 6, 10, 156), radius=8)
    bar = (progress_box[0] + 18, progress_box[1] + 14, progress_box[2] - 18, progress_box[3] - 14)
    fill_w = int((bar[2] - bar[0] - 8) * cui.clamp(pct))
    _relic_panel(img, bar, cui.CYAN, fill=(3, 6, 10, 205), radius=8)
    if fill_w > 0:
        _fill_cut_box(img, (bar[0] + 4, bar[1] + 4, bar[0] + 4 + fill_w, bar[3] - 4), cui.rgba(cui.CYAN, 224), cut=5)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, f"{pct:.1%}", (bar[0] + 12, bar[1], bar[2] - 12, bar[3]), cui.get_font(22, bold=True), cui.TEXT_BRIGHT, 13, "center", True)

    display_entries = entries_list[:5]
    next_preview_entries = next_entries_list[:5]

    def creature_art(entry: dict[str, Any], size: int) -> tuple[Image.Image, tuple[int, int, int], str, bool, str]:
        caught = bool(entry.get("caught"))
        rarity = str(entry.get("rarity", "Common"))
        rc = cui.rarity_color(rarity) if caught else cui.BORDER
        name = str(entry.get("name", "???")) if caught else "???"
        art = _premium_asset("creatures", normalize_key(str(entry.get("name", "skeleton"))), size)
        if not caught:
            art = ImageOps.grayscale(art).convert("RGBA")
            art.putalpha(118)
        return art, rc, name, caught, rarity

    def paste_creature_sprite(art: Image.Image, cx: int, base_y: int, max_size: int) -> tuple[int, int, int, int]:
        sprite = art.copy()
        bbox = sprite.getbbox()
        if bbox:
            sprite = sprite.crop(bbox)
        sprite.thumbnail((max_size, max_size), Image.Resampling.NEAREST)
        x = cx - sprite.width // 2
        y = base_y - sprite.height + 8
        img.alpha_composite(sprite, (x, y))
        return (x, y, x + sprite.width, y + sprite.height)

    def draw_centered_multiline(
        pd: ImageDraw.ImageDraw,
        text: str,
        box: tuple[int, int, int, int],
        font_size: int,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        *,
        min_size: int = 10,
        max_lines: int = 2,
    ) -> None:
        label = str(text).upper()
        chosen = cui.get_font(font_size, bold=True)
        width = max(1, box[2] - box[0])
        height = max(1, box[3] - box[1])
        line_spacing = 2
        while chosen.size > min_size:
            lines = cui.wrap_text(pd, label, width, chosen, max_lines)
            total_h = len(lines) * chosen.size + max(0, len(lines) - 1) * line_spacing
            if total_h <= height:
                break
            chosen = cui.get_font(chosen.size - 1, bold=True)
        lines = cui.wrap_text(pd, label, width, chosen, max_lines)
        total_h = len(lines) * chosen.size + max(0, len(lines) - 1) * line_spacing
        y = box[1] + max(0, (height - total_h) // 2)
        for line in lines:
            bounds = pd.textbbox((0, 0), line, font=chosen)
            tw = bounds[2] - bounds[0]
            x = box[0] + (width - tw) // 2 - bounds[0]
            pd.text((x, y - bounds[1]), line, font=chosen, fill=color)
            y += chosen.size + line_spacing

    def draw_showcase(entry: dict[str, Any], slot: tuple[Any, ...]) -> None:
        cx, base_y, size, plaque_w, plaque_h, *flags = slot
        plaque_above = "above" in flags
        front_anchor = "front" in flags
        art, rc, name, caught, rarity = creature_art(entry, size)
        platform_w = int(size * (0.92 if front_anchor else 0.74))
        platform_h = 40 if size >= 320 else 34
        cui.draw_pixel_platform(img, (cx, base_y + 8), platform_w, platform_h, rc, alpha=46)
        sprite_box = paste_creature_sprite(art, cx, base_y - 10 if front_anchor else base_y, size)
        plaque_y = max(214, sprite_box[1] - plaque_h - 12) if plaque_above else base_y + 20
        plaque = (cx - plaque_w // 2, plaque_y, cx + plaque_w // 2, plaque_y + plaque_h)
        _relic_panel(
            img,
            plaque,
            rc,
            fill=cui.rgba(cui.lerp_color((3, 4, 8), rc, 0.07 if caught else 0.0), 214),
            radius=8,
            glow=False,
        )
        pd = ImageDraw.Draw(img)
        title_size = 32 if size >= 360 else 22
        title_bottom = plaque[1] + (52 if size >= 360 else 42)
        draw_centered_multiline(
            pd,
            name,
            (plaque[0] + 18, plaque[1] + 7, plaque[2] - 18, title_bottom),
            title_size,
            cui.TEXT_BRIGHT if caught else cui.TEXT_MUTED,
            min_size=11 if size >= 360 else 10,
            max_lines=2,
        )
        if caught:
            meta = f"{rarity} | x{entry.get('total', 1)} | Lv.{entry.get('max_level', 1)}"
        else:
            meta = "Unfound"
        cui.draw_text_fit(
            pd,
            meta,
            (plaque[0] + 20, title_bottom + 3, plaque[2] - 20, plaque[3] - 8),
            cui.get_font(18 if size >= 360 else 14, bold=True),
            rc,
            10,
            "center",
            True,
        )

    slots = [
        (800, 612, 330, 454, 78),
        (444, 574, 250, 354, 66, "above"),
        (1154, 574, 250, 354, 66, "above"),
        (302, 690, 190, 320, 64, "front"),
        (1298, 690, 190, 320, 64, "front"),
    ]
    for entry, slot in sorted(zip(display_entries, slots), key=lambda item: item[1][1]):
        draw_showcase(entry, slot)

    strip = (448, 864, W - 448, 958)
    _relic_panel(img, strip, cui.CYAN, fill=(2, 4, 8, 176), radius=8)
    sd = ImageDraw.Draw(img)
    sd.fontmode = "1"
    footer_text = "Next Page" if next_preview_entries and page < total_pages else "End"
    cui.draw_text_fit(sd, footer_text, (strip[0] + 18, strip[1] + 12, strip[0] + 150, strip[3] - 12), cui.get_font(19, bold=True), cui.CYAN, 12, "center", True)
    if next_preview_entries and page < total_pages:
        cell_w, cell_h, gap = 70, 68, 13
        start_x = strip[0] + 166
        cell_y = strip[1] + 13
        for idx, entry in enumerate(next_preview_entries[:5]):
            x = start_x + idx * (cell_w + gap)
            caught = bool(entry.get("caught"))
            rarity = str(entry.get("rarity", "Common"))
            rc = cui.rarity_color(rarity) if caught else cui.BORDER
            box = (x, cell_y, x + cell_w, cell_y + cell_h)
            _relic_panel(img, box, rc, fill=(2, 4, 7, 158), radius=7)
            art, _, _, _, _ = creature_art(entry, 62)
            preview = art.copy()
            bbox = preview.getbbox()
            if bbox:
                preview = preview.crop(bbox)
            preview.thumbnail((58, 58), Image.Resampling.NEAREST)
            img.alpha_composite(preview, (box[0] + (cell_w - preview.width) // 2, box[1] + 4))
            label = str(entry.get("total", 0)) if caught else "?"
            cui.draw_text_fit(sd, label, (box[0] + 5, box[3] - 17, box[2] - 5, box[3] - 2), cui.get_font(11, bold=True), rc, 8, "right", True)
    elif page >= total_pages:
        cui.draw_text_fit(sd, "No more pages", (strip[0] + 164, strip[1] + 8, strip[2] - 18, strip[3] - 8), cui.get_font(20, bold=True), cui.TEXT_MUTED, 12, "center", True)

    page_badge = (64, H - 56, 360, H - 24)
    _relic_panel(img, page_badge, cui.CYAN, fill=(0, 0, 0, 126), radius=8)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, f"Page {page}/{total_pages}", (page_badge[0] + 12, page_badge[1], page_badge[2] - 12, page_badge[3]), cui.get_font(16), cui.TEXT_MUTED, 11, "center")
    return cui.save_png(img)


def render_autohunt_card(zone_name, *, hours, souls, gems, xp, materials, creatures, levels=0):
    W, H = 1200, 720
    img = cui.new_card(W, H, cui.ORANGE)
    draw = ImageDraw.Draw(img)
    top = cui.draw_header(img, "Expedition Report", f"{hours}h through {zone_name}", accent=cui.ORANGE)
    rewards = [
        ("Souls", f"{_card_int(souls):,}", "currency", "souls", cui.GOLD),
        ("Gems", f"{_card_int(gems):,}", "currency", "gems", cui.CYAN),
        ("XP", f"{_card_int(xp):,}", "ui", "profile", cui.GREEN),
        ("Levels", str(levels), "ui", "profile", cui.ORANGE),
    ]
    for idx, (label, value, kind, key, color) in enumerate(rewards):
        x = 52 + idx * 278
        cui.draw_reward_pill(img, (x, top + 24, x + 250, top + 98), label, value, color, _premium_asset(kind, key, 42))
    panel = (52, top + 130, W - 52, H - 82)
    cui.draw_panel(img, panel, fill=cui.PANEL, border=cui.ORANGE, radius=18)
    _premium_draw_title(draw, "Creatures Found", (panel[0] + 28, panel[1] + 24, panel[2] - 28, panel[1] + 64), cui.ORANGE)
    for idx, line in enumerate(list(creatures)[:12]):
        y = panel[1] + 84 + idx * 30
        draw.text((panel[0] + 32, y), cui.truncate_text(draw, str(line), panel[2] - panel[0] - 64, cui.get_font(22)), font=cui.get_font(22), fill=cui.TEXT_BRIGHT)
    return cui.save_png(img)


@cached_render(ttl=120)
def render_hub_panel_card(
    display_name: str,
    screen: str,
    title: str,
    subtitle: str,
    rows: Iterable[dict[str, Any]],
    *,
    progress_value: int = 0,
    progress_total: int = 1,
    balance: str = "",
    notice: str | None = None,
    rewards: Iterable[dict[str, Any]] | None = None,
    footer: str = "",
    layout_version: int = 1,
) -> BytesIO:
    W, H = 860, 1040
    accent_by_screen = {
        "daily": cui.PURPLE,
        "weekly": cui.CYAN,
        "quests": cui.GOLD,
    }
    accent = accent_by_screen.get(screen, cui.PURPLE)
    img = _relic_background(W, H, accent, scene="profile")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 80))
    img.alpha_composite(overlay)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

    top = _relic_header(img, title, subtitle, accent, right_label=screen)
    panel = (58, top + 24, W - 58, H - 64)
    _relic_panel(img, panel, accent, fill=(12, 10, 18, 224), radius=10)

    header_y = panel[1] + 30
    icon = _premium_asset("ui", screen if screen in {"daily", "quest"} else "quest", 58)
    img.alpha_composite(icon, (panel[0] + 26, header_y + 2))
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(
        draw,
        f"{display_name}'s {title}",
        (panel[0] + 96, header_y, panel[2] - 130, header_y + 38),
        cui.get_font(30, bold=True),
        cui.TEXT_BRIGHT,
        18,
        "left",
        True,
    )
    if balance:
        cui.draw_text_fit(
            draw,
            balance,
            (panel[0] + 96, header_y + 38, panel[2] - 130, header_y + 66),
            cui.get_font(18),
            cui.TEXT_MUTED,
            12,
            "left",
        )

    if notice:
        notice_box = (panel[2] - 170, header_y + 8, panel[2] - 24, header_y + 58)
        _relic_panel(img, notice_box, accent, fill=(8, 7, 14, 205), radius=8)
        cui.draw_text_fit(draw, notice, (notice_box[0] + 12, notice_box[1] + 5, notice_box[2] - 12, notice_box[3] - 5), cui.get_font(15, bold=True), accent, 10, "center", True)

    y = panel[1] + 118
    row_h = 80
    gap = 10
    row_list = list(rows)[:7]
    for idx, row in enumerate(row_list):
        current = _card_int(row.get("current", 0))
        target = max(1, _card_int(row.get("target", 1), 1))
        done = bool(row.get("done", current >= target))
        ready = bool(row.get("ready", current >= target and not bool(row.get("claimed", False))))
        claimed = bool(row.get("claimed", False))
        color = cui.GREEN if done or claimed else (cui.GOLD if ready else accent)
        row_box = (panel[0] + 24, y, panel[2] - 24, y + row_h)
        fill = (32, 29, 38, 224) if not done else (27, 35, 31, 222)
        _relic_panel(img, row_box, color, fill=fill, radius=8)

        icon_kind = str(row.get("icon_kind", "ui"))
        icon_key = str(row.get("icon_key", "quest"))
        icon_img = _premium_asset(icon_kind, icon_key, 42)
        img.alpha_composite(icon_img, (row_box[0] + 18, row_box[1] + 19))
        text_color = cui.TEXT_MUTED if claimed else cui.TEXT_BRIGHT
        title_text = str(row.get("label", "Task")).upper()
        desc_text = str(row.get("desc", "")).strip()
        cui.draw_text_fit(draw, title_text, (row_box[0] + 76, row_box[1] + 10, row_box[2] - 152, row_box[1] + 38), cui.get_font(21, bold=True), text_color, 12, "left", True)
        if desc_text:
            cui.draw_text_fit(draw, desc_text, (row_box[0] + 76, row_box[1] + 40, row_box[2] - 184, row_box[1] + 65), cui.get_font(14), cui.TEXT_MUTED, 10, "left")
        progress_label = f"{current:,}/{target:,}"
        cui.draw_text_fit(draw, progress_label, (row_box[2] - 142, row_box[1] + 10, row_box[2] - 22, row_box[1] + 36), cui.get_font(20, bold=True), color, 12, "right", True)
        bar_box = (row_box[2] - 156, row_box[1] + 50, row_box[2] - 24, row_box[1] + 67)
        cui.draw_progress_bar(img, bar_box, current, target, color)
        if claimed:
            strike_y = row_box[1] + 30
            draw.line((row_box[0] + 76, strike_y, row_box[2] - 168, strike_y), fill=cui.rgba(cui.TEXT_MUTED, 130), width=3)
        y += row_h + gap

    reward_list = list(rewards or [])
    if reward_list:
        y += 4
        draw.text((panel[0] + 28, y), "REWARDS", font=cui.get_font(20, bold=True), fill=cui.TEXT_MUTED)
        y += 30
        pill_w = (panel[2] - panel[0] - 64 - 16 * (min(3, len(reward_list)) - 1)) // max(1, min(3, len(reward_list)))
        for idx, reward in enumerate(reward_list[:3]):
            x = panel[0] + 24 + idx * (pill_w + 16)
            color = tuple(reward.get("color", accent))
            icon_kind = str(reward.get("icon_kind", "currency"))
            icon_key = str(reward.get("icon_key", "souls"))
            cui.draw_reward_pill(
                img,
                (x, y, x + pill_w, y + 66),
                str(reward.get("label", "Reward")),
                str(reward.get("value", "")),
                color,
                _premium_asset(icon_kind, icon_key, 42),
            )
        y += 82

    progress_y = min(max(y + 8, H - 188), panel[3] - 142)
    draw.text((panel[0] + 28, progress_y), "PROGRESS", font=cui.get_font(21, bold=True), fill=cui.TEXT_MUTED)
    progress_label = f"{progress_value}/{max(1, progress_total)}"
    cui.draw_text_fit(draw, progress_label, (panel[2] - 150, progress_y - 4, panel[2] - 28, progress_y + 28), cui.get_font(24, bold=True), cui.TEXT_BRIGHT, 14, "right", True)
    cui.draw_progress_bar(img, (panel[0] + 26, progress_y + 40, panel[2] - 26, progress_y + 66), progress_value, max(1, progress_total), cui.GREEN)

    if footer:
        footer_box = (panel[0] + 24, panel[3] - 48, panel[2] - 24, panel[3] - 16)
        _relic_panel(img, footer_box, accent, fill=(5, 5, 10, 172), radius=8)
        cui.draw_text_fit(draw, footer, (footer_box[0] + 16, footer_box[1], footer_box[2] - 16, footer_box[3]), cui.get_font(17), cui.TEXT_MUTED, 11, "left")

    return cui.save_png(img)


def _hub_accent(screen: str) -> tuple[int, int, int]:
    return {
        "daily": cui.PURPLE,
        "weekly": cui.CYAN,
        "quests": cui.GOLD,
    }.get(str(screen), cui.PURPLE)


def _hub_save_transparent_png(img: Image.Image) -> BytesIO:
    output = BytesIO()
    img.convert("RGBA").save(output, "PNG", optimize=False, compress_level=3)
    output.seek(0)
    return output


_HUB_FONT_CACHE: dict[tuple[int, bool], ImageFont.ImageFont] = {}


def _hub_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _HUB_FONT_CACHE:
        return _HUB_FONT_CACHE[key]
    font_dir = Path("C:/Windows/Fonts")
    names = (
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "bahnschrift.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    )
    for name in names:
        for path in (font_dir / name, Path(name)):
            try:
                font = ImageFont.truetype(str(path), size)
                _HUB_FONT_CACHE[key] = font
                return font
            except OSError:
                continue
    font = ImageFont.load_default()
    _HUB_FONT_CACHE[key] = font
    return font


def _hub_text_fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    size: int,
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    *,
    bold: bool = False,
    min_size: int = 9,
    align: str = "left",
) -> None:
    label = str(text)
    x1, y1, x2, y2 = box
    max_w = max(1, x2 - x1)
    max_h = max(1, y2 - y1)
    chosen_size = size
    chosen = _hub_font(chosen_size, bold=bold)
    while chosen_size > min_size:
        bounds = draw.textbbox((0, 0), label, font=chosen)
        if bounds[2] - bounds[0] <= max_w and bounds[3] - bounds[1] <= max_h:
            break
        chosen_size -= 1
        chosen = _hub_font(chosen_size, bold=bold)
    rendered = cui.truncate_text(draw, label, max_w, chosen)
    bounds = draw.textbbox((0, 0), rendered, font=chosen)
    tw = bounds[2] - bounds[0]
    th = bounds[3] - bounds[1]
    if align == "right":
        x = x2 - tw - bounds[0]
    elif align == "center":
        x = x1 + (max_w - tw) // 2 - bounds[0]
    else:
        x = x1 - bounds[0]
    y = y1 + max(0, (max_h - th) // 2) - bounds[1]
    draw.text((x, y), rendered, font=chosen, fill=fill)


def _hub_simple_panel(
    img: Image.Image,
    box: tuple[int, int, int, int],
    accent: tuple[int, int, int],
    *,
    fill: tuple[int, int, int, int] = (38, 36, 43, 238),
    radius: int = 10,
) -> None:
    draw = ImageDraw.Draw(img)
    shadow = (box[0] + 1, box[1] + 2, box[2] + 1, box[3] + 2)
    draw.rounded_rectangle(shadow, radius=radius, fill=(0, 0, 0, 78))
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=cui.rgba(accent, 155), width=2)


def _hub_simple_progress(
    img: Image.Image,
    box: tuple[int, int, int, int],
    value: int | float,
    total: int | float,
    color: tuple[int, int, int],
) -> None:
    draw = ImageDraw.Draw(img)
    x1, y1, x2, y2 = box
    radius = max(4, (y2 - y1) // 2)
    ratio = cui.clamp(float(value) / max(1.0, float(total)))
    draw.rounded_rectangle(box, radius=radius, fill=(25, 26, 32, 235), outline=(75, 77, 86, 130), width=1)
    fill_w = int((x2 - x1) * ratio)
    if fill_w <= 0:
        return
    fill_box = (x1, y1, min(x2, x1 + fill_w), y2)
    if fill_w < (y2 - y1):
        draw.rectangle(fill_box, fill=cui.rgba(color, 236))
    else:
        draw.rounded_rectangle(fill_box, radius=radius, fill=cui.rgba(color, 236))


def _hub_reward_pill(
    img: Image.Image,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    color: tuple[int, int, int],
    icon: Image.Image | None,
) -> None:
    _hub_simple_panel(img, box, color, fill=(38, 36, 43, 238), radius=10)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    x = box[0] + 16
    if icon is not None:
        icon.thumbnail((38, 38), Image.Resampling.LANCZOS)
        img.alpha_composite(icon, (x, box[1] + (box[3] - box[1] - icon.height) // 2))
        x += 48
    if label:
        _hub_text_fit(draw, label, (x, box[1] + 8, box[2] - 12, box[1] + 28), 13, cui.TEXT_MUTED, bold=True, min_size=9)
        _hub_text_fit(draw, value, (x, box[1] + 28, box[2] - 12, box[3] - 6), 23, color, bold=True, min_size=14)
    else:
        _hub_text_fit(draw, value, (x, box[1] + 10, box[2] - 12, box[3] - 10), 26, color, bold=True, min_size=15)


@cached_render(ttl=120)
def render_hub_tasks_pillow(
    screen: str,
    rows: Iterable[dict[str, Any]],
    *,
    layout_version: int = 1,
) -> BytesIO:
    row_list = list(rows)[:7]
    W = 760
    row_h = 64
    gap = 8
    H = max(row_h, len(row_list) * row_h + max(0, len(row_list) - 1) * gap)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    accent = _hub_accent(screen)
    for idx, row in enumerate(row_list):
        y = idx * (row_h + gap)
        current = _card_int(row.get("current", 0))
        target = max(1, _card_int(row.get("target", 1), 1))
        claimed = bool(row.get("claimed", False))
        done = bool(row.get("done", current >= target))
        ready = bool(row.get("ready", current >= target and not claimed))
        color = cui.GREEN if done or claimed else (cui.GOLD if ready else accent)
        box = (2, y + 1, W - 2, y + row_h - 1)
        fill = (45, 43, 50, 232) if not done else (38, 45, 40, 232)
        _hub_simple_panel(img, box, color, fill=fill, radius=9)
        icon_kind = str(row.get("icon_kind", "ui"))
        icon_key = str(row.get("icon_key", "quest"))
        icon = _premium_asset(icon_kind, icon_key, 42)
        img.alpha_composite(icon, (box[0] + 18, box[1] + 10))
        label = str(row.get("label", "Task"))
        desc = str(row.get("desc", "")).strip()
        text_fill = cui.TEXT_MUTED if claimed else cui.TEXT_BRIGHT
        _hub_text_fit(draw, label, (box[0] + 78, box[1] + 8, box[2] - 184, box[1] + 34), 18, text_fill, bold=True, min_size=12)
        if desc:
            _hub_text_fit(draw, desc, (box[0] + 78, box[1] + 36, box[2] - 210, box[1] + 56), 13, cui.TEXT_MUTED, min_size=9)
        progress = f"{current:,}/{target:,}"
        _hub_text_fit(draw, progress, (box[2] - 154, box[1] + 8, box[2] - 34, box[1] + 32), 17, color, bold=True, min_size=11, align="right")
        _hub_simple_progress(img, (box[2] - 170, box[1] + 44, box[2] - 34, box[1] + 56), current, target, color)
    return _hub_save_transparent_png(img)


@cached_render(ttl=120)
def render_hub_rewards_pillow(
    screen: str,
    rewards: Iterable[dict[str, Any]],
    *,
    layout_version: int = 1,
) -> BytesIO:
    reward_list = list(rewards)[:4]
    W, H = 760, 78
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not reward_list:
        return _hub_save_transparent_png(img)
    gap = 10
    pill_w = (W - gap * (len(reward_list) - 1)) // max(1, len(reward_list))
    for idx, reward in enumerate(reward_list):
        x = idx * (pill_w + gap)
        color = tuple(reward.get("color", _hub_accent(screen)))
        icon_kind = str(reward.get("icon_kind", "currency"))
        icon_key = str(reward.get("icon_key", "souls"))
        _hub_reward_pill(
            img,
            (x + 1, 5, x + pill_w - 1, H - 5),
            str(reward.get("label", "Reward")),
            str(reward.get("value", "")),
            color,
            _premium_asset(icon_kind, icon_key, 42),
        )
    return _hub_save_transparent_png(img)


@cached_render(ttl=120)
def render_hub_progress_pillow(
    screen: str,
    label: str,
    value: int,
    total: int,
    *,
    footer: str = "",
    layout_version: int = 1,
) -> BytesIO:
    W, H = 760, 92
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    accent = _hub_accent(screen)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    draw.text((4, 4), str(label), font=_hub_font(17, bold=True), fill=cui.TEXT_MUTED)
    progress = f"{int(value):,}/{max(1, int(total)):,}"
    _hub_text_fit(draw, progress, (W - 150, 0, W - 4, 28), 20, cui.TEXT_BRIGHT, bold=True, min_size=13, align="right")
    _hub_simple_progress(img, (4, 38, W - 4, 58), int(value), max(1, int(total)), cui.GREEN)
    if footer:
        icon = _premium_asset("ui", "quest", 24)
        img.alpha_composite(icon, (4, 68))
        _hub_text_fit(draw, footer, (34, 66, W - 4, 90), 14, cui.TEXT_MUTED, min_size=10)
    return _hub_save_transparent_png(img)


@cached_render()
def render_arena_card(display_name, player, *, rank, last_match=None):
    W, H = 1200, 720
    img = cui.new_card(W, H, cui.ORANGE)
    draw = ImageDraw.Draw(img)
    top = cui.draw_header(img, "Arena Ledger", display_name, accent=cui.ORANGE)
    panel = (60, top + 22, W - 60, H - 84)
    cui.draw_panel(img, panel, fill=cui.PANEL, border=cui.ORANGE, radius=20)
    draw.text((panel[0] + 36, panel[1] + 34), str(rank), font=cui.get_font(54, bold=True), fill=cui.GOLD)
    rating = _card_int(_get(player, "arena_rating", 1000), 1000)
    stats = [("Rating", f"{rating:,}", cui.GOLD), ("Level", str(_get(player, "level", 1)), cui.CYAN), ("Battles", str(_get(player, "battles_won", 0)), cui.GREEN)]
    cui.draw_stat_grid(img, stats, (panel[0] + 36, panel[1] + 126, panel[2] - 36, panel[1] + 214), columns=3)
    draw.text((panel[0] + 36, panel[1] + 258), "Last Match", font=cui.get_font(26, bold=True), fill=cui.TEXT_MUTED)
    text = last_match or "No recent arena result."
    cui.draw_multiline_text_fit(draw, text, (panel[0] + 36, panel[1] + 300, panel[2] - 36, panel[3] - 52), cui.get_font(24), cui.TEXT_BRIGHT, min_size=18, max_lines=6)
    return cui.save_png(img)


def render_buffs_card(display_name: str, buff_type: str, items: list, active: dict[str, int]) -> BytesIO:
    is_sigil = buff_type == "sigils"
    accent = cui.RED if is_sigil else cui.PURPLE
    title = "Blood Sigils" if is_sigil else "Void Charms"
    W, H = 1200, 720
    img = cui.new_card(W, H, accent)
    draw = ImageDraw.Draw(img)
    top = cui.draw_header(img, title, f"{display_name} | 5 daily hunt boosters", accent=accent)
    items = list(items)[:5]
    card_w = (W - 104 - 16 * (len(items) - 1)) // max(1, len(items))
    y = top + 26
    for idx, item in enumerate(items):
        x = 52 + idx * (card_w + 16)
        color = cui.lerp_color(accent, cui.GOLD if is_sigil else cui.CYAN, idx / max(1, len(items) - 1))
        box = (x, y, x + card_w, H - 92)
        charges = _card_int(active.get(item.key, 0))
        cui.draw_panel(img, box, fill=cui.rgba(cui.lerp_color((12, 10, 20), color, 0.06), 226), border=color, radius=18, glow=charges > 0)
        cui.draw_tag(img, (box[0] + 18, box[1] + 16, box[2] - 18, box[1] + 48), f"{charges} active" if charges else "Inactive", cui.GREEN if charges else cui.TEXT_MUTED)
        icon = _premium_asset("buffs", item.key, 112)
        cui.paste_icon_3d_clipped(img, icon, ((box[0] + box[2]) // 2, box[1] + 132), 120, color, box, 18)
        cui.draw_text_fit(draw, item.name, (box[0] + 16, box[1] + 214, box[2] - 16, box[1] + 250), cui.get_font(24, bold=True), cui.TEXT_BRIGHT, 18, "center", True)
        effect = f"+{item.extra_monsters} monsters" if is_sigil else f"+{item.extra_monsters} monsters | +{int(item.rarity_bonus * 100)}% rarity"
        cui.draw_text_fit(draw, effect, (box[0] + 18, box[1] + 262, box[2] - 18, box[1] + 294), cui.get_font(19, bold=True), color, 16, "center", True)
        cui.draw_multiline_text_fit(draw, item.desc, (box[0] + 20, box[1] + 316, box[2] - 20, box[1] + 386), cui.get_font(18), cui.TEXT_MUTED, min_size=16, max_lines=3)
        price = f"{item.cost_souls:,} Souls" + (f" | {item.cost_gems:,} Gems" if item.cost_gems else "")
        cui.draw_tag(img, (box[0] + 18, box[3] - 56, box[2] - 18, box[3] - 20), price, color)
    return cui.save_png(img)


def render_profile_card(
    display_name,
    player,
    *,
    collection_count,
    weapon_name,
    xp_needed,
    active_buffs: dict[str, int] | None = None,
    profile_cosmetics: dict[str, Any] | None = None,
    avatar_bytes: bytes | None = None,
    win_streak: int = 0,
    best_streak: int = 0,
):
    W, H = 1300, 850
    cosmetics = profile_cosmetics or {}
    accent = _profile_color(cosmetics.get("accent_color"), cui.PURPLE)
    img = _relic_background(W, H, accent, scene="profile")
    draw = ImageDraw.Draw(img)
    top = _relic_header(img, "Hunter Profile", "Abyssia relic ledger", accent, right_label="Abyssia")
    left = (64, top + 28, 520, H - 60)
    right = (560, top + 28, W - 64, H - 60)
    _relic_panel(img, left, accent, fill=(9, 7, 13, 215), glow=True)
    _relic_panel(img, right, cui.lerp_color(accent, cui.GOLD, 0.16), fill=(11, 8, 14, 224))
    avatar = _profile_avatar(str(display_name), avatar_bytes, 250, accent)
    cui.paste_icon_3d_clipped(img, avatar, ((left[0] + left[2]) // 2, left[1] + 182), 260, accent, left, 8)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(
        draw,
        str(display_name),
        (left[0] + 34, left[1] + 330, left[2] - 34, left[1] + 392),
        cui.get_font(54, bold=True),
        cui.TEXT_BRIGHT,
        30,
        "center",
        True,
    )
    level = _card_int(_get(player, "level", 1), 1)
    xp = _card_int(_get(player, "xp", 0), 0)
    cui.draw_tag(img, (left[0] + 108, left[1] + 410, left[2] - 108, left[1] + 454), f"Level {level}", accent)
    xp_label = f"XP {_compact_card_num(xp)}/{_compact_card_num(xp_needed)}"
    cui.draw_progress_bar(img, (left[0] + 46, left[1] + 472, left[2] - 46, left[1] + 516), xp, max(1, xp_needed), accent, xp_label)
    weapon_icon = _premium_asset("weapons", "sword", 76)
    weapon_box = (left[0] + 42, left[3] - 132, left[2] - 42, left[3] - 30)
    _relic_panel(img, weapon_box, cui.GOLD, fill=(8, 6, 10, 214), radius=8)
    img.alpha_composite(weapon_icon, (weapon_box[0] + 24, weapon_box[1] + 14))
    draw = ImageDraw.Draw(img)
    draw.text((weapon_box[0] + 116, weapon_box[1] + 18), "FEATURED WEAPON", font=cui.get_font(22, bold=True), fill=cui.TEXT_MUTED)
    cui.draw_text_fit(
        draw,
        weapon_name or "None",
        (weapon_box[0] + 116, weapon_box[1] + 46, weapon_box[2] - 20, weapon_box[3] - 12),
        cui.get_font(34, bold=True),
        cui.GOLD,
        22,
        "left",
        True,
    )

    stats = [
        ("Souls", f"{_card_int(_get(player, 'gold', _get(player, 'souls', 0))):,}", cui.GOLD),
        ("Gems", f"{_card_int(_get(player, 'gems', 0)):,}", cui.CYAN),
        ("Collection", f"{collection_count:,}", cui.GREEN),
        ("Hunts", f"{_card_int(_get(player, 'hunts_done', 0)):,}", cui.ORANGE),
        ("Wins", f"{_card_int(_get(player, 'battles_won', 0)):,}", cui.RED),
        ("Streak", f"{win_streak} / {best_streak}", cui.PURPLE),
    ]
    stat_x = right[0] + 42
    stat_y = right[1] + 40
    stat_w = (right[2] - right[0] - 104 - 24 * 2) // 3
    for idx, (label, value, color) in enumerate(stats):
        col = idx % 3
        row = idx // 3
        x = stat_x + col * (stat_w + 24)
        y = stat_y + row * 112
        _relic_panel(img, (x, y, x + stat_w, y + 92), color, fill=(7, 6, 10, 206), radius=8)
        draw = ImageDraw.Draw(img)
        draw.text((x + 20, y + 14), label.upper(), font=cui.get_font(18, bold=True), fill=cui.TEXT_MUTED)
        cui.draw_text_fit(draw, value, (x + 20, y + 38, x + stat_w - 18, y + 78), cui.get_font(32, bold=True), color, 20, "left", True)
    about = str(cosmetics.get("about") or "Abyssia hunter")
    about_box = (right[0] + 42, right[1] + 276, right[2] - 42, right[1] + 410)
    _relic_panel(img, about_box, accent, fill=(6, 5, 9, 184), radius=8)
    draw = ImageDraw.Draw(img)
    draw.text((about_box[0] + 22, about_box[1] + 16), "PROFILE", font=cui.get_font(22, bold=True), fill=cui.TEXT_MUTED)
    cui.draw_multiline_text_fit(draw, about, (about_box[0] + 22, about_box[1] + 50, about_box[2] - 22, about_box[3] - 18), cui.get_font(26), cui.TEXT_BRIGHT, min_size=20, max_lines=2)

    draw.text((right[0] + 42, right[1] + 454), "ACTIVE RELICS", font=cui.get_font(26, bold=True), fill=cui.TEXT_MUTED)
    buffs = active_buffs or {}
    if buffs:
        x = right[0] + 42
        for key, charges in list(buffs.items())[:6]:
            icon = _premium_asset("buffs", key, 66)
            img.alpha_composite(icon, (x, right[1] + 498))
            draw.text((x + 72, right[1] + 512), f"x{charges}", font=cui.get_font(28, bold=True), fill=cui.GOLD)
            x += 132
    else:
        draw.text((right[0] + 42, right[1] + 506), "None active", font=cui.get_font(28), fill=cui.TEXT_MUTED)
    return cui.save_png(img)
