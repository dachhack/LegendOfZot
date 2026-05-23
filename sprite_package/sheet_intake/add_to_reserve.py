"""
Sheet intake -- step 2 of 2: write the cells you kept in the picker into the
reserve so they become candidates for future assignment.

Reads the staging produced by slice_and_pick.py plus your sheet_selection.json,
assigns fresh globally-unique PIDs, copies the kept cells into
    assets/sprites/reserve/<category>/<PID>_<label>_<src_label>.png
and updates that category's:
    assets/sprites/reserve/<category>/manifest.json
    sprite_package/libraries/<category>_library.json   (reserve[] list)

Usage:
    python3 sprite_package/sheet_intake/add_to_reserve.py --label S7A
        [--selection sprite_package/sheet_intake/sheet_selection.json]
        [--pid-prefix MN] [--dry-run]

PIDs: a category's prefix (e.g. MN for monsters) is auto-detected from its
existing reserve manifest; numbering continues above the GLOBAL max for that
prefix (in-game pool + reserve), so new PIDs never collide.

After a real run, the new PNGs live only in the gitignored assets/sprites/
tree. To make them survive a fresh checkout, re-publish the bundle:
    bash sprite_package/repack_bundle.sh   # then upload to the sprite-assets-v1 release
(The local picker surfaces them immediately without that step.)

ASCII only.
"""
import argparse
import json
import os
import pickle
import re
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_POOL = os.path.join(_ROOT, 'wizardscavern', 'data', 'canonical_pool_full.pkl')


def detect_prefix(manifest, override):
    if override:
        return override
    from collections import Counter
    pre = Counter(re.match(r'^([A-Za-z]+)', s['pid']).group(1)
                  for s in manifest.get('sprites', []) if s.get('pid'))
    if not pre:
        sys.exit("ERROR: category reserve is empty; pass --pid-prefix.")
    return pre.most_common(1)[0][0]


def global_max(prefix):
    """Highest numeric suffix for `prefix` across the in-game pool and every
    reserve manifest (so a new PID can't collide with anything, anywhere)."""
    mx = 0
    pat = re.compile(r'^' + re.escape(prefix) + r'(\d+)$')
    if os.path.exists(_POOL):
        with open(_POOL, 'rb') as f:
            for pid in pickle.load(f):
                m = pat.match(pid)
                if m:
                    mx = max(mx, int(m.group(1)))
    res_root = os.path.join(_ROOT, 'assets', 'sprites', 'reserve')
    if os.path.isdir(res_root):
        for cat in os.listdir(res_root):
            mpath = os.path.join(res_root, cat, 'manifest.json')
            if not os.path.exists(mpath):
                continue
            for s in json.load(open(mpath)).get('sprites', []):
                m = pat.match(s.get('pid', ''))
                if m:
                    mx = max(mx, int(m.group(1)))
    return mx


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--label', required=True, help='Sheet id used in slice_and_pick.py.')
    ap.add_argument('--selection', default=os.path.join(_HERE, 'sheet_selection.json'))
    ap.add_argument('--staging-dir', default=os.path.join(_HERE, 'staging'))
    ap.add_argument('--pid-prefix', default=None, help='Override the auto-detected PID prefix.')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    stage = os.path.join(args.staging_dir, args.label)
    intake_path = os.path.join(stage, '_intake.json')
    if not os.path.exists(intake_path):
        sys.exit(f"ERROR: no staging for label '{args.label}' at {stage} "
                 f"(run slice_and_pick.py first).")
    intake = json.load(open(intake_path))
    category = intake['category']

    if not os.path.exists(args.selection):
        sys.exit(f"ERROR: selection not found: {args.selection} "
                 f"(Save it from the picker).")
    sel = json.load(open(args.selection))
    if sel.get('label') != args.label:
        sys.exit(f"ERROR: selection label {sel.get('label')!r} != --label {args.label!r}.")
    keep = set(sel.get('keep', []))
    if not keep:
        sys.exit("ERROR: selection has no kept cells.")

    by_src = {c['src_label']: c for c in intake['cells']}
    kept = [by_src[k] for k in sel['keep'] if k in by_src]
    if not kept:
        sys.exit("ERROR: none of the kept src_labels match the staging.")

    res_dir = os.path.join(_ROOT, 'assets', 'sprites', 'reserve', category)
    manifest_path = os.path.join(res_dir, 'manifest.json')
    lib_path = os.path.join(_ROOT, 'sprite_package', 'libraries', f'{category}_library.json')
    if not os.path.exists(manifest_path):
        sys.exit(f"ERROR: reserve manifest missing: {manifest_path} "
                 f"(unpack the assets bundle first).")
    manifest = json.load(open(manifest_path))
    library = json.load(open(lib_path)) if os.path.exists(lib_path) else None

    prefix = detect_prefix(manifest, args.pid_prefix)
    nxt = global_max(prefix) + 1
    width = max(4, len(str(nxt + len(kept))))

    print(f"label={args.label} category={category} prefix={prefix} "
          f"kept={len(kept)} -> PIDs {prefix}{nxt:0{width}d}..{prefix}{nxt+len(kept)-1:0{width}d}"
          + ("  [DRY RUN]" if args.dry_run else ""))

    new_manifest, new_library = [], []
    for i, cell in enumerate(kept):
        pid = f"{prefix}{nxt + i:0{width}d}"
        src_label = cell['src_label']
        dst_name = f"{pid}_{args.label}_{src_label}.png"
        src_png = os.path.join(stage, cell['filename'])
        dst_png = os.path.join(res_dir, dst_name)
        print(f"  {src_label} -> {pid}  ({dst_name})")
        if not args.dry_run:
            shutil.copyfile(src_png, dst_png)
        new_manifest.append({
            'pid': pid, 'filename': dst_name, 'sheet': args.label,
            'src_label': src_label, 'source_row': cell['source_row'],
            'source_col': cell['source_col'], 'marked': None,
        })
        new_library.append({
            'pid': pid, 'sheet': args.label, 'src_label': src_label,
            'status': 'reserve', 'source_row': cell['source_row'],
            'source_col': cell['source_col'], 'marked': None,
        })

    if args.dry_run:
        print("\nDRY RUN -- nothing written.")
        return

    manifest['sprites'].extend(new_manifest)
    manifest['count'] = len(manifest['sprites'])
    json.dump(manifest, open(manifest_path, 'w'), indent=2)

    if library is not None:
        library.setdefault('reserve', []).extend(new_library)
        library['reserve_count'] = len(library['reserve'])
        library['total_count'] = (len(library.get('chosen', []))
                                  + len(library['reserve']))
        json.dump(library, open(lib_path, 'w'), indent=2)

    print(f"\nAdded {len(kept)} sprites to reserve/{category}/ "
          f"(manifest now {manifest['count']}).")
    print("They show up immediately in the monster picker. To persist across")
    print("fresh checkouts, repack + re-publish the bundle:")
    print("  bash sprite_package/repack_bundle.sh")


if __name__ == '__main__':
    main()
