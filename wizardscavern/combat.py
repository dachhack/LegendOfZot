"""
combat.py - Combat system for Wizard's Cavern

Contains the core combat loop, flee/foresight direction handling,
spell memorization, spell casting during combat, journal actions,
trophy drops, and taxidermist reward helpers.

Usage:
    from .combat import process_combat_action, process_flee_direction_action, ...
"""

import random
import math

from . import game_state as gs
from .game_state import (
    add_log,
    COLOR_RED, COLOR_GREEN, COLOR_RESET, COLOR_PURPLE,
    COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_GREY,
    BOLD, UNDERLINE,
    normal_int_range, get_article,
)

from .items import (Trophy, Treasure, Rune, Shard, Towel, Spell, Potion,
                   CORROSIVE_MONSTERS, get_base_monster_name, apply_corrosion_effect,
                   apply_rust_effect, degrade_equipment, is_item_identified, identify_item,
                   get_item_display_name, process_potion_effects_in_combat,
                   process_potion_effects_on_monster_defeat, process_regeneration_effect,
                   track_equipment_use, drop_monster_items, drop_monster_meat)
from .achievements import check_achievements

from .game_data import TROPHY_DROPS, TAXIDERMIST_COLLECTIONS, BUG_MONSTER_TEMPLATES, BUG_WEAPON_TEMPLATES, BUG_ARMOR_TEMPLATES
from .dungeon import Room


# ---------------------------------------------------------------------------
# Helper: lazy imports for functions that still live in the main module
# (avoids circular-import issues during the incremental refactor)
# ---------------------------------------------------------------------------
def _main():
    """Return the game_systems module (lazy import)."""
    from . import game_systems as main
    return main


def _check_bug_queen_spawn(player_character, my_tower):
    """After a bug monster is killed, check if all bugs on the floor are dead.
    If so, the Bug Queen spawns to avenge her swarm."""
    current_floor = my_tower.floors[player_character.z]

    # Only applies on bug levels, and only if queen hasn't been defeated yet
    if not current_floor.properties.get('is_bug_level'):
        return
    if gs.bug_queen_defeated:
        return

    # Count remaining living bug monster rooms (room_type still 'M' with is_bug_monster)
    remaining_bugs = 0
    for r in range(current_floor.rows):
        for c in range(current_floor.cols):
            room = current_floor.grid[r][c]
            if room.room_type == 'M' and room.properties.get('is_bug_monster'):
                remaining_bugs += 1

    if remaining_bugs > 0:
        return

    # All bugs are dead! The Bug Queen appears to avenge them.
    # Find a suitable empty room near the player to place her
    import random
    px, py = player_character.x, player_character.y
    candidates = []
    for r in range(current_floor.rows):
        for c in range(current_floor.cols):
            room = current_floor.grid[r][c]
            if room.room_type == '.' and not room.properties.get('is_bug_queen'):
                dist = abs(r - py) + abs(c - px)
                candidates.append((dist, r, c))

    if not candidates:
        return

    # Pick a room 2-5 steps away for dramatic entrance, fallback to closest
    nearby = [cand for cand in candidates if 2 <= cand[0] <= 5]
    if not nearby:
        nearby = sorted(candidates, key=lambda x: x[0])[:5]
    _, qr, qc = random.choice(nearby)

    # Spawn the queen
    queen_room = current_floor.grid[qr][qc]
    queen_room.room_type = 'M'
    queen_room.properties['is_bug_queen'] = True
    queen_room.properties['is_bug_monster'] = True
    queen_room.discovered = True  # Reveal her position on the map

    add_log("")
    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
    add_log(f"{COLOR_RED}The ground trembles beneath your tiny feet...{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}A furious shriek echoes through the chamber!{COLOR_RESET}")
    add_log(f'{COLOR_CYAN}"YOU SLAUGHTERED MY CHILDREN!"{COLOR_RESET}')
    add_log(f'{COLOR_CYAN}"NOW FACE THEIR MOTHER!"{COLOR_RESET}')
    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
    add_log(f"{COLOR_RED}*** THE BUG QUEEN HAS APPEARED! ***{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}She has revealed herself on the map. Find her!{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
    add_log("")


# ---------------------------------------------------------------------------
# 19. COMBAT SYSTEM
# ---------------------------------------------------------------------------

def process_combat_action(player_character, my_tower, cmd):
    gs.last_monster_damage = 0
    gs.last_player_damage = 0
    gs.last_player_blocked = False
    gs.last_player_status = None
    gs.last_monster_status = None
    gs.last_player_heal = 0

    if cmd == "init":
        # Get player title for intelligent monsters
        main = _main()
        player_title = main.get_player_title(player_character)

        # Check if monster can talk and has a greeting (must be a string)
        if hasattr(gs.active_monster, 'can_talk') and gs.active_monster.can_talk and \
           hasattr(gs.active_monster, 'greeting_template') and isinstance(gs.active_monster.greeting_template, str):
            greeting = gs.active_monster.greeting_template.format(
                name=player_character.name,
                title=player_title
            )
            add_log(f"{COLOR_PURPLE}{greeting}{COLOR_RESET}")
        else:
            # Default flavor text for non-talking monsters
            if hasattr(gs.active_monster, 'flavor_text') and gs.active_monster.flavor_text:
                add_log(f"A {gs.active_monster.name} (Level {gs.active_monster.level}) appears! {gs.active_monster.flavor_text}")
            else:
                add_log(f"A {gs.active_monster.name} (Level {gs.active_monster.level}) appears!")

        # Commands now shown in HTML and placeholder
        return

    # Check if this is a vault defender (special combat)
    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]

    if room.properties.get('is_vault_chamber', False):
        # This is vault defender combat - use special handler
        main = _main()
        main.process_vault_defender_combat(player_character, my_tower, cmd)
        return

    # --- Process Status Effects at the beginning of each combat turn ---
    player_character.process_status_effects()

    main = _main()
    main.process_passive_treasures(player_character)
    if gs.active_monster and gs.active_monster.is_alive():  # Only process monster effects if it's still alive
        gs.active_monster.process_status_effects()

    # Check if player was defeated by status effects
    if not player_character.is_alive():
        add_log(f"{COLOR_RED}You were defeated by status effects...{COLOR_RESET}")
        gs.prompt_cntl = "death_screen"
        # render() removed - will be called by process_command
        return

    # Check if monster was defeated by status effects
    if gs.active_monster and not gs.active_monster.is_alive():
        add_log(f"{COLOR_GREEN}The {gs.active_monster.name} succumbed to its status effects!{COLOR_RESET}")
        # XP, Gold, Room clearing logic should be here as well
         # Calculate base rewards
        xp_reward = (gs.active_monster.level + 1) * 5

        # Check if this is a legendary monster with custom gold drop
        if gs.active_monster.properties.get('is_legendary'):
            gold_min = gs.active_monster.properties.get('gold_min', 500)
            gold_max = gs.active_monster.properties.get('gold_max', 1000)
            gold_drop = random.randint(gold_min, gold_max)
        else:
            gold_drop = random.randint(1, 10) * (gs.active_monster.level + 1)

        # Apply Treasure Shard bonus (+10% gold)
        if gs.shards_obtained.get('treasure'):
            treasure_bonus = int(gold_drop * 0.10)
            gold_drop += treasure_bonus
            add_log(f"{COLOR_YELLOW} [Treasure Shard] +{treasure_bonus} bonus gold (+10%)!{COLOR_RESET}")

        # Apply Fortune bonus
        if 'Fortune' in player_character.status_effects:
            bonus_pct = player_character.status_effects['Fortune'].magnitude
            bonus_gold = int(gold_drop * bonus_pct / 100)
            gold_drop += bonus_gold
            add_log(f"{COLOR_YELLOW} [Fortune] +{bonus_gold} bonus gold (+{bonus_pct}%)!{COLOR_RESET}")

        # Apply XP Boost
        if 'Experience Boost' in player_character.status_effects:
            bonus_pct = player_character.status_effects['Experience Boost'].magnitude
            bonus_xp = int(xp_reward * bonus_pct / 100)
            xp_reward += bonus_xp
            add_log(f"{COLOR_PURPLE} [Experience Boost] +{bonus_xp} bonus XP (+{bonus_pct}%)!{COLOR_RESET}")

        # Apply Raid Mode XP bonus (+50%) and tick down raid turns
        current_fl = my_tower.floors[player_character.z]
        if current_fl.properties.get('raid_mode_active'):
            raid_bonus = int(xp_reward * 0.50)
            xp_reward += raid_bonus
            raid_left = current_fl.properties.get('raid_turns_left', 0) - 1
            current_fl.properties['raid_turns_left'] = max(0, raid_left)
            add_log(f"{COLOR_RED} [RAID] +{raid_bonus} bonus XP! ({max(0,raid_left)} raid turns left){COLOR_RESET}")
            if raid_left <= 0:
                current_fl.properties['raid_mode_active'] = False
                add_log(f"{COLOR_YELLOW}Raid mode ends. The dust settles.{COLOR_RESET}")

        # Give rewards
        player_character.gain_experience(xp_reward)
        player_character.gold += gold_drop
        add_log(f"You found {gold_drop} gold.")
        gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold_drop
        check_achievements(player_character)

        # 20% chance to drop a potion on monster kill, scaling up with floor level
        potion_chance = min(0.35, 0.20 + player_character.z * 0.01)
        if random.random() < potion_chance:
            potion = main.get_random_potion(player_character.z)
            player_character.inventory.add_item(potion)
            potion_display = get_item_display_name(potion)
            add_log(f"{COLOR_CYAN}The {gs.active_monster.name} dropped {get_article(potion_display)} {potion_display}!{COLOR_RESET}")

        # 10% chance to drop food (rations etc from monster packs/pouches)
        if random.random() < 0.10:
            food = main.get_random_food(player_character.z)
            player_character.inventory.add_item(food)
            add_log(f"{COLOR_CYAN}You found some {food.name} among the {gs.active_monster.name}'s possessions!{COLOR_RESET}")

        # Trophy drop - chance based on TROPHY_DROPS table
        trophy = get_trophy_drop(gs.active_monster.name)
        if trophy:
            # Stack with existing trophy of same name if present
            stacked = False
            for inv_item in player_character.inventory.items:
                if isinstance(inv_item, Trophy) and inv_item.name == trophy.name:
                    inv_item.count += 1
                    stacked = True
                    break
            if not stacked:
                player_character.inventory.add_item(trophy)
            add_log(f"{COLOR_YELLOW}[Trophy] You collected: {trophy.name}! (for the Taxidermist){COLOR_RESET}")

        # Bug gear drop - bug monsters have a chance to drop bug-sized weapons/armor
        if gs.active_monster and gs.active_monster.properties.get('is_bug_monster'):
            _drop_bug_gear(player_character)

        # CHECK FOR BUG QUEEN DEFEAT (status effect path)
        if gs.active_monster and gs.active_monster.properties.get('is_bug_queen'):
            gs.bug_queen_defeated = True
            growth_mushroom = Potion(
                name="Zot's Growth Mushroom",
                description="A luminous mushroom pulsing with restorative magic. Eating it will reverse Zot's shrinking spell.",
                value=0, level=0, potion_type='growth_mushroom', effect_magnitude=0, duration=0
            )
            player_character.inventory.add_item(growth_mushroom)
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}The Bug Queen drops a glowing mushroom!{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}You obtained: Zot's Growth Mushroom!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Use it from your inventory to restore your size!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log("")

        # CHECK FOR DUNGEON KEY DROP
        # Check if this monster holds any dungeon keys
        current_floor = my_tower.floors[player_character.z]
        monster_pos = (player_character.x, player_character.y)

        for r in range(current_floor.rows):
            for c in range(current_floor.cols):
                check_room = current_floor.grid[r][c]
                if check_room.room_type == 'N':
                    if check_room.properties.get('key_holder') == monster_pos:
                        dungeon_coords = (c, r, player_character.z)
                        gs.dungeon_keys[dungeon_coords] = True
                        add_log(f"{COLOR_CYAN}The monster dropped a dungeon key for location ({c}, {r})!{COLOR_RESET}")

        current_floor = my_tower.floors[player_character.z]
        room = current_floor.grid[player_character.y][player_character.x]
        _was_bug_monster = gs.active_monster.properties.get('is_bug_monster', False)
        room.room_type = '.'  # Clear room
        # Drop items from monster
        drop_monster_items(gs.active_monster, player_character)
        # Drop meat from monster if edible
        drop_monster_meat(gs.active_monster, player_character)
        gs.active_monster = None

        # Check if all bugs are dead and the Bug Queen should spawn
        if _was_bug_monster:
            _check_bug_queen_spawn(player_character, my_tower)

        main._trigger_room_interaction(player_character, my_tower)  # Re-evaluate room as '.'
        return  # Combat ended by status effect


    if cmd == 'i':
        gs.prompt_cntl = "inventory"
        main.handle_inventory_menu(player_character, my_tower, "init")
        return

    if cmd == 'a':
        # Player attacks
        damage_type = "Physical"
        if player_character.equipped_weapon and player_character.equipped_weapon.elemental_strength:
            val = player_character.equipped_weapon.elemental_strength[0]
            if val != "None":
                damage_type = val

        # Track equipment use for auto-identification (after 5 combats, item is identified)
        if player_character.equipped_weapon:
            track_equipment_use(player_character.equipped_weapon)
        if player_character.equipped_armor:
            track_equipment_use(player_character.equipped_armor)

        # Degrade equipment durability
        durability_messages = degrade_equipment(player_character, gs.active_monster.level)
        for msg in durability_messages:
            add_log(msg)

        # FIRST ATTACK
        # Platino: immune to melee/direct attacks
        if gs.active_monster and gs.active_monster.properties.get('is_platino'):
            add_log(f"{COLOR_YELLOW}Platino easily dodges your melee attack.{COLOR_RESET}")
        else:
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

        # NEW: CHECK FOR HASTE - SECOND ATTACK
        if 'Haste' in player_character.status_effects and gs.active_monster.is_alive():
            add_log(f"{COLOR_CYAN} [HASTE] You attack again!{COLOR_RESET}")

            # SECOND ATTACK (same logic as first)
            # Platino: immune to melee
            if gs.active_monster.properties.get('is_platino'):
                add_log(f"{COLOR_YELLOW}Platino easily dodges your melee attack.{COLOR_RESET}")
            else:
                # Corrosive monsters damage equipment on contact
                if (gs.active_monster.name in CORROSIVE_MONSTERS or get_base_monster_name(gs.active_monster.name) in CORROSIVE_MONSTERS) and player_character.equipped_weapon:
                    corrosion_messages = apply_corrosion_effect(player_character, gs.active_monster.name, is_player_attacking=True)
                    for msg in corrosion_messages:
                        add_log(msg)

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

        # Continue with normal monster defeat check...
        if not gs.active_monster.is_alive():
            add_log(f"{COLOR_GREEN}You defeated the {gs.active_monster.name}!{COLOR_RESET}")
            # Cook meat if killed with fire weapon
            if damage_type == "Fire":
                add_log(f"{COLOR_YELLOW}The fire sears the {gs.active_monster.name}'s flesh!{COLOR_RESET}")
            # ... rest of defeat logic
            add_log(f"{COLOR_GREEN}{gs.active_monster.victory_text}{COLOR_RESET}")

            #
            # CALCULATE BASE REWARDS
            #
            xp_reward = (gs.active_monster.level + 1) * 5
            gold_drop = random.randint(1, 10) * (gs.active_monster.level + 1)

            #
            # APPLY FORTUNE BONUS (before adding to player)
            #
            if 'Fortune' in player_character.status_effects:
                bonus_pct = player_character.status_effects['Fortune'].magnitude
                bonus_gold = int(gold_drop * bonus_pct / 100)
                gold_drop += bonus_gold
                add_log(f"{COLOR_YELLOW} [Fortune] +{bonus_gold} bonus gold (+{bonus_pct}%)!{COLOR_RESET}")

            #
            # APPLY XP BOOST (before adding to player)
            #
            if 'Experience Boost' in player_character.status_effects:
                bonus_pct = player_character.status_effects['Experience Boost'].magnitude
                bonus_xp = int(xp_reward * bonus_pct / 100)
                xp_reward += bonus_xp
                add_log(f"{COLOR_PURPLE} [Experience Boost] +{bonus_xp} bonus XP (+{bonus_pct}%)!{COLOR_RESET}")

            #
            # NOW GIVE REWARDS TO PLAYER
            #
            player_character.gain_experience(xp_reward)
            player_character.gold += gold_drop
            add_log(f"You found {gold_drop} gold.")
            gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold_drop

            #
            # TRACK ACHIEVEMENT STATS
            #
            gs.game_stats['monsters_killed'] = gs.game_stats.get('monsters_killed', 0) + 1

            # Track if killed at full health
            if player_character.health == player_character.max_health:
                gs.game_stats['full_health_kills'] = gs.game_stats.get('full_health_kills', 0) + 1

            # Track if killed without armor
            if player_character.equipped_armor is None:
                gs.game_stats['kills_no_armor'] = gs.game_stats.get('kills_no_armor', 0) + 1

            # Track if defeated higher level monster
            if gs.active_monster.level >= player_character.level + 3:
                gs.game_stats['defeated_higher_level'] = gs.game_stats.get('defeated_higher_level', 0) + 1

            #
            # QUEST TRACKING: Rune of Battle
            #
            if not gs.runes_obtained['battle']:
                gs.rune_progress['monsters_killed_total'] += 1
                if gs.rune_progress['monsters_killed_total'] >= gs.rune_progress_reqs['monsters_killed_total'] and not gs.champion_monster_available:
                    gs.champion_monster_available = True
                    add_log(f"{COLOR_PURPLE}The air grows heavy... A Champion has been summoned!{COLOR_RESET}")
                    add_log(f"{COLOR_PURPLE}Seek it in a monster room to claim the Rune of Battle.{COLOR_RESET}")

                # Award Rune of Battle for defeating Champion
                if gs.active_monster.properties.get('is_champion'):
                    rune = Rune(
                        name="Rune of Battle",
                        rune_type='battle',
                        description="A crimson rune pulsing with warrior's courage. Unlocks the Battle Shard vault.",
                        value=0,
                        level=0
                    )
                    player_character.inventory.add_item(rune)
                    gs.runes_obtained['battle'] = True
                    gs.champion_monster_available = False
                    add_log("")
                    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                    add_log(f"{COLOR_YELLOW}* THE RUNE OF BATTLE IS YOURS! *{COLOR_RESET}")
                    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                    add_log(f"{COLOR_CYAN}The Champion's essence coalesces into a glowing rune!{COLOR_RESET}")
                    add_log("")

                # Award Shard for defeating Legendary Monster
                if gs.active_monster.properties.get('is_legendary'):
                    shard_type = gs.active_monster.properties.get('shard_type')

                    # Shard passive bonuses
                    shard_bonuses = {
                        'battle': ('Attack +3', lambda: setattr(player_character, 'base_attack', player_character.base_attack + 3)),
                        'treasure': ('Gold drops +10%', None),  # Implemented in gold calculation
                        'devotion': ('Max HP +20', lambda: (setattr(player_character, 'max_health', player_character.max_health + 20), setattr(player_character, 'health', player_character.health + 20))),
                        'reflection': ('Max Mana +20', lambda: (setattr(player_character, 'max_mana', player_character.max_mana + 20), setattr(player_character, 'mana', player_character.mana + 20))),
                        'knowledge': ('Spell costs -20%', None),  # Implemented in spell casting
                        'secrets': ('Reveal hidden rooms', None),  # Special ability
                        'eternity': ('Defense +5', lambda: setattr(player_character, 'base_defense', player_character.base_defense + 5)),
                        'growth': ('Potion effects +2 turns', None)  # Implemented in potion use
                    }

                    shard = Shard(
                        name=f"Shard of {shard_type.capitalize()}",
                        shard_type=shard_type,
                        passive_bonus=shard_bonuses[shard_type][0],
                        description=f"A fragment of primordial power. Grants: {shard_bonuses[shard_type][0]}",
                        value=0,
                        level=0
                    )
                    player_character.inventory.add_item(shard)
                    gs.shards_obtained[shard_type] = True

                    # Apply immediate passive bonus
                    if shard_bonuses[shard_type][1]:
                        shard_bonuses[shard_type][1]()

                    add_log("")
                    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                    add_log(f"{COLOR_YELLOW}** SHARD OF {shard_type.upper()} OBTAINED! **{COLOR_RESET}")
                    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                    add_log(f"{COLOR_CYAN}The legendary guardian's power crystallizes into a Shard!{COLOR_RESET}")
                    add_log(f"{COLOR_GREEN}Passive Bonus: {shard_bonuses[shard_type][0]}{COLOR_RESET}")
                    add_log("")

                    # Check if all 8 shards obtained
                    shards_count = sum(gs.shards_obtained.values())
                    if shards_count == 8:
                        gs.gate_to_floor_50_unlocked = True
                        add_log("")
                        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                        add_log(f"{COLOR_YELLOW}*** ALL 8 SHARDS OBTAINED! ***{COLOR_RESET}")
                        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                        add_log(f"{COLOR_RED}The Gate to Floor 50 has opened!{COLOR_RESET}")
                        add_log(f"{COLOR_RED}Descend to floor 49 to face Zot's Guardian!{COLOR_RESET}")
                        add_log("")

                # Check if this was Zot's Guardian - VICTORY!
                if gs.active_monster.properties.get('is_zots_guardian'):
                    add_log("")
                    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                    add_log(f"{COLOR_YELLOW}*** THE ORB OF ZOT IS YOURS! ***{COLOR_RESET}")
                    add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                    add_log("")
                    add_log(f"{COLOR_CYAN}A brilliant orb materializes, pulsing with infinite power!{COLOR_RESET}")
                    add_log(f"{COLOR_GREEN}You have conquered the Wizard's Cavern and claimed the legendary Orb!{COLOR_RESET}")
                    add_log("")
                    add_log(f"{COLOR_YELLOW}Final Statistics:{COLOR_RESET}")
                    add_log(f"  Level: {player_character.level}")
                    add_log(f"  Floors Conquered: 50")
                    add_log(f"  Monsters Slain: {gs.game_stats.get('monsters_killed', 0)}")
                    add_log(f"  Runes Collected: 8/8")
                    add_log(f"  Shards Obtained: 8/8")
                    add_log("")
                    add_log(f"{COLOR_PURPLE}*** CONGRATULATIONS! YOU WIN! ***{COLOR_RESET}")
                    add_log("")

                    # Set victory state
                    gs.prompt_cntl = "victory_screen"
                    check_achievements(player_character)
                    return

            # Check achievements
            check_achievements(player_character)

            # Trophy drop - chance based on TROPHY_DROPS table
            trophy = get_trophy_drop(gs.active_monster.name)
            if trophy:
                stacked = False
                for inv_item in player_character.inventory.items:
                    if isinstance(inv_item, Trophy) and inv_item.name == trophy.name:
                        inv_item.count += 1
                        stacked = True
                        break
                if not stacked:
                    player_character.inventory.add_item(trophy)
                add_log(f"{COLOR_YELLOW}[Trophy] You collected: {trophy.name}! (for the Taxidermist){COLOR_RESET}")

            # Bug gear drop - bug monsters have a chance to drop bug-sized weapons/armor
            if gs.active_monster and gs.active_monster.properties.get('is_bug_monster'):
                _drop_bug_gear(player_character)

            # CHECK FOR TOMB GUARDIAN REWARD
            # If we just defeated a tomb guardian, award the special reward
            if gs.active_monster and gs.active_monster.properties.get('is_tomb_guardian'):
                from .room_actions import award_tomb_guardian_reward
                award_tomb_guardian_reward(player_character)

            # CHECK FOR PLATINO DROP
            if gs.active_monster and gs.active_monster.properties.get('is_platino'):
                platino_scale = Treasure(
                    name="Platino's Scale",
                    description="A shimmering platinum scale. Halves all physical damage taken when equipped.",
                    gold_value=0,
                    value=5000,
                    treasure_type='passive',
                    is_unique=True,
                    passive_effect="Halves physical damage taken"
                )
                player_character.inventory.add_item(platino_scale)
                add_log("")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_YELLOW}   LEGENDARY UNIQUE TREASURE!   {COLOR_RESET}")
                add_log(f"{COLOR_YELLOW}You obtained: Platino's Scale!{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}Halves all physical damage taken when equipped as an accessory.{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log("")

            # CHECK FOR BUG QUEEN DEFEAT - Drop Growth Mushroom and restore size
            if gs.active_monster and gs.active_monster.properties.get('is_bug_queen'):
                gs.bug_queen_defeated = True
                # Give the player the Growth Mushroom
                growth_mushroom = Potion(
                    name="Zot's Growth Mushroom",
                    description="A luminous mushroom pulsing with restorative magic. Eating it will reverse Zot's shrinking spell.",
                    value=0,
                    level=0,
                    potion_type='growth_mushroom',
                    effect_magnitude=0,
                    duration=0
                )
                player_character.inventory.add_item(growth_mushroom)
                add_log("")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_YELLOW}The Bug Queen drops a glowing mushroom!{COLOR_RESET}")
                add_log(f"{COLOR_GREEN}You obtained: Zot's Growth Mushroom!{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}Use it from your inventory to restore your size!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log("")

            # CHECK FOR DUNGEON KEY DROP
            # Check if this monster holds any dungeon keys
            current_floor = my_tower.floors[player_character.z]
            monster_pos = (player_character.x, player_character.y)

            for r in range(current_floor.rows):
                for c in range(current_floor.cols):
                    check_room = current_floor.grid[r][c]
                    if check_room.room_type == 'N':
                        if check_room.properties.get('key_holder') == monster_pos:
                            dungeon_coords = (c, r, player_character.z)
                            gs.dungeon_keys[dungeon_coords] = True
                            add_log(f"{COLOR_CYAN}The monster dropped a dungeon key for location ({c}, {r})!{COLOR_RESET}")

            # Remove monster from room
            current_floor = my_tower.floors[player_character.z]
            room = current_floor.grid[player_character.y][player_character.x]
            _was_bug_monster = gs.active_monster.properties.get('is_bug_monster', False)
            room.room_type = '.'  # Clear room
            # Drop items from monster
            drop_monster_items(gs.active_monster, player_character)
            # Drop meat from monster if edible; auto-cook if fire kill
            _dying_monster = gs.active_monster
            _fire_kill = (damage_type == "Fire")
            gs.active_monster = None
            drop_monster_meat(_dying_monster, player_character, fire_killed=_fire_kill)

            # Check if all bugs are dead and the Bug Queen should spawn
            if _was_bug_monster:
                _check_bug_queen_spawn(player_character, my_tower)

            main._trigger_room_interaction(player_character, my_tower)  # Re-evaluate room as '.'
            return


        # Check for Invisibility - monsters can't attack invisible players
        if 'Invisibility' in player_character.status_effects:
            add_log(f"{COLOR_PURPLE}[Invisible] The {gs.active_monster.name} cannot see you!{COLOR_RESET}")
            # Skip monster attack
        else:
            # Normal monster attack
            gs.active_monster.attack_target(player_character)
            if 'Frost Armor' in player_character.status_effects:
                reflect_damage = player_character.status_effects['Frost Armor'].magnitude
                gs.active_monster.take_damage(reflect_damage, "Ice")
                add_log(f"{COLOR_CYAN} Frost Armor reflects {reflect_damage} ice damage!{COLOR_RESET}")

            # Corrosive monsters damage armor on attack
            if (gs.active_monster.name in CORROSIVE_MONSTERS or get_base_monster_name(gs.active_monster.name) in CORROSIVE_MONSTERS):
                corrosion_messages = apply_corrosion_effect(player_character, gs.active_monster.name, is_player_attacking=False)
                for msg in corrosion_messages:
                    add_log(msg)

        if not player_character.is_alive():
             add_log(f"{COLOR_RED}You were defeated by the {gs.active_monster.name}...{COLOR_RESET}")
             gs.prompt_cntl = "death_screen"
             return

    elif cmd == 'f':
        # Flee logic
        flee_chance = 0.50 + (player_character.dexterity * 0.02)  # Base 50% + 2% per dexterity
        flee_chance = min(0.95, flee_chance)  # Cap at 95%

        if 'web' in player_character.status_effects:
            add_log(f"{COLOR_RED}Flee failed! You are stuck in a big stupid web!{COLOR_RESET}")
            gs.active_monster.attack_target(player_character)
            if not player_character.is_alive():
                add_log(f"{COLOR_RED}You were defeated...{COLOR_RESET}")
                gs.prompt_cntl = "death_screen"
                return
        elif 'Invisibility' in player_character.status_effects:
            add_log(f"{COLOR_PURPLE}[Invisible] The {gs.active_monster.name} cannot see you. You escape easily.{COLOR_RESET}")
            gs.prompt_cntl = "flee_direction_mode"
        elif random.random() < flee_chance:
            add_log(f"{COLOR_GREEN}You successfully broke away from combat!{COLOR_RESET}")
            add_log("Choose a direction to flee (n/s/e/w):")
            gs.prompt_cntl = "flee_direction_mode"
        else:
            add_log(f"{COLOR_RED}Flee failed! The monster blocks your escape.{COLOR_RESET}")
            gs.active_monster.attack_target(player_character)
            if not player_character.is_alive():
                add_log(f"{COLOR_RED}You were defeated...{COLOR_RESET}")
                gs.prompt_cntl = "death_screen"
                return

    elif cmd == 'c':
        # Only allow spell casting if player can cast spells
        if not main.can_cast_spells(player_character):
            add_log(f"{COLOR_YELLOW}You cannot cast spells. (Requires Intelligence > 15){COLOR_RESET}")
            return
        gs.prompt_cntl = 'spell_casting_mode'
        add_log("Which spell will you cast?")
        process_spell_casting_action(player_character, my_tower, "init")  # Display available spells
        return
    else:
        # Generate combat commands dynamically based on spell capability
        can_cast = main.can_cast_spells(player_character)
        valid_commands = "a = attack | f = flee | i = inventory"
        if can_cast:
            valid_commands += " | c = cast spell"
        add_log(f"Invalid combat command. Valid commands: {valid_commands}")

def process_flee_direction_action(player_character, my_tower, cmd):
    main = _main()

    if cmd in ['n', 's', 'e', 'w']:
        # Try to move in the chosen direction
        current_floor = my_tower.floors[player_character.z]
        target_x, target_y = player_character.x, player_character.y

        if cmd == 'n':
            target_y -= 1
        elif cmd == 's':
            target_y += 1
        elif cmd == 'w':
            target_x -= 1
        elif cmd == 'e':
            target_x += 1

        # Check if the direction is valid
        if (0 <= target_x < current_floor.cols and
            0 <= target_y < current_floor.rows and
            current_floor.grid[target_y][target_x].room_type != current_floor.wall_char):

            # Valid direction - move there
            player_character.x = target_x
            player_character.y = target_y
            current_floor.grid[target_y][target_x].discovered = True
            main.reveal_adjacent_walls(player_character, my_tower)

            #add_log(f"{COLOR_GREEN}You fled {cmd}!{COLOR_RESET}")

            # Clear the monster
            gs.active_monster = None

            # Process status effects after fleeing
            player_character.process_status_effects()

            # Check if player died from status effects
            if not player_character.is_alive():
                add_log(f"{COLOR_RED}You succumbed to your wounds while fleeing...{COLOR_RESET}")
                gs.game_should_quit = True
                return

            # Trigger room interaction for new location
            main._trigger_room_interaction(player_character, my_tower)
        else:
            # Invalid direction - wall or out of bounds
            add_log(f"{COLOR_YELLOW}You can't flee in that direction - there's a wall!{COLOR_RESET}")
            add_log("Choose another direction (n/s/e/w) or 'c' to cancel and fight:")

    elif cmd == 'c':
        # Cancel flee and return to combat
        add_log(f"{COLOR_YELLOW}You decide to stand and fight!{COLOR_RESET}")
        gs.prompt_cntl = "combat_mode"

    else:
        add_log(f"{COLOR_YELLOW}Invalid direction. Enter n, s, e, or w to flee (or 'c' to cancel).{COLOR_RESET}")

def process_foresight_direction_action(player_character, my_tower, cmd):
    """
    Handle Scroll of Foresight - reveals 3 columns/rows in chosen direction
    """
    main = _main()

    if cmd == 'c':
        add_log(f"{COLOR_YELLOW}You roll up the scroll without using it.{COLOR_RESET}")
        gs.prompt_cntl = "inventory"
        gs.active_foresight_scroll = None
        main.handle_inventory_menu(player_character, my_tower, "init")
        return

    if cmd not in ['n', 's', 'e', 'w']:
        add_log(f"{COLOR_YELLOW}Invalid direction. Enter n, s, e, or w (or 'c' to cancel).{COLOR_RESET}")
        return

    # Direction selected - reveal the 3 rows/columns
    current_floor = my_tower.floors[player_character.z]
    player_x, player_y = player_character.x, player_character.y

    revealed_count = 0

    if cmd == 'n':  # North - reveal 3 columns going up
        add_log(f"{COLOR_CYAN}The scroll reveals the path to the NORTH...{COLOR_RESET}")
        for col_offset in [-1, 0, 1]:  # Three columns
            target_col = player_x + col_offset
            if 0 <= target_col < current_floor.cols:
                # Reveal entire column going north
                for row in range(player_y - 1, -1, -1):
                    room = current_floor.grid[row][target_col]
                    if not room.discovered:
                        room.discovered = True
                        revealed_count += 1

    elif cmd == 's':  # South - reveal 3 columns going down
        add_log(f"{COLOR_CYAN}The scroll reveals the path to the SOUTH...{COLOR_RESET}")
        for col_offset in [-1, 0, 1]:  # Three columns
            target_col = player_x + col_offset
            if 0 <= target_col < current_floor.cols:
                # Reveal entire column going south
                for row in range(player_y + 1, current_floor.rows):
                    room = current_floor.grid[row][target_col]
                    if not room.discovered:
                        room.discovered = True
                        revealed_count += 1

    elif cmd == 'w':  # West - reveal 3 rows going left
        add_log(f"{COLOR_CYAN}The scroll reveals the path to the WEST...{COLOR_RESET}")
        for row_offset in [-1, 0, 1]:  # Three rows
            target_row = player_y + row_offset
            if 0 <= target_row < current_floor.rows:
                # Reveal entire row going west
                for col in range(player_x - 1, -1, -1):
                    room = current_floor.grid[target_row][col]
                    if not room.discovered:
                        room.discovered = True
                        revealed_count += 1

    elif cmd == 'e':  # East - reveal 3 rows going right
        add_log(f"{COLOR_CYAN}The scroll reveals the path to the EAST...{COLOR_RESET}")
        for row_offset in [-1, 0, 1]:  # Three rows
            target_row = player_y + row_offset
            if 0 <= target_row < current_floor.rows:
                # Reveal entire row going east
                for col in range(player_x + 1, current_floor.cols):
                    room = current_floor.grid[target_row][col]
                    if not room.discovered:
                        room.discovered = True
                        revealed_count += 1

    add_log(f"{COLOR_GREEN}The magical vision fades... {revealed_count} rooms revealed!{COLOR_RESET}")
    add_log(f"{COLOR_GREY}The scroll crumbles to dust in your hands.{COLOR_RESET}")

    # Consume the scroll
    player_character.inventory.remove_item(gs.active_foresight_scroll.name)
    gs.active_foresight_scroll = None
    gs.prompt_cntl = "inventory"
    main.handle_inventory_menu(player_character, my_tower, "init")


# ---------------------------------------------------------------------------
# 20. SPELL & MAGIC SYSTEM
# ---------------------------------------------------------------------------

def process_spell_memorization_action(player_character, my_tower, cmd):

    if cmd == "init":
        all_spells = player_character.get_spell_inventory()
        max_slots = player_character.get_max_memorized_spell_slots()
        used_slots = player_character.get_used_spell_slots()

        add_log(f"Spell Memorization ({used_slots}/{max_slots} slots used)")
        add_log("")

        if not all_spells:
            add_log("You have no spells in your inventory.")
            # Commands now shown in HTML and placeholder
        else:
            add_log("Available Spells:")
            for i, spell in enumerate(all_spells):
                display_name = get_item_display_name(spell)
                identified = is_item_identified(spell)
                slots_needed = player_character.get_spell_slots(spell)
                memorized_marker = " [MEMORIZED]" if spell in player_character.memorized_spells else ""
                if identified:
                    add_log(f"  {i + 1}. {display_name} (Cost: {spell.mana_cost} MP, Lvl {spell.level}, {slots_needed} slot{'s' if slots_needed > 1 else ''}){memorized_marker}")
                else:
                    add_log(f"  {i + 1}. {display_name} [?]")

            add_log("")
            add_log("Memorized Spells:")
            if player_character.memorized_spells:
                for i, spell in enumerate(player_character.memorized_spells):
                    slots_used = player_character.get_spell_slots(spell)
                    add_log(f"  {i + 1}. {spell.name} ({slots_used} slot{'s' if slots_used > 1 else ''})")
            else:
                add_log("  (None)")

            add_log("")
            # Commands now shown in HTML and placeholder
        return

    if cmd == 'x':
        gs.prompt_cntl = "inventory"
        add_log("Closed spell memorization.")
        return

    all_spells = player_character.get_spell_inventory()

    if cmd.startswith('m') and len(cmd) > 1 and cmd != 'mx':
        try:
            spell_index = int(cmd[1:].strip()) - 1
            if 0 <= spell_index < len(all_spells):
                spell = all_spells[spell_index]
                success, message = player_character.memorize_spell(spell)
                add_log(f"{COLOR_GREEN if success else COLOR_YELLOW}{message}{COLOR_RESET}")
                process_spell_memorization_action(player_character, my_tower, "init")
            else:
                add_log(f"{COLOR_YELLOW}Invalid spell number.{COLOR_RESET}")
        except ValueError:
            add_log(f"{COLOR_YELLOW}Invalid input. Use 'm [number]' to memorize.{COLOR_RESET}")

    elif cmd.startswith('f') and len(cmd) > 1 and cmd != 'fx':
        try:
            spell_index = int(cmd[1:].strip()) - 1
            if 0 <= spell_index < len(player_character.memorized_spells):
                spell = player_character.memorized_spells[spell_index]
                success, message = player_character.forget_spell(spell)
                add_log(f"{COLOR_GREEN if success else COLOR_YELLOW}{message}{COLOR_RESET}")
                process_spell_memorization_action(player_character, my_tower, "init")
            else:
                add_log(f"{COLOR_YELLOW}Invalid memorized spell number.{COLOR_RESET}")
        except ValueError:
            add_log(f"{COLOR_YELLOW}Invalid input. Use 'f [number]' to forget.{COLOR_RESET}")

def process_journal_action(player_character, my_tower, cmd):
    """
    Handle journal viewing - shows all discovered items with stats
    """
    main = _main()

    if cmd == "init":
        add_log(f"{COLOR_CYAN}{COLOR_RESET}")
        add_log(f"{COLOR_CYAN} Opening your adventurer's journal...{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}{COLOR_RESET}")
        add_log("")
        add_log("Navigate: 1=Weapons | 2=Armor | 3=Potions | 4=Scrolls | 5=Spells | 6=Treasures | 7=Utilities | 8=Ingredients")
        # Commands now shown in HTML and placeholder
        return

    if cmd == 'x':
        gs.prompt_cntl = "inventory"
        add_log("Journal closed.")
        main.handle_inventory_menu(player_character, my_tower, "init")
        return

    if cmd == 's':
        gs.prompt_cntl = "character_stats_mode"
        return

    if cmd == 'a':
        gs.prompt_cntl = "achievements_mode"
        return

    if cmd == 'g':
        if gs.active_monster and gs.active_monster.is_alive():
            add_log(f"{COLOR_YELLOW}You cannot save during combat!{COLOR_RESET}")
            return
        gs.prompt_cntl = "save_load_mode"
        main.process_save_load_action(player_character, my_tower, "init")
        return

    # Category selection
    if cmd in ['1', '2', '3', '4', '5', '6', '7', '8']:
        category_map = {
            '1': 'weapons',
            '2': 'armor',
            '3': 'potions',
            '4': 'scrolls',
            '5': 'spells',
            '6': 'treasures',
            '7': 'utilities',
            '8': 'ingredients'
        }
        gs.prompt_cntl = f"journal_{category_map[cmd]}"
        process_journal_category(player_character, my_tower, category_map[cmd], "init")
        return

    add_log(f"{COLOR_YELLOW}Invalid command. Enter 1-7 to view category, or 'x' to close.{COLOR_RESET}")


def process_journal_category(player_character, my_tower, category, cmd):
    """
    Display a specific category of the journal
    """
    main = _main()

    if cmd == "init":
        # Display will be handled by render()
        return

    if cmd == 'b':
        # Back to main journal menu
        gs.prompt_cntl = "journal_mode"
        process_journal_action(player_character, my_tower, "init")
        return

    if cmd == 's':
        gs.prompt_cntl = "character_stats_mode"
        return

    if cmd == 'a':
        gs.prompt_cntl = "achievements_mode"
        return

    if cmd == 'g':
        if gs.active_monster and gs.active_monster.is_alive():
            add_log(f"{COLOR_YELLOW}You cannot save during combat!{COLOR_RESET}")
            return
        gs.prompt_cntl = "save_load_mode"
        main.process_save_load_action(player_character, my_tower, "init")
        return

    if cmd == 'x':
        # Close journal entirely
        gs.prompt_cntl = "inventory"
        add_log("Journal closed.")
        main.handle_inventory_menu(player_character, my_tower, "init")
        return

    # Commands now shown in HTML and placeholder

def process_spell_casting_action(player_character, my_tower, cmd):
    gs.last_monster_damage = 0
    gs.last_player_damage = 0
    gs.last_player_blocked = False
    gs.last_player_status = None
    gs.last_monster_status = None
    gs.last_player_heal = 0

    main = _main()

    # Filter spells from inventory that the player can cast (based on level, mana, etc. - for simplicity, just type check for now)
    available_spells = player_character.memorized_spells

    if cmd == "init":
        if not available_spells:
            add_log("You have no spells memorized. Visit the spell memorization menu to memorize spells.")
            gs.prompt_cntl = "combat_mode"
        return

        add_log("Your Memorized Spells:")
        for i, spell in enumerate(available_spells):
            add_log(f"  {i + 1}. {spell.name} (Cost: {spell.mana_cost} Mana, Power: {spell.base_power}, Type: {spell.damage_type})")
        # Command prompt is now in the placeholder
        return

    if cmd == 'x':
        add_log("Spell casting cancelled.")
        gs.prompt_cntl = "combat_mode"
        return

    try:
        spell_index = int(cmd) - 1
        if 0 <= spell_index < len(available_spells):
            chosen_spell = available_spells[spell_index]

            # Platino: immune to memorized spell attacks
            if gs.active_monster and gs.active_monster.properties.get('is_platino'):
                add_log(f"{COLOR_YELLOW}Platino interrupts your casting and the spell fizzles out.{COLOR_RESET}")
                gs.prompt_cntl = "combat_mode"
                return

            # Cast the spell
            spell_cast_successful = player_character.cast_spell(chosen_spell, gs.active_monster)

            if spell_cast_successful:

                gs.game_stats['spells_cast'] = gs.game_stats.get('spells_cast', 0) + 1
                check_achievements(player_character)

                # After casting, check combat state
                if gs.active_monster and not gs.active_monster.is_alive():
                    add_log(f"{COLOR_GREEN}You defeated the {gs.active_monster.name}!{COLOR_RESET}")
                    add_log(f"{COLOR_GREEN}{gs.active_monster.victory_text}{COLOR_RESET}")

                    # Calculate base rewards
                    xp_reward = (gs.active_monster.level + 1) * 5
                    gold_drop = random.randint(1, 10) * (gs.active_monster.level + 1)

                    # Apply Fortune bonus
                    if 'Fortune' in player_character.status_effects:
                        bonus_pct = player_character.status_effects['Fortune'].magnitude
                        bonus_gold = int(gold_drop * bonus_pct / 100)
                        gold_drop += bonus_gold
                        add_log(f"{COLOR_YELLOW} [Fortune] +{bonus_gold} bonus gold (+{bonus_pct}%)!{COLOR_RESET}")

                    # Apply XP Boost
                    if 'Experience Boost' in player_character.status_effects:
                        bonus_pct = player_character.status_effects['Experience Boost'].magnitude
                        bonus_xp = int(xp_reward * bonus_pct / 100)
                        xp_reward += bonus_xp
                        add_log(f"{COLOR_PURPLE} [Experience Boost] +{bonus_xp} bonus XP (+{bonus_pct}%)!{COLOR_RESET}")

                    # Give rewards
                    player_character.gain_experience(xp_reward)
                    player_character.gold += gold_drop
                    add_log(f"You found {gold_drop} gold.")
                    gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold_drop
                    check_achievements(player_character)

                    # Trophy drop - chance based on TROPHY_DROPS table
                    trophy = get_trophy_drop(gs.active_monster.name)
                    if trophy:
                        stacked = False
                        for inv_item in player_character.inventory.items:
                            if isinstance(inv_item, Trophy) and inv_item.name == trophy.name:
                                inv_item.count += 1
                                stacked = True
                                break
                        if not stacked:
                            player_character.inventory.add_item(trophy)
                        add_log(f"{COLOR_YELLOW}[Trophy] You collected: {trophy.name}! (for the Taxidermist){COLOR_RESET}")

                    # Bug gear drop
                    if gs.active_monster and gs.active_monster.properties.get('is_bug_monster'):
                        _drop_bug_gear(player_character)

                    # CHECK FOR BUG QUEEN DEFEAT
                    if gs.active_monster and gs.active_monster.properties.get('is_bug_queen'):
                        gs.bug_queen_defeated = True
                        growth_mushroom = Potion(
                            name="Zot's Growth Mushroom",
                            description="A luminous mushroom pulsing with restorative magic. Eating it will reverse Zot's shrinking spell.",
                            value=0, level=0, potion_type='growth_mushroom', effect_magnitude=0, duration=0
                        )
                        player_character.inventory.add_item(growth_mushroom)
                        add_log("")
                        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                        add_log(f"{COLOR_YELLOW}The Bug Queen drops a glowing mushroom!{COLOR_RESET}")
                        add_log(f"{COLOR_GREEN}You obtained: Zot's Growth Mushroom!{COLOR_RESET}")
                        add_log(f"{COLOR_CYAN}Use it from your inventory to restore your size!{COLOR_RESET}")
                        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                        add_log("")

                    # Remove monster from room
                    current_floor = my_tower.floors[player_character.z]
                    room = current_floor.grid[player_character.y][player_character.x]
                    _was_bug_monster = gs.active_monster.properties.get('is_bug_monster', False)
                    room.room_type = '.'  # Clear room
                    drop_monster_items(gs.active_monster, player_character)
                    drop_monster_meat(gs.active_monster, player_character)
                    gs.active_monster = None

                    # Check if all bugs are dead and the Bug Queen should spawn
                    if _was_bug_monster:
                        _check_bug_queen_spawn(player_character, my_tower)

                    main._trigger_room_interaction(player_character, my_tower)  # Re-evaluate room as '.'
                    return  # Combat ended

                elif gs.active_monster:  # Monster still alive, it attacks back
                    gs.active_monster.attack_target(player_character)

                    if not player_character.is_alive():
                        add_log(f"{COLOR_RED}You were defeated by the {gs.active_monster.name}...{COLOR_RESET}")
                        gs.prompt_cntl = "death_screen"
                        return  # Game Over

                # If combat continues, return to combat mode
                gs.prompt_cntl = "combat_mode"

            else:  # Spell cast not successful (e.g., not enough mana)
                gs.prompt_cntl = "spell_casting_mode"  # Stay in spell selection mode
                add_log("Choose another spell or 'x' to cancel.")

        else:
            add_log(f"{COLOR_YELLOW}Invalid spell number. Please choose a number from the list or 'x' to cancel.{COLOR_RESET}")

    except ValueError:
        add_log(f"{COLOR_YELLOW}Invalid input. Please enter a number or 'x' to cancel.{COLOR_RESET}")


# ---------------------------------------------------------------------------
# Trophy / Taxidermist helpers
# ---------------------------------------------------------------------------

def get_trophy_drop(monster_name):
    """
    Return a Trophy item if the killed monster has a drop entry and the roll succeeds.
    Returns None if no drop occurs.
    """
    entry = TROPHY_DROPS.get(monster_name)
    if not entry:
        return None
    trophy_name, trophy_desc, trophy_value, drop_chance = entry
    if random.random() > drop_chance:
        return None
    return Trophy(
        name=trophy_name,
        description=trophy_desc,
        value=trophy_value,
        level=0,
        monster_source=monster_name,
        count=1
    )


def _drop_bug_gear(player_character):
    """25% chance to drop a random bug weapon or armor after killing a bug monster."""
    from .items import Weapon, Armor
    if random.random() > 0.25:
        return
    # 50/50 weapon or armor
    if random.random() < 0.5:
        template = random.choice(BUG_WEAPON_TEMPLATES)
        item = Weapon(
            name=template['name'], description=template['description'],
            attack_bonus=template['attack_bonus'], value=template['value'],
            level=template['level'], upgrade_level=0,
            elemental_strength=template.get('elemental_strength', ["None"]),
        )
    else:
        template = random.choice(BUG_ARMOR_TEMPLATES)
        item = Armor(
            name=template['name'], description=template['description'],
            defense_bonus=template['defense_bonus'], value=template['value'],
            level=template['level'], upgrade_level=0,
            elemental_strength=template.get('elemental_strength', ["None"]),
        )
    player_character.inventory.add_item(item)
    add_log(f"{COLOR_GREEN}The bug dropped some gear: {item.name}!{COLOR_RESET}")


def get_player_trophies(player_character):
    """Return dict of {trophy_name: count} from player inventory."""
    counts = {}
    for item in player_character.inventory.items:
        if isinstance(item, Trophy):
            counts[item.name] = counts.get(item.name, 0) + getattr(item, 'count', 1)
    return counts


def get_collection_status(player_character):
    """
    Returns list of (collection_name, data, pieces_have, complete) for display.
    pieces_have = {piece_name: count_owned}
    """
    trophies = get_player_trophies(player_character)
    result = []
    for cname, cdata in TAXIDERMIST_COLLECTIONS.items():
        pieces_have = {p: trophies.get(p, 0) for p in cdata["pieces"]}
        complete = all(pieces_have[p] >= 1 for p in cdata["pieces"])
        result.append((cname, cdata, pieces_have, complete))
    return result


def _make_taxidermist_reward(cname, cdata):
    """Create the Treasure accessory reward for a completed collection."""
    return Treasure(
        name=cdata["reward_name"],
        description=cdata["reward_desc"],
        value=cdata["reward_value"],
        level=cdata["reward_level"],
        treasure_type='passive',
        passive_effect=cdata["reward_desc"],
        is_unique=True,
    )
