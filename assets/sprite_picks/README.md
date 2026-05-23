# assets/sprite_picks/

Per-pick PNG overlay over the external `sprite-assets-v1` bundle.

## What this dir is

Every PNG picked via `sprite_package/picks_recent/picker.html` lands here
when `apply_picks.py` runs. The dir is committed to git, organized as:

    assets/sprite_picks/<category>/<PID>_<Item_Name>_v0.png

The category mirrors the canonical sprite-pipeline category
(`accessories`, `bug_weapons`, `foods`, `ingredients`, `spells`, etc.).

## Why

The full sprite bundle (`wc_sprites_assets.zip` on the
`sprite-assets-v1` GitHub Release) is ~109 MB. Each picker round only
moves a handful of PNGs from `reserve/` to in-game — the actual delta
is 5-500 KB. Re-publishing the entire bundle per pick is a chore
(chunked upload + drag-drop via web UI).

This overlay solves it: per-pick PNGs (~10 KB each) get committed
straight to the repo, so `git push` ships them. The base bundle on the
release stays unchanged until you actively want to "compact" the
accumulated picks into a new base (quarterly, or whenever).

## How it plumbs in

  - `sprite_package/code/promote_all_sprites.py` reads this dir in
    addition to `assets/sprites/in_game/by_category/` when building
    the PID -> path index. Overlay entries win over the base bundle
    for the same PID.

  - `sprite_package/picks_recent/apply_picks.py` writes here as the
    canonical destination + mirrors into the local bundle's
    `in_game/by_category/` and `in_game/by_item/` views so
    `repack_bundle.sh` produces a consistent zip when you do want to
    re-publish.

## Fresh-checkout workflow

    git clone ...
    curl -L wc_sprites_assets.zip   # base bundle, 109 MB
    unzip -d assets/sprites/        # populate the gitignored bundle dir
    python3 sprite_package/code/promote_all_sprites.py \
        --in-game-dir assets/sprites/in_game \
        --reserve-dir assets/sprites/reserve

`promote_all_sprites.py` automatically detects this overlay dir and
combines it with the bundle. The resulting `canonical_pool_full.pkl`
has all chosen sprites whether they came from the base bundle or
this overlay.

## Cleanup / compaction

When the overlay grows large or you want a clean base for a new
release tag:

    1. bash sprite_package/repack_bundle.sh   # produces a fresh zip
       # that already includes the picks (mirrored into the bundle
       # by apply_picks.py)
    2. Upload the new zip to sprite-assets-v1 (or a v2 tag)
    3. `rm -rf assets/sprite_picks/<picked_pids>` -- they live in the
       base bundle now
    4. git commit
