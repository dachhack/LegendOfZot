"""
Sprite map for category: ingredients

Generated from <category>_library.json + canonical_pool_full.pkl.

Shape: _INGREDIENTS_MAP maps an item_name → list of (pid, variant_index) tuples.
Each pid resolves to a sprite in the canonical pool (lookup img_b64).

Stats:
  unique items: 22
  total sprite variants: 22

Use: pick a deterministic variant per game-instance:
    variants = _INGREDIENTS_MAP[item_name]                  # [(pid, vi), ...]
    pid, vi = variants[hash(seed) % len(variants)]
    img = canonical_pool[pid]["img_b64"]
"""

_INGREDIENTS_MAP = {
    # Dwarf mining ore drops. Reserve sprites hand-picked via the mining
    # picker (sprite_package/picks_mining) and keyed to transparent by
    # apply_mining_sprites.py; each is a distinct gem / mineral / metal.
    'Iron Chunk': [
        ('PH0189_PH2', 0),  # reserve pick, keyed transparent
    ],
    'Copper Nugget': [
        ('PH0246_PH2', 0),  # reserve pick, keyed transparent
    ],
    'Stone Shard': [
        ('PH0198_PH2', 0),  # reserve pick, keyed transparent
    ],
    'Silver Vein': [
        ('PH0209_PH2', 0),  # reserve pick, keyed transparent
    ],
    'Gold Flake': [
        ('PH0207_PH2', 0),  # reserve pick, keyed transparent
    ],
    'Coal Ember': [
        ('PH0210_PH2', 0),  # reserve pick, keyed transparent
    ],
    'Mithril Shard': [
        ('PH0206_PH2', 0),  # reserve pick, keyed transparent
    ],
    'Ruby Fragment': [
        ('PH0178_PH2', 0),  # reserve pick, keyed transparent
    ],
    'Diamond Chip': [
        ('PH0152_PH2', 0),  # reserve pick, keyed transparent
    ],
    'Adamantine Dust': [
        ('CR0013_CR1', 0),  # reserve pick, keyed transparent -- rainbow dust
    ],
    'Crystal Dew': [
        ('IN0489', 0),  # sheet=IN6 src=r04c06
    ],
    'Dragon Heart Root': [
        ('IN0220', 0),  # sheet=IN3 src=r02c10
    ],
    'Dragon Scale': [
        ('IN0261', 0),  # sheet=IN3 src=r07c05
    ],
    'Essence Vial': [
        ('IN0242', 0),  # sheet=IN3 src=r05c04
    ],
    'Ethereal Moss': [
        ('IN0474', 0),  # sheet=IN6 src=r02c11
    ],
    'Fey Blossom': [
        ('PH0012', 0),  # sheet=PH1 src=PH1
    ],
    'Fire Pepper': [
        ('IN0021', 0),  # sheet=IN1 src=r01c08
    ],
    'Fire Root': [
        ('IN0133', 0),  # sheet=IN2 src=r03c00
    ],
    'Ghost Pepper': [
        ('IN0282', 0),  # sheet=IN4 src=r00c04
    ],
    'Healing Moss': [
        ('IN0350', 0),  # sheet=IN5 src=r00c00
    ],
    'Iron Bark': [
        ('IN0535', 0),  # sheet=IN7 src=r01c04
    ],
    'Moonpetal': [
        ('PH0002', 0),  # sheet=PH1 src=PH1
    ],
    'Moonwell Water': [
        ('IN0484', 0),  # sheet=IN6 src=r04c00
    ],
    'Phoenix Feather': [
        ('CR0060', 0),  # sheet=CR1 src=CR1
    ],
    'Quicksilver Drop': [
        ('IN0255', 0),  # sheet=IN3 src=r06c09
    ],
    'Shadow Leaf': [
        ('IN0451', 0),  # sheet=IN6 src=r00c11
    ],
    'Starbloom': [
        ('PH0080', 0),  # sheet=PH1 src=PH1
    ],
    'Starfall Dust': [
        ('CR0015', 0),  # sheet=CR1 src=CR1
    ],
    'Stone Flower': [
        ('PR0099', 0),  # sheet=PR1 src=PR1
    ],
    'Unicorn Tear': [
        ('IN0142', 0),  # sheet=IN2 src=r03c11
    ],
    'Void Essence': [
        ('CR0029', 0),  # sheet=CR1 src=CR1
    ],
    'Wisdom Moss': [
        ('IN0360', 0),  # sheet=IN5 src=r00c10
    ],
    'Aphid Honeydew': [
        ('IN0231', 0),  # picked via sprite_package/picks_recent
    ],
    'Chitin Moss': [
        ('IN0359', 0),  # picked via sprite_package/picks_recent
    ],
    'Dew Silk': [
        ('IN0235', 0),  # picked via sprite_package/picks_recent
    ],
    'Mycelium Thread': [
        ('IN0225', 0),  # picked via sprite_package/picks_recent
    ],
    'Nectar Bead': [
        ('IN0228', 0),  # picked via sprite_package/picks_recent
    ],
    'Pollen Cluster': [
        ('CR0009', 0),  # picked via sprite_package/picks_recent
    ],
    'Spore Cap': [
        ('PR0103', 0),  # picked via sprite_package/picks_recent
    ],
}
