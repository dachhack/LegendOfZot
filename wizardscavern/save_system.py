"""
save_system.py - Save/Load system for Wizard's Cavern

Contains the SaveSystem class and get_classes_dict() helper for
serializing and deserializing game state to/from JSON save files.

Usage:
    from .save_system import SaveSystem, get_classes_dict
"""

import json
import os
from datetime import datetime

from . import game_state as gs
from .game_state import (
    add_log,
    COLOR_RED,
    COLOR_GREEN,
    COLOR_RESET,
    COLOR_YELLOW,
    COLOR_CYAN,
    COLOR_PURPLE,
)

# These imports are needed for serialization/deserialization of game objects.
# They are imported at module level since the save system must know about
# all concrete classes to serialize/deserialize them.
from .items import (
    Item, Potion, Weapon, Armor, Scroll, Spell, Treasure,
    Towel, Flare, Lantern, LanternFuel, Food, Meat,
    CookingKit, Ingredient, Trophy, Rune, Shard,
)
from .characters import Character, Monster, Inventory, StatusEffect
from .vendor import Vendor
from .dungeon import Room, Floor, Tower


# ---------------------------------------------------------------------------
# Constants that the save system needs from the main game.
# These are imported lazily to avoid circular imports with the main file.
# ---------------------------------------------------------------------------

def _get_spell_templates():
    """Import SPELL_TEMPLATES from item_templates."""
    from .item_templates import SPELL_TEMPLATES
    return SPELL_TEMPLATES


def _get_hunger_max():
    """Import HUNGER_MAX from item_templates."""
    from .item_templates import HUNGER_MAX
    return HUNGER_MAX


def _get_meat_rot_turns_raw():
    """Import MEAT_ROT_TURNS_RAW from item_templates."""
    from .item_templates import MEAT_ROT_TURNS_RAW
    return MEAT_ROT_TURNS_RAW


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_classes_dict():
    """Returns a dict of all game classes needed for save/load."""
    classes = {
        'Character': Character,
        'Inventory': Inventory,
        'StatusEffect': StatusEffect,
        'Room': Room,
        'Floor': Floor,
        'Tower': Tower,
        'Vendor': Vendor,
        'Monster': Monster,
        'Item': Item,
        'Weapon': Weapon,
        'Armor': Armor,
        'Potion': Potion,
        'Scroll': Scroll,
        'Spell': Spell,
        'Flare': Flare,
        'Lantern': Lantern,
        'LanternFuel': LanternFuel,
        'Treasure': Treasure,
    }
    # Add optional classes if they exist
    try:
        classes['Towel'] = Towel
    except NameError:
        pass
    try:
        classes['Shard'] = Shard
    except NameError:
        pass
    try:
        classes['Rune'] = Rune
    except NameError:
        pass
    try:
        classes['CraftingIngredient'] = Ingredient
    except NameError:
        pass
    return classes


# ---------------------------------------------------------------------------
# SaveSystem
# ---------------------------------------------------------------------------

class SaveSystem:
    """Save/Load system for Wizard's Cavern"""

    @staticmethod
    def ensure_save_directory():
        if not os.path.exists(gs.SAVE_DIRECTORY):
            os.makedirs(gs.SAVE_DIRECTORY)

    @staticmethod
    def get_save_path(slot):
        return os.path.join(gs.SAVE_DIRECTORY, f"wizards_cavern_save_{slot}.json")

    @staticmethod
    def save_exists(slot):
        return os.path.exists(SaveSystem.get_save_path(slot))

    @staticmethod
    def get_save_info(slot):
        """Get basic info about a save without fully loading it."""
        path = SaveSystem.get_save_path(slot)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            player = data.get('player', {})
            return {
                'slot': slot,
                'name': player.get('name', 'Unknown'),
                'level': player.get('level', 1),
                'floor': player.get('z', 0) + 1,
                'timestamp': data.get('save_timestamp', 'Unknown'),
                'gold': player.get('gold', 0),
                'race': player.get('race', 'Unknown'),
            }
        except:
            return None

    @staticmethod
    def list_saves():
        """List all save slots with their info."""
        saves = []
        for slot in range(1, gs.MAX_SAVE_SLOTS + 1):
            info = SaveSystem.get_save_info(slot)
            saves.append({'slot': slot, 'info': info, 'empty': info is None})
        return saves

    @staticmethod
    def serialize_item(item):
        """Serialize any item to a dict."""
        if item is None:
            return None

        data = {
            'item_class': item.__class__.__name__,
            'name': item.name,
            'description': item.description,
            'value': item.value,
            'level': item.level
        }

        if isinstance(item, Weapon):
            data['attack_bonus'] = item._base_attack_bonus
            data['upgrade_level'] = item.upgrade_level
            data['elemental_strength'] = item.elemental_strength
            data['upgrade_limit'] = item.upgrade_limit
            data['is_cursed'] = getattr(item, 'is_cursed', False)
            data['durability'] = getattr(item, 'durability', item.max_durability)
            data['max_durability'] = getattr(item, 'max_durability', 100)
        elif isinstance(item, Armor):
            data['defense_bonus'] = item._base_defense_bonus
            data['upgrade_level'] = item.upgrade_level
            data['elemental_strength'] = item.elemental_strength
            data['upgrade_limit'] = item.upgrade_limit
            data['is_cursed'] = getattr(item, 'is_cursed', False)
            data['durability'] = getattr(item, 'durability', item.max_durability)
            data['max_durability'] = getattr(item, 'max_durability', 100)
        elif isinstance(item, Potion):
            data['potion_type'] = item.potion_type
            data['effect_magnitude'] = item.effect_magnitude
            data['duration'] = getattr(item, 'duration', 0)
            data['resistance_element'] = getattr(item, 'resistance_element', None)
            data['count'] = getattr(item, 'count', 1)  # Save stack count
        elif isinstance(item, Scroll):
            data['effect_description'] = item.effect_description
            data['scroll_type'] = item.scroll_type
            if hasattr(item, 'spell_to_cast') and item.spell_to_cast:
                data['spell_to_cast_name'] = item.spell_to_cast.name
            data['spell_power_multiplier'] = getattr(item, 'spell_power_multiplier', 1.5)
            data['count'] = getattr(item, 'count', 1)  # Save stack count
        elif isinstance(item, Spell):
            data['mana_cost'] = item.mana_cost
            data['damage_type'] = item.damage_type
            data['base_power'] = item.base_power
            data['spell_type'] = item.spell_type
            data['status_effect_name'] = getattr(item, 'status_effect_name', None)
            data['status_effect_duration'] = getattr(item, 'status_effect_duration', 0)
            data['status_effect_type'] = getattr(item, 'status_effect_type', None)
            data['status_effect_magnitude'] = getattr(item, 'status_effect_magnitude', 0)
        elif isinstance(item, Flare):
            data['count'] = item.count
            data['light_radius'] = item.light_radius
        elif isinstance(item, Lantern):
            data['fuel_amount'] = item.fuel_amount
            data['light_radius'] = item.light_radius
            data['upgrade_level'] = getattr(item, 'upgrade_level', 0)
        elif isinstance(item, LanternFuel):
            data['fuel_restore_amount'] = item.fuel_restore_amount
            data['count'] = getattr(item, 'count', 1)  # Save stack count
        elif isinstance(item, Treasure):
            data['gold_value'] = item.gold_value
            data['benefit'] = item.benefit
            data['treasure_type'] = getattr(item, 'treasure_type', 'passive')
            data['is_unique'] = getattr(item, 'is_unique', False)
            data['is_equipped'] = getattr(item, 'is_equipped', False)
            data['passive_effect'] = getattr(item, 'passive_effect', None)
        elif hasattr(item, 'is_wet'):  # Towel
            data['is_wet'] = getattr(item, 'is_wet', False)
            data['wet_turns'] = getattr(item, 'wet_turns', 0)
        elif hasattr(item, 'shard_type'):  # Shard
            data['shard_type'] = item.shard_type
            data['passive_bonus'] = item.passive_bonus
        elif hasattr(item, 'rune_type'):  # Rune
            data['rune_type'] = item.rune_type
            data['active_ability'] = item.active_ability
        elif hasattr(item, 'ingredient_type'):  # CraftingIngredient
            data['ingredient_type'] = item.ingredient_type
            data['rarity'] = getattr(item, 'rarity', 'common')
            data['count'] = getattr(item, 'count', 1)
        elif isinstance(item, Meat):
            data['monster_name'] = item.monster_name
            data['is_cooked'] = item.is_cooked
            data['nutrition'] = item.nutrition
            data['rot_timer'] = item.rot_timer
            data['cut'] = item.cut
            data['descriptor'] = item.descriptor
            data['is_rotten'] = item.is_rotten
            data['count'] = getattr(item, 'count', 1)
        elif isinstance(item, Food):
            data['nutrition'] = item.nutrition
            data['count'] = getattr(item, 'count', 1)
        # CookingKit has no extra fields to save

        return data

    @staticmethod
    def deserialize_item(data):
        """Deserialize an item from dict."""
        if data is None:
            return None

        cls_name = data['item_class']

        if cls_name == 'Weapon':
            item = Weapon(
                name=data['name'], description=data.get('description', ''),
                attack_bonus=data['attack_bonus'], value=data.get('value', 0),
                level=data.get('level', 0), upgrade_level=data.get('upgrade_level', 0),
                elemental_strength=data.get('elemental_strength', ['None']),
                upgrade_limit=data.get('upgrade_limit', True),
                durability=data.get('durability'),
                max_durability=data.get('max_durability')
            )
            item.is_cursed = data.get('is_cursed', False)
            return item
        elif cls_name == 'Armor':
            item = Armor(
                name=data['name'], description=data.get('description', ''),
                defense_bonus=data['defense_bonus'], value=data.get('value', 0),
                level=data.get('level', 0), upgrade_level=data.get('upgrade_level', 0),
                elemental_strength=data.get('elemental_strength', ['None']),
                upgrade_limit=data.get('upgrade_limit', True),
                durability=data.get('durability'),
                max_durability=data.get('max_durability')
            )
            item.is_cursed = data.get('is_cursed', False)
            return item
        elif cls_name == 'Potion':
            item = Potion(
                name=data['name'], description=data.get('description', ''),
                value=data.get('value', 0), level=data.get('level', 0),
                potion_type=data.get('potion_type', 'healing'),
                effect_magnitude=data.get('effect_magnitude', 30),
                duration=data.get('duration', 0),
                resistance_element=data.get('resistance_element'),
                count=data.get('count', 1)  # Restore stack count
            )
            return item
        elif cls_name == 'Scroll':
            spell_to_cast = None
            if data.get('spell_to_cast_name'):
                SPELL_TEMPLATES = _get_spell_templates()
                for spell in SPELL_TEMPLATES:
                    if spell.name == data['spell_to_cast_name']:
                        spell_to_cast = spell
                        break
            item = Scroll(
                name=data['name'], description=data.get('description', ''),
                effect_description=data.get('effect_description', ''),
                value=data.get('value', 0), level=data.get('level', 0),
                scroll_type=data.get('scroll_type', 'generic'),
                spell_to_cast=spell_to_cast,
                spell_power_multiplier=data.get('spell_power_multiplier', 1.5),
                count=data.get('count', 1)  # Restore stack count
            )
            return item
        elif cls_name == 'Spell':
            return Spell(
                name=data['name'], description=data.get('description', ''),
                mana_cost=data.get('mana_cost', 10), damage_type=data.get('damage_type', 'Physical'),
                base_power=data.get('base_power', 10), level=data.get('level', 0),
                spell_type=data.get('spell_type', 'damage'),
                status_effect_name=data.get('status_effect_name'),
                status_effect_duration=data.get('status_effect_duration', 0),
                status_effect_type=data.get('status_effect_type'),
                status_effect_magnitude=data.get('status_effect_magnitude', 0)
            )
        elif cls_name == 'Flare':
            return Flare(
                name=data['name'], description=data.get('description', ''),
                count=data.get('count', 1), light_radius=data.get('light_radius', 5),
                value=data.get('value', 1), level=data.get('level', 0)
            )
        elif cls_name == 'Lantern':
            return Lantern(
                name=data['name'], description=data.get('description', ''),
                fuel_amount=data.get('fuel_amount', 50), light_radius=data.get('light_radius', 7),
                value=data.get('value', 30), level=data.get('level', 0),
                upgrade_level=data.get('upgrade_level', 0)
            )
        elif cls_name == 'LanternFuel':
            item = LanternFuel(
                name=data['name'], description=data.get('description', ''),
                value=data.get('value', 0), level=data.get('level', 0),
                fuel_restore_amount=data.get('fuel_restore_amount', 25)
            )
            item.count = data.get('count', 1)  # Restore stack count
            return item
        elif cls_name == 'Treasure':
            item = Treasure(
                name=data['name'], description=data.get('description', ''),
                gold_value=data.get('gold_value', 0), value=data.get('value', 0),
                benefit=data.get('benefit', {}), level=data.get('level', 0),
                treasure_type=data.get('treasure_type', 'passive'),
                is_unique=data.get('is_unique', False)
            )
            item.is_equipped = data.get('is_equipped', False)
            return item
        elif cls_name == 'Towel':
            try:
                item = Towel(
                    name=data['name'], description=data.get('description', ''),
                    value=data.get('value', 5), level=data.get('level', 0)
                )
                item.is_wet = data.get('is_wet', False)
                item.wet_turns = data.get('wet_turns', 0)
                return item
            except NameError:
                return Item(data['name'], data.get('description', ''), data.get('value', 0), data.get('level', 0))
        elif cls_name == 'Shard':
            try:
                return Shard(
                    name=data['name'], shard_type=data.get('shard_type', 'battle'),
                    passive_bonus=data.get('passive_bonus', ''),
                    description=data.get('description', ''),
                    value=data.get('value', 0), level=data.get('level', 0)
                )
            except NameError:
                return Item(data['name'], data.get('description', ''), data.get('value', 0), data.get('level', 0))
        elif cls_name == 'Rune':
            try:
                return Rune(
                    name=data['name'], rune_type=data.get('rune_type', 'battle'),
                    active_ability=data.get('active_ability', ''),
                    description=data.get('description', ''),
                    value=data.get('value', 0), level=data.get('level', 0)
                )
            except NameError:
                return Item(data['name'], data.get('description', ''), data.get('value', 0), data.get('level', 0))
        elif cls_name == 'CraftingIngredient':
            try:
                item = Ingredient(
                    name=data['name'], description=data.get('description', ''),
                    ingredient_type=data.get('ingredient_type', 'herb'),
                    value=data.get('value', 0), level=data.get('level', 0)
                )
                item.rarity = data.get('rarity', 'common')
                item.count = data.get('count', 1)
                return item
            except NameError:
                return Item(data['name'], data.get('description', ''), data.get('value', 0), data.get('level', 0))
        elif cls_name == 'Food':
            item = Food(
                name=data['name'], description=data.get('description', ''),
                value=data.get('value', 5), level=data.get('level', 0),
                nutrition=data.get('nutrition', 30), count=data.get('count', 1)
            )
            return item
        elif cls_name == 'Meat':
            MEAT_ROT_TURNS_RAW = _get_meat_rot_turns_raw()
            item = Meat(
                name=data['name'], description=data.get('description', ''),
                value=data.get('value', 2), level=data.get('level', 0),
                monster_name=data.get('monster_name', 'Unknown'),
                is_cooked=data.get('is_cooked', False),
                nutrition=data.get('nutrition', 12),
                rot_timer=data.get('rot_timer', MEAT_ROT_TURNS_RAW),
                cut=data.get('cut', 'steak'),
                descriptor=data.get('descriptor', 'edible'),
                count=data.get('count', 1)
            )
            item.is_rotten = data.get('is_rotten', False)
            return item
        elif cls_name == 'CookingKit':
            return CookingKit(
                name=data['name'], description=data.get('description', ''),
                value=data.get('value', 120), level=data.get('level', 3)
            )
        else:
            # Generic item fallback
            return Item(data['name'], data.get('description', ''), data.get('value', 0), data.get('level', 0))

    @staticmethod
    def serialize_character(character):
        """Serialize player character to dict."""
        status_effects_data = {}
        for name, effect in character.status_effects.items():
            status_effects_data[name] = {
                'name': effect.name,
                'duration': effect.duration,
                'effect_type': effect.effect_type,
                'magnitude': effect.magnitude,
                'description': effect.description
            }

        HUNGER_MAX = _get_hunger_max()

        return {
            'name': character.name,
            'race': getattr(character, 'race', 'Human'),
            'gender': getattr(character, 'gender', 'Unknown'),
            'title': getattr(character, 'title', ''),
            'character_class': getattr(character, 'character_class', 'Adventurer'),
            'health': character.health,
            # Don't save max_health - it's computed from level, strength, and bonus
            'base_max_health_bonus': getattr(character, 'base_max_health_bonus', 0),
            'base_max_mana_bonus': getattr(character, 'base_max_mana_bonus', 0),
            'mana': character.mana,
            # Don't save max_mana - it's computed from intelligence, level, and bonus
            'gold': character.gold,
            'experience': character.experience,
            'level': character.level,
            'x': character.x,
            'y': character.y,
            'z': character.z,
            'base_attack': character._base_attack,
            'base_defense': character._base_defense,
            'strength': character.strength,
            'dexterity': character.dexterity,
            'intelligence': character.intelligence,
            'inventory': [SaveSystem.serialize_item(item) for item in character.inventory.items],
            'equipped_weapon': SaveSystem.serialize_item(character.equipped_weapon),
            'equipped_armor': SaveSystem.serialize_item(character.equipped_armor),
            'equipped_accessories': [SaveSystem.serialize_item(acc) for acc in character.equipped_accessories],
            'memorized_spells': [SaveSystem.serialize_item(s) for s in character.memorized_spells],
            'status_effects': status_effects_data,
            'hunger': getattr(character, 'hunger', HUNGER_MAX),
        }

    @staticmethod
    def deserialize_character(data):
        """Deserialize player character from dict."""
        HUNGER_MAX = _get_hunger_max()

        character = Character(
            name=data['name'],
            health=100,  # Temporary, will be set below
            attack=data['base_attack'],
            defense=data['base_defense'],
            strength=data['strength'],
            dexterity=data['dexterity'],
            intelligence=data['intelligence'],
            x=data['x'], y=data['y'], z=data['z']
        )

        # Set level and bonuses BEFORE setting health (since max_health depends on them)
        character.level = data['level']
        character.experience = data['experience']
        character.base_max_health_bonus = data.get('base_max_health_bonus', 0)
        character.base_max_mana_bonus = data.get('base_max_mana_bonus', 0)

        # Now set current health/mana (max_health and max_mana are now correct)
        character.health = data['health']
        character.mana = data['mana']

        character.gold = data['gold']
        character._base_attack = data['base_attack']
        character._base_defense = data['base_defense']
        character.race = data.get('race', 'Human')
        character.gender = data.get('gender', 'Unknown')
        character.title = data.get('title', '')
        character.character_class = data.get('character_class', 'Adventurer')
        character.hunger = data.get('hunger', HUNGER_MAX)

        # Inventory
        character.inventory = Inventory()
        for item_data in data.get('inventory', []):
            item = SaveSystem.deserialize_item(item_data)
            if item:
                character.inventory.items.append(item)

        # Equipped items - find matching items in inventory by name, type, and upgrade level
        # This ensures equipped items are the same objects as in inventory
        equipped_weapon_data = data.get('equipped_weapon')
        equipped_armor_data = data.get('equipped_armor')

        character.equipped_weapon = None
        character.equipped_armor = None

        if equipped_weapon_data:
            weapon_name = equipped_weapon_data.get('name')
            weapon_upgrade = equipped_weapon_data.get('upgrade_level', 0)
            for item in character.inventory.items:
                if isinstance(item, Weapon) and item.name == weapon_name:
                    # Match by upgrade level too for weapons
                    if item.upgrade_level == weapon_upgrade:
                        character.equipped_weapon = item
                        break
            # If not found in inventory (shouldn't happen), create it
            if character.equipped_weapon is None and equipped_weapon_data:
                character.equipped_weapon = SaveSystem.deserialize_item(equipped_weapon_data)

        if equipped_armor_data:
            armor_name = equipped_armor_data.get('name')
            armor_upgrade = equipped_armor_data.get('upgrade_level', 0)
            for item in character.inventory.items:
                if isinstance(item, Armor) and item.name == armor_name:
                    # Match by upgrade level too for armor
                    if item.upgrade_level == armor_upgrade:
                        character.equipped_armor = item
                        break
            # If not found in inventory (shouldn't happen), create it
            if character.equipped_armor is None and equipped_armor_data:
                character.equipped_armor = SaveSystem.deserialize_item(equipped_armor_data)

        # Equipped accessories - find matching items in inventory by name
        # Note: We don't call _apply_accessory_bonuses here because the stats
        # were saved with bonuses already applied
        character.equipped_accessories = [None, None, None, None]
        equipped_accessories_data = data.get('equipped_accessories', [None, None, None, None])
        for i, acc_data in enumerate(equipped_accessories_data):
            if acc_data and i < 4:
                acc_name = acc_data.get('name')
                for item in character.inventory.items:
                    if isinstance(item, Treasure) and item.name == acc_name:
                        character.equipped_accessories[i] = item
                        item.is_equipped = True
                        break

        # Memorized spells
        character.memorized_spells = []
        for spell_data in data.get('memorized_spells', []):
            spell = SaveSystem.deserialize_item(spell_data)
            if spell:
                character.memorized_spells.append(spell)

        # Status effects
        character.status_effects = {}
        for name, effect_data in data.get('status_effects', {}).items():
            character.status_effects[name] = StatusEffect(
                name=effect_data['name'],
                duration=effect_data['duration'],
                effect_type=effect_data['effect_type'],
                magnitude=effect_data.get('magnitude', 0),
                description=effect_data.get('description', '')
            )

        return character

    @staticmethod
    def serialize_room(room):
        return {
            'room_type': room.room_type,
            'discovered': room.discovered,
            'properties': room.properties
        }

    @staticmethod
    def serialize_floor(floor):
        grid_data = []
        for row in floor.grid:
            row_data = [SaveSystem.serialize_room(room) for room in row]
            grid_data.append(row_data)
        return {
            'rows': floor.rows,
            'cols': floor.cols,
            'wall_char': floor.wall_char,
            'floor_char': floor.floor_char,
            'grid': grid_data
        }

    @staticmethod
    def serialize_tower(tower):
        return {
            'start_coords': tower.start_coords,
            'floors': [SaveSystem.serialize_floor(floor) for floor in tower.floors]
        }

    @staticmethod
    def deserialize_tower(data):
        tower = Tower(tuple(data.get('start_coords', (0, 0))))
        for floor_data in data['floors']:
            floor = Floor(
                floor_data['rows'], floor_data['cols'],
                floor_data.get('wall_char', '#'), floor_data.get('floor_char', '.')
            )
            floor.grid = []
            for row_data in floor_data['grid']:
                row = []
                for room_data in row_data:
                    room = Room(room_data['room_type'], room_data.get('properties', {}))
                    room.discovered = room_data.get('discovered', False)
                    row.append(room)
                floor.grid.append(row)
            tower.floors.append(floor)
        return tower

    @staticmethod
    def gather_globals():
        """Gather all global game state that needs to be saved."""
        return {
            'gs.runes_obtained': gs.runes_obtained,
            'gs.shards_obtained': gs.shards_obtained,
            'gs.rune_progress': {k: (list(v) if isinstance(v, set) else v) for k, v in gs.rune_progress.items()},
            'gs.game_stats': {k: (list(v) if isinstance(v, set) else v) for k, v in gs.game_stats.items()},
            'gs.discovered_items': {k: list(v) for k, v in gs.discovered_items.items()},
            'gs.champion_monster_available': gs.champion_monster_available,
            'gs.legendary_chest_available': gs.legendary_chest_available,
            'gs.ancient_waters_available': gs.ancient_waters_available,
            'gs.codex_available': gs.codex_available,
            'gs.master_dungeon_available': gs.master_dungeon_available,
            'gs.cursed_tomb_available': gs.cursed_tomb_available,
            'gs.world_tree_available': gs.world_tree_available,
            'gs.gate_to_floor_50_unlocked': gs.gate_to_floor_50_unlocked,
            'gs.dungeon_keys': {f"{k[0]},{k[1]},{k[2]}": v for k, v in gs.dungeon_keys.items()},
            'gs.unlocked_dungeons': [f"{k[0]},{k[1]},{k[2]}" for k in gs.unlocked_dungeons],
            'gs.looted_dungeons': [f"{k[0]},{k[1]},{k[2]}" for k in gs.looted_dungeons],
            'gs.looted_tombs': [f"{k[0]},{k[1]},{k[2]}" for k in gs.looted_tombs],
            'gs.harvested_gardens': [f"{k[0]},{k[1]},{k[2]}" for k in gs.harvested_gardens],
            'gs.haunted_floors': dict(gs.haunted_floors),  # floor_num -> turns remaining
            'gs.unique_treasures_spawned': list(gs.unique_treasures_spawned),
            'gs.ephemeral_gardens': gs.ephemeral_gardens,
            'gs.bug_level_floors': {str(k): v for k, v in gs.bug_level_floors.items()},
            'gs.player_is_shrunk': gs.player_is_shrunk,
            'gs.bug_queen_defeated': gs.bug_queen_defeated,
            'unlocked_achievements': list(gs.unlocked_achievements),
            # Identification system state
            'gs.identified_items': list(gs.identified_items),
            'gs.item_cryptic_mapping': gs.item_cryptic_mapping,
            'gs.equipment_use_count': {str(k): v for k, v in gs.equipment_use_count.items()},
        }

    @staticmethod
    def restore_globals(data):
        """Restore global game state from save data."""
        if 'gs.runes_obtained' in data:
            gs.runes_obtained.update(data['gs.runes_obtained'])
        if 'gs.shards_obtained' in data:
            gs.shards_obtained.update(data['gs.shards_obtained'])
        if 'gs.rune_progress' in data:
            loaded_rp = data['gs.rune_progress']
            # Restore unique_spells_memorized as a set (saved as list)
            if 'unique_spells_memorized' in loaded_rp and isinstance(loaded_rp['unique_spells_memorized'], list):
                loaded_rp['unique_spells_memorized'] = set(loaded_rp['unique_spells_memorized'])
            elif 'unique_spells_memorized' not in loaded_rp:
                # Old save file compatibility - rebuild from count as empty set
                loaded_rp['unique_spells_memorized'] = set()
            gs.rune_progress.update(loaded_rp)
        if 'gs.game_stats' in data:
            loaded_gs = data['gs.game_stats']
            if 'unique_vendors' in loaded_gs and isinstance(loaded_gs['unique_vendors'], list):
                loaded_gs['unique_vendors'] = set(loaded_gs['unique_vendors'])
            if 'vendors_sold_to' in loaded_gs and isinstance(loaded_gs['vendors_sold_to'], list):
                loaded_gs['vendors_sold_to'] = set(loaded_gs['vendors_sold_to'])
            gs.game_stats.update(loaded_gs)
        if 'gs.discovered_items' in data:
            for k, v in data['gs.discovered_items'].items():
                gs.discovered_items[k] = set(v)

        gs.champion_monster_available = data.get('gs.champion_monster_available', False)
        gs.legendary_chest_available = data.get('gs.legendary_chest_available', False)
        gs.ancient_waters_available = data.get('gs.ancient_waters_available', False)
        gs.codex_available = data.get('gs.codex_available', False)
        gs.master_dungeon_available = data.get('gs.master_dungeon_available', False)
        gs.cursed_tomb_available = data.get('gs.cursed_tomb_available', False)
        gs.world_tree_available = data.get('gs.world_tree_available', False)
        gs.gate_to_floor_50_unlocked = data.get('gs.gate_to_floor_50_unlocked', False)

        if 'gs.dungeon_keys' in data:
            gs.dungeon_keys.clear()
            for k, v in data['gs.dungeon_keys'].items():
                gs.dungeon_keys[tuple(map(int, k.split(',')))] = v
        if 'gs.unlocked_dungeons' in data:
            gs.unlocked_dungeons.clear()
            for k in data['gs.unlocked_dungeons']:
                gs.unlocked_dungeons.add(tuple(map(int, k.split(','))))
        if 'gs.looted_dungeons' in data:
            gs.looted_dungeons.clear()
            for k in data['gs.looted_dungeons']:
                gs.looted_dungeons.add(tuple(map(int, k.split(','))))
        if 'gs.looted_tombs' in data:
            gs.looted_tombs.clear()
            for k in data['gs.looted_tombs']:
                gs.looted_tombs[tuple(map(int, k.split(',')))] = True
        if 'gs.harvested_gardens' in data:
            gs.harvested_gardens.clear()
            for k in data['gs.harvested_gardens']:
                gs.harvested_gardens[tuple(map(int, k.split(',')))] = True
        if 'gs.haunted_floors' in data:
            gs.haunted_floors.clear()
            # JSON converts int keys to strings, so convert back
            for k, v in data['gs.haunted_floors'].items():
                gs.haunted_floors[int(k)] = v
        if 'gs.unique_treasures_spawned' in data:
            gs.unique_treasures_spawned.clear()
            gs.unique_treasures_spawned.update(data['gs.unique_treasures_spawned'])
        if 'gs.ephemeral_gardens' in data:
            gs.ephemeral_gardens.clear()
            gs.ephemeral_gardens.update(data['gs.ephemeral_gardens'])
        if 'gs.bug_level_floors' in data:
            gs.bug_level_floors.clear()
            for k, v in data['gs.bug_level_floors'].items():
                gs.bug_level_floors[int(k)] = v
        if 'gs.player_is_shrunk' in data:
            gs.player_is_shrunk = data['gs.player_is_shrunk']
        if 'gs.bug_queen_defeated' in data:
            gs.bug_queen_defeated = data['gs.bug_queen_defeated']
        if 'unlocked_achievements' in data:
            gs.unlocked_achievements.clear()
            gs.unlocked_achievements.update(data['unlocked_achievements'])

        # Restore identification system state
        if 'gs.identified_items' in data:
            gs.identified_items.clear()
            gs.identified_items.update(data['gs.identified_items'])
        if 'gs.item_cryptic_mapping' in data:
            gs.item_cryptic_mapping.clear()
            gs.item_cryptic_mapping.update(data['gs.item_cryptic_mapping'])
        if 'gs.equipment_use_count' in data:
            gs.equipment_use_count.clear()
            for k, v in data['gs.equipment_use_count'].items():
                gs.equipment_use_count[int(k)] = v

    @staticmethod
    def save_game(player_character, my_tower, slot=1):
        """Save the game to a slot. Returns True if successful."""
        SaveSystem.ensure_save_directory()
        try:
            save_data = {
                'save_version': gs.SAVE_VERSION,
                'save_timestamp': datetime.now().isoformat(),
                'player': SaveSystem.serialize_character(player_character),
                'tower': SaveSystem.serialize_tower(my_tower),
                'globals': SaveSystem.gather_globals(),
            }
            path = SaveSystem.get_save_path(slot)
            with open(path, 'w') as f:
                json.dump(save_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Save failed: {e}")
            return False

    @staticmethod
    def load_game(slot):
        """Load game from slot. Returns (player_character, my_tower) or (None, None)."""
        path = SaveSystem.get_save_path(slot)
        if not os.path.exists(path):
            return None, None
        try:
            with open(path, 'r') as f:
                save_data = json.load(f)

            player_character = SaveSystem.deserialize_character(save_data['player'])
            my_tower = SaveSystem.deserialize_tower(save_data['tower'])
            SaveSystem.restore_globals(save_data.get('globals', {}))

            return player_character, my_tower
        except Exception as e:
            print(f"Load failed: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    @staticmethod
    def delete_save(slot):
        """Delete a save file."""
        path = SaveSystem.get_save_path(slot)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
