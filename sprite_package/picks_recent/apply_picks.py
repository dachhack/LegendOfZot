"""
Apply picker.html output through the full canonical sprite pipeline.

Run:
    python3 sprite_package/picks_recent/apply_picks.py
        [--input recent_picks.json]
        [--assets-dir assets/sprites]
        [--dry-run]

The canonical pipeline has four layers; this script updates all of them
so the result is identical to what promote_all_sprites.py would produce
on a fresh build:

  L1 (PNG bundle):     move PNG from <assets>/reserve/<src_cat>/PID_*.png
                       to <assets>/in_game/by_category/<dst_cat>/
                       PID_<sanitized_name>_v<vi>.png. Also copy into
                       by_item/<dst_cat>/<sanitized_name>/v<vi>.png so
                       both bundle views stay consistent.
  L2 (library JSON):   move the PID entry from reserve[] to chosen[] in
                       sprite_package/libraries/<dst_cat>_library.json.
                       Update chosen_count / reserve_count.
  L3 (snippet):        add the PID to the relevant
                       sprite_package/code/sprite_data_<cat>.py
                       (_<CAT>_MAP for named, _<CAT>_POOL for generic).
  L4 (runtime map):    update wizardscavern/sprites/<cat>.py so the game
                       resolves the name to the new PID at runtime.

After all four are written, regenerate canonical_pool_full.pkl by calling
promote_all_sprites.py. The pool gets the full game_data metadata the
canonical pipeline produces (item_name, category, variant_index), not
the minimal entries the earlier shortcut script left behind.

The assets bundle must be locally unpacked at --assets-dir. If it isn't,
the script prints the unzip command and exits.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_PACKAGE_DIR = os.path.join(_ROOT, 'sprite_package')
_LIBRARIES_DIR = os.path.join(_PACKAGE_DIR, 'libraries')
_SNIPPETS_DIR = os.path.join(_PACKAGE_DIR, 'code')
_RUNTIME_SPRITES_DIR = os.path.join(_ROOT, 'wizardscavern', 'sprites')
_POOL_PATH = os.path.join(_ROOT, 'wizardscavern', 'data',
                          'canonical_pool_full.pkl')
_PROMOTE_SCRIPT = os.path.join(_SNIPPETS_DIR, 'promote_all_sprites.py')

# Picker category -> runtime sprite map file + var name + shape.
# bug_weapons uses the new sprites/bug_weapons.py module wired in b414.
_CATEGORY_RUNTIME = {
    'spells':      ('spells.py',      '_SPELLS_NAMED',     'simple_dict'),
    'accessories': ('accessories.py', '_ACCESSORIES_MAP',  'variant_list'),
    'foods':       ('foods.py',       '_FOODS_MAP',        'variant_list'),
    'ingredients': ('ingredients.py', '_INGREDIENTS_MAP',  'variant_list'),
    'bug_weapons': ('bug_weapons.py', '_BUG_WEAPONS_MAP',  'variant_list'),
}

# Picker category -> reserve PNG subdir + canonical pipeline category.
# bug_weapons borrows from the weapons sprite sheets (no dedicated bug
# weapons sheet exists), so PNGs come from reserve/weapons/ but the
# canonical target category is bug_weapons (matching the bug_armors
# pattern). For all other categories, src == dst.
_CATEGORY_PIPELINE = {
    'spells':      {'reserve_subdir': 'spells',      'canonical_cat': 'spells',      'kind': 'generic'},
    'accessories': {'reserve_subdir': 'accessories', 'canonical_cat': 'accessories', 'kind': 'named'},
    'foods':       {'reserve_subdir': 'foods',       'canonical_cat': 'foods',       'kind': 'named'},
    'ingredients': {'reserve_subdir': 'ingredients', 'canonical_cat': 'ingredients', 'kind': 'named'},
    'bug_weapons': {'reserve_subdir': 'weapons',     'canonical_cat': 'bug_weapons', 'kind': 'named'},
}


# -- Helpers ---------------------------------------------------------------

def _sanitize_filename(name):
    """Mirror the convention used in existing in_game PNGs:
    'Wizard's Monocle' -> 'Wizard_s_Monocle', 'Cooking Kit' -> 'Cooking_Kit'.
    """
    out = re.sub(r"[^A-Za-z0-9]+", "_", name)
    return out.strip("_")


def _by_category_dir(assets_dir, canonical_cat):
    return Path(assets_dir) / 'in_game' / 'by_category' / canonical_cat


def _by_item_dir(assets_dir, canonical_cat, item_name):
    return (Path(assets_dir) / 'in_game' / 'by_item' / canonical_cat
            / _sanitize_filename(item_name))


def _reserve_dir(assets_dir, reserve_subdir):
    return Path(assets_dir) / 'reserve' / reserve_subdir


def _find_reserve_png(assets_dir, reserve_subdir, pid):
    cat_dir = _reserve_dir(assets_dir, reserve_subdir)
    if not cat_dir.exists():
        return None
    hits = list(cat_dir.glob(f"{pid}_*.png"))
    return hits[0] if hits else None


def _find_in_game_png(assets_dir, canonical_cat, pid):
    cat_dir = _by_category_dir(assets_dir, canonical_cat)
    if not cat_dir.exists():
        return None
    hits = list(cat_dir.glob(f"{pid}_*.png"))
    return hits[0] if hits else None


# -- L1: bundle PNG move ---------------------------------------------------

def move_png_to_in_game(pid, name, category, assets_dir, dry_run, log):
    """Move (or no-op if already moved) PNG from reserve/ to
    in_game/by_category/ and copy to in_game/by_item/. Returns the
    destination Path."""
    pipe = _CATEGORY_PIPELINE[category]
    canonical_cat = pipe['canonical_cat']
    reserve_subdir = pipe['reserve_subdir']

    # If already in in_game, we're done.
    existing = _find_in_game_png(assets_dir, canonical_cat, pid)
    if existing:
        log.append(f"    L1 PNG: already at {existing.relative_to(assets_dir)}")
        return existing

    src = _find_reserve_png(assets_dir, reserve_subdir, pid)
    if src is None:
        raise RuntimeError(
            f"PNG for {pid} not found in {_reserve_dir(assets_dir, reserve_subdir)} "
            f"or {_by_category_dir(assets_dir, canonical_cat)}.")

    dst_name = f"{pid}_{_sanitize_filename(name)}_v0.png"
    dst = _by_category_dir(assets_dir, canonical_cat) / dst_name
    by_item_path = _by_item_dir(assets_dir, canonical_cat, name) / 'v0.png'

    if dry_run:
        log.append(f"    L1 PNG: would move {src.name} -> "
                   f"{dst.relative_to(assets_dir)} (+ by_item)")
        return dst

    dst.parent.mkdir(parents=True, exist_ok=True)
    by_item_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    shutil.copy2(str(dst), str(by_item_path))
    log.append(f"    L1 PNG: moved to {dst.relative_to(assets_dir)} "
               f"(+ by_item copy)")
    return dst


# -- L2: library JSON ------------------------------------------------------

def update_library_json(pid, category, dry_run, log):
    """Move PID from reserve[] to chosen[] in the destination category's
    library. If PID lives in a different category's library (e.g.
    bug_weapons picks come from weapons_library.json), remove it from
    there first."""
    pipe = _CATEGORY_PIPELINE[category]
    canonical_cat = pipe['canonical_cat']
    reserve_subdir = pipe['reserve_subdir']

    dst_lib_path = os.path.join(_LIBRARIES_DIR,
                                f'{canonical_cat}_library.json')

    # Bootstrap the library if this is a brand-new category (bug_weapons).
    bootstrap = {
        'category': canonical_cat,
        'version': 1,
        'generated_at': '',
        'chosen_count': 0,
        'reserve_count': 0,
        'total_count': 0,
        'source_pickers': ['sprite_package/picks_recent/picker.html'],
        'chosen': [],
        'reserve': [],
    }
    if os.path.exists(dst_lib_path):
        with open(dst_lib_path, 'r') as f:
            dst_lib = json.load(f)
    else:
        dst_lib = bootstrap
        if dry_run:
            log.append(f"    L2 lib: would create {os.path.basename(dst_lib_path)}")
        else:
            with open(dst_lib_path, 'w') as f:
                json.dump(bootstrap, f, indent=2)
            log.append(f"    L2 lib: created {os.path.basename(dst_lib_path)}")

    # If PID already chosen here, nothing to do.
    if any(e.get('pid') == pid for e in dst_lib.get('chosen', [])):
        log.append(f"    L2 lib: {pid} already chosen in {canonical_cat}_library.json")
        return

    # If the PID is in the source category's library (e.g. WP0339 in
    # weapons_library.json:reserve when promoting to bug_weapons), remove
    # it from there.
    src_lib_path = os.path.join(_LIBRARIES_DIR,
                                f'{reserve_subdir}_library.json')
    src_lib = None
    src_entry = None
    if os.path.exists(src_lib_path) and src_lib_path != dst_lib_path:
        with open(src_lib_path, 'r') as f:
            src_lib = json.load(f)
        for entry in list(src_lib.get('reserve', [])):
            if entry.get('pid') == pid:
                src_entry = entry
                src_lib['reserve'].remove(entry)
                src_lib['reserve_count'] = len(src_lib['reserve'])
                src_lib['total_count'] = (src_lib.get('chosen_count', 0)
                                          + src_lib['reserve_count'])
                break

    # Try to peel from dst_lib reserve (same-category move).
    if src_entry is None:
        for entry in list(dst_lib.get('reserve', [])):
            if entry.get('pid') == pid:
                src_entry = entry
                dst_lib['reserve'].remove(entry)
                break

    if src_entry is None:
        # PID isn't in any library reserve we know about. Synthesize a
        # minimal chosen entry so promote_all_sprites can still find it
        # via the PNG-by-PID index.
        src_entry = {'pid': pid, 'sheet': '', 'src_label': '',
                     'status': 'in-game'}

    # Promote to chosen with status='in-game'.
    chosen_entry = dict(src_entry)
    chosen_entry['status'] = 'in-game'
    dst_lib.setdefault('chosen', []).append(chosen_entry)
    dst_lib['chosen_count'] = len(dst_lib['chosen'])
    dst_lib['reserve_count'] = len(dst_lib.get('reserve', []))
    dst_lib['total_count'] = dst_lib['chosen_count'] + dst_lib['reserve_count']

    if dry_run:
        log.append(f"    L2 lib: would move {pid} -> "
                   f"{canonical_cat}_library.json:chosen "
                   f"(removed from {reserve_subdir}_library.json:reserve "
                   f"if cross-category)")
        return

    with open(dst_lib_path, 'w') as f:
        json.dump(dst_lib, f, indent=2)
    if src_lib is not None:
        with open(src_lib_path, 'w') as f:
            json.dump(src_lib, f, indent=2)
    log.append(f"    L2 lib: {pid} -> {canonical_cat}_library.json:chosen")


# -- L3: sprite_data snippet ------------------------------------------------

def update_sprite_data_snippet(pid, name, category, dry_run, log):
    """Add the pick to the relevant sprite_data_<cat>.py snippet."""
    pipe = _CATEGORY_PIPELINE[category]
    canonical_cat = pipe['canonical_cat']
    kind = pipe['kind']

    snippet_path = os.path.join(_SNIPPETS_DIR,
                                f'sprite_data_{canonical_cat}.py')

    if not os.path.exists(snippet_path):
        if dry_run:
            log.append(f"    L3 snippet: would create {snippet_path}")
            return
        _bootstrap_snippet(snippet_path, canonical_cat, kind)
        log.append(f"    L3 snippet: created {os.path.basename(snippet_path)}")

    with open(snippet_path, 'r') as f:
        text = f.read()

    if kind == 'named':
        new_text, action = _snippet_add_named(text, canonical_cat, name, pid)
    else:
        new_text, action = _snippet_add_generic(text, canonical_cat, pid)

    if action == 'noop':
        log.append(f"    L3 snippet: {pid} already in "
                   f"sprite_data_{canonical_cat}.py ({kind})")
        return
    if dry_run:
        log.append(f"    L3 snippet: would {action} {pid} in "
                   f"sprite_data_{canonical_cat}.py")
        return
    with open(snippet_path, 'w') as f:
        f.write(new_text)
    log.append(f"    L3 snippet: {action} {pid} in "
               f"sprite_data_{canonical_cat}.py")


def _bootstrap_snippet(path, canonical_cat, kind):
    """Create a fresh sprite_data_<cat>.py for a brand-new category."""
    if kind == 'named':
        body = (f'"""\nSprite map for category: {canonical_cat}\n\n'
                f'Generated/maintained by sprite_package/picks_recent/'
                f'apply_picks.py.\n\nShape: _{canonical_cat.upper()}_MAP '
                f'maps item_name -> [(pid, variant_index), ...].\n"""\n\n'
                f'_{canonical_cat.upper()}_MAP = {{\n}}\n')
    else:
        body = (f'"""\nSprite pool for category: {canonical_cat}\n\n'
                f'Generated/maintained by sprite_package/picks_recent/'
                f'apply_picks.py.\n\nShape: _{canonical_cat.upper()}_POOL '
                f'is a list of pids.\n"""\n\n'
                f'_{canonical_cat.upper()}_POOL = [\n]\n')
    with open(path, 'w') as f:
        f.write(body)


def _snippet_add_named(text, canonical_cat, name, pid):
    """Add `'name': [('pid', 0)]` to _<CAT>_MAP. Returns (new_text, action)."""
    dict_name = f'_{canonical_cat.upper()}_MAP'
    # If the item_name entry exists, replace its single variant.
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
        # If the same pid is already there, no-op.
        if f"('{pid}', 0)" in m.group(0):
            return text, 'noop'
        return text[:m.start()] + new_block + text[m.end():], 'replaced'

    open_m = re.search(rf"^{re.escape(dict_name)}\s*=\s*\{{\s*$",
                       text, re.MULTILINE)
    if not open_m:
        raise RuntimeError(f"Could not find {dict_name} dict in snippet")
    close_m = re.compile(r"^\}\s*$", re.MULTILINE).search(text, open_m.end())
    if not close_m:
        raise RuntimeError(f"Could not find {dict_name} closing brace")
    new_text = text[:close_m.start()] + new_block + text[close_m.start():]
    return new_text, 'inserted'


def _snippet_add_generic(text, canonical_cat, pid):
    """Add pid to _<CAT>_POOL list. Returns (new_text, action)."""
    list_name = f'_{canonical_cat.upper()}_POOL'
    # If pid already in the list, no-op.
    if re.search(rf"'\s*{re.escape(pid)}\s*'", text):
        return text, 'noop'

    open_m = re.search(rf"^{re.escape(list_name)}\s*=\s*\[\s*$",
                       text, re.MULTILINE)
    if not open_m:
        raise RuntimeError(f"Could not find {list_name} list in snippet")
    close_m = re.compile(r"^\]\s*$", re.MULTILINE).search(text, open_m.end())
    if not close_m:
        raise RuntimeError(f"Could not find {list_name} closing brace")
    new_line = f"    '{pid}',  # picked via sprite_package/picks_recent\n"
    return text[:close_m.start()] + new_line + text[close_m.start():], 'inserted'


# -- L4: wizardscavern/sprites/<cat>.py runtime map ------------------------

def update_runtime_sprite_map(pid, name, category, dry_run, log):
    """Update the runtime sprite map under wizardscavern/sprites/."""
    filename, dict_name, shape = _CATEGORY_RUNTIME[category]
    path = os.path.join(_RUNTIME_SPRITES_DIR, filename)

    with open(path, 'r') as f:
        text = f.read()
    if shape == 'simple_dict':
        new_text, action = _apply_simple_dict_pick(text, dict_name, name, pid)
    else:
        new_text, action = _apply_variant_list_pick(text, dict_name, name, pid)

    if action == 'noop':
        log.append(f"    L4 runtime: {category}/{name} already "
                   f"-> {pid} in {filename}")
        return
    if dry_run:
        log.append(f"    L4 runtime: would {action} {category}/{name} -> "
                   f"{pid} in {filename}")
        return
    with open(path, 'w') as f:
        f.write(new_text)
    log.append(f"    L4 runtime: {action} {category}/{name} -> {pid} in {filename}")


def _apply_simple_dict_pick(text, dict_name, name, pid):
    pattern = re.compile(
        r"^(\s+)([\"'])" + re.escape(name) + r"\2:\s+'([A-Z]\d+)',?\s*(?:#.*)?$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if m:
        if m.group(3) == pid:
            return text, 'noop'
        indent = m.group(1)
        quote = m.group(2)
        replacement = f"{indent}{quote}{name}{quote}: {' ' * max(1, 22 - len(name) - 2)}'{pid}',"
        return text[:m.start()] + replacement + text[m.end():], 'replaced'

    open_m = re.search(rf"^{re.escape(dict_name)}\s*=\s*\{{\s*$",
                       text, re.MULTILINE)
    if not open_m:
        raise RuntimeError(f"Could not find {dict_name} dict")
    close_m = re.compile(r"^(\}\s*)$", re.MULTILINE).search(text, open_m.end())
    if not close_m:
        raise RuntimeError(f"Could not find {dict_name} closing brace")
    new_line = f"    '{name}':{' ' * max(1, 22 - len(name) - 2)}'{pid}',\n"
    return text[:close_m.start()] + new_line + text[close_m.start():], 'inserted'


def _apply_variant_list_pick(text, dict_name, name, pid):
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
        if f"('{pid}', 0)" in m.group(0):
            return text, 'noop'
        return text[:m.start()] + new_block + text[m.end():], 'replaced'

    open_m = re.search(rf"^{re.escape(dict_name)}\s*=\s*\{{\s*$",
                       text, re.MULTILINE)
    if not open_m:
        raise RuntimeError(f"Could not find {dict_name} dict")
    close_m = re.compile(r"^\}\s*$", re.MULTILINE).search(text, open_m.end())
    if not close_m:
        raise RuntimeError(f"Could not find {dict_name} closing brace")
    new_text = text[:close_m.start()] + new_block + text[close_m.start():]
    return new_text, 'inserted'


# -- Manifest updates ------------------------------------------------------

def update_manifests(picks_by_cat, assets_dir, dry_run, log):
    """Refresh in_game/manifest.json + reserve/manifest.json totals.
    We re-derive counts from the live directory so we never drift."""
    in_game_manifest = Path(assets_dir) / 'in_game' / 'manifest.json'
    reserve_manifest = Path(assets_dir) / 'reserve' / 'manifest.json'

    for manifest_path, base_dir, key in [
        (in_game_manifest, Path(assets_dir) / 'in_game' / 'by_category', 'in_game'),
        (reserve_manifest, Path(assets_dir) / 'reserve', 'reserve'),
    ]:
        if not manifest_path.exists():
            continue
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        cats = manifest.get('categories', {})
        for cat_dir in base_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            cat_name = cat_dir.name
            count = sum(1 for _ in cat_dir.glob('*.png'))
            if key == 'in_game':
                # Preserve named vs generic shape; we don't know without
                # cross-referencing the library, so just refresh total.
                if cat_name not in cats:
                    cats[cat_name] = {'named': 0, 'generic': 0,
                                      'total': count,
                                      'unique_named_items': 0}
                else:
                    cats[cat_name]['total'] = count
            else:
                cats[cat_name] = count
        manifest['categories'] = cats
        if dry_run:
            log.append(f"    manifest: would refresh {manifest_path.name}")
        else:
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            log.append(f"    manifest: refreshed {manifest_path.name}")


# -- Pool regeneration -----------------------------------------------------

def regenerate_pool(assets_dir, dry_run):
    """Call promote_all_sprites.py to rebuild canonical_pool_full.pkl
    from the now-canonical PNG layout + library + snippet state.

    NOTE: --include-reserve is intentionally NOT passed. The shipped
    pool is in-game only (per CLAUDE.md, ~1283 sprites, ~2.9 MB).
    Reserve sprites stay in the bundle for future picker rounds but
    don't bloat the APK."""
    # Delete the pool first so we regenerate from scratch rather than
    # accumulating stale entries.
    if not dry_run and os.path.exists(_POOL_PATH):
        os.remove(_POOL_PATH)
    cmd = [
        sys.executable, _PROMOTE_SCRIPT,
        '--pool', _POOL_PATH,
        '--package', _PACKAGE_DIR,
        '--in-game-dir', str(Path(assets_dir) / 'in_game'),
        '--reserve-dir', str(Path(assets_dir) / 'reserve'),
    ]
    if dry_run:
        cmd.append('--dry-run')
    print(f"\n== regenerating pool ==")
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("  STDERR:", result.stderr, file=sys.stderr)
        raise RuntimeError(
            f"promote_all_sprites.py failed (exit {result.returncode})")
    # Surface just the summary lines.
    for line in result.stdout.splitlines()[-20:]:
        print(f"  {line}")


# -- Main ------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', default=os.path.join(_HERE, 'recent_picks.json'))
    ap.add_argument('--assets-dir',
                    default=os.path.join(_ROOT, 'assets', 'sprites'),
                    help='Where the sprite-assets-v1 bundle is unpacked.')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--skip-pool', action='store_true',
                    help="Skip the promote_all_sprites.py regeneration step.")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        sys.exit(2)

    assets_dir = Path(args.assets_dir).resolve()
    if not assets_dir.exists() or not (assets_dir / 'in_game').exists():
        print(f"ERROR: assets bundle not found at {assets_dir}/", file=sys.stderr)
        print()
        print("Download + unpack first:", file=sys.stderr)
        print(f"  curl -L -o /tmp/wc_sprites_assets.zip \\", file=sys.stderr)
        print(f"      https://github.com/dachhack/LegendOfZot/releases/"
              f"download/sprite-assets-v1/wc_sprites_assets.zip", file=sys.stderr)
        print(f"  unzip -q /tmp/wc_sprites_assets.zip -d /tmp/unpack", file=sys.stderr)
        print(f"  mkdir -p {assets_dir.parent}", file=sys.stderr)
        print(f"  mv /tmp/unpack/wc_sprites_assets {assets_dir}", file=sys.stderr)
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

    # Per-pick: L1 PNG, L2 library, L3 snippet, L4 runtime.
    for category, entries in sorted(by_cat.items()):
        if category not in _CATEGORY_PIPELINE:
            print(f"WARN: unknown picker category {category!r}, skipping")
            continue
        print(f"\n== {category} ({len(entries)} picks) ==")
        for name, pid in sorted(entries):
            print(f"  {name!r} -> {pid}")
            log = []
            move_png_to_in_game(pid, name, category, str(assets_dir),
                                args.dry_run, log)
            update_library_json(pid, category, args.dry_run, log)
            update_sprite_data_snippet(pid, name, category, args.dry_run, log)
            update_runtime_sprite_map(pid, name, category, args.dry_run, log)
            for line in log:
                print(line)

    update_manifests(by_cat, str(assets_dir), args.dry_run, log=[])

    if not args.skip_pool:
        regenerate_pool(str(assets_dir), args.dry_run)

    return 0


if __name__ == '__main__':
    sys.exit(main())
