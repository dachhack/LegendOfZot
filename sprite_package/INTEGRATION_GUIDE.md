# Integration Guide

Step-by-step for wiring this entire sprite package into `dachhack/LegendOfZot`. Python (game logic, sprite_data) + JavaScript/HTML (front end).

This guide is written for Claude Code or another agent picking up the handoff. Steps are ordered so each one is verifiable before moving to the next — don't skip ahead.

---

## Step 0 — Orient

Before changing anything:

1. **Locate `wizardscavern/sprite_data.py`**. List every category-specific data structure it defines. Most likely you'll find:
   - `_WEAPON_MAP` or similar per-category dicts
   - `_ROOM_MAP` and `_VARIANT_MAP` for rooms
   - `_CUSTOM_ROOM_SPRITES` (base64-embedded G/fey_garden hand-drawn sprites) — **this constant goes away** once rooms are integrated.
2. **Find every consumer of those constants.** `grep -rn '_WEAPON_MAP\|_MONSTER_MAP\|_ROOM_MAP\|_CUSTOM_ROOM_SPRITES' wizardscavern/`. List all call sites. You'll update them in Step 4.
3. **Locate the canonical pool** (`canonical_pool_full.pkl`). Confirm it loads as a dict where each entry has `pid`, `cat`, `img_b64`, etc. The package ships an authoritative copy at the top level.
4. **Check the front-end**. `grep -rn 'sprite_data\|canonical_pool' frontend/` (or wherever JS/HTML lives). Sprite data may also be referenced from JS via a generated JSON.

---

## Step 1 — Build the canonical pool

In the split layout, the pool is **rebuilt from the assets bundle** rather than shipped pre-built. This keeps the repo small.

Prerequisite: the assets bundle must be unpacked at `assets/sprites/`. See README.md Step 1.

```bash
# Verify assets are in place
python3 fetch_assets.py
# Expected: ✓ in_game 1283 PNGs, ✓ reserve 3968 PNGs, all categories ✓

# Backup any existing pool
[ -f wizardscavern/data/canonical_pool_full.pkl ] && \
    cp wizardscavern/data/canonical_pool_full.pkl wizardscavern/data/canonical_pool_full.pkl.bak

# Build a fresh pool from this package
python3 code/promote_all_sprites.py \
    --pool /tmp/wc_pool_rebuild.pkl \
    --include-reserve

# Inspect the rebuild
python3 -c "
import pickle
p = pickle.load(open('/tmp/wc_pool_rebuild.pkl','rb'))
print(f'Total: {len(p)}')
from collections import Counter
print(Counter(e.get('cat','?') for e in p.values()))
"
# Expected: 5251 entries, 18 categories
```

Move the rebuilt pool into the repo when satisfied:

```bash
cp /tmp/wc_pool_rebuild.pkl wizardscavern/data/canonical_pool_full.pkl
```

The pool is a binary artifact — large for a repo but tractable. If you'd rather not commit it, generate it on first run via a setup script and gitignore the .pkl.

---

## Step 2 — Add round-8 source sheets to the repo

The 13 source sheets in `source_sheets/` need a stable home for the rooms slicer. Suggested location: `assets/sheets/round8/`.

```bash
mkdir -p assets/sheets/round8
cp source_sheets/*.png assets/sheets/round8/
```

The naming convention is `S8X_<original>.png` for S8A-S8I, and `S8X.png` (no suffix) for S8J/K/L/M.

**S8M is 1024×1024 with 64px native cells**. All other sheets are 2048×2048 with 128px native cells. The slicing code MUST consult `_SHEET_NATIVE_CELL` per sheet — hard-coding 128px will silently produce wrong slices for S8M.

---

## Step 3 — Replace per-category sprite_data

For each of the 18 categories, the package has `code/sprite_data_<cat>.py`. Each is a self-contained Python module exporting one of:

- **Named categories** (13): export `_<CAT>_MAP = {item_name: [(pid, variant_index), ...]}`
- **Generic categories** (4: characters, potions, scrolls, spells): export `_<CAT>_POOL = [pid, ...]`
- **Rooms**: exports `_SHEET_NATIVE_CELL`, `_ROOM_MAP`, `_VARIANT_MAP` (uses `(sheet, row, col)` tuples)

### Recommended structure

Replace the monolithic `wizardscavern/sprite_data.py` with a package directory:

```
wizardscavern/sprite_data/
    __init__.py             ← re-exports the per-category data + helpers
    weapons.py              ← from code/sprite_data_weapons.py
    monsters.py
    armors.py
    accessories.py
    bug_armors.py
    foods.py
    ingredients.py
    lanterns.py
    runes.py
    shards.py
    towels.py
    treasures.py
    trophies.py
    characters.py
    potions.py
    scrolls.py
    spells.py
    rooms.py
```

The `__init__.py` should:

```python
from .weapons     import _WEAPONS_MAP
from .armors      import _ARMORS_MAP
from .accessories import _ACCESSORIES_MAP
# ... etc
from .characters  import _CHARACTERS_POOL
from .potions     import _POTIONS_POOL
from .scrolls     import _SCROLLS_POOL
from .spells      import _SPELLS_POOL
from .rooms       import _ROOM_MAP, _VARIANT_MAP, _SHEET_NATIVE_CELL

# Helper used by the renderer
def get_named_variant(cat_map, item_name, seed):
    """Return (pid, variant_index) for an item, deterministic per seed."""
    variants = cat_map[item_name]
    if len(variants) == 1:
        return variants[0]
    idx = hash(seed) % len(variants)
    return variants[idx]

def get_generic_variant(cat_pool, seed):
    """Return a pid from a generic pool, deterministic per seed."""
    if len(cat_pool) == 1:
        return cat_pool[0]
    return cat_pool[hash(seed) % len(cat_pool)]
```

If the codebase prefers a flatter structure, dump everything into `wizardscavern/sprite_data.py` directly — same data, just one big file.

---

## Step 4 — Update consumers

Every `_X_MAP[item_name]` lookup that currently returns one sprite/tuple/pid now returns a **list**. Update consumers to pick a variant.

### Before

```python
sheet, row, col = _ROOM_MAP[room.code]
sprite = sheet.sprite_at(row, col)
```

### After

```python
variants = _ROOM_MAP[room.code]
seed = (room.floor, room.x, room.y)
sheet_id, row, col = variants[hash(seed) % len(variants)]
sprite = _SHEET_BY_ID[sheet_id].sprite_at(row, col, _SHEET_NATIVE_CELL[sheet_id])
```

For named non-rooms categories:

```python
variants = _WEAPONS_MAP[item_name]              # [(pid, variant_index), ...]
pid, variant_index = variants[hash(item_id) % len(variants)]
img_b64 = canonical_pool[pid]['img_b64']
```

For generic categories:

```python
pid = _CHARACTERS_POOL[hash(character_id) % len(_CHARACTERS_POOL)]
img_b64 = canonical_pool[pid]['img_b64']
```

The seed should be **stable** for a given game entity — use whatever ID the game already has for the entity (room, monster instance, character slot). If there's no stable ID, derive one from `(category, instance_index)` or similar.

---

## Step 5 — Remove `_CUSTOM_ROOM_SPRITES`

The old `sprite_data.py` had:

```python
_CUSTOM_ROOM_SPRITES = {'G': '<base64>', 'fey_garden': '<base64>'}
```

Both `G` (Garden) and `fey_garden` now have real sheet sprites in `_ROOM_MAP['G']` and `_VARIANT_MAP['fey_garden']`. **Delete the constant** and any code that consults it (likely `if code in _CUSTOM_ROOM_SPRITES: ...` branches).

---

## Step 6 — Update front-end sprite references

If JS/HTML loads sprites from a generated JSON or directly from the pool, regenerate that exported data after the pool is refreshed. Look for a script like `export_sprites_json.py` or similar in the repo's `tools/`. The new JSON should reflect the 5,251-sprite pool.

---

## Step 7 — Update ROOMS.md

Replace the repo's `ROOMS.md` with `picks_rooms/ROOMS.md` from this package:

```bash
cp picks_rooms/ROOMS.md ROOMS.md
git add ROOMS.md
```

The package `ROOMS.md` documents all 27 slots and their 3 variants each.

---

## Step 8 — Test in-game

Spin up the game and verify:

- [ ] Every monster type renders a sprite (no missing/blank)
- [ ] Same monster instance, re-rendered, shows the same variant (deterministic per seed)
- [ ] Different instances of the same monster type show variety across the dungeon
- [ ] Weapons, armors, foods, etc. all render correctly
- [ ] Generic categories (characters, potions, scrolls, spells) render with random-but-stable picks
- [ ] Rooms render with the right sprite per slot, including special variants (legendary chest, ancient pool, etc.)
- [ ] Garden (`G`) and Fey Garden (`fey_garden`) render correctly without `_CUSTOM_ROOM_SPRITES`

If anything looks wrong:
- Check `libraries/<cat>_library.json` for the canonical chosen list per category
- Check `in_game/by_item/<cat>/<item_name>/` to see what sprites the package thinks belong to that item
- Compare against the snippet in `code/sprite_data_<cat>.py`

---

## Step 9 — Commit

Suggested commit shape:

```
Replace sprite system with full 18-category package

- Refresh canonical_pool_full.pkl with 5251 sprites (1283 in-game + 3968 reserve)
- Replace sprite_data.py with per-category modules in sprite_data/
- Add 13 round-8 source sheets to assets/sheets/round8/ for room slicing
- Switch _<CAT>_MAP shape from single tuple to list-of-variants per item
- Renderer now picks deterministic variant via hash(seed) % len(variants)
- Remove _CUSTOM_ROOM_SPRITES (G and fey_garden use real sheet sprites)
- Update ROOMS.md
```

If the binary `canonical_pool_full.pkl` diff is too large to review, ship `canonical_pool_index.json` alongside it — it's a non-binary index of `pid → metadata` (no image bytes) so the diff is reviewable.

---

## Common gotchas

- **64px vs 128px**: S8M is 64px native. The slicing code MUST consult `_SHEET_NATIVE_CELL` per sheet — hard-coding 128 will silently produce nonsense for S8M cells.
- **PID stability**: don't rename pids. Every snippet, library, manifest, and the canonical pool all reference the same pids. Renaming one breaks all the others.
- **Sheet ID stability**: don't rename sheets either. PIDs in some categories embed the sheet ID (`S8A_r01c04` style for rooms reserve).
- **Reserve sprites are not "junk"** — they're "kept but not assigned to a slot/item". Visually approved. Treat them as a pre-vetted pool for future expansion.
- **Generic ≠ reserve**. Generic sprites ARE in-game (just dynamic, no item_name). Reserve sprites are NOT in-game. Don't conflate them.
- **Idempotent promotion**: re-running `promote_all_sprites.py` with the same package will overwrite existing entries with the same pids. Safe to re-run after fixes.
