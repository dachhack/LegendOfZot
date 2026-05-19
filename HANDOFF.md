# Playtest Harness — Handoff (build 356)

Branch: `claude/resume-playtesting-e6mpI`. Builds 347-356 in this
session focused on **loop elimination, vendor connectivity, tomb-raid
tuning, and the build-355/356 elf rework**. Site:
https://dachhack.github.io/LegendOfZot/playtest/.

## TL;DR — build 356 highlights

The big-ticket change this stretch was the **elf overhaul** (builds
355-356). The b354 grid surfaced an elf-cohort collapse — 30/45 elves
never reached F2 because they started at INT 12 / 0 mana and could not
cast their memorised spells. Three coordinated fixes shipped:

1. **Elf mana threshold lowered INT 15 → INT 11**, softer slope
   (`(int-11)*3+5`). Fresh elf INT 12 → 8 MP (was 0); INT 16 → 20 MP;
   INT 25 → 47 MP. `wizardscavern/characters.py:899-908`.
2. **Four racial cantrips** added — `Detect Monster` (3x3 monster
   reveal), `Light` (5x5 fog-of-war reveal), `Hold Monster` (1-turn
   time_stop on target), `Mind Touch` (1 MP Psionic damage). All
   slot-free, `is_cantrip=True` on the Spell class. Definitions live in
   BOTH `wizardscavern/items.py:3619-3622` and
   `wizardscavern/item_templates.py:425-428` — the codebase has two
   parallel SPELL_TEMPLATES tables (harness uses items.py, in-game uses
   item_templates.py — pre-existing duplication, do not consolidate
   without a separate audit).
3. **New `player_cantrips` character-creation screen** between portrait
   pick and starting shop. Elves only — toggles via `ct1..ct4`,
   confirms with `x` once exactly 2 are selected. Other races skip
   straight to starting_shop unchanged.

Cast-pipeline plumbing:
- `can_cast_spells()` now allows casters with at least one cantrip
  even at 0 spell slots (fresh elves have `max_slots = 0` since
  `(12-15)//2 = 0`).
- `get_spell_slots(spell)` returns 0 for cantrips so they don't
  compete with regular L0 spells for the INT-gated slot pool.
- New spell_type handlers `detect_monster` and `reveal_fog` in
  `characters.cast_spell` AND `combat._execute_charged_spell`.
- `spell_casting_mode` now routes back to `game_loop` (not
  `combat_mode`) after a successful cast when `gs.active_monster` is
  None, so Detect/Light work as exploration utilities.
- Harness `can_cast` obs moved from `intelligence > 15` to
  `max_mana > 0` (was filtering fresh-elf cantrips out of the spell
  policy). Harness default cantrip pair for elves = `Hold Monster +
  Mind Touch` (auto-granted in `new_game` when `race='elf'`,
  combat-relevant pair so grid runs have an offensive option).

## Build 356 validation grid — PASS

20 seeds × 3 races, turns=3000, policy=smart. Site updated 2026-05-19
via `deploy_gh_pages(..., replace=True)`. Commit `d29a78b` on
`origin/main`.

| Cohort | Mean max-floor | F2+ % | F5+ % | Alive % | Mean level |
|---|---|---|---|---|---|
| Elf (n=20) | **4.55** | **95%** | 45% | 15% | 3.80 |
| Elf (b354) | 2.16 | 33% | — | — | — |
| Human (n=20) | 4.75 | 95% | 60% | 15% | 4.75 |
| Dwarf (n=20) | 5.75 | 100% | 65% | 20% | 6.35 |

**Elf cohort up +110% on mean max-floor**, +62pp on F2+. Zero crashes,
zero softlocks. Human/dwarf cohorts steady — the changes are
race-gated correctly. Max elf floor reached: F9 (seeds 3 and 9).

## Known issue carried into build 357+

**Elf mean character level (3.80) trails depth.** Comparable depth to
human cohort (F4.55 vs F4.75) but +1 level behind on average. Working
hypothesis: Hold Monster and Mind Touch let elves *skip* fights they
would have *won* on melee, so they descend on the XP curve of fights
not fought. Elf seed 9 hit F9 at lv7 and died to a Demilich —
classic "deep but fragile" pattern. Options for next build:

- Give cantrip-kill events XP credit equivalent to a melee kill
  (Mind Touch currently is sub-melee damage but kills are still kills).
- Tag Hold Monster as a panic button, not a default opener — escalating
  mana cost on consecutive uses, or per-floor uses cap.
- Just track for another build before tuning. n=20 is one data point.

## Earlier session work (builds 347-354)

Loop hunt rounds 12-14, vendor connectivity, tomb-raid gates. See
`wizardscavern/version.py:CHANGELOG` for full per-build detail. Key
landmarks:

| Build | Change | Driver |
|---|---|---|
| 347 | Warp-dir step-off passes through T (tomb) tiles | s=1234 dwarf F3 477T n/s/n loop |
| 348 | trapped_no_d fast-path when W reachable + reach_pct ≥ 95 | s=500 human F1 280-loop |
| 349 | On-D-tile anti-bounce after 3+ visits | s=271 dwarf F2 D bounce |
| 350 | Tomb-raid strength gate (level + dmg + HP all-or-nothing) | UNDEAD = 73% of combat deaths |
| 351 | Strength-gate loosened (floor+2, 3 hits) | Walk-out saved heroes were starving |
| 352 | Vendor upgrade priority promoted | F1-F4 attrition at base Dagger |
| 353 | Gear-upgrade vendor pull on F1-F2 | weapon/armor triggers + 25g floor |
| 354 | V added to floor-connectivity guarantee | "V should always be reachable" |

Cumulative loop_turns reduction across rounds 8-14: 40512 → 5410 (-87%).

## Running the harness

```bash
# Smoke run
python3 -m wizardscavern.playtest_harness --seed 42 --turns 200 \
    --policy smart --race elf

# With report output (HTML + JSON)
python3 -m wizardscavern.playtest_harness --seed 42 --turns 1500 \
    --policy smart --race elf --report-dir /tmp/myrun

# Grid (write the driver yourself; the canonical /tmp/deep_deploy.py
# doesn't survive container restarts). 20 seeds × 3 races at
# turns=3000 is the standard validation shape. Don't pass --deploy
# per-run -- do one final invocation with --deploy --replace, or call
# wizardscavern.playtest_report.deploy_gh_pages() directly.
```

The `playtester` subagent will set up grids, drill into specific
runs, and post-analyse — spawn with a focused task. Last session
artifacts in `/tmp/grid_b356/`, `/tmp/run_grid_b356.sh`,
`/tmp/analyze_grid_b356.py`.

# Playtest Harness — Handoff (build 314)

Branch: `claude/wizards-cavern-playtest-4stBF`. Continuation of the
playtest-harness work started on the previous branch
(`claude/game-playtest-agent-npMRR`). Builds 280-314 in this session
focused on **flatline elimination, balance tuning, and exploration
analytics**. Site: https://dachhack.github.io/LegendOfZot/playtest/.

## TL;DR — what's different from the last handoff

| | Before this session | After build 314 |
|---|---|---|
| Alive flatlines (HP=1 indefinite loops) | 3-6 per grid | **0/60** |
| Max floor record | F8 | **F11** (briefly, build 303) |
| Max level record | L6 | **L9** (Tauriel s=13 elf) |
| Honest survivors at 3000T | 0/60 | 3/60 (build 306) → 0/60 (current) |
| Warp avoidance | leaky | **0 voluntary warps** across grids |
| Per-run report features | basic | + warp_pct + xp_pct + Exploration table |

The honest-survivor count dipped back to 0 after the food economy
buffs because agents now push deeper and die deeper, instead of
parking healthy on F4-F5. The wedges are gone; what remains is
honest depth difficulty.

## Running the harness

```bash
# Smoke run
python3 -m wizardscavern.playtest_harness --seed 42 --turns 200 \
    --policy smart --race dwarf

# With report output (HTML + JSON)
python3 -m wizardscavern.playtest_harness --seed 42 --turns 1500 \
    --policy smart --race human --report-dir /tmp/myrun

# Deploy grid (drives 20 seeds x 3 races, pushes reports to
# main:docs/playtest/). Cap TURNS_BUDGET at 3000 for ~1min runs.
python3 /tmp/deep_deploy.py
```

A one-line summary per run is appended to `playtest_runs.log` at repo
root (gitignored). The harness is also driven by the `playtester`
subagent — spawn with a focused task and it'll set up grids, drill
into specific runs, and post-analyse.

## Site URLs

- **Index of runs**: https://dachhack.github.io/LegendOfZot/playtest/
- Per-run pages: same root + `<slug>.html`
- Deploy mechanic: `deploy_gh_pages()` in `playtest_report.py` pushes
  to `main:docs/playtest/` via git plumbing (additive by default,
  `replace=True` purges old reports first).

## Smart-policy priority chain (game_loop)

Each step re-derives intent from obs. Order of priorities, highest
first:

1. **Heal** at HP < 30% (open inventory)
2. **Cure status** if bad status + cure item available
3. **Pre-emptive heal** at HP < 80% with adjacent M
4. **Pre-combat buff drink** when buff potion + M adjacent + HP 60-95%
5. **Eat urgent meat** (rot_timer <= 20)
6. **Swap broken gear** if spare exists + not cursed
7. **Equip strongest non-cursed upgrade**
8. **Eat at hunger < 50** (ration efficiency optimised)
9. **Cook raw meat** if Cooking Kit + raw meat (any hunger)
10. **Light lantern** on ANY fog-adjacent step (fuel > 0)
11. **Wedge Hail Mary** if `current_tile_visits >= 6` + untried items
12. **Wayfinder** (BFS-based, tier-prioritised — see below)

## Wayfinder tier logic

```
if trapped_no_d AND has warp_path:   tiers = [(W,), (V,)]      # escape via known W
elif trapped_no_d AND no_warp_path AND monster visible:
                                     tiers = [(M,)]            # die fighting
elif retreat_to_floor is set:        tiers = [(U,), (V,)]      # warp recovery
elif too_long_on_floor:              tiers = [(D,), (V,)]      # press on
elif high_coverage_descend:          tiers = [(D,), SAFE, ...] # sweep done
elif is_weak:                        tiers = [(V,), SAFE, ...] # heal-first
elif wants_vendor:                   tiers = [(V,), SAFE, ...]
elif ready_to_clear:                 tiers = [SAFE, V, M, ...] # grind
else:                                tiers = [SAFE, V, M, T, N] # normal
```

`BENEFICIAL_SAFE = (C, G, L, O, A, P, Q, K, B, F)` — rooms that pay
off without forced combat.

`trapped_no_d`: D unreachable AND no new tile visited in 100+ turns.
Behavioural signal — replaces older turn-count / pct-of-floor gates.

## Key invariants the playtester enforces

- **AVOID-W is always on** (was z<10 gated). Only `trapped_no_d`
  releases it. Build 296.
- **Inferred guardian avoidance**: seeing a T tile flags the 4
  cardinal-adjacent positions as guardian-suspect (`pc.level >=
  pc.floor + 3` to engage). Build 303.
- **Wedge detector**: `current_tile_visits >= 6` triggers Hail Mary
  item-use (scrolls / unidentified potions). Build 294-295.
- **Die-fighting override**: trapped agent with no escape items
  walks toward the only visible M and commits. Build 304.
- **Tomb inference is genuinely informational**: every tomb has 4
  cardinal guardians per `dungeon.py:setup_dungeons_and_tombs`. The
  policy uses this domain knowledge to avoid corners even when M
  tiles are still in fog. Build 303.

## Balance changes shipped this session

| Build | Change | Source |
|---|---|---|
| 292 | Lantern fuel buff: starter 50→80, canisters 1-3@10 → 2-4@20 | F12 reach unlocked |
| 296 | Warp avoidance: lantern on any fog step, AVOID-W always on, no late-game accept | User: "players would avoid warps more" |
| 297 | Coverage-based trapped gates | User: "% of floor not turns" |
| 298 | Behavioural trapped (turns_since_new_tile >= 100) + W-target wayfinder | Region-split floor escapes |
| 305 | Tiered HP regen by hunger: 85+ = 1/2 moves, 60-84 = 1/4, <60 none | Smooths chip damage |
| 306 | `max(1, hp-dmg)` → `max(0, …)`: starvation can kill | Ends the HP=1 wedge |
| 306 | Rations 40→50 nutrition, starter 5→8 | Food economy buff |
| 307 | Iron Rations F1+ vendor (was F3+) | Food economy buff |
| 308 | Cooking Kit F3+ vendor (game default), policy cooks all raw meat | User: "cook all meat once you have the kit" |
| 308 | Meat drop rate 35% → 55% | Food economy buff |
| 311 | Carnyx of Doom XP bonus removed | User: "kill the exp bonus for the carnyx" |

## Per-run report features (current state)

The HTML page now surfaces:

1. **Hero sprite** — race + gender + name → game's `_CHARACTERS_POOL`
   pid (matches what character creation would show). Build 301.
2. **Journey ledger** with floor exits colour-coded:
   stairs / warp_accept / warp_forced. Includes the new
   **Warp % share of floor changes** line.
3. **Movement Efficiency** table: per-floor moves, unique tiles,
   first-visit, revisit, waste %.
4. **Exploration** table: per-floor kills/M, XP earned/pool, chests,
   boons, vendor (V), tomb (T) counts with totals row. Build 309-314.
5. **Items table** with status: equipped / in bag / used / partial.
6. **Death scene block** with last 30 log lines + 12 actions.

The **index page** has a sortable table with Warp % and XP %
columns — sort ascending by xp_pct to find under-explorers, descending
to find grinders.

## Key analytical findings

### Warps are mostly forced, not accepted (build 296+)
- Mean grid warp_pct: ~25-30%, but **>95% are forced** (resist roll
  failed) not accepted.
- 0 voluntary warps across multiple grids since build 297.
- User framing ("players would avoid warps more") is now enforced.

### Elite undead deaths are ALL from corner-walks, never raids (build 301)
- 15/15 ELITE UNDEAD deaths traced to `setup_dungeons_and_tombs`
  cardinal-adjacent guardians.
- 0 from `process_tomb_action` SEARCH outcome.
- Build 303's tomb-inference avoidance reduced these 13/60 -> 3/60.

### Exploration does NOT help survival (builds 309-314)
- Mean xp_pct for starvation deaths: **97%**.
- Mean xp_pct for combat deaths: **~50%**.
- High-xp_pct correlates with starvation (over-foraging) not depth.
- Pearson(xp_pct, max_floor) ≈ 0.09 — effectively zero.
- **The smart policy is grinding floors clean and starving**.

## Open questions / future work

1. **Honest survival at 3000T**: how to get agents to live to the
   budget AND stay healthy AND keep progressing? Build 306 had 3/60
   honest survivors at F5-F7. Current state is 0/60 because the food
   buff lets agents push deeper, where they die to combat. Worth
   testing: bump max_health curve, slow hunger decay, more vendor
   heals at depth.
2. **The descend-sooner hypothesis** (build 314 verdict): the policy
   over-grinds F1-F3. A "lower ready_to_clear threshold" or
   "descend at 50% coverage instead of 80%" might let agents reach
   deeper without starving. Untested.
3. **XP-pool formula is approximate** by design — the cap at 100%
   hides dynamic spawn bonuses (tomb spirits, chest-gas monsters,
   same-coord respawns). Per-floor rows in the Exploration table
   show raw ratios. Real fix would need a kill-event hook to
   accumulate pool deltas as they spawn.
4. **Experience Boost potion is a placebo** — `items.py:4225` logs
   the bonus but never actually multiplies XP. Either finish the
   implementation or remove the status effect.
5. **Pre-T tomb-guardian ambushes** still happen (3/60 in build 303
   grid): the four corner M tiles are sometimes revealed before the
   T tile is. Inference could be extended: a discovered M with
   `undead_guardian=True` + `tomb_location` property implies the T
   and the other 3 corners. Untested.

## Useful commits to skim cold

- **752973b** — build 303: inferred tomb guardian avoidance (the
  big elite-undead survival jump)
- **2e49fd2** — build 304: die-fighting + canister-aware lantern
- **3ee3a2f** — build 296: warp avoidance pass (Gimli's lesson)
- **a006abd** — build 309: exploration efficiency metric
- **a0e802e** — build 308 followup: death-cause walker fixes
- **eacc021** — build 314: XP/kill ratio cap (final convergence)

## Where data lives

| Path | What |
|---|---|
| `wizardscavern/playtest_harness.py` | Headless game driver + smart_policy |
| `wizardscavern/playtest_report.py` | HTML/JSON report builder + deploy |
| `wizardscavern/version.py` | BUILD_NUMBER + CHANGELOG (~8 entries) |
| `playtest_reports/` | Local report artifacts (gitignored) |
| `docs/playtest/` | Deployed report site (on main) |
| `playtest_runs.log` | One-line per-run summary (gitignored) |
| `/tmp/deep_deploy.py` | Grid driver (lives in /tmp, not tracked) |

## Persona note

`CLAUDE.md` defines "Claudia" — flirty German tabletop-nerd — for the
main conversation. The playtester subagent is clinical: numbers,
file:line refs, bug write-ups. *Schatz, eine Wurst pro Iteration.*
