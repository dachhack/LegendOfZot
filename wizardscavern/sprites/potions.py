"""
Sprite pool for category: potions (generic — no item_name mapping)

Generated from potions_library.json + canonical_pool_full.pkl.

Shape: _POTIONS_POOL is a list of pids ordered by variant_index.
These sprites are used dynamically (e.g. character creator picks one,
potion identification rolls a random sprite, etc.). They are NOT tied
to specific item names.

Stats:
  total sprites: 93

Use:
    pid = _POTIONS_POOL[index]                # if you want a specific one
    pid = random.choice(_POTIONS_POOL)        # if assignment is random
    img = canonical_pool[pid]["img_b64"]
"""

_POTIONS_POOL = [
    'P002',  # variant_index=0 sheet= src=NEW1 A2 (promoted from reserve b440)
    'P006',  # variant_index=0 sheet= src=NEW1 A7 (promoted from reserve b440)
    'P013',  # variant_index=0 sheet= src=NEW1 B2 (promoted from reserve b440)
    'P018',  # variant_index=0 sheet= src=NEW1 B7 (promoted from reserve b440)
    'P021',  # variant_index=0 sheet= src=NEW1 B10 (promoted from reserve b440)
    'P031',  # variant_index=0 sheet= src=NEW2 C9
    'P034',  # variant_index=0 sheet= src=NEW4 C12
    'P037',  # variant_index=0 sheet= src=NEW2 D3
    'P041',  # variant_index=0 sheet= src=NEW4 D7
    'P044',  # variant_index=0 sheet= src=NEW4 D10
    'P050',  # variant_index=0 sheet= src=NEW2 E8
    'P052',  # variant_index=0 sheet= src=NEW4 E10
    'P053',  # variant_index=0 sheet= src=NEW4 E11
    'P054',  # variant_index=0 sheet= src=NEW4 E12
    'P056',  # variant_index=0 sheet= src=NEW2 H2
    'P059',  # variant_index=0 sheet= src=NEW4 F6
    'P060',  # variant_index=0 sheet= src=NEW2 F7
    'P061',  # variant_index=0 sheet= src=NEW2 C4
    'P062',  # variant_index=0 sheet= src=NEW4 F11
    'P063',  # variant_index=0 sheet= src=NEW2 G1
    'P064',  # variant_index=0 sheet= src=NEW4 G2
    'P065',  # variant_index=0 sheet= src=NEW2 G3
    'P066',  # variant_index=0 sheet= src=NEW4 G4
    'P067',  # variant_index=0 sheet= src=NEW4 G5
    'P068',  # variant_index=0 sheet= src=NEW4 G6
    'P069',  # variant_index=0 sheet= src=NEW4 G7
    'P070',  # variant_index=0 sheet= src=NEW4 G8
    'P074',  # variant_index=0 sheet= src=NEW4 H1
    'P075',  # variant_index=0 sheet= src=NEW4 H2
    'P076',  # variant_index=0 sheet= src=NEW2 H3
    'P077',  # variant_index=0 sheet= src=NEW2 H5
    'P080',  # variant_index=0 sheet= src=NEW4 H8
    'P081',  # variant_index=0 sheet= src=NEW2 H9
    'P093',  # variant_index=0 sheet= src=NEW2 A9
    'P097',  # variant_index=0 sheet= src=NEW2 B3
    'P098',  # variant_index=0 sheet= src=NEW2 B4
    'P099',  # variant_index=0 sheet= src=NEW2 B5
    'P102',  # variant_index=0 sheet= src=NEW2 B8
    'P103',  # variant_index=0 sheet= src=NEW2 B11
    'P104',  # variant_index=0 sheet= src=NEW2 B12 (promoted from reserve b440)
    'P107',  # variant_index=0 sheet= src=NEW4 C6
    'P108',  # variant_index=0 sheet= src=NEW4 C7
    'P111',  # variant_index=0 sheet= src=NEW4 D4
    'P114',  # variant_index=0 sheet= src=NEW4 D12
    'P115',  # variant_index=0 sheet= src=NEW2 F5
    'P118',  # variant_index=0 sheet= src=NEW2 G10
    'P119',  # variant_index=0 sheet= src=NEW2 H4
    'P120',  # variant_index=0 sheet= src=NEW3 A1
    'P121',  # variant_index=0 sheet= src=NEW3 A2
    'P123',  # variant_index=0 sheet= src=NEW3 A4
    'P124',  # variant_index=0 sheet= src=NEW3 B1
    'P125',  # variant_index=0 sheet= src=NEW3 B2
    'P126',  # variant_index=0 sheet= src=NEW3 B3
    'P127',  # variant_index=0 sheet= src=NEW3 B4
    'P128',  # variant_index=0 sheet= src=NEW3 C1
    'P131',  # variant_index=0 sheet= src=NEW3 D2
    'P132',  # variant_index=0 sheet= src=NEW3 D3
    'P134',  # variant_index=0 sheet= src=NEW4 A1
    'P140',  # variant_index=0 sheet= src=NEW4 A8
    'P142',  # variant_index=0 sheet= src=NEW4 A10
    'P143',  # variant_index=0 sheet= src=NEW4 A11
    'P144',  # variant_index=0 sheet= src=NEW4 A12
    'P145',  # variant_index=0 sheet= src=NEW4 B1
    'P147',  # variant_index=0 sheet= src=NEW4 B3
    'P148',  # variant_index=0 sheet= src=NEW4 B4
    'P149',  # variant_index=0 sheet= src=NEW4 B5
    'P150',  # variant_index=0 sheet= src=NEW4 B6
    'P151',  # variant_index=0 sheet= src=NEW4 B7
    'P152',  # variant_index=0 sheet= src=NEW4 B9
    'P153',  # variant_index=0 sheet= src=NEW4 B10
    'P154',  # variant_index=0 sheet= src=NEW4 B11
    'P155',  # variant_index=0 sheet= src=NEW4 C1
    'P156',  # variant_index=0 sheet= src=NEW4 C2
    'P157',  # variant_index=0 sheet= src=NEW4 C5
    'P158',  # variant_index=0 sheet= src=NEW4 C11
    'P159',  # variant_index=0 sheet= src=NEW4 D1
    'P160',  # variant_index=0 sheet= src=NEW4 D2
    'P161',  # variant_index=0 sheet= src=NEW4 D5
    'P162',  # variant_index=0 sheet= src=NEW4 D6
    'P163',  # variant_index=0 sheet= src=NEW4 D8
    'P165',  # variant_index=0 sheet= src=NEW4 D11
    'P167',  # variant_index=0 sheet= src=NEW4 E5
    'P168',  # variant_index=0 sheet= src=NEW4 E6
    'P169',  # variant_index=0 sheet= src=NEW4 E7
    'P170',  # variant_index=0 sheet= src=NEW4 E8
    'P171',  # variant_index=0 sheet= src=NEW4 F5
    'P172',  # variant_index=0 sheet= src=S5 E4
    'P174',  # variant_index=0 sheet= src=S5 C4
    'P175',  # variant_index=0 sheet= src=S5 D2
    'P176',  # variant_index=0 sheet= src=S5 F2
    'P178',  # variant_index=0 sheet= src=S5 D4
    'P179',  # variant_index=0 sheet= src=S5 E3
    'P183',  # variant_index=0 sheet= src=S5 G4
]
