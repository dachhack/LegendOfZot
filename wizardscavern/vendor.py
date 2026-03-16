"""
vendor.py - Vendor system for Wizard's Cavern

Contains the Vendor class, vendor name/message data, magic shop logic,
and all vendor interaction functions (buy, sell, identify, repair).

Usage:
    from .vendor import Vendor, handle_starting_shop, handle_vendor_shop,
                       process_vendor_action, process_sell_quantity,
                       reveal_adjacent_walls
"""

import random

from . import game_state as gs
from .game_state import (
    add_log,
    COLOR_RED, COLOR_GREEN, COLOR_RESET, COLOR_PURPLE,
    COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_GREY,
    BOLD, normal_int_range, get_article,
)

# Item classes and item functions
from .items import (
    Item, Potion, Scroll, Spell, Weapon, Armor,
    Lantern, LanternFuel, Towel, Food, Flare, Ingredient,
    _create_item_copy,
    is_item_identified, identify_item,
    get_vendor_identify_cost, get_item_display_name,
    get_repair_cost,
)
from .characters import Inventory, get_sorted_inventory
from .item_templates import POTION_TEMPLATES, SCROLL_TEMPLATES, SPELL_TEMPLATES
from .achievements import check_achievements


def _get_enhanced_weapon(floor_level):
    """Lazy import wrapper to avoid circular imports with game_systems."""
    from .game_systems import create_random_enhanced_weapon
    return create_random_enhanced_weapon(floor_level)


def _get_enhanced_armor(floor_level):
    """Lazy import wrapper to avoid circular imports with game_systems."""
    from .game_systems import create_random_enhanced_armor
    return create_random_enhanced_armor(floor_level)


# ============================================================================
# VENDOR CLASS
# ============================================================================

class Vendor:
    def __init__(self, name, gold, player_character, starting=False, magic_shop=False, bug_merchant=False):
        self.name = name
        self.gold = gold
        self.inventory = Inventory()
        self.player = player_character
        self.is_magic_shop = magic_shop
        self.is_bug_merchant = bug_merchant
        if bug_merchant:
            # Bug merchant on the shrinking bug level - sells bug-sized gear
            bug_items = generate_bug_merchant_inventory()
            for item in bug_items:
                self.inventory.add_item_quiet(item)
        elif magic_shop:
            # Ye Olde Magic Shoppe - specialized arcane inventory
            magic_items = generate_magic_shop_inventory(player_character.z, player_character)
            for item in magic_items:
                self.inventory.add_item_quiet(item)
        elif starting:
            # Use the classes directly to avoid template staleness
            # Add 3-5 healing potions for starting vendor
            num_starting_potions = random.randint(3, 5)
            for _ in range(num_starting_potions):
                self.inventory.add_item_quiet(Potion("Minor Healing Potion","A small vial of red liquid that heals minor wounds.",value=30,level=0,potion_type='healing',effect_magnitude=30))
            #self.inventory.add_item_quiet(Scroll("Scroll of Upgrade", "Enhances an item.", "Permanently increases an item's upgrade level.", value=100, level=2, scroll_type='upgrade'))
            self.inventory.add_item_quiet(Weapon("Dagger", "A small, sharp blade.", attack_bonus=2, value=10, level=0, upgrade_level=0))
            self.inventory.add_item_quiet(Armor("Leather Armor","Light leather armor.", defense_bonus=3, value=50, level=0, upgrade_level=0))
            self.inventory.add_item_quiet(Lantern("Lantern", "Provides continuous light with fuel.", fuel_amount=50, light_radius=7, value=30, level=0))
            self.inventory.add_item_quiet(Food("Rations", "Standard travel rations.", value=10, level=0, nutrition=40, count=3))
            # Towel removed from starting vendor - now only randomly available from dungeon vendors
            # Add starting else
        else:
            current_floor_level = player_character.z
            min_item_level = max(0, current_floor_level - 1)
            max_item_level = current_floor_level + 1

            available_potions = [item for item in POTION_TEMPLATES if min_item_level <= item.level <= max_item_level]
            available_scolls = [item for item in SCROLL_TEMPLATES if min_item_level <= item.level <= max_item_level]
            available_spells = [item for item in SPELL_TEMPLATES if min_item_level <= item.level <= max_item_level]

            # Add 1-2 weapons with chance for upgrades/elements
            num_weapons = random.randint(1, 2)
            for _ in range(num_weapons):
                enhanced_weapon = _get_enhanced_weapon(current_floor_level)
                self.inventory.add_item_quiet(enhanced_weapon)

            # Add 1-2 armors with chance for upgrades/elements
            num_armors = random.randint(1, 2)
            for _ in range(num_armors):
                enhanced_armor = _get_enhanced_armor(current_floor_level)
                self.inventory.add_item_quiet(enhanced_armor)

            # Add a few potions and scrolls
            num_potions = random.randint(1, 3)
            for _ in range(num_potions):
                if available_potions:
                    potion_template = random.choice(available_potions)
                    # Fixed Potion instantiation here
                    self.inventory.add_item_quiet(Potion(name=potion_template.name, description=potion_template.description, value=potion_template.value, level=potion_template.level,
                                                         potion_type=potion_template.potion_type, effect_magnitude=potion_template.effect_magnitude, duration=potion_template.duration, resistance_element=potion_template.resistance_element))

            # GUARANTEED healing potions: 3-5 per vendor, scaled to floor level
            num_healing_potions = random.randint(3, 5)
            # Determine healing potion tier based on floor level
            if current_floor_level < 5:
                healing_potion_name = "Minor Healing Potion"
                healing_potion_desc = "A small vial of red liquid that heals minor wounds."
                healing_magnitude = 30
                healing_value = 30
                healing_level = 0
            elif current_floor_level < 10:
                healing_potion_name = "Healing Potion"
                healing_potion_desc = "A vial of red liquid that heals wounds."
                healing_magnitude = 60
                healing_value = 60
                healing_level = 3
            elif current_floor_level < 20:
                healing_potion_name = "Greater Healing Potion"
                healing_potion_desc = "A large vial of vibrant red liquid that heals significant wounds."
                healing_magnitude = 100
                healing_value = 100
                healing_level = 6
            else:
                healing_potion_name = "Superior Healing Potion"
                healing_potion_desc = "A potent elixir that heals grievous wounds."
                healing_magnitude = 150
                healing_value = 150
                healing_level = 10

            for _ in range(num_healing_potions):
                self.inventory.add_item_quiet(Potion(
                    name=healing_potion_name,
                    description=healing_potion_desc,
                    value=healing_value,
                    level=healing_level,
                    potion_type='healing',
                    effect_magnitude=healing_magnitude
                ))

            num_scrolls = random.randint(0, 2)
            for _ in range(num_scrolls):
                if available_scolls:
                    scroll_template = random.choice(available_scolls)
                    self.inventory.add_item_quiet(Scroll(scroll_template.name, scroll_template.description, scroll_template.effect_description, scroll_template.value, scroll_template.level, scroll_template.scroll_type))

            num_spells = random.randint(0, 2)
            for _ in range(num_spells):
                if available_spells:
                    # Get spell names player already owns
                    player_spell_names = [spell.name for spell in player_character.inventory.items if isinstance(spell, Spell)]

                    # Filter to only spells player doesn't have
                    vendor_available_spells = [s for s in available_spells if s.name not in player_spell_names]

                    if vendor_available_spells:
                        spell_template = random.choice(vendor_available_spells)
                        # Create a new instance of the Spell object
                        self.inventory.add_item_quiet(Spell(
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
                        ))

            # All vendors stock rations (3-4)
            num_rations = random.randint(3, 4)
            self.inventory.add_item_quiet(Food("Rations", "Standard travel rations.", value=10, level=0, nutrition=40, count=num_rations))

            # 30% chance for vendor to stock a towel
            if random.random() < 0.30:
                self.inventory.add_item_quiet(Towel("Towel", "A soft cotton towel. Don't panic!", value=5, level=0))

            player_has_lantern = False
            for item in player_character.inventory.items:
              if isinstance(item, Lantern):
                player_has_lantern = True
                break

            # Add lantern fuel if character has lantern. If not, add lantern
            if not player_has_lantern:
              self.inventory.add_item_quiet(Lantern("Lantern", "Provides continuous light with fuel.", fuel_amount=10, light_radius=7, value=30, level=0))
            else:
              self.inventory.add_item_quiet(LanternFuel("Lantern Fuel", "A small flask of oil for your lantern.", value=5, level=0, fuel_restore_amount=10))


# ============================================================================
# VENDOR NAMES AND MESSAGES
# ============================================================================

vendor_names = [
    "Bartholomew", "Agnes", "Old Man Tiberius", "Madame Xylos", "Flimsy Fred",
    "Grumpy Gus", "Shifty Sam", "Mysterious Madam", "Sneaky Pete", "Crazy Carl",
    "Honest Abe", "One-eyed Sarah", "Mad Max", "No-show Joe", "Emo Willow",
    "Rusty Bob", "Wanda", "Lucky Louie", "Just Sid", "Lil Nugget", "Wilford Beetus"
]

vendor_messages = {
    "Bartholomew": "Greetings, traveler! Please, ignore the smell of sulfur.",
    "Agnes": "Don't touch anything you can't afford, dearie. My cat is watching.",
    "Old Man Tiberius": "I've seen empires rise and fall... and prices go up.",
    "Madame Xylos": "The spirits told me you were coming. They also said you're cheap.",
    "Flimsy Fred": "Everything 100% guaranteed*! (*Guaranteed to exist until sold).",
    "Grumpy Gus": "Buy something or get out. I'm missing my nap.",
    "Shifty Sam": "These items fell off a wagon. A very nice wagon.",
    "Mysterious Madam": "What you seek is here... if you have the coin.",
    "Sneaky Pete": "Psst. Over here. The good stuff is in the back.",
    "Crazy Carl": "THEY ARE WATCHING US! BUY A HELMET! QUICK!",
    "Honest Abe": "I cannot tell a lie... this sword is slightly bent.",
    "One-eyed Sarah": "Keep your hands where I can see 'em. Both of 'em.",
    "Mad Max": "It's a lovely day! A lovely day to spend gold!",
    "No-show Joe": "I'm not here. Leave money on the counter.",
    "Emo Willow": "Life is pain. Buying armor might delay the inevitable, I guess.",
    "Rusty Bob": "One man's trash is... well, it's my inventory.",
    "Wanda": "A little magic, a little sparkle, a lot of gold.",
    "Lucky Louie": "Today is your lucky day! Maybe.",
    "Just Sid": "It's just stuff. Buy it.",
    "Lil Nugget": "Welcome to Buc-ii's. Try the Brishkit.",
    "Wilford Beetus": "If you're here for donuts, you're too late."
}


# ============================================================================
# YE OLDE MAGIC SHOPPE - Rare specialty vendors on floors 20+
# ============================================================================

MAGIC_SHOP_NAMES = [
    "Archmage Zephyria",
    "The Whispering Merchant",
    "Blind Seer Morvus",
    "Lady Nighthollow",
    "Professor Quillsworth",
    "The Hooded Alchemist",
    "Grimtooth the Enchanter",
    "Madame Stardust",
]

MAGIC_SHOP_MESSAGES = {
    "Archmage Zephyria": "You have found Ye Olde Magic Shoppe. The air crackles with arcane energy. Welcome, seeker of power.",
    "The Whispering Merchant": "You have found Ye Olde Magic Shoppe. The shelves rearrange themselves as you enter. The merchant speaks without moving its lips.",
    "Blind Seer Morvus": "You have found Ye Olde Magic Shoppe. I cannot see you, but I see what you need. My prices are... prophetic.",
    "Lady Nighthollow": "You have found Ye Olde Magic Shoppe. Moonlight follows her even underground. Every scroll here has tasted starlight.",
    "Professor Quillsworth": "You have found Ye Olde Magic Shoppe. Twelve doctorates and I ended up selling scrolls in a cave. Don't touch the purple ones.",
    "The Hooded Alchemist": "You have found Ye Olde Magic Shoppe. My elixirs are brewed from things best left unnamed. Satisfaction guaranteed. Side effects negotiable.",
    "Grimtooth the Enchanter": "You have found Ye Olde Magic Shoppe. Every weapon here has a name and a grudge. Choose wisely.",
    "Madame Stardust": "You have found Ye Olde Magic Shoppe. The cosmos provides, darling. For a modest fee.",
}

MAGIC_SHOP_CHANCE = 0.15  # 15% chance on floors 20+
MAGIC_SHOP_MIN_FLOOR = 20

# ============================================================================
# BUG MERCHANT DATA (Shrinking Bug Level)
# ============================================================================

BUG_MERCHANT_NAMES = [
    "Clickwick the Weevil",
    "Madame Thorax",
    "Old Chitin-face",
    "Buzzy McFly",
    "The Silk Spinner",
    "Grub the Dealer",
]

BUG_MERCHANT_GREETINGS = {
    "Clickwick the Weevil": "A weevil in a tiny top hat clicks its mandibles. 'Shrunk, are ya? I've got just the gear for your... condition.'",
    "Madame Thorax": "A regal mantis adjusts her spectacles. 'Welcome, little one. My wares are crafted from the finest chitin.'",
    "Old Chitin-face": "A scarred beetle grunts from behind a counter of bark. 'Bug-sized gear. Fair prices. No refunds.'",
    "Buzzy McFly": "A hyperactive fly rubs its hands together. 'BZZT! Welcome welcome! Everything must go! Buzz buzz!'",
    "The Silk Spinner": "A spider delicately arranges silk-wrapped bundles. 'I spin only the finest armor, dear. Try not to get eaten.'",
    "Grub the Dealer": "A fat grub lounges on a mushroom cap. 'Psst. You need gear? I got gear. Real bug-quality stuff.'",
}


def generate_bug_merchant_inventory():
    """Generate inventory for a bug merchant on the shrinking bug level.
    Stocks bug-themed weapons, armor, and healing potions."""
    from .game_data import BUG_WEAPON_TEMPLATES, BUG_ARMOR_TEMPLATES

    items = []

    # 2 random bug weapons
    weapons = random.sample(BUG_WEAPON_TEMPLATES, min(2, len(BUG_WEAPON_TEMPLATES)))
    for wt in weapons:
        w = Weapon(
            name=wt['name'], description=wt['description'],
            attack_bonus=wt['attack_bonus'], value=wt['value'],
            level=wt['level'], upgrade_level=0,
            elemental_strength=wt.get('elemental_strength', ["None"]),
        )
        items.append(w)

    # 2 random bug armors
    armors = random.sample(BUG_ARMOR_TEMPLATES, min(2, len(BUG_ARMOR_TEMPLATES)))
    for at in armors:
        a = Armor(
            name=at['name'], description=at['description'],
            defense_bonus=at['defense_bonus'], value=at['value'],
            level=at['level'], upgrade_level=0,
            elemental_strength=at.get('elemental_strength', ["None"]),
        )
        items.append(a)

    # 2-3 healing potions (nectar-themed)
    num_potions = random.randint(2, 3)
    for _ in range(num_potions):
        items.append(Potion(
            "Nectar Vial", "A drop of flower nectar - a full meal at this size.",
            value=25, level=1, potion_type='healing', effect_magnitude=35,
        ))

    return items


# ============================================================================
# VENDOR ACTION FUNCTIONS
# ============================================================================

def set_vendor_greeting(msg):
    gs.shop_message = msg

# Helper to log a vendor transaction message to the game log only (not the panel)
def set_shop_msg(msg):
    add_log(msg)

# New function to handle vendor room interaction
def process_vendor_action(player_character, vendor_character, cmd):
    """
    Processes a single command for vendor interaction.
    Returns True if shopping is finished, False otherwise.
    """

    if cmd == "init" or cmd == "l" or cmd == "list":
        if cmd != "init":
             set_vendor_greeting(vendor_messages.get(vendor_character.name, "Welcome."))
             if vendor_character.name not in gs.game_stats.get('unique_vendors', set()):
                 if 'unique_vendors' not in gs.game_stats:
                     gs.game_stats['unique_vendors'] = set()
                 gs.game_stats['unique_vendors'].add(vendor_character.name)
                 gs.game_stats['vendors_visited'] = len(gs.game_stats['unique_vendors'])
                 check_achievements(player_character)
        return False # Shopping continues


    # Check for 'ba' (buy all) BEFORE checking for 'b' to prevent conflict
    if cmd == 'ba': # Buy All - only available in starting shop
    # Check if this is being called from handle_starting_shop (starting shop context)
        if gs.active_vendor and vendor_character == gs.active_vendor and gs.prompt_cntl == "starting_shop":
            total_cost = sum(item.calculated_value for item in vendor_character.inventory.items)
            if not vendor_character.inventory.items:
                set_shop_msg("The vendor has nothing to sell!")
            elif player_character.gold >= total_cost:
                player_character.gold -= total_cost
                vendor_character.gold += total_cost
                # Transfer all items and identify them
                items_identified = 0
                for item_to_buy in list(vendor_character.inventory.items): # Iterate over a copy
                    new_item = _create_item_copy(item_to_buy)
                    player_character.inventory.add_item(new_item)
                    # Auto-identify purchased items
                    if isinstance(new_item, (Potion, Scroll, Weapon, Armor)) and not is_item_identified(new_item):
                        identify_item(new_item, silent=True)
                        items_identified += 1

                vendor_character.inventory.items.clear()
                if items_identified > 0:
                    set_shop_msg(f"You bought everything for {total_cost} gold! ({items_identified} item types identified)")
                else:
                    set_shop_msg(f"You bought everything for {total_cost} gold!")
            else:
                set_shop_msg(f"Not enough gold to buy everything! You need {total_cost} gold.")
        else:
            set_shop_msg("The 'buy all' option is only available at the starting shop.")
        return False

    elif cmd.startswith('b'):
        try:
            # Handle both "b 3" and "b3" formats
            if cmd == 'b':
                set_shop_msg("Please specify an item number (e.g., b1)")
                return False
            # Extract number - skip 'b' and optional space
            num_str = cmd[1:].strip()
            item_number_to_buy = int(num_str) - 1

            # Use sorted inventory to match display order
            sorted_vendor_items = get_sorted_inventory(vendor_character.inventory)

            if 0 <= item_number_to_buy < len(sorted_vendor_items):
                item_to_buy = sorted_vendor_items[item_number_to_buy]
                if player_character.gold >= item_to_buy.calculated_value:
                    player_character.gold -= item_to_buy.calculated_value
                    vendor_character.gold += item_to_buy.calculated_value

                    new_item = _create_item_copy(item_to_buy)

                    player_character.inventory.add_item(new_item)
                    # Remove the actual item from vendor's inventory (not by index since we used sorted)
                    vendor_character.inventory.items.remove(item_to_buy)

                    # Auto-identify item when purchased from vendor
                    # The vendor tells you what the item is when you buy it
                    was_unidentified = not is_item_identified(new_item)
                    if was_unidentified and isinstance(new_item, (Potion, Scroll, Weapon, Armor)):
                        identify_item(new_item, silent=True)
                        set_shop_msg(f"You bought {new_item.name} for {new_item.calculated_value} gold. (Now you know what {get_item_display_name(new_item)} really is!)")
                    else:
                        # Track spell learning from vendors
                        if isinstance(new_item, Spell):
                            gs.game_stats['spells_learned'] = gs.game_stats.get('spells_learned', 0) + 1
                            check_achievements(player_character)

                        item_count=1
                        if isinstance(new_item, Flare):
                            item_count += (new_item.count-1)

                        set_shop_msg(f"You bought {item_count} {new_item.name} for {new_item.calculated_value} gold.")
                    # No need to display inventory here, render() handles it
                else:
                    set_shop_msg(f"Not enough gold! You need {item_to_buy.calculated_value} gold for {item_to_buy.name}.")
            else:
                set_shop_msg(f"Invalid item number.")
        except ValueError:
            set_shop_msg(f"Invalid input. Please enter 'b' followed by the item number.")
        return False # Shopping continues

    elif cmd.startswith('s') and not cmd.startswith('sell_qty'):
        try:
            # Handle both "s 3" and "s3" formats
            if cmd == 's':
                set_shop_msg("Please specify an item number (e.g., s1)")
                return False
            # Extract number - skip 's' and optional space
            num_str = cmd[1:].strip()
            item_number_to_sell = int(num_str) - 1

            # Use sorted inventory to match display order
            sorted_player_items = get_sorted_inventory(player_character.inventory)

            if 0 <= item_number_to_sell < len(sorted_player_items):
                item_to_sell = sorted_player_items[item_number_to_sell]

                # Check if item is stackable and has multiple
                item_count = getattr(item_to_sell, 'count', 1)
                if item_count > 1 and isinstance(item_to_sell, (Potion, Scroll, Flare, Ingredient, LanternFuel, Food)):
                    # Store pending sale and ask how many
                    gs.pending_sell_item = item_to_sell
                    gs.pending_sell_item_index = item_number_to_sell
                    sell_price_each = item_to_sell.calculated_value // 2
                    set_shop_msg(f"How many {item_to_sell.name} to sell? (1-{item_count}, {sell_price_each}g each, 'a' for all, 'c' to cancel)")
                    gs.prompt_cntl = "sell_quantity_mode"
                    return False

                # For simplicity, vendor buys at half price
                sell_price = item_to_sell.calculated_value // 2
                if vendor_character.gold >= sell_price:
                    player_character.gold += sell_price
                    gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + sell_price
                    check_achievements(player_character)
                    vendor_character.gold -= sell_price

                    new_item_for_vendor = _create_item_copy(item_to_sell)

                    vendor_character.inventory.add_item_quiet(new_item_for_vendor) # Vendor gets the item

                    # De-equip if this item is currently equipped
                    if player_character.equipped_weapon == item_to_sell:
                        player_character.equipped_weapon = None
                        add_log(f"{COLOR_YELLOW}(Unequipped {item_to_sell.name}){COLOR_RESET}")
                    if player_character.equipped_armor == item_to_sell:
                        player_character.equipped_armor = None
                        add_log(f"{COLOR_YELLOW}(Unequipped {item_to_sell.name}){COLOR_RESET}")

                    # Remove the actual item from player's inventory (not by index since we used sorted)
                    player_character.inventory.items.remove(item_to_sell)

                    set_shop_msg(f"You sold {item_to_sell.name} for {sell_price} gold.")
                    # Track unique vendors sold to (for Platino unlock)
                    if vendor_character and vendor_character.name:
                        if 'vendors_sold_to' not in gs.game_stats:
                            gs.game_stats['vendors_sold_to'] = set()
                        gs.game_stats['vendors_sold_to'].add(vendor_character.name)
                    # No need to display inventory here, render() handles it
                else:
                    set_shop_msg(f"The vendor doesn't have enough gold to buy {item_to_sell.name}.")
            else:
                set_shop_msg(f"Invalid item number.")
        except ValueError:
            set_shop_msg(f"Invalid input. Please use 'b [number]', 's [number]', 'f', or 'q'.")
        return False # Shopping continues

    # IDENTIFY COMMAND - vendor identifies items for gold
    elif cmd.startswith('id'):
        try:
            # Handle both "id 3" and "id3" formats
            if cmd == 'id':
                # Show list of unidentified items
                unid_items = []
                sorted_items = get_sorted_inventory(player_character.inventory)
                for i, item in enumerate(sorted_items):
                    if isinstance(item, (Potion, Scroll, Weapon, Armor, Spell)) and not is_item_identified(item):
                        cost = get_vendor_identify_cost(item)
                        display_name = get_item_display_name(item, for_vendor=False)
                        unid_items.append(f"{i+1}. {display_name} - {cost}g to identify")

                if unid_items:
                    set_shop_msg("Unidentified items: " + ", ".join(unid_items[:5]))
                    if len(unid_items) > 5:
                        set_shop_msg(gs.shop_message + f"... and {len(unid_items) - 5} more. Use 'id#' to identify.")
                else:
                    set_shop_msg("All your items are already identified!")
                return False

            # Extract number - skip 'id' and optional space
            num_str = cmd[2:].strip()
            item_number = int(num_str) - 1

            sorted_items = get_sorted_inventory(player_character.inventory)

            if 0 <= item_number < len(sorted_items):
                item = sorted_items[item_number]

                if not isinstance(item, (Potion, Scroll, Weapon, Armor, Spell)):
                    set_shop_msg("That item doesn't need identification.")
                elif is_item_identified(item):
                    set_shop_msg(f"{item.name} is already identified.")
                else:
                    cost = get_vendor_identify_cost(item)
                    if player_character.gold >= cost:
                        player_character.gold -= cost
                        identify_item(item)
                        set_shop_msg(f"The vendor identifies it as: {item.name}! (Cost: {cost}g)")
                    else:
                        set_shop_msg(f"Not enough gold! Identification costs {cost}g.")
            else:
                set_shop_msg("Invalid item number.")
        except ValueError:
            set_shop_msg("Use 'id' to see unidentified items, or 'id#' to identify a specific item.")
        return False

    # REPAIR COMMAND - vendor repairs damaged equipment for gold
    elif cmd.startswith('r') and not cmd.startswith('ra'):
        try:
            # Handle both "r 3" and "r3" formats
            if cmd == 'r':
                # Show list of damaged items
                damaged_items = []
                sorted_items = get_sorted_inventory(player_character.inventory)
                for i, item in enumerate(sorted_items):
                    if isinstance(item, (Weapon, Armor)) and item.durability < item.max_durability:
                        if getattr(item, 'is_cursed', False):
                            damaged_items.append(f"{i+1}. {item.name} (CURSED - cannot repair)")
                        else:
                            cost = get_repair_cost(item)
                            damaged_items.append(f"{i+1}. {item.name} ({item.durability}/{item.max_durability}) - {cost}g")

                if damaged_items:
                    set_shop_msg("Damaged items: " + ", ".join(damaged_items[:4]))
                    if len(damaged_items) > 4:
                        set_shop_msg(gs.shop_message + f"... and {len(damaged_items) - 4} more. Use 'r#' to repair.")
                else:
                    set_shop_msg("All your equipment is in good condition!")
                return False

            # Repair all command
            if cmd == 'ra':
                sorted_items = get_sorted_inventory(player_character.inventory)
                total_cost = 0
                items_to_repair = []
                for item in sorted_items:
                    if isinstance(item, (Weapon, Armor)) and item.durability < item.max_durability:
                        if getattr(item, 'is_cursed', False):
                            continue  # Skip cursed items
                        items_to_repair.append(item)
                        total_cost += get_repair_cost(item)

                if not items_to_repair:
                    set_shop_msg("No items need repair!")
                elif player_character.gold >= total_cost:
                    player_character.gold -= total_cost
                    for item in items_to_repair:
                        item.durability = item.max_durability
                    set_shop_msg(f"Repaired {len(items_to_repair)} items for {total_cost} gold!")
                else:
                    set_shop_msg(f"Not enough gold! Repairing all items costs {total_cost}g.")
                return False

            # Extract number - skip 'r' and optional space
            num_str = cmd[1:].strip()
            item_number = int(num_str) - 1

            sorted_items = get_sorted_inventory(player_character.inventory)

            if 0 <= item_number < len(sorted_items):
                item = sorted_items[item_number]

                if not isinstance(item, (Weapon, Armor)):
                    set_shop_msg("That item cannot be repaired.")
                elif getattr(item, 'is_cursed', False):
                    set_shop_msg(f"{item.name} is cursed and cannot be repaired!")
                elif item.durability >= item.max_durability:
                    set_shop_msg(f"{item.name} doesn't need repair.")
                else:
                    cost = get_repair_cost(item)
                    if player_character.gold >= cost:
                        player_character.gold -= cost
                        old_dur = item.durability
                        item.durability = item.max_durability
                        set_shop_msg(f"Repaired {item.name} ({old_dur} -> {item.max_durability}) for {cost}g!")
                    else:
                        set_shop_msg(f"Not enough gold! Repair costs {cost}g.")
            else:
                set_shop_msg("Invalid item number.")
        except ValueError:
            set_shop_msg("Use 'r' to see damaged items, 'r#' to repair one, or 'ra' to repair all.")
        return False

    elif cmd == 'x' or cmd == 'q':
        return True # Shopping finished
    else:
        set_shop_msg(f"Invalid input. Please use 'b [number]', 's [number]', 'x', or 'q'.")
        return False # Shopping continues


# ============================================================================
# MAGIC SHOP INVENTORY GENERATION
# ============================================================================

def generate_magic_shop_inventory(floor_level, player_character):
    """
    Generate specialized inventory for Ye Olde Magic Shoppe.
    Heavy on scrolls, spells, elixirs, and high-tier potions.
    """
    inventory = []

    # --- SPELLS: 4-6 spells, biased toward higher levels ---
    player_spell_names = [s.name for s in player_character.inventory.items if isinstance(s, Spell)]
    # Available spells up to player_level + 1 (magic shops sell slightly ahead)
    max_spell_level = min(5, player_character.level + 1)
    available_spells = [s for s in SPELL_TEMPLATES if s.level <= max_spell_level and s.name not in player_spell_names]
    # Bias toward higher level spells
    if available_spells:
        weighted = []
        for s in available_spells:
            weight = 1 + s.level  # Higher level = more likely to appear
            weighted.extend([s] * weight)
        num_spells = random.randint(4, 6)
        chosen_spells = set()
        for _ in range(num_spells):
            if weighted:
                pick = random.choice(weighted)
                if pick.name not in chosen_spells:
                    chosen_spells.add(pick.name)
                    inventory.append(Spell(
                        name=pick.name, description=pick.description,
                        mana_cost=pick.mana_cost, damage_type=pick.damage_type,
                        base_power=pick.base_power, level=pick.level,
                        spell_type=pick.spell_type,
                        status_effect_name=pick.status_effect_name,
                        status_effect_duration=pick.status_effect_duration,
                        status_effect_type=pick.status_effect_type,
                        status_effect_magnitude=pick.status_effect_magnitude
                    ))

    # --- SCROLLS: 3-5 scrolls including upgrade scrolls ---
    scroll_pool = [s for s in SCROLL_TEMPLATES if s.level <= floor_level + 5]
    if scroll_pool:
        num_scrolls = random.randint(3, 5)
        for _ in range(num_scrolls):
            st = random.choice(scroll_pool)
            inventory.append(Scroll(st.name, st.description, st.effect_description,
                                    st.value, st.level, st.scroll_type,
                                    spell_to_cast=st.spell_to_cast,
                                    spell_power_multiplier=st.spell_power_multiplier))

    # Always include a high-tier upgrade scroll
    if floor_level >= 40:
        inventory.append(Scroll("Scroll of Eternal Upgrade", "A scroll from beyond time itself.", "Upgrade items to +35 maximum.", 6000, 40, 'upgrade'))
    elif floor_level >= 35:
        inventory.append(Scroll("Scroll of Cosmic Upgrade", "A scroll woven from starlight.", "Upgrade items to +30 maximum.", 3500, 35, 'upgrade'))
    elif floor_level >= 30:
        inventory.append(Scroll("Scroll of Celestial Upgrade", "A scroll that hums with celestial power.", "Upgrade items to +25 maximum.", 2000, 30, 'upgrade'))
    elif floor_level >= 25:
        inventory.append(Scroll("Scroll of Divine Upgrade", "The ultimate scroll of enhancement.", "Upgrade items to +20 maximum.", 1200, 25, 'upgrade'))
    else:
        inventory.append(Scroll("Scroll of Mythic Upgrade", "A scroll touched by the gods.", "Upgrade items to +17 maximum.", 850, 20, 'upgrade'))

    # --- PERMANENT ELIXIRS: 1-2 based on floor ---
    elixir_pool = []
    if floor_level >= 35:
        elixir_pool = [
            Potion(name="Supreme Elixir of Might", description="Permanently increases STR by 6.", value=5000, level=35, potion_type='permanent_strength', effect_magnitude=6),
            Potion(name="Supreme Elixir of Grace", description="Permanently increases DEX by 6.", value=5000, level=35, potion_type='permanent_dexterity', effect_magnitude=6),
            Potion(name="Supreme Elixir of Brilliance", description="Permanently increases INT by 6.", value=5000, level=35, potion_type='permanent_intelligence', effect_magnitude=6),
            Potion(name="Supreme Elixir of Vitality", description="Permanently increases max HP by 75.", value=6000, level=35, potion_type='permanent_health', effect_magnitude=75),
        ]
    elif floor_level >= 25:
        elixir_pool = [
            Potion(name="Greater Elixir of Might", description="Permanently increases STR by 4.", value=2000, level=25, potion_type='permanent_strength', effect_magnitude=4),
            Potion(name="Greater Elixir of Grace", description="Permanently increases DEX by 4.", value=2000, level=25, potion_type='permanent_dexterity', effect_magnitude=4),
            Potion(name="Greater Elixir of Brilliance", description="Permanently increases INT by 4.", value=2000, level=25, potion_type='permanent_intelligence', effect_magnitude=4),
            Potion(name="Greater Elixir of Vitality", description="Permanently increases max HP by 40.", value=3000, level=25, potion_type='permanent_health', effect_magnitude=40),
        ]
    else:
        elixir_pool = [
            Potion(name="Elixir of Might", description="Permanently increases STR by 2.", value=800, level=15, potion_type='permanent_strength', effect_magnitude=2),
            Potion(name="Elixir of Grace", description="Permanently increases DEX by 2.", value=800, level=15, potion_type='permanent_dexterity', effect_magnitude=2),
            Potion(name="Elixir of Brilliance", description="Permanently increases INT by 2.", value=800, level=15, potion_type='permanent_intelligence', effect_magnitude=2),
            Potion(name="Elixir of Vitality", description="Permanently increases max HP by 20.", value=1200, level=15, potion_type='permanent_health', effect_magnitude=20),
        ]
    num_elixirs = random.randint(1, 2)
    for _ in range(num_elixirs):
        e = random.choice(elixir_pool)
        inventory.append(Potion(name=e.name, description=e.description, value=e.value,
                                level=e.level, potion_type=e.potion_type, effect_magnitude=e.effect_magnitude))

    # --- HIGH-TIER COMBAT POTIONS: 2-4 ---
    combat_pool = []
    if floor_level >= 35:
        combat_pool = [
            Potion(name="Potion of Mythic Wrath", description="Primordial fury distilled to its purest form.", value=1500, level=35, potion_type='strength', effect_magnitude=75, duration=14),
            Potion(name="Potion of Mythic Guard", description="An impenetrable aura of ancient protection.", value=1500, level=35, potion_type='defense', effect_magnitude=60, duration=14),
            Potion(name="Supreme Vampirism Potion", description="Feast on the lifeforce of enemies.", value=600, level=20, potion_type='vampirism', effect_magnitude=100, duration=12),
            Potion(name="Supreme Regeneration Potion", description="Incredible sustained healing.", value=500, level=20, potion_type='regeneration', effect_magnitude=25, duration=15),
        ]
    elif floor_level >= 25:
        combat_pool = [
            Potion(name="Potion of Titan's Wrath", description="The rage of ancient titans empowers your strikes.", value=800, level=20, potion_type='strength', effect_magnitude=50, duration=12),
            Potion(name="Potion of Titan's Guard", description="The endurance of titans shields you from harm.", value=800, level=20, potion_type='defense', effect_magnitude=40, duration=12),
            Potion(name="Greater Vampirism Potion", description="Drain life with every blow.", value=300, level=12, potion_type='vampirism', effect_magnitude=75, duration=10),
            Potion(name="Greater Regeneration Potion", description="Powerful sustained healing.", value=200, level=10, potion_type='regeneration', effect_magnitude=15, duration=12),
        ]
    else:
        combat_pool = [
            Potion(name="Potion of Wrath", description="Battle fury surges through your veins.", value=300, level=10, potion_type='strength', effect_magnitude=25, duration=10),
            Potion(name="Potion of Iron Will", description="Your resolve hardens like iron.", value=300, level=10, potion_type='defense', effect_magnitude=20, duration=10),
            Potion(name="Potion of Berserker Rage", description="Massive attack boost, but reduces defense.", value=100, level=3, potion_type='berserker', effect_magnitude=30, duration=5),
        ]
    num_combat = random.randint(2, 4)
    for _ in range(num_combat):
        p = random.choice(combat_pool)
        inventory.append(Potion(name=p.name, description=p.description, value=p.value,
                                level=p.level, potion_type=p.potion_type,
                                effect_magnitude=p.effect_magnitude, duration=p.duration))

    # --- HEALING & MANA: 2-3 high-tier ---
    if floor_level >= 30:
        heal_pool = [
            Potion("Mythic Healing Potion", "Liquid starlight that knits flesh and bone.", value=800, level=25, potion_type='healing', effect_magnitude=500),
            Potion("Supreme Mana Potion", "Liquid moonlight that floods the mind with power.", value=400, level=20, potion_type='mana', effect_magnitude=200),
        ]
    else:
        heal_pool = [
            Potion("Legendary Healing Potion", "A shimmering elixir of extraordinary restoration.", value=500, level=15, potion_type='healing', effect_magnitude=350),
            Potion("Master Mana Potion", "A deep indigo draught of arcane power.", value=200, level=10, potion_type='mana', effect_magnitude=120),
        ]
    for _ in range(random.randint(2, 3)):
        h = random.choice(heal_pool)
        inventory.append(Potion(name=h.name, description=h.description, value=h.value,
                                level=h.level, potion_type=h.potion_type,
                                effect_magnitude=h.effect_magnitude))

    # --- ONE ENHANCED WEAPON OR ARMOR (rare quality) ---
    if random.random() < 0.5:
        weapon = _get_enhanced_weapon(floor_level + 3)  # Slightly above floor
        inventory.append(weapon)
    else:
        armor = _get_enhanced_armor(floor_level + 3)
        inventory.append(armor)

    # Sort by type and level
    inventory.sort(key=lambda item: (type(item).__name__, item.level, item.name))

    return inventory


# ============================================================================
# SELL QUANTITY HANDLER
# ============================================================================

def process_sell_quantity(player_character, my_tower, cmd):
    """Handle selling a quantity of stacked items."""

    if gs.pending_sell_item is None:
        set_shop_msg("Error: No item selected for sale.")
        gs.prompt_cntl = "vendor_shop"
        return

    item = gs.pending_sell_item
    item_count = getattr(item, 'count', 1)
    sell_price_each = item.calculated_value // 2

    # Cancel
    if cmd == 'c':
        set_shop_msg("Sale cancelled.")
        gs.pending_sell_item = None
        gs.pending_sell_item_index = None
        gs.prompt_cntl = "vendor_shop"
        return

    # Sell all
    if cmd == 'a':
        quantity = item_count
    else:
        try:
            quantity = int(cmd)
        except ValueError:
            set_shop_msg(f"Invalid input. Enter a number (1-{item_count}), 'a' for all, or 'c' to cancel.")
            return

    # Validate quantity
    if quantity < 1 or quantity > item_count:
        set_shop_msg(f"Invalid quantity. Enter 1-{item_count}, 'a' for all, or 'c' to cancel.")
        return

    total_price = sell_price_each * quantity

    # Check if vendor can afford
    if gs.active_vendor.gold < total_price:
        set_shop_msg(f"The vendor can't afford {quantity} {item.name} ({total_price}g). Try fewer.")
        return

    # Complete the sale
    player_character.gold += total_price
    gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + total_price
    check_achievements(player_character)
    gs.active_vendor.gold -= total_price

    if quantity >= item_count:
        # Selling all - remove item entirely
        player_character.inventory.items.remove(item)
        # Give vendor a copy with full count
        new_item_for_vendor = _create_item_copy(item)
        new_item_for_vendor.count = quantity
        gs.active_vendor.inventory.add_item_quiet(new_item_for_vendor)
    else:
        # Selling partial - decrement count
        item.count -= quantity
        # Give vendor a copy with sold quantity
        new_item_for_vendor = _create_item_copy(item)
        new_item_for_vendor.count = quantity
        gs.active_vendor.inventory.add_item_quiet(new_item_for_vendor)

    set_shop_msg(f"Sold {quantity} {item.name} for {total_price} gold.")
    # Track unique vendors sold to (for Platino unlock)
    if gs.active_vendor and gs.active_vendor.name:
        if 'vendors_sold_to' not in gs.game_stats:
            gs.game_stats['vendors_sold_to'] = set()
        gs.game_stats['vendors_sold_to'].add(gs.active_vendor.name)
    gs.pending_sell_item = None
    gs.pending_sell_item_index = None
    gs.prompt_cntl = "vendor_shop"


# ============================================================================
# SHOP ENTRY HANDLERS
# ============================================================================

def handle_starting_shop(player_character, my_tower, cmd):

    if gs.active_vendor is None:
        # Create the vendor if not exists
        starting_vendor = Vendor(name=random.choice(vendor_names), gold=500, player_character=player_character, starting=True)
        gs.active_vendor = starting_vendor
        # Force a 'list' command effectively for the initial display
        finished = process_vendor_action(player_character, gs.active_vendor, "list")
        # Even if finished is True here (which it won't be if process_vendor_action returns False as expected for 'list'),
        # we don't want to immediately exit the shop, so we proceed.

    # Process the actual command given by the user, or if it was the initial call, it was handled above.
    # If cmd was 'init', it was handled above. Now we use the actual command for subsequent interactions.
    if cmd != "init": # Only process the command if it's not the initial 'init' trigger
        finished = process_vendor_action(player_character, gs.active_vendor, cmd)
    else:
        finished = False # If it was 'init', we've just displayed the wares, so shopping is not finished.


    if finished: # This checks if 'q' or 'f' was entered
        add_log("You finish shopping and head out on your adventure!")
        gs.active_vendor = None
        gs.prompt_cntl = "game_loop"

    return True

def handle_vendor_shop(player_character, my_tower, cmd):

    if gs.active_vendor is None:
        # Create the vendor if not exists
        starting_vendor = Vendor(name=random.choice(vendor_names), gold=500, player_character=player_character, starting=True)
        gs.active_vendor = starting_vendor
        # Force a 'list' command effectively for the initial display
        finished = process_vendor_action(player_character, gs.active_vendor, "list")
        # Even if finished is True here (which it won't be if process_vendor_action returns False as expected for 'list'),
        # we don't want to immediately exit the shop, so we proceed.

    # Process the actual command given by the user, or if it was the initial call, it was handled above.
    # If cmd was 'init', it was handled above. Now we use the actual command for subsequent interactions.
    if cmd != "init": # Only process the command if it's not the initial 'init' trigger
        finished = process_vendor_action(player_character, gs.active_vendor, cmd)
    else:
        finished = False # If it was 'init', we've just displayed the wares, so shopping is not finished.


    if finished: # This checks if 'q' or 'f' was entered
        add_log("You finish shopping and continue on your adventure!")
        gs.active_vendor = None
        gs.prompt_cntl = "game_loop"

    return True


# ============================================================================
# WALL REVEAL UTILITY
# ============================================================================

def reveal_adjacent_walls(character, my_tower):
    current_floor = my_tower.floors[character.z]
    # Check cardinal directions: N, S, E, W
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)] # (dy, dx)

    for dy, dx in directions:
        target_y, target_x = character.y + dy, character.x + dx

        if 0 <= target_y < current_floor.rows and 0 <= target_x < current_floor.cols:
            room = current_floor.grid[target_y][target_x]
            if room.room_type == current_floor.wall_char:
                room.discovered = True
