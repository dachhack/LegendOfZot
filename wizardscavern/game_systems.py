"""
game_systems.py - Core game systems for Wizard's Cavern.
Contains vault system, treasure effects, crafting, inventory menu, movement,
chest/loot, character creation, stair handling, combat display, and grid rendering.
"""

import random
import math
import re
import textwrap
from . import game_state as gs
from .game_state import (add_log, print_to_output, COLOR_RED, COLOR_GREEN, COLOR_RESET,
                        COLOR_PURPLE, COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_GREY,
                        BOLD, UNDERLINE, normal_int_range, get_article)
from .sprite_data import generate_monster_sprite_html, generate_room_sprite_html
from .sprite_data import generate_player_sprite_html as _generate_player_sprite_html
from .game_data import (MONSTER_TEMPLATES, MONSTER_SPAWN_FLOOR_RANGE, MONSTER_EVOLUTION_TIERS,
                       TROPHY_DROPS, TAXIDERMIST_COLLECTIONS, BUG_MONSTER_TEMPLATES)
from .items import (Item, Potion, Weapon, Armor, Scroll, Spell, Treasure, Towel,
                   Flare, Lantern, LanternFuel, Food, Meat, CookingKit, CuringKit,
                   Sausage, Ingredient,
                   LembasWafer, Trophy, Rune, Shard, identify_item, is_item_identified,
                   get_item_display_name, register_item_discovery, _create_item_copy,
                   get_monster_meat_info, drop_monster_items, drop_monster_meat,
                   cook_meat_in_inventory, player_has_item_type,
                   process_potion_effects_in_combat, process_potion_effects_on_monster_defeat,
                   process_regeneration_effect, degrade_equipment, apply_corrosion_effect,
                   apply_rust_effect, repair_item, get_repair_cost,
                   process_hunger, tick_meat_rot, get_base_monster_name,
                   is_metal_item, generate_vendor_inventory, process_upgrade_scroll_action,
                   roll_buc_status, CORROSIVE_MONSTERS)
from .item_templates import (WEAPON_TEMPLATES, ARMOR_TEMPLATES, SCROLL_TEMPLATES,
                            UTILITY_TEMPLATES, TREASURE_TEMPLATES, POTION_TEMPLATES,
                            SPELL_TEMPLATES, ALL_ITEM_TEMPLATES, INGREDIENT_TEMPLATES,
                            UNIQUE_WEAPON_TEMPLATES, UNIQUE_ARMOR_TEMPLATES,
                            WEAPON_TIER_PREFIXES, ARMOR_TIER_PREFIXES,
                            POTION_RECIPES, LEMBAS_RECIPES, SAUSAGE_RECIPES,
                            GARDEN_INGREDIENTS, GARDEN_INGREDIENTS_DICT,
                            HUNGER_MAX, HUNGER_DECAY_PER_MOVE,
                            VAULT_DEFENDER_TEMPLATES, ENHANCED_MINOR_TREASURES,
                            UNIQUE_TREASURE_TEMPLATES,
                            ELEMENTAL_SUFFIXES, MULTI_ELEMENT_SUFFIXES)
from .characters import Character, Monster, Inventory, StatusEffect, get_sorted_inventory, format_item_for_display, burn_inventory_items
from .achievements import check_achievements
from .dungeon import Room, Floor, Tower, is_wall_at_coordinate
from .vendor import (Vendor, set_vendor_greeting, set_shop_msg, process_vendor_action,
                    handle_starting_shop, handle_vendor_shop, generate_magic_shop_inventory,
                    process_sell_quantity, reveal_adjacent_walls,
                    MAGIC_SHOP_NAMES, MAGIC_SHOP_MESSAGES, vendor_names)
from .save_system import SaveSystem


# Lazy imports to avoid circular dependencies with room_actions and combat.
# These functions are defined in those modules but called from here.

def use_zotle_teleporter(character, my_tower):
    from .room_actions import use_zotle_teleporter as _f; return _f(character, my_tower)

def process_altar_action(pc, tw, cmd):
    from .room_actions import process_altar_action as _f; return _f(pc, tw, cmd)
def process_pool_action(pc, tw, cmd):
    from .room_actions import process_pool_action as _f; return _f(pc, tw, cmd)
def process_library_action(pc, tw, cmd):
    from .room_actions import process_library_action as _f; return _f(pc, tw, cmd)
def process_dungeon_action(pc, tw, cmd):
    from .room_actions import process_dungeon_action as _f; return _f(pc, tw, cmd)
def process_tomb_action(pc, tw, cmd):
    from .room_actions import process_tomb_action as _f; return _f(pc, tw, cmd)
def process_garden_action(pc, tw, cmd):
    from .room_actions import process_garden_action as _f; return _f(pc, tw, cmd)
def process_oracle_action(pc, tw, cmd):
    from .room_actions import process_oracle_action as _f; return _f(pc, tw, cmd)
def process_blacksmith_action(pc, tw, cmd):
    from .room_actions import process_blacksmith_action as _f; return _f(pc, tw, cmd)
def process_shrine_action(pc, tw, cmd):
    from .room_actions import process_shrine_action as _f; return _f(pc, tw, cmd)
def process_alchemist_action(pc, tw, cmd):
    from .room_actions import process_alchemist_action as _f; return _f(pc, tw, cmd)
def process_war_room_action(pc, tw, cmd):
    from .room_actions import process_war_room_action as _f; return _f(pc, tw, cmd)
def process_taxidermist_action(pc, tw, cmd):
    from .room_actions import process_taxidermist_action as _f; return _f(pc, tw, cmd)
def process_shard_vault_action(pc, tw, cmd):
    from .room_actions import process_shard_vault_action as _f; return _f(pc, tw, cmd)
def process_save_load_action(pc, tw, cmd):
    from .room_actions import process_save_load_action as _f; return _f(pc, tw, cmd)
def process_lantern_quick_use(pc, tw):
    from .room_actions import process_lantern_quick_use as _f; return _f(pc, tw)
def process_towel_action(pc, tw, cmd):
    from .room_actions import process_towel_action as _f; return _f(pc, tw, cmd)
def process_puzzle_action(pc, tw, cmd):
    from .room_actions import process_puzzle_action as _f; return _f(pc, tw, cmd)
def process_combat_action(pc, tw, cmd):
    from .combat import process_combat_action as _f; return _f(pc, tw, cmd)
def process_spell_memorization_action(pc, tw, cmd):
    from .combat import process_spell_memorization_action as _f; return _f(pc, tw, cmd)
def process_spell_casting_action(pc, tw, cmd):
    from .combat import process_spell_casting_action as _f; return _f(pc, tw, cmd)
def process_journal_action(pc, tw, cmd):
    from .combat import process_journal_action as _f; return _f(pc, tw, cmd)


# --------------------------------------------------------------------------------
# 12. VAULT SYSTEM
# --------------------------------------------------------------------------------

def can_carve_vault_at(floor, start_row, start_col, vault_size=3):
    """
    Check if we can carve a vault_size x vault_size vault room at the given position.
    Vault must be entirely in walls with no floor cells nearby.
    """
    rows = floor.rows
    cols = floor.cols

    # Check if vault would fit in bounds (with 1-cell buffer)
    if start_row < 1 or start_col < 1:
        return False
    if start_row + vault_size + 1 >= rows or start_col + vault_size + 1 >= cols:
        return False

    # Check that entire vault area + 1-cell buffer is walls
    for r in range(start_row - 1, start_row + vault_size + 1):
        for c in range(start_col - 1, start_col + vault_size + 1):
            if 0 <= r < rows and 0 <= c < cols:
                if floor.grid[r][c].room_type != floor.wall_char:
                    return False

    return True


def find_vault_location(floor, vault_size=3):
    """
    Find a suitable location for a vault room.
    Returns (row, col) or None if no location found.
    """
    attempts = 0
    max_attempts = 100

    while attempts < max_attempts:
        # Try random location
        start_row = random.randint(2, floor.rows - vault_size - 2)
        start_col = random.randint(2, floor.cols - vault_size - 2)

        if can_carve_vault_at(floor, start_row, start_col, vault_size):
            return (start_row, start_col)

        attempts += 1

    return None


def carve_vault_rooms(floor, vault_row, vault_col, vault_size=3):
    """
    Carve out a single vault room with the guardian.
    This is a standalone chamber - players reach it via vault warp from regular warps.

    Layout:
    [#][#][#]
    [#][V][#]  <- Vault defender + treasure (single room)
    [#][#][#]

    Returns: vault_coords or None if failed
    """
    vault_center_row = vault_row + 1
    vault_center_col = vault_col + 1

    for r in range(vault_row, vault_row + vault_size):
        for c in range(vault_col, vault_col + vault_size):
            if r == vault_center_row and c == vault_center_col:
                floor.grid[r][c].room_type = 'M'  # Vault defender (monster)
                floor.grid[r][c].properties['is_vault_defender'] = True
            else:
                floor.grid[r][c].room_type = '.'  # Floor

    vault_coords = (vault_center_col, vault_center_row)

    return vault_coords


def generate_vault_on_floor(floor, floor_level):
    """
    Attempt to generate a vault on the given floor.
    Creates a single-room vault chamber and marks one existing warp as a vault warp.
    Returns True if vault was generated, False otherwise.
    In PLAYTEST mode, vaults always spawn.
    """
    # Check if we should generate a Shard Vault instead
    # Shard Vaults start appearing on floors 15+
    if floor_level >= 15:
        # Check which runes player has but hasn't gotten shards for
        available_shard_types = []
        for rune_type in ['battle', 'treasure', 'devotion', 'reflection', 'knowledge', 'secrets', 'eternity', 'growth']:
            if gs.runes_obtained.get(rune_type) and not gs.shards_obtained.get(rune_type):
                available_shard_types.append(rune_type)
        
        # 40% chance to make this a Shard Vault if runes available
        if available_shard_types and random.random() < 0.40:
            shard_type = random.choice(available_shard_types)
            return generate_shard_vault(floor, floor_level, shard_type)
    
    # Regular vault generation
    # 15% chance per floor (100% in PLAYTEST mode)
    if not gs.PLAYTEST and random.random() > 0.15:
        return False

    # Find location for vault chamber
    location = find_vault_location(floor, vault_size=3)
    if not location:
        return False

    vault_row, vault_col = location

    # Carve the vault (now returns just vault_coords)
    vault_coords = carve_vault_rooms(floor, vault_row, vault_col, vault_size=3)

    if vault_coords:
        # Mark vault chamber
        floor.grid[vault_coords[1]][vault_coords[0]].properties['is_vault_chamber'] = True
        
        # Find an existing regular warp on the floor and mark it as a vault warp
        warp_positions = []
        for r in range(floor.rows):
            for c in range(floor.cols):
                room = floor.grid[r][c]
                if room.room_type == 'W' and not room.properties.get('vault_warp', False):
                    warp_positions.append((c, r))  # (x, y) format
        
        if warp_positions:
            # Pick a random warp to be the vault warp
            chosen_warp = random.choice(warp_positions)
            warp_x, warp_y = chosen_warp
            floor.grid[warp_y][warp_x].properties['vault_warp'] = True
            floor.grid[warp_y][warp_x].properties['vault_destination'] = vault_coords
            
            if gs.PLAYTEST == True:
                add_log(f"{COLOR_PURPLE}[gs.PLAYTEST] Vault chamber at {vault_coords}, linked warp at {chosen_warp}{COLOR_RESET}")
            return True
        else:
            if gs.PLAYTEST == True:
                add_log(f"{COLOR_YELLOW}[gs.PLAYTEST] Vault chamber created but no warp found to link{COLOR_RESET}")
            # Still return True - vault exists, just no warp linked yet
            # Store vault coords on the floor for potential later linking
            floor.pending_vault_coords = vault_coords
            return True

    return False


# 
# VAULT DEFENDER CREATION
# 

def generate_shard_vault(floor, floor_level, shard_type):
    """Generate a Shard Vault containing a Legendary Monster"""
    
    # Find location
    location = find_vault_location(floor, vault_size=3)
    if not location:
        return False
    
    vault_row, vault_col = location
    
    # Carve the vault (now returns just vault_coords)
    vault_coords = carve_vault_rooms(floor, vault_row, vault_col, vault_size=3)
    
    if vault_coords:
        # Mark vault chamber as Shard Vault
        floor.grid[vault_coords[1]][vault_coords[0]].room_type = 'V'  # Make it a vault room
        floor.grid[vault_coords[1]][vault_coords[0]].properties['is_vault_chamber'] = True
        floor.grid[vault_coords[1]][vault_coords[0]].properties['shard_vault_type'] = shard_type
        
        # Find an existing regular warp on the floor and mark it as a shard vault warp
        warp_positions = []
        for r in range(floor.rows):
            for c in range(floor.cols):
                room = floor.grid[r][c]
                if room.room_type == 'W' and not room.properties.get('vault_warp', False):
                    warp_positions.append((c, r))  # (x, y) format
        
        shard_names = {
            'battle': 'Battle Shard Vault',
            'treasure': 'Treasure Shard Vault',
            'devotion': 'Devotion Shard Vault',
            'reflection': 'Reflection Shard Vault',
            'knowledge': 'Knowledge Shard Vault',
            'secrets': 'Secrets Shard Vault',
            'eternity': 'Eternity Shard Vault',
            'growth': 'Growth Shard Vault'
        }
        
        if warp_positions:
            # Pick a random warp to be the shard vault warp
            chosen_warp = random.choice(warp_positions)
            warp_x, warp_y = chosen_warp
            floor.grid[warp_y][warp_x].properties['vault_warp'] = True
            floor.grid[warp_y][warp_x].properties['vault_destination'] = vault_coords
            floor.grid[warp_y][warp_x].properties['is_shard_vault'] = True
            floor.grid[warp_y][warp_x].properties['shard_type'] = shard_type
            
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}A {shard_names[shard_type]} has manifested!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            
            if gs.PLAYTEST:
                add_log(f"{COLOR_PURPLE}[gs.PLAYTEST] Shard Vault ({shard_type}) chamber at {vault_coords}, linked warp at {chosen_warp}{COLOR_RESET}")

            return True
        else:
            if gs.PLAYTEST:
                add_log(f"{COLOR_YELLOW}[gs.PLAYTEST] Shard Vault chamber created but no warp found to link{COLOR_RESET}")
            # Store vault coords for potential later linking
            floor.pending_shard_vault_coords = vault_coords
            floor.pending_shard_vault_type = shard_type
            return True
    
    return False


def create_legendary_monster(shard_type, floor_level):
    """Create a Legendary Monster for the specified shard type"""
    
    legendary_templates = {
        'battle': {
            'name': 'DRAGON',
            'base_health': 300,
            'base_attack': 40,
            'base_defense': 25,
            'element': 'Fire',
            'flavor': 'A primordial dragon of immense power! Its scales shimmer with ancient magic!',
            'victory': 'The Ancient Dragon falls! Its power flows into you!',
            'gold_min': 800,
            'gold_max': 1200
        },
        'treasure': {
            'name': ' TREASURE GOLEM',
            'base_health': 400,
            'base_attack': 30,
            'base_defense': 35,
            'element': 'Physical',
            'flavor': 'A massive construct made of gold and gems! It guards infinite wealth!',
            'victory': 'The Treasure Golem crumbles! Riches spill forth!',
            'gold_min': 1000,
            'gold_max': 1500
        },
        'devotion': {
            'name': '~~~ DIVINE AVATAR',
            'base_health': 350,
            'base_attack': 45,
            'base_defense': 20,
            'element': 'Light',
            'flavor': 'A celestial being radiating holy power! The gods themselves watch!',
            'victory': 'The Divine Avatar dissipates into pure light!',
            'gold_min': 600,
            'gold_max': 1000
        },
        'reflection': {
            'name': 'LORD',
            'base_health': 320,
            'base_attack': 38,
            'base_defense': 28,
            'element': 'Water',
            'flavor': 'A being of pure water and reflection! Reality bends around it!',
            'victory': 'The Water Elemental Lord dissolves into mist!',
            'gold_min': 700,
            'gold_max': 1100
        },
        'knowledge': {
            'name': 'ARCHLICH',
            'base_health': 280,
            'base_attack': 50,
            'base_defense': 15,
            'element': 'Darkness',
            'flavor': 'An undead sorcerer of terrible power! Ancient spells swirl around it!',
            'victory': 'The Archlich crumbles to dust! Knowledge floods your mind!',
            'gold_min': 500,
            'gold_max': 900
        },
        'secrets': {
            'name': 'DEMON',
            'base_health': 300,
            'base_attack': 42,
            'base_defense': 22,
            'element': 'Darkness',
            'flavor': 'A creature born from secrets and lies! It knows your deepest fears!',
            'victory': 'The Shadow Demon disperses! Secrets are laid bare!',
            'gold_min': 650,
            'gold_max': 1050
        },
        'eternity': {
            'name': ' DEATH KNIGHT',
            'base_health': 380,
            'base_attack': 48,
            'base_defense': 30,
            'element': 'Darkness',
            'flavor': 'An immortal warrior cursed to fight forever! Death itself empowers it!',
            'victory': 'The Death Knight falls... at last finding peace!',
            'gold_min': 750,
            'gold_max': 1150
        },
        'growth': {
            'name': 'ANCIENT',
            'base_health': 450,
            'base_attack': 35,
            'base_defense': 40,
            'element': 'Nature',
            'flavor': 'A walking forest older than time itself! Life energy radiates from its bark!',
            'victory': 'The Treant Ancient returns to the earth! Nature rejoices!',
            'gold_min': 600,
            'gold_max': 1000
        }
    }
    
    template = legendary_templates[shard_type]
    
    # Scale with floor level
    scaled_health = template['base_health'] + (floor_level * 15)
    scaled_attack = template['base_attack'] + (floor_level * 3)
    scaled_defense = template['base_defense'] + (floor_level * 2)
    
    legendary = Monster(
        name=template['name'],
        health=scaled_health,
        attack=scaled_attack,
        defense=scaled_defense,
        elemental_weakness=[],
        elemental_strength=[template['element']],
        level=floor_level + 5,  # Much higher level
        attack_element=template['element'],
        flavor_text=template['flavor'],
        victory_text=template['victory']
    )
    
    legendary.properties['is_legendary'] = True
    legendary.properties['shard_type'] = shard_type
    legendary.properties['gold_min'] = template['gold_min']
    legendary.properties['gold_max'] = template['gold_max']
    
    return legendary


def create_vault_defender(floor_level):
    """
    Create a vault defender scaled to the floor level.
    Vault defenders are much stronger than normal monsters.
    """
    # Choose random defender template
    template = random.choice(VAULT_DEFENDER_TEMPLATES)

    # Scale stats based on floor level
    scaled_health = template['base_health'] + (template['health_per_level'] * floor_level)
    scaled_attack = template['base_attack'] + (template['attack_per_level'] * floor_level)
    scaled_defense = template['base_defense'] + (template['defense_per_level'] * floor_level)
    scaled_level = max(floor_level + 2, 1)  # Always 2+ levels above floor

    defender = Monster(
        name=template['name'],
        health=scaled_health,
        attack=scaled_attack,
        defense=scaled_defense,
        elemental_weakness=template['elemental_weakness'],
        elemental_strength=template['elemental_strength'],
        level=scaled_level,
        attack_element=template['attack_element'],
        flavor_text=template['flavor_text'],
        victory_text=template['victory_text'],
        can_talk=template.get('can_talk', False),
        greeting_template=template.get('greeting_template', '')
    )

    return defender


# 
# VAULT WARP HANDLING
# 

def process_vault_warp_action(player_character, my_tower, cmd):
    """
    Handle interaction with vault warp entrance.
    This is a one-way trip!
    """

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]

    if cmd == "init":
        add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}A mysterious warp portal shimmers before you!{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}This portal radiates immense power...{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
        add_log("")
        add_log(f"{COLOR_YELLOW}You sense this portal leads to a VAULT CHAMBER.{COLOR_RESET}")
        add_log(f"{COLOR_RED}  You cannot flee from vault defenders!{COLOR_RESET}")
        add_log("")
        add_log(f"{COLOR_CYAN}Enter the vault? (y/n){COLOR_RESET}")
        # Commands now shown in HTML and placeholder
        return

    if cmd == 'y':
        # Point of no return!
        add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}You step through the shimmering portal...{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}Reality bends around you!{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}{COLOR_RESET}")

        vault_destination = room.properties.get('vault_destination')
        if vault_destination:
            vault_x, vault_y = vault_destination
            player_character.x = vault_x
            player_character.y = vault_y

            # Discover vault chamber
            vault_room = current_floor.grid[vault_y][vault_x]
            vault_room.discovered = True
            reveal_adjacent_walls(player_character, my_tower)

            add_log(f"{COLOR_PURPLE}You materialize in a sealed chamber!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}The air crackles with ancient magic...{COLOR_RESET}")

            # Create vault defender if not already exists
            coords = (vault_x, vault_y, player_character.z)
            if coords not in gs.encountered_monsters:
                defender = create_vault_defender(player_character.z)
                gs.encountered_monsters[coords] = defender
                add_log(f"{COLOR_RED}A VAULT DEFENDER appears!{COLOR_RESET}")

            # Trigger combat
            _trigger_room_interaction(player_character, my_tower)
        else:
            add_log(f"{COLOR_RED}ERROR: Vault destination not found!{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"

    elif cmd == 'n':
        add_log(f"{COLOR_YELLOW}You step back from the portal. Perhaps you'll return when better prepared...{COLOR_RESET}")
        gs.prompt_cntl = "game_loop"

    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")

    elif cmd in ['n', 's', 'e', 'w']:
        moved = move_player(player_character, my_tower, cmd)
        if not moved:
            gs.prompt_cntl = "vault_warp_mode"

    elif cmd == 'q':
        gs.game_should_quit = True


# 
# VAULT DEFENDER COMBAT HANDLING
# 

def is_vault_defender(monster, coords):
    """Check if a monster is a vault defender"""
    if not monster:
        return False

    # Check if monster's room is marked as vault defender
    x, y, z = coords
    # Note: We'll need to check room properties in the actual integration
    return any(template['name'] == monster.name for template in VAULT_DEFENDER_TEMPLATES)


def process_vault_defender_combat(player_character, my_tower, cmd):
    """
    Handle combat with vault defender.
    Key differences:
    - Cannot flee
    - Guaranteed unique treasure on victory
    """

    if cmd == "init":
        add_log(f"{COLOR_RED}{COLOR_RESET}")
        add_log(f"{COLOR_RED}VAULT DEFENDER BATTLE!{COLOR_RESET}")
        add_log(f"{COLOR_RED}{COLOR_RESET}")

        # Get player title
        player_title = get_player_title(player_character)

        # Show defender greeting
        if hasattr(gs.active_monster, 'can_talk') and gs.active_monster.can_talk:
            greeting = gs.active_monster.greeting_template.format(
                name=player_character.name,
                title=player_title
            )
            add_log(f"{COLOR_PURPLE}{greeting}{COLOR_RESET}")
        else:
            add_log(f"{COLOR_RED}The {gs.active_monster.name} (Level {gs.active_monster.level}) guards this vault!{COLOR_RESET}")

        add_log("")
        add_log(f"{COLOR_YELLOW}  You CANNOT flee from this battle!{COLOR_RESET}")
        add_log(f"{COLOR_GREEN}Victory grants a GUARANTEED unique treasure!{COLOR_RESET}")
        add_log("")
        # Commands now shown in HTML and placeholder
        return

    # Process combat (same as normal but without flee option)
    player_character.process_status_effects()
    if gs.active_monster and gs.active_monster.is_alive():
        gs.active_monster.process_status_effects()

    process_passive_treasures(player_character)

    # Check deaths from status effects
    if not player_character.is_alive():
        add_log(f"{COLOR_RED}You were defeated by status effects...{COLOR_RESET}")
        gs.prompt_cntl = "death_screen"
        # render() removed - will be called by process_command
        return

    if gs.active_monster and not gs.active_monster.is_alive():
        handle_vault_defender_victory(player_character, my_tower)
        return

    # Handle commands
    if cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
        return

    if cmd == 'a':
        # Player attacks
        damage_type = "Physical"
        if player_character.equipped_weapon and player_character.equipped_weapon.elemental_strength:
            val = player_character.equipped_weapon.elemental_strength[0]
            if val != "None":
                damage_type = val

        # FIRST ATTACK
        dmg = player_character.attack_target(gs.active_monster)
        if dmg>0:
          gs.active_monster.take_damage(dmg, damage_type)
          if 'Vampiric' in player_character.status_effects:
              lifesteal_pct = player_character.status_effects['Vampiric'].magnitude
              heal_amount = int(dmg * lifesteal_pct / 100)
              old_health = player_character.health
              player_character.health = min(player_character.max_health, player_character.health + heal_amount)
              actual_heal = player_character.health - old_health
              if actual_heal > 0:
                  add_log(f"{COLOR_RED} Vampirism: Healed {actual_heal} HP from damage!{COLOR_RESET}")

        # If using wet towel as weapon, it dries slightly with each hit
        if isinstance(player_character.equipped_weapon, Towel) and player_character.equipped_weapon.wetness > 0:
            # 50% chance to dry by 1 level per hit
            if random.random() < 0.5:
                player_character.equipped_weapon.dry_one_level()

        # Corrosive monsters damage equipment on contact
        if (gs.active_monster.name in CORROSIVE_MONSTERS or get_base_monster_name(gs.active_monster.name) in CORROSIVE_MONSTERS) and player_character.equipped_weapon:
            corrosion_messages = apply_corrosion_effect(player_character, gs.active_monster.name, is_player_attacking=True)
            for msg in corrosion_messages:
                add_log(msg)

        # NEW: CHECK FOR HASTE - SECOND ATTACK
        if 'Haste' in player_character.status_effects and gs.active_monster.is_alive():
            add_log(f"{COLOR_CYAN} [HASTE] You attack again!{COLOR_RESET}")

            # SECOND ATTACK (same logic as first)
            dmg2 = player_character.attack_target(gs.active_monster)
            if dmg2 > 0:
                gs.active_monster.take_damage(dmg2, damage_type)
                if 'Vampiric' in player_character.status_effects:
                    lifesteal_pct = player_character.status_effects['Vampiric'].magnitude
                    heal_amount = int(dmg2 * lifesteal_pct / 100)
                    old_health = player_character.health
                    player_character.health = min(player_character.max_health, player_character.health + heal_amount)
                    actual_heal = player_character.health - old_health
                    if actual_heal > 0:
                        add_log(f"{COLOR_RED} Vampirism: Healed {actual_heal} HP from damage!{COLOR_RESET}")

        if not gs.active_monster.is_alive():
            handle_vault_defender_victory(player_character, my_tower)
            return

        # Monster attacks back
        gs.active_monster.attack_target(player_character)

        if not player_character.is_alive():
            add_log(f"{COLOR_RED}You were defeated by the {gs.active_monster.name}...{COLOR_RESET}")
            add_log(f"{COLOR_RED}The vault will claim another victim...{COLOR_RESET}")
            gs.prompt_cntl = "death_screen"
            return

    elif cmd == 'f':
        # Cannot flee!
        add_log(f"{COLOR_RED}You cannot flee from a vault defender!{COLOR_RESET}")
        add_log(f"{COLOR_RED}Fight or die - those are your only options!{COLOR_RESET}")

        # Monster gets a free attack for trying to flee!
        add_log(f"{COLOR_YELLOW}Your cowardice gives the defender an opening!{COLOR_RESET}")
        gs.active_monster.attack_target(player_character)

        if not player_character.is_alive():
            add_log(f"{COLOR_RED}You were defeated...{COLOR_RESET}")
            gs.prompt_cntl = "death_screen"
            return

    elif cmd == 'c':
        # Only allow spell casting if player can cast spells
        if not can_cast_spells(player_character):
            add_log(f"{COLOR_YELLOW}You cannot cast spells. (Requires Intelligence > 15){COLOR_RESET}")
            return
        gs.prompt_cntl = 'spell_casting_mode'
        process_spell_casting_action(player_character, my_tower, "init")
        return

    else:
        add_log(f"{COLOR_YELLOW}Invalid command. a = attack | i = inventory | c = cast spell{COLOR_RESET}")


def handle_vault_defender_victory(player_character, my_tower):
    """
    Handle victory over vault defender.
    Grants guaranteed unique treasure + massive rewards.
    Creates an escape warp to leave the vault.
    """

    add_log(f"{COLOR_GREEN}{COLOR_RESET}")
    add_log(f"{COLOR_GREEN}VICTORY! The vault defender has fallen!{COLOR_RESET}")
    add_log(f"{COLOR_GREEN}{COLOR_RESET}")

    if gs.active_monster and hasattr(gs.active_monster, 'victory_text'):
        add_log(f"{COLOR_CYAN}{gs.active_monster.victory_text}{COLOR_RESET}")

    # Massive XP reward
    xp_reward = (gs.active_monster.level + 1) * 100  # 4x normal XP
    player_character.gain_experience(xp_reward)
    add_log(f"{COLOR_GREEN}Gained {xp_reward} XP for defeating the vault defender!{COLOR_RESET}")

    # Massive gold reward
    gold_drop = random.randint(200, 500) * (player_character.z + 1)
    player_character.gold += gold_drop
    add_log(f"{COLOR_YELLOW}Found {gold_drop} gold in the vault!{COLOR_RESET}")
    gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold_drop

    # GUARANTEED UNIQUE TREASURE!
    add_log("")
    add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}The vault unseals, revealing its treasure!{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}{COLOR_RESET}")

    # Find unique treasure that hasn't spawned yet
    available_uniques = [
        t for t in UNIQUE_TREASURE_TEMPLATES
        if t.name not in gs.unique_treasures_spawned
    ]

    if available_uniques:
        # Prefer higher level treasures for deeper vaults
        suitable_uniques = [t for t in available_uniques if t.level <= player_character.z + 5]
        if not suitable_uniques:
            suitable_uniques = available_uniques

        chosen = random.choice(suitable_uniques)
        gs.unique_treasures_spawned.add(chosen.name)

        new_treasure = _create_item_copy(chosen)
        player_character.inventory.add_item(new_treasure)

        add_log(f"{COLOR_YELLOW}   LEGENDARY UNIQUE TREASURE!   {COLOR_RESET}")
        add_log(f"{COLOR_YELLOW}You obtained: {chosen.name}!{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}{chosen.description}{COLOR_RESET}")
    else:
        # All uniques already spawned - give massive stat boost instead
        add_log(f"{COLOR_YELLOW}The vault's magic infuses you with power!{COLOR_RESET}")
        player_character.strength += 3
        player_character.dexterity += 3
        player_character.intelligence += 3
        add_log(f"{COLOR_GREEN}All stats increased by 3!{COLOR_RESET}")

    # Track achievement
    gs.game_stats['monsters_killed'] = gs.game_stats.get('monsters_killed', 0) + 1
    gs.game_stats['vault_defenders_defeated'] = gs.game_stats.get('vault_defenders_defeated', 0) + 1
    check_achievements(player_character)

    # Clear the room and create escape warp
    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    room.room_type = 'W'  # Turn into a warp for escape
    room.properties['vault_cleared'] = True
    room.properties['vault_warp'] = False  # Make it a regular warp, not vault warp
    room.properties.pop('is_vault_chamber', None)
    room.properties.pop('is_vault_defender', None)

    gs.active_monster = None

    add_log("")
    add_log(f"{COLOR_PURPLE}A shimmering portal opens where the defender fell!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Step into it to escape the vault.{COLOR_RESET}")

    gs.prompt_cntl = "game_loop"




# --------------------------------------------------------------------------------
# 13. TREASURE EFFECTS & SPECIAL FLOORS
# --------------------------------------------------------------------------------

def use_carnyx_of_doom(character, my_tower):
    """Kill all monsters in adjacent squares - has 3 charges"""
    # Find the carnyx in inventory to track charges
    carnyx = None
    for item in character.inventory.items:
        if item.name == "Carnyx of Doom":
            carnyx = item
            break
    
    if not carnyx:
        add_log(f"{COLOR_RED}Error: Carnyx not found!{COLOR_RESET}")
        return False
    
    # Initialize charges if not set
    if not hasattr(carnyx, 'charges') or carnyx.charges is None:
        carnyx.charges = 3
    
    add_log(f"{COLOR_RED}{COLOR_RESET}")
    add_log(f"{COLOR_RED}You blow the CARNYX OF DOOM!{COLOR_RESET}")
    add_log(f"{COLOR_RED}A deafening war horn echoes through the cavern!{COLOR_RESET}")
    add_log(f"{COLOR_RED}{COLOR_RESET}")

    current_floor = my_tower.floors[character.z]
    monsters_killed = 0

    # Check all 8 adjacent squares
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            if dy == 0 and dx == 0:
                continue

            target_y = character.y + dy
            target_x = character.x + dx

            if 0 <= target_y < current_floor.rows and 0 <= target_x < current_floor.cols:
                room = current_floor.grid[target_y][target_x]

                if room.room_type == 'M':
                    # Check if there's a monster here
                    coords = (target_x, target_y, character.z)
                    if coords in gs.encountered_monsters:
                        monster = gs.encountered_monsters[coords]
                        if monster.is_alive():
                            monster.health = 0
                            room.room_type = '.'
                            monsters_killed += 1
                            add_log(f"{COLOR_RED} The {monster.name} at ({target_x}, {target_y}) was obliterated by the sonic blast!{COLOR_RESET}")

    if monsters_killed > 0:
        add_log(f"{COLOR_YELLOW}The Carnyx killed {monsters_killed} monster(s)!{COLOR_RESET}")
        # Award XP for kills
        xp_gain = monsters_killed * 50
        character.gain_experience(xp_gain)
        add_log(f"{COLOR_GREEN}Gained {xp_gain} XP from the carnyx kills!{COLOR_RESET}")
    else:
        add_log(f"{COLOR_YELLOW}No monsters were in range of the blast.{COLOR_RESET}")

    # Decrement charges
    carnyx.charges -= 1
    
    if carnyx.charges > 0:
        add_log(f"{COLOR_PURPLE}The Carnyx has {carnyx.charges} blast(s) remaining.{COLOR_RESET}")
        return False  # Not consumed - still has charges
    else:
        add_log(f"{COLOR_GREY}The ancient horn cracks and crumbles to dust...{COLOR_RESET}")
        return True  # Consumed after final use


def use_rhyton_of_purity(character, my_tower):
    """Negate negative pool effects for next pool"""
    add_log(f"{COLOR_CYAN}{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}You drink from the RHYTON OF PURITY!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Pure, crystalline water fills you with divine protection!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}{COLOR_RESET}")

    # Grant temporary protection buff
    character.add_status_effect(
        effect_name='Purified',
        duration=10,
        effect_type='pool_protection',
        magnitude=0,
        description='Protected from negative pool effects'
    )

    add_log(f"{COLOR_GREEN}You are protected from negative pool effects for 10 turns!{COLOR_RESET}")
    add_log(f"{COLOR_GREEN}Any harmful pools you drink from will only have positive effects!{COLOR_RESET}")

    return False  # Not consumed (reusable!)


def use_hourglass_of_ages(character, my_tower):
    """Fully restore HP and MP, remove all status effects"""
    add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}You turn the HOURGLASS OF AGES!{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}Time reverses, undoing all harm!{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}{COLOR_RESET}")

    # Full restoration
    old_health = character.health
    old_mana = character.mana

    character.health = character.max_health
    character.mana = character.max_mana

    healed = character.health - old_health
    mana_restored = character.mana - old_mana

    # Remove ALL status effects (good and bad)
    effects_removed = list(character.status_effects.keys())
    character.status_effects.clear()

    add_log(f"{COLOR_GREEN}Restored {healed} HP and {mana_restored} MP!{COLOR_RESET}")
    if effects_removed:
        add_log(f"{COLOR_GREEN}Removed all status effects: {', '.join(effects_removed)}{COLOR_RESET}")

    add_log(f"{COLOR_YELLOW}The hourglass can be used 2 more times.{COLOR_RESET}")

    # Track uses (you'll need to add a 'uses_remaining' attribute)
    if not hasattr(character, 'hourglass_uses'):
        character.hourglass_uses = 2
    else:
        character.hourglass_uses -= 1

    if character.hourglass_uses <= 0:
        add_log(f"{COLOR_GREY}The hourglass shatters, its magic exhausted...{COLOR_RESET}")
        return True  # Consumed

    return False  # Still has uses


def use_mirror_of_truth(character, my_tower):
    """Reveal all rooms on current floor and show monster levels"""
    add_log(f"{COLOR_CYAN}{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}You gaze into the MIRROR OF TRUTH!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Reality itself becomes transparent!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}{COLOR_RESET}")

    current_floor = my_tower.floors[character.z]
    revealed = 0
    monsters_found = []

    # Reveal entire floor
    for r in range(current_floor.rows):
        for c in range(current_floor.cols):
            if not current_floor.grid[r][c].discovered:
                current_floor.grid[r][c].discovered = True
                revealed += 1

            # Check for monsters
            if current_floor.grid[r][c].room_type == 'M':
                coords = (c, r, character.z)
                if coords in gs.encountered_monsters:
                    monster = gs.encountered_monsters[coords]
                    if monster.is_alive():
                        monsters_found.append((c, r, monster.name, monster.level))

    add_log(f"{COLOR_GREEN}Revealed {revealed} rooms!{COLOR_RESET}")

    if monsters_found:
        add_log(f"{COLOR_YELLOW}Monsters detected:{COLOR_RESET}")
        for x, y, name, level in monsters_found:
            add_log(f"   {name} (Lvl {level}) at ({x}, {y})")

    return False  # Reusable


def use_chalice_of_plenty(character, my_tower):
    """Generate random valuable loot"""
    add_log(f"{COLOR_YELLOW}{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}You drink from the CHALICE OF PLENTY!{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}Golden light spills from the cup!{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}{COLOR_RESET}")

    # Generate random valuable rewards
    rewards = random.choice([
        'gold_major',
        'gold_massive',
        'potion_set',
        'scroll_set',
        'stat_boost'
    ])

    if rewards == 'gold_major':
        gold = random.randint(200, 500)
        character.gold += gold
        add_log(f"{COLOR_GREEN} {gold} gold pours from the chalice!{COLOR_RESET}")
        gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold
        check_achievements(character)

    elif rewards == 'gold_massive':
        gold = random.randint(500, 1000)
        character.gold += gold
        add_log(f"{COLOR_GREEN} {gold} gold floods from the chalice!{COLOR_RESET}")
        gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold
        check_achievements(character)

    elif rewards == 'potion_set':
        add_log(f"{COLOR_GREEN}Three potions materialize!{COLOR_RESET}")
        for _ in range(3):
            potion_choices = [p for p in POTION_TEMPLATES if p.level <= character.z + 2]
            if potion_choices:
                potion = _create_item_copy(random.choice(potion_choices))
                character.inventory.add_item(potion)

    elif rewards == 'scroll_set':
        add_log(f"{COLOR_GREEN}Two powerful scrolls appear!{COLOR_RESET}")
        for _ in range(2):
            scroll_choices = [s for s in SCROLL_TEMPLATES if s.level <= character.z + 1]
            if scroll_choices:
                scroll = _create_item_copy(random.choice(scroll_choices))
                character.inventory.add_item(scroll)

    elif rewards == 'stat_boost':
        stat = random.choice(['strength', 'dexterity', 'intelligence'])
        boost = random.randint(2, 4)
        old_val = getattr(character, stat)
        setattr(character, stat, old_val + boost)
        add_log(f"{COLOR_GREEN} {stat.capitalize()} increased by {boost}!{COLOR_RESET}")

    add_log(f"{COLOR_YELLOW}The chalice can be used 1 more time.{COLOR_RESET}")

    # Track uses
    if not hasattr(character, 'chalice_uses'):
        character.chalice_uses = 1
    else:
        character.chalice_uses -= 1

    if character.chalice_uses <= 0:
        add_log(f"{COLOR_GREY}The chalice cracks and vanishes...{COLOR_RESET}")
        return True  # Consumed

    return False  # Still has uses


def use_crown_of_kings(character, my_tower):
    """Massively boost all stats temporarily"""
    add_log(f"{COLOR_YELLOW}{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}You don the CROWN OF KINGS!{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}Divine authority surges through you!{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}{COLOR_RESET}")

    # Grant powerful temporary buffs
    character.add_status_effect(
        effect_name='Royal Power',
        duration=8,
        effect_type='attack_boost',
        magnitude=20,
        description='The power of ancient kings flows through you'
    )

    character.add_status_effect(
        effect_name='Royal Defense',
        duration=8,
        effect_type='defense_boost',
        magnitude=20,
        description='Protected by royal authority'
    )

    add_log(f"{COLOR_GREEN}+20 Attack and +20 Defense for 8 turns!{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}You feel like royalty!{COLOR_RESET}")

    return False  # Reusable


def use_merchants_bell(character, my_tower):
    """
    Alternative unique treasure: Summons a temporary merchant anywhere.
    Creates a temporary vendor at your current location.
    """
    add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE} YOU RING THE MERCHANT'S BELL! {COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}A mysterious traveling merchant appears!{COLOR_RESET}")

    # Create temporary vendor at player location
    current_floor = my_tower.floors[character.z]
    room = current_floor.grid[character.y][character.x]

    # Store old room type
    old_room_type = room.room_type

    # Temporarily convert to vendor
    room.room_type = 'V'
    room.properties['vendor_inventory'] = generate_vendor_inventory(character.z, room)
    room.properties['temporary_vendor'] = True
    room.properties['old_room_type'] = old_room_type

    add_log(f"{COLOR_GREEN}A merchant has set up shop at your location!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Interact with this room to trade. The merchant will vanish when you leave.{COLOR_RESET}")

    return False  # Not consumed (reusable)

# 
# UNIQUE TREASURE TEMPLATES
# 



def get_random_potion(floor_level):
    """Return a random potion appropriate for the floor level."""
    if floor_level >= 15:
        options = [
            Potion("Superior Healing Potion", "Restores 150 HP.", value=150, level=4, potion_type='healing', effect_magnitude=150),
            Potion("Greater Healing Potion", "Restores 100 HP.", value=100, level=2, potion_type='healing', effect_magnitude=100),
            Potion("Mana Potion", "Restores 40 MP.", value=80, level=3, potion_type='mana', effect_magnitude=40),
            Potion("Strength Brew", "Temporarily boosts Strength.", value=100, level=3, potion_type='buff', effect_magnitude=5, duration=5),
        ]
    elif floor_level >= 8:
        options = [
            Potion("Greater Healing Potion", "Restores 100 HP.", value=100, level=2, potion_type='healing', effect_magnitude=100),
            Potion("Healing Potion", "Restores 50 HP.", value=50, level=1, potion_type='healing', effect_magnitude=50),
            Potion("Mana Potion", "Restores 40 MP.", value=80, level=3, potion_type='mana', effect_magnitude=40),
        ]
    elif floor_level >= 3:
        options = [
            Potion("Healing Potion", "Restores 50 HP.", value=50, level=1, potion_type='healing', effect_magnitude=50),
            Potion("Minor Healing Potion", "Restores 25 HP.", value=25, level=0, potion_type='healing', effect_magnitude=25),
            Potion("Mana Potion", "Restores 40 MP.", value=80, level=3, potion_type='mana', effect_magnitude=40),
        ]
    else:
        options = [
            Potion("Minor Healing Potion", "Restores 25 HP.", value=25, level=0, potion_type='healing', effect_magnitude=25),
            Potion("Healing Potion", "Restores 50 HP.", value=50, level=1, potion_type='healing', effect_magnitude=50),
        ]
    return random.choice(options)


def get_random_food(floor_level=0):
    """Return a random food item appropriate for the floor level."""
    if floor_level >= 10:
        options = [
            Food("Iron Rations", "Military-grade rations.", value=30, level=3, nutrition=70),
            Food("Travelers Bread", "Dense nourishing loaf.", value=20, level=2, nutrition=50),
            Food("Salted Jerky", "Dried meat. Salty and chewy.", value=15, level=1, nutrition=35),
        ]
    elif floor_level >= 5:
        options = [
            Food("Travelers Bread", "Dense nourishing loaf.", value=20, level=2, nutrition=50),
            Food("Salted Jerky", "Dried meat. Salty and chewy.", value=15, level=1, nutrition=35),
            Food("Cheese Wedge", "A wedge of pungent cave cheese.", value=12, level=1, nutrition=30),
        ]
    else:
        options = [
            Food("Rations", "Standard travel rations.", value=10, level=0, nutrition=40),
            Food("Hardtack", "Dense dry biscuit.", value=5, level=0, nutrition=25),
            Food("Dried Mushrooms", "Cave mushrooms, dried.", value=7, level=0, nutrition=20),
        ]
    return random.choice(options)


def get_random_treasure(floor_level, allow_unique=False):
    """
    Get a random treasure appropriate for the floor level.
    Handles unique treasure spawning restrictions.
    """

    # Determine treasure pool based on level
    min_level = max(0, floor_level - 1)
    max_level = floor_level + 2

    # Start with minor treasures
    available_treasures = [
        t for t in ENHANCED_MINOR_TREASURES
        if min_level <= t.level <= max_level
    ]

    # 10% chance for unique treasure on floors 3+
    if allow_unique and floor_level >= 3 and random.random() < 0.10:
        # Get unique treasures that haven't spawned yet
        available_uniques = [
            t for t in UNIQUE_TREASURE_TEMPLATES
            if t.name not in gs.unique_treasures_spawned
            and t.level <= floor_level + 3
        ]

        if available_uniques:
            chosen = random.choice(available_uniques)
            gs.unique_treasures_spawned.add(chosen.name)
            add_log(f"{COLOR_YELLOW} A LEGENDARY TREASURE has been found! {COLOR_RESET}")
            return _create_item_copy(chosen)

    # Otherwise return minor treasure
    if available_treasures:
        return _create_item_copy(random.choice(available_treasures))

    # Fallback to gold
    return Treasure(
        name="Gold Coins",
        description="A handful of gold coins.",
        gold_value=20 * (floor_level + 1),
        value=20 * (floor_level + 1),
        level=floor_level,
        treasure_type='gold'
    )


# 
# PASSIVE TREASURE EFFECTS (Process each turn)
# 

def process_passive_treasures(character):
    """
    Process passive treasure effects each turn.
    Call this in the main game loop or after each action.
    """
    for item in character.inventory.items:
        if isinstance(item, Treasure) and item.treasure_type == 'passive' and item.is_equipped:

            # Ring of Regeneration - heal 3 HP per turn
            if item.name == "Ring of Regeneration":
                if character.health < character.max_health:
                    character.health = min(character.max_health, character.health + 3)
                    add_log(f"{COLOR_GREEN}Ring of Regeneration: +3 HP{COLOR_RESET}")

            # Amulet of True Sight (handled in combat/exploration logic)
            elif item.name == "Amulet of True Sight":
                # This is checked in other parts of code
                pass

            # Boots of Haste - immunity to web/slow
            elif item.name == "Boots of Haste":
                if 'Web' in character.status_effects:
                    character.remove_status_effect('Web')
                    add_log(f"{COLOR_GREEN}Boots of Haste: Web broken!{COLOR_RESET}")
                if 'Slow' in character.status_effects:
                    character.remove_status_effect('Slow')
                    add_log(f"{COLOR_GREEN}Boots of Haste: Slow negated!{COLOR_RESET}")

            # Cloak of Shadows (handled in combat logic)
            elif item.name == "Cloak of Shadows":
                pass
            
            # Skull of the Mage - restore 2 mana per turn
            elif item.name == "Skull of the Mage":
                if character.mana < character.max_mana:
                    character.mana = min(character.max_mana, character.mana + 2)
                    add_log(f"{COLOR_CYAN}Skull of the Mage: +2 Mana{COLOR_RESET}")
            
            # Heartstone Pendant - restore 2 HP per turn
            elif item.name == "Heartstone Pendant":
                if character.health < character.max_health:
                    character.health = min(character.max_health, character.health + 2)
                    add_log(f"{COLOR_GREEN}Heartstone Pendant: +2 HP{COLOR_RESET}")


def check_pool_protection(character):
    """
    Check if player has Rhyton of Purity protection active.
    Call this before applying negative pool effects.
    """
    # Check for Purified status effect
    if 'Purified' in character.status_effects:
        return True

    # Also check if Rhyton is in inventory (backup check)
    for item in character.inventory.items:
        if isinstance(item, Treasure) and item.name == "Rhyton of Purity":
            return False  # They have it but haven't used it

    return False


def has_true_sight(character):
    """Check if player has True Sight active"""
    for item in character.inventory.items:
        if isinstance(item, Treasure) and item.name == "Amulet of True Sight" and item.is_equipped:
            return True
    return False


def process_haunted_floor(character, my_tower):
    """
    Process haunted floor effects when player moves.
    Decrements haunted timer and may trigger spirit ambushes.
    
    Called from move_player after successful movement.
    """
    
    current_floor_num = character.z
    
    # Check if current floor is haunted
    if current_floor_num not in gs.haunted_floors:
        return

    turns_remaining = gs.haunted_floors[current_floor_num]
    
    # Decrement haunted counter
    turns_remaining -= 1
    
    if turns_remaining <= 0:
        # Haunt ends
        del gs.haunted_floors[current_floor_num]
        add_log(f"{COLOR_CYAN}The oppressive presence lifts...{COLOR_RESET}")
        add_log(f"{COLOR_GREEN}The spirits have returned to their rest.{COLOR_RESET}")
        return
    
    # Update remaining turns
    gs.haunted_floors[current_floor_num] = turns_remaining
    
    # 25% chance of spirit ambush on each move while haunted
    if random.random() < 0.25:
        # Check if we're not already in combat or in a special room
        current_floor = my_tower.floors[character.z]
        room = current_floor.grid[character.y][character.x]
        
        # Only ambush on empty floor tiles
        if room.room_type == '.':
            _spawn_spirit_ambush(character, my_tower)
    else:
        # Occasionally remind player the floor is haunted
        if random.random() < 0.3:
            haunted_messages = [
                f"{COLOR_PURPLE}Cold whispers echo in the darkness...{COLOR_RESET}",
                f"{COLOR_GREY}You feel spectral eyes watching you...{COLOR_RESET}",
                f"{COLOR_PURPLE}A chill runs down your spine...{COLOR_RESET}",
                f"{COLOR_GREY}Shadows seem to move at the edge of your vision...{COLOR_RESET}"
            ]
            add_log(random.choice(haunted_messages))


def _spawn_spirit_ambush(character, my_tower):
    """Spawn a spirit enemy for haunted floor ambush."""
    
    coords = (character.x, character.y, character.z)
    floor_level = character.z
    
    add_log("")
    add_log(f"{COLOR_RED}==============================={COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}SPIRIT AMBUSH!{COLOR_RESET}")
    add_log(f"{COLOR_RED}==============================={COLOR_RESET}")
    add_log("")
    add_log(f"{COLOR_PURPLE}A restless spirit materializes before you!{COLOR_RESET}")
    
    # Create spirit enemy - weaker than tomb guardians but still dangerous
    spirit_types = [
        ("Restless Spirit", ['Holy', 'Light'], ['Darkness', 'Physical']),
        ("Wandering Ghost", ['Holy', 'Fire'], ['Darkness', 'Ice']),
        ("Lost Soul", ['Holy', 'Light'], ['Darkness', 'Psionic']),
        ("Poltergeist", ['Holy'], ['Darkness', 'Physical', 'Ice'])
    ]
    s_name, s_weak, s_strong = random.choice(spirit_types)
    
    spirit = Monster(
        name=s_name.upper(),
        health=int(40 + floor_level * 8),
        attack=int(8 + floor_level),
        defense=int(5 + floor_level * 0.5),
        elemental_weakness=s_weak,
        elemental_strength=s_strong,
        level=floor_level + 1,
        attack_element='Darkness',
        flavor_text=f"{COLOR_PURPLE}A spirit released from the disturbed tomb!{COLOR_RESET}",
        victory_text=f"{COLOR_GREEN}The spirit dissipates with a wailing cry!{COLOR_RESET}"
    )
    spirit.properties['is_haunted_spirit'] = True
    
    # Store and start combat
    gs.encountered_monsters[coords] = spirit
    gs.active_monster = spirit
    
    gs.prompt_cntl = "combat_mode"
    process_combat_action(character, my_tower, "init")


def process_ephemeral_gardens(character, my_tower):
    """
    Process ephemeral (Fey) garden spawning and despawning.
    Called from move_player after successful movement.
    
    Fey Gardens:
    - Spawn rarely (5% chance per move on floors 5+)
    - In PLAYTEST mode, spawn on every floor 5+ if not already present
    - Only spawn on floors 5+ (deeper = better ingredients)
    - Appear for 2d6 turns then vanish
    - Contain high-level rare ingredients
    - Only one can exist per floor at a time
    """
    
    current_floor_num = character.z
    current_floor = my_tower.floors[current_floor_num]
    
    # Process existing ephemeral garden on this floor (if any)
    if current_floor_num in gs.ephemeral_gardens:
        garden_data = gs.ephemeral_gardens[current_floor_num]
        garden_data['turns_remaining'] -= 1
        
        # Check if garden should despawn
        if garden_data['turns_remaining'] <= 0:
            gx, gy = garden_data['x'], garden_data['y']
            original_type = garden_data.get('original_room_type', '.')
            
            # Only revert if room is still a fey garden (player might be standing there)
            room = current_floor.grid[gy][gx]
            if room.properties.get('is_fey_garden'):
                room.room_type = original_type
                room.properties['is_fey_garden'] = False
                
                # Notify player if they're nearby or on the same floor
                add_log(f"{COLOR_PURPLE}A shimmer of fey magic fades in the distance...{COLOR_RESET}")
                add_log(f"{COLOR_GREY}The Fey Garden has vanished back to the realm between worlds.{COLOR_RESET}")
            
            del gs.ephemeral_gardens[current_floor_num]
        else:
            # Occasionally remind player a fey garden exists
            if random.random() < 0.15:
                add_log(f"{COLOR_CYAN}You sense fey magic nearby... ({garden_data['turns_remaining']} turns remaining){COLOR_RESET}")
    
    # Try to spawn a new ephemeral garden (only on floors 5+, not already present, not already harvested)
    if current_floor_num >= 5 and current_floor_num not in gs.ephemeral_gardens and current_floor_num not in gs.harvested_fey_floors:
        # In PLAYTEST mode, always spawn; otherwise 3% chance per move
        if gs.PLAYTEST or random.random() < 0.03:
            _spawn_fey_garden(character, my_tower)


def _spawn_fey_garden(character, my_tower):
    """Spawn a Fey Garden in a random empty room on the current floor."""
    
    current_floor_num = character.z
    current_floor = my_tower.floors[current_floor_num]
    
    # Find all empty floor tiles that aren't the player's current position
    empty_rooms = []
    for r in range(current_floor.rows):
        for c in range(current_floor.cols):
            room = current_floor.grid[r][c]
            # Only spawn on empty floor tiles, not on player's position
            if room.room_type == '.' and (c != character.x or r != character.y):
                empty_rooms.append((c, r))
    
    if not empty_rooms:
        return  # No valid spawn location
    
    # Pick a random empty room
    gx, gy = random.choice(empty_rooms)
    room = current_floor.grid[gy][gx]
    
    # Store original room type and convert to garden
    original_type = room.room_type
    room.room_type = 'G'  # Use garden room type
    room.properties['is_fey_garden'] = True
    room.properties['fey_garden_floor_level'] = current_floor_num
    
    # Duration: 2d6 turns (2-12 turns)
    duration = random.randint(1, 6) + random.randint(1, 6)
    
    # Store garden data
    gs.ephemeral_gardens[current_floor_num] = {
        'x': gx,
        'y': gy,
        'turns_remaining': duration,
        'original_room_type': original_type
    }
    
    # Announce the garden
    add_log("")
    add_log(f"{COLOR_PURPLE}==============================={COLOR_RESET}")
    add_log(f"{COLOR_CYAN}FEY GARDEN APPEARED!{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}==============================={COLOR_RESET}")
    add_log("")
    add_log(f"{COLOR_GREEN}A shimmer of otherworldly magic fills the air!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}A Fey Garden has materialized somewhere on this floor!{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}It will vanish in {duration} turns - find it quickly!{COLOR_RESET}")
    add_log("")


def has_dodge_cloak(character):
    """Check if player has Cloak of Shadows equipped"""
    for item in character.inventory.items:
        if isinstance(item, Treasure) and item.name == "Cloak of Shadows" and item.is_equipped:
            return True
    return False


def has_accessory(character, name):
    """Generic check: is a named accessory equipped?"""
    for item in character.inventory.items:
        if isinstance(item, Treasure) and item.name == name and item.is_equipped:
            return True
    return False


def has_poison_immunity(character):
    """Venom Ward Amulet grants permanent poison immunity."""
    return has_accessory(character, "Venom Ward Amulet")


def has_confusion_immunity(character):
    """Psychic Shield Circlet grants permanent confusion immunity."""
    return has_accessory(character, "Psychic Shield Circlet")


def has_fire_resistance(character):
    """Drake Cloak grants 60% fire damage reduction."""
    return has_accessory(character, "Drake Cloak")


def has_hunter_cloak(character):
    """Cloak of the Hunter: 15% chance attacks bypass enemy defense."""
    return has_accessory(character, "Cloak of the Hunter")


def get_holy_brand_bonus(character):
    """Holy Brand Ring adds +8 Holy damage to every attack."""
    return 8 if has_accessory(character, "Holy Brand Ring") else 0

# Define item templates for various types


def get_equipment_display_name(item):
    """
    Generate a dynamic display name for weapons and armor based on:
    - Upgrade level (tier prefix)
    - Elemental strengths (suffix)
    
    Examples:
    - "Dagger" (base, no elements)
    - "Honed Iron Sword" (+1 upgrade)
    - "Masterwork Greatsword of Flames" (+6, Fire element)
    - "Legendary Mithril Sword of Twilight" (+8, Light+Dark elements)
    """
    if not isinstance(item, (Weapon, Armor)):
        return item.name
    
    base_name = item.name
    
    # Get tier prefix based on upgrade level
    if isinstance(item, Weapon):
        prefix = WEAPON_TIER_PREFIXES.get(item.upgrade_level, "Ascended")
    else:
        prefix = ARMOR_TIER_PREFIXES.get(item.upgrade_level, "Ascended")
    
    # Get elemental suffix
    elements = [e for e in item.elemental_strength if e != "None"]
    suffix = ""
    
    if len(elements) >= 2:
        # Check for special multi-element combinations
        element_set = frozenset(elements[:2])  # Use first two elements
        suffix = MULTI_ELEMENT_SUFFIXES.get(element_set, "")
        if not suffix:
            # Default: use first element's suffix
            suffix = ELEMENTAL_SUFFIXES.get(elements[0], "")
    elif len(elements) == 1:
        suffix = ELEMENTAL_SUFFIXES.get(elements[0], "")
    
    # Build the full name
    parts = []
    if prefix:
        parts.append(prefix)
    parts.append(base_name)
    
    full_name = " ".join(parts)
    if suffix:
        full_name += " " + suffix
    
    return full_name

def create_random_enhanced_weapon(floor_level):
    """
    Create a random weapon with possible upgrades and elemental properties
    based on floor level. Higher floors = better chances for upgrades/elements.
    """
    import random
    
    # Filter weapons appropriate for this floor
    min_level = max(0, floor_level - 3)
    max_level = floor_level + 2
    available = [w for w in WEAPON_TEMPLATES if min_level <= w.level <= max_level]
    
    if not available:
        available = WEAPON_TEMPLATES
    
    # Pick a base weapon
    base = random.choice(available)
    
    # Create a copy
    weapon = Weapon(
        name=base.name,
        description=base.description,
        attack_bonus=base._base_attack_bonus,
        value=base.value,
        level=base.level,
        upgrade_level=0,
        elemental_strength=["None"],
        upgrade_limit=base.upgrade_limit
    )
    
    # Chance for upgrades (increases with floor level).
    # Starts near-zero in early floors so upgraded gear is scarce until mid-game.
    upgrade_chance = min(0.50, max(0.0, -0.05 + (floor_level * 0.035)))
    if random.random() < upgrade_chance:
        # Number of upgrades scales with floor
        max_upgrades = min(15, 1 + floor_level // 3)
        weapon.upgrade_level = random.randint(1, max_upgrades)
    
    # Chance for elemental properties
    element_chance = min(0.4, 0.05 + (floor_level * 0.025))
    if random.random() < element_chance:
        elements = ["Fire", "Ice", "Lightning", "Poison", "Dark", "Light"]
        weapon.elemental_strength = [random.choice(elements)]
        
        # Small chance for second element on high floors
        if floor_level >= 10 and random.random() < 0.2:
            second = random.choice([e for e in elements if e not in weapon.elemental_strength])
            weapon.elemental_strength.append(second)
    
    return weapon

def create_random_enhanced_armor(floor_level):
    """
    Create a random armor with possible upgrades and elemental properties
    based on floor level. Higher floors = better chances for upgrades/elements.
    """
    import random
    
    # Filter armor appropriate for this floor
    min_level = max(0, floor_level - 3)
    max_level = floor_level + 2
    available = [a for a in ARMOR_TEMPLATES if min_level <= a.level <= max_level]
    
    if not available:
        available = ARMOR_TEMPLATES
    
    # Pick a base armor
    base = random.choice(available)
    
    # Create a copy
    armor = Armor(
        name=base.name,
        description=base.description,
        defense_bonus=base._base_defense_bonus,
        value=base.value,
        level=base.level,
        upgrade_level=0,
        elemental_strength=["None"],
        upgrade_limit=base.upgrade_limit
    )
    
    # Chance for upgrades (increases with floor level).
    # Starts near-zero in early floors so upgraded gear is scarce until mid-game.
    upgrade_chance = min(0.50, max(0.0, -0.05 + (floor_level * 0.035)))
    if random.random() < upgrade_chance:
        # Number of upgrades scales with floor - lower cap than weapons to keep monster damage meaningful
        max_upgrades = min(10, 1 + floor_level // 4)
        armor.upgrade_level = random.randint(1, max_upgrades)
    
    # Chance for elemental resistance
    element_chance = min(0.4, 0.05 + (floor_level * 0.025))
    if random.random() < element_chance:
        elements = ["Fire", "Ice", "Lightning", "Poison", "Dark", "Light"]
        armor.elemental_strength = [random.choice(elements)]
        
        # Small chance for second element on high floors
        if floor_level >= 10 and random.random() < 0.2:
            second = random.choice([e for e in elements if e not in armor.elemental_strength])
            armor.elemental_strength.append(second)
    
    return armor



# --------------------------------------------------------------------------------
# 15. CRAFTING SYSTEM
# --------------------------------------------------------------------------------

def get_available_recipes(player_character):
    """Return list of recipes player can craft based on inventory"""
    available = []
    inventory_items = {}

    # Count ingredients in inventory
    for item in player_character.inventory.items:
        if isinstance(item, Ingredient):
            inventory_items[item.name] = inventory_items.get(item.name, 0) + 1

    # Count rations in inventory
    ration_count = 0
    for item in player_character.inventory.items:
        if isinstance(item, Food) and item.name == "Rations":
            ration_count += getattr(item, 'count', 1)

    # Count cooked, non-rotten monster meat in inventory (for sausage recipes)
    cooked_meat_count = 0
    for item in player_character.inventory.items:
        if isinstance(item, Meat) and item.is_cooked and not getattr(item, 'is_rotten', False):
            cooked_meat_count += getattr(item, 'count', 1)

    # Check if player owns a Curing Kit (unlocks sausage crafting)
    has_curing_kit = any(isinstance(item, CuringKit) for item in player_character.inventory.items)

    # Check each potion recipe
    for recipe_name, recipe_data in POTION_RECIPES.items():
        can_craft = True
        missing = []
        for ing_name, ing_count in recipe_data['ingredients']:
            if inventory_items.get(ing_name, 0) < ing_count:
                can_craft = False
                missing.append((ing_name, ing_count - inventory_items.get(ing_name, 0)))

        if can_craft:
            available.append((recipe_name, recipe_data, True, []))
        else:
            # Include recipes player is close to crafting
            if len(missing) <= 2:  # Show if only missing 1-2 ingredient types
                available.append((recipe_name, recipe_data, False, missing))

    # Check lembas recipes (elf only)
    if getattr(player_character, 'race', '').lower() == 'elf':
        for recipe_name, recipe_data in LEMBAS_RECIPES.items():
            can_craft = True
            missing = []
            for ing_name, ing_count in recipe_data['ingredients']:
                if inventory_items.get(ing_name, 0) < ing_count:
                    can_craft = False
                    missing.append((ing_name, ing_count - inventory_items.get(ing_name, 0)))
            # Check ration cost
            ration_needed = recipe_data.get('ration_cost', 0)
            if ration_count < ration_needed:
                can_craft = False
                missing.append(('Rations', ration_needed - ration_count))

            if can_craft:
                available.append((recipe_name, recipe_data, True, []))
            else:
                if len(missing) <= 2:
                    available.append((recipe_name, recipe_data, False, missing))

    # Check sausage recipes (requires Curing Kit)
    if has_curing_kit:
        for recipe_name, recipe_data in SAUSAGE_RECIPES.items():
            can_craft = True
            missing = []
            for ing_name, ing_count in recipe_data['ingredients']:
                if inventory_items.get(ing_name, 0) < ing_count:
                    can_craft = False
                    missing.append((ing_name, ing_count - inventory_items.get(ing_name, 0)))
            # Check cooked meat cost
            meat_needed = recipe_data.get('meat_cost', 1)
            if cooked_meat_count < meat_needed:
                can_craft = False
                missing.append(('Cooked Meat', meat_needed - cooked_meat_count))

            if can_craft:
                available.append((recipe_name, recipe_data, True, []))
            else:
                if len(missing) <= 2:
                    available.append((recipe_name, recipe_data, False, missing))

    return available

def craft_potion(player_character, recipe_name):
    """Craft a potion, lembas, or sausage, removing ingredients and adding result"""
    # Check all recipe dicts
    if recipe_name in POTION_RECIPES:
        recipe = POTION_RECIPES[recipe_name]
    elif recipe_name in LEMBAS_RECIPES:
        recipe = LEMBAS_RECIPES[recipe_name]
    elif recipe_name in SAUSAGE_RECIPES:
        recipe = SAUSAGE_RECIPES[recipe_name]
    else:
        add_log(f"{COLOR_RED}Unknown recipe: {recipe_name}{COLOR_RESET}")
        return

    # Remove herb/ingredient components from inventory
    for ing_name, ing_count in recipe['ingredients']:
        removed = 0
        for item in list(player_character.inventory.items):
            if isinstance(item, Ingredient) and item.name == ing_name:
                player_character.inventory.items.remove(item)
                removed += 1
                if removed >= ing_count:
                    break

    # Remove rations if recipe requires them (lembas)
    ration_cost = recipe.get('ration_cost', 0)
    if ration_cost > 0:
        for item in player_character.inventory.items:
            if isinstance(item, Food) and item.name == "Rations":
                count = getattr(item, 'count', 1)
                if count > ration_cost:
                    item.count -= ration_cost
                else:
                    player_character.inventory.items.remove(item)
                break

    # Remove cooked meat if recipe requires it (sausage)
    # Tag the crafted sausage with the monster source of the consumed meat.
    meat_cost = recipe.get('meat_cost', 0)
    consumed_meat_source = None
    if meat_cost > 0:
        remaining = meat_cost
        for item in list(player_character.inventory.items):
            if remaining <= 0:
                break
            if isinstance(item, Meat) and item.is_cooked and not getattr(item, 'is_rotten', False):
                count = getattr(item, 'count', 1)
                if consumed_meat_source is None:
                    consumed_meat_source = getattr(item, 'monster_name', 'Unknown')
                if count > remaining:
                    item.count -= remaining
                    remaining = 0
                else:
                    player_character.inventory.items.remove(item)
                    remaining -= count

    # Add crafted item
    new_item = recipe['result']()
    # If it's a sausage, attribute the monster source in the name and description
    if isinstance(new_item, Sausage) and consumed_meat_source:
        style = new_item.sausage_style
        new_item.monster_source = consumed_meat_source
        new_item.name = f"{consumed_meat_source} {style}"
        new_item.description = f"A hand-stuffed {style.lower()} made from cured {consumed_meat_source} meat. {new_item.description}"
    player_character.inventory.add_item(new_item)
    add_log(f"{COLOR_GREEN}* You crafted: {new_item.name}! *{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}{new_item.description}{COLOR_RESET}")

    # Update stats
    gs.game_stats['potions_crafted'] = gs.game_stats.get('potions_crafted', 0) + 1
    check_achievements(player_character)

def process_crafting_action(player_character, my_tower, cmd):
    """Handle potion crafting menu"""
    
    if cmd == "init":
        # Display is now handled in render(), just return
        return
    
    if cmd == 'x':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
        return
    
    # Try to craft a recipe
    try:
        recipe_num = int(cmd) - 1
        available_recipes = get_available_recipes(player_character)
        craftable = [r for r in available_recipes if r[2]]
        
        if 0 <= recipe_num < len(craftable):
            recipe_name = craftable[recipe_num][0]
            craft_potion(player_character, recipe_name)
            # Stay in crafting mode to show updated recipes
            gs.prompt_cntl = "crafting_mode"
        else:
            add_log(f"{COLOR_RED}Invalid recipe number.{COLOR_RESET}")
    except ValueError:
        if cmd != "init":
            add_log(f"{COLOR_RED}Enter a recipe number or 'x' to exit.{COLOR_RESET}")



def handle_inventory_menu(player_character, my_tower, cmd):

    # Check if we're in combat
    in_combat = gs.active_monster and gs.active_monster.is_alive()

    if cmd == "init":
        # Commands now shown in HTML and placeholder, not log
        return

    # Clear inventory filter when navigating away from inventory
    if cmd in ('s', 'j', 'c', 'm', 'a', 'x', 'g', 'q'):
        gs.inventory_filter = None

    # Block non-combat actions during combat (but allow journal, achievements, stats)
    if in_combat:
        if cmd in ['c', 'm', 'g']:
            add_log(f"{COLOR_YELLOW}You can't do that during combat!{COLOR_RESET}")
            return
        if cmd.startswith('e') and not cmd.startswith('eat'):
            add_log(f"{COLOR_YELLOW}You can't equip items during combat!{COLOR_RESET}")
            return

    if cmd == 's':
        gs.prompt_cntl = "character_stats_mode"
        # Commands now shown in HTML and placeholder
        return

    if cmd == 'j':
        gs.prompt_cntl = "journal_mode"
        process_journal_action(player_character, my_tower, "init")
        return
    
    if cmd == 'c':
        gs.prompt_cntl = "crafting_mode"
        process_crafting_action(player_character, my_tower, "init")
        return

    if cmd == 'm':
        # Only allow spell memorization if player can cast spells
        if not can_cast_spells(player_character):
            add_log(f"{COLOR_YELLOW}You cannot use magic. (Requires Intelligence > 15){COLOR_RESET}")
            return
        gs.prompt_cntl = "spell_memorization_mode"
        process_spell_memorization_action(player_character, my_tower, "init")
        return

    if cmd == 'a':
        gs.prompt_cntl = "achievements_mode"
        #process_achievements_action(player_character, my_tower, "init")
        return

    if cmd == 'x' or (cmd == 'q' and not in_combat):
        # Check if we're in combat - return to combat mode, not game_loop
        if in_combat:
            gs.prompt_cntl = "combat_mode"
            add_log("Returning to combat...")
        else:
            gs.prompt_cntl = "game_loop"
            add_log("Inventory closed.")
            _trigger_room_interaction(player_character, my_tower)
        return

    if cmd == 'g':
        # Don't allow saving during combat
        if in_combat:
            add_log(f"{COLOR_YELLOW}You cannot save during combat!{COLOR_RESET}")
            return
        gs.prompt_cntl = "save_load_mode"
        process_save_load_action(player_character, my_tower, "init")
        return

    # Use/Equip commands - work with sorted inventory
    # In combat, filter to only usable items (Potions, Scrolls)
    sorted_items = get_sorted_inventory(player_character.inventory)
    if in_combat:
        # Only show combat-usable items: all Potions, Food, Meat, and specific scroll types
        combat_scroll_types = ['spell_scroll', 'protection', 'restoration']
        combat_usable_items = []
        for item in sorted_items:
            if isinstance(item, Potion):
                combat_usable_items.append(item)
            elif isinstance(item, (Food, Meat)):
                combat_usable_items.append(item)
            elif isinstance(item, Scroll) and item.scroll_type in combat_scroll_types:
                combat_usable_items.append(item)
        working_items = combat_usable_items
    else:
        working_items = sorted_items

    # --- Back button: clear filter and return to main inventory view ---
    if cmd == 'b':
        gs.inventory_filter = None
        return

    # --- Bare command toggles (set filter, refresh display) ---
    if cmd == 'u':
        gs.inventory_filter = 'use' if gs.inventory_filter != 'use' else None
        return

    if cmd == 'e':
        gs.inventory_filter = 'equip' if gs.inventory_filter != 'equip' else None
        return

    if cmd == 'eat':
        gs.inventory_filter = 'eat' if gs.inventory_filter != 'eat' else None
        return

    # Apply active inventory filter to narrow working_items for numbered commands
    if gs.inventory_filter == 'use':
        working_items = [i for i in working_items if isinstance(i, (Potion, Scroll, Flare, Lantern, LanternFuel, Treasure, Towel, CookingKit))]
    elif gs.inventory_filter == 'equip':
        working_items = [i for i in working_items if isinstance(i, (Weapon, Armor, Towel)) or (isinstance(i, Treasure) and i.treasure_type == 'passive')]
    elif gs.inventory_filter == 'eat':
        working_items = [i for i in working_items if isinstance(i, (Food, Meat))]

    # When a filter is active and user types just a number, route to the appropriate action
    if gs.inventory_filter and cmd.isdigit():
        if gs.inventory_filter == 'use':
            cmd = 'u' + cmd
        elif gs.inventory_filter == 'equip':
            cmd = 'e' + cmd
        elif gs.inventory_filter == 'eat':
            cmd = 'eat' + cmd

    if cmd.startswith('u'):
        try:
            # Extract number - skip 'u' and optional space
            num_str = cmd[1:].strip()
            item_number = int(num_str) - 1  # Convert to 0-indexed
            gs.inventory_filter = None  # Clear filter after selecting item

            if 0 <= item_number < len(working_items):
                item_to_use = working_items[item_number]

                # Use the item
                if isinstance(item_to_use, Potion):
                    consumed = item_to_use.use(player_character)
                    if consumed:
                        # Handle stack: decrement count or remove if last one
                        if getattr(item_to_use, 'count', 1) > 1:
                            item_to_use.count -= 1
                            add_log(f"{COLOR_GREY}({item_to_use.count} remaining){COLOR_RESET}")
                        else:
                            player_character.inventory.remove_item(item_to_use.name)
                    gs.prompt_cntl = "inventory"
                    handle_inventory_menu(player_character, my_tower, "init")

                elif isinstance(item_to_use, Scroll):
                    if item_to_use.scroll_type == 'upgrade':
                        gs.prompt_cntl = "upgrade_scroll_mode"
                        gs.active_scroll_item = item_to_use
                        process_upgrade_scroll_action(player_character, my_tower, "init")
                    elif item_to_use.scroll_type == 'foresight':
                        consumed = item_to_use.use(player_character, my_tower)
                        if not consumed:
                            # Foresight scroll changes prompt mode
                            pass
                    else:
                        consumed = item_to_use.use(player_character, my_tower)
                        if consumed:
                            # Handle stack: decrement count or remove if last one
                            if getattr(item_to_use, 'count', 1) > 1:
                                item_to_use.count -= 1
                                add_log(f"{COLOR_GREY}({item_to_use.count} remaining){COLOR_RESET}")
                            else:
                                player_character.inventory.remove_item(item_to_use.name)
                        gs.prompt_cntl = "inventory"
                        handle_inventory_menu(player_character, my_tower, "init")

                elif isinstance(item_to_use, Flare):
                    gs.prompt_cntl = "flare_direction_mode"
                    gs.active_flare_item = item_to_use
                    add_log("Choose a direction to throw the flare (n/s/e/w) or 'c' to cancel:")

                elif isinstance(item_to_use, Lantern):
                    consumed = item_to_use.use(player_character, my_tower)
                    gs.prompt_cntl = "inventory"
                    handle_inventory_menu(player_character, my_tower, "init")

                elif isinstance(item_to_use, LanternFuel):
                    consumed = item_to_use.use(player_character)
                    if consumed:
                        # Handle stack: decrement count or remove if last one
                        if getattr(item_to_use, 'count', 1) > 1:
                            item_to_use.count -= 1
                            add_log(f"{COLOR_GREY}({item_to_use.count} remaining){COLOR_RESET}")
                        else:
                            player_character.inventory.remove_item(item_to_use.name)
                    gs.prompt_cntl = "inventory"
                    handle_inventory_menu(player_character, my_tower, "init")

                elif isinstance(item_to_use, Treasure):
                    # Store prompt_cntl before use in case use_effect changes it
                    prompt_before = gs.prompt_cntl
                    consumed = item_to_use.use(player_character, my_tower)
                    if consumed:
                        player_character.inventory.remove_item(item_to_use.name)
                    # Only return to inventory if the use_effect didn't change the mode
                    if gs.prompt_cntl == prompt_before:
                        gs.prompt_cntl = "inventory"
                        handle_inventory_menu(player_character, my_tower, "init")

                elif isinstance(item_to_use, Towel):
                    # Towel use sets prompt_cntl to towel_action_mode
                    item_to_use.use(player_character, my_tower)
                    # Don't reset prompt_cntl - towel.use() sets it to towel_action_mode

                elif isinstance(item_to_use, (Food, Meat)):
                    add_log(f"{COLOR_YELLOW}Use 'eat' to consume food items.{COLOR_RESET}")
                    gs.prompt_cntl = "inventory"
                    handle_inventory_menu(player_character, my_tower, "init")

                elif isinstance(item_to_use, CookingKit):
                    item_to_use.use(player_character, my_tower)  # Not consumed
                    gs.prompt_cntl = "inventory"
                    handle_inventory_menu(player_character, my_tower, "init")

                elif type(item_to_use).__name__ == 'Towel' or 'Towel' in item_to_use.name:
                    # Fallback for Towel - in case isinstance fails
                    add_log(f"{COLOR_CYAN}What do you want to do with the towel?{COLOR_RESET}")
                    add_log(f"  1. Wear it over your face (blind yourself)")
                    add_log(f"  2. Wipe your face (cure face-based blindness)")
                    add_log(f"  3. Wipe your hands (cure slippery hands)")
                    add_log(f"  4. Cancel")
                    gs.prompt_cntl = "towel_action_mode"
                    gs.active_towel_item = item_to_use

                else:
                    add_log(f"{COLOR_YELLOW}You cannot use {item_to_use.name}.{COLOR_RESET}")
                    gs.prompt_cntl = "inventory"
                    handle_inventory_menu(player_character, my_tower, "init")
            else:
                add_log(f"{COLOR_YELLOW}Invalid item number.{COLOR_RESET}")

        except (ValueError, IndexError):
            add_log(f"{COLOR_YELLOW}Invalid use command. Format: u [number]{COLOR_RESET}")

    elif cmd.startswith('eat') and len(cmd) > 3:
        # Eat command: eat# consumes food/meat items
        try:
            num_str = cmd[3:].strip()
            item_number = int(num_str) - 1
            edible_items = [i for i in working_items if isinstance(i, (Food, Meat))]
            if 0 <= item_number < len(edible_items):
                item_to_eat = edible_items[item_number]
                consumed = item_to_eat.use(player_character, my_tower)
                if consumed:
                    count = getattr(item_to_eat, 'count', 1)
                    if count > 1:
                        item_to_eat.count -= 1
                        add_log(f"{COLOR_GREY}({item_to_eat.count} remaining){COLOR_RESET}")
                    else:
                        player_character.inventory.remove_item(item_to_eat.name)
                gs.inventory_filter = None
                gs.prompt_cntl = "inventory"
                handle_inventory_menu(player_character, my_tower, "init")
            else:
                add_log(f"{COLOR_YELLOW}Invalid item number.{COLOR_RESET}")
        except (ValueError, IndexError):
            add_log(f"{COLOR_YELLOW}Invalid eat command. Format: eat [number]{COLOR_RESET}")

    elif cmd.startswith('e'):
        try:
            # Extract number - skip 'e' and optional space
            num_str = cmd[1:].strip()
            item_number = int(num_str) - 1
            gs.inventory_filter = None  # Clear filter after selecting item

            if 0 <= item_number < len(working_items):
                item_to_equip = working_items[item_number]

                # Block equipping non-bug items while shrunk
                if gs.player_is_shrunk:
                    from .game_data import BUG_WEAPON_TEMPLATES, BUG_ARMOR_TEMPLATES
                    bug_item_names = {t['name'] for t in BUG_WEAPON_TEMPLATES} | {t['name'] for t in BUG_ARMOR_TEMPLATES}
                    if isinstance(item_to_equip, (Weapon, Armor, Towel)) and item_to_equip.name not in bug_item_names:
                        add_log(f"{COLOR_YELLOW}You're too tiny to use {item_to_equip.name}! Only bug-sized gear fits right now.{COLOR_RESET}")
                        return
                    if isinstance(item_to_equip, Treasure) and item_to_equip.treasure_type == 'passive':
                        add_log(f"{COLOR_YELLOW}You're too tiny to wear {item_to_equip.name}! Only bug-sized gear fits right now.{COLOR_RESET}")
                        return

                if isinstance(item_to_equip, Weapon):
                    # BUC curse check: cursed weapon is welded and can't be swapped
                    old = player_character.equipped_weapon
                    if old and getattr(old, 'buc_status', 'uncursed') == 'cursed':
                        old.buc_known = True  # Reveal the curse
                        add_log(f"{COLOR_RED}The {old.name} is welded to your hand! It's CURSED!{COLOR_RESET}")
                        add_log(f"{COLOR_YELLOW}You need a Scroll of Remove Curse or altar purification.{COLOR_RESET}")
                        return
                    if old:
                        add_log(f"Unequipped {old.name}.")
                    player_character.equipped_weapon = item_to_equip
                    add_log(f"{COLOR_GREEN}Equipped {item_to_equip.name}!{COLOR_RESET}")

                elif isinstance(item_to_equip, Armor):
                    # BUC curse check: cursed armor is fused and can't be removed
                    old = player_character.equipped_armor
                    if old and getattr(old, 'buc_status', 'uncursed') == 'cursed':
                        old.buc_known = True  # Reveal the curse
                        add_log(f"{COLOR_RED}The {old.name} is fused to your body! It's CURSED!{COLOR_RESET}")
                        add_log(f"{COLOR_YELLOW}You need a Scroll of Remove Curse or altar purification.{COLOR_RESET}")
                        return
                    if old:
                        add_log(f"Unequipped {old.name}.")
                    player_character.equipped_armor = item_to_equip
                    add_log(f"{COLOR_GREEN}Equipped {item_to_equip.name}!{COLOR_RESET}")

                elif isinstance(item_to_equip, Towel):
                    # Allow equipping towel as weapon (wet towel is more effective)
                    if player_character.equipped_weapon:
                        add_log(f"Unequipped {player_character.equipped_weapon.name}.")
                    player_character.equipped_weapon = item_to_equip
                    if item_to_equip.wetness > 0:
                        add_log(f"{COLOR_GREEN}Equipped {item_to_equip.get_display_name()} as weapon!{COLOR_RESET}")
                        add_log(f"{COLOR_CYAN}Wet towel damage: 1-{min(6, item_to_equip.wetness)}{COLOR_RESET}")
                    else:
                        add_log(f"{COLOR_YELLOW}Equipped dry towel as weapon. It's not very effective...{COLOR_RESET}")
                        add_log(f"{COLOR_GREY}(Wet it in a pool for better damage!){COLOR_RESET}")

                elif isinstance(item_to_equip, Treasure) and item_to_equip.treasure_type == 'passive':
                    # Equip passive treasure as accessory
                    player_character.equip_accessory(item_to_equip)

                else:
                    add_log(f"{COLOR_YELLOW}You cannot equip {item_to_equip.name}.{COLOR_RESET}")

                gs.prompt_cntl = "inventory"
                handle_inventory_menu(player_character, my_tower, "init")
            else:
                add_log(f"{COLOR_YELLOW}Invalid item number.{COLOR_RESET}")

        except (ValueError, IndexError):
            add_log(f"{COLOR_YELLOW}Invalid equip command. Format: e [number]{COLOR_RESET}")

    else:
        if in_combat:
            add_log(f"{COLOR_YELLOW}Invalid command. Use 'u [number]' to use, 's' for stats, 'j' for journal, 'a' for achievements, 'x' to return to combat.{COLOR_RESET}")
        else:
            add_log(f"{COLOR_YELLOW}Invalid command. Use 'u [number]' to use, 'e [number]' to equip, 'm' for spells, 'j' for journal, 'a' for achievements, 'x' to exit.{COLOR_RESET}")

def move_player_randomly(player_character, my_tower):
    """
    Moves the player in a random valid direction, updating player_character's position.
    Calls _trigger_room_interaction if a move is successful.
    """
    current_x, current_y = player_character.x, player_character.y
    all_directions = ['n', 's', 'e', 'w']
    random.shuffle(all_directions) # Shuffle to attempt directions randomly

    for direction in all_directions:
        # Pass ignore_confusion=True to prevent infinite recursion
        moved = move_player(player_character, my_tower, direction, ignore_confusion=True)
        if moved:
            return # Player moved, interactions are handled by move_player itself

    add_log("No valid random moves available from current position.")

def reveal_secrets_shard_rooms(player_character, my_tower):
    """
    If player has Secrets Shard, reveal hidden rooms (V, O, W) on current floor.
    Called when player moves to update map visibility.
    """
    if not gs.shards_obtained.get('secrets'):
        return
    
    current_floor = my_tower.floors[player_character.z]
    revealed_count = 0
    
    for r in range(current_floor.rows):
        for c in range(current_floor.cols):
            room = current_floor.grid[r][c]
            # Reveal Vaults, Oracle rooms, and Warp rooms
            if room.room_type in ['V', 'O', 'W'] and not room.discovered:
                room.discovered = True
                revealed_count += 1
    
    # Only show message once per floor
    floor_key = f"secrets_revealed_floor_{player_character.z}"
    if revealed_count > 0 and not current_floor.properties.get(floor_key):
        current_floor.properties[floor_key] = True
        add_log(f"{COLOR_PURPLE}[Secrets Shard] {revealed_count} hidden room{'s' if revealed_count != 1 else ''} revealed on the map!{COLOR_RESET}")


def _trigger_room_interaction(player_character, my_tower):
    """
    Checks the room type at the player's current position and triggers the appropriate
    game mode (combat, shop, chest, etc.). Sets the global gs.prompt_cntl.
    """

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    coords = (player_character.x, player_character.y, player_character.z)

    # Check if this room should be upgraded to a special quest room
    if not room.properties.get('special_room_checked'):
        room.properties['special_room_checked'] = True  # Only check once
        
        # Champion Monster (M room upgrade)
        if room.room_type == 'M' and gs.champion_monster_available and not room.properties.get('is_champion'):
            if not gs.runes_obtained['battle']:
                room.properties['is_champion'] = True
                # Don't spawn more champions until this one is defeated
                gs.champion_monster_available = False
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_RED}You sense tremendous power... A CHAMPION awaits!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        
        # Legendary Chest (C room upgrade)
        elif room.room_type == 'C' and gs.legendary_chest_available and not room.properties.get('is_legendary'):
            if not gs.runes_obtained['treasure']:
                room.properties['is_legendary'] = True
                # Don't spawn more legendary chests until this one is opened
                gs.legendary_chest_available = False
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_YELLOW}A magnificent chest gleams with otherworldly light!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        
        # Ancient Waters (P room upgrade)
        elif room.room_type == 'P' and gs.ancient_waters_available and not room.properties.get('is_ancient'):
            if not gs.runes_obtained['reflection']:
                room.properties['is_ancient'] = True
                # Don't spawn more ancient waters until this one is used
                gs.ancient_waters_available = False
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}The pool shimmers with ancient magic! These are the Ancient Waters!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        
        # Codex of Zot (L room upgrade)
        elif room.room_type == 'L' and gs.codex_available and not room.properties.get('has_codex'):
            if not gs.runes_obtained['knowledge']:
                room.properties['has_codex'] = True
                # Don't spawn more codex locations until this one is read
                gs.codex_available = False
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}An ancient tome radiates pure knowledge... The Codex of Zot!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        
        # Master Dungeon (G room upgrade)
        elif room.room_type == 'N' and gs.master_dungeon_available and not room.properties.get('is_master'):
            if not gs.runes_obtained['secrets']:
                room.properties['is_master'] = True
                # Don't spawn more master dungeons until this one is completed
                gs.master_dungeon_available = False
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_YELLOW}Intricate locks cover this door... A Master Dungeon!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        
        # Cursed Tomb (T room upgrade)
        elif room.room_type == 'T' and gs.cursed_tomb_available and not room.properties.get('is_cursed'):
            if not gs.runes_obtained['eternity']:
                room.properties['is_cursed'] = True
                # Don't spawn more cursed tombs until this one is completed
                gs.cursed_tomb_available = False
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_RED}Dark energy emanates from this tomb... It is CURSED!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        
        # World Tree (R room upgrade)
        elif room.room_type == 'G' and gs.world_tree_available and not room.properties.get('has_world_tree'):
            if not gs.runes_obtained['growth']:
                room.properties['has_world_tree'] = True
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_GREEN}A magnificent sapling glows with primordial energy... The World Tree!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")

    # Default to game_loop, specific rooms will override
    gs.prompt_cntl = "game_loop"

    if room.room_type == 'V':
        coords = (player_character.x, player_character.y, player_character.z)

        # Check if this is a Shard Vault (requires rune to enter)
        shard_type = room.properties.get('shard_vault_type')
        if shard_type and not gs.shards_obtained.get(shard_type):
            # This is a Shard Vault
            gs.prompt_cntl = "shard_vault_mode"
            process_shard_vault_action(player_character, my_tower, "init")
        else:
            # Normal vendor vault, Magic Shop, or Bug Merchant
            if coords not in gs.encountered_vendors:
                is_magic = room.properties.get('is_magic_shop', False)
                is_bug = room.properties.get('is_bug_merchant', False)
                if is_bug:
                    from .vendor import BUG_MERCHANT_NAMES
                    v_name = random.choice(BUG_MERCHANT_NAMES)
                    new_vendor = Vendor(name=v_name, gold=random.randint(100, 300), player_character=player_character, bug_merchant=True)
                elif is_magic:
                    v_name = random.choice(MAGIC_SHOP_NAMES)
                    new_vendor = Vendor(name=v_name, gold=random.randint(500, 1200), player_character=player_character, magic_shop=True)
                else:
                    v_name = random.choice(vendor_names)
                    new_vendor = Vendor(name=v_name, gold=random.randint(200, 600), player_character=player_character)
                gs.encountered_vendors[coords] = new_vendor

            gs.active_vendor = gs.encountered_vendors[coords]
            is_magic = room.properties.get('is_magic_shop', False)
            is_bug = room.properties.get('is_bug_merchant', False)
            if is_bug:
                from .vendor import BUG_MERCHANT_GREETINGS
                greeting = BUG_MERCHANT_GREETINGS.get(gs.active_vendor.name, f"A bug merchant chitters at you. 'Need gear, tiny one?'")
                set_vendor_greeting(greeting)
                add_log(f"{COLOR_GREEN}{greeting}{COLOR_RESET}")
            elif is_magic:
                greeting = MAGIC_SHOP_MESSAGES.get(gs.active_vendor.name, "You have found Ye Olde Magic Shoppe. Arcane wonders await within.")
                set_vendor_greeting(greeting)
                add_log(f"{COLOR_PURPLE}{greeting}{COLOR_RESET}")
            else:
                set_vendor_greeting(f"You enter the shop of {gs.active_vendor.name}.")
                add_log(f"You enter the shop of {gs.active_vendor.name}.")
            gs.prompt_cntl = "vendor_shop"
            process_vendor_action(player_character, gs.active_vendor, "list")
    elif room.room_type == 'C':
        gs.prompt_cntl = "chest_mode"
        process_chest_action(player_character, my_tower, "init")
    elif room.room_type == 'A':
        gs.prompt_cntl = "altar_mode"
        process_altar_action(player_character, my_tower, "init")
    elif room.room_type == 'W':
        gs.prompt_cntl = "warp_mode"
        process_warp_action(player_character, my_tower, "init", gs.floor_params)
    elif room.room_type == 'P':
        gs.prompt_cntl = "pool_mode"
        process_pool_action(player_character, my_tower, "init")
    elif room.room_type == 'L':
        gs.prompt_cntl = "library_mode"
        process_library_action(player_character, my_tower, "init")
    elif room.room_type == 'M':
        coords = (player_character.x, player_character.y, player_character.z)
        if coords not in gs.encountered_monsters:
            # Check if this is Zot's Guardian boss arena
            is_boss_arena = room.properties.get('has_zots_guardian', False)
            
            if is_boss_arena:
                # Spawn ZOT'S GUARDIAN - The final boss!
                new_monster = Monster(
                    " ZOT'S GUARDIAN ",
                    1000,  # Massive health
                    80,    # Devastating attack
                    50,    # Strong defense
                    [],    # No weaknesses
                    ['Physical', 'Fire', 'Ice', 'Lightning', 'Darkness', 'Light'],  # All resistances
                    50,    # Maximum level
                    'Chaos',
                    f"{COLOR_RED}An immortal guardian bound to protect the Orb of Zot! Reality warps around its form!{COLOR_RESET}",
                    f"{COLOR_YELLOW}ZOT'S GUARDIAN FALLS! The Orb of Zot appears before you!{COLOR_RESET}"
                )
                new_monster.properties['is_zots_guardian'] = True
            # Check if this is Platino's lair
            elif room.properties.get('is_platino', False):
                new_monster = Monster(
                    "Platino",
                    500,   # Tough
                    60,    # Strong attack
                    40,    # High defense
                    [],    # No elemental weaknesses
                    ['Physical', 'Fire', 'Ice', 'Lightning', 'Darkness', 'Light'],  # Resists all
                    42,    # Level 42
                    'Physical',
                    f"{COLOR_PURPLE}A shimmering platinum dragon materializes! Its scales deflect all direct attacks!{COLOR_RESET}",
                    f"{COLOR_YELLOW}Platino crashes to the ground, a single scale falling loose!{COLOR_RESET}"
                )
                new_monster.properties['is_platino'] = True
            # Check if this is a Champion Monster
            elif room.properties.get('is_champion', False) and not gs.runes_obtained['battle']:
                # Spawn Champion - 2x stats, special name
                target_lvl = player_character.z + 2  # Higher level
                potential_monsters = [m for m in MONSTER_TEMPLATES if m['level'] >= target_lvl - 1 and m['level'] <= target_lvl + 1]
                if not potential_monsters:
                    potential_monsters = MONSTER_TEMPLATES
                
                m_data = random.choice(potential_monsters)
                new_monster = Monster(
                    f" CHAMPION {m_data['name'].upper()} ",
                    m_data['health'] * 2,  # Double health
                    m_data['attack'] * 2,  # Double attack
                    m_data['defense'] * 2,  # Double defense
                    m_data.get('elemental_weakness', []),
                    m_data.get('elemental_strength', []),
                    m_data.get('level', 1) + 3,  # Higher level
                    m_data.get('attack_element', 'Physical'),
                    f"{COLOR_RED}A legendary champion warrior! Its eyes glow with otherworldly power!{COLOR_RESET}",
                    f"{COLOR_PURPLE}The Champion falls! You claim victory!{COLOR_RESET}",
                    m_data.get('gold_min', 10) * 3,
                    m_data.get('gold_max', 30) * 3
                )
                new_monster.properties['is_champion'] = True  # Mark as champion
            # Check if this is an Undead Guardian (spawned near tombs)
            elif room.properties.get('undead_guardian', False):
                # Spawn tough undead guardian
                target_lvl = player_character.z + 1  # Slightly above player level
                min_lvl = max(0, target_lvl - 1)
                max_lvl = target_lvl + 2
                
                # Prefer undead monster types
                undead_types = ['Skeleton', 'Zombie', 'Ghost', 'Wraith', 'Vampire', 'Lich', 'Death Knight']
                undead_monsters = [m for m in MONSTER_TEMPLATES if any(undead in m['name'] for undead in undead_types) and min_lvl <= m['level'] <= max_lvl + 2]
                
                if undead_monsters:
                    m_data = random.choice(undead_monsters)
                else:
                    # Fallback to any monster near level
                    potential_monsters = [m for m in MONSTER_TEMPLATES if m['level'] >= target_lvl - 1 and m['level'] <= target_lvl + 2]
                    if not potential_monsters:
                        potential_monsters = MONSTER_TEMPLATES
                    m_data = random.choice(potential_monsters)
                
                # Buffed stats - 1.5x multiplier
                new_monster = Monster(
                    f" UNDEAD {m_data['name'].upper()}",
                    int(m_data['health'] * 1.5),  # 50% more health
                    int(m_data['attack'] * 1.5),  # 50% more attack
                    int(m_data['defense'] * 1.5),  # 50% more defense
                    m_data.get('elemental_weakness', []),
                    m_data.get('elemental_strength', []) + ['Darkness'],  # Add darkness resistance
                    m_data.get('level', 1) + 2,  # +2 levels
                    m_data.get('attack_element', 'Darkness'),  # Darkness attacks
                    f"{COLOR_GREY}An undead guardian risen to protect the ancient tomb!{COLOR_RESET}",
                    f"{COLOR_PURPLE}The undead guardian crumbles to dust!{COLOR_RESET}",
                    m_data.get('gold_min', 10) * 2,
                    m_data.get('gold_max', 30) * 2
                )
                new_monster.properties['undead_guardian'] = True

            # Bug Level: Spawn bug monsters on bug level floors
            elif room.properties.get('is_bug_monster'):
                is_queen = room.properties.get('is_bug_queen', False)
                if is_queen:
                    # Spawn the Bug Queen
                    queen_data = [m for m in BUG_MONSTER_TEMPLATES if m['name'] == 'BUG QUEEN'][0]
                    new_monster = Monster(
                        queen_data['name'],
                        queen_data['health'],
                        queen_data['attack'],
                        queen_data['defense'],
                        queen_data.get('elemental_weakness', []),
                        queen_data.get('elemental_strength', []),
                        queen_data.get('level', 3),
                        queen_data.get('attack_element', 'Physical'),
                        queen_data.get('flavor_text', ''),
                        queen_data.get('victory_text', ''),
                        queen_data.get('can_talk', True),
                        queen_data.get('greeting_template', ''),
                        queen_data.get('special_attack', None)
                    )
                    new_monster.properties['is_bug_queen'] = True
                    new_monster.properties['is_bug_monster'] = True
                else:
                    # Spawn a random bug monster (not the queen)
                    bug_pool = [m for m in BUG_MONSTER_TEMPLATES if m['name'] != 'BUG QUEEN']
                    m_data = random.choice(bug_pool)
                    new_monster = Monster(
                        m_data['name'],
                        m_data['health'],
                        m_data['attack'],
                        m_data['defense'],
                        m_data.get('elemental_weakness', []),
                        m_data.get('elemental_strength', []),
                        m_data.get('level', 1),
                        m_data.get('attack_element', 'Physical'),
                        m_data.get('flavor_text', ''),
                        m_data.get('victory_text', ''),
                        m_data.get('can_talk', False),
                        m_data.get('greeting_template', ''),
                        m_data.get('special_attack', None)
                    )
                    new_monster.properties['is_bug_monster'] = True

            else:
                # Normal monster spawning with floor-based phasing and evolution
                # Each template level has a floor range where it can appear.
                # Lower-level templates phase out on deeper floors.
                # Monsters evolve (Hardened/Savage/Dread/Mythic) based on floor
                # depth vs their base template level.

                target_lvl = player_character.z

                # Filter templates by floor range
                potential_monsters = [
                    m for m in MONSTER_TEMPLATES
                    if MONSTER_SPAWN_FLOOR_RANGE.get(m['level'], (0, 49))[0] <= target_lvl
                    <= MONSTER_SPAWN_FLOOR_RANGE.get(m['level'], (0, 49))[1]
                ]
                
                if not potential_monsters:
                    # Fallback: use highest level templates
                    potential_monsters = [m for m in MONSTER_TEMPLATES if m['level'] >= 8]
                    if not potential_monsters:
                        potential_monsters = MONSTER_TEMPLATES

                m_data = random.choice(potential_monsters)
                
                # Determine evolution tier based on floor depth vs template level
                base_level = m_data.get('level', 1)
                floor_diff = max(0, target_lvl - base_level)
                
                # Find matching evolution tier
                evo_prefix = ''
                hp_mult = 1.0
                atk_mult = 1.0
                def_mult = 1.0
                for min_d, max_d, prefix, hm, am, dm in MONSTER_EVOLUTION_TIERS:
                    if min_d <= floor_diff <= max_d:
                        evo_prefix = prefix
                        hp_mult = hm
                        atk_mult = am
                        def_mult = dm
                        break
                
                # Apply evolution tier multiplier + linear floor scaling
                # Linear scaling: ATK grows faster than DEF so monsters hit harder on deep floors
                linear_hp = 1.0 + (floor_diff * 0.04)
                linear_atk = 1.0 + (floor_diff * 0.03)
                linear_def = 1.0 + (floor_diff * 0.015)

                # Aggression scalar: self-correcting formula that tracks actual player
                # defense and HP at each floor. Only boosts monster attack when natural
                # scaling falls short of 7.5% HP per hit -- never dampens.
                # Late floors (35+) are intentionally brutal: natural evolution tiers
                # already push damage to 10-22% HP and we leave that intact.
                #
                # Estimates: upgrade accumulation ~0.7255*floor^0.8808 (capped 23),
                #            avg defense base + racial bonuses = 9.0,
                #            avg char level ~ 1 + floor*0.46.
                _fl = target_lvl
                _armor_pool = [a for a in ARMOR_TEMPLATES
                               if max(0, _fl - 3) <= a.level <= _fl + 2]
                if not _armor_pool:
                    _armor_pool = [a for a in ARMOR_TEMPLATES if a.level >= 40]
                _armor_base = sum(a._base_defense_bonus for a in _armor_pool) / len(_armor_pool)
                _upg_est    = min(23.0, 0.7255 * (_fl ** 0.8808)) if _fl > 0 else 0.0
                _pd_est     = 9.0 + _armor_base + _upg_est
                _lv_est     = max(1, int(1 + _fl * 0.46))
                _php_est    = 100 + _lv_est * 11 + 30

                # Natural attack before scalar
                _nat_atk    = m_data['attack'] * atk_mult * linear_atk
                # Only boost when natural attack is below the 7.5% HP floor -- never reduce
                _lo_atk     = _pd_est + _php_est * 0.107   # floor: 7.5% HP / 0.70 hit rate
                aggression_scalar = max(1.0, _lo_atk / max(1.0, _nat_atk))

                scaled_health = int(m_data['health'] * hp_mult * linear_hp)
                scaled_attack = int(m_data['attack'] * atk_mult * linear_atk * aggression_scalar)
                scaled_defense = int(m_data['defense'] * def_mult * linear_def)
                scaled_level = target_lvl  # Monster level matches floor
                
                # Build display name with evolution prefix
                monster_name = m_data['name']
                if evo_prefix:
                    monster_name = f"{evo_prefix} {monster_name}"
                
                new_monster = Monster(
                    monster_name,
                    scaled_health,
                    scaled_attack,
                    scaled_defense,
                    m_data.get('elemental_weakness', []),
                    m_data.get('elemental_strength', []),
                    scaled_level,
                    m_data.get('attack_element', 'Physical'),
                    m_data.get('flavor_text', ''),
                    m_data.get('victory_text', ''),
                m_data.get('can_talk', False),
                m_data.get('greeting_template', ''),
                m_data.get('special_attack', None)
            )
                # Store evolution tier for combat UI display
                if evo_prefix:
                    new_monster.properties['evolution_tier'] = evo_prefix
            gs.encountered_monsters[coords] = new_monster

        gs.active_monster = gs.encountered_monsters[coords]
        if gs.active_monster.is_alive():
            gs.prompt_cntl = "combat_mode"
            process_combat_action(player_character, my_tower, "init")
        else:
            add_log("A dead monster lies here.")
            gs.prompt_cntl = "game_loop" # Explicitly set if monster is dead
    elif room.room_type == 'U':
        gs.prompt_cntl = "stairs_up_mode"
        process_stairs_up_action(player_character, my_tower, "init", gs.floor_params)
    elif room.room_type == 'D':
        gs.prompt_cntl = "stairs_down_mode"
        process_stairs_down_action(player_character, my_tower, "init")
    elif room.room_type == 'N':
        gs.prompt_cntl = "dungeon_mode"
        process_dungeon_action(player_character, my_tower, "init")
    elif room.room_type == 'T':
        gs.prompt_cntl = "tomb_mode"
        process_tomb_action(player_character, my_tower, "init")
    elif room.room_type == 'G':
        gs.prompt_cntl = "garden_mode"
        process_garden_action(player_character, my_tower, "init")
    elif room.room_type == 'O':
        gs.prompt_cntl = "oracle_mode"
        process_oracle_action(player_character, my_tower, "init")
    elif room.room_type == 'B':
        gs.prompt_cntl = "blacksmith_mode"
        process_blacksmith_action(player_character, my_tower, "init")
    elif room.room_type == 'F':
        gs.prompt_cntl = "shrine_mode"
        process_shrine_action(player_character, my_tower, "init")
    elif room.room_type == 'Q':
        gs.prompt_cntl = "alchemist_mode"
        process_alchemist_action(player_character, my_tower, "init")
    elif room.room_type == 'K':
        gs.prompt_cntl = "war_room_mode"
        process_war_room_action(player_character, my_tower, "init")
    elif room.room_type == 'X':
        if room.properties.get('is_bug_taxidermist'):
            add_log(f"{COLOR_GREEN}A dung beetle in a leather apron looks up from its workbench.{COLOR_RESET}")
            add_log(f'{COLOR_CYAN}"Bring me trophies from the hive! I can make something beautiful!"{COLOR_RESET}')
        gs.prompt_cntl = "taxidermist_mode"
        process_taxidermist_action(player_character, my_tower, "init")
    elif room.room_type == 'Z' or room.properties.get('is_puzzle_room'):
        # Zotle Puzzle Room
        gs.prompt_cntl = "puzzle_mode"
        process_puzzle_action(player_character, my_tower, "init")
    # If room type is '.', prompt_cntl remains "game_loop" (set at start of function)


# --------------------------------------------------------------------------------


# --------------------------------------------------------------------------------
# 17. MOVEMENT & NAVIGATION
# --------------------------------------------------------------------------------

def move_player(character, my_tower, direction, ignore_confusion=False):

    # Check for movement-impairing status effects
    for effect_name, effect in character.status_effects.items():
        if effect.effect_type == 'web':
            add_log(f"{COLOR_YELLOW}You are stuck in a web and cannot move!{COLOR_RESET}")
            return False
        # FIX: Check ignore_confusion flag to prevent recursion
        if effect.effect_type == 'confusion' and not ignore_confusion:
            add_log(f"{COLOR_YELLOW}You are confused and move randomly!{COLOR_RESET}")
            move_player_randomly(character, my_tower) # Attempt a random move
            return True # Consider this a 'move' action for processing purposes

    current_floor = my_tower.floors[character.z]
    old_x, old_y = character.x, character.y
    new_x, new_y = character.x, character.y

    if direction == 'n':
        new_y -= 1
    elif direction == 's':
        new_y += 1
    elif direction == 'w':
        new_x -= 1
    elif direction == 'e':
        new_x += 1

    # Check boundaries and if the new position is a wall
    if 0 <= new_x < current_floor.cols and 0 <= new_y < current_floor.rows and \
       current_floor.grid[new_y][new_x].room_type != current_floor.wall_char:
        # Update player position
        character.x, character.y = new_x, new_y

        # Track max floor reached
        if character.z > gs.game_stats.get('max_floor_reached', 0):
            gs.game_stats['max_floor_reached'] = character.z
            check_achievements(character)

        # Mark the new room as discovered
        current_floor.grid[new_y][new_x].discovered = True

        # Reveal adjacent walls
        reveal_adjacent_walls(character, my_tower)
        
        # Secrets Shard: Reveal hidden rooms on current floor
        reveal_secrets_shard_rooms(character, my_tower)

        character.process_status_effects() # Process status effects after moving
        # ADD THIS LINE RIGHT HERE:
        process_passive_treasures(character)
        
        # Process hunger and meat rot each move
        process_hunger(character)
        tick_meat_rot(character)
        
        # Process haunted floor effects (may trigger combat)
        process_haunted_floor(character, my_tower)
        
        # If haunted floor triggered combat, don't continue with room interaction
        if gs.prompt_cntl == "combat_mode":
            return True
        
        # Process ephemeral (Fey) garden spawning/despawning
        process_ephemeral_gardens(character, my_tower)

        # Check for player death due to status effects
        if not character.is_alive():
            add_log(f"{COLOR_RED}You were defeated by status effects upon entering the new room... Game Over!{COLOR_RESET}")
            gs.prompt_cntl = "death_screen"
            return False # Player died, no further interaction needed

        _trigger_room_interaction(character, my_tower) # Trigger room interaction after successful move
        return True # Indicating a successful move
    else:
        add_log("You hit a wall!")
        return False # Indicating no move

def process_warp_action(player_character, my_tower, cmd, floor_params_ref):

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]

    # Check if this warp is linked to a vault
    is_vault_warp = room.properties.get('vault_warp', False)
    vault_destination = room.properties.get('vault_destination', None)

    if cmd == "init":
        add_log(f"{COLOR_PURPLE}You find a swirling portal left over from Zot's experiments!{COLOR_RESET}")
        if is_vault_warp:
            add_log(f"{COLOR_YELLOW}This portal pulses with an ominous energy...{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}Do you resist the warp? (y/n){COLOR_RESET}")
        return

    if cmd == 'y':
        # Player chooses to resist
        evasion_chance = 0.20 + (player_character.intelligence * 0.02)
        evasion_chance = min(1.0, evasion_chance)
        
        if random.random() < evasion_chance:
            add_log(f"{COLOR_GREEN}Your keen intellect allows you to resist the portal's pull! You manage to avoid being warped.{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"
        else:
            add_log(f"{COLOR_RED}You try to resist, but the portal's power overwhelms you!{COLOR_RESET}")
            _execute_warp(player_character, my_tower, floor_params_ref, is_vault_warp, vault_destination)
        return
    
    elif cmd == 'n':
        # Player chooses NOT to resist - warp happens automatically
        add_log(f"{COLOR_PURPLE}You surrender to the portal's pull...{COLOR_RESET}")
        _execute_warp(player_character, my_tower, floor_params_ref, is_vault_warp, vault_destination)
        return
    
    else:
        add_log(f"{COLOR_YELLOW}Choose: y = try to resist | n = enter the warp{COLOR_RESET}")
        return


def _execute_warp(player_character, my_tower, floor_params_ref, is_vault_warp, vault_destination):
    """Execute the warp effect - either to vault or random location"""
    
    current_floor = my_tower.floors[player_character.z]
    
    # Check if this vault warp sends player to vault
    # 50% chance normally, 100% in PLAYTEST mode
    vault_warp_chance = 1.0 if gs.PLAYTEST else 0.5
    
    if is_vault_warp and vault_destination and random.random() < vault_warp_chance:
        # WARP TO VAULT!
        add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}The portal's energy surges with dark power!{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}You are pulled into a sealed vault chamber!{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
        
        vault_x, vault_y = vault_destination
        player_character.x = vault_x
        player_character.y = vault_y
        
        # Discover vault chamber
        vault_room = current_floor.grid[vault_y][vault_x]
        vault_room.discovered = True
        reveal_adjacent_walls(player_character, my_tower)
        
        add_log(f"{COLOR_PURPLE}You materialize in a sealed chamber!{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}The air crackles with ancient magic...{COLOR_RESET}")
        add_log(f"{COLOR_RED}There is no escape from this place!{COLOR_RESET}")
        
        # Create vault defender if not already exists
        coords = (vault_x, vault_y, player_character.z)
        if coords not in gs.encountered_monsters:
            defender = create_vault_defender(player_character.z)
            gs.encountered_monsters[coords] = defender
            add_log(f"{COLOR_RED}A VAULT DEFENDER appears!{COLOR_RESET}")
        
        # Trigger combat
        _trigger_room_interaction(player_character, my_tower)
    else:
        # Normal random warp
        add_log(f"{COLOR_RED}The portal's power overwhelms you! You are sucked in...{COLOR_RESET}")
        
        # New Floor Logic
        current_z = player_character.z
        min_z = max(0, current_z - 2)
        max_z = current_z + 2

        # Generate needed floors
        while len(my_tower.floors) <= max_z:
             my_tower.add_floor(**floor_params_ref)

        # Pick new floor
        new_z = random.randint(min_z, max_z)
        if new_z == current_z and min_z != max_z:
             new_z = random.randint(min_z, max_z)  # Try one more time to change floors

        player_character.z = new_z
        target_floor = my_tower.floors[new_z]

        # Pick new location
        while True:
            rx = random.randint(0, target_floor.cols - 1)
            ry = random.randint(0, target_floor.rows - 1)
            # Check wall (ry, rx)
            if not is_wall_at_coordinate(target_floor, ry, rx) and target_floor.grid[ry][rx].room_type != 'W':
                player_character.x = rx
                player_character.y = ry
                break

        # Reveal
        target_floor.grid[player_character.y][player_character.x].discovered = True
        reveal_adjacent_walls(player_character, my_tower)

        # Check if we warped into a bug level - trigger shrinking spell
        if target_floor.properties.get('is_bug_level') and not gs.player_is_shrunk:
            _trigger_shrinking_spell(player_character)

        _trigger_room_interaction(player_character, my_tower)  # Trigger interaction for the new room
        add_log(f"You emerge disoriented in a new room at ({player_character.x}, {player_character.y}) on Floor {player_character.z + 1}.")




# 18. CHEST & LOOT
# --------------------------------------------------------------------------------

def process_chest_action(player_character, my_tower, cmd):

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]

    if cmd == "init":
        # Commands now shown in HTML and placeholder
        return

    if cmd == 'o':
        gs.sfx_event = 'chest_open'
        # Check if this is a Legendary Chest
        is_legendary = room.properties.get('is_legendary', False)

        if is_legendary and not gs.runes_obtained['treasure']:
            # LEGENDARY CHEST - Guaranteed great rewards + Rune
            add_log(f"{COLOR_YELLOW}The magnificent chest opens with a blinding flash of light!{COLOR_RESET}")
            
            # Guaranteed large gold
            gold_found = random.randint(300, 600)
            add_log(f"{COLOR_GREEN}You found {gold_found} gold!{COLOR_RESET}")
            player_character.gold += gold_found
            gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold_found
            
            # Guaranteed treasure item
            treasure_templates = [t for t in TREASURE_TEMPLATES if t.get('level', 1) <= player_character.z + 2]
            if treasure_templates:
                treasure_item = random.choice(treasure_templates)
                new_treasure = Treasure(
                    name=treasure_item['name'],
                    value=treasure_item.get('value', 100),
                    level=treasure_item.get('level', 1),
                    description=treasure_item.get('description', ''),
                    stat_bonuses=treasure_item.get('stat_bonuses', {})
                )
                player_character.inventory.add_item(new_treasure)
                add_log(f"{COLOR_CYAN}You found: {new_treasure.name}!{COLOR_RESET}")
            
            # Award Rune of Treasure
            rune = Rune(
                name="Rune of Treasure",
                rune_type='treasure',
                description="A golden rune gleaming with avarice. Unlocks the Treasure Shard vault.",
                value=0,
                level=0
            )
            player_character.inventory.add_item(rune)
            gs.runes_obtained['treasure'] = True
            gs.legendary_chest_available = False
            
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}* THE RUNE OF TREASURE IS YOURS! *{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}A glowing rune materializes from the treasure hoard!{COLOR_RESET}")
            add_log("")
            
            gs.game_stats['chests_opened'] = gs.game_stats.get('chests_opened', 0) + 1
            check_achievements(player_character)
        elif room.properties.get('has_growth_mushroom') and gs.player_is_shrunk:
            # Bug level chest with Growth Mushroom - guaranteed backup way to cure shrinking
            add_log(f"{COLOR_GREEN}You pry open the tiny chest...{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}Inside, a luminous mushroom pulses with restorative magic!{COLOR_RESET}")
            growth_mushroom = Potion(
                name="Zot's Growth Mushroom",
                description="A luminous mushroom pulsing with restorative magic. Eating it will reverse Zot's shrinking spell.",
                value=0, level=0, potion_type='growth_mushroom', effect_magnitude=0, duration=0
            )
            player_character.inventory.add_item(growth_mushroom)
            add_log(f"{COLOR_GREEN}You obtained: Zot's Growth Mushroom!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Use it from your inventory to restore your size!{COLOR_RESET}")
            # Also give some normal chest loot
            gold_found = random.randint(20, 80)
            player_character.gold += gold_found
            add_log(f"You also found {gold_found} gold.")
            gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold_found
            gs.game_stats['chests_opened'] = gs.game_stats.get('chests_opened', 0) + 1
        else:
            # Normal chest logic
            # Updated chest outcome system with Lantern Fuel, Equipment, and Upgrade Scrolls
            # Upgrade scroll chance scales with floor level
            floor_level = player_character.z
            
            # Base probabilities
            base_items = ['gold', 'gas', 'boom', 'empty', 'treasure', 'lantern_fuel', 'equipment']
            base_probs = [0.35, 0.08, 0.07, 0.05, 0.05, 0.20, 0.20]
            
            # Add upgrade scroll with floor-scaled probability
            # Floor 1-4: 0%, Floor 5-9: 3-7%, Floor 10-14: 8-12%, Floor 15+: 13-17%
            if floor_level >= 5:
                upgrade_scroll_chance = min(0.17, 0.03 + (floor_level - 5) * 0.02)
                base_items.append('upgrade_scroll')
                base_probs.append(upgrade_scroll_chance)
                # Normalize probabilities to sum to 1
                total = sum(base_probs)
                base_probs = [p / total for p in base_probs]
            
            items = base_items
            probabilities = base_probs
            selected_item_np = random.choices(items, weights=probabilities, k=1)[0]

            if selected_item_np == 'gold':
                gold_found = 0
                for _ in range(player_character.z + 1):
                    gold_found += random.randint(1, 4)
                gold_found *= 10
                add_log(f"{COLOR_GREEN}You found {gold_found} gold!{COLOR_RESET}")
                player_character.gold += gold_found
                add_log(f"{COLOR_GREEN}Total gold: {player_character.gold}{COLOR_RESET}")
                gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold_found
                gs.game_stats['chests_opened'] = gs.game_stats.get('chests_opened', 0) + 1
                
                # QUEST TRACKING: Rune of Treasure
                if not gs.runes_obtained['treasure']:
                    gs.rune_progress['chests_opened_total'] += 1
                    if gs.rune_progress['chests_opened_total'] >= gs.rune_progress_reqs['chests_opened_total'] and not gs.legendary_chest_available:
                        gs.legendary_chest_available = True
                        add_log(f"{COLOR_PURPLE}The treasure gods smile upon you! A Legendary Chest awaits discovery.{COLOR_RESET}")
                
                check_achievements(player_character)

            elif selected_item_np == 'gas':
                add_log("Gas pours from the chest! You stagger from the room!")
                room.room_type = '.'
                move_player_randomly(player_character, my_tower)
                return

            elif selected_item_np == 'boom':
                add_log(f"{COLOR_RED} The chest explodes!!! {COLOR_RESET}")
                boom_dmg = 0
                for _ in range(player_character.z + 1):
                    boom_dmg += random.randint(5, 10)
                burn_inventory_items(player_character, source='explosion')
                if player_character.take_damage_no_def(boom_dmg):
                    add_log(f"{player_character.name} has been defeated! Game Over.")
                    gs.prompt_cntl = "death_screen"
                    return

            elif selected_item_np == 'empty':
                add_log("The chest is empty. As an entitled dungeon crawler, you feel robbed.")

            elif selected_item_np == 'treasure':
                add_log(f"{COLOR_GREEN}You found a sparkling treasure!{COLOR_RESET}")
                if TREASURE_TEMPLATES:
                    chosen_treasure_template = get_random_treasure(player_character.z, allow_unique=True)
                    new_treasure = Treasure(
                        name=chosen_treasure_template.name,
                        description=chosen_treasure_template.description,
                        gold_value=chosen_treasure_template.gold_value,
                        value=chosen_treasure_template.value,
                        benefit=chosen_treasure_template.benefit,
                        level=chosen_treasure_template.level,
                        treasure_type=chosen_treasure_template.treasure_type,
                        is_unique=chosen_treasure_template.is_unique,
                        use_effect=chosen_treasure_template.use_effect,
                        passive_effect=chosen_treasure_template.passive_effect
                    )
                    player_character.inventory.add_item(new_treasure)
                    new_treasure.collect(player_character)
                else:
                    add_log("You found a treasure, but there are no defined treasure items!")

            elif selected_item_np == 'lantern_fuel':
                # NEW: Lantern Fuel drop
                fuel_count = random.randint(1, 3)  # 1-3 fuel items

                add_log(f"{COLOR_CYAN}{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}You found {fuel_count} Lantern Fuel!{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}{COLOR_RESET}")

                for _ in range(fuel_count):
                    fuel_item = LanternFuel(
                        name="Lantern Fuel",
                        description="A small flask of oil for your lantern.",
                        value=5,
                        level=0,
                        fuel_restore_amount=10
                    )
                    player_character.inventory.add_item(fuel_item)

                # Check if player has a lantern
                has_lantern = False
                for item in player_character.inventory.items:
                    if isinstance(item, Lantern):
                        has_lantern = True
                        break

                if has_lantern:
                    add_log(f"{COLOR_GREEN} Perfect! You can use this to refuel your lantern.{COLOR_RESET}")
                else:
                    add_log(f"{COLOR_YELLOW} Tip: Find a lantern to make use of this fuel!{COLOR_RESET}")

                gs.game_stats['chests_opened'] = gs.game_stats.get('chests_opened', 0) + 1
                
                # QUEST TRACKING: Rune of Treasure
                if not gs.runes_obtained['treasure']:
                    gs.rune_progress['chests_opened_total'] += 1
                    if gs.rune_progress['chests_opened_total'] >= gs.rune_progress_reqs['chests_opened_total'] and not gs.legendary_chest_available:
                        gs.legendary_chest_available = True
                        add_log(f"{COLOR_PURPLE}The treasure gods smile upon you! A Legendary Chest awaits discovery.{COLOR_RESET}")
                
                check_achievements(player_character)

            elif selected_item_np == 'equipment':
                # Enhanced weapon or armor drop
                if random.random() < 0.5:
                    weapon = create_random_enhanced_weapon(player_character.z)
                    weapon.buc_status = roll_buc_status(player_character.z, 'chest')
                    player_character.inventory.add_item(weapon)
                    add_log(f"{COLOR_CYAN}You found a weapon!{COLOR_RESET}")
                    add_log(f"{COLOR_GREEN}{weapon.get_display_name()}{COLOR_RESET}")
                    add_log(f"{COLOR_GREY}Attack: +{weapon.attack_bonus} | Level: {weapon.level}{COLOR_RESET}")
                    if weapon.elemental_strength and weapon.elemental_strength[0] != "None":
                        add_log(f"{COLOR_YELLOW}Element: {', '.join(weapon.elemental_strength)}{COLOR_RESET}")
                else:
                    armor = create_random_enhanced_armor(player_character.z)
                    armor.buc_status = roll_buc_status(player_character.z, 'chest')
                    player_character.inventory.add_item(armor)
                    add_log(f"{COLOR_CYAN}You found armor!{COLOR_RESET}")
                    add_log(f"{COLOR_GREEN}{armor.get_display_name()}{COLOR_RESET}")
                    add_log(f"{COLOR_GREY}Defense: +{armor.defense_bonus} | Level: {armor.level}{COLOR_RESET}")
                    if armor.elemental_strength and armor.elemental_strength[0] != "None":
                        add_log(f"{COLOR_YELLOW}Resists: {', '.join(armor.elemental_strength)}{COLOR_RESET}")
                
                gs.game_stats['chests_opened'] = gs.game_stats.get('chests_opened', 0) + 1
                
                # QUEST TRACKING: Rune of Treasure
                if not gs.runes_obtained['treasure']:
                    gs.rune_progress['chests_opened_total'] += 1
                    if gs.rune_progress['chests_opened_total'] >= gs.rune_progress_reqs['chests_opened_total'] and not gs.legendary_chest_available:
                        gs.legendary_chest_available = True
                        add_log(f"{COLOR_PURPLE}The treasure gods smile upon you! A Legendary Chest awaits discovery.{COLOR_RESET}")
                
                check_achievements(player_character)

            elif selected_item_np == 'upgrade_scroll':
                # Upgrade scroll drop - tier based on floor level
                floor_level = player_character.z
                if floor_level >= 25:
                    scroll_name = "Scroll of Divine Upgrade"
                    scroll_desc = "The ultimate scroll of enhancement, forged in celestial fire."
                    scroll_effect = "Upgrade items to +20 maximum."
                    scroll_value = 1200
                    scroll_level = 25
                elif floor_level >= 20:
                    scroll_name = "Scroll of Mythic Upgrade"
                    scroll_desc = "A scroll touched by the gods themselves."
                    scroll_effect = "Upgrade items to +17 maximum."
                    scroll_value = 850
                    scroll_level = 20
                elif floor_level >= 15:
                    scroll_name = "Scroll of Epic Upgrade"
                    scroll_desc = "A legendary scroll pulsing with raw power."
                    scroll_effect = "Upgrade items to +14 maximum."
                    scroll_value = 600
                    scroll_level = 15
                elif floor_level >= 10:
                    scroll_name = "Scroll of Superior Upgrade"
                    scroll_desc = "An ancient scroll that can enhance a weapon or armor up to +10."
                    scroll_effect = "Upgrade items to +10 maximum."
                    scroll_value = 400
                    scroll_level = 10
                elif floor_level >= 5:
                    scroll_name = "Scroll of Greater Upgrade"
                    scroll_desc = "A powerful scroll that can enhance a weapon or armor up to +6."
                    scroll_effect = "Upgrade items to +6 maximum."
                    scroll_value = 250
                    scroll_level = 5
                else:
                    scroll_name = "Scroll of Upgrade"
                    scroll_desc = "A mystical scroll that can enhance a weapon or armor up to +3."
                    scroll_effect = "Upgrade items to +3 maximum."
                    scroll_value = 150
                    scroll_level = 1
                
                upgrade_scroll = Scroll(
                    name=scroll_name,
                    description=scroll_desc,
                    effect_description=scroll_effect,
                    value=scroll_value,
                    level=scroll_level,
                    scroll_type='upgrade'
                )
                player_character.inventory.add_item(upgrade_scroll)
                add_log(f"{COLOR_PURPLE}You found a {get_item_display_name(upgrade_scroll)}!{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}{scroll_effect}{COLOR_RESET}")
                
                gs.game_stats['chests_opened'] = gs.game_stats.get('chests_opened', 0) + 1
                
                # QUEST TRACKING: Rune of Treasure
                if not gs.runes_obtained['treasure']:
                    gs.rune_progress['chests_opened_total'] += 1
                    if gs.rune_progress['chests_opened_total'] >= gs.rune_progress_reqs['chests_opened_total'] and not gs.legendary_chest_available:
                        gs.legendary_chest_available = True
                        add_log(f"{COLOR_PURPLE}The treasure gods smile upon you! A Legendary Chest awaits discovery.{COLOR_RESET}")
                
                check_achievements(player_character)

            # 30% chance to also find a potion in any non-trap, non-empty chest
            if selected_item_np not in ('gas', 'boom', 'empty') and random.random() < 0.30:
                potion = get_random_potion(player_character.z)
                player_character.inventory.add_item(potion)
                add_log(f"{COLOR_CYAN}You also found a {get_item_display_name(potion)} tucked inside!{COLOR_RESET}")

        room.room_type = '.'
        _trigger_room_interaction(player_character, my_tower)

    elif cmd in ['n', 's', 'e', 'w']:
        moved = move_player(player_character, my_tower, cmd)
        if not moved:
            gs.prompt_cntl = "chest_mode"

    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    else:
        add_log("Invalid command. 'o' to open, move keys to leave.")

def get_player_title(player_character):
    """
    Determines the player's title based on their stats, level, and accomplishments.
    Returns the most prestigious title they've earned.
    """
    titles = []

    # COMBAT TITLES (based on kills and strength)
    kills = gs.game_stats.get('monsters_killed', 0)
    if kills >= 100 and player_character.strength >= 20:
        titles.append(("The Legendary Warlord", 100))
    elif kills >= 50 and player_character.strength >= 15:
        titles.append(("The Warlord", 80))
    elif kills >= 25 and player_character.strength >= 12:
        titles.append(("The Warrior", 60))
    elif kills >= 10 and player_character.strength >= 10:
        titles.append(("The Fighter", 40))

    # EXPLORATION TITLES (based on floors and chests)
    max_floor = gs.game_stats.get('max_floor_reached', 0)
    chests = gs.game_stats.get('chests_opened', 0)
    if max_floor >= 10 and player_character.intelligence >= 20:
        titles.append(("The Wise Explorer", 95))
    elif max_floor >= 10 and chests >= 15:
        titles.append(("The Master Explorer", 85))
    elif max_floor >= 7 and chests >= 10:
        titles.append(("The Explorer", 65))
    elif max_floor >= 5:
        titles.append(("The Adventurer", 45))

    # MAGIC TITLES (based on spells and intelligence)
    spells_learned = gs.game_stats.get('spells_learned', 0)
    spells_cast = gs.game_stats.get('spells_cast', 0)
    if spells_learned >= 10 and player_character.intelligence >= 20:
        titles.append(("The Archmage", 100))
    elif spells_learned >= 5 and spells_cast >= 50:
        titles.append(("The Sorcerer", 75))
    elif spells_learned >= 3 and player_character.intelligence >= 15:
        titles.append(("The Mage", 55))
    elif spells_learned >= 1:
        titles.append(("The Apprentice", 35))

    # SURVIVAL TITLES (based on level and diverse stats)
    if player_character.level >= 10 and player_character.dexterity >= 18:
        titles.append(("The Nimble Champion", 90))
    elif player_character.level >= 8 and player_character.dexterity >= 15:
        titles.append(("The Swift Hero", 70))
    elif player_character.level >= 5:
        titles.append(("The Hero", 50))

    # WEALTH TITLES (based on gold collected)
    gold_collected = gs.game_stats.get('total_gold_collected', 0)
    if gold_collected >= 5000:
        titles.append(("The Wealthy", 85))
    elif gold_collected >= 2000:
        titles.append(("The Prosperous", 65))
    elif gold_collected >= 1000:
        titles.append(("The Fortunate", 45))

    # SPECIAL ACHIEVEMENT TITLES
    if gs.game_stats.get('flawless_floors', 0) >= 1:
        titles.append(("The Untouchable", 95))
    if gs.game_stats.get('defeated_higher_level', 0) >= 3:
        titles.append(("The Giant Slayer", 90))
    if gs.game_stats.get('altars_used', 0) >= 7:
        titles.append(("The Blessed", 80))
    if gs.game_stats.get('spell_backfires', 0) >= 5:
        titles.append(("The Reckless", 60))
    if gs.game_stats.get('kills_no_armor', 0) >= 5:
        titles.append(("The Fearless", 75))

    # HYBRID TITLES (multiple high stats)
    if player_character.strength >= 18 and player_character.intelligence >= 18:
        titles.append(("The Battle Sage", 95))
    if player_character.strength >= 15 and player_character.dexterity >= 15:
        titles.append(("The Blade Master", 85))
    if player_character.dexterity >= 18 and player_character.intelligence >= 18:
        titles.append(("The Shadow Sage", 90))

    # STAT MASTERY TITLES (single stat focus)
    if player_character.strength >= 25:
        titles.append(("The Titan", 95))
    if player_character.dexterity >= 25:
        titles.append(("The Wind", 95))
    if player_character.intelligence >= 25:
        titles.append(("The Genius", 95))

    # LEVEL-BASED TITLES (fallback)
    if player_character.level >= 15:
        titles.append(("The Legend", 80))
    elif player_character.level >= 10:
        titles.append(("The Champion", 60))
    elif player_character.level >= 5:
        titles.append(("The Brave", 40))

    # Default title if nothing else qualifies
    if not titles:
        titles.append(("The Novice", 10))

    # Sort by prestige (second element) and return the highest
    titles.sort(key=lambda x: x[1], reverse=True)
    return titles[0][0]




# 21. CHARACTER CREATION
# --------------------------------------------------------------------------------

def create_player_character(my_tower, player_character, _cntl, cmd):

        # Define available classes, races, and genders with base stats/modifiers
    character_races = {
        'human': {'health_mod': 0, 'attack_mod': 0, 'defense_mod': 0, 'strength_mod': 0, 'dexterity_mod': 0, 'intelligence_mod': 0},
        'elf': {'health_mod': -10, 'attack_mod': 1, 'defense_mod': -1, 'strength_mod': -1, 'dexterity_mod': 2, 'intelligence_mod': 2},
        'dwarf': {'health_mod': 20, 'attack_mod': 2, 'defense_mod': 2, 'strength_mod': 2, 'dexterity_mod': -2, 'intelligence_mod': -2}
    }

    character_genders = {
        'male': {'attack_mod': 0, 'defense_mod': 0},
        'female': {'attack_mod': 0, 'defense_mod': 0},
        'non-binary': {'attack_mod': 0, 'defense_mod': 0}
    }

    # Base stats for the 'Hero' class (since there's only one class now)
    base_stats = {'health': 100, 'attack': 15, 'defense': 5, 'strength': 10, 'dexterity': 10, 'intelligence': 10}

    # The set_player_helper function was not being called and is redundant.
    # Its logic will be directly integrated into the _cntl == "player_gender" block.

    if _cntl == "player_name":
        player_character.name = cmd.title()

        # Check for playtest mode
        if cmd.lower() == "tourist":
            add_log(f"{COLOR_PURPLE}Tourist detected! Activating playtest mode...{COLOR_RESET}")
            # Set defaults for quick testing
            player_character.race = 'human'
            player_character.gender = 'non-binary'
            player_character.character_class = "Playtester"

            gs.PLAYTEST = True;

            # Apply base stats (will be boosted in playtest mode)
            stats = {
                'health': 100,
                'attack': 15,
                'defense': 5,
                'strength': 10,
                'dexterity': 10,
                'intelligence': 10
            }

            player_character.health = stats['health']
            player_character._base_attack = stats['attack']
            player_character._base_defense = stats['defense']
            player_character.strength = stats['strength']
            player_character.dexterity = stats['dexterity']
            player_character.intelligence = stats['intelligence']

            # Activate playtest mode
            activate_playtest_mode(player_character)

            # Skip to game start
            gs.prompt_cntl = "game_loop"
            add_log(f"{COLOR_GREEN}Playtest mode ready! Press a movement key to begin.{COLOR_RESET}")
            return True

        # Don't add prompts to log - they're in the HTML now
        gs.prompt_cntl = "player_race"
        return True

    if _cntl == "player_race":
       race_choice = cmd.lower()
       if race_choice == 'h':
          player_character.race = 'human'
       elif race_choice == 'e':
          player_character.race = 'elf'
       elif race_choice == 'd':
          player_character.race = 'dwarf'
       else:
            add_log("Invalid race choice. Please enter H, E, or D.")
            return True
       # Don't add prompts to log - they're in the HTML now
       gs.prompt_cntl = "player_gender"
       return True

    if _cntl == "player_gender":
        gender_choice = cmd.lower()
        if gender_choice == 'm':
            player_character.gender = 'male'
        elif gender_choice == 'f':
            player_character.gender = 'female'
        elif gender_choice == 'n':
            player_character.gender = 'non-binary'
        else:
            add_log("Invalid gender choice. Please enter M, F, or N.")
            return True
        add_log(f"I see you're in your {player_character.gender} era.")


        # Apply base stats
        stats = base_stats.copy()

        # Apply race modifiers using player_character.race
        race_mods = character_races[player_character.race]
        stats['health'] += race_mods.get('health_mod', 0)
        stats['attack'] += race_mods.get('attack_mod', 0)
        stats['defense'] += race_mods.get('defense_mod', 0)
        stats['strength'] += race_mods.get('strength_mod', 0)
        stats['dexterity'] += race_mods.get('dexterity_mod', 0)
        stats['intelligence'] += race_mods.get('intelligence_mod', 0)

        # Apply gender modifiers using player_character.gender
        gender_mods = character_genders[player_character.gender]
        stats['attack'] += gender_mods.get('attack_mod', 0)
        stats['defense'] += gender_mods.get('defense_mod', 0)

        # Update player_character's attributes directly instead of creating a new object
        player_character.health = stats['health']
        player_character._base_attack = stats['attack']
        player_character._base_defense = stats['defense']
        player_character.strength = stats['strength']
        player_character.dexterity = stats['dexterity']
        player_character.intelligence = stats['intelligence']
        player_character.character_class = "Adventurer"
        # player_character.race and player_character.gender are already set correctly

        gs.prompt_cntl = "starting_shop"
        handle_starting_shop(player_character, my_tower, "init")
        return True
    return False # Should not be reached if state is managed
def activate_playtest_mode(player_character):
    """
    Activate playtest mode with boosted stats and ALL available items for testing.
    Gives the player one of each weapon, armor, spell, scroll, potion, and treasure.
    """
    add_log(f"{COLOR_YELLOW}========================================{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}     gs.PLAYTEST MODE ACTIVATED!          {COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}========================================{COLOR_RESET}")

    # Boost stats significantly
    player_character.health = 9999
    player_character._base_attack = 50
    player_character._base_defense = 50
    player_character.strength = 30
    player_character.dexterity = 30
    player_character.intelligence = 30
    player_character.level = 10
    player_character.experience = 10000
    player_character.gold = 99999
    player_character.mana = 999
    player_character._max_mana = 999

    add_log(f"{COLOR_GREEN}Stats maxed out for testing!{COLOR_RESET}")
    add_log(f"{COLOR_GREEN}HP: 9999, Mana: 999, Gold: 99999{COLOR_RESET}")

    # Add powerful starting equipment (equipped)
    playtest_weapon = Weapon(
        name="Playtest Sword",
        description="An infinitely powerful testing weapon",
        attack_bonus=100,
        value=1,
        level=10,
        upgrade_level=10,
        elemental_strength=['Fire', 'Ice', 'Lightning'],
        upgrade_limit=False
    )
    player_character.inventory.add_item(playtest_weapon)
    player_character.equipped_weapon = playtest_weapon

    playtest_armor = Armor(
        name="Playtest Armor",
        description="Impenetrable testing armor",
        defense_bonus=100,
        value=1,
        level=10,
        upgrade_level=10,
        elemental_strength=['Fire', 'Ice', 'Lightning'],
        upgrade_limit=False
    )
    player_character.inventory.add_item(playtest_armor)
    player_character.equipped_armor = playtest_armor

    # Add ALL weapons from templates
    add_log(f"{COLOR_CYAN}Adding all weapons...{COLOR_RESET}")
    for weapon_template in WEAPON_TEMPLATES:
        try:
            weapon_copy = Weapon(
                name=weapon_template.name,
                description=weapon_template.description,
                attack_bonus=weapon_template.attack_bonus,
                value=weapon_template.value,
                level=weapon_template.level,
                upgrade_level=weapon_template.upgrade_level,
                elemental_strength=list(weapon_template.elemental_strength) if weapon_template.elemental_strength else [],
                upgrade_limit=weapon_template.upgrade_limit
            )
            player_character.inventory.add_item(weapon_copy)
        except Exception as e:
            add_log(f"{COLOR_RED}Error adding weapon: {e}{COLOR_RESET}")

    # Add ALL armors from templates
    add_log(f"{COLOR_CYAN}Adding all armor...{COLOR_RESET}")
    for armor_template in ARMOR_TEMPLATES:
        try:
            armor_copy = Armor(
                name=armor_template.name,
                description=armor_template.description,
                defense_bonus=armor_template.defense_bonus,
                value=armor_template.value,
                level=armor_template.level,
                upgrade_level=armor_template.upgrade_level,
                elemental_strength=list(armor_template.elemental_strength) if armor_template.elemental_strength else [],
                upgrade_limit=armor_template.upgrade_limit
            )
            player_character.inventory.add_item(armor_copy)
        except Exception as e:
            add_log(f"{COLOR_RED}Error adding armor: {e}{COLOR_RESET}")

    # Add ALL spells and memorize them
    add_log(f"{COLOR_CYAN}Adding and memorizing all spells...{COLOR_RESET}")
    for spell_template in SPELL_TEMPLATES:
        try:
            spell_copy = Spell(
                name=spell_template.name,
                description=spell_template.description,
                mana_cost=spell_template.mana_cost,
                damage_type=spell_template.damage_type,
                base_power=spell_template.base_power,
                level=spell_template.level,
                spell_type=spell_template.spell_type,
                status_effect_name=spell_template.status_effect_name,
                status_effect_duration=spell_template.status_effect_duration,
                status_effect_type=spell_template.status_effect_type,
                status_effect_magnitude=spell_template.status_effect_magnitude
            )
            player_character.inventory.add_item(spell_copy)
            player_character.memorize_spell(spell_copy)
        except Exception as e:
            add_log(f"{COLOR_RED}Error adding spell: {e}{COLOR_RESET}")

    # Add ALL potions from templates
    add_log(f"{COLOR_CYAN}Adding all potions...{COLOR_RESET}")
    for potion_template in POTION_TEMPLATES:
        try:
            # Create multiple copies of each potion for testing
            for _ in range(3):
                potion_copy = Potion(
                    name=potion_template.name,
                    description=potion_template.description,
                    value=potion_template.value,
                    level=potion_template.level,
                    potion_type=potion_template.potion_type,
                    effect_magnitude=potion_template.effect_magnitude,
                    duration=getattr(potion_template, 'duration', 0),
                    resistance_element=getattr(potion_template, 'resistance_element', None)
                )
                player_character.inventory.add_item(potion_copy)
        except Exception as e:
            add_log(f"{COLOR_RED}Error adding potion {potion_template.name}: {e}{COLOR_RESET}")

    # Add useful scrolls
    add_log(f"{COLOR_CYAN}Adding scrolls...{COLOR_RESET}")
    for _ in range(5):
        player_character.inventory.add_item(Scroll(
            name="Scroll of Mapping",
            description="Reveals entire floor",
            effect_description="Reveals the entire current floor layout.",
            value=120,
            level=2,
            scroll_type='mapping'
        ))
        player_character.inventory.add_item(Scroll(
            name="Scroll of Upgrade",
            description="Enhances equipment",
            effect_description="Permanently increases an item's upgrade level.",
            value=100,
            level=2,
            scroll_type='upgrade'
        ))
        player_character.inventory.add_item(Scroll(
            name="Scroll of Teleportation",
            description="Teleport to random location",
            effect_description="Instantly teleport to a random safe location.",
            value=100,
            level=2,
            scroll_type='teleport'
        ))

    # Add lantern with lots of fuel
    lantern = Lantern(
        name="Infinite Lantern",
        description="A lantern that never dims",
        fuel_amount=999,
        light_radius=10,
        value=1,
        level=0,
        upgrade_level=5
    )
    player_character.inventory.add_item(lantern)

    # Add lantern fuel
    for _ in range(20):
        player_character.inventory.add_item(LanternFuel(
            name="Lantern Fuel",
            description="Refills lantern",
            value=5,
            level=0,
            fuel_restore_amount=50
        ))

    # Add ALL treasures (includes unique treasures and minor treasures)
    add_log(f"{COLOR_CYAN}Adding all treasures...{COLOR_RESET}")
    for treasure_template in TREASURE_TEMPLATES:
        try:
            # Create a copy of the treasure
            treasure_copy = Treasure(
                name=treasure_template.name,
                description=treasure_template.description,
                gold_value=getattr(treasure_template, 'gold_value', 0),
                value=treasure_template.value,
                level=treasure_template.level,
                treasure_type=getattr(treasure_template, 'treasure_type', 'passive'),
                is_unique=getattr(treasure_template, 'is_unique', False),
                use_effect=getattr(treasure_template, 'use_effect', None),
                passive_effect=getattr(treasure_template, 'passive_effect', ''),
                benefit=getattr(treasure_template, 'benefit', {})
            )
            player_character.inventory.add_item(treasure_copy)
        except Exception as e:
            add_log(f"{COLOR_RED}Error adding treasure {treasure_template.name}: {e}{COLOR_RESET}")

    # Add ALL unique weapons
    add_log(f"{COLOR_CYAN}Adding all unique weapons...{COLOR_RESET}")
    for weapon_template in UNIQUE_WEAPON_TEMPLATES:
        try:
            weapon_copy = Weapon(
                name=weapon_template.name,
                description=weapon_template.description,
                attack_bonus=weapon_template.attack_bonus,
                value=weapon_template.value,
                level=weapon_template.level,
                upgrade_level=weapon_template.upgrade_level,
                elemental_strength=list(weapon_template.elemental_strength) if weapon_template.elemental_strength else [],
                upgrade_limit=weapon_template.upgrade_limit
            )
            player_character.inventory.add_item(weapon_copy)
        except Exception as e:
            add_log(f"{COLOR_RED}Error adding unique weapon: {e}{COLOR_RESET}")

    # Add ALL unique armors
    add_log(f"{COLOR_CYAN}Adding all unique armors...{COLOR_RESET}")
    for armor_template in UNIQUE_ARMOR_TEMPLATES:
        try:
            armor_copy = Armor(
                name=armor_template.name,
                description=armor_template.description,
                defense_bonus=armor_template.defense_bonus,
                value=armor_template.value,
                level=armor_template.level,
                upgrade_level=armor_template.upgrade_level,
                elemental_strength=list(armor_template.elemental_strength) if armor_template.elemental_strength else [],
                upgrade_limit=armor_template.upgrade_limit
            )
            player_character.inventory.add_item(armor_copy)
        except Exception as e:
            add_log(f"{COLOR_RED}Error adding unique armor: {e}{COLOR_RESET}")

    # Add Zot's Dimensional Key (Zotle puzzle reward)
    add_log(f"{COLOR_CYAN}Adding Zot's Dimensional Key...{COLOR_RESET}")
    teleporter = Treasure(
        name="Zot's Dimensional Key",
        description="A mystical key that bends space itself. Teleport to any location in the dungeon by entering x,y,z coordinates. Warning: Cannot teleport into walls!",
        gold_value=0,
        value=5000,
        level=10,
        treasure_type='usable',
        is_unique=True,
        use_effect=use_zotle_teleporter,
        benefit={'special': 'Teleport to any coordinate in the dungeon'}
    )
    player_character.inventory.add_item(teleporter)
    # Mark puzzle as solved so it doesn't spawn
    if gs.zotle_puzzle:
        gs.zotle_puzzle['solved'] = True

    # Count items added
    total_items = len(player_character.inventory.items)
    total_spells = len(player_character.memorized_spells)
    
    # PLAYTEST: Identify ALL items so tester can see real names
    add_log(f"{COLOR_CYAN}Identifying all items for testing...{COLOR_RESET}")
    for item in player_character.inventory.items:
        identify_item(item, silent=True)
    # Also identify all template items globally
    for potion in POTION_TEMPLATES:
        gs.identified_items.add(potion.name)
    for scroll in SCROLL_TEMPLATES:
        gs.identified_items.add(scroll.name)
    for weapon in WEAPON_TEMPLATES:
        gs.identified_items.add(weapon.name)
    for armor in ARMOR_TEMPLATES:
        gs.identified_items.add(armor.name)

    add_log(f"{COLOR_GREEN}========================================{COLOR_RESET}")
    add_log(f"{COLOR_GREEN}Total items in inventory: {total_items}{COLOR_RESET}")
    add_log(f"{COLOR_GREEN}Total spells memorized: {total_spells}{COLOR_RESET}")
    add_log(f"{COLOR_GREEN}All items identified for testing!{COLOR_RESET}")
    add_log(f"{COLOR_GREEN}========================================{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}[gs.PLAYTEST] Vaults spawn on EVERY floor{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}[gs.PLAYTEST] Zotle puzzles spawn on EVERY floor{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}[gs.PLAYTEST] Fey Gardens spawn on floors 5+{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}Happy testing, TOURIST! {COLOR_RESET}")



def _trigger_shrinking_spell(player_character):
    """Trigger Zot's shrinking spell when player enters a bug level."""
    gs.player_is_shrunk = True
    gs.bug_queen_defeated = False

    # Add the shrinking status effect (very long duration - effectively permanent until cured)
    player_character.add_status_effect(
        effect_name='Shrinking',
        duration=999,
        effect_type='shrinking',
        magnitude=0,
        description="Zot's shrinking spell - you are tiny!"
    )

    add_log("")
    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
    add_log(f"{COLOR_RED}*** ZOT'S SHRINKING SPELL ***{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}A cackling voice echoes through the chamber:{COLOR_RESET}")
    add_log(f'{COLOR_CYAN}"HAHAHAHA! You thought you could just waltz through MY tower?"{COLOR_RESET}')
    add_log(f'{COLOR_CYAN}"Let us see how brave you are when you are the size of a BUG!"{COLOR_RESET}')
    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
    add_log(f"{COLOR_RED}Arcane energy crackles around you!{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}The world grows larger... no, YOU are growing smaller!{COLOR_RESET}")
    add_log(f"{COLOR_RED}You shrink to the size of an insect!{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")

    # Unequip all gear - nothing fits at insect size!
    gear_dropped = False
    if player_character.equipped_weapon:
        wep_name = player_character.equipped_weapon.name
        player_character.equipped_weapon = None
        add_log(f"{COLOR_YELLOW}Your {wep_name} clatters to the ground, now bigger than you are!{COLOR_RESET}")
        gear_dropped = True
    if player_character.equipped_armor:
        arm_name = player_character.equipped_armor.name
        player_character.equipped_armor = None
        add_log(f"{COLOR_YELLOW}You tumble out of your {arm_name} like a pea from a pod!{COLOR_RESET}")
        gear_dropped = True
    for slot in range(4):
        if player_character.equipped_accessories[slot] is not None:
            acc = player_character.equipped_accessories[slot]
            player_character._remove_accessory_bonuses(acc)
            acc.is_equipped = False
            player_character.equipped_accessories[slot] = None
            add_log(f"{COLOR_YELLOW}Your {acc.name} slips off - it's enormous now!{COLOR_RESET}")
            gear_dropped = True
    if gear_dropped:
        add_log(f"{COLOR_RED}None of your gear fits anymore! You'll need to find bug-sized equipment!{COLOR_RESET}")
    else:
        add_log(f"{COLOR_RED}Good thing you weren't wearing much - nothing would fit now!{COLOR_RESET}")

    add_log(f"{COLOR_YELLOW}The bugs on this floor now tower over you!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Find and defeat the Bug Queen or find a Growth Mushroom{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}to restore your size and escape this floor!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Look for bug merchants to find gear that fits!{COLOR_RESET}")
    add_log(f"{COLOR_RED}The stairs are sealed by Zot's magic while you are shrunk!{COLOR_RESET}")
    add_log("")


def handle_stairs_up(player_character, my_tower, floor_params):
    interacted_this_turn = False
    print_to_output("You found a passage leading back up toward the entrance.")
    if player_character.z == 0:
        print_to_output("You are at the entrance...")
        return player_character.x, player_character.y, False, False

    player_character.z -= 1  # Going up now means back to previous depth
    print_to_output(f"Ascending toward entrance. Depth {player_character.z + 1}!")
    current_floor = my_tower.floors[player_character.z]
    # Find the 'D' room on the new floor to place the character
    found_d = False
    for r_idx, row in enumerate(current_floor.grid):
            for c_idx, room in enumerate(row):
                if room.room_type == 'D': # Now looking for 'D' for descending stairs
                    player_character.y = r_idx # Corrected: row is y-coordinate
                    player_character.x = c_idx # Corrected: column is x-coordinate
                    current_floor.grid[r_idx][c_idx].discovered = True # Mark the 'D' room as discovered
                    found_d = True
                    break
            if found_d:
                break
    reveal_adjacent_walls(player_character, my_tower)
    _trigger_room_interaction(player_character, my_tower) # Trigger room interaction for the new room
    interacted_this_turn = True
    print_to_output(f"You arrive at ({player_character.x}, {player_character.y}) on Depth {player_character.z + 1}.")
    return player_character.x, player_character.y, False, interacted_this_turn # False for gs.game_should_quit

def handle_stairs_down(player_character, my_tower, floor_params):
    interacted_this_turn = False
    print_to_output("You found a passage leading down!")

    player_character.z += 1
    while len(my_tower.floors) <= player_character.z:
        my_tower.add_floor(**gs.floor_params)  # Generate new deeper floor

    print_to_output(f"Descending deeper! Depth {player_character.z + 1}!")

    current_floor = my_tower.floors[player_character.z]
    # Find the 'U' room on the previous floor to place the character
    found_u = False
    for r_idx, row in enumerate(current_floor.grid):
        for c_idx, room in enumerate(row):
            if room.room_type == 'U': # Now looking for 'U' for ascending stairs
                player_character.y = r_idx # Corrected: row is y-coordinate
                player_character.x = c_idx # Corrected: column is x-coordinate
                current_floor.grid[r_idx][c_idx].discovered = True # Mark the 'U' room as discovered
                found_u = True
                break
        if found_u:
            break
    reveal_adjacent_walls(player_character, my_tower)

    # Check if we just entered a bug level - trigger Zot's shrinking spell
    current_floor = my_tower.floors[player_character.z]
    if current_floor.properties.get('is_bug_level') and not gs.player_is_shrunk:
        _trigger_shrinking_spell(player_character)

    _trigger_room_interaction(player_character, my_tower) # Trigger room interaction for the new room
    interacted_this_turn = True
    print_to_output(f"You arrive at ({player_character.x}, {player_character.y}) on Depth {player_character.z + 1}.")
    return player_character.x, player_character.y, False, interacted_this_turn # False for gs.game_should_quit

def handle_warp_room(current_x, current_y, current_room, game_should_quit, my_tower, player_character, floor_params):
    """
    Handles interaction when player enters a 'W' (Warp) room.

    Args:
        current_x (int): The current row coordinate of the player.
        current_y (int): The current column coordinate of the player.
        current_room (Room): The Room object the player is currently in.
        grid_size (int): The size of one dimension of the square grid.
        gs.game_should_quit (bool): Flag to indicate if the game should quit.
        my_tower (Tower): The Tower object.
        player_character (Character): The player's character object.
        specified_chars (list): List of specified room characters.
        required_chars (list): List of required room characters.

    Returns:
        tuple: (updated_x, updated_y, gs.game_should_quit, interacted_this_turn)
    """
    interacted_this_turn = False
    print_to_output("A swirling portal shimmers before you!")

    # Calculate evasion chance based on intelligence
    evasion_chance = 0.20 + (player_character.intelligence * 0.02) # Base 20% + 2% per intelligence point
    evasion_chance = min(1.0, evasion_chance) # Cap at 100%

    if random.random() < evasion_chance:
        print_to_output(f"{COLOR_GREEN}Your keen intellect allows you to resist the portal's pull! You manage to avoid being warped.{COLOR_RESET}")
        # No movement or turn consumed specific to the warp, player can move normally.
        # This means the game loop will ask for input again.
    else:
        print_to_output(f"{COLOR_RED}The portal's power overwhelms you! You are sucked in...{COLOR_RESET}")

        # Determine new floor (within +/- 2 floors)
        min_z = max(0, player_character.z - 2)
        max_z = player_character.z + 2

        # Ensure max_z does not exceed newly generated floor (if any) to prevent errors
        # This might require generating floors up to max_z if they don't exist.
        while len(my_tower.floors) <= max_z:
            # When generating new floors due to warp, use the standard required_chars including 'D', 'U', 'V'
            my_tower.add_floor(**gs.floor_params)

        new_z = random.randint(min_z, max_z)
        player_character.z = new_z

        # Determine new (x,y) on the new floor
        #work to do here
        #check if not wall
        while True:
          new_x = random.randint(0, my_tower.floors[player_character.z].rows - 1)
          new_y = random.randint(0, my_tower.floors[player_character.z].cols - 1)
          current_room = my_tower.floors[player_character.z].grid[new_x][new_y]
          current_room_type = current_room.room_type
          if is_wall_at_coordinate(my_tower.floors[player_character.z], new_x, new_y) or current_room_type=='W':
            continue
          else:
            break

        player_character.x = new_x
        player_character.y = new_y

        # Check if we warped into a bug level - trigger shrinking spell
        warp_target_floor = my_tower.floors[player_character.z]
        if warp_target_floor.properties.get('is_bug_level') and not gs.player_is_shrunk:
            _trigger_shrinking_spell(player_character)

        print_to_output(f"You emerge disoriented in a new room at ({player_character.x}, {player_character.y}) on Depth {player_character.z + 1}!")
        interacted_this_turn = True # A turn was definitely consumed by warping

    return player_character.x, player_character.y, gs.game_should_quit, interacted_this_turn



def process_stairs_up_action(player_character, my_tower, cmd, floor_params_ref):

    if cmd == "init":
        if gs.player_is_shrunk:
            add_log(f"{COLOR_YELLOW}You see stairs leading upwards, but each step is a cliff face at your size!{COLOR_RESET}")
            add_log(f"{COLOR_RED}Zot's shrinking spell prevents you from leaving! Defeat the Bug Queen or find a Growth Mushroom!{COLOR_RESET}")
        else:
            add_log("You see stairs leading upwards. Press 'u' to ascend.")
        return

    if cmd == 'u':
        if gs.player_is_shrunk:
            add_log(f"{COLOR_RED}You try to climb but the stairs are impossibly tall! You need to break the shrinking spell first!{COLOR_RESET}")
            return
        add_log("You begin to climb the stairs.")
        ch_x, ch_y, game_quit, interacted = handle_stairs_up(player_character, my_tower, floor_params_ref)
        if game_quit:
            gs.game_should_quit = True
        # prompt_cntl is now handled by _trigger_room_interaction within handle_stairs_up
    elif cmd == 'i':
        gs.previous_prompt_cntl = "stairs_up_mode" # Save state to return to stairs_up_mode after inventory
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd in ['n', 's', 'e', 'w']:
        # Allow normal movement away from stairs
        move_player(player_character, my_tower, cmd)
    elif cmd == 'l':
        # Allow lantern use
        process_lantern_quick_use(player_character, my_tower)

def process_stairs_down_action(player_character, my_tower, cmd):

    if cmd == "init":
        if gs.player_is_shrunk:
            add_log(f"{COLOR_YELLOW}You see stairs leading downwards, but each step is a deadly drop at your size!{COLOR_RESET}")
            add_log(f"{COLOR_RED}Zot's shrinking spell prevents you from leaving! Defeat the Bug Queen or find a Growth Mushroom!{COLOR_RESET}")
            return
        # Check if this is floor 49 (the gate to floor 50)
        if player_character.z == 48:  # 0-indexed, floor 48 is the 49th floor
            if gs.gate_to_floor_50_unlocked:
                add_log(f"{COLOR_PURPLE}The Gate to Floor 50 stands before you, glowing with immense power!{COLOR_RESET}")
                add_log(f"{COLOR_RED}Press 'd' to descend and face Zot's Guardian!{COLOR_RESET}")
            else:
                shards_count = sum(gs.shards_obtained.values())
                add_log(f"{COLOR_YELLOW}The stairs are sealed by powerful magic!{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}You have {shards_count}/8 Shards of Power.{COLOR_RESET}")
                add_log(f"{COLOR_YELLOW}Obtain all 8 shards to unlock the Gate to Floor 50!{COLOR_RESET}")
        else:
            add_log("You see stairs leading downwards. Press 'd' to descend.")
        return

    if cmd == 'd':
        if gs.player_is_shrunk:
            add_log(f"{COLOR_RED}You peer over the edge but the drop is lethal at your size! Break the shrinking spell first!{COLOR_RESET}")
            return
        # Check if trying to descend from floor 49 without all shards
        if player_character.z == 48 and not gs.gate_to_floor_50_unlocked:
            add_log(f"{COLOR_RED}The gate remains sealed! You need all 8 Shards of Power!{COLOR_RESET}")
            return
        
        add_log("You begin to descend the stairs.")
        ch_x, ch_y, game_quit, interacted = handle_stairs_down(player_character, my_tower, gs.floor_params) # Removed move_player
        if game_quit:
            gs.game_should_quit = True
        # prompt_cntl is now handled by _trigger_room_interaction within handle_stairs_down
    elif cmd == 'i':
        gs.previous_prompt_cntl = "stairs_down_mode" # Save state to return to stairs_down_mode after inventory
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd in ['n', 's', 'e', 'w']:
        # Allow normal movement away from stairs
        move_player(player_character, my_tower, cmd)
    elif cmd == 'l':
        # Allow lantern use
        process_lantern_quick_use(player_character, my_tower)


def _handle(my_tower, player_character, cmd):

  if gs.prompt_cntl == "intro_story" or gs.prompt_cntl == "main_menu":
    # Check if player wants to load a save
    if cmd in ['1', '2', '3']:
        slot = int(cmd)
        if SaveSystem.save_exists(slot):
            loaded_player, loaded_tower = SaveSystem.load_game(slot)
            if loaded_player and loaded_tower:
                gs._pending_load = (loaded_player, loaded_tower)
                gs.prompt_cntl = "game_loaded_summary"  # Changed from "load_pending"
                return True
            else:
                add_log(f"{COLOR_RED}Failed to load!{COLOR_RESET}")
        else:
            add_log(f"{COLOR_YELLOW}No save in slot {slot}{COLOR_RESET}")
        return True
    # Otherwise start new game
    gs.log_lines.clear()
    gs.prompt_cntl = "player_name"
    return True
  if gs.prompt_cntl == "player_name":
    return create_player_character(my_tower, player_character, gs.prompt_cntl, cmd)
  elif gs.prompt_cntl == "player_race":
    return create_player_character(my_tower, player_character, gs.prompt_cntl, cmd)
  elif gs.prompt_cntl == "player_gender":
    return create_player_character(my_tower, player_character, gs.prompt_cntl, cmd)
  elif gs.prompt_cntl == "starting_shop":
    return handle_starting_shop(player_character, my_tower, cmd)
  elif gs.prompt_cntl == "stairs_up_mode":
      process_stairs_up_action(player_character, my_tower, cmd, gs.floor_params) # Pass gs.floor_params here
      return True # Indicates the command was handled
  elif gs.prompt_cntl == "stairs_down_mode": # New state for stairs down
      process_stairs_down_action(player_character, my_tower, cmd)
      return True # Indicates the command was handled
  elif gs.prompt_cntl == "warp_mode":
      process_warp_action(player_character, my_tower, cmd, gs.floor_params) # Pass gs.floor_params here
      return True # Indicates the command was handled
  elif gs.prompt_cntl == "altar_mode":
      process_altar_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "pool_mode":
      process_pool_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "dungeon_mode":
      process_dungeon_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "dungeon_unlocked_mode":
      process_dungeon_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "tomb_mode":
      process_tomb_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "garden_mode" or gs.prompt_cntl == "fey_garden_mode":
      process_garden_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "oracle_mode":
      process_oracle_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "blacksmith_mode":
      process_blacksmith_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "shrine_mode":
      process_shrine_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "alchemist_mode":
      process_alchemist_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "war_room_mode":
      process_war_room_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "taxidermist_mode":
      process_taxidermist_action(player_character, my_tower, cmd)
      return True
  elif gs.prompt_cntl == "towel_action_mode":
      process_towel_action(player_character, my_tower, cmd)
      return True
  else:
    return False
def health_bar(current, maximum, width=20):
    filled = int((current / maximum) * width) if maximum > 0 else 0
    filled = min(filled, width)  # Cap at width
    bar = "[" + "#" * filled + "-" * (width - filled) + "]"
    # Abbreviate large numbers to keep display compact
    if maximum >= 1000:
        cur_str = f"{current//1000}k" if current >= 1000 else str(current)
        max_str = f"{maximum//1000}k"
    else:
        cur_str = str(current)
        max_str = str(maximum)
    return f"{bar} {cur_str}/{max_str}"

def mana_bar(current, maximum, width=20):
    if maximum == 0:
        return " "
    filled = int((current / maximum) * width)
    filled = min(filled, width)  # Cap at width
    bar = "[" + "#" * filled + "-" * (width - filled) + "]"
    # Abbreviate large numbers to keep display compact
    if maximum >= 1000:
        cur_str = f"{current//1000}k" if current >= 1000 else str(current)
        max_str = f"{maximum//1000}k"
    else:
        cur_str = str(current)
        max_str = str(maximum)
    return f"{bar} {cur_str}/{max_str}"


def generate_damage_float_js(monster_name, monster_dmg, player_dmg, player_blocked=False,
                              player_status=None, monster_status=None, player_heal=0):
    """Generate floating damage/heal/status text above combat sprites.

    Injects absolutely-positioned divs into the sprite wrapper elements.
    Uses a JS-driven animation loop (requestAnimationFrame) so it works
    reliably in Toga/WKWebView without requiring <style> blocks in <body>.
    """
    monster_canvas_id = "ms_" + "".join(ch if ch.isalnum() else "_" for ch in monster_name)

    # --- Determine player text / color ---
    if player_dmg > 0:
        p_text = f"-{player_dmg}"
        p_color = "#FF5252"
    elif player_blocked:
        p_text = "Blocked"
        p_color = "#69F0AE"
    elif player_heal > 0:
        p_text = f"+{player_heal}"
        p_color = "#69F0AE"
    elif player_status:
        p_text = str(player_status).replace('"', '').replace("'", '').replace('<', '').replace('>', '')[:12]
        p_color = "#FFB74D"
    else:
        p_text = None
        p_color = None

    # --- Determine monster text / color ---
    if monster_dmg > 0:
        m_text = f"-{monster_dmg}"
        m_color = "#FF5252"
    elif monster_status:
        m_text = str(monster_status).replace('"', '').replace("'", '').replace('<', '').replace('>', '')[:12]
        m_color = "#FFB74D"
    else:
        m_text = None
        m_color = None

    # --- Secondary heal float (when player both heals AND takes damage) ---
    h_text = None
    h_color = None
    if player_heal > 0 and player_dmg > 0:
        h_text = f"+{player_heal}"
        h_color = "#69F0AE"

    # Nothing to show
    if m_text is None and p_text is None:
        return ""

    # Build JS calls for each float.  The showFloat function:
    #  1. Creates a div with all styles inline
    #  2. Appends it to the wrapper (which has position:relative)
    #  3. Animates it upward with fading via requestAnimationFrame
    #  4. delay_ms parameter staggers multiple notifications
    # -----------------------------------------------------------------
    # TUNING: Change FLOAT_DELAY_MS to adjust the gap (in milliseconds)
    #         between successive floating notifications.
    #         0 = all appear at once, 400 = 0.4s stagger, etc.
    # -----------------------------------------------------------------
    FLOAT_DELAY_MS = 400
    float_calls = []
    delay_idx = 0
    if m_text:
        float_calls.append(
            f'showFloat("{monster_canvas_id}_wrap","{m_text}","{m_color}",0,{delay_idx * FLOAT_DELAY_MS});'
        )
        delay_idx += 1
    if p_text:
        float_calls.append(
            f'showFloat("player_sprite_wrap","{p_text}","{p_color}",0,{delay_idx * FLOAT_DELAY_MS});'
        )
        delay_idx += 1
    if h_text:
        float_calls.append(
            f'showFloat("player_sprite_wrap","{h_text}","{h_color}",24,{delay_idx * FLOAT_DELAY_MS});'
        )

    js = (
        '<script>(function(){'
        # -----------------------------------------------------------------
        # showFloat(wrapperID, text, color, xOffset, delayMs)
        #
        # TUNING KNOBS (search for these values to adjust):
        #   FLOAT_TOTAL_FRAMES  - total animation frames (~60fps).
        #                         Higher = longer on screen. Current: 40
        #   FLOAT_PX_PER_FRAME  - pixels moved upward each frame.
        #                         Lower = slower rise. Current: 1.2
        #   delayMs             - ms before this float starts animating.
        #                         Set via FLOAT_DELAY_MS in Python above.
        # -----------------------------------------------------------------
        'function showFloat(wid,txt,clr,ox,delayMs){'
        'setTimeout(function(){'
        'var w=document.getElementById(wid);'
        'if(!w)return;'
        'var e=document.createElement("div");'
        'e.textContent=txt;'
        'var s=e.style;'
        's.position="absolute";'
        's.left=(w.offsetWidth/2+ox)+"px";'
        's.top="0px";'
        's.color=clr;'
        's.fontSize="16px";'
        's.fontWeight="bold";'
        's.fontFamily="monospace";'
        's.pointerEvents="none";'
        's.zIndex="99999";'
        's.whiteSpace="nowrap";'
        's.textShadow="0 0 4px #000,0 0 4px #000";'
        's.transform="translateX(-50%)";'
        's.transition="none";'
        's.overflow="visible";'
        's.maxWidth="none";'
        'w.appendChild(e);'
        'var f=0;'
        'var total=40;'     # FLOAT_TOTAL_FRAMES - raise to keep text visible longer
        'var pxPerFrame=1.2;'  # FLOAT_PX_PER_FRAME - lower = slower rise
        'function step(){'
        'f++;'
        'e.style.top=(-f*pxPerFrame)+"px";'
        'e.style.opacity=""+(1-f/total);'
        'if(f<total){requestAnimationFrame(step);}'
        'else if(e.parentNode){e.parentNode.removeChild(e);}'
        '}'
        'requestAnimationFrame(step);'
        '},delayMs||0);'
        '}'
        + ''.join(float_calls)
        + '})();</script>'
    )
    return js


# ============================================================
# SPRITE SYSTEM
# Sprite sheets, mappings, and rendering functions
# All sprite data and rendering now in external sprite_data.py
# ============================================================

def get_evolution_tier_style(monster):
    """Return (border_color, tier_label_html) for evolution tier display."""
    tier = monster.properties.get('evolution_tier', '') if hasattr(monster, 'properties') else ''
    if tier == 'Hardened':
        return '#8B7355', '<span style="color:#8B7355;font-size:9px;font-weight:bold;">[Hardened]</span>'
    elif tier == 'Savage':
        return '#A0522D', '<span style="color:#A0522D;font-size:9px;font-weight:bold;">[Savage]</span>'
    elif tier == 'Dread':
        return '#7B68AE', '<span style="color:#7B68AE;font-size:9px;font-weight:bold;">[Dread]</span>'
    elif tier == 'Mythic':
        return '#B8962E', '<span style="color:#B8962E;font-size:9px;font-weight:bold;">[Mythic]</span>'
    return '', ''  # Normal: no border, no label


def generate_player_sprite_html(race, gender, equipped_armor=None):
    """Wrapper that resolves armor state, then delegates to sprite_data."""
    if equipped_armor is None or getattr(equipped_armor, 'is_broken', False):
        armor_state = 'none'
    elif is_metal_item(equipped_armor):
        armor_state = 'metal'
    else:
        armor_state = 'nonmetal'
    return _generate_player_sprite_html(race, armor_state)

def can_cast_spells(player_character):
    """
    Check if player has the ability to cast spells.
    Returns True if player has: 
    - Max mana > 0 (requires Intelligence > 15)
    - Max spell slots > 0 (requires Intelligence > 15)
    """
    return player_character.max_mana > 0 and player_character.get_max_memorized_spell_slots() > 0

def generate_grid_html(floor, player_x, player_y):
    """Generate the HTML for the dungeon grid/map display."""
    highlight_coords = (player_y, player_x)
    grid_html = '<div style="text-align: center; max-width: 385px; overflow-x: auto; margin: 0 auto;"><div style="background-color: #222; display: inline-block; padding: 5px; border-radius: 2px; max-width: 100%;">'

    for r_idx in range(floor.rows):
        grid_html += '<div style="height: 18px; white-space: nowrap;">'
        for c_idx in range(floor.cols):
            room = floor.grid[r_idx][c_idx]
            cell_style = "display: inline-block; width: 18px; height: 18px; line-height: 18px; text-align: center; vertical-align: top; font-family: monospace; font-size: 11px;"
            content = "&nbsp;"

            if room.discovered or (r_idx, c_idx) == highlight_coords:
                content = room.room_type
                if content == '#':
                    cell_style += "color: #555;"
                elif content == '.':
                    cell_style += "color: #888;"
                elif content in ['E', 'D', 'U']:
                    cell_style += "color: #4CAF50;"
                elif content == 'V':
                    cell_style += "color: #FFD700;"
                elif content in ['M', 'W']:
                    # Check if this is a champion monster room
                    if content == 'M' and room.properties.get('is_champion'):
                        cell_style += "color: #FF0000; font-weight: bold; text-shadow: 0 0 3px #FF0000;"
                        content = "M"  # Bold M for champion
                    else:
                        cell_style += "color: #F44336;"
                elif content == 'C':
                    # Check if this is a legendary chest
                    if room.properties.get('is_legendary'):
                        cell_style += "color: #FFD700; font-weight: bold; text-shadow: 0 0 3px #FFD700;"
                    else:
                        cell_style += "color: #03A9F4;"
                elif content == 'A':
                    cell_style += "color: #FFEB3B;"
                elif content == 'P':
                    # Check if this is ancient waters
                    if room.properties.get('is_ancient'):
                        cell_style += "color: #00FFFF; font-weight: bold; text-shadow: 0 0 3px #00FFFF;"
                    else:
                        cell_style += "color: #03A9F4;"
                elif content == 'L':
                    # Check if this has the Codex
                    if room.properties.get('has_codex'):
                        cell_style += "color: #FFD700; font-weight: bold; text-shadow: 0 0 3px #FFD700;"
                    else:
                        cell_style += "color: #E040FB;"
                elif content == 'N':
                    # Check if this is a master dungeon
                    if room.properties.get('is_master'):
                        cell_style += "color: #FFD700; font-weight: bold; text-shadow: 0 0 3px #FFD700;"
                    else:
                        cell_style += "color: #FF6B6B;"  # Red-orange for locked dungeons
                elif content == 'T':
                    # Check if this is a cursed tomb
                    if room.properties.get('is_cursed'):
                        cell_style += "color: #E040FB; font-weight: bold; text-shadow: 0 0 3px #E040FB;"
                    else:
                        cell_style += "color: #8B4513;"  # Brown for tombs
                elif content == 'G':
                    # Check if this is a world tree or fey garden
                    if room.properties.get('has_world_tree'):
                        cell_style += "color: #00FF00; font-weight: bold; text-shadow: 0 0 3px #00FF00;"
                    elif room.properties.get('is_fey_garden'):
                        cell_style += "color: #FF00FF; font-weight: bold; text-shadow: 0 0 3px #FF00FF;"
                    else:
                        cell_style += "color: #4CAF50;"  # Green for magical gardens
                elif content == 'O':
                    cell_style += "color: #E040FB;"  # Purple for oracle rooms
                elif content == 'B':
                    cell_style += "color: #FF8C00;"  # Orange for blacksmith
                elif content == 'F':
                    cell_style += "color: #87CEEB;"  # Sky blue for shrine
                elif content == 'Q':
                    cell_style += "color: #39FF14;"  # Neon green for alchemist lab
                elif content == 'K':
                    cell_style += "color: #CD5C5C;"  # Indian red for war room
                elif content == 'X':
                    cell_style += "color: #D4A017;"  # Gold/amber for taxidermist
                elif content == 'X':
                    cell_style += "color: #D2691E;"  # Saddle brown for taxidermist
                elif content == 'Z':
                    # Puzzle room (Zotle)
                    cell_style += "color: #E040FB; font-weight: bold; text-shadow: 0 0 3px #E040FB;"
                else:
                    cell_style += "color: #DDD;"

                if (r_idx, c_idx) == highlight_coords:
                    cell_style += "background-color: #DDD; color: #000; font-weight: bold; border-radius: 2px;"

            grid_html += f'<span style="{cell_style}">{content}</span>'
        grid_html += "</div>"
    grid_html += "</div></div>"
    return grid_html



# --------------------------------------------------------------------------------
