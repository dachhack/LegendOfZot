"""
Replace specific pool sprites with their pre-Gemini orig art, re-keyed
to transparent.

Use when the Gemini round-trip swapped the sprite for a completely
different one (P170: pink round bottle -> green Erlenmeyer flask). The
scrubber can't fix those cases -- restoring orig RGB onto current's
alpha just makes a Frankenstein. The clean fix is to drop current
entirely and take orig as both the colour and the shape, then chroma-
key its background out so it gets proper transparency.

Per pid:
  1. Read orig RGB from --orig-pool.
  2. Auto-detect orig's bg colour from a thin border ring (median),
     or take it from --key HEX.
  3. Run chroma_key.py's keying + edge despill at default thresholds.
  4. Re-encode as WebP and write into --pool.

Usage:
    python3 sprite_package/code/restore_from_orig.py \\
        --pool wizardscavern/data/canonical_pool_full.pkl \\
        --orig-pool /tmp/pool_orig.pkl \\
        --pids P170
    # or batch:
    python3 sprite_package/code/restore_from_orig.py --pool ... --orig-pool ... \\
        --pids-file /tmp/swaps.txt
"""

import argparse
import base64
import io
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
import chroma_key as ck


def _auto_key(orig_im):
    arr = np.asarray(orig_im.convert("RGB"), dtype=np.int16)
    H, W = arr.shape[:2]
    bw = max(1, min(3, H // 16, W // 16))
    ring = np.concatenate([
        arr[:bw, :, :].reshape(-1, 3),
        arr[-bw:, :, :].reshape(-1, 3),
        arr[:, :bw, :].reshape(-1, 3),
        arr[:, -bw:, :].reshape(-1, 3),
    ])
    return tuple(int(c) for c in np.median(ring, axis=0))


def restore(orig_im, key=None, inner=20, outer=80, despill_band=3):
    if key is None:
        key = _auto_key(orig_im)
    keyed = ck.chroma_key(
        orig_im.convert("RGBA"),
        key=key,
        inner=inner,
        outer=outer,
        despill=True,
        despill_band=despill_band,
    )
    return keyed, key


def encode_webp_b64(img):
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="WEBP", quality=80, method=4)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--pool", required=True)
    ap.add_argument("--orig-pool", required=True)
    ap.add_argument("--pids", nargs="*", default=[],
                    help="pids to restore (e.g. --pids P170 W141)")
    ap.add_argument("--pids-file",
                    help="text file with one pid per line, or a JSON list")
    ap.add_argument("--key",
                    help="force a hex key colour instead of auto-detecting")
    ap.add_argument("--inner", type=int, default=20)
    ap.add_argument("--outer", type=int, default=80)
    ap.add_argument("--despill-band", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pids = list(args.pids)
    if args.pids_file:
        text = Path(args.pids_file).read_text()
        text = text.strip()
        if text.startswith("["):
            import json
            pids.extend(json.loads(text))
        else:
            pids.extend(p.strip() for p in text.splitlines() if p.strip())
    if not pids:
        ap.error("no pids specified -- use --pids or --pids-file")

    force_key = None
    if args.key:
        k = args.key.lstrip("#")
        force_key = (int(k[0:2], 16), int(k[2:4], 16), int(k[4:6], 16))

    with open(args.pool, "rb") as f:
        pool = pickle.load(f)
    with open(args.orig_pool, "rb") as f:
        orig_pool = pickle.load(f)

    done = missing = 0
    for pid in pids:
        if pid not in orig_pool:
            print(f"  SKIP {pid}: not in orig pool")
            missing += 1
            continue
        if pid not in pool:
            print(f"  SKIP {pid}: not in current pool")
            missing += 1
            continue
        oim = Image.open(io.BytesIO(base64.b64decode(orig_pool[pid]["img_b64"])))
        keyed, key = restore(
            oim, key=force_key, inner=args.inner, outer=args.outer,
            despill_band=args.despill_band,
        )
        print(f"  {pid}: key={key}  keyed_size={keyed.size}")
        if not args.dry_run:
            pool[pid]["img_b64"] = encode_webp_b64(keyed)
        done += 1

    print(f"\nrestored {done} sprite(s); missing {missing}")
    if args.dry_run:
        print("DRY RUN -- pool not written.")
        return
    with open(args.pool, "wb") as f:
        pickle.dump(pool, f)
    print(f"wrote {args.pool}")


if __name__ == "__main__":
    main()
