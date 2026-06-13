from __future__ import annotations

from core.rpg import creature_xp_for_level, row_get
from core.theme import creature_label, rarity_emoji, stat_emoji, weapon_emoji


def team_slot_value(slot: int, creature, weapon) -> tuple[str, str]:
    from core.battle_engine import compute_display_stats
    name = str(row_get(creature, "name", "?") or "?")
    rarity = str(row_get(creature, "rarity", "Common") or "Common")
    level = int(row_get(creature, "level", 1) or 1)
    xp = int(row_get(creature, "xp", 0) or 0)
    xp_needed = creature_xp_for_level(level)
    stats = compute_display_stats(creature)
    header = f"[{slot}] {rarity_emoji(rarity) or ''} **{creature_label(name, rarity)}**".strip()

    hp = stats['HP']
    str_val = stats['STR']
    def_pct = stats['DEF']
    mana = stats['MANA']
    mag = stats['MAG']
    res_pct = stats['RES']

    lines = [
        f"Lvl **{level}** XP `{xp}/{xp_needed}`",
        f"{stat_emoji('hp')} `{hp:,}`  {stat_emoji('mana')} `{mana:,}`",
        f"{stat_emoji('str')} `{str_val:,}`  {stat_emoji('mag')} `{mag:,}`",
        f"{stat_emoji('def')} `{def_pct}%`  {stat_emoji('res')} `{res_pct}%`",
    ]
    if weapon:
        wtype = str(row_get(weapon, "weapon_type", "sword") or "sword")
        quality_pct = int(row_get(weapon, "quality_pct", 50) or 50)
        wid = f"{int(row_get(weapon, 'id', 0)):05d}"
        lines.append(f"`{wid}` {weapon_emoji(wtype) or ''} `{quality_pct}%`")
    else:
        lines.append("*no weapon*")
    return header, "\n".join(lines)
