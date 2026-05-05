"""
Sprite map for category: shards

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _SHARDS_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 8
  total sprite variants: 24

Use: pick a deterministic variant per game-instance:
    variants = _SHARDS_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_SHARDS_MAP = {
    'Battle': [
        ('SH0032', 0),  # sheet=GS1 src=r02c07
        ('SH0057', 1),  # sheet=GS1 src=r04c08
        ('SH0061', 2),  # sheet=GS1 src=r05c00
    ],
    'Devotion': [
        ('SH0035', 0),  # sheet=GS1 src=r02c10
        ('SH0064', 1),  # sheet=GS1 src=r05c03
        ('SH0083', 2),  # sheet=GS1 src=r06c10
    ],
    'Eternity': [
        ('SH0088', 0),  # sheet=GS1 src=r07c03
        ('SH0103', 1),  # sheet=GS1 src=r08c06
        ('SH0055', 2),  # sheet=GS1 src=r04c06
    ],
    'Growth': [
        ('SH0062', 0),  # sheet=GS1 src=r05c01
        ('SH0065', 1),  # sheet=GS1 src=r05c04
        ('SH0069', 2),  # sheet=GS1 src=r05c08
    ],
    'Knowledge': [
        ('SH0044', 0),  # sheet=GS1 src=r03c07
        ('SH0063', 1),  # sheet=GS1 src=r05c02
        ('SH0072', 2),  # sheet=GS1 src=r05c11
    ],
    'Reflection': [
        ('SH0077', 0),  # sheet=GS1 src=r06c04
        ('SH0047', 1),  # sheet=GS1 src=r03c10
        ('SH0066', 2),  # sheet=GS1 src=r05c05
    ],
    'Secrets': [
        ('SH0085', 0),  # sheet=GS1 src=r07c00
        ('SH0033', 1),  # sheet=GS1 src=r02c08
        ('SH0079', 2),  # sheet=GS1 src=r06c06
    ],
    'Treasure': [
        ('SH0034', 0),  # sheet=GS1 src=r02c09
        ('SH0059', 1),  # sheet=GS1 src=r04c10
        ('SH0058', 2),  # sheet=GS1 src=r04c09
    ],
}
