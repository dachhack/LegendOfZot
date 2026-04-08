"""
items.py - Item classes and item-related systems for Wizard's Cavern.
Contains all item subclasses, identification, durability, and item management functions.
"""

import random
import math
from . import game_state as gs
from .game_state import (add_log, COLOR_RED, COLOR_GREEN, COLOR_RESET, COLOR_PURPLE,
                        COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_GREY, BOLD, UNDERLINE,
                        normal_int_range, get_article)


def register_item_discovery(item):
    """Register an item as discovered in the journal - only if identified"""
    
    # Only register if item is identified
    if not is_item_identified(item):
        return

    item_name = item.name

    if isinstance(item, Weapon):
        gs.discovered_items['weapons'].add(item_name)
    elif isinstance(item, Armor):
        gs.discovered_items['armor'].add(item_name)
    elif isinstance(item, Potion):
        gs.discovered_items['potions'].add(item_name)
    elif isinstance(item, Scroll):
        gs.discovered_items['scrolls'].add(item_name)
    elif isinstance(item, Spell):
        gs.discovered_items['spells'].add(item_name)
    elif isinstance(item, Treasure):
        gs.discovered_items['treasures'].add(item_name)
    elif isinstance(item, (Flare, Lantern, LanternFuel, Food, CookingKit)):
        gs.discovered_items['utilities'].add(item_name)
    elif isinstance(item, Ingredient):
        gs.discovered_items['ingredients'].add(item_name)


# ============================================================================
# ITEM IDENTIFICATION SYSTEM
# ============================================================================

# Cryptic names for unidentified potions (color-based like NetHack)
POTION_CRYPTIC_NAMES = [
    "Bubbling Potion", "Smoky Potion", "Cloudy Potion", "Effervescent Potion",
    "Fizzy Potion", "Milky Potion", "Murky Potion", "Glowing Potion",
    "Sparkling Potion", "Swirling Potion", "Viscous Potion", "Luminous Potion",
    "Oily Potion", "Slimy Potion", "Fuming Potion", "Steaming Potion",
    "Pungent Potion", "Clear Potion", "Thick Potion", "Watery Potion",
    "Iridescent Potion", "Shimmering Potion", "Opaque Potion", "Frothy Potion",
    "Dusty Potion", "Greasy Potion", "Chunky Potion", "Layered Potion"
]

# Cryptic names for unidentified scrolls (material-based like NetHack)
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
    "Scroll labeled HACKEM MUCHE", "Scroll labeled VELOX NEB"
]

# Cryptic names for unidentified spells (mystical appearance)
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

# Cryptic names for unidentified weapons (appearance-based)
WEAPON_CRYPTIC_NAMES = [
    "Rusty Blade", "Worn Sword", "Notched Axe", "Dented Mace",
    "Tarnished Dagger", "Weathered Spear", "Crude Club", "Old Hammer",
    "Battered Blade", "Scratched Sword", "Chipped Axe", "Bent Blade",
    "Dusty Weapon", "Ancient Blade", "Mysterious Sword", "Strange Dagger",
    "Ornate Blade", "Etched Sword", "Runed Weapon", "Glinting Blade"
]

# Cryptic names for unidentified armor (appearance-based)
ARMOR_CRYPTIC_NAMES = [
    "Dented Armor", "Worn Mail", "Rusty Plate", "Tattered Leather",
    "Faded Robes", "Patched Armor", "Scuffed Mail", "Dingy Plate",
    "Frayed Leather", "Dusty Armor", "Mysterious Garb", "Strange Mail",
    "Ancient Armor", "Ornate Plate", "Etched Mail", "Glinting Armor",
    "Battered Plate", "Weathered Mail", "Crude Armor", "Old Leather"
]

EQUIPMENT_ID_THRESHOLD = 5  # Number of combats before auto-identify

def initialize_identification_system():
    """
    Initialize the identification system for a new game.
    Shuffles cryptic names and creates mappings.
    Called at game start.
    """
    from .item_templates import SCROLL_TEMPLATES, WEAPON_TEMPLATES, ARMOR_TEMPLATES

    # Reset identification state
    gs.identified_items = set()
    gs.equipment_use_count = {}
    
    # Shuffle cryptic name lists
    potion_names = POTION_CRYPTIC_NAMES.copy()
    scroll_names = SCROLL_CRYPTIC_NAMES.copy()
    spell_names = SPELL_CRYPTIC_NAMES.copy()
    weapon_names = WEAPON_CRYPTIC_NAMES.copy()
    armor_names = ARMOR_CRYPTIC_NAMES.copy()
    
    random.shuffle(potion_names)
    random.shuffle(scroll_names)
    random.shuffle(spell_names)
    random.shuffle(weapon_names)
    random.shuffle(armor_names)
    
    # Create mappings for potions
    gs.item_cryptic_mapping['potions'] = {}
    potion_idx = 0
    for potion in POTION_TEMPLATES:
        if potion_idx < len(potion_names):
            gs.item_cryptic_mapping['potions'][potion.name] = potion_names[potion_idx]
            potion_idx += 1
    
    # Create mappings for scrolls
    gs.item_cryptic_mapping['scrolls'] = {}
    scroll_idx = 0
    for scroll in SCROLL_TEMPLATES:
        if scroll_idx < len(scroll_names):
            gs.item_cryptic_mapping['scrolls'][scroll.name] = scroll_names[scroll_idx]
            scroll_idx += 1
    
    # Create mappings for spells
    gs.item_cryptic_mapping['spells'] = {}
    spell_idx = 0
    for spell in SPELL_TEMPLATES:
        if spell_idx < len(spell_names):
            gs.item_cryptic_mapping['spells'][spell.name] = spell_names[spell_idx]
            spell_idx += 1
    
    # Create mappings for weapons
    gs.item_cryptic_mapping['weapons'] = {}
    weapon_idx = 0
    for weapon in WEAPON_TEMPLATES:
        if weapon_idx < len(weapon_names):
            gs.item_cryptic_mapping['weapons'][weapon.name] = weapon_names[weapon_idx]
            weapon_idx += 1
    
    # Create mappings for armor
    gs.item_cryptic_mapping['armor'] = {}
    armor_idx = 0
    for armor in ARMOR_TEMPLATES:
        if armor_idx < len(armor_names):
            gs.item_cryptic_mapping['armor'][armor.name] = armor_names[armor_idx]
            armor_idx += 1

def is_item_identified(item):
    """Check if an item type has been identified"""
    
    # Treasures and utilities are always identified
    if isinstance(item, (Treasure, Flare, Lantern, LanternFuel)):
        return True
    
    # Check the real name
    return item.name in gs.identified_items

def identify_item(item, silent=False):
    """
    Identify an item type. All items of this type become identified.
    Returns True if this was a new identification.
    """
    
    if item.name in gs.identified_items:
        return False  # Already identified
    
    gs.identified_items.add(item.name)
    
    if not silent:
        add_log(f"{COLOR_CYAN}You have identified: {item.name}!{COLOR_RESET}")
    
    # Register in journal now that it's identified
    register_item_discovery(item)
    
    return True

def get_item_display_name(item, for_vendor=False):
    """
    Get the display name for an item, accounting for identification status.
    for_vendor: If True, vendors show the real name (they know what items are)
    
    Note: Weapons and armor always show their real name - you can see what they are.
    Potions, scrolls, and spells have cryptic/obfuscated names when unidentified.
    """
    
    # Always show real name if identified
    if is_item_identified(item):
        # For weapons/armor, use get_display_name if available (includes upgrades)
        if hasattr(item, 'get_display_name'):
            return item.get_display_name()
        return item.name
    
    # Vendors know what items really are
    if for_vendor:
        if hasattr(item, 'get_display_name'):
            return item.get_display_name()
        return item.name
    
    # Return cryptic name for unidentified potions, scrolls, and spells
    if isinstance(item, Potion):
        return gs.item_cryptic_mapping['potions'].get(item.name, item.name)
    elif isinstance(item, Scroll):
        return gs.item_cryptic_mapping['scrolls'].get(item.name, item.name)
    elif isinstance(item, Spell):
        return gs.item_cryptic_mapping['spells'].get(item.name, item.name)
    
    # Weapons and armor always show real name - stats are what's unknown
    # Default: return real name
    if hasattr(item, 'get_display_name'):
        return item.get_display_name()
    return item.name

def track_equipment_use(item):
    """
    Track equipment usage in combat. After threshold, auto-identify.
    Call this after each combat round where equipment is used.
    """
    
    if not isinstance(item, (Weapon, Armor)):
        return
    
    if is_item_identified(item):
        return
    
    item_id = id(item)
    gs.equipment_use_count[item_id] = gs.equipment_use_count.get(item_id, 0) + 1
    
    if gs.equipment_use_count[item_id] >= EQUIPMENT_ID_THRESHOLD:
        add_log(f"{COLOR_CYAN}Through extensive use, you've learned the true nature of your equipment!{COLOR_RESET}")
        identify_item(item)

def get_vendor_identify_cost(item):
    """Calculate the cost to identify an item at a vendor"""
    base_cost = 25
    level_mult = item.level + 1
    
    if isinstance(item, (Weapon, Armor)):
        return base_cost * level_mult * 2  # Equipment costs more
    else:
        return base_cost * level_mult

def vendor_identify_item(item, player_character):
    """
    Have a vendor identify an item for gold.
    Returns True if successful.
    """
    cost = get_vendor_identify_cost(item)
    
    if player_character.gold < cost:
        add_log(f"{COLOR_RED}You don't have enough gold! Identification costs {cost} gold.{COLOR_RESET}")
        return False
    
    if is_item_identified(item):
        add_log(f"{COLOR_YELLOW}That item is already identified.{COLOR_RESET}")
        return False
    
    player_character.gold -= cost
    identify_item(item)
    add_log(f"{COLOR_GREEN}The vendor examines the item carefully...{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}You paid {cost} gold for identification.{COLOR_RESET}")
    
    return True


# ============================================================================
# DURABILITY SYSTEM
# ============================================================================

def calculate_durability_loss(item, monster_level):
    """
    Calculate how much durability an item loses when used against a monster.
    Higher level monsters cause more wear. Better items resist wear better.
    Returns the durability loss amount.
    """
    if not isinstance(item, (Weapon, Armor)):
        return 0
    
    # Base loss is 1 per combat
    base_loss = 1
    
    # Monster level adds to wear (every 5 levels adds +1 wear)
    monster_bonus = monster_level // 5
    
    # Item level and upgrades reduce wear
    item_protection = (item.level + item.upgrade_level) // 3
    
    # Calculate final loss (minimum 1)
    final_loss = max(1, base_loss + monster_bonus - item_protection)
    
    return final_loss

def calculate_break_chance(item, monster_level):
    """
    Calculate the chance of an item breaking when durability hits 0.
    Higher level/upgraded items are less likely to break completely.
    Returns a float between 0 and 1.
    """
    if not isinstance(item, (Weapon, Armor)):
        return 0
    
    # Base break chance when durability is 0
    base_chance = 0.50  # 50% base chance
    
    # Each item level reduces break chance by 3%
    level_reduction = item.level * 0.03
    
    # Each upgrade reduces break chance by 5%
    upgrade_reduction = item.upgrade_level * 0.05
    
    # Monster level increases break chance slightly
    monster_increase = monster_level * 0.01
    
    # Calculate final chance (minimum 5%, maximum 80%)
    final_chance = base_chance - level_reduction - upgrade_reduction + monster_increase
    final_chance = max(0.05, min(0.80, final_chance))
    
    return final_chance

def degrade_equipment(player_character, monster_level):
    """
    Degrade the player's equipped weapon and armor after combat.
    Called after each combat round where the player attacks/is attacked.
    Returns a list of messages about equipment status.
    """
    messages = []
    
    # Degrade weapon
    if player_character.equipped_weapon and not player_character.equipped_weapon.is_broken:
        weapon = player_character.equipped_weapon
        loss = calculate_durability_loss(weapon, monster_level)
        weapon.durability = max(0, weapon.durability - loss)
        
        # Check for low durability warnings
        if weapon.durability == 0:
            break_chance = calculate_break_chance(weapon, monster_level)
            if random.random() < break_chance:
                messages.append(f"{COLOR_RED}Your {weapon.name} shatters to pieces! It is gone forever!{COLOR_RESET}")
                player_character.inventory.items.remove(weapon)
                player_character.equipped_weapon = None
            else:
                messages.append(f"{COLOR_RED}Your {weapon.name} is broken! It gives no combat bonus and needs repair before it is useful again!{COLOR_RESET}")
        elif weapon.durability_percent <= 25:
            messages.append(f"{COLOR_YELLOW}Your {weapon.name} is badly damaged ({weapon.durability}/{weapon.max_durability})!{COLOR_RESET}")
        elif weapon.durability_percent <= 50 and (weapon.durability + loss) > (weapon.max_durability * 0.5):
            messages.append(f"{COLOR_YELLOW}Your {weapon.name} is getting worn ({weapon.durability}/{weapon.max_durability}).{COLOR_RESET}")
    
    # Degrade armor
    if player_character.equipped_armor and not player_character.equipped_armor.is_broken:
        armor = player_character.equipped_armor
        loss = calculate_durability_loss(armor, monster_level)
        armor.durability = max(0, armor.durability - loss)
        
        # Check for low durability warnings
        if armor.durability == 0:
            break_chance = calculate_break_chance(armor, monster_level)
            if random.random() < break_chance:
                messages.append(f"{COLOR_RED}Your {armor.name} falls apart in tatters! It is gone forever!{COLOR_RESET}")
                player_character.inventory.items.remove(armor)
                player_character.equipped_armor = None
            else:
                messages.append(f"{COLOR_RED}Your {armor.name} is broken! It gives no protection and needs repair before it is useful again!{COLOR_RESET}")
        elif armor.durability_percent <= 25:
            messages.append(f"{COLOR_YELLOW}Your {armor.name} is badly damaged ({armor.durability}/{armor.max_durability})!{COLOR_RESET}")
        elif armor.durability_percent <= 50 and (armor.durability + loss) > (armor.max_durability * 0.5):
            messages.append(f"{COLOR_YELLOW}Your {armor.name} is getting worn ({armor.durability}/{armor.max_durability}).{COLOR_RESET}")
    
    return messages

# Metal items that can be rusted
METAL_WEAPONS = ['Sword', 'Dagger', 'Axe', 'Mace', 'Hammer', 'Spear', 'Halberd', 'Flail', 
                 'Longsword', 'Shortsword', 'Greatsword', 'Battleaxe', 'Warhammer', 
                 'Iron', 'Steel', 'Chain', 'Plate']
METAL_ARMOR = ['Chainmail', 'Plate', 'Mail', 'Iron', 'Steel', 'Brigandine', 'Scale',
               'Splint', 'Half Plate', 'Full Plate', 'Chain', 'Ring']

# Organic/burnable items
ORGANIC_WEAPONS = ['Staff', 'Club', 'Quarterstaff', 'Wood', 'Bow']
ORGANIC_ARMOR = ['Leather', 'Hide', 'Padded', 'Cloth', 'Robe']

# Monsters with equipment-damaging effects
CORROSIVE_MONSTERS = {
    'Rust Monster': {'type': 'rust', 'damage': (3, 8), 'targets': 'metal', 'break_chance': 0.4},
    'Gelatinous Cube': {'type': 'acid', 'damage': (2, 5), 'targets': 'all', 'break_chance': 0.2},
    'Slime Mold': {'type': 'acid', 'damage': (1, 3), 'targets': 'armor_only', 'break_chance': 0.1},
    'Black Pudding': {'type': 'acid', 'damage': (4, 8), 'targets': 'all', 'break_chance': 0.3},
    'Gray Ooze': {'type': 'acid', 'damage': (2, 6), 'targets': 'metal', 'break_chance': 0.25},
    'Ochre Jelly': {'type': 'acid', 'damage': (2, 4), 'targets': 'organic', 'break_chance': 0.15},
}

EVOLUTION_PREFIXES = ('Hardened ', 'Savage ', 'Dread ', 'Mythic ')

def get_base_monster_name(monster_name):
    """Strip evolution prefixes to get the base template name."""
    name = monster_name.strip()
    for prefix in EVOLUTION_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name

def is_metal_item(item):
    """Check if an item is made of metal and can rust"""
    if not isinstance(item, (Weapon, Armor)):
        return False
    name_lower = item.name.lower()
    if isinstance(item, Weapon):
        for metal in METAL_WEAPONS:
            if metal.lower() in name_lower:
                return True
    elif isinstance(item, Armor):
        for metal in METAL_ARMOR:
            if metal.lower() in name_lower:
                return True
    return False

def is_organic_item(item):
    """Check if an item is organic/burnable"""
    if not isinstance(item, (Weapon, Armor)):
        return False
    name_lower = item.name.lower()
    if isinstance(item, Weapon):
        for organic in ORGANIC_WEAPONS:
            if organic.lower() in name_lower:
                return True
    elif isinstance(item, Armor):
        for organic in ORGANIC_ARMOR:
            if organic.lower() in name_lower:
                return True
    return False

def apply_corrosion_effect(player_character, monster_name, is_player_attacking=True):
    """
    Apply corrosive/acid effects from various monsters.
    Called when player attacks or is attacked by corrosive monsters.
    Returns list of messages.
    """
    messages = []
    
    if monster_name not in CORROSIVE_MONSTERS:
        # Try base name (strip evolution prefixes)
        base_name = get_base_monster_name(monster_name)
        if base_name not in CORROSIVE_MONSTERS:
            return messages
        monster_name = base_name
    
    config = CORROSIVE_MONSTERS[monster_name]
    damage = random.randint(config['damage'][0], config['damage'][1])
    targets = config['targets']
    break_chance = config['break_chance']
    effect_type = config['type']
    
    # Determine effect description
    if effect_type == 'rust':
        verb_weapon = "corrodes"
        verb_armor = "corrodes"
        result = "rust"
    else:  # acid
        verb_weapon = "dissolves"
        verb_armor = "dissolves"
        result = "slime"
    
    def should_affect_item(item):
        if targets == 'all':
            return True
        elif targets == 'metal':
            return is_metal_item(item)
        elif targets == 'organic':
            return is_organic_item(item)
        elif targets == 'armor_only':
            return isinstance(item, Armor)
        return False
    
    def damage_item(item, is_weapon=True):
        if not item or item.is_broken:
            return
        if not should_affect_item(item):
            return
            
        old_dur = item.durability
        item.durability = max(0, item.durability - damage)
        actual_damage = old_dur - item.durability
        
        if actual_damage > 0:
            if is_player_attacking and is_weapon:
                messages.append(f"{COLOR_RED}Your {item.name} {verb_weapon} on contact! (-{actual_damage} durability){COLOR_RESET}")
            else:
                messages.append(f"{COLOR_RED}The {monster_name}'s touch {verb_armor} your {item.name}! (-{actual_damage} durability){COLOR_RESET}")
            
            if item.durability == 0:
                if random.random() < break_chance:
                    messages.append(f"{COLOR_RED}Your {item.name} crumbles to {result}!{COLOR_RESET}")
                    if item in player_character.inventory.items:
                        player_character.inventory.items.remove(item)
                    if is_weapon:
                        player_character.equipped_weapon = None
                    else:
                        player_character.equipped_armor = None
                else:
                    messages.append(f"{COLOR_YELLOW}Your {item.name} is badly damaged and needs repair!{COLOR_RESET}")
    
    if is_player_attacking:
        # Player attacks monster - weapon gets damaged
        if targets != 'armor_only':
            damage_item(player_character.equipped_weapon, is_weapon=True)
    else:
        # Monster attacks player - armor gets damaged (and sometimes weapon too for strong acid)
        damage_item(player_character.equipped_armor, is_weapon=False)
        # Strong acid monsters also damage weapons
        if targets == 'all' and monster_name in ['Gelatinous Cube', 'Black Pudding']:
            if random.random() < 0.3:  # 30% chance to also hit weapon
                damage_item(player_character.equipped_weapon, is_weapon=True)
    
    return messages

def apply_rust_effect(player_character, is_player_attacking=True):
    """
    Legacy function - redirects to new corrosion system for Rust Monster.
    """
    return apply_corrosion_effect(player_character, "Rust Monster", is_player_attacking)

def get_repair_cost(item):
    """Calculate the cost to repair an item at a vendor"""
    if not isinstance(item, (Weapon, Armor)):
        return 0
    
    # Cost based on how much durability is missing
    missing = item.max_durability - item.durability
    if missing <= 0:
        return 0
    
    # Base cost per durability point, scaled by item level and value
    cost_per_point = max(1, item.value // 50) + item.level
    
    return missing * cost_per_point

def repair_item(item, player_character):
    """
    Repair an item to full durability.
    Returns True if successful, False if not enough gold.
    """
    if not isinstance(item, (Weapon, Armor)):
        return False
    
    cost = get_repair_cost(item)
    if cost <= 0:
        add_log(f"{COLOR_YELLOW}{item.name} doesn't need repair.{COLOR_RESET}")
        return False
    
    if player_character.gold < cost:
        add_log(f"{COLOR_RED}Not enough gold! Repair costs {cost} gold.{COLOR_RESET}")
        return False
    
    player_character.gold -= cost
    old_dur = item.durability
    item.durability = item.max_durability
    add_log(f"{COLOR_GREEN}Repaired {item.name} ({old_dur} -> {item.max_durability}) for {cost} gold.{COLOR_RESET}")
    return True


# ============================================================================
# ITEM CLASSES
# ============================================================================

class Item:
    def __init__(self, name, description="", value=0, level=0):
        super().__init__()
        self.name = name
        self.description = description
        self.value = value # Added a value attribute for buying/selling
        self.level = level # Added a level attribute

    def __repr__(self):
        return f"Item(name='{self.name}', description='{self.description}', value={self.value}, level={self.level})"

    @property
    def calculated_value(self):
        """Returns the base value of the item. Can change this to increase value for upgraded gear"""
        return self.value

    def use(self, character, my_tower=None):
        add_log(f"Using {self.name}. (No specific effect defined for base item)")
        return False # Base item generally not consumed


GROWTH_SHARD_DURATION_BONUS = 2


def apply_growth_shard_bonus(base_duration):
    """Apply Growth Shard duration bonus if the shard is obtained."""
    if gs.shards_obtained.get('growth'):
        duration = base_duration + GROWTH_SHARD_DURATION_BONUS
        add_log(f"{COLOR_GREEN}[Growth Shard] Potion duration extended: {base_duration} \u2192 {duration} turns!{COLOR_RESET}")
        return duration
    return base_duration


class Potion(Item):
    """
    Verify your existing Potion class has these attributes:
    - name, description, value, level (from Item)
    - potion_type (healing, mana, buff, etc.)
    - effect_magnitude (how much it heals/buffs)
    - duration (for buffs, 0 for instant effects)
    - count (for stacking)
    """
    def __init__(self, name, description="", value=0, level=0,
                 potion_type='healing', effect_magnitude=0, duration=0, resistance_element=None, count=1):
        super().__init__(name, description, value, level)
        self.potion_type = potion_type
        self.effect_magnitude = effect_magnitude
        self.duration = duration
        self.resistance_element = resistance_element
        self.count = count  # For stacking

    def __repr__(self):
        return f"Potion(name='{self.name}', type='{self.potion_type}', effect={self.effect_magnitude}, duration={self.duration}, value={self.value}, level={self.level}, count={self.count})"

    def use(self, character, my_tower=None):
        """
        Use the potion. This should be in your existing Potion class.
        Add new potion types to this method.
        """

        # Auto-identify potion on use
        identify_item(self, silent=False)

        if self.potion_type == 'healing':
            old_health = character.health
            character.health = min(character.max_health, character.health + self.effect_magnitude)
            healed = character.health - old_health
            add_log(f"{COLOR_GREEN}{character.name} drinks {self.name} and recovers {healed} HP!{COLOR_RESET}")
            return True  # Consumed

        elif self.potion_type == 'mana':
            old_mana = character.mana
            character.mana = min(character.max_mana, character.mana + self.effect_magnitude)
            restored = character.mana - old_mana
            add_log(f"{COLOR_CYAN}{character.name} drinks {self.name} and recovers {restored} mana!{COLOR_RESET}")
            return True  # Consumed

        elif self.potion_type == 'strength':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            character.add_status_effect(
                effect_name='Strength Boost',
                duration=duration,
                effect_type='attack_boost',
                magnitude=self.effect_magnitude,
                description=f'Increased strength from {self.name}'
            )
            add_log(f"{COLOR_YELLOW}{character.name} drinks {self.name}! Attack increased by {self.effect_magnitude} for {duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'dexterity':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            character.add_status_effect(
                effect_name='Dexterity Boost',
                duration=duration,
                effect_type='dexterity_boost',
                magnitude=self.effect_magnitude,
                description=f'Increased dexterity from {self.name}'
            )
            add_log(f"{COLOR_YELLOW}{character.name} drinks {self.name}! Dexterity increased by {self.effect_magnitude} for {duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'intelligence':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            character.add_status_effect(
                effect_name='Intelligence Boost',
                duration=duration,
                effect_type='magic_boost',
                magnitude=self.effect_magnitude,
                description=f'Increased intelligence from {self.name}'
            )
            add_log(f"{COLOR_YELLOW}{character.name} drinks {self.name}! Intelligence increased by {self.effect_magnitude} for {duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'defense':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            character.add_status_effect(
                effect_name='Defense Boost',
                duration=duration,
                effect_type='defense_boost',
                magnitude=self.effect_magnitude,
                description=f'Increased defense from {self.name}'
            )
            add_log(f"{COLOR_YELLOW}{character.name} drinks {self.name}! Defense increased by {self.effect_magnitude} for {duration} turns!{COLOR_RESET}")
            return True

        # 
        # NEW POTION TYPES BELOW
        # 

        elif self.potion_type == 'invisibility':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}Your body fades from view...{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}{COLOR_RESET}")

            character.add_status_effect(
                effect_name='Invisibility',
                duration=duration,
                effect_type='invisibility',
                magnitude=0,
                description='Invisible - enemies cannot attack you'
            )
            add_log(f"{COLOR_GREEN}You are invisible for {duration} turns! Enemies will not attack.{COLOR_RESET}")
            return True

        elif self.potion_type == 'true_sight':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_CYAN}{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Your vision becomes supernaturally keen!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{COLOR_RESET}")

            # Reveal large area around player
            current_floor = my_tower.floors[character.z]
            revealed = 0
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    ny, nx = character.y + dy, character.x + dx
                    if 0 <= ny < current_floor.rows and 0 <= nx < current_floor.cols:
                        if not current_floor.grid[ny][nx].discovered:
                            current_floor.grid[ny][nx].discovered = True
                            revealed += 1

            # Grant status effect for seeing hidden things
            character.add_status_effect(
                effect_name='True Sight',
                duration=duration,
                effect_type='true_sight',
                magnitude=0,
                description='See all hidden properties'
            )

            add_log(f"{COLOR_GREEN}Revealed {revealed} rooms! True Sight active for {duration} turns.{COLOR_RESET}")
            return True

        elif self.potion_type == 'berserker':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_RED}{COLOR_RESET}")
            add_log(f"{COLOR_RED}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_RED}RAGE surges through your veins!{COLOR_RESET}")
            add_log(f"{COLOR_RED}{COLOR_RESET}")

            # Massive attack boost
            character.add_status_effect(
                effect_name='Berserker Rage',
                duration=duration,
                effect_type='attack_boost',
                magnitude=self.effect_magnitude,  # +30 attack
                description='Massive attack increase, reduced defense'
            )

            # But defense penalty
            character.add_status_effect(
                effect_name='Berserker Vulnerability',
                duration=duration,
                effect_type='defense_penalty',
                magnitude=-10,
                description='Reckless fighting reduces defense'
            )

            add_log(f"{COLOR_YELLOW}Attack +{self.effect_magnitude}, Defense -10 for {duration} turns!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}High risk, high reward!{COLOR_RESET}")
            return True

        elif self.potion_type == 'regeneration':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_GREEN}{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Warmth spreads through your body...{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}{COLOR_RESET}")

            character.add_status_effect(
                effect_name='Regeneration',
                duration=duration,
                effect_type='regeneration',
                magnitude=self.effect_magnitude,  # HP per turn
                description='Slowly heal over time'
            )
            add_log(f"{COLOR_GREEN}Regenerating {self.effect_magnitude} HP per turn for {duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'clarity':
            add_log(f"{COLOR_CYAN}{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}A wave of mental clarity washes over you!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{COLOR_RESET}")

            # Remove ALL negative status effects - FIX: Use list() to avoid modification during iteration
            effects_removed = []
            for effect_name in list(character.status_effects.keys()):  # FIX: Added list()
                effect = character.status_effects[effect_name]
                if effect.effect_type in ['confusion', 'slow', 'curse', 'weakness']:
                    character.remove_status_effect(effect_name)
                    effects_removed.append(effect_name)

            if effects_removed:
                add_log(f"{COLOR_GREEN}Removed: {', '.join(effects_removed)}!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_YELLOW}No negative effects to remove.{COLOR_RESET}")

            # Also restore some mana
            character.mana = min(character.max_mana, character.mana + 30)
            add_log(f"{COLOR_CYAN}Restored 30 mana!{COLOR_RESET}")
            return True
        
        # PERMANENT STAT INCREASES
        elif self.potion_type == 'permanent_strength':
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}You drink the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_RED}Power surges through your muscles!{COLOR_RESET}")
            character.strength += self.effect_magnitude
            character.base_attack += self.effect_magnitude
            add_log(f"{COLOR_GREEN}* PERMANENT: Strength +{self.effect_magnitude}! *{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}New Strength: {character.strength}{COLOR_RESET}")
            add_log("")
            return True
        
        elif self.potion_type == 'permanent_dexterity':
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}You drink the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Your reflexes sharpen to inhuman levels!{COLOR_RESET}")
            character.dexterity += self.effect_magnitude
            add_log(f"{COLOR_GREEN}* PERMANENT: Dexterity +{self.effect_magnitude}! *{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}New Dexterity: {character.dexterity}{COLOR_RESET}")
            add_log("")
            return True
        
        elif self.potion_type == 'permanent_intelligence':
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}You drink the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Arcane knowledge floods your mind!{COLOR_RESET}")
            character.intelligence += self.effect_magnitude
            character.base_max_mana_bonus += self.effect_magnitude * 5  # +10 mana per +2 INT
            character.mana = character.max_mana  # Fill mana
            add_log(f"{COLOR_GREEN}* PERMANENT: Intelligence +{self.effect_magnitude}! *{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Max Mana +{self.effect_magnitude * 5}!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}New Intelligence: {character.intelligence}{COLOR_RESET}")
            add_log("")
            return True
        
        elif self.potion_type == 'permanent_health':
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}You drink the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Vitality courses through your veins!{COLOR_RESET}")
            character.base_max_health_bonus += self.effect_magnitude
            character.health += self.effect_magnitude  # Also heal
            add_log(f"{COLOR_GREEN}* PERMANENT: Max HP +{self.effect_magnitude}! *{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}New Max HP: {character.max_health}{COLOR_RESET}")
            add_log("")
            return True
        
        elif self.potion_type == 'permanent_defense':
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}You drink the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_GREY}Your skin hardens like iron!{COLOR_RESET}")
            character.base_defense += self.effect_magnitude
            add_log(f"{COLOR_GREEN}* PERMANENT: Defense +{self.effect_magnitude}! *{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}New Defense: {character.base_defense}{COLOR_RESET}")
            add_log("")
            return True
        
        # ELEMENTAL RESISTANCE POTIONS (Permanent)
        elif self.potion_type.startswith('resistance_'):
            if self.potion_type == 'resistance_all':
                # Prismatic Elixir - grants ALL resistances
                elements = ['Fire', 'Ice', 'Lightning', 'Darkness', 'Light']
                add_log("")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_YELLOW}~~~ PRISMATIC ELIXIR ~~~{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}Rainbow energy floods through your body!{COLOR_RESET}")
                add_log("")
                
                newly_gained = []
                already_had = []
                
                for element in elements:
                    if element not in character.elemental_resistance:
                        character.elemental_resistance.append(element)
                        newly_gained.append(element)
                    else:
                        already_had.append(element)
                
                if newly_gained:
                    add_log(f"{COLOR_GREEN}* GAINED RESISTANCE TO: {', '.join(newly_gained)}! *{COLOR_RESET}")
                
                if already_had:
                    add_log(f"{COLOR_GREY}(Already had: {', '.join(already_had)}){COLOR_RESET}")
                
                add_log("")
                add_log(f"{COLOR_PURPLE}~~~ You are now resistant to ALL elements! ~~~{COLOR_RESET}")
                add_log("")
                return True
            else:
                # Single element resistance
                element = self.resistance_element
                add_log("")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                add_log(f"{COLOR_YELLOW}You drink the {self.name}!{COLOR_RESET}")
                add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
                
                if element not in character.elemental_resistance:
                    character.elemental_resistance.append(element)
                    add_log(f"{COLOR_GREEN}* PERMANENT: {element} Resistance gained! *{COLOR_RESET}")
                    add_log(f"{COLOR_CYAN}You now resist {element} damage!{COLOR_RESET}")
                else:
                    add_log(f"{COLOR_YELLOW}You already have {element} resistance.{COLOR_RESET}")
                    add_log(f"{COLOR_GREY}The potion has no effect.{COLOR_RESET}")
                add_log("")
                return True

        elif self.potion_type == 'frost_armor':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_CYAN}{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Frost crystals form on your skin!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{COLOR_RESET}")

            character.add_status_effect(
                effect_name='Frost Armor',
                duration=self.duration,
                effect_type='thorns',
                magnitude=self.effect_magnitude,  # Damage reflected
                description='Attackers take ice damage'
            )
            add_log(f"{COLOR_GREEN}Frost Armor active! Attackers take {self.effect_magnitude} ice damage for {self.duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'giant_strength':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_YELLOW}{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}Your muscles swell with titanic power!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}{COLOR_RESET}")

            # Temporary STR increase (not just attack)
            old_str = character.strength
            character.strength += self.effect_magnitude

            # Store original strength for removal
            character.add_status_effect(
                effect_name='Giant Strength',
                duration=self.duration,
                effect_type='stat_boost_str',
                magnitude=self.effect_magnitude,
                description='Massive temporary strength increase'
            )
            add_log(f"{COLOR_GREEN}Strength increased from {old_str} to {character.strength} for {self.duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'vampirism':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_RED}{COLOR_RESET}")
            add_log(f"{COLOR_RED}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_RED}Dark energy courses through you...{COLOR_RESET}")
            add_log(f"{COLOR_RED}{COLOR_RESET}")

            character.add_status_effect(
                effect_name='Vampiric',
                duration=self.duration,
                effect_type='lifesteal',
                magnitude=self.effect_magnitude,  # % of damage as healing
                description='Heal when dealing damage'
            )
            add_log(f"{COLOR_GREEN}Lifesteal active! Heal {self.effect_magnitude}% of damage dealt for {self.duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'fortune':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_YELLOW}{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}Luck smiles upon you!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}{COLOR_RESET}")

            character.add_status_effect(
                effect_name='Fortune',
                duration=self.duration,
                effect_type='luck_boost',
                magnitude=self.effect_magnitude,  # % better loot
                description='Increased gold and item drops'
            )
            add_log(f"{COLOR_GREEN}Luck increased! +{self.effect_magnitude}% better loot for {self.duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'experience':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}Ancient knowledge flows into your mind!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}{COLOR_RESET}")

            character.add_status_effect(
                effect_name='Experience Boost',
                duration=self.duration,
                effect_type='xp_boost',
                magnitude=self.effect_magnitude,  # % bonus XP
                description='Increased XP from all sources'
            )
            add_log(f"{COLOR_GREEN}XP gain increased by {self.effect_magnitude}% for {self.duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'haste':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_CYAN}{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Time seems to slow around you!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{COLOR_RESET}")

            character.add_status_effect(
                effect_name='Haste',
                duration=self.duration,
                effect_type='haste',
                magnitude=2,  # 2 actions per turn
                description='Act twice per turn'
            )
            add_log(f"{COLOR_GREEN}Haste active! You can act twice per turn for {self.duration} turns!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}(Attack twice or move + attack){COLOR_RESET}")
            return True

        elif self.potion_type == 'stone_skin':
            # Apply Growth Shard bonus
            duration = apply_growth_shard_bonus(self.duration)
            
            add_log(f"{COLOR_GREY}{COLOR_RESET}")
            add_log(f"{COLOR_GREY}{character.name} drinks {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_GREY}Your skin hardens to stone!{COLOR_RESET}")
            add_log(f"{COLOR_GREY}{COLOR_RESET}")

            character.add_status_effect(
                effect_name='Stone Skin',
                duration=self.duration,
                effect_type='damage_reduction',
                magnitude=self.effect_magnitude,  # Flat damage reduction
                description='Reduce all incoming damage'
            )
            add_log(f"{COLOR_GREEN}Stone Skin active! Reduce incoming damage by {self.effect_magnitude} for {self.duration} turns!{COLOR_RESET}")
            return True

        elif self.potion_type == 'resistance':
            element = self.resistance_element
            reduction_pct = self.effect_magnitude

            # Visual effects based on element
            element_colors = {
                'Fire': COLOR_RED,
                'Ice': COLOR_CYAN,
                'Lightning': COLOR_YELLOW,
                'Water': COLOR_CYAN,
                'Earth': COLOR_GREY,
                'Wind': COLOR_GREY,
                'Holy': COLOR_YELLOW,
                'Darkness': COLOR_PURPLE,
                'Poison': COLOR_GREEN,
                'Physical': COLOR_GREY,
                'Psionic': COLOR_PURPLE,
                'Multi': COLOR_YELLOW,
                'Multi-Natural': COLOR_GREEN,
                'Multi-Arcane': COLOR_PURPLE,
                'Universal': COLOR_PURPLE
            }

            color = element_colors.get(element, COLOR_CYAN)

            add_log(f"{color}{COLOR_RESET}")
            add_log(f"{color}{character.name} drinks {self.name}!{COLOR_RESET}")

            if element == 'Multi':
                add_log(f"{color}Fire, ice, and lightning shields surround you!{COLOR_RESET}")
            elif element == 'Multi-Natural':
                add_log(f"{color}Earth, water, and wind shields surround you!{COLOR_RESET}")
            elif element == 'Multi-Arcane':
                add_log(f"{color}Holy, shadow, and psionic shields surround you!{COLOR_RESET}")
            elif element == 'Universal':
                add_log(f"{color}A prismatic barrier envelops your body!{COLOR_RESET}")
            else:
                add_log(f"{color}A shimmering {element.lower()} shield surrounds you!{COLOR_RESET}")

            add_log(f"{color}{COLOR_RESET}")

            # Add status effect
            effect_name = f'{element} Resistance'

            character.add_status_effect(
                effect_name=effect_name,
                duration=self.duration,
                effect_type='elemental_resistance',
                magnitude=reduction_pct,
                description=f'Reduce {element} damage by {reduction_pct}%',
                resistance_element=element
            )

            if 'Multi' in element:
                add_log(f"{COLOR_GREEN}Resisting multiple elements by {reduction_pct}% for {self.duration} turns!{COLOR_RESET}")
            elif element == 'Universal':
                add_log(f"{COLOR_GREEN}Resisting ALL damage by {reduction_pct}% for {self.duration} turns!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_GREEN}Resisting {element} by {reduction_pct}% for {self.duration} turns!{COLOR_RESET}")

            return True  # Consumed

        elif self.potion_type == 'growth_mushroom':
            from . import game_state as gs
            add_log("")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}{character.name} eats the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}Warmth floods your body as you begin to GROW!{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Your arms stretch, your legs lengthen...{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}The bugs around you shrink back to their normal size!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}Zot's shrinking spell has been broken!{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}You can now use the stairs to leave this floor!{COLOR_RESET}")
            add_log("")

            # Remove shrinking effect
            gs.player_is_shrunk = False
            character.remove_status_effect('Shrinking')

            return True  # Consumed

        else:
            add_log(f"{character.name} drinks {self.name}, but nothing happens...")
            return True

class Ingredient(Item):
    """Crafting ingredient for potion making"""
    def __init__(self, name, description="", value=0, level=0, ingredient_type='herb', count=1):
        super().__init__(name, description, value, level)
        self.ingredient_type = ingredient_type
        self.count = count
    
    def __repr__(self):
        return f"Ingredient(name='{self.name}', type='{self.ingredient_type}', value={self.value}, count={self.count})"


class Trophy(Item):
    """
    Monster body part collected for the Taxidermist room.
    Stacks by count like Ingredient. Not usable, only tradeable at the taxidermist.
    Can be sold at vendors for modest gold if the player doesn't want to collect.
    """
    def __init__(self, name, description="", value=0, level=0, monster_source="", count=1):
        super().__init__(name, description, value, level)
        self.monster_source = monster_source  # Name of monster it came from
        self.count = count

    def __repr__(self):
        return f"Trophy(name='{self.name}', source='{self.monster_source}', count={self.count}, value={self.value})"

class Rune(Item):
    """Quest item - Rune that unlocks shard vaults"""
    def __init__(self, name, rune_type, description="", value=0, level=0):
        super().__init__(name, description, value, level)
        self.rune_type = rune_type  # 'battle', 'treasure', etc.
    
    def __repr__(self):
        return f"Rune(name='{self.name}', type='{self.rune_type}')"

class Shard(Item):
    """Quest item - Shard of Power with passive bonus"""
    def __init__(self, name, shard_type, passive_bonus, description="", value=0, level=0):
        super().__init__(name, description, value, level)
        self.shard_type = shard_type  # 'battle', 'treasure', etc.
        self.passive_bonus = passive_bonus  # Dictionary with bonus details
        # Example: {'stat': 'attack', 'amount': 3} or {'effect': 'gold_boost', 'percent': 10}
    
    def __repr__(self):
        return f"Shard(name='{self.name}', type='{self.shard_type}', bonus={self.passive_bonus})"

# Potion Recipes: {potion_name: {'ingredients': [(ingredient_name, count)], 'result': Potion object}}
POTION_RECIPES = {
    # ============================================================
    # TIER 1: BASIC POTIONS (Common ingredients)
    # ============================================================
    
    'Healing Potion': {
        'ingredients': [('Moonpetal', 2), ('Healing Moss', 1)],
        'tier': 1,
        'result': lambda: Potion(name="Healing Potion", potion_type='healing', effect_magnitude=50, value=50, level=1, description="Restores 50 HP")
    },
    'Mana Potion': {
        'ingredients': [('Starbloom', 2), ('Healing Moss', 1)],
        'tier': 1,
        'result': lambda: Potion(name="Mana Potion", potion_type='mana', effect_magnitude=40, value=50, level=1, description="Restores 40 Mana")
    },
    'Antidote': {
        'ingredients': [('Healing Moss', 3), ('Moonpetal', 1)],
        'tier': 1,
        'result': lambda: Potion(name="Antidote", potion_type='cure_all', effect_magnitude=0, value=100, level=1, description="Cures all negative status effects")
    },
    
    # ============================================================
    # TIER 2: INTERMEDIATE POTIONS (Common + Uncommon)
    # ============================================================
    
    'Greater Healing Potion': {
        'ingredients': [('Moonpetal', 3), ('Crystal Dew', 2)],
        'tier': 2,
        'result': lambda: Potion(name="Greater Healing Potion", potion_type='healing', effect_magnitude=100, value=100, level=2, description="Restores 100 HP")
    },
    'Greater Mana Potion': {
        'ingredients': [('Starbloom', 3), ('Essence Vial', 2)],
        'tier': 2,
        'result': lambda: Potion(name="Greater Mana Potion", potion_type='mana', effect_magnitude=80, value=100, level=2, description="Restores 80 Mana")
    },
    'Strength Elixir': {
        'ingredients': [('Fire Root', 3), ('Shadow Leaf', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Strength Elixir", potion_type='strength', effect_magnitude=5, duration=5, value=75, level=2, description="+5 Attack for 5 turns")
    },
    'Dexterity Tonic': {
        'ingredients': [('Shadow Leaf', 3), ('Starbloom', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Dexterity Tonic", potion_type='dexterity', effect_magnitude=5, duration=5, value=75, level=2, description="+5 Dexterity for 5 turns")
    },
    'Intelligence Brew': {
        'ingredients': [('Starbloom', 3), ('Crystal Dew', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Intelligence Brew", potion_type='intelligence', effect_magnitude=5, duration=5, value=75, level=2, description="+5 Intelligence for 5 turns")
    },
    'Defense Brew': {
        'ingredients': [('Healing Moss', 3), ('Shadow Leaf', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Defense Brew", potion_type='defense', effect_magnitude=5, duration=5, value=75, level=2, description="+5 Defense for 5 turns")
    },
    'Regeneration Potion': {
        'ingredients': [('Moonpetal', 2), ('Healing Moss', 2), ('Crystal Dew', 1)],
        'tier': 2,
        'result': lambda: Potion(name="Regeneration Potion", potion_type='regeneration', effect_magnitude=10, duration=5, value=80, level=2, description="Restore 10 HP per turn for 5 turns")
    },
    
    # ============================================================
    # TIER 3: ADVANCED POTIONS (Uncommon + Rare)
    # ============================================================
    
    'Berserker Rage': {
        'ingredients': [('Fire Root', 3), ('Dragon Scale', 1), ('Shadow Leaf', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Berserker Rage", potion_type='berserker', effect_magnitude=100, duration=3, value=150, level=3, description="Double attack, -50% defense for 3 turns")
    },
    'Giant\'s Might': {
        'ingredients': [('Dragon Scale', 2), ('Iron Bark', 1), ('Fire Root', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Giant's Might", potion_type='giant_strength', effect_magnitude=10, duration=4, value=150, level=3, description="+10 Strength for 4 turns")
    },
    'Haste Potion': {
        'ingredients': [('Quicksilver Drop', 2), ('Shadow Leaf', 2), ('Essence Vial', 1)],
        'tier': 3,
        'result': lambda: Potion(name="Haste Potion", potion_type='haste', effect_magnitude=1, duration=3, value=150, level=3, description="Extra actions for 3 turns")
    },
    'Stone Skin': {
        'ingredients': [('Iron Bark', 2), ('Stone Flower', 2), ('Healing Moss', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Stone Skin", potion_type='stone_skin', effect_magnitude=50, duration=5, value=150, level=3, description="50% damage reduction for 5 turns")
    },
    'Invisibility Potion': {
        'ingredients': [('Shadow Leaf', 4), ('Essence Vial', 2), ('Quicksilver Drop', 1)],
        'tier': 3,
        'result': lambda: Potion(name="Invisibility Potion", potion_type='invisibility', effect_magnitude=0, duration=3, value=175, level=3, description="Enemies cannot attack you for 3 turns")
    },
    'True Sight': {
        'ingredients': [('Wisdom Moss', 2), ('Starbloom', 3), ('Crystal Dew', 2)],
        'tier': 3,
        'result': lambda: Potion(name="True Sight", potion_type='true_sight', effect_magnitude=0, duration=5, value=150, level=3, description="Reveal hidden enemies and secrets for 5 turns")
    },
    'Fortune Brew': {
        'ingredients': [('Crystal Dew', 3), ('Essence Vial', 2), ('Moonpetal', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Fortune Brew", potion_type='fortune', effect_magnitude=50, duration=5, value=150, level=3, description="+50% gold drops for 5 turns")
    },
    'Experience Elixir': {
        'ingredients': [('Wisdom Moss', 2), ('Essence Vial', 2), ('Starbloom', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Experience Elixir", potion_type='experience', effect_magnitude=50, duration=5, value=150, level=3, description="+50% XP gain for 5 turns")
    },
    'Vampiric Elixir': {
        'ingredients': [('Dragon Scale', 1), ('Shadow Leaf', 3), ('Fire Root', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Vampiric Elixir", potion_type='vampirism', effect_magnitude=30, duration=5, value=175, level=3, description="Lifesteal 30% of damage dealt for 5 turns")
    },
    'Frost Armor': {
        'ingredients': [('Crystal Dew', 3), ('Essence Vial', 2), ('Shadow Leaf', 1)],
        'tier': 3,
        'result': lambda: Potion(name="Frost Armor", potion_type='frost_armor', effect_magnitude=15, duration=5, value=150, level=3, description="Reflect 15 ice damage to attackers for 5 turns")
    },
    'Clarity Potion': {
        'ingredients': [('Wisdom Moss', 2), ('Starbloom', 2), ('Moonpetal', 2)],
        'tier': 3,
        'result': lambda: Potion(name="Clarity Potion", potion_type='clarity', effect_magnitude=0, duration=0, value=125, level=3, description="Remove confusion, slow, curse, weakness. Restore 30 mana.")
    },
    
    # ============================================================
    # TIER 4: LEGENDARY POTIONS - PERMANENT STAT INCREASES
    # ============================================================
    
    'Elixir of Might': {
        'ingredients': [('Dragon Scale', 3), ('Iron Bark', 2), ('Fire Root', 4)],
        'tier': 4,
        'result': lambda: Potion(name="Elixir of Might", potion_type='permanent_strength', effect_magnitude=2, value=250, level=4, description="~~~ PERMANENT: +2 Strength forever")
    },
    'Potion of Swiftness': {
        'ingredients': [('Quicksilver Drop', 3), ('Shadow Leaf', 4), ('Essence Vial', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Potion of Swiftness", potion_type='permanent_dexterity', effect_magnitude=2, value=250, level=4, description="~~~ PERMANENT: +2 Dexterity forever")
    },
    'Draught of Brilliance': {
        'ingredients': [('Wisdom Moss', 3), ('Starbloom', 4), ('Crystal Dew', 3)],
        'tier': 4,
        'result': lambda: Potion(name="Draught of Brilliance", potion_type='permanent_intelligence', effect_magnitude=2, value=250, level=4, description="~~~ PERMANENT: +2 Intelligence forever")
    },
    'Potion of Fortitude': {
        'ingredients': [('Dragon Scale', 2), ('Moonpetal', 5), ('Crystal Dew', 3)],
        'tier': 4,
        'result': lambda: Potion(name="Potion of Fortitude", potion_type='permanent_health', effect_magnitude=20, value=300, level=4, description="~~~ PERMANENT: +20 Max HP forever")
    },
    'Essence of Resilience': {
        'ingredients': [('Iron Bark', 3), ('Stone Flower', 3), ('Dragon Scale', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Essence of Resilience", potion_type='permanent_defense', effect_magnitude=2, value=250, level=4, description="~~~ PERMANENT: +2 Defense forever")
    },
    
    # ============================================================
    # TIER 4: LEGENDARY POTIONS - PERMANENT ELEMENTAL RESISTANCE
    # ============================================================
    
    'Fireward Elixir': {
        'ingredients': [('Fire Root', 5), ('Dragon Scale', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Fireward Elixir", potion_type='resistance_fire', resistance_element='Fire', value=200, level=4, description="~~~ PERMANENT: Fire Resistance forever")
    },
    'Frostward Tonic': {
        'ingredients': [('Crystal Dew', 5), ('Essence Vial', 3)],
        'tier': 4,
        'result': lambda: Potion(name="Frostward Tonic", potion_type='resistance_ice', resistance_element='Ice', value=200, level=4, description="~~~ PERMANENT: Ice Resistance forever")
    },
    'Stormward Brew': {
        'ingredients': [('Quicksilver Drop', 4), ('Essence Vial', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Stormward Brew", potion_type='resistance_lightning', resistance_element='Lightning', value=200, level=4, description="~~~ PERMANENT: Lightning Resistance forever")
    },
    'Shadowward Potion': {
        'ingredients': [('Shadow Leaf', 5), ('Wisdom Moss', 2)],
        'tier': 4,
        'result': lambda: Potion(name="Shadowward Potion", potion_type='resistance_darkness', resistance_element='Darkness', value=200, level=4, description="~~~ PERMANENT: Darkness Resistance forever")
    },
    'Lightward Essence': {
        'ingredients': [('Starbloom', 5), ('Moonpetal', 4)],
        'tier': 4,
        'result': lambda: Potion(name="Lightward Essence", potion_type='resistance_light', resistance_element='Light', value=200, level=4, description="~~~ PERMANENT: Light Resistance forever")
    },
    
    # ============================================================
    # TIER 5: ULTIMATE POTION - ALL ELEMENTAL RESISTANCE
    # ============================================================
    
    'Prismatic Elixir': {
        'ingredients': [
            ('Dragon Scale', 5),
            ('Fire Root', 5),
            ('Crystal Dew', 5),
            ('Quicksilver Drop', 5),
            ('Shadow Leaf', 5),
            ('Starbloom', 5),
            ('Wisdom Moss', 3),
            ('Essence Vial', 3)
        ],
        'tier': 5,
        'result': lambda: Potion(name="Prismatic Elixir", potion_type='resistance_all', value=1000, level=5, description="~~~ PERMANENT: ALL Elemental Resistances forever! ~~~")
    },
}

# Available garden ingredients with spawn chances
GARDEN_INGREDIENTS = [
    # Common (60% chance)
    ('Moonpetal', 'A silver flower that glows faintly in darkness', 5, 1, 0.15),
    ('Starbloom', 'A blue flower dotted with tiny glowing specks', 8, 1, 0.15),
    ('Healing Moss', 'Soft green moss with regenerative properties', 5, 1, 0.15),
    ('Fire Root', 'A red root that is warm to the touch', 7, 1, 0.15),
    # Uncommon (30% chance)
    ('Shadow Leaf', 'A dark leaf that seems to absorb light', 10, 2, 0.10),
    ('Crystal Dew', 'Crystallized morning dew with magical properties', 12, 2, 0.10),
    ('Essence Vial', 'A small vial of concentrated magical essence', 15, 2, 0.10),
    # Rare (10% chance)
    ('Dragon Scale', 'A shimmering scale from a mighty dragon', 25, 3, 0.03),
    ('Iron Bark', 'Bark from an ancient ironwood tree', 20, 3, 0.02),
    ('Wisdom Moss', 'Rare moss said to enhance mental clarity', 20, 3, 0.02),
    ('Stone Flower', 'A flower as hard as granite', 18, 3, 0.02),
    ('Quicksilver Drop', 'A drop of liquid mercury-like substance', 22, 3, 0.01),
    # Spicy peppers — dwarves find these at double the base rate (see garden spawn code)
    ('Fire Pepper', 'A small red pepper that hums with heat. Dwarves seem drawn to them.', 12, 1, 0.06),
    ('Ghost Pepper', 'An ashen, wrinkled pepper so hot it shimmers. Deeply prized for cured meats.', 35, 3, 0.02),
]

# Dictionary for easy lookup
GARDEN_INGREDIENTS_DICT = {
    name: {'description': desc, 'value': value, 'level': level, 'chance': chance}
    for name, desc, value, level, chance in GARDEN_INGREDIENTS
}

class Weapon(Item):
    # Base durability for weapons by level
    BASE_DURABILITY = {0: 40, 1: 60, 2: 84, 3: 112, 4: 144, 5: 180, 6: 220, 7: 264, 8: 312, 9: 364, 10: 420}
    UPGRADE_DURABILITY_BONUS = 20  # Each upgrade adds 20 durability
    
    def __init__(self, name, description="", attack_bonus=0, value=0, level=0, upgrade_level=0, elemental_strength=["None"], upgrade_limit=True, is_cursed=False, durability=None, max_durability=None):
        super().__init__(name, description, value, level)
        self._base_attack_bonus = attack_bonus
        self.upgrade_limit = upgrade_limit
        self.upgrade_level = upgrade_level
        self.elemental_strength = elemental_strength
        self.is_cursed = is_cursed  # Cursed weapons cannot be upgraded
        
        # Durability system - higher level/upgrade = more durable
        base_dur = self.BASE_DURABILITY.get(min(level, 10), 420)
        upgrade_bonus = upgrade_level * self.UPGRADE_DURABILITY_BONUS
        calculated_max = base_dur + upgrade_bonus
        
        self.max_durability = max_durability if max_durability is not None else calculated_max
        self.durability = durability if durability is not None else self.max_durability

    @property
    def attack_bonus(self):
        return self._base_attack_bonus + self.upgrade_level

    @property
    def is_broken(self):
        return self.durability <= 0
    
    @property
    def durability_percent(self):
        if self.max_durability <= 0:
            return 0
        return int((self.durability / self.max_durability) * 100)
    
    def get_durability_status(self):
        """Get a color-coded durability status string"""
        pct = self.durability_percent
        if pct > 75:
            return f"<span style='color: #4CAF50;'>{self.durability}/{self.max_durability}</span>"
        elif pct > 50:
            return f"<span style='color: #8BC34A;'>{self.durability}/{self.max_durability}</span>"
        elif pct > 25:
            return f"<span style='color: #FFC107;'>{self.durability}/{self.max_durability}</span>"
        elif pct > 0:
            return f"<span style='color: #FF5722;'>{self.durability}/{self.max_durability}</span>"
        else:
            return f"<span style='color: #F44336;'>BROKEN</span>"

    @property
    def calculated_value(self):
        strengths=0
        for i in self.elemental_strength:
          if i != "None":
            strengths+=1
        """Returns the base value of the item. Can change this to increase value for upgraded gear"""
        return self.value*(self.upgrade_level+1) + int((self.value/2)*strengths)
    
    def get_display_name(self):
        """Get the full display name with tier prefix and elemental suffix."""
        # Tier prefixes - expanded to +20
        tier_prefixes = {
            0: "", 1: "Honed", 2: "Keen", 3: "Tempered", 4: "Reinforced",
            5: "Superior", 6: "Masterwork", 7: "Epic", 8: "Legendary",
            9: "Mythic", 10: "Divine", 11: "Celestial", 12: "Ethereal",
            13: "Transcendent", 14: "Exalted", 15: "Godslayer", 16: "Worldender",
            17: "Cosmic", 18: "Primordial", 19: "Infinite", 20: "Perfect"
        }
        # Elemental suffixes
        elem_suffixes = {
            "Fire": "of Flames", "Ice": "of Frost", "Lightning": "of Thunder",
            "Poison": "of Venom", "Dark": "of Shadow", "Light": "of Radiance",
            "Physical": "of Force", "Arcane": "of the Arcane", "None": ""
        }
        # Multi-element combos
        multi_elem = {
            frozenset(["Fire", "Ice"]): "of Extremes",
            frozenset(["Fire", "Lightning"]): "of the Storm",
            frozenset(["Light", "Dark"]): "of Twilight",
            frozenset(["Fire", "Dark"]): "of Hellfire",
            frozenset(["Ice", "Light"]): "of the Moon",
            frozenset(["Lightning", "Dark"]): "of the Tempest",
            frozenset(["Fire", "Light"]): "of the Sun",
            frozenset(["Ice", "Dark"]): "of the Void",
            frozenset(["Poison", "Dark"]): "of Corruption",
            frozenset(["Lightning", "Light"]): "of Judgment",
        }
        
        prefix = tier_prefixes.get(min(self.upgrade_level, 20), "Ascended")
        elements = [e for e in self.elemental_strength if e != "None"]
        suffix = ""
        
        if len(elements) >= 2:
            suffix = multi_elem.get(frozenset(elements[:2]), elem_suffixes.get(elements[0], ""))
        elif len(elements) == 1:
            suffix = elem_suffixes.get(elements[0], "")
        
        parts = []
        if prefix:
            parts.append(prefix)
        parts.append(self.name)
        full_name = " ".join(parts)
        if suffix:
            full_name += " " + suffix
        
        # Add upgrade indicator
        if self.upgrade_level > 0:
            full_name += f" (+{self.upgrade_level})"
        
        if self.is_cursed:
            full_name += " [CURSED]"
        
        return full_name

    def __repr__(self):
        cursed_str = ", CURSED" if self.is_cursed else ""
        return f"Weapon(name='{self.name}', attack_bonus={self.attack_bonus}, value={self.value}, level={self.level}, upgrade_level={self.upgrade_level}{cursed_str})"

class Armor(Item):
    # Base durability for armor by level
    BASE_DURABILITY = {0: 50, 1: 76, 2: 106, 3: 140, 4: 180, 5: 224, 6: 272, 7: 324, 8: 380, 9: 440, 10: 504}
    UPGRADE_DURABILITY_BONUS = 24  # Each upgrade adds 24 durability (armor is tougher)
    
    def __init__(self, name, description="", defense_bonus=0, value=0, level=0, upgrade_level=0, elemental_strength=["None"], upgrade_limit=True, is_cursed=False, durability=None, max_durability=None):
        super().__init__(name, description, value, level)
        self._base_defense_bonus = defense_bonus
        self.upgrade_level = upgrade_level
        self.upgrade_limit = upgrade_limit
        self.elemental_strength = elemental_strength
        self.is_cursed = is_cursed  # Cursed armor cannot be upgraded
        
        # Durability system - higher level/upgrade = more durable
        base_dur = self.BASE_DURABILITY.get(min(level, 10), 504)
        upgrade_bonus = upgrade_level * self.UPGRADE_DURABILITY_BONUS
        calculated_max = base_dur + upgrade_bonus
        
        self.max_durability = max_durability if max_durability is not None else calculated_max
        self.durability = durability if durability is not None else self.max_durability

    @property
    def defense_bonus(self):
        return self._base_defense_bonus + self.upgrade_level

    @property
    def is_broken(self):
        return self.durability <= 0
    
    @property
    def durability_percent(self):
        if self.max_durability <= 0:
            return 0
        return int((self.durability / self.max_durability) * 100)
    
    def get_durability_status(self):
        """Get a color-coded durability status string"""
        pct = self.durability_percent
        if pct > 75:
            return f"<span style='color: #4CAF50;'>{self.durability}/{self.max_durability}</span>"
        elif pct > 50:
            return f"<span style='color: #8BC34A;'>{self.durability}/{self.max_durability}</span>"
        elif pct > 25:
            return f"<span style='color: #FFC107;'>{self.durability}/{self.max_durability}</span>"
        elif pct > 0:
            return f"<span style='color: #FF5722;'>{self.durability}/{self.max_durability}</span>"
        else:
            return f"<span style='color: #F44336;'>BROKEN</span>"

    @property
    def calculated_value(self):
        strengths=0
        for i in self.elemental_strength:
          if i != "None":
            strengths+=1
        """Returns the base value of the item. Can change this to increase value for upgraded gear"""
        return self.value*(self.upgrade_level+1) + int((self.value/2)*strengths)
    
    def get_display_name(self):
        """Get the full display name with tier prefix and elemental suffix."""
        # Tier prefixes - expanded to +20
        tier_prefixes = {
            0: "", 1: "Sturdy", 2: "Hardened", 3: "Reinforced", 4: "Fortified",
            5: "Superior", 6: "Masterwork", 7: "Epic", 8: "Legendary",
            9: "Mythic", 10: "Divine", 11: "Celestial", 12: "Ethereal",
            13: "Transcendent", 14: "Exalted", 15: "Godforged", 16: "Worldguard",
            17: "Cosmic", 18: "Primordial", 19: "Infinite", 20: "Perfect"
        }
        # Elemental suffixes (resistance)
        elem_suffixes = {
            "Fire": "of Flame Ward", "Ice": "of Frost Ward", "Lightning": "of Storm Ward",
            "Poison": "of Venom Ward", "Dark": "of Shadow Ward", "Light": "of Light Ward",
            "Physical": "of Fortitude", "Arcane": "of Spell Guard", "None": ""
        }
        # Multi-element combos
        multi_elem = {
            frozenset(["Fire", "Ice"]): "of Elemental Ward",
            frozenset(["Fire", "Lightning"]): "of the Tempest",
            frozenset(["Light", "Dark"]): "of Balance",
            frozenset(["Fire", "Dark"]): "of the Inferno",
            frozenset(["Ice", "Light"]): "of the Aurora",
            frozenset(["Lightning", "Dark"]): "of the Maelstrom",
            frozenset(["Fire", "Light"]): "of the Phoenix",
            frozenset(["Ice", "Dark"]): "of the Abyss",
            frozenset(["Poison", "Dark"]): "of Corruption Ward",
            frozenset(["Lightning", "Light"]): "of Divine Protection",
        }
        
        prefix = tier_prefixes.get(min(self.upgrade_level, 20), "Ascended")
        elements = [e for e in self.elemental_strength if e != "None"]
        suffix = ""
        
        if len(elements) >= 2:
            suffix = multi_elem.get(frozenset(elements[:2]), elem_suffixes.get(elements[0], ""))
        elif len(elements) == 1:
            suffix = elem_suffixes.get(elements[0], "")
        
        parts = []
        if prefix:
            parts.append(prefix)
        parts.append(self.name)
        full_name = " ".join(parts)
        if suffix:
            full_name += " " + suffix
        
        # Add upgrade indicator
        if self.upgrade_level > 0:
            full_name += f" (+{self.upgrade_level})"
        
        if self.is_cursed:
            full_name += " [CURSED]"
        
        return full_name

    def __repr__(self):
        cursed_str = ", CURSED" if self.is_cursed else ""
        return f"Armor(name='{self.name}', defense_bonus={self.defense_bonus}, value={self.value}, level={self.level}, upgrade_level={self.upgrade_level}{cursed_str})"

class Scroll(Item):
    def __init__(self, name, description="", effect_description="", value=0, level=0,
                scroll_type='generic', spell_to_cast=None, spell_power_multiplier=1.5, count=1):
        super().__init__(name, description, value, level)
        self.effect_description = effect_description
        self.scroll_type = scroll_type # New attribute for scroll type
        self.spell_to_cast = spell_to_cast  # Store the spell this scroll casts
        self.spell_power_multiplier = spell_power_multiplier
        self.count = count  # For stacking

    def __repr__(self):
        return f"Scroll(name='{self.name}', effect='{self.effect_description}', type='{self.scroll_type}', value={self.value}, level={self.level}, count={self.count})"

    def use(self, character, my_tower=None):
        """
        Enhanced scroll use method with spell-casting and new scroll types.

        Replace the existing Scroll.use() method with this function.
        """
        from .dungeon import is_wall_at_coordinate
        from .vendor import reveal_adjacent_walls
        from .game_systems import _trigger_room_interaction

        # Auto-identify scroll on use
        identify_item(self, silent=False)

        if self.scroll_type == 'upgrade':
            add_log(f"{character.name} reads the {self.name}. You feel its magic seeking an item to enhance...")

            upgradable_items = []
            for item in character.inventory.items:
                if isinstance(item, (Weapon, Armor)):
                    # Skip cursed items - they cannot be upgraded
                    if getattr(item, 'is_cursed', False):
                        continue
                    # Skip unidentified items - must identify before upgrading
                    if not is_item_identified(item):
                        continue
                    upgradable_items.append(item)

            if not upgradable_items:
                add_log("You have no weapons or armor that can be upgraded.")
                add_log(f"{COLOR_GREY}(Cursed items cannot be upgraded. Unidentified items must be identified first.){COLOR_RESET}")
                return False

            add_log("\nSelect an item to upgrade (or 'c' to cancel):")
            for i, item in enumerate(upgradable_items):
                if isinstance(item, Weapon):
                    add_log(f"  {i + 1}. {item.name} (Attack: {item.attack_bonus}, +{item.upgrade_level} Upgrade Level)")
                elif isinstance(item, Armor):
                    add_log(f"  {i + 1}. {item.name} (Defense: {item.defense_bonus}, +{item.upgrade_level} Upgrade Level)")

            gs.prompt_cntl = 'upgrade_scroll_mode'
            gs.active_scroll_item = self
            return False

        elif self.scroll_type == 'lantern_upgrade':
            add_log(f"{character.name} reads the {self.name}. You feel its magic seeking a lantern to enhance...")

            # Find the lantern in inventory
            lantern = None
            for item in character.inventory.items:
                if isinstance(item, Lantern):
                    lantern = item
                    break

            if not lantern:
                add_log("You have no lantern to upgrade!")
                return False

            # Check if already at max upgrade
            if lantern.upgrade_level >= 2:
                add_log(f"{COLOR_YELLOW}Your lantern is already at maximum upgrade level!{COLOR_RESET}")
                return False

            # Upgrade success chance based on intelligence
            upgrade_prob = 0.70 + (character.intelligence / 50)
            upgrade_prob = min(0.95, upgrade_prob)

            if random.random() < upgrade_prob:
                lantern.upgrade_level += 1
                add_log(f"{COLOR_GREEN} Successfully upgraded {lantern.name}! It is now +{lantern.upgrade_level}.{COLOR_RESET}")
                add_log(f"{COLOR_GREEN}The lantern's light now reaches further into the darkness! Shiney!{COLOR_RESET}")
            else:
                add_log(f"{COLOR_RED}Upgrade failed! The scroll crumbles in your hands.{COLOR_RESET}")

            return True  # Consumed either way
                # FIX: Handle foresight scroll properly
        if self.scroll_type == 'foresight':
            add_log(f"{COLOR_CYAN}{character.name} unfurls the {self.name}...{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Ancient runes glow, revealing the path ahead!{COLOR_RESET}")
            add_log(f"{COLOR_YELLOW}Choose a direction to peer into (n/s/e/w) or 'c' to cancel:{COLOR_RESET}")

            gs.prompt_cntl = 'foresight_direction_mode'
            gs.active_foresight_scroll = self
            return False  # Don't consume yet - wait for direction

        elif self.scroll_type == 'spell_scroll':
            #  SPELL SCROLL LOGIC 
            if not self.spell_to_cast:
                add_log(f"{COLOR_YELLOW}This scroll's magic has faded...{COLOR_RESET}")
                return True

            add_log(f"{COLOR_CYAN}{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}You read the {self.name} aloud!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Arcane words of power echo through the chamber!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}{COLOR_RESET}")

            # Create a temporary enhanced spell
            enhanced_spell = Spell(
                name=self.spell_to_cast.name,
                description=self.spell_to_cast.description,
                mana_cost=0,  # Scrolls don't cost mana!
                damage_type=self.spell_to_cast.damage_type,
                base_power=int(self.spell_to_cast.base_power * self.spell_power_multiplier),
                level=self.spell_to_cast.level,
                spell_type=self.spell_to_cast.spell_type,
                status_effect_name=self.spell_to_cast.status_effect_name,
                status_effect_duration=self.spell_to_cast.status_effect_duration,
                status_effect_type=self.spell_to_cast.status_effect_type,
                status_effect_magnitude=int(self.spell_to_cast.status_effect_magnitude * self.spell_power_multiplier) if self.spell_to_cast.status_effect_magnitude else 0
            )

            # Cast on active monster if in combat, otherwise heal/buff self
            if gs.active_monster and gs.active_monster.is_alive():
                # Scrolls bypass Platino's defenses
                if gs.active_monster.properties.get('is_platino'):
                    add_log(f"{COLOR_GREEN}It works! Platino is confused where the attack came from!{COLOR_RESET}")
                character.cast_spell(enhanced_spell, gs.active_monster)
                add_log(f"{COLOR_GREEN}The scroll's enhanced magic surges forth! (+{int((self.spell_power_multiplier - 1) * 100)}% power){COLOR_RESET}")

                # Check if monster died
                if not gs.active_monster.is_alive():
                    add_log(f"{COLOR_GREEN}The scroll's power obliterated the {gs.active_monster.name}!{COLOR_RESET}")
            else:
                # Self-cast (healing/buff spells)
                character.cast_spell(enhanced_spell, character)
                add_log(f"{COLOR_GREEN}The scroll's enhanced magic flows through you! (+{int((self.spell_power_multiplier - 1) * 100)}% power){COLOR_RESET}")

            add_log(f"{COLOR_GREY}The scroll crumbles to ash in your hands...{COLOR_RESET}")
            return True  # Consumed

        elif self.scroll_type == 'teleport':
            #  TELEPORT SCROLL 
            add_log(f"{COLOR_PURPLE}You read the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}Reality bends around you...{COLOR_RESET}")

            current_floor = my_tower.floors[character.z]

            # Find random safe location
            for _ in range(100):
                rx = random.randint(0, current_floor.cols - 1)
                ry = random.randint(0, current_floor.rows - 1)
                if not is_wall_at_coordinate(current_floor, ry, rx):
                    character.x = rx
                    character.y = ry
                    current_floor.grid[ry][rx].discovered = True
                    reveal_adjacent_walls(character, my_tower)
                    add_log(f"{COLOR_CYAN}You materialize at ({rx}, {ry})!{COLOR_RESET}")
                    _trigger_room_interaction(character, my_tower)
                    break

            return True  # Consumed

        elif self.scroll_type == 'mapping':
            #  MAPPING SCROLL 
            add_log(f"{COLOR_CYAN}You unfurl the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}The entire floor layout appears in your mind!{COLOR_RESET}")

            current_floor = my_tower.floors[character.z]
            revealed = 0
            for r in range(current_floor.rows):
                for c in range(current_floor.cols):
                    if not current_floor.grid[r][c].discovered:
                        current_floor.grid[r][c].discovered = True
                        revealed += 1

            add_log(f"{COLOR_GREEN}Revealed {revealed} rooms!{COLOR_RESET}")
            return True  # Consumed

        elif self.scroll_type == 'protection':
            #  PROTECTION SCROLL 
            add_log(f"{COLOR_CYAN}You read the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}A shimmering barrier surrounds you!{COLOR_RESET}")

            character.add_status_effect(
                effect_name='Magical Protection',
                duration=5,
                effect_type='defense_boost',
                magnitude=15,
                description='Protected by ancient wards'
            )

            add_log(f"{COLOR_GREEN}Defense increased by 15 for 5 turns!{COLOR_RESET}")
            return True  # Consumed

        elif self.scroll_type == 'restoration':
            #  RESTORATION SCROLL 
            add_log(f"{COLOR_GREEN}You read the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}Divine energy washes over you!{COLOR_RESET}")

            old_health = character.health
            character.health = character.max_health
            healed = character.health - old_health

            # Remove all negative status effects
            effects_removed = []
            for effect_name in list(character.status_effects.keys()):
                if character.status_effects[effect_name].effect_type in ['poison', 'damage_over_time', 'confusion', 'web', 'sticky_hands']:
                    character.remove_status_effect(effect_name)
                    effects_removed.append(effect_name)

            add_log(f"{COLOR_GREEN}Fully healed! (+{healed} HP){COLOR_RESET}")
            if effects_removed:
                add_log(f"{COLOR_GREEN}Cleansed: {', '.join(effects_removed)}{COLOR_RESET}")

            return True  # Consumed

        elif self.scroll_type == 'descent':
            #  DESCENT SCROLL 
            add_log(f"{COLOR_PURPLE}You read the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_PURPLE}The floor beneath you opens...{COLOR_RESET}")

            # Teleport down 1-3 floors
            floors_down = random.randint(1, 3)
            character.z += floors_down

            # Generate floors if needed
            while len(my_tower.floors) <= character.z:
                my_tower.add_floor(**gs.floor_params)

            # Find safe landing spot
            current_floor = my_tower.floors[character.z]
            for _ in range(100):
                rx = random.randint(0, current_floor.cols - 1)
                ry = random.randint(0, current_floor.rows - 1)
                if not is_wall_at_coordinate(current_floor, ry, rx):
                    character.x = rx
                    character.y = ry
                    current_floor.grid[ry][rx].discovered = True
                    reveal_adjacent_walls(character, my_tower)
                    add_log(f"{COLOR_CYAN}You descend {floors_down} floors to Floor {character.z + 1}!{COLOR_RESET}")
                    _trigger_room_interaction(character, my_tower)
                    break

            return True  # Consumed
        elif self.scroll_type == 'vendor_restock':
            return use_scroll_of_commerce(character, my_tower)
        elif self.scroll_type == 'identify':
            # IDENTIFY SCROLL
            add_log(f"{COLOR_CYAN}You read the {self.name}!{COLOR_RESET}")
            add_log(f"{COLOR_CYAN}Ancient knowledge flows into your mind...{COLOR_RESET}")
            
            # Find unidentified items in inventory
            unidentified_items = []
            for item in character.inventory.items:
                if isinstance(item, (Potion, Scroll, Spell, Weapon, Armor)):
                    if not is_item_identified(item):
                        unidentified_items.append(item)
            
            if not unidentified_items:
                add_log(f"{COLOR_YELLOW}All your items are already identified!{COLOR_RESET}")
                return False  # Don't consume if nothing to identify
            
            # Enter identify selection mode
            add_log(f"{COLOR_YELLOW}Select an item to identify (1-{len(unidentified_items)}) or 'c' to cancel:{COLOR_RESET}")
            for i, item in enumerate(unidentified_items):
                cryptic_name = get_item_display_name(item)
                add_log(f"  {i + 1}. {cryptic_name}")
            
            gs.prompt_cntl = 'identify_scroll_mode'
            gs.active_scroll_item = self
            return False  # Don't consume yet - wait for selection
        else:
            # Generic scroll behavior
            add_log(f"{character.name} read the {self.name}. Effect: {self.effect_description}")
            return True

def process_upgrade_scroll_action(player_character, my_tower, cmd):
    from .game_systems import handle_inventory_menu

    if cmd.lower() == 'c':
        add_log("Upgrade cancelled.")
        gs.prompt_cntl = "inventory"
        gs.active_scroll_item = None
        handle_inventory_menu(player_character, my_tower, "init")
        return

    # Determine scroll tier and max upgrade level
    scroll_name = gs.active_scroll_item.name if gs.active_scroll_item else ""
    if "Eternal" in scroll_name:
        max_upgrade_level = 35
        scroll_tier = "Eternal"
        next_tier_hint = None  # Max tier
    elif "Cosmic" in scroll_name:
        max_upgrade_level = 30
        scroll_tier = "Cosmic"
        next_tier_hint = "Scroll of Eternal Upgrade (floor 40+)"
    elif "Celestial" in scroll_name:
        max_upgrade_level = 25
        scroll_tier = "Celestial"
        next_tier_hint = "Scroll of Cosmic Upgrade (floor 35+)"
    elif "Divine" in scroll_name:
        max_upgrade_level = 20
        scroll_tier = "Divine"
        next_tier_hint = "Scroll of Celestial Upgrade (floor 30+)"
    elif "Mythic" in scroll_name:
        max_upgrade_level = 17
        scroll_tier = "Mythic"
        next_tier_hint = "Scroll of Divine Upgrade (floor 25+)"
    elif "Epic" in scroll_name:
        max_upgrade_level = 14
        scroll_tier = "Epic"
        next_tier_hint = "Scroll of Mythic Upgrade (floor 20+)"
    elif "Superior" in scroll_name:
        max_upgrade_level = 10
        scroll_tier = "Superior"
        next_tier_hint = "Scroll of Epic Upgrade (floor 15+)"
    elif "Greater" in scroll_name:
        max_upgrade_level = 6
        scroll_tier = "Greater"
        next_tier_hint = "Scroll of Superior Upgrade (floor 10+)"
    else:
        max_upgrade_level = 3
        scroll_tier = "Basic"
        next_tier_hint = "Scroll of Greater Upgrade (floor 5+)"

    upgradable_items = []
    for item in player_character.inventory.items:
        if isinstance(item, (Weapon, Armor)):
            upgradable_items.append(item)

    if cmd == "init":
        # Show available items with upgrade limits
        add_log(f"{COLOR_PURPLE}=== {gs.active_scroll_item.name} ==={COLOR_RESET}")
        add_log(f"{COLOR_CYAN}This scroll can upgrade items up to +{max_upgrade_level}{COLOR_RESET}")
        add_log("")
        if not upgradable_items:
            add_log(f"{COLOR_YELLOW}You have no weapons or armor to upgrade!{COLOR_RESET}")
            gs.prompt_cntl = "inventory"
            gs.active_scroll_item = None
            handle_inventory_menu(player_character, my_tower, "init")
            return
        
        add_log(f"{COLOR_YELLOW}Choose an item to upgrade:{COLOR_RESET}")
        for i, item in enumerate(upgradable_items, 1):
            current_level = item.upgrade_level
            item_display = item.get_display_name() if hasattr(item, 'get_display_name') else item.name
            
            if current_level >= max_upgrade_level:
                add_log(f"  {COLOR_GREY}{i}. {item_display} - MAX for this scroll{COLOR_RESET}")
            else:
                add_log(f"  {COLOR_GREEN}{i}. {item_display}{COLOR_RESET}")
        
        add_log("")
        add_log(f"{COLOR_CYAN}Enter number to upgrade, or 'c' to cancel.{COLOR_RESET}")
        return

    try:
        item_index = int(cmd) - 1
        if 0 <= item_index < len(upgradable_items):
            chosen_item = upgradable_items[item_index]
            
            # Check if item is already at max for this scroll tier
            if chosen_item.upgrade_level >= max_upgrade_level:
                add_log(f"{COLOR_RED}This item is already at +{chosen_item.upgrade_level}!{COLOR_RESET}")
                if next_tier_hint:
                    add_log(f"{COLOR_YELLOW}You need a stronger scroll to go beyond +{max_upgrade_level}.{COLOR_RESET}")
                    add_log(f"{COLOR_CYAN}Try finding a {next_tier_hint}{COLOR_RESET}")
                else:
                    add_log(f"{COLOR_YELLOW}This item has reached the maximum possible upgrade level!{COLOR_RESET}")
                return

            # Upgrade probability logic - gets harder at higher levels
            base_prob = 0.70
            if chosen_item.upgrade_level >= 15:
                base_prob = 0.35  # Very hard at +15 and above
            elif chosen_item.upgrade_level >= 10:
                base_prob = 0.45  # Hard at +10 to +14
            elif chosen_item.upgrade_level >= 6:
                base_prob = 0.55  # Medium at +6 to +9
            elif chosen_item.upgrade_level >= 3:
                base_prob = 0.60  # Slightly harder at +3 to +5
            
            # Item's own upgrade limit still applies
            if chosen_item.upgrade_limit:
                if chosen_item.upgrade_level >= (chosen_item.level + 1):
                    base_prob -= 0.15  # Penalty for exceeding item's natural limit
            
            # Intelligence and level bonuses
            upgrade_prob = base_prob + (player_character.intelligence / 100) + (player_character.level / 100)
            upgrade_prob = min(0.95, max(0.10, upgrade_prob))  # Clamp between 10% and 95%

            if random.random() < upgrade_prob:
                chosen_item.upgrade_level += 1
                # Recalculate max_durability to reflect the upgrade, and heal proportionally
                if isinstance(chosen_item, (Weapon, Armor)):
                    old_max = chosen_item.max_durability
                    bonus = chosen_item.UPGRADE_DURABILITY_BONUS
                    chosen_item.max_durability += bonus
                    chosen_item.durability = min(chosen_item.max_durability, chosen_item.durability + bonus)
                new_display = chosen_item.get_display_name() if hasattr(chosen_item, 'get_display_name') else f"{chosen_item.name} +{chosen_item.upgrade_level}"
                add_log(f"{COLOR_GREEN}Successfully upgraded!{COLOR_RESET}")
                add_log(f"{COLOR_CYAN}{new_display}{COLOR_RESET}")
                if chosen_item.upgrade_level >= max_upgrade_level:
                    if next_tier_hint:
                        add_log(f"{COLOR_YELLOW}This item is now at the max for {scroll_tier} scrolls.{COLOR_RESET}")
                    else:
                        add_log(f"{COLOR_PURPLE}*** MAXIMUM UPGRADE ACHIEVED! ***{COLOR_RESET}")
            else:
                add_log(f"{COLOR_RED}Upgrade failed! The scroll crumbles to dust.{COLOR_RESET}")

            # Consume the scroll
            player_character.inventory.remove_item(gs.active_scroll_item.name)
            gs.active_scroll_item = None
            gs.prompt_cntl = "inventory"
            handle_inventory_menu(player_character, my_tower, "init")
        else:
            add_log(f"{COLOR_YELLOW}Invalid number. Please choose a number from the list.{COLOR_RESET}")
    except ValueError:
        add_log(f"{COLOR_YELLOW}Invalid input. Please enter a number or 'c' to cancel.{COLOR_RESET}")
# 
# SCROLL OF COMMERCE (Consumable)
# 

def process_identify_scroll_action(player_character, my_tower, cmd):
    """Handle item selection for Scroll of Identify"""
    from .game_systems import handle_inventory_menu

    if cmd.lower() == 'c':
        add_log("Identification cancelled.")
        gs.prompt_cntl = "inventory"
        gs.active_scroll_item = None
        handle_inventory_menu(player_character, my_tower, "init")
        return
    
    # Build list of unidentified items
    unidentified_items = []
    for item in player_character.inventory.items:
        if isinstance(item, (Potion, Scroll, Spell, Weapon, Armor)):
            if not is_item_identified(item):
                unidentified_items.append(item)
    
    if cmd == "init":
        # Show available items to identify
        add_log(f"{COLOR_PURPLE}=== Scroll of Identify ==={COLOR_RESET}")
        add_log("")
        if not unidentified_items:
            add_log(f"{COLOR_YELLOW}All your items are already identified!{COLOR_RESET}")
            gs.prompt_cntl = "inventory"
            gs.active_scroll_item = None
            handle_inventory_menu(player_character, my_tower, "init")
            return
        
        add_log(f"{COLOR_YELLOW}Choose an item to identify:{COLOR_RESET}")
        for i, item in enumerate(unidentified_items, 1):
            cryptic_name = get_item_display_name(item)
            add_log(f"  {COLOR_CYAN}{i}. {cryptic_name}{COLOR_RESET}")
        
        add_log("")
        add_log(f"{COLOR_CYAN}Enter number to identify, or 'c' to cancel.{COLOR_RESET}")
        return
    
    try:
        item_index = int(cmd) - 1
        if 0 <= item_index < len(unidentified_items):
            chosen_item = unidentified_items[item_index]
            cryptic_name = get_item_display_name(chosen_item)
            
            # Identify the item
            identify_item(chosen_item)
            
            add_log(f"{COLOR_GREEN}The {cryptic_name} is revealed to be: {chosen_item.name}!{COLOR_RESET}")
            
            # Consume the scroll
            if gs.active_scroll_item:
                if hasattr(gs.active_scroll_item, 'count') and gs.active_scroll_item.count > 1:
                    gs.active_scroll_item.count -= 1
                else:
                    player_character.inventory.items.remove(gs.active_scroll_item)
            
            gs.prompt_cntl = "inventory"
            gs.active_scroll_item = None
            handle_inventory_menu(player_character, my_tower, "init")
        else:
            add_log(f"{COLOR_RED}Invalid selection. Choose 1-{len(unidentified_items)} or 'c' to cancel.{COLOR_RESET}")
    except ValueError:
        add_log(f"{COLOR_RED}Invalid input. Enter a number or 'c' to cancel.{COLOR_RESET}")


def use_scroll_of_commerce(character, my_tower):
    """
    Restock a single vendor on the current floor.
    If multiple vendors exist, player chooses which one.
    """

    current_floor = my_tower.floors[character.z]

    # Find all vendor rooms on current floor
    vendor_rooms = []
    for r in range(current_floor.rows):
        for c in range(current_floor.cols):
            room = current_floor.grid[r][c]
            if room.room_type == 'V' and room.discovered:
                vendor_rooms.append((c, r, room))

    if not vendor_rooms:
        add_log(f"{COLOR_YELLOW}There are no known vendors on this floor!{COLOR_RESET}")
        add_log(f"{COLOR_YELLOW}Explore to find a vendor first, then use this scroll.{COLOR_RESET}")
        return False  # Not consumed

    # If only one vendor, restock it automatically
    if len(vendor_rooms) == 1:
        vendor_x, vendor_y, vendor_room = vendor_rooms[0]
        restock_vendor_at(my_tower, character, vendor_x, vendor_y)

        add_log(f"{COLOR_GREEN}{COLOR_RESET}")
        add_log(f"{COLOR_GREEN} SCROLL OF COMMERCE ACTIVATED! {COLOR_RESET}")
        add_log(f"{COLOR_GREEN}{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}The vendor at ({vendor_x}, {vendor_y}) has restocked their inventory!{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}New items are now available for purchase!{COLOR_RESET}")

        return True  # Consumed

    # Multiple vendors - need to choose
    add_log(f"{COLOR_YELLOW}{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}Multiple vendors detected on this floor:{COLOR_RESET}")
    for i, (vx, vy, vroom) in enumerate(vendor_rooms, 1):
        add_log(f"  {i}. Vendor at ({vx}, {vy})")
    add_log(f"{COLOR_YELLOW}{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Which vendor would you like to restock? (1-{len(vendor_rooms)}){COLOR_RESET}")

    # Store vendor info for selection (in practice, you'd handle this via a new prompt mode)
    # For simplicity, we'll just restock the first one
    vendor_x, vendor_y, vendor_room = vendor_rooms[0]
    restock_vendor_at(my_tower, character, vendor_x, vendor_y)

    add_log(f"{COLOR_GREEN} Vendor at ({vendor_x}, {vendor_y}) restocked!{COLOR_RESET}")
    return True  # Consumed


# 
# MERCHANT'S HORN (Unique Treasure - Reusable)
# 

def use_merchants_horn(character, my_tower):
    """
    Restock ALL vendors on the current floor.
    This is a reusable unique treasure.
    """
    current_floor = my_tower.floors[character.z]

    # Find all vendor rooms on current floor
    vendor_rooms = []
    for r in range(current_floor.rows):
        for c in range(current_floor.cols):
            room = current_floor.grid[r][c]
            if room.room_type == 'V':  # Include undiscovered vendors too
                vendor_rooms.append((c, r, room))

    if not vendor_rooms:
        add_log(f"{COLOR_YELLOW}There are no vendors on this floor.{COLOR_RESET}")
        return False  # Not consumed

    add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
    add_log(f"{COLOR_PURPLE} YOU BLOW THE MERCHANT'S HORN! {COLOR_RESET}")
    add_log(f"{COLOR_PURPLE}{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}A melodious tune echoes through the cavern!{COLOR_RESET}")
    add_log(f"{COLOR_YELLOW}All merchants on this floor rush to restock!{COLOR_RESET}")

    # Restock all vendors
    for vendor_x, vendor_y, vendor_room in vendor_rooms:
        restock_vendor_at(my_tower, character, vendor_x, vendor_y)

    add_log(f"{COLOR_GREEN} {len(vendor_rooms)} vendor(s) restocked with fresh inventory!{COLOR_RESET}")
    add_log(f"{COLOR_CYAN}Visit them to see the new wares!{COLOR_RESET}")

    return False  # NOT consumed (reusable)


# 
# VENDOR RESTOCKING CORE FUNCTION
# 

def restock_vendor_at(tower, character, vendor_x, vendor_y):
    """
    Restock a specific vendor with new random inventory.
    This regenerates the vendor's stock as if it's a new vendor.
    """
    from .achievements import check_achievements

    floor_level = character.z

    current_floor = tower.floors[floor_level]
    vendor_room = current_floor.grid[vendor_y][vendor_x]

    # Check if it's actually a vendor room
    if vendor_room.room_type != 'V':
        add_log(f"{COLOR_RED}ERROR: No vendor at ({vendor_x}, {vendor_y}){COLOR_RESET}")
        return

    # Generate new vendor inventory
    # This is similar to how vendors are initially populated
    new_inventory = generate_vendor_inventory(floor_level)
    # Track in game stats
    gs.game_stats['vendors_restocked'] = gs.game_stats.get('vendors_restocked', 0) + 1
    check_achievements(character)
    # Store the new inventory in the room properties
    vendor_room.properties['vendor_inventory'] = new_inventory
    vendor_room.properties['restocked'] = vendor_room.properties.get('restocked', 0) + 1

    # Optional: Add a visual indicator that vendor was restocked
    add_log(f"{COLOR_GREEN}[Vendor at ({vendor_x}, {vendor_y}) has been restocked!]{COLOR_RESET}")


def generate_vendor_inventory(floor_level, room):
    """
    Generate a new random vendor inventory for the given floor level.
    Uses enhanced weapon/armor generation for better variety.
    """
    from .game_systems import create_random_enhanced_weapon, create_random_enhanced_armor
    from .item_templates import ALL_ITEM_TEMPLATES

    inventory = []

    # Determine item level range for this vendor
    min_item_level = max(0, floor_level - 1)
    max_item_level = floor_level + 2

    # Get available non-weapon/armor items
    available_items = [
        item for item in ALL_ITEM_TEMPLATES
        if min_item_level <= item.level <= max_item_level
        and not isinstance(item, (Weapon, Armor))
    ]

    if not available_items:
        available_items = [item for item in ALL_ITEM_TEMPLATES if not isinstance(item, (Weapon, Armor))]

    # Add 1-2 enhanced weapons
    num_weapons = random.randint(1, 2)
    for _ in range(num_weapons):
        weapon = create_random_enhanced_weapon(floor_level)
        inventory.append(weapon)
    
    # Add 1-2 enhanced armors
    num_armors = random.randint(1, 2)
    for _ in range(num_armors):
        armor = create_random_enhanced_armor(floor_level)
        inventory.append(armor)

    # Always stock 2-4 healing potions appropriate to floor level
    if floor_level >= 30:
        heal_potions = [
            Potion("Legendary Healing Potion", "A shimmering elixir of extraordinary restoration.", value=500, level=15, potion_type='healing', effect_magnitude=350),
            Potion("Mythic Healing Potion", "Liquid starlight that knits flesh and bone.", value=800, level=25, potion_type='healing', effect_magnitude=500),
        ]
    elif floor_level >= 20:
        heal_potions = [
            Potion("Heroic Healing Potion", "A radiant vial that mends grievous wounds.", value=250, level=10, potion_type='healing', effect_magnitude=200),
            Potion("Legendary Healing Potion", "A shimmering elixir of extraordinary restoration.", value=500, level=15, potion_type='healing', effect_magnitude=350),
        ]
    elif floor_level >= 10:
        heal_potions = [
            Potion("Greater Healing Potion", "Restores 100 HP.", value=100, level=2, potion_type='healing', effect_magnitude=100),
            Potion("Superior Healing Potion", "Restores 150 HP.", value=150, level=4, potion_type='healing', effect_magnitude=150),
        ]
    elif floor_level >= 5:
        heal_potions = [
            Potion("Healing Potion", "Restores 50 HP.", value=50, level=1, potion_type='healing', effect_magnitude=50),
            Potion("Greater Healing Potion", "Restores 100 HP.", value=100, level=2, potion_type='healing', effect_magnitude=100),
        ]
    else:
        heal_potions = [
            Potion("Minor Healing Potion", "Restores 25 HP.", value=25, level=0, potion_type='healing', effect_magnitude=25),
            Potion("Healing Potion", "Restores 50 HP.", value=50, level=1, potion_type='healing', effect_magnitude=50),
        ]
    num_heal = random.randint(2, 4)
    for i in range(num_heal):
        inventory.append(_create_item_copy(random.choice(heal_potions)))

    # ALWAYS add an appropriate upgrade scroll for this floor level
    if floor_level >= 40:
        upgrade_scroll = Scroll("Scroll of Eternal Upgrade", "A scroll from beyond time itself.", "Upgrade items to +35 maximum.", 6000, 40, 'upgrade')
    elif floor_level >= 35:
        upgrade_scroll = Scroll("Scroll of Cosmic Upgrade", "A scroll woven from starlight.", "Upgrade items to +30 maximum.", 3500, 35, 'upgrade')
    elif floor_level >= 30:
        upgrade_scroll = Scroll("Scroll of Celestial Upgrade", "A scroll that hums with celestial power.", "Upgrade items to +25 maximum.", 2000, 30, 'upgrade')
    elif floor_level >= 25:
        upgrade_scroll = Scroll("Scroll of Divine Upgrade", "The ultimate scroll of enhancement.", "Upgrade items to +20 maximum.", 1200, 25, 'upgrade')
    elif floor_level >= 20:
        upgrade_scroll = Scroll("Scroll of Mythic Upgrade", "A scroll touched by the gods.", "Upgrade items to +17 maximum.", 850, 20, 'upgrade')
    elif floor_level >= 15:
        upgrade_scroll = Scroll("Scroll of Epic Upgrade", "A legendary scroll pulsing with power.", "Upgrade items to +14 maximum.", 600, 15, 'upgrade')
    elif floor_level >= 10:
        upgrade_scroll = Scroll("Scroll of Superior Upgrade", "An ancient scroll of enhancement.", "Upgrade items to +10 maximum.", 400, 10, 'upgrade')
    elif floor_level >= 5:
        upgrade_scroll = Scroll("Scroll of Greater Upgrade", "A powerful scroll of enhancement.", "Upgrade items to +6 maximum.", 250, 5, 'upgrade')
    else:
        upgrade_scroll = Scroll("Scroll of Upgrade", "A mystical scroll of enhancement.", "Upgrade items to +3 maximum.", 150, 1, 'upgrade')
    inventory.append(upgrade_scroll)

    # Always stock some food items
    rations = Food("Rations", "Standard travel rations.", value=10, level=0, nutrition=40, count=1)
    inventory.append(_create_item_copy(rations))
    if floor_level >= 2:
        jerky = Food("Salted Jerky", "Dried meat. Salty and chewy.", value=15, level=1, nutrition=35, count=1)
        inventory.append(_create_item_copy(jerky))
    if floor_level >= 3:
        # Cooking Kit available from floor 3+
        cooking_kit = CookingKit()
        inventory.append(cooking_kit)
        iron_rations = Food("Iron Rations", "Military-grade rations. Tasteless but highly nutritious.", value=30, level=3, nutrition=70, count=1)
        inventory.append(_create_item_copy(iron_rations))

    # Curing Kit: stocked on the first vendor found on a specific random floor (1-10).
    # Safety net: if player has reached floor 10 without the kit being stocked yet,
    # the next vendor they find will always carry it.
    if not getattr(gs, 'curing_kit_stocked', False):
        target_floor = getattr(gs, 'curing_kit_floor', None)
        is_target_floor = target_floor is not None and floor_level == target_floor
        is_last_chance = floor_level >= 9  # Floor 10 (0-indexed 9) is the safety net
        if (1 <= floor_level <= 10) and (is_target_floor or is_last_chance):
            inventory.append(CuringKit())
            gs.curing_kit_stocked = True

    # Generate 4-8 random other items
    num_items = random.randint(4, 8)

    for _ in range(num_items):
        if available_items:
            item_template = random.choice(available_items)
            new_item = _create_item_copy(item_template)
            inventory.append(new_item)

    # Sort by type and level
    inventory.sort(key=lambda item: (
        type(item).__name__,
        item.level,
        item.name
    ))

    for item in inventory:
        penalty = 1.0 + (room.properties.get('restocked', 0) * 0.1)
        item.value = int(item.value * penalty)

    return inventory

class Flare(Item):
    def __init__(self, name, description="", count=10, light_radius=5, value=1, level=0):
        super().__init__(name, description, value, level)
        self.count = count
        self.light_radius = light_radius
        # Removed: self.value = self.count to keep original value for base calculation

    @property
    def calculated_value(self):
        """Calculates the total value based on the item's base value and count."""
        return self.value * self.count

    def use(self, character, my_tower):

        if self.count <= 0:
            add_log("You are out of flares.")
            return False

        add_log(f"{character.name} lit a {self.name}. Choose a direction (n, s, e, w) to shine it.")
        self.count -= 1
        gs.active_flare_item = self
        gs.prompt_cntl = 'flare_direction_mode'
        return False # Not immediately consumed, awaiting direction

room_discover_descriptions = {
        'M': 'You see a monster!',
        'D': 'You see a passage descending deeper into the cavern',
        'U': 'You see stairs ascending back toward the entrance',
        'E': 'You see the entrance to the cavern',
        'P': 'You see a room with a basin of water',
        'V': 'There is a vendor in this room',
        'W': 'A strange portal fills this room',
        'C': 'You see a treasure chest!',
        '.': 'You see a room with nothing of interest',
        'L': 'You see a dusty library filled with ancient tomes',
        'A': 'An alter to an unknown god is in this room',
        'Z': 'A shimmering portal leads to Zot\'s puzzle chamber',
        'B': 'The ring of hammer on anvil echoes from a blacksmith\'s forge',
        'F': 'A rough shrine scratched into the cavern wall marks where someone fell',
        'Q': 'Strange fumes and bubbling sounds drift from an alchemist\'s laboratory',
        'K': 'A crumbling fortification marks an old war room, maps still pinned to its walls',
        'X': 'The smell of tanning leather and preserving salts drifts from a taxidermist workshop'}


class Lantern(Item):
    def __init__(self, name="Lantern", description="", fuel_amount=50, light_radius=7, value=0, level=0, upgrade_level=0):
        super().__init__(name, description, value, level)
        self.fuel_amount = fuel_amount
        self.light_radius = light_radius
        self.upgrade_level = upgrade_level

    def __repr__(self):
        return f"Lantern(name='{self.name}', fuel={self.fuel_amount}, radius={self.light_radius}, value={self.value}, level={self.level})"

    def use(self, character, my_tower=None):
        if self.fuel_amount > 0:
            add_log(f"{character.name} lit the {self.name}.")

            if my_tower is None:
                add_log("Error: Lantern cannot reveal rooms without tower and grid information.")
                return False # Not consumed

            current_floor = my_tower.floors[character.z]

            # Circular reveal with radius based on light_radius
            # Uses line-of-sight: walls block the lantern light
            directions_to_reveal = []
            radius = self.upgrade_level+1  # Or use self.light_radius if you want it variable

            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    # Calculate Euclidean distance
                    distance = (dr**2 + dc**2)**0.5

                    # Include if within radius and not the character's position
                    if distance <= radius and (dr, dc) != (0, 0):
                        directions_to_reveal.append((dr, dc))

            revealed_any = False
            for dr, dc in directions_to_reveal:
                target_x, target_y = character.y + dr, character.x + dc

                # Check boundaries (target_x is row/y, target_y is col/x)
                if 0 <= target_x < current_floor.rows and 0 <= target_y < current_floor.cols:
                    # Line-of-sight check: walk from player to target,
                    # if any intermediate cell is a wall, light is blocked
                    blocked = False
                    pr, pc_ = character.y, character.x
                    tr, tc = target_x, target_y
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

            # FIX: Swap coordinates to (y, x) for row, col
            my_tower.floors[character.z].print_floor(highlight_coords=(character.x, character.y))
            if not revealed_any:
                add_log("The lantern shines brightly, but no new undiscovered rooms were revealed nearby.")
            else:
                add_log("The lantern shines brightly, revealing undiscovered rooms around you.")

            self.fuel_amount -= 1
            add_log(f"Fuel remaining: {self.fuel_amount}")
            return False # Lantern is not consumed, only fuel
        else:
            # If lantern is out of fuel, try to use Lantern Fuel from inventory
            lantern_fuel_item = character.inventory.get_item("Lantern Fuel")
            if lantern_fuel_item:
                add_log(f"{COLOR_GREEN}The {self.name} is out of fuel. Using {lantern_fuel_item.name} to refuel.{COLOR_RESET}")
                self.fuel_amount += 10 # Refuel amount
                character.inventory.remove_item(lantern_fuel_item.name)
                add_log(f"{COLOR_GREEN}Lantern refueled! Fuel remaining: {self.fuel_amount}){COLOR_RESET}")
                # Now that it's refueled, it can be used, so return False (not consumed)
                return False
            else:
                add_log(f"The {self.name} is out of fuel and you have no Lantern Fuel to refill it.")
                return False # Not consumed

class LanternFuel(Item):
    def __init__(self, name="Lantern Fuel", description="A small flask of oil for your lantern.", value=5, level=0, fuel_restore_amount=10, count=1):
        super().__init__(name, description, value, level)
        self.fuel_restore_amount = fuel_restore_amount
        self.count = count

    def __repr__(self):
        return f"LanternFuel(name='{self.name}', fuel_restore={self.fuel_restore_amount}, value={self.value}, level={self.level}, count={self.count})"

    def use(self, character, my_tower=None):
        # Check if the character has a lantern to refuel
        lantern = None
        for item in character.inventory.items:
            if isinstance(item, Lantern):
                lantern = item
                break

        if lantern:
            lantern.fuel_amount += self.fuel_restore_amount
            add_log(f"{COLOR_GREEN}{character.name} used {self.name} to refuel {lantern.name}. It now has {lantern.fuel_amount} fuel.{COLOR_RESET}")
            return True # Consumed
        else:
            add_log(f"You have no lantern to refuel with silly {character.race}.")
            return False # Not consumed

# --------------------------------------------------------------------------------
# HUNGER SYSTEM - Food, Meat, and Cooking Kit
# --------------------------------------------------------------------------------

# Monster meat descriptors for cooked forms
MEAT_COOK_STYLES = {
    "Goblin":     ("burger",    "barely palatable",  5),
    "Orc":        ("steak",     "tough and gamey",   7),
    "Rat":        ("nuggets",   "surprisingly edible", 8),
    "Bat":        ("kebab",     "chewy",              9),
    "Spider":     ("skewer",    "oddly crunchy",     2),
    "Troll":      ("burger",    "rubbery but filling", 20),
    "Ogre":       ("roast",     "pungent but hearty", 22),
    "Gnoll":      ("burger",    "gamey",             15),
    "Centipede":  ("filet",     "questionable",       4),
    "Lizard":     ("filet",     "surprisingly delicious", 14),
    "Kobold":     ("cold cuts", "sinewy",            10),
    "Minotaur":   ("burger",    "yummy",             25),
    "Werewolf":   ("steak",     "wild and savory",   22),
    "Wyvern":     ("filet",     "rich and dragonlike", 30),
    "Dragon":     ("steak",     "magnificent",       40),
    "Crocodile":  ("filet",     "quite good",        20),
    "Boar":       ("burger",    "delicious",         22),
    "Skeleton":   None,   # Not edible - undead
    "Zombie":     None,   # Not edible - undead
    "Ghost":      None,   # Not edible - undead
    "Wraith":     None,   # Not edible - undead
    "Lich":       None,   # Not edible - undead
    "Vampire":    None,   # Not edible - undead
    "Slime":      None,   # Not edible - amorphous
    "Mold":       None,   # Not edible - fungal
    "Golem":      None,   # Not edible - construct
    "Demon":      None,   # Not edible - demonic
    "Elemental":  None,   # Not edible - elemental
}

# Default for monsters not in the dict
MEAT_DEFAULT = ("steak", "dubious", 12)
MEAT_DEFAULT_CUTS = ["steak", "burger", "chops", "filet", "kebab"]

HUNGER_MAX = 100
HUNGER_DECAY_PER_MOVE = 1  # hunger decreases 1 per move
HUNGER_STARVING_THRESHOLD = 10   # below this: starving, take 1 dmg per move
HUNGER_HUNGRY_THRESHOLD = 40     # below this: hungry, slight combat penalty
HUNGER_PECKISH_THRESHOLD = 70     # below this: peckish, just a cute British word
HUNGER_SATED_THRESHOLD = 90     # above this: sated bonus

MEAT_ROT_TURNS_RAW = 30         # raw meat rots after 30 moves
MEAT_ROT_TURNS_COOKED = 100     # cooked meat keeps longer
MEAT_ROT_TURNS_PRESERVED = 200  # cooked with kit keeps even longer


def get_monster_meat_info(monster_name):
    """Return (cut, descriptor, nutrition) for a monster, or None if not edible."""
    # Check exact name first
    if monster_name in MEAT_COOK_STYLES:
        return MEAT_COOK_STYLES[monster_name]
    # Check if monster name contains a key
    for key, val in MEAT_COOK_STYLES.items():
        if key.lower() in monster_name.lower():
            return val
    # Default: most flesh-and-blood creatures are edible
    # Skip obviously non-edible types
    non_edible_keywords = ['slime', 'mold', 'golem', 'elemental', 'ghost', 'wraith',
                           'skeleton', 'zombie', 'lich', 'vampire', 'specter', 'shade',
                           'revenant', 'mummy', 'demon', 'construct', 'blob', 'ooze',
                           'spore', 'myconid', 'fungal', 'mushroom', 'puff']
    for kw in non_edible_keywords:
        if kw in monster_name.lower():
            return None
    return (random.choice(MEAT_DEFAULT_CUTS), "dubious", 12)


class Food(Item):
    """Generic food item (rations, mushrooms, berries, etc.)"""
    def __init__(self, name, description="", value=5, level=0, nutrition=30, count=1):
        super().__init__(name, description, value, level)
        self.nutrition = nutrition
        self.count = count

    def __repr__(self):
        return f"Food(name='{self.name}', nutrition={self.nutrition}, count={self.count})"

    def use(self, character, my_tower=None):
        old_hunger = character.hunger
        character.hunger = min(HUNGER_MAX, character.hunger + self.nutrition)
        gained = character.hunger - old_hunger
        add_log(f"{COLOR_GREEN}You eat the {self.name}. Hunger restored by {gained}.{COLOR_RESET}")
        return True  # consumed


class LembasWafer(Food):
    """Elven lembas wafer - fills hunger completely and freezes hunger decay for 30 turns."""
    def __init__(self, name="Lembas Wafer", description="A golden elven waybread that sustains travelers on long journeys.", value=25, level=0, count=1):
        super().__init__(name, description, value, level, nutrition=HUNGER_MAX, count=count)

    def __repr__(self):
        return f"LembasWafer(name='{self.name}', count={self.count})"

    def use(self, character, my_tower=None):
        character.hunger = HUNGER_MAX
        character.hunger_freeze_turns = 30
        add_log(f"{COLOR_GREEN}You eat a {self.name}. Its golden warmth fills you completely!{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}The lembas sustains you — hunger will not decrease for 30 turns.{COLOR_RESET}")
        return True  # consumed


class Sausage(Food):
    """Cured sausage crafted from monster meat.

    Dwarves get a +50% nutrition and healing bonus (hearty mountain appetite).
    Spicy variants (is_spicy=True) grant a temporary attack buff on eat.
    """
    def __init__(self, name="Sausage", description="A hand-stuffed cured sausage. Smoked, spiced, and shelf-stable.",
                 value=30, level=1, nutrition=60, count=1, monster_source="Generic", sausage_style="Bratwurst",
                 is_spicy=False, spice_level=0):
        super().__init__(name, description, value, level, nutrition=nutrition, count=count)
        self.monster_source = monster_source
        self.sausage_style = sausage_style
        self.is_spicy = is_spicy
        self.spice_level = spice_level  # 1 = Fire Pepper, 2 = Ghost Pepper

    def __repr__(self):
        return f"Sausage(name='{self.name}', nutrition={self.nutrition}, spicy={self.is_spicy})"

    def use(self, character, my_tower=None):
        is_dwarf = getattr(character, 'race', '').lower() == 'dwarf'
        # Dwarves get +50% nutrition and healing from sausages
        nutrition_gain = int(self.nutrition * 1.5) if is_dwarf else self.nutrition
        base_heal = 5
        heal_amount = int(base_heal * 1.5) if is_dwarf else base_heal

        old_hunger = character.hunger
        character.hunger = min(HUNGER_MAX, character.hunger + nutrition_gain)
        gained = character.hunger - old_hunger
        heal = min(heal_amount, character.max_health - character.health)
        if heal > 0:
            character.health += heal

        add_log(f"{COLOR_GREEN}You eat the {self.name}. Hunger restored by {gained}.{COLOR_RESET}")
        if heal > 0:
            add_log(f"{COLOR_GREEN}The hearty cured meat restores {heal} HP.{COLOR_RESET}")
        if is_dwarf:
            add_log(f"{COLOR_YELLOW}[Dwarven Appetite] Your stout constitution draws extra nourishment from the meal.{COLOR_RESET}")

        # Spicy sausage buff — grants "Spiced Fury" attack boost
        if self.is_spicy:
            magnitude = 3 if self.spice_level <= 1 else 6  # Fire = +3 atk, Ghost = +6 atk
            duration = 10 if self.spice_level <= 1 else 15  # Ghost lasts longer
            # Dwarves handle heat better — 50% longer duration
            if is_dwarf:
                duration = int(duration * 1.5)
            character.add_status_effect(
                effect_name="Spiced Fury",
                duration=duration,
                effect_type='attack_boost',
                magnitude=magnitude,
                description=f"The spicy sausage fills you with fiery vigor (+{magnitude} Atk)."
            )
            add_log(f"{COLOR_RED}Your blood boils with spicy fury! +{magnitude} Attack for {duration} turns.{COLOR_RESET}")

        return True  # consumed


class Meat(Item):
    """Meat dropped by monsters - can be raw or cooked, rots over time."""
    def __init__(self, name, description="", value=3, level=0,
                 monster_name="Unknown", is_cooked=False, nutrition=12,
                 rot_timer=None, cut="steak", descriptor="edible", count=1):
        super().__init__(name, description, value, level)
        self.monster_name = monster_name
        self.is_cooked = is_cooked
        self.nutrition = nutrition
        self.cut = cut            # burger, steak, chops, etc.
        self.descriptor = descriptor  # yummy, gamey, etc.
        self.count = count
        # rot_timer: moves remaining before spoilage
        if rot_timer is None:
            self.rot_timer = MEAT_ROT_TURNS_COOKED if is_cooked else MEAT_ROT_TURNS_RAW
        else:
            self.rot_timer = rot_timer
        self.is_rotten = False

    def __repr__(self):
        state = "cooked" if self.is_cooked else "raw"
        return f"Meat('{self.name}', {state}, rot={self.rot_timer}, nutrition={self.nutrition})"

    def cook(self, with_kit=False):
        """Cook this meat item in place."""
        if self.is_cooked:
            return False
        self.is_cooked = True
        self.nutrition = max(self.nutrition, int(self.nutrition * 1.5))
        self.rot_timer = MEAT_ROT_TURNS_PRESERVED if with_kit else MEAT_ROT_TURNS_COOKED
        # Rename to reflect cooking
        self.name = f"Cooked {self.monster_name} {self.cut.capitalize()}"
        self.description = f"A {self.descriptor} {self.monster_name} {self.cut}, ready to eat."
        return True

    def tick_rot(self):
        """Decrease rot timer by 1. Returns True if meat just became rotten."""
        if self.is_rotten:
            return False
        self.rot_timer -= 1
        if self.rot_timer <= 0:
            self.is_rotten = True
            old_name = self.name
            self.name = f"Rotten {self.monster_name} {self.cut.capitalize()}"
            self.description = "Spoiled meat. Eating it will make you sick."
            self.nutrition = -15  # eating rotten meat hurts
            return True
        return False

    def use(self, character, my_tower=None):
        if self.is_rotten:
            add_log(f"{COLOR_RED}You choke down the rotten {self.monster_name} {self.cut}. Ugh! Your stomach protests.{COLOR_RESET}")
            character.take_damage_no_def(10, "Physical")
            add_log(f"{COLOR_RED}You lose 10 HP from food poisoning!{COLOR_RESET}")
            return True  # consumed anyway
        if not self.is_cooked:
            add_log(f"{COLOR_YELLOW}You gnaw on the raw {self.monster_name} {self.cut}. It's disgusting but fills you a little.{COLOR_RESET}")
            old_hunger = character.hunger
            character.hunger = min(HUNGER_MAX, character.hunger + max(5, self.nutrition // 2))
            gained = character.hunger - old_hunger
            add_log(f"{COLOR_YELLOW}Hunger restored by {gained}.{COLOR_RESET}")
        else:
            old_hunger = character.hunger
            character.hunger = min(HUNGER_MAX, character.hunger + self.nutrition)
            gained = character.hunger - old_hunger
            article = "a" if self.descriptor[0].lower() not in 'aeiou' else "an"
            add_log(f"{COLOR_GREEN}You ate {article} {self.descriptor} {self.monster_name} {self.cut}! Hunger restored by {gained}.{COLOR_RESET}")
        return True  # consumed


class CookingKit(Item):
    """Purchaseable from vendors on floor 3+. Lets you cook meat and food."""
    def __init__(self, name="Cooking Kit", description="A compact kit for cooking meat over a small fire.", value=120, level=3):
        super().__init__(name, description, value, level)

    def __repr__(self):
        return f"CookingKit(name='{self.name}', value={self.value})"

    def use(self, character, my_tower=None):
        """Cook all raw uncooked meat in inventory."""
        meat_items = [item for item in character.inventory.items
                      if isinstance(item, Meat) and not item.is_cooked and not item.is_rotten]
        if not meat_items:
            add_log(f"{COLOR_YELLOW}You have no raw meat to cook.{COLOR_RESET}")
            return False  # not consumed
        cooked_count = 0
        for meat in meat_items:
            meat.cook(with_kit=True)
            cooked_count += 1
            add_log(f"{COLOR_GREEN}You cooked the {meat.name}!{COLOR_RESET}")
        add_log(f"{COLOR_GREEN}Cooked {cooked_count} piece(s) of meat. It will stay fresh much longer!{COLOR_RESET}")
        return False  # kit is reusable, not consumed


class CuringKit(Item):
    """Guaranteed purchase from a vendor on floors 1-10. Unlocks sausage crafting."""
    def __init__(self, name="Curing Kit",
                 description="A small wooden box of salt, saltpeter, spice jars, and natural casings. Unlocks sausage crafting at the cooking pot.",
                 value=180, level=1):
        super().__init__(name, description, value, level)

    def __repr__(self):
        return f"CuringKit(name='{self.name}', value={self.value})"

    def use(self, character, my_tower=None):
        """Curing kit is never used directly — it enables sausage recipes in crafting."""
        add_log(f"{COLOR_CYAN}The Curing Kit unlocks sausage recipes in the crafting menu. Combine meat with curing ingredients!{COLOR_RESET}")
        return False  # not consumed


def cook_meat_in_inventory(character, source="fire"):
    """Cook all raw meat in character's inventory (from fire damage or fire kill)."""
    has_kit = any(isinstance(item, CookingKit) for item in character.inventory.items)
    raw_meat = [item for item in character.inventory.items
                if isinstance(item, Meat) and not item.is_cooked and not item.is_rotten]
    if not raw_meat:
        return
    add_log(f"{COLOR_YELLOW}The {source} cooks the meat in your pack!{COLOR_RESET}")
    for meat in raw_meat:
        meat.cook(with_kit=has_kit)
        quality = "perfectly" if has_kit else "unevenly"
        add_log(f"{COLOR_GREEN}Your {meat.name} has been {quality} cooked!{COLOR_RESET}")


def drop_monster_items(monster, player_character):
    """
    Chance to drop equipment/items from slain monsters.
    Low base probability, scales with monster level and floor.
    """
    from .game_systems import create_random_enhanced_weapon, create_random_enhanced_armor, get_random_potion
    from .item_templates import SCROLL_TEMPLATES

    monster_lvl = getattr(monster, 'level', 1)
    floor_lvl = player_character.z

    # Base 3% chance, +1% per monster level, +0.5% per floor, cap at 18%
    drop_chance = min(0.18, 0.03 + monster_lvl * 0.01 + floor_lvl * 0.005)

    if random.random() >= drop_chance:
        return

    # Decide what drops: weapon, armor, scroll, spell, or potion
    # Higher level monsters drop better categories
    roll = random.random()
    if roll < 0.25:
        # Weapon drop
        item = create_random_enhanced_weapon(floor_lvl)
        add_log(f"{COLOR_YELLOW}The {monster.name} dropped {get_article(item.name)} {item.name}!{COLOR_RESET}")
    elif roll < 0.50:
        # Armor drop
        item = create_random_enhanced_armor(floor_lvl)
        add_log(f"{COLOR_YELLOW}The {monster.name} dropped some {item.name}!{COLOR_RESET}")
    elif roll < 0.70:
        # Potion drop
        item = get_random_potion(floor_lvl)
        display = get_item_display_name(item)
        add_log(f"{COLOR_CYAN}The {monster.name} dropped {get_article(display)} {display}!{COLOR_RESET}")
    elif roll < 0.85:
        # Scroll drop
        scroll_candidates = [s for s in SCROLL_TEMPLATES if s.level <= floor_lvl + 2]
        if not scroll_candidates:
            scroll_candidates = SCROLL_TEMPLATES
        base = random.choice(scroll_candidates)
        item = Scroll(name=base.name, scroll_type=base.scroll_type,
                      spell_to_cast=base.spell_to_cast,
                      spell_power_multiplier=base.spell_power_multiplier,
                      value=base.value, level=base.level,
                      description=base.description,
                      effect_description=base.effect_description)
        display = get_item_display_name(item)
        add_log(f"{COLOR_CYAN}The {monster.name} dropped {get_article(display)} {display}!{COLOR_RESET}")
    else:
        # Spell drop
        spell_candidates = [s for s in SPELL_TEMPLATES if s.level <= min(5, floor_lvl // 3 + 1)]
        if not spell_candidates:
            spell_candidates = [s for s in SPELL_TEMPLATES if s.level <= 1]
        base = random.choice(spell_candidates)
        item = Spell(name=base.name, spell_type=base.spell_type,
                     mana_cost=base.mana_cost, effect_magnitude=base.effect_magnitude,
                     value=base.value, level=base.level, description=base.description,
                     element=getattr(base, 'element', 'None'))
        display = get_item_display_name(item)
        add_log(f"{COLOR_PURPLE}The {monster.name} dropped {get_article(display)} {display}!{COLOR_RESET}")

    player_character.inventory.add_item(item)


def drop_monster_meat(monster, player_character, fire_killed=False):
    """Drop meat from a slain monster into player's inventory, if edible."""
    info = get_monster_meat_info(monster.name)
    if info is None:
        return  # Not edible
    # 35% chance to drop meat
    if random.random() > 0.35:
        return
    cut, descriptor, nutrition = info
    raw_name = f"Raw {monster.name} {cut.capitalize()}"
    meat = Meat(
        name=raw_name,
        description=f"Raw {monster.name} meat. Cook it for better results.",
        value=2,
        level=0,
        monster_name=monster.name,
        is_cooked=False,
        nutrition=nutrition,
        cut=cut,
        descriptor=descriptor
    )
    if fire_killed:
        # Fire kill auto-cooks the meat
        has_kit = any(isinstance(item, CookingKit) for item in player_character.inventory.items)
        meat.cook(with_kit=has_kit)
        add_log(f"{COLOR_YELLOW}The fire kill cooked the {monster.name} meat!{COLOR_RESET}")
        add_log(f"{COLOR_GREEN}You harvested a {meat.name}!{COLOR_RESET}")
    else:
        add_log(f"{COLOR_CYAN}You harvested some raw {monster.name} meat.{COLOR_RESET}")
    player_character.inventory.add_item(meat)


def tick_meat_rot(character):
    """Called each move to advance meat rot timers. Returns messages."""
    for item in list(character.inventory.items):
        if isinstance(item, Meat) and not item.is_rotten:
            just_rotted = item.tick_rot()
            if just_rotted:
                add_log(f"{COLOR_RED}Your {item.monster_name} meat has gone rotten!{COLOR_RESET}")


def process_hunger(character):
    """Called each move. Decreases hunger and applies penalties/bonuses."""
    # Check for lembas hunger freeze
    freeze = getattr(character, 'hunger_freeze_turns', 0)
    if freeze > 0:
        character.hunger_freeze_turns -= 1
        if character.hunger_freeze_turns == 0:
            add_log(f"{COLOR_YELLOW}The sustaining power of the lembas fades.{COLOR_RESET}")
    else:
        character.hunger = max(0, character.hunger - HUNGER_DECAY_PER_MOVE)

    h = character.hunger

    # HP regeneration: 1 HP every 2 moves when hunger >= 85
    if h >= 85 and character.health < character.max_health:
        tracker = getattr(character, 'hunger_regen_tracker', 0) + 1
        character.hunger_regen_tracker = tracker
        if tracker >= 2:
            character.hunger_regen_tracker = 0
            character.health = min(character.max_health, character.health + 1)
            add_log(f"{COLOR_GREEN}[Well-fed] +1 HP{COLOR_RESET}")
    else:
        character.hunger_regen_tracker = 0

    if h <= 0:
        # Starving: take damage
        dmg = 2
        character.health = max(1, character.health - dmg)
        add_log(f"{COLOR_RED}You are STARVING! Lost {dmg} HP from hunger!{COLOR_RESET}")
    elif h <= HUNGER_STARVING_THRESHOLD:
        # About to starve warning
        if h % 10 == 0:
            add_log(f"{COLOR_RED}You are desperately hungry! Find food soon!{COLOR_RESET}")
    elif h <= HUNGER_HUNGRY_THRESHOLD:
        if h % 20 == 0:
            add_log(f"{COLOR_YELLOW}Your stomach growls. You are hungry.{COLOR_RESET}")


def get_hunger_label(hunger):
    """Return a text label for the current hunger level."""
    if hunger <= 0:
        return "STARVING"
    elif hunger <= HUNGER_STARVING_THRESHOLD:
        return "Starving"
    elif hunger <= HUNGER_HUNGRY_THRESHOLD:
        return "Hungry"
    elif hunger <= HUNGER_PECKISH_THRESHOLD:
        return "Peckish"
    elif hunger <= HUNGER_SATED_THRESHOLD:
        return "Satisfied"
    else:
        return "Full"


def get_hunger_color(hunger):
    """Return HTML color for hunger label."""
    if hunger <= HUNGER_STARVING_THRESHOLD:
        return "#FF4444"
    elif hunger <= HUNGER_HUNGRY_THRESHOLD:
        return "#FFA500"
    elif hunger <= HUNGER_SATED_THRESHOLD:
        return "#FFFF88"
    else:
        return "#88FF88"

class Treasure(Item):
    def __init__(self, name, description="", gold_value=0, value=0, benefit=None, level=0,
                 treasure_type='gold', is_unique=False, use_effect=None, passive_effect=None):
        super().__init__(name, description, value, level)
        self.gold_value = gold_value
        self.benefit = benefit if benefit is not None else {}
        self.treasure_type = treasure_type  # 'gold', 'stat_boost', 'usable', 'passive'
        self.is_unique = is_unique
        self.use_effect = use_effect  # Function to call when used
        self.passive_effect = passive_effect  # Continuous effect description
        self.is_equipped = False  # For passive items

    def __repr__(self):
        unique_marker = " [UNIQUE]" if self.is_unique else ""
        return f"Treasure(name='{self.name}', value={self.gold_value} gold, benefit={self.benefit}, level={self.level}){unique_marker}"

    def collect(self, character):
        """Called when treasure is picked up from a chest"""
        from .achievements import check_achievements

        if self.treasure_type == 'gold':
            character.gold += self.gold_value
            add_log(f"{COLOR_GREEN}{character.name} collected {self.name} worth {self.gold_value} gold. Total gold: {character.gold}{COLOR_RESET}")
            gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + self.gold_value
            check_achievements(character)
            return True  # Remove from inventory after collecting

        elif self.treasure_type == 'stat_boost':
            # Apply permanent stat boosts
            for stat, amount in self.benefit.items():
                # Handle properties that don't have setters
                if stat == 'defense':
                    character._base_defense += amount
                    add_log(f"{COLOR_GREEN}Defense increased by {amount}! Now: {character.defense}{COLOR_RESET}")
                elif stat == 'attack':
                    character._base_attack += amount
                    add_log(f"{COLOR_GREEN}Attack increased by {amount}! Now: {character.attack}{COLOR_RESET}")
                elif hasattr(character, stat):
                    current = getattr(character, stat)
                    setattr(character, stat, current + amount)
                    add_log(f"{COLOR_GREEN}{stat.capitalize()} increased by {amount}! Now: {getattr(character, stat)}{COLOR_RESET}")
            add_log(f"{COLOR_GREEN}You absorbed the power of {self.name}!{COLOR_RESET}")
            return True  # Remove after use

        elif self.treasure_type in ['usable', 'passive']:
            # Keep in inventory as a usable/equipable item
            add_log(f"{COLOR_CYAN}You obtained {self.name}!{COLOR_RESET}")
            if self.is_unique:
                add_log(f"{COLOR_YELLOW} This is a legendary unique treasure! {COLOR_RESET}")
            return False  # Keep in inventory

        return True

    def use(self, character, my_tower=None):
        """Use the treasure item"""

        if self.treasure_type == 'passive':
            # Toggle equip/unequip using accessory slots
            if self.is_equipped:
                # Find which slot it's in and unequip
                for i, acc in enumerate(character.equipped_accessories):
                    if acc == self:
                        character.unequip_accessory(i)
                        return False
                # Fallback if not found in slots
                self.is_equipped = False
                add_log(f"{COLOR_YELLOW}Unequipped {self.name}.{COLOR_RESET}")
            else:
                # Equip to first available slot
                character.equip_accessory(self)
            return False  # Not consumed

        elif self.treasure_type == 'usable' and self.use_effect:
            # Call the custom use effect function
            result = self.use_effect(character, my_tower)
            return result  # Function determines if consumed

        else:
            add_log(f"{self.name} cannot be used directly.")
            return False


class Towel(Item):
    """
    A towel - the most massively useful thing an adventurer can have!
    Inspired by NetHack and The Hitchhiker's Guide to the Galaxy.
    
    Uses:
    - Equip to blind yourself (protection from gaze attacks)
    - Apply to wipe face (cure blindness from cream pies, venom, etc.)
    - Apply to dry slippery hands (cure slippery status)
    - When wet, can be wielded as a weak weapon
    - Wet towel provides some protection from poison/gas
    
    Wetness levels: 0-7 (0=dry, 7=soaking)
    """
    def __init__(self, name="Towel", description="A soft cotton towel. Don't panic.", 
                 value=5, level=0, wetness=0):
        super().__init__(name, description, value, level)
        self.wetness = wetness  # 0-7, 0=dry, 7=soaking wet
        self.is_worn = False  # Worn over face = blinded
        self.elemental_strength = ["Water"]  # For combat calculations
    
    @property
    def attack_bonus(self):
        """Attack bonus based on wetness - wet towels hit harder!"""
        if self.wetness == 0:
            return 1  # Dry towel = minimal damage
        # Wet towel: 1 to wetness damage, capped at 6
        return min(6, self.wetness)
    
    def __repr__(self):
        wetness_desc = self._get_wetness_description()
        worn_str = " [WORN]" if self.is_worn else ""
        return f"Towel(name='{self.name}', wetness={self.wetness} ({wetness_desc}){worn_str})"
    
    def _get_wetness_description(self):
        """Get text description of wetness level."""
        if self.wetness == 0:
            return "dry"
        elif self.wetness <= 2:
            return "moist"
        elif self.wetness <= 4:
            return "damp"
        elif self.wetness <= 6:
            return "wet"
        else:
            return "soaking"
    
    def get_display_name(self):
        """Get name with wetness indicator."""
        wetness_desc = self._get_wetness_description()
        if self.wetness > 0:
            return f"{wetness_desc} {self.name}"
        return self.name
    
    def wet(self, amount=None):
        """Make the towel wet. Amount is 1-7 if not specified."""
        if amount is None:
            amount = random.randint(1, 7)
        old_wetness = self.wetness
        self.wetness = min(7, self.wetness + amount)
        if self.wetness > old_wetness:
            add_log(f"{COLOR_CYAN}Your towel gets wet! ({self._get_wetness_description()}){COLOR_RESET}")
    
    def dry_one_level(self):
        """Reduce wetness by 1."""
        if self.wetness > 0:
            self.wetness -= 1
            if self.wetness == 0:
                add_log(f"{COLOR_GREY}Your towel has dried out.{COLOR_RESET}")
    
    def use(self, character, my_tower=None):
        """
        Use the towel. Multiple actions available:
        - If not worn: wear it (blinds self)
        - If worn: remove it (unblind)
        - Apply to wipe face/hands
        """
        
        if self.is_worn:
            # Remove the towel
            self.is_worn = False
            # Remove self-imposed blindness
            if 'Towel Blindfold' in character.status_effects:
                character.remove_status_effect('Towel Blindfold')
            add_log(f"{COLOR_GREEN}You remove the towel from your face. You can see again!{COLOR_RESET}")
            return False  # Not consumed
        
        # Not worn - offer options
        add_log(f"{COLOR_CYAN}What do you want to do with the towel?{COLOR_RESET}")
        add_log(f"  1. Wear it over your face (blind yourself)")
        add_log(f"  2. Wipe your face (cure face-based blindness)")
        add_log(f"  3. Wipe your hands (cure slippery hands)")
        add_log(f"  4. Cancel")
        
        # Set up towel action mode
        gs.prompt_cntl = "towel_action_mode"
        gs.active_towel_item = self
        return False  # Not consumed yet
    
    def wear(self, character):
        """Wear the towel over face, blinding self."""
        self.is_worn = True
        # Add blindness effect (self-imposed, removable)
        character.add_status_effect(
            effect_name='Towel Blindfold',
            duration=9999,  # Permanent until removed
            effect_type='blindness',
            magnitude=1,
            description='You have a towel over your face'
        )
        add_log(f"{COLOR_PURPLE}You wrap the towel around your face.{COLOR_RESET}")
        add_log(f"{COLOR_GREY}You can't see anything, but you're protected from gaze attacks!{COLOR_RESET}")
    
    def wipe_face(self, character):
        """Wipe face to cure certain types of blindness."""
        # Check for curable blindness effects
        curable_effects = ['Blinded', 'Cream Pie', 'Venom Blind', 'Flash Blind']
        cured_something = False
        
        for effect_name in curable_effects:
            if effect_name in character.status_effects:
                character.remove_status_effect(effect_name)
                cured_something = True
                add_log(f"{COLOR_GREEN}You wipe the {effect_name.lower()} from your face!{COLOR_RESET}")
        
        if not cured_something:
            add_log(f"{COLOR_GREY}Your face feels clean now.{COLOR_RESET}")
        
        # Using towel dries it by 1 level
        self.dry_one_level()
    
    def wipe_hands(self, character):
        """Wipe hands to cure slippery status."""
        if 'Slippery Hands' in character.status_effects:
            character.remove_status_effect('Slippery Hands')
            add_log(f"{COLOR_GREEN}You dry your hands. You can grip your weapons properly again!{COLOR_RESET}")
        elif 'Greasy' in character.status_effects:
            character.remove_status_effect('Greasy')
            add_log(f"{COLOR_GREEN}You wipe the grease from your hands!{COLOR_RESET}")
        else:
            add_log(f"{COLOR_GREY}Your hands feel dry now.{COLOR_RESET}")
        
        # Using towel dries it by 1 level
        self.dry_one_level()
    
    def get_weapon_damage(self):
        """Get damage when used as a weapon (when wet)."""
        if self.wetness == 0:
            return 1  # Dry towel = minimal damage
        # Wet towel deals 1 to wetness damage, capped at 6
        return min(6, random.randint(1, self.wetness))
    
    def provides_gas_protection(self):
        """Check if towel provides protection from gas/poison clouds."""
        # Wet towel over face provides protection
        return self.is_worn and self.wetness >= 3


class Spell(Item):
    def __init__(self, name, description="", mana_cost=0, damage_type='Physical', base_power=0, level=0, spell_type='damage',
                 status_effect_name=None, status_effect_duration=0, status_effect_type=None, status_effect_magnitude=0):
        # Call parent Item class's __init__. Value is placeholder based on mana_cost.
        super().__init__(name, description, value=mana_cost * 2, level=level)
        self.mana_cost = mana_cost
        self.damage_type = damage_type
        self.base_power = base_power
        self.spell_type = spell_type
        self.status_effect_name = status_effect_name
        self.status_effect_duration = status_effect_duration
        self.status_effect_type = status_effect_type
        self.status_effect_magnitude = status_effect_magnitude

    def __repr__(self):
        base_repr = f"Spell(name='{self.name}', mana_cost={self.mana_cost}, level={self.level}, spell_type='{self.spell_type}')"
        if self.spell_type == 'damage':
            base_repr += f", damage_type='{self.damage_type}', base_power={self.base_power}"
        elif self.spell_type == 'healing':
            base_repr += f", base_power={self.base_power}"
        elif self.spell_type in ['remove_status', 'add_status_effect']:
            base_repr += f", status_effect_name='{self.status_effect_name}'"
            if self.status_effect_type:
                base_repr += f", status_effect_type='{self.status_effect_type}'"
            if self.status_effect_magnitude > 0:
                base_repr += f", status_effect_magnitude={self.status_effect_magnitude}"
            if self.status_effect_duration > 0:
                base_repr += f", status_effect_duration={self.status_effect_duration}"
        return base_repr

# Global list of Spell templates
# EXPANDED SPELL LIST
# Replace your existing SPELL_TEMPLATES list with this expanded version:

SPELL_TEMPLATES = [
    # ===== LEVEL 0 SPELLS (1 slot each) - Basic Cantrips =====
    Spell(name="Ice Shard", description="Launches a sharp shard of ice.", mana_cost=8, damage_type='Ice', base_power=15, level=0),
    Spell(name="Spark", description="A tiny jolt of electricity.", mana_cost=5, damage_type='Wind', base_power=12, level=0),
    Spell(name="Stone Throw", description="Magically hurls a small rock.", mana_cost=6, damage_type='Earth', base_power=13, level=0),
    Spell(name="Minor Heal", description="Restores a tiny amount of health.", mana_cost=8, damage_type='Healing', base_power=15, level=0, spell_type='healing'),
    Spell(name="Shadow Bolt", description="A weak bolt of shadow energy.", mana_cost=7, damage_type='Darkness', base_power=14, level=0),
    Spell(name="Light Ray", description="A beam of pure light.", mana_cost=7, damage_type='Light', base_power=14, level=0),

    # ===== LEVEL 1 SPELLS (2 slots each) - Intermediate =====
    Spell(name="Fireball", description="Hurls a ball of fire at the enemy.", mana_cost=10, damage_type='Fire', base_power=20, level=1),
    Spell(name="Heal", description="Restores a small amount of health.", mana_cost=12, damage_type='Healing', base_power=25, level=1, spell_type='healing'),
    Spell(name="Water Blast", description="A pressurized stream of water.", mana_cost=11, damage_type='Water', base_power=22, level=1),
    Spell(name="Wind Slash", description="A cutting blade of wind.", mana_cost=10, damage_type='Wind', base_power=21, level=1),
    Spell(name="Acid Splash", description="Corrosive acid burns the target.", mana_cost=12, damage_type='Earth', base_power=23, level=1),
    Spell(name="Mind Spike", description="A sharp psionic attack.", mana_cost=13, damage_type='Psionic', base_power=24, level=1),
    Spell(name="Purify", description="Cleanses poison from the caster.", mana_cost=15, level=1, spell_type='remove_status', status_effect_name='Poison'),
    Spell(name="Cure Weakness", description="Restores strength and vigor.", mana_cost=12, level=1, spell_type='add_status_effect', status_effect_name='Vigor', status_effect_duration=3, status_effect_type='attack_boost', status_effect_magnitude=5),

    # ===== LEVEL 2 SPELLS (2 slots each) - Advanced =====
    Spell(name="Thunder Clap", description="A concussive wave of sound.", mana_cost=15, damage_type='Physical', base_power=30, level=2),
    Spell(name="Darkness Bolt", description="Fires a bolt of pure shadow.", mana_cost=14, damage_type='Darkness', base_power=28, level=2),
    Spell(name="Ice Storm", description="A freezing blizzard strikes the enemy.", mana_cost=16, damage_type='Ice', base_power=32, level=2),
    Spell(name="Freedom", description="Removes the web effect from the caster.", mana_cost=18, level=2, spell_type='remove_status', status_effect_name='Web'),
    Spell(name="Battle Hymn", description="Inspires the caster with increased attack for a short time.", mana_cost=20, level=2, spell_type='add_status_effect', status_effect_name='Inspired', status_effect_duration=3, status_effect_type='attack_boost', status_effect_magnitude=10),
    Spell(name="Stone Skin", description="Hardens your skin like stone.", mana_cost=18, level=2, spell_type='add_status_effect', status_effect_name='Stone Skin', status_effect_duration=4, status_effect_type='defense_boost', status_effect_magnitude=8),
    Spell(name="Flame Lance", description="A concentrated spear of flame.", mana_cost=17, damage_type='Fire', base_power=33, level=2),
    Spell(name="Lightning Bolt", description="A powerful bolt of electricity.", mana_cost=16, damage_type='Wind', base_power=31, level=2),
    Spell(name="Greater Heal", description="Restores a moderate amount of health.", mana_cost=18, damage_type='Healing', base_power=40, level=2, spell_type='healing'),

    # ===== LEVEL 3 SPELLS (3 slots each) - Expert =====
    Spell(name="Holy Light", description="Blinds and damages unholy foes.", mana_cost=18, damage_type='Holy', base_power=35, level=3),
    Spell(name="Meteor Strike", description="Summons a falling meteor.", mana_cost=22, damage_type='Fire', base_power=45, level=3),
    Spell(name="Regeneration", description="Heals the caster over several turns.", mana_cost=25, level=3, spell_type='add_status_effect', status_effect_name='Regenerating', status_effect_duration=4, status_effect_type='heal_over_time', status_effect_magnitude=8),
    Spell(name="Chain Lightning", description="Lightning that bounces between foes.", mana_cost=24, damage_type='Wind', base_power=42, level=3),
    Spell(name="Blizzard", description="A devastating ice storm.", mana_cost=23, damage_type='Ice', base_power=43, level=3),
    Spell(name="Earthquake", description="Shakes the ground violently.", mana_cost=25, damage_type='Earth', base_power=46, level=3),
    Spell(name="Mind Blast", description="Overwhelming psionic power.", mana_cost=21, damage_type='Psionic', base_power=40, level=3),
    Spell(name="Shadow Strike", description="A deadly strike from the shadows.", mana_cost=20, damage_type='Darkness', base_power=38, level=3),
    Spell(name="Divine Shield", description="Grants powerful protection.", mana_cost=28, level=3, spell_type='add_status_effect', status_effect_name='Divine Shield', status_effect_duration=3, status_effect_type='defense_boost', status_effect_magnitude=15),
    Spell(name="Mass Heal", description="Restores a large amount of health.", mana_cost=30, damage_type='Healing', base_power=60, level=3, spell_type='healing'),

    # ===== LEVEL 4 SPELLS (3 slots each) - Master =====
    Spell(name="Inferno", description="An all-consuming firestorm.", mana_cost=35, damage_type='Fire', base_power=55, level=4),
    Spell(name="Absolute Zero", description="Freeze the enemy solid.", mana_cost=33, damage_type='Ice', base_power=52, level=4),
    Spell(name="Tsunami", description="A massive wave crashes down.", mana_cost=34, damage_type='Water', base_power=53, level=4),
    Spell(name="Void Beam", description="Erases matter with dark energy.", mana_cost=32, damage_type='Darkness', base_power=50, level=4),
    Spell(name="Holy Smite", description="Divine wrath incarnate.", mana_cost=36, damage_type='Holy', base_power=56, level=4),
    Spell(name="Psychic Scream", description="Tears at the mind itself.", mana_cost=31, damage_type='Psionic', base_power=48, level=4),
    Spell(name="Full Restore", description="Completely restores health.", mana_cost=40, damage_type='Healing', base_power=100, level=4, spell_type='healing'),
    Spell(name="Titan's Strength", description="Grants enormous power.", mana_cost=38, level=4, spell_type='add_status_effect', status_effect_name='Titan Strength', status_effect_duration=5, status_effect_type='attack_boost', status_effect_magnitude=20),
    Spell(name="Clarity", description="Removes all negative status effects.", mana_cost=35, level=4, spell_type='remove_status', status_effect_name='All'),
    Spell(name="Time Stop", description="Slows time around the caster.", mana_cost=45, level=4, spell_type='add_status_effect', status_effect_name='Hasted', status_effect_duration=3, status_effect_type='attack_boost', status_effect_magnitude=25),

    # ===== LEVEL 5 SPELLS (3 slots each) - Legendary =====
    Spell(name="Armageddon", description="The end of all things.", mana_cost=50, damage_type='Demonic', base_power=75, level=5),
    Spell(name="Supernova", description="The power of an exploding star.", mana_cost=48, damage_type='Fire', base_power=70, level=5),
    Spell(name="Black Hole", description="Draws enemies into oblivion.", mana_cost=52, damage_type='Darkness', base_power=72, level=5),
    Spell(name="Divine Intervention", description="The gods themselves aid you.", mana_cost=55, damage_type='Holy', base_power=80, level=5),
    Spell(name="Perfect Regeneration", description="Constant healing for many turns.", mana_cost=50, level=5, spell_type='add_status_effect', status_effect_name='Perfect Regen', status_effect_duration=8, status_effect_type='heal_over_time', status_effect_magnitude=15),
    Spell(name="Ultimate Shield", description="Near-invulnerability.", mana_cost=60, level=5, spell_type='add_status_effect', status_effect_name='Ultimate Shield', status_effect_duration=5, status_effect_type='defense_boost', status_effect_magnitude=30),
]


# 
# COMPLETE POTION TEMPLATES
# 

POTION_TEMPLATES = [
    #  HEALING POTIONS 
    Potion(
        name="Minor Healing Potion",
        description="A small vial of red liquid that heals minor wounds.",
        value=30,
        level=0,
        potion_type='healing',
        effect_magnitude=30
    ),
    Potion(
        name="Healing Potion",
        description="A flask of red liquid that heals moderate wounds.",
        value=50,
        level=1,
        potion_type='healing',
        effect_magnitude=50
    ),
    Potion(
        name="Greater Healing Potion",
        description="A large flask of crimson liquid that heals significant wounds.",
        value=80,
        level=3,
        potion_type='healing',
        effect_magnitude=80
    ),
    Potion(
        name="Superior Healing Potion",
        description="A crystalline vial of ruby liquid that heals major wounds.",
        value=120,
        level=5,
        potion_type='healing',
        effect_magnitude=120
    ),
    Potion(
        name="Master Healing Potion",
        description="A glowing vial of brilliant red liquid that heals the most grievous wounds.",
        value=180,
        level=7,
        potion_type='healing',
        effect_magnitude=180
    ),

    #  MANA POTIONS 
    Potion(
        name="Minor Mana Potion",
        description="A small vial of blue liquid that restores a small amount of mana.",
        value=30,
        level=0,
        potion_type='mana',
        effect_magnitude=25
    ),
    Potion(
        name="Mana Potion",
        description="A flask of blue liquid that restores moderate mana.",
        value=50,
        level=1,
        potion_type='mana',
        effect_magnitude=40
    ),
    Potion(
        name="Greater Mana Potion",
        description="A large flask of deep blue liquid that restores significant mana.",
        value=80,
        level=3,
        potion_type='mana',
        effect_magnitude=60
    ),
    Potion(
        name="Superior Mana Potion",
        description="A crystalline vial of sapphire liquid that restores major mana.",
        value=120,
        level=5,
        potion_type='mana',
        effect_magnitude=90
    ),

    #  STAT BUFF POTIONS 
    Potion(
        name="Potion of Strength",
        description="Increases physical power for a short time.",
        value=60,
        level=2,
        potion_type='strength',
        effect_magnitude=10,
        duration=6
    ),
    Potion(
        name="Potion of Greater Strength",
        description="Greatly increases physical power.",
        value=100,
        level=4,
        potion_type='strength',
        effect_magnitude=20,
        duration=8
    ),
    Potion(
        name="Potion of Dexterity",
        description="Increases agility and precision for a short time.",
        value=60,
        level=2,
        potion_type='dexterity',
        effect_magnitude=10,
        duration=6
    ),
    Potion(
        name="Potion of Intelligence",
        description="Increases mental acuity and magical power.",
        value=60,
        level=2,
        potion_type='intelligence',
        effect_magnitude=10,
        duration=6
    ),
    Potion(
        name="Potion of Defense",
        description="Hardens the body against physical attacks.",
        value=70,
        level=2,
        potion_type='defense',
        effect_magnitude=15,
        duration=6
    ),

    #  NEW SPECIAL POTIONS 
    Potion(
        name="Potion of Invisibility",
        description="Makes you invisible, allowing cowards to avoid combat encounters.",
        value=150,
        level=4,
        potion_type='invisibility',
        effect_magnitude=0,
        duration=5
    ),
    Potion(
        name="Potion of True Sight",
        description="Reveals hidden things and grants supernatural vision.",
        value=120,
        level=3,
        potion_type='true_sight',
        effect_magnitude=0,
        duration=8
    ),
    Potion(
        name="Potion of Berserker Rage",
        description="Massive attack boost, but reduces defense. High risk, high reward!",
        value=100,
        level=3,
        potion_type='berserker',
        effect_magnitude=30,
        duration=5
    ),
    Potion(
        name="Potion of Regeneration",
        description="Gradually heals wounds over time.",
        value=110,
        level=3,
        potion_type='regeneration',
        effect_magnitude=8,  # HP per turn
        duration=10
    ),
    Potion(
        name="Potion of Clarity",
        description="Removes all negative status effects and restores mana.",
        value=130,
        level=4,
        potion_type='clarity',
        effect_magnitude=30,  # Mana restored
        duration=0
    ),
    Potion(
        name="Potion of Frost Armor",
        description="Coats you in protective ice that damages attackers. But it doesn't feel cool, just kind of refreshing.",
        value=140,
        level=4,
        potion_type='frost_armor',
        effect_magnitude=15,  # Damage reflected
        duration=7
    ),
    Potion(
        name="Potion of Giant's Strength",
        description="Grants the strength of a giant for a short time.",
        value=160,
        level=5,
        potion_type='giant_strength',
        effect_magnitude=15,  # Temporary STR bonus
        duration=6
    ),
    Potion(
        name="Potion of Vampirism",
        description="Heal yourself by stealing life from enemies. Moral dilemmas to be solved later.",
        value=150,
        level=5,
        potion_type='vampirism',
        effect_magnitude=50,  # 50% lifesteal
        duration=8
    ),
    Potion(
        name="Potion of Fortune",
        description="Increases the quality and quantity of treasure found. Because you are greedy.",
        value=120,
        level=3,
        potion_type='fortune',
        effect_magnitude=50,  # 50% better loot
        duration=10
    ),
    Potion(
        name="Potion of Experience",
        description="Grants bonus experience from all sources.",
        value=140,
        level=4,
        potion_type='experience',
        effect_magnitude=50,  # 50% bonus XP
        duration=10
    ),
    Potion(
        name="Potion of Haste",
        description="Allows you to act twice as fast in combat.",
        value=180,
        level=6,
        potion_type='haste',
        effect_magnitude=2,
        duration=4
    ),
    Potion(
        name="Potion of Stone Skin",
        description="Your skin hardens like stone, reducing all damage.",
        value=130,
        level=4,
        potion_type='stone_skin',
        effect_magnitude=10,  # Flat damage reduction
        duration=8
    ),
    Potion(
        name="Potion of Fire Resistance",
        description="A red, warm liquid that protects against fire damage. Eat a hot pepper. Impress your dopey friends.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,  # 50% reduction
        duration=6,
        resistance_element='Fire'
    ),

    Potion(
        name="Potion of Ice Resistance",
        description="A frigid blue liquid that protects against ice damage. Of course it's blue.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Ice'
    ),

    Potion(
        name="Potion of Lightning Resistance",
        description="A crackling yellow liquid that protects against lightning damage. Tastes like pop rocks.",
        value=75,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Lightning'
    ),

    Potion(
        name="Potion of Water Resistance",
        description="A flowing aqua liquid that protects against water damage. Come on let's go party.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Water'
    ),

    Potion(
        name="Potion of Earth Resistance",
        description="A viscous brown liquid that protects against earth damage. You had me at viscous and brown.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Earth'
    ),

    Potion(
        name="Potion of Wind Resistance",
        description="A light, swirling liquid that protects against wind damage. Bascially a skinny drink.",
        value=70,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Wind'
    ),

    Potion(
        name="Potion of Holy Resistance",
        description="A golden liquid that protects against holy damage. You had me at golden liquid.",
        value=80,
        level=3,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Holy'
    ),

    Potion(
        name="Potion of Shadow Resistance",
        description="A dark, inky liquid that protects against darkness damage.",
        value=80,
        level=3,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Darkness'
    ),

    Potion(
        name="Potion of Poison Resistance",
        description="A green, bubbling liquid that protects against poison damage.",
        value=85,
        level=3,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Poison'
    ),

    Potion(
        name="Potion of Physical Resistance",
        description="A silvery liquid that hardens skin against physical attacks.",
        value=75,
        level=2,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Physical'
    ),

    Potion(
        name="Potion of Psionic Resistance",
        description="A shimmering purple liquid that shields the mind.",
        value=90,
        level=3,
        potion_type='resistance',
        effect_magnitude=50,
        duration=6,
        resistance_element='Psionic'
    ),

    #  GREATER RESISTANCE (75% reduction) 

    Potion(
        name="Greater Fire Resistance",
        description="A brilliant crimson elixir that grants powerful fire protection.",
        value=120,
        level=4,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Fire'
    ),

    Potion(
        name="Greater Ice Resistance",
        description="A crystalline blue elixir that grants powerful ice protection.",
        value=120,
        level=4,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Ice'
    ),

    Potion(
        name="Greater Lightning Resistance",
        description="An electrified golden elixir that grants powerful lightning protection.",
        value=125,
        level=4,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Lightning'
    ),

    Potion(
        name="Greater Shadow Resistance",
        description="A void-black elixir that grants powerful darkness protection.",
        value=130,
        level=5,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Darkness'
    ),

    Potion(
        name="Greater Poison Resistance",
        description="A luminous green elixir that grants powerful poison protection.",
        value=135,
        level=5,
        potion_type='resistance',
        effect_magnitude=75,
        duration=8,
        resistance_element='Poison'
    ),

    #  MULTI-ELEMENT RESISTANCE (30% to multiple) 

    Potion(
        name="Potion of Elemental Warding",
        description="A tri-colored liquid that protects against fire, ice, and lightning.",
        value=110,
        level=3,
        potion_type='resistance',
        effect_magnitude=30,  # Lower reduction but covers 3 elements
        duration=6,
        resistance_element='Multi'  # Special: Fire + Ice + Lightning
    ),

    Potion(
        name="Potion of Natural Warding",
        description="An earthy liquid that protects against earth, water, and wind.",
        value=100,
        level=3,
        potion_type='resistance',
        effect_magnitude=30,
        duration=6,
        resistance_element='Multi-Natural'  # Special: Earth + Water + Wind
    ),

    Potion(
        name="Potion of Arcane Warding",
        description="A mystical liquid that protects against holy, darkness, and psionic.",
        value=130,
        level=4,
        potion_type='resistance',
        effect_magnitude=30,
        duration=6,
        resistance_element='Multi-Arcane'  # Special: Holy + Darkness + Psionic
    ),

    #  UNIVERSAL RESISTANCE (25% to ALL) 

    Potion(
        name="Potion of Universal Resistance",
        description="A shimmering rainbow liquid that protects against all damage types.",
        value=180,
        level=6,
        potion_type='resistance',
        effect_magnitude=25,  # Lower but covers EVERYTHING
        duration=5,
        resistance_element='Universal'
    ),

    Potion(
        name="Elixir of Invulnerability",
        description="A legendary elixir that grants near-invulnerability to all damage.",
        value=250,
        level=8,
        potion_type='resistance',
        effect_magnitude=40,  # Stronger universal resistance
        duration=4,
        resistance_element='Universal'
    ),

    # === DEEP FLOOR POTIONS (Level 10+) ===

    # Higher tier healing
    Potion(name="Supreme Healing Potion", description="Restores 250 HP.", value=250, level=10, potion_type='healing', effect_magnitude=250),
    Potion(name="Divine Healing Potion", description="Restores 400 HP.", value=400, level=15, potion_type='healing', effect_magnitude=400),
    Potion(name="Godly Healing Potion", description="Restores 600 HP.", value=600, level=20, potion_type='healing', effect_magnitude=600),

    # Higher tier mana
    Potion(name="Supreme Mana Potion", description="Restores 120 mana.", value=200, level=10, potion_type='mana', effect_magnitude=120),
    Potion(name="Divine Mana Potion", description="Restores 180 mana.", value=350, level=15, potion_type='mana', effect_magnitude=180),

    # Combat buff potions - bigger magnitudes for deep floors
    Potion(name="Potion of Titan Strength", description="Massive strength surge.", value=200, level=10, potion_type='strength', effect_magnitude=25, duration=10),
    Potion(name="Potion of Dragon Strength", description="Strength of an ancient dragon.", value=350, level=15, potion_type='strength', effect_magnitude=35, duration=10),
    Potion(name="Potion of God Strength", description="Divine power flows through you.", value=500, level=20, potion_type='strength', effect_magnitude=50, duration=10),
    Potion(name="Potion of Cat Reflexes", description="Lightning-fast reflexes.", value=200, level=10, potion_type='dexterity', effect_magnitude=25, duration=10),
    Potion(name="Potion of Wind Reflexes", description="Move like the wind itself.", value=350, level=15, potion_type='dexterity', effect_magnitude=35, duration=10),
    Potion(name="Potion of Iron Fortress", description="Skin hardens like iron.", value=200, level=10, potion_type='defense', effect_magnitude=25, duration=10),
    Potion(name="Potion of Adamant Fortress", description="Become nearly impenetrable.", value=350, level=15, potion_type='defense', effect_magnitude=40, duration=10),
    Potion(name="Potion of Diamond Fortress", description="The ultimate defensive ward.", value=500, level=20, potion_type='defense', effect_magnitude=60, duration=10),

    # War elixirs - huge short combat buffs
    Potion(name="War Elixir", description="Doubles your combat prowess briefly.", value=300, level=12, potion_type='berserker', effect_magnitude=50, duration=6),
    Potion(name="Warlord Elixir", description="Fight like a god of war.", value=600, level=18, potion_type='berserker', effect_magnitude=80, duration=6),

    # Permanent stat elixirs - rare, expensive, one-time boosts
    Potion(name="Elixir of Might", description="Permanently increases STR by 2.", value=800, level=15, potion_type='permanent_strength', effect_magnitude=2),
    Potion(name="Elixir of Grace", description="Permanently increases DEX by 2.", value=800, level=15, potion_type='permanent_dexterity', effect_magnitude=2),
    Potion(name="Elixir of Brilliance", description="Permanently increases INT by 2.", value=800, level=15, potion_type='permanent_intelligence', effect_magnitude=2),
    Potion(name="Greater Elixir of Might", description="Permanently increases STR by 4.", value=2000, level=25, potion_type='permanent_strength', effect_magnitude=4),
    Potion(name="Greater Elixir of Grace", description="Permanently increases DEX by 4.", value=2000, level=25, potion_type='permanent_dexterity', effect_magnitude=4),
    Potion(name="Greater Elixir of Brilliance", description="Permanently increases INT by 4.", value=2000, level=25, potion_type='permanent_intelligence', effect_magnitude=4),
    Potion(name="Supreme Elixir of Might", description="Permanently increases STR by 6.", value=5000, level=35, potion_type='permanent_strength', effect_magnitude=6),
    Potion(name="Supreme Elixir of Grace", description="Permanently increases DEX by 6.", value=5000, level=35, potion_type='permanent_dexterity', effect_magnitude=6),
    Potion(name="Supreme Elixir of Brilliance", description="Permanently increases INT by 6.", value=5000, level=35, potion_type='permanent_intelligence', effect_magnitude=6),
    Potion(name="Elixir of Vitality", description="Permanently increases max HP by 20.", value=1200, level=15, potion_type='permanent_health', effect_magnitude=20),
    Potion(name="Greater Elixir of Vitality", description="Permanently increases max HP by 40.", value=3000, level=25, potion_type='permanent_health', effect_magnitude=40),
    Potion(name="Supreme Elixir of Vitality", description="Permanently increases max HP by 75.", value=6000, level=35, potion_type='permanent_health', effect_magnitude=75),

    # Deep-floor healing potions
    Potion(name="Heroic Healing Potion", description="A radiant vial that mends grievous wounds.", value=250, level=10, potion_type='healing', effect_magnitude=200),
    Potion(name="Legendary Healing Potion", description="A shimmering elixir of extraordinary restoration.", value=500, level=15, potion_type='healing', effect_magnitude=350),
    Potion(name="Mythic Healing Potion", description="Liquid starlight that knits flesh and bone.", value=800, level=25, potion_type='healing', effect_magnitude=500),

    # Deep-floor mana potions
    Potion(name="Master Mana Potion", description="A deep indigo draught of arcane power.", value=200, level=10, potion_type='mana', effect_magnitude=120),
    Potion(name="Supreme Mana Potion", description="Liquid moonlight that floods the mind with power.", value=400, level=20, potion_type='mana', effect_magnitude=200),

    # Tiered combat buff potions - Wrath line (ATK boost)
    Potion(name="Potion of Wrath", description="Battle fury surges through your veins.", value=300, level=10, potion_type='strength', effect_magnitude=25, duration=10),
    Potion(name="Potion of Titan's Wrath", description="The rage of ancient titans empowers your strikes.", value=800, level=20, potion_type='strength', effect_magnitude=50, duration=12),
    Potion(name="Potion of Mythic Wrath", description="Primordial fury distilled to its purest form.", value=1500, level=35, potion_type='strength', effect_magnitude=75, duration=14),

    # Tiered combat buff potions - Guard line (DEF boost)
    Potion(name="Potion of Iron Will", description="Your resolve hardens like iron.", value=300, level=10, potion_type='defense', effect_magnitude=20, duration=10),
    Potion(name="Potion of Titan's Guard", description="The endurance of titans shields you from harm.", value=800, level=20, potion_type='defense', effect_magnitude=40, duration=12),
    Potion(name="Potion of Mythic Guard", description="An impenetrable aura of ancient protection.", value=1500, level=35, potion_type='defense', effect_magnitude=60, duration=14),

    # Tiered Greater Dexterity and Intelligence buffs
    Potion(name="Potion of Greater Dexterity", description="Greatly increases agility and reaction speed.", value=200, level=8, potion_type='dexterity', effect_magnitude=20, duration=8),
    Potion(name="Potion of Superior Dexterity", description="Move with supernatural speed and precision.", value=500, level=18, potion_type='dexterity', effect_magnitude=35, duration=10),
    Potion(name="Potion of Greater Intelligence", description="Greatly increases mental focus and magical potency.", value=200, level=8, potion_type='intelligence', effect_magnitude=20, duration=8),
    Potion(name="Potion of Superior Intelligence", description="Arcane brilliance floods your consciousness.", value=500, level=18, potion_type='intelligence', effect_magnitude=35, duration=10),

    # Deep-floor special combat potions
    Potion(name="Potion of Greater Berserker Rage", description="Overwhelming fury. Massive attack, reduced defense.", value=400, level=15, potion_type='berserker', effect_magnitude=50, duration=6),
    Potion(name="Greater Potion of Haste", description="Time seems to slow around you.", value=400, level=15, potion_type='haste', effect_magnitude=2, duration=6),
    Potion(name="Greater Potion of Stone Skin", description="Your body becomes nearly impervious to harm.", value=350, level=15, potion_type='stone_skin', effect_magnitude=20, duration=10),
    Potion(name="Potion of Greater Frost Armor", description="A shell of enchanted ice surrounds you.", value=400, level=15, potion_type='frost_armor', effect_magnitude=25, duration=10),

    # Higher tier regen and vampirism
    Potion(name="Greater Regeneration Potion", description="Powerful sustained healing.", value=200, level=10, potion_type='regeneration', effect_magnitude=15, duration=12),
    Potion(name="Supreme Regeneration Potion", description="Incredible sustained healing.", value=500, level=20, potion_type='regeneration', effect_magnitude=25, duration=15),
    Potion(name="Greater Vampirism Potion", description="Drain life with every blow.", value=300, level=12, potion_type='vampirism', effect_magnitude=75, duration=10),
    Potion(name="Supreme Vampirism Potion", description="Feast on the lifeforce of enemies.", value=600, level=20, potion_type='vampirism', effect_magnitude=100, duration=12),
]

def player_has_item_type(player_character, item_class):
    """Check if player has item in equipment or inventory."""
    if player_character.equipped_weapon and isinstance(player_character.equipped_weapon, item_class):
        return True
    if player_character.equipped_armor and isinstance(player_character.equipped_armor, item_class):
        return True
    for item in player_character.inventory.items:
        if isinstance(item, item_class):
            return True
    return False

# 
# POTION EFFECT PROCESSING HOOKS
# 

def process_potion_effects_in_combat(character, active_monster):
    """
    Call this during combat to process special potion effects.
    Add to your process_combat_action() function.
    """

    # Check for Invisibility - monsters can't attack invisible players
    if 'Invisibility' in character.status_effects:
        add_log(f"{COLOR_PURPLE}[You are invisible - the enemy cannot see you!]{COLOR_RESET}")
        return True  # Skip monster attack

    # Check for Haste - player can act twice
    if 'Haste' in character.status_effects:
        # You'll need to implement double-action logic in your combat system
        pass

    # Check for Vampirism - heal on damage dealt
    if 'Vampiric' in character.status_effects:
        lifesteal_pct = character.status_effects['Vampiric'].magnitude
        # After dealing damage, heal character based on percentage
        # Example: heal_amount = int(damage_dealt * lifesteal_pct / 100)
        pass

    # Check for Frost Armor - reflect damage to attacker
    if 'Frost Armor' in character.status_effects:
        reflect_damage = character.status_effects['Frost Armor'].magnitude
        if gs.active_monster:
            gs.active_monster.take_damage(reflect_damage, "Ice")
            add_log(f"{COLOR_CYAN}Frost Armor deals {reflect_damage} ice damage to {gs.active_monster.name}!{COLOR_RESET}")

    # Check for Stone Skin - reduce incoming damage
    if 'Stone Skin' in character.status_effects:
        reduction = character.status_effects['Stone Skin'].magnitude
        # Reduce damage in your damage calculation
        # Example: final_damage = max(0, damage - reduction)
        pass

    return False  # Normal combat flow


def process_potion_effects_on_monster_defeat(character, monster):
    """
    Call this when a monster is defeated to process loot/XP bonuses.
    Add to your monster defeat handler.
    """

    # Check for Fortune - better loot
    if 'Fortune' in character.status_effects:
        bonus_pct = character.status_effects['Fortune'].magnitude
        # Increase gold drop
        # Example: gold_drop = int(gold_drop * (1 + bonus_pct / 100))
        add_log(f"{COLOR_YELLOW}[Fortune] +{bonus_pct}% gold from loot!{COLOR_RESET}")

    # Check for Experience Boost
    if 'Experience Boost' in character.status_effects:
        bonus_pct = character.status_effects['Experience Boost'].magnitude
        # Increase XP gained
        # Example: xp_gain = int(xp_gain * (1 + bonus_pct / 100))
        add_log(f"{COLOR_PURPLE}[Experience Boost] +{bonus_pct}% XP gained!{COLOR_RESET}")


def process_regeneration_effect(character):
    """
    Call this each turn to process regeneration.
    Add to character.process_status_effects() or main game loop.
    """
    if 'Regeneration' in character.status_effects:
        heal_amount = character.status_effects['Regeneration'].magnitude
        old_health = character.health
        character.health = min(character.max_health, character.health + heal_amount)
        actual_heal = character.health - old_health
        if actual_heal > 0:
            add_log(f"{COLOR_GREEN}[Regeneration] +{actual_heal} HP{COLOR_RESET}")


def remove_giant_strength_on_expire(character, effect):
    """
    When Giant's Strength expires, restore original STR.
    Add to your status effect expiration handler.
    """
    if effect.effect_type == 'stat_boost_str':
        character.strength -= effect.magnitude
        add_log(f"{COLOR_YELLOW}Giant's Strength fades. Strength returns to {character.strength}.{COLOR_RESET}")

def _create_item_copy(item_obj):
    """Helper function to create a new instance of an item, preserving its specific class and attributes."""
    if isinstance(item_obj, Weapon):
        return Weapon(item_obj.name, item_obj.description, item_obj._base_attack_bonus, item_obj.value, item_obj.level, item_obj.upgrade_level, elemental_strength=item_obj.elemental_strength, upgrade_limit=item_obj.upgrade_limit)
    elif isinstance(item_obj, Armor):
        return Armor(item_obj.name, item_obj.description, item_obj._base_defense_bonus, item_obj.value, item_obj.level, item_obj.upgrade_level, elemental_strength=item_obj.elemental_strength, upgrade_limit=item_obj.upgrade_limit)
    elif isinstance(item_obj, Potion):
        # Updated for new Potion attributes including count
        return Potion(name=item_obj.name, description=item_obj.description, value=item_obj.value, level=item_obj.level,
                      potion_type=item_obj.potion_type, effect_magnitude=item_obj.effect_magnitude, duration=item_obj.duration, resistance_element=item_obj.resistance_element, count=getattr(item_obj, 'count', 1))
    elif isinstance(item_obj, Scroll):
        return Scroll(item_obj.name, item_obj.description, item_obj.effect_description, item_obj.value, item_obj.level, item_obj.scroll_type, count=getattr(item_obj, 'count', 1))
    elif isinstance(item_obj, Flare):
        return Flare(item_obj.name, item_obj.description, item_obj.count, item_obj.light_radius, item_obj.value, item_obj.level)
    elif isinstance(item_obj, Lantern):
        return Lantern(item_obj.name, item_obj.description, item_obj.fuel_amount, item_obj.light_radius, item_obj.value, item_obj.level)
    elif isinstance(item_obj, LanternFuel):
        return LanternFuel(item_obj.name, item_obj.description, item_obj.value, item_obj.level, item_obj.fuel_restore_amount, count=getattr(item_obj, 'count', 1))
    elif isinstance(item_obj, Ingredient):
        return Ingredient(item_obj.name, item_obj.description, item_obj.value, item_obj.level, item_obj.ingredient_type, count=getattr(item_obj, 'count', 1))
    elif isinstance(item_obj, Treasure):
        # FIX: Include all Treasure attributes
        return Treasure(
            name=item_obj.name,
            description=item_obj.description,
            gold_value=item_obj.gold_value,
            value=item_obj.value,
            benefit=item_obj.benefit.copy() if isinstance(item_obj.benefit, dict) else item_obj.benefit,  # Deep copy dict
            level=item_obj.level,
            treasure_type=item_obj.treasure_type,
            is_unique=item_obj.is_unique,
            use_effect=item_obj.use_effect,  # Function reference
            passive_effect=item_obj.passive_effect
        )
    elif isinstance(item_obj, Spell):
        return Spell(name=item_obj.name, description=item_obj.description, mana_cost=item_obj.mana_cost, damage_type=item_obj.damage_type, base_power=item_obj.base_power, level=item_obj.level, spell_type=item_obj.spell_type,
                     status_effect_name=item_obj.status_effect_name, status_effect_duration=item_obj.status_effect_duration, status_effect_type=item_obj.status_effect_type, status_effect_magnitude=item_obj.status_effect_magnitude)
    elif isinstance(item_obj, Towel):
        return Towel(name=item_obj.name, description=item_obj.description, value=item_obj.value, level=item_obj.level, wetness=item_obj.wetness)
    elif isinstance(item_obj, CookingKit):
        return CookingKit(name=item_obj.name, description=item_obj.description, value=item_obj.value, level=item_obj.level)
    elif isinstance(item_obj, CuringKit):
        return CuringKit(name=item_obj.name, description=item_obj.description, value=item_obj.value, level=item_obj.level)
    elif isinstance(item_obj, Meat):
        new_meat = Meat(
            name=item_obj.name, description=item_obj.description, value=item_obj.value, level=item_obj.level,
            monster_name=item_obj.monster_name, is_cooked=item_obj.is_cooked, nutrition=item_obj.nutrition,
            rot_timer=item_obj.rot_timer, cut=item_obj.cut, descriptor=item_obj.descriptor, count=getattr(item_obj, 'count', 1)
        )
        new_meat.is_rotten = item_obj.is_rotten
        return new_meat
    elif isinstance(item_obj, Sausage):
        new_sausage = Sausage(
            name=item_obj.name, description=item_obj.description, value=item_obj.value, level=item_obj.level,
            nutrition=item_obj.nutrition, count=getattr(item_obj, 'count', 1),
            monster_source=getattr(item_obj, 'monster_source', 'Generic'),
            sausage_style=getattr(item_obj, 'sausage_style', 'Bratwurst'),
            is_spicy=getattr(item_obj, 'is_spicy', False),
            spice_level=getattr(item_obj, 'spice_level', 0),
        )
        return new_sausage
    elif isinstance(item_obj, Food):
        return Food(name=item_obj.name, description=item_obj.description, value=item_obj.value, level=item_obj.level,
                    nutrition=item_obj.nutrition, count=getattr(item_obj, 'count', 1))
    else:
        return Item(item_obj.name, item_obj.description, item_obj.value, item_obj.level)

