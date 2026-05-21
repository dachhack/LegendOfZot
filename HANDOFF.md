# Session Handoff — F30-F50 Wall Broken at F25 Plant

**Date:** 2026-05-21
**Outgoing branch:** `claude/f25-plant-balance-sweep-ZQKaG` (b407 + b408)
**Incoming task:** Lift F25-F30 caster transition or polish the late-game wall.

---

## What just shipped (b407 + b408)

Two builds tuned F25-plant strength up until the deep dungeon became
reachable. Each build's full rationale lives in `wizardscavern/version.py`
CHANGELOG; the arc:

| Build | Change | Why |
|---|---|---|
| b407 | target_level N-2 → N+1, elixir N//5 → N//4, upg (N-1)//3 → (N-1)//2 | F25 plant L23 was under-levelled; smart-policy descent gate refused starter Dagger+Leather |
| b407 | Gear swap helper: F15+ Adamantine, F20+ Volcanic, F25+ Enchanted | Descent gate `(eq_w+eq_a) < (2z+3)` required base-tier swap, not just upgrade levels |
| b407 | Tier 6 inventory at F25+: Antidote x3, +3 Master Heals, +2 Restoration, +2 Teleport, 6 Bratwurst | Status-lockout deaths + 7000T food clock |
| b407 | base_max_health_bonus += (N-1)*5, base_max_mana_bonus += (N-1)*3 | Status-lockout killed casters in 2-3 swings at 290 HP; +120 HP buffer survives 4-5 swings |
| b407 | Bug fix: combat_mode wedge break 'x' → 'f' | Combat doesn't accept 'x' (combat.py:1271); elf seed=4 burned 2919T against a Werewolf |
| b407 | Bug fix: freeze_key includes mana | Casters buffing themselves no longer trip the wedge break |
| b408 | Add Meteor Strike (L3) + Inferno (L4) to F18+/F22+ memorize tiers | Damage spells were stuck at Flame Lance (33 base) which couldn't 1-shot F25 monsters |
| b408 | Spell-pick burst-nuke gate at priority 1b | Damage spells lived at position 6 behind 3 buff turns -- 70 of 6260 spell casts were L3+ before fix |

### F25-plant baseline (b406, 30 seeds, 1500T)

| Plant | Dwarf | Elf | Human | Max Depth |
|---|---|---|---|---|
| F25 | 3/30 (10%) | 10/30 (33%) | 3/30 (10%) | F35 dwarf |

### F25-plant final (b408, 30 seeds, 3000T)

| Plant | Dwarf | Elf | Human |
|---|---|---|---|
| F25 | 21/30 (70%) | 16/30 (53%) | 13/30 (43%) |

avg_max: dwarf F34.7, elf F31.1, human F29.9. max_max: F41, F39, F39.

### F25-plant deep sweep (b408, 15 seeds, 7000T)

| Plant | Dwarf | Elf | Human |
|---|---|---|---|
| F25 | 6/15 alive | 5/15 alive | 1/15 alive |
| avg max | F40.2 | F36.3 | F30.8 |
| max max | **F49 (cap)** | **F49 (cap)** | **F49 (cap)** |

**The F30-F50 wall is broken.** `MAX_FLOOR_Z = 49` is the dungeon
floor (game_systems.py:3034); dwarves AND elves consistently reach
F49 at 7000T. 4/6 alive dwarves at F49, 4/5 alive elves at F49,
1/1 alive human at F49. F30-F40 mid-game still claims some seeds,
but the deepest content is now accessible.

---

## What changed under the hood (key files)

- `wizardscavern/playtest_harness.py`:
  - `_plant_survivor_baseline` (line 794): stat/level/gear pumps
  - `_swap_plant_gear` (line 949): swaps base weapon+armor by tier
  - `_grant_memorized_spells` (line 977): adds Meteor Strike / Inferno
  - `_grant_survivor_inventory` (line 1057): adds Tier 6 (F25+) stash
  - `smart_policy` line 3209: combat_mode wedge break returns 'f'
  - `smart_policy` line 5790: burst-nuke gate for L3+ damage spells
  - `PlaytestSession.step` line 2947: freeze_key now includes mana
- `wizardscavern/version.py`: b408, CHANGELOG keeps 8 entries

---

## Next session task: lift the F25-F30 caster transition

The remaining death distribution at b408 (3000T, 30 seeds, F25 plant):

| Race | <F30 | F30-35 | F35-40 | F40+ |
|---|---|---|---|---|
| Dwarf (9 deaths) | 5 | 4 | 0 | 0 |
| Elf (14 deaths) | 14 | 0 | 0 | 0 |
| Human (17 deaths) | 14 | 3 | 0 | 0 |

**Casters who survive F30 reach F49.** The killer is the F25-F30
transition: 14/14 elf deaths and 14/17 human deaths happen below F30.
Diagnostic shows these are mostly status-lockout monsters:

- **Frost Worm**: 50-80 dmg/swing + freeze → 2-3 hits dead
- **Basilisk / Gorgon / Medusa**: paralysis/petrify lockout
- **Death Knight**: 90 dmg + burn ticks
- **Tarrasque**: vault defender, 102-125 dmg, no flee
- **Demilich**: 98 dmg + soul-trap drain
- **Vampire**: life-drain heal-back loops

### Possible next iterations

1. **Monster-identity flee gate.** Smart-policy currently uses
   `m_level > pc_level + 2` for threat. Add a name-based override:
   "frost worm", "basilisk", "gorgon", "medusa" → auto-flee when
   pc HP < 80%. Risk: humans/elves who'd rather kill them for XP
   would now skip every fight, slowing progression.

2. **Status resistance gear.** Add a Frostproof Cloak / Anti-
   Petrification Amulet to F25+ Tier 6 (similar pattern to b407's
   Enchanted Plate swap). Two slots: Hourglass Talisman already
   occupies one. Need to check accessory slot budget.

3. **Better cantrip damage.** At INT 26 elf, Mind Touch hits for
   18 dmg, Ice Shard 25 dmg. Both too low for status-locker
   monsters. A new tier-1 cantrip with ~40 dmg would let the elf
   burn down small monsters in 2 free cantrip casts (no channel).

4. **Bump caster HP further.** Current base_max_health_bonus pad
   is (N-1)*5 = +120 HP at F25. Going to +180 (N-1)*7.5 would let
   elves tank one extra status-lockout cycle. But the dwarf is
   already at 70% — risk of homogenizing the races.

5. **Pre-combat buff casting** (deferred from b407). In game_loop,
   when `nearest_monster_path` dist <= 3 AND Spectral Hand / Mage
   Armor not active → enter spell_casting_mode and pre-buff. Was
   designed but not implemented in b407 because numbers were
   already too high; now numbers are 53% elf and pre-buffing
   would lift them to ~65-70% by absorbing the first surprise hit.

### Suggested 1st move next session

Audit which monsters claim the F25-F30 elf deaths (use
`/tmp/death_audit.py` — already written). If 60%+ are name-listed
status-inflictors, option 1 (monster-identity flee gate) is the
highest-leverage change. Otherwise option 2 (status resistance
accessory) or option 5 (pre-combat buffing).

---

## Sweep harness commands

```bash
# Standard 3000T sweep, 30 seeds (~4-7 min)
timeout 1800 python3 /tmp/caster_sweep.py

# Deep 7000T sweep, 15 seeds (~10-15 min)
timeout 2400 python3 /tmp/caster_sweep_7k.py

# Death cause audit (last killer + log tail for 20 seeds)
timeout 1200 python3 /tmp/death_audit.py

# Spell-cast audit (per-spell cast counts + killers)
timeout 1200 python3 /tmp/caster_audit.py
```

## Key reference

- `MAX_FLOOR_Z = 49` (game_systems.py:3034, room_actions.py:4097)
- Descent gate: `weakly_geared_d = (eq_w + eq_a) < (2*z + 3)`
  at playtest_harness.py:6322. F25 needs 53; default Dagger+Leather
  max +20 each only reaches 47.
- Slot capacity: `int_ss = (INT-15)//2`, `lvl_ss = level-4 if INT>15`.
  F25 elf INT 26 L 26 = 27 slots; F25 human INT 20 L 26 = 24 slots.
- Burst-nuke trigger: `best_dmg.level >= 3 AND base_power * 2 >= monster.max_hp`
  at playtest_harness.py:5790. Meteor Strike 45*2=90 covers most
  F25 monsters; Inferno 55*2=110 covers tougher ones.

## Open questions for next session

1. Is the F25-F30 caster transition fixable with smart-policy
   monster-name flee, or does it need a fundamental damage / HP
   bump?
2. The dungeon cap is F49 -- should F25 plants be expected to
   "win" by reaching F49 alive, or is there a final boss / vault
   that ends the run?
3. Should the gear-swap helper extend to F30+ tiers (Abyssal,
   Void, Primordial)? Currently F25+ caps at Enchanted Longsword
   (+30 base, +20 upgrade); at F40+ monsters need higher dmg.
