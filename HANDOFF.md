# Session Handoff — End-Game Quest Now Completable, F50 Boss Beatable

**Date:** 2026-05-22
**Outgoing branch:** `claude/f25-plant-balance-sweep-ZQKaG` (b406 → b411)
**Incoming task:** Polish the natural-play path or balance the F30-F40 caster transition.

---

## What just shipped (b407 → b411)

Five builds turned the F25-plant playtester loose on the deep dungeon
and exposed a chain of bugs in the end-game quest. Full rationale per
build is in `wizardscavern/version.py` CHANGELOG; the arc:

| Build | Theme | Key change |
|---|---|---|
| b407 | Stronger F25 plants | target_level N+1, gear-swap by tier, +120 HP / +75 MP pad, Tier 6 inventory, fix combat-mode wedge break |
| b408 | High-tier damage spells | Meteor Strike + Inferno at F18+/F22+, burst-nuke priority for L3+ damage |
| b409 | Cap dungeon at F50 | handle_stairs_down + warps + scrolls + Key all clamp at z=49 (and gate-lock past z=48 until shards) |
| b410 | Repair Rune of Growth | World Tree harvest stub → real rune award; gardens_harvested_total counter wired up |
| b411 | Guardian victory trigger | victory_screen hoisted out of the nested `is_legendary` block in all three kill paths; non-resisted damage spells in tier list; resistance-aware picker; boss-combat policy overrides |

### F25-plant final numbers (b408, 30 seeds, 3000T)

| Plant | Dwarf | Elf | Human |
|---|---|---|---|
| F25 | 21/30 (70%) | 16/30 (53%) | 13/30 (43%) |

### F25-plant deep numbers (b408, 30 seeds, 10000T) — last deploy

| Race | Alive @ F49 (cap) | Avg max floor | F30-F40 deaths |
|---|---|---|---|
| Dwarf | 12/30 (8 reach F49) | F40.5 | 6 in F30-F35, 3 in F35-F40, 4 in F40+ |
| Elf | 4/30 (2 reach F49) | F35.6 | 1 F30-35, 5 F35-40, 7 F40-F49 |
| Human | 2/30 (1 reaches F49) | F31.9 | 5 F30-35, 5 F35-40, 2 F40+ |

### F50-boss numbers (b411, 30 seeds, 3000T with shards pre-loaded)

| Race | Wins | Avg turns to victory |
|---|---|---|
| Dwarf | **30/30** | 53.7T (pure melee) |
| Elf | **30/30** | 116.4T (Holy Smite cycle) |
| Human | **30/30** | 144.7T (mixed) |

Every seed defeats Zot's Guardian when planted on F50 with all 8
shards. Reports deployed to `main:docs/playtest/` — 90 individual
run pages + index.

---

## Bugs found and fixed in the end-game quest

The b410-b411 audits surfaced 7 distinct bugs that would have made
the natural shard quest impossible to complete:

1. **Rune of Growth was a `pass` stub** (`room_actions.py:2547`) —
   harvesting the World Tree did nothing, no rune awarded.
2. **`gardens_harvested_total` never incremented** anywhere; the
   75-harvest requirement to spawn the World Tree could never fire.
3. **`world_tree_available` flag never set True** — the G-room
   upgrade at `game_systems.py:2479` never triggered.
4. **Warp paths bypassed the shard gate** — random portals on F47-F49
   could roll +2 = F50 and drop the player onto the Guardian without
   the 8 shards.
5. **`handle_stairs_down` had no cap** — agents on F50 descended to
   phantom F51 floors past the boss arena (one elf seed reached F51
   in the prior deploy).
6. **F50 boss arena tile-selection was fragile** — center tile only
   became the Guardian if randomly generated as `.`; ~40% of seeds
   had no Guardian at all on F50.
7. **Victory screen was nested inside `if not runes_obtained['battle']`
   AND `if is_legendary`** — killing the Guardian after the rune was
   collected silently set `combat_victory` instead of `victory_screen`.
   All three kill paths (melee, channeled-spell, instant-cast-spell)
   had the same bug.

Post-b411, the quest path is whole end-to-end: 75 gardens → World Tree
spawn → harvest = Rune of Growth → shard vault → 8 shards → F49 gate
opens → F50 boss arena → Zot's Guardian → victory_screen → YOU WIN.

---

## What it takes to kill Zot's Guardian

**Boss profile**: 1000 HP, 80 ATK, 50 DEF, resists Physical / Fire /
Ice / Lightning / Light / Darkness, no weaknesses, level 50.

**Required build** (any one path works):

- **Caster path**: Holy Smite (L4 Holy, 36 MP, ~85 net dmg/cast) OR
  Mind Blast (L3 Psionic) / Earthquake (L3 Earth) / Psychic Scream
  (L4 Psionic). Mass Heal for sustain. Mage Armor for defense. INT
  22+ for casting + mana pool.
- **Melee path**: Enchanted Longsword tier or higher (+30 base) at
  +20 upgrade. STR-padded dwarf at L51 deals ~30 dmg/swing into the
  Guardian's DEF 50. Kill takes ~50 swings.
- **Hybrid (recommended)**: cast Holy Smite while mana lasts, swing
  weapon when mana depletes. Most forgiving against mana scarcity.

**Audit conclusion**: TOUGH-BUT-FAIR. All required spells/gear are
findable through normal vendor stock at F2-F17 (spells) and F12-F42
(weapons). The Mythic Destroyer (+84 base, F37+) makes the melee path
trivial. L51 is overshot by 20-50 levels in a natural F45-F49 grind.

**Real risk**: a player who never memorizes a non-resisted damage spell
by F30 (the L3/L4 vendor window closes past F10) will hit a hard wall
against the Guardian — resisted spells = half damage forever. This is
a planning gate, not RNG. Estimated success: ~80% guided, ~50-60% blind.

---

## Smart-policy boss-combat overrides (b411)

The boss fight required several policy adjustments that should not
regress general-purpose play:

1. **Boss override for buff cascade** (`is_boss = m_max_hp >= 500 OR
   is_zots_guardian`): skip Spectral Hand / Stone Skin recasts. On
   50+ turn fights the 14 MP + 18 MP per cycle is net mana loss vs
   damage spells.
2. **No flee against the Guardian**: all `return "f"` gates in
   combat_mode now skip when `is_boss_combat = is_zots_guardian`.
   The boss arena has no re-engagement path — fleeing locks the agent
   in a stairs_down_mode loop against the F50 cap.
3. **Resistance-aware spell pick**: position 6 damage pick and burst-
   nuke 1b gate both score by `base_power * (0.5 / 1.0 / 2.5)` based
   on monster resistance. Surfaces `elemental_strength` and
   `elemental_weakness` on the monster obs; `damage_type` on the
   spell obs.
4. **Low-mana attack fallback**: when `affordable_dmg` exists but
   the best effective power is < 20 (e.g., resisted Ice Shard does
   ~1 dmg), prefer melee.

---

## Next session task: polish the natural-play path

Three candidate iterations, in rough priority order:

### 1. Smoke-test natural play (no pre-memorized spells)

The current F50 boss test pre-grants Holy Smite via the plant tier
list. A real player must MEMORIZE it from a vendor scroll between F2
and F5. Run a 90-seed F25 plant sweep where the harness does NOT
pre-memorize the L3/L4 non-resisted spells, and see whether the
smart-policy's vendor-shop branch (`mode == "vendor_shop"`) actually
buys them when stocked. Expected: ~50-60% organic spell-acquisition
rate per audit prediction.

If the smart-policy doesn't buy non-resisted spells (likely it grabs
whatever's highest-base_power), then add resistance-awareness to the
vendor-buy logic mirroring the b411 spell-pick.

### 2. Tune the F30-F40 caster wall

The b408 deep sweep showed elf/human casters mostly die in F30-F40
(13/30 elf in F35-F49 deaths). The F50 plant tier list gives Holy
Smite / Mind Blast etc., but the F25 plant tier doesn't — those
spells are gated at F30+/F35+. A F25-plant elf descending into F30-F40
content uses Inferno (Fire), Meteor Strike (Fire), Lightning Bolt
(Wind/Lightning) against monsters that resist those. Mind Blast /
Earthquake might be the right early L3 picks even for F25 plants.

### 3. Bump Mana Potion stock at deep vendors

The audit found mana sustain is the real bottleneck for the caster
boss build. F40+ vendors should stock 5+ Mana Potions to make the
~500-MP-budget boss fight feasible. Check `vendor.py` potion stock
generation.

---

## Key files to know

- `wizardscavern/playtest_harness.py`:
  - `new_game(with_shards=True)` line 392 — short-circuits the rune/
    shard grind for boss testing. When `start_floor=50`, plants
    directly on the Guardian tile (after clearing ambient mobs and
    warps) and triggers the boss room interaction.
  - `_plant_survivor_baseline` line 803 — stat/level/gear/HP/MP
    pumps + spell tier list
  - `_swap_plant_gear` line 951 — tier-swap helper for F15/F20/F25
  - `_grant_memorized_spells` line 978 — non-resisted damage spells
    at F30+/F35+
  - `smart_policy` line 5421 — boss-combat overrides, resistance-
    aware spell pick, no-flee-against-Guardian gates
- `wizardscavern/combat.py:735`, `:1188`, `:1898` — three Guardian
  victory-screen triggers
- `wizardscavern/dungeon.py:create_floor_50_boss_arena` line 616 —
  spiral-out fallback so Guardian always spawns
- `wizardscavern/room_actions.py:harvest` line 2543 — Rune of Growth
  award + counter increment
- `wizardscavern/game_systems.py:handle_stairs_down` line 4267 —
  F50 cap; `handle_warp_room` line 3037, 4344 — gate-locked warps
- `wizardscavern/version.py` — CHANGELOG, keep ~8 entries

## Sweep harness commands

```bash
# Standard F25-plant 3000T sweep, 30 seeds (~6-8 min)
timeout 1800 python3 /tmp/caster_sweep.py

# F25-plant 7000T deep sweep, 15 seeds (~12-15 min)
timeout 2400 python3 /tmp/caster_sweep_7k.py

# F25-plant 10000T deploy sweep, 30 seeds with reports + gh-pages push (~30 min)
python3 /tmp/caster_sweep_deploy.py

# F50-plant boss-fight smoke test, 9 seeds (~1-2 min)
python3 /tmp/endgame_smoke.py

# F50-plant boss-fight deploy sweep, 90 reports + gh-pages push (~12-15 min)
python3 /tmp/guardian_deploy.py

# Spell-cast audit (counts per spell + last monster killer)
timeout 1200 python3 /tmp/caster_audit.py

# Death cause audit (last killer + log tail per seed)
timeout 1200 python3 /tmp/death_audit.py
```

## Open questions for next session

1. Does the smart-policy `vendor_shop` branch buy non-resisted spells
   when stocked? Or does it always pick highest-base_power (i.e. it
   would grab Inferno over Mind Blast at the same level)?
2. Should the F25 plant tier list include at least one non-resisted
   L3 spell (Mind Blast or Earthquake) to give F30+ descenders a
   fighting chance against Fire/Lightning-resistant Mythic monsters?
3. The b411 boss-combat override applies to all monsters with
   `max_hp >= 500` (vault Tarrasques, Mythic bosses, plus the
   Guardian). Is the "skip Spectral Hand / Stone Skin recast" rule
   universally correct, or only for the Guardian's 1000-HP / multi-
   resist profile?
4. The F50 deploy reports show 90/90 victories — does the user want
   to see a "natural progression" sweep (F25 plant, 10000T, agents
   reach F50 organically) to confirm the quest can complete without
   the with_shards plant baseline?
