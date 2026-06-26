# ruff: noqa: E402
from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.battle_card_renderer import BattleCardRenderer  # noqa: E402
from core.battle_engine import compute_display_stats  # noqa: E402
from core.cards import (
    render_arena_card,
    render_autohunt_card,
    render_buffs_card,
    render_collection_card,
    render_crate_open_card,
    render_creature_card,
    render_profile_card,
    render_shop_card,
    render_team_card,
    render_weapon_detail_card,
    render_weapons_card,
)  # noqa: E402
from core.hunt_card_renderer import HuntCardRenderer  # noqa: E402
from core.rpg_data import CHARMS, CREATURES, RARITIES, SIGILS, derive_7stats, determine_role  # noqa: E402

OUT_DIR = Path("tmp/card_previews")
REQUESTED_PREVIEWS = (
    "weapon_vault.png",
    "hunt_result_6.png",
    "hunt_result_15.png",
    "crate_shop.png",
    "weapon_detail.png",
    "battle_card.png",
    "bestiary_page.png",
    "profile_card.png",
)


def write(name: str, data: BytesIO) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data.seek(0)
    (OUT_DIR / name).write_bytes(data.read())


def alias(src: str, dst: str) -> None:
    source = OUT_DIR / src
    if source.exists():
        (OUT_DIR / dst).write_bytes(source.read_bytes())


def _sheet_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    for name in ("segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_contact_sheet(names: tuple[str, ...] = REQUESTED_PREVIEWS, *, output_name: str = "all_cards_contact_sheet.png", title: str = "Abyssia Card Preview Contact Sheet") -> None:
    images: list[tuple[str, Image.Image]] = []
    for name in names:
        path = OUT_DIR / name
        if not path.exists():
            continue
        image = Image.open(path).convert("RGB")
        image.thumbnail((360, 240), Image.Resampling.LANCZOS)
        images.append((name, image))
    if not images:
        return
    cols = 2
    cell_w = 410
    cell_h = 306
    title_h = 64
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w + 28, rows * cell_h + title_h + 28), (10, 8, 16))
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 18), title, font=_sheet_font(28, bold=True), fill=(236, 229, 218))
    draw.rectangle((0, title_h - 4, sheet.width, title_h), fill=(238, 196, 82))
    for idx, (name, image) in enumerate(images):
        col = idx % cols
        row = idx // cols
        x = 14 + col * cell_w
        y = title_h + 14 + row * cell_h
        draw.rounded_rectangle((x, y, x + cell_w - 14, y + cell_h - 12), radius=8, fill=(23, 19, 32), outline=(62, 53, 78))
        px = x + (cell_w - 14 - image.width) // 2
        py = y + 18
        sheet.paste(image, (px, py))
        draw.text((x + 18, y + cell_h - 48), name, font=_sheet_font(17, bold=True), fill=(236, 229, 218))
    sheet.save(OUT_DIR / output_name, "PNG", optimize=True)


def by_rarity() -> dict[str, Any]:
    found: dict[str, Any] = {}
    for creature in CREATURES:
        found.setdefault(creature.rarity, creature)
    return found


def pick_creature(rarity: str, fallback_index: int = 0) -> Any:
    found = by_rarity()
    return found.get(rarity) or CREATURES[fallback_index % len(CREATURES)]


def hunt_monsters(count: int) -> list[dict[str, Any]]:
    rarity_order = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic", "Ancient", "Divine", "Eldritch"]
    monsters: list[dict[str, Any]] = []
    for idx in range(count):
        rarity = rarity_order[idx % len(rarity_order)]
        creature = pick_creature(rarity, idx)
        monsters.append(
            {
                "name": creature.name if idx != count - 1 else "A Very Long Abyssal Monster Name That Must Fit",
                "rarity": creature.rarity,
                "value": 1_250 + idx * 875,
                "collection_status": "NEW DISCOVERY" if idx % 4 == 0 else "DUPLICATE",
            }
        )
    return monsters


def sample_hunt_data(count: int) -> dict[str, Any]:
    return {
        "hunter_name": "Nyx",
        "hunter_rank": "Voidbound Hunter",
        "hunt_streak": 42,
        "zone_name": "Void Realm",
        "zone_key": "void_realm",
        "monsters": hunt_monsters(count),
        "total_souls": 88_888,
        "rewards": [
            {"label": "Souls", "amount": 88_888, "icon_key": "souls", "kind": "currency", "color": (238, 196, 82)},
            {"label": "XP", "amount": 12_450, "icon_key": "profile", "kind": "ui", "color": (80, 212, 126)},
            {"label": "Lootbox [2/3]", "amount": 1, "icon_key": "cache", "kind": "crate", "color": (58, 218, 232)},
        ],
        "special_drop": {"type": "crate", "key": "relic", "name": "Eldritch Relic", "rarity": "Legendary"},
    }


def sample_weapon(idx: int = 1, *, missing_icon: bool = False, zero_stats: bool = False) -> dict[str, Any]:
    wtype = "missing_icon_key" if missing_icon else ("lantern" if idx % 2 else "sword")
    return {
        "id": 1000 + idx,
        "user_id": 1,
        "name": "Lantern" if not missing_icon else "Missing Icon Regression Relic",
        "rarity": "Legendary",
        "weapon_type": wtype,
        "quality": "Legendary",
        "quality_pct": 91 if idx == 1 else 47,
        "mana_cost": 217,
        "wear": "Pristine",
        "attack_bonus": 0 if zero_stats else 44,
        "defense_bonus": 0 if zero_stats else 18,
        "passive": json.dumps(
            {
                "key": "life_steal",
                "name": "Lifesteal",
                "roll": 83,
                "chance": 31,
                "extra": [{"key": "mana_tap", "name": "Mana Tap", "roll": 70, "chance": 24}],
            }
        ),
        "affixes": json.dumps(
            [
                {"key": "crit", "fmt": "+18% critical force"},
                {"key": "soul_gain", "fmt": "+12% soul gain"},
                {"key": "burn", "fmt": "Infernal brand"},
            ]
        ),
        "stat_rolls": json.dumps({"active": 77, "wp_cost": 68, "passive_1": 83}),
        "equipped_creature_id": None,
    }


def sample_team() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, rarity in enumerate(("Epic", "Legendary", "Eldritch"), start=1):
        creature = pick_creature(rarity, idx)
        rows.append(
            {
                "id": idx,
                "name": creature.name,
                "rarity": creature.rarity,
                "level": 18 + idx,
                "ability": creature.ability,
                "_weapon": sample_weapon(idx),
            }
        )
    return rows


def battle_meter_samples(team: list[dict[str, Any]], hp_ratios: tuple[float, ...], mana_ratios: tuple[float, ...]) -> tuple[list[int], list[int]]:
    hp_values: list[int] = []
    mana_values: list[int] = []
    for idx, creature in enumerate(team):
        stats = compute_display_stats(creature)
        hp_ratio = hp_ratios[idx] if idx < len(hp_ratios) else 1.0
        mana_ratio = mana_ratios[idx] if idx < len(mana_ratios) else 1.0
        hp_values.append(max(0, int(int(stats.get("HP", 1)) * hp_ratio)))
        mana_values.append(max(0, int(int(stats.get("MANA", 1)) * mana_ratio)))
    return hp_values, mana_values


def render_all() -> None:
    hunt = HuntCardRenderer()
    battle = BattleCardRenderer()

    write("hunt_grid_6.png", hunt.render_hunt_grid_card(sample_hunt_data(6)))
    write("hunt_grid_15.png", hunt.render_hunt_grid_card(sample_hunt_data(15)))
    write("hunt_grid_premium.png", hunt.render_hunt_grid_card(sample_hunt_data(15)))
    write("hunt_dense_15.png", hunt.render_dense_hunt_card(sample_hunt_data(15)))

    best = pick_creature("Eldritch", 8)
    stats = derive_7stats(best)
    write(
        "bestiary_premium.png",
        render_creature_card(
            creature_name=best.name,
            rarity=best.rarity,
            hp=stats["hp"],
            str_stat=stats["str"],
            pr_stat=stats["pr"],
            wp_stat=stats["wp"],
            mag_stat=stats["mag"],
            mr_stat=stats["mr"],
            role=determine_role(best),
            ability=best.ability,
            level=27,
            xp=74,
            caught=True,
            player_name="Nyx",
            catch_rate=0.0025,
            mana=500,
            weight=9.8,
        ),
    )

    weapon = sample_weapon(1)
    write("weapon_detail_premium.png", render_weapon_detail_card("Nyx", weapon))
    write("weapon_missing_icon_test.png", render_weapon_detail_card("Nyx", sample_weapon(2, missing_icon=True, zero_stats=True)))
    write("weapon_vault_premium.png", render_weapons_card("Nyx", [sample_weapon(i) for i in range(1, 6)], page=1, total_pages=2))

    deals = [
        {"item_key": "cache", "item_name": "Void Cache", "desc": "Cold iron cache with early relic traces.", "rarities": "Rare to Mythic", "shard_cost": 25},
        {"item_key": "relic", "item_name": "Eldritch Relic", "desc": "A whispering relic case from below.", "rarities": "Epic to Abyssal", "shard_cost": 75},
        {"item_key": "treasure", "item_name": "Abyssal Treasure", "desc": "Heavy treasure sealed in red void glass.", "rarities": "Legendary+", "shard_cost": 160},
    ]
    write("weapon_crate_shop.png", render_shop_card("Nyx", deals))
    write(
        "weapon_crate_open_premium.png",
        render_crate_open_card(
            "Nyx",
            "Eldritch Relic",
            {"gold": 1_250_000, "gems": 8_888, "swords": 3, "materials": {"weapon_shard": 240}},
            weapons=[weapon, sample_weapon(2), sample_weapon(3)],
        ),
    )
    write(
        "high_number_rewards_test.png",
        render_crate_open_card(
            "Nyx",
            "Abyssal Treasure",
            {"gold": 999_999_999, "gems": 123_456, "swords": 999, "materials": {"weapon_shard": 88_888}},
            weapons=[sample_weapon(4)],
        ),
    )

    team = sample_team()
    weapons = {1: sample_weapon(1), 2: sample_weapon(2), 3: sample_weapon(3)}
    write("team_premium.png", render_team_card("Nyx", team, team_power=987_654, weapons=weapons))
    enemy_team = list(reversed(team))
    player_hp, player_wp = battle_meter_samples(team, (1.0, 0.72, 0.54), (0.92, 0.66, 0.48))
    enemy_hp, enemy_wp = battle_meter_samples(enemy_team, (0.84, 0.52, 0.0), (0.78, 0.18, 0.0))
    write(
        "battle_card_sample.png",
        battle.render_battle_result(
            {
                "player_name": "Nyx",
                "enemy_name": "Asterion",
                "player_rank": "Voidbound",
                "enemy_rank": "Black Sun",
                "player_team": team,
                "enemy_team": enemy_team,
                "player_hp": player_hp,
                "enemy_hp": enemy_hp,
                "player_wp": player_wp,
                "enemy_wp": enemy_wp,
                "zone_key": "void_realm",
                "won": True,
                "turn": 7,
                "log": ["Nyx's lantern burns through the veil.", "Asterion reels.", "Victory claimed."],
                "rewards": {"gold": 222_222, "gems": 42},
            }
        ),
    )

    entries = []
    rarity_names = [r.name for r in RARITIES]
    for idx, rarity in enumerate((rarity_names * 2)[:10]):
        creature = pick_creature(rarity, idx)
        entries.append(
            {
                "name": creature.name,
                "rarity": creature.rarity,
                "caught": idx % 3 != 0,
                "total": idx + 1,
                "max_level": 10 + idx,
            }
        )
    write(
        "collection_all_rarity_test.png",
        render_collection_card(
            "Nyx",
            entries[:5],
            caught_count=7,
            total_templates=10,
            page=1,
            total_pages=2,
            next_entries=entries[5:10],
        ),
    )
    write(
        "profile_premium.png",
        render_profile_card(
            "Nyx",
            {"level": 42, "xp": 3120, "gold": 8_765_432, "gems": 321, "hunts_done": 1400, "battles_won": 88},
            collection_count=177,
            weapon_name="Lantern",
            xp_needed=5000,
            active_buffs={"blood_sigil": 3, "void_charm": 2},
            profile_cosmetics={"about": "Collector of impossible creatures and polished relics from the lower dark."},
            win_streak=9,
            best_streak=21,
        ),
    )
    write(
        "autohunt_premium.png",
        render_autohunt_card(
            "Void Realm",
            hours=12,
            souls=654_321,
            gems=44,
            xp=18_500,
            materials={"weapon_shard": 90},
            creatures=[f"{m['rarity']} {m['name']} x1" for m in hunt_monsters(9)],
            levels=3,
        ),
    )
    write(
        "buffs_premium.png",
        render_buffs_card("Nyx", "sigils", list(SIGILS)[:5], {list(SIGILS)[0].key: 2} if SIGILS else {}),
    )
    write(
        "charms_premium.png",
        render_buffs_card("Nyx", "charms", list(CHARMS)[:5], {list(CHARMS)[0].key: 2} if CHARMS else {}),
    )
    write(
        "arena_premium.png",
        render_arena_card("Nyx", {"arena_rating": 1840, "level": 42, "battles_won": 88}, rank="Obsidian III", last_match="Won vs Asterion\n+24 rating\nRewards claimed"),
    )

    long_name = sample_hunt_data(3)
    long_name["monsters"][0]["name"] = "The Unspeakably Long Crownless Verdigris Devourer of the Black Sun Gate"
    write("long_name_truncation_test.png", hunt.render_hunt_grid_card(long_name))

    alias("weapon_vault_premium.png", "weapon_vault.png")
    alias("hunt_grid_6.png", "hunt_result_6.png")
    alias("hunt_grid_15.png", "hunt_result_15.png")
    alias("weapon_crate_shop.png", "crate_shop.png")
    alias("weapon_detail_premium.png", "weapon_detail.png")
    alias("battle_card_sample.png", "battle_card.png")
    alias("bestiary_premium.png", "bestiary_page.png")
    alias("profile_premium.png", "profile_card.png")
    build_contact_sheet()
    build_contact_sheet(output_name="all_cards_contact_sheet_v2.png", title="Abyssia Card Preview Contact Sheet V2")


if __name__ == "__main__":
    render_all()
    print(f"Wrote previews to {OUT_DIR}")
