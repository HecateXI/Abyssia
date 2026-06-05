# Goal
Strip away generic RPG complexity (stats, evolutions, traits, charms, quality tiers) and align Abyssia with OwO Bot's lean, addictive loop: hunt → sell → open crates → equip weapons → battle.

# Constraints & Preferences
- Do NOT turn Abyssia into a generic RPG, Diablo clone, or Pokémon clone
- Every major OwO feature must have a dark fantasy equivalent
- Core loop must mirror OwO exactly: hunt, collect monsters, sell duplicates, earn Souls, open crates, obtain weapons, build battle teams, battle players
- Weapons come primarily from crates, events, bosses, marketplace — NOT crafting
- Majority of monsters should become currency via sell/sellall (core economy driver)
- Souls are the primary currency for almost everything
- Crate opening should be a major dopamine system (3 tiers: Cache, Relic, Treasure)
- Battle uses teams of 3 monsters; weapons, levels, and team composition matter
- Help command should be a progression guide, not a command list
- Autohunt is the only feature that should go beyond OwO (offline progression, supplement not replace)
- Remove raid bosses, evolution/traits, stat allocation, charm system, crafting, old equipment system

# GLOBAL BATTLE SYSTEM (OWO STYLE)

## CRITICAL REQUIREMENT
When a player runs `!battle` they should NOT only battle friends. The system should automatically find another eligible player from the global playerbase. This creates a constant PvP ecosystem.

## MATCHMAKING FLOW
`!battle` → Matchmaking begins → Find another player currently in queue → Generate battle → Display results

## OFFLINE PLAYER BATTLES
If no live opponent exists, use saved teams from other players (their most recently saved team). This guarantees fast matchmaking, no waiting, and an active battle queue.

## NPC BATTLE SYSTEM
If matchmaking cannot find a suitable player, spawn AI-controlled hunters that appear as real hunters (not generic monsters). Examples: Gravekeeper Aldric, Soul Hunter Kael, The Hollow Knight, Void Apostle, Ashen Wanderer, The Crimson Reaper.

Each NPC has: Name, Rank, Arena Rating, Monster Team, Equipment, Titles.

## NPC DIFFICULTY SCALING
Scale NPCs to player power: Weak players get Beginner NPCs, Midgame players get Experienced Hunters, Endgame players get Legendary Hunters. The challenge should always feel fair.

## WIN STREAK SYSTEM
Track: Current Win Streak, Highest Win Streak, Season Win Streak. Each consecutive win increases rewards.
- 1 Win: +0%
- 3 Wins: +5%
- 5 Wins: +10%
- 10 Wins: +20%
- 20 Wins: +35%
- 50 Wins: +75%

Bonus rewards: Souls, Monster XP, Arena Rating, Crates, Materials.

Streak Milestones: 5 Wins (Minor Cache), 10 Wins (Rare Cache), 25 Wins (Epic Cache), 50 Wins (Legendary Cache), 100 Wins (Exclusive Title).

## BOUNTY SYSTEM
High win streak players become targets (e.g., "AbyssLord has reached a 42 win streak. Bonus rewards are available for defeating them.").

## RANKED MATCHMAKING
Match primarily using: Arena Rating, Team Power, Monster Levels. Prevents new players from facing veterans.

## ARENA RATING SYSTEM
Similar to Elo — gain rating for victories, lose rating for defeats. Ranks: Iron, Bronze, Silver, Gold, Platinum, Diamond, Master, Grandmaster, Abyssal Lord.

## BATTLE REWARDS
- Winning: Souls, Monster XP, Arena Rating, Materials, Crates, Achievements
- Losing: Reduced Souls, Reduced XP, Participation Rewards
Players should always feel progression.

## REVENGE SYSTEM
After losing, `!revenge` allows a rematch with the same opponent.

## BATTLE HISTORY
`!history` Shows: Recent Opponents, Wins, Losses, Rating Changes, Rewards Earned.

## TEAM POWER SYSTEM
Every team has a visible power score calculated from: Monster Levels, Monster Rarity, Monster Traits, Weapons, Charms, Ascensions.

## GLOBAL LEADERBOARDS
Track: Highest Arena Rating, Most Wins, Highest Win Streak, Most Battles, Most Souls, Collection Completion, Boss Kills.

## SEASONAL PVP REWARDS
Top 100, Top 10, and Rank #1 players getting exclusive titles, profile borders, cosmetics, or monster skins.

## BATTLE GOAL
Battle → Earn Rewards → Improve Team → Hunt More → Get Better Monsters → Get Better Weapons → Battle Again. Battling and hunting must constantly feed each other as the primary long-term progression loop.

# Progress
## Done
- Stripped evolution/traits from database schema (removed migration columns)
- Simplified database: weapons table now just id/guild/user/name/rarity/attack_bonus/defense_bonus/affixes/equipped_creature_id — no quality/speed/hp/templates
- Removed weapon_templates, charms, charm_templates tables from schema creation
- Removed EVOLUTION_COSTS, TRAIT_POOL, TRAIT_STAT_MAP, CHARM_TEMPLATES, CHARM_EFFECTS, QUALITY_NAMES, QUALITY_MULTIPLIERS, WEAPON_RARITY_QUALITY, RARITY_AFFIX_COUNTS, EQUIPMENT dict from rpg_data.py
- Replaced complex weapon system with simplified WEAPON_NAMES, WEAPON_AFFIXES (15 flat affixes), WEAPON_AFFIX_COUNTS, WEAPON_BASE_ATTACK/DEFENSE arrays indexed by rarity
- Replaced 5 crate types with 3: Void Cache (500g), Eldritch Relic (5000g+30gems), Abyssal Treasure (25000g+150gems) — each has weapon_chance, weapon_rarities, gold/gems/swords/materials
- Removed equipment_effects, pay_crafting_cost, equipment_display_name from rpg.py
- Removed roll_weapon_quality, roll_weapon_affix_count, roll_weapon_affix, generate_charm, insert_charm, player_charms, equip_charm_to_creature, unequip_charm, charm_for_creature, creature_charms, evolution_cost, roll_trait, apply_trait_bonuses, weapon_total_stats, weapon_special_effects, apply_weapon_to_creature, prepare_creatures_for_battle, charm_bonuses_for_player from rpg.py
- Added simplified generate_weapon (picks random name, base atk/def from arrays by rarity, rolls affixes from flat list capped by affix count)
- Added simplified weapon_stats, weapon_effects (reads affixes JSON from 'affixes' column)
- Added apply_weapon (applies +ATK/DEF, handles attack%/defense% percentage boosts)
- Added prepare_battle (returns battle-ready creature list with weapons applied)
- Added simplified open_crate (flat gold/gems/swords ranges, materials from all MATERIALS keys, single weapon roll at weapon_chance)
- Updated rpg_hunting.py: removed equipment_effects/charm_bonuses calls, replaced dexterity cooldown with level-based cooldown, simplified _hunt_roll to use player level directly
- Updated rpg_battle.py: replaced prepare_creatures_for_battle with prepare_battle, removed charm_bonuses_for_player import
- Updated rpg_profile.py: removed STAT_NAMES, removed estat/equip/craft/recipes/equipment/inspect commands, removed stats group commands, simplified profile/inventory commands
- Updated bot.py: registered rpg_equipment and rpg_shop cogs
- Fixed all command alias conflicts (renamed inv→armory, info→details, equip→weaponequip, unequip→weaponunequip, shop→crateshop, sell alias→sellcreature)
- Removed "Pokédex" terminology entirely (alias pokedex→vault, description changed)
- Crate drops now happen from hunts (4%+zone level+luck chance, zone-appropriate crate tier)
- Cleaned up dead code in rpg.py (old trait code, old open_crate, old weapon stat functions, charm_bonuses_for_player)
- Stripped rpg_equipment.py of charm commands, evolution commands, old weapon stats
- Fixed cards.py to remove CHARM_EFFECTS reference, quality/speed/hp/affixes_json references
- Added gambling commands (flip, roll) to rpg_shop.py

### In Progress
- Battle system overhaul (global matchmaking, NPCs, win streaks, arena rating, bounties, revenge, history, seasonal rewards)

### Blocked
- (none)

# Key Decisions
- Stripped stat allocation (Strength/Dexterity/Luck/Wisdom/Endurance) because OwO doesn't have it — player level is the only progression metric
- Removed evolution/traits because they add generic RPG complexity without matching OwO's simplicity
- Removed charms entirely (too complex, OwO doesn't have a separate charm slot)
- Reduced crates from 5 to 3 to mirror OwO's simple lootbox tiers
- Weapons no longer have quality tiers or speed/hp bonuses — just ATK, DEF, and affixes from a flat pool
- affixes column stores JSON array of {stat, value, fmt} objects
- Hunt cooldown now based purely on player level instead of dexterity stat
- !help should be rewritten as a progression guide (not yet done but mandated)
- Battle system must use global matchmaking, support offline player battles, NPC fallback, win streaks, arena rating, and seasonal rewards

# Next Steps
1. Implement global battle matchmaking system (queue, offline player teams, NPC fallback)
2. Add arena rating system with Elo-like mechanic and rank tiers
3. Add win streak tracking with bonuses and milestone rewards
4. Add bounty system for high-streak players
5. Add revenge command for rematches
6. Add battle history command
7. Add team power score calculation and display
8. Add PvP leaderboards
9. Add seasonal PvP rewards system
10. Add gambling commands (!flip, !roll) to rpg_economy.py
11. Rewrite !help as a step-by-step progression guide
12. Add marketplace/trading commands
13. Add quest system (generated daily quests: hunt 50, catch 10 rares, win 3 battles, sell 100 monsters)
14. Add daily command with mandatory login reward (Souls, crates, materials)
15. Add leaderboard commands (most Souls, most monsters, collection %, arena rating)

# Critical Context
- Base bot class: AbyssiaBot in bot.py using discord.py >=2.4.0 with hybrid commands
- Database: SQLite with WAL mode at data/bot.sqlite3
- 14 rarities: Common through Hidden
- Weapons table uses 'affixes' column (JSON array)
- No more EQUIPMENT dict, no more equipment_effects function (though some references remain in economy cog)
- Crate types: "cache" (500g), "relic" (5000g+30gems), "treasure" (25000g+150gems)
- Crates drop from hunts automatically and can be bought via !crateshop
- Weapon generation: random name from 10 names, base ATK/DEF from rarity-indexed arrays, affixes from 15 flat affixes

# Relevant Files
- C:\Users\HomeAdmin\Downloads\bot\core\database.py: Simplified schema (no evolution_tier/trait, simplified weapons table)
- C:\Users\HomeAdmin\Downloads\bot\core\rpg_data.py: Removed evolution, traits, charms, quality, old equipment; added simplified WEAPON_NAMES, WEAPON_AFFIXES, WEAPON_AFFIX_COUNTS, WEAPON_BASE_ATTACK/DEFENSE, simplified CRATE_TYPES
- C:\Users\HomeAdmin\Downloads\bot\core\rpg.py: Stripped ~500 lines of evolution/trait/charm/equipment/quality code; added simplified generate_weapon, weapon_stats, weapon_effects, apply_weapon, prepare_battle, simplified open_crate
- C:\Users\HomeAdmin\Downloads\bot\cogs\rpg_hunting.py: Removed equipment_effects/charm_bonuses calls, level-based cooldown, simplified _hunt_roll
- C:\Users\HomeAdmin\Downloads\bot\cogs\rpg_battle.py: Updated to use prepare_battle, removed charm_bonuses_for_player
- C:\Users\HomeAdmin\Downloads\bot\cogs\rpg_profile.py: Removed estat/equip/craft/recipes/inspect/stats commands, simplified profile/inventory
- C:\Users\HomeAdmin\Downloads\bot\cogs\rpg_economy.py: Existing sell/shop commands — needs gambling added
- C:\Users\HomeAdmin\Downloads\bot\cogs\rpg_equipment.py: Stripped charms/evolution, only weapon equip/unequip and creature detail remain
- C:\Users\HomeAdmin\Downloads\bot\cogs\rpg_shop.py: Crate shop, open, release, sellall, salvage, flip, roll commands
- C:\Users\HomeAdmin\Downloads\bot\bot.py: Updated COGS tuple with rpg_equipment, rpg_shop

# MULTI-HUNT SUPPORT

## Overview
Players can increase the number of monsters found per hunt using charms, sigils, relics, buffs, and other progression systems. The hunt card renderer supports both SINGLE HUNTS and MULTI HUNTS with tiered layouts.

## Layout Tiers

### Single Hunt (1 monster)
- Use the cinematic full-screen layout (existing `render_hunt_card`)
- Monster is the centerpiece with large portrait
- Large rarity banner and full reward presentation

### Loot Grid (2-5 monsters)
- Dedicated loot summary card with zone header
- Monster panels arranged in rows of 3
- Each panel: Portrait, Name, Rarity, Value, Collection Status
- Rare monsters visually stand out with glow borders
- Epic+ monsters have larger glows
- Legendary+ monsters receive special borders and particles
- Rarest monster gets a larger highlighted cell

### Compact Grid (6-10 monsters)
- Smaller cells in rows of 5
- Same visual hierarchy as Loot Grid
- Rarest monster still visually prominent

### Mass Hunt (10+ monsters)
- Compact inventory-style list rows
- Small icons with name, rarity bar, and value
- Discord-friendly dimensions (max ~1200px height)
- Rarest monster highlighted with accent row

## Rarity Priority
When multiple monsters are found, the rarest monster becomes the focal point:
- Larger or highlighted cell
- Player's eye drawn to the rarest reward immediately
- Visual hierarchy: Common < Uncommon < Rare < Epic < Legendary < Mythic < Ancient < Divine < Eldritch < Abyssal

## Summary Panel
Every multi-hunt card includes a summary panel showing:
- Total Souls Earned
- Total Materials Earned
- Rare Drops
- Special Loot (weapons, crates)

## Collection Status
- New discoveries: ✨ NEW badge with sparkle effect
- Duplicates: Muted DUPLICATE label
- Quick scanning optimized for fast grinding

## Design Goals
- Quick reward overview
- Easy rarity recognition
- Fast grinding experience
- Screenshot-worthy rare finds
- Discord-friendly image dimensions
