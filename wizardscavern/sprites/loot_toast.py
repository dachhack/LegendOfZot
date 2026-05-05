"""
Loot toast popups — small floating banners that appear when the player
finds an item in the dungeon.

Each toast renders as `[icon] You found a Bubbling Potion!` near the
top-right of the screen, fades in, holds for ~3 seconds, then fades
out. Multiple toasts stack vertically so opening a chest with several
items doesn't lose any of them.

State lives on `game_state.loot_toasts` as a list of dicts:
    {'icon': html, 'text': str, 'created_at': float}

Server-side timing: each render filters out toasts older than
_TOAST_LIFETIME and emits a CSS `animation-delay` based on the
remaining toast's age, so the fade animation stays in sync even
though the WebView replaces the toast HTML on every update.
"""

import time

from .identifiables import render_item_icon

_TOAST_LIFETIME = 4.0  # seconds
_TOAST_QUEUE_CAP = 20

_VOWELS = set('aeiouAEIOU')


def _ensure_queue():
    from .. import game_state as _gs
    if not hasattr(_gs, 'loot_toasts') or _gs.loot_toasts is None:
        _gs.loot_toasts = []
    return _gs


def _display_name(item):
    """Best-effort display name — cryptic for unidentified potions /
    scrolls / spells, real name for everything else."""
    try:
        from ..items import get_item_display_name
        return get_item_display_name(item)
    except Exception:
        return getattr(item, 'name', 'something')


def _article(name):
    if not name:
        return 'a'
    first = name.lstrip()[:1]
    return 'an' if first in _VOWELS else 'a'


def notify_loot(item, message=None):
    """Push a toast for an item the player just acquired.

    `message` overrides the default "You found a {name}!" text.
    """
    if item is None:
        return
    gs = _ensure_queue()
    icon_html = render_item_icon(item, size=28)
    if message is None:
        name = _display_name(item)
        message = f"You found {_article(name)} {name}!"
    gs.loot_toasts.append({
        'icon': icon_html,
        'text': message,
        'created_at': time.time(),
    })
    # Cap queue size so a misbehaving caller can't blow up memory.
    if len(gs.loot_toasts) > _TOAST_QUEUE_CAP:
        gs.loot_toasts = gs.loot_toasts[-_TOAST_QUEUE_CAP:]


def render_loot_toasts_html():
    """Return the toast container HTML, or '' if no live toasts.

    Drops expired entries from gs.loot_toasts as a side effect.
    """
    from .. import game_state as _gs
    queue = getattr(_gs, 'loot_toasts', None)
    if not queue:
        return ''
    now = time.time()
    live = [t for t in queue if (now - t['created_at']) < _TOAST_LIFETIME]
    _gs.loot_toasts = live
    if not live:
        return ''
    items_html = []
    for t in live:
        age = max(0.0, now - t['created_at'])
        items_html.append(
            f'<div class="loot-toast" style="animation-delay:-{age:.2f}s;">'
            f'{t["icon"]}'
            f'<span class="loot-toast-text">{t["text"]}</span>'
            f'</div>'
        )
    return '<div id="loot-toasts">' + ''.join(items_html) + '</div>'
