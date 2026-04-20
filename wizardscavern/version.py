"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 92
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "FIX: Use filter now renders! NameError on player_character crashed render",
    "FIX: Name-entry input field visible again (width=0 regression)",
    "FIX: Use/Equip/Eat buttons are double-fire safe (no more phantom cancels)",
    "FIX: Use filter now actually uses Curing Kits (render/handler were out of sync)",
    "Input box: compact by default, right-aligned; full-width only for name entry",
    "Bottom panel: ~12px shorter, more room for inventory/message view",
    "Healing potions: drink one, or tap Heal to drink-to-full (opt-in bulk)",
    "Number pad: added 0 key, centered at bottom",
    "Equip/Use stay in filter mode so you can act on more items without backing out",
    "Keyboard: centered rows, shift highlights when active, smaller shift key",
    "Combat dice scaled up 1.3x for readability, anchored to panel right edge",
]
