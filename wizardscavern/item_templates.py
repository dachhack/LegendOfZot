"""Item template data for Wizard's Cavern."""
from .items import (
    Item, Potion, Ingredient, Trophy, Rune, Shard,
    Weapon, Armor, Scroll, Flare, Lantern, LanternFuel,
    Food, Meat, CookingKit, Treasure, Towel, Spell, LembasWafer,
)


# ================================================================================
# POTION RECIPES (Alchemy crafting data)
# ================================================================================

POTION_RECIPES = {
    # ============================================================
    # TIER 1: BASIC POTIONS (Common ingredients)
    # ============================================================

    'Healing Potion': {
        'ingredients': [('Moonpetal', 2), ('Healing Moss', 1)],
        'tier': 1,
        'result': lambda: Potion(name="Healing Potion", potion_type='healing', effect_magnitude=50, value=50, level=1, description="Restores 50 HP")
    },
    'Mana Potion': {
        'ingredients': [('Starbloom', 2), ('Healing Moss', 1)],
        'tier': 1,
        'result': lambda: Potion(name="Mana Potion", potion_type='mana', effect_magnitude=40, value=50, level=1, description="Restores 40 Mana")
    },
    'Antidote': {
        'ingredients': [('Healing Moss', 3), ('Moonpetal', 1)],
        'tier': 1,
        'result': lambda: Potion(name="Antidote", potion_type='cure_all', effect_magnitude=0, value=100, level=1, description="Cures all negative status effects")
    },

    # ============================================================
    # TIER 2: INTERMEDIATE POTIONS (Common + Uncommon)
    # ============================================================

    'Greater Healing Potion': {
        'ingredients': [('Moonpetal', 3), ('Crystal Dew', 2)],
        'tier': 2,
        'result': lambda: Potion(name="Greater Healing Potion", potion_type='healing', effect_magnitude=100, value=100, level=2, description="Restores 100 HP")
    },
    'Greater Mana Potion': {
        'ingredients': [('Starbloom', 3), ('Essence Vial', 2)],
        'tier': 2,
        'result': lambda: Potion(name="Greater Mana Potion", potion_type='mana', effect_magnitude=80, value=100, level=2, description="Restores 80 Mana")
    },
    'Strength Elixir': {
        'ingredients': [('Fire Root', 3), ('Shadow Leaf', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Strength Elixir", potion_type='strength', effect_magnitude=5, duration=5, value=75, level=2, description="+5 Attack for 5 turns")
    },
    'Dexterity Tonic': {
        'ingredients': [('Shadow Leaf', 3), ('Starbloom', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Dexterity Tonic", potion_type='dexterity', effect_magnitude=5, duration=5, value=75, level=2, description="+5 Dexterity for 5 turns")
    },
    'Intelligence Brew': {
        'ingredients': [('Starbloom', 3), ('Crystal Dew', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Intelligence Brew", potion_type='intelligence', effect_magnitude=5, duration=5, value=75, level=2, description="+5 Intelligence for 5 turns")
    },
    'Defense Brew': {
        'ingredients': [('Healing Moss', 3), ('Shadow Leaf', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Defense Brew", potion_type='defense', effect_magnitude=5, duration=5, value=75, level=2, description="+5 Defense for 5 turns")
    },
    'Regeneration Potion': {
        'ingredients': [('Moonpetal', 2), ('Healing Moss', 2), ('Crystal Dew', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Regeneration Potion", potion_type='regeneration', effect_magnitude=10, duration=5, value=80, level=2, description="Restore 10 HP per turn for 5 turns")
    },

    # ============================================================
    # TIER 3: ADVANCED POTIONS (Uncommon + Rare)
    # ============================================================

    'Berserker Rage': {
        'ingredients': [('Fire Root', 3), ('Dragon Scale', 1), ('Shadow Leaf', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Berserker Rage", potion_type='berserker', effect_magnitude=100, duration=3, value=150, level=3, description="Double attack, -50% defense for 3 turns")
    },
    'Giant\'s Might': {
        'ingredients': [('Dragon Scale', 2), ('Iron Bark', 1), ('Fire Root', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Giant's Might", potion_type='giant_strength', effect_magnitude=10, duration=4, value=150, level=3, description="+10 Strength for 4 turns")
    },
    'Haste Potion': {
        'ingredients': [('Quicksilver Drop', 2), ('Shadow Leaf', 2), ('Essence Vial', 1)],
        'tier': 3,
        'result': lambda: Potion(name="Haste Potion", potion_type='haste', effect_magnitude=1, duration=3, value=150, level=3, description="Extra actions for 3 turns")
    },
    'Stone Skin': {
        'ingredients': [('Iron Bark', 2), ('Stone Flower', 2), ('Healing Moss', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Stone Skin", potion_type='stone_skin', effect_magnitude=50, duration=5, value=150, level=3, description="50% damage reduction for 5 turns")
    },
    'Invisibility Potion': {
        'ingredients': [('Shadow Leaf', 4), ('Essence Vial', 2), ('Quicksilver Drop', 1)],
        'tier': 3,
        'result': lambda: Potion(name="Invisibility Potion", potion_type='invisibility', effect_magnitude=0, duration=3, value=175, level=3, description="Enemies cannot attack you for 3 turns")
    },
    'True Sight': {
        'ingredients': [('Wisdom Moss', 2), ('Starbloom', 3), ('Crystal Dew', 2)],
        'tier': 3,
        'result': lambda: Potion(name="True Sight", potion_type='true_sight', effect_magnitude=0, duration=5, value=150, level=3, description="Reveal hidden enemies and secrets for 5 turns")
    },
    'Fortune Brew': {
        'ingredients': [('Crystal Dew', 3), ('Essence Vial', 2), ('Moonpetal', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Fortune Brew", potion_type='fortune', effect_magnitude=50, duration=5, value=150, level=3, description="+50% gold drops for 5 turns")
    },
    'Experience Elixir': {
        'ingredients': [('Wisdom Moss', 2), ('Essence Vial', 2), ('Starbloom', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Experience Elixir", potion_type='experience', effect_magnitude=50, duration=5, value=150, level=3, description="+50% XP gain for 5 turns")
    },
    'Vampiric Elixir': {
        'ingredients': [('Dragon Scale', 1), ('Shadow Leaf', 3), ('Fire Root', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Vampiric Elixir", potion_type='vampirism', effect_magnitude=30, duration=5, value=175, level=3, description="Lifesteal 30% of damage dealt for 5 turns")
    },
    'Frost Armor': {
        'ingredients': [('Crystal Dew', 3), ('Essence Vial', 2), ('Shadow Leaf', 1)],
        'tier': 3,
        'result': lambda: Potion(name="Frost Armor", potion_type='frost_armor', effect_magnitude=15, duration=5, value=150, level=3, description="Reflect 15 ice damage to attackers for 5 turns")
    },
    'Clarity Potion': {
        'ingredients': [('Wisdom Moss', 2), ('Starbloom', 2), ('Moonpetal', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Clarity Potion", potion_type='clarity', effect_magnitude=0, duration=0, value=125, level=3, description="Remove confusion, slow, curse, weakness. Restore 30 mana.")
    },

    # ============================================================
    # TIER 4: LEGENDARY POTIONS - PERMANENT STAT INCREASES
    # ============================================================

    'Elixir of Might': {
        'ingredients': [('Dragon Scale', 3), ('Iron Bark', 2), ('Fire Root', 4)],
        'tier': 4,
        'result': lambda: Potion(name="Elixir of Might", potion_type='permanent_strength', effect_magnitude=2, value=250, level=4, description="~~~ PERMANENT: +2 Strength forever")
    },
    'Potion of Swiftness': {
        'ingredients': [('Quicksilver Drop', 3), ('Shadow Leaf', 4), ('Essence Vial', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Potion of Swiftness", potion_type='permanent_dexterity', effect_magnitude=2, value=250, level=4, description="~~~ PERMANENT: +2 Dexterity forever")
    },
    'Draught of Brilliance': {
        'ingredients': [('Wisdom Moss', 3), ('Starbloom', 4), ('Crystal Dew', 3)],
        'tier': 4,
        'result': lambda: Potion(name="Draught of Brilliance", potion_type='permanent_intelligence', effect_magnitude=2, value=250, level=4, description="~~~ PERMANENT: +2 Intelligence forever")
    },
    'Potion of Fortitude': {
        'ingredients': [('Dragon Scale', 2), ('Moonpetal', 5), ('Crystal Dew', 3)],
        'tier': 4,
        'result': lambda: Potion(name="Potion of Fortitude", potion_type='permanent_health', effect_magnitude=20, value=300, level=4, description="~~~ PERMANENT: +20 Max HP forever")
    },
    'Essence of Resilience': {
        'ingredients': [('Iron Bark', 3), ('Stone Flower', 3), ('Dragon Scale', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Essence of Resilience", potion_type='permanent_defense', effect_magnitude=2, value=250, level=4, description="~~~ PERMANENT: +2 Defense forever")
    },

    # ============================================================
    # TIER 4: LEGENDARY POTIONS - PERMANENT ELEMENTAL RESISTANCE
    # ============================================================

    'Fireward Elixir': {
        'ingredients': [('Fire Root', 5), ('Dragon Scale', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Fireward Elixir", potion_type='resistance_fire', resistance_element='Fire', value=200, level=4, description="~~~ PERMANENT: Fire Resistance forever")
    },
    'Frostward Tonic': {
        'ingredients': [('Crystal Dew', 5), ('Essence Vial', 3)],
        'tier': 4,
        'result': lambda: Potion(name="Frostward Tonic", potion_type='resistance_ice', resistance_element='Ice', value=200, level=4, description="~~~ PERMANENT: Ice Resistance forever")
    },
    'Stormward Brew': {
        'ingredients': [('Quicksilver Drop', 4), ('Essence Vial', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Stormward Brew", potion_type='resistance_lightning', resistance_element='Lightning', value=200, level=4, description="~~~ PERMANENT: Lightning Resistance forever")
    },
    'Shadowward Potion': {
        'ingredients': [('Shadow Leaf', 5), ('Wisdom Moss', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Shadowward Potion", potion_type='resistance_darkness', resistance_element='Darkness', value=200, level=4, description="~~~ PERMANENT: Darkness Resistance forever")
    },
    'Lightward Essence': {
        'ingredients': [('Starbloom', 5), ('Moonpetal', 4)],
        'tier': 4,
        'result': lambda: Potion(name="Lightward Essence", potion_type='resistance_light', resistance_element='Light', value=200, level=4, description="~~~ PERMANENT: Light Resistance forever")
    },

    # ============================================================
    # TIER 5: ULTIMATE POTION - ALL ELEMENTAL RESISTANCE
    # ============================================================

    'Prismatic Elixir': {
        'ingredients': [
            ('Dragon Scale', 5),
            ('Fire Root', 5),
            ('Crystal Dew', 5),
            ('Quicksilver Drop', 5),
            ('Shadow Leaf', 5),
            ('Starbloom', 5),
            ('Wisdom Moss', 3),
            ('Essence Vial', 3)
        ],
        'tier': 5,
        'result': lambda: Potion(name="Prismatic Elixir", potion_type='resistance_all', value=1000, level=5, description="~~~ PERMANENT: ALL Elemental Resistances forever! ~~~")
    },
}

# ============================================================================
# LEMBAS RECIPES (Elf-only): Garden ingredients + Rations -> Lembas Wafer
# Each recipe requires garden herbs plus one Ration to bake into lembas.
# ============================================================================
LEMBAS_RECIPES = {
    'Lembas Wafer (Moonpetal)': {
        'ingredients': [('Moonpetal', 2), ('Healing Moss', 1)],
        'ration_cost': 1,
        'tier': 1,
        'result': lambda: LembasWafer(),
    },
    'Lembas Wafer (Starbloom)': {
        'ingredients': [('Starbloom', 2), ('Crystal Dew', 1)],
        'ration_cost': 1,
        'tier': 2,
        'result': lambda: LembasWafer(),
    },
    'Lembas Wafer (Herbal)': {
        'ingredients': [('Fire Root', 1), ('Shadow Leaf', 1), ('Moonpetal', 1)],
        'ration_cost': 1,
        'tier': 2,
        'result': lambda: LembasWafer(),
    },
}

# ============================================================================
# MINING INGREDIENTS (Dwarf mining loot)
# ============================================================================
MINING_INGREDIENTS = [
    # Common (60%)
    ('Iron Chunk', 'A rough piece of iron ore', 8, 1, 0.20),
    ('Copper Nugget', 'A small nugget of gleaming copper', 6, 1, 0.20),
    ('Stone Shard', 'A sharp fragment of cave stone', 4, 1, 0.20),
    # Uncommon (30%)
    ('Silver Vein', 'A thin strip of pure silver', 15, 2, 0.12),
    ('Gold Flake', 'A glittering flake of gold', 20, 2, 0.10),
    ('Coal Ember', 'A smoldering piece of deep coal', 10, 2, 0.08),
    # Rare (10%)
    ('Mithril Shard', 'A sliver of the legendary metal, light as air', 50, 4, 0.04),
    ('Ruby Fragment', 'A rough ruby shard pulsing with inner fire', 40, 3, 0.03),
    ('Diamond Chip', 'A tiny but brilliant diamond chip', 60, 5, 0.02),
    ('Adamantine Dust', 'Dust from the hardest substance known', 75, 5, 0.01),
]

# ============================================================================
# DWARVEN RECIPES (Dwarf-only): Mining ingredients -> Ioun Stone accessories
# Inspired by D&D Ioun Stones — orbiting gemstones that grant passive bonuses.
# Equip in accessory slots for permanent stat boosts while worn.
# ============================================================================
DWARVEN_RECIPES = {
    'Ioun Stone of Fortitude': {
        'ingredients': [('Iron Chunk', 4), ('Copper Nugget', 3)],
        'tier': 1,
        'result': lambda: Treasure(
            name="Ioun Stone of Fortitude",
            description="A deep red rhomboid that orbits your head, pulsing with earthy vitality.",
            gold_value=60, value=60, level=2,
            treasure_type='passive',
            passive_effect="+10 Max HP, +2 Defense",
        ),
    },
    'Ioun Stone of Might': {
        'ingredients': [('Silver Vein', 3), ('Coal Ember', 2)],
        'tier': 2,
        'result': lambda: Treasure(
            name="Ioun Stone of Might",
            description="A pale blue rhomboid that orbits your head, humming with raw power.",
            gold_value=80, value=80, level=3,
            treasure_type='passive',
            passive_effect="+3 Strength, +3 Attack",
        ),
    },
    'Ioun Stone of Agility': {
        'ingredients': [('Mithril Shard', 2), ('Gold Flake', 3)],
        'tier': 3,
        'result': lambda: Treasure(
            name="Ioun Stone of Agility",
            description="A shimmering emerald sphere that orbits your head in quick, darting loops.",
            gold_value=120, value=120, level=4,
            treasure_type='passive',
            passive_effect="+4 Dexterity",
        ),
    },
    'Ioun Stone of Mastery': {
        'ingredients': [('Ruby Fragment', 2), ('Diamond Chip', 1), ('Adamantine Dust', 1)],
        'tier': 4,
        'result': lambda: Treasure(
            name="Ioun Stone of Mastery",
            description="A brilliant prismatic spindle that orbits your head, refracting light into rainbows.",
            gold_value=200, value=200, level=5,
            treasure_type='passive',
            passive_effect="+3 Str/Dex/Int, +15 Max HP",
        ),
    },
}

# Available garden ingredients with spawn chances
GARDEN_INGREDIENTS = [
    # Common (60% chance)
    ('Moonpetal', 'A silver flower that glows faintly in darkness', 5, 1, 0.15),
    ('Starbloom', 'A blue flower dotted with tiny glowing specks', 8, 1, 0.15),
    ('Healing Moss', 'Soft green moss with regenerative properties', 5, 1, 0.15),
    ('Fire Root', 'A red root that is warm to the touch', 7, 1, 0.15),
    # Uncommon (30% chance)
    ('Shadow Leaf', 'A dark leaf that seems to absorb light', 10, 2, 0.10),
    ('Crystal Dew', 'Crystallized morning dew with magical properties', 12, 2, 0.10),
    ('Essence Vial', 'A small vial of concentrated magical essence', 15, 2, 0.10),
    # Rare (10% chance)
    ('Dragon Scale', 'A shimmering scale from a mighty dragon', 25, 3, 0.03),
    ('Iron Bark', 'Bark from an ancient ironwood tree', 20, 3, 0.02),
    ('Wisdom Moss', 'Rare moss said to enhance mental clarity', 20, 3, 0.02),
    ('Stone Flower', 'A flower as hard as granite', 18, 3, 0.02),
    ('Quicksilver Drop', 'A drop of liquid mercury-like substance', 22, 3, 0.01)
]

# Dictionary for easy lookup
GARDEN_INGREDIENTS_DICT = {
    name: {'description': desc, 'value': value, 'level': level, 'chance': chance}
    for name, desc, value, level, chance in GARDEN_INGREDIENTS
}

# Fey Garden ingredients (rare, high-level)
FEY_GARDEN_INGREDIENTS = [
    ('Fey Blossom', 'A flower from the realm between worlds, shimmering with otherworldly light', 50, 5, 0.20),
    ('Ethereal Moss', 'Translucent moss that phases in and out of existence', 45, 5, 0.20),
    ('Starfall Dust', 'Crystallized essence of fallen stars', 60, 6, 0.15),
    ('Phoenix Feather', 'A feather still warm with eternal flame', 75, 6, 0.12),
    ('Unicorn Tear', 'A single perfect drop of pure magical essence', 80, 7, 0.10),
    ('Dragon Heart Root', 'A root pulsing with draconic vitality', 70, 6, 0.10),
    ('Moonwell Water', 'Water blessed by a thousand full moons', 55, 5, 0.08),
    ('Void Essence', 'A fragment of the space between dimensions', 100, 8, 0.05),
]


# ================================================================================
# HUNGER SYSTEM CONSTANTS
# ================================================================================

# Monster meat descriptors for cooked forms
MEAT_COOK_STYLES = {
    "Goblin":     ("burger",    "barely palatable",  5),
    "Orc":        ("steak",     "tough and gamey",   7),
    "Rat":        ("nuggets",   "surprisingly edible", 8),
    "Bat":        ("kebab",     "chewy",              9),
    "Spider":     ("skewer",    "oddly crunchy",     2),
    "Troll":      ("burger",    "rubbery but filling", 20),
    "Ogre":       ("roast",     "pungent but hearty", 22),
    "Gnoll":      ("burger",    "gamey",             15),
    "Centipede":  ("filet",     "questionable",       4),
    "Lizard":     ("filet",     "surprisingly delicious", 14),
    "Kobold":     ("cold cuts", "sinewy",            10),
    "Minotaur":   ("burger",    "yummy",             25),
    "Werewolf":   ("steak",     "wild and savory",   22),
    "Wyvern":     ("filet",     "rich and dragonlike", 30),
    "Dragon":     ("steak",     "magnificent",       40),
    "Crocodile":  ("filet",     "quite good",        20),
    "Boar":       ("burger",    "delicious",         22),
    "Skeleton":   None,   # Not edible - undead
    "Zombie":     None,   # Not edible - undead
    "Ghost":      None,   # Not edible - undead
    "Wraith":     None,   # Not edible - undead
    "Lich":       None,   # Not edible - undead
    "Vampire":    None,   # Not edible - undead
    "Slime":      None,   # Not edible - amorphous
    "Mold":       None,   # Not edible - fungal
    "Golem":      None,   # Not edible - construct
    "Demon":      None,   # Not edible - demonic
    "Elemental":  None,   # Not edible - elemental
}

# Default for monsters not in the dict
MEAT_DEFAULT = ("steak", "dubious", 12)
MEAT_DEFAULT_CUTS = ["steak", "burger", "chops", "filet", "kebab"]

HUNGER_MAX = 100
HUNGER_DECAY_PER_MOVE = 1  # hunger decreases 1 per move
HUNGER_STARVING_THRESHOLD = 10   # below this: starving, take 1 dmg per move
HUNGER_HUNGRY_THRESHOLD = 40     # below this: hungry, slight combat penalty
HUNGER_PECKISH_THRESHOLD = 70     # below this: peckish, just a cute British word
HUNGER_SATED_THRESHOLD = 90     # above this: sated bonus

MEAT_ROT_TURNS_RAW = 30         # raw meat rots after 30 moves
MEAT_ROT_TURNS_COOKED = 100     # cooked meat keeps longer
MEAT_ROT_TURNS_PRESERVED = 200  # cooked with kit keeps even longer


# ================================================================================
# SPELL TEMPLATES
# ================================================================================

SPELL_TEMPLATES = [
    # ===== LEVEL 0 SPELLS (1 slot each) - Basic Cantrips =====
    Spell(name="Ice Shard", description="Launches a sharp shard of ice.", mana_cost=8, damage_type='Ice', base_power=15, level=0),
    Spell(name="Spark", description="A tiny jolt of electricity.", mana_cost=5, damage_type='Wind', base_power=12, level=0),
    Spell(name="Stone Throw", description="Magically hurls a small rock.", mana_cost=6, damage_type='Earth', base_power=13, level=0),
    Spell(name="Minor Heal", description="Restores a tiny amount of health.", mana_cost=8, damage_type='Healing', base_power=15, level=0, spell_type='healing'),
    Spell(name="Shadow Bolt", description="A weak bolt of shadow energy.", mana_cost=7, damage_type='Darkness', base_power=14, level=0),
    Spell(name="Light Ray", description="A beam of pure light.", mana_cost=7, damage_type='Light', base_power=14, level=0),

    # ===== LEVEL 1 SPELLS (2 slots each) - Intermediate =====
    Spell(name="Fireball", description="Hurls a ball of fire at the enemy.", mana_cost=10, damage_type='Fire', base_power=20, level=1),
    Spell(name="Heal", description="Restores a small amount of health.", mana_cost=12, damage_type='Healing', base_power=25, level=1, spell_type='healing'),
    Spell(name="Water Blast", description="A pressurized stream of water.", mana_cost=11, damage_type='Water', base_power=22, level=1),
    Spell(name="Wind Slash", description="A cutting blade of wind.", mana_cost=10, damage_type='Wind', base_power=21, level=1),
    Spell(name="Acid Splash", description="Corrosive acid burns the target.", mana_cost=12, damage_type='Earth', base_power=23, level=1),
    Spell(name="Mind Spike", description="A sharp psionic attack.", mana_cost=13, damage_type='Psionic', base_power=24, level=1),
    Spell(name="Purify", description="Cleanses poison from the caster.", mana_cost=15, level=1, spell_type='remove_status', status_effect_name='Poison'),
    Spell(name="Cure Weakness", description="Restores strength and vigor.", mana_cost=12, level=1, spell_type='add_status_effect', status_effect_name='Vigor', status_effect_duration=3, status_effect_type='attack_boost', status_effect_magnitude=5),

    # ===== LEVEL 2 SPELLS (2 slots each) - Advanced =====
    Spell(name="Thunder Clap", description="A concussive wave of sound.", mana_cost=15, damage_type='Physical', base_power=30, level=2),
    Spell(name="Darkness Bolt", description="Fires a bolt of pure shadow.", mana_cost=14, damage_type='Darkness', base_power=28, level=2),
    Spell(name="Ice Storm", description="A freezing blizzard strikes the enemy.", mana_cost=16, damage_type='Ice', base_power=32, level=2),
    Spell(name="Freedom", description="Removes the web effect from the caster.", mana_cost=18, level=2, spell_type='remove_status', status_effect_name='Web'),
    Spell(name="Battle Hymn", description="Inspires the caster with increased attack for a short time.", mana_cost=20, level=2, spell_type='add_status_effect', status_effect_name='Inspired', status_effect_duration=3, status_effect_type='attack_boost', status_effect_magnitude=10),
    Spell(name="Stone Skin", description="Hardens your skin like stone.", mana_cost=18, level=2, spell_type='add_status_effect', status_effect_name='Stone Skin', status_effect_duration=4, status_effect_type='defense_boost', status_effect_magnitude=8),
    Spell(name="Flame Lance", description="A concentrated spear of flame.", mana_cost=17, damage_type='Fire', base_power=33, level=2),
    Spell(name="Lightning Bolt", description="A powerful bolt of electricity.", mana_cost=16, damage_type='Wind', base_power=31, level=2),
    Spell(name="Greater Heal", description="Restores a moderate amount of health.", mana_cost=18, damage_type='Healing', base_power=40, level=2, spell_type='healing'),

    # ===== LEVEL 3 SPELLS (3 slots each) - Expert =====
    Spell(name="Holy Light", description="Blinds and damages unholy foes.", mana_cost=18, damage_type='Holy', base_power=35, level=3),
    Spell(name="Meteor Strike", description="Summons a falling meteor.", mana_cost=22, damage_type='Fire', base_power=45, level=3),
    Spell(name="Regeneration", description="Heals the caster over several turns.", mana_cost=25, level=3, spell_type='add_status_effect', status_effect_name='Regenerating', status_effect_duration=4, status_effect_type='heal_over_time', status_effect_magnitude=8),
    Spell(name="Chain Lightning", description="Lightning that bounces between foes.", mana_cost=24, damage_type='Wind', base_power=42, level=3),
    Spell(name="Blizzard", description="A devastating ice storm.", mana_cost=23, damage_type='Ice', base_power=43, level=3),
    Spell(name="Earthquake", description="Shakes the ground violently.", mana_cost=25, damage_type='Earth', base_power=46, level=3),
    Spell(name="Mind Blast", description="Overwhelming psionic power.", mana_cost=21, damage_type='Psionic', base_power=40, level=3),
    Spell(name="Shadow Strike", description="A deadly strike from the shadows.", mana_cost=20, damage_type='Darkness', base_power=38, level=3),
    Spell(name="Divine Shield", description="Grants powerful protection.", mana_cost=28, level=3, spell_type='add_status_effect', status_effect_name='Divine Shield', status_effect_duration=3, status_effect_type='defense_boost', status_effect_magnitude=15),
    Spell(name="Mass Heal", description="Restores a large amount of health.", mana_cost=30, damage_type='Healing', base_power=60, level=3, spell_type='healing'),

    # ===== LEVEL 4 SPELLS (3 slots each) - Master =====
    Spell(name="Inferno", description="An all-consuming firestorm.", mana_cost=35, damage_type='Fire', base_power=55, level=4),
    Spell(name="Absolute Zero", description="Freeze the enemy solid.", mana_cost=33, damage_type='Ice', base_power=52, level=4),
    Spell(name="Tsunami", description="A massive wave crashes down.", mana_cost=34, damage_type='Water', base_power=53, level=4),
    Spell(name="Void Beam", description="Erases matter with dark energy.", mana_cost=32, damage_type='Darkness', base_power=50, level=4),
    Spell(name="Holy Smite", description="Divine wrath incarnate.", mana_cost=36, damage_type='Holy', base_power=56, level=4),
    Spell(name="Psychic Scream", description="Tears at the mind itself.", mana_cost=31, damage_type='Psionic', base_power=48, level=4),
    Spell(name="Full Restore", description="Completely restores health.", mana_cost=40, damage_type='Healing', base_power=100, level=4, spell_type='healing'),
    Spell(name="Titan's Strength", description="Grants enormous power.", mana_cost=38, level=4, spell_type='add_status_effect', status_effect_name='Titan Strength', status_effect_duration=5, status_effect_type='attack_boost', status_effect_magnitude=20),
    Spell(name="Clarity", description="Removes all negative status effects.", mana_cost=35, level=4, spell_type='remove_status', status_effect_name='All'),
    Spell(name="Time Stop", description="Slows time around the caster.", mana_cost=45, level=4, spell_type='add_status_effect', status_effect_name='Hasted', status_effect_duration=3, status_effect_type='attack_boost', status_effect_magnitude=25),

    # ===== LEVEL 5 SPELLS (3 slots each) - Legendary =====
    Spell(name="Armageddon", description="The end of all things.", mana_cost=50, damage_type='Demonic', base_power=75, level=5),
    Spell(name="Supernova", description="The power of an exploding star.", mana_cost=48, damage_type='Fire', base_power=70, level=5),
    Spell(name="Black Hole", description="Draws enemies into oblivion.", mana_cost=52, damage_type='Darkness', base_power=72, level=5),
    Spell(name="Divine Intervention", description="The gods themselves aid you.", mana_cost=55, damage_type='Holy', base_power=80, level=5),
    Spell(name="Perfect Regeneration", description="Constant healing for many turns.", mana_cost=50, level=5, spell_type='add_status_effect', status_effect_name='Perfect Regen', status_effect_duration=8, status_effect_type='heal_over_time', status_effect_magnitude=15),
    Spell(name="Ultimate Shield", description="Near-invulnerability.", mana_cost=60, level=5, spell_type='add_status_effect', status_effect_name='Ultimate Shield', status_effect_duration=5, status_effect_type='defense_boost', status_effect_magnitude=30),
]


# ================================================================================
# POTION TEMPLATES
# ================================================================================

POTION_TEMPLATES = [
    #  HEALING POTIONS
    Potion(
        name="Minor Healing Potion",
        description="A small vial of red liquid that heals minor wounds.",
        value=30,
        level=0,
        potion_type='healing',
        effect_magnitude=30
    ),
    Potion(
        name="Healing Potion",
        description="A flask of red liquid that heals moderate wounds.",
        value=50,
        level=1,
        potion_type='healing',
        effect_magnitude=50
    ),
    Potion(
        name="Greater Healing Potion",
        description="A large flask of crimson liquid that heals significant wounds.",
        value=80,
        level=3,
        potion_type='healing',
        effect_magnitude=80
    ),
    Potion(
        name="Superior Healing Potion",
        description="A crystalline vial of ruby liquid that heals major wounds.",
        value=120,
        level=5,
        potion_type='healing',
        effect_magnitude=120
    ),
    Potion(
        name="Master Healing Potion",
        description="A glowing vial of brilliant red liquid that heals the most grievous wounds.",
        value=180,
        level=7,
        potion_type='healing',
        effect_magnitude=180
    ),

    #  MANA POTIONS
    Potion(
        name="Minor Mana Potion",
        description="A small vial of blue liquid that restores a small amount of mana.",
        value=30,
        level=0,
        potion_type='mana',
        effect_magnitude=25
    ),
    Potion(
        name="Mana Potion",
        description="A flask of blue liquid that restores moderate mana.",
        value=50,
        level=1,
        potion_type='mana',
        effect_magnitude=40
    ),
    Potion(
        name="Greater Mana Potion",
        description="A large flask of deep blue liquid that restores significant mana.",
        value=80,
        level=3,
        potion_type='mana',
        effect_magnitude=60
    ),
    Potion(
        name="Superior Mana Potion",
        description="A crystalline vial of sapphire liquid that restores major mana.",
        value=120,
        level=5,
        potion_type='mana',
        effect_magnitude=90
    ),

    #  STAT BUFF POTIONS
    Potion(
        name="Potion of Strength",
        description="Increases physical power for a short time.",
        value=60,
        level=2,
        potion_type='strength',
        effect_magnitude=10,
        duration=6
    ),
    Potion(
        name="Potion of Greater Strength",
        description="Greatly increases physical power.",
        value=100,
        level=4,
        potion_type='strength',
        effect_magnitude=20,
        duration=8
    ),
    Potion(
        name="Potion of Dexterity",
        description="Increases agility and precision for a short time.",
        value=60,
        level=2,
        potion_type='dexterity',
        effect_magnitude=10,
        duration=6
    ),
    Potion(
        name="Potion of Intelligence",
        description="Increases mental acuity and magical power.",
        value=60,
        level=2,
        potion_type='intelligence',
        effect_magnitude=10,
        duration=6
    ),
    Potion(
        name="Potion of Defense",
        description="Hardens the body against physical attacks.",
        value=70,
        level=2,
        potion_type='defense',
        effect_magnitude=15,
        duration=6
    ),

    #  NEW SPECIAL POTIONS
    Potion(
        name="Potion of Invisibility",
        description="Makes you invisible, allowing cowards to avoid combat encounters.",
        value=150,
        level=4,
        potion_type='invisibility',
        effect_magnitude=0,
        duration=5
    ),
    Potion(
        name="Potion of True Sight",
        description="Reveals hidden things and grants supernatural vision.",
        value=120,
        level=3,
        potion_type='true_sight',
        effect_magnitude=0,
        duration=8
    ),
    Potion(
        name="Potion of Berserker Rage",
        description="Massive attack boost, but reduces defense. High risk, high reward!",
        value=100,
        level=3,
        potion_type='berserker',
        effect_magnitude=30,
        duration=5
    ),
    Potion(
        name="Potion of Regeneration",
        description="Gradually heals wounds over time.",
        value=110,
        level=3,
        potion_type='regeneration',
        effect_magnitude=8,  # HP per turn
        duration=10
    ),
    Potion(
        name="Potion of Clarity",
        description="Removes all negative status effects and restores mana.",
        value=130,
        level=4,
        potion_type='clarity',
        effect_magnitude=30,  # Mana restored
        duration=0
    ),
    Potion(
        name="Potion of Frost Armor",
        description="Coats you in protective ice that damages attackers. But it doesn't feel cool, just kind of refreshing.",
        value=140,
        level=4,
        potion_type='frost_armor',
        effect_magnitude=15,  # Damage reflected
        duration=7
    ),
    Potion(
        name="Potion of Giant's Strength",
        description="Grants the strength of a giant for a short time.",
        value=160,
        level=5,
        potion_type='giant_strength',
        effect_magnitude=15,  # Temporary STR bonus
        duration=6
    ),
    Potion(
        name="Potion of Vampirism",
        description="Heal yourself by stealing life from enemies. Moral dilemmas to be solved later.",
        value=150,
        level=5,
        potion_type='vampirism',
        effect_magnitude=50,  # 50% lifesteal
        duration=8
    ),
    Potion(
        name="Potion of Fortune",
        description="Increases the quality and quantity of treasure found. Because you are greedy.",
        value=120,
        level=3,
        potion_type='fortune',
        effect_magnitude=50,  # 50% better loot
        duration=10
    ),
    Potion(
        name="Potion of Experience",
        description="Grants bonus experience from all sources.",
        value=140,
        level=4,
        potion_type='experience',
        effect_magnitude=50,  # 50% bonus XP
        duration=10
    ),
    Potion(
        name="Potion of Haste",
        description="Allows you to act twice as fast in combat.",
        value=180,
        level=6,
        potion_type='haste',
        effect_magnitude=2,
        duration=4
    ),
    Potion(
        name="Potion of Stone Skin",
        description="Your skin hardens like stone, reducing all damage.",
        value=130,
        level=4,
        potion_type='stone_skin',
        effect_magnitude=10,  # Flat damage reduction
        duration=8
    ),
    Potion(
        name="Potion of Fire Resistance",
        description="A red, warm liquid that protects against fire damage. Eat a hot pepper. Impress your dopey friends.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,  # 50% reduction
        duration=6,
        resistance_element='Fire'
    ),

    Potion(
        name="Potion of Ice Resistance",
        description="A frigid blue liquid that protects against ice damage. Of course it's blue.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Ice'
    ),

    Potion(
        name="Potion of Lightning Resistance",
        description="A crackling yellow liquid that protects against lightning damage. Tastes like pop rocks.",
        value=75,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Lightning'
    ),

    Potion(
        name="Potion of Water Resistance",
        description="A flowing aqua liquid that protects against water damage. Come on let's go party.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Water'
    ),

    Potion(
        name="Potion of Earth Resistance",
        description="A viscous brown liquid that protects against earth damage. You had me at viscous and brown.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Earth'
    ),

    Potion(
        name="Potion of Wind Resistance",
        description="A light, swirling liquid that protects against wind damage. Bascially a skinny drink.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Wind'
    ),

    Potion(
        name="Potion of Holy Resistance",
        description="A golden liquid that protects against holy damage. You had me at golden liquid.",
        value=80,
        level=3,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Holy'
    ),

    Potion(
        name="Potion of Shadow Resistance",
        description="A dark, inky liquid that protects against darkness damage.",
        value=80,
        level=3,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Darkness'
    ),

    Potion(
        name="Potion of Poison Resistance",
        description="A green, bubbling liquid that protects against poison damage.",
        value=85,
        level=3,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Poison'
    ),

    Potion(
        name="Potion of Physical Resistance",
        description="A silvery liquid that hardens skin against physical attacks.",
        value=75,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Physical'
    ),

    Potion(
        name="Potion of Psionic Resistance",
        description="A shimmering purple liquid that shields the mind.",
        value=90,
        level=3,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Psionic'
    ),

    #  GREATER RESISTANCE (75% reduction)

    Potion(
        name="Greater Fire Resistance",
        description="A brilliant crimson elixir that grants powerful fire protection.",
        value=120,
        level=4,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Fire'
    ),

    Potion(
        name="Greater Ice Resistance",
        description="A crystalline blue elixir that grants powerful ice protection.",
        value=120,
        level=4,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Ice'
    ),

    Potion(
        name="Greater Lightning Resistance",
        description="An electrified golden elixir that grants powerful lightning protection.",
        value=125,
        level=4,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Lightning'
    ),

    Potion(
        name="Greater Shadow Resistance",
        description="A void-black elixir that grants powerful darkness protection.",
        value=130,
        level=5,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Darkness'
    ),

    Potion(
        name="Greater Poison Resistance",
        description="A luminous green elixir that grants powerful poison protection.",
        value=135,
        level=5,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Poison'
    ),

    #  MULTI-ELEMENT RESISTANCE (30% to multiple)

    Potion(
        name="Potion of Elemental Warding",
        description="A tri-colored liquid that protects against fire, ice, and lightning.",
        value=110,
        level=3,
        potion_type='resistance',
        effect_magnitude=30,  # Lower reduction but covers 3 elements
        duration=6,
        resistance_element='Multi'  # Special: Fire + Ice + Lightning
    ),

    Potion(
        name="Potion of Natural Warding",
        description="An earthy liquid that protects against earth, water, and wind.",
        value=100,
        level=3,
        potion_type='resistance',
        effect_magnitude=30,
        duration=6,
        resistance_element='Multi-Natural'  # Special: Earth + Water + Wind
    ),

    Potion(
        name="Potion of Arcane Warding",
        description="A mystical liquid that protects against holy, darkness, and psionic.",
        value=130,
        level=4,
        potion_type='resistance',
        effect_magnitude=30,
        duration=6,
        resistance_element='Multi-Arcane'  # Special: Holy + Darkness + Psionic
    ),

    #  UNIVERSAL RESISTANCE (25% to ALL)

    Potion(
        name="Potion of Universal Resistance",
        description="A shimmering rainbow liquid that protects against all damage types.",
        value=180,
        level=6,
        potion_type='resistance',
        effect_magnitude=25,  # Lower but covers EVERYTHING
        duration=5,
        resistance_element='Universal'
    ),

    Potion(
        name="Elixir of Invulnerability",
        description="A legendary elixir that grants near-invulnerability to all damage.",
        value=250,
        level=8,
        potion_type='resistance',
        effect_magnitude=40,  # Stronger universal resistance
        duration=4,
        resistance_element='Universal'
    ),

    # === DEEP FLOOR POTIONS (Level 10+) ===

    # Higher tier healing
    Potion(name="Supreme Healing Potion", description="Restores 250 HP.", value=250, level=10, potion_type='healing', effect_magnitude=250),
    Potion(name="Divine Healing Potion", description="Restores 400 HP.", value=400, level=15, potion_type='healing', effect_magnitude=400),
    Potion(name="Godly Healing Potion", description="Restores 600 HP.", value=600, level=20, potion_type='healing', effect_magnitude=600),

    # Higher tier mana
    Potion(name="Supreme Mana Potion", description="Restores 120 mana.", value=200, level=10, potion_type='mana', effect_magnitude=120),
    Potion(name="Divine Mana Potion", description="Restores 180 mana.", value=350, level=15, potion_type='mana', effect_magnitude=180),

    # Combat buff potions - bigger magnitudes for deep floors
    Potion(name="Potion of Titan Strength", description="Massive strength surge.", value=200, level=10, potion_type='strength', effect_magnitude=25, duration=10),
    Potion(name="Potion of Dragon Strength", description="Strength of an ancient dragon.", value=350, level=15, potion_type='strength', effect_magnitude=35, duration=10),
    Potion(name="Potion of God Strength", description="Divine power flows through you.", value=500, level=20, potion_type='strength', effect_magnitude=50, duration=10),
    Potion(name="Potion of Cat Reflexes", description="Lightning-fast reflexes.", value=200, level=10, potion_type='dexterity', effect_magnitude=25, duration=10),
    Potion(name="Potion of Wind Reflexes", description="Move like the wind itself.", value=350, level=15, potion_type='dexterity', effect_magnitude=35, duration=10),
    Potion(name="Potion of Iron Fortress", description="Skin hardens like iron.", value=200, level=10, potion_type='defense', effect_magnitude=25, duration=10),
    Potion(name="Potion of Adamant Fortress", description="Become nearly impenetrable.", value=350, level=15, potion_type='defense', effect_magnitude=40, duration=10),
    Potion(name="Potion of Diamond Fortress", description="The ultimate defensive ward.", value=500, level=20, potion_type='defense', effect_magnitude=60, duration=10),

    # War elixirs - huge short combat buffs
    Potion(name="War Elixir", description="Doubles your combat prowess briefly.", value=300, level=12, potion_type='berserker', effect_magnitude=50, duration=6),
    Potion(name="Warlord Elixir", description="Fight like a god of war.", value=600, level=18, potion_type='berserker', effect_magnitude=80, duration=6),

    # Permanent stat elixirs - rare, expensive, one-time boosts
    Potion(name="Elixir of Might", description="Permanently increases STR by 2.", value=800, level=15, potion_type='permanent_strength', effect_magnitude=2),
    Potion(name="Elixir of Grace", description="Permanently increases DEX by 2.", value=800, level=15, potion_type='permanent_dexterity', effect_magnitude=2),
    Potion(name="Elixir of Brilliance", description="Permanently increases INT by 2.", value=800, level=15, potion_type='permanent_intelligence', effect_magnitude=2),
    Potion(name="Greater Elixir of Might", description="Permanently increases STR by 4.", value=2000, level=25, potion_type='permanent_strength', effect_magnitude=4),
    Potion(name="Greater Elixir of Grace", description="Permanently increases DEX by 4.", value=2000, level=25, potion_type='permanent_dexterity', effect_magnitude=4),
    Potion(name="Greater Elixir of Brilliance", description="Permanently increases INT by 4.", value=2000, level=25, potion_type='permanent_intelligence', effect_magnitude=4),
    Potion(name="Supreme Elixir of Might", description="Permanently increases STR by 6.", value=5000, level=35, potion_type='permanent_strength', effect_magnitude=6),
    Potion(name="Supreme Elixir of Grace", description="Permanently increases DEX by 6.", value=5000, level=35, potion_type='permanent_dexterity', effect_magnitude=6),
    Potion(name="Supreme Elixir of Brilliance", description="Permanently increases INT by 6.", value=5000, level=35, potion_type='permanent_intelligence', effect_magnitude=6),
    Potion(name="Elixir of Vitality", description="Permanently increases max HP by 20.", value=1200, level=15, potion_type='permanent_health', effect_magnitude=20),
    Potion(name="Greater Elixir of Vitality", description="Permanently increases max HP by 40.", value=3000, level=25, potion_type='permanent_health', effect_magnitude=40),
    Potion(name="Supreme Elixir of Vitality", description="Permanently increases max HP by 75.", value=6000, level=35, potion_type='permanent_health', effect_magnitude=75),

    # Deep-floor healing potions
    Potion(name="Heroic Healing Potion", description="A radiant vial that mends grievous wounds.", value=250, level=10, potion_type='healing', effect_magnitude=200),
    Potion(name="Legendary Healing Potion", description="A shimmering elixir of extraordinary restoration.", value=500, level=15, potion_type='healing', effect_magnitude=350),
    Potion(name="Mythic Healing Potion", description="Liquid starlight that knits flesh and bone.", value=800, level=25, potion_type='healing', effect_magnitude=500),

    # Deep-floor mana potions
    Potion(name="Master Mana Potion", description="A deep indigo draught of arcane power.", value=200, level=10, potion_type='mana', effect_magnitude=120),
    Potion(name="Supreme Mana Potion", description="Liquid moonlight that floods the mind with power.", value=400, level=20, potion_type='mana', effect_magnitude=200),

    # Tiered combat buff potions - Wrath line (ATK boost)
    Potion(name="Potion of Wrath", description="Battle fury surges through your veins.", value=300, level=10, potion_type='strength', effect_magnitude=25, duration=10),
    Potion(name="Potion of Titan's Wrath", description="The rage of ancient titans empowers your strikes.", value=800, level=20, potion_type='strength', effect_magnitude=50, duration=12),
    Potion(name="Potion of Mythic Wrath", description="Primordial fury distilled to its purest form.", value=1500, level=35, potion_type='strength', effect_magnitude=75, duration=14),

    # Tiered combat buff potions - Guard line (DEF boost)
    Potion(name="Potion of Iron Will", description="Your resolve hardens like iron.", value=300, level=10, potion_type='defense', effect_magnitude=20, duration=10),
    Potion(name="Potion of Titan's Guard", description="The endurance of titans shields you from harm.", value=800, level=20, potion_type='defense', effect_magnitude=40, duration=12),
    Potion(name="Potion of Mythic Guard", description="An impenetrable aura of ancient protection.", value=1500, level=35, potion_type='defense', effect_magnitude=60, duration=14),

    # Tiered Greater Dexterity and Intelligence buffs
    Potion(name="Potion of Greater Dexterity", description="Greatly increases agility and reaction speed.", value=200, level=8, potion_type='dexterity', effect_magnitude=20, duration=8),
    Potion(name="Potion of Superior Dexterity", description="Move with supernatural speed and precision.", value=500, level=18, potion_type='dexterity', effect_magnitude=35, duration=10),
    Potion(name="Potion of Greater Intelligence", description="Greatly increases mental focus and magical potency.", value=200, level=8, potion_type='intelligence', effect_magnitude=20, duration=8),
    Potion(name="Potion of Superior Intelligence", description="Arcane brilliance floods your consciousness.", value=500, level=18, potion_type='intelligence', effect_magnitude=35, duration=10),

    # Deep-floor special combat potions
    Potion(name="Potion of Greater Berserker Rage", description="Overwhelming fury. Massive attack, reduced defense.", value=400, level=15, potion_type='berserker', effect_magnitude=50, duration=6),
    Potion(name="Greater Potion of Haste", description="Time seems to slow around you.", value=400, level=15, potion_type='haste', effect_magnitude=2, duration=6),
    Potion(name="Greater Potion of Stone Skin", description="Your body becomes nearly impervious to harm.", value=350, level=15, potion_type='stone_skin', effect_magnitude=20, duration=10),
    Potion(name="Potion of Greater Frost Armor", description="A shell of enchanted ice surrounds you.", value=400, level=15, potion_type='frost_armor', effect_magnitude=25, duration=10),

    # Higher tier regen and vampirism
    Potion(name="Greater Regeneration Potion", description="Powerful sustained healing.", value=200, level=10, potion_type='regeneration', effect_magnitude=15, duration=12),
    Potion(name="Supreme Regeneration Potion", description="Incredible sustained healing.", value=500, level=20, potion_type='regeneration', effect_magnitude=25, duration=15),
    Potion(name="Greater Vampirism Potion", description="Drain life with every blow.", value=300, level=12, potion_type='vampirism', effect_magnitude=75, duration=10),
    Potion(name="Supreme Vampirism Potion", description="Feast on the lifeforce of enemies.", value=600, level=20, potion_type='vampirism', effect_magnitude=100, duration=12),
]


# ================================================================================
# WEAPON TEMPLATES
# ================================================================================

WEAPON_TEMPLATES = [
    # Level 0 - Basic weapons
    Weapon(name="Dagger", description="A small, sharp blade.", attack_bonus=2, value=10, level=0, upgrade_level=0),
    Weapon(name="Short Sword", description="A balanced one-handed sword.", attack_bonus=4, value=25, level=0, upgrade_level=0),
    Weapon(name="Club", description="A simple wooden club.", attack_bonus=2, value=5, level=0, upgrade_level=0),
    Weapon(name="Staff", description="A simple wooden staff, good for bludgeoning.", attack_bonus=3, value=15, level=0, upgrade_level=0, upgrade_limit=False),
    Weapon(name="Rusty Sword", description="A worn blade, still serviceable.", attack_bonus=3, value=8, level=0, upgrade_level=0),

    # Level 1-2 - Iron tier
    Weapon(name="Iron Sword", description="A sturdy iron sword.", attack_bonus=5, value=75, level=1, upgrade_level=0),
    Weapon(name="Mace", description="A heavy flanged mace.", attack_bonus=5, value=60, level=1, upgrade_level=0),
    Weapon(name="Handaxe", description="A small but deadly axe.", attack_bonus=4, value=45, level=1, upgrade_level=0),
    Weapon(name="Spear", description="A long-reaching polearm.", attack_bonus=5, value=55, level=1, upgrade_level=0),
    Weapon(name="Longsword", description="A classic adventurer's sword.", attack_bonus=6, value=100, level=2, upgrade_level=0),
    Weapon(name="Battle Axe", description="A heavy axe for close combat.", attack_bonus=7, value=120, level=2, upgrade_level=0),
    Weapon(name="Morningstar", description="A spiked ball on a chain.", attack_bonus=6, value=90, level=2, upgrade_level=0),

    # Level 3-4 - Steel tier
    Weapon(name="Greatsword", description="A massive two-handed sword.", attack_bonus=10, value=250, level=3, upgrade_level=0),
    Weapon(name="Warhammer", description="A crushing blow with this hammer.", attack_bonus=8, value=180, level=3, upgrade_level=0),
    Weapon(name="Steel Blade", description="A finely crafted steel sword.", attack_bonus=9, value=200, level=3, upgrade_level=0),
    Weapon(name="Halberd", description="A versatile polearm with axe head.", attack_bonus=9, value=190, level=3, upgrade_level=0),
    Weapon(name="Falchion", description="A curved, single-edged sword.", attack_bonus=8, value=170, level=3, upgrade_level=0),
    Weapon(name="War Scythe", description="A deadly curved blade.", attack_bonus=10, value=220, level=4, upgrade_level=0),
    Weapon(name="Claymore", description="A Scottish great sword.", attack_bonus=11, value=280, level=4, upgrade_level=0),

    # Level 5-7 - Rare tier
    Weapon(name="Mithril Sword", description="Light yet incredibly sharp.", attack_bonus=12, value=400, level=5, upgrade_level=0),
    Weapon(name="Dwarven Waraxe", description="Forged in mountain fires.", attack_bonus=13, value=450, level=5, upgrade_level=0),
    Weapon(name="Elven Blade", description="Graceful and deadly.", attack_bonus=11, value=380, level=5, upgrade_level=0),
    Weapon(name="Executioner's Blade", description="A massive cleaving sword.", attack_bonus=14, value=500, level=6, upgrade_level=0),
    Weapon(name="Runic Hammer", description="Inscribed with ancient runes.", attack_bonus=13, value=480, level=6, upgrade_level=0),
    Weapon(name="Obsidian Edge", description="Volcanic glass, incredibly sharp.", attack_bonus=14, value=520, level=6, upgrade_level=0),
    Weapon(name="Dragon Slayer", description="A blade forged to fell dragons.", attack_bonus=16, value=650, level=7, upgrade_level=0),

    # Level 8-10 - Epic tier
    Weapon(name="Adamantine Sword", description="Nearly indestructible metal.", attack_bonus=18, value=800, level=8, upgrade_level=0),
    Weapon(name="Soul Reaver", description="Drinks the essence of foes.", attack_bonus=17, value=750, level=8, upgrade_level=0),
    Weapon(name="Blade of the Ancients", description="From a forgotten age.", attack_bonus=19, value=900, level=9, upgrade_level=0),
    Weapon(name="Worldbreaker", description="Shatters stone and steel alike.", attack_bonus=20, value=1000, level=10, upgrade_level=0),
    # Level 12 - Volcanic/Crystal tier
    Weapon(name="Volcanic Blade", description="Forged in magma flows deep below.", attack_bonus=24, value=1400, level=12, upgrade_level=0, upgrade_limit=15),
    Weapon(name="Crystal Greatsword", description="Carved from a single massive crystal.", attack_bonus=26, value=1600, level=12, upgrade_level=0, upgrade_limit=15),
    Weapon(name="Runeforged Axe", description="Ancient runes pulse along the blade.", attack_bonus=25, value=1500, level=12, upgrade_level=0, upgrade_limit=15),
    # Level 15 - Enchanted tier
    Weapon(name="Enchanted Longsword", description="Hums with arcane energy.", attack_bonus=30, value=2200, level=15, upgrade_level=0, upgrade_limit=20),
    Weapon(name="Stormcaller", description="Lightning crackles along the edge.", attack_bonus=32, value=2500, level=15, upgrade_level=0, upgrade_limit=20),
    Weapon(name="Venomblade", description="Drips with a sickly green sheen.", attack_bonus=31, value=2300, level=15, upgrade_level=0, upgrade_limit=20),
    # Level 18 - Abyssal tier
    Weapon(name="Abyssal Scythe", description="Ripped from the hands of a fallen reaper.", attack_bonus=36, value=3200, level=18, upgrade_level=0, upgrade_limit=20),
    Weapon(name="Deepforge Hammer", description="Forged at the heart of the earth.", attack_bonus=38, value=3500, level=18, upgrade_level=0, upgrade_limit=20),
    Weapon(name="Shadowsteel Blade", description="Made from metal that absorbs light.", attack_bonus=37, value=3400, level=18, upgrade_level=0, upgrade_limit=20),
    # Level 22 - Void tier
    Weapon(name="Void Reaver", description="Tears holes in reality itself.", attack_bonus=44, value=4500, level=22, upgrade_level=0, upgrade_limit=25),
    Weapon(name="Elder Warblade", description="Wielded by forgotten war gods.", attack_bonus=46, value=4800, level=22, upgrade_level=0, upgrade_limit=25),
    Weapon(name="Nethersteel Edge", description="Folded from metal between planes.", attack_bonus=45, value=4600, level=22, upgrade_level=0, upgrade_limit=25),
    # Level 26 - Primordial tier
    Weapon(name="Primordial Cleaver", description="Hewn from the bones of a titan.", attack_bonus=52, value=6000, level=26, upgrade_level=0, upgrade_limit=25),
    Weapon(name="Starfall Blade", description="Forged from a fallen star.", attack_bonus=54, value=6500, level=26, upgrade_level=0, upgrade_limit=25),
    # Level 30 - Titan tier
    Weapon(name="Titan Slayer", description="Made to fell the unkillable.", attack_bonus=60, value=8000, level=30, upgrade_level=0, upgrade_limit=30),
    Weapon(name="Worldrender", description="The earth trembles at each swing.", attack_bonus=64, value=8500, level=30, upgrade_level=0, upgrade_limit=30),
    Weapon(name="Doomhammer", description="Each blow echoes like thunder.", attack_bonus=62, value=8200, level=30, upgrade_level=0, upgrade_limit=30),
    # Level 35 - Godslayer tier
    Weapon(name="Godslayer", description="Even the divine fear its edge.", attack_bonus=72, value=11000, level=35, upgrade_level=0, upgrade_limit=30),
    Weapon(name="Eternity Blade", description="Its edge exists across all timelines.", attack_bonus=76, value=12000, level=35, upgrade_level=0, upgrade_limit=30),
    # Level 40 - Mythic tier
    Weapon(name="Mythic Destroyer", description="A weapon from the age before ages.", attack_bonus=84, value=15000, level=40, upgrade_level=0, upgrade_limit=35),
    Weapon(name="Cosmic Reaper", description="Cuts through the fabric of existence.", attack_bonus=88, value=16000, level=40, upgrade_level=0, upgrade_limit=35),
    # Level 42 - Ultimate
    Weapon(name="Astral Annihilator", description="The final weapon. Nothing survives its touch.", attack_bonus=92, value=18000, level=42, upgrade_level=0, upgrade_limit=35),
]


# ================================================================================
# ARMOR TEMPLATES
# ================================================================================

ARMOR_TEMPLATES = [
    # Level 0 - Basic armor
    Armor(name="Cloth Robes", description="Simple cloth protection.", defense_bonus=1, value=15, level=0, upgrade_level=0),
    Armor(name="Padded Armor", description="Quilted fabric for light protection.", defense_bonus=2, value=30, level=0, upgrade_level=0),
    Armor(name="Leather Armor", description="Light leather armor.", defense_bonus=3, value=50, level=0, upgrade_level=0),

    # Level 1-2 - Iron tier
    Armor(name="Hide Armor", description="Thick animal hide.", defense_bonus=3, value=55, level=1, upgrade_level=0),
    Armor(name="Studded Leather", description="Leather reinforced with metal studs.", defense_bonus=4, value=70, level=2, upgrade_level=0),
    Armor(name="Ring Mail", description="Leather with metal rings sewn in.", defense_bonus=4, value=80, level=2, upgrade_level=0),

    # Level 3-4 - Steel tier
    Armor(name="Chainmail", description="Interlocking metal rings.", defense_bonus=5, value=90, level=3, upgrade_level=0),
    Armor(name="Scale Mail", description="Overlapping scales of metal.", defense_bonus=6, value=110, level=4, upgrade_level=0),
    Armor(name="Breastplate", description="Solid chest protection.", defense_bonus=6, value=120, level=4, upgrade_level=0),
    Armor(name="Splint Armor", description="Metal strips riveted to leather.", defense_bonus=7, value=140, level=4, upgrade_level=0),

    # Level 5-6 - Plate tier
    Armor(name="Plate Armor", description="Heavy, protective metal plates.", defense_bonus=8, value=150, level=5, upgrade_level=0),
    Armor(name="Half Plate", description="Plate armor with lighter leg protection.", defense_bonus=7, value=130, level=5, upgrade_level=0),
    Armor(name="Full Plate", description="Complete plate coverage.", defense_bonus=9, value=200, level=6, upgrade_level=0),
    Armor(name="Knight's Armor", description="Noble knight's full protection.", defense_bonus=10, value=250, level=6, upgrade_level=0),

    # Level 7-8 - Rare tier
    Armor(name="Mithril Chainmail", description="Light as silk, strong as steel.", defense_bonus=10, value=350, level=7, upgrade_level=0),
    Armor(name="Dwarven Plate", description="Masterwork dwarven craftsmanship.", defense_bonus=12, value=450, level=7, upgrade_level=0),
    Armor(name="Elven Mail", description="Flowing silver links.", defense_bonus=11, value=400, level=7, upgrade_level=0),
    Armor(name="Dragon Scale", description="Scales from a true dragon.", defense_bonus=14, value=600, level=8, upgrade_level=0),

    # Level 9-10 - Epic tier
    Armor(name="Adamantine Plate", description="Nearly impenetrable armor.", defense_bonus=16, value=800, level=9, upgrade_level=0),
    Armor(name="Celestial Mail", description="Blessed by the gods.", defense_bonus=18, value=1000, level=10, upgrade_level=0),
    # Level 12 - Volcanic/Crystal tier
    Armor(name="Volcanic Mail", description="Forged in lava, warm to the touch.", defense_bonus=16, value=1200, level=12, upgrade_level=0, upgrade_limit=15),
    Armor(name="Crystal Plate", description="Transparent yet harder than steel.", defense_bonus=18, value=1400, level=12, upgrade_level=0, upgrade_limit=15),
    Armor(name="Runeforged Armor", description="Glowing runes reinforce every joint.", defense_bonus=17, value=1300, level=12, upgrade_level=0, upgrade_limit=15),
    # Level 15 - Enchanted tier
    Armor(name="Enchanted Plate", description="Magic flows through every seam.", defense_bonus=22, value=2000, level=15, upgrade_level=0, upgrade_limit=20),
    Armor(name="Stormweave Armor", description="Woven from solidified lightning.", defense_bonus=24, value=2200, level=15, upgrade_level=0, upgrade_limit=20),
    Armor(name="Venomscale Mail", description="Scales that repel all toxins.", defense_bonus=23, value=2100, level=15, upgrade_level=0, upgrade_limit=20),
    # Level 18 - Abyssal tier
    Armor(name="Abyssal Shell", description="Grown from deep sea chitin.", defense_bonus=28, value=2800, level=18, upgrade_level=0, upgrade_limit=20),
    Armor(name="Deepforge Plate", description="Hammered at the core of the world.", defense_bonus=30, value=3100, level=18, upgrade_level=0, upgrade_limit=20),
    Armor(name="Shadowsteel Mail", description="Bends light around the wearer.", defense_bonus=29, value=3000, level=18, upgrade_level=0, upgrade_limit=20),
    # Level 22 - Void tier
    Armor(name="Void Carapace", description="A shell of nothingness that deflects all.", defense_bonus=36, value=4000, level=22, upgrade_level=0, upgrade_limit=25),
    Armor(name="Elder Warplate", description="Armor of the first warriors.", defense_bonus=38, value=4300, level=22, upgrade_level=0, upgrade_limit=25),
    Armor(name="Nethersteel Armor", description="Phased between realities.", defense_bonus=37, value=4100, level=22, upgrade_level=0, upgrade_limit=25),
    # Level 26 - Primordial tier
    Armor(name="Primordial Bastion", description="Made from the hide of a world beast.", defense_bonus=44, value=5500, level=26, upgrade_level=0, upgrade_limit=25),
    Armor(name="Starfall Plate", description="Meteor-forged and crater-cooled.", defense_bonus=46, value=5800, level=26, upgrade_level=0, upgrade_limit=25),
    # Level 30 - Titan tier
    Armor(name="Titan Guard", description="Ripped from a fallen colossus.", defense_bonus=52, value=7200, level=30, upgrade_level=0, upgrade_limit=30),
    Armor(name="Worldshield", description="The earth itself is your armor.", defense_bonus=56, value=7800, level=30, upgrade_level=0, upgrade_limit=30),
    Armor(name="Doomplate", description="Nothing that wears this has ever fallen.", defense_bonus=54, value=7500, level=30, upgrade_level=0, upgrade_limit=30),
    # Level 35 - Godplate tier
    Armor(name="Godplate", description="Worn by deities in forgotten wars.", defense_bonus=64, value=10000, level=35, upgrade_level=0, upgrade_limit=30),
    Armor(name="Eternity Aegis", description="Exists outside of time itself.", defense_bonus=68, value=11000, level=35, upgrade_level=0, upgrade_limit=30),
    # Level 40 - Mythic tier
    Armor(name="Mythic Bulwark", description="From the dawn of creation.", defense_bonus=76, value=14000, level=40, upgrade_level=0, upgrade_limit=35),
    Armor(name="Cosmic Shell", description="Forged from compressed starlight.", defense_bonus=80, value=15000, level=40, upgrade_level=0, upgrade_limit=35),
    # Level 42 - Ultimate
    Armor(name="Astral Fortress", description="The ultimate defense. An armor of pure will.", defense_bonus=84, value=17000, level=42, upgrade_level=0, upgrade_limit=35),
]


# ================================================================================
# TIER PREFIXES AND ELEMENTAL SUFFIXES
# ================================================================================

# Tier names based on upgrade level
WEAPON_TIER_PREFIXES = {
    0: "",           # No prefix for base items
    1: "Honed",      # +1
    2: "Keen",       # +2
    3: "Tempered",   # +3
    4: "Reinforced", # +4
    5: "Superior",   # +5
    6: "Masterwork", # +6
    7: "Epic",       # +7
    8: "Legendary",  # +8
    9: "Mythic",     # +9
    10: "Divine",    # +10
}

ARMOR_TIER_PREFIXES = {
    0: "",           # No prefix for base items
    1: "Sturdy",     # +1
    2: "Hardened",   # +2
    3: "Reinforced", # +3
    4: "Fortified",  # +4
    5: "Superior",   # +5
    6: "Masterwork", # +6
    7: "Epic",       # +7
    8: "Legendary",  # +8
    9: "Mythic",     # +9
    10: "Divine",    # +10
}

# Elemental suffixes
ELEMENTAL_SUFFIXES = {
    "Fire": "of Flames",
    "Ice": "of Frost",
    "Lightning": "of Thunder",
    "Poison": "of Venom",
    "Dark": "of Shadow",
    "Light": "of Radiance",
    "Physical": "of Force",
    "Arcane": "of the Arcane",
    "None": "",
}

# Multiple element combinations
MULTI_ELEMENT_SUFFIXES = {
    frozenset(["Fire", "Ice"]): "of Extremes",
    frozenset(["Fire", "Lightning"]): "of the Storm",
    frozenset(["Ice", "Lightning"]): "of the Tempest",
    frozenset(["Light", "Dark"]): "of Twilight",
    frozenset(["Fire", "Dark"]): "of Hellfire",
    frozenset(["Ice", "Dark"]): "of the Void",
    frozenset(["Fire", "Light"]): "of the Sun",
    frozenset(["Ice", "Light"]): "of the Moon",
    frozenset(["Poison", "Dark"]): "of Corruption",
}


# ================================================================================
# SCROLL TEMPLATES
# ================================================================================

SCROLL_TEMPLATES = [
    #  SPELL SCROLLS - Cast spells at 1.5x power

    # Level 0-1 Spell Scrolls
    Scroll(
        name="Scroll of Ice Shard",
        description="A frozen scroll that releases shards of ice when read.",
        effect_description="Casts Ice Shard at 150% power without mana cost.",
        value=30,
        level=0,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Ice Shard"),
        spell_power_multiplier=1.5
    ),

    Scroll(
        name="Scroll of Fireball",
        description="Ancient runes that summon enhanced flames.",
        effect_description="Casts Fireball at 150% power without mana cost.",
        value=50,
        level=1,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Fireball"),
        spell_power_multiplier=1.5
    ),

    Scroll(
        name="Scroll of Healing",
        description="Blessed parchment that mends wounds.",
        effect_description="Casts Heal at 150% power without mana cost.",
        value=50,
        level=1,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Heal"),
        spell_power_multiplier=1.5
    ),

    # Level 2-3 Spell Scrolls
    Scroll(
        name="Scroll of Lightning Bolt",
        description="Crackling with electrical energy.",
        effect_description="Casts Lightning Bolt at 150% power without mana cost.",
        value=80,
        level=2,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Lightning Bolt"),
        spell_power_multiplier=1.5
    ),

    Scroll(
        name="Scroll of Ice Storm",
        description="A frigid scroll that summons blizzards.",
        effect_description="Casts Ice Storm at 150% power without mana cost.",
        value=100,
        level=2,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Ice Storm"),
        spell_power_multiplier=1.5
    ),

    Scroll(
        name="Scroll of Greater Heal",
        description="Divine light emanates from this scroll.",
        effect_description="Casts Greater Heal at 150% power without mana cost.",
        value=90,
        level=2,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Greater Heal"),
        spell_power_multiplier=1.5
    ),

    Scroll(
        name="Scroll of Meteor Strike",
        description="Reality trembles around this scroll.",
        effect_description="Casts Meteor Strike at 150% power without mana cost.",
        value=150,
        level=3,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Meteor Strike"),
        spell_power_multiplier=1.5
    ),

    Scroll(
        name="Scroll of Chain Lightning",
        description="Arc lightning dances across the parchment.",
        effect_description="Casts Chain Lightning at 150% power without mana cost.",
        value=160,
        level=3,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Chain Lightning"),
        spell_power_multiplier=1.5
    ),

    # Level 4-5 Spell Scrolls (Rare)
    Scroll(
        name="Scroll of Inferno",
        description="The parchment itself seems to burn without consuming.",
        effect_description="Casts Inferno at 150% power without mana cost.",
        value=250,
        level=4,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Inferno"),
        spell_power_multiplier=1.5
    ),

    Scroll(
        name="Scroll of Full Restore",
        description="Radiates with pure restorative energy.",
        effect_description="Casts Full Restore at 150% power without mana cost.",
        value=300,
        level=4,
        scroll_type='spell_scroll',
        spell_to_cast=next(s for s in SPELL_TEMPLATES if s.name == "Full Restore"),
        spell_power_multiplier=1.5
    ),

    #  UTILITY SCROLLS - New tactical options

    Scroll(
        name="Scroll of Teleportation",
        description="Space itself warps around this scroll.",
        effect_description="Instantly teleport to a random safe location on the current floor.",
        value=100,
        level=2,
        scroll_type='teleport'
    ),

    Scroll(
        name="Scroll of Mapping",
        description="Contains the essence of cartographic magic.",
        effect_description="Reveals the entire current floor layout.",
        value=120,
        level=2,
        scroll_type='mapping'
    ),

    Scroll(
        name="Scroll of Protection",
        description="Glows with a protective aura.",
        effect_description="Grants +15 defense for 5 turns.",
        value=80,
        level=1,
        scroll_type='protection'
    ),

    Scroll(
        name="Scroll of Restoration",
        description="Pulses with healing light.",
        effect_description="Fully restore HP and remove all negative status effects.",
        value=200,
        level=3,
        scroll_type='restoration'
    ),

    Scroll(
        name="Scroll of Descent",
        description="Dark magic pulls downward from this scroll.",
        effect_description="Teleport down 1-3 floors instantly.",
        value=150,
        level=2,
        scroll_type='descent'
    ),

    # Keep existing scrolls
    Scroll(
        name="Scroll of Foresight",
        description="A scroll that reveals what lies ahead.",
        effect_description="Reveals three rows or columns in a chosen direction.",
        value=40,
        level=1,
        scroll_type='foresight'
    ),

    Scroll(
        name="Scroll of Upgrade",
        description="A mystical scroll that can enhance a weapon or armor up to +3.",
        effect_description="Upgrade items to +3 maximum.",
        value=150,
        level=1,  # Floor 1+ (available early)
        scroll_type='upgrade'
    ),
    Scroll(
        name="Scroll of Greater Upgrade",
        description="A powerful scroll that can enhance a weapon or armor up to +6.",
        effect_description="Upgrade items to +6 maximum.",
        value=250,
        level=5,  # Floor 5+
        scroll_type='upgrade'
    ),
    Scroll(
        name="Scroll of Superior Upgrade",
        description="An ancient scroll that can enhance a weapon or armor up to +10.",
        effect_description="Upgrade items to +10 maximum.",
        value=400,
        level=10,  # Floor 10+
        scroll_type='upgrade'
    ),
    Scroll(
        name="Scroll of Epic Upgrade",
        description="A legendary scroll pulsing with raw power.",
        effect_description="Upgrade items to +14 maximum.",
        value=600,
        level=15,  # Floor 15+
        scroll_type='upgrade'
    ),
    Scroll(
        name="Scroll of Mythic Upgrade",
        description="A scroll touched by the gods themselves.",
        effect_description="Upgrade items to +17 maximum.",
        value=850,
        level=20,  # Floor 20+
        scroll_type='upgrade'
    ),
    Scroll(
        name="Scroll of Divine Upgrade",
        description="The ultimate scroll of enhancement, forged in celestial fire.",
        effect_description="Upgrade items to +20 maximum.",
        value=1200,
        level=25,  # Floor 25+
        scroll_type='upgrade'
    ),
    Scroll(
        name="Scroll of Commerce",
        description="Restocks a vendor's inventory with new wares.",
        value=150,
        level=2,
        scroll_type='vendor_restock',
        effect_description='Restock one vendor on this floor'
    ),
    Scroll(
        name="Scroll of Lantern Upgrade",
        description="A mystical scroll that enhances your lantern's light.",
        effect_description="Permanently increases your lantern's reveal radius.",
        value=120,
        level=2,
        scroll_type='lantern_upgrade'
    ),
    Scroll(
        name="Scroll of Identify",
        description="Ancient runes of knowledge that reveal an item's true nature.",
        effect_description="Identifies one unidentified item in your inventory.",
        value=50,
        level=0,
        scroll_type='identify'
    ),
    Scroll(
        name="Scroll of Verdant Growth",
        description="Druidic magic pulses from this scroll, smelling of rich earth and wild flowers.",
        effect_description="Sprouts gardens in nearby rooms. May attract fey magic.",
        value=200,
        level=4,
        scroll_type='verdant_growth'
    ),
]


# ================================================================================
# UTILITY TEMPLATES
# ================================================================================

UTILITY_TEMPLATES = [
    Lantern(name="Lantern", description="Provides continuous light with fuel.", fuel_amount=10, light_radius=7, value=30, level=0),
    LanternFuel(name="Lantern Fuel", description="A small flask of oil for your lantern.", value=5, level=0, fuel_restore_amount=10),
    # Food items
    Food(name="Rations", description="Standard travel rations. Keeps hunger at bay.", value=10, level=0, nutrition=40, count=1),
    Food(name="Hardtack", description="Dense, dry biscuit. Filling if not delicious.", value=5, level=0, nutrition=25, count=1),
    Food(name="Dried Mushrooms", description="Cave mushrooms, dried and somewhat edible.", value=7, level=0, nutrition=20, count=1),
    Food(name="Salted Jerky", description="Dried meat of unknown origin. Salty and chewy.", value=15, level=1, nutrition=35, count=1),
    Food(name="Cheese Wedge", description="A wedge of pungent cave cheese.", value=12, level=1, nutrition=30, count=1),
    Food(name="Travelers Bread", description="Dense loaf that keeps for weeks. Nourishing.", value=20, level=2, nutrition=50, count=1),
    Food(name="Iron Rations", description="Military-grade rations. Tasteless but highly nutritious.", value=30, level=3, nutrition=70, count=1),
    CookingKit(name="Cooking Kit", description="Compact kit for cooking meat. Makes meat last longer and taste better.", value=120, level=3),
]


# ================================================================================
# UNIQUE TREASURE TEMPLATES
# ================================================================================

# NOTE: The use_effect callbacks (use_carnyx_of_doom, use_rhyton_of_purity, etc.)
# are defined in the main game module. They must be injected after import, or these
# templates must be imported from the main module where those functions are defined.
# For now, we use a late-binding approach: set use_effect to None and patch them
# at startup, OR import them from the game module that defines them.

# Placeholder for use_effect functions - these will be set by the main module
use_carnyx_of_doom = None
use_rhyton_of_purity = None
use_hourglass_of_ages = None
use_mirror_of_truth = None
use_chalice_of_plenty = None
use_crown_of_kings = None
use_merchants_horn = None
use_merchants_bell = None


def _build_unique_treasure_templates():
    """Build UNIQUE_TREASURE_TEMPLATES list. Called after use_effect functions are set."""
    return [
        #  LEGENDARY USABLE TREASURES

        Treasure(
            name="Carnyx of Doom",
            description="An ancient Celtic war horn that resonates with destructive power. Has 3 charges.",
            gold_value=0,
            value=1000,
            level=5,
            treasure_type='usable',
            is_unique=True,
            use_effect=use_carnyx_of_doom,
            benefit={'special': 'Kill all adjacent monsters (3 uses)'}
        ),

        Treasure(
            name="Rhyton of Purity",
            description="A sacred drinking vessel that purifies all liquids.",
            gold_value=0,
            value=800,
            level=4,
            treasure_type='usable',
            is_unique=True,
            use_effect=use_rhyton_of_purity,
            benefit={'special': 'Negate negative pool effects for 10 turns'}
        ),

        Treasure(
            name="Hourglass of Ages",
            description="An hourglass filled with sands of time itself. Can be used 3 times.",
            gold_value=0,
            value=1200,
            level=6,
            treasure_type='usable',
            is_unique=True,
            use_effect=use_hourglass_of_ages,
            benefit={'special': 'Full HP/MP restore + cleanse all effects (3 uses)'}
        ),

        Treasure(
            name="Mirror of Truth",
            description="A mirror that reveals all hidden things.",
            gold_value=0,
            value=600,
            level=3,
            treasure_type='usable',
            is_unique=True,
            use_effect=use_mirror_of_truth,
            benefit={'special': 'Reveal entire floor + monster info (reusable)'}
        ),

        Treasure(
            name="Chalice of Plenty",
            description="A golden chalice that creates treasures. Can be used 2 times.",
            gold_value=0,
            value=900,
            level=5,
            treasure_type='usable',
            is_unique=True,
            use_effect=use_chalice_of_plenty,
            benefit={'special': 'Generate random valuable loot (2 uses)'}
        ),

        Treasure(
            name="Crown of Kings",
            description="A crown worn by ancient rulers, radiating authority.",
            gold_value=0,
            value=1000,
            level=6,
            treasure_type='usable',
            is_unique=True,
            use_effect=use_crown_of_kings,
            benefit={'special': '+20 Atk/Def for 8 turns (reusable)'}
        ),

        #  LEGENDARY PASSIVE TREASURES

        Treasure(
            name="Ring of Regeneration",
            description="A mystical ring that slowly heals wounds over time.",
            gold_value=0,
            value=700,
            level=4,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+3 HP/turn',
            benefit={'special': 'Passive healing'}
        ),

        Treasure(
            name="Amulet of True Sight",
            description="An amulet that reveals the true nature of all things.",
            gold_value=0,
            value=500,
            level=3,
            treasure_type='passive',
            is_unique=True,
            passive_effect='Auto-ID all',
            benefit={'special': 'Perfect knowledge'}
        ),

        Treasure(
            name="Boots of Haste",
            description="Enchanted boots that blur with speed.",
            gold_value=0,
            value=600,
            level=4,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+5 Dex, no slow',
            benefit={'special': 'Speed boost'}
        ),

        Treasure(
            name="Cloak of Shadows",
            description="A dark cloak that makes you harder to hit.",
            gold_value=0,
            value=650,
            level=4,
            treasure_type='passive',
            is_unique=True,
            passive_effect='-20% enemy hit',
            benefit={'special': 'Dodge boost'}
        ),

        # NEW PASSIVE ACCESSORIES

        Treasure(
            name="Ring of Strength",
            description="A heavy iron ring that pulses with raw power.",
            gold_value=0,
            value=400,
            level=2,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+3 Str',
            benefit={'special': 'Strength boost'}
        ),

        Treasure(
            name="Circlet of Intelligence",
            description="A silver circlet that sharpens the mind.",
            gold_value=0,
            value=450,
            level=2,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+3 Int',
            benefit={'special': 'Intelligence boost'}
        ),

        Treasure(
            name="Gauntlets of Power",
            description="Heavy gauntlets crackling with energy.",
            gold_value=0,
            value=750,
            level=5,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+5 Atk',
            benefit={'special': 'Attack boost'}
        ),

        Treasure(
            name="Pendant of Fortitude",
            description="A sturdy pendant that hardens the body.",
            gold_value=0,
            value=750,
            level=5,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+5 Def',
            benefit={'special': 'Defense boost'}
        ),

        Treasure(
            name="Belt of the Giant",
            description="A massive belt once worn by a giant king.",
            gold_value=0,
            value=900,
            level=6,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+6 Str, +20 HP',
            benefit={'special': 'Giant strength'}
        ),

        Treasure(
            name="Wizard's Monocle",
            description="A magical monocle that enhances spellcasting.",
            gold_value=0,
            value=800,
            level=5,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+5 Int, +20 MP',
            benefit={'special': 'Arcane focus'}
        ),

        Treasure(
            name="Bracers of Balance",
            description="Elegant bracers that enhance all abilities equally.",
            gold_value=0,
            value=850,
            level=5,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+2 Str/Dex/Int',
            benefit={'special': 'Balanced enhancement'}
        ),

        Treasure(
            name="Anklet of Swiftness",
            description="A light anklet that quickens your movements.",
            gold_value=0,
            value=350,
            level=2,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+3 Dex',
            benefit={'special': 'Dexterity boost'}
        ),

        Treasure(
            name="Skull of the Mage",
            description="A crystallized skull humming with arcane energy.",
            gold_value=0,
            value=1000,
            level=7,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+8 Int, +2 MP/turn',
            benefit={'special': 'Arcane mastery'}
        ),

        Treasure(
            name="Champion's Signet",
            description="A signet ring worn by legendary warriors.",
            gold_value=0,
            value=950,
            level=7,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+4 Str/Dex, +10 Atk',
            benefit={'special': 'Champion power'}
        ),

        Treasure(
            name="Heartstone Pendant",
            description="A warm stone that beats like a heart.",
            gold_value=0,
            value=600,
            level=4,
            treasure_type='passive',
            is_unique=True,
            passive_effect='+30 HP, +2 HP/turn',
            benefit={'special': 'Vitality boost'}
        ),

        Treasure(
            name="Merchant's Horn",
            description="An ornate horn that summons merchants and compels them to restock.",
            gold_value=0,
            value=900,
            level=4,
            treasure_type='usable',
            is_unique=True,
            use_effect=use_merchants_horn,
            benefit={'special': 'Restock ALL vendors on current floor (reusable)'}
        ),

        # OPTIONAL: Add Merchant's Bell too
        Treasure(
            name="Merchant's Bell",
            description="A magical bell that summons a traveling merchant.",
            gold_value=0,
            value=1100,
            level=5,
            treasure_type='usable',
            is_unique=True,
            use_effect=use_merchants_bell,
            benefit={'special': 'Summon temporary merchant (reusable)'}
        ),
    ]


# ================================================================================
# ENHANCED MINOR TREASURE TEMPLATES
# ================================================================================

ENHANCED_MINOR_TREASURES = [
    #  GOLD TREASURES (Direct gold value)
    Treasure(
        name="Small Gem",
        description="A tiny, sparkling gem.",
        gold_value=20,
        value=20,
        level=0,
        treasure_type='gold'
    ),

    Treasure(
        name="Silver Necklace",
        description="A delicate silver chain.",
        gold_value=40,
        value=40,
        level=1,
        treasure_type='gold'
    ),

    Treasure(
        name="Gold Coin Pouch",
        description="A heavy pouch filled with gold coins.",
        gold_value=100,
        value=100,
        level=1,
        treasure_type='gold'
    ),

    Treasure(
        name="Ornate Goblet",
        description="A beautifully crafted goblet.",
        gold_value=75,
        value=75,
        level=1,
        treasure_type='gold'
    ),

    Treasure(
        name="Ruby Ring",
        description="A ring with a brilliant red ruby.",
        gold_value=150,
        value=150,
        level=2,
        treasure_type='gold'
    ),

    Treasure(
        name="Emerald Pendant",
        description="A pendant with a flawless emerald.",
        gold_value=180,
        value=180,
        level=2,
        treasure_type='gold'
    ),

    Treasure(
        name="Diamond Brooch",
        description="A brooch studded with diamonds.",
        gold_value=300,
        value=300,
        level=3,
        treasure_type='gold'
    ),

    Treasure(
        name="Ancient Coin Collection",
        description="A set of rare ancient coins.",
        gold_value=250,
        value=250,
        level=3,
        treasure_type='gold'
    ),

    #  EQUIPPABLE STAT ACCESSORIES
    Treasure(
        name="Amulet of Health",
        description="An amulet that increases vitality when worn.",
        gold_value=0,
        value=60,
        level=2,
        treasure_type='passive',
        passive_effect='+10 Max HP',
        benefit={'max_health': 10}
    ),

    Treasure(
        name="Ring of Protection",
        description="A ring that offers minor protection when worn.",
        gold_value=0,
        value=80,
        level=2,
        treasure_type='passive',
        passive_effect='+1 Def',
        benefit={'defense': 1}
    ),

    Treasure(
        name="Bracer of Strength",
        description="A bracer that increases muscle power when worn.",
        gold_value=0,
        value=100,
        level=3,
        treasure_type='passive',
        passive_effect='+2 Str',
        benefit={'strength': 2}
    ),

    Treasure(
        name="Circlet of Intellect",
        description="A circlet that sharpens the mind when worn.",
        gold_value=0,
        value=100,
        level=3,
        treasure_type='passive',
        passive_effect='+2 Int',
        benefit={'intelligence': 2}
    ),

    Treasure(
        name="Anklet of Agility",
        description="An anklet that improves reflexes when worn.",
        gold_value=0,
        value=100,
        level=3,
        treasure_type='passive',
        passive_effect='+2 Dex',
        benefit={'dexterity': 2}
    ),

    Treasure(
        name="Orb of Vitality",
        description="A glowing orb that greatly increases life force. Consumed on use.",
        gold_value=0,
        value=200,
        level=4,
        treasure_type='stat_boost',
        benefit={'max_health': 25}
    ),

    Treasure(
        name="Crystal of Power",
        description="A crystal that permanently enhances all attributes. Consumed on use.",
        gold_value=0,
        value=300,
        level=5,
        treasure_type='stat_boost',
        benefit={'strength': 1, 'dexterity': 1, 'intelligence': 1}
    ),
]


# ================================================================================
# VAULT DEFENDER TEMPLATES
# ================================================================================

VAULT_DEFENDER_TEMPLATES = [
    {
        'name': 'Vault Guardian Golem',
        'base_health': 150,
        'base_attack': 25,
        'base_defense': 15,
        'health_per_level': 30,
        'attack_per_level': 5,
        'defense_per_level': 3,
        'elemental_weakness': ['Earth'],
        'elemental_strength': ['Physical', 'Fire'],
        'attack_element': 'Physical',
        'flavor_text': 'An ancient construct powered by magical runes. Its sole purpose: guard the vault.',
        'victory_text': 'The golem crumbles, its enchantments broken. The vault treasure is yours!',
        'can_talk': True,
        'greeting_template': 'HALT, {name} {title}. You have entered the sacred vault. Defeat me, or perish. There is no escape.'
    },
    {
        'name': 'Vault Keeper Wraith',
        'base_health': 120,
        'base_attack': 30,
        'base_defense': 10,
        'health_per_level': 25,
        'attack_per_level': 6,
        'defense_per_level': 2,
        'elemental_weakness': ['Holy', 'Light'],
        'elemental_strength': ['Darkness', 'Physical'],
        'attack_element': 'Darkness',
        'flavor_text': 'A spectral guardian bound to the vault for eternity.',
        'victory_text': 'The wraith wails as it dissipates. The vault treasure is now unguarded!',
        'can_talk': True,
        'greeting_template': '{title} {name}... your life ends here. The vault\'s treasure is NOT for mortals!'
    },
    {
        'name': 'Vault Sentinel Dragon',
        'base_health': 180,
        'base_attack': 28,
        'base_defense': 12,
        'health_per_level': 35,
        'attack_per_level': 5,
        'defense_per_level': 3,
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Fire', 'Physical'],
        'attack_element': 'Fire',
        'flavor_text': 'A young dragon, bound by ancient magic to guard this vault until death.',
        'victory_text': 'The dragon roars one last time before collapsing. You have proven worthy of the vault treasure!',
        'can_talk': True,
        'greeting_template': 'So, {name} {title}, you dare challenge me? I am bound to this vault for eternity. Prepare to join me in death!'
    },
    {
        'name': 'Vault Warden Lich',
        'base_health': 100,
        'base_attack': 35,
        'base_defense': 8,
        'health_per_level': 20,
        'attack_per_level': 7,
        'defense_per_level': 2,
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness', 'Psionic'],
        'attack_element': 'Darkness',
        'flavor_text': 'An undead sorcerer, its soul trapped as eternal guardian of the vault.',
        'victory_text': 'The lich crumbles to dust. Its eternal vigil is finally over. The vault treasure is yours!',
        'can_talk': True,
        'greeting_template': 'Mortal fool, {name}... The vault will be your tomb. None have ever defeated me and lived!'
    },
    {
        'name': 'Vault Protector Titan',
        'base_health': 200,
        'base_attack': 22,
        'base_defense': 18,
        'health_per_level': 40,
        'attack_per_level': 4,
        'defense_per_level': 4,
        'elemental_weakness': ['Psionic'],
        'elemental_strength': ['Physical', 'Earth'],
        'attack_element': 'Physical',
        'flavor_text': 'A colossal construct of stone and steel, built to be the perfect guardian.',
        'victory_text': 'The titan falls with a thunderous crash. Against all odds, you have triumphed!',
        'can_talk': True,
        'greeting_template': '{name} {title}. ANALYSIS: THREAT LEVEL - INSUFFICIENT. INITIATING TERMINATION PROTOCOL.'
    }
]


# ================================================================================
# COMBINED TREASURE TEMPLATES
# ================================================================================

# UNIQUE_TREASURE_TEMPLATES is built lazily via _build_unique_treasure_templates()
# because the use_effect functions are defined in the main game module.
# The main module should call init_unique_treasures() after setting the use_effect refs.
UNIQUE_TREASURE_TEMPLATES = []

TREASURE_TEMPLATES = ENHANCED_MINOR_TREASURES + UNIQUE_TREASURE_TEMPLATES


# ================================================================================
# INGREDIENT TEMPLATES (for journal)
# ================================================================================

INGREDIENT_TEMPLATES = [
    Ingredient(name=name, description=desc, value=value, level=level, ingredient_type='herb')
    for name, desc, value, level, chance in GARDEN_INGREDIENTS
] + [
    Ingredient(name=name, description=desc, value=value, level=level, ingredient_type='fey')
    for name, desc, value, level, chance in FEY_GARDEN_INGREDIENTS
]


# ================================================================================
# ALL ITEM TEMPLATES (combined master list)
# ================================================================================

ALL_ITEM_TEMPLATES = (
    WEAPON_TEMPLATES +
    ARMOR_TEMPLATES +
    POTION_TEMPLATES +
    SCROLL_TEMPLATES +  #  Includes Scroll of Commerce
    UTILITY_TEMPLATES +
    TREASURE_TEMPLATES  #  Includes Merchant's Horn
)


# ================================================================================
# UNIQUE WEAPON AND ARMOR TEMPLATES
# ================================================================================

UNIQUE_WEAPON_TEMPLATES = [
    Weapon(name="Eldrich Sword", description="A wicked dark blade radiating magic.", attack_bonus=14, value=1500, level=20, upgrade_level=4, elemental_strength=['Darkness'], upgrade_limit=False),
    Weapon(name="Blade of the Phoenix", description="A sword that burns with eternal flame, said to rise from ashes.", attack_bonus=18, value=2500, level=25, upgrade_level=5, elemental_strength=['Fire'], upgrade_limit=False),
    Weapon(name="Stormbreaker Axe", description="A mighty axe that calls upon the fury of storms, capable of splitting mountains.", attack_bonus=20, value=2800, level=30, upgrade_level=6, elemental_strength=['Wind'], upgrade_limit=False),
    Weapon(name="Scepter of the Ancients", description="A staff imbued with primordial magic, granting wisdom and devastating arcane power.", attack_bonus=12, value=2000, level=22, upgrade_level=7, elemental_strength=['Psionic'], upgrade_limit=False),
    Weapon(name="Whisperwind Bow", description="An elven bow that shoots arrows silent as the wind, striking foes with unerring accuracy.", attack_bonus=16, value=2300, level=28, upgrade_level=5, elemental_strength=['Wind'], upgrade_limit=False),
    Weapon(name="Dragon's Tooth Blade", description="A sword forged from a dragon's fang, glowing with draconic energy.", attack_bonus=25, value=3500, level=35, upgrade_level=7, elemental_strength=['Fire'], upgrade_limit=False),
    Weapon(name="Hammer of the Titans", description="A colossal hammer wielded by ancient giants, capable of shattering mountains.", attack_bonus=30, value=4000, level=40, upgrade_level=8, elemental_strength=['Earth'], upgrade_limit=False),
    Weapon(name="Soulreaver Scythe", description="A sinister scythe that hungers for souls, said to steal life with every strike.", attack_bonus=28, value=3800, level=38, upgrade_level=6, elemental_strength=['Darkness'], upgrade_limit=False),
    Weapon(name="Shieldbreaker Maul", description="A heavy maul designed to crush defenses, leaving enemies vulnerable.", attack_bonus=22, value=3000, level=32, upgrade_level=7, elemental_strength=['Physical'], upgrade_limit=False),
    Weapon(name="Vorpal Blade", description="A legendary sword with an insatiable thirst for blood, known for its decapitating strikes.", attack_bonus=32, value=4500, level=42, upgrade_level=9, elemental_strength=['Physical'], upgrade_limit=False)
]

UNIQUE_ARMOR_TEMPLATES = [
    Armor(name="Eldrich Mail", description="An imposing suit of armor.", defense_bonus=12, value=2300, level=20, upgrade_level=8, elemental_strength=['Darkness'], upgrade_limit=False),
    Armor(name="Dragon Scale Armor", description="Forged from the scales of a mighty dragon, offering supreme protection.", defense_bonus=15, value=3000, level=25, upgrade_level=9, elemental_strength=['Fire'], upgrade_limit=False),
    Armor(name="Aegis of the Paladin", description="A holy plate armor imbued with divine protection, radiating a calming aura.", defense_bonus=18, value=3800, level=30, upgrade_level=10, elemental_strength=['Holy'], upgrade_limit=False),
    Armor(name="Shadow Cloak of Nocturne", description="A cloak woven from pure shadow, granting the wearer unparalleled stealth and defense against dark magic.", defense_bonus=10, value=2500, level=22, upgrade_level=8, elemental_strength=['Darkness'], upgrade_limit=False),
    Armor(name="Titan's Plate", description="Massive, heavy plate armor said to have been worn by a Titan, offering incredible physical defense.", defense_bonus=20, value=4200, level=35, upgrade_level=12, elemental_strength=['Earth'], upgrade_limit=False),
    Armor(name="Runesmith's Carapace", description="Dwarven plate armor etched with ancient runes, deflecting both physical and magical attacks.", defense_bonus=17, value=3500, level=28, upgrade_level=11, elemental_strength=['Physical'], upgrade_limit=False)
]


# Sort ALL_ITEM_TEMPLATES by item level
ALL_ITEM_TEMPLATES.sort(key=lambda item: item.level)


# ================================================================================
# INITIALIZATION HELPER
# ================================================================================

def init_unique_treasures(effect_funcs):
    """
    Initialize UNIQUE_TREASURE_TEMPLATES with use_effect functions from the main module.

    Args:
        effect_funcs: dict mapping function names to actual functions, e.g.:
            {
                'use_carnyx_of_doom': <function>,
                'use_rhyton_of_purity': <function>,
                ...
            }
    """
    global use_carnyx_of_doom, use_rhyton_of_purity, use_hourglass_of_ages
    global use_mirror_of_truth, use_chalice_of_plenty, use_crown_of_kings
    global use_merchants_horn, use_merchants_bell
    global UNIQUE_TREASURE_TEMPLATES, TREASURE_TEMPLATES, ALL_ITEM_TEMPLATES

    use_carnyx_of_doom = effect_funcs.get('use_carnyx_of_doom')
    use_rhyton_of_purity = effect_funcs.get('use_rhyton_of_purity')
    use_hourglass_of_ages = effect_funcs.get('use_hourglass_of_ages')
    use_mirror_of_truth = effect_funcs.get('use_mirror_of_truth')
    use_chalice_of_plenty = effect_funcs.get('use_chalice_of_plenty')
    use_crown_of_kings = effect_funcs.get('use_crown_of_kings')
    use_merchants_horn = effect_funcs.get('use_merchants_horn')
    use_merchants_bell = effect_funcs.get('use_merchants_bell')

    UNIQUE_TREASURE_TEMPLATES[:] = _build_unique_treasure_templates()
    TREASURE_TEMPLATES[:] = ENHANCED_MINOR_TREASURES + UNIQUE_TREASURE_TEMPLATES

    ALL_ITEM_TEMPLATES[:] = (
        WEAPON_TEMPLATES +
        ARMOR_TEMPLATES +
        POTION_TEMPLATES +
        SCROLL_TEMPLATES +
        UTILITY_TEMPLATES +
        TREASURE_TEMPLATES
    )
    ALL_ITEM_TEMPLATES.sort(key=lambda item: item.level)

# Magic shop constants
MAGIC_SHOP_CHANCE = 0.15  # 15% chance on floors 20+
MAGIC_SHOP_MIN_FLOOR = 20
