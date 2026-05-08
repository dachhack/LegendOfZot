"""One-off audit: render the _SPELLS_NAMED mapping as an HTML page so a
human can eyeball every spell name -> sprite pairing.

Usage:
    python3 scripts/audit_spell_sprites.py [--out /tmp/spell_audit.html]
"""

import argparse
import html
import json
import pickle
from pathlib import Path

from wizardscavern.sprites import spells as _spells

ROOT = Path(__file__).resolve().parent.parent
POOL_PATH = ROOT / 'wizardscavern' / 'data' / 'canonical_pool_full.pkl'
LIBRARY_PATH = ROOT / 'sprite_package' / 'libraries' / 'spells_library.json'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'docs' / 'spell_sprite_audit.html'))
    args = ap.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    with open(POOL_PATH, 'rb') as f:
        pool = pickle.load(f)
    with open(LIBRARY_PATH) as f:
        library = json.load(f)
    pid_to_drawn_name = {
        e['pid']: (e.get('game_data') or {}).get('spell_name', '?')
        for e in library.get('chosen', [])
    }

    rows = []
    sorted_named = sorted(_spells._SPELLS_NAMED.items(), key=lambda kv: kv[0].lower())
    for name, pid in sorted_named:
        entry = pool.get(pid) or {}
        img_b64 = entry.get('img_b64', '')
        original_spell = pid_to_drawn_name.get(pid, '?')
        match = name == original_spell
        flag = '' if match else ' <span class="warn">[!= drawn for: '
        flag += '' if match else html.escape(str(original_spell)) + ']</span>'
        rows.append(
            f'<div class="row {"ok" if match else "warn-row"}">'
            f'<img src="data:image/webp;base64,{img_b64}" />'
            f'<div class="meta">'
            f'<div class="name">{html.escape(name)}</div>'
            f'<div class="pid">{html.escape(pid)}{flag}</div>'
            f'</div></div>'
        )

    used_pids = set(_spells._SPELLS_NAMED.values())
    unused_pids = [p for p in _spells._SPELLS_POOL if p not in used_pids]
    unused_html = ''
    if unused_pids:
        cards = []
        for pid in unused_pids:
            entry = pool.get(pid) or {}
            img_b64 = entry.get('img_b64', '')
            drawn_for = pid_to_drawn_name.get(pid, '?')
            cards.append(
                f'<div class="row ok">'
                f'<img src="data:image/webp;base64,{img_b64}" />'
                f'<div class="meta">'
                f'<div class="name">{html.escape(str(drawn_for))}</div>'
                f'<div class="pid">{html.escape(pid)} (in pool, no in-game spell)</div>'
                f'</div></div>'
            )
        unused_html = (
            '<h2>Pool sprites with no in-game spell using them</h2>'
            f'<div class="grid">{"".join(cards)}</div>'
        )

    out = (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<title>Spell Sprite Audit</title>'
        '<style>'
        'body{background:#1a1a1a;color:#ddd;font-family:monospace;padding:16px;}'
        'h1,h2{color:#FFD700;}'
        '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;}'
        '.row{display:flex;align-items:center;gap:10px;padding:8px;border:1px solid #333;border-radius:4px;background:#222;}'
        '.row img{width:64px;height:64px;image-rendering:pixelated;background:#111;border-radius:3px;}'
        '.meta{flex:1;}'
        '.name{font-weight:bold;color:#FFF;font-size:14px;}'
        '.pid{color:#888;font-size:11px;margin-top:3px;}'
        '.warn{color:#F44336;}'
        '.warn-row{border-color:#F44336;}'
        f'.summary{{color:#4CAF50;margin-bottom:12px;}}'
        '</style></head><body>'
        f'<h1>Spell Sprite Audit ({len(sorted_named)} spells)</h1>'
        f'<div class="summary">All entries flagged green match their original drawn-for spell. '
        f'Red entries [!=] mean the in-game name was matched to a sprite drawn for a different spell.</div>'
        f'<div class="grid">{"".join(rows)}</div>'
        f'{unused_html}'
        '</body></html>'
    )

    Path(args.out).write_text(out)
    print(f'Wrote {args.out}')
    mismatches = [n for n, p in sorted_named if pid_to_drawn_name.get(p) != n]
    print(f'{len(sorted_named)} spells mapped, {len(mismatches)} mismatched, '
          f'{len(unused_pids)} unused pool pids')
    for n in mismatches:
        p = _spells._SPELLS_NAMED[n]
        print(f'  MISMATCH: in-game name {n!r} -> {p} (drawn for {pid_to_drawn_name.get(p)!r})')


if __name__ == '__main__':
    main()
