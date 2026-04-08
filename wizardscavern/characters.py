"""
characters.py - Character, Monster, Inventory, and Status Effect classes for Wizard's Cavern

Contains:
    - Inventory class (item storage and stacking)
    - get_sorted_inventory() - Sort inventory by type and level
    - format_item_for_display() - Format items for UI display
    - StatusEffect class and pre-built effect instances
    - apply_poison_to_player() - Apply poison status
    - burn_inventory_items() - Fire/explosion item destruction
    - freeze_inventory_items() - Ice item destruction
    - rot_food_items() - Spore-based food rot
    - apply_elemental_resistance() - Elemental damage reduction
    - Character class (player character)
    - Monster class (enemies)
    - VAULT_DEFENDER_TEMPLATES data

Usage:
    from .characters import Character, Monster, Inventory, StatusEffect
"""

import random
import math
from . import game_state as gs
from .game_state import (
    add_log, COLOR_RED, COLOR_GREEN, COLOR_RESET, COLOR_PURPLE,
    COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_GREY, BOLD,
    normal_int_range, get_article, print_to_output
)

from .items import (
    Item, Potion, Weapon, Armor, Scroll, Spell, Treasure, Towel,
    Flare, Lantern, LanternFuel, Food, Meat, CookingKit, Ingredient,
    Trophy, Rune, Shard, LembasWafer
)


# ============================================================================
# OPPOSED DICE ROLL HELPER
# ============================================================================
def opposed_roll(player_wins, sides=20, p_mod=0, m_mod=0):
    """Synthesize a pair of opposed dice rolls whose outcome matches player_wins.

    The *total* comparison (p_roll + p_mod) vs (m_roll + m_mod) determines
    the winner, so the displayed modifiers stay consistent with the glow.
    Uses rejection sampling over independent uniform rolls so the
    distribution looks natural.

    Returns (player_roll, monster_roll) where
        (player_roll + p_mod > monster_roll + m_mod) == player_wins

    Ties on the total are rerolled. Safety-capped at 100 tries; falls
    back to forcing extremes if exhausted.
    """
    for _ in range(100):
        p = random.randint(1, sides)
        m = random.randint(1, sides)
        p_total = p + p_mod
        m_total = m + m_mod
        if p_total == m_total:
            continue
        if (p_total > m_total) == player_wins:
            return p, m
    # Fallback: force extremes such that (p+p_mod) beats or loses to (m+m_mod)
    if player_wins:
        return sides, 1
    return 1, sides


# ============================================================================
# LAZY IMPORTS (to avoid circular dependencies during refactoring)
# ============================================================================

def _get_register_item_discovery():
    from .items import register_item_discovery
    return register_item_discovery

def _get_item_display_name(item, for_vendor=False):
    from .items import get_item_display_name
    return get_item_display_name(item, for_vendor=for_vendor)

def _is_item_identified(item):
    from .items import is_item_identified
    return is_item_identified(item)

def _identify_item(item):
    from .items import identify_item
    return identify_item(item)

def _cook_meat_in_inventory(character, source="fire"):
    from .items import cook_meat_in_inventory
    return cook_meat_in_inventory(character, source)

def _has_dodge_cloak(character):
    from .game_systems import has_dodge_cloak
    return has_dodge_cloak(character)

def _has_hunter_cloak(character):
    from .game_systems import has_hunter_cloak
    return has_hunter_cloak(character)

def _get_holy_brand_bonus(character):
    from .game_systems import get_holy_brand_bonus
    return get_holy_brand_bonus(character)

def _has_poison_immunity(character):
    from .game_systems import has_poison_immunity
    return has_poison_immunity(character)

def _has_confusion_immunity(character):
    from .game_systems import has_confusion_immunity
    return has_confusion_immunity(character)

def _has_fire_resistance(character):
    from .game_systems import has_fire_resistance
    return has_fire_resistance(character)

def _check_achievements(player_char):
    from .achievements import check_achievements
    return check_achievements(player_char)


# ============================================================================
# HUNGER CONSTANT
# ============================================================================
HUNGER_MAX = 100


# --------------------------------------------------------------------------------
# INVENTORY & ITEM MANAGEMENT
# --------------------------------------------------------------------------------

class Inventory:
    def __init__(self, items=None):
        self.items = items if items is not None else []

    def add_item(self, item_obj):
        # Register discovery
        register_item_discovery = _get_register_item_discovery()
        register_item_discovery(item_obj)

        # Stack Flares
        if isinstance(item_obj, Flare):
            for item in self.items:
                if isinstance(item, Flare) and item.name == item_obj.name:
                    item.count += item_obj.count
                    return

        # Stack Potions (same name = same type)
        if isinstance(item_obj, Potion):
            for item in self.items:
                if isinstance(item, Potion) and item.name == item_obj.name:
                    count_to_add = getattr(item_obj, 'count', 1)
                    item.count = getattr(item, 'count', 1) + count_to_add
                    display_name = _get_item_display_name(item_obj)
                    return

        # Stack Scrolls (same name and type)
        if isinstance(item_obj, Scroll):
            for item in self.items:
                if isinstance(item, Scroll) and item.name == item_obj.name and item.scroll_type == item_obj.scroll_type:
                    count_to_add = getattr(item_obj, 'count', 1)
                    item.count = getattr(item, 'count', 1) + count_to_add
                    display_name = _get_item_display_name(item_obj)
                    return

        # Stack Ingredients (same name)
        if isinstance(item_obj, Ingredient):
            for item in self.items:
                if isinstance(item, Ingredient) and item.name == item_obj.name:
                    count_to_add = getattr(item_obj, 'count', 1)
                    item.count = getattr(item, 'count', 1) + count_to_add
                    return

        # Stack Lantern Fuel (same name)
        if isinstance(item_obj, LanternFuel):
            for item in self.items:
                if isinstance(item, LanternFuel) and item.name == item_obj.name:
                    count_to_add = getattr(item_obj, 'count', 1)
                    item.count = getattr(item, 'count', 1) + count_to_add
                    return

        # Stack Food items (same name - Rations etc.)
        # Meat does NOT stack - each piece has its own rot timer
        if isinstance(item_obj, Food):
            for item in self.items:
                if isinstance(item, Food) and item.name == item_obj.name:
                    count_to_add = getattr(item_obj, 'count', 1)
                    item.count = getattr(item, 'count', 1) + count_to_add
                    return

        self.items.append(item_obj)

        # ADD THIS HELPFUL HINT
        if isinstance(item_obj, Lantern):
            add_log(f"{COLOR_CYAN} Tip: Press 'l' during exploration to quickly use your lantern!{COLOR_RESET}")

    def add_item_quiet(self, item_obj):
        self.items.append(item_obj)

    def remove_item(self, item_name):
        found = False
        for item in self.items:
            if item.name.lower() == item_name.lower():
                self.items.remove(item)
                found = True
                add_log(f"Removed {item_name} from inventory.")
                break
        if not found:
            add_log(f"{item_name} not found in inventory.")
        return found

    def get_item(self, item_name):
        for item in self.items:
            if item.name.lower() == item_name.lower():
                return item
        return None

    def check_item(self, item_name):
        for item in self.items:
            if item.name.lower() == item_name.lower():
                return True
        return False

    def display_inventory(self):
        if not self.items:
            add_log("Inventory is empty.")
        else:
            add_log("Inventory:")
            for i, item in enumerate(self.items):
                item_display = f"  {i + 1}. {item.name} (Value: {item.calculated_value} gold)"
                if isinstance(item, (Weapon, Armor)) and item.upgrade_level>0:
                    item_display += f" +{item.upgrade_level}"
                if isinstance(item, Flare):
                    item_display += f" (Count: {item.count})"
                if isinstance(item, Lantern):
                    item_display += f" (Fuel: {item.fuel_amount})"
                    if item.upgrade_level > 0:
                        item_str += f" +{item.upgrade_level}"
                add_log(item_display)

    def __repr__(self):
        return f"Inventory(items={[item.name for item in self.items]})"

def get_sorted_inventory(inventory):
    """
    Sort inventory items by type first, then by level within each type.

    Type order:
    1. Weapons
    2. Armor
    3. Potions
    4. Scrolls
    5. Spells
    6. Treasures
    7. Flares
    8. Lanterns
    9. Lantern Fuel
    10. Other Items

    Within each type, sort by level (descending), then by name
    """

    def get_item_sort_key(item):
        # Define type priority (lower number = shown first)
        type_priority = {
            'Weapon': 1,
            'Armor': 2,
            'Potion': 3,
            'Scroll': 4,
            'Spell': 5,
            'Treasure': 6,
            'Food': 7,
            'Meat': 8,
            'CookingKit': 9,
            'Flare': 10,
            'Lantern': 11,
            'LanternFuel': 12,
            'Ingredient': 13,
            'Towel': 14,
            'Item': 15
        }

        item_type = type(item).__name__
        priority = type_priority.get(item_type, 99)

        # Sort by: (type_priority, -level, name)
        # Negative level so higher levels appear first
        return (priority, -item.level, item.name)

    return sorted(inventory.items, key=get_item_sort_key)


def format_item_for_display(item, player_character=None, show_price=False, is_sell_price=False, for_vendor=False):
    """
    Format an item for display in inventory lists.

    Args:
        item: The item to format
        player_character: Player character (for checking equipped status)
        show_price: Whether to show price (for vendor interactions)
        is_sell_price: If True, show half price (sell value). If False, show full price (buy value)
        for_vendor: If True, show real names (vendors know what items are)

    Returns:
        Formatted HTML string for the item
    """
    # Price suffix (shown at end)
    price_str = ""
    if show_price:
        price = item.calculated_value
        if is_sell_price:
            price = price // 2
        price_str = f" ({price}g)"

    # Check if item is identified
    is_identified = _is_item_identified(item) or for_vendor

    if isinstance(item, Weapon):
        # Weapons always show real name - you can see it's a sword
        # Only stats/upgrades are hidden when unidentified
        display_name = item.name

        # Check if equipped - underline and yellow color
        is_equipped = player_character and player_character.equipped_weapon == item
        if is_equipped:
            item_str = f"<span style='color: #FFD700;'><b>{display_name}</b></span>"
        else:
            item_str = f"{display_name}"

        # Only show detailed stats if identified
        if is_identified:
            # Compact format: (L x, +y) for level and upgrade
            if item.upgrade_level > 0:
                item_str += f" (L{item.level}, +{item.upgrade_level})"
            else:
                item_str += f" (L{item.level})"

            # Show attack stats in orange
            current_atk = item.attack_bonus
            item_str += f" <span style='color: #FF6F00;'>{current_atk} Atk</span>"

            # Show durability
            if hasattr(item, 'durability'):
                item_str += f" {item.get_durability_status()}"
        else:
            item_str += " <span style='color: #888;'>[stats unknown]</span>"

        item_str += price_str

    elif isinstance(item, Armor):
        # Armor always shows real name - you can see it's chainmail
        # Only stats/upgrades are hidden when unidentified
        display_name = item.name

        # Check if equipped - underline and yellow color
        is_equipped = player_character and player_character.equipped_armor == item
        if is_equipped:
            item_str = f"<span style='color: #FFD700;'><b>{display_name}</b></span>"
        else:
            item_str = f"{display_name}"

        # Only show detailed stats if identified
        if is_identified:
            # Compact format: (L x, +y) for level and upgrade
            if item.upgrade_level > 0:
                item_str += f" (L{item.level}, +{item.upgrade_level})"
            else:
                item_str += f" (L{item.level})"

            # Show defense stats in green
            current_def = item.defense_bonus
            item_str += f" <span style='color: #4CAF50;'>{current_def} Def</span>"

            # Show durability
            if hasattr(item, 'durability'):
                item_str += f" {item.get_durability_status()}"
        else:
            item_str += " <span style='color: #888;'>[stats unknown]</span>"

        item_str += price_str

    elif isinstance(item, Treasure):
        # Check if this is an equipped accessory - underline and yellow color
        is_equipped = False
        if player_character and hasattr(player_character, 'equipped_accessories'):
            is_equipped = item in player_character.equipped_accessories

        if is_equipped:
            item_str = f"<span style='color: #FFD700;'><b>{item.name}</b></span>"
        else:
            item_str = f"{item.name}"

        # Show passive effect in bright purple for equippable accessories
        if item.treasure_type == 'passive' and item.passive_effect:
            item_str += f" <span style='color: #E040FB;'>{item.passive_effect}</span>"

        item_str += price_str

    elif isinstance(item, Potion):
        # Get display name (cryptic if unidentified)
        display_name = _get_item_display_name(item, for_vendor=for_vendor) if not is_identified else item.name

        item_str = f"{display_name}"
        count = getattr(item, 'count', 1)
        if count > 1:
            item_str += f" (x{count})"
        if not is_identified:
            item_str += " <span style='color: #888;'>[?]</span>"
        item_str += price_str

    elif isinstance(item, Scroll):
        # Get display name (cryptic if unidentified)
        display_name = _get_item_display_name(item, for_vendor=for_vendor) if not is_identified else item.name

        item_str = f"{display_name}"
        count = getattr(item, 'count', 1)
        if count > 1:
            item_str += f" (x{count})"
        if not is_identified:
            item_str += " <span style='color: #888;'>[?]</span>"
        item_str += price_str

    elif isinstance(item, Flare):
        item_str = f"{item.name}"
        item_str += f" (x{item.count})"
        item_str += price_str

    elif isinstance(item, Ingredient):
        item_str = f"<span style='color: #4CAF50;'>{item.name}</span>"
        count = getattr(item, 'count', 1)
        if count > 1:
            item_str += f" (x{count})"
        item_str += price_str

    elif isinstance(item, LanternFuel):
        item_str = f"{item.name}"
        count = getattr(item, 'count', 1)
        if count > 1:
            item_str += f" (x{count})"
        item_str += price_str

    elif isinstance(item, Lantern):
        item_str = f"{item.name}"
        item_str += f" (Fuel: {item.fuel_amount})"
        if item.upgrade_level > 0:
            item_str += f" +{item.upgrade_level}"
        item_str += price_str

    elif isinstance(item, Meat):
        state = "Cooked" if item.is_cooked else "Raw"
        if item.is_rotten:
            item_str = f"<span style='color:#888;'>{item.name} [ROTTEN]</span>"
        elif item.is_cooked:
            item_str = f"<span style='color:#FFA040;'>{item.name}</span> (+{item.nutrition} hunger)"
        else:
            item_str = f"<span style='color:#CC8844;'>{item.name}</span> (rot in {item.rot_timer} moves)"
        item_str += price_str

    elif isinstance(item, LembasWafer):
        item_str = f"<span style='color:#FFD700;'>{item.name}</span> (Full + 30 turn sustain)"
        count = getattr(item, 'count', 1)
        if count > 1:
            item_str += f" (x{count})"
        item_str += price_str

    elif isinstance(item, Food):
        item_str = f"<span style='color:#88FF88;'>{item.name}</span> (+{item.nutrition} hunger)"
        count = getattr(item, 'count', 1)
        if count > 1:
            item_str += f" (x{count})"
        item_str += price_str

    elif isinstance(item, CookingKit):
        item_str = f"<span style='color:#FF8844;'>{item.name}</span> [Cook meat]"
        item_str += price_str

    elif isinstance(item, Spell):
        # Get display name (cryptic if unidentified)
        display_name = _get_item_display_name(item, for_vendor=for_vendor) if not is_identified else item.name

        # Spells are blue to distinguish them
        item_str = f"<span style='color: #42A5F5;'>{display_name}</span>"

        # Only show details if identified
        if is_identified:
            # Simple format - just level and memorized status
            memorized_marker = ""
            if player_character and item in player_character.memorized_spells:
                memorized_marker = " <span style='color: #4CAF50;'>[MEM]</span>"
            item_str += f" (L{item.level}){memorized_marker}"
        else:
            item_str += " <span style='color: #888;'>[?]</span>"
        item_str += price_str

    else:
        item_str = f"{item.name}"
        item_str += price_str

    return item_str


# --------------------------------------------------------------------------------
# STATUS EFFECTS
# --------------------------------------------------------------------------------

class StatusEffect:
    def __init__(self, name, duration, effect_type, magnitude=0, description="", resistance_element=None):
        self.name = name
        self.duration = duration  # Duration in turns
        self.effect_type = effect_type  # e.g., 'poison', 'silence', 'stuck', 'damage_over_time', 'heal_over_time', 'stat_boost', 'stat_reduce', 'attack_boost', 'defense_boost'
        self.magnitude = magnitude  # e.g., damage per turn for poison, or stat modifier
        self.description = description
        self.resistance_element = resistance_element

    def tick(self, target):
        """
        Applies the per-turn effect of the status.
        Returns True if the effect is still active, False if it expires this turn.
        """
        if self.duration > 0:
            self.duration -= 1
            # Apply immediate effects specific to the type (e.g., poison damage)
            if self.effect_type == 'damage_over_time' or self.effect_type == 'poison':
                add_log(f"{COLOR_RED}{target.name} is affected by {self.name} and takes {self.magnitude} damage!{COLOR_RESET}")
                target.take_damage_no_def(self.magnitude)
            elif self.effect_type == 'heal_over_time':
                add_log(f"{COLOR_GREEN}{target.name} is affected by {self.name} and heals {self.magnitude} HP!{COLOR_RESET}")
                target.health += self.magnitude
                if target.health > target.max_health:
                    target.health = target.max_health
            # Other effects like stat_boost/reduce are applied via properties/methods, not directly here per tick
            return True
        return False # Effect expired

    def __repr__(self):
        return f"StatusEffect(name='{self.name}', duration={self.duration}, type='{self.effect_type}', mag={self.magnitude})"

POISON_EFFECT = StatusEffect(name='Poison', duration=3, effect_type='poison', magnitude=5, description='You feel the poison slowly hurting your body.')
SILENCE_EFFECT = StatusEffect(name='Silence', duration=2, effect_type='silence', magnitude=0, description='You cannot speak! This will make spell casting impossible.')
CONFUSION_EFFECT = StatusEffect(name='Confusion', duration=2, effect_type='confusion', description='You feel disoriented and might move randomly.')
WEB_EFFECT = StatusEffect(name='Web', duration=3, effect_type='web', description='You are stuck in a sticky web and cannot move.')
STICKY_HANDS_EFFECT = StatusEffect(name='Sticky Hands', duration=4, effect_type='sticky_hands', description='Your hands are covered in a sticky substance, making it hard to use or equip items.')

def apply_poison_to_player(player_character):
    """
    Applies a poison status effect to the player if not already poisoned.
    """
    if 'Poison' in player_character.status_effects:
        add_log(f"{COLOR_YELLOW}You are already poisoned! Moving will continue to apply damage.{COLOR_RESET}")
    else:
        player_character.add_status_effect(
            effect_name='Poison',
            duration=3,
            effect_type='damage_over_time',
            magnitude=5,
            description='You are taking damage from poison.'
        )
        add_log(f"{COLOR_RED}You have been poisoned! Move around to observe the effect. Each move will deal damage.{COLOR_RESET}")
        add_log(f"If your HP reaches 0 from poison, you will be defeated.")

def burn_inventory_items(player_character, source="fire"):
    """
    Chance to destroy potions and scrolls in player's inventory from fire/explosion.
    source: 'fire' (lower chance, 1-2 items) or 'explosion' (higher chance, 1-3 items)
    Also cooks any raw meat in inventory.
    """
    # Cook meat in inventory from fire
    _cook_meat_in_inventory(player_character, source)
    burnable = [item for item in player_character.inventory.items
                if isinstance(item, (Potion, Scroll))]
    if not burnable:
        return

    if source == 'explosion':
        num_at_risk = random.randint(1, min(3, len(burnable)))
        burn_chance = 0.60
    else:  # fire/burn status
        num_at_risk = random.randint(1, min(2, len(burnable)))
        burn_chance = 0.35

    destroyed = []
    for item in random.sample(burnable, num_at_risk):
        if random.random() < burn_chance:
            destroyed.append(item)

    for item in destroyed:
        if item in player_character.inventory.items:
            player_character.inventory.items.remove(item)
            add_log(f"{COLOR_RED}Your {item.name} was destroyed by the {source}!{COLOR_RESET}")

    if not destroyed:
        add_log(f"{COLOR_YELLOW}Your potions and scrolls survived the {source}... barely.{COLOR_RESET}")


def freeze_inventory_items(player_character):
    """
    Chance to destroy potions in player's inventory from freezing attacks.
    Liquid potions freeze solid and shatter. Scrolls are unaffected.
    """
    freezable = [item for item in player_character.inventory.items
                 if isinstance(item, Potion)]
    if not freezable:
        return

    num_at_risk = random.randint(1, min(2, len(freezable)))
    freeze_chance = 0.30

    destroyed = []
    for item in random.sample(freezable, num_at_risk):
        if random.random() < freeze_chance:
            destroyed.append(item)

    for item in destroyed:
        if item in player_character.inventory.items:
            player_character.inventory.items.remove(item)
            add_log(f"{COLOR_CYAN}Your {item.name} froze solid and shattered!{COLOR_RESET}")

    if not destroyed:
        add_log(f"{COLOR_CYAN}Your potions held together against the cold... this time.{COLOR_RESET}")


def rot_food_items(player_character, magnitude=1):
    """
    Mushroom monster spore attack: instantly rots food and meat in player's inventory.
    magnitude 1 (Spore Puff): 1 food item, 40% chance to rot each piece of meat
    magnitude 2 (Myconid Shaman): 1-2 items, 60% chance, cooked meat loses half its rot_timer
    magnitude 3 (Fungal Hulk): 1-3 items, 80% chance, all meat timer halved
    """
    inventory = player_character.inventory.items

    # Collect food and non-rotten meat targets
    food_targets = [item for item in inventory if isinstance(item, Food)]
    meat_targets = [item for item in inventory if isinstance(item, Meat) and not item.is_rotten]

    any_effect = False

    # --- Food destruction ---
    max_food_rot = magnitude
    if food_targets:
        victims = random.sample(food_targets, min(max_food_rot, len(food_targets)))
        for item in victims:
            if item in inventory:
                inventory.remove(item)
                add_log(f"{COLOR_GREY}The spores rot your {item.name} into a pile of mold!{COLOR_RESET}")
                any_effect = True

    # --- Meat rot effect ---
    rot_chance = [0.40, 0.60, 0.80][min(magnitude - 1, 2)]
    for meat in meat_targets:
        if random.random() < rot_chance:
            if magnitude >= 2 and not meat.is_rotten:
                # Higher tiers: halve the remaining rot timer (instant if <= 1)
                meat.rot_timer = max(0, meat.rot_timer // 2)
                if meat.rot_timer <= 0:
                    meat.is_rotten = True
                    meat.name = f"Rotten {meat.monster_name} {meat.cut.capitalize()}"
                    meat.nutrition = -15
                    add_log(f"{COLOR_GREY}The spores instantly rot your {meat.monster_name} {meat.cut}!{COLOR_RESET}")
                else:
                    add_log(f"{COLOR_YELLOW}Spores accelerate the rot on your {meat.name} ({meat.rot_timer} turns left)!{COLOR_RESET}")
            else:
                # Magnitude 1: just decay the timer by 10
                meat.rot_timer = max(0, meat.rot_timer - 10)
                if meat.rot_timer <= 0:
                    meat.is_rotten = True
                    meat.name = f"Rotten {meat.monster_name} {meat.cut.capitalize()}"
                    meat.nutrition = -15
                    add_log(f"{COLOR_GREY}The spores rot your {meat.monster_name} {meat.cut}!{COLOR_RESET}")
                else:
                    add_log(f"{COLOR_YELLOW}Spores hasten the decay of your {meat.name} ({meat.rot_timer} turns left)!{COLOR_RESET}")
            any_effect = True

    if not any_effect:
        add_log(f"{COLOR_GREY}The spores drift past -- you have nothing to rot.{COLOR_RESET}")


def apply_elemental_resistance(target, damage, damage_type):
    """
    Apply elemental resistance to incoming damage.

    Args:
        target: Character or Monster taking damage
        damage: Base damage amount
        damage_type: String like 'Fire', 'Ice', 'Physical', etc.

    Returns:
        final_damage: Damage after resistance reduction
    """

    final_damage = damage

    # Check all resistance status effects
    for effect_name, effect in target.status_effects.items():
        if effect.effect_type == 'elemental_resistance':
            element = getattr(effect, 'resistance_element', None)
            if not element:
                continue

            reduction_pct = effect.magnitude

            # Check if this resistance applies to the damage type
            resistance_applies = False

            if element == damage_type:
                # Direct match (e.g., Fire Resistance vs Fire damage)
                resistance_applies = True

            elif element == 'Universal':
                # Universal resistance applies to everything
                resistance_applies = True

            elif element == 'Multi':
                # Multi covers Fire, Ice, Lightning
                if damage_type in ['Fire', 'Ice', 'Lightning']:
                    resistance_applies = True

            elif element == 'Multi-Natural':
                # Multi-Natural covers Earth, Water, Wind
                if damage_type in ['Earth', 'Water', 'Wind']:
                    resistance_applies = True

            elif element == 'Multi-Arcane':
                # Multi-Arcane covers Holy, Darkness, Psionic
                if damage_type in ['Holy', 'Darkness', 'Psionic']:
                    resistance_applies = True

            # Apply resistance if it matches
            if resistance_applies:
                reduction = int(damage * reduction_pct / 100)
                final_damage = max(0, final_damage - reduction)

                # Visual feedback
                color_map = {
                    'Fire': COLOR_RED,
                    'Ice': COLOR_CYAN,
                    'Lightning': COLOR_YELLOW,
                    'Darkness': COLOR_PURPLE,
                    'Poison': COLOR_GREEN,
                    'Holy': COLOR_YELLOW,
                    'Universal': COLOR_PURPLE
                }
                color = color_map.get(damage_type, COLOR_CYAN)

                add_log(f"{color} {effect_name}: -{reduction} {damage_type} damage ({reduction_pct}%)!{COLOR_RESET}")

    return final_damage


# --------------------------------------------------------------------------------
# CHARACTER & MONSTER CLASSES
# --------------------------------------------------------------------------------

class Character:
    def __init__(self, name, health, attack, defense, strength, dexterity, intelligence, x=0, y=0, z=0):
        self.name = name
        self.health = health
        self._base_attack = attack
        self._base_defense = defense
        self.strength = strength
        self.dexterity = dexterity
        self.intelligence = intelligence
        self.x = x
        self.y = y
        self.z = z
        self.gold = 0
        self.level = 1
        self.experience = 0
        self.inventory = Inventory()
        self.equipped_weapon = None
        self.equipped_armor = None
        self.equipped_accessories = [None, None, None, None]  # 4 accessory slots
        self.race = "Human"
        self.gender = "Unknown"
        self.character_class = "Adventurer"
        self.elemental_strengths = [] # Initialize as empty list
        self.elemental_weaknesses = [] # Initialize as empty list
        self.elemental_resistance = [] # For permanent resistances from potions
        self.status_effects = {}
        self.memorized_spells = []
        # Initialize bonus attributes BEFORE calling max_mana/max_health
        self.base_max_health_bonus = 0  # For permanent HP bonuses (altars, potions, etc.)
        self.base_max_mana_bonus = 0    # For permanent mana bonuses
        # Hunger system
        self.hunger = HUNGER_MAX  # Start full
        self.hunger_freeze_turns = 0  # Lembas wafer postpones hunger decay
        self.hunger_regen_tracker = 0  # Tracks moves for HP regen when well-fed
        # Now safe to call max_mana property
        self.mana = self.max_mana # Initialize mana to max_mana

    @property
    def max_health(self):
        return 100 + (self.level * 10) + (self.strength * 2) + self.base_max_health_bonus

    @property
    def max_mana(
        self
    ):
        # Max mana scales with intelligence and level
        #int requirement
        int_mp = max(0,(self.intelligence-15)*5)
        #level requirement
        lvl_mp = 0
        if (self.intelligence>15):
            lvl_mp = max(0, (self.level-4)*10)
        return max(0, (int_mp+lvl_mp)) + self.base_max_mana_bonus


    @property
    def attack(self):
        # Broken weapon gives no attack bonus
        if self.equipped_weapon and not self.equipped_weapon.is_broken:
            bonus = self.equipped_weapon.attack_bonus
        else:
            bonus = 0
        attack_from_stats = self._base_attack + bonus + (self.strength // 2)
        # Add attack boost from status effects
        for effect in self.status_effects.values():
            if effect.effect_type == 'attack_boost':
                attack_from_stats += effect.magnitude
        return attack_from_stats

    @property
    def defense(self):
        # Broken armor gives no defense bonus
        if self.equipped_armor and not self.equipped_armor.is_broken:
            bonus = self.equipped_armor.defense_bonus
        else:
            bonus = 0
        defense_from_stats = self._base_defense + bonus + (self.dexterity // 3)
        # Add defense boost from status effects
        for effect in self.status_effects.values():
            if effect.effect_type == 'defense_boost':
                defense_from_stats += effect.magnitude
        return defense_from_stats

    def get_current_floor(self, tower):
        """Get the floor the character is currently on."""
        return tower.floors[self.z]

    def get_current_room(self, tower):
        """Get the room the character is currently in."""
        return tower.floors[self.z].grid[self.y][self.x]

    def equip_item(self, item):
        # Calculate strength requirement based on item level
        # Formula: Base 5 + (level * 2), so level 0 = 5 STR, level 5 = 15 STR, level 10 = 25 STR
        if isinstance(item, (Weapon, Armor)):
            str_required = 5 + (item.level * 2)
            if self.strength < str_required:
                add_log(f"{COLOR_RED}You are not strong enough to equip {item.name}!{COLOR_RESET}")
                add_log(f"{COLOR_YELLOW}Requires {str_required} Strength (you have {self.strength}).{COLOR_RESET}")
                return False

        if isinstance(item, Weapon):
            self.equipped_weapon = item
            add_log(f"Equipped {item.name}.")
            return True
        elif isinstance(item, Armor):
            self.equipped_armor = item
            add_log(f"Equipped {item.name}.")
            return True
        return False

    def equip_accessory(self, item, slot=None):
        """Equip a passive treasure to an accessory slot (0-3)."""
        if not isinstance(item, Treasure) or item.treasure_type != 'passive':
            add_log(f"{COLOR_YELLOW}{item.name} cannot be equipped as an accessory.{COLOR_RESET}")
            return False

        # Check if already equipped in any slot
        for i, acc in enumerate(self.equipped_accessories):
            if acc == item:
                add_log(f"{COLOR_YELLOW}{item.name} is already equipped in slot {i+1}.{COLOR_RESET}")
                return False

        # Find an empty slot or use specified slot
        if slot is not None:
            if slot < 0 or slot > 3:
                add_log(f"{COLOR_RED}Invalid accessory slot.{COLOR_RESET}")
                return False
            if self.equipped_accessories[slot] is not None:
                # Unequip existing accessory (this will remove its bonuses)
                self.unequip_accessory(slot)
            self.equipped_accessories[slot] = item
            item.is_equipped = True
            self._apply_accessory_bonuses(item)
            add_log(f"{COLOR_GREEN}Equipped {item.name} in accessory slot {slot+1}!{COLOR_RESET}")
            if item.passive_effect:
                add_log(f"{COLOR_CYAN}Passive: {item.passive_effect}{COLOR_RESET}")
            return True
        else:
            # Find first empty slot
            for i in range(4):
                if self.equipped_accessories[i] is None:
                    self.equipped_accessories[i] = item
                    item.is_equipped = True
                    self._apply_accessory_bonuses(item)
                    add_log(f"{COLOR_GREEN}Equipped {item.name} in accessory slot {i+1}!{COLOR_RESET}")
                    if item.passive_effect:
                        add_log(f"{COLOR_CYAN}Passive: {item.passive_effect}{COLOR_RESET}")
                    return True
            add_log(f"{COLOR_RED}All accessory slots are full! Unequip something first.{COLOR_RESET}")
            return False

    def unequip_accessory(self, slot):
        """Unequip an accessory from a specific slot (0-3)."""
        if slot < 0 or slot > 3:
            add_log(f"{COLOR_RED}Invalid accessory slot.{COLOR_RESET}")
            return False
        if self.equipped_accessories[slot] is None:
            add_log(f"{COLOR_YELLOW}Accessory slot {slot+1} is empty.{COLOR_RESET}")
            return False

        item = self.equipped_accessories[slot]
        self._remove_accessory_bonuses(item)
        item.is_equipped = False
        self.equipped_accessories[slot] = None
        add_log(f"{COLOR_YELLOW}Unequipped {item.name} from slot {slot+1}.{COLOR_RESET}")
        return True

    def _apply_accessory_bonuses(self, item):
        """Apply stat bonuses from an accessory when equipped."""
        if not isinstance(item, Treasure):
            return

        # Define accessory bonuses by name
        accessory_bonuses = {
            'Boots of Haste': {'dexterity': 5},
            'Ring of Regeneration': {},  # Handled per-turn, no static bonus
            'Amulet of True Sight': {},  # Handled via has_true_sight check
            'Cloak of Shadows': {},  # Handled via dodge check in combat
            'Ring of Strength': {'strength': 3},
            'Circlet of Intelligence': {'intelligence': 3},
            'Gauntlets of Power': {'_base_attack': 5},
            'Pendant of Fortitude': {'_base_defense': 5},
            'Belt of the Giant': {'strength': 6, 'base_max_health_bonus': 20},
            'Wizard\'s Monocle': {'intelligence': 5, 'base_max_mana_bonus': 20},
            'Bracers of Balance': {'strength': 2, 'dexterity': 2, 'intelligence': 2},
            'Anklet of Swiftness': {'dexterity': 3},
            'Skull of the Mage': {'intelligence': 8},  # Mana regen handled per-turn
            'Champion\'s Signet': {'strength': 4, 'dexterity': 4, '_base_attack': 10},
            'Heartstone Pendant': {'base_max_health_bonus': 30},  # HP regen handled per-turn
            # New equippable stat accessories
            'Amulet of Health': {'base_max_health_bonus': 10},
            'Ring of Protection': {'_base_defense': 1},
            'Bracer of Strength': {'strength': 2},
            'Circlet of Intellect': {'intelligence': 2},
            'Anklet of Agility': {'dexterity': 2},
            "Platino's Scale": {},  # Physical damage halving handled in combat
            # Taxidermist collection rewards
            "Cloak of the Hunter":    {"dexterity": 3},
            "Venom Ward Amulet":      {"dexterity": 2},
            "Holy Brand Ring":        {"strength": 2, "dexterity": 2, "intelligence": 2},
            "Belt of Giant Slaying":  {"strength": 5, "_base_defense": 5, "base_max_health_bonus": 30},
            "Drake Cloak":            {"_base_defense": 4},
            "Psychic Shield Circlet": {"intelligence": 6, "base_max_mana_bonus": 10},
            "Apex Predator Signet":   {"_base_attack": 8, "dexterity": 5, "strength": 3},
        }

        bonuses = accessory_bonuses.get(item.name, {})
        for stat, amount in bonuses.items():
            if hasattr(self, stat):
                current = getattr(self, stat)
                setattr(self, stat, current + amount)
                # Format stat name for display
                display_name = stat.replace('_base_', '').replace('base_max_', 'Max ').replace('_bonus', '').replace('_', ' ').title()
                add_log(f"{COLOR_GREEN}{display_name} +{amount}!{COLOR_RESET}")

    def _remove_accessory_bonuses(self, item):
        """Remove stat bonuses from an accessory when unequipped."""
        if not isinstance(item, Treasure):
            return

        # Define accessory bonuses by name (same as apply)
        accessory_bonuses = {
            'Boots of Haste': {'dexterity': 5},
            'Ring of Regeneration': {},
            'Amulet of True Sight': {},
            'Cloak of Shadows': {},
            'Ring of Strength': {'strength': 3},
            'Circlet of Intelligence': {'intelligence': 3},
            'Gauntlets of Power': {'_base_attack': 5},
            'Pendant of Fortitude': {'_base_defense': 5},
            'Belt of the Giant': {'strength': 6, 'base_max_health_bonus': 20},
            'Wizard\'s Monocle': {'intelligence': 5, 'base_max_mana_bonus': 20},
            'Bracers of Balance': {'strength': 2, 'dexterity': 2, 'intelligence': 2},
            'Anklet of Swiftness': {'dexterity': 3},
            'Skull of the Mage': {'intelligence': 8},
            'Champion\'s Signet': {'strength': 4, 'dexterity': 4, '_base_attack': 10},
            'Heartstone Pendant': {'base_max_health_bonus': 30},
            # New equippable stat accessories
            'Amulet of Health': {'base_max_health_bonus': 10},
            'Ring of Protection': {'_base_defense': 1},
            'Bracer of Strength': {'strength': 2},
            'Circlet of Intellect': {'intelligence': 2},
            'Anklet of Agility': {'dexterity': 2},
            "Platino's Scale": {},  # Physical damage halving handled in combat
            # Taxidermist collection rewards
            "Cloak of the Hunter":    {"dexterity": 3},
            "Venom Ward Amulet":      {"dexterity": 2},
            "Holy Brand Ring":        {"strength": 2, "dexterity": 2, "intelligence": 2},
            "Belt of Giant Slaying":  {"strength": 5, "_base_defense": 5, "base_max_health_bonus": 30},
            "Drake Cloak":            {"_base_defense": 4},
            "Psychic Shield Circlet": {"intelligence": 6, "base_max_mana_bonus": 10},
            "Apex Predator Signet":   {"_base_attack": 8, "dexterity": 5, "strength": 3},
        }

        bonuses = accessory_bonuses.get(item.name, {})
        for stat, amount in bonuses.items():
            if hasattr(self, stat):
                current = getattr(self, stat)
                setattr(self, stat, current - amount)
                # Format stat name for display
                display_name = stat.replace('_base_', '').replace('base_max_', 'Max ').replace('_bonus', '').replace('_', ' ').title()
                add_log(f"{COLOR_YELLOW}{display_name} -{amount}{COLOR_RESET}")

    def get_equipped_accessory_names(self):
        """Get list of equipped accessory names for display."""
        names = []
        for i, acc in enumerate(self.equipped_accessories):
            if acc:
                names.append(f"{i+1}: {acc.name}")
            else:
                names.append(f"{i+1}: (empty)")
        return names

    def attack_target(self, target):
        for effect_name, effect in self.status_effects.items():
            if effect.effect_type == 'sticky_hands':
                add_log(f"{COLOR_YELLOW}Your hands are sticky, you can't attack!{COLOR_RESET}")
                return 0
            if effect.effect_type == 'web':
                add_log(f"{COLOR_YELLOW}You are stuck in a web and cannot attack!{COLOR_RESET}")
                return 0

        # --- Hit Probability Calculation ---
        # Base chance: 75%
        base_chance = 0.50

        # Dex bonus: +2% per point over 10
        dex_bonus = (self.dexterity - 10) * 0.02

        # Level bonus: +5% per level difference
        level_bonus = (self.level - target.level) * 0.05

        hit_chance = base_chance + dex_bonus + level_bonus

        # Clamp hit chance between 5% and 95%
        hit_chance = max(0.05, min(0.95, hit_chance))

        # Opposed d20 roll: player attack vs monster defense.
        # Display modifiers are derived from the stat totals (already include
        # weapon bonus, strength, status boosts, etc.) scaled to a d20 scale.
        sides = 20
        player_wins = random.random() < hit_chance
        p_mod = max(0, self.attack // 4)
        m_mod = max(0, target.defense // 4)
        p_roll, m_roll = opposed_roll(player_wins, sides, p_mod, m_mod)
        gs.last_dice_rolls.append((p_roll, m_roll, player_wins, "ATK", sides, p_mod, m_mod))
        hit = player_wins
        if not hit:
            add_log(f"{COLOR_YELLOW}You missed the evil {target.name}!{COLOR_RESET}")
            return 0

        # Check weapon status for warnings and damage penalty
        weapon_broken = self.equipped_weapon and self.equipped_weapon.is_broken
        no_weapon = not self.equipped_weapon

        if weapon_broken:
            add_log(f"{COLOR_YELLOW}Hitting a {target.name} with a broken weapon is pretty stupid.{COLOR_RESET}")
        elif no_weapon:
            add_log(f"{COLOR_YELLOW}Pounding on a {target.name} with your fists won't hurt it much!{COLOR_RESET}")

        elemental = self.equipped_weapon.elemental_strength[0] if self.equipped_weapon and not weapon_broken else "None"
        scaled_attack = self.attack
        # Broken weapon or bare fists: drastically reduce damage (max 2 damage)
        if weapon_broken or no_weapon:
            scaled_attack = max(1, self._base_attack // 4)
        elif elemental != "None" and elemental in target.elemental_weakness:
          scaled_attack=int(scaled_attack*1.5)
          print_to_output(f"{target.name} is weak against {elemental}!")

        dmg = max(1, scaled_attack - target.defense)

        # Cloak of the Hunter: 15% chance to bypass target defense entirely
        if _has_hunter_cloak(self) and not (weapon_broken or no_weapon) and random.random() < 0.15:
            dmg = max(1, scaled_attack)
            add_log(f"{COLOR_GREEN}[Hunter Cloak] Defense bypassed!{COLOR_RESET}")

        # Holy Brand Ring: +8 Holy damage on every hit
        holy_bonus = _get_holy_brand_bonus(self)
        if holy_bonus > 0 and not (weapon_broken or no_weapon):
            # Holy damage bypasses defense and hits undead hard
            dmg += holy_bonus
            add_log(f"{COLOR_YELLOW}[Holy Brand] +{holy_bonus} Holy damage!{COLOR_RESET}")

        add_log(f"You hit the evil {target.name}!")
        return dmg

    def take_damage(self, amount, elemental_type="None"):
        # Check for elemental resistance
        """
        Alternative version with individual messages for each damage reduction effect.
        Use this if you want more detailed combat log messages.
        """
        # Step 1: Apply elemental resistance
        actual_damage = apply_elemental_resistance(self, amount, elemental_type)

        # Drake Cloak: 60% fire damage reduction
        if elemental_type == 'Fire' and _has_fire_resistance(self):
            reduction = int(actual_damage * 0.60)
            actual_damage = max(0, actual_damage - reduction)
            add_log(f"{COLOR_RED}[Drake Cloak] Fire resistance absorbs {reduction} damage!{COLOR_RESET}")

        # Defense is already applied in attack_target - don't subtract again
        reduced_amount = max(0, actual_damage)

        # Step 2: Apply damage reduction effects individually
        for effect_name, effect in self.status_effects.items():
            if effect.effect_type == 'damage_reduction':
                reduction = effect.magnitude
                reduced_amount = max(0, reduced_amount - reduction)

                # Custom messages for different effects
                if effect_name == 'Stone Skin':
                    add_log(f"{COLOR_GREY} [Stone Skin] Reduced damage by {reduction}!{COLOR_RESET}")
                else:
                    add_log(f" [{effect_name}] Reduced damage by {reduction}!")

        # Step 4: Apply final damage
        self.health -= reduced_amount
        gs.last_player_damage = reduced_amount
        if reduced_amount == 0:
            gs.last_player_blocked = True

        if reduced_amount > 0:
           add_log(f"You took {reduced_amount} damage!")
        else:
           add_log(f"You were not harmed by the attack.")

        # Fire damage has a chance to destroy potions/scrolls in inventory
        if elemental_type == 'Fire' and reduced_amount > 0:
            burn_inventory_items(self, source='fire')

        # Ice damage has a chance to freeze and shatter potions
        if elemental_type == 'Ice' and reduced_amount > 0:
            freeze_inventory_items(self)

        return self.health <= 0

    def take_damage_no_def(self, amount, elemental_type="None"):
        self.health -= amount
        if amount > 0:
            gs.last_player_damage = amount
        add_log(f"You took {amount} damage!")
        return self.health <= 0

    def add_elemental_strength(self, element):
        if element in self.elemental_weaknesses:
            self.elemental_weaknesses.remove(element)
            add_log(f"You are no longer weak against {element}!")
        if element not in self.elemental_strengths:
            self.elemental_strengths.append(element)
            add_log(f"You are now resistant to {element}.")


    def add_elemental_weakness(self, element):
        if element in self.elemental_strengths:
            self.elemental_strengths.remove(element)
            add_log(f"You are no longer resistant to {element}!")
        if element not in self.elemental_weaknesses:
            self.elemental_weaknesses.append(element)
            add_log(f"You are now weak against {element}!")


    def gain_experience(self, amount):
        self.experience += amount
        add_log(f"You gained {amount} experience.")
        if int(math.sqrt(self.experience)/5) > self.level:
            self.level = int(math.sqrt(self.experience)/5)
            add_log(f"{COLOR_YELLOW}*** LEVEL UP! You are now level {self.level} ***{COLOR_RESET}")
            add_log(f"Max Health increased to {self.max_health}!")
            _check_achievements(self)

    def is_alive(self):
        return self.health > 0

    def cast_spell(self, spell_to_cast, target):

        # Auto-identify spell when cast
        if not _is_item_identified(spell_to_cast):
            _identify_item(spell_to_cast)

        for effect_name, effect in self.status_effects.items():
            if effect.effect_type == 'silence':
                add_log(f"{COLOR_YELLOW}You are silenced and cannot cast spells!{COLOR_RESET}")
                return False

        # Calculate actual mana cost with Knowledge Shard bonus
        actual_cost = spell_to_cast.mana_cost
        if gs.shards_obtained.get('knowledge'):
            actual_cost = int(spell_to_cast.mana_cost * 0.8)  # 20% reduction
            add_log(f"{COLOR_PURPLE}[Knowledge Shard] Mana cost reduced: {spell_to_cast.mana_cost} -> {actual_cost}!{COLOR_RESET}")

        if self.mana < actual_cost:
            add_log(f"{COLOR_YELLOW}Not enough mana to cast {spell_to_cast.name}! You have {self.mana}/{self.max_mana} mana.{COLOR_RESET}")
            return False

        self.mana -= actual_cost
        add_log(f"{COLOR_CYAN}You cast {spell_to_cast.name}! Mana remaining: {self.mana}.{COLOR_RESET}")

        if spell_to_cast.spell_type == 'healing':
            healing_amount = spell_to_cast.base_power + (self.intelligence // 2) # Intelligence boosts healing
            self.health += healing_amount
            if self.health > self.max_health:
                self.health = self.max_health
            gs.last_player_heal = healing_amount
            add_log(f"{COLOR_GREEN}You healed for {healing_amount} HP! Current health: {self.health}.{COLOR_RESET}")
            return True
        elif spell_to_cast.spell_type == 'damage':
            # Base spell damage boosted by player's intelligence and spell level
            # INT scaling: higher INT rewards higher-level spells significantly
            int_bonus = (self.intelligence // 2) + (max(0, self.intelligence - 10) * spell_to_cast.level // 3)
            base_damage = spell_to_cast.base_power + int_bonus
            effective_damage = base_damage

            # Elemental interactions
            if spell_to_cast.damage_type != 'Physical': # Physical damage doesn't have elemental weaknesses/strengths in this context
                if spell_to_cast.damage_type in target.elemental_weakness:
                    effective_damage = int(effective_damage * 2.5)
                    add_log(f"{COLOR_RED}{target.name} is weak to {spell_to_cast.damage_type}! Devastating damage!{COLOR_RESET}")
                elif spell_to_cast.damage_type in target.elemental_strength:
                    effective_damage = int(effective_damage * 0.5)
                    add_log(f"{COLOR_GREEN}{target.name} is resistant to {spell_to_cast.damage_type}! Reduced damage.{COLOR_RESET}")

            # Apply target's defense - elemental weakness hits bypass half of defense
            if spell_to_cast.damage_type in target.elemental_weakness:
                reduced_defense = target.defense // 2
            else:
                reduced_defense = target.defense
            final_damage = max(1, effective_damage - reduced_defense)
            add_log(f"{COLOR_RED}Your {spell_to_cast.name} hits {target.name} for {final_damage} {spell_to_cast.damage_type} damage!{COLOR_RESET}")
            target.take_damage(final_damage, spell_to_cast.damage_type)
            return True
        elif spell_to_cast.spell_type == 'remove_status':
            if spell_to_cast.status_effect_name:
                if spell_to_cast.status_effect_name in self.status_effects:
                    self.remove_status_effect(spell_to_cast.status_effect_name)
                    add_log(f"{COLOR_GREEN}{self.name} cleansed {spell_to_cast.status_effect_name}!{COLOR_RESET}")
                else:
                    add_log(f"{COLOR_YELLOW}{self.name} is not affected by {spell_to_cast.status_effect_name}.{COLOR_RESET}")
            else:
                add_log(f"{COLOR_YELLOW}No specific status effect to remove for {spell_to_cast.name}.{COLOR_RESET}")
            return True
        elif spell_to_cast.spell_type == 'add_status_effect':
            if spell_to_cast.status_effect_name and spell_to_cast.status_effect_type:
                target.add_status_effect(
                    effect_name=spell_to_cast.status_effect_name,
                    duration=spell_to_cast.status_effect_duration,
                    effect_type=spell_to_cast.status_effect_type,
                    magnitude=spell_to_cast.status_effect_magnitude,
                    description=spell_to_cast.description # Re-use spell description for effect
                )
                add_log(f"{COLOR_GREEN}{target.name} is now affected by {spell_to_cast.status_effect_name}!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_YELLOW}Missing status effect details for {spell_to_cast.name}. No effect.{COLOR_RESET}")
            return True
        else:
            add_log(f"{COLOR_YELLOW}Unknown spell type for {spell_to_cast.name}. No effect.{COLOR_RESET}")
            return False

    def add_status_effect(self, effect_name, duration, effect_type, magnitude=0, description=""):
        # Venom Ward Amulet: block all poison effects
        if effect_type == 'poison' and _has_poison_immunity(self):
            add_log(f"{COLOR_GREEN}[Venom Ward] You are immune to poison!{COLOR_RESET}")
            return
        # Psychic Shield Circlet: block confusion
        if effect_type == 'confusion' and _has_confusion_immunity(self):
            add_log(f"{COLOR_CYAN}[Psychic Shield] Your mind repels the confusion!{COLOR_RESET}")
            return
        effect = StatusEffect(effect_name, duration, effect_type, magnitude, description)
        self.status_effects[effect_name] = effect
        add_log(f"{self.name} is now affected by {effect_name}!")
        if effect_type in gs.NEGATIVE_EFFECT_TYPES:
            gs.last_player_status = effect_name
        # Track poison for achievements
        if effect_name == 'Poison':
            gs.game_stats['times_poisoned'] = gs.game_stats.get('times_poisoned', 0) + 1

    def remove_status_effect(self, effect_name):
        if effect_name in self.status_effects:
            del self.status_effects[effect_name]
            add_log(f"{self.name} is no longer affected by {effect_name}.")

    def process_status_effects(self):
        """Processes all active status effects for the character."""
        effects_to_remove = []
        for name, effect in list(self.status_effects.items()):
            if not effect.tick(self): # Use the tick method of StatusEffect
                effects_to_remove.append(name)
        for name in effects_to_remove:
            self.remove_status_effect(name)
        # Process regeneration
        if 'Regeneration' in self.status_effects:
            heal_amount = self.status_effects['Regeneration'].magnitude
            old_health = self.health
            self.health = min(self.max_health, self.health + heal_amount)
            actual_heal = self.health - old_health
            if actual_heal > 0:
                add_log(f"{COLOR_GREEN}[Regeneration] +{actual_heal} HP{COLOR_RESET}")

    def get_spell_slots(self, spell):
        """Calculate how many slots a spell takes to memorize based on its level."""
        # Level 0 spells: 1 slot
        # Level 1-2 spells: 2 slots
        # Level 3+ spells: 3 slots
        if spell.level == 0:
            return 1
        elif spell.level <= 2:
            return 2
        else:
            return 3

    def get_max_memorized_spell_slots(self):
        """Calculate maximum number of spell slots available."""
        # Max mana scales with intelligence and level
        #int requirement
        int_ss = max(0,(self.intelligence-15)//2)
        #level requirement
        lvl_ss = 0
        if (self.intelligence>15):
            lvl_ss = max(0, (self.level-4))
        return max(0, (int_ss+lvl_ss))


    def get_used_spell_slots(self):
        """Calculate how many spell slots are currently in use."""
        return sum(self.get_spell_slots(spell) for spell in self.memorized_spells)

    def get_spell_inventory(self):
        """Get all Spell items from inventory."""
        return [item for item in self.inventory.items if isinstance(item, Spell)]

    def memorize_spell(self, spell):
        """Memorize a spell if there's room."""
        if spell not in self.get_spell_inventory():
            return False, "You don't have that spell in your inventory."

        # Must identify spell before memorizing
        if not _is_item_identified(spell):
            cryptic_name = _get_item_display_name(spell)
            return False, f"You must identify this {cryptic_name} before you can memorize it."

        if spell in self.memorized_spells:
            return False, "That spell is already memorized."

        spell_slots_needed = self.get_spell_slots(spell)
        max_slots = self.get_max_memorized_spell_slots()
        used_slots = self.get_used_spell_slots()

        if used_slots + spell_slots_needed > max_slots:
            return False, f"Not enough slots. Need {spell_slots_needed}, have {max_slots - used_slots}/{max_slots} free."

        self.memorized_spells.append(spell)

        # QUEST TRACKING: Rune of Knowledge - track unique spells memorized
        if not gs.runes_obtained['knowledge']:
            spell_name = spell.name
            if spell_name not in gs.rune_progress['unique_spells_memorized']:
                gs.rune_progress['unique_spells_memorized'].add(spell_name)
                gs.rune_progress['spells_learned_total'] = len(gs.rune_progress['unique_spells_memorized'])
                if gs.rune_progress['spells_learned_total'] >= gs.rune_progress_reqs['spells_learned_total'] and not gs.codex_available:
                    gs.codex_available = True
                    add_log(f"{COLOR_PURPLE}Your mastery of magic deepens... The Codex of Zot awaits!{COLOR_RESET}")

        return True, f"You memorized {spell.name} ({spell_slots_needed} slot{'s' if spell_slots_needed > 1 else ''})."

    def forget_spell(self, spell):
        """Forget a memorized spell."""
        if spell in self.memorized_spells:
            spell_slots_freed = self.get_spell_slots(spell)
            self.memorized_spells.remove(spell)
            return True, f"You forgot {spell.name} (freed {spell_slots_freed} slot{'s' if spell_slots_freed > 1 else ''})."
        return False, "That spell is not memorized."

    def can_cast_spell(self, spell):
        """Check if a spell can be cast (must be memorized and have enough mana)."""
        if spell not in self.memorized_spells:
            return False, "You haven't memorized that spell."

        # Calculate actual mana cost with Knowledge Shard bonus
        actual_cost = spell.mana_cost
        if gs.shards_obtained.get('knowledge'):
            actual_cost = int(spell.mana_cost * 0.8)  # 20% reduction

        if self.mana < actual_cost:
            return False, f"Not enough mana. Need {actual_cost}, have {self.mana}."
        return True, "OK"


class Monster:
    def __init__(self, name, health, attack, defense, elemental_weakness, elemental_strength, level, attack_element="Physical", flavor_text="", victory_text="", can_talk=False, greeting_template="", special_attack=None):
        super().__init__()
        self.name = name
        self.health = health
        self.max_health = health
        self.attack = attack
        self.defense = defense
        self.elemental_weakness = elemental_weakness
        self.elemental_strength = elemental_strength
        self.level = level
        self.attack_element = attack_element
        self.flavor_text = flavor_text
        self.victory_text = victory_text
        self.status_effects = {}
        self.can_talk = can_talk
        self.greeting_template = greeting_template
        self.special_attack = special_attack
        self.properties = {}  # For storing special flags like is_champion, is_legendary

    def take_damage(self, amount, elemental_type):
        actual_damage = apply_elemental_resistance(self, amount, elemental_type)

        # Defense is already applied in attack_target - just apply elemental resistance here
        final_dmg = int(max(1, actual_damage))
        self.health -= final_dmg
        gs.last_monster_damage = final_dmg
        add_log(f"{self.name} took {final_dmg} damage.")
        return final_dmg

    def take_damage_no_def(self, amount, elemental_type="None"):
        self.health -= amount
        if amount > 0:
            gs.last_monster_damage = amount
        add_log(f"{self.name} took {amount} damage.")
        return self.health <= 0

    def attack_target(self, target):
        base_chance = 0.70
        # Monster Level bonus: +3% per level difference (monster_level - player_level)
        level_bonus = (self.level - target.level) * 0.03
        # Player Dexterity penalty (dodge chance): -1% per point over 10
        dex_penalty = (target.dexterity - 10) * -0.01
        hit_chance = base_chance + level_bonus + dex_penalty
        # Clamp hit chance between a reasonable range, e.g., 10% and 90%
        hit_chance = max(0.10, min(0.90, hit_chance))

        if _has_dodge_cloak(gs.player_character):
            hit_chance *= 0.8  # 20% reduced

        # Opposed d20 roll: monster attack vs player defense.
        # hit_chance is the monster's chance to hit; player_wins (dodge) is the inverse.
        # For DEF entries, p_mod is the PLAYER's defense mod and m_mod is the
        # MONSTER's attack mod — so the same (p_roll+p_mod > m_roll+m_mod) → player_wins
        # check holds regardless of ATK/DEF label.
        sides = 20
        monster_hits = random.random() < hit_chance
        player_wins = not monster_hits  # player dodged if monster missed
        p_mod = max(0, target.defense // 4)
        m_mod = max(0, self.attack // 4)
        p_roll, m_roll = opposed_roll(player_wins, sides, p_mod, m_mod)
        gs.last_dice_rolls.append((p_roll, m_roll, player_wins, "DEF", sides, p_mod, m_mod))
        hit = monster_hits
        if not hit:
          gs.last_player_blocked = True
          add_log(f"{COLOR_YELLOW}{self.name} missed {target.name}!{COLOR_RESET}")
          return 0 # No damage dealt
        # If it hits, calculate damage
        dmg = max(1, self.attack - target.defense)

        # Raid mode: monsters deal +25% damage while raid is active
        try:
            current_fl = gs.my_tower.floors[target.z]
            if current_fl.properties.get('raid_mode_active'):
                dmg = max(1, int(dmg * current_fl.properties.get('raid_atk_mult', 1.25)))
        except Exception:
            pass

        # Platino's Scale: halve physical damage
        if self.attack_element in ('Physical', 'None', None):
            for acc in target.equipped_accessories:
                if acc and acc.name == "Platino's Scale":
                    dmg = max(1, dmg // 2)
                    break

        add_log(f"Ouch! {self.name} hit {target.name}!")
        target.take_damage(dmg, self.attack_element)

        # ======= NEW: SPECIAL ATTACK CODE =======
        if self.special_attack and random.random() < self.special_attack.get('chance', 0):
            effect_type = self.special_attack['effect_type']
            duration = self.special_attack.get('duration', 3)
            magnitude = self.special_attack.get('magnitude', 5)
            description = self.special_attack.get('description', 'uses a special attack')

            if effect_type == 'life_drain':
                drain_amount = magnitude
                target.take_damage_no_def(drain_amount, 'Shadow')
                old_health = self.health
                self.health = min(self.max_health, self.health + drain_amount)
                healed = self.health - old_health
                add_log(f"{COLOR_PURPLE} The {self.name} {description}!{COLOR_RESET}")
                add_log(f"{COLOR_RED}You lose {drain_amount} HP to life drain!{COLOR_RESET}")
                if healed > 0:
                    add_log(f"{COLOR_GREEN}The {self.name} heals {healed} HP!{COLOR_RESET}")
            else:
                target.add_status_effect(
                    effect_name=f"{self.name}'s {effect_type.replace('_', ' ').title()}",
                    duration=duration,
                    effect_type=effect_type,
                    magnitude=magnitude,
                    description=description
                )
                add_log(f"{COLOR_PURPLE} The {self.name} {description}!{COLOR_RESET}")

                if effect_type == 'web':
                    add_log(f"{COLOR_YELLOW}You are caught in sticky webbing!{COLOR_RESET}")
                elif effect_type == 'poison':
                    add_log(f"{COLOR_GREEN}Poison courses through your veins!{COLOR_RESET}")
                elif effect_type == 'paralysis':
                    add_log(f"{COLOR_YELLOW}Your body refuses to move!{COLOR_RESET}")
                elif effect_type == 'confusion':
                    add_log(f"{COLOR_PURPLE}Your mind reels in confusion!{COLOR_RESET}")
                elif effect_type == 'weakness':
                    add_log(f"{COLOR_GREY}You feel weakened!{COLOR_RESET}")
                elif effect_type == 'burn':
                    add_log(f"{COLOR_RED}Your flesh burns!{COLOR_RESET}")
                    burn_inventory_items(target, source='fire')
                elif effect_type == 'freeze':
                    add_log(f"{COLOR_CYAN}You are frozen by intense cold!{COLOR_RESET}")
                    freeze_inventory_items(target)
                elif effect_type == 'food_rot':
                    add_log(f"{COLOR_GREY}A cloud of spores engulfs your pack!{COLOR_RESET}")
                    rot_food_items(target, magnitude=magnitude)

        return dmg

    def is_alive(self):
        return self.health > 0

    def add_status_effect(self, effect_name, duration, effect_type, magnitude=0, description=""):
        effect = StatusEffect(effect_name, duration, effect_type, magnitude, description)
        self.status_effects[effect_name] = effect
        add_log(f"{self.name} is now affected by {effect_name}!")
        if effect_type in gs.NEGATIVE_EFFECT_TYPES:
            gs.last_monster_status = effect_name

    def remove_status_effect(self, effect_name):
        if effect_name in self.status_effects:
            del self.status_effects[effect_name]
            add_log(f"{self.name} is no longer affected by {effect_name}.")

    def process_status_effects(self):
        """Processes all active status effects for the monster."""
        effects_to_remove = []
        for name, effect in list(self.status_effects.items()):
            if not effect.tick(self):
                effects_to_remove.append(name)
        for name in effects_to_remove:
            self.remove_status_effect(name)


VAULT_DEFENDER_TEMPLATES = [
    {
        'name': 'Vault Guardian Golem',
        'base_health': 150,
        'base_attack': 25,
        'base_defense': 15,
        'health_per_level': 30,
        'attack_per_level': 5,
        'defense_per_level': 3,
        'elemental_weakness': ['Earth'],
        'elemental_strength': ['Physical', 'Fire'],
        'attack_element': 'Physical',
        'flavor_text': 'An ancient construct powered by magical runes. Its sole purpose: guard the vault.',
        'victory_text': 'The golem crumbles, its enchantments broken. The vault treasure is yours!',
        'can_talk': True,
        'greeting_template': 'HALT, {name} {title}. You have entered the sacred vault. Defeat me, or perish. There is no escape.'
    },
    {
        'name': 'Vault Keeper Wraith',
        'base_health': 120,
        'base_attack': 30,
        'base_defense': 10,
        'health_per_level': 25,
        'attack_per_level': 6,
        'defense_per_level': 2,
        'elemental_weakness': ['Holy', 'Light'],
        'elemental_strength': ['Darkness', 'Physical'],
        'attack_element': 'Darkness',
        'flavor_text': 'A spectral guardian bound to the vault for eternity.',
        'victory_text': 'The wraith wails as it dissipates. The vault treasure is now unguarded!',
        'can_talk': True,
        'greeting_template': '{title} {name}... your life ends here. The vault\'s treasure is NOT for mortals!'
    },
    {
        'name': 'Vault Sentinel Dragon',
        'base_health': 180,
        'base_attack': 28,
        'base_defense': 12,
        'health_per_level': 35,
        'attack_per_level': 5,
        'defense_per_level': 3,
        'elemental_weakness': ['Ice'],
        'elemental_strength': ['Fire', 'Physical'],
        'attack_element': 'Fire',
        'flavor_text': 'A young dragon, bound by ancient magic to guard this vault until death.',
        'victory_text': 'The dragon roars one last time before collapsing. You have proven worthy of the vault treasure!',
        'can_talk': True,
        'greeting_template': 'So, {name} {title}, you dare challenge me? I am bound to this vault for eternity. Prepare to join me in death!'
    },
    {
        'name': 'Vault Warden Lich',
        'base_health': 100,
        'base_attack': 35,
        'base_defense': 8,
        'health_per_level': 20,
        'attack_per_level': 7,
        'defense_per_level': 2,
        'elemental_weakness': ['Holy'],
        'elemental_strength': ['Darkness', 'Psionic'],
        'attack_element': 'Darkness',
        'flavor_text': 'An undead sorcerer, its soul trapped as eternal guardian of the vault.',
        'victory_text': 'The lich crumbles to dust. Its eternal vigil is finally over. The vault treasure is yours!',
        'can_talk': True,
        'greeting_template': 'Mortal fool, {name}... The vault will be your tomb. None have ever defeated me and lived!'
    },
    {
        'name': 'Vault Protector Titan',
        'base_health': 200,
        'base_attack': 22,
        'base_defense': 18,
        'health_per_level': 40,
        'attack_per_level': 4,
        'defense_per_level': 4,
        'elemental_weakness': ['Psionic'],
        'elemental_strength': ['Physical', 'Earth'],
        'attack_element': 'Physical',
        'flavor_text': 'A colossal construct of stone and steel, built to be the perfect guardian.',
        'victory_text': 'The titan falls with a thunderous crash. Against all odds, you have triumphed!',
        'can_talk': True,
        'greeting_template': '{name} {title}. ANALYSIS: THREAT LEVEL - INSUFFICIENT. INITIATING TERMINATION PROTOCOL.'
    }
]
