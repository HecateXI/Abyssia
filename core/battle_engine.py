from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

from core.rpg_data import CREATURES, INFUSED_PREFIXES, RARITY_BY_NAME, WEAPON_TYPES, derive_7stats, normalize_key


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        if hasattr(row, "keys") and key not in row.keys():
            return default
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _quality(value: Any) -> float:
    return _clamp(_float(value, 50.0), 0.0, 150.0) / 150.0


def _parse_json(raw: Any, fallback: Any) -> Any:
    if raw in (None, ""):
        return fallback
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(str(raw))
    except Exception:
        return fallback


def _template_name(name: str) -> str:
    clean = str(name or "").strip()
    for prefix in INFUSED_PREFIXES:
        prefix_text = f"{prefix} "
        if clean.startswith(prefix_text):
            return clean[len(prefix_text):]
    return clean


_TEMPLATES = {normalize_key(creature.name): creature for creature in CREATURES}

_STATUS_LABELS = {
    "bleed": "bleeding",
    "burn": "burned",
    "poison": "poisoned",
    "stun": "stunned",
}


# -- Structured Battle Event --

@dataclass
class BattleEvent:
    round_no: int
    actor: str
    actor_side: str
    action: str
    target: str | None = None
    action_type: str = "damage"
    stat_used: str | None = None
    stat_value: int = 0
    defense_used: str | None = None
    defense_value: int = 0
    mana_before: int = 0
    mana_after: int = 0
    damage: int = 0
    healing: int = 0
    is_crit: bool = False
    status_applied: str | None = None
    status_damage: int = 0
    defeated: str | None = None
    is_first: bool = False
    skipped_reason: str | None = None
    heal_from_lifesteal: int = 0
    heal_from_regen: int = 0


# -- Ability --

@dataclass
class Ability:
    id: str
    name: str
    scale_stat: str
    multiplier_min: float
    multiplier_max: float
    damage_type: str
    wp_cost_min: int
    wp_cost_max: int
    mode: str = "damage"
    status: str | None = None

    @classmethod
    def for_weapon_type(cls, weapon_type: str) -> "Ability":
        specs: dict[str, dict[str, Any]] = {
            "sword": dict(name="Gravecut", scale="STR", mult=(1.15, 1.65), dtype="physical", cost=(100, 190), mode="execute"),
            "bow": dict(name="Black Arrow", scale="STR", mult=(1.10, 1.60), dtype="physical", cost=(120, 220), mode="double_strike"),
            "axe": dict(name="Butcher Sweep", scale="STR", mult=(0.65, 0.95), dtype="physical", cost=(140, 240), mode="cleave"),
            "dagger": dict(name="Vein Pierce", scale="STR", mult=(0.80, 1.20), dtype="physical", cost=(90, 180), mode="bleed_apply", status="bleed"),
            "crossbow": dict(name="Coffin Nail", scale="STR", mult=(2.20, 3.10), dtype="physical", cost=(260, 460), mode="charge"),
            "staff": dict(name="Witchflame", scale="MAG", mult=(0.85, 1.20), dtype="magical", cost=(110, 210), mode="burn_detonate", status="burn"),
            "staff_of_purity": dict(name="Black Benediction", scale="MAG", mult=(0.65, 1.15), dtype="magical", cost=(150, 230), mode="cleanse_ward"),
            "shield": dict(name="Oath of the Last Wall", scale="HP", mult=(0.10, 0.18), dtype="true", cost=(150, 260), mode="taunt_shield"),
            "hammer": dict(name="Bellringer", scale="STR", mult=(1.00, 1.45), dtype="physical", cost=(150, 250), mode="stagger_stun"),
            "orb": dict(name="Void Resonance", scale="MAG", mult=(0.45, 0.70), dtype="magical", cost=(130, 220), mode="heal"),
            "rune": dict(name="Rune Empowerment", scale="MAG", mult=(0, 0), dtype="true", cost=(0, 0), mode="rune_empowerment"),
            "soulreaper": dict(name="Mortal Harvest", scale="STR", mult=(0.80, 1.20), dtype="physical", cost=(120, 220), mode="mortality"),
            "briar_relic": dict(name="Thorn Tether", scale="HP", mult=(0.25, 0.50), dtype="true", cost=(140, 240), mode="tether"),
            "rot_chalice": dict(name="Rotten Communion", scale="MAG", mult=(0.60, 0.90), dtype="magical", cost=(130, 230), mode="poison_spread", status="poison"),
            "banner": dict(name="War Under No Dawn", scale="MAG", mult=(0.15, 0.25), dtype="true", cost=(230, 300), mode="team_buff"),
            "eye": dict(name="Witness Madness", scale="MAG", mult=(1.50, 2.10), dtype="magical", cost=(0, 0), mode="force_attack"),
            "judgement_blade": dict(name="Sin and Sentence", scale="STR", mult=(1.00, 1.40), dtype="physical", cost=(125, 225), mode="stack_consumption"),
            "lantern": dict(name="Light That Starves", scale="MAG", mult=(0.70, 1.10), dtype="magical", cost=(100, 200), mode="mana_drain"),
            "mirror_relic": dict(name="Reflected Curse", scale="HP", mult=(0.50, 0.90), dtype="true", cost=(120, 220), mode="reflect_debuff"),
            "final_bell_scythe": dict(name="Toll the End", scale="STR", mult=(0.60, 0.90), dtype="physical", cost=(180, 280), mode="doom_bell"),
        }
        data = specs.get(weapon_type, specs["sword"])
        low, high = data["mult"]
        cost_low, cost_high = data["cost"]
        return cls(
            id=weapon_type,
            name=str(data["name"]),
            scale_stat=str(data["scale"]),
            multiplier_min=float(low),
            multiplier_max=float(high),
            damage_type=str(data["dtype"]),
            wp_cost_min=int(cost_low),
            wp_cost_max=int(cost_high),
            mode=str(data.get("mode", "damage")),
            status=data.get("status"),
        )

    def multiplier(self, quality_percent: int) -> float:
        q = _quality(quality_percent)
        return self.multiplier_min + (self.multiplier_max - self.multiplier_min) * q

    def wp_cost(self, quality_percent: int) -> int:
        q = _quality(quality_percent)
        return max(1, round(self.wp_cost_max - (self.wp_cost_max - self.wp_cost_min) * q))


# -- Passive --

@dataclass
class Passive:
    key: str
    name: str
    value: int
    roll: int = 50

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Passive | None":
        key = str(data.get("key") or data.get("stat") or "").lower()
        if not key:
            return None
        value = _int(data.get("value", data.get("chance", 0)), 0)
        return cls(
            key=key,
            name=str(data.get("name") or key.replace("_", " ").title()),
            value=max(0, value),
            roll=_int(data.get("roll", 50), 50),
        )

    def apply_to(self, creature: "Creature") -> None:
        roll = max(0, min(100, self.roll))
        if self.key in {"strength", "attack_pct"}:
            creature.strength = round(creature.strength * (1.0 + roll / 100.0))
        elif self.key == "magic":
            creature.magic = round(creature.magic * (1.0 + roll / 100.0))
        elif self.key == "hp":
            old_max = creature.max_hp
            creature.max_hp = round(creature.max_hp * (1.0 + roll / 100.0))
            creature.current_hp += max(0, creature.max_hp - old_max)
        elif self.key == "wp":
            old_max = creature.max_wp
            creature.max_wp = round(creature.max_wp * (1.0 + roll * 1.5 / 100.0))
            creature.current_wp += max(0, creature.max_wp - old_max)
        elif self.key == "pr":
            creature.pr = min(0.80, creature.pr + roll / 100.0 * 0.35)
        elif self.key in {"mr", "defense_pct"}:
            creature.mr = min(0.80, creature.mr + roll / 100.0 * 0.35)
            if self.key == "defense_pct":
                creature.pr = min(0.80, creature.pr + roll / 100.0 * 0.35)
        elif self.key == "crit":
            creature.crit = creature.crit + roll / 10.0
            creature.crit_damage_bonus = creature.crit_damage_bonus + roll / 5.0 / 100.0
        elif self.key == "life_steal":
            pass
        elif self.key == "mana_tap":
            pass
        elif self.key == "soul_gain":
            pass
        elif self.key == "gem_finder":
            pass
        elif self.key == "xp_boost":
            pass
        elif self.key == "rare_finder":
            pass
        elif self.key == "energize":
            pass
        elif self.key == "fear":
            pass


# -- Weapon --

@dataclass
class Weapon:
    id: int | None
    name: str
    weapon_type: str
    rarity: str
    statRolls: dict[str, int]
    passiveSlots: int
    wpCostMin: int
    wpCostMax: int
    activeAbility: Ability
    passives: list[Passive]
    qualityPercent: int

    @classmethod
    def from_row(cls, row: Any) -> "Weapon | None":
        if not row:
            return None
        weapon_type = str(_row_get(row, "weapon_type", "sword") or "sword")
        ability = Ability.for_weapon_type(weapon_type)
        quality = _int(_row_get(row, "quality_pct", 50), 50)
        passive_slots = 0 if weapon_type == "rune" else (2 if weapon_type == "orb" else 1)
        rolls: dict[str, int] = {"quality": quality}
        passives: list[Passive] = []

        passive_raw = _parse_json(_row_get(row, "passive"), None)
        if isinstance(passive_raw, dict):
            passive = Passive.from_dict(passive_raw)
            if passive:
                passives.append(passive)
                rolls["passive_1"] = passive.roll
            for idx, extra_data in enumerate(passive_raw.get("extra", []) if isinstance(passive_raw.get("extra"), list) else [], start=2):
                if not isinstance(extra_data, dict):
                    continue
                extra = Passive.from_dict(extra_data)
                if extra:
                    passives.append(extra)
                    rolls[f"passive_{idx}"] = extra.roll

        affixes = _parse_json(_row_get(row, "affixes", "[]"), [])
        if isinstance(affixes, list):
            for index, affix in enumerate(affixes, start=1):
                if not isinstance(affix, dict):
                    continue
                passive = Passive.from_dict(affix)
                if passive:
                    passives.append(passive)
                    rolls[f"affix_{index}"] = passive.roll
        if weapon_type == "rune":
            passives = []

        return cls(
            id=_int(_row_get(row, "id"), 0) or None,
            name=str(_row_get(row, "name", "Weapon") or "Weapon"),
            weapon_type=weapon_type,
            rarity=str(_row_get(row, "rarity", "Common") or "Common"),
            statRolls=rolls,
            passiveSlots=passive_slots,
            wpCostMin=ability.wp_cost_min,
            wpCostMax=ability.wp_cost_max,
            activeAbility=ability,
            passives=passives[: max(passive_slots, len(passives))],
            qualityPercent=quality,
        )


# -- Creature --

@dataclass
class Creature:
    source: dict[str, Any]
    side: str
    index: int
    id: int
    name: str
    rarity: str
    level: int
    ability: str
    hp_stat: int
    str_stat: int
    pr_stat: int
    wp_stat: int
    mag_stat: int
    mr_stat: int
    speed: int
    crit: float
    crit_damage_bonus: float = 0.0
    weapon: Weapon | None = None
    max_hp: int = 0
    current_hp: int = 0
    strength: int = 0
    max_wp: int = 0
    current_wp: int = 0
    magic: int = 0
    pr: float = 0.0
    mr: float = 0.0
    statuses: dict[str, dict[str, Any]] = field(default_factory=dict)
    taunting: bool = False
    sacrifice_triggered: bool = False

    @classmethod
    def from_row(cls, row: dict[str, Any], side: str, index: int) -> "Creature":
        name = str(row.get("name", "Creature") or "Creature")
        rarity = str(row.get("rarity", "Common") or "Common")
        level = max(1, _int(row.get("level", 1), 1))

        raw_str = _int(row.get("str_stat"), 0)
        raw_pr = _int(row.get("pr_stat"), 0)
        raw_hp = _int(row.get("hp_stat"), 0)
        raw_wp = _int(row.get("wp_stat"), 0)
        raw_mag = _int(row.get("mag_stat"), 0)
        raw_mr = _int(row.get("mr_stat"), 0)
        raw_spd = _int(row.get("spd"), 0)

        if raw_str > 0 and raw_hp > 0:
            hp_stat = max(1, raw_hp)
            str_stat = max(1, raw_str)
            pr_stat = max(1, raw_pr)
            wp_stat = max(1, raw_wp)
            mag_stat = max(1, raw_mag)
            mr_stat = max(1, raw_mr)
            speed = max(1, raw_spd)
            ability = str(row.get("ability", "Attack") or "Attack")
        else:
            template = _TEMPLATES.get(normalize_key(_template_name(name)))
            rarity_mult = float(RARITY_BY_NAME.get(rarity, RARITY_BY_NAME["Common"]).stat_multiplier)
            if template:
                s7 = derive_7stats(template)
                hp_stat = max(1, round(s7["hp"] * rarity_mult))
                str_stat = max(1, round(s7["str"] * rarity_mult))
                pr_stat = max(1, round(s7["pr"] * rarity_mult))
                wp_stat = max(1, round(s7["wp"] * rarity_mult))
                mag_stat = max(1, round(s7["mag"] * rarity_mult))
                mr_stat = max(1, round(s7["mr"] * rarity_mult))
                speed = max(1, round(s7["spd"] * rarity_mult))
                ability = template.ability
            else:
                hp = max(1, _int(row.get("hp", 600), 600))
                attack = max(1, _int(row.get("attack", 120), 120))
                defense = max(1, _int(row.get("defense", 30), 30))
                mana = max(1, _int(row.get("mana", 200), 200))
                speed = max(1, _int(row.get("speed", 10), 10))
                hp_stat = max(1, round(max(0, hp - 500) / (2 * level))) if hp > 500 else max(1, round(hp / 20))
                str_stat = max(1, round(attack / max(1, level)))
                pr_stat = max(1, round(defense / max(1, level)))
                wp_stat = max(1, round(max(0, mana - 500) / (2 * level))) if mana > 500 else max(1, round(mana / 20))
                mag_stat = max(1, round((speed + str_stat) * 0.5))
                mr_stat = max(1, round((pr_stat + speed) * 0.5))
                ability = str(row.get("ability", "Attack") or "Attack")

        creature = cls(
            source=row,
            side=side,
            index=index,
            id=_int(row.get("id"), index),
            name=name,
            rarity=rarity,
            level=level,
            ability=ability,
            hp_stat=hp_stat,
            str_stat=str_stat,
            pr_stat=pr_stat,
            wp_stat=wp_stat,
            mag_stat=mag_stat,
            mr_stat=mr_stat,
            speed=max(1, speed),
            crit=float(_int(row.get("crit", 5), 5)),
            weapon=Weapon.from_row(row.get("_weapon")),
        )
        creature.calculate_final_stats()
        return creature

    def calculate_final_stats(self) -> None:
        self.max_hp = 2 * self.hp_stat * self.level + 500
        self.current_hp = self.max_hp
        self.strength = self.str_stat * self.level + 100
        self.max_wp = 2 * self.wp_stat * self.level + 500
        self.current_wp = self.max_wp
        self.magic = self.mag_stat * self.level + 100
        self.pr = 0.8 * ((25 + 2 * self.pr_stat * self.level) / (125 + 2 * self.pr_stat * self.level))
        self.mr = 0.8 * ((25 + 2 * self.mr_stat * self.level) / (125 + 2 * self.mr_stat * self.level))
        if self.weapon:
            for passive in self.weapon.passives:
                passive.apply_to(self)
        self.current_hp = min(self.current_hp, self.max_hp)
        self.current_wp = min(self.current_wp, self.max_wp)

    @property
    def alive(self) -> bool:
        return self.current_hp > 0

    def stat_value(self, stat: str) -> int:
        stat = stat.upper()
        if stat == "STR":
            return self.strength
        if stat == "MAG":
            return self.magic
        if stat == "HP":
            return self.max_hp
        if stat == "MANA":
            return self.max_wp
        if stat == "DEF":
            return round(self.pr * 1000)
        if stat == "RES":
            return round(self.mr * 1000)
        return self.strength

    def add_status(self, key: str, *, duration: int = 3, power: int = 1, order: int = 0) -> None:
        status = self.statuses.setdefault(key, {"duration": 0, "stacks": 0, "power": power})
        status["duration"] = max(int(status.get("duration", 0)), duration)
        status["stacks"] = min(5, int(status.get("stacks", 0)) + 1)
        status["power"] = max(power, int(status.get("power", power)))
        status.setdefault("order", order)

    def remove_oldest_buff(self) -> str | None:
        buff_keys = {"shield", "attack_up", "defense_up", "taunt", "regeneration"}
        matches = [(key, int(data.get("order", 0))) for key, data in self.statuses.items() if key in buff_keys]
        if not matches:
            return None
        key = min(matches, key=lambda item: item[1])[0]
        del self.statuses[key]
        return key

    def remove_oldest_debuff(self) -> str | None:
        buff_keys = {"shield", "attack_up", "defense_up", "taunt", "regeneration"}
        matches = [(key, int(data.get("order", 0))) for key, data in self.statuses.items() if key not in buff_keys]
        if not matches:
            return None
        key = min(matches, key=lambda item: item[1])[0]
        del self.statuses[key]
        return key

    def export(self) -> None:
        self.source["hp"] = self.max_hp
        self.source["attack"] = self.strength
        self.source["defense"] = max(1, round((self.pr + self.mr) * 250))
        self.source["mana"] = self.max_wp
        self.source["speed"] = self.speed
        self.source["crit"] = round(self.crit)
        self.source["ability"] = self.ability
        self.source["_battle_stats"] = {
            "HP": self.max_hp,
            "STR": self.strength,
            "DEF": round(self.pr, 4),
            "MANA": self.max_wp,
            "MAG": self.magic,
            "RES": round(self.mr, 4),
        }


# ===== BattleEngine — event-driven battle simulation =====

class BattleEngine:
    def __init__(self, left_team: list[dict[str, Any]], right_team: list[dict[str, Any]], *, max_turns: int = 30, log_enabled: bool = False) -> None:
        self.left = [Creature.from_row(creature, "left", index) for index, creature in enumerate(left_team)]
        self.right = [Creature.from_row(creature, "right", index) for index, creature in enumerate(right_team)]
        self.max_turns = max_turns
        self.debug = log_enabled
        self.tied = False
        self._status_order = 0
        self.events: list[BattleEvent] = []
        for creature in self.left + self.right:
            creature.export()

    def run(self) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        for turn in range(1, self.max_turns + 1):
            left_living = self._living(self.left)
            right_living = self._living(self.right)
            if not left_living or not right_living:
                break
            self._turn_start(turn)
            left_living = self._living(self.left)
            right_living = self._living(self.right)
            if not left_living or not right_living:
                frames.append(self._frame(turn))
                self._render_frame_logs(frames[-1], turn)
                break
            actors = [creature for creature in self.left + self.right if creature.alive]
            actors.sort(key=lambda c: (c.speed, c.current_wp, c.level), reverse=True)
            for idx, actor in enumerate(actors):
                if not actor.alive:
                    self.events.append(BattleEvent(
                        round_no=turn, actor=actor.name, actor_side=actor.side,
                        action="", action_type="skip", skipped_reason="dead",
                        is_first=(idx == 0), target=actor.name, defeated=actor.name,
                    ))
                    continue
                enemies = self._living(self.right if actor.side == "left" else self.left)
                allies = self._living(self.left if actor.side == "left" else self.right)
                if not enemies or not allies:
                    break
                self._act(turn, actor, allies, enemies, is_first=(idx == 0))
            self._turn_end()
            frame = self._frame(turn)
            self._render_frame_logs(frame, turn)
            frames.append(frame)
            if frame["finished"]:
                break
        if not frames:
            frame = self._frame(0)
            self._render_frame_logs(frame, 0)
            frames.append(frame)
        self._resolve_result(frames)
        return frames

    def _resolve_result(self, frames: list[dict[str, Any]]) -> None:
        last = frames[-1]
        left_alive = any(c.current_hp > 0 for c in self.left)
        right_alive = any(c.current_hp > 0 for c in self.right)

        if last["turn"] >= self.max_turns and left_alive and right_alive:
            self.tied = True
            last["tied"] = True
            last["finished"] = True
            last["left_won"] = False
        elif last["finished"]:
            self.tied = False

        if not self.tied and last["finished"]:
            winner_side = "Left" if last["left_won"] else "Right"
            last["left_won"] = (winner_side == "Left")
        elif not last["finished"]:
            last["left_won"] = False
            last["tied"] = True
            last["finished"] = True

        # Re-render final frame logs with result block appended
        self._render_frame_logs(last, last["turn"])

    def _render_frame_logs(self, frame: dict[str, Any], up_to_turn: int) -> None:
        turn_events = [e for e in self.events if e.round_no == up_to_turn]
        up_to_events = [e for e in self.events if e.round_no <= up_to_turn]
        turn_ids = {id(e) for e in turn_events}
        if self.debug:
            turn_log, full_log = self._render_debug_log(up_to_events, turn_ids, frame)
        else:
            turn_log, full_log = self._render_story_log(up_to_events, turn_ids, frame)
        frame["turn_log"] = turn_log
        frame["full_log"] = full_log
        frame["log"] = full_log[-5:]
        frame["compact_log"] = self._render_compact_log(up_to_events)

    def _render_story_log(self, up_to_events: list[BattleEvent], turn_ids: set[int], frame: dict[str, Any]) -> tuple[list[str], list[str]]:
        turn_log: list[str] = []
        full_log: list[str] = []
        current_round = 0
        for ev in up_to_events:
            is_turn = id(ev) in turn_ids
            if ev.round_no != current_round:
                current_round = ev.round_no
                if is_turn:
                    turn_log.append(f"Round {current_round}")
                    turn_log.append("")
                full_log.append(f"Round {current_round}")
                full_log.append("")
            if ev.action_type == "skip":
                if ev.is_first and ev.skipped_reason != "dead":
                    if is_turn:
                        turn_log.append(f"{ev.actor} acts first. SPD {self._get_speed(ev.actor)}.")
                    full_log.append(f"{ev.actor} acts first. SPD {self._get_speed(ev.actor)}.")
                if ev.defeated:
                    if is_turn:
                        turn_log.append(f"{ev.actor} cannot act.")
                        turn_log.append(f"{ev.actor} is defeated.")
                    full_log.append(f"{ev.actor} cannot act.")
                    full_log.append(f"{ev.actor} is defeated.")
                elif ev.skipped_reason == "stunned":
                    if is_turn:
                        turn_log.append(f"{ev.actor} is stunned and cannot act.")
                    full_log.append(f"{ev.actor} is stunned and cannot act.")
                if is_turn:
                    turn_log.append("")
                full_log.append("")
                continue
            if ev.heal_from_regen > 0:
                if is_turn:
                    turn_log.append(f"{ev.actor} regenerates {ev.heal_from_regen} HP.")
                full_log.append(f"{ev.actor} regenerates {ev.heal_from_regen} HP.")
            if ev.status_damage > 0:
                status_key = ev.action
                if is_turn:
                    turn_log.append(f"{ev.actor} suffers {ev.status_damage} {status_key} damage.")
                full_log.append(f"{ev.actor} suffers {ev.status_damage} {status_key} damage.")
            if ev.action == "":
                continue
            if ev.is_first:
                if is_turn:
                    turn_log.append(f"{ev.actor} acts first. SPD {self._get_speed(ev.actor)}.")
                full_log.append(f"{ev.actor} acts first. SPD {self._get_speed(ev.actor)}.")
            if is_turn:
                turn_log.append(f"{ev.actor} uses {ev.action}.")
            full_log.append(f"{ev.actor} uses {ev.action}.")
            if ev.mana_before != ev.mana_after:
                if is_turn:
                    turn_log.append(f"MANA {ev.mana_before} -> {ev.mana_after}.")
                full_log.append(f"MANA {ev.mana_before} -> {ev.mana_after}.")
            if ev.target is not None:
                if is_turn:
                    turn_log.append(f"Target: {ev.target}.")
                full_log.append(f"Target: {ev.target}.")
            if ev.stat_used and ev.defense_used:
                if is_turn:
                    turn_log.append(f"{ev.stat_used} {ev.stat_value} vs {ev.defense_used} {ev.defense_value}.")
                full_log.append(f"{ev.stat_used} {ev.stat_value} vs {ev.defense_used} {ev.defense_value}.")
            if ev.damage > 0:
                if is_turn:
                    turn_log.append(f"{ev.target} takes {ev.damage} damage.")
                full_log.append(f"{ev.target} takes {ev.damage} damage.")
            if ev.is_crit:
                if is_turn:
                    turn_log.append("Critical hit.")
                full_log.append("Critical hit.")
            if ev.healing > 0:
                if is_turn:
                    turn_log.append(f"{ev.actor} heals {ev.healing} HP.")
                full_log.append(f"{ev.actor} heals {ev.healing} HP.")
            if ev.heal_from_lifesteal > 0:
                if is_turn:
                    turn_log.append(f"{ev.actor} heals {ev.heal_from_lifesteal} HP.")
                full_log.append(f"{ev.actor} heals {ev.heal_from_lifesteal} HP.")
            if ev.status_applied:
                label = _STATUS_LABELS.get(ev.status_applied, ev.status_applied)
                if is_turn:
                    turn_log.append(f"{ev.target} is {label}.")
                full_log.append(f"{ev.target} is {label}.")
            if ev.defeated:
                if is_turn:
                    turn_log.append(f"{ev.defeated} is defeated.")
                full_log.append(f"{ev.defeated} is defeated.")
            if is_turn:
                turn_log.append("")
            full_log.append("")
        self._append_result_block(full_log, frame)
        if frame.get("tied") or frame.get("finished"):
            self._append_result_block(turn_log, frame)
        return turn_log, full_log

    def _render_compact_log(self, up_to_events: list[BattleEvent]) -> list[str]:
        hp: dict[str, int] = {}
        mx: dict[str, int] = {}
        for c in self.left + self.right:
            mx[c.name] = c.max_hp
            hp[c.name] = c.max_hp
        lines: list[str] = []
        current_turn = 0
        for ev in up_to_events:
            if ev.damage > 0 and ev.target:
                hp[ev.target] = max(0, hp[ev.target] - ev.damage)
            if ev.status_damage > 0:
                hp[ev.actor] = max(0, hp[ev.actor] - ev.status_damage)
            if ev.healing > 0:
                hp[ev.actor] = min(mx.get(ev.actor, hp.get(ev.actor, 0)), hp.get(ev.actor, 0) + ev.healing)
            if ev.heal_from_lifesteal > 0:
                hp[ev.actor] = min(mx.get(ev.actor, hp.get(ev.actor, 0)), hp.get(ev.actor, 0) + ev.heal_from_lifesteal)
            if ev.heal_from_regen > 0:
                hp[ev.actor] = min(mx.get(ev.actor, hp.get(ev.actor, 0)), hp.get(ev.actor, 0) + ev.heal_from_regen)

            if ev.round_no != current_turn:
                current_turn = ev.round_no
                if lines:
                    lines.append("")
                lines.append(f"⚔️ **Turn {current_turn}**")

            if ev.action_type in ("regen", "energize", "passive_trigger", "charge"):
                continue
            if ev.action_type == "skip" and ev.skipped_reason == "dead":
                continue
            if ev.action != "" and "debug" in ev.action_type:
                continue

            if ev.status_damage > 0:
                lines.append(f"  {ev.actor} takes `{ev.status_damage}` {_STATUS_LABELS.get(ev.action, ev.action)} damage.")
                if ev.defeated:
                    lines.append(f"  **{ev.defeated} was defeated!**")
                continue

            if ev.action_type == "status" and ev.status_applied:
                lines.append(f"  {ev.target} is now {_STATUS_LABELS.get(ev.status_applied, ev.status_applied)}.")
                continue

            if ev.action_type == "skip" and ev.skipped_reason == "stunned":
                lines.append(f"  **{ev.actor}** is stunned!")
                continue

            if ev.action_type == "defeat" and ev.defeated:
                lines.append(f"  **{ev.defeated} was defeated!**")
                continue

            if ev.action_type == "lifesteal" and ev.heal_from_lifesteal > 0:
                lines.append(f"  {ev.actor} steals `{ev.heal_from_lifesteal}` HP.")
                continue

            if ev.action == "":
                continue

            action_name = ev.action.replace("Basic Attack", "attacks")
            tgt = ev.target or "?"
            tgt_hp = hp.get(tgt, 0)
            tgt_mx = mx.get(tgt, 0)

            if ev.damage > 0:
                crit = " **CRIT!**" if ev.is_crit else ""
                lines.append(f"**{ev.actor}** → {tgt}: `{action_name}`{crit}")
                lines.append(f"  `{ev.damage}` dmg. {tgt} HP: `{tgt_hp}/{tgt_mx}`")
            else:
                lines.append(f"**{ev.actor}** → {tgt}: `{action_name}`")

            if ev.defeated:
                lines.append(f"  **{ev.defeated} was defeated!**")

        if not lines:
            return lines
        left_alive = any(c.current_hp > 0 for c in self.left)
        right_alive = any(c.current_hp > 0 for c in self.right)
        if self.tied:
            lines.append("")
            lines.append("Battle ends in a tie.")
        elif left_alive and not right_alive:
            lines.append("")
            lines.append("🏆 **Victory!**")
        elif right_alive and not left_alive:
            lines.append("")
            lines.append("💀 **Defeat!**")
        return lines
        lines.append("")
        left_alive = any(c.current_hp > 0 for c in self.left)
        right_alive = any(c.current_hp > 0 for c in self.right)
        if self.tied:
            lines.append("⚖️ **The battle ended in a tie!**")
        elif left_alive and not right_alive:
            lines.append("🏆 **Victory!**")
        elif right_alive and not left_alive:
            lines.append("💀 **Defeat!**")
        return lines

    def _render_debug_log(self, up_to_events: list[BattleEvent], turn_ids: set[int], frame: dict[str, Any]) -> tuple[list[str], list[str]]:
        turn_log: list[str] = []
        full_log: list[str] = []
        current_round = 0
        for ev in up_to_events:
            is_turn = id(ev) in turn_ids
            if ev.round_no != current_round:
                current_round = ev.round_no
                if is_turn:
                    turn_log.append(f"=== Round {current_round} ===")
                full_log.append(f"=== Round {current_round} ===")
            if ev.action_type == "skip":
                if ev.skipped_reason == "dead":
                    if is_turn:
                        turn_log.append(f"[DEAD] {ev.actor} is already dead, cannot act.")
                    full_log.append(f"[DEAD] {ev.actor} is already dead, cannot act.")
                elif ev.skipped_reason == "stunned":
                    if is_turn:
                        turn_log.append(f"[STUN] {ev.actor} is stunned, cannot act.")
                    full_log.append(f"[STUN] {ev.actor} is stunned, cannot act.")
                if ev.defeated:
                    if is_turn:
                        turn_log.append(f"[DEFEAT] {ev.defeated} is defeated.")
                    full_log.append(f"[DEFEAT] {ev.defeated} is defeated.")
                continue
            if ev.heal_from_regen > 0:
                if is_turn:
                    turn_log.append(f"[REGEN] {ev.actor} regenerates {ev.heal_from_regen} HP.")
                full_log.append(f"[REGEN] {ev.actor} regenerates {ev.heal_from_regen} HP.")
            if ev.status_damage > 0:
                if is_turn:
                    turn_log.append(f"[STATUS_DMG] {ev.actor} suffers {ev.status_damage} {ev.action} damage.")
                full_log.append(f"[STATUS_DMG] {ev.actor} suffers {ev.status_damage} {ev.action} damage.")
            if ev.action == "":
                continue
            if is_turn:
                turn_log.append(f"[ACTION] {ev.actor} uses {ev.action} (type={ev.action_type}, is_first={ev.is_first})")
            full_log.append(f"[ACTION] {ev.actor} uses {ev.action} (type={ev.action_type}, is_first={ev.is_first})")
            if ev.mana_before != ev.mana_after:
                if is_turn:
                    turn_log.append(f"[MANA] {ev.actor}: {ev.mana_before} -> {ev.mana_after}")
                full_log.append(f"[MANA] {ev.actor}: {ev.mana_before} -> {ev.mana_after}")
            if ev.target:
                if is_turn:
                    turn_log.append(f"[TARGET] {ev.target}")
                full_log.append(f"[TARGET] {ev.target}")
            if ev.stat_used and ev.defense_used:
                if is_turn:
                    turn_log.append(f"[STATS] {ev.stat_used}={ev.stat_value} vs {ev.defense_used}={ev.defense_value}")
                full_log.append(f"[STATS] {ev.stat_used}={ev.stat_value} vs {ev.defense_used}={ev.defense_value}")
            if ev.damage > 0:
                if is_turn:
                    turn_log.append(f"[DMG] {ev.target} takes {ev.damage} damage{' CRIT' if ev.is_crit else ''}")
                full_log.append(f"[DMG] {ev.target} takes {ev.damage} damage{' CRIT' if ev.is_crit else ''}")
            if ev.healing > 0:
                if is_turn:
                    turn_log.append(f"[HEAL] {ev.actor} heals for {ev.healing}")
                full_log.append(f"[HEAL] {ev.actor} heals for {ev.healing}")
            if ev.heal_from_lifesteal > 0:
                if is_turn:
                    turn_log.append(f"[LIFESTEAL] {ev.actor} heals {ev.heal_from_lifesteal}")
                full_log.append(f"[LIFESTEAL] {ev.actor} heals {ev.heal_from_lifesteal}")
            if ev.status_applied:
                if is_turn:
                    turn_log.append(f"[STATUS] {ev.target} is {ev.status_applied}")
                full_log.append(f"[STATUS] {ev.target} is {ev.status_applied}")
            if ev.defeated:
                if is_turn:
                    turn_log.append(f"[DEFEAT] {ev.defeated} is defeated.")
                full_log.append(f"[DEFEAT] {ev.defeated} is defeated.")
        if self.debug:
            turn_log.append(f"[HP] Left: {[max(0, round(c.current_hp)) for c in self.left]}")
            turn_log.append(f"[HP] Right: {[max(0, round(c.current_hp)) for c in self.right]}")
            turn_log.append(f"[WP] Left: {[max(0, round(c.current_wp)) for c in self.left]}")
            turn_log.append(f"[WP] Right: {[max(0, round(c.current_wp)) for c in self.right]}")
            full_log.append(f"[HP] Left: {[max(0, round(c.current_hp)) for c in self.left]}")
            full_log.append(f"[HP] Right: {[max(0, round(c.current_hp)) for c in self.right]}")
            full_log.append(f"[WP] Left: {[max(0, round(c.current_wp)) for c in self.left]}")
            full_log.append(f"[WP] Right: {[max(0, round(c.current_wp)) for c in self.right]}")
        self._append_result_block(full_log, frame)
        if frame.get("tied") or frame.get("finished"):
            self._append_result_block(turn_log, frame)
        return turn_log, full_log

    def _append_result_block(self, log_lines: list[str], last: dict[str, Any]) -> None:
        if last["tied"]:
            log_lines.append("")
            log_lines.append("Battle Over")
            log_lines.append("")
            log_lines.append(f"Battle ends in a tie.")
            log_lines.append(f"Reason: both teams still had surviving creatures after {self.max_turns} rounds.")
        elif last["finished"]:
            winner_side = "Left" if last["left_won"] else "Right"
            loser_side = "Right" if last["left_won"] else "Left"
            log_lines.append("")
            log_lines.append("Battle Over")
            log_lines.append("")
            log_lines.append(f"{winner_side} team wins.")
            log_lines.append(f"Reason: all {loser_side.lower()}-side creatures were defeated in Round {last['turn']}.")

    def _get_speed(self, name: str) -> int:
        for c in self.left + self.right:
            if c.name == name:
                return c.speed
        return 0

    def _living(self, team: list[Creature]) -> list[Creature]:
        return [c for c in team if c.alive]

    def _turn_start(self, turn: int) -> None:
        for creature in self.left + self.right:
            if not creature.alive:
                continue
            creature.current_wp = min(creature.max_wp, creature.current_wp + max(12, round(creature.max_wp * 0.06)))
            for passive in (creature.weapon.passives if creature.weapon else []):
                if passive.key == "regeneration":
                    heal_pct = max(5, min(10, passive.value)) / 100.0
                    heal = max(1, round(creature.max_hp * heal_pct))
                    old = creature.current_hp
                    creature.current_hp = min(creature.max_hp, creature.current_hp + heal)
                    if creature.current_hp > old:
                        self.events.append(BattleEvent(
                            round_no=turn, actor=creature.name, actor_side=creature.side,
                            action="regen", action_type="regen", heal_from_regen=creature.current_hp - old,
                        ))
                elif passive.key == "energize":
                    mana_restore = max(20, min(40, passive.value))
                    old_wp = creature.current_wp
                    creature.current_wp = min(creature.max_wp, creature.current_wp + mana_restore)
                    if creature.current_wp > old_wp:
                        self.events.append(BattleEvent(
                            round_no=turn, actor=creature.name, actor_side=creature.side,
                            action="energize", action_type="regen",
                        ))
            for key, status in list(creature.statuses.items()):
                stacks = max(1, int(status.get("stacks", 1)))
                if key == "bleed":
                    damage = max(1, round(creature.max_hp * 0.025 * stacks))
                    creature.current_hp -= damage
                    self.events.append(BattleEvent(
                        round_no=turn, actor=creature.name, actor_side=creature.side,
                        action="bleed", action_type="status_damage", status_damage=damage,
                    ))
                elif key == "burn":
                    damage = max(1, round(creature.max_hp * 0.030 * stacks))
                    creature.current_hp -= damage
                    self.events.append(BattleEvent(
                        round_no=turn, actor=creature.name, actor_side=creature.side,
                        action="burn", action_type="status_damage", status_damage=damage,
                    ))
                elif key == "poison":
                    damage = max(1, round(creature.max_hp * 0.022 * stacks))
                    creature.current_hp -= damage
                    self.events.append(BattleEvent(
                        round_no=turn, actor=creature.name, actor_side=creature.side,
                        action="poison", action_type="status_damage", status_damage=damage,
                    ))
                elif key == "doom_bell":
                    if status.get("duration", 0) <= 1:
                        missing_hp = creature.max_hp - creature.current_hp
                        doom_pct = max(12, min(25, int(status.get("power", 15)))) / 100.0
                        doom_damage = max(1, round(missing_hp * doom_pct))
                        creature.current_hp -= doom_damage
                        self.events.append(BattleEvent(
                            round_no=turn, actor=creature.name, actor_side=creature.side,
                            action="doom_bell", action_type="status_damage", status_damage=doom_damage,
                        ))
        for creature in self.left + self.right:
            if creature.current_hp <= 0:
                self._handle_death(creature, self.left if creature.side == "left" else self.right)

    def _turn_end(self) -> None:
        for creature in self.left + self.right:
            creature.taunting = False
            for key in list(creature.statuses.keys()):
                creature.statuses[key]["duration"] = int(creature.statuses[key].get("duration", 1)) - 1
                if creature.statuses[key]["duration"] <= 0:
                    del creature.statuses[key]

    def _act(self, turn: int, actor: Creature, allies: list[Creature], enemies: list[Creature], *, is_first: bool = False) -> None:
        speed = actor.speed
        if "stun" in actor.statuses:
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action="", action_type="skip", skipped_reason="stunned",
                is_first=is_first,
            ))
            return

        weapon = actor.weapon
        ability = None
        cost = 0
        if weapon:
            ability = weapon.activeAbility
            cost = ability.wp_cost(weapon.qualityPercent)
            if ability.mode in ("passive_only", "rune_empowerment"):
                self._act_ability(turn, actor, allies, enemies, weapon, ability, actor.current_wp, is_first)
                self._phase_remove_dead(turn)
                return
            if actor.current_wp >= cost:
                old_wp = actor.current_wp
                actor.current_wp -= cost
                self._act_ability(turn, actor, allies, enemies, weapon, ability, old_wp, is_first)
                self._phase_remove_dead(turn)
                return

        if self.debug:
            reason = f"(cost {cost}, has {actor.current_wp})" if weapon else "(no weapon)"
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=f"Basic Attack {reason}", action_type="basic_attack_debug",
                is_first=is_first,
            ))

        actor.current_wp = min(actor.max_wp, actor.current_wp + max(10, round(actor.max_wp * 0.04)))
        target = self._pick_target(enemies)
        weapon_bonus = 0
        if actor.weapon and isinstance(actor.weapon.statRolls, dict):
            weapon_bonus = int(actor.weapon.statRolls.get("base_str", 0))
        if actor.weapon and actor.weapon.activeAbility.mode == "rune_empowerment":
            hybrid_stat = round(actor.strength * 0.6 + actor.magic * 0.6)
            damage, is_crit = self._deal_damage(actor, target, hybrid_stat, "true", weapon_bonus=weapon_bonus)
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action="Basic Attack (Rune)", target=target.name,
                action_type="damage", stat_used="HYB", stat_value=hybrid_stat,
                defense_used="NONE", defense_value=0,
                damage=damage, is_crit=is_crit, is_first=is_first,
            ))
        else:
            damage, is_crit = self._deal_damage(actor, target, actor.strength, "physical", weapon_bonus=weapon_bonus)
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action="Basic Attack", target=target.name,
                action_type="damage", stat_used="STR", stat_value=actor.strength,
                defense_used="DEF", defense_value=round(target.pr * 100),
                damage=damage, is_crit=is_crit, is_first=is_first,
            ))
        for passive in (target.weapon.passives if target.weapon else []):
            if passive.key == "thorns" and actor.alive:
                reflected = max(1, round(damage * min(0.35, passive.value / 100.0)))
                actor.current_hp = max(0, actor.current_hp - reflected)
            elif passive.key == "adaptation":
                gain = passive.value / 1000.0
                target.pr = min(0.80, target.pr + gain)
                target.mr = min(0.80, target.mr + gain)
        self._after_hit(actor, target, damage, turn)
        self._phase_remove_dead(turn)

    def _act_ability(
        self, turn: int, actor: Creature, allies: list[Creature], enemies: list[Creature],
        weapon: Weapon, ability: Ability, old_wp: int, is_first: bool,
    ) -> None:
        q = _quality(weapon.qualityPercent)
        mult = ability.multiplier(weapon.qualityPercent)

        if ability.mode == "passive_only":
            passive_triggered = 0
            for passive in weapon.passives:
                chance = passive.value / 100.0
                if random.random() < chance:
                    passive_triggered += 1
            if passive_triggered >= 2:
                mana_restore = max(1, round(actor.max_wp * (0.05 + q * 0.05)))
                actor.current_wp = min(actor.max_wp, actor.current_wp + mana_restore)
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, action_type="passive_trigger",
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            return

        if ability.mode == "rune_empowerment":
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, action_type="passive_trigger",
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            return

        if ability.mode == "execute":
            target = self._pick_target(enemies)
            raw_stat = actor.strength
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            hp_pct = target.current_hp / max(1, target.max_hp)
            if hp_pct < 0.35:
                bonus_pct = 0.15 + q * 0.20
                bonus = max(1, int(damage * bonus_pct))
                target.current_hp = max(0, target.current_hp - bonus)
                damage += bonus
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="STR", stat_value=raw_stat,
                defense_used="DEF", defense_value=round(target.pr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "double_strike":
            target = self._pick_target(enemies)
            raw_stat = actor.strength
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="STR", stat_value=raw_stat,
                defense_used="DEF", defense_value=round(target.pr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            self._after_hit(actor, target, damage, turn)
            if actor.speed > target.speed and target.alive:
                double_chance = 0.20 + q * 0.20
                if random.random() < double_chance:
                    mult2 = 0.35 + q * 0.20
                    damage2, is_crit2 = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult2)
                    self.events.append(BattleEvent(
                        round_no=turn, actor=actor.name, actor_side=actor.side,
                        action=f"{ability.name} (double)", target=target.name,
                        action_type="damage", stat_used="STR", stat_value=raw_stat,
                        defense_used="DEF", defense_value=round(target.pr * 100),
                        damage=damage2, is_crit=is_crit2,
                        is_first=is_first,
                    ))
                    self._after_hit(actor, target, damage2, turn)
            return

        if ability.mode == "cleave":
            raw_stat = actor.strength
            for enemy in list(enemies):
                if not enemy.alive:
                    continue
                damage, is_crit = self._deal_damage(actor, enemy, raw_stat, ability.damage_type, multiplier=mult)
                if "bleed" in enemy.statuses:
                    bonus_pct = 0.20 + q * 0.25
                    bonus = max(1, int(damage * bonus_pct))
                    enemy.current_hp = max(0, enemy.current_hp - bonus)
                    damage += bonus
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=ability.name, target=enemy.name,
                    action_type="damage", stat_used="STR", stat_value=raw_stat,
                    defense_used="DEF", defense_value=round(enemy.pr * 100),
                    damage=damage, is_crit=is_crit,
                    mana_before=old_wp, mana_after=actor.current_wp,
                    is_first=is_first,
                ))
                self._after_hit(actor, enemy, damage, turn)
            return

        if ability.mode == "bleed_apply":
            target = self._pick_target(enemies)
            raw_stat = actor.strength
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="STR", stat_value=raw_stat,
                defense_used="DEF", defense_value=round(target.pr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            if "bleed" in target.statuses:
                bleed_dmg = max(1, round(target.max_hp * (0.15 + q * 0.20)))
                target.current_hp = max(0, target.current_hp - bleed_dmg)
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action="", target=target.name,
                    action_type="status_damage", status_damage=bleed_dmg,
                ))
            target.add_status("bleed", duration=3, order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action="", target=target.name,
                action_type="status", status_applied="bleed",
            ))
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "charge":
            charge_key = f"_charge_{actor.id}"
            if hasattr(actor, charge_key):
                delattr(actor, charge_key)
                target = self._pick_target(enemies)
                raw_stat = actor.strength
                damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
                target.add_status("exposed", duration=2, power=max(1, round(10 + q * 20)), order=self._next_status_order())
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=ability.name, target=target.name,
                    action_type="damage", stat_used="STR", stat_value=raw_stat,
                    defense_used="DEF", defense_value=round(target.pr * 100),
                    damage=damage, is_crit=is_crit,
                    mana_before=old_wp, mana_after=actor.current_wp,
                    is_first=is_first,
                ))
                self._after_hit(actor, target, damage, turn)
            else:
                setattr(actor, charge_key, True)
                charge_cost = ability.wp_cost(weapon.qualityPercent)
                actor.current_wp = min(actor.max_wp, actor.current_wp + charge_cost)
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=f"{ability.name} (loading)", action_type="charge",
                    mana_before=old_wp, mana_after=actor.current_wp,
                    is_first=is_first,
                ))
            return

        if ability.mode == "burn_detonate":
            target = self._pick_target(enemies)
            raw_stat = actor.magic
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="MAG", stat_value=raw_stat,
                defense_used="RES", defense_value=round(target.mr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            if "burn" in target.statuses and target.alive:
                detonate_mult = 0.90 + q * 0.40
                detonate_dmg, det_crit = self._deal_damage(actor, target, raw_stat, "magical", multiplier=detonate_mult)
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=f"{ability.name} (detonate)", target=target.name,
                    action_type="damage", stat_used="MAG", stat_value=raw_stat,
                    defense_used="RES", defense_value=round(target.mr * 100),
                    damage=detonate_dmg, is_crit=det_crit,
                    is_first=is_first,
                ))
            target.add_status("burn", duration=3, order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action="", target=target.name,
                action_type="status", status_applied="burn",
            ))
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "cleanse_ward":
            ally_target = None
            max_debuffs = 0
            for ally in allies:
                debuff_count = sum(1 for k in ally.statuses if k not in {"shield", "attack_up", "defense_up", "taunt", "regeneration", "sacred_ward"})
                if debuff_count > max_debuffs:
                    max_debuffs = debuff_count
                    ally_target = ally
            if ally_target:
                removed = ally_target.remove_oldest_debuff()
                heal = max(1, round(actor.magic * mult))
                ally_target.current_hp = min(ally_target.max_hp, ally_target.current_hp + heal)
                ally_target.add_status("sacred_ward", duration=2, order=self._next_status_order())
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=ability.name, target=ally_target.name,
                    action_type="heal", healing=heal,
                    mana_before=old_wp, mana_after=actor.current_wp,
                    is_first=is_first,
                ))
            else:
                lowest = min(allies, key=lambda a: a.current_hp / max(1, a.max_hp))
                heal = max(1, round(actor.magic * mult))
                lowest.current_hp = min(lowest.max_hp, lowest.current_hp + heal)
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=ability.name, target=lowest.name,
                    action_type="heal", healing=heal,
                    mana_before=old_wp, mana_after=actor.current_wp,
                    is_first=is_first,
                ))
            return

        if ability.mode == "taunt_shield":
            actor.taunting = True
            actor.add_status("shield", duration=2, power=1, order=self._next_status_order())
            hp_pct = actor.current_hp / max(1, actor.max_hp)
            if hp_pct < 0.40:
                shield_val = max(1, round(actor.stat_value("DEF") * (0.50 + q * 0.50)))
                actor.add_status("shield", duration=2, power=shield_val, order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=actor.name,
                action_type="guard",
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            return

        if ability.mode == "stagger_stun":
            target = self._pick_target(enemies)
            raw_stat = actor.strength
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="STR", stat_value=raw_stat,
                defense_used="DEF", defense_value=round(target.pr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            if "stagger" in target.statuses:
                target.add_status("stun", duration=1, order=self._next_status_order())
                del target.statuses["stagger"]
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action="", target=target.name,
                    action_type="status", status_applied="stun",
                ))
            else:
                target.add_status("stagger", duration=2, order=self._next_status_order())
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "mortality":
            target = self._pick_target(enemies)
            raw_stat = actor.strength
            target_hp_before = target.current_hp
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            target.add_status("mortality", duration=2, power=max(1, round(45 + q * 30)), order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="STR", stat_value=raw_stat,
                defense_used="DEF", defense_value=round(target.pr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            if target.current_hp <= 0 and target_hp_before > 0:
                hp_heal = max(1, round(actor.max_hp * (0.10 + q * 0.15)))
                wp_heal = max(1, round(actor.max_wp * (0.10 + q * 0.15)))
                actor.current_hp = min(actor.max_hp, actor.current_hp + hp_heal)
                actor.current_wp = min(actor.max_wp, actor.current_wp + wp_heal)
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "tether":
            actor.add_status("tether", duration=2, power=max(1, round(25 + q * 25)), order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=actor.name,
                action_type="guard",
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            return

        if ability.mode == "poison_spread":
            target = self._pick_target(enemies)
            raw_stat = actor.magic
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            target.add_status("poison", duration=3, order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="MAG", stat_value=raw_stat,
                defense_used="RES", defense_value=round(target.mr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action="", target=target.name,
                action_type="status", status_applied="poison",
            ))
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "team_buff":
            for ally in allies:
                ally.add_status("black_sun_march", duration=2, power=max(1, round(15 + q * 10)), order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, action_type="buff",
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            return

        if ability.mode == "force_attack":
            hp_cost = max(1, round(actor.max_hp * (0.10 + q * 0.10)))
            actor.current_hp = max(1, actor.current_hp - hp_cost)
            living_enemies = [e for e in enemies if e.alive]
            if len(living_enemies) > 1:
                target = random.choice(living_enemies)
                allies_of_target = [e for e in living_enemies if e is not target]
                if allies_of_target:
                    friendly_target = random.choice(allies_of_target)
                    fake_mult = 0.35 + q * 0.20
                    damage, is_crit = self._deal_damage(target, friendly_target, target.strength, "physical", multiplier=fake_mult)
                    self.events.append(BattleEvent(
                        round_no=turn, actor=actor.name, actor_side=actor.side,
                        action=ability.name, target=target.name,
                        action_type="damage", stat_used="MAG", stat_value=actor.magic,
                        defense_used="DEF", defense_value=round(friendly_target.pr * 100),
                        damage=damage, is_crit=is_crit,
                        mana_before=old_wp, mana_after=actor.current_wp,
                        is_first=is_first,
                    ))
            else:
                target = self._pick_target(enemies)
                raw_stat = actor.magic
                big_mult = 1.50 + q * 0.60
                damage, is_crit = self._deal_damage(actor, target, raw_stat, "magical", multiplier=big_mult)
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=ability.name, target=target.name,
                    action_type="damage", stat_used="MAG", stat_value=raw_stat,
                    defense_used="RES", defense_value=round(target.mr * 100),
                    damage=damage, is_crit=is_crit,
                    mana_before=old_wp, mana_after=actor.current_wp,
                    is_first=is_first,
                ))
                self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "stack_consumption":
            target = self._pick_target(enemies)
            raw_stat = max(actor.strength, actor.magic)
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="STR", stat_value=raw_stat,
                defense_used="DEF", defense_value=round(target.pr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "mana_drain":
            target = self._pick_target(enemies)
            raw_stat = actor.magic
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            stolen = max(1, round(target.current_wp * (0.15 + q * 0.20)))
            stolen = min(stolen, target.current_wp)
            target.current_wp = max(0, target.current_wp - stolen)
            actor.current_wp = min(actor.max_wp, actor.current_wp + stolen)
            if target.current_wp / max(1, target.max_wp) < 0.20:
                bonus_pct = 0.50 + q * 0.40
                bonus = max(1, int(damage * bonus_pct))
                target.current_hp = max(0, target.current_hp - bonus)
                damage += bonus
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="MAG", stat_value=raw_stat,
                defense_used="RES", defense_value=round(target.mr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "reflect_debuff":
            actor.add_status("mirror_ward", duration=2, power=max(1, round(60 + q * 40)), order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=actor.name,
                action_type="guard",
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            return

        if ability.mode == "doom_bell":
            target = self._pick_target(enemies)
            raw_stat = actor.strength
            damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
            target.add_status("doom_bell", duration=3, power=max(1, round(12 + q * 13)), order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="STR", stat_value=raw_stat,
                defense_used="DEF", defense_value=round(target.pr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "heal":
            damaged = [ally for ally in allies if ally.current_hp < ally.max_hp]
            if damaged:
                target = min(damaged, key=lambda ally: ally.current_hp / max(1, ally.max_hp))
                heal = max(1, round(actor.stat_value(ability.scale_stat) * mult))
                target.current_hp = min(target.max_hp, target.current_hp + heal)
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=ability.name, target=target.name,
                    action_type="heal", healing=heal,
                    mana_before=old_wp, mana_after=actor.current_wp,
                    is_first=is_first,
                ))
                return
            target = self._pick_target(enemies)
            fallback_mult = 0.70 + 0.35 * q
            damage, is_crit = self._deal_damage(actor, target, actor.magic, "magical", multiplier=fallback_mult)
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action=ability.name, target=target.name,
                action_type="damage", stat_used="MAG", stat_value=actor.magic,
                defense_used="RES", defense_value=round(target.mr * 100),
                damage=damage, is_crit=is_crit,
                mana_before=old_wp, mana_after=actor.current_wp,
                is_first=is_first,
            ))
            self._after_hit(actor, target, damage, turn)
            return

        if ability.mode == "purity":
            enemy_target = next((enemy for enemy in enemies if enemy.remove_oldest_buff()), None)
            ally_target = next((ally for ally in allies if ally.remove_oldest_debuff()), None)
            if enemy_target:
                damage, is_crit = self._deal_damage(actor, enemy_target, actor.magic, "magical", multiplier=mult)
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=ability.name, target=enemy_target.name,
                    action_type="damage", stat_used="MAG", stat_value=actor.magic,
                    defense_used="RES", defense_value=round(enemy_target.mr * 100),
                    damage=damage, is_crit=is_crit,
                    mana_before=old_wp, mana_after=actor.current_wp,
                    is_first=is_first,
                ))
            if ally_target:
                heal_multiplier = 0.50 + (1.00 - 0.50) * q
                heal = max(1, round(actor.strength * heal_multiplier))
                ally_target.current_hp = min(ally_target.max_hp, ally_target.current_hp + heal)
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=ability.name, target=ally_target.name,
                    action_type="heal", healing=heal,
                    is_first=is_first,
                ))
            if not enemy_target and not ally_target:
                self.events.append(BattleEvent(
                    round_no=turn, actor=actor.name, actor_side=actor.side,
                    action=ability.name, action_type="noop",
                    mana_before=old_wp, mana_after=actor.current_wp,
                    is_first=is_first,
                ))
            return

        target = self._pick_target(enemies)
        if ability.scale_stat == "STR":
            raw_stat = actor.strength
            def_value = round(target.pr * 100)
            stat_label = "STR"
            def_label = "DEF"
        elif ability.scale_stat == "HP":
            raw_stat = actor.max_hp
            def_value = round(target.pr * 100)
            stat_label = "HP"
            def_label = "DEF"
        else:
            raw_stat = actor.magic
            def_value = round(target.mr * 100)
            stat_label = "MAG"
            def_label = "RES"
        damage, is_crit = self._deal_damage(actor, target, raw_stat, ability.damage_type, multiplier=mult)
        self.events.append(BattleEvent(
            round_no=turn, actor=actor.name, actor_side=actor.side,
            action=ability.name, target=target.name,
            action_type="damage", stat_used=stat_label, stat_value=raw_stat,
            defense_used=def_label, defense_value=def_value,
            damage=damage, is_crit=is_crit,
            mana_before=old_wp, mana_after=actor.current_wp,
            is_first=is_first,
        ))
        if ability.mode == "guard":
            actor.taunting = True
            actor.add_status("shield", duration=2, power=1, order=self._next_status_order())
        if ability.status and random.random() < 0.28 + q * 0.18:
            target.add_status(ability.status, duration=2 if ability.status == "stun" else 3, order=self._next_status_order())
            self.events.append(BattleEvent(
                round_no=turn, actor=actor.name, actor_side=actor.side,
                action="", target=target.name,
                action_type="status", status_applied=ability.status,
            ))
        self._after_hit(actor, target, damage, turn)

    def _pick_target(self, enemies: list[Creature]) -> Creature:
        taunts = [e for e in enemies if e.taunting]
        return random.choice(taunts or enemies)

    def _physical_damage(self, attacker: Creature, defender: Creature, multiplier: float = 1.0, weapon_bonus: int = 0) -> int:
        atk = attacker.strength + weapon_bonus
        defense = round(defender.pr * 100)
        return max(1, int((atk * 1.25 - defense * 0.45) * multiplier))

    def _magical_damage(self, attacker: Creature, defender: Creature, multiplier: float = 1.0, weapon_bonus: int = 0) -> int:
        atk = attacker.magic + weapon_bonus
        res = round(defender.mr * 100)
        return max(1, int((atk * 1.25 - res * 0.45) * multiplier))

    def _deal_damage(self, attacker: Creature, target: Creature, stat_value: int, damage_type: str, *, multiplier: float = 1.0, weapon_bonus: int = 0) -> tuple[int, bool]:
        if damage_type == "physical":
            damage = self._physical_damage(attacker, target, multiplier, weapon_bonus)
        elif damage_type == "magical":
            damage = self._magical_damage(attacker, target, multiplier, weapon_bonus)
        else:
            damage = max(1, int((stat_value + weapon_bonus) * multiplier))
        if "fear" in attacker.statuses:
            damage = max(1, int(damage * 0.75))
        if "curse" in attacker.statuses:
            damage = max(1, int(damage * 0.80))
        if "black_sun_march" in attacker.statuses:
            march_power = int(attacker.statuses["black_sun_march"].get("power", 15))
            damage = max(1, int(damage * (1.0 + march_power / 100.0)))
        if "exposed" in target.statuses:
            exposed_power = int(target.statuses["exposed"].get("power", 15))
            damage = max(1, int(damage * (1.0 + exposed_power / 100.0)))
        is_crit = random.random() < min(1.0, attacker.crit / 100.0)
        if is_crit:
            crit_mult = 1.5 + attacker.crit_damage_bonus
            damage = max(1, int(damage * crit_mult))
        if "shield" in target.statuses:
            damage = max(1, int(damage * 0.70))
        if "tether" in target.statuses:
            tether_power = int(target.statuses["tether"].get("power", 25))
            absorbed = max(1, int(damage * tether_power / 100.0))
            damage = max(1, damage - absorbed)
        for passive in (target.weapon.passives if target.weapon else []):
            if passive.key == "safeguard" and damage > target.max_hp * 0.20:
                damage = max(1, int(damage * (1.0 - min(0.40, passive.value / 100.0))))
        target.current_hp = max(0, target.current_hp - damage)
        return damage, is_crit

    def _after_hit(self, attacker: Creature, target: Creature, damage: int, turn: int) -> None:
        if not attacker.weapon:
            return
        for passive in attacker.weapon.passives:
            chance = passive.value / 100.0
            if passive.key in {"bleed", "burn", "poison", "stun"} and random.random() < chance:
                target.add_status(passive.key, duration=2 if passive.key == "stun" else 3, order=self._next_status_order())
                self.events.append(BattleEvent(
                    round_no=turn, actor=attacker.name, actor_side=attacker.side,
                    action="", target=target.name,
                    action_type="status", status_applied=passive.key,
                ))
            elif passive.key == "shield" and random.random() < chance:
                attacker.add_status("shield", duration=2, order=self._next_status_order())
                self.events.append(BattleEvent(
                    round_no=turn, actor=attacker.name, actor_side=attacker.side,
                    action="", target=attacker.name,
                    action_type="status", status_applied="shield",
                ))
            elif passive.key in {"heal", "life_steal"} and damage > 0:
                heal = max(1, round(damage * min(0.35, passive.value / 100.0)))
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal)
                self.events.append(BattleEvent(
                    round_no=turn, actor=attacker.name, actor_side=attacker.side,
                    action="", target=attacker.name,
                    action_type="lifesteal", heal_from_lifesteal=heal,
                ))
            elif passive.key == "mana_tap" and damage > 0:
                mana_restore = max(1, round(damage * passive.value / 100.0))
                attacker.current_wp = min(attacker.max_wp, attacker.current_wp + mana_restore)
            elif passive.key == "fear" and random.random() < chance:
                target.add_status("fear", duration=2, order=self._next_status_order())
                self.events.append(BattleEvent(
                    round_no=turn, actor=attacker.name, actor_side=attacker.side,
                    action="", target=target.name,
                    action_type="status", status_applied="fear",
                ))

    def _next_status_order(self) -> int:
        self._status_order += 1
        return self._status_order

    def _phase_remove_dead(self, turn: int) -> None:
        for creature in self.left + self.right:
            if creature.current_hp <= 0 and creature.alive:
                creature.current_hp = 0
                self.events.append(BattleEvent(
                    round_no=turn, actor=creature.name, actor_side=creature.side,
                    action="", target=creature.name,
                    action_type="defeat", defeated=creature.name,
                ))
                self._handle_death(creature, self.left if creature.side == "left" else self.right)

    def _check_deaths(self, turn_log: list[str]) -> None:
        pass

    def _handle_death(self, dead: Creature, allies: list[Creature]) -> None:
        if dead.sacrifice_triggered or dead.current_hp > 0 or not dead.weapon:
            return
        for passive in dead.weapon.passives:
            if passive.key != "sacrifice":
                continue
            bonus = min(0.50, max(0.25, passive.value / 100.0))
            hp_gain = max(1, round(dead.max_hp * bonus))
            wp_gain = max(1, round(dead.max_wp * bonus))
            boosted = 0
            for ally in allies:
                if ally is dead or not ally.alive:
                    continue
                ally.max_hp += hp_gain
                ally.current_hp = min(ally.max_hp, ally.current_hp + hp_gain)
                ally.max_wp += wp_gain
                ally.current_wp = min(ally.max_wp, ally.current_wp + wp_gain)
                boosted += 1
            if boosted:
                self.events.append(BattleEvent(
                    round_no=0, actor=dead.name, actor_side=dead.side,
                    action="Sacrifice", target=dead.name,
                    action_type="sacrifice", healing=hp_gain,
                ))
            dead.sacrifice_triggered = True
            break

    def _frame(self, turn: int, *, finished: bool | None = None) -> dict[str, Any]:
        left_total = sum(max(0, c.current_hp) for c in self.left)
        right_total = sum(max(0, c.current_hp) for c in self.right)
        left_any = any(c.current_hp > 0 for c in self.left)
        right_any = any(c.current_hp > 0 for c in self.right)
        if self.tied:
            left_won = False
            done = True
        elif finished is not None:
            done = finished
            left_won = finished and left_any and not right_any
        elif left_any and not right_any:
            done = True
            left_won = True
        elif right_any and not left_any:
            done = True
            left_won = False
        else:
            done = False
            left_won = left_total >= right_total
        return {
            "turn": turn,
            "left_won": left_won,
            "log": [],
            "turn_log": [],
            "full_log": [],
            "left_hp": [max(0, round(c.current_hp)) for c in self.left],
            "right_hp": [max(0, round(c.current_hp)) for c in self.right],
            "left_wp": [max(0, round(c.current_wp)) for c in self.left],
            "right_wp": [max(0, round(c.current_wp)) for c in self.right],
            "finished": done,
            "tied": self.tied,
        }


# -- Display stats (unchanged) --

def compute_display_stats(row: Any) -> dict[str, int]:
    name = str(_row_get(row, "name", "") or "")
    rarity = str(_row_get(row, "rarity", "Common") or "Common")
    level = max(1, _int(_row_get(row, "level", 1), 1))
    template = _TEMPLATES.get(normalize_key(_template_name(name)))
    rarity_mult = float(RARITY_BY_NAME.get(rarity, RARITY_BY_NAME["Common"]).stat_multiplier)
    if template:
        s7 = derive_7stats(template)
        hp_stat = max(1, round(s7["hp"] * rarity_mult))
        str_stat = max(1, round(s7["str"] * rarity_mult))
        pr_stat = max(1, round(s7["pr"] * rarity_mult))
        wp_stat = max(1, round(s7["wp"] * rarity_mult))
        mag_stat = max(1, round(s7["mag"] * rarity_mult))
        mr_stat = max(1, round(s7["mr"] * rarity_mult))
        speed = max(1, round(s7["spd"] * rarity_mult))
    else:
        hp = max(1, _int(_row_get(row, "hp", 600), 600))
        attack = max(1, _int(_row_get(row, "attack", 120), 120))
        defense = max(1, _int(_row_get(row, "defense", 30), 30))
        mana = max(1, _int(_row_get(row, "mana", 200), 200))
        speed = max(1, _int(_row_get(row, "speed", 10), 10))
        hp_stat = max(1, round(max(0, hp - 500) / (2 * level)))
        str_stat = max(1, round(max(0, attack - 100) / level))
        pr_stat = max(1, round(defense / max(1, level)))
        wp_stat = max(1, round(max(0, mana - 500) / (2 * level))) if mana > 500 else max(1, round((hp_stat + pr_stat) / 2))
        mag_stat = max(1, round(speed + str_stat * 0.4))
        mr_stat = max(1, round((pr_stat + speed) / 2))
    max_hp = 2 * hp_stat * level + 500
    strength = str_stat * level + 100
    max_wp = 2 * wp_stat * level + 500
    magic = mag_stat * level + 100
    pr = 0.8 * ((25 + 2 * pr_stat * level) / (125 + 2 * pr_stat * level))
    mr = 0.8 * ((25 + 2 * mr_stat * level) / (125 + 2 * mr_stat * level))
    return {
        "HP": max_hp,
        "STR": strength,
        "MAG": magic,
        "MANA": max_wp,
        "DEF": round(pr * 100),
        "RES": round(mr * 100),
        "SPD": max(1, speed),
        "Crit": _int(_row_get(row, "crit", 5), 5),
    }
