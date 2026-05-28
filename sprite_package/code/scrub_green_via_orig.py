"""
Scrub residual Gemini bg-green from a keyed canonical pool, using the
pre-greening pool as ground truth.

After the Gemini round-trip + chroma_key, two kinds of green survive:

1. Enclosed interiors that the key flood-fill couldn't reach (the hole
   in an archway, the panel of a door, the inside of a ring). The pixels
   are bright green, but they sit inside a closed sprite silhouette.
2. A thin edge fringe where the kept anti-aliased edge still carries
   spill from the painted-on green background.

A pure-image despill can't tell case 1 from a genuinely green sprite
(slime, healing potion, green gem). The orig pool can: any pixel that
is green-excess NOW but was NOT green-excess BEFORE the greening is, by
construction, contamination -- you can't gain real green art during a
chroma-key.

For each (current, orig) sprite pair this:
  - cuts pixels where current is green-excess but orig was not, by
    setting their alpha to 0;
  - despills the resulting opaque edge band -- general key-colour
    formula (cap each dominant key channel at the highest weak channel)
    so the same code works if we ever key against another colour.

Pixels where orig was already green-excess are NEVER touched, so a
genuine green sprite (orig green ~ current green) survives untouched.

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
except ImportError:
    print("ERROR: Pillow and numpy required.  pip install Pillow numpy",
          file=sys.stderr)
    sys.exit(1)


GREEN_KEY = (0, 255, 0)
# "Contamination" = how much MORE green-excess a pixel has now than it did in
# the orig pool. Threshold compares the SHIFT, not the absolute level, so a
# sprite that was always teal/cyan in orig (where G is high but not channel-
# dominant, so absolute green-excess is near 0) survives untouched -- we only
# cut where Gemini pushed the pixel further into pure-green than it ever was.
GEX_SHIFT = 30


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


def _green_excess(rgb):
    return rgb[..., 1].astype(np.int16) - np.maximum(rgb[..., 0], rgb[..., 2]).astype(np.int16)


def scrub(cur_im, orig_im, key=GREEN_KEY, despill_band=3):
    """Return a new RGBA image with contamination cut and edges despilled,
    or None if no change is needed."""
    cur = np.asarray(cur_im.convert("RGBA"), dtype=np.float32)
    rgb = cur[..., :3]
    alpha = cur[..., 3].copy()

    orig_arr = np.asarray(orig_im.convert("RGB"), dtype=np.float32)
    if orig_arr.shape[:2] != rgb.shape[:2]:
        orig_arr = np.asarray(
            orig_im.convert("RGB").resize(cur_im.size, Image.LANCZOS),
            dtype=np.float32,
        )

    cur_gex = _green_excess(rgb)
    orig_gex = _green_excess(orig_arr)

    # Contamination = pixel got noticeably greener than orig. Catches both
    # interior-fill (orig gex ~ 0, cur gex ~ 100, shift = 100) and edge fringe
    # (orig gex ~ 0, cur gex ~ 40, shift = 40), and leaves intrinsic green art
    # alone (orig and cur both gex ~ 80, shift ~ 0).
    opaque = alpha > 32
    contam = opaque & ((cur_gex - orig_gex) > GEX_SHIFT)

    if not contam.any():
        # Even with no enclosed contamination, the existing edge ring may
        # still hold soft fringe -- let the despill pass run anyway.
        pass

    # Cut: drop alpha to 0 wherever we flagged contamination.
    alpha[contam] = 0

    # Generalised key-colour despill on the opaque edge band.
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

    # Did anything actually change?
    new_arr = np.dstack([rgb, alpha]).round().clip(0, 255).astype(np.uint8)
    if np.array_equal(new_arr, np.asarray(cur_im.convert("RGBA"))):
        return None, int(contam.sum())
    return Image.fromarray(new_arr, "RGBA"), int(contam.sum())


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
    """rows: list of (pid, cat, orig_im, before_im, after_im, n_cut)."""
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
    for i, (pid, cat, orig_im, before_im, after_im, n_cut) in enumerate(rows):
        y = 25 + i * (TILE + PAD * 2 + LABEL)
        x0 = PAD + 200
        d.text((PAD, y + TILE // 2 - 8), f"{pid}\n{cat}\ncut: {n_cut}px",
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
        # Score every pid by contamination count, then render the worst N.
        candidates = []
        for pid, ent in pool.items():
            if pid not in orig_pool:
                continue
            cim = Image.open(io.BytesIO(base64.b64decode(ent["img_b64"])))
            if cim.mode not in ("RGBA", "LA"):
                continue
            oim = Image.open(io.BytesIO(base64.b64decode(orig_pool[pid]["img_b64"])))
            after, n_cut = scrub(cim, oim, despill_band=args.band)
            if after is None or n_cut < 10:
                continue
            candidates.append((pid, ent["cat"], cim.copy(), after, oim.copy(), n_cut))
        candidates.sort(key=lambda r: -r[5])
        rows = [(pid, cat, oim, before, after, n)
                for pid, cat, before, after, oim, n in candidates[: args.sample]]
        if not rows:
            print("nothing flagged.")
            return
        size = render_sample(rows, args.sample_out)
        print(f"sample render: {args.sample_out}  {size[0]}x{size[1]}  "
              f"({len(rows)} sprites, worst-first)")
        return

    cut_total = 0
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
        out, n_cut = scrub(cim, oim, despill_band=args.band)
        cut_total += n_cut
        if out is None:
            unchanged += 1
            continue
        if not args.dry_run:
            ent["img_b64"] = encode_webp_b64(out)
        changed += 1

    print(f"scrubbed {changed} sprites  "
          f"({cut_total} green pixels cut total, unchanged {unchanged}, "
          f"no-alpha {no_alpha}, missing-orig {missing})")
    if args.dry_run:
        print("DRY RUN -- pool not written.")
        return
    with open(args.pool, "wb") as f:
        pickle.dump(pool, f)
    print(f"wrote {args.pool}")


if __name__ == "__main__":
    main()
