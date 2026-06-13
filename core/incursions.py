from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from typing import Any

from core.battle_engine import BattleEngine, Creature
from core.database import BotDatabase
from core.rpg import (
    add_item,
    award_currency,
    award_player_xp,
    ensure_player,
    now_ts,
    prepare_battle,
    unlock_achievement,
)
from core.rpg_data import BOSSES, RARITY_BY_NAME, WEAPON_SHARD_KEY, normalize_key

ATTACK_COOLDOWN_SECONDS = 30
DEFAULT_DURATION_SECONDS = 45 * 60
SPAWN_MIN_SECONDS = 3 * 60 * 60
SPAWN_MAX_SECONDS = 6 * 60 * 60

ACTION_ALIASES = {
    "attack": "strike",
    "hit": "strike",
    "slash": "strike",
    "strike": "strike",
    "focus": "focus",
    "study": "focus",
    "guard": "guard",
    "ward": "guard",
    "cleanse": "cleanse",
    "heal": "cleanse",
    "channel": "channel",
    "ritual": "channel",
}

ACTION_COOLDOWNS = {
    "strike": 30,
    "focus": 24,
    "guard": 26,
    "cleanse": 34,
    "channel": 42,
}

ACTION_LABELS = {
    "strike": "Abyssal Strike",
    "focus": "Pattern Focus",
    "guard": "Server Ward",
    "cleanse": "Cleansing Rite",
    "channel": "Void Channel",
}


class IncursionError(ValueError):
    pass


@dataclass(frozen=True)
class IncursionBoss:
    key: str
    name: str
    title: str
    material_key: str
    level: int
    base_hp: int
    hp_scale: float
    hp_cap: int
    damage_scale: float
    duration_seconds: int
    color: int
    weight: int = 1


@dataclass(frozen=True)
class AttackOutcome:
    incursion_id: int
    boss_key: str
    boss_name: str
    damage: int
    healing: int
    damage_taken: int
    hp_before: int
    hp_after: int
    max_hp: int
    phase: int
    previous_phase: int
    defeated: bool
    wiped: bool
    team_hp: int
    team_max_hp: int
    cooldown_seconds: int
    log_lines: tuple[str, ...]
    action: str
    action_label: str
    summary: str
    focus: int
    guard: int
    ward: int
    fracture: int
    mitigation: int


@dataclass(frozen=True)
class JoinOutcome:
    incursion_id: int
    boss_key: str
    boss_name: str
    team_power: int
    hp_added: int
    hp: int
    max_hp: int
    participants: int


@dataclass(frozen=True)
class RewardBundle:
    incursion_id: int
    boss_key: str
    boss_name: str
    status: str
    rank: int
    contribution_pct: float
    gold: int
    gems: int
    xp: int
    shards: int
    material_key: str
    material_amount: int
    crate_key: str | None
    gained_levels: int


_BASE_BOSSES = {boss.key: boss for boss in BOSSES}

BOSS_CONFIGS: dict[str, IncursionBoss] = {
    "hollow_king": IncursionBoss(
        key="hollow_king",
        name=_BASE_BOSSES["hollow_king"].name,
        title=_BASE_BOSSES["hollow_king"].title,
        material_key=_BASE_BOSSES["hollow_king"].material_key,
        level=18,
        base_hp=3_250_000,
        hp_scale=80.0,
        hp_cap=60_000_000,
        damage_scale=6.75,
        duration_seconds=45 * 60,
        color=0xC8CCD7,
        weight=34,
    ),
    "mother_of_rot": IncursionBoss(
        key="mother_of_rot",
        name=_BASE_BOSSES["mother_of_rot"].name,
        title=_BASE_BOSSES["mother_of_rot"].title,
        material_key=_BASE_BOSSES["mother_of_rot"].material_key,
        level=22,
        base_hp=4_250_000,
        hp_scale=90.0,
        hp_cap=75_000_000,
        damage_scale=7.50,
        duration_seconds=50 * 60,
        color=0x4CC46B,
        weight=28,
    ),
    "void_leviathan": IncursionBoss(
        key="void_leviathan",
        name=_BASE_BOSSES["void_leviathan"].name,
        title=_BASE_BOSSES["void_leviathan"].title,
        material_key=_BASE_BOSSES["void_leviathan"].material_key,
        level=28,
        base_hp=5_500_000,
        hp_scale=105.0,
        hp_cap=100_000_000,
        damage_scale=8.25,
        duration_seconds=55 * 60,
        color=0x4F9EFF,
        weight=22,
    ),
    "nameless_god": IncursionBoss(
        key="nameless_god",
        name=_BASE_BOSSES["nameless_god"].name,
        title=_BASE_BOSSES["nameless_god"].title,
        material_key=_BASE_BOSSES["nameless_god"].material_key,
        level=35,
        base_hp=7_250_000,
        hp_scale=120.0,
        hp_cap=140_000_000,
        damage_scale=9.25,
        duration_seconds=60 * 60,
        color=0xD7A84B,
        weight=16,
    ),
}

PHASE_NAMES = {
    "hollow_king": ("Crownless Stirring", "Thronebreak", "King's Ruin"),
    "mother_of_rot": ("Spore Wake", "Rot Bloom", "Green Graves"),
    "void_leviathan": ("Deep Current", "Abyssal Surge", "World-Tide"),
    "nameless_god": ("Silent Omen", "Namebreak", "Last Prayer"),
}


def boss_config(key: str | None) -> IncursionBoss:
    if not key:
        return random_boss()
    safe = normalize_key(key)
    for boss in BOSS_CONFIGS.values():
        if safe in {boss.key, normalize_key(boss.name), normalize_key(boss.title)}:
            return boss
    known = ", ".join(boss.key for boss in BOSS_CONFIGS.values())
    raise IncursionError(f"Unknown incursion boss. Try one of: {known}.")


def random_boss() -> IncursionBoss:
    bosses = list(BOSS_CONFIGS.values())
    weights = [boss.weight for boss in bosses]
    return random.choices(bosses, weights=weights, k=1)[0]


def random_next_spawn(after_ts: int | None = None) -> int:
    base = now_ts() if after_ts is None else int(after_ts)
    return base + random.randint(SPAWN_MIN_SECONDS, SPAWN_MAX_SECONDS)


def phase_for(hp: int, max_hp: int) -> int:
    ratio = max(0.0, min(1.0, hp / max(1, max_hp)))
    if ratio > 0.66:
        return 1
    if ratio > 0.33:
        return 2
    return 3


def phase_name(boss_key: str, phase: int) -> str:
    names = PHASE_NAMES.get(boss_key, ("Awakening", "Rupture", "Enrage"))
    return names[max(1, min(3, phase)) - 1]


def hp_bar(hp: int, max_hp: int, *, width: int = 18) -> str:
    max_hp = max(1, int(max_hp))
    filled = max(0, min(width, round((max(0, hp) / max_hp) * width)))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _json_load(raw: Any, fallback: Any) -> Any:
    if raw in (None, ""):
        return fallback
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return fallback


def _json_dump(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def normalize_action(action: str | None) -> str:
    safe = normalize_key(action or "strike")
    result = ACTION_ALIASES.get(safe)
    if result is None:
        known = ", ".join(("strike", "focus", "guard", "cleanse", "channel"))
        raise IncursionError(f"Unknown incursion tactic. Try one of: {known}.")
    return result


def default_mechanics() -> dict[str, int | str]:
    return {
        "fracture": 0,
        "ward": 0,
        "instability": 0,
        "last_action": "",
        "action_count": 0,
    }


def mechanics_from_row(row: Any) -> dict[str, int | str]:
    state = default_mechanics()
    keys = set(row.keys()) if row is not None and hasattr(row, "keys") else set()
    loaded = _json_load(row["mechanics_json"] if "mechanics_json" in keys else None, {})
    if isinstance(loaded, dict):
        state.update(loaded)
    for key in ("fracture", "ward", "instability", "action_count"):
        state[key] = max(0, int(state.get(key, 0) or 0))
    state["last_action"] = str(state.get("last_action", "") or "")
    return state


def default_action_state() -> dict[str, int | str]:
    return {
        "focus": 0,
        "guard": 0,
        "last_action": "",
    }


def action_state_from_participant(participant: Any) -> dict[str, int | str]:
    state = default_action_state()
    raw = None
    keys = set(participant.keys()) if participant is not None and hasattr(participant, "keys") else set()
    if "action_state_json" in keys:
        raw = participant["action_state_json"]
    loaded = _json_load(raw, {})
    if isinstance(loaded, dict):
        state.update(loaded)
    for key in ("focus", "guard"):
        state[key] = max(0, int(state.get(key, 0) or 0))
    state["last_action"] = str(state.get("last_action", "") or "")
    return state


def _clean_statuses(statuses: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    clean: dict[str, dict[str, int]] = {}
    for key, data in statuses.items():
        if not isinstance(data, dict):
            continue
        clean[str(key)] = {
            "duration": max(0, int(data.get("duration", 0))),
            "stacks": max(0, int(data.get("stacks", 0))),
            "power": max(0, int(data.get("power", 0))),
            "order": max(0, int(data.get("order", 0))),
        }
    return {key: data for key, data in clean.items() if data["duration"] > 0 and data["stacks"] > 0}


def _creature_from_snapshot(row: dict[str, Any], side: str, index: int) -> Creature:
    return Creature.from_row(dict(row), side, index)


def initial_team_state(team: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state: list[dict[str, Any]] = []
    for index, row in enumerate(team):
        creature = _creature_from_snapshot(row, "left", index)
        state.append(
            {
                "id": creature.id,
                "name": creature.name,
                "current_hp": round(creature.current_hp),
                "max_hp": creature.max_hp,
                "current_wp": round(creature.current_wp),
                "max_wp": creature.max_wp,
                "statuses": {},
            }
        )
    return state


def apply_team_state(team: list[dict[str, Any]], state: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {int(row.get("id", 0)): row for row in state if isinstance(row, dict)}
    merged: list[dict[str, Any]] = []
    for row in team:
        current = by_id.get(int(row.get("id", 0)), {})
        hydrated = dict(row)
        if "current_hp" in current:
            hydrated["current_hp"] = int(current.get("current_hp") or 0)
        if "current_wp" in current:
            hydrated["current_wp"] = int(current.get("current_wp") or 0)
        statuses = current.get("statuses", {})
        if isinstance(statuses, dict):
            hydrated["current_statuses"] = statuses
        merged.append(hydrated)
    return merged


def state_from_creatures(creatures: list[Creature]) -> list[dict[str, Any]]:
    return [
        {
            "id": creature.id,
            "name": creature.name,
            "current_hp": max(0, round(creature.current_hp)),
            "max_hp": creature.max_hp,
            "current_wp": max(0, round(creature.current_wp)),
            "max_wp": creature.max_wp,
            "statuses": _clean_statuses(creature.statuses),
        }
        for creature in creatures
    ]


def team_state_totals(state: list[dict[str, Any]]) -> tuple[int, int]:
    hp = 0
    max_hp = 0
    for row in state:
        if not isinstance(row, dict):
            continue
        hp += max(0, int(row.get("current_hp", 0)))
        max_hp += max(0, int(row.get("max_hp", 0)))
    return hp, max_hp


def _restore_mitigated_damage(
    before_state: list[dict[str, Any]],
    after_state: list[dict[str, Any]],
    amount: int,
) -> tuple[list[dict[str, Any]], int]:
    if amount <= 0:
        return after_state, 0
    before_by_id = {int(row.get("id", 0)): row for row in before_state if isinstance(row, dict)}
    damage_windows: list[tuple[dict[str, Any], int]] = []
    total_window = 0
    for row in after_state:
        if not isinstance(row, dict):
            continue
        before = before_by_id.get(int(row.get("id", 0)), {})
        lost = max(0, int(before.get("current_hp", 0)) - int(row.get("current_hp", 0)))
        if lost:
            damage_windows.append((row, lost))
            total_window += lost
    if total_window <= 0:
        return after_state, 0
    remaining = min(amount, total_window)
    restored = 0
    for index, (row, lost) in enumerate(damage_windows):
        if remaining <= 0:
            break
        share = remaining if index == len(damage_windows) - 1 else max(1, round(amount * (lost / total_window)))
        restore = min(lost, remaining, share)
        row["current_hp"] = int(row.get("current_hp", 0)) + restore
        remaining -= restore
        restored += restore
    return after_state, restored


def _heal_team_state(
    state: list[dict[str, Any]],
    pct: float,
    *,
    flat: int = 0,
    remove_statuses: bool = False,
) -> tuple[list[dict[str, Any]], int, int]:
    healed = 0
    removed = 0
    for row in state:
        if not isinstance(row, dict):
            continue
        current_hp = max(0, int(row.get("current_hp", 0)))
        max_hp = max(1, int(row.get("max_hp", 1)))
        if current_hp <= 0:
            continue
        heal = max(0, round(max_hp * pct) + flat)
        new_hp = min(max_hp, current_hp + heal)
        healed += max(0, new_hp - current_hp)
        row["current_hp"] = new_hp
        if remove_statuses:
            statuses = row.get("statuses", {})
            if isinstance(statuses, dict):
                removed += len(statuses)
                row["statuses"] = {}
    return state, healed, removed


def _sacrifice_team_state(state: list[dict[str, Any]], pct: float) -> tuple[list[dict[str, Any]], int]:
    taken = 0
    for row in state:
        if not isinstance(row, dict):
            continue
        current_hp = max(0, int(row.get("current_hp", 0)))
        max_hp = max(1, int(row.get("max_hp", 1)))
        if current_hp <= 1:
            continue
        loss = min(current_hp - 1, max(1, round(max_hp * pct)))
        row["current_hp"] = current_hp - loss
        taken += loss
    return state, taken


def _boss_pressure_state(
    state: list[dict[str, Any]],
    boss: IncursionBoss,
    phase: int,
    action: str,
    *,
    ward: int,
    guard: int,
    seconds_left: int,
) -> tuple[list[dict[str, Any]], int, int]:
    phase_pct = {1: 0.050, 2: 0.072, 3: 0.096}.get(phase, 0.060)
    action_mult = {
        "focus": 1.00,
        "guard": 0.52,
        "cleanse": 0.72,
        "channel": 0.38,
    }.get(action, 1.0)
    enrage = 1.35 if seconds_left <= 5 * 60 else 1.0
    mitigation_rate = min(0.72, ward * 0.045 + guard * 0.14 + (0.18 if action == "guard" else 0.0))
    pct = phase_pct * boss.damage_scale * action_mult * enrage * (1.0 - mitigation_rate)
    taken = 0
    mitigated = 0
    for row in state:
        if not isinstance(row, dict):
            continue
        current_hp = max(0, int(row.get("current_hp", 0)))
        max_hp = max(1, int(row.get("max_hp", 1)))
        if current_hp <= 0:
            continue
        raw = max(1, round(max_hp * phase_pct * boss.damage_scale * action_mult * enrage))
        loss = min(current_hp, max(1, round(max_hp * pct)))
        row["current_hp"] = current_hp - loss
        taken += loss
        mitigated += max(0, raw - loss)
    return state, taken, mitigated


def calculate_team_power(team: list[dict[str, Any]]) -> int:
    total = 0.0
    for index, row in enumerate(team):
        creature = _creature_from_snapshot(row, "left", index)
        rarity = RARITY_BY_NAME.get(creature.rarity)
        rarity_bonus = 1.0 + ((rarity.stat_multiplier - 1.0) * 0.35 if rarity else 0.0)
        creature_score = (
            creature.max_hp * 0.38
            + creature.strength * 2.35
            + creature.magic * 2.15
            + creature.max_wp * 0.24
            + (creature.pr + creature.mr) * 1250
            + creature.speed * 10
            + creature.level * 65
            + creature.crit * 16
        )
        weapon = row.get("_weapon")
        if isinstance(weapon, dict):
            quality_pct = int(weapon.get("quality_pct", 50) or 50)
            creature_score += quality_pct * 18
            creature_score += int(weapon.get("attack_bonus", 0) or 0) * 12
            creature_score += int(weapon.get("defense_bonus", 0) or 0) * 12
            if weapon.get("passive"):
                creature_score += 900
        total += creature_score * rarity_bonus
    return max(1, round(total))


def _boss_hp_added(boss: IncursionBoss, team_power: int, current_max_hp: int) -> int:
    scaled = max(900_000, round(team_power * boss.hp_scale))
    return max(0, min(scaled, boss.hp_cap - int(current_max_hp)))


def _damage_modifier(boss: IncursionBoss, phase: int) -> float:
    modifier = {1: 1.0, 2: 0.94, 3: 0.86}.get(phase, 1.0)
    if boss.key == "hollow_king" and phase == 3:
        modifier -= 0.04
    if boss.key == "void_leviathan" and phase >= 2:
        modifier -= 0.03
    return max(0.72, modifier)


def _boss_attack_stats(
    boss: IncursionBoss,
    hydrated_team: list[dict[str, Any]],
    phase: int,
    seconds_left: int,
) -> tuple[int, int, int]:
    living: list[Creature] = []
    for index, row in enumerate(hydrated_team):
        creature = _creature_from_snapshot(row, "left", index)
        if creature.current_hp > 0:
            living.append(creature)
    if not living:
        return 1, 1, 1

    avg_hp = sum(creature.max_hp for creature in living) / len(living)
    avg_reduction = sum((creature.pr + creature.mr) / 2 for creature in living) / len(living)
    phase_factor = {1: 0.22, 2: 0.30, 3: 0.40}.get(phase, 0.24)
    enrage = 1.65 if seconds_left <= 5 * 60 else 1.0
    target_hit = avg_hp * phase_factor * boss.damage_scale * enrage
    raw_strength = target_hit / max(0.2, 1.0 - min(0.78, avg_reduction))
    str_stat = max(1, round((raw_strength - 100) / max(1, boss.level)))
    mag_stat = max(1, round(str_stat * 0.9))
    spd = max(1, round(8 + boss.level * 0.8))
    return str_stat, mag_stat, spd


def _boss_creature(
    boss: IncursionBoss,
    hp: int,
    max_hp: int,
    hydrated_team: list[dict[str, Any]],
    phase: int,
    seconds_left: int,
) -> dict[str, Any]:
    hp_stat = max(1, math.ceil((max_hp - 500) / (2 * max(1, boss.level))))
    str_stat, mag_stat, spd = _boss_attack_stats(boss, hydrated_team, phase, seconds_left)
    return {
        "id": -1,
        "name": boss.name,
        "rarity": "Abyssal",
        "level": boss.level,
        "ability": "Abyssal Strike",
        "hp_stat": hp_stat,
        "str_stat": str_stat,
        "pr_stat": 1,
        "wp_stat": max(1, boss.level // 2),
        "mag_stat": mag_stat,
        "mr_stat": 1,
        "spd": spd,
        "crit": 6 + phase * 2,
        "current_hp": hp,
    }


async def guild_config(db: BotDatabase, guild_id: int) -> Any:
    await db.execute(
        """INSERT OR IGNORE INTO boss_guild_config
           (guild_id, enabled, channel_id, last_spawn_at, next_spawn_at)
           VALUES (?, 1, NULL, 0, ?)""",
        (guild_id, random_next_spawn()),
    )
    return await db.fetchone("SELECT * FROM boss_guild_config WHERE guild_id = ?", (guild_id,))


async def set_guild_enabled(db: BotDatabase, guild_id: int, enabled: bool) -> None:
    await guild_config(db, guild_id)
    await db.execute(
        "UPDATE boss_guild_config SET enabled = ? WHERE guild_id = ?",
        (1 if enabled else 0, guild_id),
    )


async def set_guild_channel(db: BotDatabase, guild_id: int, channel_id: int | None) -> None:
    await guild_config(db, guild_id)
    await db.execute(
        "UPDATE boss_guild_config SET channel_id = ? WHERE guild_id = ?",
        (channel_id, guild_id),
    )


async def record_spawn_schedule(db: BotDatabase, guild_id: int, spawned_at: int) -> None:
    await guild_config(db, guild_id)
    await db.execute(
        "UPDATE boss_guild_config SET last_spawn_at = ?, next_spawn_at = ? WHERE guild_id = ?",
        (spawned_at, random_next_spawn(spawned_at), guild_id),
    )


async def expire_due_incursions(db: BotDatabase, guild_id: int | None = None) -> list[Any]:
    current = now_ts()
    if guild_id is None:
        rows = await db.fetchall(
            "SELECT * FROM boss_incursions WHERE status = 'active' AND ends_at <= ?",
            (current,),
        )
    else:
        rows = await db.fetchall(
            "SELECT * FROM boss_incursions WHERE guild_id = ? AND status = 'active' AND ends_at <= ?",
            (guild_id, current),
        )
    for row in rows:
        await db.execute(
            """UPDATE boss_incursions
               SET status = 'fled', fled_at = ?, summary = ?
               WHERE id = ? AND status = 'active'""",
            (current, "The boss fled into the deep.", int(row["id"])),
        )
    return rows


async def active_incursion(db: BotDatabase, guild_id: int) -> Any | None:
    await expire_due_incursions(db, guild_id)
    row = await db.fetchone(
        """SELECT * FROM boss_incursions
           WHERE guild_id = ? AND status = 'active'
           ORDER BY started_at DESC LIMIT 1""",
        (guild_id,),
    )
    if row is None:
        return None
    boss = boss_config(str(row["boss_key"]))
    total_power = max(0, int(row["total_power"] or 0))
    participants = max(0, int(row["participant_count"] or 0))
    expected_added = max(round(total_power * boss.hp_scale), participants * 900_000)
    expected_max_hp = min(boss.hp_cap, boss.base_hp + expected_added)
    if int(row["max_hp"]) < expected_max_hp:
        delta = expected_max_hp - int(row["max_hp"])
        new_hp = min(expected_max_hp, int(row["hp"]) + delta)
        await db.execute(
            """UPDATE boss_incursions
               SET hp = ?, max_hp = ?, base_hp = ?
               WHERE id = ? AND status = 'active'""",
            (new_hp, expected_max_hp, boss.base_hp, int(row["id"])),
        )
        row = await db.fetchone("SELECT * FROM boss_incursions WHERE id = ?", (int(row["id"]),))
    return row


async def latest_incursion(db: BotDatabase, guild_id: int) -> Any | None:
    await expire_due_incursions(db, guild_id)
    return await db.fetchone(
        "SELECT * FROM boss_incursions WHERE guild_id = ? ORDER BY started_at DESC LIMIT 1",
        (guild_id,),
    )


async def incursion_participants(db: BotDatabase, incursion_id: int) -> list[Any]:
    return await db.fetchall(
        """SELECT * FROM boss_participants
           WHERE incursion_id = ?
           ORDER BY support_score DESC, damage_dealt DESC, joined_at ASC""",
        (incursion_id,),
    )


async def create_incursion(
    db: BotDatabase,
    guild_id: int,
    channel_id: int | None,
    *,
    boss_key: str | None = None,
    created_by: int | None = None,
) -> Any:
    await expire_due_incursions(db, guild_id)
    existing = await active_incursion(db, guild_id)
    if existing is not None:
        raise IncursionError("An Abyssal Incursion is already active in this server.")

    boss = boss_config(boss_key)
    started = now_ts()
    incursion_id = await db.insert(
        """INSERT INTO boss_incursions
           (guild_id, channel_id, boss_key, boss_name, status, phase, hp, max_hp, base_hp,
            total_power, participant_count, started_at, ends_at, created_by, mechanics_json)
           VALUES (?, ?, ?, ?, 'active', 1, ?, ?, ?, 0, 0, ?, ?, ?, ?)""",
        (
            guild_id,
            channel_id,
            boss.key,
            boss.name,
            boss.base_hp,
            boss.base_hp,
            boss.base_hp,
            started,
            started + boss.duration_seconds,
            created_by,
            _json_dump(default_mechanics()),
        ),
    )
    return await db.fetchone("SELECT * FROM boss_incursions WHERE id = ?", (incursion_id,))


async def set_incursion_message(db: BotDatabase, incursion_id: int, message_id: int | None) -> None:
    await db.execute(
        "UPDATE boss_incursions SET message_id = ? WHERE id = ?",
        (message_id, incursion_id),
    )


async def join_incursion(
    db: BotDatabase,
    guild_id: int,
    user_id: int,
    display_name: str,
) -> JoinOutcome:
    row = await active_incursion(db, guild_id)
    if row is None:
        raise IncursionError("No Abyssal Incursion is active right now.")

    existing = await db.fetchone(
        "SELECT 1 FROM boss_participants WHERE incursion_id = ? AND user_id = ?",
        (int(row["id"]), user_id),
    )
    if existing is not None:
        raise IncursionError("Your team is already bound to this incursion.")

    team = await prepare_battle(db, user_id)
    if not team:
        raise IncursionError("Set a creature team before joining the incursion.")
    snapshot = [dict(creature) for creature in team]
    state = initial_team_state(snapshot)
    team_power = calculate_team_power(snapshot)

    boss = boss_config(str(row["boss_key"]))
    hp_added = _boss_hp_added(boss, team_power, int(row["max_hp"]))
    new_max_hp = int(row["max_hp"]) + hp_added
    new_hp = int(row["hp"]) + hp_added
    participants = int(row["participant_count"]) + 1

    await db.execute(
        """INSERT INTO boss_participants
           (incursion_id, guild_id, user_id, display_name, team_snapshot_json, team_state_json,
            team_power, joined_at, action_state_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            int(row["id"]),
            guild_id,
            user_id,
            display_name[:80],
            _json_dump(snapshot),
            _json_dump(state),
            team_power,
            now_ts(),
            _json_dump(default_action_state()),
        ),
    )
    await db.execute(
        """UPDATE boss_incursions
           SET hp = ?, max_hp = ?, total_power = total_power + ?, participant_count = ?
           WHERE id = ?""",
        (new_hp, new_max_hp, team_power, participants, int(row["id"])),
    )
    return JoinOutcome(
        incursion_id=int(row["id"]),
        boss_key=boss.key,
        boss_name=boss.name,
        team_power=team_power,
        hp_added=hp_added,
        hp=new_hp,
        max_hp=new_max_hp,
        participants=participants,
    )


async def leave_incursion(db: BotDatabase, guild_id: int, user_id: int) -> None:
    row = await active_incursion(db, guild_id)
    if row is None:
        raise IncursionError("No Abyssal Incursion is active right now.")
    participant = await db.fetchone(
        "SELECT * FROM boss_participants WHERE incursion_id = ? AND user_id = ?",
        (int(row["id"]), user_id),
    )
    if participant is None:
        raise IncursionError("You are not part of this incursion.")
    if int(participant["left_at"]):
        raise IncursionError("Your team has already left this incursion.")
    await db.execute(
        "UPDATE boss_participants SET left_at = ? WHERE incursion_id = ? AND user_id = ?",
        (now_ts(), int(row["id"]), user_id),
    )


async def perform_incursion_action(
    db: BotDatabase,
    guild_id: int,
    user_id: int,
    display_name: str,
    action: str = "strike",
) -> AttackOutcome:
    action = normalize_action(action)
    row = await active_incursion(db, guild_id)
    if row is None:
        raise IncursionError("No Abyssal Incursion is active right now.")
    participant = await db.fetchone(
        "SELECT * FROM boss_participants WHERE incursion_id = ? AND user_id = ?",
        (int(row["id"]), user_id),
    )
    if participant is None:
        raise IncursionError("Join the incursion before attacking.")
    if int(participant["left_at"]):
        raise IncursionError("Your team left this incursion and cannot attack.")
    if int(participant["wiped"]):
        raise IncursionError("Your bound team has been wiped in this incursion.")

    current = now_ts()
    cooldown = ACTION_COOLDOWNS[action]
    cooldown_left = cooldown - (current - int(participant["last_attack_at"]))
    if cooldown_left > 0:
        raise IncursionError(f"Your team is recovering. Try again in {cooldown_left}s.")

    team_snapshot = _json_load(participant["team_snapshot_json"], [])
    team_state = _json_load(participant["team_state_json"], [])
    if not isinstance(team_snapshot, list) or not team_snapshot:
        raise IncursionError("Your incursion team snapshot is broken. Leave and join the next incursion.")
    if not isinstance(team_state, list):
        team_state = initial_team_state(team_snapshot)

    hydrated_team = apply_team_state(team_snapshot, team_state)
    team_hp_before, team_max_hp_before = team_state_totals(team_state)
    if team_hp_before <= 0:
        await db.execute(
            "UPDATE boss_participants SET wiped = 1 WHERE incursion_id = ? AND user_id = ?",
            (int(row["id"]), user_id),
        )
        raise IncursionError("Your bound team has been wiped in this incursion.")
    if action == "channel" and team_hp_before <= max(3, round(team_max_hp_before * 0.22)):
        raise IncursionError("Your team is too wounded to channel. Guard or cleanse before attempting another ritual hit.")

    boss = boss_config(str(row["boss_key"]))
    hp_before = int(row["hp"])
    max_hp = int(row["max_hp"])
    previous_phase = phase_for(hp_before, max_hp)
    seconds_left = max(0, int(row["ends_at"]) - current)
    mechanics = mechanics_from_row(row)
    action_state = action_state_from_participant(participant)
    focus = int(action_state["focus"])
    guard = int(action_state["guard"])
    fracture = int(mechanics["fracture"])
    ward = int(mechanics["ward"])
    team_power = int(participant["team_power"])

    damage = 0
    healing = 0
    damage_taken = 0
    mitigation = 0
    score_gain = 0
    hp_after = hp_before
    new_state = team_state
    log_lines: tuple[str, ...] = ()
    summary = ""

    if action == "strike":
        before_state = _json_load(_json_dump(team_state), [])
        boss_team = [_boss_creature(boss, hp_before, max_hp, hydrated_team, previous_phase, seconds_left)]
        engine = BattleEngine(hydrated_team, boss_team, max_turns=2, log_enabled=False)
        frames = engine.run()
        boss_after_engine = max(0, round(engine.right[0].current_hp)) if engine.right else hp_before
        raw_damage = max(0, hp_before - boss_after_engine)
        focus_bonus = 1.0 + focus * 0.28
        fracture_bonus = 1.0 + min(12, fracture) * 0.045
        if boss_after_engine <= 0:
            damage = hp_before
        else:
            damage = round(raw_damage * _damage_modifier(boss, previous_phase) * focus_bonus * fracture_bonus)
            damage = min(hp_before, max(1, damage))
        hp_after = max(0, hp_before - damage)

        healing = sum(
            int(ev.healing + ev.heal_from_lifesteal + ev.heal_from_regen)
            for ev in engine.events
            if ev.actor_side == "left"
        )
        for ev in engine.events:
            if ev.actor_side == "right":
                damage_taken += int(ev.damage)
            elif ev.actor_side == "left" and ev.action_type == "status_damage":
                damage_taken += int(ev.status_damage)

        new_state = state_from_creatures(engine.left)
        mitigation_rate = min(0.62, ward * 0.055 + guard * 0.16)
        if mitigation_rate > 0 and isinstance(before_state, list):
            new_state, mitigation = _restore_mitigated_damage(
                before_state,
                new_state,
                round(damage_taken * mitigation_rate),
            )
            damage_taken = max(0, damage_taken - mitigation)
        if ward:
            mechanics["ward"] = max(0, ward - (2 if previous_phase >= 3 else 1))
        action_state["focus"] = 0
        action_state["guard"] = 0
        summary = f"Strike dealt {damage:,} damage"
        if focus:
            summary += f" after consuming {focus} Focus"
        if fracture:
            summary += f" against {fracture} Fracture"
        compact = tuple(str(line) for line in frames[-1].get("compact_log", [])[-4:]) if frames else ()
        log_lines = compact or (summary,)
        score_gain = damage + round(healing * 0.60) + round(damage_taken * 0.25) + round(mitigation * 0.80)

    elif action == "focus":
        focus_gain = 1 if focus < 3 else 0
        fracture_gain = 1 + (1 if previous_phase >= 3 else 0)
        action_state["focus"] = min(3, focus + focus_gain)
        mechanics["fracture"] = min(12, fracture + fracture_gain)
        summary = f"Focus +{focus_gain}; boss Fracture +{fracture_gain}"
        log_lines = (
            "Your team studies the boss rhythm instead of rushing in.",
            "Next strike gains power; the server damage window widens.",
        )
        score_gain = round(900 + team_power * 0.08 + fracture_gain * 1600 + focus_gain * 900)

    elif action == "guard":
        ward_gain = 2 + (1 if previous_phase >= 2 else 0)
        guard_gain = 1 if guard < 2 else 0
        mechanics["ward"] = min(10, ward + ward_gain)
        action_state["guard"] = min(2, guard + guard_gain)
        summary = f"Server Ward +{ward_gain}; personal Guard +{guard_gain}"
        log_lines = (
            "Your team locks formation and raises a server-wide ward.",
            "The next boss retaliation will be partially absorbed.",
        )
        score_gain = round(800 + team_power * 0.06 + ward_gain * 1300 + guard_gain * 900)

    elif action == "cleanse":
        cleanse_pct = 0.16 + (0.03 if previous_phase >= 3 else 0.0)
        new_state, healing, removed = _heal_team_state(team_state, cleanse_pct, flat=60, remove_statuses=True)
        mechanics["ward"] = min(10, ward + (1 if healing else 0))
        summary = f"Cleansed {removed} effects and restored {healing:,} HP"
        log_lines = (
            "A cold rite burns rot and fear out of your formation.",
            "This is a recovery turn; no direct boss damage dealt.",
        )
        score_gain = round(650 + healing * 0.78 + removed * 1800)

    elif action == "channel":
        sacrifice_pct = 0.12 + previous_phase * 0.035
        new_state, damage_taken = _sacrifice_team_state(team_state, sacrifice_pct)
        instability = int(mechanics["instability"]) + 1
        fracture_gain = 1 if instability >= 3 else 0
        mechanics["instability"] = 0 if fracture_gain else instability
        mechanics["fracture"] = min(12, fracture + fracture_gain)
        channel_bonus = 1.0 + focus * 0.24 + min(12, fracture) * 0.035
        channel_cap = round(max_hp * {1: 0.055, 2: 0.070, 3: 0.085}.get(previous_phase, 0.060))
        damage = max(1, round((team_power * 0.62 + team_hp_before * 0.22) * channel_bonus))
        damage = min(hp_before, max(1, min(damage, channel_cap)))
        hp_after = max(0, hp_before - damage)
        new_state, pressure_taken, pressure_mitigated = _boss_pressure_state(
            new_state,
            boss,
            previous_phase,
            action,
            ward=ward,
            guard=guard,
            seconds_left=seconds_left,
        )
        damage_taken += pressure_taken
        mitigation += pressure_mitigated
        action_state["focus"] = 0
        action_state["guard"] = 0
        summary = f"Channel dealt {damage:,} damage and cost {damage_taken:,} team HP"
        log_lines = (
            "Your team pours life into the breach for a heavy ritual hit.",
            "Every third channel cracks the boss armor for the whole server.",
        )
        score_gain = damage + round(damage_taken * 0.15) + fracture_gain * 2200

    if action in {"focus", "guard", "cleanse"}:
        new_state, pressure_taken, pressure_mitigated = _boss_pressure_state(
            new_state,
            boss,
            previous_phase,
            action,
            ward=int(mechanics["ward"]),
            guard=int(action_state["guard"]),
            seconds_left=seconds_left,
        )
        damage_taken += pressure_taken
        mitigation += pressure_mitigated
        score_gain += round(pressure_taken * 0.22 + pressure_mitigated * 0.55)
        if pressure_taken:
            log_lines = tuple(log_lines) + (f"{boss.name} pressed the formation for {pressure_taken:,} damage.",)
        if ward and action != "guard":
            mechanics["ward"] = max(0, int(mechanics["ward"]) - 1)
    elif action == "channel" and ward:
        mechanics["ward"] = max(0, int(mechanics["ward"]) - 1)

    team_hp_after, team_max_hp = team_state_totals(new_state)
    wiped = team_hp_after <= 0
    new_phase = phase_for(hp_after, max_hp)
    defeated = hp_after <= 0
    mechanics["last_action"] = action
    mechanics["action_count"] = int(mechanics["action_count"]) + 1
    action_state["last_action"] = action

    await db.execute(
        """UPDATE boss_participants
           SET display_name = ?, team_state_json = ?, damage_dealt = damage_dealt + ?,
               damage_taken = damage_taken + ?, healing_done = healing_done + ?,
               support_score = support_score + ?, attacks = attacks + 1,
               last_attack_at = ?, wiped = ?, action_state_json = ?
           WHERE incursion_id = ? AND user_id = ?""",
        (
            display_name[:80],
            _json_dump(new_state),
            damage,
            damage_taken,
            healing,
            score_gain,
            current,
            1 if wiped else 0,
            _json_dump(action_state),
            int(row["id"]),
            user_id,
        ),
    )
    await db.execute(
        """UPDATE boss_incursions
           SET hp = ?, phase = ?, last_attack_at = ?, mechanics_json = ?
           WHERE id = ?""",
        (hp_after, new_phase, current, _json_dump(mechanics), int(row["id"])),
    )
    if defeated:
        await db.execute(
            """UPDATE boss_incursions
               SET status = 'defeated', defeated_at = ?, summary = ?
               WHERE id = ? AND status = 'active'""",
            (current, f"{boss.name} was defeated by the server.", int(row["id"])),
        )

    return AttackOutcome(
        incursion_id=int(row["id"]),
        boss_key=boss.key,
        boss_name=boss.name,
        damage=damage,
        healing=healing,
        damage_taken=damage_taken,
        hp_before=hp_before,
        hp_after=hp_after,
        max_hp=max_hp,
        phase=new_phase,
        previous_phase=previous_phase,
        defeated=defeated,
        wiped=wiped,
        team_hp=team_hp_after,
        team_max_hp=team_max_hp,
        cooldown_seconds=cooldown,
        log_lines=log_lines,
        action=action,
        action_label=ACTION_LABELS[action],
        summary=summary,
        focus=int(action_state["focus"]),
        guard=int(action_state["guard"]),
        ward=int(mechanics["ward"]),
        fracture=int(mechanics["fracture"]),
        mitigation=mitigation,
    )


async def attack_incursion(
    db: BotDatabase,
    guild_id: int,
    user_id: int,
    display_name: str,
) -> AttackOutcome:
    return await perform_incursion_action(db, guild_id, user_id, display_name, "strike")


async def participant_for_active(db: BotDatabase, guild_id: int, user_id: int) -> Any | None:
    row = await active_incursion(db, guild_id)
    if row is None:
        return None
    return await db.fetchone(
        "SELECT * FROM boss_participants WHERE incursion_id = ? AND user_id = ?",
        (int(row["id"]), user_id),
    )


async def claim_rewards(
    db: BotDatabase,
    guild_id: int,
    user_id: int,
    display_name: str,
) -> RewardBundle:
    await expire_due_incursions(db, guild_id)
    row = await db.fetchone(
        """SELECT i.*
           FROM boss_incursions i
           JOIN boss_participants p ON p.incursion_id = i.id
           WHERE i.guild_id = ?
             AND p.user_id = ?
             AND i.status IN ('defeated', 'fled')
           ORDER BY i.started_at DESC
           LIMIT 1""",
        (guild_id, user_id),
    )
    if row is None:
        active = await active_incursion(db, guild_id)
        if active is not None:
            raise IncursionError("This incursion is still active. Rewards unlock when it ends.")
        raise IncursionError("You do not have any incursion rewards to claim.")

    participant = await db.fetchone(
        "SELECT * FROM boss_participants WHERE incursion_id = ? AND user_id = ?",
        (int(row["id"]), user_id),
    )
    if participant is None:
        raise IncursionError("You did not join that incursion.")
    if int(participant["reward_claimed"]):
        raise IncursionError("You already claimed rewards for your latest incursion.")

    participants = await incursion_participants(db, int(row["id"]))
    total_score = sum(max(0, int(p["support_score"])) for p in participants)
    if total_score <= 0:
        total_score = sum(max(0, int(p["damage_dealt"])) for p in participants)
    if total_score <= 0:
        raise IncursionError("No contribution was recorded for this incursion.")

    rank = 1
    for index, other in enumerate(participants, start=1):
        if int(other["user_id"]) == user_id:
            rank = index
            break

    boss = boss_config(str(row["boss_key"]))
    status = str(row["status"])
    score = max(0, int(participant["support_score"]))
    if score <= 0:
        score = max(0, int(participant["damage_dealt"]))
    contribution = score / total_score
    rank_bonus = {1: 260, 2: 160, 3: 100}.get(rank, 40)
    victory_mult = 1.0 if status == "defeated" else 0.42

    gold = round((900 + boss.level * 85 + int(participant["damage_dealt"]) / 16 + rank_bonus) * victory_mult)
    gems = round((4 + boss.level / 4 + min(40, score / 7500) + (4 if rank == 1 else 0)) * victory_mult)
    xp = round((180 + boss.level * 28 + score / 110) * victory_mult)
    shards = round((35 + score / 430 + rank_bonus / 5) * victory_mult)
    material_amount = max(1 if status == "defeated" else 0, round((3 + score / 9000 + max(0, 4 - rank)) * victory_mult))
    crate_key: str | None = None
    if status == "defeated":
        crate_key = "treasure" if rank == 1 else ("relic" if rank <= 3 else "cache")
    elif score >= max(1, total_score * 0.10):
        crate_key = "cache"

    player = await ensure_player(db, user_id, display_name)
    await award_currency(db, user_id, gold=max(0, gold), gems=max(0, gems))
    refreshed, gained_levels = await award_player_xp(db, player, max(0, xp))
    del refreshed
    if shards:
        await add_item(db, user_id, "material", WEAPON_SHARD_KEY, max(0, shards))
    if material_amount:
        await add_item(db, user_id, "material", boss.material_key, max(0, material_amount))
    if crate_key:
        await add_item(db, user_id, "crate", crate_key, 1)
    if status == "defeated":
        await unlock_achievement(db, user_id, "raid_slayer")
    await db.execute(
        "UPDATE boss_participants SET reward_claimed = 1 WHERE incursion_id = ? AND user_id = ?",
        (int(row["id"]), user_id),
    )

    return RewardBundle(
        incursion_id=int(row["id"]),
        boss_key=boss.key,
        boss_name=boss.name,
        status=status,
        rank=rank,
        contribution_pct=contribution * 100,
        gold=max(0, gold),
        gems=max(0, gems),
        xp=max(0, xp),
        shards=max(0, shards),
        material_key=boss.material_key,
        material_amount=max(0, material_amount),
        crate_key=crate_key,
        gained_levels=gained_levels,
    )
