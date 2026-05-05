# Context — How we got here

This document captures session decisions and design choices so a fresh agent (Claude Code) can pick up the work without re-deriving everything.

> **Note on package shape**: This handoff is split into two bundles for GitHub friendliness:
>
> - **wc_sprites_repo** (this bundle, ~16 MB) — code, manifests, libraries, source sheets, docs. Goes in the repo.
> - **wc_sprites_assets** (~108 MB total, or 6 chunks ≤24 MB each) — sprite PNGs + picker tool. Hosted separately (GitHub Releases / S3 / Drive); downloaded once at setup; gitignored locally at `assets/sprites/`.
>
> The `canonical_pool_full.pkl` is **not** shipped pre-built — Claude Code rebuilds it via `code/promote_all_sprites.py --include-reserve` after the assets bundle is unpacked. This is documented in INTEGRATION_GUIDE.md Step 1.

## Project context

**Game**: Legend of Zot / Wizard's Cavern, a dungeon crawler in Python (game logic + sprite_data) with a JS/HTML front end. Repo: `dachhack/LegendOfZot` on GitHub.

**Sprite pipeline** (Sessions 6–8): The user has been building an asset pipeline that generates sprite sheets via Gemini, slices them, runs them through a picker UI, and promotes selected sprites into a canonical pool stored as `canonical_pool_full.pkl`. Categories built across multiple sessions.

## What this package contains

A complete sprite-asset deliverable for replacing every category's sprite data in the game:

### 18 categories, 5,251 sprites

- **17 pre-existing categories** from prior sessions (weapons, monsters, armors, accessories, bug_armors, foods, ingredients, lanterns, runes, shards, towels, treasures, trophies, characters, potions, scrolls, spells)
- **1 new category** from this session: **rooms** (27 slots × 3 variants = 81 named, plus 343 reserve)

### Three sprite states

Every sprite is in exactly one of three states:

1. **named** — chosen, has `game_data.item_name` mapping to a specific game item (e.g. "Volcanic Blade" v0). 1,032 total.
2. **generic** — chosen but no item_name; used dynamically (random character avatar, random potion appearance, etc.). 251 total.
3. **reserve** — kept-but-not-in-game; visually approved but not promoted. 3,968 total.

Per the user's direction: **named + generic go into the game**, **reserve goes into a separate part of the package** (and into the pool but with `status: 'reserve'`).

## Why the data shape changed

Each named category now uses an **item-name → list-of-variants** mapping rather than a flat list:

```python
_WEAPONS_MAP = {
    'Volcanic Blade': [('WP0006', 0)],            # 1 variant
    'Battle Axe':     [('WP0340', 0), ('WP0284', 1), ('WP0232', 2)],   # 3 variants
    ...
}
```

The renderer picks a deterministic variant per game instance:

```python
variants = _WEAPONS_MAP[item_name]
pid, vi = variants[hash(seed) % len(variants)]
img_b64 = canonical_pool[pid]['img_b64']
```

Same item, same seed, same sprite — but different game instances see different variants, so the dungeon doesn't look like a copy-paste.

Generic categories (characters, potions, scrolls, spells) use a flat pid list:

```python
_CHARACTERS_POOL = ['CH0008', 'CH0009', 'CH0010', ...]   # 73 entries
```

…because there's no item_name to key by.

Rooms is special — uses `(sheet_id, row, col)` tuples instead of pids, because rooms are sliced from source sheets at game-load time rather than pre-rendered into the pool. See `code/sprite_data_rooms.py` for details.

## What was done in this session

### 1. Built the rooms picker

A 2-pass picker UI (junk filter → slot assignment) was developed and run against 13 source sheets (S8A–S8M). The picker is in `picker/room_picker.html` — single-file, mobile-friendly, with import/export and auto-migration from older versions.

Final picks: **434 kept (81 assigned + 343 reserve), all 27 slots at 3/3**.

### 2. Generated per-category sprite_data snippets

For all 18 categories, generated a `sprite_data_<cat>.py` module documenting the named-or-generic mapping. These replace whatever `_<CAT>_MAP` / `_<CAT>_POOL` constants currently exist in `wizardscavern/sprite_data.py`.

### 3. Refreshed and verified the libraries

The user requested re-deriving stale libraries from the canonical pool. Investigation showed all 17 pre-existing libraries are actually already in sync with the pool (no staleness; my initial read was wrong). All 4,827 pool sprites are tracked in libraries. The rooms category got a fresh library generated. The 18 libraries in `libraries/` are authoritative.

### 4. Built the unified promotion script

`code/promote_all_sprites.py` is a single entry point that:
- Reads each category's `sprite_data_<cat>.py` snippet
- Looks up each pid in `in_game/by_category/<cat>/`
- Writes everything (image + game_data + status) into the canonical pool
- Optionally promotes reserve sprites too (`--include-reserve`)
- Idempotent: re-running overwrites existing entries
- Dry-run flag for safety

Verified end-to-end: against an empty pool, dry-run promotes 1,283 in-game (or 5,251 with reserve) cleanly.

## Design decisions and trade-offs

### Why `by_item/` is the primary view

`in_game/by_item/<cat>/<item_name>/v<n>.png` mirrors the renderer's mental model — given an item name, get its variants. The `by_category/` directory is for direct PID lookup but is just a flat dump.

### Sprite size & format

Every sprite is 96×96 PNG (RGBA). The pool stores them as base64 webp at quality 80 (smaller than PNG; ~9 KB average). The promotion script re-encodes PNG → webp on the way into the pool to match existing pool conventions.

### Sheet ID vs sheet object

`sprite_data_*.py` snippets use **sheet ID strings** (`'WP0006'`, `'S8A'`, etc.) and pid references — not module-level sheet objects. The renderer needs a `_SHEET_BY_ID` dict (or similar) to resolve string → sheet at render time.

### Rooms is special

Rooms sprites are not pre-rendered into the canonical pool by default — they're sliced from `source_sheets/` at promotion time. This keeps the package leaner (the 13 source sheets + the slicing logic, instead of 81 baked PNGs) and makes it easy to re-pick later. The rooms PNGs in `in_game/by_category/rooms/` are the same sprites pre-rendered for visual reference; the promotion script re-slices from sheets.

### Sheet S8M is 64px native, all others are 128px

The rooms snippet has a `_SHEET_NATIVE_CELL` dict that the renderer must consult per-sheet. Hard-coding 128px for all sheets will produce wrong slices for S8M.

### War Room (K) is a known-mixed pick

Of the 3 K-slot variants: 1 is crossed swords (good "war room" feel), 2 are weapon racks (more "armory"). The user flagged this as acceptable but possibly worth swapping later. Reserve sprites in `reserve/rooms/` include several "war table with miniatures" candidates that would fit better — see `picks_rooms/preview_all_picks.png` for the current picks.

## What's NOT in this package (and why)

- **No game-side renderer code** — that lives in the user's repo. `INTEGRATION_GUIDE.md` describes the change pattern but doesn't include actual game source.
- **No PR/branch automation** — the user manages the GitHub repo directly. Integration is meant to be reviewed before commit.
- **No test fixtures** — the verification steps use the unified promotion script's dry-run mode.

## Picker future-use notes

If picks need to be revisited:
- Open `picker/room_picker.html` in any browser
- Tap **Import JSON** and load `picks_rooms/room_picks.json` to restore current state
- Make changes (re-trash, re-assign)
- Tap **Export JSON** → **📋 Copy to clipboard** → paste into a chat
- Re-run the apply step with the new picks JSON

The picker auto-migrates from older storage keys (`wc_room_picker_v1`, `v2`) to `v3` on first load. Slim export shape (v2): 7-8 KB instead of 90 KB.

## Conventions used throughout

- **PID format**:
  - Pre-existing categories: `WP0006`, `MN3760`, `AC0016`, etc. — first 1-2 letters denote category, digits are the sequence number in the original sheet ordering.
  - Rooms: `RM####` for assigned, `RES####` for reserve.
- **Sheet IDs**: stable across the pipeline. Don't rename — embedded in pids and used by sprite_data_rooms.py.
- **Output sprite size**: 96×96 PNG (or webp inside the pool).
- **Library shape**: `chosen[]` and `reserve[]` lists; chosen items have `game_data` populated, reserve items don't.
