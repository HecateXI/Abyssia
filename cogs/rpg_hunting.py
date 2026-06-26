from __future__ import annotations

import logging
import random
import time
from io import BytesIO
from pathlib import Path

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from core.card_controls import add_shortcuts, shortcut_view
from core.card_layout import AbyssiaLayoutView
from core.card_ui import run_render
from core.cards import render_autohunt_card
from core.content_config import ROOT_DIR, get_asset_file_path
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
    refresh_player,
    roll_checklist_hunt_lootboxes,
    roll_creature_stats,
    seconds_until_daily_reset,
    team_creatures,
    unlock_achievement,
    xp_for_level,
)
from core.rpg_data import CHARMS, CRATE_TYPES, SIGILS, ZONES, normalize_key
from core.theme import (
    GOLD_COLOR,
    asset_emoji,
    consumable_label,
    crate_label,
    currency_emoji,
    currency_label,
    creature_emoji,
    creature_line,
    dark_embed,
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
ZONE_PREVIEW_SIZE = (1200, 675)
GENERATED_ZONE_BACKDROP_DIR = ROOT_DIR / "assets" / "ui" / "generated_zone_backdrops"
LEGACY_ZONE_BACKDROP_DIR = ROOT_DIR / "assets" / "ui" / "zone_backdrops"


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
    if kind == "consumable" and key:
        return consumable_label(key, label)
    if kind and key:
        emoji = asset_emoji(kind, key)
        if emoji:
            return f"{emoji} {label}"
    return label


SWORD_BUFF_KEY = "hunt_sword"
SWORD_DURATION = HUNT_SWORD_DURATION_SECONDS
LOG = logging.getLogger("abyssia.hunt")


async def _get_sword_buff(db, user_id: int) -> tuple[bool, int]:
    """Return (is_active, activated_at) for the Hunt Sword buff in one query."""
    row = await db.fetchone(
        "SELECT activated_at FROM rpg_active_buffs WHERE user_id = ? AND buff_key = ?",
        (user_id, SWORD_BUFF_KEY),
    )
    if row is None:
        return False, 0
    activated_at = int(row["activated_at"])
    return (now_ts() - activated_at) < SWORD_DURATION, activated_at


async def _check_sword_active(db, user_id: int) -> bool:
    """Check if Hunt Sword buff is active (within 20 min window, regardless of charges)."""
    active, _ = await _get_sword_buff(db, user_id)
    return active


async def _get_sword_activated_at(db, user_id: int) -> int:
    """Get the activation timestamp of the Hunt Sword buff."""
    _, activated_at = await _get_sword_buff(db, user_id)
    return activated_at


def _zone_backdrop_path(zone_key: str) -> Path | None:
    safe = normalize_key(zone_key)
    for directory in (GENERATED_ZONE_BACKDROP_DIR, LEGACY_ZONE_BACKDROP_DIR):
        path = directory / f"{safe}.png"
        if path.exists():
            return path
    path = get_asset_file_path("zones", safe)
    return path if path and path.exists() else None


def _zone_option_emoji(zone_key: str) -> discord.PartialEmoji | str | None:
    icon = zone_emoji(zone_key)
    if not icon:
        return None
    try:
        return discord.PartialEmoji.from_str(icon)
    except (TypeError, ValueError):
        return None


def _rarity_rgb(rarity: str) -> tuple[int, int, int]:
    value = rarity_color(rarity).value
    return ((value >> 16) & 255, (value >> 8) & 255, value & 255)


def _zone_preview_file(zone) -> discord.File:
    w, h = ZONE_PREVIEW_SIZE
    path = _zone_backdrop_path(zone.key)
    if path is not None:
        try:
            with Image.open(path) as raw:
                img = raw.convert("RGB")
            img = ImageOps.fit(img, (w, h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.54)).convert("RGBA")
        except OSError:
            img = Image.new("RGBA", (w, h), (8, 7, 13, 255))
    else:
        img = Image.new("RGBA", (w, h), (8, 7, 13, 255))

    img = ImageEnhance.Contrast(img).enhance(1.08)
    accent = _rarity_rgb(zone.max_rarity)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(h):
        edge = max(0, 1.0 - min(y, h - y - 1) / 180)
        if edge > 0:
            od.line((0, y, w, y), fill=(0, 0, 0, int(135 * edge)))
    od.rectangle((7, 7, w - 8, h - 8), outline=(*accent, 180), width=4)
    od.rectangle((18, 18, w - 19, h - 19), outline=(230, 220, 190, 55), width=1)
    img.alpha_composite(overlay)

    buffer = BytesIO()
    img.save(buffer, format="PNG", compress_level=3)
    buffer.seek(0)
    return discord.File(buffer, filename=f"abyssia_zone_{zone.key}.png")


class ZonePageButton(discord.ui.Button):
    def __init__(self, direction: int, *, disabled: bool = False) -> None:
        label = "Prev" if direction < 0 else "Next"
        emoji = "\u25c0\ufe0f" if direction < 0 else "\u25b6\ufe0f"
        super().__init__(label=label, style=discord.ButtonStyle.secondary, emoji=emoji, disabled=disabled)
        self.direction = direction

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, ExploreZoneView):
            await interaction.response.send_message("This route card expired.", ephemeral=True)
            return
        view.index = max(0, min(len(view.zones) - 1, view.index + self.direction))
        view.notice = None
        await view._edit_page(interaction)


class ZoneMarkButton(discord.ui.Button):
    def __init__(self, *, locked: bool, current: bool, required_level: int) -> None:
        if locked:
            label = f"Lv {required_level}"
            style = discord.ButtonStyle.secondary
            emoji = "\U0001f512"
        elif current:
            label = "Selected"
            style = discord.ButtonStyle.success
            emoji = "\u2705"
        else:
            label = "Select"
            style = discord.ButtonStyle.success
            emoji = "\u2705"
        super().__init__(label=label, style=style, emoji=emoji, disabled=locked or current)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, ExploreZoneView):
            await interaction.response.send_message("This route card expired.", ephemeral=True)
            return
        zone = view.current_zone
        if not view.unlocked(zone):
            await interaction.response.send_message(f"{zone.name} unlocks at hunter level {zone.required_level}.", ephemeral=True)
            return
        await view.ctx.bot.db.execute(
            "UPDATE rpg_players SET current_zone = ?, updated_at = ? WHERE user_id = ?",
            (zone.key, now_ts(), interaction.user.id),
        )
        view.player = await refresh_player(view.ctx.bot.db, interaction.user.id)
        view.current_zone_key = zone.key
        view.notice = f"Route marked: {zone_label(zone.key)}"
        await view._edit_page(interaction)


class ZoneJumpSelect(discord.ui.Select):
    def __init__(self, view: "ExploreZoneView") -> None:
        options: list[discord.SelectOption] = []
        for zone in view.zones:
            unlocked = view.unlocked(zone)
            current = zone.key == view.current_zone_key
            desc = "Current route" if current else ("Unlocked" if unlocked else f"Unlocks at Lv {zone.required_level}")
            options.append(
                discord.SelectOption(
                    label=zone.name[:100],
                    value=zone.key,
                    description=desc[:100],
                    emoji=_zone_option_emoji(zone.key),
                    default=zone.key == view.current_zone.key,
                )
            )
        super().__init__(placeholder="Jump to a hunting zone...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, ExploreZoneView):
            await interaction.response.send_message("This route card expired.", ephemeral=True)
            return
        selected = self.values[0]
        for idx, zone in enumerate(view.zones):
            if zone.key == selected:
                view.index = idx
                break
        view.notice = None
        await view._edit_page(interaction)


class ExploreZoneView(discord.ui.LayoutView):
    def __init__(self, ctx: commands.Context, player, *, start_index: int | None = None, notice: str | None = None) -> None:
        super().__init__(timeout=180)
        self.ctx = ctx
        self.owner_id = ctx.author.id
        self.player = player
        self.level = int(player["level"])
        self.current_zone_key = str(player["current_zone"])
        self.zones = list(ZONES.values())
        self.index = start_index if start_index is not None else self._index_for(self.current_zone_key)
        self.index = max(0, min(len(self.zones) - 1, self.index))
        self.notice = notice
        self._last_filename = f"abyssia_zone_{self.current_zone.key}.png"

    @property
    def current_zone(self):
        return self.zones[self.index]

    def _index_for(self, zone_key: str) -> int:
        for idx, zone in enumerate(self.zones):
            if zone.key == zone_key:
                return idx
        return 0

    def unlocked(self, zone) -> bool:
        return self.level >= int(zone.required_level)

    def _refresh_layout(self) -> None:
        self.clear_items()
        zone = self.current_zone
        unlocked = self.unlocked(zone)
        current = zone.key == self.current_zone_key
        accent = rarity_color(zone.max_rarity) if unlocked else discord.Color.dark_gray()
        status = "Current route" if current else ("Unlocked" if unlocked else f"Locked until Lv {zone.required_level}")
        gem_chance = f"{float(zone.gems_chance) * 100:.0f}%"
        souls = f"{zone.gold[0]:,}-{zone.gold[1]:,}"
        progress = f"{self.index + 1}/{len(self.zones)}"

        container = discord.ui.Container(accent_colour=accent)
        container.add_item(
            discord.ui.TextDisplay(
                f"## {zone_label(zone.key)}\n"
                f"{self.ctx.author.display_name} - Zone `{progress}` - {status}"
            )
        )
        container.add_item(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    f"attachment://{self._last_filename}",
                    description=f"{zone.name} route preview",
                )
            )
        )
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(
            discord.ui.TextDisplay(
                "**Route Intel**\n"
                f"Required Lv `{zone.required_level}` - Max rarity {rarity_label(zone.max_rarity)} - "
                f"{currency_emoji('gold') or currency_label('gold')} `{souls}` - "
                f"{currency_emoji('gems') or currency_label('gems')} `{gem_chance}`\n"
                f"*{zone.flavor}*"
            )
        )
        if self.notice:
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(f"**Selection**\n{self.notice}"))

        select_row = discord.ui.ActionRow()
        select_row.add_item(ZoneJumpSelect(self))
        container.add_item(select_row)

        nav_row = discord.ui.ActionRow()
        nav_row.add_item(ZonePageButton(-1, disabled=self.index <= 0))
        nav_row.add_item(ZoneMarkButton(locked=not unlocked, current=current, required_level=zone.required_level))
        nav_row.add_item(ZonePageButton(1, disabled=self.index >= len(self.zones) - 1))
        container.add_item(nav_row)

        self.add_item(container)

    async def _build_page(self) -> list[discord.File]:
        zone = self.current_zone
        self._last_filename = f"abyssia_zone_{zone.key}.png"
        self._refresh_layout()
        return [_zone_preview_file(zone)]

    async def _edit_page(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        files = await self._build_page()
        if interaction.message is not None:
            await interaction.message.edit(content=None, embed=None, attachments=files, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("These route controls belong to another hunter.", ephemeral=True)
        return False


class HuntSwordView(discord.ui.View):
    def __init__(self, db, user_id: int) -> None:
        super().__init__(timeout=120)
        self.db = db
        self.user_id = user_id
        self._used = False

    @discord.ui.button(label="Use Hunt Sword", style=discord.ButtonStyle.green, emoji="⚔️", row=1)
    async def use_sword(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your hunt.", ephemeral=True)
            return
        if self._used:
            await interaction.response.send_message("Already used.", ephemeral=True)
            return
        await interaction.response.defer()
        sword_qty = await get_quantity(self.db, self.user_id, "consumable", HUNT_SWORD_KEY)
        if sword_qty <= 0:
            self._disable_all()
            await interaction.edit_original_response(view=self)
            await interaction.followup.send("No Hunt Swords in inventory.", ephemeral=True)
            return
        sword_active = await _check_sword_active(self.db, self.user_id)
        if sword_active:
            remaining = SWORD_DURATION - (now_ts() - await _get_sword_activated_at(self.db, self.user_id))
            mins = max(0, remaining // 60)
            self._disable_all()
            await interaction.edit_original_response(view=self)
            await interaction.followup.send(f"Hunt Sword already active! **{mins}** min remaining.", ephemeral=True)
            return
        await add_item(self.db, self.user_id, "consumable", HUNT_SWORD_KEY, -1)
        await activate_buff(self.db, self.user_id, SWORD_BUFF_KEY, "consumable", 1)
        self._used = True
        self._disable_all()
        button.label = "Hunt Sword Active (20 min)"
        button.style = discord.ButtonStyle.grey
        await interaction.edit_original_response(view=self)

    def _disable_all(self) -> None:
        for child in self.children:
            child.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id


class HuntSwordLayoutButton(discord.ui.Button):
    def __init__(self, db, user_id: int, *, active: bool = False, disabled: bool = False) -> None:
        super().__init__(
            label="Hunt Sword Active (20 min)" if active else "Use Hunt Sword",
            style=discord.ButtonStyle.secondary if active else discord.ButtonStyle.green,
            emoji="⚔️",
            disabled=disabled,
        )
        self.db = db
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your hunt.", ephemeral=True)
            return
        await interaction.response.defer()
        sword_qty = await get_quantity(self.db, self.user_id, "consumable", HUNT_SWORD_KEY)
        if sword_qty <= 0:
            self.disabled = True
            await interaction.edit_original_response(view=self.view)
            await interaction.followup.send("No Hunt Swords in inventory.", ephemeral=True)
            return
        sword_active = await _check_sword_active(self.db, self.user_id)
        if sword_active:
            remaining = SWORD_DURATION - (now_ts() - await _get_sword_activated_at(self.db, self.user_id))
            mins = max(0, remaining // 60)
            self.disabled = True
            self.label = "Hunt Sword Active (20 min)"
            self.style = discord.ButtonStyle.secondary
            await interaction.edit_original_response(view=self.view)
            await interaction.followup.send(f"Hunt Sword already active! **{mins}** min remaining.", ephemeral=True)
            return
        await add_item(self.db, self.user_id, "consumable", HUNT_SWORD_KEY, -1)
        await activate_buff(self.db, self.user_id, SWORD_BUFF_KEY, "consumable", 1)
        self.disabled = True
        self.label = "Hunt Sword Active (20 min)"
        self.style = discord.ButtonStyle.secondary
        await interaction.edit_original_response(view=self.view)


class HuntBuffsLayoutButton(discord.ui.Button):
    def __init__(self, user_id: int) -> None:
        super().__init__(
            label="Buffs",
            style=discord.ButtonStyle.secondary,
            emoji=asset_emoji("buffs", "lesser_void") or None,
        )
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your hunt.", ephemeral=True)
            return
        buffs_cog = interaction.client.get_cog("Buffs")
        if buffs_cog is None or not hasattr(buffs_cog, "build_buffs_view"):
            await interaction.response.send_message("Buffs are not available right now.", ephemeral=True)
            return
        view = await buffs_cog.build_buffs_view(interaction.user.id, interaction.user.display_name)
        await interaction.response.send_message(view=view, ephemeral=True)


class RPGHunting(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _award_hunt_team_xp(self, user_id: int, xp: int) -> tuple[list, dict[int, int], dict[int, int]]:
        team = await team_creatures(self.bot.db, user_id)
        levelups: dict[int, int] = {}
        xp_gains: dict[int, int] = {}
        if not team or xp <= 0:
            return team, levelups, xp_gains
        avg_level = sum(int(c["level"]) for c in team) / len(team) if team else 1
        for creature in team:
            level = int(creature["level"])
            creature_level = max(1, level)
            ratio = avg_level / creature_level
            xp_boost = max(1.0, ratio ** 0.28)
            boosted_xp = max(1, round(xp * xp_boost))
            xp_gains[int(creature["id"])] = boosted_xp
            stored_xp = int(creature["xp"]) + boosted_xp
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
                await self.bot.db.execute(
                    """
                    UPDATE rpg_creature_collection
                    SET max_level = MAX(max_level, ?)
                    WHERE user_id = ? AND name = ? AND rarity = ?
                    """,
                    (level, user_id, str(creature["name"]), str(creature["rarity"])),
                )
                levelups[int(creature["id"])] = gained
        return await team_creatures(self.bot.db, user_id), levelups, xp_gains

    async def _hunt_roll(self, user_id: int, player, zone, *, roll_index: int = 0, rarity_bonus: float = 0.0, allow_creature: bool = True, creature_mult: float = 1.0) -> dict[str, object]:
        luck = int(player["luck"])
        level = int(player["level"])
        gold = (random.randint(*zone.gold) + level * 5 + roll_index * 6) // 3
        gems = 0

        creature_id = None
        creature_stats = None
        if allow_creature:
            catch_rate = HUNT_BASE_CATCH_RATE + luck * HUNT_LUCK_CATCH_BONUS
            if random.random() < min(HUNT_MAX_CATCH_RATE, catch_rate * creature_mult):
                rarity = choose_rarity(zone, luck, rarity_bonus)
                template = choose_creature_template(rarity)
                creature_stats = roll_creature_stats(template, level)
                creature_id = await create_creature(self.bot.db, user_id, creature_stats)
                await progress_quest(self.bot.db, user_id, "daily_catches")
                await unlock_achievement(self.bot.db, user_id, "first_blood")
                if rarity not in ("Common", "Uncommon"):
                    await unlock_achievement(self.bot.db, user_id, "rare_keeper")

        xp = random.randint(25, 45) + zone.required_level * 4
        await award_currency(self.bot.db, user_id, gold=gold)
        return {
            "gold": gold, "gems": gems,
            "creature_id": creature_id, "creature": creature_stats, "xp": xp,
        }

    @commands.hybrid_command(name="hunt", aliases=["h"])
    async def hunt(self, ctx: commands.Context, *, zone: str | None = None) -> None:
        """Hunt for creatures. Active Hunt Sword grants 1.3x catch rate for 20 min."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=600.0)
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        target_zone = get_zone(zone, player["current_zone"])
        if int(player["level"]) < target_zone.required_level:
            raise commands.BadArgument(f"{target_zone.name} unlocks at hunter level {target_zone.required_level}.")

        level = int(player["level"])
        cooldown = max(HUNT_MIN_COOLDOWN_SECONDS, round(HUNT_BASE_COOLDOWN_SECONDS - level * HUNT_LEVEL_COOLDOWN_REDUCTION))
        elapsed = now_ts() - int(player["last_hunt_at"])
        if elapsed < cooldown:
            raise commands.BadArgument(f"You are recovering from the hunt. Try again in {readable_seconds(cooldown - elapsed)}.")

        # Check if Hunt Sword buff is active (time-based, 20 min) — gives 1.3x catch rate
        sword_active = await _check_sword_active(self.bot.db, ctx.author.id)
        sword_creature_mult = 1.3 if sword_active else 1.0
        hunts_amount = 1

        catch_boost = 1.0
        xp_boost = 1.0
        gold_boost = 1.0

        total_gold = 0
        total_xp = 0
        creatures: list[dict[str, object]] = []
        
        # Check active buffs
        active_buffs = await get_active_buffs(self.bot.db, ctx.author.id)
        sigil_extra = apply_sigil(active_buffs)
        rarity_bonus = apply_charm(active_buffs)
        
        for i in range(hunts_amount):
            # Sigil: roll extra monsters per hunt
            monster_rolls = 1 + sigil_extra
            for mi in range(monster_rolls):
                result = await self._hunt_roll(ctx.author.id, player, target_zone, roll_index=i, rarity_bonus=rarity_bonus, creature_mult=sword_creature_mult * catch_boost)
                total_gold += int(result["gold"] * gold_boost)
                total_xp += int(result["xp"] * xp_boost)
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
        xp_team, team_levelups, team_xp_gains = await self._award_hunt_team_xp(ctx.author.id, total_xp)
        await self.bot.db.execute(
            "UPDATE rpg_players SET hunts_done = hunts_done + ?, last_hunt_at = ?, updated_at = ? WHERE user_id = ?",
            (hunts_amount, now_ts(), now_ts(), ctx.author.id),
        )
        await progress_quest(self.bot.db, ctx.author.id, "daily_hunts", hunts_amount)
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
        if sword_active:
            rewards_list.append({"label": "Hunt Sword Active", "amount": 0, "icon_key": HUNT_SWORD_KEY, "kind": "consumable", "color": (90, 225, 130)})
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
        if sword_active:
            active_buff_lines.append(_hunt_sword_label())
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
                "SELECT COALESCE(SUM(total_caught), 0) as cnt FROM rpg_creature_collection WHERE user_id = ? AND name = ?",
                (ctx.author.id, str(best_creature.get("name", ""))),
            )
            if dup_check and int(dup_check["cnt"]) > 1:
                collection_status = "DUPLICATE"

        hunter_rank = "Hunter"

        renderer = HuntCardRenderer()
        is_multi = len(creatures) > 1
        render_window_start = time.perf_counter()

        loading_embed = discord.Embed(
            title=" Searching for Prey...",
            description=f"**{ctx.author.display_name}** is hunting in **{target_zone.name}**\n\nRendering hunt results...",
            color=discord.Color.green(),
        )
        loading_embed.set_footer(text="Please wait...")
        hunt_message = await ctx.send(embed=loading_embed)
        loading_sent_at = time.perf_counter()

        duplicate_counts: dict[str, int] = {}
        creature_names = sorted({str(c.get("name", "")) for c in creatures if c.get("name")})
        if creature_names:
            placeholders = ",".join("?" for _ in creature_names)
            rows = await self.bot.db.fetchall(
                f"SELECT name, SUM(total_caught) as cnt FROM rpg_creature_collection WHERE user_id = ? AND name IN ({placeholders}) GROUP BY name",
                (ctx.author.id, *creature_names),
            )
            duplicate_counts = {str(row["name"]): int(row["cnt"]) for row in rows}
        duplicate_checked_at = time.perf_counter()

        if is_multi:
            monsters_data = []
            for c in creatures:
                c_name = str(c.get("name", "Unknown"))
                mon_status = "DUPLICATE"
                if duplicate_counts.get(c_name, 0) <= 1:
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
            render_started_at = time.perf_counter()
            hunt_card_buf = await run_render(renderer.render_multi_hunt_card, hunt_card_data)
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
            render_started_at = time.perf_counter()
            hunt_card_buf = await run_render(renderer.render_hunt_card, hunt_card_data)
        rendered_at = time.perf_counter()

        card_file = discord.File(hunt_card_buf, filename="abyssia_hunt.png")

        header_icon = asset_emoji("ui", "hunt") or ""
        xp_icon = asset_emoji("passives", "xp_boost") or asset_emoji("ui", "profile") or "XP"
        souls_icon = currency_emoji("souls") or currency_emoji("gold") or "S"
        reward_parts = []
        reward_parts.append(f"{xp_icon} **{total_xp:,}**")
        reward_parts.append(f"{souls_icon} **{total_gold:,}**")
        if checklist_lootboxes:
            loot_icon = asset_emoji("crate", "cache") or crate_label("cache", "Lootbox")
            reward_parts.append(f"{loot_icon} **{checklist_lootbox_count}/3**")
        if found_crate:
            crate_name = str(CRATE_TYPES[found_crate].get("name", "Weapon Crate"))
            reward_parts.append(f"{asset_emoji('crate', found_crate) or crate_label(found_crate, crate_name)} {crate_name}")
        caught_icons: list[str] = []
        for caught in creatures[:20]:
            caught_name = str(caught.get("name", "Unknown"))
            caught_rarity = str(caught.get("rarity", "Common"))
            caught_icons.append(creature_emoji(caught_name, caught_rarity) or rarity_emoji(caught_rarity))
        result_bits = [
            f"**{target_zone.name}**",
            f"`{len(creatures)}` tracked",
            f"Streak `{int(player['hunts_done']) if 'hunts_done' in player.keys() else 0}`",
        ]
        team_xp_lines: list[str] = []
        for cr in list(xp_team or [])[:3]:
            cid = int(cr["id"])
            cname = str(cr["name"])
            crarity = str(cr["rarity"])
            cicon = creature_emoji(cname, crarity) or rarity_emoji(crarity)
            gained_xp = int(team_xp_gains.get(cid, total_xp if total_xp > 0 else 0))
            level_text = f" • Lv.`{int(cr['level'])}`"
            if team_levelups.get(cid):
                level_text += f" (`+{team_levelups[cid]}`)"
            team_xp_lines.append(f"{cicon} **{cname}** {xp_icon} `+{gained_xp:,}`{level_text}")
        embed_title = f"{header_icon} Hunt Complete".strip()
        sword_qty = await get_quantity(self.bot.db, ctx.author.id, "consumable", HUNT_SWORD_KEY)
        sword_active = await _check_sword_active(self.bot.db, ctx.author.id)
        buttons: list[discord.ui.Button] = []
        if sword_qty > 0 or sword_active:
            buttons.append(
                HuntSwordLayoutButton(
                    self.bot.db,
                    ctx.author.id,
                    active=sword_active,
                    disabled=sword_active or sword_qty <= 0,
                )
            )
        buttons.append(HuntBuffsLayoutButton(ctx.author.id))
        sections: list[tuple[str, str]] = [
            ("Rewards", "  ".join(reward_parts)),
        ]
        if caught_icons:
            more = len(creatures) - len(caught_icons)
            caught_text = " ".join(caught_icons)
            if more > 0:
                caught_text += f" `+{more}`"
            sections.append(("Caught!", caught_text))
        if team_xp_lines:
            sections.append(("Team XP", "\n".join(team_xp_lines)))
        if active_buff_lines:
            sections.append(("Boosts", " ".join(active_buff_lines[:6])))
        view = AbyssiaLayoutView(
            owner_id=ctx.author.id,
            title=embed_title or "Hunt Complete",
            subtitle=f"{target_zone.name} • {len(creatures)} tracked",
            image_filename="abyssia_hunt.png",
            image_description=f"{target_zone.name} hunt result",
            sections=sections,
            footer=f"Streak `{int(player['hunts_done']) if 'hunts_done' in player.keys() else 0}` • Daily reset `{_daily_reset_timer()}`",
            shortcuts=[
                ("Explore", "b explore"),
            ],
            buttons=buttons,
            accent=discord.Color.dark_green(),
        )
        try:
            await hunt_message.edit(content=None, embed=None, attachments=[card_file], view=view)
        except discord.NotFound:
            await ctx.send(file=card_file, view=view)
        edited_at = time.perf_counter()
        try:
            card_bytes = hunt_card_buf.getbuffer().nbytes
        except Exception:
            card_bytes = 0
        LOG.info(
            "hunt timings user=%s count=%s bytes=%s loading_send=%.3fs duplicate_check=%.3fs render=%.3fs discord_edit=%.3fs total_window=%.3fs",
            ctx.author.id,
            len(creatures),
            card_bytes,
            loading_sent_at - render_window_start,
            duplicate_checked_at - loading_sent_at,
            rendered_at - render_started_at,
            edited_at - rendered_at,
            edited_at - render_window_start,
        )

    @commands.hybrid_command(name="use", aliases=["activate"])
    async def use_item(self, ctx: commands.Context, *, item_name: str | None = None) -> None:
        """Use a consumable item. Currently: Hunt Sword (1.3x catch rate for 20 min)."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=600.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        
        if item_name is None:
            sword_qty = await get_quantity(self.bot.db, ctx.author.id, "consumable", HUNT_SWORD_KEY)
            sword_active = await _check_sword_active(self.bot.db, ctx.author.id)
            embed = dark_embed("Use Item", color=discord.Color.dark_green())
            if sword_qty > 0:
                status = "ACTIVE" if sword_active else "Ready"
                embed.add_field(name=_hunt_sword_label(), value=f"Quantity: **{sword_qty}**\nStatus: **{status}**\nEffect: 1.3x catch rate for 20 minutes\n\n`b use sword` to activate", inline=False)
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
            embed.add_field(name="Effect", value="1.3x catch rate for **20 minutes**", inline=False)
            embed.add_field(name="Remaining", value=f"{sword_qty - 1} sword(s) left in inventory", inline=False)
            embed.set_footer(text="Hunt now for bonus rolls!")
            await ctx.reply(embed=embed, mention_author=False)
        else:
            await ctx.reply(embed=dark_embed("Use", f"Unknown item: `{item_name}`. Try `b use sword`."), mention_author=False, ephemeral=True)

    @commands.hybrid_command(name="explore")
    async def explore(self, ctx: commands.Context, *, zone: str | None = None) -> None:
        """Show or change unlocked hunting zones."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=600.0)
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        if zone is None:
            view = ExploreZoneView(ctx, player)
            files = await view._build_page()
            await ctx.reply(files=files, view=view, mention_author=False)
            return
        target_zone = get_zone(zone, player["current_zone"])
        if int(player["level"]) < target_zone.required_level:
            raise commands.BadArgument(f"{target_zone.name} unlocks at hunter level {target_zone.required_level}.")
        await self.bot.db.execute(
            "UPDATE rpg_players SET current_zone = ?, updated_at = ? WHERE user_id = ?",
            (target_zone.key, now_ts(), ctx.author.id),
        )
        player = await refresh_player(self.bot.db, ctx.author.id)
        view = ExploreZoneView(
            ctx,
            player,
            start_index=list(ZONES).index(target_zone.key),
            notice=f"Route marked: {zone_label(target_zone.key)}",
        )
        files = await view._build_page()
        await ctx.reply(files=files, view=view, mention_author=False)

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
            embed.set_image(url=asset_url)
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
        creatures: list[str] = []
        card_creatures: list[str] = []
        for _ in range(rolls):
            result = await self._hunt_roll(ctx.author.id, player, zone, allow_creature=len(creatures) < 12)
            total_gold += int(result["gold"])
            total_gems += int(result["gems"])
            total_xp += int(result["xp"])
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
        await progress_quest(self.bot.db, ctx.author.id, "daily_hunts", rolls)
        embed = dark_embed(f"Expedition Complete: {zone.name}", color=discord.Color.dark_teal())
        gold_icon = currency_emoji("gold") or currency_label("gold")
        gem_icon = currency_emoji("gems") or currency_label("gems")
        embed.add_field(name="Rewards", value=f"{gold_icon} **{total_gold}**\n{gem_icon} **{total_gems}**", inline=True)
        embed.add_field(name="Progress", value=f"**+{total_xp}** XP" + (f"\nLeveled up {levels} time(s)" if levels else ""), inline=True)
        embed.add_field(name="Bound Monsters", value="\n".join(creatures[:10]) if creatures else "None caught. The dark kept its monsters.", inline=False)
        asset_url, file = embed_asset("zones", zone.key)
        if asset_url:
            embed.set_image(url=asset_url)
        image = await run_render(
            render_autohunt_card,
            zone.name,
            hours=int(row["duration_hours"]),
            souls=total_gold,
            gems=total_gems,
            xp=total_xp,
            materials={},
            creatures=card_creatures,
            levels=levels,
        )
        card_file = discord.File(image, filename="abyssia_autohunt.png")
        embed.set_image(url="attachment://abyssia_autohunt.png")
        files = [card_file]
        if file:
            files.append(file)
        await ctx.reply(
            embed=embed,
            files=files,
            view=shortcut_view(
                ctx.author.id,
                [("Explore", "b explore")],
            ),
            mention_author=False,
        )

    @commands.hybrid_command(name="zones")
    async def zones(self, ctx: commands.Context) -> None:
        """List all hunting zones."""
        lines = [f"{zone_label(zone.key)} - Lv.`{zone.required_level}`+, max {rarity_label(zone.max_rarity)}" for zone in ZONES.values()]
        embed = dark_embed("Zone Index", "\n".join(lines), color=GOLD_COLOR)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGHunting(bot))
