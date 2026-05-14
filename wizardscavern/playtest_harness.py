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
    "dwarf": {"health_mod": 20,  "attack_mod": 2, "defense_mod": 2,
              "strength_mod": 2,  "dexterity_mod": -2, "intelligence_mod": -2},
}
BASE_STATS = {"health": 30, "attack": 15, "defense": 5,
              "strength": 10, "dexterity": 10, "intelligence": 10}


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_HTML_RE = re.compile(r"<[^>]+>")


def _strip_markup(s):
    if not isinstance(s, str):
        return s
    return _HTML_RE.sub("", _ANSI_RE.sub("", s))


def _strip_markup_list(lines):
    return [_strip_markup(line) for line in lines]


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
    return "other"


def new_game(seed=None, playtest_mode=False, name="Tester",
             race="human", gender="non-binary",
             int_bonus=0, spells=None):
    """Initialise a fresh headless game. Returns a ``PlaytestSession``.

    ``race`` applies the same stat modifiers the UI's character-creation
    flow uses (see game_systems.process_character_creation_action). Pass
    ``int_bonus`` to bump intelligence past the spell-casting threshold
    (int > 15) so an Elf can actually cast on turn one. ``spells`` is an
    iterable of SPELL_TEMPLATES names to pre-memorize.
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
    pc.gender = gender
    pc.character_class = "Adventurer"
    pc.health = min(stats["health"], pc.max_health)
    pc.mana = pc.max_mana  # re-clamp after the int_bonus bumps max_mana
    pc.gold = 500
    pc.memorized_spells = []
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
    return PlaytestSession()


ACTION_HINTS = {
    "game_loop":     "n s e w | d (descend) u (ascend) | i (inventory)",
    "combat_mode":   "a (attack) f (flee) c (cast) I (item) x (back)",
    "spell_casting_mode": "1..N (spell slot) x (cancel)",
    "inventory":     "1..9 (slot) x (back) e (equip-filter) u (use-filter)",
    "chest_mode":    "o (open) l (leave)",
    "vendor_shop":   "b (buy) s (sell) x (leave)",
    "stairs_down_mode": "d (descend) x (cancel)",
    "stairs_up_mode":   "u (ascend) x (cancel)",
    "death_screen":  "<game over>",
}


class PlaytestSession:
    """One playthrough. Holds a log-pointer + turn counter; state lives in gs."""

    def __init__(self):
        self._log_pointer = len(gs.log_lines)
        self.turn = 0
        self.last_action = None
        self.last_error = None

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
            },
            "memorized_spells": [
                {"slot": i + 1, "name": s.name,
                 "mana_cost": s.mana_cost, "level": s.level,
                 "type": s.spell_type}
                for i, s in enumerate(pc.memorized_spells)
            ],
            "vendor_inventory": self._vendor_obs(),
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
        return {
            "name": _strip_markup(m.name).strip(),
            "level": getattr(m, "level", None),
            "hp": m.health,
            "max_hp": getattr(m, "max_health", m.health),
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
            out.append({
                "slot": i + 1,
                "name": getattr(item, "name", repr(item)),
                "count": count,
                "category": _item_category(item),
            })
        return out

    def _vendor_obs(self):
        if gs.prompt_cntl != "vendor_shop" or gs.active_vendor is None:
            return None
        # Vendor's "buy" command uses get_sorted_inventory, so the slot
        # number we report must match the sorted order or 'b<N>' will buy
        # the wrong item.
        from .characters import get_sorted_inventory
        sorted_items = get_sorted_inventory(gs.active_vendor.inventory)
        return [
            {
                "slot": i + 1,
                "name": getattr(item, "name", repr(item)),
                "price": getattr(item, "calculated_value",
                                 getattr(item, "value", 0)),
                "category": _item_category(item),
            }
            for i, item in enumerate(sorted_items)
        ]

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

        return self.observe()

    def is_done(self):
        return (gs.game_should_quit
                or gs.prompt_cntl == "death_screen"
                or not gs.player_character.is_alive())


# ----------------------------------------------------------------------
# Policies
# ----------------------------------------------------------------------
def smart_policy(obs, rng):
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
    food_slot = next((i["slot"] for i in inv if i["category"] == "food"), None)
    heal_spell_slot = next((s["slot"] for s in spells
                            if s["type"] == "healing"
                            and s["mana_cost"] <= mana), None)
    affordable_spells = [s for s in spells if s["mana_cost"] <= mana]
    affordable_dmg = [s for s in affordable_spells if s["type"] == "damage"]

    if mode == "game_loop":
        if hp_pct < 0.30 and heal_pot_slot:
            return "i"
        if hunger < 50 and food_slot:
            return "i"
        return rng.choice(["n", "s", "e", "w", "n", "s", "e", "w", "d"])

    if mode == "inventory":
        # If the previous action raised an exception, bail out instead of
        # retrying the same thing (e.g. a buggy use-handler would otherwise
        # spin the policy forever). The harness records last_error per step.
        if obs.get("last_error"):
            return "x"
        # Heal first, then eat, then leave. Re-checks each turn so the slot
        # number stays valid if items were consumed.
        if hp_pct < 0.95 and heal_pot_slot:
            return f"u{heal_pot_slot}"
        if hunger < 80 and food_slot:
            return f"eat{food_slot}"
        return "x"

    if mode == "combat_mode":
        # Mid-fight heal: if a Heal-type spell fits the mana budget AND we're
        # below 40% HP, queue a cast (next-turn spell_casting_mode picks Heal).
        if hp_pct < 0.40 and heal_spell_slot:
            return "c"
        if affordable_dmg and rng.random() < 0.65:
            return "c"
        return "a" if rng.random() < 0.92 else "f"

    if mode == "spell_casting_mode":
        if hp_pct < 0.40 and heal_spell_slot:
            return str(heal_spell_slot)
        if affordable_dmg:
            return str(rng.choice(affordable_dmg)["slot"])
        if affordable_spells:
            return str(rng.choice(affordable_spells)["slot"])
        return "x"

    if mode == "vendor_shop":
        vendor_inv = obs.get("vendor_inventory") or []
        gold = p["gold"]
        # Stockpile: keep at least a few uses of each survival staple.
        # Sum item counts (not stack rows) so a single stack of 5 potions
        # still counts as 5 and the policy doesn't over-buy.
        STOCK = {"potion_healing": 3, "food": 2, "potion_mana": 2}
        owned = {cat: sum(i.get("count", 1) for i in inv
                          if i["category"] == cat)
                 for cat in STOCK}
        for v in vendor_inv:
            if v["price"] > gold:
                continue
            cat = v["category"]
            if cat in STOCK and owned.get(cat, 0) < STOCK[cat]:
                return f"b{v['slot']}"
        return "x"

    if mode == "chest_mode":
        return "o" if rng.random() < 0.85 else "l"
    if mode == "stairs_down_mode":
        return "d"
    if mode == "stairs_up_mode":
        return "u"
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
        f"{p['race'][:3]}",
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
    args = parser.parse_args(argv)

    spells = [s for s in args.spells.split(",") if s.strip()] if args.spells else None
    sess = new_game(seed=args.seed, playtest_mode=args.playtest_mode,
                    name=args.name, race=args.race,
                    int_bonus=args.int_bonus, spells=spells)
    obs = sess.observe()
    print(_summarise(obs, args.jsonl))

    rng = _stdlib_random.Random(args.seed)

    if args.interactive:
        action_source = iter(sys.stdin)
    elif args.policy == "script":
        if not args.script:
            parser.error("--policy script requires --script PATH (or '-')")
        action_source = _read_script_actions(args.script)
    else:
        action_source = None

    policy_fn = smart_policy if args.policy == "smart" else random_policy

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
    return 0 if obs["alive"] else 1


if __name__ == "__main__":
    sys.exit(main())
