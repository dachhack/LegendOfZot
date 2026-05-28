"""
Post-hoc edge-band despill for an already-keyed canonical pool.

After the Gemini round-trip + chroma key, a faint green fringe can survive on
the anti-aliased silhouette of some sprites -- the kept edge pixels still carry
a little of the key colour. This scrubs that fringe directly on the transparent
sprites in a canonical_pool .pkl, with no re-keying or re-upload: for each RGBA
sprite it finds the ring of opaque pixels within --band px of transparency and
pulls their green channel down to max(R, B). Interiors are never touched, so a
genuinely green sprite (a goblin, a dragon) keeps its colour. Sprites with no
green excess on the edge are left byte-for-byte unchanged (not re-encoded).

Usage:
    python3 sprite_package/code/despill_pool.py \
        --pool wizardscavern/data/canonical_pool_full.pkl --band 2
    # preview only:
    python3 sprite_package/code/despill_pool.py --pool ... --dry-run
"""

import argparse
import base64
import io
import pickle
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("ERROR: Pillow and numpy are required.  pip install Pillow numpy",
          file=sys.stderr)
    sys.exit(1)


def _dilate(mask, iterations):
    m = mask
    for _ in range(iterations):
        d = m.copy()
        d[1:, :] |= m[:-1, :]
        d[:-1, :] |= m[1:, :]
        d[:, 1:] |= m[:, :-1]
        d[:, :-1] |= m[:, 1:]
        m = d
    return m


def despill_edge(im, band):
    """Despill the opaque edge ring; return a new image, or None if unchanged."""
    a = np.asarray(im.convert("RGBA"), dtype=np.float32)
    rgb = a[..., :3]
    transp = a[..., 3] < 64
    if not transp.any():           # no transparency -> no edge to clean
        return None
    edge = _dilate(transp, band) & (~transp)
    cap = np.maximum(rgb[..., 0], rgb[..., 2])
    spill = np.maximum(rgb[..., 1] - cap, 0.0)
    g_new = rgb[..., 1] - np.where(edge, spill, 0.0)
    if np.array_equal(g_new, rgb[..., 1]):
        return None                # no green excess on the edge -> leave as-is
    rgb[..., 1] = g_new
    a[..., :3] = rgb
    return Image.fromarray(a.round().clip(0, 255).astype(np.uint8), "RGBA")


def encode_webp_b64(img):
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="WEBP", quality=80, method=4)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main():
    ap = argparse.ArgumentParser(
        description="Edge-band despill an already-keyed canonical pool.")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--band", type=int, default=2,
                    help="width in px of the opaque edge ring to despill (default 2)")
    ap.add_argument("--status", help="only entries with this status (e.g. in-game)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report counts; write nothing")
    args = ap.parse_args()

    with open(args.pool, "rb") as f:
        pool = pickle.load(f)

    changed = unchanged = no_alpha = 0
    for pid, e in pool.items():
        if args.status and e.get("status") != args.status:
            continue
        b = e.get("img_b64")
        if not b:
            continue
        im = Image.open(io.BytesIO(base64.b64decode(b)))
        if im.mode not in ("RGBA", "LA"):
            no_alpha += 1
            continue
        out = despill_edge(im, args.band)
        if out is None:
            unchanged += 1
            continue
        if not args.dry_run:
            e["img_b64"] = encode_webp_b64(out)
        changed += 1

    print(f"despilled {changed} sprites  "
          f"(unchanged {unchanged}, opaque/no-alpha {no_alpha})")
    if args.dry_run:
        print("DRY RUN -- pool not written.")
        return
    with open(args.pool, "wb") as f:
        pickle.dump(pool, f)
    print(f"wrote {args.pool}")


if __name__ == "__main__":
    main()
