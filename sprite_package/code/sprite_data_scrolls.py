"""
Sprite pool for category: scrolls (generic — no item_name mapping)

Generated from scrolls_library.json + canonical_pool_full.pkl.

Shape: _SCROLLS_POOL is a list of pids ordered by variant_index.
These sprites are used dynamically (e.g. character creator picks one,
potion identification rolls a random sprite, etc.). They are NOT tied
to specific item names.

Stats:
  total sprites: 42

Use:
    pid = _SCROLLS_POOL[index]                # if you want a specific one
    pid = random.choice(_SCROLLS_POOL)        # if assignment is random
    img = canonical_pool[pid]["img_b64"]
"""

_SCROLLS_POOL = [
    'S040',  # variant_index=0 sheet= src=S6 E15
    'S085',  # variant_index=0 sheet=NS7 src=NS7 B3
    'S086',  # variant_index=0 sheet=NS6 src=NS6 A3
    'S087',  # variant_index=0 sheet=NS3 src=NS3 A4
    'S088',  # variant_index=0 sheet=NS1 src=NS1 A4
    'S089',  # variant_index=0 sheet=NS1 src=NS1 C3
    'S090',  # variant_index=0 sheet=NS4 src=NS4 C2
    'S091',  # variant_index=0 sheet=NS6 src=NS6 C1
    'S092',  # variant_index=0 sheet=NS1 src=NS1 A2
    'S093',  # variant_index=0 sheet=NS1 src=NS1 C2
    'S094',  # variant_index=0 sheet=NS4 src=NS4 A4
    'S095',  # variant_index=0 sheet=NS1 src=NS1 B1
    'S096',  # variant_index=0 sheet=NS1 src=NS1 C1
    'S097',  # variant_index=0 sheet=NS7 src=NS7 C3
    'S098',  # variant_index=0 sheet=NS6 src=NS6 C2
    'S099',  # variant_index=0 sheet=NS7 src=NS7 A2
    'S100',  # variant_index=0 sheet=NS1 src=NS1 A1
    'S101',  # variant_index=0 sheet=NS7 src=NS7 A4
    'S102',  # variant_index=0 sheet=NS4 src=NS4 B2
    'S103',  # variant_index=0 sheet=NS3 src=NS3 D3
    'S104',  # variant_index=0 sheet=NS6 src=NS6 A1
    'S105',  # variant_index=0 sheet=NS3 src=NS3 C3
    'S106',  # variant_index=0 sheet=NS7 src=NS7 B1
    'S107',  # variant_index=0 sheet=NS3 src=NS3 C2
    'S108',  # variant_index=0 sheet=NS3 src=NS3 A1
    'S109',  # variant_index=0 sheet=NS7 src=NS7 C4
    'S110',  # variant_index=0 sheet=NS6 src=NS6 B1
    'S111',  # variant_index=0 sheet=NS3 src=NS3 A2
    'S112',  # variant_index=0 sheet=NS7 src=NS7 A1
    'S113',  # variant_index=0 sheet=NS7 src=NS7 C2
    'S114',  # variant_index=0 sheet=NS4 src=NS4 B4
    'S115',  # variant_index=0 sheet=NS6 src=NS6 C3
    'S116',  # variant_index=0 sheet=NS6 src=NS6 B2
    'S117',  # variant_index=0 sheet=NS7 src=NS7 A3
    'S118',  # variant_index=0 sheet=NS4 src=NS4 A3
    'S119',  # variant_index=0 sheet=NS6 src=NS6 A2
    'S120',  # variant_index=0 sheet=NS4 src=NS4 C3
    'S121',  # variant_index=0 sheet=NS7 src=NS7 B4
    'S122',  # variant_index=0 sheet=NS7 src=NS7 B2
    'S123',  # variant_index=0 sheet=NS6 src=NS6 B3
    'S124',  # variant_index=0 sheet=NS4 src=NS4 B1
    'S125',  # variant_index=0 sheet=3646.png src=3646.png C1 (unidentified scroll)
]
