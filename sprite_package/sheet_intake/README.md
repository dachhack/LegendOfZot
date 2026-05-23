# sprite_package/sheet_intake/

Turn a raw **sprite sheet** into reserve sprites you can later assign to
game entities. Three steps, mirroring the existing pick -> apply flow.

```
sprite sheet ──slice_and_pick──▶ sheet_picker.html ──(you pick)──▶ sheet_selection.json
                                                                          │
                                                          add_to_reserve  ▼
                                  assets/sprites/reserve/<category>/  +  manifest + library
                                                                          │
                                                       (later) build_monster_picker.py
                                                          surfaces them as assignment candidates
```

## Step 1 — slice + pick

```bash
python3 sprite_package/sheet_intake/slice_and_pick.py \
    --sheet path/to/new_monsters.png \
    --cell-size 96 \
    --label S7A \
    --category monsters
```

- Carves the sheet into a grid and **auto-skips blank/transparent cells**.
- Give geometry as `--cell-size N` (square cells) **or** `--grid ROWSxCOLS`.
  Use `--margin` / `--spacing` for sheets with a border or gutters.
- Cells are NEAREST-resampled to `--out-size` (default 96; `0` keeps native).
- Stages cells under `staging/<label>/` and writes `sheet_picker.html`.

Open `sheet_picker.html` (works on mobile). **Every non-blank cell starts
selected** — tap to drop the junk (dupes, backgrounds, half-cut frames), then
**Save selection** to download `sheet_selection.json`. Put that file in this
directory.

## Step 2 — add the kept cells to the reserve

```bash
python3 sprite_package/sheet_intake/add_to_reserve.py --label S7A
# preview without writing:
python3 sprite_package/sheet_intake/add_to_reserve.py --label S7A --dry-run
```

- Auto-detects the category's PID prefix (e.g. `MN`) and numbers new sprites
  **above the global max** across the in-game pool *and* every reserve
  manifest, so PIDs never collide. Override with `--pid-prefix`.
- Copies kept cells to `assets/sprites/reserve/<category>/<PID>_<label>_<src>.png`
  and updates that category's `manifest.json` + `libraries/<category>_library.json`.

## Step 3 — persist (only when you want them on fresh checkouts)

`assets/sprites/` is gitignored, so new reserve PNGs live only locally until
you re-publish the asset bundle:

```bash
bash sprite_package/repack_bundle.sh   # -> wc_sprites_assets.zip
# then replace the asset on the sprite-assets-v1 GitHub Release
```

The local monster picker (`build_monster_picker.py`) surfaces the new reserve
sprites immediately without this step — re-publishing only matters for other
machines / fresh clones.

## Notes

- `staging/`, `sheet_picker.html`, and `sheet_selection.json` are per-run
  working files and are gitignored. The two `.py` scripts are the source.
- This adds sprites to the **reserve** (the candidate pool). To actually put
  one in the game, assign it to an entity via the relevant picker
  (`build_monster_picker.py`) + `apply_picks.py`, which promotes it from
  reserve to in-game.
