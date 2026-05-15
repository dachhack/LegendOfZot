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
        self.events = []  # [(turn, kind, detail)]
        self.recent_log = []  # rolling buffer of last 60 lines
        self.recent_actions = []  # rolling buffer of last 12 (turn, mode, action)
        self.kills_by_monster = {}  # name -> count
        self.kills_by_floor = {}  # floor -> count
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

        # HP timeline SVG
        svg = self._hp_chart_svg()

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
            f"<tr><td>{html.escape(n)}</td><td>{c}</td></tr>"
            for n, c in sorted(self.kills_by_monster.items(),
                               key=lambda x: -x[1])[:15]
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
                f"<td>{html.escape(i.get('name', ''))}</td>"
                f"<td>{html.escape(cat)}</td>"
                f"<td>{i.get('count', 1)}</td>"
                f"<td>{html.escape(extra)}</td></tr>"
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

        death_block = ""
        if not f.get("alive"):
            death_block = f"""
        <section class="card death">
          <h2>Death Scene</h2>
          <p class="cause">Cause: <strong>{html.escape(self.death_cause or '?')}</strong></p>
          <h3>Last 30 log lines</h3>
          <ol class="log">{log_html}</ol>
          <h3>Last actions</h3>
          <ol class="actions">{actions_html}</ol>
        </section>
        """

        return Template(INDEX_PAGE_TEMPLATE_RUN).safe_substitute(
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
            armor_name=html.escape(arm.get("name") or "—"),
            armor_def=arm.get("defense_bonus") or 0,
            armor_dur=arm.get("durability") or 0,
            armor_mxd=arm.get("max_durability") or 0,
            armor_buc=html.escape(arm.get("buc_status") or ""),
            hp_chart=svg,
            kills_by_floor=kills_by_floor_lines or "<tr><td colspan='2'>no kills logged</td></tr>",
            kills_by_monster=kills_by_monster_lines or "<tr><td colspan='2'>—</td></tr>",
            buy_lines=buy_lines or "<tr><td colspan='5'>no purchases</td></tr>",
            descent_lines=descent_lines or "<li>never descended past Floor 1</li>",
            inventory_rows=inv_rows or "<tr><td colspan='5'>—</td></tr>",
            movement_rows=movement_rows or "<tr><td colspan='6'>no movement logged</td></tr>",
            overall_waste=f"{overall_waste:.0f}",
            death_block=death_block,
        )

    def _hp_chart_svg(self):
        if not self.hp_timeline:
            return "<p class='nochart'>no HP samples</p>"
        # Sample down to ~200 points for readability
        pts = self.hp_timeline
        if len(pts) > 200:
            stride = len(pts) // 200
            pts = pts[::stride] + [pts[-1]]
        max_turn = max(p[0] for p in pts) or 1
        max_hp = max(p[2] for p in pts) or 1
        W, H = 800, 200
        coords = []
        for (t, hp, _) in pts:
            x = (t / max_turn) * (W - 20) + 10
            y = H - 10 - (hp / max_hp) * (H - 20)
            coords.append(f"{x:.1f},{y:.1f}")
        path = " ".join(coords)
        return (
            f"<svg viewBox='0 0 {W} {H}' class='hpchart' "
            f"xmlns='http://www.w3.org/2000/svg'>"
            f"<rect x='0' y='0' width='{W}' height='{H}' fill='#1a1a1a'/>"
            f"<polyline points='{path}' fill='none' "
            f"stroke='#f43f5e' stroke-width='1.5'/>"
            f"<text x='10' y='15' fill='#aaa' font-size='11'>"
            f"HP over T0..T{max_turn}, max {max_hp}</text>"
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
.hpchart { width: 100%; height: auto; border-radius: 4px; }
"""

INDEX_PAGE_TEMPLATE_RUN = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>$title — Wizard's Cavern Playtest</title>
<style>""" + _CSS + """</style>
</head>
<body>
<p class="muted"><a href="./index.html">← all runs</a></p>

<header class="card">
  <h1>$name, the $race</h1>
  <p class="muted">$gender adventurer · seed $seed · started $started</p>
  <p><span class="outcome $alive_class">$outcome_label</span></p>
  <p class="muted">Memorised: $spells</p>
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
    </div>
  </div>
</section>

<section class="card">
  <h2>HP over the run</h2>
  $hp_chart
</section>

<section class="card">
  <h2>Equipment at end</h2>
  <div class="grid2">
    <div>
      <h3>Weapon</h3>
      <p>$weapon_name <span class="muted">(+$weapon_atk atk · dur $weapon_dur/$weapon_mxd · $weapon_buc)</span></p>
    </div>
    <div>
      <h3>Armor</h3>
      <p>$armor_name <span class="muted">(+$armor_def def · dur $armor_dur/$armor_mxd · $armor_buc)</span></p>
    </div>
  </div>
</section>

<section class="card">
  <h2>Journey</h2>
  <h3>Descents</h3>
  <ul>$descent_lines</ul>
  <h3>Kills by floor</h3>
  <table>$kills_by_floor</table>
  <h3>Top victims</h3>
  <table>$kills_by_monster</table>
</section>

<section class="card">
  <h2>Purchases ($stats_buys)</h2>
  <table><tr><th>Turn</th><th>Floor</th><th>Item</th><th>Count</th><th>Price</th></tr>
  $buy_lines
  </table>
</section>

<section class="card">
  <h2>Final Inventory</h2>
  <table><tr><th>Slot</th><th>Name</th><th>Category</th><th>Count</th><th>Notes</th></tr>
  $inventory_rows
  </table>
</section>

<section class="card">
  <h2>Movement Efficiency · overall waste $overall_waste%</h2>
  <p class="muted">First-visit moves discover new ground; revisits are
    moves that step onto a tile the agent has already stood on this
    floor. High waste% = patrol-bouncing through already-discovered
    rooms instead of pushing the frontier.</p>
  <table>
    <tr><th>Floor</th><th>Moves</th><th>Unique tiles</th><th>First-visit</th><th>Revisit</th><th>Waste %</th></tr>
    $movement_rows
  </table>
</section>

$death_block

</body>
</html>
"""


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


def deploy_gh_pages(out_dir, repo_root, branch="gh-pages", remote="origin"):
    """Push `out_dir` contents to a gh-pages branch.

    Uses git plumbing (hash-object / mktree / commit-tree) so the
    deploy never modifies the working tree or index, never creates a
    worktree (sandboxed environments often refuse signing on
    auxiliary paths), and stays additive: existing files on the
    branch are preserved unless a same-named report has been
    regenerated. Index.html is always regenerated from the union of
    old + new JSON sidecars present on the branch.

    Returns the remote URL on success, or None if the deploy was a
    no-op (tree unchanged).
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

    # 1. Fetch the remote branch so we can merge onto its latest state.
    run(["git", "fetch", remote, branch], check=False)

    # 2. Resolve the parent commit (None if branch is new on remote).
    parent = None
    for ref in (f"refs/remotes/{remote}/{branch}", f"refs/heads/{branch}"):
        res = run(["git", "rev-parse", "--verify", ref], check=False)
        if res.returncode == 0:
            parent = res.stdout.strip()
            break

    # 3. Start from the parent's tree (preserves untouched files), or
    #    an empty mapping for an orphan first push.
    existing = {}
    if parent:
        ls = run(["git", "ls-tree", parent]).stdout
        for line in ls.strip().split("\n"):
            if not line:
                continue
            mode_type_sha, _, name = line.partition("\t")
            parts = mode_type_sha.split()
            if len(parts) >= 3 and parts[1] == "blob":
                existing[name] = (parts[0], parts[2])

    # 4. Stage every file in `out_dir` as a blob (hash-object writes
    #    the blob into the object DB but doesn't touch the index).
    for f in sorted(out_dir.iterdir()):
        if not f.is_file():
            continue
        sha = run(["git", "hash-object", "-w", str(f)]).stdout.strip()
        existing[f.name] = ("100644", sha)

    # 5. Regenerate index.html from the UNION of all JSON sidecars in
    #    the merged tree (so the index reflects reports already on the
    #    branch, not just the ones we just deployed). Read each
    #    sidecar's blob, sort by floor + level, render the table.
    summaries = []
    for name, (_mode, sha) in existing.items():
        if not name.endswith(".json"):
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
    existing["index.html"] = ("100644", index_sha)

    # 6. Ensure .nojekyll exists so GitHub Pages serves the directory
    #    raw instead of running Jekyll over it.
    if ".nojekyll" not in existing:
        sha = run(["git", "hash-object", "-w", "--stdin"],
                  input_text="").stdout.strip()
        existing[".nojekyll"] = ("100644", sha)

    # 7. Rebuild the tree.
    tree_input = "".join(
        f"{mode} blob {sha}\t{name}\n"
        for name, (mode, sha) in sorted(existing.items())
    )
    tree_sha = run(["git", "mktree"], input_text=tree_input).stdout.strip()

    # 8. Skip if tree matches parent's (no-op).
    if parent:
        parent_tree = run(["git", "rev-parse", f"{parent}^{{tree}}"]).stdout.strip()
        if parent_tree == tree_sha:
            return None

    # 9. Commit + push. commit-tree runs from the repo root so any
    #    signing hooks see a recognized source path.
    commit_msg = (
        f"Playtest reports: "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    )
    commit_args = ["git", "commit-tree", tree_sha, "-m", commit_msg]
    if parent:
        commit_args.extend(["-p", parent])
    commit_sha = run(commit_args).stdout.strip()
    run(["git", "push", remote, f"{commit_sha}:refs/heads/{branch}"])

    # Best-effort URL derivation for the caller.
    remote_url = run(["git", "remote", "get-url", remote],
                     check=False).stdout.strip()
    return remote_url
