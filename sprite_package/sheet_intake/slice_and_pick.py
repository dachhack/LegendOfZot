"""
Sheet intake -- step 1 of 2: slice a sprite sheet into cells and build a
mobile multi-select picker to choose which cells go into the reserve.

Pipeline:
    1. python3 sprite_package/sheet_intake/slice_and_pick.py \
           --sheet path/to/new_monsters.png --cell-size 96 \
           --label S7A --category monsters
       -> slices the sheet into cells (auto-skips blank/transparent ones),
          stages them under sheet_intake/staging/<label>/, and writes
          sheet_intake/sheet_picker.html

    2. Open sheet_picker.html (works on mobile). Every non-blank cell starts
       SELECTED; tap to drop the junk (dupes, backgrounds, half-cut frames).
       Hit "Save selection" to download sheet_selection.json.

    3. python3 sprite_package/sheet_intake/add_to_reserve.py --label S7A
       -> assigns fresh PIDs, copies the kept cells into
          assets/sprites/reserve/<category>/, and updates that category's
          manifest.json + libraries/<category>_library.json.

Grid geometry: give EITHER --cell-size N (square cells) or --rows R --cols C
(cell size derived). --margin and --spacing handle sheets with a border or
gutters between cells.

ASCII only.
"""
import argparse
import base64
import io
import json
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow required. pip install Pillow", file=sys.stderr)
    sys.exit(2)


def cell_is_blank(cell, threshold, min_variance):
    """A cell is blank if almost none of it is opaque, or (for flat opaque
    sheets with no alpha) if its content is near-uniform background."""
    alpha = cell.getchannel('A')
    lo, hi = alpha.getextrema()
    if hi == 0:
        return True  # fully transparent
    # fraction of pixels with meaningful opacity (alpha > 16), via histogram
    hist = alpha.histogram()
    opaque = sum(hist[17:])
    if (opaque / (cell.width * cell.height)) < threshold:
        return True
    # Opaque-sheet fallback: a background-only cell has very low luminance
    # spread. Only applied when --min-variance > 0 (it's sheet-specific).
    if min_variance > 0:
        from PIL import ImageStat
        if ImageStat.Stat(cell.convert('L')).stddev[0] < min_variance:
            return True
    return False


def webp_b64(img):
    buf = io.BytesIO()
    img.save(buf, format='WEBP', quality=80, method=4)
    return base64.b64encode(buf.getvalue()).decode('ascii')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sheet', required=True, help='Path to the sprite sheet PNG.')
    ap.add_argument('--label', required=True,
                    help='Short sheet id, used in filenames + manifest (e.g. S7A).')
    ap.add_argument('--category', default='monsters',
                    help='Target reserve category (default: monsters).')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--cell-size', type=int, help='Square cell size in px.')
    g.add_argument('--grid', help='ROWSxCOLS, e.g. 8x12 (cell size derived).')
    ap.add_argument('--margin', type=int, default=0, help='Border around the whole sheet (px).')
    ap.add_argument('--offset-x', type=int, default=0,
                    help='Extra px to skip from the LEFT before the grid starts '
                         '(e.g. a row-label gutter). Not mirrored on the right.')
    ap.add_argument('--offset-y', type=int, default=0,
                    help='Extra px to skip from the TOP before the grid starts '
                         '(e.g. a column-label header). Not mirrored on the bottom.')
    ap.add_argument('--spacing', type=int, default=0, help='Gutter between cells (px).')
    ap.add_argument('--out-size', type=int, default=96,
                    help='Output cell size, NEAREST-resampled (default 96; 0 = keep native).')
    ap.add_argument('--blank-threshold', type=float, default=0.01,
                    help='Skip cells with less than this opaque fraction (default 0.01).')
    ap.add_argument('--min-variance', type=float, default=0.0,
                    help='For flat opaque sheets (no transparency): also skip cells whose '
                         'luminance std-dev is below this, i.e. background-only. Sheet-specific; '
                         '0 = off (default). ~13 worked for a dark-stone demon sheet.')
    ap.add_argument('--staging-dir', default=os.path.join(_HERE, 'staging'))
    args = ap.parse_args()

    sheet = Image.open(args.sheet).convert('RGBA')
    W, H = sheet.size
    m, sp = args.margin, args.spacing
    start_x = m + args.offset_x   # left edge of the first cell
    start_y = m + args.offset_y   # top edge of the first cell

    if args.cell_size:
        cw = ch = args.cell_size
        cols = (W - m - start_x + sp) // (cw + sp)
        rows = (H - m - start_y + sp) // (ch + sp)
    else:
        rows, cols = (int(x) for x in args.grid.lower().split('x'))
        cw = (W - m - start_x - (cols - 1) * sp) // cols
        ch = (H - m - start_y - (rows - 1) * sp) // rows

    if rows < 1 or cols < 1:
        print(f"ERROR: computed a {rows}x{cols} grid from {W}x{H}. "
              f"Check --cell-size/--grid/--margin/--offset-x/--offset-y/--spacing.",
              file=sys.stderr)
        sys.exit(1)

    out_dir = os.path.join(args.staging_dir, args.label)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    out_size = args.out_size or None
    cells = []          # metadata for staging manifest
    picker_cells = []   # {src_label, img} for the HTML
    blank = 0
    for r in range(rows):
        for c in range(cols):
            x = start_x + c * (cw + sp)
            y = start_y + r * (ch + sp)
            cell = sheet.crop((x, y, x + cw, y + ch))
            if cell_is_blank(cell, args.blank_threshold, args.min_variance):
                blank += 1
                continue
            if out_size:
                cell = cell.resize((out_size, out_size), Image.NEAREST)
            src_label = f"r{r:02d}c{c:02d}"
            fname = f"{src_label}.png"
            cell.save(os.path.join(out_dir, fname))
            cells.append({'src_label': src_label, 'source_row': r,
                          'source_col': c, 'filename': fname})
            picker_cells.append({'src_label': src_label, 'img': webp_b64(cell)})

    intake = {
        'label': args.label,
        'category': args.category,
        'sheet_source': os.path.abspath(args.sheet),
        'grid': {'rows': rows, 'cols': cols, 'cell_w': cw, 'cell_h': ch,
                 'margin': m, 'spacing': sp, 'out_size': out_size},
        'cells': cells,
    }
    with open(os.path.join(out_dir, '_intake.json'), 'w') as f:
        json.dump(intake, f, indent=2)

    # --- build the picker -------------------------------------------------
    data = json.dumps({'label': args.label, 'category': args.category,
                       'cells': picker_cells})
    html = _TEMPLATE.replace('__DATA__', data)
    picker_path = os.path.join(_HERE, 'sheet_picker.html')
    with open(picker_path, 'w') as f:
        f.write(html)

    print(f"Sheet {W}x{H} -> {rows}x{cols} grid (cell {cw}x{ch}).")
    print(f"  kept {len(cells)} non-blank cells, skipped {blank} blank.")
    print(f"  staged: {out_dir}/")
    print(f"  picker: {picker_path}  ({os.path.getsize(picker_path)/1024:.0f} KB)")
    print("\nOpen the picker, deselect junk, Save selection -> sheet_selection.json,")
    print(f"then: python3 {os.path.relpath(__file__, _ROOT)} ... "
          f"\n      python3 sprite_package/sheet_intake/add_to_reserve.py --label {args.label}")


_TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Sheet Intake Picker</title>
<style>
  * { box-sizing: border-box; }
  html,body { margin:0; background:#1a1a1a; color:#eee;
              font-family:system-ui,-apple-system,sans-serif; -webkit-text-size-adjust:100%; }
  body { padding-top:84px; padding-bottom:80px; }
  header { position:fixed; top:0; left:0; right:0; z-index:30;
           background:#141414; border-bottom:1px solid #333; padding:10px 12px; }
  header h1 { margin:0; font-size:15px; color:#FFD700; }
  header .sub { font-size:12px; color:#aaa; margin-top:3px; }
  header .actions { margin-top:8px; display:flex; gap:8px; }
  header .actions button { flex:0 0 auto; padding:5px 11px; background:#333; color:#ccc;
           border:1px solid #444; border-radius:14px; font-size:12px; }
  main { padding:8px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(76px,1fr)); gap:6px; }
  .tile { background:#181818; border:2px solid #2a2a2a; border-radius:6px; padding:4px;
          position:relative; -webkit-tap-highlight-color:transparent; -webkit-user-select:none;
          user-select:none; cursor:pointer; }
  .tile.keep { border-color:#50c878; box-shadow:0 0 8px rgba(80,200,120,0.35); }
  .tile canvas { width:100%; aspect-ratio:1; background:#0a0a0a; image-rendering:pixelated;
                 display:block; border-radius:3px; }
  .tile .lbl { font-family:monospace; font-size:9px; color:#888; text-align:center; margin-top:2px; }
  .tile .chk { position:absolute; top:3px; right:3px; width:16px; height:16px; border-radius:50%;
               background:#333; border:1px solid #555; }
  .tile.keep .chk { background:#50c878; border-color:#50c878; }
  footer { position:fixed; bottom:0; left:0; right:0; z-index:30; background:#141414;
           border-top:1px solid #333; padding:10px 12px;
           padding-bottom:calc(10px + env(safe-area-inset-bottom,0px)); display:flex; gap:8px; }
  footer button { flex:1; padding:13px; border-radius:6px; font-size:14px; font-weight:bold;
                  border:1px solid #4a8a5a; background:#2a5a3a; color:#fff; }
  #modal { display:none; position:fixed; inset:0; z-index:40; background:rgba(0,0,0,0.85);
           align-items:center; justify-content:center; padding:20px; }
  #modal.on { display:flex; }
  #modal .box { background:#222; border:1px solid #333; border-radius:10px; padding:16px;
                width:100%; max-width:600px; }
  #modal textarea { width:100%; height:160px; background:#0a0a0a; color:#9f9;
                    font-family:monospace; font-size:11px; padding:8px; border:1px solid #333;
                    border-radius:4px; }
  #modal .row { display:flex; gap:8px; margin-top:10px; }
  #modal .row button { flex:1; padding:10px; border-radius:4px; border:1px solid #555;
                       background:#333; color:#eee; }
</style></head><body>
<header>
  <h1 id="title">Sheet Intake</h1>
  <div class="sub" id="sub"></div>
  <div class="actions">
    <button id="all">Select all</button>
    <button id="none">Select none</button>
    <button id="invert">Invert</button>
  </div>
</header>
<main><div class="grid" id="grid"></div></main>
<footer><button id="save">Save selection</button></footer>
<div id="modal"><div class="box">
  <h3 style="margin:0 0 8px 0;color:#FFD700;">sheet_selection.json</h3>
  <textarea id="out" readonly></textarea>
  <div class="row">
    <button id="copy">Copy</button>
    <button id="dl" style="background:#2a5a3a;border-color:#4a8a5a;">Download</button>
    <button id="close">Close</button>
  </div>
</div></div>
<script>
const DATA = __DATA__;
const keep = {};
DATA.cells.forEach(c => keep[c.src_label] = true);  // default: keep all non-blank

const lazy = ('IntersectionObserver' in window) ? new IntersectionObserver(es => {
  es.forEach(e => { if (e.isIntersecting) { const cv=e.target;
    if (!cv._done){ const img=new Image(); img.onload=()=>{ const x=cv.getContext('2d');
      x.imageSmoothingEnabled=false; x.clearRect(0,0,cv.width,cv.height);
      x.drawImage(img,0,0,cv.width,cv.height); }; img.src='data:image/webp;base64,'+cv._b64; cv._done=1; }
    lazy.unobserve(cv); } });
}, { rootMargin:'300px' }) : null;

function render() {
  const g = document.getElementById('grid'); g.innerHTML='';
  if (lazy) lazy.disconnect();
  DATA.cells.forEach(c => {
    const t=document.createElement('div'); t.className='tile'+(keep[c.src_label]?' keep':'');
    t.dataset.k=c.src_label;
    const cv=document.createElement('canvas'); cv.width=76; cv.height=76; cv._b64=c.img;
    t.appendChild(cv);
    const chk=document.createElement('div'); chk.className='chk'; t.appendChild(chk);
    const lb=document.createElement('div'); lb.className='lbl'; lb.textContent=c.src_label; t.appendChild(lb);
    t.onclick=()=>{ keep[c.src_label]=!keep[c.src_label]; t.classList.toggle('keep',keep[c.src_label]); updateSub(); };
    g.appendChild(t);
    if (lazy) lazy.observe(cv); else { const x=cv.getContext('2d'); const im=new Image();
      im.onload=()=>{x.imageSmoothingEnabled=false;x.drawImage(im,0,0,76,76);}; im.src='data:image/webp;base64,'+c.img; }
  });
  updateSub();
}
function updateSub() {
  const n=Object.values(keep).filter(Boolean).length;
  document.getElementById('sub').textContent =
    DATA.label+' -> '+DATA.category+' | '+n+' of '+DATA.cells.length+' cells kept';
}
document.getElementById('title').textContent='Sheet Intake: '+DATA.label;
document.getElementById('all').onclick=()=>{DATA.cells.forEach(c=>keep[c.src_label]=true);render();};
document.getElementById('none').onclick=()=>{DATA.cells.forEach(c=>keep[c.src_label]=false);render();};
document.getElementById('invert').onclick=()=>{DATA.cells.forEach(c=>keep[c.src_label]=!keep[c.src_label]);render();};
function payload(){ return { label:DATA.label, category:DATA.category,
  keep:DATA.cells.map(c=>c.src_label).filter(k=>keep[k]) }; }
document.getElementById('save').onclick=()=>{ document.getElementById('out').value=
  JSON.stringify(payload(),null,2); document.getElementById('modal').classList.add('on'); };
document.getElementById('close').onclick=()=>document.getElementById('modal').classList.remove('on');
document.getElementById('copy').onclick=()=>{const t=document.getElementById('out');t.select();
  try{navigator.clipboard.writeText(t.value);}catch(e){document.execCommand('copy');}};
document.getElementById('dl').onclick=()=>{const b=new Blob([document.getElementById('out').value],
  {type:'application/json'}); const u=URL.createObjectURL(b); const a=document.createElement('a');
  a.href=u; a.download='sheet_selection.json'; document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(u);};
render();
</script></body></html>
"""


if __name__ == '__main__':
    main()
