"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 133
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "Pick your portrait! New character creation step shows all 73 avatars in a tappable grid",
    "Player avatar now picks from 73 round-8 character sprites — each new character gets a unique stable look",
    "Each monster instance now picks its own sprite variant — same Goblin always looks the same, different Goblins vary",
    "Each room instance now picks its own variant — same Chest looks the same when you come back, but different Chests vary",
    "Rooms now render from the round-8 sprite pool — 27 slots x 3 variants each",
    "FIX: tomb-spawned undead now use the new sprites (UNDEAD SKELETON, DEATH KNIGHT, etc.)",
    "Reverted prior sprite work — fresh approach coming",
    "FIX: Character creation (race + gender) now has tappable choice cards",
    "FIX: Character Stats screen has a tappable Back to Inventory card",
    "FIX: Splash + Death screens have tappable Continue / Close cards",
    "Numpad retired from tap-first modes — only Teleporter shows it now",
    "Input field + SEND hidden in tap modes — ~32px more screen for the game",
    "Internal: MODES refactor — dispatch tables replace prompt_cntl elif trees",
    "Towel: Wipe Face / Wipe Hands grey out when not blind or slippery",
]
