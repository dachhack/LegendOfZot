"""
game_state.py - Shared global state and core utilities for Wizard's Cavern

All mutable game state lives here. Other modules import this module
and access/modify state via `gs.variable_name`.

Usage:
    from . import game_state as gs
    gs.prompt_cntl = "combat_mode"
    gs.player_character.health -= 10

For colors and utility functions, import directly:
    from .game_state import add_log, COLOR_RED, COLOR_GREEN, COLOR_RESET
"""

import random

# ============================================================================
# ANSI COLOR CODES
# ============================================================================
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_RESET = "\033[0m"
COLOR_PURPLE = '\033[35m'
COLOR_BLUE = '\033[94m'
COLOR_CYAN = '\033[96m'
COLOR_YELLOW = '\033[93m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
COLOR_GREY = '\u001b[38;5;245m'

# ============================================================================
# SAVE SYSTEM CONFIGURATION
# ============================================================================
SAVE_VERSION = "1.0"
SAVE_DIRECTORY = "saves"  # Overridden at startup on mobile via app.paths.data
MAX_SAVE_SLOTS = 3

# ============================================================================
# GAME LOOP STATE
# ============================================================================
log_lines = []
prompt_cntl = "intro_story"
previous_prompt_cntl = ""
game_should_quit = False
lets_go = False
html_cache = ""
quit_txt = "q = quit"

# ============================================================================
# PLAYER & WORLD
# ============================================================================
player_character = None
my_tower = None

# ============================================================================
# ACTIVE INTERACTION STATE
# ============================================================================
active_monster = None
active_vendor = None
active_altar_state = None
active_scroll_item = None
active_flare_item = None
active_foresight_scroll = None
active_flee_state = None
active_spell_choice = None
active_towel_item = None
active_library_state = None

# Inventory filter: None (show all), 'use', 'equip', or 'eat'
inventory_filter = None

# ============================================================================
# SHOP & SELL STATE
# ============================================================================
shop_message = ""
pending_sell_item = None
pending_sell_item_index = None

# ============================================================================
# ZOTLE PUZZLE SYSTEM
# ============================================================================
ZOTLE_WORDS = [
    'MORON', 'IDIOT', 'LOSER', 'DWEEB', 'PANSY', 'DUMMY', 'DUNCE', 'CLOWN',
    'DENSE', 'SILLY', 'TWERP', 'DUMBO', 'VAPID', 'THICK', 'NINNY', 'INANE'
]
zotle_puzzle = None
active_zotle_teleporter = False

# ============================================================================
# PLAYTEST MODE
# ============================================================================
PLAYTEST = False
_pending_load = None

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================
large_text_mode = False

# ============================================================================
# GAME STATISTICS (for achievements)
# ============================================================================
game_stats = {
    'monsters_killed': 0,
    'max_floor_reached': 0,
    'spells_learned': 0,
    'spells_cast': 0,
    'times_poisoned': 0,
    'chests_opened': 0,
    'vendors_visited': 0,
    'grimoires_read': 0,
    'spell_backfires': 0,
    'total_gold_collected': 0,
    'kills_no_armor': 0,
    'full_health_kills': 0,
    'defeated_higher_level': 0,
    'altars_used': 0,
    'flawless_floors': 0,
    'unique_vendors': set(),
    'vendors_sold_to': set(),
}

newly_unlocked_achievements = []
achievement_notification_timer = 0

# ============================================================================
# JOURNAL - DISCOVERED ITEMS
# ============================================================================
discovered_items = {
    'weapons': set(),
    'armor': set(),
    'potions': set(),
    'scrolls': set(),
    'spells': set(),
    'treasures': set(),
    'utilities': set(),
    'ingredients': set(),
}

# ============================================================================
# ITEM IDENTIFICATION SYSTEM
# ============================================================================
POTION_CRYPTIC_NAMES = [
    "Bubbling Potion", "Smoky Potion", "Cloudy Potion", "Effervescent Potion",
    "Fizzy Potion", "Milky Potion", "Murky Potion", "Glowing Potion",
    "Sparkling Potion", "Swirling Potion", "Viscous Potion", "Luminous Potion",
    "Oily Potion", "Slimy Potion", "Fuming Potion", "Steaming Potion",
    "Pungent Potion", "Clear Potion", "Thick Potion", "Watery Potion",
    "Iridescent Potion", "Shimmering Potion", "Opaque Potion", "Frothy Potion",
    "Dusty Potion", "Greasy Potion", "Chunky Potion", "Layered Potion",
]

SCROLL_CRYPTIC_NAMES = [
    "Scroll labeled ZELGO MER", "Scroll labeled JUYED AWK YACC",
    "Scroll labeled FOOBIE BLETCH", "Scroll labeled TEMOV",
    "Scroll labeled XIXAXA XOXAXA", "Scroll labeled PRATYAVAYAH",
    "Scroll labeled DAIYEN FANSEN", "Scroll labeled LEP GEX VEN ZEA",
    "Scroll labeled PRIRUTSENIE", "Scroll labeled ELBIB YLANSEN",
    "Scroll labeled VERR YED HULL", "Scroll labeled VENZAR BORGAVVE",
    "Scroll labeled NOSMAS", "Scroll labeled NEDNIL",
    "Scroll labeled KERNOD WEL", "Scroll labeled ELAM EBOW",
    "Scroll labeled DUAM XNAHT", "Scroll labeled ANDOVA BEGARIN",
    "Scroll labeled KIRJE", "Scroll labeled VE FORBRULL",
    "Scroll labeled GARVEN DEH", "Scroll labeled READ ME",
    "Scroll labeled HACKEM MUCHE", "Scroll labeled VELOX NEB",
]

SPELL_CRYPTIC_NAMES = [
    "Arcane Glyph", "Mystic Rune", "Eldritch Symbol", "Ancient Sigil",
    "Cryptic Inscription", "Faded Incantation", "Glowing Script", "Ethereal Writing",
    "Celestial Sign", "Runic Cipher", "Forbidden Verse", "Sacred Notation",
    "Profane Symbol", "Twisted Glyph", "Void Inscription", "Primal Rune",
    "Chaotic Script", "Ordered Pattern", "Spirit Writing", "Dream Sigil",
    "Ember Mark", "Twisted Cipher", "Shadow Script", "Blood Rune",
    "Power Glyph", "Sunken Verse", "Hollow Inscription", "Burning Notation",
    "Pale Sigil", "Iron Mark", "Shattered Glyph", "Woven Symbol",
    "Ashen Rune", "Dim Inscription", "Cracked Cipher", "Seeping Script",
    "Bound Verse", "Wandering Mark", "Silent Notation", "Echoing Sigil",
    "Warped Glyph", "Molten Rune", "Whispered Symbol", "Sundered Inscription",
    "Gilded Cipher", "Starless Script", "Bleached Verse", "Coiling Mark",
    "Veiled Notation", "Dormant Sigil", "Hungering Glyph", "Tideless Rune",
    "Fractured Symbol", "Unseen Inscription", "Fevered Cipher", "Rotting Script",
    "Hissing Verse", "Smoldering Mark", "Tangled Notation", "Midnight Sigil",
]

WEAPON_CRYPTIC_NAMES = [
    "Rusty Blade", "Worn Sword", "Notched Axe", "Dented Mace",
    "Tarnished Dagger", "Weathered Spear", "Crude Club", "Old Hammer",
    "Battered Blade", "Scratched Sword", "Chipped Axe", "Bent Blade",
    "Dusty Weapon", "Ancient Blade", "Mysterious Sword", "Strange Dagger",
    "Ornate Blade", "Etched Sword", "Runed Weapon", "Glinting Blade",
]

ARMOR_CRYPTIC_NAMES = [
    "Dented Armor", "Worn Mail", "Rusty Plate", "Tattered Leather",
    "Faded Robes", "Patched Armor", "Scuffed Mail", "Dingy Plate",
    "Frayed Leather", "Dusty Armor", "Mysterious Garb", "Strange Mail",
    "Ancient Armor", "Ornate Plate", "Etched Mail", "Glinting Armor",
    "Battered Plate", "Weathered Mail", "Crude Armor", "Old Leather",
]

item_cryptic_mapping = {
    'potions': {},
    'scrolls': {},
    'spells': {},
    'weapons': {},
    'armor': {},
}

identified_items = set()
equipment_use_count = {}
EQUIPMENT_ID_THRESHOLD = 5

# ============================================================================
# DUNGEON GENERATION PARAMETERS
# ============================================================================
specified_chars = ['M', 'C', 'A', 'P', 'W', 'L', 'N', 'T', 'G', 'O', 'B', 'F', 'Q', 'K', 'X', '.']
required_chars = ['D', 'U', 'V']
grid_rows = 15
grid_cols = 21
wall_char = '#'
floor_char = '.'

p_limits_val = (1, 3)
c_limits_val = (3, 7)
w_limits_val = (3, 6)
a_limits_val = (1, 3)
l_limits_val = (1, 3)
dungeon_limits_val = (1, 2)
t_limits_val = (1, 2)
garden_limits_val = (1, 2)
o_limits_val = (1, 2)
m_limits_val = (5, 12)
b_limits_val = (0, 1)
f_limits_val = (0, 1)
q_limits_val = (0, 1)
k_limits_val = (0, 1)
x_limits_val = (0, 1)

floor_params = {
    'specified_chars': specified_chars,
    'required_chars': required_chars,
    'grid_rows': grid_rows,
    'grid_cols': grid_cols,
    'wall_char': wall_char,
    'floor_char': floor_char,
    'p_limits': p_limits_val,
    'c_limits': c_limits_val,
    'w_limits': w_limits_val,
    'a_limits': a_limits_val,
    'l_limits': l_limits_val,
    'dungeon_limits': dungeon_limits_val,
    't_limits': t_limits_val,
    'garden_limits': garden_limits_val,
    'o_limits': o_limits_val,
    'm_limits': m_limits_val,
    'b_limits': b_limits_val,
    'f_limits': f_limits_val,
    'q_limits': q_limits_val,
    'k_limits': k_limits_val,
    'x_limits': x_limits_val,
}

# ============================================================================
# LOCATION TRACKING
# ============================================================================
searched_libraries = {}
dungeon_keys = {}
unlocked_dungeons = {}
looted_dungeons = {}
looted_tombs = {}
harvested_gardens = {}
harvested_fey_floors = set()  # Floors where a fey garden has been harvested (no respawn)

# ============================================================================
# QUEST TRACKING - RUNES & SHARDS (Orb of Zot)
# ============================================================================
runes_obtained = {
    'battle': False, 'treasure': False, 'devotion': False, 'reflection': False,
    'knowledge': False, 'secrets': False, 'eternity': False, 'growth': False,
}

shards_obtained = {
    'battle': False, 'treasure': False, 'devotion': False, 'reflection': False,
    'knowledge': False, 'secrets': False, 'eternity': False, 'growth': False,
}

rune_progress = {
    'monsters_killed_total': 0,
    'chests_opened_total': 0,
    'pools_drunk_total': 0,
    'spells_learned_total': 0,
    'unique_spells_memorized': set(),
    'dungeons_unlocked_total': 0,
    'tombs_looted_total': 0,
    'gardens_harvested_total': 0,
}

rune_progress_reqs = {
    'monsters_killed_total': 200,
    'chests_opened_total': 100,
    'pools_drunk_total': 50,
    'spells_learned_total': 30,
    'dungeons_unlocked_total': 30,
    'tombs_looted_total': 30,
    'gardens_harvested_total': 75,
    'player_health_obtained': 500,
    'gold_obtained': 50000,
}

# ============================================================================
# SPECIAL FLOOR AVAILABILITY FLAGS
# ============================================================================
champion_monster_available = False
legendary_chest_available = False
ancient_waters_available = False
codex_available = False
master_dungeon_available = False
cursed_tomb_available = False
world_tree_available = False
gate_to_floor_50_unlocked = False

# ============================================================================
# ENCOUNTER CACHES
# ============================================================================
encountered_vendors = {}
encountered_monsters = {}
unique_treasures_spawned = set()
curing_kit_stocked = False  # True once a vendor has stocked a Curing Kit — prevents duplicates

# ============================================================================
# COMBAT ANIMATION STATE
# ============================================================================
last_monster_damage = 0
last_player_damage = 0
last_player_blocked = False
last_player_status = None
last_monster_status = None
last_player_heal = 0

# ============================================================================
# MONSTER DEFEAT ANIMATION STATE
# ============================================================================
monster_defeated_anim = None  # Set to monster name string when killed, cleared after render
victory_monster_name = None   # Saved monster name for combat_victory view

# ============================================================================
# DICE ROLL ANIMATION STATE
# ============================================================================
# Stores the last combat dice rolls for the animated d20 display.
# Each entry is a tuple: (roll_value, needed, hit_bool, label)
#   roll_value: 1-20 result
#   needed: DC threshold (roll >= needed to succeed)
#   hit_bool: True if succeeded
#   label: short description e.g. "ATK", "DEF", "FLEE"
last_dice_rolls = []   # list of roll tuples to show this frame

# ============================================================================
# NEGATIVE STATUS EFFECT TYPES
# ============================================================================
NEGATIVE_EFFECT_TYPES = {
    'poison', 'damage_over_time', 'confusion', 'blindness', 'silence',
    'defense_penalty', 'web', 'sticky_hands', 'paralysis', 'weakness',
    'burn', 'freeze', 'life_drain', 'shrinking',
}

# ============================================================================
# SPECIAL FLOOR TRACKING
# ============================================================================
haunted_floors = {}
pending_tomb_guardian_reward = None
ephemeral_gardens = {}

# ============================================================================
# BUG LEVEL TRACKING
# ============================================================================
# Tracks which floors are bug levels. Player is shrunk on entry and must
# defeat the Bug Queen or find the Growth Mushroom to restore normal size.
bug_level_floors = {}  # floor_index -> True if this floor is a bug level
player_is_shrunk = False  # True while player is under Zot's shrinking spell
bug_queen_defeated = False  # Set True when Bug Queen falls on current bug level

# ============================================================================
# FEY GARDEN INGREDIENTS
# ============================================================================
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

# ============================================================================
# UNLOCKED ACHIEVEMENTS (runtime set)
# ============================================================================
unlocked_achievements = set()


# ============================================================================
# CORE UTILITY FUNCTIONS
# ============================================================================

def add_log(text):
    """Add a message to the game log, converting ANSI codes to HTML spans."""
    text = text.replace(COLOR_GREEN, '<span style="color: green;">')
    text = text.replace(COLOR_RED, '<span style="color: red;">')
    text = text.replace(COLOR_PURPLE, '<span style="color: #E040FB;">')
    text = text.replace(COLOR_BLUE, '<span style="color: darkblue;">')
    text = text.replace(COLOR_CYAN, '<span style="color: cyan;">')
    text = text.replace(COLOR_YELLOW, '<span style="color: yellow;">')
    text = text.replace(COLOR_GREY, '<span style="color: grey;">')
    text = text.replace(COLOR_RESET, '</span>')
    log_lines.append(text)
    if len(log_lines) > 16:
        log_lines.pop(0)


def print_to_output(text):
    """Alias for add_log for compatibility."""
    add_log(text)


def normal_int_range(mean):
    """Return an int drawn from a normal distribution centered on mean."""
    rand_num = random.gauss(1, 0.25)
    return int(max(0, (rand_num * mean)))


def get_article(name):
    """Return 'an' if the name starts with a vowel, otherwise 'a'."""
    if name and name[0].lower() in 'aeiou':
        return 'an'
    return 'a'
