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
    Potion, Food, Meat, Weapon, Armor, Spell,
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

# Race-themed name pools, LOTR-flavoured. Used when new_game() is called
# with the default name="Tester" -- each run picks a seed-stable name so
# transcripts read like adventurer logs instead of T200 spreadsheets.
RACE_NAMES = {
    "human": (
        "Aragorn", "Boromir", "Faramir", "Theoden", "Eomer", "Eowyn",
        "Denethor", "Isildur", "Elendil", "Beregond", "Imrahil",
        "Bard", "Beorn", "Hama", "Halbarad", "Forlong", "Gilraen",
    ),
    "elf": (
        "Elrond", "Legolas", "Galadriel", "Arwen", "Celeborn",
        "Glorfindel", "Haldir", "Thranduil", "Luthien", "Tauriel",
        "Finrod", "Earendil", "Feanor", "Idril", "Cirdan", "Galadhrim",
    ),
    "dwarf": (
        "Gimli", "Thorin", "Balin", "Dwalin", "Gloin", "Oin",
        "Bifur", "Bofur", "Bombur", "Fili", "Kili", "Dain",
        "Nori", "Ori", "Dori", "Durin", "Thror", "Thrain",
    ),
}


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_HTML_RE = re.compile(r"<[^>]+>")


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
            "attack_bonus": getattr(it, "attack_bonus", None),
            "defense_bonus": getattr(it, "defense_bonus", None),
            "item_level": getattr(it, "level", 0),
        }
    return {"weapon": slot(pc.equipped_weapon),
            "armor":  slot(pc.equipped_armor)}


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
        name = _stdlib_random.choice(RACE_NAMES.get(race, RACE_NAMES["human"]))
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
        from .items import Lantern as _Lantern, Food as _Food
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
            fuel_amount=50, light_radius=7, value=30, level=0,
        ))
        pc.inventory.add_item_quiet(_Food(
            "Rations", "Standard travel rations.",
            value=10, level=0, nutrition=40, count=5,
        ))
        for _ in range(4):
            pc.inventory.add_item_quiet(Potion(
                "Minor Healing Potion",
                "A small vial of red liquid that heals minor wounds.",
                value=30, level=0,
                potion_type="healing", effect_magnitude=30,
            ))
        # Spent on the starting shop: 4*30 + 10 + 50 + 30 + 0 = 210g.
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
    "chest_mode":    "o (open) l (leave)",
    "vendor_shop":   "b (buy) s (sell) x (leave)",
    "stairs_down_mode": "d (descend) x (cancel)",
    "stairs_up_mode":   "u (ascend) x (cancel)",
    "oracle_mode":      "g (gaze) | n s e w to leave",
    "alchemist_mode":   "c (combine) | '<a> <b>' to brew slots a+b | x (cancel) | n s e w to leave",
    "war_room_mode":    "1 (intel - free) 2 (raid - 100+f*5g) | n s e w to leave",
    "taxidermist_mode": "<N> (complete collection N) | s (sell trophies) | n s e w to leave",
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

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------
    def observe(self):
        pc = gs.player_character
        floor = gs.my_tower.floors[pc.z]
        room = floor.grid[pc.y][pc.x]
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
                "intelligence": pc.intelligence,
                "floor": pc.z + 1,
                "x": pc.x,
                "y": pc.y,
                "status_effects": list(pc.status_effects.keys()),
                "equipped": _equipped_obs(pc),
                "lantern": _lantern_obs(pc),
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
            "dungeon_keys": list(getattr(gs, "dungeon_keys", {}).keys()),
            "keyed_dungeon_target": self._keyed_dungeon_target_obs(),
            "nearest_undiscovered": self._nearest_undiscovered_obs(),
            "turns_on_floor": self.turn - self.floor_arrival_turn,
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
        return {
            "name": name,
            "level": getattr(m, "level", None),
            "hp": m.health,
            "max_hp": getattr(m, "max_health", m.health),
            "is_edible": meat_info is not None,
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

        in_combat = (gs.active_monster is not None
                     and gs.active_monster.is_alive())
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
                # are @properties that already fold in upgrade_level, so
                # we don't need to expose upgrade_level separately --
                # whatever the equipped property returns is what the
                # Character.attack / Character.defense calc will use.
                if isinstance(item, Weapon):
                    entry["attack_bonus"] = getattr(item, "attack_bonus", 0)
                else:
                    entry["defense_bonus"] = getattr(item, "defense_bonus", 0)
                entry["item_level"] = getattr(item, "level", 0)
                # equipped flag so the policy can compare bag items
                # against the slotted one without doing name matching.
                pc = gs.player_character
                entry["equipped"] = (
                    item is pc.equipped_weapon or item is pc.equipped_armor
                )
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
        for target in ("D", "V", "C", "G", "A", "L", "O", "P", "T", "N",
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
        for target in ("D", "V", "C", "G", "A", "L", "O", "P", "T", "N",
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
        if room_now.room_type not in (".", "E", "#", "D"):
            self.visited_features.add(
                (pc_after.z, pc_after.x, pc_after.y, room_now.room_type)
            )
        # Reset floor-arrival counter when we change floors so the
        # stuck-on-floor override fires per-floor, not cumulative.
        if pc_after.z != self._last_floor:
            self._last_floor = pc_after.z
            self.floor_arrival_turn = self.turn
            # Clear the recent-position history on floor change so the
            # anti-backtrack guard doesn't try to avoid a tile that's
            # no longer reachable (different floor).
            self.recent_positions = []
        # Record the new position for anti-backtrack. Keep a short
        # window (4 entries) -- long enough to detect 2-tile and
        # 3-tile oscillations, short enough that the agent isn't
        # blocked from genuinely retracing through a corridor.
        cur_xy = (pc_after.z, pc_after.x, pc_after.y)
        if not self.recent_positions or self.recent_positions[-1] != cur_xy:
            self.recent_positions.append(cur_xy)
            if len(self.recent_positions) > 4:
                self.recent_positions.pop(0)

        return self.observe()

    def is_done(self):
        return (gs.game_should_quit
                or gs.prompt_cntl == "death_screen"
                or not gs.player_character.is_alive())


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
    # `urgent_meat` is set when we hold a fresh meat with a low rot timer.
    # Raw meat lasts 30 moves, cooked 100, preserved 200 -- eating slightly
    # before rot lets the agent stretch its food budget instead of letting
    # the kill drop go to waste. Tracks the 1-based edible-list index of
    # the first fresh meat with the shortest fuse.
    edible_count = 0
    urgent_meat = None
    urgent_rot = None
    MEAT_EAT_BEFORE = 8  # eat fresh meat once rot_timer <= 8 moves
    for i in inv:
        if i["category"] in ("food", "food_rotten"):
            edible_count += 1
            if i["category"] == "food" and food_slot is None:
                food_slot = edible_count
            # rot_timer is only set on Meat entries (Food rations don't rot).
            rot = i.get("rot_timer")
            if (i["category"] == "food" and rot is not None
                    and rot <= MEAT_EAT_BEFORE):
                if urgent_rot is None or rot < urgent_rot:
                    urgent_rot = rot
                    urgent_meat = edible_count
    heal_spell_slot = next((s["slot"] for s in spells
                            if s["type"] == "healing"
                            and s["mana_cost"] <= mana), None)
    affordable_spells = [s for s in spells if s["mana_cost"] <= mana]
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
    is_weak = (
        hp_pct < 0.50
        or broken_weapon
        or broken_armor
        or (equipped.get("weapon") is None)
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
        # Pre-combat buff: when M is adjacent AND we have an identified
        # combat-buff potion in the bag, open inventory to drink it
        # BEFORE stepping into combat. Buff potions (Stone Skin /
        # Strength / Defense / Regeneration / etc.) have 3-5 turn
        # durations and are wasted when drunk far from a fight; this
        # times them to the actual encounter. HP gate at >= 60%
        # ensures we don't burn the inventory turn when healing is
        # the higher priority.
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
        if has_buff_potion and hp_pct >= 0.60 and m_adjacent:
            return "i"
        if urgent_meat is not None:
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
        if hunger < 50 and food_slot:
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
        if use_lantern and lantern_fuel > 5:
            if unknown_neighbours >= 2:
                return "l"
            if stuck_on_floor and unknown_neighbours >= 1:
                return "l"
            if very_stuck and obs["turn"] % 10 == 0:
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
        if starving:
            AVOID = ({"W"} if is_weak else set())  # still avoid warps
        else:
            AVOID = ({"M", "W"} if is_weak else set())

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
        nearest = obs.get("nearest_features") or {}
        feature_paths_check = obs.get("feature_paths") or {}
        unvisited_beneficials_exist = any(
            feature_paths_check.get(t) for t in BENEFICIAL_SAFE
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

        if too_long_on_floor:
            # Hard descent override: 300+ turns on one floor means
            # whatever's left (an unreachable beneficial, a hunt-mode
            # monster respawn loop) isn't worth more grinding. Push the
            # agent toward the stairs and let the next floor reset the
            # economy.
            priority = ["D", "V"]
        elif is_weak:
            priority = ["V"] + list(BENEFICIAL_SAFE)
            if not unvisited_beneficials_exist:
                priority.append("D")  # only descend if nothing safer
        elif wants_vendor:
            priority = ["V"] + list(BENEFICIAL_SAFE) + ["T", "N"]
            if not unvisited_beneficials_exist:
                priority.append("D")
        elif ready_to_clear:
            # Boon budget spent OR resource pressure forces the shift:
            # the agent transitions to efficient monster clearing for
            # meat (food) + XP + gold. M comes BEFORE D so the agent
            # banks value from the current floor rather than racing
            # the stairs into harder content with no kill rewards. The
            # too_long_on_floor escape (300+ turns) bounds this from
            # looping on a respawning floor. SAFE rooms stay at the
            # top for any beneficials that respawn or become reachable.
            priority = list(BENEFICIAL_SAFE) + ["V", "M", "T", "N", "D"]
        elif unvisited_beneficials_exist:
            # Healthy + boons remain: opportunistic monster hunting
            # while still preferring safer boons. M slots after V but
            # before T/N so the agent banks XP on the way to chests /
            # gardens / altars instead of dying at F4 with 0 kills
            # (the audit caught mean kills/run = 0.5 across 30 runs
            # before this -- BFS routing AROUND M tiles in transit
            # meant the agent literally never fought unless M was in
            # its priority list).
            priority = list(BENEFICIAL_SAFE) + ["V", "M", "T", "N"]
        else:
            # Floor mostly explored, no boons remain: descend, but
            # take a parting M kill if one is on the path.
            priority = ["D", "V", "M", "T", "N"] + list(BENEFICIAL_SAFE)
        priority = tuple(priority)

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
            if t in priority and not visited.get(d):
                rank = priority.index(t)
                if rank < best_rank:
                    best_dir, best_rank = d, rank
        if best_dir is not None:
            return best_dir

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

        def _swap_if_backtrack(d):
            """Anti-backtrack: if `d` would re-step on a recent tile and
            a non-recent walkable alternative exists, use the
            alternative instead. Breaks the SE-tiebreak ping-pong that
            burned 4857/5000 turns on seed=42 dwarf F2 before the fix."""
            if d not in recent_steps:
                return d
            alts = []
            for alt in ("n", "s", "e", "w"):
                if alt == d or alt in recent_steps:
                    continue
                t = neighbors.get(alt)
                if t in AVOID or t == "#":
                    continue
                alts.append(alt)
            if alts:
                return rng.choice(alts)
            return d

        # Keyed dungeon (if any) via BFS first_step.
        if keyed_tgt and keyed_tgt.get("first_step"):
            return _swap_if_backtrack(keyed_tgt["first_step"])

        # Priority-ordered feature targeting via BFS.
        for t in priority:
            if t == "M":
                # Monsters aren't in feature_paths -- use the dedicated
                # monster-path obs which routes to an adjacent tile and
                # steps into the M to initiate combat.
                if monster_path and monster_path.get("first_step"):
                    return _swap_if_backtrack(monster_path["first_step"])
                continue
            path = feature_paths.get(t)
            if path and path.get("first_step"):
                return _swap_if_backtrack(path["first_step"])

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
            return t not in AVOID and t != "#"
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
        undiscovered_nbrs = [d for d in candidates if neighbors.get(d) is None]
        if undiscovered_nbrs:
            candidates = undiscovered_nbrs
        if not candidates:
            candidates = [d for d in ("n", "s", "e", "w") if _walkable(d)]
        if not candidates:
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
        if proposed is None and hp_pct < 0.95 and heal_pot_slot:
            proposed = f"u{heal_pot_slot}"
        if proposed is None and urgent_meat is not None:
            # Don't wait until starving -- consume the kill drop now.
            proposed = f"eat{urgent_meat}"
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
                        and entry["name"] != equipped["weapon"]["name"]):
                    proposed = f"e{entry['slot']}"
                    break
        if (proposed is None
                and equipped.get("armor", {})
                and equipped["armor"].get("is_broken")
                and not cursed_armor):
            for entry in inv:
                if (entry["category"] == "armor"
                        and not entry.get("is_broken")
                        and entry["name"] != equipped["armor"]["name"]):
                    proposed = f"e{entry['slot']}"
                    break
        if proposed is None and weapon_upgrade_slot is not None:
            # Strict-bonus upgrade in the bag, equip it. The
            # _best_upgrade helper already filtered known-cursed and
            # sealed candidates.
            proposed = f"e{weapon_upgrade_slot}"
        if proposed is None and armor_upgrade_slot is not None:
            proposed = f"e{armor_upgrade_slot}"
        if proposed is None and hunger < 80 and food_slot:
            proposed = f"eat{food_slot}"
        # Read safe identified scrolls -- one-shot beneficial effects
        # the agent's been hoarding. Skip teleport (random
        # destination, could land in a dangerous spot) and descent
        # (skips the floor, defeats boon-collection). remove_curse
        # only when actually cursed.
        SAFE_SCROLL_TYPES = {
            "mapping", "upgrade", "spell_scroll",
            "lantern_upgrade", "restoration", "foresight",
            "protection", "identify", "vendor_restock",
        }
        if proposed is None:
            for entry in inv:
                if entry["category"] != "scroll":
                    continue
                if not entry.get("is_identified"):
                    continue
                stype = entry.get("scroll_type")
                if stype in SAFE_SCROLL_TYPES:
                    proposed = f"u{entry['slot']}"
                    break
                if (stype == "remove_curse"
                        and (cursed_weapon or cursed_armor)):
                    proposed = f"u{entry['slot']}"
                    break
        # Drink identified buff potions when HP is decent but not
        # full. The combat-buff potions (strength, defense, stone
        # skin, regeneration, etc.) are tactical effects that
        # otherwise sit in the bag until death. Drink them while
        # the agent is alive to see -- worst case the duration runs
        # out before a fight, best case it saves the next combat.
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
        UNDEAD_NAMES = ("wraith", "lich", "skeleton", "vampire",
                        "ghost", "zombie", "spectral", "phantom")
        is_undead = any(k in m_name_low for k in UNDEAD_NAMES)
        # Two-band threat assessment:
        #  * general monsters: flee at m_level > pc.level + 2 (the
        #    original threshold -- aggressive enough that Lv1 agents
        #    fight Lv0-3 monsters and bank XP).
        #  * undead (wraith/lich/skeleton/etc.): flee one tier
        #    earlier (m_level >= pc.level + 1) because they hit for
        #    raw damage and resist physical, often dropping no meat.
        # max_hp gate (m_max_hp > 2x pc_max_hp) catches HP-bag bosses.
        monster_too_tough = (
            m_level > pc_level + 2
            or m_max_hp > 2 * p["max_hp"]
            or (is_undead and m_level > pc_level)
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
        # Threat-flee only when NOT starving -- a starving agent vs
        # an edible monster needs to win this fight to live.
        if monster_too_tough and not starving:
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
        STOCK = {"potion_healing": 3, "food": 8, "potion_mana": 2}
        if use_lantern and lantern_fuel < 20:
            STOCK["lantern_fuel"] = 2
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
        SCROLL_BUY_CAP = 3
        owned_scrolls = sum(1 for i in inv if i["category"] == "scroll")
        owned_buff_potion_types = {
            i["category"] for i in inv
            if i["category"].startswith("potion_")
            and i["category"] not in ("potion_healing", "potion_mana")
        }
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
        return "o" if rng.random() < 0.85 else "l"
    if mode == "stairs_down_mode":
        # Clear beneficials before descending -- but only if BFS says
        # they're CLOSE. The previous Manhattan-based check could pick a
        # beneficial behind a wall, causing an endless step-away /
        # step-back-onto-D ping-pong (seed=13 human burned 40 turns in
        # this loop). With path_dist <= 3 the agent only detours for
        # nearby beneficials and otherwise descends.
        feature_paths = obs.get("feature_paths") or {}
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
        return "d"
    if mode == "stairs_up_mode":
        # Stairs-up_mode fires as soon as you arrive on floor N+1 (your
        # landing tile is the U). Confirming would immediately bounce
        # the agent back to floor N's D, where stairs_down_mode would
        # fire again and we'd loop forever -- the playtester observed
        # 182/200 turns burned to this ping-pong. The handler accepts
        # n/s/e/w as a "walk away from the stairs" move, so step in
        # whatever direction has the most useful neighbour (or random
        # if none) -- this matches the game_loop wayfinder's instinct.
        neighbors = obs.get("neighbors") or {}
        for d in ("n", "s", "e", "w"):
            t = neighbors.get(d)
            if t and t not in ("#", "U"):
                return d
        return rng.choice(["n", "s", "e", "w"])
    if mode == "warp_mode":
        # Floors are sometimes split into regions only connected via
        # warps (verified empirically on seed 7 floor 1: D was in a
        # region unreachable from the start). The default 'always
        # resist' policy was leaving dwarves stuck on floor 1 for the
        # full 5000-turn budget because they could never reach the
        # downstairs. New rule: resist when fresh, accept when stuck.
        # Accepting a warp drops us at a random (z +/- 2) location,
        # so an accept on floor 1 either lands deeper or stays on
        # floor 1 in a different region -- both moves help.
        stuck = (obs.get("turns_on_floor") or 0) > 200
        return "n" if stuck else "y"
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
        if p["hp"] < 50:
            neighbors = obs.get("neighbors") or {}
            for d in ("n", "s", "e", "w"):
                if neighbors.get(d) not in ("#", None):
                    return d
            return "x"
        return "dr"
    if mode == "tomb_mode":
        # Tombs offer a binary risk choice each visit:
        #   'r' (Raid)         -- spawns an undead guardian; if you win,
        #                         major reward (cursed weapon/armor).
        #   'p' (Pay Respects) -- safe heal or minor buff, no fight.
        # Raid only when we have a real fallback for a bad fight.
        # Tomb guardians can be Lv5 at floor 1-3 (dwarf/123 ate a 46-dmg
        # Wraith one-shot at 91% HP with no escape route), so HP% alone
        # is not enough. Two gates, EITHER triggers 'p':
        #   1. is_weak            (HP < 50% or broken / missing gear)
        #   2. no fallback option (no healing potion in bag AND no
        #                          affordable Heal spell). If both are
        #                          missing we have no way to recover
        #                          from a bad guardian draw.
        no_escape = (heal_pot_slot is None) and (heal_spell_slot is None)
        if is_weak or no_escape:
            return "p"
        return "r"
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
        # ( <100% durability). Otherwise leave. Reforge (3/4) is a
        # gamble that re-rolls stats -- skip it for now, the playtest
        # value is risk-bounded repair coverage.
        w = equipped.get("weapon")
        a = equipped.get("armor")
        w_worn = w and (w.get("durability") or 0) < (w.get("max_durability") or 1)
        a_worn = a and (a.get("durability") or 0) < (a.get("max_durability") or 1)
        if w_worn and not w.get("is_sealed"):
            return "1"
        if a_worn and not a.get("is_sealed"):
            return "2"
        # Nothing to repair: handler doesn't auto-exit so we have to
        # walk off. Step in any non-wall direction; on the next obs
        # we'll be in game_loop and the wayfinder takes over.
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
        neighbour, then any direction."""
        fp = obs.get("feature_paths") or {}
        ms = obs.get("nearest_monster_path")
        fs = obs.get("frontier_step")
        nb = obs.get("neighbors") or {}
        rs = set(obs.get("recent_step_set") or [])
        AVOID_TILES = {"#"}
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
        # Fallback: any non-recent walkable direction (SE-biased).
        for d in ("e", "s", "w", "n"):
            if d in rs:
                continue
            if nb.get(d) in AVOID_TILES:
                continue
            return d
        for d in ("e", "s", "w", "n"):
            if nb.get(d) not in AVOID_TILES:
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
        has_trophies = any(
            i.get("category") == "trophy" for i in inv
        )
        if has_trophies:
            return "s"
        return _step_away()

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
        obs = sess.step(action)
        if report is not None:
            report.record_action(sess.turn, obs["mode"], action)
            report.record_obs(sess.turn, obs, gs.log_lines)
        print(f"-> {action}")
        print(_summarise(obs, args.jsonl))
        if sess.last_error:
            print(f"  ! {sess.last_error}", file=sys.stderr)

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
        report.finalize(obs, gs.log_lines, sess.turn)
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
                url = deploy_gh_pages(out_dir, repo_root)
                if url:
                    print(f">>> Deployed to gh-pages branch ({url})")
                else:
                    print(">>> Deploy skipped (no changes).")
            except Exception as e:
                print(f"  ! deploy failed: {e}", file=sys.stderr)

    return 0 if obs["alive"] else 1


if __name__ == "__main__":
    sys.exit(main())
