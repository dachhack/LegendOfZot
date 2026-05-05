"""
Sprite map for category: lanterns

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _LANTERNS_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 2
  total sprite variants: 4

Use: pick a deterministic variant per game-instance:
    variants = _LANTERNS_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_LANTERNS_MAP = {
    'Lantern': [
        ('CR0108', 0),  # sheet=CR1 src=r09c00
        ('CR0116', 1),  # sheet=CR1 src=r09c08
        ('CR0114', 2),  # sheet=CR1 src=r09c06
    ],
    'Lantern Fuel': [
        ('LF0080', 0),  # sheet=LF1 src=r06c07
    ],
}
