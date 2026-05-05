"""
Sprite map for category: towels

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _TOWELS_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 1
  total sprite variants: 3

Use: pick a deterministic variant per game-instance:
    variants = _TOWELS_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_TOWELS_MAP = {
    'Towel': [
        ('LN0153', 0),  # sheet=LN2 src=r00c10
        ('LN0175', 1),  # sheet=LN2 src=r02c08
        ('LN0177', 2),  # sheet=LN2 src=r02c10
    ],
}
