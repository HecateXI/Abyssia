from __future__ import annotations

import math
import random
from io import BytesIO
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from core import card_ui as cui
from core.rpg_data import normalize_key

W, H = 1200, 760

BOSS_THEMES: dict[str, tuple[int, int, int]] = {
    "hollow_king": (190, 202, 218),
    "mother_of_rot": (76, 196, 107),
    "void_leviathan": (79, 158, 255),
    "nameless_god": (215, 168, 75),
}

ACTION_COLORS: dict[str, tuple[int, int, int]] = {
    "strike": (235, 76, 92),
    "focus": (70, 215, 235),
    "guard": (90, 154, 255),
    "cleanse": (90, 220, 142),
    "channel": (172, 92, 245),
    "status": (215, 168, 75),
    "join": (90, 220, 142),
    "spawn": (215, 168, 75),
    "rewards": (236, 196, 82),
}


def _rgb(value: Any, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(value, tuple) and len(value) >= 3:
        return (int(value[0]), int(value[1]), int(value[2]))
    try:
        raw = int(value)
    except (TypeError, ValueError):
        return fallback
    return ((raw >> 16) & 255, (raw >> 8) & 255, raw & 255)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _pct(current: int, maximum: int) -> float:
    return max(0.0, min(1.0, current / max(1, maximum)))


def _fmt(value: int | float) -> str:
    value = int(round(value))
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 10_000:
        return f"{value / 1000:.1f}K"
    return f"{value:,}"


def _shadow_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int,
    fill: tuple[int, int, int] = cui.TEXT_BRIGHT,
    *,
    bold: bool = True,
) -> None:
    font = cui.get_font(size, bold=bold)
    x, y = xy
    draw.text((x + 3, y + 4), text, font=font, fill=(0, 0, 0, 160))
    draw.text((x, y), text, font=font, fill=fill)


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return cui.lerp_color(a, b, t)


def _arena(image: Image.Image, accent: tuple[int, int, int], seed: int) -> None:
    rng = random.Random(seed)
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    horizon = 238
    floor = [(90, 760), (520, horizon), (980, horizon), (1410, 760)]
    draw.polygon(floor, fill=(16, 14, 27, 224), outline=cui.rgba(accent, 115))
    for i in range(11):
        t = i / 10
        x_top = 520 + (980 - 520) * t
        x_bot = 90 + (1410 - 90) * t
        draw.line((x_top, horizon, x_bot, 760), fill=cui.rgba(accent, 28), width=2)
    for i in range(8):
        y = horizon + i * 66
        left = 520 - i * 54
        right = 980 + i * 54
        draw.line((left, y, right, y), fill=cui.rgba(_blend(accent, cui.TEXT_BRIGHT, 0.2), 24), width=2)
    for _ in range(34):
        x = rng.randint(220, 1280)
        y = rng.randint(250, 720)
        length = rng.randint(26, 90)
        draw.line((x, y, x + rng.randint(-80, 80), y + length), fill=cui.rgba(accent, rng.randint(22, 64)), width=1)
    draw.ellipse((475, 190, 1025, 330), fill=cui.rgba(accent, 34), outline=cui.rgba(accent, 90), width=3)
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.25)))


def _sprite_3d(
    image: Image.Image,
    kind: str,
    key: str,
    center: tuple[int, int],
    size: int,
    accent: tuple[int, int, int],
    *,
    boss: bool = False,
    opacity: int = 255,
) -> None:
    icon = cui.load_asset_icon(kind, key, (size, size), pixel=True).convert("RGBA")
    if opacity < 255:
        alpha = icon.split()[-1].point(lambda p: int(p * opacity / 255))
        icon.putalpha(alpha)
    x = center[0] - size // 2
    y = center[1] - size // 2
    shadow = Image.new("RGBA", (size + 90, size // 2 + 50), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((34, 14, shadow.width - 34, shadow.height - 18), fill=(0, 0, 0, 125 if boss else 92))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18 if boss else 12))
    image.alpha_composite(shadow, (center[0] - shadow.width // 2, center[1] + size // 3))

    glow = Image.new("RGBA", (size + 150, size + 150), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((24, 24, glow.width - 24, glow.height - 24), fill=cui.rgba(accent, 80 if boss else 48))
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(30 if boss else 20)), (center[0] - glow.width // 2, center[1] - glow.height // 2))

    rim_mask = ImageChops.subtract(
        icon.split()[-1].filter(ImageFilter.MaxFilter(13 if boss else 9)),
        icon.split()[-1],
    ).filter(ImageFilter.GaussianBlur(1.6 if boss else 1.1))
    rim = Image.new("RGBA", icon.size, cui.rgba(_blend(accent, cui.TEXT_BRIGHT, 0.28), 175 if boss else 126))
    rim.putalpha(rim_mask.point(lambda p: min(180, int(p * (0.82 if boss else 0.64)))))
    image.alpha_composite(rim, (x - (2 if boss else 1), y - (2 if boss else 1)))

    for i in range(8 if boss else 5, 0, -1):
        extrusion = Image.new("RGBA", icon.size, (0, 0, 0, 0))
        extrusion.alpha_composite(icon)
        dark = Image.new("RGBA", icon.size, (0, 0, 0, 0))
        dark.paste(cui.rgba(_blend(accent, (0, 0, 0), 0.7), 45), mask=extrusion.split()[-1])
        image.alpha_composite(dark, (x + i * 2, y + i * 3))

    mask = icon.split()[-1]
    lit_icon = Image.new("RGBA", icon.size, (0, 0, 0, 0))
    lit_icon.alpha_composite(icon)
    highlight_alpha = Image.new("L", icon.size, 0)
    hd = ImageDraw.Draw(highlight_alpha)
    hd.polygon(
        [
            (0, 0),
            (int(size * 0.72), 0),
            (int(size * 0.18), int(size * 0.68)),
            (0, int(size * 0.86)),
        ],
        fill=58 if boss else 44,
    )
    highlight_alpha = ImageChops.multiply(highlight_alpha.filter(ImageFilter.GaussianBlur(4)), mask)
    highlight = Image.new("RGBA", icon.size, (255, 255, 255, 0))
    highlight.putalpha(highlight_alpha)
    shade_alpha = Image.new("L", icon.size, 0)
    sd2 = ImageDraw.Draw(shade_alpha)
    sd2.polygon(
        [
            (int(size * 0.55), int(size * 0.18)),
            (size, int(size * 0.32)),
            (size, size),
            (int(size * 0.18), size),
        ],
        fill=52 if boss else 38,
    )
    shade_alpha = ImageChops.multiply(shade_alpha.filter(ImageFilter.GaussianBlur(5)), mask)
    shade = Image.new("RGBA", icon.size, (0, 0, 0, 0))
    shade.putalpha(shade_alpha)
    lit_icon.alpha_composite(shade)
    lit_icon.alpha_composite(highlight)
    image.alpha_composite(lit_icon, (x, y))

    ring = Image.new("RGBA", image.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse(
        (center[0] - size // 2 - 16, center[1] + size // 3 - 18, center[0] + size // 2 + 16, center[1] + size // 3 + 36),
        outline=cui.rgba(accent, 115),
        width=3,
    )
    image.alpha_composite(ring)


def _draw_boss_presence(
    image: Image.Image,
    payload: dict[str, Any],
    center: tuple[int, int],
    accent: tuple[int, int, int],
) -> None:
    boss_key = str(payload.get("boss_key", "hollow_king"))
    action = str(payload.get("action", "status"))
    defeated = bool(payload.get("defeated"))
    action_color = cui.GOLD if defeated else ACTION_COLORS.get(action, accent)
    rng = random.Random(_safe_int(payload.get("seed"), 31) + sum(accent))
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = center

    for idx, radius in enumerate((210, 278, 346)):
        alpha = 68 - idx * 12
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=cui.rgba(action_color, alpha), width=3)
    draw.ellipse((cx - 252, cy - 252, cx + 252, cy + 252), fill=cui.rgba(accent, 24))
    draw.ellipse((cx - 176, cy - 176, cx + 176, cy + 176), fill=cui.rgba(action_color, 18))

    for i in range(14):
        angle = (i / 14) * math.tau + rng.random() * 0.08
        inner = 156 + rng.randint(-8, 14)
        outer = 282 + rng.randint(-18, 24)
        x1 = cx + math.cos(angle) * inner
        y1 = cy + math.sin(angle) * inner * 0.72
        x2 = cx + math.cos(angle) * outer
        y2 = cy + math.sin(angle) * outer * 0.72
        draw.line((x1, y1, x2, y2), fill=cui.rgba(action_color, rng.randint(34, 78)), width=rng.randint(2, 4))

    for i in range(8):
        angle = (i / 8) * math.tau + rng.random() * 0.12
        x = cx + math.cos(angle) * rng.randint(160, 274)
        y = cy + math.sin(angle) * rng.randint(96, 178)
        shard = rng.randint(8, 18)
        points = [
            (x, y - shard),
            (x + shard * 0.7, y),
            (x, y + shard),
            (x - shard * 0.7, y),
        ]
        draw.polygon(points, fill=cui.rgba(_blend(action_color, cui.TEXT_BRIGHT, 0.22), rng.randint(46, 102)))

    if boss_key == "hollow_king":
        for i in range(5):
            x = cx - 118 + i * 59
            draw.polygon(
                [(x, cy - 232), (x + 28, cy - 286 - (i % 2) * 18), (x + 56, cy - 232)],
                fill=cui.rgba(cui.TEXT_BRIGHT, 34),
                outline=cui.rgba(accent, 92),
            )
    elif boss_key == "mother_of_rot":
        for _ in range(18):
            x = rng.randint(cx - 260, cx + 260)
            y = rng.randint(cy - 210, cy + 205)
            r = rng.randint(8, 24)
            draw.ellipse((x - r, y - r, x + r, y + r), outline=cui.rgba(action_color, rng.randint(34, 86)), width=2)
    elif boss_key == "void_leviathan":
        for i in range(5):
            y = cy - 174 + i * 76
            draw.arc((cx - 308, y - 52, cx + 308, y + 86), 188, 348, fill=cui.rgba(action_color, 70), width=5)
    else:
        for radius in (92, 144, 198):
            draw.arc((cx - radius * 2, cy - radius, cx + radius * 2, cy + radius), 12, 168, fill=cui.rgba(action_color, 86), width=4)
            draw.arc((cx - radius * 2, cy - radius, cx + radius * 2, cy + radius), 192, 348, fill=cui.rgba(cui.TEXT_BRIGHT, 44), width=2)

    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.35)))


def _team_members(payload: dict[str, Any]) -> list[dict[str, Any]]:
    team = payload.get("team") if isinstance(payload.get("team"), list) else []
    state = payload.get("team_state") if isinstance(payload.get("team_state"), list) else []
    by_id = {int(row.get("id", 0)): row for row in state if isinstance(row, dict)}
    result = []
    for row in team[:3]:
        if not isinstance(row, dict):
            continue
        current = by_id.get(int(row.get("id", 0)), {})
        max_hp = _safe_int(current.get("max_hp"), _safe_int(row.get("hp"), 1))
        current_hp = _safe_int(current.get("current_hp"), max_hp)
        result.append(
            {
                "id": _safe_int(row.get("id")),
                "name": str(row.get("name", "Creature")),
                "rarity": str(row.get("rarity", "Common")),
                "level": _safe_int(row.get("level"), 1),
                "current_hp": current_hp,
                "max_hp": max_hp,
                "key": normalize_key(str(row.get("name", "creature"))),
            }
        )
    return result


def _draw_team(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    positions = [(326, 462, 150), (216, 600, 126), (456, 612, 132)]
    for index, member in enumerate(_team_members(payload)):
        x, y, size = positions[index]
        alive = member["current_hp"] > 0
        opacity = 255 if alive else 120
        rarity = cui.rarity_color(member["rarity"])
        _sprite_3d(image, "creatures", member["key"], (x, y), size, rarity, opacity=opacity)
        bar = (x - 74, y + size // 2 + 54, x + 74, y + size // 2 + 76)
        cui.draw_progress_bar(
            image,
            bar,
            member["current_hp"],
            member["max_hp"],
            cui.GREEN if alive else cui.TEXT_MUTED,
            f"{_fmt(member['current_hp'])}/{_fmt(member['max_hp'])}",
        )
        name = cui.truncate_text(draw, member["name"], 150, cui.get_font(18, bold=True))
        draw.text((x - cui.text_width(draw, name, cui.get_font(18, bold=True)) // 2, bar[3] + 8), name, font=cui.get_font(18, bold=True), fill=cui.TEXT)


def _draw_boss(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    boss_key = str(payload.get("boss_key", "hollow_king"))
    hp = _safe_int(payload.get("hp"))
    max_hp = max(1, _safe_int(payload.get("max_hp"), 1))
    phase = _safe_int(payload.get("phase"), 1)
    draw = ImageDraw.Draw(image)
    _sprite_3d(image, "bosses", boss_key, (1055, 396), 310, accent, boss=True)
    title = str(payload.get("boss_name", "Incursion Boss")).upper()
    _shadow_text(draw, (748, 116), title, 46, cui.TEXT_BRIGHT)
    draw.text((752, 168), f"PHASE {phase} - {payload.get('phase_name', 'Awakening')}", font=cui.get_font(24, bold=True), fill=accent)
    cui.draw_progress_bar(image, (746, 204, 1390, 244), hp, max_hp, accent, f"BOSS HP {_fmt(hp)} / {_fmt(max_hp)}")


def _effect_lines(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    action = str(payload.get("action", "status"))
    color = ACTION_COLORS.get(action, accent)
    rng = random.Random(_safe_int(payload.get("seed"), 1) + sum(color))
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    if action == "strike":
        for _ in range(7):
            sx = rng.randint(250, 470)
            sy = rng.randint(430, 620)
            ex = rng.randint(890, 1120)
            ey = rng.randint(300, 430)
            draw.line((sx, sy, ex, ey), fill=cui.rgba(color, rng.randint(95, 170)), width=rng.randint(4, 9))
        draw.arc((884, 220, 1240, 548), 210, 315, fill=cui.rgba(cui.TEXT_BRIGHT, 170), width=11)
        draw.arc((908, 252, 1200, 510), 205, 322, fill=cui.rgba(color, 210), width=8)
    elif action == "focus":
        for radius in (135, 190, 245):
            draw.ellipse((1055 - radius, 396 - radius, 1055 + radius, 396 + radius), outline=cui.rgba(color, 125), width=4)
        for i in range(8):
            angle = i * math.tau / 8
            x = 1055 + math.cos(angle) * 245
            y = 396 + math.sin(angle) * 180
            draw.line((1055, 396, x, y), fill=cui.rgba(color, 44), width=2)
    elif action == "guard":
        for box in ((145, 360, 545, 740), (190, 410, 500, 705), (235, 460, 455, 675)):
            draw.arc(box, 120, 250, fill=cui.rgba(color, 155), width=8)
            draw.arc(box, 290, 60, fill=cui.rgba(color, 95), width=5)
    elif action == "cleanse":
        for x in (216, 326, 456):
            draw.rounded_rectangle((x - 20, 290, x + 20, 705), radius=20, fill=cui.rgba(color, 42))
            draw.ellipse((x - 70, 555, x + 70, 710), outline=cui.rgba(color, 132), width=5)
    elif action == "channel":
        for _ in range(10):
            sx = rng.randint(240, 430)
            sy = rng.randint(470, 650)
            draw.line((sx, sy, 1055 + rng.randint(-30, 30), 396 + rng.randint(-30, 30)), fill=cui.rgba(color, 132), width=6)
        draw.ellipse((928, 264, 1182, 518), outline=cui.rgba(color, 190), width=10)
    layer = layer.filter(ImageFilter.GaussianBlur(0.25 if action != "channel" else 1.2))
    image.alpha_composite(layer)


def _draw_hud(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    action = str(payload.get("action", "status"))
    action_color = ACTION_COLORS.get(action, accent)
    seconds_left = max(0, _safe_int(payload.get("seconds_left")))
    participants = _safe_int(payload.get("participants"))
    team_hp = _safe_int(payload.get("team_hp"))
    team_max_hp = max(1, _safe_int(payload.get("team_max_hp"), 1))

    cui.draw_panel(image, (46, 112, 690, 244), fill=(11, 9, 18, 214), border=accent, radius=18, glow=accent)
    draw.text((76, 134), "ABYSSAL INCURSION", font=cui.get_font(28, bold=True), fill=cui.TEXT_BRIGHT)
    draw.text((78, 174), f"Time {seconds_left // 60:02d}:{seconds_left % 60:02d}", font=cui.get_font(24, bold=True), fill=cui.GOLD)
    draw.text((284, 174), f"Hunters {participants}", font=cui.get_font(24, bold=True), fill=cui.TEXT)
    cui.draw_text_fit(
        draw,
        str(payload.get("action_label", "Status")).upper(),
        (466, 170, 654, 202),
        cui.get_font(22, bold=True),
        action_color,
        min_size=15,
        align="right",
        bold=True,
    )
    if _team_members(payload):
        cui.draw_progress_bar(
            image,
            (76, 206, 650, 232),
            team_hp,
            team_max_hp,
            cui.GREEN,
            f"YOUR TEAM {_fmt(team_hp)} / {_fmt(team_max_hp)}",
        )
    else:
        cui.draw_tag(image, (76, 206, 334, 232), "JOIN TO BIND A TEAM", action_color)
        draw.text((354, 208), "bincursion join", font=cui.get_font(20, bold=True), fill=cui.TEXT_MUTED)

    cui.draw_panel(image, (46, 704, 690, 824), fill=(11, 9, 18, 220), border=action_color, radius=18, glow=False)
    summary = str(payload.get("summary") or "Choose a tactic to shape the raid.")
    cui.draw_text_fit(
        draw,
        summary,
        (76, 720, 650, 762),
        cui.get_font(28, bold=True),
        cui.TEXT_BRIGHT,
        min_size=17,
        bold=True,
    )
    stats = [
        ("FOCUS", _safe_int(payload.get("focus")), ACTION_COLORS["focus"]),
        ("GUARD", _safe_int(payload.get("guard")), ACTION_COLORS["guard"]),
        ("WARD", _safe_int(payload.get("ward")), ACTION_COLORS["guard"]),
        ("FRACTURE", _safe_int(payload.get("fracture")), ACTION_COLORS["strike"]),
    ]
    x = 76
    for label, value, color in stats:
        cui.draw_tag(image, (x, 774, x + 132, 810), f"{label} {value}", color)
        x += 142

    cui.draw_panel(image, (746, 612, 1390, 824), fill=(11, 9, 18, 224), border=accent, radius=18, glow=False)
    draw.text((776, 638), "TOP CONTRIBUTION", font=cui.get_font(24, bold=True), fill=cui.TEXT_BRIGHT)
    top = payload.get("top") if isinstance(payload.get("top"), list) else []
    if not top:
        draw.text((776, 686), "No hunters have entered the breach.", font=cui.get_font(24), fill=cui.TEXT_MUTED)
    for index, row in enumerate(top[:4], start=1):
        y = 670 + (index - 1) * 36
        name = cui.truncate_text(draw, str(row.get("name", "Hunter")), 275, cui.get_font(22, bold=True))
        score = _fmt(_safe_int(row.get("score")))
        damage = _fmt(_safe_int(row.get("damage")))
        draw.text((776, y), f"#{index}", font=cui.get_font(22, bold=True), fill=accent)
        draw.text((826, y), name, font=cui.get_font(22, bold=True), fill=cui.TEXT)
        draw.text((1130, y), f"{score} score", font=cui.get_font(20, bold=True), fill=cui.GOLD)
        draw.text((1260, y), f"{damage} dmg", font=cui.get_font(20), fill=cui.TEXT_MUTED)

    commands = "strike  focus  guard  cleanse  channel"
    draw.text((776, 786), commands.upper(), font=cui.get_font(20, bold=True), fill=cui.TEXT_MUTED)


def _chip(
    image: Image.Image,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    color: tuple[int, int, int],
    *,
    icon_kind: str | None = None,
    icon_key: str | None = None,
) -> None:
    draw = ImageDraw.Draw(image)
    cui.draw_panel(image, box, fill=(10, 9, 17, 216), border=color, radius=10, glow=False)
    x = box[0] + 14
    if icon_kind and icon_key:
        icon = cui.load_asset_icon(icon_kind, icon_key, (34, 34), pixel=icon_kind != "bosses")
        image.alpha_composite(icon, (x, box[1] + (box[3] - box[1] - 34) // 2))
        x += 44
    draw.text((x, box[1] + 9), label.upper(), font=cui.get_font(14, bold=True), fill=cui.TEXT_MUTED)
    cui.draw_text_fit(
        draw,
        value,
        (x, box[1] + 28, box[2] - 12, box[3] - 8),
        cui.get_font(22, bold=True),
        color,
        min_size=13,
        bold=True,
    )


def _draw_compact_team_slot(
    image: Image.Image,
    box: tuple[int, int, int, int],
    member: dict[str, Any] | None,
    index: int,
    accent: tuple[int, int, int],
) -> None:
    draw = ImageDraw.Draw(image)
    if member is None:
        cui.draw_panel(image, box, fill=(9, 8, 16, 184), border=cui.BORDER, radius=10, glow=False)
        cui.draw_text_fit(
            draw,
            f"SLOT {index}",
            (box[0] + 14, box[1] + 16, box[2] - 14, box[1] + 46),
            cui.get_font(18, bold=True),
            cui.TEXT_MUTED,
            min_size=12,
            align="center",
            bold=True,
        )
        cui.draw_text_fit(
            draw,
            "JOIN RAID",
            (box[0] + 16, box[1] + 145, box[2] - 16, box[1] + 180),
            cui.get_font(22, bold=True),
            accent,
            min_size=14,
            align="center",
            bold=True,
        )
        return

    rarity = cui.rarity_color(str(member.get("rarity", "Common")))
    alive = int(member.get("current_hp", 0)) > 0
    border = rarity if alive else cui.TEXT_MUTED
    fill = cui.rgba(cui.lerp_color((12, 10, 20), border, 0.08), 226 if alive else 180)
    cui.draw_panel(image, box, fill=fill, border=border, radius=10, glow=index == 1 and alive)
    cui.draw_tag(image, (box[0] + 12, box[1] + 12, box[0] + 78, box[1] + 38), f"Slot {index}", border)
    level = str(member.get("level") or "")
    if level:
        cui.draw_tag(image, (box[2] - 78, box[1] + 12, box[2] - 12, box[1] + 38), f"Lv {level}", border)
    _sprite_3d(
        image,
        "creatures",
        str(member.get("key", "creature")),
        ((box[0] + box[2]) // 2, box[1] + 122),
        116,
        border,
        opacity=255 if alive else 95,
    )
    cui.draw_text_fit(
        draw,
        str(member.get("name", "Creature")),
        (box[0] + 14, box[1] + 202, box[2] - 14, box[1] + 232),
        cui.get_font(19, bold=True),
        cui.TEXT_BRIGHT if alive else cui.TEXT_MUTED,
        min_size=12,
        align="center",
        bold=True,
    )
    current_hp = int(member.get("current_hp", 0))
    max_hp = max(1, int(member.get("max_hp", 1)))
    cui.draw_progress_bar(
        image,
        (box[0] + 14, box[1] + 246, box[2] - 14, box[1] + 274),
        current_hp,
        max_hp,
        cui.GREEN if alive else cui.TEXT_MUTED,
        f"{_fmt(current_hp)} / {_fmt(max_hp)}",
    )


def _draw_boss_showcase(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    boss_key = str(payload.get("boss_key", "hollow_king"))
    hp = _safe_int(payload.get("hp"))
    max_hp = max(1, _safe_int(payload.get("max_hp"), 1))
    phase = max(1, _safe_int(payload.get("phase"), 1))
    defeated = bool(payload.get("defeated"))
    box = (742, 134, 1130, 522)
    cui.draw_panel(image, box, fill=(10, 9, 18, 226), border=accent, radius=12, glow=True)
    label = "DEFEATED" if defeated else f"PHASE {phase}"
    cui.draw_tag(image, (box[0] + 18, box[1] + 18, box[0] + 142, box[1] + 48), label, cui.GOLD if defeated else accent)
    phase_text = str(payload.get("phase_name", "Awakening"))
    cui.draw_text_fit(
        draw,
        phase_text.upper(),
        (box[0] + 156, box[1] + 18, box[2] - 18, box[1] + 48),
        cui.get_font(18, bold=True),
        cui.TEXT_MUTED,
        min_size=11,
        align="right",
        bold=True,
    )
    _sprite_3d(image, "bosses", boss_key, ((box[0] + box[2]) // 2, box[1] + 178), 260, accent, boss=True)
    cui.draw_text_fit(
        draw,
        str(payload.get("boss_name", "Boss")),
        (box[0] + 22, box[1] + 288, box[2] - 22, box[1] + 330),
        cui.get_font(30, bold=True),
        cui.TEXT_BRIGHT,
        min_size=18,
        align="center",
        bold=True,
    )
    cui.draw_progress_bar(
        image,
        (box[0] + 24, box[1] + 344, box[2] - 24, box[1] + 380),
        hp,
        max_hp,
        cui.GOLD if defeated else accent,
        f"{_fmt(hp)} / {_fmt(max_hp)}",
    )


def _draw_roster(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    panel = (46, 134, 714, 522)
    cui.draw_panel(image, panel, fill=(10, 9, 18, 212), border=accent, radius=12, glow=False)
    title = "BOUND TEAM"
    subtitle = "persistent HP for this bossfight"
    draw.text((panel[0] + 24, panel[1] + 20), title, font=cui.get_font(24, bold=True), fill=cui.TEXT_BRIGHT)
    draw.text((panel[0] + 190, panel[1] + 24), subtitle, font=cui.get_font(18), fill=cui.TEXT_MUTED)
    members = _team_members(payload)
    if not members:
        join_box = (panel[0] + 34, panel[1] + 84, panel[2] - 34, panel[3] - 36)
        cui.draw_panel(image, join_box, fill=(7, 6, 13, 210), border=cui.TEXT_MUTED, radius=10, glow=False)
        cui.draw_text_fit(
            draw,
            "JOIN TO BIND YOUR CURRENT TEAM",
            (join_box[0] + 24, join_box[1] + 70, join_box[2] - 24, join_box[1] + 112),
            cui.get_font(30, bold=True),
            accent,
            min_size=18,
            align="center",
            bold=True,
        )
        cui.draw_text_fit(
            draw,
            "bincursion join",
            (join_box[0] + 24, join_box[1] + 124, join_box[2] - 24, join_box[1] + 160),
            cui.get_font(24, bold=True),
            cui.TEXT_BRIGHT,
            min_size=16,
            align="center",
            bold=True,
        )
        return
    card_w = 196
    gap = 14
    x = panel[0] + 24
    for index in range(3):
        slot = (x + index * (card_w + gap), panel[1] + 72, x + index * (card_w + gap) + card_w, panel[3] - 28)
        _draw_compact_team_slot(image, slot, members[index] if index < len(members) else None, index + 1, accent)


def _draw_damage_table(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    panel = (46, 548, 714, 750)
    cui.draw_panel(image, panel, fill=(10, 9, 18, 220), border=accent, radius=12, glow=False)
    draw.text((panel[0] + 24, panel[1] + 20), "TOP DAMAGE DEALT", font=cui.get_font(24, bold=True), fill=cui.TEXT_BRIGHT)
    headings = [("Rank", 70), ("Score", 170), ("Damage", 300), ("Hunter", 438)]
    for label, x in headings:
        draw.text((panel[0] + x, panel[1] + 58), label.upper(), font=cui.get_font(13, bold=True), fill=cui.TEXT_MUTED)
    top = payload.get("top") if isinstance(payload.get("top"), list) else []
    if not top:
        draw.text((panel[0] + 24, panel[1] + 102), "No hunters have damaged the boss yet.", font=cui.get_font(22), fill=cui.TEXT_MUTED)
        return
    for idx, row in enumerate(top[:4], start=1):
        y = panel[1] + 78 + (idx - 1) * 30
        draw.rounded_rectangle((panel[0] + 22, y - 2, panel[2] - 22, y + 24), radius=6, fill=(18, 16, 28, 190), outline=cui.rgba(accent, 68))
        draw.text((panel[0] + 70, y + 2), f"{idx}", font=cui.get_font(15, bold=True), fill=accent)
        draw.text((panel[0] + 170, y + 2), _fmt(_safe_int(row.get("score"))), font=cui.get_font(15, bold=True), fill=cui.GOLD)
        draw.text((panel[0] + 300, y + 2), _fmt(_safe_int(row.get("damage"))), font=cui.get_font(15, bold=True), fill=cui.TEXT_BRIGHT)
        name = cui.truncate_text(draw, str(row.get("name", "Hunter")), 176, cui.get_font(15, bold=True))
        draw.text((panel[0] + 438, y + 2), name, font=cui.get_font(15, bold=True), fill=cui.TEXT)


def _draw_raid_state(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    panel = (742, 548, 1130, 750)
    action = str(payload.get("action", "status"))
    action_color = ACTION_COLORS.get(action, accent)
    cui.draw_panel(image, panel, fill=(10, 9, 18, 220), border=action_color, radius=12, glow=False)
    draw.text((panel[0] + 24, panel[1] + 20), "BOSS STATE", font=cui.get_font(24, bold=True), fill=cui.TEXT_BRIGHT)
    seconds_left = max(0, _safe_int(payload.get("seconds_left")))
    chips = [
        ("Time", f"{seconds_left // 60:02d}:{seconds_left % 60:02d}", cui.GOLD),
        ("Hunters", str(_safe_int(payload.get("participants"))), cui.GREEN),
        ("Focus", str(_safe_int(payload.get("focus"))), ACTION_COLORS["focus"]),
        ("Guard", str(_safe_int(payload.get("guard"))), ACTION_COLORS["guard"]),
        ("Ward", str(_safe_int(payload.get("ward"))), ACTION_COLORS["guard"]),
        ("Fracture", str(_safe_int(payload.get("fracture"))), ACTION_COLORS["strike"]),
    ]
    chip_w = 108
    for idx, (label, value, color) in enumerate(chips):
        col = idx % 3
        row = idx // 3
        x = panel[0] + 24 + col * (chip_w + 14)
        y = panel[1] + 62 + row * 58
        _chip(image, (x, y, x + chip_w, y + 48), label, value, color)


def _draw_bottom_bar(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    panel = (46, 774, 1130, 920)
    action = str(payload.get("action", "status"))
    action_color = ACTION_COLORS.get(action, accent)
    cui.draw_panel(image, panel, fill=(10, 9, 18, 224), border=action_color, radius=12, glow=False)
    summary = str(payload.get("summary") or "Coordinate tactics, protect the team, then strike.")
    cui.draw_text_fit(
        draw,
        summary,
        (panel[0] + 24, panel[1] + 18, panel[2] - 24, panel[1] + 54),
        cui.get_font(24, bold=True),
        cui.TEXT_BRIGHT,
        min_size=15,
        bold=True,
    )
    damage = _safe_int(payload.get("damage"))
    taken = _safe_int(payload.get("damage_taken"))
    healed = _safe_int(payload.get("healing"))
    if damage or taken or healed:
        data = [
            ("Damage", _fmt(damage), ACTION_COLORS["strike"], "ui", "battle"),
            ("Taken", _fmt(taken), cui.RED, "status", "bleed"),
            ("Healed", _fmt(healed), cui.GREEN, "status", "heal"),
            ("Next", str(payload.get("action_label", "Tactic")), action_color, "ui", "boss_raid"),
        ]
    elif payload.get("defeated"):
        data = [
            ("Rewards", "bincursion rewards", cui.GOLD, "crate", "treasure"),
            ("Boss", "Defeated", cui.GREEN, "bosses", str(payload.get("boss_key", "hollow_king"))),
            ("Team", "Claim split", accent, "ui", "profile"),
            ("Loot", "Score based", cui.CYAN, "materials", "weapon_shard"),
        ]
    else:
        data = [
            ("Strike", "damage", ACTION_COLORS["strike"], "ui", "battle"),
            ("Focus", "setup", ACTION_COLORS["focus"], "stats", "mag"),
            ("Guard", "protect", ACTION_COLORS["guard"], "stats", "def"),
            ("Channel", "burst", ACTION_COLORS["channel"], "ui", "boss_raid"),
        ]
    chip_w = 246
    for idx, (label, value, color, kind, key) in enumerate(data[:4]):
        x = panel[0] + 24 + idx * (chip_w + 18)
        _chip(image, (x, panel[1] + 72, x + chip_w, panel[1] + 128), label, value, color, icon_kind=kind, icon_key=key)


def _draw_battle_arena(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    scene = (46, 120, 1130, 666)
    defeated = bool(payload.get("defeated"))
    cui.draw_panel(
        image,
        scene,
        fill=(8, 7, 16, 228),
        border=cui.GOLD if defeated else accent,
        radius=16,
        glow=cui.GOLD if defeated else accent,
    )
    sx, sy, ex, ey = scene
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    rng = random.Random(_safe_int(payload.get("incursion_id"), 17) + sum(accent))

    for y in range(sy + 12, ey - 10):
        t = (y - sy) / max(1, ey - sy)
        col = _blend((4, 4, 12), _blend(accent, (9, 8, 18), 0.70), min(1.0, t * 1.2))
        draw.line((sx + 12, y, ex - 12, y), fill=(*col, 104))

    sun = _blend(accent, cui.TEXT_BRIGHT, 0.18)
    draw.ellipse((660, 42, 1254, 610), fill=cui.rgba(sun, 34), outline=cui.rgba(sun, 58), width=3)
    draw.ellipse((722, 96, 1196, 552), outline=cui.rgba(cui.TEXT_BRIGHT, 22), width=2)
    draw.rectangle((sx + 22, sy + 212, ex - 22, sy + 218), fill=cui.rgba(cui.TEXT_BRIGHT, 22))

    floor_top = sy + 278
    floor = [(sx + 52, ey - 42), (sx + 420, floor_top), (ex - 360, floor_top), (ex - 34, ey - 42)]
    draw.polygon(floor, fill=(13, 11, 24, 224), outline=cui.rgba(accent, 96))
    for i in range(13):
        t = i / 12
        x_top = sx + 420 + (ex - sx - 780) * t
        x_bot = sx + 52 + (ex - sx - 86) * t
        draw.line((x_top, floor_top, x_bot, ey - 42), fill=cui.rgba(accent, 32), width=2)
    for i in range(7):
        y = floor_top + i * 42
        inset = i * 50
        draw.line((sx + 420 - inset, y, ex - 360 + inset, y), fill=cui.rgba(cui.TEXT_BRIGHT, 20 + i * 4), width=2)

    draw.ellipse((694, sy + 286, 1052, sy + 370), fill=cui.rgba(accent, 30), outline=cui.rgba(accent, 118), width=4)
    draw.ellipse((158, sy + 362, 508, sy + 466), fill=cui.rgba(cui.BLUE, 26), outline=cui.rgba(cui.BLUE, 98), width=4)
    draw.ellipse((72, sy + 440, 310, sy + 508), fill=cui.rgba(cui.PURPLE, 24), outline=cui.rgba(cui.PURPLE, 78), width=3)
    draw.ellipse((374, sy + 444, 606, sy + 510), fill=cui.rgba(cui.CYAN, 22), outline=cui.rgba(cui.CYAN, 74), width=3)

    for _ in range(34):
        x = rng.randint(sx + 44, ex - 44)
        y = rng.randint(sy + 34, ey - 62)
        draw.ellipse((x, y, x + 2, y + 2), fill=cui.rgba(_blend(accent, cui.TEXT_BRIGHT, rng.random() * 0.7), rng.randint(38, 118)))
    for _ in range(18):
        x = rng.randint(sx + 80, ex - 120)
        y = rng.randint(sy + 40, ey - 120)
        length = rng.randint(58, 180)
        draw.line((x, y, x + rng.randint(-64, 88), y + length), fill=cui.rgba(accent, rng.randint(22, 58)), width=2)

    if defeated:
        draw.rectangle((sx + 12, sy + 12, ex - 12, ey - 12), fill=(235, 190, 76, 18))
        for radius in (170, 230, 292):
            draw.ellipse((872 - radius, 392 - radius, 872 + radius, 392 + radius), outline=cui.rgba(cui.GOLD, 62), width=3)

    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.15)))


def _small_scene_chip(
    image: Image.Image,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    color: tuple[int, int, int],
) -> None:
    draw = ImageDraw.Draw(image)
    height = box[3] - box[1]
    label_font = cui.get_font(11 if height <= 50 else 12, bold=True)
    value_font = cui.get_font(18 if height <= 50 else 20, bold=True)
    draw.rounded_rectangle(box, radius=9, fill=(8, 7, 16, 220), outline=cui.rgba(color, 205), width=2)
    draw.text((box[0] + 12, box[1] + 6), label.upper(), font=label_font, fill=cui.TEXT_MUTED)
    cui.draw_text_fit(
        draw,
        value,
        (box[0] + 8, box[1] + 22, box[2] - 8, box[3] - 4),
        value_font,
        color,
        min_size=12,
        align="center",
        bold=True,
    )


def _draw_battle_scene_sprites(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    defeated = bool(payload.get("defeated"))
    boss_key = str(payload.get("boss_key", "hollow_king"))
    boss_center = (866, 382)
    _draw_boss_presence(image, payload, boss_center, cui.GOLD if defeated else accent)
    _sprite_3d(
        image,
        "bosses",
        boss_key,
        boss_center,
        326 if not defeated else 304,
        cui.GOLD if defeated else accent,
        boss=True,
        opacity=170 if defeated else 255,
    )
    boss_name = str(payload.get("boss_name", "Boss"))
    cui.draw_text_fit(
        draw,
        boss_name,
        (boss_center[0] - 238, boss_center[1] + 178, boss_center[0] + 238, boss_center[1] + 224),
        cui.get_font(34, bold=True),
        cui.TEXT_BRIGHT,
        min_size=20,
        align="center",
        bold=True,
    )

    positions = [(316, 522, 166), (176, 586, 132), (456, 592, 138)]
    members = _team_members(payload)
    if not members:
        cui.draw_panel(image, (128, 426, 520, 574), fill=(8, 7, 16, 210), border=accent, radius=12, glow=False)
        cui.draw_text_fit(
            draw,
            "BIND YOUR TEAM TO ENTER THE FIGHT",
            (154, 464, 494, 504),
            cui.get_font(24, bold=True),
            accent,
            min_size=16,
            align="center",
            bold=True,
        )
        cui.draw_text_fit(
            draw,
            "bincursion join",
            (154, 512, 494, 546),
            cui.get_font(22, bold=True),
            cui.TEXT_BRIGHT,
            min_size=15,
            align="center",
            bold=True,
        )
        return

    for index, member in enumerate(members[:3]):
        x, y, size = positions[index]
        alive = int(member.get("current_hp", 0)) > 0
        color = cui.rarity_color(str(member.get("rarity", "Common")))
        _sprite_3d(
            image,
            "creatures",
            str(member.get("key", "creature")),
            (x, y),
            size,
            color,
            opacity=255 if alive else 100,
        )


def _draw_battle_action_fx(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    action = str(payload.get("action", "status"))
    defeated = bool(payload.get("defeated"))
    color = cui.GOLD if defeated else ACTION_COLORS.get(action, accent)
    rng = random.Random(_safe_int(payload.get("incursion_id"), 23) + sum(color))
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    team_anchor = (330, 516)
    boss_anchor = (866, 382)

    if defeated:
        draw.arc((714, 226, 1028, 536), 18, 168, fill=cui.rgba(cui.GOLD, 185), width=9)
        draw.arc((738, 250, 1002, 510), 23, 161, fill=cui.rgba(cui.TEXT_BRIGHT, 135), width=5)
        for _ in range(18):
            x = rng.randint(720, 1010)
            y = rng.randint(190, 506)
            draw.line((x, y, x + rng.randint(-18, 18), y + rng.randint(30, 86)), fill=cui.rgba(cui.GOLD, rng.randint(60, 145)), width=3)
    elif action == "strike":
        for _ in range(5):
            sx = team_anchor[0] + rng.randint(-80, 105)
            sy = team_anchor[1] + rng.randint(-42, 68)
            ex = boss_anchor[0] + rng.randint(-118, 126)
            ey = boss_anchor[1] + rng.randint(-92, 72)
            draw.line((sx, sy, ex, ey), fill=cui.rgba(color, rng.randint(95, 165)), width=rng.randint(3, 7))
        draw.arc((710, 234, 1030, 548), 204, 322, fill=cui.rgba(cui.TEXT_BRIGHT, 170), width=10)
        draw.arc((734, 258, 1002, 516), 204, 322, fill=cui.rgba(color, 220), width=7)
    elif action == "focus":
        for radius in (92, 136, 184):
            draw.ellipse(
                (team_anchor[0] - radius, team_anchor[1] - radius, team_anchor[0] + radius, team_anchor[1] + radius),
                outline=cui.rgba(color, 112),
                width=4,
            )
        for i in range(10):
            angle = i * math.tau / 10
            x = team_anchor[0] + math.cos(angle) * 210
            y = team_anchor[1] + math.sin(angle) * 130
            draw.line((team_anchor[0], team_anchor[1], x, y), fill=cui.rgba(color, 34), width=2)
    elif action == "guard":
        for box in ((128, 334, 532, 696), (174, 382, 488, 668), (224, 430, 446, 644)):
            draw.arc(box, 118, 256, fill=cui.rgba(color, 150), width=8)
            draw.arc(box, 294, 64, fill=cui.rgba(color, 86), width=5)
    elif action == "cleanse":
        for x in (176, 316, 456):
            draw.rounded_rectangle((x - 20, 348, x + 20, 650), radius=20, fill=cui.rgba(color, 42))
            draw.ellipse((x - 72, 506, x + 72, 654), outline=cui.rgba(color, 130), width=5)
    elif action == "channel":
        for _ in range(12):
            sx = team_anchor[0] + rng.randint(-118, 120)
            sy = team_anchor[1] + rng.randint(-56, 92)
            draw.line(
                (sx, sy, boss_anchor[0] + rng.randint(-38, 38), boss_anchor[1] + rng.randint(-38, 38)),
                fill=cui.rgba(color, 130),
                width=6,
            )
        draw.ellipse((732, 244, 1000, 516), outline=cui.rgba(color, 188), width=10)
    else:
        draw.line((team_anchor[0] + 80, team_anchor[1] - 10, boss_anchor[0] - 70, boss_anchor[1] + 24), fill=cui.rgba(color, 42), width=3)

    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.25 if action != "channel" else 1.0)))


def _draw_boss_battle_hud(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    defeated = bool(payload.get("defeated"))
    hp = _safe_int(payload.get("hp"))
    max_hp = max(1, _safe_int(payload.get("max_hp"), 1))
    phase = max(1, _safe_int(payload.get("phase"), 1))
    panel = (604, 132, 1110, 236)
    color = cui.GOLD if defeated else accent
    cui.draw_panel(image, panel, fill=(7, 6, 14, 226), border=color, radius=12, glow=False)
    cui.draw_text_fit(
        draw,
        str(payload.get("boss_name", "Boss")),
        (panel[0] + 24, panel[1] + 14, panel[2] - 164, panel[1] + 48),
        cui.get_font(27, bold=True),
        cui.TEXT_BRIGHT,
        min_size=16,
        bold=True,
    )
    phase_label = "DEFEATED" if defeated else f"PHASE {phase}"
    cui.draw_tag(image, (panel[2] - 148, panel[1] + 16, panel[2] - 24, panel[1] + 44), phase_label, color)
    phase_name = str(payload.get("phase_name", "Awakening"))
    cui.draw_text_fit(
        draw,
        phase_name.upper(),
        (panel[0] + 26, panel[1] + 48, panel[2] - 26, panel[1] + 70),
        cui.get_font(15, bold=True),
        cui.TEXT_MUTED,
        min_size=11,
        bold=True,
    )
    cui.draw_progress_bar(
        image,
        (panel[0] + 24, panel[1] + 72, panel[2] - 24, panel[1] + 96),
        hp,
        max_hp,
        color,
        f"{_fmt(hp)} / {_fmt(max_hp)}",
    )


def _draw_team_combined_hud(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    members = _team_members(payload)
    team_hp = _safe_int(payload.get("team_hp"))
    team_max_hp = _safe_int(payload.get("team_max_hp"), 1)
    if team_hp <= 0 and members:
        team_hp = sum(max(0, int(member.get("current_hp", 0))) for member in members)
        team_max_hp = sum(max(1, int(member.get("max_hp", 1))) for member in members)
    team_max_hp = max(1, team_max_hp)
    panel = (72, 142, 548, 212)
    title = "BOUND TEAM HP"
    cui.draw_panel(image, panel, fill=(7, 6, 14, 214), border=accent, radius=12, glow=False)
    cui.draw_text_fit(
        draw,
        title,
        (panel[0] + 18, panel[1] + 10, panel[0] + 250, panel[1] + 34),
        cui.get_font(16, bold=True),
        cui.TEXT_MUTED,
        min_size=11,
        bold=True,
    )
    if not members:
        command = "bincursion join"
        cui.draw_text_fit(
            draw,
            command,
            (panel[0] + 18, panel[1] + 34, panel[2] - 18, panel[3] - 10),
            cui.get_font(24, bold=True),
            accent,
            min_size=16,
            align="center",
            bold=True,
        )
        return
    dot_x = panel[2] - 74
    for idx, member in enumerate(members[:3]):
        color = cui.rarity_color(str(member.get("rarity", "Common")))
        fill = color if int(member.get("current_hp", 0)) > 0 else cui.TEXT_MUTED
        draw.ellipse((dot_x + idx * 20, panel[1] + 15, dot_x + idx * 20 + 10, panel[1] + 25), fill=cui.rgba(fill, 220))
    cui.draw_progress_bar(
        image,
        (panel[0] + 18, panel[1] + 38, panel[2] - 18, panel[3] - 14),
        team_hp,
        team_max_hp,
        cui.GREEN if team_hp > 0 else cui.TEXT_MUTED,
        f"{_fmt(team_hp)} / {_fmt(team_max_hp)}",
    )


def _draw_battle_status_chips(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    seconds_left = max(0, _safe_int(payload.get("seconds_left")))
    chips = [
        ("Time", f"{seconds_left // 60:02d}:{seconds_left % 60:02d}", cui.GOLD),
        ("Hunters", str(_safe_int(payload.get("participants"))), cui.GREEN),
        ("Focus", str(_safe_int(payload.get("focus"))), ACTION_COLORS["focus"]),
        ("Guard", str(_safe_int(payload.get("guard"))), ACTION_COLORS["guard"]),
    ]
    x = 74
    for label, value, color in chips:
        _small_scene_chip(image, (x, 142, x + 118, 190), label, value, color)
        x += 130
    _small_scene_chip(
        image,
        (74, 202, 192, 250),
        "Ward",
        str(_safe_int(payload.get("ward"))),
        ACTION_COLORS["guard"],
    )
    _small_scene_chip(
        image,
        (204, 202, 342, 250),
        "Fracture",
        str(_safe_int(payload.get("fracture"))),
        ACTION_COLORS["strike"],
    )
    action = str(payload.get("action_label", payload.get("action", "status"))).upper()
    _small_scene_chip(image, (354, 202, 522, 250), "Action", action, ACTION_COLORS.get(str(payload.get("action", "status")), accent))


def _draw_team_status_panel(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    panel = (46, 688, 594, 840)
    title = "BOUND TEAM"
    cui.draw_panel(image, panel, fill=(8, 7, 16, 224), border=accent, radius=12, glow=False)
    draw.text((panel[0] + 22, panel[1] + 16), title, font=cui.get_font(23, bold=True), fill=cui.TEXT_BRIGHT)
    members = _team_members(payload)
    if not members:
        cui.draw_text_fit(
            draw,
            "No team loaded for this bossfight.",
            (panel[0] + 24, panel[1] + 68, panel[2] - 24, panel[1] + 102),
            cui.get_font(22, bold=True),
            cui.TEXT_MUTED,
            min_size=15,
            align="center",
            bold=True,
        )
        return
    for idx, member in enumerate(members[:3]):
        y = panel[1] + 52 + idx * 32
        color = cui.rarity_color(str(member.get("rarity", "Common")))
        icon = cui.load_asset_icon("creatures", str(member.get("key", "creature")), (28, 28), pixel=True)
        image.alpha_composite(icon, (panel[0] + 24, y - 1))
        name = cui.truncate_text(draw, str(member.get("name", "Creature")), 170, cui.get_font(15, bold=True))
        draw.text((panel[0] + 60, y + 3), name, font=cui.get_font(15, bold=True), fill=cui.TEXT_BRIGHT)
        draw.text((panel[0] + 238, y + 4), f"Lv {member.get('level', 1)}", font=cui.get_font(14, bold=True), fill=color)
        cui.draw_progress_bar(
            image,
            (panel[0] + 294, y + 1, panel[2] - 24, y + 27),
            int(member.get("current_hp", 0)),
            max(1, int(member.get("max_hp", 1))),
            cui.GREEN if int(member.get("current_hp", 0)) > 0 else cui.TEXT_MUTED,
            f"{_fmt(int(member.get('current_hp', 0)))} / {_fmt(max(1, int(member.get('max_hp', 1))))}",
        )


def _draw_contribution_panel(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    panel = (616, 688, 1130, 840)
    cui.draw_panel(image, panel, fill=(8, 7, 16, 224), border=accent, radius=12, glow=False)
    draw.text((panel[0] + 22, panel[1] + 16), "TOP DAMAGE", font=cui.get_font(23, bold=True), fill=cui.TEXT_BRIGHT)
    top = payload.get("top") if isinstance(payload.get("top"), list) else []
    if not top:
        draw.text((panel[0] + 22, panel[1] + 68), "No hunters have damaged the boss yet.", font=cui.get_font(20), fill=cui.TEXT_MUTED)
        return
    headings = [("#", 24), ("Damage", 74), ("Score", 184), ("Hunter", 294)]
    for label, x in headings:
        draw.text((panel[0] + x, panel[1] + 52), label.upper(), font=cui.get_font(12, bold=True), fill=cui.TEXT_MUTED)
    for idx, row in enumerate(top[:4], start=1):
        y = panel[1] + 72 + (idx - 1) * 26
        fill = (18, 16, 28, 190) if idx % 2 else (12, 11, 21, 170)
        draw.rounded_rectangle((panel[0] + 18, y - 2, panel[2] - 18, y + 22), radius=6, fill=fill, outline=cui.rgba(accent, 50))
        draw.text((panel[0] + 28, y + 1), str(idx), font=cui.get_font(14, bold=True), fill=accent)
        draw.text((panel[0] + 74, y + 1), _fmt(_safe_int(row.get("damage"))), font=cui.get_font(14, bold=True), fill=cui.TEXT_BRIGHT)
        draw.text((panel[0] + 184, y + 1), _fmt(_safe_int(row.get("score"))), font=cui.get_font(14, bold=True), fill=cui.GOLD)
        name = cui.truncate_text(draw, str(row.get("name", "Hunter")), 170, cui.get_font(14, bold=True))
        draw.text((panel[0] + 294, y + 1), name, font=cui.get_font(14, bold=True), fill=cui.TEXT)


def _draw_battle_bottom_hud(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    defeated = bool(payload.get("defeated"))
    panel = (46, 858, 1130, 920)
    action = str(payload.get("action", "status"))
    action_color = cui.GOLD if defeated else ACTION_COLORS.get(action, accent)
    cui.draw_panel(image, panel, fill=(8, 7, 16, 228), border=action_color, radius=12, glow=False)
    summary = str(payload.get("summary") or "Choose a tactic and keep pressure on the boss.")
    cui.draw_text_fit(
        draw,
        summary,
        (panel[0] + 24, panel[1] + 12, panel[0] + 532, panel[3] - 12),
        cui.get_font(23, bold=True),
        cui.TEXT_BRIGHT,
        min_size=14,
        bold=True,
    )

    damage = _safe_int(payload.get("damage"))
    taken = _safe_int(payload.get("damage_taken"))
    healed = _safe_int(payload.get("healing"))
    if defeated:
        chips = [
            ("Rewards", "Claim", cui.GOLD),
            ("Boss", "Defeated", cui.GREEN),
            ("Loot", "Score based", cui.CYAN),
            ("Next", "Rewards", action_color),
        ]
    elif damage or taken or healed:
        chips = [
            ("Damage", _fmt(damage), ACTION_COLORS["strike"]),
            ("Taken", _fmt(taken), cui.RED),
            ("Healed", _fmt(healed), cui.GREEN),
            ("Next", str(payload.get("action_label", "Tactic")), action_color),
        ]
    else:
        chips = [
            ("Strike", "damage", ACTION_COLORS["strike"]),
            ("Focus", "setup", ACTION_COLORS["focus"]),
            ("Guard", "protect", ACTION_COLORS["guard"]),
            ("Channel", "burst", ACTION_COLORS["channel"]),
        ]
    chip_w = 122
    x = 590
    for label, value, color in chips:
        _small_scene_chip(image, (x, panel[1] + 8, x + chip_w, panel[3] - 8), label, value, color)
        x += chip_w + 14


def _draw_bossfight_card(image: Image.Image, payload: dict[str, Any], accent: tuple[int, int, int]) -> None:
    defeated = bool(payload.get("defeated"))
    action = str(payload.get("action", "status"))
    right_label = "DEFEATED" if defeated else str(payload.get("action_label", action.replace("_", " ").title())).upper()
    title = "Abyssal Boss Defeated" if defeated else "Abyssal Bossfight"
    subtitle = f"{payload.get('boss_name', 'Boss')} | Phase {payload.get('phase', 1)}"
    cui.draw_header(image, title, subtitle, right_label=right_label, accent=cui.GOLD if defeated else accent)
    battle_accent = cui.GOLD if defeated else accent
    _draw_battle_arena(image, payload, battle_accent)
    _draw_battle_scene_sprites(image, payload, battle_accent)
    _draw_battle_action_fx(image, payload, battle_accent)
    _draw_boss_battle_hud(image, payload, battle_accent)
    _draw_team_combined_hud(image, payload, battle_accent)
    footer = "bincursion join | strike | focus | guard | cleanse | channel | rewards"
    cui.draw_footer(image, footer, cui.GOLD if defeated else accent)


def render_incursion_scene(payload: dict[str, Any]) -> BytesIO:
    boss_key = str(payload.get("boss_key", "hollow_king"))
    accent = _rgb(payload.get("boss_color"), BOSS_THEMES.get(boss_key, BOSS_THEMES["hollow_king"]))
    image = cui.new_card(W, H, accent)
    _draw_bossfight_card(image, payload, accent)
    return cui.save_png(image)
