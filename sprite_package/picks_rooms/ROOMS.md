# Room Sprites (round 4 — 27 slots × 3 variants each = 81 sprite assignments)

Every room type the game can render, what it does, and which sprite variants are assigned.
Source: 13 newly-uploaded sheets (S8A–S8M), sliced at native cell size, downsampled to 96×96 NEAREST.

Each slot has up to 3 variants. The renderer should pick deterministically per-room
(e.g. `hash((room.floor, room.x, room.y)) % len(variants)`) so a room's appearance is
stable across re-renders, but the dungeon shows variety across rooms of the same type.

## Source sheets

| Sheet ID | File | Native cell |
|---|---|---|
| `S8A` | `Doors_Floors1.png` | 128px |
| `S8B` | `Doors_Floors2.png` | 128px |
| `S8C` | `Doors_Floors3.png` | 128px |
| `S8D` | `Doors_Floors4.png` | 128px |
| `S8E` | `Doors_Floors5.png` | 128px |
| `S8F` | `Doors_Floors6.png` | 128px |
| `S8G` | `Misc1.png` | 128px |
| `S8H` | `Misc2.png` | 128px |
| `S8I` | `Misc3.png` | 128px |
| `S8J` | `S8J.png` | 128px |
| `S8K` | `S8K.png` | 128px |
| `S8L` | `S8L.png` | 128px |
| `S8M` | `S8M.png` | 64px |

## Base Room Types (19)

Single-letter codes drawn on the dungeon grid.

| Code | Name | Function | Variants (sheet, row, col) |
|---|---|---|---|
| `C` | Chest | Tap to loot — gold + items | `S8B(0,6)` · `S8C(3,10)` · `S8E(0,10)` |
| `A` | Altar | BUC blessings, sacrifice items | `S8K(6,12)` · `S8L(3,10)` · `S8L(6,14)` |
| `P` | Pool / Fountain | Drink for random buff/debuff | `S8E(7,11)` · `S8E(7,14)` · `S8E(7,15)` |
| `L` | Library | Read tomes — XP / spell drops | `S8A(1,6)` · `S8A(2,6)` · `S8A(2,7)` |
| `V` | Vendor / Shop | Buy and sell items | `S8A(12,4)` · `S8A(12,5)` · `S8A(13,4)` |
| `W` | Warp | Teleport across the floor | `S8A(3,8)` · `S8B(5,13)` · `S8G(7,14)` |
| `T` | Tomb | Loot a sarcophagus (BUC-rolled) | `S8B(5,7)` · `S8C(5,5)` · `S8C(5,7)` |
| `N` | Dungeon (locked door) | Themed mini-dungeon entrance | `S8A(10,5)` · `S8A(11,1)` · `S8A(11,3)` |
| `G` | Garden | Forage crafting ingredients | `S8B(6,7)` · `S8I(2,9)` · `S8I(2,10)` |
| `O` | Oracle | Pay for a quest hint | `S8A(3,14)` · `S8B(4,15)` · `S8G(7,15)` |
| `D` | Stairs Down | Descend one floor | `S8M(2,15)` · `S8M(4,15)` · `S8M(8,0)` |
| `U` | Stairs Up | Ascend one floor | `S8M(0,11)` · `S8M(1,13)` · `S8M(1,14)` |
| `E` | Entrance | Floor-1 entry portal | `S8B(5,15)` · `S8J(10,13)` · `S8K(9,12)` |
| `F` | Shrine of the Fallen | Memorial — heal / buff for a price | `S8I(13,9)` · `S8I(13,10)` · `S8K(4,15)` |
| `Z` | Zotle Puzzle | Word-puzzle mini-game | `S8J(14,14)` · `S8K(7,13)` · `S8K(14,14)` |
| `B` | Blacksmith | Repair / upgrade gear | `S8A(3,10)` · `S8A(3,11)` · `S8A(5,10)` |
| `Q` | Alchemist | Brew potions, pursue side-quests | `S8A(1,4)` · `S8A(1,7)` · `S8B(1,7)` |
| `K` | War Room | Combat-prep buffs / planning | `S8F(11,11)` · `S8K(10,6)` · `S8K(11,6)` |
| `X` | Taxidermist | Trade monster trophies for accessories | `S8K(3,7)` · `S8L(7,4)` · `S8L(7,5)` |

Room code `M` (Monster) does not have a room sprite — the monster sprite is rendered instead.

## Special Variants (8)

Triggered by specific game state (usually Rune ownership). Override the base sprite when active.

| Variant key | Replaces | Name | Function | Variants (sheet, row, col) |
|---|---|---|---|---|
| `legendary` | `C` | Legendary Chest | Better loot — appears once per game (battle Rune) | `S8J(3,8)` · `S8J(3,9)` · `S8J(3,12)` |
| `ancient` | `P` | Ancient Waters | Permanent buff (reflection Rune) | `S8D(7,4)` · `S8D(11,5)` · `S8E(7,12)` |
| `master` | `N` | Master Dungeon | Locked-door dungeon (secrets Rune) | `S8K(11,0)` · `S8K(11,1)` · `S8K(11,3)` |
| `cursed` | `T` | Cursed Tomb | Hard tomb encounter (eternity Rune) | `S8K(3,14)` · `S8L(3,8)` · `S8L(3,9)` |
| `codex` | `L` | Codex of Zot | Reveals lore (knowledge Rune) | `S8M(13,4)` · `S8M(13,11)` · `S8M(14,11)` |
| `shard_vault` | `V` | Shard Vault | Boss arena, drops a Shard | `S8K(4,14)` · `S8K(5,15)` · `S8L(4,15)` |
| `fey_garden` | `G` | Fey Garden | Rare ingredient pool (high-tier) | `S8D(6,7)` · `S8D(7,7)` · `S8I(0,15)` |
| `champion` | `M` | Champion Arena | Champion monster fight (battle Rune) | `S8K(4,8)` · `S8K(10,7)` · `S8L(4,8)` |

## Totals
- 19 base room types + 1 monster room = 20 rooms
- 8 special variants
- **81 sprite assignments** (27 fully-filled slots × 3 variants)

