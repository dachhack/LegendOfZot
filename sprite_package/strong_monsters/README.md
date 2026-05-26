# Strong Monsters — asset finalize task

This directory holds Gemini-generated boss/shard-guardian/elite sprites packed into one atlas PNG. The original 239-sprite carve has been **deduped down to 112** in three passes:
- Pass 1: 38 obvious dupes removed by hand
- Pass 2: 72 perceptual-hash near-duplicates removed via grouped picker
- Pass 3: 17 final visually-sorted-pass dupes removed

Your job is to slice them back into per-sprite PNGs, help Matt match each to its `monster_sprite_map.json` key, and output named PNGs at the correct resolutions.

## Inputs in this folder

- `strong_monsters_atlas.png` — 5632×5632 RGBA, 11×11 grid of 512px cells, 112 sprites (last 9 cells empty). **Sprites are arranged in visual-similarity order** (hierarchical clustering on pHash + colorhash), so similar monsters are adjacent — useful when assigning keys.
- `strong_monsters_manifest.json` — full metadata:
  ```
  {
    "atlas_file": "strong_monsters_atlas.png",
    "atlas_size": [5632, 5632],
    "cell_size": 512,
    "grid": {"cols": 11, "rows": 11},
    "frame_fill": 0.68,
    "n_sprites": 112,
    "sort_method": "hierarchical_clustering_phash_plus_colorhash",
    "sprites": [{id, pos, col, row, x, y}, ...],
    "original_count": 239,
    "deduped_count": 112,
    "skipped_from_original": [...],
    "skip_summary": {...}
  }
  ```
- `strong_monsters_contact_sheet.jpg` — visual overview with sprite IDs labeled. Open this first to plan your key assignments.

## What Matt needs

1. **Slice all 112 sprites** out of the atlas into individual transparent-bg PNGs in a working directory (e.g. `_carved/`). Naming by sprite ID is fine (`s00_00.png` etc.) — they'll be renamed in step 3.

2. **Build a `review.html` contact-sheet view** Matt can scroll through — show all 112 sprites in a grid with their IDs visible, in the manifest's sort order (so similar monsters stay adjacent).

3. **Take Matt's key assignments** (he'll provide a `sprite_id → key` mapping when he's ready) and produce the final per-sprite PNGs at the right resolutions:
   - **512×512** for keys in `BOSS_KEYS` (see below)
   - **256×256** for everything else (elites)
   - **Reserve sprites** (any not assigned to a key but worth keeping): 256×256, placed in `reserve/` subfolder
   - Use the `make_square` and `resize` helpers below — sprite should occupy ~68% of the frame per the spec

4. **Emit the final files**:
   - `monster_sprite_map.json` — `{ "<game key>": [["<stem>", <variant_index>], ...] }`
   - `filename_to_key.json` — reverse side-list `{ "<stem>": "<game key>" }`

## Boss-tier keys (get 512×512; everything else gets 256×256)

```python
BOSS_KEYS = {
    "ZOT'S GUARDIAN", "Platino", "BUG QUEEN",
    "DRAGON", "TREASURE GOLEM", "DIVINE AVATAR", "LORD",
    "ARCHLICH", "DEMON", "DEATH KNIGHT", "ANCIENT",
}
```

## All 51 spec keys

```
ZOT'S GUARDIAN, Platino, BUG QUEEN, DRAGON, TREASURE GOLEM, DIVINE AVATAR, LORD,
ARCHLICH, DEMON, DEATH KNIGHT, ANCIENT, Elder Starspawn, Voidmaw Devourer,
Cataclysm Fiend, Nightmare Lich, Soulflayer Wraith, Infernal Warlord, Abyssal Archfiend,
Starspawn Aberration, Crimson Wyrmlord, Sepulchral Lich, Maw of the Deep, Glacian Titan,
Abyssal Fiend, Illithid Overmind, Hundred-Eyed Watcher, Necrarch Lich, Graven Colossus,
Cryptborn Wraith, Hollow Lich, Emberscale Drake, Gnashing Horror, Iron Vanguard,
Cinderborn Efreet, Rimebound Djinn, Cinder Serpent, Gloomback Bear, Ridgeback Wyvern,
Voidspawn Brute, Sporelord Myconid, Balrog, Balor, Demilich, Elder Brain, Pit Fiend,
Storm Giant, Cyclops, Dragon Turtle, Fire Giant, Purple Worm, Sphinx
```

Truncated uppercase keys map to game-internal names:
- `DRAGON` = Ancient Dragon
- `TREASURE GOLEM` = Treasure Golem (Golem of Wealth)
- `DIVINE AVATAR` = Divine Avatar / Arch-Avatar
- `LORD` = Water Elemental Lord
- `ARCHLICH` = Archlich / Dragon Lich
- `DEMON` = Shadow Demon / Shadow Lord
- `DEATH KNIGHT` = Death Knight
- `ANCIENT` = Treant / Treant Overlord

Reserve-only creatures Matt's original spec said to leave OUT of the main map: Ragnarok, Overlord, Gravewright, Chain Tyrant, Petrifang Hydra.

## Reference implementation (slicing helpers)

```python
import json
from pathlib import Path
import numpy as np
from PIL import Image

BOSS_KEYS = {
    "ZOT'S GUARDIAN", "Platino", "BUG QUEEN",
    "DRAGON", "TREASURE GOLEM", "DIVINE AVATAR", "LORD",
    "ARCHLICH", "DEMON", "DEATH KNIGHT", "ANCIENT",
}

def tight_alpha_bbox(arr, threshold=8):
    alpha = arr[:, :, 3]
    mask = alpha > threshold
    if not mask.any(): return None
    ys = np.where(mask.any(axis=1))[0]
    xs = np.where(mask.any(axis=0))[0]
    return int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1

def make_square(arr, frame_fill=0.68, padding_px=8):
    bbox = tight_alpha_bbox(arr)
    if bbox is None: return arr
    x0, y0, x1, y1 = bbox
    sw, sh = x1 - x0, y1 - y0
    side = max(sw, sh) / frame_fill
    side = max(side, sw + 2 * padding_px, sh + 2 * padding_px)
    side = int(np.ceil(side))
    if side % 2: side += 1
    canvas = np.zeros((side, side, 4), dtype=np.uint8)
    dx = (side - sw) // 2
    dy = (side - sh) // 2
    canvas[dy:dy + sh, dx:dx + sw] = arr[y0:y1, x0:x1]
    return canvas

def resize(arr, target):
    return np.array(Image.fromarray(arr, 'RGBA').resize((target, target), Image.LANCZOS))

# Slice every cell from the manifest into _carved/
manifest = json.loads(Path('strong_monsters_manifest.json').read_text())
atlas = np.array(Image.open(manifest['atlas_file']).convert('RGBA'))
cell = manifest['cell_size']
out_carved = Path('_carved')
out_carved.mkdir(exist_ok=True)

for s in manifest['sprites']:
    crop = atlas[s['y']:s['y']+cell, s['x']:s['x']+cell]
    Image.fromarray(crop, 'RGBA').save(out_carved / f"{s['id']}.png", 'PNG', optimize=True)

# Build a contact-sheet HTML for Matt to review (in sort order)
sorted_ids = [s['id'] for s in manifest['sprites']]
html = ['<!doctype html><html><head><meta charset="utf-8"><title>Strong Monsters Review</title>',
        '<style>body{background:#15151c;color:#d8d8e0;font-family:sans-serif;margin:0;padding:16px}',
        '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}',
        '.card{background:#20202a;padding:6px;border-radius:6px;text-align:center}',
        '.card img{width:100%;height:140px;object-fit:contain}',
        '.card .id{font:11px monospace;color:#aab;margin-top:4px}',
        '</style></head><body><div class="grid">']
for sid in sorted_ids:
    html.append(f'<div class="card"><img src="_carved/{sid}.png"><div class="id">{sid}</div></div>')
html.append('</div></body></html>')
Path('review.html').write_text('\n'.join(html))
print("Wrote review.html — open in browser; sprites are in visual-similarity order")
```

## Workflow once Matt sends assignments

Matt will provide assignments in one of two forms:

**Form A — structured JSON**:
```json
{
  "s00_00": {"key": "DRAGON", "variant": 0, "stem": "ancient_dragon"},
  "s00_01": {"key": "DRAGON", "variant": 1, "stem": "ancient_dragon_2"},
  ...
}
```

**Form B — casual notes** like "s00_00 is the main dragon, s00_01 is variant 2, …". Translate to Form A and confirm with Matt before applying.

Then for each assignment:
- Open `_carved/<sprite_id>.png`
- `arr = np.array(img.convert('RGBA'))`
- `squared = make_square(arr)`
- `target = 512 if key in BOSS_KEYS else 256`
- `out = resize(squared, target)`
- Save as `<stem>.png` in `assets/strong_monsters/`

Final structure:
```
assets/strong_monsters/
  ancient_dragon.png        512  (boss)
  ancient_dragon_2.png      512  (boss variant)
  archlich.png              512  (shard guardian)
  cyclops.png               256  (elite)
  ... (51 keys total + variants) ...
  monster_sprite_map.json
  filename_to_key.json
  reserve/
    ... (any extra sprites Matt wants kept) ...
```

After this is done, the source atlas + manifest can be moved to a `_source/` subfolder — the game only needs the per-sprite PNGs + the JSONs.
