"""Global PvP battle system with matchmaking, NPC fallback, streaks, and arena rating."""
from __future__ import annotations

import asyncio
import random

import discord
from discord.ext import commands

from core.battle_card_renderer import BattleCardRenderer
from core.cards import render_arena_card, render_team_card
from core.team_display import team_slot_value
from core.battle_rewards import creature_power, daily_reset_timer, streak_milestone_reward
from core.battle_matchmaking import get_or_make_opponent
from core.battle_images import select_battle_preview_frames, simulate_battle_timeline
from core.battle_display import (
    battle_log_line,
    battle_overview_embed,
    battle_team_line,
    emoji_prefix,
    format_battle_log,
    outcome_badge,
    weapon_status,
)
from core.discord_assets import embed_asset, ensure_application_emojis
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
    get_bounty_targets,
    get_quantity,
    join_battle_queue,
    leave_battle_queue,
    load_team_snapshot,
    now_ts,
    prepare_battle,
    progress_quest,
    readable_seconds,
    record_battle_history,
    roll_checklist_battle_crates,
    save_team_snapshot,
    team_creatures,
    team_power,
    top_creatures,
    unlock_achievement,
    update_arena_after_battle,
)
from core.rpg_data import (
    BOSSES,
    BOUNTY_STREAK,
    WEAPON_SHARD_KEY,
    arena_rank,
    get_npc_pool,
    normalize_key,
    streak_multiplier,
)
from core.theme import (
    BLOOD_COLOR,
    GOLD_COLOR,
    boss_label,
    creature_label,
    currency_label,
    crate_label,
    dark_embed,
    rarity_emoji,
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

    async def _run_battle_and_reward(
        self, ctx: commands.Context, attacker: sqlite3.Row, left_team: list,
        opponent_name: str, opponent_id: int, right_team: list,
        is_npc: bool = False,
    ) -> None:
        # Check user's battle log preference
        pref = await self.bot.db.fetchone("SELECT battle_log FROM rpg_user_prefs WHERE user_id = ?", (ctx.author.id,))
        log_enabled = bool(int(pref["battle_log"])) if pref else False
        frames = simulate_battle_timeline(left_team, right_team, log_enabled=log_enabled)
        preview_frames = select_battle_preview_frames(frames, max_frames=5)
        battle_message = None
        battle_renderer = BattleCardRenderer()
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
                "won": None,
            }
            image = battle_renderer.render_battle_frame(frame_data)
            filename = f"abyssia_battle_turn_{frame_index}.png"
            file = discord.File(image, filename=filename)
            embed = battle_overview_embed(
                ctx.author,
                opponent_name,
                left_team,
                right_team,
                color=discord.Color.dark_gray(),
                image_filename=filename,
                footer=f"Battle animation {frame_index}/{len(preview_frames)}",
            )
            if battle_message is None:
                battle_message = await ctx.send(embed=embed, file=file)
            else:
                await battle_message.edit(embed=embed, attachments=[file])
            await asyncio.sleep(1)

        result = frames[-1]
        tied = result.get("tied", False)
        won = bool(result["left_won"]) if not tied else False

        arena = await ensure_arena_stats(self.bot.db, ctx.author.id, ctx.guild.id)
        previous_streak = int(arena["win_streak"])
        opp_arena = await ensure_arena_stats(self.bot.db, opponent_id, ctx.guild.id) if not is_npc else None
        opp_rating = int(opp_arena["rating"]) if opp_arena else int(arena["rating"])

        if not tied:
            winner_change, loser_change = elo_rating_change(int(arena["rating"]), opp_rating)
            rating_change = winner_change if won else loser_change
            await update_arena_after_battle(self.bot.db, ctx.author.id, ctx.guild.id, won, rating_change)
            if not is_npc and opp_arena:
                await update_arena_after_battle(self.bot.db, opponent_id, ctx.guild.id, not won, loser_change if won else winner_change)
        else:
            rating_change = 0

        streak = previous_streak + 1 if won else 0
        streak_bonus_str = ""
        if won and streak >= 3:
            mult = streak_multiplier(streak)
            streak_bonus_str = f"\n{status_effect_label('burn', f'{streak}-win streak')} | **+{mult:.0%}** rewards"

        rewards = calculate_battle_rewards(won, int(attacker["level"]), streak if won else 0, int(arena["rating"]))
        if won:
            await award_currency(self.bot.db, ctx.author.id, gold=rewards["gold"], gems=rewards["gems"])
            await award_player_xp(self.bot.db, attacker, rewards["xp"])
            await progress_quest(self.bot.db, ctx.author.id, "daily_battle")
            await unlock_achievement(self.bot.db, ctx.author.id, "arena_victor")

            # Streak milestone reward
            milestone = streak_milestone_reward(streak)
            if milestone:
                need, mname, rtype = milestone
                if rtype == "cache":
                    qty = await get_quantity(self.bot.db, ctx.author.id, "crate", rtype)
                    await add_item(self.bot.db, ctx.author.id, "crate", rtype, 1)
                    streak_bonus_str += f"\nMilestone: **{mname}** awarded!"
                elif rtype == "title":
                    streak_bonus_str += f"\nMilestone: **{mname}** - `Void Champion` title unlocked!"
        elif not tied:
            await award_currency(self.bot.db, ctx.author.id, gold=rewards["gold"])

        checklist_crates, checklist_crate_count = await roll_checklist_battle_crates(self.bot.db, ctx.author.id, 1)

        # Bounty check
        bounty_str = ""
        if won and streak >= BOUNTY_STREAK:
            bounty_str = f"\n**BOUNTY!** {ctx.author.display_name} has reached a {streak} win streak! Bonus rewards are available for defeating them."

        new_rating = int(arena["rating"]) + rating_change
        rank = arena_rank(max(0, new_rating))

        log = list(result.get("full_log") or result["log"])
        await record_battle_history(
            self.bot.db, ctx.author.id, opponent_name, opponent_id,
            won, rating_change, opp_rating, is_npc, log,
        )

        # ── Build battle result card data ──
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

        player_rank_label = arena_rank(int(attacker["arena_rating"]))
        enemy_rating = opp_rating if not is_npc else int(arena["rating"])
        enemy_rank_label = arena_rank(enemy_rating)

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
            "player_rating": int(attacker["arena_rating"]),
            "enemy_rating": enemy_rating,
            "player_rank": f"{player_rank_label} Hunter",
            "enemy_rank": f"{enemy_rank_label} Hunter",
            "rating_change": rating_change,
            "win_streak": streak if won else 0,
            "zone_key": str(attacker["current_zone"]) if "current_zone" in attacker.keys() else "bloodmoon_forest",
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

        image = battle_renderer.render_battle_result(battle_result_data)
        file = discord.File(image, filename="abyssia_battle.png")
        turns_total = int(result.get("turn", len(frames)))
        if tied:
            result_word = "tied"
        else:
            result_word = "won" if won else "lost"
        footer_bits = [
            f"You {result_word} in {turns_total} turns!",
            f"+{int(rewards.get('xp', 0))} xp",
            f"Rating {new_rating} ({rating_change:+d})",
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
        embed = battle_overview_embed(
            ctx.author,
            opponent_name,
            left_team,
            right_team,
            color=discord.Color.dark_gray() if tied else (discord.Color.green() if won else discord.Color.dark_red()),
            image_filename="abyssia_battle.png",
            footer=" | ".join(footer_bits),
        )
        compact_log = result.get("compact_log", [])
        if compact_log:
            log_text = format_battle_log(compact_log, max_lines=18)
            embed.add_field(name="⚔️ Battle Log", value=f"{log_text}", inline=False)
        message_content = None
        if checklist_crates:
            message_content = (
                f"{crate_label('cache', 'Weapon Crate')} | **{ctx.author.display_name}**, "
                f"You found a **weapon crate!** `[{checklist_crate_count}/3]` "
                f"**RESETS IN:** `{daily_reset_timer()}`"
            )
        if battle_message is not None:
            await battle_message.edit(content=message_content, embed=embed, attachments=[file])
        else:
            await ctx.reply(content=message_content, embed=embed, file=file, mention_author=False)

        # Bounty announcement
        if won and streak >= BOUNTY_STREAK:
            bounty_embed = dark_embed(
                status_effect_label("burn", "Bounty Active"),
                f"**{ctx.author.display_name}** has reached a **{streak} win streak**!\n"
                f"Defeat them in the arena for bonus rewards.\n"
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
                await ctx.reply(embed=embed, mention_author=False)
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
            await ctx.reply(embed=embed, mention_author=False)
            return

        power = team_power(creatures)
        cids = [int(c["id"]) for c in creatures]
        weapons = await creature_weapons(self.bot.db, cids)
        arena = await ensure_arena_stats(self.bot.db, target.id, ctx.guild.id)
        streak = int(arena['win_streak'])
        title = ui_label("team", f"{target.display_name}'s Team")
        description = (
            "`b team set <slot> <name>` set a team slot\n"
            "`b weaponequip <weapon id> <creature>` equip a weapon"
        )
        embed = discord.Embed(title=title, description=description, color=GOLD_COLOR)
        embed.set_author(name=str(target), icon_url=target.display_avatar.url)
        for index, creature in enumerate(creatures[:3], start=1):
            field_name, field_value = team_slot_value(index, creature, weapons.get(int(creature["id"])))
            embed.add_field(name=field_name, value=field_value, inline=True)
        streak_text = f"Current Streak: {streak}"
        if streak >= 3:
            from core.rpg_data import get_streak_tier, streak_bonus_text
            tier = get_streak_tier(streak)
            if tier.label:
                streak_text = f"{tier.emoji} Streak: {streak} ({tier.label})"
        embed.set_footer(
            text=(
                f"Team Power: {power:,} | {streak_text} | "
                f"Best: {int(arena['highest_win_streak'])}"
            )
        )
        await ctx.reply(embed=embed, mention_author=False)
        return
        image = render_team_card(target.display_name, creatures, team_power=power, weapons=weapons)
        file = discord.File(image, filename="abyssia_team.png")
        embed = discord.Embed(color=GOLD_COLOR)
        embed.set_author(name=str(target), icon_url=target.display_avatar.url)
        embed.set_image(url="attachment://abyssia_team.png")
        await ctx.reply(embed=embed, file=file, mention_author=False)

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
            defender = await ensure_player(self.bot.db, opponent.id, opponent.display_name)
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
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        last = await self.bot.db.fetchone(
            "SELECT * FROM rpg_battle_history WHERE user_id = ? ORDER BY fought_at DESC LIMIT 1",
            (ctx.author.id,),
        )
        if not last:
            raise commands.BadArgument("No previous battle found.")
        opp_id = int(last["opponent_id"])
        opp_name = str(last["opponent_name"])
        is_npc = bool(last["is_npc"])

        left_team = await prepare_battle(self.bot.db, ctx.author.id)
        if not left_team:
            raise commands.BadArgument("You need at least one creature.")

        if is_npc or opp_id == 0:
            arena = await ensure_arena_stats(self.bot.db, ctx.author.id, ctx.guild.id)
            rating = int(arena["rating"])
            pool = get_npc_pool(rating)
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
            lines.append(f"{badge} vs **{r['opponent_name']}**{npc_tag} - rating `{r['rating_change']:+d}` -> `{r['opponent_rating']}`")
        embed = dark_embed(
            ui_label("battle", "Battle History"),
            f"Record: **{wins}W** / **{losses}L**\n\n" + "\n".join(lines),
            color=GOLD_COLOR,
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ── Battle Log Toggle ──────────────────────────────────────────

    # ── Arena Stats ──────────────────────────────────────────────────

    @commands.hybrid_command(name="arena")
    async def arena(self, ctx: commands.Context) -> None:
        """Show your arena rating, rank, streak, and stats."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        arena = await ensure_arena_stats(self.bot.db, ctx.author.id, ctx.guild.id)
        rank = arena_rank(int(arena["rating"]))
        streak = int(arena["win_streak"])
        best = int(arena["highest_win_streak"])
        total = int(arena["total_battles"])
        wins = int(arena["wins"])
        losses = int(arena["losses"])
        winrate = f"{round(wins / max(1, total) * 100)}%" if total > 0 else "N/A"

        streak_line = f"{status_effect_label('burn', 'Current streak')}: **{streak}** | Best: **{best}**"
        if streak >= 3:
            from core.rpg_data import get_streak_tier, streak_bonus_text
            tier = get_streak_tier(streak)
            if tier.label:
                bonus_text = streak_bonus_text(streak)
                streak_line = f"{status_effect_label('burn', f'{tier.emoji} Streak: {streak}')}: **{tier.label}** | Best: **{best}**\n{bonus_text}"

        message = (
            f"{ui_label('leaderboard', 'Rating')}: **{arena['rating']}** | Rank: **{rank}**\n"
            f"{ui_label('battle', 'Record')}: **{wins}W** / **{losses}L** ({winrate})\n"
            f"{streak_line}\n"
            f"Total battles: **{total}**"
        )
        if streak >= BOUNTY_STREAK:
            message += f"\n\n{status_effect_label('burn', 'Bounty Active')} - You're a target. Defend your streak!"

        last_match = None
        last = await self.bot.db.fetchone(
            "SELECT * FROM rpg_battle_history WHERE user_id = ? ORDER BY fought_at DESC LIMIT 1",
            (ctx.author.id,),
        )
        if last:
            outcome = "win" if last["won"] else "loss"
            last_match = f"Last match: {outcome} vs {last['opponent_name']}, {last['rating_change']:+d} rating"

        embed = dark_embed(ui_label("leaderboard", "Arena Ledger"), message, color=GOLD_COLOR)
        image = render_arena_card(ctx.author.display_name, player, rank=rank, last_match=last_match)
        file = discord.File(image, filename="abyssia_arena.png")
        embed.set_image(url="attachment://abyssia_arena.png")
        await ctx.reply(embed=embed, file=file, mention_author=False)

    # ── Leaderboard ──────────────────────────────────────────────────

    @commands.hybrid_command(name="leaderboard", aliases=["lb", "rankings"])
    async def leaderboard(self, ctx: commands.Context, category: str = "rating") -> None:
        """Show top hunters: rating, streak, wins, level, souls."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        if category == "rating":
            rows = await self.bot.db.fetchall(
                """SELECT s.*, p.hunter_name FROM rpg_arena_stats s
                   JOIN rpg_players p ON s.user_id = p.user_id
                   ORDER BY s.rating DESC LIMIT 15""",
            )
            label = "Arena Rating"
            fmt = lambda r: f"{rarity_emoji('Legendary') or ''} **{r['hunter_name']}** - `{r['rating']}` ({arena_rank(int(r['rating']))})"
        elif category in ("streak", "win_streak"):
            rows = await self.bot.db.fetchall(
                """SELECT s.*, p.hunter_name FROM rpg_arena_stats s
                   JOIN rpg_players p ON s.user_id = p.user_id
                   ORDER BY s.win_streak DESC LIMIT 15""",
            )
            label = "Win Streak"
            fmt = lambda r: f"{status_effect_label('burn', str(r['win_streak']) + ' streak')} - **{r['hunter_name']}**"
        elif category in ("wins", "battles"):
            rows = await self.bot.db.fetchall(
                """SELECT s.*, p.hunter_name FROM rpg_arena_stats s
                   JOIN rpg_players p ON s.user_id = p.user_id
                   ORDER BY s.wins DESC LIMIT 15""",
            )
            label = "Most Wins"
            fmt = lambda r: f"{ui_label('battle', str(r['wins']) + ' wins')} - **{r['hunter_name']}**"
        elif category in ("level", "hunter"):
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
            raise commands.BadArgument("Categories: rating, streak, wins, level, souls.")

        if not rows:
            await ctx.reply(embed=status_embed(ui_label("leaderboard", f"{label} Leaderboard"), "No hunters ranked yet."), mention_author=False)
            return
        lines = [f"`#{i}` {fmt(r)}" for i, r in enumerate(rows, start=1)]
        embed = dark_embed(ui_label("leaderboard", f"{label} Leaderboard"), "\n".join(lines), color=GOLD_COLOR)
        await ctx.reply(embed=embed, mention_author=False)

    # ── Raid Commands (unchanged) ────────────────────────────────────

    @commands.hybrid_group(name="raid", invoke_without_command=True)
    async def raid(self, ctx: commands.Context) -> None:
        """Show active server raid."""
        assert ctx.guild is not None
        row = await self.bot.db.fetchone("SELECT * FROM rpg_raid_state WHERE guild_id = ?", (ctx.guild.id,))
        if row is None:
            await ctx.reply(embed=status_embed("Raid", "No raid is active. Use `b raid awaken` to call a server boss."), mention_author=False)
            return
        boss = next(boss for boss in BOSSES if boss.key == row["boss_key"])
        embed = dark_embed(boss_label(boss.key, boss.name), f"HP: **{row['hp']}/{row['max_hp']}**\nEnds in **{readable_seconds(row['ends_at'] - now_ts())}**", color=BLOOD_COLOR)
        asset_url, file = embed_asset("bosses", boss.key)
        if asset_url:
            embed.set_thumbnail(url=asset_url)
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @raid.command(name="awaken")
    async def raid_awaken(self, ctx: commands.Context) -> None:
        """Start a server-wide boss raid."""
        assert ctx.guild is not None
        current = await self.bot.db.fetchone("SELECT 1 FROM rpg_raid_state WHERE guild_id = ?", (ctx.guild.id,))
        if current is not None:
            raise commands.BadArgument("A raid is already active.")
        boss = random.choice(BOSSES)
        started = now_ts()
        await self.bot.db.execute(
            "INSERT INTO rpg_raid_state (guild_id, boss_key, hp, max_hp, started_at, ends_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ctx.guild.id, boss.key, boss.hp, boss.hp, started, started + 86400),
        )
        await self.bot.db.execute("DELETE FROM rpg_raid_damage WHERE guild_id = ?", (ctx.guild.id,))
        embed = dark_embed(f"{boss.name} Has Awakened", f"HP: **{boss.hp}**\nUse `b raid attack` before the server is swallowed.", color=BLOOD_COLOR)
        asset_url, file = embed_asset("bosses", boss.key)
        if asset_url:
            embed.set_thumbnail(url=asset_url)
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @raid.command(name="attack")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def raid_attack(self, ctx: commands.Context) -> None:
        """Attack the active raid boss."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        row = await self.bot.db.fetchone("SELECT * FROM rpg_raid_state WHERE guild_id = ?", (ctx.guild.id,))
        if row is None:
            raise commands.BadArgument("No raid is active.")
        if int(row["ends_at"]) <= now_ts():
            await self.bot.db.execute("DELETE FROM rpg_raid_state WHERE guild_id = ?", (ctx.guild.id,))
            raise commands.BadArgument("The raid expired.")
        team = await team_creatures(self.bot.db, ctx.author.id)
        if not team:
            raise commands.BadArgument("You need at least one creature to raid.")
        damage = sum(creature_power(creature) for creature in team) + random.randint(50, 180)
        new_hp = max(0, int(row["hp"]) - damage)
        await self.bot.db.execute("UPDATE rpg_raid_state SET hp = ? WHERE guild_id = ?", (new_hp, ctx.guild.id))
        await self.bot.db.execute(
            """INSERT INTO rpg_raid_damage (guild_id, user_id, damage, attacks, last_attack_at)
               VALUES (?, ?, ?, 1, ?)
               ON CONFLICT(guild_id, user_id)
               DO UPDATE SET damage = damage + excluded.damage,
                             attacks = attacks + 1,
                             last_attack_at = excluded.last_attack_at""",
            (ctx.guild.id, ctx.author.id, damage, now_ts()),
        )
        boss = next(boss for boss in BOSSES if boss.key == row["boss_key"])
        if new_hp > 0:
            embed = dark_embed(boss_label(boss.key, boss.name), f"You dealt **{damage}** damage.\nHP left: **{new_hp}**.", color=BLOOD_COLOR)
            asset_url, file = embed_asset("bosses", boss.key)
            if asset_url:
                embed.set_thumbnail(url=asset_url)
            await ctx.reply(embed=embed, file=file, mention_author=False)
            return

        rows = await self.bot.db.fetchall("SELECT user_id, damage FROM rpg_raid_damage WHERE guild_id = ? ORDER BY damage DESC", (ctx.guild.id,))
        for damage_row in rows:
            reward_gold = 750 + int(damage_row["damage"]) // 8
            reward_gems = 10 + min(30, int(damage_row["damage"]) // 3500)
            reward_shards = 25 + min(100, int(damage_row["damage"]) // 1000)
            await ensure_player(self.bot.db, damage_row["user_id"], "Raid Hunter")
            await award_currency(self.bot.db, damage_row["user_id"], gold=reward_gold, gems=reward_gems)
            await add_item(self.bot.db, damage_row["user_id"], "material", WEAPON_SHARD_KEY, reward_shards)
            await unlock_achievement(self.bot.db, damage_row["user_id"], "raid_slayer")
        await self.bot.db.execute("DELETE FROM rpg_raid_state WHERE guild_id = ?", (ctx.guild.id,))
        top = "\n".join(f"<@{row['user_id']}> - {row['damage']} damage" for row in rows[:5])
        embed = dark_embed(
            f"{boss.name} Has Fallen",
            description=f"Rewards paid to all participants.\n\n**Top Damage**\n{top}\n\nWeapon Shards awarded by damage contribution.",
            color=discord.Color.gold(),
        )
        asset_url, file = embed_asset("bosses", boss.key)
        if asset_url:
            embed.set_thumbnail(url=asset_url)
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.hybrid_group(name="boss", invoke_without_command=True)
    async def boss(self, ctx: commands.Context) -> None:
        """Show active server boss raid."""
        await self.raid.callback(self, ctx)

    @boss.command(name="awaken")
    async def boss_awaken(self, ctx: commands.Context) -> None:
        """Start a server-wide boss raid."""
        await self.raid_awaken.callback(self, ctx)

    @boss.command(name="attack")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def boss_attack(self, ctx: commands.Context) -> None:
        """Attack the active raid boss."""
        await self.raid_attack.callback(self, ctx)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RPGBattle(bot))
