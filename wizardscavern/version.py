"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 512
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "b512: LETTERS YOU CAN READ FROM ORBIT. Room badges and the monster M now scale INVERSELY with zoom -- the further out you zoom, the bigger their share of the cell (close 14px badges, mid 12px, full-floor 11px on 19px cells; the M runs 19/16/14px). The full-floor strategic view finally reads like a proper legend instead of colored dust.",
    "b511: CRACKS, NOT KNOTS. Ore-vein bolts now use a self-avoiding walk: a vein never crosses itself and never turns back toward rock it already split, and a momentum bias makes it prefer running straight -- so each detected tile carries one long clean fissure, and neighbouring vein tiles chain into what reads as a single crack streaking through the wall.",
    "b510: LONGER BOLTS + PICKAXE FEEDBACK. (1) Ore-vein bolts run longer -- 8 crevice steps instead of 5, so a detected vein tile carries one proper lightning crack instead of a stub. (2) Mining finally LOOKS like mining: when your pickaxe smashes through, a dust cloud bursts over the broken wall and four rock chips fly outward while the stone becomes open floor. One swing, one satisfying puff.",
    "b509: VEINS LIKE LIGHTNING. Ore seams take their final form: a muted ochre BOLT cracking through the wall -- the vein routes through the crevices between the drawn boulders, but each segment kinks at a sharp perpendicular jag with hard miter corners, like a fissure of mineral splitting the stone. The nugget flecks are gone entirely; the crack IS the tell.",
    "b507: GOLD IN THEM WALLS. Detected ore veins are visible again. The old amber % glyph silently vanished when walls went art-only in b493; now a dwarf (or a Stonelore human) walking past a vein sees a golden seam drawn right into the rock, one segment per vein tile, so you can trace the whole worm before you swing. Tap MINE, pick the direction, follow the sparkle.",
    "b506: YOU ARE THE BRACKETS. The white player box is retired for four clean corner brackets -- a targeting reticle around your cell -- so the room you occupy stays fully visible: its floor, its prop, its letter badge, even the debris under your boots. No more standing in a chest room wondering what you're standing on.",
    "b505: LURKERS UNMASKED + LUSHER GARDENS. (1) The monster M shrinks to a compact centered glyph -- and when a monster squats in a themed room, that room's own color-coded letter now shows in the corner beside it: you can see it's YOUR chest room the thing is guarding before you commit to the fight. (2) Gardens stopped being a single potted plant: each garden room grows its own dense little grove -- 5 to 7 plants, flowers and mushrooms clustered together, seeded per room so every garden grows differently.",
    "b503: THE CURATED CAVERN. The full sprite set is now hand-picked (all 245 picker edits applied): floor debris nearly QUADRUPLES to 282 sprites across 16 groups -- 64 rubble variants, 37 flora, 31 bones, 25 mushrooms, 24 pottery, plus chains, cloth, webs, wood and more, so repeats get rare. Room art deepens too: 6 alchemist benches, 8 stairways up / 6 down, 5 locked-dungeon grates, 5 pools including a glowing fountain, 4 chests, a mirror and orb pedestal for the Oracle, an extra rune circle for warps. The open cauldron, lotus and crystal shards are retired. Zotle chambers go minimalist: just the violet Z.",
]
