from __future__ import annotations

import json as _json

import discord

from core.theme import (
    asset_emoji,
    creature_emoji,
    dark_embed,
    passive_emoji,
    rarity_emoji,
    status_effect_emoji,
    weapon_emoji,
)


def emoji_prefix(emoji: str) -> str:
    return f"{emoji} " if emoji else ""


def weapon_status(creature: dict) -> str:
    weapon = creature.get("_weapon") if isinstance(creature.get("_weapon"), dict) else None
    if not weapon:
        return ""
    rarity = str(weapon.get("rarity", "Common") or "Common")
    weapon_type = str(weapon.get("weapon_type", "sword") or "sword")
    wep = weapon_emoji(weapon_type) or weapon_type[:1].upper()
    passive_raw = weapon.get("passive")
    passive = ""
    if passive_raw:
        try:
            pdata = _json.loads(str(passive_raw)) if isinstance(passive_raw, str) else passive_raw
            if isinstance(pdata, dict) and pdata.get("key"):
                passive = f" {passive_emoji(str(pdata['key']))}" if passive_emoji(str(pdata["key"])) else ""
        except Exception:
            pass
    return f"{rarity_emoji(rarity) or rarity[0].upper()}{wep}{passive}"


def battle_team_line(creature: dict) -> str:
    level = int(creature.get("level", 1) or 1)
    name = str(creature.get("name", "?") or "?")
    rarity = str(creature.get("rarity", "Common") or "Common")
    creature_badge = creature_emoji(name, rarity) or rarity[:1].upper()
    weapon = weapon_status(creature)
    if weapon:
        return f"L.`{level}` {creature_badge} - {weapon}"
    return f"L.`{level}` {creature_badge} - no weapons"


def battle_overview_embed(
    author: discord.Member | discord.User,
    opponent_name: str,
    left_team: list,
    right_team: list,
    *,
    color: discord.Color,
    image_filename: str,
    footer: str | None = None,
    log_lines: list[str] | None = None,
) -> discord.Embed:
    embed = dark_embed(f"{author.display_name} goes into battle!", color=color)
    embed.set_author(name=f"{author.display_name} goes into battle!", icon_url=author.display_avatar.url)
    team_lines = [battle_team_line(cr) for cr in left_team]
    enemy_lines = [battle_team_line(cr) for cr in right_team]
    embed.add_field(name=f"{author.display_name}'s Team", value="\n".join(team_lines) if team_lines else "None", inline=True)
    embed.add_field(name="Enemy Team", value="\n".join(enemy_lines) if enemy_lines else "None", inline=True)
    if log_lines:
        log_text = "\n".join(log_lines[-12:])
        embed.add_field(name="Turn Log", value=f"```{log_text}```", inline=False)
    if footer:
        embed.set_footer(text=footer)
    embed.set_image(url=f"attachment://{image_filename}")
    return embed


def battle_log_line(line: str) -> str:
    lowered = line.lower()
    for key in ("bleed", "burn", "poison", "stun", "shield", "heal", "fear", "curse"):
        if key in lowered:
            return f"{emoji_prefix(status_effect_emoji(key))}{line}"
    if "crit" in lowered:
        return f"{emoji_prefix(asset_emoji('passives', 'crit'))}{line}"
    return f"{emoji_prefix(asset_emoji('ui', 'battle'))}{line}"


def outcome_badge(won: bool) -> str:
    return rarity_emoji("Legendary") if won else status_effect_emoji("bleed")


def format_battle_log(log_lines: list[str], *, max_lines: int = 20, max_chars: int = 1000) -> str:
    """Format a compact battle log for Discord embed display."""
    if not log_lines:
        return ""
    truncated_by_lines = len(log_lines) > max_lines
    display = list(log_lines[:max_lines]) if truncated_by_lines else list(log_lines)
    text = "\n".join(display)
    if len(text) > max_chars and len(display) > 1:
        while len(display) > 1 and len("\n".join(display)) > max_chars:
            display.pop()
        text = "\n".join(display)
        if len(display) < len(log_lines):
            omitted = len(log_lines) - len(display)
            text += f"\n... *{omitted} more events*"
    elif truncated_by_lines:
        text += f"\n... *{len(log_lines) - max_lines} more events*"
    return text[:1024]
