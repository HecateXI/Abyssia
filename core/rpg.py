from __future__ import annotations

import json
import random
import sqlite3
import time
from hashlib import sha256
from datetime import datetime, timezone

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
    Sigil,
    Zone,
    normalize_key,
)


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
    choices = list(RARITIES[: max_index + 1])
    adjusted_weights: list[float] = []
    for index, rarity in enumerate(choices):
        bonus = 1.0 + rarity_bonus + (luck * 0.012 * index)
        adjusted_weights.append(max(1.0, rarity.weight * bonus / (1 + max(0, index - 2) * 0.18)))
    return random.choices([rarity.name for rarity in choices], weights=adjusted_weights, k=1)[0]


def choose_creature_template(rarity: str) -> CreatureTemplate:
    pool = [creature for creature in CREATURES if creature.rarity == rarity]
    if not pool:
        pool = list(CREATURES)
    return random.choice(pool)


def roll_creature_stats(template: CreatureTemplate, hunter_level: int) -> dict[str, int | str]:
    rarity = RARITY_BY_NAME[template.rarity]
    rarity_index = RARITY_INDEX[template.rarity]
    level = max(1, min(100, random.randint(max(1, hunter_level - 2), hunter_level + 2)))
    scaling = rarity.stat_multiplier * (1 + (level - 1) * 0.08)
    variance = random.uniform(0.90, 1.15)
    attack = max(1, round(template.attack * scaling * variance))
    defense = max(1, round(template.defense * scaling * variance))
    hp = max(1, round(template.hp * scaling * variance))
    speed = max(1, round(template.speed * scaling * variance))
    value = max(10, round((attack * 5 + defense * 4 + hp * 1.8 + speed * 5) * (1 + rarity_index * 0.38)))
    return {
        "name": template.name, "rarity": template.rarity,
        "attack": attack, "defense": defense, "hp": hp, "speed": speed,
        "crit": min(45, 5 + rarity_index * 2 + speed // 24),
        "mana": 35 + rarity_index * 8 + level,
        "ability": template.ability, "value": value,
        "image": normalize_key(template.name), "level": level,
    }


async def create_creature(db: BotDatabase, user_id: int, stats: dict[str, int | str]) -> int:
    return await db.insert(
        """INSERT INTO rpg_creatures (user_id, name, rarity, attack, defense, hp, speed, crit, mana, ability, value, image, level, xp, caught_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (user_id, stats["name"], stats["rarity"], stats["attack"], stats["defense"],
         stats["hp"], stats["speed"], stats["crit"], stats["mana"], stats["ability"],
         stats["value"], stats["image"], stats["level"], now_ts()),
    )


async def top_creatures(db: BotDatabase, user_id: int, limit: int = 3) -> list[sqlite3.Row]:
    return await db.fetchall(
        "SELECT * FROM rpg_creatures WHERE user_id = ? ORDER BY level DESC, attack + defense + hp + speed DESC, id ASC LIMIT ?",
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


def _quality_label(quality_pct: int) -> str:
    if quality_pct >= 95:
        return "Ancient"
    if quality_pct >= 85:
        return "Masterwork"
    if quality_pct >= 70:
        return "Superior"
    if quality_pct >= 55:
        return "Fine"
    return "Normal"


def _quality_multiplier(quality_pct: int) -> float:
    return 0.65 + _clamp(quality_pct, 1, 100) * 0.009


def _roll_wear() -> str:
    return random.choices(list(WEAPON_WEAR_STAGES), weights=[8, 18, 31, 31, 12], k=1)[0]


def _degrade_wear(wear: str) -> str:
    stages = list(WEAPON_WEAR_STAGES)
    if wear not in stages:
        return "Unknown"
    return stages[min(len(stages) - 1, stages.index(wear) + 1)]


def _roll_quality_pct(wear: str) -> int:
    tier = _roll_quality()
    ranges = {
        "Normal": (35, 60),
        "Fine": (55, 74),
        "Superior": (70, 86),
        "Masterwork": (82, 95),
        "Ancient": (92, 100),
    }
    low, high = ranges.get(str(tier["name"]), (35, 60))
    return _clamp(random.randint(low, high) + WEAPON_WEAR_BONUS.get(wear, 0), 1, 100)


def _roll_mana_cost(rarity_index: int, quality_pct: int) -> int:
    base = max(1, 6 - min(4, rarity_index // 3))
    quality_discount = 1 if quality_pct >= 85 else 0
    return _clamp(base + random.randint(-1, 2) - quality_discount, 1, 7)


def _roll_affixes(rarity_index: int, quality_mult: float, affix_keys: list[str] | None = None) -> list[dict[str, object]]:
    if affix_keys is None:
        keys = list(WEAPON_AFFIXES.keys())
        random.shuffle(keys)
        keys = keys[:WEAPON_AFFIX_COUNTS[rarity_index]]
    else:
        keys = [key for key in affix_keys if key in WEAPON_AFFIXES]

    affixes: list[dict[str, object]] = []
    for key in keys:
        af = WEAPON_AFFIXES[key]
        val = max(1, int(random.randint(int(af["min"]), int(af["max"])) * quality_mult))
        affixes.append({"stat": key, "value": val, "fmt": str(af["fmt"]).format(val)})
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
    wtype_key = wtype_key if wtype_key in WEAPON_TYPES else random.choice(list(WEAPON_TYPES.keys()))
    wtype = WEAPON_TYPES[wtype_key]
    if name is None:
        prefix = random.choice(WEAPON_NAME_PREFIX)
        suffix = random.choice(WEAPON_NAME_SUFFIX.get(wtype_key, ["Blade"]))
        name = f"{prefix} {suffix}"
    wear = wear if wear in WEAPON_WEAR_STAGES else _roll_wear()
    quality_pct = _roll_quality_pct(wear)
    quality_mult = _quality_multiplier(quality_pct)

    base_atk = random.randint(int(wtype["atk_range"][0]), int(wtype["atk_range"][1]))
    base_def = random.randint(int(wtype["def_range"][0]), int(wtype["def_range"][1]))
    atk = max(1, int((base_atk + WEAPON_BASE_ATTACK[rarity_index] * 0.6) * quality_mult))
    defense = max(0, int((base_def + WEAPON_BASE_DEFENSE[rarity_index] * 0.6) * quality_mult))
    passive = None if keep_no_passive and passive_key is None else _roll_passive(wtype_key, rarity_index, passive_key)
    affixes = _roll_affixes(rarity_index, quality_mult, affix_keys)

    return {
        "user_id": user_id,
        "name": name,
        "rarity": rarity,
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
    quality = str(row_get(weapon_row, "quality", "Normal"))
    name = str(row_get(weapon_row, "name", "?"))
    if quality == "Normal":
        return name
    return f"{quality} {name}"


async def insert_weapon(db: BotDatabase, weapon: dict[str, object]) -> int:
    return await db.insert(
        """INSERT INTO weapons
           (user_id, name, rarity, weapon_type, quality, quality_pct, mana_cost, wear,
            attack_bonus, defense_bonus, passive, affixes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (weapon["user_id"], weapon["name"], weapon["rarity"],
         weapon.get("weapon_type", "sword"), weapon.get("quality", "Normal"),
         weapon.get("quality_pct", 50), weapon.get("mana_cost", 3), weapon.get("wear", "Unknown"),
         weapon["attack_bonus"], weapon["defense_bonus"],
         weapon.get("passive"), weapon["affixes"], weapon["created_at"]),
    )


async def ensure_weapon_passives(db: BotDatabase) -> int:
    rows = await db.fetchall("SELECT * FROM weapons WHERE passive IS NULL OR passive = ''")
    updated = 0
    for row in rows:
        rarity = str(row_get(row, "rarity", "Common"))
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
    return await db.fetchall("SELECT * FROM weapons WHERE user_id = ? ORDER BY rarity DESC, id DESC", (user_id,))


def weapon_salvage_shards(weapon_row) -> int:
    rarity_index = RARITY_INDEX.get(str(row_get(weapon_row, "rarity", "Common")), 0)
    quality_pct = int(row_get(weapon_row, "quality_pct", 50))
    base = [5, 8, 14, 24, 40, 65, 100, 150, 220, 320, 450, 550, 700, 900]
    return base[min(rarity_index, len(base) - 1)] + max(0, quality_pct // 20)


def weapon_reroll_cost(weapon_row, mode: str) -> int:
    rarity_index = RARITY_INDEX.get(str(row_get(weapon_row, "rarity", "Common")), 0)
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

    rarity = str(row_get(row, "rarity", "Common"))
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
               SET quality = ?, quality_pct = ?, mana_cost = ?, wear = ?,
                   attack_bonus = ?, defense_bonus = ?, passive = ?, affixes = ?
               WHERE id = ? AND user_id = ?""",
            (
                rolled["quality"], rolled["quality_pct"], rolled["mana_cost"], rolled["wear"],
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
        await add_item(db, user_id, "material", WEAPON_SHARD_KEY, -cost)
        await db.execute(
            """UPDATE weapons
               SET quality = ?, quality_pct = ?, mana_cost = ?, wear = ?, passive = ?
               WHERE id = ? AND user_id = ?""",
            (
                _quality_label(quality_pct), quality_pct, _roll_mana_cost(rarity_index, quality_pct),
                wear, json.dumps(passive) if passive else None, weapon_id, user_id,
            ),
        )
    elif mode_key in {"full", "all"}:
        rolled = _roll_weapon(user_id, rarity, wear=wear)
        await add_item(db, user_id, "material", WEAPON_SHARD_KEY, -cost)
        await db.execute(
            """UPDATE weapons
               SET name = ?, weapon_type = ?, quality = ?, quality_pct = ?, mana_cost = ?, wear = ?,
                   attack_bonus = ?, defense_bonus = ?, passive = ?, affixes = ?
               WHERE id = ? AND user_id = ?""",
            (
                rolled["name"], rolled["weapon_type"], rolled["quality"], rolled["quality_pct"],
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


def weapon_stats(weapon_row) -> dict[str, int]:
    if weapon_row is None:
        return {"attack": 0, "defense": 0}
    atk = int(row_get(weapon_row, "attack_bonus", 0))
    df = int(row_get(weapon_row, "defense_bonus", 0))
    stats = {"attack": atk, "defense": df}
    affixes_raw = row_get(weapon_row, "affixes", "[]")
    try:
        affixes = json.loads(str(affixes_raw))
    except Exception:
        affixes = []
    for a in affixes:
        s, v = str(a.get("stat", "")), int(a.get("value", 0))
        if s == "attack_flat":
            stats["attack"] = stats.get("attack", 0) + v
        elif s == "defense_flat":
            stats["defense"] = stats.get("defense", 0) + v
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
        if s in ("crit", "life_steal", "bleed", "burn", "stun", "shield", "poison", "soul_gain", "gem_finder", "xp_boost", "attack_pct", "defense_pct", "rare_finder"):
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
        "rarity": str(row_get(weapon_row, "rarity", "Common")),
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
    ws = weapon_stats(weapon_row)
    for s in ("attack", "defense"):
        cr[s] = int(cr.get(s, 0)) + ws.get(s, 0)
    for k, v in weapon_effects(weapon_row).items():
        if k == "attack_pct":
            cr["attack"] = int(cr.get("attack", 0)) * (100 + v) // 100
        elif k == "defense_pct":
            cr["defense"] = int(cr.get("defense", 0)) * (100 + v) // 100
        else:
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
            for s in ("attack", "defense"):
                cr[s] = int(cr.get(s, 0)) + ws.get(s, 0)
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
    from core.rpg_data import streak_multiplier
    mult = 1.0 + streak_multiplier(streak)
    if won:
        gold = round((160 + player_level * 12) * mult)
        gems = max(1, round(3 * mult))
        xp = round(75 * mult)
        return {"gold": gold, "gems": gems, "xp": xp}
    else:
        gold = round((40 + player_level * 4) * mult)
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
