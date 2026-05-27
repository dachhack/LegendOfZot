"""
Build a mobile-first HTML picker for flagging sprites that still carry
residual background-green (filled openings etc.) and need a green cut.

Residual key-green and genuinely green art are the same colour, so no
automatic filter can separate them -- this hands the judgement to a human.
Tap every sprite that has background-green to remove; leave green art
(slimes, potions, green pools) alone. Export writes greenfix_pids.json,
which apply_greenfix.py then cuts green from.

Likely offenders are PRE-FLAGGED (and the grid is sorted worst-first) by
comparing each sprite to the pre-greening original: green that's present
now but wasn't before is contamination. Pass --orig-pool to enable that;
without it, nothing is pre-flagged and you select everything by hand.

Usage:
    python3 sprite_package/code/build_greenfix_picker.py \
        --pool wizardscavern/data/canonical_pool_full.pkl \
        --orig-pool /tmp/pool_orig.pkl \
        --out sprite_package/code/greenfix_picker.html
"""

import argparse
import base64
import io
import json
import pickle
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("ERROR: Pillow and numpy required.  pip install Pillow numpy", file=sys.stderr)
    sys.exit(1)


def _green_count(rgb, opaque):
    gex = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
    return int(((gex > 30) & opaque).sum())


def added_green(cur_b64, orig_b64):
    """How many MORE green pixels exist now than in the pre-greening original.

    Alignment-free (a count, not a per-pixel diff): a sprite that was already
    green (a slime, a green potion) has a similar green count before and after,
    so it scores ~0; a sprite that gained a filled green region scores high.
    """
    c = np.asarray(Image.open(io.BytesIO(base64.b64decode(cur_b64))).convert("RGBA")
                   .resize((96, 96)), dtype=int)
    o = np.asarray(Image.open(io.BytesIO(base64.b64decode(orig_b64))).convert("RGB")
                   .resize((96, 96)), dtype=int)
    cur = _green_count(c[..., :3], c[..., 3] > 128)
    orig = _green_count(o, np.ones(o.shape[:2], bool))
    return max(0, cur - orig)


TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Green-fix picker</title>
<style>
  body{margin:0;background:#15171a;color:#ddd;font:14px system-ui,sans-serif}
  #bar{position:sticky;top:0;background:#1f2228;padding:8px;display:flex;
       gap:6px;flex-wrap:wrap;align-items:center;border-bottom:1px solid #333;z-index:5}
  #bar button,#bar select{background:#2c313a;color:#ddd;border:1px solid #444;
       border-radius:5px;padding:6px 9px;font-size:13px}
  #bar button.on{background:#3a5;border-color:#4c7}
  #count{font-weight:bold;margin-left:auto}
  #grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(84px,1fr));
        gap:4px;padding:6px}
  .cell{position:relative;border-radius:5px;overflow:hidden;cursor:pointer;
        outline:2px solid transparent}
  .cell img{width:100%;display:block;image-rendering:pixelated;aspect-ratio:1}
  .cell .lbl{position:absolute;left:0;bottom:0;right:0;font-size:9px;
        background:rgba(0,0,0,.55);padding:1px 2px;white-space:nowrap;overflow:hidden}
  .cell.flag{outline-color:#ff3b3b}
  .cell.flag::after{content:"\\2715";position:absolute;top:2px;right:3px;
        color:#ff3b3b;font-weight:bold;text-shadow:0 0 3px #000}
  /* backdrops to reveal green */
  body.bg-check .cell{background:
     conic-gradient(#cfcfcf 90deg,#888 0 180deg,#cfcfcf 0 270deg,#888 0) 0 0/16px 16px}
  body.bg-dark .cell{background:#181818}
  body.bg-white .cell{background:#fff}
  body.bg-mag .cell{background:#f0f}
</style></head>
<body class="bg-check">
<div id="bar">
  <strong>Tap sprites with background-green to remove</strong>
  <button onclick="setbg('check')">Checker</button>
  <button onclick="setbg('dark')">Dark</button>
  <button onclick="setbg('white')">White</button>
  <button onclick="setbg('mag')">Magenta</button>
  <select id="cat" onchange="render()"></select>
  <button id="onlyflag" onclick="toggleOnly()">Show flagged only</button>
  <span id="count"></span>
  <button onclick="exportPids()" style="background:#3a5;border-color:#4c7">Export</button>
</div>
<div id="grid"></div>
<textarea id="out" style="width:100%;height:80px;display:none;background:#111;color:#6f6"></textarea>
<script>
const DATA=__DATA__;
const flagged=new Set(DATA.filter(d=>d.pre).map(d=>d.pid));
let onlyFlag=false;
function setbg(b){document.body.className='bg-'+b;}
function toggleOnly(){onlyFlag=!onlyFlag;document.getElementById('onlyflag').classList.toggle('on',onlyFlag);render();}
function cats(){const s=new Set(DATA.map(d=>d.cat));return ['(all)',...[...s].sort()];}
function render(){
  const cat=document.getElementById('cat').value||'(all)';
  const g=document.getElementById('grid');g.innerHTML='';
  let shown=0;
  for(const d of DATA){
    if(cat!=='(all)'&&d.cat!==cat)continue;
    if(onlyFlag&&!flagged.has(d.pid))continue;
    shown++;
    const c=document.createElement('div');c.className='cell'+(flagged.has(d.pid)?' flag':'');
    c.innerHTML='<img src="data:image/webp;base64,'+d.b64+'"><span class="lbl">'+d.pid+'</span>';
    c.onclick=()=>{if(flagged.has(d.pid))flagged.delete(d.pid);else flagged.add(d.pid);
      c.classList.toggle('flag');upd();};
    g.appendChild(c);
  }
  upd(shown);
}
function upd(shown){document.getElementById('count').textContent=
   flagged.size+' flagged'+(shown!=null?(' / '+shown+' shown'):'');}
function exportPids(){
  const arr=[...flagged].sort();
  const t=document.getElementById('out');t.style.display='block';
  t.value=JSON.stringify(arr);
  const blob=new Blob([t.value],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download='greenfix_pids.json';a.click();
  try{navigator.clipboard.writeText(t.value);}catch(e){}
}
(function init(){
  const sel=document.getElementById('cat');
  for(const c of cats()){const o=document.createElement('option');o.value=o.textContent=c;sel.appendChild(o);}
  render();
})();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Build a green-fix flagging picker.")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--orig-pool", help="pre-greening pool, to pre-flag contaminated sprites")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preflag-threshold", type=int, default=120,
                    help="added-green px above which a sprite is pre-flagged (default 120)")
    args = ap.parse_args()

    with open(args.pool, "rb") as f:
        pool = pickle.load(f)
    orig = None
    if args.orig_pool:
        with open(args.orig_pool, "rb") as f:
            orig = pickle.load(f)

    data = []
    for pid, e in pool.items():
        b = e.get("img_b64")
        if not b:
            continue
        score = 0
        if orig and pid in orig and orig[pid].get("img_b64"):
            score = added_green(b, orig[pid]["img_b64"])
        data.append({"pid": pid, "cat": e.get("cat") or "", "b64": b,
                     "score": score, "pre": score >= args.preflag_threshold})
    data.sort(key=lambda d: -d["score"])      # worst-first

    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    with open(args.out, "w") as f:
        f.write(html)
    pre = sum(1 for d in data if d["pre"])
    print(f"wrote {args.out}  ({len(data)} sprites, {pre} pre-flagged)")


if __name__ == "__main__":
    main()
