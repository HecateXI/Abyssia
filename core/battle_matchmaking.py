from __future__ import annotations

import random

from core.rpg import (
    ensure_arena_stats,
    ensure_player,
    find_match,
    generate_npc_team,
    load_team_snapshot,
    prepare_battle,
    team_power,
)
from core.rpg_data import arena_rank, get_npc_pool


async def get_or_make_opponent(
    db, author_id: int, guild_id: int, player_team: list
) -> tuple[str, int, list]:
    match = await find_match(db, author_id)
    if match:
        opp_id = int(match["user_id"])
        opp_player = await ensure_player(db, opp_id, "Opponent")
        opp_name = str(opp_player["hunter_name"])
        opp_team = await prepare_battle(db, opp_id)
        if opp_team:
            return opp_name, opp_id, opp_team

    # Try offline player snapshot
    offline = await db.fetchall(
        "SELECT DISTINCT user_id FROM rpg_team_snapshots WHERE user_id != ? ORDER BY RANDOM() LIMIT 5",
        (author_id,),
    )
    for row in offline:
        snap = await load_team_snapshot(db, int(row["user_id"]))
        if snap:
            opp_row = await db.fetchone(
                "SELECT hunter_name FROM rpg_players WHERE user_id = ?",
                (int(row["user_id"]),),
            )
            opp_name = str(opp_row["hunter_name"]) if opp_row else "Wandering Hunter"
            return opp_name, int(row["user_id"]), snap

    # NPC fallback
    arena = await ensure_arena_stats(db, author_id, guild_id)
    rating = int(arena["rating"])
    pool = get_npc_pool(rating)
    npc = random.choice(pool)
    npc_team = generate_npc_team(npc)
    player_power = team_power(player_team)
    npc_power = team_power(npc_team)
    scale = max(0.7, min(1.3, player_power / max(1, npc_power)))
    for c in npc_team:
        c["str_stat"] = round(int(c.get("str_stat", c.get("attack", 0))) * scale)
        c["pr_stat"] = round(int(c.get("pr_stat", c.get("defense", 0))) * scale)
        c["hp"] = round(int(c["hp"]) * scale)
        c["speed"] = round(max(1, int(c["speed"]) * scale))
        c["level"] = max(1, round(int(c["level"]) * scale))
    npc_name = f"{npc.title} {npc.name}"
    return npc_name, 0, npc_team
