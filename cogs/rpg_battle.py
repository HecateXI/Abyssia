"""Global PvP battle system with matchmaking, NPC fallback, streaks, and arena rating."""
from __future__ import annotations

import asyncio
import random

import discord
from discord.ext import commands

from core.battle_card_renderer import BattleCardRenderer
from core.cards import render_arena_card, render_team_card
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
    find_match,
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
    row_get,
    save_team_snapshot,
    seconds_until_daily_reset,
    team_creatures,
    team_power,
    top_creatures,
    unlock_achievement,
    update_arena_after_battle,
    weapon_display_name,
    weapon_stats,
)
from core.rpg_data import (
    BOSSES,
    BOUNTY_STREAK,
    STREAK_MILESTONES,
    WEAPON_SHARD_KEY,
    arena_rank,
    get_npc_pool,
    normalize_key,
    streak_multiplier,
)
from core.theme import (
    BLOOD_COLOR,
    GOLD_COLOR,
    asset_emoji,
    boss_label,
    creature_label,
    creature_line,
    currency_label,
    crate_label,
    dark_embed,
    rarity_emoji,
    rarity_label,
    status_effect_emoji,
    status_effect_label,
    status_embed,
    ui_label,
    weapon_emoji,
    weapon_label,
)


REVENGE_COOLDOWN = 10


def creature_power(creature) -> int:
    return team_power([creature])


def _row_value(creature, key: str, fallback: int | str = 0):
    try:
        return creature[key]
    except (KeyError, IndexError, TypeError):
        return fallback


def _get_weapon_affixes(creature: dict) -> dict[str, int]:
    """Extract weapon affixes from creature dict (they're prefixed with _)."""
    affixes = {}
    for key, value in creature.items():
        if key.startswith("_"):
            affix_name = key[1:]
            try:
                affixes[affix_name] = int(value)
            except (TypeError, ValueError):
                pass
    return affixes


def _emoji_prefix(emoji: str) -> str:
    return f"{emoji} " if emoji else ""


def _weapon_status(creature: dict) -> str:
    weapon = creature.get("_weapon") if isinstance(creature.get("_weapon"), dict) else None
    if not weapon:
        return "*no weapon*"
    weapon_name = str(weapon.get("name", "Weapon") or "Weapon")
    weapon_type = str(weapon.get("weapon_type", "sword") or "sword")
    return f"**{weapon_label(weapon_type, weapon_name)}**"


def _battle_team_line(creature: dict) -> str:
    level = int(creature.get("level", 1) or 1)
    name = str(creature.get("name", "?") or "?")
    rarity = str(creature.get("rarity", "Common") or "Common")
    rarity_badge = rarity_emoji(rarity) or rarity
    return f"L.`{level}` {_emoji_prefix(rarity_badge)}**{creature_label(name, rarity)}** - {_weapon_status(creature)}"


def _team_slot_value(slot: int, creature, weapon) -> tuple[str, str]:
    name = str(row_get(creature, "name", "?") or "?")
    rarity = str(row_get(creature, "rarity", "Common") or "Common")
    level = int(row_get(creature, "level", 1) or 1)
    hp = int(row_get(creature, "hp", 0) or 0)
    atk = int(row_get(creature, "attack", 0) or 0)
    defense = int(row_get(creature, "defense", 0) or 0)
    speed = int(row_get(creature, "speed", 0) or 0)
    crit = int(row_get(creature, "crit", 0) or 0)
    mana = int(row_get(creature, "mana", 0) or 0)
    header = f"[{slot}] {rarity_emoji(rarity) or ''} **{creature_label(name, rarity)}**".strip()
    lines = [
        f"Lvl **{level}**",
        f"`HP {hp:,}`",
        f"`ATK {atk:,}`  `DEF {defense:,}`",
        f"`SPD {speed:,}`  `Crit {crit}%`",
        f"`Mana {mana}`",
    ]
    if weapon:
        wtype = str(row_get(weapon, "weapon_type", "sword") or "sword")
        quality_pct = int(row_get(weapon, "quality_pct", 50) or 50)
        ws = weapon_stats(weapon)
        lines.append(f"`{int(row_get(weapon, 'id', 0)):05d}` {weapon_label(wtype, weapon_display_name(weapon))} `{quality_pct}%`")
        if ws:
            lines.append(f"`W ATK +{ws.get('attack', 0)}`  `W DEF +{ws.get('defense', 0)}`")
    else:
        lines.append("*no weapon*")
    return header, "\n".join(lines)


def _battle_overview_embed(
    author: discord.Member | discord.User,
    opponent_name: str,
    left_team: list,
    right_team: list,
    *,
    color: discord.Color,
    image_filename: str,
    footer: str | None = None,
) -> discord.Embed:
    embed = dark_embed(f"{author.display_name} goes into battle!", color=color)
    embed.set_author(name=f"{author.display_name} goes into battle!", icon_url=author.display_avatar.url)
    team_lines = [_battle_team_line(cr) for cr in left_team]
    enemy_lines = [_battle_team_line(cr) for cr in right_team]
    embed.add_field(name=f"{author.display_name}'s Team", value="\n".join(team_lines) if team_lines else "None", inline=True)
    embed.add_field(name="Enemy Team", value="\n".join(enemy_lines) if enemy_lines else "None", inline=True)
    if footer:
        embed.set_footer(text=footer)
    embed.set_image(url=f"attachment://{image_filename}")
    return embed


def _battle_log_line(line: str) -> str:
    lowered = line.lower()
    for key in ("bleed", "burn", "poison", "stun", "shield", "heal", "fear", "curse"):
        if key in lowered:
            return f"{_emoji_prefix(status_effect_emoji(key))}{line}"
    if "crit" in lowered:
        return f"{_emoji_prefix(asset_emoji('passives', 'crit'))}{line}"
    return f"{_emoji_prefix(asset_emoji('ui', 'battle'))}{line}"


def _outcome_badge(won: bool) -> str:
    return rarity_emoji("Legendary") if won else status_effect_emoji("bleed")


def _daily_reset_timer() -> str:
    seconds = max(0, seconds_until_daily_reset())
    hours, rem = divmod(seconds, 3600)
    minutes, sec = divmod(rem, 60)
    return f"{hours}H {minutes}M {sec}S"


def simulate_battle_timeline(left_team, right_team, *, max_turns: int = 30) -> list[dict[str, object]]:
    """
    Simulate a battle between two teams with support for status effects and weapon affixes.
    
    Each creature can have weapon affixes that trigger status effects on hit:
    - bleed, burn, poison: DoT effects
    - shield: reduce damage taken
    - curse, fear: damage reduction
    - stun: skip next turn
    
    Status effects tracked per creature with duration.
    """
    left_hp = [int(c["hp"]) for c in left_team]
    right_hp = [int(c["hp"]) for c in right_team]
    left_mana = [int(_row_value(c, "mana", 50)) for c in left_team]
    right_mana = [int(_row_value(c, "mana", 50)) for c in right_team]
    
    # Extract weapon affixes for each creature
    left_affixes = [_get_weapon_affixes(c) for c in left_team]
    right_affixes = [_get_weapon_affixes(c) for c in right_team]
    
    # Status effect tracking: list of dicts with {"effect": str, "stacks": int, "duration": int}
    left_statuses: list[dict[str, dict]] = [{} for _ in left_team]
    right_statuses: list[dict[str, dict]] = [{} for _ in right_team]
    
    stunned_left: set[int] = set()
    stunned_right: set[int] = set()
    log: list[str] = []
    frames: list[dict[str, object]] = []

    for turn in range(1, max_turns + 1):
        living_left = [index for index, hp in enumerate(left_hp) if hp > 0]
        living_right = [index for index, hp in enumerate(right_hp) if hp > 0]
        if not living_left or not living_right:
            break
        turn_log: list[str] = []
        
        # ── Apply status effects at turn start ──
        for index in living_left:
            if "bleed" in left_statuses[index]:
                damage = max(1, int(left_team[index]["hp"] * 0.05))
                left_hp[index] -= damage
                turn_log.append(f"T{turn}: {left_team[index]['name']} bled for {damage}.")
            if "burn" in left_statuses[index]:
                damage = max(1, int(left_team[index]["hp"] * 0.08))
                left_hp[index] -= damage
                turn_log.append(f"T{turn}: {left_team[index]['name']} took burn damage {damage}.")
            if "poison" in left_statuses[index]:
                damage = max(1, int(left_team[index]["hp"] * 0.06))
                left_hp[index] -= damage
                turn_log.append(f"T{turn}: {left_team[index]['name']} took poison damage {damage}.")
            if "heal" in left_statuses[index]:
                heal = max(3, int(left_team[index]["hp"] * 0.10))
                left_hp[index] = min(int(left_team[index]["hp"]), left_hp[index] + heal)
                turn_log.append(f"T{turn}: {left_team[index]['name']} recovered {heal} HP.")
        
        for index in living_right:
            if "bleed" in right_statuses[index]:
                damage = max(1, int(right_team[index]["hp"] * 0.05))
                right_hp[index] -= damage
                turn_log.append(f"T{turn}: {right_team[index]['name']} bled for {damage}.")
            if "burn" in right_statuses[index]:
                damage = max(1, int(right_team[index]["hp"] * 0.08))
                right_hp[index] -= damage
                turn_log.append(f"T{turn}: {right_team[index]['name']} took burn damage {damage}.")
            if "poison" in right_statuses[index]:
                damage = max(1, int(right_team[index]["hp"] * 0.06))
                right_hp[index] -= damage
                turn_log.append(f"T{turn}: {right_team[index]['name']} took poison damage {damage}.")
            if "heal" in right_statuses[index]:
                heal = max(3, int(right_team[index]["hp"] * 0.10))
                right_hp[index] = min(int(right_team[index]["hp"]), right_hp[index] + heal)
                turn_log.append(f"T{turn}: {right_team[index]['name']} recovered {heal} HP.")
        
        # Re-check living after status effects
        living_left = [index for index, hp in enumerate(left_hp) if hp > 0]
        living_right = [index for index, hp in enumerate(right_hp) if hp > 0]
        if not living_left or not living_right:
            break
        
        # ── Turn order by speed ──
        actors = [("left", index) for index in living_left] + [("right", index) for index in living_right]
        actors.sort(key=lambda item: (left_team if item[0] == "left" else right_team)[item[1]]["speed"], reverse=True)
        
        for side, index in actors:
            living_left = [idx for idx, hp in enumerate(left_hp) if hp > 0]
            living_right = [idx for idx, hp in enumerate(right_hp) if hp > 0]
            if not living_left or not living_right:
                break
            
            attacker = left_team[index] if side == "left" else right_team[index]
            attacker_hp = left_hp if side == "left" else right_hp
            attacker_mana = left_mana if side == "left" else right_mana
            defender_hp = right_hp if side == "left" else left_hp
            attacker_statuses = left_statuses if side == "left" else right_statuses
            attacker_affixes = left_affixes if side == "left" else right_affixes
            defender_statuses = right_statuses if side == "left" else left_statuses
            defender_affixes = right_affixes if side == "left" else left_affixes
            stunned_attackers = stunned_left if side == "left" else stunned_right
            stunned_defenders = stunned_right if side == "left" else stunned_left
            defender_team = right_team if side == "left" else left_team

            # ── Check stun ──
            if index in stunned_attackers:
                stunned_attackers.remove(index)
                turn_log.append(f"T{turn}: {attacker['name']} was stunned.")
                continue

            # ── Shadow Cloak dodge ──
            target_index = random.choice(living_right if side == "left" else living_left)
            defender = defender_team[target_index]
            if defender["ability"] == "Shadow Cloak" and random.random() < 0.08:
                attacker_mana[index] = min(int(_row_value(attacker, "mana", 50)), attacker_mana[index] + 10)
                turn_log.append(f"T{turn}: {defender['name']} dodged with Shadow Cloak.")
                continue

            # ── Action selection ──
            action = "Attack"
            multiplier = 1.0
            if attacker_mana[index] >= 80:
                action = "Ultimate"
                multiplier = 1.85
                attacker_mana[index] -= 80
            elif attacker_mana[index] >= 35 and random.random() < 0.42:
                action = "Skill"
                multiplier = 1.30
                attacker_mana[index] -= 35
            else:
                attacker_mana[index] = min(int(_row_value(attacker, "mana", 50)), attacker_mana[index] + 14)

            # ── Damage calculation ──
            base_damage = attacker["attack"] * multiplier * random.uniform(0.86, 1.16)
            defense_reduction = defender["defense"] * 0.42
            
            # Fear reduces damage
            if "fear" in attacker_statuses[index]:
                base_damage *= 0.75
            
            # Curse reduces damage
            if "curse" in attacker_statuses[index]:
                base_damage *= 0.80
            
            damage = max(3, int(base_damage - defense_reduction))
            
            # Ability bonuses
            if attacker["ability"] == "Infernal Rage":
                damage = round(damage * 1.15)
            elif attacker["ability"] == "Void Corruption":
                damage = round(damage * 1.12)
            elif defender["ability"] == "Blood Pact":
                damage = round(damage * 0.88)

            # Shield reduces damage
            if "shield" in defender_statuses[target_index]:
                damage = round(damage * 0.70)

            # Critical hit
            critical = random.random() < min(0.45, int(_row_value(attacker, "crit", 5)) / 100)
            if critical:
                damage = round(damage * 1.55)
                
                # Weapon crit bonus
                if attacker_affixes[index].get("crit", 0) > 0:
                    damage = round(damage * 1.1)
            
            defender_hp[target_index] -= damage

            # ── Apply status effects from weapon affixes ──
            weapon_affixes = attacker_affixes[index]
            
            # Bleed chance from weapon
            if weapon_affixes.get("bleed", 0) > 0:
                if random.random() < min(0.50, weapon_affixes["bleed"] / 100):
                    if "bleed" not in defender_statuses[target_index]:
                        defender_statuses[target_index]["bleed"] = {"stacks": 1, "duration": 3}
                    else:
                        defender_statuses[target_index]["bleed"]["stacks"] += 1
                        defender_statuses[target_index]["bleed"]["duration"] = max(3, defender_statuses[target_index]["bleed"]["duration"])
            
            # Burn chance from weapon
            if weapon_affixes.get("burn", 0) > 0:
                if random.random() < min(0.50, weapon_affixes["burn"] / 100):
                    if "burn" not in defender_statuses[target_index]:
                        defender_statuses[target_index]["burn"] = {"stacks": 1, "duration": 3}
                    else:
                        defender_statuses[target_index]["burn"]["stacks"] += 1
                        defender_statuses[target_index]["burn"]["duration"] = max(3, defender_statuses[target_index]["burn"]["duration"])
            
            # Poison chance from weapon
            if weapon_affixes.get("poison", 0) > 0:
                if random.random() < min(0.50, weapon_affixes["poison"] / 100):
                    if "poison" not in defender_statuses[target_index]:
                        defender_statuses[target_index]["poison"] = {"stacks": 1, "duration": 3}
                    else:
                        defender_statuses[target_index]["poison"]["stacks"] += 1
                        defender_statuses[target_index]["poison"]["duration"] = max(3, defender_statuses[target_index]["poison"]["duration"])
            
            # Stun chance from weapon
            if weapon_affixes.get("stun", 0) > 0:
                if random.random() < min(0.40, weapon_affixes["stun"] / 100):
                    stunned_defenders.add(target_index)
            
            # Shield buff
            if weapon_affixes.get("shield", 0) > 0:
                if random.random() < min(0.40, weapon_affixes["shield"] / 100):
                    if "shield" not in defender_statuses[target_index]:
                        defender_statuses[target_index]["shield"] = {"stacks": 1, "duration": 2}
                    else:
                        defender_statuses[target_index]["shield"]["stacks"] += 1
            
            # Life steal
            if weapon_affixes.get("life_steal", 0) > 0:
                heal_amount = int(damage * weapon_affixes["life_steal"] / 100)
                attacker_hp[index] = min(int(attacker["hp"]), attacker_hp[index] + heal_amount)
            
            # Creature abilities
            if attacker["ability"] == "Soul Drain":
                attacker_hp[index] = min(int(attacker["hp"]), attacker_hp[index] + max(1, damage // 5))
            elif attacker["ability"] == "Abyssal Howl" and action != "Attack" and random.random() < 0.18:
                stunned_defenders.add(target_index)

            turn_log.append(f"T{turn}: {attacker['name']} used {action}{' CRIT' if critical else ''} on {defender['name']} for {damage}.")

        # ── Decay status effect durations ──
        for index in living_left:
            for status in list(left_statuses[index].keys()):
                left_statuses[index][status]["duration"] -= 1
                if left_statuses[index][status]["duration"] <= 0:
                    del left_statuses[index][status]
        
        for index in living_right:
            for status in list(right_statuses[index].keys()):
                right_statuses[index][status]["duration"] -= 1
                if right_statuses[index][status]["duration"] <= 0:
                    del right_statuses[index][status]

        log.extend(turn_log)
        left_alive = sum(max(0, hp) for hp in left_hp)
        right_alive = sum(max(0, hp) for hp in right_hp)
        frames.append({
            "turn": turn,
            "left_won": left_alive >= right_alive,
            "log": log[-5:],
            "turn_log": list(turn_log),
            "full_log": list(log),
            "left_hp": [max(0, hp) for hp in left_hp],
            "right_hp": [max(0, hp) for hp in right_hp],
            "finished": not left_alive or not right_alive,
        })
        if not left_alive or not right_alive:
            break

    if not frames:
        frames.append({"turn": 0, "left_won": True, "log": ["Battle ended before either team moved."], "full_log": [], "left_hp": left_hp, "right_hp": right_hp, "finished": True})
    return frames


def select_battle_preview_frames(frames: list[dict[str, object]], *, max_frames: int = 5) -> list[dict[str, object]]:
    """Pick a short, evenly spaced preview while preserving the final battle state."""
    if len(frames) <= max_frames:
        return frames
    last = len(frames) - 1
    indexes = {round(i * last / (max_frames - 1)) for i in range(max_frames)}
    return [frames[i] for i in sorted(indexes)]


def streak_milestone_reward(streak: int) -> str | None:
    for need, (name, rtype) in sorted(STREAK_MILESTONES.items(), reverse=True):
        if streak == need:
            return need, name, rtype
    return None


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
        frames = simulate_battle_timeline(left_team, right_team)
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
            "zone_key": str(attacker["current_zone"]) if "current_zone" in attacker.keys() else "bloodmoon_forest",
                "log": [],
            }
            image = battle_renderer.render_battle_frame(frame_data)
            filename = f"abyssia_battle_turn_{frame_index}.png"
            file = discord.File(image, filename=filename)
            embed = _battle_overview_embed(
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
        won = bool(result["left_won"])

        arena = await ensure_arena_stats(self.bot.db, ctx.author.id, ctx.guild.id)
        opp_arena = await ensure_arena_stats(self.bot.db, opponent_id, ctx.guild.id) if not is_npc else None
        opp_rating = int(opp_arena["rating"]) if opp_arena else int(arena["rating"])
        winner_change, loser_change = elo_rating_change(int(arena["rating"]), opp_rating)
        rating_change = winner_change if won else loser_change

        await update_arena_after_battle(self.bot.db, ctx.author.id, ctx.guild.id, won, rating_change)
        if not is_npc and opp_arena:
            await update_arena_after_battle(self.bot.db, opponent_id, ctx.guild.id, not won, loser_change if won else winner_change)

        streak = int(arena["win_streak"]) + 1 if won else 0
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
        else:
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
        for line in (log or []):
            for cr in left_team + right_team:
                cn = str(cr.get("name", ""))
                if cn and cn in line:
                    creature_damage.setdefault(cn, 0)
                    creature_kills.setdefault(cn, 0)
            if "CRIT" in line:
                crits += 1
            if "for " in line and "damage" in line:
                try:
                    parts = line.split("for ")
                    val = int(parts[-1].split()[0].replace(",", ""))
                    if ctx.author.display_name in line or any(cn in line for cn in [c["name"] for c in left_team]):
                        damage_dealt += val
                        for cr in left_team:
                            if cr["name"] in line:
                                creature_damage[str(cr["name"])] = creature_damage.get(str(cr["name"]), 0) + val
                    else:
                        damage_taken += val
                except (ValueError, IndexError):
                    pass
            if any(e in line for e in ["Bleed", "Burn", "Poison", "Stun", "Shield"]):
                status_applied += 1
            if "defeated" in line.lower() or "DEFEATED" in line:
                for cr in left_team:
                    if str(cr.get("name", "")) in line:
                        creature_kills[str(cr.get("name", ""))] = creature_kills.get(str(cr.get("name", "")), 0) + 1

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

        battle_result_data = {
            "won": won,
            "winner_name": ctx.author.display_name if won else opponent_name,
            "loser_name": opponent_name if won else ctx.author.display_name,
            "player_name": ctx.author.display_name,
            "enemy_name": opponent_name,
            "player_team": left_team,
            "enemy_team": right_team,
            "player_hp": list(result["left_hp"]),
            "enemy_hp": list(result["right_hp"]),
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
            "xp_reward": rewards.get("xp", 0),
            "gold_reward": rewards.get("gold", 0),
            "turns": int(result.get("turn", len(frames))),
        }

        image = battle_renderer.render_battle_result(battle_result_data)
        file = discord.File(image, filename="abyssia_battle.png")
        turns_total = int(result.get("turn", len(frames)))
        result_word = "won" if won else "lost"
        embed = _battle_overview_embed(
            ctx.author,
            opponent_name,
            left_team,
            right_team,
            color=discord.Color.green() if won else discord.Color.dark_red(),
            image_filename="abyssia_battle.png",
            footer=f"You {result_word} in {turns_total} turns! | +{int(rewards.get('xp', 0))} xp | Rating {new_rating} ({rating_change:+d})",
        )
        message_content = None
        if checklist_crates:
            message_content = (
                f"{crate_label('cache', 'Weapon Crate')} | **{ctx.author.display_name}**, "
                f"You found a **weapon crate!** `[{checklist_crate_count}/3]` "
                f"**RESETS IN:** `{_daily_reset_timer()}`"
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

    async def _get_or_make_opponent(self, ctx: commands.Context, player_team: list) -> tuple[str, int, list]:
        match = await find_match(self.bot.db, ctx.author.id)
        if match:
            opp_id = int(match["user_id"])
            opp_guild = int(match["guild_id"])
            opp_player = await ensure_player(self.bot.db, opp_id, "Opponent")
            opp_name = str(opp_player["hunter_name"])
            opp_team = await prepare_battle(self.bot.db, opp_id)
            if opp_team:
                return opp_name, opp_id, opp_team

        # Try offline player snapshot
        offline = await self.bot.db.fetchall(
            "SELECT DISTINCT user_id FROM rpg_team_snapshots WHERE user_id != ? ORDER BY RANDOM() LIMIT 5",
            (ctx.author.id,),
        )
        for row in offline:
            snap = await load_team_snapshot(self.bot.db, int(row["user_id"]))
            if snap:
                opp_row = await self.bot.db.fetchone("SELECT hunter_name FROM rpg_players WHERE user_id = ?", (int(row["user_id"]),))
                opp_name = str(opp_row["hunter_name"]) if opp_row else "Wandering Hunter"
                return opp_name, int(row["user_id"]), snap

        # NPC fallback
        arena = await ensure_arena_stats(self.bot.db, ctx.author.id, ctx.guild.id)
        rating = int(arena["rating"])
        pool = get_npc_pool(rating)
        npc = random.choice(pool)
        npc_team = generate_npc_team(npc)
        player_power = team_power(player_team)
        npc_power = team_power(npc_team)
        scale = max(0.7, min(1.3, player_power / max(1, npc_power)))
        for c in npc_team:
            c["attack"] = round(int(c["attack"]) * scale)
            c["defense"] = round(int(c["defense"]) * scale)
            c["hp"] = round(int(c["hp"]) * scale)
            c["speed"] = round(max(1, int(c["speed"]) * scale))
            c["level"] = max(1, round(int(c["level"]) * scale))
        rank_label = arena_rank(rating)
        npc_name = f"{npc.title} {npc.name}"
        return npc_name, 0, npc_team

    # ── Team Commands ────────────────────────────────────────────────

    @commands.hybrid_group(name="team", invoke_without_command=True)
    async def team(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        """Show a hunter's battle team with a team card."""
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
                f"Then `{prefix}team set 2 <name>` and `{prefix}team set 3 <name>` for slots 2 and 3.\n"
                f"Example: `{prefix}team set 1 {your_creatures[0]['name']}`",
                color=GOLD_COLOR,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return
        power = team_power(creatures)
        cids = [int(c["id"]) for c in creatures]
        weapons = await creature_weapons(self.bot.db, cids)
        arena = await ensure_arena_stats(self.bot.db, target.id, ctx.guild.id)
        title = ui_label("team", f"{target.display_name}'s Team")
        description = (
            "`b team set <slot> <name>` set a team slot\n"
            "`b weaponequip <weapon id> <creature>` equip a weapon"
        )
        embed = discord.Embed(title=title, description=description, color=GOLD_COLOR)
        embed.set_author(name=str(target), icon_url=target.display_avatar.url)
        for index, creature in enumerate(creatures[:3], start=1):
            field_name, field_value = _team_slot_value(index, creature, weapons.get(int(creature["id"])))
            embed.add_field(name=field_name, value=field_value, inline=True)
        embed.set_footer(
            text=(
                f"Team Power: {power:,} | Current Streak: {int(arena['win_streak'])} | "
                f"Highest Streak: {int(arena['highest_win_streak'])}"
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
        creatures = await self.bot.db.fetchall(
            "SELECT id, name FROM rpg_creatures WHERE user_id = ? AND LOWER(name) LIKE ? ORDER BY level DESC, attack + defense + hp + speed DESC LIMIT 1",
            (ctx.author.id, f"%{creature_name.lower()}%"),
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

    # ── Battle Command ──────────────────────────────────────────────

    @commands.hybrid_command(name="battle", aliases=["duel"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def battle(self, ctx: commands.Context, opponent: discord.Member | None = None) -> None:
        """Battle another hunter or enter global matchmaking."""
        assert ctx.guild is not None
        await ensure_application_emojis(self.bot, max_age=60.0)
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)

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
            challenge = dark_embed(
                ui_label("battle", "Duel Challenge"),
                f"{ctx.author.mention} challenges {opponent.mention} to a duel.\n\n"
                f"Team Power: **{team_power(left_team):,}** vs **{team_power(right_team):,}**\n"
                "Expires in **60s**.",
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
            opp_name = opponent.display_name
            opp_id = opponent.id
        else:
            # Auto matchmaking
            await save_team_snapshot(self.bot.db, ctx.author.id)
            left_team = await prepare_battle(self.bot.db, ctx.author.id)
            if not left_team:
                raise commands.BadArgument("You need at least one creature in your team to battle. Use `b team set`.")
            await join_battle_queue(self.bot.db, ctx.author.id, ctx.guild.id)
            status_msg = await ctx.reply(embed=dark_embed(ui_label("battle", "Matchmaking"), "Searching for an opponent...", color=discord.Color.dark_gray()), mention_author=False)
            await asyncio.sleep(1)
            opp_name, opp_id, right_team = await self._get_or_make_opponent(ctx, left_team)
            await status_msg.delete()
            if opp_id == ctx.author.id:
                raise commands.BadArgument("No opponents found. Try again later.")

        await self._run_battle_and_reward(ctx, player, left_team, opp_name, opp_id, right_team, is_npc=(opp_id == 0))

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
            badge = _outcome_badge(won) or ("WIN" if won else "LOSS")
            npc_tag = " [NPC]" if r["is_npc"] else ""
            lines.append(f"{badge} vs **{r['opponent_name']}**{npc_tag} - rating `{r['rating_change']:+d}` -> `{r['opponent_rating']}`")
        embed = dark_embed(
            ui_label("battle", "Battle History"),
            f"Record: **{wins}W** / **{losses}L**\n\n" + "\n".join(lines),
            color=GOLD_COLOR,
        )
        await ctx.reply(embed=embed, mention_author=False)

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

        message = (
            f"{ui_label('leaderboard', 'Rating')}: **{arena['rating']}** | Rank: **{rank}**\n"
            f"{ui_label('battle', 'Record')}: **{wins}W** / **{losses}L** ({winrate})\n"
            f"{status_effect_label('burn', 'Current streak')}: **{streak}** | Best: **{best}**\n"
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
