"""
Sprite map for category: bug_weapons

Mirrors the bug_armors module pattern. Bug weapons are the 5 weapons
that drop on the shrinking-bug level (Stinger Blade, Mandible Axe,
Thorax Spear, Firefly Wand, Scorpion Tail Whip). Without this map they
fall through to the regular _WEAPONS_POOL and look identical to
generic dungeon swords.

Shape: _BUG_WEAPONS_MAP maps an item_name -> list of (pid, variant_index)
tuples. The dispatcher in sprites/identifiables.py checks this map
BEFORE _WEAPONS_MAP so a bug-weapon name resolves to its insectoid
sprite even though the underlying Weapon class is shared.
"""

_BUG_WEAPONS_MAP = {
}
