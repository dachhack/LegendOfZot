"""
Restore a Gemini-round-tripped canonical pool toward the pre-greening
ground truth, pixel by pixel.

The orig pool is the source of truth: it tells us, per sprite, both
WHAT COLOUR each pixel should be and WHETHER THAT PIXEL IS PART OF THE
SPRITE AT ALL. The current pool gives us the clean RGBA alpha channel
(produced by chroma_key after the round-trip). We want orig's colour and
current's alpha, fused.

Per sprite:

  1. Flood-fill the orig RGB image from its four corners with colour
     tolerance to identify the background (the dark stone tone the orig
     was rendered against). Pixels not reached are the orig sprite.
     A 1px dilation forgives sub-pixel Gemini re-scaling.
  2. For each pixel:
       a. orig was SPRITE and current is OPAQUE  -> restore orig RGB,
          keep current alpha. Fixes "shape preserved, colour shifted"
          (W141: cyan ring desaturated to green; RM0017: arch frame
          tinted greener).
       b. orig was BACKGROUND and current is OPAQUE -> cut alpha to 0.
          Fixes "shape extended into bg" (RM0017's filled-in hole,
          AC0004's Gemini-added leaves).
  3. Generalised key-aware despill on the resulting opaque edge band so
     any leftover anti-alias fringe gets neutralised.

Genuinely green sprites (slime, healing potion liquid, green gems) are
SPRITE in orig, so they get their orig colour restored -- never cut.
Brand-new Gemini hallucinations (AC0004's leaves) are BG in orig, so
they get cut cleanly.

Usage:
    python3 sprite_package/code/scrub_green_via_orig.py \\
        --pool wizardscavern/data/canonical_pool_full.pkl \\
        --orig-pool /tmp/pool_orig.pkl
    # dry run (counts only):
    python3 sprite_package/code/scrub_green_via_orig.py --pool ... --orig-pool ... --dry-run
    # save a side-by-side render of the N worst sprites before/after:
    python3 sprite_package/code/scrub_green_via_orig.py --pool ... --orig-pool ... \\
        --sample 12 --sample-out /tmp/scrub_sample.png
"""

import argparse
import base64
import io
import pickle
import sys

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from scipy.ndimage import binary_dilation
except ImportError:
    print("ERROR: Pillow, numpy and scipy required.  "
          "pip install Pillow numpy scipy", file=sys.stderr)
    sys.exit(1)


GREEN_KEY = (0, 255, 0)
BG_TOLERANCE = 40    # px-color must be within this Linf distance to count as bg
SPRITE_DILATE = 1    # forgive sub-pixel Gemini re-scaling by widening sprite mask


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


def _orig_bg_mask(orig_rgb_arr, tol=BG_TOLERANCE):
    """Flood-fill bg from the four corners through pixels close to the median
    border colour. Returns a bool mask (True where bg)."""
    H, W = orig_rgb_arr.shape[:2]
    arr_i = orig_rgb_arr.astype(np.int16)
    # Median of a thin border ring -- robust to a noisy corner pixel.
    bw = max(1, min(3, H // 16, W // 16))
    ring = np.concatenate([
        arr_i[:bw, :, :].reshape(-1, 3),
        arr_i[-bw:, :, :].reshape(-1, 3),
        arr_i[:, :bw, :].reshape(-1, 3),
        arr_i[:, -bw:, :].reshape(-1, 3),
    ])
    bg_color = np.median(ring, axis=0)
    close = np.max(np.abs(arr_i - bg_color), axis=-1) <= tol
    # Seed from the four corners IF they're close to bg.
    seed = np.zeros_like(close)
    for cy, cx in [(0, 0), (0, W-1), (H-1, 0), (H-1, W-1)]:
        if close[cy, cx]:
            seed[cy, cx] = True
    if not seed.any():
        # All corners look like sprite -- treat nothing as bg.
        return np.zeros_like(close)
    # Flood-fill through 'close' using binary dilation with mask.
    prev = -1
    cur = seed
    while cur.sum() != prev:
        prev = cur.sum()
        cur = binary_dilation(cur, iterations=1, mask=close)
    return cur


def scrub(cur_im, orig_im, key=GREEN_KEY, despill_band=3,
          sprite_dilate=SPRITE_DILATE):
    """Return (new_rgba_image, n_restored, n_cut), or (None, 0, 0) if no change."""
    cur = np.asarray(cur_im.convert("RGBA"), dtype=np.float32)
    rgb = cur[..., :3].copy()
    alpha = cur[..., 3].copy()

    orig_arr = np.asarray(orig_im.convert("RGB"), dtype=np.float32)
    if orig_arr.shape[:2] != rgb.shape[:2]:
        orig_arr = np.asarray(
            orig_im.convert("RGB").resize(cur_im.size, Image.LANCZOS),
            dtype=np.float32,
        )

    bg = _orig_bg_mask(orig_arr)
    sprite = ~bg
    if sprite_dilate > 0 and sprite.any():
        sprite = binary_dilation(sprite, iterations=sprite_dilate)
        bg = ~sprite

    opaque = alpha > 32

    # (a) Where orig was sprite and current is opaque: restore orig RGB
    #     (Gemini may have shifted the colour; orig is ground truth). We
    #     keep current's alpha so anti-aliased edges remain soft.
    restore = sprite & opaque
    if restore.any():
        rgb[restore] = orig_arr[restore]

    # (b) Where orig was bg and current is opaque: this is sprite-extension
    #     contamination -- bg painted-in regions (arch holes, ring centres,
    #     Gemini-hallucinated leaves). Cut alpha to 0.
    cut = bg & opaque
    if cut.any():
        alpha[cut] = 0.0

    # (c) Generalised despill on the resulting opaque edge band.
    if despill_band > 0:
        transp = alpha < 32
        if transp.any() and (~transp).any():
            band = _dilate(transp, despill_band) & (~transp)
            key_arr = np.asarray(key, dtype=np.float32)
            key_mean = float(key_arr.mean())
            dom = key_arr > key_mean
            weak = key_arr < key_mean
            if weak.any() and dom.any():
                weak_max = rgb[..., weak].max(axis=-1)
                for ch in range(3):
                    if dom[ch]:
                        excess = np.maximum(rgb[..., ch] - weak_max, 0.0)
                        rgb[..., ch] = np.where(
                            band, rgb[..., ch] - excess, rgb[..., ch]
                        )

    new_arr = np.dstack([rgb, alpha]).round().clip(0, 255).astype(np.uint8)
    if np.array_equal(new_arr, np.asarray(cur_im.convert("RGBA"))):
        return None, 0, 0
    return Image.fromarray(new_arr, "RGBA"), int(restore.sum()), int(cut.sum())


def encode_webp_b64(img):
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="WEBP", quality=80, method=4)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _make_stone(size):
    a = np.full((size, size, 3), (45, 38, 32), dtype=np.uint8)
    rng = np.random.RandomState(0)
    n = rng.randint(-8, 8, (size, size, 3))
    return Image.fromarray(np.clip(a + n, 0, 255).astype(np.uint8))


def render_sample(rows, out_path):
    """rows: list of (pid, cat, orig_im, before_im, after_im, n_restored, n_cut)."""
    TILE = 192
    PAD = 6
    LABEL = 22
    COLS = 4  # orig | before | after | alpha(after)
    R = len(rows)
    W = COLS * (TILE + PAD) + PAD * 2 + 220
    H = R * (TILE + PAD * 2 + LABEL) + 30

    canvas = Image.new("RGB", (W, H), (15, 15, 20))
    d = ImageDraw.Draw(canvas)
    try:
        f = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14
        )
        fs = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11
        )
    except Exception:
        f = ImageFont.load_default()
        fs = f
    d.text((PAD, 4),
           "ORIG (RGB) | BEFORE pool (RGBA on stone) | AFTER scrub (on stone) | AFTER alpha",
           fill=(255, 220, 100), font=f)

    stone = _make_stone(TILE)
    for i, (pid, cat, orig_im, before_im, after_im, n_restored, n_cut) in enumerate(rows):
        y = 25 + i * (TILE + PAD * 2 + LABEL)
        x0 = PAD + 200
        d.text((PAD, y + TILE // 2 - 16),
               f"{pid}\n{cat}\nrestore:{n_restored}\ncut: {n_cut}",
               fill=(220, 220, 180), font=fs)

        def sz(im, mode="RGBA"):
            im = im.convert(mode)
            if im.size != (TILE, TILE):
                im = im.resize((TILE, TILE), Image.NEAREST)
            return im

        canvas.paste(sz(orig_im, "RGB"), (x0, y))
        cell_b = stone.copy()
        b = sz(before_im)
        cell_b.paste(b, (0, 0), b)
        canvas.paste(cell_b, (x0 + (TILE + PAD), y))
        cell_a = stone.copy()
        a = sz(after_im)
        cell_a.paste(a, (0, 0), a)
        canvas.paste(cell_a, (x0 + 2 * (TILE + PAD), y))
        alpha = sz(after_im).split()[3]
        canvas.paste(Image.merge("RGB", (alpha, alpha, alpha)),
                     (x0 + 3 * (TILE + PAD), y))

    canvas.save(out_path)
    return canvas.size


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True,
                    help="canonical pool (will be modified in place unless --dry-run)")
    ap.add_argument("--orig-pool", required=True,
                    help="pre-greening canonical pool used as the ground-truth reference")
    ap.add_argument("--band", type=int, default=3,
                    help="edge-despill band width in px (default 3)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report stats only; do not modify the pool")
    ap.add_argument("--sample", type=int, default=0,
                    help="render side-by-side preview of the N worst sprites and exit")
    ap.add_argument("--sample-out", default="/tmp/scrub_sample.png",
                    help="output path for --sample render")
    args = ap.parse_args()

    with open(args.pool, "rb") as f:
        pool = pickle.load(f)
    with open(args.orig_pool, "rb") as f:
        orig_pool = pickle.load(f)

    if args.sample > 0:
        candidates = []
        for pid, ent in pool.items():
            if pid not in orig_pool:
                continue
            cim = Image.open(io.BytesIO(base64.b64decode(ent["img_b64"])))
            if cim.mode not in ("RGBA", "LA"):
                continue
            oim = Image.open(io.BytesIO(base64.b64decode(orig_pool[pid]["img_b64"])))
            after, n_restored, n_cut = scrub(cim, oim, despill_band=args.band)
            if after is None or (n_cut + n_restored) < 10:
                continue
            candidates.append((pid, ent["cat"], cim.copy(), after, oim.copy(),
                               n_restored, n_cut))
        candidates.sort(key=lambda r: -(r[5] + r[6]))
        rows = [(pid, cat, oim, before, after, nr, nc)
                for pid, cat, before, after, oim, nr, nc in candidates[: args.sample]]
        if not rows:
            print("nothing flagged.")
            return
        size = render_sample(rows, args.sample_out)
        print(f"sample render: {args.sample_out}  {size[0]}x{size[1]}  "
              f"({len(rows)} sprites, worst-first)")
        return

    cut_total = restored_total = 0
    changed = unchanged = no_alpha = missing = 0
    for pid, ent in pool.items():
        if pid not in orig_pool:
            missing += 1
            continue
        cim = Image.open(io.BytesIO(base64.b64decode(ent["img_b64"])))
        if cim.mode not in ("RGBA", "LA"):
            no_alpha += 1
            continue
        oim = Image.open(io.BytesIO(base64.b64decode(orig_pool[pid]["img_b64"])))
        out, n_restored, n_cut = scrub(cim, oim, despill_band=args.band)
        cut_total += n_cut
        restored_total += n_restored
        if out is None:
            unchanged += 1
            continue
        if not args.dry_run:
            ent["img_b64"] = encode_webp_b64(out)
        changed += 1

    print(f"scrubbed {changed} sprites  "
          f"(restored {restored_total} px, cut {cut_total} px, "
          f"unchanged {unchanged}, no-alpha {no_alpha}, missing-orig {missing})")
    if args.dry_run:
        print("DRY RUN -- pool not written.")
        return
    with open(args.pool, "wb") as f:
        pickle.dump(pool, f)
    print(f"wrote {args.pool}")


if __name__ == "__main__":
    main()
