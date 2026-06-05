from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Rarity:
    name: str
    weight: float
    stat_multiplier: float
    color: int


@dataclass(frozen=True)
class CreatureTemplate:
    name: str
    rarity: str
    attack: int
    defense: int
    hp: int
    speed: int
    ability: str


@dataclass(frozen=True)
class Zone:
    key: str
    name: str
    required_level: int
    max_rarity: str
    gold: tuple[int, int]
    gems_chance: float
    material_keys: tuple[str, ...]
    flavor: str


@dataclass(frozen=True)
class Equipment:
    key: str
    name: str
    slot: str
    tier: int
    stats: dict[str, int]
    effects: dict[str, float]
    cost: dict[str, int]
    durability: int | None = None


@dataclass(frozen=True)
class Boss:
    key: str
    name: str
    hp: int
    level: int
    material_key: str
    title: str


RARITIES: tuple[Rarity, ...] = (
    Rarity("Common", 5000, 1.00, 0x8b949e),
    Rarity("Uncommon", 3000, 1.12, 0x4ade80),
    Rarity("Rare", 1000, 1.28, 0x38bdf8),
    Rarity("Epic", 100, 1.52, 0xa78bfa),
    Rarity("Legendary", 360, 1.85, 0xfacc15),
    Rarity("Mythic", 165, 2.20, 0xfb7185),
    Rarity("Ancient", 78, 2.65, 0xf97316),
    Rarity("Divine", 38, 3.15, 0xfef3c7),
    Rarity("Eldritch", 18, 3.80, 0x22d3ee),
    Rarity("Abyssal", 8, 4.60, 0x111827),
    Rarity("Prismatic", 2, 5.50, 0x10b981),
    Rarity("Ethereal", 4, 2.40, 0x60a5fa),
    Rarity("Void Lord", 0.5, 4.20, 0x1e3a5f),
    Rarity("Hidden", 0.05, 5.00, 0x9333ea),
)

RARITY_BY_NAME = {rarity.name: rarity for rarity in RARITIES}
RARITY_INDEX = {rarity.name: index for index, rarity in enumerate(RARITIES)}
RARITY_CATCH_RATES: dict[str, float] = {
    "Common": 0.90,
    "Uncommon": 0.45,
    "Rare": 0.15,
    "Epic": 0.05,
    "Legendary": 0.02,
    "Mythic": 0.01,
    "Ancient": 0.005,
    "Divine": 0.002,
    "Eldritch": 0.001,
    "Abyssal": 0.0005,
    "Prismatic": 0.0001,
    "Ethereal": 0.0002,
    "Void Lord": 0.00003,
    "Hidden": 0.00001,
}

CREATURES: tuple[CreatureTemplate, ...] = (
    # ── COMMON ── (basic undead, animals, simple monsters)
    CreatureTemplate("Skeleton", "Common", 8, 4, 22, 8, "Blood Pact"),
    CreatureTemplate("Zombie", "Common", 9, 3, 30, 5, "Soul Drain"),
    CreatureTemplate("Giant Rat", "Common", 6, 4, 18, 14, "Shadow Cloak"),
    CreatureTemplate("Slime", "Common", 5, 6, 26, 4, "Blood Pact"),
    CreatureTemplate("Grave Moth", "Common", 7, 4, 24, 9, "Shadow Cloak"),
    CreatureTemplate("Ribcage Hound", "Common", 9, 5, 28, 7, "Blood Pact"),
    CreatureTemplate("Ash Imp", "Common", 8, 4, 22, 11, "Infernal Rage"),
    CreatureTemplate("Crypt Skitter", "Common", 6, 6, 26, 12, "Shadow Cloak"),
    CreatureTemplate("Lantern Rat", "Common", 7, 3, 20, 16, "Soul Drain"),
    CreatureTemplate("Mourning Toad", "Common", 5, 8, 32, 5, "Blood Pact"),
    # ── UNCOMMON ── (tougher variants)
    CreatureTemplate("Bone Stalker", "Uncommon", 13, 9, 40, 8, "Abyssal Howl"),
    CreatureTemplate("Mire Wisp", "Uncommon", 11, 7, 34, 12, "Soul Drain"),
    CreatureTemplate("Dusk Harrier", "Uncommon", 12, 6, 32, 15, "Shadow Cloak"),
    CreatureTemplate("Briar Ghast", "Uncommon", 12, 10, 42, 9, "Shadow Cloak"),
    CreatureTemplate("Cinder Pup", "Uncommon", 15, 6, 35, 16, "Infernal Rage"),
    CreatureTemplate("Hollow Lynx", "Uncommon", 14, 8, 38, 18, "Abyssal Howl"),
    CreatureTemplate("Sootscale Newt", "Uncommon", 10, 12, 44, 10, "Blood Pact"),
    CreatureTemplate("Ravenous Reliquary", "Uncommon", 13, 13, 46, 7, "Soul Drain"),
    CreatureTemplate("Frozen Shade", "Uncommon", 12, 10, 38, 14, "Void Corruption"),
    CreatureTemplate("Bog Serpent", "Uncommon", 14, 11, 48, 9, "Blood Pact"),
    # ── RARE ──
    CreatureTemplate("Rot Chapel Knight", "Rare", 17, 14, 55, 8, "Blood Pact"),
    CreatureTemplate("Moonless Basilisk", "Rare", 19, 11, 48, 13, "Void Corruption"),
    CreatureTemplate("Thornbound Revenant", "Rare", 16, 16, 62, 7, "Soul Drain"),
    CreatureTemplate("Glassbone Jackal", "Rare", 20, 12, 55, 20, "Shadow Cloak"),
    CreatureTemplate("Marrow Siren", "Rare", 18, 13, 64, 17, "Soul Drain"),
    CreatureTemplate("Coffinback Beetle", "Rare", 16, 22, 80, 8, "Blood Pact"),
    CreatureTemplate("Nocturne Eel", "Rare", 21, 10, 50, 24, "Void Corruption"),
    CreatureTemplate("Ember-Horned Stag", "Rare", 23, 16, 66, 15, "Infernal Rage"),
    CreatureTemplate("Grave Warden", "Rare", 22, 18, 72, 10, "Blood Pact"),
    CreatureTemplate("Plague Doctor", "Rare", 20, 14, 58, 19, "Soul Drain"),
    # ── EPIC ──
    CreatureTemplate("Bloodmoon Drake", "Epic", 25, 18, 78, 15, "Infernal Rage"),
    CreatureTemplate("Witchfire Seraph", "Epic", 27, 15, 70, 18, "Void Corruption"),
    CreatureTemplate("Carrion Oracle", "Epic", 21, 20, 84, 10, "Soul Drain"),
    CreatureTemplate("Gallows Gryphon", "Epic", 29, 19, 86, 22, "Abyssal Howl"),
    CreatureTemplate("Velvet Hexcat", "Epic", 26, 14, 72, 31, "Shadow Cloak"),
    CreatureTemplate("Sable Manticore", "Epic", 32, 20, 92, 18, "Infernal Rage"),
    CreatureTemplate("Choirbone Swan", "Epic", 24, 24, 96, 16, "Soul Drain"),
    CreatureTemplate("Voidglass Angler", "Epic", 28, 17, 82, 25, "Void Corruption"),
    CreatureTemplate("Bone Hydra", "Epic", 30, 16, 88, 20, "Abyssal Howl"),
    CreatureTemplate("Spectre Knight", "Epic", 26, 22, 76, 24, "Shadow Cloak"),
    # ── LEGENDARY ──
    CreatureTemplate("The Pale Chimera", "Legendary", 35, 25, 115, 19, "Abyssal Howl"),
    CreatureTemplate("Gilded Wraith", "Legendary", 33, 22, 98, 27, "Shadow Cloak"),
    CreatureTemplate("Hellroot Colossus", "Legendary", 31, 34, 142, 7, "Blood Pact"),
    CreatureTemplate("Warden of Wax", "Legendary", 38, 35, 155, 13, "Blood Pact"),
    CreatureTemplate("Ebon Antler Saint", "Legendary", 42, 28, 130, 25, "Soul Drain"),
    CreatureTemplate("Crimson Moon Kirin", "Legendary", 45, 24, 122, 34, "Infernal Rage"),
    CreatureTemplate("Sepulcher Leviathan", "Legendary", 39, 38, 180, 12, "Abyssal Howl"),
    CreatureTemplate("Mirror-Eyed Roc", "Legendary", 44, 27, 128, 37, "Void Corruption"),
    CreatureTemplate("Lich King", "Legendary", 40, 32, 140, 21, "Soul Drain"),
    CreatureTemplate("Abyssal Hound", "Legendary", 46, 28, 135, 30, "Infernal Rage"),
    # ── MYTHIC ──
    CreatureTemplate("Soulreaper Wyvern", "Mythic", 45, 33, 150, 25, "Soul Drain"),
    CreatureTemplate("Demon of Black Glass", "Mythic", 49, 29, 136, 31, "Infernal Rage"),
    CreatureTemplate("Choir of Teeth", "Mythic", 42, 38, 168, 17, "Void Corruption"),
    CreatureTemplate("Thorn Queen's Hound", "Mythic", 54, 36, 165, 33, "Shadow Cloak"),
    CreatureTemplate("Black Chalice Hydra", "Mythic", 58, 40, 205, 22, "Soul Drain"),
    CreatureTemplate("Doompetal Phoenix", "Mythic", 62, 32, 155, 42, "Infernal Rage"),
    CreatureTemplate("Silent Bell Kraken", "Mythic", 55, 45, 220, 19, "Abyssal Howl"),
    CreatureTemplate("Void-Thread Spider", "Mythic", 57, 34, 170, 46, "Void Corruption"),
    CreatureTemplate("Infernal Warlord", "Mythic", 60, 42, 190, 28, "Blood Pact"),
    CreatureTemplate("Titan of Rust", "Mythic", 52, 48, 240, 14, "Abyssal Howl"),
    # ── ANCIENT ──
    CreatureTemplate("Ancient Starved Dragon", "Ancient", 62, 47, 225, 30, "Abyssal Howl"),
    CreatureTemplate("Forgotten King", "Ancient", 58, 55, 245, 22, "Blood Pact"),
    CreatureTemplate("First Grave Dragon", "Ancient", 74, 58, 275, 35, "Abyssal Howl"),
    CreatureTemplate("Ashen Oracle Beast", "Ancient", 68, 63, 290, 31, "Soul Drain"),
    CreatureTemplate("The Old Hunger", "Ancient", 78, 54, 265, 42, "Blood Pact"),
    CreatureTemplate("Crownless Sunwyrm", "Ancient", 82, 50, 250, 48, "Infernal Rage"),
    CreatureTemplate("Memory-Eating Hart", "Ancient", 70, 59, 260, 52, "Void Corruption"),
    CreatureTemplate("World Serpent", "Ancient", 76, 60, 310, 38, "Soul Drain"),
    CreatureTemplate("Fallen Star Beast", "Ancient", 80, 52, 270, 44, "Shadow Cloak"),
    # ── DIVINE ──
    CreatureTemplate("Saint of Cinders", "Divine", 72, 61, 280, 34, "Infernal Rage"),
    CreatureTemplate("Dawnless Valkyr", "Divine", 70, 57, 255, 45, "Shadow Cloak"),
    CreatureTemplate("Seraph of Black Rain", "Divine", 88, 69, 315, 44, "Soul Drain"),
    CreatureTemplate("Moonlit Executioner", "Divine", 94, 64, 300, 54, "Shadow Cloak"),
    CreatureTemplate("Saint Hydra of Ash", "Divine", 98, 72, 360, 32, "Infernal Rage"),
    CreatureTemplate("Ivory Void Paladin", "Divine", 90, 80, 340, 40, "Abyssal Howl"),
    CreatureTemplate("Halo-Eater Moth", "Divine", 92, 62, 285, 66, "Void Corruption"),
    CreatureTemplate("Celestial Judge", "Divine", 96, 70, 330, 48, "Blood Pact"),
    # ── ELDRITCH ──
    CreatureTemplate("Eater Beneath Names", "Eldritch", 91, 73, 340, 41, "Void Corruption"),
    CreatureTemplate("Oracle of the Last Door", "Eldritch", 84, 81, 365, 36, "Soul Drain"),
    CreatureTemplate("The Eye Behind Winter", "Eldritch", 108, 88, 410, 52, "Void Corruption"),
    CreatureTemplate("Choirmaster Below", "Eldritch", 102, 96, 440, 44, "Soul Drain"),
    CreatureTemplate("Nameless Thorn Serpent", "Eldritch", 112, 82, 390, 63, "Blood Pact"),
    CreatureTemplate("Lullaby of Knives", "Eldritch", 118, 75, 370, 72, "Shadow Cloak"),
    CreatureTemplate("Apostle of the Deep Door", "Eldritch", 106, 91, 425, 58, "Abyssal Howl"),
    # ── ABYSSAL ──
    CreatureTemplate("Abyssal Godling", "Abyssal", 115, 95, 460, 52, "Abyssal Howl"),
    CreatureTemplate("The Night That Hunts", "Abyssal", 125, 88, 430, 65, "Void Corruption"),
    CreatureTemplate("Godling of Unlit Stars", "Abyssal", 140, 105, 520, 72, "Void Corruption"),
    CreatureTemplate("The Grave That Breathes", "Abyssal", 132, 122, 580, 45, "Blood Pact"),
    CreatureTemplate("Crown of Endless Teeth", "Abyssal", 150, 100, 505, 80, "Infernal Rage"),
    CreatureTemplate("Daughter of No Dawn", "Abyssal", 142, 112, 540, 68, "Soul Drain"),
    # ── PRISMATIC ──
    CreatureTemplate("Spectrum Reaver", "Prismatic", 165, 118, 560, 82, "Void Corruption"),
    CreatureTemplate("Glass Star Phoenix", "Prismatic", 172, 110, 530, 94, "Infernal Rage"),
    CreatureTemplate("Aurora Fang Serpent", "Prismatic", 168, 128, 590, 76, "Abyssal Howl"),
    CreatureTemplate("Chromabone Archon", "Prismatic", 176, 135, 620, 70, "Soul Drain"),
    CreatureTemplate("Prism Maw Leviathan", "Prismatic", 184, 145, 690, 58, "Blood Pact"),
    # ── ETHEREAL ──
    CreatureTemplate("Mistbound Sovereign", "Ethereal", 188, 150, 660, 86, "Soul Drain"),
    CreatureTemplate("Ghostlight Behemoth", "Ethereal", 196, 162, 750, 64, "Abyssal Howl"),
    CreatureTemplate("The Pale Between", "Ethereal", 204, 140, 630, 104, "Shadow Cloak"),
    CreatureTemplate("Warden of Silent Stars", "Ethereal", 210, 172, 780, 72, "Void Corruption"),
    # ── VOID LORD ──
    CreatureTemplate("Void Lord Asterion", "Void Lord", 225, 185, 860, 78, "Abyssal Howl"),
    CreatureTemplate("Black Sun Monarch", "Void Lord", 238, 170, 820, 98, "Infernal Rage"),
    CreatureTemplate("Nameless Void Regent", "Void Lord", 245, 198, 940, 70, "Blood Pact"),
    # ── HIDDEN ──
    CreatureTemplate("The Unlisted Hunger", "Hidden", 270, 220, 1040, 88, "Void Corruption"),
    CreatureTemplate("Secret That Devours Dawn", "Hidden", 290, 240, 1200, 76, "Soul Drain"),
)

ZONES: dict[str, Zone] = {
    "forgotten_woods": Zone("forgotten_woods", "Forgotten Woods", 1, "Rare", (30, 70), 0.08, ("bone_fragments", "corrupted_essence"), "Dead trees whisper old hunting songs."),
    "grave_marsh": Zone("grave_marsh", "Grave Marsh", 3, "Epic", (55, 105), 0.11, ("bone_fragments", "corrupted_essence", "demon_horns"), "Black water hides things that learned to breathe mud."),
    "bloodmoon_forest": Zone("bloodmoon_forest", "Bloodmoon Forest", 6, "Legendary", (85, 160), 0.15, ("corrupted_essence", "demon_horns"), "The moon hangs low enough to bleed on the canopy."),
    "ashen_wastes": Zone("ashen_wastes", "Ashen Wastes", 10, "Mythic", (130, 230), 0.19, ("demon_horns", "void_crystals"), "Every footstep stirs the dust of vanished kingdoms."),
    "infernal_catacombs": Zone("infernal_catacombs", "Infernal Catacombs", 15, "Ancient", (190, 330), 0.23, ("demon_horns", "void_crystals", "ancient_relics"), "The dead below still bargain with flame."),
    "abyssal_depths": Zone("abyssal_depths", "Abyssal Depths", 22, "Eldritch", (275, 470), 0.28, ("void_crystals", "ancient_relics", "abyssal_ichor"), "Pressure, darkness, and hunger become one thing here."),
    "void_realm": Zone("void_realm", "Void Realm", 30, "Abyssal", (390, 680), 0.35, ("void_crystals", "ancient_relics", "abyssal_ichor"), "No horizon. No mercy. Only the hunt."),
    "cursed_sanctum": Zone("cursed_sanctum", "Cursed Sanctum", 38, "Prismatic", (520, 880), 0.39, ("ancient_relics", "abyssal_ichor"), "Candles burn downward and every prayer has claws."),
    "starless_menagerie": Zone("starless_menagerie", "Starless Menagerie", 46, "Ethereal", (680, 1120), 0.43, ("void_crystals", "ancient_relics", "abyssal_ichor"), "Cages hang open, but nothing inside has learned mercy."),
    "throne_of_teeth": Zone("throne_of_teeth", "Throne of Teeth", 58, "Void Lord", (890, 1450), 0.48, ("demon_horns", "ancient_relics", "abyssal_ichor"), "A royal hall made from bite marks, bone, and old crowns."),
    "black_sun_gate": Zone("black_sun_gate", "Black Sun Gate", 72, "Hidden", (1200, 1900), 0.55, ("void_crystals", "ancient_relics", "abyssal_ichor"), "The final gate opens only for hunters the dark recognizes."),
}

MATERIALS: dict[str, str] = {
    "weapon_shards": "Weapon Shards",
}

WEAPON_SHARD_KEY = "weapon_shards"
WEAPON_WEAR_STAGES: tuple[str, ...] = ("Pristine", "Fine", "Decent", "Worn", "Unknown")
WEAPON_WEAR_BONUS: dict[str, int] = {
    "Pristine": 8,
    "Fine": 5,
    "Decent": 2,
    "Worn": 0,
    "Unknown": 0,
}

WEAPON_TYPES: dict[str, dict[str, object]] = {
    "sword": {
        "name": "Sword", "desc": "Balanced blade of steel and shadow.",
        "atk_range": (8, 14), "def_range": (3, 7),
        "passive_pool": ["bleed", "crit"],
    },
    "axe": {
        "name": "Axe", "desc": "Heavy cleaver that splits bone.",
        "atk_range": (12, 20), "def_range": (1, 4),
        "passive_pool": ["bleed", "stun"],
    },
    "dagger": {
        "name": "Dagger", "desc": "Quick strikes from the darkness.",
        "atk_range": (6, 11), "def_range": (2, 5),
        "passive_pool": ["crit", "poison"],
    },
    "staff": {
        "name": "Staff", "desc": "Channels eldritch energy.",
        "atk_range": (7, 13), "def_range": (4, 8),
        "passive_pool": ["burn", "heal"],
    },
    "shield": {
        "name": "Shield", "desc": "Unyielding ward against the void.",
        "atk_range": (2, 5), "def_range": (10, 18),
        "passive_pool": ["shield", "heal"],
    },
    "hammer": {
        "name": "Hammer", "desc": "Crushing force of the abyss.",
        "atk_range": (14, 24), "def_range": (0, 3),
        "passive_pool": ["stun", "bleed"],
    },
}

WEAPON_NAME_PREFIX: list[str] = [
    "Soulreaper", "Bonefang", "Shadowblade", "Voidcleaver",
    "Blood Moon", "Infernal", "Eldritch", "Abyssal",
    "Crystal", "Duskfang", "Grim", "Wraith", "Nightmare",
    "Hex", "Sorrow", "Ash", "Grave", "Obsidian", "Rune",
]
WEAPON_NAME_SUFFIX: dict[str, list[str]] = {
    "sword": ["Blade", "Edge", "Fang", "Kiss", "Fang"],
    "axe": ["Cleaver", "Rend", "Gnaw", "Bite", "Splitter"],
    "dagger": ["Stiletto", "Fang", "Needle", "Whisper", "Shiv"],
    "staff": ["Scepter", "Wand", "Conduit", "Rod", "Spire"],
    "shield": ["Guard", "Bulwark", "Ward", "Aegis", "Bastion"],
    "hammer": ["Maul", "Crusher", "Thunder", "Smasher", "Bonk"],
}

WEAPON_AFFIXES: dict[str, dict[str, object]] = {
    "crit": {"name": "Cruel", "min": 3, "max": 15, "fmt": "+{}% Crit"},
    "life_steal": {"name": "Leeching", "min": 3, "max": 12, "fmt": "+{}% Life Steal"},
    "soul_gain": {"name": "Soulbound", "min": 10, "max": 40, "fmt": "+{}% Soul Gain"},
    "gem_finder": {"name": "Greedy", "min": 8, "max": 30, "fmt": "+{}% Gems"},
    "xp_boost": {"name": "Scholarly", "min": 10, "max": 35, "fmt": "+{}% XP"},
    "attack_pct": {"name": "Might", "min": 5, "max": 20, "fmt": "+{}% ATK"},
    "defense_pct": {"name": "Bulwark", "min": 5, "max": 20, "fmt": "+{}% DEF"},
    "bleed": {"name": "Rending", "min": 5, "max": 20, "fmt": "{}% Bleed"},
    "burn": {"name": "Infernal", "min": 5, "max": 20, "fmt": "{}% Burn"},
    "stun": {"name": "Stunning", "min": 3, "max": 12, "fmt": "{}% Stun"},
    "shield": {"name": "Aegis", "min": 5, "max": 20, "fmt": "{}% Shield"},
    "poison": {"name": "Virulent", "min": 5, "max": 18, "fmt": "{}% Poison"},
    "rare_finder": {"name": "Lucky", "min": 3, "max": 12, "fmt": "+{}% Rare Find"},
    "attack_flat": {"name": "Sharp", "min": 4, "max": 18, "fmt": "+{} ATK"},
    "defense_flat": {"name": "Sturdy", "min": 3, "max": 14, "fmt": "+{} DEF"},
}

WEAPON_QUALITIES: list[dict[str, object]] = [
    {"name": "Normal", "mult": 1.00, "chance": 0.55},
    {"name": "Fine", "mult": 1.12, "chance": 0.25},
    {"name": "Superior", "mult": 1.25, "chance": 0.12},
    {"name": "Masterwork", "mult": 1.40, "chance": 0.06},
    {"name": "Ancient", "mult": 1.55, "chance": 0.02},
]

WEAPON_PASSIVES: dict[str, dict[str, object]] = {
    "bleed": {"name": "Rending", "desc": "Chance to inflict Bleed on hit.", "icon": "🩸"},
    "burn": {"name": "Infernal", "desc": "Chance to inflict Burn on hit.", "icon": "🔥"},
    "poison": {"name": "Virulent", "desc": "Chance to inflict Poison on hit.", "icon": "☠️"},
    "stun": {"name": "Stunning", "desc": "Chance to Stun on hit.", "icon": "⚡"},
    "shield": {"name": "Aegis", "desc": "Chance to gain Shield on hit.", "icon": "🛡️"},
    "heal": {"name": "Lifestream", "desc": "Chance to heal on hit.", "icon": "💚"},
    "crit": {"name": "Precision", "desc": "Increased critical hit chance.", "icon": "💀"},
}

WEAPON_PASSIVE_CHANCE: dict[str, dict[str, int]] = {
    "bleed": {"min": 12, "max": 25},
    "burn": {"min": 12, "max": 25},
    "poison": {"min": 12, "max": 25},
    "stun": {"min": 8, "max": 18},
    "shield": {"min": 10, "max": 22},
    "heal": {"min": 10, "max": 20},
    "crit": {"min": 8, "max": 18},
}

WEAPON_AFFIX_COUNTS: list[int] = [
    0, 0, 1, 1, 2, 2, 3, 3, 3, 4, 4, 3, 4, 4,
]
WEAPON_BASE_ATTACK: list[int] = [
    5, 10, 18, 28, 40, 55, 72, 90, 110, 135, 160, 100, 140, 180,
]
WEAPON_BASE_DEFENSE: list[int] = [
    3, 5, 8, 12, 16, 22, 28, 35, 42, 50, 60, 38, 52, 65,
]

CRATE_TYPES: dict[str, dict[str, object]] = {
    "cache": {
        "name": "Void Cache", "cost": {"gold": 500},
        "desc": "A sealed pouch of eldritch trinkets.",
        "weapon_chance": 1.00,
        "weapon_rarities": ("Common", "Uncommon", "Rare"),
        "gold": (80, 250), "gems": (2, 6), "swords": (1, 3),
        "materials": 2,
    },
    "relic": {
        "name": "Eldritch Relic", "cost": {"gold": 5000, "gems": 30},
        "desc": "Pulsing with trapped souls.",
        "weapon_chance": 1.00,
        "weapon_rarities": ("Uncommon", "Rare", "Epic", "Legendary"),
        "gold": (500, 1500), "gems": (10, 30), "swords": (3, 8),
        "materials": 4,
    },
    "treasure": {
        "name": "Abyssal Treasure", "cost": {"gold": 25000, "gems": 150},
        "desc": "The deep calls to those who open it.",
        "weapon_chance": 1.00,
        "weapon_rarities": ("Rare", "Epic", "Legendary", "Mythic", "Ancient", "Divine", "Eldritch", "Abyssal"),
        "gold": (2000, 6000), "gems": (40, 120), "swords": (8, 20),
        "materials": 6,
    },
}

EQUIPMENT: dict[str, Equipment] = {
    "rusted_sword": Equipment("rusted_sword", "Rusted Sword", "weapon", 1, {"strength": 1}, {}, {}, 100),
    "iron_sword": Equipment("iron_sword", "Iron Sword", "weapon", 2, {"strength": 3}, {"battle_attack": 0.05}, {"bone_fragments": 15, "gold": 200}, 140),
    "darksteel_blade": Equipment("darksteel_blade", "Darksteel Blade", "weapon", 3, {"strength": 6, "dexterity": 2}, {"battle_attack": 0.10}, {"bone_fragments": 25, "corrupted_essence": 15, "gold": 600}, 180),
    "bloodfang_greatsword": Equipment("bloodfang_greatsword", "Bloodfang Greatsword", "weapon", 4, {"strength": 10, "endurance": 3}, {"battle_attack": 0.18}, {"demon_horns": 25, "corrupted_essence": 30, "gold": 1400}, 220),
    "soulreaper": Equipment("soulreaper", "Soulreaper", "weapon", 5, {"strength": 16, "wisdom": 6}, {"battle_attack": 0.26, "catch": 0.05}, {"void_crystals": 25, "ancient_relics": 8, "gold": 3200}, 260),
    "abyssal_cleaver": Equipment("abyssal_cleaver", "Abyssal Cleaver", "weapon", 6, {"strength": 25, "endurance": 10}, {"battle_attack": 0.38, "rarity": 0.08}, {"void_crystals": 45, "ancient_relics": 22, "abyssal_ichor": 10, "gold": 7500}, 320),
    "lucky_charm": Equipment("lucky_charm", "Lucky Charm", "charm", 1, {"luck": 2}, {"gems": 0.08}, {"bone_fragments": 10, "gold": 150}),
    "hunters_sigil": Equipment("hunters_sigil", "Hunter's Sigil", "charm", 2, {"luck": 3, "dexterity": 2}, {"catch": 0.08}, {"bone_fragments": 20, "corrupted_essence": 10, "gold": 500}),
    "demon_eye": Equipment("demon_eye", "Demon Eye", "charm", 3, {"luck": 5, "wisdom": 3}, {"rarity": 0.05}, {"demon_horns": 18, "corrupted_essence": 20, "gold": 1200}),
    "void_talisman": Equipment("void_talisman", "Void Talisman", "charm", 4, {"wisdom": 7, "luck": 7}, {"rarity": 0.09, "autohunt": 0.10}, {"void_crystals": 20, "demon_horns": 20, "gold": 2800}),
    "forgotten_crown": Equipment("forgotten_crown", "Crown of the Forgotten King", "charm", 5, {"wisdom": 12, "luck": 10, "endurance": 5}, {"catch": 0.12, "rarity": 0.12, "gems": 0.15}, {"ancient_relics": 18, "void_crystals": 35, "abyssal_ichor": 5, "gold": 6400}),
}

BOSSES: tuple[Boss, ...] = (
    Boss("hollow_king", "The Hollow King", 45000, 12, "ancient_relics", "Kingbreaker"),
    Boss("mother_of_rot", "Mother of Rot", 62000, 18, "corrupted_essence", "Rotbane"),
    Boss("void_leviathan", "Void Leviathan", 88000, 25, "void_crystals", "Deepbreaker"),
    Boss("nameless_god", "The Nameless God", 130000, 35, "abyssal_ichor", "Godhunter"),
)

QUESTS: dict[str, dict[str, int | str]] = {
    "daily_hunts": {"name": "Complete 5 hunts", "target": 5, "gold": 250, "gems": 5},
    "daily_catches": {"name": "Catch 2 monsters", "target": 2, "gold": 300, "gems": 8},
    "daily_battle": {"name": "Win 1 battle", "target": 1, "gold": 400, "gems": 10},
}

ACHIEVEMENTS: dict[str, tuple[str, str]] = {
    "first_blood": ("First Blood", "Catch your first creature."),
    "ten_hunts": ("Bone Trail", "Complete 10 hunts."),
    "rare_keeper": ("Keeper of Rares", "Catch a Rare or better creature."),
    "arena_victor": ("Arena Victor", "Win a PvP battle."),
    "raid_slayer": ("Raid Slayer", "Help defeat a server raid boss."),
}


def normalize_key(value: str) -> str:
    return value.strip().lower().replace("'", "").replace(" ", "_").replace("-", "_")


def normalize_rarity(value: str | None) -> str | None:
    if not value:
        return None
    key = normalize_key(value)
    aliases = {
        "mythical": "mythic",
        "voidlord": "void_lord",
    }
    key = aliases.get(key, key)
    for rarity in RARITIES:
        if normalize_key(rarity.name) == key:
            return rarity.name
    return None


def catch_rate_for_rarity(value: str | None) -> float:
    rarity = normalize_rarity(value)
    if rarity is None:
        return RARITY_CATCH_RATES["Common"]
    return RARITY_CATCH_RATES.get(rarity, RARITY_CATCH_RATES["Common"])


def _as_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _as_float(value: object, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _as_dict(value: object, fallback: dict[str, int] | dict[str, float]) -> dict:
    return value if isinstance(value, dict) else dict(fallback)


def _as_list(value: object, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(value, str):
        values = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        values = [str(item).strip() for item in value]
    else:
        values = list(fallback)
    return tuple(item for item in values if item)


def _as_int_list(value: object, fallback: list[int]) -> list[int]:
    if not isinstance(value, list):
        return list(fallback)
    return [_as_int(item, fallback[index] if index < len(fallback) else 0) for index, item in enumerate(value)]


def _range_pair(value: object, fallback: tuple[int, int]) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return (_as_int(value[0], fallback[0]), _as_int(value[1], fallback[1]))
    return fallback


def _apply_content_overrides() -> None:
    try:
        from core.content_config import load_config
    except Exception:
        return

    config = load_config()
    overrides = config.get("overrides", {})
    if not isinstance(overrides, dict):
        return
    balancing = config.get("balancing", {})
    if not isinstance(balancing, dict):
        balancing = {}

    global RARITIES, RARITY_BY_NAME, RARITY_INDEX, RARITY_CATCH_RATES
    global CREATURES, ZONES, MATERIALS, EQUIPMENT, BOSSES
    global WEAPON_TYPES, WEAPON_PASSIVES, WEAPON_PASSIVE_CHANCE, WEAPON_AFFIXES
    global WEAPON_QUALITIES, WEAPON_AFFIX_COUNTS, WEAPON_BASE_ATTACK, WEAPON_BASE_DEFENSE
    global CRATE_TYPES, QUESTS, STATUS_EFFECTS, STATUS_EFFECTS_BY_KEY
    global SIGILS, CHARMS, INFUSED_TYPES, INFUSED_WEIGHTS, INFUSED_PREFIXES

    rarity_balance = balancing.get("rarity", {})
    if isinstance(rarity_balance, dict):
        weights = rarity_balance.get("weights", {})
        stat_multipliers = rarity_balance.get("stat_multipliers", {})
        colors = rarity_balance.get("colors", {})
        if not isinstance(weights, dict):
            weights = {}
        if not isinstance(stat_multipliers, dict):
            stat_multipliers = {}
        if not isinstance(colors, dict):
            colors = {}
        RARITIES = tuple(
            Rarity(
                rarity.name,
                _as_float(weights.get(rarity.name), rarity.weight),
                _as_float(stat_multipliers.get(rarity.name), rarity.stat_multiplier),
                _as_int(colors.get(rarity.name), rarity.color),
            )
            for rarity in RARITIES
        )
        RARITY_BY_NAME = {rarity.name: rarity for rarity in RARITIES}
        RARITY_INDEX = {rarity.name: index for index, rarity in enumerate(RARITIES)}

        catch_rates = rarity_balance.get("catch_rates", {})
        if isinstance(catch_rates, dict):
            for raw_name, raw_value in catch_rates.items():
                name = normalize_rarity(str(raw_name)) or str(raw_name)
                RARITY_CATCH_RATES[name] = max(0.0, min(1.0, _as_float(raw_value, RARITY_CATCH_RATES.get(name, 0.0))))

    for key, patch in (overrides.get("materials") or {}).items():
        if not isinstance(patch, dict):
            continue
        safe = normalize_key(str(key))
        if patch.get("deleted"):
            MATERIALS.pop(safe, None)
        else:
            MATERIALS[safe] = str(patch.get("name") or MATERIALS.get(safe) or safe.replace("_", " ").title())

    creature_order = [normalize_key(creature.name) for creature in CREATURES]
    creatures = {normalize_key(creature.name): creature for creature in CREATURES}
    for key, patch in (overrides.get("creatures") or {}).items():
        if not isinstance(patch, dict):
            continue
        safe = normalize_key(str(key))
        if patch.get("deleted"):
            creatures.pop(safe, None)
            continue
        base = creatures.get(safe)
        data = {
            "name": base.name if base else safe.replace("_", " ").title(),
            "rarity": base.rarity if base else "Common",
            "attack": base.attack if base else 10,
            "defense": base.defense if base else 8,
            "hp": base.hp if base else 35,
            "speed": base.speed if base else 10,
            "ability": base.ability if base else "Shadow Cloak",
        }
        data.update({field: value for field, value in patch.items() if field in data})
        if data["rarity"] not in RARITY_BY_NAME:
            data["rarity"] = "Common"
        creatures[safe] = CreatureTemplate(
            str(data["name"]),
            str(data["rarity"]),
            _as_int(data["attack"], 10),
            _as_int(data["defense"], 8),
            _as_int(data["hp"], 35),
            _as_int(data["speed"], 10),
            str(data["ability"]),
        )
        if safe not in creature_order:
            creature_order.append(safe)
    CREATURES = tuple(creatures[key] for key in creature_order if key in creatures)

    zones = dict(ZONES)
    for key, patch in (overrides.get("zones") or {}).items():
        if not isinstance(patch, dict):
            continue
        safe = normalize_key(str(key))
        if patch.get("deleted"):
            zones.pop(safe, None)
            continue
        base = zones.get(safe)
        gold_value = patch.get("gold", base.gold if base else (25, 75))
        if isinstance(gold_value, list) and len(gold_value) >= 2:
            gold = (_as_int(gold_value[0], 25), _as_int(gold_value[1], 75))
        else:
            gold = base.gold if base else (25, 75)
        max_rarity = str(patch.get("max_rarity") or (base.max_rarity if base else "Rare"))
        if max_rarity not in RARITY_BY_NAME:
            max_rarity = "Rare"
        zones[safe] = Zone(
            safe,
            str(patch.get("name") or (base.name if base else safe.replace("_", " ").title())),
            _as_int(patch.get("required_level"), base.required_level if base else 1),
            max_rarity,
            gold,
            _as_float(patch.get("gems_chance"), base.gems_chance if base else 0.08),
            _as_list(patch.get("material_keys"), base.material_keys if base else ("bone_fragments",)),
            str(patch.get("flavor") or (base.flavor if base else "The road ahead is cursed.")),
        )
    ZONES = zones

    equipment = dict(EQUIPMENT)
    for key, patch in (overrides.get("equipment") or {}).items():
        if not isinstance(patch, dict):
            continue
        safe = normalize_key(str(key))
        if patch.get("deleted"):
            equipment.pop(safe, None)
            continue
        base = equipment.get(safe)
        equipment[safe] = Equipment(
            safe,
            str(patch.get("name") or (base.name if base else safe.replace("_", " ").title())),
            str(patch.get("slot") or (base.slot if base else "weapon")),
            _as_int(patch.get("tier"), base.tier if base else 1),
            {str(k): _as_int(v, 0) for k, v in _as_dict(patch.get("stats"), base.stats if base else {}).items()},
            {str(k): _as_float(v, 0.0) for k, v in _as_dict(patch.get("effects"), base.effects if base else {}).items()},
            {str(k): _as_int(v, 0) for k, v in _as_dict(patch.get("cost"), base.cost if base else {}).items()},
            None if patch.get("durability", base.durability if base else None) in {"", None} else _as_int(patch.get("durability"), base.durability if base else 100),
        )
    EQUIPMENT = equipment

    boss_order = [boss.key for boss in BOSSES]
    bosses = {boss.key: boss for boss in BOSSES}
    for key, patch in (overrides.get("bosses") or {}).items():
        if not isinstance(patch, dict):
            continue
        safe = normalize_key(str(key))
        if patch.get("deleted"):
            bosses.pop(safe, None)
            continue
        base = bosses.get(safe)
        bosses[safe] = Boss(
            safe,
            str(patch.get("name") or (base.name if base else safe.replace("_", " ").title())),
            _as_int(patch.get("hp"), base.hp if base else 25000),
            _as_int(patch.get("level"), base.level if base else 10),
            str(patch.get("material_key") or (base.material_key if base else "ancient_relics")),
            str(patch.get("title") or (base.title if base else "Boss Slayer")),
        )
        if safe not in boss_order:
            boss_order.append(safe)
    BOSSES = tuple(bosses[key] for key in boss_order if key in bosses)

    weapon_types = dict(WEAPON_TYPES)
    for key, patch in (overrides.get("weapons") or {}).items():
        if not isinstance(patch, dict):
            continue
        safe = normalize_key(str(key))
        if patch.get("deleted"):
            weapon_types.pop(safe, None)
            continue
        base = weapon_types.get(safe, {})
        weapon_types[safe] = {
            "name": str(patch.get("name") or base.get("name") or safe.replace("_", " ").title()),
            "desc": str(patch.get("desc") or base.get("desc") or ""),
            "atk_range": _range_pair(patch.get("atk_range"), tuple(base.get("atk_range", (1, 3)))),
            "def_range": _range_pair(patch.get("def_range"), tuple(base.get("def_range", (0, 1)))),
            "passive_pool": list(_as_list(patch.get("passive_pool"), tuple(base.get("passive_pool", ())))),
        }
    WEAPON_TYPES = weapon_types

    passives = dict(WEAPON_PASSIVES)
    for key, patch in (overrides.get("passives") or {}).items():
        if not isinstance(patch, dict):
            continue
        safe = normalize_key(str(key))
        if patch.get("deleted"):
            passives.pop(safe, None)
            continue
        base = passives.get(safe, {})
        passives[safe] = {
            "name": str(patch.get("name") or base.get("name") or safe.replace("_", " ").title()),
            "desc": str(patch.get("desc") or base.get("desc") or ""),
            "icon": str(patch.get("icon") or base.get("icon") or ""),
        }
    WEAPON_PASSIVES = passives

    crates = dict(CRATE_TYPES)
    for key, patch in (overrides.get("crate") or {}).items():
        if not isinstance(patch, dict):
            continue
        safe = normalize_key(str(key))
        if patch.get("deleted"):
            crates.pop(safe, None)
            continue
        base = crates.get(safe, {})
        crates[safe] = {
            "name": str(patch.get("name") or base.get("name") or safe.replace("_", " ").title()),
            "desc": str(patch.get("desc") or base.get("desc") or ""),
            "cost": {str(k): _as_int(v, 0) for k, v in _as_dict(patch.get("cost"), base.get("cost", {})).items()},
            "weapon_chance": _as_float(patch.get("weapon_chance"), float(base.get("weapon_chance", 0.0))),
            "weapon_rarities": _as_list(patch.get("weapon_rarities"), tuple(base.get("weapon_rarities", ("Common",)))),
            "gold": _range_pair(patch.get("gold"), tuple(base.get("gold", (0, 0)))),
            "gems": _range_pair(patch.get("gems"), tuple(base.get("gems", (0, 0)))),
            "swords": _range_pair(patch.get("swords"), tuple(base.get("swords", (0, 0)))),
            "materials": _as_int(patch.get("materials"), int(base.get("materials", 0))),
        }
    CRATE_TYPES = crates

    status_order = [effect.key for effect in STATUS_EFFECTS]
    statuses = {effect.key: effect for effect in STATUS_EFFECTS}
    for key, patch in (overrides.get("status") or {}).items():
        if not isinstance(patch, dict):
            continue
        safe = normalize_key(str(key))
        if patch.get("deleted"):
            statuses.pop(safe, None)
            continue
        base = statuses.get(safe)
        statuses[safe] = StatusEffect(
            safe,
            str(patch.get("name") or (base.name if base else safe.replace("_", " ").title())),
            _as_int(patch.get("color"), base.color if base else 0x8b949e),
            str(patch.get("emoji") or (base.emoji if base else "")),
            str(patch.get("desc") or patch.get("description") or (base.description if base else "")),
        )
        if safe not in status_order:
            status_order.append(safe)
    STATUS_EFFECTS = tuple(statuses[key] for key in status_order if key in statuses)
    STATUS_EFFECTS_BY_KEY = {effect.key: effect for effect in STATUS_EFFECTS}

    buff_balance = balancing.get("buffs", {})
    if isinstance(buff_balance, dict):
        sigil_patches = buff_balance.get("sigils", {})
        charm_patches = buff_balance.get("charms", {})
        if isinstance(sigil_patches, dict):
            updated_sigils = []
            for sigil in SIGILS:
                patch = sigil_patches.get(sigil.key, {})
                if not isinstance(patch, dict):
                    patch = {}
                updated_sigils.append(Sigil(
                    sigil.key,
                    str(patch.get("name") or sigil.name),
                    _as_int(patch.get("extra_monsters"), sigil.extra_monsters),
                    _as_int(patch.get("charges"), sigil.charges),
                    _as_int(patch.get("cost_souls"), sigil.cost_souls),
                    _as_int(patch.get("cost_gems"), sigil.cost_gems),
                    str(patch.get("desc") or sigil.desc),
                ))
            SIGILS = tuple(updated_sigils)
        if isinstance(charm_patches, dict):
            updated_charms = []
            for charm in CHARMS:
                patch = charm_patches.get(charm.key, {})
                if not isinstance(patch, dict):
                    patch = {}
                updated_charms.append(Charm(
                    charm.key,
                    str(patch.get("name") or charm.name),
                    _as_float(patch.get("rarity_bonus"), charm.rarity_bonus),
                    _as_int(patch.get("charges"), charm.charges),
                    _as_int(patch.get("cost_souls"), charm.cost_souls),
                    _as_int(patch.get("cost_gems"), charm.cost_gems),
                    str(patch.get("desc") or charm.desc),
                    _as_int(patch.get("extra_monsters"), charm.extra_monsters),
                ))
            CHARMS = tuple(updated_charms)

    weapon_balance = balancing.get("weapons", {})
    if isinstance(weapon_balance, dict):
        passive_chances = weapon_balance.get("passive_chance", {})
        if isinstance(passive_chances, dict):
            for key, patch in passive_chances.items():
                safe = normalize_key(str(key))
                if not isinstance(patch, dict):
                    continue
                base = WEAPON_PASSIVE_CHANCE.get(safe, {"min": 10, "max": 20})
                WEAPON_PASSIVE_CHANCE[safe] = {
                    "min": _as_int(patch.get("min"), int(base.get("min", 10))),
                    "max": _as_int(patch.get("max"), int(base.get("max", 20))),
                }
        quality_chances = weapon_balance.get("quality_chances", {})
        if isinstance(quality_chances, dict):
            for quality in WEAPON_QUALITIES:
                name = str(quality.get("name", ""))
                if name in quality_chances:
                    quality["chance"] = _as_float(quality_chances.get(name), float(quality.get("chance", 0.0)))
        WEAPON_AFFIX_COUNTS = _as_int_list(weapon_balance.get("affix_counts"), WEAPON_AFFIX_COUNTS)
        WEAPON_BASE_ATTACK = _as_int_list(weapon_balance.get("base_attack"), WEAPON_BASE_ATTACK)
        WEAPON_BASE_DEFENSE = _as_int_list(weapon_balance.get("base_defense"), WEAPON_BASE_DEFENSE)

    economy_balance = balancing.get("economy", {})
    if isinstance(economy_balance, dict):
        quest_patches = economy_balance.get("quests", {})
        if isinstance(quest_patches, dict):
            for key, patch in quest_patches.items():
                safe = normalize_key(str(key))
                if not isinstance(patch, dict):
                    continue
                base = QUESTS.get(safe, {})
                QUESTS[safe] = {
                    "name": str(patch.get("name") or base.get("name") or safe.replace("_", " ").title()),
                    "target": _as_int(patch.get("target"), int(base.get("target", 1))),
                    "gold": _as_int(patch.get("gold"), int(base.get("gold", 0))),
                    "gems": _as_int(patch.get("gems"), int(base.get("gems", 0))),
                }

    infused_balance = balancing.get("infused", {})
    if isinstance(infused_balance, dict):
        chance = infused_balance.get("chance")
        types = infused_balance.get("types")
        if isinstance(types, list):
            valid_types = [item for item in types if isinstance(item, dict) and item.get("prefix")]
            if valid_types:
                INFUSED_TYPES = valid_types
                INFUSED_WEIGHTS = [_as_int(i.get("weight"), 1) for i in INFUSED_TYPES]
                INFUSED_PREFIXES = [str(i["prefix"]) for i in INFUSED_TYPES]
        if chance is not None:
            globals()["INFUSED_CHANCE"] = max(0.0, min(1.0, _as_float(chance, globals().get("INFUSED_CHANCE", 0.08))))


def zone_choices() -> str:
    return ", ".join(zone.name for zone in ZONES.values())


def get_color_for_rarity(rarity: str) -> discord.Color:
    import discord

    return discord.Color(RARITY_BY_NAME[rarity].color)


# ── Battle System ──────────────────────────────────────────────────────

ARENA_RANKS = (
    (2600, "Abyssal Lord"),
    (2400, "Grandmaster"),
    (2200, "Master"),
    (2000, "Diamond"),
    (1750, "Platinum"),
    (1500, "Gold"),
    (1250, "Silver"),
    (1050, "Bronze"),
    (0, "Iron"),
)


def arena_rank(rating: int) -> str:
    for threshold, rank in ARENA_RANKS:
        if rating >= threshold:
            return rank
    return "Iron"


STREAK_BONUSES = (
    (50, 0.75),
    (20, 0.35),
    (10, 0.20),
    (5, 0.10),
    (3, 0.05),
    (0, 0.00),
)


def streak_multiplier(streak: int) -> float:
    for need, mult in STREAK_BONUSES:
        if streak >= need:
            return mult
    return 0.0


STREAK_MILESTONES = {
    5: ("Minor Cache", "cache"),
    10: ("Rare Cache", "relic"),
    25: ("Epic Cache", "treasure"),
    50: ("Legendary Cache", "treasure"),
    100: ("Exclusive Title", "title"),
}

BOUNTY_STREAK = 20


# Status Effects
@dataclass(frozen=True)
class StatusEffect:
    """A status effect that can be applied to creatures."""
    key: str
    name: str
    color: int
    emoji: str
    description: str


STATUS_EFFECTS = (
    StatusEffect("bleed", "Bleed", 0xc2185b, "🩸", "Deals damage at end of turn"),
    StatusEffect("burn", "Burn", 0xff6f00, "🔥", "Deals damage at end of turn"),
    StatusEffect("poison", "Poison", 0x7b1fa2, "☠️", "Deals damage at end of turn"),
    StatusEffect("curse", "Curse", 0x1a237e, "👁️", "Reduces damage output"),
    StatusEffect("fear", "Fear", 0x424242, "😨", "Reduces accuracy and damage"),
    StatusEffect("shield", "Shield", 0x0277bd, "🛡️", "Reduces incoming damage"),
    StatusEffect("stun", "Stun", 0xfdd835, "⚡", "Skips next turn"),
    StatusEffect("heal", "Heal", 0x2e7d32, "💚", "Recovers health over time"),
)

STATUS_EFFECTS_BY_KEY = {effect.key: effect for effect in STATUS_EFFECTS}


@dataclass
class NPCCreature:
    name: str
    rarity: str
    attack: int
    defense: int
    hp: int
    speed: int
    crit: int
    mana: int
    ability: str
    level: int


@dataclass
class NPCHunter:
    name: str
    title: str
    min_rating: int
    max_rating: int
    creatures: list[NPCCreature]


NPC_HUNTERS_BEGINNER: list[NPCHunter] = [
    NPCHunter("Gravekeeper Aldric", "Rookie", 0, 1100, [
        NPCCreature("Skeletal Hound", "Common", 28, 18, 160, 24, 5, 35, "Soul Drain", 5),
        NPCCreature("Feral Wraith", "Common", 24, 20, 140, 28, 6, 40, "Shadow Cloak", 5),
        NPCCreature("Bone Reaper", "Common", 32, 14, 120, 22, 4, 30, "Infernal Rage", 5),
    ]),
    NPCHunter("Soul Hunter Kael", "Initiate", 0, 1100, [
        NPCCreature("Dark Hound", "Common", 30, 16, 150, 26, 5, 35, "Infernal Rage", 6),
        NPCCreature("Soul Leech", "Common", 26, 22, 130, 20, 4, 45, "Soul Drain", 6),
        NPCCreature("Shadow Stalker", "Common", 34, 12, 110, 30, 7, 30, "Shadow Cloak", 6),
    ]),
    NPCHunter("The Hollow Knight", "Challenger", 0, 1100, [
        NPCCreature("Hollow Soldier", "Uncommon", 38, 24, 180, 22, 5, 40, "Blood Pact", 8),
        NPCCreature("Cursed Blade", "Uncommon", 42, 18, 160, 28, 6, 35, "Void Corruption", 8),
        NPCCreature("Wailing Spirit", "Common", 34, 20, 140, 32, 7, 45, "Abyssal Howl", 8),
    ]),
]

NPC_HUNTERS_MID: list[NPCHunter] = [
    NPCHunter("Void Apostle", "Veteran", 1100, 1600, [
        NPCCreature("Void Hound", "Uncommon", 55, 32, 240, 30, 6, 50, "Void Corruption", 15),
        NPCCreature("Abyssal Watcher", "Uncommon", 48, 40, 220, 26, 5, 55, "Shadow Cloak", 15),
        NPCCreature("Dusk Reaper", "Rare", 62, 28, 200, 34, 8, 45, "Infernal Rage", 15),
    ]),
    NPCHunter("Ashen Wanderer", "Adept", 1100, 1600, [
        NPCCreature("Ash Golem", "Uncommon", 44, 48, 300, 18, 4, 40, "Blood Pact", 16),
        NPCCreature("Ember Hound", "Rare", 60, 30, 230, 32, 7, 50, "Infernal Rage", 16),
        NPCCreature("Cinder Wraith", "Uncommon", 52, 34, 200, 36, 6, 55, "Soul Drain", 16),
    ]),
    NPCHunter("The Crimson Reaper", "Slayer", 1100, 1600, [
        NPCCreature("Blood Stalker", "Rare", 66, 28, 210, 36, 9, 50, "Soul Drain", 18),
        NPCCreature("Crimson Hound", "Uncommon", 56, 36, 250, 28, 6, 45, "Blood Pact", 18),
        NPCCreature("Night Terror", "Rare", 58, 32, 230, 38, 8, 55, "Abyssal Howl", 18),
    ]),
]

NPC_HUNTERS_END: list[NPCHunter] = [
    NPCHunter("Abyss Lord", "Grandmaster", 1600, 9999, [
        NPCCreature("Void Behemoth", "Rare", 78, 52, 380, 28, 7, 60, "Blood Pact", 28),
        NPCCreature("Shadow Tyrant", "Epic", 92, 44, 340, 34, 9, 65, "Void Corruption", 28),
        NPCCreature("Dusk Monarch", "Epic", 86, 48, 360, 32, 8, 70, "Abyssal Howl", 28),
    ]),
    NPCHunter("Nightmare Weaver", "Legendary", 1600, 9999, [
        NPCCreature("Phantom King", "Epic", 96, 40, 320, 40, 10, 65, "Shadow Cloak", 32),
        NPCCreature("Doom Herald", "Epic", 88, 46, 370, 36, 8, 60, "Infernal Rage", 32),
        NPCCreature("Eternal Void", "Rare", 76, 56, 420, 26, 6, 55, "Soul Drain", 32),
    ]),
    NPCHunter("The First Hunter", "Abyssal Lord", 1600, 9999, [
        NPCCreature("Primordial Wraith", "Epic", 104, 50, 400, 38, 10, 75, "Void Corruption", 35),
        NPCCreature("Ancient Behemoth", "Legendary", 116, 60, 480, 30, 8, 70, "Blood Pact", 35),
        NPCCreature("Void Sovereign", "Epic", 98, 54, 420, 42, 11, 80, "Abyssal Howl", 35),
    ]),
]


def get_npc_pool(rating: int) -> list[NPCHunter]:
    if rating < 1100:
        return NPC_HUNTERS_BEGINNER
    elif rating < 1600:
        return NPC_HUNTERS_BEGINNER + NPC_HUNTERS_MID
    return NPC_HUNTERS_BEGINNER + NPC_HUNTERS_MID + NPC_HUNTERS_END


# ══════════════════════════════════════════════════════════════════
#  SIGILS & CHARMS
# ══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Sigil:
    key: str
    name: str
    extra_monsters: int
    charges: int
    cost_souls: int
    cost_gems: int = 0
    desc: str = ""


SIGILS: tuple[Sigil, ...] = (
    Sigil("lesser_blood", "Lesser Blood Sigil", 2, 5, 1500, 0, "Adds +2 monsters per hunt for 5 hunts."),
    Sigil("greater_blood", "Greater Blood Sigil", 3, 10, 6000, 0, "Adds +3 monsters per hunt for 10 hunts."),
    Sigil("dread_blood", "Dread Blood Sigil", 4, 15, 14000, 0, "Adds +4 monsters per hunt for 15 hunts."),
    Sigil("abyssal_blood", "Abyssal Blood Sigil", 6, 22, 24000, 0, "Adds +6 monsters per hunt for 22 hunts."),
    Sigil("sovereign_blood", "Sovereign Blood Sigil", 8, 30, 50000, 0, "Adds +8 monsters per hunt for 30 hunts."),
)


@dataclass(frozen=True)
class Charm:
    key: str
    name: str
    rarity_bonus: float
    charges: int
    cost_souls: int
    cost_gems: int = 0
    desc: str = ""
    extra_monsters: int = 0


CHARMS: tuple[Charm, ...] = (
    Charm("lesser_void", "Lesser Void Charm", 0.05, 5, 2000, 0, "Adds +2 monsters and improves rare monster odds for 5 hunts.", extra_monsters=2),
    Charm("greater_void", "Greater Void Charm", 0.08, 10, 8000, 0, "Adds +3 monsters and improves rare monster odds for 10 hunts.", extra_monsters=3),
    Charm("deep_void", "Deep Void Charm", 0.12, 15, 16000, 0, "Adds +4 monsters and improves rare monster odds for 15 hunts.", extra_monsters=4),
    Charm("eldritch_void", "Eldritch Void Charm", 0.16, 22, 25000, 0, "Adds +6 monsters and improves rare monster odds for 22 hunts.", extra_monsters=6),
    Charm("singularity_void", "Singularity Void Charm", 0.22, 30, 60000, 0, "Adds +8 monsters and improves rare monster odds for 30 hunts.", extra_monsters=8),
)


# Infused gem variants — applied on top of caught creatures
INFUSED_CHANCE = 0.08
INFUSED_TYPES: list[dict[str, object]] = [
    {"prefix": "Ruby", "multiplier": 1.6, "weight": 50, "color": (235, 60, 80)},
    {"prefix": "Emerald", "multiplier": 2.2, "weight": 25, "color": (60, 210, 120)},
    {"prefix": "Sapphire", "multiplier": 2.8, "weight": 12, "color": (60, 140, 235)},
    {"prefix": "Diamond", "multiplier": 3.5, "weight": 6, "color": (220, 220, 245)},
    {"prefix": "Abyssal", "multiplier": 5.0, "weight": 2, "color": (130, 50, 200)},
]

INFUSED_WEIGHTS: list[int] = [i["weight"] for i in INFUSED_TYPES]
INFUSED_PREFIXES: list[str] = [i["prefix"] for i in INFUSED_TYPES]


def roll_infused() -> dict | None:
    if random.random() < INFUSED_CHANCE:
        return random.choices(INFUSED_TYPES, weights=INFUSED_WEIGHTS, k=1)[0]
    return None


def infused_name(base_name: str, prefix: str) -> str:
    return f"{prefix} {base_name}"


_apply_content_overrides()
