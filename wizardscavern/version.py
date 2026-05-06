"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 147
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "FIX: name-entry screen — toga input row + duplicate ⌫/SEND row removed (HTML cards are now the single source of truth); SEND/BACKSPACE always tappable, dimmed when name is empty",
    "Big in-body d-pad! Chunky 70px N/S/E/W tap targets sit under the HUD chips so movement is finger-friendly; walls grey out so you see at a glance which way you can step",
    "Tap-to-move map! D-pad and bottom button panel retired in game_loop — tap an adjacent tile to step that way; INVENTORY / LANTERN / STAIRS now live as HUD chip-buttons under the map",
    "FIX: dying from status effects on room entry now actually kills you — caller no longer overrides death_screen back to game_loop after a failed move",
    "Name-entry screen redesigned — big gold name slate with blinking cursor, tappable BACKSPACE / SEND cards, live letter feedback as you type",
    "Internal: app icons recompressed (-3.6 MB), repo cleanup of orphan + stale sprite reference files (-23 MB)",
    "Internal: trimmed ~9 MB of reserve sprites from the APK pool (kept the 1283 in-game ones, dropped 3968 unused reserves)",
    "FIX: playtest mode no longer crashes with TypeError when adding scrolls / lantern fuel",
    "Internal: deleted ~24 MB of legacy sprite-sheet base64 now that everything renders from the round-8 pool",
    "Spell cast animations! Spell icons fly, flash, descend, orbit, spiral, or fill the screen depending on the spell type",
    "Loot toast popups — find an item, see a banner with its icon and name fade in at the top of the screen",
    "Every item now has an inventory icon — weapons, armor, accessories, food, ingredients, treasures, runes, shards, trophies, lanterns, towels, bug armors",
    "Spells share a single placeholder ? icon — all spells look the same in inventory until you've cast them",
    "Potions, scrolls, and spells now have icons — each new game shuffles which sprite means what (NetHack-style)",
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
