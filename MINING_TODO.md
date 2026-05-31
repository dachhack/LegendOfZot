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

## 2. Mining limits / tuning (economy checked — healthy)
- [x] **Per-floor cap REMOVED.** A vein is a finite 5-10 tile worm and
      mining one tile opens the next for tunnelling, so the vein's length
      is the natural per-floor limit — no artificial cap.
      `gs.dwarf_mines_per_floor` is kept only as a stat counter.
- [x] **Economy measured** (drop-table model over deep ~17-vein runs +
      20 live no-fog dwarf runs). Removing the cap took live mining from
      ~2 → ~10 attempts/run and Ioun-Stone crafts from 0 → 14 across 20
      runs (7 worn). Curve is good: ~13 of each common, 5-8 uncommon,
      0.7-2.6 rare per deep run.
- [ ] **Vein spawn rate**: ~70% of non-boss floors get one vein, ~25% of
      those get a second (`dungeon.py` add_floor). Density feels fine;
      revisit if early floors seem sparse.
- [ ] **Drop rate / split** (75% loot/mine; 70% ore / 30% gem) and **gem
      gold scaling** (`gem_value + (floor//5)*3`, ~547 gold/deep-run) look
      reasonable; leave unless a depth sweep says otherwise.
- [x] **Ore rarity weights** verified: Adamantine (0.01) / Diamond (0.02)
      stay rare enough that Mastery is craftable in only ~21% of deep
      runs — appropriately aspirational.

## 3. Recipes (4 Ioun Stones — costs validated, power still TBD)
- [x] Dwarf-only gating works; recipes appear only for dwarves; ore is
      consumed correctly (ingredient `.count` fix landed alongside).
- [x] Ingredient **costs validated against measured drop rates**: the
      three cheap stones (Fortitude/Might/Agility) are readily craftable
      on a deep run (~92-99%); Mastery (Ruby×2 + Diamond + Adamantine) is
      a real grind (~21%). Good entry-to-capstone curve.
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
- [x] **Full loop now fires in live runs** after removing the per-floor
      cap (§2): 20 no-fog dwarf runs went from ~2 → ~10 mine attempts/run
      and **0 → 14 Ioun Stones crafted (7 worn)**. The cap was the blocker.
- [ ] **Remaining limiter is dwarf survival** (≈0/20 alive at 4000T, avg
      depth ~F3) — the policy pilots the melee dwarf poorly, so most runs
      die shallow. Not a mining issue; better dwarf combat/descent piloting
      would lift mining volume further. (See §6.)
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
