from __future__ import annotations

from core.battle_engine import BattleEngine


def simulate_battle_timeline(left_team, right_team, *, max_turns: int = 30, log_enabled: bool = False) -> list[dict[str, object]]:
    return BattleEngine(left_team, right_team, max_turns=max_turns, log_enabled=log_enabled).run()


def select_battle_preview_frames(frames: list[dict[str, object]], *, max_frames: int = 5) -> list[dict[str, object]]:
    """Pick a short, evenly spaced preview while preserving the final battle state."""
    if len(frames) <= max_frames:
        return frames
    last = len(frames) - 1
    indexes = {round(i * last / (max_frames - 1)) for i in range(max_frames)}
    return [frames[i] for i in sorted(indexes)]
