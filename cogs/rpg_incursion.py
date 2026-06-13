"""Abyssal Incursion server-wide boss events."""
from __future__ import annotations

import json
import logging

import discord
from discord.ext import commands, tasks

from core.incursion_renderer import render_incursion_scene
from core.incursions import (
    ACTION_COOLDOWNS,
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
from core.theme import BLOOD_COLOR, boss_label, crate_label, currency_label, dark_embed, emoji_health_bar, material_label, status_embed

log = logging.getLogger(__name__)


class IncursionActionView(discord.ui.View):
    def __init__(self, cog: "RPGIncursion") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    async def _run(self, interaction: discord.Interaction, action: str) -> None:
        await self.cog._run_tactic_interaction(interaction, action)

    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger, row=0, custom_id="abyssia:incursion:strike")
    async def strike_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "strike")

    @discord.ui.button(label="Focus", style=discord.ButtonStyle.primary, row=0, custom_id="abyssia:incursion:focus")
    async def focus_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "focus")

    @discord.ui.button(label="Guard", style=discord.ButtonStyle.primary, row=0, custom_id="abyssia:incursion:guard")
    async def guard_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "guard")

    @discord.ui.button(label="Cleanse", style=discord.ButtonStyle.success, row=0, custom_id="abyssia:incursion:cleanse")
    async def cleanse_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "cleanse")

    @discord.ui.button(label="Channel", style=discord.ButtonStyle.secondary, row=0, custom_id="abyssia:incursion:channel")
    async def channel_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._run(interaction, "channel")

    @discord.ui.button(label="Rewards", style=discord.ButtonStyle.success, row=1, custom_id="abyssia:incursion:rewards")
    async def rewards_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog._claim_rewards_interaction(interaction)


class RPGIncursion(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
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

    def _scene_file(self, payload: dict[str, object]) -> discord.File:
        return discord.File(render_incursion_scene(payload), filename="incursion_scene.png")

    def _incursion_view(self) -> IncursionActionView:
        return IncursionActionView(self)

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

    async def _status_embed_for(self, row) -> tuple[discord.Embed, discord.File | None]:
        boss = boss_config(str(row["boss_key"]))
        hp = int(row["hp"])
        max_hp = int(row["max_hp"])
        seconds_left = max(0, int(row["ends_at"]) - now_ts())
        phase = int(row["phase"])
        joined = int(row["participant_count"])
        description = (
            f"{self._boss_hp_line(hp, max_hp)}\n"
            f"Phase **{phase} - {phase_name(boss.key, phase)}** | "
            f"Time **{readable_seconds(seconds_left)}** | Hunters **{joined}**"
        )
        embed = dark_embed(
            f"Abyssal Incursion - {boss_label(boss.key, boss.name)}",
            description,
            color=boss.color,
        )
        participants = await incursion_participants(self.bot.db, int(row["id"]))
        mechanics = mechanics_from_row(row)
        embed.add_field(
            name="Raid State",
            value=(
                f"Time **{readable_seconds(seconds_left)}**\n"
                f"Hunters **{joined}**\n"
                f"Ward **{int(mechanics.get('ward', 0) or 0)}** | "
                f"Fracture **{int(mechanics.get('fracture', 0) or 0)}**"
            ),
            inline=True,
        )
        embed.add_field(name="Top Damage", value=self._top_contribution_text(participants), inline=True)
        payload = await self._scene_payload(row)
        embed.set_image(url="attachment://incursion_scene.png")
        file = self._scene_file(payload)
        return embed, file

    async def _send_spawn_announcement(self, channel: discord.TextChannel, row, *, manual: bool = False) -> None:
        boss = boss_config(str(row["boss_key"]))
        seconds_left = max(0, int(row["ends_at"]) - now_ts())
        embed = dark_embed(
            f"{boss_label(boss.key, boss.name)} Has Breached the Veil",
            (
                f"An **Abyssal Incursion** has begun.\n"
                f"{self._boss_hp_line(int(row['hp']), int(row['max_hp']))}\n"
                f"Ends in **{readable_seconds(seconds_left)}**."
            ),
            color=boss.color if not manual else BLOOD_COLOR,
        )
        embed.add_field(name="Raid Rule", value="Your bound team's HP and tactical state persist for this incursion.", inline=False)
        payload = await self._scene_payload(row, action="spawn", summary="A server-wide breach has opened.")
        embed.set_image(url="attachment://incursion_scene.png")
        file = self._scene_file(payload)
        kwargs: dict[str, object] = {"embed": embed}
        if file is not None:
            kwargs["file"] = file
        kwargs["view"] = self._incursion_view()
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

    @tasks.loop(minutes=30)
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
        if participant is not None:
            payload = await self._scene_payload(row, participant)
            boss = boss_config(str(row["boss_key"]))
            hp = int(row["hp"])
            max_hp = int(row["max_hp"])
            mechanics = mechanics_from_row(row)
            embed = dark_embed(
                f"Abyssal Incursion - {row['boss_name']}",
                (
                    f"{self._boss_hp_line(hp, max_hp)}\n"
                    f"Phase **{int(row['phase'])} - {phase_name(boss.key, int(row['phase']))}**"
                ),
                color=boss.color,
            )
            embed.set_image(url="attachment://incursion_scene.png")
            file = self._scene_file(payload)
        else:
            embed, file = await self._status_embed_for(row)
        if participant is not None:
            state = "wiped" if int(participant["wiped"]) else "bound"
            action_state = action_state_from_participant(participant)
            last_action = str(action_state.get("last_action", "") or "strike")
            cooldown_window = ACTION_COOLDOWNS.get(last_action, 30)
            cooldown = max(0, cooldown_window - (now_ts() - int(participant["last_attack_at"])))
            team_hp, team_max_hp = self._team_hp_from_participant(participant)
            embed.add_field(
                name="Your Team",
                value=(
                    f"State **{state}**\n"
                    f"Team HP **{team_hp:,}/{team_max_hp:,}**\n"
                    f"Damage **{int(participant['damage_dealt']):,}**\n"
                    f"Next attack **{'ready' if cooldown <= 0 else str(cooldown) + 's'}**"
                ),
                inline=True,
            )
            embed.add_field(
                name="Tactics",
                value=(
                    f"Focus **{int(action_state.get('focus', 0) or 0)}** | "
                    f"Guard **{int(action_state.get('guard', 0) or 0)}**\n"
                    f"Ward **{int(mechanics.get('ward', 0) or 0)}** | "
                    f"Fracture **{int(mechanics.get('fracture', 0) or 0)}**"
                ),
                inline=True,
            )
            participants = await incursion_participants(self.bot.db, int(row["id"]))
            embed.add_field(name="Top Damage", value=self._top_contribution_text(participants), inline=False)
        await self._send_embed(ctx, embed, file, view=self._incursion_view())

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
        embed = dark_embed(
            "Team Bound to the Incursion",
            (
                f"Your current team and equipped weapons have been snapshotted.\n"
                f"Team power **{outcome.team_power:,}** added **{outcome.hp_added:,}** boss HP.\n\n"
                f"{self._boss_hp_line(outcome.hp, outcome.max_hp)}"
            ),
            color=boss_config(outcome.boss_key).color,
        )
        if row is not None:
            payload = await self._scene_payload(
                row,
                participant,
                action="join",
                summary=f"{ctx.author.display_name} entered the breach.",
            )
            embed.set_image(url="attachment://incursion_scene.png")
            file = self._scene_file(payload)
        else:
            file = None
        await self._send_embed(ctx, embed, file, view=self._incursion_view())

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
    ) -> tuple[discord.Embed, discord.File | None]:
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
        boss = boss_config(outcome.boss_key)
        title = f"{outcome.boss_name} Has Fallen" if outcome.defeated else f"{outcome.boss_name} - {outcome.action_label}"
        description = (
            f"{outcome.summary}\n"
            f"{self._boss_hp_line(outcome.hp_after, outcome.max_hp)}"
        )
        embed = dark_embed(title, description, color=discord.Color.gold() if outcome.defeated else boss.color)
        embed.add_field(
            name="Battle Stats",
            value=(
                f"Damage **{outcome.damage:,}**\n"
                f"Team HP **{outcome.team_hp:,}/{outcome.team_max_hp:,}**\n"
                f"Taken **{outcome.damage_taken:,}** | Healed **{outcome.healing:,}**"
            ),
            inline=True,
        )
        embed.add_field(
            name="Tactics",
            value=(
                f"Focus **{outcome.focus}** | Guard **{outcome.guard}**\n"
                f"Ward **{outcome.ward}** | Fracture **{outcome.fracture}**"
            ),
            inline=True,
        )
        participants = await incursion_participants(self.bot.db, outcome.incursion_id)
        embed.add_field(name="Top Damage", value=self._top_contribution_text(participants), inline=False)
        if outcome.phase != outcome.previous_phase and not outcome.defeated:
            embed.add_field(
                name="Phase Shift",
                value=f"Phase **{outcome.phase} - {phase_name(outcome.boss_key, outcome.phase)}** has begun.",
                inline=False,
            )
        if outcome.mitigation:
            embed.add_field(name="Ward Absorbed", value=f"Prevented **{outcome.mitigation:,}** damage.", inline=True)
        if outcome.wiped:
            embed.add_field(name="Team Wiped", value="This bound team can no longer attack this incursion.", inline=False)
        if outcome.defeated:
            embed.add_field(name="Rewards", value="Use `bincursion rewards` to claim your split.", inline=False)
        elif outcome.log_lines:
            embed.add_field(name="Exchange", value="\n".join(outcome.log_lines[:4]), inline=False)
        if row is not None:
            payload = await self._scene_payload(row, participant, outcome=outcome)
            embed.set_image(url="attachment://incursion_scene.png")
            file = self._scene_file(payload)
        else:
            file = None
        return embed, file

    async def _run_tactic(self, ctx: commands.Context, action: str) -> None:
        assert ctx.guild is not None
        await ctx.defer()
        try:
            embed, file = await self._build_tactic_response(ctx.guild, ctx.author.id, ctx.author.display_name, action)
        except IncursionError as exc:
            await self._reply_error(ctx, str(exc))
            return
        await self._send_embed(ctx, embed, file, view=self._incursion_view())

    async def _run_tactic_interaction(self, interaction: discord.Interaction, action: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Incursion buttons only work inside a server.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        try:
            embed, file = await self._build_tactic_response(
                interaction.guild,
                interaction.user.id,
                getattr(interaction.user, "display_name", interaction.user.name),
                action,
            )
        except IncursionError as exc:
            await interaction.followup.send(embed=status_embed("Abyssal Incursion", str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=embed, file=file, view=self._incursion_view())

    async def _build_rewards_response(
        self,
        guild: discord.Guild,
        user_id: int,
        display_name: str,
    ) -> tuple[discord.Embed, discord.File | None]:
        bundle = await claim_rewards(self.bot.db, guild.id, user_id, display_name)
        status = "defeated" if bundle.status == "defeated" else "fled"
        rewards = [
            f"{currency_label('gold')} **{bundle.gold:,}**",
            f"{currency_label('gems')} **{bundle.gems:,}**",
            f"XP **{bundle.xp:,}**",
            f"{material_label('weapon_shards')} **{bundle.shards:,}**",
        ]
        if bundle.material_amount:
            rewards.append(f"{material_label(bundle.material_key)} **{bundle.material_amount:,}**")
        if bundle.crate_key:
            rewards.append(f"{crate_label(bundle.crate_key, bundle.crate_key.title())} **1**")
        if bundle.gained_levels:
            rewards.append(f"Level up **+{bundle.gained_levels}**")
        embed = dark_embed(
            f"Incursion Rewards - {bundle.boss_name}",
            (
                f"The boss **{status}**.\n"
                f"Rank **#{bundle.rank}** - contribution **{bundle.contribution_pct:.1f}%**\n\n"
                + "\n".join(rewards)
            ),
            color=boss_config(bundle.boss_key).color,
        )
        row = await self._incursion_by_id(bundle.incursion_id)
        if row is None:
            return embed, None
        payload = await self._scene_payload(
            row,
            None,
            action="rewards",
            summary=f"Rewards claimed: rank #{bundle.rank}.",
        )
        embed.set_image(url="attachment://incursion_scene.png")
        return embed, self._scene_file(payload)

    async def _claim_rewards_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Incursion buttons only work inside a server.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            embed, file = await self._build_rewards_response(
                interaction.guild,
                interaction.user.id,
                getattr(interaction.user, "display_name", interaction.user.name),
            )
        except IncursionError as exc:
            await interaction.followup.send(embed=status_embed("Abyssal Incursion", str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)

    @incursion.command(name="rewards")
    @commands.guild_only()
    async def incursion_rewards(self, ctx: commands.Context) -> None:
        """Claim rewards from your latest completed incursion."""
        assert ctx.guild is not None
        await ctx.defer()
        try:
            embed, file = await self._build_rewards_response(ctx.guild, ctx.author.id, ctx.author.display_name)
        except IncursionError as exc:
            await self._reply_error(ctx, str(exc))
            return
        await self._send_embed(ctx, embed, file, view=self._incursion_view())

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
        embed, file = await self._status_embed_for(row)
        await self._send_embed(ctx, embed, file, view=self._incursion_view())

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
