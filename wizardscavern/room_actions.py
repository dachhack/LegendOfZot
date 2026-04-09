"""
room_actions.py - Room interaction handlers for Wizard's Cavern.
Contains all process_*_action functions for altars, pools, libraries, dungeons,
tombs, gardens, oracles, blacksmith, shrine, alchemist, war room, taxidermist, etc.
"""

import random
import math
from . import game_state as gs
from .game_state import (add_log, COLOR_RED, COLOR_GREEN, COLOR_RESET, COLOR_PURPLE,
                        COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_GREY, BOLD, UNDERLINE,
                        normal_int_range, get_article)
from .game_data import TROPHY_DROPS, TAXIDERMIST_COLLECTIONS, BUG_MONSTER_TEMPLATES, BUG_GARDEN_INGREDIENTS
from .items import (Item, Potion, Weapon, Armor, Scroll, Spell, Treasure, Towel,
                   Flare, Lantern, LanternFuel, Food, Meat, CookingKit, Ingredient,
                   Trophy, Rune, Shard, identify_item, is_item_identified,
                   get_item_display_name, _create_item_copy, roll_buc_status)
from .characters import Monster, get_sorted_inventory, format_item_for_display, burn_inventory_items
from .achievements import check_achievements
from .zotle import check_zotle_guess
from .dungeon import is_wall_at_coordinate
from .item_templates import (POTION_RECIPES, GARDEN_INGREDIENTS, GARDEN_INGREDIENTS_DICT,
                            SPELL_TEMPLATES, POTION_TEMPLATES, WEAPON_TEMPLATES,
                            ARMOR_TEMPLATES, SCROLL_TEMPLATES, FEY_GARDEN_INGREDIENTS)
from .save_system import SaveSystem


# Lazy imports to avoid circular dependencies with game_systems and combat
def _get_trigger_room_interaction():
    from .game_systems import _trigger_room_interaction
    return _trigger_room_interaction

def _get_reveal_adjacent_walls():
    from .vendor import reveal_adjacent_walls
    return reveal_adjacent_walls

def check_pool_protection(character):
    from .game_systems import check_pool_protection as _f; return _f(character)

def create_legendary_monster(shard_type, floor_level):
    from .game_systems import create_legendary_monster as _f; return _f(shard_type, floor_level)

def create_random_enhanced_weapon(floor_level):
    from .game_systems import create_random_enhanced_weapon as _f; return _f(floor_level)

def create_random_enhanced_armor(floor_level):
    from .game_systems import create_random_enhanced_armor as _f; return _f(floor_level)

def get_random_treasure(floor_level, allow_unique=False):
    from .game_systems import get_random_treasure as _f; return _f(floor_level, allow_unique)

def get_repair_cost(item):
    from .items import get_repair_cost as _f; return _f(item)

def handle_inventory_menu(pc, tw, cmd):
    from .game_systems import handle_inventory_menu as _f; return _f(pc, tw, cmd)

def move_player(character, tw, direction, ignore_confusion=False):
    from .game_systems import move_player as _f; return _f(character, tw, direction, ignore_confusion)

def process_combat_action(pc, tw, cmd):
    from .combat import process_combat_action as _f; return _f(pc, tw, cmd)

def get_collection_status(pc):
    from .combat import get_collection_status as _f; return _f(pc)

def _make_taxidermist_reward(cname, cdata):
    from .combat import _make_taxidermist_reward as _f; return _f(cname, cdata)


# --------------------------------------------------------------------------------
# 16. ROOM INTERACTIONS (altars, pools, libraries, dungeons, tombs, gardens, oracles)
# --------------------------------------------------------------------------------

def process_altar_action(player_character, my_tower, cmd):

    # -------------------------------------------------------------------------
    # GOD DEFINITIONS - each god aligned to an item type
    # -------------------------------------------------------------------------
    gods = {
        1: {
            'name': 'Solara, the Radiant Dawn',
            'title': 'Goddess of Life',
            'symbol': '*',
            'color': '#FFD700',
            'item_type': Potion,
            'item_label': 'Potions',
            'altar_desc': 'A pristine altar of white marble radiates warmth. Golden light dances across inscriptions of healing hymns.',
            'pleased_msg': 'Solara\'s divine light transmutes your offering into something greater!',
            'displeased_msg': 'Solara recoils from your unworthy offering!',
        },
        2: {
            'name': 'Zephyros, the Windwalker',
            'title': 'God of the Wild',
            'symbol': '~',
            'color': '#87CEEB',
            'item_type': Ingredient,
            'item_label': 'Ingredients',
            'altar_desc': 'Wind swirls around a sleek silver altar. Feathers float in an endless updraft, never touching the ground.',
            'pleased_msg': 'The Windwalker breathes life into your offering, returning rare gifts from the wilds!',
            'displeased_msg': 'Zephyros howls in displeasure at your mundane gift!',
        },
        3: {
            'name': 'Athenaeum, the All-Knowing',
            'title': 'God of Wisdom',
            'symbol': '@',
            'color': '#9370DB',
            'item_type': Scroll,
            'item_label': 'Scrolls',
            'altar_desc': 'Books orbit a crystalline altar in perfect geometric patterns. Ancient runes glow with arcane knowledge.',
            'pleased_msg': 'Forbidden knowledge flows back to you, transmuted and amplified!',
            'displeased_msg': 'Athenaeum is not amused by your ignorance.',
        },
        4: {
            'name': 'Titanforge, the Unyielding',
            'title': 'God of the Forge',
            'symbol': '#',
            'color': '#DC143C',
            'item_type': Weapon,
            'item_label': 'Weapons',
            'altar_desc': 'An anvil-shaped altar of obsidian and iron. Ghostly hammers ring out in endless rhythm.',
            'pleased_msg': 'The forge god\'s hammer rings! Your weapon is reborn, stronger than before!',
            'displeased_msg': 'Titanforge sneers. A true warrior brings steel, not trinkets!',
        },
        5: {
            'name': 'Lunara, the Moon Sentinel',
            'title': 'Goddess of Protection',
            'symbol': ')',
            'color': '#E6E6FA',
            'item_type': Armor,
            'item_label': 'Armor',
            'altar_desc': 'A crescent altar of silver and moonstone pulses with ethereal energy. Starlight pools in its basin.',
            'pleased_msg': 'Lunara\'s celestial power flows through your armor, reinforcing every plate and fibre!',
            'displeased_msg': 'Lunara turns her back. She guards only those who bring worthy shields.',
        },
        6: {
            'name': 'Loki the Trickster',
            'title': 'God of Fortune',
            'symbol': '?',
            'color': '#FF69B4',
            'item_type': None,  # Accepts anything
            'item_label': 'Anything (wildcards favor rare items)',
            'altar_desc': 'The altar shifts and changes - stone to gold to smoke. Reality seems... negotiable here.',
            'pleased_msg': 'The Trickster laughs! The cosmic dice tumble...',
            'displeased_msg': 'Even the Trickster is bored by this offering.',
        },
        7: {
            'name': 'The Void',
            'title': 'The Cleanser',
            'symbol': 'O',
            'color': '#4B0082',
            'item_type': 'sealed',  # Special: only accepts sealed items
            'item_label': 'Cursed items',
            'altar_desc': 'There is no altar. Only absence. A space where something should be, but isn\'t.',
            'pleased_msg': 'The Void consumes the seal, releasing pure energy...',
            'displeased_msg': 'The Void rejects the unsealed. It hungers only for corruption.',
        },
        8: {
            'name': 'Malachar, the Relentless',
            'title': 'God of Fortitude',
            'symbol': '+',
            'color': '#8B0000',
            'item_type': Treasure,
            'item_label': 'Treasures & Artifacts',
            'altar_desc': 'A jagged altar of darkened iron pulses with raw vitality. Crimson runes glow with life force.',
            'pleased_msg': 'MALACHAR ROARS! Your treasure is consumed and power flows into you!',
            'displeased_msg': 'Malachar demands real treasure, not scraps!',
        },
    }

    def _get_upgrade_scroll(floor_level):
        """Return an upgrade scroll appropriate for the floor level."""
        if floor_level >= 25:
            return Scroll("Scroll of Divine Upgrade", "A godly scroll of enhancement.", "Upgrade items to +20 maximum.", 1200, 25, 'upgrade')
        elif floor_level >= 20:
            return Scroll("Scroll of Mythic Upgrade", "A scroll touched by the gods.", "Upgrade items to +17 maximum.", 850, 20, 'upgrade')
        elif floor_level >= 15:
            return Scroll("Scroll of Epic Upgrade", "A legendary scroll pulsing with power.", "Upgrade items to +14 maximum.", 600, 15, 'upgrade')
        elif floor_level >= 10:
            return Scroll("Scroll of Superior Upgrade", "An ancient scroll of enhancement.", "Upgrade items to +10 maximum.", 400, 10, 'upgrade')
        elif floor_level >= 5:
            return Scroll("Scroll of Greater Upgrade", "A powerful scroll of enhancement.", "Upgrade items to +6 maximum.", 250, 5, 'upgrade')
        else:
            return Scroll("Scroll of Upgrade", "A mystical scroll of enhancement.", "Upgrade items to +3 maximum.", 150, 1, 'upgrade')

    def _item_matches_god(item, god_info):
        """Check if item matches the god's preferred type."""
        item_type = god_info['item_type']
        if item_type is None:
            return True  # Loki accepts anything
        if item_type == 'sealed':
            return getattr(item, 'is_sealed', False)
        return isinstance(item, item_type)

    def _apply_pleased_reward(player_character, item, god_id, god_info, floor_level):
        """Apply the blessed reward when correct item type is sacrificed."""
        add_log(f"<span style='color: {god_info['color']}; font-weight: bold;'>{god_info['symbol']} {god_info['pleased_msg']}</span>")
        add_log("")

        if god_id == 1:
            # Solara (Potions) - returns a better potion
            roll = random.random()
            if roll < 0.20:
                reward = Potion("Superior Healing Potion", "Restores 150 HP.", value=150, level=4, potion_type='healing', effect_magnitude=150)
                add_log(f"{COLOR_GREEN}Your offering is transmuted into a Superior Healing Potion!{COLOR_RESET}")
            elif roll < 0.50:
                reward = Potion("Greater Healing Potion", "Restores 100 HP.", value=100, level=2, potion_type='healing', effect_magnitude=100)
                add_log(f"{COLOR_GREEN}Your offering is transmuted into a Greater Healing Potion!{COLOR_RESET}")
            else:
                # Heal and restore mana
                heal = min(player_character.max_health - player_character.health, 80)
                player_character.health += heal
                mana_restore = 50
                player_character.mana = min(player_character.max_mana, player_character.mana + mana_restore)
                add_log(f"{COLOR_GREEN}Solara blesses you directly! +{heal} HP, +{mana_restore} MP{COLOR_RESET}")
                reward = None
            if reward:
                player_character.inventory.add_item(reward)

        elif god_id == 2:
            # Zephyros (Ingredients) - returns a rare ingredient or gold
            roll = random.random()
            if roll < 0.30 and FEY_GARDEN_INGREDIENTS:
                chosen = random.choice(FEY_GARDEN_INGREDIENTS)
                reward = Ingredient(name=chosen[0], description=chosen[1], value=chosen[2], level=chosen[3])
                add_log(f"{COLOR_GREEN}The wilds return a rare gift: {reward.name}!{COLOR_RESET}")
                player_character.inventory.add_item(reward)
            else:
                gold = item.value * random.randint(3, 6)
                player_character.gold += gold
                add_log(f"{COLOR_GREEN}Zephyros scatters {gold} gold coins from the winds!{COLOR_RESET}")

        elif god_id == 3:
            # Athenaeum (Scrolls) - returns a better scroll
            roll = random.random()
            if roll < 0.40:
                reward = _get_upgrade_scroll(floor_level)
                add_log(f"{COLOR_GREEN}Knowledge transmuted: you receive a {reward.name}!{COLOR_RESET}")
            else:
                # Return a spell scroll or identification scroll
                choices = [s for s in SCROLL_TEMPLATES if s.level <= floor_level + 2 and s.scroll_type in ['spell_scroll', 'identification']]
                if choices:
                    reward = _create_item_copy(random.choice(choices))
                    add_log(f"{COLOR_GREEN}Athenaeum returns a {reward.name}!{COLOR_RESET}")
                else:
                    reward = _get_upgrade_scroll(floor_level)
                    add_log(f"{COLOR_GREEN}You receive a {reward.name}!{COLOR_RESET}")
            player_character.inventory.add_item(reward)

        elif god_id == 4:
            # Titanforge (Weapons) - upgrades the weapon or returns upgraded copy
            if isinstance(item, Weapon):
                roll = random.random()
                bonus_upgrades = random.randint(1, 3) if floor_level < 15 else random.randint(2, 5)
                item.upgrade_level = min(item.upgrade_level + bonus_upgrades, 20)
                add_log(f"{COLOR_GREEN}The forge god's hammer strikes! Your {item.name} gains +{bonus_upgrades} upgrades!{COLOR_RESET}")
                add_log(f"{COLOR_GREEN}Now: {item.get_display_name()} (Atk +{item.attack_bonus}){COLOR_RESET}")
                player_character.inventory.add_item(item)
                if roll < 0.25:
                    scroll = _get_upgrade_scroll(floor_level)
                    player_character.inventory.add_item(scroll)
                    add_log(f"{COLOR_GREEN}And a {scroll.name} falls from the forge fires!{COLOR_RESET}")
            else:
                # Shouldn't happen, but fallback
                player_character.inventory.add_item(item)

        elif god_id == 5:
            # Lunara (Armor) - upgrades the armor or returns upgraded copy
            if isinstance(item, Armor):
                roll = random.random()
                bonus_upgrades = random.randint(1, 3) if floor_level < 15 else random.randint(2, 5)
                item.upgrade_level = min(item.upgrade_level + bonus_upgrades, 20)
                add_log(f"{COLOR_GREEN}Moonlight reinforces your {item.name}! +{bonus_upgrades} upgrades!{COLOR_RESET}")
                add_log(f"{COLOR_GREEN}Now: {item.get_display_name()} (Def +{item.defense_bonus}){COLOR_RESET}")
                player_character.inventory.add_item(item)
                if roll < 0.25:
                    scroll = _get_upgrade_scroll(floor_level)
                    player_character.inventory.add_item(scroll)
                    add_log(f"{COLOR_GREEN}A {scroll.name} materializes in moonlight!{COLOR_RESET}")
            else:
                player_character.inventory.add_item(item)

        elif god_id == 6:
            # Loki (Anything) - random outcome, quality scales with item value
            item_rarity = item.value
            is_rare = item_rarity >= 200
            roll = random.random()
            good_chance = 0.80 if is_rare else 0.50

            if roll < good_chance:
                # Good outcome - random reward
                outcome = random.choice(['upgrade_scroll', 'gold', 'stat', 'better_item'])
                if outcome == 'upgrade_scroll':
                    reward = _get_upgrade_scroll(floor_level)
                    player_character.inventory.add_item(reward)
                    add_log(f"{COLOR_GREEN}The Trickster grins - a {reward.name} appears!{COLOR_RESET}")
                elif outcome == 'gold':
                    gold = item.value * random.randint(4, 8)
                    player_character.gold += gold
                    add_log(f"{COLOR_GREEN}Gold rains down! +{gold} coins!{COLOR_RESET}")
                elif outcome == 'stat':
                    stat = random.choice(['strength', 'dexterity', 'intelligence'])
                    amt = 3 if is_rare else 1
                    setattr(player_character, stat, getattr(player_character, stat) + amt)
                    add_log(f"{COLOR_GREEN}The Trickster pokes your {stat}! +{amt}!{COLOR_RESET}")
                else:
                    reward = get_random_treasure(floor_level, allow_unique=is_rare)
                    player_character.inventory.add_item(reward)
                    add_log(f"{COLOR_GREEN}A {reward.name} tumbles from the chaos!{COLOR_RESET}")
            else:
                # Bad outcome
                _apply_displeased_punishment(player_character, god_info, floor_level)
                return

        elif god_id == 7:
            # The Void (Cursed items) - cleanses curse, grants reward
            if getattr(item, 'is_sealed', False):
                item.is_sealed = False
                add_log(f"{COLOR_CYAN}The curse is consumed by The Void!{COLOR_RESET}")
                add_log(f"{COLOR_GREEN}{item.name} is now purified!{COLOR_RESET}")
                player_character.inventory.add_item(item)
                # Bonus reward
                roll = random.random()
                if roll < 0.50:
                    scroll = _get_upgrade_scroll(floor_level)
                    player_character.inventory.add_item(scroll)
                    add_log(f"{COLOR_GREEN}Void energy crystallizes into a {scroll.name}!{COLOR_RESET}")
                else:
                    gold = random.randint(50, 150) * (floor_level + 1)
                    player_character.gold += gold
                    add_log(f"{COLOR_GREEN}Void energy dissolves into {gold} gold!{COLOR_RESET}")

        elif god_id == 8:
            # Malachar (Treasures) - stat boosts, possibly unique treasure back
            roll = random.random()
            if roll < 0.30:
                # Return a better treasure
                reward = get_random_treasure(floor_level + 2, allow_unique=True)
                player_character.inventory.add_item(reward)
                add_log(f"{COLOR_GREEN}Malachar returns power made manifest: {reward.name}!{COLOR_RESET}")
            elif roll < 0.60:
                # Stat boost
                stat = random.choice(['strength', 'intelligence', 'dexterity'])
                amt = random.randint(1, 3)
                setattr(player_character, stat, getattr(player_character, stat) + amt)
                player_character.base_max_health_bonus += 5
                add_log(f"{COLOR_GREEN}Malachar's power surges through you! {stat.capitalize()} +{amt}, Max HP +5!{COLOR_RESET}")
            else:
                # Gold + max health
                gold = item.value * random.randint(3, 5)
                player_character.gold += gold
                player_character.base_max_health_bonus += 10
                add_log(f"{COLOR_GREEN}Malachar's relentless power: +{gold} gold, Max HP +10!{COLOR_RESET}")

        gs.game_stats['altars_used'] = gs.game_stats.get('altars_used', 0) + 1
        check_achievements(player_character)

    def _apply_displeased_punishment(player_character, god_info, floor_level):
        """Apply punishment when wrong item type sacrificed."""
        add_log(f"<span style='color: {god_info['color']}; font-weight: bold;'>{god_info['symbol']} {god_info['displeased_msg']}</span>")
        add_log("")
        roll = random.random()
        if roll < 0.50:
            # Return a sealed weapon or armor (divine punishment — cannot be upgraded)
            sealed_options = [
                Weapon("Sealed Blade", "A blade bound by dark magic.", attack_bonus=max(1, player_character.z), value=10, level=player_character.z, is_sealed=True, buc_status='cursed'),
                Armor("Sealed Mail", "Armor locked by a divine seal.", defense_bonus=max(1, player_character.z // 2), value=10, level=player_character.z, is_sealed=True, buc_status='cursed'),
            ]
            sealed_item = random.choice(sealed_options)
            player_character.inventory.add_item(sealed_item)
            add_log(f"{COLOR_RED}A {sealed_item.name} materializes in your hands - SEALED!{COLOR_RESET}")
        else:
            # Small gold pittance
            gold = random.randint(5, 20)
            player_character.gold += gold
            add_log(f"{COLOR_YELLOW}The god tosses {gold} gold coins at your feet dismissively.{COLOR_RESET}")

    # -------------------------------------------------------------------------
    # INIT
    # -------------------------------------------------------------------------
    if cmd == "init":
        current_floor = my_tower.floors[player_character.z]
        room = current_floor.grid[player_character.y][player_character.x]

        # Assign blessed god for this altar if not already set
        if 'blessed_god_id' not in room.properties:
            room.properties['blessed_god_id'] = random.choice(list(gods.keys()))

        blessed_god_id = room.properties['blessed_god_id']
        blessed_god_info = gods[blessed_god_id]

        # Hunch - intelligence-based chance of seeing the true god
        hunch_chance = min(0.95, max(0.10, 0.10 + (player_character.intelligence - 10) * 0.03))
        if random.random() < hunch_chance:
            room.properties['hunch_god_id'] = blessed_god_id
        else:
            room.properties['hunch_god_id'] = random.choice(list(gods.keys()))

        add_log(f"{COLOR_PURPLE}You enter a sacred chamber...{COLOR_RESET}")
        add_log(f"{blessed_god_info['altar_desc']}")
        add_log("")
        hunch_god = gods[room.properties['hunch_god_id']]
        add_log(f"{COLOR_CYAN}You sense this altar belongs to {hunch_god['name']}. It hungers for: {hunch_god['item_label']} (INT {player_character.intelligence} intuition){COLOR_RESET}")
        add_log("")
        add_log(f"{COLOR_YELLOW}Sacrifice an item from your inventory. Choose wisely - please the god for great rewards.{COLOR_RESET}")

        # Show Devotion Rune hint if player qualifies
        if not gs.runes_obtained.get('devotion', False):
            gold_req = gs.rune_progress_reqs.get('gold_obtained', 500)
            hp_req = gs.rune_progress_reqs.get('player_health_obtained', 50)
            if player_character.gold >= gold_req and player_character.health >= hp_req:
                add_log("")
                add_log(f"{COLOR_YELLOW}[9] - Offer {gold_req} gold and {hp_req} HP to all gods for the Rune of Devotion.{COLOR_RESET}")

        gs.active_altar_state = {'gods': gods, 'blessed_id': blessed_god_id}
        return

    # -------------------------------------------------------------------------
    # SPECIAL: Devotion Rune ultimate offering (cmd = '9' shortcut kept)
    # -------------------------------------------------------------------------
    if cmd == '9' and not gs.runes_obtained['devotion'] and player_character.gold >= 500 and player_character.health >= 50:
        add_log("")
        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        add_log(f"{COLOR_YELLOW}You offer 500 gold and 50 health to all the gods...{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        add_log("")
        player_character.gold -= 500
        player_character.health -= 50
        player_character.base_max_health_bonus += 20
        player_character.strength += 2
        player_character.intelligence += 2
        add_log(f"{COLOR_GREEN}The gods accept your ultimate sacrifice!{COLOR_RESET}")
        add_log(f"{COLOR_GREEN}Maximum Health +20 | Strength +2 | Intelligence +2{COLOR_RESET}")
        rune = Rune(name="Rune of Devotion", rune_type='devotion',
                    description="A radiant rune pulsing with holy light.", value=0, level=0)
        player_character.inventory.add_item(rune)
        gs.runes_obtained['devotion'] = True
        add_log("")
        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        add_log(f"{COLOR_YELLOW}* THE RUNE OF DEVOTION IS YOURS! *{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        current_floor = my_tower.floors[player_character.z]
        room = current_floor.grid[player_character.y][player_character.x]
        room.room_type = '.'
        gs.active_altar_state = None
        _get_trigger_room_interaction()(player_character, my_tower)
        return

    # -------------------------------------------------------------------------
    # ITEM SACRIFICE - player types s# to sacrifice that inventory item (e.g., s1, s2)
    # -------------------------------------------------------------------------
    if (cmd.startswith('s') and len(cmd) > 1 and cmd[1:].isdigit()):
        item_index = int(cmd[1:]) - 1
        sorted_items = get_sorted_inventory(player_character.inventory)
        # Filter out Runes, Shards and Keys - those can't be sacrificed
        sacrificeable = [it for it in sorted_items if not isinstance(it, (Rune, Shard))]

        if 0 <= item_index < len(sacrificeable):
            item = sacrificeable[item_index]
            blessed_id = gs.active_altar_state['blessed_id']
            god_info = gods[blessed_id]
            floor_level = player_character.z

            add_log("")
            add_log(f"{COLOR_PURPLE}You place {item.name} upon the altar...{COLOR_RESET}")
            add_log("")

            # Remove item from inventory first
            player_character.inventory.remove_item(item.name)

            # Check if item matches god's affinity
            if _item_matches_god(item, god_info):
                _apply_pleased_reward(player_character, item, blessed_id, god_info, floor_level)
            else:
                _apply_displeased_punishment(player_character, god_info, floor_level)

            # Destroy altar
            add_log("")
            add_log(f"{COLOR_PURPLE}The altar crumbles to dust, its divine power spent.{COLOR_RESET}")
            current_floor = my_tower.floors[player_character.z]
            room = current_floor.grid[player_character.y][player_character.x]
            room.room_type = '.'
            gs.active_altar_state = None
            _get_trigger_room_interaction()(player_character, my_tower)
        else:
            add_log(f"{COLOR_YELLOW}No item at that number. Use s1-s{len(sacrificeable)} to sacrifice.{COLOR_RESET}")
        return

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # BUC ALTAR ACTIONS: Detect, Bless, Purify
    # -------------------------------------------------------------------------
    if cmd == 'd':
        # DETECT BUC — reveals BUC status of all equipped items
        equipped = [('weapon', player_character.equipped_weapon),
                    ('armor', player_character.equipped_armor)]
        equipped += [(f'acc {i+1}', acc) for i, acc in enumerate(player_character.equipped_accessories) if acc]
        revealed_any = False
        for slot_name, item in equipped:
            if item and hasattr(item, 'buc_known') and not item.buc_known:
                item.buc_known = True
                revealed_any = True
                if item.buc_status == 'blessed':
                    add_log(f"{COLOR_GREEN}Your {slot_name} ({item.name}) glows BLUE — it is blessed!{COLOR_RESET}")
                elif item.buc_status == 'cursed':
                    add_log(f"{COLOR_RED}Your {slot_name} ({item.name}) glows BLACK — it is cursed!{COLOR_RESET}")
                else:
                    add_log(f"{COLOR_GREY}Your {slot_name} ({item.name}) glows WHITE — it is uncursed.{COLOR_RESET}")
        if not revealed_any:
            add_log(f"{COLOR_YELLOW}You already know the BUC status of all your equipped gear.{COLOR_RESET}")
        else:
            add_log(f"{COLOR_CYAN}The altar's light fades.{COLOR_RESET}")
        return

    elif cmd == 'b':
        # BLESS ITEM — upgrade one equipped uncursed item to blessed (costs gold)
        bless_cost = 100 + player_character.z * 10
        candidates = []
        if player_character.equipped_weapon and getattr(player_character.equipped_weapon, 'buc_status', '') == 'uncursed':
            candidates.append(('weapon', player_character.equipped_weapon))
        if player_character.equipped_armor and getattr(player_character.equipped_armor, 'buc_status', '') == 'uncursed':
            candidates.append(('armor', player_character.equipped_armor))
        if not candidates:
            add_log(f"{COLOR_YELLOW}You have no uncursed equipped weapon or armor to bless.{COLOR_RESET}")
            add_log(f"{COLOR_GREY}(Items must be uncursed. Remove curse first if cursed.){COLOR_RESET}")
            return
        if player_character.gold < bless_cost:
            add_log(f"{COLOR_RED}Blessing requires {bless_cost} gold. You have {player_character.gold}.{COLOR_RESET}")
            return
        # Bless the first candidate (weapon priority)
        slot_name, item = candidates[0]
        player_character.gold -= bless_cost
        item.buc_status = 'blessed'
        item.buc_known = True
        add_log(f"{COLOR_GREEN}You offer {bless_cost} gold to the altar...{COLOR_RESET}")
        add_log(f"{COLOR_YELLOW}Divine light bathes your {item.name}! It is now BLESSED!{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}(Blessed equipment grants +2 attack or defense.){COLOR_RESET}")
        return

    elif cmd == 'u':
        # PURIFY — remove curse from one equipped item (costs 10% max HP)
        hp_cost = max(5, player_character.max_health // 10)
        cursed_equipped = []
        if player_character.equipped_weapon and getattr(player_character.equipped_weapon, 'buc_status', '') == 'cursed':
            cursed_equipped.append(('weapon', player_character.equipped_weapon))
        if player_character.equipped_armor and getattr(player_character.equipped_armor, 'buc_status', '') == 'cursed':
            cursed_equipped.append(('armor', player_character.equipped_armor))
        if not cursed_equipped:
            add_log(f"{COLOR_YELLOW}None of your equipped items are cursed.{COLOR_RESET}")
            return
        if player_character.health <= hp_cost:
            add_log(f"{COLOR_RED}Purification costs {hp_cost} HP as penance. You don't have enough health.{COLOR_RESET}")
            return
        # Purify the first cursed item
        slot_name, item = cursed_equipped[0]
        player_character.health -= hp_cost
        item.buc_status = 'uncursed'
        item.buc_known = True
        add_log(f"{COLOR_RED}You offer {hp_cost} HP as penance to the altar...{COLOR_RESET}")
        add_log(f"{COLOR_GREEN}The curse on {item.name} is purified! It is now uncursed.{COLOR_RESET}")
        add_log(f"{COLOR_GREY}(You can now unequip it or bless it with gold.){COLOR_RESET}")
        return

    # -------------------------------------------------------------------------
    # NAVIGATION / OTHER
    # -------------------------------------------------------------------------
    if cmd == 'x':
        add_log("You step away from the altar.")
        gs.prompt_cntl = "game_loop"
    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd == 'q':
        gs.game_should_quit = True
        add_log("You abandon the altar.")
    else:
        add_log(f"{COLOR_YELLOW}Enter s# to sacrifice (e.g., s1), 'i' for inventory, or 'x' to exit.{COLOR_RESET}")

def process_pool_action(player_character, my_tower, cmd):

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]

    # Define pool types with themes
    pool_types = {
        'healing': {
            'name': 'Crystalline Spring',
            'symbol': '',
            'color': '#00CED1',
            'description': 'Crystal-clear water bubbles up from an ancient spring. It glows with a soft, inviting light.',
            'effect_desc': 'The water feels warm and soothing to the touch.',
            'outcomes': {
                'major_heal': {'chance': 0.50, 'min': 30, 'max': 50},
                'minor_heal': {'chance': 0.30, 'min': 15, 'max': 25},
                'full_heal': {'chance': 0.15, 'min': 100, 'max': 100},
                'poison': {'chance': 0.05, 'min': 5, 'max': 10}
            }
        },
        'mystical': {
            'name': 'Pool of Insight',
            'symbol': '',
            'color': '#9370DB',
            'description': 'Swirling purple mist rises from this ethereal pool. Glimpses of distant places shimmer on its surface.',
            'effect_desc': 'Your reflection seems sharper, more focused...',
            'outcomes': {
                'intelligence': {'chance': 0.40, 'min': 1, 'max': 3},
                'wisdom': {'chance': 0.30, 'min': 1, 'max': 2},
                'reveal_map': {'chance': 0.20, 'radius': 5},
                'confusion': {'chance': 0.10, 'duration': 3}
            }
        },
        'strength': {
            'name': 'Iron Spring',
            'symbol': '',
            'color': '#DC143C',
            'description': 'Thick, metallic-smelling water fills this dark basin. It looks heavy, almost like liquid iron.',
            'effect_desc': 'The water is surprisingly dense and cold.',
            'outcomes': {
                'strength': {'chance': 0.50, 'min': 1, 'max': 3},
                'health': {'chance': 0.25, 'min': 10, 'max': 20},
                'weakness': {'chance': 0.15, 'min': -2, 'max': -1},
                'damage': {'chance': 0.10, 'min': 10, 'max': 20}
            }
        },
        'agility': {
            'name': 'Quicksilver Pool',
            'symbol': '',
            'color': '#87CEEB',
            'description': 'The water moves with unnatural speed, racing around the basin in endless circles.',
            'effect_desc': 'You can barely see your reflection - the water moves too fast.',
            'outcomes': {
                'dexterity': {'chance': 0.50, 'min': 1, 'max': 3},
                'haste': {'chance': 0.25, 'duration': 4, 'magnitude': 5},
                'slow': {'chance': 0.15, 'duration': 3},
                'slip': {'chance': 0.10, 'min': 5, 'max': 15}
            }
        },
        'cursed': {
            'name': 'Tainted Well',
            'symbol': '',
            'color': '#8B0000',
            'description': 'Murky, foul-smelling water sits stagnant in this corrupted basin. Wisps of dark energy rise from its surface.',
            'effect_desc': 'The stench is overwhelming. This water looks dangerous.',
            'outcomes': {
                'poison': {'chance': 0.40, 'min': 10, 'max': 20},
                'curse': {'chance': 0.30, 'stat': 'random', 'min': -2, 'max': -1},
                'damage': {'chance': 0.20, 'min': 20, 'max': 35},
                'nothing': {'chance': 0.10}  # Lucky escape
            }
        },
        'golden': {
            'name': 'Fortune\'s Font',
            'symbol': '',
            'color': '#FFD700',
            'description': 'Golden coins glitter at the bottom of this ornate fountain. The water sparkles with an otherworldly sheen.',
            'effect_desc': 'Is that... gold in the water?',
            'outcomes': {
                'gold_major': {'chance': 0.35, 'min': 100, 'max': 300},
                'gold_minor': {'chance': 0.35, 'min': 30, 'max': 80},
                'item': {'chance': 0.20},  # Random item
                'mimic': {'chance': 0.10, 'min': 50, 'max': 100}  # Fake gold, take damage
            }
        },
        'mysterious': {
            'name': 'Pool of Chance',
            'symbol': '',
            'color': '#FF69B4',
            'description': 'This pool constantly shifts between colors and states. One moment clear, the next murky, then glowing.',
            'effect_desc': 'Who knows what this will do?',
            'outcomes': {
                'random_buff': {'chance': 0.30},  # Any stat +1-3
                'random_debuff': {'chance': 0.20},  # Any stat -1-2
                'teleport': {'chance': 0.20},
                'random_item': {'chance': 0.15},
                'explosion': {'chance': 0.15, 'min': 15, 'max': 40}
            }
        }
    }

    if cmd == "init":
        # Determine pool type for this room if not already set
        if 'pool_type' not in room.properties:
            # Weight pool types - healing and mystical more common
            pool_weights = {
                'healing': 0.25,
                'mystical': 0.20,
                'strength': 0.15,
                'agility': 0.15,
                'cursed': 0.10,
                'golden': 0.10,
                'mysterious': 0.05
            }

            pool_type = random.choices(
                list(pool_weights.keys()),
                weights=list(pool_weights.values()),
                k=1
            )[0]
            room.properties['pool_type'] = pool_type

        pool_type = room.properties['pool_type']
        pool_info = pool_types[pool_type]
        unknown_pool_info="The water has curious properties..."

        # Atmospheric description
        add_log(f"{COLOR_CYAN}{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}A basin of water fills this chamber...{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}{COLOR_RESET}")
        add_log("")
        add_log(f"{unknown_pool_info}")
        #add_log(f"{pool_info['description']}")
        add_log("")

        pool_type_dict = {
            'healing': ('   This looks safe - possibly beneficial.', COLOR_GREEN),
            'strength': ('   You sense magical power here. It might enhance you.', COLOR_CYAN),
            'agility': ('   You sense magical power here. It might enhance you.', COLOR_CYAN),
            'mystical': ('   You sense magical power here. It might enhance you.', COLOR_CYAN),
            'cursed': ('   Warning: Dark magic radiates from this water!', COLOR_RED),
            'golden': ('   Fortune favors the bold... or does it?', COLOR_YELLOW),
            'mysterious': ('   Completely unpredictable. Could be anything.', COLOR_PURPLE)
        }

        insight_chance = 0.15 + (player_character.intelligence * 0.02)
        insight_roll = random.random()

        if insight_roll < 0.2:
            # Close call - somewhat uncertain
            add_log(f"{COLOR_PURPLE} Your keen mind analyzes the water...{COLOR_RESET}")
        elif insight_roll < 0.4:
            # Moderate failure - confused
            add_log(f"{COLOR_PURPLE} You study the water carefully, but something feels... unclear.{COLOR_RESET}")
        else:
            # Bad failure - very uncertain
            add_log(f"{COLOR_PURPLE} The complex enchantments here are clouding your understanding.{COLOR_RESET}")

        # Intelligence-based insight
        if insight_roll < insight_chance:
            # Successful insight - show correct pool typ
            if pool_type in pool_type_dict:
                hint_text, hint_color = pool_type_dict[pool_type]
                add_log(f"{hint_color}{hint_text}{COLOR_RESET}")
        else:
            # Pick a random pool type (possibly the correct one, possibly not)
            random_pool_type = random.choice(list(pool_type_dict.keys()))
            hint_text, hint_color = pool_type_dict[random_pool_type]
            add_log(f"{hint_color}{hint_text}{COLOR_RESET}")

        add_log("")

        #add_log(f"{pool_info['effect_desc']}")
        add_log(f"{COLOR_YELLOW}Will you drink from the basin?{COLOR_RESET}")
        
        # Check if player has a towel
        has_towel = any(isinstance(item, Towel) for item in player_character.inventory.items)
        if has_towel:
            add_log(f"{COLOR_CYAN}(Press 'w' to wet your towel in the water){COLOR_RESET}")

        # Store pool info for render
        room.properties['pool_info'] = pool_info
        return

    if cmd == 'dr':
        # Check if this is Ancient Waters
        is_ancient = room.properties.get('is_ancient', False)
        
        if is_ancient and not gs.runes_obtained['reflection']:
            # ANCIENT WATERS - Special rewards + Rune
            add_log("")
            add_log(f"{COLOR_CYAN}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}You drink from the Ancient Waters...{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}============================================================{COLOR_RESET}")
            add_log("")
            add_log(f"{COLOR_PURPLE}Visions of past and future flood your mind!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}The waters grant you wisdom beyond mortal ken!{COLOR_RESET}")
            add_log("")
            
            # Grant significant stat boosts
            player_character.intelligence += 3
            player_character.max_mana += 30
            player_character.mana = player_character.max_mana
            add_log(f"{COLOR_GREEN}Intelligence +3{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Maximum Mana +30{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Mana fully restored!{COLOR_RESET}")
            
            # Award Rune of Reflection
            rune = Rune(
                name="Rune of Reflection",
                rune_type='reflection',
                description="A shimmering rune that ripples like water. Unlocks the Reflection Shard vault.",
                value=0,
                level=0
            )
            player_character.inventory.add_item(rune)
            
            # QUEST TRACKING - must be done BEFORE marking rune as obtained
            gs.rune_progress['pools_drunk_total'] += 1
            
            gs.runes_obtained['reflection'] = True
            gs.ancient_waters_available = False
            
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}* THE RUNE OF REFLECTION IS YOURS! *{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}The waters crystallize into a glowing rune!{COLOR_RESET}")
            add_log("")
            
            # Empty the pool
            add_log(f"{COLOR_CYAN}The Ancient Waters drain away, their power spent.{COLOR_RESET}")
            room.room_type = '.'
            _get_trigger_room_interaction()(player_character, my_tower)
            return
        
        # Normal pool drinking logic
        pool_type = room.properties.get('pool_type', 'healing')
        pool_info = pool_types[pool_type]

        add_log("")
        add_log(f"{COLOR_CYAN}{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}You drink deeply from the basin...{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}{COLOR_RESET}")
        add_log("")

        # Reveal what type of pool it was
        add_log(f"<span style='color: {pool_info['color']}; font-weight: bold; font-size: 11px;'>{pool_info['symbol']} It was the {pool_info['name']}! {pool_info['symbol']}</span>")
        add_log("")

        # Determine outcome based on pool type
        outcomes = pool_info['outcomes']
        outcome_names = list(outcomes.keys())
        outcome_weights = [outcomes[name]['chance'] for name in outcome_names]
        chosen_outcome = random.choices(outcome_names, weights=outcome_weights, k=1)[0]

        outcome_data = outcomes[chosen_outcome]

        # Process the outcome
        if chosen_outcome in ['major_heal', 'minor_heal', 'full_heal']:
            if chosen_outcome == 'full_heal':
                old_health = player_character.health
                player_character.health = player_character.max_health
                heal_amount = player_character.health - old_health
                add_log(f"{COLOR_GREEN} The water surges with divine power!{COLOR_RESET}")
                add_log(f"{COLOR_GREEN} FULLY RESTORED! Healed {heal_amount} HP!{COLOR_RESET}")
            else:
                heal = random.randint(outcome_data['min'], outcome_data['max'])
                old_health = player_character.health
                player_character.health = min(player_character.max_health, player_character.health + heal)
                actual_heal = player_character.health - old_health
                add_log(f"{COLOR_GREEN} Warm, soothing energy flows through you!{COLOR_RESET}")
                add_log(f"{COLOR_GREEN} Healed {actual_heal} HP! Current health: {player_character.health}{COLOR_RESET}")

        elif chosen_outcome == 'intelligence':
            boost = random.randint(outcome_data['min'], outcome_data['max'])
            player_character.intelligence += boost
            add_log(f"{COLOR_PURPLE} Your mind expands! Clarity floods your thoughts!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE} Intelligence increased by {boost}! Now: {player_character.intelligence}{COLOR_RESET}")

        elif chosen_outcome == 'wisdom':
            boost = random.randint(outcome_data['min'], outcome_data['max'])
            player_character.intelligence += boost  # Using INT as wisdom stat
            add_log(f"{COLOR_PURPLE} Ancient wisdom fills your consciousness!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE} Intelligence increased by {boost}! Now: {player_character.intelligence}{COLOR_RESET}")

        elif chosen_outcome == 'strength':
            boost = random.randint(outcome_data['min'], outcome_data['max'])
            player_character.strength += boost
            add_log(f"{COLOR_RED} Your muscles surge with newfound power!{COLOR_RESET}")
            add_log(f"{COLOR_RED} Strength increased by {boost}! Now: {player_character.strength}{COLOR_RESET}")

        elif chosen_outcome == 'dexterity':
            boost = random.randint(outcome_data['min'], outcome_data['max'])
            player_character.dexterity += boost
            add_log(f"{COLOR_CYAN} Your reflexes sharpen! You feel lighter, faster!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN} Dexterity increased by {boost}! Now: {player_character.dexterity}{COLOR_RESET}")

        elif chosen_outcome == 'health':
            boost = random.randint(outcome_data['min'], outcome_data['max'])
            old_health = player_character.health
            player_character.health = min(player_character.max_health, player_character.health + boost)
            actual_heal = player_character.health - old_health
            add_log(f"{COLOR_GREEN} Vitality courses through your veins!{COLOR_RESET}")
            add_log(f"{COLOR_GREEN} Healed {actual_heal} HP!{COLOR_RESET}")

        elif chosen_outcome == 'poison':
            if not check_pool_protection(player_character):
                damage = random.randint(outcome_data['min'], outcome_data['max'])
                add_log(f"{COLOR_RED} The water burns! You've been poisoned!{COLOR_RESET}")
                player_character.add_status_effect('Poison', 4, 'damage_over_time', damage // 2, 'Poisoned by cursed water')
                if player_character.take_damage_no_def(damage):
                    add_log(f"{COLOR_RED}The poison was too strong... you collapse.{COLOR_RESET}")
                    gs.game_should_quit = True
                    return
                add_log(f"{COLOR_RED} Took {damage} immediate damage! Poison will continue...{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'weakness':
            if not check_pool_protection(player_character):
                reduction = random.randint(outcome_data['min'], outcome_data['max'])
                stat = random.choice(['strength', 'dexterity', 'intelligence'])
                old_val = getattr(player_character, stat)
                setattr(player_character, stat, max(1, old_val + reduction))
                add_log(f"{COLOR_RED} You feel weaker... something's wrong!{COLOR_RESET}")
                add_log(f"{COLOR_RED} {stat.capitalize()} decreased by {abs(reduction)}!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'damage':
            if not check_pool_protection(player_character):
                dmg = random.randint(outcome_data['min'], outcome_data['max'])
                add_log(f"{COLOR_RED} The water explodes with dark energy!{COLOR_RESET}")
                if player_character.take_damage_no_def(dmg):
                    add_log(f"{COLOR_RED}The explosion was fatal...{COLOR_RESET}")
                    gs.game_should_quit = True
                    return
                add_log(f"{COLOR_RED} Took {dmg} damage! Current HP: {player_character.health}{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'haste':
            duration = outcome_data.get('duration', 3)
            magnitude = outcome_data.get('magnitude', 5)
            player_character.add_status_effect('Haste', duration, 'attack_boost', magnitude, 'Moving at incredible speed!')
            add_log(f"{COLOR_CYAN} Time seems to slow around you! You move with incredible speed!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN} Haste active for {duration} turns! (+{magnitude} attack){COLOR_RESET}")

        elif chosen_outcome == 'confusion':
            if not check_pool_protection(player_character):
                duration = outcome_data.get('duration', 3)
                player_character.add_status_effect('Confusion', duration, 'confusion', 0, 'The world spins...')
                add_log(f"{COLOR_PURPLE} Your head spins! Which way is up?!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE} Confused for {duration} turns!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'slow':
            if not check_pool_protection(player_character):
                duration = outcome_data.get('duration', 3)
                player_character.add_status_effect('Slow', duration, 'attack_boost', -3, 'Moving through molasses...')
                add_log(f"{COLOR_YELLOW} Everything feels so... slow...{COLOR_RESET}")
                add_log(f"{COLOR_YELLOW} Slowed for {duration} turns! (-3 attack){COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'reveal_map':
            radius = outcome_data.get('radius', 5)
            revealed = 0
            current_floor = my_tower.floors[player_character.z]
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    ty = player_character.y + dy
                    tx = player_character.x + dx
                    if 0 <= ty < current_floor.rows and 0 <= tx < current_floor.cols:
                        if not current_floor.grid[ty][tx].discovered:
                            current_floor.grid[ty][tx].discovered = True
                            revealed += 1
            add_log(f"{COLOR_PURPLE} Visions flood your mind! The layout becomes clear!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE} Revealed {revealed} rooms in a {radius*2+1}x{radius*2+1} area!{COLOR_RESET}")

        elif chosen_outcome in ['gold_major', 'gold_minor']:
            gold = random.randint(outcome_data['min'], outcome_data['max'])
            player_character.gold += gold
            add_log(f"{COLOR_YELLOW} Gold materializes in your hands!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW} Found {gold} gold! Total: {player_character.gold}{COLOR_RESET}")
            gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + gold
            check_achievements(player_character)

        elif chosen_outcome == 'item':
            # Give random potion
            potion_choices = [p for p in POTION_TEMPLATES if p.level <= player_character.z + 2]
            if potion_choices:
                item_template = random.choice(potion_choices)
                new_item = _create_item_copy(item_template)
                player_character.inventory.add_item(new_item)
                add_log(f"{COLOR_GREEN} Something materializes from the water!{COLOR_RESET}")
                add_log(f"{COLOR_GREEN} Found: {new_item.name}!{COLOR_RESET}")

        elif chosen_outcome == 'mimic':
            if not check_pool_protection(player_character):
                dmg = random.randint(outcome_data['min'], outcome_data['max'])
                add_log(f"{COLOR_RED} The 'gold' was an illusion! Sharp pain shoots through you!{COLOR_RESET}")
                if player_character.take_damage_no_def(dmg):
                    add_log(f"{COLOR_RED}The trap was lethal...{COLOR_RESET}")
                    gs.game_should_quit = True
                    render()
                    return
                add_log(f"{COLOR_RED} Took {dmg} damage from the trap!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'teleport':
            if not check_pool_protection(player_character):
                add_log(f"{COLOR_PURPLE} Reality bends! Space twists around you!{COLOR_RESET}")
                current_floor = my_tower.floors[player_character.z]
                for _ in range(100):
                    rx = random.randint(0, current_floor.cols - 1)
                    ry = random.randint(0, current_floor.rows - 1)
                    if not is_wall_at_coordinate(current_floor, ry, rx):
                        player_character.x = rx
                        player_character.y = ry
                        current_floor.grid[ry][rx].discovered = True
                        _get_reveal_adjacent_walls()(player_character, my_tower)
                        add_log(f"{COLOR_PURPLE} You find yourself elsewhere! ({rx}, {ry}){COLOR_RESET}")
                        break
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'random_buff':
            stat = random.choice(['strength', 'dexterity', 'intelligence'])
            boost = random.randint(1, 3)
            old_val = getattr(player_character, stat)
            setattr(player_character, stat, old_val + boost)
            add_log(f"{COLOR_GREEN} Chaotic energy empowers you!{COLOR_RESET}")
            add_log(f"{COLOR_GREEN} {stat.capitalize()} increased by {boost}!{COLOR_RESET}")

        elif chosen_outcome == 'random_debuff':
            if not check_pool_protection(player_character):
                stat = random.choice(['strength', 'dexterity', 'intelligence'])
                reduction = random.randint(1, 2)
                old_val = getattr(player_character, stat)
                setattr(player_character, stat, max(1, old_val - reduction))
                add_log(f"{COLOR_RED} Chaotic energy weakens you!{COLOR_RESET}")
                add_log(f"{COLOR_RED} {stat.capitalize()} decreased by {reduction}!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'explosion':
            if not check_pool_protection(player_character):
                dmg = random.randint(outcome_data['min'], outcome_data['max'])
                add_log(f"{COLOR_RED} THE POOL EXPLODES!{COLOR_RESET}")
                if player_character.take_damage_no_def(dmg):
                    add_log(f"{COLOR_RED}The explosion was too powerful...{COLOR_RESET}")
                    gs.game_should_quit = True
                    return
                add_log(f"{COLOR_RED} Took {dmg} explosive damage!{COLOR_RESET}")
                burn_inventory_items(player_character, source='explosion')
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'curse':
            if not check_pool_protection(player_character):
                stat = random.choice(['strength', 'dexterity', 'intelligence'])
                reduction = random.randint(outcome_data['min'], outcome_data['max'])
                old_val = getattr(player_character, stat)
                setattr(player_character, stat, max(1, old_val + reduction))
                add_log(f"{COLOR_RED} A curse falls upon you!{COLOR_RESET}")
                add_log(f"{COLOR_RED} {stat.capitalize()} decreased by {abs(reduction)}!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREEN}The water was purified by your Rhyton!{COLOR_RESET}")

        elif chosen_outcome == 'nothing':
            add_log(f"{COLOR_GREY}... Nothing happens.{COLOR_RESET}")
            add_log(f"{COLOR_GREY}The water tasted awful, but at least you're alive.{COLOR_RESET}")

        # QUEST TRACKING: Rune of Reflection
        if not gs.runes_obtained['reflection']:
            gs.rune_progress['pools_drunk_total'] += 1
            if gs.rune_progress['pools_drunk_total'] >= gs.rune_progress_reqs['pools_drunk_total'] and not gs.ancient_waters_available:
                gs.ancient_waters_available = True
                add_log(f"{COLOR_PURPLE}Your visions align... Ancient Waters have manifested!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}Seek them in a mystical pool to claim the Rune of Reflection.{COLOR_RESET}")

        # Empty the pool
        add_log("")
        add_log(f"{COLOR_CYAN}The basin drains empty, its magic spent.{COLOR_RESET}")
        room.room_type = '.'
        _get_trigger_room_interaction()(player_character, my_tower)

    elif cmd == 'i':
         gs.prompt_cntl = "inventory"
         handle_inventory_menu(player_character, my_tower, "init")

    elif cmd in ['n', 's', 'e', 'w']:
         moved = move_player(player_character, my_tower, cmd)
         if not moved:
             gs.prompt_cntl = "pool_mode"

    elif cmd == 'q':
         gs.game_should_quit = True
         add_log("Exiting game.")
    
    elif cmd == 'w':
        # Wet towel in the pool
        towel = None
        for item in player_character.inventory.items:
            if isinstance(item, Towel):
                towel = item
                break
        
        if towel:
            towel.wet()
            add_log(f"{COLOR_CYAN}You dip your towel in the water.{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Your towel is now {towel._get_wetness_description()}!{COLOR_RESET}")
            # Don't drain the pool - you can still drink from it
        else:
            add_log(f"{COLOR_YELLOW}You don't have a towel to wet.{COLOR_RESET}")
    
    else:
        add_log("Invalid command for pool.")

def process_library_action(player_character, my_tower, cmd):

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    library_coords = (player_character.x, player_character.y, player_character.z)

    if cmd == "init":
        if library_coords in gs.searched_libraries:
            add_log("You've already searched this library thoroughly. The shelves are empty.")
            room.room_type = '.'
            # Commands now shown in HTML and placeholder
        else:
            add_log("Ancient tomes line the dusty shelves. You could search for useful grimoires here.")
            # Commands now shown in HTML and placeholder
        return

    if cmd == 'r':
        # Check if this is the Codex of Zot
        has_codex = room.properties.get('has_codex', False)
        
        if has_codex and not gs.runes_obtained['knowledge']:
            # CODEX OF ZOT - Special rewards + Rune
            add_log("")
            add_log(f"{COLOR_CYAN}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}You pull the ancient Codex from the shelf...{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}============================================================{COLOR_RESET}")
            add_log("")
            add_log(f"{COLOR_YELLOW}Arcane symbols dance across the pages!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}Knowledge beyond mortal comprehension floods your mind!{COLOR_RESET}")
            add_log("")
            
            # Grant significant intelligence and mana boost
            player_character.intelligence += 3
            player_character.max_mana += 40
            add_log(f"{COLOR_GREEN}Intelligence +3{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Maximum Mana +40{COLOR_RESET}")
            
            # Grant a powerful spell
            high_level_spells = [s for s in SPELL_TEMPLATES if s.level >= 3]
            if high_level_spells:
                found_spell = random.choice(high_level_spells)
                new_spell = Spell(
                    name=found_spell.name,
                    level=found_spell.level,
                    mana_cost=found_spell.mana_cost,
                    spell_type=found_spell.spell_type,
                    damage_min=found_spell.damage_min,
                    damage_max=found_spell.damage_max,
                    elemental_type=found_spell.elemental_type,
                    description=found_spell.description,
                    status_effect_type=found_spell.status_effect_type,
                    status_effect_duration=found_spell.status_effect_duration,
                    status_effect_magnitude=found_spell.status_effect_magnitude
                )
                player_character.inventory.add_item(new_spell)
                add_log(f"{COLOR_CYAN}You learned the spell: {new_spell.name} (Level {new_spell.level})!{COLOR_RESET}")
            
            # Award Rune of Knowledge
            rune = Rune(
                name="Rune of Knowledge",
                rune_type='knowledge',
                description="A luminous rune pulsing with arcane wisdom. Unlocks the Knowledge Shard vault.",
                value=0,
                level=0
            )
            player_character.inventory.add_item(rune)
            gs.runes_obtained['knowledge'] = True
            gs.codex_available = False
            
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}* THE RUNE OF KNOWLEDGE IS YOURS! *{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}The Codex dissolves into a glowing rune!{COLOR_RESET}")
            add_log("")
            
            gs.searched_libraries[library_coords] = True
            room.room_type = '.'
            gs.prompt_cntl = "game_loop"
            return
        
        # Normal library search logic
        if library_coords in gs.searched_libraries:
            add_log("You've already searched this library. Nothing left to find.")
            return

        add_log(f"{COLOR_CYAN}You begin searching through the dusty tomes...{COLOR_RESET}")

        # Base chance to find something: 60%
        find_chance = 0.60 + (player_character.intelligence * 0.02)  # +2% per INT
        find_chance = min(0.95, find_chance)  # Cap at 95%

        if random.random() > find_chance:
            add_log("After extensive searching, you find nothing but mundane texts and moth-eaten pages.")
            gs.searched_libraries[library_coords] = True  # Mark as searched even if nothing found
            room.room_type = '.'
            gs.prompt_cntl = "game_loop"
            return

        add_log(f"{COLOR_GREEN}You found a grimoire!{COLOR_RESET}")

        # Determine spell level based on floor and player level
        min_spell_level = max(0, player_character.z - 1)
        max_spell_level = min(5, player_character.z + 2)

        available_spells = [s for s in SPELL_TEMPLATES if min_spell_level <= s.level <= max_spell_level]

        if not available_spells:
            available_spells = SPELL_TEMPLATES  # Fallback to all spells

        found_spell = random.choice(available_spells)

        # Check if this spell is already known/identified
        spell_already_known = found_spell.name in gs.identified_items

        # Show intelligence-based hint about the spell
        hint = f"{COLOR_PURPLE}You examine the tome...{COLOR_RESET}\n"

        if player_character.intelligence >= 8:
            hint += f"It appears to be a Level {found_spell.level} grimoire.\n"

        if player_character.intelligence >= 12:
            if found_spell.spell_type == 'damage':
                hint += f"It contains Combat Magic.\n"
            elif found_spell.spell_type == 'healing':
                hint += f"It contains Restorative Magic.\n"
            elif found_spell.spell_type == 'add_status_effect':
                hint += f"It contains Enhancement Magic.\n"
            elif found_spell.spell_type == 'remove_status':
                hint += f"It contains Cleansing Magic.\n"

        if player_character.intelligence >= 16:
            if found_spell.spell_type == 'damage':
                hint += f"The spell deals {found_spell.damage_type} damage.\n"
            elif found_spell.spell_type == 'healing':
                hint += f"The spell heals approximately {found_spell.base_power} HP.\n"

        if spell_already_known:
            hint += f"You recognize it as '{found_spell.name}' (Costs {found_spell.mana_cost} MP).\n"

        add_log(hint)
        add_log(f"{COLOR_YELLOW}Do you want to attempt to read this grimoire? (y/n){COLOR_RESET}")

        # Store the found spell temporarily
        room.properties['found_spell'] = found_spell
        gs.prompt_cntl = 'library_read_decision_mode'
        return

    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")

    elif cmd in ['n', 's', 'e', 'w']:
        moved = move_player(player_character, my_tower, cmd)
        if not moved:
            gs.prompt_cntl = "library_mode"

    elif cmd == 'q':
        gs.game_should_quit = True
        add_log("Leaving the library and the world behind.")
    else:
        add_log("Invalid command for library.")

def process_library_read_decision(player_character, my_tower, cmd):

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    library_coords = (player_character.x, player_character.y, player_character.z)

    if cmd == 'y':
        found_spell = room.properties.get('found_spell')

        if not found_spell:
            add_log("Error: No spell found to read.")
            gs.prompt_cntl = "game_loop"
            return

        # Mark library as searched
        gs.searched_libraries[library_coords] = True

        add_log(f"{COLOR_CYAN}You carefully open the grimoire and attempt to decipher its ancient text...{COLOR_RESET}")

        # Reading difficulty check
        read_success_chance = 0.50 + (player_character.intelligence * 0.03) - (found_spell.level * 0.10)
        read_success_chance = max(0.10, min(0.95, read_success_chance))

        if random.random() < read_success_chance:
            # Success!
            new_spell = Spell(
                name=found_spell.name,
                description=found_spell.description,
                mana_cost=found_spell.mana_cost,
                damage_type=found_spell.damage_type,
                base_power=found_spell.base_power,
                level=found_spell.level,
                spell_type=found_spell.spell_type,
                status_effect_name=found_spell.status_effect_name,
                status_effect_duration=found_spell.status_effect_duration,
                status_effect_type=found_spell.status_effect_type,
                status_effect_magnitude=found_spell.status_effect_magnitude
            )
            player_character.inventory.add_item(new_spell)
            add_log(f"{COLOR_GREEN}Success! You deciphered the grimoire and extracted the spell!{COLOR_RESET}")
            add_log(f"The unidentified spell has been added to your inventory. Take it to a vendor to identify it.")

            # Track stats
            gs.game_stats['spells_learned'] = gs.game_stats.get('spells_learned', 0) + 1
            gs.game_stats['grimoires_read'] = gs.game_stats.get('grimoires_read', 0) + 1
            
            # Note: Rune of Knowledge progress is now tracked when spells are MEMORIZED, not when added to inventory
            
            check_achievements(player_character)
        else:
            # Failure - backfire!
            add_log(f"{COLOR_RED}The arcane text is too complex! The spell backfires!{COLOR_RESET}")

            backfire_outcomes = ['damage', 'status_poison', 'status_confusion', 'mana_drain', 'stat_drain']
            backfire = random.choice(backfire_outcomes)

            if backfire == 'damage':
                damage = random.randint(10, 25) + (found_spell.level * 5)
                add_log(f"{COLOR_RED}Magical energy lashes out at you!{COLOR_RESET}")
                if player_character.take_damage_no_def(damage):
                    add_log(f"{COLOR_RED}You have been defeated by the backfiring spell... Game Over!{COLOR_RESET}")
                    gs.prompt_cntl = "death_screen"
                    return

            elif backfire == 'status_poison':
                player_character.add_status_effect(
                    effect_name='Poison',
                    duration=4,
                    effect_type='damage_over_time',
                    magnitude=8,
                    description='Poisoned by corrupted magic.'
                )
                add_log(f"{COLOR_RED}Toxic magic courses through your veins!{COLOR_RESET}")

            elif backfire == 'status_confusion':
                player_character.add_status_effect(
                    effect_name='Confusion',
                    duration=3,
                    effect_type='confusion',
                    description='Your mind reels from the arcane overload.'
                )
                add_log(f"{COLOR_RED}Your mind becomes clouded with confusion!{COLOR_RESET}")

            elif backfire == 'mana_drain':
                mana_lost = min(player_character.mana, random.randint(15, 30))
                player_character.mana -= mana_lost
                add_log(f"{COLOR_RED}The spell drains {mana_lost} of your mana!{COLOR_RESET}")

            elif backfire == 'stat_drain':
                stats = ['strength', 'dexterity', 'intelligence']
                stat = random.choice(stats)
                drain = random.randint(1, 3)
                current_val = getattr(player_character, stat)
                setattr(player_character, stat, max(1, current_val - drain))
                add_log(f"{COLOR_RED}The backlash weakens you! {stat.capitalize()} decreased by {drain}!{COLOR_RESET}")

            # Track backfire
            gs.game_stats['spell_backfires'] = gs.game_stats.get('spell_backfires', 0) + 1
            check_achievements(player_character)

        # Clear the spell from room properties
        room.properties.pop('found_spell', None)

        # ADD THESE LINES - Convert library to empty room
        room.room_type = '.'
        add_log(f"{COLOR_GREY}The library's knowledge has been exhausted. The shelves are now empty.{COLOR_RESET}")

        _get_trigger_room_interaction()(player_character, my_tower)  # Re-evaluate as empty room
        # prompt_cntl will be set by _trigger_room_interaction
        # render() removed - will be called by process_command

    elif cmd in ('x', 'n'):
        add_log(f"{COLOR_YELLOW}You decide not to risk reading the grimoire and set it aside.{COLOR_RESET}")
        add_log("The book crumbles to dust, its magic fading away...")

        # Mark library as searched
        gs.searched_libraries[library_coords] = True

        # Clear the spell from room properties
        room.properties.pop('found_spell', None)

        # ADD THESE LINES - Convert library to empty room
        room.room_type = '.'
        add_log(f"{COLOR_GREY}The library's shelves are now empty.{COLOR_RESET}")

        _get_trigger_room_interaction()(player_character, my_tower)  # Re-evaluate as empty room
        # prompt_cntl will be set by _trigger_room_interaction
        # render() removed - will be called by process_command

    else:
        add_log(f"{COLOR_YELLOW}Invalid input. Enter 'y' to read the grimoire or 'n' to discard it.{COLOR_RESET}")

def process_library_book_selection(player_character, my_tower, cmd):

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    library_coords = (player_character.x, player_character.y, player_character.z)

    if cmd == 'x':
        add_log("You decide not to take any books for now.")
        gs.prompt_cntl = "library_mode"
        return

    try:
        book_index = int(cmd) - 1
        available_books = room.properties.get('available_books', [])

        if 0 <= book_index < len(available_books):
            found_spell = available_books[book_index]

            # Mark library as searched since they're taking a book
            gs.searched_libraries[library_coords] = True

            add_log(f"{COLOR_CYAN}You carefully remove the tome and attempt to decipher its ancient text...{COLOR_RESET}")

            # Reading difficulty check - slightly better chance since they chose
            read_success_chance = 0.55 + (player_character.intelligence * 0.03) - (found_spell.level * 0.10)
            read_success_chance = max(0.15, min(0.95, read_success_chance))

            if random.random() < read_success_chance:
                # Success!
                new_spell = Spell(
                    name=found_spell.name,
                    description=found_spell.description,
                    mana_cost=found_spell.mana_cost,
                    damage_type=found_spell.damage_type,
                    base_power=found_spell.base_power,
                    level=found_spell.level,
                    spell_type=found_spell.spell_type,
                    status_effect_name=found_spell.status_effect_name,
                    status_effect_duration=found_spell.status_effect_duration,
                    status_effect_type=found_spell.status_effect_type,
                    status_effect_magnitude=found_spell.status_effect_magnitude
                )
                player_character.inventory.add_item(new_spell)
                add_log(f"{COLOR_GREEN}Success! You've learned the spell '{found_spell.name}' (Level {found_spell.level})!{COLOR_RESET}")
                add_log(f"The spell has been added to your inventory. Use spell memorization to prepare it for use.")

                # Track stats
                gs.game_stats['spells_learned'] = gs.game_stats.get('spells_learned', 0) + 1
                gs.game_stats['grimoires_read'] = gs.game_stats.get('grimoires_read', 0) + 1
                check_achievements(player_character)
            else:
                # Failure - backfire!
                add_log(f"{COLOR_RED}The arcane text is too complex! The spell backfires!{COLOR_RESET}")

                backfire_outcomes = ['damage', 'status_poison', 'status_confusion', 'mana_drain', 'stat_drain']
                backfire = random.choice(backfire_outcomes)

                if backfire == 'damage':
                    damage = random.randint(10, 25) + (found_spell.level * 5)
                    add_log(f"{COLOR_RED}Magical energy lashes out at you!{COLOR_RESET}")
                    if player_character.take_damage_no_def(damage):
                        add_log(f"{COLOR_RED}You have been defeated by the backfiring spell... Game Over!{COLOR_RESET}")
                        gs.prompt_cntl = "death_screen"
                        return

                elif backfire == 'status_poison':
                    player_character.add_status_effect(
                        effect_name='Poison',
                        duration=4,
                        effect_type='damage_over_time',
                        magnitude=8,
                        description='Poisoned by corrupted magic.'
                    )
                    add_log(f"{COLOR_RED}Toxic magic courses through your veins!{COLOR_RESET}")

                elif backfire == 'status_confusion':
                    player_character.add_status_effect(
                        effect_name='Confusion',
                        duration=3,
                        effect_type='confusion',
                        description='Your mind reels from the arcane overload.'
                    )
                    add_log(f"{COLOR_RED}Your mind becomes clouded with confusion!{COLOR_RESET}")

                elif backfire == 'mana_drain':
                    mana_lost = min(player_character.mana, random.randint(15, 30))
                    player_character.mana -= mana_lost
                    add_log(f"{COLOR_RED}The spell drains {mana_lost} of your mana!{COLOR_RESET}")

                elif backfire == 'stat_drain':
                    stats = ['strength', 'dexterity', 'intelligence']
                    stat = random.choice(stats)
                    drain = random.randint(1, 3)
                    current_val = getattr(player_character, stat)
                    setattr(player_character, stat, max(1, current_val - drain))
                    add_log(f"{COLOR_RED}The backlash weakens you! {stat.capitalize()} decreased by {drain}!{COLOR_RESET}")

                # Track backfire
                gs.game_stats['spell_backfires'] = gs.game_stats.get('spell_backfires', 0) + 1
                check_achievements(player_character)

            # Clear the books from room properties
            room.properties.pop('available_books', None)
            gs.prompt_cntl = "game_loop"
        else:
            add_log(f"{COLOR_YELLOW}Invalid book number. Please choose from the list or 'x' to cancel.{COLOR_RESET}")

    except ValueError:
        add_log(f"{COLOR_YELLOW}Invalid input. Please enter a number or 'x' to cancel.{COLOR_RESET}")

def process_dungeon_action(player_character, my_tower, cmd):
    """Handle locked dungeon room interactions"""
    
    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    coords = (player_character.x, player_character.y, player_character.z)
    
    if cmd == "init":
        # Check if already unlocked
        if coords in gs.unlocked_dungeons:
            add_log(f"{COLOR_CYAN}This dungeon has been unlocked.{COLOR_RESET}")
            if coords in gs.looted_dungeons:
                add_log(f"{COLOR_GREY}The treasure has already been taken.{COLOR_RESET}")
            gs.prompt_cntl = "dungeon_unlocked_mode"
        else:
            # Check if player has the key
            if coords in gs.dungeon_keys:
                add_log(f"{COLOR_CYAN}You have the key to this dungeon!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_YELLOW}This dungeon is locked. A monster on this floor holds the key.{COLOR_RESET}")
            # Stay in dungeon_mode to show the info box
            gs.prompt_cntl = "dungeon_mode"
        return
    
    elif cmd == 'u':  # Unlock
        if coords in gs.dungeon_keys:
            gs.unlocked_dungeons[coords] = True
            add_log(f"{COLOR_GREEN}You unlock the dungeon door!{COLOR_RESET}")
            
            # QUEST TRACKING: Rune of Secrets
            if not gs.runes_obtained['secrets']:
                gs.rune_progress['dungeons_unlocked_total'] += 1
                if gs.rune_progress['dungeons_unlocked_total'] >= gs.rune_progress_reqs['dungeons_unlocked_total'] and not gs.master_dungeon_available:
                    gs.master_dungeon_available = True
                    add_log(f"{COLOR_PURPLE}Your skills as a lockbreaker are renowned... A Master Dungeon awaits!{COLOR_RESET}")
            
            gs.prompt_cntl = "dungeon_unlocked_mode"
        else:
            add_log(f"{COLOR_YELLOW}You don't have the key to this dungeon.{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"
        return
    
    elif cmd == 'r':  # Loot (Raid)
        # Check if this is a Master Dungeon
        is_master = room.properties.get('is_master', False)
        
        if is_master and not gs.runes_obtained['secrets']:
            # MASTER DUNGEON - Special rewards + Rune
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}You unlock the Master Dungeon!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log("")
            add_log(f"{COLOR_CYAN}Treasure beyond imagining gleams in the darkness!{COLOR_RESET}")
            
            # Guaranteed excellent rewards
            gold_amount = random.randint(500, 800)
            player_character.gold += gold_amount
            add_log(f"{COLOR_YELLOW}You found {gold_amount} gold!{COLOR_RESET}")
            
            # Legendary weapon
            weapon = Weapon(
                name="Master's Blade",
                attack_bonus=random.randint(8, 12),
                elemental_strength=['Physical'],
                level=player_character.z,
                description="A legendary blade from the Master Dungeon"
            )
            player_character.inventory.add_item(weapon)
            add_log(f"{COLOR_CYAN}You found the Master's Blade!{COLOR_RESET}")
            
            # Award Rune of Secrets
            rune = Rune(
                name="Rune of Secrets",
                rune_type='secrets',
                description="A shadowy rune wreathed in mystery. Unlocks the Secrets Shard vault.",
                value=0,
                level=0
            )
            player_character.inventory.add_item(rune)
            gs.runes_obtained['secrets'] = True
            gs.master_dungeon_available = False
            
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}* THE RUNE OF SECRETS IS YOURS! *{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Hidden power coalesces into a glowing rune!{COLOR_RESET}")
            add_log("")
            
            gs.looted_dungeons[coords] = True
            gs.game_stats['dungeons_looted'] = gs.game_stats.get('dungeons_looted', 0) + 1
            gs.prompt_cntl = "game_loop"
            return
        
        # Normal dungeon looting
        if coords in gs.unlocked_dungeons and coords not in gs.looted_dungeons:
            # Give minor treasure
            treasure_roll = random.random()
            if treasure_roll < 0.4:  # 40% gold
                gold_amount = random.randint(100, 300)
                player_character.gold += gold_amount
                add_log(f"{COLOR_YELLOW}You found {gold_amount} gold in the dungeon!{COLOR_RESET}")
            elif treasure_roll < 0.7:  # 30% healing potion
                potion = Potion(name="Healing Potion", potion_type='healing', effect_magnitude=50, value=50, level=1, description="Restores 50 HP")
                player_character.inventory.add_item(potion)
                add_log(f"{COLOR_GREEN}You found a {get_item_display_name(potion)}!{COLOR_RESET}")
            else:  # 30% enhanced weapon or armor
                if random.random() < 0.5:
                    weapon = create_random_enhanced_weapon(player_character.z)
                    player_character.inventory.add_item(weapon)
                    add_log(f"{COLOR_CYAN}You found a {weapon.get_display_name()}!{COLOR_RESET}")
                else:
                    armor = create_random_enhanced_armor(player_character.z)
                    player_character.inventory.add_item(armor)
                    add_log(f"{COLOR_CYAN}You found {armor.get_display_name()}!{COLOR_RESET}")
            
            gs.looted_dungeons[coords] = True
            gs.game_stats['dungeons_looted'] = gs.game_stats.get('dungeons_looted', 0) + 1
        else:
            add_log(f"{COLOR_YELLOW}There's nothing left to loot here.{COLOR_RESET}")
        gs.prompt_cntl = "game_loop"
        return
    
    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd in ['n', 's', 'e', 'w']:
        move_player(player_character, my_tower, cmd)

def process_tomb_action(player_character, my_tower, cmd):
    """
    Handle tomb room interactions - REVAMPED!
    
    Each tomb is surrounded by undead monsters in adjacent non-wall rooms (handled in setup_dungeons_and_tombs).
    Upon entering the tomb, player chooses to SEARCH or PAY RESPECTS.
    
    SEARCH outcomes (equal chance each):
    1. Guardian appears - defeat for major cursed weapon/armor reward
    2. Small treasure found (gold + minor item)
    3. Small treasure + spirits released (floor haunted for 3d6 turns!)
    
    PAY RESPECTS:
    - Healing or minor buff (random)
    
    After interaction, tomb becomes inert.
    
    Cursed weapons/armor from guardians: powerful for their level but CANNOT be upgraded.
    """
    
    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    coords = (player_character.x, player_character.y, player_character.z)
    
    if cmd == "init":
        if coords in gs.looted_tombs:
            add_log(f"{COLOR_GREY}This tomb lies empty and silent. Nothing remains.{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"
        else:
            # Check if this is a Cursed Tomb (special quest tomb for Rune of Eternity)
            is_cursed = room.properties.get('is_cursed', False)
            
            if is_cursed:
                add_log("")
                add_log(f"{COLOR_RED}==============================={COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}    CURSED TOMB{COLOR_RESET}")
                add_log(f"{COLOR_RED}==============================={COLOR_RESET}")
                add_log("")
                add_log(f"{COLOR_RED}Dark energy radiates from within!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}The dead do not rest here...{COLOR_RESET}")
                add_log("")
                add_log(f"{COLOR_YELLOW}Press any key to enter...{COLOR_RESET}")
            else:
                add_log("")
                add_log(f"{COLOR_GREY}==============================={COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}       Ancient Tomb{COLOR_RESET}")
                add_log(f"{COLOR_GREY}==============================={COLOR_RESET}")
                add_log("")
                add_log(f"{COLOR_CYAN}A stone sarcophagus sealed for centuries.{COLOR_RESET}")
                add_log(f"{COLOR_GREY}Dust motes dance in the stale air...{COLOR_RESET}")
                add_log("")
                add_log(f"{COLOR_YELLOW}What will you do?{COLOR_RESET}")
                add_log("")
                add_log(f"{COLOR_YELLOW}R - Raid the tomb (Risky){COLOR_RESET}")
                add_log(f"{COLOR_CYAN}P - Pay your respects (Safe){COLOR_RESET}")
                add_log("")
            
            gs.prompt_cntl = "tomb_mode"
        return
    
    elif cmd in ['r', 'p']:
        # Check if this is a Cursed Tomb (special quest tomb)
        is_cursed = room.properties.get('is_cursed', False)
        
        if is_cursed and not gs.runes_obtained['eternity']:
            # CURSED TOMB - Spawns a powerful guardian, rewards Rune of Eternity on victory
            add_log("")
            add_log(f"{COLOR_RED}You step into the Cursed Tomb...{COLOR_RESET}")
            add_log("")
            add_log(f"{COLOR_PURPLE}The air freezes. Darkness coalesces into form!{COLOR_RESET}")
            add_log(f"{COLOR_RED}A DEATH KNIGHT rises from the sarcophagus!{COLOR_RESET}")
            add_log("")
            
            # Create powerful Death Knight guardian
            floor_level = player_character.z
            guardian = Monster(
                name="CURSED DEATH KNIGHT",
                health=int(150 + floor_level * 15),
                attack=int(20 + floor_level * 2),
                defense=int(15 + floor_level),
                elemental_weakness=['Holy', 'Fire'],
                elemental_strength=['Darkness', 'Ice', 'Physical'],
                level=floor_level + 5,
                attack_element='Darkness',
                flavor_text=f"{COLOR_PURPLE}The eternal guardian of the Cursed Tomb, bound by dark magic!{COLOR_RESET}",
                victory_text=f"{COLOR_GREEN}The Death Knight crumbles, releasing its cursed power!{COLOR_RESET}"
            )
            guardian.properties['is_tomb_guardian'] = True
            guardian.properties['is_cursed_tomb_guardian'] = True
            guardian.properties['tomb_coords'] = coords
            
            # Store for combat and set pending reward
            gs.encountered_monsters[coords] = guardian
            gs.active_monster = guardian
            gs.pending_tomb_guardian_reward = {
                'coords': coords,
                'floor_level': floor_level,
                'is_cursed_tomb': True
            }
            
            gs.prompt_cntl = "combat_mode"
            process_combat_action(player_character, my_tower, "init")
            return
        
        # Normal tomb with player choice
        if coords not in gs.looted_tombs:
            add_log("")
            
            # Choice R: SEARCH the tomb (Risky - 3 possible outcomes)
            if cmd == 'r':
                add_log(f"{COLOR_YELLOW}You pry open the sarcophagus lid...{COLOR_RESET}")
                add_log("")
                
                outcome_roll = random.randint(1, 3)
                floor_level = player_character.z
                
                # OUTCOME 1: Guardian appears!
                if outcome_roll == 1:
                    add_log(f"{COLOR_RED}The tomb's guardian awakens!{COLOR_RESET}")
                    add_log(f"{COLOR_PURPLE}A spectral form rises from the remains!{COLOR_RESET}")
                    add_log("")
                    
                    # Create guardian based on floor level
                    guardian_types = [
                        ("Tomb Wraith", ['Holy', 'Fire'], ['Darkness', 'Ice']),
                        ("Skeletal Champion", ['Holy', 'Light'], ['Darkness', 'Physical']),
                        ("Mummified King", ['Fire', 'Holy'], ['Darkness', 'Earth']),
                        ("Spectral Knight", ['Holy', 'Light'], ['Darkness', 'Ice', 'Physical'])
                    ]
                    g_name, g_weak, g_strong = random.choice(guardian_types)
                    
                    guardian = Monster(
                        name=f"{g_name.upper()}",
                        health=int(80 + floor_level * 12),
                        attack=int(12 + floor_level * 1.5),
                        defense=int(8 + floor_level),
                        elemental_weakness=g_weak,
                        elemental_strength=g_strong,
                        level=floor_level + 2,
                        attack_element='Darkness',
                        flavor_text=f"{COLOR_PURPLE}Guardian of this ancient tomb, sworn to protect its treasures!{COLOR_RESET}",
                        victory_text=f"{COLOR_GREEN}The guardian's form dissipates, releasing its treasures!{COLOR_RESET}"
                    )
                    guardian.properties['is_tomb_guardian'] = True
                    guardian.properties['tomb_coords'] = coords
                    
                    # Store for combat and set pending reward
                    gs.encountered_monsters[coords] = guardian
                    gs.active_monster = guardian
                    gs.pending_tomb_guardian_reward = {
                        'coords': coords,
                        'floor_level': floor_level,
                        'is_cursed_tomb': False
                    }
                    
                    gs.prompt_cntl = "combat_mode"
                    process_combat_action(player_character, my_tower, "init")
                    return
                
                # OUTCOME 2: Small treasure found
                elif outcome_roll == 2:
                    add_log(f"{COLOR_GREEN}The tomb yields its modest treasures...{COLOR_RESET}")
                    add_log("")
                    
                    # Gold reward scaled to floor
                    gold_amount = random.randint(50 + floor_level * 10, 100 + floor_level * 15)
                    player_character.gold += gold_amount
                    add_log(f"{COLOR_YELLOW}Found: {gold_amount} gold coins{COLOR_RESET}")
                    
                    # Minor item (potion or scroll)
                    if random.random() < 0.5:
                        potion = Potion(name="Healing Potion", potion_type='healing', effect_magnitude=50, value=50, level=1, description="Restores 50 HP")
                        player_character.inventory.add_item(potion)
                        add_log(f"{COLOR_GREEN}Found: Healing Potion{COLOR_RESET}")
                    else:
                        # Rare ingredient
                        rare_ingredients = ['Shadow Leaf', 'Wisdom Moss', 'Iron Bark', 'Moon Petal']
                        ing_name = random.choice(rare_ingredients)
                        if ing_name in GARDEN_INGREDIENTS_DICT:
                            ing = Ingredient(name=ing_name, value=GARDEN_INGREDIENTS_DICT[ing_name]['value'], level=1, description=GARDEN_INGREDIENTS_DICT[ing_name]['description'])
                        else:
                            ing = Ingredient(name=ing_name, value=15, level=1, description="A rare alchemical ingredient")
                        player_character.inventory.add_item(ing)
                        add_log(f"{COLOR_PURPLE}Found: {ing_name}{COLOR_RESET}")
                    
                    # Mark tomb as looted
                    gs.looted_tombs[coords] = True
                    gs.game_stats['tombs_looted'] = gs.game_stats.get('tombs_looted', 0) + 1
                    _track_tomb_progress()
                
                # OUTCOME 3: Small treasure + SPIRITS RELEASED (floor haunted!)
                elif outcome_roll == 3:
                    add_log(f"{COLOR_YELLOW}You find some treasure, but...{COLOR_RESET}")
                    add_log("")
                    
                    # Small gold reward
                    gold_amount = random.randint(30 + floor_level * 8, 70 + floor_level * 12)
                    player_character.gold += gold_amount
                    add_log(f"{COLOR_YELLOW}Found: {gold_amount} gold coins{COLOR_RESET}")
                    
                    # Minor potion
                    potion = Potion(name="Minor Healing Potion", potion_type='healing', effect_magnitude=30, value=30, level=1, description="Restores 30 HP")
                    player_character.inventory.add_item(potion)
                    add_log(f"{COLOR_GREEN}Found: Minor Healing Potion{COLOR_RESET}")
                    
                    add_log("")
                    add_log(f"{COLOR_RED}======================================{COLOR_RESET}")
                    add_log(f"{COLOR_PURPLE}SPIRITS RELEASED!{COLOR_RESET}")
                    add_log(f"{COLOR_RED}======================================{COLOR_RESET}")
                    add_log("")
                    add_log(f"{COLOR_PURPLE}Spectral forms burst from the sarcophagus!{COLOR_RESET}")
                    add_log(f"{COLOR_RED}The spirits scatter throughout the level!{COLOR_RESET}")
                    
                    # Haunt the floor for 3d6 turns
                    haunt_duration = random.randint(1, 6) + random.randint(1, 6) + random.randint(1, 6)
                    gs.haunted_floors[player_character.z] = haunt_duration
                    
                    add_log(f"{COLOR_PURPLE}This floor is now HAUNTED for {haunt_duration} turns!{COLOR_RESET}")
                    add_log(f"{COLOR_GREY}(Spirits may ambush you as you explore...){COLOR_RESET}")
                    
                    # Mark tomb as looted
                    gs.looted_tombs[coords] = True
                    gs.game_stats['tombs_looted'] = gs.game_stats.get('tombs_looted', 0) + 1
                    _track_tomb_progress()
            
            # Choice P: PAY RESPECTS (Safe - healing or buff)
            elif cmd == 'p':
                add_log(f"{COLOR_CYAN}You kneel before the sarcophagus and bow your head...{COLOR_RESET}")
                add_log("")
                add_log(f"{COLOR_PURPLE}A gentle warmth fills the chamber.{COLOR_RESET}")
                add_log(f"{COLOR_GREEN}The spirits acknowledge your reverence.{COLOR_RESET}")
                add_log("")
                
                # Random blessing - 50% healing, 50% buff
                if random.random() < 0.5:
                    # Healing blessing
                    heal_amount = int(player_character.max_health * 0.3)  # 30% max HP heal
                    old_hp = player_character.health
                    player_character.health = min(player_character.max_health, player_character.health + heal_amount)
                    actual_heal = player_character.health - old_hp
                    add_log(f"{COLOR_GREEN}The spirits restore your vitality!{COLOR_RESET}")
                    add_log(f"{COLOR_GREEN}Healed {actual_heal} HP{COLOR_RESET}")
                else:
                    # Random minor buff
                    buffs = [
                        ('Ancestral Protection', 'defense_boost', 2, 15, 'Protected by ancestral spirits'),
                        ('Spirit Sight', 'wisdom_boost', 3, 12, 'Spirits guide your path'),
                        ('Tomb\'s Blessing', 'attack_boost', 2, 12, 'Blessed by the honored dead'),
                        ('Spectral Ward', 'resistance', 3, 10, 'Shielded from dark forces')
                    ]
                    buff_name, buff_type, magnitude, duration, desc = random.choice(buffs)
                    
                    player_character.add_status_effect(
                        effect_name=buff_name,
                        duration=duration,
                        effect_type=buff_type,
                        magnitude=magnitude,
                        description=desc
                    )
                    add_log(f"{COLOR_CYAN}{buff_name}: +{magnitude} for {duration} turns{COLOR_RESET}")
                
                # Mark tomb as used (respects paid)
                gs.looted_tombs[coords] = True
                gs.game_stats['tombs_looted'] = gs.game_stats.get('tombs_looted', 0) + 1
                _track_tomb_progress()
            
            add_log("")
        else:
            add_log(f"{COLOR_GREY}This tomb lies empty and silent.{COLOR_RESET}")
        
        gs.prompt_cntl = "game_loop"
        return
    
    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd in ['n', 's', 'e', 'w']:
        move_player(player_character, my_tower, cmd)


def _track_tomb_progress():
    """Helper to track tomb progress for Rune of Eternity quest."""
    
    if not gs.runes_obtained['eternity']:
        gs.rune_progress['tombs_looted_total'] += 1
        if gs.rune_progress['tombs_looted_total'] >= gs.rune_progress_reqs['tombs_looted_total'] and not gs.cursed_tomb_available:
            gs.cursed_tomb_available = True
            add_log(f"{COLOR_PURPLE}==============================={COLOR_RESET}")
            add_log(f"{COLOR_RED}The spirits acknowledge your boldness...{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}A CURSED TOMB has manifested somewhere in the depths!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}==============================={COLOR_RESET}")
            add_log("")


def award_tomb_guardian_reward(player_character):
    """
    Award the major reward for defeating a tomb guardian.
    Called from combat victory processing when guardian is defeated.
    Returns True if reward was given, False otherwise.
    """
    
    if gs.pending_tomb_guardian_reward is None:
        return False
    
    coords = gs.pending_tomb_guardian_reward['coords']
    floor_level = gs.pending_tomb_guardian_reward['floor_level']
    is_cursed = gs.pending_tomb_guardian_reward.get('is_cursed_tomb', False)
    
    add_log("")
    add_log(f"{COLOR_PURPLE}==============================={COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}GUARDIAN DEFEATED!{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}==============================={COLOR_RESET}")
    add_log("")
    
    if is_cursed:
        # CURSED TOMB GUARDIAN - Best rewards + Rune of Eternity
        add_log(f"{COLOR_RED}The Death Knight's cursed power flows into you!{COLOR_RESET}")
        add_log("")
        
        # Large gold reward
        gold_amount = random.randint(400, 700)
        player_character.gold += gold_amount
        add_log(f"{COLOR_YELLOW}Cursed gold: +{gold_amount}{COLOR_RESET}")
        
        # Powerful cursed weapon (cannot be upgraded but strong for level)
        cursed_weapons = [
            ("Deathbringer", "A blade that drinks the souls of the fallen", ['Darkness', 'Ice']),
            ("Soul Reaver", "A cursed sword that hungers eternally", ['Darkness', 'Demonic']),
            ("Wraithblade", "Forged from the essence of tormented spirits", ['Darkness', 'Psionic'])
        ]
        w_name, w_desc, w_elem = random.choice(cursed_weapons)
        
        # Powerful stats - +4-6 above normal for floor level
        base_attack = 5 + floor_level + random.randint(4, 6)
        
        weapon = Weapon(
            name=w_name,
            attack_bonus=base_attack,
            elemental_strength=w_elem,
            level=floor_level,
            description=f"{w_desc} [SEALED - Cannot be upgraded]",
            value=400 + floor_level * 20,
            is_sealed=True,  # Cannot be upgraded!
            buc_status=roll_buc_status(floor_level, 'tomb'),
        )
        player_character.inventory.add_item(weapon)
        add_log(f"{COLOR_PURPLE}Found: {w_name} (Attack +{base_attack}) [SEALED]{COLOR_RESET}")
        add_log(f"{COLOR_GREY}(Sealed items are powerful but cannot be upgraded. BUC status unknown.){COLOR_RESET}")
        
        # Award Rune of Eternity
        rune = Rune(
            name="Rune of Eternity",
            rune_type='eternity',
            description="A dark rune pulsing with the power of undeath. Unlocks the Eternity Shard vault.",
            value=0,
            level=0
        )
        player_character.inventory.add_item(rune)
        gs.runes_obtained['eternity'] = True
        gs.cursed_tomb_available = False
        
        add_log("")
        add_log(f"{COLOR_PURPLE}==============================={COLOR_RESET}")
        add_log(f"{COLOR_YELLOW}RUNE OF ETERNITY OBTAINED!{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}==============================={COLOR_RESET}")
        add_log("")
        
    else:
        # Regular tomb guardian - good cursed weapon or armor
        add_log(f"{COLOR_GREEN}The guardian's treasures are yours!{COLOR_RESET}")
        add_log("")
        
        # Good gold reward
        gold_amount = random.randint(150 + floor_level * 15, 250 + floor_level * 20)
        player_character.gold += gold_amount
        add_log(f"{COLOR_YELLOW}Found: {gold_amount} gold{COLOR_RESET}")
        
        # 50% weapon, 50% armor - both cursed but powerful
        if random.random() < 0.5:
            # Cursed weapon
            cursed_weapons = [
                ("Gravedigger's Blade", "A blade stained by countless burials", ['Darkness']),
                ("Tomb King's Scepter", "Once wielded by a mighty ruler", ['Darkness', 'Psionic']),
                ("Bonecrusher", "Forged from the bones of fallen warriors", ['Darkness', 'Physical']),
                ("Specter's Touch", "Chilling blade that drains warmth", ['Darkness', 'Ice'])
            ]
            w_name, w_desc, w_elem = random.choice(cursed_weapons)
            
            # +2-4 above normal for floor level
            base_attack = 4 + floor_level + random.randint(2, 4)
            
            weapon = Weapon(
                name=w_name,
                attack_bonus=base_attack,
                elemental_strength=w_elem,
                level=floor_level,
                description=f"{w_desc} [SEALED - Cannot be upgraded]",
                value=200 + floor_level * 15,
                is_sealed=True,
                buc_status=roll_buc_status(floor_level, 'tomb'),
            )
            player_character.inventory.add_item(weapon)
            add_log(f"{COLOR_PURPLE}Found: {w_name} (Attack +{base_attack}) [SEALED]{COLOR_RESET}")
        else:
            # Cursed armor
            cursed_armors = [
                ("Shroud of Shadows", "Armor woven from eternal darkness", ['Darkness']),
                ("Tomb Warden's Plate", "Armor of an ancient guardian", ['Darkness', 'Physical']),
                ("Wraith's Embrace", "Spectral armor that chills the soul", ['Darkness', 'Ice']),
                ("Deathshroud", "A cloak that blurs the line between life and death", ['Darkness', 'Psionic'])
            ]
            a_name, a_desc, a_elem = random.choice(cursed_armors)
            
            # +2-4 above normal for floor level
            base_defense = 3 + floor_level + random.randint(2, 4)
            
            armor = Armor(
                name=a_name,
                defense_bonus=base_defense,
                elemental_strength=a_elem,
                level=floor_level,
                description=f"{a_desc} [SEALED - Cannot be upgraded]",
                value=200 + floor_level * 15,
                is_sealed=True,
                buc_status=roll_buc_status(floor_level, 'tomb'),
            )
            player_character.inventory.add_item(armor)
            add_log(f"{COLOR_PURPLE}Found: {a_name} (Defense +{base_defense}) [SEALED]{COLOR_RESET}")
        
        add_log(f"{COLOR_GREY}(Cursed items are powerful but cannot be upgraded){COLOR_RESET}")
    
    # Mark tomb as looted
    gs.looted_tombs[coords] = True
    gs.game_stats['tombs_looted'] = gs.game_stats.get('tombs_looted', 0) + 1
    
    # Track progress if not cursed tomb (cursed tomb already handled rune)
    if not is_cursed:
        _track_tomb_progress()
    
    # Clear pending reward
    gs.pending_tomb_guardian_reward = None
    add_log("")
    
    return True


def process_garden_action(player_character, my_tower, cmd):
    """Handle magical garden room interactions"""

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    coords = (player_character.x, player_character.y, player_character.z)

    # Check if this is a Fey Garden (ephemeral) or Bug Garden
    is_fey_garden = room.properties.get('is_fey_garden', False)
    is_bug_garden = room.properties.get('is_bug_garden', False)

    if cmd == "init":
        if coords in gs.harvested_gardens:
            add_log(f"{COLOR_GREY}This garden has been harvested. Only withered plants remain.{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"
        elif is_fey_garden:
            # FEY GARDEN: Set distinct mode and skip the logs (moved to UI)
            gs.prompt_cntl = "fey_garden_mode"
        elif is_bug_garden:
            add_log(f"{COLOR_GREEN}A tiny overgrown garden thrives in the hive's damp soil.{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}Luminous fungi and strange bug-sized plants grow here.{COLOR_RESET}")
            add_log(f"{COLOR_GREY}(Harvesting may disturb something lurking in the undergrowth...){COLOR_RESET}")
            gs.prompt_cntl = "garden_mode"
        else:
            # NORMAL GARDEN: Keep standard behavior
            add_log(f"{COLOR_GREEN}A lush magical garden blooms before you, filled with rare ingredients.{COLOR_RESET}")
            gs.prompt_cntl = "garden_mode"
        return

    elif cmd == 'h':  # Harvest
        # Check if this is the World Tree
        has_world_tree = room.properties.get('has_world_tree', False)

        if has_world_tree and not gs.runes_obtained['growth']:
            # ... (Existing World Tree logic remains unchanged) ...
            pass  # (Keep your existing World Tree code block here if modifying manually)

        # Standard Harvest Logic
        if coords in gs.harvested_gardens:
            add_log(f"{COLOR_YELLOW}This garden has already been harvested.{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"
            return

        # Determine loot table based on garden type
        if is_fey_garden:
            # Fey Garden Loot (Rare/Exotic)
            loot_table = [
                ('Moonbell Flower', 'mana_boost', 2, 25, 'Glows with soft lunar light'),
                ('Starshade Root', 'stealth_boost', 3, 40, 'Shadows cling to it'),
                ('Sunfire Petal', 'strength_boost', 1, 30, 'Warm to the touch'),
                ('Voidshroom', 'magic_resist', 2, 50, 'Absorbs light around it'),
                ('Fey Grace', 'defense_boost', 3, 15, 'Protected by fey spirits'),
                ('Time Blossom', 'speed_boost', 2, 35, 'Petals fall in slow motion')
            ]
            add_log(f"{COLOR_CYAN}You carefully harvest the otherworldly flora...{COLOR_RESET}")
        elif is_bug_garden:
            # Bug Garden Loot
            loot_table = BUG_GARDEN_INGREDIENTS
            add_log(f"{COLOR_GREEN}You carefully pluck the tiny fungi and plants...{COLOR_RESET}")
        else:
            # Normal Garden Loot
            loot_table = GARDEN_INGREDIENTS
            add_log(f"{COLOR_GREEN}You gather useful herbs and plants...{COLOR_RESET}")

        # Grant Items
        num_items = random.randint(2, 4)
        for _ in range(num_items):
            item_data = random.choice(loot_table)
            # item_data is (name, description, value, level, chance)
            ingredient = Ingredient(name=item_data[0], description=item_data[1],
                                    value=item_data[2], level=item_data[3])
            player_character.inventory.add_item(ingredient)
            add_log(f"{COLOR_GREEN}Gathered: {ingredient.name}{COLOR_RESET}")

        # Dwarf bonus: dwarves have a nose for hot peppers.
        # In normal and bug gardens, they get extra pepper rolls.
        is_dwarf = getattr(player_character, 'race', '').lower() == 'dwarf'
        if is_dwarf and not is_fey_garden:
            if random.random() < 0.40:
                fp = Ingredient(name='Fire Pepper', description='A small red pepper that hums with heat. Dwarves seem drawn to them.', value=12, level=1)
                player_character.inventory.add_item(fp)
                add_log(f"{COLOR_RED}[Dwarven Instinct] You spot a Fire Pepper tucked between the rocks!{COLOR_RESET}")
            if random.random() < 0.10:
                gp = Ingredient(name='Ghost Pepper', description='An ashen, wrinkled pepper so hot it shimmers. Deeply prized for cured meats.', value=35, level=3)
                player_character.inventory.add_item(gp)
                add_log(f"{COLOR_PURPLE}[Dwarven Instinct] A rare Ghost Pepper hides in the soil!{COLOR_RESET}")

        gs.harvested_gardens[coords] = True

        # Track fey garden floors so they don't respawn
        if is_fey_garden:
            gs.harvested_fey_floors.add(player_character.z)

        # Set garden to empty room after harvesting
        current_floor = my_tower.floors[player_character.z]
        current_room = current_floor.grid[player_character.y][player_character.x]
        current_room.room_type = '.'

        # Bug garden harvest: 40% chance to disturb a lurking bug
        if is_bug_garden and random.random() < 0.40:
            bug_pool = [m for m in BUG_MONSTER_TEMPLATES if m['name'] != 'BUG QUEEN']
            m_data = random.choice(bug_pool)
            add_log("")
            add_log(f"{COLOR_RED}Something was hiding in the undergrowth!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}A {m_data['name']} lunges at you!{COLOR_RESET}")
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
            gs.encountered_monsters[coords] = new_monster
            gs.active_monster = new_monster
            gs.prompt_cntl = "combat_mode"
            process_combat_action(player_character, my_tower, "init")
            return

        gs.prompt_cntl = "game_loop"
        _get_trigger_room_interaction()(player_character, my_tower)

    elif cmd in ['n', 's', 'e', 'w']:
        moved = move_player(player_character, my_tower, cmd)
        if not moved:
            # Stay in the correct mode if move failed
            gs.prompt_cntl = "fey_garden_mode" if is_fey_garden else "garden_mode"

    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")

    else:
        add_log("Invalid command. Press 'h' to harvest or move to leave.")

def generate_oracle_hints(player_character, my_tower):
    """Generate contextual hints based on quest progress, with chance-based secret reveals"""
    
    hints = []
    current_floor = player_character.z
    
    # Count runes and shards
    runes_count = sum(gs.runes_obtained.values())
    shards_count = sum(gs.shards_obtained.values())
    
    # =========================================================================
    # VAULT LOCATION HINTS (30% chance per hint)
    # =========================================================================
    
    # Check for vaults on current and nearby floors
    for floor_idx in range(max(0, current_floor - 2), min(len(my_tower.floors), current_floor + 3)):
        floor = my_tower.floors[floor_idx]
        floor_num = floor_idx + 1
        
        # Check for vault warps
        for r in range(floor.rows):
            for c in range(floor.cols):
                room = floor.grid[r][c]
                if room.properties.get('vault_warp') and random.random() < 0.30:
                    if room.discovered:
                        hints.append(f"A vault warp pulses with energy at ({c}, {r}) on floor {floor_num}. Step through to face the guardian within.")
                    else:
                        hints.append(f"Hidden on floor {floor_num}, a warp leads to a secret vault. Explore carefully to find it.")
                    break
        
        # Check for shard vaults
        for r in range(floor.rows):
            for c in range(floor.cols):
                room = floor.grid[r][c]
                if room.properties.get('is_shard_vault') and random.random() < 0.25:
                    shard_type = room.properties.get('shard_type', 'unknown')
                    if room.discovered:
                        hints.append(f"A Shard Vault of {shard_type.title()} awaits at ({c}, {r}) on floor {floor_num}. A legendary guardian protects it.")
                    else:
                        hints.append(f"The Shard of {shard_type.title()} lies hidden in a vault somewhere on floor {floor_num}...")
                    break
    
    # =========================================================================
    # RUNE PROGRESS HINTS
    # =========================================================================
    
    # Battle rune (champion monster)
    if not gs.runes_obtained['battle']:
        kills = gs.rune_progress['monsters_killed_total']
        if kills < gs.rune_progress_reqs['monsters_killed_total']:
            remaining = gs.rune_progress_reqs['monsters_killed_total'] - kills
            hints.append(f"You have slain {kills} foes. {remaining} more victories will summon a Champion bearing the Rune of Battle.")
        elif gs.champion_monster_available:
            hints.append(f"A Champion Monster prowls nearby, bearing the Rune of Battle. Seek it in a monster room.")
    
    # Treasure rune (legendary chest)
    if not gs.runes_obtained['treasure']:
        chests = gs.rune_progress['chests_opened_total']
        if chests < gs.rune_progress_reqs['chests_opened_total']:
            remaining = gs.rune_progress_reqs['chests_opened_total'] - chests
            hints.append(f"You have opened {chests} chests. {remaining} more treasures must be claimed before a Legendary Chest appears.")
        elif gs.legendary_chest_available:
            hints.append(f"A Legendary Chest awaits discovery in a treasure room, containing the Rune of Treasure.")
    
    # Devotion rune (altar sacrifice)
    if not gs.runes_obtained['devotion']:
        if player_character.gold >= gs.rune_progress_reqs['gold_obtained'] and player_character.health >= gs.rune_progress_reqs['player_health_obtained']:
            hints.append(f"Your devotion is sufficient. Offer {gs.rune_progress_reqs['gold_obtained']} gold and {gs.rune_progress_reqs['player_health_obtained']} health at a sacred altar to receive the Rune of Devotion.")
        else:
            needs = []
            if player_character.gold < gs.rune_progress_reqs['gold_obtained'] :
                needs.append(f"{gs.rune_progress_reqs['gold_obtained']  - player_character.gold} more gold")
            if player_character.health < gs.rune_progress_reqs['player_health_obtained']:
                needs.append(f"{gs.rune_progress_reqs['player_health_obtained'] - player_character.health} more health")
            hints.append(f"To prove your devotion, you need {' and '.join(needs)}. Seek altars when ready.")
    
    # Reflection rune (ancient waters)
    if not gs.runes_obtained['reflection']:
        pools = gs.rune_progress['pools_drunk_total']
        if pools < gs.rune_progress_reqs['pools_drunk_total']:
            remaining = gs.rune_progress_reqs['pools_drunk_total'] - pools
            hints.append(f"You have drunk from {pools} sacred pools. {remaining} more visions await before the Ancient Waters reveal themselves.")
        elif gs.ancient_waters_available:
            hints.append(f"Ancient Waters shimmer in a mystical pool, ready to grant the Rune of Reflection.")
    
    # Knowledge rune (codex)
    if not gs.runes_obtained['knowledge']:
        spells = gs.rune_progress['spells_learned_total']
        if spells < gs.rune_progress_reqs['spells_learned_total']:
            remaining = gs.rune_progress_reqs['spells_learned_total'] - spells
            hints.append(f"You have memorized {spells} unique spells. Learn {remaining} more different spells to unlock the Codex of Zot.")
        elif gs.codex_available:
            hints.append(f"The Codex of Zot awaits in an ancient library, ready to bestow the Rune of Knowledge.")
    
    # Secrets rune (master dungeon)
    if not gs.runes_obtained['secrets']:
        dungeons = gs.rune_progress['dungeons_unlocked_total']
        if dungeons < gs.rune_progress_reqs['dungeons_unlocked_total']:
            remaining = gs.rune_progress_reqs['dungeons_unlocked_total'] - dungeons
            hints.append(f"You have unlocked {dungeons} dungeons. {remaining} more must yield their secrets before the Master Dungeon appears.")
        elif gs.master_dungeon_available:
            hints.append(f"A Master Dungeon lies hidden, sealed with ancient locks. The Rune of Secrets awaits within.")
    
    # Eternity rune (cursed tomb)
    if not gs.runes_obtained['eternity']:
        tombs = gs.rune_progress['tombs_looted_total']
        if tombs < gs.rune_progress_reqs['tombs_looted_total']:
            remaining = gs.rune_progress_reqs['tombs_looted_total'] - tombs
            hints.append(f"You have desecrated {tombs} tombs. {remaining} more must be plundered before the Cursed Tomb reveals itself.")
        elif gs.cursed_tomb_available:
            hints.append(f"A Cursed Tomb, heavy with dark power, awaits. The Rune of Eternity lies within.")
    
    # Growth rune (world tree)
    if not gs.runes_obtained['growth']:
        gardens = gs.rune_progress['gardens_harvested_total']
        if gardens < gs.rune_progress_reqs['gardens_harvested_total']:
            remaining = gs.rune_progress_reqs['gardens_harvested_total'] - gardens
            hints.append(f"You have harvested {gardens} magical gardens. Tend {remaining} more before the World Tree sapling appears.")
        elif gs.world_tree_available:
            hints.append(f"The World Tree Sapling grows in a mystical garden, ready to grant the Rune of Growth.")
    
    # =========================================================================
    # SECRET ROOM LOCATION HINTS (20% chance)
    # =========================================================================
    
    floor = my_tower.floors[current_floor]
    
    # Hint about undiscovered special rooms on current floor
    special_rooms = {'L': 'library', 'A': 'altar', 'P': 'pool', 'T': 'tomb', 'G': 'garden', 'N': 'dungeon', 'C': 'treasure chest'}
    for r in range(floor.rows):
        for c in range(floor.cols):
            room = floor.grid[r][c]
            if room.room_type in special_rooms and not room.discovered and random.random() < 0.20:
                hints.append(f"A hidden {special_rooms[room.room_type]} lies undiscovered on this floor. The spirits whisper of treasures unseen.")
                break
    
    # =========================================================================
    # SHARD ACQUISITION HINTS (for obtained runes without shards)
    # =========================================================================
    
    for rune_type in ['battle', 'treasure', 'devotion', 'reflection', 'knowledge', 'secrets', 'eternity', 'growth']:
        if gs.runes_obtained.get(rune_type) and not gs.shards_obtained.get(rune_type):
            if random.random() < 0.35:
                hints.append(f"You possess the Rune of {rune_type.title()}, but the Shard eludes you. Seek Shard Vaults on floors 15 and deeper.")
                break
    
    # =========================================================================
    # STRATEGIC HINTS (chance-based)
    # =========================================================================
    
    # Hint about current floor dangers
    if random.random() < 0.25:
        monster_count = sum(1 for r in range(floor.rows) for c in range(floor.cols) if floor.grid[r][c].room_type == 'M')
        if monster_count > 5:
            hints.append(f"This floor crawls with {monster_count} beasts. Tread carefully, or become their prey.")
    
    # Hint about equipment upgrade potential
    if player_character.equipped_weapon and random.random() < 0.20:
        upgrade_lvl = player_character.equipped_weapon.upgrade_level
        if upgrade_lvl < 10:
            hints.append(f"Your weapon is at +{upgrade_lvl}. Seek Upgrade Scrolls to enhance its power further.")
    
    # Hint about low health
    if player_character.health < player_character.max_health * 0.3 and random.random() < 0.40:
        hints.append("Your life force wanes. Seek healing before the darkness claims you.")
    
    # Hint about floor 50
    if current_floor >= 45 and not gs.gate_to_floor_50_unlocked:
        hints.append("The Gate to Floor 50 requires all 8 Shards of Power. Gather them to face Zot's Guardian.")
    
    # =========================================================================
    # OVERALL PROGRESS
    # =========================================================================
    
    if runes_count > 0 and runes_count < 8:
        hints.append(f"You possess {runes_count} of 8 runes. {8 - runes_count} remain hidden in the depths.")
    elif runes_count == 8:
        hints.append(f"All eight runes are yours! Seek the shard vaults to claim the Shards of Power.")
    
    # SHARD HINTS
    if shards_count > 0 and shards_count < 8:
        hints.append(f"The shards pulse with power. You have claimed {shards_count} of 8. Continue your hunt.")
    elif shards_count == 8:
        hints.append(f"Eight shards of power resonate in harmony! The Gate to Floor 50 awaits on floor 49.")
    
    # FLOOR 50 HINT
    if gs.gate_to_floor_50_unlocked:
        hints.append(f"The Gate to Floor 50 is open. Descend to face Zot's Guardian and claim the Orb!")
    
    # =========================================================================
    # CRYPTIC LORE (random flavor)
    # =========================================================================
    
    cryptic_lore = [
        "The walls remember all who have fallen here...",
        "Eight runes, eight shards, one destiny.",
        "The Orb of Zot dreams of freedom. Will you be its liberator... or its jailer?",
        "Beware the deep floors. Monsters there have feasted on countless adventurers.",
        "Upgrade Scrolls grow in power as you descend. Seek the Divine Scrolls in the deepest vaults.",
        "Altars reward devotion, but the gods are fickle. Choose your prayers wisely.",
        "Pools may heal or harm. The Rhyton of Purity offers protection from their curses.",
        "Champions roam where monsters gather. Slay many to summon them.",
        "Legendary Chests appear to those who open many. Treasure begets treasure.",
        "The libraries of the deep contain spells of terrible power.",
        "Tombs hold eternal riches... and eternal guardians.",
        "Fey Gardens bloom between worlds. Harvest their gifts before they vanish.",
        "Dungeons hide their keys in nearby monsters. Defeat them to claim entry.",
    ]
    
    if random.random() < 0.30:
        hints.append(random.choice(cryptic_lore))
    
    # LORE/FLAVOR
    if runes_count == 0:
        hints.append(f"The Orb of Zot sleeps in the deepest chamber, guarded by an ancient power. Seek the eight runes to begin your quest.")
    
    if len(hints) == 0:
        hints.append("The mirror shows swirling mists... Your path is not yet clear.")
    
    # Shuffle and limit hints to avoid overwhelming the player
    random.shuffle(hints)
    return hints[:5]  # Return at most 5 hints

def process_oracle_action(player_character, my_tower, cmd):
    """Handle oracle room interactions"""
    
    if cmd == "init":
        add_log(f"{COLOR_PURPLE}A mystical mirror stands before you, its surface rippling with arcane energy.{COLOR_RESET}")
        gs.prompt_cntl = "oracle_mode"
        return
    
    elif cmd == 'g':  # Gaze into mirror
        add_log(f"{COLOR_PURPLE}You gaze into the Oracle's mirror...{COLOR_RESET}")
        add_log("")
        
        hints = generate_oracle_hints(player_character, my_tower)
        
        # Display hints
        for hint in hints[:3]:  # Show up to 3 hints at a time
            add_log(f"{COLOR_CYAN}> {hint}{COLOR_RESET}")
        
        add_log("")
        gs.prompt_cntl = "oracle_mode"
        return
    
    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd == 'l':
        # Lantern quick-use
        process_lantern_quick_use(player_character, my_tower)
    elif cmd in ['n', 's', 'e', 'w']:
        move_player(player_character, my_tower, cmd)


# --------------------------------------------------------------------------------
# BLACKSMITH ROOM (B) - floors 5-50: repair and reforge equipment
# --------------------------------------------------------------------------------

def process_blacksmith_action(player_character, my_tower, cmd):
    """
    Blacksmith room: repair weapons/armor, or REFORGE for a gamble.

    REPAIR:  Restore durability of equipped weapon or armor.
             Costs 80% of normal vendor repair price (specialist discount).

    REFORGE: Re-rolls the base attack/defense of equipped gear from the
             same item template pool. Upgrade level is preserved.
             Durability is fully restored. Costs 200 + floor*10 gold.
             One reforge per item type per visit.
    """

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    floor_level = player_character.z

    if cmd == "init":
        if room.properties.get('smith_done'):
            add_log(f"{COLOR_GREY}The forge is cold. The smith has moved on.{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"
            return
        gs.prompt_cntl = "blacksmith_mode"
        return

    weapon = player_character.equipped_weapon
    armor  = player_character.equipped_armor

    if cmd == '1':  # Repair weapon
        if not weapon:
            add_log(f"{COLOR_YELLOW}You have no weapon equipped.{COLOR_RESET}")
        elif weapon.durability >= weapon.max_durability:
            add_log(f"{COLOR_YELLOW}Your {weapon.name} is already in perfect condition.{COLOR_RESET}")
        else:
            cost = max(1, int(get_repair_cost(weapon) * 0.80))
            if player_character.gold < cost:
                add_log(f"{COLOR_RED}Not enough gold. Repair costs {cost}g.{COLOR_RESET}")
            else:
                player_character.gold -= cost
                weapon.durability = weapon.max_durability
                add_log(f"{COLOR_GREEN}The smith hammers your {weapon.name} back to full condition. (-{cost}g){COLOR_RESET}")
        gs.prompt_cntl = "blacksmith_mode"

    elif cmd == '2':  # Repair armor
        if not armor:
            add_log(f"{COLOR_YELLOW}You have no armor equipped.{COLOR_RESET}")
        elif armor.durability >= armor.max_durability:
            add_log(f"{COLOR_YELLOW}Your {armor.name} is already in perfect condition.{COLOR_RESET}")
        else:
            cost = max(1, int(get_repair_cost(armor) * 0.80))
            if player_character.gold < cost:
                add_log(f"{COLOR_RED}Not enough gold. Repair costs {cost}g.{COLOR_RESET}")
            else:
                player_character.gold -= cost
                armor.durability = armor.max_durability
                add_log(f"{COLOR_GREEN}The smith patches your {armor.name} back to full protection. (-{cost}g){COLOR_RESET}")
        gs.prompt_cntl = "blacksmith_mode"

    elif cmd == '3':  # Reforge weapon
        if not weapon:
            add_log(f"{COLOR_YELLOW}You have no weapon equipped to reforge.{COLOR_RESET}")
            gs.prompt_cntl = "blacksmith_mode"
            return
        if room.properties.get('reforged_weapon'):
            add_log(f"{COLOR_YELLOW}You have already reforged your weapon at this forge.{COLOR_RESET}")
            gs.prompt_cntl = "blacksmith_mode"
            return
        cost = 200 + floor_level * 10
        if player_character.gold < cost:
            add_log(f"{COLOR_RED}Reforging costs {cost}g. Not enough gold.{COLOR_RESET}")
            gs.prompt_cntl = "blacksmith_mode"
            return
        player_character.gold -= cost
        old_bonus = weapon._base_attack_bonus
        matching = [w for w in WEAPON_TEMPLATES if w.level == weapon.level]
        if matching:
            template = random.choice(matching)
            weapon._base_attack_bonus = template._base_attack_bonus
        else:
            spread = max(1, int(old_bonus * 0.20))
            weapon._base_attack_bonus = max(1, old_bonus + random.randint(-spread, spread))
        new_bonus = weapon._base_attack_bonus
        weapon.durability = weapon.max_durability
        room.properties['reforged_weapon'] = True
        delta = new_bonus - old_bonus
        if delta > 0:
            add_log(f"{COLOR_GREEN}The forge sings! {weapon.name} ATK {old_bonus} -> {new_bonus} (+{delta})!{COLOR_RESET}")
        elif delta < 0:
            add_log(f"{COLOR_YELLOW}The metal cools poorly. {weapon.name} ATK {old_bonus} -> {new_bonus} ({delta}).{COLOR_RESET}")
        else:
            add_log(f"{COLOR_CYAN}The blade emerges unchanged. ATK stays at {new_bonus}.{COLOR_RESET}")
        gs.prompt_cntl = "blacksmith_mode"

    elif cmd == '4':  # Reforge armor
        if not armor:
            add_log(f"{COLOR_YELLOW}You have no armor equipped to reforge.{COLOR_RESET}")
            gs.prompt_cntl = "blacksmith_mode"
            return
        if room.properties.get('reforged_armor'):
            add_log(f"{COLOR_YELLOW}You have already reforged your armor at this forge.{COLOR_RESET}")
            gs.prompt_cntl = "blacksmith_mode"
            return
        cost = 200 + floor_level * 10
        if player_character.gold < cost:
            add_log(f"{COLOR_RED}Reforging costs {cost}g. Not enough gold.{COLOR_RESET}")
            gs.prompt_cntl = "blacksmith_mode"
            return
        player_character.gold -= cost
        old_bonus = armor._base_defense_bonus
        matching = [a for a in ARMOR_TEMPLATES if a.level == armor.level]
        if matching:
            template = random.choice(matching)
            armor._base_defense_bonus = template._base_defense_bonus
        else:
            spread = max(1, int(old_bonus * 0.20))
            armor._base_defense_bonus = max(1, old_bonus + random.randint(-spread, spread))
        new_bonus = armor._base_defense_bonus
        armor.durability = armor.max_durability
        room.properties['reforged_armor'] = True
        delta = new_bonus - old_bonus
        if delta > 0:
            add_log(f"{COLOR_GREEN}The plates gleam brighter! {armor.name} DEF {old_bonus} -> {new_bonus} (+{delta})!{COLOR_RESET}")
        elif delta < 0:
            add_log(f"{COLOR_YELLOW}A flaw in the metal. {armor.name} DEF {old_bonus} -> {new_bonus} ({delta}).{COLOR_RESET}")
        else:
            add_log(f"{COLOR_CYAN}The armor emerges unchanged. DEF stays at {new_bonus}.{COLOR_RESET}")
        gs.prompt_cntl = "blacksmith_mode"

    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd in ['n', 's', 'e', 'w']:
        move_player(player_character, my_tower, cmd)


# --------------------------------------------------------------------------------
# SHRINE OF THE FALLEN (F) - floors 1-20: memorial to dead adventurers
# --------------------------------------------------------------------------------

def process_shrine_action(player_character, my_tower, cmd):
    """
    Shrine of the Fallen: a rough memorial scratched into the cavern wall.
    Only found on floors 1-20 -- the deeper dead are forgotten.

    PRAY (free):
        33% - Ghost's blessing: +5 max HP or +1 to STR/DEX/INT
        33% - Hint: reveals one adjacent undiscovered special room on map
        33% - Silence: the spirit rests undisturbed (nothing happens)

    LEAVE OFFERING (50 gold):
        Guaranteed small reward: healing potion or upgrade scroll.

    One use per shrine.
    """

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    floor_level = player_character.z

    if cmd == "init":
        if room.properties.get('shrine_used'):
            add_log(f"{COLOR_GREY}The shrine lies silent. The spirit has passed on.{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"
            return
        gs.prompt_cntl = "shrine_mode"
        return

    if cmd == 'p':  # Pray
        room.properties['shrine_used'] = True
        roll = random.random()
        if roll < 0.33:
            buff = random.choice(['hp', 'str', 'dex', 'int'])
            if buff == 'hp':
                player_character.max_health += 5
                player_character.health = min(player_character.health + 5, player_character.max_health)
                add_log(f"{COLOR_CYAN}A gentle warmth passes through you. Max HP +5!{COLOR_RESET}")
            elif buff == 'str':
                player_character.strength += 1
                add_log(f"{COLOR_GREEN}The fallen warrior's strength flows into you. STR +1!{COLOR_RESET}")
            elif buff == 'dex':
                player_character.dexterity += 1
                add_log(f"{COLOR_GREEN}The fallen scout's swiftness flows into you. DEX +1!{COLOR_RESET}")
            else:
                player_character.intelligence += 1
                add_log(f"{COLOR_CYAN}The fallen mage's wisdom flows into you. INT +1!{COLOR_RESET}")
        elif roll < 0.66:
            floor = my_tower.floors[floor_level]
            px, py = player_character.x, player_character.y
            room_names = {
                'M':'monster room','C':'treasure chest','V':'vendor','A':'altar',
                'L':'library','P':'pool','N':'locked dungeon','T':'tomb',
                'G':'garden','O':'oracle','B':'blacksmith','Q':'alchemist lab',
                'K':'war room','W':'warp portal'
            }
            hint_given = False
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
                nx, ny = px+dx, py+dy
                if 0 <= nx < floor.cols and 0 <= ny < floor.rows:
                    adj = floor.grid[ny][nx]
                    if not adj.discovered and adj.room_type not in [floor.wall_char, '.']:
                        rname = room_names.get(adj.room_type, 'special room')
                        add_log(f"{COLOR_PURPLE}A whispered voice guides you... a {rname} lies nearby.{COLOR_RESET}")
                        adj.discovered = True
                        hint_given = True
                        break
            if not hint_given:
                add_log(f"{COLOR_GREY}The spirit's voice is faint. You sense something nearby, but see nothing clearly.{COLOR_RESET}")
        else:
            add_log(f"{COLOR_GREY}You pray in silence. The spirit rests undisturbed. A faint peace settles over you.{COLOR_RESET}")
        room.room_type = '.'
        gs.prompt_cntl = "game_loop"

    elif cmd == 'o':  # Leave offering
        if player_character.gold < 50:
            add_log(f"{COLOR_RED}You need 50 gold to leave an offering.{COLOR_RESET}")
            gs.prompt_cntl = "shrine_mode"
            return
        player_character.gold -= 50
        room.properties['shrine_used'] = True
        if random.random() < 0.5:
            potion = Potion("Healing Potion", "Restores 50 HP.", value=60, level=1,
                            potion_type='healing', effect_magnitude=50)
            player_character.inventory.add_item(potion)
            add_log(f"{COLOR_GREEN}The spirit is grateful. A healing potion materializes at the shrine. (-50g){COLOR_RESET}")
        else:
            scroll = Scroll("Scroll of Upgrade", "A scroll of enhancement.", "Upgrades a weapon or armor.",
                            150, 1, 'upgrade')
            player_character.inventory.add_item(scroll)
            add_log(f"{COLOR_GREEN}The spirit is grateful. An upgrade scroll materializes at the shrine. (-50g){COLOR_RESET}")
        room.room_type = '.'
        gs.prompt_cntl = "game_loop"

    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd in ['n', 's', 'e', 'w']:
        move_player(player_character, my_tower, cmd)


# --------------------------------------------------------------------------------
# ALCHEMIST'S LAB (Q) - floors 12-40: combine potions into new ones
# --------------------------------------------------------------------------------

def _alchemist_brew(p1, p2, floor_level):
    """Determine the result of combining two potions. Called by process_alchemist_action."""
    if random.random() < 0.10:  # 10% botch
        add_log(f"{COLOR_RED}The mixture reacts violently! Something went wrong...{COLOR_RESET}")
        return random.choice([
            Potion("Foul Brew", "Smells terrible. Causes 30 poison damage.", value=1, level=1,
                   potion_type='poison', effect_magnitude=30),
            Potion("Confusion Draught", "The world spins badly.", value=1, level=1,
                   potion_type='confusion', effect_magnitude=5),
        ])
    t1 = getattr(p1, 'potion_type', '')
    t2 = getattr(p2, 'potion_type', '')
    if t1 == 'healing' and t2 == 'healing':
        mag = int((getattr(p1,'effect_magnitude',50) + getattr(p2,'effect_magnitude',50)) * 1.25)
        name = "Superior Healing Potion" if mag >= 120 else "Greater Healing Potion"
        return Potion(name, f"Restores {mag} HP.", value=mag*2,
                      level=max(p1.level, p2.level)+1, potion_type='healing', effect_magnitude=mag)
    elif t1 == 'mana' and t2 == 'mana':
        mag = int((getattr(p1,'effect_magnitude',30) + getattr(p2,'effect_magnitude',30)) * 1.25)
        return Potion("Greater Mana Potion", f"Restores {mag} MP.", value=mag*2,
                      level=max(p1.level, p2.level)+1, potion_type='mana', effect_magnitude=mag)
    else:
        mag_h = 50 + floor_level * 5
        return random.choice([
            Potion("Elixir of Vigor", "Boosts STR and restores some HP.", value=200,
                   level=max(1, floor_level//3), potion_type='strength', effect_magnitude=10),
            Potion("Arcane Infusion", "Restores MP and boosts INT briefly.", value=180,
                   level=max(1, floor_level//3), potion_type='mana', effect_magnitude=mag_h//2),
            Potion("Tincture of Iron", "Temporarily boosts defense.", value=160,
                   level=max(1, floor_level//3), potion_type='defense', effect_magnitude=10),
            Potion("Volatile Compound", f"Restores {mag_h} HP but may cause confusion.", value=220,
                   level=max(1, floor_level//3), potion_type='healing', effect_magnitude=mag_h),
        ])


def process_alchemist_action(player_character, my_tower, cmd):
    """
    Alchemist's Lab: combine two potions from inventory into one new one.
    3 uses per lab. Matching potion types give better results.
    10% chance of a botched brew (poison/confusion potion).
    """

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    floor_level = player_character.z

    if cmd == "init":
        uses_left = room.properties.get('alch_uses', 3)
        if uses_left <= 0:
            add_log(f"{COLOR_GREY}The alchemist's apparatus is exhausted. Smoke still lingers in the air.{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"
            return
        gs.prompt_cntl = "alchemist_mode"
        return

    potions = [item for item in player_character.inventory.items if isinstance(item, Potion)]

    if cmd == 'c':  # Begin combine
        if len(potions) < 2:
            add_log(f"{COLOR_YELLOW}You need at least 2 potions to combine.{COLOR_RESET}")
            gs.prompt_cntl = "alchemist_mode"
            return
        add_log(f"{COLOR_CYAN}Your potions:{COLOR_RESET}")
        for i, p in enumerate(potions, 1):
            add_log(f"  {i}. {p.name}")
        add_log(f"{COLOR_YELLOW}Enter two numbers separated by a space (e.g. '1 2') to combine.{COLOR_RESET}")
        room.properties['alch_combining'] = True
        gs.prompt_cntl = "alchemist_mode"
        return

    # Handle "X Y" two-number combine input
    if room.properties.get('alch_combining') and ' ' in str(cmd):
        room.properties['alch_combining'] = False
        parts = cmd.strip().split()
        if len(parts) == 2:
            try:
                a, b = int(parts[0]) - 1, int(parts[1]) - 1
                if a == b:
                    add_log(f"{COLOR_RED}Choose two different potions.{COLOR_RESET}")
                    gs.prompt_cntl = "alchemist_mode"
                    return
                if not (0 <= a < len(potions) and 0 <= b < len(potions)):
                    add_log(f"{COLOR_RED}Invalid selection.{COLOR_RESET}")
                    gs.prompt_cntl = "alchemist_mode"
                    return
                p1, p2 = potions[a], potions[b]
                player_character.inventory.remove_item(p1.name)
                player_character.inventory.remove_item(p2.name)
                result = _alchemist_brew(p1, p2, floor_level)
                player_character.inventory.add_item(result)
                uses_left = room.properties.get('alch_uses', 3) - 1
                room.properties['alch_uses'] = uses_left
                room.properties['alch_combining'] = False
                add_log(f"{COLOR_CYAN}The apparatus bubbles and hisses...{COLOR_RESET}")
                add_log(f"{COLOR_GREEN}Result: {result.name}! ({uses_left} use(s) remaining){COLOR_RESET}")
                if uses_left <= 0:
                    add_log(f"{COLOR_GREY}The alchemist's reagents are fully spent.{COLOR_RESET}")
                    room.room_type = '.'
                gs.prompt_cntl = "alchemist_mode"
                return
            except (ValueError, IndexError):
                pass
        add_log(f"{COLOR_RED}Enter two numbers like '1 2'.{COLOR_RESET}")
        room.properties['alch_combining'] = False
        gs.prompt_cntl = "alchemist_mode"
        return

    if cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd in ['n', 's', 'e', 'w']:
        move_player(player_character, my_tower, cmd)


# --------------------------------------------------------------------------------
# WAR ROOM (K) - floors 20-50: intel and raid mode
# --------------------------------------------------------------------------------

def process_war_room_action(player_character, my_tower, cmd):
    """
    War Room: a forgotten fortification with two functions.

    INTEL (free, once per visit):
        Reveals all special room types on the NEXT floor (or current floor
        if next hasn't generated yet), marking them discovered on the map.

    RAID MODE (100 + floor*5 gold, once per war room):
        Activates a 10-turn assault on the current floor.
        All monsters get +25% attack.
        All kills grant +50% bonus XP.
        Monsters display [RAIDING] prefix during combat.
        Stored in floor.properties so it persists across rooms.
    """

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    floor_level = player_character.z

    if cmd == "init":
        gs.prompt_cntl = "war_room_mode"
        return

    if cmd == '1':  # Intel
        if room.properties.get('intel_used'):
            add_log(f"{COLOR_GREY}The maps have already been studied. Nothing new to learn here.{COLOR_RESET}")
            gs.prompt_cntl = "war_room_mode"
            return
        room_names = {
            'M':'Monster','C':'Chest','V':'Vendor','A':'Altar','L':'Library',
            'P':'Pool','N':'Dungeon','T':'Tomb','G':'Garden','O':'Oracle',
            'B':'Blacksmith','Q':'Alchemist','K':'War Room','W':'Warp',
            'D':'Stairs Down','U':'Stairs Up','Z':'Puzzle'
        }
        next_idx = floor_level + 1
        if next_idx < len(my_tower.floors):
            next_floor = my_tower.floors[next_idx]
            add_log(f"{COLOR_CYAN}=== BATTLE MAPS: Floor {next_idx+1} ==={COLOR_RESET}")
            revealed = 0
            for r in range(next_floor.rows):
                for c in range(next_floor.cols):
                    cell = next_floor.grid[r][c]
                    if cell.room_type not in [next_floor.wall_char, '.']:
                        cell.discovered = True
                        rname = room_names.get(cell.room_type, cell.room_type)
                        add_log(f"  ({c},{r}) {rname}")
                        revealed += 1
            if revealed == 0:
                add_log(f"  No special rooms detected on floor {next_idx+1}.")
        else:
            add_log(f"{COLOR_CYAN}=== BATTLE MAPS: Current Floor ==={COLOR_RESET}")
            revealed = 0
            for r in range(current_floor.rows):
                for c in range(current_floor.cols):
                    cell = current_floor.grid[r][c]
                    if not cell.discovered and cell.room_type != current_floor.wall_char:
                        cell.discovered = True
                        revealed += 1
            add_log(f"  Revealed {revealed} undiscovered rooms on this floor.")
        room.properties['intel_used'] = True
        gs.prompt_cntl = "war_room_mode"

    elif cmd == '2':  # Raid mode
        if current_floor.properties.get('raid_mode_active'):
            turns = current_floor.properties.get('raid_turns_left', 0)
            add_log(f"{COLOR_RED}Raid mode already active! ({turns} turns remaining){COLOR_RESET}")
            gs.prompt_cntl = "war_room_mode"
            return
        if room.properties.get('raid_used'):
            add_log(f"{COLOR_GREY}This war room's battle plans are spent.{COLOR_RESET}")
            gs.prompt_cntl = "war_room_mode"
            return
        cost = 100 + floor_level * 5
        if player_character.gold < cost:
            add_log(f"{COLOR_RED}Rallying the assault costs {cost}g. Not enough gold.{COLOR_RESET}")
            gs.prompt_cntl = "war_room_mode"
            return
        player_character.gold -= cost
        current_floor.properties['raid_mode_active'] = True
        current_floor.properties['raid_turns_left'] = 10
        current_floor.properties['raid_xp_mult'] = 1.5
        current_floor.properties['raid_atk_mult'] = 1.25
        room.properties['raid_used'] = True
        add_log(f"{COLOR_RED}=============================={COLOR_RESET}")
        add_log(f"{COLOR_RED}   RAID MODE ACTIVATED! (-{cost}g)  {COLOR_RESET}")
        add_log(f"{COLOR_RED}=============================={COLOR_RESET}")
        add_log(f"{COLOR_YELLOW}All monsters on this floor are enraged!{COLOR_RESET}")
        add_log(f"{COLOR_GREEN}Kills grant +50% XP for 10 turns.{COLOR_RESET}")
        add_log(f"{COLOR_RED}Monsters deal +25% damage for 10 turns.{COLOR_RESET}")
        gs.prompt_cntl = "war_room_mode"

    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd in ['n', 's', 'e', 'w']:
        move_player(player_character, my_tower, cmd)


# --------------------------------------------------------------------------------
# TAXIDERMIST ROOM (X) - floors 10-45: trophy collections for accessory rewards
# --------------------------------------------------------------------------------

def process_taxidermist_action(player_character, my_tower, cmd):
    """
    Taxidermist room: trade in monster trophy collections for powerful accessories.

    The taxidermist maintains 7 collections. Each needs 3 specific trophies
    from monster kills. Complete a collection to receive a unique accessory.

    Trophies drop from monsters at 15-35% chance and stack in inventory.
    Completed collections are turned in here; trophies are consumed on trade.
    Each collection can only be completed once (reward given once).

    The taxidermist also buys individual trophies for gold if the player
    doesn't want to collect (press 's' to sell all trophies).
    """

    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]

    is_bug = room.properties.get('is_bug_taxidermist', False)

    if cmd == "init":
        gs.prompt_cntl = "taxidermist_mode"
        return

    # Complete a collection by number - filter by bug/regular taxidermist
    collection_status = get_collection_status(player_character)
    collection_status = [(name, data, pieces, complete) for name, data, pieces, complete in collection_status
                         if bool(data.get('is_bug')) == is_bug]
    completable = [(i, name, data) for i, (name, data, pieces, complete)
                   in enumerate(collection_status) if complete and not room.properties.get(f'completed_{name}')]

    if cmd.isdigit():
        idx = int(cmd) - 1
        if 0 <= idx < len(completable):
            _, cname, cdata = completable[idx]
            # Remove one of each required trophy from inventory
            for piece_name in cdata["pieces"]:
                for inv_item in list(player_character.inventory.items):
                    if isinstance(inv_item, Trophy) and inv_item.name == piece_name:
                        if getattr(inv_item, 'count', 1) > 1:
                            inv_item.count -= 1
                        else:
                            player_character.inventory.remove_item(inv_item.name)
                        break
            # Create and give reward accessory
            reward = _make_taxidermist_reward(cname, cdata)
            player_character.inventory.add_item(reward)
            room.properties[f'completed_{cname}'] = True
            add_log(f"{COLOR_YELLOW}{'=' * 40}{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Collection complete: {cname}!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{cdata['flavor']}{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}You received: {reward.name}!{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}{reward.description}{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}{'=' * 40}{COLOR_RESET}")
            # Auto-equip if a slot is free
            player_character.equip_accessory(reward)
            gs.prompt_cntl = "taxidermist_mode"
        else:
            add_log(f"{COLOR_RED}Invalid collection number.{COLOR_RESET}")
            gs.prompt_cntl = "taxidermist_mode"
        return

    if cmd == 's':
        # Sell all trophies
        trophies_to_sell = [item for item in list(player_character.inventory.items) if isinstance(item, Trophy)]
        if not trophies_to_sell:
            add_log(f"{COLOR_YELLOW}You have no trophies to sell.{COLOR_RESET}")
            gs.prompt_cntl = "taxidermist_mode"
            return
        total_gold = 0
        for trophy in trophies_to_sell:
            count = getattr(trophy, 'count', 1)
            gold = trophy.value * count
            total_gold += gold
            player_character.inventory.remove_item(trophy.name)
        player_character.gold += total_gold
        add_log(f"{COLOR_GREEN}Sold all trophies for {total_gold}g.{COLOR_RESET}")
        gs.prompt_cntl = "taxidermist_mode"
        return

    if cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd == 'x':
        # Exit taxidermist interaction back to normal room mode
        gs.prompt_cntl = "move"


def process_shard_vault_action(player_character, my_tower, cmd):
    """Handle Shard Vault interactions - require rune, fight legendary monster, get shard"""
    
    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    coords = (player_character.x, player_character.y, player_character.z)
    shard_type = room.properties.get('shard_vault_type')
    
    if cmd == "init":
        # Check if player has the required rune
        if not gs.runes_obtained.get(shard_type):
            add_log(f"{COLOR_RED}This vault is sealed with powerful magic!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}You need the Rune of {shard_type.capitalize()} to enter.{COLOR_RESET}")
            gs.prompt_cntl = "game_loop"
            return
        
        # Check if already obtained this shard
        if gs.shards_obtained.get(shard_type):
            add_log(f"{COLOR_GREY}This vault is empty. You've already claimed its shard.{COLOR_RESET}")
            room.room_type = '.'
            gs.prompt_cntl = "game_loop"
            return
        
        # Player has rune and hasn't gotten shard - spawn legendary monster!
        if coords not in gs.encountered_monsters:
            legendary = create_legendary_monster(shard_type, player_character.z)
            gs.encountered_monsters[coords] = legendary
            
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_RED}The vault door opens... A LEGENDARY GUARDIAN awakens!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log("")
        
        gs.active_monster = gs.encountered_monsters[coords]
        add_log(f"{COLOR_RED}{gs.active_monster.name} blocks your path!{COLOR_RESET}")
        add_log(f"{gs.active_monster.flavor_text}")
        gs.prompt_cntl = "combat"
        return
    
    # Other commands handled by normal movement
    elif cmd in ['n', 's', 'e', 'w']:
        move_player(player_character, my_tower, cmd)
    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")


def process_save_load_action(player_character, my_tower, cmd):
    """Handle save/load menu input."""

    if cmd == "init":
        add_log("")
        add_log(f"{COLOR_PURPLE}========== SAVE / LOAD GAME =========={COLOR_RESET}")
        saves = SaveSystem.list_saves()
        for save in saves:
            slot = save['slot']
            if save['empty']:
                add_log(f"  Slot {slot}: [Empty]")
            else:
                info = save['info']
                add_log(f"  Slot {slot}: {info['name']} (Lvl {info['level']}, Floor {info['floor']}, {info['gold']}g)")
        add_log("")
        add_log(f"Press 1-3 to save/load, 'x' to cancel")
        add_log(f"{COLOR_PURPLE}======================================{COLOR_RESET}")
        return

    if cmd == 'x':
        gs.prompt_cntl = "inventory"
        add_log("Save/Load cancelled.")
        handle_inventory_menu(player_character, my_tower, "init")
        return

    if cmd in ['1', '2', '3']:
        slot = int(cmd)
        if SaveSystem.save_exists(slot):
            # Load existing save
            loaded_player, loaded_tower = SaveSystem.load_game(slot)
            if loaded_player and loaded_tower:
                gs._pending_load = (loaded_player, loaded_tower)
                gs.prompt_cntl = "game_loaded_summary"
            else:
                add_log(f"{COLOR_RED}Failed to load game from slot {slot}!{COLOR_RESET}")
                gs.prompt_cntl = "inventory"
                handle_inventory_menu(player_character, my_tower, "init")
        else:
            # Save to empty slot
            if SaveSystem.save_game(player_character, my_tower, slot):
                add_log(f"{COLOR_GREEN}Game saved to slot {slot}!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_RED}Failed to save game!{COLOR_RESET}")
            gs.prompt_cntl = "inventory"
            handle_inventory_menu(player_character, my_tower, "init")
        return

    # Overwrite commands (o1, o2, o3)
    if cmd in ['o1', 'o2', 'o3']:
        slot = int(cmd[1])
        if SaveSystem.save_game(player_character, my_tower, slot):
            add_log(f"{COLOR_GREEN}Game saved to slot {slot}!{COLOR_RESET}")
        else:
            add_log(f"{COLOR_RED}Failed to save game!{COLOR_RESET}")
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
        return

def process_main_menu_action(cmd):
    """Handle main menu input (new game vs continue)."""

    if cmd == 'n' or cmd == '':
        # Start new game
        gs.prompt_cntl = "intro_story"
        return True

    if cmd in ['1', '2', '3']:
        slot = int(cmd)
        if SaveSystem.save_exists(slot):
            loaded_player, loaded_tower = SaveSystem.load_game(slot)
            if loaded_player and loaded_tower:
                gs._pending_load = (loaded_player, loaded_tower)
                gs.prompt_cntl = "load_pending"
                add_log(f"{COLOR_GREEN}Loading saved game...{COLOR_RESET}")
                return True
            else:
                add_log(f"{COLOR_RED}Failed to load save from slot {slot}!{COLOR_RESET}")
        else:
            add_log(f"{COLOR_YELLOW}No save in slot {slot}.{COLOR_RESET}")
        return True

    return False

def process_lantern_quick_use(player_character, my_tower):
    """
    Quick-use lantern from map view without opening inventory
    Returns True if lantern was used successfully, False otherwise
    """
    # Find lantern in inventory
    lantern = None
    for item in player_character.inventory.items:
        if isinstance(item, Lantern):
            lantern = item
            break

    if not lantern:
        add_log(f"{COLOR_YELLOW}You don't have a lantern!{COLOR_RESET}")
        return False

    current_floor = my_tower.floors[player_character.z]

    # Use the lantern
    if lantern.fuel_amount > 0:
        add_log(f"{COLOR_CYAN}You light your {lantern.name}...{COLOR_RESET}")

        # Circular reveal with radius based on light_radius
        # Uses line-of-sight: walls block the lantern light
        directions_to_reveal = []
        radius = lantern.upgrade_level+1  # Or use self.light_radius if you want it variable

        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                # Calculate Euclidean distance
                distance = (dr**2 + dc**2)**0.5

                # Include if within radius and not the character's position
                if distance <= radius and (dr, dc) != (0, 0):
                    directions_to_reveal.append((dr, dc))

        revealed_any = False
        revealed_count=0
        for dr, dc in directions_to_reveal:
            target_x, target_y = player_character.y + dr, player_character.x + dc

            # Check boundaries (target_x is row/y, target_y is col/x)
            if 0 <= target_x < current_floor.rows and 0 <= target_y < current_floor.cols:
                # Line-of-sight check: walk from player to target,
                # if any intermediate cell is a wall, light is blocked
                blocked = False
                pr, pc_ = player_character.y, player_character.x
                tr, tc = target_x, target_y
                # Bresenham-style ray: step through intermediate cells
                steps = max(abs(tr - pr), abs(tc - pc_))
                if steps > 1:
                    for s in range(1, steps):
                        ir = pr + round((tr - pr) * s / steps)
                        ic = pc_ + round((tc - pc_) * s / steps)
                        if current_floor.grid[ir][ic].room_type == current_floor.wall_char:
                            blocked = True
                            break

                if not blocked:
                    target_room = current_floor.grid[target_x][target_y]
                    if not target_room.discovered:
                        target_room.discovered = True
                        revealed_any = True
                        revealed_count+=1

        if not revealed_any:
            add_log(f"{COLOR_CYAN}The lantern shines brightly, but reveals no new rooms nearby.{COLOR_RESET}")
        else:
            add_log(f"{COLOR_GREEN}The lantern reveals {revealed_count} nearby room{'s' if revealed_count != 1 else ''}!{COLOR_RESET}")

        lantern.fuel_amount -= 1
        add_log(f"{COLOR_YELLOW}Lantern fuel remaining: {lantern.fuel_amount}{COLOR_RESET}")

        # Check if out of fuel
        if lantern.fuel_amount <= 0:
            # Try to auto-refuel
            lantern_fuel_item = player_character.inventory.get_item("Lantern Fuel")
            if lantern_fuel_item:
                add_log(f"{COLOR_GREEN}Auto-refueling lantern with {lantern_fuel_item.name}...{COLOR_RESET}")
                lantern.fuel_amount += 10
                player_character.inventory.remove_item(lantern_fuel_item.name)
                add_log(f"{COLOR_GREEN}Lantern refueled! Fuel remaining: {lantern.fuel_amount}{COLOR_RESET}")
            else:
                add_log(f"{COLOR_RED}Your lantern is out of fuel! Find Lantern Fuel to refill it.{COLOR_RESET}")

        return True
    else:
        # Lantern out of fuel
        lantern_fuel_item = player_character.inventory.get_item("Lantern Fuel")
        if lantern_fuel_item:
            add_log(f"{COLOR_GREEN}Your lantern is empty. Using {lantern_fuel_item.name} to refuel...{COLOR_RESET}")
            lantern.fuel_amount += 10
            player_character.inventory.remove_item(lantern_fuel_item.name)
            add_log(f"{COLOR_GREEN}Lantern refueled! Fuel remaining: {lantern.fuel_amount}{COLOR_RESET}")
            return False  # Don't use it this turn, just refueled
        else:
            add_log(f"{COLOR_RED}Your lantern is out of fuel and you have no Lantern Fuel to refill it.{COLOR_RESET}")
            return False


def process_towel_action(player_character, my_tower, cmd):
    """Handle towel usage options."""
    
    if gs.active_towel_item is None:
        add_log(f"{COLOR_RED}Error: No towel selected.{COLOR_RESET}")
        gs.prompt_cntl = "game_loop"
        return
    
    towel = gs.active_towel_item
    
    # Check if towel has required methods (might be a generic Item)
    has_towel_methods = hasattr(towel, 'wear') and hasattr(towel, 'wipe_face')
    
    if cmd == '1':
        # Wear towel over face (blind self)
        if has_towel_methods:
            towel.wear(player_character)
        else:
            # Fallback for generic Item
            towel.is_worn = True
            player_character.add_status_effect(
                effect_name='Towel Blindfold',
                duration=-1,
                stat_changes={'accuracy': -100},
                description='You have a towel over your face'
            )
            add_log(f"{COLOR_PURPLE}You wrap the towel around your face.{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}You are now BLIND! (But protected from gaze attacks){COLOR_RESET}")
        gs.prompt_cntl = "game_loop"
    elif cmd == '2':
        # Wipe face
        if has_towel_methods:
            towel.wipe_face(player_character)
        else:
            # Fallback for generic Item
            if 'Blinded' in player_character.status_effects:
                player_character.remove_status_effect('Blinded')
                add_log(f"{COLOR_GREEN}You wipe your face clean. You can see again!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREY}You wipe your face. Nothing happens.{COLOR_RESET}")
        gs.prompt_cntl = "game_loop"
    elif cmd == '3':
        # Wipe hands
        if has_towel_methods:
            towel.wipe_hands(player_character)
        else:
            # Fallback for generic Item
            if 'Slippery Hands' in player_character.status_effects:
                player_character.remove_status_effect('Slippery Hands')
                add_log(f"{COLOR_GREEN}You dry your hands. Your grip is firm again!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREY}You wipe your hands. Nothing happens.{COLOR_RESET}")
        gs.prompt_cntl = "game_loop"
    elif cmd == '4' or cmd == 'c':
        # Cancel
        add_log(f"{COLOR_GREY}You put the towel away.{COLOR_RESET}")
        gs.prompt_cntl = "game_loop"
    elif cmd == 'i':
        gs.prompt_cntl = "inventory"
        handle_inventory_menu(player_character, my_tower, "init")
    elif cmd in ['n', 's', 'e', 'w']:
        move_player(player_character, my_tower, cmd)
    else:
        add_log(f"{COLOR_YELLOW}Please choose 1-4.{COLOR_RESET}")
    
    # Clear the active towel after action (unless going to inventory)
    if gs.prompt_cntl != "inventory":
        gs.active_towel_item = None


# =============================================================================
# ZOTLE PUZZLE ROOM - Process Functions
# =============================================================================

def process_puzzle_action(player_character, my_tower, cmd):
    """Handle puzzle room interactions (Zotle - Zot's word puzzle)."""
    
    current_floor = my_tower.floors[player_character.z]
    room = current_floor.grid[player_character.y][player_character.x]
    
    if cmd == "init":
        # Check if puzzle already solved
        if gs.zotle_puzzle is None or gs.zotle_puzzle['solved']:
            add_log(f"{COLOR_GREY}The puzzle chamber is empty. Zot's projection has departed.{COLOR_RESET}")
            room.room_type = '.'
            gs.prompt_cntl = "game_loop"
            return
        
        # Check if failed on this floor
        if player_character.z in gs.zotle_puzzle['failed_floors']:
            add_log(f"{COLOR_GREY}The puzzle room has faded from this level...{COLOR_RESET}")
            room.room_type = '.'  # Convert to empty room
            gs.prompt_cntl = "game_loop"
            return
        
        # Reset current guess when entering
        gs.zotle_puzzle['current_guess'] = ['', '', '', '', '']
        
        gs.prompt_cntl = "puzzle_mode"
        return
    
    # Handle commands
    if cmd.lower() == 'x':
        gs.prompt_cntl = "game_loop"
        return
    
    if cmd.lower() == 'q':
        gs.game_should_quit = True
        return
    
    # Handle backspace/delete - remove last letter from current guess
    if cmd.lower() in ['backspace', 'back', 'del', 'delete']:
        for i in range(4, -1, -1):
            if gs.zotle_puzzle['current_guess'][i]:
                gs.zotle_puzzle['current_guess'][i] = ''
                break
        return
    
    # Handle Enter/Submit (empty string from Send button)
    if cmd == '':
        # Get current guess as string
        guess = ''.join(gs.zotle_puzzle['current_guess']).upper()
        
        # Only accept exactly 5 letters
        if len(guess) != 5:
            # Not enough letters - do nothing, wait for more input
            return
        
        # Check the guess against the SCRAMBLED word
        results = check_zotle_guess(guess, gs.zotle_puzzle['scrambled_word'])
        gs.zotle_puzzle['guesses'].append((guess, results))
        
        # Update keyboard_used with letter statuses (keep best status)
        if 'keyboard_used' not in gs.zotle_puzzle:
            gs.zotle_puzzle['keyboard_used'] = {}
        
        for letter, status in results:
            if letter not in gs.zotle_puzzle['keyboard_used']:
                gs.zotle_puzzle['keyboard_used'][letter] = status
            else:
                # Keep the best status (correct > present > absent)
                current = gs.zotle_puzzle['keyboard_used'][letter]
                if status == 'correct':
                    gs.zotle_puzzle['keyboard_used'][letter] = 'correct'
                elif status == 'present' and current != 'correct':
                    gs.zotle_puzzle['keyboard_used'][letter] = 'present'
        
        # Reset current guess for next attempt
        gs.zotle_puzzle['current_guess'] = ['', '', '', '', '']
        
        # Check if correct (compare against scrambled word!)
        if guess == gs.zotle_puzzle['scrambled_word']:
            # VICTORY!
            handle_puzzle_victory(player_character, my_tower, room)
            return
        else:
            # Wrong guess - room disappears from THIS floor only
            gs.zotle_puzzle['failed_floors'].add(player_character.z)
            room.room_type = '.'
            room.properties.pop('is_puzzle_room', None)
            gs.prompt_cntl = "game_loop"

            # --- START ZOT INSULTS ---
            insults = [
                "Your intellect is as dull as a goblin's blade!",
                "Is that the best your mortal mind can conjure?",
                "I've seen slimes with a better vocabulary!",
                "Ha! A swing and a miss.",
                "Pathetic. Simply pathetic.",
                "Are you even trying, or just mashing runestones?",
                "My grand-wizard grandmother spells better than that!",
                "Incorrect! What a cringy guess.",
                "Maybe stick to fighting rats? Thinking isn't your strong suit.",
                "You call yourself an adventurer? I call you illiterate!",
                "Wrong! I demand a challenger with actual brain cells!",
            ]

            add_log("")
            add_log(f"{COLOR_PURPLE}Zot's Phantom cackles maniacally...{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}\"{random.choice(insults)}\"{COLOR_RESET}")
            add_log(f"{COLOR_RED}The puzzle room fades away in disappointment...{COLOR_RESET}")
            # --- END ZOT INSULTS ---

        return
    
    # Handle single letter input (typed or from keyboard buttons)
    if len(cmd) == 1 and cmd.isalpha():
        letter = cmd.upper()
        # Find first empty slot (only if we have less than 5 letters)
        current_count = sum(1 for c in gs.zotle_puzzle['current_guess'] if c)
        if current_count < 5:
            for i in range(5):
                if not gs.zotle_puzzle['current_guess'][i]:
                    gs.zotle_puzzle['current_guess'][i] = letter
                    break
        return
    
    # Handle full word input (fallback for typed words - only accept exactly 5 letters)
    if len(cmd) >= 2 and cmd.isalpha():
        if len(cmd) == 5:
            guess = cmd.upper()
            gs.zotle_puzzle['current_guess'] = list(guess)
        # If not exactly 5 letters, ignore
        return


def handle_puzzle_victory(player_character, my_tower, room):
    """Handle when the player solves the Zotle puzzle."""
    
    original_word = gs.zotle_puzzle['original_word']
    
    add_log("")
    add_log(f"{COLOR_GREEN}======================================={COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}        PUZZLE SOLVED!{COLOR_RESET}")
    add_log(f"{COLOR_GREEN}======================================={COLOR_RESET}")
    add_log("")
    add_log(f"{COLOR_CYAN}Zot's phantom claps slowly...{COLOR_RESET}")
    add_log(f'{COLOR_PURPLE}"Well done, you magnificent {original_word}!"{COLOR_RESET}')
    add_log(f'{COLOR_PURPLE}"I suppose even a {original_word.lower()} can get lucky sometimes!"{COLOR_RESET}')
    add_log("")
    add_log(f"{COLOR_YELLOW}Zot's phantom hands you a glowing key...{COLOR_RESET}")
    add_log("")
    
    # Create and give the teleporter item
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
    
    add_log(f"{COLOR_GREEN}You received: Zot's Dimensional Key!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Use it to teleport anywhere in the dungeon!{COLOR_RESET}")
    add_log("")
    add_log(f"{COLOR_PURPLE}Zot's phantom fades away with a mocking bow...{COLOR_RESET}")
    
    # Mark puzzle as solved
    gs.zotle_puzzle['solved'] = True
    
    # Remove the puzzle room
    room.room_type = '.'
    room.properties.pop('is_puzzle_room', None)
    
    gs.prompt_cntl = "game_loop"


def use_zotle_teleporter(character, my_tower):
    """
    Use the Zotle Teleporter - set up for coordinate input.
    """
    
    add_log(f"{COLOR_PURPLE}======================================={COLOR_RESET}")
    add_log(f"{COLOR_CYAN}   ZOT'S DIMENSIONAL KEY{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}======================================={COLOR_RESET}")
    add_log("")
    add_log(f"{COLOR_YELLOW}The key hums with reality-bending power!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Enter coordinates to teleport (x,y,z):{COLOR_RESET}")
    add_log(f"{COLOR_GREY}Format: x,y,z (e.g., 5,3,2){COLOR_RESET}")
    add_log(f"{COLOR_GREY}Current location: ({character.x}, {character.y}, Floor {character.z + 1}){COLOR_RESET}")
    add_log(f"{COLOR_GREY}Available floors: 1-{len(my_tower.floors)}{COLOR_RESET}")
    add_log("")
    
    gs.active_zotle_teleporter = True
    gs.prompt_cntl = "zotle_teleporter_mode"
    return False  # Not consumed


def process_zotle_teleporter_action(player_character, my_tower, cmd):
    """Handle teleporter coordinate input."""

    if cmd.lower() == 'x' or cmd.lower() == 'c':
        add_log(f"{COLOR_YELLOW}Teleportation cancelled.{COLOR_RESET}")
        gs.active_zotle_teleporter = False
        gs.prompt_cntl = "game_loop"
        return

    # Parse coordinates
    try:
        parts = cmd.replace(' ', '').split(',')
        if len(parts) != 3:
            add_log(f"{COLOR_RED}Invalid format! Use: x,y,z (e.g., 5,3,2){COLOR_RESET}")
            return

        target_x = int(parts[0])
        target_y = int(parts[1])
        target_z = int(parts[2]) - 1  # Convert to 0-indexed

        # Validate floor exists or generate it
        if target_z < 0:
            add_log(f"{COLOR_RED}Floor must be 1 or higher!{COLOR_RESET}")
            return

        # Generate floors if needed (for floors not yet visited)
        while len(my_tower.floors) <= target_z:
            my_tower.add_floor(gs.specified_chars, gs.required_chars, gs.grid_rows, gs.grid_cols, gs.wall_char, gs.floor_char,
                              p_limits=gs.p_limits_val, c_limits=gs.c_limits_val, w_limits=gs.w_limits_val,
                              a_limits=gs.a_limits_val, l_limits=gs.l_limits_val, dungeon_limits=gs.dungeon_limits_val,
                              t_limits=gs.t_limits_val, garden_limits=gs.garden_limits_val, o_limits=gs.o_limits_val,
                              b_limits=gs.b_limits_val, f_limits=gs.f_limits_val, q_limits=gs.q_limits_val, k_limits=gs.k_limits_val, x_limits=gs.x_limits_val)

        target_floor = my_tower.floors[target_z]

        # Validate coordinates are in bounds
        if target_x < 0 or target_x >= target_floor.cols or target_y < 0 or target_y >= target_floor.rows:
            add_log(f"{COLOR_RED}Coordinates out of bounds!{COLOR_RESET}")
            add_log(f"{COLOR_GREY}Floor {target_z + 1} size: {target_floor.cols}x{target_floor.rows}{COLOR_RESET}")
            return

        # Check if target is a wall
        target_room = target_floor.grid[target_y][target_x]
        if target_room.room_type == '#':
            add_log(f"{COLOR_RED}ERROR: Cannot teleport into solid rock!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}The key sparks and fizzles...{COLOR_RESET}")

            # Find nearest non-wall room using BFS
            from collections import deque
            visited = set()
            queue = deque([(target_x, target_y, 0)])  # x, y, distance
            visited.add((target_x, target_y))
            nearest_valid = None

            while queue and not nearest_valid:
                cx, cy, dist = queue.popleft()
                # Check all 4 directions
                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) not in visited and 0 <= nx < target_floor.cols and 0 <= ny < target_floor.rows:
                        visited.add((nx, ny))
                        if target_floor.grid[ny][nx].room_type != '#':
                            nearest_valid = (nx, ny, dist + 1)
                            break
                        queue.append((nx, ny, dist + 1))

            if nearest_valid:
                nx, ny, dist = nearest_valid
                add_log(f"{COLOR_CYAN}Nearest valid location: {nx},{ny},{target_z + 1}{COLOR_RESET}")
            return

        # Teleport successful!
        add_log(f"{COLOR_PURPLE}======================================={COLOR_RESET}")
        add_log(f"{COLOR_CYAN}Reality bends around you...{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}======================================={COLOR_RESET}")

        player_character.x = target_x
        player_character.y = target_y
        player_character.z = target_z

        # Discover the target room and adjacent walls
        target_room.discovered = True
        _get_reveal_adjacent_walls()(player_character, my_tower)

        add_log(f"{COLOR_GREEN}Teleported to ({target_x}, {target_y}) on Floor {target_z + 1}!{COLOR_RESET}")

        # Update floor reached stats
        if target_z + 1 > gs.game_stats.get('max_floor_reached', 0):
            gs.game_stats['max_floor_reached'] = target_z + 1

        gs.active_zotle_teleporter = False
        gs.prompt_cntl = "game_loop"

        # Trigger room interaction
        _get_trigger_room_interaction()(player_character, my_tower)

    except ValueError:
        add_log(f"{COLOR_RED}Invalid coordinates! Use numbers only: x,y,z{COLOR_RESET}")
