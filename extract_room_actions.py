#!/usr/bin/env python3
"""
Script to extract room interaction handlers from cavernwiz_0_1_2_20_4.py
into room_actions.py with proper gs. transformations.
"""

import re

SOURCE = "/Users/matthewporritt/Downloads/Cavern/cavernwiz_0_1_2_20_4.py"
OUTPUT = "/Users/matthewporritt/Downloads/Cavern/room_actions.py"

# Read source file
with open(SOURCE, 'r') as f:
    lines = f.readlines()

# Extract lines 13622-17057 (1-indexed -> 0-indexed: 13621-17056)
extracted = lines[13621:17057]

# Join into single string for processing
code = ''.join(extracted)

# 1. Remove all 'global varname' declarations
# Match lines like "    global prompt_cntl, game_should_quit, active_altar_state"
code = re.sub(r'^(\s*)global\s+[^\n]+\n', '', code, flags=re.MULTILINE)

# 2. Replace bare global variable references with gs.varname
# We need to be careful not to replace function parameters or local variables.
# Strategy: replace known global names that appear as bare identifiers.

# These are the globals we need to prefix with gs.
# We use word boundaries to avoid partial matches.
globals_to_replace = [
    'prompt_cntl',
    'active_altar_state',
    'game_stats',
    'zotle_puzzle',
    'active_zotle_teleporter',
    'searched_libraries',
    'dungeon_keys',
    'unlocked_dungeons',
    'looted_dungeons',
    'looted_tombs',
    'harvested_gardens',
    'runes_obtained',
    'shards_obtained',
    'rune_progress',
    'pending_tomb_guardian_reward',
    '_pending_load',
    'active_library_state',
    'active_scroll_item',
    'active_vendor',
    'shop_message',
    'game_should_quit',
    'PLAYTEST',
    'active_monster',
    'encountered_monsters',
    'ancient_waters_available',
    'cursed_tomb_available',
    'haunted_floors',
    'active_towel_item',
    'rune_progress_reqs',
    'previous_prompt_cntl',
    'floor_params',
    'identified_items',
    'ephemeral_gardens',
]

for gname in globals_to_replace:
    # Replace bare references that are NOT already prefixed with gs.
    # Also don't replace if preceded by a dot (would be obj.varname)
    # Pattern: word boundary, not preceded by 'gs.' or '.'
    pattern = r'(?<!gs\.)(?<!\.)(?<!\w)' + re.escape(gname) + r'(?=\b)'
    replacement = f'gs.{gname}'
    code = re.sub(pattern, replacement, code)

# Fix double-prefixing: gs.gs.varname -> gs.varname
code = re.sub(r'gs\.gs\.', 'gs.', code)

# 3. Fix specific issues:
# - 'codex_available' is used as local var in one place, but also as global
# We need gs.codex_available for the global references
code = code.replace('codex_available = False', 'gs.codex_available = False')
# Same for master_dungeon_available
code = code.replace('master_dungeon_available = True', 'gs.master_dungeon_available = True')
code = code.replace('master_dungeon_available = False', 'gs.master_dungeon_available = False')
code = code.replace('not master_dungeon_available', 'not gs.master_dungeon_available')
# champion_monster_available
code = code.replace('champion_monster_available', 'gs.champion_monster_available')
code = code.replace('gs.gs.champion_monster_available', 'gs.champion_monster_available')
# legendary_chest_available
code = code.replace('legendary_chest_available', 'gs.legendary_chest_available')
code = code.replace('gs.gs.legendary_chest_available', 'gs.legendary_chest_available')
# codex_available (bare references)
code = code.replace('not codex_available', 'not gs.codex_available')
code = code.replace('elif codex_available', 'elif gs.codex_available')
# world_tree_available
code = code.replace('world_tree_available', 'gs.world_tree_available')
code = code.replace('gs.gs.world_tree_available', 'gs.world_tree_available')
# gate_to_floor_50_unlocked
code = code.replace('gate_to_floor_50_unlocked', 'gs.gate_to_floor_50_unlocked')
code = code.replace('gs.gs.gate_to_floor_50_unlocked', 'gs.gate_to_floor_50_unlocked')
# ancient_waters_available bare refs (not already caught)
code = code.replace('not ancient_waters_available', 'not gs.ancient_waters_available')
code = code.replace('elif ancient_waters_available', 'elif gs.ancient_waters_available')
# cursed_tomb_available bare refs
code = code.replace('not cursed_tomb_available', 'not gs.cursed_tomb_available')
code = code.replace('elif cursed_tomb_available', 'elif gs.cursed_tomb_available')

# Fix any double gs. that slipped through
code = re.sub(r'gs\.gs\.', 'gs.', code)

# Fix floor generation params in process_zotle_teleporter_action
# These are module-level variables in game_state
code = code.replace('my_tower.add_floor(specified_chars, required_chars, grid_rows, grid_cols, wall_char, floor_char,',
                     'my_tower.add_floor(gs.specified_chars, gs.required_chars, gs.grid_rows, gs.grid_cols, gs.wall_char, gs.floor_char,')
code = code.replace('p_limits=p_limits_val', 'p_limits=gs.p_limits_val')
code = code.replace('c_limits=c_limits_val', 'c_limits=gs.c_limits_val')
code = code.replace('w_limits=w_limits_val', 'w_limits=gs.w_limits_val')
code = code.replace('a_limits=a_limits_val', 'a_limits=gs.a_limits_val')
code = code.replace('l_limits=l_limits_val', 'l_limits=gs.l_limits_val')
code = code.replace('dungeon_limits=dungeon_limits_val', 'dungeon_limits=gs.dungeon_limits_val')
code = code.replace('t_limits=t_limits_val', 't_limits=gs.t_limits_val')
code = code.replace('garden_limits=garden_limits_val', 'garden_limits=gs.garden_limits_val')
code = code.replace('o_limits=o_limits_val', 'o_limits=gs.o_limits_val')
code = code.replace('b_limits=b_limits_val', 'b_limits=gs.b_limits_val')
code = code.replace('f_limits=f_limits_val', 'f_limits=gs.f_limits_val')
code = code.replace('q_limits=q_limits_val', 'q_limits=gs.q_limits_val')
code = code.replace('k_limits=k_limits_val', 'k_limits=gs.k_limits_val')
code = code.replace('x_limits=x_limits_val', 'x_limits=gs.x_limits_val')

# Fix double gs. again
code = re.sub(r'gs\.gs\.', 'gs.', code)

# Build the header
header = '''"""
room_actions.py - Room interaction handlers for Wizard's Cavern.
Contains all process_*_action functions for altars, pools, libraries, dungeons,
tombs, gardens, oracles, blacksmith, shrine, alchemist, war room, taxidermist, etc.
"""

import random
import math
import game_state as gs
from game_state import (add_log, COLOR_RED, COLOR_GREEN, COLOR_RESET, COLOR_PURPLE,
                        COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_GREY, BOLD, UNDERLINE,
                        normal_int_range, get_article)

'''

# Remove the section comment header at the top of extracted code
code = re.sub(r'^# -+\n# 16\. ROOM INTERACTIONS.*?\n# -+\n\n', '', code)

# Write output
with open(OUTPUT, 'w') as f:
    f.write(header)
    f.write(code)

print(f"Wrote {OUTPUT}")

# Count lines
with open(OUTPUT, 'r') as f:
    line_count = sum(1 for _ in f)
print(f"Total lines: {line_count}")

# Verify key functions exist
with open(OUTPUT, 'r') as f:
    content = f.read()

functions = [
    'def process_altar_action',
    'def process_pool_action',
    'def process_library_action',
    'def process_library_read_decision',
    'def process_library_book_selection',
    'def process_dungeon_action',
    'def process_tomb_action',
    'def _track_tomb_progress',
    'def award_tomb_guardian_reward',
    'def process_garden_action',
    'def generate_oracle_hints',
    'def process_oracle_action',
    'def process_blacksmith_action',
    'def process_shrine_action',
    'def _alchemist_brew',
    'def process_alchemist_action',
    'def process_war_room_action',
    'def process_taxidermist_action',
    'def process_shard_vault_action',
    'def process_save_load_action',
    'def process_main_menu_action',
    'def process_lantern_quick_use',
    'def process_towel_action',
    'def process_puzzle_action',
    'def handle_puzzle_victory',
    'def use_zotle_teleporter',
    'def process_zotle_teleporter_action',
]

print("\nFunction verification:")
for func in functions:
    if func in content:
        print(f"  OK: {func}")
    else:
        print(f"  MISSING: {func}")

# Verify no bare 'global' statements remain
global_lines = [line for line in content.split('\n') if line.strip().startswith('global ')]
if global_lines:
    print(f"\nWARNING: {len(global_lines)} 'global' statements still present:")
    for gl in global_lines:
        print(f"  {gl.strip()}")
else:
    print("\nAll 'global' statements removed successfully.")

# Verify gs. prefixing
bare_refs = []
for gname in ['prompt_cntl', 'game_should_quit', 'active_altar_state', 'game_stats',
              'zotle_puzzle', 'active_zotle_teleporter', 'searched_libraries',
              'dungeon_keys', 'unlocked_dungeons', 'looted_dungeons', 'looted_tombs',
              'harvested_gardens', 'runes_obtained', 'shards_obtained', 'rune_progress',
              'pending_tomb_guardian_reward', '_pending_load', 'active_monster',
              'encountered_monsters']:
    # Find lines with bare references (not gs. prefixed)
    pattern = re.compile(r'(?<!gs\.)(?<!\.)(?<!\w)' + re.escape(gname) + r'\b')
    for i, line in enumerate(content.split('\n'), 1):
        # Skip comments and strings
        stripped = line.lstrip()
        if stripped.startswith('#'):
            continue
        if stripped.startswith(('"""', "'''")):
            continue
        matches = pattern.findall(line)
        if matches:
            # Check it's not in a string or comment
            code_part = line.split('#')[0]  # Remove inline comments
            if pattern.search(code_part):
                bare_refs.append((i, gname, line.strip()))

if bare_refs:
    print(f"\nWARNING: {len(bare_refs)} potential bare global references found:")
    for lineno, gname, line in bare_refs[:20]:
        print(f"  Line {lineno}: {gname} in: {line[:100]}")
else:
    print("\nAll global references properly prefixed with gs.")
