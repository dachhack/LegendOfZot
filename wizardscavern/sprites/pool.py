"""
Canonical sprite pool loader + helpers.

The pool is a pickle of {pid: {'cat', 'status', 'img_b64', 'pid', ...}} with
5,251 entries. It's loaded lazily on first lookup so importing this module
is cheap.

Variant selection is deterministic: same (item, seed) always returns the
same sprite, so a given monster instance keeps its appearance across
re-renders, but different instances of the same monster type spread across
the available variants.
"""

import os
import pickle
import zlib

_POOL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data',
                          'canonical_pool_full.pkl')

_pool_cache = None


def _load_pool():
    global _pool_cache
    if _pool_cache is None:
        path = os.path.abspath(_POOL_PATH)
        with open(path, 'rb') as f:
            _pool_cache = pickle.load(f)
    return _pool_cache


def pool_size():
    """Return the total number of sprites in the loaded pool."""
    return len(_load_pool())


def get_pool_entry(pid):
    """Return the full pool entry for a pid, or None."""
    return _load_pool().get(pid)


def get_image_b64(pid):
    """Return the base64-encoded webp image bytes for a pid, or '' if missing."""
    entry = _load_pool().get(pid)
    if entry is None:
        return ''
    return entry.get('img_b64', '')


def _stable_seed(seed):
    """Hash an arbitrary seed to a stable non-negative int across processes."""
    if isinstance(seed, int):
        return seed
    return zlib.crc32(repr(seed).encode('utf-8'))


def render_sprite_canvas(safe_id, size, img_uri, canvas_css,
                         onload_extra='', wrap_id=None, wrap_style=''):
    """Build the shared <canvas> + image-loader <script> for a pre-rendered sprite.

    Every sprite render path (monster / room / player / inline item icon) draws
    a pool webp into a pixelated 2D canvas with the same boilerplate; only these
    differ:

      safe_id       DOM id for the canvas.
      size          square px (used for both the attributes and drawImage).
      img_uri       data: URI of the webp.
      canvas_css    style payload appended after the shared image-rendering rules.
      onload_extra  extra JS run inside img.onload after drawImage (e.g. the
                    monster loom/flourish effects); '' for the simple paths.
      wrap_id       if set, the canvas+script are wrapped in a positioned <div>
                    with this id + '_wrap' (monster/player need this so overlays
                    can escape the canvas); None leaves them bare (room/item).
      wrap_style    extra CSS for the wrapper div.
    """
    inner = (
        f'<canvas id="{safe_id}" width="{size}" height="{size}" '
        f'style="image-rendering:pixelated;image-rendering:crisp-edges;'
        f'{canvas_css}"></canvas>'
        f'<script>(function(){{'
        f'var c=document.getElementById("{safe_id}");if(!c)return;'
        f'var ctx=c.getContext("2d");ctx.imageSmoothingEnabled=false;'
        f'var img=new Image();'
        f'img.onload=function(){{ctx.drawImage(img,0,0,img.naturalWidth,img.naturalHeight,0,0,{size},{size});{onload_extra}}};'
        f'img.src="{img_uri}";'
        f'}})()</script>'
    )
    if wrap_id is None:
        return inner
    return (
        f'<div id="{wrap_id}_wrap" style="{wrap_style}">'
        + inner +
        '</div>'
    )


def get_named_variant(cat_map, item_name, seed):
    """Pick a deterministic (pid, variant_index) for a named item.

    cat_map: dict like _WEAPONS_MAP, _MONSTERS_MAP, etc.
    item_name: the game's item name (string).
    seed: any hashable representing the game-instance identity.

    Returns (pid, variant_index) or None if item_name not in cat_map.
    """
    variants = cat_map.get(item_name)
    if not variants:
        return None
    if len(variants) == 1:
        return variants[0]
    return variants[_stable_seed(seed) % len(variants)]


def get_generic_variant(cat_pool, seed):
    """Pick a deterministic pid from a generic (no-item-name) pool.

    cat_pool: list like _CHARACTERS_POOL, _POTIONS_POOL, etc.
    seed: any hashable.

    Returns a pid (string) or None if pool empty.
    """
    if not cat_pool:
        return None
    if len(cat_pool) == 1:
        return cat_pool[0]
    return cat_pool[_stable_seed(seed) % len(cat_pool)]
