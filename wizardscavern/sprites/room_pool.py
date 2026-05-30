"""
Room-sprite pool index — builds (room_code, variant_index) -> pid lookups
from the canonical pool's room entries, lazily on first call.

The pool already pre-renders all 81 named room sprites (24 base codes +
8 variant keys × ~3 variants each), so the renderer can fetch image
bytes directly without runtime PIL slicing.
"""

from .pool import _load_pool

_base_pids = None
_variant_pids = None


def _build():
    global _base_pids, _variant_pids
    if _base_pids is not None:
        return
    base = {}
    variant = {}
    for pid, entry in _load_pool().items():
        if entry.get('cat') != 'rooms':
            continue
        if not pid.startswith('RM'):
            continue  # skip reserve
        gd = entry.get('game_data', {})
        key = gd.get('item_name')
        vi = gd.get('variant_index', 0)
        kind = gd.get('slot_kind')
        if not key:
            continue
        target = base if kind == 'base' else variant
        target.setdefault(key, []).append((vi, pid))
    # Sort each list by variant_index, store just the pids.
    _base_pids = {k: [pid for _vi, pid in sorted(v)] for k, v in base.items()}
    _variant_pids = {k: [pid for _vi, pid in sorted(v)] for k, v in variant.items()}


def get_room_pids(room_code):
    """Return the list of named-room pids for a base room code, or []."""
    _build()
    return _base_pids.get(room_code, [])


def get_variant_pids(variant_key):
    """Return the list of pids for a variant key (e.g. 'legendary'), or []."""
    _build()
    return _variant_pids.get(variant_key, [])
