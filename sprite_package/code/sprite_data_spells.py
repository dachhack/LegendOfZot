"""
Sprite pool for category: spells (generic — no item_name mapping)

Generated from spells_library.json + canonical_pool_full.pkl.

Shape: _SPELLS_POOL is a list of pids ordered by variant_index.
These sprites are used dynamically (e.g. character creator picks one,
potion identification rolls a random sprite, etc.). They are NOT tied
to specific item names.

Stats:
  total sprites: 49

Use:
    pid = _SPELLS_POOL[index]                # if you want a specific one
    pid = random.choice(_SPELLS_POOL)        # if assignment is random
    img = canonical_pool[pid]["img_b64"]
"""

_SPELLS_POOL = [
    'I012',  # variant_index=0 sheet=original src=E4
    'I028',  # variant_index=0 sheet=original src=J12
    'I029',  # variant_index=0 sheet=original src=E1
    'I047',  # variant_index=0 sheet=original src=J2
    'I056',  # variant_index=0 sheet=original src=F12
    'I058',  # variant_index=0 sheet=original src=J1
    'I062',  # variant_index=0 sheet=original src=I2
    'I087',  # variant_index=0 sheet=original src=J3
    'I096',  # variant_index=0 sheet=original src=I1
    'I098',  # variant_index=0 sheet=original src=D15
    'I099',  # variant_index=0 sheet=original src=E11
    'I102',  # variant_index=0 sheet=original src=E13
    'I111',  # variant_index=0 sheet=original src=K11
    'I114',  # variant_index=0 sheet=original src=J4
    'I115',  # variant_index=0 sheet=original src=J11
    'I118',  # variant_index=0 sheet=original src=I4
    'I120',  # variant_index=0 sheet=original src=C14
    'I124',  # variant_index=0 sheet=original src=I3
    'I131',  # variant_index=0 sheet=original src=F11
    'I132',  # variant_index=0 sheet=original src=D12
    'I150',  # variant_index=0 sheet=original src=C7
    'I154',  # variant_index=0 sheet=original src=E7
    'I159',  # variant_index=0 sheet=original src=C6
    'I164',  # variant_index=0 sheet=original src=H5
    'I168',  # variant_index=0 sheet=original src=I7
    'I170',  # variant_index=0 sheet=original src=I11
    'I171',  # variant_index=0 sheet=original src=E5
    'I181',  # variant_index=0 sheet=original src=K16
    'I185',  # variant_index=0 sheet=original src=J16
    'I186',  # variant_index=0 sheet=original src=C16
    'V054',  # variant_index=0 sheet=3664 src=x188y253-x258y324
    'V060',  # variant_index=0 sheet=3664 src=x126y255-x193y322
    'V078',  # variant_index=0 sheet=3664 src=x0y320-x63y383
    'V109',  # variant_index=0 sheet=3665 src=x422y102-x476y157
    'V167',  # variant_index=0 sheet=3664 src=x511y639-x577y705
    'V211',  # variant_index=0 sheet=3664 src=x447y704-x512y768
    'V213',  # variant_index=0 sheet=3665 src=x898y549-x954y606
    'V215',  # variant_index=0 sheet=3664 src=x379y701-x449y772
    'V219',  # variant_index=0 sheet=3665 src=x629y601-x693y666
    'V220',  # variant_index=0 sheet=3665 src=x473y605-x531y662
    'V228',  # variant_index=0 sheet=3665 src=x1109y549-x1167y607
    'V247',  # variant_index=0 sheet=3664 src=x61y63-x130y131
    'V289',  # variant_index=0 sheet=3664 src=x829y62-x898y131
    'V292',  # variant_index=0 sheet=3664 src=x957y254-x1024y321
    'V298',  # variant_index=0 sheet=3664 src=x892y61-x962y131
    'V335',  # variant_index=0 sheet=3665 src=x895y491-x958y554
    'W141',  # variant_index=0 sheet=ewck9w src=x319y979-x416y1076
    'W144',  # variant_index=0 sheet=ewck9w src=x1161y321-x1272y433
    'W146',  # variant_index=0 sheet=ewck9w src=x526y321-x635y430
    'V124',  # picked via sprite_package/picks_recent
    'V175',  # picked via sprite_package/picks_recent
    'I172',  # picked via sprite_package/picks_recent
    'V310',  # picked via sprite_package/picks_recent
    'V358',  # picked via sprite_package/picks_recent
    'I135',  # picked via sprite_package/picks_recent
]
