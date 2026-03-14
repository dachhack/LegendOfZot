"""Scan module files for bare global references missing gs. prefix."""
import re

globals_list = [
    'log_lines', 'prompt_cntl', 'game_should_quit', 'player_character', 'my_tower',
    'previous_prompt_cntl', 'lets_go', 'encountered_monsters', 'encountered_vendors',
    'active_vendor', 'active_monster', 'shop_message', 'active_flare_item',
    'active_scroll_item', 'active_foresight_scroll', 'active_spell_choice',
    'active_altar_state', 'active_towel_item', 'active_zotle_teleporter',
    'newly_unlocked_achievements', 'achievement_notification_timer', 'game_stats',
    'html_cache', 'dungeon_keys', 'unlocked_dungeons', 'looted_dungeons', 'looted_tombs',
    'harvested_gardens', 'haunted_floors', 'pending_tomb_guardian_reward',
    'ephemeral_gardens', 'searched_libraries', 'runes_obtained', 'shards_obtained',
    'rune_progress', 'rune_progress_reqs', 'champion_monster_available',
    'legendary_chest_available', 'ancient_waters_available', 'codex_available',
    'master_dungeon_available', 'cursed_tomb_available', 'world_tree_available',
    'gate_to_floor_50_unlocked', 'zotle_puzzle', 'floor_params', 'specified_chars',
    'required_chars', 'grid_rows', 'grid_cols', 'wall_char', 'floor_char',
    'identified_items', 'equipment_use_count', 'discovered_items',
    'item_cryptic_mapping', 'unique_treasures_spawned', '_pending_load',
    'pending_sell_item', 'pending_sell_item_index', 'PLAYTEST',
    'last_player_damage', 'last_player_blocked', 'last_player_heal',
    'last_player_status', 'last_monster_damage', 'last_monster_status',
]

files = ['items.py', 'game_systems.py', 'room_actions.py', 'combat.py',
         'vendor.py', 'characters.py', 'dungeon.py', 'save_system.py']

for fname in files:
    with open(fname) as f:
        lines = f.readlines()
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if (stripped.startswith('#') or stripped.startswith('import ') or
            stripped.startswith('from ') or stripped.startswith('def ') or
            stripped.startswith('class ') or not stripped or
            stripped.startswith('"""') or stripped.startswith("'''")):
            continue
        for var in globals_list:
            # Simple approach: check if var appears as a word not preceded by "gs."
            # First check if the var word appears at all
            word_pat = re.compile(r'\b' + re.escape(var) + r'\b')
            if not word_pat.search(line):
                continue
            # Now check if there's a bare occurrence (not preceded by "gs.")
            gs_pat = re.compile(r'gs\.' + re.escape(var) + r'\b')
            # Remove all gs.var occurrences
            cleaned = gs_pat.sub('XXXREMOVED', line)
            # Check if bare var still exists
            if word_pat.search(cleaned):
                # Skip if it's a function parameter (line contains "def " further up)
                # Skip if it's inside a string that looks like a key name
                print(f'{fname}:{i}: [{var}] {line.rstrip()[:120]}')
