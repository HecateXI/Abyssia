from __future__ import annotations

from core.rpg import seconds_until_daily_reset, team_power
from core.rpg_data import STREAK_MILESTONES


def creature_power(creature) -> int:
    return team_power([creature])


def streak_milestone_reward(streak: int) -> tuple | None:
    for need, (name, rtype) in sorted(STREAK_MILESTONES.items(), reverse=True):
        if streak == need:
            return need, name, rtype
    return None


def daily_reset_timer() -> str:
    seconds = max(0, seconds_until_daily_reset())
    hours, rem = divmod(seconds, 3600)
    minutes, sec = divmod(rem, 60)
    return f"{hours}H {minutes}M {sec}S"
