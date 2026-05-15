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
        self.buys = []  # (turn, floor, name, price, count)
        self.identifies = []  # (turn, item_name)
        self.descents = []  # turn at which each new floor was first entered
        self.equipped_history = []  # (turn, weapon_name, armor_name)
        self.last_equip = (None, None)
        self.max_floor = 1
        self.last_seen_log = set()

        # Final-state fields, filled in by `finalize`
        self.final = None
        self.death_cause = None

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
            eq = p.get("equipped") or {}
            cur = ((eq.get("weapon") or {}).get("name"),
                   (eq.get("armor") or {}).get("name"))
            if cur != self.last_equip:
                self.last_equip = cur
                self.equipped_history.append((turn, cur[0], cur[1]))
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
        self.recent_actions.append((turn, mode, action))
        if len(self.recent_actions) > 12:
            self.recent_actions.pop(0)

    def _categorise_log(self, turn, line, p):
        low = line.lower()
        floor = (p or {}).get("floor", 1)

        if "you gained" in low and "experience" in low:
            self.events.append((turn, "xp", line))
            self.kills_by_floor[floor] = self.kills_by_floor.get(floor, 0) + 1

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
            "equipped": p.get("equipped") or {},
            "lantern": p.get("lantern") or {},
            "inventory": final_obs.get("inventory") or [],
            "mode": final_obs.get("mode"),
            "logs_at_end": final_logs,
        }
        if not alive:
            self.death_cause = self._derive_death_cause()

    def _derive_death_cause(self):
        """Walk recent_log backwards for a recognisable killer."""
        for (_, line) in reversed(self.recent_log):
            low = line.lower()
            if "the trap was lethal" in low or "the explosion was fatal" in low:
                return "lethal pool trap"
            if "the chest explodes" in low:
                return "chest explosion"
            m = re.search(r"you were defeated by(?: the)? ([^.]+?)\.\.\.",
                          line, re.IGNORECASE)
            if m:
                return f"defeated by {m.group(1).strip()}"
            if "starving" in low and "lost" in low:
                return "starvation"
        return "unknown"

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
            "death_cause": self.death_cause or "—",
            "started": self.start_iso,
            "moves_total": total_moves,
            "moves_revisit": total_revisit,
            "wasted_pct": round(wasted_pct, 1),
        }

    def to_html(self):
        f = self.final or {}
        eq = f.get("equipped") or {}
        wpn = eq.get("weapon") or {}
        arm = eq.get("armor") or {}
        inv = f.get("inventory") or []
        alive_class = "alive" if f.get("alive") else "dead"
        outcome_label = "SURVIVED" if f.get("alive") else "FELL"

        # Per-page sprite registry -- collects every pid referenced
        # on this page and emits a single dedup'd <style> block.
        sprites = SpriteRegistry()

        # Player sprite: generic character pool, seeded by (race, name).
        try:
            from .sprites import characters as _csprites, get_generic_variant
            pid = get_generic_variant(
                _csprites._CHARACTERS_POOL,
                seed=(self.race, self.name),
            )
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
        buy_lines = "".join(
            f"<tr><td>T{t}</td><td>F{fl}</td><td>{html.escape(n)}</td>"
            f"<td>{c}×</td><td>{p}g</td></tr>"
            for (t, fl, n, p, c) in self.buys[-30:]
        )
        descent_lines = "".join(
            f"<li>T{t}: arrived on Floor {fl}</li>"
            for (t, fl) in self.descents
        )

        inv_rows = ""
        for i in inv[:24]:
            cat = i.get("category", "")
            sprite_cat = _category_to_sprite_cat(cat)
            pid = _sprite_pid_for(sprite_cat, i.get("name")) if sprite_cat else None
            sprite_cell = _sprite_span(sprites, pid, size=28)
            extra = ""
            if cat in ("weapon", "armor"):
                bonus = i.get("attack_bonus") or i.get("defense_bonus") or 0
                dur = i.get("durability")
                mx = i.get("max_durability")
                eq_flag = " ★" if i.get("equipped") else ""
                extra = f"+{bonus} | dur {dur}/{mx}{eq_flag}"
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
            stats_turn=f.get("turn"),
            stats_max_floor=self.max_floor,
            stats_kills=kills_total,
            stats_buys=buys_total,
            stats_identifies=len(self.identifies),
            weapon_name=html.escape(wpn.get("name") or "—"),
            weapon_atk=wpn.get("attack_bonus") or 0,
            weapon_dur=wpn.get("durability") or 0,
            weapon_mxd=wpn.get("max_durability") or 0,
            weapon_buc=html.escape(wpn.get("buc_status") or ""),
            weapon_sprite=wpn_sprite,
            armor_name=html.escape(arm.get("name") or "—"),
            armor_def=arm.get("defense_bonus") or 0,
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
            buy_lines=buy_lines or "<tr><td colspan='5'>no purchases</td></tr>",
            descent_lines=descent_lines or "<li>never descended past Floor 1</li>",
            inventory_rows=inv_rows or "<tr><td colspan='6'>—</td></tr>",
            movement_rows=movement_rows or "<tr><td colspan='6'>no movement logged</td></tr>",
            overall_waste=f"{overall_waste:.0f}",
            tomb_sighting_lines=tomb_sighting_lines,
            tomb_floor_count=len(self.tomb_suspected_floors),
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
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
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
  <div class="grid3">
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
            <p class="muted" style="margin:0;">+$weapon_atk atk · dur $weapon_dur/$weapon_mxd · $weapon_buc</p>
          </div>
        </div>
        <div class="gear-card">
          $armor_sprite
          <div class="gear-meta">
            <h3 style="margin:0;">Armor</h3>
            <p style="margin:4px 0;">$armor_name</p>
            <p class="muted" style="margin:0;">+$armor_def def · dur $armor_dur/$armor_mxd · $armor_buc</p>
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
            <p class="muted" style="margin:0;">+$weapon_atk atk · dur $weapon_dur/$weapon_mxd · $weapon_buc</p>
          </div>
        </div>
        <div class="gear-card">
          $armor_sprite
          <div class="gear-meta">
            <h3 style="margin:0;">Armor</h3>
            <p style="margin:4px 0;">$armor_name</p>
            <p class="muted" style="margin:0;">+$armor_def def · dur $armor_dur/$armor_mxd · $armor_buc</p>
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
      $death_block
    </div>

    <!-- Journey -->
    <div class="tab-panel" id="panel-journey">
      <h2>Descents</h2>
      <ul>$descent_lines</ul>
      <h2 style="margin-top:18px;">Movement Efficiency · overall waste $overall_waste%</h2>
      <p class="muted">First-visit moves discover new ground; revisits
        are moves that step onto a tile the agent has already stood on
        this floor. High waste% = patrol-bouncing.</p>
      <table>
        <tr><th>Floor</th><th>Moves</th><th>Unique tiles</th><th>First-visit</th><th>Revisit</th><th>Waste %</th></tr>
        $movement_rows
      </table>
      <h2 style="margin-top:18px;">Purchases ($stats_buys)</h2>
      <table><tr><th>Turn</th><th>Floor</th><th>Item</th><th>Count</th><th>Price</th></tr>
      $buy_lines
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
<title>Wizard's Cavern — Playtest Reports</title>
<style>""" + _CSS + """
.runs th, .runs td { font-size: 13px; padding: 6px 8px; }
.runs tr:hover { background: #1a1a1a; }
.tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; }
.tag.alive { background: #134e2b; color: #bbf7d0; }
.tag.dead { background: #5a1313; color: #fecaca; }
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
      <th>Gold</th><th>Kills</th><th>Waste %</th><th>Cause</th>
    </tr>
    $rows
  </table>
</section>
</body>
</html>
"""


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
        alive_tag = "alive" if d.get("alive") else "dead"
        outcome_label = "alive" if d.get("alive") else "dead"
        rows.append(
            f"<tr>"
            f"<td><a href='{d['slug']}.html'>{html.escape(d.get('name','?'))}</a></td>"
            f"<td>{html.escape(d.get('race','?'))}</td>"
            f"<td>{d.get('seed','?')}</td>"
            f"<td><span class='tag {alive_tag}'>{outcome_label}</span></td>"
            f"<td>{d.get('turn','?')}</td>"
            f"<td>F{d.get('max_floor','?')}</td>"
            f"<td>L{d.get('level','?')}</td>"
            f"<td>{d.get('hp','?')}/{d.get('max_hp','?')}</td>"
            f"<td>{d.get('gold','?')}g</td>"
            f"<td>{d.get('kills','?')}</td>"
            f"<td>{d.get('wasted_pct','?')}%</td>"
            f"<td>{html.escape(str(d.get('death_cause','—')))}</td>"
            f"</tr>"
        )
    body = Template(_INDEX_TEMPLATE).safe_substitute(
        count=len(summaries),
        generated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rows="\n".join(rows) or "<tr><td colspan='12'>no runs yet</td></tr>",
    )
    (out_dir / "index.html").write_text(body, encoding="utf-8")


def deploy_gh_pages(out_dir, repo_root, branch="main", remote="origin",
                    sub_path="docs/playtest"):
    """Push `out_dir` contents to `<branch>:<sub_path>/`.

    Default target is `main:docs/playtest/` because dachhack/LegendOfZot
    serves GitHub Pages from `main:docs/` (per repo settings), and we
    don't want to clobber the existing spell-sprite-audit site. The
    reports land at `https://dachhack.github.io/LegendOfZot/playtest/`
    as a sibling of the existing audit pages.

    Uses git plumbing (hash-object / ls-tree / mktree / commit-tree)
    so the deploy never modifies the working tree or index, never
    creates a worktree (sandboxed environments often refuse signing
    on auxiliary paths), and stays additive: existing files at
    `<sub_path>/` are preserved unless a same-named report has been
    regenerated. Files outside `<sub_path>/` (the rest of the
    repository) are passed through unchanged.

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

    # 4. Target directory: start from what's already at <sub_path>/
    #    (preserves prior runs deployed to the same path), then
    #    overlay every file in `out_dir` as a fresh blob.
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
        alive_tag = "alive" if d.get("alive") else "dead"
        outcome_label = "alive" if d.get("alive") else "dead"
        rows.append(
            f"<tr>"
            f"<td><a href='{d['slug']}.html'>{html.escape(d.get('name','?'))}</a></td>"
            f"<td>{html.escape(d.get('race','?'))}</td>"
            f"<td>{d.get('seed','?')}</td>"
            f"<td><span class='tag {alive_tag}'>{outcome_label}</span></td>"
            f"<td>{d.get('turn','?')}</td>"
            f"<td>F{d.get('max_floor','?')}</td>"
            f"<td>L{d.get('level','?')}</td>"
            f"<td>{d.get('hp','?')}/{d.get('max_hp','?')}</td>"
            f"<td>{d.get('gold','?')}g</td>"
            f"<td>{d.get('kills','?')}</td>"
            f"<td>{d.get('wasted_pct','?')}%</td>"
            f"<td>{html.escape(str(d.get('death_cause','—')))}</td>"
            f"</tr>"
        )
    index_html = Template(_INDEX_TEMPLATE).safe_substitute(
        count=len(summaries),
        generated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rows="\n".join(rows) or "<tr><td colspan='12'>no runs yet</td></tr>",
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
