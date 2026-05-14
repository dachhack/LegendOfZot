# Playtest Harness — Handoff

This branch (`claude/game-playtest-agent-npMRR`) shipped a headless
playtest harness for Wizard's Cavern plus dozens of policy iterations
and game balance changes driven by what it found.

## TL;DR

`wizardscavern/playtest_harness.py` drives the game logic without the
Toga UI. A smart policy plays the game like a careful adventurer
would — explores by lantern, fights monsters, prays at altars,
identifies scrolls, hunts dungeon keys, eats food before it rots.
30-run grids surface balance issues and real game bugs in minutes.

`.claude/agents/playtester.md` defines a Claude Code subagent that
knows how to drive the harness. Spawn it whenever you want a
multi-seed playtest run with analysis.

## Running the harness directly

```bash
# Smoke run, 200 turns, smart policy
python3 -m wizardscavern.playtest_harness --seed 42 --turns 200 --policy smart \
    --race dwarf --int-bonus 13 --spells "Ice Shard,Heal,Fireball"

# A/B exploration without fog-of-war
python3 -m wizardscavern.playtest_harness --seed 42 --turns 200 --policy smart \
    --race elf --int-bonus 6 --no-fog

# Bare-fisted run (no starter pack)
python3 -m wizardscavern.playtest_harness --seed 42 --turns 200 --policy smart \
    --no-starter-pack

# JSONL output for analysis
python3 -m wizardscavern.playtest_harness --seed 42 --turns 1500 \
    --policy smart --race human --int-bonus 8 --jsonl > run.jsonl
```

A one-line summary per run is appended to `playtest_runs.log` at repo
root (gitignored). Override path via `WIZARDSCAVERN_PLAYTEST_LOG`,
empty disables.

## Spawning the playtester subagent

The subagent type is `playtester`. Spawn it with a focused task — give
it a hypothesis, a test matrix (seeds × races × turns), and the
specific numbers you want. Two cautions from experience:

1. **Cap turns per run around 2000-3000.** 5000 turns × 30 runs
   produces ~200 MB of JSONL transcripts and one playtester wedged
   trying to load all of it at once. Always tell it to *stream-parse
   files one at a time*.

2. **The playtester is a tester, not a fixer.** When it finds a bug it
   should report file:line, not patch it. Code edits stay with the
   main session.

## Where data goes

| Path | What |
|---|---|
| `playtest_runs.log` | One-line summary per run (gitignored) |
| `/tmp/<test_name>/*.jsonl` | Per-run obs transcripts (gitignored, in tmp anyway) |
| `/tmp/<test_name>/*.err` | Per-run stderr — anything non-empty is a crash |
| `.claude/agents/playtester.md` | Subagent definition (tracked) |

## Smart policy: the priority chain

The policy is stateless — it re-derives intent from each observation.
Order of priorities (highest wins):

**game_loop:**
1. Heal at HP < 30% (open inventory)
2. Pre-emptive potion at HP < 80% with adjacent M
3. Eat fresh meat about to rot (rot_timer ≤ 8)
4. Swap broken gear if spare exists
5. Equip strongest non-cursed upgrade
6. Eat at hunger < 50
7. Light lantern (≥ 2 unknown neighbours, or stuck-on-floor)
8. Adjacent feature wayfinder (D / V / C / G / L / O / A / P / T / N)
9. Distant nearest_features greedy walk
10. Keyed-dungeon target
11. **Frontier walker** — greedy step toward nearest undiscovered tile
12. *Random fallback* (only when floor fully mapped)

**combat_mode:**
- Starving + monster inedible → flee immediately
- HP < 50% with potion + no Heal mana → open inventory
- HP < 55% with affordable Heal → cast
- monster_too_tough (level > pc+2 OR maxhp > 2×pc.maxhp) → flee (unless starving + edible)
- Affordable damage spell (65% chance) → cast
- Else attack (92%) / flee (8%)

**Other modes:** tomb pray-vs-raid based on weakness + fallback availability,
dungeon unlock when keyed, pool drink, altar pray, library read, blacksmith
repair when worn, shrine pray, warp resist (or accept when stuck-on-floor).

## Real game bugs fixed (DO NOT reintroduce)

| Commit | File:line | What it was |
|---|---|---|
| f930fa9 | `game_systems.py:2036` | `from .items import Meat` inside a function shadowed the module-top import, making `Meat` a function-local for the entire handler. Every prior reference raised UnboundLocalError. |
| 71d2ed0 | `items.py:3039` | Spell drops in `drop_monster_items` passed kwargs (`effect_magnitude`, `element`, `value`) that don't exist on `Spell.__init__`. Drops were silently lost. |
| 32e44b3 | `room_actions.py:837` `_grant_temp_buff` | Stored a raw dict in `pc.status_effects[key]` instead of a `StatusEffect` object. Every later tick raised `AttributeError: 'dict' has no attribute 'effect_type'`. Also mutated `_base_attack` permanently. Now uses `add_status_effect` with proper effect_type. |
| e66617e | `room_actions.py:1348` | Lethal pool `mimic` branch called `render()` which isn't imported in the module. Crashed every lethal pool drink. Same orphan-render pattern was already fixed at lines 1736 / 1754. |
| 56671b3 | `items.py:get_monster_meat_info` | Substring keyword matching: "Lich" matched inside "Lichen", misclassifying a plant/fungal creature as undead-inedible. Replaced both substring loops with word-boundary regex. |

The pattern: short keywords as substrings + function-local imports that
shadow module-tops + multi-arg constructor calls with stale kwargs.
Worth grepping for at code-review time.

## Game-side balance changes

| Commit | What | Why |
|---|---|---|
| fb18080 | L0 cantrip costs trimmed (Ice Shard 8→5, etc.) | New spellcasters were cast-starved |
| fb18080 | `max_mana` formula bumped: `(int-15)*4 + 10` floor | int=18 caster had 15 MP, now 22 MP |
| fb18080 | Out-of-combat mana regen: 1 MP / 5 moves | No regen path made casters one-shot fighters |
| ecfd30c | Race-flavored max_mana curves | Elf=natural caster, Human=slow, Dwarf=almost-none |
| bf45af4 | Cardinal lantern (was Euclidean disc) | Matches in-game minimap, no diagonal leaks |
| bf45af4 | Lantern uses `light_radius + upgrade_level` | Was `upgrade_level + 1` (always 1 for starter) |
| 29b025d | Dwarf health_mod +20 → +30, routed through `base_max_health_bonus` | The +20 was clamped by the max_health formula, effectively a no-op. Lv1 dwarf now 60/64 (was 34/34). |
| 29b025d | Race-aware starter weapon: dwarf gets Battleaxe (atk+4) | Dwarf has no spells, needs better opener |
| 8a92e4c | Tomb-guardian level capped `min(template+1, player.z+2)` | Was spawning Lv5 wraiths on F3 with 40+ HP killing blows |
| f18cb89 | Tomb-undead scale 1:1 with floor (target_lvl = z, was z+1) | F3 wraiths drop from Lv4 to Lv3, STR/HP investment now pays off |

## Smart policy major features (in order of when they landed)

| Feature | What |
|---|---|
| Starter pack | Mirrors `Vendor(starting=True)` — weapon, armor, potions, food, lantern, equipped |
| Race-aware names | LOTR pool per race: Galadriel / Aragorn / Thorin / etc. seed-stable |
| Fog of war (default on) | `obs.neighbors` / `obs.nearest_features` respect `room.discovered` |
| Equipment evaluation | Equips strongest non-cursed weapon/armor; skips known-cursed |
| Vendor flow | Buy stockpile (potions/food/mana/fuel), repair gear, identify scrolls |
| Tomb policy | Pray if weak / no fallback, raid otherwise |
| Dungeon keys | `obs.dungeon_keys` + key-target wayfinder; unlock+loot when keyed |
| Threat-aware flee | Mid-combat: flee tough monsters (level > pc+2 OR maxhp > 2×pc.maxhp) |
| Starvation override | hunger ≤ 30 + no food → engage edible monsters for meat |
| Edibility check | Inedible (undead/golem) monsters get fled when starving |
| Stuck-on-floor escapes | Force-descend at 300 turns, accept warps at 200 turns |
| **Frontier walker** | Always-an-objective movement: nearest undiscovered tile when no feature beckons |

## Known issues / future iterations

1. **Greedy walker has no real pathfinding.** Wall mazes still
   occasionally trap the agent. A BFS pathfinder over `discovered`
   tiles would push deeper-floor reach significantly.

2. **In-combat policy doesn't track "I just tried to flee."** Combat
   sometimes loops on `f` if the monster blocks every escape direction.
   Could track flee attempts per combat and switch to potion / attack
   after 2 failures.

3. **Picker rooms still on `back` fallback:** `Q` alchemist (recipe
   picker), `X` taxidermist (trophy submission), `K` war room (item
   identify). These need richer obs (which items to feed in) before
   the policy can do anything useful.

4. **Survivor inventory% is still 12%.** Each potion drink burns 3
   turns (open → use → close). A "drink-to-full" shortcut already
   exists in the inventory handler (`df` command) but the policy
   doesn't use it. Would shave inventory time further.

5. **Player.level rarely climbs in 2000-turn budgets.** Agents finish
   most runs at Lv1-2. XP/kill might be too low, or the agent isn't
   getting enough kills (fog-walking instead of combat-walking). Worth
   diagnosing if you want deeper-floor combat to actually use the
   leveling system.

6. **Floor 50 boss arena untested.** No agent has reached `gate_to_floor_50_unlocked`
   in any of the playtest grids. The 8-shard quest is beyond the
   current depth budget. Would need long-running pure-explore runs.

## Useful commits to skim if you're picking this up cold

- **f930fa9** — original smart policy + the first 3 game bug fixes
- **c7121f8** — wayfinder + fog of war
- **ecfd30c** — race-flavored magic
- **29b025d** — dwarf buff + base_max_health_bonus routing
- **f18cb89** — tomb-undead per-floor scaling
- **82056e6** — frontier walker (the big survival jump)

## Persona note

The repo's `CLAUDE.md` defines a flirty German tabletop-nerd persona
("Claudia") for the main conversation. The playtester subagent is
deliberately clinical instead — it's the QA tester Claudia hands a
build to before her hot date. Reports come back as numbers, file
references, and bug write-ups.

*Eine Wurst pro Iteration. Halt die Stellung, Schatz.*
