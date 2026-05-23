"""
Sprite map for category: monsters

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _MONSTERS_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 124
  total sprite variants: 372

Use: pick a deterministic variant per game-instance:
    variants = _MONSTERS_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_MONSTERS_MAP = {
    'ANCIENT': [
        ('MN0590', 0),  # sheet=M3 src=r05c15
        ('MN2237', 1),  # sheet=S6C src=r09c10
        ('MN2825', 2),  # sheet=S6G src=r08c00
    ],
    'ARCHLICH': [
        ('MN2260', 0),  # sheet=S6C src=r11c10
        ('MN2259', 1),  # sheet=S6C src=r11c09
        ('MN1945', 2),  # sheet=S6A src=r11c10
    ],
    'Ancient Dragon': [
        ('MN1829', 0),  # sheet=S6A src=r01c11
        ('MN1840', 1),  # sheet=S6A src=r04c03
        ('MN1862', 2),  # sheet=S6A src=r06c03
    ],
    'Ant Soldier': [
        ('MN1492', 0),  # sheet=BG2 src=r00c00
        ('MN1494', 1),  # sheet=BG2 src=r00c02
        ('MN1496', 2),  # sheet=BG2 src=r00c04
    ],
    'BUG QUEEN': [
        ('MN1718', 0),  # sheet=BG2 src=r14c02
        ('MN1733', 1),  # sheet=BG2 src=r15c01
        ('MN1735', 2),  # sheet=BG2 src=r15c03
    ],
    'Balor': [
        ('MN0108', 0),  # sheet=M1 src=r06c12
        ('MN0107', 1),  # sheet=M1 src=r06c11
        ('MN0191', 2),  # sheet=M1 src=r11c15
    ],
    'Balrog': [
        ('MN2634', 0),  # sheet=S6F src=r09c06
        ('MN2635', 1),  # sheet=S6F src=r09c07
        ('MN2701', 2),  # sheet=S6F src=r13c12
    ],
    'Basilisk': [
        ('MN0741', 0),  # sheet=M3 src=r15c06
        ('MN2772', 1),  # sheet=S6G src=r04c02
        ('MN2425', 2),  # sheet=S6D src=r09c07
    ],
    'Bat': [
        ('MN0052', 0),  # sheet=M1 src=r03c03
        ('MN0053', 1),  # sheet=M1 src=r03c04
        ('MN0022', 2),  # sheet=M1 src=r01c05
    ],
    'Beholder': [
        ('MN0041', 0),  # sheet=M1 src=r02c08
        ('MN0042', 1),  # sheet=M1 src=r02c09
        ('MN0043', 2),  # sheet=M1 src=r02c10
    ],
    'Black Pudding': [
        ('MN0511', 0),  # sheet=M3 src=r00c10
        ('MN0527', 1),  # sheet=M3 src=r01c10
        ('MN2655', 2),  # sheet=S6F src=r10c11
    ],
    'Bugbear': [
        ('MN0652', 0),  # sheet=M3 src=r09c13
        ('MN0650', 1),  # sheet=M3 src=r09c11
        ('MN0644', 2),  # sheet=M3 src=r09c05
    ],
    'Bulette': [
        ('MN2686', 0),  # sheet=S6F src=r12c13
        ('MN2687', 1),  # sheet=S6F src=r12c14
        ('MN2477', 2),  # sheet=S6D src=r14c07
    ],
    'CURSED DEATH KNIGHT': [
        ('MN2534', 0),  # sheet=S6F src=r02c11
        ('MN2536', 1),  # sheet=S6F src=r02c13
        ('MN2537', 2),  # sheet=S6F src=r02c14
    ],
    'Carrion Crawler': [
        ('MN1505', 0),  # sheet=BG2 src=r00c13
        ('MN1507', 1),  # sheet=BG2 src=r00c15
        ('MN1501', 2),  # sheet=BG2 src=r00c09
    ],
    'Cockatrice': [
        ('MN2852', 0),  # sheet=S6G src=r09c13
        ('MN2664', 1),  # sheet=S6F src=r11c05
        ('MN2663', 2),  # sheet=S6F src=r11c04
    ],
    'Crawling Claw': [
        ('MN4122', 0),  # sheet=S6N src=r11c08
        ('MN4138', 1),  # sheet=S6N src=r13c15
        ('MN4104', 2),  # sheet=S6N src=r08c12
    ],
    'Cyclops': [
        ('MN0009', 0),  # sheet=M1 src=r00c08
        ('MN0025', 1),  # sheet=M1 src=r01c08
        ('MN0010', 2),  # sheet=M1 src=r00c09
    ],
    'DEATH KNIGHT': [
        ('MN2911', 0),  # sheet=S6G src=r13c12
        ('MN2909', 1),  # sheet=S6G src=r13c10
        ('MN2174', 2),  # sheet=S6C src=r03c09
    ],
    'DEMON': [
        ('MN2636', 0),  # sheet=S6F src=r09c08
        ('MN2699', 1),  # sheet=S6F src=r13c10
        ('MN2700', 2),  # sheet=S6F src=r13c11
    ],
    'DIVINE AVATAR': [
        ('MN2697', 0),  # sheet=S6F src=r13c08
        ('MN2827', 1),  # sheet=S6G src=r08c02
        ('MN2896', 2),  # sheet=S6G src=r12c13
    ],
    'DRAGON': [
        ('MN2875', 0),  # sheet=S6G src=r11c08
        ('MN2882', 1),  # sheet=S6G src=r11c15
        ('MN2884', 2),  # sheet=S6G src=r12c01
    ],
    'Death Knight': [
        ('MN2703', 0),  # sheet=S6F src=r13c14
        ('MN2702', 1),  # sheet=S6F src=r13c13
        ('MN2910', 2),  # sheet=S6G src=r13c11
    ],
    'Demilich': [
        ('MN2255', 0),  # sheet=S6C src=r11c05
        ('MN2256', 1),  # sheet=S6C src=r11c06
        ('MN2257', 2),  # sheet=S6C src=r11c07
    ],
    'Displacer Beast': [
        ('MN2587', 0),  # sheet=S6F src=r06c06
        ('MN2588', 1),  # sheet=S6F src=r06c07
        ('MN2589', 2),  # sheet=S6F src=r06c08
    ],
    'Dragon Lich': [
        ('MN2609', 0),  # sheet=S6F src=r07c13
        ('MN1914', 1),  # sheet=S6A src=r09c10
        ('MN3948', 2),  # sheet=S6M src=r07c09
    ],
    'Dragon Turtle': [
        ('MN2630', 0),  # sheet=S6F src=r09c02
        ('MN2633', 1),  # sheet=S6F src=r09c05
        ('MN2833', 2),  # sheet=S6G src=r08c08
    ],
    'Dragonfly Enchantress': [
        ('MN1132', 0),  # sheet=BG src=r08c13
        ('MN1130', 1),  # sheet=BG src=r08c11
        ('MN1131', 2),  # sheet=BG src=r08c12
    ],
    'Dung Beetle Lord': [
        ('MN1059', 0),  # sheet=BG src=r04c03
        ('MN1057', 1),  # sheet=BG src=r04c01
        ('MN1043', 2),  # sheet=BG src=r03c03
    ],
    'Earthworm': [
        ('MN1683', 0),  # sheet=BG2 src=r11c15
        ('MN1666', 1),  # sheet=BG2 src=r10c14
        ('MN1682', 2),  # sheet=BG2 src=r11c14
    ],
    'Efreeti': [
        ('MN2696', 0),  # sheet=S6F src=r13c07
        ('MN2695', 1),  # sheet=S6F src=r13c06
        ('MN2831', 2),  # sheet=S6G src=r08c06
    ],
    'Elder Brain': [
        ('MN1672', 0),  # sheet=BG2 src=r11c04
        ('MN2577', 1),  # sheet=S6F src=r05c12
        ('MN2578', 2),  # sheet=S6F src=r05c13
    ],
    'Ettercap': [
        ('MN0180', 0),  # sheet=M1 src=r11c04
        ('MN2586', 1),  # sheet=S6F src=r06c05
        ('MN2781', 2),  # sheet=S6G src=r04c15
    ],
    'Fire Elemental': [
        ('MN0119', 0),  # sheet=M1 src=r07c07
        ('MN0134', 1),  # sheet=M1 src=r08c06
        ('MN0123', 2),  # sheet=M1 src=r07c11
    ],
    'Fire Giant': [
        ('MN0026', 0),  # sheet=M1 src=r01c09
        ('MN0149', 1),  # sheet=M1 src=r09c05
        ('MN2076', 2),  # sheet=S6B src=r05c05
    ],
    'Firefly Mage': [
        ('MN1598', 0),  # sheet=BG2 src=r06c10
        ('MN1582', 1),  # sheet=BG2 src=r05c10
        ('MN1745', 2),  # sheet=BG2 src=r15c13
    ],
    'Fly Swarm': [
        ('MN1003', 0),  # sheet=BG src=r00c06
        ('MN1004', 1),  # sheet=BG src=r00c07
        ('MN1048', 2),  # sheet=BG src=r03c08
    ],
    'Frost Giant': [
        ('MN0187', 0),  # sheet=M1 src=r11c11
        ('MN0612', 1),  # sheet=M3 src=r07c05
        ('MN0144', 2),  # sheet=M1 src=r09c00
    ],
    'Fungal Hulk': [
        ('MN2550', 0),  # sheet=S6F src=r03c15
        ('MN2556', 1),  # sheet=S6F src=r04c05
        ('MN2558', 2),  # sheet=S6F src=r04c07
    ],
    'Gargoyle': [
        ('MN0105', 0),  # sheet=M1 src=r06c09
        ('MN0106', 1),  # sheet=M1 src=r06c10
        ('MN0109', 2),  # sheet=M1 src=r06c13
    ],
    'Gelatinous Cube': [
        ('MN2126', 0),  # sheet=S6B src=r15c04
        ('MN2651', 1),  # sheet=S6F src=r10c07
        ('MN2650', 2),  # sheet=S6F src=r10c06
    ],
    'Giant Centipede': [
        ('MN1692', 0),  # sheet=BG2 src=r12c08
        ('MN1710', 1),  # sheet=BG2 src=r13c10
        ('MN1694', 2),  # sheet=BG2 src=r12c10
    ],
    'Giant Frost Worm': [
        ('MN3645', 0),  # sheet=S6K src=r07c03
        ('MN3586', 1),  # sheet=S6K src=r00c06
        ('MN3635', 2),  # sheet=S6K src=r06c05
    ],
    'Giant Rat': [
        ('MN2505', 0),  # sheet=S6F src=r00c07
        ('MN2516', 1),  # sheet=S6F src=r01c04
        ('MN2734', 2),  # sheet=S6G src=r01c04
    ],
    'Giant Spider': [
        ('MN1006', 0),  # sheet=BG src=r00c09
        ('MN1005', 1),  # sheet=BG src=r00c08
        ('MN1021', 2),  # sheet=BG src=r01c08
    ],
    'Gnoll': [
        ('MN2531', 0),  # sheet=S6F src=r02c08
        ('MN2532', 1),  # sheet=S6F src=r02c09
        ('MN2539', 2),  # sheet=S6F src=r03c02
    ],
    'Goblin': [
        ('MN0575', 0),  # sheet=M3 src=r05c00
        ('MN0720', 1),  # sheet=M3 src=r14c01
        ('MN0693', 2),  # sheet=M3 src=r12c06
    ],
    'Gorgon': [
        ('MN2597', 0),  # sheet=S6F src=r07c00
        ('MN2598', 1),  # sheet=S6F src=r07c01
        ('MN2493', 2),  # sheet=S6D src=r15c08
    ],
    'Gray Ooze': [
        ('MN2854', 0),  # sheet=S6G src=r10c00
        ('MN0531', 1),  # sheet=M3 src=r01c14
        ('MN2653', 2),  # sheet=S6F src=r10c09
    ],
    'Grell': [
        ('MN3758', 0),  # sheet=S6L src=r02c11
        ('MN3765', 1),  # sheet=S6L src=r03c11
        ('MN3662', 2),  # sheet=S6K src=r08c11
    ],
    'Grick': [
        ('MN3760', 0),  # sheet=S6L src=r02c15
        ('MN3764', 1),  # sheet=S6L src=r03c10
        ('MN3767', 2),  # sheet=S6L src=r03c15
    ],
    'Griffin': [
        ('MN2483', 0),  # sheet=S6D src=r14c14
        ('MN2497', 1),  # sheet=S6D src=r15c13
        ('MN2824', 2),  # sheet=S6G src=r07c15
    ],
    'Harpy': [
        ('MN3464', 0),  # sheet=S6J src=r08c00
        ('MN3465', 1),  # sheet=S6J src=r08c01
        ('MN3480', 2),  # sheet=S6J src=r09c00
    ],
    'Hell Hound': [
        ('MN2557', 0),  # sheet=S6F src=r04c06
        ('MN2549', 1),  # sheet=S6F src=r03c14
        ('MN2770', 2),  # sheet=S6G src=r04c00
    ],
    'Hill Giant': [
        ('MN0084', 0),  # sheet=M1 src=r05c03
        ('MN2075', 1),  # sheet=S6B src=r05c03
        ('MN2014', 2),  # sheet=S6B src=r00c09
    ],
    'Iron Golem': [
        ('MN3042', 0),  # sheet=S6H src=r08c15
        ('MN3110', 1),  # sheet=S6H src=r13c05
        ('MN3094', 2),  # sheet=S6H src=r12c05
    ],
    'Kobold': [
        ('MN0179', 0),  # sheet=M1 src=r11c03
        ('MN0097', 1),  # sheet=M1 src=r06c01
        ('MN0655', 2),  # sheet=M3 src=r10c00
    ],
    'Kraken': [
        ('MN3459', 0),  # sheet=S6J src=r07c10
        ('MN3408', 1),  # sheet=S6J src=r03c07
        ('MN3406', 2),  # sheet=S6J src=r03c05
    ],
    'LORD': [
        ('MN2912', 0),  # sheet=S6G src=r13c13
        ('MN2258', 1),  # sheet=S6C src=r11c08
        ('MN1943', 2),  # sheet=S6A src=r11c08
    ],
    'LOST SOUL': [
        ('MN2767', 0),  # sheet=S6G src=r03c12
        ('MN2768', 1),  # sheet=S6G src=r03c13
        ('MN3466', 2),  # sheet=S6J src=r08c02
    ],
    'Lich': [
        ('MN0574', 0),  # sheet=M3 src=r04c15
        ('MN0572', 1),  # sheet=M3 src=r04c13
        ('MN0589', 2),  # sheet=M3 src=r05c14
    ],
    'Lichen': [
        ('MN1366', 0),  # sheet=PM2 src=r07c15
        ('MN1365', 1),  # sheet=PM2 src=r07c14
        ('MN1364', 2),  # sheet=PM2 src=r07c13
    ],
    'MUMMIFIED KING': [
        ('MN2271', 0),  # sheet=S6C src=r12c14
        ('MN2286', 1),  # sheet=S6C src=r14c10
        ('MN2287', 2),  # sheet=S6C src=r14c11
    ],
    'Manticore': [
        ('MN2481', 0),  # sheet=S6D src=r14c11
        ('MN2496', 1),  # sheet=S6D src=r15c11
        ('MN2468', 2),  # sheet=S6D src=r13c14
    ],
    'Medusa': [
        ('MN2603', 0),  # sheet=S6F src=r07c07
        ('MN2802', 1),  # sheet=S6G src=r06c07
        ('MN2805', 2),  # sheet=S6G src=r06c11
    ],
    'Mimic': [
        ('MN0150', 0),  # sheet=M1 src=r09c06
        ('MN0139', 1),  # sheet=M1 src=r08c11
        ('MN0151', 2),  # sheet=M1 src=r09c07
    ],
    'Mind Flayer': [
        ('MN2613', 0),  # sheet=S6F src=r08c01
        ('MN2615', 1),  # sheet=S6F src=r08c03
        ('MN2816', 2),  # sheet=S6G src=r07c07
    ],
    'Minotaur': [
        ('MN0593', 0),  # sheet=M3 src=r06c02
        ('MN0011', 1),  # sheet=M1 src=r00c10
        ('MN0028', 2),  # sheet=M1 src=r01c11
    ],
    'Mummy': [
        ('MN0058', 0),  # sheet=M1 src=r03c09
        ('MN2252', 1),  # sheet=S6C src=r10c12
        ('MN2238', 2),  # sheet=S6C src=r09c11
    ],
    'Myconid Shaman': [
        ('MN1275', 0),  # sheet=PM2 src=r02c01
        ('MN1274', 1),  # sheet=PM2 src=r02c00
        ('MN1291', 2),  # sheet=PM2 src=r03c01
    ],
    'Naga': [
        ('MN2424', 0),  # sheet=S6D src=r09c06
        ('MN2422', 1),  # sheet=S6D src=r09c04
        ('MN2418', 2),  # sheet=S6D src=r09c00
    ],
    'Naga Guardian': [
        ('MN2619', 0),  # sheet=S6F src=r08c07
        ('MN2618', 1),  # sheet=S6F src=r08c06
        ('MN2407', 2),  # sheet=S6D src=r08c05
    ],
    'Night Hag': [
        ('MN1948', 0),  # sheet=S6A src=r11c13
        ('MN2186', 1),  # sheet=S6C src=r04c12
        ('MN2236', 2),  # sheet=S6C src=r09c09
    ],
    'Ochre Jelly': [
        ('MN2502', 0),  # sheet=S6F src=r00c04
        ('MN0530', 1),  # sheet=M3 src=r01c13
        ('MN2654', 2),  # sheet=S6F src=r10c10
    ],
    'Ogre': [
        ('MN0198', 0),  # sheet=M1 src=r12c06
        ('MN0085', 1),  # sheet=M1 src=r05c04
        ('MN0666', 2),  # sheet=M3 src=r10c11
    ],
    'Orc': [
        ('MN0066', 0),  # sheet=M1 src=r04c01
        ('MN0172', 1),  # sheet=M1 src=r10c12
        ('MN0143', 2),  # sheet=M1 src=r08c15
    ],
    'Otyugh': [
        ('MN2783', 0),  # sheet=S6G src=r05c01
        ('MN2581', 1),  # sheet=S6F src=r06c00
        ('MN2782', 2),  # sheet=S6G src=r05c00
    ],
    'Owlbear': [
        ('MN2656', 0),  # sheet=S6F src=r10c12
        ('MN2657', 1),  # sheet=S6F src=r10c13
        ('MN2670', 2),  # sheet=S6F src=r11c13
    ],
    'POLTERGEIST': [
        ('MN2233', 0),  # sheet=S6C src=r09c06
        ('MN2232', 1),  # sheet=S6C src=r09c05
        ('MN2231', 2),  # sheet=S6C src=r09c04
    ],
    'Pill Bug Golem': [
        ('MN1613', 0),  # sheet=BG2 src=r07c09
        ('MN1612', 1),  # sheet=BG2 src=r07c08
        ('MN1611', 2),  # sheet=BG2 src=r07c07
    ],
    'Pit Fiend': [
        ('MN0713', 0),  # sheet=M3 src=r13c10
        ('MN0218', 1),  # sheet=M1 src=r13c10
        ('MN0124', 2),  # sheet=M1 src=r07c12
    ],
    'Platino': [
        ('MN1860', 0),  # sheet=S6A src=r06c01
        ('MN1876', 1),  # sheet=S6A src=r07c01
        ('MN1877', 2),  # sheet=S6A src=r07c02
    ],
    'Purple Worm': [
        ('MN3699', 0),  # sheet=S6K src=r11c11
        ('MN3721', 1),  # sheet=S6K src=r13c03
        ('MN3747', 2),  # sheet=S6K src=r14c13
    ],
    'RESTLESS SPIRIT': [
        ('MN2572', 0),  # sheet=S6F src=r05c07
        ('MN2571', 1),  # sheet=S6F src=r05c06
        ('MN2570', 2),  # sheet=S6F src=r05c05
    ],
    'Rakshasa': [
        ('MN2624', 0),  # sheet=S6F src=r08c12
        ('MN2694', 1),  # sheet=S6F src=r13c05
        ('MN2693', 2),  # sheet=S6F src=r13c04
    ],
    'Roc': [
        ('MN0077', 0),  # sheet=M1 src=r04c12
        ('MN0095', 1),  # sheet=M1 src=r05c14
        ('MN0079', 2),  # sheet=M1 src=r04c14
    ],
    'Rust Monster': [
        ('MN2777', 0),  # sheet=S6G src=r04c11
        ('MN2776', 1),  # sheet=S6G src=r04c10
        ('MN2647', 2),  # sheet=S6F src=r10c03
    ],
    'SKELETAL CHAMPION': [
        ('MN2176', 0),  # sheet=S6C src=r03c11
        ('MN2139', 1),  # sheet=S6C src=r00c09
        ('MN2172', 2),  # sheet=S6C src=r03c05
    ],
    'SPECTRAL KNIGHT': [
        ('MN2748', 0),  # sheet=S6G src=r02c04
        ('MN2704', 1),  # sheet=S6F src=r13c15
        ('MN2254', 2),  # sheet=S6C src=r11c02
    ],
    'Sewer Rat': [
        ('MN2528', 0),  # sheet=S6F src=r02c03
        ('MN2526', 1),  # sheet=S6F src=r02c00
        ('MN2517', 2),  # sheet=S6F src=r01c06
    ],
    'Skeleton': [
        ('MN0562', 0),  # sheet=M3 src=r04c03
        ('MN0070', 1),  # sheet=M1 src=r04c05
        ('MN0054', 2),  # sheet=M1 src=r03c05
    ],
    'Slime Mold': [
        ('MN0513', 0),  # sheet=M3 src=r00c12
        ('MN0526', 1),  # sheet=M3 src=r01c09
        ('MN0514', 2),  # sheet=M3 src=r00c13
    ],
    'Snail': [
        ('MN3955', 0),  # sheet=S6M src=r08c01
        ('MN3968', 1),  # sheet=S6M src=r09c01
        ('MN3969', 2),  # sheet=S6M src=r09c02
    ],
    'Specter': [
        ('MN0556', 0),  # sheet=M3 src=r03c13
        ('MN2247', 1),  # sheet=S6C src=r10c07
        ('MN2246', 2),  # sheet=S6C src=r10c06
    ],
    'Sphinx': [
        ('MN2479', 0),  # sheet=S6D src=r14c09
        ('MN2494', 1),  # sheet=S6D src=r15c09
        ('MN2822', 2),  # sheet=S6G src=r07c13
    ],
    'Spore Puff': [
        ('MN1277', 0),  # sheet=PM2 src=r02c03
        ('MN1278', 1),  # sheet=PM2 src=r02c04
        ('MN1276', 2),  # sheet=PM2 src=r02c02
    ],
    'Stinkbug Brute': [
        ('MN1134', 0),  # sheet=BG src=r08c15
        ('MN1094', 1),  # sheet=BG src=r06c06
        ('MN1142', 2),  # sheet=BG src=r09c07
    ],
    'Stirge': [
        ('MN2845', 0),  # sheet=S6G src=r09c05
        ('MN2648', 1),  # sheet=S6F src=r10c04
        ('MN2649', 2),  # sheet=S6F src=r10c05
    ],
    'Stone Golem': [
        ('MN2604', 0),  # sheet=S6F src=r07c08
        ('MN2605', 1),  # sheet=S6F src=r07c09
        ('MN2607', 2),  # sheet=S6F src=r07c11
    ],
    'Storm Giant': [
        ('MN0700', 0),  # sheet=M3 src=r12c13
        ('MN0205', 1),  # sheet=M1 src=r12c13
        ('MN0145', 2),  # sheet=M1 src=r09c01
    ],
    'Succubus': [
        ('MN2900', 0),  # sheet=S6G src=r13c01
        ('MN3475', 1),  # sheet=S6J src=r08c11
        ('MN3497', 2),  # sheet=S6J src=r10c01
    ],
    'TOMB WRAITH': [
        ('MN2234', 0),  # sheet=S6C src=r09c07
        ('MN2235', 1),  # sheet=S6C src=r09c08
        ('MN2248', 2),  # sheet=S6C src=r10c08
    ],
    'TREASURE GOLEM': [
        ('MN4022', 0),  # sheet=S6M src=r12c13
        ('MN4039', 1),  # sheet=S6M src=r13c14
        ('MN4004', 2),  # sheet=S6M src=r11c10
    ],
    'Tarrasque': [
        ('MN2641', 0),  # sheet=S6F src=r09c13
        ('MN2640', 1),  # sheet=S6F src=r09c12
        ('MN2639', 2),  # sheet=S6F src=r09c11
    ],
    'Titan Beetle': [
        ('MN1529', 0),  # sheet=BG2 src=r02c05
        ('MN1530', 1),  # sheet=BG2 src=r02c06
        ('MN1526', 2),  # sheet=BG2 src=r02c02
    ],
    'Troll': [
        ('MN0680', 0),  # sheet=M3 src=r11c09
        ('MN0730', 1),  # sheet=M3 src=r14c11
        ('MN0096', 2),  # sheet=M1 src=r06c00
    ],
    'Umber Hulk': [
        ('MN2790', 0),  # sheet=S6G src=r05c08
        ('MN2791', 1),  # sheet=S6G src=r05c09
        ('MN2595', 2),  # sheet=S6F src=r06c14
    ],
    'Vampire': [
        ('MN1985', 0),  # sheet=S6A src=r14c02
        ('MN1972', 1),  # sheet=S6A src=r13c05
        ('MN1960', 2),  # sheet=S6A src=r12c09
    ],
    'Vault Guardian Golem': [
        ('MN0616', 0),  # sheet=M3 src=r07c09
        ('MN0617', 1),  # sheet=M3 src=r07c10
        ('MN0618', 2),  # sheet=M3 src=r07c11
    ],
    'Vault Keeper Wraith': [
        ('MN0587', 0),  # sheet=M3 src=r05c12
        ('MN0571', 1),  # sheet=M3 src=r04c12
        ('MN0555', 2),  # sheet=M3 src=r03c12
    ],
    'Vault Protector Titan': [
        ('MN0627', 0),  # sheet=M3 src=r08c04
        ('MN0685', 1),  # sheet=M3 src=r11c14
        ('MN0728', 2),  # sheet=M3 src=r14c09
    ],
    'Vault Sentinel Dragon': [
        ('MN1861', 0),  # sheet=S6A src=r06c02
        ('MN1849', 1),  # sheet=S6A src=r05c06
        ('MN1866', 2),  # sheet=S6A src=r06c07
    ],
    'Vault Warden Lich': [
        ('MN2712', 0),  # sheet=S6F src=r14c08
        ('MN2711', 1),  # sheet=S6F src=r14c07
        ('MN2913', 2),  # sheet=S6G src=r13c14
    ],
    'WANDERING GHOST': [
        ('MN2240', 0),  # sheet=S6C src=r10c00
        ('MN2242', 1),  # sheet=S6C src=r10c02
        ('MN2243', 2),  # sheet=S6C src=r10c03
    ],
    'Werewolf': [
        ('MN0141', 0),  # sheet=M1 src=r08c13
        ('MN2674', 1),  # sheet=S6F src=r12c01
        ('MN2673', 2),  # sheet=S6F src=r12c00
    ],
    'Wight': [
        ('MN0570', 0),  # sheet=M3 src=r04c11
        ('MN0091', 1),  # sheet=M1 src=r05c10
        ('MN0090', 2),  # sheet=M1 src=r05c09
    ],
    'Wraith': [
        ('MN0588', 0),  # sheet=M3 src=r05c13
        ('MN2138', 1),  # sheet=S6C src=r00c08
        ('MN2153', 2),  # sheet=S6C src=r01c09
    ],
    'Wyvern': [
        ('MN0740', 0),  # sheet=M3 src=r15c05
        ('MN2411', 1),  # sheet=S6D src=r08c09
        ('MN2413', 2),  # sheet=S6D src=r08c11
    ],
    'Young Dragon': [
        ('MN1823', 0),  # sheet=S6A src=r01c00
        ('MN1810', 1),  # sheet=S6A src=r00c00
        ('MN1832', 2),  # sheet=S6A src=r02c04
    ],
    'Zombie': [
        ('MN0073', 0),  # sheet=M1 src=r04c08
        ('MN0060', 1),  # sheet=M1 src=r03c11
        ('MN0076', 2),  # sheet=M1 src=r04c11
    ],

    # ------------------------------------------------------------------
    # Deep-descent bestiary (tiers 11-15) -- reserve sprites promoted to
    # in-game for the floors-24-49 monster overhaul. One variant each.
    # ------------------------------------------------------------------
    'Gloomback Bear': [
        ('MN2668', 0),  # sheet=S6F src=r11c09 (reserve-promoted)
    ],
    'Voidspawn Brute': [
        ('MN2593', 0),  # sheet=S6F src=r06c12 (reserve-promoted)
    ],
    'Cinder Serpent': [
        ('MN2427', 0),  # sheet=S6D src=r09c09 (reserve-promoted)
    ],
    'Sporelord Myconid': [
        ('MN2757', 0),  # sheet=S6G src=r03c02 (reserve-promoted)
    ],
    'Bonepicker Reaver': [
        ('MN2535', 0),  # sheet=S6F src=r02c12 (reserve-promoted)
    ],
    'Ridgeback Wyvern': [
        ('MN2421', 0),  # sheet=S6D src=r09c03 (reserve-promoted)
    ],
    'Iron Vanguard': [
        ('MN2601', 0),  # sheet=S6F src=r07c05 (reserve-promoted)
    ],
    'Rimebound Djinn': [
        ('MN2626', 0),  # sheet=S6F src=r08c14 (reserve-promoted)
    ],
    'Cinderborn Efreet': [
        ('MN2627', 0),  # sheet=S6F src=r08c15 (reserve-promoted)
    ],
    'Hollow Lich': [
        ('MN2614', 0),  # sheet=S6F src=r08c02 (reserve-promoted)
    ],
    'Emberscale Drake': [
        ('MN2691', 0),  # sheet=S6F src=r13c02 (reserve-promoted)
    ],
    'Gnashing Horror': [
        ('MN2638', 0),  # sheet=S6F src=r09c10 (reserve-promoted)
    ],
    'Abyssal Fiend': [
        ('MN3452', 0),  # sheet=S6J src=r06c15 (reserve-promoted)
    ],
    'Illithid Overmind': [
        ('MN3438', 0),  # sheet=S6J src=r05c12 (reserve-promoted)
    ],
    'Hundred-Eyed Watcher': [
        ('MN3348', 0),  # sheet=S6I src=r14c12 (reserve-promoted)
    ],
    'Necrarch Lich': [
        ('MN3468', 0),  # sheet=S6J src=r08c04 (reserve-promoted)
    ],
    'Graven Colossus': [
        ('MN3526', 0),  # sheet=S6J src=r11c15 (reserve-promoted)
    ],
    'Cryptborn Wraith': [
        ('MN2562', 0),  # sheet=S6F src=r04c11 (reserve-promoted)
    ],
    'Abyssal Archfiend': [
        ('MN3479', 0),  # sheet=S6J src=r08c15 (reserve-promoted)
    ],
    'Starspawn Aberration': [
        ('MN3400', 0),  # sheet=S6J src=r02c14 (reserve-promoted)
    ],
    'Crimson Wyrmlord': [
        ('MN2692', 0),  # sheet=S6F src=r13c03 (reserve-promoted)
    ],
    'Sepulchral Lich': [
        ('MN2813', 0),  # sheet=S6G src=r07c04 (reserve-promoted)
    ],
    'Maw of the Deep': [
        ('MN3414', 0),  # sheet=S6J src=r03c15 (reserve-promoted)
    ],
    'Glacian Titan': [
        ('MN3543', 0),  # sheet=S6J src=r13c00 (reserve-promoted)
    ],
    'Elder Starspawn': [
        ('MN3422', 0),  # sheet=S6J src=r04c08 (reserve-promoted)
    ],
    'Infernal Warlord': [
        ('MN3469', 0),  # sheet=S6J src=r08c05 (reserve-promoted)
    ],
    'Voidmaw Devourer': [
        ('MN3343', 0),  # sheet=S6I src=r14c07 (reserve-promoted)
    ],
    'Cataclysm Fiend': [
        ('MN3490', 0),  # sheet=S6J src=r09c10 (reserve-promoted)
    ],
    'Nightmare Lich': [
        ('MN3484', 0),  # sheet=S6J src=r09c04 (reserve-promoted)
    ],
    'Soulflayer Wraith': [
        ('MN3496', 0),  # sheet=S6J src=r10c00 (reserve-promoted)
    ],
}
