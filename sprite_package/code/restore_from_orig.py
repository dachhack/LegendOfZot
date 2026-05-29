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
import scrub_green_via_orig as sgo


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


def _flood_alpha(orig_im, despill_band=2):
    """Use the orig flood-fill bg mask to produce an RGBA image. Robust when
    the bg colour overlaps with dark sprite tones (chroma_key would over-key
    in that case). The flood reaches BG only through bg-coloured pixels from
    the four corners, so isolated dark sprite pixels (eyes, armour) survive.

    Anti-aliased orig edges are within bg tolerance and get swept up as bg
    by the flood, which leaves the sprite-side edge clean. The result has
    hard-edged alpha; the edge-band despill then neutralises any green
    fringe that came along with the kept RGB.
    """
    orig_rgb = np.asarray(orig_im.convert("RGB"), dtype=np.float32)
    bg = sgo._orig_bg_mask(orig_rgb)
    sprite = ~bg
    alpha = np.where(sprite, 255.0, 0.0)
    rgba = np.dstack([orig_rgb, alpha])
    out = Image.fromarray(rgba.round().clip(0, 255).astype(np.uint8), "RGBA")
    if despill_band > 0:
        # Run the generalised despill against the orig's bg colour. Caps any
        # spill direction the bg leans toward (green/dark/whatever) without
        # assuming a specific key.
        bg_color = _auto_key(orig_im)
        out = ck.chroma_key(
            out, key=bg_color,
            inner=999, outer=999,        # no-op the keying; we want despill only
            despill=True, despill_band=despill_band,
        )
        # ^ chroma_key recomputes alpha from RGB distance; with inner=outer=999
        # every pixel gets alpha=0. Bypass it: feed our hard alpha back through.
        new_arr = np.asarray(out, dtype=np.float32).copy()
        new_arr[..., 3] = alpha
        out = Image.fromarray(new_arr.round().clip(0, 255).astype(np.uint8), "RGBA")
    return out


def _trim_alpha(cur_im, orig_im, despill_band=3, sprite_dilate=1):
    """Keep current's RGB (Gemini's interpretation -- the bug body, the
    armour detail, whatever) but TRIM its alpha to orig's silhouette.
    Use for halo-only cases where the sprite shape is fine but a ring of
    dark Gemini-bg leaked through the chroma key. The orig flood-fill
    gives the clean shape; current keeps its colour.
    """
    cur = np.asarray(cur_im.convert("RGBA"), dtype=np.float32)
    rgb = cur[..., :3].copy()
    alpha = cur[..., 3].copy()

    orig_arr = np.asarray(orig_im.convert("RGB"), dtype=np.float32)
    if orig_arr.shape[:2] != rgb.shape[:2]:
        orig_arr = np.asarray(
            orig_im.convert("RGB").resize(cur_im.size, Image.LANCZOS),
            dtype=np.float32,
        )

    bg = sgo._orig_bg_mask(orig_arr)
    sprite = ~bg
    if sprite_dilate > 0 and sprite.any():
        from scipy.ndimage import binary_dilation
        sprite = binary_dilation(sprite, iterations=sprite_dilate)
        bg = ~sprite

    # Cut alpha wherever orig says bg. Current's RGB is preserved
    # everywhere; only the silhouette is tightened.
    alpha = np.where(bg, 0.0, alpha)

    if despill_band > 0:
        transp = alpha < 32
        if transp.any() and (~transp).any():
            from scrub_green_via_orig import _dilate
            band = _dilate(transp, despill_band) & (~transp)
            # Use green key by default for the despill since that's what
            # leaked through; harmless for any other tint.
            key = np.asarray(GREEN_KEY := (0, 255, 0), dtype=np.float32)
            key_mean = float(key.mean())
            dom = key > key_mean
            weak = key < key_mean
            if weak.any() and dom.any():
                weak_max = rgb[..., weak].max(axis=-1)
                for ch in range(3):
                    if dom[ch]:
                        excess = np.maximum(rgb[..., ch] - weak_max, 0.0)
                        rgb[..., ch] = np.where(
                            band, rgb[..., ch] - excess, rgb[..., ch]
                        )

    new_arr = np.dstack([rgb, alpha]).round().clip(0, 255).astype(np.uint8)
    return Image.fromarray(new_arr, "RGBA")


def _dim_to_orig(cur_im, orig_im, threshold=15, full=75):
    """Where CURRENT is brighter than ORIG (luma delta > threshold), blend
    current RGB toward orig RGB. Weight ramps 0 at delta=threshold up to 1
    at delta=full. Alpha is preserved -- the silhouette stays Gemini's,
    only the colour is pulled back toward the pre-greening original. This
    catches the systematic "Gemini washed everything a few stops brighter"
    pattern, while leaving anti-aliased edge anti-alias (small delta) alone.
    """
    cur = np.asarray(cur_im.convert("RGBA"), dtype=np.float32)
    rgb = cur[..., :3].copy()
    alpha = cur[..., 3]

    orig_arr = np.asarray(orig_im.convert("RGB"), dtype=np.float32)
    if orig_arr.shape[:2] != rgb.shape[:2]:
        orig_arr = np.asarray(
            orig_im.convert("RGB").resize(cur_im.size, Image.LANCZOS),
            dtype=np.float32,
        )

    # Rec.709 luma
    def _luma(arr):
        return 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]

    delta = _luma(rgb) - _luma(orig_arr)
    opaque = alpha > 32
    mask = (delta > threshold) & opaque
    if not mask.any():
        return cur_im, 0
    weight = np.clip((delta - threshold) / max(full - threshold, 1), 0.0, 1.0)
    w = weight[..., None]
    rgb = np.where(mask[..., None], rgb * (1 - w) + orig_arr * w, rgb)

    new_arr = np.dstack([rgb, alpha]).round().clip(0, 255).astype(np.uint8)
    return Image.fromarray(new_arr, "RGBA"), int(mask.sum())


def restore(orig_im, mode="flood", cur_im=None, key=None,
            inner=20, outer=80, despill_band=3):
    """mode='dim'    : keep current's alpha + shape, blend RGB toward orig
                       where current is brighter than orig. Use for the
                       'Gemini washed it lighter' pattern; needs cur_im.
       mode='trim'   : keep current's RGB, use orig flood mask as alpha
                       (kills halo without losing Gemini detail); needs cur_im.
       mode='flood'  : drop current entirely, re-key orig via flood-fill mask
                       (robust on dark bgs); for real Gemini swaps.
       mode='chroma' : chroma_key the orig with auto-detected (or forced) key
                       (legacy fallback)."""
    if mode == "dim":
        if cur_im is None:
            raise ValueError("--mode dim needs the current pool image too")
        out, n = _dim_to_orig(cur_im, orig_im)
        return out, f"dim:{n}"
    if mode == "trim":
        if cur_im is None:
            raise ValueError("--mode trim needs the current pool image too")
        return _trim_alpha(cur_im, orig_im, despill_band=despill_band), "trim"
    if mode == "flood":
        return _flood_alpha(orig_im, despill_band=max(2, despill_band)), "flood"
    if key is None:
        key = _auto_key(orig_im)
    keyed = ck.chroma_key(
        orig_im.convert("RGBA"),
        key=key, inner=inner, outer=outer,
        despill=True, despill_band=despill_band,
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
                    help="force a hex key colour instead of auto-detecting (only with --mode chroma)")
    ap.add_argument("--mode",
                    choices=["dim", "trim", "flood", "chroma"], default="dim",
                    help="dim (default): keep current's alpha, blend RGB "
                         "toward orig where current is brighter than orig; "
                         "trim: keep current's RGB, use orig flood mask as "
                         "alpha; flood: drop current and re-key orig from "
                         "its flood-fill mask (real swaps); chroma: legacy "
                         "auto-detected chroma_key of orig")
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
        cim = Image.open(io.BytesIO(base64.b64decode(pool[pid]["img_b64"])))
        keyed, key = restore(
            oim, mode=args.mode, cur_im=cim, key=force_key, inner=args.inner,
            outer=args.outer, despill_band=args.despill_band,
        )
        print(f"  {pid}: mode={args.mode} key={key}  size={keyed.size}")
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
