"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 165
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "Map movement: X-quadrant triangle hotspots tile the whole map area — tap the top triangle to step n, right for e, bottom for s, left for w. Small ▲▼◄► glyphs at the edge midpoints serve as visual hints. No more cardinal-neighbour cell taps; no more perimeter bars",
    "Map centering fix — mvframe now uses display:block + width:fit-content + margin:0 auto, so the full 15x21 floor renders centered on the screen instead of hugging the left edge",
    "Map edge tap zones now always tappable — walls log 'You hit a wall!' instead of greying out the affordance",
    "Map edge tap zones! Big in-body d-pad gone — tap the slim arrow strips around the map perimeter to step that direction. INV / LANT / STAIRS chips shrunk to compact pills",
    "Toga panel retired everywhere: list-picker modes (spell cast/memorize, crafting, journal, save/load, sell quantity, character stats, scroll picks), plus an HTML numpad for the Zotle teleporter — every mode is now body-only",
    "Map-view room modes finished: warp, dungeon, fey garden, blacksmith, shrine, alchemist, war room, taxidermist, towel, altar — all on body-only HTML with HUD chips + d-pad, toga bottom panel collapsed",
    "Zotle puzzle mode: HTML keyboard with Wordle-style letter coloring (green/yellow/grey hints), tappable BACKSPACE / ENTER / LEAVE chips, no more invisible toga keyboard",
    "Build number now appears next to 'Wizard's Cavern' header on every screen — easy to verify which build is running from a screenshot",
    "Combat + inventory chips: ATTACK / CAST / FLEE / INVENTORY in combat, CRAFT / SPELLS / JOURNAL / QUIT / SAVE&QUIT / CLOSE in inventory — all as HTML chips since the toga buttons render invisible",
    "Game-loop polish: map cell highlights gone, INVENTORY / LANTERN chips bigger and bolder, d-pad arrows trimmed from 70 to 52 px",
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
