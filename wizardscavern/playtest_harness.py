"""
Headless playtest harness for Wizard's Cavern.

Drives the game logic without the Toga UI so scripted policies (or LLM
playtest agents) can play turns, observe state, and surface bugs / balance
issues. The game-logic modules (``game_systems``, ``combat``, ``dungeon``,
``characters``, ``room_actions``) are UI-free; this module wires them up
around the module-level ``game_state`` globals.

CLI usage:

    python -m wizardscavern.playtest_harness --seed 42 --turns 200 --policy random
    python -m wizardscavern.playtest_harness --seed 42 --script actions.txt
    python -m wizardscavern.playtest_harness --interactive
    python -m wizardscavern.playtest_harness --seed 42 --turns 200 --policy random --jsonl

Action vocabulary (mode-sensitive — see ``ACTION_HINTS``):

    game_loop:   n s e w   d (descend) u (ascend) i (inventory)
    combat_mode: a (attack) f (flee) c (cast) I (item) x (back)
    inventory:   1..9 (item) x (back) e (equip filter) u (use) E (eat)
    other modes: pass the raw key through; mode-specific handlers route it.
"""

import argparse
import collections
import json
import random as _stdlib_random
import re
import sys

from . import game_state as gs
from .characters import Character
from .dungeon import Tower
from .game_systems import (
    _trigger_room_interaction,
    handle_inventory_menu,
    move_player,
    process_chest_action,
    process_combat_action,
    process_spell_casting_action,
    process_stairs_down_action,
    process_stairs_up_action,
)
from .vendor import handle_vendor_shop, handle_starting_shop
from .items import (
    initialize_identification_system, SPELL_TEMPLATES,
    Potion, Food, Meat, Weapon, Armor, Spell, Scroll,
)
from .game_data import BUG_WEAPON_TEMPLATES, BUG_ARMOR_TEMPLATES

# Names of bug-sized gear -- the only equipment a shrunk player can use.
# Mirrors the check at game_systems.py:2239 so the policy can filter
# upgrade candidates correctly when player_is_shrunk is True.
_BUG_GEAR_NAMES = frozenset(
    [t["name"] for t in BUG_WEAPON_TEMPLATES]
    + [t["name"] for t in BUG_ARMOR_TEMPLATES]
)


# Race stat modifiers, mirrored from game_systems.process_character_creation_action.
# Base stats: health=30, attack=15, defense=5, str=10, dex=10, int=10.
RACE_MODS = {
    "human": {"health_mod": 0,   "attack_mod": 0, "defense_mod": 0,
              "strength_mod": 0,  "dexterity_mod": 0, "intelligence_mod": 0},
    "elf":   {"health_mod": -10, "attack_mod": 1, "defense_mod": -1,
              "strength_mod": -1, "dexterity_mod": 2, "intelligence_mod": 2},
    # Dwarf HP +30 (was +20) -- see game_systems.py:3455 for the death-
    # cause-analysis rationale.
    "dwarf": {"health_mod": 30,  "attack_mod": 2, "defense_mod": 2,
              "strength_mod": 2,  "dexterity_mod": -2, "intelligence_mod": -2},
}
BASE_STATS = {"health": 30, "attack": 15, "defense": 5,
              "strength": 10, "dexterity": 10, "intelligence": 10}

# Race-themed name pools, LOTR-flavoured. Used when new_game() is
# called with the default name="Tester". Each run pairs a canonical
# first name with a procedurally-picked epithet so 60-run grids
# stop colliding (16 first names × 24 epithets ~= 384 combos per
# race, well past the no-collision floor). Seed-stable so the same
# seed always produces the same hero.
RACE_FIRST_NAMES = {
    "human": (
        "Aragorn", "Boromir", "Faramir", "Theoden", "Eomer", "Eowyn",
        "Denethor", "Isildur", "Elendil", "Beregond", "Imrahil",
        "Bard", "Beorn", "Hama", "Halbarad", "Forlong", "Gilraen",
        "Anborn", "Mablung", "Erkenbrand",
    ),
    "elf": (
        "Elrond", "Legolas", "Galadriel", "Arwen", "Celeborn",
        "Glorfindel", "Haldir", "Thranduil", "Luthien", "Tauriel",
        "Finrod", "Earendil", "Feanor", "Idril", "Cirdan", "Galadhrim",
        "Maeglin", "Beleg", "Voronwe",
    ),
    "dwarf": (
        "Gimli", "Thorin", "Balin", "Dwalin", "Gloin", "Oin",
        "Bifur", "Bofur", "Bombur", "Fili", "Kili", "Dain",
        "Nori", "Ori", "Dori", "Durin", "Thror", "Thrain",
        "Farin", "Nain", "Borin",
    ),
}
# Race-flavoured epithets / patronymics. Combined with a first name
# to disambiguate hero identities across the playtest grid. Picked
# to feel like LOTR rather than D&D one-shot characters.
RACE_EPITHETS = {
    "human": (
        "the Brave", "the Stalwart", "the Wise", "the Younger",
        "the Bold", "Stoneward", "Strider", "Oakheart",
        "of Gondor", "of Rohan", "of Arnor", "of Bree",
        "of the Mark", "of the White City", "Greycloak",
        "Stormcrow", "the Tall", "the Quick", "II",
        "III", "the Wanderer", "Crownless",
        "Stonefoot", "the Vigilant",
    ),
    "elf": (
        "the Fair", "Star-eyed", "Moonsinger", "Silver-tongued",
        "of Lothlorien", "of Imladris", "of the Greenwood",
        "of Mithlond", "the Sun-bright", "the Wise",
        "the Singer", "the Bowyer", "the Pathfinder",
        "Skywatcher", "Silverleaf", "Stareyed",
        "Goldenbough", "the Ageless", "the Twice-Born",
        "of the West", "the Quenya-tongued", "the Sea-stained",
        "Whitepetal", "the Lorekeeper",
    ),
    "dwarf": (
        "Ironbeard", "Stonefoot", "Goldfinder", "Anvilheart",
        "Hammerhand", "the Stout", "the Mighty", "the Bold",
        "of Erebor", "of the Iron Hills", "of Khazad-dum",
        "of Belegost", "Forgewright", "Stonebreaker",
        "Deepdelver", "Coalbeard", "the Younger", "II",
        "III", "the Cup-Bearer", "Runesinger", "Axebreaker",
        "Steelpalm", "Oakshield",
    ),
}
# Back-compat alias: a few callers still import RACE_NAMES from the
# pre-procedural era. Keep a flat name list per race so they don't
# break. The procedural _race_name() below is what new_game() uses.
RACE_NAMES = RACE_FIRST_NAMES


def _race_name(race, rng):
    """Pick a seed-stable LOTR-flavoured name for the hero.

    Returns ``"<First> <Epithet>"``. ``rng`` is a ``random.Random``
    instance, so two calls with the same seed/state produce the
    same name. Falls back to the human pool for unknown races.
    """
    first_pool = RACE_FIRST_NAMES.get(race) or RACE_FIRST_NAMES["human"]
    epi_pool = RACE_EPITHETS.get(race) or RACE_EPITHETS["human"]
    return f"{rng.choice(first_pool)} {rng.choice(epi_pool)}"


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_HTML_RE = re.compile(r"<[^>]+>")

# Words in a monster name that flag it as undead. Shared between the
# combat threat-assessment branch and the tomb-proximity tracker in
# _monster_obs -- a tomb is the ONLY way undead spawn at typical
# playtest depths (game_systems.undead_guardian branch), so any combat
# with one of these names is a reliable tell that the agent is next to
# a tomb and a higher-tier ELITE UNDEAD waits at one of the other
# adjacent guardian rooms. Matched against word boundaries via the
# `_is_undead_name` helper -- substring matching wrongly flagged
# Lichen (a fungal plant creature) as undead because "lich" is in
# "lichen". User-flagged: "Lichens don't signal a tomb."
_UNDEAD_NAME_TOKENS = (
    "wraith", "lich", "skeleton", "vampire",
    "ghost", "zombie", "spectral", "phantom",
    "mummy", "specter", "death knight", "demilich",
    "undead",
)
import re as _re
_UNDEAD_NAME_RE = _re.compile(
    r"\b(" + "|".join(_re.escape(t) for t in _UNDEAD_NAME_TOKENS) + r")\b"
)


def _is_undead_name(name):
    """Word-boundary match against _UNDEAD_NAME_TOKENS. Lower-case the
    name first. Returns False for unrelated names that contain a token
    as a substring (e.g. "Lichen" wrongly matched "lich" under the
    prior substring loop)."""
    if not name:
        return False
    return bool(_UNDEAD_NAME_RE.search(name.lower()))

# Status effects that LOSE HP EVERY TURN -- poison ticks, fire burn,
# damage-over-time, life-drain. With one of these active the agent
# should bail out of combat (fleeing breaks the engagement, the tick
# continues but the monster doesn't add hits). Used for the combat
# flee branch + the game_loop avoid-step-into-M gate.
_TICKING_STATUS_TYPES = frozenset({
    "poison", "damage_over_time", "burn", "life_drain",
})
# Status effects that DEGRADE combat performance but don't kill on
# their own (weakness reduces damage, defense_penalty / blindness
# hurts hit rate, confusion randomises movement, sticky_hands blocks
# attacks). Agent SHOULD still avoid stepping into NEW fights with
# these active, but shouldn't disengage from a fight already in
# progress -- fleeing wastes turns the status would have ticked off
# anyway, and the monster is usually still there when the debuff
# wears off.
_DEBUFF_STATUS_TYPES = frozenset({
    "weakness", "defense_penalty", "blindness", "confusion",
    "sticky_hands",
})
# Status effects that immobilise -- web, paralysis, freeze. The
# game refuses move + attack actions while these are active. Don't
# flee (movement refused) and don't waste turns trying. Stand and
# heal / cast / wait the duration out.
_IMMOBILISING_STATUS_TYPES = frozenset({"web", "paralysis", "freeze"})
# Union: any of these makes the agent treat itself as "weak" for the
# game_loop AVOID gate, but only _TICKING_STATUS_TYPES forces a flee
# mid-combat.
_DANGEROUS_STATUS_TYPES = (
    _TICKING_STATUS_TYPES | _DEBUFF_STATUS_TYPES | _IMMOBILISING_STATUS_TYPES
)


def _strip_markup(s):
    if not isinstance(s, str):
        return s
    return _HTML_RE.sub("", _ANSI_RE.sub("", s))


def _strip_markup_list(lines):
    return [_strip_markup(line) for line in lines]


def _lantern_obs(pc):
    """Snapshot of lantern + spare-fuel state so the smart policy can
    decide when to light up and when to buy refills. The Lantern lives
    in inventory and ticks `fuel_amount`; LanternFuel items refill +10
    per use (auto-applied when fuel hits 0)."""
    from .items import Lantern as _L, LanternFuel as _LF
    lantern = None
    spare_fuel = 0
    for it in pc.inventory.items:
        if isinstance(it, _L):
            lantern = it
        elif isinstance(it, _LF):
            spare_fuel += getattr(it, "count", 1) or 1
    if lantern is None:
        return None
    return {
        "fuel": lantern.fuel_amount,
        "spare_fuel_uses": spare_fuel,
        "upgrade_level": getattr(lantern, "upgrade_level", 0),
    }


def _neighbour_coord(player, direction):
    """Translate an n/s/e/w direction key into the (x, y) cell the
    player would step onto. Used by the wayfinder when it needs the
    coords (not just the room_type) of an adjacent tile -- e.g. to
    check whether a neighbouring N is a dungeon we already hold the
    key for."""
    dx, dy = {"n": (0, -1), "s": (0, 1),
              "e": (1, 0), "w": (-1, 0)}.get(direction, (0, 0))
    return player["x"] + dx, player["y"] + dy


def _equipped_obs(pc):
    """Snapshot of the player's equipped weapon + armor. Lets the smart
    policy notice when its gear is wearing out and walk to a vendor."""
    def slot(it):
        if it is None:
            return None
        max_d = getattr(it, "max_durability", None)
        cur_d = getattr(it, "durability", None)
        return {
            "name": it.name,
            "durability": cur_d,
            "max_durability": max_d,
            "is_broken": bool(getattr(it, "is_broken", False)),
            "durability_pct": (cur_d / max_d) if (max_d and max_d > 0) else None,
            "buc_status": getattr(it, "buc_status", "uncursed"),
            "buc_known": bool(getattr(it, "buc_known", False)),
            "is_sealed": bool(getattr(it, "is_sealed", False)),
            # Power stat (already includes upgrade_level via the property).
            # The bonus is 0 when the item is broken, but we report the
            # raw value so the policy can decide based on intended power.
            # Also surface base_*_bonus (the template's intrinsic
            # power) and upgrade_level (Scroll of Upgrade increments)
            # so the report can show "+5 atk (3 base + 2 upgrades)".
            "attack_bonus": getattr(it, "attack_bonus", None),
            "defense_bonus": getattr(it, "defense_bonus", None),
            "base_attack_bonus": getattr(it, "_base_attack_bonus", None),
            "base_defense_bonus": getattr(it, "_base_defense_bonus", None),
            "upgrade_level": getattr(it, "upgrade_level", 0),
            "item_level": getattr(it, "level", 0),
            # Blacksmith repair cost estimate -- 80% of the vendor
            # formula. Exposed so smart_policy can refuse to enter
            # the blacksmith repair option when broke (otherwise
            # the handler logs 'Not enough gold' but stays in
            # blacksmith_mode, and the policy re-issues the same
            # key forever -- caught as stuck=loop on s=1234 dwarf
            # F5: 850+ turns mashing '2' with 4g in pocket).
            "repair_cost_est": _repair_cost_est(it),
        }
    out = {"weapon": slot(pc.equipped_weapon),
           "armor":  slot(pc.equipped_armor)}
    # Gear-only 1-based slot index of each equipped item in the
    # sorted-inventory-filtered-to-(Weapon|Armor) view -- the same
    # ordering process_upgrade_scroll_action builds its menu from
    # (items.py:2123-2127). Exposed here because obs.inventory gets
    # filter-narrowed when gs.inventory_filter is set ('use' /
    # 'equip' / 'eat'), so an in-mode scroll picker can't always
    # walk obs.inventory to find the equipped slot.
    from .characters import get_sorted_inventory
    gear_only = [
        i for i in get_sorted_inventory(pc.inventory)
        if isinstance(i, (Weapon, Armor))
    ]
    weapon_gear_idx = None
    armor_gear_idx = None
    for idx, item in enumerate(gear_only, 1):
        if item is pc.equipped_weapon and weapon_gear_idx is None:
            weapon_gear_idx = idx
        if item is pc.equipped_armor and armor_gear_idx is None:
            armor_gear_idx = idx
    out["weapon_gear_idx"] = weapon_gear_idx
    out["armor_gear_idx"] = armor_gear_idx
    return out


def _repair_cost_est(item):
    """Cheap recomputation of items.get_repair_cost() * 0.80 (the
    blacksmith specialist discount). Returns 0 when the item is full
    durability or lacks the inputs."""
    max_d = getattr(item, "max_durability", 0) or 0
    cur_d = getattr(item, "durability", 0) or 0
    missing = max_d - cur_d
    if missing <= 0:
        return 0
    value = getattr(item, "value", 0) or 0
    level = getattr(item, "level", 0) or 0
    cost_per_point = max(1, value // 50) + level
    return max(1, int(missing * cost_per_point * 0.80))


def _item_category(item):
    """Coarse category tag so the smart policy can filter inventory + vendor
    listings without needing the full item class hierarchy."""
    if isinstance(item, Potion):
        ptype = getattr(item, "potion_type", "")
        if ptype == "healing":
            return "potion_healing"
        if ptype == "mana":
            return "potion_mana"
        return f"potion_{ptype}" if ptype else "potion"
    if isinstance(item, (Food, Meat)):
        if isinstance(item, Meat) and getattr(item, "is_rotten", False):
            return "food_rotten"
        return "food"
    if isinstance(item, Weapon):
        return "weapon"
    if isinstance(item, Armor):
        return "armor"
    if isinstance(item, Spell):
        return "spell"
    # Scrolls get their own tag so the policy can target them for
    # vendor-identify (upgrade scrolls are the high-value find the
    # user explicitly called out). Importing Scroll lazily keeps the
    # module-level import block tight.
    from .items import Scroll
    if isinstance(item, Scroll):
        return "scroll"
    # Lantern + LanternFuel get explicit tags so the policy can refuel
    # without needing isinstance checks across module boundaries.
    # Trophy gets its own tag so the taxidermist policy can detect
    # whether there's anything to sell / hand in.
    cls = type(item).__name__
    if cls == "Lantern":
        return "lantern"
    if cls == "LanternFuel":
        return "lantern_fuel"
    if cls == "Trophy":
        return "trophy"
    if cls == "CookingKit":
        return "cooking_kit"
    return "other"


def new_game(seed=None, playtest_mode=False, name="Tester",
             race="human", gender="non-binary",
             int_bonus=0, spells=None, starter_pack=True,
             fog_of_war=True):
    """Initialise a fresh headless game. Returns a ``PlaytestSession``.

    ``race`` applies the same stat modifiers the UI's character-creation
    flow uses (see game_systems.process_character_creation_action). Pass
    ``int_bonus`` to bump intelligence past the spell-casting threshold
    (int > 15) so an Elf can actually cast on turn one. ``spells`` is an
    iterable of SPELL_TEMPLATES names to pre-memorize. ``starter_pack``
    seeds the same gear the in-game starting_shop hands out -- Dagger +
    Leather Armor (auto-equipped), Lantern, 4 Minor Healing Potions,
    3 Rations -- so the agent isn't punching monsters bare-fisted.
    """
    if seed is not None:
        _stdlib_random.seed(seed)
    race = (race or "human").lower()
    if race not in RACE_MODS:
        raise ValueError(f"unknown race {race!r}; choose from {list(RACE_MODS)}")

    # Reset every gs global the UI's new-game path resets. The game_state
    # module is module-level mutable, so a previous run leaks unless we
    # explicitly clear here.
    gs.PLAYTEST = playtest_mode
    gs.log_lines = []
    gs.prompt_cntl = "game_loop"
    gs.previous_prompt_cntl = ""
    gs.game_should_quit = False
    gs.lets_go = False
    gs.html_cache = ""
    gs.loot_toasts = []

    gs.active_monster = None
    gs.active_vendor = None
    gs.active_altar_state = None
    gs.active_scroll_item = None
    gs.active_flare_item = None
    gs.active_foresight_scroll = None
    gs.active_flee_state = None
    gs.active_spell_choice = None
    gs.active_towel_item = None
    gs.active_library_state = None
    gs.inventory_filter = None
    gs.vendor_action = None
    gs.spell_memo_action = None
    gs.altar_action = None
    gs.shop_message = ""
    gs.pending_sell_item = None
    gs.pending_sell_item_index = None
    gs.zotle_puzzle = None
    gs.active_zotle_teleporter = False
    gs._pending_load = None

    # Combat / turn state — these leak between runs in batch testing,
    # causing seed=42 Arwen to inherit Tauriel's shrunk status on bug
    # floors and softlock in stairs_down_mode forever.
    gs.player_is_shrunk = False
    gs.bug_queen_defeated = False
    gs.player_passed_bug_quest = False
    gs.bug_shrink_moves = 0
    gs.bug_kills_this_level = 0
    gs.bug_level_floors = {}
    gs.monster_acts_first = False
    gs.monster_initiative_pending = False
    gs.last_spell_cast = None
    gs.spell_charging = None
    gs.last_concentration_roll = None
    gs.monster_defeated_anim = None
    gs.victory_monster_name = None
    gs.last_dice_rolls = []
    gs.unique_treasures_spawned = set()
    gs.last_monster_damage = 0
    gs.last_player_damage = 0
    gs.last_player_blocked = False
    gs.last_player_status = None
    gs.last_monster_status = None
    gs.last_player_heal = 0
    gs.last_monster_damage_badge = None
    gs.last_player_damage_badge = None
    gs.pre_round_monster_hp = None
    gs.pre_round_player_hp = None

    initialize_identification_system()

    gs.my_tower = Tower()
    gs.my_tower.add_floor(
        gs.specified_chars, gs.required_chars,
        gs.grid_rows, gs.grid_cols,
        gs.wall_char, gs.floor_char,
        p_limits=gs.p_limits_val, c_limits=gs.c_limits_val,
        w_limits=gs.w_limits_val, a_limits=gs.a_limits_val,
        l_limits=gs.l_limits_val, dungeon_limits=gs.dungeon_limits_val,
        t_limits=gs.t_limits_val, garden_limits=gs.garden_limits_val,
        o_limits=gs.o_limits_val,
        b_limits=gs.b_limits_val, f_limits=gs.f_limits_val,
        q_limits=gs.q_limits_val, k_limits=gs.k_limits_val,
        x_limits=gs.x_limits_val,
    )

    ch_x, ch_y = 1, 1
    mods = RACE_MODS[race]
    stats = {k: BASE_STATS[k] + mods[f"{k}_mod"] for k in BASE_STATS}
    # Pick a race-themed name when the caller didn't override the
    # default. _stdlib_random is already seeded above if a seed was
    # passed, so the name is stable across reruns of the same seed.
    if name == "Tester":
        name = _race_name(race, _stdlib_random)
    pc = Character(
        name=name,
        health=stats["health"],
        attack=stats["attack"],
        defense=stats["defense"],
        strength=stats["strength"],
        dexterity=stats["dexterity"],
        intelligence=stats["intelligence"] + int_bonus,
        x=ch_x, y=ch_y, z=0,
    )
    pc.race = race
    # Mirror game_systems.py: positive race health_mod feeds
    # base_max_health_bonus so it actually raises max_health (which is a
    # property over level + strength + base_max_health_bonus). Without
    # this the dwarf +30 would clamp at the formula's natural max.
    if mods["health_mod"] > 0:
        pc.base_max_health_bonus = mods["health_mod"]
    pc.gender = gender
    pc.character_class = "Adventurer"
    pc.health = min(stats["health"], pc.max_health)
    pc.mana = pc.max_mana  # re-clamp after the int_bonus bumps max_mana
    pc.gold = 500
    pc.memorized_spells = []
    if starter_pack:
        # Mirror Vendor(starting=True) inventory at vendor.py:93-104,
        # plus the _auto_equip_starting_shop_item behaviour: the weapon
        # + armor land in BOTH the equipment slots and inventory.items
        # (the in-game buy flow at vendor.py:485-499 adds the item to
        # inventory first, then equips by reference -- so equipped
        # gear ALSO appears in inventory.items, which is what lets the
        # vendor repair handler at vendor.py:733-749 see it).
        from .items import Lantern as _Lantern, Food as _Food, LanternFuel as _LF
        # Race-flavoured starter weapon, mirroring vendor.py:93+ now
        # that the starting shop gives dwarves a Battleaxe.
        if race == "dwarf":
            starter_weapon = Weapon(
                "Battleaxe", "A heavy two-handed axe of dwarven make.",
                attack_bonus=4, value=25, level=0, upgrade_level=0,
            )
        else:
            starter_weapon = Weapon(
                "Dagger", "A small, sharp blade.",
                attack_bonus=2, value=10, level=0, upgrade_level=0,
            )
        leather = Armor(
            "Leather Armor", "Light leather armor.",
            defense_bonus=3, value=50, level=0, upgrade_level=0,
        )
        pc.inventory.add_item_quiet(starter_weapon)
        pc.inventory.add_item_quiet(leather)
        pc.equipped_weapon = starter_weapon
        pc.equipped_armor = leather
        pc.inventory.add_item_quiet(_Lantern(
            "Lantern", "Provides continuous light with fuel.",
            fuel_amount=80, light_radius=7, value=30, level=0,
        ))
        # Starter pack also includes 2 fuel canisters (40 fires).
        # Combined with the lantern's 80 base = 120 fires before
        # the agent needs to hit a vendor for more, enough to
        # explore F1-F3 thoroughly even with aggressive fog reveal.
        for _ in range(2):
            pc.inventory.add_item_quiet(_LF(
                "Lantern Fuel", "A small flask of oil for your lantern.",
                value=5, level=0, fuel_restore_amount=20,
            ))
        pc.inventory.add_item_quiet(_Food(
            "Rations", "Standard travel rations.",
            value=10, level=0, nutrition=50, count=8,
        ))
        # User-requested balance pass: Iron Rations in starter pack
        # to extend the early-floor food window (70 nutrition each
        # vs 50 for plain Rations).
        pc.inventory.add_item_quiet(_Food(
            "Iron Rations",
            "Military-grade rations. Tasteless but highly nutritious.",
            value=30, level=3, nutrition=70, count=4,
        ))
        # Cooking Kit also in the starter pack. Earlier balance pass
        # framed cooking as a "mid-game depth bonus" gated on a F3+
        # vendor, but the 160-seed audit showed 40% of runs never
        # visit a vendor at all and 67% die starving. Mirror the
        # UI starting-shop change in vendor.py that put a kit on
        # the F1 starter inventory: every fresh agent gets one
        # auto-cook tool in the bag from turn 0. The kit is heavy
        # (120g value, but free in the starter) and pays itself
        # off after ~2 monster meat drops.
        from .items import CookingKit as _CookingKit
        pc.inventory.add_item_quiet(_CookingKit())
        for _ in range(4):
            pc.inventory.add_item_quiet(Potion(
                "Minor Healing Potion",
                "A small vial of red liquid that heals minor wounds.",
                value=30, level=0,
                potion_type="healing", effect_magnitude=30,
            ))
        pc.gold = 500 - 210
    if spells:
        spell_index = {s.name.lower(): s for s in SPELL_TEMPLATES}
        for raw in spells:
            key = raw.strip().lower()
            if not key:
                continue
            if key not in spell_index:
                raise ValueError(
                    f"unknown spell {raw!r}; check items.py:SPELL_TEMPLATES"
                )
            pc.memorized_spells.append(spell_index[key])
    gs.player_character = pc
    gs.my_tower.floors[0].grid[ch_y][ch_x].discovered = True

    gs.encountered_monsters = {}
    gs.encountered_vendors = {}
    gs.newly_unlocked_achievements = []
    gs.curing_kit_stocked = False
    gs.curing_kit_floor = _stdlib_random.randint(0, 9)
    gs.achievement_notification_timer = 0

    gs.dungeon_keys = {}
    gs.unlocked_dungeons = {}
    gs.looted_dungeons = {}
    gs.looted_tombs = {}
    gs.harvested_gardens = {}
    gs.harvested_fey_floors = set()
    gs.haunted_floors = {}
    gs.ephemeral_gardens = {}
    gs.pending_tomb_guardian_reward = None
    gs.searched_libraries = {}

    rune_keys = ('battle', 'treasure', 'devotion', 'reflection',
                 'knowledge', 'secrets', 'eternity', 'growth')
    gs.runes_obtained = {k: False for k in rune_keys}
    gs.shards_obtained = {k: False for k in rune_keys}
    gs.altar_piety = {i: 0 for i in range(1, 9)}
    gs.rune_progress = {
        'monsters_killed_total': 0,
        'chests_opened_total': 0,
        'pools_drunk_total': 0,
        'spells_learned_total': 0,
        'unique_spells_memorized': set(),
        'dungeons_unlocked_total': 0,
        'tombs_looted_total': 0,
        'gardens_harvested_total': 0,
    }
    gs.champion_monster_available = False
    gs.legendary_chest_available = False
    gs.ancient_waters_available = False
    gs.codex_available = False
    gs.master_dungeon_available = False
    gs.cursed_tomb_available = False
    gs.world_tree_available = False
    gs.gate_to_floor_50_unlocked = False

    gs.game_stats = {
        'monsters_killed': 0,
        'max_floor_reached': 0,
        'spells_learned': 0,
        'spells_cast': 0,
        'times_poisoned': 0,
        'chests_opened': 0,
        'dungeons_looted': 0,
        'vendors_sold_to': set(),
    }

    _trigger_room_interaction(gs.player_character, gs.my_tower)
    return PlaytestSession(fog_of_war=fog_of_war)


ACTION_HINTS = {
    "game_loop":     "n s e w | d (descend) u (ascend) | i (inventory)",
    "combat_mode":   "a (attack) f (flee) c (cast) I (item) x (back)",
    "spell_casting_mode": "1..N (spell slot) x (cancel)",
    "inventory":     "1..9 (slot) x (back) e (equip-filter) u (use-filter)",
    "chest_mode":    "o (open) n s e w (walk off; chest handler doesn't accept 'l')",
    "vendor_shop":   "b (buy) s (sell) x (leave)",
    "stairs_down_mode": "d (descend) x (cancel)",
    "stairs_up_mode":   "u (ascend) x (cancel)",
    "oracle_mode":      "g (gaze) | n s e w to leave",
    "alchemist_mode":   "c (combine) | '<a> <b>' to brew slots a+b | x (cancel) | n s e w to leave",
    "war_room_mode":    "1 (intel - free) 2 (raid - 100+f*5g) | n s e w to leave",
    "taxidermist_mode": "<N> (complete collection N) | s (sell trophies) | x (leave)",
    "death_screen":  "<game over>",
}


class PlaytestSession:
    """One playthrough. Holds a log-pointer + turn counter; state lives in gs."""

    def __init__(self, fog_of_war=True):
        self._log_pointer = len(gs.log_lines)
        self.turn = 0
        self.last_action = None
        self.last_error = None
        # Feature tiles (vendor / chest / altar / etc.) the policy has
        # already stepped onto -- exposed via `visited_features` in obs
        # so the wayfinder can skip them and avoid oscillating between
        # an altar tile and an empty neighbour for 50+ turns.
        self.visited_features = set()
        # Recent positions for anti-backtrack. The BFS first_step + SE
        # tiebreak can flip direction each turn when the agent is on a
        # 2-tile saddle point between frontiers (seed=42 dwarf burned
        # 4857 turns of a 5000-turn budget ping-ponging n/s). Tracking
        # the last 4 (z, x, y) tuples lets the policy break ties by
        # preferring directions that DON'T re-step on a recent tile.
        self.recent_positions = []
        # Longer history just for 2-tile-oscillation detection. The
        # 4-entry recent_positions above is meant for anti-backtrack
        # tiebreaking; an actual stable oscillation needs a wider
        # window to identify (both tiles are 'recent' so swap-if-
        # backtrack finds no alternative and the wayfinder keeps
        # returning the same direction). 16 entries covers period-2
        # / period-3 / period-4 bounces with margin.
        self.position_history = []  # last 16 (z, x, y)
        # Consecutive turns the 2-tile oscillation detector has been
        # tripping. Lets the policy distinguish a transient wobble
        # (a few turns of n/s while the wayfinder rebuilds its
        # target) from a real wedge (50+ turns stuck on the same
        # 2-tile pair). Used by the stairs_up_mode 'use the stairs
        # to escape' valve so it only fires on persistent loops,
        # avoiding the descend/ascend cancellation that killed the
        # earlier symmetric stair-island valve in build 318.
        self.osc_streak = 0
        self._last_osc_pair = None  # the (a, b) pair the streak is on
        # z-indexes of floors the agent escaped from via the stairs_up
        # osc-valve. Recorded the moment the policy issues 'u' to
        # break a 50-turn 2-tile wedge. stairs_down_mode reads this
        # set to refuse re-descent into a region-split fragment --
        # otherwise the escape valve fires, the agent lands on
        # F(N-1)'s D and the default 'd' sends them right back into
        # the same wedge floor. Caught on s=88 human F2 (1,1)U <->
        # (1,2): without this set the agent ping-ponged for 1500+
        # turns alternating stair-floor and wedge-floor.
        # z -> turn the wedge marker was added. stairs_down_mode /
        # game_loop strip D from priority when (current_z + 1) is in
        # this dict. The 500T age cap stops permanent blocks: an
        # agent who escapes F2 wedge, exhausts F1, and is stuck
        # (D reachable on F1 but goes to wedged F2) should retry
        # F2 after a budget rather than starve on F1. After 3
        # wedge-add events on the same floor, the wedge becomes
        # PERMANENT (no expiry) and the agent should seek a warp
        # to skip past entirely -- this floor is provably impassable
        # via stairs and we've burned 1500+ turns confirming it.
        self.wedge_floors = {}  # z -> turn-added (most recent)
        self.wedge_count = {}   # z -> number of times marked
        self._WEDGE_EXPIRY_TURNS = 500
        self._WEDGE_PERMANENT_AFTER = 3
        # Early-termination flag for runs the agent CAN'T escape:
        # no D / U / W reachable on this floor, no Scroll of
        # Teleport / Descent in the bag, and 1500+ turns burned
        # walking the same tile set. The agent isn't dying (food +
        # full HP) but it can't make any further progress either --
        # continuing the loop just wastes harness CPU. Detected via
        # _is_truly_trapped() each step; the main loop breaks when
        # set. Caught on s=16180 human 3791T on F3 (region-split
        # entered via stairs down, 22 tiles visited, 0 kills out
        # of 16 monsters because all M were in the unreachable
        # region, no escape items in bag).
        self.early_terminated = False
        self.early_terminate_reason = None
        # Per-floor walkable-tile coverage: set of (x, y) the player
        # has stood on for the current floor. Reset on descent. Used
        # by the policy's tile-coverage descent gate to leave a floor
        # once enough has been swept, even if a far beneficial remains.
        self.visited_tiles_this_floor = set()
        # Turn at which a NEW tile (not in visited_tiles_this_floor)
        # was last entered. Used by the trapped detector: if the
        # agent has stopped making exploration progress -- visiting
        # the same tiles repeatedly without growing the set -- they
        # are wedged on a tiny island. Reset on floor change.
        self.last_new_tile_turn = 0
        # Per-floor revisit counter: dict {(x,y): visit_count}. Reset
        # on floor change. Used by the wedge detector -- when the
        # agent has revisited the current tile 6+ times the wayfinder
        # has lost the plot and we fire Hail-Mary item use to break
        # the loop (Durin seed=314 burned 2345 turns at HP=1 on F2
        # bouncing e/w in a 3-tile corridor with no D reachable).
        self.floor_visit_count = {}
        # Per-floor set of inventory action strings already attempted
        # during a wedge episode. Reset on floor change. Without
        # this the Hail Mary in the inventory branch alternates
        # u1<->u2 forever (last_action only blocks IMMEDIATE repeats,
        # not 2-step loops): Forlong seed=314 human burned 2900 turns
        # alternating two unidentified scrolls that both refused to
        # consume out of combat.
        self.wedge_attempted_actions = set()
        # Floor-scoped Hail-Mary tracker. wedge_attempted_actions
        # above resets on EVERY MOVE (per-tile episode), so a
        # 5-tile bounce loop re-tries the same unidentified potion
        # on every tile -- 100 moves = 100 inventory opens. This
        # set persists across moves on the same floor: once we've
        # tried a slot's escape item, we don't keep re-trying it
        # until the floor changes. Caught on s=16180 human F3:
        # unidentified Healing Potion in slot 6 not consumed at
        # full HP (game: 'Already at full health!'), agent
        # re-tried u6 on every tile of a 22-tile bounce for 3800T.
        self.wedge_tried_this_floor = set()
        # Blocked-directions tracker. When the agent issues a
        # cardinal-direction action (n/s/e/w from game_loop or a
        # flee/move-accepting mode) and the position doesn't change,
        # that direction is added here. Cleared whenever the agent
        # successfully moves OR changes floors. Surfaces in obs so the
        # wayfinder can avoid retrying the same wall over and over --
        # Oin/Legolas/Boromir burned 2592-2780 turns each sending 's'
        # into a wall because the BFS first_step kept resolving south
        # and anti-backtrack only fires on POSITION CHANGE.
        self.blocked_directions = set()
        # Floors where the agent has fought (or is fighting) an undead.
        # Tomb-adjacent guardian rooms are the only way undead spawn at
        # those depths (see game_systems.py's undead_guardian branch),
        # so seeing an undead is a near-100% reliable "there's a tomb
        # on this floor and a higher-tier ELITE UNDEAD is one of the
        # other adjacent guardians" tell. The wayfinder uses this when
        # weak to drop M/T from priority and stay near already-revealed
        # tiles instead of rushing into fog where another wraith may be
        # waiting. Cleared whenever the agent changes floors (the next
        # floor needs its own undead-sighting to be flagged).
        self.suspected_tomb_floors = set()
        # Deepest floor index reached via the canonical stairs-down
        # path (the agent stood on a D tile and pressed 'd'). Used as
        # the retreat target when a warp drops the agent below this
        # depth: the user's framing is that warp-skipped floors are
        # near-instakill because the agent doesn't have the gear /
        # level / item supply for the deeper monsters. Whenever
        # pc.z > max_z_via_stairs, obs.retreat_to_floor flags the
        # floor we should ascend back to, and the wayfinder + stairs
        # mode policies switch from descend-and-clear into ascend-
        # back mode until pc.z <= max_z_via_stairs again.
        self.max_z_via_stairs = 0
        # Post-flee recovery tracker: the turn at which the agent
        # most recently issued a flee from combat_mode, plus the HP
        # ratio at that flee. Only damage-fled flees (HP at flee was
        # < ~70%) trigger the post-flee heal-up; tough-monster flees
        # at full HP don't need recovery -- the agent should find a
        # different path. User-flagged: Celeborn the elf was fleeing
        # from a wraith at HP24, getting a free monster attack on
        # every flee attempt, then immediately re-engaging without
        # healing. None set means no recent flee.
        self.last_flee_turn = None
        self.last_flee_hp_pct = None
        # Kills logged on the current floor. Incremented every time
        # the agent transitions into combat_victory mode (one entry
        # per defeated monster). Reset on floor change. Used by the
        # grind-first descent gate so under-levelled agents stay on
        # the current floor banking XP instead of pushing into a
        # depth they can't handle.
        self.kills_on_floor = 0
        # Fog of war: when True, the neighbour + nearest-feature obs
        # respect room.discovered so the agent has to actually walk over
        # (or lantern-light) tiles before knowing what's there. The
        # in-game starting condition; default-on for realistic playtest.
        self.fog_of_war = fog_of_war
        # Floor-arrival turn lets the policy force descent when it has
        # been stuck on the same floor too long. Without it, a single
        # unreachable beneficial (behind a wall the greedy walker can't
        # navigate around) makes clear-before-descend loop forever --
        # dwarf seed 7 spent 5000 turns on floor 1 in the last batch
        # because of this.
        self.floor_arrival_turn = 0
        self._last_floor = 0
        # Per-floor exploration totals, snapshotted on first arrival.
        # User-requested: 'evaluate exp + treasure left on each level
        # to see if better exploring would help with survival.' For
        # each floor we capture monsters / chests / beneficials /
        # vendors / tombs / dungeons available, then the report
        # combines with kills_by_floor + visited_features to compute
        # the engagement ratios.
        # Shape: floor_totals[z] = {"M":N, "C":N, "G":N, ...,
        #   "xp_pool": expected XP if every M is killed}
        self.floor_totals = {}

    def _snapshot_floor_totals(self, z):
        """Tally the floor's monster / chest / beneficial-room totals
        the first time the player arrives on it AND on every later
        arrival, accumulating the M / XP pool to account for
        respawns. Static tiles (C / V / T / N / B / F / G / L / O /
        A / P / Q / K / X) are captured once; only M tiles and the
        derived xp_pool grow on re-arrivals.

        Why re-snapshot M: build-309 grid surfaced runs with
        kill_pct = 226% (Durin Forgewright s=314 dwarf F4) because
        the snapshot was a one-shot at first floor visit. Agents
        that revisit floors (warp + retreat + re-descend) encounter
        FRESH M spawns each time, so the kill counter sails past
        the static pool. Re-arrival accumulation closes the loop.

        XP pool respects per-M-tile property markers so the formula
        doesn't underestimate elite undead / champions / vault
        keepers / boss arenas.
        """
        already_seen = z in self.floor_totals
        floor = gs.my_tower.floors[z]
        if not already_seen:
            counts = {
                "M": 0, "C": 0, "G": 0, "L": 0, "O": 0, "A": 0, "P": 0,
                "V": 0, "T": 0, "N": 0, "Q": 0, "K": 0, "B": 0, "F": 0,
                "X": 0,
            }
            counts["xp_pool"] = 0
        else:
            # On a return visit, keep the static-tile totals as they
            # were and only re-tally M + xp_pool for the new spawns
            # we're about to encounter. Tiles never UN-spawn -- we
            # always add, never subtract.
            counts = self.floor_totals[z]
        # Per-monster XP estimate accounting for spawn-level offsets:
        #   * tomb_elite -- spawn at floor+1 (game_systems.py:2613)
        #   * undead_guardian (non-elite) -- spawn at floor (z)
        #   * has_zots_guardian / is_boss_arena -- vault defender,
        #     awards (level+1)*100 (4x baseline, game_systems.py:727)
        #   * default -- spawn at z (game_systems.py:2771)
        # The (L+1)*8 + L²*2 formula is the canonical per-kill XP.
        def _kill_xp(lvl):
            return (lvl + 1) * 8 + lvl * lvl * 2

        # Pool computation strategy: rebuild from scratch on every
        # arrival using two sources of truth:
        #   (1) gs.encountered_monsters[(x,y,z)] for any tile the
        #       agent has ALREADY interacted with -- gives the real
        #       monster.level (handles champion/platino/spirit/elite
        #       upgrades + revisit respawns). Includes dead monsters
        #       (the dict isn't pruned on death).
        #   (2) Static tile scan for un-encountered M tiles, using
        #       property markers to estimate spawn level.
        # The previous accumulator double-counted on revisit because
        # the same M tile got tallied each pass; this rebuild-from-
        # source approach matches xp_earned which only logs once per
        # kill.
        new_xp = 0
        m_count = 0
        floor_monsters = {
            (x, y): m for (x, y, mz), m in
            (getattr(gs, "encountered_monsters", {}) or {}).items()
            if mz == z
        }
        # First, credit every encountered monster on this floor.
        for (mx, my), monster in floor_monsters.items():
            lvl = getattr(monster, "level", z)
            props = getattr(monster, "properties", {}) or {}
            m_count += 1
            if props.get("has_zots_guardian") or props.get("is_boss_arena"):
                new_xp += (lvl + 1) * 100
            else:
                new_xp += _kill_xp(lvl)
        # Then walk static tiles for M's that haven't been
        # encountered yet (no entry in floor_monsters).
        for y in range(floor.rows):
            for x in range(floor.cols):
                cell = floor.grid[y][x]
                t = cell.room_type
                if not already_seen and t in counts:
                    counts[t] += 1
                if t == "M" and (x, y) not in floor_monsters:
                    m_count += 1
                    props = cell.properties
                    if props.get("is_platino"):
                        new_xp += _kill_xp(42)
                    elif props.get("has_zots_guardian") or props.get("is_boss_arena"):
                        new_xp += (z + 1) * 100
                    elif props.get("is_champion"):
                        new_xp += _kill_xp(z + 4)
                    elif props.get("tomb_elite"):
                        new_xp += _kill_xp(z + 1)
                    elif props.get("undead_guardian"):
                        new_xp += _kill_xp(z)
                    else:
                        new_xp += _kill_xp(z)
        counts["M"] = m_count
        counts["xp_pool"] = new_xp
        self.floor_totals[z] = counts

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------
    def observe(self):
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        room = floor.grid[pc.y][pc.x]
        # Snapshot floor totals on arrival (first OR return visit).
        # _last_snapshot_floor tracks the most recently snapshotted
        # floor so we re-tally M (which respawns across visits) once
        # per arrival rather than every observe(). The static-tile
        # counters inside _snapshot_floor_totals are idempotent.
        if getattr(self, "_last_snapshot_floor", None) != pc.z:
            self._snapshot_floor_totals(pc.z)
            self._last_snapshot_floor = pc.z
        # log_lines is capped at 16 — if our pointer is past the end the
        # log was rotated and we just take everything that's left.
        if self._log_pointer > len(gs.log_lines):
            self._log_pointer = 0
        log_delta = gs.log_lines[self._log_pointer:]
        self._log_pointer = len(gs.log_lines)
        # Clear the per-turn BFS cache; the four path-obs methods will
        # share one BFS pass on first access.
        self._bfs_cache = None
        return {
            "turn": self.turn,
            "mode": gs.prompt_cntl,
            "hint": ACTION_HINTS.get(gs.prompt_cntl, "(pass raw key)"),
            "player": {
                "name": pc.name,
                "race": getattr(pc, "race", "human"),
                "hp": pc.health,
                "max_hp": pc.max_health,
                "mana": pc.mana,
                "max_mana": pc.max_mana,
                "hunger": pc.hunger,
                "gold": pc.gold,
                "level": pc.level,
                "xp": pc.experience,
                "strength": pc.strength,
                "dexterity": pc.dexterity,
                "intelligence": pc.intelligence,
                "can_cast": pc.intelligence > 15,
                "floor": pc.z + 1,
                "x": pc.x,
                "y": pc.y,
                "status_effects": list(pc.status_effects.keys()),
                "status_effect_types": [
                    eff.effect_type for eff in pc.status_effects.values()
                ],
                "equipped": _equipped_obs(pc),
                "lantern": _lantern_obs(pc),
                "is_shrunk": bool(gs.player_is_shrunk),
                # Persistent across re-shrinks: True once the player
                # has consumed the Growth Mushroom this run. While
                # True the policy can route to D/U even when shrunk
                # because the stair handlers auto-cure on use.
                "passed_bug_quest": bool(getattr(gs, 'player_passed_bug_quest', False)),
            },
            "memorized_spells": [
                {"slot": i + 1, "name": s.name,
                 "mana_cost": s.mana_cost, "level": s.level,
                 "type": s.spell_type}
                for i, s in enumerate(pc.memorized_spells)
            ],
            "vendor_inventory": self._vendor_obs(),
            "neighbors": self._neighbors_obs(),
            "visited_neighbors": self._visited_neighbors_obs(),
            "nearest_features": self._nearest_features_obs(),
            "feature_paths": self._feature_paths_obs(),
            "frontier_step": self._frontier_step_obs(),
            "nearest_monster_path": self._nearest_monster_path_obs(),
            "recent_step_set": self._recent_step_set(),
            "oscillation": self._oscillation_state(),
            "blocked_directions": sorted(self.blocked_directions),
            "suspected_tomb_floors": sorted(self.suspected_tomb_floors),
            # Cardinal dirs adjacent to a known tomb-guardian M tile.
            # The policy refuses to step into these unless over-levelled.
            "tomb_guardian_dirs": self._tomb_guardian_dirs_obs(),
            "suspected_guardian_coords": self._suspected_guardian_coords_obs(),
            "inferred_guardian_dirs": self._inferred_guardian_dirs_obs(),
            "tomb_suspected_here": pc.z in self.suspected_tomb_floors,
            "max_z_via_stairs": self.max_z_via_stairs,
            # Z-indexes (0-based) the policy has escaped from via the
            # osc-streak 'u' valve. stairs_down_mode skips re-descent
            # into these so the agent doesn't bounce back into a
            # region-split wedge.
            "wedge_floors": sorted(
                z for z, t in self.wedge_floors.items()
                if (self.turn - t < self._WEDGE_EXPIRY_TURNS
                    or self.wedge_count.get(z, 0) >= self._WEDGE_PERMANENT_AFTER)
            ),
            "permanent_wedge_floors": sorted(
                z for z, c in self.wedge_count.items()
                if c >= self._WEDGE_PERMANENT_AFTER
            ),
            # Name of the scroll currently driving upgrade_scroll_mode
            # / identify_scroll_mode -- empty otherwise. Lets the
            # smart_policy compute the scroll's tier cap (Basic +3,
            # Greater +6, ... Eternal +35) and skip consuming when
            # the equipped weapon is already at cap.
            "active_scroll_item": getattr(
                getattr(gs, "active_scroll_item", None), "name", ""
            ) or "",
            # Per-floor kill counter. Used by the grind-first gate so
            # under-levelled agents stay on the floor banking XP.
            "kills_on_floor": self.kills_on_floor,
            # Post-flee recovery window. True for the first 15 turns
            # after a flee that triggered at low HP (< 70%). Tough-
            # monster flees at full HP don't need recovery -- the
            # agent should look for a different path. Outside the
            # window the flag clears so a long-ago flee doesn't keep
            # the agent in heal-up mode.
            "recently_fled": (
                self.last_flee_turn is not None
                and self.last_flee_hp_pct is not None
                and self.last_flee_hp_pct < 0.70
                and (self.turn - self.last_flee_turn) <= 15
            ),
            # Retreat target: when a warp drops the agent below the
            # deepest floor they've reached via canonical stairs, the
            # wayfinder switches into ascend-back mode and aims for
            # this floor index. None when no retreat is needed.
            # Retreat target: when a warp drops the agent BELOW the
            # deepest floor they've reached via canonical stairs by
            # 2 or more, the wayfinder switches into ascend-back mode
            # and aims for this floor index. A single-floor gap (warp
            # F1 -> F2 with max_z_via_stairs = 0) no longer triggers
            # retreat -- if D is reachable on the current floor the
            # agent should descend it normally rather than route back
            # up and re-warp later. Caught on s=99 elf F2: warped from
            # F1, found F2's D reachable at 86% reach, but retreat
            # mode kept tiers = [U, V] and the agent routed onto a W
            # tile, force-warped back to F1, wandered 2000 more turns
            # in circles before starving.
            "retreat_to_floor": (self.max_z_via_stairs
                                 if pc.z > self.max_z_via_stairs + 1
                                 else None),
            "tile_coverage": self._tile_coverage_obs(),
            "nearest_warp_path": self._nearest_warp_path_obs(),
            "dungeon_keys": list(getattr(gs, "dungeon_keys", {}).keys()),
            "keyed_dungeon_target": self._keyed_dungeon_target_obs(),
            "nearest_undiscovered": self._nearest_undiscovered_obs(),
            "turns_on_floor": self.turn - self.floor_arrival_turn,
            "current_tile_visits": self.floor_visit_count.get((pc.x, pc.y), 0),
            "floor_totals": dict(self.floor_totals),
            "turns_since_new_tile": self.turn - self.last_new_tile_turn,
            "wedge_attempted_actions": sorted(self.wedge_attempted_actions),
            # Floor-scoped Hail-Mary tracker. The policy unions
            # this with wedge_attempted_actions when deciding
            # which slots to try -- prevents re-trying a dud
            # potion / scroll on every tile of a bounce loop.
            "wedge_tried_this_floor": sorted(self.wedge_tried_this_floor),
            "room": {
                "type": room.room_type,
                "properties": {
                    k: v for k, v in room.properties.items()
                    if isinstance(v, (bool, int, str, float))
                },
            },
            "monster": self._monster_obs(),
            "inventory": self._inventory_obs(),
            "log": _strip_markup_list(log_delta),
            "alive": pc.is_alive() and gs.prompt_cntl != "death_screen",
            "done": self.is_done(),
            "last_action": self.last_action,
            "last_error": self.last_error,
        }

    def _monster_obs(self):
        m = gs.active_monster
        if m is None or gs.prompt_cntl != "combat_mode":
            return None
        name = _strip_markup(m.name).strip()
        # Edibility check via items.get_monster_meat_info -- returns
        # None for undead / constructs / oozes / fungi etc. Lets the
        # starving-flee policy avoid throwing the agent at fights that
        # produce no meat.
        from .items import get_monster_meat_info
        meat_info = get_monster_meat_info(name)
        # Tomb-proximity tell: undead spawn exclusively as tomb-adjacent
        # guardians at typical playtest depths, so seeing one means a
        # T tile is on this floor and (per the rebalance) one of the
        # other 3 adjacent guardians is an ELITE UNDEAD at floor+1.
        # Mark the floor; the wayfinder drops M/T from priority when
        # weak on a flagged floor so the agent doesn't blunder into a
        # second wraith while limping away from the first.
        is_undead = _is_undead_name(name)
        if is_undead:
            self.suspected_tomb_floors.add(gs.player_character.z)
        return {
            "name": name,
            "level": getattr(m, "level", None),
            "hp": m.health,
            "max_hp": getattr(m, "max_health", m.health),
            "is_edible": meat_info is not None,
            "is_undead": is_undead,
        }

    def _inventory_obs(self):
        # Must mirror handle_inventory_menu's `working_items` exactly --
        # slot numbers in u<N>/eat<N>/e<N> index off the FILTERED sorted
        # list, not raw inventory. Two filters apply:
        #   1. If gs.active_monster is alive (player is in -- or fled --
        #      combat), the handler restricts to combat-usable items
        #      (Potions, Food, Meat, certain scrolls).
        #   2. The inventory_filter sub-mode further narrows to use/equip/eat.
        # Get them wrong and the policy spins on Invalid-item-number.
        # Pull a few extras only used here. (Don't import Potion/Weapon/Armor/
        # Food/Meat -- those are at module top; importing them again in this
        # function would shadow the module names and break helpers below
        # if they ever pre-reference them. See the Meat shadow bug we just
        # fixed in game_systems.py:handle_inventory_menu.)
        from .characters import get_sorted_inventory
        from .items import (Scroll, Flare, Lantern, LanternFuel,
                            Treasure, Towel, CookingKit, CuringKit)
        items = get_sorted_inventory(gs.player_character.inventory)

        # in_combat: ONLY when the game is actually in combat OR the
        # player is currently in the inventory handler (which itself
        # applies the same active_monster filter -- the harness must
        # mirror the destination handler's slot numbering or u<N>
        # hits the wrong item). A stale gs.active_monster lingers
        # after the player flees, so checking the monster alone was
        # filtering obs.inventory mid-VENDOR and causing slot-
        # mismatch loops (vendor's id<N> uses the UNFILTERED sorted
        # inventory): seed=1100 dwarf Fili burned 2926 turns sending
        # `id2` to identify a Minor Healing Potion (obs view) that
        # the vendor mapped to Studded Leather (unfiltered view) and
        # replied "already identified". Now: filter only when the
        # destination handler also filters.
        in_combat = (
            gs.active_monster is not None
            and gs.active_monster.is_alive()
            and gs.prompt_cntl in (
                "combat_mode", "spell_casting_mode",
                "flee_direction_mode", "combat_victory",
                "inventory",
            )
        )
        if in_combat:
            combat_scrolls = ('spell_scroll', 'protection', 'restoration')
            items = [
                i for i in items
                if isinstance(i, (Potion, Food, Meat))
                or (isinstance(i, Scroll)
                    and getattr(i, 'scroll_type', None) in combat_scrolls)
            ]
        if gs.inventory_filter == 'use':
            items = [i for i in items if isinstance(i,
                (Potion, Scroll, Flare, Lantern, LanternFuel,
                 Treasure, Towel, CookingKit, CuringKit))]
        elif gs.inventory_filter == 'equip':
            items = [i for i in items if isinstance(i, (Weapon, Armor, Towel))
                     or (isinstance(i, Treasure)
                         and getattr(i, 'treasure_type', None) == 'passive')]
        elif gs.inventory_filter == 'eat':
            items = [i for i in items if isinstance(i, (Food, Meat))]

        out = []
        for i, item in enumerate(items):
            count = getattr(item, "count", 1) or 1
            entry = {
                "slot": i + 1,
                "name": getattr(item, "name", repr(item)),
                "count": count,
                "category": _item_category(item),
            }
            # Meat: surface the rot timer + cooked flag so the policy
            # can eat raw monster meat before it spoils (30 raw / 100
            # cooked / 200 cooked-with-curing-kit moves before rot).
            if isinstance(item, Meat):
                entry["rot_timer"] = getattr(item, "rot_timer", None)
                entry["is_cooked"] = bool(getattr(item, "is_cooked", False))
                entry["is_rotten"] = bool(getattr(item, "is_rotten", False))
            # Gear: surface durability so the policy can spot worn /
            # broken equipment and budget for repairs at vendors.
            if isinstance(item, (Weapon, Armor)):
                entry["durability"] = getattr(item, "durability", None)
                entry["max_durability"] = getattr(item, "max_durability", None)
                entry["is_broken"] = bool(getattr(item, "is_broken", False))
                # BUC + identification state. Cursed gear cannot be
                # unequipped once worn; the policy avoids equipping a
                # weapon/armor whose status it can't yet read.
                entry["buc_status"] = getattr(item, "buc_status", "uncursed")
                entry["buc_known"] = bool(getattr(item, "buc_known", False))
                entry["is_sealed"] = bool(getattr(item, "is_sealed", False))
                # Power stat for comparison. attack_bonus / defense_bonus
                # are @properties that already fold in upgrade_level.
                # Also expose the base / upgrade split so the report
                # can render "+5 atk (3 base + 2 upgrades)" -- useful
                # for tracking how the agent's scaling came from gear
                # tier vs upgrade-scroll consumption.
                if isinstance(item, Weapon):
                    entry["attack_bonus"] = getattr(item, "attack_bonus", 0)
                    entry["base_attack_bonus"] = getattr(item, "_base_attack_bonus", 0)
                else:
                    entry["defense_bonus"] = getattr(item, "defense_bonus", 0)
                    entry["base_defense_bonus"] = getattr(item, "_base_defense_bonus", 0)
                entry["upgrade_level"] = getattr(item, "upgrade_level", 0)
                entry["item_level"] = getattr(item, "level", 0)
                # equipped flag so the policy can compare bag items
                # against the slotted one without doing name matching.
                pc = gs.player_character
                entry["equipped"] = (
                    item is pc.equipped_weapon or item is pc.equipped_armor
                )
                # Bug-sized: only flag bug gear can be equipped while
                # the player is shrunk on a bug floor. Without this,
                # Tauriel elf seed=13 burned 786 turns trying to equip
                # her Falchion -- the handler silently rejected each
                # attempt with "too tiny" and the policy never knew.
                entry["is_bug_gear"] = item.name in _BUG_GEAR_NAMES
            # Identification status applies to potions / scrolls / spells
            # too -- knowing what's in your bag changes what's safe to
            # use. is_item_identified is the canonical check.
            from .items import is_item_identified
            try:
                entry["is_identified"] = bool(is_item_identified(item))
            except Exception:
                entry["is_identified"] = True  # non-identifiable -> safe
            # Surface scroll_type and potion_type so the usage policy
            # can target specific item effects (read mapping when
            # fog-blind, drink stone_skin before combat, etc.) without
            # parsing display names.
            if isinstance(item, Scroll):
                entry["scroll_type"] = getattr(item, "scroll_type", None)
                # Raw name for tier-word detection (Basic / Greater /
                # Superior / Epic / Mythic / Divine / Celestial /
                # Cosmic / Eternal upgrade scrolls). Lets the
                # inventory-use branch skip an upgrade scroll whose
                # cap the equipped weapon has already hit.
                entry["scroll_name"] = getattr(item, "name", "")
            if isinstance(item, Potion):
                entry["potion_type"] = getattr(item, "potion_type", None)
            out.append(entry)
        return out

    def _vendor_obs(self):
        if gs.prompt_cntl != "vendor_shop" or gs.active_vendor is None:
            return None
        # Vendor's "buy" command uses get_sorted_inventory, so the slot
        # number we report must match the sorted order or 'b<N>' will buy
        # the wrong item.
        from .characters import get_sorted_inventory
        sorted_items = get_sorted_inventory(gs.active_vendor.inventory)
        out = []
        for i, item in enumerate(sorted_items):
            entry = {
                "slot": i + 1,
                "name": getattr(item, "name", repr(item)),
                "price": getattr(item, "calculated_value",
                                 getattr(item, "value", 0)),
                "category": _item_category(item),
            }
            # Surface weapon / armor stats so the policy can compare
            # against equipped gear and buy strict upgrades. Without
            # these fields the vendor policy was only stocking
            # potions / food and silently walking past a Longsword
            # (atk+10) sitting at 100g while the agent went on to die
            # holding a Dagger (atk+2) at floor 4.
            # Scroll metadata: vendor buy policy uses scroll_type to
            # prioritise upgrade scrolls over generic ones.
            if isinstance(item, Scroll):
                entry["scroll_type"] = getattr(item, "scroll_type", None)
            if isinstance(item, (Weapon, Armor)):
                entry["is_broken"] = bool(getattr(item, "is_broken", False))
                entry["buc_status"] = getattr(item, "buc_status", "uncursed")
                entry["buc_known"] = bool(getattr(item, "buc_known", False))
                entry["is_sealed"] = bool(getattr(item, "is_sealed", False))
                entry["item_level"] = getattr(item, "level", 0)
                if isinstance(item, Weapon):
                    entry["attack_bonus"] = getattr(item, "attack_bonus", 0)
                else:
                    entry["defense_bonus"] = getattr(item, "defense_bonus", 0)
            out.append(entry)
        return out

    def _nearest_features_obs(self):
        """For each feature type the policy cares about (D, V, C, plus
        beneficial-room set G, A, L, O, P, T, N), return the (dx, dy)
        vector to the nearest unvisited instance on the current floor
        by Manhattan distance. Lets the wayfinder walk *toward* distant
        targets instead of relying on adjacency. Returns {} when no
        unvisited instance exists. Cheaper than pathfinding and good
        enough on the 18x21 floors here -- we step in the dimension with
        the larger absolute delta each turn.

        Respects `fog_of_war`: when on, the agent only sees features on
        tiles it has actually walked over or lit up (room.discovered).
        Off (--no-fog), the agent has god-mode view, useful for testing
        upstream balance without the navigation gate.
        """
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        out = {}
        for target in ("D", "U", "V", "C", "G", "A", "L", "O", "P", "T", "N",
                       "Q", "K", "X", "B", "F"):
            best = None
            best_d = float("inf")
            for y in range(floor.rows):
                for x in range(floor.cols):
                    cell = floor.grid[y][x]
                    if cell.room_type != target:
                        continue
                    if self.fog_of_war and not cell.discovered:
                        continue
                    if (pc.z, x, y, target) in self.visited_features:
                        continue
                    if (x, y) == (pc.x, pc.y):
                        continue
                    d = abs(x - pc.x) + abs(y - pc.y)
                    if d < best_d:
                        best, best_d = (x - pc.x, y - pc.y), d
            if best is not None:
                out[target] = {"dx": best[0], "dy": best[1], "dist": best_d}
        return out

    def _nearest_undiscovered_obs(self):
        """Return (dx, dy, dist) to the nearest undiscovered floor cell.
        Lets the policy walk toward the fog frontier instead of falling
        back to a directionless random walk -- the lantern will then
        reveal whatever is there. Only counts walkable cells (room_type
        != wall_char) so we don't aim at solid rock. Skips when
        fog_of_war is off (everything is "visible" by default)."""
        if not self.fog_of_war:
            return None
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        wall = floor.wall_char
        best = None
        best_d = float("inf")
        for y in range(floor.rows):
            for x in range(floor.cols):
                cell = floor.grid[y][x]
                if cell.discovered:
                    continue
                if cell.room_type == wall:
                    continue
                d = abs(x - pc.x) + abs(y - pc.y)
                if d < best_d:
                    best, best_d = (x - pc.x, y - pc.y), d
        if best is None:
            return None
        return {"dx": best[0], "dy": best[1], "dist": best_d}

    def _keyed_dungeon_target_obs(self):
        """If the player holds a key for an unlooted dungeon on this
        floor, return navigation info to the nearest one. Bypasses
        visited_features (re-targets a dungeon we walked past unkeyed
        before the key dropped) and visited filters on nearest_features.
        Looted dungeons are excluded via gs.looted_dungeons.

        Returns dx/dy/dist (Manhattan) for the adjacency check, plus
        first_step/path_dist (BFS through discovered tiles) for the
        distant wayfinder. first_step is None when the keyed dungeon
        is not reachable through known passage.
        """
        pc = gs.player_character
        z = pc.z
        keys = getattr(gs, "dungeon_keys", {}) or {}
        looted = getattr(gs, "looted_dungeons", {}) or {}
        dist_map, first_step = self._bfs_paths()
        # Prefer BFS-closest; fall back to Manhattan-closest if no keyed
        # tile is reachable through known passage (the agent then walks
        # toward it via the frontier walker until it becomes reachable).
        best_bfs = None  # (path_dist, x, y)
        best_manhattan = None  # (manhattan_dist, x, y)
        for coord in keys.keys():
            if len(coord) < 3 or coord[2] != z:
                continue
            if coord in looted:
                continue
            x, y = coord[0], coord[1]
            md = abs(x - pc.x) + abs(y - pc.y)
            if best_manhattan is None or md < best_manhattan[0]:
                best_manhattan = (md, x, y)
            if (x, y) in dist_map:
                pd = dist_map[(x, y)]
                if best_bfs is None or pd < best_bfs[0]:
                    best_bfs = (pd, x, y)
        chosen = best_bfs or best_manhattan
        if chosen is None:
            return None
        _, x, y = chosen
        fs = first_step.get((x, y))
        pd = dist_map.get((x, y))
        return {
            "dx": x - pc.x,
            "dy": y - pc.y,
            "dist": abs(x - pc.x) + abs(y - pc.y),
            "first_step": fs,
            "path_dist": pd,
        }

    def _visited_neighbors_obs(self):
        """Mirror of _neighbors_obs but with a bool: is this neighbouring
        feature tile already in visited_features? Lets the wayfinder skip
        a vendor / altar / chest we've already interacted with."""
        pc = gs.player_character
        out = {}
        for d, (dx, dy) in (("n", (0, -1)), ("s", (0, 1)),
                            ("e", (1, 0)), ("w", (-1, 0))):
            nx, ny = pc.x + dx, pc.y + dy
            floor = gs.my_tower.floors[pc.z]
            if not (0 <= nx < floor.cols and 0 <= ny < floor.rows):
                out[d] = False
                continue
            rt = floor.grid[ny][nx].room_type
            out[d] = (pc.z, nx, ny, rt) in self.visited_features
        return out

    def _tomb_guardian_dirs_obs(self):
        """Cardinal directions whose adjacent tile is an M room with the
        `undead_guardian` property set -- one of the four tomb-adjacent
        guardian spawns (one elite at floor+1, three regular undead at
        floor). Restricted to DISCOVERED tiles so the agent doesn't get
        god-mode info; the agent has to actually see the M tile (via
        walking near or lantern-revealing) before recognising it as a
        guardian. Used by the policy to refuse stepping into an elite
        undead they're not over-levelled to handle.
        """
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        out = []
        for d, (dx, dy) in (("n", (0, -1)), ("s", (0, 1)),
                            ("e", (1, 0)), ("w", (-1, 0))):
            nx, ny = pc.x + dx, pc.y + dy
            if not (0 <= nx < floor.cols and 0 <= ny < floor.rows):
                continue
            cell = floor.grid[ny][nx]
            if self.fog_of_war and not cell.discovered:
                continue
            if cell.room_type != "M":
                continue
            if cell.properties.get("undead_guardian"):
                out.append(d)
        return out

    def _suspected_guardian_coords_obs(self):
        """(x, y) tiles that are CARDINAL-ADJACENT to any discovered T
        (tomb) on the current floor. Every tomb spawns exactly four
        guardians in its cardinal neighbours (setup_dungeons_and_tombs
        in dungeon.py), so once the agent sees a T tile they can infer
        the four guardian positions WITHOUT having to discover the M
        tiles directly. Used by the policy's inference-based avoid: a
        Lv1 elf who lantern-reveals a T two tiles away now knows not
        to step into the M positions around it, even before those Ms
        are themselves discovered.

        User-requested ('let's create playtests logic that detects "a
        tomb might be here so there could be a guardian in one of
        these adjacent rooms"').
        """
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        out = set()
        for y in range(floor.rows):
            for x in range(floor.cols):
                cell = floor.grid[y][x]
                if cell.room_type != "T":
                    continue
                if self.fog_of_war and not cell.discovered:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < floor.cols and 0 <= ny < floor.rows):
                        continue
                    # If the candidate tile is already discovered AND
                    # not an M tile, it definitely isn't a guardian
                    # spawn. Skip. Caught on s=941 dwarf F1 at T404:
                    # the agent stood adjacent to a D tile that
                    # happened to neighbour a discovered T -- the
                    # blanket 'every adjacent to T is suspected'
                    # rule flagged the D as a guardian, the policy
                    # refused 'w' onto D and stayed wedged for
                    # 1700+ turns at full HP. Now: discovered non-M
                    # tiles (D, U, ., features, etc.) are safe.
                    ncell = floor.grid[ny][nx]
                    if self.fog_of_war and ncell.discovered:
                        if ncell.room_type != "M":
                            continue
                    out.add((nx, ny))
        return sorted(out)

    def _inferred_guardian_dirs_obs(self):
        """Cardinal directions whose adjacent tile is a suspected
        guardian (cardinal-adjacent to a discovered T). Complements
        tomb_guardian_dirs (which requires the M to be DISCOVERED and
        flagged): this one fires purely off T-sighting, so a Lv1
        agent can avoid stepping onto a fog-hidden guardian as long as
        they've seen the tomb. Stops the four-corner-walk-in problem
        without requiring lantern-reveal of every M tile first."""
        pc = gs.player_character
        suspected = set(self._suspected_guardian_coords_obs())
        if not suspected:
            return []
        out = []
        for d, (dx, dy) in (("n", (0, -1)), ("s", (0, 1)),
                            ("e", (1, 0)), ("w", (-1, 0))):
            nx, ny = pc.x + dx, pc.y + dy
            if (nx, ny) in suspected:
                out.append(d)
        return out

    def _bfs_paths(self):
        """BFS from player over walkable, discovered tiles. Returns
        (dist_map, first_step_map) keyed by (x, y).

        Walkable transit excludes walls, undiscovered tiles (under fog),
        and known hazards (M monsters, W warps). Feature tiles (D, V,
        C, G, A, L, O, P, T, N) ARE walkable -- the agent steps onto
        them to interact. To attack a monster, route to one of its
        cardinal neighbours and step into the M tile.

        Cached per observe() via self._bfs_cache so the three
        path-obs methods share one BFS pass.
        """
        cache = getattr(self, "_bfs_cache", None)
        if cache is not None:
            return cache

        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        wall = floor.wall_char
        rows, cols = floor.rows, floor.cols
        BLOCK_TRANSIT = {wall, "M", "W"}

        dist = {(pc.x, pc.y): 0}
        first_step = {(pc.x, pc.y): None}
        queue = collections.deque([(pc.x, pc.y)])
        DIRS = (("n", 0, -1), ("s", 0, 1), ("e", 1, 0), ("w", -1, 0))
        while queue:
            x, y = queue.popleft()
            for d, dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < cols and 0 <= ny < rows):
                    continue
                if (nx, ny) in dist:
                    continue
                cell = floor.grid[ny][nx]
                if self.fog_of_war and not cell.discovered:
                    continue
                if cell.room_type in BLOCK_TRANSIT:
                    continue
                dist[(nx, ny)] = dist[(x, y)] + 1
                first_step[(nx, ny)] = (
                    d if (x, y) == (pc.x, pc.y) else first_step[(x, y)]
                )
                queue.append((nx, ny))

        self._bfs_cache = (dist, first_step)
        return self._bfs_cache

    def _feature_paths_obs(self):
        """For each feature type, the BFS shortest path through
        discovered, non-hazard tiles: first step direction + path
        distance. Replaces Manhattan-vector greedy stepping with a
        real navigator that respects walls + fog. {} for unreachable.
        """
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        dist, first_step = self._bfs_paths()
        out = {}
        for target in ("D", "U", "V", "C", "G", "A", "L", "O", "P", "T", "N",
                       "Q", "K", "X", "B", "F"):
            best = None
            best_d = float("inf")
            for y in range(floor.rows):
                for x in range(floor.cols):
                    cell = floor.grid[y][x]
                    if cell.room_type != target:
                        continue
                    if self.fog_of_war and not cell.discovered:
                        continue
                    if (pc.z, x, y, target) in self.visited_features:
                        continue
                    if (x, y) == (pc.x, pc.y):
                        continue
                    if (x, y) not in dist:
                        continue
                    d = dist[(x, y)]
                    if d < best_d:
                        best, best_d = (x, y), d
            if best is not None:
                out[target] = {
                    "first_step": first_step[best],
                    "path_dist": best_d,
                }
        return out

    def _frontier_step_obs(self):
        """BFS first-step toward the nearest reachable frontier: a
        discovered, walkable tile with at least one undiscovered
        neighbour. Lower-right tiebreak (SE-most wins ties on path_dist)
        mirrors the player heuristic that D tends to be down-right.
        """
        if not self.fog_of_war:
            return None
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        dist, first_step = self._bfs_paths()
        best_xy = None
        best_key = None
        for (x, y), d in dist.items():
            if (x, y) == (pc.x, pc.y):
                continue
            has_undiscovered = False
            for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < floor.cols and 0 <= ny < floor.rows):
                    continue
                if not floor.grid[ny][nx].discovered:
                    has_undiscovered = True
                    break
            if not has_undiscovered:
                continue
            key = (d, -(x + y))
            if best_key is None or key < best_key:
                best_key = key
                best_xy = (x, y)
        if best_xy is None:
            return None
        return {
            "first_step": first_step[best_xy],
            "path_dist": dist[best_xy],
        }

    def _nearest_monster_path_obs(self):
        """BFS first-step + path distance to engaging the nearest
        visible monster. M tiles aren't walkable transit, so we BFS to
        their cardinal neighbours and report the approach + 1 step into
        the M. Used by hunt-mode when the player is strong enough to
        farm monsters for XP/gold. Returns None when no visible M is
        reachable through discovered tiles.
        """
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        dist, first_step = self._bfs_paths()
        opp = {"n": "s", "s": "n", "e": "w", "w": "e"}
        best = None
        for y in range(floor.rows):
            for x in range(floor.cols):
                cell = floor.grid[y][x]
                if cell.room_type != "M":
                    continue
                if self.fog_of_war and not cell.discovered:
                    continue
                approach = None
                for d, dx, dy in (("n", 0, -1), ("s", 0, 1),
                                  ("e", 1, 0), ("w", -1, 0)):
                    nx, ny = x + dx, y + dy
                    if (nx, ny) not in dist:
                        continue
                    step_into = opp[d]
                    ad = dist[(nx, ny)]
                    if approach is None or ad < approach[0]:
                        approach = (ad, step_into, (nx, ny))
                if approach is None:
                    continue
                approach_dist, step_into, neighbour_xy = approach
                fs = step_into if approach_dist == 0 else first_step[neighbour_xy]
                total = approach_dist + 1
                if best is None or total < best[0]:
                    best = (total, fs)
        if best is None:
            return None
        return {"first_step": best[1], "path_dist": best[0]}

    def _nearest_warp_path_obs(self):
        """BFS first-step + path distance to a tile ADJACENT to a
        discovered W (warp), plus the cardinal step onto the W
        itself. W is in BLOCK_TRANSIT so the regular feature_paths
        BFS treats it as unreachable -- this companion computes the
        approach explicitly, like nearest_monster_path does for M.
        Returns None when no discovered W is reachable. Used by
        the trapped-no-D escape valve: when the floor is region-
        split and D is behind walls, the only way out is to walk
        onto a known W and accept the random teleport.
        """
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        dist, first_step = self._bfs_paths()
        opp = {"n": "s", "s": "n", "e": "w", "w": "e"}
        best = None
        for y in range(floor.rows):
            for x in range(floor.cols):
                cell = floor.grid[y][x]
                if cell.room_type != "W":
                    continue
                if self.fog_of_war and not cell.discovered:
                    continue
                approach = None
                for d, dx, dy in (("n", 0, -1), ("s", 0, 1),
                                  ("e", 1, 0), ("w", -1, 0)):
                    nx, ny = x + dx, y + dy
                    if (nx, ny) not in dist:
                        continue
                    step_into = opp[d]
                    ad = dist[(nx, ny)]
                    if approach is None or ad < approach[0]:
                        approach = (ad, step_into, (nx, ny))
                if approach is None:
                    continue
                approach_dist, step_into, neighbour_xy = approach
                fs = step_into if approach_dist == 0 else first_step[neighbour_xy]
                total = approach_dist + 1
                if best is None or total < best[0]:
                    best = (total, fs)
        if best is None:
            return None
        return {"first_step": best[1], "path_dist": best[0]}

    def _tile_coverage_obs(self):
        """How much of the current floor's walkable area has the
        agent stood on? Returns dict with `visited`, `walkable`,
        `pct` (0-100), `reachable` (BFS-reachable from current pos),
        and `reach_pct` (visited / reachable * 100 -- "% of MY
        island I've walked"). Region-split floors (D in another
        part of the floor behind walls) leave the agent on a tiny
        reachable island where global `pct` can never climb past
        a few percent; `reach_pct` correctly hits 100% once the
        island is swept, and that's the right signal for the
        trapped-no-D escape valve.
        """
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        wall = floor.wall_char
        walkable = 0
        for y in range(floor.rows):
            for x in range(floor.cols):
                if floor.grid[y][x].room_type != wall:
                    walkable += 1
        visited = len(self.visited_tiles_this_floor)
        pct = (visited / walkable * 100.0) if walkable else 0.0
        dist, _ = self._bfs_paths()
        reachable = len(dist)
        # visited may include tiles BFS can't currently reach if
        # the agent walked through them earlier (W tile, dead
        # monster tile that's since gone walls-elsewhere). Clamp
        # reach_pct at 100 so the gate doesn't false-fire on the
        # rare past-walked-now-unreachable case.
        reach_pct = min(100.0, (visited / reachable * 100.0)) if reachable else 0.0
        return {
            "visited": visited,
            "walkable": walkable,
            "pct": pct,
            "reachable": reachable,
            "reach_pct": reach_pct,
        }

    def _oscillation_state(self):
        """Detect a stable 2-tile oscillation in the last 12 position
        snapshots. Returns a dict consumed by the smart-policy
        anti-oscillation branch: {"detected": bool, "pair":
        [(x1,y1), (x2,y2)]}. The 4-entry recent_positions is too
        short to catch this (both tiles are 'recent' so swap-if-
        backtrack finds no alternative and the wayfinder keeps
        returning the same BFS first_step). We need the wider
        position_history window. Caught on s=23 dwarf F1 (9,14)
        <-> (10,14) for 392 turns post-shrine.

        3-tile cycle detection was tried but regressed the total
        turns-wasted: it false-positives on legitimate short-
        corridor exploration (an agent BFS-walking n/e/n through
        a 3-cell pinch toward a fog frontier looks identical to
        an n/e/n oscillation in raw position snapshots). Sticking
        with 2-tile only for now; the 3-tile patterns surface in
        the report's mid-run-loop table for diagnosis."""
        pc = gs.player_character
        tail = [(x, y) for (z, x, y) in self.position_history[-12:]
                if z == pc.z]
        detected = False
        pair = []
        if len(tail) >= 12:
            uniq = set(tail)
            if len(uniq) == 2:
                a, b = list(uniq)
                if tail.count(a) >= 5 and tail.count(b) >= 5:
                    detected = True
                    pair = [a, b]
            elif len(uniq) == 1:
                # Position frozen (agent stopped to use inventory /
                # mid-handler turn / etc). Don't break the streak
                # just because of a pause; treat the single-tile
                # window as 'consistent with the current pair' if
                # we already had a pair tripping. Otherwise leave
                # detected=False so a truly idle agent doesn't get
                # flagged.
                if self.osc_streak > 0 and self._last_osc_pair and \
                        list(uniq)[0] in self._last_osc_pair:
                    detected = True
                    pair = self._last_osc_pair
        # Maintain the consecutive-oscillation streak so callers can
        # gate escape valves on persistence (e.g. stairs_up_mode
        # should only force 'u' after 50+ turns of confirmed wedge).
        # Streak survives single-tile pauses (inventory / handler
        # turns) when the pair stays the same -- s=88 human spent
        # ~1500 turns oscillating on F2 (1,1)U <-> (1,2) with
        # frequent inventory eats breaking the detector and
        # resetting the streak. The pause-tolerant logic above
        # closes that hole.
        if detected:
            self.osc_streak += 1
            self._last_osc_pair = pair
        else:
            self.osc_streak = 0
            self._last_osc_pair = None
        return {"detected": detected, "pair": pair, "streak": self.osc_streak}

    def _recent_step_set(self):
        """List of cardinal directions (n/s/e/w) whose neighbour is in
        recent_positions on the current floor. Used by the wayfinder
        as a tiebreak: when a BFS first_step would re-step on a recent
        tile AND an alternative direction is walkable, prefer the
        alternative. Solves the 2-tile saddle-point oscillation
        (seed=42 dwarf burned 4857/5000 turns alternating n/s through
        a corridor). Returns a sorted list for JSON-friendliness."""
        pc = gs.player_character
        recent_on_floor = {(x, y) for (z, x, y) in self.recent_positions
                           if z == pc.z}
        if not recent_on_floor:
            return []
        out = []
        for d, (dx, dy) in (("n", (0, -1)), ("s", (0, 1)),
                            ("e", (1, 0)), ("w", (-1, 0))):
            if (pc.x + dx, pc.y + dy) in recent_on_floor:
                out.append(d)
        return out

    def _neighbors_obs(self):
        """Cardinal-neighbor room types so the policy can spot adjacent
        features (D = downstairs, V = vendor, C = chest, etc.). Returns
        '#' for out-of-bounds. Respects `fog_of_war`: when on, returns
        None for undiscovered tiles so the agent must rely on the lantern
        (or walking onto a tile to discover it) to plan. Off, the
        actual room_type is always reported.
        """
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        out = {}
        for d, (dx, dy) in (("n", (0, -1)), ("s", (0, 1)),
                            ("e", (1, 0)), ("w", (-1, 0))):
            nx, ny = pc.x + dx, pc.y + dy
            if not (0 <= nx < floor.cols and 0 <= ny < floor.rows):
                out[d] = "#"
                continue
            cell = floor.grid[ny][nx]
            if self.fog_of_war and not cell.discovered:
                out[d] = None
                continue
            out[d] = cell.room_type
        return out
        return out

    # ------------------------------------------------------------------
    # ASCII map (debug / human-readable)
    # ------------------------------------------------------------------
    def ascii_map(self, show_undiscovered=False):
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        rows = []
        for y in range(floor.rows):
            row = []
            for x in range(floor.cols):
                cell = floor.grid[y][x]
                if x == pc.x and y == pc.y:
                    row.append("@")
                elif not cell.discovered and not show_undiscovered:
                    row.append(" ")
                else:
                    row.append(cell.room_type)
            rows.append("".join(row))
        return "\n".join(rows)

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------
    def step(self, action):
        self.turn += 1
        self.last_action = action
        self.last_error = None
        pc = gs.player_character
        tw = gs.my_tower
        mode = gs.prompt_cntl
        # Detect a policy-issued 'u' escape from a persistent 2-tile
        # oscillation in stairs_up_mode. Record the current z so the
        # stairs_down_mode policy refuses to re-descend into a known
        # region-split wedge. s=88 human F2 (1,1)U <-> (1,2): without
        # this the agent ascended out, hit F1's D, and immediately
        # descended right back, ping-ponging another 1500 turns.
        if (mode == "stairs_up_mode"
                and action == "u"
                and self.osc_streak >= 50):
            self.wedge_floors[pc.z] = self.turn
            self.wedge_count[pc.z] = self.wedge_count.get(pc.z, 0) + 1
        # Cornered-ascend: a 1-tile region-split where the U tile has
        # no walkable cardinal neighbours from the agent's POV (fog-
        # of-war counted as wall -- an undiscovered tile is just as
        # unreachable as a real wall until the agent walks adjacent
        # to reveal it). The stairs_up_mode fallback returns 'u'
        # rather than wall-bumping forever; mirror the wedge-mark
        # here so the next stairs_down_mode strips D from priority.
        # Caught on s=2500 human/elf F2 (U at (1,1) with N/W walls
        # and S/E undiscovered fog).
        if mode == "stairs_up_mode" and action == "u":
            floor = tw.floors[pc.z]
            wall = floor.wall_char
            cornered = True
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = pc.x + dx, pc.y + dy
                if not (0 <= nx < floor.cols and 0 <= ny < floor.rows):
                    continue  # off-map counts as wall
                cell = floor.grid[ny][nx]
                rt = cell.room_type
                if rt == wall or rt == "U":
                    continue
                # Fog-of-war: undiscovered cells are unreachable
                # from the policy's POV. Only a DISCOVERED
                # walkable cell breaks the cornered state.
                if self.fog_of_war and not cell.discovered:
                    continue
                cornered = False
                break
            if cornered:
                self.wedge_floors[pc.z] = self.turn
                # Definitionally permanent: a U tile with zero
                # discovered walkable cardinal neighbours is a 1-
                # tile island that won't open up via lantern reveal
                # (the agent never moves off U to reveal more). Jump
                # straight to the permanent threshold so the
                # stairs_down_mode block never expires.
                self.wedge_count[pc.z] = max(
                    self.wedge_count.get(pc.z, 0) + 1,
                    self._WEDGE_PERMANENT_AFTER,
                )
        # Record flee attempts (both successful and failed) so the
        # game_loop heal-up gate can fire before the agent walks back
        # into another fight. Every flee costs one monster attack
        # (combat.py:1158 unconditional), so the player is by
        # definition wounded by the time the policy returns control.
        if mode == "combat_mode" and action == "f":
            self.last_flee_turn = self.turn
            max_h = max(1, pc.max_health)
            self.last_flee_hp_pct = pc.health / max_h
        # Capture pre-step position. The loop-prevention check below
        # only forces game_loop when the agent JUST LANDED on a
        # previously-visited feature tile -- not when they're
        # mid-dialog with a fresh feature (e.g., still inside an
        # altar prayer sequence). Without this guard, the override
        # short-circuits boon-claiming on first visit.
        pre_step_xyz = (pc.z, pc.x, pc.y)

        try:
            if mode == "death_screen":
                pass  # game over, no-op
            elif mode == "game_loop":
                if action in ("n", "s", "e", "w"):
                    move_player(pc, tw, action)
                elif action == "d":
                    process_stairs_down_action(pc, tw, "init")
                elif action == "u":
                    process_stairs_up_action(pc, tw, "init", gs.floor_params)
                elif action == "i":
                    gs.prompt_cntl = "inventory"
                    gs.inventory_filter = None
                    handle_inventory_menu(pc, tw, "init")
                elif action == "l":
                    # Lantern quick-use. Reveals adjacent tiles (radius =
                    # upgrade_level + 1) and consumes 1 fuel. No game turn
                    # is ticked -- hunger / status / monster spawns don't
                    # advance, just the lantern itself depletes. Auto-
                    # refuels from Lantern Fuel items in inventory when
                    # fuel hits 0.
                    from .room_actions import process_lantern_quick_use
                    process_lantern_quick_use(pc, tw)
                elif action == "pass":
                    pass
                else:
                    self.last_error = f"unknown game_loop action: {action!r}"
            elif mode == "combat_mode":
                process_combat_action(pc, tw, action)
            elif mode == "flee_direction_mode":
                # Mid-flee direction prompt. Handler accepts n/s/e/w to
                # move + exit combat, or 'c' to cancel + return to
                # combat. Anything else (incl. 'back') just logs an
                # invalid-direction message and stays in flee_dir mode.
                # Without this dispatch + policy branch, the agent fell
                # into the catch-all 'back' which the harness mapped to
                # game_loop, but the player was still on the monster
                # tile so the next step walked right back into combat
                # -- Finrod the elf burned ~10 turns this way taking
                # 24-dmg Wraith hits between failed flees.
                from .combat import process_flee_direction_action
                process_flee_direction_action(pc, tw, action)
            elif mode == "spell_casting_mode":
                process_spell_casting_action(pc, tw, action)
            elif mode == "chest_mode":
                process_chest_action(pc, tw, action)
            elif mode == "stairs_down_mode":
                process_stairs_down_action(pc, tw, action)
            elif mode == "stairs_up_mode":
                process_stairs_up_action(pc, tw, action, gs.floor_params)
            elif mode == "inventory":
                handle_inventory_menu(pc, tw, action)
            elif mode == "vendor_shop":
                handle_vendor_shop(pc, tw, action)
            elif mode == "starting_shop":
                handle_starting_shop(pc, tw, action)
            elif mode == "warp_mode":
                # Warp = random teleport. The agent resists by default --
                # see the smart_policy warp_mode branch.
                from .game_systems import process_warp_action
                process_warp_action(pc, tw, action, gs.floor_params)
            elif mode == "altar_mode":
                from .game_systems import process_altar_action
                process_altar_action(pc, tw, action)
            elif mode == "pool_mode":
                from .game_systems import process_pool_action
                process_pool_action(pc, tw, action)
            elif mode == "tomb_mode":
                from .game_systems import process_tomb_action
                process_tomb_action(pc, tw, action)
            elif mode in ("dungeon_mode", "dungeon_unlocked_mode"):
                from .game_systems import process_dungeon_action
                process_dungeon_action(pc, tw, action)
            elif mode in ("garden_mode", "fey_garden_mode"):
                from .game_systems import process_garden_action
                process_garden_action(pc, tw, action)
            elif mode == "library_mode":
                from .game_systems import process_library_action
                process_library_action(pc, tw, action)
            elif mode == "library_read_decision_mode":
                from .room_actions import process_library_read_decision
                process_library_read_decision(pc, tw, action)
            elif mode == "blacksmith_mode":
                from .game_systems import process_blacksmith_action
                process_blacksmith_action(pc, tw, action)
            elif mode == "shrine_mode":
                from .game_systems import process_shrine_action
                process_shrine_action(pc, tw, action)
            elif mode == "oracle_mode":
                from .game_systems import process_oracle_action
                process_oracle_action(pc, tw, action)
            elif mode == "alchemist_mode":
                from .game_systems import process_alchemist_action
                process_alchemist_action(pc, tw, action)
            elif mode == "war_room_mode":
                from .game_systems import process_war_room_action
                process_war_room_action(pc, tw, action)
            elif mode == "taxidermist_mode":
                from .game_systems import process_taxidermist_action
                process_taxidermist_action(pc, tw, action)
            elif mode == "identify_scroll_mode":
                from .items import process_identify_scroll_action
                process_identify_scroll_action(pc, tw, action)
            elif mode == "upgrade_scroll_mode":
                from .items import process_upgrade_scroll_action
                process_upgrade_scroll_action(pc, tw, action)
            elif mode == "foresight_direction_mode":
                from .combat import process_foresight_direction_action
                process_foresight_direction_action(pc, tw, action)
            else:
                # Last-resort: many process_X_action handlers accept a back
                # command of 'x' or 'l'. Route an explicit "back" to that;
                # otherwise leave the harness in this mode for the agent to
                # diagnose.
                if action == "back":
                    gs.prompt_cntl = "game_loop"
                else:
                    self.last_error = f"no headless dispatch for mode {mode!r}"
        except Exception as e:  # surface, don't crash the harness
            self.last_error = f"{type(e).__name__}: {e}"

        # Record any feature tile the player is now standing on so the
        # wayfinder can avoid bouncing back onto it once we exit the
        # corresponding interaction mode. '.' / 'E' / '#' / 'D' aren't
        # tracked -- '.' is empty, 'E' is the floor-start tile (we'll
        # revisit it harmlessly), '#' is a wall, and 'D' is the descent
        # goal that should always be re-targeted.
        pc_after = gs.player_character
        room_now = gs.my_tower.floors[pc_after.z].grid[pc_after.y][pc_after.x]
        landing_key = (pc_after.z, pc_after.x, pc_after.y, room_now.room_type)
        was_visited = landing_key in self.visited_features
        post_step_xyz = (pc_after.z, pc_after.x, pc_after.y)
        # Loop-prevention: feature-room modes re-fire their prompt
        # every time the agent steps onto the tile, even after the
        # boon is consumed. Two re-trigger paths:
        #   - move-step lands on visited feature -> mode init fires
        #   - inventory exit ('x') on a feature tile calls
        #     _trigger_room_interaction(), which re-fires mode init
        # Without this guard each visit burns turns on a re-prompt
        # the policy then has to 'back' out of. HP charts on the
        # deployed report site exposed this: many 'alive' runs were
        # flat-lining HP from T300+ stuck in chest / pool / vendor /
        # blacksmith oscillations. The override forces game_loop when
        # we re-enter a loop-prone mode on a tile that's already been
        # visited AND we weren't already in that same mode last step
        # (the latter clause preserves multi-turn boon-claim
        # dialogues like altar pray sequences). stairs_down_mode is
        # excluded -- D isn't in visited_features and we want
        # descent prompts to fire.
        LOOP_PRONE_MODES = {
            "altar_mode", "pool_mode", "garden_mode", "fey_garden_mode",
            "library_mode", "oracle_mode", "chest_mode", "tomb_mode",
            "vendor_shop", "blacksmith_mode", "shrine_mode",
            "stairs_up_mode", "alchemist_mode", "war_room_mode",
            "taxidermist_mode",
            "dungeon_mode", "dungeon_unlocked_mode",
        }
        # The step transitioned INTO a loop-prone mode (either because
        # the agent landed via movement, or _trigger_room_interaction
        # re-fired the mode on inventory exit / similar).
        transitioned_in = (
            gs.prompt_cntl != mode
            and gs.prompt_cntl in LOOP_PRONE_MODES
        )
        # Keyed-dungeon exception: when the agent has the key for the
        # dungeon they just stepped onto AND it isn't looted yet, keep
        # the dungeon_mode prompt so the policy's 'u' (unlock) can
        # fire. Gloin III s=99 dwarf burned 3000 turns on F1 because
        # the key dropped AFTER his first un-keyed visit -- the N tile
        # entered visited_features, then once keyed the agent kept
        # re-targeting it via the adjacent-shortcut but the override
        # reset dungeon_mode -> game_loop every step, so 'u' never
        # fired and the dungeon stayed locked.
        if (was_visited and transitioned_in
                and gs.prompt_cntl in ("dungeon_mode", "dungeon_unlocked_mode")):
            coord = (pc_after.x, pc_after.y, pc_after.z)
            holds_key = coord in (getattr(gs, "dungeon_keys", {}) or {})
            already_looted = coord in (getattr(gs, "looted_dungeons", {}) or {})
            if holds_key and not already_looted:
                pass  # let the unlock/loot prompts fire
            else:
                gs.prompt_cntl = "game_loop"
        elif was_visited and transitioned_in:
            gs.prompt_cntl = "game_loop"
        # Skip visited-tracking for traversal tiles (., E), walls (#),
        # and stair tiles (D, U). The agent steps onto stairs to use
        # them, and we want the wayfinder to re-target them when
        # retreating up from a warp-skipped floor or descending later.
        if room_now.room_type not in (".", "E", "#", "D", "U"):
            self.visited_features.add(landing_key)
        # Reset floor-arrival counter when we change floors so the
        # stuck-on-floor override fires per-floor, not cumulative.
        if pc_after.z != self._last_floor:
            # Stairs descent vs warp-arrival: if the pre-step mode was
            # stairs_down_mode AND the action was 'd' AND z went up by
            # exactly 1, it's a canonical descent and we bank the new
            # depth as max_z_via_stairs. Anything else (warp accept,
            # warp-resist-fail, multi-floor jump) leaves the cap
            # alone, which triggers retreat-mode in the wayfinder.
            if (mode == "stairs_down_mode"
                    and action == "d"
                    and pc_after.z == self._last_floor + 1):
                if pc_after.z > self.max_z_via_stairs:
                    self.max_z_via_stairs = pc_after.z
            self._last_floor = pc_after.z
            self.floor_arrival_turn = self.turn
            # Clear the recent-position history on floor change so the
            # anti-backtrack guard doesn't try to avoid a tile that's
            # no longer reachable (different floor).
            self.recent_positions = []
            # Same reasoning for the oscillation detector's history.
            self.position_history = []
            self.osc_streak = 0  # fresh floor, fresh wedge count
            self._last_osc_pair = None
            # Reset tile-coverage tracking: the new floor starts at 0%
            # explored from the agent's perspective.
            self.visited_tiles_this_floor = set()
            self.floor_visit_count = {}
            self.last_new_tile_turn = self.turn
            self.wedge_attempted_actions = set()
            # Reset the floor-scoped Hail-Mary tracker too -- fresh
            # floor means fresh items worth trying (new scrolls
            # picked up, different vendor stock).
            self.wedge_tried_this_floor = set()
            # Fresh floor, fresh walls to discover.
            self.blocked_directions = set()
            # Reset per-floor kill counter so the grind-first descent
            # gate measures kills on the CURRENT floor only.
            self.kills_on_floor = 0
        # Bump the kill counter on transitions INTO combat_victory.
        # combat_victory fires exactly once per defeated monster, so
        # this is a clean per-kill signal.
        if mode != "combat_victory" and gs.prompt_cntl == "combat_victory":
            self.kills_on_floor += 1
        # Retreat give-up: if we've been retreat-active on this floor
        # for more than 800 turns without resolving (no floor change
        # back to <= max_z_via_stairs), bank current depth as the
        # new max so the retreat flag clears and the agent resumes
        # normal play. Faramir the Brave (human seed 12345) reached
        # F2 only via warps (max_z_via_stairs stayed 0), then
        # couldn't find an unreachable U for 1500+ turns -- retreat
        # mode trapped him in the wander loop. Banking max_z = 1
        # lets him drop retreat and try to descend normally instead.
        if (pc_after.z > self.max_z_via_stairs
                and (self.turn - self.floor_arrival_turn) > 800):
            self.max_z_via_stairs = pc_after.z
        # Track current-floor coverage for the policy's descent gate.
        xy_after = (pc_after.x, pc_after.y)
        if xy_after not in self.visited_tiles_this_floor:
            self.last_new_tile_turn = self.turn
        self.visited_tiles_this_floor.add(xy_after)
        # Bump per-tile visit count ONLY on actual arrival (position
        # changed this step). Standing still during inventory ops or
        # multi-turn mode dialogues must NOT inflate the counter --
        # the wedge detector reads "how many times have we arrived
        # here from elsewhere" so a 2-tile bounce shows up cleanly.
        if pre_step_xyz != post_step_xyz:
            xy_now = (pc_after.x, pc_after.y)
            self.floor_visit_count[xy_now] = self.floor_visit_count.get(xy_now, 0) + 1
        # Wedge action tracker: when we're wedged (current tile
        # visited 6+ times) AND the agent issues an inventory item
        # use, remember the action so the Hail Mary doesn't re-try
        # the same slot in this episode. Reset whenever the player
        # actually moves -- a fresh tile = fresh wedge episode.
        cur_visits = self.floor_visit_count.get(
            (pc_after.x, pc_after.y), 0
        )
        if pre_step_xyz != post_step_xyz:
            self.wedge_attempted_actions = set()
        elif cur_visits >= 6 and isinstance(action, str) and action.startswith("u"):
            self.wedge_attempted_actions.add(action)
            # Also remember it at floor scope so a bounce loop
            # across 5 tiles doesn't re-try the same dud item on
            # every tile (s=16180 human burned 3800T on F3 re-
            # trying an unidentified Healing Potion at full HP).
            self.wedge_tried_this_floor.add(action)
        # Maintain blocked_directions: when a cardinal-move action
        # fails to change position, that direction is a wall from the
        # current tile. Cleared on any successful move.
        if action in ("n", "s", "e", "w"):
            if pre_step_xyz == post_step_xyz:
                self.blocked_directions.add(action)
            else:
                self.blocked_directions.clear()
        elif pre_step_xyz != post_step_xyz:
            # Any other action that caused movement (e.g., flee
            # direction processed differently) also resets blockers.
            self.blocked_directions.clear()
        # Record the new position for anti-backtrack. Keep a short
        # window (4 entries) -- long enough to detect 2-tile and
        # 3-tile oscillations, short enough that the agent isn't
        # blocked from genuinely retracing through a corridor.
        cur_xy = (pc_after.z, pc_after.x, pc_after.y)
        if not self.recent_positions or self.recent_positions[-1] != cur_xy:
            self.recent_positions.append(cur_xy)
            if len(self.recent_positions) > 4:
                self.recent_positions.pop(0)
        # Wider buffer for the oscillation detector. Recorded EVERY
        # step (not just position changes) so a no-op step (action
        # bounced off a wall, inventory open, etc.) still consumes a
        # slot -- otherwise long stretches in inventory mode would
        # leave the buffer full of stale positions and the detector
        # would mis-fire after returning to game_loop.
        self.position_history.append(cur_xy)
        if len(self.position_history) > 16:
            self.position_history.pop(0)

        return self.observe()

    def is_done(self):
        return (gs.game_should_quit
                or gs.prompt_cntl == "death_screen"
                or not gs.player_character.is_alive()
                or self.early_terminated)

    def is_truly_trapped(self, obs):
        """Detect the unreachable-corner case where the agent has
        no algorithmic escape: no D / U on this floor's reachable
        region, no warp, no Teleport / Descent scroll in inventory,
        and has burned 1500+ turns since the last new tile without
        progress. Returning True flips early_terminated and lets
        is_done() break the main loop -- saves 3000+ wasted turns
        per stuck-but-not-dead run.

        Conservative gates so we never short-circuit a run that
        could still progress:
          - turns_on_floor >= 1500
          - turns_since_new_tile >= 800
          - reach_pct >= 90 (we've fully explored the region)
          - feature_paths has neither D nor U
          - nearest_warp_path is None
          - inventory has no identified Scroll of Teleport or
            Scroll of Descent (the two scrolls that move the
            player off the current tile / floor)
        """
        if obs is None:
            return False
        # Bug-level shrunken agent: stairs/warps are sealed by
        # design. The escape is a chest-borne Growth Mushroom or
        # the Bug Queen kill (her drop), neither visible to the
        # 'no D/U/W + no escape scroll' shape of this check. Don't
        # early-terminate -- the quest path is alive.
        p = obs.get("player") or {}
        if p.get("is_shrunk"):
            return False
        feature_paths = obs.get("feature_paths") or {}
        # D-leads-to-permanent-wedge counts as "no D" here. Without
        # this an agent in a 3-tile pocket with D pointing into a
        # known-impassable F2 wedge stays "D=reachable" forever and
        # never early-terminates. s=1234 (all races) F1: D reachable
        # south but it lands on a 1-tile region-split, agent bounces
        # 500T in the pocket until starvation.
        cur_z_for_perm = (p.get("floor") or 1) - 1
        perm_wedge = set(obs.get("permanent_wedge_floors") or [])
        d_into_perm = (cur_z_for_perm + 1) in perm_wedge
        # "On the D tile" also counts as D-reachable -- BFS skips
        # the player's own tile so feature_paths.D=None when the
        # agent is standing on D. Otherwise the early-term gate
        # false-fires the moment the agent steps onto D.
        mode = obs.get("mode")
        on_d_tile = (mode == "stairs_down_mode")
        d_reachable = (
            (bool((feature_paths.get("D") or {}).get("first_step"))
             or on_d_tile)
            and not d_into_perm
        )
        on_u_tile = (mode == "stairs_up_mode")
        u_reachable = (bool((feature_paths.get("U") or {}).get("first_step"))
                       or on_u_tile)
        w_reachable = obs.get("nearest_warp_path") is not None
        # Escape-scroll check (Teleport / Descent only).
        ESCAPE_SCROLLS = {"teleport", "descent"}
        has_escape_scroll = any(
            e.get("category") == "scroll"
            and e.get("is_identified")
            and e.get("scroll_type") in ESCAPE_SCROLLS
            for e in (obs.get("inventory") or [])
        )
        if d_reachable or u_reachable or w_reachable or has_escape_scroll:
            return False
        # Tiny-pocket fast-path: a small reachable region (<= 20
        # tiles) with reach_pct >= 90 and no escape options means
        # the agent has nothing more to do. Fire after 200T-since-
        # new (their last fog reveal happened at least 200T ago)
        # instead of waiting the full 1500T floor budget. Caught on
        # s=1234 (dwarf/human/elf) F1: 3-tile pocket, D-into-perm-
        # wedge, no W, no scrolls -- starved at T883 because the
        # 1500T threshold never fired.
        #
        # EXCEPTION: don't terminate while the agent is still
        # productively grinding M rooms (kills_on_floor >= 20). M
        # tiles respawn monsters per-visit, so a tight 3-tile
        # pocket adjacent to an M can churn out XP + drops for a
        # long stretch -- the run ends in real combat death, which
        # is more diagnostic than 'stuck'. Caught on s=271 human
        # F1: 3-tile pocket vs M east, 100 bug kills, died T2154
        # to poison -- shorting to T1166 stuck cut the combat story.
        cov = obs.get("tile_coverage") or {}
        reach_pct = cov.get("reach_pct") or 0
        reachable_tiles = cov.get("reachable") or 0
        turns_since_new = obs.get("turns_since_new_tile") or 0
        turns_on_floor = obs.get("turns_on_floor") or 0
        kills_on_floor = obs.get("kills_on_floor") or 0
        if (reachable_tiles <= 20
                and reach_pct >= 90
                and turns_since_new >= 200
                and turns_on_floor >= 300
                and kills_on_floor < 20):
            return True
        # Standard gates (region big enough to plausibly hide
        # something the agent hasn't seen yet).
        if turns_on_floor < 1500:
            return False
        if turns_since_new < 800:
            return False
        if reach_pct < 90:
            return False
        return True


# ----------------------------------------------------------------------
# Policies
# ----------------------------------------------------------------------
def smart_policy(obs, rng, use_lantern=True):
    """Priority-gated policy that actually plays the game.

    Order of intents (highest priority wins):
      1. Critical HP   -> drink healing potion / cast Heal
      2. Hungry        -> eat food
      3. In combat     -> cast best affordable spell, else attack
      4. In a vendor   -> buy 1-2 healing potions + food, then leave
      5. Otherwise     -> explore (random move + occasional descend)

    Stateless: the policy re-derives intent from each observation. That keeps
    multi-step actions (open-inventory -> use-slot -> back) coherent without
    a hand-rolled FSM, since each step's gate condition resolves once the
    goal is achieved (HP up -> stop wanting to heal -> exit inventory).
    """
    mode = obs["mode"]
    p = obs["player"]
    inv = obs.get("inventory") or []
    spells = obs.get("memorized_spells") or []

    hp_pct = p["hp"] / max(1, p["max_hp"])
    hunger = p["hunger"]
    mana = p["mana"]

    heal_pot_slot = next((i["slot"] for i in inv
                          if i["category"] == "potion_healing"), None)
    # eat<N> is the second class of slot-mismatch the harness has hit:
    # handle_inventory_menu's eat<N> branch re-filters working_items to
    # Food/Meat only, then indexes off THAT list -- not the broader
    # sorted+combat-filtered inventory we report as `slot`. Compute the
    # 1-based position in the edible-items filter (which includes rotten
    # meat, so we count both 'food' and 'food_rotten' but prefer fresh).
    food_slot = None
    meat_slot = None  # first meat (rot_timer is not None) in the edible list
    # `urgent_meat` is set when we hold a fresh meat with a low rot timer.
    # Raw meat lasts 30 moves, cooked 100, preserved 200 -- eating slightly
    # before rot lets the agent stretch its food budget instead of letting
    # the kill drop go to waste. Tracks the 1-based edible-list index of
    # the first fresh meat with the shortest fuse.
    edible_count = 0
    urgent_meat = None
    urgent_rot = None
    MEAT_EAT_BEFORE = 20  # eat fresh meat at rot_timer <= 20 moves so kill drops actually convert to nutrition
    for i in inv:
        if i["category"] in ("food", "food_rotten"):
            edible_count += 1
            is_meat = i.get("rot_timer") is not None
            # Prefer meat over rations for the routine eat-when-hungry
            # gate. Rations are vendor-restockable; meat is per-kill
            # and rots after 30-200 moves. 160-seed audit found
            # s=666 elf accumulated 114 raw-meat samples + 34 cook
            # actions but only ATE 2 meats (and 4 rations) before
            # starving at F2 -- the routine eat picked the first
            # 'food' (rations) and meat sat until rotten.
            if is_meat and meat_slot is None:
                meat_slot = edible_count
            if i["category"] == "food" and food_slot is None:
                food_slot = edible_count
            # rot_timer is only set on Meat entries (Food rations don't rot).
            rot = i.get("rot_timer")
            if (i["category"] == "food" and rot is not None
                    and rot <= MEAT_EAT_BEFORE):
                if urgent_rot is None or rot < urgent_rot:
                    urgent_rot = rot
                    urgent_meat = edible_count
    # Routine eat prefers meat (perishable) over rations (stable).
    eat_slot = meat_slot if meat_slot is not None else food_slot
    # Spell-cast gate: the game refuses any cast attempt with
    # "Requires Intelligence > 15" (combat.py:1161) and consumes the
    # turn. Pre-memorised spells in the bag are useless until int
    # climbs past the threshold via level-ups, stat-boost potions,
    # altar boons, or library reads. Without this gate a dwarf at
    # int=8 with a memorised Heal would spin returning "c" in
    # combat_mode and burn the budget trying to cast a spell the
    # handler rejects every turn.
    can_cast = bool(p.get("can_cast"))
    heal_spell_slot = next((s["slot"] for s in spells
                            if s["type"] == "healing"
                            and s["mana_cost"] <= mana), None) if can_cast else None
    affordable_spells = ([s for s in spells if s["mana_cost"] <= mana]
                         if can_cast else [])
    affordable_dmg = [s for s in affordable_spells if s["type"] == "damage"]

    # Lantern state. With the omniscient nearest_features obs the agent
    # doesn't NEED to reveal tiles, but a real player would, and the
    # playtest answers a balance question: does spending fuel + turns on
    # the lantern net-help survival? Honest answer is "probably no since
    # tiles are already visible to the policy" -- the value here is the
    # data, not the gameplay.
    lantern = p.get("lantern")
    lantern_fuel = lantern["fuel"] if lantern else 0
    spare_fuel_uses = lantern["spare_fuel_uses"] if lantern else 0

    # Equipment damage signals: when an equipped weapon or armor is broken
    # or worn below 40%, we want to detour through a vendor for repair.
    equipped = p.get("equipped") or {}
    def _gear_needs_help(slot):
        if slot is None:
            return False
        if slot.get("is_broken"):
            return True
        pct = slot.get("durability_pct")
        return pct is not None and pct < 0.40
    weapon_worn = _gear_needs_help(equipped.get("weapon"))
    armor_worn = _gear_needs_help(equipped.get("armor"))
    needs_repair = weapon_worn or armor_worn

    # Equipment evaluation: find the strongest non-cursed weapon /
    # armor in inventory that beats whatever is currently equipped.
    # Returns the inventory slot to equip, or None if the current
    # gear is already best. Skips items the agent KNOWS are cursed
    # (welds to hand) or sealed (can't be repaired); unidentified
    # items are eligible -- that's the gamble the upgrade economy
    # is built around.
    is_shrunk = bool(p.get("is_shrunk"))
    def _best_upgrade(category, bonus_key, current_bonus):
        best_slot = None
        best_bonus = current_bonus
        for entry in inv:
            if entry["category"] != category:
                continue
            if entry.get("equipped"):
                continue
            if entry.get("is_broken"):
                continue
            if entry.get("buc_known") and entry.get("buc_status") == "cursed":
                continue
            # Bug-gear sizing: while shrunk only bug-sized gear
            # equips ("too tiny"), and while normal-sized bug gear
            # is rejected as "comically tiny in your hands". The
            # policy mirrors both filters so _best_upgrade doesn't
            # return a slot the equip handler will refuse.
            if is_shrunk and not entry.get("is_bug_gear"):
                continue
            if (not is_shrunk) and entry.get("is_bug_gear"):
                continue
            b = entry.get(bonus_key) or 0
            if b > best_bonus:
                best_bonus = b
                best_slot = entry["slot"]
        return best_slot, best_bonus
    cur_w = (equipped.get("weapon") or {}).get("attack_bonus") or 0
    cur_a = (equipped.get("armor") or {}).get("defense_bonus") or 0
    # Known-cursed equipped gear can't be unequipped (welds to hand),
    # so any swap or upgrade attempt against that slot just burns
    # i -> e<N> -> x turns. Skip the upgrade detection entirely when
    # cursed -- the only way out is an altar uncurse.
    cursed_weapon = bool(
        equipped.get("weapon")
        and equipped["weapon"].get("buc_known")
        and equipped["weapon"].get("buc_status") == "cursed"
    )
    cursed_armor = bool(
        equipped.get("armor")
        and equipped["armor"].get("buc_known")
        and equipped["armor"].get("buc_status") == "cursed"
    )
    weapon_upgrade_slot = None
    if not cursed_weapon:
        weapon_upgrade_slot, _ = _best_upgrade("weapon", "attack_bonus", cur_w)
    armor_upgrade_slot = None
    if not cursed_armor:
        armor_upgrade_slot, _ = _best_upgrade("armor", "defense_bonus", cur_a)
    has_upgrade = weapon_upgrade_slot is not None or armor_upgrade_slot is not None

    # Hoisted out of game_loop so tomb_mode etc. can use the same gate.
    broken_weapon = bool(equipped.get("weapon")
                         and equipped["weapon"].get("is_broken"))
    broken_armor = bool(equipped.get("armor")
                        and equipped["armor"].get("is_broken"))
    # Active dangerous status effects on the player (poison, web,
    # paralysis, sticky_hands, weakness, burn, freeze, etc.). Mirrors
    # gs.NEGATIVE_EFFECT_TYPES minus silence (gated separately by
    # can_cast) and shrinking (equipment-fit only). Used by is_weak
    # so the agent avoids new combat while statused, and by the
    # combat_mode flee branch so it disengages from an active fight
    # the moment a tick fires.
    active_status_types = set(p.get("status_effect_types") or [])
    has_bad_status = bool(active_status_types & _DANGEROUS_STATUS_TYPES)
    has_ticking_status = bool(active_status_types & _TICKING_STATUS_TYPES)
    immobilised = bool(active_status_types & _IMMOBILISING_STATUS_TYPES)
    # is_weak gates "should I avoid M tiles and skip risky targets".
    # Only ticking statuses (poison/burn/DoT/life_drain) and
    # immobilisation (web/paralysis/freeze) make new combat actually
    # dangerous; stat debuffs (weakness, blindness, confusion,
    # sticky_hands, defense_penalty) are tolerable for melee and
    # don't justify a full avoid-M policy that lets the agent
    # under-level. The cure-item open-inventory trigger still uses
    # has_bad_status so debuffs get treated when a cure is available.
    # Recently fled? The post-flee window pulls the agent into
    # heal-up-first mode so they don't blunder back into the same
    # monster at low HP. Surfaced via obs.recently_fled (30-turn
    # window) -- inside that window, the agent treats themselves as
    # is_weak so the wayfinder avoids M tiles, and the game_loop
    # heal trigger fires at hp_pct < 0.95 (vs the default 0.80 +
    # m_adjacent gate) so the recovery is to FULL.
    recently_fled = bool(obs.get("recently_fled"))
    is_weak = (
        hp_pct < 0.50
        or broken_weapon
        or broken_armor
        or (equipped.get("weapon") is None)
        or has_ticking_status
        or immobilised
        or (recently_fled and hp_pct < 0.80)
    )
    # Resource pressure: lantern fuel + hunger together set a soft
    # deadline on how long the agent can keep weaving the floor looking
    # for boons before it MUST start efficiently clearing monsters (for
    # meat / XP / gold) or descend. Without this clock the agent could
    # spend the whole budget exploring fog while the food + light run
    # out. Pressure says "stop dawdling, transition to hunt or descend."
    # Each LanternFuel canister adds 10 to the fuel gauge on auto-refill
    # (items.py: +10 per use), so spare units count as fuel * 10.
    fuel_total = (lantern_fuel or 0) + (spare_fuel_uses or 0) * 10
    resources_pressing = (
        hunger < 60       # below comfort, need meat soon
        or fuel_total < 15  # less than ~15 lantern fires of light left
    )
    # Starving = critical hunger AND no food in bag. Hoisted because
    # combat_mode also gates on it (flee from inedible monsters when
    # starving). Threshold raised 15 -> 30 so the override fires while
    # the agent still has HP cushion.
    starving = hunger <= 30 and food_slot is None

    if mode == "game_loop":
        # Tier 0 priorities -- self-care that takes precedence over
        # any exploration / fighting decision.
        # Growth Mushroom: instant escape from the bug-level quest.
        # If we're shrunk AND holding the mushroom, open inventory
        # so the in-inventory cascade can consume it -- this
        # un-shrinks the agent and re-opens the stairs. Beats
        # every other gate because it's the only way to break the
        # sealed-floor lockout.
        is_shrunk_now = bool(p.get("is_shrunk"))
        if is_shrunk_now:
            has_mushroom = any(
                e.get("category", "").startswith("potion_")
                and e.get("potion_type") == "growth_mushroom"
                for e in inv
            )
            if has_mushroom and obs.get("last_action") not in ("i", "x"):
                return "i"
        if hp_pct < 0.30 and heal_pot_slot:
            return "i"
        # Pre-emptive heal: 11 of 16 deaths in the analysis pass died
        # holding unused potions because the in-combat drink trigger
        # (HP<30%) fired too late -- monsters that won initiative could
        # take the agent 100% -> 5% in one hit, past the gate. Drink
        # BEFORE stepping into adjacent combat when HP <80% and a
        # potion is in the bag. The neighbors check is fog-of-war
        # aware: only fires if we actually see an M tile next door.
        neighbors_now = obs.get("neighbors") or {}
        m_adjacent = any(neighbors_now.get(d) == "M"
                         for d in ("n", "s", "e", "w"))
        if heal_pot_slot and hp_pct < 0.80 and m_adjacent:
            return "i"
        # Post-flee recovery: heal aggressively to FULL after a flee
        # so we don't walk back into the same monster at low HP.
        # Celeborn the elf seed=271 was fleeing wraiths at HP 24-26,
        # taking the unconditional monster parting attack on every
        # flee, then immediately re-engaging without healing -- the
        # combat heal-pot gate at HP<50% never fired because each
        # round started above it. Recovery uses the 0.95 ceiling the
        # inventory branch's heal logic already targets. Burns
        # potions, but losing a fight is more expensive than three
        # healing potions.
        if recently_fled and hp_pct < 0.80 and heal_pot_slot:
            return "i"
        # Pre-combat buff drink in game_loop: when M is adjacent AND
        # we have an identified buff potion (strength/defense/stone
        # skin/regeneration/berserker/etc.) AND HP is 60-95% (NOT at
        # max -- if hp >= 95% the inventory branch's buff-drink gate
        # rejects, falling through to a scroll read that may not
        # consume; agent loops `i -> x -> i -> x`. Gate aligned to
        # match the inventory branch).
        BUFF_POTION_TYPES = {
            "strength", "defense", "stone_skin", "regeneration",
            "berserker", "giant_strength", "haste", "vampirism",
            "frost_armor", "fortune",
        }
        has_buff_potion = any(
            i.get("category", "").startswith("potion_")
            and i.get("is_identified")
            and i.get("potion_type") in BUFF_POTION_TYPES
            for i in inv
        )
        if (has_buff_potion and 0.60 <= hp_pct < 0.95
                and m_adjacent):
            return "i"
        # Bad-status cure: when the player has a curable negative
        # effect (poison / web / sticky_hands / confusion etc.) AND
        # a Scroll of Restoration or Antidote-style cure_all potion
        # is in the bag, open inventory to consume it. Without this
        # trigger the agent kept walking through poison ticks /
        # confusion-spam until the duration ticked down naturally.
        has_cure_item = any(
            (i.get("category") == "scroll"
             and i.get("is_identified")
             and i.get("scroll_type") == "restoration")
            or (i.get("category", "").startswith("potion_")
                and i.get("is_identified")
                and i.get("potion_type") == "cure_all")
            for i in inv
        )
        if has_bad_status and has_cure_item:
            return "i"
        if urgent_meat is not None:
            return "i"
        # Cooking gate: user spec is "cook all their meat once they
        # have the kit -- eating cooked meat is much better for
        # survival." Fire whenever has_cooking_kit AND has_raw_meat,
        # no hunger gate. The kit cooks ALL raw meat in one action
        # (CookingKit.use()), so this triggers once per batch of
        # fresh kills regardless of how much remains. urgent_meat
        # still fires first when a raw meat is about to rot --
        # better to eat it raw than to lose it before the cook turn
        # completes.
        has_cooking_kit = any(i["category"] == "cooking_kit" for i in inv)
        has_raw_meat = any(
            i["category"] == "food" and i.get("rot_timer") is not None
            and not i.get("is_cooked")
            for i in inv
        )
        if has_cooking_kit and has_raw_meat:
            return "i"
        # broken_weapon / broken_armor / is_weak are hoisted above.
        # Open inventory to swap when current gear is broken AND we
        # have a working spare, OR when an unequipped item beats what's
        # in the slot (subsumes the prior broken-only check).
        # cursed_weapon / cursed_armor: skip the swap if the broken
        # slot is welded on -- equip attempts just bounce off and the
        # agent burns 3 turns per i->e<N>->x cycle until uncurse.
        if (broken_weapon and not cursed_weapon and any(
                e["category"] == "weapon" and not e.get("is_broken")
                and e["name"] != equipped["weapon"]["name"]
                for e in inv)):
            return "i"
        if (broken_armor and not cursed_armor and any(
                e["category"] == "armor" and not e.get("is_broken")
                and e["name"] != equipped["armor"]["name"]
                for e in inv)):
            return "i"
        if has_upgrade:
            return "i"
        # Wedge escape: when the agent has ARRIVED at the current
        # tile 6+ times on this floor (real bounces, not stand-still
        # inventory ops -- floor_visit_count only bumps on movement),
        # the wayfinder has lost the plot. Durin seed=314 dwarf on
        # F2 burned 2345 turns at HP=1 in a (2,1)<->(3,1)<->(1,1) U
        # corridor with no D reachable. Open inventory so the
        # wedged-item-use block can read any escape scroll (mapping
        # reveals fog, teleport relocates) or drink unidentified
        # potions as Hail Marys. Gate on last_action != "i" so the
        # trigger doesn't fire on the same turn we just exited
        # inventory (that would be a 1-turn ping). The inventory
        # branch's last_action guards prevent re-picking the same
        # item twice in a row.
        current_tile_visits = obs.get("current_tile_visits") or 0
        wedged = current_tile_visits >= 6
        attempted_already = (
            set(obs.get("wedge_attempted_actions") or [])
            | set(obs.get("wedge_tried_this_floor") or [])
        )
        WEDGE_SKIP_SCROLL_TRIGGER = {"spell_scroll", "vendor_restock"}
        untried_scroll = any(
            e["category"] == "scroll"
            and not (e.get("is_identified")
                     and e.get("scroll_type") in WEDGE_SKIP_SCROLL_TRIGGER)
            and f"u{e['slot']}" not in attempted_already
            for e in inv
        )
        untried_unid_potion = any(
            e["category"].startswith("potion")
            and not e.get("is_identified")
            and f"u{e['slot']}" not in attempted_already
            for e in inv
        )
        if (wedged and (untried_scroll or untried_unid_potion)
                and obs.get("last_action") not in ("i", "x")):
            return "i"
        # Eat at hunger < 50 so each ration delivers close to full
        # nutrition value -- rations are 50 nutrition (build 305),
        # so eating at 49 hits the 100 cap with one unit to spare,
        # while eating at 70 wastes ~20 nutrition to the cap. Still
        # well above HUNGER_STARVING_THRESHOLD (10) so the safety
        # margin remains. User: 'work on balance so some are still
        # alive without looping at the end' -- food efficiency
        # extends the food-clock window proportionally.
        if hunger < 50 and eat_slot:
            return "i"

        # Lantern as exploration tool. With fog-of-war on, neighbours
        # show None for undiscovered tiles -- light up so the wayfinder
        # has something to work with. The new radius (light_radius +
        # upgrade_level, was upgrade_level + 1) gives the starter a
        # 7-tile reveal, so one light is enough for several moves of
        # planning before fuel becomes a concern.
        neighbors = obs.get("neighbors") or {}
        visited = obs.get("visited_neighbors") or {}
        unknown_neighbours = sum(1 for v in neighbors.values() if v is None)
        # Light up when fog-blind (>= 2 unknown neighbours), or when
        # stuck and even one is unknown, or periodically (every 10
        # turns) when truly stuck to reveal farther-out tiles past the
        # immediate region. The radius-7 cardinal lantern reveals up to
        # 28 cells per fire even when all four neighbours are already
        # known -- the rays shoot down corridors. Without this the
        # agent corners itself in a small explored region and never
        # discovers the rest of the floor.
        turns_on_floor = obs.get("turns_on_floor") or 0
        stuck_on_floor = turns_on_floor > 100
        very_stuck = turns_on_floor > 200
        # Lantern policy: KNOW what you're walking into. The lantern
        # reveals tiles along the four cardinal axes up to
        # (light_radius + upgrade_level) -- 7+ cells per direction
        # with the starter lantern -- so one fire often catches a W
        # or M tile several rooms away. Fire whenever the next step
        # could land on an undiscovered tile (any fog-adjacent
        # neighbour). Per user framing: "best way to stay alive is
        # know what you are walking into for each room."
        #
        # TWO EXPLICIT RELEASE VALVES skip the fire:
        #   1. fuel_scarce: lantern_fuel + spare canisters * 10 < 15
        #      uses left. Conserve the last few fires for genuine
        #      emergencies and trust the wayfinder's AVOID set.
        #   2. strong_and_healthy: pc.level >= pc.floor + 2 AND
        #      hp_pct >= 0.80. An over-levelled, full-HP agent can
        #      tank a surprise wraith / warp / chest-gas the lantern
        #      would have revealed -- the fuel cost outweighs the
        #      surprise cost.
        fuel_total = (lantern_fuel or 0) + (spare_fuel_uses or 0) * 10
        # Two-tier fuel gate. "Low" lets the agent skip frivolous
        # fires (random fog-adjacent move on a known-safe area).
        # "Empty" is the hard stop -- can't fire without fuel.
        # Critical lanterns (fog-adjacent step IMMINENT) always fire
        # while fuel > 0, even when fuel_low triggers -- a single
        # warp is worth dozens of saved fires. User-flagged Forlong
        # of the Mark (human seed 314): stepped east into a fog
        # tile that was W, got forced-warped F2->F4, because fuel=10
        # triggered the old 'fuel_scarce' gate and the lantern
        # skipped the critical reveal.
        fuel_empty = lantern_fuel <= 0
        over_leveled_for_floor = (
            p.get("level", 1) >= p.get("floor", 1) + 2
        )
        strong_and_healthy = over_leveled_for_floor and hp_pct >= 0.80
        # Critical fire: any fuel left + fog adjacent = burn it.
        # User on Gimli the Mighty (s=256 dwarf, F14 L6, 147 kills):
        # "I would think players would be avoiding warps more". Gimli
        # warped 5+ times by stepping into fog tiles that turned out
        # to be W -- the prior `not strong_and_healthy` gate let an
        # over-levelled healthy agent skip the reveal because they
        # could "tank a surprise wraith / warp / chest-gas". The cost
        # asymmetry is wrong: an extra wraith is a few HP, a force-
        # warp is 100-200 turns of recovery + retreat. ANY fuel +
        # ANY fog neighbour = fire. Strong agents still skip when
        # all four neighbours are already known (the gate below).
        if (use_lantern and not fuel_empty
                and unknown_neighbours >= 1):
            return "l"
        # Periodic stuck-fire even when other gates would skip --
        # reveals long-range tiles when the agent is truly cornered.
        # Uses fuel_total (lantern + spare canisters) instead of raw
        # lantern_fuel so an agent with 2 spare cans at lantern_fuel=5
        # still fires. Arwen Silverleaf (s=42 elf F1) burned 2960
        # turns at HP=1 with 2 spare canisters because the prior
        # `lantern_fuel > 5` gate gated on the in-lantern reservoir
        # alone, and her four immediate neighbours were all known so
        # the unknown-neighbours gate also skipped -- but the lantern
        # would have revealed undiscovered tiles further down the
        # corridor (radius 7 per cardinal).
        if (use_lantern and fuel_total > 5
                and very_stuck and obs["turn"] % 10 == 0):
            return "l"

        # Weakness model (hoisted to top of smart_policy for reuse in
        # tomb_mode / pool_mode). When weak we avoid stepping onto
        # monsters (M) or warps (W) because random teleport could drop
        # us into a deeper floor's monster room, and combat at low HP
        # / broken gear is a death sentence.
        # Starvation override: when hunger is critical AND we have no
        # food in the bag, drop the M-avoid so the agent will engage
        # monsters for meat drops. The prior policy made dying agents
        # MORE timid (HP < 50% triggers AVOID), which trapped them in
        # slow-motion starvation pinning at HP=1 for 1500+ turns
        # (7/30 runs in the last playtest). When the chicken-and-egg
        # is "no meat -> can't fight" we'd rather try the fight.
        # `starving` is hoisted to the top of smart_policy.
        #
        # Warps are avoided on the early floors (z < 10): the
        # warp_action drops the agent at random within +/- 2 floors,
        # which routinely lands a fresh Lv1 dwarf next to a Wraith
        # on F3 with no escape route. Even healthy agents shouldn't
        # gamble that early; the 20-44% resist roll fails often
        # enough that resisting isn't reliable cover. Once the agent
        # is in the late game (z >= 10) the depth boost from a lucky
        # warp can outweigh the downside, so the avoid drops.
        #
        # ESCAPE VALVE: if the agent is truly trapped on this floor
        # -- 400+ turns spent here AND no D reachable on the
        # discovered map -- the warp is the only way out, so we drop
        # the W avoid. Without this, seeds with region-split floors
        # (seed 7 F1, seed 500 F1) softlock at HP=1 alive forever.
        # NOTE: was `z < 10` -- the user flagged Gimli the Mighty
        # (s=256 dwarf F14 L6) for "warping a lot" past z=10. The
        # late-game release was meant to let lucky warps boost
        # depth, but the cost asymmetry is wrong (warp = 100-200
        # turn recovery vs minor depth bump). Always AVOID W
        # unless trapped_no_d -- BFS still excludes W from transit
        # so this only matters for fog steps and random fallbacks.
        early_floor = True
        feature_paths_avoid = obs.get("feature_paths") or {}
        d_avoid_reachable = bool(
            (feature_paths_avoid.get("D") or {}).get("first_step")
        )
        # Treat D as unreachable for the trapped_no_d gate when the
        # only D leads to a PERMANENT wedge floor (3+ wedge-add
        # events, agent has provably bounced through this layout
        # multiple times). The wayfinder should now seek W instead
        # so the agent skips past the impassable floor via warp.
        # Caught on s=88 human: F1 D points to F2 wedge, agent
        # cycled F1 <-> F2 for 1500+ turns until starvation.
        cur_z_for_perm = p.get("floor", 1) - 1
        perm_wedge = set(obs.get("permanent_wedge_floors") or [])
        d_leads_to_perm_wedge = (cur_z_for_perm + 1) in perm_wedge
        if d_leads_to_perm_wedge:
            d_avoid_reachable = False
        coverage_obs_avoid = obs.get("tile_coverage") or {}
        coverage_pct_avoid = coverage_obs_avoid.get("pct", 0)
        reach_pct_avoid = coverage_obs_avoid.get("reach_pct", 0)
        frontier_avoid = obs.get("frontier_step")
        # Behavioral trapped detector: D unreachable AND the agent
        # has stopped making exploration progress (no new tile
        # visited in 100+ turns). The agent is on an island, has
        # walked it, and the wayfinder is just bouncing among
        # already-visited tiles. Uses turns_since_new_tile (NOT
        # global pct or reach_pct), because:
        #  - global pct false-negatives on region-split floors
        #    (Gloin III s=99 dwarf: 9-tile pocket of 122-tile F1,
        #    max 7.4% global pct, prior gate never fired).
        #  - reach_pct false-positives on early exploration
        #    (Gimli s=256 dwarf at T17: 66% of 9 reachable tiles
        #    walked, prior gate fired and he warped to a Lv2
        #    Vault Keeper Wraith on the same floor).
        # turns_since_new_tile measures actual progress: while the
        # agent keeps reaching new tiles via walking + lantern
        # reveals, no escape valve.
        #
        # User asked agents to avoid warps unless absolutely
        # necessary, so this gate now requires THREE conditions:
        #   1. D is unreachable on the discovered map.
        #   2. reach_pct >= 90% -- the agent has walked nearly all
        #      reachable tiles, so further wandering won't reveal
        #      a hidden path to D via lantern. Without this, the
        #      old 100T-since-new gate fired on small starting
        #      pockets where the agent could still uncover ground
        #      via short detours.
        #   3. turns_since_new >= 200 -- doubled from 100T to give
        #      a real exploration budget. Was popping the warp valve
        #      on agents who'd just paused for a long fight, eaten
        #      from inventory, or done some other non-movement work.
        # If ALL three fire, the floor is a genuine warp-only island
        # (region-split layout) and warping is the only way out.
        # 159-seed grid before tightening: 35% of floor changes were
        # warps (194 forced + 35 accepted of 647 transitions).
        turns_since_new = obs.get("turns_since_new_tile") or 0
        turns_on_floor_avoid = obs.get("turns_on_floor") or 0
        # trapped_no_d: D unreachable + agent has exhausted exploration.
        # Three firing paths:
        #   1. Standard: swept >= 80% of reachable tiles AND no new
        #      tile in 200T. (Eased from reach_pct >= 90; build-329
        #      audit caught s=88 dwarf stuck at reach_pct=85% for
        #      2500+ turns because BFS-reachable count included a
        #      handful of tiles the wayfinder never routed to.)
        #   2. Long-stale: no new tile in 500T regardless of
        #      reach_pct. Covers the rare case where reach_pct
        #      stays low because BFS discovers new fog-tiles
        #      faster than the agent walks to them, but the agent
        #      is functionally idle anyway.
        #   3. Long-floor: 600T on the same floor with no D found.
        #      Catches s=317 elf 3220T F3 with 402 kills -- agent
        #      kept revealing 1 new tile every 200T (so ts_new
        #      never hit 500) while D stayed unreachable in a
        #      different region. The 600T floor budget is generous
        #      vs the avg 130-160 moves a productive floor takes.
        trapped_no_d = (
            (not d_avoid_reachable)
            and (
                (reach_pct_avoid >= 80 and turns_since_new >= 200)
                or (turns_since_new >= 500)
                or (turns_on_floor_avoid >= 600)
                # Fast-path: D points only to a permanent wedge AND a
                # warp is in reach. No need to wait for full
                # exploration -- the agent has already proven this
                # floor's D is a dead end and the food clock is
                # ticking. Caught on s=88 human dying 2032T on F2
                # after cycling F1 <-> F2 wedge.
                or (d_leads_to_perm_wedge
                    and obs.get("nearest_warp_path") is not None
                    and turns_on_floor_avoid >= 150)
                # Fully-explored-but-no-D fast-path: reach_pct>=95
                # AND a warp is reachable. The agent has swept their
                # region and there's literally no D to find -- warp
                # is the only escape, fire trapped_no_d immediately
                # so the W tier kicks in. Caught on s=500 human F1:
                # 24-tile region, no D, W reachable, ts_new=18 (not
                # 200+), turns_on_floor=170 (not 600+), so trapped
                # didn't fire and agent oscillated around W for 280T
                # before the standard 200T-since-new gate engaged.
                or (reach_pct_avoid >= 95
                    and obs.get("nearest_warp_path") is not None)
            )
        )
        # Cornered detection: agent's ONLY walkable cardinal
        # neighbour is an M tile (the rest are walls). Without this
        # override the agent can sit on the tile forever while M
        # stays in AVOID (e.g., Galadhrim Goldenbough elf seed 999
        # lost his starter Dagger to durability decay, is_weak
        # fires from "no weapon", AVOID adds M, agent oscillates
        # s/e/w into walls for 1500+ turns). Forcing M-engagement
        # in this corner case gives the agent a chance at a weapon
        # drop from the kill -- better than the indefinite stuck
        # state.
        peek_neighbours = obs.get("neighbors") or {}
        walkable_neighbour_types = {
            peek_neighbours.get(d)
            for d in ("n", "s", "e", "w")
            if peek_neighbours.get(d) not in (None, "#")
        }
        only_m_walkable = walkable_neighbour_types == {"M"}

        avoid_set = set()
        if is_weak and not starving and not only_m_walkable:
            avoid_set.add("M")
        if (is_weak or early_floor) and not trapped_no_d:
            avoid_set.add("W")
        # Avoid D while under-levelled and the floor's grind isn't
        # done. Without this, an agent who walked OFF the D tile
        # (stairs_down_mode's step-off branch) gets pulled BACK onto
        # D by the wayfinder targeting fog past it -- Anborn of the
        # White City (human seed 1100) burned 1260 game-loop turns
        # walking west onto D and 1260 stairs_down_mode turns
        # stepping east off D. The grind-gate tier filter strips D
        # from priority, but BFS over walkable tiles still treats D
        # as transit; adding D to AVOID prevents the step ENTIRELY
        # until grind_complete releases (kills target met or floor
        # 70% explored).
        avoid_pc_floor = p.get("floor", 1)
        avoid_pc_z = avoid_pc_floor - 1
        avoid_under_leveled = p.get("level", 1) <= avoid_pc_z + 1
        avoid_kills = obs.get("kills_on_floor") or 0
        avoid_min_kills = min(12, max(3, avoid_pc_z * 2 + 1))
        avoid_coverage = (obs.get("tile_coverage") or {}).get("pct", 0)
        avoid_grind_done = (
            avoid_kills >= avoid_min_kills
            or avoid_coverage >= 70
        )
        if (avoid_under_leveled and not avoid_grind_done
                and not is_weak and not trapped_no_d):
            # Restore `not is_weak`: dropping it left HP=1 retreat
            # agents (Thorin / Legolas / Boromir seed 1234) stuck
            # on F1 because the BFS first_step was D, the AVOID-D
            # filter swapped it, and there were no real alternatives
            # so they oscillated. Better to let weak agents step on
            # D and descend (or trigger the stairs_down step-off)
            # than to lock them at F1.
            avoid_set.add("D")
        # Retreat-after-warp: agent wants to ASCEND, not descend.
        # Adding D to AVOID prevents the wayfinder's frontier walker
        # from routing through a D tile (BFS treats D as walkable
        # transit) and triggering stairs_down_mode where the agent
        # then loops step-off/walk-back. Anborn of the White City
        # (human seed 1100): warped F1->F3 at T464, retreated F3->F2
        # at T476, then burned 2500 turns oscillating between F2's
        # D tile and the tile next to it. Trapped_no_d still releases
        # the avoid so the agent can warp out if truly stuck.
        # Retreat-mode trapped check: if the agent is retreating but
        # U isn't reachable on this floor AND they've spent enough
        # turns trying, release the D-avoid so they can at least
        # descend (probably into worse, but at least they leave the
        # F2 ping-pong). Anborn of the White City (human seed 1100)
        # was retreat-stuck on F2 D tile with all neighbours
        # walls/M/D for 2500+ turns -- no path to U existed because
        # the agent had only explored 2.7% of the floor.
        retreat_active = obs.get("retreat_to_floor") is not None
        retreat_u_path = (feature_paths_avoid.get("U") or {}).get("first_step")
        retreat_trapped = (
            retreat_active
            and not retreat_u_path
            and turns_since_new >= 100
        )
        if retreat_active and not trapped_no_d and not retreat_trapped:
            avoid_set.add("D")
        AVOID = avoid_set
        # Targeted tomb-guardian avoid. Adjacent M tiles flagged as
        # `undead_guardian` are the 4 tomb-adjacent spawns (one elite
        # at floor+1, three regular undead at floor). The agent
        # should NOT step into one of these unless over-levelled
        # enough to win the trade. Release valve: pc.level >=
        # pc.floor + 2 (so F7 needs Lv9). Surgical -- only blocks
        # the specific cardinal dirs that lead to a guardian; other
        # M tiles remain valid targets for normal grinding.
        # User-flagged after Gloin Axebreaker (seed 2500 dwarf, F7
        # L7) walked east into a tomb-adjacent M and died to an
        # ELITE UNDEAD DRAGON LICH. tomb_guardian_dirs is exposed
        # via obs and only populated for DISCOVERED tiles -- the
        # agent has to actually see the M before recognising it as
        # a guardian.
        guardian_dirs = set(obs.get("tomb_guardian_dirs") or [])
        # Inferred guardians: cardinal-adjacent tile sits next to a
        # DISCOVERED T. Every tomb spawns four cardinal guardians
        # (dungeon.py setup_dungeons_and_tombs), so once the agent
        # has SEEN a T they can rule out the four corner tiles
        # WITHOUT having to step adjacent to each M first. User-
        # requested: "create playtests logic that detects 'a tomb
        # might be here so there could be a guardian in one of these
        # adjacent rooms'". Folded into the same release-gate as
        # the M-confirmed guardian_dirs -- once over-levelled, the
        # agent will still engage the corner mobs for XP/gold.
        inferred_guardian_dirs = set(obs.get("inferred_guardian_dirs") or [])
        all_guardian_dirs = guardian_dirs | inferred_guardian_dirs
        # Release threshold: pc.level >= pc.floor + 3 (was +2). The
        # earlier +2 gate released for Lv4 elf on F2 (4 >= 4), but
        # the elite mummy at Lv4 hits fragile races (elf base HP 28)
        # for 28 per swing -- one-shot. +3 keeps the avoid active
        # until the agent actually has the HP cushion to survive
        # the trade.
        guardian_safe = p.get("level", 1) >= p.get("floor", 1) + 3
        blocked_guardian_dirs = (
            all_guardian_dirs if all_guardian_dirs and not guardian_safe
            else set()
        )

        # Clear-before-descend gate. Beneficials = rooms that pay off
        # without forced combat (chest, garden, library, oracle, altar,
        # pool). Tombs (T) and dungeons (N) are kept off the "must
        # clear" list because they trigger guardian fights / locked
        # gates -- the agent can still target them but won't refuse
        # descent for them. D is suppressed while unvisited beneficials
        # remain so the playtester actually clears the floor before
        # moving on.
        # BENEFICIAL_SAFE = rooms that pay off without forced combat.
        # Q (alchemist): combine 2 potions for stronger result.
        # K (war room): free intel reveals next floor's special rooms.
        # B (blacksmith): cheap repair of worn gear.
        # F (shrine of the fallen): one-shot stat boost.
        # X (taxidermist) deliberately omitted -- only useful when the
        # agent has trophies, and adding it forces BFS detours for an
        # often-empty handoff. Stepped onto incidentally still works
        # via the mode handler, just not proactively targeted.
        BENEFICIAL_SAFE = ("C", "G", "L", "O", "A", "P", "Q", "K", "B", "F")
        # Use BFS-aware feature_paths so we only delay descent for
        # beneficials we can actually reach. The old Manhattan check
        # (nearest_features) counted beneficials behind walls, leading
        # to endless clear-before-descend loops on closed floors.
        # Include V here so the agent never descends with an unvisited
        # vendor reachable -- vendor-on-every-floor guarantee. Once V
        # is visited it leaves feature_paths and the gate releases.
        nearest = obs.get("nearest_features") or {}
        feature_paths_check = obs.get("feature_paths") or {}
        unvisited_beneficials_exist = any(
            feature_paths_check.get(t) for t in BENEFICIAL_SAFE + ("V",)
        )
        # Boon-exhaustion gate (replaces the old Lv>=3 character-strength
        # gate). A real player squeezes every safe boon out of a floor
        # before committing to monster clearing -- chests, gardens,
        # altars, pools, libraries, oracles. Once those are gone (or
        # resources are pressing so we can't afford more weaving) the
        # agent shifts into efficient-clear mode: hunt M tiles for meat
        # + XP + gold, then descend. Requires we're not is_weak so
        # broken-gear / low-HP agents recover first instead of picking
        # fights they can't win.
        ready_to_clear = (
            not is_weak
            and (not unvisited_beneficials_exist or resources_pressing)
        )
        # Stuck-on-floor override: if we've spent more than this many
        # turns on the current floor, drop the clear-before-descend
        # gate. Pulls the agent off floor 1 when an unreachable
        # beneficial (behind a wall the greedy walker can't navigate
        # around) would otherwise loop forever. 300 turns is enough
        # to do a thorough sweep of a 18x21 floor.
        FLOOR_STUCK_TURNS = 300
        too_long_on_floor = (obs.get("turns_on_floor") or 0) > FLOOR_STUCK_TURNS
        if too_long_on_floor:
            unvisited_beneficials_exist = False

        # Keyed dungeons get exposed via obs.keyed_dungeon_target,
        # which filters out looted dungeons -- referenced below in the
        # adjacent-key shortcut and the distant wayfinder.

        # Build the priority list. Order: keyed dungeons > vendor (if
        # needed) > safe beneficials > unlocked tombs (when healthy) >
        # plain N (only valuable once a key drops) > D. When weak,
        # drop tombs/dungeons -- those have guardians that finish a
        # low-HP run quickly. M and W are NEVER active targets.
        healing_count = sum(i.get("count", 1) for i in inv
                            if i["category"] == "potion_healing")
        wants_vendor = ((healing_count < 2 or needs_repair)
                        and p["gold"] >= 50)

        # Tile-coverage descent gate: when we've swept >= 70% of this
        # floor's walkable tiles AND D is reachable, descend even if
        # a few SAFE rooms remain unvisited (probably stuck behind a
        # wall the BFS can navigate but the cost-to-walk-there isn't
        # worth it). The waste% audit caught agents burning 50+
        # patrol-bouncing moves to retrieve one far beneficial after
        # the bulk of the floor was explored.
        coverage_pct = (obs.get("tile_coverage") or {}).get("pct", 0)
        d_path = feature_paths_check.get("D")
        d_reachable = bool(d_path and d_path.get("first_step"))
        # Grind gate. Roguelike convention: character level should
        # roughly match floor depth. A Lv2 player on F4 is under-
        # levelled and gets vaporised by the next wraith. When
        # pc_level <= pc_z, the agent stays on the current floor
        # banking XP before descending -- D is dropped from the
        # priority tiers, the high-coverage descend gate gets a
        # minimum-kills requirement, and the tier ordering pulls M
        # ahead of D so the agent actively hunts for fights.
        # M is in BLOCK_TRANSIT for the main BFS so feature_paths['M']
        # would always be None. obs.nearest_monster_path uses a
        # different BFS that walks to a cardinal neighbour of an M
        # tile then steps in; that's the right reachability signal
        # for the grind gate.
        nm_path = obs.get("nearest_monster_path") or {}
        m_reachable_via_path = bool(nm_path.get("first_step"))
        m_reachable_adj = any(
            (obs.get("neighbors") or {}).get(d) == "M"
            for d in ("n", "s", "e", "w")
        )
        m_reachable = m_reachable_via_path or m_reachable_adj
        # Minimum kills required before this floor's descend gate
        # opens. Scales with depth: F1 needs 3, F3 needs 5, F5 needs
        # 9. Past that the curve caps at 12 so deep floors don't
        # demand impossible grind counts. Bumped from the earlier
        # F4=5 / F8=9 curve because the lighter version didn't
        # actually change the grid (existing tier order already
        # preferred SAFE/V/M over D when boons remained, so the
        # filter was a near no-op).
        pc_z = (p.get("floor", 1) - 1)
        min_kills_for_floor = min(12, max(3, pc_z * 2 + 1))
        kills_so_far = obs.get("kills_on_floor") or 0
        # under_leveled fires when:
        #  - pc.level <= pc.z + 1 (Lv N on F N is "on-pace", anything
        #    below is under-levelled -- Lv2 on F3 / Lv3 on F4 etc.
        #    qualifies), AND
        #  - this floor still has a reachable monster to fight.
        # The pc.z comparison uses the 0-indexed floor; the user-
        # facing floor is z+1, so "Lv equal to displayed floor" =
        # pc.level == pc.z + 1.
        # under_leveled drops the m_reachable check -- if there are
        # NO visible monsters and the agent is under-levelled, we
        # want them to explore (find more monsters in fog) before
        # descending, not bolt for the stairs.
        under_leveled = (p.get("level", 1) <= pc_z + 1)
        # Grind is "not done" until one of:
        #   - kills_so_far meets the per-floor minimum, OR
        #   - no monsters remain reachable AND coverage >= 70%
        #     (i.e., the floor has been thoroughly swept and the
        #     visible M tiles are gone; remaining M tiles, if any,
        #     are behind fog the BFS can't path through anyway).
        # The 70% gate is softer than high_coverage_descend's 80%
        # because grind cares about M tiles, not boons -- once 70%
        # of walkable tiles are seen, most M spawns have been found.
        grind_complete = (
            kills_so_far >= min_kills_for_floor
            or (not m_reachable and coverage_pct >= 70)
        )
        # 90% sweep + D reachable + not weak + grind done. Bumped
        # 80 -> 90 because a 20% slice of an 18x21 floor still
        # hides plenty of M spawns the agent hasn't fought; the
        # earlier threshold descended before the floor's XP was
        # banked. grind_complete (min_kills met OR thoroughly
        # explored with no M visible) is the second gate -- ensures
        # under-levelled agents don't rush past their depth.
        high_coverage_descend = (
            coverage_pct >= 90
            and d_reachable
            and not is_weak
            and grind_complete
        )

        # Tomb-suspected on this floor: the agent has fought an undead
        # here, which (per the rebalanced spawn logic) means there's a
        # T tile somewhere on the floor and an ELITE UNDEAD waits at
        # one of the other 3 tomb-adjacent guardian rooms. When weak,
        # we want the agent to actively avoid blundering into another
        # wraith while limping toward healing -- drop M from the
        # priority and treat T as a NO-GO unless we're back at full
        # strength. The flag is set by _monster_obs the first time the
        # agent enters combat with an undead and stays set for the
        # remainder of the floor.
        tomb_suspected = bool(obs.get("tomb_suspected_here"))

        # Retreat-after-warp override. obs.retreat_to_floor is set
        # whenever pc.z exceeds max_z_via_stairs -- i.e. a warp dropped
        # the agent onto a floor they haven't earned via stairs yet.
        # Those floors are near-instakill on a fresh Lv1 / Lv2
        # character per the user's framing: the monster pool is
        # tuned for their floor depth, and the agent doesn't have
        # the level / gear / item supply. Cut the wayfinder over to
        # ascend mode: target U exclusively (with V as a fallback if
        # U isn't visible yet) so the agent makes for the up stairs.
        # The stairs_up_mode + stairs_down_mode branches below also
        # check this flag to flip their descend / walk-away
        # behaviour into ascend.
        retreat_to_floor = obs.get("retreat_to_floor")
        # Trapped-no-D escape: region-split floor where D is behind
        # walls and the only way out is a known W tile. The W tier
        # is handled specially in the tier-iteration below
        # (feature_paths doesn't include W, but nearest_warp_path
        # provides the approach + step-onto-W). This block takes
        # priority over everything except retreat (which targets U
        # back to known territory).
        if (retreat_to_floor is None
                and trapped_no_d
                and obs.get("nearest_warp_path")):
            tiers = [("W",), ("V",)]
        elif (retreat_to_floor is None
                and trapped_no_d
                and not obs.get("nearest_warp_path")
                and obs.get("nearest_monster_path")):
            # Trapped on island with no D, no W, but a visible M.
            # Engage as last resort -- "die fighting" beats the
            # indefinite HP=1 flatline. Arwen Silverleaf (s=42 elf
            # F1) was wedged for 2960 turns at HP=1 with a tomb-
            # guardian M blocking her only exit east; AVOID-M
            # already drops when starving, but is_weak's priority
            # list excludes M, so she paced two `.` tiles forever
            # without ever stepping toward the only available
            # threat. The M tier wires nearest_monster_path so
            # she'll walk to the M and engage. Loss is bounded
            # (one combat); the alternative is a 3000-turn flatline.
            tiers = [("M",)]
        elif retreat_to_floor is not None:
            tiers = [("U",), ("V",)]
        elif too_long_on_floor:
            tiers = [("D",), ("V",)]
        elif high_coverage_descend:
            # Floor mostly swept + stairs in sight -- go.
            tiers = [("D",), tuple(BENEFICIAL_SAFE), ("V",), ("M",), ("T", "N")]
        elif is_weak:
            tiers = [("V",), tuple(BENEFICIAL_SAFE)]
            if not unvisited_beneficials_exist:
                tiers.append(("D",))
        elif wants_vendor:
            tiers = [("V",), tuple(BENEFICIAL_SAFE), ("T", "N")]
            if not unvisited_beneficials_exist:
                tiers.append(("D",))
        elif ready_to_clear:
            tiers = [tuple(BENEFICIAL_SAFE), ("V",), ("M",),
                     ("T", "N"), ("D",)]
        elif unvisited_beneficials_exist:
            tiers = [tuple(BENEFICIAL_SAFE), ("V",), ("M",), ("T", "N")]
        else:
            tiers = [("D",), tuple(BENEFICIAL_SAFE), ("V",), ("M",), ("T", "N")]
        # Tomb-aware filter: when an undead has been encountered on
        # this floor AND the agent is weak (low HP or broken gear),
        # strip M and T/N from every tier. M because stepping into
        # another tomb guardian at low HP is a death sentence; T/N
        # because the elite guardian is sitting next to a T tile we
        # might wander into while route-planning around. The agent
        # keeps targeting V/SAFE/D so it can heal up or descend off
        # the floor cleanly.
        if tomb_suspected and is_weak:
            tiers = [
                tuple(t for t in tier if t not in ("M", "T", "N"))
                for tier in tiers
            ]
            tiers = [tier for tier in tiers if tier]
            tiers = [tier for tier in tiers if tier]
        # Shrunk filter: Zot's spell on bug-levels blocks stairs in
        # BOTH directions ('the drop is lethal' / 'stairs impossibly
        # tall'). Targeting D or U while shrunk burns the agent's
        # turn budget on a stair tile the handler will reject.
        #
        # Build-338 reroute: when shrunk, ABANDON the normal tier
        # mix and target vendor first, then chests, then monsters,
        # then other beneficials. Vendor wins #1 because the bug
        # merchant stocks 2 bug weapons + 2 bug armors + 2-3 heal
        # pots (vendor.py:generate_bug_merchant_inventory) -- the
        # agent's only path to a working loadout when the
        # shrinking spell triggered via warp-forced from F6 with
        # no chance to prep. Chests come second (one holds the
        # Growth Mushroom, dungeon.py:674). Monsters third (Bug
        # Queen spawns after every bug M on the floor is cleared,
        # dropping the Growth Mushroom). The build-337 starter
        # kit (game_systems.py:_trigger_shrinking_spell) covers
        # the truly-stranded case where no V is reachable.
        passed_quest = bool(p.get("passed_bug_quest"))
        if is_shrunk:
            shrunk_beneficials = tuple(
                t for t in BENEFICIAL_SAFE if t != "C"
            )
            if passed_quest:
                # Re-shrunk veteran: the stair handlers auto-cure
                # via the Mushroom's residual power, so D/U are
                # valid targets. Put U FIRST (closer to known
                # territory) and D second so the agent heads for
                # the exit instead of fighting the floor again
                # with no fresh cure available.
                tiers = [
                    ("U",),
                    ("D",),
                    ("V",),
                    ("C",),
                    ("M",),
                    shrunk_beneficials,
                    ("T", "N"),
                ]
            else:
                tiers = [
                    ("V",),
                    ("C",),
                    ("M",),
                    shrunk_beneficials,
                    ("T", "N"),
                ]
            tiers = [tier for tier in tiers if tier]
        # Wedge-floor descent block: target floor (current_z + 1)
        # has been escaped from before via the osc 'u' valve. Strip
        # D from priority so the wayfinder doesn't route the agent
        # back onto the D tile and re-descend into the wedge. Also
        # add D to avoid_set so the random fallback skips it. Goal:
        # the agent stays on the current floor and finds a W tile
        # (warp) or Scroll of Descent to skip past the wedge.
        avoid_descent_to = set(obs.get("wedge_floors") or [])
        cur_z_for_wedge = p.get("floor", 1) - 1
        # If the agent has spent 600+ turns on this safe floor, the
        # safe floor itself is now functionally a wedge -- the food
        # / time cost of staying outweighs the risk of re-descending
        # into the previously-marked wedge. Drop the block so the
        # agent can try the wedge floor again with a fresh state
        # (more XP, more meat, possibly different fog reveals).
        # Caught on s=88 human: agent escaped F2 wedge, exhausted
        # F1 with D pointing back to F2, then re-wedged-and-escaped
        # F2 in 100T cycles for 1500+ turns before starvation.
        turns_on_floor_wedge = obs.get("turns_on_floor") or 0
        # Permanent wedge: never retry. The 600T-on-floor release
        # below only applies to ordinary wedges (where a fresh
        # exploration might open the floor up); a permanent wedge
        # is a known 1-tile region-split that won't get better.
        # Caught on s=941 dwarf F2: marked permanent at T293 but
        # the 600T release fired four times (T896, T1502, T2108)
        # to re-descend, wasting ~600T per cycle.
        perm_wedge_set = set(obs.get("permanent_wedge_floors") or [])
        is_perm_target = (cur_z_for_wedge + 1) in perm_wedge_set
        if (((cur_z_for_wedge + 1) in avoid_descent_to)
                and (turns_on_floor_wedge < 600 or is_perm_target)):
            # Also add D to BFS avoid_set so the wayfinder routes
            # AROUND the D tile instead of walking onto it
            # incidentally while targeting V / chests / frontier
            # (D is walkable terrain so BFS will path through it
            # otherwise, and stepping onto D triggers stairs_down_
            # mode which is what we're trying to avoid). Caught on
            # s=2500 human/elf F2 (1-tile region-split): without
            # this gate the agent ascended out of F2 wedge, hit F1's
            # D incidentally during exploration, descended right
            # back, looped 4800+T.
            avoid_set.add("D")
            tiers = [
                tuple(t for t in tier if t != "D")
                for tier in tiers
            ]
            tiers = [tier for tier in tiers if tier]
            avoid_set.add("D")
        # Grind-first filter: when the agent is under-levelled and the
        # floor still has reachable monsters AND they haven't met the
        # minimum kill count yet, strip D from the tiers so the
        # wayfinder targets SAFE / V / M / T / N instead. Don't shuffle
        # tier ORDER -- the agent should still grab heal pools / chests
        # / altars before walking into monsters (an earlier version
        # pushed M to the front and the agent died with full bags).
        # Skip the filter when retreat is active (retreat tiers are
        # U-focused), when is_weak (recovering, not grinding), when
        # too_long_on_floor (override -- the floor is stalled, get
        # out), and when resources are pressing.
        if (under_leveled
                and not grind_complete
                and not is_weak
                and not retreat_to_floor
                and not too_long_on_floor
                and not resources_pressing):
            tiers = [
                tuple(t for t in tier if t != "D")
                for tier in tiers
            ]
            tiers = [tier for tier in tiers if tier]
        # Legacy flat-priority alias for the adjacent-feature shortcut
        # below, which iterates a flat list of types.
        priority = tuple(t for tier in tiers for t in tier)

        # First pass: a keyed dungeon adjacent to us is the best move
        # -- bypass the priority list entirely. The keyed_dungeon_target
        # obs filters out looted dungeons, so this won't loop on a tile
        # we've already raided.
        keyed_tgt = obs.get("keyed_dungeon_target")
        if keyed_tgt and keyed_tgt["dist"] == 1:
            kdx, kdy = keyed_tgt["dx"], keyed_tgt["dy"]
            for d, (dx_d, dy_d) in (("e", (1, 0)), ("w", (-1, 0)),
                                    ("s", (0, 1)), ("n", (0, -1))):
                if (dx_d, dy_d) == (kdx, kdy):
                    return d

        best_dir, best_rank = None, len(priority)
        for d in ("n", "s", "e", "w"):
            t = neighbors.get(d)
            if t in AVOID:
                continue
            if d in blocked_guardian_dirs:
                continue
            if t in priority and not visited.get(d):
                rank = priority.index(t)
                if rank < best_rank:
                    best_dir, best_rank = d, rank
        if best_dir is not None:
            return best_dir

        # 2-tile oscillation guard: when the agent has been bouncing
        # between exactly two tiles for the last 12 frames, the BFS
        # wayfinder + anti-backtrack swap can't break out (both tiles
        # are 'recent', so the swap has no alternative to offer).
        # Force a direction whose neighbour is NOT in the
        # oscillation pair, preferring '.' / known walkable tiles
        # but accepting M (combat) when the agent is surrounded by
        # hazards -- one fight beats 400 turns ping-ponging. Caught
        # s=23 dwarf F1 (9,14) <-> (10,14) for 392 turns with 3
        # monsters adjacent the policy was avoiding while waiting
        # for vendor-repair gold to a broken armor (the is_weak
        # mask included broken armor; relaxed here to HP-only
        # because oscillation has worse EV than one fight even
        # with damaged gear). HP gate kept conservative -- a 30%-
        # HP agent shouldn't be shoved into M.
        osc = obs.get("oscillation") or {}
        oscillation_can_fight = hp_pct >= 0.50 and not immobilised
        if osc.get("detected") and oscillation_can_fight:
            pair = set(tuple(t) for t in osc.get("pair", []))
            px, py = p["x"], p["y"]
            DIRS = (("n", (0, -1)), ("s", (0, 1)),
                    ("e", (1, 0)), ("w", (-1, 0)))
            nb_now = obs.get("neighbors") or {}
            # Pass 1: a safe non-pair step (any walkable that isn't
            # M / W / # / a pair-tile).
            for d, (dx, dy) in DIRS:
                if (px + dx, py + dy) in pair:
                    continue
                t = nb_now.get(d)
                if t and t not in ("#", "M", "W"):
                    return d
            # Pass 2: accept M (engage combat). The flee gate inside
            # combat is HP-aware so a desperate agent can still flee
            # in the right direction.
            for d, (dx, dy) in DIRS:
                if (px + dx, py + dy) in pair:
                    continue
                if nb_now.get(d) == "M":
                    return d
            # Pass 3: accept W (warp). Last-resort -- random teleport
            # is better than 400 idle turns.
            for d, (dx, dy) in DIRS:
                if (px + dx, py + dy) in pair:
                    continue
                if nb_now.get(d) == "W":
                    return d
            # Truly cornered -- no non-pair direction. Fall through
            # to the wayfinder which will pick from the pair as usual.

        # Distant wayfinder via BFS first-step. Held-key dungeons jump
        # ahead of the normal priority list (guaranteed loot, the
        # key-holder monster is already dead). After that, walk through
        # the priority list and take the BFS first_step toward the
        # nearest reachable instance of each type. Reachability respects
        # walls + fog + AVOID hazards, so no more bouncing off walls or
        # walking into monsters/warps while weak.
        feature_paths = obs.get("feature_paths") or {}
        monster_path = obs.get("nearest_monster_path")
        recent_steps = set(obs.get("recent_step_set") or [])
        blocked = set(obs.get("blocked_directions") or []) | blocked_guardian_dirs

        def _swap_if_backtrack(d):
            """Anti-backtrack + anti-wall guard: swap to an alternative
            direction if `d` would re-step a recent tile OR is
            known-blocked. (Earlier attempted to also swap when
            t_main was in AVOID, but that left HP=1 retreat agents
            stuck on F1 forever -- with no alternatives the fallback
            returned `d` anyway and the AVOID check just added a
            no-op detour. Reverted.)"""
            if d not in recent_steps and d not in blocked:
                return d
            alts = []
            for alt in ("n", "s", "e", "w"):
                if alt == d:
                    continue
                if alt in recent_steps or alt in blocked:
                    continue
                t = neighbors.get(alt)
                if t in AVOID or t == "#":
                    continue
                alts.append(alt)
            if alts:
                return rng.choice(alts)
            # All non-recent / non-blocked alternatives also walls/
            # recent. Try ANY walkable that isn't blocked.
            for alt in ("n", "s", "e", "w"):
                if alt in blocked:
                    continue
                t = neighbors.get(alt)
                if t not in AVOID and t != "#":
                    return alt
            return d

        # Keyed dungeon (if any) via BFS first_step.
        if keyed_tgt and keyed_tgt.get("first_step"):
            return _swap_if_backtrack(keyed_tgt["first_step"])

        # Tier-aware distant wayfinder: within each tier, pick the
        # BFS-nearest reachable target. This is the routing fix for
        # the 47% revisit waste -- the agent now goes to the closest
        # beneficial instead of the highest-ranked-type-but-far one.
        warp_path = obs.get("nearest_warp_path")
        for tier in tiers:
            candidates = []
            for t in tier:
                if t == "M":
                    mp = monster_path
                    if (mp and mp.get("first_step")
                            and mp.get("path_dist") is not None):
                        # Trapped-engage-M (no D / no W island with a
                        # visible monster) bypasses _swap_if_backtrack
                        # for the same reason the W tier does -- the
                        # agent must traverse already-walked tiles to
                        # reach the only available threat.
                        if (trapped_no_d
                                and not obs.get("nearest_warp_path")):
                            return mp["first_step"]
                        # Tiny-pocket M-engage: in a small region
                        # (<= 10 reachable) the agent cannot reach
                        # M without re-stepping recent tiles --
                        # _swap_if_backtrack would rewrite 'n'
                        # (toward M) to 's' (away) forever. Bypass
                        # the swap when M is adjacent (dist 1) in
                        # a tiny pocket. Caught on s=8128 dwarf F3
                        # 3-tile pocket: M at (17,7) was 1 north,
                        # wayfinder picked 'n' but swap turned it
                        # 's' every other turn, n/s/n/s for 247T.
                        pocket_reach_mt = (
                            (obs.get("tile_coverage") or {}).get("reachable") or 0
                        )
                        if (pocket_reach_mt <= 10
                                and mp.get("path_dist") <= 2):
                            return mp["first_step"]
                        candidates.append((mp["path_dist"], mp["first_step"]))
                    continue
                if t == "W":
                    wp = warp_path
                    if (wp and wp.get("first_step")
                            and wp.get("path_dist") is not None):
                        # Escape from a trapped island -- the agent
                        # NEEDS to walk through already-visited
                        # tiles to reach the warp. Skip the
                        # anti-backtrack swap that would otherwise
                        # send them bouncing among the visited
                        # tiles forever (Gloin III s=99 dwarf was
                        # at the W's adjacent tile but the swap
                        # kept redirecting south->east because
                        # 's' was in recent_step_set).
                        return wp["first_step"]
                    continue
                path = feature_paths.get(t)
                if (path and path.get("first_step")
                        and path.get("path_dist") is not None):
                    candidates.append((path["path_dist"], path["first_step"]))
            if candidates:
                # When D is in avoid_set (wedge block active),
                # BFS through walkable tiles can still pick a
                # first_step that lands ON the D tile incidentally
                # (BFS treats D as walkable transit). Stepping onto
                # D triggers stairs_down_mode where the wedge step-
                # off fires another loop. Filter out candidates
                # whose first_step lands on a D neighbour so the
                # wayfinder picks the next-closest non-D path.
                # Caught on s=271 dwarf F2 D at (12,15): wayfinder
                # picked 's' (toward U via BFS path that crossed D),
                # agent walked onto D, step-off, n/s/n/s for 300+T.
                if "D" in avoid_set:
                    safe_cands = [
                        (pd, fs) for (pd, fs) in candidates
                        if neighbors.get(fs) != "D"
                    ]
                    if safe_cands:
                        candidates = safe_cands
                candidates.sort(key=lambda c: c[0])
                return _swap_if_backtrack(candidates[0][1])

        # Frontier walker via BFS. When no feature beckons, take the
        # BFS first-step toward the nearest reachable discovered tile
        # that borders the fog. Lower-right tiebreak in the obs mirrors
        # the player heuristic that D tends to be down-right of the map.
        frontier_step = obs.get("frontier_step")
        if frontier_step and frontier_step.get("first_step"):
            return _swap_if_backtrack(frontier_step["first_step"])

        # Random fallback only when the BFS has nothing reachable to
        # offer (fully-explored floor or trapped behind a fog wall).
        # Prefer an undiscovered neighbour if one happens to sit
        # adjacent so the lantern still has a chance to break through.
        # The anti-backtrack guard filters out recent tiles first so the
        # random walk doesn't immediately re-feed the oscillation.
        FEATURE_TILES = ("C", "G", "L", "O", "A", "P", "T", "N", "V")
        def _walkable(d):
            t = neighbors.get(d)
            if t in AVOID or t == "#":
                return False
            # Also exclude inferred/known guardian directions so the
            # random fallback doesn't blunder into a tomb-adjacent M.
            if d in blocked_guardian_dirs:
                return False
            return True
        def _fresh(d):
            t = neighbors.get(d)
            if t in FEATURE_TILES and visited.get(d):
                return False
            return True
        candidates = [d for d in ("n", "s", "e", "w")
                      if _walkable(d) and _fresh(d)]
        non_recent = [d for d in candidates if d not in recent_steps]
        if non_recent:
            candidates = non_recent
        else:
            # Every fresh walkable is also recent -- 2-tile oscillation
            # in a dead-end corridor. If a non-recent walkable exists
            # (typically a visited feature like a re-enterable dungeon
            # or vendor), take that to break the loop. Boromir seed=1234
            # human burned 2700 turns ping-ponging between (13,4) and
            # (14,4); the only escape was south into a visited N tile
            # that the freshness filter was excluding.
            stuck_break = [d for d in ("n", "s", "e", "w")
                           if _walkable(d) and d not in recent_steps]
            if stuck_break:
                candidates = stuck_break
        undiscovered_nbrs = [d for d in candidates if neighbors.get(d) is None]
        if undiscovered_nbrs:
            candidates = undiscovered_nbrs
        if not candidates:
            candidates = [d for d in ("n", "s", "e", "w") if _walkable(d)]
        if not candidates:
            # Truly cornered: every walkable direction is recent OR
            # the only neighbours are walls/AVOID tiles. Don't just
            # rng.choice all 4 dirs -- that picks W tiles when AVOID
            # has W (Fili of Khazad-dum dwarf seed 13 stepped onto a
            # known W via this exact path because rng landed on it
            # uniformly across all 4 dirs). Prefer non-AVOID dirs
            # even if walls -- a wall bump wastes one turn; a W
            # step wastes 200+ turns of warp + retreat. Fall through
            # to all 4 only if even the non-AVOID set is empty (no
            # tile is safer than another).
            safe_dirs = [d for d in ("n", "s", "e", "w")
                         if neighbors.get(d) not in AVOID]
            if safe_dirs:
                candidates = safe_dirs
            else:
                candidates = ["n", "s", "e", "w"]
        return rng.choice(candidates)

    if mode == "inventory":
        # If the previous action raised an exception, bail out instead of
        # retrying the same thing (e.g. a buggy use-handler would otherwise
        # spin the policy forever). The harness records last_error per step.
        if obs.get("last_error"):
            return "x"
        # Priority order: heal -> eat-meat-before-rot -> swap broken
        # gear -> equip upgrade -> eat-when-hungry -> leave. Re-checks
        # each turn so the slot number stays valid if items were
        # consumed and the inventory order shifted.
        # Sequential `if proposed is None` guards so a branch that
        # ENTERS its condition but finds no candidate (e.g. broken
        # weapon with no spare to swap to) doesn't short-circuit the
        # later steps. The previous elif-cascade left a starving agent
        # holding a broken weapon + no replacement bouncing i -> x
        # forever, even with food in the bag (seed=314 dwarf: 1738
        # consecutive turns standing on (8,11) at hunger=49 with food
        # in slot 9 -- the broken-weapon block was entered, found no
        # swap, and `elif hunger < 80 and food_slot:` was never reached).
        proposed = None
        # Growth Mushroom: highest priority while shrunk. Reverses
        # Zot's shrinking spell, re-opens stairs/warps, ends the
        # bug-level quest. Caught on s=777 human: agent picked up
        # the Mushroom from a chest at T~2000, kept it in slot 15
        # until starvation at T4357 because the cascade had no
        # gate that recognised potion_type='growth_mushroom'.
        if is_shrunk:
            for entry in inv:
                if (entry.get("category", "").startswith("potion_")
                        and entry.get("potion_type") == "growth_mushroom"):
                    proposed = f"u{entry['slot']}"
                    break
        if proposed is None and hp_pct < 0.95 and heal_pot_slot:
            proposed = f"u{heal_pot_slot}"
        if proposed is None and urgent_meat is not None:
            # Don't wait until starving -- consume the kill drop now.
            proposed = f"eat{urgent_meat}"
        # Cook raw meat with the Cooking Kit. User: 'have the player
        # cook all their meat once they have the kit. Eating cooked
        # meat is much better for survival.' No hunger gate -- cook
        # whenever raw meat exists. CookingKit.use() cooks ALL raw
        # meat in inventory in a single action.
        if proposed is None:
            has_raw_meat_iv = any(
                e["category"] == "food"
                and e.get("rot_timer") is not None
                and not e.get("is_cooked")
                for e in inv
            )
            if has_raw_meat_iv:
                for entry in inv:
                    if entry["category"] == "cooking_kit":
                        proposed = f"u{entry['slot']}"
                        break
        if (proposed is None
                and equipped.get("weapon", {})
                and equipped["weapon"].get("is_broken")
                and not cursed_weapon):
            # Find a non-broken Weapon in inventory and equip it. e<N>
            # indexes off working_items just like u<N> does. Falls
            # through to the next step if no spare exists or if the
            # current weapon is welded on (cursed_weapon).
            for entry in inv:
                if (entry["category"] == "weapon"
                        and not entry.get("is_broken")
                        and entry["name"] != equipped["weapon"]["name"]
                        and ((is_shrunk and entry.get("is_bug_gear"))
                             or (not is_shrunk and not entry.get("is_bug_gear")))):
                    proposed = f"e{entry['slot']}"
                    break
        if (proposed is None
                and equipped.get("armor", {})
                and equipped["armor"].get("is_broken")
                and not cursed_armor):
            for entry in inv:
                if (entry["category"] == "armor"
                        and not entry.get("is_broken")
                        and entry["name"] != equipped["armor"]["name"]
                        and ((is_shrunk and entry.get("is_bug_gear"))
                             or (not is_shrunk and not entry.get("is_bug_gear")))):
                    proposed = f"e{entry['slot']}"
                    break
        if proposed is None and weapon_upgrade_slot is not None:
            # Strict-bonus upgrade in the bag, equip it. The
            # _best_upgrade helper already filtered known-cursed and
            # sealed candidates.
            proposed = f"e{weapon_upgrade_slot}"
        if proposed is None and armor_upgrade_slot is not None:
            proposed = f"e{armor_upgrade_slot}"
        if proposed is None and hunger < 50 and eat_slot:
            # Threshold dropped 80 -> 50 to match the game_loop open-
            # inventory trigger above (line 2499). Rations have 50
            # nutrition, so eating at hunger >= 51 caps at 100 and
            # wastes the surplus. Starvation audit on the 5000-turn
            # grid: agents were restoring 4-8 hunger/turn (well above
            # the 1/turn decay) but still spent 50-200 turns at
            # hunger 0 -- they binge-ate at hunger 79 early (gaining
            # only 21 per Ration), exhausted the starter stash, then
            # had no food in the late-run drought. Tighter threshold
            # stretches the food window proportionally.
            proposed = f"eat{eat_slot}"
        # Read safe identified scrolls -- one-shot beneficial effects
        # the agent's been hoarding. Skip teleport (random
        # destination, could land in a dangerous spot) and descent
        # (skips the floor, defeats boon-collection). remove_curse
        # only when actually cursed. vendor_restock (Scroll of
        # Commerce) is excluded -- reading it restocks the floor's
        # vendor, which then sells MORE Scrolls of Commerce, and the
        # agent buys + reads them in an infinite buy-restock-buy
        # loop. Tauriel the elf seed=500 burned 957 turns on a
        # Commerce loop before this fix.
        SAFE_SCROLL_TYPES = {
            "mapping", "upgrade",
            "lantern_upgrade", "restoration", "foresight",
            "protection", "identify",
        }
        # spell_scroll is intentionally OMITTED here -- a Scroll of
        # Fireball cast out of combat has no target and the game now
        # refuses to consume it (items.py:1899). Leaving it in the
        # set caused a 2-turn `u<N> -> x -> u<N>` ping-pong as the
        # policy retried the scroll every inventory open. Combat-mode
        # has its own branch that reads spell_scrolls with the live
        # monster as target.
        # Equipped weapon's current upgrade level, used to gate
        # upgrade scrolls (skip a tier whose cap we've already hit
        # so the scroll isn't wasted on junk or stuck in a
        # u-then-cancel re-prompt loop).
        eq_weapon = equipped.get("weapon") or {}
        eq_weapon_upg = eq_weapon.get("upgrade_level", 0) if eq_weapon else 0
        UPG_TIER_CAPS = (
            ("Eternal", 35), ("Cosmic", 30), ("Celestial", 25),
            ("Divine", 20), ("Mythic", 17), ("Epic", 14),
            ("Superior", 10), ("Greater", 6),
        )
        def _upgrade_scroll_cap(name):
            for tag, cap in UPG_TIER_CAPS:
                if tag in (name or ""):
                    return cap
            return 3  # Basic
        if proposed is None:
            for entry in inv:
                if entry["category"] != "scroll":
                    continue
                if not entry.get("is_identified"):
                    continue
                stype = entry.get("scroll_type")
                # Hold an upgrade scroll when the equipped weapon is
                # already at this scroll's tier cap -- consuming it
                # would either error (handler keeps the scroll, the
                # policy re-prompts forever) or waste the +1 on
                # junk. Saving it for a higher-tier scroll later is
                # the patient play.
                if (stype == "upgrade"
                        and (not eq_weapon
                             or eq_weapon_upg >= _upgrade_scroll_cap(
                                 entry.get("scroll_name")))):
                    # No equipped weapon (broke or never had one) OR
                    # equipped weapon at this scroll's cap -- either
                    # way reading the scroll either errors and stays
                    # (handler doesn't consume on MAX / out-of-range)
                    # or wastes the +1 on a junk bag item. Hold for
                    # later. Caught s=941 elf F9 at 497 idle turns:
                    # broken Halberd, no equip, scroll u12 -> 1 -> c
                    # ping-ponging forever.
                    continue
                if stype in SAFE_SCROLL_TYPES:
                    proposed = f"u{entry['slot']}"
                    break
                if (stype == "remove_curse"
                        and (cursed_weapon or cursed_armor)):
                    proposed = f"u{entry['slot']}"
                    break
        # Wedge Hail Mary: when the agent has arrived at this tile
        # 6+ times AND the safer paths above produced nothing,
        # try unidentified scrolls (skip known spell_scroll and
        # vendor_restock -- both re-prompt without consuming a turn
        # so they'd lock the agent in inventory) and unidentified
        # potions. Skip any slot in wedge_attempted_actions (session
        # tracker, reset on movement) so each slot is tried at most
        # once per wedge episode. If every candidate is exhausted,
        # send 'x' to exit inventory so the wayfinder gets another
        # turn -- without this the policy falls through to whatever
        # default the inventory tail returns, which has historically
        # been u<N>-loop fodder.
        # Drink identified buff potions when HP is decent but not
        # full. The combat-buff potions (strength, defense, stone
        # skin, regeneration, etc.) are tactical effects that
        # otherwise sit in the bag until death. Drink them while
        # the agent is alive to see -- worst case the duration runs
        # out before a fight, best case it saves the next combat.
        # MUST run BEFORE the wedge Hail Mary: game_loop opens
        # inventory specifically for this drink when m_adjacent
        # and has_buff_potion, and if the wedge bail short-circuits
        # to proposed='x' first the agent loops i->x->i->x forever.
        # Dori of Belegost (s=2200 dwarf F4) burned 1800 turns at
        # full HP with a Potion of Berserker Rage in slot 8 because
        # the wedge bail consumed `proposed` before the buff-drink
        # gate could fire.
        HELPFUL_POTION_TYPES = {
            "strength", "defense", "stone_skin", "regeneration",
            "berserker", "giant_strength", "haste", "vampirism",
            "dexterity", "intelligence", "frost_armor",
            "true_sight", "invisibility", "fortune", "experience",
        }
        if proposed is None and hp_pct < 0.95:
            for entry in inv:
                if not entry["category"].startswith("potion_"):
                    continue
                if not entry.get("is_identified"):
                    continue
                if entry.get("potion_type") in HELPFUL_POTION_TYPES:
                    proposed = f"u{entry['slot']}"
                    break
        current_tile_visits_iv = obs.get("current_tile_visits") or 0
        wedged_iv = current_tile_visits_iv >= 6
        wedge_attempted = (
            set(obs.get("wedge_attempted_actions") or [])
            | set(obs.get("wedge_tried_this_floor") or [])
        )
        WEDGE_SKIP_SCROLL_TYPES = {"spell_scroll", "vendor_restock"}
        if proposed is None and wedged_iv:
            for entry in inv:
                if entry["category"] != "scroll":
                    continue
                stype = entry.get("scroll_type")
                if entry.get("is_identified") and stype in WEDGE_SKIP_SCROLL_TYPES:
                    continue
                # An identified upgrade scroll at cap won't consume
                # itself -- it just re-prompts. Excluding it here
                # closes the wedge re-entry path that previously
                # spun s=941 elf 60+ times around the same scroll.
                if (entry.get("is_identified") and stype == "upgrade"
                        and eq_weapon
                        and eq_weapon_upg >= _upgrade_scroll_cap(
                            entry.get("scroll_name"))):
                    continue
                candidate = f"u{entry['slot']}"
                if candidate in wedge_attempted:
                    continue
                proposed = candidate
                break
        if proposed is None and wedged_iv:
            for entry in inv:
                if not entry["category"].startswith("potion"):
                    continue
                if entry.get("is_identified"):
                    continue
                candidate = f"u{entry['slot']}"
                if candidate in wedge_attempted:
                    continue
                proposed = candidate
                break
        if proposed is None and wedged_iv:
            # All escape items exhausted -- back out of inventory so
            # the game_loop wayfinder gets the next turn. The
            # game_loop wedge trigger is gated on last_action not in
            # ("i", "x"), which blocks immediate re-open. Combined
            # with the per-floor wedge_attempted_actions set, this
            # prevents the inventory loop entirely.
            proposed = "x"
        # Cure-all (Antidote) gets its own gate -- only drink when
        # actually statused, otherwise it sits as insurance for the
        # next nasty effect. has_bad_status is hoisted at the top of
        # smart_policy.
        if proposed is None and has_bad_status:
            for entry in inv:
                if (entry.get("category", "").startswith("potion_")
                        and entry.get("is_identified")
                        and entry.get("potion_type") == "cure_all"):
                    proposed = f"u{entry['slot']}"
                    break
        if proposed is None:
            return "x"
        # Anti-stuck guard: if the last action was the same as what we're
        # about to send and we're still in inventory mode, the handler is
        # silently rejecting it (e.g. a slot-mismatch logging "Invalid
        # item number" but not advancing state). Bail rather than spin --
        # the playtester caught this pattern with `eat3` looping when the
        # food was in edible-list slot 1.
        if obs.get("last_action") == proposed:
            return "x"
        return proposed

    if mode == "combat_mode":
        # Threat assessment: monster_too_tough = monster level >
        # player level + 1, OR monster max_hp > 1.5x player max_hp,
        # OR monster is undead at any level >= player level. The F4
        # audit caught 5 Lv2 agents dying to Lv3-4 UNDEAD WRAITHs
        # because the old threshold (level > pc+2) had them fighting
        # those at parity. Wraiths hit for 15-25 raw, so even a flee-
        # capable agent burns 1-2 hits worth of HP per engagement;
        # tighten to flee earlier. The undead check uses obs.monster's
        # name; we don't have a type field but the name contains
        # "wraith/lich/skeleton/vampire/ghost/zombie/spectral".
        m = obs.get("monster") or {}
        m_level = m.get("level") or 0
        m_max_hp = m.get("max_hp") or 0
        m_is_edible = m.get("is_edible", True)
        m_name_low = (m.get("name") or "").lower()
        pc_level = p.get("level") or 1
        # Reuse the module-level token list; obs.monster.is_undead is
        # already set by _monster_obs, but we recompute here so the
        # combat threat assessment is self-contained.
        is_undead = bool(m.get("is_undead") or _is_undead_name(m_name_low))
        # ELITE undead are the tomb-elite guardians spawned at
        # floor+1 with 1.3x stats and 3x gold (see game_systems.py's
        # undead_guardian branch). At parity level they hit harder
        # and tank more than a regular Lv-equal undead, so the
        # threat assessment treats them as one tier above where
        # they'd otherwise sit. Without this, Gloin Axebreaker the
        # dwarf at Lv7 vs an ELITE UNDEAD DRAGON LICH (Lv7) chose
        # 'a' (attack) instead of 'f' (flee) and lost the trade
        # 13 dmg vs 19 dmg per round, dying in three rounds.
        is_elite_undead = is_undead and "elite" in m_name_low
        # Three-band threat assessment:
        #  * general monsters: flee at m_level > pc.level + 2.
        #  * regular undead (wraith/lich/skeleton/etc.): flee at
        #    m_level > pc.level (one tier earlier than general).
        #  * ELITE undead: flee at m_level >= pc.level (parity is
        #    already too dangerous given the 1.3x stat multiplier).
        # max_hp gate (m_max_hp > 2x pc_max_hp) catches HP-bag bosses.
        monster_too_tough = (
            m_level > pc_level + 2
            or m_max_hp > 2 * p["max_hp"]
            or (is_undead and m_level > pc_level)
            or (is_elite_undead and m_level >= pc_level)
        )
        # Starving + inedible monster: flee. Prior playtest showed
        # 39 starvation-override engagements, only 2 produced meat
        # because the agent kept fighting Wraiths/Liches/Lichen with
        # no meat return. Now we abort those fights immediately and
        # keep looking for an edible target.
        if starving and not m_is_edible:
            return "f"
        # Drink a healing potion mid-fight as a last resort.
        if hp_pct < 0.50 and heal_pot_slot and not heal_spell_slot:
            return "i"  # opens inventory; in_combat filter shows usables
        # Mid-fight heal: queue a cast at HP < 55%.
        if hp_pct < 0.55 and heal_spell_slot:
            return "c"
        # Ticking-status flee: poison / burn / DoT / life_drain
        # ticks every round, and the monster's adding hits on top.
        # Break off, let the duration tick down out of combat,
        # re-engage when clean. Stat-debuff statuses (weakness,
        # defense_penalty, blindness, confusion, sticky_hands) are
        # NOT in this gate -- fleeing wastes turns the debuff would
        # have ticked through anyway, and the monster is usually
        # still there when the debuff wears off. Skip the flee when
        # immobilised (move refused) and when starving + edible-
        # monster (we need this kill to eat).
        # Tiny-pocket exception: in a small reachable region (<=
        # 10 tiles) fleeing from a status effect just re-encounters
        # the same M next move -- the status ticks AND the flee
        # parting blow lands AND the M is back. Commit to combat
        # instead. Caught on s=1234 dwarf F1: 4-tile pocket, M
        # south of D with a poison special; agent's a/f cycle
        # drained HP without producing a kill.
        pocket_reach = (obs.get("tile_coverage") or {}).get("reachable") or 0
        in_tiny_pocket = pocket_reach <= 10
        if (has_ticking_status and not immobilised
                and not (starving and m_is_edible)
                and not in_tiny_pocket):
            return "f"
        # Low-HP last-ditch flee: HP < 30%, no healing options at all,
        # not starving. Better to disengage and look for a vendor /
        # altar / pool than die on the next swing. Prior policy
        # silently kept attacking and lost most of these fights.
        # SHRUNK exception: on a sealed bug-level floor there is no
        # 'find a vendor' option -- stairs refuse, warps refuse,
        # the agent bounces flee->re-engage->flee in the same 3
        # tiles forever. s=317 human F8 burned 1500T cycling
        # combat (low HP) -> flee -> walk back -> combat. Commit
        # to the fight instead.
        # Tiny-pocket exception (same as the ticking-status gate):
        # with no D / no W reachable and a tiny reachable region,
        # fleeing just re-encounters the same M next move forever
        # while the food clock drains. Commit to combat (die
        # fighting at depth beats a 500T flee->re-engage loop).
        # Caught on s=8128 dwarf F3: 3-tile pocket, M north, agent
        # fled 247T against a too-tough Tomb Guardian instead of
        # engaging it or accepting the early-term.
        pocket_reach_cb = (obs.get("tile_coverage") or {}).get("reachable") or 0
        no_escape_pocket = (
            pocket_reach_cb <= 10
            and not (obs.get("feature_paths") or {}).get("D")
            and not obs.get("nearest_warp_path")
        )
        if (hp_pct < 0.30
                and not heal_pot_slot
                and not heal_spell_slot
                and not starving
                and not is_shrunk
                and not no_escape_pocket):
            return "f"
        # Threat-flee only when NOT starving -- a starving agent vs
        # an edible monster needs to win this fight to live. Same
        # shrunk + tiny-pocket exception: with no escape route,
        # fleeing just postpones the same fight.
        if (monster_too_tough and not starving and not is_shrunk
                and not no_escape_pocket):
            return "f"
        # Damage spells beat melee: more damage per turn, no weapon
        # durability loss, scale with INT for casters. Mana regens at
        # 1/5 moves so casting freely between fights is sustainable.
        # Bumped 0.65 -> 0.90 to actually USE the spells the agent
        # buys (Scroll of Fireball etc.) instead of saving mana for
        # an emergency that never comes.
        if affordable_dmg and rng.random() < 0.90:
            return "c"
        return "a" if rng.random() < 0.92 else "f"

    if mode == "identify_scroll_mode":
        # Scroll of Identify opened a sub-mode listing unidentified
        # items (1..N) or 'c' to cancel. Cancel doesn't consume the
        # scroll, so the agent loops `i -> u<scroll> -> back -> i`
        # forever; Eowyn the human seed=5678 burned 1244 turns on
        # this. Always pick '1' (first unidentified item) so the
        # scroll consumes. If there's nothing to identify the
        # handler returns to inventory on its own.
        return "1"

    if mode == "upgrade_scroll_mode":
        # Pick the equipped weapon by its position in the gear-only
        # filtered view of the bag. After build-316, the scroll
        # handler iterates get_sorted_inventory filtered to Weapon |
        # Armor (items.py:2115), the same order obs.inventory uses,
        # so we can mirror it cleanly here. Before the fix the menu
        # ran in raw insertion order, so smart_policy's '1' upgraded
        # whichever piece of junk landed in the bag first --
        # playtester audit on s=1 dwarf showed 9 scrolls consumed
        # and the equipped Halberd ended +0 upg.
        #
        # Scroll-tier cap: each tier maxes the upgrade level it can
        # push to (Basic +3, Greater +6, Superior +10, Epic +14,
        # Mythic +17, Divine +20, Celestial +25, Cosmic +30, Eternal
        # +35). If the equipped weapon is already at the cap for
        # THIS scroll, the handler rejects without consuming the
        # scroll. Cancel rather than fall through to a junk slot --
        # save the scroll for a stronger upgrade scroll later.
        scroll_name = obs.get("active_scroll_item") or ""
        tier_caps = (
            ("Eternal", 35), ("Cosmic", 30), ("Celestial", 25),
            ("Divine", 20), ("Mythic", 17), ("Epic", 14),
            ("Superior", 10), ("Greater", 6),
        )
        scroll_cap = 3  # Basic
        for tag, cap in tier_caps:
            if tag in scroll_name:
                scroll_cap = cap
                break
        last_us = obs.get("last_action") or ""
        # If we just picked a slot but the mode persisted, the handler
        # rejected the choice (MAX-upgrade or out-of-range -- neither
        # consumes the scroll). Cancel rather than walk junk slots.
        if last_us and last_us.isdigit():
            return "c"
        # Collect BOTH equipped weapon and armor slots. Earlier policy
        # always picked weapon when both were equipped, so an agent
        # with 6 scrolls and a Longsword + Splint Armor ended up with
        # 2 weapon upgrades and 0 armor upgrades (s=857 human
        # Erkenbrand the Tall: weapon got 2 upgrades, armor got 0).
        # Round-robin instead: pick whichever piece has the lower
        # upgrade level so both gear slots scale together. Weapon
        # wins ties because attack scales kill speed (which
        # compresses every other survival metric) more than armor
        # soak does -- but only by a tiebreak, not as a hard rule.
        #
        # NB: in upgrade_scroll_mode the harness still applies the
        # 'use' inventory filter, so obs.inventory hides Weapon/Armor
        # entries entirely. We can't walk it for the gear index here
        # -- pull the equipped_*_gear_idx fields off obs.player.equipped
        # instead (computed off the unfiltered sorted view).
        eq_weapon_idx = equipped.get("weapon_gear_idx")
        eq_armor_idx = equipped.get("armor_gear_idx")
        eq_weapon_upg = (equipped.get("weapon") or {}).get("upgrade_level", 0)
        eq_armor_upg = (equipped.get("armor") or {}).get("upgrade_level", 0)
        # Decide which slot to upgrade. Skip a slot whose item is
        # already at the scroll's cap (the handler keeps the scroll
        # but errors silently). If both at cap, cancel and save the
        # scroll for a stronger tier.
        wpn_eligible = eq_weapon_idx is not None and eq_weapon_upg < scroll_cap
        arm_eligible = eq_armor_idx is not None and eq_armor_upg < scroll_cap
        if not wpn_eligible and not arm_eligible:
            return "c"
        # Routing rule: weapon priority by default (attack scales
        # kill speed, which compresses every other survival metric)
        # but let armor catch up when it's lagging by 2+ levels.
        # On a 6-scroll budget that produces roughly a 4 weapon /
        # 2 armor split, which mirrors the user's intuition that
        # the equipped armor should also be getting some upgrades.
        ARMOR_CATCHUP_GAP = 2
        chosen_idx = None
        if wpn_eligible and arm_eligible:
            if eq_weapon_upg - eq_armor_upg >= ARMOR_CATCHUP_GAP:
                chosen_idx = eq_armor_idx
            else:
                chosen_idx = eq_weapon_idx
        elif wpn_eligible:
            chosen_idx = eq_weapon_idx
        else:
            chosen_idx = eq_armor_idx
        if chosen_idx is not None and chosen_idx <= 9:
            return str(chosen_idx)
        return "1"

    if mode == "foresight_direction_mode":
        # Scroll of Foresight reveals 3 rows/cols toward n/s/e/w.
        # The handler only accepts n/s/e/w/c -- anything else
        # (including the catch-all 'back') just re-prompts. Eowyn
        # seed=7 burned 682 turns looping `i -> u<scroll> -> back`
        # because the policy fell into the default and returned
        # 'back'. Pick a direction biased away from the wall the
        # player is closest to so we maximise new map revealed.
        neighbors = obs.get("neighbors") or {}
        unseen = {}
        for d in ("n", "s", "e", "w"):
            t = neighbors.get(d)
            unseen[d] = 1 if t is None else 0
        for d in ("n", "s", "e", "w"):
            if unseen[d]:
                return d
        return rng.choice(["n", "s", "e", "w"])

    if mode == "flee_direction_mode":
        # Pick a walkable direction to actually flee. Without this
        # the policy fell into the catch-all and returned 'back',
        # which the harness mapped to game_loop while leaving the
        # player on the monster's tile -- Finrod the elf took
        # consecutive 24-dmg Wraith hits between failed flees.
        # Prefer non-recent SAFE (non-hazard) walkable directions
        # so the agent doesn't flee back through the same tile that
        # just spawned the fight AND doesn't trade combat for a
        # warp / second monster. Fall back to 'c' (cancel flee and
        # stand to fight) if no walkable direction exists.
        # User-flagged: 28 of the first-warp triggers across the
        # 159-seed grid came from flee_direction_mode -- the agent
        # bolted from one M into a W next door.
        neighbors = obs.get("neighbors") or {}
        recent = set(obs.get("recent_step_set") or [])
        HAZARD = ("M", "W")
        # Pass 1: non-recent, non-hazard, non-wall.
        for d in ("n", "s", "e", "w"):
            if d in recent:
                continue
            t = neighbors.get(d)
            if t and t not in HAZARD and t != "#":
                return d
        # Pass 2: drop the recent filter but keep hazard avoidance.
        for d in ("n", "s", "e", "w"):
            t = neighbors.get(d)
            if t and t not in HAZARD and t != "#":
                return d
        # Pass 3: any non-wall direction (including hazards). A
        # warp landing or a fresh monster fight is still better
        # than another round against the current attacker.
        for d in ("n", "s", "e", "w"):
            t = neighbors.get(d)
            if t not in ("#", None):
                return d
        return "c"  # cornered; fight back

    if mode == "spell_casting_mode":
        if hp_pct < 0.55 and heal_spell_slot:
            return str(heal_spell_slot)
        if affordable_dmg:
            return str(rng.choice(affordable_dmg)["slot"])
        if affordable_spells:
            return str(rng.choice(affordable_spells)["slot"])
        return "x"

    if mode == "vendor_shop":
        vendor_inv = obs.get("vendor_inventory") or []
        gold = p["gold"]

        # 1) Repair damaged gear first while we have a vendor. The repair
        # command 'r<N>' indexes off the whole sorted inventory (NOT a
        # filtered damaged-only list), so we pass the inventory slot of
        # any worn / broken gear. Equipped weapon + armor also appear in
        # inventory.items, so they show up in obs.inventory like normal.
        for entry in inv:
            if entry["category"] not in ("weapon", "armor"):
                continue
            dur = entry.get("durability")
            mx = entry.get("max_durability")
            if not (dur and mx) or dur >= mx:
                continue
            broken = entry.get("is_broken")
            pct = (dur / mx) if mx else 1.0
            if broken or pct < 0.40:
                # Skip if we've just tried it (silent reject ->
                # stuck loop, same anti-stuck pattern as inventory).
                proposed = f"r{entry['slot']}"
                if obs.get("last_action") != proposed:
                    return proposed

        # 2) Stockpile: keep at least a few uses of each survival staple.
        # Sum item counts (not stack rows) so a single stack of 5 potions
        # still counts as 5 and the policy doesn't over-buy. Lantern Fuel
        # only counts as a stockpile target if the agent is actually using
        # the lantern -- otherwise it's gold wasted on a vanity item.
        # Food bumped 2 -> 5 after a playtest pass showed 7/30 runs
        # ending in slow-motion starvation pinning (HP=1, hunger=0,
        # 1500+ turns alive but doomed). 2 Rations stacks of 3 each = 6
        # nutrition uses, not enough for runs past floor 3.
        # Food target 5 -> 8 after the post-fix playtest: 8/30 runs
        # still died at hunger=0 because the override couldn't
        # consistently produce meat (5.1% conversion in fights). Buy
        # harder to never get to the override stage.
        # Stockpile targets. Each vendor visit tops these up so the
        # agent keeps buying every floor's vendor stock until the
        # quota is full -- preventing the "only bought F4-F5" pattern
        # where a player starves on F7 after the starter pack runs
        # out. User-flagged after Thorin of Belegost (dwarf seed
        # 1234): purchased only on F4 + F5, then starved into a warp
        # surrender on F7 with no rations left.
        # - food: 25 (was 15). 25 Rations = 1000 nutrition uses,
        #   enough for ~1000 turns of comfort eating between meat
        #   kills. The starter pack ships only 5 so the agent needs
        #   most floors' vendors to fill.
        # - potion_healing: 6 (was 4) -- one extra emergency per
        #   deep floor pushes survival.
        # - potion_mana: 3 (held).
        STOCK = {"potion_healing": 6, "food": 25, "potion_mana": 3}
        # Lantern fuel stockpile. Bumped trigger 20 -> 30 and target
        # 2 -> 4 so the more-aggressive lantern policy doesn't run
        # dry mid-floor. Four canisters = 40 fires; combined with the
        # base fuel that's ~70 fires per vendor visit -- enough to
        # lantern every fog-adjacent step for 7-8 floors.
        # Fuel buys: trigger any time fuel < 45, target 6 canisters.
        # With the every-fog-step lantern policy, fuel drains ~1 per
        # 3-4 moves. Six canisters = 60 fires, base 50 starter,
        # ~110 fires per vendor visit which covers 8-10 floors of
        # aggressive lantern use. Bumped from 4 canisters/trigger
        # 30 because Fili of Khazad-dum hit fuel=0 between vendor
        # visits and stepped blind into a W.
        if use_lantern and lantern_fuel < 45:
            STOCK["lantern_fuel"] = 6

        # COOKING KIT FIRST: a one-time purchase that quadruples meat
        # nutrition for the rest of the run AND auto-cooks the entire
        # raw-meat backlog in a single 'use' action. Without it the
        # food economy relies entirely on rations and uncooked-meat
        # spoilage windows -- 67% of the 160-seed grid died of
        # starvation before the vendor.py stock fix exposed kits to
        # the dungeon vendor inventory. Skip if already owned (kit
        # is permanent, no need to stockpile).
        has_kit = any(i["category"] == "cooking_kit" for i in inv)
        if not has_kit:
            for v in vendor_inv:
                if v["category"] == "cooking_kit" and v["price"] <= gold:
                    return f"b{v['slot']}"

        # RATIONS FIRST: buy EVERY ration the vendor offers, before
        # any other stockpile or magic-item check. User framing:
        # "Buying all rations from every vendor on every floor
        # should be a very high priority. It's pretty much top of
        # the explorer priority list." Rations are cheap (10g
        # apiece) and starvation is the silent floor-7 killer; the
        # STOCK["food"] cap was leaving deficit on long runs.
        # Vendor stocks 3-4 rations as a single stack -- one 'b' click
        # buys the stack at floor-tier value (the vendor's
        # calculated_value field).
        for v in vendor_inv:
            if v["category"] == "food" and v["price"] <= gold:
                return f"b{v['slot']}"

        owned = {cat: sum(i.get("count", 1) for i in inv
                          if i["category"] == cat)
                 for cat in STOCK}
        for v in vendor_inv:
            if v["price"] > gold:
                continue
            cat = v["category"]
            if cat in STOCK and owned.get(cat, 0) < STOCK[cat]:
                return f"b{v['slot']}"

        # 2.5) Magical / utility items the agent should keep one or two
        # of around: stat-buff potions are pre-combat insurance
        # (Strength Elixir / Defense Brew / Stone Skin / Regeneration
        # / Berserker Rage / Giant's Might / Haste / Vampiric Elixir),
        # scrolls are the high-EV grab bag (mapping reveals the floor,
        # upgrade buffs equipment, remove_curse breaks welds, spell
        # scrolls teach new spells). Buy one of each unknown
        # potion_<type> beyond healing/mana, and up to 3 scrolls. Keep
        # a 150g cushion for emergency healing-pot restock at the next
        # vendor.
        MAGIC_RESERVE = 150
        # Scroll cap bumped 3 -> 5. Upgrade scrolls in particular are
        # the only melee-scaling lever for non-caster races; capping
        # at 3 meant agents stopped buying after one or two vendors
        # and walked past later vendors' guaranteed upgrade scroll.
        # Five lets the agent keep stocking upgrade scrolls through
        # mid-game vendors so the weapon attack_bonus actually
        # scales with depth.
        SCROLL_BUY_CAP = 5
        owned_scrolls = sum(1 for i in inv if i["category"] == "scroll")
        owned_buff_potion_types = {
            i["category"] for i in inv
            if i["category"].startswith("potion_")
            and i["category"] not in ("potion_healing", "potion_mana")
        }
        # First pass: prefer upgrade scrolls over any other scroll
        # type. For non-caster races (dwarf, human) the upgrade
        # scroll is the only weapon-power scaling lever they have --
        # +1 attack_bonus per scroll, no level / int requirement,
        # consumed via the new upgrade_scroll_mode dispatch. A
        # generic scroll grab-bag mixes upgrades with identify /
        # mapping / restoration, so the agent randomly skipped half
        # the upgrades. Now we buy upgrades FIRST, fill remaining
        # scroll slots with whatever else is on offer.
        for v in vendor_inv:
            if v["price"] > gold - MAGIC_RESERVE:
                continue
            cat = v["category"]
            if (cat == "scroll"
                    and v.get("scroll_type") == "upgrade"
                    and owned_scrolls < SCROLL_BUY_CAP):
                return f"b{v['slot']}"
        for v in vendor_inv:
            if v["price"] > gold - MAGIC_RESERVE:
                continue
            cat = v["category"]
            if cat == "scroll" and owned_scrolls < SCROLL_BUY_CAP:
                return f"b{v['slot']}"
            if (cat.startswith("potion_")
                    and cat not in ("potion_healing", "potion_mana", "potion")
                    and cat not in owned_buff_potion_types):
                return f"b{v['slot']}"

        # 3) Replacement gear: if our equipped weapon or armor is broken
        # (durability hit 0 -- repair won't fix without cost we may not
        # afford), buy a like-category replacement and trust the vendor's
        # buy flow to leave it in our inventory for manual equip later.
        if equipped.get("weapon", {}) and equipped["weapon"].get("is_broken"):
            for v in vendor_inv:
                if v["category"] == "weapon" and v["price"] <= gold:
                    return f"b{v['slot']}"
        if equipped.get("armor", {}) and equipped["armor"].get("is_broken"):
            for v in vendor_inv:
                if v["category"] == "armor" and v["price"] <= gold:
                    return f"b{v['slot']}"

        # 4) Equipment UPGRADES from the vendor. The biggest combat-
        # balance gap surfaced by the F4 death cliff: vendors stock
        # weapons (Longsword atk+10, Mace +6, Morningstar +8) and
        # armor (Ring Mail def+4, Chainmail +6) that BLOW AWAY the
        # starter Dagger / Leather Armor, but the policy was buying
        # only stockpile items and walking past the upgrades. Now we
        # scan vendor weapons / armor and buy any strict-bonus
        # improvement we can afford, after keeping a healing-pot
        # reserve. Skip known-cursed and sealed items -- can't be
        # repaired and weld to hand on equip.
        UPGRADE_RESERVE = 150  # keep this much for next vendor's potions
        cur_w_bonus = (equipped.get("weapon") or {}).get("attack_bonus") or 0
        cur_a_bonus = (equipped.get("armor") or {}).get("defense_bonus") or 0
        for v in vendor_inv:
            if v["category"] not in ("weapon", "armor"):
                continue
            if v["price"] > gold - UPGRADE_RESERVE:
                continue
            if v.get("is_broken") or v.get("is_sealed"):
                continue
            if v.get("buc_known") and v.get("buc_status") == "cursed":
                continue
            if v["category"] == "weapon":
                if (v.get("attack_bonus") or 0) > cur_w_bonus:
                    return f"b{v['slot']}"
            else:  # armor
                if (v.get("defense_bonus") or 0) > cur_a_bonus:
                    return f"b{v['slot']}"

        # 5) Identify unknown scrolls + potions. Upgrade scrolls are the
        # high-value drop the user explicitly called out -- you can't
        # use one without knowing what it is, and the vendor identify
        # cost (25g per L0 item, scaled by level) is small relative to
        # the upside. Equipment identify costs 2x and gives less
        # actionable info, so skip weapons/armor here -- they get
        # identified by use anyway after EQUIPMENT_ID_THRESHOLD uses.
        # Leave a 100g cushion so we don't spend our healing potion
        # money on consultations.
        IDENT_BUDGET_FLOOR = 100
        # Identify cost = 25 * (item.level + 1) for scrolls/potions
        # (items.py:296). We don't have item.level in obs, so assume
        # the cheapest case (25g) -- the handler aborts on insufficient
        # gold anyway so a too-aggressive request is harmless.
        IDENT_GUESS_COST = 25
        if gold >= IDENT_BUDGET_FLOOR + IDENT_GUESS_COST:
            IDENT_TARGETS = ("scroll", "spell")
            for entry in inv:
                if entry.get("is_identified"):
                    continue
                cat = entry["category"]
                # Scrolls + spells = high-info identifies (the agent
                # can't safely use them blind). Potions are still
                # high-value but the policy auto-drinks any healing
                # potion it sees, so paying for ID is less critical.
                # Skip weapon/armor: 2x cost, learned by use anyway.
                if cat not in IDENT_TARGETS and not cat.startswith("potion"):
                    continue
                proposed = f"id{entry['slot']}"
                if obs.get("last_action") != proposed:
                    return proposed

        return "x"

    if mode == "chest_mode":
        # Chests can explode for 30-48 raw damage. The death dossier
        # showed Lv4-5 agents getting one-shot by chest explosions
        # at low HP with no heal pot in the bag -- a narrow safety
        # net for those runs. When HP is critical AND heal pots are
        # exhausted, walk away from the chest instead of gambling.
        # CHEST GAME BUG: the chest handler doesn't accept 'l' as a
        # leave command (only o / i / n / s / e / w); sending 'l'
        # logs "Invalid command" and stays in chest_mode, looping
        # forever. Walk away via cardinal move instead. If ALL 4
        # neighbours are walls (Cirdan elf seed=2200 was warp-landed
        # on a chest with walls on all sides and burned 2815 turns
        # sending `n` into the wall), open the chest as a last
        # resort -- a 30-50 dmg gamble beats an infinite loop.
        neighbors = obs.get("neighbors") or {}
        blocked = set(obs.get("blocked_directions") or [])
        recent_steps_chest = set(obs.get("recent_step_set") or [])
        def _walk_off_chest():
            # Prefer non-recent, non-blocked, non-wall, NON-HAZARD
            # directions first. Without the hazard filter the agent
            # was walking off chests onto adjacent W (warp) tiles --
            # 13 first-warp triggers across the 159-seed grid came
            # from chest_mode. Walls vs hazards swap is intentional:
            # bumping a wall wastes 1 turn, stepping on W wastes
            # 100-200T of warp recovery.
            # Also avoid bouncing between two adjacent chest tiles
            # forever (Thranduil seed 9001 burned 2720 turns at
            # HP=1 oscillating n/s between two stacked chests).
            HAZARD_OFF = ("M", "W")
            for d in ("n", "s", "e", "w"):
                if d in blocked or d in recent_steps_chest:
                    continue
                t = neighbors.get(d)
                if t and t not in HAZARD_OFF and t != "#":
                    return d
            # Drop recent filter, keep hazard + wall filter.
            for d in ("n", "s", "e", "w"):
                if d in blocked:
                    continue
                t = neighbors.get(d)
                if t and t not in HAZARD_OFF and t != "#":
                    return d
            # Last resort: any non-blocked non-wall direction
            # (accepts hazards rather than oscillating off-chest
            # forever).
            for d in ("n", "s", "e", "w"):
                if d in blocked:
                    continue
                t = neighbors.get(d)
                if t != "#":
                    return d
            return "o"  # walled in; open the chest and hope
        if p["hp"] < 40 and heal_pot_slot is None:
            return _walk_off_chest()
        return "o" if rng.random() < 0.85 else _walk_off_chest()
    if mode == "stairs_down_mode":
        # Shrunk on a bug level: Zot's spell blocks descent ('You peer
        # over the edge but the drop is lethal at your size!') and the
        # handler stays in stairs_down_mode. Without this gate the
        # policy mashes 'd' forever -- caught as status=stuck on
        # s=461 elf F8 (176+ turns at HP 42/78). Walk off the D tile
        # so the wayfinder can route to the Bug Queen / Growth
        # Mushroom in game_loop. Same gate guards stairs_up_mode below.
        # Exception: a quest-passed re-shrunk player CAN descend --
        # the stair handler auto-cures them via the Mushroom's
        # residual power and they emerge normal-sized on the next
        # floor (game_systems._restore_size_on_bug_exit).
        if p.get("is_shrunk") and not p.get("passed_bug_quest"):
            neighbors = obs.get("neighbors") or {}
            for d in ("n", "s", "e", "w"):
                t = neighbors.get(d)
                if t and t not in ("#", "M", "W"):
                    return d
            for d in ("n", "s", "e", "w"):
                if neighbors.get(d) not in ("#", None):
                    return d
            return rng.choice(["n", "s", "e", "w"])
        # Refuse to re-descend into a floor we already had to escape
        # from via the stairs_up osc-valve. Target z = current z + 1
        # (going down). If that z is in wedge_floors, the agent
        # descended once, hit a 2-tile region-split, ascended, and
        # would just bounce right back without this gate. Step off
        # the D tile instead so the wayfinder can keep exploring the
        # current floor (find a W, level up, find Scroll of Descent
        # to skip the wedge floor entirely). Caught on s=88 human
        # F2 (1,1)U <-> (1,2).
        avoid_descent_to = set(obs.get("wedge_floors") or [])
        cur_z = (p.get("floor", 1) - 1)
        # 600T-on-floor escape: if the supposedly-safe floor has
        # also become a wedge (agent stuck here too long), drop
        # the block and let normal descent fire. Mirrors the
        # game_loop gate above. EXCEPTION: permanent wedge never
        # releases -- s=941 dwarf F2 cycled 4 times at 600T
        # intervals before this gate.
        turns_on_floor_wedge = obs.get("turns_on_floor") or 0
        perm_wedge_sd = set(obs.get("permanent_wedge_floors") or [])
        is_perm_sd = (cur_z + 1) in perm_wedge_sd
        if ((cur_z + 1) in avoid_descent_to
                and (turns_on_floor_wedge < 600 or is_perm_sd)):
            neighbors = obs.get("neighbors") or {}
            # Direction toward the nearest warp -- if the agent has
            # a W reachable, walking off D in the warp's direction
            # makes progress instead of bouncing onto T/M.
            warp_path = obs.get("nearest_warp_path") or {}
            warp_dir = warp_path.get("first_step")
            # Prefer the warp direction first if it's a clean step
            # (non-wall non-hazard non-D non-T). Caught on s=941
            # dwarf F1 D at (17,14): step-off picked 'n' (toward
            # T tile) by iteration order, but W was 9 steps south.
            # Walking north spawned a 3-tile bounce loop instead
            # of routing toward escape.
            STEP_OFF_SKIP = ("#", "M", "W", "D", "T")
            # Warp-dir-preferred set: step toward W is the goal,
            # AND tomb (T) tiles are passable (combat-risky but
            # navigable -- the wayfinder routes through them).
            # Caught on s=1234 dwarf F3 D at (1,5) with W south
            # at path_dist=9 PAST a T at (1,6): step-off skipped
            # 's' (T neighbour), walked 'n' away from W, looped
            # n/s for 477T. Allow T as a valid warp-dir step.
            WARP_DIR_SKIP = ("#", "M", "D")
            if warp_dir:
                t = neighbors.get(warp_dir)
                if t == "W" and (warp_path.get("path_dist") or 99) == 1:
                    return warp_dir
                if t and t not in WARP_DIR_SKIP:
                    return warp_dir
            for d in ("n", "s", "e", "w"):
                t = neighbors.get(d)
                if t and t not in STEP_OFF_SKIP:
                    return d
            # No clean step-off: take any non-wall non-hazard non-D.
            for d in ("n", "s", "e", "w"):
                t = neighbors.get(d)
                if t and t not in ("#", "D"):
                    return d
            # All four cardinals are fog (None) or walls -- the agent
            # arrived on this D via warp / direct stair landing and
            # hasn't seen any neighbour yet. Step BLINDLY into a
            # fog direction so reveal_adjacent_walls uncovers a
            # walkable tile. Anything is better than re-descending
            # into a known-permanent wedge. Caught on s=7 elf F2 D
            # at (8,10) with all None neighbours, descending every
            # turn to F3 (1,1) and immediately ascending back.
            unknown_dirs = [d for d in ("n", "s", "e", "w")
                            if neighbors.get(d) is None]
            if unknown_dirs:
                return rng.choice(unknown_dirs)
            # Truly cornered (only D in non-wall neighbours). Fall
            # through to the normal descent logic -- we tried.
        # Retreat-after-warp: if a warp landed us on a floor deeper
        # than max_z_via_stairs, we DON'T want to descend further --
        # we want to walk off this D tile and find the U tile so we
        # can ascend back to known territory. The wayfinder is
        # already targeting U in retreat mode, so steer toward it.
        feature_paths = obs.get("feature_paths") or {}
        if obs.get("retreat_to_floor") is not None:
            u_path = feature_paths.get("U")
            if u_path and u_path.get("first_step"):
                return u_path["first_step"]
            neighbors = obs.get("neighbors") or {}
            recent_retreat = set(obs.get("recent_step_set") or [])
            # Step OFF the D tile via a NON-RECENT walkable direction
            # so we don't immediately walk back onto D from the tile
            # we just came from.
            for d in ("n", "s", "e", "w"):
                if d in recent_retreat:
                    continue
                t = neighbors.get(d)
                if t and t not in ("#", "M", "W"):
                    return d
            # No non-recent step exists -- agent is oscillating
            # between D and its single non-wall neighbour. ESCAPE
            # VALVE: if we've been on this floor a long time, just
            # descend. Worse than retreat but ends the loop.
            # Faramir the Brave + Forlong of the Mark (human seeds
            # 12345 + 314) hit this exact pattern on F3 / F5 with
            # HP=1, 1000+ turns oscillating.
            if (obs.get("turns_on_floor") or 0) > 400:
                return "d"
            # Otherwise fall back to a recent step (back to where we
            # came from -- explore there one more time).
            for d in ("n", "s", "e", "w"):
                t = neighbors.get(d)
                if t and t not in ("#", "M", "W"):
                    return d
            return rng.choice(["n", "s", "e", "w"])
        # Clear beneficials before descending -- but only if BFS says
        # they're CLOSE. The previous Manhattan-based check could pick a
        # beneficial behind a wall, causing an endless step-away /
        # step-back-onto-D ping-pong (seed=13 human burned 40 turns in
        # this loop). With path_dist <= 3 the agent only detours for
        # nearby beneficials and otherwise descends.
        # BENEFICIAL_SAFE = rooms that pay off without forced combat.
        # Q (alchemist): combine 2 potions for stronger result.
        # K (war room): free intel reveals next floor's special rooms.
        # B (blacksmith): cheap repair of worn gear.
        # F (shrine of the fallen): one-shot stat boost.
        # X (taxidermist) deliberately omitted -- only useful when the
        # agent has trophies, and adding it forces BFS detours for an
        # often-empty handoff. Stepped onto incidentally still works
        # via the mode handler, just not proactively targeted.
        BENEFICIAL_SAFE = ("C", "G", "L", "O", "A", "P", "Q", "K", "B", "F")
        stuck = (obs.get("turns_on_floor") or 0) > 300
        nearby = [
            feature_paths[t] for t in BENEFICIAL_SAFE
            if feature_paths.get(t)
            and feature_paths[t].get("path_dist") is not None
            and feature_paths[t]["path_dist"] <= 3
        ]
        if not stuck and nearby:
            best = min(nearby, key=lambda p: p["path_dist"])
            fs = best.get("first_step")
            if fs:
                return fs
        # Under-levelled + grind incomplete + not stuck: step OFF the
        # D tile so the agent finishes exploring + grinding the floor
        # before descending. The wayfinder's tier-strip filter handles
        # the targeting side, but an agent who frontier-walks INTO a
        # D tile (or spawns next to one -- F1 Thorin spawned with D
        # 2 tiles south and descended on turn 9 after 2 kills) lands
        # here without the tier filter ever firing. User-flagged:
        # "seeing a lot of runs with 1 or 2 moves on floor 1. That's
        # an easy way to start off on the wrong foot."
        kills_so_far_descend = obs.get("kills_on_floor") or 0
        pc_z_descend = (p.get("floor", 1) - 1)
        min_kills_descend = min(12, max(3, pc_z_descend * 2 + 1))
        coverage_pct_descend = (obs.get("tile_coverage") or {}).get("pct", 0)
        under_descend = p.get("level", 1) <= pc_z_descend + 1
        grind_done_descend = (
            kills_so_far_descend >= min_kills_descend
            or coverage_pct_descend >= 70
        )
        if (under_descend and not grind_done_descend
                and not stuck and not is_weak):
            # Anti-bounce: if we've visited this D tile 3+ times
            # already, the grind-step-off is creating a loop
            # (step north, wayfinder routes back to D, step north
            # again, repeat). Just descend and let the next floor
            # have the grind opportunity. Caught on s=271 dwarf
            # F2 D at (12,15): kof=0/3, on_floor=22, grind-step-off
            # fired each visit to D, agent looped n/s for 319T
            # without ever staying on F2 long enough to fight.
            cur_visits_d = obs.get("current_tile_visits") or 0
            if cur_visits_d >= 3:
                return "d"
            nmp_descend = obs.get("nearest_monster_path") or {}
            # Pocket short-circuit: if NO M tile is BFS-reachable on
            # this floor, there are no kills to grind for. Descend
            # rather than step-off and bounce.
            if not nmp_descend.get("first_step"):
                return "d"
            # Engage adjacent M directly: when nearest M is at
            # path_dist 1 (one of D's cardinal neighbours), step
            # toward it to fight. The step-off cascade below skips
            # M (hazard) and picks a non-M direction, which then
            # routes back to D next turn -- s=1234 dwarf F1 with D
            # at (2,2) and M south at (2,3), grind-not-done at
            # kof=2/3 looped n -> back to D -> n for 200+T. Going
            # straight into the M produces the kill we needed.
            if (nmp_descend.get("path_dist") == 1
                    and nmp_descend.get("first_step")):
                return nmp_descend["first_step"]
            neighbors = obs.get("neighbors") or {}
            recent_descend = set(obs.get("recent_step_set") or [])
            blocked_descend = set(obs.get("blocked_directions") or [])
            # Stair-island short-circuit: if the only non-wall non-
            # hazard neighbour is the OTHER stair (U), stepping off D
            # walks straight onto U where stairs_up_mode then steps
            # back onto D. Just descend and let the next floor have
            # a chance. Caught on s=1234 human F3 (1,1)U <-> (2,1)D
            # ping-pong for 99 turns. Same valve added in stairs_up.
            has_real_neighbor_down = any(
                neighbors.get(d) and neighbors.get(d) not in ("#", "U", "D", "M", "W")
                for d in ("n", "s", "e", "w")
            )
            if not has_real_neighbor_down:
                return "d"
            # Prefer non-recent, non-blocked, non-hazard direction
            # so the agent doesn't immediately walk back onto D the
            # next turn.
            for d in ("n", "s", "e", "w"):
                if d in recent_descend or d in blocked_descend:
                    continue
                t = neighbors.get(d)
                if t and t not in ("#", "M", "W"):
                    return d
            # Fall back to any non-blocked non-hazard dir.
            for d in ("n", "s", "e", "w"):
                if d in blocked_descend:
                    continue
                t = neighbors.get(d)
                if t and t not in ("#", "M", "W"):
                    return d
            # ESCAPE VALVE: no clean step-off direction exists --
            # all neighbours are walls/monsters/warps/recent.
            # Better to descend than oscillate forever. Anborn of
            # the White City (human seed 1100) reached an F2 D tile
            # with n=#, s=M, e=#, w=came-from -- the policy step-off
            # rng.choice'd a wall, agent stayed on D, repeat. 2500+
            # turns wasted. Descending into F3 is risky but at least
            # the agent makes progress and eventually dies honestly.
            return "d"
        return "d"
    if mode == "stairs_up_mode":
        # Shrunk on a bug level: ascent is also blocked ('the stairs
        # are impossibly tall'). Walk off the U tile. Quest-passed
        # re-shrunk player can still climb (auto-cure fires).
        if p.get("is_shrunk") and not p.get("passed_bug_quest"):
            neighbors = obs.get("neighbors") or {}
            for d in ("n", "s", "e", "w"):
                t = neighbors.get(d)
                if t and t not in ("#", "M", "W"):
                    return d
            for d in ("n", "s", "e", "w"):
                if neighbors.get(d) not in ("#", None):
                    return d
            return rng.choice(["n", "s", "e", "w"])
        # Retreat-after-warp: ASCEND. The agent landed on a U tile
        # while pc.z > max_z_via_stairs, so going up is the goal.
        # The default policy below walks AWAY from U to avoid the
        # stairs ping-pong, but during retreat we want the
        # ping-pong's opposite -- the trip back through familiar
        # territory.
        if obs.get("retreat_to_floor") is not None:
            return "u"
        # Persistent-oscillation escape: when the agent has been
        # stuck on a 2-tile fragment of this floor for 50+ turns
        # AND we're now on the U tile, ascend back to the prior
        # floor. Region-split layouts (e.g. s=88 human F2 with U at
        # (1,1) and a single '.' neighbour, surrounded by walls)
        # leave the smart-policy's normal step-off bouncing forever
        # because the only non-pair neighbour is the other stair-
        # adjacent tile. Build 318 tried a symmetric stair-island
        # 'u' valve but it cancelled out with stairs_down's 'd'
        # valve on descend/ascend, surfacing as 87/159 stuck.
        # Gating on osc_streak >= 50 fixes that -- the descend
        # valve fires immediately on entering a stair-island, then
        # we explore the new floor; only if exploration produces
        # a real 50-turn wedge does the ascend valve fire, bounded
        # by the 50T threshold per island visit.
        osc = obs.get("oscillation") or {}
        if osc.get("streak", 0) >= 50:
            return "u"
        # Stairs-up_mode fires as soon as you arrive on floor N+1 (your
        # landing tile is the U). Confirming would immediately bounce
        # the agent back to floor N's D, where stairs_down_mode would
        # fire again and we'd loop forever -- the playtester observed
        # 182/200 turns burned to this ping-pong. The handler accepts
        # n/s/e/w as a "walk away from the stairs" move, so step in
        # whatever direction has the most useful neighbour (or random
        # if none) -- this matches the game_loop wayfinder's instinct.
        neighbors = obs.get("neighbors") or {}
        recent_up = set(obs.get("recent_step_set") or [])
        # Prefer non-recent walkable so we don't immediately walk
        # back onto U from the same tile we came from. Without this,
        # Durin Forgewright (dwarf seed 314) and Eomer Crownless
        # (human seed 2500) bounced 415-1033 times between U and
        # the tile next to it -- stairs_up_mode walked east off U,
        # game_loop walked west back onto U, repeat.
        for d in ("n", "s", "e", "w"):
            if d in recent_up:
                continue
            t = neighbors.get(d)
            if t and t not in ("#", "U", "M", "W"):
                return d
        # Drop the recent-step filter but KEEP the hazard filter --
        # the earlier fallback excluded only ('#', 'U') so the agent
        # stepped onto a W neighbour from a U tile and got force-
        # warped. Gimli the Mighty (s=256 dwarf) walked off the F3 U
        # tile south straight onto a W and lost ~150 turns of
        # progress per warp. Hazards take precedence over recency.
        for d in ("n", "s", "e", "w"):
            t = neighbors.get(d)
            if t and t not in ("#", "U", "M", "W"):
                return d
        # Truly cornered: U above and the only other neighbour is M
        # or W. Prefer M over W (one fight vs a random teleport),
        # then fall back to ASCEND if even M/W are absent.
        # Caught on s=2500 human/elf: F2 was a 1-tile region-split
        # where the U tile sat alone with walls in all four cardinals.
        # stairs_up_mode's step-off cascade fell through to a random
        # cardinal pick, which wall-bumped 124+ turns, eventually
        # the agent stepped onto a passing W tile by chance and the
        # cycle repeated -- F1<->F2 ping-pong via stairs for 1400+T
        # until starvation. The ascend fallback breaks the loop AND
        # the step() recorder marks F2 as wedge so the next
        # stairs_down_mode strips D from priority.
        for d in ("n", "s", "e", "w"):
            t = neighbors.get(d)
            if t == "M":
                return d
        for d in ("n", "s", "e", "w"):
            t = neighbors.get(d)
            if t and t not in ("#", "U"):
                return d
        # All cardinals are wall/U/hazard absent. Wall-bumping for
        # 100+ turns hits the food clock; ascend instead so the
        # step() recorder marks this floor as a wedge and the next
        # descent skips it. See PlaytestSession.step().
        return "u"

    if mode == "warp_mode":
        # Floors are sometimes split into regions only connected via
        # warps (verified empirically on seed 7 floor 1: D was in a
        # region unreachable from the start), so we keep an accept
        # path -- but the early-game cost is brutal. Warps drop the
        # agent at random within +/- 2 floors, which routinely lands
        # a fresh Lv1 next to a Wraith on F3 with no escape route.
        # Resist hard on early floors and only accept when ACTUALLY
        # trapped (no reachable D + very stuck). Late game (z >= 10)
        # keeps the prior loose gate -- a lucky warp there is more
        # often a depth boost than a death sentence.
        #
        # HARD OVERRIDES (always resist, no matter how stuck):
        #   * starving: a random teleport does not feed you. User-
        #     flagged after Thorin of Belegost (dwarf seed 1234)
        #     surrendered to a warp at HP-low + starving, landed
        #     adjacent to a Lv6 Stirge on F7, died on the next
        #     flee's parting attack.
        #   * hp_pct < 0.20: random landing into a Lv(z+2) monster
        #     at sub-20% HP is a one-hit kill.
        feature_paths = obs.get("feature_paths") or {}
        d_reachable = bool((feature_paths.get("D") or {}).get("first_step"))
        # Same permanent-wedge override as game_loop: if the only D
        # leads to a known-impassable floor, treat D as unreachable
        # so the trapped_no_d path fires and we accept the warp.
        perm_wedge_warp = set(obs.get("permanent_wedge_floors") or [])
        cur_z_warp = p.get("floor", 1) - 1
        d_leads_to_perm_warp = (cur_z_warp + 1) in perm_wedge_warp
        if d_leads_to_perm_warp:
            d_reachable = False
        turns_since_new_warp = obs.get("turns_since_new_tile") or 0
        reach_pct_warp = (obs.get("tile_coverage") or {}).get("reach_pct", 0)
        turns_on_floor_warp_mode = obs.get("turns_on_floor") or 0
        if starving or hp_pct < 0.20:
            return "y"
        # Mirror the tightened trapped_no_d in game_loop: only
        # ACCEPT the warp when the agent is genuinely stuck on a
        # warp-only fragment of the floor (D unreachable, nearly all
        # reachable tiles already walked, no new tile in 200T).
        # Otherwise resist -- the resist roll fails ~60% of the
        # time, but the cost asymmetry (warp = 100-200T recovery vs
        # walking around) favours the gamble.
        # Mirror the tightened trapped_no_d in game_loop: ACCEPT the
        # warp when the agent is genuinely stuck. Three firing paths
        # (matched to the game_loop gate exactly):
        #   1. reach_pct >= 80% AND no new tile in 200T
        #   2. no new tile in 500T regardless of reach_pct
        #   3. 600T on the current floor with no D found
        turns_on_floor_warp = obs.get("turns_on_floor") or 0
        if (not d_reachable
                and (
                    (reach_pct_warp >= 80 and turns_since_new_warp >= 200)
                    or (turns_since_new_warp >= 500)
                    or (turns_on_floor_warp >= 600)
                    or (d_leads_to_perm_warp
                        and turns_on_floor_warp_mode >= 150)
                )):
            return "n"
        return "y"
    if mode == "altar_mode":
        # Pray once per altar -- claims the god's current tier reward
        # (HP heal, MP restore, hunger fill, blessing, eventually a
        # rune of devotion at T3). The altar is consumed by praying,
        # so the visited_features tracker will keep us from oscillating.
        # Sacrifice would be a multi-step item-picker; the playtest
        # value of guaranteed prayer boons is higher.
        return "pray"
    if mode == "pool_mode":
        # Drink, but with an HP gate. Pool outcomes are RNG: healing
        # restores HP, iron springs buff strength, BUT cursed wells
        # deal 20-35 raw (no-defense) damage, golden pool mimic deals
        # 50-100, mysterious explosion 15-40, all bypassing armor.
        # The combat audit caught 4 deaths whose last log was "basin
        # drains empty" -- agents drinking at low HP and being one-
        # shot by the unlucky outcome. Skip the drink when HP < 50
        # (covers cursed pool max + buffer; still some mimic risk on
        # gold pools but those are 10% within the 10% gold-pool slice).
        # When too weak, just walk away.
        # Pool drink gate: cursed pool max 35, mysterious explosion
        # 15-40, golden mimic 50-100 -- all raw, bypass armor. Skip
        # the drink when HP is below 60% of max (covers cursed pool
        # damage with a buffer; still some mimic risk). Relative
        # threshold matters: elf max_hp is 28, so an absolute HP<50
        # gate ALWAYS fires for elves at full health and traps them
        # in pool_mode forever sending 'x' (invalid command). Cirdan
        # the elf burned 2695 turns at full HP 48/48 stuck in a
        # warp-landed pool with all neighbours undiscovered before
        # this fix. Now: drink at >=60% HP; below that, try to walk
        # off; if no known walkable direction exists (warp landed in
        # fog), drink anyway -- a 1% catastrophic-mimic risk beats
        # an infinite loop.
        hp_pct_now = p["hp"] / max(1, p["max_hp"])
        if hp_pct_now >= 0.60:
            return "dr"
        neighbors = obs.get("neighbors") or {}
        recent = set(obs.get("recent_step_set") or [])
        for d in ("n", "s", "e", "w"):
            if d in recent:
                continue
            t = neighbors.get(d)
            if t not in ("#", None):
                return d
        for d in ("n", "s", "e", "w"):
            t = neighbors.get(d)
            if t not in ("#", None):
                return d
        # No known walkable direction (e.g., warp-landed in fog).
        # Take the drink rather than loop forever.
        return "dr"
    if mode == "tomb_mode":
        # Three choices from tomb_mode:
        #   'r' (Raid)         -- spawns an undead guardian at floor+2;
        #                         major cursed-gear reward on win.
        #   'p' (Pay Respects) -- free heal (30% max HP) or minor buff.
        #   n/s/e/w            -- walk out (process_tomb_action accepts
        #                         cardinal moves; the '.' neighbour we
        #                         arrived on is always safe since the
        #                         four-corner guardians block the rest).
        # Build-349 audit: UNDEAD/ELITE UNDEAD = 73% of combat deaths,
        # concentrated F5-F8 where the level+2 raid spawn outpaces
        # actual gear/HP growth. The prior gate (`pc.level < floor+2`)
        # let parity-level heroes raid into a floor+2 guardian and lose
        # the trade even with full HP. Replace with a strength gate
        # that gates on the THREE numbers that actually matter for the
        # fight outcome:
        #   1. level_ok    : pc.level >= floor+3 -- matches the cardinal-
        #                    guardian avoid threshold, gives us at least
        #                    a one-level HP cushion over the raid spawn.
        #   2. can_dent    : pc.strength + weapon.attack_bonus >=
        #                    guardian_defense + 5  -- if our hits round
        #                    to 1-2 dmg we'll never out-DPS the 140+ HP
        #                    guardian before food/HP runs out.
        #   3. can_survive : max_hp >= 4 * expected_dmg_per_hit. The
        #                    raid is multi-turn; we need 4 swings of
        #                    cushion to alpha-strike the guardian down.
        # If any gate fails: we're not strong enough to raid. Fall back:
        #   - Wounded (hp_pct < 0.70): 'p' for the free heal.
        #   - Full HP: walk out via the '.' neighbour we came from --
        #             don't burn the one-shot benefit at full HP.
        #   - No '.' neighbour visible: 'p' as last resort (still safe).
        # Hard vetoes (always pay respects, never raid):
        #   - is_weak               (HP < 50% or broken / missing gear)
        #   - no_escape             (no Healing Potion + no Heal spell)
        #   - tomb_suspected_here   (already saw undead on this floor;
        #                            multiple tomb encounters compound)
        pc_floor = p.get("floor", 1)
        floor_idx = pc_floor - 1  # raid spawn uses pc.z, which is 0-indexed
        pc_lv = p.get("level", 1)
        pc_str = p.get("strength", 10)
        pc_max_hp = p.get("max_hp", 1)
        equipped = p.get("equipped") or {}
        weapon = equipped.get("weapon") or {}
        armor = equipped.get("armor") or {}
        weapon_atk_bonus = (weapon.get("attack_bonus") or 0) if weapon else 0
        armor_def_bonus = (armor.get("defense_bonus") or 0) if armor else 0

        # Tomb-raid guardian stats (room_actions.py:2138-2149).
        # health = 80 + floor*12, attack = 12 + floor*1.5, defense = 8 + floor.
        g_attack = 12 + floor_idx * 1.5
        g_defense = 8 + floor_idx

        pc_attack = pc_str + weapon_atk_bonus
        pc_defense = 5 + armor_def_bonus  # game default base defense

        level_ok = pc_lv >= floor_idx + 3
        can_dent = pc_attack >= g_defense + 5
        expected_dmg = max(1, int(g_attack) - pc_defense)
        can_survive = pc_max_hp >= 4 * expected_dmg
        strong_enough = level_ok and can_dent and can_survive

        no_escape = (heal_pot_slot is None) and (heal_spell_slot is None)
        tomb_floor = bool(obs.get("tomb_suspected_here"))
        hard_veto = is_weak or no_escape or tomb_floor

        if strong_enough and not hard_veto:
            return "r"

        # Not strong enough -- decline. Pay respects when we'd benefit;
        # walk out when at full HP (the heal is wasted there).
        if hp_pct < 0.70:
            return "p"

        # Full HP: walk out via the '.' we came in on. The 4-corner
        # guardian spawn means non-'.' neighbours are walls or M tiles
        # (one of which we already cleared to step onto T). The cleared
        # tile becomes '.' and is our safe exit.
        neighbors = obs.get("neighbors") or {}
        for d in ("n", "s", "e", "w"):
            if neighbors.get(d) == ".":
                return d
        # No '.' exit visible (fog or unusual layout) -- pay respects
        # instead of raiding without the strength gate.
        return "p"
    if mode == "dungeon_mode":
        # Locked dungeon. Send 'u' regardless: if we hold the key the
        # handler unlocks and flips us into dungeon_unlocked_mode (next
        # turn we raid); if we don't, room_actions.py:1914 logs "no key"
        # and sets prompt_cntl back to game_loop -- the wayfinder picks
        # up from there. The handler does NOT accept n/s/e/w (it stays
        # in dungeon_mode silently), so we can't escape via movement
        # from inside this mode. visited_features keeps the wayfinder
        # from re-targeting the same locked dungeon over and over.
        return "u"
    if mode == "dungeon_unlocked_mode":
        # Loot the dungeon. The 'r' command pays out gold + items (or
        # rolls a Master Dungeon for the rune).
        return "r"
    if mode in ("garden_mode", "fey_garden_mode"):
        # Harvest. Yields herbs / ingredients / food. Fey gardens are
        # ephemeral and disappear if not harvested, so always grab.
        return "h"
    if mode == "library_mode":
        # Read a tome. The handler rolls vs INT to find a grimoire;
        # if it does, we get bumped into library_read_decision_mode
        # for the y/n attempt.
        return "r"
    if mode == "library_read_decision_mode":
        # Always attempt to read the grimoire. Risk is mostly upside --
        # success teaches a spell (or XP); failure just wastes the find.
        return "y"
    if mode == "blacksmith_mode":
        # Blacksmith repair is cheaper than vendors. Repair weapon then
        # armor, in priority order, only when the gear is actually worn
        # ( <100% durability) AND we can afford it. The handler stays
        # in blacksmith_mode on insufficient-gold (just logs 'Not
        # enough gold') so an unguarded "1"/"2" return creates an
        # infinite loop -- caught as status=stuck on s=1234 dwarf
        # F5 (4g in pocket, 850+ turns mashing '2'). Reforge (3/4)
        # is a gamble that re-rolls stats -- skip it for now, the
        # playtest value is risk-bounded repair coverage.
        gold = p.get("gold", 0)
        w = equipped.get("weapon")
        a = equipped.get("armor")
        w_worn = w and (w.get("durability") or 0) < (w.get("max_durability") or 1)
        a_worn = a and (a.get("durability") or 0) < (a.get("max_durability") or 1)
        w_can_pay = w_worn and gold >= (w.get("repair_cost_est") or 0)
        a_can_pay = a_worn and gold >= (a.get("repair_cost_est") or 0)
        if w_can_pay and not w.get("is_sealed"):
            return "1"
        if a_can_pay and not a.get("is_sealed"):
            return "2"
        # Nothing repairable that we can afford: handler doesn't
        # auto-exit so we have to walk off. Step in any non-wall
        # direction; on the next obs we'll be in game_loop and the
        # wayfinder takes over.
        neighbors = obs.get("neighbors") or {}
        for d in ("n", "s", "e", "w"):
            if neighbors.get(d) not in ("#", None):
                return d
        return rng.choice(["n", "s", "e", "w"])
    if mode == "shrine_mode":
        # One-shot stat boost (Shrine of the Fallen). Always pray --
        # the property `shrine_used` makes this one-and-done so the
        # visited_features tracker prevents oscillation.
        return "p"

    # ----------------------------------------------------------------
    # Picker rooms (Q alchemist, X taxidermist, K war room) + oracle.
    # Each opens its own prompt mode when the player steps onto the
    # tile; the handlers below either claim the boon and walk away, or
    # walk away immediately when there's nothing left to claim. Each
    # of these modes accepts n/s/e/w as walk-away movement, so the
    # _step_away helper routes through the same BFS first_step the
    # game_loop wayfinder would use.
    # ----------------------------------------------------------------
    def _step_away():
        """Walk off the current feature tile. Re-uses BFS first_step
        toward whatever target the game_loop would pick (D, beneficial,
        vendor) so the agent doesn't immediately step back. Falls
        through to any non-recent walkable neighbour, then any walkable
        neighbour, then any direction.

        The fallback path skips hazards (M / W) until exhausted, so a
        feature-room exit doesn't dump the agent onto an adjacent warp
        tile when a plain corridor is also available."""
        fp = obs.get("feature_paths") or {}
        ms = obs.get("nearest_monster_path")
        fs = obs.get("frontier_step")
        nb = obs.get("neighbors") or {}
        rs = set(obs.get("recent_step_set") or [])
        HAZARD_OFF = ("M", "W")
        # Try BFS-routed targets in roughly the game_loop priority.
        for cand in (
            fp.get("D"), fp.get("V"), fp.get("C"), fp.get("G"),
            fp.get("L"), fp.get("O"), fp.get("A"), fp.get("P"),
            fp.get("T"), fp.get("N"), ms, fs,
        ):
            if cand and cand.get("first_step"):
                d = cand["first_step"]
                # If the chosen step would re-enter a recent tile and
                # alternatives exist, swap; same anti-backtrack pattern
                # the main wayfinder uses.
                if d not in rs:
                    return d
        # Fallback: non-recent, non-hazard walkable direction
        # (SE-biased). User-flagged warps slipping in via _step_away
        # callers (oracle / war_room / taxidermist / alchemist).
        for d in ("e", "s", "w", "n"):
            if d in rs:
                continue
            t = nb.get(d)
            if t and t not in HAZARD_OFF and t != "#":
                return d
        # Drop the recent filter, keep hazard avoidance.
        for d in ("e", "s", "w", "n"):
            t = nb.get(d)
            if t and t not in HAZARD_OFF and t != "#":
                return d
        # Last resort: any non-wall neighbour, even a hazard.
        for d in ("e", "s", "w", "n"):
            t = nb.get(d)
            if t and t != "#":
                return d
        return rng.choice(["n", "s", "e", "w"])

    if mode == "oracle_mode":
        # Hints from generate_oracle_hints are text-only -- they reveal
        # vault / shard / boss locations as log lines but don't mutate
        # game state in a way our policy can read. So gazing is a wash
        # for us; skip it and walk away. visited_features marks O on
        # arrival, so the wayfinder won't re-target the oracle.
        return _step_away()

    if mode == "war_room_mode":
        # Free intel reveals all special rooms on the NEXT floor (or
        # current floor if next isn't generated yet) -- pre-scouts the
        # descent, real value. The raid mode option (2) is a gold-
        # gated XP gamble (100 + floor*5 gold for +50% XP / +25%
        # monster atk over 10 turns); skip it to keep gold reserves
        # for vendor restock.
        props = obs.get("room", {}).get("properties", {}) or {}
        if not props.get("intel_used"):
            return "1"
        return _step_away()

    if mode == "alchemist_mode":
        # Combine 2 potions into 1 stronger one. 3 uses per lab.
        # Two matching healing pots -> Superior Healing (~125 HP from
        # 2*50). Mixed types -> random elixir (still beneficial).
        # 10% botch -> poison / confusion potion (drinkable but
        # harmful; our policy only auto-drinks potion_healing so a
        # bad brew sits inert in the bag). Net EV positive.
        # Need at least 2 potions in the bag and uses remaining.
        props = obs.get("room", {}).get("properties", {}) or {}
        uses_left = props.get("alch_uses", 3)
        combining = bool(props.get("alch_combining"))
        potion_categories = (
            "potion_healing", "potion_mana", "potion",
        )
        potion_count = sum(
            1 for i in inv
            if (i.get("category") or "").startswith("potion")
        )
        if uses_left > 0 and potion_count >= 2:
            if combining:
                # Handler is awaiting "<a> <b>"; the alchemist's
                # potion list iterates inventory.items in insertion
                # order. Slot 1 + 2 is the safest pick -- starter
                # bag has 4 Minor Heals up front, and even mixed
                # types brew into a useful elixir.
                return "1 2"
            return "c"
        # Lab exhausted or no potions to combine -- leave.
        return _step_away()

    if mode == "taxidermist_mode":
        # 's' sells all trophies for gold (always +EV). We don't have
        # enough obs to know which collections are completable without
        # extending the harness; the gold sale is safe and frees a
        # bag slot. Completion rewards (auto-equipped accessories) are
        # left on the table for a future iteration with richer obs.
        #
        # NB: room_actions.process_taxidermist_action only accepts
        # digit / 's' / 'i' / 'x' -- NOT n/s/e/w (the action hint at
        # line 638 lies about that). Returning a direction here used
        # to softlock the agent on the X tile (caught as stuck=loop
        # on s=941 elf F9: 500+ idle turns mashing 'w' at hunger=0).
        # 'x' returns to game_loop where the wayfinder takes over.
        has_trophies = any(
            i.get("category") == "trophy" for i in inv
        )
        if has_trophies:
            return "s"
        return "x"

    return "back"


def random_policy(obs, rng):
    """Cheap-and-cheerful random policy for smoke-testing."""
    mode = obs["mode"]
    if mode == "game_loop":
        # Bias toward exploration + occasional descend
        choices = ["n", "s", "e", "w", "n", "s", "e", "w", "d"]
        return rng.choice(choices)
    if mode == "combat_mode":
        # Caster policy: if any affordable spell is memorized, sometimes cast
        p = obs["player"]
        affordable = [s for s in obs.get("memorized_spells", [])
                      if s["mana_cost"] <= p["mana"]]
        if affordable and rng.random() < 0.55:
            return "c"
        return "a" if rng.random() < 0.85 else "f"
    if mode == "spell_casting_mode":
        # Pick a random affordable spell (was hardcoded to slot 1, which
        # meant Fireball / Heal never got tested). Falls back to 'x' if
        # nothing is castable so the harness doesn't deadlock the turn.
        p = obs["player"]
        affordable = [s for s in obs.get("memorized_spells", [])
                      if s["mana_cost"] <= p["mana"]]
        if not affordable:
            return "x"
        return str(rng.choice(affordable)["slot"])
    if mode == "chest_mode":
        return "o" if rng.random() < 0.7 else "l"
    if mode == "stairs_down_mode":
        return "d"
    if mode == "stairs_up_mode":
        return "u"
    if mode == "inventory":
        return "x"
    return "back"


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _summarise(obs, jsonl=False):
    if jsonl:
        safe = {k: v for k, v in obs.items() if k != "log"}
        safe["log_tail"] = obs["log"][-3:]
        return json.dumps(safe, default=str)
    p = obs["player"]
    parts = [
        f"T{obs['turn']:>4} mode={obs['mode']:<19}",
        f"{p['name']}({p['race'][:3]})",
        f"F{p['floor']}@({p['x']:>2},{p['y']:>2})",
        f"HP {p['hp']}/{p['max_hp']}",
        f"MP {p['mana']}/{p['max_mana']}",
        f"Hu{p['hunger']:>3}",
        f"$ {p['gold']}",
        f"room={obs['room']['type']}",
    ]
    if obs.get("memorized_spells"):
        parts.append(f"spells={len(obs['memorized_spells'])}")
    if obs["monster"]:
        m = obs["monster"]
        parts.append(f"vs {m['name']}(L{m['level']} HP{m['hp']}/{m['max_hp']})")
    line = " ".join(parts)
    if obs["log"]:
        line += "\n  " + "\n  ".join(obs["log"])
    return line


def _read_script_actions(path):
    if path == "-":
        src = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    for raw in src.splitlines():
        a = raw.split("#", 1)[0].strip()
        if a:
            yield a


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="wizardscavern.playtest_harness",
        description="Headless playtest driver for Wizard's Cavern.",
    )
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed for reproducible runs.")
    parser.add_argument("--turns", type=int, default=200,
                        help="Maximum turns to run.")
    parser.add_argument("--policy", choices=("random", "smart", "script"),
                        default="random",
                        help="Action policy: random (cheap exploration), "
                             "smart (heal/eat/buy gates), or script (read "
                             "actions from --script).")
    parser.add_argument("--script", default=None,
                        help="Script file (one action per line). '-' for stdin.")
    parser.add_argument("--playtest-mode", action="store_true",
                        help="Enable gs.PLAYTEST (vaults/zotle force-spawn).")
    parser.add_argument("--jsonl", action="store_true",
                        help="Emit one JSON object per turn (machine-readable).")
    parser.add_argument("--interactive", action="store_true",
                        help="Read one action per line from stdin.")
    parser.add_argument("--name", default="Tester")
    parser.add_argument("--race", choices=sorted(RACE_MODS.keys()),
                        default="human",
                        help="Race (applies the same stat mods as the UI).")
    parser.add_argument("--int-bonus", type=int, default=0,
                        help="Add to intelligence after race mods. "
                             "Note: spell-casting requires int > 15.")
    parser.add_argument("--spells", default="",
                        help="Comma-separated SPELL_TEMPLATES names to "
                             "pre-memorize, e.g. 'Ice Shard,Heal'.")
    parser.add_argument("--no-starter-pack", action="store_true",
                        help="Skip the starting_shop bundle. Default is to "
                             "ship with Dagger + Leather Armor equipped, "
                             "4 Minor Healing Potions, Lantern, and Rations.")
    parser.add_argument("--no-lantern", action="store_true",
                        help="Smart policy skips lantern use + Lantern Fuel "
                             "buying. For A/B testing whether the lantern "
                             "mechanic adds anything to survival numbers.")
    parser.add_argument("--no-fog", action="store_true",
                        help="Disable fog-of-war in obs (agent sees the full "
                             "floor regardless of `discovered`). Useful for "
                             "isolating upstream balance from navigation.")
    parser.add_argument("--report-dir", default=None,
                        help="Write a per-run HTML report (and JSON sidecar) "
                             "to this directory. The report covers the hero, "
                             "their journey, victories, equipment, and death "
                             "if any. Auto-regenerates index.html.")
    parser.add_argument("--deploy", action="store_true",
                        help="After writing the report, push the report "
                             "directory to a gh-pages branch of this repo "
                             "via a worktree. Idempotent and additive: each "
                             "run accumulates onto the branch.")
    parser.add_argument("--replace", action="store_true",
                        help="With --deploy, purge the existing remote "
                             "docs/playtest/ tree before overlaying the "
                             "current report dir. Use this when you want "
                             "the deployed grid to reflect ONLY the current "
                             "batch (no stale runs from prior builds). "
                             "Without --replace, deploys are additive.")
    args = parser.parse_args(argv)

    spells = [s for s in args.spells.split(",") if s.strip()] if args.spells else None
    sess = new_game(seed=args.seed, playtest_mode=args.playtest_mode,
                    name=args.name, race=args.race,
                    starter_pack=not args.no_starter_pack,
                    fog_of_war=not args.no_fog,
                    int_bonus=args.int_bonus, spells=spells)
    obs = sess.observe()
    print(_summarise(obs, args.jsonl))

    # Report collector: tracks per-turn obs + log lines so we can
    # render a hero-postmortem page after the run finishes. Cheap
    # enough to leave on for every run; the rendering work happens
    # at finalize.
    report = None
    if args.report_dir or args.deploy:
        from .playtest_report import RunReport
        pc = gs.player_character
        starting_stats = {
            "health": pc.max_health, "attack": pc.attack,
            "defense": pc.defense, "strength": pc.strength,
            "dexterity": pc.dexterity, "intelligence": pc.intelligence,
            "max_mana": pc.max_mana,
        }
        report = RunReport(
            seed=args.seed, race=args.race,
            gender=getattr(pc, "gender", "non-binary"),
            name=pc.name, spells=spells,
            starting_stats=starting_stats,
        )
        report.record_obs(0, obs, gs.log_lines)

    rng = _stdlib_random.Random(args.seed)

    if args.interactive:
        action_source = iter(sys.stdin)
    elif args.policy == "script":
        if not args.script:
            parser.error("--policy script requires --script PATH (or '-')")
        action_source = _read_script_actions(args.script)
    else:
        action_source = None

    if args.policy == "smart":
        # Bind the lantern toggle so the per-turn callsite stays the same
        # shape as random_policy(obs, rng).
        use_lantern = not args.no_lantern
        def policy_fn(o, r, _ul=use_lantern):
            return smart_policy(o, r, use_lantern=_ul)
    else:
        policy_fn = random_policy

    for _ in range(args.turns):
        if sess.is_done():
            break
        if action_source is None:
            action = policy_fn(obs, rng)
        else:
            try:
                raw = next(action_source)
            except StopIteration:
                break
            action = raw.strip() if isinstance(raw, str) else raw
            if not action or action.startswith("#"):
                continue
        # Capture the PRE-step mode so record_action sees the mode
        # the agent was actually issuing the action from. Before
        # this fix, the call ran with obs['mode'] AFTER step() --
        # so e.g. a descent ('d' in stairs_down_mode) recorded as
        # ('stairs_up_mode', 'd') because step() landed the agent
        # on the new floor's U tile by the time we measured. The
        # floor-exit classifier then never matched 'stairs_down_mode
        # + d' and labelled every transition 'other'. User caught
        # it on s=461 human's Journey tab.
        pre_mode = obs["mode"]
        obs = sess.step(action)
        if report is not None:
            report.record_action(sess.turn, pre_mode, action)
            report.record_obs(sess.turn, obs, gs.log_lines)
        print(f"-> {action}")
        print(_summarise(obs, args.jsonl))
        if sess.last_error:
            print(f"  ! {sess.last_error}", file=sys.stderr)
        # Early-stop genuinely unsalvageable runs (no D/U/W
        # reachable + no escape scrolls + 1500+ turns on this
        # floor). Continuing would just burn harness CPU for no
        # signal. See PlaytestSession.is_truly_trapped.
        if not sess.early_terminated and sess.is_truly_trapped(obs):
            sess.early_terminated = True
            sess.early_terminate_reason = (
                f"no escape (F{obs['player']['floor']}, "
                f"{obs.get('turns_on_floor', 0)}T on floor, "
                f"reach {(obs.get('tile_coverage') or {}).get('reach_pct', 0):.0f}%)"
            )
            print(f"  ! early-terminate: {sess.early_terminate_reason}",
                  file=sys.stderr)

    # Final summary
    p = obs["player"]
    print()
    print(f"=== run finished: turns={sess.turn} "
          f"floor={p['floor']} hp={p['hp']}/{p['max_hp']} "
          f"gold={p['gold']} alive={obs['alive']} mode={obs['mode']} ===")

    # Append a one-line summary to the run log. Lives at the repo root
    # by default (gitignored) so you can `tail -f playtest_runs.log`
    # while running smoke tests. WIZARDSCAVERN_PLAYTEST_LOG env var
    # overrides the path; empty string disables.
    import os as _os
    import datetime as _dt
    default_log = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
        "playtest_runs.log",
    )
    log_path = _os.environ.get("WIZARDSCAVERN_PLAYTEST_LOG", default_log)
    if log_path:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"{_dt.datetime.now().isoformat(timespec='seconds')}"
                    f" seed={args.seed} race={args.race}"
                    f" name={p['name']} policy={args.policy}"
                    f" turns={sess.turn} floor={p['floor']}"
                    f" hp={p['hp']}/{p['max_hp']} gold={p['gold']}"
                    f" alive={obs['alive']} mode={obs['mode']}\n"
                )
        except OSError:
            pass  # logging is best-effort

    # Write HTML report and optionally deploy. Failures here are
    # non-fatal -- the run already finished and the data is in
    # game_state, but we don't want a bad git config to break runs.
    if report is not None:
        from .playtest_report import write_report, write_index, deploy_gh_pages
        report.finalize(
            obs, gs.log_lines, sess.turn,
            early_terminate_reason=sess.early_terminate_reason,
        )
        # Surface the 3-state classification (alive / dead / stuck) in
        # the run-end console output so smoke-test loops can see it
        # without scraping the HTML.
        suffix = f" reason={report.status_reason}" if report.status_reason else ""
        print(f"    status={report.status}{suffix}")
        out_dir = args.report_dir or _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            "playtest_reports",
        )
        try:
            page_path = write_report(report, out_dir)
            write_index(out_dir)
            print(f"\n>>> Report: {page_path}")
        except OSError as e:
            print(f"  ! report write failed: {e}", file=sys.stderr)
        if args.deploy:
            try:
                repo_root = _os.path.dirname(
                    _os.path.dirname(_os.path.abspath(__file__))
                )
                url = deploy_gh_pages(out_dir, repo_root, replace=args.replace)
                if url:
                    mode_label = "replace" if args.replace else "additive"
                    print(f">>> Deployed to gh-pages branch ({mode_label}, {url})")
                else:
                    print(">>> Deploy skipped (no changes).")
            except Exception as e:
                print(f"  ! deploy failed: {e}", file=sys.stderr)

    return 0 if obs["alive"] else 1


if __name__ == "__main__":
    sys.exit(main())
