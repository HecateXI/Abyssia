import asyncio
import sqlite3
from pathlib import Path
from typing import Any


class BotDatabase:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        await self._execute_script(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY (guild_id, key)
            );
            CREATE TABLE IF NOT EXISTS booster_roles (
                guild_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, member_id)
            );
            CREATE TABLE IF NOT EXISTS patreon_members (
                guild_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                tier INTEGER NOT NULL DEFAULT 1,
                note TEXT NOT NULL DEFAULT '',
                updated_at INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, member_id)
            );
            CREATE TABLE IF NOT EXISTS command_invocations (
                dedupe_key TEXT NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                command_name TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mod_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS rpg_players (
                user_id INTEGER NOT NULL PRIMARY KEY,
                hunter_name TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1,
                xp INTEGER NOT NULL DEFAULT 0,
                gold INTEGER NOT NULL DEFAULT 250,
                gems INTEGER NOT NULL DEFAULT 25,
                strength INTEGER NOT NULL DEFAULT 1,
                dexterity INTEGER NOT NULL DEFAULT 1,
                luck INTEGER NOT NULL DEFAULT 1,
                wisdom INTEGER NOT NULL DEFAULT 1,
                endurance INTEGER NOT NULL DEFAULT 1,
                unspent_points INTEGER NOT NULL DEFAULT 0,
                current_zone TEXT NOT NULL DEFAULT 'forgotten_woods',
                equipped_weapon TEXT NOT NULL DEFAULT 'rusted_sword',
                equipped_charm TEXT,
                arena_rating INTEGER NOT NULL DEFAULT 1000,
                prestige INTEGER NOT NULL DEFAULT 0,
                title TEXT NOT NULL DEFAULT 'Void Hunter',
                hunts_done INTEGER NOT NULL DEFAULT 0,
                last_hunt_at INTEGER NOT NULL DEFAULT 0,
                last_daily_at INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rpg_creatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                rarity TEXT NOT NULL,
                attack INTEGER NOT NULL DEFAULT 0,
                defense INTEGER NOT NULL DEFAULT 0,
                hp INTEGER NOT NULL,
                speed INTEGER NOT NULL DEFAULT 1,
                crit INTEGER NOT NULL DEFAULT 5,
                mana INTEGER NOT NULL DEFAULT 200,
                str_stat INTEGER NOT NULL DEFAULT 1,
                pr_stat INTEGER NOT NULL DEFAULT 1,
                wp_stat INTEGER NOT NULL DEFAULT 1,
                mag_stat INTEGER NOT NULL DEFAULT 1,
                mr_stat INTEGER NOT NULL DEFAULT 1,
                spd INTEGER NOT NULL DEFAULT 1,
                role TEXT NOT NULL DEFAULT 'Balanced',
                ability TEXT NOT NULL,
                value INTEGER NOT NULL DEFAULT 10,
                image TEXT,
                level INTEGER NOT NULL DEFAULT 1,
                xp INTEGER NOT NULL DEFAULT 0,
                caught_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_creatures_owner ON rpg_creatures (user_id);
            CREATE TABLE IF NOT EXISTS rpg_inventory (
                user_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_key TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, item_type, item_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_autohunts (
                user_id INTEGER NOT NULL PRIMARY KEY,
                zone_key TEXT NOT NULL,
                duration_hours INTEGER NOT NULL,
                started_at INTEGER NOT NULL,
                ends_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rpg_teams (
                user_id INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                creature_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, slot)
            );
            CREATE TABLE IF NOT EXISTS rpg_battle_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                winner_id INTEGER NOT NULL,
                loser_id INTEGER NOT NULL,
                rating_change INTEGER NOT NULL,
                summary TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rpg_quests (
                user_id INTEGER NOT NULL,
                quest_key TEXT NOT NULL,
                period_key TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                claimed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, quest_key, period_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_daily_checklists (
                user_id INTEGER NOT NULL,
                period_key TEXT NOT NULL,
                daily_claimed INTEGER NOT NULL DEFAULT 0,
                hunt_lootboxes INTEGER NOT NULL DEFAULT 0,
                battle_crates INTEGER NOT NULL DEFAULT 0,
                reward_claimed INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, period_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_achievements (
                user_id INTEGER NOT NULL,
                achievement_key TEXT NOT NULL,
                unlocked_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, achievement_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_raid_state (
                guild_id INTEGER PRIMARY KEY,
                boss_key TEXT NOT NULL,
                hp INTEGER NOT NULL,
                max_hp INTEGER NOT NULL,
                started_at INTEGER NOT NULL,
                ends_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rpg_raid_damage (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                damage INTEGER NOT NULL DEFAULT 0,
                attacks INTEGER NOT NULL DEFAULT 0,
                last_attack_at INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS rpg_market_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_key TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rpg_market_guild ON rpg_market_listings (guild_id, created_at);
            CREATE TABLE IF NOT EXISTS rpg_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                proposer_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                offer_type TEXT NOT NULL,
                offer_key TEXT NOT NULL,
                offer_quantity INTEGER NOT NULL,
                request_type TEXT NOT NULL,
                request_key TEXT NOT NULL,
                request_quantity INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rpg_shop_rotation (
                guild_id INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_key TEXT NOT NULL,
                price INTEGER NOT NULL,
                date TEXT NOT NULL,
                PRIMARY KEY (guild_id, slot, date)
            );
            CREATE TABLE IF NOT EXISTS rpg_active_buffs (
                user_id INTEGER NOT NULL,
                buff_key TEXT NOT NULL,
                buff_type TEXT NOT NULL,
                charges_remaining INTEGER NOT NULL DEFAULT 0,
                activated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, buff_key)
            );
            CREATE TABLE IF NOT EXISTS rpg_profile_cosmetics (
                user_id INTEGER NOT NULL PRIMARY KEY,
                background_key TEXT NOT NULL DEFAULT '',
                accent_color TEXT NOT NULL DEFAULT '',
                about TEXT NOT NULL DEFAULT '',
                updated_at INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        await self._migrate_schema()

    async def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def _migrate_to_global(self) -> None:
        """Migrate RPG tables from guild-scoped to user-global (user_id PK)."""

        # ── rpg_players: PK(guild_id, user_id) → PK(user_id) ──
        cursor = self.conn.execute("PRAGMA table_info(rpg_players)")
        col_info = {row["name"]: row for row in cursor.fetchall()}
        if col_info and "guild_id" in {name for name, info in col_info.items() if info["pk"]}:
            self.conn.executescript("""
                CREATE TABLE rpg_players_new (
                    user_id INTEGER NOT NULL PRIMARY KEY,
                    hunter_name TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 1,
                    xp INTEGER NOT NULL DEFAULT 0,
                    gold INTEGER NOT NULL DEFAULT 250,
                    gems INTEGER NOT NULL DEFAULT 25,
                    strength INTEGER NOT NULL DEFAULT 1,
                    dexterity INTEGER NOT NULL DEFAULT 1,
                    luck INTEGER NOT NULL DEFAULT 1,
                    wisdom INTEGER NOT NULL DEFAULT 1,
                    endurance INTEGER NOT NULL DEFAULT 1,
                    unspent_points INTEGER NOT NULL DEFAULT 0,
                    current_zone TEXT NOT NULL DEFAULT 'forgotten_woods',
                    equipped_weapon TEXT NOT NULL DEFAULT 'rusted_sword',
                    equipped_charm TEXT,
                    arena_rating INTEGER NOT NULL DEFAULT 1000,
                    prestige INTEGER NOT NULL DEFAULT 0,
                    title TEXT NOT NULL DEFAULT 'Void Hunter',
                    hunts_done INTEGER NOT NULL DEFAULT 0,
                    last_hunt_at INTEGER NOT NULL DEFAULT 0,
                    last_daily_at INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                INSERT INTO rpg_players_new (user_id, hunter_name, level, xp, gold, gems,
                    strength, dexterity, luck, wisdom, endurance, unspent_points,
                    current_zone, equipped_weapon, equipped_charm, arena_rating, prestige,
                    title, hunts_done, last_hunt_at, last_daily_at, created_at, updated_at)
                SELECT user_id, hunter_name, level, xp, gold, gems,
                    strength, dexterity, luck, wisdom, endurance, unspent_points,
                    current_zone, equipped_weapon, equipped_charm, arena_rating, prestige,
                    title, hunts_done, last_hunt_at, last_daily_at, created_at, updated_at
                FROM rpg_players
                WHERE (user_id, updated_at) IN (
                    SELECT user_id, MAX(updated_at) FROM rpg_players GROUP BY user_id
                );
                DROP TABLE rpg_players;
                ALTER TABLE rpg_players_new RENAME TO rpg_players;
            """)

        # ── rpg_inventory: PK(guild_id, user_id, ...) → PK(user_id, ...) ──
        inv_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_inventory)")}
        if "guild_id" in inv_cols:
            self.conn.executescript("""
                CREATE TABLE rpg_inventory_new (
                    user_id INTEGER NOT NULL,
                    item_type TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, item_type, item_key)
                );
                INSERT INTO rpg_inventory_new (user_id, item_type, item_key, quantity)
                SELECT user_id, item_type, item_key, SUM(quantity)
                FROM rpg_inventory GROUP BY user_id, item_type, item_key;
                DROP TABLE rpg_inventory;
                ALTER TABLE rpg_inventory_new RENAME TO rpg_inventory;
            """)

        team_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_teams)")}
        if "guild_id" in team_cols:
            self.conn.executescript("""
                CREATE TABLE rpg_teams_new (
                    user_id INTEGER NOT NULL,
                    slot INTEGER NOT NULL,
                    creature_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, slot)
                );
                INSERT INTO rpg_teams_new (user_id, slot, creature_id)
                SELECT user_id, slot, creature_id
                FROM rpg_teams
                WHERE (user_id, slot, creature_id) IN (
                    SELECT user_id, slot, MAX(creature_id) FROM rpg_teams GROUP BY user_id, slot
                );
                DROP TABLE rpg_teams;
                ALTER TABLE rpg_teams_new RENAME TO rpg_teams;
            """)

        auto_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_autohunts)")}
        if "guild_id" in auto_cols:
            self.conn.executescript("""
                CREATE TABLE rpg_autohunts_new (
                    user_id INTEGER NOT NULL PRIMARY KEY,
                    zone_key TEXT NOT NULL,
                    duration_hours INTEGER NOT NULL,
                    started_at INTEGER NOT NULL,
                    ends_at INTEGER NOT NULL
                );
                INSERT INTO rpg_autohunts_new (user_id, zone_key, duration_hours, started_at, ends_at)
                SELECT user_id, zone_key, duration_hours, started_at, ends_at
                FROM rpg_autohunts
                WHERE (user_id, started_at) IN (
                    SELECT user_id, MAX(started_at) FROM rpg_autohunts GROUP BY user_id
                );
                DROP TABLE rpg_autohunts;
                ALTER TABLE rpg_autohunts_new RENAME TO rpg_autohunts;
            """)

        buff_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_active_buffs)")}
        if "guild_id" in buff_cols:
            self.conn.executescript("""
                CREATE TABLE rpg_active_buffs_new (
                    user_id INTEGER NOT NULL,
                    buff_key TEXT NOT NULL,
                    buff_type TEXT NOT NULL,
                    charges_remaining INTEGER NOT NULL DEFAULT 0,
                    activated_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, buff_key)
                );
                INSERT INTO rpg_active_buffs_new (user_id, buff_key, buff_type, charges_remaining, activated_at)
                SELECT user_id, buff_key, buff_type, charges_remaining, activated_at
                FROM rpg_active_buffs
                WHERE (user_id, buff_key, activated_at) IN (
                    SELECT user_id, buff_key, MAX(activated_at) FROM rpg_active_buffs GROUP BY user_id, buff_key
                );
                DROP TABLE rpg_active_buffs;
                ALTER TABLE rpg_active_buffs_new RENAME TO rpg_active_buffs;
            """)

        quest_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_quests)")}
        if "guild_id" in quest_cols:
            self.conn.executescript("""
                CREATE TABLE rpg_quests_new (
                    user_id INTEGER NOT NULL,
                    quest_key TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    claimed INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, quest_key, period_key)
                );
                INSERT INTO rpg_quests_new (user_id, quest_key, period_key, progress, claimed)
                SELECT user_id, quest_key, period_key, MAX(progress), claimed
                FROM rpg_quests GROUP BY user_id, quest_key, period_key;
                DROP TABLE rpg_quests;
                ALTER TABLE rpg_quests_new RENAME TO rpg_quests;
            """)

        ach_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_achievements)")}
        if "guild_id" in ach_cols:
            self.conn.executescript("""
                CREATE TABLE rpg_achievements_new (
                    user_id INTEGER NOT NULL,
                    achievement_key TEXT NOT NULL,
                    unlocked_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, achievement_key)
                );
                INSERT INTO rpg_achievements_new (user_id, achievement_key, unlocked_at)
                SELECT user_id, achievement_key, MIN(unlocked_at)
                FROM rpg_achievements GROUP BY user_id, achievement_key;
                DROP TABLE rpg_achievements;
                ALTER TABLE rpg_achievements_new RENAME TO rpg_achievements;
            """)

        shop_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_crate_shop)")}
        if "guild_id" in shop_cols:
            self.conn.executescript("""
                CREATE TABLE rpg_crate_shop_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    slot INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    bundle_size INTEGER NOT NULL DEFAULT 1,
                    original_souls INTEGER NOT NULL DEFAULT 0,
                    original_gems INTEGER NOT NULL DEFAULT 0,
                    discounted_souls INTEGER NOT NULL DEFAULT 0,
                    discounted_gems INTEGER NOT NULL DEFAULT 0,
                    discount_pct INTEGER NOT NULL DEFAULT 0,
                    purchased INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(user_id, date, slot)
                );
                INSERT INTO rpg_crate_shop_new
                    (id, user_id, date, slot, item_key, item_name, bundle_size,
                     original_souls, original_gems, discounted_souls, discounted_gems, discount_pct, purchased)
                SELECT id, user_id, date, slot, item_key, item_name, bundle_size,
                    original_souls, original_gems, discounted_souls, discounted_gems, discount_pct, purchased
                FROM rpg_crate_shop;
                DROP TABLE rpg_crate_shop;
                ALTER TABLE rpg_crate_shop_new RENAME TO rpg_crate_shop;
            """)

        # ── rpg_creatures: remove guild_id ──
        creature_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_creatures)").fetchall()}
        if "guild_id" in creature_cols:
            self.conn.executescript("""
                DROP TABLE IF EXISTS rpg_creatures_new;
                CREATE TABLE rpg_creatures_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    attack INTEGER NOT NULL,
                    defense INTEGER NOT NULL,
                    hp INTEGER NOT NULL,
                    speed INTEGER NOT NULL,
                    crit INTEGER NOT NULL DEFAULT 5,
                    mana INTEGER NOT NULL DEFAULT 200,
                    ability TEXT NOT NULL,
                    value INTEGER NOT NULL DEFAULT 10,
                    image TEXT,
                    level INTEGER NOT NULL DEFAULT 1,
                    xp INTEGER NOT NULL DEFAULT 0,
                    caught_at INTEGER NOT NULL
                );
                INSERT INTO rpg_creatures_new
                    (id, user_id, name, rarity, attack, defense, hp, speed, crit, mana, ability, value, image, level, xp, caught_at)
                SELECT id, user_id, name, rarity, attack, defense, hp, speed, crit, mana, ability, value, image, level, xp, caught_at
                FROM rpg_creatures;
                DROP TABLE rpg_creatures;
                ALTER TABLE rpg_creatures_new RENAME TO rpg_creatures;
            """)

        # ── weapons: remove guild_id ──
        weapon_cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(weapons)").fetchall()}
        if "guild_id" in weapon_cols:
            self.conn.execute("DROP TABLE IF EXISTS weapons_new")
            # Build target table definition
            new_defs = [
                "id INTEGER PRIMARY KEY AUTOINCREMENT",
                "user_id INTEGER NOT NULL",
                "name TEXT NOT NULL",
                "rarity TEXT NOT NULL",
                "attack_bonus INTEGER NOT NULL DEFAULT 0",
                "defense_bonus INTEGER NOT NULL DEFAULT 0",
                "affixes TEXT NOT NULL DEFAULT '[]'",
                "equipped_creature_id INTEGER",
                "created_at INTEGER NOT NULL",
                "quality_pct INTEGER NOT NULL DEFAULT 50",
                "mana_cost INTEGER NOT NULL DEFAULT 3",
                "wear TEXT NOT NULL DEFAULT 'Unknown'",
            ]
            for col_name, ddl in [("weapon_type", "weapon_type TEXT NOT NULL DEFAULT 'sword'"),
                                   ("quality", "quality TEXT NOT NULL DEFAULT 'Normal'"),
                                   ("passive", "passive TEXT")]:
                if col_name in weapon_cols:
                    new_defs.append(ddl)
            # Columns present in both source and target
            target_cols = {d.split()[0] for d in new_defs}
            common = sorted((weapon_cols - {"guild_id"}) & target_cols)
            col_list = ", ".join(common)
            self.conn.execute(f"CREATE TABLE weapons_new ({', '.join(new_defs)})")
            if common:
                self.conn.execute(f"INSERT INTO weapons_new ({col_list}) SELECT {col_list} FROM weapons")
            self.conn.execute("DROP TABLE weapons")
            self.conn.execute("ALTER TABLE weapons_new RENAME TO weapons")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_weapons_owner ON weapons (user_id)")

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def _execute_script(self, script: str) -> None:
        async with self._lock:
            self.conn.executescript(script)
            self.conn.commit()

    async def _migrate_schema(self) -> None:
        async with self._lock:
            creature_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_creatures)").fetchall()}
            additions = {
                "crit": "INTEGER NOT NULL DEFAULT 5",
                "mana": "INTEGER NOT NULL DEFAULT 200",
                "value": "INTEGER NOT NULL DEFAULT 10",
                "image": "TEXT",
                "str_stat": "INTEGER NOT NULL DEFAULT 1",
                "pr_stat": "INTEGER NOT NULL DEFAULT 1",
                "wp_stat": "INTEGER NOT NULL DEFAULT 1",
                "mag_stat": "INTEGER NOT NULL DEFAULT 1",
                "mr_stat": "INTEGER NOT NULL DEFAULT 1",
                "spd": "INTEGER NOT NULL DEFAULT 1",
                "role": "TEXT NOT NULL DEFAULT 'Balanced'",
            }
            for column, ddl in additions.items():
                if column not in creature_columns:
                    self.conn.execute(f"ALTER TABLE rpg_creatures ADD COLUMN {column} {ddl}")
            shop_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_shop_rotation)").fetchall()}
            if not shop_columns:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS rpg_shop_rotation (
                        guild_id INTEGER NOT NULL,
                        slot INTEGER NOT NULL,
                        item_type TEXT NOT NULL,
                        item_key TEXT NOT NULL,
                        price INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        PRIMARY KEY (guild_id, slot, date)
                 )
            """)
            snapshot_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(rpg_team_snapshots)").fetchall()}
            snapshot_additions = {
                "weapon_type": "TEXT DEFAULT 'sword'",
                "weapon_quality": "TEXT DEFAULT 'Normal'",
                "weapon_passive": "TEXT",
            }
            for column, ddl in snapshot_additions.items():
                if snapshot_columns and column not in snapshot_columns:
                    self.conn.execute(f"ALTER TABLE rpg_team_snapshots ADD COLUMN {column} {ddl}")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS weapons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    attack_bonus INTEGER NOT NULL DEFAULT 0,
                    defense_bonus INTEGER NOT NULL DEFAULT 0,
                    affixes TEXT NOT NULL DEFAULT '[]',
                    equipped_creature_id INTEGER,
                    created_at INTEGER NOT NULL
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_weapons_owner ON weapons (user_id)")
            weapon_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(weapons)").fetchall()}
            weapon_additions = {
                "weapon_type": "TEXT NOT NULL DEFAULT 'sword'",
                "quality": "TEXT NOT NULL DEFAULT 'Normal'",
                "quality_pct": "INTEGER NOT NULL DEFAULT 50",
                "mana_cost": "INTEGER NOT NULL DEFAULT 3",
                "wear": "TEXT NOT NULL DEFAULT 'Unknown'",
                "passive": "TEXT",
                "stat_rolls": "TEXT",
                "is_favorite": "INTEGER NOT NULL DEFAULT 0",
            }
            for column, ddl in weapon_additions.items():
                if column not in weapon_columns:
                    self.conn.execute(f"ALTER TABLE weapons ADD COLUMN {column} {ddl}")
            # Battle system tables
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rpg_battle_queue (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    joined_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rpg_arena_stats (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL DEFAULT 1000,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    win_streak INTEGER NOT NULL DEFAULT 0,
                    highest_win_streak INTEGER NOT NULL DEFAULT 0,
                    total_battles INTEGER NOT NULL DEFAULT 0,
                    last_battle_at INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rpg_battle_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    opponent_name TEXT NOT NULL,
                    opponent_id INTEGER NOT NULL,
                    won INTEGER NOT NULL,
                    rating_change INTEGER NOT NULL DEFAULT 0,
                    opponent_rating INTEGER NOT NULL DEFAULT 1000,
                    is_npc INTEGER NOT NULL DEFAULT 0,
                    log TEXT NOT NULL DEFAULT '',
                    fought_at INTEGER NOT NULL
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_battle_history_user ON rpg_battle_history (user_id, fought_at DESC)")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rpg_team_snapshots (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    slot INTEGER NOT NULL,
                    creature_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    attack INTEGER NOT NULL,
                    defense INTEGER NOT NULL,
                    hp INTEGER NOT NULL,
                    speed INTEGER NOT NULL,
                    crit INTEGER NOT NULL DEFAULT 5,
                    mana INTEGER NOT NULL DEFAULT 200,
                    ability TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    weapon_id INTEGER,
                    weapon_name TEXT,
                    weapon_rarity TEXT,
                    weapon_attack_bonus INTEGER DEFAULT 0,
                    weapon_defense_bonus INTEGER DEFAULT 0,
                    weapon_affixes TEXT DEFAULT '[]',
                    weapon_type TEXT DEFAULT 'sword',
                    weapon_quality TEXT DEFAULT 'Normal',
                    weapon_passive TEXT,
                    PRIMARY KEY (user_id, slot)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rpg_seasons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    started_at INTEGER NOT NULL,
                    ends_at INTEGER NOT NULL,
                    active INTEGER NOT NULL DEFAULT 0
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rpg_season_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    season_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    rank INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    claimed INTEGER NOT NULL DEFAULT 0
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rpg_crate_shop (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    slot INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    bundle_size INTEGER NOT NULL DEFAULT 1,
                    original_souls INTEGER NOT NULL DEFAULT 0,
                    original_gems INTEGER NOT NULL DEFAULT 0,
                    discounted_souls INTEGER NOT NULL DEFAULT 0,
                    discounted_gems INTEGER NOT NULL DEFAULT 0,
                    discount_pct INTEGER NOT NULL DEFAULT 0,
                    purchased INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(user_id, date, slot)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rpg_profile_cosmetics (
                    user_id INTEGER NOT NULL PRIMARY KEY,
                    background_key TEXT NOT NULL DEFAULT '',
                    accent_color TEXT NOT NULL DEFAULT '',
                    about TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL DEFAULT 0
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rpg_user_prefs (
                    user_id INTEGER NOT NULL PRIMARY KEY,
                    battle_log INTEGER NOT NULL DEFAULT 0
                )
            """)
            await self._migrate_to_global()
            self.conn.commit()

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        async with self._lock:
            self.conn.execute(sql, params)
            self.conn.commit()

    async def insert(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        async with self._lock:
            cursor = self.conn.execute(sql, params)
            self.conn.commit()
            return int(cursor.lastrowid)

    async def claim_command_invocation(self, dedupe_key: str, user_id: int, command_name: str, created_at: int) -> bool:
        async with self._lock:
            self.conn.execute("DELETE FROM command_invocations WHERE created_at < ?", (created_at - 3600,))
            cursor = self.conn.execute(
                """
                INSERT OR IGNORE INTO command_invocations (dedupe_key, user_id, command_name, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (dedupe_key, user_id, command_name, created_at),
            )
            self.conn.commit()
            return cursor.rowcount == 1

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        async with self._lock:
            return self.conn.execute(sql, params).fetchone()

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        async with self._lock:
            return list(self.conn.execute(sql, params).fetchall())

    async def get_setting(self, guild_id: int, key: str) -> str | None:
        row = await self.fetchone("SELECT value FROM guild_settings WHERE guild_id = ? AND key = ?", (guild_id, key))
        return None if row is None else row["value"]

    async def set_setting(self, guild_id: int, key: str, value: str | None) -> None:
        if value is None:
            await self.execute("DELETE FROM guild_settings WHERE guild_id = ? AND key = ?", (guild_id, key))
            return
        await self.execute(
            """
            INSERT INTO guild_settings (guild_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, key) DO UPDATE SET value = excluded.value
            """,
            (guild_id, key, value),
        )
