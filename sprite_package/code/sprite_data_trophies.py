"""
Sprite map for category: trophies

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _TROPHIES_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 31
  total sprite variants: 91

Use: pick a deterministic variant per game-instance:
    variants = _TROPHIES_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_TROPHIES_MAP = {
    'Ant Mandible': [
        ('TP0217', 0),  # sheet=MP3 src=r00c00
        ('TP0218', 1),  # sheet=MP3 src=r00c01
        ('TP0220', 2),  # sheet=MP3 src=r00c03
    ],
    'Basilisk Scale': [
        ('TP0265', 0),  # sheet=MP3 src=r04c00
        ('TP0266', 1),  # sheet=MP3 src=r04c01
        ('TP0267', 2),  # sheet=MP3 src=r04c02
    ],
    'Beholder Eyestalk': [
        ('TP0282', 0),  # sheet=MP3 src=r05c05
        ('TP0280', 1),  # sheet=MP3 src=r05c03
        ('TP0281', 2),  # sheet=MP3 src=r05c04
    ],
    'Cyclops Eye': [
        ('TP0283', 0),  # sheet=MP3 src=r05c06
        ('TP0284', 1),  # sheet=MP3 src=r05c07
        ('TP0287', 2),  # sheet=MP3 src=r05c10
    ],
    'Displacer Beast Hide': [
        ('TP0254', 0),  # sheet=MP3 src=r03c01
        ('TP0258', 1),  # sheet=MP3 src=r03c05
        ('TP0257', 2),  # sheet=MP3 src=r03c04
    ],
    'Dragonfly Wing Dust': [
        ('TP0221', 0),  # sheet=MP3 src=r00c04
        ('TP0222', 1),  # sheet=MP3 src=r00c05
        ('TP0224', 2),  # sheet=MP3 src=r00c07
    ],
    'Dung Beetle Carapace': [
        ('TP0226', 0),  # sheet=MP3 src=r00c09
        ('TP0227', 1),  # sheet=MP3 src=r00c10
        ('TP0228', 2),  # sheet=MP3 src=r00c11
    ],
    'Earthworm Segment': [
        ('TP0229', 0),  # sheet=MP3 src=r01c00
        ('TP0066', 1),  # sheet=MP1 src=r05c05
        ('TP0069', 2),  # sheet=MP1 src=r05c08
    ],
    'Elder Brain Lobe': [
        ('TP0068', 0),  # sheet=MP1 src=r05c07
        ('TP0293', 1),  # sheet=MP3 src=r06c04
        ('TP0072', 2),  # sheet=MP1 src=r05c11
    ],
    'Firefly Lantern Gland': [
        ('TP0234', 0),  # sheet=MP3 src=r01c05
        ('TP0015', 1),  # sheet=MP1 src=r01c02
        ('TP0016', 2),  # sheet=MP1 src=r01c03
    ],
    'Fly Swarm Wings': [
        ('TP0238', 0),  # sheet=MP3 src=r01c09
        ('TP0239', 1),  # sheet=MP3 src=r01c10
        ('TP0237', 2),  # sheet=MP3 src=r01c08
    ],
    'Frost Giant Shard': [
        ('TP0321', 0),  # sheet=MP3 src=r08c08
        ('TP0322', 1),  # sheet=MP3 src=r08c09
        ('TP0320', 2),  # sheet=MP3 src=r08c07
    ],
    'Giant Spider Silk': [
        ('TP0355', 0),  # sheet=MP3 src=r11c06
    ],
    'Griffin Feather': [
        ('TP0315', 0),  # sheet=MP3 src=r08c02
        ('TP0316', 1),  # sheet=MP3 src=r08c03
        ('TP0313', 2),  # sheet=MP3 src=r08c00
    ],
    'Hell Hound Ember': [
        ('TP0307', 0),  # sheet=MP3 src=r07c06
        ('TP0308', 1),  # sheet=MP3 src=r07c07
        ('TP0309', 2),  # sheet=MP3 src=r07c08
    ],
    'Hill Giant Knuckle': [
        ('TP0325', 0),  # sheet=MP3 src=r09c00
        ('TP0326', 1),  # sheet=MP3 src=r09c01
        ('TP0329', 2),  # sheet=MP3 src=r09c04
    ],
    'Manticore Spine': [
        ('TP0331', 0),  # sheet=MP3 src=r09c06
        ('TP0334', 1),  # sheet=MP3 src=r09c09
        ('TP0335', 2),  # sheet=MP3 src=r09c10
    ],
    'Mind Flayer Tendril': [
        ('TP0296', 0),  # sheet=MP3 src=r06c07
        ('TP0297', 1),  # sheet=MP3 src=r06c08
        ('TP0299', 2),  # sheet=MP3 src=r06c10
    ],
    'Mummy Wrappings': [
        ('TP0342', 0),  # sheet=MP3 src=r10c05
        ('TP0341', 1),  # sheet=MP3 src=r10c04
        ('TP0337', 2),  # sheet=MP3 src=r10c00
    ],
    'Naga Scale': [
        ('TP0276', 0),  # sheet=MP3 src=r04c11
        ('TP0274', 1),  # sheet=MP3 src=r04c09
        ('TP0272', 2),  # sheet=MP3 src=r04c07
    ],
    'Owlbear Feather': [
        ('TP0301', 0),  # sheet=MP3 src=r07c00
        ('TP0305', 1),  # sheet=MP3 src=r07c04
        ('TP0304', 2),  # sheet=MP3 src=r07c03
    ],
    'Pill Bug Shell Plate': [
        ('TP0242', 0),  # sheet=MP3 src=r02c01
        ('TP0244', 1),  # sheet=MP3 src=r02c03
        ('TP0243', 2),  # sheet=MP3 src=r02c02
    ],
    'Roc Talon': [
        ('TP0112', 0),  # sheet=MP2 src=r00c03
        ('TP0113', 1),  # sheet=MP2 src=r00c04
        ('TP0116', 2),  # sheet=MP2 src=r00c07
    ],
    'Royal Chitin Crown': [
        ('TP0495', 0),  # sheet=BC1 src=r02c03
        ('TP0502', 1),  # sheet=BC1 src=r02c10
        ('TP0511', 2),  # sheet=BC1 src=r03c07
    ],
    'Skeleton Bone Dust': [
        ('TP0057', 0),  # sheet=MP1 src=r04c08
        ('TP0349', 1),  # sheet=MP3 src=r11c00
        ('TP0402', 2),  # sheet=MP4 src=r03c06
    ],
    'Snail Shell Shard': [
        ('TP0080', 0),  # sheet=MP1 src=r06c07
        ('TP0440', 1),  # sheet=MP4 src=r06c08
        ('TP0430', 2),  # sheet=MP4 src=r05c10
    ],
    'Stinkbug Gland': [
        ('TP0017', 0),  # sheet=MP1 src=r01c04
        ('TP0018', 1),  # sheet=MP1 src=r01c05
        ('TP0020', 2),  # sheet=MP1 src=r01c07
    ],
    'Titan Beetle Horn': [
        ('TP0036', 0),  # sheet=MP1 src=r02c11
        ('TP0169', 1),  # sheet=MP2 src=r05c00
        ('TP0157', 2),  # sheet=MP2 src=r04c00
    ],
    'Wight Finger': [
        ('TP0365', 0),  # sheet=MP4 src=r00c05
        ('TP0373', 1),  # sheet=MP4 src=r01c01
        ('TP0377', 2),  # sheet=MP4 src=r01c05
    ],
    'Wyvern Barb': [
        ('TP0425', 0),  # sheet=MP4 src=r05c05
        ('TP0437', 1),  # sheet=MP4 src=r06c05
        ('TP0436', 2),  # sheet=MP4 src=r06c04
    ],
    'Young Dragon Scale': [
        ('TP0137', 0),  # sheet=MP2 src=r02c04
        ('TP0144', 1),  # sheet=MP2 src=r02c11
        ('TP0134', 2),  # sheet=MP2 src=r02c01
    ],
}
