# Abyssia Discord Bot

Abyssia is a modular Discord.py bot with a dark fantasy monster-collecting RPG, moderation tools, booster-role management, a local content admin, and PNG-backed Discord game cards.

The RPG is inspired by addictive hunt/collection loops: quick hunts, rare capture moments, permanent monster collection, autohunt expeditions, teams, equipment, crafting, PvP, raids, markets, daily rewards, and profile/arena/card images generated with Pillow.

## Features

- Hunter profiles with level, XP, Souls, Void Gems, titles, stats, equipment, and generated profile cards.
- Hunting zones with level requirements, loot tables, materials, rarity caps, and PNG thumbnails.
- Monster collection with Common through Abyssal rarities, level, XP, HP, attack, defense, speed, crit, mana, value, ability, and image keys.
- Offline autohunt expeditions for 1, 4, 8, 12, or 24 hours with generated report cards.
- Crafting and equipment for weapons and charms with stat/economy effects.
- Summoning rituals that spend earned gems for boosted monster pulls.
- Teams of up to three monsters, button-based PvP duel challenges, auto battle simulation, arena ranks, and generated battle result cards.
- Daily rewards, daily quests, achievements, leaderboards, and server-wide boss raids.
- Shop, sell, player market, and direct item trades.
- Custom booster roles and moderation utilities.
- Local web admin for content overrides, asset uploads, guild settings, and runtime paths.
- SQLite persistence in `data/bot.sqlite3` with additive migrations for new RPG tables.
- Prefix commands and synced slash-compatible hybrid commands.

## Setup

1. Create a Discord application and bot at the Discord Developer Portal.
2. Enable these privileged gateway intents for the bot:
   - Server Members Intent
   - Message Content Intent
3. Invite the bot with these permissions:
   - Manage Roles
   - Kick Members
   - Ban Members
   - Moderate Members
   - Manage Messages
   - Manage Channels
   - Send Messages
   - Use Slash Commands
4. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

5. Copy `.env.example` to `.env` and add your bot token:

```powershell
Copy-Item .env.example .env
```

6. Run the bot:

```powershell
python bot.py
```

7. Optional: run the local content admin:

```powershell
python web_admin.py
```

Default admin URL: `http://127.0.0.1:8080`

## Assets

Abyssia loads PNGs from `data/assets` and through content overrides managed by the web admin.

Supported asset groups:

- `creatures`
- `equipment`
- `materials`
- `zones`
- `bosses`
- `rarity`
- `currency`
- `ui`

Set `PUBLIC_ASSET_BASE_URL` or use the admin setting when Discord needs public asset URLs instead of local file attachments.

## RPG Commands

### Start and progression

- `!start [hunter name]`
- `!profile [@member]`
- `!stats`
- `!stats allocate <strength|dexterity|luck|wisdom|endurance> [points]`
- `!daily`
- `!quest`
- `!quests claim`
- `!achievements`

### Hunting

- `!hunt [amount] [zone]`
- `!h [amount] [zone]`
- `!explore`
- `!explore <zone>`
- `!zones`
- `!autohunt`
- `!autohunt start <1|4|8|12|24> [zone]`
- `!autohunt claim`

### Collection, inventory, and crafting

- `!monsters [@member]`
- `!bestiary [@member]`
- `!inventory`
- `!equipment`
- `!recipes`
- `!craft <item>`
- `!equip <item>`
- `!inspect <item>`
- `!summon [1|5|10]`

### Economy

- `!shop`
- `!shop buy <item> [quantity]`
- `!sell <item|monster_id> [quantity]`
- `!market`
- `!market sell <material|equipment> <item> <quantity> <price>`
- `!market buy <listing_id>`
- `!market cancel <listing_id>`
- `!trade @member <offer_type> <offer_item> <offer_qty> <request_type> <request_item> <request_qty>`

### Battle, arena, and bosses

- `!team`
- `!team set <slot 1-3> <creature_id>`
- `!team clear`
- `!battle @user`
- `!duel @user`
- `!arena`
- `!leaderboard [rating|level|souls|gems|hunts]`
- `!boss`
- `!boss awaken`
- `!boss attack`
- `!raid`
- `!raid awaken`
- `!raid attack`

## Utility Commands

### Booster roles

- `!booster create <name> [#hex]`
- `!booster name <name>`
- `!booster color <#hex>`
- `!booster delete`
- `!booster sync`
- `!giveboosterrole @member`

### Admin config

- `!config`
- `!config prefix <prefix>`
- `!config modlog [#channel]`
- `!config welcome [#channel]`
- `!config booster-base [@role]`

### Moderation

- `!kick @member [reason]`
- `!ban @member [reason]`
- `!unban <user_id> [reason]`
- `!timeout @member <minutes> [reason]`
- `!untimeout @member [reason]`
- `!purge <1-100>`
- `!slowmode <seconds>`

## Notes

- RPG state is server-scoped. The same Discord user has separate progress in separate servers.
- The database keeps the historical `gold` column internally, but the UI presents that balance as Souls.
- `/hunt` rolls up to 3 monsters for free. Larger hunts spend temporary Hunt Sword charges, earned from `/daily`, hunting drops, or `/shop`.
- `/battle` and `/duel` animate turn by turn by editing generated battle cards about every 2 seconds.
- Existing databases are migrated additively on startup.
- Discord role hierarchy matters. Move the bot's highest role above any custom booster roles it creates or manages.
- Slash commands can take a minute to appear globally. Prefix commands work immediately.
