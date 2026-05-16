"""
Sprite pool for category: characters (generic — no item_name mapping)

Generated from characters_library.json + canonical_pool_full.pkl.

Shape: _CHARACTERS_POOL is a list of pids ordered by variant_index.
These sprites are used dynamically (e.g. character creator picks one,
potion identification rolls a random sprite, etc.). They are NOT tied
to specific item names.

Stats:
  total sprites: 73

Use:
    pid = _CHARACTERS_POOL[index]                # if you want a specific one
    pid = random.choice(_CHARACTERS_POOL)        # if assignment is random
    img = canonical_pool[pid]["img_b64"]

Race filtering
--------------
`_CHARACTERS_BY_RACE` maps 'human' / 'elf' / 'dwarf' to a list of pids
that are visually appropriate for that race. Maintained by the
sprite_package/picks_characters/picker.html tool — the JSON output from
that picker gets transcribed into the dict below.

Call `get_race_pool(race)` to fetch the filtered pool. If the race has
no curated picks yet (empty list), it falls back to `_CHARACTERS_POOL`
so character creation never breaks.
"""

_CHARACTERS_POOL = [
    'CH0008',  # variant_index=0 sheet=S6R src=r00c08
    'CH0009',  # variant_index=1 sheet=S6R src=r00c10
    'CH0010',  # variant_index=2 sheet=S6R src=r00c11
    'CH0012',  # variant_index=3 sheet=S6R src=r00c13
    'CH0013',  # variant_index=4 sheet=S6R src=r00c14
    'CH0014',  # variant_index=5 sheet=S6R src=r00c15
    'CH0022',  # variant_index=6 sheet=S6R src=r01c08
    'CH0024',  # variant_index=7 sheet=S6R src=r01c10
    'CH0025',  # variant_index=8 sheet=S6R src=r01c11
    'CH0026',  # variant_index=9 sheet=S6R src=r01c12
    'CH0028',  # variant_index=10 sheet=S6R src=r01c14
    'CH0040',  # variant_index=11 sheet=S6R src=r03c00
    'CH0042',  # variant_index=12 sheet=S6R src=r03c02
    'CH0045',  # variant_index=13 sheet=S6R src=r03c05
    'CH0048',  # variant_index=14 sheet=S6R src=r03c08
    'CH0049',  # variant_index=15 sheet=S6R src=r03c09
    'CH0050',  # variant_index=16 sheet=S6R src=r03c10
    'CH0051',  # variant_index=17 sheet=S6R src=r03c11
    'CH0054',  # variant_index=18 sheet=S6R src=r03c14
    'CH0055',  # variant_index=19 sheet=S6R src=r03c15
    'CH0057',  # variant_index=20 sheet=S6R src=r04c01
    'CH0060',  # variant_index=21 sheet=S6R src=r04c04
    'CH0061',  # variant_index=22 sheet=S6R src=r04c05
    'CH0064',  # variant_index=23 sheet=S6R src=r04c08
    'CH0065',  # variant_index=24 sheet=S6R src=r04c09
    'CH0066',  # variant_index=25 sheet=S6R src=r04c10
    'CH0068',  # variant_index=26 sheet=S6R src=r04c12
    'CH0070',  # variant_index=27 sheet=S6R src=r04c14
    'CH0078',  # variant_index=28 sheet=S6R src=r05c06
    'CH0081',  # variant_index=29 sheet=S6R src=r05c09
    'CH0082',  # variant_index=30 sheet=S6R src=r05c10
    'CH0084',  # variant_index=31 sheet=S6R src=r05c12
    'CH0093',  # variant_index=32 sheet=S6R src=r06c05
    'CH0107',  # variant_index=33 sheet=S6R src=r07c04
    'CH0108',  # variant_index=34 sheet=S6R src=r07c05
    'CH0119',  # variant_index=35 sheet=S6R src=r08c01
    'CH0124',  # variant_index=36 sheet=S6R src=r08c06
    'CH0134',  # variant_index=37 sheet=S6R src=r09c00
    'CH0135',  # variant_index=38 sheet=S6R src=r09c01
    'CH0138',  # variant_index=39 sheet=S6R src=r09c04
    'CH0139',  # variant_index=40 sheet=S6R src=r09c05
    'CH0140',  # variant_index=41 sheet=S6R src=r09c06
    'CH0145',  # variant_index=42 sheet=S6R src=r09c11
    'CH0147',  # variant_index=43 sheet=S6R src=r09c13
    'CH0150',  # variant_index=44 sheet=S6R src=r10c00
    'CH0152',  # variant_index=45 sheet=S6R src=r10c03
    'CH0155',  # variant_index=46 sheet=S6R src=r10c06
    'CH0156',  # variant_index=47 sheet=S6R src=r10c07
    'CH0161',  # variant_index=48 sheet=S6R src=r10c12
    'CH0162',  # variant_index=49 sheet=S6R src=r10c13
    'CH0165',  # variant_index=50 sheet=S6R src=r11c01
    'CH0167',  # variant_index=51 sheet=S6R src=r11c03
    'CH0185',  # variant_index=52 sheet=S6R src=r12c05
    'CH0186',  # variant_index=53 sheet=S6R src=r12c06
    'CH0272',  # variant_index=54 sheet=S6S src=r07c12
    'CH0275',  # variant_index=55 sheet=S6S src=r08c07
    'CH0282',  # variant_index=56 sheet=S6S src=r09c00
    'CH0284',  # variant_index=57 sheet=S6S src=r09c04
    'CH0313',  # variant_index=58 sheet=S6T src=r01c14
    'CH0332',  # variant_index=59 sheet=S6T src=r03c11
    'CH0338',  # variant_index=60 sheet=S6T src=r04c01
    'CH0341',  # variant_index=61 sheet=S6T src=r04c04
    'CH0347',  # variant_index=62 sheet=S6T src=r04c10
    'CH0349',  # variant_index=63 sheet=S6T src=r04c12
    'CH0353',  # variant_index=64 sheet=S6T src=r05c00
    'CH0362',  # variant_index=65 sheet=S6T src=r05c10
    'CH0365',  # variant_index=66 sheet=S6T src=r05c13
    'CH0377',  # variant_index=67 sheet=S6T src=r06c12
    'CH0389',  # variant_index=68 sheet=S6T src=r08c01
    'CH0393',  # variant_index=69 sheet=S6T src=r08c06
    'CH0397',  # variant_index=70 sheet=S6T src=r08c13
    'CH0400',  # variant_index=71 sheet=S6T src=r09c01
    'CH0405',  # variant_index=72 sheet=S6T src=r09c11
]


# Race -> list of pids. Populated by hand from the picker.html export
# (see sprite_package/picks_characters/). Empty list means "no curated
# selection yet — fall back to the full pool".
_CHARACTERS_BY_RACE = {
    'human': [],
    'elf':   [],
    'dwarf': [],
}


def get_race_pool(race):
    """Return the curated sprite pool for `race`, or the full pool if empty.

    Accepts any casing; unknown races fall back to the full pool too.
    """
    key = (race or '').lower()
    pool = _CHARACTERS_BY_RACE.get(key)
    if pool:
        return pool
    return _CHARACTERS_POOL

