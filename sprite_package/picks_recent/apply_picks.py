"""
Apply the JSON output of picker.html back into the per-category sprite
maps under wizardscavern/sprites/.

Run:
    python3 sprite_package/picks_recent/apply_picks.py
        [--input recent_picks.json]
        [--reserve-dir /tmp/wc_reserve/wc_sprites_assets/reserve]
        [--dry-run]

For each pick:
  1. If the PID isn't already in canonical_pool_full.pkl, promote the
     PNG from --reserve-dir (encode as base64 webp matching pool
     conventions) and write the pool back.
  2. Update the sprite map (_SPELLS_NAMED single-pid dict, or
     _ACCESSORIES_MAP [(pid, 0)] block).

Skip the pool step entirely if every picked PID is already shipped.
With --dry-run nothing is written; you get the planned actions.
"""
import argparse
import base64
import io
import json
import os
import pickle
import re
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_SPRITES_DIR = os.path.join(_ROOT, 'wizardscavern', 'sprites')
_POOL_PATH = os.path.join(_ROOT, 'wizardscavern', 'data',
                          'canonical_pool_full.pkl')


def _spells_path():
    return os.path.join(_SPRITES_DIR, 'spells.py')


def _accessories_path():
    return os.path.join(_SPRITES_DIR, 'accessories.py')


# --- Pool promotion -------------------------------------------------------

def png_to_b64_webp(path):
    """Match canonical_pool_full.pkl format (webp@80, method=4)."""
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=80, method=4)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def find_reserve_png(reserve_dir, category, pid):
    """Return Path to <pid>_*.png under reserve_dir/category/, or None."""
    cat_dir = Path(reserve_dir) / category
    if not cat_dir.exists():
        return None
    hits = list(cat_dir.glob(f"{pid}_*.png"))
    return hits[0] if hits else None


def promote_pids(pool, picks_by_cat, reserve_dir, dry_run):
    """Add missing reserve PIDs to the pool. Mutates `pool` in place.
    Returns list of (pid, action) for reporting."""
    actions = []
    for category, entries in picks_by_cat.items():
        for _name, pid in entries:
            if pid in pool:
                actions.append((pid, 'already-in-pool'))
                continue
            png = find_reserve_png(reserve_dir, category, pid)
            if png is None:
                raise RuntimeError(
                    f"Reserve PNG for {pid} not found under "
                    f"{Path(reserve_dir) / category}/. Re-unzip the "
                    f"sprite-assets-v1 release into --reserve-dir.")
            img_b64 = '' if dry_run else png_to_b64_webp(png)
            # Match the schema other pool entries use (cat / status / pid /
            # img_b64 / sheet / src_label / game_data).
            pool[pid] = {
                'pid': pid,
                'cat': category,
                'status': 'in-game',
                'img_b64': img_b64,
                'sheet': png.stem.split('_', 1)[1] if '_' in png.stem else '',
                'src_label': '',
                'game_data': {},
            }
            actions.append((pid, f'promoted from {png.name}'))
    return actions


# --- Sprite map edits -----------------------------------------------------

def apply_spell_pick(text, name, pid):
    """Find `'Name': 'OLDPID',` in _SPELLS_NAMED and rewrite the PID.
    Returns (new_text, action) where action is 'replaced'/'inserted'/'noop'.
    """
    pattern = re.compile(
        r"^(\s+)([\"'])" + re.escape(name) + r"\2:\s+'[A-Z]\d+',?\s*(?:#.*)?$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if m:
        indent = m.group(1)
        quote = m.group(2)
        replacement = f"{indent}{quote}{name}{quote}: {' ' * max(1, 22 - len(name) - 2)}'{pid}',"
        new_text = text[:m.start()] + replacement + text[m.end():]
        return new_text, 'replaced'

    closing = re.compile(r"^(\}\s*)$", re.MULTILINE)
    open_m = re.search(r"^_SPELLS_NAMED\s*=\s*\{\s*$", text, re.MULTILINE)
    if not open_m:
        raise RuntimeError("Could not find _SPELLS_NAMED dict in spells.py")
    close_m = closing.search(text, open_m.end())
    if not close_m:
        raise RuntimeError("Could not find _SPELLS_NAMED closing brace")
    new_line = f"    '{name}':{' ' * max(1, 22 - len(name) - 2)}'{pid}',\n"
    new_text = text[:close_m.start()] + new_line + text[close_m.start():]
    return new_text, 'inserted'


def apply_accessory_pick(text, name, pid):
    """Replace the existing `"Name": [...],` block in _ACCESSORIES_MAP
    with a single-variant `[('PID', 0)]`. Inserts new if missing."""
    block = re.compile(
        r"^(\s+)([\"'])" + re.escape(name) + r"\2:\s*\[\s*\n"
        r"(?:.*?\n)*?"
        r"\s*\],?\s*\n",
        re.MULTILINE,
    )
    m = block.search(text)
    new_block = (
        f"    '{name}': [\n"
        f"        ('{pid}', 0),  # picked via sprite_package/picks_recent\n"
        f"    ],\n"
    )
    if m:
        new_text = text[:m.start()] + new_block + text[m.end():]
        return new_text, 'replaced'

    open_m = re.search(r"^_ACCESSORIES_MAP\s*=\s*\{\s*$", text, re.MULTILINE)
    if not open_m:
        raise RuntimeError("Could not find _ACCESSORIES_MAP in accessories.py")
    close_m = re.compile(r"^\}\s*$", re.MULTILINE).search(text, open_m.end())
    if not close_m:
        raise RuntimeError("Could not find _ACCESSORIES_MAP closing brace")
    new_text = text[:close_m.start()] + new_block + text[close_m.start():]
    return new_text, 'inserted'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', default=os.path.join(_HERE, 'recent_picks.json'))
    ap.add_argument('--reserve-dir',
                    default='/tmp/wc_reserve/wc_sprites_assets/reserve',
                    help='Where the unzipped reserve PNGs live '
                         '(only needed if a picked PID is not yet in the '
                         'canonical pool).')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        sys.exit(2)

    with open(args.input, 'r') as f:
        data = json.load(f)
    picks = data.get('picks', {})
    if not picks:
        print("No picks in input -- nothing to apply.")
        return 0

    by_cat = {}
    for key, pid in picks.items():
        category, _, name = key.partition('::')
        by_cat.setdefault(category, []).append((name, pid))

    # Step 1: promote missing PIDs into the canonical pool.
    print("== pool promotion ==")
    with open(_POOL_PATH, 'rb') as f:
        pool = pickle.load(f)
    pool_size_before = len(pool)
    pool_actions = promote_pids(pool, by_cat, args.reserve_dir, args.dry_run)
    for pid, action in pool_actions:
        print(f"  {pid}: {action}")
    if args.dry_run:
        print(f"  [dry-run] would write pool "
              f"(+{len(pool) - pool_size_before} entries)")
    elif len(pool) > pool_size_before:
        with open(_POOL_PATH, 'wb') as f:
            pickle.dump(pool, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"  wrote pool: {pool_size_before} -> {len(pool)}")
    else:
        print("  pool unchanged (all PIDs already present)")

    # Step 2: rewrite the sprite-map files.
    print("\n== sprite-map edits ==")
    for category, entries in sorted(by_cat.items()):
        if category == 'spells':
            path = _spells_path()
            apply = apply_spell_pick
        elif category == 'accessories':
            path = _accessories_path()
            apply = apply_accessory_pick
        else:
            print(f"WARN: unknown category {category!r}, skipping "
                  f"{len(entries)} entries")
            continue

        with open(path, 'r') as f:
            text = f.read()
        for name, pid in sorted(entries):
            text, action = apply(text, name, pid)
            print(f"  {category}/{name!r}: {pid} ({action})")
        if args.dry_run:
            print(f"  [dry-run] would write {path}")
        else:
            with open(path, 'w') as f:
                f.write(text)
            print(f"  wrote {path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
