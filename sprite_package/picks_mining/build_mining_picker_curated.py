"""Build a CURATED mining sprite picker -- a handful of hand-picked reserve
candidates per item (vs build_mining_picker.py's all-candidates firehose).

Each item shows its few options keyed to transparent on a checkerboard;
tap one to select (the first is pre-selected as the recommended default).
"Save picks JSON" downloads mining_sprite_picks.json for
apply_mining_sprites.py.

    python3 sprite_package/picks_mining/build_mining_picker_curated.py \\
        --reserve-dir /tmp/wc_reserve/wc_sprites_assets/reserve \\
        --out /tmp/mining_sprite_picker_curated.html
"""
import argparse
import base64
import glob
import io
import json
import os
import sys
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))
import chroma_key as ck

# Per-item curated candidates (first = recommended default). All confirmed
# to exist in the reserve treasures/ingredients categories.
CANDS = {
    "Ioun Stone of Fortitude": ["CR0156", "CR0144", "CR0149", "CR0165"],
    "Ioun Stone of Might":     ["CR0157", "CR0145", "CR0162"],
    "Ioun Stone of Agility":   ["CR0158", "CR0146", "CR0167"],
    "Ioun Stone of Mastery":   ["CR0149", "CR0161", "CR0166", "CR0013"],
    "Iron Chunk":              ["CR0153", "CR0154", "CR0152"],
    "Copper Nugget":           ["CR0151", "CR0163"],
    "Stone Shard":             ["CR0150", "CR0167", "CR0162"],
    "Silver Vein":             ["CR0162", "CR0150"],
    "Gold Flake":              ["CR0147", "CR0159", "CR0160"],
    "Coal Ember":              ["CR0155", "CR0152", "CR0164"],
    "Mithril Shard":           ["CR0145", "CR0157", "CR0162"],
    "Ruby Fragment":           ["CR0144", "CR0156"],
    "Diamond Chip":            ["CR0161", "CR0149", "CR0150"],
    # Adamantine Dust: full dust/powder set (CR0004 matte grey powder +
    # CR0028 dark metallic are the most "powder"; rest are glitter piles).
    "Adamantine Dust":         ["CR0004", "CR0028", "CR0013", "CR0001", "CR0014", "CR0003"],
}


def _border_median_key(im):
    rgb = im.convert('RGB'); w, h = rgb.size; px = rgb.load(); ring = []
    for x in range(w): ring += [px[x, 0], px[x, h - 1]]
    for y in range(h): ring += [px[0, y], px[w - 1, y]]
    ring.sort()
    return ring[len(ring) // 2]


def keyed_b64(path, sz=80):
    im = Image.open(path).convert('RGBA')
    k = ck.chroma_key(im, _border_median_key(im), 60, 130, True).resize((sz, sz), Image.NEAREST)
    buf = io.BytesIO(); k.save(buf, 'WEBP', quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reserve-dir', required=True)
    ap.add_argument('--out', default='/tmp/mining_sprite_picker_curated.html')
    a = ap.parse_args()

    index = {os.path.basename(f).split('_')[0]: f
             for f in glob.glob(os.path.join(a.reserve_dir, '*', '*.png'))}
    b64 = {}
    for ids in CANDS.values():
        for rid in ids:
            if rid not in b64:
                b64[rid] = keyed_b64(index[rid])

    data = json.dumps({"cands": CANDS, "b64": b64,
                       "order": list(CANDS.keys())})
    html = _TEMPLATE.replace("/*DATA*/", data)
    with open(a.out, 'w') as fh:
        fh.write(html)
    print("wrote", a.out, f"{os.path.getsize(a.out)//1024} KB",
          f"({len(b64)} unique sprites)")


_TEMPLATE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Mining Sprite Picker (curated)</title><style>
body{margin:0;background:#15151c;color:#e8e8f0;font-family:system-ui,sans-serif}
#bar{position:sticky;top:0;background:#1d1d28;padding:8px;box-shadow:0 2px 8px #000a;z-index:10;display:flex;gap:10px;align-items:center}
button{background:#2e7d32;color:#fff;border:0;border-radius:6px;padding:9px 16px;font-size:15px;cursor:pointer}
.hint{font-size:12px;color:#9a9aa8}
.item{padding:8px 10px;border-bottom:1px solid #2a2a36}
.item h3{margin:0 0 6px;font-size:14px;color:#ffd23f}
.row{display:flex;flex-wrap:wrap;gap:8px}
.chk{background-image:linear-gradient(45deg,#3a3a44 25%,transparent 25%,transparent 75%,#3a3a44 75%),linear-gradient(45deg,#3a3a44 25%,#22222a 25%,#22222a 75%,#3a3a44 75%);background-size:16px 16px;background-position:0 0,8px 8px}
.cand{border:3px solid #333;border-radius:8px;cursor:pointer;text-align:center;overflow:hidden}
.cand img{width:80px;height:80px;image-rendering:pixelated;display:block}
.cand .id{font-size:9px;color:#aab;background:#16161c;padding:1px}
.cand.sel{border-color:#ffd23f;box-shadow:0 0 8px #ffd23f88}
</style></head><body>
<div id=bar>
  <button onclick=save()>Save picks JSON</button>
  <span class=hint>Each item is pre-set to the recommended pick (gold border). Tap a different sprite to change it.</span>
</div>
<div id=app></div>
<script>
const D=/*DATA*/;
let picks={};
D.order.forEach(it=>picks[it]=D.cands[it][0]);  // default = first
const app=document.getElementById('app');
function draw(){
  app.innerHTML='';
  D.order.forEach(it=>{
    const div=document.createElement('div'); div.className='item';
    let row='';
    D.cands[it].forEach(rid=>{
      row+=`<div class="cand${picks[it]===rid?' sel':''}" onclick="pick('${it}','${rid}')">`
         +`<img class=chk src="data:image/webp;base64,${D.b64[rid]}"><div class=id>${rid}</div></div>`;
    });
    div.innerHTML=`<h3>${it}</h3><div class=row>${row}</div>`;
    app.appendChild(div);
  });
}
function pick(it,rid){picks[it]=rid;draw();}
function save(){
  const blob=new Blob([JSON.stringify(picks,null,2)],{type:'application/json'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='mining_sprite_picks.json'; a.click();
}
draw();
</script></body></html>"""


if __name__ == '__main__':
    main()
