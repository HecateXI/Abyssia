from __future__ import annotations

import discord
from discord.ext import commands

from core.cards import render_collection_card, render_profile_card
from core.discord_assets import embed_asset
from core.items import HUNT_SWORD_KEY, HUNT_SWORD_NAME

from core.rpg import (
    CHECKLIST_BATTLE_CRATE_TARGET,
    CHECKLIST_HUNT_LOOTBOX_TARGET,
    add_item,
    award_currency,
    checklist_is_complete,
    claim_daily_checklist_reward,
    daily_reset_text,
    ensure_daily_checklist,
    ensure_player,
    get_active_buffs,
    get_quantity,
    inventory_rows,
    mark_checklist_daily,
    now_ts,
    progress_quest,
    refresh_player,
    top_creatures,
    utc_day_start,
    unlock_achievement,
    xp_for_level,
)
from core.rpg_data import ACHIEVEMENTS, CREATURES, MATERIALS, QUESTS, RARITY_INDEX, WEAPON_SHARD_KEY, normalize_key
from core.theme import (
    DARK_COLOR,
    GOLD_COLOR,
    STAT_EMOJIS,
    creature_emoji,
    creature_line,
    consumable_label,
    crate_emoji,
    crate_label,
    currency_label,
    dark_embed,
    equipment_label,
    material_label,
    progress_bar,
    rarity_label,
    rarity_level_badge,
    rarity_rank,
    status_embed,
    ui_label,
    zone_label,
)


SPECIES_PER_PAGE = 21

RARITY_OPTIONS = [
    ("All", "all"),
    ("Common", "Common"),
    ("Uncommon", "Uncommon"),
    ("Rare", "Rare"),
    ("Epic", "Epic"),
    ("Legendary", "Legendary"),
    ("Mythic", "Mythic"),
    ("Ancient", "Ancient"),
    ("Divine", "Divine"),
    ("Eldritch", "Eldritch"),
    ("Abyssal", "Abyssal"),
]


class InventoryView(discord.ui.View):
    def __init__(self, ctx: commands.Context, has_crates: bool = False, has_swords: bool = False) -> None:
        super().__init__(timeout=60)
        self.ctx = ctx
        self.has_crates = has_crates
        self.has_swords = has_swords

    @discord.ui.button(label="Open Crate", style=discord.ButtonStyle.secondary, emoji="📦", row=0)
    async def open_crate(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        from cogs.rpg_shop import CrateOpenView
        from core.rpg import ensure_player, get_quantity
        from core.rpg_data import CRATE_TYPES
        db = self.ctx.bot.db
        player = await ensure_player(db, self.ctx.author.id, self.ctx.author.display_name)
        # Find owned crates
        owned = []
        for ck in CRATE_TYPES:
            qty = await get_quantity(db, self.ctx.author.id, "crate", ck)
            if qty > 0:
                owned.append((ck, CRATE_TYPES[ck]["name"], qty))
        if not owned:
            await interaction.followup.send("No crates found. Hunt for crates or buy one with `b shardcrate cache`.", ephemeral=True)
            return
        # Build dropdown with only owned crates
        options = [
            discord.SelectOption(
                label=name,
                value=ck,
                description=f"Owned: {qty}",
                emoji=discord.PartialEmoji.from_str(crate_emoji(ck)) if crate_emoji(ck) else "📦",
            )
            for ck, name, qty in owned
        ]
        view = CrateOpenView(self.ctx)
        view.crate_select.options = options
        view.crate_select.placeholder = f"You own {sum(q for _, _, q in owned)} crate(s)..."
        embed = discord.Embed(title=crate_label(owned[0][0], "Open Crate"), description="Choose a crate to open from your inventory.", color=discord.Color.orange())
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Use Hunt Sword", style=discord.ButtonStyle.primary, emoji="⚔️", row=0)
    async def use_sword(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        db = self.ctx.bot.db
        qty = await get_quantity(db, self.ctx.author.id, "consumable", HUNT_SWORD_KEY)
        if qty <= 0:
            await interaction.followup.send("No Hunt Swords in inventory.", ephemeral=True)
            return
        # Check if already active
        from cogs.rpg_hunting import _check_sword_active, _get_sword_activated_at, SWORD_DURATION, SWORD_BUFF_KEY
        from core.rpg import activate_buff
        active = await _check_sword_active(db, self.ctx.author.id)
        if active:
            remaining = SWORD_DURATION - (now_ts() - await _get_sword_activated_at(db, self.ctx.author.id))
            mins = max(0, remaining // 60)
            await interaction.followup.send(f"Hunt Sword already active! **{mins}** min remaining. Use `b hunt` for +1 roll.", ephemeral=True)
            return
        # Activate
        await add_item(db, self.ctx.author.id, "consumable", HUNT_SWORD_KEY, -1)
        await activate_buff(db, self.ctx.author.id, SWORD_BUFF_KEY, "consumable", 1)
        embed = discord.Embed(
            title=f"{consumable_label(HUNT_SWORD_KEY, HUNT_SWORD_NAME)} Activated",
            description=f"+1 extra hunt roll for **20 minutes**\n{qty - 1} sword(s) remaining\n\nUse `b hunt` now!",
            color=discord.Color.dark_green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id


class RaritySelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [discord.SelectOption(label=label, value=value) for label, value in RARITY_OPTIONS]
        super().__init__(placeholder="Filter by rarity...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        view: BestiaryView = self.view  # type: ignore
        view.selected_rarity = self.values[0]
        view.page = 1
        embed, files = await view._build_page()
        await interaction.response.edit_message(embed=embed, attachments=files, view=view)


class BestiaryView(discord.ui.View):
    def __init__(self, bot, target_id: int, target_name: str, target_avatar_url: str, page: int) -> None:
        super().__init__(timeout=180)
        self.bot = bot
        self.target_id = target_id
        self.target_name = target_name
        self.target_avatar_url = target_avatar_url
        self.page = page
        self.total_pages = 1
        self.selected_rarity = "all"
        self.add_item(RaritySelect())

    def _update_buttons(self) -> None:
        self.prev_page.disabled = self.page <= 1
        self.next_page.disabled = self.page >= self.total_pages

    async def _build_page(self) -> tuple[discord.Embed, list[discord.File]]:
        caught_rows = await self.bot.db.fetchall(
            "SELECT name, rarity, COUNT(*) AS total, MAX(level) AS max_level FROM rpg_creatures WHERE user_id = ? GROUP BY name, rarity",
            (self.target_id,),
        )
        caught_map = {}
        for r in caught_rows:
            caught_map[(str(r["name"]), str(r["rarity"]))] = {
                "total": int(r["total"]),
                "max_level": int(r["max_level"]),
            }

        entries = []
        for ct in CREATURES:
            key = (ct.name, ct.rarity)
            info = caught_map.get(key)
            entries.append({
                "name": ct.name,
                "rarity": ct.rarity,
                "caught": info is not None,
                "total": info["total"] if info else 0,
                "max_level": info["max_level"] if info else 0,
            })

        if self.selected_rarity != "all":
            entries = [e for e in entries if e["rarity"] == self.selected_rarity]

        entries.sort(key=lambda e: (RARITY_INDEX.get(e["rarity"], 0), e["name"]))
        total_templates = len(entries)
        caught_count = sum(1 for e in entries if e["caught"])
        self.total_pages = max(1, -(-total_templates // SPECIES_PER_PAGE))
        self.page = max(1, min(self.page, self.total_pages))
        self._update_buttons()

        start = (self.page - 1) * SPECIES_PER_PAGE
        page_entries = entries[start:start + SPECIES_PER_PAGE]

        rarity_label = self.selected_rarity.title() if self.selected_rarity != "all" else "All Rarities"
        embed = discord.Embed(color=DARK_COLOR)
        embed.set_author(name=f"{self.target_name}'s Index  ({caught_count}/{total_templates})  •  {rarity_label}", icon_url=self.target_avatar_url)
        embed.set_footer(text=f"Page {self.page}/{self.total_pages}  •  {total_templates} species")

        image = render_collection_card(self.target_name, page_entries, caught_count, total_templates, self.page, self.total_pages)
        card_file = discord.File(image, filename="abyssia_collection.png")
        embed.set_image(url="attachment://abyssia_collection.png")

        return embed, [card_file]

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.page <= 1:
            await interaction.response.defer()
            return
        self.page -= 1
        embed, files = await self._build_page()
        await interaction.response.edit_message(embed=embed, attachments=files, view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.page >= self.total_pages:
            await interaction.response.defer()
            return
        self.page += 1
        embed, files = await self._build_page()
        await interaction.response.edit_message(embed=embed, attachments=files, view=self)


class RPGProfile(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="start")
    async def start(self, ctx: commands.Context, *, hunter_name: str | None = None) -> None:
        """Create your hunter profile."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, hunter_name or ctx.author.display_name)
        if hunter_name:
            hunter_name = hunter_name[:32]
            await self.bot.db.execute(
                "UPDATE rpg_players SET hunter_name = ?, updated_at = ? WHERE user_id = ?",
                (hunter_name, now_ts(), ctx.author.id),
            )
            player = await refresh_player(self.bot.db, ctx.author.id)
        embed = dark_embed(
            "Hunter Contract Signed",
            f"**{player['hunter_name']}** has entered the Abyssia ledger.\nStart with `b tutorial`, then use `b hunt` to bind your first monster.",
            color=GOLD_COLOR,
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="profile")
    async def profile(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        """Show a hunter profile."""
        assert ctx.guild is not None
        target = member or ctx.author
        player = await ensure_player(self.bot.db, target.id, target.display_name)
        creature_count = await self.bot.db.fetchone(
            "SELECT COUNT(*) AS total FROM rpg_creatures WHERE user_id = ?",
            (target.id,),
        )
        embed = dark_embed(f"{player['hunter_name']} - {player['title']}", color=discord.Color.dark_purple())
        embed.set_author(name=str(target), icon_url=target.display_avatar.url)
        embed.add_field(name="Level", value=f"**{player['level']}**\n{progress_bar(int(player['xp']), xp_for_level(int(player['level'])))}\n`{player['xp']}/{xp_for_level(player['level'])} XP`", inline=True)
        embed.add_field(name="Wallet", value=f"{currency_label('gold')} **{player['gold']}**\n{currency_label('gems')} **{player['gems']}**", inline=True)
        embed.add_field(name="Arena", value=f"**{player['arena_rating']}** rating", inline=True)
        embed.add_field(name="Collection", value=f"**{creature_count['total']}** monsters bound\n**{player['hunts_done']}** hunts survived\n**{player['prestige']}** prestige", inline=True)
        weapon_row = await self.bot.db.fetchone("SELECT name, quality, weapon_type FROM weapons WHERE user_id = ? AND equipped_creature_id IS NOT NULL LIMIT 1", (target.id,))
        if weapon_row:
            wq = str(weapon_row["quality"]) if weapon_row["quality"] else "Normal"
            wn = str(weapon_row["name"])
            weapon_name = f"{wq} {wn}" if wq != "Normal" else wn
        else:
            weapon_name = "None"
        active_buffs = await get_active_buffs(self.bot.db, target.id)
        image = render_profile_card(
            target.display_name,
            player,
            collection_count=int(creature_count["total"]),
            weapon_name=weapon_name,
            xp_needed=xp_for_level(int(player["level"])),
            active_buffs=active_buffs if active_buffs else None,
        )
        file = discord.File(image, filename="abyssia_profile.png")
        embed.set_image(url="attachment://abyssia_profile.png")
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.hybrid_command(name="bestiary", aliases=["zoo", "den", "pets", "collection", "vault"])
    async def bestiary(self, ctx: commands.Context, member: discord.Member | None = None, page: int = 1) -> None:
        """Show your Abyssian monster index. Sorted by rarity, shows caught and uncaught."""
        assert ctx.guild is not None
        target = member or ctx.author
        await ensure_player(self.bot.db, target.id, target.display_name)

        view = BestiaryView(self.bot, target.id, target.display_name, str(target.display_avatar.url), page)
        embed, files = await view._build_page()

        if embed.description:
            embed.set_author(name=str(target), icon_url=target.display_avatar.url)
            await ctx.reply(embed=embed, mention_author=False)
            return

        await ctx.reply(embed=embed, files=files, view=view, mention_author=False)

    @commands.hybrid_command(name="monsters")
    async def monsters(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        """Show a hunter's monster collection."""
        await self.bestiary.callback(self, ctx, member)

    @commands.hybrid_command(name="tutorial")
    async def tutorial(self, ctx: commands.Context) -> None:
        """Show the built-in RPG tutorial."""
        prefix = "b"
        if ctx.guild is not None:
            prefix = await self.bot.db.get_setting(ctx.guild.id, "prefix") or prefix
        embed = dark_embed(
            "Abyssia Tutorial",
            "A quick route from new hunter to monster collector.",
            color=GOLD_COLOR,
        )
        embed.add_field(name="1. Sign the ledger", value=f"`{prefix}start <hunter name>` creates your hunter profile.", inline=False)
        embed.add_field(name="2. Hunt and bind monsters", value=f"`{prefix}hunt` rolls Souls, XP, lootboxes, and a chance to bind a monster.\n`{prefix}explore` shows unlockable hunting grounds.", inline=False)
        embed.add_field(name="3. Build your bestiary", value=f"`{prefix}monsters` shows your dark collection.\n`{prefix}summon 1|5|10` spends gems for boosted monster pulls.", inline=False)
        embed.add_field(name="4. Grow stronger", value=f"`{prefix}weapons`, `{prefix}wdex <id>`, `{prefix}wrr <id> stat`, and `{prefix}wrr <id> passive` manage weapon rolls.", inline=False)
        embed.add_field(name="5. Fight the dark", value=f"`{prefix}team`, `{prefix}battle @user`, `{prefix}arena`, and `{prefix}boss attack` use your strongest monsters.", inline=False)
        embed.add_field(name="Tip", value="Use `b weapons <id>` to inspect any weapon by ID. Use `b weapons` to see your vault with IDs.", inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx: commands.Context) -> None:
        """Show your materials, crates, and items. Use buttons to open crates or use items."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        rows = await inventory_rows(self.bot.db, ctx.author.id)
        if not rows:
            await ctx.reply(embed=status_embed("Inventory", "Your inventory is empty."), mention_author=False)
            return
        sections: dict[str, list[str]] = {}
        has_crates = False
        has_swords = False
        for row in rows:
            key = row["item_key"]
            if row["item_type"] == "material":
                if key != WEAPON_SHARD_KEY:
                    continue
                name = material_label(key)
            elif row["item_type"] == "consumable" and key == HUNT_SWORD_KEY:
                name = consumable_label(HUNT_SWORD_KEY, HUNT_SWORD_NAME)
                has_swords = True
            elif row["item_type"] == "consumable" and key == "cookie":
                continue
            elif row["item_type"] == "crate":
                from core.rpg_data import CRATE_TYPES
                crate = CRATE_TYPES.get(key, {})
                name = crate_label(key, str(crate.get("name", key.replace("_", " ").title())))
                has_crates = True
            elif row["item_type"] == "lootbox":
                name = crate_label("cache", "Lootbox")
            else:
                name = key.replace("_", " ").title()
            sections.setdefault(row["item_type"], []).append(f"{name} x`{row['quantity']}`")
        if not sections:
            await ctx.reply(embed=status_embed("Inventory", "Your inventory has no active items."), mention_author=False)
            return
        embed = dark_embed("Inventory", color=discord.Color.dark_gold())
        label_map = {
            "material": "Weapon Shards",
            "lootbox": "Lootboxes",
            "consumable": "Consumables",
            "crate": "Weapon Crates",
            "weapon": ui_label("forge", "Weapons"),
        }
        for section, lines in sections.items():
            if lines:
                embed.add_field(name=label_map.get(section, section.title()), value="\n".join(lines[:15]), inline=False)
        
        view = InventoryView(ctx, has_crates=has_crates, has_swords=has_swords)
        await ctx.reply(embed=embed, view=view, mention_author=False)

    # ── Daily ──────────────────────────────────────────────────────

    @commands.hybrid_command(name="daily")
    async def daily(self, ctx: commands.Context) -> None:
        """Claim your daily reward."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        today_start = utc_day_start()
        if int(player["last_daily_at"]) >= today_start:
            raise commands.BadArgument("You already claimed today's daily reward.")
        gold = 500 + int(player["level"]) * 35
        gems = 15 + int(player["wisdom"]) // 3
        swords = 4 + min(8, int(player["level"]) // 4) + max(0, int(player["luck"]) // 8)
        await award_currency(self.bot.db, ctx.author.id, gold=gold, gems=gems)
        await add_item(self.bot.db, ctx.author.id, "consumable", HUNT_SWORD_KEY, swords)
        await self.bot.db.execute(
            "UPDATE rpg_players SET last_daily_at = ?, updated_at = ? WHERE user_id = ?",
            (now_ts(), now_ts(), ctx.author.id),
        )
        await mark_checklist_daily(self.bot.db, ctx.author.id)
        embed = status_embed("Daily Claimed", f"{currency_label('gold')} **{gold}**\n{currency_label('gems')} **{gems}**\n{consumable_label(HUNT_SWORD_KEY, HUNT_SWORD_NAME)} **{swords}**")
        embed.set_footer(text=f"Daily reset is {daily_reset_text()} for everyone")
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="checklist", aliases=["task", "tasks", "cl"])
    async def checklist(self, ctx: commands.Context) -> None:
        """Show today's checklist and claim the completion reward when ready."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        row = await ensure_daily_checklist(self.bot.db, ctx.author.id)
        claimed_rewards: dict[str, int] | None = None
        if checklist_is_complete(row) and not bool(row["reward_claimed"]):
            claimed_rewards = await claim_daily_checklist_reward(self.bot.db, ctx.author.id)
            row = await ensure_daily_checklist(self.bot.db, ctx.author.id)

        daily_done = bool(row["daily_claimed"])
        hunt_count = min(CHECKLIST_HUNT_LOOTBOX_TARGET, int(row["hunt_lootboxes"]))
        battle_count = min(CHECKLIST_BATTLE_CRATE_TARGET, int(row["battle_crates"]))
        hunt_done = hunt_count >= CHECKLIST_HUNT_LOOTBOX_TARGET
        battle_done = battle_count >= CHECKLIST_BATTLE_CRATE_TARGET

        def mark(done: bool) -> str:
            return "Done" if done else "Todo"

        lines = [
            f"`{mark(daily_done)}` Claim daily reward",
            f"`{mark(hunt_done)}` Find hunt lootboxes `{hunt_count}/{CHECKLIST_HUNT_LOOTBOX_TARGET}`",
            f"`{mark(battle_done)}` Find battle weapon crates `{battle_count}/{CHECKLIST_BATTLE_CRATE_TARGET}`",
        ]
        embed = dark_embed("Daily Checklist", "\n".join(lines), color=GOLD_COLOR)
        reward_text = (
            f"{currency_label('gold')} **1,000**\n"
            f"{crate_label('cache', 'Lootbox')} **1**\n"
            f"{crate_label('cache', 'Weapon Crate')} **1**\n"
            f"{material_label(WEAPON_SHARD_KEY)} **100**"
        )
        if claimed_rewards:
            embed.add_field(name="Completion Reward Claimed", value=reward_text, inline=False)
        elif bool(row["reward_claimed"]):
            embed.add_field(name="Completion Reward", value="Already claimed today.", inline=False)
        else:
            embed.add_field(name="Completion Reward", value=reward_text, inline=False)
        embed.set_footer(text=f"Resets daily at {daily_reset_text()}")
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_group(name="quests", invoke_without_command=True)
    async def quests(self, ctx: commands.Context) -> None:
        """Show daily quest progress."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        from core.rpg import today_key

        period = today_key()
        rows = await self.bot.db.fetchall(
            "SELECT quest_key, progress, claimed FROM rpg_quests WHERE user_id = ? AND period_key = ?",
            (ctx.author.id, period),
        )
        progress = {row["quest_key"]: row for row in rows}
        lines = []
        for key, quest in QUESTS.items():
            row = progress.get(key)
            value = 0 if row is None else int(row["progress"])
            claimed = bool(row and row["claimed"])
            lines.append(f"**{quest['name']}**: {value}/{quest['target']}" + (" - claimed" if claimed else ""))
        embed = dark_embed("Daily Quests", "\n".join(lines) + "\n\nUse `b quests claim` when a quest is complete.", color=GOLD_COLOR)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="quest")
    async def quest(self, ctx: commands.Context) -> None:
        """Show daily quest progress."""
        await self.quests.callback(self, ctx)

    @quests.command(name="claim")
    async def claim_quests(self, ctx: commands.Context) -> None:
        """Claim completed daily quests."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        from core.rpg import today_key

        period = today_key()
        total_gold = 0
        total_gems = 0
        claimed_keys: list[str] = []
        for key, quest in QUESTS.items():
            row = await self.bot.db.fetchone(
                "SELECT progress, claimed FROM rpg_quests WHERE user_id = ? AND quest_key = ? AND period_key = ?",
                (ctx.author.id, key, period),
            )
            if row is None or row["claimed"] or int(row["progress"]) < int(quest["target"]):
                continue
            await self.bot.db.execute(
                "UPDATE rpg_quests SET claimed = 1 WHERE user_id = ? AND quest_key = ? AND period_key = ?",
                (ctx.author.id, key, period),
            )
            total_gold += int(quest["gold"])
            total_gems += int(quest["gems"])
            claimed_keys.append(str(quest["name"]))
        if not claimed_keys:
            raise commands.BadArgument("No completed unclaimed quests.")
        await award_currency(self.bot.db, ctx.author.id, gold=total_gold, gems=total_gems)
        await ctx.reply(embed=status_embed("Quests Claimed", f"Claimed **{len(claimed_keys)}** quest(s).\n{currency_label('gold')} **{total_gold}**\n{currency_label('gems')} **{total_gems}**"), mention_author=False)

    @commands.hybrid_command(name="achievements")
    async def achievements(self, ctx: commands.Context) -> None:
        """Show unlocked achievements."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        rows = await self.bot.db.fetchall(
            "SELECT achievement_key FROM rpg_achievements WHERE user_id = ? ORDER BY unlocked_at",
            (ctx.author.id,),
        )
        if not rows:
            await ctx.reply(embed=status_embed("Achievements", "No achievements unlocked yet."), mention_author=False)
            return
        lines = []
        for row in rows:
            name, description = ACHIEVEMENTS.get(row["achievement_key"], (row["achievement_key"], ""))
            lines.append(f"**{name}** - {description}")
        await ctx.reply(embed=dark_embed("Achievements", "\n".join(lines)), mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGProfile(bot))
