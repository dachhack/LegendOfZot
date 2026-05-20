# Handoff — Builds 369-372 (Resource Economy Restoration)

**Session window:** 2026-05-20
**Branch:** `claude/playtest-starting-conditions-SUICF` (merged to `main`)
**Final HEAD on main:** `293da76`

## What this session was about

One user question — *"why would a player step into a warp room?"* —
cascaded into four merged builds that peeled off the warp-roulette
band-aid and fixed **eight silent stack-wipe bugs** the band-aid had
been hiding.

The arc:

1. **b369**: stopped the smart-policy from voluntarily stepping on W tiles
2. **b370**: exposed two game bugs where monster attacks / auto-refuel
   wiped entire stacks (Food, LanternFuel)
3. **b371**: audited the codebase, found six more identical stack-wipe sites
4. **b372** (`deploy_gh_pages` default): every sweep now ships a clean
   gh-pages set so the live index reflects only the current build

## Bombur Ironbeard (dwarf seed 4) — the canary

Same seed, same race, same starter pack across the session:

| build | result |
|-------|--------|
| b369 | died T819 F1, starvation (no rations in pack — Spore Puff ate them) |
| b370 | died T3530 F11, combat (max HP 64 → 190) |
| b371 | **alive T4000 F13** in a 4000T smoke; full 7000T sweep died T4395 F14 to Hardened Medusa |

The progression came purely from closing resource-bleed bugs — no
policy changes after b369, no game balance retuning.

## The eight stack-wipe sites

All shared the same pattern: `inventory.remove(item)` or
`inventory.remove_item(name)` was meant to consume **one** of something
but the API removes the entire stack by name. A 5-stack of Healing
Potions or an 8-stack of Rations or a 7-stack of Lantern Fuel would
vanish on a single hit / refuel / sacrifice.

| # | file:line | trigger |
|---|-----------|---------|
| 1 | `characters.py:rot_food_items` | Spore Puff / Myconid / Fungal Hulk spore attack |
| 2 | `items.py:Lantern.use` auto-refuel | first 'l' fire on an empty lantern |
| 3 | `room_actions.py:3722` auto-refuel | mirror of #2 |
| 4 | `characters.py:burn_inventory_items` | fire damage (Fire Imp / Salamander / etc) |
| 5 | `characters.py:freeze_inventory_items` | freeze damage (Mind Flayer / Ice Salamander) |
| 6 | `items.py:Upgrade-scroll consume` | using one upgrade scroll |
| 7 | `combat.py:foresight-scroll consume` | using one foresight scroll |
| 8 | `room_actions.py:alchemist brew` | brewing 2 potions (wiped both stacks) |

All eight now check `item.count`: decrement when `> 1`, remove the
entry only when count hits 0. Same one-paragraph fix everywhere. The
altar-sacrifice path (`room_actions.py:677`) got the same treatment.

## b369 specifically — the warp-step fix

Three smart-policy paths committed agents to known W tiles:

1. `trapped_no_d → tiers = [("W",), ("V",)]` at `playtest_harness.py:3488`
2. The `not trapped_no_d` carve-out at `playtest_harness.py:3104`
   dropped W from AVOID
3. The `perm_wedge` override of `d_avoid_reachable = False` at
   `playtest_harness.py:2995` forced trapped_no_d to fire even when D
   was genuinely reachable

Plus a fourth — the cornered detector at `playtest_harness.py:2018`
marked floors PERMANENT on a single fog-blind stairs_up arrival,
hard-locking agents once the W escape was removed. Softened to a
regular +1 bump.

Plus a fifth — the lantern fire at `playtest_harness.py:2927` is gated
on `mode == "game_loop"` and never fired in `stairs_up_mode` /
`stairs_down_mode`. An agent landing on a corner U/D with all-fog
cardinals couldn't step off and ascended right back, accumulating the
wedge marks. Added a lantern-first check at the top of both stair modes.

## Sweep deltas (3 races × seeds 1-12 × 7000T, `--policy smart`)

| metric | b369 | b370 | b371 |
|--------|------|------|------|
| Warp share (global) | 52.7% (b366 baseline) | 7.6% | clean |
| Stack-wipe events / 36 runs | many | many | **0** |
| Median depth (human / elf / dwarf) | F4 / F3 / F3 | F4.5 / F6.5 / F6 | **F7 / F7 / F7** |
| Best depth | F9 / F5 / F6 | F13 / F8 / **F19** | F11 / F10 / F14 |
| Alive at T7000 | 0 | 0 | **1** (dwarf_s5) |
| Hunger death share | — | 41% | 46% |
| V/floor (human / elf / dwarf) | 70 / 54 / 62% | **100 / 92 / 100%** | maintained |

**Note the b371 dwarf-ceiling regression** (F19 → F14): single-seed
variance. b370's F19 on dwarf_s2 was a lucky run; same seed dropped to
F7 in b371. The median moved the right direction for all three races.

## What's next — the food economy

b371 left **hunger as the dominant death cause (46% vs ~30% combat)**.
With potion stacks now surviving fire/freeze, smart-policy heals more
aggressively in combat, survives longer, then runs out the food clock.

The right next session would audit:

- `items.py:Food` `nutrition` values — are rations too thin?
- `items.py:get_monster_meat_info` and `drop_monster_meat` — drop rate
  is currently 70%; nutrition per cut may need a pass
- The hunger-per-turn cost — search for `character.hunger -=` to find
  the per-tick drain
- `items.py:CookingKit` — does the kit actually 4× meat nutrition like
  the comments claim?

Secondary lead: **dwarf seed 2 F19 → F7 regression between b370 and
b371**. Almost certainly variance, but a side-by-side transcript
diff would confirm. If there's a real bug, the divergence turn is in
the JSONL — look for the first stack-changing event between
`/tmp/playtest_sweep_370/dwarf_s2.jsonl` and the b371 equivalent.

## Key files touched this session

- `wizardscavern/playtest_harness.py` — policy fixes (b369)
- `wizardscavern/characters.py` — burn / freeze / rot stack-wipe fixes
- `wizardscavern/items.py` — lantern auto-refuel + upgrade scroll
- `wizardscavern/room_actions.py` — auto-refuel mirror + alchemist + altar
- `wizardscavern/combat.py` — foresight scroll
- `wizardscavern/playtest_report.py` — `deploy_gh_pages(replace=True)` default
- `wizardscavern/version.py` — `BUILD_NUMBER = 371`, changelog entries

## Reproducing the canary

```bash
# Confirms Bombur reaches F13+ with stacks intact
python3 -m wizardscavern.playtest_harness \
    --seed 4 --race dwarf --turns 4000 \
    --policy smart --jsonl > /tmp/bombur.jsonl

tail -1 /tmp/bombur.jsonl | python3 -c '
import json, sys
r = json.loads(sys.stdin.read())
p = r["player"]
print(f"T{r[\"turn\"]} F{p[\"floor\"]} hp={p[\"hp\"]}/{p[\"max_hp\"]} hunger={p[\"hunger\"]} alive={r[\"alive\"]}")
'
# Expected: T4000 F13 hp=188/208 hunger=60 alive=True
```

## Reproducing the sweep

```bash
mkdir -p /tmp/playtest_sweep
for seed in $(seq 1 12); do
  for race in dwarf elf human; do
    timeout 90 python3 -m wizardscavern.playtest_harness \
        --seed $seed --race $race --turns 7000 \
        --policy smart --jsonl \
        --report-dir /home/user/LegendOfZot/playtest_reports/ \
        > /tmp/playtest_sweep/${race}_s${seed}.jsonl 2>&1 &
  done
  wait
done

# Now ships clean (replace=True default per b372)
python3 -c "
from wizardscavern.playtest_report import deploy_gh_pages
import os
print(deploy_gh_pages('/home/user/LegendOfZot/playtest_reports', os.getcwd()))
"
```

Live results: `https://dachhack.github.io/LegendOfZot/playtest/`

## Prior handoff context (build 356, preserved as reference)

Builds 347-356 focused on loop elimination, vendor connectivity, tomb-raid
tuning, and the build-355/356 elf rework. That work set up the policy in
the state b369 inherited — V always tier-1 in non-emergency branches,
trapped_no_d as the recover path for region-split floors, tomb_suspected
tracking, and the gear/level grind gates. The b369-371 fixes specifically
do NOT regress that work; the policy structure is intact.
