"""
Sprite map for category: bug_armors

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _BUG_ARMORS_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 5
  total sprite variants: 15

Use: pick a deterministic variant per game-instance:
    variants = _BUG_ARMORS_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_BUG_ARMORS_MAP = {
    'Chitin Shell': [
        ('BU0009', 0),  # sheet=BU1 src=r03c02
        ('BU0011', 1),  # sheet=BU1 src=r03c05
        ('BU0017', 2),  # sheet=BU1 src=r04c04
    ],
    'Moth Wing Cape': [
        ('BU0055', 0),  # sheet=BU3 src=r01c00
        ('BU0053', 1),  # sheet=BU3 src=r00c02
        ('BU0052', 2),  # sheet=BU3 src=r00c01
    ],
    'Pill Bug Plate': [
        ('BU0021', 0),  # sheet=BU1 src=r05c01
        ('BU0014', 1),  # sheet=BU1 src=r06c01
        ('BU0002', 2),  # sheet=BU1 src=r02c02
    ],
    'Royal Jelly Mail': [
        ('BU0032', 0),  # sheet=BU1 src=r06c07
        ('BU0041', 1),  # sheet=BU2 src=r01c01
        ('BU0043', 2),  # sheet=BU2 src=r01c03
    ],
    'Silk Weave': [
        ('BU0005', 0),  # sheet=BU1 src=r02c05
        ('BU0006', 1),  # sheet=BU1 src=r02c06
        ('BU0007', 2),  # sheet=BU1 src=r02c07
    ],
}
