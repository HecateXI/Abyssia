# Abyssia Card Asset Prompts

These records define the reusable premium card UI asset pack. Text must be drawn by the bot, not baked into image assets.

## Workflow

1. Run `python scripts/generate_card_asset_prompts.py` after editing asset records.
2. Use `data/card_asset_prompts.json` to generate final AI assets, or run `python scripts/process_card_assets.py` to create manifest-tracked placeholders.
3. Run `python scripts/process_card_assets.py --force-normalize` after replacing any source PNGs.
4. Run `python scripts/validate_card_assets.py --render-previews` and review `tmp/card_previews/all_cards_contact_sheet.png`.

## Universal Style

Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark.

## Universal Negative Prompt

cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.

## Backgrounds

### abyssia_dark_base

- Output: `assets/ui/backgrounds/abyssia_dark_base.png`
- Purpose: dark violet black base card backdrop with faint void particles
- Size: 1200x720
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssia Dark Base. Purpose: dark violet black base card backdrop with faint void particles. Full rectangular background, no text, no logo, no UI labels. Wide composition, subtle ruins, faint fog, particles, magical depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### abyssia_void_base

- Output: `assets/ui/backgrounds/abyssia_void_base.png`
- Purpose: deep void magic base backdrop with abyssal fog
- Size: 1200x720
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssia Void Base. Purpose: deep void magic base backdrop with abyssal fog. Full rectangular background, no text, no logo, no UI labels. Wide composition, subtle ruins, faint fog, particles, magical depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### abyssia_ruins_base

- Output: `assets/ui/backgrounds/abyssia_ruins_base.png`
- Purpose: ruined gothic stone hall backdrop with subtle fog
- Size: 1200x720
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssia Ruins Base. Purpose: ruined gothic stone hall backdrop with subtle fog. Full rectangular background, no text, no logo, no UI labels. Wide composition, subtle ruins, faint fog, particles, magical depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### abyssia_forge_base

- Output: `assets/ui/backgrounds/abyssia_forge_base.png`
- Purpose: haunted forge backdrop with low ember glow
- Size: 1200x720
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssia Forge Base. Purpose: haunted forge backdrop with low ember glow. Full rectangular background, no text, no logo, no UI labels. Wide composition, subtle ruins, faint fog, particles, magical depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### abyssia_battle_arena_base

- Output: `assets/ui/backgrounds/abyssia_battle_arena_base.png`
- Purpose: battle arena backdrop with distant dungeon architecture
- Size: 1200x720
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssia Battle Arena Base. Purpose: battle arena backdrop with distant dungeon architecture. Full rectangular background, no text, no logo, no UI labels. Wide composition, subtle ruins, faint fog, particles, magical depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### abyssia_hunt_forest_base

- Output: `assets/ui/backgrounds/abyssia_hunt_forest_base.png`
- Purpose: dark haunted forest hunt backdrop
- Size: 1200x720
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssia Hunt Forest Base. Purpose: dark haunted forest hunt backdrop. Full rectangular background, no text, no logo, no UI labels. Wide composition, subtle ruins, faint fog, particles, magical depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### abyssia_crate_shop_base

- Output: `assets/ui/backgrounds/abyssia_crate_shop_base.png`
- Purpose: premium dark fantasy merchant relic shop backdrop with altar table, coins, shards, candlelight, and soft mist
- Size: 1200x720
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssia Crate Shop Base. Purpose: premium dark fantasy merchant relic shop backdrop with altar table, coins, shards, candlelight, and soft mist. Full rectangular background, no text, no logo, no UI labels. Wide composition, subtle ruins, faint fog, particles, magical depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### abyssia_weapon_vault_base

- Output: `assets/ui/backgrounds/abyssia_weapon_vault_base.png`
- Purpose: cursed weapon vault room backdrop with gothic stone arch, chains, candles, relic pedestal, and void mist
- Size: 1200x720
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssia Weapon Vault Base. Purpose: cursed weapon vault room backdrop with gothic stone arch, chains, candles, relic pedestal, and void mist. Full rectangular background, no text, no logo, no UI labels. Wide composition, subtle ruins, faint fog, particles, magical depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### dark_altar_background

- Output: `assets/ui/backgrounds/dark_altar_background.png`
- Purpose: dark altar background with black marble, candles, chains, and sacred ruin depth
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Dark Altar Background. Purpose: dark altar background with black marble, candles, chains, and sacred ruin depth. Full rectangular background, no text, no logo, no UI labels. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### fantasy_shop_table

- Output: `assets/ui/backgrounds/fantasy_shop_table.png`
- Purpose: dark fantasy merchant shop table with coins, shards, candle dust, and premium relic display lighting
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Fantasy Shop Table. Purpose: dark fantasy merchant shop table with coins, shards, candle dust, and premium relic display lighting. Full rectangular background, no text, no logo, no UI labels. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### cursed_vault_arch

- Output: `assets/ui/backgrounds/cursed_vault_arch.png`
- Purpose: cursed vault arch backdrop with gothic stone, chains, candles, and abyssal mist
- Size: 1600x1000
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Cursed Vault Arch. Purpose: cursed vault arch backdrop with gothic stone, chains, candles, and abyssal mist. Full rectangular background, no text, no logo, no UI labels. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### boss_arena_backdrop

- Output: `assets/ui/backgrounds/boss_arena_backdrop.png`
- Purpose: dark fantasy boss arena backdrop with readable left/right staging and dramatic depth
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Boss Arena Backdrop. Purpose: dark fantasy boss arena backdrop with readable left/right staging and dramatic depth. Full rectangular background, no text, no logo, no UI labels. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### battle_arena_backdrop

- Output: `assets/ui/backgrounds/battle_arena_backdrop.png`
- Purpose: battle arena backdrop
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Battle Arena Backdrop. Purpose: battle arena backdrop. Full rectangular background, no text, no logo, no UI labels.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_vault_room_background

- Output: `assets/ui/backgrounds/weapon_vault_room_background.png`
- Purpose: weapon vault room background
- Size: 1200x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Vault Room Background. Purpose: weapon vault room background. Full rectangular background, no text, no logo, no UI labels.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Panels

### gothic_stone_panel

- Output: `assets/ui/panels/gothic_stone_panel.png`
- Purpose: large raised black stone UI panel with carved depth and readable interior
- Size: 900x560
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Gothic Stone Panel. Purpose: large raised black stone UI panel with carved depth and readable interior. Transparent background where useful; keep useful alpha and transparent corners. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### main_panel_dark

- Output: `assets/ui/panels/main_panel_dark.png`
- Purpose: large dark stone/glass content panel
- Size: 900x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Main Panel Dark. Purpose: large dark stone/glass content panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### main_panel_glass

- Output: `assets/ui/panels/main_panel_glass.png`
- Purpose: large translucent dark glass content panel
- Size: 900x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Main Panel Glass. Purpose: large translucent dark glass content panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### small_panel

- Output: `assets/ui/panels/small_panel.png`
- Purpose: compact beveled UI panel
- Size: 420x220
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Small Panel. Purpose: compact beveled UI panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### stat_panel

- Output: `assets/ui/panels/stat_panel.png`
- Purpose: compact stat block panel
- Size: 320x160
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Stat Panel. Purpose: compact stat block panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### item_panel

- Output: `assets/ui/panels/item_panel.png`
- Purpose: item tile panel
- Size: 520x320
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Item Panel. Purpose: item tile panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### tooltip_panel

- Output: `assets/ui/panels/tooltip_panel.png`
- Purpose: tooltip information panel
- Size: 620x360
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Tooltip Panel. Purpose: tooltip information panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### card_slot_panel

- Output: `assets/ui/panels/card_slot_panel.png`
- Purpose: vertical card slot panel
- Size: 360x480
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Card Slot Panel. Purpose: vertical card slot panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### list_row_panel

- Output: `assets/ui/panels/list_row_panel.png`
- Purpose: horizontal list row panel
- Size: 900x120
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: List Row Panel. Purpose: horizontal list row panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### selected_row_panel

- Output: `assets/ui/panels/selected_row_panel.png`
- Purpose: selected list row panel with stronger glow
- Size: 900x120
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Selected Row Panel. Purpose: selected list row panel with stronger glow. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### modal_panel

- Output: `assets/ui/panels/modal_panel.png`
- Purpose: large modal dialog panel
- Size: 960x620
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Modal Panel. Purpose: large modal dialog panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### battle_team_panel_left

- Output: `assets/ui/panels/battle_team_panel_left.png`
- Purpose: left battle team panel
- Size: 620x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Battle Team Panel Left. Purpose: left battle team panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### battle_team_panel_right

- Output: `assets/ui/panels/battle_team_panel_right.png`
- Purpose: right battle team panel
- Size: 620x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Battle Team Panel Right. Purpose: right battle team panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### hunt_dense_row

- Output: `assets/ui/panels/hunt_dense_row.png`
- Purpose: dense hunt row panel
- Size: 900x96
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Hunt Dense Row. Purpose: dense hunt row panel. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Frames

### cursed_gold_frame

- Output: `assets/ui/frames/cursed_gold_frame.png`
- Purpose: ancient cursed gold card frame with engraved trim and premium RPG depth
- Size: 900x560
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Cursed Gold Frame. Purpose: ancient cursed gold card frame with engraved trim and premium RPG depth. Transparent background where useful; keep useful alpha and transparent corners. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### bone_corner_ornaments

- Output: `assets/ui/frames/bone_corner_ornaments.png`
- Purpose: bone and aged gold corner ornament set for gothic reward cards
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Bone Corner Ornaments. Purpose: bone and aged gold corner ornament set for gothic reward cards. Transparent background where useful; keep useful alpha and transparent corners. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_common

- Output: `assets/ui/frames/creature_tile_common.png`
- Purpose: Common creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Common. Purpose: Common creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_uncommon

- Output: `assets/ui/frames/creature_tile_uncommon.png`
- Purpose: Uncommon creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Uncommon. Purpose: Uncommon creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_rare

- Output: `assets/ui/frames/creature_tile_rare.png`
- Purpose: Rare creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Rare. Purpose: Rare creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_epic

- Output: `assets/ui/frames/creature_tile_epic.png`
- Purpose: Epic creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Epic. Purpose: Epic creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_legendary

- Output: `assets/ui/frames/creature_tile_legendary.png`
- Purpose: Legendary creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Legendary. Purpose: Legendary creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_mythic

- Output: `assets/ui/frames/creature_tile_mythic.png`
- Purpose: Mythic creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Mythic. Purpose: Mythic creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_ancient

- Output: `assets/ui/frames/creature_tile_ancient.png`
- Purpose: Ancient creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Ancient. Purpose: Ancient creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_patreon

- Output: `assets/ui/frames/creature_tile_patreon.png`
- Purpose: Patreon creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Patreon. Purpose: Patreon creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_divine

- Output: `assets/ui/frames/creature_tile_divine.png`
- Purpose: Divine creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Divine. Purpose: Divine creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_eldritch

- Output: `assets/ui/frames/creature_tile_eldritch.png`
- Purpose: Eldritch creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Eldritch. Purpose: Eldritch creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_abyssal

- Output: `assets/ui/frames/creature_tile_abyssal.png`
- Purpose: Abyssal creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Abyssal. Purpose: Abyssal creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_prismatic

- Output: `assets/ui/frames/creature_tile_prismatic.png`
- Purpose: Prismatic creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Prismatic. Purpose: Prismatic creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_ethereal

- Output: `assets/ui/frames/creature_tile_ethereal.png`
- Purpose: Ethereal creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Ethereal. Purpose: Ethereal creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_void_lord

- Output: `assets/ui/frames/creature_tile_void_lord.png`
- Purpose: Void Lord creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Void Lord. Purpose: Void Lord creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_tile_hidden

- Output: `assets/ui/frames/creature_tile_hidden.png`
- Purpose: Hidden creature tile frame with portrait/name/badge zones
- Size: 420x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Tile Hidden. Purpose: Hidden creature tile frame with portrait/name/badge zones. Transparent background where useful; keep useful alpha and transparent corners. Supports portrait area, name area, rarity badge area, duplicate/new tag area, subtle 3D depth.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_slot_frame

- Output: `assets/ui/frames/weapon_slot_frame.png`
- Purpose: weapon slot frame for grid cards
- Size: 360x460
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Slot Frame. Purpose: weapon slot frame for grid cards. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_feature_frame

- Output: `assets/ui/frames/weapon_feature_frame.png`
- Purpose: featured weapon display frame
- Size: 620x520
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Feature Frame. Purpose: featured weapon display frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_relic_large_frame

- Output: `assets/ui/frames/weapon_relic_large_frame.png`
- Purpose: large relic tooltip weapon frame
- Size: 520x600
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Relic Large Frame. Purpose: large relic tooltip weapon frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_vault_side_slot

- Output: `assets/ui/frames/weapon_vault_side_slot.png`
- Purpose: weapon vault side slot frame
- Size: 300x320
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Vault Side Slot. Purpose: weapon vault side slot frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_vault_center_display

- Output: `assets/ui/frames/weapon_vault_center_display.png`
- Purpose: weapon vault center information display
- Size: 760x360
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Vault Center Display. Purpose: weapon vault center information display. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### buy_dropdown_frame

- Output: `assets/ui/frames/buy_dropdown_frame.png`
- Purpose: buy dropdown frame
- Size: 520x240
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Buy Dropdown Frame. Purpose: buy dropdown frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### battle_creature_slot

- Output: `assets/ui/frames/battle_creature_slot.png`
- Purpose: battle creature slot frame
- Size: 360x260
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Battle Creature Slot. Purpose: battle creature slot frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### hunt_result_tile

- Output: `assets/ui/frames/hunt_result_tile.png`
- Purpose: hunt result creature tile
- Size: 340x380
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Hunt Result Tile. Purpose: hunt result creature tile. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### hunt_result_tile_selected

- Output: `assets/ui/frames/hunt_result_tile_selected.png`
- Purpose: selected hunt result creature tile
- Size: 340x380
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Hunt Result Tile Selected. Purpose: selected hunt result creature tile. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_vault_side_slot_left

- Output: `assets/ui/frames/weapon_vault_side_slot_left.png`
- Purpose: left side weapon slot
- Size: 300x340
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Vault Side Slot Left. Purpose: left side weapon slot. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_vault_side_slot_right

- Output: `assets/ui/frames/weapon_vault_side_slot_right.png`
- Purpose: right side weapon slot
- Size: 300x340
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Vault Side Slot Right. Purpose: right side weapon slot. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Overlays

### abyssal_mist_overlay

- Output: `assets/ui/overlays/abyssal_mist_overlay.png`
- Purpose: layered abyssal mist and subtle drifting particles for foreground depth
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssal Mist Overlay. Purpose: layered abyssal mist and subtle drifting particles for foreground depth. Transparent background where useful; keep useful alpha and transparent corners. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### foreground_fog

- Output: `assets/ui/overlays/foreground_fog.png`
- Purpose: foreground fog overlay
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Foreground Fog. Purpose: foreground fog overlay. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### void_particles

- Output: `assets/ui/overlays/void_particles.png`
- Purpose: void particles overlay
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Void Particles. Purpose: void particles overlay. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### gold_sparkles

- Output: `assets/ui/overlays/gold_sparkles.png`
- Purpose: gold sparkles overlay
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Gold Sparkles. Purpose: gold sparkles overlay. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### cyan_magic_motes

- Output: `assets/ui/overlays/cyan_magic_motes.png`
- Purpose: cyan magic motes overlay
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Cyan Magic Motes. Purpose: cyan magic motes overlay. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### purple_magic_motes

- Output: `assets/ui/overlays/purple_magic_motes.png`
- Purpose: purple magic motes overlay
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Purple Magic Motes. Purpose: purple magic motes overlay. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### bloodmoon_particles

- Output: `assets/ui/overlays/bloodmoon_particles.png`
- Purpose: bloodmoon particles overlay
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Bloodmoon Particles. Purpose: bloodmoon particles overlay. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### stone_grain_texture

- Output: `assets/ui/overlays/stone_grain_texture.png`
- Purpose: subtle black marble and carved stone grain overlay
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Stone Grain Texture. Purpose: subtle black marble and carved stone grain overlay. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### vignette_overlay

- Output: `assets/ui/overlays/vignette_overlay.png`
- Purpose: vignette overlay
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Vignette Overlay. Purpose: vignette overlay. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### radial_spotlight

- Output: `assets/ui/overlays/radial_spotlight.png`
- Purpose: radial spotlight overlay
- Size: 1200x720
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Radial Spotlight. Purpose: radial spotlight overlay. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Effects

### relic_pedestal

- Output: `assets/ui/effects/relic_pedestal.png`
- Purpose: stone relic pedestal with soft upward void light for featured rewards
- Size: 640x320
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Relic Pedestal. Purpose: stone relic pedestal with soft upward void light for featured rewards. Transparent background where useful; keep useful alpha and transparent corners. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### creature_display_pedestal

- Output: `assets/ui/effects/creature_display_pedestal.png`
- Purpose: collectible creature display pedestal with bone trim and rarity glow
- Size: 560x300
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Creature Display Pedestal. Purpose: collectible creature display pedestal with bone trim and rarity glow. Transparent background where useful; keep useful alpha and transparent corners. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_display_pedestal

- Output: `assets/ui/effects/weapon_display_pedestal.png`
- Purpose: weapon display pedestal with black stone, cursed metal, and upward relic glow
- Size: 560x300
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Display Pedestal. Purpose: weapon display pedestal with black stone, cursed metal, and upward relic glow. Transparent background where useful; keep useful alpha and transparent corners. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### crate_glow_cyan

- Output: `assets/ui/effects/crate_glow_cyan.png`
- Purpose: cyan crate glow effect
- Size: 420x420
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Crate Glow Cyan. Purpose: cyan crate glow effect. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### crate_glow_green

- Output: `assets/ui/effects/crate_glow_green.png`
- Purpose: green crate glow effect
- Size: 420x420
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Crate Glow Green. Purpose: green crate glow effect. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### crate_glow_purple

- Output: `assets/ui/effects/crate_glow_purple.png`
- Purpose: purple crate glow effect
- Size: 420x420
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Crate Glow Purple. Purpose: purple crate glow effect. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_vault_center_pedestal

- Output: `assets/ui/effects/weapon_vault_center_pedestal.png`
- Purpose: center weapon pedestal
- Size: 520x220
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Vault Center Pedestal. Purpose: center weapon pedestal. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_vault_glow

- Output: `assets/ui/effects/weapon_vault_glow.png`
- Purpose: weapon vault central glow
- Size: 640x640
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Vault Glow. Purpose: weapon vault central glow. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Dividers

### rune_divider

- Output: `assets/ui/dividers/rune_divider.png`
- Purpose: carved ancient rune divider in muted gold and void purple
- Size: 900x42
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Rune Divider. Purpose: carved ancient rune divider in muted gold and void purple. Transparent background where useful; keep useful alpha and transparent corners. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### thin_gold_divider

- Output: `assets/ui/dividers/thin_gold_divider.png`
- Purpose: thin gold divider
- Size: 760x18
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Thin Gold Divider. Purpose: thin gold divider. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### cyan_divider

- Output: `assets/ui/dividers/cyan_divider.png`
- Purpose: cyan divider
- Size: 760x24
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Cyan Divider. Purpose: cyan divider. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### purple_divider

- Output: `assets/ui/dividers/purple_divider.png`
- Purpose: purple divider
- Size: 760x24
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Purple Divider. Purpose: purple divider. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Badges

### rarity_gem_badges

- Output: `assets/ui/badges/rarity_gem_badges.png`
- Purpose: large readable rarity gem badge row for crate rewards
- Size: 640x128
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Rarity Gem Badges. Purpose: large readable rarity gem badge row for crate rewards. Transparent background where useful; keep useful alpha and transparent corners. Prioritize carved ancient fantasy materials, strong depth, premium reward-card readability, large focal object support, no sci-fi paneling, no circuit lines, no tiny HUD details.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### battle_center_plaque

- Output: `assets/ui/badges/battle_center_plaque.png`
- Purpose: battle result center plaque
- Size: 520x180
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Battle Center Plaque. Purpose: battle result center plaque. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### victory_banner

- Output: `assets/ui/badges/victory_banner.png`
- Purpose: victory banner frame
- Size: 700x160
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Victory Banner. Purpose: victory banner frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### defeat_banner

- Output: `assets/ui/badges/defeat_banner.png`
- Purpose: defeat banner frame
- Size: 700x160
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Defeat Banner. Purpose: defeat banner frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### tie_banner

- Output: `assets/ui/badges/tie_banner.png`
- Purpose: tie banner frame
- Size: 700x160
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Tie Banner. Purpose: tie banner frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### hunt_header_plate

- Output: `assets/ui/badges/hunt_header_plate.png`
- Purpose: hunt card header plate
- Size: 900x120
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Hunt Header Plate. Purpose: hunt card header plate. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### duplicate_tag

- Output: `assets/ui/badges/duplicate_tag.png`
- Purpose: duplicate result tag
- Size: 220x64
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Duplicate Tag. Purpose: duplicate result tag. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### new_tag

- Output: `assets/ui/badges/new_tag.png`
- Purpose: new discovery tag
- Size: 220x64
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: New Tag. Purpose: new discovery tag. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### quality_badge

- Output: `assets/ui/badges/quality_badge.png`
- Purpose: quality badge
- Size: 260x76
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Quality Badge. Purpose: quality badge. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### mana_badge

- Output: `assets/ui/badges/mana_badge.png`
- Purpose: mana badge
- Size: 260x76
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Mana Badge. Purpose: mana badge. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### level_badge

- Output: `assets/ui/badges/level_badge.png`
- Purpose: level badge
- Size: 260x76
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Level Badge. Purpose: level badge. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### owned_badge

- Output: `assets/ui/badges/owned_badge.png`
- Purpose: owned badge
- Size: 260x76
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Owned Badge. Purpose: owned badge. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### locked_badge

- Output: `assets/ui/badges/locked_badge.png`
- Purpose: locked badge
- Size: 260x76
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Locked Badge. Purpose: locked badge. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Zone Backdrops

### forgotten_woods

- Output: `assets/ui/zone_backdrops/forgotten_woods.png`
- Purpose: Forgotten Woods zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Forgotten Woods. Purpose: Forgotten Woods zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Forgotten Woods; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### grave_marsh

- Output: `assets/ui/zone_backdrops/grave_marsh.png`
- Purpose: Grave Marsh zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Grave Marsh. Purpose: Grave Marsh zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Grave Marsh; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### bloodmoon_forest

- Output: `assets/ui/zone_backdrops/bloodmoon_forest.png`
- Purpose: Bloodmoon Forest zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Bloodmoon Forest. Purpose: Bloodmoon Forest zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Bloodmoon Forest; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### ashen_wastes

- Output: `assets/ui/zone_backdrops/ashen_wastes.png`
- Purpose: Ashen Wastes zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Ashen Wastes. Purpose: Ashen Wastes zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Ashen Wastes; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### infernal_catacombs

- Output: `assets/ui/zone_backdrops/infernal_catacombs.png`
- Purpose: Infernal Catacombs zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Infernal Catacombs. Purpose: Infernal Catacombs zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Infernal Catacombs; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### abyssal_depths

- Output: `assets/ui/zone_backdrops/abyssal_depths.png`
- Purpose: Abyssal Depths zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssal Depths. Purpose: Abyssal Depths zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Abyssal Depths; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### void_realm

- Output: `assets/ui/zone_backdrops/void_realm.png`
- Purpose: Void Realm zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Void Realm. Purpose: Void Realm zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Void Realm; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### cursed_sanctum

- Output: `assets/ui/zone_backdrops/cursed_sanctum.png`
- Purpose: Cursed Sanctum zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Cursed Sanctum. Purpose: Cursed Sanctum zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Cursed Sanctum; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### starless_menagerie

- Output: `assets/ui/zone_backdrops/starless_menagerie.png`
- Purpose: Starless Menagerie zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Starless Menagerie. Purpose: Starless Menagerie zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Starless Menagerie; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### throne_of_teeth

- Output: `assets/ui/zone_backdrops/throne_of_teeth.png`
- Purpose: Throne of Teeth zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Throne Of Teeth. Purpose: Throne of Teeth zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Throne of Teeth; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### black_sun_gate

- Output: `assets/ui/zone_backdrops/black_sun_gate.png`
- Purpose: Black Sun Gate zone backdrop for hunt and bestiary cards
- Size: 1600x900
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Black Sun Gate. Purpose: Black Sun Gate zone backdrop for hunt and bestiary cards. Full rectangular background, no text, no logo, no UI labels. Environmental dark fantasy scene evoking Black Sun Gate; no characters, no UI text.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Rarity Frames

### common

- Output: `assets/ui/rarity_frames/common.png`
- Purpose: Common rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Common. Purpose: Common rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Common rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### uncommon

- Output: `assets/ui/rarity_frames/uncommon.png`
- Purpose: Uncommon rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Uncommon. Purpose: Uncommon rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Uncommon rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### rare

- Output: `assets/ui/rarity_frames/rare.png`
- Purpose: Rare rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Rare. Purpose: Rare rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Rare rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### epic

- Output: `assets/ui/rarity_frames/epic.png`
- Purpose: Epic rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Epic. Purpose: Epic rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Epic rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### legendary

- Output: `assets/ui/rarity_frames/legendary.png`
- Purpose: Legendary rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Legendary. Purpose: Legendary rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Legendary rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### mythic

- Output: `assets/ui/rarity_frames/mythic.png`
- Purpose: Mythic rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Mythic. Purpose: Mythic rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Mythic rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### ancient

- Output: `assets/ui/rarity_frames/ancient.png`
- Purpose: Ancient rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Ancient. Purpose: Ancient rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Ancient rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### patreon

- Output: `assets/ui/rarity_frames/patreon.png`
- Purpose: Patreon rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Patreon. Purpose: Patreon rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Patreon rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### divine

- Output: `assets/ui/rarity_frames/divine.png`
- Purpose: Divine rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Divine. Purpose: Divine rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Divine rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### eldritch

- Output: `assets/ui/rarity_frames/eldritch.png`
- Purpose: Eldritch rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Eldritch. Purpose: Eldritch rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Eldritch rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### abyssal

- Output: `assets/ui/rarity_frames/abyssal.png`
- Purpose: Abyssal rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Abyssal. Purpose: Abyssal rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Abyssal rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### prismatic

- Output: `assets/ui/rarity_frames/prismatic.png`
- Purpose: Prismatic rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Prismatic. Purpose: Prismatic rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Prismatic rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### ethereal

- Output: `assets/ui/rarity_frames/ethereal.png`
- Purpose: Ethereal rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Ethereal. Purpose: Ethereal rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Ethereal rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### void_lord

- Output: `assets/ui/rarity_frames/void_lord.png`
- Purpose: Void Lord rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Void Lord. Purpose: Void Lord rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Void Lord rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### hidden

- Output: `assets/ui/rarity_frames/hidden.png`
- Purpose: Hidden rarity frame for creature, weapon, and item tiles
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Hidden. Purpose: Hidden rarity frame for creature, weapon, and item tiles. Transparent background where useful; keep useful alpha and transparent corners. Consistent frame shape; material and glow should clearly signal Hidden rarity.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Card Templates

### crate_shop_panel

- Output: `assets/ui/card_templates/crate_shop_panel.png`
- Purpose: full crate shop card base panel
- Size: 1200x720
- Transparent: false

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Crate Shop Panel. Purpose: full crate shop card base panel. Full rectangular background, no text, no logo, no UI labels.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### crate_shop_card_void_cache

- Output: `assets/ui/card_templates/crate_shop_card_void_cache.png`
- Purpose: void cache shop card frame
- Size: 360x480
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Crate Shop Card Void Cache. Purpose: void cache shop card frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### crate_shop_card_eldritch_relic

- Output: `assets/ui/card_templates/crate_shop_card_eldritch_relic.png`
- Purpose: eldritch relic shop card frame
- Size: 360x480
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Crate Shop Card Eldritch Relic. Purpose: eldritch relic shop card frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### crate_shop_card_abyssal_treasure

- Output: `assets/ui/card_templates/crate_shop_card_abyssal_treasure.png`
- Purpose: abyssal treasure shop card frame
- Size: 360x480
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Crate Shop Card Abyssal Treasure. Purpose: abyssal treasure shop card frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Buttons

### price_button

- Output: `assets/ui/buttons/price_button.png`
- Purpose: readable price button frame
- Size: 320x96
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Price Button. Purpose: readable price button frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_vault_filter_button

- Output: `assets/ui/buttons/weapon_vault_filter_button.png`
- Purpose: weapon vault filter button
- Size: 220x72
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Vault Filter Button. Purpose: weapon vault filter button. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Bars

### hp_bar_frame

- Output: `assets/ui/bars/hp_bar_frame.png`
- Purpose: HP bar frame
- Size: 520x64
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Hp Bar Frame. Purpose: HP bar frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### mana_bar_frame

- Output: `assets/ui/bars/mana_bar_frame.png`
- Purpose: mana bar frame
- Size: 520x64
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Mana Bar Frame. Purpose: mana bar frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### boss_hp_bar_frame

- Output: `assets/ui/bars/boss_hp_bar_frame.png`
- Purpose: boss HP bar frame
- Size: 900x80
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Boss Hp Bar Frame. Purpose: boss HP bar frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### weapon_vault_page_bar

- Output: `assets/ui/bars/weapon_vault_page_bar.png`
- Purpose: weapon vault page bar
- Size: 900x64
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Weapon Vault Page Bar. Purpose: weapon vault page bar. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### hp_bar_fill

- Output: `assets/ui/bars/hp_bar_fill.png`
- Purpose: HP bar fill
- Size: 520x36
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Hp Bar Fill. Purpose: HP bar fill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### mana_bar_fill

- Output: `assets/ui/bars/mana_bar_fill.png`
- Purpose: mana bar fill
- Size: 520x36
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Mana Bar Fill. Purpose: mana bar fill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### xp_bar_fill

- Output: `assets/ui/bars/xp_bar_fill.png`
- Purpose: XP bar fill
- Size: 520x36
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Xp Bar Fill. Purpose: XP bar fill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### quality_bar_fill

- Output: `assets/ui/bars/quality_bar_fill.png`
- Purpose: quality bar fill
- Size: 520x36
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Quality Bar Fill. Purpose: quality bar fill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### progress_bar_frame

- Output: `assets/ui/bars/progress_bar_frame.png`
- Purpose: progress bar frame
- Size: 620x64
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Progress Bar Frame. Purpose: progress bar frame. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Reward Pills

### souls_pill

- Output: `assets/ui/reward_pills/souls_pill.png`
- Purpose: souls reward pill
- Size: 320x88
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Souls Pill. Purpose: souls reward pill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### xp_pill

- Output: `assets/ui/reward_pills/xp_pill.png`
- Purpose: XP reward pill
- Size: 320x88
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Xp Pill. Purpose: XP reward pill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### crate_reward_pill

- Output: `assets/ui/reward_pills/crate_reward_pill.png`
- Purpose: crate reward pill
- Size: 360x88
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Crate Reward Pill. Purpose: crate reward pill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### reward_pill_souls

- Output: `assets/ui/reward_pills/reward_pill_souls.png`
- Purpose: souls reward pill
- Size: 360x90
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Reward Pill Souls. Purpose: souls reward pill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### reward_pill_xp

- Output: `assets/ui/reward_pills/reward_pill_xp.png`
- Purpose: XP reward pill
- Size: 360x90
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Reward Pill Xp. Purpose: XP reward pill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### reward_pill_weapon_shards

- Output: `assets/ui/reward_pills/reward_pill_weapon_shards.png`
- Purpose: weapon shards reward pill
- Size: 360x90
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Reward Pill Weapon Shards. Purpose: weapon shards reward pill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

### reward_pill_crate

- Output: `assets/ui/reward_pills/reward_pill_crate.png`
- Purpose: crate reward pill
- Size: 360x90
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Reward Pill Crate. Purpose: crate reward pill. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```

## Placeholders

### missing_card_asset

- Output: `assets/ui/placeholders/missing_card_asset.png`
- Purpose: fallback placeholder for missing card assets
- Size: 512x512
- Transparent: true

Prompt:

```text
Premium gothic dark fantasy RPG UI asset for Abyssia, black stone, cursed metal, bone ornamentation, abyssal mist, relic pedestal lighting, engraved ancient gold trim, subtle void glow, purple abyss glow, 3D layered game card depth, readable Discord card scale, carved, ancient, mystical, cursed, dimensional, not sci-fi, not cyberpunk, no circuit board lines, no tiny HUD text, no text, no letters, no watermark. Asset: Missing Card Asset. Purpose: fallback placeholder for missing card assets. Transparent background where useful; keep useful alpha and transparent corners.
```

Negative prompt:

```text
cyberpunk, sci-fi HUD, circuit lines, terminal UI, robotic, spaceship, flat neon rectangle, tiny text, microtext, cluttered interface, low readability, text, letters, numbers, watermark, logo, blurry, cheap flat UI, plain rectangle, overexposed glow, cropped edges, photorealistic object, cartoon sticker, low-resolution artifact.
```
