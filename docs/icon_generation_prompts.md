# Abyssia Icon Generation Prompts

This repository stores the weapon/passive prompt set and local processing pipeline. Do not mark the icon art complete until 512x512 transparent PNGs exist at the listed `output_path` values.

## Workflow

1. Run `python scripts/generate_icon_prompts.py` after editing prompt records.
2. Generate one source image per record with the selected image model. For built-in image generation, ask for a flat chroma-key background (`#00ff00` by default, `#ff00ff` for green subjects).
3. Process each built-in source with `python scripts/process_ai_icon_source.py --category <weapons|passives> --key <key> --source <generated.png>`. This copies the raw source under `tmp/imagegen/icons_ai/raw/` and writes the final transparent master to `output_path`.
4. Run `python scripts/process_icons.py --mode pixel` to normalize masters and create Discord-ready 128x128 PNGs plus 64px previews.
5. Run `python scripts/build_icon_contact_sheet.py` and review the sheets under `tmp/icon_contact_sheets/`.
6. Run `python scripts/validate_icons.py --strict-assets --strict-transparency` once all masters are present.
7. Set `DISCORD_TOKEN` and `EMOJI_GUILD_ID`, then run `python scripts/sync_emojis.py` to upload and update `data/emoji_map.json`.

## Art Direction Rules

- Dark fantasy RPG, gothic, cursed relics, abyssal/void magic.
- Crisp pixel-art game UI asset, bold silhouette, moderate detail, readable at Discord emoji size.
- Final transparent background, centered object, generous padding, consistent rim light and outline/glow.
- No text, letters, numbers, watermarks, generic emoji art, or flat circles with initials.

## Weapons

### weapon_sword - Gravecut

- Bot key: `sword`
- Output: `assets/icons/weapons/sword.png`
- Palette: black steel, bone ivory, grave cyan, cold mist

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Gravecut: black steel grave-sword with bone hilt and cyan edge glow. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_bow - Dreadbow

- Bot key: `bow`
- Output: `assets/icons/weapons/bow.png`
- Palette: bone ivory, void blue, black shadow, pale spectral light

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Dreadbow: twisted bone-and-shadow bow with a spectral arrow. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_axe - Goreaxe

- Bot key: `axe`
- Output: `assets/icons/weapons/axe.png`
- Palette: crimson, rust brown, dark iron, blackened red

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Goreaxe: brutal crimson execution axe, chipped head, blood-rust glow. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_dagger - Veinshiv

- Bot key: `dagger`
- Output: `assets/icons/weapons/dagger.png`
- Palette: toxic green, black leather, bone white, dark steel

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Veinshiv: curved fang shiv with poison green edge and black handle. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_crossbow - Corpsebolt

- Bot key: `crossbow`
- Output: `assets/icons/weapons/crossbow.png`
- Palette: dark iron, old bone, coffin wood, cold blue accents

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Corpsebolt: gothic bone crossbow loaded with a coffin-bolt. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_staff - Witchflame

- Bot key: `staff`
- Output: `assets/icons/weapons/staff.png`
- Palette: violet flame, black wood, rune cyan, ashen gray

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Witchflame: witch staff crowned with violet flame and simple carved runes. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_staff_of_purity - Pale Benediction

- Bot key: `staff_of_purity`
- Output: `assets/icons/weapons/staff_of_purity.png`
- Palette: pale ivory, black halo, white blue flame, silver

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Pale Benediction: pale staff with black halo and white-blue cleansing flame. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_shield - Lastwall

- Bot key: `shield`
- Output: `assets/icons/weapons/shield.png`
- Palette: aged steel, royal blue ward, crown gold, black cracks

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Lastwall: ancient cracked shield with crown sigil and blue ward glow. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_hammer - Bellmaul

- Bot key: `hammer`
- Output: `assets/icons/weapons/hammer.png`
- Palette: dark iron, funeral brass, ember cracks, muted bone

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Bellmaul: funeral maul with bell motif and a few glowing cracks. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_orb - Voidheart

- Bot key: `orb`
- Output: `assets/icons/weapons/orb.png`
- Palette: black glass, void blue, cyan glow, silver shard highlights

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Voidheart: floating black orb with blue void core and orbiting shards. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_rune - Hexrune

- Bot key: `rune`
- Output: `assets/icons/weapons/rune.png`
- Palette: ancient stone, eldritch teal, violet shadows, bone dust

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Hexrune: stone rune slab with one impossible glowing glyph. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_soulreaper - Mournreaper

- Bot key: `soulreaper`
- Output: `assets/icons/weapons/soulreaper.png`
- Palette: cold steel, spectral cyan, black handle, pale soul mist

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Mournreaper: crescent scythe with pale soul mist. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_briar_relic - Thornheart

- Bot key: `briar_relic`
- Output: `assets/icons/weapons/briar_relic.png`
- Palette: deep green, black thorns, red heart glow, antique bronze

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Thornheart: thorn-wrapped relic heart with green-black briars. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_rot_chalice - Rotgrail

- Bot key: `rot_chalice`
- Output: `assets/icons/weapons/rot_chalice.png`
- Palette: toxic green, black ichor, tarnished gold, sickly yellow

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Rotgrail: cursed chalice dripping green rot and black ichor. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_banner - Dawnbane

- Bot key: `banner`
- Output: `assets/icons/weapons/banner.png`
- Palette: black cloth, faded crimson, dull gold, ash gray

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Dawnbane: torn war banner with black sun emblem. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_eye - Gloomgaze

- Bot key: `eye`
- Output: `assets/icons/weapons/eye.png`
- Palette: void teal, wet black, cold stone, pale eye glow

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Gloomgaze: eldritch eye in a half-open stone doorway. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_judgement_blade - Sinblade

- Bot key: `judgement_blade`
- Output: `assets/icons/weapons/judgement_blade.png`
- Palette: silver steel, broken gold crown, black enamel, blue white gleam

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Sinblade: judgment blade with broken crown and scale motif. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_lantern - Starvelight

- Bot key: `lantern`
- Output: `assets/icons/weapons/lantern.png`
- Palette: black iron, hungry blue flame, desaturated brass, smoky cyan

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Starvelight: black lantern with starving blue flame. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_mirror_relic - Curseglass

- Bot key: `mirror_relic`
- Output: `assets/icons/weapons/mirror_relic.png`
- Palette: black glass, silver cracks, pale eye, violet reflection

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Curseglass: cracked mirror with an eye in reflection. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### weapon_final_bell_scythe - Doomknell

- Bot key: `final_bell_scythe`
- Output: `assets/icons/weapons/final_bell_scythe.png`
- Palette: pale steel, funeral brass, deathly cyan, black wood

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Doomknell: scythe with hanging funeral bell and pale death glow. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

## Passives

### passive_strength - Strength

- Bot key: `strength`
- Output: `assets/icons/passives/strength.png`
- Palette: dark iron, bone, ember red, sharp highlights

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Strength: cursed gauntlet breaking bone chains. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_magic - Magic

- Bot key: `magic`
- Output: `assets/icons/passives/magic.png`
- Palette: royal purple, cyan sparks, black void, bright rune edges

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Magic: purple spell sigil with floating sparks. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_hp - Bloodwell

- Bot key: `hp`
- Output: `assets/icons/passives/hp.png`
- Palette: blood red, black crystal, ruby glow, dark silver

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Bloodwell: red blood crystal heart. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_wp - Mana Vein

- Bot key: `wp`
- Output: `assets/icons/passives/wp.png`
- Palette: mana blue, deep navy, crystalline white, violet shadow

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Mana Vein: blue glowing crystal-vein network. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_pr - Ironhide

- Bot key: `pr`
- Output: `assets/icons/passives/pr.png`
- Palette: dark iron, smoky gray, blue glints, black cracks

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Ironhide: cracked iron scale plate. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_mr - Witchward

- Bot key: `mr`
- Output: `assets/icons/passives/mr.png`
- Palette: teal magic, charcoal shield, pale sparks, violet rim

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Witchward: teal ward circle over dark shield. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_thorns - Thorns

- Bot key: `thorns`
- Output: `assets/icons/passives/thorns.png`
- Palette: black thorn, blood red, poison green, old gold

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Thorns: thorn crown around a blood drop. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_safeguard - Safeguard

- Bot key: `safeguard`
- Output: `assets/icons/passives/safeguard.png`
- Palette: ward blue, bone ivory, transparent cyan, black ground

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Safeguard: barrier dome over skull. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_regeneration - Regeneration

- Bot key: `regeneration`
- Output: `assets/icons/passives/regeneration.png`
- Palette: life green, bone ivory, black ash, soft gold

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Regeneration: green life flame rising from bone. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_adaptation - Adaptation

- Bot key: `adaptation`
- Output: `assets/icons/passives/adaptation.png`
- Palette: stone gray, void purple, teal magic, black outline

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Adaptation: split shield, half stone, half magic aura. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_sacrifice - Sacrifice

- Bot key: `sacrifice`
- Output: `assets/icons/passives/sacrifice.png`
- Palette: black hand, red soul, crimson rim, smoky gray

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Sacrifice: black hand offering a red soul. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_bleed - Rending

- Bot key: `bleed`
- Output: `assets/icons/passives/bleed.png`
- Palette: blood red, black claw shadow, wet crimson, pale edge

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Rending: claw marks dripping blood. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_burn - Infernal

- Bot key: `burn`
- Output: `assets/icons/passives/burn.png`
- Palette: black ember, infernal red, hot orange, pale ash

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Infernal: black-red flame. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_poison - Virulent

- Bot key: `poison`
- Output: `assets/icons/passives/poison.png`
- Palette: venom green, bone skull, dark glass, yellow vapor

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Virulent: poison skull/vial with green vapor. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_stun - Stunning

- Bot key: `stun`
- Output: `assets/icons/passives/stun.png`
- Palette: brass bell, electric yellow, blue sparks, black cracks

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Stunning: cracked bell with lightning impact. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_shield - Aegis

- Bot key: `shield`
- Output: `assets/icons/passives/shield.png`
- Palette: ward blue, silver edge, black center, cyan glow

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Aegis: blue ward shield. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_heal - Lifestream

- Bot key: `heal`
- Output: `assets/icons/passives/heal.png`
- Palette: emerald green, red heart, gold light, dark void

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Lifestream: green healing stream around a heart. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_crit - Precision

- Bot key: `crit`
- Output: `assets/icons/passives/crit.png`
- Palette: gold glint, black iris, pale eye, red crosshair

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Precision: eye through crosshair with gold star glint. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_life_steal - Lifesteal

- Bot key: `life_steal`
- Output: `assets/icons/passives/life_steal.png`
- Palette: ivory fangs, red essence, black mouth, crimson shine

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Lifesteal: fangs draining red essence. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_mana_tap - Mana Tap

- Bot key: `mana_tap`
- Output: `assets/icons/passives/mana_tap.png`
- Palette: mana blue, dark purple, cyan drops, black spiral

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Mana Tap: blue siphon spiral pulling mana drops. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_soul_gain - Soul Gain

- Bot key: `soul_gain`
- Output: `assets/icons/passives/soul_gain.png`
- Palette: soul gold, pale ghost, cyan trail, dark edge

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Soul Gain: golden soul coin with ghost trail. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_gem_finder - Gem Finder

- Bot key: `gem_finder`
- Output: `assets/icons/passives/gem_finder.png`
- Palette: prismatic gem, black claws, cyan sparkle, ruby edge

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Gem Finder: prism gem held in dark claws. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_xp_boost - XP Boost

- Bot key: `xp_boost`
- Output: `assets/icons/passives/xp_boost.png`
- Palette: old parchment, gold flame, black cover, violet shadow

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for XP Boost: open book with gold flame. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_rare_finder - Rare Finder

- Bot key: `rare_finder`
- Output: `assets/icons/passives/rare_finder.png`
- Palette: brass lens, teal glass, dark relic, gold fleck

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Rare Finder: magnifying glass over tiny relic. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_energize - Energize

- Bot key: `energize`
- Output: `assets/icons/passives/energize.png`
- Palette: electric blue, black stone, white lightning, violet rim

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Energize: blue lightning battery rune. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```

### passive_fear - Dread

- Bot key: `fear`
- Output: `assets/icons/passives/fear.png`
- Palette: pale mask, smoky purple, black void, sickly teal

Prompt:

```text
Crisp pixel-art dark fantasy RPG icon for Dread: ghostly mask with fear aura. Centered object, transparent background, 512x512, bold readable silhouette, high contrast, gothic Abyssia style, subtle rim light, cool game UI asset, moderate detail only, readable at Discord emoji size, no text, no letters, no watermark, no character, no full scene.
```

Negative prompt:

```text
text, letters, numbers, watermark, logo, blurry, low contrast, flat circle with letter, simple emoji, cluttered background, cropped object, photorealism, cartoon sticker, generic app icon, UI button text.
```
