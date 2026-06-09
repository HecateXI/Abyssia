from __future__ import annotations

import discord
from discord.ext import commands

from core.cards import render_collection_card, render_profile_card
from core.items import HUNT_SWORD_KEY, HUNT_SWORD_NAME

from core.rpg import (
    CHECKLIST_BATTLE_CRATE_TARGET,
    CHECKLIST_HUNT_LOOTBOX_TARGET,
    add_item,
    award_currency,
    checklist_is_complete,
    claim_daily_checklist_reward,
    daily_reset_text,
    ensure_arena_stats,
    ensure_daily_checklist,
    ensure_player,
    get_zone,
    get_active_buffs,
    get_quantity,
    inventory_rows,
    mark_checklist_daily,
    now_ts,
    refresh_player,
    utc_day_start,
    xp_for_level,
)
from core.rpg_data import ACHIEVEMENTS, CREATURES, QUESTS, RARITIES, RARITY_INDEX, WEAPON_SHARD_KEY, ZONES
from core.theme import (
    DARK_COLOR,
    GOLD_COLOR,
    consumable_label,
    creature_emoji,
    crate_emoji,
    crate_label,
    currency_label,
    dark_embed,
    equipment_label,
    material_label,
    rarity_emoji,
    rarity_label,
    status_embed,
)


RARITY_ORDER = [r.name for r in RARITIES]


_SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _superscript(n: int) -> str:
    return str(n).translate(_SUPERSCRIPT)


async def _build_dense_zoo(db, target_id: int, target_name: str, target_avatar_url: str) -> str:
    """Build an OwO-style dense zoo display as plain text."""
    caught_rows = await db.fetchall(
        "SELECT name, rarity, COUNT(*) AS total, SUM(level) AS total_levels, SUM(value) AS total_value FROM rpg_creatures WHERE user_id = ? GROUP BY name, rarity",
        (target_id,),
    )
    caught_map: dict[tuple[str, str], dict] = {}
    for r in caught_rows:
        caught_map[(str(r["name"]), str(r["rarity"]))] = {
            "total": int(r["total"]),
            "total_levels": int(r["total_levels"] or 0),
            "total_value": int(r["total_value"] or 0),
        }

    by_rarity: dict[str, list[tuple[str, int]]] = {r: [] for r in RARITY_ORDER}
    total_points = 0
    total_creatures = 0
    species_caught = 0
    species_total = 0

    for ct in CREATURES:
        species_total += 1
        key = (ct.name, ct.rarity)
        info = caught_map.get(key)
        if info:
            species_caught += 1
            count = info["total"]
            total_points += info["total_value"]
            total_creatures += count
            by_rarity[ct.rarity].append((ct.name, count))

    for rarity in by_rarity:
        by_rarity[rarity].sort(key=lambda x: (-x[1], x[0]))

    lines: list[str] = []
    lines.append(f"**{target_name}'s Abyssia Zoo**")
    lines.append(f"{species_caught}/{species_total} species • {total_creatures:,} creatures • Zoo Points: {total_points:,}")
    lines.append("")

    # Rarity short codes for footer
    rarity_short = {"Common": "C", "Uncommon": "U", "Rare": "R", "Epic": "E", "Legendary": "L", "Mythic": "M", "Ancient": "A", "Patreon": "P", "Divine": "D", "Eldritch": "El", "Abyssal": "Ab", "Prismatic": "Pr", "Ethereal": "Et", "Void Lord": "VL", "Hidden": "H"}
    missing_counts: list[str] = []
    
    for rarity in RARITY_ORDER:
        creatures = by_rarity.get(rarity, [])
        if not creatures:
            continue
            
        total_in_rarity = sum(c[1] for c in creatures)
        species_in_rarity = len(creatures)
        total_species_in_rarity = sum(1 for ct in CREATURES if ct.rarity == rarity)
        missing_in_rarity = total_species_in_rarity - species_in_rarity
        
        if missing_in_rarity > 0:
            short = rarity_short.get(rarity, rarity[:1])
            missing_counts.append(f"{short}-{missing_in_rarity}")
            
        rmob = rarity_emoji(rarity)
        header = f"{rmob} **{rarity}** ({_superscript(total_in_rarity)})" if rmob else f"**{rarity}** ({_superscript(total_in_rarity)})"
        lines.append(header)

        # Build creature entries with emojis and counts
        parts: list[str] = []
        for name, count in creatures:
            emoji = creature_emoji(name)
            if emoji:
                parts.append(f"{emoji}{_superscript(count)}")
            else:
                parts.append(f"`{name[:12]}`{_superscript(count)}")

        # Wrap rows at ~500 chars for clean display
        rows: list[str] = []
        current_row = ""
        for p in parts:
            if not current_row:
                current_row = p
            elif len(current_row) + 1 + len(p) > 500:
                rows.append(current_row)
                current_row = p
            else:
                current_row += " " + p
        if current_row:
            rows.append(current_row)
        
        lines.extend(rows)
        lines.append("")

    if species_caught == 0:
        lines.append("*No creatures caught yet.*")
    elif missing_counts:
        lines.append(f"Missing: {', '.join(missing_counts)}")

    return "\n".join(lines)


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
    ("Patreon", "Patreon"),
    ("Divine", "Divine"),
    ("Eldritch", "Eldritch"),
    ("Abyssal", "Abyssal"),
    ("Prismatic", "Prismatic"),
    ("Ethereal", "Ethereal"),
    ("Void Lord", "Void Lord"),
    ("Hidden", "Hidden"),
]

PROFILE_ACCENT_PRESETS = {
    "purple": "#AA5FF5",
    "gold": "#EBC350",
    "cyan": "#37E1D2",
    "green": "#50D278",
    "red": "#DC3C4B",
    "orange": "#F5912D",
    "blue": "#46A0EB",
    "pink": "#FB7185",
}


def _available_profile_backgrounds() -> str:
    return ", ".join(zone.name for zone in ZONES.values())


def _normalize_profile_color(value: str) -> str:
    raw = value.strip()
    lowered = raw.lower()
    if lowered in {"default", "reset", "none", "zone"}:
        return ""
    if lowered in PROFILE_ACCENT_PRESETS:
        return PROFILE_ACCENT_PRESETS[lowered]
    if lowered.startswith("0x"):
        raw = raw[2:]
    raw = raw.lstrip("#")
    if len(raw) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in raw):
        presets = ", ".join(PROFILE_ACCENT_PRESETS)
        raise commands.BadArgument(f"Use a hex color like `#22d3ee`, `default`, or one of: {presets}.")
    return f"#{raw.upper()}"


def _profile_embed_color(value: str | None, fallback: discord.Color = discord.Color.dark_purple()) -> discord.Color:
    if not value:
        return fallback
    raw = value.strip().lstrip("#")
    if len(raw) != 6:
        return fallback
    try:
        return discord.Color(int(raw, 16))
    except ValueError:
        return fallback


class InventoryView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context,
        has_crates: bool = False,
        has_swords: bool = False,
        has_lootboxes: bool = False,
    ) -> None:
        super().__init__(timeout=60)
        self.ctx = ctx
        self.has_crates = has_crates
        self.has_swords = has_swords
        self.has_lootboxes = has_lootboxes
        self.open_crate.disabled = not (has_crates or has_lootboxes)
        self.use_sword.disabled = not has_swords

    @discord.ui.button(label="Open Crate", style=discord.ButtonStyle.secondary, emoji="📦", row=0)
    async def open_crate(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        from cogs.rpg_shop import CrateOpenView
        from core.rpg import ensure_player
        db = self.ctx.bot.db
        await ensure_player(db, self.ctx.author.id, self.ctx.author.display_name)
        view = CrateOpenView(self.ctx)
        if not await view.load_owned_options():
            await interaction.followup.send("No lootboxes or crates found. Hunt for lootboxes or buy one with `b shardcrate cache`.", ephemeral=True)
            return
        embed = discord.Embed(title="Open Box", description="Choose a lootbox or weapon crate to open.", color=discord.Color.orange())
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        return
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
            await interaction.followup.send(f"Hunt Sword already active! **{mins}** min remaining. Use `b hunt` for 1.3x catch rate.", ephemeral=True)
            return
        # Activate
        await add_item(db, self.ctx.author.id, "consumable", HUNT_SWORD_KEY, -1)
        await activate_buff(db, self.ctx.author.id, SWORD_BUFF_KEY, "consumable", 1)
        embed = discord.Embed(
            title=f"{consumable_label(HUNT_SWORD_KEY, HUNT_SWORD_NAME)} Activated",
            description=f"1.3x catch rate for **20 minutes**\n{qty - 1} sword(s) remaining\n\nUse `b hunt` now!",
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

    async def _get_profile_cosmetics(self, user_id: int) -> dict[str, str]:
        row = await self.bot.db.fetchone(
            "SELECT background_key, accent_color, about FROM rpg_profile_cosmetics WHERE user_id = ?",
            (user_id,),
        )
        if row is None:
            return {"background_key": "", "accent_color": "", "about": ""}
        return {
            "background_key": str(row["background_key"] or ""),
            "accent_color": str(row["accent_color"] or ""),
            "about": str(row["about"] or ""),
        }

    async def _set_profile_cosmetics(self, user_id: int, **changes: str) -> dict[str, str]:
        current = await self._get_profile_cosmetics(user_id)
        current.update({key: value for key, value in changes.items() if key in current})
        await self.bot.db.execute(
            """
            INSERT INTO rpg_profile_cosmetics (user_id, background_key, accent_color, about, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                background_key = excluded.background_key,
                accent_color = excluded.accent_color,
                about = excluded.about,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                current["background_key"],
                current["accent_color"],
                current["about"],
                now_ts(),
            ),
        )
        return current

    @commands.hybrid_command(name="start")
    async def start(self, ctx: commands.Context, *, hunter_name: str | None = None) -> None:
        """Create your hunter profile."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, hunter_name or ctx.author.display_name)
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO rpg_user_agreements (user_id, agreed_at) VALUES (?, ?)",
            (ctx.author.id, now_ts()),
        )
        if hunter_name:
            hunter_name = hunter_name[:32]
            await self.bot.db.execute(
                "UPDATE rpg_players SET hunter_name = ?, updated_at = ? WHERE user_id = ?",
                (hunter_name, now_ts(), ctx.author.id),
            )
            player = await refresh_player(self.bot.db, ctx.author.id)
        embed = dark_embed(
            "Hunter Contract Signed",
            f"**{player['hunter_name']}** has entered the Abyssia ledger.\nUse `b help` for commands, then `b hunt` to bind your first monster.",
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
        cosmetics = await self._get_profile_cosmetics(target.id)
        embed = dark_embed(f"{player['hunter_name']} - {player['title']}", color=_profile_embed_color(cosmetics.get("accent_color")))
        embed.set_author(name=str(target), icon_url=target.display_avatar.url)
        weapon_row = await self.bot.db.fetchone("SELECT name, quality, weapon_type FROM weapons WHERE user_id = ? AND equipped_creature_id IS NOT NULL LIMIT 1", (target.id,))
        if weapon_row:
            wq = str(weapon_row["quality"]) if weapon_row["quality"] else "Normal"
            wn = str(weapon_row["name"])
            weapon_name = f"{wq} {wn}" if wq != "Normal" else wn
        else:
            weapon_name = "None"
        active_buffs = await get_active_buffs(self.bot.db, target.id)
        arena = await ensure_arena_stats(self.bot.db, target.id, ctx.guild.id)
        win_streak = int(arena["win_streak"])
        best_streak = int(arena["highest_win_streak"])
        avatar_bytes: bytes | None = None
        try:
            avatar_asset = target.display_avatar.with_size(256)
            if hasattr(avatar_asset, "with_static_format"):
                avatar_asset = avatar_asset.with_static_format("png")
            avatar_bytes = await avatar_asset.read()
        except Exception:
            avatar_bytes = None
        image = render_profile_card(
            target.display_name,
            player,
            collection_count=int(creature_count["total"]),
            weapon_name=weapon_name,
            xp_needed=xp_for_level(int(player["level"])),
            active_buffs=active_buffs if active_buffs else None,
            profile_cosmetics=cosmetics,
            avatar_bytes=avatar_bytes,
            win_streak=win_streak,
            best_streak=best_streak,
        )
        file = discord.File(image, filename="abyssia_profile.png")
        embed.set_image(url="attachment://abyssia_profile.png")
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.hybrid_group(name="profilecustomize", aliases=["profilecard", "pcard", "pc"], invoke_without_command=True)
    async def profilecustomize(self, ctx: commands.Context) -> None:
        """Customize your hunter profile card."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        cosmetics = await self._get_profile_cosmetics(ctx.author.id)
        background_key = cosmetics["background_key"] or str(player["current_zone"])
        zone = ZONES.get(background_key) or ZONES.get("void_realm")
        accent = cosmetics["accent_color"] or "zone default"
        about = cosmetics["about"] or "zone flavor"
        embed = dark_embed(
            "Profile Customization",
            (
                f"Background: **{zone.name if zone else background_key}**\n"
                f"Accent: `{accent}`\n"
                f"About: {about}\n\n"
                "`b profilecustomize background <zone>`\n"
                "`b profilecustomize accent <hex|preset|default>`\n"
                "`b profilecustomize about <text|clear>`\n"
                "`b profilecustomize reset`"
            ),
            color=_profile_embed_color(cosmetics.get("accent_color")),
        )
        embed.add_field(name="Backgrounds", value=_available_profile_backgrounds()[:1024], inline=False)
        embed.add_field(name="Accent Presets", value=", ".join(PROFILE_ACCENT_PRESETS), inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @profilecustomize.command(name="background", aliases=["bg"])
    async def profile_background(self, ctx: commands.Context, *, zone: str) -> None:
        """Set your profile card background."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        try:
            selected = get_zone(zone)
        except ValueError as exc:
            raise commands.BadArgument(f"{exc}\nAvailable backgrounds: {_available_profile_backgrounds()}") from exc
        cosmetics = await self._set_profile_cosmetics(ctx.author.id, background_key=selected.key)
        await ctx.reply(
            embed=status_embed(
                "Profile Background Updated",
                f"Your profile background is now **{selected.name}**.",
                color=_profile_embed_color(cosmetics.get("accent_color")),
            ),
            mention_author=False,
        )

    @profilecustomize.command(name="accent")
    async def profile_accent(self, ctx: commands.Context, *, color: str) -> None:
        """Set your profile card accent color."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        normalized = _normalize_profile_color(color)
        cosmetics = await self._set_profile_cosmetics(ctx.author.id, accent_color=normalized)
        label = "the background default" if not normalized else f"`{normalized}`"
        await ctx.reply(
            embed=status_embed(
                "Profile Accent Updated",
                f"Your profile accent now uses {label}.",
                color=_profile_embed_color(cosmetics.get("accent_color")),
            ),
            mention_author=False,
        )

    @profilecustomize.command(name="about", aliases=["bio"])
    async def profile_about(self, ctx: commands.Context, *, text: str) -> None:
        """Set your profile card about text."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        cleaned = " ".join(text.strip().split())
        if cleaned.lower() in {"clear", "reset", "none", "default"}:
            cleaned = ""
        if len(cleaned) > 140:
            raise commands.BadArgument("About text must be 140 characters or fewer.")
        cosmetics = await self._set_profile_cosmetics(ctx.author.id, about=cleaned)
        description = "Your about text now uses the selected background's flavor." if not cleaned else cleaned
        await ctx.reply(
            embed=status_embed(
                "Profile About Updated",
                description,
                color=_profile_embed_color(cosmetics.get("accent_color")),
            ),
            mention_author=False,
        )

    @profilecustomize.command(name="reset")
    async def profile_reset(self, ctx: commands.Context) -> None:
        """Reset your profile card cosmetics."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        await self.bot.db.execute("DELETE FROM rpg_profile_cosmetics WHERE user_id = ?", (ctx.author.id,))
        await ctx.reply(
            embed=status_embed("Profile Customization Reset", "Your profile card is back to its zone defaults."),
            mention_author=False,
        )

    @commands.hybrid_command(name="bestiary", aliases=["zoo", "den", "pets", "collection", "vault"])
    async def bestiary(self, ctx: commands.Context, *, content: str = "") -> None:
        """View your monster collection. Pass 'd' for dense view."""
        assert ctx.guild is not None
        content = content.strip()

        if content.lower() in ("d", "dense"):
            target = ctx.author
            await ensure_player(self.bot.db, target.id, target.display_name)
            text = await _build_dense_zoo(self.bot.db, target.id, target.display_name, str(target.display_avatar.url))
            chunks: list[str] = []
            while text:
                if len(text) <= 1900:
                    chunks.append(text)
                    break
                split_at = text.rfind("\n", 0, 1900)
                if split_at == -1:
                    split_at = 1900
                chunks.append(text[:split_at])
                text = text[split_at:].lstrip("\n")
            for idx, chunk in enumerate(chunks):
                if idx == 0:
                    await ctx.reply(chunk, mention_author=False)
                else:
                    await ctx.send(chunk)
            return

        target = ctx.author
        page = 1
        if content:
            try:
                page = max(1, int(content))
            except ValueError:
                try:
                    converter = commands.MemberConverter()
                    target = await converter.convert(ctx, content)
                except commands.MemberNotFound:
                    pass

        await ensure_player(self.bot.db, target.id, target.display_name)
        view = BestiaryView(self.bot, target.id, target.display_name, str(target.display_avatar.url), page)
        embed, files = await view._build_page()

        if embed.description:
            embed.set_author(name=str(target), icon_url=target.display_avatar.url)
            await ctx.reply(embed=embed, mention_author=False)
            return

        await ctx.reply(embed=embed, files=files, view=view, mention_author=False)

    @commands.hybrid_command(name="zoodense", aliases=["zood", "zoode", "bestiaryd", "bd"])
    async def bestiary_dense(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        """Show your Abyssian monster collection in dense OwO-style format."""
        assert ctx.guild is not None
        target = member or ctx.author
        await ensure_player(self.bot.db, target.id, target.display_name)

        text = await _build_dense_zoo(self.bot.db, target.id, target.display_name, str(target.display_avatar.url))
        chunks: list[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= 1900:
                chunks.append(remaining)
                break
            split_at = remaining.rfind("\n", 0, 1900)
            if split_at == -1:
                split_at = 1900
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip("\n")
        for idx, chunk in enumerate(chunks):
            if idx == 0:
                await ctx.reply(chunk, mention_author=False)
            else:
                await ctx.send(chunk)

    @commands.hybrid_command(name="monsters")
    async def monsters(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        """Show a hunter's monster collection."""
        await self.bestiary.callback(self, ctx, member)

    @commands.hybrid_command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx: commands.Context) -> None:
        """Show your materials, crates, and items. Use buttons to open crates or use items."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        rows = await inventory_rows(self.bot.db, ctx.author.id)
        if not rows:
            await ctx.reply(embed=status_embed("Inventory", "Your inventory is empty."), mention_author=False)
            return
        sections: dict[str, list[tuple[str, int]]] = {}
        has_crates = False
        has_swords = False
        has_lootboxes = False
        for row in rows:
            item_type = str(row["item_type"])
            key = str(row["item_key"])
            quantity = int(row["quantity"])
            if quantity <= 0:
                continue
            if item_type == "equipment" and key == "rusted_sword":
                continue
            if item_type == "material":
                if key != WEAPON_SHARD_KEY:
                    continue
                name = material_label(key)
            elif item_type == "consumable" and key == HUNT_SWORD_KEY:
                name = consumable_label(HUNT_SWORD_KEY, HUNT_SWORD_NAME)
                has_swords = True
            elif item_type == "consumable" and key == "cookie":
                continue
            elif item_type == "crate":
                from core.rpg_data import CRATE_TYPES
                crate = CRATE_TYPES.get(key, {})
                name = crate_label(key, str(crate.get("name", key.replace("_", " ").title())))
                has_crates = True
            elif item_type == "lootbox":
                name = crate_label("cache", "Lootbox")
                has_lootboxes = True
            elif item_type == "equipment":
                name = equipment_label(key, key.replace("_", " ").title())
            else:
                name = key.replace("_", " ").title()
            sections.setdefault(item_type, []).append((name, quantity))
        if not sections:
            await ctx.reply(embed=status_embed("Inventory", "Your inventory has no active items."), mention_author=False)
            return
        embed = dark_embed(
            "Inventory",
            f"{currency_label('gold')} **{int(player['gold']):,}**   {currency_label('gems')} **{int(player['gems']):,}**",
            color=discord.Color.dark_gold(),
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        label_map = {
            "material": "Materials",
            "lootbox": "Lootboxes",
            "consumable": "Consumables",
            "crate": "Weapon Crates",
            "equipment": "Legacy Equipment",
            "weapon": "Weapons",
        }
        order = ["crate", "lootbox", "consumable", "material", "equipment", "weapon"]
        for section in order + sorted(k for k in sections if k not in order):
            lines = sections.get(section, [])
            if not lines:
                continue
            lines.sort(key=lambda item: item[0].lower())
            value = "\n".join(f"{name} `x{quantity:,}`" for name, quantity in lines[:12])
            extra = len(lines) - 12
            if extra > 0:
                value += f"\n...and {extra} more"
            embed.add_field(name=label_map.get(section, section.title()), value=value, inline=True)
        embed.set_footer(text="Use the buttons below for quick item actions.")
        
        view = InventoryView(ctx, has_crates=has_crates, has_swords=has_swords, has_lootboxes=has_lootboxes)
        await ctx.reply(embed=embed, view=view, mention_author=False)

    # ── Daily ──────────────────────────────────────────────────────

    @commands.hybrid_command(name="daily")
    async def daily(self, ctx: commands.Context) -> None:
        """Claim your daily reward."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        today_start = utc_day_start()
        if int(player["last_daily_at"]) >= today_start:
            await ctx.reply(embed=status_embed("Daily", "You already claimed today's daily reward."), mention_author=False)
            return
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
