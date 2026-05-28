"""
Mobile-first HTML picker for flagging sprites where the Gemini round-trip
swapped them for a different sprite (P170 went from pink round bottle to
green Erlenmeyer flask). For those, scrub_green_via_orig.py can't help
-- the right fix is to restore the orig art outright via restore_from_orig.

The picker shows each sprite as a pair: orig (pre-Gemini, RGB, the
reference) and current (post-scrub, RGBA on a stone backdrop, what's in
the pool now). Tap a pair to flag it for restore. Tap again to clear.
Export writes restore_pids.json next to the HTML.

Filter by category, sort by category or by "swap-likelihood" (a noisy
heuristic combining normalised-bbox shape IoU and dominant-colour
distance -- not reliable enough to auto-flag, useful as a starting
order). Mobile-friendly: 2-column grid, sticky toolbar.

Usage:
    python3 sprite_package/code/build_restore_picker.py \\
        --pool wizardscavern/data/canonical_pool_full.pkl \\
        --orig-pool /tmp/pool_orig.pkl \\
        --out sprite_package/code/restore_picker.html
"""

import argparse
import base64
import io
import json
import pickle
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("ERROR: Pillow and numpy required.  pip install Pillow numpy",
          file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scrub_green_via_orig as sgo


STONE_RGB = (45, 38, 32)


def _stone_b64(size):
    a = np.full((size, size, 3), STONE_RGB, dtype=np.uint8)
    rng = np.random.RandomState(0)
    arr = np.clip(a + rng.randint(-8, 8, (size, size, 3)), 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _detect_mime(b64):
    """Sniff the image format from the first few bytes of decoded base64."""
    head = base64.b64decode(b64[:32])
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    return "image/png"


def _bbox(mask):
    if not mask.any():
        return None
    ys = np.where(mask.any(axis=1))[0]
    xs = np.where(mask.any(axis=0))[0]
    return ys[0], xs[0], ys[-1] + 1, xs[-1] + 1


def _norm_mask(mask, size=64):
    bb = _bbox(mask)
    if bb is None:
        return None
    y0, x0, y1, x1 = bb
    crop = mask[y0:y1, x0:x1]
    im = Image.fromarray((crop * 255).astype(np.uint8))
    return np.asarray(im.resize((size, size), Image.NEAREST)) > 127


def _swap_score(cim, oim):
    """Heuristic. Higher = looks more like a Gemini swap.
    Combines low shape match with high colour distance."""
    if cim.mode not in ("RGBA", "LA"):
        return 0.0
    orig_rgb = np.asarray(oim.convert("RGB"), dtype=np.float32)
    bg = sgo._orig_bg_mask(orig_rgb)
    sprite_o = ~bg
    cur_rgba = np.asarray(cim.convert("RGBA"))
    sprite_c = cur_rgba[..., 3] > 128
    cur_rgb = cur_rgba[..., :3].astype(np.float32)
    if sprite_o.sum() < 50 or sprite_c.sum() < 50:
        return 0.0
    nmo = _norm_mask(sprite_o)
    nmc = _norm_mask(sprite_c)
    if nmo is None or nmc is None:
        return 0.0
    iou_n = (nmo & nmc).sum() / max((nmo | nmc).sum(), 1)
    co = orig_rgb[sprite_o].mean(axis=0)
    cc = cur_rgb[sprite_c].mean(axis=0)
    cdist = float(np.linalg.norm(co - cc))
    return cdist * (1.0 - iou_n)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--pool", required=True)
    ap.add_argument("--orig-pool", required=True)
    ap.add_argument("--out", required=True,
                    help="path to write the HTML file")
    ap.add_argument("--tile", type=int, default=96,
                    help="display size per sprite (default 96)")
    ap.add_argument("--top", type=int, default=0,
                    help="keep only the top N by swap-score (0 = all)")
    args = ap.parse_args()

    with open(args.pool, "rb") as f:
        pool = pickle.load(f)
    with open(args.orig_pool, "rb") as f:
        orig_pool = pickle.load(f)

    print(f"scoring {len(pool)} sprites...", file=sys.stderr)
    items = []
    for pid, ent in pool.items():
        if pid not in orig_pool:
            continue
        cur_b64 = ent["img_b64"]
        orig_b64 = orig_pool[pid]["img_b64"]
        cim = Image.open(io.BytesIO(base64.b64decode(cur_b64)))
        oim = Image.open(io.BytesIO(base64.b64decode(orig_b64)))
        try:
            score = _swap_score(cim, oim)
        except Exception:
            score = 0.0
        cat = ent.get("cat", "")
        gd = ent.get("game_data") or {}
        name = (gd.get("item_name") or gd.get("monster_name")
                or gd.get("room_type") or "")
        items.append({
            "pid": pid,
            "cat": cat,
            "name": str(name),
            "score": round(score, 2),
            "om": _detect_mime(orig_b64),
            "cm": _detect_mime(cur_b64),
            "orig": orig_b64,
            "cur": cur_b64,
        })
    items.sort(key=lambda r: (-r["score"], r["cat"], r["pid"]))
    if args.top > 0:
        items = items[: args.top]
    print(f"emitting {len(items)} entries to {args.out}", file=sys.stderr)

    cats = sorted({r["cat"] for r in items})
    stone_b64 = _stone_b64(args.tile)

    html = _HTML.format(
        items_json=json.dumps(items),
        cats_json=json.dumps(cats),
        stone_b64=stone_b64,
        tile=args.tile,
    )
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"wrote {args.out}  ({Path(args.out).stat().st_size // 1024} KB)",
          file=sys.stderr)


_HTML = r"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Restore-from-orig picker</title>
<style>
  :root {{
    --tile: {tile}px;
    --bg: #15151a;
    --panel: #1d1d24;
    --text: #e0e0e0;
    --muted: #999;
    --accent: #ff5f3b;
    --ok: #4ade80;
  }}
  html,body {{ margin:0; padding:0; background:var(--bg); color:var(--text);
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  header {{
    position: sticky; top: 0; z-index: 10;
    background: var(--panel); padding: 8px 10px;
    border-bottom: 1px solid #333;
    display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  }}
  header select, header input[type=number] {{
    background: #2a2a32; color: var(--text); border: 1px solid #444;
    border-radius: 4px; padding: 6px 8px; font-size: 14px;
  }}
  header label {{ font-size: 13px; color: var(--muted); }}
  header .count {{ flex: 1; text-align: right; font-size: 13px; color: var(--muted); }}
  header button {{
    background: var(--accent); color: white; border: none;
    border-radius: 4px; padding: 8px 12px; font-weight: 600;
    font-size: 14px; cursor: pointer;
  }}
  #grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(calc(var(--tile)*2 + 8px), 1fr));
    gap: 8px; padding: 8px;
  }}
  .cell {{
    background: #25252e; border-radius: 6px; padding: 6px;
    border: 3px solid transparent;
    cursor: pointer; user-select: none;
    -webkit-tap-highlight-color: transparent;
  }}
  .cell.flagged {{ border-color: var(--accent); background: #3a1f1f; }}
  .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }}
  .img-wrap {{
    width: 100%; aspect-ratio: 1; background-size: cover;
    image-rendering: pixelated; image-rendering: crisp-edges;
    background-position: center;
  }}
  .img-wrap.orig {{ background-color: #0a0a0a; }}
  .img-wrap.cur {{ background-image: url(data:image/png;base64,{stone_b64});
                  background-size: 100% 100%; }}
  .img-wrap > img {{
    width: 100%; height: 100%; display: block;
    image-rendering: pixelated; image-rendering: crisp-edges;
  }}
  .meta {{ font-size: 11px; color: var(--muted); margin-top: 4px;
          display: flex; justify-content: space-between; gap: 4px; }}
  .meta .pid {{ font-weight: 600; color: var(--text); }}
  .meta .name {{ flex: 1; overflow: hidden; text-overflow: ellipsis;
                white-space: nowrap; text-align: center; }}
  .meta .score {{ color: #888; }}
  .cell.flagged .meta .score {{ color: var(--accent); font-weight: 600; }}
  #export-modal {{
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8);
    z-index: 20; align-items: center; justify-content: center; padding: 20px;
  }}
  #export-modal.open {{ display: flex; }}
  #export-modal .box {{
    background: var(--panel); padding: 16px; border-radius: 8px;
    max-width: 600px; width: 100%; max-height: 80vh; overflow: auto;
  }}
  #export-modal h2 {{ margin: 0 0 8px; font-size: 16px; }}
  #export-modal pre {{ background: #0a0a0a; padding: 12px; border-radius: 4px;
                      font-size: 12px; color: #aaa; white-space: pre-wrap;
                      word-break: break-all; overflow-x: auto; max-height: 40vh; }}
  #export-modal .actions {{ display: flex; gap: 8px; margin-top: 12px; }}
  #export-modal button {{ flex: 1; }}
  .close-btn {{ background: #444 !important; }}
</style>

<header>
  <label>Cat <select id="cat-filter"><option value="">all</option></select></label>
  <label>Sort
    <select id="sort">
      <option value="score">swap-score (noisy)</option>
      <option value="cat">category</option>
      <option value="pid">pid</option>
    </select>
  </label>
  <label>Min score <input type="number" id="min-score" value="0" min="0" max="200" style="width:60px"></label>
  <span class="count"><span id="flag-count">0</span> flagged / <span id="vis-count">0</span> shown</span>
  <button id="export-btn">Export</button>
</header>

<div id="grid"></div>

<div id="export-modal">
  <div class="box">
    <h2>Flagged pids (<span id="modal-count">0</span>)</h2>
    <p style="font-size:13px;color:var(--muted);margin:0 0 8px">
      Copy the JSON list and either paste it where you want it, or save as a
      .json/.txt and run:<br>
      <code style="color:#ddd">restore_from_orig.py --pool POOL --orig-pool ORIG --pids-file FILE</code>
    </p>
    <pre id="export-json"></pre>
    <div class="actions">
      <button id="copy-btn">Copy to clipboard</button>
      <button id="download-btn">Download JSON</button>
      <button id="close-btn" class="close-btn">Close</button>
    </div>
  </div>
</div>

<script>
const ITEMS = {items_json};
const CATS = {cats_json};
const flagged = new Set();

const grid = document.getElementById('grid');
const catFilter = document.getElementById('cat-filter');
const sortSel = document.getElementById('sort');
const minScore = document.getElementById('min-score');
const flagCount = document.getElementById('flag-count');
const visCount = document.getElementById('vis-count');

CATS.forEach(c => {{
  const o = document.createElement('option');
  o.value = c; o.textContent = c;
  catFilter.appendChild(o);
}});

function render() {{
  const cat = catFilter.value;
  const sort = sortSel.value;
  const minS = parseFloat(minScore.value) || 0;
  let list = ITEMS.filter(r => (!cat || r.cat === cat) && r.score >= minS);
  if (sort === 'cat') list.sort((a,b) => a.cat.localeCompare(b.cat) || a.pid.localeCompare(b.pid));
  else if (sort === 'pid') list.sort((a,b) => a.pid.localeCompare(b.pid));
  else list.sort((a,b) => b.score - a.score || a.pid.localeCompare(b.pid));

  grid.innerHTML = '';
  for (const r of list) {{
    const cell = document.createElement('div');
    cell.className = 'cell' + (flagged.has(r.pid) ? ' flagged' : '');
    cell.dataset.pid = r.pid;
    cell.innerHTML = `
      <div class="pair">
        <div class="img-wrap orig"><img alt="${{r.pid}} orig" src="data:${{r.om}};base64,${{r.orig}}"></div>
        <div class="img-wrap cur"><img alt="${{r.pid}} cur" src="data:${{r.cm}};base64,${{r.cur}}"></div>
      </div>
      <div class="meta">
        <span class="pid">${{r.pid}}</span>
        <span class="name">${{r.name || r.cat}}</span>
        <span class="score">${{r.score.toFixed(0)}}</span>
      </div>
    `;
    cell.addEventListener('click', () => {{
      if (flagged.has(r.pid)) {{ flagged.delete(r.pid); cell.classList.remove('flagged'); }}
      else {{ flagged.add(r.pid); cell.classList.add('flagged'); }}
      flagCount.textContent = flagged.size;
    }});
    grid.appendChild(cell);
  }}
  visCount.textContent = list.length;
  flagCount.textContent = flagged.size;
}}

catFilter.addEventListener('change', render);
sortSel.addEventListener('change', render);
minScore.addEventListener('input', render);

const modal = document.getElementById('export-modal');
const exportBtn = document.getElementById('export-btn');
const closeBtn = document.getElementById('close-btn');
const copyBtn = document.getElementById('copy-btn');
const downloadBtn = document.getElementById('download-btn');
const exportJson = document.getElementById('export-json');
const modalCount = document.getElementById('modal-count');

function showModal() {{
  const sorted = [...flagged].sort();
  exportJson.textContent = JSON.stringify(sorted, null, 2);
  modalCount.textContent = sorted.length;
  modal.classList.add('open');
}}
exportBtn.addEventListener('click', showModal);
closeBtn.addEventListener('click', () => modal.classList.remove('open'));
modal.addEventListener('click', (e) => {{ if (e.target === modal) modal.classList.remove('open'); }});
copyBtn.addEventListener('click', async () => {{
  try {{
    await navigator.clipboard.writeText(exportJson.textContent);
    copyBtn.textContent = 'Copied!';
    setTimeout(() => copyBtn.textContent = 'Copy to clipboard', 1200);
  }} catch (e) {{
    copyBtn.textContent = 'Failed -- select manually';
  }}
}});
downloadBtn.addEventListener('click', () => {{
  const blob = new Blob([exportJson.textContent], {{type: 'application/json'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'restore_pids.json';
  a.click();
  URL.revokeObjectURL(url);
}});

render();
</script>
"""


if __name__ == "__main__":
    main()
