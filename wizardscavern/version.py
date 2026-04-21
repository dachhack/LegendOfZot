"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 109
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "FIX: Quit actually quits now — Android finishAndRemoveTask + os._exit fallback",
    "Main-menu Delete: nuke saves from the launch screen (two-tap gated, same as in-game)",
    "Save cards show \"3h ago\" / \"2d ago\" relative times instead of raw dates",
    "NPC rooms go tap-first: Oracle, Blacksmith, Shrine, Dungeon all use action cards",
    "FIX: Dungeon rummage hint said 'l' — should have been 'r' (actual command)",
    "Save & Quit button in inventory: writes to your most-recent slot then asks y/n",
    "Delete save affordance: red Delete button on each populated slot, two-tap gated",
    "Tappable save slots! Main menu + save/load menu become fat card buttons",
]
