"""
Build a self-contained HTML picker for assigning the 73 round-8 character
sprites to one of: Human / Elf / Dwarf / Unassigned.

Run:
    python3 sprite_package/picks_characters/build_picker.py

Writes:
    sprite_package/picks_characters/picker.html

Open picker.html in a browser, click a race button under each portrait,
then hit "Export JSON" at the top — copy the JSON back to Claude (or save
it as character_picks.json next to this script).
"""
import json
import os
import sys

# Make the wizardscavern package importable when running from repo root.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, _ROOT)

from wizardscavern.sprites import characters as _csprites  # noqa: E402
from wizardscavern.sprites import get_image_b64  # noqa: E402

# Load any existing assignments so re-running the builder seeds the UI.
_PICKS_PATH = os.path.join(_HERE, 'character_picks.json')
existing_picks = {}
if os.path.exists(_PICKS_PATH):
    with open(_PICKS_PATH, 'r') as f:
        try:
            existing_picks = json.load(f).get('assignments', {})
        except Exception:
            existing_picks = {}

tiles = []
for idx, pid in enumerate(_csprites._CHARACTERS_POOL):
    img_b64 = get_image_b64(pid)
    if not img_b64:
        continue
    current = existing_picks.get(pid, '')
    tiles.append({
        'idx': idx,
        'pid': pid,
        'img': img_b64,
        'race': current,
    })

# Embed the data as JSON in the page; JS handles the rest.
embedded = json.dumps(tiles)

html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Character Sprite Race Picker</title>
<style>
  body { background:#1a1a1a; color:#eee; font-family: system-ui, sans-serif; margin: 0; padding: 0; }
  header { position: sticky; top: 0; background:#111; padding: 12px 16px; border-bottom: 1px solid #333; z-index: 10; }
  h1 { margin: 0 0 6px 0; font-size: 18px; color: #FFD700; }
  .toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .toolbar button { background:#333; color:#eee; border:1px solid #555; padding: 6px 12px; cursor:pointer; border-radius: 4px; font-size: 13px; }
  .toolbar button:hover { background:#444; }
  .counts { font-size: 12px; color: #aaa; margin-left: 8px; }
  .filters { font-size: 12px; color: #ccc; }
  .filters label { margin-right: 10px; cursor: pointer; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; padding: 16px; }
  .tile { background:#222; border: 2px solid #333; border-radius: 6px; padding: 8px; text-align: center; transition: border-color 0.15s; }
  .tile.race-human { border-color: #4a90e2; }
  .tile.race-elf   { border-color: #50c878; }
  .tile.race-dwarf { border-color: #d97706; }
  .tile canvas { width: 96px; height: 96px; image-rendering: pixelated; image-rendering: crisp-edges; display:block; margin: 0 auto; background: #0a0a0a; border-radius: 4px; }
  .pid { font-family: monospace; font-size: 11px; color: #888; margin-top: 4px; }
  .races { display: flex; gap: 4px; margin-top: 6px; justify-content: center; flex-wrap: wrap; }
  .races button { background:#333; color:#ccc; border:1px solid #555; border-radius: 3px; padding: 3px 6px; cursor:pointer; font-size: 11px; flex: 1 1 0; min-width: 0; }
  .races button:hover { background:#444; }
  .races button.active.human { background:#4a90e2; color:#fff; border-color:#4a90e2; }
  .races button.active.elf   { background:#50c878; color:#fff; border-color:#50c878; }
  .races button.active.dwarf { background:#d97706; color:#fff; border-color:#d97706; }
  .races button.active.none  { background:#666; color:#fff; border-color:#666; }
  #out { width: 100%; height: 200px; background:#0a0a0a; color:#9f9; font-family: monospace; font-size: 12px; padding: 8px; border:1px solid #333; box-sizing: border-box; display: none; }
  #out.shown { display: block; }
</style>
</head>
<body>
<header>
  <h1>Character Sprite Race Picker</h1>
  <div class="toolbar">
    <button id="export">Export JSON</button>
    <button id="download">Download character_picks.json</button>
    <button id="clear">Clear all</button>
    <span class="counts" id="counts"></span>
    <span class="filters">
      Show:
      <label><input type="checkbox" class="filter" value="human" checked> Human</label>
      <label><input type="checkbox" class="filter" value="elf" checked> Elf</label>
      <label><input type="checkbox" class="filter" value="dwarf" checked> Dwarf</label>
      <label><input type="checkbox" class="filter" value="" checked> Unassigned</label>
    </span>
  </div>
  <textarea id="out" readonly></textarea>
</header>
<div class="grid" id="grid"></div>
<script>
const TILES = __DATA__;
const RACES = ['human', 'elf', 'dwarf'];
const state = {};
TILES.forEach(t => { state[t.pid] = t.race || ''; });

function refreshCounts() {
  const c = { human: 0, elf: 0, dwarf: 0, none: 0 };
  Object.values(state).forEach(r => {
    if (r === 'human') c.human++;
    else if (r === 'elf') c.elf++;
    else if (r === 'dwarf') c.dwarf++;
    else c.none++;
  });
  document.getElementById('counts').textContent =
    `Human: ${c.human}  Elf: ${c.elf}  Dwarf: ${c.dwarf}  Unassigned: ${c.none}  (Total ${TILES.length})`;
}

function applyFilter() {
  const allowed = new Set(
    Array.from(document.querySelectorAll('.filter:checked')).map(el => el.value)
  );
  document.querySelectorAll('.tile').forEach(tile => {
    const r = state[tile.dataset.pid] || '';
    tile.style.display = allowed.has(r) ? '' : 'none';
  });
}

function setRace(pid, race) {
  state[pid] = race;
  const tile = document.querySelector(`[data-pid="${pid}"]`);
  tile.classList.remove('race-human', 'race-elf', 'race-dwarf');
  if (race) tile.classList.add(`race-${race}`);
  tile.querySelectorAll('.races button').forEach(b => {
    b.classList.remove('active', 'human', 'elf', 'dwarf', 'none');
    if (b.dataset.race === race) {
      b.classList.add('active');
      b.classList.add(race || 'none');
    }
  });
  refreshCounts();
  applyFilter();
}

function buildTile(t) {
  const div = document.createElement('div');
  div.className = 'tile' + (t.race ? ' race-' + t.race : '');
  div.dataset.pid = t.pid;
  const canvas = document.createElement('canvas');
  canvas.width = 64; canvas.height = 64;
  div.appendChild(canvas);
  const pidEl = document.createElement('div');
  pidEl.className = 'pid';
  pidEl.textContent = t.pid;
  div.appendChild(pidEl);
  const races = document.createElement('div');
  races.className = 'races';
  [['H', 'human'], ['E', 'elf'], ['D', 'dwarf'], ['-', '']].forEach(([label, race]) => {
    const b = document.createElement('button');
    b.textContent = label;
    b.dataset.race = race;
    if (state[t.pid] === race) {
      b.classList.add('active', race || 'none');
    }
    b.addEventListener('click', () => setRace(t.pid, race));
    races.appendChild(b);
  });
  div.appendChild(races);
  const img = new Image();
  img.onload = () => {
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img, 0, 0, img.naturalWidth, img.naturalHeight, 0, 0, 64, 64);
  };
  img.src = 'data:image/webp;base64,' + t.img;
  return div;
}

function buildPayload() {
  const assignments = {};
  Object.entries(state).forEach(([pid, r]) => { if (r) assignments[pid] = r; });
  return {
    version: 1,
    counts: {
      human: Object.values(state).filter(r => r === 'human').length,
      elf:   Object.values(state).filter(r => r === 'elf').length,
      dwarf: Object.values(state).filter(r => r === 'dwarf').length,
      unassigned: Object.values(state).filter(r => !r).length,
      total: TILES.length,
    },
    assignments,
  };
}

document.getElementById('export').addEventListener('click', () => {
  const out = document.getElementById('out');
  out.classList.add('shown');
  out.value = JSON.stringify(buildPayload(), null, 2);
  out.select();
});

document.getElementById('download').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(buildPayload(), null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'character_picks.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

document.getElementById('clear').addEventListener('click', () => {
  if (!confirm('Clear all race assignments?')) return;
  Object.keys(state).forEach(pid => setRace(pid, ''));
});

document.querySelectorAll('.filter').forEach(el =>
  el.addEventListener('change', applyFilter));

const grid = document.getElementById('grid');
TILES.forEach(t => grid.appendChild(buildTile(t)));
refreshCounts();
applyFilter();
</script>
</body>
</html>
"""

html = html.replace('__DATA__', embedded)

out_path = os.path.join(_HERE, 'picker.html')
with open(out_path, 'w') as f:
    f.write(html)
print(f"Wrote {out_path} with {len(tiles)} tiles "
      f"({sum(1 for t in tiles if t['race'])} pre-assigned).")
