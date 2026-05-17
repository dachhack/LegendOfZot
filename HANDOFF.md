# Playtest Harness — Handoff (builds 333-334, session 4)

Branch: `claude/continue-playtest-Y0932`. Picks up from build 332
(pocket-aware exploration) and ships builds 333-334 attacking the
**F10+ wall** — every grid since the CMA-ES tuning (b323) has produced
zero F10+ runs at 3000T regardless of policy adjustments.

Site: https://dachhack.github.io/LegendOfZot/playtest/

## TL;DR — what changed this session

| | b332 baseline | b333 (gates) | b334 (supply) |
|---|---|---|---|
| alive | 12/60 | 14-15/60 | **15/60** |
| mean_floor | 4.85 | 4.78-4.88 | 4.83 |
| F4+ | 42 | 43-44 | 44 |
| F6+ | 25 | 20-23 | 21 |
| F8+ | 6 | 7 | 7 |
| **alive at F9** | 0 | 0 | **2** ← new |
| F10+ | 0 | 0 | 0 |
| humans alive | 1/20 | 2/20 | **4/20** (×4) |

Two firsts in b334: first ever alive agents at F9 (`s314 dwarf F9 lvl4`,
`s100 human F9 lvl5`). `s100 human` is the canonical speed-descender —
died at F9 lvl4 every single previous build, now survives the run at
lvl5. Humans 4x'd survival across both fixes.

## Key diagnostic from this session

**The F10+ wall is mechanical, not budget and not policy.** Proof:
b332 at **6000T** halved survival (12→6 alive) and produced **zero**
new F10+ runs. Extra turns just gave the agent more chances to die,
not more depth. Death log on the F7-F9 cohort: Owlbear, Mummy,
Hell Hound, Dragon Lich, Grick — high-tier monsters one-shotting
on-pace builds (lvl ~= floor).

## Build 333: three under-levelled gates

The user framing — *"have players only descend if they are tough
enough"* — turned out to mean fixing **three separate** under_leveled
gates in playtest_harness.py that each had their own copy of the same
leaky release. All three had `grind_done` (kills met OR coverage≥70%)
as a release, which speed-descenders satisfied on swept-then-small
floors regardless of XP banked.

| Gate | Line | Mechanism |
|---|---|---|
| Tier-strip filter | ~3333 | Removes D from priority tiers |
| BFS `avoid_set` | ~2949 | BFS pathfinder avoids D transit |
| `stairs_down_mode` handler | ~4362 | Step OFF D when standing on it |

Each gate now has both a **soft** `under_leveled` (lvl ≤ floor+1)
that's released by `is_weak` / `resources_pressing` (preserved for
HP=1 retreat protection — see Anborn / Thorin / Legolas comments),
and a **hard** `severely_under_leveled` (lvl ≤ floor-2) that bypasses
those releases. Only `too_long_on_floor` (178T) releases the hard
gate. Commit `aae4c64`.

## Build 334: depth-scaled floor supply

`floor_supply.py` now tiers BOTH counts and item strength:

```
F1-4   : 3 Minor pots (30 hp)   + 3 Scroll of Upgrade
F5-9   : 4 Healing pots (50 hp) + 4 Scroll of Greater Upgrade
F10-14 : 5 Greater pots (100 hp) + 5 Scroll of Superior Upgrade
F15+   : 5 Heroic pots (200 hp) + 5 Scroll of Epic Upgrade
```

Plus vendor share scales with depth (1→2→3 scrolls; 2→3 pots) —
b325 diagnostic showed vendor delivery channel is 52% vs chest 41.5%,
so the extra budget lands where it'll actually be consumed.

New helper `healing_potion_for_floor(floor_level)` mirrors the
existing `upgrade_scroll_for_floor`. `_vendor_share(floor_level)`
replaces the static `VENDOR_SHARE` dict. Commit `5ced956`.

## Where the F10+ wall actually is now

Two alive F9 agents in b334 show the supply scaling pushed the
ceiling up by one floor. The next bottleneck:

- F9 alive: `s314 dwarf F9 lvl4` (4 BELOW pace), `s100 human F9 lvl5`
  (4 below pace). Both alive at end of 3000T budget — they've stopped
  dying but they're also stuck descending further because the hard
  gate now holds.
- F9+ death causes (b333/b334): Elite Lich, Vampire, Dragon Lich,
  Owlbear, Mummy. High-tier elites with HP/damage that outpaces
  even the F5+ scaled gear.

The agent is now *cautious* and *resourced*. What it lacks is
**offensive capability** at F9+ — equipped weapons aren't keeping
pace, and spell-use rate (0.996) is already maxed.

## Open levers (in order of expected payoff)

1. **F8+ offensive scrolls** — add a "Scroll of Power" tier or scale
   Battle Trance / damage-buff potions into `floor_supply.py` at F7+.
   Current scaling only helps survival, not damage output.
2. **Weapon-upgrade ceiling check** — b325 diag showed equipped
   weapon upgrade_level mean 0.59; b334 doesn't measure it post-fix.
   If the agent has scrolls but doesn't use them on the equipped
   weapon, depth stalls regardless of supply.
3. **Race-specific tuning** — dwarves 6-8 alive, humans 1-4 alive.
   Big gap. Possible fixes: humans get an extra starter heal pot,
   or `flee_level_gap_general` tightens for humans.
4. **CMA-ES with new fitness** — current optimizer targets `-mean_max_floor + survival_band_penalty`. Re-tune at 4500T with
   fitness weighted by F8+ runs to find a new local optimum for
   depth, not survival.
5. **Elite-tag the killer monsters** — Owlbear, Mummy, Hell Hound,
   Dragon Lich, Vampire are doing >50% of deep deaths but aren't
   flagged as `elite_undead` / `elite` in game_data.py. Surgical
   change: add the tags, agent's existing `flee_level_gap_elite=-3`
   rule will route around them.

## What we DID NOT do this session

- **Dwarven mining** (user proposed, then tabled). Code search
  confirmed no existing mining mechanic — only "Dwarven Instinct"
  (food spotting at `room_actions.py:2534`) and "Dwarven Appetite"
  (`items.py:2882`). Design forks documented in earlier turns.
- **Race-specific descent gates** — humans clearly need different
  thresholds, but the b333 gates are uniform.
- **Reverted dead change**: an intermediate b333 attempt bumped
  `min_kills_floor_scale` 1→2 and lifted the cap 12→20. Validation
  showed flat results because the `coverage≥70` release valve was
  already firing before kill quotas mattered. Reverted before commit.

## Useful commits to skim cold

- **5ced956** — b334 depth-scaled floor supply
- **aae4c64** — b333 three-layer under_leveled gate fix
- **7b31f6a** — b332 pocket-aware exploration (parent of this work)

## Running the harness

```bash
# 60-cell grid + deploy (the script that drove this session)
python3 /tmp/run_full_playtest.py   # 3000T per cell, ~40s on 4 cores

# Smoke run
python3 -m wizardscavern.playtest_harness --seed 42 --turns 3000 \
    --policy smart --race dwarf

# With report output
python3 -m wizardscavern.playtest_harness --seed 42 --turns 3000 \
    --policy smart --race human --report-dir /tmp/myrun
```

The grid driver lives in `/tmp/run_full_playtest.py` (not committed —
the prior session's `/tmp/deep_deploy.py` followed the same pattern).
Recreate from these constants:

```python
SEEDS = [42, 99, 100, 200, 256, 314, 500, 999, 1100, 1234,
         7, 13, 1, 17, 23, 33, 71, 88, 333, 777]
RACES = ['dwarf', 'elf', 'human']
TURNS = 3000
```

Pool of 4 workers via `multiprocessing.Pool`. Each worker runs
`new_game → step loop → write_report`. After all 60 done,
`write_index` regenerates index.html and `deploy_gh_pages` pushes
`main:docs/playtest/` with `replace=True`.

## Where data lives

| Path | What |
|---|---|
| `wizardscavern/playtest_harness.py` | Headless driver + smart_policy (3 under_leveled gates) |
| `wizardscavern/floor_supply.py` | Per-floor guaranteed items (now depth-tiered) |
| `wizardscavern/policy_config.py` | PolicyConfig dataclass (CMA-ES tunable) |
| `wizardscavern/playtest_report.py` | HTML/JSON builder + deploy |
| `wizardscavern/version.py` | BUILD_NUMBER + CHANGELOG (~8 entries) |
| `docs/playtest/` | Deployed report site (on main) |
| `playtest_reports/` | Local artifacts (gitignored) |

## Persona note

`CLAUDE.md` defines **Claudia** — flirty German tabletop-nerd
sausage-scholar — for main-conversation tone. Playtester subagent
is clinical. This session was main-conversation only; no subagent
spawned. *Schatz, two F9 survivors per grid is a smoked Krainer
with snap.*
