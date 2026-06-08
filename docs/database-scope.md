# Database Schema Scope Review

## Global (user_id PK, no guild_id)

| Table | Notes |
|-------|-------|
| `rpg_players` | Player profile, stats, currency — global |
| `rpg_creatures` | Caught creatures — global |
| `rpg_inventory` | Items/materials — global |
| `weapons` | Weapon collection — global |
| `rpg_teams` | Team assignment — global |
| `rpg_autohunts` | Auto-hunt config — global |
| `rpg_active_buffs` | Sigils/charms — global |
| `rpg_quests` | Quest progress — global |
| `rpg_achievements` | Achievements — global |
| `rpg_crate_shop` | Daily crate deals — global |
| `rpg_profile_cosmetics` | Cosmetics — global |
| `rpg_user_prefs` | User preferences — global |

All migrated from `(guild_id, user_id)` → `(user_id)` via `_migrate_to_global()`.

## Guild-Scoped (has guild_id, non-RPG progress)

| Table | Justification |
|-------|---------------|
| `guild_settings` | Per-guild prefix/config — correct |
| `booster_roles` | Guild booster perks — correct |
| `patreon_members` | Guild patreon linking — correct |
| `mod_cases` | Guild moderation — correct |

## Guild-Scoped (competitive / PvP features)

| Table | Justification |
|-------|---------------|
| `rpg_battle_logs` | Per-guild battle records — acceptable |
| `rpg_raid_state` | Raid is guild-wide — correct |
| `rpg_raid_damage` | Raid damage tracking — correct |
| `rpg_market_listings` | Market per-guild — acceptable |
| `rpg_trades` | Trade per-guild — acceptable |
| `rpg_shop_rotation` | Shop per-guild — acceptable |
| `rpg_battle_queue` | Matchmaking per-guild — correct |
| `rpg_arena_stats` | Arena rating per-guild — correct |
| `rpg_battle_history` | Battle history per-guild — acceptable |
| `rpg_team_snapshots` | Team snapshot per-guild — acceptable |
| `rpg_seasons` | Arena seasons per-guild — correct |
| `rpg_season_rewards` | Season rewards per-guild — correct |
| `rpg_crate_shop` | Has guild_id column (but PK is user_id) — legacy, safe to keep |

## Assessment

**The split is correct.** Core RPG progress (creatures, weapons, currency, inventory, levels, quests, achievements, buffs) is global — a player keeps their stuff across servers. Competitive features (arena rating, battle history, market, trades, raids, shop rotation) remain guild-scoped because they're socially meaningful only within a server community.

**No changes needed.** The `_migrate_to_global()` function in `database.py` has already been run. New tables created after the migration use the correct PK pattern. Existing tables with `guild_id` in competitive/social features are intentional and should stay.
