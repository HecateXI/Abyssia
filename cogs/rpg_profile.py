from __future__ import annotations

import math
import random

import discord
from discord.ext import commands

from core.card_controls import ButtonContext, shortcut_view
from core.card_layout import AbyssiaLayoutView
from core.card_ui import run_render
from core.cards import (
    render_collection_card,
    render_hub_progress_pillow,
    render_hub_rewards_pillow,
    render_hub_tasks_pillow,
    render_profile_card,
)
from core.items import HUNT_SWORD_KEY, HUNT_SWORD_NAME

from core.rpg import (
    CHECKLIST_BATTLE_CRATE_TARGET,
    CHECKLIST_HUNT_LOOTBOX_TARGET,
    add_item,
    award_currency,
    checklist_is_complete,
    claim_daily_checklist_reward,
    creature_xp_for_level,
    daily_reset_text,
    ensure_arena_stats,
    ensure_daily_checklist,
    ensure_player,
    get_creature_counts,
    get_creature_zoo_summary,
    get_zone,
    get_active_buffs,
    get_quantity,
    inventory_rows,
    mark_checklist_daily,
    now_ts,
    team_creatures,
    refresh_player,
    today_key,
    utc_day_start,
    week_key,
    xp_for_level,
)
from core.rpg_data import ACHIEVEMENTS, CREATURES, QUESTS, RARITIES, WEAPON_SHARD_KEY, ZONES
from core.theme import (
    DARK_COLOR,
    GOLD_COLOR,
    consumable_label,
    creature_emoji,
    crate_label,
    currency_emoji,
    currency_label,
    dark_embed,
    material_label,
    rarity_emoji,
    status_embed,
    ui_label,
)


RARITY_ORDER = [r.name for r in RARITIES]
RARITY_SORT_INDEX = {rarity: idx for idx, rarity in enumerate(RARITY_ORDER)}


_SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _superscript(n: int) -> str:
    return str(n).translate(_SUPERSCRIPT)


def _currency_icon(key: str) -> str:
    return currency_emoji(key) or currency_label(key)


async def _build_dense_zoo(db, target_id: int, target_name: str, target_avatar_url: str) -> str:
    """Build an OwO-style dense zoo display as plain text."""
    caught_map = await get_creature_zoo_summary(db, target_id)

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

    lines: list[str] = [
        f"**{target_name}'s Abyssia Zoo**",
        f"`{species_caught}/{species_total}` species | `{total_creatures:,}` creatures | `{total_points:,}` points",
    ]

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
        header = f"{rmob} **{rarity}**{_superscript(total_in_rarity)}" if rmob else f"**{rarity}**{_superscript(total_in_rarity)}"

        parts: list[str] = []
        for name, count in creatures:
            emoji = creature_emoji(name)
            if emoji:
                parts.append(f"{emoji}{_superscript(count)}")
            else:
                parts.append(f"`{name[:12]}`{_superscript(count)}")

        rows: list[str] = []
        current_row = header
        for p in parts:
            if len(current_row) + 1 + len(p) > 760:
                rows.append(current_row)
                current_row = f"  {p}"
            else:
                current_row += " " + p
        if current_row:
            rows.append(current_row)
        
        lines.extend(rows)

    if species_caught == 0:
        lines.append("*No creatures caught yet.*")
    elif missing_counts:
        lines.append(f"Missing: {', '.join(missing_counts)}")

    return "\n".join(lines)


SPECIES_PER_PAGE = 5

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


class InventoryOpenCrateButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, *, disabled: bool) -> None:
        super().__init__(
            label="Open Box",
            style=discord.ButtonStyle.secondary,
            emoji="\U0001f4e6",
            disabled=disabled,
        )
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        from cogs.rpg_shop import CrateOpenView
        db = self.ctx.bot.db
        await ensure_player(db, self.ctx.author.id, self.ctx.author.display_name)
        view = CrateOpenView(self.ctx)
        if not await view.load_owned_options():
            await interaction.followup.send(
                "No lootboxes or crates found. Hunt for lootboxes or buy one with `b shardcrate cache`.",
                ephemeral=True,
            )
            return
        embed = discord.Embed(
            title="Open Box",
            description="Choose a lootbox or weapon crate to open.",
            color=discord.Color.orange(),
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class InventoryBulkOpenButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, *, disabled: bool) -> None:
        super().__init__(
            label="Bulk Open",
            style=discord.ButtonStyle.primary,
            emoji="\U0001f4e6",
            disabled=disabled,
        )
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        from cogs.rpg_shop import MassOpenView

        view = MassOpenView(self.ctx)
        if not await view.load_owned_options():
            await interaction.followup.send("No lootboxes or weapon crates are available for bulk opening.", ephemeral=True)
            return
        embed = discord.Embed(
            title="Bulk Open",
            description="Choose a lootbox or weapon crate stack. This opens the whole stack at once.",
            color=discord.Color.orange(),
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class InventoryUseSwordButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, *, disabled: bool) -> None:
        super().__init__(
            label="Use Hunt Sword",
            style=discord.ButtonStyle.primary,
            emoji="\u2694\ufe0f",
            disabled=disabled,
        )
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        db = self.ctx.bot.db
        qty = await get_quantity(db, self.ctx.author.id, "consumable", HUNT_SWORD_KEY)
        if qty <= 0:
            await interaction.followup.send("No Hunt Swords in inventory.", ephemeral=True)
            return
        from cogs.rpg_hunting import SWORD_BUFF_KEY, SWORD_DURATION, _check_sword_active, _get_sword_activated_at
        from core.rpg import activate_buff

        active = await _check_sword_active(db, self.ctx.author.id)
        if active:
            remaining = SWORD_DURATION - (now_ts() - await _get_sword_activated_at(db, self.ctx.author.id))
            mins = max(0, remaining // 60)
            await interaction.followup.send(
                f"Hunt Sword already active. **{mins}** min remaining. Use `b hunt` for 1.3x catch rate.",
                ephemeral=True,
            )
            return
        await add_item(db, self.ctx.author.id, "consumable", HUNT_SWORD_KEY, -1)
        await activate_buff(db, self.ctx.author.id, SWORD_BUFF_KEY, "consumable", 1)
        embed = discord.Embed(
            title=f"{consumable_label(HUNT_SWORD_KEY, HUNT_SWORD_NAME)} Activated",
            description=f"1.3x catch rate for **20 minutes**\n`{qty - 1}` sword(s) remaining\n\nUse `b hunt` now.",
            color=discord.Color.dark_green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class QuestRerollButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, *, disabled: bool) -> None:
        super().__init__(
            label="Reroll Daily",
            style=discord.ButtonStyle.primary,
            emoji="\U0001f3b2",
            disabled=disabled,
        )
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("These quest controls belong to another hunter.", ephemeral=True)
            return
        cog = self.ctx.bot.get_cog("RPGProfile")
        if cog is None or not isinstance(cog, RPGProfile):
            await interaction.response.send_message("Quest controls are not ready.", ephemeral=True)
            return
        try:
            replaced, new_key = await cog._reroll_daily_quest(self.ctx.author.id)
        except commands.BadArgument as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.defer()
        notice = f"Rerolled **{QUESTS[replaced]['name']}** into **{QUESTS[new_key]['name']}**."
        view, files = await cog._build_quests_view(self.ctx, notice=notice)
        if interaction.message is not None:
            await interaction.message.edit(attachments=files, view=view)


class HubTabButton(discord.ui.Button):
    def __init__(self, screen: str, current: str) -> None:
        labels = {"daily": "Daily", "weekly": "Weekly", "quests": "Quests"}
        emojis = {"daily": "\U0001f4cb", "weekly": "\U0001f5d3\ufe0f", "quests": "\U0001f4dc"}
        super().__init__(
            label=labels.get(screen, screen.title()),
            style=discord.ButtonStyle.primary if screen == current else discord.ButtonStyle.secondary,
            emoji=emojis.get(screen),
            disabled=screen == current,
        )
        self.screen = screen

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("RPGProfile")
        if cog is None or not isinstance(cog, RPGProfile):
            await interaction.response.send_message("Hub controls are not ready.", ephemeral=True)
            return
        ctx = ButtonContext(interaction)
        await interaction.response.defer()
        if self.screen == "weekly":
            view, files = await cog._build_weekly_view(ctx)
        elif self.screen == "quests":
            view, files = await cog._build_quests_view(ctx)
        else:
            player = await ensure_player(cog.bot.db, interaction.user.id, interaction.user.display_name)
            view, files = await cog._build_daily_view(ctx, player)
        if interaction.message is not None:
            await interaction.message.edit(attachments=files, view=view)


class DailyClaimButton(discord.ui.Button):
    def __init__(self, *, disabled: bool) -> None:
        super().__init__(label="Claim Daily", style=discord.ButtonStyle.success, emoji="\U0001f381", disabled=disabled)

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("RPGProfile")
        if cog is None or not isinstance(cog, RPGProfile):
            await interaction.response.send_message("Daily controls are not ready.", ephemeral=True)
            return
        ctx = ButtonContext(interaction)
        await interaction.response.defer()
        claimed_rewards, player = await cog._claim_daily_reward(ctx)
        notice = "Daily claimed" if claimed_rewards else "Already claimed"
        view, files = await cog._build_daily_view(ctx, player, claimed_rewards=claimed_rewards, notice=notice)
        if interaction.message is not None:
            await interaction.message.edit(attachments=files, view=view)


class ChecklistClaimButton(discord.ui.Button):
    def __init__(self, *, disabled: bool) -> None:
        super().__init__(label="Claim Rewards", style=discord.ButtonStyle.success, emoji="\U0001f381", disabled=disabled)

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("RPGProfile")
        if cog is None or not isinstance(cog, RPGProfile):
            await interaction.response.send_message("Checklist controls are not ready.", ephemeral=True)
            return
        row = await ensure_daily_checklist(cog.bot.db, interaction.user.id)
        if not checklist_is_complete(row) or bool(row["reward_claimed"]):
            await interaction.response.send_message("No checklist reward is ready yet.", ephemeral=True)
            return
        claimed_rewards = await claim_daily_checklist_reward(cog.bot.db, interaction.user.id)
        row = await ensure_daily_checklist(cog.bot.db, interaction.user.id)
        player = await ensure_player(cog.bot.db, interaction.user.id, interaction.user.display_name)
        ctx = ButtonContext(interaction)
        await interaction.response.defer()
        view, files = await cog._build_daily_view(ctx, player, checklist_row=row, checklist_rewards=claimed_rewards, notice="Checklist rewards claimed")
        if interaction.message is not None:
            await interaction.message.edit(attachments=files, view=view)


class QuestClaimButton(discord.ui.Button):
    def __init__(self, *, disabled: bool = False) -> None:
        super().__init__(label="Claim Quests", style=discord.ButtonStyle.success, emoji="\U0001f381", disabled=disabled)

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("RPGProfile")
        if cog is None or not isinstance(cog, RPGProfile):
            await interaction.response.send_message("Quest controls are not ready.", ephemeral=True)
            return
        claimed, total_gold, total_gems, total_shards = await cog._claim_ready_quests(interaction.user.id)
        if claimed:
            notice = f"Claimed {len(claimed)} quest(s)"
        else:
            notice = "Nothing ready"
        ctx = ButtonContext(interaction)
        await interaction.response.defer()
        view, files = await cog._build_quests_view(ctx, notice=notice)
        if interaction.message is not None:
            await interaction.message.edit(attachments=files, view=view)


class HubPanelView(discord.ui.LayoutView):
    def __init__(
        self,
        *,
        owner_id: int,
        screen: str,
        title: str,
        subtitle: str,
        balance: str,
        task_filename: str,
        progress_filename: str,
        reward_filename: str | None = None,
        notice: str | None = None,
        footer: str | None = None,
        action_buttons: tuple[discord.ui.Button, ...] = (),
    ) -> None:
        super().__init__(timeout=180)
        self.owner_id = owner_id
        container = discord.ui.Container(accent_colour=GOLD_COLOR)
        tab_row = discord.ui.ActionRow()
        for tab in ("daily", "weekly", "quests"):
            tab_row.add_item(HubTabButton(tab, screen))
        container.add_item(tab_row)
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        header = f"### {title}\n{subtitle}"
        if balance:
            header += f"\n{balance}"
        if notice:
            header += f"\n`{notice}`"
        container.add_item(discord.ui.TextDisplay(header))
        container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    f"attachment://{task_filename}",
                    description=f"Abyssia {screen} tasks",
                )
            )
        )
        if reward_filename:
            container.add_item(discord.ui.TextDisplay("**Rewards**"))
            container.add_item(
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(
                        f"attachment://{reward_filename}",
                        description=f"Abyssia {screen} rewards",
                    )
                )
            )
        container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    f"attachment://{progress_filename}",
                    description=f"Abyssia {screen} progress",
                )
            )
        )
        if footer:
            container.add_item(discord.ui.TextDisplay(footer))
        if action_buttons:
            action_row = discord.ui.ActionRow()
            for button in action_buttons[:5]:
                action_row.add_item(button)
            container.add_item(action_row)
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("This hub belongs to another hunter.", ephemeral=True)
        return False


class RaritySelect(discord.ui.Select):
    def __init__(self, selected: str = "all") -> None:
        options = [
            discord.SelectOption(label=label, value=value, default=value == selected)
            for label, value in RARITY_OPTIONS
        ]
        super().__init__(placeholder="Filter by rarity...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        view: BestiaryView = self.view  # type: ignore
        view.selected_rarity = self.values[0]
        view.page = 1
        await view._edit_page(interaction)


class BestiaryPageButton(discord.ui.Button):
    def __init__(self, direction: int, *, disabled: bool = False) -> None:
        super().__init__(
            label="Prev" if direction < 0 else "Next",
            style=discord.ButtonStyle.secondary,
            emoji="◀️" if direction < 0 else "▶️",
            disabled=disabled,
        )
        self.direction = direction

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, BestiaryView):
            await interaction.response.send_message("This zoo page expired.", ephemeral=True)
            return
        if self.direction < 0 and view.page <= 1:
            await interaction.response.defer()
            return
        if self.direction > 0 and view.page >= view.total_pages:
            await interaction.response.defer()
            return
        view.page += self.direction
        await view._edit_page(interaction)


class BestiaryDexSelect(discord.ui.Select):
    def __init__(self, entries: list[dict]) -> None:
        options: list[discord.SelectOption] = []
        for entry in entries[:5]:
            name = str(entry.get("name", "Unknown"))
            rarity = str(entry.get("rarity", "Common"))
            total = int(entry.get("total", 0) or 0)
            level = int(entry.get("max_level", 0) or 0)
            icon = creature_emoji(name, rarity) or rarity_emoji(rarity)
            options.append(
                discord.SelectOption(
                    label=name[:100],
                    value=name[:100],
                    description=f"x{total} | Lv.{level}"[:100],
                    emoji=discord.PartialEmoji.from_str(icon) if icon and icon.startswith("<") else None,
                )
            )
        super().__init__(placeholder="Open dex card for displayed creature...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        cog = interaction.client.get_cog("Bestiary")
        command = getattr(cog, "dex", None) if cog is not None else None
        callback = getattr(command, "callback", None)
        if callback is None:
            await interaction.response.send_message("Dex command is not ready.", ephemeral=True)
            return
        ctx = ButtonContext(interaction)
        await callback(cog, ctx, creature_name=self.values[0])


class BestiaryView(discord.ui.LayoutView):
    def __init__(self, bot, target_id: int, target_name: str, target_avatar_url: str, page: int, *, viewer_id: int | None = None) -> None:
        super().__init__(timeout=180)
        self.bot = bot
        self.target_id = target_id
        self.viewer_id = viewer_id or target_id
        self.target_name = target_name
        self.target_avatar_url = target_avatar_url
        self.page = page
        self.total_pages = 1
        self.selected_rarity = "all"
        self._caught_map = None
        self._entries = None
        self._last_filename = "abyssia_collection.png"

    def _update_buttons(self) -> None:
        return

    async def _load_caught_map(self) -> dict:
        if self._caught_map is None:
            self._caught_map = await get_creature_counts(self.bot.db, self.target_id)
        return self._caught_map

    async def _build_entries(self, caught_map: dict) -> list:
        """Build entry list once, filtered by current rarity."""
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
        entries.sort(key=lambda e: (RARITY_SORT_INDEX.get(str(e["rarity"]), 10_000), 0 if e["caught"] else 1, str(e["name"])))
        return entries

    def _refresh_layout(self, *, rarity_label: str, caught_count: int, total_templates: int, page_entries: list[dict]) -> None:
        self.clear_items()
        container = discord.ui.Container(accent_colour=DARK_COLOR)
        container.add_item(
            discord.ui.TextDisplay(
                f"## {self.target_name}'s Index ({caught_count}/{total_templates})\n"
                f"Page `{self.page}/{self.total_pages}` • {rarity_label}"
            )
        )
        shown_lines: list[str] = []
        for idx, entry in enumerate(page_entries[:5], start=1):
            name = str(entry.get("name", "Unknown"))
            rarity = str(entry.get("rarity", "Common"))
            icon = creature_emoji(name, rarity) or rarity_emoji(rarity)
            rarity_icon = rarity_emoji(rarity) or rarity
            total = int(entry.get("total", 0) or 0)
            level = int(entry.get("max_level", 0) or 0)
            shown_lines.append(f"`{idx}.` {icon} **{name}** {rarity_icon} x`{total}` Lv.`{level}`")
        container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    f"attachment://{self._last_filename}",
                    description=f"{self.target_name}'s Abyssia zoo page {self.page}",
                )
            )
        )
        pct = caught_count / max(1, total_templates)
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(
            discord.ui.TextDisplay(
                f"**Collection**\n"
                f"`{caught_count}/{total_templates}` species discovered • `{pct:.1%}` complete"
            )
        )
        if shown_lines:
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay("**Displayed Creatures**\n" + "\n".join(shown_lines)))
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        select_row = discord.ui.ActionRow()
        select_row.add_item(RaritySelect(self.selected_rarity))
        container.add_item(select_row)
        if page_entries:
            dex_row = discord.ui.ActionRow()
            dex_row.add_item(BestiaryDexSelect(page_entries))
            container.add_item(dex_row)
        button_row = discord.ui.ActionRow()
        button_row.add_item(BestiaryPageButton(-1, disabled=self.page <= 1))
        button_row.add_item(BestiaryPageButton(1, disabled=self.page >= self.total_pages))
        container.add_item(button_row)
        self.add_item(container)

    async def _build_page(self) -> list[discord.File]:
        caught_map = await self._load_caught_map()
        entries = await self._build_entries(caught_map)
        total_templates = len(entries)
        caught_count = sum(1 for e in entries if e["caught"])
        self.total_pages = max(1, -(-total_templates // SPECIES_PER_PAGE))
        self.page = max(1, min(self.page, self.total_pages))

        start = (self.page - 1) * SPECIES_PER_PAGE
        page_entries = entries[start:start + SPECIES_PER_PAGE]
        next_entries = entries[start + SPECIES_PER_PAGE:start + SPECIES_PER_PAGE * 2]
        filter_key = str(self.selected_rarity).lower().replace(" ", "_")
        self._last_filename = f"abyssia_collection_{self.target_id}_{filter_key}_{self.page}.png"

        rarity_label = self.selected_rarity.title() if self.selected_rarity != "all" else "All Rarities"
        image = await run_render(
            render_collection_card,
            self.target_name,
            page_entries,
            caught_count,
            total_templates,
            self.page,
            self.total_pages,
            next_entries=next_entries,
            layout_version=3,
        )
        card_file = discord.File(image, filename=self._last_filename)
        self._refresh_layout(rarity_label=rarity_label, caught_count=caught_count, total_templates=total_templates, page_entries=page_entries)
        return [card_file]

    async def _edit_page(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        files = await self._build_page()
        if interaction.message is not None:
            await interaction.message.edit(content=None, attachments=files, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.viewer_id:
            return True
        await interaction.response.send_message("This collection view belongs to another hunter.", ephemeral=True)
        return False


UPGRADE_MAX_CREATURE_LEVEL = 100


def _creature_upgrade_costs(creature) -> dict[str, int]:
    level = max(1, int(creature["level"]))
    xp = max(0, int(creature["xp"]))
    needed = creature_xp_for_level(level)
    missing = max(0, needed - xp)
    if level >= UPGRADE_MAX_CREATURE_LEVEL:
        missing = 0
    return {
        "level": level,
        "xp": xp,
        "needed": needed,
        "missing": missing,
        "gems": max(1, math.ceil(missing / 4500) + math.ceil(level / 8)) if missing else 0,
        "souls": max(0, missing * 8 + (level ** 3) * 25) if missing else 0,
    }


def _upgrade_creature_title(creature) -> str:
    icon = creature_emoji(str(creature["name"]), str(creature["rarity"])) or rarity_emoji(str(creature["rarity"]))
    return f"{icon + ' ' if icon else ''}{creature['name']} Lv.{int(creature['level'])}"


class CreatureUpgradeTeamButton(discord.ui.Button):
    def __init__(self, creature, slot: int, *, is_selected: bool) -> None:
        level = int(creature["level"])
        name = str(creature["name"])
        rarity = str(creature["rarity"])
        emoji_str = creature_emoji(name, rarity) or rarity_emoji(rarity) or ""
        partial = None
        if emoji_str:
            try:
                partial = discord.PartialEmoji.from_str(emoji_str)
            except Exception:
                partial = None
        super().__init__(
            label=f"Slot {slot}: {name[:40]} Lv.{level}"[:80],
            emoji=partial,
            style=discord.ButtonStyle.primary if is_selected else discord.ButtonStyle.secondary,
        )
        self.creature_id = int(creature["id"])

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, CreatureUpgradeView):
            await interaction.response.send_message("Upgrade panel expired.", ephemeral=True)
            return
        selected = await view.cog._get_upgrade_creature(view.owner_id, self.creature_id)
        if selected is None:
            await interaction.response.send_message("That creature could not be found anymore.", ephemeral=True)
            return
        choices = await view.cog._upgrade_choices(view.owner_id)
        team = await team_creatures(view.cog.bot.db, view.owner_id)
        await interaction.response.edit_message(
            view=CreatureUpgradeView(
                view.cog,
                owner_id=view.owner_id,
                display_name=view.display_name,
                selected=selected,
                choices=choices,
                team=team,
            )
        )


class CreatureUpgradeButton(discord.ui.Button):
    def __init__(self, currency: str, *, disabled: bool) -> None:
        super().__init__(
            label="Use Void Gems" if currency == "gems" else "Use Souls",
            emoji=(currency_emoji("gems") or None) if currency == "gems" else (currency_emoji("gold") or None),
            style=discord.ButtonStyle.primary if currency == "gems" else discord.ButtonStyle.secondary,
            disabled=disabled,
        )
        self.currency = currency

    async def callback(self, interaction: discord.Interaction) -> None:
        view_ref = self.view
        if not isinstance(view_ref, CreatureUpgradeView):
            await interaction.response.send_message("Upgrade panel expired.", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            selected, notice = await view_ref.cog._buy_creature_upgrade(
                view_ref.owner_id,
                int(view_ref.selected["id"]),
                self.currency,
            )
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        choices = await view_ref.cog._upgrade_choices(view_ref.owner_id)
        team = await team_creatures(view_ref.cog.bot.db, view_ref.owner_id)
        await interaction.edit_original_response(
            view=CreatureUpgradeView(
                view_ref.cog,
                owner_id=view_ref.owner_id,
                display_name=view_ref.display_name,
                selected=selected,
                choices=choices,
                team=team,
                notice=notice,
            )
        )


class CreatureUpgradeView(discord.ui.LayoutView):
    def __init__(
        self,
        cog: "RPGProfile",
        *,
        owner_id: int,
        display_name: str,
        selected,
        choices: list,
        team: list | None = None,
        notice: str | None = None,
    ) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.owner_id = owner_id
        self.display_name = display_name
        self.selected = selected
        self.choices = choices

        costs = _creature_upgrade_costs(selected)
        can_upgrade = costs["missing"] > 0
        selected_id = int(selected["id"])

        container = discord.ui.Container(accent_colour=discord.Color.purple())
        container.add_item(discord.ui.TextDisplay(f"## Creature Upgrade\n{display_name}"))

        # --- Team section ---
        team = list(team or [])
        if team:
            team_lines = []
            for slot, cr in enumerate(team, start=1):
                cr_id = int(cr["id"])
                cr_lv = int(cr["level"])
                cr_xp = int(cr["xp"])
                cr_needed = creature_xp_for_level(cr_lv)
                cr_name = str(cr["name"])
                cr_rarity = str(cr["rarity"])
                icon = creature_emoji(cr_name, cr_rarity) or rarity_emoji(cr_rarity) or "\U0001f47e"
                marker = "\U0001f3c6" if cr_id == selected_id else f"[{slot}]"
                team_lines.append(
                    f"{marker} {icon} **{cr_name}** {rarity_emoji(cr_rarity) or ''} "
                    f"Lv.`{cr_lv}` XP `{cr_xp:,}/{cr_needed:,}`"
                )
            container.add_item(discord.ui.TextDisplay("**Battle Team**\n" + "\n".join(team_lines)))

            # Team slot select buttons
            row = discord.ui.ActionRow()
            for slot, cr in enumerate(team, start=1):
                row.add_item(CreatureUpgradeTeamButton(cr, slot, is_selected=int(cr["id"]) == selected_id))
            container.add_item(row)
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))

        # --- Selected creature ---
        name = str(selected["name"])
        rarity = str(selected["rarity"])
        icon = creature_emoji(name, rarity) or rarity_emoji(rarity) or ""
        container.add_item(
            discord.ui.TextDisplay(
                f"**Selected**\n"
                f"{icon} **{name}** {rarity_emoji(rarity) or ''} `{rarity}`\n"
                f"Level `{costs['level']}` | XP `{costs['xp']:,}/{costs['needed']:,}` | Missing `{costs['missing']:,}`"
            )
        )
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(
            discord.ui.TextDisplay(
                "**Upgrade Cost**\n"
                f"{_currency_icon('gems')} `{costs['gems']:,}`\n"
                f"{_currency_icon('gold')} `{costs['souls']:,}`"
            )
        )
        if not can_upgrade:
            container.add_item(
                discord.ui.TextDisplay(f"Already at the current upgrade cap `Lv.{UPGRADE_MAX_CREATURE_LEVEL}`.")
            )
        if notice:
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(f"**Result**\n{notice}"))



        # --- Upgrade buttons ---
        row = discord.ui.ActionRow()
        row.add_item(CreatureUpgradeButton("gems", disabled=not can_upgrade))
        row.add_item(CreatureUpgradeButton("souls", disabled=not can_upgrade))
        container.add_item(row)
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("This upgrade panel belongs to another hunter.", ephemeral=True)
        return False


class RPGProfile(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _upgrade_choices(self, user_id: int) -> list:
        return await self.bot.db.fetchall(
            """
            SELECT *
            FROM rpg_creatures
            WHERE user_id = ?
            ORDER BY level DESC, xp DESC, value DESC, id DESC
            LIMIT 25
            """,
            (user_id,),
        )

    async def _get_upgrade_creature(self, user_id: int, creature_id: int):
        return await self.bot.db.fetchone(
            "SELECT * FROM rpg_creatures WHERE user_id = ? AND id = ?",
            (user_id, creature_id),
        )

    async def _find_upgrade_creature(self, user_id: int, query: str | None):
        if query:
            clean = query.strip()
            if clean.startswith("#"):
                clean = clean[1:]
            if clean.isdigit():
                row = await self._get_upgrade_creature(user_id, int(clean))
                if row is not None:
                    return row
            like = f"%{clean.lower().replace('-', ' ').replace('_', ' ')}%"
            return await self.bot.db.fetchone(
                """
                SELECT *
                FROM rpg_creatures
                WHERE user_id = ?
                  AND LOWER(REPLACE(REPLACE(name, '-', ' '), '_', ' ')) LIKE ?
                ORDER BY level DESC, value DESC, id DESC
                LIMIT 1
                """,
                (user_id, like),
            )
        choices = await self._upgrade_choices(user_id)
        return choices[0] if choices else None

    async def _buy_creature_upgrade(self, user_id: int, creature_id: int, currency: str):
        row = await self._get_upgrade_creature(user_id, creature_id)
        if row is None:
            raise ValueError("That creature could not be found.")
        costs = _creature_upgrade_costs(row)
        if costs["missing"] <= 0:
            raise ValueError("That creature is already at the current upgrade cap.")
        player = await refresh_player(self.bot.db, user_id)
        if currency == "gems":
            cost = costs["gems"]
            if int(player["gems"]) < cost:
                raise ValueError(f"Need {_currency_icon('gems')} **{cost:,}**, you have **{int(player['gems']):,}**.")
            await award_currency(self.bot.db, user_id, gems=-cost)
            paid = f"{_currency_icon('gems')} `{cost:,}`"
        elif currency == "souls":
            cost = costs["souls"]
            if int(player["gold"]) < cost:
                raise ValueError(f"Need {_currency_icon('gold')} **{cost:,}**, you have **{int(player['gold']):,}**.")
            await award_currency(self.bot.db, user_id, gold=-cost)
            paid = f"{_currency_icon('gold')} `{cost:,}`"
        else:
            raise ValueError("Currency must be gems or souls.")

        new_level = int(row["level"]) + 1
        await self.bot.db.execute(
            "UPDATE rpg_creatures SET level = ?, xp = 0 WHERE user_id = ? AND id = ?",
            (new_level, user_id, creature_id),
        )
        await self.bot.db.execute(
            """
            UPDATE rpg_creature_collection
            SET max_level = MAX(max_level, ?)
            WHERE user_id = ? AND name = ? AND rarity = ?
            """,
            (new_level, user_id, str(row["name"]), str(row["rarity"])),
        )
        refreshed = await self._get_upgrade_creature(user_id, creature_id)
        notice = f"Upgraded **{row['name']}** from Lv.`{int(row['level'])}` to Lv.`{new_level}` for {paid}."
        return refreshed, notice

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

    def _main_shortcuts(self) -> tuple[tuple[str, str], ...]:
        return (
            ("Daily", "b daily"),
            ("Quests", "b quests"),
            ("Weapons", "b weapons"),
            ("Zoo", "b zoo"),
        )

    def _quest_period_key(self, period_type: str) -> str:
        return week_key() if period_type == "weekly" else today_key()

    def _quest_pool(self, period_type: str) -> list[str]:
        return [
            key
            for key, quest in QUESTS.items()
            if str(quest.get("period", "daily")).lower() == period_type
        ]

    async def _ensure_quest_assignments(self, user_id: int, period_type: str) -> list:
        period_key = self._quest_period_key(period_type)
        pool = self._quest_pool(period_type)
        if not pool:
            return []
        slot_count = min(3, len(pool))
        rows = await self.bot.db.fetchall(
            """
            SELECT quest_key, slot, rerolls_used
            FROM rpg_quest_assignments
            WHERE user_id = ? AND period_type = ? AND period_key = ?
            ORDER BY slot ASC, quest_key ASC
            """,
            (user_id, period_type, period_key),
        )
        valid_rows = [row for row in rows if str(row["quest_key"]) in pool]
        invalid_keys = [str(row["quest_key"]) for row in rows if str(row["quest_key"]) not in pool]
        for key in invalid_keys:
            await self.bot.db.execute(
                """
                DELETE FROM rpg_quest_assignments
                WHERE user_id = ? AND period_type = ? AND period_key = ? AND quest_key = ?
                """,
                (user_id, period_type, period_key, key),
            )
        if len(valid_rows) >= slot_count:
            return valid_rows[:slot_count]

        used = {str(row["quest_key"]) for row in valid_rows}
        rerolls_used = max((int(row["rerolls_used"]) for row in valid_rows), default=0)
        available = [key for key in pool if key not in used]
        rng = random.Random(f"{user_id}:{period_type}:{period_key}")
        rng.shuffle(available)
        occupied_slots = {int(row["slot"]) for row in valid_rows}
        open_slots = [slot for slot in range(slot_count) if slot not in occupied_slots]
        for slot, key in zip(open_slots, available):
            await self.bot.db.execute(
                """
                INSERT OR IGNORE INTO rpg_quest_assignments
                    (user_id, period_type, period_key, quest_key, slot, rerolls_used, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, period_type, period_key, key, slot, rerolls_used, now_ts(), now_ts()),
            )
        return await self.bot.db.fetchall(
            """
            SELECT quest_key, slot, rerolls_used
            FROM rpg_quest_assignments
            WHERE user_id = ? AND period_type = ? AND period_key = ?
            ORDER BY slot ASC, quest_key ASC
            """,
            (user_id, period_type, period_key),
        )

    async def _quest_states(self, user_id: int, period_type: str) -> tuple[list[dict[str, object]], int]:
        assignments = await self._ensure_quest_assignments(user_id, period_type)
        period_key = self._quest_period_key(period_type)
        progress_rows = await self.bot.db.fetchall(
            "SELECT quest_key, progress, claimed FROM rpg_quests WHERE user_id = ? AND period_key = ?",
            (user_id, period_key),
        )
        progress = {str(row["quest_key"]): row for row in progress_rows}
        rerolls_used = max((int(row["rerolls_used"]) for row in assignments), default=0)
        states: list[dict[str, object]] = []
        for row in assignments:
            key = str(row["quest_key"])
            quest = QUESTS.get(key)
            if not quest:
                continue
            progress_row = progress.get(key)
            current = int(progress_row["progress"]) if progress_row else 0
            claimed = bool(progress_row and progress_row["claimed"])
            target = int(quest.get("target", 1))
            states.append({
                "key": key,
                "slot": int(row["slot"]),
                "quest": quest,
                "progress": min(current, target),
                "target": target,
                "claimed": claimed,
            })
        return states, rerolls_used

    def _quest_reward_text(self, quest: dict[str, object]) -> str:
        rewards: list[str] = []
        gold = int(quest.get("gold", 0))
        gems = int(quest.get("gems", 0))
        shards = int(quest.get("shards", 0))
        if gold:
            rewards.append(f"{_currency_icon('gold')} `{gold:,}`")
        if gems:
            rewards.append(f"{_currency_icon('gems')} `{gems:,}`")
        if shards:
            rewards.append(f"{material_label(WEAPON_SHARD_KEY)} `{shards:,}`")
        return "  ".join(rewards) if rewards else "No payout"

    def _quest_line(self, state: dict[str, object]) -> str:
        quest = state["quest"]
        assert isinstance(quest, dict)
        current = int(state["progress"])
        target = max(1, int(state["target"]))
        claimed = bool(state["claimed"])
        ready = current >= target
        status = "Claimed" if claimed else ("Ready to claim" if ready else f"{round((current / target) * 100)}%")
        mark = "\u2705" if claimed else ("\U0001f381" if ready else "\u25c6")
        difficulty = str(quest.get("difficulty", "Hard"))
        desc = str(quest.get("desc", "")).strip()
        desc_line = f"\n{desc}" if desc else ""
        return (
            f"{mark} **{quest['name']}** `{difficulty}`{desc_line}\n"
            f"`{current:,}/{target:,}` {status}\n"
            f"{self._quest_reward_text(quest)}"
        )

    def _quest_card_row(self, state: dict[str, object]) -> dict[str, object]:
        quest = state["quest"]
        assert isinstance(quest, dict)
        current = int(state["progress"])
        target = max(1, int(state["target"]))
        claimed = bool(state["claimed"])
        ready = current >= target and not claimed
        metric = str(quest.get("metric", "daily_hunts"))
        icon_key = "battle" if "battle" in metric else ("hunt" if "hunt" in metric else "profile")
        difficulty = str(quest.get("difficulty", "Hard"))
        desc = str(quest.get("desc", "")).strip()
        return {
            "label": str(quest.get("name", "Quest")),
            "desc": f"{difficulty} | {desc}" if desc else difficulty,
            "current": current,
            "target": target,
            "claimed": claimed,
            "ready": ready,
            "done": claimed,
            "icon_kind": "ui",
            "icon_key": icon_key,
        }

    def _hub_filename(self, ctx: commands.Context, screen: str) -> str:
        return f"abyssia_hub_{ctx.author.id}_{screen}_{now_ts()}_{random.randint(1000, 9999)}.png"

    def _reward_card_items(self, *, gold: int = 0, gems: int = 0, shards: int = 0, swords: int = 0, lootboxes: int = 0, crates: int = 0) -> list[dict[str, object]]:
        rewards: list[dict[str, object]] = []
        if gold:
            rewards.append({"label": "", "value": f"{gold:,}", "icon_kind": "currency", "icon_key": "souls", "color": (225, 176, 72)})
        if gems:
            rewards.append({"label": "", "value": f"{gems:,}", "icon_kind": "currency", "icon_key": "gems", "color": (78, 178, 190)})
        if shards:
            rewards.append({"label": "", "value": f"{shards:,}", "icon_kind": "materials", "icon_key": WEAPON_SHARD_KEY, "color": (142, 82, 198)})
        if swords:
            rewards.append({"label": "", "value": f"x{swords:,}", "icon_kind": "consumable", "icon_key": HUNT_SWORD_KEY, "color": (210, 112, 44)})
        if lootboxes:
            rewards.append({"label": "", "value": f"x{lootboxes:,}", "icon_kind": "crate", "icon_key": "cache", "color": (76, 178, 112)})
        if crates:
            rewards.append({"label": "", "value": f"x{crates:,}", "icon_kind": "crate", "icon_key": "cache", "color": (78, 178, 190)})
        return rewards

    async def _reroll_daily_quest(self, user_id: int) -> tuple[str, str]:
        states, rerolls_used = await self._quest_states(user_id, "daily")
        if rerolls_used >= 1:
            raise commands.BadArgument("Your daily quest reroll has already been used.")
        if not states:
            raise commands.BadArgument("No daily quests are available to reroll.")
        incomplete = [state for state in states if not bool(state["claimed"]) and int(state["progress"]) < int(state["target"])]
        replace = min(incomplete or states, key=lambda state: int(state["progress"]) / max(1, int(state["target"])))
        old_key = str(replace["key"])
        pool = self._quest_pool("daily")
        active = {str(state["key"]) for state in states}
        available = [key for key in pool if key not in active]
        if not available:
            raise commands.BadArgument("No alternate daily quest is available right now.")
        new_key = random.choice(available)
        period_key = today_key()
        slot = int(replace["slot"])
        timestamp = now_ts()
        await self.bot.db.execute(
            """
            DELETE FROM rpg_quest_assignments
            WHERE user_id = ? AND period_type = 'daily' AND period_key = ? AND quest_key = ?
            """,
            (user_id, period_key, old_key),
        )
        await self.bot.db.execute(
            """
            UPDATE rpg_quest_assignments
            SET rerolls_used = 1, updated_at = ?
            WHERE user_id = ? AND period_type = 'daily' AND period_key = ?
            """,
            (timestamp, user_id, period_key),
        )
        await self.bot.db.execute(
            """
            INSERT OR REPLACE INTO rpg_quest_assignments
                (user_id, period_type, period_key, quest_key, slot, rerolls_used, created_at, updated_at)
            VALUES (?, 'daily', ?, ?, ?, 1, ?, ?)
            """,
            (user_id, period_key, new_key, slot, timestamp, timestamp),
        )
        return old_key, new_key

    async def _claim_ready_quests(self, user_id: int) -> tuple[list[str], int, int, int]:
        claimed_names: list[str] = []
        total_gold = 0
        total_gems = 0
        total_shards = 0
        for period_type in ("daily", "weekly"):
            states, _ = await self._quest_states(user_id, period_type)
            period_key = self._quest_period_key(period_type)
            for state in states:
                quest = state["quest"]
                assert isinstance(quest, dict)
                if bool(state["claimed"]) or int(state["progress"]) < int(state["target"]):
                    continue
                key = str(state["key"])
                await self.bot.db.execute(
                    "UPDATE rpg_quests SET claimed = 1 WHERE user_id = ? AND quest_key = ? AND period_key = ?",
                    (user_id, key, period_key),
                )
                total_gold += int(quest.get("gold", 0))
                total_gems += int(quest.get("gems", 0))
                total_shards += int(quest.get("shards", 0))
                claimed_names.append(str(quest["name"]))
        if total_gold or total_gems:
            await award_currency(self.bot.db, user_id, gold=total_gold, gems=total_gems)
        if total_shards:
            await add_item(self.bot.db, user_id, "material", WEAPON_SHARD_KEY, total_shards)
        return claimed_names, total_gold, total_gems, total_shards

    async def _build_quests_view(self, ctx: commands.Context, *, notice: str | None = None) -> tuple[HubPanelView, list[discord.File]]:
        daily_states, rerolls_used = await self._quest_states(ctx.author.id, "daily")
        rerolls_left = max(0, 1 - rerolls_used)
        rows = [self._quest_card_row(state) for state in daily_states]
        ready = any(bool(row.get("ready")) for row in rows)
        progress_value = sum(1 for row in rows if bool(row.get("claimed")))
        rewards = self._reward_card_items(
            gold=sum(int(state["quest"].get("gold", 0)) for state in daily_states if isinstance(state["quest"], dict)),
            gems=sum(int(state["quest"].get("gems", 0)) for state in daily_states if isinstance(state["quest"], dict)),
            shards=sum(int(state["quest"].get("shards", 0)) for state in daily_states if isinstance(state["quest"], dict)),
        )
        base_filename = self._hub_filename(ctx, "quests").removesuffix(".png")
        task_filename = f"{base_filename}_tasks.png"
        reward_filename = f"{base_filename}_rewards.png"
        progress_filename = f"{base_filename}_progress.png"
        task_image = await run_render(render_hub_tasks_pillow, "quests", rows, layout_version=8)
        reward_image = await run_render(render_hub_rewards_pillow, "quests", rewards, layout_version=8)
        progress_image = await run_render(
            render_hub_progress_pillow,
            "quests",
            "Quest Progress",
            progress_value,
            max(1, len(rows)),
            footer="Claim completed contracts or reroll one unfinished daily quest.",
            layout_version=8,
        )
        balance = f"Daily reroll `{rerolls_left}/1` | Reset `{daily_reset_text()}`"
        view = HubPanelView(
            owner_id=ctx.author.id,
            screen="quests",
            title=f"{ctx.author.display_name}'s Quest Board",
            subtitle="Complete contracts for larger rewards.",
            balance=balance,
            task_filename=task_filename,
            reward_filename=reward_filename,
            progress_filename=progress_filename,
            notice=notice,
            footer="Daily contracts refresh every reset.",
            action_buttons=(
                QuestClaimButton(disabled=not ready),
                QuestRerollButton(ctx, disabled=rerolls_left <= 0),
            ),
        )
        return view, [
            discord.File(task_image, filename=task_filename),
            discord.File(reward_image, filename=reward_filename),
            discord.File(progress_image, filename=progress_filename),
        ]

    async def _build_weekly_view(self, ctx: commands.Context, *, notice: str | None = None) -> tuple[HubPanelView, list[discord.File]]:
        weekly_states, _ = await self._quest_states(ctx.author.id, "weekly")
        rows = [self._quest_card_row(state) for state in weekly_states]
        ready = any(bool(row.get("ready")) for row in rows)
        progress_value = sum(1 for row in rows if bool(row.get("claimed")))
        rewards = self._reward_card_items(
            gold=sum(int(state["quest"].get("gold", 0)) for state in weekly_states if isinstance(state["quest"], dict)),
            gems=sum(int(state["quest"].get("gems", 0)) for state in weekly_states if isinstance(state["quest"], dict)),
            shards=sum(int(state["quest"].get("shards", 0)) for state in weekly_states if isinstance(state["quest"], dict)),
        )
        base_filename = self._hub_filename(ctx, "weekly").removesuffix(".png")
        task_filename = f"{base_filename}_tasks.png"
        reward_filename = f"{base_filename}_rewards.png"
        progress_filename = f"{base_filename}_progress.png"
        task_image = await run_render(render_hub_tasks_pillow, "weekly", rows, layout_version=8)
        reward_image = await run_render(render_hub_rewards_pillow, "weekly", rewards, layout_version=8)
        progress_image = await run_render(
            render_hub_progress_pillow,
            "weekly",
            "Weekly Progress",
            progress_value,
            max(1, len(rows)),
            footer="Weekly oaths are harder and pay out larger rewards.",
            layout_version=8,
        )
        view = HubPanelView(
            owner_id=ctx.author.id,
            screen="weekly",
            title=f"{ctx.author.display_name}'s Weekly Oaths",
            subtitle="Long-form contracts with heavier payouts.",
            balance=f"Week `{week_key()}` | Reset `Monday`",
            task_filename=task_filename,
            reward_filename=reward_filename,
            progress_filename=progress_filename,
            notice=notice,
            footer="Weekly progress lasts until the next reset.",
            action_buttons=(QuestClaimButton(disabled=not ready),),
        )
        return view, [
            discord.File(task_image, filename=task_filename),
            discord.File(reward_image, filename=reward_filename),
            discord.File(progress_image, filename=progress_filename),
        ]

    def _build_inventory_view(
        self,
        ctx: commands.Context,
        player,
        sections: dict[str, list[tuple[str, int]]],
        *,
        has_crates: bool,
        has_swords: bool,
        has_lootboxes: bool,
    ) -> AbyssiaLayoutView:
        label_map = {
            "material": "Weapon Shards",
            "lootbox": "Lootboxes",
            "consumable": "Consumables",
            "crate": "Weapon Crates",
            "weapon": "Weapons",
        }
        order = ["crate", "lootbox", "consumable", "material", "weapon"]
        card_sections: list[tuple[str, str]] = [
            (
                "Wallet",
                f"{_currency_icon('gold')} `{int(player['gold']):,}`  "
                f"{_currency_icon('gems')} `{int(player['gems']):,}`",
            )
        ]
        for section in order + sorted(k for k in sections if k not in order):
            if section == "equipment":
                continue
            lines = sections.get(section, [])
            if not lines:
                continue
            lines.sort(key=lambda item: item[0].lower())
            value = "\n".join(f"{name} `x{quantity:,}`" for name, quantity in lines[:10])
            extra = len(lines) - 10
            if extra > 0:
                value += f"\n`+{extra}` more"
            card_sections.append((label_map.get(section, section.title()), value))
        return AbyssiaLayoutView(
            owner_id=ctx.author.id,
            title="Inventory",
            subtitle=f"{ctx.author.display_name} | Currency, boxes, shards, and usable supplies",
            sections=tuple(card_sections),
            footer="Open one box, bulk-open a whole stack, or jump to another hub page. Hunt Swords are activated from hunt cards.",
            buttons=(
                InventoryOpenCrateButton(ctx, disabled=not (has_crates or has_lootboxes)),
                InventoryBulkOpenButton(ctx, disabled=not (has_crates or has_lootboxes)),
            ),
            shortcuts=(
                ("Daily", "b daily"),
                ("Quests", "b quests"),
                ("Weapons", "b weapons"),
                ("Crate Shop", "b crateshop"),
            ),
            accent=discord.Color.dark_gold(),
        )

    def _daily_reward_values(self, player) -> dict[str, int]:
        return {
            "gold": 1500 + int(player["level"]) * 90,
            "gems": 35 + int(player["wisdom"]) // 2,
            "shards": 75 + int(player["level"]) * 2,
            "swords": 1 if int(player["level"]) >= 10 else 0,
        }

    async def _claim_daily_reward(self, ctx: commands.Context) -> tuple[dict[str, int] | None, object]:
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        if int(player["last_daily_at"]) >= utc_day_start():
            return None, player
        rewards = self._daily_reward_values(player)
        await award_currency(self.bot.db, ctx.author.id, gold=rewards["gold"], gems=rewards["gems"])
        await add_item(self.bot.db, ctx.author.id, "material", WEAPON_SHARD_KEY, rewards["shards"])
        await add_item(self.bot.db, ctx.author.id, "consumable", HUNT_SWORD_KEY, rewards["swords"])
        await self.bot.db.execute(
            "UPDATE rpg_players SET last_daily_at = ?, updated_at = ? WHERE user_id = ?",
            (now_ts(), now_ts(), ctx.author.id),
        )
        await mark_checklist_daily(self.bot.db, ctx.author.id)
        return rewards, await refresh_player(self.bot.db, ctx.author.id)

    async def _build_daily_view(
        self,
        ctx: commands.Context,
        player,
        *,
        claimed_rewards: dict[str, int] | None = None,
        checklist_row=None,
        checklist_rewards: dict[str, int] | None = None,
        notice: str | None = None,
    ) -> tuple[HubPanelView, list[discord.File]]:
        row = checklist_row or await ensure_daily_checklist(self.bot.db, ctx.author.id)
        daily_done = bool(row["daily_claimed"])
        hunt_count = min(CHECKLIST_HUNT_LOOTBOX_TARGET, int(row["hunt_lootboxes"]))
        battle_count = min(CHECKLIST_BATTLE_CRATE_TARGET, int(row["battle_crates"]))
        voted_done = bool(row["voted"])
        daily_states, _ = await self._quest_states(ctx.author.id, "daily")
        quest_claimed = sum(1 for state in daily_states if bool(state["claimed"]))
        quest_ready = any(int(state["progress"]) >= int(state["target"]) and not bool(state["claimed"]) for state in daily_states)
        rows = [
            {
                "label": "Claim Your Daily",
                "desc": "Collect the daily reward bundle.",
                "current": 1 if daily_done else 0,
                "target": 1,
                "done": daily_done,
                "icon_kind": "ui",
                "icon_key": "quest",
            },
            {
                "label": "Vote",
                "desc": "Vote on Top.gg when available.",
                "current": 1 if voted_done else 0,
                "target": 1,
                "done": voted_done,
                "icon_kind": "ui",
                "icon_key": "quest",
            },
            {
                "label": "Claim a Quest",
                "desc": "Finish and claim any daily contract.",
                "current": min(1, quest_claimed),
                "target": 1,
                "done": quest_claimed >= 1,
                "ready": quest_ready,
                "icon_kind": "ui",
                "icon_key": "quest",
            },
            {
                "label": "Find Lootboxes",
                "desc": "Hunt until lootboxes drop.",
                "current": hunt_count,
                "target": CHECKLIST_HUNT_LOOTBOX_TARGET,
                "done": hunt_count >= CHECKLIST_HUNT_LOOTBOX_TARGET,
                "icon_kind": "crate",
                "icon_key": "cache",
            },
            {
                "label": "Find Weapon Crates",
                "desc": "Win battles and recover weapon crates.",
                "current": battle_count,
                "target": CHECKLIST_BATTLE_CRATE_TARGET,
                "done": battle_count >= CHECKLIST_BATTLE_CRATE_TARGET,
                "icon_kind": "crate",
                "icon_key": "cache",
            },
        ]
        complete_count = sum(1 for task in rows if bool(task.get("done")))
        daily_preview = claimed_rewards or self._daily_reward_values(player)
        rewards = self._reward_card_items(
            gold=int(daily_preview.get("gold", 0)),
            gems=int(daily_preview.get("gems", 0)),
            shards=int(daily_preview.get("shards", 0)),
        )
        if checklist_rewards:
            rewards = self._reward_card_items(
                gold=int(checklist_rewards.get("gold", 0)),
                shards=int(checklist_rewards.get("shards", 0)),
                lootboxes=1,
                crates=1,
            )
        base_filename = self._hub_filename(ctx, "daily").removesuffix(".png")
        task_filename = f"{base_filename}_tasks.png"
        reward_filename = f"{base_filename}_rewards.png"
        progress_filename = f"{base_filename}_progress.png"
        if notice is None and claimed_rewards:
            notice = "Daily claimed"
        task_image = await run_render(render_hub_tasks_pillow, "daily", rows, layout_version=8)
        reward_image = await run_render(render_hub_rewards_pillow, "daily", rewards, layout_version=8)
        progress_image = await run_render(
            render_hub_progress_pillow,
            "daily",
            "Daily Progress",
            complete_count,
            len(rows),
            footer=f"Daily checklist resets at {daily_reset_text()}",
            layout_version=8,
        )
        checklist_ready = checklist_is_complete(row) and not bool(row["reward_claimed"])
        view = HubPanelView(
            owner_id=ctx.author.id,
            screen="daily",
            title=f"{ctx.author.display_name}'s Daily Checklist",
            subtitle="Complete tasks to earn your daily reward.",
            balance=f"Balance: {_currency_icon('gold')} `{int(player['gold']):,}` | {_currency_icon('gems')} `{int(player['gems']):,}`",
            task_filename=task_filename,
            reward_filename=reward_filename,
            progress_filename=progress_filename,
            notice=notice,
            footer="Daily actions and checklist rewards share this hub.",
            action_buttons=(
                DailyClaimButton(disabled=daily_done),
                ChecklistClaimButton(disabled=not checklist_ready),
            ),
        )
        return view, [
            discord.File(task_image, filename=task_filename),
            discord.File(reward_image, filename=reward_filename),
            discord.File(progress_image, filename=progress_filename),
        ]

    async def _build_checklist_view(
        self,
        ctx: commands.Context,
        row,
        *,
        claimed_rewards: dict[str, int] | None = None,
    ) -> tuple[HubPanelView, list[discord.File]]:
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        return await self._build_daily_view(ctx, player, checklist_row=row, checklist_rewards=claimed_rewards)

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
        embed = discord.Embed(
            title="📜 Hunter Contract Sealed",
            description=(
                f"**{player['hunter_name']}** scrawled their name in the Abyssia ledger.\n"
                "*The ink smokes. Somewhere, a bell tolls.*\n\n"
                "You are now bound to this realm. There is no turning back."
            ),
            color=GOLD_COLOR,
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.add_field(
            name="⛓️ Your First Chains",
            value=(
                "`b hunt` — Draw your first blade and bind a monster\n"
                "`b team` — Organize your growing军团\n"
                "`b profile` — Inspect your hunter's record\n"
                "`b help` — Learn the incantations"
            ),
            inline=False,
        )
        embed.add_field(
            name="💀 A Warning",
            value="The deeper you hunt, the darker the prey. Choose your weapons wisely. "
                  "Not all who enter Abyssia return the same.",
            inline=False,
        )
        embed.set_footer(text="Abyssia RPG - Dark Fantasy Monster Collector")
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="upgrade", aliases=["petupgrade", "creatureupgrade", "levelpet"])
    async def upgrade_creature(self, ctx: commands.Context, *, creature: str | None = None) -> None:
        """Upgrade one of your creatures with Void Gems or expensive Souls."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        selected = await self._find_upgrade_creature(ctx.author.id, creature)
        if selected is None:
            raise commands.BadArgument("You do not own any creatures to upgrade yet.")
        choices = await self._upgrade_choices(ctx.author.id)
        team = await team_creatures(self.bot.db, ctx.author.id)
        view = CreatureUpgradeView(
            self,
            owner_id=ctx.author.id,
            display_name=ctx.author.display_name,
            selected=selected,
            choices=choices,
            team=team,
        )
        await ctx.reply(view=view, mention_author=False)

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
        image = await run_render(
            render_profile_card,
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
        await ctx.reply(
            embed=embed,
            file=file,
            view=shortcut_view(
                ctx.author.id,
                [
                    ("Weapons", "b weapons"),
                    ("Zoo", "b zoo"),
                    ("Customize", "b profilecustomize"),
                ],
            ),
            mention_author=False,
        )

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
        view = BestiaryView(self.bot, target.id, target.display_name, str(target.display_avatar.url), page, viewer_id=ctx.author.id)
        files = await view._build_page()
        await ctx.reply(files=files, view=view, mention_author=False)

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
        """Show your shards, crates, and usable items."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        rows = await inventory_rows(self.bot.db, ctx.author.id)
        if not rows:
            view = self._build_inventory_view(
                ctx,
                player,
                {},
                has_crates=False,
                has_swords=False,
                has_lootboxes=False,
            )
            await ctx.reply(view=view, mention_author=False)
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
            if item_type == "equipment":
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
            else:
                name = key.replace("_", " ").title()
            sections.setdefault(item_type, []).append((name, quantity))
        if not sections:
            view = self._build_inventory_view(
                ctx,
                player,
                {},
                has_crates=False,
                has_swords=False,
                has_lootboxes=False,
            )
            await ctx.reply(view=view, mention_author=False)
            return
        view = self._build_inventory_view(
            ctx,
            player,
            sections,
            has_crates=has_crates,
            has_swords=has_swords,
            has_lootboxes=has_lootboxes,
        )
        await ctx.reply(view=view, mention_author=False)

    # ── Daily ──────────────────────────────────────────────────────

    @commands.hybrid_command(name="daily")
    async def daily(self, ctx: commands.Context) -> None:
        """Claim your daily reward."""
        assert ctx.guild is not None
        claimed_rewards, player = await self._claim_daily_reward(ctx)
        view, files = await self._build_daily_view(
            ctx,
            player,
            claimed_rewards=claimed_rewards,
        )
        await ctx.reply(files=files, view=view, mention_author=False)

    @commands.hybrid_command(name="checklist", aliases=["task", "tasks", "cl"])
    async def checklist(self, ctx: commands.Context) -> None:
        """Show today's checklist and claim the completion reward when ready."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        row = await ensure_daily_checklist(self.bot.db, ctx.author.id)
        view, files = await self._build_daily_view(ctx, player, checklist_row=row)
        await ctx.reply(files=files, view=view, mention_author=False)

    @commands.hybrid_group(name="quests", invoke_without_command=True)
    async def quests(self, ctx: commands.Context) -> None:
        """Show daily and weekly quest progress."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        view, files = await self._build_quests_view(ctx)
        await ctx.reply(files=files, view=view, mention_author=False)

    @commands.hybrid_command(name="quest")
    async def quest(self, ctx: commands.Context) -> None:
        """Show daily quest progress."""
        await self.quests.callback(self, ctx)

    @quests.command(name="claim")
    async def claim_quests(self, ctx: commands.Context) -> None:
        """Claim completed daily and weekly quests."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        claimed, total_gold, total_gems, total_shards = await self._claim_ready_quests(ctx.author.id)
        if claimed:
            notice = (
                f"Claimed `{len(claimed)}` quest(s): "
                f"{_currency_icon('gold')} `{total_gold:,}`  "
                f"{_currency_icon('gems')} `{total_gems:,}`  "
                f"{material_label(WEAPON_SHARD_KEY)} `{total_shards:,}`"
            )
        else:
            notice = "No completed unclaimed quests yet."
        view, files = await self._build_quests_view(ctx, notice=notice)
        await ctx.reply(files=files, view=view, mention_author=False)

    @quests.command(name="reroll")
    async def reroll_quest(self, ctx: commands.Context) -> None:
        """Reroll one active daily quest once per day."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        replaced, new_key = await self._reroll_daily_quest(ctx.author.id)
        notice = f"Rerolled **{QUESTS[replaced]['name']}** into **{QUESTS[new_key]['name']}**."
        view, files = await self._build_quests_view(ctx, notice=notice)
        await ctx.reply(files=files, view=view, mention_author=False)

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
