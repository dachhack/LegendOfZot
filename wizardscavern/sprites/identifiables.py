"""
Cryptic-name keyed sprite picks for identifiable items.

Potions, scrolls, and spells in the game use a per-game shuffled "cryptic
name" (e.g. "Bubbling Potion", "Scroll labeled ZELGO MER", "Arcane Glyph")
stored in `gs.item_cryptic_mapping`. The same cryptic name is shown to
the player both before and after identification — only the meaning of
the name changes when the item is identified.

Mapping each cryptic name to a sprite via stable hash means:
  - Same item type within a game = same sprite (identification keeps
    the appearance fixed, just reveals the function).
  - Different game = different cryptic shuffle = different sprite.
  - Player can rely on visual recognition once they've identified one.

If an item has no cryptic mapping (e.g. crafted items, special drops)
we fall back to its real name. That gives a stable sprite per name
across identifications, just one without the per-game shuffle.
"""

from .pool import _stable_seed, get_image_b64
from . import potions as _potions
from . import scrolls as _scrolls
from . import spells as _spells


_POOLS = {
    'potions': _potions._POTIONS_POOL,
    'scrolls': _scrolls._SCROLLS_POOL,
    'spells':  _spells._SPELLS_POOL,
}


def get_cryptic_sprite_pid(item, category):
    """Return the round-8 pid for a potion / scroll / spell.

    Looks up the per-game cryptic appearance from
    `game_state.item_cryptic_mapping[category]` and hashes it into the
    matching pool. If no cryptic mapping exists yet, falls back to the
    item's real name (still deterministic, just not shuffled per game).
    Returns None if the pool is empty or the item has no usable name.
    """
    pool = _POOLS.get(category)
    if not pool:
        return None
    try:
        from .. import game_state as _gs
        mapping = _gs.item_cryptic_mapping.get(category, {}) if _gs.item_cryptic_mapping else {}
    except Exception:
        mapping = {}
    name = getattr(item, 'name', '') or ''
    cryptic = mapping.get(name, name)
    if not cryptic:
        return None
    return pool[_stable_seed(cryptic) % len(pool)]


_render_seq = [0]


def render_inline_item_sprite(pid, size=24):
    """Tiny canvas + draw script for an inline item icon.

    Designed for use inside `format_item_for_display`. Each call gets a
    unique DOM id so the same pid can render twice on one page without
    JS clashes.
    """
    if not pid:
        return ''
    img_b64 = get_image_b64(pid)
    if not img_b64:
        return ''
    _render_seq[0] += 1
    safe_id = f'isp_{_render_seq[0]}'
    img_uri = f'data:image/webp;base64,{img_b64}'
    return (
        f'<canvas id="{safe_id}" width="{size}" height="{size}" '
        f'style="image-rendering:pixelated;image-rendering:crisp-edges;'
        f'vertical-align:middle;display:inline-block;margin-right:4px;"></canvas>'
        f'<script>(function(){{'
        f'var c=document.getElementById("{safe_id}");if(!c)return;'
        f'var ctx=c.getContext("2d");ctx.imageSmoothingEnabled=false;'
        f'var img=new Image();'
        f'img.onload=function(){{ctx.drawImage(img,0,0,img.naturalWidth,img.naturalHeight,0,0,{size},{size});}};'
        f'img.src="{img_uri}";'
        f'}})()</script>'
    )
