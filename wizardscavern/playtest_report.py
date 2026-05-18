"""Playtest report generator.

Collects per-run data during a smart-policy playtest and writes a
standalone HTML page per hero, plus an index page listing every run.
The output is deploy-ready for a GitHub Pages site (see
``scripts/deploy_playtest_reports.sh``) -- a `--deploy` flag on the
CLI invokes the deploy script after the report lands.

Each per-run page renders:

* a header with hero name / race / seed / outcome (alive / dead)
* the journey ledger: turns, max floor, level climb, gold, total kills
* the death scene (if dead): last 30 log lines, last actions, HP arc
* an equipment + inventory snapshot at end-of-run
* an HP timeline SVG chart so deep runs look like roguelike postmortems
"""

import html
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from string import Template

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip(s):
    return _HTML_TAG_RE.sub("", s or "")


def _normalize_monster_name(name):
    """Canonicalize a captured monster name. Tomb-adjacent guardians
    are spawned with a leading space (' UNDEAD WRAITH'), and the
    combat log's 'The X strikes first!' line yields 'The  ELITE
    UNDEAD WRAITH' when captured naively. This strips a leading
    'the ' (case-insensitive) and collapses any internal whitespace
    so the death-cause histogram doesn't fork the same monster into
    'ELITE UNDEAD WRAITH' and 'The  ELITE UNDEAD WRAITH' buckets."""
    if not name:
        return name
    out = " ".join(name.split()).strip()
    if out.lower().startswith("the "):
        out = out[4:].strip()
    return out


# ---------------------------------------------------------------------------
# Sprite helpers
# ---------------------------------------------------------------------------
# Pull base64 sprite data from the round-8 canonical pool and emit it as
# inline `<img>` tags. We dedupe identical sprites across the page by
# minting a CSS class per pid and pointing every reference at the same
# background-image rule -- without dedupe a 50-monster kill list balloons
# the page to 200+ KB of redundant base64 blobs.

def _sprite_pid_for(category, name, seed_extra=""):
    """Resolve a (category, item_name) pair to a sprite pid in the pool.

    category: one of 'monster', 'weapon', 'armor', 'potion', 'scroll',
              'food', 'lantern', 'ingredient', 'trophy', 'treasure'.
    name: in-game item name. Best-effort match via _resolve_new_monster_key
          (handles UNDEAD-prefixed / evo-prefixed names).
    seed_extra: appended to the lookup seed so two distinct instances of
                the same item type can deterministically land on
                different variants (e.g. two Goblins on a kill list).

    Returns a pid string, or None.
    """
    try:
        from .sprites import (
            monsters as _msprites,
            weapons as _wsprites,
            armors as _asprites,
            bug_armors as _basprites,
            potions as _psprites,
            spells as _sspsprites,
            scrolls as _scsprites,
            foods as _fsprites,
            lanterns as _lsprites,
            ingredients as _isprites,
            trophies as _tsprites,
            treasures as _trsprites,
            accessories as _accsprites,
            get_named_variant, get_generic_variant,
        )
        from .sprite_data import _resolve_new_monster_key
    except Exception:
        return None

    if not name:
        return None
    seed = (name, seed_extra)
    if category == "monster":
        cat_map = _msprites._MONSTERS_MAP
        key = _resolve_new_monster_key(name, cat_map)
        if key:
            v = get_named_variant(cat_map, key, seed=seed)
            return v[0] if v else None
        return None
    if category == "weapon":
        v = get_named_variant(_wsprites._WEAPONS_MAP, name, seed=seed)
        return v[0] if v else None
    if category == "armor":
        # Try standard armors first, then bug-sized armors.
        v = get_named_variant(_asprites._ARMORS_MAP, name, seed=seed)
        if v:
            return v[0]
        v = get_named_variant(_basprites._BUG_ARMORS_MAP, name, seed=seed)
        return v[0] if v else None
    if category == "potion":
        # Generic pool -- one sprite per pid, name used as seed for
        # deterministic colour pick.
        return get_generic_variant(_psprites._POTIONS_POOL, seed=seed)
    if category == "scroll":
        cat_map = _scsprites._SCROLLS_MAP if hasattr(_scsprites, "_SCROLLS_MAP") else None
        if cat_map:
            v = get_named_variant(cat_map, name, seed=seed)
            if v:
                return v[0]
        return None
    if category == "spell":
        return get_generic_variant(_sspsprites._SPELLS_POOL, seed=seed)
    if category == "food":
        v = get_named_variant(_fsprites._FOODS_MAP, name, seed=seed)
        return v[0] if v else None
    if category == "lantern":
        v = get_named_variant(_lsprites._LANTERNS_MAP, name, seed=seed)
        return v[0] if v else None
    if category == "ingredient":
        v = get_named_variant(_isprites._INGREDIENTS_MAP, name, seed=seed)
        return v[0] if v else None
    if category == "trophy":
        v = get_named_variant(_tsprites._TROPHIES_MAP, name, seed=seed)
        return v[0] if v else None
    if category == "treasure":
        cat_map = getattr(_trsprites, "_TREASURES_MAP", None)
        if cat_map:
            v = get_named_variant(cat_map, name, seed=seed)
            if v:
                return v[0]
        return None
    if category == "accessory":
        v = get_named_variant(_accsprites._ACCESSORIES_MAP, name, seed=seed)
        return v[0] if v else None
    return None


def _category_to_sprite_cat(inv_category):
    """Map an obs.inventory entry's `category` string to the sprite
    lookup key used by _sprite_pid_for. Returns None for categories
    without sprites (e.g. trophies the pool doesn't cover)."""
    if inv_category in ("weapon",):
        return "weapon"
    if inv_category in ("armor",):
        return "armor"
    if inv_category.startswith("potion"):
        return "potion"
    if inv_category in ("scroll",):
        return "scroll"
    if inv_category in ("spell",):
        return "spell"
    if inv_category in ("food", "food_rotten", "meat"):
        return "food"
    if inv_category in ("lantern",):
        return "lantern"
    if inv_category in ("lantern_fuel",):
        return "lantern"
    if inv_category in ("trophy",):
        return "trophy"
    if inv_category in ("ingredient",):
        return "ingredient"
    return None


class SpriteRegistry:
    """Per-page sprite deduplication.

    Calling `cls(pid)` returns a stable CSS class name. After rendering,
    `style_block()` emits a single <style> chunk with one
    `.sprite-<class> { background-image: url(data:image/webp;base64,...) }`
    rule per unique pid. Each reference in the HTML becomes a tiny
    <span class="sprite sprite-<class>"></span> tag instead of a 4 KB
    inline blob.
    """

    def __init__(self):
        self._pid_to_class = {}

    def cls(self, pid):
        if not pid:
            return None
        klass = self._pid_to_class.get(pid)
        if klass is None:
            klass = f"p{len(self._pid_to_class):04d}"
            self._pid_to_class[pid] = klass
        return klass

    def style_block(self):
        try:
            from .sprites import get_image_b64
        except Exception:
            return ""
        rules = []
        for pid, klass in self._pid_to_class.items():
            b64 = get_image_b64(pid)
            if not b64:
                continue
            rules.append(
                f".sprite-{klass}{{background-image:"
                f"url(data:image/webp;base64,{b64})}}"
            )
        return "\n".join(rules)


def _detect_loop_period(actions, min_matches=12):
    """Given a list of action strings, return the cycle period
    (1, 2, 3, or 4) if at least `min_matches` of them fit a tight
    periodic pattern keyed to the tail. Else None.

    Used both for end-of-run stuck classification (called once with
    the last 20 actions) and the post-hoc episode scan (called per
    sliding window across the whole run)."""
    if len(actions) < min_matches:
        return None
    for period in (1, 2, 3, 4):
        if len(actions) < period * 3:  # need at least 3 cycles
            continue
        base = actions[-period:]
        matches = 0
        for i in range(len(actions)):
            pos_from_end = len(actions) - 1 - i
            if actions[i] == base[(period - 1) - (pos_from_end % period)]:
                matches += 1
        if matches >= min_matches:
            return period
    return None


def _sprite_span(registry, pid, size=32, extra_class=""):
    """Emit an inline sprite reference using the registry for dedupe."""
    if not pid:
        return ""
    klass = registry.cls(pid)
    if not klass:
        return ""
    extra = f" {extra_class}" if extra_class else ""
    return (
        f"<span class='sprite sprite-{klass}{extra}' "
        f"style='width:{size}px;height:{size}px'></span>"
    )


class RunReport:
    """Per-run accumulator. The harness pumps obs frames + final state
    here, and `to_html()` renders a page that can be dropped into a
    GitHub Pages site.

    Stateless across runs -- one instance per playtest. Caller holds it
    and queries `to_html()` after the game loop exits.
    """

    MAX_LOG_BUFFER = 60
    HP_SAMPLE_EVERY_N = 1  # record every HP change

    def __init__(self, seed, race, gender, name, spells, starting_stats):
        self.seed = seed
        self.race = race
        self.gender = gender
        self.name = name
        self.spells = list(spells or [])
        self.starting_stats = dict(starting_stats or {})
        self.start_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # Lightweight per-turn snapshots
        self.hp_timeline = []  # [(turn, hp, max_hp)]
        self.mana_timeline = []  # [(turn, mana, max_mana)]
        self.hunger_timeline = []  # [(turn, hunger)]  -- hunger is 0-100
        self.events = []  # [(turn, kind, detail)]
        self.recent_log = []  # rolling buffer of last 60 lines
        self.recent_actions = []  # rolling buffer of last 12 (turn, mode, action)
        # Full per-run action history used for two passes:
        #   - end-of-run stuck classification (last 20 actions only)
        #   - post-hoc mid-run loop-episode scan (whole list, at
        #     finalize time, after the run is over)
        # Each entry is (turn, mode, action) so the episode reporter
        # can name the mode the agent got wedged in.
        self._action_history = []  # [(turn, mode, action)] full run
        # Mid-run loop episodes found at finalize. Each entry:
        #   {"start": int, "end": int, "length": int, "period": int,
        #    "mode": str, "action": str}
        # Sorted by length descending. Episodes < 50 turns are
        # filtered out -- the harness's anti-wedge breaks short
        # ones cheaply; what we care about are the persistent ones
        # that burn real budget before resolving.
        self.loop_episodes = []
        self.kills_by_monster = {}  # name -> count
        self.kills_by_floor = {}  # floor -> count
        # Tomb-suspicion log -- floors where the agent fought an undead
        # (a reliable tell for a tomb on that floor; see harness comment
        # in _monster_obs). Each entry is (turn, floor, monster_name).
        # The set form is also kept for quick "is this floor flagged"
        # lookups during HTML rendering.
        self.tomb_suspected_floors = set()
        self.tomb_sightings = []  # [(turn, floor, monster_name)]
        # First time the agent's character sprite is determined.
        # generate_player_sprite_html is seed-based; we mirror that.
        self.player_sprite_pid = None
        # Movement efficiency tracking. For each floor we keep:
        #   - the set of (x, y) tiles the agent has stood on
        #   - the per-floor counters: total game_loop moves, first-visit
        #     moves (new (x,y) reached), revisit moves (already seen).
        # Per-floor waste% = revisits / total_moves. Combined with
        # turns_on_floor, this tells us how much of the floor budget
        # was patrol-bouncing vs productive exploration.
        self.visited_tiles_by_floor = {}  # floor -> set[(x,y)]
        self.moves_by_floor = {}          # floor -> total game_loop moves
        self.first_visit_moves = {}       # floor -> new-tile moves
        self.revisit_moves = {}           # floor -> already-seen tile moves
        self._last_xy = None              # (z, x, y) of prior frame
        # Last turn we reached a tile we hadn't seen before (anywhere
        # on the run). Combined with progress-event timestamps to
        # gate the flatline classifier so an exploring agent doesn't
        # get flagged stuck just because it hasn't killed anything.
        self.last_new_tile_turn = 0
        self.buys = []  # (turn, floor, name, price, count)
        self.identifies = []  # (turn, item_name)
        self.descents = []  # turn at which each new floor was first entered
        # Per-floor exploration totals: how many monsters / chests /
        # boons exist on the floor, captured from obs.floor_totals
        # the first time the agent stands on each floor. Combined
        # with kills_by_floor + xp_by_floor + visited features at
        # report time to compute engagement ratios. User-requested
        # ('evaluate exp + treasure left on each level to see if
        # better exploring would help with survival').
        self.floor_totals = {}  # floor -> {"M":N, "C":N, ..., "xp_pool":N}
        self.xp_by_floor = {}   # floor -> total kill-XP earned
        # How each floor was LEFT. Populated from the (mode, action)
        # pair that triggered the floor change, inferred at the
        # moment record_obs sees a new floor index. Methods:
        #   'stairs_down' -- pressed 'd' on a D tile
        #   'stairs_up'   -- pressed 'u' on a U tile (retreat path)
        #   'warp_accept' -- chose 'n' in warp_mode (took the warp)
        #   'warp_forced' -- chose 'y' but the resist roll failed
        #   'other'       -- couldn't identify (e.g., scroll teleport)
        # Entry: (from_floor, to_floor, turn, method)
        self.floor_exits = []
        self.equipped_history = []  # (turn, weapon_name, armor_name)
        self.last_equip = (None, None)
        # Tracks the (mode, action) of the most-recently-issued
        # action so floor-exit detection can read what caused the
        # transition. Updated by record_action; read by record_obs.
        self._last_action_mode = (None, None)
        # name -> category mapping built from per-turn inventory
        # snapshots. Lets the aggregated tables look up the
        # category of a bought / found item by name without parsing
        # log lines.
        self.item_categories = {}
        # Items the agent picked up off the map (monster drops,
        # chest contents, garden harvests, tomb treasures, etc.) --
        # NOT bought from a vendor. Parsed from log messages like
        # "The Goblin dropped a Longsword!" or "Found: 50 gold +
        # Healing Potion!". Used by the report's Equipment-found
        # table so the user can see which dropped weapons/armor the
        # agent actually equipped vs left in the bag.
        # Entry: (turn, floor, name, source) where source is one of
        # 'monster_drop' / 'chest' / 'tomb' / 'garden' / 'altar' /
        # 'shrine' / 'oracle' / 'library' / 'pool' / 'other'.
        self.found_items = []
        # Names of items ever equipped (weapon or armor) over the
        # course of the run, derived from equipped_history. Used to
        # mark found / bought gear as "equipped" vs "never equipped".
        self._ever_equipped_names = set()
        self.max_floor = 1
        self.last_seen_log = set()

        # Final-state fields, filled in by `finalize`
        self.final = None
        self.death_cause = None
        # Three-state outcome: "alive" | "dead" | "stuck". "stuck"
        # means the agent finished alive but stopped making progress
        # (flatlined HP + no events) or got trapped in a tight action
        # cycle. status_reason is a short human-readable detail used
        # in the per-run page and in the index "Cause" column for
        # stuck runs (death_cause holds the analogous string for
        # dead runs).
        self.status = None
        self.status_reason = None

    # ------------------------------------------------------------------
    # Recording -- called every turn from the harness loop
    # ------------------------------------------------------------------
    def record_obs(self, turn, obs, gs_log_lines):
        """Capture an observation. `gs_log_lines` is read directly so
        we don't miss lines when the harness's `obs.log` delta is
        truncated by the in-game 16-line cap on rotation."""
        p = obs.get("player") or {}
        if p:
            self.hp_timeline.append((turn, p.get("hp", 0), p.get("max_hp", 1)))
            self.mana_timeline.append(
                (turn, p.get("mana", 0), p.get("max_mana", 0) or 1)
            )
            self.hunger_timeline.append((turn, p.get("hunger", 0)))
            f = p.get("floor", 1)
            if f > self.max_floor:
                self.max_floor = f
                self.descents.append((turn, f))
            # Floor-exit detector. Any floor change (up OR down) gets
            # an entry in floor_exits keyed on the action that
            # triggered it. Re-visits of an already-known floor (via
            # warp back) ARE counted so the user can see warp ping-
            # pongs in the journey log.
            prev_floor = getattr(self, "_last_floor_seen", None)
            if prev_floor is not None and f != prev_floor:
                mode_at, action_at = self._last_action_mode
                if mode_at == "stairs_down_mode" and action_at == "d":
                    method = "stairs_down"
                elif mode_at == "stairs_up_mode" and action_at == "u":
                    method = "stairs_up"
                elif mode_at == "warp_mode" and action_at == "n":
                    method = "warp_accept"
                elif mode_at == "warp_mode" and action_at == "y":
                    method = "warp_forced"
                else:
                    method = "other"
                self.floor_exits.append((prev_floor, f, turn, method))
            self._last_floor_seen = f
        # Capture floor exploration totals on first observation of
        # each floor (including F1 which doesn't trigger the floor-
        # change block above). obs.floor_totals is keyed by INTERNAL
        # z (0-indexed); we key everything else by 1-based floor.
        ft = obs.get("floor_totals") or {}
        z_now = f - 1
        if z_now in ft and f not in self.floor_totals:
            self.floor_totals[f] = ft[z_now]
        # Per-frame stats that run regardless of floor change.
        # name -> category map for the aggregated tables. Pull
        # categories off every inventory snapshot so we have a
        # lookup at write-time for items that were bought, used,
        # and gone by the end of the run.
        for item in obs.get("inventory") or []:
            nm = item.get("name")
            cat = item.get("category")
            if nm and cat:
                self.item_categories[nm] = cat
        eq = p.get("equipped") or {}
        cur = ((eq.get("weapon") or {}).get("name"),
               (eq.get("armor") or {}).get("name"))
        if cur != self.last_equip:
            self.last_equip = cur
            self.equipped_history.append((turn, cur[0], cur[1]))
            # Record any newly-slotted item so found / bought
            # gear can be flagged "equipped" in the post-run
            # tables.
            if cur[0]:
                self._ever_equipped_names.add(cur[0])
            if cur[1]:
                self._ever_equipped_names.add(cur[1])
        # Movement-efficiency: when we observe a fresh position
        # while in game_loop, classify it as first-visit or
        # revisit relative to this floor's history. We count by
        # position-CHANGE, not by action-issued, so step-blocked
        # (walked into wall) doesn't inflate either counter.
        cur_xyz = (p.get("floor", 1), p.get("x"), p.get("y"))
        if (obs.get("mode") == "game_loop"
                and self._last_xy is not None
                and cur_xyz != self._last_xy):
            # Different from prior frame -> a real move landed
            floor = cur_xyz[0]
            xy = (cur_xyz[1], cur_xyz[2])
            seen = self.visited_tiles_by_floor.setdefault(floor, set())
            self.moves_by_floor[floor] = self.moves_by_floor.get(floor, 0) + 1
            if xy in seen:
                self.revisit_moves[floor] = self.revisit_moves.get(floor, 0) + 1
            else:
                seen.add(xy)
                # Stamp "new tile reached" as a progress event so the
                # flatline classifier counts cartographic progress
                # alongside kill / xp / descent. Without this, an agent
                # who's exploring fog but hasn't killed anything for a
                # long stretch can still be productively scouting.
                self.last_new_tile_turn = turn
                self.first_visit_moves[floor] = (
                    self.first_visit_moves.get(floor, 0) + 1
                )
        self._last_xy = cur_xyz

        # Mirror the harness's tomb-suspicion tracker for the report.
        # obs.suspected_tomb_floors is a sorted list of floor indices
        # (0-based); add the 1-based floor to our set.
        for z in obs.get("suspected_tomb_floors") or []:
            self.tomb_suspected_floors.add(z + 1)
        # First-time undead sighting on a floor: record it so the
        # "Combat" tab can show the player WHEN the suspicion fired.
        mon = obs.get("monster") or {}
        if mon and mon.get("is_undead"):
            floor_1based = (p.get("floor", 1))
            if not any(s[1] == floor_1based for s in self.tomb_sightings):
                self.tomb_sightings.append(
                    (turn, floor_1based, mon.get("name") or "undead")
                )

        for raw in gs_log_lines:
            line = _strip(raw)
            if not line:
                continue
            key = (turn // 4, line)
            if key in self.last_seen_log:
                continue
            self.last_seen_log.add(key)
            self.recent_log.append((turn, line))
            if len(self.recent_log) > self.MAX_LOG_BUFFER:
                self.recent_log.pop(0)
            self._categorise_log(turn, line, p)

    def record_action(self, turn, mode, action):
        # Remember the action that's about to be dispatched -- the
        # floor-exit detector reads this after step() observes a
        # floor change.
        self._last_action_mode = (mode, action)
        self.recent_actions.append((turn, mode, action))
        if len(self.recent_actions) > 12:
            self.recent_actions.pop(0)
        # Full-run action history -- no cap. The whole-run scan at
        # finalize uses this to find loop episodes the agent
        # eventually escaped. 5k turns x ~16 bytes per tuple ~ 80KB,
        # fine for a per-run report buffer.
        if isinstance(action, str):
            self._action_history.append((turn, mode, action))

    def _categorise_log(self, turn, line, p):
        low = line.lower()
        floor = (p or {}).get("floor", 1)

        if "you gained" in low and "experience" in low:
            self.events.append((turn, "xp", line))
            self.kills_by_floor[floor] = self.kills_by_floor.get(floor, 0) + 1
            # Sum kill-XP per floor. Log line: 'You gained N
            # experience.' Capture N for the exploration metric.
            xp_match = re.search(r"gained\s+(\d+)\s+experience", line, re.IGNORECASE)
            if xp_match:
                xp_n = int(xp_match.group(1))
                self.xp_by_floor[floor] = self.xp_by_floor.get(floor, 0) + xp_n

        m = re.match(r"you defeated the ([\w '\-]+?)[.!]", line, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            self.kills_by_monster[name] = self.kills_by_monster.get(name, 0) + 1
            self.events.append((turn, "kill", name))

        if line.startswith("You bought "):
            m = re.match(r"You bought (\d+ )?([^.]+?) for (\d+) gold", line)
            if m:
                count = int(m.group(1).strip()) if m.group(1) else 1
                name = m.group(2).strip()
                price = int(m.group(3))
                self.buys.append((turn, floor, name, price, count))
                self.events.append((turn, "buy", f"{count}× {name} ({price}g)"))

        # Map-found items: monster drops, chest contents, garden
        # harvests, tomb treasures, altar prayers, etc. Patterns
        # mirror the in-game log strings (see items.py
        # drop_monster_items and game_systems.py chest payouts).
        # The agent's intent — equip the dropped weapon or leave it
        # — surfaces via _ever_equipped_names.
        m = re.match(r"The [\w '\-]+ dropped (?:a |an |some )?([^.!]+?)[.!]",
                     line)
        if m:
            name = m.group(1).strip()
            self.found_items.append((turn, floor, name, "monster_drop"))
        m = re.match(r"You found (?:a |an |some )?([^.!]+?)[.!]", line)
        if m:
            name = m.group(1).strip()
            # Filter out gold-only / xp-only messages
            low_name = name.lower()
            if (low_name.startswith("gold")
                    or "experience" in low_name
                    or low_name.endswith(" gold")
                    or low_name.endswith(" gold coins")):
                pass
            else:
                self.found_items.append((turn, floor, name, "chest"))
        m = re.match(r"Found: (?:\d+ )?([^.!\d][^.!]*?)$", line.strip())
        if m:
            name = m.group(1).strip()
            low_name = name.lower()
            if not (low_name.startswith("gold")
                    or low_name.endswith(" gold")
                    or low_name.endswith(" gold coins")):
                self.found_items.append((turn, floor, name, "drop"))
        m = re.match(r"Gathered:\s+(.+?)$", line.strip())
        if m:
            name = m.group(1).strip()
            self.found_items.append((turn, floor, name, "garden"))

        m = re.search(r"identified: ([^!]+)!", line)
        if m:
            self.identifies.append((turn, m.group(1).strip()))

        if "level up" in low or "leveled up" in low:
            self.events.append((turn, "level_up", line))

        if "perfect! you can use this to refuel" in low:
            self.events.append((turn, "fuel_drop", line))

        if "tomb guardian" in low or "spectral knight" in low:
            self.events.append((turn, "tomb_fight", line))

    # ------------------------------------------------------------------
    # Finalising
    # ------------------------------------------------------------------
    def finalize(self, final_obs, gs_log_lines, turns):
        p = final_obs.get("player") or {}
        alive = final_obs.get("alive")
        # Grab a snapshot of the final log buffer (in addition to
        # whatever we already accumulated). gs.log_lines is capped at
        # 16 so this is the recent-history view.
        final_logs = [_strip(l) for l in gs_log_lines]
        self.final = {
            "turn": turns,
            "alive": bool(alive),
            "floor": p.get("floor"),
            "level": p.get("level"),
            "hp": p.get("hp"),
            "max_hp": p.get("max_hp"),
            "mana": p.get("mana"),
            "max_mana": p.get("max_mana"),
            "gold": p.get("gold"),
            "xp": p.get("xp"),
            "hunger": p.get("hunger"),
            "strength": p.get("strength"),
            "dexterity": p.get("dexterity"),
            "intelligence": p.get("intelligence"),
            "can_cast": p.get("can_cast"),
            "equipped": p.get("equipped") or {},
            "lantern": p.get("lantern") or {},
            "inventory": final_obs.get("inventory") or [],
            "mode": final_obs.get("mode"),
            "logs_at_end": final_logs,
        }
        if not alive:
            self.death_cause = self._derive_death_cause()
        # Three-state classification: dead beats stuck beats alive.
        # Stuck only fires when the agent is still alive but has
        # clearly stopped progressing (see _classify_status).
        self.status, self.status_reason = self._classify_status(turns)
        # Scan the whole run for mid-run loop episodes the agent
        # eventually escaped. These don't change status (the run
        # ended fine) but signal a softlock the harness's anti-
        # wedge had to fight through -- exactly the diagnostic
        # surface the user asked for ('loops within runs').
        self.loop_episodes = self._scan_loop_episodes()

    def _classify_status(self, turns):
        """Return (status, reason) where status is one of
        'alive' / 'dead' / 'stuck'. Reason is a short human-readable
        detail string for stuck runs, or None.

        Stuck signals (alive only):
          1. flatline -- no progress event (kill / xp / level_up /
             buy / identify / descent / NEW TILE reached) AND HP
             roughly flat in a recent window. Window = max(80, turns
             // 5); HP stable = max-min <= 3 in that window.
          2. loop -- the last N action strings form a tight
             repeating cycle (1, 2, 3, or 4-action period covering
             at least 12 of the last 20 actions). Catches the
             classic ping-pong-on-warp-tile pattern.

        Dead always wins over stuck. Alive-with-no-stuck-signal is
        plain 'alive'.
        """
        alive = (self.final or {}).get("alive", False)
        if not alive:
            return "dead", None

        # ---- flatline check -----------------------------------------
        # 'Progress' = any signal the agent is still making forward
        # motion: a kill, XP gain, level-up, vendor buy, identify,
        # fuel drop, tomb fight, descent to a new floor, OR reaching
        # a tile not previously stood on (cartographic progress).
        # The last-progress turn is the latest of any of these.
        progress_kinds = {
            "kill", "xp", "level_up", "buy", "identify",
            "fuel_drop", "tomb_fight",
        }
        last_progress = 0
        for (t, kind, _detail) in self.events:
            if kind in progress_kinds and t > last_progress:
                last_progress = t
        if self.descents:
            last_progress = max(last_progress, max(t for (t, _f) in self.descents))
        if self.identifies:
            last_progress = max(last_progress, max(t for (t, _n) in self.identifies))
        last_progress = max(last_progress, self.last_new_tile_turn)

        idle_turns = max(0, turns - last_progress)
        # Tighter window than the earlier max(100, turns//4): at
        # 2000-turn budgets that was 500 idle, which let a lot of
        # softly-stuck runs pass. The new-tile signal above makes
        # the gate honest about exploration progress, so we can
        # narrow the idle window without false positives.
        window = max(80, turns // 5)

        # HP must be roughly stable in the idle window (no fights, no
        # ticks). max-min <= 3 lets passive regen + 1 hunger-tick
        # count as 'stable' so a turn-budget-bound exploring agent
        # whose HP creeps from 60 -> 63 over 400 turns still
        # qualifies as flatlined when nothing else is happening.
        window_start = max(0, turns - window)
        hp_samples = [hp for (t, hp, _mx) in self.hp_timeline if t >= window_start]
        hp_stable = bool(hp_samples) and (max(hp_samples) - min(hp_samples) <= 3)

        flatlined = (
            turns >= 80          # need enough runtime to be confident
            and idle_turns >= window
            and hp_stable
        )

        # ---- loop check ---------------------------------------------
        # A periodic action sequence ALONE doesn't mean stuck -- a
        # healthy explore phase can run n/e/s/w in a loop while still
        # making real progress. Only treat the cycle as 'stuck' when
        # the agent ALSO hasn't logged a progress event for a while
        # (idle for at least 30 turns). The flatline check above
        # requires HP-stability + a full window; the loop branch is
        # a lighter idle gate that catches tighter ping-pong wedges
        # before the flatline window fully closes.
        loop_period = self._detect_action_loop()
        looped = loop_period is not None and idle_turns >= 30 and turns >= 80

        if looped:
            return "stuck", f"loop (period={loop_period}, {idle_turns} idle)"
        if flatlined:
            return "stuck", f"flatline ({idle_turns} turns, no progress)"
        return "alive", None

    def _detect_action_loop(self):
        """Look at the last 20 action STRINGS. If at least 12 of them
        form a tight period-1/2/3/4 cycle, return that period. Else
        None.

        Period-1 = same action repeated (e.g., 'i i i i ...').
        Period-2 = two-action ping-pong ('n s n s ...').
        Periods 3 and 4 cover the longer wander-loops the harness's
        own stuck-on-floor override is designed to break out of."""
        actions = [a for (_t, _m, a) in self._action_history[-20:]]
        return _detect_loop_period(actions, min_matches=12)

    def _scan_loop_episodes(self):
        """Whole-run pass over self._action_history to find stretches
        where the agent was looping but eventually escaped. Returns
        a list of episode dicts sorted by length descending. Only
        episodes >= 50 turns are kept -- shorter wedges that the
        harness's anti-wedge override clears are noise.

        Algorithm: slide a 20-action window across the whole history.
        At each position, run the same period-1..4 loop detector
        used by the end-of-run classifier. Mark each frame as 'in
        loop' (and at which period). Merge consecutive marked frames
        into episodes, taking start/end turns and the dominant mode
        + action at the start.
        """
        if len(self._action_history) < 20:
            return []
        actions = [a for (_t, _m, a) in self._action_history]
        # in_loop[i] = period (1..4) or None for action index i
        # Walk i = 19..N-1: the window ends at i (inclusive of last
        # 20 frames). Mark every frame within a tripping window.
        in_loop = [None] * len(actions)
        tripped_until = -1  # right edge of currently-tripped window
        for i in range(19, len(actions)):
            window = actions[i - 19:i + 1]
            period = _detect_loop_period(window, min_matches=12)
            if period is not None:
                # Mark all 20 frames in the window as part of a loop
                # with this period. Frames before tripped_until keep
                # their already-recorded period (first-seen wins so
                # period stays consistent across overlapping windows).
                left = max(i - 19, tripped_until + 1)
                for j in range(left, i + 1):
                    in_loop[j] = period
                tripped_until = i
        # Merge consecutive marked frames into episodes. For each
        # episode, pick a representative "cycle" string by sampling
        # `period` actions from a stable section (skip the first few
        # frames where the boundary action may differ from the body
        # of the loop). The MODE comes from the same section too --
        # the start frame's mode can be a transition (e.g.
        # 'inventory' on the boundary while the cycle is really in
        # game_loop with n/s/n/s).
        episodes = []
        i = 0
        while i < len(actions):
            if in_loop[i] is None:
                i += 1
                continue
            start = i
            period = in_loop[i]
            while i < len(actions) and in_loop[i] is not None:
                i += 1
            end = i - 1
            start_turn = self._action_history[start][0]
            end_turn = self._action_history[end][0]
            length = end_turn - start_turn + 1
            # Sample mode + cycle from the middle of the episode so
            # the labels reflect the steady-state loop, not the
            # transition frame at start.
            mid = (start + end) // 2
            mode = self._action_history[mid][1]
            cycle_start = max(start, mid - (period - 1))
            cycle = "".join(
                self._action_history[j][2]
                for j in range(cycle_start, min(cycle_start + period, end + 1))
            )
            # Skip combat-mode runs: a long fight is the agent
            # repeatedly attacking the same monster (action 'a'
            # period-1) or flee+attack ping-ponging at low HP --
            # not a softlock, the monster's HP is ticking down.
            # HP changes alongside the period-1 action so it doesn't
            # match the 'no progress' definition either. Filter at
            # the report level so the loop-episodes table surfaces
            # only real wedges.
            COMBAT_MODES = ("combat_mode", "combat_victory",
                            "spell_casting_mode", "flee_direction_mode")
            if mode in COMBAT_MODES:
                continue
            if length >= 50:  # filter transient wedges
                episodes.append({
                    "start": start_turn,
                    "end": end_turn,
                    "length": length,
                    "period": period,
                    "mode": mode,
                    "action": cycle,
                })
        episodes.sort(key=lambda e: -e["length"])
        return episodes

    def _derive_death_cause(self):
        """Walk recent_log backwards for a recognisable killer.

        Combat.py logs death four ways:
          1. 'You were defeated by the {monster}...'    (most common)
          2. 'You were defeated by status effects...'   (poison etc.)
          3. 'You were defeated while channeling...'    (spell interrupt)
          4. 'You were defeated...'                     (failed-flee
             parting attack, status tick, chest explosion -- no
             by-clause in the line itself; the killer is the most
             recent monster name OR explicit hazard in the lead-up).

        Forlong of the Mark (human, F3 Wight): the user-flagged
        screenshot showed 'Cause: unknown' because the run hit
        path #4 -- a failed flee at HP=1 with Wight life-drain
        adjacent. The regex only matched #1.
        """
        # Explicit hazards first -- these supersede a generic
        # 'defeated' line if both appear nearby.
        for (_, line) in reversed(self.recent_log):
            low = line.lower()
            if "the trap was lethal" in low or "the explosion was fatal" in low:
                return "lethal pool trap"
            if "the chest explodes" in low or "chest explodes" in low:
                return "chest explosion"
            # Starvation collapse must be checked BEFORE the status-
            # effects branch -- combat.py logs the final defeat as
            # 'You were defeated by status effects upon entering the
            # new room...' AFTER 'You collapse from starvation...',
            # so the backward walk would otherwise bucket starvation
            # deaths as the generic 'defeated by status effects'.
            # Playtester flagged 31/57 build-306 deaths landing in
            # the wrong bucket.
            if "collapse from starvation" in low:
                return "starvation"
            if "you were defeated by status effects" in low:
                # Find the source status from prior log lines.
                # Starvation is checked FIRST because the prior
                # build-308 ordering attempt only re-ordered the
                # outer branches -- but the death log emits
                # 'You collapse from starvation...' on the turn
                # BEFORE the 'defeated by status effects' line,
                # so the outer reverse walk hits status_effects
                # first and never sees the collapse. The playtester
                # found 33/33 sampled status-effects deaths were
                # actually starvation. Now check inside.
                for (_, prev) in reversed(self.recent_log):
                    pl = prev.lower()
                    if "collapse from starvation" in pl:
                        return "starvation"
                    if "poison" in pl and ("hp from" in pl or "damage" in pl):
                        return "defeated by poison"
                    if "burn" in pl and "damage" in pl:
                        return "defeated by burn"
                    if "life drain" in pl:
                        return "defeated by life-drain"
                return "defeated by status effects"
            if "you were defeated while channeling" in low:
                return "defeated while channeling spell"

            # Explicit 'defeated by the X' form
            m = re.search(r"you were defeated by(?: the)? ([^.]+?)\.\.\.",
                          line, re.IGNORECASE)
            if m:
                return f"defeated by {_normalize_monster_name(m.group(1))}"

            # Generic 'You were defeated...' (no by-clause). Walk
            # back from this point to find the killer: most recent
            # monster verb (hit / drains / poisons / burns / etc.).
            if low.startswith("you were defeated"):
                # Find most recent monster mention in the log.
                killer = self._extract_recent_attacker()
                if killer:
                    # Also flag the killing-effect type for clarity.
                    effect = self._extract_recent_effect()
                    if effect:
                        return f"defeated by {killer} ({effect})"
                    return f"defeated by {killer}"
                # Last resort: did we starve to a damage-source
                # while at HP=1?
                if self._was_starving_recently():
                    return "starvation"
                return "defeated"

            if "starving" in low and "lost" in low:
                return "starvation"
            if "collapse from starvation" in low:
                return "starvation"
        return "unknown"

    # Killer-name patterns from combat.py log strings. The leading
    # space in some monster names (legendary spawns sometimes
    # render as ' BUG QUEEN') is tolerated by the \S+ pattern.
    _ATTACK_VERBS = (
        "hit", "missed", "drains your", "claws at", "bites",
        "strikes", "slashes", "casts", "breathes",
    )

    def _extract_recent_attacker(self):
        """Find the most recent monster acting on the player. Scans
        the last 30 log lines (most recent first) for an attack /
        miss / status-inflict from a named monster.

        Name normalization: tomb-adjacent guardians are spawned with
        a LEADING SPACE in the name (' UNDEAD WRAITH' / ' ELITE
        UNDEAD WRAITH' -- see game_systems.py:2641). The combat log
        renders them via 'The {name} strikes first!' -> 'The  ELITE
        UNDEAD WRAITH strikes first!' (double space). The regex
        used to capture 'The  ELITE UNDEAD WRAITH' (with the leading
        'The' AND the double space) because the optional `(?:The )?`
        was skipped when the greedy capture could match the whole
        'The X' string. We post-strip 'the ' prefix + collapse
        internal whitespace so the death-cause histogram doesn't
        split the same monster into multiple buckets.
        """
        for (_, line) in reversed(self.recent_log[-30:]):
            stripped = line.strip()
            # 'Wight missed X' / 'Wight hit X' / 'Wight drains your...'
            m = re.match(
                r"(?:Ouch! )?(?:The )?([A-Z][A-Za-z' \-]+?) "
                r"(?:hit|missed|drains|claws|bites|strikes|slashes"
                r"|casts|breathes|releases)\b",
                stripped,
            )
            if m:
                name = _normalize_monster_name(m.group(1))
                # Skip the player's own name and 'You' patterns.
                if name.lower() == "you" or name == self.name:
                    continue
                return name
        return None

    def _extract_recent_effect(self):
        """Identify a recent DoT / debuff effect that might have
        landed the killing blow."""
        for (_, line) in reversed(self.recent_log[-15:]):
            low = line.lower()
            if "life drain" in low or "life force" in low:
                return "life drain"
            if "poison" in low and "hp" in low:
                return "poison tick"
            if "burn" in low and "damage" in low:
                return "burn"
            if "freeze" in low and "damage" in low:
                return "freeze"
        return None

    def _was_starving_recently(self):
        """Did the agent take any starvation HP loss in the last 20
        log lines? Catches HP=1 → starvation-tick → defeated paths."""
        for (_, line) in reversed(self.recent_log[-20:]):
            low = line.lower()
            if "starving" in low and "lost" in low:
                return True
        return False

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    @property
    def slug(self):
        return f"{self.seed:05d}_{self.race}"

    def summary_row(self):
        """One-row dict used by index.html generation."""
        f = self.final or {}
        total_moves = sum(self.moves_by_floor.values())
        total_revisit = sum(self.revisit_moves.values())
        wasted_pct = (total_revisit / total_moves * 100.0) if total_moves else 0
        # Warp share of floor changes: every floor change is recorded
        # in floor_exits with a method tag (stairs_down / stairs_up /
        # warp_accept / warp_forced / other). When this number is
        # high, the agent's warp-avoidance is leaking -- either the
        # AVOID-W gate is dropping too eagerly or the agent keeps
        # stepping onto W tiles via fog. Used to audit unwanted warp
        # acceptance per the user's "I would think players would be
        # avoiding warps more" framing.
        n_exits = len(self.floor_exits)
        n_warp = sum(
            1 for (_fr, _to, _t, m) in self.floor_exits
            if m in ("warp_accept", "warp_forced")
        )
        n_warp_accept = sum(
            1 for (_fr, _to, _t, m) in self.floor_exits if m == "warp_accept"
        )
        n_warp_forced = sum(
            1 for (_fr, _to, _t, m) in self.floor_exits if m == "warp_forced"
        )
        warp_pct = (n_warp / n_exits * 100.0) if n_exits else 0
        # Exploration efficiency across all visited floors. User
        # asked: 'evaluate exp + treasure left on each level to see
        # if better exploring would help with survival.' For each
        # floor we have totals (M / C / G / L / O / A / P / V / T /
        # N / xp_pool) and kills_by_floor + xp_by_floor. Sum across
        # visited floors and report engagement %.
        total_monsters = sum(ft.get("M", 0) for ft in self.floor_totals.values())
        total_kills = sum(self.kills_by_floor.values())
        total_xp_pool = sum(ft.get("xp_pool", 0) for ft in self.floor_totals.values())
        total_xp_earned = sum(self.xp_by_floor.values())
        total_chests = sum(ft.get("C", 0) for ft in self.floor_totals.values())
        boon_keys = ("G", "L", "O", "A", "P", "Q", "K", "B", "F")
        total_boons = sum(
            ft.get(k, 0) for ft in self.floor_totals.values() for k in boon_keys
        )
        # Pool denominator is approximate -- dynamic spawns (haunted
        # spirits from tomb raids, chest-gas monsters, multi-visit
        # respawns on already-killed tiles) add to the numerator
        # without updating the static M-tile count. Lift the
        # denominator to at least the numerator so the ratio reads
        # as "% of MINIMUM available pool". The trailing residual is
        # honest "bonus" XP, not formula error.
        total_monsters = max(total_monsters, total_kills)
        total_xp_pool = max(total_xp_pool, total_xp_earned)
        kill_pct = (total_kills / total_monsters * 100.0) if total_monsters else 0
        xp_pct = (total_xp_earned / total_xp_pool * 100.0) if total_xp_pool else 0
        return {
            "slug": self.slug,
            "name": self.name,
            "race": self.race,
            "seed": self.seed,
            "turn": f.get("turn", 0),
            "max_floor": self.max_floor,
            "level": f.get("level", 1),
            "hp": f.get("hp"),
            "max_hp": f.get("max_hp"),
            "gold": f.get("gold"),
            "kills": sum(self.kills_by_floor.values()),
            "alive": f.get("alive", False),
            "status": self.status or ("alive" if f.get("alive") else "dead"),
            "status_reason": self.status_reason or "",
            "death_cause": self.death_cause or "—",
            "started": self.start_iso,
            "moves_total": total_moves,
            "moves_revisit": total_revisit,
            "wasted_pct": round(wasted_pct, 1),
            "floor_changes": n_exits,
            "warp_changes": n_warp,
            "warp_accepts": n_warp_accept,
            "warp_forced": n_warp_forced,
            "warp_pct": round(warp_pct, 1),
            "monsters_total": total_monsters,
            "monsters_killed": total_kills,
            "kill_pct": round(kill_pct, 1),
            "xp_pool": total_xp_pool,
            "xp_earned": total_xp_earned,
            "xp_pct": round(xp_pct, 1),
            "chests_total": total_chests,
            "boons_total": total_boons,
            # Mid-run loop episodes (eventually escaped). Top-line:
            # count + total turns burned. Per-run page shows details.
            "loop_episode_count": len(self.loop_episodes),
            "loop_turns_total": sum(e["length"] for e in self.loop_episodes),
        }

    def to_html(self):
        f = self.final or {}
        eq = f.get("equipped") or {}
        wpn = eq.get("weapon") or {}
        arm = eq.get("armor") or {}
        inv = f.get("inventory") or []
        # Three-state outcome on the per-run page.
        status = self.status or ("alive" if f.get("alive") else "dead")
        if status == "stuck":
            alive_class = "stuck"
            outcome_label = "STUCK"
        elif status == "alive":
            alive_class = "alive"
            outcome_label = "SURVIVED"
        else:
            alive_class = "dead"
            outcome_label = "FELL"
        if self.status_reason:
            outcome_label = f"{outcome_label} · {self.status_reason}"

        # Per-page sprite registry -- collects every pid referenced
        # on this page and emits a single dedup'd <style> block.
        sprites = SpriteRegistry()

        # Player sprite: mirror the IN-GAME character pick. The game's
        # generate_player_sprite_html (sprite_data.py:182) seeds the
        # pool with (race, gender, character_name) so a fresh
        # character gets a stable-but-unique look that matches what
        # they'd see launching this seed in the actual game. The
        # playtest report previously used (race, name) which produced
        # a DIFFERENT sprite for the same hero, breaking the visual
        # link between reports and live runs. User-flagged: "use the
        # race to sprite assignments in the game for the playtest."
        try:
            from .sprites import characters as _csprites, get_generic_variant
            pid = get_generic_variant(
                _csprites._CHARACTERS_POOL,
                seed=(self.race, self.gender, self.name),
            )
            self.player_sprite_pid = pid
            player_sprite_html = _sprite_span(sprites, pid, size=96,
                                              extra_class="player-sprite")
        except Exception:
            player_sprite_html = ""

        # Equipped weapon + armor sprites for the overview banner.
        wpn_pid = _sprite_pid_for("weapon", wpn.get("name")) if wpn else None
        arm_pid = _sprite_pid_for("armor", arm.get("name")) if arm else None
        wpn_sprite = _sprite_span(sprites, wpn_pid, size=48)
        arm_sprite = _sprite_span(sprites, arm_pid, size=48)

        # Charts
        hp_chart = self._hp_chart_svg()
        mana_chart = self._mana_chart_svg()
        hunger_chart = self._hunger_chart_svg()

        kills_total = sum(self.kills_by_floor.values())
        kills_by_floor_lines = "".join(
            f"<tr><td>Floor {fl}</td><td>{c}</td></tr>"
            for fl, c in sorted(self.kills_by_floor.items())
        )
        # Per-floor movement efficiency table
        all_floors = sorted(set(self.moves_by_floor) | set(self.first_visit_moves)
                            | set(self.revisit_moves) | set(self.visited_tiles_by_floor))
        movement_rows = ""
        total_moves = 0
        total_first = 0
        total_revisit = 0
        total_unique = 0
        for fl in all_floors:
            moves = self.moves_by_floor.get(fl, 0)
            first = self.first_visit_moves.get(fl, 0)
            revisit = self.revisit_moves.get(fl, 0)
            unique = len(self.visited_tiles_by_floor.get(fl, set()))
            waste_pct = (revisit / moves * 100.0) if moves else 0
            total_moves += moves
            total_first += first
            total_revisit += revisit
            total_unique += unique
            movement_rows += (
                f"<tr><td>Floor {fl}</td><td>{moves}</td>"
                f"<td>{unique}</td><td>{first}</td>"
                f"<td>{revisit}</td><td>{waste_pct:.0f}%</td></tr>"
            )
        overall_waste = (total_revisit / total_moves * 100.0) if total_moves else 0
        # Per-floor exploration efficiency. Shows what fraction of
        # each floor's available monsters / XP / boon rooms the
        # agent actually engaged. Big gaps here = unclaimed survival
        # value. User-requested ('evaluate exp + treasure left').
        exploration_rows = ""
        sorted_floors = sorted(self.floor_totals.keys())
        for fl in sorted_floors:
            tot = self.floor_totals.get(fl) or {}
            mt = tot.get("M", 0)
            ct = tot.get("C", 0)
            xp_pool_fl = tot.get("xp_pool", 0)
            kills_fl = self.kills_by_floor.get(fl, 0)
            xp_earned_fl = self.xp_by_floor.get(fl, 0)
            boon_count = sum(tot.get(k, 0) for k in ("G", "L", "O", "A", "P", "Q", "K", "B", "F"))
            kpct = (kills_fl / mt * 100.0) if mt else 0
            xpct = (xp_earned_fl / xp_pool_fl * 100.0) if xp_pool_fl else 0
            exploration_rows += (
                f"<tr><td>Floor {fl}</td>"
                f"<td>{kills_fl}/{mt}</td><td>{kpct:.0f}%</td>"
                f"<td>{xp_earned_fl}/{xp_pool_fl}</td><td>{xpct:.0f}%</td>"
                f"<td>{ct}</td><td>{boon_count}</td>"
                f"<td>{tot.get('V', 0)}</td><td>{tot.get('T', 0)}</td></tr>"
            )
        total_M_all = sum(t.get("M", 0) for t in self.floor_totals.values())
        total_xp_pool_all = sum(t.get("xp_pool", 0) for t in self.floor_totals.values())
        total_kills_all = sum(self.kills_by_floor.values())
        total_xp_earned_all = sum(self.xp_by_floor.values())
        total_kpct = (total_kills_all / total_M_all * 100.0) if total_M_all else 0
        total_xpct = (total_xp_earned_all / total_xp_pool_all * 100.0) if total_xp_pool_all else 0
        total_ct = sum(t.get("C", 0) for t in self.floor_totals.values())
        total_boons_all = sum(t.get(k, 0) for t in self.floor_totals.values()
                              for k in ("G", "L", "O", "A", "P", "Q", "K", "B", "F"))
        total_V_all = sum(t.get("V", 0) for t in self.floor_totals.values())
        total_T_all = sum(t.get("T", 0) for t in self.floor_totals.values())
        exploration_rows += (
            f"<tr style='font-weight:bold; border-top: 2px solid #444;'>"
            f"<td>Total</td>"
            f"<td>{total_kills_all}/{total_M_all}</td><td>{total_kpct:.0f}%</td>"
            f"<td>{total_xp_earned_all}/{total_xp_pool_all}</td><td>{total_xpct:.0f}%</td>"
            f"<td>{total_ct}</td><td>{total_boons_all}</td>"
            f"<td>{total_V_all}</td><td>{total_T_all}</td></tr>"
        )
        movement_rows += (
            f"<tr style='font-weight:bold; border-top: 2px solid #444;'>"
            f"<td>Total</td><td>{total_moves}</td><td>{total_unique}</td>"
            f"<td>{total_first}</td><td>{total_revisit}</td>"
            f"<td>{overall_waste:.0f}%</td></tr>"
        )
        kills_by_monster_lines = "".join(
            f"<tr><td>{_sprite_span(sprites, _sprite_pid_for('monster', n), size=32)} "
            f"{html.escape(n)}</td><td>{c}</td></tr>"
            for n, c in sorted(self.kills_by_monster.items(),
                               key=lambda x: -x[1])[:20]
        )
        buys_total = len(self.buys)
        # Per-item usage check. An item is "in bag" if its name shows
        # up in the final inventory, otherwise "used / consumed".
        # Equipped gear counts as both "in bag" and "equipped".
        final_inv_names = {
            (i.get("name") or "").strip().lower()
            for i in (f.get("inventory") or [])
        }
        equipped_names_lower = {
            n.lower() for n in self._ever_equipped_names if n
        }

        def _item_status(name):
            n_low = (name or "").strip().lower()
            if n_low in equipped_names_lower:
                return ("equipped", "#4ade80")
            if n_low in final_inv_names:
                return ("in bag", "#fde68a")
            return ("used", "#94a3b8")

        # Aggregated items table. The per-event lists (self.buys +
        # self.found_items) had a lot of duplicates -- agents buy
        # rations on every vendor, find healing potions from chests
        # repeatedly, etc. User feedback: "There's a lot of dupes...
        # I don't care what floor the item was found/purchased on,
        # just how many were found/purchased and how many were used."
        # Group by item NAME and report:
        #   bought (sum across all vendor buys)
        #   found  (sum across all map drops)
        #   in bag (count in final inventory)
        #   used   (max(0, total - in_bag - equipped_kept))
        # Equipped items count as "in bag" if they're still on the
        # character. Sorted by total acquired desc so the agent's
        # most-trafficked items show first.
        # Build per-name aggregates.
        agg = {}  # name -> dict(bought, found, sources_set)
        for (_t, _fl, n, _pr, c) in self.buys:
            entry = agg.setdefault(n, {"bought": 0, "found": 0, "sources": set()})
            entry["bought"] += c
        for (_t, _fl, n, src) in self.found_items:
            entry = agg.setdefault(n, {"bought": 0, "found": 0, "sources": set()})
            entry["found"] += 1
            entry["sources"].add(src)
        final_inv_counts = {}
        for it in (f.get("inventory") or []):
            nm = (it.get("name") or "").strip()
            cnt = it.get("count", 1) or 1
            final_inv_counts[nm] = final_inv_counts.get(nm, 0) + cnt

        def _agg_status(name, in_bag, total_acquired):
            if name in self._ever_equipped_names and in_bag > 0:
                return ("equipped", "#4ade80")
            if in_bag >= total_acquired and in_bag > 0:
                return ("in bag", "#fde68a")
            if in_bag > 0:
                return ("partial", "#fbbf24")
            return ("used", "#94a3b8")

        # Render rows sorted by total acquired desc.
        agg_rows = sorted(
            agg.items(),
            key=lambda kv: -(kv[1]["bought"] + kv[1]["found"]),
        )
        items_lines = ""
        for name, info in agg_rows:
            bought = info["bought"]
            found = info["found"]
            in_bag = final_inv_counts.get(name, 0)
            total = bought + found
            used = max(0, total - in_bag)
            item_status, color = _agg_status(name, in_bag, total)
            # Sprite: use the recorded category for the icon.
            cat = self.item_categories.get(name)
            sprite_cat = _category_to_sprite_cat(cat) if cat else None
            pid = _sprite_pid_for(sprite_cat, name) if sprite_cat else None
            sprite_cell = _sprite_span(sprites, pid, size=28) if pid else ""
            items_lines += (
                f"<tr>"
                f"<td class='sprite-cell'>{sprite_cell}</td>"
                f"<td>{html.escape(name)}</td>"
                f"<td>{found}</td>"
                f"<td>{bought}</td>"
                f"<td>{in_bag}</td>"
                f"<td>{used}</td>"
                f"<td style='color:{color};'>{item_status}</td></tr>"
            )
        items_total_rows = len(agg_rows)

        # Per-vendor (per-floor) purchase breakdown grouped by
        # category. User: "I'd like to know how many items were
        # purchased by vendor by floor and of what category."
        vendor_by_floor = {}  # floor -> {category: (count, gold_spent)}
        for (_t, fl, n, price, c) in self.buys:
            cat = self.item_categories.get(n, "other")
            f_dict = vendor_by_floor.setdefault(fl, {})
            cur = f_dict.get(cat, (0, 0))
            f_dict[cat] = (cur[0] + c, cur[1] + price * c)
        vendor_rows = ""
        for fl in sorted(vendor_by_floor):
            cats = vendor_by_floor[fl]
            total_items = sum(c for c, _ in cats.values())
            total_gold = sum(g for _, g in cats.values())
            # One li per category, all on one row.
            cat_breakdown = " · ".join(
                f"{c} {html.escape(cat)} ({g}g)"
                for cat, (c, g) in sorted(cats.items(),
                                          key=lambda x: -x[1][0])
            )
            vendor_rows += (
                f"<tr><td>F{fl}</td>"
                f"<td>{total_items}</td>"
                f"<td>{total_gold}g</td>"
                f"<td>{cat_breakdown}</td></tr>"
            )
        vendor_floor_count = len(vendor_by_floor)
        buys_total = len(self.buys)
        found_total = len(self.found_items)

        # Floor-exit summary. Combines descents (first arrivals on
        # each floor) with the per-transition method log so the
        # user can see e.g. "F2 -> F3 at T203 (stairs_down)" or
        # "F3 -> F5 at T314 (warp_forced -- skipped F4)".
        method_label = {
            "stairs_down": "stairs down",
            "stairs_up":   "stairs up",
            "warp_accept": "warp accepted",
            "warp_forced": "warp forced (resist failed)",
            "other":       "other",
        }
        method_color = {
            "stairs_down": "#94a3b8",
            "stairs_up":   "#94a3b8",
            "warp_accept": "#fb923c",
            "warp_forced": "#f43f5e",
            "other":       "#94a3b8",
        }
        descent_lines = ""
        if self.floor_exits:
            for (fr, to, t, method) in self.floor_exits:
                color = method_color.get(method, "#94a3b8")
                label = method_label.get(method, method)
                arrow = "↓" if to > fr else "↑"
                descent_lines += (
                    f"<li>T{t}: F{fr} {arrow} F{to} "
                    f"<span style='color:{color};'>({label})</span></li>"
                )
        else:
            descent_lines = "<li>never left Floor 1</li>"

        inv_rows = ""
        for i in inv[:24]:
            cat = i.get("category", "")
            sprite_cat = _category_to_sprite_cat(cat)
            pid = _sprite_pid_for(sprite_cat, i.get("name")) if sprite_cat else None
            sprite_cell = _sprite_span(sprites, pid, size=28)
            extra = ""
            if cat in ("weapon", "armor"):
                bonus = i.get("attack_bonus") or i.get("defense_bonus") or 0
                base = (i.get("base_attack_bonus")
                        if cat == "weapon"
                        else i.get("base_defense_bonus")) or 0
                upg = i.get("upgrade_level") or 0
                dur = i.get("durability")
                mx = i.get("max_durability")
                eq_flag = " ★" if i.get("equipped") else ""
                upg_note = f" ({base}+{upg})" if upg > 0 else ""
                extra = f"+{bonus}{upg_note} | dur {dur}/{mx}{eq_flag}"
            elif cat.startswith("potion") or cat == "scroll":
                extra = "identified" if i.get("is_identified") else "unidentified"
            inv_rows += (
                f"<tr><td>{i.get('slot')}</td>"
                f"<td class='sprite-cell'>{sprite_cell}</td>"
                f"<td>{html.escape(i.get('name', ''))}</td>"
                f"<td>{html.escape(cat)}</td>"
                f"<td>{i.get('count', 1)}</td>"
                f"<td>{html.escape(extra)}</td></tr>"
            )

        # Tomb-suspected floors list for the Combat tab.
        if self.tomb_sightings:
            tomb_sighting_lines = "".join(
                f"<li>T{t}: F{fl} — encountered "
                f"{_sprite_span(sprites, _sprite_pid_for('monster', n), size=24)}"
                f" <strong>{html.escape(n)}</strong>"
                f" → tomb suspected on Floor {fl}</li>"
                for (t, fl, n) in self.tomb_sightings
            )
        else:
            tomb_sighting_lines = (
                "<li class='muted'>no undead encountered — no tombs suspected</li>"
            )

        # Mid-run loop episodes (escaped wedges). Each row names the
        # mode the agent got wedged in, the dominant action, the
        # turn window, and the period. Top of the list is the
        # longest wedge -- usually where to start diagnosing.
        if self.loop_episodes:
            loop_episode_rows = "".join(
                f"<tr><td>T{e['start']}–T{e['end']}</td>"
                f"<td>{e['length']}</td>"
                f"<td>{html.escape(e['mode'])}</td>"
                f"<td><code>{html.escape(e['action'])}</code></td>"
                f"<td>period {e['period']}</td></tr>"
                for e in self.loop_episodes
            )
            loop_episode_total = sum(e["length"] for e in self.loop_episodes)
            loop_episodes_section = (
                f"<h2 style='margin-top:18px;'>Mid-run Loop Episodes "
                f"({len(self.loop_episodes)} · {loop_episode_total} turns wasted)</h2>"
                f"<p class='muted'>Stretches where the agent was caught in a tight "
                f"period-1..4 action cycle for 50+ turns before escaping. The mode + "
                f"first action name where the wedge happened so the next fix targets "
                f"the right handler. Long episodes here = the harness's anti-wedge "
                f"needed to fight through a real softlock.</p>"
                f"<table><tr><th>Turns</th><th>Length</th><th>Mode</th>"
                f"<th>Action</th><th>Cycle</th></tr>{loop_episode_rows}</table>"
            )
        else:
            loop_episodes_section = (
                "<h2 style='margin-top:18px;'>Mid-run Loop Episodes</h2>"
                "<p class='muted'>None — the agent never wedged in a tight cycle for 50+ turns.</p>"
            )

        actions_html = "".join(
            f"<li>T{t} <span class='mode'>{html.escape(m)}</span>: "
            f"<code>{html.escape(a)}</code></li>"
            for (t, m, a) in self.recent_actions
        )

        log_html = "".join(
            f"<li>T{t}: {html.escape(l)}</li>"
            for (t, l) in self.recent_log[-30:]
        )

        spells_html = ", ".join(html.escape(s) for s in self.spells) or "—"

        # Last-seen killer sprite for the death scene. Match the
        # derived death-cause string against a monster name when
        # possible -- "defeated by <name>" puts the killer's sprite at
        # the top of the Combat tab.
        killer_sprite = ""
        if not f.get("alive") and self.death_cause:
            m = re.search(r"defeated by (?:the )?(.+)$", self.death_cause)
            if m:
                killer_name = m.group(1).strip()
                killer_pid = _sprite_pid_for("monster", killer_name)
                killer_sprite = _sprite_span(sprites, killer_pid, size=64)

        death_block = ""
        if not f.get("alive"):
            death_block = f"""
        <div class="death-banner">
          {killer_sprite}
          <p class="cause">Cause: <strong>{html.escape(self.death_cause or '?')}</strong></p>
        </div>
        <h3>Last 30 log lines</h3>
        <ol class="log">{log_html}</ol>
        <h3>Last actions</h3>
        <ol class="actions">{actions_html}</ol>
        """
        elif status == "stuck":
            death_block = f"""
        <div class="stuck-banner">
          <p class="cause">Stuck: <strong>{html.escape(self.status_reason or '?')}</strong></p>
        </div>
        <h3>Last 30 log lines</h3>
        <ol class="log">{log_html}</ol>
        <h3>Last actions</h3>
        <ol class="actions">{actions_html}</ol>
        """

        page_html = Template(_TABBED_PAGE_TEMPLATE).safe_substitute(
            title=html.escape(f"{self.name} the {self.race}"),
            name=html.escape(self.name),
            race=html.escape(self.race),
            gender=html.escape(self.gender),
            seed=self.seed,
            outcome_label=outcome_label,
            alive_class=alive_class,
            started=html.escape(self.start_iso),
            spells=spells_html,
            stats_hp=f.get("hp"),
            stats_max_hp=f.get("max_hp"),
            stats_mana=f.get("mana"),
            stats_max_mana=f.get("max_mana"),
            stats_gold=f.get("gold"),
            stats_level=f.get("level"),
            stats_xp=f.get("xp"),
            stats_hunger=f.get("hunger"),
            stats_str=f.get("strength") or "—",
            stats_dex=f.get("dexterity") or "—",
            stats_int=f.get("intelligence") or "—",
            stats_can_cast=("yes" if f.get("can_cast") else "no (int <= 15)"),
            start_str=self.starting_stats.get("strength") or "—",
            start_dex=self.starting_stats.get("dexterity") or "—",
            start_int=self.starting_stats.get("intelligence") or "—",
            stats_turn=f.get("turn"),
            stats_max_floor=self.max_floor,
            stats_kills=kills_total,
            stats_buys=buys_total,
            stats_identifies=len(self.identifies),
            weapon_name=html.escape(wpn.get("name") or "—"),
            weapon_atk=wpn.get("attack_bonus") or 0,
            weapon_base_atk=wpn.get("base_attack_bonus") or 0,
            weapon_upgrades=wpn.get("upgrade_level") or 0,
            weapon_dur=wpn.get("durability") or 0,
            weapon_mxd=wpn.get("max_durability") or 0,
            weapon_buc=html.escape(wpn.get("buc_status") or ""),
            weapon_sprite=wpn_sprite,
            armor_name=html.escape(arm.get("name") or "—"),
            armor_def=arm.get("defense_bonus") or 0,
            armor_base_def=arm.get("base_defense_bonus") or 0,
            armor_upgrades=arm.get("upgrade_level") or 0,
            armor_dur=arm.get("durability") or 0,
            armor_mxd=arm.get("max_durability") or 0,
            armor_buc=html.escape(arm.get("buc_status") or ""),
            armor_sprite=arm_sprite,
            player_sprite=player_sprite_html,
            hp_chart=hp_chart,
            mana_chart=mana_chart,
            hunger_chart=hunger_chart,
            kills_by_floor=kills_by_floor_lines or "<tr><td colspan='2'>no kills logged</td></tr>",
            kills_by_monster=kills_by_monster_lines or "<tr><td colspan='2'>—</td></tr>",
            items_lines=items_lines or "<tr><td colspan='7'>no items</td></tr>",
            items_total_rows=items_total_rows,
            vendor_rows=vendor_rows or "<tr><td colspan='4'>no vendor purchases</td></tr>",
            vendor_floor_count=vendor_floor_count,
            buys_total=buys_total,
            found_total=found_total,
            descent_lines=descent_lines,
            warp_pct=f"{(sum(1 for (_a, _b, _t, m) in self.floor_exits if m in ('warp_accept', 'warp_forced')) / len(self.floor_exits) * 100.0):.0f}" if self.floor_exits else "0",
            floor_changes=len(self.floor_exits),
            warp_changes=sum(1 for (_a, _b, _t, m) in self.floor_exits if m in ("warp_accept", "warp_forced")),
            warp_accepts=sum(1 for (_a, _b, _t, m) in self.floor_exits if m == "warp_accept"),
            warp_forced=sum(1 for (_a, _b, _t, m) in self.floor_exits if m == "warp_forced"),
            inventory_rows=inv_rows or "<tr><td colspan='6'>—</td></tr>",
            movement_rows=movement_rows or "<tr><td colspan='6'>no movement logged</td></tr>",
            overall_waste=f"{overall_waste:.0f}",
            exploration_rows=exploration_rows or "<tr><td colspan='9'>no floor totals captured</td></tr>",
            overall_kill_pct=f"{total_kpct:.0f}",
            overall_xp_pct=f"{total_xpct:.0f}",
            tomb_sighting_lines=tomb_sighting_lines,
            tomb_floor_count=len(self.tomb_suspected_floors),
            loop_episodes_section=loop_episodes_section,
            death_block=death_block,
            sprite_styles=sprites.style_block(),
        )
        return page_html

    def _hp_chart_svg(self):
        return self._timeline_chart_svg(
            self.hp_timeline, "#f43f5e", "HP", with_max=True,
        )

    def _mana_chart_svg(self):
        return self._timeline_chart_svg(
            self.mana_timeline, "#38bdf8", "Mana", with_max=True,
        )

    def _hunger_chart_svg(self):
        # Hunger has a fixed 0-100 scale, so reuse the timeline helper
        # with a "max value 100" override that doesn't read from the
        # timeline tuples.
        if not self.hunger_timeline:
            return "<p class='nochart'>no hunger samples</p>"
        pts = self.hunger_timeline
        if len(pts) > 200:
            stride = len(pts) // 200
            pts = pts[::stride] + [pts[-1]]
        max_turn = max(p[0] for p in pts) or 1
        W, H = 800, 200
        coords = []
        # Mark the starvation zone (hunger <= 30): a red band at the
        # bottom of the chart so the eye can tell at a glance when the
        # agent was starving.
        starve_y = H - 10 - (30 / 100) * (H - 20)
        for (t, h) in pts:
            x = (t / max_turn) * (W - 20) + 10
            y = H - 10 - ((h or 0) / 100) * (H - 20)
            coords.append(f"{x:.1f},{y:.1f}")
        path = " ".join(coords)
        return (
            f"<svg viewBox='0 0 {W} {H}' class='hpchart' "
            f"xmlns='http://www.w3.org/2000/svg'>"
            f"<rect x='0' y='0' width='{W}' height='{H}' fill='#1a1a1a'/>"
            f"<rect x='10' y='{starve_y:.1f}' width='{W-20}' "
            f"height='{H-10-starve_y:.1f}' fill='#5a131333'/>"
            f"<polyline points='{path}' fill='none' "
            f"stroke='#fb923c' stroke-width='1.5'/>"
            f"<text x='10' y='15' fill='#aaa' font-size='11'>"
            f"Hunger 0..100 over T0..T{max_turn} "
            f"(red band = starving)</text>"
            f"</svg>"
        )

    def _timeline_chart_svg(self, timeline, color, label, with_max=True):
        if not timeline:
            return f"<p class='nochart'>no {label} samples</p>"
        # Sample down to ~200 points for readability
        pts = timeline
        if len(pts) > 200:
            stride = len(pts) // 200
            pts = pts[::stride] + [pts[-1]]
        max_turn = max(p[0] for p in pts) or 1
        if with_max:
            scale_max = max((p[2] if len(p) > 2 else 1) for p in pts) or 1
        else:
            scale_max = max((p[1] for p in pts), default=1) or 1
        W, H = 800, 200
        coords = []
        for entry in pts:
            t = entry[0]
            v = entry[1] or 0
            x = (t / max_turn) * (W - 20) + 10
            y = H - 10 - (v / scale_max) * (H - 20)
            coords.append(f"{x:.1f},{y:.1f}")
        path = " ".join(coords)
        return (
            f"<svg viewBox='0 0 {W} {H}' class='hpchart' "
            f"xmlns='http://www.w3.org/2000/svg'>"
            f"<rect x='0' y='0' width='{W}' height='{H}' fill='#1a1a1a'/>"
            f"<polyline points='{path}' fill='none' "
            f"stroke='{color}' stroke-width='1.5'/>"
            f"<text x='10' y='15' fill='#aaa' font-size='11'>"
            f"{label} over T0..T{max_turn}, max {scale_max}</text>"
            f"</svg>"
        )


# ----------------------------------------------------------------------
# HTML templates -- inline so the report is fully self-contained
# ----------------------------------------------------------------------

_CSS = """
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", monospace;
  background: #0c0c0c; color: #e6e6e6;
  max-width: 1100px; margin-left: auto; margin-right: auto;
}
h1 { font-size: 22px; margin: 0 0 4px 0; }
h2 { font-size: 16px; margin-top: 0; color: #fbbf24; border-bottom: 1px solid #333; padding-bottom: 4px; }
h3 { font-size: 13px; color: #94a3b8; margin: 16px 0 6px 0; }
a { color: #38bdf8; text-decoration: none; }
a:hover { text-decoration: underline; }
.muted { color: #888; font-size: 12px; }
.card {
  background: #161616; border: 1px solid #2a2a2a;
  border-radius: 6px; padding: 14px 18px; margin: 14px 0;
}
.outcome {
  display: inline-block; padding: 4px 10px; border-radius: 4px;
  font-weight: bold; letter-spacing: 0.05em;
}
.outcome.alive { background: #134e2b; color: #bbf7d0; }
.outcome.dead { background: #5a1313; color: #fecaca; }
.outcome.stuck { background: #4a3a0a; color: #fde68a; }
.stuck-banner { display:flex; align-items:center; gap:14px;
  padding:10px; background:#1a160a; border-left:3px solid #fbbf24;
  border-radius:4px; margin-bottom:10px;
}
.stuck-banner .cause strong { color: #fbbf24; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
.grid4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 14px; }
/* Mobile-friendly layout. Body padding shrinks, hero portrait stacks
   above the info column, the Final Tally drops from 4 columns to 2,
   gear cards stack, tab labels shrink, tables get a touch smaller.
   The two breakpoints (800 / 600) cover tablet and phone-portrait. */
@media (max-width: 800px) {
  .grid4 { grid-template-columns: 1fr 1fr; }
  .grid3 { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 600px) {
  body { padding: 12px; }
  .card { padding: 10px 12px; }
  h1 { font-size: 18px; }
  h2 { font-size: 14px; }
  .grid4, .grid3, .grid2 { grid-template-columns: 1fr; }
  .hero-banner {
    grid-template-columns: 1fr;
    text-align: center;
  }
  .hero-portrait { min-height: auto; }
  .gear-cards { grid-template-columns: 1fr; }
  .tabs > label {
    padding: 6px 10px;
    font-size: 12px;
    margin-right: 1px;
  }
  .tab-panels { padding: 10px 12px; }
  table { font-size: 11px; }
  th, td { padding: 3px 4px; }
  .stat { font-size: 12px; }
  .hpchart { /* Stretch the SVG full-width on small screens */
    max-width: 100%;
  }
}
.stat { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dotted #2a2a2a; }
.stat:last-child { border-bottom: none; }
.stat .v { color: #fde68a; font-weight: 600; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid #222; }
th { color: #94a3b8; font-weight: normal; }
.log, .actions { font-family: ui-monospace, monospace; font-size: 11px;
  background: #0a0a0a; padding: 10px; border-radius: 4px;
  max-height: 320px; overflow-y: auto; }
.log li, .actions li { list-style: none; padding: 2px 0; }
.actions code { color: #67e8f9; }
.mode { color: #94a3b8; font-size: 10px; }
.cause strong { color: #fb923c; }
.death { border-left: 3px solid #f43f5e; }
.death-banner { display:flex; align-items:center; gap:14px;
  padding:10px; background:#1a0c0c; border-left:3px solid #f43f5e;
  border-radius:4px; margin-bottom:10px;
}
.hpchart { width: 100%; height: auto; border-radius: 4px; }

/* Sprite system: each sprite renders as a background-image on a <span>,
   so a sprite referenced N times only embeds the base64 webp once. */
.sprite {
  display: inline-block;
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  image-rendering: pixelated;
  vertical-align: middle;
  margin-right: 6px;
}
.player-sprite { display:block; margin: 0 auto; image-rendering: pixelated; }
.sprite-cell { width: 36px; }

/* Hero banner with portrait + headline stats side by side. */
.hero-banner {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 18px;
  align-items: center;
}
.hero-portrait {
  background: #0a0a0a;
  border: 1px solid #2a2a2a;
  border-radius: 6px;
  padding: 8px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 120px;
}
.hero-info p { margin: 4px 0; }
.gear-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.gear-card {
  display: flex;
  gap: 12px;
  align-items: center;
  background: #0a0a0a;
  border: 1px solid #2a2a2a;
  border-radius: 4px;
  padding: 10px;
}
.gear-card .sprite { width: 48px; height: 48px; margin-right: 0; }
.gear-card .gear-meta { flex: 1; }

/* Tabs -- pure-CSS radio-button pattern, no JS required. */
.tabs { margin-top: 14px; }
.tabs input[type=radio] { position: absolute; opacity: 0; pointer-events: none; }
.tabs > label {
  display: inline-block;
  padding: 8px 14px;
  background: #161616;
  border: 1px solid #2a2a2a;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  font-size: 13px;
  color: #94a3b8;
  cursor: pointer;
  margin-right: 2px;
  margin-bottom: -1px;
  transition: background .15s;
}
.tabs > label:hover { background: #1f1f1f; color: #fde68a; }
.tabs > input[type=radio]:checked + label {
  background: #2a1f0a;
  color: #fbbf24;
  border-bottom: 1px solid #2a1f0a;
}
.tab-panels { background: #161616; border: 1px solid #2a2a2a;
  border-radius: 0 6px 6px 6px; padding: 14px 18px; }
.tab-panel { display: none; }
/* Show the panel whose paired radio is :checked. ~ matches siblings
   that follow the input, and the panels live right after the labels. */
#tab-overview:checked ~ .tab-panels #panel-overview,
#tab-stats:checked ~ .tab-panels #panel-stats,
#tab-equipment:checked ~ .tab-panels #panel-equipment,
#tab-combat:checked ~ .tab-panels #panel-combat,
#tab-journey:checked ~ .tab-panels #panel-journey { display: block; }

.chart-block { margin: 16px 0; }
.chart-block h3 { margin-top: 0; }
.tomb-list { list-style: none; padding: 0; }
.tomb-list li { padding: 6px 0; border-bottom: 1px dotted #2a2a2a; }
.tomb-list li:last-child { border: none; }
.tomb-list strong { color: #f97316; }
"""

_TABBED_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title — Wizard's Cavern Playtest</title>
<style>""" + _CSS + """
$sprite_styles
</style>
</head>
<body>
<p class="muted"><a href="./index.html">← all runs</a></p>

<header class="card">
  <div class="hero-banner">
    <div class="hero-portrait">
      $player_sprite
      <p class="muted" style="margin-top:8px;font-size:11px;">$race</p>
    </div>
    <div class="hero-info">
      <h1>$name, the $race</h1>
      <p class="muted">$gender adventurer · seed $seed · started $started</p>
      <p><span class="outcome $alive_class">$outcome_label</span></p>
      <p class="muted">Memorised: $spells</p>
    </div>
  </div>
</header>

<section class="card">
  <h2>Final Tally</h2>
  <div class="grid4">
    <div>
      <div class="stat"><span>Turns lived</span><span class="v">$stats_turn</span></div>
      <div class="stat"><span>Max floor reached</span><span class="v">F$stats_max_floor</span></div>
      <div class="stat"><span>Final level</span><span class="v">L$stats_level</span></div>
      <div class="stat"><span>Experience</span><span class="v">$stats_xp</span></div>
    </div>
    <div>
      <div class="stat"><span>HP</span><span class="v">$stats_hp / $stats_max_hp</span></div>
      <div class="stat"><span>Mana</span><span class="v">$stats_mana / $stats_max_mana</span></div>
      <div class="stat"><span>Hunger</span><span class="v">$stats_hunger</span></div>
      <div class="stat"><span>Gold</span><span class="v">${stats_gold}g</span></div>
    </div>
    <div>
      <div class="stat"><span>STR</span><span class="v">$stats_str <span class="muted" style="font-weight:normal;">(start $start_str)</span></span></div>
      <div class="stat"><span>DEX</span><span class="v">$stats_dex <span class="muted" style="font-weight:normal;">(start $start_dex)</span></span></div>
      <div class="stat"><span>INT</span><span class="v">$stats_int <span class="muted" style="font-weight:normal;">(start $start_int)</span></span></div>
      <div class="stat"><span>Can cast</span><span class="v">$stats_can_cast</span></div>
    </div>
    <div>
      <div class="stat"><span>Total kills</span><span class="v">$stats_kills</span></div>
      <div class="stat"><span>Items bought</span><span class="v">$stats_buys</span></div>
      <div class="stat"><span>Items identified</span><span class="v">$stats_identifies</span></div>
      <div class="stat"><span>Tombs suspected</span><span class="v">$tomb_floor_count</span></div>
    </div>
  </div>
</section>

<div class="tabs">
  <input type="radio" name="rep-tabs" id="tab-overview" checked>
  <label for="tab-overview">Overview</label>
  <input type="radio" name="rep-tabs" id="tab-stats">
  <label for="tab-stats">Stats</label>
  <input type="radio" name="rep-tabs" id="tab-equipment">
  <label for="tab-equipment">Equipment</label>
  <input type="radio" name="rep-tabs" id="tab-combat">
  <label for="tab-combat">Combat</label>
  <input type="radio" name="rep-tabs" id="tab-journey">
  <label for="tab-journey">Journey</label>

  <div class="tab-panels">
    <!-- Overview -->
    <div class="tab-panel" id="panel-overview">
      <h2>Equipment at end</h2>
      <div class="gear-cards">
        <div class="gear-card">
          $weapon_sprite
          <div class="gear-meta">
            <h3 style="margin:0;">Weapon</h3>
            <p style="margin:4px 0;">$weapon_name</p>
            <p class="muted" style="margin:0;">+$weapon_atk atk ($weapon_base_atk base + $weapon_upgrades upg) · dur $weapon_dur/$weapon_mxd · $weapon_buc</p>
          </div>
        </div>
        <div class="gear-card">
          $armor_sprite
          <div class="gear-meta">
            <h3 style="margin:0;">Armor</h3>
            <p style="margin:4px 0;">$armor_name</p>
            <p class="muted" style="margin:0;">+$armor_def def ($armor_base_def base + $armor_upgrades upg) · dur $armor_dur/$armor_mxd · $armor_buc</p>
          </div>
        </div>
      </div>
      <div class="chart-block">
        <h3>HP arc</h3>
        $hp_chart
      </div>
    </div>

    <!-- Stats -->
    <div class="tab-panel" id="panel-stats">
      <div class="chart-block">
        <h3>HP over the run</h3>
        $hp_chart
      </div>
      <div class="chart-block">
        <h3>Mana over the run</h3>
        $mana_chart
      </div>
      <div class="chart-block">
        <h3>Hunger over the run</h3>
        $hunger_chart
      </div>
    </div>

    <!-- Equipment + Inventory -->
    <div class="tab-panel" id="panel-equipment">
      <h2>Equipped</h2>
      <div class="gear-cards">
        <div class="gear-card">
          $weapon_sprite
          <div class="gear-meta">
            <h3 style="margin:0;">Weapon</h3>
            <p style="margin:4px 0;">$weapon_name</p>
            <p class="muted" style="margin:0;">+$weapon_atk atk ($weapon_base_atk base + $weapon_upgrades upg) · dur $weapon_dur/$weapon_mxd · $weapon_buc</p>
          </div>
        </div>
        <div class="gear-card">
          $armor_sprite
          <div class="gear-meta">
            <h3 style="margin:0;">Armor</h3>
            <p style="margin:4px 0;">$armor_name</p>
            <p class="muted" style="margin:0;">+$armor_def def ($armor_base_def base + $armor_upgrades upg) · dur $armor_dur/$armor_mxd · $armor_buc</p>
          </div>
        </div>
      </div>
      <h2 style="margin-top:18px;">Final Inventory</h2>
      <table><tr><th>Slot</th><th></th><th>Name</th><th>Category</th><th>Count</th><th>Notes</th></tr>
      $inventory_rows
      </table>
    </div>

    <!-- Combat -->
    <div class="tab-panel" id="panel-combat">
      <h2>Top Victims</h2>
      <table><tr><th>Monster</th><th>Kills</th></tr>
      $kills_by_monster
      </table>
      <h2 style="margin-top:18px;">Kills by floor</h2>
      <table>$kills_by_floor</table>
      <h2 style="margin-top:18px;">Tomb-suspected floors</h2>
      <p class="muted">Encountering an undead is a reliable tell that a
        tomb is on the floor; the policy drops M/T from its priority
        list while weak on flagged floors to avoid blundering into the
        elite guardian.</p>
      <ul class="tomb-list">$tomb_sighting_lines</ul>
      $loop_episodes_section
      $death_block
    </div>

    <!-- Journey -->
    <div class="tab-panel" id="panel-journey">
      <h2>Floor Transitions</h2>
      <p class="muted">How each floor was left.
        <span style="color:#94a3b8;">stairs</span> = chosen,
        <span style="color:#fb923c;">warp accepted</span> = trapped-escape valve,
        <span style="color:#f43f5e;">warp forced</span> = resist roll failed.
        <strong>Warp share of floor changes: $warp_pct%</strong>
        ($warp_changes warp / $floor_changes total · $warp_accepts accepted, $warp_forced forced).</p>
      <ul>$descent_lines</ul>
      <h2 style="margin-top:18px;">Movement Efficiency · overall waste $overall_waste%</h2>
      <p class="muted">First-visit moves discover new ground; revisits
        are moves that step onto a tile the agent has already stood on
        this floor. High waste% = patrol-bouncing.</p>
      <table>
        <tr><th>Floor</th><th>Moves</th><th>Unique tiles</th><th>First-visit</th><th>Revisit</th><th>Waste %</th></tr>
        $movement_rows
      </table>
      <h2 style="margin-top:18px;">Exploration · kills $overall_kill_pct% · XP $overall_xp_pct%</h2>
      <p class="muted">Per-floor share of available monsters
        engaged and XP banked. Big gaps indicate unclaimed survival
        value (missed kills, missed level-ups). Boons = G/L/O/A/P/Q/K/B/F;
        V = vendor rooms; T = tombs (each has 4 cardinal guardians).
        Totals capped at 100% -- dynamic spawns (tomb-raid spirits,
        same-coord respawns across revisits) can push the
        numerator past the static M-tile pool, so the cap reads as
        "% of MINIMUM available pool". Per-floor rows show raw
        ratios for diagnosis.</p>
      <table>
        <tr><th>Floor</th><th>Kills</th><th>Kill %</th><th>XP</th><th>XP %</th><th>Chests</th><th>Boons</th><th>V</th><th>T</th></tr>
        $exploration_rows
      </table>
      <h2 style="margin-top:18px;">Items ($items_total_rows unique · $buys_total bought · $found_total found)</h2>
      <p class="muted">Aggregated by item name across the run. Status:
        <span style="color:#4ade80;">equipped</span> at some point,
        <span style="color:#fde68a;">in bag</span> still held at death/end,
        <span style="color:#fbbf24;">partial</span> some held / some used,
        <span style="color:#94a3b8;">used</span> fully consumed.</p>
      <table>
        <tr><th></th><th>Item</th><th>Found</th><th>Bought</th><th>In bag</th><th>Used</th><th>Status</th></tr>
        $items_lines
      </table>
      <h2 style="margin-top:18px;">Vendor Purchases by Floor ($vendor_floor_count vendors)</h2>
      <p class="muted">Grouped by the floor's vendor. Category breakdown shows
        what was bought + how much gold went toward each category.</p>
      <table>
        <tr><th>Floor</th><th>Items</th><th>Gold spent</th><th>By category</th></tr>
        $vendor_rows
      </table>
    </div>
  </div>
</div>

</body>
</html>
"""

# Backwards-compatible alias: deployed older scripts may import this
# name. Points at the new tabbed template.
INDEX_PAGE_TEMPLATE_RUN = _TABBED_PAGE_TEMPLATE


_INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wizard's Cavern — Playtest Reports</title>
<style>""" + _CSS + """
.runs th, .runs td { font-size: 13px; padding: 6px 8px; }
.runs tr:hover { background: #1a1a1a; }
.tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; }
.tag.alive { background: #134e2b; color: #bbf7d0; }
.tag.dead { background: #5a1313; color: #fecaca; }
.tag.stuck { background: #4a3a0a; color: #fde68a; }
</style>
</head>
<body>
<header class="card">
  <h1>Wizard's Cavern · Playtest Reports</h1>
  <p class="muted">$count runs · generated $generated</p>
</header>

<section class="card">
  <h2>Runs</h2>
  <table class="runs">
    <tr>
      <th>Hero</th><th>Race</th><th>Seed</th><th>Outcome</th>
      <th>Turns</th><th>Floor</th><th>Level</th><th>HP</th>
      <th>Gold</th><th>Kills</th><th>Waste %</th><th>Warp %</th><th>XP %</th>
      <th title="Mid-run loop episodes &gt;= 50 turns (count · total turns wasted)">Loops</th>
      <th>Cause</th>
    </tr>
    $rows
  </table>
</section>
</body>
</html>
"""


def _index_row(d):
    """Render one <tr> for the index table from a JSON summary dict.

    Status reads from the new 'status' field (alive / dead / stuck)
    when present, else falls back to the legacy 'alive' bool so old
    sidecars from before the three-state classifier still render."""
    status = d.get("status")
    if not status:
        status = "alive" if d.get("alive") else "dead"
    cause = d.get("status_reason") if status == "stuck" else d.get("death_cause", "—")
    cause = cause or "—"
    return (
        f"<tr>"
        f"<td><a href='{d['slug']}.html'>{html.escape(d.get('name','?'))}</a></td>"
        f"<td>{html.escape(d.get('race','?'))}</td>"
        f"<td>{d.get('seed','?')}</td>"
        f"<td><span class='tag {status}'>{status}</span></td>"
        f"<td>{d.get('turn','?')}</td>"
        f"<td>F{d.get('max_floor','?')}</td>"
        f"<td>L{d.get('level','?')}</td>"
        f"<td>{d.get('hp','?')}/{d.get('max_hp','?')}</td>"
        f"<td>{d.get('gold','?')}g</td>"
        f"<td>{d.get('kills','?')}</td>"
        f"<td>{d.get('wasted_pct','?')}%</td>"
        f"<td>{d.get('warp_pct','?')}% "
        f"<span style='color:#94a3b8;font-size:0.85em;'>"
        f"({d.get('warp_changes', 0)}/{d.get('floor_changes', 0)})"
        f"</span></td>"
        f"<td>{d.get('xp_pct','?')}% "
        f"<span style='color:#94a3b8;font-size:0.85em;'>"
        f"({d.get('xp_earned', 0)}/{d.get('xp_pool', 0)})"
        f"</span></td>"
        f"<td>{_loops_cell(d)}</td>"
        f"<td>{html.escape(str(cause))}</td>"
        f"</tr>"
    )


def _loops_cell(d):
    """Render the Loops column: count × total-turns-wasted, with
    the row tinted amber when the agent wasted heavy time wedged.
    Old JSON sidecars without the field render as a dash."""
    n = d.get("loop_episode_count")
    if n is None:
        return "—"
    if n == 0:
        return "<span class='muted'>0</span>"
    total = d.get("loop_turns_total", 0)
    color = "#fbbf24" if total >= 200 else "#fde68a"
    return (
        f"<span style='color:{color};'>{n}</span> "
        f"<span style='color:#94a3b8;font-size:0.85em;'>"
        f"({total} turns)</span>"
    )


def write_report(report, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    page_path = out_dir / f"{report.slug}.html"
    page_path.write_text(report.to_html(), encoding="utf-8")
    # Also write a JSON sidecar for index regeneration and external use
    json_path = out_dir / f"{report.slug}.json"
    json_path.write_text(json.dumps(report.summary_row(), indent=2),
                         encoding="utf-8")
    return page_path


def write_index(out_dir):
    """Regenerate index.html from the JSON sidecars in out_dir."""
    out_dir = Path(out_dir)
    rows = []
    summaries = []
    for jp in sorted(out_dir.glob("*.json")):
        try:
            data = json.loads(jp.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        summaries.append(data)

    summaries.sort(key=lambda d: (-(d.get("max_floor") or 0),
                                   -(d.get("level") or 0),
                                   d.get("seed") or 0))
    for d in summaries:
        rows.append(_index_row(d))
    body = Template(_INDEX_TEMPLATE).safe_substitute(
        count=len(summaries),
        generated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rows="\n".join(rows) or "<tr><td colspan='15'>no runs yet</td></tr>",
    )
    (out_dir / "index.html").write_text(body, encoding="utf-8")


def deploy_gh_pages(out_dir, repo_root, branch="main", remote="origin",
                    sub_path="docs/playtest", replace=False):
    """Push `out_dir` contents to `<branch>:<sub_path>/`.

    Default target is `main:docs/playtest/` because dachhack/LegendOfZot
    serves GitHub Pages from `main:docs/` (per repo settings), and we
    don't want to clobber the existing spell-sprite-audit site. The
    reports land at `https://dachhack.github.io/LegendOfZot/playtest/`.

    ``replace=False`` (default) is ADDITIVE: existing files at
    ``<sub_path>/`` are preserved unless a same-named report has been
    regenerated. Good for incremental runs that add a few new seeds.

    ``replace=True`` purges the entire ``<sub_path>/`` tree before
    overlaying the current ``out_dir``. Use after a report-template
    change so old-format pages don't linger -- e.g., when the layout
    moves from a single-page card list to the tabbed sprite-rich
    format and a stale seed-1800 page from the prior format sticks
    around because the current grid doesn't cover that seed.

    Uses git plumbing (hash-object / ls-tree / mktree / commit-tree)
    so the deploy never modifies the working tree or index, never
    creates a worktree (sandboxed environments often refuse signing
    on auxiliary paths). Files outside ``<sub_path>/`` (the rest of
    the repository) are always passed through unchanged.

    Returns the remote URL on success, or None if the deploy was a
    no-op (resulting commit tree matches parent's).
    """
    import subprocess

    out_dir = Path(out_dir).resolve()
    repo_root = Path(repo_root).resolve()

    def run(cmd, cwd=None, check=True, input_text=None):
        res = subprocess.run(
            cmd, cwd=str(cwd or repo_root), check=False,
            capture_output=True, text=True, input=input_text,
        )
        if check and res.returncode != 0:
            raise RuntimeError(
                f"git step failed (rc={res.returncode}): "
                f"{' '.join(cmd)}\n  stdout: {res.stdout.strip()}\n"
                f"  stderr: {res.stderr.strip()}"
            )
        return res

    def read_tree(sha):
        """Return {name: (mode, type, sha)} for a tree object SHA, or
        {} if the SHA is None / non-existent."""
        if not sha:
            return {}
        ls = run(["git", "ls-tree", sha], check=False)
        if ls.returncode != 0:
            return {}
        out = {}
        for line in ls.stdout.strip().split("\n"):
            if not line:
                continue
            mode_type_sha, _, name = line.partition("\t")
            parts = mode_type_sha.split()
            if len(parts) >= 3:
                out[name] = (parts[0], parts[1], parts[2])
        return out

    def write_tree(entries):
        """Build a new tree object from {name: (mode, type, sha)}.
        Returns the new tree SHA."""
        tree_input = "".join(
            f"{mode} {typ} {sha}\t{name}\n"
            for name, (mode, typ, sha) in sorted(entries.items())
        )
        return run(["git", "mktree"], input_text=tree_input).stdout.strip()

    # 1. Fetch the remote branch so we apply on top of its latest tree.
    run(["git", "fetch", remote, branch], check=False)

    # 2. Resolve the parent commit.
    parent = None
    for ref in (f"refs/remotes/{remote}/{branch}", f"refs/heads/{branch}"):
        res = run(["git", "rev-parse", "--verify", ref], check=False)
        if res.returncode == 0:
            parent = res.stdout.strip()
            break
    if not parent:
        raise RuntimeError(
            f"branch {branch!r} has no commits on remote or local refs; "
            "cannot deploy into a subpath of a missing branch."
        )

    # 3. Walk down the path components, reading each tree level so we
    #    can rebuild from the leaf up. For `docs/playtest`:
    #      level 0 = root (commit's tree)
    #      level 1 = docs/
    #      level 2 = docs/playtest/  <- target dir
    path_parts = [p for p in sub_path.split("/") if p]
    root_tree_sha = run(
        ["git", "rev-parse", f"{parent}^{{tree}}"]
    ).stdout.strip()
    parent_trees = [read_tree(root_tree_sha)]
    for part in path_parts:
        cur_tree = parent_trees[-1]
        sub = cur_tree.get(part)
        if sub and sub[1] == "tree":
            parent_trees.append(read_tree(sub[2]))
        else:
            parent_trees.append({})  # missing subdirectory; we'll create it

    # 4. Target directory: in replace mode start from empty (purges
    #    old-format pages from prior templates); in additive mode
    #    start from what's already at <sub_path>/ (preserves prior
    #    runs deployed to the same path). Then overlay every file in
    #    `out_dir` as a fresh blob.
    if replace:
        target = {}
    else:
        target = dict(parent_trees[-1])
    for f in sorted(out_dir.iterdir()):
        if not f.is_file():
            continue
        sha = run(["git", "hash-object", "-w", str(f)]).stdout.strip()
        target[f.name] = ("100644", "blob", sha)

    # 5. Regenerate index.html from the union of all JSON sidecars in
    #    the merged target tree (so reports already on the branch keep
    #    their index entry even if not re-deployed this run).
    summaries = []
    for name, (_mode, typ, sha) in target.items():
        if typ != "blob" or not name.endswith(".json"):
            continue
        blob = run(["git", "cat-file", "blob", sha]).stdout
        try:
            summaries.append(json.loads(blob))
        except json.JSONDecodeError:
            continue
    summaries.sort(key=lambda d: (-(d.get("max_floor") or 0),
                                   -(d.get("level") or 0),
                                   d.get("seed") or 0))
    rows = []
    for d in summaries:
        rows.append(_index_row(d))
    index_html = Template(_INDEX_TEMPLATE).safe_substitute(
        count=len(summaries),
        generated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rows="\n".join(rows) or "<tr><td colspan='15'>no runs yet</td></tr>",
    )
    index_sha = run(
        ["git", "hash-object", "-w", "--stdin"], input_text=index_html
    ).stdout.strip()
    target["index.html"] = ("100644", "blob", index_sha)

    # 6. Rebuild the tree chain leaf -> root.
    new_sub_sha = write_tree(target)
    for i in range(len(path_parts) - 1, -1, -1):
        # parent_trees[i] is the directory that CONTAINS path_parts[i]
        parent_dir = dict(parent_trees[i])
        part_name = path_parts[i]
        parent_dir[part_name] = ("040000", "tree", new_sub_sha)
        # If this is the docs/ level (Pages site root), ensure
        # .nojekyll is present so the site bypasses Jekyll
        # processing -- matters for paths with underscores like
        # `00007_dwarf.html`.
        if path_parts[i] == "docs" and ".nojekyll" not in parent_dir:
            empty_sha = run(
                ["git", "hash-object", "-w", "--stdin"], input_text=""
            ).stdout.strip()
            parent_dir[".nojekyll"] = ("100644", "blob", empty_sha)
        new_sub_sha = write_tree(parent_dir)
    new_root_tree = new_sub_sha

    # 7. Skip if rebuilt root tree matches parent's (no-op).
    if new_root_tree == root_tree_sha:
        return None

    # 8. Commit and push to `branch`.
    commit_msg = (
        f"Playtest reports: "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    )
    commit_sha = run(
        ["git", "commit-tree", new_root_tree, "-p", parent, "-m", commit_msg]
    ).stdout.strip()
    run(["git", "push", remote, f"{commit_sha}:refs/heads/{branch}"])

    remote_url = run(["git", "remote", "get-url", remote],
                     check=False).stdout.strip()
    return remote_url
