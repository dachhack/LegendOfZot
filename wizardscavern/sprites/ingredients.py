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
    # Dwarf mining ore drops. Each reuses a distinct in-pool gem / mineral
    # / metal sprite, hand-picked from a rendered montage for a fitting
    # colour + a shape distinct from the other ores (no two share a pid).
    'Iron Chunk': [
        ('IN0535', 0),  # Iron Bark -- rough grey-brown chunk
    ],
    'Copper Nugget': [
        ('LN0085', 0),  # copper-brown nugget pouch
    ],
    'Stone Shard': [
        ('PR0099', 0),  # Stone Flower -- cyan crystal cluster
    ],
    'Silver Vein': [
        ('IN0255', 0),  # Quicksilver Drop -- silver bead
    ],
    'Gold Flake': [
        ('CR0060', 0),  # bright gold wisp
    ],
    'Coal Ember': [
        ('CR0009', 0),  # dark coal cluster
    ],
    'Mithril Shard': [
        ('TR0164', 0),  # blue gem -- light mithril
    ],
    'Ruby Fragment': [
        ('TR0163', 0),  # red gem
    ],
    'Diamond Chip': [
        ('TR0165', 0),  # bright cut gem
    ],
    'Adamantine Dust': [
        ('CR0015', 0),  # sparkling dust
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
