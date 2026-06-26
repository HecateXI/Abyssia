"""Generate Abyssia card UI asset prompt records and documentation."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPTS_PATH = ROOT_DIR / "data" / "card_asset_prompts.json"
DOC_PATH = ROOT_DIR / "docs" / "card_asset_prompts.md"

UNIVERSAL_STYLE = (
    "Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone "
    "ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle "
    "void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, "
    "carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board "
    "lines, no tiny HUD text, no text, no letters, no watermark."
)

NEGATIVE_PROMPT = (
    "cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, "
    "tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, "
    "logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic "
    "object, cartoon sticker, low-resolution artifact."
)

REQUIRED_FOLDERS = (
    "assets/ui/backgrounds",
    "assets/ui/panels",
    "assets/ui/frames",
    "assets/ui/buttons",
    "assets/ui/borders",
    "assets/ui/bars",
    "assets/ui/badges",
    "assets/ui/dividers",
    "assets/ui/overlays",
    "assets/ui/effects",
    "assets/ui/card_templates",
    "assets/ui/zone_backdrops",
    "assets/ui/rarity_frames",
    "assets/ui/reward_pills",
    "assets/ui/placeholders",
)


@dataclass(frozen=True)
class CardAssetSpec:
    key: str
    category: str
    output_path: str
    purpose: str
    size: tuple[int, int]
    transparent: bool
    prompt: str
    negative_prompt: str = NEGATIVE_PROMPT
    source_path: str = ""


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def prompt_for(name: str, purpose: str, *, transparent: bool, details: str = "") -> str:
    background = (
        "Transparent background where useful; keep useful alpha and transparent corners."
        if transparent
        else "Full rectangular background, no text, no logo, no UI labels."
    )
    suffix = f" {details.strip()}" if details.strip() else ""
    return f"{UNIVERSAL_STYLE} Asset: {name}. Purpose: {purpose}. {background}{suffix}"


def spec(
    category: str,
    key: str,
    filename: str,
    purpose: str,
    size: tuple[int, int],
    *,
    transparent: bool,
    details: str = "",
    source_path: str = "",
) -> CardAssetSpec:
    output_path = f"assets/ui/{category}/{filename}"
    return CardAssetSpec(
        key=key,
        category=category,
        output_path=output_path,
        purpose=purpose,
        size=size,
        transparent=transparent,
        prompt=prompt_for(key.replace("_", " ").title(), purpose, transparent=transparent, details=details),
        source_path=source_path,
    )


RARITIES: tuple[tuple[str, str], ...] = (
    ("common", "Common"),
    ("uncommon", "Uncommon"),
    ("rare", "Rare"),
    ("epic", "Epic"),
    ("legendary", "Legendary"),
    ("mythic", "Mythic"),
    ("ancient", "Ancient"),
    ("patreon", "Patreon"),
    ("divine", "Divine"),
    ("eldritch", "Eldritch"),
    ("abyssal", "Abyssal"),
    ("prismatic", "Prismatic"),
    ("ethereal", "Ethereal"),
    ("void_lord", "Void Lord"),
    ("hidden", "Hidden"),
)

ZONE_NAMES = (
    "Forgotten Woods",
    "Grave Marsh",
    "Bloodmoon Forest",
    "Ashen Wastes",
    "Infernal Catacombs",
    "Abyssal Depths",
    "Void Realm",
    "Cursed Sanctum",
    "Starless Menagerie",
    "Throne of Teeth",
    "Black Sun Gate",
)


def all_records() -> list[dict[str, object]]:
    records: list[CardAssetSpec] = []

    backgrounds = (
        ("abyssia_dark_base", "dark violet black base card backdrop with faint void particles", "data/assets/ui/card_bg_abyssia_pixel.png"),
        ("abyssia_void_base", "deep void magic base backdrop with abyssal fog", "data/assets/ui/card_bg_abyssia_pixel.png"),
        ("abyssia_ruins_base", "ruined gothic stone hall backdrop with subtle fog", ""),
        ("abyssia_forge_base", "haunted forge backdrop with low ember glow", ""),
        ("abyssia_battle_arena_base", "battle arena backdrop with distant dungeon architecture", "data/assets/ui/battle_bg_abyssia_pixel.png"),
        ("abyssia_hunt_forest_base", "dark haunted forest hunt backdrop", ""),
        ("abyssia_crate_shop_base", "premium dark fantasy merchant relic shop backdrop with altar table, coins, shards, candlelight, and soft mist", ""),
        ("abyssia_weapon_vault_base", "cursed weapon vault room backdrop with gothic stone arch, chains, candles, relic pedestal, and void mist", "data/assets/ui/weapon_vault_bg_abyssia_pixel.png"),
    )
    for key, purpose, source in backgrounds:
        records.append(
            spec(
                "backgrounds",
                key,
                f"{key}.png",
                purpose,
                (1200, 720),
                transparent=False,
                details="Wide composition, subtle ruins, faint fog, particles, magical depth.",
                source_path=source,
            )
        )

    second_pass_assets = (
        ("panels", "gothic_stone_panel", "gothic_stone_panel.png", (900, 560), True, "large raised black stone UI panel with carved depth and readable interior"),
        ("frames", "cursed_gold_frame", "cursed_gold_frame.png", (900, 560), True, "ancient cursed gold card frame with engraved trim and premium RPG depth"),
        ("frames", "bone_corner_ornaments", "bone_corner_ornaments.png", (512, 512), True, "bone and aged gold corner ornament set for gothic reward cards"),
        ("overlays", "abyssal_mist_overlay", "abyssal_mist_overlay.png", (1200, 720), True, "layered abyssal mist and subtle drifting particles for foreground depth"),
        ("effects", "relic_pedestal", "relic_pedestal.png", (640, 320), True, "stone relic pedestal with soft upward void light for featured rewards"),
        ("backgrounds", "dark_altar_background", "dark_altar_background.png", (1600, 900), False, "dark altar background with black marble, candles, chains, and sacred ruin depth"),
        ("dividers", "rune_divider", "rune_divider.png", (900, 42), True, "carved ancient rune divider in muted gold and void purple"),
        ("badges", "rarity_gem_badges", "rarity_gem_badges.png", (640, 128), True, "large readable rarity gem badge row for crate rewards"),
        ("backgrounds", "fantasy_shop_table", "fantasy_shop_table.png", (1600, 900), False, "dark fantasy merchant shop table with coins, shards, candle dust, and premium relic display lighting"),
        ("backgrounds", "cursed_vault_arch", "cursed_vault_arch.png", (1600, 1000), False, "cursed vault arch backdrop with gothic stone, chains, candles, and abyssal mist"),
        ("backgrounds", "boss_arena_backdrop", "boss_arena_backdrop.png", (1600, 900), False, "dark fantasy boss arena backdrop with readable left/right staging and dramatic depth"),
        ("effects", "creature_display_pedestal", "creature_display_pedestal.png", (560, 300), True, "collectible creature display pedestal with bone trim and rarity glow"),
        ("effects", "weapon_display_pedestal", "weapon_display_pedestal.png", (560, 300), True, "weapon display pedestal with black stone, cursed metal, and upward relic glow"),
    )
    for category, key, filename, size, transparent, purpose in second_pass_assets:
        records.append(
            spec(
                category,
                key,
                filename,
                purpose,
                size,
                transparent=transparent,
                details=(
                    "Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, "
                    "large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details."
                ),
            )
        )

    for name in ZONE_NAMES:
        key = slug(name)
        records.append(
            spec(
                "zone_backdrops",
                key,
                f"{key}.png",
                f"{name} zone backdrop for hunt and bestiary cards",
                (1600, 900),
                transparent=False,
                details=f"Environmental dark fantasy scene evoking {name}; no characters, no UI text.",
            )
        )

    panels = (
        ("main_panel_dark", (900, 520), "large dark stone/glass content panel", "data/assets/ui/frame_window_abyssia_pixel.png"),
        ("main_panel_glass", (900, 520), "large translucent dark glass content panel", "data/assets/ui/frame_window_abyssia_pixel.png"),
        ("small_panel", (420, 220), "compact beveled UI panel", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("stat_panel", (320, 160), "compact stat block panel", "data/assets/ui/frame_badge_abyssia_pixel.png"),
        ("item_panel", (520, 320), "item tile panel", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("tooltip_panel", (620, 360), "tooltip information panel", "data/assets/ui/frame_window_abyssia_pixel.png"),
        ("card_slot_panel", (360, 480), "vertical card slot panel", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("list_row_panel", (900, 120), "horizontal list row panel", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("selected_row_panel", (900, 120), "selected list row panel with stronger glow", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("modal_panel", (960, 620), "large modal dialog panel", "data/assets/ui/frame_window_abyssia_pixel.png"),
    )
    for key, size, purpose, source in panels:
        records.append(spec("panels", key, f"{key}.png", purpose, size, transparent=True, source_path=source))

    for key, display in RARITIES:
        records.append(
            spec(
                "rarity_frames",
                key,
                f"{key}.png",
                f"{display} rarity frame for creature, weapon, and item tiles",
                (512, 512),
                transparent=True,
                details=f"Consistent frame shape; material and glow should clearly signal {display} rarity.",
                source_path="data/assets/ui/frame_icon_abyssia_pixel.png",
            )
        )
        records.append(
            spec(
                "frames",
                f"creature_tile_{key}",
                f"creature_tile_{key}.png",
                f"{display} creature tile frame with portrait/name/badge zones",
                (420, 520),
                transparent=True,
                details="Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.",
                source_path="data/assets/ui/frame_card_abyssia_pixel.png",
            )
        )

    weapon_frames = (
        ("weapon_slot_frame", (360, 460), "weapon slot frame for grid cards"),
        ("weapon_feature_frame", (620, 520), "featured weapon display frame"),
        ("weapon_relic_large_frame", (520, 600), "large relic tooltip weapon frame"),
        ("weapon_vault_side_slot", (300, 320), "weapon vault side slot frame"),
        ("weapon_vault_center_display", (760, 360), "weapon vault center information display"),
    )
    for key, size, purpose in weapon_frames:
        records.append(spec("frames", key, f"{key}.png", purpose, size, transparent=True, source_path="data/assets/ui/frame_card_abyssia_pixel.png"))

    crate_assets = (
        ("card_templates", "crate_shop_panel", "crate_shop_panel.png", (1200, 720), False, "full crate shop card base panel", "data/assets/ui/card_bg_abyssia_pixel.png"),
        ("card_templates", "crate_shop_card_void_cache", "crate_shop_card_void_cache.png", (360, 480), True, "void cache shop card frame", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("card_templates", "crate_shop_card_eldritch_relic", "crate_shop_card_eldritch_relic.png", (360, 480), True, "eldritch relic shop card frame", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("card_templates", "crate_shop_card_abyssal_treasure", "crate_shop_card_abyssal_treasure.png", (360, 480), True, "abyssal treasure shop card frame", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("buttons", "price_button", "price_button.png", (320, 96), True, "readable price button frame", "data/assets/ui/frame_badge_abyssia_pixel.png"),
        ("frames", "buy_dropdown_frame", "buy_dropdown_frame.png", (520, 240), True, "buy dropdown frame", "data/assets/ui/frame_window_abyssia_pixel.png"),
        ("effects", "crate_glow_cyan", "crate_glow_cyan.png", (420, 420), True, "cyan crate glow effect", ""),
        ("effects", "crate_glow_green", "crate_glow_green.png", (420, 420), True, "green crate glow effect", ""),
        ("effects", "crate_glow_purple", "crate_glow_purple.png", (420, 420), True, "purple crate glow effect", ""),
    )
    for category, key, filename, size, transparent, purpose, source in crate_assets:
        records.append(spec(category, key, filename, purpose, size, transparent=transparent, source_path=source))

    battle_assets = (
        ("backgrounds", "battle_arena_backdrop", "battle_arena_backdrop.png", (1600, 900), False, "battle arena backdrop", "data/assets/ui/battle_bg_abyssia_pixel.png"),
        ("panels", "battle_team_panel_left", "battle_team_panel_left.png", (620, 720), True, "left battle team panel", "data/assets/ui/battle_panel_bg_abyssia_pixel.png"),
        ("panels", "battle_team_panel_right", "battle_team_panel_right.png", (620, 720), True, "right battle team panel", "data/assets/ui/battle_panel_bg_abyssia_pixel.png"),
        ("frames", "battle_creature_slot", "battle_creature_slot.png", (360, 260), True, "battle creature slot frame", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("badges", "battle_center_plaque", "battle_center_plaque.png", (520, 180), True, "battle result center plaque", "data/assets/ui/frame_badge_abyssia_pixel.png"),
        ("bars", "hp_bar_frame", "hp_bar_frame.png", (520, 64), True, "HP bar frame", "data/assets/ui/frame_badge_abyssia_pixel.png"),
        ("bars", "mana_bar_frame", "mana_bar_frame.png", (520, 64), True, "mana bar frame", "data/assets/ui/frame_badge_abyssia_pixel.png"),
        ("bars", "boss_hp_bar_frame", "boss_hp_bar_frame.png", (900, 80), True, "boss HP bar frame", "data/assets/ui/frame_badge_abyssia_pixel.png"),
        ("badges", "victory_banner", "victory_banner.png", (700, 160), True, "victory banner frame", "data/assets/ui/frame_badge_abyssia_pixel.png"),
        ("badges", "defeat_banner", "defeat_banner.png", (700, 160), True, "defeat banner frame", "data/assets/ui/frame_badge_abyssia_pixel.png"),
        ("badges", "tie_banner", "tie_banner.png", (700, 160), True, "tie banner frame", "data/assets/ui/frame_badge_abyssia_pixel.png"),
    )
    for category, key, filename, size, transparent, purpose, source in battle_assets:
        records.append(spec(category, key, filename, purpose, size, transparent=transparent, source_path=source))

    hunt_assets = (
        ("badges", "hunt_header_plate", "hunt_header_plate.png", (900, 120), True, "hunt card header plate"),
        ("frames", "hunt_result_tile", "hunt_result_tile.png", (340, 380), True, "hunt result creature tile"),
        ("frames", "hunt_result_tile_selected", "hunt_result_tile_selected.png", (340, 380), True, "selected hunt result creature tile"),
        ("panels", "hunt_dense_row", "hunt_dense_row.png", (900, 96), True, "dense hunt row panel"),
        ("badges", "duplicate_tag", "duplicate_tag.png", (220, 64), True, "duplicate result tag"),
        ("badges", "new_tag", "new_tag.png", (220, 64), True, "new discovery tag"),
        ("reward_pills", "souls_pill", "souls_pill.png", (320, 88), True, "souls reward pill"),
        ("reward_pills", "xp_pill", "xp_pill.png", (320, 88), True, "XP reward pill"),
        ("reward_pills", "crate_reward_pill", "crate_reward_pill.png", (360, 88), True, "crate reward pill"),
    )
    for category, key, filename, size, transparent, purpose in hunt_assets:
        records.append(spec(category, key, filename, purpose, size, transparent=transparent, source_path="data/assets/ui/frame_badge_abyssia_pixel.png" if "pill" in key or "tag" in key else "data/assets/ui/frame_card_abyssia_pixel.png"))

    vault_assets = (
        ("backgrounds", "weapon_vault_room_background", "weapon_vault_room_background.png", (1200, 900), False, "weapon vault room background", "data/assets/ui/weapon_vault_bg_abyssia_pixel.png"),
        ("effects", "weapon_vault_center_pedestal", "weapon_vault_center_pedestal.png", (520, 220), True, "center weapon pedestal"),
        ("effects", "weapon_vault_glow", "weapon_vault_glow.png", (640, 640), True, "weapon vault central glow"),
        ("frames", "weapon_vault_side_slot_left", "weapon_vault_side_slot_left.png", (300, 340), True, "left side weapon slot", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("frames", "weapon_vault_side_slot_right", "weapon_vault_side_slot_right.png", (300, 340), True, "right side weapon slot", "data/assets/ui/frame_card_abyssia_pixel.png"),
        ("bars", "weapon_vault_page_bar", "weapon_vault_page_bar.png", (900, 64), True, "weapon vault page bar", "data/assets/ui/frame_badge_abyssia_pixel.png"),
        ("buttons", "weapon_vault_filter_button", "weapon_vault_filter_button.png", (220, 72), True, "weapon vault filter button", "data/assets/ui/frame_badge_abyssia_pixel.png"),
    )
    for item in vault_assets:
        category, key, filename, size, transparent, purpose, *source = item
        records.append(spec(category, key, filename, purpose, size, transparent=transparent, source_path=source[0] if source else ""))

    bars = (
        ("hp_bar_fill", "HP bar fill", (520, 36), "bars"),
        ("mana_bar_fill", "mana bar fill", (520, 36), "bars"),
        ("xp_bar_fill", "XP bar fill", (520, 36), "bars"),
        ("quality_bar_fill", "quality bar fill", (520, 36), "bars"),
        ("progress_bar_frame", "progress bar frame", (620, 64), "bars"),
        ("thin_gold_divider", "thin gold divider", (760, 18), "dividers"),
        ("cyan_divider", "cyan divider", (760, 24), "dividers"),
        ("purple_divider", "purple divider", (760, 24), "dividers"),
    )
    for key, purpose, size, category in bars:
        source = "data/assets/ui/frame_badge_abyssia_pixel.png" if "frame" in key else ""
        records.append(spec(category, key, f"{key}.png", purpose, size, transparent=True, source_path=source))

    rewards = (
        ("reward_pill_souls", "souls reward pill"),
        ("reward_pill_xp", "XP reward pill"),
        ("reward_pill_weapon_shards", "weapon shards reward pill"),
        ("reward_pill_crate", "crate reward pill"),
    )
    for key, purpose in rewards:
        records.append(spec("reward_pills", key, f"{key}.png", purpose, (360, 90), transparent=True, source_path="data/assets/ui/frame_badge_abyssia_pixel.png"))
    for key, purpose in (
        ("quality_badge", "quality badge"),
        ("mana_badge", "mana badge"),
        ("level_badge", "level badge"),
        ("owned_badge", "owned badge"),
        ("locked_badge", "locked badge"),
    ):
        records.append(spec("badges", key, f"{key}.png", purpose, (260, 76), transparent=True, source_path="data/assets/ui/frame_badge_abyssia_pixel.png"))

    overlays = (
        ("foreground_fog", "foreground fog overlay"),
        ("void_particles", "void particles overlay"),
        ("gold_sparkles", "gold sparkles overlay"),
        ("cyan_magic_motes", "cyan magic motes overlay"),
        ("purple_magic_motes", "purple magic motes overlay"),
        ("bloodmoon_particles", "bloodmoon particles overlay"),
        ("stone_grain_texture", "subtle black marble and carved stone grain overlay"),
        ("vignette_overlay", "vignette overlay"),
        ("radial_spotlight", "radial spotlight overlay"),
    )
    for key, purpose in overlays:
        records.append(spec("overlays", key, f"{key}.png", purpose, (1200, 720), transparent=True))

    records.append(
        spec(
            "placeholders",
            "missing_card_asset",
            "missing_card_asset.png",
            "fallback placeholder for missing card assets",
            (512, 512),
            transparent=True,
            source_path="data/assets/ui/frame_icon_abyssia_pixel.png",
        )
    )
    return [asdict(item) for item in records]


def grouped_records(records: Iterable[dict[str, object]]) -> dict[str, dict[str, dict[str, object]]]:
    grouped: dict[str, dict[str, dict[str, object]]] = {}
    for record in records:
        grouped.setdefault(str(record["category"]), {})[str(record["key"])] = record
    return grouped


def write_json(records: list[dict[str, object]]) -> None:
    payload = {
        "version": 1,
        "style": UNIVERSAL_STYLE,
        "negative_prompt": NEGATIVE_PROMPT,
        "required_folders": list(REQUIRED_FOLDERS),
        "records": records,
    }
    PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_docs(records: list[dict[str, object]]) -> None:
    lines = [
        "# Abyssia Card Asset Prompts",
        "",
        "These records define the reusable premium card UI asset pack. Text must be drawn by the bot, not baked into image assets.",
        "",
        "## Workflow",
        "",
        "1. Run `python scripts/generate_card_asset_prompts.py` after editing asset records.",
        "2. Use `data/card_asset_prompts.json` to generate final AI assets, or run `python scripts/process_card_assets.py` to create manifest-tracked placeholders.",
        "3. Run `python scripts/process_card_assets.py --force-normalize` after replacing any source PNGs.",
        "4. Run `python scripts/validate_card_assets.py --render-previews` and review `tmp/card_previews/all_cards_contact_sheet.png`.",
        "",
        "## Universal Style",
        "",
        UNIVERSAL_STYLE,
        "",
        "## Universal Negative Prompt",
        "",
        NEGATIVE_PROMPT,
        "",
    ]
    for category, items in grouped_records(records).items():
        lines.extend([f"## {category.replace('_', ' ').title()}", ""])
        for key, record in items.items():
            lines.extend(
                [
                    f"### {key}",
                    "",
                    f"- Output: `{record['output_path']}`",
                    f"- Purpose: {record['purpose']}",
                    f"- Size: {record['size'][0]}x{record['size'][1]}",
                    f"- Transparent: {str(record['transparent']).lower()}",
                    "",
                    "Prompt:",
                    "",
                    "```text",
                    str(record["prompt"]),
                    "```",
                    "",
                    "Negative prompt:",
                    "",
                    "```text",
                    str(record["negative_prompt"]),
                    "```",
                    "",
                ]
            )
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()
    records = all_records()
    write_json(records)
    if not args.json_only:
        write_docs(records)
    print(f"Wrote {PROMPTS_PATH.relative_to(ROOT_DIR)}")
    if not args.json_only:
        print(f"Wrote {DOC_PATH.relative_to(ROOT_DIR)}")
    print(f"Records: {len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
