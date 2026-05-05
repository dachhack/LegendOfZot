"""
Sprite map for category: runes

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _RUNES_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 8
  total sprite variants: 24

Use: pick a deterministic variant per game-instance:
    variants = _RUNES_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_RUNES_MAP = {
    'Battle': [
        ('RN0006', 0),  # sheet=RC1 src=r00c05
        ('RN0010', 1),  # sheet=RC1 src=r00c09
        ('RN0141', 2),  # sheet=RC2 src=r02c08
    ],
    'Devotion': [
        ('RN0030', 0),  # sheet=RC1 src=r02c05
        ('RN0129', 1),  # sheet=RC2 src=r01c08
        ('RN0146', 2),  # sheet=RC2 src=r03c01
    ],
    'Eternity': [
        ('RN0134', 0),  # sheet=RC2 src=r02c01
        ('RN0135', 1),  # sheet=RC2 src=r02c02
        ('RN0113', 2),  # sheet=RC2 src=r00c04
    ],
    'Growth': [
        ('RN0002', 0),  # sheet=RC1 src=r00c01
        ('RN0016', 1),  # sheet=RC1 src=r01c03
        ('RN0019', 2),  # sheet=RC1 src=r01c06
    ],
    'Knowledge': [
        ('RN0025', 0),  # sheet=RC1 src=r02c00
        ('RN0112', 1),  # sheet=RC2 src=r00c03
        ('RN0151', 2),  # sheet=RC2 src=r03c06
    ],
    'Reflection': [
        ('RN0027', 0),  # sheet=RC1 src=r02c02
        ('RN0005', 1),  # sheet=RC1 src=r00c04
        ('RN0123', 2),  # sheet=RC2 src=r01c02
    ],
    'Secrets': [
        ('RN0131', 0),  # sheet=RC2 src=r01c10
        ('RN0121', 1),  # sheet=RC2 src=r01c00
        ('RN0008', 2),  # sheet=RC1 src=r00c07
    ],
    'Treasure': [
        ('RN0133', 0),  # sheet=RC2 src=r02c00
        ('RN0001', 1),  # sheet=RC1 src=r00c00
        ('RN0116', 2),  # sheet=RC2 src=r00c07
    ],
}
