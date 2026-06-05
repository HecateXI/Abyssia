from __future__ import annotations

import random

import discord
from discord.ext import commands

from core.cards import render_autohunt_card
from core.hunt_card_renderer import HuntCardRenderer
from core.discord_assets import embed_asset, ensure_application_emojis
from core.items import HUNT_SWORD_KEY, HUNT_SWORD_NAME
from core.rpg import (
    HUNT_AUTOHUNT_MAX_ROLLS,
    HUNT_AUTOHUNT_ROLLS_PER_HOUR,
    HUNT_BASE_CATCH_RATE,
    HUNT_BASE_COOLDOWN_SECONDS,
    HUNT_BASE_CRATE_CHANCE,
    HUNT_LEVEL_COOLDOWN_REDUCTION,
    HUNT_LUCK_CATCH_BONUS,
    HUNT_LUCK_CRATE_BONUS,
    HUNT_MAX_CATCH_RATE,
    HUNT_MAX_CRATE_CHANCE,
    HUNT_MIN_COOLDOWN_SECONDS,
    HUNT_SWORD_DURATION_SECONDS,
    HUNT_SWORD_EXTRA_ROLLS,
    HUNT_ZONE_LEVEL_CRATE_BONUS,
    activate_buff,
    add_item,
    apply_charm,
    apply_sigil,
    award_currency,
    award_player_xp,
    choose_creature_template,
    choose_rarity,
    consume_buff,
    create_creature,
    creature_xp_for_level,
    ensure_player,
    get_active_buffs,
    get_quantity,
    get_zone,
    now_ts,
    progress_quest,
    readable_seconds,
    roll_checklist_hunt_lootboxes,
    roll_creature_stats,
    seconds_until_daily_reset,
    team_creatures,
    unlock_achievement,
    xp_for_level,
)
from core.rpg_data import CHARMS, CRATE_TYPES, SIGILS, ZONES, infused_name, normalize_key, roll_infused
from core.theme import (
    GOLD_COLOR,
    asset_emoji,
    consumable_label,
    crate_label,
    currency_label,
    creature_emoji,
    creature_line,
    dark_embed,
    material_label,
    progress_bar,
    rarity_emoji,
    rarity_color,
    rarity_label,
    rarity_level_badge,
    ui_label,
    zone_emoji,
    zone_label,
)


AUTOHUNT_DURATIONS = {1, 4, 8, 12, 24}

BASE_HUNT_ROLLS = 3
MAX_HUNT_ROLLS = 20


def _hunt_sword_label() -> str:
    return consumable_label(HUNT_SWORD_KEY, HUNT_SWORD_NAME)


def _daily_reset_timer() -> str:
    seconds = max(0, seconds_until_daily_reset())
    hours, rem = divmod(seconds, 3600)
    minutes, sec = divmod(rem, 60)
    return f"{hours}H {minutes}M {sec}S"


def _reward_display(reward: dict[str, object]) -> str:
    label = str(reward.get("label") or "Reward")
    kind = str(reward.get("kind") or "")
    key = str(reward.get("icon_key") or "")
    if kind == "currency" and key:
        return currency_label(key)
    if kind == "materials" and key:
        return material_label(key)
    if kind == "consumable" and key:
        return consumable_label(key, label)
    if kind and key:
        emoji = asset_emoji(kind, key)
        if emoji:
            return f"{emoji} {label}"
    return label


SWORD_BUFF_KEY = "hunt_sword"
SWORD_DURATION = HUNT_SWORD_DURATION_SECONDS


async def _check_sword_active(db, user_id: int) -> bool:
    """Check if Hunt Sword buff is active (within 20 min window)."""
    rows = await db.fetchall(
        "SELECT activated_at FROM rpg_active_buffs WHERE user_id = ? AND buff_key = ? AND charges_remaining > 0",
        (user_id, SWORD_BUFF_KEY),
    )
    if not rows:
        return False
    return True


async def _get_sword_activated_at(db, user_id: int) -> int:
    """Get the activation timestamp of the Hunt Sword buff."""
    rows = await db.fetchall(
        "SELECT activated_at FROM rpg_active_buffs WHERE user_id = ? AND buff_key = ? AND charges_remaining > 0",
        (user_id, SWORD_BUFF_KEY),
    )
    if not rows:
        return 0
    return int(rows[0]["activated_at"])


class ExploreZoneView(discord.ui.View):
    def __init__(self, ctx: commands.Context, player) -> None:
        super().__init__(timeout=60)
        self.ctx = ctx
        self.player = player
        self._add_options()

    def _add_options(self) -> None:
        level = int(self.player["level"])
        options = []
        for z in ZONES.values():
            unlocked = level >= z.required_level
            icon = zone_emoji(z.key)
            emoji = discord.PartialEmoji.from_str(icon) if icon else None
            desc = f"{'Current' if self.player['current_zone'] == z.key else ('Unlocked' if unlocked else f'Lv.{z.required_level}')}"
            options.append(discord.SelectOption(label=z.name, value=z.key, description=desc, emoji=emoji))
        self.zone_select.options = options

    @discord.ui.select(placeholder="Select a hunting zone...", options=[])
    async def zone_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        zone_key = select.values[0]
        zone = ZONES[zone_key]
        level = int(self.player["level"])
        if level < zone.required_level:
            await interaction.response.send_message(f"{zone.name} unlocks at level {zone.required_level}.", ephemeral=True)
            return
        db = self.ctx.bot.db
        await db.execute(
            "UPDATE rpg_players SET current_zone = ?, updated_at = ? WHERE user_id = ?",
            (zone_key, now_ts(), interaction.user.id),
        )
        self.zone_select.disabled = True
        embed = dark_embed("Route Marked", f"Current hunting zone set to {zone_label(zone_key)}.\n*{zone.flavor}*", color=GOLD_COLOR)
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id


class RPGHunting(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _award_hunt_team_xp(self, user_id: int, xp: int) -> tuple[list, dict[int, int]]:
        team = await team_creatures(self.bot.db, user_id)
        levelups: dict[int, int] = {}
        if not team or xp <= 0:
            return team, levelups
        for creature in team:
            level = int(creature["level"])
            stored_xp = int(creature["xp"]) + xp
            gained = 0
            while stored_xp >= creature_xp_for_level(level):
                stored_xp -= creature_xp_for_level(level)
                level += 1
                gained += 1
            await self.bot.db.execute(
                "UPDATE rpg_creatures SET level = ?, xp = ? WHERE id = ? AND user_id = ?",
                (level, stored_xp, int(creature["id"]), user_id),
            )
            if gained:
                levelups[int(creature["id"])] = gained
        return await team_creatures(self.bot.db, user_id), levelups

    async def _hunt_roll(self, user_id: int, player, zone, *, roll_index: int = 0, rarity_bonus: float = 0.0, allow_creature: bool = True) -> dict[str, object]:
        luck = int(player["luck"])
        level = int(player["level"])
        gold = random.randint(*zone.gold) + level * 5 + roll_index * 6
        gems = 0

        creature_id = None
        creature_stats = None
        if allow_creature:
            catch_rate = HUNT_BASE_CATCH_RATE + luck * HUNT_LUCK_CATCH_BONUS
            if random.random() < min(HUNT_MAX_CATCH_RATE, catch_rate):
                rarity = choose_rarity(zone, luck, rarity_bonus)
                template = choose_creature_template(rarity)
                creature_stats = roll_creature_stats(template, level)
                # Check for infused gem variant
                infused = roll_infused()
                if infused:
                    creature_stats["name"] = infused_name(str(creature_stats["name"]), str(infused["prefix"]))
                    creature_stats["value"] = int(int(creature_stats["value"]) * float(infused["multiplier"]))
                creature_id = await create_creature(self.bot.db, user_id, creature_stats)
                await progress_quest(self.bot.db, user_id, "daily_catches")
                await unlock_achievement(self.bot.db, user_id, "first_blood")
                if rarity not in ("Common", "Uncommon"):
                    await unlock_achievement(self.bot.db, user_id, "rare_keeper")

        xp = random.randint(25, 45) + zone.required_level * 4
        await award_currency(self.bot.db, user_id, gold=gold)
        return {
            "gold": gold, "gems": gems,
            "material_key": None, "material_amount": 0,
            "creature_id": creature_id, "creature": creature_stats, "xp": xp,
        }

    @commands.hybrid_command(name="hunt", aliases=["h"])
    async def hunt(self, ctx: commands.Context, *, zone: str | None = None) -> None:
        """Hunt for creatures. Active Hunt Sword grants +1 roll for 20 min."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        target_zone = get_zone(zone, player["current_zone"])
        if int(player["level"]) < target_zone.required_level:
            raise commands.BadArgument(f"{target_zone.name} unlocks at hunter level {target_zone.required_level}.")

        level = int(player["level"])
        cooldown = max(HUNT_MIN_COOLDOWN_SECONDS, round(HUNT_BASE_COOLDOWN_SECONDS - level * HUNT_LEVEL_COOLDOWN_REDUCTION))
        elapsed = now_ts() - int(player["last_hunt_at"])
        if elapsed < cooldown:
            raise commands.BadArgument(f"You are recovering from the hunt. Try again in {readable_seconds(cooldown - elapsed)}.")

        # Check if Hunt Sword buff is active (time-based, 20 min)
        sword_active = await _check_sword_active(self.bot.db, ctx.author.id)
        sword_count = HUNT_SWORD_EXTRA_ROLLS if sword_active else 0
        hunts_amount = 1 + sword_count

        total_gold = 0
        total_xp = 0
        materials: dict[str, int] = {}
        creatures: list[dict[str, object]] = []
        
        # Check active buffs
        active_buffs = await get_active_buffs(self.bot.db, ctx.author.id)
        sigil_extra = apply_sigil(active_buffs)
        rarity_bonus = apply_charm(active_buffs)
        
        for i in range(hunts_amount):
            # Sigil: roll extra monsters per hunt
            monster_rolls = 1 + sigil_extra
            for mi in range(monster_rolls):
                result = await self._hunt_roll(ctx.author.id, player, target_zone, roll_index=i, rarity_bonus=rarity_bonus)
                total_gold += int(result["gold"])
                total_xp += int(result["xp"])
                if result.get("material_key") and int(result.get("material_amount", 0)):
                    materials[str(result["material_key"])] = materials.get(str(result["material_key"]), 0) + int(result["material_amount"])
                if result["creature"]:
                    creatures.append(result["creature"])
        
        # Consume one charge from each active buff
        for bk in active_buffs:
            await consume_buff(self.bot.db, ctx.author.id, bk)

        found_crate = None
        crate_chance = HUNT_BASE_CRATE_CHANCE + target_zone.required_level * HUNT_ZONE_LEVEL_CRATE_BONUS + int(player["luck"]) * HUNT_LUCK_CRATE_BONUS
        if random.random() < min(HUNT_MAX_CRATE_CHANCE, crate_chance):
            crate_keys = list(CRATE_TYPES.keys())
            max_idx = min(len(crate_keys) - 1, max(0, (target_zone.required_level - 1) // 10))
            found_crate = crate_keys[random.randint(0, max_idx)]
            await add_item(self.bot.db, ctx.author.id, "crate", found_crate, 1)
        checklist_lootboxes, checklist_lootbox_count = await roll_checklist_hunt_lootboxes(self.bot.db, ctx.author.id, hunts_amount)

        player, levels = await award_player_xp(self.bot.db, player, total_xp)
        xp_team, _ = await self._award_hunt_team_xp(ctx.author.id, total_xp)
        await self.bot.db.execute(
            "UPDATE rpg_players SET hunts_done = hunts_done + ?, last_hunt_at = ?, updated_at = ? WHERE user_id = ?",
            (hunts_amount, now_ts(), now_ts(), ctx.author.id),
        )
        await progress_quest(self.bot.db, ctx.author.id, "daily_hunts", min(5, hunts_amount))
        if int(player["hunts_done"]) + hunts_amount >= 10:
            await unlock_achievement(self.bot.db, ctx.author.id, "ten_hunts")

        # ── Premium hunt card ──
        best_creature = None
        if creatures:
            rarity_order = {"Common": 0, "Uncommon": 1, "Rare": 2, "Epic": 3, "Legendary": 4, "Mythic": 5, "Ancient": 6, "Divine": 7, "Eldritch": 8, "Abyssal": 9}
            best_creature = max(creatures, key=lambda item: (rarity_order.get(str(item["rarity"]), 0), int(item["level"])))

        rewards_list = [
            {"label": "Souls", "amount": total_gold, "icon_key": "souls", "kind": "currency", "color": (235, 195, 80)},
            {"label": "XP", "amount": total_xp, "icon_key": "profile", "kind": "ui", "color": (250, 204, 21)},
        ]
        if sword_count:
            rewards_list.append({"label": f"{sword_count} Hunt Swords Used", "amount": 0, "icon_key": HUNT_SWORD_KEY, "kind": "consumable", "color": (90, 225, 130)})
        if levels:
            rewards_list.append({"label": "Levels", "amount": levels, "icon_key": "profile", "kind": "ui", "color": (250, 204, 21)})
        if checklist_lootboxes:
            rewards_list.append({
                "label": f"Lootbox [{checklist_lootbox_count}/3]",
                "amount": checklist_lootboxes,
                "icon_key": "cache",
                "kind": "crate",
                "color": (195, 150, 90),
            })
        active_buff_lines: list[str] = []
        for buff_key, charges in active_buffs.items():
            sigil = next((s for s in SIGILS if s.key == buff_key), None)
            charm = next((c for c in CHARMS if c.key == buff_key), None)
            item = sigil or charm
            if not item:
                continue
            remaining = max(0, int(charges) - 1)
            max_charges = max(1, int(item.charges))
            if sigil:
                color = (235, 80, 95)
            else:
                color = (120, 120, 240)
            icon = asset_emoji("buffs", buff_key)
            counter = f"`[{remaining}/{max_charges}]`"
            active_buff_lines.append(f"{icon} {counter}" if icon else counter)
            rewards_list.append({"label": f"[{remaining}/{max_charges}]", "amount": 0, "icon_key": buff_key, "kind": "buffs", "color": color})
        for mk, mv in materials.items():
            display_name = str(mk).replace("_", " ").title()
            rewards_list.append({"label": display_name, "amount": mv, "icon_key": mk, "kind": "materials", "color": (80, 210, 120)})

        monster_data = None
        collection_status = "NEW DISCOVERY"
        if best_creature:
            monster_data = {
                "name": str(best_creature.get("name", "Unknown")),
                "level": int(best_creature.get("level", 1)),
                "rarity": str(best_creature.get("rarity", "Common")),
                "trait": str(best_creature.get("ability", "")),
                "value": int(best_creature.get("value", 0)),
            }
            dup_check = await self.bot.db.fetchone(
                "SELECT COUNT(*) as cnt FROM rpg_creatures WHERE user_id = ? AND name = ?",
                (ctx.author.id, str(best_creature.get("name", ""))),
            )
            if dup_check and int(dup_check["cnt"]) > 1:
                collection_status = "DUPLICATE"

        arena_rating = int(player["arena_rating"]) if "arena_rating" in player.keys() else 1000
        from core.rpg_data import arena_rank
        hunter_rank = arena_rank(arena_rating)

        renderer = HuntCardRenderer()
        is_multi = len(creatures) > 1

        if is_multi:
            monsters_data = []
            for c in creatures:
                c_name = str(c.get("name", "Unknown"))
                # Check duplicates for this specific monster
                dup_check = await self.bot.db.fetchone(
                    "SELECT COUNT(*) as cnt FROM rpg_creatures WHERE user_id = ? AND name = ?",
                    (ctx.author.id, c_name),
                )
                mon_status = "DUPLICATE"
                if not dup_check or int(dup_check["cnt"]) <= 1:
                    mon_status = "NEW DISCOVERY"
                    
                monsters_data.append({
                    "name": c_name,
                    "rarity": str(c.get("rarity", "Common")),
                    "value": int(c.get("value", 0)),
                    "collection_status": mon_status
                })
                
            special_drop = None
            if found_crate:
                crate_name = str(CRATE_TYPES[found_crate].get("name", "Unknown Cache"))
                special_drop = {"type": "crate", "key": found_crate, "name": crate_name, "rarity": "Legendary"}

            hunt_card_data = {
                "hunter_name": ctx.author.display_name,
                "hunter_rank": f"{hunter_rank} Hunter",
                "hunt_streak": int(player["hunts_done"]) if "hunts_done" in player.keys() else 0,
                "zone_name": target_zone.name,
                "zone_key": target_zone.key,
                "monsters": monsters_data,
                "total_souls": total_gold,
                "rewards": rewards_list,
                "special_drop": special_drop,
            }
            hunt_card_buf = renderer.render_multi_hunt_card(hunt_card_data)
        else:
            special_drop = None
            if found_crate:
                crate_name = str(CRATE_TYPES[found_crate].get("name", "Unknown Cache"))
                special_drop = {"type": "crate", "key": found_crate, "name": crate_name, "rarity": "Legendary"}
                
            hunt_card_data = {
                "hunter_name": ctx.author.display_name,
                "hunter_rank": f"{hunter_rank} Hunter",
                "hunt_streak": int(player["hunts_done"]) if "hunts_done" in player.keys() else 0,
                "zone_name": target_zone.name,
                "zone_key": target_zone.key,
                "monster": monster_data,
                "collection_status": collection_status,
                "rewards": rewards_list,
                "special_drop": special_drop,
                "catch_chance": 100.0,
                "rarity_chance": 0.0,
            }
            hunt_card_buf = renderer.render_hunt_card(hunt_card_data)

        card_file = discord.File(hunt_card_buf, filename="abyssia_hunt.png")

        header_icon = asset_emoji("ui", "hunt") or "Hunt"
        if active_buff_lines:
            header_text = f"{header_icon} | **{ctx.author.display_name}**, active buffs {' '.join(active_buff_lines[:6])} !"
        else:
            header_text = f"{header_icon} | **{ctx.author.display_name}**, hunt !"
        embed_lines = [
            header_text,
        ]
        if xp_team:
            team_icons = []
            for cr in xp_team[:3]:
                icon = creature_emoji(str(cr["name"]), str(cr["rarity"])) or rarity_emoji(str(cr["rarity"]))
                if icon:
                    team_icons.append(icon)
            icon_prefix = f"{' '.join(team_icons)} " if team_icons else ""
            embed_lines.append(f"| {icon_prefix}gained **{total_xp:,}xp**!")
        else:
            embed_lines.append(f"| gained **{total_xp:,}xp**!")
        embed_lines.append(f"| {currency_label('gold')} **{total_gold:,}**")
        if checklist_lootboxes:
            embed_lines.append(f"| {crate_label('cache', 'Lootbox')} `[{checklist_lootbox_count}/3]` **RESETS IN:** `{_daily_reset_timer()}`")
        if found_crate:
            crate_name = str(CRATE_TYPES[found_crate].get("name", "Weapon Crate"))
            embed_lines.append(f"| {crate_label(found_crate, crate_name)}")

        embed = discord.Embed(description="\n".join(embed_lines), color=discord.Color.dark_green())
        embed.set_image(url="attachment://abyssia_hunt.png")
        await ctx.reply(embed=embed, file=card_file, mention_author=False)

    @commands.hybrid_command(name="use", aliases=["activate"])
    async def use_item(self, ctx: commands.Context, *, item_name: str | None = None) -> None:
        """Use a consumable item. Currently: Hunt Sword (+1 roll for 20 min)."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        
        if item_name is None:
            sword_qty = await get_quantity(self.bot.db, ctx.author.id, "consumable", HUNT_SWORD_KEY)
            sword_active = await _check_sword_active(self.bot.db, ctx.author.id)
            embed = dark_embed("Use Item", color=discord.Color.dark_green())
            if sword_qty > 0:
                status = "ACTIVE" if sword_active else "Ready"
                embed.add_field(name=_hunt_sword_label(), value=f"Quantity: **{sword_qty}**\nStatus: **{status}**\nEffect: +1 extra hunt roll for 20 minutes\n\n`b use sword` to activate", inline=False)
            else:
                embed.add_field(name=_hunt_sword_label(), value="None owned\nGet them from daily rewards, crates, or the shop.", inline=False)
            if sword_active:
                remaining = SWORD_DURATION - (now_ts() - await _get_sword_activated_at(self.bot.db, ctx.author.id))
                mins = max(0, remaining // 60)
                embed.add_field(name=ui_label("autohunt", "Time Remaining"), value=f"**{mins}** minutes", inline=False)
            await ctx.reply(embed=embed, mention_author=False)
            return
        
        key = item_name.strip().lower()
        if key in ("sword", "hunt_sword", "hunt sword", "swords"):
            sword_qty = await get_quantity(self.bot.db, ctx.author.id, "consumable", HUNT_SWORD_KEY)
            if sword_qty <= 0:
                await ctx.reply(embed=dark_embed("Use", "No Hunt Swords in inventory."), mention_author=False, ephemeral=True)
                return
            sword_active = await _check_sword_active(self.bot.db, ctx.author.id)
            if sword_active:
                remaining = SWORD_DURATION - (now_ts() - await _get_sword_activated_at(self.bot.db, ctx.author.id))
                mins = max(0, remaining // 60)
                await ctx.reply(embed=dark_embed("Use", f"Hunt Sword already active! **{mins}** min remaining."), mention_author=False, ephemeral=True)
                return
            # Consume 1 sword and activate buff
            await add_item(self.bot.db, ctx.author.id, "consumable", HUNT_SWORD_KEY, -1)
            await activate_buff(self.bot.db, ctx.author.id, SWORD_BUFF_KEY, "consumable", 1)
            embed = dark_embed(f"{_hunt_sword_label()} Activated", color=discord.Color.dark_green())
            embed.add_field(name="Effect", value="+1 extra hunt roll for **20 minutes**", inline=False)
            embed.add_field(name="Remaining", value=f"{sword_qty - 1} sword(s) left in inventory", inline=False)
            embed.set_footer(text="Hunt now for bonus rolls!")
            await ctx.reply(embed=embed, mention_author=False)
        else:
            await ctx.reply(embed=dark_embed("Use", f"Unknown item: `{item_name}`. Try `b use sword`."), mention_author=False, ephemeral=True)

    @commands.hybrid_command(name="explore")
    async def explore(self, ctx: commands.Context, *, zone: str | None = None) -> None:
        """Show or change unlocked hunting zones."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        if zone is None:
            view = ExploreZoneView(ctx, player)
            embed = dark_embed(ui_label("hunt", "Hunting Grounds"), "Select a zone from the dropdown below.", color=GOLD_COLOR)
            await ctx.reply(embed=embed, view=view, mention_author=False)
            return
        target_zone = get_zone(zone, player["current_zone"])
        if int(player["level"]) < target_zone.required_level:
            raise commands.BadArgument(f"{target_zone.name} unlocks at hunter level {target_zone.required_level}.")
        await self.bot.db.execute(
            "UPDATE rpg_players SET current_zone = ?, updated_at = ? WHERE user_id = ?",
            (target_zone.key, now_ts(), ctx.author.id),
        )
        embed = dark_embed("Route Marked", f"Current hunting zone set to {zone_label(target_zone.key)}.\n*{target_zone.flavor}*", color=GOLD_COLOR)
        asset_url, file = embed_asset("zones", target_zone.key)
        if asset_url:
            embed.set_thumbnail(url=asset_url)
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.hybrid_group(name="autohunt", invoke_without_command=True)
    async def autohunt(self, ctx: commands.Context) -> None:
        """Show autohunt status."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        row = await self.bot.db.fetchone(
            "SELECT * FROM rpg_autohunts WHERE user_id = ?",
            (ctx.author.id,),
        )
        if row is None:
            embed = dark_embed("No Expedition Active", "Send your hunter into the dark with `b autohunt start 4`.\nLonger expeditions return more loot and more bound monsters.", color=GOLD_COLOR)
            await ctx.reply(embed=embed, mention_author=False)
            return
        zone = ZONES[row["zone_key"]]
        embed = dark_embed(
            f"Expedition: {zone.name}",
            f"Duration: **{row['duration_hours']}h**\nClaim status: **{readable_seconds(row['ends_at'] - now_ts())}**",
            color=discord.Color.dark_teal(),
        )
        await ctx.reply(embed=embed, mention_author=False)

    @autohunt.command(name="start")
    async def autohunt_start(self, ctx: commands.Context, duration_hours: int = 1, *, zone: str | None = None) -> None:
        """Send your hunter offline for 1, 4, 8, 12, or 24 hours."""
        assert ctx.guild is not None
        if duration_hours not in AUTOHUNT_DURATIONS:
            raise commands.BadArgument("Duration must be 1, 4, 8, 12, or 24 hours.")
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        current = await self.bot.db.fetchone("SELECT 1 FROM rpg_autohunts WHERE user_id = ?", (ctx.author.id,))
        if current is not None:
            raise commands.BadArgument("You already have an active autohunt.")
        target_zone = get_zone(zone, player["current_zone"])
        if int(player["level"]) < target_zone.required_level:
            raise commands.BadArgument(f"{target_zone.name} unlocks at hunter level {target_zone.required_level}.")
        duration_seconds = round(duration_hours * 3600)
        started = now_ts()
        await self.bot.db.execute(
            "INSERT INTO rpg_autohunts (user_id, zone_key, duration_hours, started_at, ends_at) VALUES (?, ?, ?, ?, ?)",
            (ctx.author.id, target_zone.key, duration_hours, started, started + duration_seconds),
        )
        embed = dark_embed(
            "Expedition Started",
            f"Your hunter vanished into {zone_label(target_zone.key)}.\nReturn in **{readable_seconds(duration_seconds)}** and claim the spoils.",
            color=discord.Color.dark_teal(),
        )
        asset_url, file = embed_asset("zones", target_zone.key)
        if asset_url:
            embed.set_thumbnail(url=asset_url)
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @autohunt.command(name="claim")
    async def autohunt_claim(self, ctx: commands.Context) -> None:
        """Claim finished autohunt rewards."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        row = await self.bot.db.fetchone("SELECT * FROM rpg_autohunts WHERE user_id = ?", (ctx.author.id,))
        if row is None:
            raise commands.BadArgument("You do not have an active autohunt.")
        if int(row["ends_at"]) > now_ts():
            raise commands.BadArgument(f"Autohunt finishes in {readable_seconds(row['ends_at'] - now_ts())}.")
        zone = ZONES[row["zone_key"]]
        rolls = min(HUNT_AUTOHUNT_MAX_ROLLS, int(row["duration_hours"]) * HUNT_AUTOHUNT_ROLLS_PER_HOUR)
        total_gold = 0
        total_gems = 0
        total_xp = 0
        materials: dict[str, int] = {}
        creatures: list[str] = []
        card_creatures: list[str] = []
        for _ in range(rolls):
            result = await self._hunt_roll(ctx.author.id, player, zone, allow_creature=len(creatures) < 12)
            total_gold += int(result["gold"])
            total_gems += int(result["gems"])
            total_xp += int(result["xp"])
            if result.get("material_key") and int(result.get("material_amount", 0)):
                materials[str(result["material_key"])] = materials.get(str(result["material_key"]), 0) + int(result["material_amount"])
            if result["creature"]:
                creature = result["creature"]
                creatures.append(creature_line({**creature, "id": result["creature_id"]}, show_stats=False))
                card_creatures.append(f"{creature['name']} ({creature['rarity']}) Lv.{creature['level']}")
        player, levels = await award_player_xp(self.bot.db, player, total_xp)
        await self.bot.db.execute(
            "UPDATE rpg_players SET hunts_done = hunts_done + ?, updated_at = ? WHERE user_id = ?",
            (rolls, now_ts(), ctx.author.id),
        )
        await self.bot.db.execute("DELETE FROM rpg_autohunts WHERE user_id = ?", (ctx.author.id,))
        await progress_quest(self.bot.db, ctx.author.id, "daily_hunts", min(5, rolls))
        embed = dark_embed(f"Expedition Complete: {zone.name}", color=discord.Color.dark_teal())
        embed.add_field(name="Rewards", value=f"{currency_label('gold')} **{total_gold}**\n{currency_label('gems')} **{total_gems}**", inline=True)
        embed.add_field(name="Progress", value=f"**+{total_xp}** XP" + (f"\nLeveled up {levels} time(s)" if levels else ""), inline=True)
        embed.add_field(name="Bound Monsters", value="\n".join(creatures[:10]) if creatures else "None caught. The dark kept its monsters.", inline=False)
        asset_url, file = embed_asset("zones", zone.key)
        if asset_url:
            embed.set_thumbnail(url=asset_url)
        image = render_autohunt_card(
            zone.name,
            hours=int(row["duration_hours"]),
            souls=total_gold,
            gems=total_gems,
            xp=total_xp,
            materials=materials,
            creatures=card_creatures,
            levels=levels,
        )
        card_file = discord.File(image, filename="abyssia_autohunt.png")
        embed.set_image(url="attachment://abyssia_autohunt.png")
        files = [card_file]
        if file:
            files.append(file)
        await ctx.reply(embed=embed, files=files, mention_author=False)

    @commands.hybrid_command(name="zones")
    async def zones(self, ctx: commands.Context) -> None:
        """List all hunting zones."""
        lines = [f"{zone_label(zone.key)} - Lv.`{zone.required_level}`+, max {rarity_label(zone.max_rarity)}" for zone in ZONES.values()]
        embed = dark_embed("Zone Index", "\n".join(lines), color=GOLD_COLOR)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGHunting(bot))
