"""Abyssal Incursion server-wide boss events."""
from __future__ import annotations

import json
import logging
import random
import asyncio

import discord
from discord.ext import commands, tasks

from core.card_ui import run_render
from core.incursion_renderer import render_incursion_reward_strip, render_incursion_scene, render_incursion_status_strip
from core.incursions import (
    IncursionError,
    action_state_from_participant,
    active_incursion,
    boss_config,
    claim_rewards,
    create_incursion,
    guild_config,
    incursion_participants,
    join_incursion,
    latest_incursion,
    leave_incursion,
    mechanics_from_row,
    participant_for_active,
    perform_incursion_action,
    phase_name,
    random_next_spawn,
    record_spawn_schedule,
    set_guild_channel,
    set_guild_enabled,
    set_incursion_message,
    team_state_totals,
)
from core.rpg import ensure_player, now_ts, readable_seconds
from core.theme import boss_label, crate_label, currency_emoji, currency_label, dark_embed, emoji_health_bar, material_label, status_embed

log = logging.getLogger(__name__)

BOSS_ACTIVITY_THRESHOLD = 34
BOSS_ACTIVITY_HARD_TRIGGER = 82
BOSS_ACTIVITY_COOLDOWN_SECONDS = 35 * 60
BOSS_ACTIVITY_ROLL_SECONDS = 90

ACTION_BUTTON_META = {
    "join": ("Join", "\U0001f517", discord.ButtonStyle.success),
    "strike": ("Strike", "\u2694\ufe0f", discord.ButtonStyle.danger),
    "focus": ("Focus", "\U0001f3af", discord.ButtonStyle.primary),
    "guard": ("Guard", "\U0001f6e1\ufe0f", discord.ButtonStyle.primary),
    "cleanse": ("Cleanse", "\u2728", discord.ButtonStyle.success),
    "channel": ("Channel", "\U0001f300", discord.ButtonStyle.secondary),
    "rewards": ("Rewards", "\U0001f381", discord.ButtonStyle.success),
}

ACTION_HELP = (
    "\u2694\ufe0f **Strike** direct damage | "
    "\U0001f3af **Focus** buffs the next hit and adds fracture\n"
    "\U0001f6e1\ufe0f **Guard** reduces retaliation | "
    "\u2728 **Cleanse** heals your bound team | "
    "\U0001f300 **Channel** spends team HP for burst"
)


def _money_icon(key: str) -> str:
    return currency_emoji(key) or currency_label(key)


class IncursionControlButton(discord.ui.Button):
    def __init__(self, cog: "RPGIncursion", action: str, *, row: int | None = None) -> None:
        label, emoji, style = ACTION_BUTTON_META[action]
        super().__init__(
            label=label,
            emoji=emoji,
            style=style,
            custom_id=f"abyssia:incursion:{action}",
            row=row,
        )
        self.cog = cog
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.action == "join":
            await self.cog._join_interaction(interaction)
            return
        if self.action == "rewards":
            await self.cog._claim_rewards_interaction(interaction)
            return
        await self.cog._run_tactic_interaction(interaction, self.action)


class IncursionPanelView(discord.ui.LayoutView):
    def __init__(
        self,
        cog: "RPGIncursion",
        *,
        title: str,
        subtitle: str,
        sections: list[tuple[str, str]],
        accent: discord.Colour | int,
        image_filename: str | None = None,
        status_filename: str | None = None,
        rewards_filename: str | None = None,
        footer: str | None = None,
    ) -> None:
        super().__init__(timeout=300)
        self.cog = cog
        colour = accent if isinstance(accent, discord.Colour) else discord.Colour(int(accent))
        container = discord.ui.Container(accent_colour=colour)
        container.add_item(discord.ui.TextDisplay(f"## {title}\n{subtitle}"))
        if image_filename:
            container.add_item(
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(
                        f"attachment://{image_filename}",
                        description=title[:256],
                    )
                )
            )
        if status_filename:
            container.add_item(
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(
                        f"attachment://{status_filename}",
                        description="Boss and team status",
                    )
                )
            )
        for name, value in sections:
            if not value:
                continue
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(f"**{name}**\n{value}"))
        if rewards_filename:
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay("**Rewards**"))
            container.add_item(
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(
                        f"attachment://{rewards_filename}",
                        description="Bossfight rewards",
                    )
                )
            )
        if footer:
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(footer))
        first = discord.ui.ActionRow()
        for action in ("join", "strike", "focus", "guard"):
            first.add_item(IncursionControlButton(cog, action))
        second = discord.ui.ActionRow()
        for action in ("cleanse", "channel", "rewards"):
            second.add_item(IncursionControlButton(cog, action))
        container.add_item(first)
        container.add_item(second)
        self.add_item(container)


class IncursionActionView(discord.ui.View):
    def __init__(self, cog: "RPGIncursion") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    async def _run(self, interaction: discord.Interaction, action: str) -> None:
        await self.cog._run_tactic_interaction(interaction, action)

    @discord.ui.button(label="Join", emoji="\U0001f517", style=discord.ButtonStyle.success, row=0, custom_id="abyssia:incursion:join")
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog._join_interaction(interaction)

    @discord.ui.button(label="Strike", emoji="\u2694\ufe0f", style=discord.ButtonStyle.danger, row=0, custom_id="abyssia:incursion:strike")
    async def strike_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "strike")

    @discord.ui.button(label="Focus", emoji="\U0001f3af", style=discord.ButtonStyle.primary, row=0, custom_id="abyssia:incursion:focus")
    async def focus_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "focus")

    @discord.ui.button(label="Guard", emoji="\U0001f6e1\ufe0f", style=discord.ButtonStyle.primary, row=0, custom_id="abyssia:incursion:guard")
    async def guard_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "guard")

    @discord.ui.button(label="Cleanse", emoji="\u2728", style=discord.ButtonStyle.success, row=1, custom_id="abyssia:incursion:cleanse")
    async def cleanse_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "cleanse")

    @discord.ui.button(label="Channel", emoji="\U0001f300", style=discord.ButtonStyle.secondary, row=1, custom_id="abyssia:incursion:channel")
    async def channel_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "channel")

    @discord.ui.button(label="Rewards", emoji="\U0001f381", style=discord.ButtonStyle.success, row=1, custom_id="abyssia:incursion:rewards")
    async def rewards_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog._claim_rewards_interaction(interaction)


class RPGIncursion(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._activity: dict[int, dict[str, int]] = {}
        if not getattr(self.bot, "_abyssia_incursion_view_registered", False):
            self.bot.add_view(IncursionActionView(self))
            setattr(self.bot, "_abyssia_incursion_view_registered", True)
        self.spawn_loop.start()

    def cog_unload(self) -> None:
        self.spawn_loop.cancel()

    async def _send_embed(
        self,
        ctx: commands.Context,
        embed: discord.Embed,
        file: discord.File | None = None,
        view: discord.ui.View | None = None,
    ) -> None:
        kwargs: dict[str, object] = {"embed": embed, "mention_author": False}
        if file is not None:
            kwargs["file"] = file
        if view is not None:
            kwargs["view"] = view
        await ctx.reply(**kwargs)

    async def _send_panel(
        self,
        ctx: commands.Context,
        view: discord.ui.LayoutView,
        file: discord.File | list[discord.File] | None = None,
    ) -> None:
        kwargs: dict[str, object] = {"view": view, "mention_author": False}
        if isinstance(file, list):
            kwargs["files"] = file
        elif file is not None:
            kwargs["file"] = file
        await ctx.reply(**kwargs)

    async def _reply_error(self, ctx: commands.Context, message: str) -> None:
        await self._send_embed(ctx, status_embed("Abyssal Incursion", message))

    def _loads(self, raw: object, fallback: object) -> object:
        if raw in (None, ""):
            return fallback
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(str(raw))
        except (TypeError, json.JSONDecodeError):
            return fallback

    async def _incursion_by_id(self, incursion_id: int):
        return await self.bot.db.fetchone("SELECT * FROM boss_incursions WHERE id = ?", (incursion_id,))

    async def _scene_payload(
        self,
        row,
        participant=None,
        *,
        action: str = "status",
        summary: str | None = None,
        outcome=None,
    ) -> dict[str, object]:
        boss = boss_config(str(row["boss_key"]))
        participants = await incursion_participants(self.bot.db, int(row["id"]))
        top = [
            {
                "name": str(p["display_name"]),
                "score": int(p["support_score"]),
                "damage": int(p["damage_dealt"]),
            }
            for p in participants[:5]
        ]
        mechanics = mechanics_from_row(row)
        action_state = action_state_from_participant(participant) if participant is not None else {"focus": 0, "guard": 0}
        team = []
        team_state = []
        if participant is not None:
            loaded_team = self._loads(participant["team_snapshot_json"], [])
            loaded_state = self._loads(participant["team_state_json"], [])
            team = loaded_team if isinstance(loaded_team, list) else []
            team_state = loaded_state if isinstance(loaded_state, list) else []
        team_hp, team_max_hp = team_state_totals(team_state) if team_state else (0, 1)
        hp = int(row["hp"])
        phase = int(row["phase"])
        if outcome is not None:
            hp = int(outcome.hp_after)
            phase = int(outcome.phase)
            team_hp = int(outcome.team_hp)
            team_max_hp = int(outcome.team_max_hp)
            action = str(outcome.action)
            summary = str(outcome.summary)
            mechanics["ward"] = int(outcome.ward)
            mechanics["fracture"] = int(outcome.fracture)
            action_state["focus"] = int(outcome.focus)
            action_state["guard"] = int(outcome.guard)
        return {
            "incursion_id": int(row["id"]),
            "boss_key": boss.key,
            "boss_name": boss.name,
            "boss_color": boss.color,
            "material_key": boss.material_key,
            "boss_title": boss.title,
            "hp": hp,
            "max_hp": int(row["max_hp"]),
            "phase": phase,
            "phase_name": phase_name(boss.key, phase),
            "seconds_left": max(0, int(row["ends_at"]) - now_ts()),
            "participants": int(row["participant_count"]),
            "top": top,
            "team": team,
            "team_state": team_state,
            "team_hp": team_hp,
            "team_max_hp": team_max_hp,
            "action": action,
            "action_label": str(outcome.action_label if outcome is not None else action.replace("_", " ").title()),
            "summary": summary or "Coordinate tactics. Focus, guard, cleanse, channel, then strike.",
            "defeated": bool(outcome.defeated) if outcome is not None else str(row["status"]) == "defeated",
            "damage": int(outcome.damage) if outcome is not None else 0,
            "damage_taken": int(outcome.damage_taken) if outcome is not None else 0,
            "healing": int(outcome.healing) if outcome is not None else 0,
            "focus": int(action_state.get("focus", 0) or 0),
            "guard": int(action_state.get("guard", 0) or 0),
            "ward": int(mechanics.get("ward", 0) or 0),
            "fracture": int(mechanics.get("fracture", 0) or 0),
            "seed": int(row["id"]) * 1009 + hp + now_ts() % 997,
        }

    async def _scene_file(self, payload: dict[str, object]) -> discord.File:
        return discord.File(await run_render(render_incursion_scene, payload), filename="incursion_scene.png")

    async def _panel_files(self, payload: dict[str, object], reward_payload: dict[str, object] | None = None) -> list[discord.File]:
        scene, status, rewards = await asyncio.gather(
            run_render(render_incursion_scene, payload),
            run_render(render_incursion_status_strip, payload),
            run_render(render_incursion_reward_strip, reward_payload or payload),
        )
        return [
            discord.File(scene, filename="incursion_scene.png"),
            discord.File(status, filename="incursion_status.png"),
            discord.File(rewards, filename="incursion_rewards.png"),
        ]

    def _incursion_view(self) -> IncursionActionView:
        return IncursionActionView(self)

    def _boss_panel_view(
        self,
        row,
        payload: dict[str, object],
        *,
        title: str | None = None,
        notice: str | None = None,
        extra_sections: list[tuple[str, str]] | None = None,
    ) -> IncursionPanelView:
        boss = boss_config(str(row["boss_key"]))
        phase = int(payload.get("phase", row["phase"]))
        seconds_left = max(0, int(payload.get("seconds_left", int(row["ends_at"]) - now_ts())))
        damage = int(payload.get("damage", 0) or 0)
        taken = int(payload.get("damage_taken", 0) or 0)
        healing = int(payload.get("healing", 0) or 0)
        defeated = bool(payload.get("defeated"))
        accent = discord.Color.gold() if defeated else discord.Color(boss.color)
        title_text = title or ("Abyssal Boss Defeated" if defeated else f"{boss.name} Has Breached the Veil")
        subtitle = (
            f"{boss_label(boss.key, boss.name)} | Phase `{phase}` "
            f"({phase_name(boss.key, phase)}) | `{readable_seconds(seconds_left)}` left"
        )
        sections: list[tuple[str, str]] = []
        if damage or taken or healing:
            sections.append(
                (
                    "Last Action",
                    f"{str(payload.get('summary') or 'Action resolved.')}\n"
                    f"\u2694\ufe0f Damage `{damage:,}`  \U0001f6e1\ufe0f Taken `{taken:,}`  \u2728 Healed `{healing:,}`",
                )
            )
        elif notice:
            sections.append(("Breach", notice))
        else:
            sections.append(("Tactics", ACTION_HELP))
        if extra_sections:
            sections.extend((name, value) for name, value in extra_sections if value)
        top = payload.get("top") if isinstance(payload.get("top"), list) else []
        if top:
            lines = []
            for index, entry in enumerate(top[:5], start=1):
                lines.append(
                    f"`#{index}` **{entry.get('name', 'Hunter')}**  "
                    f"\u2694\ufe0f `{int(entry.get('damage', 0)):,}`  \u2b50 `{int(entry.get('score', 0)):,}`"
                )
            sections.append(("Top Damage Dealt", "\n".join(lines)))
        else:
            sections.append(("Top Damage Dealt", "No damage dealt yet."))
        state = "defeated" if defeated else "active"
        footer = f"\u23f3 runs away in `{readable_seconds(seconds_left)}` | \u2694\ufe0f `{int(row['participant_count'])}` fighters | \U0001f480 `{state}`"
        return IncursionPanelView(
            self,
            title=title_text,
            subtitle=subtitle,
            sections=sections,
            accent=accent,
            image_filename="incursion_scene.png",
            status_filename="incursion_status.png",
            rewards_filename="incursion_rewards.png",
            footer=footer,
        )

    def _boss_hp_line(self, hp: int, max_hp: int, *, label: str = "Boss HP") -> str:
        return f"**{label}** {hp:,}/{max_hp:,}\n{emoji_health_bar(hp, max_hp, width=14)}"

    def _top_contribution_text(self, participants: list, *, limit: int = 3) -> str:
        if not participants:
            return "No damage logged yet."
        lines = []
        for index, participant in enumerate(participants[:limit], start=1):
            lines.append(
                f"`#{index}` **{participant['display_name']}** - "
                f"{int(participant['damage_dealt']):,} dmg / {int(participant['support_score']):,} score"
            )
        return "\n".join(lines)

    def _team_hp_from_participant(self, participant) -> tuple[int, int]:
        if participant is None:
            return 0, 1
        loaded_state = self._loads(participant["team_state_json"], [])
        team_state = loaded_state if isinstance(loaded_state, list) else []
        return team_state_totals(team_state) if team_state else (0, 1)

    async def _status_panel_for(self, row, participant=None) -> tuple[IncursionPanelView, list[discord.File]]:
        payload = await self._scene_payload(row, participant)
        file = await self._panel_files(payload)
        view = self._boss_panel_view(row, payload, title=f"Abyssal Bossfight - {row['boss_name']}")
        return view, file

    async def _send_spawn_announcement(self, channel: discord.TextChannel, row, *, manual: bool = False) -> None:
        boss = boss_config(str(row["boss_key"]))
        payload = await self._scene_payload(row, action="spawn", summary="A server-wide breach has opened.")
        file = await self._panel_files(payload)
        view = self._boss_panel_view(
            row,
            payload,
            title=f"{boss_label(boss.key, boss.name)} Has Breached the Veil",
            notice="A server-wide bossfight has begun. Join with your current team, then coordinate tactics.",
        )
        kwargs: dict[str, object] = {"view": view}
        if file:
            kwargs["files"] = file
        message = await channel.send(**kwargs)
        await set_incursion_message(self.bot.db, int(row["id"]), message.id)

    def _can_use_channel(self, guild: discord.Guild, channel: discord.abc.GuildChannel | None) -> bool:
        if not isinstance(channel, discord.TextChannel):
            return False
        me = guild.me
        if me is None and self.bot.user is not None:
            me = guild.get_member(self.bot.user.id)
        if me is None:
            return False
        perms = channel.permissions_for(me)
        return bool(perms.view_channel and perms.send_messages and perms.embed_links)

    async def _spawn_channel(self, guild: discord.Guild, channel_id: int | None) -> discord.TextChannel | None:
        configured = guild.get_channel(channel_id) if channel_id else None
        if self._can_use_channel(guild, configured):
            return configured  # type: ignore[return-value]
        if self._can_use_channel(guild, guild.system_channel):
            return guild.system_channel
        for channel in guild.text_channels:
            if self._can_use_channel(guild, channel):
                return channel
        return None

    async def _record_chat_activity(self, message: discord.Message) -> None:
        if message.guild is None or not isinstance(message.channel, discord.TextChannel):
            return
        current = now_ts()
        bucket = self._activity.setdefault(
            message.guild.id,
            {"window_start": current, "count": 0, "last_roll": 0, "last_spawn": 0},
        )
        if current - int(bucket["window_start"]) > 600:
            bucket["window_start"] = current
            bucket["count"] = max(0, int(bucket["count"]) // 3)
        bucket["count"] = int(bucket["count"]) + 1

        if current - int(bucket["last_roll"]) < BOSS_ACTIVITY_ROLL_SECONDS:
            return
        bucket["last_roll"] = current
        count = int(bucket["count"])
        if count < BOSS_ACTIVITY_THRESHOLD:
            return
        if current - int(bucket["last_spawn"]) < BOSS_ACTIVITY_COOLDOWN_SECONDS:
            return

        try:
            config = await guild_config(self.bot.db, message.guild.id)
            if config is None or not int(config["enabled"]):
                return
            if await active_incursion(self.bot.db, message.guild.id) is not None:
                return
            last_spawn_at = int(config["last_spawn_at"] or 0)
            if current - last_spawn_at < BOSS_ACTIVITY_COOLDOWN_SECONDS:
                return
            chance = min(0.78, 0.12 + max(0, count - BOSS_ACTIVITY_THRESHOLD) * 0.018)
            if count < BOSS_ACTIVITY_HARD_TRIGGER and random.random() > chance:
                return
            channel = await self._spawn_channel(
                message.guild,
                int(config["channel_id"]) if config["channel_id"] is not None else message.channel.id,
            )
            if channel is None:
                return
            row = await create_incursion(self.bot.db, message.guild.id, channel.id)
            await record_spawn_schedule(self.bot.db, message.guild.id, current)
            await self._send_spawn_announcement(channel, row)
            bucket["count"] = 0
            bucket["last_spawn"] = current
        except IncursionError:
            return
        except discord.HTTPException:
            log.exception("Could not announce activity bossfight in guild %s", message.guild.id)
        except Exception:
            log.exception("Activity bossfight spawn failed in guild %s", message.guild.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        await self._record_chat_activity(message)

    @tasks.loop(minutes=5)
    async def spawn_loop(self) -> None:
        current = now_ts()
        for guild in list(self.bot.guilds):
            try:
                config = await guild_config(self.bot.db, guild.id)
                if config is None or not int(config["enabled"]):
                    continue
                if await active_incursion(self.bot.db, guild.id) is not None:
                    continue
                next_spawn_at = int(config["next_spawn_at"])
                if next_spawn_at <= 0 or current < next_spawn_at:
                    continue
                channel = await self._spawn_channel(
                    guild,
                    int(config["channel_id"]) if config["channel_id"] is not None else None,
                )
                if channel is None:
                    await self.bot.db.execute(
                        "UPDATE boss_guild_config SET next_spawn_at = ? WHERE guild_id = ?",
                        (current + 3600, guild.id),
                    )
                    continue
                row = await create_incursion(self.bot.db, guild.id, channel.id)
                await record_spawn_schedule(self.bot.db, guild.id, current)
                await self._send_spawn_announcement(channel, row)
            except IncursionError:
                continue
            except discord.HTTPException:
                log.exception("Could not announce Abyssal Incursion in guild %s", guild.id)
            except Exception:
                log.exception("Abyssal Incursion spawn loop failed for guild %s", guild.id)

    @spawn_loop.before_loop
    async def before_spawn_loop(self) -> None:
        await self.bot.wait_until_ready()

    @commands.hybrid_group(name="incursion", aliases=("inc", "raid", "boss"), invoke_without_command=True)
    @commands.guild_only()
    async def incursion(self, ctx: commands.Context) -> None:
        """Show the active Abyssal Incursion."""
        await self.incursion_status.callback(self, ctx)

    @incursion.command(name="status")
    @commands.guild_only()
    async def incursion_status(self, ctx: commands.Context) -> None:
        """Show the active incursion status."""
        assert ctx.guild is not None
        row = await active_incursion(self.bot.db, ctx.guild.id)
        if row is None:
            config = await guild_config(self.bot.db, ctx.guild.id)
            latest = await latest_incursion(self.bot.db, ctx.guild.id)
            enabled = bool(config and int(config["enabled"]))
            next_spawn = int(config["next_spawn_at"]) if config and config["next_spawn_at"] is not None else 0
            parts = ["No Abyssal Incursion is active right now."]
            if latest is not None:
                parts.append(f"Last incursion: **{latest['boss_name']}** - `{latest['status']}`.")
            if enabled and next_spawn > now_ts():
                parts.append(f"Next breach can occur in **{readable_seconds(next_spawn - now_ts())}**.")
            elif not enabled:
                parts.append("Incursions are disabled for this server.")
            await self._send_embed(ctx, status_embed("Abyssal Incursion", "\n".join(parts)))
            return
        participant = await participant_for_active(self.bot.db, ctx.guild.id, ctx.author.id)
        view, file = await self._status_panel_for(row, participant)
        await self._send_panel(ctx, view, file)

    @incursion.command(name="join")
    @commands.guild_only()
    async def incursion_join(self, ctx: commands.Context) -> None:
        """Join the active incursion with your current team."""
        assert ctx.guild is not None
        await ctx.defer()
        try:
            await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
            outcome = await join_incursion(self.bot.db, ctx.guild.id, ctx.author.id, ctx.author.display_name)
        except IncursionError as exc:
            await self._reply_error(ctx, str(exc))
            return
        row = await self._incursion_by_id(outcome.incursion_id)
        participant = await participant_for_active(self.bot.db, ctx.guild.id, ctx.author.id)
        if row is not None:
            payload = await self._scene_payload(
                row,
                participant,
                action="join",
                summary=f"{ctx.author.display_name} entered the breach.",
            )
            file = await self._panel_files(payload)
            view = self._boss_panel_view(
                row,
                payload,
                title="Team Bound to the Bossfight",
                notice=(
                    f"Your current team and equipped weapons were snapshotted.\n"
                    f"Team power `{outcome.team_power:,}` added `{outcome.hp_added:,}` boss HP."
                ),
            )
        else:
            file = None
            view = IncursionPanelView(
                self,
                title="Team Bound",
                subtitle="Bossfight state is being refreshed.",
                sections=[("Team", f"Power `{outcome.team_power:,}`")],
                accent=discord.Color(boss_config(outcome.boss_key).color),
            )
        await self._send_panel(ctx, view, file)

    @incursion.command(name="attack")
    @commands.guild_only()
    async def incursion_attack(self, ctx: commands.Context) -> None:
        """Attack the active incursion boss."""
        await self._run_tactic(ctx, "strike")

    @incursion.command(name="strike")
    @commands.guild_only()
    async def incursion_strike(self, ctx: commands.Context) -> None:
        """Spend your action on direct boss damage."""
        await self._run_tactic(ctx, "strike")

    @incursion.command(name="focus")
    @commands.guild_only()
    async def incursion_focus(self, ctx: commands.Context) -> None:
        """Build focus and fracture the boss for stronger future hits."""
        await self._run_tactic(ctx, "focus")

    @incursion.command(name="guard")
    @commands.guild_only()
    async def incursion_guard(self, ctx: commands.Context) -> None:
        """Raise wards that reduce boss retaliation."""
        await self._run_tactic(ctx, "guard")

    @incursion.command(name="cleanse")
    @commands.guild_only()
    async def incursion_cleanse(self, ctx: commands.Context) -> None:
        """Heal and cleanse your bound incursion team."""
        await self._run_tactic(ctx, "cleanse")

    @incursion.command(name="channel")
    @commands.guild_only()
    async def incursion_channel(self, ctx: commands.Context) -> None:
        """Risk team HP for a heavy ritual hit."""
        await self._run_tactic(ctx, "channel")

    async def _build_tactic_response(
        self,
        guild: discord.Guild,
        user_id: int,
        display_name: str,
        action: str,
    ) -> tuple[IncursionPanelView, list[discord.File] | None]:
        await ensure_player(self.bot.db, user_id, display_name)
        outcome = await perform_incursion_action(
            self.bot.db,
            guild.id,
            user_id,
            display_name,
            action,
        )
        row = await self._incursion_by_id(outcome.incursion_id)
        participant = await self.bot.db.fetchone(
            "SELECT * FROM boss_participants WHERE incursion_id = ? AND user_id = ?",
            (outcome.incursion_id, user_id),
        )
        title = f"{outcome.boss_name} Has Fallen" if outcome.defeated else f"{outcome.boss_name} - {outcome.action_label}"
        if row is not None:
            payload = await self._scene_payload(row, participant, outcome=outcome)
            file = await self._panel_files(payload)
            extra: list[str] = []
            if outcome.phase != outcome.previous_phase and not outcome.defeated:
                extra.append(f"Phase `{outcome.phase}` began: **{phase_name(outcome.boss_key, outcome.phase)}**.")
            if outcome.mitigation:
                extra.append(f"Ward absorbed `{outcome.mitigation:,}` damage.")
            if outcome.wiped:
                extra.append("Your bound team was wiped and can no longer attack this boss.")
            if outcome.defeated:
                extra.append("Boss defeated. Claim your reward split with the Rewards button.")
            elif outcome.log_lines:
                extra.extend(str(line) for line in outcome.log_lines[:3])
            extra_sections = [("Exchange", "\n".join(extra))] if extra else None
            view = self._boss_panel_view(row, payload, title=title, extra_sections=extra_sections)
        else:
            file = None
            view = IncursionPanelView(
                self,
                title=title,
                subtitle="Bossfight state is being refreshed.",
                sections=[("Action", outcome.summary)],
                accent=discord.Color.gold() if outcome.defeated else discord.Color(boss_config(outcome.boss_key).color),
            )
        return view, file

    async def _run_tactic(self, ctx: commands.Context, action: str) -> None:
        assert ctx.guild is not None
        await ctx.defer()
        try:
            view, file = await self._build_tactic_response(ctx.guild, ctx.author.id, ctx.author.display_name, action)
        except IncursionError as exc:
            await self._reply_error(ctx, str(exc))
            return
        await self._send_panel(ctx, view, file)

    async def _run_tactic_interaction(self, interaction: discord.Interaction, action: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Incursion buttons only work inside a server.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        try:
            view, file = await self._build_tactic_response(
                interaction.guild,
                interaction.user.id,
                getattr(interaction.user, "display_name", interaction.user.name),
                action,
            )
        except IncursionError as exc:
            await interaction.followup.send(embed=status_embed("Abyssal Incursion", str(exc)), ephemeral=True)
            return
        if isinstance(file, list):
            await interaction.followup.send(files=file, view=view)
        elif file is not None:
            await interaction.followup.send(file=file, view=view)
        else:
            await interaction.followup.send(view=view)

    async def _join_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Incursion buttons only work inside a server.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        try:
            await ensure_player(self.bot.db, interaction.user.id, display_name)
            outcome = await join_incursion(self.bot.db, interaction.guild.id, interaction.user.id, display_name)
            row = await self._incursion_by_id(outcome.incursion_id)
            participant = await participant_for_active(self.bot.db, interaction.guild.id, interaction.user.id)
            if row is None:
                raise IncursionError("The bossfight state could not be refreshed.")
            payload = await self._scene_payload(
                row,
                participant,
                action="join",
                summary=f"{display_name} entered the breach.",
            )
            file = await self._panel_files(payload)
            view = self._boss_panel_view(
                row,
                payload,
                title="Team Bound to the Bossfight",
                notice=(
                    f"Your current team and equipped weapons were snapshotted.\n"
                    f"Team power `{outcome.team_power:,}` added `{outcome.hp_added:,}` boss HP."
                ),
            )
        except IncursionError as exc:
            await interaction.followup.send(embed=status_embed("Abyssal Incursion", str(exc)), ephemeral=True)
            return
        if isinstance(file, list):
            await interaction.followup.send(files=file, view=view, ephemeral=True)
        elif file is not None:
            await interaction.followup.send(file=file, view=view, ephemeral=True)
        else:
            await interaction.followup.send(view=view, ephemeral=True)

    async def _build_rewards_response(
        self,
        guild: discord.Guild,
        user_id: int,
        display_name: str,
    ) -> tuple[IncursionPanelView, list[discord.File] | None]:
        bundle = await claim_rewards(self.bot.db, guild.id, user_id, display_name)
        status = "defeated" if bundle.status == "defeated" else "fled"
        rewards = [
            f"{_money_icon('gold')} `{bundle.gold:,}`",
            f"{_money_icon('gems')} `{bundle.gems:,}`",
            f"\u2b50 XP `{bundle.xp:,}`",
            f"{material_label('weapon_shards')} **{bundle.shards:,}**",
        ]
        if bundle.crate_key:
            rewards.append(f"{crate_label(bundle.crate_key, bundle.crate_key.title())} **1**")
        if bundle.gained_levels:
            rewards.append(f"Level up **+{bundle.gained_levels}**")
        boss = boss_config(bundle.boss_key)
        reward_items: list[dict[str, object]] = [
            {"kind": "currency", "key": "gold", "label": "Gold", "value": f"{bundle.gold:,}", "color": 0xD7A84B},
            {"kind": "currency", "key": "gems", "label": "Gems", "value": f"{bundle.gems:,}", "color": 0x54D5E8},
            {"kind": "passives", "key": "xp_boost", "label": "XP", "value": f"{bundle.xp:,}", "color": 0x7DDC72},
            {"kind": "materials", "key": "weapon_shards", "label": "Shards", "value": f"{bundle.shards:,}", "color": 0xB47AF2},
        ]
        if bundle.crate_key:
            reward_items.append(
                {
                    "kind": "crate",
                    "key": bundle.crate_key,
                    "label": "Crate",
                    "value": "1",
                    "color": 0xD7A84B,
                }
            )
        reward_payload: dict[str, object] = {
            "boss_key": boss.key,
            "boss_color": boss.color,
            "reward_items": reward_items,
        }
        row = await self._incursion_by_id(bundle.incursion_id)
        if row is None:
            reward_file = discord.File(
                await run_render(render_incursion_reward_strip, reward_payload),
                filename="incursion_rewards.png",
            )
            view = IncursionPanelView(
                self,
                title=f"Boss Rewards - {bundle.boss_name}",
                subtitle=f"Boss `{status}` | Rank `#{bundle.rank}` | Contribution `{bundle.contribution_pct:.1f}%`",
                sections=[("Payout", "\n".join(rewards))],
                accent=discord.Color(boss.color),
                rewards_filename="incursion_rewards.png",
            )
            return view, [reward_file]
        payload = await self._scene_payload(
            row,
            None,
            action="rewards",
            summary=f"Rewards claimed: rank #{bundle.rank}.",
        )
        file = await self._panel_files(payload, reward_payload=reward_payload)
        view = IncursionPanelView(
            self,
            title=f"Boss Rewards - {bundle.boss_name}",
            subtitle=f"Boss `{status}` | Rank `#{bundle.rank}` | Contribution `{bundle.contribution_pct:.1f}%`",
            sections=[
                ("Payout", "\n".join(rewards)),
                ("Result", "Victory payouts are score based. Higher damage and support improve your split."),
            ],
            accent=discord.Color(boss.color),
            image_filename="incursion_scene.png",
            status_filename="incursion_status.png",
            rewards_filename="incursion_rewards.png",
        )
        return view, file

    async def _claim_rewards_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Incursion buttons only work inside a server.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            view, file = await self._build_rewards_response(
                interaction.guild,
                interaction.user.id,
                getattr(interaction.user, "display_name", interaction.user.name),
            )
        except IncursionError as exc:
            await interaction.followup.send(embed=status_embed("Abyssal Incursion", str(exc)), ephemeral=True)
            return
        if isinstance(file, list):
            await interaction.followup.send(files=file, view=view, ephemeral=True)
        elif file is not None:
            await interaction.followup.send(file=file, view=view, ephemeral=True)
        else:
            await interaction.followup.send(view=view, ephemeral=True)

    @incursion.command(name="rewards")
    @commands.guild_only()
    async def incursion_rewards(self, ctx: commands.Context) -> None:
        """Claim rewards from your latest completed incursion."""
        assert ctx.guild is not None
        await ctx.defer()
        try:
            view, file = await self._build_rewards_response(ctx.guild, ctx.author.id, ctx.author.display_name)
        except IncursionError as exc:
            await self._reply_error(ctx, str(exc))
            return
        await self._send_panel(ctx, view, file)

    @incursion.command(name="leave")
    @commands.guild_only()
    async def incursion_leave(self, ctx: commands.Context) -> None:
        """Leave the active incursion."""
        assert ctx.guild is not None
        try:
            await leave_incursion(self.bot.db, ctx.guild.id, ctx.author.id)
        except IncursionError as exc:
            await self._reply_error(ctx, str(exc))
            return
        await self._send_embed(ctx, status_embed("Incursion Left", "Your bound team stepped out of the breach."))

    @incursion.command(name="spawn")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def incursion_spawn(self, ctx: commands.Context, boss: str | None = None) -> None:
        """Admin: manually spawn an incursion boss."""
        assert ctx.guild is not None
        await ctx.defer()
        try:
            row = await create_incursion(
                self.bot.db,
                ctx.guild.id,
                ctx.channel.id if isinstance(ctx.channel, discord.TextChannel) else None,
                boss_key=boss,
                created_by=ctx.author.id,
            )
        except IncursionError as exc:
            await self._reply_error(ctx, str(exc))
            return
        await record_spawn_schedule(self.bot.db, ctx.guild.id, now_ts())
        if isinstance(ctx.channel, discord.TextChannel):
            await self._send_spawn_announcement(ctx.channel, row, manual=True)
        view, file = await self._status_panel_for(row)
        await self._send_panel(ctx, view, file)

    @incursion.group(name="config", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def incursion_config(self, ctx: commands.Context) -> None:
        """Show incursion server config."""
        assert ctx.guild is not None
        config = await guild_config(self.bot.db, ctx.guild.id)
        enabled = bool(config and int(config["enabled"]))
        channel_id = int(config["channel_id"]) if config and config["channel_id"] is not None else None
        next_spawn = int(config["next_spawn_at"]) if config and config["next_spawn_at"] is not None else 0
        channel_text = f"<#{channel_id}>" if channel_id else "auto"
        next_text = readable_seconds(max(0, next_spawn - now_ts())) if enabled and next_spawn else "unscheduled"
        embed = dark_embed(
            "Abyssal Incursion Config",
            f"Enabled **{enabled}**\nChannel **{channel_text}**\nNext window **{next_text}**",
        )
        await self._send_embed(ctx, embed)

    @incursion_config.command(name="channel")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def incursion_config_channel(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel | None = None,
    ) -> None:
        """Set the incursion announcement channel."""
        assert ctx.guild is not None
        await set_guild_channel(self.bot.db, ctx.guild.id, channel.id if channel else None)
        text = "Incursion channel set to auto." if channel is None else f"Incursion channel set to {channel.mention}."
        await self._send_embed(ctx, status_embed("Incursion Config", text))

    @incursion_config.command(name="enable")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def incursion_config_enable(self, ctx: commands.Context) -> None:
        """Enable random incursion spawns."""
        assert ctx.guild is not None
        await set_guild_enabled(self.bot.db, ctx.guild.id, True)
        config = await guild_config(self.bot.db, ctx.guild.id)
        if config and int(config["next_spawn_at"]) <= now_ts():
            await self.bot.db.execute(
                "UPDATE boss_guild_config SET next_spawn_at = ? WHERE guild_id = ?",
                (random_next_spawn(), ctx.guild.id),
            )
        await self._send_embed(ctx, status_embed("Incursions Enabled", "Random Abyssal Incursions can now spawn."))

    @incursion_config.command(name="disable")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def incursion_config_disable(self, ctx: commands.Context) -> None:
        """Disable random incursion spawns."""
        assert ctx.guild is not None
        await set_guild_enabled(self.bot.db, ctx.guild.id, False)
        await self._send_embed(ctx, status_embed("Incursions Disabled", "Random Abyssal Incursions are disabled."))

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        original = getattr(error, "original", error)
        if isinstance(original, IncursionError):
            await self._send_embed(ctx, status_embed("Abyssal Incursion", str(original)))
            return
        if isinstance(original, commands.MissingPermissions):
            await self._send_embed(ctx, status_embed("Abyssal Incursion", "You need Manage Server for that incursion command."))
            return
        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGIncursion(bot))
