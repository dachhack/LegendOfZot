"""Build a self-contained HTML picker for the 14 dwarf-mining items
(10 ore ingredients + 4 Ioun Stones), sourcing candidates from the
RESERVE pool (the `sprite-assets-v1` GitHub Release).

Reserve sprites have solid dark backgrounds; they're shown as-is here
(the picker UI is dark too, so the art reads fine). Keying the chosen
sprites to TRANSPARENT happens later in apply_mining_sprites.py.

Pull the reserve first (treasures/ingredients/accessories cover gems,
minerals, orbs and jewelry):

    curl -L -o /tmp/wc_sprites_assets.zip \\
      https://github.com/dachhack/LegendOfZot/releases/download/sprite-assets-v1/wc_sprites_assets.zip
    unzip -q -o /tmp/wc_sprites_assets.zip \\
      'wc_sprites_assets/reserve/treasures/*' \\
      'wc_sprites_assets/reserve/ingredients/*' \\
      'wc_sprites_assets/reserve/accessories/*' \\
      'wc_sprites_assets/reserve/manifest.json' -d /tmp/wc_reserve/

    python3 sprite_package/picks_mining/build_mining_picker.py \\
        --reserve-dir /tmp/wc_reserve/wc_sprites_assets/reserve \\
        --out /tmp/mining_sprite_picker.html

Open the HTML in a browser: tap an item chip (top), then tap a sprite to
assign it; repeat for each item; "Save picks JSON" downloads
mining_sprite_picks.json. Feed that to apply_mining_sprites.py.
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

ITEMS = [
    "Ioun Stone of Fortitude", "Ioun Stone of Might",
    "Ioun Stone of Agility", "Ioun Stone of Mastery",
    "Iron Chunk", "Copper Nugget", "Stone Shard", "Silver Vein",
    "Gold Flake", "Coal Ember", "Mithril Shard", "Ruby Fragment",
    "Diamond Chip", "Adamantine Dust",
]
CATS = ['treasures', 'ingredients', 'accessories']


def _border_median_key(im):
    rgb = im.convert('RGB'); w, h = rgb.size; px = rgb.load(); ring = []
    for x in range(w): ring += [px[x, 0], px[x, h - 1]]
    for y in range(h): ring += [px[0, y], px[w - 1, y]]
    ring.sort()
    return ring[len(ring) // 2]


def thumb_b64(path, sz=56):
    """Key the reserve sprite's dark background to TRANSPARENT (same keyer
    apply_mining_sprites.py uses), then embed as an RGBA webp so the picker
    previews the real in-game look. Shown on a CSS checkerboard. 56px keeps
    the all-candidates file light; pixel art upscales fine in the grid."""
    im = Image.open(path).convert('RGBA')
    keyed = ck.chroma_key(im, _border_median_key(im), 60, 130, True)
    keyed = keyed.resize((sz, sz), Image.NEAREST)
    buf = io.BytesIO()
    keyed.save(buf, 'WEBP', quality=80)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reserve-dir', required=True,
                    help='Unzipped reserve dir (...wc_sprites_assets/reserve)')
    ap.add_argument('--out', default='/tmp/mining_sprite_picker.html')
    ap.add_argument('--size', type=int, default=56,
                    help='Preview thumb px (smaller = lighter file)')
    a = ap.parse_args()

    cands = []
    for cat in CATS:
        for f in sorted(glob.glob(os.path.join(a.reserve_dir, cat, '*.png'))):
            rid = os.path.basename(f)[:-4]
            cands.append({"id": rid, "cat": cat, "b64": thumb_b64(f, a.size)})
    print("candidates:", len(cands))

    data = json.dumps({"items": ITEMS, "cands": cands})
    html = _TEMPLATE.replace("/*DATA*/", data)
    with open(a.out, 'w') as fh:
        fh.write(html)
    print("wrote", a.out, f"{os.path.getsize(a.out)//1024} KB")


_TEMPLATE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Mining Sprite Picker</title><style>
body{margin:0;background:#15151c;color:#e8e8f0;font-family:system-ui,sans-serif}
/* checkerboard reveals the transparent (keyed) background */
.chk{background-image:linear-gradient(45deg,#3a3a44 25%,transparent 25%,transparent 75%,#3a3a44 75%),linear-gradient(45deg,#3a3a44 25%,#22222a 25%,#22222a 75%,#3a3a44 75%);background-size:14px 14px;background-position:0 0,7px 7px}
#slots{position:sticky;top:0;background:#1d1d28;padding:6px;display:flex;flex-wrap:wrap;gap:4px;box-shadow:0 2px 8px #000a;z-index:10}
.slot{border:2px solid #444;border-radius:6px;padding:3px 5px;font-size:11px;cursor:pointer;display:flex;align-items:center;gap:4px;background:#262633}
.slot.active{border-color:#ffd23f;background:#33301c}
.slot img{width:30px;height:30px;image-rendering:pixelated;border-radius:3px}
.slot .nm{max-width:110px;line-height:1.05}
#bar{padding:6px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button{background:#2e7d32;color:#fff;border:0;border-radius:6px;padding:8px 14px;font-size:14px;cursor:pointer}
#tabs button{background:#333;margin-right:4px} #tabs button.on{background:#3949ab}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:4px;padding:6px}
.cand{border:2px solid #333;border-radius:6px;cursor:pointer;text-align:center;overflow:hidden}
.cand img{width:76px;height:76px;image-rendering:pixelated;display:block;margin:auto}
.cand .id{font-size:8px;color:#aab;background:#16161c}
.cand.sel{border-color:#ffd23f}
.hint{font-size:12px;color:#9a9aa8;padding:0 6px}
</style></head><body>
<div id=slots></div>
<div id=bar>
  <div id=tabs></div>
  <button onclick=save()>Save picks JSON</button>
  <span class=hint>Tap an item chip (top), then tap a sprite to assign it. Repeat for each item.</span>
</div>
<div id=grid></div>
<script>
const D=/*DATA*/;
let picks={}, active=D.items[0], tab='treasures';
const slots=document.getElementById('slots'), grid=document.getElementById('grid'), tabs=document.getElementById('tabs');
function byId(id){return D.cands.find(c=>c.id===id);}
function drawSlots(){
  slots.innerHTML='';
  D.items.forEach(it=>{
    const c=picks[it];
    const el=document.createElement('div'); el.className='slot'+(it===active?' active':'');
    el.innerHTML=(c?`<img class=chk src="data:image/webp;base64,${byId(c).b64}">`:'<img class=chk>')+`<span class=nm>${it}</span>`;
    el.onclick=()=>{active=it;drawSlots();};
    slots.appendChild(el);
  });
}
function drawTabs(){
  tabs.innerHTML='';
  ['treasures','ingredients','accessories'].forEach(t=>{
    const b=document.createElement('button'); b.textContent=t+' ('+D.cands.filter(c=>c.cat===t).length+')';
    b.className=(t===tab?'on':''); b.onclick=()=>{tab=t;drawGrid();drawTabs();}; tabs.appendChild(b);
  });
}
function drawGrid(){
  grid.innerHTML='';
  D.cands.filter(c=>c.cat===tab).forEach(c=>{
    const el=document.createElement('div'); el.className='cand'+(picks[active]===c.id?' sel':'');
    el.innerHTML=`<img class=chk src="data:image/webp;base64,${c.b64}"><div class=id>${c.id.split('_')[0]}</div>`;
    el.onclick=()=>{picks[active]=c.id;drawSlots();drawGrid();};
    grid.appendChild(el);
  });
}
function save(){
  const blob=new Blob([JSON.stringify(picks,null,2)],{type:'application/json'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='mining_sprite_picks.json'; a.click();
}
drawSlots();drawTabs();drawGrid();
</script></body></html>"""


if __name__ == '__main__':
    main()
