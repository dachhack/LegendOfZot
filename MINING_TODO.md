# Dwarf Mining — Finishing Checklist

Status of the dwarf-mining feature (ore veins → mine → ore/gems → Ioun
Stones) and what's left to call it *done*. Core mechanic is in and works
end-to-end; everything below is polish, balance, and verification.

## 1. Sprites (cosmetic — currently placeholder reuse)
- [ ] **Ore ingredients** (`sprites/ingredients.py`): Iron Chunk, Copper
      Nugget, Stone Shard, Silver Vein, Gold Flake, Coal Ember, Mithril
      Shard, Ruby Fragment, Diamond Chip, Adamantine Dust currently
      *reuse* in-pool gem/crystal pids (TR0163-165, CR0240/252/254,
      IN0261/0535, LN0085). They render, but aren't bespoke.
- [ ] **Ioun Stones** (`sprites/accessories.py`): Fortitude/Might/Agility/
      Mastery reuse the same gem/crystal pids. Want four distinct
      rhomboid/spindle "orbiting stone" sprites matching the lore colours
      (red / pale-blue / emerald / prismatic).
- [ ] Promote real art via the canonical-pool workflow in `CLAUDE.md`
      (drop PNGs in `assets/sprites/in_game/by_category/{ingredients,
      accessories}/`, rebuild pool, map the new pids). Reserve pool has
      gems/minerals — check `--include-reserve` before drawing new ones.
- [ ] Optional: a distinct **ore-vein wall tile** sprite for the map (the
      detected vein currently renders as an amber `%` glyph, not a sprite).

## 2. Mining limits / tuning (mechanic is in; numbers need a balance pass)
- [x] Per-floor cap enforced at **3** (`game_systems.MINE_LIMIT_PER_FLOOR`)
      — verified by direct test (locked out at 3 even with fresh adjacent
      veins) and per-floor independence.
- [ ] Decide whether 3/floor is the right number, or should scale (with
      depth? with a dwarf-mining skill/level? with a pickaxe item?).
- [ ] **Vein spawn rate**: currently ~70% of non-boss floors get one vein,
      ~25% of those get a second (`dungeon.py` add_floor). Confirm density
      feels right and isn't too sparse on early floors.
- [ ] **Drop rate / split**: 75% chance of loot per mine; of that, 70% ore
      ingredient (rarity-weighted) / 30% sellable gem → gold. Confirm
      these against the crafting economy.
- [ ] **Gem gold scaling**: `gem_value + (floor//5)*3`. Sanity-check vs
      vendor prices at depth.
- [ ] **Ore rarity weights** (`item_templates.MINING_INGREDIENTS`, 5th
      tuple field, sums to ~1.0): confirm Adamantine/Diamond stay rare
      enough that the top Ioun Stone is a real grind.

## 3. Recipes (4 Ioun Stones — review costs & power)
- [x] Dwarf-only gating works; recipes appear only for dwarves; ore is
      consumed correctly (ingredient `.count` fix landed alongside).
- [ ] Balance ingredient **costs** vs realistic ore drop rates — e.g.
      Mastery needs Ruby×2 + Diamond + Adamantine (all rare); confirm
      that's achievable but aspirational over a full run.
- [ ] Balance **stat bonuses** vs existing accessories in
      `characters._apply_accessory_bonuses` (Ioun numbers must stay in
      sync with the `passive_effect` display strings in
      `item_templates.DWARVEN_RECIPES`). Are they over/under-tuned next to
      Belt of the Giant, Champion's Signet, etc.?
- [ ] Consider whether the line should expand (mining tools, dwarven
      armor, a capstone unique) or stay at four stones.
- [ ] Confirm Ioun Stones sell/vendor sensibly and aren't trivially
      buyable elsewhere (should be a dwarf craft, not shop stock).

## 4. Playtest engagement (full loop wired; volume gated by survival + economy)
- [x] Harness drives mining: `m` → `mine_direction_mode` dispatch, shared
      `process_mine_action`, smart-policy intent (mines when adjacent to a
      vein, no monster next door), and `obs["mining"]`.
- [x] **Proactive vein-seeking**: `_mining_target_obs` BFS-paths to the
      nearest reachable floor tile adjacent to a known ore-vein wall;
      the policy detours there (safe BFS, skipped while wedged/oscillating,
      bounded by the per-floor cap). On surviving runs this works well
      (e.g. 15 mines, reached F12).
- [x] **Crafting**: `_pick_craftable_ioun` + inventory/game_loop triggers
      so a dwarf with enough ore crafts the highest-tier Ioun Stone.
- [x] **Equipping**: policy wears a crafted Ioun Stone (verified in
      isolation: opens inventory → `e<N>` → worn within ~2 steps, stats
      apply). Prioritised above food-crafting so it isn't starved.
- [x] Fixed a pre-existing dwarf **memorize-spell loop** (non-casters
      with a spell slot but `max_mana 0` looped `i→m→x` forever, burning
      ~half a dwarf run) — gated the memorize intent on `can_cast`. This
      was the single biggest drag on dwarf mining volume.
- [ ] **Volume is gated by two things, both balance, not harness:**
      (a) **Dwarf survival** — the policy pilots the melee dwarf poorly
      (≈1/15 runs alive at 4000T), so most runs die before mining much
      (aggregate ≈2 mines/run; healthy runs hit 15). (b) **Ore economy** —
      the cheapest Ioun Stone needs 4 specific commons (Iron×2+Copper×2)
      but ~2 mines/run × 75% drop × 70% ore ≈ 1 ore/run, so **0 Ioun
      Stones were crafted across 15 live runs** despite the path working.
      Tuning recipe costs / drop rates (§2, §3) is what unlocks the full
      loop in live runs.
- [ ] Add ore/Ioun-Stone counters to the playtest report
      (`playtest_report.py`) so balance runs surface mining volume.

## 5. Detection UX (works; could be richer)
- [x] Adjacent veins are sensed on move (dwarf only) → amber `%` on map +
      "m = mine" hint.
- [ ] Consider a wider "dwarven sense" radius (reveal veins within lantern
      range, not just orthogonally adjacent) so the player can plan routes
      to ore instead of stumbling onto it.

## 6. Loose ends / flags
- [ ] `ingredient_type='ore'` is a new label; nothing branches on it yet.
      Confirm it's fine everywhere meat/herb/fey types are special-cased.
- [x] **Pre-existing harness bug (fixed):** non-casters (dwarf, INT 8)
      fell into an inventory *memorize-spell* loop — fixed by gating the
      memorize intent on `can_cast`. Casters (elf/human) unaffected.
- [ ] **Pre-existing harness fragility (NOT mining):** the smart-policy
      gear-swap can oscillate between two similar non-broken weapons
      (`e1`↔`e2`), and the melee dwarf dies early on many seeds. Neither
      is caused by mining, but both cap how much a dwarf run mines.
