"""Global PvP battle system with matchmaking, NPC fallback, and streak rewards."""
from __future__ import annotations

import asyncio
import random
import sqlite3

import discord
from discord.ext import commands

from core.battle_card_renderer import BattleCardRenderer, battle_backdrop_keys
from core.card_controls import shortcut_view
from core.card_layout import AbyssiaLayoutView
from core.card_ui import run_render
from core.cards import render_team_card
from core.team_display import team_slot_value
from core.battle_rewards import streak_milestone_reward
from core.battle_matchmaking import get_or_make_opponent
from core.battle_images import select_battle_preview_frames, simulate_battle_timeline
from core.battle_display import (
    battle_team_line,
    format_battle_log,
    outcome_badge,
)
from core.discord_assets import ensure_application_emojis
from core.rpg import (
    add_item,
    award_currency,
    award_player_xp,
    calculate_battle_rewards,
    creature_weapons,
    elo_rating_change,
    ensure_arena_stats,
    ensure_player,
    generate_npc_team,
    join_battle_queue,
    load_team_snapshot,
    prepare_battle,
    progress_quest,
    record_battle_history,
    roll_checklist_battle_crates,
    save_team_snapshot,
    team_creatures,
    team_power,
    top_creatures,
    update_arena_after_battle,
)
from core.rpg_data import (
    BOUNTY_STREAK,
    get_npc_pool,
    streak_multiplier,
)
from core.theme import (
    BLOOD_COLOR,
    GOLD_COLOR,
    asset_emoji,
    creature_label,
    currency_emoji,
    currency_label,
    dark_embed,
    rarity_label,
    status_effect_label,
    status_embed,
    ui_label,
)


REVENGE_COOLDOWN = 10


















class BattleChallengeView(discord.ui.View):
    def __init__(self, challenger_id: int, opponent_id: int) -> None:
        super().__init__(timeout=60)
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.accepted = False
        self.declined = False

    async def _check_user(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("Only the challenged hunter can answer this duel.", ephemeral=True)
            return False
        return True

    def _disable(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_user(interaction):
            return
        self.accepted = True
        self._disable()
        await interaction.response.edit_message(content="Duel accepted. Simulating the battle...", view=self)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_user(interaction):
            return
        self.declined = True
        self._disable()
        await interaction.response.edit_message(content="Duel declined.", view=self)
        self.stop()


class RevengeView(discord.ui.View):
    def __init__(self, target_id: int) -> None:
        super().__init__(timeout=30)
        self.target_id = target_id
        self.wants_revenge = False

    @discord.ui.button(label="Take Revenge!", style=discord.ButtonStyle.danger)
    async def revenge_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("Not your prompt.", ephemeral=True)
            return
        self.wants_revenge = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Hunting for a rematch...", view=self)
        self.stop()

    @discord.ui.button(label="Forget it", style=discord.ButtonStyle.secondary)
    async def forget_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("Not your prompt.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class RPGBattle(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Helpers ──────────────────────────────────────────────────────

    def _battle_layout(
        self,
        ctx: commands.Context,
        opponent_name: str,
        left_team: list,
        right_team: list,
        *,
        filename: str,
        title: str,
        subtitle: str,
        color: discord.Color,
        footer: str | None = None,
        log_lines: list[str] | None = None,
        rewards: str | None = None,
    ) -> AbyssiaLayoutView:
        team_lines = "\n".join(battle_team_line(cr) for cr in left_team) or "None"
        enemy_lines = "\n".join(battle_team_line(cr) for cr in right_team) or "None"
        sections: list[tuple[str, str]] = [
            ("Matchup", f"**{ctx.author.display_name}**\n{team_lines}\n\n**{opponent_name}**\n{enemy_lines}"),
        ]
        if rewards:
            sections.append(("Rewards", rewards))
        if log_lines:
            sections.append(("Turn Log", format_battle_log(log_lines[-12:], max_lines=12, max_chars=900)))
        return AbyssiaLayoutView(
            owner_id=ctx.author.id,
            title=title,
            subtitle=subtitle,
            image_filename=filename,
            image_description=f"{ctx.author.display_name} versus {opponent_name}",
            sections=sections,
            footer=footer,
            shortcuts=[
                ("Weapons", "b weapons"),
                ("Upgrade", "b upgrade"),
            ],
            accent=color,
        )

    async def _run_battle_and_reward(
        self, ctx: commands.Context, attacker: sqlite3.Row, left_team: list,
        opponent_name: str, opponent_id: int, right_team: list,
        is_npc: bool = False,
    ) -> None:
        # Check user's battle log preference
        pref = await self.bot.db.fetchone("SELECT battle_log FROM rpg_user_prefs WHERE user_id = ?", (ctx.author.id,))
        log_enabled = bool(int(pref["battle_log"])) if pref else False
        frames = simulate_battle_timeline(left_team, right_team, log_enabled=log_enabled)
        preview_frames = select_battle_preview_frames(frames, max_frames=1)
        battle_message = None
        battle_renderer = BattleCardRenderer()
        available_backdrops = battle_backdrop_keys()
        battle_bg_key = random.choice(available_backdrops) if available_backdrops else None
        for frame_index, frame in enumerate(preview_frames, start=1):
            frame_data = {
                "turn": int(frame["turn"]),
                "player_name": ctx.author.display_name,
                "enemy_name": opponent_name,
                "player_team": left_team,
                "enemy_team": right_team,
                "player_hp": list(frame["left_hp"]),
                "enemy_hp": list(frame["right_hp"]),
                "player_wp": list(frame.get("left_wp", [])),
                "enemy_wp": list(frame.get("right_wp", [])),
                "zone_key": str(attacker["current_zone"]) if "current_zone" in attacker.keys() else "bloodmoon_forest",
                "battle_bg_key": battle_bg_key,
                "won": None,
            }
            frame_data["preview_card"] = True
            image = await run_render(battle_renderer.render_battle_frame, frame_data)
            filename = f"abyssia_battle_turn_{frame_index}.png"
            file = discord.File(image, filename=filename)
            view = self._battle_layout(
                ctx,
                opponent_name,
                left_team,
                right_team,
                filename=filename,
                title="Battle Turn",
                subtitle=f"{ctx.author.display_name} vs {opponent_name}",
                color=discord.Color.dark_gray(),
                footer=f"Turn {int(frame['turn'])} | Battle animation {frame_index}/{len(preview_frames)}",
                log_lines=list(frame.get("compact_log", [])) if log_enabled else None,
            )
            if battle_message is None:
                battle_message = await ctx.send(file=file, view=view)
            else:
                await battle_message.edit(content=None, embed=None, attachments=[file], view=view)

        result = frames[-1]
        tied = result.get("tied", False)
        won = bool(result["left_won"]) if not tied else False

        battle_stats = await ensure_arena_stats(self.bot.db, ctx.author.id, ctx.guild.id)
        previous_streak = int(battle_stats["win_streak"])
        my_rating = int(battle_stats["rating"])
        my_change = 0
        opp_rating = 0

        if not tied:
            if not is_npc and opponent_id:
                opp_stats = await ensure_arena_stats(self.bot.db, opponent_id, ctx.guild.id)
                opp_rating = int(opp_stats["rating"])
                if won:
                    my_change, opp_change = elo_rating_change(my_rating, opp_rating)
                else:
                    opp_change, my_change = elo_rating_change(opp_rating, my_rating)
                await update_arena_after_battle(self.bot.db, ctx.author.id, ctx.guild.id, won, my_change)
                await update_arena_after_battle(self.bot.db, opponent_id, ctx.guild.id, not won, opp_change)
            else:
                await update_arena_after_battle(self.bot.db, ctx.author.id, ctx.guild.id, won, 0)
        else:
            pass

        streak = previous_streak + 1 if won else 0
        streak_bonus_str = ""
        if won and streak >= 3:
            mult = streak_multiplier(streak)
            streak_bonus_str = f"\n{status_effect_label('burn', f'{streak}-win streak')} | **+{mult:.0%}** rewards"

        rewards = calculate_battle_rewards(won, int(attacker["level"]), streak if won else 0, 0)
        if won:
            await award_currency(self.bot.db, ctx.author.id, gold=rewards["gold"], gems=rewards["gems"])
            await award_player_xp(self.bot.db, attacker, rewards["xp"])
            await progress_quest(self.bot.db, ctx.author.id, "daily_battle")

            # Streak milestone reward
            milestone = streak_milestone_reward(streak)
            if milestone:
                _, mname, rtype = milestone
                if rtype == "cache":
                    await add_item(self.bot.db, ctx.author.id, "crate", rtype, 1)
                    streak_bonus_str += f"\nMilestone: **{mname}** awarded!"
                elif rtype == "title":
                    streak_bonus_str += f"\nMilestone: **{mname}** - `Void Champion` title unlocked!"
        elif not tied:
            await award_currency(self.bot.db, ctx.author.id, gold=rewards["gold"])

        await roll_checklist_battle_crates(self.bot.db, ctx.author.id, 1)

        log = list(result.get("full_log") or result["log"])
        await record_battle_history(
            self.bot.db, ctx.author.id, opponent_name, opponent_id,
            won, my_change if not tied else 0, opp_rating if not is_npc and opponent_id else 0, is_npc, log,
        )

        # Build battle result card data.
        has_ultra = any(str(c.get("rarity", "")) in ("Eldritch", "Abyssal") for c in left_team + right_team)

        damage_dealt = 0
        damage_taken = 0
        crits = 0
        status_applied = 0
        creature_damage: dict[str, int] = {}
        creature_kills: dict[str, int] = {}
        current_actor: str | None = None
        left_names = {str(c["name"]) for c in left_team}
        for line in (log or []):
            for cr in left_team + right_team:
                cn = str(cr.get("name", ""))
                if cn and cn in line:
                    creature_damage.setdefault(cn, 0)
                    creature_kills.setdefault(cn, 0)
            # Track current actor from action lines
            if " uses " in line and ". SPD" not in line and " vs " not in line:
                current_actor = line.split(" uses ")[0].strip()
            # Clear actor when creature cannot act (skip)
            if " cannot act" in line:
                current_actor = None
            if "Critical hit" in line:
                crits += 1
            if " takes " in line and " damage" in line:
                try:
                    parts = line.split(" takes ")
                    val = int(parts[-1].split()[0].replace(",", ""))
                    target_name = parts[0].strip()
                    if target_name in left_names:
                        damage_taken += val  # player's creature was hit
                    else:
                        damage_dealt += val  # enemy was hit by player
                    # Attribute damage to the current actor if on left team
                    if current_actor and current_actor in left_names:
                        creature_damage[current_actor] = creature_damage.get(current_actor, 0) + val
                except (ValueError, IndexError):
                    pass
            if any(e in line for e in ["bleeding", "burned", "poisoned", "stunned", "shielded"]):
                status_applied += 1
            if "defeated" in line.lower():
                if current_actor and current_actor in left_names:
                    creature_kills[current_actor] = creature_kills.get(current_actor, 0) + 1

        mvp_creature = None
        if creature_damage:
            mvp_name = max(creature_damage, key=creature_damage.get)
            mvp_creature = {"name": mvp_name, "damage": creature_damage[mvp_name], "kills": creature_kills.get(mvp_name, 0)}

        player_weapons = []
        for cr in left_team:
            w = cr.get("_weapon") if isinstance(cr.get("_weapon"), dict) else None
            if w:
                player_weapons.append({"name": str(w.get("name", "")), "rarity": str(w.get("rarity", "Common"))})

        tied = result.get("tied", False)
        battle_result_data = {
            "won": won if not tied else None,
            "tied": tied,
            "winner_name": ctx.author.display_name if won else opponent_name,
            "loser_name": opponent_name if won else ctx.author.display_name,
            "player_name": ctx.author.display_name,
            "enemy_name": opponent_name,
            "player_team": left_team,
            "enemy_team": right_team,
            "player_hp": list(result["left_hp"]),
            "enemy_hp": list(result["right_hp"]),
            "player_wp": list(result["left_wp"]),
            "enemy_wp": list(result["right_wp"]),
            "player_rank": "Battle Team",
            "enemy_rank": "Opponent Team",
            "win_streak": streak if won else 0,
            "zone_key": str(attacker["current_zone"]) if "current_zone" in attacker.keys() else "bloodmoon_forest",
            "battle_bg_key": battle_bg_key,
            "has_ultra_rare": has_ultra,
            "damage_stats": {
                "player_damage_dealt": damage_dealt,
                "player_damage_taken": damage_taken,
                "player_crits": crits,
                "player_status_applied": status_applied,
            },
            "mvp": mvp_creature,
            "player_weapons": player_weapons,
            "log": log,
            "full_log": list(result.get("full_log", log)),
            "xp_reward": rewards.get("xp", 0),
            "gold_reward": rewards.get("gold", 0),
            "turns": int(result.get("turn", len(frames))),
        }

        image = await run_render(battle_renderer.render_battle_result, battle_result_data)
        file = discord.File(image, filename="abyssia_battle.png")
        turns_total = int(result.get("turn", len(frames)))
        if tied:
            result_word = "tied"
        else:
            result_word = "won" if won else "lost"
        footer_bits = [
            f"You {result_word} in {turns_total} turns",
        ]
        if won:
            streak_text = f"Streak: {streak}"
            if streak >= 3:
                from core.rpg_data import get_streak_tier
                tier = get_streak_tier(streak)
                if tier.label:
                    streak_text = f"{tier.emoji} {streak}x Streak ({tier.label})"
            footer_bits.append(streak_text)
        elif previous_streak > 0 and not tied:
            footer_bits.append(f"Streak broken: {previous_streak}")
        xp_icon = asset_emoji("passives", "xp_boost") or asset_emoji("ui", "profile") or "XP"
        souls_icon = currency_emoji("souls") or currency_emoji("gold") or "Souls"
        reward_line = f"{xp_icon} `+{int(rewards.get('xp', 0)):,}`"
        if int(rewards.get("gold", 0) or 0):
            reward_line += f"  {souls_icon} `{int(rewards.get('gold', 0)):,}`"
        result_title = "Battle Draw" if tied else ("Victory" if won else "Defeat")
        view = self._battle_layout(
            ctx,
            opponent_name,
            left_team,
            right_team,
            filename="abyssia_battle.png",
            title=result_title,
            subtitle=f"{ctx.author.display_name} vs {opponent_name}",
            color=discord.Color.dark_gray() if tied else (discord.Color.green() if won else discord.Color.dark_red()),
            footer=" | ".join(footer_bits),
            log_lines=list(result.get("compact_log", [])) if log_enabled else None,
            rewards=reward_line,
        )
        if battle_message is not None:
            await battle_message.edit(content=None, embed=None, attachments=[file], view=view)
        else:
            await ctx.reply(files=[file], view=view, mention_author=False)

        # Bounty announcement
        if won and streak >= BOUNTY_STREAK:
            bounty_embed = dark_embed(
                status_effect_label("burn", "Bounty Active"),
                f"**{ctx.author.display_name}** has reached a **{streak} win streak**!\n"
                f"Defeat them in battle for bonus rewards.\n"
                f"Use `b battle` to challenge them.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=bounty_embed)

    # ── Team Commands ────────────────────────────────────────────────

    @commands.hybrid_group(name="team", invoke_without_command=True)
    async def team(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        """Show a hunter's battle team."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        target = member or ctx.author
        await ensure_player(self.bot.db, target.id, target.display_name)
        creatures = await team_creatures(self.bot.db, target.id)
        if not creatures:
            prefix = "b"
            if ctx.guild is not None:
                prefix = await self.bot.db.get_setting(ctx.guild.id, "prefix") or prefix
            your_creatures = await top_creatures(self.bot.db, ctx.author.id, 5)
            if not your_creatures:
                embed = dark_embed(
                    "Battle Team",
                    "You have no monsters yet.\n\n"
                    f"Use `{prefix}hunt` to find monsters in the wild.",
                color=discord.Color.dark_gray(),
            )
                await ctx.reply(
                    embed=embed,
                    view=shortcut_view(ctx.author.id, [("Zoo", "b zoo")]),
                    mention_author=False,
                )
                return
            lines = []
            for c in your_creatures:
                lines.append(f"{rarity_label(str(c['rarity']))} **{creature_label(str(c['name']), str(c['rarity']))}** - Lv.`{c['level']}`")
            embed = dark_embed(
                ui_label("team", "Set Up Your Battle Team"),
                "You haven't set a team yet. Pick up to **3 monsters** to fight for you.\n\n"
                "**Your strongest monsters:**\n" + "\n".join(lines) + "\n\n"
                f"Use `{prefix}team set 1 <name>` to assign a monster to slot 1.\n"
                f"Then `{prefix}team set 2 <name>` and `{prefix}team set 2 <name>` for slots 2 and 3.\n"
                f"Example: `{prefix}team set 1 {your_creatures[0]['name']}`",
                color=GOLD_COLOR,
            )
            await ctx.reply(
                embed=embed,
                view=shortcut_view(
                    ctx.author.id,
                    [
                        ("Set Slot 1", f"b team set 1 {your_creatures[0]['name']}"),
                        ("Zoo", "b zoo"),
                        ("Weapons", "b weapons"),
                    ],
                ),
                mention_author=False,
            )
            return

        power = team_power(creatures)
        cids = [int(c["id"]) for c in creatures]
        weapons = await creature_weapons(self.bot.db, cids)
        battle_stats = await ensure_arena_stats(self.bot.db, target.id, ctx.guild.id)
        streak = int(battle_stats["win_streak"])
        streak_text = f"Current Streak: {streak}"
        if streak >= 3:
            from core.rpg_data import get_streak_tier
            tier = get_streak_tier(streak)
            if tier.label:
                streak_text = f"{tier.emoji} Streak: {streak} ({tier.label})"
        image = render_team_card(target.display_name, creatures, team_power=power, weapons=weapons)
        file = discord.File(image, filename="abyssia_team.png")
        team_sections = [
            ("Team Ledger", f"Power `{power:,}` | {streak_text} | Best `{int(battle_stats['highest_win_streak'])}`"),
        ]
        for slot, creature in enumerate(creatures, start=1):
            weapon = weapons.get(int(creature["id"]))
            team_sections.append(team_slot_value(slot, creature, weapon))
        view = AbyssiaLayoutView(
            owner_id=ctx.author.id,
            title="Battle Team",
            subtitle=f"{target.display_name} | Power `{power:,}`",
            image_filename="abyssia_team.png",
            image_description=f"{target.display_name}'s battle team",
            sections=team_sections,
            shortcuts=[
                ("Weapons", "b weapons"),
                ("Zoo", "b zoo"),
            ],
            accent=GOLD_COLOR,
        )
        await ctx.reply(
            file=file,
            view=view,
            mention_author=False,
        )

    @team.command(name="set")
    async def team_set(self, ctx: commands.Context, slot: int, *, creature_name: str) -> None:
        """Set a creature in team slot 1-3 by name."""
        assert ctx.guild is not None
        if slot not in {1, 2, 3}:
            raise commands.BadArgument("Slot must be 1, 2, or 3.")
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        
        # Normalize search: replace hyphens and underscores with spaces for better matching
        search_name = creature_name.lower().replace("-", " ").replace("_", " ")
        creatures = await self.bot.db.fetchall(
            "SELECT id, name FROM rpg_creatures WHERE user_id = ? AND LOWER(REPLACE(REPLACE(name, '-', ' '), '_', ' ')) LIKE ? ORDER BY level DESC, str_stat + pr_stat + hp + spd DESC LIMIT 1",
            (ctx.author.id, f"%{search_name}%"),
        )
        if not creatures:
            raise commands.BadArgument(f"No creature found matching `{creature_name}`.")
        creature_id = int(creatures[0]["id"])
        creature_display_name = str(creatures[0]["name"])
        duplicate = await self.bot.db.fetchone(
            """
            SELECT 1
            FROM rpg_teams t
            JOIN rpg_creatures c ON c.id = t.creature_id
            WHERE t.user_id = ? AND t.slot != ? AND LOWER(c.name) = LOWER(?)
            LIMIT 1
            """,
            (ctx.author.id, slot, creature_display_name),
        )
        if duplicate:
            raise commands.BadArgument(f"`{creature_display_name}` is already on your team. Pick a different species.")
        await self.bot.db.execute(
            "INSERT INTO rpg_teams (user_id, slot, creature_id) VALUES (?, ?, ?) ON CONFLICT(user_id, slot) DO UPDATE SET creature_id = excluded.creature_id",
            (ctx.author.id, slot, creature_id),
        )
        await save_team_snapshot(self.bot.db, ctx.author.id)
        await ctx.reply(embed=status_embed("Team Updated", f"Team slot **{slot}** set to **{creature_display_name}**."), mention_author=False)

    @team.command(name="clear")
    async def team_clear(self, ctx: commands.Context) -> None:
        """Clear your manual team selection."""
        assert ctx.guild is not None
        await self.bot.db.execute("DELETE FROM rpg_teams WHERE user_id = ?", (ctx.author.id,))
        await ctx.reply(embed=status_embed("Team Cleared", "Your team has been cleared. Use `b team` to set a new one."), mention_author=False)

    @commands.hybrid_command(name="battle", aliases=["duel", "bbattle"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def battle(self, ctx: commands.Context, opponent: discord.Member | None = None, *, level: str | None = None) -> None:
        """Battle another hunter or enter global matchmaking. Usage: bbattle @user lvl 10"""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)

        override_level = None
        if level:
            import re
            m = re.search(r'(?:lvl|level)\s*(\d+)', level.lower())
            if m:
                override_level = max(1, min(100, int(m.group(1))))

        if opponent:
            if opponent.bot:
                raise commands.BadArgument("You cannot battle bots.")
            if opponent.id == ctx.author.id:
                raise commands.BadArgument("You cannot battle yourself.")
            await ensure_player(self.bot.db, opponent.id, opponent.display_name)
            left_team = await prepare_battle(self.bot.db, ctx.author.id)
            right_team = await prepare_battle(self.bot.db, opponent.id)
            if not left_team or not right_team:
                raise commands.BadArgument("Both players need at least one creature.")
            if override_level:
                for c in left_team:
                    c["level"] = override_level
                for c in right_team:
                    c["level"] = override_level
            challenge = dark_embed(
                ui_label("battle", "Duel Challenge"),
                f"{ctx.author.mention} challenges {opponent.mention} to a duel.\n\n"
                f"Team Power: **{team_power(left_team):,}** vs **{team_power(right_team):,}**\n"
                + (f"All creatures set to **Level {override_level}**.\n" if override_level else "")
                + "Expires in **60s**.",
                color=BLOOD_COLOR,
            )
            view = BattleChallengeView(ctx.author.id, opponent.id)
            message = await ctx.reply(embed=challenge, view=view, mention_author=False)
            timed_out = await view.wait()
            if timed_out:
                view._disable()
                await message.edit(content="Duel challenge expired.", view=view)
                return
            if not view.accepted:
                return
            left_team = await prepare_battle(self.bot.db, ctx.author.id)
            right_team = await prepare_battle(self.bot.db, opponent.id)
            if override_level:
                for c in left_team:
                    c["level"] = override_level
                for c in right_team:
                    c["level"] = override_level
            opp_name = opponent.display_name
            opp_id = opponent.id
        else:
            # Auto matchmaking
            await save_team_snapshot(self.bot.db, ctx.author.id)
            left_team = await prepare_battle(self.bot.db, ctx.author.id)
            if not left_team:
                raise commands.BadArgument("You need at least one creature in your team to battle. Use `b team set`.")
            if override_level:
                for c in left_team:
                    c["level"] = override_level
            await join_battle_queue(self.bot.db, ctx.author.id, ctx.guild.id)
            status_msg = await ctx.reply(embed=dark_embed(ui_label("battle", "Matchmaking"), "Searching for an opponent...", color=discord.Color.dark_gray()), mention_author=False)
            await asyncio.sleep(1)
            opp_name, opp_id, right_team = await get_or_make_opponent(self.bot.db, ctx.author.id, ctx.guild.id, left_team)
            if override_level:
                for c in right_team:
                    c["level"] = override_level
            await status_msg.delete()
            if opp_id == ctx.author.id:
                raise commands.BadArgument("No opponents found. Try again later.")

        await self._run_battle_and_reward(ctx, player, left_team, opp_name, opp_id, right_team, is_npc=(opp_id == 0))

    @commands.hybrid_command(name="b", aliases=[])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def b_shortcut(self, ctx: commands.Context, opponent: discord.Member | None = None, *, level: str | None = None) -> None:
        """Shortcut: 'bb' = b + b -> battle. Usage: bb @user"""
        await self.battle(ctx, opponent, level=level)

    # ── Revenge ──────────────────────────────────────────────────────

    @commands.hybrid_command(name="revenge")
    @commands.cooldown(1, REVENGE_COOLDOWN, commands.BucketType.user)
    async def revenge(self, ctx: commands.Context) -> None:
        """Rematch against your last opponent."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        last = await self.bot.db.fetchone(
            "SELECT * FROM rpg_battle_history WHERE user_id = ? ORDER BY fought_at DESC LIMIT 1",
            (ctx.author.id,),
        )
        if not last:
            raise commands.BadArgument("No previous battle found.")
        opp_id = int(last["opponent_id"])
        opp_name = str(last["opponent_name"])
        is_npc = bool(last["is_npc"])

        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        left_team = await prepare_battle(self.bot.db, ctx.author.id)
        if not left_team:
            raise commands.BadArgument("You need at least one creature.")

        if is_npc or opp_id == 0:
            pool = get_npc_pool(1000 + min(1400, team_power(left_team) // 2))
            npc = random.choice(pool)
            right_team = generate_npc_team(npc)
            opp_name = f"{npc.title} {npc.name}"
        else:
            right_team = await prepare_battle(self.bot.db, opp_id)
            if not right_team:
                # Try snapshot
                snap = await load_team_snapshot(self.bot.db, opp_id)
                if not snap:
                    raise commands.BadArgument("Opponent no longer has a team available.")
                right_team = snap

        await self._run_battle_and_reward(ctx, player, left_team, opp_name, opp_id, right_team, is_npc=is_npc)

    # ── Battle Log Toggle ──────────────────────────────────────────────

    @commands.hybrid_command(name="blog")
    async def blog(self, ctx: commands.Context) -> None:
        """Toggle battle logs on/off for your battles."""
        assert ctx.guild is not None
        pref = await self.bot.db.fetchone("SELECT battle_log FROM rpg_user_prefs WHERE user_id = ?", (ctx.author.id,))
        current = bool(int(pref["battle_log"])) if pref else False
        new_val = 0 if current else 1
        await self.bot.db.execute(
            "INSERT INTO rpg_user_prefs (user_id, battle_log) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET battle_log = ?",
            (ctx.author.id, new_val, new_val),
        )
        status = "ON" if new_val else "OFF"
        await ctx.reply(f"Battle logs are now **{status}**.", mention_author=False)

    # ── History ──────────────────────────────────────────────────────

    @commands.hybrid_command(name="history", aliases=["hist"])
    async def history(self, ctx: commands.Context) -> None:
        """Show your recent battle history."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        rows = await self.bot.db.fetchall(
            "SELECT * FROM rpg_battle_history WHERE user_id = ? ORDER BY fought_at DESC LIMIT 10",
            (ctx.author.id,),
        )
        if not rows:
            await ctx.reply(embed=status_embed("Battle History", "No battles fought yet. Use `b battle`."), mention_author=False)
            return
        lines = []
        wins = 0
        losses = 0
        for r in rows:
            won = bool(r["won"])
            wins += won
            losses += not won
            badge = outcome_badge(won) or ("WIN" if won else "LOSS")
            npc_tag = " [NPC]" if r["is_npc"] else ""
            lines.append(f"{badge} vs **{r['opponent_name']}**{npc_tag}")
        embed = dark_embed(
            ui_label("battle", "Battle History"),
            f"Record: **{wins}W** / **{losses}L**\n\n" + "\n".join(lines),
            color=GOLD_COLOR,
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ── Battle Log Toggle ──────────────────────────────────────────

    # ── Leaderboard ──────────────────────────────────────────────────

    # ── Leaderboard ──────────────────────────────────────────────────

    @commands.hybrid_command(name="leaderboard", aliases=["lb", "rankings"])
    async def leaderboard(self, ctx: commands.Context, category: str = "level") -> None:
        """Show top hunters by level or souls."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        if category in ("level", "hunter"):
            rows = await self.bot.db.fetchall(
                "SELECT user_id, hunter_name, level FROM rpg_players ORDER BY level DESC LIMIT 15",
            )
            label = "Hunter Level"
            fmt = lambda r: f"{ui_label('profile', 'Lv.' + str(r['level']))} - **{r['hunter_name']}**"
        elif category in ("souls", "gold"):
            rows = await self.bot.db.fetchall(
                "SELECT user_id, hunter_name, gold FROM rpg_players ORDER BY gold DESC LIMIT 15",
            )
            label = "Souls"
            fmt = lambda r: f"{currency_label('gold')} **{r['gold']:,}** - **{r['hunter_name']}**"
        else:
            raise commands.BadArgument("Categories: level, souls.")

        if not rows:
            await ctx.reply(embed=status_embed(ui_label("leaderboard", f"{label} Leaderboard"), "No hunters ranked yet."), mention_author=False)
            return
        lines = [f"`#{i}` {fmt(r)}" for i, r in enumerate(rows, start=1)]
        embed = dark_embed(ui_label("leaderboard", f"{label} Leaderboard"), "\n".join(lines), color=GOLD_COLOR)
        await ctx.reply(embed=embed, mention_author=False)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGBattle(bot))
