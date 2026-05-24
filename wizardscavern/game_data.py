# game_data.py - Wizard's Cavern game data tables
#
# Pure data definitions extracted from the main game file.
# Contains monster templates, spawn ranges, evolution tiers,
# trophy drops, and taxidermist collections.
#
# ASCII only - no Unicode, emojis, or special characters.

# ============================================================================
# COMPLETE MONSTER TEMPLATES WITH SPECIAL ATTACKS
# ============================================================================
# ALL 55 monsters with carefully balanced special attacks
# Copy these entire monster definitions to replace your MONSTER_TEMPLATES
# ============================================================================

# Monster spawn floor ranges: template_level -> (first_floor, last_floor)
# Sixteen tiers span the full 50-floor descent. Each tier covers a band of
# floors and overlaps its neighbours so every floor draws from 2-5 distinct
# tiers. Low tiers phase out as you descend and genuinely stronger monsters
# (defined natively, not re-skinned with a prefix) take their place.
MONSTER_SPAWN_FLOOR_RANGE = {
    0:  (0, 5),    # Bats, rats, kobolds
    1:  (0, 7),    # Goblins, skeletons
    2:  (1, 9),    # Orcs, gnolls, bugbears
    3:  (3, 12),   # Ogres, trolls, minotaurs
    4:  (5, 15),   # Wraiths, basilisks, hill giants
    5:  (7, 18),   # Mummies, werewolves, manticores
    6:  (9, 20),   # Vampires, golems, dragon liches
    7:  (11, 23),  # Beholders, mind flayers, young dragons
    8:  (13, 26),  # Frost giants, fire elementals, rocs
    9:  (16, 29),  # Sphinxes, efreeti, fire giants
    10: (18, 32),  # Ancient dragons, tarrasque, balor
    11: (20, 35),  # Voidspawn, cinder serpents, lesser horrors
    12: (24, 39),  # Djinn, hollow liches, drakes
    13: (28, 44),  # Abyssal fiends, illithid overminds, colossi
    14: (32, 49),  # Archfiends, wyrmlords, glacial titans
    15: (43, 49),  # Zot's elite: starspawn, infernal warlords, the unmaking
}

# ============================================================================
# TROPHY SYSTEM - drops, collections, and taxidermist rewards
# ============================================================================

# Maps monster name -> (trophy_name, description, value, drop_chance)
TROPHY_DROPS = {
    # BEAST collection pieces
    "Giant Spider":    ("Giant Spider Silk",      "Thick, silvery strands of spider silk.",          40,  0.30),
    "Owlbear":         ("Owlbear Feather",         "A large, tawny feather from an owlbear.",         45,  0.30),
    "Displacer Beast": ("Displacer Beast Hide",    "Iridescent hide that still seems to shift.",      55,  0.25),

    # SERPENT collection pieces
    "Basilisk":        ("Basilisk Scale",          "A grey scale with a faint petrifying residue.",   50,  0.28),
    "Naga Guardian":   ("Naga Scale",              "A golden scale from a naga guardian.",            55,  0.25),
    "Naga":            ("Naga Scale",              "A golden scale from a naga.",                     50,  0.28),
    "Wyvern":          ("Wyvern Barb",             "A venomous tail barb still dripping poison.",     60,  0.25),

    # UNDEAD collection pieces
    "Skeleton":        ("Skeleton Bone Dust",      "Fine grey powder ground from cursed bones.",      25,  0.35),
    "Wight":           ("Wight Finger",            "A blackened finger that radiates cold.",          40,  0.30),
    "Mummy":           ("Mummy Wrappings",         "Ancient bandages soaked in preservation oils.",   50,  0.28),

    # GIANT collection pieces
    "Hill Giant":      ("Hill Giant Knuckle",      "A scarred knuckle the size of a fist.",           55,  0.28),
    "Cyclops":         ("Cyclops Eye",             "A massive single eye, still glassy and huge.",    65,  0.22),
    "Frost Giant":     ("Frost Giant Shard",       "A shard of ice-blue bone from a frost giant.",   65,  0.22),

    # DRAKE collection pieces
    "Young Dragon":    ("Young Dragon Scale",      "A crimson scale still warm to the touch.",        70,  0.22),
    "Hell Hound":      ("Hell Hound Ember",        "A smoldering coal pulled from a hell hound.",     45,  0.30),

    # DEEP HORROR collection pieces
    "Mind Flayer":     ("Mind Flayer Tendril",     "A pale tentacle that still twitches faintly.",    75,  0.20),
    "Beholder":        ("Beholder Eyestalk",       "A severed eyestalk, its gaze forever fixed.",     80,  0.18),
    "Elder Brain":     ("Elder Brain Lobe",        "A pulsing grey lobe from an elder brain.",        90,  0.15),

    # APEX PREDATOR collection pieces
    "Manticore":       ("Manticore Spine",         "A hollow spine loaded with dried venom.",         65,  0.22),
    "Griffin":         ("Griffin Feather",         "A golden flight feather as long as a sword.",     70,  0.22),
    "Roc":             ("Roc Talon",               "A talon as long as a dagger, razor-sharp.",       80,  0.18),

    # BUG HIVE collection pieces (Shrinking Bug Level)
    "Titan Beetle":    ("Titan Beetle Horn",       "A curved horn of iridescent chitin, impossibly hard.",         30,  0.35),
    "Stinkbug Brute":  ("Stinkbug Gland",          "A swollen gland that still reeks. Handle with care.",         25,  0.35),
    "Fly Swarm":       ("Fly Swarm Wings",         "A handful of iridescent fly wings, still buzzing faintly.",   20,  0.40),
    "Pill Bug Golem":  ("Pill Bug Shell Plate",    "A curved armor plate from a pill bug's carapace.",            30,  0.35),
    "Firefly Mage":    ("Firefly Lantern Gland",   "A bioluminescent organ that pulses with soft green light.",   35,  0.30),
    "Ant Soldier":     ("Ant Mandible",            "A serrated mandible that could cut through stone.",           25,  0.35),
    "Dung Beetle Lord": ("Dung Beetle Carapace",   "A polished piece of dung beetle shell, surprisingly pretty.", 30,  0.35),
    "Dragonfly Enchantress": ("Dragonfly Wing Dust", "Shimmering scales from an enchanted dragonfly wing.",         35,  0.30),
    "Earthworm":       ("Earthworm Segment",       "A tough, rubbery segment of giant earthworm.",               15,  0.45),
    "Snail":           ("Snail Shell Shard",        "A pearlescent fragment of snail shell, surprisingly hard.",  20,  0.40),
    "BUG QUEEN":       ("Royal Chitin Crown",      "A fragment of the Bug Queen's crown, thrumming with power.",  60,  0.80),
}

# Seven collections: each needs exactly 3 trophy pieces
# Reward is a Treasure item that gets auto-equipped if a slot is free
TAXIDERMIST_COLLECTIONS = {
    "Beast Hunter": {
        "pieces": ["Giant Spider Silk", "Owlbear Feather", "Displacer Beast Hide"],
        "reward_name": "Cloak of the Hunter",
        "reward_desc": "Forged from apex predator hides. +3 DEX, attacks have a 15% chance to bypass enemy defense.",
        "reward_value": 1800,
        "reward_level": 5,
        "flavor": "The taxidermist stitches the hides together with practiced hands. 'Few survive all three. This cloak remembers their power.'",
    },
    "Serpent Slayer": {
        "pieces": ["Basilisk Scale", "Naga Scale", "Wyvern Barb"],
        "reward_name": "Venom Ward Amulet",
        "reward_desc": "Crafted from serpent scales and venom barbs. Grants permanent poison immunity and +2 DEX.",
        "reward_value": 2000,
        "reward_level": 6,
        "flavor": "The taxidermist grinds the barb into the clasp. 'Poison runs in all three. Wear this and it runs away from you.'",
    },
    "Undead Bane": {
        "pieces": ["Skeleton Bone Dust", "Wight Finger", "Mummy Wrappings"],
        "reward_name": "Holy Brand Ring",
        "reward_desc": "Infused with the remains of three undead. Your weapon deals +8 bonus Holy damage. +2 to all stats.",
        "reward_value": 2200,
        "reward_level": 6,
        "flavor": "The taxidermist burns the wrappings and presses the ash into the ring. 'The dead give their power to you now.'",
    },
    "Giant Killer": {
        "pieces": ["Hill Giant Knuckle", "Cyclops Eye", "Frost Giant Shard"],
        "reward_name": "Belt of Giant Slaying",
        "reward_desc": "Made from the remains of three giants. +30 Max HP, +5 STR, +5 DEF.",
        "reward_value": 2400,
        "reward_level": 7,
        "flavor": "The taxidermist hammers the shard into the buckle. 'You killed things that kill armies. Wear that.'",
    },
    "Drake Hunter": {
        "pieces": ["Young Dragon Scale", "Hell Hound Ember", "Wyvern Barb"],
        "reward_name": "Drake Cloak",
        "reward_desc": "Scales and ember-hide bound together. Grants permanent fire resistance (Fire damage -60%). +4 DEF.",
        "reward_value": 2200,
        "reward_level": 7,
        "flavor": "The taxidermist dips the scale in the ember. 'Fire made this. Fire won't touch you now.'",
    },
    "Deep Horror": {
        "pieces": ["Mind Flayer Tendril", "Beholder Eyestalk", "Elder Brain Lobe"],
        "reward_name": "Psychic Shield Circlet",
        "reward_desc": "Wired from aberration parts. Grants permanent confusion immunity. +6 INT, +10 Max Mana.",
        "reward_value": 2600,
        "reward_level": 8,
        "flavor": "The taxidermist works in silence, eyes averted. 'Don't look at the lobe while I work. Just don't.'",
    },
    "Apex Predator": {
        "pieces": ["Manticore Spine", "Griffin Feather", "Roc Talon"],
        "reward_name": "Apex Predator Signet",
        "reward_desc": "Ring set with the trophies of the sky's three greatest hunters. +8 ATK, +5 DEX, +3 STR.",
        "reward_value": 2800,
        "reward_level": 9,
        "flavor": "The taxidermist sets the talon in silver. 'Every creature in this cavern will sense this ring and think twice.'",
    },
    "Bug Hive": {
        "pieces": ["Royal Chitin Crown", "Titan Beetle Horn", "Dragonfly Wing Dust"],
        "reward_name": "Chitin Crown of the Hive",
        "reward_desc": "A crown forged from the bug hive's mightiest. +4 DEF, +3 ATK, grants permanent paralysis immunity.",
        "reward_value": 1500,
        "reward_level": 4,
        "flavor": "The bug taxidermist clicks excitedly. 'Crown... horn... dust... YES! A masterwork! The hive's power is yours, tiny one!'",
        "is_bug": True,
    },
    "Swarm Warden": {
        "pieces": ["Fly Swarm Wings", "Ant Mandible", "Stinkbug Gland"],
        "reward_name": "Swarm Caller's Brooch",
        "reward_desc": "A brooch that hums with swarm energy. +3 DEX, +2 ATK, 20% chance to summon a fly swarm on hit.",
        "reward_value": 1200,
        "reward_level": 3,
        "flavor": "The dung beetle threads the wings together with mandible wire. 'The swarm remembers its own. They'll fight for you now.'",
        "is_bug": True,
    },
    "Shell Breaker": {
        "pieces": ["Pill Bug Shell Plate", "Dung Beetle Carapace", "Snail Shell Shard"],
        "reward_name": "Carapace Shield Ring",
        "reward_desc": "A ring of interlocking shell fragments. +5 DEF, +15 Max HP, 10% chance to reflect damage.",
        "reward_value": 1300,
        "reward_level": 3,
        "flavor": "The dung beetle polishes each piece to a mirror shine. 'Hard outside, safe inside. The hive's oldest lesson.'",
        "is_bug": True,
    },
    "Glow Hunter": {
        "pieces": ["Firefly Lantern Gland", "Earthworm Segment", "Dragonfly Wing Dust"],
        "reward_name": "Bioluminescent Pendant",
        "reward_desc": "A glowing pendant that pulses with life. +4 INT, +8 Max Mana, reveals hidden rooms on the floor.",
        "reward_value": 1400,
        "reward_level": 4,
        "flavor": "The dung beetle holds the gland up to the light. 'Glow and dust and earth. The deep places will open for you.'",
        "is_bug": True,
    },
}


MONSTER_TEMPLATES = [

    # ========================================================================
    # LEVEL 0 - Weak Creatures (Tutorial Monsters)
    # ========================================================================

    {
        'name': "Slime Mold",
        'health': 15,
        'attack': 5,
        'defense': 0,
        'level': 0,
        'flavor_text': "A gelatinous blob quivers menacingly.",
        'victory_text': "The slime mold dies. It's now a melty and gross puddle on the floor.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Water'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.15,
            'duration': 2,
            'magnitude': 3,
            'description': 'covers you in sticky slime'
        }
    },

    {
        'name': "Sewer Rat",
        'health': 10,
        'attack': 4,
        'defense': 0,
        'level': 0,
        'flavor_text': "A scurrying rat, unnaturally large.",
        'victory_text': "The rat squeals the last squeal it will ever squeal.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Darkness'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.10,
            'duration': 2,
            'magnitude': 2,
            'description': 'bites you with disease-ridden teeth'
        }
    },

    {
        'name': "Bat",
        'health': 12,
        'attack': 3,
        'defense': 0,
        'level': 0,
        'flavor_text': "A cranky flying puppy intent on violence.",
        'victory_text': "The bat crashes to the floor all dead and stuff.",
        'elemental_weakness': ['Wind'],
        'elemental_strength': ['Darkness'],
        'can_talk': False
        # No special attack - bats are just fast and annoying
    },

    {
        'name': "Giant Centipede",
        'health': 15,
        'attack': 5,
        'defense': 0,
        'level': 0,
        'flavor_text': "Like a bunch of bugs sewn together face to butt.",
        'victory_text': "The centipede's legs curl up, motionless.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.20,
            'duration': 3,
            'magnitude': 3,
            'description': 'injects weak venom'
        }
    },

    {
        'name': "Lichen",
        'health': 10,
        'attack': 2,
        'defense': 0,
        'level': 0,
        'flavor_text': "A slow and menacing living amalgam of fungus and plant. Like nature but mean.",
        'victory_text': "The lichen lies motionless at your feet.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Earth'],
        'can_talk': False
        # No special attack - lichen is just slow and weak
    },

    # ========================================================================
    # LEVEL 1 - Basic Dungeon Monsters
    # ========================================================================

    {
        'name': "Goblin",
        'health': 30,
        'attack': 10,
        'defense': 2,
        'level': 1,
        'flavor_text': "A small, green-skinned goblin snarls at you.",
        'victory_text': "The goblin yelps and falls, its snarl replaced by a whimper.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Physical'],
        'can_talk': True,
        'greeting_template': "Hehehe! {name} {title}? Goblin gonna bash you good!"
        # No special attack - basic enemy
    },

    {
        'name': "Skeleton",
        'health': 25,
        'attack': 12,
        'defense': 3,
        'level': 1,
        'flavor_text': "Rattling bones form a reanimated skeleton. It was practicing a TikTok before you barged in.",
        'victory_text': "The skeleton clatters to pieces, its unholy animation ceased.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.15,
            'duration': 3,
            'magnitude': 4,
            'description': 'chills you with its undead touch'
        }
    },

    {
        'name': "Kobold",
        'health': 20,
        'attack': 8,
        'defense': 1,
        'level': 1,
        'flavor_text': "A small, dog-like humanoid yaps angrily.",
        'victory_text': "The kobold whines as it falls, its primitive weapon clattering.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Fire'],
        'can_talk': False
        # No special attack - weak basic enemy
    },

    {
        'name': "Giant Rat",
        'health': 22,
        'attack': 7,
        'defense': 1,
        'level': 1,
        'flavor_text': "A rat the size of a dog, with yellowed teeth.",
        'victory_text': "The giant rat squeals its last giant squeal it will ever giant squeal.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Darkness'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.12,
            'duration': 3,
            'magnitude': 2,
            'description': 'infects you with filth fever which is very different than Disco fever'
        }
    },

    {
        'name': "Zombie",
        'health': 35,
        'attack': 9,
        'defense': 1,
        'level': 1,
        'flavor_text': "A shambling corpse reaches for you with rotting hands. If it's looking for brains, it's come to the wrong place.",
        'victory_text': "The zombie collapses, truly dead this time.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Darkness'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.20,
            'duration': 4,
            'magnitude': 5,
            'description': 'grabs you with necrotic claws'
        }
    },

    {
        'name': "Spore Puff",
        'health': 18,
        'attack': 6,
        'defense': 0,
        'level': 1,
        'flavor_text': "A fat, wobbly mushroom the size of a pumpkin waddles toward you, puffing clouds of yellowish spores.",
        'victory_text': "The Spore Puff bursts with a wet pop, releasing one final cloud of harmless spores.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'food_rot',
            'chance': 0.25,
            'duration': 1,
            'magnitude': 1,
            'description': 'puffs a cloud of rotting spores at your pack'
        }
    },

    # ========================================================================
    # LEVEL 2 - Dangerous Encounters
    # ========================================================================

    {
        'name': "Orc",
        'health': 50,
        'attack': 15,
        'defense': 5,
        'level': 2,
        'flavor_text': "A brutish orc wielding a crude weapon.",
        'victory_text': "The orc falls with a grunt, defeated.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Darkness'],
        'can_talk': True,
        'greeting_template': "{name}? Puny {title}! Orc smash! Orc Smash is a Trademark of dungeon crawler llc."
        # No special attack - just hits hard
    },

    {
        'name': "Giant Spider",
        'health': 40,
        'attack': 18,
        'defense': 4,
        'level': 2,
        'flavor_text': "An enormous spider with eight glaring eyes. It's a spiiiiiiiider.",
        'victory_text': "The spider curls up, its legs twitching one last time.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'web',
            'chance': 0.35,
            'duration': 3,
            'magnitude': 0,
            'description': 'shoots sticky webbing at you'
        }
    },

    {
        'name': "Gnoll",
        'health': 45,
        'attack': 13,
        'defense': 3,
        'level': 2,
        'flavor_text': "A hyena-like humanoid cackles menacingly. Time to chow down!",
        'victory_text': "The gnoll's laughter dies as it falls.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': False
        # No special attack - basic fighter
    },

    {
        'name': "Wight",
        'health': 40,
        'attack': 16,
        'defense': 4,
        'level': 2,
        'flavor_text': "An undead warrior with burning eyes.",
        'victory_text': "The wight's malevolent spirit dissipates.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.25,
            'duration': 1,
            'magnitude': 6,
            'description': 'drains your life force with its touch'
        }
    },

    {
        'name': "Bugbear",
        'health': 55,
        'attack': 14,
        'defense': 4,
        'level': 2,
        'flavor_text': "A large, hairy goblinoid stalks toward you.",
        'victory_text': "The bugbear slumps to the ground, defeated.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': False
        # No special attack - just tough
    },

    {
        'name': "Myconid Shaman",
        'health': 45,
        'attack': 12,
        'defense': 3,
        'level': 2,
        'flavor_text': "A hunched, robed figure made entirely of interlocking mushroom caps. It raises a staff tipped with a pulsing spore sac.",
        'victory_text': "The Myconid Shaman crumples, its colony link severed. Spores drift from its body like smoke.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'food_rot',
            'chance': 0.30,
            'duration': 1,
            'magnitude': 2,
            'description': 'blasts a concentrated spore cloud at your provisions'
        }
    },

    # ========================================================================
    # LEVEL 3 - Serious Threats
    # ========================================================================

    {
        'name': "Troll",
        'health': 70,
        'attack': 20,
        'defense': 6,
        'level': 3,
        'flavor_text': "A large troll. It's drooling. Why is it drooling?",
        'victory_text': "The troll falls with a thunderous crash.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        # Trolls regenerate -- knit wounds shut each turn unless you out-damage it.
        'regen': 0.07
    },

    {
        'name': "Ogre",
        'health': 80,
        'attack': 18,
        'defense': 7,
        'level': 3,
        'flavor_text': "A massive humanoid of muscle and rage.",
        'victory_text': "The ogre crashes down like a felled tree.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': True,
        'greeting_template': "Ogre hungry! {name} look tasty!"
        # No special attack - pure strength
    },

    {
        'name': "Minotaur",
        'health': 75,
        'attack': 22,
        'defense': 6,
        'level': 3,
        'flavor_text': "A bull-headed warrior charges at you.",
        'victory_text': "The minotaur falls with a final snort.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.25,
            'duration': 1,
            'magnitude': 0,
            'description': 'gores you with a goring charge that leaves you reeling'
        }
    },

    {
        'name': "Gargoyle",
        'health': 60,
        'attack': 25,
        'defense': 8,
        'level': 3,
        'flavor_text': "A stone creature comes to life with a grinding sound.",
        'victory_text': "The gargoyle crumbles into rubble.",
        'elemental_weakness': ['Earth'],
        'elemental_strength': ['Wind'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.25,
            'duration': 3,
            'magnitude': 6,
            'description': 'strikes with stone fists'
        }
    },

    {
        'name': "Hell Hound",
        'health': 65,
        'attack': 23,
        'defense': 5,
        'level': 3,
        'flavor_text': "A demonic dog wreathed in flames.",
        'victory_text': "The hell hound's flames extinguish as it dies.",
        'elemental_weakness': ['Water'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': False,
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.40,
            'duration': 3,
            'magnitude': 6,
            'description': 'breathes hellfire at you'
        }
    },

    {
        'name': "Fungal Hulk",
        'health': 80,
        'attack': 21,
        'defense': 7,
        'level': 3,
        'flavor_text': "A hulking mass of interwoven fungal growth the size of a bear. Every impact sends spore clouds billowing from its body.",
        'victory_text': "The Fungal Hulk collapses with a deep, wet crack. A foul-smelling cloud of spores hangs in the air where it stood.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Earth'],
        'attack_element': 'Earth',
        'can_talk': False,
        'special_attack': {
            'effect_type': 'food_rot',
            'chance': 0.35,
            'duration': 1,
            'magnitude': 3,
            'description': 'slams you with a spore-laden fist, drenching your pack in rot'
        }
    },

    # ========================================================================
    # LEVEL 4 - Elite Monsters
    # ========================================================================

    {
        'name': "Wraith",
        'health': 80,
        'attack': 28,
        'defense': 7,
        'level': 4,
        'flavor_text': "A spectral figure radiates cold hatred.",
        'victory_text': "The wraith dissipates with a final wail.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Shadow',
        'can_talk': False,
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.40,
            'duration': 1,
            'magnitude': 10,
            'description': 'touches you with icy ethereal claws'
        }
    },

    {
        'name': "Basilisk",
        'health': 90,
        'attack': 25,
        'defense': 10,
        'level': 4,
        'flavor_text': "A serpentine creature with a deadly gaze.",
        'victory_text': "The basilisk's eyes dim as it falls.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.30,
            'duration': 2,
            'magnitude': 0,
            'description': 'locks eyes with you, beginning to turn you to stone'
        }
    },

    {
        'name': "Specter",
        'health': 70,
        'attack': 26,
        'defense': 6,
        'level': 4,
        'flavor_text': "A ghostly apparition phases in and out of reality.",
        'victory_text': "The specter fades from existence.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Shadow',
        'can_talk': False,
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.35,
            'duration': 1,
            'magnitude': 8,
            'description': 'drains your essence'
        }
    },

    {
        'name': "Otyugh",
        'health': 110,
        'attack': 20,
        'defense': 12,
        'level': 4,
        'flavor_text': "A repulsive creature covered in filth and tentacles.",
        'victory_text': "The otyugh collapses into its own refuse.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.45,
            'duration': 5,
            'magnitude': 7,
            'description': 'infects you with disgusting filth'
        }
    },

    {
        'name': "Hill Giant",
        'health': 130,
        'attack': 22,
        'defense': 8,
        'level': 4,
        'flavor_text': "An enormous brute wielding a tree trunk.",
        'victory_text': "The hill giant topples like a falling mountain.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': True,
        'greeting_template': "Fee fi fo fum! {name} die!",
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 6,
            'description': 'slams its tree-trunk club down, leaving you dazed'
        }
    },

    # ========================================================================
    # LEVEL 5 - Very Dangerous
    # ========================================================================

    {
        'name': "Mummy",
        'health': 95,
        'attack': 30,
        'defense': 10,
        'level': 5,
        'flavor_text': "Ancient bandages conceal unholy power.",
        'victory_text': "The mummy crumbles to dust, its curse lifted.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.45,
            'duration': 5,
            'magnitude': 10,
            'description': 'curses you with ancient magic'
        }
    },

    {
        'name': "Grick",
        'health': 80,
        'attack': 28,
        'defense': 15,
        'level': 5,
        'flavor_text': "A worm-like predator with a beak and tentacles.",
        'victory_text': "The grick's tentacles fall limp.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.25,
            'duration': 2,
            'magnitude': 0,
            'description': 'constricts you with its tentacles'
        }
    },

    {
        'name': "Grell",
        'health': 75,
        'attack': 32,
        'defense': 10,
        'level': 5,
        'flavor_text': "A floating brain with a beak and tentacles writhing beneath. So weird.",
        'victory_text': "The grell's tentacles go limp as it crashes down.",
        'elemental_weakness': ['Psionic'],
        'elemental_strength': ['Wind'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.35,
            'duration': 2,
            'magnitude': 0,
            'description': 'paralyzes you with its tentacles'
        }
    },

    {
        'name': "Umber Hulk",
        'health': 140,
        'attack': 25,
        'defense': 18,
        'level': 5,
        'flavor_text': "An insectoid behemoth with massive mandibles.",
        'victory_text': "The umber hulk collapses with a chittering cry.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'confusion',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 0,
            'description': 'disorients you with its confusing gaze'
        }
    },

    {
        'name': "Displacer Beast",
        'health': 105,
        'attack': 35,
        'defense': 10,
        'level': 5,
        'flavor_text': "A panther-like creature that appears in multiple places at once.",
        'victory_text': "The displacer beast's image solidifies as it dies.",
        'elemental_weakness': ['Light'],
        'elemental_strength': ['Darkness'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'blindness',
            'chance': 0.40,
            'duration': 3,
            'magnitude': 0,
            'description': 'blurs into a half-dozen afterimages, baffling your aim'
        }
    },

    # ========================================================================
    # LEVEL 6 - Boss Territory
    # ========================================================================

    {
        'name': "Gorgon",
        'health': 160,
        'attack': 35,
        'defense': 15,
        'level': 6,
        'flavor_text': "A bull-like creature with metallic scales.",
        'victory_text': "The gorgon's petrifying breath finally stills.",
        'elemental_weakness': ['Demonic'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.40,
            'duration': 3,
            'magnitude': 0,
            'description': 'breathes petrifying gas at you'
        }
    },

    {
        'name': "Iron Golem",
        'health': 180,
        'attack': 30,
        'defense': 25,
        'level': 6,
        'flavor_text': "A massive construct of iron and magic.",
        'victory_text': "The iron golem falls with an echoing crash.",
        'elemental_weakness': ['Earth'],
        'elemental_strength': ['Physical'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.35,
            'duration': 4,
            'magnitude': 12,
            'description': 'strikes you with overwhelming force'
        }
    },

    {
        'name': "Medusa",
        'health': 95,
        'attack': 48,
        'defense': 9,
        'level': 6,
        'flavor_text': "Serpents writhe where hair should be.",
        'victory_text': "The medusa's petrifying gaze fades forever.",
        'elemental_weakness': ['Light'],
        'elemental_strength': ['Darkness'],
        'can_talk': True,
        'greeting_template': "Look upon me, {name}, and despair!",
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.40,
            'duration': 3,
            'magnitude': 0,
            'description': 'meets your gaze, turning you to stone'
        }
    },

    {
        'name': "Lich",
        'health': 130,
        'attack': 45,
        'defense': 10,
        'level': 6,
        'flavor_text': "An undead sorcerer radiates arcane power.",
        'victory_text': "The lich's phylactery shatters, ending its existence.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Shadow',
        'can_talk': True,
        'greeting_template': "Fool! {name} the {title} dares challenge immortality itself?",
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.55,
            'duration': 6,
            'magnitude': 15,
            'description': 'blasts you with necromantic energy'
        },
        'spell_chance': 0.35,
        'spells': [
            {'name': 'Necrotic Bolt', 'type': 'damage', 'element': 'Shadow', 'power': 26,
             'cast_text': 'raises a skeletal hand and hurls a crackling bolt of necrotic energy'},
            {'name': 'Drain Vitality', 'type': 'heal', 'power': 28,
             'cast_text': 'siphons the life from the air to knit its rotting form back together'},
            {'name': 'Force Shield', 'type': 'self_buff', 'effect_type': 'hit_absorb', 'duration': 4, 'magnitude': 2,
             'cast_text': 'weaves a shimmering shield of force around itself'},
        ]
    },

    {
        'name': "Vampire",
        'health': 110,
        'attack': 40,
        'defense': 10,
        'level': 6,
        'flavor_text': "A pale figure moves with unnatural grace.",
        'victory_text': "The vampire crumbles to ash with a final shriek.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Shadow',
        'can_talk': True,
        'greeting_template': "Ah, {name} the {title}... Your blood smells delicious. What!? You live as long as I do and you get into some wierd stuff.",
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.55,
            'duration': 1,
            'magnitude': 15,
            'description': 'sinks its fangs into your neck'
        }
    },

    # ========================================================================
    # LEVEL 7 - Major Bosses
    # ========================================================================

    {
        'name': "Dragon Lich",
        'health': 95,
        'attack': 32,
        'defense': 12,
        'level': 7,
        'flavor_text': "A skeletal dragon wreathed in necrotic energy, its hollow eye sockets burn with malevolent intelligence.",
        'victory_text': "The dragon lich crumbles to dust, its phylactery shattered.",
        'elemental_weakness': ['Fire', 'Holy'],
        'elemental_strength': ['Ice', 'Dark'],
        'attack_element': 'Dark',
        'can_talk': True,
        'greeting_template': "I have conquered death itself... you are merely an inconvenience.",
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.40,
            'duration': 4,
            'magnitude': 8,
            'description': 'exhales a wave of necrotic breath'
        },
        'spell_chance': 0.32,
        'spells': [
            {'name': 'Necrotic Bolt', 'type': 'damage', 'element': 'Dark', 'power': 22,
             'cast_text': 'gathers shadow between its horns and hurls a bolt of necrotic energy'},
            {'name': 'Bone Mending', 'type': 'heal', 'power': 22,
             'cast_text': 'drags loose bone and shadow back into its frame, mending itself'},
        ]
    },

    {
        'name': "Beholder",
        'health': 100,
        'attack': 35,
        'defense': 12,
        'level': 7,
        'flavor_text': "A floating orb covered in eyes, each one deadly. It's looking for a contact lens.",
        'victory_text': "The beholder's central eye dims as it falls to the floor.",
        'elemental_weakness': ['Psionic'],
        'elemental_strength': ['Light'],
        'can_talk': True,
        'greeting_template': "Your presence offends my eyes, {name} the {title}.",
        'special_attack': {
            'effect_type': 'confusion',
            'chance': 0.60,
            'duration': 4,
            'magnitude': 0,
            'description': 'fires a disintegration ray from one of its eyes'
        },
        'spell_chance': 0.45,
        'spells': [
            {'name': 'Disintegration Ray', 'type': 'damage', 'element': 'Arcane', 'power': 30,
             'cast_text': 'fixes its great central eye on you and fires a disintegration ray'},
            {'name': 'Antimagic Eye', 'type': 'debuff', 'effect_type': 'silence', 'duration': 2, 'magnitude': 0,
             'cast_text': 'sweeps its central eye over you, snuffing the magic from your fingertips'},
            {'name': 'Petrification Ray', 'type': 'debuff', 'effect_type': 'paralysis', 'duration': 1, 'magnitude': 0,
             'cast_text': 'fires a flesh-to-stone ray and your limbs seize up'},
            {'name': 'Slowing Ray', 'type': 'debuff', 'effect_type': 'slow', 'duration': 3, 'magnitude': 0,
             'cast_text': 'fires a slowing ray that turns the air around you to syrup'},
            {'name': 'Enervation Ray', 'type': 'debuff', 'effect_type': 'weakness', 'duration': 3, 'magnitude': 10,
             'cast_text': 'fires an enervation ray that drains the strength from your arm'},
        ]
    },

    {
        'name': "Young Dragon",
        'health': 120,
        'attack': 32,
        'defense': 15,
        'level': 7,
        'flavor_text': "A young dragon, still dangerous despite its age. It's cute in a mess-you-up sorta way.",
        'victory_text': "The young dragon falls, its reign of terror ended.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "Pathetic {title}! I will add your treasure to my hoard!",
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.50,
            'duration': 5,
            'magnitude': 10,
            'description': 'engulfs you in dragon fire'
        }
    },

    {
        'name': "Stone Golem",
        'health': 150,
        'attack': 28,
        'defense': 20,
        'level': 7,
        'flavor_text': "A golem carved from solid stone.",
        'victory_text': "The stone golem crumbles into boulders.",
        'elemental_weakness': ['Earth'],
        'elemental_strength': ['Physical'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'slow',
            'chance': 0.40,
            'duration': 3,
            'magnitude': 0,
            'description': 'slams the ground, the shockwave dragging at your limbs'
        }
    },

    {
        'name': "Mind Flayer",
        'health': 85,
        'attack': 40,
        'defense': 8,
        'level': 7,
        'flavor_text': "A nightmarish creature with writhing tentacles for a face.",
        'victory_text': "The mind flayer's psionic presence fades.",
        'elemental_weakness': ['Psionic'],
        'elemental_strength': ['Darkness'],
        'can_talk': True,
        'greeting_template': "Your mind is delicious, {name}. I will feast upon it. It's pronounced kuh thoo loo.",
        'special_attack': {
            'effect_type': 'confusion',
            'chance': 0.60,
            'duration': 4,
            'magnitude': 0,
            'description': 'assaults your mind with psionic energy'
        },
        'spell_chance': 0.35,
        'spells': [
            {'name': 'Mind Blast', 'type': 'damage', 'element': 'Psionic', 'power': 26,
             'cast_text': 'unleashes a cone of psionic force that detonates inside your skull'},
            {'name': 'Dominate', 'type': 'debuff', 'effect_type': 'paralysis', 'duration': 1, 'magnitude': 0,
             'cast_text': 'seizes your will, and for a moment your body is not your own'},
        ]
    },

    # ========================================================================
    # LEVEL 8 - Late Game Terrors
    # ========================================================================

    {
        'name': "Giant Frost Worm",
        'health': 170,
        'attack': 38,
        'defense': 15,
        'level': 8,
        'flavor_text': "A massive worm of ice and fury.",
        'victory_text': "The frost worm's body cracks and melts.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Ice'],
        'attack_element': 'Ice',
        'can_talk': False,
        'special_attack': {
            'effect_type': 'freeze',
            'chance': 0.50,
            'duration': 4,
            'magnitude': 10,
            'description': 'freezes you with its breath'
        }
    },

    {
        'name': "Fire Elemental",
        'health': 100,
        'attack': 45,
        'defense': 10,
        'level': 8,
        'flavor_text': "Living flame dances with malevolent intelligence.",
        'victory_text': "The flames sputter and die.",
        'elemental_weakness': ['Water'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': False,
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.60,
            'duration': 4,
            'magnitude': 12,
            'description': 'engulfs you in flames'
        }
    },

    {
        'name': "Griffin",
        'health': 110,
        'attack': 30,
        'defense': 12,
        'level': 8,
        'flavor_text': "A majestic creature with the body of a lion and wings of an eagle.",
        'victory_text': "The griffin's final cry echoes through the chamber.",
        'elemental_weakness': ['Wind'],
        'elemental_strength': ['Physical'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'damage_over_time',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 7,
            'description': 'dives and rakes you open with its talons'
        }
    },

    {
        'name': "Naga Guardian",
        'health': 120,
        'attack': 33,
        'defense': 13,
        'level': 8,
        'flavor_text': "A serpentine guardian with arcane power.",
        'victory_text': "The naga's coils go still.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Water'],
        'can_talk': True,
        'greeting_template': "Turn back, {name}. This sanctuary is not for mortals.",
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.55,
            'duration': 5,
            'magnitude': 11,
            'description': 'strikes with venomous fangs'
        }
    },

    {
        'name': "Roc",
        'health': 190,
        'attack': 30,
        'defense': 18,
        'level': 8,
        'flavor_text': "A gigantic bird of prey, large enough to carry off elephants.",
        'victory_text': "The roc plummets to the floor.",
        'elemental_weakness': ['Wind'],
        'elemental_strength': ['Physical'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.30,
            'duration': 1,
            'magnitude': 0,
            'description': 'snatches you up in its talons and slams you back down'
        }
    },

    # ========================================================================
    # LEVEL 9 - Epic Encounters
    # ========================================================================

    {
        'name': "Sphinx",
        'health': 150,
        'attack': 40,
        'defense': 20,
        'level': 9,
        'flavor_text': "A creature of riddles and ancient wisdom.",
        'victory_text': "The sphinx's enigmatic smile fades forever.",
        'elemental_weakness': ['Psionic'],
        'elemental_strength': ['Light'],
        'can_talk': True,
        'greeting_template': "Answer my riddle, {name}, or face my wrath!",
        'special_attack': {
            'effect_type': 'confusion',
            'chance': 0.50,
            'duration': 5,
            'magnitude': 0,
            'description': 'confounds you with impossible riddles'
        },
        'spell_chance': 0.30,
        'spells': [
            {'name': 'Word of Power', 'type': 'damage', 'element': 'Arcane', 'power': 26,
             'cast_text': 'speaks a Word of Power that detonates against your mind'},
        ]
    },

    {
        'name': "Purple Worm",
        'health': 200,
        'attack': 45,
        'defense': 20,
        'level': 9,
        'flavor_text': "Like the Prince song. A massive purple worm bursts from the ground.",
        'victory_text': "The worm's body convulses and lies still.",
        'elemental_weakness': ['Earth'],
        'elemental_strength': ['Physical'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.50,
            'duration': 6,
            'magnitude': 14,
            'description': 'injects deadly venom with its bite'
        }
    },

    {
        'name': "Efreeti",
        'health': 140,
        'attack': 48,
        'defense': 15,
        'level': 9,
        'flavor_text': "A fire genie wreathed in flames.",
        'victory_text': "The efreeti dissolves into smoke and ash.",
        'elemental_weakness': ['Water'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "You dare summon me, {name}? Burn!",
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.65,
            'duration': 5,
            'magnitude': 15,
            'description': 'surrounds you with infernal flames'
        },
        'spell_chance': 0.33,
        'spells': [
            {'name': 'Fireball', 'type': 'damage', 'element': 'Fire', 'power': 30,
             'cast_text': 'conjures a roaring ball of flame and hurls it at you'},
        ]
    },

    {
        'name': "Cyclops",
        'health': 220,
        'attack': 35,
        'defense': 25,
        'level': 9,
        'flavor_text': "A one-eyed giant of tremendous power.",
        'victory_text': "The cyclops falls like a toppled mountain.",
        'elemental_weakness': ['Physical'],
        'elemental_strength': ['Earth'],
        'can_talk': True,
        'greeting_template': "Tiny {title}! Cyclops crush you!",
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.30,
            'duration': 1,
            'magnitude': 0,
            'description': 'brings its massive club down and stuns you senseless'
        }
    },

    {
        'name': "Dragon Turtle",
        'health': 180,
        'attack': 50,
        'defense': 22,
        'level': 9,
        'flavor_text': "A colossal turtle with a dragon's head and very fishy breath.",
        'victory_text': "The dragon turtle retreats into its shell, dead.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Water'],
        'can_talk': True,
        'greeting_template': "The depths claim all who disturb my slumber.",
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.45,
            'duration': 4,
            'magnitude': 12,
            'description': 'unleashes scalding steam'
        }
    },

    # ========================================================================
    # LEVEL 10 - Legendary Threats
    # ========================================================================

    {
        'name': "Demilich",
        'health': 180,
        'attack': 55,
        'defense': 30,
        'level': 10,
        'flavor_text': "A floating skull radiating terrible power.",
        'victory_text': "The demilich's skull shatters, releasing trapped souls.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Shadow',
        'can_talk': True,
        'greeting_template': "Your soul will join my collection, {name}. Because everyone has worth. I value you just as you are.",
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.70,
            'duration': 1,
            'magnitude': 20,
            'description': 'attempts to trap your soul'
        },
        'spell_chance': 0.35,
        'spells': [
            {'name': 'Soul Bolt', 'type': 'damage', 'element': 'Shadow', 'power': 34,
             'cast_text': 'looses a screaming bolt of trapped souls'},
            {'name': 'Devour Essence', 'type': 'heal', 'power': 30,
             'cast_text': 'feeds on the souls in its sockets to restore itself'},
        ]
    },

    {
        'name': "Ancient Dragon",
        'health': 200,
        'attack': 50,
        'defense': 25,
        'level': 10,
        'flavor_text': "An ancient wyrm of incomprehensible power.",
        'victory_text': "The ancient dragon's reign ends at last.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "Insignificant mortal! I have ended kingdoms!",
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.70,
            'duration': 6,
            'magnitude': 18,
            'description': 'bathes you in ancient dragon fire'
        }
    },

    {
        'name': "Balrog",
        'health': 160,
        'attack': 48,
        'defense': 22,
        'level': 10,
        'flavor_text': "A demon of shadow and flame from the depths.",
        'victory_text': "The balrog falls into darkness, its fire extinguished.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "You cannot pass, {name}!",
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.65,
            'duration': 5,
            'magnitude': 16,
            'description': 'lashes you with its flaming whip'
        }
    },

    {
        'name': "Elder Brain",
        'health': 140,
        'attack': 42,
        'defense': 18,
        'level': 10,
        'flavor_text': "A massive brain floats in psychic fluid.",
        'victory_text': "The elder brain's consciousness fades forever.",
        'elemental_weakness': ['Psionic'],
        'elemental_strength': ['Darkness'],
        'can_talk': True,
        'greeting_template': "I know your every thought, {name}. You cannot win. And you should tell Debbie in accounting how you really feel about her.",
        'special_attack': {
            'effect_type': 'confusion',
            'chance': 0.75,
            'duration': 5,
            'magnitude': 0,
            'description': 'overwhelms your mind with psychic assault'
        },
        'spell_chance': 0.40,
        'spells': [
            {'name': 'Psychic Crush', 'type': 'damage', 'element': 'Psionic', 'power': 30,
             'cast_text': 'clenches an invisible fist around your mind and squeezes'},
            {'name': 'Dominate', 'type': 'debuff', 'effect_type': 'paralysis', 'duration': 1, 'magnitude': 0,
             'cast_text': 'overrides your will and freezes you mid-motion'},
        ]
    },

    {
        'name': "Tarrasque",
        'health': 250,
        'attack': 60,
        'defense': 35,
        'level': 10,
        'flavor_text': "The ultimate destroyer, a force of nature made flesh. It's also French.",
        'victory_text': "The tarrasque falls... for now. It will return.",
        'elemental_weakness': ['Demonic'],
        'elemental_strength': ['Physical'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.60,
            'duration': 5,
            'magnitude': 20,
            'description': 'savages you with overwhelming fury'
        }
    },

    # ========================================================================
    # ADDITIONAL D&D-INSPIRED MONSTERS - LEVEL 0-1 (Weak/Fodder)
    # ========================================================================

    {
        'name': "Kobold",
        'health': 8,
        'attack': 3,
        'defense': 1,
        'level': 0,
        'flavor_text': "A small reptilian humanoid clutching a rusty dagger.",
        'victory_text': "The kobold squeaks its last and collapses.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': [],
        'can_talk': True,
        'greeting_template': "You no take candle! ...Wait, wrong kobold."
    },

    {
        'name': "Stirge",
        'health': 6,
        'attack': 4,
        'defense': 0,
        'level': 0,
        'flavor_text': "A bat-like creature with a long proboscis, hungry for blood.",
        'victory_text': "The stirge falls, its proboscis twitching.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': [],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.30,
            'duration': 1,
            'magnitude': 3,
            'description': 'latches on and drains your blood'
        }
    },

    {
        'name': "Crawling Claw",
        'health': 5,
        'attack': 3,
        'defense': 0,
        'level': 0,
        'flavor_text': "A severed hand scuttles across the floor with malicious intent.",
        'victory_text': "The crawling claw twitches and goes still.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Poison'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'sticky_hands',
            'chance': 0.20,
            'duration': 1,
            'magnitude': 0,
            'description': 'latches onto your sword hand in a vice grip'
        }
    },

    {
        'name': "Goblin",
        'health': 12,
        'attack': 4,
        'defense': 1,
        'level': 1,
        'flavor_text': "A small, green-skinned creature with a wicked grin.",
        'victory_text': "The goblin falls with a pitiful shriek.",
        'elemental_weakness': [],
        'elemental_strength': [],
        'can_talk': True,
        'greeting_template': "Shinies! Give us your shinies, {title}!"
    },

    {
        'name': "Rust Monster",
        'health': 18,
        'attack': 3,
        'defense': 2,
        'level': 1,
        'flavor_text': "An insectoid creature with feathery antennae that twitch toward your gear.",
        'victory_text': "The rust monster crumbles into orange dust.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Physical'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.35,
            'duration': 3,
            'magnitude': 5,
            'description': 'corrodes your equipment with its touch'
        }
    },

    # ========================================================================
    # LEVEL 2-3 (Low-Mid Tier)
    # ========================================================================

    {
        'name': "Bugbear",
        'health': 35,
        'attack': 12,
        'defense': 5,
        'level': 2,
        'flavor_text': "A hulking goblinoid with matted fur and cruel eyes.",
        'victory_text': "The bugbear crashes to the ground with a thud.",
        'elemental_weakness': [],
        'elemental_strength': [],
        'can_talk': True,
        'greeting_template': "Bugbear smash puny {title}!"
    },

    {
        'name': "Gnoll",
        'health': 32,
        'attack': 11,
        'defense': 4,
        'level': 2,
        'flavor_text': "A hyena-headed humanoid cackling with bloodlust.",
        'victory_text': "The gnoll's laughter dies in its throat.",
        'elemental_weakness': [],
        'elemental_strength': [],
        'can_talk': True,
        'greeting_template': "Yeenoghu hungers! Your flesh will feed him!"
    },

    {
        'name': "Harpy",
        'health': 28,
        'attack': 9,
        'defense': 3,
        'level': 2,
        'flavor_text': "A creature with a woman's face and a vulture's body.",
        'victory_text': "The harpy's song ends in a death rattle.",
        'elemental_weakness': ['Lightning'],
        'elemental_strength': ['Wind'],
        'can_talk': True,
        'greeting_template': "Come closer, sweet {name}... let me sing for you...",
        'special_attack': {
            'effect_type': 'confusion',
            'chance': 0.25,
            'duration': 2,
            'magnitude': 0,
            'description': 'enchants you with her alluring song'
        }
    },

    {
        'name': "Cockatrice",
        'health': 25,
        'attack': 8,
        'defense': 4,
        'level': 2,
        'flavor_text': "A rooster-dragon hybrid with a petrifying gaze.",
        'victory_text': "The cockatrice turns to stone itself. Ironic.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'slow',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 0,
            'description': 'begins turning your flesh to stone'
        }
    },

    {
        'name': "Gelatinous Cube",
        'health': 45,
        'attack': 7,
        'defense': 2,
        'level': 3,
        'flavor_text': "A perfectly cube-shaped mass of transparent ooze.",
        'victory_text': "The cube splashes apart into harmless puddles.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Physical', 'Lightning'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.40,
            'duration': 4,
            'magnitude': 4,
            'description': 'begins dissolving you in acid'
        }
    },

    {
        'name': "Gray Ooze",
        'health': 35,
        'attack': 6,
        'defense': 1,
        'level': 2,
        'flavor_text': "A puddle of metalite gray slime that flows toward you hungrily.",
        'victory_text': "The ooze stops moving and slowly evaporates.",
        'elemental_weakness': ['Fire', 'Ice'],
        'elemental_strength': ['Physical', 'Lightning'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 4,
            'description': 'secretes metal-dissolving acid'
        }
    },

    {
        'name': "Ochre Jelly",
        'health': 55,
        'attack': 8,
        'defense': 0,
        'level': 4,
        'flavor_text': "A massive blob of orange-brown ooze that smells of decay.",
        'victory_text': "The jelly shudders and collapses into inert goo.",
        'elemental_weakness': ['Fire', 'Ice'],
        'elemental_strength': ['Physical', 'Lightning'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.35,
            'duration': 3,
            'magnitude': 3,
            'description': 'sprays digestive enzymes'
        }
    },

    {
        'name': "Black Pudding",
        'health': 85,
        'attack': 12,
        'defense': 0,
        'level': 6,
        'flavor_text': "An enormous mass of jet-black ooze that devours everything it touches.",
        'victory_text': "The pudding dissolves into a steaming, harmless residue.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Physical', 'Lightning', 'Ice'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.45,
            'duration': 4,
            'magnitude': 6,
            'description': 'engulfs you in caustic slime'
        }
    },

    {
        'name': "Owlbear",
        'health': 50,
        'attack': 14,
        'defense': 6,
        'level': 3,
        'flavor_text': "A terrifying hybrid of owl and bear, all talons and fury.",
        'victory_text': "The owlbear lets out a final screech-roar and falls.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': [],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'damage_over_time',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 4,
            'description': 'rends you with beak and talons, leaving you bleeding'
        }
    },

    {
        'name': "Displacer Beast",
        'health': 42,
        'attack': 13,
        'defense': 8,
        'level': 3,
        'flavor_text': "A six-legged panther with tentacles, its image shifts constantly.",
        'victory_text': "The beast's illusions fade as it dies.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Arcane'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'blindness',
            'chance': 0.35,
            'duration': 3,
            'magnitude': 0,
            'description': 'confuses your aim with its displacement'
        }
    },

    # ========================================================================
    # LEVEL 4-5 (Mid Tier)
    # ========================================================================

    {
        'name': "Minotaur",
        'health': 65,
        'attack': 18,
        'defense': 8,
        'level': 4,
        'flavor_text': "A massive bull-headed humanoid wielding a greataxe.",
        'victory_text': "The minotaur falls, its labyrinth days over.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Physical'],
        'can_talk': True,
        'greeting_template': "You dare enter MY maze, {title}?!",
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.25,
            'duration': 1,
            'magnitude': 0,
            'description': 'gores you with a goring charge that leaves you reeling'
        }
    },

    {
        'name': "Ettercap",
        'health': 48,
        'attack': 14,
        'defense': 7,
        'level': 4,
        'flavor_text': "A spider-like humanoid dripping with venom.",
        'victory_text': "The ettercap's web-spinning days are done.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Poison'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.45,
            'duration': 4,
            'magnitude': 6,
            'description': 'injects you with spider venom'
        }
    },

    {
        'name': "Basilisk",
        'health': 55,
        'attack': 12,
        'defense': 10,
        'level': 4,
        'flavor_text': "An eight-legged reptile whose gaze turns flesh to stone.",
        'victory_text': "The basilisk's deadly gaze dims forever.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Earth', 'Poison'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'slow',
            'chance': 0.50,
            'duration': 4,
            'magnitude': 0,
            'description': 'begins petrifying you with its gaze'
        }
    },

    {
        'name': "Carrion Crawler",
        'health': 52,
        'attack': 15,
        'defense': 6,
        'level': 4,
        'flavor_text': "A giant centipede-like creature with paralyzing tentacles.",
        'victory_text': "The carrion crawler writhes and goes still.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Poison'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'slow',
            'chance': 0.55,
            'duration': 3,
            'magnitude': 0,
            'description': 'paralyzes you with its tentacles'
        }
    },

    {
        'name': "Werewolf",
        'health': 60,
        'attack': 17,
        'defense': 7,
        'level': 5,
        'flavor_text': "A cursed human transformed into a savage wolf-beast.",
        'victory_text': "The werewolf reverts to human form in death.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Physical'],
        'can_talk': True,
        'greeting_template': "The moon... it calls to me! Run, {name}, RUN!",
        'special_attack': {
            'effect_type': 'curse',
            'chance': 0.30,
            'duration': 5,
            'magnitude': 5,
            'description': 'infects you with lycanthropy'
        }
    },

    {
        'name': "Gorgon",
        'health': 70,
        'attack': 16,
        'defense': 12,
        'level': 5,
        'flavor_text': "An iron-scaled bull that breathes petrifying gas.",
        'victory_text': "The gorgon's metallic hide crashes to the ground.",
        'elemental_weakness': ['Lightning'],
        'elemental_strength': ['Physical', 'Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'slow',
            'chance': 0.45,
            'duration': 4,
            'magnitude': 0,
            'description': 'breathes petrifying vapor at you'
        }
    },

    {
        'name': "Manticore",
        'health': 68,
        'attack': 19,
        'defense': 8,
        'level': 5,
        'flavor_text': "A lion with dragon wings and a tail of deadly spikes.",
        'victory_text': "The manticore's tail-spikes clatter to the floor.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': [],
        'can_talk': True,
        'greeting_template': "I've eaten better adventurers than you for breakfast!",
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.40,
            'duration': 3,
            'magnitude': 7,
            'description': 'launches venomous tail spikes at you'
        }
    },

    # ========================================================================
    # LEVEL 6-7 (Mid-High Tier)
    # ========================================================================

    {
        'name': "Bulette",
        'health': 85,
        'attack': 22,
        'defense': 14,
        'level': 6,
        'flavor_text': "A massive armored landshark bursts from the ground!",
        'victory_text': "The bulette sinks back into the earth, defeated.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Physical', 'Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'damage_over_time',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 6,
            'description': 'clamps down with serrated jaws, tearing a ragged wound'
        }
    },

    {
        'name': "Dragon Lich",
        'health': 82,
        'attack': 26,
        'defense': 11,
        'level': 6,
        'flavor_text': "An undead dragon held together by dark magic, bones rattling with every step.",
        'victory_text': "The necromantic bonds fail and the dragon lich collapses into a pile of ancient bones.",
        'elemental_weakness': ['Fire', 'Holy'],
        'elemental_strength': ['Ice', 'Dark'],
        'attack_element': 'Dark',
        'can_talk': True,
        'greeting_template': "My tomb shall become YOUR tomb!",
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.45,
            'duration': 4,
            'magnitude': 8,
            'description': 'claws with life-draining talons'
        },
        'spell_chance': 0.32,
        'spells': [
            {'name': 'Necrotic Bolt', 'type': 'damage', 'element': 'Dark', 'power': 18,
             'cast_text': 'gathers shadow between its horns and hurls a bolt of necrotic energy'},
            {'name': 'Bone Mending', 'type': 'heal', 'power': 18,
             'cast_text': 'drags loose bone and shadow back into its frame, mending itself'},
        ]
    },

    {
        'name': "Otyugh",
        'health': 78,
        'attack': 18,
        'defense': 10,
        'level': 6,
        'flavor_text': "A disgusting trash-eater with tentacles and a gaping maw.",
        'victory_text': "The otyugh collapses into the filth it loved.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Poison'],
        'can_talk': True,
        'greeting_template': "MORE GARBAGE FOR THE PILE! YOU SMELL DELICIOUS!",
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.55,
            'duration': 5,
            'magnitude': 8,
            'description': 'infects you with filth fever'
        }
    },

    {
        'name': "Wyvern",
        'health': 90,
        'attack': 25,
        'defense': 12,
        'level': 7,
        'flavor_text': "A dragon's lesser cousin with a venomous tail stinger.",
        'victory_text': "The wyvern crashes from the sky.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Poison'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.50,
            'duration': 5,
            'magnitude': 10,
            'description': 'stings you with its tail'
        }
    },

    {
        'name': "Hill Giant",
        'health': 95,
        'attack': 23,
        'defense': 10,
        'level': 7,
        'flavor_text': "A brutish giant hurling boulders with abandon.",
        'victory_text': "The hill giant falls with an earth-shaking thud.",
        'elemental_weakness': [],
        'elemental_strength': ['Physical'],
        'can_talk': True,
        'greeting_template': "ME SMASH LITTLE THING!",
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 8,
            'description': 'hurls a boulder that knocks the wind out of you'
        }
    },

    {
        'name': "Naga",
        'health': 80,
        'attack': 20,
        'defense': 13,
        'level': 7,
        'flavor_text': "A serpent with a human face, ancient and cunning.",
        'victory_text': "The naga's coils unwind in death.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Poison', 'Arcane'],
        'can_talk': True,
        'greeting_template': "I have ssslithered through centuriess, {name}. You are nothing.",
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.50,
            'duration': 4,
            'magnitude': 9,
            'description': 'spits venom at your eyes'
        }
    },

    # ========================================================================
    # LEVEL 8-9 (High Tier)
    # ========================================================================

    {
        'name': "Mind Flayer",
        'health': 100,
        'attack': 28,
        'defense': 15,
        'level': 8,
        'flavor_text': "An octopus-headed aberration that feeds on brains.",
        'victory_text': "The mind flayer's tentacles go limp as it dies.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Psionic', 'Darkness'],
        'can_talk': True,
        'greeting_template': "Your brain... will be exquisite, {name}.",
        'special_attack': {
            'effect_type': 'confusion',
            'chance': 0.60,
            'duration': 4,
            'magnitude': 0,
            'description': 'blasts your mind with psionic energy'
        },
        'spell_chance': 0.35,
        'spells': [
            {'name': 'Mind Blast', 'type': 'damage', 'element': 'Psionic', 'power': 22,
             'cast_text': 'unleashes a cone of psionic force that detonates inside your skull'},
            {'name': 'Dominate', 'type': 'debuff', 'effect_type': 'paralysis', 'duration': 1, 'magnitude': 0,
             'cast_text': 'seizes your will, and for a moment your body is not your own'},
        ]
    },

    {
        'name': "Beholder",
        'health': 110,
        'attack': 32,
        'defense': 18,
        'level': 8,
        'flavor_text': "A floating orb of flesh with a giant eye and ten eyestalks.",
        'victory_text': "The beholder's eyes dim one by one.",
        'elemental_weakness': [],
        'elemental_strength': ['Arcane'],
        'can_talk': True,
        'greeting_template': "I am PERFECTION. You are a FLAW to be ERASED.",
        'special_attack': {
            'effect_type': 'curse',
            'chance': 0.55,
            'duration': 5,
            'magnitude': 10,
            'description': 'hits you with multiple eye rays'
        },
        'spell_chance': 0.45,
        'spells': [
            {'name': 'Disintegration Ray', 'type': 'damage', 'element': 'Arcane', 'power': 30,
             'cast_text': 'fixes its great central eye on you and fires a disintegration ray'},
            {'name': 'Antimagic Eye', 'type': 'debuff', 'effect_type': 'silence', 'duration': 2, 'magnitude': 0,
             'cast_text': 'sweeps its central eye over you, snuffing the magic from your fingertips'},
            {'name': 'Petrification Ray', 'type': 'debuff', 'effect_type': 'paralysis', 'duration': 1, 'magnitude': 0,
             'cast_text': 'fires a flesh-to-stone ray and your limbs seize up'},
            {'name': 'Slowing Ray', 'type': 'debuff', 'effect_type': 'slow', 'duration': 3, 'magnitude': 0,
             'cast_text': 'fires a slowing ray that turns the air around you to syrup'},
            {'name': 'Enervation Ray', 'type': 'debuff', 'effect_type': 'weakness', 'duration': 3, 'magnitude': 12,
             'cast_text': 'fires an enervation ray that drains the strength from your arm'},
        ]
    },

    {
        'name': "Frost Giant",
        'health': 130,
        'attack': 30,
        'defense': 16,
        'level': 8,
        'flavor_text': "A towering giant of ice and cold fury.",
        'victory_text': "The frost giant shatters like an iceberg.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Ice'],
        'attack_element': 'Ice',
        'can_talk': True,
        'greeting_template': "The cold will claim you, tiny warm-blood!",
        'special_attack': {
            'effect_type': 'freeze',
            'chance': 0.30,
            'duration': 1,
            'magnitude': 0,
            'description': 'hammers you with a fist of solid ice'
        }
    },

    {
        'name': "Rakshasa",
        'health': 105,
        'attack': 26,
        'defense': 20,
        'level': 9,
        'flavor_text': "A tiger-headed fiend in noble garments, reeking of deception.",
        'victory_text': "The rakshasa dissolves, returning to the Nine Hells.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Arcane', 'Fire'],
        'can_talk': True,
        'greeting_template': "How... delightful to have a guest for dinner. YOU are the dinner.",
        'special_attack': {
            'effect_type': 'curse',
            'chance': 0.45,
            'duration': 4,
            'magnitude': 8,
            'description': 'hexes you with fiendish magic'
        },
        'spell_chance': 0.32,
        'spells': [
            {'name': 'Mind Twist', 'type': 'damage', 'element': 'Arcane', 'power': 24,
             'cast_text': 'twists reality and lashes your mind with searing arcane force'},
            {'name': 'Phantom Veil', 'type': 'debuff', 'effect_type': 'blindness', 'duration': 3, 'magnitude': 0,
             'cast_text': 'splits into a dozen illusory doubles, baffling your aim'},
            {'name': 'Spell Turning', 'type': 'self_buff', 'effect_type': 'spell_ward', 'duration': 4, 'magnitude': 1,
             'cast_text': 'traces a sigil of spell-turning -- your next spell will rebound off it'},
        ]
    },

    {
        'name': "Fire Giant",
        'health': 145,
        'attack': 35,
        'defense': 18,
        'level': 9,
        'flavor_text': "A massive smith-warrior wreathed in flame.",
        'victory_text': "The fire giant's flames sputter and die.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "Your bones will fuel my forge!",
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.50,
            'duration': 4,
            'magnitude': 12,
            'description': 'hurls molten iron at you'
        }
    },

    {
        'name': "Succubus",
        'health': 95,
        'attack': 24,
        'defense': 14,
        'level': 9,
        'flavor_text': "A seductive demon that feeds on life essence.",
        'victory_text': "The succubus fades away with a disappointed sigh.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Fire', 'Darkness'],
        'can_talk': True,
        'greeting_template': "Oh {name}... why fight when we could... negotiate?",
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.55,
            'duration': 1,
            'magnitude': 15,
            'description': 'drains your life force with a kiss'
        },
        'spell_chance': 0.30,
        'spells': [
            {'name': 'Charm', 'type': 'debuff', 'effect_type': 'confusion', 'duration': 3, 'magnitude': 0,
             'cast_text': 'meets your eyes and whispers a charm that scrambles your resolve'},
            {'name': 'Soul Siphon', 'type': 'damage', 'element': 'Shadow', 'power': 18,
             'cast_text': 'reaches out a clawed hand and tears at your life essence from across the room'},
        ]
    },

    # ========================================================================
    # LEVEL 10 (Legendary Tier)
    # ========================================================================

    {
        'name': "Storm Giant",
        'health': 175,
        'attack': 45,
        'defense': 22,
        'level': 10,
        'flavor_text': "A colossus wielding lightning itself as a weapon.",
        'victory_text': "Thunder rolls across the sky as the storm giant falls.",
        'elemental_weakness': ['Earth'],
        'elemental_strength': ['Lightning', 'Wind'],
        'attack_element': 'Lightning',
        'can_talk': True,
        'greeting_template': "The storms bow to my will, mortal. As shall you.",
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.60,
            'duration': 3,
            'magnitude': 18,
            'description': 'calls lightning down upon you'
        }
    },

    {
        'name': "Balor",
        'health': 200,
        'attack': 55,
        'defense': 28,
        'level': 10,
        'flavor_text': "A towering demon of flame and shadow, wielding a flaming whip.",
        'victory_text': "The balor explodes in a final burst of hellfire!",
        'elemental_weakness': ['Holy', 'Ice'],
        'elemental_strength': ['Fire', 'Darkness'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "You face a general of the Abyss! DESPAIR!",
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.65,
            'duration': 5,
            'magnitude': 20,
            'description': 'lashes you with its flaming whip'
        }
    },

    {
        'name': "Pit Fiend",
        'health': 190,
        'attack': 48,
        'defense': 30,
        'level': 10,
        'flavor_text': "An archdevil of the Nine Hells, cunning and terrible.",
        'victory_text': "The pit fiend's contract is broken. It returns to Hell.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Fire', 'Poison'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "I could offer you power, {name}. All it costs... is everything.",
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.55,
            'duration': 6,
            'magnitude': 15,
            'description': 'poisons you with infernal venom'
        }
    },

    {
        'name': "Death Knight",
        'health': 165,
        'attack': 52,
        'defense': 26,
        'level': 10,
        'flavor_text': "A fallen paladin, cursed to undeath for breaking their oath.",
        'victory_text': "The death knight's armor crumbles, its curse finally lifted.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness', 'Fire'],
        'attack_element': 'Darkness',
        'can_talk': True,
        'greeting_template': "I was once like you, {title}. Righteous. Foolish.",
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.50,
            'duration': 4,
            'magnitude': 16,
            'description': 'unleashes hellfire upon you'
        }
    },

    {
        'name': "Kraken",
        'health': 220,
        'attack': 50,
        'defense': 24,
        'level': 10,
        'flavor_text': "A titanic squid-beast from the deepest ocean trenches.",
        'victory_text': "The kraken sinks back into the abyss, defeated.",
        'elemental_weakness': ['Lightning'],
        'elemental_strength': ['Water', 'Ice'],
        'attack_element': 'Water',
        'can_talk': True,
        'greeting_template': "The depths have sent me to claim you, surface-dweller.",
        'special_attack': {
            'effect_type': 'slow',
            'chance': 0.60,
            'duration': 4,
            'magnitude': 0,
            'description': 'constricts you in its massive tentacles'
        }
    },

    {
        'name': "Night Hag",
        'health': 112,
        'attack': 30,
        'defense': 18,
        'level': 10,
        'flavor_text': "A hideous crone from the Gray Wastes, trading in souls.",
        'victory_text': "The night hag shrieks as her soul-bag scatters.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness', 'Arcane'],
        'can_talk': True,
        'greeting_template': "Your soul has a lovely color, {name}. I'll take it.",
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.50,
            'duration': 1,
            'magnitude': 18,
            'description': 'haunts your dreams and drains your vitality'
        },
        'spell_chance': 0.33,
        'spells': [
            {'name': 'Nightmare', 'type': 'damage', 'element': 'Shadow', 'power': 24,
             'cast_text': 'pours a waking nightmare into your skull'},
            {'name': 'Sup on Souls', 'type': 'heal', 'power': 20,
             'cast_text': 'sups from her soul-bag and the years melt off her'},
        ]
    },

    # ========================================================================
    # DEEP DESCENT BESTIARY - TIERS 11-15 (Floors ~24-49)
    # ========================================================================
    # Native inhabitants of the lower vaults leading to Zot. These are not
    # re-skinned low-level mobs -- they carry their own baked-in stats so the
    # deep floors stay lethal without any name-prefix evolution. Stat budgets
    # are anchored to the difficulty curve the old evolution tiers produced
    # at the same depths, so the endgame ceiling is preserved.

    # ---- TIER 11 (floors 24-39): the outer dark ----
    {
        'name': "Gloomback Bear",
        'health': 560, 'attack': 74, 'defense': 42, 'level': 11,
        'flavor_text': "A cave bear gone wrong in the lightless deep, its hide rimed with frost.",
        'victory_text': "The gloomback bear slumps, its cold breath stilled.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Ice', 'Physical'],
        'attack_element': 'Physical',
        'can_talk': False,
        'special_attack': {'effect_type': 'weakness', 'chance': 0.40, 'duration': 3, 'magnitude': 12, 'description': 'rakes you with frostbitten claws'}
    },
    {
        'name': "Voidspawn Brute",
        'health': 480, 'attack': 90, 'defense': 32, 'level': 11,
        'flavor_text': "A slab of muscle birthed from the gaps between worlds. It should not be.",
        'victory_text': "The voidspawn collapses inward and is simply gone.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Darkness',
        'can_talk': False,
        'special_attack': {'effect_type': 'confusion', 'chance': 0.35, 'duration': 3, 'magnitude': 0, 'description': 'gibbers in a tongue that warps your mind'}
    },
    {
        'name': "Cinder Serpent",
        'health': 380, 'attack': 102, 'defense': 28, 'level': 11,
        'flavor_text': "A great serpent that nests in magma vents, scales glowing like banked coals.",
        'victory_text': "The cinder serpent's fires gutter out into ash.",
        'elemental_weakness': ['Ice', 'Water'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': False,
        'special_attack': {'effect_type': 'burn', 'chance': 0.50, 'duration': 4, 'magnitude': 12, 'description': 'spits a gout of magma'}
    },
    {
        'name': "Sporelord Myconid",
        'health': 440, 'attack': 78, 'defense': 30, 'level': 11,
        'flavor_text': "An ancient mushroom-sovereign, its cap a cathedral of toxic spores.",
        'victory_text': "The sporelord bursts one final time and falls silent.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Poison', 'Earth'],
        'attack_element': 'Earth',
        'can_talk': True,
        'greeting_template': "Breathe deep, {name}. Join the colony.",
        'special_attack': {'effect_type': 'poison', 'chance': 0.60, 'duration': 5, 'magnitude': 8, 'description': 'bursts in a cloud of choking spores'}
    },
    {
        'name': "Bonepicker Reaver",
        'health': 360, 'attack': 108, 'defense': 26, 'level': 11,
        'flavor_text': "A skeletal marauder that hunts the deep for marrow and warmth.",
        'victory_text': "The reaver clatters apart into a heap of yellowed bone.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Physical',
        'can_talk': False,
        'special_attack': {'effect_type': 'life_drain', 'chance': 0.40, 'duration': 1, 'magnitude': 14, 'description': 'drinks the warmth from your veins'}
    },
    {
        'name': "Ridgeback Wyvern",
        'health': 400, 'attack': 94, 'defense': 34, 'level': 11,
        'flavor_text': "A lean, vicious cousin of the dragons, all stinger and spite.",
        'victory_text': "The wyvern's venomous tail droops and goes limp.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Poison'],
        'attack_element': 'Physical',
        'can_talk': False,
        'special_attack': {'effect_type': 'poison', 'chance': 0.50, 'duration': 4, 'magnitude': 10, 'description': 'drives its venom-slick stinger home'}
    },

    # ---- TIER 12 (floors 28-43): elementals, liches, and drakes ----
    {
        'name': "Iron Vanguard",
        'health': 700, 'attack': 96, 'defense': 50, 'level': 12,
        'flavor_text': "A war-construct of black iron, built to hold a line that no longer exists.",
        'victory_text': "The iron vanguard topples with a deafening crash.",
        'elemental_weakness': ['Lightning'],
        'elemental_strength': ['Physical', 'Earth'],
        'attack_element': 'Physical',
        'can_talk': False,
        'special_attack': {'effect_type': 'slow', 'chance': 0.45, 'duration': 3, 'magnitude': 0, 'description': 'slams you with a tower-shield charge'}
    },
    {
        'name': "Rimebound Djinn",
        'health': 480, 'attack': 134, 'defense': 34, 'level': 12,
        'flavor_text': "A genie of the frozen wastes, bound here long ago and very, very bitter about it.",
        'victory_text': "The rimebound djinn shatters into a flurry of snow.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Ice', 'Wind'],
        'attack_element': 'Ice',
        'can_talk': True,
        'greeting_template': "A thousand years in the ice, and now YOU disturb me?",
        'special_attack': {'effect_type': 'freeze', 'chance': 0.40, 'duration': 2, 'magnitude': 0, 'description': 'exhales a blizzard that locks your limbs'},
        'spell_chance': 0.30,
        'spells': [
            {'name': 'Ice Lance', 'type': 'damage', 'element': 'Ice', 'power': 58,
             'cast_text': 'conjures a javelin of black ice and hurls it through the cold air'},
        ]
    },
    {
        'name': "Cinderborn Efreet",
        'health': 480, 'attack': 136, 'defense': 34, 'level': 12,
        'flavor_text': "A noble of the City of Brass, wreathed in furnace-heat and arrogance.",
        'victory_text': "The efreet gutters out, its fire reclaimed by the dark.",
        'elemental_weakness': ['Ice', 'Water'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "Mortal ash, that is all you will leave behind.",
        'special_attack': {'effect_type': 'burn', 'chance': 0.55, 'duration': 5, 'magnitude': 14, 'description': 'wreathes you in furnace flame'},
        'spell_chance': 0.30,
        'spells': [
            {'name': 'Fireball', 'type': 'damage', 'element': 'Fire', 'power': 60,
             'cast_text': 'gathers the furnace-heat of the City of Brass into a screaming fireball'},
        ]
    },
    {
        'name': "Hollow Lich",
        'health': 500, 'attack': 126, 'defense': 36, 'level': 12,
        'flavor_text': "An undead spellweaver, hollowed of all but ambition and malice.",
        'victory_text': "The hollow lich crumbles -- until its phylactery is found.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness', 'Ice'],
        'attack_element': 'Darkness',
        'can_talk': True,
        'greeting_template': "Death is a door, {name}. Allow me to open it.",
        'special_attack': {'effect_type': 'curse', 'chance': 0.40, 'duration': 4, 'magnitude': 10, 'description': 'speaks a word that rots your luck'},
        'spell_chance': 0.32,
        'spells': [
            {'name': 'Necrotic Bolt', 'type': 'damage', 'element': 'Darkness', 'power': 56,
             'cast_text': 'speaks a word of unmaking and a bolt of pure entropy leaps from its palm'},
            {'name': 'Drain Vitality', 'type': 'heal', 'power': 55,
             'cast_text': 'rips the warmth from the room to knit its hollow frame'},
            {'name': 'Force Shield', 'type': 'self_buff', 'effect_type': 'hit_absorb', 'duration': 4, 'magnitude': 2,
             'cast_text': 'sheathes itself in a lattice of deathless force'},
        ]
    },
    {
        'name': "Emberscale Drake",
        'health': 660, 'attack': 112, 'defense': 46, 'level': 12,
        'flavor_text': "A young dragon already drunk on its own fire, hoarding the bones of the deep.",
        'victory_text': "The emberscale drake's furnace heart goes cold.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "My hoard grows. Your bones will round it out nicely.",
        'special_attack': {'effect_type': 'burn', 'chance': 0.55, 'duration': 5, 'magnitude': 14, 'description': 'looses a torrent of dragonfire'}
    },
    {
        'name': "Gnashing Horror",
        'health': 470, 'attack': 130, 'defense': 32, 'level': 12,
        'flavor_text': "A floating cluster of teeth and psychic hunger. Do not look directly at it.",
        'victory_text': "The gnashing horror's thoughts unravel and scatter.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Psionic', 'Darkness'],
        'attack_element': 'Psionic',
        'can_talk': False,
        'special_attack': {'effect_type': 'confusion', 'chance': 0.50, 'duration': 4, 'magnitude': 0, 'description': 'lashes your thoughts with raw psionic dread'}
    },

    # ---- TIER 13 (floors 32-47): fiends, overminds, and colossi ----
    {
        'name': "Abyssal Fiend",
        'health': 760, 'attack': 158, 'defense': 50, 'level': 13,
        'flavor_text': "A horned devil straight off the burning plains of the Abyss.",
        'victory_text': "The abyssal fiend is dragged screaming back to its layer.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Fire', 'Demonic'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "Your contract is overdue, {name}. I'm here to collect.",
        'special_attack': {'effect_type': 'burn', 'chance': 0.55, 'duration': 5, 'magnitude': 18, 'description': 'engulfs you in hellfire'}
    },
    {
        'name': "Illithid Overmind",
        'health': 620, 'attack': 168, 'defense': 40, 'level': 13,
        'flavor_text': "A mind flayer elder, its tentacled maw twitching with anticipation.",
        'victory_text': "The overmind's psychic presence vanishes like a snuffed candle.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Psionic'],
        'attack_element': 'Psionic',
        'can_talk': True,
        'greeting_template': "Such a delectable cortex. Hold still.",
        'special_attack': {'effect_type': 'confusion', 'chance': 0.60, 'duration': 5, 'magnitude': 0, 'description': 'reaches into your skull for a snack'},
        'spell_chance': 0.35,
        'spells': [
            {'name': 'Mind Blast', 'type': 'damage', 'element': 'Psionic', 'power': 66,
             'cast_text': 'unfurls its full intellect and detonates a cone of psionic force in your mind'},
            {'name': 'Dominate', 'type': 'debuff', 'effect_type': 'paralysis', 'duration': 1, 'magnitude': 0,
             'cast_text': 'takes the reins of your nervous system and your body locks up'},
        ]
    },
    {
        'name': "Hundred-Eyed Watcher",
        'health': 660, 'attack': 152, 'defense': 44, 'level': 13,
        'flavor_text': "A bloated orb of flesh studded with eyes, each one a different kind of doom.",
        'victory_text': "The watcher's many eyes roll back and close, one by one.",
        'elemental_weakness': ['Earth'],
        'elemental_strength': ['Arcane', 'Psionic'],
        'attack_element': 'Psionic',
        'can_talk': True,
        'greeting_template': "I see every path your life could take. They all end here.",
        'special_attack': {'effect_type': 'paralysis', 'chance': 0.45, 'duration': 3, 'magnitude': 0, 'description': 'transfixes you with a ray from a dozen eyes'}
    },
    {
        'name': "Necrarch Lich",
        'health': 600, 'attack': 172, 'defense': 42, 'level': 13,
        'flavor_text': "A lich-king of a fallen dynasty, crown fused to a fleshless skull.",
        'victory_text': "The necrarch's reign ends as its bones finally still.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Darkness',
        'can_talk': True,
        'greeting_template': "I ruled empires while your ancestors were mud, {name}.",
        'special_attack': {'effect_type': 'life_drain', 'chance': 0.50, 'duration': 1, 'magnitude': 22, 'description': 'siphons your soul toward its phylactery'},
        'spell_chance': 0.33,
        'spells': [
            {'name': 'Necrotic Bolt', 'type': 'damage', 'element': 'Darkness', 'power': 68,
             'cast_text': 'levels a crowned skull at you and lets fly a bolt of grave-cold'},
            {'name': 'Drain Vitality', 'type': 'heal', 'power': 66,
             'cast_text': 'drinks the life from the very stones to mend itself'},
        ]
    },
    {
        'name': "Graven Colossus",
        'health': 880, 'attack': 124, 'defense': 58, 'level': 13,
        'flavor_text': "A mountain given legs and a grudge, carved in an age before names.",
        'victory_text': "The graven colossus cracks down its center and falls to rubble.",
        'elemental_weakness': ['Lightning'],
        'elemental_strength': ['Earth', 'Physical'],
        'attack_element': 'Earth',
        'can_talk': False,
        'special_attack': {'effect_type': 'weakness', 'chance': 0.45, 'duration': 3, 'magnitude': 16, 'description': 'brings a fist of living stone down on you'}
    },
    {
        'name': "Cryptborn Wraith",
        'health': 620, 'attack': 165, 'defense': 44, 'level': 13,
        'flavor_text': "A shroud of grave-cold malice that remembers being a person, and resents it.",
        'victory_text': "The wraith dissipates with a sigh of ancient grief.",
        'elemental_weakness': ['Holy', 'Light'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Darkness',
        'can_talk': False,
        'special_attack': {'effect_type': 'curse', 'chance': 0.45, 'duration': 4, 'magnitude': 11, 'description': 'wraps you in grave-cold despair'}
    },

    # ---- TIER 14 (floors 36-49): archfiends, wyrmlords, titans ----
    {
        'name': "Abyssal Archfiend",
        'health': 1080, 'attack': 188, 'defense': 64, 'level': 14,
        'flavor_text': "A demon-prince in miniature, commanding lesser fiends with a glance.",
        'victory_text': "The archfiend's infernal form buckles and is unmade.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness', 'Demonic'],
        'attack_element': 'Darkness',
        'can_talk': True,
        'greeting_template': "Kneel, {name}, and I may make your end merely eternal.",
        'special_attack': {'effect_type': 'curse', 'chance': 0.50, 'duration': 5, 'magnitude': 12, 'description': 'brands your soul with an infernal sigil'}
    },
    {
        'name': "Starspawn Aberration",
        'health': 920, 'attack': 210, 'defense': 52, 'level': 14,
        'flavor_text': "A fragment of something vast that fell from the night sky aeons ago.",
        'victory_text': "The starspawn folds away into an angle that no longer exists.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Psionic', 'Arcane'],
        'attack_element': 'Psionic',
        'can_talk': False,
        'special_attack': {'effect_type': 'confusion', 'chance': 0.60, 'duration': 5, 'magnitude': 0, 'description': 'unfolds in geometries that should not be'}
    },
    {
        'name': "Crimson Wyrmlord",
        'health': 1180, 'attack': 172, 'defense': 68, 'level': 14,
        'flavor_text': "An elder red dragon, scales like furnace doors, voice like an avalanche of coins.",
        'victory_text': "The wyrmlord's final roar collapses into smoldering silence.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Fire'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "I have eaten kings, {name}. You are barely an appetizer.",
        'special_attack': {'effect_type': 'burn', 'chance': 0.60, 'duration': 6, 'magnitude': 20, 'description': 'incinerates the air around you'}
    },
    {
        'name': "Sepulchral Lich",
        'health': 820, 'attack': 232, 'defense': 50, 'level': 14,
        'flavor_text': "An archmage who chose undeath to finish a spell that should never be finished.",
        'victory_text': "The sepulchral lich's grand working collapses with it.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness', 'Arcane'],
        'attack_element': 'Darkness',
        'can_talk': True,
        'greeting_template': "I am SO close, {name}. I will not be interrupted now.",
        'special_attack': {'effect_type': 'curse', 'chance': 0.50, 'duration': 5, 'magnitude': 12, 'description': 'intones a litany of unmaking'},
        'spell_chance': 0.33,
        'spells': [
            {'name': 'Word of Unmaking', 'type': 'damage', 'element': 'Darkness', 'power': 86,
             'cast_text': 'utters a fragment of its forbidden working and reality tears at you'},
            {'name': 'Phylactery Mending', 'type': 'heal', 'power': 90,
             'cast_text': 'draws on its hidden phylactery and its wounds close like rewound time'},
            {'name': 'Force Shield', 'type': 'self_buff', 'effect_type': 'hit_absorb', 'duration': 4, 'magnitude': 2,
             'cast_text': 'wraps itself in a shell of unmaking that turns aside the next blows'},
        ]
    },
    {
        'name': "Maw of the Deep",
        'health': 980, 'attack': 196, 'defense': 54, 'level': 14,
        'flavor_text': "A leviathan of the drowned vaults, all tentacles and a hunger older than light.",
        'victory_text': "The maw recedes into the black water, defeated for now.",
        'elemental_weakness': ['Lightning'],
        'elemental_strength': ['Water', 'Ice'],
        'attack_element': 'Ice',
        'can_talk': False,
        'special_attack': {'effect_type': 'slow', 'chance': 0.55, 'duration': 4, 'magnitude': 0, 'description': 'drags you under with a forest of tentacles'}
    },
    {
        'name': "Glacian Titan",
        'health': 1140, 'attack': 168, 'defense': 68, 'level': 14,
        'flavor_text': "A giant carved from a living glacier, each footfall a small avalanche.",
        'victory_text': "The glacian titan splinters into a field of melting ice.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Ice'],
        'attack_element': 'Ice',
        'can_talk': False,
        'special_attack': {'effect_type': 'freeze', 'chance': 0.45, 'duration': 2, 'magnitude': 0, 'description': 'hammers you with a glacier-forged maul'}
    },

    # ---- TIER 15 (floors 40-49): Zot's elite, the final horrors ----
    {
        'name': "Elder Starspawn",
        'health': 1340, 'attack': 290, 'defense': 62, 'level': 15,
        'flavor_text': "The progenitor of the lesser starspawn, vast and patient and wrong.",
        'victory_text': "The elder starspawn withdraws beyond the stars, screaming silence.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Psionic', 'Arcane'],
        'attack_element': 'Psionic',
        'can_talk': True,
        'greeting_template': "You are a brief idea, {name}. I am the dark between thoughts.",
        'special_attack': {'effect_type': 'confusion', 'chance': 0.65, 'duration': 6, 'magnitude': 0, 'description': 'floods your mind with the silence between stars'}
    },
    {
        'name': "Infernal Warlord",
        'health': 1240, 'attack': 305, 'defense': 66, 'level': 15,
        'flavor_text': "A general of the Nine Hells, armored in the suffering of legions.",
        'victory_text': "The warlord's infernal legion-banner burns to nothing.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Fire', 'Demonic'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "I have a throne of skulls, {name}, and one seat is open.",
        'special_attack': {'effect_type': 'burn', 'chance': 0.60, 'duration': 6, 'magnitude': 24, 'description': 'calls down a rain of brimstone'},
        'spell_chance': 0.30,
        'spells': [
            {'name': 'Hellfire Bolt', 'type': 'damage', 'element': 'Fire', 'power': 92,
             'cast_text': 'gestures with a gauntleted hand and a lance of hellfire roars out'},
        ]
    },
    {
        'name': "Voidmaw Devourer",
        'health': 1480, 'attack': 258, 'defense': 70, 'level': 15,
        'flavor_text': "A mouth in the shape of a world, eating its way toward the surface.",
        'victory_text': "The voidmaw's endless hunger finally consumes itself.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Arcane', 'Darkness'],
        'attack_element': 'Darkness',
        'can_talk': False,
        'special_attack': {'effect_type': 'life_drain', 'chance': 0.55, 'duration': 1, 'magnitude': 30, 'description': 'swallows a piece of you whole'}
    },
    {
        'name': "Cataclysm Fiend",
        'health': 1650, 'attack': 248, 'defense': 84, 'level': 15,
        'flavor_text': "A walking apocalypse of abyssal flame, the last thing many heroes ever see.",
        'victory_text': "The cataclysm fiend detonates one final time and is spent.",
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Fire', 'Demonic'],
        'attack_element': 'Fire',
        'can_talk': True,
        'greeting_template': "Everything ends, {name}. I just make it sooner.",
        'special_attack': {'effect_type': 'burn', 'chance': 0.60, 'duration': 6, 'magnitude': 26, 'description': 'detonates in a pillar of abyssal flame'}
    },
    {
        'name': "Nightmare Lich",
        'health': 1120, 'attack': 322, 'defense': 58, 'level': 15,
        'flavor_text': "A lich who mastered death so thoroughly it became death's nightmare.",
        'victory_text': "The nightmare lich unravels into a scream no one will remember.",
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness', 'Arcane'],
        'attack_element': 'Darkness',
        'can_talk': True,
        'greeting_template': "I have rewritten my own ending a thousand times, {name}. Yours is fixed.",
        'special_attack': {'effect_type': 'curse', 'chance': 0.55, 'duration': 6, 'magnitude': 14, 'description': 'rewrites your fate in a dead language'},
        'spell_chance': 0.35,
        'spells': [
            {'name': 'Death Bolt', 'type': 'damage', 'element': 'Darkness', 'power': 100,
             'cast_text': 'speaks your name in a dead language and a bolt of pure ending answers'},
            {'name': 'Unlife Mending', 'type': 'heal', 'power': 110,
             'cast_text': 'rewrites the last few moments so its wounds were never dealt'},
            {'name': 'Force Shield', 'type': 'self_buff', 'effect_type': 'hit_absorb', 'duration': 4, 'magnitude': 3,
             'cast_text': 'edits itself out of harm, a shell of unbeing turning your strikes aside'},
        ]
    },
    {
        'name': "Soulflayer Wraith",
        'health': 1100, 'attack': 318, 'defense': 60, 'level': 15,
        'flavor_text': "Less a ghost than a wound in the world, hungry for the spark that fills it.",
        'victory_text': "The soulflayer thins to nothing, its hunger finally answered.",
        'elemental_weakness': ['Holy', 'Light'],
        'elemental_strength': ['Darkness'],
        'attack_element': 'Darkness',
        'can_talk': False,
        'special_attack': {'effect_type': 'life_drain', 'chance': 0.55, 'duration': 1, 'magnitude': 28, 'description': 'flays the soul from your body'}
    },
]

# ============================================================================
# BUG LEVEL MONSTER TEMPLATES
# ============================================================================
# These monsters only appear on the special Shrinking Bug Level.
# They are NOT in MONSTER_TEMPLATES because they don't use normal spawn logic.
# Instead, they are spawned directly by the bug level generation code.
# ============================================================================

# ============================================================================
# BUG GARDEN INGREDIENTS
# Harvestable from bug gardens on the shrinking bug level.
# Bug-sized plants and fungi growing in the hive's overgrown chambers.
# ============================================================================

BUG_GARDEN_INGREDIENTS = [
    ('Aphid Honeydew', 'A sticky droplet of sweet honeydew, harvested from tiny aphids.', 8, 1, 0.20),
    ('Mycelium Thread', 'A strand of luminous fungal thread growing between cracks.', 10, 1, 0.15),
    ('Pollen Cluster', 'A dense ball of golden pollen, buzzing with residual energy.', 6, 1, 0.20),
    ('Spore Cap', 'A tiny mushroom cap releasing glittering spores.', 12, 2, 0.15),
    ('Nectar Bead', 'A crystallized bead of flower nectar, impossibly sweet.', 15, 2, 0.10),
    ('Chitin Moss', 'Moss that grows on discarded bug shells, tough and fibrous.', 7, 1, 0.15),
    ('Dew Silk', 'A thread of spider silk coated in morning dew, glistening.', 20, 2, 0.05),
]

# ============================================================================
# BUG-THEMED WEAPON AND ARMOR TEMPLATES
# Used by bug merchants on the shrinking bug level.
# Level 1-2 range to match floors 8-15 player power level.
# ============================================================================

BUG_WEAPON_TEMPLATES = [
    {'name': "Stinger Blade", 'description': "A sharpened wasp stinger, perfect for bug-sized combat.", 'attack_bonus': 9, 'value': 40, 'level': 2, 'elemental_strength': ["Poison"]},
    {'name': "Mandible Axe", 'description': "An ant mandible repurposed as a wicked axe.", 'attack_bonus': 12, 'value': 70, 'level': 2, 'elemental_strength': ["Physical"]},
    {'name': "Thorax Spear", 'description': "A beetle leg sharpened to a deadly point.", 'attack_bonus': 11, 'value': 55, 'level': 2, 'elemental_strength': ["None"]},
    {'name': "Firefly Wand", 'description': "A glowing firefly abdomen that crackles with bioluminescent energy.", 'attack_bonus': 14, 'value': 90, 'level': 3, 'elemental_strength': ["Fire"]},
    {'name': "Scorpion Tail Whip", 'description': "A venomous scorpion tail segment, still dripping.", 'attack_bonus': 16, 'value': 110, 'level': 3, 'elemental_strength': ["Poison"]},
]

BUG_ARMOR_TEMPLATES = [
    {'name': "Chitin Shell", 'description': "A piece of beetle carapace strapped on as armor.", 'defense_bonus': 6, 'value': 45, 'level': 2, 'elemental_strength': ["Earth"]},
    {'name': "Silk Weave", 'description': "Spider silk woven into surprisingly tough armor.", 'defense_bonus': 8, 'value': 65, 'level': 2, 'elemental_strength': ["None"]},
    {'name': "Moth Wing Cape", 'description': "Shimmering moth wing scales that deflect attacks.", 'defense_bonus': 7, 'value': 50, 'level': 2, 'elemental_strength': ["Air"]},
    {'name': "Pill Bug Plate", 'description': "Interlocking pill bug segments form heavy but sturdy armor.", 'defense_bonus': 10, 'value': 85, 'level': 3, 'elemental_strength': ["Earth"]},
    {'name': "Royal Jelly Mail", 'description': "Hardened royal jelly molded into glistening armor.", 'defense_bonus': 12, 'value': 120, 'level': 3, 'elemental_strength': ["None"]},
]

BUG_MONSTER_TEMPLATES = [
    {
        'name': "Titan Beetle",
        'health': 30,
        'attack': 10,
        'defense': 8,
        'level': 2,
        'flavor_text': "A massive beetle towers over your shrunken form. Its horn is bigger than you are.",
        'victory_text': "The beetle topples over with a thunderous crash. Well, thunderous to you.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Earth', 'Physical'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'paralysis',
            'chance': 0.20,
            'duration': 2,
            'magnitude': 0,
            'description': 'slams you with its massive horn'
        }
    },
    {
        'name': "Stinkbug Brute",
        'health': 25,
        'attack': 8,
        'defense': 3,
        'level': 1,
        'flavor_text': "A hulking stinkbug blocks your path. The smell alone could kill you at this size.",
        'victory_text': "The stinkbug releases one final noxious cloud as it expires. Gross.",
        'elemental_weakness': ['Wind'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'poison',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 4,
            'description': 'sprays you with nauseating stink chemicals'
        }
    },
    {
        'name': "Fly Swarm",
        'health': 18,
        'attack': 12,
        'defense': 1,
        'level': 1,
        'flavor_text': "A buzzing cloud of flies. At your current size, each one is like a dive-bombing fighter jet.",
        'victory_text': "The swarm disperses, leaving twitching wings scattered on the ground.",
        'elemental_weakness': ['Fire', 'Wind'],
        'elemental_strength': ['Physical'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'life_drain',
            'chance': 0.35,
            'duration': 1,
            'magnitude': 5,
            'description': 'swarms you with dozens of biting flies'
        }
    },
    {
        'name': "Pill Bug Golem",
        'health': 40,
        'attack': 6,
        'defense': 12,
        'level': 2,
        'flavor_text': "A pill bug the size of a boulder has rolled into a defensive ball. It uncurls menacingly.",
        'victory_text': "The pill bug curls into a ball one last time and doesn't uncurl.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Physical', 'Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'defense_penalty',
            'chance': 0.25,
            'duration': 3,
            'magnitude': 5,
            'description': 'rolls over you like a tiny steamroller'
        }
    },
    {
        'name': "Firefly Mage",
        'health': 20,
        'attack': 14,
        'defense': 2,
        'level': 2,
        'flavor_text': "A firefly pulses with arcane light. At this size, its glow is blinding and magical.",
        'victory_text': "The firefly's light flickers and fades to darkness.",
        'elemental_weakness': ['Darkness'],
        'elemental_strength': ['Light', 'Fire'],
        'attack_element': 'Fire',
        'can_talk': False,
        'special_attack': {
            'effect_type': 'burn',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 4,
            'description': 'sears you with concentrated bioluminescent fire'
        },
        'spell_chance': 0.30,
        'spells': [
            {'name': 'Lumen Lance', 'type': 'damage', 'element': 'Fire', 'power': 9,
             'cast_text': 'gathers its glow into a searing lance of light'},
        ]
    },
    {
        'name': "Ant Soldier",
        'health': 22,
        'attack': 9,
        'defense': 5,
        'level': 1,
        'flavor_text': "A soldier ant clacks its mandibles. To your shrunken self, it looks like a war machine.",
        'victory_text': "The ant falls, its mandibles still twitching with duty.",
        'elemental_weakness': ['Fire', 'Water'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.25,
            'duration': 3,
            'magnitude': 4,
            'description': 'sprays formic acid that burns your skin'
        }
    },
    {
        'name': "Dung Beetle Lord",
        'health': 35,
        'attack': 11,
        'defense': 7,
        'level': 2,
        'flavor_text': "A dung beetle rolls a ball twice your size. It regards you as an obstacle. Or maybe an ingredient.",
        'victory_text': "The dung beetle lord falls. Its precious dung ball rolls away into the darkness.",
        'elemental_weakness': ['Fire', 'Wind'],
        'elemental_strength': ['Earth', 'Darkness'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'confusion',
            'chance': 0.25,
            'duration': 3,
            'magnitude': 0,
            'description': 'flings a chunk of dung at your face'
        }
    },
    {
        'name': "Dragonfly Enchantress",
        'health': 22,
        'attack': 11,
        'defense': 3,
        'level': 2,
        'flavor_text': "A dragonfly with iridescent wings hovers before you. Its compound eyes shimmer with arcane light.",
        'victory_text': "The dragonfly spirals downward, its enchanting wings going still.",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Darkness', 'Light'],
        'attack_element': 'Arcane',
        'can_talk': False,
        'special_attack': {
            'effect_type': 'confusion',
            'chance': 0.35,
            'duration': 4,
            'magnitude': 0,
            'description': 'mesmerizes you with prismatic wing flashes'
        },
        'spell_chance': 0.32,
        'spells': [
            {'name': 'Prismatic Bolt', 'type': 'damage', 'element': 'Arcane', 'power': 8,
             'cast_text': 'focuses its compound eyes and looses a prismatic bolt'},
            {'name': 'Enervating Charm', 'type': 'debuff', 'effect_type': 'weakness', 'duration': 3, 'magnitude': 3,
             'cast_text': 'weaves a draining enchantment that saps the strength from your limbs'},
        ]
    },
    {
        'name': "Earthworm",
        'health': 28,
        'attack': 7,
        'defense': 4,
        'level': 1,
        'flavor_text': "A massive earthworm bursts from the soil. Its segmented body writhes with surprising speed.",
        'victory_text': "The earthworm retreats into the earth, leaving a tunnel behind.",
        'elemental_weakness': ['Fire', 'Light'],
        'elemental_strength': ['Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'weakness',
            'chance': 0.25,
            'duration': 3,
            'magnitude': 3,
            'description': 'coils around you and squeezes tight'
        }
    },
    {
        'name': "Snail",
        'health': 35,
        'attack': 5,
        'defense': 10,
        'level': 1,
        'flavor_text': "A giant snail oozes toward you, leaving a corrosive trail. Its shell is like a fortress.",
        'victory_text': "The snail withdraws into its shell one final time, cracking as it topples over.",
        'elemental_weakness': ['Fire', 'Poison'],
        'elemental_strength': ['Physical', 'Earth'],
        'can_talk': False,
        'special_attack': {
            'effect_type': 'defense_penalty',
            'chance': 0.20,
            'duration': 3,
            'magnitude': 4,
            'description': 'coats you in corrosive slime'
        }
    },
    {
        'name': "BUG QUEEN",
        'health': 65,
        'attack': 16,
        'defense': 10,
        'level': 3,
        'flavor_text': "The Bug Queen rises from her throne of chitin and silk. She holds Zot's Growth Mushroom in her mandibles. You're going to need that.",
        'victory_text': "The Bug Queen shrieks and collapses! A glowing mushroom tumbles from her mandibles!",
        'elemental_weakness': ['Fire'],
        'elemental_strength': ['Earth', 'Physical', 'Darkness'],
        'can_talk': True,
        'greeting_template': "Tiny {title} {name}? The wizard promised me a kingdom. You are trespassing in it!",
        'special_attack': {
            'effect_type': 'web',
            'chance': 0.30,
            'duration': 3,
            'magnitude': 0,
            'description': 'ensnares you in royal silk webbing'
        }
    },
]

# ============================================================================
# SPECIAL ATTACK BALANCE NOTES
# ============================================================================
"""
DESIGN PHILOSOPHY:
- Not every monster needs a special attack
- Basic monsters (levels 0-2): Weak/rare special attacks or none
- Intermediate (3-5): Moderate special attacks become common
- Advanced (6-8): Strong special attacks, higher chances
- Boss tier (9-10): Very powerful special attacks, high chances

SPECIAL ATTACK DISTRIBUTION:
- 39 out of 55 monsters have special attacks (71%)
- 16 monsters have no special attack (basic fighters/tanks)

EFFECT TYPE USAGE:
- Poison: 8 monsters (Rats, Centipede, Otyugh, Naga, Purple Worm, etc.)
- Life Drain: 6 monsters (Wight, Wraith, Specter, Vampire, Demilich)
- Burn: 8 monsters (Hell Hound, Fire Elemental, Dragons, etc.)
- Weakness: 9 monsters (Slime, Skeleton, Zombie, Mummy, Lich, etc.)
- Paralysis/Petrification: 6 monsters (Basilisk, Medusa, Gorgon, Grick, Grell)
- Confusion: 5 monsters (Umber Hulk, Beholder, Mind Flayer, Elder Brain, Sphinx)
- Web: 1 monster (Giant Spider - signature move!)
- Freeze: 1 monster (Giant Frost Worm)

BALANCE CONSIDERATIONS:
- Early game (0-2): 10-35% chance, 2-6 damage
- Mid game (3-5): 25-45% chance, 6-10 damage
- Late game (6-8): 35-60% chance, 10-15 damage
- End game (9-10): 45-75% chance, 14-20 damage

MONSTERS WITHOUT SPECIAL ATTACKS (By Design):
- Bat, Lichen (too weak)
- Goblin, Kobold (basic fighters)
- Gnoll, Bugbear, Ogre, Minotaur (pure physical fighters)
- Displacer Beast (has displacement ability)
- Griffin, Roc (aerial mobility)
- Stone Golem, Cyclops (just tanky)
"""

# Update MONSTER_TEMPLATES with attack_element
# Modifying specific monsters to have elemental attacks
for m in MONSTER_TEMPLATES:
    m['attack_element'] = 'Physical' # Default
    if 'Fire' in m['name'] or 'Hell' in m['name'] or 'Balrog' in m['name'] or 'Dragon' in m['name']:
        m['attack_element'] = 'Fire'
    elif 'Ice' in m['name'] or 'Frost' in m['name']:
        m['attack_element'] = 'Ice'
    elif 'Wind' in m['name'] or 'Griffin' in m['name']:
        m['attack_element'] = 'Wind'
    elif 'Earth' in m['name'] or 'Golem' in m['name']:
        m['attack_element'] = 'Earth'
    elif 'Water' in m['name'] or 'Turtle' in m['name']:
        m['attack_element'] = 'Water'
    elif 'Darkness' in m['name'] or 'Shadow' in m['name'] or 'Vampire' in m['name'] or 'Lich' in m['name'] or 'Wraith' in m['name']:
        m['attack_element'] = 'Darkness'
    elif 'Holy' in m['name'] or 'Angel' in m['name']:
        m['attack_element'] = 'Holy'
    elif 'Mind' in m['name'] or 'Brain' in m['name']:
        m['attack_element'] = 'Psionic'

