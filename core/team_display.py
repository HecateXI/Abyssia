from __future__ import annotations

import json

from core.rpg import creature_xp_for_level, row_get
from core.theme import creature_label, passive_label, rarity_emoji, stat_emoji, weapon_label


def team_slot_value(slot: int, creature, weapon) -> tuple[str, str]:
    from core.battle_engine import compute_display_stats
    name = str(row_get(creature, "name", "?") or "?")
    rarity = str(row_get(creature, "rarity", "Common") or "Common")
    level = int(row_get(creature, "level", 1) or 1)
    xp = int(row_get(creature, "xp", 0) or 0)
    xp_needed = creature_xp_for_level(level)
    stats = compute_display_stats(creature)
    header = f"[{slot}] {rarity_emoji(rarity) or ''} {creature_label(name, rarity)}".strip()

    hp = stats['HP']
    str_val = stats['STR']
    def_pct = stats['DEF']
    mana = stats['MANA']
    mag = stats['MAG']
    res_pct = stats['RES']
    hp_icon = stat_emoji("hp") or "HP"
    mana_icon = stat_emoji("mana") or "MANA"
    str_icon = stat_emoji("str") or "STR"
    mag_icon = stat_emoji("mag") or "MAG"
    def_icon = stat_emoji("def") or "DEF"
    res_icon = stat_emoji("res") or "RES"

    lines = [
        f"Lvl `{level}` XP `{xp}/{xp_needed}`",
        f"{hp_icon} `{hp:,}`  {mana_icon} `{mana:,}`",
        f"{str_icon} `{str_val:,}`  {mag_icon} `{mag:,}`",
        f"{def_icon} `{def_pct}%`  {res_icon} `{res_pct}%`",
    ]
    if weapon:
        wtype = str(row_get(weapon, "weapon_type", "sword") or "sword")
        quality_pct = int(row_get(weapon, "quality_pct", 50) or 50)
        wid = f"{int(row_get(weapon, 'id', 0)):05d}"
        passive_raw = row_get(weapon, "passive")
        passive = ""
        if passive_raw:
            try:
                pdata = json.loads(str(passive_raw)) if isinstance(passive_raw, str) else passive_raw
            except Exception:
                pdata = None
            if isinstance(pdata, dict) and pdata.get("key"):
                passive = f"  {passive_label(str(pdata['key']), chance=int(pdata.get('roll', quality_pct)), show_rarity=False)}"
        lines.append(f"`#{wid}` {weapon_label(wtype)} `{quality_pct}%`{passive}")
    else:
        lines.append("*no weapon*")
    return header, "\n".join(lines)
