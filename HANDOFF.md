# Handoff — Balance & Harness Honesty Arc (builds 314 → 328)

**Branch:** `claude/balance-upgrades-stats-mq7E2`
**Last commit:** `0c9f320` (build 328)
**State:** Clean. Pushed. No uncommitted work.

Continuation of the playtest-harness work from prior branch
`claude/wizards-cavern-playtest-4stBF` (builds 280–314).

---

## TL;DR

Built a fast, honest playtest harness and used it to fix the dominant
failure mode (loop-induced starvation on F1–F3). Net result vs build 324
on the same 120-seed grid:

| metric                     | B324  | B328 |
|----------------------------|-------|------|
| legit_alive (honest)       | 0     | **7** |
| starvation deaths          | 71    | 24   |
| harness wall-clock (s)     | 444   | 37   |
| nominal alive @ T5000      | ~1    | 48   |
| max floor reached          | F5    | F10  |
| natural deaths at F4+      | 32    | 38   |

The harness is now ~12× faster and the survival metric is no longer
inflated by tile-cycling. Deployed showcase: `00023_elf` (Elite Undead
Dragon Lich death on F7 at T1290).

---

## What "legit_alive" means

Defined in `wizardscavern/playtest_report.py:744`. A run is legit_alive iff:

```
alive AND wasted_pct < 50 AND moves_total > 30 AND max_floor >= 3
```

It exists because raw "alive @ T5000" was contaminated — runs were
"alive" by virtue of having never made meaningful progress (95% wasted,
1 HP, looping on F2). Whenever survival numbers come up, ask whether
they're nominal or legit. B324: 1/120 nominal, 0/120 legit. B328:
48/120 nominal, 7/120 legit.

---

## Build-by-build (this arc)

| build | what                                                                                  |
|-------|---------------------------------------------------------------------------------------|
| 314   | Tomb-gating fix (prior branch tail)                                                    |
| 315   | Upgrade scroll + permanent elixir reachability (level gates 15/25/35 → 8/16/25)       |
| 316   | F1–F6 survival pass                                                                    |
| 317   | Reverted food-drop curve change                                                        |
| 318–320 | Smart-policy descent push, fog-aware descent, warp tier                              |
| 321   | Sealed-pocket gen fix, blacksmith afford-loop                                          |
| 322–323 | U-camp escape, then reverted                                                         |
| 324   | M-cage flatline fixes (cage detection, retreat threshold, U-plain-neighbor)            |
| **325** | Vendor restock arity TypeError (real game-side crash, surfaced by harness)           |
| **326** | `legit_alive` metric — exposed contamination, established honest baseline            |
| **327** | Stair-tile starvation valve + oscillation abort v1                                   |
| **328** | Oscillation abort v2 — unique-floor gate (lets multi-floor descenders run)           |

---

## How the harness works (the workflow that paid off)

The `playtester` subagent is the unit of work. Typical loop:

1. Run the 120-grid (40 seeds × 3 races, 5000T, smart policy). ~37s.
2. Identify the worst-class deaths (highest wasted%, dominant cause).
3. Read the `.html` autopsies in `playtest_reports/` for the worst 3–5.
4. Look for the shared pathology in the per-step JSONL.
5. Patch `playtest_harness.py` (policy) or game code (mechanics).
6. Smoke on the autopsy seeds. Re-grid. Compare metrics honestly.

**Seed list (the standard grid):**
```
[1, 7, 13, 42, 100, 137, 200, 256, 314, 421, 512, 666, 777, 999,
 1100, 1337, 1500, 2025, 5000, 9999, 3, 11, 23, 47, 89, 113, 167,
 211, 271, 317, 367, 419, 461, 521, 587, 643, 719, 787, 857, 941]
```
40 seeds × {human, elf, dwarf} = 120 runs.

**Wall-clock to beat:** 37s for the full grid. If a future change
balloons this, something regressed in the abort heuristics.

---

## Open questions / candidate next bottlenecks

If picking this arc back up, the most likely root causes for the
remaining 113 non-legit_alive runs:

1. **Slow descent on non-loop runs.** Most of the 38 natural deaths at
   F4+ took 800–1500T to reach their kill floor. Wayfinder targeting may
   be picking the wrong D candidate, or the smart policy's combat-vs-
   descend gate is too cautious. Worth autopsying 5 deepest-natural-
   death runs to see where the turn budget goes.

2. **M-cage variant at F3 (00461_dwarf class).** B327/B328 both still
   starve this seed. The starvation valve at the stair handlers doesn't
   fire because there's no reachable U/D — the player is genuinely
   walled off. Different fix needed (item-based escape? wayfinder
   warp-priority bump even without warp tile visible?).

3. **The 7 legit_alive runs are all aborted mid-bounce with maxF=3–6.**
   They pass the legit_reason gate (`wasted<50`) only because they were
   stopped early. If you tighten legit to `wasted_pct < 35` or
   `max_floor >= 5`, the count drops to 2–3. Worth deciding what number
   we actually want to maximize — the threshold is one autopsy old.

---

## Key files

- `wizardscavern/playtest_harness.py` — the smart policy.
  - Stair handlers: ~line 3864 (down) / ~4015 (up). Starvation escape
    valve at top of each.
  - Oscillation abort: ~line 1990 (v2 unique-floor gate).
- `wizardscavern/playtest_report.py:744` — `legit_alive` definition.
- `wizardscavern/version.py` — `BUILD_NUMBER` + `CHANGELOG` (keep at 8
  entries, drop oldest). Splash screen reads this on launch.
- `wizardscavern/app.py` / `game_systems.py` / `combat.py` — main game.
- `wizardscavern/items.py:2391, 2403` — vendor restock signature (B325).
- `playtest_reports/` — current grid (B328).
- `playtest_reports_b327_archive/` — prior grid for comparison.

---

## Persona note

Project `CLAUDE.md` defines the agent persona — **Claudia**, German
TTRPG-obsessed coed, aggressively flirty, sausage scholar, one German
phrase per response on average, no emojis. A new session picks this up
from CLAUDE.md automatically. Stay precise; the bit shouldn't override
clarity in code reviews or bug fixes.

---

*Bis bald.* The next bottleneck is slow-descent, not loop-death.
