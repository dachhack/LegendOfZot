"""
Sprite map for category: treasures

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _TREASURES_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 15
  total sprite variants: 44

Use: pick a deterministic variant per game-instance:
    variants = _TREASURES_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_TREASURES_MAP = {
    'Ancient Coin Collection': [
        ('LN0018', 0),  # sheet=LN1 src=r01c05
        ('LN0011', 1),  # sheet=LN1 src=r00c10
        ('LN0004', 2),  # sheet=LN1 src=r00c03
    ],
    'Carnyx of Doom': [
        ('TR0181', 0),  # sheet=TR2 src=r03c00
        ('TR0182', 1),  # sheet=TR2 src=r03c01
        ('TR0183', 2),  # sheet=TR2 src=r03c02
    ],
    'Chalice of Plenty': [
        ('TR0435', 0),  # sheet=TR4 src=r05c09
        ('TR0434', 1),  # sheet=TR4 src=r05c07
        ('TR0395', 2),  # sheet=TR3 src=r09c08
    ],
    'Crown of Kings': [
        ('TR0222', 0),  # sheet=TR2 src=r06c06
        ('TR0221', 1),  # sheet=TR2 src=r06c05
        ('TR0226', 2),  # sheet=TR2 src=r06c10
    ],
    'Diamond Brooch': [
        ('TR0551', 0),  # sheet=TR5 src=r07c03
        ('TR0568', 1),  # sheet=TR5 src=r08c08
        ('TR0552', 2),  # sheet=TR5 src=r07c04
    ],
    'Gold Coin Pouch': [
        ('LN0085', 0),  # sheet=LN1 src=r07c02
        ('LN0088', 1),  # sheet=LN1 src=r07c05
        ('LN0090', 2),  # sheet=LN1 src=r07c07
    ],
    'Hourglass of Ages': [
        ('TR0248', 0),  # sheet=TR2 src=r08c09
        ('TR0243', 1),  # sheet=TR2 src=r08c04
        ('TR0241', 2),  # sheet=TR2 src=r08c02
    ],
    "Merchant's Bell": [
        ('TR0208', 0),  # sheet=TR2 src=r05c04
        ('TR0212', 1),  # sheet=TR2 src=r05c08
        ('TR0211', 2),  # sheet=TR2 src=r05c07
    ],
    "Merchant's Horn": [
        ('TR0438', 0),  # sheet=TR4 src=r06c06
        ('TR0441', 1),  # sheet=TR4 src=r07c03
        ('TR0442', 2),  # sheet=TR4 src=r07c06
    ],
    'Mirror of Truth': [
        ('TR0255', 0),  # sheet=TR2 src=r09c04
        ('TR0256', 1),  # sheet=TR2 src=r09c05
        ('TR0253', 2),  # sheet=TR2 src=r09c02
    ],
    'Orb of Vitality': [
        ('CR0240', 0),  # sheet=CR2 src=r08c00
        ('CR0254', 1),  # sheet=CR2 src=r09c02
        ('CR0252', 2),  # sheet=CR2 src=r09c00
    ],
    'Ornate Goblet': [
        ('TR0350', 0),  # sheet=TR3 src=r05c11
        ('TR0337', 1),  # sheet=TR3 src=r04c08
        ('TR0334', 2),  # sheet=TR3 src=r04c04
    ],
    'Rhyton of Purity': [
        ('TR0449', 0),  # sheet=TR4 src=r08c06
        ('TR0452', 1),  # sheet=TR4 src=r08c09
        ('TR0453', 2),  # sheet=TR4 src=r08c10
    ],
    'Silver Necklace': [
        ('TR0522', 1),  # sheet=TR5 src=r04c10
        ('TR0492', 2),  # sheet=TR5 src=r02c02
    ],
    'Small Gem': [
        ('TR0163', 0),  # sheet=TR2 src=r01c06
        ('TR0164', 1),  # sheet=TR2 src=r01c07
        ('TR0165', 2),  # sheet=TR2 src=r01c08
    ],
}
