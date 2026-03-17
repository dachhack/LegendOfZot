"""
achievements.py - Achievement system for Wizard's Cavern

Contains the Achievement class, the master ACHIEVEMENTS list,
and the check_achievements() function.

Usage:
    from achievements import ACHIEVEMENTS, check_achievements
"""

import game_state as gs
from game_state import COLOR_GREEN, COLOR_RESET, COLOR_YELLOW, add_log


# --------------------------------------------------------------------------------
# ACHIEVEMENT SYSTEM
# --------------------------------------------------------------------------------

class Achievement:
    def __init__(self, id, name, description, category, unlock_condition, reward_gold=0, reward_description=""):
        self.id = id
        self.name = name
        self.description = description
        self.category = category  # 'combat', 'exploration', 'magic', 'survival', 'collection'
        self.unlock_condition = unlock_condition  # Function that checks if unlocked
        self.unlocked = False
        self.unlock_time = None
        self.reward_gold = reward_gold
        self.reward_description = reward_description

    def check_unlock(self, player_character, game_stats):
        """Check if achievement should be unlocked"""
        if not self.unlocked and self.unlock_condition(player_character, game_stats):
            self.unlocked = True
            self.unlock_time = "now"  # You could use datetime if you want
            return True
        return False


# Define all achievements (unlock conditions use inline lambdas)
ACHIEVEMENTS = [
    # Combat Achievements
    Achievement("first_blood", "First Blood", "Defeat your first monster", "combat",
                lambda p, s: s.get('monsters_killed', 0) >= 1, 50, "You've drawn first blood!"),
    Achievement("monster_hunter", "Monster Hunter", "Defeat 10 monsters", "combat",
                lambda p, s: s.get('monsters_killed', 0) >= 10, 100, "You're becoming a skilled hunter."),
    Achievement("monster_slayer", "Monster Slayer", "Defeat 50 monsters", "combat",
                lambda p, s: s.get('monsters_killed', 0) >= 50, 250, "Your reputation precedes you."),
    Achievement("legendary_warrior", "Legendary Warrior", "Defeat 100 monsters", "combat",
                lambda p, s: s.get('monsters_killed', 0) >= 100, 500, "Legends will be told of your prowess."),
    Achievement("david_goliath", "David vs Goliath", "Defeat a monster 3+ levels higher", "combat",
                lambda p, s: s.get('defeated_higher_level', 0) >= 1, 200, "You punched above your weight!"),
    Achievement("untouchable", "Untouchable", "Kill a monster without taking damage", "combat",
                lambda p, s: s.get('full_health_kills', 0) >= 1, 100, "Flawless execution!"),
    Achievement("bold_adventurer", "Bold Adventurer", "Defeat a monster with no armor equipped", "combat",
                lambda p, s: s.get('kills_no_armor', 0) >= 1, 150, "Bravery or foolishness?"),

    # Exploration Achievements
    Achievement("deep_delver", "Deep Delver", "Reach floor 5", "exploration",
                lambda p, s: s.get('max_floor_reached', 0) >= 5, 100, "The depths call to you."),
    Achievement("abyss_walker", "Abyss Walker", "Reach floor 10", "exploration",
                lambda p, s: s.get('max_floor_reached', 0) >= 10, 300, "Few have ventured this deep."),
    Achievement("treasure_hunter", "Treasure Hunter", "Open 10 chests", "exploration",
                lambda p, s: s.get('chests_opened', 0) >= 10, 100, "You have an eye for treasure."),
    Achievement("well_traveled", "Well Traveled", "Visit 10 different vendors", "exploration",
                lambda p, s: s.get('vendors_visited', 0) >= 10, 100, "You know all the merchants."),
    Achievement("flawless", "Flawless Victory", "Clear a floor without taking damage", "exploration",
                lambda p, s: s.get('flawless_floors', 0) >= 1, 300, "Perfection achieved!"),

    # Magic Achievements
    Achievement("apprentice", "Apprentice Mage", "Learn your first spell", "magic",
                lambda p, s: s.get('spells_learned', 0) >= 1, 50, "Your magical journey begins."),
    Achievement("spellcaster", "Spellcaster", "Learn 5 different spells", "magic",
                lambda p, s: s.get('spells_learned', 0) >= 5, 150, "Your grimoire grows."),
    Achievement("archmage", "Archmage", "Learn 10 different spells", "magic",
                lambda p, s: s.get('spells_learned', 0) >= 10, 300, "Your magical knowledge is vast."),
    Achievement("magic_missile", "Magic Missile", "Cast your first spell in combat", "magic",
                lambda p, s: s.get('spells_cast', 0) >= 1, 50, "The arcane answers your call."),
    Achievement("spell_slinger", "Spell Slinger", "Cast 50 spells", "magic",
                lambda p, s: s.get('spells_cast', 0) >= 50, 200, "Magic flows through you."),
    Achievement("librarian", "Librarian", "Successfully read 5 grimoires", "magic",
                lambda p, s: s.get('grimoires_read', 0) >= 5, 150, "Knowledge is power."),
    Achievement("risky_reader", "Risky Reader", "Survive a spell backfire", "magic",
                lambda p, s: s.get('spell_backfires', 0) >= 1, 100, "Learning the hard way."),
    Achievement("memory_master", "Memory Master", "Achieve 15+ spell slots", "magic",
                lambda p, s: p.get_max_memorized_spell_slots() >= 15, 250, "Your mind is a weapon."),

    # Survival Achievements
    Achievement("survivor", "Survivor", "Survive being poisoned", "survival",
                lambda p, s: s.get('times_poisoned', 0) >= 1, 75, "What doesn't kill you..."),
    Achievement("devoted", "Devoted", "Pray at all 7 god altars", "survival",
                lambda p, s: s.get('altars_used', 0) >= 7, 200, "The gods smile upon you."),

    # Collection Achievements
    Achievement("wealthy", "Wealthy Adventurer", "Collect 1000 total gold", "collection",
                lambda p, s: s.get('total_gold_collected', 0) >= 1000, 0, "Riches await."),
    Achievement("pack_rat", "Pack Rat", "Carry 20+ items", "collection",
                lambda p, s: len(p.inventory.items) >= 20, 100, "You never know when you'll need it."),

    # Character Development
    Achievement("strong_arm", "Strong Arm", "Reach 20 Strength", "development",
                lambda p, s: p.strength >= 20, 150, "Your muscles bulge with power."),
    Achievement("nimble", "Nimble", "Reach 20 Dexterity", "development",
                lambda p, s: p.dexterity >= 20, 150, "Swift as the wind."),
    Achievement("genius", "Genius", "Reach 20 Intelligence", "development",
                lambda p, s: p.intelligence >= 20, 150, "Your mind is sharp as a blade."),
    Achievement("hero", "Hero", "Reach level 5", "development",
                lambda p, s: p.level >= 5, 100, "You're becoming a hero."),
    Achievement("champion", "Champion", "Reach level 10", "development",
                lambda p, s: p.level >= 10, 250, "A true champion of legend."),

    Achievement("vault_raider", "Vault Raider", "Defeat your first vault defender", "combat",
                lambda p, s: s.get('vault_defenders_defeated', 0) >= 1, 500, "You've conquered a legendary vault guardian!"),
    Achievement("vault_master", "Vault Master", "Defeat 5 vault defenders", "combat",
                lambda p, s: s.get('vault_defenders_defeated', 0) >= 5, 2000, "You are a legendary vault conqueror!"),
    Achievement("merchant_friend", "Merchant's Friend", "Restock a vendor for the first time", "exploration",
                lambda p, s: s.get('vendors_restocked', 0) >= 1, 100, "Making it rain stonks."),
]


def check_achievements(player_character):
    """Check all achievements and unlock any that are newly completed"""
    for achievement in ACHIEVEMENTS:
        if achievement.check_unlock(player_character, gs.game_stats):
            # Achievement just unlocked!
            # Only show in log with description
            add_log(f"{COLOR_YELLOW} ACHIEVEMENT UNLOCKED: {achievement.name} - {achievement.description}{COLOR_RESET}")

            if achievement.reward_gold > 0:
                player_character.gold += achievement.reward_gold
                add_log(f"{COLOR_GREEN}Reward: {achievement.reward_gold} gold!{COLOR_RESET}")
                gs.game_stats['total_gold_collected'] = gs.game_stats.get('total_gold_collected', 0) + achievement.reward_gold
                check_achievements(player_character)
