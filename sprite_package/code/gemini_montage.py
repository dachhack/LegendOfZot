"""
Montage tool for the Gemini "repaint the background flat green" round-trip.

Shipping 1,300+ sprites to Gemini one-at-a-time is wasteful (each image is a
flat ~258-token cost and you smack into per-request image limits). This packs
many sprites into a few labelled grid sheets, records where each one sits, and
then re-slices Gemini's returned sheets back into individual PNGs -- which you
then run through chroma_key.py and promote_all_sprites.py as usual.

    pack   pool/PNGs  ->  sheet_NNN.png (+ manifest.json)   [send sheets to Gemini]
    slice  Gemini's sheets + manifest  ->  <pid>.png per sprite

Why this is built the way it is:
  * Gemini is a *generative* model -- it returns a fixed-resolution canvas, so
    the sheet you get back is rarely the exact pixels/size you sent. `slice`
    therefore cuts cells by GRID FRACTION (sheet_w / cols), never by absolute
    pixels, so a resized/rescaled return still maps cell-for-cell.
  * Each sprite is centred in a cell with a margin of background around it, so
    minor misalignment in Gemini's output eats into throwaway margin, not the
    sprite. The margin is flat key-colour, which chroma_key.py removes anyway.
  * The pid->cell mapping lives in manifest.json (by row/col position), not in
    burned-in text, so Gemini repainting the sheet can't corrupt the mapping.
    Pass --labeled to ALSO get a *_ref.png with pids drawn on, for your eyes.
  * Keep grids modest. Bigger grids = fewer Gemini calls but more risk Gemini
    garbles or shifts individual cells. cell defaults to 128px so an 8x8 grid
    lands at 1024x1024 -- close to Gemini's native output canvas, which
    minimises resampling. Test grid size on ONE sheet before batching all.

Recommended Gemini prompt (per sheet):
    "This is a grid of game sprites. Replace ONLY the background behind each
     sprite with a single flat, uniform, bright green (#00FF00). Do not move,
     resize, recolour, redraw, add, or remove any sprite. Keep the grid layout
     and every sprite's pixels exactly as-is. Return the same grid, same size."

Usage:
    # pack the whole in-game pool into 8x8 sheets
    python3 sprite_package/code/gemini_montage.py pack \
        --from-pool wizardscavern/data/canonical_pool_full.pkl \
        --rows 8 --cols 8 --out-dir /tmp/montage --labeled

    # pack a folder of PNGs instead
    python3 sprite_package/code/gemini_montage.py pack sprites_dir/ --out-dir out/

    # after Gemini returns the greened sheets into returned/:
    python3 sprite_package/code/gemini_montage.py slice \
        --manifest /tmp/montage/manifest.json --in-dir returned/ --out-dir cut/
    # then: chroma_key.py cut/  ->  promote_all_sprites.py

    # ...or do slice + chroma-key in one pass (output is ready to promote):
    python3 sprite_package/code/gemini_montage.py slice \
        --manifest /tmp/montage/manifest.json --in-dir returned/ \
        --out-dir cut/ --dechroma
"""

import argparse
import base64
import io
import json
import pickle
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: Pillow is required.  pip install Pillow", file=sys.stderr)
    sys.exit(1)

PID_RE = re.compile(r"^([A-Z]+\d+)")


def parse_hex(s):
    s = s.lstrip("#")
    if len(s) != 6:
        raise argparse.ArgumentTypeError(f"colour must be 6 hex digits, got {s!r}")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def _load_chroma():
    """Import chroma_key.py (same dir) so `slice --dechroma` reuses its keying
    algorithm instead of duplicating it. Lazy -- only called with --dechroma,
    so plain pack/slice keep working without numpy installed."""
    import importlib.util
    path = Path(__file__).with_name("chroma_key.py")
    spec = importlib.util.spec_from_file_location("chroma_key", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# Sprite sources
# --------------------------------------------------------------------------

def sprites_from_pool(pool_path, cats, status):
    with open(pool_path, "rb") as f:
        pool = pickle.load(f)
    out = []
    for pid, e in pool.items():
        if status and e.get("status") != status:
            continue
        if cats and e.get("cat") not in cats:
            continue
        b64 = e.get("img_b64")
        if not b64:
            continue
        im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
        out.append((pid, e.get("cat") or "", im))
    out.sort(key=lambda t: (t[1], t[0]))   # stable: by cat then pid
    return out


def sprites_from_dir(paths, recursive):
    out = []
    for p in paths:
        path = Path(p)
        files = []
        if path.is_dir():
            files = sorted(path.rglob("*.png") if recursive else path.glob("*.png"))
        elif path.is_file():
            files = [path]
        for fp in files:
            m = PID_RE.match(fp.stem)
            pid = m.group(1) if m else fp.stem
            out.append((pid, fp.parent.name, Image.open(fp).convert("RGBA")))
    return out


# --------------------------------------------------------------------------
# pack
# --------------------------------------------------------------------------

def cmd_pack(args):
    if args.from_pool:
        sprites = sprites_from_pool(args.from_pool, set(args.cats or []), args.status)
    else:
        if not args.inputs:
            print("pack: give PNG files/dirs, or --from-pool", file=sys.stderr)
            sys.exit(1)
        sprites = sprites_from_dir(args.inputs, args.recursive)
    if not sprites:
        print("pack: no sprites found", file=sys.stderr)
        sys.exit(1)

    ss, margin = args.sprite_size, args.margin
    cell = ss + 2 * margin
    rows, cols = args.rows, args.cols
    per_sheet = rows * cols
    bg = parse_hex(args.bg)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"sprite_size": ss, "margin": margin, "cell": cell,
                "rows": rows, "cols": cols, "bg": args.bg.lstrip("#"),
                "sheets": []}

    n_sheets = (len(sprites) + per_sheet - 1) // per_sheet
    for s in range(n_sheets):
        chunk = sprites[s * per_sheet:(s + 1) * per_sheet]
        sheet = Image.new("RGB", (cols * cell, rows * cell), bg)
        ref = sheet.copy() if args.labeled else None
        draw = ImageDraw.Draw(ref) if ref else None
        cells = []
        for i, (pid, cat, im) in enumerate(chunk):
            row, col = divmod(i, cols)
            spr = im if im.size == (ss, ss) else im.resize((ss, ss), Image.NEAREST)
            x, y = col * cell + margin, row * cell + margin
            sheet.paste(spr, (x, y), spr)          # composite onto bg via alpha
            cells.append({"row": row, "col": col, "pid": pid, "cat": cat})
            if draw:
                ref.paste(spr, (x, y), spr)
                draw.text((col * cell + 2, row * cell + 2), pid, fill=(255, 0, 255))
        fname = f"sheet_{s + 1:03d}.png"
        sheet.save(out_dir / fname)
        if ref:
            ref.save(out_dir / f"sheet_{s + 1:03d}_ref.png")
        manifest["sheets"].append({"file": fname, "w": sheet.width,
                                   "h": sheet.height, "cells": cells})
        print(f"  {fname}  {len(cells)} sprites  {sheet.width}x{sheet.height}")

    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\npacked {len(sprites)} sprites into {n_sheets} sheet(s) -> {out_dir}")
    print(f"manifest: {out_dir / 'manifest.json'}")


# --------------------------------------------------------------------------
# slice
# --------------------------------------------------------------------------

def cmd_slice(args):
    with open(args.manifest) as f:
        manifest = json.load(f)
    rows, cols = manifest["rows"], manifest["cols"]
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ck = forced_key = None
    if args.dechroma:
        ck = _load_chroma()
        forced_key = args.key       # tuple, or None -> auto-detect per cell

    inset = args.trim               # fraction of a cell to crop off each side
    n = 0
    for sh in manifest["sheets"]:
        src = in_dir / sh["file"]
        if not src.exists():
            print(f"  skip {sh['file']}: not found in {in_dir}")
            continue
        img = Image.open(src).convert("RGB")
        W, H = img.size
        # Slice by grid fraction -> robust to Gemini returning a resized canvas.
        cw, ch = W / cols, H / rows
        for c in sh["cells"]:
            r, col, pid = c["row"], c["col"], c["pid"]
            left, top = col * cw, r * ch
            box = tuple(round(v) for v in (
                left + inset * cw, top + inset * ch,
                left + (1 - inset) * cw, top + (1 - inset) * ch))
            cell_img = img.crop(box)
            if ck:                  # one-pass: key the green margin away too
                key = forced_key or ck.detect_key_color(ck.np.asarray(cell_img))
                cell_img = ck.chroma_key(cell_img, key, args.inner, args.outer,
                                         despill=not args.no_despill)
            cell_img.save(out_dir / f"{pid}.png")
            n += 1
        print(f"  {sh['file']}  {W}x{H}  ->  {len(sh['cells'])} cells")
    print(f"\nsliced {n} sprite(s) -> {out_dir}")
    if args.dechroma:
        print("transparent PNGs written; next: promote_all_sprites.py")
    else:
        print("next: chroma_key.py on this folder, then promote_all_sprites.py")


def main():
    ap = argparse.ArgumentParser(description="Pack sprites into grid sheets for "
                                 "Gemini, and re-slice the returned sheets.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pk = sub.add_parser("pack", help="lay sprites out into grid sheets + manifest")
    pk.add_argument("inputs", nargs="*", help="PNG files/dirs (or use --from-pool)")
    pk.add_argument("--from-pool", help="canonical_pool_full.pkl to pull sprites from")
    pk.add_argument("--cats", nargs="+", help="only these pool categories")
    pk.add_argument("--status", default="in-game", help="pool status filter (default in-game)")
    pk.add_argument("--rows", type=int, default=8)
    pk.add_argument("--cols", type=int, default=8)
    pk.add_argument("--sprite-size", type=int, default=96)
    pk.add_argument("--margin", type=int, default=16, help="bg padding around each sprite")
    pk.add_argument("--bg", default="00FF00", help="cell background hex (default green)")
    pk.add_argument("--labeled", action="store_true", help="also emit *_ref.png with pids")
    pk.add_argument("--recursive", action="store_true")
    pk.add_argument("--out-dir", required=True)
    pk.set_defaults(func=cmd_pack)

    sl = sub.add_parser("slice", help="re-slice Gemini's returned sheets via manifest")
    sl.add_argument("--manifest", required=True)
    sl.add_argument("--in-dir", required=True, help="dir of Gemini-returned sheets")
    sl.add_argument("--out-dir", required=True)
    sl.add_argument("--trim", type=float, default=0.0,
                    help="fraction of each cell to crop off all sides (0..0.4); "
                         "leave 0 -- chroma_key removes the green margin anyway")
    sl.add_argument("--dechroma", action="store_true",
                    help="one-pass: also chroma-key each cell to transparency "
                         "(reuses chroma_key.py); output is ready to promote")
    sl.add_argument("--key", type=parse_hex, default=None,
                    help="[--dechroma] force key colour hex; default auto-detect per cell")
    sl.add_argument("--inner", type=float, default=60.0,
                    help="[--dechroma] distance at/below which a pixel is fully transparent")
    sl.add_argument("--outer", type=float, default=130.0,
                    help="[--dechroma] distance at/above which a pixel is fully kept")
    sl.add_argument("--no-despill", action="store_true",
                    help="[--dechroma] skip green-fringe removal on edges")
    sl.set_defaults(func=cmd_slice)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
