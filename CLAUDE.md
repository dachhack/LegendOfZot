# CLAUDE.md

## Sprite Reference Guides

When the user needs to view or update sprite assignments:

1. **Regenerate annotated sprite grid images and markdown reference files** by running the Python script pattern:
   - Parse `sprite_data.py` to extract sheet base64 data and all `_ROOM_MAP`, `_VARIANT_MAP`, and monster `_MAP` coordinate entries
   - Use PIL to decode each sheet, render a scaled grid (4x scale, 16px cells) with:
     - Green outline + bright = used/assigned sprites
     - Dim + grey outline = unused/available sprites
     - Coordinate labels (col,row) on every cell, assignment names on used cells
   - Output annotated PNGs per sheet and markdown files with summary tables + embedded images

2. **Generated files** (commit to branch, viewable on GitHub mobile):
   - `ROOM_SPRITES.md` + `room_sprites_<SheetName>.png` — room sprite sheets (Chest0, Decor1, Door0, Tile0)
   - `MONSTER_SPRITES.md` + `monster_sprites_<SheetName>.png` — monster sprite sheets (16 creature sheets)

3. **To assign a new sprite to a room:**
   - Add entry to `_ROOM_MAP` in `sprite_data.py` `generate_room_sprite_html()` (~line 6310)
   - Add `generate_room_sprite_html('<code>')` call in the room's interaction box HTML in `cavernwiz_0_1_2_20_4.py`
   - Use flex layout pattern: sprite div (flex-shrink:0) on left, title + description div on right
   - Regenerate the reference markdown/images and push for review
