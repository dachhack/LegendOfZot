"""
The Orb of Zot — a playable embedding of the original 1980 *Wizard's Castle*.

When the hero claims the Orb of Zot at the end of Wizard's Cavern, the cavern
seals itself. The only way out is *inside* the orb: a faithful recreation of
Joseph Power's 1980 BASIC classic *The Wizard's Castle* — the very game whose
goal was, fittingly, to find the Orb of Zot. Beat it (claim the inner Orb and
walk out the entrance) and the castle whispers a Word of Passage that unseals
the cavern.

This module is fully self-contained: it owns its own game state (stored on
`gs.orb_game`), its own input dispatch (`process_orb_command`) and its own
rendering (`render_orb_html`). The outer game routes to it whenever
`gs.prompt_cntl == 'orb_game'`.

Design notes (the iconic 1980 systems, all present):
  * 8x8x8 toroidal castle, the Entrance on level 1.
  * Race / attribute setup; Strength doubles as hit points (you die at ST 0).
  * The 12 monsters, 8 treasures, the Runestaff and the Orb of Zot.
  * Pools, chests, books, crystal orbs, flares, the lamp, warps, sinkholes,
    stairs, vendors, gold and the three curses (Lethargy, the Leech,
    Forgetfulness) with their curing treasures.
  * Web / Fireball / Deathspell combat magic, bribery and retreat.
  * Death inside the orb is not permadeath — you wake in the sealed chamber
    and may re-enter for a freshly woven castle.
"""

import random

from . import game_state as gs


# ---------------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------------

SIZE = 8  # castle is SIZE x SIZE x SIZE
ENTRANCE = (4, 1, 1)  # (x, y, z) — north edge of level 1

# (name, tier).  Tier scales hp and the attack die.  Deeper levels lean
# toward higher-tier monsters.
MONSTERS = [
    ("Kobold", 1), ("Orc", 2), ("Wolf", 3), ("Goblin", 4),
    ("Ogre", 5), ("Troll", 6), ("Bear", 7), ("Minotaur", 8),
    ("Gargoyle", 9), ("Chimera", 10), ("Balrog", 11), ("Dragon", 12),
]
MONSTER_TIER = {name: tier for name, tier in MONSTERS}

# Treasures: name -> (gold value, cure).  The cure is the status/curse this
# treasure neutralises when carried (and removes on pickup).
RUBY_RED, NORN_STONE, PALE_PEARL, OPAL_EYE = "Ruby Red", "Norn Stone", "Pale Pearl", "Opal Eye"
GREEN_GEM, BLUE_FLAME, PALANTIR, SILMARIL = "Green Gem", "Blue Flame", "Palantir", "Silmaril"

TREASURES = {
    RUBY_RED:   (1500, "lethargy"),
    NORN_STONE: (1000, None),
    PALE_PEARL: (1750, "leech"),
    OPAL_EYE:   (1250, "blind"),
    GREEN_GEM:  (2000, "forgetful"),
    BLUE_FLAME: (2250, "book_stuck"),
    PALANTIR:   (2500, None),
    SILMARIL:   (5000, None),
}
TREASURE_ORDER = [RUBY_RED, NORN_STONE, PALE_PEARL, OPAL_EYE,
                  GREEN_GEM, BLUE_FLAME, PALANTIR, SILMARIL]

# Armor / weapon shop tables: id -> (label, cost, value)
ARMORS = {
    "none":    ("No Armor", 0, 0),
    "leather": ("Leather",  10, 7),
    "chain":   ("Chainmail", 20, 14),
    "plate":   ("Plate",     30, 21),
}
WEAPONS = {
    "none":   ("Bare Hands", 0, 0),
    "dagger": ("Dagger", 10, 1),
    "mace":   ("Mace",   20, 2),
    "sword":  ("Sword",  30, 3),
}

RACES = {
    "human":  ("Human",  dict(st=0, iq=0, dx=0, other=8)),
    "elf":    ("Elf",    dict(st=0, iq=2, dx=2, other=6)),
    "dwarf":  ("Dwarf",  dict(st=4, iq=0, dx=0, other=6)),
    "hobbit": ("Hobbit", dict(st=0, iq=0, dx=4, other=4)),
}

ATTR_BASE = 8     # every attribute starts here before race + allocation
ATTR_MAX = 18     # hard cap, as in the original
START_GOLD = 60

# Map glyphs for the discovered-room minimap.
GLYPHS = {
    "entrance": "E", "empty": ".", "stairs_down": "v", "stairs_up": "^",
    "pool": "P", "chest": "C", "gold": "$", "flares": "*", "warp": "W",
    "sinkhole": "O", "crystal": "*", "book": "B", "vendor": "V",
    "monster": "M", "treasure": "T",
}


# ---------------------------------------------------------------------------
# Castle generation
# ---------------------------------------------------------------------------

def _key(x, y, z):
    return f"{x},{y},{z}"


def _empty_rooms(castle):
    return [k for k, r in castle.items() if r["t"] == "empty"]


def _generate_castle():
    """Weave a fresh 8x8x8 Wizard's Castle. Returns dict[str_key] -> room."""
    castle = {}
    for z in range(1, SIZE + 1):
        for y in range(1, SIZE + 1):
            for x in range(1, SIZE + 1):
                castle[_key(x, y, z)] = {"t": "empty"}

    castle[_key(*ENTRANCE)] = {"t": "entrance"}

    # Stairs: 2 down-stairs per level 1..7, each paired with an up-stair
    # directly below it so descent/ascent is reversible.
    for z in range(1, SIZE):
        placed = 0
        attempts = 0
        while placed < 2 and attempts < 200:
            attempts += 1
            x = random.randint(1, SIZE)
            y = random.randint(1, SIZE)
            here = _key(x, y, z)
            below = _key(x, y, z + 1)
            if castle[here]["t"] != "empty" or castle[below]["t"] != "empty":
                continue
            castle[here] = {"t": "stairs_down"}
            castle[below] = {"t": "stairs_up"}
            placed += 1

    # Eight treasures, one each, scattered across the whole castle.
    empties = _empty_rooms(castle)
    random.shuffle(empties)
    for name in TREASURE_ORDER:
        if empties:
            castle[empties.pop()] = {"t": "treasure", "name": name}

    # Scatter the lively contents through the remaining empty rooms.
    # Weighted to feel like the original: lots of monsters, a sprinkle of
    # everything else, and a good number of genuinely empty rooms.
    pool = (
        ["monster"] * 22 + ["gold"] * 8 + ["flares"] * 6 + ["pool"] * 7 +
        ["chest"] * 7 + ["book"] * 5 + ["crystal"] * 4 + ["warp"] * 4 +
        ["sinkhole"] * 4 + ["vendor"] * 4 + ["empty"] * 29
    )
    for k in _empty_rooms(castle):
        t = random.choice(pool)
        if t == "monster":
            z = int(k.split(",")[2])
            # Deeper => tougher. Centre the monster tier on the level depth.
            lo = max(0, z - 3)
            hi = min(len(MONSTERS) - 1, z + 2)
            name = MONSTERS[random.randint(lo, hi)][0]
            castle[k] = {"t": "monster", "name": name, "rune": False}
        else:
            castle[k] = {"t": t}

    # The Orb of Zot lives inside a warp on a deep level (5-8).
    deep_warps = [k for k, r in castle.items()
                  if r["t"] == "warp" and int(k.split(",")[2]) >= 5]
    if not deep_warps:
        # No deep warp materialised — convert a deep empty/monster room.
        candidates = [k for k in castle if int(k.split(",")[2]) >= 5
                      and castle[k]["t"] not in ("entrance", "stairs_up", "stairs_down")]
        orb_room = random.choice(candidates)
        castle[orb_room] = {"t": "warp"}
    else:
        orb_room = random.choice(deep_warps)
    castle[orb_room]["orb"] = True

    # The Runestaff is held by one (deep) monster.
    monster_rooms = [k for k, r in castle.items() if r["t"] == "monster"]
    if monster_rooms:
        deep_mons = [k for k in monster_rooms if int(k.split(",")[2]) >= 4] or monster_rooms
        castle[random.choice(deep_mons)]["rune"] = True

    # Three hidden curse rooms (overlaid on otherwise-empty rooms).
    curse_targets = _empty_rooms(castle)
    random.shuffle(curse_targets)
    for curse in ("lethargy", "leech", "forgetful"):
        if curse_targets:
            castle[curse_targets.pop()]["curse"] = curse

    return castle


def _new_player():
    return {
        "race": None, "sex": "male",
        "st": ATTR_BASE, "iq": ATTR_BASE, "dx": ATTR_BASE,
        "gold": START_GOLD, "flares": 0,
        "armor": "none", "armor_pts": 0,
        "weapon": "none", "lamp": False,
        "treasures": [], "runestaff": False, "orb": False,
        "blind": False, "book_stuck": False,
        "curses": {"lethargy": False, "leech": False, "forgetful": False},
        "x": ENTRANCE[0], "y": ENTRANCE[1], "z": ENTRANCE[2],
        "other_points": 0,
    }


def _new_castle_state(screen="setup_race"):
    return {
        "screen": screen,
        "log": [],
        "castle": _generate_castle(),
        "seen": [_key(*ENTRANCE)],
        "player": _new_player(),
        "monster": None,        # active combat monster dict
        "turns": 0,
        "code_entry": "",       # buffer for the escape-lock screen
    }


# ---------------------------------------------------------------------------
# Logging / small helpers
# ---------------------------------------------------------------------------

def _log(g, msg):
    g["log"].append(msg)
    if len(g["log"]) > 40:
        g["log"] = g["log"][-40:]


def _here(g):
    p = g["player"]
    return g["castle"][_key(p["x"], p["y"], p["z"])]


def _see(g, x, y, z):
    k = _key(x, y, z)
    if k not in g["seen"]:
        g["seen"].append(k)


def _gen_code():
    # A four-rune Word of Passage. Avoids ambiguous letters.
    alphabet = "ABCDEFGHJKLMNPRSTUVWXYZ"
    return "".join(random.choice(alphabet) for _ in range(4))


# ---------------------------------------------------------------------------
# Public entry — called by combat.py when Zot's Guardian falls
# ---------------------------------------------------------------------------

def begin_orb_endgame(player_character):
    """The Guardian is slain. Grant the Orb, seal the cavern, open the orb."""
    gs.cavern_sealed = True
    gs.orb_escaped = False
    gs.orb_escape_code = None
    g = {
        "screen": "intro",
        "log": [],
        "castle": None, "seen": [], "player": None,
        "monster": None, "turns": 0, "code_entry": "",
    }
    gs.orb_game = g
    gs.prompt_cntl = "orb_game"
    try:
        gs.game_stats["orb_obtained"] = True
    except Exception:
        pass


def resume_orb_if_sealed():
    """After a load: if the cavern is sealed and not yet escaped, drop the
    player back into the orb (a fresh castle if none is in progress)."""
    if getattr(gs, "cavern_sealed", False) and not getattr(gs, "orb_escaped", False):
        if not gs.orb_game:
            gs.orb_game = {"screen": "intro", "log": [], "castle": None,
                           "seen": [], "player": None, "monster": None,
                           "turns": 0, "code_entry": ""}
        gs.prompt_cntl = "orb_game"
        return True
    return False


# ---------------------------------------------------------------------------
# Input dispatch
# ---------------------------------------------------------------------------

def process_orb_command(app, cmd):
    g = gs.orb_game
    if g is None:
        # Defensive: shouldn't happen, but never hard-lock the player.
        begin_orb_endgame(gs.player_character)
        return
    screen = g.get("screen", "intro")

    handler = {
        "intro": _cmd_intro,
        "setup_race": _cmd_setup_race,
        "setup_stats": _cmd_setup_stats,
        "setup_shop": _cmd_setup_shop,
        "play": _cmd_play,
        "combat": _cmd_combat,
        "vendor": _cmd_vendor,
        "death": _cmd_death,
        "won": _cmd_won,
        "escape_lock": _cmd_escape_lock,
        "escaped": _cmd_escaped,
    }.get(screen)

    if handler:
        handler(g, cmd)


def _cmd_intro(g, cmd):
    if cmd == "o_enter":
        ng = _new_castle_state("setup_race")
        ng["screen"] = "setup_race"
        gs.orb_game = ng
        _log(ng, "You drift inside the Orb of Zot...")
        _log(ng, "A castle of impossible geometry unfolds around you.")


def _cmd_setup_race(g, cmd):
    if cmd.startswith("o_race_"):
        race = cmd[len("o_race_"):]
        if race in RACES:
            p = g["player"]
            bonus = RACES[race][1]
            p["race"] = race
            p["st"] = ATTR_BASE + bonus["st"]
            p["iq"] = ATTR_BASE + bonus["iq"]
            p["dx"] = ATTR_BASE + bonus["dx"]
            p["other_points"] = bonus["other"]
            g["screen"] = "setup_stats"


def _cmd_setup_stats(g, cmd):
    p = g["player"]
    if cmd.startswith("o_stat_up_") and p["other_points"] > 0:
        attr = cmd[len("o_stat_up_"):]
        if attr in ("st", "iq", "dx") and p[attr] < ATTR_MAX:
            p[attr] += 1
            p["other_points"] -= 1
    elif cmd.startswith("o_stat_dn_"):
        attr = cmd[len("o_stat_dn_"):]
        bonus = RACES[p["race"]][1]
        floor = ATTR_BASE + bonus.get(attr, 0)
        if attr in ("st", "iq", "dx") and p[attr] > floor:
            p[attr] -= 1
            p["other_points"] += 1
    elif cmd == "o_sex":
        p["sex"] = "female" if p["sex"] == "male" else "male"
    elif cmd == "o_setup_done":
        g["screen"] = "setup_shop"


def _cmd_setup_shop(g, cmd):
    p = g["player"]
    if cmd.startswith("o_buy_armor_"):
        aid = cmd[len("o_buy_armor_"):]
        if aid in ARMORS:
            cost = ARMORS[aid][1]
            already = ARMORS[p["armor"]][1]
            delta = cost - already
            if p["gold"] >= delta:
                p["gold"] -= delta
                p["armor"] = aid
                p["armor_pts"] = ARMORS[aid][2]
    elif cmd.startswith("o_buy_weapon_"):
        wid = cmd[len("o_buy_weapon_"):]
        if wid in WEAPONS:
            cost = WEAPONS[wid][1]
            already = WEAPONS[p["weapon"]][1]
            delta = cost - already
            if p["gold"] >= delta:
                p["gold"] -= delta
                p["weapon"] = wid
    elif cmd == "o_buy_lamp":
        if not p["lamp"] and p["gold"] >= 20:
            p["gold"] -= 20
            p["lamp"] = True
    elif cmd == "o_buy_flare":
        if p["gold"] >= 1:
            p["gold"] -= 1
            p["flares"] += 1
    elif cmd == "o_buy_flare5":
        n = min(5, p["gold"])
        p["gold"] -= n
        p["flares"] += n
    elif cmd == "o_enter_castle":
        g["screen"] = "play"
        _log(g, "You step through the Entrance. The castle swallows the light.")
        _enter_room(g, first=True)


# ----- main exploration -----

def _move(g, dx, dy):
    """Toroidal step. Returns False if the move is blocked (entrance exit)."""
    p = g["player"]
    # Leaving via the Entrance (stepping North off level 1).
    if (p["x"], p["y"], p["z"]) == ENTRANCE and (dx, dy) == (0, -1):
        if p["orb"]:
            _win_castle(g)
            return True
        else:
            _log(g, "A force bars the gate. You may not leave without the Orb of Zot!")
            return False
    p["x"] = (p["x"] - 1 + dx) % SIZE + 1
    p["y"] = (p["y"] - 1 + dy) % SIZE + 1
    _after_step(g)
    _enter_room(g)
    return True


def _after_step(g):
    """Per-step curse upkeep + map discovery."""
    p = g["player"]
    g["turns"] += 1
    _see(g, p["x"], p["y"], p["z"])
    if p["curses"]["leech"] and p["gold"] > 0:
        drain = min(p["gold"], random.randint(1, 2))
        p["gold"] -= drain
        _log(g, f"The Leech feeds — {drain} gold gone.")
    if p["curses"]["forgetful"] and random.random() < 0.15 and len(g["seen"]) > 1:
        forget = random.choice([k for k in g["seen"] if k != _key(p["x"], p["y"], p["z"])])
        if forget in g["seen"]:
            g["seen"].remove(forget)


def _enter_room(g, first=False):
    """Resolve whatever the player just stepped onto."""
    p = g["player"]
    room = _here(g)
    t = room["t"]

    # Hidden curse on an otherwise-quiet room.
    curse = room.get("curse")
    if curse and not p["curses"][curse]:
        cure_treasure = {"lethargy": RUBY_RED, "leech": PALE_PEARL,
                         "forgetful": GREEN_GEM}[curse]
        if cure_treasure not in p["treasures"]:
            p["curses"][curse] = True
            names = {"lethargy": "Lethargy", "leech": "the Leech",
                     "forgetful": "Forgetfulness"}
            _log(g, f"A chill creeps in... you are cursed with {names[curse]}!")

    if t == "entrance":
        if not first:
            _log(g, "You stand at the Entrance to the castle.")
    elif t == "empty":
        pass
    elif t == "stairs_down":
        _log(g, "Here are stairs leading down.")
    elif t == "stairs_up":
        _log(g, "Here are stairs leading up.")
    elif t == "pool":
        _log(g, "You come upon a shimmering pool.")
    elif t == "chest":
        _log(g, "There is a large chest here.")
    elif t == "book":
        _log(g, "A dusty book rests on a lectern.")
    elif t == "crystal":
        _log(g, "A crystal orb glows on a pedestal.")
    elif t == "vendor":
        _log(g, "A Vendor beckons you over to trade.")
        g["screen"] = "vendor"
    elif t == "gold":
        amt = random.randint(5, 60)
        p["gold"] += amt
        _log(g, f"You found {amt} gold pieces!")
        g["castle"][_key(p['x'], p['y'], p['z'])] = {"t": "empty"}
    elif t == "flares":
        amt = random.randint(2, 10)
        p["flares"] += amt
        _log(g, f"You found {amt} flares!")
        g["castle"][_key(p['x'], p['y'], p['z'])] = {"t": "empty"}
    elif t == "treasure":
        _pickup_treasure(g, room["name"])
        g["castle"][_key(p['x'], p['y'], p['z'])] = {"t": "empty"}
    elif t == "sinkhole":
        _log(g, "The floor gives way — you plunge through a sinkhole!")
        p["z"] = p["z"] % SIZE + 1
        _see(g, p["x"], p["y"], p["z"])
        _enter_room(g)
    elif t == "warp":
        _resolve_warp(g, room)
    elif t == "monster":
        _start_combat(g, room["name"], room.get("rune", False))


def _pickup_treasure(g, name):
    p = g["player"]
    if name in p["treasures"]:
        return
    p["treasures"].append(name)
    _log(g, f"You found {name}!")
    cure = TREASURES[name][1]
    if cure == "blind" and p["blind"]:
        p["blind"] = False
        _log(g, "The Opal Eye restores your sight!")
    elif cure == "book_stuck" and p["book_stuck"]:
        p["book_stuck"] = False
        _log(g, "The Blue Flame burns the book from your hands!")
    elif cure in ("lethargy", "leech", "forgetful") and p["curses"].get(cure):
        p["curses"][cure] = False
        names = {"lethargy": "Lethargy", "leech": "the Leech",
                 "forgetful": "Forgetfulness"}
        _log(g, f"The {name} lifts {names[cure]} from you!")


def _resolve_warp(g, room):
    p = g["player"]
    if room.get("orb") and not p["orb"]:
        p["orb"] = True
        room.pop("orb", None)
        _log(g, "*** A blazing sphere hangs in the void: THE ORB OF ZOT! ***")
        _log(g, "It is yours. Now bear it back to the Entrance and leave!")
        return
    # An ordinary warp flings you elsewhere.
    if p["orb"] and random.random() < 0.25:
        p["orb"] = False
        # Hide the orb again in a fresh deep warp / room.
        deep = [k for k in g["castle"] if int(k.split(",")[2]) >= 5]
        target = random.choice(deep)
        if g["castle"][target]["t"] == "warp":
            g["castle"][target]["orb"] = True
        else:
            g["castle"][target] = {"t": "warp", "orb": True}
        _log(g, "The warp wrenches the Orb of Zot from your grasp! It is gone...")
    p["x"] = random.randint(1, SIZE)
    p["y"] = random.randint(1, SIZE)
    p["z"] = random.randint(1, SIZE)
    _log(g, "The warp scrambles reality — you are flung to a new room!")
    _see(g, p["x"], p["y"], p["z"])
    _enter_room(g)


def _cmd_play(g, cmd):
    p = g["player"]
    if cmd == "o_n":
        _move(g, 0, -1)
    elif cmd == "o_s":
        _move(g, 0, 1)
    elif cmd == "o_e":
        _move(g, 1, 0)
    elif cmd == "o_w":
        _move(g, -1, 0)
    elif cmd == "o_down":
        if _here(g)["t"] == "stairs_down":
            p["z"] += 1
            _log(g, "You descend the stairs.")
            _after_step(g)
            _enter_room(g)
        else:
            _log(g, "There are no stairs down here.")
    elif cmd == "o_up":
        if _here(g)["t"] == "stairs_up":
            p["z"] -= 1
            _log(g, "You climb the stairs.")
            _after_step(g)
            _enter_room(g)
        else:
            _log(g, "There are no stairs up here.")
    elif cmd == "o_drink":
        if _here(g)["t"] == "pool":
            _drink_pool(g)
        else:
            _log(g, "There is no pool here to drink from.")
    elif cmd == "o_open":
        t = _here(g)["t"]
        if t == "chest":
            _open_chest(g)
        elif t == "book":
            _read_book(g)
        else:
            _log(g, "There is nothing here to open.")
    elif cmd == "o_gaze":
        if _here(g)["t"] == "crystal":
            _gaze_orb(g)
        else:
            _log(g, "There is no crystal orb here.")
    elif cmd == "o_flare":
        _light_flare(g)
    elif cmd.startswith("o_lamp_"):
        _shine_lamp(g, cmd[len("o_lamp_"):])
    elif cmd == "o_forfeit":
        # Give up on this castle; wake in the chamber for a fresh attempt.
        g["screen"] = "death"
        g["forfeit"] = True
        _log(g, "You release your grip on this castle and drift back to the chamber.")


def _drink_pool(g):
    p = g["player"]
    roll = random.randint(1, 11)
    if roll == 1:
        _log(g, "The water is cool and refreshing. Nothing happens.")
    elif roll == 2:
        n = random.randint(1, 3); _set_attr(g, "st", p["st"] + n)
        _log(g, f"You feel stronger! (+{n} Strength)")
    elif roll == 3:
        n = random.randint(1, 2)
        _set_attr(g, "st", p["st"] - n)
        _log(g, f"Ugh, foul water. (-{n} Strength)")
        _check_death(g)
    elif roll == 4:
        n = random.randint(1, 3); _set_attr(g, "iq", p["iq"] + n)
        _log(g, f"Your mind sharpens! (+{n} Intelligence)")
    elif roll == 5:
        n = random.randint(1, 2); _set_attr(g, "iq", p["iq"] - n)
        _log(g, f"You feel foggy. (-{n} Intelligence)")
    elif roll == 6:
        n = random.randint(1, 3); _set_attr(g, "dx", p["dx"] + n)
        _log(g, f"You feel nimble! (+{n} Dexterity)")
    elif roll == 7:
        n = random.randint(1, 2); _set_attr(g, "dx", p["dx"] - n)
        _log(g, f"You feel clumsy. (-{n} Dexterity)")
    elif roll == 8:
        new = random.choice([r for r in RACES if r != p["race"]])
        p["race"] = new
        _log(g, f"You feel strange... you are now a {RACES[new][0]}!")
    elif roll == 9:
        p["sex"] = "female" if p["sex"] == "male" else "male"
        _log(g, f"How odd — you are now {p['sex']}!")
    elif roll == 10:
        _reveal_treasure_vision(g)
    else:
        gold = random.randint(10, 80); p["gold"] += gold
        _log(g, f"The pool sparkles with coins — you scoop up {gold} gold!")


def _open_chest(g):
    p = g["player"]
    g["castle"][_key(p["x"], p["y"], p["z"])] = {"t": "empty"}
    roll = random.randint(1, 6)
    if roll <= 2:
        gold = random.randint(20, 120); p["gold"] += gold
        _log(g, f"The chest is full of treasure — {gold} gold!")
    elif roll == 3:
        dmg = random.randint(1, 6)
        _take_damage(g, dmg)
        _log(g, f"KABOOM! The chest explodes for {dmg} damage!")
        _check_death(g)
    elif roll == 4:
        _log(g, "GAS! You choke and are teleported away!")
        p["x"] = random.randint(1, SIZE); p["y"] = random.randint(1, SIZE)
        _see(g, p["x"], p["y"], p["z"]); _enter_room(g)
    elif roll == 5:
        _log(g, "A Kobold leaps out of the chest!")
        _start_combat(g, "Kobold", False)
    else:
        _log(g, "The chest is empty but for cobwebs.")


def _read_book(g):
    p = g["player"]
    g["castle"][_key(p["x"], p["y"], p["z"])] = {"t": "empty"}
    roll = random.randint(1, 7)
    if roll == 1:
        _log(g, "It's another volume of Zot's poetry. Yeech!")
    elif roll == 2:
        _log(g, "It's an old issue of Play-Elf magazine. Hubba hubba.")
    elif roll == 3:
        _set_attr(g, "st", ATTR_MAX)
        _log(g, "It's a manual of Strength! (Strength now 18)")
    elif roll == 4:
        _set_attr(g, "iq", ATTR_MAX)
        _log(g, "It's a tome of Intelligence! (Intelligence now 18)")
    elif roll == 5:
        _set_attr(g, "dx", ATTR_MAX)
        _log(g, "It's a manual of Dexterity! (Dexterity now 18)")
    elif roll == 6:
        p["book_stuck"] = True
        _log(g, "It's a sticky book — now your hands are stuck to it! (Find the Blue Flame.)")
    else:
        p["blind"] = True
        _log(g, "FLASH! The book blinds you! (Find the Opal Eye.)")


def _gaze_orb(g):
    p = g["player"]
    roll = random.randint(1, 6)
    if roll == 1:
        _log(g, "You see yourself in a bloody heap. Charming.")
    elif roll == 2:
        mon = random.choice(MONSTERS)[0]
        _log(g, f"You see a {mon} gnawing on a bone.")
    elif roll == 3:
        _reveal_treasure_vision(g)
    elif roll == 4:
        # A vision of the Orb of Zot — true half the time.
        orb_loc = _find_orb(g)
        if orb_loc and random.random() < 0.5:
            x, y, z = orb_loc
            _see(g, x, y, z)
            _log(g, f"You see the ORB OF ZOT at ({x},{y}) on level {z}!")
        else:
            x, y, z = (random.randint(1, SIZE), random.randint(1, SIZE), random.randint(1, SIZE))
            _log(g, f"You see the Orb of Zot at ({x},{y}) level {z}... or do you? (a trick!)")
    elif roll == 5:
        _log(g, "You see a soap-opera rerun. Riveting.")
    else:
        _log(g, "You see a Vendor counting an enormous pile of gold.")


def _reveal_treasure_vision(g):
    castle = g["castle"]
    treas = [(k, r["name"]) for k, r in castle.items() if r["t"] == "treasure"]
    if not treas:
        _log(g, "You see only swirling mist. (All treasures are claimed.)")
        return
    k, name = random.choice(treas)
    x, y, z = map(int, k.split(","))
    _see(g, x, y, z)
    _log(g, f"A vision: the {name} lies at ({x},{y}) on level {z}.")


def _find_orb(g):
    for k, r in g["castle"].items():
        if r.get("orb"):
            return tuple(map(int, k.split(",")))
    return None


def _light_flare(g):
    p = g["player"]
    if p["flares"] <= 0:
        _log(g, "You have no flares!")
        return
    if p["blind"]:
        _log(g, "You're blind — the flare does you no good.")
        return
    p["flares"] -= 1
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            x = (p["x"] - 1 + dx) % SIZE + 1
            y = (p["y"] - 1 + dy) % SIZE + 1
            _see(g, x, y, p["z"])
    _log(g, "The flare flares bright, revealing the rooms around you!")


def _shine_lamp(g, direction):
    p = g["player"]
    if not p["lamp"]:
        _log(g, "You don't have a lamp!")
        return
    if p["blind"]:
        _log(g, "You're blind — the lamp is useless.")
        return
    deltas = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
    if direction not in deltas:
        return
    dx, dy = deltas[direction]
    x = (p["x"] - 1 + dx) % SIZE + 1
    y = (p["y"] - 1 + dy) % SIZE + 1
    _see(g, x, y, p["z"])
    room = g["castle"][_key(x, y, p["z"])]
    _log(g, f"You shine the lamp {direction.upper()}: {_room_name(room)}.")


def _room_name(room):
    t = room["t"]
    if t == "monster":
        return f"a {room['name']}"
    if t == "treasure":
        return f"the {room['name']}"
    return {
        "entrance": "the Entrance", "empty": "an empty room",
        "stairs_down": "stairs down", "stairs_up": "stairs up",
        "pool": "a pool", "chest": "a chest", "gold": "gold pieces",
        "flares": "flares", "warp": "a warp", "sinkhole": "a sinkhole",
        "crystal": "a crystal orb", "book": "a book", "vendor": "a Vendor",
    }.get(t, "something")


# ----- attribute / damage helpers -----

def _set_attr(g, attr, value):
    g["player"][attr] = max(0, min(ATTR_MAX, value))


def _take_damage(g, dmg):
    """Apply damage, absorbed first by armor, then by Strength (= HP)."""
    p = g["player"]
    if p["armor_pts"] > 0:
        absorbed = min(dmg, p["armor_pts"])
        p["armor_pts"] -= absorbed
        dmg -= absorbed
    if dmg > 0:
        p["st"] = max(0, p["st"] - dmg)


def _check_death(g):
    p = g["player"]
    if p["st"] <= 0:
        g["screen"] = "death"
        g["monster"] = None
        _log(g, "Your Strength fails utterly. You crumble to dust...")
        return True
    return False


# ----- combat -----

def _start_combat(g, name, rune):
    tier = MONSTER_TIER.get(name, 1)
    g["monster"] = {
        "name": name, "tier": tier,
        "hp": tier + random.randint(1, 3),
        "max_hp": tier + 3,
        "rune": rune, "web": 0, "bribed": False,
    }
    g["screen"] = "combat"
    _log(g, f"You have encountered a {name}!")


def _player_weapon_damage(g):
    wid = g["player"]["weapon"]
    tier = WEAPONS[wid][2]
    if tier == 0:
        return random.randint(1, 2)  # bare hands
    return random.randint(1, 3) + tier * 2


def _monster_attacks(g):
    p = g["player"]
    m = g["monster"]
    if m["web"] > 0:
        m["web"] -= 1
        _log(g, f"The {m['name']} struggles against the web!")
        return
    swings = 1
    if p["curses"]["lethargy"] and random.random() < 0.5:
        swings = 2  # lethargy lets the monster press its advantage
    for _ in range(swings):
        if m["hp"] <= 0:
            break
        dmg = random.randint(1, m["tier"] + 1)
        _take_damage(g, dmg)
        _log(g, f"The {m['name']} hits you for {dmg}!")
        if _check_death(g):
            return


def _end_combat_victory(g):
    p = g["player"]
    m = g["monster"]
    _log(g, f"You have slain the {m['name']}!")
    if m["rune"] and not p["runestaff"]:
        p["runestaff"] = True
        _log(g, "*** It clutched the RUNESTAFF — now it is yours! ***")
    if random.random() < 0.4:
        gold = random.randint(5, 40); p["gold"] += gold
        _log(g, f"You loot {gold} gold from its corpse.")
    g["castle"][_key(p["x"], p["y"], p["z"])] = {"t": "empty"}
    g["monster"] = None
    g["screen"] = "play"


def _cmd_combat(g, cmd):
    p = g["player"]
    m = g["monster"]
    if not m:
        g["screen"] = "play"
        return

    if cmd == "o_atk":
        if p["book_stuck"]:
            _log(g, "Your hands are stuck to a book — you can barely fight! (-2 hit)")
        hit_roll = random.randint(1, 20) + p["dx"] // 3 - (2 if p["book_stuck"] else 0)
        if hit_roll >= 10:
            dmg = _player_weapon_damage(g)
            m["hp"] -= dmg
            _log(g, f"You strike the {m['name']} for {dmg}!")
            # Tough hides shatter weak weapons.
            if m["name"] in ("Gargoyle", "Dragon") and p["weapon"] != "none" \
                    and random.random() < 0.15:
                _log(g, f"Your {WEAPONS[p['weapon']][0]} shatters on the {m['name']}!")
                p["weapon"] = "none"
            if m["hp"] <= 0:
                _end_combat_victory(g)
                return
        else:
            _log(g, f"You swing at the {m['name']} and miss!")
        _monster_attacks(g)

    elif cmd == "o_bribe":
        if m["bribed"]:
            return
        if p["treasures"]:
            given = p["treasures"].pop(0)
            _log(g, f"You bribe the {m['name']} with the {given}. It lets you pass.")
            g["castle"][_key(p["x"], p["y"], p["z"])] = {"t": "empty"}
            g["monster"] = None
            g["screen"] = "play"
        else:
            _log(g, "You have no treasure to bribe with! The monster attacks!")
            _monster_attacks(g)

    elif cmd == "o_retreat":
        g["pending_retreat"] = True
        _log(g, "Retreat which way? Choose a direction.")

    elif cmd in ("o_n", "o_s", "o_e", "o_w") and g.get("pending_retreat"):
        g["pending_retreat"] = False
        _monster_attacks(g)  # free swing as you turn to flee
        if _check_death(g):
            return
        g["monster"] = None
        g["screen"] = "play"
        deltas = {"o_n": (0, -1), "o_s": (0, 1), "o_e": (1, 0), "o_w": (-1, 0)}
        dx, dy = deltas[cmd]
        _move(g, dx, dy)

    elif cmd == "o_cast_web":
        if p["book_stuck"]:
            _log(g, "Your hands are stuck — you cannot gesture the spell!")
            return
        if p["iq"] < 10:
            _log(g, "Your mind isn't keen enough to weave the Web spell.")
            _monster_attacks(g)
            return
        m["web"] = 2
        _log(g, f"You cast WEB! The {m['name']} is ensnared!")
        _monster_attacks(g)

    elif cmd == "o_cast_fire":
        if p["book_stuck"]:
            _log(g, "Your hands are stuck — you cannot gesture the spell!")
            return
        if p["iq"] < 12 or p["st"] < 2:
            _log(g, "You lack the Intelligence or Strength to hurl a Fireball.")
            _monster_attacks(g)
            return
        _set_attr(g, "st", p["st"] - 1)
        dmg = random.randint(2, 7) + p["iq"] // 4
        m["hp"] -= dmg
        _log(g, f"You hurl a FIREBALL for {dmg}!")
        if m["hp"] <= 0:
            _end_combat_victory(g)
            return
        _monster_attacks(g)

    elif cmd == "o_cast_death":
        if p["book_stuck"]:
            _log(g, "Your hands are stuck — you cannot gesture the spell!")
            return
        if p["iq"] >= 15 or p["runestaff"]:
            _log(g, "You speak the DEATHSPELL. The monster simply ceases to be.")
            m["hp"] = 0
            _end_combat_victory(g)
            return
        else:
            _log(g, "DEATHSPELL backfires! Your mind was too weak — it claims YOU!")
            p["st"] = 0
            _check_death(g)


# ----- vendor -----

def _cmd_vendor(g, cmd):
    p = g["player"]
    if cmd == "o_leave_v":
        g["screen"] = "play"
        _log(g, "You wave the Vendor off and move on.")
    elif cmd == "o_v_heal":
        # Vendors mend you (sell Strength) for gold.
        if p["gold"] >= 50 and p["st"] < ATTR_MAX:
            p["gold"] -= 50
            _set_attr(g, "st", p["st"] + random.randint(2, 5))
            _log(g, "The Vendor pours a healing draught down your throat. (+Strength)")
        else:
            _log(g, "You can't afford the Vendor's healing, or you're hale already.")
    elif cmd.startswith("o_v_buy_armor_"):
        _cmd_setup_shop(g, "o_buy_armor_" + cmd[len("o_v_buy_armor_"):])
    elif cmd.startswith("o_v_buy_weapon_"):
        _cmd_setup_shop(g, "o_buy_weapon_" + cmd[len("o_v_buy_weapon_"):])
    elif cmd == "o_v_buy_lamp":
        _cmd_setup_shop(g, "o_buy_lamp")
    elif cmd.startswith("o_v_sell_"):
        idx = cmd[len("o_v_sell_"):]
        try:
            i = int(idx)
        except ValueError:
            return
        if 0 <= i < len(p["treasures"]):
            name = p["treasures"][i]
            # Vendors lowball — half the listed value.
            price = TREASURES[name][0] // 2
            p["gold"] += price
            p["treasures"].pop(i)
            _log(g, f"You sell the {name} for {price} gold.")
    elif cmd == "o_v_attack":
        _log(g, "You attack the Vendor! Now he's MAD!")
        g["castle"][_key(p["x"], p["y"], p["z"])] = {"t": "monster", "name": "Vendor", "rune": False}
        # A furious vendor is a brutal fight.
        g["monster"] = {"name": "Mad Vendor", "tier": 9,
                        "hp": 15 + random.randint(0, 6), "max_hp": 21,
                        "rune": False, "web": 0, "bribed": False}
        g["screen"] = "combat"


# ----- death / win / escape -----

def _cmd_death(g, cmd):
    if cmd == "o_reenter":
        ng = _new_castle_state("setup_race")
        gs.orb_game = ng
        _log(ng, "You re-enter the Orb. A new castle weaves itself from the dark.")


def _win_castle(g):
    g["screen"] = "won"
    code = _gen_code()
    gs.orb_escape_code = code
    g["log"].append("")
    _log(g, "*** YOU WALK OUT THE ENTRANCE BEARING THE ORB OF ZOT! ***")
    _log(g, "*** YOU HAVE WON THE WIZARD'S CASTLE! ***")
    _log(g, "The orb dissolves. A Word of Passage burns itself into your mind.")


def _cmd_won(g, cmd):
    if cmd == "o_approach":
        g["screen"] = "escape_lock"
        g["code_entry"] = ""


def _cmd_escape_lock(g, cmd):
    code = gs.orb_escape_code or ""
    if cmd.startswith("o_code_") and cmd != "o_code_bs" and cmd != "o_code_submit":
        ch = cmd[len("o_code_"):]
        if len(g["code_entry"]) < len(code):
            g["code_entry"] += ch
    elif cmd == "o_code_bs":
        g["code_entry"] = g["code_entry"][:-1]
    elif cmd == "o_code_submit":
        if g["code_entry"] == code:
            g["screen"] = "escaped"
            gs.orb_escaped = True
            _log(g, "The sealed door grinds open. Daylight!")
            _grant_escape_rewards()
        else:
            _log(g, "The runes do not align. The door stays shut. (Try again.)")
            g["code_entry"] = ""


def _grant_escape_rewards():
    try:
        from .achievements import check_achievements
        check_achievements(gs.player_character)
    except Exception:
        pass
    try:
        gs.game_stats["cavern_escaped"] = True
    except Exception:
        pass


def _cmd_escaped(g, cmd):
    if cmd == "o_finish":
        gs.game_should_quit = True


# ===========================================================================
# Rendering
# ===========================================================================

def _chip(cmd, label, bg="#2a2a3a", fg="#EEE", border="#556"):
    return (
        f"<div data-zcmd='{cmd}' onclick=\"window.__zotTap('{cmd}', this)\" "
        f"style=\"display:inline-block; margin:3px; padding:8px 12px; "
        f"background:{bg}; color:{fg}; border:1px solid {border}; "
        f"border-radius:5px; font-family:monospace; font-size:13px; "
        f"cursor:pointer; user-select:none;\">{label}</div>"
    )


def _panel_open(extra=""):
    return (
        "<div style=\"font-family:monospace; min-height:80vh; "
        "background:linear-gradient(180deg,#0a0a14,#05050a); color:#cfd2e0; "
        f"padding:12px 12px 24px; border-radius:6px; {extra}\">"
    )


def _log_html(g, n=8):
    lines = g["log"][-n:]
    rows = "".join(
        f"<div style='margin:1px 0; color:#b8bcd0;'>{_esc(l)}</div>" if l else "<div style='height:6px;'></div>"
        for l in lines
    )
    return (
        "<div style=\"background:rgba(0,0,0,0.4); border:1px solid #223; "
        "border-radius:4px; padding:8px 10px; margin:8px 0; min-height:120px; "
        "font-size:12.5px; line-height:1.35;\">" + rows + "</div>"
    )


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_orb_html(app):
    g = gs.orb_game
    if g is None:
        return _panel_open() + "<div>The Orb of Zot flickers...</div></div>"
    screen = g.get("screen", "intro")
    renderer = {
        "intro": _render_intro,
        "setup_race": _render_setup_race,
        "setup_stats": _render_setup_stats,
        "setup_shop": _render_setup_shop,
        "play": _render_play,
        "combat": _render_combat,
        "vendor": _render_vendor,
        "death": _render_death,
        "won": _render_won,
        "escape_lock": _render_escape_lock,
        "escaped": _render_escaped,
    }.get(screen, _render_intro)
    return renderer(g)


def _header(title, sub=""):
    sub_html = f"<div style='font-size:12px; color:#8a8fb0; margin-top:2px;'>{sub}</div>" if sub else ""
    return (
        f"<div style='text-align:center; margin-bottom:8px;'>"
        f"<div style='font-size:18px; color:#ffd24a; letter-spacing:2px; "
        f"text-shadow:0 0 10px rgba(255,210,74,0.4);'>{title}</div>{sub_html}</div>"
    )


def _render_intro(g):
    html = _panel_open()
    html += _header("THE ORB OF ZOT")
    html += (
        "<div style='max-width:420px; margin:6px auto; font-size:13.5px; "
        "line-height:1.5; color:#cfd2e0;'>"
        "<p>The Guardian falls. The Orb of Zot floats into your hands, "
        "warm and impossibly heavy &mdash; and behind you, with a sound like "
        "a mountain closing its eye, <b>the cavern seals shut.</b></p>"
        "<p>There is no door now. No stair. Only the orb, and within it, "
        "a castle of eight floors and eight halls &mdash; the legendary "
        "<b>Wizard's Castle</b>, whose only prize was ever the Orb of Zot "
        "itself.</p>"
        "<p>Find the Orb <i>inside</i> the orb. Carry it out the Entrance. "
        "The castle will give up the <b>Word of Passage</b> that unseals "
        "the cavern. Lose yourself, and you simply wake here, to try again.</p>"
        "</div>"
    )
    html += "<div style='text-align:center; margin-top:14px;'>"
    html += _chip("o_enter", "Enter the Orb", bg="#3a2a5a", fg="#ffd24a", border="#7a5")
    html += "</div></div>"
    return html


def _render_setup_race(g):
    html = _panel_open()
    html += _header("WIZARD'S CASTLE", "Choose your kind, bold one")
    html += (
        "<div style='max-width:420px; margin:6px auto; font-size:12.5px; color:#aab;'>"
        "Each race begins differently. Dwarves are mighty (+Strength); Elves "
        "quick and clever (+Dex, +Int); Hobbits deft (+Dex); Humans flexible "
        "(more points to spend).</div>"
    )
    html += "<div style='text-align:center; margin-top:12px;'>"
    for rid, (label, bonus) in RACES.items():
        b = bonus
        meta = []
        if b["st"]: meta.append(f"+{b['st']} ST")
        if b["iq"]: meta.append(f"+{b['iq']} IQ")
        if b["dx"]: meta.append(f"+{b['dx']} DX")
        meta.append(f"{b['other']} pts")
        html += _chip(f"o_race_{rid}", f"{label}<br><span style='font-size:10px;color:#9a9;'>{', '.join(meta)}</span>")
    html += "</div></div>"
    return html


def _render_setup_stats(g):
    p = g["player"]
    html = _panel_open()
    html += _header("ATTRIBUTES", f"{RACES[p['race']][0]} &mdash; spend your points")
    html += (
        f"<div style='text-align:center; font-size:13px; margin:8px 0;'>"
        f"Points to spend: <b style='color:#ffd24a;'>{p['other_points']}</b> "
        f"(max {ATTR_MAX} each)</div>"
    )
    html += "<div style='max-width:340px; margin:0 auto;'>"
    for attr, name in (("st", "Strength"), ("iq", "Intelligence"), ("dx", "Dexterity")):
        html += (
            "<div style='display:flex; align-items:center; justify-content:space-between; "
            "margin:6px 0; background:rgba(0,0,0,0.3); padding:6px 10px; border-radius:4px;'>"
            f"<span style='width:120px;'>{name}</span>"
            f"<span style='font-size:16px; color:#ffd24a; width:36px; text-align:center;'>{p[attr]}</span>"
            f"<span>{_chip('o_stat_dn_' + attr, '&minus;', bg='#402')}"
            f"{_chip('o_stat_up_' + attr, '&plus;', bg='#240')}</span>"
            "</div>"
        )
    html += "</div>"
    html += "<div style='text-align:center; margin-top:10px;'>"
    html += _chip("o_sex", f"Sex: {p['sex'].title()}", bg="#234")
    html += _chip("o_setup_done", "To the Vendor &raquo;", bg="#3a2a5a", fg="#ffd24a", border="#7a5")
    html += "</div></div>"
    return html


def _render_setup_shop(g):
    p = g["player"]
    html = _panel_open()
    html += _header("OUTFITTING", "Spend your gold before you descend")
    html += f"<div style='text-align:center; margin:6px 0; font-size:14px;'>Gold: <b style='color:#ffd24a;'>{p['gold']}</b></div>"

    html += "<div style='max-width:420px; margin:0 auto;'>"
    html += "<div style='color:#9ab; font-size:12px; margin-top:8px;'>Armor (current: " + ARMORS[p['armor']][0] + ")</div>"
    for aid, (label, cost, _v) in ARMORS.items():
        sel = " &check;" if p['armor'] == aid else ""
        html += _chip(f"o_buy_armor_{aid}", f"{label} ({cost}g){sel}", bg="#243" if p['armor'] == aid else "#223")
    html += "<div style='color:#9ab; font-size:12px; margin-top:8px;'>Weapon (current: " + WEAPONS[p['weapon']][0] + ")</div>"
    for wid, (label, cost, _v) in WEAPONS.items():
        sel = " &check;" if p['weapon'] == wid else ""
        html += _chip(f"o_buy_weapon_{wid}", f"{label} ({cost}g){sel}", bg="#243" if p['weapon'] == wid else "#223")
    html += "<div style='color:#9ab; font-size:12px; margin-top:8px;'>Sundries</div>"
    lamp_lbl = "Lamp (owned)" if p['lamp'] else "Lamp (20g)"
    html += _chip("o_buy_lamp", lamp_lbl, bg="#243" if p['lamp'] else "#223")
    html += _chip("o_buy_flare", "Flare +1 (1g)", bg="#223")
    html += _chip("o_buy_flare5", "Flares +5 (5g)", bg="#223")
    html += f"<div style='font-size:12px; color:#9ab; margin-top:4px;'>Flares: {p['flares']}</div>"
    html += "</div>"

    html += "<div style='text-align:center; margin-top:14px;'>"
    html += _chip("o_enter_castle", "Enter the Castle", bg="#3a2a5a", fg="#ffd24a", border="#7a5")
    html += "</div></div>"
    return html


def _stat_bar(g):
    p = g["player"]
    flags = []
    if p["blind"]: flags.append("<span style='color:#f66;'>BLIND</span>")
    if p["book_stuck"]: flags.append("<span style='color:#f96;'>BOOK-STUCK</span>")
    if p["curses"]["lethargy"]: flags.append("<span style='color:#f6f;'>LETHARGY</span>")
    if p["curses"]["leech"]: flags.append("<span style='color:#6f6;'>LEECH</span>")
    if p["curses"]["forgetful"]: flags.append("<span style='color:#fd6;'>FORGETFUL</span>")
    if p["runestaff"]: flags.append("<span style='color:#9cf;'>RUNESTAFF</span>")
    if p["orb"]: flags.append("<span style='color:#ffd24a;'>ORB OF ZOT</span>")
    flag_html = (" &middot; " + " ".join(flags)) if flags else ""
    return (
        "<div style='font-size:12px; background:#11131f; padding:5px 8px; "
        "border-radius:3px; line-height:1.5;'>"
        f"<b>{RACES[p['race']][0]}</b> &middot; "
        f"ST <b style='color:#f88;'>{p['st']}</b> "
        f"IQ <b style='color:#8cf;'>{p['iq']}</b> "
        f"DX <b style='color:#8f8;'>{p['dx']}</b> &middot; "
        f"{p['gold']}g &middot; {p['flares']} flares &middot; "
        f"{WEAPONS[p['weapon']][0]} / {ARMORS[p['armor']][0]} "
        f"(arm {p['armor_pts']})"
        f"<br>Treasures: {len(p['treasures'])}/8{flag_html}"
        "</div>"
    )


def _minimap(g):
    p = g["player"]
    z = p["z"]
    rows = []
    for y in range(1, SIZE + 1):
        cells = []
        for x in range(1, SIZE + 1):
            k = _key(x, y, z)
            if x == p["x"] and y == p["y"]:
                glyph, color, bg = "@", "#000", "#ffd24a"
            elif p["blind"]:
                glyph, color, bg = "?", "#445", "transparent"
            elif k in g["seen"]:
                room = g["castle"][k]
                glyph = GLYPHS.get(room["t"], "?")
                if room.get("orb"):
                    glyph = "!"
                color = "#cdd"
                bg = "transparent"
                if room["t"] == "monster": color = "#f88"
                elif room["t"] == "treasure": color = "#fd6"
                elif room["t"] in ("stairs_down", "stairs_up"): color = "#8cf"
                elif room.get("orb"): color = "#ffd24a"
            else:
                glyph, color, bg = "?", "#445", "transparent"
            cells.append(
                f"<span style='display:inline-block; width:20px; height:20px; "
                f"line-height:20px; text-align:center; color:{color}; "
                f"background:{bg}; border-radius:2px; font-weight:bold;'>{glyph}</span>"
            )
        rows.append("<div>" + "".join(cells) + "</div>")
    grid = "".join(rows)
    return (
        f"<div style='text-align:center; font-size:13px; color:#9ab; margin:4px 0;'>Level {z} &mdash; ({p['x']},{p['y']})</div>"
        f"<div style='display:inline-block; font-family:monospace; "
        f"background:#08080f; padding:6px; border-radius:4px; border:1px solid #223;'>{grid}</div>"
    )


def _render_play(g):
    p = g["player"]
    room = _here(g)
    html = _panel_open()
    html += _stat_bar(g)
    html += "<div style='text-align:center; margin-top:6px;'>" + _minimap(g) + "</div>"
    html += _log_html(g, n=6)

    # Movement
    html += "<div style='text-align:center;'>"
    html += _chip("o_n", "&#9650; N")
    html += "<br>"
    html += _chip("o_w", "&#9664; W")
    html += _chip("o_e", "E &#9654;")
    html += "<br>"
    html += _chip("o_s", "&#9660; S")
    html += "</div>"

    # Contextual actions
    actions = []
    t = room["t"]
    if t == "stairs_down":
        actions.append(_chip("o_down", "Descend", bg="#234"))
    if t == "stairs_up":
        actions.append(_chip("o_up", "Climb up", bg="#234"))
    if t == "pool":
        actions.append(_chip("o_drink", "Drink", bg="#234"))
    if t == "chest":
        actions.append(_chip("o_open", "Open chest", bg="#234"))
    if t == "book":
        actions.append(_chip("o_open", "Read book", bg="#234"))
    if t == "crystal":
        actions.append(_chip("o_gaze", "Gaze", bg="#234"))
    if p["flares"] > 0:
        actions.append(_chip("o_flare", "Flare", bg="#332"))
    if actions:
        html += "<div style='text-align:center; margin-top:8px;'>" + "".join(actions) + "</div>"

    # Lamp directions
    if p["lamp"]:
        html += ("<div style='text-align:center; margin-top:6px; font-size:11px; color:#9ab;'>Lamp:</div>"
                 "<div style='text-align:center;'>")
        for d, lbl in (("n", "N"), ("s", "S"), ("e", "E"), ("w", "W")):
            html += _chip(f"o_lamp_{d}", f"&#128294;{lbl}", bg="#222", fg="#fd8")
        html += "</div>"

    html += ("<div style='text-align:center; margin-top:12px;'>"
             + _chip("o_forfeit", "Abandon castle", bg="#311", fg="#c88", border="#633")
             + "</div>")
    html += "</div>"
    return html


def _render_combat(g):
    p = g["player"]
    m = g["monster"]
    html = _panel_open()
    html += _stat_bar(g)
    html += _header("COMBAT", f"A {m['name']} blocks your way!")
    # Monster HP bar
    pct = max(0, int(100 * m["hp"] / max(1, m["max_hp"])))
    html += (
        f"<div style='max-width:320px; margin:8px auto;'>"
        f"<div style='font-size:13px; margin-bottom:3px;'>{m['name']} &mdash; "
        f"HP {max(0, m['hp'])}{' &#9876;RUNESTAFF' if m.get('rune') else ''}</div>"
        f"<div style='background:#311; border-radius:4px; height:12px; overflow:hidden;'>"
        f"<div style='width:{pct}%; height:100%; background:#c44;'></div></div></div>"
    )
    html += _log_html(g, n=6)

    if g.get("pending_retreat"):
        html += "<div style='text-align:center;'><div style='font-size:12px;color:#9ab;'>Flee which way?</div>"
        html += _chip("o_n", "&#9650; N") + "<br>"
        html += _chip("o_w", "&#9664; W") + _chip("o_e", "E &#9654;") + "<br>"
        html += _chip("o_s", "&#9660; S")
        html += "</div></div>"
        return html

    html += "<div style='text-align:center; margin-top:8px;'>"
    html += _chip("o_atk", "Attack", bg="#422", fg="#fcc", border="#844")
    html += _chip("o_retreat", "Retreat", bg="#222")
    html += _chip("o_bribe", "Bribe", bg="#332")
    html += "</div>"
    html += "<div style='text-align:center; margin-top:6px; font-size:11px; color:#9ab;'>Spells:</div>"
    html += "<div style='text-align:center;'>"
    html += _chip("o_cast_web", "Web", bg="#234", fg="#9cf")
    html += _chip("o_cast_fire", "Fireball", bg="#234", fg="#f96")
    html += _chip("o_cast_death", "Deathspell", bg="#234", fg="#c9f")
    html += "</div>"
    html += "</div>"
    return html


def _render_vendor(g):
    p = g["player"]
    html = _panel_open()
    html += _stat_bar(g)
    html += _header("THE VENDOR", "He spreads his wares (and eyes your treasures)")
    html += _log_html(g, n=4)
    html += f"<div style='text-align:center; font-size:13px;'>Gold: <b style='color:#ffd24a;'>{p['gold']}</b></div>"

    html += "<div style='max-width:420px; margin:6px auto;'>"
    html += "<div style='color:#9ab; font-size:12px; margin-top:6px;'>Buy armor / weapon / lamp</div>"
    for aid, (label, cost, _v) in ARMORS.items():
        if aid == "none":
            continue
        html += _chip(f"o_v_buy_armor_{aid}", f"{label} ({cost}g)", bg="#223")
    for wid, (label, cost, _v) in WEAPONS.items():
        if wid == "none":
            continue
        html += _chip(f"o_v_buy_weapon_{wid}", f"{label} ({cost}g)", bg="#223")
    if not p["lamp"]:
        html += _chip("o_v_buy_lamp", "Lamp (20g)", bg="#223")
    html += _chip("o_v_heal", "Healing (50g)", bg="#232")

    if p["treasures"]:
        html += "<div style='color:#9ab; font-size:12px; margin-top:8px;'>Sell treasures (half value)</div>"
        for i, name in enumerate(p["treasures"]):
            price = TREASURES[name][0] // 2
            html += _chip(f"o_v_sell_{i}", f"{name} &rarr; {price}g", bg="#232")
    html += "</div>"

    html += "<div style='text-align:center; margin-top:12px;'>"
    html += _chip("o_leave_v", "Leave", bg="#234", fg="#9cf")
    html += _chip("o_v_attack", "Attack the Vendor!", bg="#411", fg="#f99", border="#633")
    html += "</div></div>"
    return html


def _render_death(g):
    html = _panel_open("text-align:center;")
    html += _header("YOU HAVE FALLEN")
    html += (
        "<div style='max-width:400px; margin:10px auto; font-size:13.5px; line-height:1.5;'>"
        "Your body crumbles to dust on the cold flagstones &mdash; but you are "
        "inside the Orb of Zot, and the orb is not so cruel. You wake again in "
        "the sealed chamber, the castle already re-weaving itself in the dark.</div>"
    )
    html += _log_html(g, n=5)
    html += "<div style='margin-top:14px;'>"
    html += _chip("o_reenter", "Re-enter the Orb", bg="#3a2a5a", fg="#ffd24a", border="#7a5")
    html += "</div></div>"
    return html


def _render_won(g):
    code = gs.orb_escape_code or "????"
    html = _panel_open("text-align:center;")
    html += _header("A WINNER IS YOU!", "The Wizard's Castle is conquered")
    html += (
        "<div style='max-width:420px; margin:10px auto; font-size:13.5px; line-height:1.5;'>"
        "You stride out the Entrance, the inner Orb of Zot blazing in your fist. "
        "The castle unravels into motes of light, and from the dissolving stone "
        "a single <b>Word of Passage</b> sears itself into your memory:</div>"
    )
    html += (
        f"<div style='font-size:34px; letter-spacing:10px; color:#ffd24a; "
        f"margin:14px 0; text-shadow:0 0 16px rgba(255,210,74,0.5);'>{code}</div>"
    )
    html += (
        "<div style='max-width:420px; margin:6px auto; font-size:12.5px; color:#aab;'>"
        "Remember it. The sealed cavern will demand the Word before it lets "
        "you go.</div>"
    )
    html += "<div style='margin-top:14px;'>"
    html += _chip("o_approach", "Approach the sealed door", bg="#3a2a5a", fg="#ffd24a", border="#7a5")
    html += "</div></div>"
    return html


def _render_escape_lock(g):
    code = gs.orb_escape_code or "????"
    entry = g.get("code_entry", "")
    html = _panel_open("text-align:center;")
    html += _header("THE SEALED DOOR", "Inscribe the Word of Passage")
    # Show the word as a reminder (you earned it).
    html += (
        f"<div style='font-size:12px; color:#778; margin:4px 0;'>The Word burned into your memory: "
        f"<b style='color:#cda;'>{code}</b></div>"
    )
    # Slots
    slots = ""
    for i in range(len(code)):
        ch = entry[i] if i < len(entry) else "_"
        slots += (
            f"<span style='display:inline-block; width:34px; height:42px; line-height:42px; "
            f"margin:3px; font-size:24px; color:#ffd24a; background:#11131f; "
            f"border:1px solid #335; border-radius:4px;'>{ch}</span>"
        )
    html += f"<div style='margin:10px 0;'>{slots}</div>"
    # Keypad: the code's letters plus a few decoys, shuffled.
    letters = list(dict.fromkeys(list(code)))
    decoys = [c for c in "ABCDEFGHJKLMNPRSTUVWXYZ" if c not in letters]
    random.Random(code).shuffle(decoys)
    keys = sorted(set(letters + decoys[:max(0, 8 - len(letters))]))
    html += "<div style='max-width:360px; margin:0 auto;'>"
    for ch in keys:
        html += _chip(f"o_code_{ch}", ch, bg="#223")
    html += "</div>"
    html += "<div style='margin-top:12px;'>"
    html += _chip("o_code_bs", "&#9003; Back", bg="#311")
    html += _chip("o_code_submit", "Inscribe", bg="#3a2a5a", fg="#ffd24a", border="#7a5")
    html += "</div></div>"
    return html


def _render_escaped(g):
    html = _panel_open("text-align:center;")
    html += _header("FREEDOM!", "The Legend of Zot is complete")
    html += (
        "<div style='max-width:430px; margin:12px auto; font-size:14px; line-height:1.6;'>"
        "The Word leaves your lips and the great seal cracks like spring ice. "
        "Daylight &mdash; real, warm, impossible daylight &mdash; pours into the "
        "cavern. You climb out with the Orb of Zot under one arm, a folded "
        "castle inside it, and the whole sprawling Wizard's Cavern conquered "
        "behind you.</div>"
    )
    html += (
        "<div style='max-width:430px; margin:8px auto; font-size:13px; color:#9ab;'>"
        "You have beaten Wizard's Cavern <i>and</i> the 1980 Wizard's Castle "
        "nested within it. Few heroes ever will. Go tell someone.</div>"
    )
    html += "<div style='font-size:26px; color:#ffd24a; margin:14px 0; letter-spacing:3px;'>&#10024; THE END &#10024;</div>"
    html += "<div style='margin-top:10px;'>"
    html += _chip("o_finish", "Close the book", bg="#3a2a5a", fg="#ffd24a", border="#7a5")
    html += "</div></div>"
    return html
