"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 149
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "FIX: name-entry letters not appearing — set_input_visibility was wiping input_field.value on every render, erasing each letter the polling intercept just added",
    "FIX: in-body QWERTY keyboard on name-entry — toga keyboard renders invisible on some devices, so the body now owns the whole flow (slate + BACKSPACE/SEND + Q-Z keys); bottom panel collapsed for the screen",
    "Big in-body d-pad — chunky 70px N/S/E/W tap targets under the HUD chips, walls grey out, finger-friendly movement",
    "Tap-to-move map + HUD chips for INVENTORY / LANTERN / STAIRS in game_loop — bottom button panel retired",
    "FIX: dying from status effects on room entry now actually kills you — caller no longer overrides death_screen after a failed move",
    "Name-entry screen redesigned — big gold name slate with blinking cursor and live letter feedback",
    "Spell cast animations — spell icons fly, flash, descend, orbit, spiral, or fill the screen depending on the spell type",
    "Loot toast popups — find an item, see a banner with its icon and name fade in at the top of the screen",
    "Every item has an inventory icon; potions/scrolls/spells get NetHack-style shuffled icons each new game",
]
