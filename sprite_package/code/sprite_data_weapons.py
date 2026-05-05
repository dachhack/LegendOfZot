"""
Sprite map for category: weapons

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _WEAPONS_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 63
  total sprite variants: 124

Use: pick a deterministic variant per game-instance:
    variants = _WEAPONS_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_WEAPONS_MAP = {
    'Abyssal Scythe': [
        ('WP0366', 0),  # sheet=Weapons1 src=r08c13
    ],
    'Adamantine Sword': [
        ('WP0604', 0),  # sheet=Weapons7 src=r04c03
        ('WP0601', 1),  # sheet=Weapons6 src=r08c02
        ('WP0617', 2),  # sheet=Weapons8 src=r08c02
    ],
    'Astral Annihilator': [
        ('WP0872', 0),  # sheet=Weapons5 src=r10c06
    ],
    'Battle Axe': [
        ('WP0340', 0),  # sheet=Weapons8 src=r02c05
        ('WP0284', 1),  # sheet=Weapons8 src=r07c14
        ('WP0232', 2),  # sheet=Weapons6 src=r10c05
    ],
    'Blade of the Ancients': [
        ('WP0333', 0),  # sheet=Weapons3 src=r02c13
        ('WP0305', 1),  # sheet=Weapons3 src=r03c15
        ('WP0337', 2),  # sheet=Weapons3 src=r00c12
    ],
    'Blade of the Phoenix': [
        ('WP0590', 0),  # sheet=Weapons6 src=r07c03
    ],
    'Bow': [
        ('WP0624', 0),  # sheet=Weapons2 src=r10c09
    ],
    'Claymore': [
        ('WP0481', 0),  # sheet=Weapons8 src=r07c03
        ('WP0464', 1),  # sheet=Weapons7 src=r09c00
        ('WP0882', 2),  # sheet=Weapons1 src=r00c00
    ],
    'Club': [
        ('WP0150', 0),  # sheet=Weapons4 src=r04c01
        ('WP0194', 1),  # sheet=Weapons4 src=r05c02
        ('WP0372', 2),  # sheet=Weapons3 src=r00c00
    ],
    'Cosmic Reaper': [
        ('WP0864', 0),  # sheet=Weapons1 src=r02c06
    ],
    'Crystal Greatsword': [
        ('WP0779', 0),  # sheet=Weapons6 src=r10c02
    ],
    'Dagger': [
        ('WP0526', 0),  # sheet=Weapons8 src=r01c02
        ('WP0547', 1),  # sheet=Weapons3 src=r01c12
        ('WP0563', 2),  # sheet=Weapons3 src=r01c06
    ],
    'Deepforge Hammer': [
        ('WP0888', 0),  # sheet=Weapons1 src=r12c06
    ],
    'Doomhammer': [
        ('WP0879', 0),  # sheet=Weapons6 src=r05c07
    ],
    'Dragon Slayer': [
        ('WP0099', 0),  # sheet=Weapons6 src=r10c00
        ('WP0206', 1),  # sheet=Weapons3 src=r02c15
        ('WP0450', 2),  # sheet=Weapons6 src=r10c01
    ],
    "Dragon's Tooth Blade": [
        ('WP0664', 0),  # sheet=Weapons1 src=r06c03
    ],
    'Dwarven Waraxe': [
        ('WP0269', 0),  # sheet=Weapons8 src=r10c05
        ('WP0578', 1),  # sheet=Weapons8 src=r00c05
        ('WP0171', 2),  # sheet=Weapons8 src=r11c04
    ],
    'Elder Warblade': [
        ('WP0834', 0),  # sheet=Weapons1 src=r00c05
    ],
    'Eldrich Sword': [
        ('WP0867', 0),  # sheet=Weapons1 src=r12c02
    ],
    'Elven Blade': [
        ('WP0777', 0),  # sheet=Weapons1 src=r00c04
        ('WP0763', 1),  # sheet=Weapons1 src=r11c11
        ('WP0626', 2),  # sheet=Weapons7 src=r03c01
    ],
    'Enchanted Longsword': [
        ('WP0746', 0),  # sheet=Weapons1 src=r04c04
        ('WP0608', 1),  # sheet=Weapons7 src=r03c03
        ('WP0469', 2),  # sheet=Weapons8 src=r10c01
    ],
    'Eternity Blade': [
        ('WP0633', 0),  # sheet=Weapons1 src=r02c07
    ],
    "Executioner's Blade": [
        ('WP0522', 0),  # sheet=Weapons1 src=r07c01
        ('WP0700', 1),  # sheet=Weapons1 src=r01c00
        ('WP0123', 2),  # sheet=Weapons3 src=r09c11
    ],
    'Falchion': [
        ('WP0431', 0),  # sheet=Weapons8 src=r11c00
        ('WP0559', 1),  # sheet=Weapons8 src=r01c03
        ('WP0505', 2),  # sheet=Weapons8 src=r00c15
    ],
    'Godslayer': [
        ('WP0534', 0),  # sheet=Weapons6 src=r04c02
    ],
    'Greatsword': [
        ('WP0314', 0),  # sheet=Weapons8 src=r09c03
        ('WP0092', 1),  # sheet=Weapons8 src=r08c03
        ('WP0789', 2),  # sheet=Weapons1 src=r07c04
    ],
    'Halberd': [
        ('WP0507', 0),  # sheet=Weapons7 src=r05c08
        ('WP0348', 1),  # sheet=Weapons7 src=r07c08
        ('WP0784', 2),  # sheet=Weapons1 src=r08c10
    ],
    'Hammer of the Titans': [
        ('WP0827', 0),  # sheet=Weapons6 src=r07c07
    ],
    'Handaxe': [
        ('WP0345', 0),  # sheet=Weapons6 src=r08c04
        ('WP0224', 1),  # sheet=Weapons4 src=r06c01
        ('WP0443', 2),  # sheet=Weapons6 src=r01c04
    ],
    'Iron Sword': [
        ('WP0178', 0),  # sheet=Weapons3 src=r07c10
        ('WP0160', 1),  # sheet=Weapons3 src=r08c10
        ('WP0163', 2),  # sheet=Weapons3 src=r08c14
    ],
    'Longsword': [
        ('WP0213', 0),  # sheet=Weapons4 src=r07c03
        ('WP0413', 1),  # sheet=Weapons6 src=r08c00
        ('WP0490', 2),  # sheet=Weapons8 src=r09c00
    ],
    'Mace': [
        ('WP0444', 0),  # sheet=Weapons6 src=r04c07
        ('WP0462', 1),  # sheet=Weapons7 src=r05c09
    ],
    'Mithril Sword': [
        ('WP0421', 0),  # sheet=Weapons7 src=r06c03
        ('WP0502', 1),  # sheet=Weapons6 src=r05c00
        ('WP0599', 2),  # sheet=Weapons6 src=r03c03
    ],
    'Morningstar': [
        ('WP0332', 0),  # sheet=Weapons7 src=r08c07
        ('WP0335', 1),  # sheet=Weapons7 src=r08c06
        ('WP0352', 2),  # sheet=Weapons4 src=r05c05
    ],
    'Mythic Destroyer': [
        ('WP0741', 0),  # sheet=Weapons6 src=r10c07
    ],
    'Nethersteel Edge': [
        ('WP0612', 0),  # sheet=Weapons8 src=r04c02
    ],
    'Obsidian Edge': [
        ('WP0571', 0),  # sheet=Weapons3 src=r13c05
        ('WP0511', 1),  # sheet=Weapons4 src=r02c01
        ('WP0602', 2),  # sheet=Weapons3 src=r05c03
    ],
    'Primordial Cleaver': [
        ('WP0772', 0),  # sheet=Weapons1 src=r11c04
    ],
    'Runeforged Axe': [
        ('WP0891', 0),  # sheet=Weapons1 src=r08c07
    ],
    'Runic Hammer': [
        ('WP0152', 0),  # sheet=Weapons6 src=r11c06
        ('WP0317', 1),  # sheet=Weapons7 src=r05c07
        ('WP0404', 2),  # sheet=Weapons8 src=r10c07
    ],
    'Rusty Sword': [
        ('WP0708', 0),  # sheet=Weapons1 src=r04c03
        ('WP0183', 1),  # sheet=Weapons3 src=r08c07
        ('WP0319', 2),  # sheet=Weapons3 src=r03c12
    ],
    'Scepter of the Ancients': [
        ('WP0678', 0),  # sheet=Weapons8 src=r03c12
    ],
    'Shadowsteel Blade': [
        ('WP0655', 0),  # sheet=Weapons6 src=r03c01
    ],
    'Shieldbreaker Maul': [
        ('WP0714', 0),  # sheet=Weapons1 src=r07c09
    ],
    'Short Sword': [
        ('WP0405', 0),  # sheet=Weapons3 src=r05c01
        ('WP0290', 1),  # sheet=Weapons3 src=r12c10
        ('WP0349', 2),  # sheet=Weapons3 src=r12c09
    ],
    'Soul Reaver': [
        ('WP0338', 0),  # sheet=Weapons8 src=r10c15
        ('WP0570', 1),  # sheet=Weapons3 src=r04c11
        ('WP0508', 2),  # sheet=Weapons6 src=r02c03
    ],
    'Soulreaver Scythe': [
        ('WP0488', 0),  # sheet=Weapons7 src=r03c14
    ],
    'Spear': [
        ('WP0196', 0),  # sheet=Weapons4 src=r08c07
        ('WP0251', 1),  # sheet=Weapons4 src=r08c02
        ('WP0330', 2),  # sheet=Weapons6 src=r09c08
    ],
    'Staff': [
        ('WP0657', 0),  # sheet=Weapons2 src=r07c08
        ('WP0238', 1),  # sheet=Weapons2 src=r01c03
        ('WP0236', 2),  # sheet=Weapons4 src=r12c14
    ],
    'Starfall Blade': [
        ('WP0855', 0),  # sheet=Weapons1 src=r03c05
    ],
    'Steel Blade': [
        ('WP0355', 0),  # sheet=Weapons8 src=r09c01
        ('WP0383', 1),  # sheet=Weapons7 src=r05c03
        ('WP0433', 2),  # sheet=Weapons8 src=r05c00
    ],
    'Stormbreaker Axe': [
        ('WP0759', 0),  # sheet=Weapons6 src=r05c05
    ],
    'Stormcaller': [
        ('WP0034', 0),  # sheet=Weapons6 src=r02c14
        ('WP0756', 1),  # sheet=Weapons8 src=r11c15
        ('WP0814', 2),  # sheet=Weapons1 src=r05c14
    ],
    'Titan Slayer': [
        ('WP0783', 0),  # sheet=Weapons6 src=r05c02
    ],
    'Venomblade': [
        ('WP0731', 0),  # sheet=Weapons1 src=r03c09
    ],
    'Void Reaver': [
        ('WP0765', 0),  # sheet=Weapons1 src=r03c11
    ],
    'Volcanic Blade': [
        ('WP0006', 0),  # sheet=Weapons1 src=r12c00
    ],
    'Vorpal Blade': [
        ('WP0874', 0),  # sheet=Weapons8 src=r07c01
    ],
    'War Scythe': [
        ('WP0427', 0),  # sheet=Weapons8 src=r03c14
        ('WP0703', 1),  # sheet=Weapons1 src=r08c14
        ('WP0880', 2),  # sheet=Weapons1 src=r10c13
    ],
    'Warhammer': [
        ('WP0423', 0),  # sheet=Weapons7 src=r06c07
        ('WP0187', 1),  # sheet=Weapons8 src=r11c06
        ('WP0377', 2),  # sheet=Weapons8 src=r09c07
    ],
    'Whisperwind Bow': [
        ('WP0172', 0),  # sheet=Weapons4 src=r10c03
    ],
    'Worldbreaker': [
        ('WP0712', 0),  # sheet=Weapons1 src=r07c06
    ],
    'Worldrender': [
        ('WP0842', 0),  # sheet=Weapons1 src=r06c05
    ],
}
