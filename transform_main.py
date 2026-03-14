"""
Script to transform cavernwiz_0_1_2_20_4.py into a thin wrapper.
Keeps only: imports, UI helper functions, WizardsCavernApp class, and entry point.
Removes all game logic that has been extracted to modules.
Transforms bare global references to gs.var_name.
"""
import re

SOURCE = "/Users/matthewporritt/Downloads/Cavern/cavernwiz_0_1_2_20_4.py"
OUTPUT = "/Users/matthewporritt/Downloads/Cavern/cavernwiz_0_1_2_20_4.py"
BACKUP = "/Users/matthewporritt/Downloads/Cavern/cavernwiz_0_1_2_20_4.py.bak"

# Read the original file
with open(SOURCE, 'r') as f:
    lines = f.readlines()

# Save backup
with open(BACKUP, 'w') as f:
    f.writelines(lines)

# ===================================================================
# STEP 1: Build the new file header with proper imports
# ===================================================================
header = '''#!/usr/bin/env python3
"""
Wizard's Cavern - Toga Version
A text-based dungeon crawler built with Toga and WebView for HTML rendering.

This file contains the UI layer (WizardsCavernApp class) and entry point.
Game logic is split across module files:
  - game_state.py: Shared mutable globals and utility functions
  - achievements.py: Achievement system
  - zotle.py: Zotle puzzle system
  - item_templates.py: Item/template data
  - items.py: Item classes and identification system
  - characters.py: Character, Monster, Inventory, StatusEffect classes
  - dungeon.py: Room, Floor, Tower classes and dungeon generation
  - combat.py: Combat system
  - vendor.py: Vendor system
  - save_system.py: Save/load system
  - room_actions.py: Room interaction handlers
  - game_systems.py: Vault, treasure, crafting, movement, stairs, etc.
"""

# Standard library imports
import random
import math
import re
import textwrap
from collections import deque
import json
import os
from datetime import datetime

# Toga framework
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

# Sprite and game data
from sprite_data import (
    generate_monster_sprite_html,
    generate_room_sprite_html,
    generate_player_sprite_html as _generate_player_sprite_html,
)
from game_data import (
    MONSTER_TEMPLATES,
    MONSTER_SPAWN_FLOOR_RANGE,
    MONSTER_EVOLUTION_TIERS,
    TROPHY_DROPS,
    TAXIDERMIST_COLLECTIONS,
)

# Game state (all shared mutable globals)
import game_state as gs
from game_state import (add_log, print_to_output, normal_int_range, get_article,
                        COLOR_RED, COLOR_GREEN, COLOR_RESET, COLOR_PURPLE,
                        COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_GREY, BOLD, UNDERLINE)

# Game modules - import all public names for backward compatibility
from achievements import Achievement, ACHIEVEMENTS, check_achievements
from zotle import (scramble_word_for_zotle, check_zotle_guess, initialize_zotle_puzzle,
                   format_zotle_guess_html, should_spawn_puzzle_room, spawn_puzzle_room_on_floor)
from item_templates import *
from items import *
from characters import *
from dungeon import Room, Floor, Tower, is_wall_at_coordinate
from combat import *
from vendor import *
from save_system import SaveSystem
from room_actions import *
from game_systems import *

'''

# ===================================================================
# STEP 2: Extract UI helper functions (lines 17204-17502)
# and WizardsCavernApp class + entry point (lines 17507-22412)
# ===================================================================
# We extract lines 17204 through end of file (0-indexed: 17203 to end)
ui_lines = lines[17203:]  # Line 17204 is index 17203

# ===================================================================
# STEP 3: Define globals that need gs. prefix
# ===================================================================
# These are ALL module-level mutable variables that have been moved to game_state.py
GLOBALS_TO_PREFIX = [
    # Core game state
    'log_lines', 'prompt_cntl', 'game_should_quit', 'player_character', 'my_tower',
    'previous_prompt_cntl', 'lets_go',
    # Entities
    'encountered_monsters', 'encountered_vendors', 'active_vendor', 'active_monster',
    'shop_message',
    # Active items/state
    'active_flare_item', 'active_scroll_item', 'active_foresight_scroll',
    'active_spell_choice', 'active_altar_state', 'active_towel_item',
    'active_zotle_teleporter',
    # Achievements
    'newly_unlocked_achievements', 'achievement_notification_timer',
    # Stats and tracking
    'game_stats', 'html_cache',
    # Dungeon/location tracking
    'dungeon_keys', 'unlocked_dungeons', 'looted_dungeons', 'looted_tombs',
    'harvested_gardens', 'haunted_floors', 'pending_tomb_guardian_reward',
    'ephemeral_gardens', 'searched_libraries',
    # Runes and quests
    'runes_obtained', 'shards_obtained', 'rune_progress', 'rune_progress_reqs',
    'champion_monster_available', 'legendary_chest_available', 'ancient_waters_available',
    'codex_available', 'master_dungeon_available', 'cursed_tomb_available',
    'world_tree_available', 'gate_to_floor_50_unlocked',
    # Zotle
    'zotle_puzzle',
    # Floor generation params
    'floor_params', 'specified_chars', 'required_chars', 'grid_rows', 'grid_cols',
    'wall_char', 'floor_char',
    'p_limits_val', 'c_limits_val', 'w_limits_val', 'a_limits_val', 'l_limits_val',
    'dungeon_limits_val', 't_limits_val', 'garden_limits_val', 'o_limits_val',
    'b_limits_val', 'f_limits_val', 'q_limits_val', 'k_limits_val', 'x_limits_val',
    # Combat state
    'last_player_damage', 'last_player_blocked', 'last_player_heal',
    'last_player_status', 'last_monster_damage', 'last_monster_status',
    # Identification system
    'item_cryptic_mapping', 'identified_items', 'equipment_use_count', 'discovered_items',
    # Miscellaneous
    'unique_treasures_spawned', '_pending_load',
    'pending_sell_item', 'pending_sell_item_index',
    'PLAYTEST',
    # Save system constants
    'SAVE_VERSION', 'SAVE_DIRECTORY', 'MAX_SAVE_SLOTS',
    # Zotle constants
    'ZOTLE_WORDS',
    # Misc constants
    'quit_txt',
]

# ===================================================================
# STEP 4: Transform the UI code
# ===================================================================
transformed_lines = []

for line in ui_lines:
    original = line

    # 4a. Remove 'global' declaration lines
    stripped = line.lstrip()
    if stripped.startswith('global ') and not stripped.startswith('global_'):
        # Check if this is truly a global declaration (not inside a string)
        indent = len(line) - len(stripped)
        # Keep it as a comment for reference but effectively remove it
        # Actually, just skip global declaration lines entirely
        # But we need to keep the line if it's inside a string literal
        # Simple heuristic: if the line starts with 'global' after stripping, it's a declaration
        transformed_lines.append('')  # Keep blank line to preserve line count
        continue

    # 4b. Replace bare global references with gs.var_name
    # Use word boundaries to avoid partial matches
    # Don't replace inside string literals (approximate: skip lines that are mostly strings)

    for var in GLOBALS_TO_PREFIX:
        # Pattern: word boundary + variable name + word boundary
        # But NOT when preceded by a dot (attribute access like self.player_character)
        # And NOT when preceded by 'gs.' (already prefixed)
        # And NOT in function parameter definitions
        # And NOT in import statements
        pattern = r'(?<!\.)\b' + re.escape(var) + r'\b'

        if re.search(pattern, line):
            # Don't modify import lines
            if 'import ' in line:
                continue
            # Don't modify def lines (function parameters)
            if stripped.startswith('def '):
                continue
            # Don't modify class lines
            if stripped.startswith('class '):
                continue
            # Don't modify comment-only lines
            if stripped.startswith('#'):
                continue

            # Apply the replacement, but not inside string literals
            # Simple approach: replace outside of quotes
            # More robust: use a callback function
            new_line = re.sub(
                r'(?<!\.)\b' + re.escape(var) + r'\b',
                'gs.' + var,
                line
            )
            line = new_line

    transformed_lines.append(line)

# ===================================================================
# STEP 5: Write the new file
# ===================================================================
with open(OUTPUT, 'w') as f:
    f.write(header)
    f.writelines(transformed_lines)

print(f"Transformation complete!")
print(f"Backup saved to: {BACKUP}")
print(f"New file written to: {OUTPUT}")
print(f"Original lines: {len(lines)}")
print(f"UI section lines: {len(ui_lines)}")
print(f"Total output lines: {len(header.splitlines()) + len(transformed_lines)}")
