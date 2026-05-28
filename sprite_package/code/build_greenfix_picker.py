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
  #legend{font-size:12px;opacity:.85}
  #legend b.f{color:#ff5c5c} #legend b.m{color:#f3c54a} #legend b.s{color:#7cc77c}
  #count{font-weight:bold;margin-left:auto;font-size:13px}
  #grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(84px,1fr));
        gap:4px;padding:6px}
  .cell{position:relative;border-radius:5px;overflow:hidden;cursor:pointer;
        outline:2px solid transparent}
  .cell img{width:100%;display:block;image-rendering:pixelated;aspect-ratio:1}
  .cell .lbl{position:absolute;left:0;bottom:0;right:0;font-size:9px;
        background:rgba(0,0,0,.55);padding:1px 2px;white-space:nowrap;overflow:hidden}
  .cell.fix{outline-color:#ff3b3b}
  .cell.fix::after{content:"\\2715";position:absolute;top:2px;right:3px;
        color:#ff3b3b;font-weight:bold;text-shadow:0 0 3px #000}
  .cell.manual{outline-color:#f3c54a;outline-width:3px}
  .cell.manual::after{content:"M";position:absolute;top:2px;right:3px;
        color:#f3c54a;font-weight:bold;text-shadow:0 0 3px #000;font-size:13px}
  body.bg-check .cell{background:
     conic-gradient(#cfcfcf 90deg,#888 0 180deg,#cfcfcf 0 270deg,#888 0) 0 0/16px 16px}
  body.bg-dark .cell{background:#181818}
  body.bg-white .cell{background:#fff}
  body.bg-mag .cell{background:#f0f}
</style></head>
<body class="bg-check">
<div id="bar">
  <span id="legend">Tap to cycle: <b class="f">FIX</b> &rarr; <b class="s">skip</b> &rarr; <b class="m">MANUAL</b></span>
  <button onclick="setbg('check')">Checker</button>
  <button onclick="setbg('dark')">Dark</button>
  <button onclick="setbg('white')">White</button>
  <button onclick="setbg('mag')">Magenta</button>
  <select id="cat" onchange="render()"></select>
  <select id="filt" onchange="render()">
    <option value="all">show: all</option>
    <option value="nonskip">show: fix + manual only</option>
    <option value="fix">show: fix only</option>
    <option value="manual">show: manual only</option>
    <option value="skip">show: skip only</option>
  </select>
  <span id="count"></span>
  <button onclick="exportPids()" style="background:#3a5;border-color:#4c7">Export</button>
</div>
<div id="grid"></div>
<textarea id="out" style="width:100%;height:80px;display:none;background:#111;color:#6f6"></textarea>
<script>
const DATA=__DATA__;
// state per pid: 'fix' | 'skip' | 'manual'.  Pre-flagged default to FIX,
// others to SKIP (so the user only marks exceptions either way).
const state={};
for(const d of DATA) state[d.pid]=d.pre?'fix':'skip';
const NEXT={fix:'skip',skip:'manual',manual:'fix'};
function setbg(b){document.body.className='bg-'+b;}
function cats(){const s=new Set(DATA.map(d=>d.cat));return ['(all)',...[...s].sort()];}
function classFor(s){return s==='skip'?'':s;}
function render(){
  const cat=document.getElementById('cat').value||'(all)';
  const filt=document.getElementById('filt').value;
  const g=document.getElementById('grid');g.innerHTML='';
  for(const d of DATA){
    if(cat!=='(all)'&&d.cat!==cat)continue;
    const s=state[d.pid];
    if(filt==='nonskip'&&s==='skip')continue;
    if(filt==='fix'&&s!=='fix')continue;
    if(filt==='manual'&&s!=='manual')continue;
    if(filt==='skip'&&s!=='skip')continue;
    const c=document.createElement('div');
    c.className=('cell '+classFor(s)).trim();
    c.innerHTML='<img src="data:image/webp;base64,'+d.b64+'"><span class="lbl">'+d.pid+'</span>';
    c.onclick=()=>{state[d.pid]=NEXT[state[d.pid]];
      c.className=('cell '+classFor(state[d.pid])).trim();upd();};
    g.appendChild(c);
  }
  upd();
}
function counts(){const c={fix:0,skip:0,manual:0};for(const p in state)c[state[p]]++;return c;}
function upd(){const c=counts();
  document.getElementById('count').innerHTML=
    '<span style="color:#ff5c5c">'+c.fix+' fix</span> &middot; '+
    '<span style="color:#f3c54a">'+c.manual+' manual</span> &middot; '+
    '<span style="color:#7cc77c">'+c.skip+' skip</span>';}
function exportPids(){
  const fix=[],manual=[];
  for(const d of DATA){if(state[d.pid]==='fix')fix.push(d.pid);else if(state[d.pid]==='manual')manual.push(d.pid);}
  const payload={fix:fix.sort(),manual:manual.sort()};
  const t=document.getElementById('out');t.style.display='block';
  t.value=JSON.stringify(payload,null,2);
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
