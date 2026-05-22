"""
Apply the JSON output of picker.html back into the per-category sprite
maps under wizardscavern/sprites/.

Run:
    python3 sprite_package/picks_recent/apply_picks.py
        [--input recent_picks.json]
        [--dry-run]

Default input is sprite_package/picks_recent/recent_picks.json (drop the
file the picker downloaded next to this script). With --dry-run the
script prints the planned edits without touching files.

Edit shape per category:
  spells       -> updates _SPELLS_NAMED (single-pid dict)
  accessories  -> replaces _ACCESSORIES_MAP entry with [(pid, 0)]
                  (single variant; add more by hand if you want a pool)
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_SPRITES_DIR = os.path.join(_ROOT, 'wizardscavern', 'sprites')


def _spells_path():
    return os.path.join(_SPRITES_DIR, 'spells.py')


def _accessories_path():
    return os.path.join(_SPRITES_DIR, 'accessories.py')


def apply_spell_pick(text, name, pid):
    """Find `'Name': 'OLDPID',` in _SPELLS_NAMED and rewrite the PID.
    Returns (new_text, action) where action is 'replaced'/'inserted'/'noop'.
    """
    # Existing entry: 'Name': 'PID', or "Name": 'PID',
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

    # New entry -- insert before the closing brace of _SPELLS_NAMED.
    # The map ends with a single `}` on its own line after the last entry.
    closing = re.compile(r"^(\}\s*)$", re.MULTILINE)
    # Find the close that belongs to _SPELLS_NAMED. The dict opens with
    # `_SPELLS_NAMED = {`; we take the FIRST `^}` after that point.
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
    with a single-variant `[('PID', 0)]`. Inserts a new block before the
    closing brace if the entry doesn't exist yet."""
    # Multi-line entry block:
    #   "Name": [
    #       ('AC...', 0),  # ...
    #       ...
    #   ],
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

    # Insert before _ACCESSORIES_MAP closing brace.
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
    ap.add_argument('--input', default=os.path.join(_HERE, 'recent_picks.json'),
                    help='Picks JSON file (default: recent_picks.json next '
                         'to this script).')
    ap.add_argument('--dry-run', action='store_true',
                    help="Don't write anything; just print planned edits.")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        print("Download recent_picks.json from picker.html first.", file=sys.stderr)
        sys.exit(2)

    with open(args.input, 'r') as f:
        data = json.load(f)
    picks = data.get('picks', {})
    if not picks:
        print("No picks in input -- nothing to apply.")
        return 0

    # Group picks by sprite-map file.
    by_file = {}
    for key, pid in picks.items():
        category, _, name = key.partition('::')
        by_file.setdefault(category, []).append((name, pid))

    for category, entries in sorted(by_file.items()):
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
