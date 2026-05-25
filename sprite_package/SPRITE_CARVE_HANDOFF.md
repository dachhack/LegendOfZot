# Sprite Carving & Organizing — Handoff

Goal for the local session: **carve the Gemini-generated epic-monster sheets into
individual sprites and organize/assign them into the game** via the picker
pipeline. This doc is self-contained — everything you need is below, including a
proven carving script and the tricky name-mapping table.

> The monster-spellcasting feature on this branch (PR #173) is a **separate
> concern** — ignore it for sprite work. It does NOT touch the sprite pool.

---

## 1. What's been generated (and where)

We generated several epic boss/elite sheets in Gemini. Committed so far:

- `sprite_package/source_sheets/Gemini_Generated_Image_kcpiuekcpiuekcpi.png`
  — the **original 11**: 3 bosses (Zot's Guardian, Platino, Bug Queen) +
  8 shard guardians (Ancient Dragon, Treasure Golem, Divine Avatar, Water Lord,
  Archlich, Shadow Demon, Death Knight, Treant).

Still on your laptop (push them into `sprite_package/source_sheets/` with clear
names before carving):

- 2 **reserve** sheets (a "demonic/corrupted" set + a "natural" set): Ragnarok,
  Terrasque(=Tarrasque), Behemoth, Ancient Dragon, Golem (Wealth/Dark Iron),
  Avatar, Kraken, Dragon Lich, Shadow Lord, Death Knight, Treant/Overlord.
- The **deep-tier (L12–15)** sheet(s) — 24 monsters (Elder Starspawn, Voidmaw
  Devourer, Cataclysm Fiend, Nightmare/Sepulchral/Necrarch/Hollow Lich, Abyssal
  Archfiend/Fiend, Crimson Wyrmlord, Maw of the Deep, Glacian Titan, Illithid
  Overmind, Hundred-Eyed Watcher, Graven Colossus, Cryptborn/Soulflayer Wraith,
  Emberscale Drake, Gnashing Horror, Iron Vanguard, Cinderborn Efreet,
  Rimebound Djinn, Infernal Warlord, Starspawn Aberration).
- The **iconic giants (L9–11)** sheet(s) — Cinder Serpent, Gloomback Bear,
  Ridgeback Wyvern, Voidspawn Brute, Sporelord Myconid, Balrog, Demilich,
  Elder Brain, Pit Fiend, Storm Giant, Cyclops, Dragon Turtle, Fire Giant,
  Purple Worm, Sphinx.
- Plus any from the "new monster ideas" brainstorm (Gravewright, Bone Choir,
  Chain Tyrant, Clockwork Inquisitor, Petrifang Hydra, Thornhag, etc.) — these
  have **no in-game monster yet**, so they're reserve art.

---

## 2. Sheet quirks / gotchas (read before carving)

- **The "transparent" checkerboard is fake.** The first sheet is RGBA but fully
  opaque; the background is a *dark-gray checker* (two shades ≈ `(72,72,72)` and
  `(102,101,102)`). Detect creatures by **color, not alpha**. (Newer sheets we
  switched to a flat dark charcoal `~#2c2a28` — much easier; just key that one
  color.)
- **Baked-in white text labels** in the sheets — exclude them (they sit in thin
  bands between the tall sprite rows).
- **Duplicate rows** — sheets often repeat the creature row 2–3×. Carve ONE
  clean instance per creature.
- **Match the existing format.** Existing pool sprites are **96×96 RGBA, fully
  opaque, on a solid dark background `(51,47,44)`**. For consistency, key the
  checker out and **replace it with that charcoal** (don't ship transparent),
  then center on a square canvas. Store at higher res (e.g. **256×256**) so
  bosses stay crisp — the renderer upscales the source to the render size.

---

## 3. Proven carving technique

What worked here (validated on the original 11):

1. **Foreground mask by color**: `bg = desaturated & mid-brightness` (the dark
   checker), `fg = everything else` (colorful / bright white creature parts /
   near-black outlines).
2. **Row/column projection** of `fg` to auto-find the grid: tall bands = sprite
   rows, thin bands = text (skip), column clusters within a band = individual
   sprites.
3. **Flood-fill the background from each cell's borders** through bg-colored
   pixels (scipy `binary_propagation`). This is the key trick — it keeps gray
   creature *interiors* (e.g. a silver dragon's scales) opaque while removing
   the surrounding checker.
4. **Recolor** flood-filled bg → `(51,47,44)`, tight-crop to the creature bbox
   + ~8% pad, center on a square charcoal canvas, resize to 256×256.

### Carving script (drop in `sprite_package/code/carve_sheet.py`)

```python
#!/usr/bin/env python3
"""Carve a Gemini monster sheet into individual sprites.
Usage:
  # 1) detect grid (prints row bands + column boxes):
  python3 carve_sheet.py SHEET.png --detect
  # 2) carve a band's creatures left-to-right into named PNGs:
  python3 carve_sheet.py SHEET.png --band <y0> <y1> --names a b c ... --out DIR
Needs: pip install pillow numpy scipy
"""
import sys, argparse
import numpy as np
from PIL import Image
from scipy import ndimage

CHARCOAL = (51, 47, 44)   # matches existing pool sprites
OUT_SIZE = 256

def fg_mask(arr):
    mx = arr.max(2); mn = arr.min(2); sat = mx - mn; bright = mx
    bg = (sat < 18) & (bright >= 52) & (bright <= 124)   # dark checker (+AA)
    return ~bg, bg

def detect(path):
    arr = np.array(Image.open(path).convert('RGB')).astype(int)
    H, W, _ = arr.shape
    fg, _ = fg_mask(arr)
    rs = fg.sum(1); rthr = W * 0.012
    inb = False; bands = []
    for y in range(H):
        if rs[y] > rthr and not inb: s = y; inb = True
        elif rs[y] <= rthr and inb: bands.append((s, y)); inb = False
    if inb: bands.append((s, H))
    for s, e in [(s, e) for s, e in bands if e - s > 12]:
        sub = fg[s:e]; cs = sub.sum(0); cthr = (e - s) * 0.06
        inc = False; cols = []
        for x in range(W):
            if cs[x] > cthr and not inc: c0 = x; inc = True
            elif cs[x] <= cthr and inc: cols.append((c0, x)); inc = False
        if inc: cols.append((c0, W))
        cols = [(a, b) for a, b in cols if b - a > 30]
        kind = 'TEXT' if (e - s) < 90 else 'SPRITES'
        print(f'band y[{s}:{e}] h={e-s} {kind}: {len(cols)} cols -> {cols}')

def carve(path, y0, y1, names, out):
    import os; os.makedirs(out, exist_ok=True)
    arr = np.array(Image.open(path).convert('RGB')).astype(int)
    H, W, _ = arr.shape
    fg, _ = fg_mask(arr)
    sub = fg[y0:y1]; cs = sub.sum(0); cthr = (y1 - y0) * 0.06
    inc = False; cols = []
    for x in range(W):
        if cs[x] > cthr and not inc: c0 = x; inc = True
        elif cs[x] <= cthr and inc: cols.append((c0, x)); inc = False
    if inc: cols.append((c0, W))
    cols = [(a, b) for a, b in cols if b - a > 30]
    assert len(cols) == len(names), f'{len(cols)} sprites but {len(names)} names'
    rgb = np.array(Image.open(path).convert('RGB')).astype(np.uint8)
    _, bgmask_full = fg_mask(np.array(Image.open(path).convert('RGB')).astype(int))
    PAD = 10
    for (x0, x1), name in zip(cols, names):
        X0, Y0 = max(0, x0 - PAD), max(0, y0 - PAD); X1, Y1 = x1 + PAD, y1 + PAD
        cell = rgb[Y0:Y1, X0:X1].copy()
        chk = bgmask_full[Y0:Y1, X0:X1]
        seed = np.zeros_like(chk)
        seed[0, :] |= chk[0, :]; seed[-1, :] |= chk[-1, :]
        seed[:, 0] |= chk[:, 0]; seed[:, -1] |= chk[:, -1]
        bg = ndimage.binary_propagation(seed, mask=chk)
        cell[bg] = CHARCOAL
        ys, xs = np.where(~bg)
        crop = cell[ys.min():ys.max()+1, xs.min():xs.max()+1]
        h, w, _ = crop.shape; s = max(h, w); p = int(s*0.08); side = s + 2*p
        canv = np.full((side, side, 3), CHARCOAL, np.uint8)
        oy, ox = (side-h)//2, (side-w)//2; canv[oy:oy+h, ox:ox+w] = crop
        Image.fromarray(canv).resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS).save(f'{out}/{name}.png')
        print(f'  {name}: {w}x{h} -> {OUT_SIZE}px')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet'); ap.add_argument('--detect', action='store_true')
    ap.add_argument('--band', nargs=2, type=int); ap.add_argument('--names', nargs='+')
    ap.add_argument('--out', default='./carved')
    a = ap.parse_args()
    if a.detect: detect(a.sheet)
    else: carve(a.sheet, a.band[0], a.band[1], a.names, a.out)
```

**For the original sheet** (`Gemini_Generated_Image_kcpiuekcpiuekcpi.png`,
2754×1536) the detected grid was:
- Bosses in band `y[137:462]`, first 3 columns:
  `30-365` Guardian, `396-734` Platino, `788-1063` Bug Queen.
- The clean 8 guardians in band `y[658:997]` (the row directly above its labels):
  `25-362` Ancient Dragon, `377-690` Treasure Golem, `722-1024` Divine Avatar,
  `1069-1368` Water Lord, `1399-1706` Archlich, `1736-2052` Shadow Demon,
  `2133-2334` Death Knight, `2447-2708` Treant.
- (band `y[1189:1526]` is a duplicate of the guardians — ignore.)

Always `--detect` first, then eyeball a contact sheet before committing crops.

---

## 4. The sprite pipeline (paths + tools)

- **Per-category maps — TWO copies kept in sync:**
  `sprite_package/code/sprite_data_monsters.py` (read by the promote script) and
  `wizardscavern/sprites/monsters.py` (read at runtime). Format:
  `_MONSTERS_MAP = {name: [(pid, variant_index), ...]}`. **Multiple entries =
  variants** — the engine picks one by seed (`get_named_variant`), so this is how
  you give a monster several looks.
- **PNG overlay dir:** `assets/sprite_picks/monsters/` (`MN####_Name_v0.png`).
  The canonical bundle also has `assets/sprites/in_game/by_category/monsters/`.
  `promote_all_sprites.py:index_in_game_pngs` scans both (the `sprite_picks` form
  has no `by_category/` wrapper and acts as an overlay).
- **Pool:** `wizardscavern/data/canonical_pool_full.pkl` (binary, ~2.9 MB,
  1283 in-game entries; ~5251 with reserve).
- **Rebuild the pool:**
  ```bash
  python3 sprite_package/code/promote_all_sprites.py \
      --pool /tmp/pool.pkl --categories monsters --dry-run   # inspect first
  python3 sprite_package/code/promote_all_sprites.py --pool /tmp/pool.pkl --include-reserve
  cp /tmp/pool.pkl wizardscavern/data/canonical_pool_full.pkl
  ```
- **Name resolver:** `wizardscavern/sprite_data.py:_resolve_new_monster_key` —
  matches a (decorated) monster name to a map key: as-is → strip spaces/`~` →
  trailing-tail in Title/UPPER/raw casing → per-word Title. So `" TREASURE
  GOLEM"` resolves to key `TREASURE GOLEM`.
- **Render sizes** (`app.py:get_monster_threat_style` → `_THREAT_TIERS`):
  trivial 50 / normal 64 / tough 74 / dangerous 84 / deadly 92 / champion 96 /
  legendary 120 / boss 150 px. Bosses + shard guardians are the always-large
  ones (120–150) where high-res art pays off most; deep-tier monsters hit 84–92
  whenever you meet them underleveled.

**Authoritative reading:** `sprite_package/INTEGRATION_GUIDE.md` (full
step-by-step) and `sprite_package/CONTEXT.md`.

---

## 5. Picker workflow ("organizing via pickers")

- `sprite_package/picks_recent/build_monster_picker.py` → builds
  `picker_monsters.html`, a visual chooser (candidate pids per monster).
- Open the HTML in a browser, click your picks → saved to `recent_picks.json`.
- `sprite_package/picks_recent/apply_picks.py` → runs the full pipeline: PNG →
  `sprite_picks` overlay + bundle mirror, library reserve→chosen, updates **both
  `_MONSTERS_MAP` copies**, and regenerates the pool. (This is how the 30 deep
  monsters were assigned earlier — see the b421/b422 changelog entries.)

---

## 6. Monster → map-key mapping (the tricky part)

The legendaries are spawned by `create_legendary_monster` (game_systems.py:319)
with **oddly-truncated `name` strings**. To make new art actually appear, the
map key must match what the resolver produces. Verify each `Monster(...)` name
arg, but here's the current state:

| Generated art | In-game name string | Map key needed | Status |
|---|---|---|---|
| Zot's Guardian | `" ZOT'S GUARDIAN "` | `ZOT'S GUARDIAN` | **ADD key** |
| Platino | `"Platino"` | `Platino` | exists ✓ (re-point pid) |
| Bug Queen | (combat.py spawn) | `BUG QUEEN` | exists ✓ |
| Ancient Dragon (battle) | `"DRAGON"` | `DRAGON` | **ADD** (bare `DRAGON` won't match `Ancient Dragon`) |
| Treasure Golem (treasure) | `" TREASURE GOLEM"` | `TREASURE GOLEM` | exists ✓ |
| Divine Avatar (devotion) | `"~~~ DIVINE AVATAR"` | `DIVINE AVATAR` | exists ✓ |
| Water Elemental Lord (reflection) | `"LORD"` | `LORD` | **ADD** |
| Archlich (knowledge) | `"ARCHLICH"` | `ARCHLICH` | exists ✓ |
| Shadow Demon (secrets) | `"DEMON"` | `DEMON` | **ADD** |
| Death Knight (eternity) | `" DEATH KNIGHT"` | `DEATH KNIGHT` | exists ✓ |
| Treant Ancient (growth) | `"ANCIENT"` | `ANCIENT` | **ADD** |

- **Re-pointing** an existing key = replace the old `(pid, vi)` with your new
  pid (or append it as a variant).
- **Reserve/variant art** (Tarrasque, Kraken, Behemoth, Iron Golem, Dragon Lich,
  etc.) → add as extra `(pid, vi)` variants on the existing keys for instant
  in-fight variety.
- **Brand-new creatures** (Ragnarok, Overlord, Gravewright, Chain Tyrant, …) have
  no monster entry — park their PNGs as reserve (descriptive pids, unassigned)
  until/if those monsters are added to `game_data.py`.

---

## 7. Task checklist

1. `pip install pillow numpy scipy` (and confirm the game's deps).
2. `git pull` this branch; drop all generated sheets into
   `sprite_package/source_sheets/` with clear names.
3. For each sheet: `carve_sheet.py SHEET --detect`, map boxes→names, then
   `--band ... --names ...` → individual 256px PNGs. Build a contact sheet and
   eyeball before committing.
4. Place carved PNGs into `assets/sprite_picks/monsters/` as
   `MN####_<Name>_v0.png` (pick free MN#### pids; check the pool/index for
   collisions), **or** feed them through `build_monster_picker.py` +
   `apply_picks.py`.
5. Add/re-point `_MONSTERS_MAP` keys in **both** copies per §6.
6. Rebuild the pool (`promote_all_sprites.py`), confirm entry counts.
7. Launch the game and verify each boss/guardian renders correctly at 96–150px
   (fight one, or use a debug spawn).
8. Commit (don't forget the regenerated `.pkl` if you commit it, or gitignore +
   build-on-setup per INTEGRATION_GUIDE §1).

---

## 8. Known per-sprite notes (from review)

- **Death Knight** art kept a stone **pedestal** — every other sprite floats
  full-body; re-roll it without the base or it'll look like it's on a slab.
- The three Darkness guardians (**Archlich / Shadow Demon / Death Knight**) read
  too similarly at small size — consider pushing their palettes apart.
- **Platino** read as a generic white dragon — push the metallic/platinum sheen.
