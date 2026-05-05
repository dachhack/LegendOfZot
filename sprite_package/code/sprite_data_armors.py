"""
Sprite map for category: armors

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _ARMORS_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 48
  total sprite variants: 114

Use: pick a deterministic variant per game-instance:
    variants = _ARMORS_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_ARMORS_MAP = {
    'Abyssal Shell': [
        ('AR0170', 0),  # sheet=A2 src=r07c03
        ('AR0160', 1),  # sheet=A2 src=r06c03
        ('AR0065', 2),  # sheet=A1 src=r06c07
    ],
    'Adamantine Plate': [
        ('AR0071', 0),  # sheet=A1 src=r07c03
        ('AR0009', 1),  # sheet=A1 src=r00c08
        ('AR0094', 2),  # sheet=A1 src=r09c07
    ],
    'Aegis of the Paladin': [
        ('AR0176', 0),  # sheet=A2 src=r07c09
        ('AR0092', 1),  # sheet=A1 src=r09c04
        ('AR0136', 2),  # sheet=A2 src=r03c09
    ],
    'Astral Fortress': [
        ('AR0188', 0),  # sheet=A2 src=r09c01
        ('AR0086', 1),  # sheet=A1 src=r08c08
    ],
    'Breastplate': [
        ('AR0025', 0),  # sheet=A1 src=r02c05
        ('AR0006', 1),  # sheet=A1 src=r00c05
        ('AR0120', 2),  # sheet=A2 src=r02c03
    ],
    'Celestial Mail': [
        ('AR0158', 0),  # sheet=A2 src=r06c01
        ('AR0168', 1),  # sheet=A2 src=r07c01
        ('AR0145', 2),  # sheet=A2 src=r04c08
    ],
    'Chainmail': [
        ('AR0118', 0),  # sheet=A2 src=r02c01
        ('AR0020', 1),  # sheet=A1 src=r02c00
        ('AR0021', 2),  # sheet=A1 src=r02c01
    ],
    'Cloth Robes': [
        ('AR0001', 0),  # sheet=A1 src=r00c00
        ('AR0002', 1),  # sheet=A1 src=r00c01
        ('AR0003', 2),  # sheet=A1 src=r00c02
    ],
    'Cosmic Shell': [
        ('AR0190', 0),  # sheet=A2 src=r09c03
        ('AR0180', 1),  # sheet=A2 src=r08c03
        ('AR0146', 2),  # sheet=A2 src=r04c09
    ],
    'Crystal Plate': [
        ('AR0051', 0),  # sheet=A1 src=r05c02
        ('AR0143', 1),  # sheet=A2 src=r04c06
        ('AR0052', 2),  # sheet=A1 src=r05c03
    ],
    'Deepforge Plate': [
        ('AR0156', 0),  # sheet=A2 src=r05c09
        ('AR0058', 1),  # sheet=A1 src=r05c09
        ('AR0152', 2),  # sheet=A2 src=r05c05
    ],
    'Doomplate': [
        ('AR0175', 0),  # sheet=A2 src=r07c08
        ('AR0165', 1),  # sheet=A2 src=r06c08
    ],
    'Dragon Scale': [
        ('AR0129', 0),  # sheet=A2 src=r03c02
        ('AR0045', 1),  # sheet=A1 src=r04c06
        ('AR0140', 2),  # sheet=A2 src=r04c03
    ],
    'Dragon Scale Armor': [
        ('AR0182', 0),  # sheet=A2 src=r08c05
    ],
    'Dwarven Plate': [
        ('AR0159', 0),  # sheet=A2 src=r06c02
        ('AR0164', 1),  # sheet=A2 src=r06c07
        ('AR0047', 2),  # sheet=A1 src=r04c08
    ],
    'Elder Warplate': [
        ('AR0163', 0),  # sheet=A2 src=r06c06
    ],
    'Eldrich Mail': [
        ('AR0173', 0),  # sheet=A2 src=r07c06
        ('AR0063', 1),  # sheet=A1 src=r06c05
    ],
    'Elven Mail': [
        ('AR0151', 0),  # sheet=A2 src=r05c04
        ('AR0149', 1),  # sheet=A2 src=r05c02
        ('AR0139', 2),  # sheet=A2 src=r04c02
    ],
    'Enchanted Plate': [
        ('AR0148', 0),  # sheet=A2 src=r05c01
        ('AR0193', 1),  # sheet=A2 src=r09c06
        ('AR0062', 2),  # sheet=A1 src=r06c04
    ],
    'Eternity Aegis': [
        ('AR0162', 0),  # sheet=A2 src=r06c05
        ('AR0183', 1),  # sheet=A2 src=r08c06
        ('AR0177', 2),  # sheet=A2 src=r08c00
    ],
    'Full Plate': [
        ('AR0125', 0),  # sheet=A2 src=r02c08
        ('AR0135', 1),  # sheet=A2 src=r03c08
        ('AR0042', 2),  # sheet=A1 src=r04c03
    ],
    'Godplate': [
        ('AR0091', 0),  # sheet=A1 src=r09c03
        ('AR0087', 1),  # sheet=A1 src=r08c09
        ('AR0081', 2),  # sheet=A1 src=r08c03
    ],
    'Half Plate': [
        ('AR0031', 0),  # sheet=A1 src=r03c02
        ('AR0083', 1),  # sheet=A1 src=r08c05
        ('AR0128', 2),  # sheet=A2 src=r03c01
    ],
    'Hide Armor': [
        ('AR0014', 0),  # sheet=A1 src=r01c03
        ('AR0016', 1),  # sheet=A1 src=r01c05
        ('AR0018', 2),  # sheet=A1 src=r01c07
    ],
    "Knight's Armor": [
        ('AR0147', 0),  # sheet=A2 src=r05c00
        ('AR0138', 1),  # sheet=A2 src=r04c01
        ('AR0141', 2),  # sheet=A2 src=r04c04
    ],
    'Leather Armor': [
        ('AR0012', 0),  # sheet=A1 src=r01c01
        ('AR0110', 1),  # sheet=A2 src=r01c03
        ('AR0011', 2),  # sheet=A1 src=r01c00
    ],
    'Mithril Chainmail': [
        ('AR0137', 0),  # sheet=A2 src=r04c00
        ('AR0039', 1),  # sheet=A1 src=r04c00
        ('AR0040', 2),  # sheet=A1 src=r04c01
    ],
    'Mythic Bulwark': [
        ('AR0172', 0),  # sheet=A2 src=r07c05
        ('AR0195', 1),  # sheet=A2 src=r09c08
    ],
    'Nethersteel Armor': [
        ('AR0054', 0),  # sheet=A1 src=r05c05
    ],
    'Padded Armor': [
        ('AR0004', 0),  # sheet=A1 src=r00c03
        ('AR0005', 1),  # sheet=A1 src=r00c04
        ('AR0013', 2),  # sheet=A1 src=r01c02
    ],
    'Plate Armor': [
        ('AR0122', 0),  # sheet=A2 src=r02c05
        ('AR0134', 1),  # sheet=A2 src=r03c07
        ('AR0036', 2),  # sheet=A1 src=r03c07
    ],
    'Primordial Bastion': [
        ('AR0171', 0),  # sheet=A2 src=r07c04
    ],
    'Ring Mail': [
        ('AR0022', 0),  # sheet=A1 src=r02c02
        ('AR0127', 1),  # sheet=A2 src=r03c00
    ],
    'Runeforged Armor': [
        ('AR0169', 0),  # sheet=A2 src=r07c02
        ('AR0053', 1),  # sheet=A1 src=r05c04
    ],
    "Runesmith's Carapace": [
        ('AR0095', 0),  # sheet=A1 src=r09c08
    ],
    'Scale Mail': [
        ('AR0023', 0),  # sheet=A1 src=r02c03
        ('AR0024', 1),  # sheet=A1 src=r02c04
        ('AR0119', 2),  # sheet=A2 src=r02c02
    ],
    'Shadow Cloak of Nocturne': [
        ('AR0184', 0),  # sheet=A2 src=r08c07
        ('AR0194', 1),  # sheet=A2 src=r09c07
        ('AR0167', 2),  # sheet=A2 src=r07c00
    ],
    'Shadowsteel Mail': [
        ('AR0191', 0),  # sheet=A2 src=r09c04
    ],
    'Splint Armor': [
        ('AR0027', 0),  # sheet=A1 src=r02c07
        ('AR0028', 1),  # sheet=A1 src=r02c09
        ('AR0131', 2),  # sheet=A2 src=r03c04
    ],
    'Starfall Plate': [
        ('AR0069', 0),  # sheet=A1 src=r07c01
    ],
    'Stormweave Armor': [
        ('AR0144', 0),  # sheet=A2 src=r04c07
    ],
    'Studded Leather': [
        ('AR0019', 0),  # sheet=A1 src=r01c09
        ('AR0116', 1),  # sheet=A2 src=r01c09
        ('AR0115', 2),  # sheet=A2 src=r01c08
    ],
    'Titan Guard': [
        ('AR0192', 0),  # sheet=A2 src=r09c05
    ],
    "Titan's Plate": [
        ('AR0178', 0),  # sheet=A2 src=r08c01
    ],
    'Venomscale Mail': [
        ('AR0150', 0),  # sheet=A2 src=r05c03
        ('AR0056', 1),  # sheet=A1 src=r05c07
        ('AR0089', 2),  # sheet=A1 src=r09c01
    ],
    'Void Carapace': [
        ('AR0155', 0),  # sheet=A2 src=r05c08
    ],
    'Volcanic Mail': [
        ('AR0049', 0),  # sheet=A1 src=r05c00
        ('AR0050', 1),  # sheet=A1 src=r05c01
        ('AR0142', 2),  # sheet=A2 src=r04c05
    ],
    'Worldshield': [
        ('AR0174', 0),  # sheet=A2 src=r07c07
    ],
}
