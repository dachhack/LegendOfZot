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

This module also exposes get_named_item_pid(item) — a generic
dispatcher that picks the right sprite for any non-cryptic item type
(weapons, armor, accessories, treasures, trophies, runes, shards,
foods, ingredients, lanterns, towels, bug armors). Each named map
shipped with the round-8 package may have multiple variants per item
name; we pick a deterministic variant by hashing item.name.
"""

from .pool import _stable_seed, get_image_b64
from . import potions as _potions
from . import scrolls as _scrolls
from . import spells as _spells
from . import weapons as _weapons
from . import armors as _armors
from . import accessories as _accessories
from . import bug_armors as _bug_armors
from . import foods as _foods
from . import ingredients as _ingredients
from . import lanterns as _lanterns
from . import runes as _runes
from . import shards as _shards
from . import towels as _towels
from . import treasures as _treasures
from . import trophies as _trophies


_POOLS = {
    'potions': _potions._POTIONS_POOL,
    'scrolls': _scrolls._SCROLLS_POOL,
    'spells':  _spells._SPELLS_POOL,
}

# All spells share a single placeholder icon (a scroll sprite). The user's
# spec: "Spells should just be question marks (you can use the scroll ? icon)."
# We pick a deterministic scroll pid and reuse it for every spell, identified
# or not — spells are abstract knowledge, no need for per-spell visual.
_SPELL_PLACEHOLDER_PID = (
    _scrolls._SCROLLS_POOL[0] if _scrolls._SCROLLS_POOL else None
)


def get_cryptic_sprite_pid(item, category):
    """Return the round-8 pid for a potion / scroll / spell.

    For 'spells' specifically, returns the shared placeholder scroll pid
    (every spell uses the same icon). For potions and scrolls, looks up
    the per-game cryptic appearance from
    `game_state.item_cryptic_mapping[category]` and hashes it into the
    matching pool. Falls back to item.name when no cryptic mapping is set.
    """
    if category == 'spells':
        return _SPELL_PLACEHOLDER_PID
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


def get_per_spell_sprite_pid(spell):
    """Return the unique round-8 pid for a specific spell (NOT the shared
    `?` placeholder used in inventory).

    Used for cast-time animations where each spell should look distinct so
    the player can learn the icon-to-spell association by sight.
    """
    pool = _POOLS.get('spells')
    if not pool:
        return None
    try:
        from .. import game_state as _gs
        mapping = _gs.item_cryptic_mapping.get('spells', {}) if _gs.item_cryptic_mapping else {}
    except Exception:
        mapping = {}
    name = getattr(spell, 'name', '') or ''
    cryptic = mapping.get(name, name)
    if not cryptic:
        return None
    return pool[_stable_seed(cryptic) % len(pool)]


def _pick_named(cat_map, key):
    """Pick a deterministic (pid, variant_index) for a named item.

    Returns the pid, or None if the key isn't in the map.
    """
    if not cat_map or not key:
        return None
    variants = cat_map.get(key)
    if not variants:
        return None
    pid, _vi = variants[_stable_seed(key) % len(variants)]
    return pid


def get_named_item_pid(item):
    """Pick a sprite pid for any non-cryptic item type.

    Dispatches on the item class name. Returns None for item types that
    have no round-8 sprite map yet (e.g. Flare, CookingKit, CuringKit).
    """
    cls = type(item).__name__
    name = getattr(item, 'name', '') or ''

    if cls == 'Weapon':
        return _pick_named(_weapons._WEAPONS_MAP, name)

    if cls == 'Armor':
        # Bug armors first since they're a subset of Armor but get their
        # own map (Chitin Shell, Silk Weave, ...).
        bug = _pick_named(_bug_armors._BUG_ARMORS_MAP, name)
        if bug:
            return bug
        return _pick_named(_armors._ARMORS_MAP, name)

    if cls == 'Treasure':
        # Wearable accessories (rings, amulets, circlets, bracers, ...) live
        # in the accessories map; everything else lands in treasures.
        if getattr(item, 'treasure_type', '') == 'passive':
            acc = _pick_named(_accessories._ACCESSORIES_MAP, name)
            if acc:
                return acc
        return _pick_named(_treasures._TREASURES_MAP, name)

    if cls == 'Trophy':
        return _pick_named(_trophies._TROPHIES_MAP, name)

    if cls == 'Rune':
        # Map keys are bare types ('Battle', 'Devotion', ...) but item
        # names are 'Rune of Battle' etc. Strip the prefix.
        key = name[len('Rune of '):] if name.startswith('Rune of ') else name
        return _pick_named(_runes._RUNES_MAP, key)

    if cls == 'Shard':
        key = name[len('Shard of '):] if name.startswith('Shard of ') else name
        return _pick_named(_shards._SHARDS_MAP, key)

    if cls == 'Towel':
        return _pick_named(_towels._TOWELS_MAP, name)

    if cls in ('Lantern', 'LanternFuel'):
        return _pick_named(_lanterns._LANTERNS_MAP, name)

    if cls == 'Ingredient':
        return _pick_named(_ingredients._INGREDIENTS_MAP, name)

    if cls in ('Food', 'LembasWafer', 'Sausage'):
        return _pick_named(_foods._FOODS_MAP, name)

    if cls == 'Meat':
        # Meat names are dynamic ("Raw Goblin Burger"); the food map keys
        # them by cut ("burger", "filet", ...). Use the stored cut
        # attribute when available, else parse the last word of the name.
        cut = getattr(item, 'cut', None)
        if not cut:
            parts = name.split()
            cut = (parts[-1] if parts else '').lower()
        return _pick_named(_foods._FOODS_MAP, (cut or '').lower())

    if cls == 'CookingKit':
        return _pick_named(_foods._FOODS_MAP, 'Cooking Kit')

    if cls == 'CuringKit':
        return _pick_named(_foods._FOODS_MAP, 'Curing Kit')

    return None


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


def render_item_icon(item, size=24, for_vendor=False):
    """One-call helper for format_item_for_display: pick the right pid
    for the item (cryptic for potions/scrolls/spells, named map for
    everything else) and return the inline canvas HTML.

    ``for_vendor=True`` reveals the real per-spell sprite for spell
    rows in vendor wares -- vendors know what they're selling, so the
    spell book icon should match the actual spell.

    Spells in the player's inventory show the real per-spell sprite
    once identified, else fall back to the generic scroll/book icon.

    Returns '' if no sprite is mapped for this item type.
    """
    cls = type(item).__name__
    if cls == 'Potion':
        return render_inline_item_sprite(get_cryptic_sprite_pid(item, 'potions'), size=size)
    if cls == 'Scroll':
        return render_inline_item_sprite(get_cryptic_sprite_pid(item, 'scrolls'), size=size)
    if cls == 'Spell':
        # Per-spell sprite when the vendor is showing it OR the player
        # has already identified this spell type; otherwise the generic
        # scroll/book placeholder.
        try:
            from ..items import is_item_identified as _is_id
            identified = _is_id(item)
        except Exception:
            identified = False
        if for_vendor or identified:
            pid = get_per_spell_sprite_pid(item)
            if pid:
                return render_inline_item_sprite(pid, size=size)
        return render_inline_item_sprite(get_cryptic_sprite_pid(item, 'spells'), size=size)
    return render_inline_item_sprite(get_named_item_pid(item), size=size)

