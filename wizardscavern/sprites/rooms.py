# === Generated room sprite picks (round 4 — final) ===
# 27 slots × up to 3 variants each = 81 sprite assignments
# Source: 13 sheets (S8A-S8M), sliced at native cell sizes,
# downsampled to 96x96 NEAREST.
#
# Sheet → file map:
#   S8A: Doors_Floors1.png  (native cell=128px)
#   S8B: Doors_Floors2.png  (native cell=128px)
#   S8C: Doors_Floors3.png  (native cell=128px)
#   S8D: Doors_Floors4.png  (native cell=128px)
#   S8E: Doors_Floors5.png  (native cell=128px)
#   S8F: Doors_Floors6.png  (native cell=128px)
#   S8G: Misc1.png  (native cell=128px)
#   S8H: Misc2.png  (native cell=128px)
#   S8I: Misc3.png  (native cell=128px)
#   S8J: S8J.png  (native cell=128px)
#   S8K: S8K.png  (native cell=128px)
#   S8L: S8L.png  (native cell=128px)
#   S8M: S8M.png  (native cell=64px)
#
# Each slot value is a LIST of (sheet_id, row, col) variants.
# The renderer should deterministically pick one variant per room
# (e.g. hash(room.id) % len(variants)) so a room's sprite is stable
# across re-renders but variants distribute across the dungeon.

# Native cell px per sheet — needed at slice time, not at render time.
_SHEET_NATIVE_CELL = {
    'S8A': 128,
    'S8B': 128,
    'S8C': 128,
    'S8D': 128,
    'S8E': 128,
    'S8F': 128,
    'S8G': 128,
    'S8H': 128,
    'S8I': 128,
    'S8J': 128,
    'S8K': 128,
    'S8L': 128,
    'S8M': 64,
}

# Base rooms (19) — primary sprite key for each room type
_ROOM_MAP = {
    # Chest
    'C': [
        ('S8B',  0,  6),  # S8B_r00c06
        ('S8C',  3, 10),  # S8C_r03c10
        ('S8E',  0, 10),  # S8E_r00c10
    ],
    # Altar
    'A': [
        ('S8K',  6, 12),  # S8K_r06c12
        ('S8L',  3, 10),  # S8L_r03c10
        ('S8L',  6, 14),  # S8L_r06c14
    ],
    # Pool / Fountain
    'P': [
        ('S8E',  7, 11),  # S8E_r07c11
        ('S8E',  7, 14),  # S8E_r07c14
        ('S8E',  7, 15),  # S8E_r07c15
    ],
    # Library
    'L': [
        ('S8A',  1,  6),  # S8A_r01c06
        ('S8A',  2,  6),  # S8A_r02c06
        ('S8A',  2,  7),  # S8A_r02c07
    ],
    # Vendor / Shop
    'V': [
        ('S8A', 12,  4),  # S8A_r12c04
        ('S8A', 12,  5),  # S8A_r12c05
        ('S8A', 13,  4),  # S8A_r13c04
    ],
    # Warp
    'W': [
        ('S8A',  3,  8),  # S8A_r03c08
        ('S8B',  5, 13),  # S8B_r05c13
        ('S8G',  7, 14),  # S8G_r07c14
    ],
    # Tomb
    'T': [
        ('S8B',  5,  7),  # S8B_r05c07
        ('S8C',  5,  5),  # S8C_r05c05
        ('S8C',  5,  7),  # S8C_r05c07
    ],
    # Dungeon (locked)
    'N': [
        ('S8A', 10,  5),  # S8A_r10c05
        ('S8A', 11,  1),  # S8A_r11c01
        ('S8A', 11,  3),  # S8A_r11c03
    ],
    # Garden
    'G': [
        ('S8B',  6,  7),  # S8B_r06c07
        ('S8I',  2,  9),  # S8I_r02c09
        ('S8I',  2, 10),  # S8I_r02c10
    ],
    # Oracle
    'O': [
        ('S8A',  3, 14),  # S8A_r03c14
        ('S8B',  4, 15),  # S8B_r04c15
        ('S8G',  7, 15),  # S8G_r07c15
    ],
    # Stairs Down
    'D': [
        ('S8M',  2, 15),  # S8M_r02c15
        ('S8M',  4, 15),  # S8M_r04c15
        ('S8M',  8,  0),  # S8M_r08c00
    ],
    # Stairs Up
    'U': [
        ('S8M',  0, 11),  # S8M_r00c11
        ('S8M',  1, 13),  # S8M_r01c13
        ('S8M',  1, 14),  # S8M_r01c14
    ],
    # Entrance
    'E': [
        ('S8B',  5, 15),  # S8B_r05c15
        ('S8J', 10, 13),  # S8J_r10c13
        ('S8K',  9, 12),  # S8K_r09c12
    ],
    # Shrine of the Fallen
    'F': [
        ('S8I', 13,  9),  # S8I_r13c09
        ('S8I', 13, 10),  # S8I_r13c10
        ('S8K',  4, 15),  # S8K_r04c15
    ],
    # Zotle Puzzle
    'Z': [
        ('S8J', 14, 14),  # S8J_r14c14
        ('S8K',  7, 13),  # S8K_r07c13
        ('S8K', 14, 14),  # S8K_r14c14
    ],
    # Blacksmith
    'B': [
        ('S8A',  3, 10),  # S8A_r03c10
        ('S8A',  3, 11),  # S8A_r03c11
        ('S8A',  5, 10),  # S8A_r05c10
    ],
    # Alchemist
    'Q': [
        ('S8A',  1,  4),  # S8A_r01c04
        ('S8A',  1,  7),  # S8A_r01c07
        ('S8B',  1,  7),  # S8B_r01c07
    ],
    # War Room
    'K': [
        ('S8F', 11, 11),  # S8F_r11c11
        ('S8K', 10,  6),  # S8K_r10c06
        ('S8K', 11,  6),  # S8K_r11c06
    ],
    # Taxidermist
    'X': [
        ('S8K',  3,  7),  # S8K_r03c07
        ('S8L',  7,  4),  # S8L_r07c04
        ('S8L',  7,  5),  # S8L_r07c05
    ],
    # 'M' (Monster) — no room sprite, monster sprite is rendered instead.
}

# Special variants (8) — override base sprite when room is upgraded
_VARIANT_MAP = {
    # Legendary Chest
    'legendary': [
        ('S8J',  3,  8),  # S8J_r03c08
        ('S8J',  3,  9),  # S8J_r03c09
        ('S8J',  3, 12),  # S8J_r03c12
    ],
    # Ancient Waters
    'ancient': [
        ('S8D',  7,  4),  # S8D_r07c04
        ('S8D', 11,  5),  # S8D_r11c05
        ('S8E',  7, 12),  # S8E_r07c12
    ],
    # Master Dungeon
    'master': [
        ('S8K', 11,  0),  # S8K_r11c00
        ('S8K', 11,  1),  # S8K_r11c01
        ('S8K', 11,  3),  # S8K_r11c03
    ],
    # Cursed Tomb
    'cursed': [
        ('S8K',  3, 14),  # S8K_r03c14
        ('S8L',  3,  8),  # S8L_r03c08
        ('S8L',  3,  9),  # S8L_r03c09
    ],
    # Codex of Zot
    'codex': [
        ('S8M', 13,  4),  # S8M_r13c04
        ('S8M', 13, 11),  # S8M_r13c11
        ('S8M', 14, 11),  # S8M_r14c11
    ],
    # Shard Vault
    'shard_vault': [
        ('S8K',  4, 14),  # S8K_r04c14
        ('S8K',  5, 15),  # S8K_r05c15
        ('S8L',  4, 15),  # S8L_r04c15
    ],
    # Fey Garden
    'fey_garden': [
        ('S8D',  6,  7),  # S8D_r06c07
        ('S8D',  7,  7),  # S8D_r07c07
        ('S8I',  0, 15),  # S8I_r00c15
    ],
    # Champion Arena
    'champion': [
        ('S8K',  4,  8),  # S8K_r04c08
        ('S8K', 10,  7),  # S8K_r10c07
        ('S8L',  4,  8),  # S8L_r04c08
    ],
}

# `_CUSTOM_ROOM_SPRITES` (the old base64-embedded G/fey_garden art)
# is no longer needed — both slots now use real sheet sprites.

# Renderer hint: if a slot has multiple variants, pick by hashing
# something stable about the room:
#   variants = _ROOM_MAP[code] or _VARIANT_MAP[variant_key]
#   sprite_idx = hash((room.floor, room.x, room.y)) % len(variants)
#   sheet, row, col = variants[sprite_idx]
