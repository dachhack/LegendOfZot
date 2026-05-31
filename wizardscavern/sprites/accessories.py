"""
Sprite map for category: accessories

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _ACCESSORIES_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 20
  total sprite variants: 60

Use: pick a deterministic variant per game-instance:
    variants = _ACCESSORIES_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_ACCESSORIES_MAP = {
    # Dwarven Ioun Stones (crafted from mined ore). Reserve sprites
    # hand-picked via the mining picker (sprite_package/picks_mining) and
    # keyed to transparent by apply_mining_sprites.py; distinct gems/orbs.
    'Ioun Stone of Fortitude': [
        ('CR0163_CR2', 0),  # reserve pick, keyed transparent
    ],
    'Ioun Stone of Might': [
        ('CR0159_CR2', 0),  # reserve pick, keyed transparent
    ],
    'Ioun Stone of Agility': [
        ('CR0164_CR2', 0),  # reserve pick, keyed transparent
    ],
    'Ioun Stone of Mastery': [
        ('CR0157_CR2', 0),  # reserve pick, keyed transparent
    ],
    'Amulet of Health': [
        ('AC0058', 0),  # sheet=AC1 src=r04c11
        ('AC0069', 1),  # sheet=AC1 src=r05c10
        ('AC0497', 2),  # sheet=AC6 src=r03c11
    ],
    'Amulet of True Sight': [
        ('AC0037', 0),  # sheet=AC1 src=r03c02
        ('AC0039', 1),  # sheet=AC1 src=r03c04
        ('AC0038', 2),  # sheet=AC1 src=r03c03
    ],
    'Anklet of Agility': [
        ('AC0120', 0),  # sheet=AC1 src=r10c01
        ('AC0119', 1),  # sheet=AC1 src=r10c00
        ('AC0122', 2),  # sheet=AC1 src=r10c03
    ],
    'Anklet of Swiftness': [
        ('AC0534', 0),  # sheet=AC7 src=r09c10
        ('AC0131', 1),  # sheet=AC1 src=r11c00
        ('AC0121', 2),  # sheet=AC1 src=r10c02
    ],
    'Belt of the Giant': [
        ('AC0532', 0),  # sheet=AC7 src=r09c08
        ('AC0533', 1),  # sheet=AC6 src=r09c09
        ('AC0118', 2),  # sheet=AC7 src=r09c11
    ],
    'Boots of Haste': [
        ('AC0393', 0),  # sheet=AC5 src=r09c01
        ('AC0394', 1),  # sheet=AC5 src=r09c02
        ('AC0395', 2),  # sheet=AC5 src=r09c03
    ],
    'Bracer of Strength': [
        ('AC0097', 0),  # sheet=AC1 src=r08c02
        ('AC0098', 1),  # sheet=AC1 src=r08c03
        ('AC0099', 2),  # sheet=AC1 src=r08c04
    ],
    'Bracers of Balance': [
        ('AC0089', 0),  # sheet=AC1 src=r07c06
        ('AC0090', 1),  # sheet=AC1 src=r07c07
        ('AC0091', 2),  # sheet=AC6 src=r07c08
    ],
    "Champion's Signet": [
        ('AC0026', 0),  # sheet=AC1 src=r02c03
        ('AC0025', 1),  # sheet=AC1 src=r02c02
        ('AC0027', 2),  # sheet=AC1 src=r02c04
    ],
    'Circlet of Intellect': [
        ('AC0072', 0),  # sheet=AC1 src=r06c01
        ('AC0071', 1),  # sheet=AC1 src=r06c00
        ('AC0076', 2),  # sheet=AC1 src=r06c05
    ],
    'Circlet of Intelligence': [
        ('AC0077', 0),  # sheet=AC1 src=r06c06
        ('AC0078', 1),  # sheet=AC1 src=r06c07
        ('AC0079', 2),  # sheet=AC1 src=r06c08
    ],
    'Cloak of Shadows': [
        ('AC0464', 0),  # sheet=AC5 src=r10c05
        ('AC0404', 1),  # sheet=AC3 src=r10c00
        ('AC0409', 2),  # sheet=AC3 src=r10c05
    ],
    'Gauntlets of Power': [
        ('AC0355', 0),  # sheet=AC3 src=r05c11
        ('AC0353', 1),  # sheet=AC3 src=r05c09
        ('AC0362', 2),  # sheet=AC5 src=r06c06
    ],
    'Heartstone Pendant': [
        ('AC0053', 0),  # sheet=AC1 src=r04c06
        ('AC0055', 1),  # sheet=AC1 src=r04c08
        ('AC0057', 2),  # sheet=AC1 src=r04c10
    ],
    'Pendant of Fortitude': [
        ('AC0061', 0),  # sheet=AC1 src=r05c02
        ('AC0063', 1),  # sheet=AC1 src=r05c04
        ('AC0064', 2),  # sheet=AC1 src=r05c05
    ],
    'Ring of Protection': [
        ('AC0010', 0),  # sheet=AC1 src=r01c06
        ('AC0008', 1),  # sheet=AC1 src=r00c07
        ('AC0020', 2),  # sheet=AC1 src=r01c09
    ],
    'Ring of Regeneration': [
        ('AC0016', 0),  # sheet=AC1 src=r01c04
        ('AC0015', 1),  # sheet=AC1 src=r01c03
        ('AC0004', 2),  # sheet=AC1 src=r00c03
    ],
    'Ring of Strength': [
        ('AC0022', 0),  # sheet=AC1 src=r01c11
        ('AC0021', 1),  # sheet=AC1 src=r01c10
        ('AC0011', 2),  # sheet=AC1 src=r00c11
    ],
    'Skull of the Mage': [
        ('AC0041', 0),  # sheet=AC1 src=r03c06
        ('AC0042', 1),  # sheet=AC1 src=r03c07
        ('AC0188', 2),  # sheet=AC4 src=r03c11
    ],
    "Wizard's Monocle": [
        ('AC0129', 0),  # sheet=AC1 src=r10c10
        ('AC0130', 1),  # sheet=AC1 src=r10c11
        ('AC0136', 2),  # sheet=AC1 src=r11c06
    ],
    'Hourglass Talisman': [
        ('AC0495', 0),  # picked via sprite_package/picks_recent
    ],
}
