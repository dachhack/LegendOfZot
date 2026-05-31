# Mining sprite picker

Pick reserve sprites for the dwarf-mining items (10 ore ingredients + 4
Ioun Stones) and key them to transparent backgrounds.

## 1. Pull the reserve (from the `sprite-assets-v1` Release)

```sh
curl -L -o /tmp/wc_sprites_assets.zip \
  https://github.com/dachhack/LegendOfZot/releases/download/sprite-assets-v1/wc_sprites_assets.zip
unzip -q -o /tmp/wc_sprites_assets.zip \
  'wc_sprites_assets/reserve/treasures/*' \
  'wc_sprites_assets/reserve/ingredients/*' \
  'wc_sprites_assets/reserve/accessories/*' \
  'wc_sprites_assets/reserve/manifest.json' -d /tmp/wc_reserve/
```

## 2. Build + open the picker

```sh
python3 sprite_package/picks_mining/build_mining_picker.py \
  --reserve-dir /tmp/wc_reserve/wc_sprites_assets/reserve \
  --out /tmp/mining_sprite_picker.html
```

Open the HTML in a browser. Tap an item chip (top), then tap a sprite to
assign it; repeat for all 14. Hit **Save picks JSON** →
`mining_sprite_picks.json`.

## 3. Apply: key to transparent + promote + wire in

```sh
python3 sprite_package/picks_mining/apply_mining_sprites.py \
  --picks /path/to/mining_sprite_picks.json \
  --reserve-dir /tmp/wc_reserve/wc_sprites_assets/reserve \
  --pool wizardscavern/data/canonical_pool_full.pkl
```

This chroma-keys each picked sprite's dark background to transparent
(border-median key + edge despill via `../code/chroma_key.py`), promotes
the keyed webp into `canonical_pool_full.pkl` (`status="reserve"`, pid =
the reserve id), and rewrites the `(pid, 0)` tuple for that item in
`wizardscavern/sprites/ingredients.py` / `accessories.py`. Use
`--dry-run` to preview.
