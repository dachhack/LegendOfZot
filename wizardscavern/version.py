"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 181
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "Mobile UX: chips taller for thumb-friendly tap targets. .hudchip padding 6/9 -> 11/14, font-size 11 -> 13, min-height: 44px (Apple HIG tap target), border-radius 14 -> 18. Log shrunk 140 -> 110 to make room; .bottom-pinned-zone moved from bottom: 140 to bottom: 110 to match. Net layout still fits comfortably in the viewport",
    "Mobile UX: log grown to 140px and combat layout restructured: battle box (monster + player combat + channeling) in the room-panel slot ABOVE the map; battle chips (ATTACK/CAST/FLEE/INVENTORY) in the bottom-pinned-zone UNDER the map, replacing the lantern/inventory chips. Combat mirrors regular gameplay layout exactly",
    "Mobile UX: 'Wizard's Cavern bXXX' title moved into the fixed top strip, stacked above the stats bar so the title is the first thing on every gameplay screen. Stripped the inline header from 34 per-mode templates",
    "Mobile UX: pin map+chips above the log via fixed-position. Switched .bottom-pinned-zone to position: fixed; bottom: 90px so it sits directly above the log regardless of content-area sizing",
    "Mobile UX (superseded): pin map+chips just above the log so there is no wasted vertical space. New .bottom-pinned-zone wrapper with margin-top: auto + min-height on flex containers",
    "Mobile UX: pin the map's vertical position. The flex bottom-anchor trick (min-height + margin-top:auto) was misbehaving on screens where grid_html was empty (post-shopping transition for example), pushing the Wizard's Cavern header all the way to the bottom of the content area. Replaced with a CSS rule: every .room-panel has min-height: 110px so the slot height is consistent, and the map sits at the same Y regardless of which room card (or the empty-floor placeholder) is showing. Stripped min-height + margin-top:auto from 18 flex containers and 24 grid wrappers",
    "Mobile UX layout settled: stats bar pinned at the very top, room interaction card below (now ALWAYS present -- empty floors get a placeholder showing floor + flavor + lantern fuel), then map, then action chips, then log pinned at the bottom. The empty-room placeholder keeps the map's vertical position stable when the player walks off a special tile. Live-update path syncs stats html and body class so transitions stay in lockstep",
    "Mobile UX: room interaction panels now render ABOVE the map (was below the inventory chips). Map drops into the bottom thumb-zone where every-turn movement taps live; room info card stays at the top where you only reach when you arrive on a special tile. Same content, same chips - just reordered across all 21 room modes (chest, tomb, pool, warp, stairs, library, dungeon, garden, fey, oracle, smith, shrine, alchemist, war, taxidermist, towel, teleporter, etc.)",
    "Intro/main-menu screen reuses the rune-archway splash backdrop. Backstory paragraph and NEW GAME / save-slot panel now sit over the dungeon art with darkening gradient + drop-shadows for legibility",
    "Splash + game-over screens now use full-bleed pixel-art backdrops (rune archway descending into the dungeon for splash; tombstone with skeleton remains for game-over). Watermarks trimmed off both. Title/version/changelog and final stats overlay the artwork with drop-shadows for legibility",
    "Tomb undead guardians toned down for the new HP curve: template pool tightened to player_floor +/-1 (no more F1 Wraiths from a +5 reach), buff multiplier 1.5x -> 1.25x, level bonus +2 -> +1",
    "Progression rebalance: aggression scalar removed (Lichen on F1 now hits for ~1 dmg, not 16). Player Lv1 max HP dropped from 130 to 30 (formula: lv*10 + str*2). Old saves clamped on load. Monster strength now scales purely via spawn-floor-range + linear floor scaling (3-4% per floor of overshoot) + evolution tiers (Hardened/Savage/Dread/Mythic at floor_diff 5+/13+/23+/35+)",
    "Map UI polish: tap-flash on map removed, room interaction panels now render BELOW the INVENTORY/lantern chips, INV chip spelled out as INVENTORY, lantern chip swapped for the lantern sprite, SAVE & QUIT chip removed from the inventory bar, hudchip dimensions trimmed so 5 chips (CRAFT/SPELLS/JOURNAL/QUIT/CLOSE) fit on one row even when spells are available",
    "Map arrows dimmed and shrunk — ▲▼◄► hint glyphs now render at 12px in 25% opacity green so they barely whisper at the edges of the map without competing with the dungeon glyphs",
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
