# CLAUDE.md

## Sprite Reference Guides

When the user needs to view or update sprite assignments:

1. **Regenerate annotated sprite grid images and markdown reference files** by running the Python script pattern:
   - Parse `wizardscavern/sprite_data.py` to extract sheet base64 data and all `_ROOM_MAP`, `_VARIANT_MAP`, and monster `_MAP` coordinate entries
   - Use PIL to decode each sheet, render a scaled grid (4x scale, 16px cells) with:
     - Green outline + bright = used/assigned sprites
     - Dim + grey outline = unused/available sprites
     - Coordinate labels (col,row) on every cell, assignment names on used cells
   - Output annotated PNGs per sheet and markdown files with summary tables + embedded images

2. **Generated files** (commit to branch, viewable on GitHub mobile):
   - `ROOM_SPRITES.md` + `room_sprites_<SheetName>.png` — room sprite sheets (Chest0, Decor1, Door0, Tile0)
   - `MONSTER_SPRITES.md` + `monster_sprites_<SheetName>.png` — monster sprite sheets (16 creature sheets)

3. **To assign a new sprite to a room:**
   - Add entry to `_ROOM_MAP` in `wizardscavern/sprite_data.py` `generate_room_sprite_html()` (~line 6310)
   - Add `generate_room_sprite_html('<code>')` call in the room's interaction box HTML in `wizardscavern/app.py`
   - Use flex layout pattern: sprite div (flex-shrink:0) on left, title + description div on right
   - Regenerate the reference markdown/images and push for review

## Source of Truth

**IMPORTANT:** All game source code lives in `wizardscavern/`. Briefcase builds the APK directly from that package. There are no root-level copies to keep in sync — edit files in `wizardscavern/` and your changes will appear in the next APK build automatically.

**NEVER edit root-level .py files** (e.g. `cavernwiz_*.py`) — these are stale legacy copies and are NOT used by the build. The actual source files are:
- `wizardscavern/app.py` — main application, UI, and rendering
- `wizardscavern/game_systems.py` — inventory, crafting, game logic
- `wizardscavern/combat.py` — combat, journal, spells
- `wizardscavern/game_state.py` — global state
- `wizardscavern/sprite_data.py` — sprite sheets and mappings
