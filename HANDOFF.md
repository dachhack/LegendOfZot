# Handoff — Builds 373-382 (Food Economy + Race Identity)

**Session window:** 2026-05-20
**Branch:** `claude/playtest-food-economy-j6JnU` (NOT merged to main)
**Final HEAD:** `f84638e1`
**Live reports:** https://dachhack.github.io/LegendOfZot/playtest/

## What this session was about

The prior session (b369-b372) closed eight resource-bleed bugs and
handed off the question: *"is the food clock actually a clock?"*

Playtest-371 audit answered: **no.** Mean hunger sat at 67-77 across
all runs, 0/18 ever crossed the Hungry threshold, peak inventory
nutrition 2840 vs max-hunger 100. The sausage / lembas / Curing Kit
crafting subsystems existed in code but **never fired** — agents had
no Curing Kit because it was only stocked on a restock path the policy
never triggered, and the smart policy had no craft trigger.

This session built the food clock that actually bites, restored the
crafting subsystems, then discovered that the same fixes had a deeper
implication: **race identity was broken.** Humans and dwarves had
INT-gated cast access they could never reach, and the food cuts hit
the melee race hardest. Two more builds restored race identity (human
Mind Touch cantrip, Dwarven Carnivore Diet).

## The arc — 10 builds in 4 acts

### Act I: Food economy (b373-b374)
| build | change |
|---|---|
| b373 | Curing Kit stocks at every F10+ regular vendor until purchased (b372 fixed the never-stocking; b373 fixed the bug-merchant-skip pattern with a buy-flip flag) |
| b374 | Hunger decay 0.7/move → 1.0/move (reverted b327 sparse-food tuning — food clock finally bites) |

### Act II: Crafting + cuts (b375-b379)
| build | change |
|---|---|
| b375 | Smart policy crafts sausages (new `_pick_craftable_food` helper; `crafting_mode` step dispatch added) |
| b376 | Dwarven sausages (Landjäger, Blutwurst) added with race-locked recipes; lembas crafting policy wired for elves |
| b377 | Curing Kit gate F10 → F5 (the relief valve was placed AFTER the starvation cliff, not on it) |
| b378 | Vendor Rations stack 3-4 → 1-2 (cut cheap-bulk hoard) |
| b379 | Iron Rations 3 → 1; meat drop 70% → 55% (final rollback of b327's sparse-food cascade) |

### Act III: Stat-point system (b380)
| build | change |
|---|---|
| b380 | New stat-point allocation system: every 2 levels → +1 point, spendable on STR/DEX/INT via character-stats UI (`p` from stats screen → `stat_allocation_mode` → `a`/`d`/`i`). Smart-policy auto-spend: INT until past racial cast threshold + 4, then alternates STR/DEX. Routes `game_loop → i → s → p → allocation`, exits cleanly. Also: Elixir of Brilliance level gate 15 → 4. |

### Act IV: Race identity (b381-b382)
| build | change |
|---|---|
| b381 | Humans get Mind Touch cantrip at character creation (single cantrip vs elf's two — preserves magic gap, locked behind INT gate); Dwarven Appetite: dwarves draw +50% nutrition from ALL food |
| b382 | Human cast threshold INT > 15 → INT > 13 (humans cast at INT 14, reachable mid-game); Dwarven Carnivore Diet: reverted Food.use() bonus (Rations/Iron Rations base for all races), bumped Meat.use() and Sausage.use() dwarf bonus 1.5x → 2.0x ("lean into the dwarf carnivore diet") |

## Key data — b372 baseline vs b382 final

| Metric | b372 baseline | **b382 final** |
|---|---|---|
| Mean hunger (F1-F3) | 74.5 | 73.7 |
| Mean hunger (F4-F6) | 70.8 | ~67 |
| Hungry-threshold (≤30) crossings | 0/18 | several/18 |
| Starvation deaths | 0/18 | ~5/18 (real food clock) |
| Curing Kit pickup | 0/8 (audit) | 4-7/18 (F5 gate) |
| Sausages crafted | 0 | 7 across 4 runs (Bratwurst, Andouille, Landjäger) |
| Lembas crafted | 0 | 1 (elf survivor) |
| **Humans casting** | **0/6** | **3/6 (179 casts)** |
| Elves casting | varies | 6/6 (458 casts) |
| Dwarves casting | 0/6 | 0/6 (intentional) |
| Dwarf mean max floor | F7.2 | **F8.5** (deepest race) |
| Dwarf mean level | ~6 | **L10.7** (highest) |
| Peak inventory nutrition | 1560-3315 | substantially lower |

## Race identity scorecard (design intent vs reality)

User's spec: *"Elves balanced toward magic, Dwarves towards melee,
Humans balanced between both. I'm okay with dwarves never casting if
they are strong enough melee."*

| Race | Magic | Melee/Survival | Verdict |
|---|---|---|---|
| Elf | INT 11+ gate (start INT 12), 2 cantrips, 458 casts/6 runs | Squishy (HP 20), mean F5.5 | **✓ Magic dominant** |
| Human | INT 13+ gate (b382), Mind Touch cantrip, 179 casts/6 runs | Balanced (HP 30), mean F7.5 | **✓ Balanced** |
| Dwarf | INT 20+ gate, no cantrip, 0 casts | Tank (HP 60), Carnivore Diet 2x meat, deepest reach F8.5 | **✓ Melee — but 0/6 alive at cap** |

Dwarves' 0/6 survival is misleading: they're descending furthest and
dying to F9-F12 elites (Death Knights, Demiliches), not to early-game
problems. Their melee identity works.

## Open issues for next session

### High value
1. **Spellbook-reading policy gap.** Humans / dwarves can only ever
   cast their starter cantrip (humans: Mind Touch only; dwarves: none).
   The smart policy doesn't buy spellbooks at vendors or read found
   spellbooks. A `_pick_spellbook_to_memorize` helper + an
   `i → m` (memorize) flow would let mid-game humans expand beyond
   Mind Touch.
2. **Elixir of Brilliance auto-drink gap.** b380 dropped the level
   gate to 4, but no policy hook drinks them. The 1-3 elixirs that
   appear per run sit in inventory unused. A trivial trigger:
   "if elixir is identified and INT below cast threshold, drink."
3. **Sausage/Lembas crafting still rare in playtests** (4-7/18 runs).
   Garden access is the bottleneck — agents don't visit garden rooms
   often enough to accumulate herbs. Either bump garden spawn rate,
   or give garden visits priority in the wayfinder.
4. **Dwarf deep-floor mortality** (F9-F12 elite kills). The Carnivore
   Diet keeps them fed; what kills them at depth is monster scaling.
   Could investigate: monster HP curves vs dwarf gear progression,
   or whether STR-allocated points actually translate to attack.

### Medium value
5. **Stat drains erase allocated INT.** `human_101` in the b381 sweep
   went INT 10→8→7→10 from Stat Drain effects, undoing 3 stat-point
   allocations. Should allocated points be protected? Or treat as
   intended risk?
6. **F2-F5 starvation cluster** persists for runs that don't find
   vendors. Considered "bad luck variance" but worth measuring
   whether a guaranteed F2 vendor would close the cliff.

### Low-value / report bugs
7. **HTML report inventory truncation** at slot 24
   (`playtest_report.py:1573`: `for i in inv[:24]`). Late-game crafted
   sausages land at slot 60+ and disappear from the rendered table.
   Cosmetic but blocks naive grep-the-HTML analysis.
8. **Vendor purchase "gold spent" inflated** in HTML report
   (`playtest_report.py:1508`: `cur[1] + price * c`). The vendor
   charges `price` for the whole stack, not per-item. Report's gold
   figures are wrong by a factor of `count`. Item counts are correct.

## Important file paths & constants

### Game state
- `wizardscavern/characters.py:914` — `max_mana` property (per-race INT gates: elf 11, human 13, dwarf 20)
- `wizardscavern/characters.py:1331` — `gain_experience` (stat point grant: `(level - 1) // 2`)
- `wizardscavern/characters.py:898` — `unspent_stat_points` field on PlayerCharacter
- `wizardscavern/items.py:2837-2840` — `HUNGER_DECAY_PER_MOVE=10`, `HUNGER_DECAY_INTERVAL=10` (= 1.0/move)
- `wizardscavern/items.py:3219` — `random.random() > 0.55` meat drop gate (was 0.70)
- `wizardscavern/items.py:Meat.use` — Carnivore Diet 2.0x for dwarves
- `wizardscavern/items.py:Sausage.use` — 2.0x + 10 HP heal for dwarves
- `wizardscavern/items.py:Food.use` — NO race bonus (rations/jerky base for all)
- `wizardscavern/items.py:LembasWafer` — fill hunger + freeze 30 turns

### Vendor stock
- `wizardscavern/vendor.py:129` — starting shop: 5 Rations (kept)
- `wizardscavern/vendor.py:287` — dungeon vendor: 1-2 Rations stack
- `wizardscavern/vendor.py:300` — Iron Rations stack = 1 (was 3)
- `wizardscavern/vendor.py:308-322` — Cooking Kit F3+, Curing Kit F5+ (z >= 4) — gate flips in buy handler
- `wizardscavern/vendor.py:996` — Elixir of Brilliance level 4 (was 15)

### Recipes
- `wizardscavern/item_templates.py:245+` — `SAUSAGE_RECIPES` (Bratwurst, Chorizo, Andouille, Boerewors, Landjäger dwarf-only, Blutwurst dwarf-only, 3 spicy)
- `wizardscavern/item_templates.py:218+` — `LEMBAS_RECIPES` (elf-only)
- `wizardscavern/game_systems.py:1724+` — recipe filtering, including `recipe_data.get('race')` race-lock check

### Smart policy
- `wizardscavern/playtest_harness.py:_pick_craftable_food` — picks the best craftable recipe (race-locked > lembas > generic, all non-spicy)
- `wizardscavern/playtest_harness.py:530-560` — race cantrips at character creation (elf gets 2, human gets Mind Touch, dwarf gets none)
- `wizardscavern/playtest_harness.py` — `stat_allocation_mode` policy handler (auto-spends INT until past threshold + 4)
- `wizardscavern/playtest_harness.py` — inventory-mode cascade order: heal → urgent_meat → cook → craft → stat-allocate → broken-gear → upgrade → eat → scrolls

### UI flow (in-game)
- `wizardscavern/game_systems.py:process_stat_allocation_action` — handles `a`/`d`/`i` stat point spends
- `wizardscavern/app.py:character_stats_mode render` — shows "Unspent Points: N (press p to allocate)"
- `wizardscavern/app.py:stat_allocation_mode render` — allocation panel

## How to validate / pick up

```bash
# Smoke-test the build compiles
python3 -m py_compile wizardscavern/characters.py wizardscavern/items.py \
                       wizardscavern/playtest_harness.py wizardscavern/game_systems.py

# Quick single-run check (vanilla human, no cheats)
python3 -m wizardscavern.playtest_harness --seed 5 --race human \
        --turns 4000 --policy smart \
        --report-dir /tmp/test_report

# Full sweep + deploy (use the playtester agent)
# In agent task: 15-18 runs across 3 races, same seed set as prior sweeps:
# 1, 5, 7, 42, 101, 202, 303, 404, 505, 808, 909, 1010, 1234, 2024, 3030, 5555, 7777, 9999
# Then call deploy_gh_pages(reports_dir, repo_root, replace=True)
```

## Deploy notes

- `deploy_gh_pages` despite its name targets `main:docs/playtest/`, not
  `gh-pages` branch. The function uses a worktree to commit + push
  without affecting the working tree.
- API 529 Overloaded hit twice mid-session during deploy. The function
  is retry-safe — wrap in `for attempt in range(3): ... time.sleep(15)`.
- If a sweep crashes at deploy, the reports are already on disk in
  `playtest_reports/` — you can manually invoke
  `deploy_gh_pages('/home/user/LegendOfZot/playtest_reports', '/home/user/LegendOfZot', replace=True)`.

## Decisions to know

1. **Dwarves DO NOT cast by design.** They can mathematically reach
   the gate (one b382 dwarf hit INT 23, mana 49), but they have no
   starter cantrip and the policy doesn't memorize spellbooks. This
   is intentional, per user spec.
2. **Sausages crafted in the wild get the +50% from b381's Sausage
   bonus AND the +50% bump in b382, totaling +100% for dwarves**.
   Bratwurst (60 nut) → 120 nut + 10 HP heal for a dwarf.
3. **The 1 pt per 2 levels pacing was deliberately chosen over 1
   pt/level** to preserve race identity at endgame. A long L20 dwarf
   at 1pt/level all-in INT would reach INT 18 — closer to cast
   threshold than intended. The 1/2 pace keeps dwarves practically
   non-casters.
4. **The food cuts (b378-b379) are working** — the b327 sparse-food
   tuning is fully reverted. Don't loosen further without re-checking
   the b382 mean-hunger data.
5. **The b381 Food.use dwarf bonus was reverted in b382** because the
   user wanted dwarves to be carnivores, not bread-eaters. Rations
   are race-neutral now; meat is dwarf-specific.

## Closing context

Branch is **NOT merged to main** yet. The deployed reports on
gh-pages were generated from this branch via the `deploy_gh_pages`
worktree mechanism, which commits to main's `docs/playtest/` subpath
without merging the branch itself.

To ship: open a PR from `claude/playtest-food-economy-j6JnU` against
main. The Bombur-style canary check for this session would be
`human_5` (the 3800-turn human survivor who reached INT 20 and cast
Mind Touch 127 times) — that's the new "did food economy + race
identity work?" test case.
