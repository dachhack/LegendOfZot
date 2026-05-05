# Wizard's Cavern — Sprite Repo Bundle

The **repo-friendly** half of the full sprite handoff for `dachhack/LegendOfZot`. Contains code, manifests, libraries, docs, and the round-8 source sheets needed for rooms slicing — everything that should live in the GitHub repo.

The **sprite PNGs themselves** (1,283 in-game + 3,968 reserve = 5,251 total) ship as a separate **assets bundle**, hosted outside the repo. See [Step 1](#step-1--fetch-the-assets-bundle) below.

## You are likely Claude Code

Read these in order:

1. **[CONTEXT.md](./CONTEXT.md)** — what's in the package, what was decided, what was already done
2. **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** — step-by-step integration into the game
3. **[code/promote_all_sprites.py](./code/promote_all_sprites.py)** — the unified script that wires sprites into the canonical pool

## Package layout

This (repo) bundle:

```
wc_sprites_repo/
├── README.md                      ← you are here
├── CONTEXT.md                     ← session history & design decisions
├── INTEGRATION_GUIDE.md           ← step-by-step apply
├── .gitignore                     ← keeps unpacked assets out of git
│
├── code/                          ← all integration code
│   ├── promote_all_sprites.py     ← unified merge script (idempotent, dry-run flag)
│   ├── sprite_data_weapons.py     ← _WEAPONS_MAP = {item_name: [(pid, vi), ...]}
│   ├── sprite_data_monsters.py    ← _MONSTERS_MAP, 124 items × 372 variants
│   ├── sprite_data_characters.py  ← _CHARACTERS_POOL = [pid, ...] (generic, 73)
│   ├── sprite_data_rooms.py       ← _ROOM_MAP/_VARIANT_MAP with (sheet, row, col)
│   └── ...                        ← 18 sprite_data_*.py files (one per category)
│
├── libraries/  (18 files)         ← authoritative chosen+reserve metadata per category
│
├── picks_rooms/                   ← rooms-specific deliverables
│   ├── room_picks.json            ← slim picks export
│   ├── slice_manifest.json        ← 81 assigned rooms sprites with RM IDs
│   ├── reserve_manifest.json      ← 343 reserve rooms sprites with RES IDs
│   ├── ROOMS.md                   ← updated room sprite documentation
│   └── preview_all_picks.png      ← visual reference: every slot × 3 variants
│
├── source_sheets/  (13 files)     ← round-8 sheets for rooms slicing
│   └── (S8M is 64px native; all others 128px)
│
├── canonical_pool_index.json      ← non-binary pid → metadata index (no images)
└── fetch_assets.py                ← verify the assets bundle is unpacked correctly
```

The assets bundle (separate; download from wherever it's hosted):

```
wc_sprites_assets/
├── in_game/
│   ├── manifest.json
│   ├── by_category/<cat>/<PID>_<name>_v<n>.png  (1,283 PNGs)
│   └── by_item/<cat>/<item_name>/v<n>.png       ← primary view, item → variants
├── reserve/                                      (3,968 PNGs)
└── picker/                                       (room_picker.html, future-rounds tool)
```

The full assets bundle is ~108 MB compressed. There are also chunked versions (`wc_sprites_assets_part01.zip` through `wc_sprites_assets_part06.zip`, each ≤24 MB) for environments where uploading large files is hard (e.g. GitHub web UI).

## Step 0 — One-time setup

Drop this bundle's contents into your repo. The integration commands below assume the repo root.

```bash
unzip wc_sprites_repo.zip
cp -r wc_sprites_repo/* path/to/your/LegendOfZot/
cp wc_sprites_repo/.gitignore path/to/your/LegendOfZot/  # also pick up the dotfile
```

## Step 1 — Fetch the assets bundle

The assets bundle lives **outside** the repo (too large for GitHub free tier). Download it from wherever you've hosted it (GitHub Releases, S3, Drive, etc.) and unpack into `assets/sprites/`:

```bash
# Either: single-file download
mkdir -p assets/sprites
curl -L -o /tmp/assets.zip <URL>
unzip /tmp/assets.zip -d /tmp/
mv /tmp/wc_sprites_assets/* assets/sprites/

# Or: chunked downloads (each part is ≤24 MB; unzip them all into the same place)
mkdir -p assets/sprites
for i in 01 02 03 04 05 06; do
    curl -L -o /tmp/assets_part$i.zip <URL>/wc_sprites_assets_part$i.zip
    unzip -o /tmp/assets_part$i.zip -d /tmp/extract/
done
mv /tmp/extract/wc_sprites_assets/* assets/sprites/
```

Verify the unpack:

```bash
python3 fetch_assets.py
# Expected:
#   ✓ in_game     1283 PNGs       — in-game sprites (named + generic)
#   ✓ reserve     3968 PNGs       — reserve sprites (kept but not in-game)
#   per-category counts all ✓
```

`assets/sprites/` is already in `.gitignore`, so unpacked sprites stay out of git.

## Step 2 — Build the canonical pool

```bash
python3 code/promote_all_sprites.py \
    --pool canonical_pool_full.pkl \
    --include-reserve
# Expected: Pool: 0 → 5251 entries
```

The script auto-finds assets at `assets/sprites/` if present; pass `--in-game-dir`, `--reserve-dir` to override.

## Step 3 — Integrate

See [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) for the 9-step walk.

## Headline numbers

```
                  named   generic   reserve   total
weapons             124         0       320     444
monsters            372         0      1428    1800
armors              114         0        73     187
accessories          60         0       414     474
bug_armors           15         0        41      56
foods                54         0       121     175
ingredients          22         0       375     397
lanterns              4         0         0       4
runes                24         0        45      69
shards               24         0        11      35
towels                3         0         0       3
treasures            44         0       397     441
trophies             91         0       296     387
characters            0        73         0      73
potions               0        87         6      93
scrolls               0        42        10      52
spells                0        49        88     137
rooms                81         0       343     424
─────────────────────────────────────────────────────
TOTAL              1032       251      3968    5251
```

- **named** (1,032) = chosen sprites with a specific game `item_name` (e.g. "Volcanic Blade")
- **generic** (251) = chosen sprites without item names (dynamic — characters, potions, scrolls, spells)
- **reserve** (3,968) = kept-but-not-in-game (visually approved, available for future use)
