"""
Build a mobile-first HTML picker for the b403-b412 sprite additions.

v2 (post-feedback): candidate sprites now come from the RESERVE pool
(3,968 visually approved but unassigned sprites in the
`sprite-assets-v1` GitHub Release), not from the already-in-game pool.
Layout is one item at a time with prev/next nav so each candidate gets
a chunky tap target instead of a 50px thumb buried in a 109-tile grid.

Scope: 4 cantrip spells with no current sprite assignment + 8 recent
spells that landed pids during balance work + 1 accessory (Hourglass
Talisman, currently sharing Heartstone Pendant sprites).

Run:
    python3 sprite_package/picks_recent/build_picker.py
        [--reserve-dir /tmp/wc_reserve/wc_sprites_assets/reserve]

Default reserve dir is the unzipped sprite-assets-v1 release at
/tmp/wc_reserve/wc_sprites_assets/reserve. If the dir is missing the
script falls back to the shipped canonical_pool_full.pkl (chosen pool
only). To refresh:
    curl -L -o /tmp/wc_sprites_assets.zip \\
        https://github.com/dachhack/LegendOfZot/releases/download/\\
        sprite-assets-v1/wc_sprites_assets.zip
    unzip -q -o /tmp/wc_sprites_assets.zip \\
        'wc_sprites_assets/reserve/spells/*' \\
        'wc_sprites_assets/reserve/accessories/*' \\
        -d /tmp/wc_reserve/

Writes:
    sprite_package/picks_recent/picker.html

Open in a mobile browser, swipe / tap to navigate items, tap a
candidate to pick it, hit "Save All" to download recent_picks.json.
Then run apply_picks.py to write the edits back.
"""
import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, _ROOT)

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
    sys.exit(2)

from wizardscavern.sprites import get_image_b64  # noqa: E402
from wizardscavern.sprites.pool import _load_pool  # noqa: E402
from wizardscavern.sprites.spells import _SPELLS_NAMED  # noqa: E402
from wizardscavern.sprites.accessories import _ACCESSORIES_MAP  # noqa: E402
from wizardscavern.sprites.ingredients import _INGREDIENTS_MAP  # noqa: E402
from wizardscavern.sprites.foods import _FOODS_MAP  # noqa: E402
from wizardscavern.sprites.bug_weapons import _BUG_WEAPONS_MAP  # noqa: E402
from wizardscavern.item_templates import SPELL_TEMPLATES  # noqa: E402


# --- Scope ----------------------------------------------------------------

SPELL_PICKS = [
    ('Detect Monster',  'gap',  'cantrip -- no current pick, falls through to pool'),
    ('Hold Monster',    'gap',  'cantrip -- no current pick, falls through to pool'),
    ('Light',           'gap',  'cantrip -- no current pick, falls through to pool'),
    ('Mind Touch',      'gap',  'cantrip -- no current pick, falls through to pool'),
    ('Mind Blast',      'auto', 'b411 -- auto-assigned I185 during caster sweep'),
    ('Earthquake',      'auto', 'b411 -- auto-assigned V078 during caster sweep'),
    ('Holy Smite',      'auto', 'b411 -- auto-assigned V215 during caster sweep'),
    ('Psychic Scream',  'auto', 'b411 -- auto-assigned I120 during caster sweep'),
    ('Meteor Strike',   'auto', 'b408 -- auto-assigned V292 during damage suite'),
    ('Inferno',         'auto', 'b408 -- auto-assigned I012 during damage suite'),
    ('Mage Armor',      'auto', 'b403 -- shares I047 with Divine Shield (orphan spell)'),
    ('Spectral Hand',   'auto', 'b403 -- shares I058 with Stone Skin (orphan spell)'),
]

ACCESSORY_PICKS = [
    ('Hourglass Talisman', 'auto',
     'b403 -- shares pendant sprites with Heartstone Pendant; '
     'flagged for a dedicated sand/glass visual'),
]

FOOD_PICKS = [
    ('Blutwurst', 'gap',
     'dwarf-tier-3 sausage recipe (SAUSAGE_RECIPES) -- '
     'no _FOODS_MAP entry, falls to generic food pool'),
    ('Landjäger', 'gap',
     'dwarf-tier-2 sausage recipe (SAUSAGE_RECIPES) -- '
     'no _FOODS_MAP entry, falls to generic food pool'),
]

INGREDIENT_PICKS = [
    ('Aphid Honeydew',  'gap',  'bug garden T1 (BUG_GARDEN_INGREDIENTS) -- unmapped'),
    ('Mycelium Thread', 'gap',  'bug garden T1 (BUG_GARDEN_INGREDIENTS) -- unmapped'),
    ('Pollen Cluster',  'gap',  'bug garden T1 (BUG_GARDEN_INGREDIENTS) -- unmapped'),
    ('Chitin Moss',     'gap',  'bug garden T1 (BUG_GARDEN_INGREDIENTS) -- unmapped'),
    ('Spore Cap',       'gap',  'bug garden T2 (BUG_GARDEN_INGREDIENTS) -- unmapped'),
    ('Nectar Bead',     'gap',  'bug garden T2 (BUG_GARDEN_INGREDIENTS) -- unmapped'),
    ('Dew Silk',        'gap',  'bug garden T2 (BUG_GARDEN_INGREDIENTS) -- unmapped'),
]

BUG_WEAPON_PICKS = [
    ('Stinger Blade',      'gap', 'shrinking-bug-level loot, no bug_weapons sprite map until now'),
    ('Mandible Axe',       'gap', 'shrinking-bug-level loot, no bug_weapons sprite map until now'),
    ('Thorax Spear',       'gap', 'shrinking-bug-level loot, no bug_weapons sprite map until now'),
    ('Firefly Wand',       'gap', 'shrinking-bug-level loot, no bug_weapons sprite map until now'),
    ('Scorpion Tail Whip', 'gap', 'shrinking-bug-level loot, no bug_weapons sprite map until now'),
]


# --- Reserve loader -------------------------------------------------------

def png_to_b64_webp(path):
    """PNG file -> base64 webp (matches canonical_pool_full.pkl format)."""
    im = Image.open(path).convert("RGBA")
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=80, method=4)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def load_reserve_sprites(reserve_dir, category):
    """Walk reserve_dir/<category>/*.png and return [{pid, img, source}].
    Returns empty list (with warning) if the dir is missing -- caller
    falls back to chosen-only."""
    cat_dir = Path(reserve_dir) / category
    if not cat_dir.exists():
        print(f"  WARN: reserve dir missing for {category}: {cat_dir}",
              file=sys.stderr)
        return []
    sprites = []
    for png in sorted(cat_dir.glob('*.png')):
        # filename: PID_label.png -> pid is first underscore segment
        pid = png.stem.split('_', 1)[0]
        try:
            img_b64 = png_to_b64_webp(png)
        except Exception as e:
            print(f"  WARN: failed to encode {png.name}: {e}", file=sys.stderr)
            continue
        sprites.append({'pid': pid, 'img': img_b64, 'source': 'reserve'})
    return sprites


def load_chosen_sprites(category):
    """Pull the already-shipped chosen sprites for a category from the
    canonical pool (so the user can compare reserve picks to what's
    already in-game, or fall back to a chosen sprite if they prefer)."""
    pool = _load_pool()
    sprites = []
    for pid, entry in sorted(pool.items()):
        if entry.get('cat') == category:
            img = entry.get('img_b64', '')
            if img:
                sprites.append({'pid': pid, 'img': img, 'source': 'chosen'})
    return sprites


# --- Item info helpers ----------------------------------------------------

def spell_meta(name):
    for s in SPELL_TEMPLATES:
        if s.name == name:
            return {
                'description': s.description,
                'meta': f"L{s.level} · {s.mana_cost} MP · "
                        f"{s.damage_type or 'utility'}"
                        + (' · cantrip' if getattr(s, 'is_cantrip', False)
                           else ''),
            }
    return {
        'description': '(declared outside SPELL_TEMPLATES -- '
                       'see Mage Armor / Spectral Hand code-smell note)',
        'meta': 'orphan',
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reserve-dir',
                    default='/tmp/wc_reserve/wc_sprites_assets/reserve',
                    help='Path to the unzipped reserve sprite dir.')
    args = ap.parse_args()

    print(f"Loading reserve sprites from {args.reserve_dir}...")
    # bug_weapons uses the regular weapons reserve pool (no dedicated
    # reserve dir exists). User hand-picks the insectoid-looking ones
    # from the 321 weapon reserve sprites.
    spell_reserve = load_reserve_sprites(args.reserve_dir, 'spells')
    acc_reserve = load_reserve_sprites(args.reserve_dir, 'accessories')
    food_reserve = load_reserve_sprites(args.reserve_dir, 'foods')
    ing_reserve = load_reserve_sprites(args.reserve_dir, 'ingredients')
    weapon_reserve = load_reserve_sprites(args.reserve_dir, 'weapons')
    print(f"  spells reserve: {len(spell_reserve)}")
    print(f"  accessories reserve: {len(acc_reserve)}")
    print(f"  foods reserve: {len(food_reserve)}")
    print(f"  ingredients reserve: {len(ing_reserve)}")
    print(f"  weapons reserve (used for bug_weapons): {len(weapon_reserve)}")

    spell_chosen = load_chosen_sprites('spells')
    acc_chosen = load_chosen_sprites('accessories')
    food_chosen = load_chosen_sprites('foods')
    ing_chosen = load_chosen_sprites('ingredients')
    weapon_chosen = load_chosen_sprites('weapons')

    items = []
    for name, kind, note in SPELL_PICKS:
        info = spell_meta(name)
        current = _SPELLS_NAMED.get(name, '')
        items.append({
            'category': 'spells',
            'name': name,
            'kind': kind,
            'note': note,
            'description': info['description'],
            'meta': info['meta'],
            'current': current,
            'current_img': get_image_b64(current) if current else '',
        })

    for name, kind, note in ACCESSORY_PICKS:
        variants = _ACCESSORIES_MAP.get(name) or []
        current = variants[0][0] if variants else ''
        items.append({
            'category': 'accessories',
            'name': name,
            'kind': kind,
            'note': note,
            'description': '',
            'meta': f"variants currently: {len(variants)}",
            'current': current,
            'current_img': get_image_b64(current) if current else '',
        })

    for name, kind, note in FOOD_PICKS:
        variants = _FOODS_MAP.get(name) or []
        current = variants[0][0] if variants else ''
        items.append({
            'category': 'foods',
            'name': name,
            'kind': kind,
            'note': note,
            'description': '',
            'meta': 'sausage recipe',
            'current': current,
            'current_img': get_image_b64(current) if current else '',
        })

    for name, kind, note in INGREDIENT_PICKS:
        variants = _INGREDIENTS_MAP.get(name) or []
        current = variants[0][0] if variants else ''
        items.append({
            'category': 'ingredients',
            'name': name,
            'kind': kind,
            'note': note,
            'description': '',
            'meta': 'bug-garden harvest',
            'current': current,
            'current_img': get_image_b64(current) if current else '',
        })

    for name, kind, note in BUG_WEAPON_PICKS:
        variants = _BUG_WEAPONS_MAP.get(name) or []
        current = variants[0][0] if variants else ''
        items.append({
            'category': 'bug_weapons',
            'name': name,
            'kind': kind,
            'note': note,
            'description': '',
            'meta': 'bug-level weapon drop',
            'current': current,
            'current_img': get_image_b64(current) if current else '',
        })

    candidates = {
        'spells':       {'reserve': spell_reserve,  'chosen': spell_chosen},
        'accessories':  {'reserve': acc_reserve,    'chosen': acc_chosen},
        'foods':        {'reserve': food_reserve,   'chosen': food_chosen},
        'ingredients':  {'reserve': ing_reserve,    'chosen': ing_chosen},
        # bug_weapons borrows the weapons candidate pool (no dedicated
        # bug_weapons reserve dir exists; user picks insect-looking ones
        # from the regular weapons sprite reserve).
        'bug_weapons':  {'reserve': weapon_reserve, 'chosen': weapon_chosen},
    }

    # Seed any existing picks from a previous session.
    picks_path = os.path.join(_HERE, 'recent_picks.json')
    existing_picks = {}
    if os.path.exists(picks_path):
        with open(picks_path, 'r') as f:
            try:
                existing_picks = json.load(f).get('picks', {})
            except Exception:
                existing_picks = {}

    for it in items:
        key = f"{it['category']}::{it['name']}"
        it['picked'] = existing_picks.get(key, '')

    embedded = json.dumps({'items': items, 'candidates': candidates})

    html = TEMPLATE.replace('__DATA__', embedded)
    out_path = os.path.join(_HERE, 'picker.html')
    with open(out_path, 'w') as f:
        f.write(html)
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\nWrote {out_path}")
    print(f"  items={len(items)}")
    for cat, c in candidates.items():
        print(f"  {cat} candidates: {len(c['reserve'])} reserve + "
              f"{len(c['chosen'])} chosen = "
              f"{len(c['reserve']) + len(c['chosen'])}")
    print(f"  size={size_mb:.2f} MB")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Sprite Picker</title>
<style>
  :root {
    --bg: #1a1a1a;
    --panel: #222;
    --panel-2: #2a2a2a;
    --line: #333;
    --text: #eee;
    --muted: #aaa;
    --accent: #FFD700;
    --reserve: #50c878;
    --chosen: #4a90e2;
    --gap: #d97706;
    --pick: #FFD700;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
               font-family: system-ui, -apple-system, sans-serif;
               overflow-x: hidden;
               -webkit-text-size-adjust: 100%; }
  body { padding-top: 124px; padding-bottom: 88px; }

  /* Sticky top bar -- always visible so context never scrolls out. */
  header {
    position: fixed; top: 0; left: 0; right: 0; z-index: 30;
    background: linear-gradient(180deg, #181818 0%, #141414 100%);
    border-bottom: 1px solid var(--line);
    padding: 8px 12px;
  }
  .topline {
    display: flex; align-items: center; gap: 10px;
    font-size: 12px; color: var(--muted);
  }
  .topline .progress {
    flex: 1; height: 4px; background: #333; border-radius: 2px; overflow: hidden;
    margin-right: 4px;
  }
  .topline .progress-bar {
    height: 100%; background: var(--pick); width: 0%;
    transition: width 0.2s;
  }
  .topline .count { font-family: monospace; font-size: 11px; }
  .title-row {
    display: flex; align-items: center; gap: 10px; margin-top: 4px;
  }
  .title-row .current-preview {
    flex: 0 0 56px; width: 56px; height: 56px; background: #0a0a0a;
    border-radius: 6px; border: 2px solid #444; position: relative;
  }
  .title-row .current-preview canvas {
    width: 100%; height: 100%; image-rendering: pixelated;
    image-rendering: crisp-edges; border-radius: 4px;
  }
  .title-row .current-preview.has-pick { border-color: var(--pick); }
  .title-row .current-preview .pid-label {
    position: absolute; bottom: -16px; left: 0; right: 0;
    font-family: monospace; font-size: 10px; color: var(--muted);
    text-align: center; line-height: 1;
  }
  .title-row .info { flex: 1 1 auto; min-width: 0; }
  .title-row h1 {
    margin: 0; font-size: 16px; color: var(--accent); font-weight: bold;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .title-row .tag {
    font-size: 11px; color: var(--muted); margin-top: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .badge {
    display: inline-block; padding: 1px 5px; font-size: 9px;
    font-weight: bold; border-radius: 3px; margin-right: 4px;
    text-transform: uppercase; letter-spacing: 0.5px; vertical-align: middle;
  }
  .badge.gap { background: var(--gap); color: #fff; }
  .badge.auto { background: #555; color: #fff; }

  /* Filter chips. */
  .filters {
    display: flex; gap: 6px; margin-top: 18px;
    overflow-x: auto; -webkit-overflow-scrolling: touch;
    padding-bottom: 4px;
  }
  .filter-chip {
    flex: 0 0 auto; padding: 5px 11px; background: #333; color: #ccc;
    border: 1px solid #444; border-radius: 16px;
    font-size: 12px; cursor: pointer; white-space: nowrap;
    -webkit-user-select: none; user-select: none;
  }
  .filter-chip.active { background: var(--pick); color: #000; border-color: var(--pick); }

  /* Body content. */
  main { padding: 8px 8px 16px 8px; }
  .description {
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;
    font-size: 13px; color: #ddd; line-height: 1.4;
  }
  .description .note {
    font-size: 11px; color: var(--muted); font-style: italic;
    margin-top: 6px;
  }
  .section-label {
    font-size: 11px; color: var(--muted); margin: 12px 4px 6px 4px;
    text-transform: uppercase; letter-spacing: 0.7px; font-weight: bold;
  }
  .section-label .swatch { display: inline-block; width: 10px; height: 10px;
                            border-radius: 2px; margin-right: 6px;
                            vertical-align: middle; }
  .section-label .swatch.reserve { background: var(--reserve); }
  .section-label .swatch.chosen { background: var(--chosen); }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
    gap: 6px;
  }
  @media (min-width: 480px) {
    .grid { grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); }
  }
  .tile {
    background: #181818; border: 2px solid #2a2a2a; border-radius: 6px;
    padding: 4px; cursor: pointer; -webkit-tap-highlight-color: transparent;
    transition: border-color 0.1s, transform 0.08s;
    -webkit-user-select: none; user-select: none;
    position: relative;
  }
  .tile.reserve { border-color: rgba(80, 200, 120, 0.25); }
  .tile.chosen { border-color: rgba(74, 144, 226, 0.25); }
  .tile.current { border-color: var(--chosen); }
  .tile.picked {
    border-color: var(--pick); transform: scale(1.05);
    box-shadow: 0 0 12px rgba(255, 215, 0, 0.45);
    z-index: 1;
  }
  .tile canvas {
    width: 100%; aspect-ratio: 1; background: #0a0a0a;
    image-rendering: pixelated; image-rendering: crisp-edges;
    display: block; border-radius: 3px;
  }
  .tile .pid {
    font-family: monospace; font-size: 9px; color: #888;
    margin-top: 2px; text-align: center; line-height: 1.2;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .tile.picked .pid { color: var(--pick); }
  .tile .source-tag {
    position: absolute; top: 2px; right: 2px;
    width: 8px; height: 8px; border-radius: 50%;
  }
  .tile.reserve .source-tag { background: var(--reserve); }
  .tile.chosen .source-tag { background: var(--chosen); }
  .tile.current .source-tag::after {
    content: ''; position: absolute; top: -2px; left: -2px;
    width: 12px; height: 12px; border-radius: 50%;
    border: 1px solid #fff; box-sizing: border-box;
  }

  /* Bottom action bar. */
  footer {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 30;
    background: linear-gradient(0deg, #181818 0%, #141414 100%);
    border-top: 1px solid var(--line);
    padding: 10px 12px; padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px));
    display: flex; gap: 8px; align-items: center;
  }
  footer button {
    flex: 1; padding: 12px 8px; background: #333; color: var(--text);
    border: 1px solid #555; border-radius: 6px; font-size: 14px;
    font-weight: bold; cursor: pointer; -webkit-tap-highlight-color: transparent;
    -webkit-user-select: none; user-select: none;
  }
  footer button:active { background: #444; }
  footer button.primary { background: #2a5a3a; border-color: #4a8a5a; }
  footer button.primary:active { background: #3a6a4a; }
  footer button.clear-pick {
    flex: 0 0 60px; background: #3a2020; border-color: #553;
    color: #fcc; font-size: 12px;
  }
  footer .nav-arrow { flex: 0 0 50px; font-size: 18px; }

  /* JSON export modal. */
  #export-modal {
    display: none; position: fixed; inset: 0; z-index: 40;
    background: rgba(0,0,0,0.85); align-items: center; justify-content: center;
    padding: 20px;
  }
  #export-modal.shown { display: flex; }
  #export-modal .modal-inner {
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 10px; padding: 16px; width: 100%; max-width: 600px;
    max-height: 80vh; overflow-y: auto;
  }
  #export-modal h3 { margin: 0 0 10px 0; color: var(--accent); }
  #export-modal textarea {
    width: 100%; height: 200px; background: #0a0a0a; color: #9f9;
    font-family: monospace; font-size: 11px; padding: 8px;
    border: 1px solid var(--line); border-radius: 4px;
    box-sizing: border-box; resize: vertical;
  }
  #export-modal .actions { display: flex; gap: 8px; margin-top: 10px; }
  #export-modal .actions button {
    flex: 1; padding: 10px; background: #333; color: var(--text);
    border: 1px solid #555; border-radius: 4px; font-size: 13px; cursor: pointer;
  }
  #export-modal .actions button.primary {
    background: #2a5a3a; border-color: #4a8a5a;
  }
</style>
</head>
<body>
<header>
  <div class="topline">
    <span class="count" id="counter">1 / 1</span>
    <div class="progress"><div class="progress-bar" id="progress-bar"></div></div>
    <span class="count" id="picks-count">0 picked</span>
  </div>
  <div class="title-row">
    <div class="current-preview" id="current-preview">
      <canvas width="56" height="56"></canvas>
      <div class="pid-label" id="current-pid">--</div>
    </div>
    <div class="info">
      <h1 id="item-name">--</h1>
      <div class="tag" id="item-tag">--</div>
    </div>
  </div>
  <div class="filters">
    <div class="filter-chip active" data-filter="reserve">Reserve only</div>
    <div class="filter-chip" data-filter="all">Reserve + Chosen</div>
    <div class="filter-chip" data-filter="chosen">Chosen only</div>
  </div>
</header>

<main>
  <div class="description" id="description"></div>
  <div id="grid-host"></div>
</main>

<footer>
  <button class="nav-arrow" id="prev">‹</button>
  <button class="clear-pick" id="clear-pick">Clear</button>
  <button class="primary" id="save-all">Save All</button>
  <button class="nav-arrow" id="next">›</button>
</footer>

<div id="export-modal">
  <div class="modal-inner">
    <h3>Picks JSON</h3>
    <p style="font-size:12px;color:var(--muted);margin:0 0 8px 0;">
      Copy this or use Download. <code>apply_picks.py</code> writes it
      back into the per-category sprite maps.
    </p>
    <textarea id="export-text" readonly></textarea>
    <div class="actions">
      <button id="modal-copy">Copy</button>
      <button class="primary" id="modal-download">Download recent_picks.json</button>
      <button id="modal-close">Close</button>
    </div>
  </div>
</div>

<script>
const DATA = __DATA__;
const ITEMS = DATA.items;
const CANDIDATES = DATA.candidates;  // {category: {reserve: [...], chosen: [...]}}
const state = {};
ITEMS.forEach(it => {
  const key = it.category + '::' + it.name;
  state[key] = it.picked || '';
});

function itemCandidates(item) {
  return CANDIDATES[item.category] || { reserve: [], chosen: [] };
}

let activeIdx = 0;
let filterMode = 'reserve';

function renderCanvas(canvas, imgB64) {
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!imgB64) {
    ctx.fillStyle = '#222';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#666';
    ctx.font = '10px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('(none)', canvas.width / 2, canvas.height / 2);
    return;
  }
  const img = new Image();
  img.onload = () => {
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, img.naturalWidth, img.naturalHeight,
                  0, 0, canvas.width, canvas.height);
  };
  img.src = 'data:image/webp;base64,' + imgB64;
}

function getKey(item) { return item.category + '::' + item.name; }

function getPickedSprite(item) {
  const key = getKey(item);
  const pid = state[key];
  if (!pid) return null;
  const c = itemCandidates(item);
  return c.reserve.find(s => s.pid === pid)
      || c.chosen.find(s => s.pid === pid)
      || null;
}

function refreshTop(item) {
  document.getElementById('counter').textContent =
    `${activeIdx + 1} / ${ITEMS.length}`;
  const pickedCount = Object.values(state).filter(v => v).length;
  document.getElementById('picks-count').textContent =
    `${pickedCount} picked`;
  document.getElementById('progress-bar').style.width =
    `${(pickedCount / ITEMS.length) * 100}%`;

  const nameEl = document.getElementById('item-name');
  const badge = document.createElement('span');
  badge.className = 'badge ' + item.kind;
  badge.textContent = item.kind === 'gap' ? 'GAP' : 'AUTO';
  nameEl.innerHTML = '';
  nameEl.appendChild(badge);
  nameEl.appendChild(document.createTextNode(' ' + item.name));

  document.getElementById('item-tag').textContent =
    `${item.category} · ${item.meta}`;

  const picked = getPickedSprite(item);
  const previewWrap = document.getElementById('current-preview');
  previewWrap.classList.toggle('has-pick', !!state[getKey(item)]);
  const canvas = previewWrap.querySelector('canvas');
  if (picked) {
    renderCanvas(canvas, picked.img);
    document.getElementById('current-pid').textContent =
      picked.pid + ' (pick)';
  } else if (item.current) {
    renderCanvas(canvas, item.current_img);
    document.getElementById('current-pid').textContent =
      item.current + ' (cur)';
  } else {
    renderCanvas(canvas, '');
    document.getElementById('current-pid').textContent = '--';
  }

  const desc = document.getElementById('description');
  desc.innerHTML = '';
  if (item.description) {
    const d = document.createElement('div');
    d.textContent = item.description;
    desc.appendChild(d);
  }
  const n = document.createElement('div');
  n.className = 'note';
  n.textContent = item.note;
  desc.appendChild(n);
}

function buildTile(sprite, item, source) {
  const t = document.createElement('div');
  t.className = 'tile ' + source;
  if (sprite.pid === item.current) t.classList.add('current');
  if (state[getKey(item)] === sprite.pid) t.classList.add('picked');
  t.dataset.pid = sprite.pid;

  const canvas = document.createElement('canvas');
  canvas.width = 80; canvas.height = 80;
  t.appendChild(canvas);

  const tag = document.createElement('div');
  tag.className = 'source-tag';
  t.appendChild(tag);

  const pidEl = document.createElement('div');
  pidEl.className = 'pid';
  pidEl.textContent = sprite.pid;
  t.appendChild(pidEl);

  t.addEventListener('click', () => {
    const k = getKey(item);
    state[k] = (state[k] === sprite.pid) ? '' : sprite.pid;
    // Toggle picked state across all tiles for this item.
    document.querySelectorAll('.tile').forEach(el => {
      el.classList.toggle('picked',
        el.dataset.pid === state[k] && !!state[k]);
    });
    refreshTop(item);
    persistState();
  });

  renderCanvas(canvas, sprite.img);
  return t;
}

function renderGrid(item) {
  const host = document.getElementById('grid-host');
  host.innerHTML = '';

  const c = itemCandidates(item);
  let reserve = c.reserve;
  let chosen = c.chosen;
  if (filterMode === 'reserve') chosen = [];
  if (filterMode === 'chosen') reserve = [];

  if (reserve.length) {
    const label = document.createElement('div');
    label.className = 'section-label';
    label.innerHTML = `<span class="swatch reserve"></span>Reserve · ${reserve.length} candidates`;
    host.appendChild(label);
    const g = document.createElement('div');
    g.className = 'grid';
    reserve.forEach(s => g.appendChild(buildTile(s, item, 'reserve')));
    host.appendChild(g);
  }
  if (chosen.length) {
    const label = document.createElement('div');
    label.className = 'section-label';
    label.innerHTML = `<span class="swatch chosen"></span>Already in-game · ${chosen.length} candidates`;
    host.appendChild(label);
    const g = document.createElement('div');
    g.className = 'grid';
    chosen.forEach(s => g.appendChild(buildTile(s, item, 'chosen')));
    host.appendChild(g);
  }
  if (!reserve.length && !chosen.length) {
    const empty = document.createElement('div');
    empty.style.padding = '20px';
    empty.style.textAlign = 'center';
    empty.style.color = 'var(--muted)';
    empty.textContent = 'No candidates with this filter.';
    host.appendChild(empty);
  }
}

function gotoItem(idx) {
  activeIdx = Math.max(0, Math.min(ITEMS.length - 1, idx));
  const item = ITEMS[activeIdx];
  refreshTop(item);
  renderGrid(item);
  // Scroll to top so the new item's grid starts visible.
  window.scrollTo({ top: 0, behavior: 'instant' });
  persistState();
}

document.getElementById('prev').addEventListener('click',
  () => gotoItem(activeIdx - 1));
document.getElementById('next').addEventListener('click',
  () => gotoItem(activeIdx + 1));

document.getElementById('clear-pick').addEventListener('click', () => {
  const item = ITEMS[activeIdx];
  state[getKey(item)] = '';
  document.querySelectorAll('.tile').forEach(el => el.classList.remove('picked'));
  refreshTop(item);
  persistState();
});

document.querySelectorAll('.filter-chip').forEach(el => {
  el.addEventListener('click', () => {
    document.querySelectorAll('.filter-chip').forEach(c =>
      c.classList.toggle('active', c === el));
    filterMode = el.dataset.filter;
    renderGrid(ITEMS[activeIdx]);
  });
});

// Swipe nav (touch).
let touchStartX = null;
document.addEventListener('touchstart', e => {
  if (e.touches.length === 1) touchStartX = e.touches[0].clientX;
}, { passive: true });
document.addEventListener('touchend', e => {
  if (touchStartX == null) return;
  const dx = e.changedTouches[0].clientX - touchStartX;
  touchStartX = null;
  // Only react to horizontal swipes near header (avoid hijacking grid taps).
  if (e.changedTouches[0].clientY > 200) return;
  if (Math.abs(dx) > 60) {
    if (dx > 0) gotoItem(activeIdx - 1);
    else gotoItem(activeIdx + 1);
  }
}, { passive: true });

// Keyboard nav.
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'TEXTAREA') return;
  if (e.key === 'ArrowLeft') gotoItem(activeIdx - 1);
  else if (e.key === 'ArrowRight') gotoItem(activeIdx + 1);
});

// Export modal.
function buildPayload() {
  const picks = {};
  Object.entries(state).forEach(([k, v]) => { if (v) picks[k] = v; });
  return {
    version: 2,
    generated: new Date().toISOString(),
    total_items: ITEMS.length,
    picked: Object.values(picks).length,
    picks,
  };
}

document.getElementById('save-all').addEventListener('click', () => {
  const out = document.getElementById('export-text');
  out.value = JSON.stringify(buildPayload(), null, 2);
  document.getElementById('export-modal').classList.add('shown');
});
document.getElementById('modal-close').addEventListener('click', () => {
  document.getElementById('export-modal').classList.remove('shown');
});
document.getElementById('modal-copy').addEventListener('click', () => {
  const ta = document.getElementById('export-text');
  ta.select(); ta.setSelectionRange(0, ta.value.length);
  try {
    navigator.clipboard.writeText(ta.value);
  } catch (_) { document.execCommand('copy'); }
});
document.getElementById('modal-download').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(buildPayload(), null, 2)],
                        { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'recent_picks.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

// Persist picks + active index across reloads.
function persistState() {
  try {
    localStorage.setItem('wc_sprite_picks_v2', JSON.stringify({
      picks: state, activeIdx,
    }));
  } catch (_) {}
}
function restoreState() {
  try {
    const raw = localStorage.getItem('wc_sprite_picks_v2');
    if (!raw) return;
    const blob = JSON.parse(raw);
    if (blob && blob.picks) {
      Object.entries(blob.picks).forEach(([k, v]) => {
        if (k in state) state[k] = v;
      });
    }
    if (typeof blob.activeIdx === 'number') activeIdx = blob.activeIdx;
  } catch (_) {}
}

restoreState();
gotoItem(activeIdx);
</script>
</body>
</html>
"""


if __name__ == '__main__':
    main()
