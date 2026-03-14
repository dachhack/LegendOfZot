"""Fix remaining bare global references in module files."""
import re

# Globals that should NEVER be function parameters - safe to replace everywhere
ALWAYS_GLOBAL = [
    'active_monster', 'active_vendor', 'active_flare_item', 'active_scroll_item',
    'active_foresight_scroll', 'active_spell_choice', 'active_altar_state',
    'active_towel_item', 'active_zotle_teleporter',
    'rune_progress_reqs', 'runes_obtained', 'shards_obtained', 'rune_progress',
    'champion_monster_available', 'legendary_chest_available', 'ancient_waters_available',
    'codex_available', 'master_dungeon_available', 'cursed_tomb_available',
    'world_tree_available', 'gate_to_floor_50_unlocked',
    'encountered_monsters', 'encountered_vendors',
    'dungeon_keys', 'unlocked_dungeons', 'looted_dungeons', 'looted_tombs',
    'harvested_gardens', 'haunted_floors', 'ephemeral_gardens',
    'pending_tomb_guardian_reward', 'searched_libraries',
    'newly_unlocked_achievements', 'achievement_notification_timer',
    'game_stats', 'html_cache', 'unique_treasures_spawned',
    'identified_items', 'equipment_use_count', 'discovered_items', 'item_cryptic_mapping',
    'pending_sell_item', 'pending_sell_item_index',
    'last_player_damage', 'last_player_blocked', 'last_player_heal',
    'last_player_status', 'last_monster_damage', 'last_monster_status',
    'log_lines', 'prompt_cntl', 'game_should_quit', 'previous_prompt_cntl',
    'lets_go', 'shop_message', 'zotle_puzzle', '_pending_load',
    'PLAYTEST',
    # floor params
    'floor_params', 'specified_chars', 'required_chars', 'grid_rows', 'grid_cols',
]

files_to_fix = ['items.py', 'game_systems.py', 'room_actions.py', 'combat.py',
                'vendor.py', 'characters.py', 'dungeon.py', 'save_system.py']

for fname in files_to_fix:
    with open(fname) as f:
        content = f.read()

    original = content
    changes = 0

    for var in ALWAYS_GLOBAL:
        # Replace bare var with gs.var, but NOT when preceded by a dot or 'gs.'
        # Use negative lookbehind for dot
        pattern = r'(?<!\.)(?<![\w])' + re.escape(var) + r'\b'

        def replacer(m):
            # Get context before match
            start = m.start()
            # Check the character before our match (accounting for start of string)
            if start > 0 and content[start-1] == '.':
                return m.group(0)  # Don't replace attribute access
            # Check if already prefixed with gs.
            if start >= 3 and content[start-3:start] == 'gs.':
                return m.group(0)
            return 'gs.' + m.group(0)

        # Process line by line to skip def/class/import/comment lines
        lines = content.split('\n')
        new_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.lstrip()

            # Track docstrings
            if '"""' in stripped or "'''" in stripped:
                count = stripped.count('"""') + stripped.count("'''")
                if count == 1:
                    in_docstring = not in_docstring
                # If line has opening and closing quotes, it's a single-line docstring

            if in_docstring:
                new_lines.append(line)
                continue

            # Skip lines we shouldn't modify
            if (stripped.startswith('#') or stripped.startswith('import ') or
                stripped.startswith('from ') or stripped.startswith('def ') or
                stripped.startswith('class ') or stripped.startswith('"""') or
                stripped.startswith("'''")):
                new_lines.append(line)
                continue

            # Apply replacement
            word_pat = re.compile(r'\b' + re.escape(var) + r'\b')
            if word_pat.search(line):
                gs_pat = re.compile(r'gs\.' + re.escape(var) + r'\b')
                # Check if there are bare occurrences after removing gs.var ones
                cleaned = gs_pat.sub('XXXREMOVED', line)
                if word_pat.search(cleaned):
                    # There are bare occurrences - fix them
                    # Replace bare var with gs.var (not preceded by dot or word char)
                    new_line = re.sub(r'(?<!\.)(?<!\w)' + re.escape(var) + r'\b',
                                     'gs.' + var, line)
                    if new_line != line:
                        changes += 1
                        line = new_line

            new_lines.append(line)

        content = '\n'.join(new_lines)

    if content != original:
        with open(fname, 'w') as f:
            f.write(content)
        print(f'{fname}: {changes} lines fixed')
    else:
        print(f'{fname}: no changes needed')
