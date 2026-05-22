"""
wizardscavern.sprites — new sprite system (round-8 handoff).

This package replaces the monolithic `wizardscavern/sprite_data.py` with
per-category modules + a canonical pool of 5,251 sprites.

Layout
------
- One module per category (`weapons`, `monsters`, `armors`, ...) exporting
  either `_<CAT>_MAP` (named: item_name -> [(pid, variant_index), ...]) or
  `_<CAT>_POOL` (generic: list of pids).
- `rooms` is special — exports `_ROOM_MAP`, `_VARIANT_MAP`, `_SHEET_NATIVE_CELL`
  with `(sheet_id, row, col)` tuples instead of pids. Source sheets live in
  `assets/sheets/round8/`.
- The canonical pool is loaded lazily from
  `wizardscavern/data/canonical_pool_full.pkl` via `pool.get_image_b64(pid)`.

Usage
-----
    from wizardscavern.sprites import (
        weapons, monsters, accessories, ...,
        get_named_variant, get_generic_variant, get_image_b64,
    )

    pid, vi = get_named_variant(weapons._WEAPONS_MAP, 'Volcanic Blade', seed)
    img_b64 = get_image_b64(pid)
"""

from .pool import (
    get_image_b64,
    get_pool_entry,
    get_named_variant,
    get_generic_variant,
    pool_size,
)

# Re-export the per-category modules so callers can do
# `from wizardscavern.sprites import weapons` etc.
from . import (
    accessories,
    armors,
    bug_armors,
    bug_weapons,
    characters,
    foods,
    ingredients,
    lanterns,
    monsters,
    potions,
    rooms,
    runes,
    scrolls,
    shards,
    spells,
    towels,
    treasures,
    trophies,
    weapons,
)

__all__ = [
    'get_image_b64', 'get_pool_entry', 'get_named_variant',
    'get_generic_variant', 'pool_size',
    'accessories', 'armors', 'bug_armors', 'bug_weapons', 'characters', 'foods',
    'ingredients', 'lanterns', 'monsters', 'potions', 'rooms', 'runes',
    'scrolls', 'shards', 'spells', 'towels', 'treasures', 'trophies',
    'weapons',
]
