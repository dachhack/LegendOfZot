# Handoff — Builds 384-390 (Item Identification → Spell Memorize → Crafting → Monster Scaling)

**Session window:** 2026-05-20 / 2026-05-21
**Branch:** `claude/fix-item-identification-uGNZ7` (about to merge to main)
**Final HEAD:** `01c4fcc` (b390)
**Live reports:** https://dachhack.github.io/LegendOfZot/playtest/

## What this session was about

The b383 handoff flagged five gaps:

1. Spellbook-reading policy (humans/dwarves stuck on starter cantrip)
2. Smart-policy crafting trigger gaps (sausages/lembas rarely fire)
3. Dwarf deep-floor mortality
4. Elixir of Brilliance auto-drink (drops at F4+ but never consumed)
5. HTML report inventory truncation + vendor "gold spent" report bugs

This session closed #1, #2, #4, and **investigated** #3 (turning up surprising data). The two report bugs (#5) are still open.

## The arc — 7 builds in 4 acts

### Act I: Identification + permanent buff drinks (b384-b386)

User: *"Lets work on getting items identified and then used (beneficial potions) so characters can buff up."*

| build | change |
|---|---|
| b384 | Smart policy drinks unidentified potions (was wedge-only) AND identified permanent stat / resistance potions on sight. New game_loop trigger opens inventory proactively for either. PERMANENT_POTION_TYPES set in `playtest_harness.py:2901+` |
| b385 | Three layered fixes: (a) `vendor.py:338` stocks one of {Elixir of Might / Grace / Brilliance / Vitality} at F4+ regular vendors at 25% chance — pre-fix these only spawned in F20+ Magic Shoppes, 0/18 b383 agents reached F20. (b) Smart-policy buy gate hoisted ABOVE the Healing Potion stockpile (was draining gold first). (c) **Fixed a pre-existing crash in `Potion.use()`**: `character.base_attack` → `_base_attack` and `character.base_defense` → `_base_defense` (Character stores both as private). The AttributeError fired after `character.strength` was mutated, then the harness swallowed it silently — the elixir stayed in inventory dripping +2 STR per re-drink. Seed=1 human ran STR to 615 over 1500T before the fix. |
| b386 | Basic-tier elixir prices cut ~50% (Might/Grace/Brilliance 800g→400g, Vitality 1200g→600g). The b385 sweep showed 3/4 stocked elixirs missed the buy at the 800g threshold against mid-game gold (700-1100g per vendor visit after stockpile). |

**Result**: 18-run sweep on b386 = 8 stockings, 4 buys, 4 drinks, 0 leftovers, 0 crashes. The mechanic works end-to-end with stat-delta math confirmed (each Might drink applies +2 STR + +2 _base_attack). Remaining missed buys are gold-gated edge cases.

### Act II: Spell memorization pipeline (b387)

User: *"Lets check into spell book usage"*.

Pre-fix, humans (with Mind Touch cantrip) and dwarves (no cantrip) could never expand their spell repertoire. Vendors stocked 0-2 random spells per visit but the smart policy ignored them, and even if it bought one, no policy hook entered `spell_memorization_mode`.

Four `playtest_harness.py` changes:

1. Expose `pc.get_max_memorized_spell_slots()` + `pc.get_used_spell_slots()` as `max_spell_slots` / `used_spell_slots` in player obs.
2. New `spell_inventory` obs field in `pc.get_spell_inventory()` *insertion order* (NOT sorted) — the combat.py:1454 handler indexes `m<N>` off that order; sorted_inventory ordering would slot-mismatch.
3. Inventory-mode trigger at `:4255+`: when free spell slots > 0 AND an identified non-cantrip unmemorized spell fits, return `m` to enter `spell_memorization_mode`.
4. `spell_memorization_mode` policy handler at `:4855+`: score `healing (10000+power) > damage (5000+power*10/mana) > buff/utility (1000)`, send `m<N>` for best fit.

Plus harness dispatch for `spell_memorization_mode` at `:2121+` (was missing — would have stuck the agent if any path landed them there). Vendor branch gets a spell-buy gate at `:5247+` (gated on `can_cast`, capped at 5 distinct spell names).

**Result**:
- +10 INT planted-stat sweep: 69 spells bought, 13 memorized (Heal, Full Restore, Stone Skin, Lightning Bolt, Blizzard, Meteor Strike, Acid Splash, etc.), 0 crashes
- Vanilla sweep: 101 spells bought, 3 memorized beyond starters (INT 17 gate is high — most vanilla runs die before reaching it)
- Dwarves correctly excluded: hit INT 17 (max_slots > 0) but `can_cast=False` (INT < 20 for max_mana), so trigger skips

### Act III: Crafting + garden fix (b388-b389)

User: *"Lets work on crafting"*.

b383 handoff: *"sausages/lembas wired but rarely fire in playtests — 0/18 in the b383 7000T sweep"*. The current state (after b385's Curing Kit buy priority) was actually ~11 crafts/18 runs, but diagnostic on dwarf seed=1 showed 21 turns where `_pick_craftable_food` returned a recipe but only 2 crafting_mode entries — 19 missed opportunities.

| build | change |
|---|---|
| b388 | Game-loop crafting trigger at `:3032+`. Defense-in-depth so the agent enters inventory for crafting even when no other trigger fires. Sweep impact in seed set was neutral (11 craft entries before vs after) — the existing inventory cascade already catches opportunities IF the agent enters inv for any reason. Reduces craft *latency*. |
| b389 | **Two real bugs** in `room_actions.py:process_garden_action`: (a) `GARDEN_INGREDIENTS` at `item_templates.py:357` carries a `chance` field (0.15 common / 0.10 uncommon / 0.02-0.03 rare) that was never used — `random.choice(loot_table)` gave Dragon Scale (3% intended) and Moonpetal (15% intended) equal weight, starving lembas / sausage recipes that key on the common herbs. Switched to `random.choices(loot_table, weights=...)`. (b) The inline fey-garden loot table at `room_actions.py:2548` puts a DESCRIPTION string in slot [4] (not a chance float), so blindly extracting weights crashed `random.choices` with `TypeError: can only concatenate str (not 'float') to str` — harness swallowed the exception silently and fey-garden harvests vanished entire result lists. Added an isinstance check; numeric-only weights or fall back to uniform. |

**Result**: 18 craft entries vs 11 in b388 (+64%), distributed across all three races (human 4 / elf 6 / dwarf 8). 0 errors.

### Act IV: Monster scaling investigation (b390)

User: *"Lets investigate monster scaling"*.

**The b383 hypothesis (dwarf F9-F12 elite kills) didn't hold.** Death-cause data from the b389 sweep:

| Source | Encounters | Deaths |
|---|---:|---:|
| Hardened / Savage / Dread / Mythic evolution tiers | 11 (2%) | **0** |
| Base-tier regular monsters | ~485 (96%) | 12/17 |
| Tomb elite undead (`tomb_elite=True`, 1.3x stats) | rare | 3/17 (Wraith ×2, Specter ×1, all at F3) |
| Boss / quest mobs | rare | 2/17 (Bug Queen, Dragon Lich) |

The Hardened+ scaling system is fine — 2% of encounters, 0 deaths. The real lethal patterns:

1. **Tomb elites at F2-F5**: F3 ELITE UNDEAD WRAITH has 32 atk × 1.3 = 41 raw, kills L3 player (def ~5, HP ~50) in 2 rounds. Smart-policy threat assessment correctly flags for flee, but the parting blow + adjacent re-engage on tight floors mean the flee gate alone isn't enough.
2. **Cumulative damage on F2-F5 regular encounters**: agents don't heal aggressively enough between fights and a stray Bugbear / Stirge / Harpy finishes them.

**Two playtest_harness.py interventions** at user request (do 1 + 2):

1. **T-tile wayfinder avoid** at `:3410+`. When `pc.level < pc.floor + 3` (mirrors `blocked_guardian_dirs` release gate at `:3522`), T tiles join AVOID so the BFS first_step doesn't pull the agent toward tomb-corner elites. `trapped_no_d` drops the avoid so a stranded agent can still pray at the tomb.
2. **Heal-before-flee narrow window** at `:4820+`. When `monster_too_tough` AND HP between 50-65% AND a heal pot is in bag AND `last_action != "i"`, drink first then flee next turn. Tighter than HP<80% because heals cap at max_hp (>65% wastes the heal) and HP<50% the existing low-HP gate already fires.

**Caveat:** n=18 sweep variance (±2 deaths between runs) is too noisy to show statistically clean improvement. Mean floors held (human 5.33 / elf 3.50 / dwarf 5.50, comparable to b389). The changes are defensive code grounded in the death-cause analysis; a real A/B would need 50+ seeds.

## Key data — b383 vs b390

| Metric | b383 baseline (handoff) | **b390** |
|---|---|---|
| Permanent stat/resistance potions drunk | 0/18 | 4/18 (Elixir of Might in sweep), planted-stat test 10/36 |
| Unidentified potions left in bag at end | many | 0/18 (all drunk via b384's eager-drink path) |
| Spells memorized beyond starter cantrips | 0/18 | 3/18 vanilla (INT 17 gate), 13/12 with +10 INT |
| Sausages + lembas crafted | 0/18 | 18 craft entries / 18 runs (8 dwarf, 6 elf, 4 human) |
| Garden loot weighting | uniform (bug) | proper (15% common / 3% rare) |
| Potion.use() crash on permanent_strength/defense | silent every drink | fixed |
| Alive at 4000T | varies | 0-1/18 (no change — survival is downstream of other systems) |

## Race identity scorecard (still holds per b382 design)

| Race | Magic | Melee/Survival | Verdict |
|---|---|---|---|
| Elf | INT 11+ gate, 2 cantrips, NOW memorizes Heal / Stone Skin / etc. via b387 | Squishy (HP 20), mean F4 | ✓ Magic dominant, NOW SCALES with INT 17 |
| Human | INT 13+ gate, Mind Touch + NOW memorizes additional spells at INT 17 | Balanced (HP 30), mean F5-7 | ✓ Balanced |
| Dwarf | INT 20+ gate, no cantrip, b387 spell-buy correctly skips them | Tank (HP 60), Carnivore Diet 2x meat | ✓ Melee — never casts by design |

## Open issues for next session

### High value
1. **F2-F5 mortality cluster persists.** 5-7/18 deaths happen below F5 to regular monsters (Bugbear / Stirge / Harpy / Kobold / Wight). The b390 interventions are defensive but don't move the needle at n=18. Two concrete options:
   - **Hard floor cap on tomb_elite** (z >= 5): single change in `dungeon.py` or `game_systems.py:2624` to refuse to flag rooms `tomb_elite=True` on shallow floors. Removes the F2-F4 elite death trap entirely. Cleaner than the wayfinder + flee tweaks since it operates at spawn time.
   - **Better mid-combat heal escalation**: drink Greater Heal first if available (current heal_pot_slot just picks first by sort order, which happens to be highest level already — but the agent might be holding only Minor heals).
2. **HTML report inventory truncation** at slot 24 (`playtest_report.py:1573`: `for i in inv[:24]`). Late-game crafted sausages land at slot 60+ and disappear from the rendered table.
3. **Vendor purchase "gold spent" inflated** (`playtest_report.py:1508`: `cur[1] + price * c`). Vendor charges `price` for the whole stack, not per-item.

### Medium value
4. **Larger A/B sweep for b390 interventions** (50+ seeds) to determine if T-avoid + heal-before-flee are actually neutral or slightly negative.
5. **Spellbook drop rate**: vanilla agents rarely reach INT 17 to memorize spells. Either lower the slot threshold (e.g. `(int-14)//2` so INT 16 = 1 slot) or make INT scaling more attainable.
6. **Permanent elixir reachability is borderline** at 400g for non-vitality. Could drop to 250g or add to chest drop tables.

### Low value
7. **Garden weight rebalance**: now that drops are properly weighted, the 15% common rate might actually be too high — humans / dwarves are accumulating large herb stockpiles. The b389 numbers haven't been audited at scale.

## Important file paths & constants

### Smart policy
- `wizardscavern/playtest_harness.py:1066-1102` — player obs (max_spell_slots / used_spell_slots / can_cast / unspent_stat_points)
- `wizardscavern/playtest_harness.py:1391+` — `_spell_inventory_obs()` (separate from `_inventory_obs` to match handler indexing)
- `wizardscavern/playtest_harness.py:2121+` — `spell_memorization_mode` harness dispatch
- `wizardscavern/playtest_harness.py:2901+` — PERMANENT_POTION_TYPES game_loop trigger
- `wizardscavern/playtest_harness.py:3032+` — game_loop crafting trigger (b388)
- `wizardscavern/playtest_harness.py:3410+` — T-tile wayfinder avoid (b390)
- `wizardscavern/playtest_harness.py:4255+` — inventory-mode spell memorize trigger
- `wizardscavern/playtest_harness.py:4436+` — inventory-mode permanent-potion drink path
- `wizardscavern/playtest_harness.py:4820+` — combat-mode heal-before-flee (b390)
- `wizardscavern/playtest_harness.py:4855+` — `spell_memorization_mode` policy handler
- `wizardscavern/playtest_harness.py:5108+` — vendor-mode permanent elixir buy
- `wizardscavern/playtest_harness.py:5247+` — vendor-mode spell-buy gate

### Game state
- `wizardscavern/items.py:897` — `character._base_attack` (was `base_attack`, crashed Potion.use)
- `wizardscavern/items.py:949,951` — `character._base_defense` (was `base_defense`, crashed Potion.use)
- `wizardscavern/items.py:4267-4276` — POTION_TEMPLATES basic-tier prices 400g/600g
- `wizardscavern/item_templates.py:1022-1031` — mirror POTION_TEMPLATES with same prices
- `wizardscavern/vendor.py:338+` — F4+ regular vendor permanent elixir gate (25% chance)
- `wizardscavern/vendor.py:1036-1039` — Magic Shoppe basic-tier same prices
- `wizardscavern/room_actions.py:2562+` — `random.choices(loot_table, weights=...)` weighted garden harvest with fey-table fallback
- `wizardscavern/characters.py:1571` — `get_max_memorized_spell_slots()` formula (INT 17 = 1 slot)

## How to validate / pick up

```bash
# Smoke-test the build compiles
python3 -m py_compile wizardscavern/playtest_harness.py wizardscavern/items.py \
                      wizardscavern/vendor.py wizardscavern/room_actions.py

# Quick single-run check (vanilla)
python3 -m wizardscavern.playtest_harness --seed 5 --race human \
        --turns 4000 --policy smart \
        --report-dir /tmp/test_report

# +10 INT bonus to verify spell-memorize pipeline
python3 -m wizardscavern.playtest_harness --seed 5 --race human \
        --int-bonus 10 --turns 2000 --policy smart \
        --report-dir /tmp/test_spell

# Full sweep + deploy (in-process via playtester subagent)
# 18 runs across 3 races × 6 seeds: 1, 5, 7, 42, 101, 202
# Then call deploy_gh_pages(reports_dir, repo_root, replace=True)
```

## Deploy notes

- `deploy_gh_pages` targets `main:docs/playtest/`, not a `gh-pages` branch. The function uses a worktree to commit + push without affecting the working tree.
- Wrap in `for attempt in range(3): try: ... except: time.sleep(15)` — API 529 has been intermittent.

## Decisions to know

1. **Permanent elixirs at F4+ are basic-tier ONLY** (400g/600g). Greater (+4, 2000g) and Supreme (+6, 5000g) tiers stay locked to F20+ Magic Shoppes so deep-floor Magic Shop finds feel special.
2. **Spell-buy is gated on `can_cast`** — excludes dwarves (cast threshold INT 20, almost never reached) and pre-INT-13 humans. Cap of 5 distinct spell names so the buy doesn't drain gold from stockpile.
3. **INT 17 memorize threshold is intentional** per the `(int-15)//2` formula at `characters.py:1571`. Most vanilla runs don't reach it; +10 INT bonus runs do. This is a design choice — preserves race identity at endgame.
4. **`Potion.use()` crash fix is a real pre-existing bug**, not just a b385 regression. Lived in the code unnoticed because no agent ever drank a permanent_strength / permanent_defense potion until the b384/b385 pipeline.
5. **Garden weighting was a real pre-existing bug**, not a design call. The `chance` field was authored with intent but never wired up; it now matches that intent.
6. **Tomb-elite floor cap is the simpler fix** for F2-F4 deaths, but the user asked for the wayfinder + flee interventions. Cap remains an open option for next session.

## Closing context

Seven builds, all merged to main this session. Branch
`claude/fix-item-identification-uGNZ7` was the work tree; main is at
`01c4fcc` (b390) after merge.

The canary check for this session would be:
- **seed=5 human +10 INT**: should buy a spell, memorize it via `m<N>` at T~100, NOT loop in spell_memorization_mode (the b387 slot-index bug was subtle)
- **seed=1 human**: should buy an Elixir of Might at the F7 Flimsy Fred vendor, drink it cleanly, STR + _base_attack each +2, elixir removed (the b385 crash test)
- **seed=42 dwarf**: garden harvest should now produce common herbs at ~14% per pick (vs 7.7% pre-b389)
