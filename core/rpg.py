from __future__ import annotations

import json
import random
import sqlite3
import time
from hashlib import sha256
from datetime import datetime, timezone

from core.battle_engine import Ability
from core.content_config import balancing_value
from core.database import BotDatabase
from core.rpg_data import (
    ACHIEVEMENTS,
    CHARMS,
    CRATE_TYPES,
    CREATURES,
    MATERIALS,
    NPCHunter,
    QUESTS,
    RARITIES,
    RARITY_BY_NAME,
    RARITY_INDEX,
    SIGILS,
    WEAPON_AFFIXES,
    WEAPON_AFFIX_COUNTS,
    WEAPON_BASE_ATTACK,
    WEAPON_BASE_DEFENSE,
    WEAPON_BASE_STATS,
    WEAPON_NAME_PREFIX,
    WEAPON_NAME_SUFFIX,
    WEAPON_PASSIVES,
    WEAPON_PASSIVE_CHANCE,
    WEAPON_QUALITIES,
    WEAPON_SHARD_KEY,
    WEAPON_TYPES,
    WEAPON_WEAR_BONUS,
    WEAPON_WEAR_STAGES,
    ZONES,
    Charm,
    CreatureTemplate,
    determine_role,
    Sigil,
    Zone,
    creature_asset_key,
    normalize_key,
)
from core.theme import material_label


def _json_obj(raw: Any, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(str(raw))
    except Exception:
        return fallback


def now_ts() -> int:
    return int(time.time())


def today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def utc_day_start(ts: int | None = None) -> int:
    current = now_ts() if ts is None else int(ts)
    return current - (current % 86400)


def seconds_until_daily_reset(ts: int | None = None) -> int:
    current = now_ts() if ts is None else int(ts)
    return utc_day_start(current) + 86400 - current


def daily_reset_text() -> str:
    return "00:00 UTC"


def _balance_int(path: str, fallback: int) -> int:
    try:
        return int(balancing_value(path, fallback))
    except (TypeError, ValueError):
        return fallback


def _balance_float(path: str, fallback: float) -> float:
    try:
        return float(balancing_value(path, fallback))
    except (TypeError, ValueError):
        return fallback


CHECKLIST_HUNT_LOOTBOX_TARGET = _balance_int("hunt.checklist_hunt_lootbox_target", 3)
CHECKLIST_BATTLE_CRATE_TARGET = _balance_int("hunt.checklist_battle_crate_target", 3)
CHECKLIST_HUNT_LOOTBOX_CHANCE = _balance_float("hunt.checklist_hunt_lootbox_chance", 0.05)
CHECKLIST_BATTLE_CRATE_CHANCE = _balance_float("hunt.checklist_battle_crate_chance", 0.05)
CHECKLIST_LOOTBOX_KEY = "lootbox"
HUNT_BASE_CATCH_RATE = _balance_float("hunt.base_catch_rate", 0.60)
HUNT_LUCK_CATCH_BONUS = _balance_float("hunt.luck_catch_bonus", 0.015)
HUNT_MAX_CATCH_RATE = _balance_float("hunt.max_catch_rate", 0.95)
HUNT_BASE_COOLDOWN_SECONDS = _balance_float("hunt.base_cooldown_seconds", 15)
HUNT_LEVEL_COOLDOWN_REDUCTION = _balance_float("hunt.level_cooldown_reduction", 0.10)
HUNT_MIN_COOLDOWN_SECONDS = _balance_float("hunt.min_cooldown_seconds", 10)
HUNT_BASE_CRATE_CHANCE = _balance_float("hunt.base_crate_chance", 0.04)
HUNT_ZONE_LEVEL_CRATE_BONUS = _balance_float("hunt.zone_level_crate_bonus", 0.003)
HUNT_LUCK_CRATE_BONUS = _balance_float("hunt.luck_crate_bonus", 0.002)
HUNT_MAX_CRATE_CHANCE = _balance_float("hunt.max_crate_chance", 0.20)
HUNT_AUTOHUNT_ROLLS_PER_HOUR = _balance_int("hunt.autohunt_rolls_per_hour", 3)
HUNT_AUTOHUNT_MAX_ROLLS = _balance_int("hunt.autohunt_max_rolls", 48)
HUNT_SWORD_DURATION_SECONDS = _balance_int("hunt.hunt_sword_duration_seconds", 1200)
HUNT_SWORD_EXTRA_ROLLS = _balance_int("hunt.hunt_sword_extra_rolls", 1)

_DEFAULT_WEAPON_AFFIX_COUNTS = [0, 0, 1, 1, 2, 2, 3, 3, 3, 4, 4, 3, 4, 4]
_DEFAULT_WEAPON_BASE_ATTACK = [5, 10, 18, 28, 40, 55, 72, 90, 110, 135, 160, 100, 140, 180]
_DEFAULT_WEAPON_BASE_DEFENSE = [3, 5, 8, 12, 16, 22, 28, 35, 42, 50, 60, 38, 52, 65]


def _tier_value(values: list[int] | tuple[int, ...], defaults: list[int], rarity_index: int) -> int:
    source = list(values or defaults)
    if not source:
        source = defaults
    return int(source[min(max(0, rarity_index), len(source) - 1)])


def xp_for_level(level: int) -> int:
    return 100 + (level - 1) * 55 + level * level * 18


def creature_xp_for_level(level: int) -> int:
    return 60 + level * level * 24


def readable_seconds(seconds: int) -> str:
    if seconds <= 0:
        return "ready"
    hours, rem = divmod(seconds, 3600)
    minutes, sec = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def stat_total(player: sqlite3.Row) -> int:
    return int(player["strength"] + player["dexterity"] + player["luck"] + player["wisdom"] + player["endurance"])


def get_zone(value: str | None, fallback: str = "forgotten_woods") -> Zone:
    if not value:
        return ZONES[fallback]
    key = normalize_key(value)
    for zone in ZONES.values():
        if key in {zone.key, normalize_key(zone.name)}:
            return zone
    raise ValueError(f"Unknown zone. Try one of: {', '.join(zone.name for zone in ZONES.values())}")


async def ensure_player(db: BotDatabase, user_id: int, display_name: str) -> sqlite3.Row:
    row = await db.fetchone("SELECT * FROM rpg_players WHERE user_id = ?", (user_id,))
    if row is not None:
        return row

    created = now_ts()
    hunter_name = display_name[:32] or "Void Hunter"
    await db.execute(
        """
        INSERT INTO rpg_players (
            user_id, hunter_name, created_at, updated_at
        ) VALUES (?, ?, ?, ?)
        """,
        (user_id, hunter_name, created, created),
    )
    await add_item(db, user_id, "equipment", "rusted_sword", 1)
    return await db.fetchone("SELECT * FROM rpg_players WHERE user_id = ?", (user_id,))


async def refresh_player(db: BotDatabase, user_id: int) -> sqlite3.Row:
    row = await db.fetchone("SELECT * FROM rpg_players WHERE user_id = ?", (user_id,))
    if row is None:
        raise RuntimeError("RPG player does not exist")
    return row


async def add_item(db: BotDatabase, user_id: int, item_type: str, item_key: str, quantity: int) -> None:
    if quantity == 0:
        return
    await db.execute(
        """
        INSERT INTO rpg_inventory (user_id, item_type, item_key, quantity)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, item_type, item_key)
        DO UPDATE SET quantity = MAX(0, quantity + excluded.quantity)
        """,
        (user_id, item_type, item_key, quantity),
    )


async def get_quantity(db: BotDatabase, user_id: int, item_type: str, item_key: str) -> int:
    row = await db.fetchone(
        "SELECT quantity FROM rpg_inventory WHERE user_id = ? AND item_type = ? AND item_key = ?",
        (user_id, item_type, item_key),
    )
    return 0 if row is None else int(row["quantity"])


async def inventory_rows(db: BotDatabase, user_id: int) -> list[sqlite3.Row]:
    return await db.fetchall(
        "SELECT item_type, item_key, quantity FROM rpg_inventory WHERE user_id = ? AND quantity > 0 ORDER BY item_type, item_key",
        (user_id,),
    )


async def award_player_xp(db: BotDatabase, player: sqlite3.Row, gained_xp: int) -> tuple[sqlite3.Row, int]:
    level = int(player["level"])
    xp = int(player["xp"]) + gained_xp
    gained_levels = 0
    while xp >= xp_for_level(level):
        xp -= xp_for_level(level)
        level += 1
        gained_levels += 1
    await db.execute(
        "UPDATE rpg_players SET level = ?, xp = ?, updated_at = ? WHERE user_id = ?",
        (level, xp, now_ts(), player["user_id"]),
    )
    return await refresh_player(db, player["user_id"]), gained_levels


async def award_currency(db: BotDatabase, user_id: int, *, gold: int = 0, gems: int = 0) -> None:
    await db.execute(
        "UPDATE rpg_players SET gold = MAX(0, gold + ?), gems = MAX(0, gems + ?), updated_at = ? WHERE user_id = ?",
        (gold, gems, now_ts(), user_id),
    )


async def ensure_daily_checklist(db: BotDatabase, user_id: int) -> sqlite3.Row:
    period = today_key()
    await db.execute(
        """INSERT OR IGNORE INTO rpg_daily_checklists
           (user_id, period_key, daily_claimed, hunt_lootboxes, battle_crates, reward_claimed, updated_at)
           VALUES (?, ?, 0, 0, 0, 0, ?)""",
        (user_id, period, now_ts()),
    )
    row = await db.fetchone(
        "SELECT * FROM rpg_daily_checklists WHERE user_id = ? AND period_key = ?",
        (user_id, period),
    )
    if row is None:
        raise RuntimeError("Could not create daily checklist.")
    return row


def checklist_is_complete(row: sqlite3.Row) -> bool:
    return (
        bool(row["daily_claimed"])
        and int(row["hunt_lootboxes"]) >= CHECKLIST_HUNT_LOOTBOX_TARGET
        and int(row["battle_crates"]) >= CHECKLIST_BATTLE_CRATE_TARGET
    )


async def mark_checklist_daily(db: BotDatabase, user_id: int) -> sqlite3.Row:
    await ensure_daily_checklist(db, user_id)
    await db.execute(
        "UPDATE rpg_daily_checklists SET daily_claimed = 1, updated_at = ? WHERE user_id = ? AND period_key = ?",
        (now_ts(), user_id, today_key()),
    )
    return await ensure_daily_checklist(db, user_id)


async def roll_checklist_hunt_lootboxes(db: BotDatabase, user_id: int, attempts: int = 1) -> tuple[int, int]:
    found = 0
    final_count = 0
    for _ in range(max(1, attempts)):
        row = await ensure_daily_checklist(db, user_id)
        current = int(row["hunt_lootboxes"])
        final_count = current
        if current >= CHECKLIST_HUNT_LOOTBOX_TARGET:
            break
        if current == 0 or random.random() < max(0.0, min(1.0, CHECKLIST_HUNT_LOOTBOX_CHANCE)):
            final_count = current + 1
            found += 1
            await add_item(db, user_id, "lootbox", CHECKLIST_LOOTBOX_KEY, 1)
            await db.execute(
                "UPDATE rpg_daily_checklists SET hunt_lootboxes = ?, updated_at = ? WHERE user_id = ? AND period_key = ?",
                (final_count, now_ts(), user_id, today_key()),
            )
    return found, final_count


async def roll_checklist_battle_crates(db: BotDatabase, user_id: int, attempts: int = 1) -> tuple[int, int]:
    found = 0
    final_count = 0
    for _ in range(max(1, attempts)):
        row = await ensure_daily_checklist(db, user_id)
        current = int(row["battle_crates"])
        final_count = current
        if current >= CHECKLIST_BATTLE_CRATE_TARGET:
            break
        if current == 0 or random.random() < max(0.0, min(1.0, CHECKLIST_BATTLE_CRATE_CHANCE)):
            final_count = current + 1
            found += 1
            await add_item(db, user_id, "crate", "cache", 1)
            await db.execute(
                "UPDATE rpg_daily_checklists SET battle_crates = ?, updated_at = ? WHERE user_id = ? AND period_key = ?",
                (final_count, now_ts(), user_id, today_key()),
            )
    return found, final_count


async def claim_daily_checklist_reward(db: BotDatabase, user_id: int) -> dict[str, int]:
    row = await ensure_daily_checklist(db, user_id)
    if bool(row["reward_claimed"]):
        raise ValueError("Today's checklist reward is already claimed.")
    if not checklist_is_complete(row):
        raise ValueError("Finish every checklist task before claiming the reward.")

    rewards = {"gold": 1000, "lootbox": 1, "weapon_crate": 1, "weapon_shards": 100}
    await award_currency(db, user_id, gold=rewards["gold"])
    await add_item(db, user_id, "lootbox", CHECKLIST_LOOTBOX_KEY, rewards["lootbox"])
    await add_item(db, user_id, "crate", "cache", rewards["weapon_crate"])
    await add_item(db, user_id, "material", WEAPON_SHARD_KEY, rewards["weapon_shards"])
    await db.execute(
        "UPDATE rpg_daily_checklists SET reward_claimed = 1, updated_at = ? WHERE user_id = ? AND period_key = ?",
        (now_ts(), user_id, today_key()),
    )
    return rewards


def choose_rarity(zone: Zone, luck: int, rarity_bonus: float = 0.0) -> str:
    max_index = RARITY_INDEX[zone.max_rarity]
    available_rarities = {creature.rarity for creature in CREATURES}
    choices = [
        rarity
        for rarity in RARITIES
        if RARITY_INDEX.get(rarity.name, 0) <= max_index and rarity.name in available_rarities
    ]
    if not choices:
        choices = [RARITY_BY_NAME["Common"]]
    adjusted_weights: list[float] = []
    for rarity in choices:
        index = RARITY_INDEX.get(rarity.name, 0)
        bonus = 1.0 + rarity_bonus + (luck * 0.012 * index)
        adjusted_weights.append(max(1.0, rarity.weight * bonus / (1 + max(0, index - 2) * 0.18)))
    return random.choices([rarity.name for rarity in choices], weights=adjusted_weights, k=1)[0]


def choose_creature_template(rarity: str) -> CreatureTemplate:
    pool = [creature for creature in CREATURES if creature.rarity == rarity]
    if not pool:
        pool = list(CREATURES)
    return random.choice(pool)


def calculate_creature_stats(template: CreatureTemplate, level: int, *, variance: float = 1.0) -> dict[str, int | str]:
    rarity = RARITY_BY_NAME[template.rarity]
    rarity_index = RARITY_INDEX[template.rarity]
    level = max(1, min(100, int(level)))
    rarity_tilt = rarity.stat_multiplier

    hp = max(1, round((120 + template.hp * (12 + level * 1.85)) * rarity_tilt * variance))
    str_score = max(1, round((18 + template.attack * (3.2 + level * 0.62)) * rarity_tilt * variance))
    pr_score = max(1, round((12 + template.defense * (2.6 + level * 0.50)) * rarity_tilt * variance))
    wp_score = max(1, round((100 + template.wp_stat * (5 + level * 0.8)) * rarity_tilt * variance))
    mag_score = max(1, round((18 + template.mag_stat * (3.2 + level * 0.62)) * rarity_tilt * variance))
    mr_score = max(1, round((12 + template.mr_stat * (2.6 + level * 0.50)) * rarity_tilt * variance))
    spd = max(1, round((8 + template.speed * (1.5 + level * 0.22)) * rarity_tilt * variance))
    value = max(10, round((str_score * 1.5 + mag_score * 1.5 + pr_score * 1.2 + mr_score * 1.2 + hp * 0.55 + spd * 4.0 + wp_score * 0.8) * (1 + rarity_index * 0.06)))
    role = determine_role(template)

    return {
        "name": template.name, "rarity": template.rarity,
        "attack": str_score, "defense": pr_score, "hp": hp, "speed": spd,
        "crit": min(30, 4 + template.speed // 2 + rarity_index // 3 + spd // 60),
        "mana": 200,
        "str_stat": str_score, "pr_stat": pr_score, "wp_stat": wp_score,
        "mag_stat": mag_score, "mr_stat": mr_score, "spd": spd,
        "role": role,
        "ability": template.ability, "value": value,
        "image": creature_asset_key(template.name), "level": level,
    }


def roll_creature_stats(template: CreatureTemplate, hunter_level: int) -> dict[str, int | str]:
    return calculate_creature_stats(template, 1, variance=random.uniform(0.94, 1.08))


async def create_creature(db: BotDatabase, user_id: int, stats: dict[str, int | str]) -> int:
    return await db.insert(
        """INSERT INTO rpg_creatures (user_id, name, rarity, attack, defense, hp, speed, crit, mana, str_stat, pr_stat, wp_stat, mag_stat, mr_stat, spd, role, ability, value, image, level, xp, caught_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (user_id, stats["name"], stats["rarity"], stats.get("attack", 0), stats.get("defense", 0), stats["hp"], stats.get("speed", 1), stats["crit"], stats["mana"],
         stats["str_stat"], stats["pr_stat"], stats["wp_stat"], stats["mag_stat"], stats["mr_stat"], stats["spd"], stats["role"],
         stats["ability"], stats["value"], stats["image"], stats["level"], now_ts()),
    )


async def top_creatures(db: BotDatabase, user_id: int, limit: int = 3) -> list[sqlite3.Row]:
    return await db.fetchall(
        "SELECT * FROM rpg_creatures WHERE user_id = ? ORDER BY level DESC, str_stat + pr_stat + hp + spd DESC, id ASC LIMIT ?",
        (user_id, limit),
    )


async def team_creatures(db: BotDatabase, user_id: int) -> list[sqlite3.Row]:
    return await db.fetchall(
        "SELECT c.* FROM rpg_teams t JOIN rpg_creatures c ON c.id = t.creature_id WHERE t.user_id = ? ORDER BY t.slot ASC",
        (user_id,),
    )


async def progress_quest(db: BotDatabase, user_id: int, quest_key: str, amount: int = 1) -> None:
    if quest_key not in QUESTS:
        return
    period_key = today_key()
    await db.execute(
        """INSERT INTO rpg_quests (user_id, quest_key, period_key, progress, claimed) VALUES (?, ?, ?, ?, 0)
        ON CONFLICT(user_id, quest_key, period_key) DO UPDATE SET progress = MIN(progress + excluded.progress, ?)""",
        (user_id, quest_key, period_key, amount, int(QUESTS[quest_key]["target"])),
    )


async def unlock_achievement(db: BotDatabase, user_id: int, key: str) -> bool:
    if key not in ACHIEVEMENTS:
        return False
    before = await db.fetchone("SELECT 1 FROM rpg_achievements WHERE user_id = ? AND achievement_key = ?", (user_id, key))
    if before is not None:
        return False
    await db.execute("INSERT INTO rpg_achievements (user_id, achievement_key, unlocked_at) VALUES (?, ?, ?)", (user_id, key, now_ts()))
    return True


# ── Weapon Generation ───────────────────────────────────────────────

def row_get(row, key: str, default=None):
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        if hasattr(row, "keys") and key not in row.keys():
            return default
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


WEAPON_QUALITY_RARITY_TIERS: tuple[tuple[int, int, str], ...] = (
    (0, 10, "Common"),
    (11, 20, "Uncommon"),
    (21, 30, "Rare"),
    (31, 40, "Epic"),
    (41, 50, "Legendary"),
    (51, 60, "Mythic"),
    (61, 70, "Ancient"),
    (71, 80, "Divine"),
    (81, 85, "Eldritch"),
    (86, 90, "Abyssal"),
    (91, 120, "Prismatic"),
    (121, 135, "Ethereal"),
    (136, 145, "Void Lord"),
    (146, 150, "Hidden"),
)


def weapon_quality_rarity(quality_pct: int) -> str:
    quality = _clamp(quality_pct, 0, 150)
    for low, high, rarity in WEAPON_QUALITY_RARITY_TIERS:
        if low <= quality <= high:
            return rarity
    return "Common"


def weapon_quality_range_for_rarity(rarity: str) -> tuple[int, int]:
    normalized = str(rarity or "Common")
    for low, high, tier in WEAPON_QUALITY_RARITY_TIERS:
        if tier == normalized:
            return low, high
    return 0, 10


def _quality_label(quality_pct: int) -> str:
    return weapon_quality_rarity(quality_pct)


def _quality_multiplier(quality_pct: int) -> float:
    return 0.65 + _clamp(quality_pct, 0, 150) * 0.006


def calculate_weapon_roll_quality(row) -> int:
    """Calculate quality_pct (0-150) from core non-stat rolls only:
    active damage %, MANA cost, and passive_roll. Ignores all base stat rolls.
    """
    wtype_key = str(row_get(row, "weapon_type", "sword"))
    ability = Ability.for_weapon_type(wtype_key)
    sr_raw = row_get(row, "stat_rolls", "{}")
    try:
        sr = json.loads(str(sr_raw)) if isinstance(sr_raw, str) else sr_raw
    except Exception:
        sr = {}
    if not isinstance(sr, dict):
        sr = {}

    weighted_sum = 0.0
    total_weight = 0.0

    # Active damage percent (higher is better)
    active_roll = int(sr.get("active", 50))
    active_range = ability.multiplier_max - ability.multiplier_min
    if active_range > 0:
        active_pct = ability.multiplier_min + active_range * active_roll / 100.0
        active_score = (active_pct - ability.multiplier_min) / active_range
        weighted_sum += max(0.0, min(1.0, active_score)) * 45
        total_weight += 45

    # MANA cost (lower is better)
    wp_roll = int(sr.get("wp_cost", 50))
    cost_range = ability.wp_cost_max - ability.wp_cost_min
    if cost_range > 0:
        mana_cost = ability.wp_cost_max - cost_range * wp_roll / 100.0
        mana_score = (ability.wp_cost_max - mana_cost) / cost_range
        weighted_sum += max(0.0, min(1.0, mana_score)) * 25
        total_weight += 25

    # Passive roll (higher is better)
    passive = int(sr.get("passive_1", -1))
    if passive >= 0:
        passive_score = passive / 100.0
        weighted_sum += max(0.0, min(1.0, passive_score)) * 30
        total_weight += 30

    if total_weight <= 0:
        return 50

    avg = weighted_sum / total_weight
    return max(0, min(150, round(avg * 150)))


def _roll_wear() -> str:
    return random.choices(list(WEAPON_WEAR_STAGES), weights=[8, 18, 31, 31, 12], k=1)[0]


def _degrade_wear(wear: str) -> str:
    stages = list(WEAPON_WEAR_STAGES)
    if wear not in stages:
        return "Unknown"
    return stages[min(len(stages) - 1, stages.index(wear) + 1)]


def _roll_quality_pct(wear: str) -> int:
    ranges = {
        "Pristine": (100, 150),
        "Fine": (70, 125),
        "Decent": (35, 95),
        "Worn": (10, 65),
        "Unknown": (0, 80),
    }
    low, high = ranges.get(wear, (0, 80))
    return _clamp(random.randint(low, high) + WEAPON_WEAR_BONUS.get(wear, 0), 0, 150)


def _roll_mana_cost(rarity_index: int, quality_pct: int) -> int:
    quality = _clamp(quality_pct, 0, 150) / 150.0
    high = 240 - min(40, rarity_index * 3)
    low = max(90, high - 100)
    return _clamp(round(high - (high - low) * quality), low, high)


def _roll_affixes(rarity_index: int, quality_mult: float, affix_keys: list[str] | None = None) -> list[dict[str, object]]:
    if affix_keys is None:
        battle_pool = {
            "strength", "magic", "hp", "wp", "pr", "mr", "thorns", "regeneration",
            "safeguard", "adaptation", "crit", "life_steal", "attack_pct",
            "defense_pct", "bleed", "burn", "stun", "shield", "poison",
        }
        keys = [key for key in WEAPON_AFFIXES if key in battle_pool]
        random.shuffle(keys)
        keys = keys[:_tier_value(WEAPON_AFFIX_COUNTS, _DEFAULT_WEAPON_AFFIX_COUNTS, rarity_index)]
    else:
        keys = [key for key in affix_keys if key in WEAPON_AFFIXES]

    affixes: list[dict[str, object]] = []
    for key in keys:
        af = WEAPON_AFFIXES[key]
        roll = random.randint(0, 150)
        val = max(1, int(random.randint(int(af["min"]), int(af["max"])) * quality_mult))
        affixes.append({"stat": key, "value": val, "roll": roll, "fmt": str(af["fmt"]).format(val)})
    return affixes


def _roll_passive(wtype_key: str, rarity_index: int, passive_key: str | None = None) -> dict[str, object] | None:
    wtype = WEAPON_TYPES.get(wtype_key, {})
    pool = list(wtype.get("passive_pool", []))
    if passive_key is None:
        if not pool:
            return None
        passive_key = random.choice(pool)
    if passive_key not in WEAPON_PASSIVES:
        return None
    pc = WEAPON_PASSIVE_CHANCE.get(passive_key, {"min": 10, "max": 20})
    passive = WEAPON_PASSIVES[passive_key]
    return {
        "key": passive_key,
        "name": passive["name"],
        "desc": passive["desc"],
        "icon": passive["icon"],
        "chance": random.randint(pc["min"], pc["max"]),
    }


def _passive_key(weapon_row) -> str | None:
    passive_raw = row_get(weapon_row, "passive")
    if not passive_raw:
        return None
    try:
        passive = json.loads(str(passive_raw))
    except Exception:
        return None
    if isinstance(passive, dict) and passive.get("key"):
        return str(passive["key"])
    return None


def _affix_keys(weapon_row) -> list[str]:
    affixes_raw = row_get(weapon_row, "affixes", "[]")
    try:
        affixes = json.loads(str(affixes_raw))
    except Exception:
        return []
    if not isinstance(affixes, list):
        return []
    return [str(a.get("stat", "")) for a in affixes if isinstance(a, dict) and a.get("stat")]


def _roll_weapon(
    user_id: int,
    rarity: str,
    *,
    name: str | None = None,
    wtype_key: str | None = None,
    passive_key: str | None = None,
    keep_no_passive: bool = False,
    affix_keys: list[str] | None = None,
    wear: str | None = None,
) -> dict[str, object]:
    rarity_index = RARITY_INDEX.get(rarity, 0)
    if wtype_key and wtype_key in WEAPON_TYPES:
        pass
    else:
        wtype_keys = list(WEAPON_TYPES.keys())
        wtype_weights = [int(WEAPON_TYPES[k].get("crate_weight", 10)) for k in wtype_keys]
        wtype_key = random.choices(wtype_keys, weights=wtype_weights, k=1)[0]
    wtype = WEAPON_TYPES[wtype_key]
    if name is None:
        prefix = random.choice(WEAPON_NAME_PREFIX)
        suffix = random.choice(WEAPON_NAME_SUFFIX.get(wtype_key, ["Blade"]))
        name = f"{prefix} {suffix}"
    wear = wear if wear in WEAPON_WEAR_STAGES else _roll_wear()
    stat_rolls: dict[str, int] = {
        "active": random.randint(*weapon_quality_range_for_rarity(rarity)),
        "wp_cost": random.randint(*weapon_quality_range_for_rarity(rarity)),
    }
    passive_slots = 0 if wtype_key == "rune" else (2 if wtype_key == "orb" else 1)
    for slot in range(passive_slots):
        stat_rolls[f"passive_{slot + 1}"] = random.randint(*weapon_quality_range_for_rarity(rarity))

    passive = None if keep_no_passive and passive_key is None else _roll_passive(wtype_key, rarity_index, passive_key)
    affixes = [] if wtype_key == "rune" else _roll_affixes(rarity_index, 1.0, affix_keys)
    for index, affix in enumerate(affixes, start=1):
        roll_value = random.randint(*weapon_quality_range_for_rarity(rarity))
        affix["roll"] = roll_value
        stat_rolls[f"affix_{index}"] = roll_value
    quality_pct = max(1, round(sum(stat_rolls.values()) / max(1, len(stat_rolls))))
    if passive and "passive_1" in stat_rolls:
        passive["roll"] = stat_rolls["passive_1"]
    if passive and wtype_key == "orb":
        pool = [key for key in list(wtype.get("passive_pool", [])) if key != passive.get("key")]
        extra_key = random.choice(pool) if pool else None
        extra = _roll_passive(wtype_key, rarity_index, extra_key) if extra_key else None
        if extra:
            extra["roll"] = stat_rolls.get("passive_2", random.randint(*weapon_quality_range_for_rarity(rarity)))
            passive["extra"] = [extra]
    quality_mult = _quality_multiplier(quality_pct)
    for affix in affixes:
        stat = str(affix.get("stat", ""))
        af = WEAPON_AFFIXES.get(stat)
        if not af:
            continue
        val = max(1, round(int(af["min"]) + (int(af["max"]) - int(af["min"])) * (_clamp(quality_pct, 0, 150) / 150.0)))
        affix["value"] = val
        affix["fmt"] = str(af["fmt"]).format(val)

    base_atk = random.randint(int(wtype["atk_range"][0]), int(wtype["atk_range"][1]))
    base_def = random.randint(int(wtype["def_range"][0]), int(wtype["def_range"][1]))
    base_hp = random.randint(1, 6)
    base_wp = random.randint(1, 4)
    base_mag = random.randint(1, max(2, int(wtype["atk_range"][1]) // 2))
    base_mr = random.randint(1, max(2, int(wtype["def_range"][1]) // 2))
    base_spd = random.randint(1, 4)
    scale_stat = str(wtype.get("scale_stat", "STR")).upper()
    qm = 0.70 + quality_pct / 150.0
    active_score = round((base_atk + rarity_index * 2) * qm)
    guard_score = round((base_def + rarity_index) * qm)

    str_val = max(0, active_score if scale_stat == "STR" else active_score // 3)
    mag_val = max(0, active_score if scale_stat == "MAG" else active_score // 3)
    pr_val = max(0, guard_score if scale_stat in {"DEF", "HP", "RES", "MANA"} else guard_score)
    mr_val = max(0, guard_score // 3)

    if scale_stat == "HP":
        hp_val = max(0, round((base_def + base_hp) * qm))
    elif scale_stat == "STR":
        hp_val = max(0, round((base_hp + base_atk * 0.3) * qm))
    elif scale_stat == "MAG":
        hp_val = max(0, round(base_hp * qm * 0.8))
    else:
        hp_val = max(0, round(base_hp * qm))

    if scale_stat == "MAG":
        wp_val = max(0, round((base_wp + base_atk * 0.2) * qm))
    else:
        wp_val = max(0, round(base_wp * qm * 0.7))

    if scale_stat == "STR":
        spd_val = max(0, round((base_spd + base_atk * 0.2) * qm))
    elif scale_stat == "MAG":
        spd_val = max(0, round(base_spd * qm * 0.8))
    else:
        spd_val = max(0, round(base_spd * qm))

    base_hp_final = hp_val
    base_wp_final = wp_val
    base_mag_final = mag_val
    base_mr_final = mr_val
    base_spd_final = spd_val

    allowed = WEAPON_BASE_STATS.get(wtype_key, WEAPON_BASE_STATS["sword"])

    if "str_stat" in allowed:
        stat_rolls["base_str"] = base_atk
    if "pr_stat" in allowed:
        stat_rolls["base_pr"] = base_def
    if "hp" in allowed:
        stat_rolls["base_hp"] = base_hp_final
        stat_rolls["hp"] = base_hp_final
    if "wp_stat" in allowed:
        stat_rolls["base_wp"] = base_wp_final
        stat_rolls["wp_stat"] = base_wp_final
    if "mag_stat" in allowed:
        stat_rolls["base_mag"] = base_mag_final
        stat_rolls["mag_stat"] = base_mag_final
    if "mr_stat" in allowed:
        stat_rolls["base_mr"] = base_mr_final
        stat_rolls["mr_stat"] = base_mr_final
    if "spd" in allowed:
        stat_rolls["base_spd"] = base_spd_final
        stat_rolls["spd"] = base_spd_final

    atk = str_val if "str_stat" in allowed else 0
    defense = pr_val if "pr_stat" in allowed else 0
    for affix in affixes:
        if int(affix.get("roll", 0)) <= 0:
            affix["roll"] = random.randint(*weapon_quality_range_for_rarity(rarity))

    return {
        "user_id": user_id,
        "name": name,
        "rarity": weapon_quality_rarity(quality_pct),
        "weapon_type": wtype_key,
        "quality": _quality_label(quality_pct),
        "quality_pct": quality_pct,
        "mana_cost": _roll_mana_cost(rarity_index, quality_pct),
        "wear": wear,
        "attack_bonus": atk,
        "defense_bonus": defense,
        "passive": json.dumps(passive) if passive else None,
        "affixes": json.dumps(affixes),
        "affixes_list": affixes,
        "stat_rolls": json.dumps(stat_rolls),
        "created_at": now_ts(),
    }


def generate_weapon(user_id: int, rarity: str = "Common") -> dict[str, object]:
    return _roll_weapon(user_id, rarity)


def _roll_quality() -> dict[str, object]:
    r = random.random()
    cumulative = 0.0
    for q in WEAPON_QUALITIES:
        cumulative += float(q["chance"])
        if r < cumulative:
            return q
    return WEAPON_QUALITIES[0]


def weapon_display_name(weapon_row) -> str:
    quality_pct = int(row_get(weapon_row, "quality_pct", 50))
    quality = weapon_quality_rarity(quality_pct)
    wtype = str(row_get(weapon_row, "weapon_type", "sword"))
    type_data = WEAPON_TYPES.get(wtype, {})
    type_name = str(type_data.get("name", wtype.replace("_", " ").title()))
    if quality == "Common":
        return type_name
    return f"{quality} {type_name}"


async def insert_weapon(db: BotDatabase, weapon: dict[str, object]) -> int:
    return await db.insert(
        """INSERT INTO weapons
           (user_id, name, rarity, weapon_type, quality, quality_pct, mana_cost, wear,
            attack_bonus, defense_bonus, passive, affixes, stat_rolls, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (weapon["user_id"], weapon["name"], weapon["rarity"],
         weapon.get("weapon_type", "sword"), weapon.get("quality", "Normal"),
         weapon.get("quality_pct", 50), weapon.get("mana_cost", 3), weapon.get("wear", "Unknown"),
         weapon["attack_bonus"], weapon["defense_bonus"],
         weapon.get("passive"), weapon["affixes"], weapon.get("stat_rolls"), weapon["created_at"]),
    )


async def ensure_weapon_passives(db: BotDatabase) -> int:
    rows = await db.fetchall("SELECT * FROM weapons WHERE passive IS NULL OR passive = ''")
    updated = 0
    for row in rows:
        rarity = weapon_quality_rarity(int(row_get(row, "quality_pct", 50)))
        rarity_index = RARITY_INDEX.get(rarity, 0)
        wtype_key = str(row_get(row, "weapon_type", "sword"))
        passive = _roll_passive(wtype_key, rarity_index)
        if not passive:
            continue
        await db.execute(
            "UPDATE weapons SET passive = ? WHERE id = ?",
            (json.dumps(passive), int(row["id"])),
        )
        updated += 1
    return updated


async def player_weapons(db: BotDatabase, user_id: int) -> list[sqlite3.Row]:
    return await db.fetchall("SELECT * FROM weapons WHERE user_id = ? ORDER BY quality_pct DESC, id DESC", (user_id,))


def weapon_salvage_shards(weapon_row) -> int:
    quality_pct = int(row_get(weapon_row, "quality_pct", 50))
    rarity_index = RARITY_INDEX.get(weapon_quality_rarity(quality_pct), 0)
    base = [5, 8, 14, 24, 40, 65, 100, 150, 220, 320, 450, 550, 700, 900]
    return base[min(rarity_index, len(base) - 1)] + max(0, quality_pct // 20)


OWO_REROLL_COST = 100


def weapon_reroll_cost(weapon_row, mode: str) -> int:
    quality_pct = int(row_get(weapon_row, "quality_pct", 50))
    rarity_index = RARITY_INDEX.get(weapon_quality_rarity(quality_pct), 0)
    mode_key = normalize_key(mode)
    if mode_key in {"stat", "stats"}:
        return 10 + rarity_index * 5
    if mode_key in {"passive", "pass"}:
        return 22 + rarity_index * 8
    if mode_key in {"full", "all"}:
        return 35 + rarity_index * 12
    raise ValueError("Reroll mode must be `stat`, `passive`, or `full`.")


async def reroll_weapon(db: BotDatabase, user_id: int, weapon_id: int, mode: str) -> sqlite3.Row:
    row = await db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, user_id))
    if row is None:
        raise ValueError("Weapon not found.")
    mode_key = normalize_key(mode)
    cost = weapon_reroll_cost(row, mode_key)
    owned = await get_quantity(db, user_id, "material", WEAPON_SHARD_KEY)
    if owned < cost:
        raise ValueError(f"Need {cost} Weapon Shards. You have {owned}.")

    quality_pct_current = int(row_get(row, "quality_pct", 50))
    rarity = weapon_quality_rarity(quality_pct_current)
    rarity_index = RARITY_INDEX.get(rarity, 0)
    current_wear = str(row_get(row, "wear", "Unknown"))
    wear = _degrade_wear(current_wear) if random.random() < 0.35 else current_wear

    if mode_key in {"stat", "stats"}:
        rolled = _roll_weapon(
            user_id,
            rarity,
            name=str(row_get(row, "name", "?")),
            wtype_key=str(row_get(row, "weapon_type", "sword")),
            passive_key=_passive_key(row),
            affix_keys=_affix_keys(row),
            wear=wear,
        )
        await add_item(db, user_id, "material", WEAPON_SHARD_KEY, -cost)
        await db.execute(
            """UPDATE weapons
               SET rarity = ?, quality = ?, quality_pct = ?, mana_cost = ?, wear = ?,
                   attack_bonus = ?, defense_bonus = ?, passive = ?, affixes = ?
               WHERE id = ? AND user_id = ?""",
            (
                rolled["rarity"], rolled["quality"], rolled["quality_pct"], rolled["mana_cost"], rolled["wear"],
                rolled["attack_bonus"], rolled["defense_bonus"], rolled["passive"], rolled["affixes"],
                weapon_id, user_id,
            ),
        )
    elif mode_key in {"passive", "pass"}:
        wtype_key = str(row_get(row, "weapon_type", "sword"))
        pool = list(WEAPON_TYPES.get(wtype_key, {}).get("passive_pool", []))
        if not pool:
            raise ValueError("This weapon type has no passive pool.")
        current = _passive_key(row)
        choices = [key for key in pool if key != current] or pool
        passive = _roll_passive(wtype_key, rarity_index, random.choice(choices))
        quality_pct = _roll_quality_pct(wear)
        quality_rarity = weapon_quality_rarity(quality_pct)
        await add_item(db, user_id, "material", WEAPON_SHARD_KEY, -cost)
        await db.execute(
            """UPDATE weapons
               SET rarity = ?, quality = ?, quality_pct = ?, mana_cost = ?, wear = ?, passive = ?
               WHERE id = ? AND user_id = ?""",
            (
                quality_rarity, _quality_label(quality_pct), quality_pct, _roll_mana_cost(rarity_index, quality_pct),
                wear, json.dumps(passive) if passive else None, weapon_id, user_id,
            ),
        )
    elif mode_key in {"full", "all"}:
        rolled = _roll_weapon(user_id, rarity, wear=wear)
        await add_item(db, user_id, "material", WEAPON_SHARD_KEY, -cost)
        await db.execute(
            """UPDATE weapons
               SET name = ?, rarity = ?, weapon_type = ?, quality = ?, quality_pct = ?, mana_cost = ?, wear = ?,
                   attack_bonus = ?, defense_bonus = ?, passive = ?, affixes = ?
               WHERE id = ? AND user_id = ?""",
            (
                rolled["name"], rolled["rarity"], rolled["weapon_type"], rolled["quality"], rolled["quality_pct"],
                rolled["mana_cost"], rolled["wear"], rolled["attack_bonus"], rolled["defense_bonus"],
                rolled["passive"], rolled["affixes"], weapon_id, user_id,
            ),
        )
    else:
        raise ValueError("Reroll mode must be `stat`, `passive`, or `full`.")

    updated = await db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, user_id))
    if updated is None:
        raise RuntimeError("Weapon disappeared after reroll.")
    return updated


def _owo_map_roll(roll: float, min_val: float, max_val: float, higher_is_better: bool = True) -> float:
    """Map a 0-100 OwO-style roll to the actual value within a range."""
    if higher_is_better:
        return min_val + (max_val - min_val) * _clamp(roll, 0, 100) / 100.0
    else:
        return max_val - (max_val - min_val) * _clamp(roll, 0, 100) / 100.0


def _owo_generate_stat_rolls(wtype_key: str, affixes: list[dict]) -> dict[str, int]:
    """Generate fresh 0-100 OwO-style stat rolls for a weapon type."""
    allowed = WEAPON_BASE_STATS.get(wtype_key, WEAPON_BASE_STATS["sword"])
    rolls: dict[str, int] = {
        "active": random.randint(0, 100),
        "wp_cost": random.randint(0, 100),
    }
    base_keys = {
        "hp": "hp",
        "str_stat": "str_stat",
        "pr_stat": "pr_stat",
        "wp_stat": "wp_stat",
        "mag_stat": "mag_stat",
        "mr_stat": "mr_stat",
        "spd": "spd",
    }
    for short_key in base_keys:
        if short_key in allowed:
            rolls[short_key] = random.randint(0, 100)
    passive_slots = 0 if wtype_key == "rune" else (2 if wtype_key == "orb" else 1)
    for slot in range(passive_slots):
        rolls[f"passive_{slot + 1}"] = random.randint(0, 100)
    for idx, affix in enumerate(affixes, start=1):
        rolls[f"affix_{idx}"] = random.randint(0, 100)
    return rolls


def _owo_quality_from_rolls(stat_rolls: dict[str, int]) -> int:
    """Compute quality_pct (0-150 scale) from average of 0-100 stat rolls."""
    avg = sum(stat_rolls.values()) / max(1, len(stat_rolls))
    return max(0, min(150, round(avg * 150 / 100)))


async def owo_reroll_stat(db: BotDatabase, user_id: int, weapon_id: int) -> sqlite3.Row:
    """OwO-style stat reroll: reroll allowed base stats, active damage %, and MANA cost. Does NOT change passive or affixes."""
    row = await db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, user_id))
    if row is None:
        raise ValueError(f"No weapon with ID `{weapon_id}`.")

    owned = await get_quantity(db, user_id, "material", WEAPON_SHARD_KEY)
    if owned < OWO_REROLL_COST:
        raise ValueError(f"You need **{OWO_REROLL_COST}** {material_label(WEAPON_SHARD_KEY)} to reroll. You have **{owned:,}**.")

    wtype_key = str(row_get(row, "weapon_type", "sword"))
    wtype = WEAPON_TYPES.get(wtype_key, WEAPON_TYPES["sword"])
    allowed = WEAPON_BASE_STATS.get(wtype_key, WEAPON_BASE_STATS["sword"])

    stat_rolls_raw = str(row_get(row, "stat_rolls", ""))
    stat_rolls: dict[str, int] = _json_obj(stat_rolls_raw, {}) if stat_rolls_raw else {}

    for stat_key in allowed:
        roll = random.randint(0, 100)
        stat_rolls[stat_key] = roll
        if stat_key == "str_stat":
            stat_rolls["base_str"] = roll
        elif stat_key == "pr_stat":
            stat_rolls["base_pr"] = roll
        elif stat_key == "hp":
            stat_rolls["base_hp"] = roll
        elif stat_key == "wp_stat":
            stat_rolls["base_wp"] = roll
        elif stat_key == "mag_stat":
            stat_rolls["base_mag"] = roll
        elif stat_key == "mr_stat":
            stat_rolls["base_mr"] = roll
        elif stat_key == "spd":
            stat_rolls["base_spd"] = roll

    stat_rolls["active"] = random.randint(0, 100)
    stat_rolls["wp_cost"] = random.randint(0, 100)

    def _map_owostat(key: str, rmin: float, rmax: float) -> int:
        return round(_owo_map_roll(stat_rolls.get(key, 50), rmin, rmax))

    atk = _map_owostat("str_stat", float(wtype["atk_range"][0]), float(wtype["atk_range"][1])) if "str_stat" in allowed else 0
    defense = _map_owostat("pr_stat", float(wtype["def_range"][0]), float(wtype["def_range"][1])) if "pr_stat" in allowed else 0

    quality_pct = calculate_weapon_roll_quality({"weapon_type": wtype_key, "stat_rolls": json.dumps(stat_rolls)})

    await add_item(db, user_id, "material", WEAPON_SHARD_KEY, -OWO_REROLL_COST)
    await db.execute(
        """UPDATE weapons
           SET attack_bonus = ?, defense_bonus = ?, stat_rolls = ?,
               quality_pct = ?, rarity = ?, quality = ?
           WHERE id = ? AND user_id = ?""",
        (
            atk, defense, json.dumps(stat_rolls),
            quality_pct, weapon_quality_rarity(quality_pct), _quality_label(quality_pct),
            weapon_id, user_id,
        ),
    )

    updated = await db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, user_id))
    if updated is None:
        raise RuntimeError("Weapon disappeared after reroll.")
    return updated


async def owo_reroll_passive(db: BotDatabase, user_id: int, weapon_id: int) -> sqlite3.Row:
    """OwO-style passive reroll: replace passive and recalculate quality from core rolls. Does NOT change base stats or affixes."""
    row = await db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, user_id))
    if row is None:
        raise ValueError(f"No weapon with ID `{weapon_id}`.")

    wtype_key = str(row_get(row, "weapon_type", "sword"))
    pool = list(WEAPON_TYPES.get(wtype_key, {}).get("passive_pool", []))
    if not pool:
        raise ValueError("This weapon type has no passive pool.")

    owned = await get_quantity(db, user_id, "material", WEAPON_SHARD_KEY)
    if owned < OWO_REROLL_COST:
        raise ValueError(f"You need **{OWO_REROLL_COST}** {material_label(WEAPON_SHARD_KEY)} to reroll. You have **{owned:,}**.")

    current_passive_key = str(row_get(row, "passive", "{}"))
    try:
        current_key = str(json.loads(current_passive_key).get("key", "")) if current_passive_key else ""
    except (json.JSONDecodeError, TypeError, AttributeError):
        current_key = ""

    choices = [key for key in pool if key != current_key] or pool
    new_key = random.choice(choices)

    rarity_index = RARITY_INDEX.get(str(row_get(row, "rarity", "Common")), 0)
    new_passive = _roll_passive(wtype_key, rarity_index, new_key)
    if not new_passive:
        raise ValueError("Failed to generate a new passive.")

    stat_rolls_str = str(row_get(row, "stat_rolls", ""))
    stat_rolls: dict[str, int] = _json_obj(stat_rolls_str, {}) if stat_rolls_str else {}

    passive_roll = random.randint(0, 100)
    stat_rolls["passive_1"] = passive_roll

    if new_passive.get("key"):
        p_data = WEAPON_PASSIVE_CHANCE.get(str(new_passive["key"]), {"min": 5, "max": 20})
        p_value = round(_owo_map_roll(passive_roll, float(p_data["min"]), float(p_data["max"])))
        new_passive["roll"] = passive_roll
        new_passive["chance"] = p_value

    if wtype_key == "orb":
        pool2 = [key for key in pool if key != new_key] or pool
        extra_key = random.choice(pool2) if pool2 else None
        if extra_key:
            extra_passive = _roll_passive(wtype_key, rarity_index, extra_key)
            if extra_passive:
                extra_roll = random.randint(0, 100)
                stat_rolls["passive_2"] = extra_roll
                e_data = WEAPON_PASSIVE_CHANCE.get(extra_key, {"min": 5, "max": 20})
                e_value = round(_owo_map_roll(extra_roll, float(e_data["min"]), float(e_data["max"])))
                extra_passive["roll"] = extra_roll
                extra_passive["chance"] = e_value
                new_passive["extra"] = [extra_passive]
        if "passive_2" not in stat_rolls:
            stat_rolls["passive_2"] = random.randint(0, 100)

    quality_pct = calculate_weapon_roll_quality({"weapon_type": wtype_key, "stat_rolls": json.dumps(stat_rolls)})

    await add_item(db, user_id, "material", WEAPON_SHARD_KEY, -OWO_REROLL_COST)
    await db.execute(
        """UPDATE weapons
           SET passive = ?, stat_rolls = ?,
               quality_pct = ?, rarity = ?, quality = ?
           WHERE id = ? AND user_id = ?""",
        (
            json.dumps(new_passive) if new_passive.get("key") else None,
            json.dumps(stat_rolls),
            quality_pct, weapon_quality_rarity(quality_pct), _quality_label(quality_pct),
            weapon_id, user_id,
        ),
    )

    updated = await db.fetchone("SELECT * FROM weapons WHERE id = ? AND user_id = ?", (weapon_id, user_id))
    if updated is None:
        raise RuntimeError("Weapon disappeared after reroll.")
    return updated


async def equip_weapon_to_creature(db: BotDatabase, weapon_id: int, creature_id: int) -> None:
    await db.execute("UPDATE weapons SET equipped_creature_id = ? WHERE id = ?", (creature_id, weapon_id))


async def unequip_weapon(db: BotDatabase, weapon_id: int) -> None:
    await db.execute("UPDATE weapons SET equipped_creature_id = NULL WHERE id = ?", (weapon_id,))


async def weapon_for_creature(db: BotDatabase, creature_id: int) -> sqlite3.Row | None:
    return await db.fetchone("SELECT * FROM weapons WHERE equipped_creature_id = ?", (creature_id,))


async def creature_weapons(db: BotDatabase, creature_ids: list[int]) -> dict[int, sqlite3.Row | None]:
    if not creature_ids:
        return {}
    placeholders = ",".join("?" for _ in creature_ids)
    rows = await db.fetchall(f"SELECT * FROM weapons WHERE equipped_creature_id IN ({placeholders})", creature_ids)
    result: dict[int, sqlite3.Row | None] = {cid: None for cid in creature_ids}
    for row in rows:
        result[int(row["equipped_creature_id"])] = row
    return result


# ══════════════════════════════════════════════════════════════════
#  SIGIL & CHARM BUFFS
# ══════════════════════════════════════════════════════════════════

def _buff_max_charges(buff_key: str, fallback: int) -> int:
    for item in (*SIGILS, *CHARMS):
        if item.key == buff_key:
            return max(1, int(item.charges))
    return max(1, int(fallback))


async def activate_buff(db: BotDatabase, user_id: int, buff_key: str, buff_type: str, charges: int) -> None:
    max_charges = _buff_max_charges(buff_key, charges)
    charges = min(max(1, int(charges)), max_charges)
    await db.execute(
        """INSERT INTO rpg_active_buffs (user_id, buff_key, buff_type, charges_remaining, activated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id, buff_key) DO UPDATE SET charges_remaining = MIN(charges_remaining + ?, ?), activated_at = ?""",
        (user_id, buff_key, buff_type, charges, now_ts(), charges, max_charges, now_ts()),
    )


async def get_active_buffs(db: BotDatabase, user_id: int) -> dict[str, int]:
    rows = await db.fetchall(
        "SELECT buff_key, buff_type, charges_remaining FROM rpg_active_buffs WHERE user_id = ? AND charges_remaining > 0",
        (user_id,),
    )
    active: dict[str, int] = {}
    for row in rows:
        key = str(row["buff_key"])
        charges = int(row["charges_remaining"])
        capped = min(charges, _buff_max_charges(key, charges))
        active[key] = capped
        if capped != charges:
            await db.execute(
                "UPDATE rpg_active_buffs SET charges_remaining = ? WHERE user_id = ? AND buff_key = ?",
                (capped, user_id, key),
            )
    return active


async def consume_buff(db: BotDatabase, user_id: int, buff_key: str) -> None:
    await db.execute(
        "UPDATE rpg_active_buffs SET charges_remaining = charges_remaining - 1 WHERE user_id = ? AND buff_key = ? AND charges_remaining > 0",
        (user_id, buff_key),
    )


def apply_sigil(buffs: dict[str, int]) -> int:
    extra = 0
    for s in SIGILS:
        if s.key in buffs:
            extra += s.extra_monsters
    for c in CHARMS:
        if c.key in buffs:
            extra += c.extra_monsters
    return extra


def apply_charm(buffs: dict[str, int]) -> float:
    bonus = 0.0
    for c in CHARMS:
        if c.key in buffs:
            bonus += c.rarity_bonus
    return bonus


STAT_KEY_MAP: dict[str, str] = {
    "hp": "hp",
    "strength": "str_stat",
    "str": "str_stat",
    "str_stat": "str_stat",
    "attack_flat": "str_stat",
    "attack": "str_stat",
    "def": "pr_stat",
    "pr": "pr_stat",
    "pr_stat": "pr_stat",
    "defense_flat": "pr_stat",
    "defense": "pr_stat",
    "wp": "wp_stat",
    "mana": "wp_stat",
    "wp_stat": "wp_stat",
    "magic": "mag_stat",
    "mag": "mag_stat",
    "mag_stat": "mag_stat",
    "mr": "mr_stat",
    "res": "mr_stat",
    "mr_stat": "mr_stat",
    "res_stat": "mr_stat",
    "speed": "spd",
    "spd": "spd",
    "base_hp": "hp",
    "base_str": "str_stat",
    "base_pr": "pr_stat",
    "base_wp": "wp_stat",
    "base_mag": "mag_stat",
    "base_mr": "mr_stat",
    "base_spd": "spd",
}


def weapon_stats(weapon_row) -> dict[str, int]:
    if weapon_row is None:
        return {"hp": 0, "str_stat": 0, "pr_stat": 0, "wp_stat": 0, "mag_stat": 0, "mr_stat": 0, "spd": 0}

    wtype_key = str(row_get(weapon_row, "weapon_type", "sword"))
    allowed = WEAPON_BASE_STATS.get(wtype_key, WEAPON_BASE_STATS["sword"])

    atk = int(row_get(weapon_row, "attack_bonus", 0))
    df = int(row_get(weapon_row, "defense_bonus", 0))

    stats: dict[str, int] = {"hp": 0, "str_stat": 0, "pr_stat": 0, "wp_stat": 0, "mag_stat": 0, "mr_stat": 0, "spd": 0}
    if "str_stat" in allowed:
        stats["str_stat"] = atk
    if "pr_stat" in allowed:
        stats["pr_stat"] = df

    affixes_raw = row_get(weapon_row, "affixes", "[]")
    try:
        affixes = json.loads(str(affixes_raw))
    except Exception:
        affixes = []
    for a in affixes:
        s, v = str(a.get("stat", "")), int(a.get("value", 0))
        target = STAT_KEY_MAP.get(s)
        if target and target in stats:
            stats[target] = stats[target] + v

    stat_rolls_raw = row_get(weapon_row, "stat_rolls")
    if stat_rolls_raw:
        try:
            sr = json.loads(str(stat_rolls_raw))
            if isinstance(sr, dict):
                for raw_key, raw_val in sr.items():
                    target = STAT_KEY_MAP.get(raw_key)
                    if target and target in stats and target in allowed:
                        stats[target] = stats[target] + int(raw_val)
        except Exception:
            pass
    return stats


def weapon_effects(weapon_row) -> dict[str, int]:
    effects: dict[str, int] = {}
    if weapon_row is None:
        return effects
    affixes_raw = row_get(weapon_row, "affixes", "[]")
    try:
        affixes = json.loads(str(affixes_raw))
    except Exception:
        affixes = []
    for a in affixes:
        s, v = str(a.get("stat", "")), int(a.get("value", 0))
        if s in (
            "strength", "magic", "hp", "wp", "pr", "mr", "thorns", "regeneration",
            "safeguard", "adaptation", "crit", "life_steal", "bleed", "burn",
            "stun", "shield", "poison", "soul_gain", "gem_finder", "xp_boost",
            "attack_pct", "defense_pct", "rare_finder",
        ):
            effects[s] = effects.get(s, 0) + v
    passive_raw = row_get(weapon_row, "passive")
    if passive_raw:
        try:
            passive = json.loads(str(passive_raw))
            if isinstance(passive, dict) and passive.get("key"):
                effects[passive["key"]] = passive.get("chance", 0)
        except Exception:
            pass
    return effects


def apply_weapon(creature: dict[str, object], weapon_row) -> dict[str, object]:
    cr = dict(creature)
    if weapon_row is None:
        return cr
    cr["_weapon"] = {
        "id": row_get(weapon_row, "id"),
        "name": str(row_get(weapon_row, "name", "?")),
        "rarity": weapon_quality_rarity(int(row_get(weapon_row, "quality_pct", 50))),
        "attack_bonus": int(row_get(weapon_row, "attack_bonus", 0)),
        "defense_bonus": int(row_get(weapon_row, "defense_bonus", 0)),
        "affixes": str(row_get(weapon_row, "affixes", "[]")),
        "weapon_type": str(row_get(weapon_row, "weapon_type", "sword")),
        "quality": str(row_get(weapon_row, "quality", "Normal")),
        "quality_pct": int(row_get(weapon_row, "quality_pct", 50)),
        "mana_cost": int(row_get(weapon_row, "mana_cost", 3)),
        "wear": str(row_get(weapon_row, "wear", "Unknown")),
        "passive": row_get(weapon_row, "passive"),
    }
    for k, v in weapon_effects(weapon_row).items():
        cr["_" + k] = v
    return cr


async def prepare_battle(db: BotDatabase, user_id: int) -> list[dict[str, object]]:
    creatures = await team_creatures(db, user_id)
    if not creatures:
        return []
    cids = [int(c["id"]) for c in creatures]
    weapons = await creature_weapons(db, cids)
    return [apply_weapon(dict(c), weapons.get(int(c["id"]))) for c in creatures]


# ── Crate Opening (Simplified) ─────────────────────────────────────

async def open_crate(db: BotDatabase, user_id: int, crate_key: str) -> dict[str, object]:
    crate = CRATE_TYPES.get(crate_key)
    if not crate:
        raise ValueError(f"Unknown crate: {crate_key}")
    gold = random.randint(int(crate["gold"][0]), int(crate["gold"][1]))
    gems = random.randint(int(crate["gems"][0]), int(crate["gems"][1]))
    swords = random.randint(int(crate["swords"][0]), int(crate["swords"][1]))
    materials: dict[str, int] = {}
    weapons: list[dict[str, object]] = []
    if random.random() < float(crate["weapon_chance"]):
        wr = random.choice(list(crate["weapon_rarities"]))
        w = generate_weapon(user_id, str(wr))
        wid = await insert_weapon(db, w)
        w["id"] = wid
        weapons.append(w)
    await award_currency(db, user_id, gold=gold, gems=gems)
    if swords:
        await add_item(db, user_id, "consumable", "hunt_sword", swords)
    return {"gold": gold, "gems": gems, "materials": materials, "swords": swords, "weapons": weapons}


async def open_lootbox(db: BotDatabase, user_id: int) -> dict[str, object]:
    """Open a hunt lootbox.

    Lootboxes are stored separately from weapon crates in inventory, but they
    use the same reward presentation as a small cache.
    """
    return await open_crate(db, user_id, "cache")


# ── Battle System ──────────────────────────────────────────────────────

async def ensure_arena_stats(db: BotDatabase, user_id: int, guild_id: int) -> sqlite3.Row:
    row = await db.fetchone("SELECT * FROM rpg_arena_stats WHERE user_id = ?", (user_id,))
    if row is None:
        await db.execute(
            "INSERT INTO rpg_arena_stats (user_id, guild_id, rating, wins, losses, win_streak, highest_win_streak, total_battles, last_battle_at) VALUES (?, ?, 1000, 0, 0, 0, 0, 0, 0)",
            (user_id, guild_id),
        )
        row = await db.fetchone("SELECT * FROM rpg_arena_stats WHERE user_id = ?", (user_id,))
    return row


def elo_rating_change(winner_rating: int, loser_rating: int, k: int = 32) -> tuple[int, int]:
    expected_winner = 1.0 / (1.0 + 10.0 ** ((loser_rating - winner_rating) / 400.0))
    expected_loser = 1.0 / (1.0 + 10.0 ** ((winner_rating - loser_rating) / 400.0))
    winner_change = round(k * (1.0 - expected_winner))
    loser_change = round(k * (0.0 - expected_loser))
    return winner_change, loser_change


def team_power(creatures: list[sqlite3.Row | dict]) -> int:
    total = 0
    for c in creatures:
        atk = int(c.get("attack", 0) if isinstance(c, dict) else c["attack"])
        defense = int(c.get("defense", 0) if isinstance(c, dict) else c["defense"])
        hp = int(c.get("hp", 0) if isinstance(c, dict) else c["hp"])
        spd = int(c.get("speed", 0) if isinstance(c, dict) else c["speed"])
        lvl = int(c.get("level", 1) if isinstance(c, dict) else c["level"])
        crit = int(c.get("crit", 5) if isinstance(c, dict) else c["crit"])
        mana = int(c.get("mana", 50) if isinstance(c, dict) else c["mana"])
        total += atk + defense + spd + hp // 4 + lvl * 8 + crit * 3 + mana // 5
    return total


async def join_battle_queue(db: BotDatabase, user_id: int, guild_id: int) -> None:
    await db.execute(
        "INSERT OR REPLACE INTO rpg_battle_queue (user_id, guild_id, joined_at) VALUES (?, ?, ?)",
        (user_id, guild_id, now_ts()),
    )


async def leave_battle_queue(db: BotDatabase, user_id: int) -> None:
    await db.execute("DELETE FROM rpg_battle_queue WHERE user_id = ?", (user_id,))


async def find_match(db: BotDatabase, user_id: int) -> sqlite3.Row | None:
    rows = await db.fetchall(
        "SELECT * FROM rpg_battle_queue WHERE user_id != ? ORDER BY joined_at ASC LIMIT 1",
        (user_id,),
    )
    if rows:
        await db.execute("DELETE FROM rpg_battle_queue WHERE user_id IN (?, ?)", (user_id, rows[0]["user_id"]))
        return rows[0]
    return None


def generate_npc_team(npc: NPCHunter) -> list[dict[str, object]]:
    team = []
    for nc in npc.creatures:
        creature = {
            "name": nc.name,
            "rarity": nc.rarity,
            "attack": nc.attack,
            "defense": nc.defense,
            "hp": nc.hp,
            "speed": nc.speed,
            "str_stat": nc.str_stat or nc.attack,
            "pr_stat": nc.pr_stat or nc.defense,
            "wp_stat": nc.wp_stat or 0,
            "mag_stat": nc.mag_stat or 0,
            "mr_stat": nc.mr_stat or 0,
            "spd": nc.spd or nc.speed,
            "role": nc.role or "Balanced",
            "crit": nc.crit,
            "mana": nc.mana,
            "ability": nc.ability,
            "level": nc.level,
            "_npc": True,
        }
        team.append(creature)
    return team


async def save_team_snapshot(db: BotDatabase, user_id: int) -> None:
    creatures = await team_creatures(db, user_id)
    if not creatures:
        return
    await db.execute("DELETE FROM rpg_team_snapshots WHERE user_id = ?", (user_id,))
    cids = [int(c["id"]) for c in creatures]
    weapons = await creature_weapons(db, cids)
    for slot, cr in enumerate(creatures, start=1):
        w = weapons.get(int(cr["id"]))
        await db.execute(
            """INSERT INTO rpg_team_snapshots
               (user_id, guild_id, slot, creature_id, name, rarity, attack, defense, hp, speed, crit, mana, ability, level,
                weapon_id, weapon_name, weapon_rarity, weapon_attack_bonus, weapon_defense_bonus, weapon_affixes,
                weapon_type, weapon_quality, weapon_passive)
               VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, slot, int(cr["id"]),
                str(cr["name"]), str(cr["rarity"]),
                int(cr["attack"]), int(cr["defense"]), int(cr["hp"]), int(cr["speed"]),
                int(cr["crit"]), int(cr["mana"]), str(cr["ability"]), int(cr["level"]),
                int(w["id"]) if w else None,
                str(w["name"]) if w else None,
                str(w["rarity"]) if w else None,
                int(w["attack_bonus"]) if w else 0,
                int(w["defense_bonus"]) if w else 0,
                str(w["affixes"]) if w else "[]",
                str(w["weapon_type"]) if w else "sword",
                str(w["quality"]) if w else "Normal",
                str(w["passive"]) if w else None,
            ),
        )


async def load_team_snapshot(db: BotDatabase, user_id: int) -> list[dict[str, object]]:
    rows = await db.fetchall(
        "SELECT * FROM rpg_team_snapshots WHERE user_id = ? ORDER BY slot ASC",
        (user_id,),
    )
    if not rows:
        return []
    team = []
    for r in rows:
        cr = {
            "name": str(r["name"]), "rarity": str(r["rarity"]),
            "attack": int(r["attack"]), "defense": int(r["defense"]),
            "hp": int(r["hp"]), "speed": int(r["speed"]),
            "crit": int(r["crit"]), "mana": int(r["mana"]),
            "ability": str(r["ability"]), "level": int(r["level"]),
            "_snapshot": True,
        }
        if r["weapon_id"]:
            cr["_weapon"] = {
                "name": str(r["weapon_name"]), "rarity": str(r["weapon_rarity"]),
                "attack_bonus": int(r["weapon_attack_bonus"]), "defense_bonus": int(r["weapon_defense_bonus"]),
                "affixes": str(r["weapon_affixes"]),
                "weapon_type": str(r["weapon_type"]) if r["weapon_type"] else "sword",
                "quality": str(r["weapon_quality"]) if r["weapon_quality"] else "Normal",
                "passive": str(r["weapon_passive"]) if r["weapon_passive"] else None,
            }
            ws = weapon_stats(cr["_weapon"])
            cr["attack"] = int(cr.get("attack", 0)) + ws.get("str_stat", 0)
            cr["defense"] = int(cr.get("defense", 0)) + ws.get("pr_stat", 0)
        team.append(cr)
    return team


async def update_arena_after_battle(
    db: BotDatabase, user_id: int, guild_id: int, won: bool, rating_change: int,
) -> sqlite3.Row:
    stats = await ensure_arena_stats(db, user_id, guild_id)
    streak = int(stats["win_streak"])
    new_streak = (streak + 1) if won else 0
    await db.execute(
        """UPDATE rpg_arena_stats SET
           rating = MAX(0, rating + ?),
           wins = wins + ?,
           losses = losses + ?,
           win_streak = ?,
           highest_win_streak = MAX(highest_win_streak, ?),
           total_battles = total_battles + 1,
           last_battle_at = ?
           WHERE user_id = ?""",
        (rating_change, 1 if won else 0, 0 if won else 1, new_streak, new_streak, now_ts(), user_id),
    )
    return await db.fetchone("SELECT * FROM rpg_arena_stats WHERE user_id = ?", (user_id,))


async def record_battle_history(
    db: BotDatabase, user_id: int, opponent_name: str, opponent_id: int,
    won: bool, rating_change: int, opponent_rating: int, is_npc: bool, log: list[str],
) -> None:
    await db.execute(
        """INSERT INTO rpg_battle_history (user_id, opponent_name, opponent_id, won, rating_change, opponent_rating, is_npc, log, fought_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, opponent_name, opponent_id, 1 if won else 0, rating_change, opponent_rating, 1 if is_npc else 0, "\n".join(log), now_ts()),
    )


def calculate_battle_rewards(won: bool, player_level: int, streak: int, rating: int) -> dict[str, object]:
    from core.rpg_data import streak_multiplier, get_streak_tier
    base_mult = 1.0 + streak_multiplier(streak)
    tier = get_streak_tier(streak)
    xp_mult = base_mult * (1.0 + tier.xp_boost)
    gold_mult = base_mult * (1.0 + tier.gold_boost)
    if won:
        gold = round((160 + player_level * 12) * gold_mult)
        gems = max(1, round(3 * base_mult))
        xp = round(75 * xp_mult)
        return {"gold": gold, "gems": gems, "xp": xp}
    else:
        gold = round((40 + player_level * 4) * gold_mult)
        return {"gold": gold, "gems": 0, "xp": 0}


async def get_bounty_targets(db: BotDatabase, min_streak: int = 20) -> list[sqlite3.Row]:
    return await db.fetchall(
        """SELECT s.*, p.hunter_name FROM rpg_arena_stats s
           JOIN rpg_players p ON s.user_id = p.user_id
           WHERE s.win_streak >= ? ORDER BY s.win_streak DESC LIMIT 5""",
        (min_streak,),
    )


# ══════════════════════════════════════════════════════════════════
#  DAILY CRATE SHOP
# ══════════════════════════════════════════════════════════════════

_CRATE_SHOP_DEALS: list[dict[str, object]] = [
    {"key": "cache", "name": "Void Cache", "base_souls": 500, "base_gems": 0, "emoji": "📦"},
    {"key": "relic", "name": "Eldritch Relic", "base_souls": 5000, "base_gems": 30, "emoji": "🔮"},
    {"key": "treasure", "name": "Abyssal Treasure", "base_souls": 25000, "base_gems": 150, "emoji": "👑"},
]

_BUNDLE_TEMPLATES: list[dict[str, object]] = [
    {"name": "Cache Duo", "crate": "cache", "bundle": 2, "emoji": "📦📦", "desc": "2x Void Caches"},
    {"name": "Cache Stack", "crate": "cache", "bundle": 5, "emoji": "📦📦📦", "desc": "5x Void Caches"},
    {"name": "Relic Pair", "crate": "relic", "bundle": 2, "emoji": "🔮🔮", "desc": "2x Eldritch Relics"},
    {"name": "Relic Bundle", "crate": "relic", "bundle": 3, "emoji": "🔮🔮🔮", "desc": "3x Eldritch Relics"},
    {"name": "Treasure Hunt", "crate": "treasure", "bundle": 2, "emoji": "👑👑", "desc": "2x Abyssal Treasures"},
    {"name": "Starter Pack", "crate": "cache", "bundle": 3, "emoji": "🎁", "desc": "3x Void Caches — beginner friendly!"},
    {"name": "Hunter's Bundle", "crate": "relic", "bundle": 2, "emoji": "⚔️", "desc": "2x Eldritch Relics — for the dedicated"},
    {"name": "Void Hoard", "crate": "treasure", "bundle": 3, "emoji": "💎", "desc": "3x Abyssal Treasures — the deep rewards patience"},
    {"name": "Mixed Cache", "crate": "mixed_cache", "bundle": 1, "emoji": "🎲", "desc": "1x Cache + 1x Relic — a bit of both"},
    {"name": "Mixed Relic", "crate": "mixed_relic", "bundle": 1, "emoji": "🎰", "desc": "1x Relic + 1x Treasure — high risk, high reward"},
]


def _today_str() -> str:
    return today_key()


def _stable_seed(*parts: object) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(sha256(payload).digest()[:8], "big")


def _build_daily_crate_deals(date: str) -> list[dict[str, object]]:
    rng = random.Random(_stable_seed("crate_shop", date))
    deals: list[dict[str, object]] = []

    for i in range(6):
        crate = rng.choice(_CRATE_SHOP_DEALS)
        discount = rng.randint(10, 35)
        mult = (100 - discount) / 100
        orig_s = int(crate["base_souls"])
        orig_g = int(crate["base_gems"])
        disc_s = max(0, int(orig_s * mult))
        disc_g = max(0, int(orig_g * mult))
        deals.append({
            "slot": i, "item_key": crate["key"], "item_name": crate["name"],
            "bundle_size": 1, "emoji": crate["emoji"], "deal_type": "crate",
            "original_souls": orig_s, "original_gems": orig_g,
            "discounted_souls": disc_s, "discounted_gems": disc_g,
            "discount_pct": discount, "purchased": 0,
        })

    crate_lookup = {c["key"]: c for c in _CRATE_SHOP_DEALS}
    for i in range(6):
        bundle = rng.choice(_BUNDLE_TEMPLATES)
        base = crate_lookup.get(str(bundle["crate"]))
        if not base and bundle["crate"].startswith("mixed_"):
            discount = rng.randint(20, 50)
            if bundle["crate"] == "mixed_cache":
                orig_s = 500 + 5000
                orig_g = 0 + 30
            else:
                orig_s = 5000 + 25000
                orig_g = 30 + 150
        elif base:
            discount = rng.randint(15, 45)
            orig_s = int(base["base_souls"]) * int(bundle["bundle"])
            orig_g = int(base["base_gems"]) * int(bundle["bundle"])
        else:
            discount = 20
            orig_s = 1000
            orig_g = 10
        mult = (100 - discount) / 100
        disc_s = max(0, int(orig_s * mult))
        disc_g = max(0, int(orig_g * mult))
        deals.append({
            "slot": 6 + i, "item_key": bundle["crate"], "item_name": bundle["name"],
            "bundle_size": int(bundle["bundle"]),
            "emoji": bundle.get("emoji", "🎁"),
            "desc": bundle.get("desc", ""), "deal_type": "bundle",
            "original_souls": orig_s, "original_gems": orig_g,
            "discounted_souls": disc_s, "discounted_gems": disc_g,
            "discount_pct": discount, "purchased": 0,
        })

    return deals


def _same_deal_shape(row: sqlite3.Row, deal: dict[str, object]) -> bool:
    fields = (
        "slot", "item_key", "item_name", "bundle_size", "original_souls",
        "original_gems", "discounted_souls", "discounted_gems", "discount_pct",
    )
    for field in fields:
        if str(row[field]) != str(deal[field]):
            return False
    return True


async def get_or_create_daily_deals(db: BotDatabase, user_id: int) -> list[dict[str, object]]:
    today = _today_str()
    deals = _build_daily_crate_deals(today)
    existing = await db.fetchall(
        "SELECT * FROM rpg_crate_shop WHERE user_id = ? AND date = ? ORDER BY slot ASC",
        (user_id, today),
    )
    if len(existing) == len(deals) and all(_same_deal_shape(row, deals[i]) for i, row in enumerate(existing)):
        return [dict(r) for r in existing]

    if existing:
        await db.execute(
            "DELETE FROM rpg_crate_shop WHERE user_id = ? AND date = ?",
            (user_id, today),
        )

    for deal in deals:
        await db.execute(
            """INSERT OR REPLACE INTO rpg_crate_shop
               (user_id, date, slot, item_key, item_name, bundle_size,
                original_souls, original_gems, discounted_souls, discounted_gems, discount_pct, purchased)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (user_id, today, deal["slot"], deal["item_key"], deal["item_name"],
             deal["bundle_size"], deal["original_souls"], deal["original_gems"],
             deal["discounted_souls"], deal["discounted_gems"], deal["discount_pct"]),
        )

    return deals


async def purchase_shop_deal(db: BotDatabase, user_id: int, slot: int, currency: str) -> dict[str, object]:
    raise ValueError("Weapon crate purchases now use Weapon Shards. Use `b shardcrate <cache|relic|treasure>`.")

    today = _today_str()
    row = await db.fetchone(
        "SELECT * FROM rpg_crate_shop WHERE user_id = ? AND date = ? AND slot = ?",
        (user_id, today, slot),
    )
    if not row:
        raise ValueError("Deal not found or expired.")
    if row["purchased"]:
        raise ValueError("Already purchased this deal today.")

    player = await ensure_player(db, user_id, "")
    souls = int(player["gold"])
    gems = int(player["gems"])

    if currency == "souls":
        cost = int(row["discounted_souls"])
        if cost > 0 and souls < cost:
            raise ValueError(f"Need **{cost:,}** Souls, you have **{souls:,}**.")
    elif currency == "gems":
        cost = int(row["discounted_gems"])
        if cost <= 0:
            raise ValueError("This deal cannot be bought with Gems.")
        if gems < cost:
            raise ValueError(f"Need **{cost}** Gems, you have **{gems}**.")
    else:
        raise ValueError("Currency must be `souls` or `gems`.")

    if currency == "souls":
        await award_currency(db, user_id, gold=-cost)
    else:
        await award_currency(db, user_id, gems=-cost)

    await db.execute(
        "UPDATE rpg_crate_shop SET purchased = 1 WHERE user_id = ? AND date = ? AND slot = ?",
        (user_id, today, slot),
    )

    item_key = str(row["item_key"])
    bundle_size = int(row["bundle_size"])
    results: list[dict[str, object]] = []

    if item_key in ("mixed_cache", "mixed_relic"):
        if item_key == "mixed_cache":
            opens = [("cache", 1), ("relic", 1)]
        else:
            opens = [("relic", 1), ("treasure", 1)]
        for ck, cnt in opens:
            for _ in range(cnt):
                r = await open_crate(db, user_id, ck)
                results.append(r)
    else:
        for _ in range(bundle_size):
            r = await open_crate(db, user_id, item_key)
            results.append(r)

    merged: dict[str, object] = {"gold": 0, "gems": 0, "materials": {}, "swords": 0, "weapons": []}
    for r in results:
        merged["gold"] = int(merged["gold"]) + int(r.get("gold", 0))
        merged["gems"] = int(merged["gems"]) + int(r.get("gems", 0))
        merged["swords"] = int(merged["swords"]) + int(r.get("swords", 0))
        for mk, mv in r.get("materials", {}).items():
            merged["materials"][mk] = merged["materials"].get(mk, 0) + mv
        merged["weapons"].extend(r.get("weapons", []))

    return merged
