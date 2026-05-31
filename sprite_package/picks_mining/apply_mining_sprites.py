"""Apply mining-item sprite picks from the reserve.

Pipeline for the dwarf-mining ore ingredients + Ioun Stones:
  1. Read mining_sprite_picks.json  {item_name: reserve_id}  (from the picker).
  2. For each pick, load the reserve PNG, chroma-key its dark background to
     TRANSPARENT (border-median key + edge despill, via chroma_key.py).
  3. Promote the keyed sprite into canonical_pool_full.pkl as a webp with
     status="reserve" and the reserve id as its pid.
  4. Rewrite the (pid, 0) tuple for that item in sprites/ingredients.py or
     sprites/accessories.py so the game renders the new sprite.

Usage:
    python3 sprite_package/picks_mining/apply_mining_sprites.py \
        --picks /tmp/mining_sprite_picks.json \
        --reserve-dir /tmp/wc_reserve/wc_sprites_assets/reserve \
        --pool wizardscavern/data/canonical_pool_full.pkl
    # add --dry-run to preview without writing
"""
import argparse, base64, io, glob, os, pickle, re, sys
from pathlib import Path
from PIL import Image
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / 'code'))
import chroma_key as ck

ORE_ITEMS = {'Iron Chunk','Copper Nugget','Stone Shard','Silver Vein','Gold Flake',
             'Coal Ember','Mithril Shard','Ruby Fragment','Diamond Chip','Adamantine Dust'}
IOUN_ITEMS = {'Ioun Stone of Fortitude','Ioun Stone of Might',
              'Ioun Stone of Agility','Ioun Stone of Mastery'}

def border_median_key(im):
    rgb = im.convert('RGB'); w,h = rgb.size; px = rgb.load()
    ring = []
    for x in range(w): ring += [px[x,0], px[x,h-1]]
    for y in range(h): ring += [px[0,y], px[w-1,y]]
    ring.sort()
    return ring[len(ring)//2]

def key_to_rgba(path):
    im = Image.open(path).convert('RGBA')
    key = border_median_key(im)
    return ck.chroma_key(im, key, inner=60, outer=130, despill=True)

def find_png(reserve_dir, res_id):
    for cat in ('treasures','ingredients','accessories','runes','shards','foods','spells','weapons'):
        hits = glob.glob(os.path.join(reserve_dir, cat, f'{res_id}*.png'))
        if hits: return hits[0], cat
    return None, None

def patch_map(map_path, item, new_pid):
    src = Path(map_path).read_text()
    # match  'Item': [ \n  ('OLD', N),  -> replace OLD with new_pid
    pat = re.compile(r"(\['\"]?" + re.escape(item) + r"['\"]\s*:\s*\[\s*\n\s*\(')[A-Za-z0-9_]+(',\s*\d+\))")
    pat = re.compile(r"(['\"]" + re.escape(item) + r"['\"]\s*:\s*\[\s*\n\s*\(')[A-Za-z0-9_]+(',\s*\d+\))")
    new, n = pat.subn(rf"\g<1>{new_pid}\g<2>", src, count=1)
    if n != 1:
        return False
    Path(map_path).write_text(new)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--picks', required=True)
    ap.add_argument('--reserve-dir', required=True)
    ap.add_argument('--pool', default='wizardscavern/data/canonical_pool_full.pkl')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    import json
    picks = json.load(open(a.picks))
    pool = pickle.load(open(a.pool,'rb'))
    ing_map = _HERE.parent.parent / 'wizardscavern' / 'sprites' / 'ingredients.py'
    acc_map = _HERE.parent.parent / 'wizardscavern' / 'sprites' / 'accessories.py'
    changed = 0
    for item, res_id in picks.items():
        if not res_id: continue
        png, cat = find_png(a.reserve_dir, res_id)
        if not png:
            print(f"  !! {item}: reserve {res_id} not found"); continue
        keyed = key_to_rgba(png)
        buf = io.BytesIO(); keyed.save(buf,'WEBP',quality=92,lossless=False)
        b64 = base64.b64encode(buf.getvalue()).decode()
        pid = res_id  # e.g. CR0144_CR2 -- unique, no collision with in-game pids
        target_cat = 'accessories' if item in IOUN_ITEMS else 'ingredients'
        pool[pid] = {'pid': pid, 'cat': target_cat, 'img_b64': b64, 'sheet': None,
                     'src_label': f'reserve:{res_id}',
                     'game_data': {'item_name': item, 'category': target_cat, 'variant_index': 0},
                     'status': 'reserve'}
        mp = acc_map if item in IOUN_ITEMS else ing_map
        ok = '(dry)' if a.dry_run else ('patched' if patch_map(mp, item, pid) else 'MAP-MISS')
        print(f"  {item:26s} <- {res_id:18s} [{cat}] keyed+promoted, map:{ok}")
        changed += 1
    if a.dry_run:
        print(f"DRY RUN: {changed} picks would be applied (no files written)")
        return
    pickle.dump(pool, open(a.pool,'wb'))
    print(f"Wrote {changed} sprites into pool ({a.pool}) + patched maps.")

if __name__ == '__main__':
    main()
