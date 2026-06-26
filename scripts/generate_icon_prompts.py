"""Generate Abyssia weapon/passive icon prompts and workflow docs.

This script intentionally does not generate art by itself. It creates the
canonical prompt catalog for a selected image model or future repo integration.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "icon_prompts.json"
DOC_PATH = ROOT_DIR / "docs" / "icon_generation_prompts.md"

PROMPT_TEMPLATE = (
    "Crisp pixel-art dark fantasy RPG icon for {display_name}: {concept}. "
    "Centered object, transparent background, 512x512, bold readable silhouette, "
    "high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, "
    "moderate detail only, readable at Discord emoji size, no text, no letters, "
    "no watermark, no character, no full scene."
)

NEGATIVE_PROMPT = (
    "text, letters, numbers, watermark, logo, blurry, low contrast, flat circle "
    "with letter, simple emoji, cluttered background, cropped object, "
    "photorealism, cartoon sticker, generic app icon, UI button text."
)


@dataclass(frozen=True)
class IconSpec:
    key: str
    display_name: str
    category: str
    concept: str
    palette: str

    @property
    def emoji_name(self) -> str:
        prefix = "weapon" if self.category == "weapons" else "passive"
        return f"{prefix}_{self.key}"

    @property
    def output_path(self) -> str:
        return f"assets/icons/{self.category}/{self.key}.png"

    @property
    def prompt(self) -> str:
        return PROMPT_TEMPLATE.format(display_name=self.display_name, concept=self.concept)

    def to_record(self) -> dict[str, str]:
        return {
            "key": self.key,
            "display_name": self.display_name,
            "category": self.category,
            "concept": self.concept,
            "palette": self.palette,
            "output_path": self.output_path,
            "emoji_name": self.emoji_name,
            "prompt": self.prompt,
            "negative_prompt": NEGATIVE_PROMPT,
        }


WEAPONS: tuple[IconSpec, ...] = (
    IconSpec("sword", "Gravecut", "weapons", "black steel grave-sword with bone hilt and cyan edge glow", "black steel, bone ivory, grave cyan, cold mist"),
    IconSpec("bow", "Dreadbow", "weapons", "twisted bone-and-shadow bow with a spectral arrow", "bone ivory, void blue, black shadow, pale spectral light"),
    IconSpec("axe", "Goreaxe", "weapons", "brutal crimson execution axe, chipped head, blood-rust glow", "crimson, rust brown, dark iron, blackened red"),
    IconSpec("dagger", "Veinshiv", "weapons", "curved fang shiv with poison green edge and black handle", "toxic green, black leather, bone white, dark steel"),
    IconSpec("crossbow", "Corpsebolt", "weapons", "gothic bone crossbow loaded with a coffin-bolt", "dark iron, old bone, coffin wood, cold blue accents"),
    IconSpec("staff", "Witchflame", "weapons", "witch staff crowned with violet flame and simple carved runes", "violet flame, black wood, rune cyan, ashen gray"),
    IconSpec("staff_of_purity", "Pale Benediction", "weapons", "pale staff with black halo and white-blue cleansing flame", "pale ivory, black halo, white blue flame, silver"),
    IconSpec("shield", "Lastwall", "weapons", "ancient cracked shield with crown sigil and blue ward glow", "aged steel, royal blue ward, crown gold, black cracks"),
    IconSpec("hammer", "Bellmaul", "weapons", "funeral maul with bell motif and a few glowing cracks", "dark iron, funeral brass, ember cracks, muted bone"),
    IconSpec("orb", "Voidheart", "weapons", "floating black orb with blue void core and orbiting shards", "black glass, void blue, cyan glow, silver shard highlights"),
    IconSpec("rune", "Hexrune", "weapons", "stone rune slab with one impossible glowing glyph", "ancient stone, eldritch teal, violet shadows, bone dust"),
    IconSpec("soulreaper", "Mournreaper", "weapons", "crescent scythe with pale soul mist", "cold steel, spectral cyan, black handle, pale soul mist"),
    IconSpec("briar_relic", "Thornheart", "weapons", "thorn-wrapped relic heart with green-black briars", "deep green, black thorns, red heart glow, antique bronze"),
    IconSpec("rot_chalice", "Rotgrail", "weapons", "cursed chalice dripping green rot and black ichor", "toxic green, black ichor, tarnished gold, sickly yellow"),
    IconSpec("banner", "Dawnbane", "weapons", "torn war banner with black sun emblem", "black cloth, faded crimson, dull gold, ash gray"),
    IconSpec("eye", "Gloomgaze", "weapons", "eldritch eye in a half-open stone doorway", "void teal, wet black, cold stone, pale eye glow"),
    IconSpec("judgement_blade", "Sinblade", "weapons", "judgment blade with broken crown and scale motif", "silver steel, broken gold crown, black enamel, blue white gleam"),
    IconSpec("lantern", "Starvelight", "weapons", "black lantern with starving blue flame", "black iron, hungry blue flame, desaturated brass, smoky cyan"),
    IconSpec("mirror_relic", "Curseglass", "weapons", "cracked mirror with an eye in reflection", "black glass, silver cracks, pale eye, violet reflection"),
    IconSpec("final_bell_scythe", "Doomknell", "weapons", "scythe with hanging funeral bell and pale death glow", "pale steel, funeral brass, deathly cyan, black wood"),
)

PASSIVES: tuple[IconSpec, ...] = (
    IconSpec("strength", "Strength", "passives", "cursed gauntlet breaking bone chains", "dark iron, bone, ember red, sharp highlights"),
    IconSpec("magic", "Magic", "passives", "purple spell sigil with floating sparks", "royal purple, cyan sparks, black void, bright rune edges"),
    IconSpec("hp", "Bloodwell", "passives", "red blood crystal heart", "blood red, black crystal, ruby glow, dark silver"),
    IconSpec("wp", "Mana Vein", "passives", "blue glowing crystal-vein network", "mana blue, deep navy, crystalline white, violet shadow"),
    IconSpec("pr", "Ironhide", "passives", "cracked iron scale plate", "dark iron, smoky gray, blue glints, black cracks"),
    IconSpec("mr", "Witchward", "passives", "teal ward circle over dark shield", "teal magic, charcoal shield, pale sparks, violet rim"),
    IconSpec("thorns", "Thorns", "passives", "thorn crown around a blood drop", "black thorn, blood red, poison green, old gold"),
    IconSpec("safeguard", "Safeguard", "passives", "barrier dome over skull", "ward blue, bone ivory, transparent cyan, black ground"),
    IconSpec("regeneration", "Regeneration", "passives", "green life flame rising from bone", "life green, bone ivory, black ash, soft gold"),
    IconSpec("adaptation", "Adaptation", "passives", "split shield, half stone, half magic aura", "stone gray, void purple, teal magic, black outline"),
    IconSpec("sacrifice", "Sacrifice", "passives", "black hand offering a red soul", "black hand, red soul, crimson rim, smoky gray"),
    IconSpec("bleed", "Rending", "passives", "claw marks dripping blood", "blood red, black claw shadow, wet crimson, pale edge"),
    IconSpec("burn", "Infernal", "passives", "black-red flame", "black ember, infernal red, hot orange, pale ash"),
    IconSpec("poison", "Virulent", "passives", "poison skull/vial with green vapor", "venom green, bone skull, dark glass, yellow vapor"),
    IconSpec("stun", "Stunning", "passives", "cracked bell with lightning impact", "brass bell, electric yellow, blue sparks, black cracks"),
    IconSpec("shield", "Aegis", "passives", "blue ward shield", "ward blue, silver edge, black center, cyan glow"),
    IconSpec("heal", "Lifestream", "passives", "green healing stream around a heart", "emerald green, red heart, gold light, dark void"),
    IconSpec("crit", "Precision", "passives", "eye through crosshair with gold star glint", "gold glint, black iris, pale eye, red crosshair"),
    IconSpec("life_steal", "Lifesteal", "passives", "fangs draining red essence", "ivory fangs, red essence, black mouth, crimson shine"),
    IconSpec("mana_tap", "Mana Tap", "passives", "blue siphon spiral pulling mana drops", "mana blue, dark purple, cyan drops, black spiral"),
    IconSpec("soul_gain", "Soul Gain", "passives", "golden soul coin with ghost trail", "soul gold, pale ghost, cyan trail, dark edge"),
    IconSpec("gem_finder", "Gem Finder", "passives", "prism gem held in dark claws", "prismatic gem, black claws, cyan sparkle, ruby edge"),
    IconSpec("xp_boost", "XP Boost", "passives", "open book with gold flame", "old parchment, gold flame, black cover, violet shadow"),
    IconSpec("rare_finder", "Rare Finder", "passives", "magnifying glass over tiny relic", "brass lens, teal glass, dark relic, gold fleck"),
    IconSpec("energize", "Energize", "passives", "blue lightning battery rune", "electric blue, black stone, white lightning, violet rim"),
    IconSpec("fear", "Dread", "passives", "ghostly mask with fear aura", "pale mask, smoky purple, black void, sickly teal"),
)


def all_specs() -> tuple[IconSpec, ...]:
    return WEAPONS + PASSIVES


def all_records() -> list[dict[str, str]]:
    return [spec.to_record() for spec in all_specs()]


def ensure_output_dirs() -> None:
    for path in (
        ROOT_DIR / "assets" / "icons" / "weapons",
        ROOT_DIR / "assets" / "icons" / "passives",
        ROOT_DIR / "assets" / "emojis" / "weapons",
        ROOT_DIR / "assets" / "emojis" / "passives",
        ROOT_DIR / "tmp" / "icon_contact_sheets",
        DATA_PATH.parent,
        DOC_PATH.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)


def write_json() -> None:
    payload = {
        "version": 1,
        "image_size": 512,
        "emoji_size": 128,
        "preview_size": 64,
        "negative_prompt": NEGATIVE_PROMPT,
        "records": all_records(),
    }
    DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _category_title(category: str) -> str:
    return "Weapons" if category == "weapons" else "Passives"


def write_docs() -> None:
    lines: list[str] = [
        "# Abyssia Icon Generation Prompts",
        "",
        "This repository stores the weapon/passive prompt set and local processing pipeline. Do not mark the icon art complete until 512x512 transparent PNGs exist at the listed `output_path` values.",
        "",
        "## Workflow",
        "",
        "1. Run `python scripts/generate_icon_prompts.py` after editing prompt records.",
        "2. Generate one source image per record with the selected image model. For built-in image generation, ask for a flat chroma-key background (`#00ff00` by default, `#ff00ff` for green subjects).",
        "3. Process each built-in source with `python scripts/process_ai_icon_source.py --category <weapons|passives> --key <key> --source <generated.png>`. This copies the raw source under `tmp/imagegen/icons_ai/raw/` and writes the final transparent master to `output_path`.",
        "4. Run `python scripts/process_icons.py --mode pixel` to normalize masters and create Discord-ready 128x128 PNGs plus 64px previews.",
        "5. Run `python scripts/build_icon_contact_sheet.py` and review the sheets under `tmp/icon_contact_sheets/`.",
        "6. Run `python scripts/validate_icons.py --strict-assets --strict-transparency` once all masters are present.",
        "7. Set `DISCORD_TOKEN` and `EMOJI_GUILD_ID`, then run `python scripts/sync_emojis.py` to upload and update `data/emoji_map.json`.",
        "",
        "## Art Direction Rules",
        "",
        "- Dark fantasy RPG, gothic, cursed relics, abyssal/void magic.",
        "- Crisp pixel-art game UI asset, bold silhouette, moderate detail, readable at Discord emoji size.",
        "- Final transparent background, centered object, generous padding, consistent rim light and outline/glow.",
        "- No text, letters, numbers, watermarks, generic emoji art, or flat circles with initials.",
        "",
    ]
    for category in ("weapons", "passives"):
        lines.extend([f"## {_category_title(category)}", ""])
        for record in [item for item in all_records() if item["category"] == category]:
            lines.extend(
                [
                    f"### {record['emoji_name']} - {record['display_name']}",
                    "",
                    f"- Bot key: `{record['key']}`",
                    f"- Output: `{record['output_path']}`",
                    f"- Palette: {record['palette']}",
                    "",
                    "Prompt:",
                    "",
                    "```text",
                    record["prompt"],
                    "```",
                    "",
                    "Negative prompt:",
                    "",
                    "```text",
                    record["negative_prompt"],
                    "```",
                    "",
                ]
            )
    DOC_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_output_dirs()
    write_json()
    write_docs()
    print(f"Wrote {DATA_PATH.relative_to(ROOT_DIR)}")
    print(f"Wrote {DOC_PATH.relative_to(ROOT_DIR)}")
    print(f"Records: {len(all_records())}")


if __name__ == "__main__":
    main()
