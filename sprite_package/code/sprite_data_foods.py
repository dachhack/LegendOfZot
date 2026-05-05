"""
Sprite map for category: foods

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _FOODS_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 26
  total sprite variants: 54

Use: pick a deterministic variant per game-instance:
    variants = _FOODS_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_FOODS_MAP = {
    'Andouille': [
        ('FD0642', 0),  # sheet=F5 src=r07c01
    ],
    'Boerewors': [
        ('FD0650', 0),  # sheet=F5 src=r06c07
    ],
    'Bratwurst': [
        ('FD0214', 0),  # sheet=F2 src=r10c05
    ],
    'Cheese Wedge': [
        ('FD0711', 0),  # sheet=F5 src=r00c00
        ('FD0740', 1),  # sheet=F5 src=r00c01
        ('FD0738', 2),  # sheet=F5 src=r00c02
    ],
    'Chorizo': [
        ('FD0685', 0),  # sheet=F5 src=r05c05
    ],
    'Cooking Kit': [
        ('FD0789', 0),  # sheet=F6 src=r05c06
    ],
    'Curing Kit': [
        ('FD0788', 0),  # sheet=F6 src=r05c08
    ],
    'Diablo Chorizo': [
        ('FD0732', 0),  # sheet=F5 src=r06c05
    ],
    'Dragonbreath Sausage': [
        ('FD0645', 0),  # sheet=F5 src=r06c03
    ],
    'Dried Mushrooms': [
        ('FD0722', 0),  # sheet=F5 src=r02c04
        ('FD0725', 1),  # sheet=F5 src=r02c05
        ('FD0727', 2),  # sheet=F5 src=r02c02
    ],
    'Hardtack': [
        ('FD0710', 0),  # sheet=F5 src=r03c08
        ('FD0676', 1),  # sheet=F5 src=r03c09
        ('FD0693', 2),  # sheet=F5 src=r04c06
    ],
    'Iron Rations': [
        ('FD0700', 0),  # sheet=F5 src=r04c02
    ],
    'Lembas Wafer': [
        ('FD0699', 0),  # sheet=F5 src=r03c06
    ],
    'Pepperwurst': [
        ('FD0643', 0),  # sheet=F5 src=r06c04
    ],
    'Rations': [
        ('FD0652', 0),  # sheet=F5 src=r04c03
    ],
    'Salted Jerky': [
        ('FD0726', 0),  # sheet=F5 src=r08c05
        ('FD0674', 1),  # sheet=F5 src=r04c09
        ('FD0672', 2),  # sheet=F5 src=r08c06
    ],
    'Travelers Bread': [
        ('FD0662', 0),  # sheet=F5 src=r04c01
        ('FD0666', 1),  # sheet=F5 src=r04c07
        ('FD0213', 2),  # sheet=F3 src=r06c01
    ],
    'burger': [
        ('FD0099', 0),  # sheet=F2 src=r11c09
        ('FD0145', 1),  # sheet=F2 src=r06c08
        ('FD0140', 2),  # sheet=F2 src=r07c08
    ],
    'chops': [
        ('FD0059', 0),  # sheet=F3 src=r00c08
        ('FD0081', 1),  # sheet=F3 src=r00c09
        ('FD0103', 2),  # sheet=F2 src=r10c13
    ],
    'cold cuts': [
        ('FD0076', 0),  # sheet=F2 src=r11c04
        ('FD0112', 1),  # sheet=F2 src=r09c06
        ('FD0110', 2),  # sheet=F2 src=r10c04
    ],
    'filet': [
        ('FD0150', 0),  # sheet=F3 src=r01c09
        ('FD0144', 1),  # sheet=F2 src=r11c12
        ('FD0141', 2),  # sheet=F2 src=r08c12
    ],
    'kebab': [
        ('FD0289', 0),  # sheet=F2 src=r07c01
        ('FD0273', 1),  # sheet=F2 src=r07c02
        ('FD0316', 2),  # sheet=F2 src=r09c01
    ],
    'nuggets': [
        ('FD0755', 0),  # sheet=F6 src=r03c08
        ('FD0782', 1),  # sheet=F6 src=r02c01
        ('FD0777', 2),  # sheet=F6 src=r02c02
    ],
    'roast': [
        ('FD0071', 0),  # sheet=F2 src=r08c06
        ('FD0127', 1),  # sheet=F2 src=r07c14
        ('FD0346', 2),  # sheet=F2 src=r09c15
    ],
    'skewer': [
        ('FD0357', 0),  # sheet=F2 src=r08c02
        ('FD0361', 1),  # sheet=F2 src=r09c00
        ('FD0362', 2),  # sheet=F2 src=r10c01
    ],
    'steak': [
        ('FD0129', 0),  # sheet=F2 src=r07c12
        ('FD0196', 1),  # sheet=F2 src=r09c13
        ('FD0199', 2),  # sheet=F2 src=r10c12
    ],
}
