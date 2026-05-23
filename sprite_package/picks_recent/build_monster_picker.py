"""
Build a mobile-first HTML picker for the b420 deep-dungeon monsters.

Scope: the 30 new tier-11..15 monsters added in the monster-generation
overhaul. Each currently has a single auto-assigned reserve sprite; this
picker lets you confirm it or swap it for any of the ~1,428 reserve
monster sprites in the sprite-assets-v1 bundle. If nothing in the reserve
fits a monster, leave it unpicked (Clear) -- that's the signal that it
needs bespoke art commissioned.

Reuses the picker UI/template from build_picker.py (same swipe/tap/Save
flow). Candidates come from the unpacked reserve dir.

Run (after unpacking the bundle into assets/sprites/, as CLAUDE.md describes):
    python3 sprite_package/picks_recent/build_monster_picker.py
        [--reserve-dir assets/sprites/reserve]

Writes:
    sprite_package/picks_recent/picker_monsters.html

Open it, page through the 30 monsters, tap a candidate to pick, hit
"Save All" to download recent_picks.json (keys are `monsters::<Name>`),
then run apply_picks.py to write the swaps back into the sprite maps and
regenerate the pool.
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

from build_picker import TEMPLATE, load_reserve_sprites  # noqa: E402
from wizardscavern.sprites import get_image_b64  # noqa: E402
from wizardscavern.sprites.monsters import _MONSTERS_MAP  # noqa: E402
from wizardscavern.game_data import (  # noqa: E402
    MONSTER_TEMPLATES, MONSTER_SPAWN_FLOOR_RANGE,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reserve-dir', default=os.path.join(_ROOT, 'assets/sprites/reserve'),
                    help='Path to the unpacked reserve sprite dir '
                         '(expects a monsters/ subdir).')
    args = ap.parse_args()

    print(f"Loading reserve monster sprites from {args.reserve_dir}/monsters ...")
    reserve = load_reserve_sprites(args.reserve_dir, 'monsters')
    print(f"  monsters reserve candidates: {len(reserve)}")
    if not reserve:
        print("ERROR: no reserve monster sprites found. Unpack the "
              "sprite-assets-v1 bundle into assets/sprites/ first "
              "(see CLAUDE.md / sprite_package/fetch_assets.py).",
              file=sys.stderr)
        sys.exit(1)

    # The 30 new deep-dungeon monsters are template levels 11-15.
    new_monsters = [m for m in MONSTER_TEMPLATES if m.get('level', 0) >= 11]
    new_monsters.sort(key=lambda m: (m['level'], m['name']))

    items = []
    for m in new_monsters:
        name = m['name']
        lvl = m['level']
        lo, hi = MONSTER_SPAWN_FLOOR_RANGE.get(lvl, (0, 49))
        variants = _MONSTERS_MAP.get(name) or []
        current = variants[0][0] if variants else ''
        weak = ', '.join(m.get('elemental_weakness', [])) or 'none'
        strong = ', '.join(m.get('elemental_strength', [])) or 'none'
        items.append({
            'category': 'monsters',
            'name': name,
            'kind': 'auto',  # auto-assigned reserve sprite -- confirm or swap
            'note': m.get('flavor_text', ''),
            'description': (f"Tier {lvl} · floors {lo}-{hi} · "
                            f"{m['health']} HP / {m['attack']} ATK / "
                            f"{m['defense']} DEF · hits {m.get('attack_element','Physical')}"),
            'meta': f"T{lvl} F{lo}-{hi} · weak: {weak} · strong: {strong}",
            'current': current,
            'current_img': get_image_b64(current) if current else '',
        })

    candidates = {
        'monsters': {'reserve': reserve, 'chosen': []},
    }

    # Seed any existing picks (so re-opening keeps your work).
    picks_path = os.path.join(_HERE, 'recent_picks.json')
    existing = {}
    if os.path.exists(picks_path):
        try:
            with open(picks_path) as f:
                existing = json.load(f).get('picks', {})
        except Exception:
            existing = {}
    for it in items:
        it['picked'] = existing.get(f"{it['category']}::{it['name']}", '')

    embedded = json.dumps({'items': items, 'candidates': candidates})
    html = TEMPLATE.replace('__DATA__', embedded)
    out_path = os.path.join(_HERE, 'picker_monsters.html')
    with open(out_path, 'w') as f:
        f.write(html)
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\nWrote {out_path}")
    print(f"  items={len(items)} monsters")
    print(f"  candidates={len(reserve)} reserve monster sprites")
    print(f"  size={size_mb:.2f} MB")


if __name__ == '__main__':
    main()
