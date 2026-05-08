"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 198
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "Layout fix: tomb + stairs (and other room interactions) were forcing the bigger 18-row map to scroll. Two .room-panel CSS rules existed -- the second one set max-height: calc(100vh - 340px), which on a 700px phone gave 360px of room-panel and pushed the map below the visible bottom-pinned-zone. Removed the duplicate rule, tightened the canonical max-height 220 -> 180, and dropped redundant inner max-height: 300 from the two stairs panels. Tomb/stairs now cap at 180px and let .room-panel be the single source of truth",
    "Map dimensions: cell size 17px -> 19px and font 13px -> 15px for better legibility on phones, plus grid_rows 15 -> 18 to use the vertical room above the log. Dungeon floors are now 18x21 instead of 15x21, giving 3 more rows for room placement and exploration. All carve / spawn / pathfinding code reads gs.grid_rows dynamically so no hardcoded assumptions broke",
    "Bug fix: Wight, Ghoul, Spirit, Phantom, Banshee, Gargoyle, and other undead/spirit/construct monsters were dropping meat because they weren't in the MEAT_COOK_STYLES table OR the non_edible_keywords list -- they fell through to the default 'dubious steak'. Expanded the keyword list with wight/ghoul/spirit/phantom/banshee/poltergeist/apparition/haunt/spook/undead/crypt/death-knight/animated/gargoyle/jelly/devil/fiend/imp/efreeti/djinn/wisp/spectre so undead and incorporeal foes never harvest as meat. Goblin/Orc/Bat/etc. still drop meat as before",
    "Equip UX: equipped items now show a dedicated red UNEQUIP chip; row itself is non-tappable. Starting shop auto-equips Weapon/Armor/passive-accessory purchases",
    "Splash + intro screens now fill 100vh (was 88vh) so the title/lore/save panels sit flush against the very bottom edge instead of leaving a 12vh gap. Title shrunk 24->22px and bottom padding tightened 12->8px so even more art shows through. pointer-events: none added to the gradient overlay divs as a defensive guard so they can never swallow taps meant for the Enter button or NEW GAME chip",
    "Spell sprite fix: unidentified spell books were rendering as a CAT. Switched placeholder PID to S087 -- a tome with an arcane circle on the cover",
    "Bug fix: on a CRIT the map+chips jumped to the top because the screen-shake set transform on #content-area, re-rooting position:fixed descendants. Targeted the shake at the .room-panel only. Log strip grown 110 -> 150 for 2-3 more visible lines",
    "Toga bottom-panel collapsed on every body-only screen so the leftover SEND + backspace buttons stop peeking through, and the intro story screen has the full 88vh to render its content",
]
