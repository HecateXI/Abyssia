from __future__ import annotations

import json
from io import BytesIO
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from core import card_ui as cui
from core.content_config import ASSET_DIR, get_asset_file_path, get_creature_asset_path, safe_key
from core.rpg_data import CHARMS, RARITY_INDEX, SIGILS, ZONES, arena_rank, normalize_key


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
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "segoeuii.ttf", "arialbd.ttf" if bold else "arial.ttf",
        "ariali.ttf", "consolab.ttf" if bold else "consola.ttf",
        "courbd.ttf" if bold else "cour.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "DejaVuSans.ttf", "LiberationSans-Bold.ttf" if bold else "LiberationSans.ttf",
        "NotoSans-Bold.ttf" if bold else "NotoSans.ttf",
    )
    for n in names:
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
    s = str(text)
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
    img = Image.new("RGB", (w, h), _BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        draw.line((0, y, w, y), fill=_lerp_color(_BG_TOP, _BG_BOT, t))
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
                px = a.load()
                for y in range(a.height):
                    for x in range(a.width):
                        ca = px[x, y]
                        if ca[3]:
                            gray = int(ca[0] * 0.299 + ca[1] * 0.587 + ca[2] * 0.114)
                            gray = max(0, min(255, gray))
                            px[x, y] = (r * gray // 255, g * gray // 255, b * gray // 255, ca[3])
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
    rating = int(_get(player, "arena_rating", 1000))
    draw.text((62, 224), "Level", font=F16, fill=(229, 236, 238, 190))
    draw.text((132, 203), str(level), font=_font(54, bold=True), fill=(255, 255, 255, 245))

    rank_text = f"Rank: {arena_rank(rating)}"
    xp_text = f"XP: {xp:,}/{int(xp_needed):,}"
    bar_x, bar_y = 252, 226
    draw.text((bar_x, bar_y - 26), _fit(draw, rank_text, 260, F16), font=F16, fill=(235, 240, 242, 215))
    draw.text((bar_x + 470 - _tw(draw, xp_text, F16), bar_y - 26), xp_text, font=F16, fill=(235, 240, 242, 215))
    _profile_bar(draw, bar_x, bar_y + 2, 470, 15, xp, int(xp_needed), accent)
    draw.text((bar_x + 210, bar_y + 24), f"rating {rating:,}", font=F12, fill=(226, 232, 235, 155))

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
    draw.text((info_x + 18, streak_y), "Win Streak", font=F12, fill=(235, 240, 242, 150))
    draw.text((info_x + 110, streak_y), str(win_streak), font=F16, fill=_GOLD)
    draw.text((info_x + 110, streak_y + 22), f"Best: {best_streak}", font=F11, fill=(235, 240, 242, 165))

    footer = "b profilecustomize"
    draw.text((W - 28 - _tw(draw, footer, F11), H - 24), footer, font=F11, fill=(235, 240, 242, 128))
    return _save(img)


# ══════════════════════════════════════════════════════════════════
#  COLLECTION CARD  (POKEDEX-STYLE)
# ══════════════════════════════════════════════════════════════════
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
        ab = int(_get(w, "attack_bonus", 0))
        dbv = int(_get(w, "defense_bonus", 0))
        stat_x = cx + bw - 320
        for si, (lab, val, color) in enumerate((("STR", ab, _GOLD), ("DEF", dbv, _BLUE))):
            sx = stat_x + si * 140
            draw.rounded_rectangle((sx, cy + 28, sx + 118, cy + 95), radius=8,
                                   fill=(12, 10, 18), outline=_lerp_color(color, _BORDER, 0.35))
            draw.text((sx + 14, cy + 38), lab, font=F12, fill=_TEXT_MUTED)
            draw.text((sx + 14, cy + 58), f"+{val}", font=F24, fill=color)
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
    quality = max(0, min(150, int(quality_pct)))
    tiers = (
        (0, 10, "Common"),
        (11, 20, "Uncommon"),
        (21, 30, "Rare"),
        (31, 40, "Epic"),
        (41, 50, "Legendary"),
        (51, 60, "Mythic"),
        (61, 70, "Ancient"),
        (71, 80, "Patreon"),
        (81, 90, "Divine"),
        (91, 95, "Eldritch"),
        (96, 99, "Abyssal"),
        (100, 124, "Prismatic"),
        (125, 139, "Ethereal"),
        (140, 149, "Void Lord"),
        (150, 150, "Hidden"),
    )
    for low, high, rarity in tiers:
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
    return str(_get(row, "weapon_type", "weapon") or "weapon").replace("_", " ").title()


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

        atk = _card_int(_get(weapon, "attack_bonus", 0))
        defense = _card_int(_get(weapon, "defense_bonus", 0))
        _draw_stat_tile(img, draw, stat_x, y + 34, 112, 74, "STR", f"+{atk}", _GOLD)
        _draw_stat_tile(img, draw, stat_x + 134, y + 34, 112, 74, "DEF", f"+{defense}", _BLUE)
        draw.text((stat_x, y + 126), "Reroll: b wrr <id> stat/passive", font=F13, fill=_TEXT_MUTED)

        y += row_h + gap

    footer = f"Page {page}/{total_pages} | {len(weapons or [])} weapon(s) | b weapons <id> | b salvage <id>"
    draw.text((panel[0] + 24, H - 54), footer, font=F14, fill=_TEXT_MUTED)
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

        stat_x = hero[2] - 232
        _draw_stat_tile(img, draw, stat_x, hero[1] + 58, 96, 68, "STR", f"+{_card_int(_get(featured, 'attack_bonus', 0))}", _GOLD)
        _draw_stat_tile(img, draw, stat_x + 112, hero[1] + 58, 96, 68, "DEF", f"+{_card_int(_get(featured, 'defense_bonus', 0))}", _BLUE)
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

    footer = "Get shards by dismantling weak weapons with b salvage <weapon id> | Reroll with b wrr <id> stat/passive"
    draw.text((52, H - 56), _fit(draw, footer, W - 104, F14), font=F14, fill=_TEXT_MUTED)
    return _save(img)


# Premium Abyssia card system overrides. These final definitions intentionally
# replace the older renderers above while keeping their public signatures stable.


def _premium_draw_title(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], accent: tuple[int, int, int]) -> None:
    cui.draw_text_fit(draw, text, box, cui.get_font(34, bold=True), cui.TEXT_BRIGHT, min_size=22, align="left", bold=True)
    draw.line((box[0], box[3] - 2, min(box[2], box[0] + 260), box[3] - 2), fill=cui.rgba(accent, 170), width=2)


def _premium_asset(kind: str, key: str, size: int | tuple[int, int]) -> Image.Image:
    if isinstance(size, int):
        size = (size, size)
    return cui.load_asset_icon(kind, key, size, pixel=kind in {"creatures", "weapons", "passives"})


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
    stats = [
        ("STR", _card_int(_get(row, "attack_bonus", 0)), cui.GOLD),
        ("DEF", _card_int(_get(row, "defense_bonus", 0)), cui.BLUE),
    ]
    return [(label, f"+{value}", color) for label, value, color in stats if value != 0]


_WEAPON_VAULT_BG = ASSET_DIR / "ui" / "weapon_vault_bg_abyssia_pixel.png"
_ZOO_ARCHIVE_BG = ASSET_DIR / "ui" / "zoo_archive_bg_abyssia_pixel.png"


def _generated_bg(path, size: tuple[int, int], accent: tuple[int, int, int]) -> Image.Image:
    try:
        if path.exists():
            return cui.cover_resize(Image.open(path).convert("RGB"), size).convert("RGBA")
    except OSError:
        pass
    return cui.new_card(size[0], size[1], accent)


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
        cui.paste_icon_3d(img, icon, (x + 72, y + 72), 98, rc)
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
    footer = f"Showing {shown} of {total}" if shown < total else (f"Level ups: {levels}" if levels else "Abyssia hunt report")
    cui.draw_footer(img, footer, accent)
    return cui.save_png(img)


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
    W, H = 1200, 720
    rc = cui.rarity_color(rarity)
    img = cui.new_card(W, H, rc)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    if cui.PIXEL_CARD_BG.exists():
        try:
            bg = cui.cover_resize(Image.open(cui.PIXEL_CARD_BG), (W, H)).convert("RGBA")
            img.alpha_composite(bg)
            draw.rectangle((0, 0, W, H), fill=(0, 0, 0, 32))
        except OSError:
            pass

    title_font = cui.get_font(40, bold=True)
    sub_font = cui.get_font(19)
    draw.text((43, 29), "BESTIARY", font=title_font, fill=(0, 0, 0, 190))
    draw.text((40, 26), "BESTIARY", font=title_font, fill=cui.TEXT_BRIGHT)
    draw.text((42, 74), creature_name, font=sub_font, fill=cui.TEXT_MUTED)
    badge_w = max(94, cui.text_width(draw, rarity.upper(), cui.get_font(16, bold=True)) + 28)
    cui.draw_pixel_box(draw, (W - badge_w - 42, 33, W - 42, 63), (0, 0, 0, 112), cui.rgba(rc, 135), cut=7, width=1)
    cui.draw_text_fit(draw, rarity.upper(), (W - badge_w - 34, 33, W - 50, 63), cui.get_font(16, bold=True), rc, 11, "center", True)
    draw.rectangle((40, 100, W - 40, 102), fill=cui.rgba(rc, 120))

    left = (48, 126, 424, H - 58)
    right = (456, 126, W - 48, H - 58)

    cui.draw_generated_panel_fill(img, left, (5, 5, 10, 196), cui.rgba(rc, 170), cut=18, texture_alpha=54)
    if not cui.paste_ai_frame(img, left, cui.PIXEL_FRAME_WINDOW, rc, strength=0.14, opacity=245):
        cui.draw_pixel_box(draw, left, (0, 0, 0, 0), cui.rgba(rc, 150), cut=18, width=2)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

    portrait_box = (left[0] + 44, left[1] + 42, left[2] - 44, left[1] + 326)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rectangle((portrait_box[0] + 18, portrait_box[1] + 28, portrait_box[2] - 18, portrait_box[3] - 24), fill=cui.rgba(rc, 54))
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    img.alpha_composite(glow)
    art = _premium_asset("creatures", normalize_key(creature_name), 292)
    cui.paste_pixel_art_fit(img, art, portrait_box)

    cui.draw_text_fit(
        draw,
        creature_name,
        (left[0] + 30, left[3] - 156, left[2] - 30, left[3] - 112),
        cui.get_font(30, bold=True),
        cui.TEXT_BRIGHT,
        18,
        "center",
        True,
    )

    def simple_chip(box: tuple[int, int, int, int], label: str, color: tuple[int, int, int]) -> None:
        cui.draw_pixel_box(draw, box, cui.rgba(color, 44), cui.rgba(color, 145), cut=6, width=1)
        cui.draw_text_fit(
            draw,
            label.upper(),
            (box[0] + 8, box[1], box[2] - 8, box[3]),
            cui.get_font(15, bold=True),
            cui.lerp_color(color, cui.TEXT_BRIGHT, 0.45),
            10,
            "center",
            True,
        )

    simple_chip((left[0] + 80, left[3] - 100, left[2] - 80, left[3] - 70), rarity, rc)
    simple_chip((left[0] + 62, left[3] - 54, left[2] - 62, left[3] - 24), f"Lv.{level} | {role}", rc)

    cui.draw_generated_panel_fill(img, right, (6, 6, 12, 214), cui.rgba(rc, 145), cut=16, texture_alpha=58)
    cui.draw_pixel_box(draw, right, (0, 0, 0, 0), cui.rgba(rc, 135), cut=16, width=2)

    draw.text((right[0] + 30, right[1] + 26), "CREATURE RECORD", font=cui.get_font(27, bold=True), fill=cui.TEXT_BRIGHT)
    draw.rectangle((right[0] + 30, right[1] + 64, right[0] + 270, right[1] + 67), fill=cui.rgba(rc, 150))
    draw.text((right[0] + 30, right[1] + 92), "Ability", font=cui.get_font(18), fill=cui.TEXT_MUTED)
    cui.draw_text_fit(
        draw,
        ability,
        (right[0] + 30, right[1] + 116, right[2] - 30, right[1] + 154),
        cui.get_font(28, bold=True),
        cui.TEXT_BRIGHT,
        18,
        bold=True,
    )

    def simple_bar(box: tuple[int, int, int, int], value: int | float, maximum: int | float, color: tuple[int, int, int], label: str) -> None:
        x1, y1, x2, y2 = box
        cui.draw_pixel_box(draw, box, (4, 4, 10, 230), cui.rgba(color, 128), cut=6, width=1)
        ratio = cui.clamp(float(value) / max(1.0, float(maximum)))
        fill_w = int((x2 - x1 - 6) * ratio)
        if fill_w > 0:
            cui.draw_pixel_box(draw, (x1 + 3, y1 + 3, min(x2 - 3, x1 + 3 + fill_w), y2 - 3), cui.rgba(color, 220), None, cut=4)
        cui.draw_text_fit(draw, label, (x1 + 10, y1, x2 - 10, y2), cui.get_font(17, bold=True), cui.TEXT_BRIGHT, 11, "center", True)

    progress_label = f"XP {xp}/100" if caught else "Not yet caught"
    simple_bar((right[0] + 30, right[1] + 174, right[2] - 30, right[1] + 204), xp if caught else 0, 100, rc if caught else cui.RED, progress_label)

    stats = [
        ("HP", hp, cui.RED),
        ("STR", str_stat, cui.GOLD),
        ("DEF", pr_stat, cui.BLUE),
        ("MANA", wp_stat or mana, cui.PURPLE),
        ("MAG", mag_stat, cui.ORANGE),
        ("RES", mr_stat, cui.CYAN),
    ]
    stat_x = right[0] + 30
    stat_y = right[1] + 238
    stat_w = 188
    stat_h = 54
    for idx, (label, value, color) in enumerate(stats):
        col = idx % 3
        row = idx // 3
        sx = stat_x + col * (stat_w + 16)
        sy = stat_y + row * (stat_h + 16)
        cui.draw_pixel_box(draw, (sx, sy, sx + stat_w, sy + stat_h), (4, 4, 10, 188), cui.rgba(color, 120), cut=7, width=1)
        draw.text((sx + 14, sy + 8), label, font=cui.get_font(15, bold=True), fill=cui.TEXT_MUTED)
        draw.text((sx + 14, sy + 27), str(value), font=cui.get_font(22, bold=True), fill=color)

    rate_pct = max(0.0, catch_rate * 100)
    rate_color = cui.GREEN if rate_pct >= 30 else (cui.GOLD if rate_pct >= 1 else cui.RED)
    info_y = right[1] + 402
    draw.text((right[0] + 30, info_y), "Catch Rate", font=cui.get_font(18), fill=cui.TEXT_MUTED)
    draw.text((right[0] + 30, info_y + 24), _format_rate(rate_pct), font=cui.get_font(32, bold=True), fill=rate_color)
    simple_bar((right[0] + 230, info_y + 34, right[2] - 30, info_y + 62), max(1, int(rate_pct * 100)), 10000, rate_color, "")

    source = f"Weight {weight:g}" if weight is not None else "Weight unknown"
    status = f"Caught by {player_name}" if caught and player_name else ("Caught" if caught else "Uncaught")
    details = f"{source} | {status}"
    cui.draw_text_fit(draw, details, (right[0] + 30, right[3] - 48, right[2] - 30, right[3] - 18), cui.get_font(20, bold=True), cui.GREEN if caught else cui.RED, 14, bold=True)

    footer = "Bestiary records use fixed creature data and your caught progress."
    footer_font = cui.get_font(17)
    fw = cui.text_width(draw, footer, footer_font)
    draw.text(((W - fw) // 2, H - 32), footer, font=footer_font, fill=cui.TEXT_MUTED)
    return cui.save_png(img)


def render_weapon_detail_card(owner_name: str, weapon: Any) -> BytesIO:
    W, H = 1200, 720
    rarity = _premium_weapon_rarity(weapon)
    rc = cui.rarity_color(rarity)
    img = cui.new_card(W, H, rc)
    draw = ImageDraw.Draw(img)
    weapon_name = _premium_weapon_name(weapon)
    quality_pct = _card_int(_get(weapon, "quality_pct", 50), 50)
    quality_tier = _weapon_quality_label(quality_pct)
    quality_color = cui.rarity_color(quality_tier)
    top = cui.draw_header(
        img,
        "Weapon Relic",
        f"{owner_name} | ID #{_get(weapon, 'id', '?')}",
        right_label=f"{quality_tier.upper()} {quality_pct}%",
        accent=rc,
    )
    icon_panel = (52, top + 10, 420, H - 92)
    info_panel = (452, top + 10, W - 52, H - 92)
    cui.draw_floating_frame(img, icon_panel, rc, rc)
    icon = _premium_asset("weapons", _weapon_icon_key(weapon), 270)
    cui.paste_icon_3d(img, icon, ((icon_panel[0] + icon_panel[2]) // 2, icon_panel[1] + 220), 286, rc)
    cui.draw_rarity_badge(img, (icon_panel[0] + 72, icon_panel[3] - 112, icon_panel[2] - 72, icon_panel[3] - 72), quality_tier)
    cui.draw_tag(img, (icon_panel[0] + 100, icon_panel[3] - 58, icon_panel[2] - 100, icon_panel[3] - 20), str(_get(weapon, "wear", "Unknown")), cui.TEXT_MUTED)
    cui.draw_panel(img, info_panel, fill=cui.PANEL, border=rc, radius=18)
    cui.draw_text_fit(draw, weapon_name, (info_panel[0] + 28, info_panel[1] + 24, info_panel[2] - 28, info_panel[1] + 76), cui.get_font(44, bold=True), cui.TEXT_BRIGHT, 24, bold=True)
    meta = f"MANA {_card_int(_get(weapon, 'mana_cost', 0))} | {quality_tier} Quality {quality_pct}%"
    draw.text((info_panel[0] + 30, info_panel[1] + 86), meta, font=cui.get_font(24, bold=True), fill=quality_color)
    stats = _premium_weapon_stats(weapon)
    if stats:
        cui.draw_stat_grid(img, stats, (info_panel[0] + 30, info_panel[1] + 128, info_panel[0] + 330, info_panel[1] + 210), columns=max(1, len(stats)), hide_zero=True)
    ability = _weapon_type_label(weapon)
    draw.text((info_panel[0] + 30, info_panel[1] + 236), "Active Ability", font=cui.get_font(20), fill=cui.TEXT_MUTED)
    active_text = f"{ability} attack. Rolled values are represented by this weapon's quality, MANA cost, and stat rolls."
    cui.draw_multiline_text_fit(draw, active_text, (info_panel[0] + 30, info_panel[1] + 264, info_panel[2] - 30, info_panel[1] + 338), cui.get_font(23), cui.TEXT, min_size=18, max_lines=2)
    draw.text((info_panel[0] + 30, info_panel[1] + 366), "Passive", font=cui.get_font(20), fill=cui.TEXT_MUTED)
    passive_line = _premium_passive_summary(weapon, limit=3)
    passive_icon_x = info_panel[0] + 30
    passives = _premium_passive_items(weapon)
    if passives:
        for idx, passive in enumerate(passives[:3]):
            p_icon = _premium_asset("passives", str(passive.get("key", "")), 42)
            img.alpha_composite(p_icon, (passive_icon_x + idx * 48, info_panel[1] + 398))
        text_x = passive_icon_x + min(3, len(passives)) * 48 + 12
    else:
        text_x = passive_icon_x
    cui.draw_text_fit(draw, passive_line, (text_x, info_panel[1] + 398, info_panel[2] - 30, info_panel[1] + 438), cui.get_font(24, bold=True), cui.GOLD, 18, bold=True)
    affixes = _premium_affix_labels(weapon, limit=4)
    draw.text((info_panel[0] + 30, info_panel[1] + 444), "Affixes", font=cui.get_font(20), fill=cui.TEXT_MUTED)
    if affixes:
        for idx, label in enumerate(affixes[:4]):
            col = idx % 2
            row = idx // 2
            x = info_panel[0] + 30 + col * 324
            y = info_panel[1] + 472 + row * 30
            cui.draw_tag(img, (x, y, x + 302, y + 26), label, rc if idx == 0 else cui.TEXT_MUTED)
    else:
        draw.text((info_panel[0] + 30, info_panel[1] + 476), "None", font=cui.get_font(22), fill=cui.TEXT_MUTED)
    cui.draw_footer(img, "Only nonzero stats are shown. Values come from this weapon instance.", rc)
    return cui.save_png(img)


def render_weapons_card(display_name: str, weapons: list, *, page: int = 1, total_pages: int = 1) -> BytesIO:
    W, H = 1200, 900
    img = _generated_bg(_WEAPON_VAULT_BG, (W, H), cui.GOLD)
    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 42)))
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

    title_font = cui.get_font(38, bold=True)
    sub_font = cui.get_font(18)
    draw.text((43, 29), "WEAPON VAULT", font=title_font, fill=(0, 0, 0, 190))
    draw.text((40, 26), "WEAPON VAULT", font=title_font, fill=cui.TEXT_BRIGHT)
    draw.text((42, 74), f"{display_name} | Page {page}/{total_pages}", font=sub_font, fill=cui.TEXT_MUTED)
    _clean_pixel_panel(img, (1002, 34, 1148, 66), (0, 0, 0, 132), cui.GOLD, cut=8, shadow=False)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, "ABYSSIA", (1014, 34, 1136, 66), cui.get_font(16, bold=True), cui.GOLD, 10, "center", True)
    draw.rectangle((0, 98, W, 104), fill=cui.rgba(cui.GOLD, 132))

    page_weapons = list(weapons or [])[(max(1, page) - 1) * 4:(max(1, page) - 1) * 4 + 4]
    if not page_weapons:
        empty = (312, 312, 888, 592)
        _clean_pixel_panel(img, empty, (3, 5, 10, 162), cui.GOLD, cut=18)
        draw = ImageDraw.Draw(img)
        cui.draw_text_fit(draw, "No weapons on this page", empty, cui.get_font(34, bold=True), cui.TEXT_MUTED, 20, "center", True)
        footer = (34, H - 48, W - 34, H - 22)
        _clean_pixel_panel(img, footer, (0, 0, 0, 128), cui.GOLD, cut=9, shadow=False)
        cui.draw_text_fit(draw, f"{len(weapons or [])} weapon(s) | b weapons <id> | b salvage <id>", (footer[0] + 10, footer[1], footer[2] - 10, footer[3]), cui.get_font(16), cui.TEXT_MUTED, 11, "center")
        return cui.save_png(img)

    featured = page_weapons[0]

    def badge(box: tuple[int, int, int, int], text: str, color: tuple[int, int, int]) -> None:
        _clean_pixel_panel(img, box, cui.rgba(color, 42), color, cut=7, shadow=False)
        bd = ImageDraw.Draw(img)
        cui.draw_text_fit(bd, text, (box[0] + 8, box[1], box[2] - 8, box[3]), cui.get_font(14, bold=True), cui.lerp_color(color, cui.TEXT_BRIGHT, 0.45), 9, "center", True)

    def stat_chip(box: tuple[int, int, int, int], label: str, value: str, color: tuple[int, int, int]) -> None:
        _clean_pixel_panel(img, box, (0, 0, 0, 116), color, cut=6, shadow=False)
        sd = ImageDraw.Draw(img)
        sd.text((box[0] + 10, box[1] + 5), label, font=cui.get_font(12, bold=True), fill=cui.TEXT_MUTED)
        sd.text((box[0] + 10, box[1] + 22), value, font=cui.get_font(18, bold=True), fill=color)

    rarity = _premium_weapon_rarity(featured)
    rc = cui.rarity_color(rarity)
    quality_pct = _card_int(_get(featured, "quality_pct", 50), 50)
    quality_tier = _weapon_quality_label(quality_pct)
    quality_color = cui.rarity_color(quality_tier)
    weapon_name = _premium_weapon_name(featured)

    beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beam)
    bd.polygon(((504, 155), (696, 155), (772, 586), (428, 586)), fill=cui.rgba(rc, 28))
    bd.ellipse((442, 512, 758, 622), fill=cui.rgba(rc, 42), outline=cui.rgba(rc, 96), width=2)
    beam = beam.filter(ImageFilter.GaussianBlur(7))
    img.alpha_composite(beam)

    icon = _premium_asset("weapons", _weapon_icon_key(featured), 300)
    cui.paste_icon_3d(img, icon, (600, 382), 292, rc)
    draw = ImageDraw.Draw(img)
    draw.ellipse((448, 525, 752, 614), outline=cui.rgba(rc, 165), width=2)
    draw.ellipse((500, 542, 700, 598), outline=cui.rgba(cui.GOLD, 96), width=1)

    info = (310, 592, 890, 748)
    _clean_pixel_panel(img, info, (2, 4, 9, 172), rc, cut=14)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, weapon_name, (info[0] + 26, info[1] + 16, info[2] - 26, info[1] + 54), cui.get_font(30, bold=True), cui.TEXT_BRIGHT, 18, "center", True)
    meta = f"#{_get(featured, 'id', '?')} | Quality {quality_pct}% | MANA {_card_int(_get(featured, 'mana_cost', 0))}"
    cui.draw_text_fit(draw, meta, (info[0] + 28, info[1] + 58, info[2] - 28, info[1] + 84), cui.get_font(18, bold=True), quality_color, 12, "center", True)
    passive = _premium_passive_summary(featured, limit=2)
    cui.draw_text_fit(draw, passive, (info[0] + 26, info[1] + 92, info[2] - 26, info[1] + 122), cui.get_font(18, bold=True), cui.GOLD, 12, "center", True)
    affixes = _premium_affix_labels(featured, limit=2)
    affix_line = "Affixes: " + (" | ".join(affixes) if affixes else "None")
    cui.draw_text_fit(draw, affix_line, (info[0] + 26, info[1] + 124, info[2] - 26, info[1] + 148), cui.get_font(15), cui.TEXT_MUTED, 10, "center")
    badge((470, 152, 590, 184), quality_tier.upper(), quality_color)
    badge((610, 152, 730, 184), rarity.upper(), rc)

    stats = _premium_weapon_stats(featured)
    stat_x = 918
    stat_y = 662
    for idx, (label, value, color) in enumerate(stats[:2]):
        stat_chip((stat_x + idx * 116, stat_y, stat_x + 104 + idx * 116, stat_y + 54), label, value, color)

    def draw_side_slot(weapon: Any, box: tuple[int, int, int, int]) -> None:
        rarity = _premium_weapon_rarity(weapon)
        rc = cui.rarity_color(rarity)
        quality_pct = _card_int(_get(weapon, "quality_pct", 50), 50)
        _clean_pixel_panel(img, box, cui.rgba(cui.lerp_color((2, 5, 10), rc, 0.04), 150), rc, cut=13)
        sd = ImageDraw.Draw(img)
        icon = _premium_asset("weapons", _weapon_icon_key(weapon), 120)
        cui.paste_icon_3d(img, icon, ((box[0] + box[2]) // 2, box[1] + 88), 116, rc)
        sd = ImageDraw.Draw(img)
        name = _premium_weapon_name(weapon)
        cui.draw_text_fit(sd, name, (box[0] + 14, box[1] + 138, box[2] - 14, box[1] + 168), cui.get_font(18, bold=True), cui.TEXT_BRIGHT, 12, "center", True)
        meta = f"#{_get(weapon, 'id', '?')} | {quality_pct}% | MANA {_card_int(_get(weapon, 'mana_cost', 0))}"
        cui.draw_text_fit(sd, meta, (box[0] + 14, box[1] + 170, box[2] - 14, box[1] + 194), cui.get_font(13, bold=True), rc, 9, "center", True)
        equipped = _get(weapon, "equipped_creature_id", None)
        status_color = cui.GREEN if equipped is not None else cui.TEXT_MUTED
        status_text = "EQUIPPED" if equipped is not None else "VAULT"
        badge((box[0] + 40, box[3] - 34, box[2] - 40, box[3] - 10), status_text, status_color)

    slots = [
        (54, 178, 278, 402),
        (922, 178, 1146, 402),
        (54, 436, 278, 660),
    ]
    for weapon, box in zip(page_weapons[1:], slots):
        draw_side_slot(weapon, box)

    footer = (34, H - 48, W - 34, H - 22)
    _clean_pixel_panel(img, footer, (0, 0, 0, 134), cui.GOLD, cut=9, shadow=False)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, f"{len(weapons or [])} weapon(s) | b weapons <id> | b salvage <id>", (footer[0] + 10, footer[1], footer[2] - 10, footer[3]), cui.get_font(16), cui.TEXT_MUTED, 11, "center")
    return cui.save_png(img)


def render_crate_open_card(display_name: str, crate_name: str, result: dict, *, weapons: list = None, compact: bool = False) -> BytesIO:
    weapon_list = list(weapons or [])
    W, H = (1200, 900) if compact and len(weapon_list) > 4 else (1200, 720)
    featured = max(weapon_list, key=lambda row: _card_int(_get(row, "quality_pct", 50), 50), default=None)
    rarity = _premium_weapon_rarity(featured) if featured else "Rare"
    rc = cui.rarity_color(rarity)
    img = cui.new_card(W, H, rc)
    draw = ImageDraw.Draw(img)
    top = cui.draw_header(img, "Weapon Crate", f"{display_name} opened {crate_name}", right_label="LOOT", accent=rc)
    hero = (52, top + 8, W - 52, top + 318)
    cui.draw_panel(img, hero, fill=cui.rgba(cui.lerp_color((13, 10, 22), rc, 0.07), 232), border=rc, radius=22, glow=True)
    if featured:
        icon = _premium_asset("weapons", _weapon_icon_key(featured), 220)
        cui.paste_icon_3d(img, icon, (hero[0] + 190, hero[1] + 164), 232, rc)
        tx = hero[0] + 340
        stats_x = hero[2] - 392
        text_right = stats_x - 24
        draw.text((tx, hero[1] + 44), "Acquired Weapon", font=cui.get_font(22), fill=cui.TEXT_MUTED)
        cui.draw_text_fit(draw, _premium_weapon_name(featured), (tx, hero[1] + 78, text_right, hero[1] + 128), cui.get_font(44, bold=True), cui.TEXT_BRIGHT, 24, bold=True)
        q_pct = _card_int(_get(featured, "quality_pct", 50), 50)
        meta = f"Quality {q_pct}% | MANA {_card_int(_get(featured, 'mana_cost', 0))} | {_get(featured, 'wear', 'Unknown')}"
        draw.text((tx, hero[1] + 140), cui.truncate_text(draw, meta, text_right - tx, cui.get_font(24, bold=True)), font=cui.get_font(24, bold=True), fill=rc)
        draw.text((tx, hero[1] + 182), cui.truncate_text(draw, _premium_passive_summary(featured, limit=3), text_right - tx, cui.get_font(23, bold=True)), font=cui.get_font(23, bold=True), fill=cui.GOLD)
        affixes = _premium_affix_labels(featured, limit=3)
        affix_width = max(220, text_right - tx)
        draw.text((tx, hero[1] + 218), cui.truncate_text(draw, "Affixes: " + (" | ".join(affixes) if affixes else "None"), affix_width, cui.get_font(20)), font=cui.get_font(20), fill=cui.TEXT_MUTED)
        stats = _premium_weapon_stats(featured)
        if stats:
            cui.draw_stat_grid(img, stats, (stats_x, hero[1] + 206, hero[2] - 34, hero[1] + 286), columns=len(stats), hide_zero=True)
    else:
        cui.draw_text_fit(draw, "Crate opened", hero, cui.get_font(42, bold=True), cui.TEXT_BRIGHT, 24, "center", True)
    reward_items = _premium_reward_items(result)
    if not reward_items:
        reward_items = [("Loot", "Collected", "crate", "cache", cui.GOLD)]
    reward_y = hero[3] + 28
    reward_w = (W - 104 - 18 * 3) // 4
    for idx, (label, value, kind, key, color) in enumerate(reward_items[:4]):
        x = 52 + idx * (reward_w + 18)
        cui.draw_reward_pill(img, (x, reward_y, x + reward_w, reward_y + 78), label, value, color, _premium_asset(kind, key, 44))
    list_y = reward_y + 112
    remaining_weapons = [w for w in weapon_list if w is not featured] if featured and not compact else weapon_list
    if remaining_weapons:
        row_y = list_y + 34
        available = max(0, H - 92 - row_y)
        max_extra_rows = min(6, max(1, available // 50)) if available >= 38 else 0
        if max_extra_rows:
            draw.text((54, list_y), "Additional weapons", font=cui.get_font(22, bold=True), fill=cui.TEXT_MUTED)
            for w in remaining_weapons[:max_extra_rows]:
                rarity = _premium_weapon_rarity(w)
                row_rc = cui.rarity_color(rarity)
                row = (54, row_y, W - 54, row_y + 42)
                cui.draw_panel(img, row, fill=(10, 8, 16, 204), border=row_rc, radius=12)
                icon = _premium_asset("weapons", _weapon_icon_key(w), 32)
                img.alpha_composite(icon, (row[0] + 12, row[1] + 5))
                line = f"{_premium_weapon_name(w)} | Quality {_card_int(_get(w, 'quality_pct', 50))}% | {_premium_passive_summary(w, limit=1)}"
                draw.text((row[0] + 54, row[1] + 9), cui.truncate_text(draw, line, row[2] - row[0] - 72, cui.get_font(20)), font=cui.get_font(20), fill=cui.TEXT)
                row_y += 50
        else:
            cui.draw_tag(img, (54, list_y, W - 54, list_y + 36), f"+{len(remaining_weapons)} more weapon(s) added to vault", rc)
    cui.draw_footer(img, f"{len(weapon_list)} weapon(s) acquired" if weapon_list else "No weapon drop this time", rc)
    return cui.save_png(img)


def render_shop_card(display_name: str, deals: list, *, page: int = 1, total_pages: int = 1) -> BytesIO:
    W, H = 1200, 720
    img = cui.new_card(W, H, cui.CYAN)
    draw = ImageDraw.Draw(img)
    top = cui.draw_header(img, "Weapon Crate Shop", f"{display_name} | Weapon Shards only", accent=cui.CYAN)
    accents = {"cache": cui.CYAN, "relic": cui.GREEN, "treasure": cui.PURPLE}
    names = {"cache": "Void Cache", "relic": "Eldritch Relic", "treasure": "Abyssal Treasure"}
    card_w, card_h, gap = 340, 440, 28
    base_x = (W - card_w * 3 - gap * 2) // 2
    y = top + 28
    for idx, deal in enumerate(list(deals or [])[:3]):
        crate_key = str(deal.get("item_key") or "cache")
        accent = accents.get(crate_key, (cui.CYAN, cui.GREEN, cui.PURPLE)[idx % 3])
        box = (base_x + idx * (card_w + gap), y, base_x + idx * (card_w + gap) + card_w, y + card_h)
        cui.draw_panel(img, box, fill=cui.rgba(cui.lerp_color((13, 10, 22), accent, 0.07), 230), border=accent, radius=22, glow=True)
        icon = _premium_asset("crate", _deal_icon_key({"item_key": crate_key}), 154)
        cui.paste_icon_3d(img, icon, ((box[0] + box[2]) // 2, box[1] + 128), 166, accent)
        name = str(deal.get("item_name") or names.get(crate_key, crate_key.replace("_", " ").title()))
        cui.draw_text_fit(draw, name, (box[0] + 26, box[1] + 224, box[2] - 26, box[1] + 266), cui.get_font(30, bold=True), cui.TEXT_BRIGHT, 20, "center", True)
        desc = str(deal.get("desc") or "A sealed Abyssia weapon cache.")
        cui.draw_multiline_text_fit(draw, desc, (box[0] + 30, box[1] + 278, box[2] - 30, box[1] + 334), cui.get_font(20), cui.TEXT_MUTED, min_size=18, max_lines=2)
        rarities = str(deal.get("rarities") or "Rare+ weapons")
        cui.draw_tag(img, (box[0] + 34, box[1] + 346, box[2] - 34, box[1] + 378), rarities, accent)
        cost = _card_int(deal.get("shard_cost", 0))
        price = f"{cost:,} Shards" if cost else "Weapon Shards"
        cui.draw_reward_pill(img, (box[0] + 34, box[3] - 74, box[2] - 34, box[3] - 18), "Price", price, accent, _premium_asset("materials", "weapon_shard", 38))
    cui.draw_footer(img, "Use b shardcrate <cache|relic|treasure>. Salvage weak weapons for Weapon Shards.", cui.CYAN)
    return cui.save_png(img)


def render_team_card(display_name: str, team: Iterable[Any], *, team_power: int, weapons: dict[int, Any] | None = None) -> BytesIO:
    W, H = 1200, 720
    img = cui.new_card(W, H, cui.PURPLE)
    draw = ImageDraw.Draw(img)
    top = cui.draw_header(img, "Battle Team", f"{display_name} | Power {team_power:,}", accent=cui.PURPLE)
    members = list(team)[:3]
    card_w, card_h, gap = 350, 500, 26
    base_x = (W - card_w * 3 - gap * 2) // 2
    y = top + 28
    from core.battle_engine import compute_display_stats

    for idx, cr in enumerate(members):
        rarity = str(_get(cr, "rarity", "Common"))
        rc = cui.rarity_color(rarity)
        box = (base_x + idx * (card_w + gap), y, base_x + idx * (card_w + gap) + card_w, y + card_h)
        cui.draw_panel(img, box, fill=cui.rgba(cui.lerp_color((14, 11, 24), rc, 0.07), 226), border=rc, radius=20, glow=idx == 0)
        cui.draw_tag(img, (box[0] + 22, box[1] + 18, box[0] + 116, box[1] + 48), f"Slot {idx + 1}", rc)
        cui.draw_rarity_badge(img, (box[2] - 144, box[1] + 18, box[2] - 22, box[1] + 48), rarity)
        art = _premium_asset("creatures", normalize_key(str(_get(cr, "name", "?"))), 180)
        cui.paste_icon_3d(img, art, ((box[0] + box[2]) // 2, box[1] + 160), 190, rc)
        cui.draw_text_fit(draw, str(_get(cr, "name", "?")), (box[0] + 22, box[1] + 252, box[2] - 22, box[1] + 292), cui.get_font(28, bold=True), cui.TEXT_BRIGHT, 20, "center", True)
        draw.text((box[0] + 130, box[1] + 296), f"Lv.{_get(cr, 'level', 1)}", font=cui.get_font(22, bold=True), fill=cui.GOLD)
        stats = compute_display_stats(cr)
        stat_items = [
            ("HP", stats.get("HP", 0), cui.RED),
            ("STR", stats.get("STR", 0), cui.GOLD),
            ("DEF", stats.get("DEF", 0), cui.BLUE),
            ("MANA", stats.get("MANA", 0), cui.PURPLE),
            ("MAG", stats.get("MAG", 0), cui.ORANGE),
            ("RES", stats.get("RES", 0), cui.CYAN),
        ]
        cui.draw_stat_grid(img, stat_items, (box[0] + 22, box[1] + 324, box[2] - 22, box[1] + 432), columns=3)
        if weapons:
            w = weapons.get(_card_int(_get(cr, "id", 0)))
            if w:
                row = (box[0] + 22, box[3] - 66, box[2] - 22, box[3] - 18)
                cui.draw_panel(img, row, fill=(9, 8, 16, 220), border=cui.rarity_color(_premium_weapon_rarity(w)), radius=12)
                icon = _premium_asset("weapons", _weapon_icon_key(w), 36)
                img.alpha_composite(icon, (row[0] + 10, row[1] + 6))
                text_x = row[0] + 54
                passives = _premium_passive_items(w)
                if passives:
                    for p_idx, passive in enumerate(passives[:2]):
                        p_icon = _premium_asset("passives", str(passive.get("key", "")), 26)
                        img.alpha_composite(p_icon, (text_x + p_idx * 30, row[1] + 11))
                    text_x += min(2, len(passives)) * 30 + 8
                passive_text = _premium_passive_summary(w, limit=1).replace("Passive: ", "")
                text = f"#{_get(w, 'id', '?')}  {_premium_weapon_name(w)} | {passive_text}"
                cui.draw_text_fit(draw, text, (text_x, row[1] + 8, row[2] - 12, row[3] - 8), cui.get_font(18), cui.TEXT, 12)
    cui.draw_footer(img, "Use b team set <slot> <name> | b weaponequip <id> <creature>", cui.PURPLE)
    return cui.save_png(img)


def render_collection_card(
    display_name: str,
    entries: Iterable[dict[str, Any]],
    caught_count: int,
    total_templates: int,
    page: int,
    total_pages: int,
) -> BytesIO:
    W, H = 1200, 900
    img = _generated_bg(_ZOO_ARCHIVE_BG, (W, H), cui.CYAN)
    dim = Image.new("RGBA", (W, H), (0, 0, 0, 56))
    img.alpha_composite(dim)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

    title_font = cui.get_font(39, bold=True)
    sub_font = cui.get_font(18)
    draw.text((43, 29), "SPIRIT INDEX", font=title_font, fill=(0, 0, 0, 185))
    draw.text((40, 26), "SPIRIT INDEX", font=title_font, fill=cui.TEXT_BRIGHT)
    draw.text((42, 74), f"{display_name} | Page {page}/{total_pages}", font=sub_font, fill=cui.TEXT_MUTED)
    _clean_pixel_panel(img, (994, 34, 1148, 66), (0, 0, 0, 128), cui.CYAN, cut=8, shadow=False)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, "ABYSSIA", (1006, 34, 1136, 66), cui.get_font(16, bold=True), cui.CYAN, 10, "center", True)
    draw.rectangle((0, 98, W, 104), fill=cui.rgba(cui.CYAN, 132))

    panel = (38, 120, W - 38, H - 78)
    _clean_pixel_panel(img, panel, (5, 8, 14, 118), cui.CYAN, cut=18, shadow=True)
    draw = ImageDraw.Draw(img)
    pct = caught_count / max(1, total_templates)

    draw.text((panel[0] + 26, panel[1] + 20), f"{caught_count}/{total_templates}", font=cui.get_font(40, bold=True), fill=cui.TEXT_BRIGHT)
    draw.text((panel[0] + 204, panel[1] + 34), "spirits discovered", font=cui.get_font(22), fill=cui.TEXT_MUTED)
    bar = (panel[0] + 26, panel[1] + 78, panel[2] - 26, panel[1] + 108)
    _clean_pixel_panel(img, bar, (3, 6, 10, 198), cui.CYAN, cut=7, shadow=False)
    fill_w = int((bar[2] - bar[0] - 8) * cui.clamp(pct))
    if fill_w > 0:
        _fill_cut_box(img, (bar[0] + 4, bar[1] + 4, bar[0] + 4 + fill_w, bar[3] - 4), cui.rgba(cui.CYAN, 224), cut=5)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, f"{pct:.1%} complete", (bar[0] + 10, bar[1], bar[2] - 10, bar[3]), cui.get_font(19, bold=True), cui.TEXT_BRIGHT, 12, "center", True)

    entries_list = list(entries)[:21]
    cols, gap = 7, 12
    cell_w = (panel[2] - panel[0] - 52 - gap * (cols - 1)) // cols
    cell_h = 176
    start_x, start_y = panel[0] + 26, panel[1] + 136
    for idx, entry in enumerate(entries_list):
        col, row = idx % cols, idx // cols
        x = start_x + col * (cell_w + gap)
        y = start_y + row * (cell_h + 12)
        caught = bool(entry.get("caught"))
        rarity = str(entry.get("rarity", "Common"))
        rc = cui.rarity_color(rarity)
        box = (x, y, x + cell_w, y + cell_h)
        border = rc if caught else cui.BORDER
        fill = cui.rgba(cui.lerp_color((5, 8, 13), rc, 0.06 if caught else 0.0), 156 if caught else 178)
        _clean_pixel_panel(img, box, fill, border, cut=10, shadow=False)
        draw = ImageDraw.Draw(img)
        art = _premium_asset("creatures", normalize_key(str(entry.get("name", "?"))), 98)
        if not caught:
            art = ImageOps.grayscale(art).convert("RGBA")
            art.putalpha(120)
        cui.paste_icon_3d(img, art, ((box[0] + box[2]) // 2, box[1] + 70), 98, rc if caught else cui.BORDER)
        name = str(entry.get("name", "???")) if caught else "???"
        cui.draw_text_fit(draw, name, (box[0] + 10, box[1] + 118, box[2] - 10, box[1] + 148), cui.get_font(20, bold=True), cui.TEXT_BRIGHT if caught else cui.TEXT_MUTED, 16, "center", True)
        if caught:
            draw.text((box[0] + 14, box[1] + 158), f"x{entry.get('total', 1)}", font=cui.get_font(18), fill=cui.TEXT_MUTED)
            draw.text((box[2] - 62, box[1] + 158), f"Lv.{entry.get('max_level', 1)}", font=cui.get_font(18, bold=True), fill=cui.GOLD)

    footer = (34, H - 48, W - 34, H - 22)
    _clean_pixel_panel(img, footer, (0, 0, 0, 126), cui.CYAN, cut=9, shadow=False)
    draw = ImageDraw.Draw(img)
    cui.draw_text_fit(draw, f"Page {page}/{total_pages}", (footer[0] + 10, footer[1], footer[2] - 10, footer[3]), cui.get_font(16), cui.TEXT_MUTED, 11, "center")
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
    cui.draw_footer(img, "Autohunt rewards are aggregated from completed expedition rolls.", cui.ORANGE)
    return cui.save_png(img)


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
    cui.draw_footer(img, "Battle team uses your selected or strongest three creatures.", cui.ORANGE)
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
        cui.paste_icon_3d(img, icon, ((box[0] + box[2]) // 2, box[1] + 132), 120, color)
        cui.draw_text_fit(draw, item.name, (box[0] + 16, box[1] + 214, box[2] - 16, box[1] + 250), cui.get_font(24, bold=True), cui.TEXT_BRIGHT, 18, "center", True)
        effect = f"+{item.extra_monsters} monsters" if is_sigil else f"+{item.extra_monsters} monsters | +{int(item.rarity_bonus * 100)}% rarity"
        cui.draw_text_fit(draw, effect, (box[0] + 18, box[1] + 262, box[2] - 18, box[1] + 294), cui.get_font(19, bold=True), color, 16, "center", True)
        cui.draw_multiline_text_fit(draw, item.desc, (box[0] + 20, box[1] + 316, box[2] - 20, box[1] + 386), cui.get_font(18), cui.TEXT_MUTED, min_size=16, max_lines=3)
        price = f"{item.cost_souls:,} Souls" + (f" | {item.cost_gems:,} Gems" if item.cost_gems else "")
        cui.draw_tag(img, (box[0] + 18, box[3] - 56, box[2] - 18, box[3] - 20), price, color)
    cui.draw_footer(img, "Activate boosters before hunting to improve hunt results.", accent)
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
    W, H = 1200, 720
    cosmetics = profile_cosmetics or {}
    accent = _profile_color(cosmetics.get("accent_color"), cui.PURPLE)
    img = cui.new_card(W, H, accent)
    draw = ImageDraw.Draw(img)
    top = cui.draw_header(img, "Hunter Profile", str(display_name), accent=accent)
    left = (54, top + 18, 420, H - 86)
    right = (452, top + 18, W - 54, H - 86)
    cui.draw_panel(img, left, fill=cui.PANEL, border=accent, radius=22, glow=True)
    avatar = _profile_avatar(str(display_name), avatar_bytes, 188, accent)
    cui.paste_icon_3d(img, avatar, ((left[0] + left[2]) // 2, left[1] + 150), 196, accent)
    cui.draw_text_fit(
        draw,
        str(display_name),
        (left[0] + 28, left[1] + 270, left[2] - 28, left[1] + 316),
        cui.get_font(36, bold=True),
        cui.TEXT_BRIGHT,
        22,
        "center",
        True,
    )
    level = _card_int(_get(player, "level", 1), 1)
    xp = _card_int(_get(player, "xp", 0), 0)
    cui.draw_tag(img, (left[0] + 86, left[1] + 326, left[2] - 86, left[1] + 364), f"Level {level}", accent)
    xp_label = f"XP {_compact_card_num(xp)}/{_compact_card_num(xp_needed)}"
    cui.draw_progress_bar(img, (left[0] + 36, left[1] + 374, left[2] - 36, left[1] + 406), xp, max(1, xp_needed), accent, xp_label)
    weapon_icon = _premium_asset("weapons", "sword", 48)
    weapon_box = (left[0] + 36, left[3] - 92, left[2] - 36, left[3] - 24)
    cui.draw_panel(img, weapon_box, fill=(11, 9, 18, 222), border=cui.GOLD, radius=16)
    img.alpha_composite(weapon_icon, (weapon_box[0] + 16, weapon_box[1] + 10))
    draw.text((weapon_box[0] + 76, weapon_box[1] + 12), "FEATURED WEAPON", font=cui.get_font(18), fill=cui.TEXT_MUTED)
    cui.draw_text_fit(
        draw,
        weapon_name or "None",
        (weapon_box[0] + 76, weapon_box[1] + 34, weapon_box[2] - 14, weapon_box[3] - 8),
        cui.get_font(24, bold=True),
        cui.GOLD,
        16,
        "left",
        True,
    )
    cui.draw_panel(img, right, fill=cui.PANEL, border=accent, radius=22)
    stats = [
        ("Souls", f"{_card_int(_get(player, 'gold', _get(player, 'souls', 0))):,}", cui.GOLD),
        ("Gems", f"{_card_int(_get(player, 'gems', 0)):,}", cui.CYAN),
        ("Collection", f"{collection_count:,}", cui.GREEN),
        ("Hunts", f"{_card_int(_get(player, 'hunts_done', 0)):,}", cui.ORANGE),
        ("Wins", f"{_card_int(_get(player, 'battles_won', 0)):,}", cui.RED),
        ("Streak", f"{win_streak} / {best_streak}", cui.PURPLE),
    ]
    cui.draw_stat_grid(img, stats, (right[0] + 34, right[1] + 34, right[2] - 34, right[1] + 220), columns=3)
    about = str(cosmetics.get("about") or "Abyssia hunter")
    draw.text((right[0] + 36, right[1] + 260), "About", font=cui.get_font(26, bold=True), fill=cui.TEXT_MUTED)
    cui.draw_multiline_text_fit(draw, about, (right[0] + 36, right[1] + 300, right[2] - 36, right[1] + 390), cui.get_font(24), cui.TEXT_BRIGHT, min_size=18, max_lines=3)
    draw.text((right[0] + 36, right[1] + 430), "Active Buffs", font=cui.get_font(26, bold=True), fill=cui.TEXT_MUTED)
    buffs = active_buffs or {}
    if buffs:
        x = right[0] + 36
        for key, charges in list(buffs.items())[:6]:
            icon = _premium_asset("buffs", key, 46)
            img.alpha_composite(icon, (x, right[1] + 472))
            draw.text((x + 52, right[1] + 482), f"x{charges}", font=cui.get_font(20, bold=True), fill=cui.GOLD)
            x += 118
    else:
        draw.text((right[0] + 36, right[1] + 478), "None active", font=cui.get_font(22), fill=cui.TEXT_MUTED)
    cui.draw_footer(img, "Use b profilecustomize to personalize your profile.", accent)
    return cui.save_png(img)
