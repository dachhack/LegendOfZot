# Session Handoff — Caster Sweep Complete, Next: F25 Plant with Stronger Stats

**Date:** 2026-05-21  
**Outgoing branch:** `claude/fix-tomb-elite-cap-YnjrE` (b391 → b406, ten builds)  
**Incoming task:** Repeat the playtest/balance sweep at F25 plant with stronger starting characters to probe F30-F50 content.

---

## What just shipped (b391 → b406)

Ten coordinated builds turned casters from "0% F25 survival" into a viable late-game archetype. Each build's full rationale is in `wizardscavern/version.py` CHANGELOG, but the arc:

| Build | Change | Why |
|---|---|---|
| b391/b393 | Hard cap tomb_elite at F5+ | F2-F5 elite Wraith one-shots |
| b394 | `--start-floor N` plant baseline | Iterate deep without 4000T waits |
| b395 | Wedge-break / oscillation detector | 9/90 wedged runs at b394 |
| b396 | Survivor inventory grants | Plants arrived consumable-bare |
| b397 | Stat-elixir pad + pre-memorized utility spells | Plants arrived spell-bare |
| b398 | Power-aware spell pick + pre-fight Stone Skin | Smart-policy ignored Lightning Bolt |
| b399 | Race+INT mana regen (elf 1/2, human 1/3, dwarf 1/5) | Casters bled mana between fights |
| b400 | Additive INT-scaling on spell damage | Cantrips didn't scale with stat investment |
| b401 | Prey-filter on Stone Skin trigger | Wasted buff on short fights |
| b402 | INT-scaled Quick Cast (skip channel-init swing) | F25 elf died mid-cast 50% of deaths |
| b403 | Hold Monster fix + DEX concentration + Mage Armor + Spectral Hand + Hourglass Talisman | Defensive suite |
| b404 | Spell priority rewrite + monster obs in spell_casting_mode | b403 features never fired |
| b405 | Spectral Hand 3→1 absorb, Mage Armor +6→+4 DEF | b404 over-corrected (80% F25 survival) |
| b406 | Hold Monster duration 2→1 | Final balance pass |

### Final balance numbers (1500T sweep, 30 seeds each)

| Plant | Dwarf | Elf | Human |
|---|---|---|---|
| F15 | 20% | 23% | 30% |
| F20 | 10% | 17% | 7% |
| F25 | 27% | 20% | 20% |

Race niche distribution: **Human strongest at F15** (balanced stats), **Elf strongest at F20** (mid-tier caster prime), **Dwarf strongest at F25** (deep-floor tank). Each race has a survival sweet spot.

### Final balance numbers (7000T sweep, 15 seeds each)

| Plant | Dwarf | Elf | Human | Max Depth |
|---|---|---|---|---|
| F15 | 0/15 | 0/15 | 1/15 | F35 (human) |
| F20 | 0/15 | 1/15 | 0/15 | F28 (dwarf) |
| F25 | 1/15 | 2/15 | 2/15 | F33 (dwarf) |

Long-form (5% overall) is much harder than short-form (20-30%). **F25 caster wall is broken; F30+ wall is the next frontier.** F25 elf max depth = F26 (they survive but don't push). F25 dwarf max depth = F33 (the real deep-game runner).

---

## Next session task: F25-plant playtest with stronger starting players

The user's directive: "Repeat the playtesters but seeds at floor 25 this time. Same process we just went through but deeper with stronger starting players."

**Interpretation:** We've broken the F25 wall; now turn the dial up. Plant characters with stronger profiles (more stats, more gear, more memorized spells) at F25, then run them with 5000-7000T budgets, and see which floor becomes the new wall (F30? F35? F40?). Iterate balance changes against the new wall.

### Concrete starting point

1. **Beef up `_plant_survivor_baseline` for F25+ plants:**
   - Currently grants `(level*5)**2 + 1` XP where `level = max(1, N-2)`. F25 plant → L23 character. Bump to L26-28 (target L=N+1 or N+2).
   - Stat-elixir pad: +1 per 5 floors. At F25 → +5 to each stat. Consider F25+ getting +6 or +7.
   - Equipment upgrades: weapon/armor `+(N-1)//3`. F25 → +8. Could bump to +10 at F25+.

2. **F25-plant sweep harness:**
   - `/tmp/caster_sweep_7k.py` is the existing 7000T template. Trim to just F25 plant, all races, 30 seeds, 5000-7000T.
   - Expect ~2-4 min per sweep at this size.

3. **Audit script for deep diagnostics:**
   - `/tmp/caster_audit.py` tracks Hold Monster cast rate, Spectral Hand uptime, Mage Armor uptime, Quick Cast triggers. Reuse it.
   - Add: track final floor reached, deaths by depth, death cause (last monster type / mode).

4. **Likely investigation areas (predicting the F30+ wall):**
   - **Food clock** — at 7000T, hunger ticks ~1400 times. Stronger plants need more food OR longer-lasting sausages.
   - **Item replenishment** — F25 plant inventory runs out by F30. Magic Shoppes are rare past F30; need a deep-floor refresh mechanic.
   - **Monster scaling** — at F40+ monsters have base_health + 600. Spell damage caps at ~80 raw. Need stronger damage or pierce mechanics.
   - **Mana decay even with b399 regen** — high-INT casters at F35+ deplete mana faster than they regen.

### What NOT to repeat from this session

- **Don't fight the priority cascade again.** The b404 fix already wired the `spell_casting_mode` priority correctly. New defensive spells should fit into the existing order (Hold Monster → Spectral Hand → Mage Armor → Stone Skin → Heal → Damage).
- **Don't auto-grant items in plant baseline.** Hourglass Talisman is in `UNIQUE_TREASURE_TEMPLATES` and drops via the 10% chest path. Any new accessory should follow that pattern, not the failed b403 auto-equip pattern.
- **Don't break the dwarf identity.** The b405/b406 nerf restored dwarf as deep-floor tank. New caster features should not push them below dwarf survivability.

---

## Key files to know

- `wizardscavern/playtest_harness.py` — `_plant_survivor_baseline`, `_grant_memorized_spells`, `_grant_survivor_inventory`, `smart_policy` (3000+ line dispatcher)
- `wizardscavern/combat.py` — `_execute_charged_spell`, `process_combat_action`, `process_spell_casting_action`, `concentration_check`, `get_spell_charge_turns`
- `wizardscavern/characters.py` — `Character.cast_spell`, `take_damage`, `max_mana` property, `add_status_effect`
- `wizardscavern/items.py` — `SPELL_TEMPLATES` (1500+ entries), `process_mana_regen`
- `wizardscavern/item_templates.py` — `UNIQUE_TREASURE_TEMPLATES` (built lazily), `ENHANCED_MINOR_TREASURES`
- `wizardscavern/version.py` — `CHANGELOG` (keep <8 entries, drop oldest)

## Caster mechanic reference

- **Spell channeling**: L2-L3 spells take 1 channel turn + 1 fire turn (2 monster swings). L4-L5 take 2+1=3. L0-L1 are instant (1 swing).
- **Quick Cast**: `(INT - 17) * 4%` chance to skip channel-init swing, capped 75%, +cast_speed_bonus from Hourglass Talisman.
- **Concentration check**: d20 + INT//4 + DEX//4 vs DC = max(5, dmg_taken // 2). Pass = channel continues, fail = mana lost.
- **Hold Monster**: 1 MP, 1-turn freeze, monster's reactive swing (post-cast) skipped. Doesn't cover next-spell channel-init (duration too short by design after b406).
- **Mage Armor + Stone Skin stack**: Different `status_effect_name`, both apply `defense_boost` magnitude. +4 + +8 = +12 DEF when both up.

## Sweep harness commands

```bash
# Short sweep, 1500T, 30 seeds (~7 min)
timeout 1500 python3 /tmp/caster_sweep.py

# Long sweep, 7000T, 15 seeds (~5-6 min)
timeout 1800 python3 /tmp/caster_sweep_7k.py

# Deep audit (Hold Monster usage, buff uptime, quick-cast rate) ~10-15 min
timeout 900 python3 /tmp/caster_audit.py
```

## Pre-combat buff casting (deferred but designed)

The user asked about it; I designed but didn't implement. The plan:

In `smart_policy` game_loop branch, when `nearest_monster_path` distance ≤ 3 AND Spectral Hand / Mage Armor not active → fire `c` to enter spell_casting_mode and pre-buff. Would push F25 survival from 20% → ~30-40% but might over-tune again. Keep in reserve for the F25+ playtest if survival drops too low.

---

## Open questions for next session

1. Is +5 stat pad enough at F25 plant, or should it scale steeper (e.g. +1 per 4 floors)?
2. Should the F25 plant inventory tier add a Master Mana Potion stack to push casters past the F30 mana wall?
3. Should new spells get dedicated sprites (Mage Armor / Spectral Hand currently share Divine Shield / Stone Skin pids)? Pool has 49 named-mapped pids; canonical has 1283 available.
4. Is the b406 1500T F25 distribution (27/20/20) close enough to "balanced" or should casters get bumped back up?
