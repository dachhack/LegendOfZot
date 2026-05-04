# Room Sprites

Every room type the game can render, what it does, and where its sprite currently comes from.
Source: `wizardscavern/sprite_data.py` (`_ROOM_MAP`, `_VARIANT_MAP`, `_CUSTOM_ROOM_SPRITES`),
`wizardscavern/game_systems.py` (`_trigger_room_interaction`).

---

## Base Room Types (20)

Single-letter codes drawn on the dungeon grid. Each code gets its own sprite.

| Code | Name | Function | Sprite source |
|---|---|---|---|
| `C` | **Chest** | Tap to loot — gold + items | `Chest0` (1, 0) — dark chest |
| `A` | **Altar** | BUC blessings, sacrifice items | `Decor1` (0, 20) — shrine |
| `P` | **Pool / Fountain** | Drink for random buff/debuff | `Decor1` (0, 21) — fountain |
| `L` | **Library** | Read tomes — XP / spell drops | `Decor1` (5, 4) — bookshelf |
| `V` | **Vendor / Shop** | Buy and sell items | `Decor1` (5, 6) — throne/chair |
| `W` | **Warp** | Teleport across the floor | `Door0` (1, 5) — portal swirl |
| `T` | **Tomb** | Loot a sarcophagus (BUC-rolled) | `Decor1` (0, 18) — skull/bones |
| `N` | **Dungeon (locked door)** | Themed mini-dungeon entrance | `Door0` (2, 1) — locked door |
| `G` | **Garden** | Forage crafting ingredients | _custom 16px sprite_ (stored as base64 in `_CUSTOM_ROOM_SPRITES['G']`) |
| `O` | **Oracle** | Pay for a quest hint | `Door0` (5, 5) — mystic portal |
| `D` | **Stairs Down** | Descend one floor | `Tile0` (7, 3) — tile stairs |
| `U` | **Stairs Up** | Ascend one floor | `Tile0` (5, 3) — tile stairs |
| `E` | **Entrance** | Floor-1 entry portal | `Door0` (0, 5) — portal |
| `F` | **Shrine of the Fallen** | Memorial — heal / buff for a price | `Decor1` (1, 20) — memorial shrine |
| `Z` | **Zotle Puzzle** | Word-puzzle mini-game | `Door0` (3, 5) — mystic portal |
| `B` | **Blacksmith** | Repair / upgrade gear | `Decor1` (1, 11) — anvil/forge |
| `Q` | **Alchemist (Quest)** | Brew potions, pursue side-quests | `Decor1` (3, 4) — alchemist setup |
| `K` | **War Room** | Combat-prep buffs / planning | `Decor1` (5, 11) — war banner / table |
| `X` | **Taxidermist** | Trade monster trophies for accessories | `Decor1` (2, 12) — workbench |
| `M` | **Monster** | Combat encounter | _no room sprite — monster sprite is shown instead_ |

---

## Special Variants (8)

Triggered by specific game state (usually Rune ownership). They override the base sprite.

| Variant key | Replaces | Name | Function | Sprite source |
|---|---|---|---|---|
| `legendary` | `C` chest | **Legendary Chest** | Better loot — appears once per game (battle Rune) | `Chest0` (4, 0) — ornate chest |
| `ancient` | `P` pool | **Ancient Waters** | Permanent buff (reflection Rune) | `Decor1` (1, 21) — special fountain |
| `master` | `N` dungeon | **Master Dungeon** | Locked-door dungeon (secrets Rune) | `Door0` (4, 1) — ornate locked door |
| `cursed` | `T` tomb | **Cursed Tomb** | Hard tomb encounter (eternity Rune) | `Decor1` (2, 18) — different skull |
| `codex` | `L` library | **Codex of Zot** | Reveals lore (knowledge Rune) | `Decor1` (6, 4) — different bookshelf |
| `shard_vault` | `V` vendor slot | **Shard Vault** | Boss arena, drops a Shard | `Door0` (4, 0) — dark vault door |
| `fey_garden` | `G` garden | **Fey Garden** | Rare ingredient pool (high-tier) | _custom 16px sprite_ (stored as base64 in `_CUSTOM_ROOM_SPRITES['fey_garden']`) |
| `champion` | `M` monster | **Champion Arena** | Champion monster fight (battle Rune) | `Door0` (7, 5) — special portal |

---

## Sheets currently used by rooms

- **`Chest0`** — chests (base + legendary)
- **`Decor1`** — altar, pool, library, vendor, tomb, shrine, blacksmith, alchemist, war room, taxidermist, ancient/cursed/codex variants
- **`Door0`** — warp, dungeon, oracle, entrance, zotle, shard vault, master dungeon, champion arena
- **`Tile0`** — stairs up/down

Plus 2 custom hand-drawn sprites in `_CUSTOM_ROOM_SPRITES`: `G` (garden) and `fey_garden`.

---

## Totals
- **20 base room types** (19 with sprites + 1 monster room that uses the monster sprite)
- **8 special variants**
- **2 hand-drawn custom rooms**
- **= 28 distinct sprite slots** if every variant gets its own art.

A new room sprite sheet should ideally cover all 28 slots, or at minimum the 20 base types — variants can be tints/overlays of their base sprite.
