"""
Sprite pool + named map for category: spells

Each sprite in the round-8 spell pool was originally drawn for a specific
spell, captured in spells_library.json under game_data.spell_name. We
expose both:

  _SPELLS_POOL  -- ordered list of pids, used as a fallback when a spell
                   has no explicit named mapping (e.g. modded / future
                   spells added without a matching sprite).

  _SPELLS_NAMED -- dict mapping the in-game spell name to the thematic
                   pid drawn for it. Consulted first so Chain Lightning
                   always shows the lightning sprite, Fireball always
                   shows the flame sprite, etc.

Stats:
  total sprites: 49
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
]

# Built from spells_library.json -- each pid was drawn for the named
# spell, so this preserves visual thematic identity (Fireball looks
# like fire, Chain Lightning looks like lightning, etc).
_SPELLS_NAMED = {
    'Inferno':              'I012',
    'Flame Lance':          'I028',
    'Fireball':             'I029',
    'Divine Shield':        'I047',
    'Time Stop':            'I056',
    'Stone Skin':           'I058',
    'Heal':                 'I062',
    'Ultimate Shield':      'I087',
    'Minor Heal':           'I096',
    'Battle Hymn':          'I098',
    'Purify':               'I099',
    'Cure Weakness':        'I102',
    'Acid Splash':          'I111',
    'Full Restore':         'I114',
    'Regeneration':         'I115',
    'Mass Heal':            'I118',
    'Psychic Scream':       'I120',
    'Greater Heal':         'I124',
    'Clarity':              'I131',
    'Divine Intervention':  'I132',
    'Ice Storm':            'I150',
    'Ice Shard':            'I154',
    'Absolute Zero':        'I159',
    'Water Blast':          'I164',
    'Blizzard':             'I168',
    'Holy Light':           'I170',
    'Tsunami':              'I171',
    'Mind Spike':           'I181',
    'Mind Blast':           'I185',
    'Armageddon':           'I186',
    "Titan's Strength":     'V054',
    'Stone Throw':          'V060',
    'Earthquake':           'V078',
    'Spark':                'V109',
    'Perfect Regeneration': 'V167',
    'Darkness Bolt':        'V211',
    'Shadow Strike':        'V213',
    'Holy Smite':           'V215',
    'Light Ray':            'V219',
    'Shadow Bolt':          'V220',
    'Freedom':              'V228',
    'Wind Slash':           'V247',
    'Black Hole':           'V289',
    'Meteor Strike':        'V292',
    'Supernova':            'V298',
    'Void Beam':            'V335',
    'Thunder Clap':         'W141',
    'Chain Lightning':      'W144',
    'Lightning Bolt':       'W146',
    # Mage Armor still reuses the Divine Shield force-field visual.
    'Mage Armor':           'I047',
    'Spectral Hand':        'V358',
    'Detect Monster':       'V124',
    'Hold Monster':         'V175',
    'Light':                'I172',
    'Mind Touch':           'V310',
}
