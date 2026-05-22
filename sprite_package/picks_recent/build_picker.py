"""
Build a self-contained HTML picker for the b403-b412 sprite additions the
user wants to hand-pick instead of auto-assigning.

Scope: 4 cantrip-tier spells with no current sprite assignment (Detect
Monster / Hold Monster / Light / Mind Touch) + 8 recent spells that
landed pids during balance work (Mind Blast / Earthquake / Holy Smite /
Psychic Scream / Meteor Strike / Inferno / Mage Armor / Spectral Hand)
+ 1 accessory (Hourglass Talisman, currently sharing Heartstone Pendant
sprites).

Run:
    python3 sprite_package/picks_recent/build_picker.py

Writes:
    sprite_package/picks_recent/picker.html

Open picker.html in a browser, click a candidate sprite under each item,
hit "Download recent_picks.json", then run apply_picks.py to write the
edits back into the per-category sprite maps.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, _ROOT)

from wizardscavern.sprites import get_image_b64  # noqa: E402
from wizardscavern.sprites.pool import _load_pool  # noqa: E402
from wizardscavern.sprites.spells import _SPELLS_NAMED, _SPELLS_POOL  # noqa: E402
from wizardscavern.sprites.accessories import _ACCESSORIES_MAP  # noqa: E402
from wizardscavern.item_templates import SPELL_TEMPLATES  # noqa: E402


# --- Scope ----------------------------------------------------------------

# Spells the user wants to assign sprites for. Each entry is (name, why).
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
    ('Mage Armor',      'auto', 'b403 -- shares I047 with Divine Shield (orphan)'),
    ('Spectral Hand',   'auto', 'b403 -- shares I058 with Stone Skin (orphan)'),
]

ACCESSORY_PICKS = [
    ('Hourglass Talisman', 'auto',
     'b403 -- shares pendant sprites with Heartstone Pendant; '
     'CLAUDE.md note suggests promoting a dedicated sand/glass sprite'),
]


def _spell_info(name):
    """Pull description / tier metadata for the picker card."""
    for s in SPELL_TEMPLATES:
        if s.name == name:
            return {
                'description': s.description,
                'level': s.level,
                'mana_cost': s.mana_cost,
                'damage_type': s.damage_type or 'utility',
                'is_cantrip': bool(getattr(s, 'is_cantrip', False)),
            }
    return {
        'description': '(not in SPELL_TEMPLATES -- declared in items.py only)',
        'level': '?',
        'mana_cost': '?',
        'damage_type': '?',
        'is_cantrip': False,
    }


def _current_spell_pid(name):
    return _SPELLS_NAMED.get(name) or ''


def _current_accessory_variants(name):
    return _ACCESSORIES_MAP.get(name) or []


# Build the per-item data for the page.
items = []

# --- Spells: candidate set is _SPELLS_POOL (49 spell-themed sprites) -----
spell_candidates = []
pool = _load_pool()
for pid in _SPELLS_POOL:
    img = get_image_b64(pid)
    if not img:
        continue
    spell_candidates.append({'pid': pid, 'img': img})

for name, kind, note in SPELL_PICKS:
    info = _spell_info(name)
    current = _current_spell_pid(name)
    items.append({
        'category': 'spells',
        'name': name,
        'kind': kind,
        'note': note,
        'description': info['description'],
        'meta': f"L{info['level']} {info['mana_cost']} MP {info['damage_type']}"
                + (' cantrip' if info['is_cantrip'] else ''),
        'current': current,
        'current_img': get_image_b64(current) if current else '',
        'candidates': spell_candidates,
    })

# --- Accessories: candidate set is all cat=='accessories' pids in pool --
acc_candidates = []
for pid, entry in sorted(pool.items()):
    if entry.get('cat') == 'accessories':
        img = entry.get('img_b64', '')
        if img:
            acc_candidates.append({'pid': pid, 'img': img})

for name, kind, note in ACCESSORY_PICKS:
    variants = _current_accessory_variants(name)
    current_pid = variants[0][0] if variants else ''
    items.append({
        'category': 'accessories',
        'name': name,
        'kind': kind,
        'note': note,
        'description': '',
        'meta': f"variants currently: {len(variants)}",
        'current': current_pid,
        'current_img': get_image_b64(current_pid) if current_pid else '',
        'candidates': acc_candidates,
    })


# Seed any existing picks from a previous session.
_PICKS_PATH = os.path.join(_HERE, 'recent_picks.json')
existing_picks = {}
if os.path.exists(_PICKS_PATH):
    with open(_PICKS_PATH, 'r') as f:
        try:
            existing_picks = json.load(f).get('picks', {})
        except Exception:
            existing_picks = {}

# Apply existing picks to seed the UI (key format: "category::name").
for it in items:
    key = f"{it['category']}::{it['name']}"
    if key in existing_picks:
        it['picked'] = existing_picks[key]
    else:
        it['picked'] = ''


embedded = json.dumps(items)

html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Sprite Picker -- Recent Additions (b403-b412)</title>
<style>
  body { background:#1a1a1a; color:#eee; font-family: system-ui, sans-serif; margin: 0; padding: 0; }
  header { position: sticky; top: 0; background:#111; padding: 12px 16px;
           border-bottom: 1px solid #333; z-index: 10; }
  h1 { margin: 0 0 6px 0; font-size: 18px; color: #FFD700; }
  .toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .toolbar button { background:#333; color:#eee; border:1px solid #555;
                    padding: 6px 12px; cursor:pointer; border-radius: 4px;
                    font-size: 13px; }
  .toolbar button:hover { background:#444; }
  .counts { font-size: 12px; color: #aaa; margin-left: 8px; }
  #out { width: 100%; height: 200px; background:#0a0a0a; color:#9f9;
         font-family: monospace; font-size: 12px; padding: 8px;
         border:1px solid #333; box-sizing: border-box; display: none;
         margin-top: 8px; }
  #out.shown { display: block; }
  main { padding: 16px; max-width: 1200px; margin: 0 auto; }
  .card { background:#222; border: 1px solid #333; border-radius: 8px;
          padding: 14px; margin-bottom: 18px; }
  .card-head { display: flex; align-items: flex-start; gap: 14px;
               border-bottom: 1px solid #2a2a2a; padding-bottom: 10px;
               margin-bottom: 10px; }
  .card-current { flex: 0 0 88px; text-align: center; }
  .card-current canvas { width: 72px; height: 72px;
                         image-rendering: pixelated; image-rendering: crisp-edges;
                         background: #0a0a0a; border: 2px solid #444;
                         border-radius: 4px; display:block; margin: 0 auto; }
  .card-current .pid { font-family: monospace; font-size: 11px;
                       color: #888; margin-top: 3px; }
  .card-current.has-pick canvas { border-color: #FFD700; }
  .card-meta { flex: 1 1 auto; }
  .card-meta h2 { margin: 0; font-size: 16px; color: #FFD700; }
  .card-meta .tagline { font-size: 12px; color: #aaa; margin: 3px 0; }
  .card-meta .desc { font-size: 13px; color: #ddd; margin: 6px 0 0 0; }
  .card-meta .note { font-size: 11px; color: #888; margin-top: 6px;
                     font-style: italic; }
  .badge { display: inline-block; padding: 2px 6px; font-size: 10px;
           font-weight: bold; border-radius: 3px; margin-right: 4px;
           vertical-align: middle; }
  .badge.gap  { background:#a02020; color:#fff; }
  .badge.auto { background:#404080; color:#fff; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
          gap: 6px; padding-top: 4px; }
  .tile { background:#181818; border: 2px solid #2a2a2a; border-radius: 4px;
          padding: 4px; text-align: center; cursor: pointer;
          transition: border-color 0.12s, transform 0.08s; }
  .tile:hover { border-color: #666; }
  .tile.picked { border-color: #FFD700; transform: scale(1.04);
                 box-shadow: 0 0 8px rgba(255,215,0,0.4); }
  .tile.current { border-color: #4a90e2; }
  .tile canvas { width: 56px; height: 56px;
                 image-rendering: pixelated; image-rendering: crisp-edges;
                 background: #0a0a0a; display:block; margin: 0 auto; }
  .tile .pid { font-family: monospace; font-size: 10px;
               color: #888; margin-top: 2px; }
  .reset-btn { background:#3a2020; color:#fcc; border:1px solid #553;
               padding: 2px 8px; cursor:pointer; border-radius: 3px;
               font-size: 11px; margin-left: 6px; }
  .reset-btn:hover { background:#552020; }
</style>
</head>
<body>
<header>
  <h1>Sprite Picker -- Recent Additions (b403-b412)</h1>
  <div class="toolbar">
    <button id="export">Show JSON</button>
    <button id="download">Download recent_picks.json</button>
    <button id="clear">Clear all picks</button>
    <span class="counts" id="counts"></span>
  </div>
  <textarea id="out" readonly></textarea>
</header>
<main id="main"></main>
<script>
const ITEMS = __DATA__;
const state = {};
ITEMS.forEach(it => {
  const key = it.category + '::' + it.name;
  state[key] = it.picked || '';
});

function refreshCounts() {
  const picked = Object.values(state).filter(v => v).length;
  document.getElementById('counts').textContent =
    `Picked ${picked}/${ITEMS.length}`;
}

function renderCanvas(canvas, imgB64) {
  if (!imgB64) {
    const ctx = canvas.getContext('2d');
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
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, img.naturalWidth, img.naturalHeight,
                  0, 0, canvas.width, canvas.height);
  };
  img.src = 'data:image/webp;base64,' + imgB64;
}

function updateCurrentTile(item) {
  const wrap = document.getElementById('current-' + item.idx);
  const key = item.category + '::' + item.name;
  const pickedPid = state[key];
  const effectivePid = pickedPid || item.current;
  const candidate = item.candidates.find(c => c.pid === effectivePid);
  const img = candidate ? candidate.img : (effectivePid ? item.current_img : '');
  wrap.classList.toggle('has-pick', !!pickedPid);
  wrap.querySelector('.pid').textContent =
    pickedPid ? pickedPid + ' (picked)' : (item.current || '(none)');
  renderCanvas(wrap.querySelector('canvas'), img);
}

function setPick(item, pid) {
  const key = item.category + '::' + item.name;
  state[key] = (state[key] === pid) ? '' : pid;
  const card = document.getElementById('card-' + item.idx);
  card.querySelectorAll('.tile').forEach(t => {
    t.classList.toggle('picked', t.dataset.pid === state[key] && !!state[key]);
  });
  updateCurrentTile(item);
  refreshCounts();
}

function buildCard(item, idx) {
  item.idx = idx;
  const card = document.createElement('section');
  card.className = 'card';
  card.id = 'card-' + idx;

  const head = document.createElement('div');
  head.className = 'card-head';

  // Current preview.
  const cur = document.createElement('div');
  cur.className = 'card-current';
  cur.id = 'current-' + idx;
  const curCanvas = document.createElement('canvas');
  curCanvas.width = 72; curCanvas.height = 72;
  cur.appendChild(curCanvas);
  const curPid = document.createElement('div');
  curPid.className = 'pid';
  curPid.textContent = item.current || '(none)';
  cur.appendChild(curPid);
  head.appendChild(cur);

  // Item meta.
  const meta = document.createElement('div');
  meta.className = 'card-meta';
  const h2 = document.createElement('h2');
  const badge = document.createElement('span');
  badge.className = 'badge ' + item.kind;
  badge.textContent = item.kind === 'gap' ? 'UNASSIGNED' : 'AUTO-PICKED';
  h2.appendChild(badge);
  h2.appendChild(document.createTextNode(item.name));
  meta.appendChild(h2);
  const tagline = document.createElement('div');
  tagline.className = 'tagline';
  tagline.textContent = item.category + ' · ' + item.meta;
  meta.appendChild(tagline);
  if (item.description) {
    const desc = document.createElement('div');
    desc.className = 'desc';
    desc.textContent = item.description;
    meta.appendChild(desc);
  }
  const note = document.createElement('div');
  note.className = 'note';
  note.textContent = item.note;
  meta.appendChild(note);
  // Reset button per card.
  const reset = document.createElement('button');
  reset.className = 'reset-btn';
  reset.textContent = 'Clear pick';
  reset.addEventListener('click', () => {
    const key = item.category + '::' + item.name;
    state[key] = '';
    card.querySelectorAll('.tile').forEach(t => t.classList.remove('picked'));
    updateCurrentTile(item);
    refreshCounts();
  });
  meta.appendChild(reset);
  head.appendChild(meta);
  card.appendChild(head);

  // Candidate grid.
  const grid = document.createElement('div');
  grid.className = 'grid';
  const key = item.category + '::' + item.name;
  item.candidates.forEach(c => {
    const t = document.createElement('div');
    t.className = 'tile';
    if (c.pid === item.current) t.classList.add('current');
    if (state[key] === c.pid) t.classList.add('picked');
    t.dataset.pid = c.pid;
    const canvas = document.createElement('canvas');
    canvas.width = 56; canvas.height = 56;
    t.appendChild(canvas);
    const pidEl = document.createElement('div');
    pidEl.className = 'pid';
    pidEl.textContent = c.pid;
    t.appendChild(pidEl);
    t.addEventListener('click', () => setPick(item, c.pid));
    grid.appendChild(t);
    renderCanvas(canvas, c.img);
  });
  card.appendChild(grid);

  return card;
}

function buildPayload() {
  const picks = {};
  Object.entries(state).forEach(([k, v]) => { if (v) picks[k] = v; });
  return {
    version: 1,
    generated: new Date().toISOString(),
    total_items: ITEMS.length,
    picked: Object.values(picks).length,
    picks,
  };
}

document.getElementById('export').addEventListener('click', () => {
  const out = document.getElementById('out');
  out.classList.add('shown');
  out.value = JSON.stringify(buildPayload(), null, 2);
  out.select();
});

document.getElementById('download').addEventListener('click', () => {
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

document.getElementById('clear').addEventListener('click', () => {
  if (!confirm('Clear all picks?')) return;
  Object.keys(state).forEach(k => { state[k] = ''; });
  document.querySelectorAll('.tile.picked').forEach(t => t.classList.remove('picked'));
  ITEMS.forEach(updateCurrentTile);
  refreshCounts();
});

const mainEl = document.getElementById('main');
ITEMS.forEach((it, i) => mainEl.appendChild(buildCard(it, i)));
ITEMS.forEach(updateCurrentTile);
refreshCounts();
</script>
</body>
</html>
"""

html = html.replace('__DATA__', embedded)

out_path = os.path.join(_HERE, 'picker.html')
with open(out_path, 'w') as f:
    f.write(html)

# Size-aware reporting -- this file can get chunky because every tile
# bundles a webp data URI inline.
size_mb = os.path.getsize(out_path) / (1024 * 1024)
print(f"Wrote {out_path}")
print(f"  items={len(items)}  spell_candidates={len(spell_candidates)}  "
      f"accessory_candidates={len(acc_candidates)}")
print(f"  size={size_mb:.2f} MB")
