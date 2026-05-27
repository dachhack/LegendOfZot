"""
Batch chroma-key (green-screen removal) for sprite sheets.

Gemini hands back a sprite sheet on a flat bright-green background; this turns
that green into transparency for every file you point it at, so you don't have
to round-trip each sheet through Adobe by hand. De-green the whole sheet here,
then slice it into individual sprites as usual.

Why not just "make #00FF00 transparent": an exact-match key leaves a green halo,
because the key colour is never perfectly uniform and anti-aliased sprite edges
blend sprite-colour *into* the background green. This keyer does three things to
avoid that:
  1. Tolerance band  -- keys a *range* of greens by RGB distance to the key
     colour, not an exact value.
  2. Soft alpha      -- edge pixels get partial transparency (a ramp between
     --inner and --outer) instead of a jagged 1-bit cutout.
  3. Despill         -- on edge pixels it pulls the green channel back down to
     max(R, B), killing the green fringe. Fully-kept pixels (e.g. a goblin's
     green skin, which sits far from the bright key) are left untouched, so
     genuinely-green sprites survive.

Keying is by distance to the *specific* key colour (auto-sampled from the sheet
border, or pass --key), which is far more selective than a generic "greenness"
metric -- that's what lets a green monster coexist with a green background.

Usage (from repo root):
    # de-green one sheet -> writes alongside it in a keyed/ subfolder
    python3 sprite_package/code/chroma_key.py path/to/sheet.png

    # a whole folder of sheets, into one output dir
    python3 sprite_package/code/chroma_key.py path/to/sheets/ -o path/to/out/

    # recurse, overwrite in place, force a known key colour
    python3 sprite_package/code/chroma_key.py sheets/ --recursive --in-place --key 00FF00

Tuning (eyeball the output, then adjust):
    --inner N   distance at/below which a pixel is FULLY transparent (default 60)
    --outer N   distance at/above which a pixel is FULLY kept       (default 130)
    Raise --inner if green halo remains; lower --outer if sprite edges are eaten.
    Distances are RGB Euclidean, range 0..441.
"""

import argparse
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("ERROR: Pillow and numpy are required.  pip install Pillow numpy",
          file=sys.stderr)
    sys.exit(1)


def parse_hex(s):
    s = s.lstrip("#")
    if len(s) != 6:
        raise argparse.ArgumentTypeError(f"key must be 6 hex digits, got {s!r}")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def detect_key_color(rgb):
    """Median colour of the 2px border ring -- the background, not the sprite."""
    ring = np.concatenate([
        rgb[:2, :, :].reshape(-1, 3),
        rgb[-2:, :, :].reshape(-1, 3),
        rgb[:, :2, :].reshape(-1, 3),
        rgb[:, -2:, :].reshape(-1, 3),
    ])
    return tuple(int(c) for c in np.median(ring, axis=0))


def _dilate(mask, iterations):
    """Binary dilation by `iterations` px (4-connectivity), numpy-only."""
    m = mask
    for _ in range(iterations):
        d = m.copy()
        d[1:, :] |= m[:-1, :]
        d[:-1, :] |= m[1:, :]
        d[:, 1:] |= m[:, :-1]
        d[:, :-1] |= m[:, 1:]
        m = d
    return m


def chroma_key(im, key, inner, outer, despill, despill_band=3):
    """Return a new RGBA image with the key colour removed."""
    arr = np.asarray(im.convert("RGBA"), dtype=np.float32)
    rgb = arr[..., :3]
    orig_a = arr[..., 3]

    dist = np.sqrt(np.sum((rgb - np.array(key, dtype=np.float32)) ** 2, axis=-1))
    # 0.0 = looks like background (transparent), 1.0 = clearly sprite (keep)
    keep = np.clip((dist - inner) / max(outer - inner, 1e-6), 0.0, 1.0)
    alpha = orig_a * keep

    if despill and despill_band > 0:
        # Despill the EDGE BAND: kept pixels within despill_band px of a
        # transparent one. That ring is where the key colour bled into
        # anti-aliased edges (the green halo) -- especially after a generative
        # model resamples the sheet. Interiors are untouched, so a genuinely
        # green sprite (goblin skin, slime) keeps its colour.
        transparent = alpha < 32
        band = _dilate(transparent, despill_band) & (~transparent)
        cap = np.maximum(rgb[..., 0], rgb[..., 2])          # max(R, B)
        spill = np.maximum(rgb[..., 1] - cap, 0.0)          # excess green
        rgb[..., 1] = np.where(band, rgb[..., 1] - spill, rgb[..., 1])

    arr[..., :3] = rgb
    arr[..., 3] = alpha
    return Image.fromarray(arr.round().clip(0, 255).astype(np.uint8), "RGBA")


def gather_inputs(paths, recursive):
    files = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.png") if recursive
                                else path.glob("*.png")))
        elif path.is_file():
            files.append(path)
        else:
            print(f"  WARN: not found, skipping: {p}", file=sys.stderr)
    return files


def main():
    ap = argparse.ArgumentParser(
        description="Batch-remove a green (or any flat) background from sprite sheets.")
    ap.add_argument("inputs", nargs="+", help="PNG files and/or directories")
    ap.add_argument("-o", "--out-dir", default=None,
                    help="Output directory (default: a keyed/ subfolder next to each input)")
    ap.add_argument("--in-place", action="store_true",
                    help="Overwrite the source files (ignores --out-dir)")
    ap.add_argument("--recursive", action="store_true",
                    help="Recurse into input directories")
    ap.add_argument("--key", type=parse_hex, default=None,
                    help="Key colour as hex (e.g. 00FF00). Default: auto-detect per file.")
    ap.add_argument("--inner", type=float, default=60.0,
                    help="Distance at/below which a pixel is fully transparent (default 60)")
    ap.add_argument("--outer", type=float, default=130.0,
                    help="Distance at/above which a pixel is fully kept (default 130)")
    ap.add_argument("--no-despill", action="store_true",
                    help="Skip green-fringe removal on edges")
    ap.add_argument("--despill-band", type=int, default=3,
                    help="Width in px of the edge ring to despill (default 3); "
                         "raise it if a thick green halo survives a downscale")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would be done; write nothing")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.outer <= args.inner:
        ap.error("--outer must be greater than --inner")

    files = gather_inputs(args.inputs, args.recursive)
    if not files:
        print("No PNG inputs found.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir and not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    n_ok = 0
    for src in files:
        try:
            im = Image.open(src)
            rgb = np.asarray(im.convert("RGB"))
            key = args.key or detect_key_color(rgb)

            if args.in_place:
                dst = src
            elif out_dir:
                dst = out_dir / src.name
            else:
                dst = src.parent / "keyed" / src.name

            if args.verbose or args.dry_run:
                kr, kg, kb = key
                print(f"  {src}  key=#{kr:02X}{kg:02X}{kb:02X}  ->  {dst}")

            if args.dry_run:
                continue

            dst.parent.mkdir(parents=True, exist_ok=True)
            chroma_key(im, key, args.inner, args.outer,
                       despill=not args.no_despill,
                       despill_band=args.despill_band).save(dst)
            n_ok += 1
        except Exception as e:
            print(f"  WARN {src}: {e}", file=sys.stderr)

    verb = "would process" if args.dry_run else "wrote"
    print(f"\n{verb} {len(files) if args.dry_run else n_ok} file(s).")


if __name__ == "__main__":
    main()
