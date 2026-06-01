"""Ambient flavor text for plain, empty dungeon tiles.

In the 1980 *Wizard's Castle* (Recreational Computing, July/Aug 1980) the
main loop would, one turn in five, toss out a little ambient line: you
stepped on a frog, you heard a scream / footsteps / a wumpus / thunder,
you sneezed, you saw a bat fly by, you smelled a monster frying, you felt
watched, you heard faint rustling.  Half dread, half deadpan -- pure Zot.

This module keeps that spirit but blows the bank wide open.  Instead of a
flat list of eight strings we assemble lines from sense-keyed fragment
pools, so a plain stone floor can read a few hundred different ways while
still landing in the original's voice.

`empty_room_flavor(seed)` is deterministic: the same seed always yields
the same line.  Callers pass a seed derived from the player's position so
the flavor stays put until the player actually moves (a re-render of the
same tile must not reshuffle the text).
"""

import random


# Fully-formed atmospheric one-liners.  These carry the "silent dread"
# half of the original's tone and need no assembly.
_STANDALONE = (
    "An empty stretch of dungeon -- silent and still.",
    "Cool, damp stones underfoot.",
    "Dust drifts in the still air.",
    "Distant water drips somewhere far off.",
    "Faint runes glow on a nearby wall, then fade.",
    "The torch-smoke of long-dead adventurers lingers here.",
    "Stone, shadow, and the smell of mildew.",
    "A draft from somewhere chills the back of your neck.",
    "Your footsteps echo and do not quite stop when you do.",
    "The walls sweat a slow, cold sweat.",
    "Cobwebs the size of bedsheets sag from the corners.",
    "Something scuttles out of the torchlight before you can name it.",
    "The silence has a texture down here, like wet wool.",
    "A single bone lies in the dust. You decide not to ask.",
    "Old scratch-marks score the stone at exactly your eye level.",
    "The air tastes of iron and very old secrets.",
    "Empty. Suspiciously, almost insultingly, empty.",
    "Nothing here but the patient dark.",
    "A chalk tally on the wall counts to forty-one and stops.",
    "The floor is worn smooth by feet that never came back.",
)

# Sense-keyed fragment pools.  Each line is assembled as
# "You <verb> <fragment>" so the fragment just needs to read naturally
# after the verb.  Mix of menace and Zot's signature deadpan.
_HEAR = (
    "a distant scream cut suddenly short.",
    "footsteps that match your own, one beat behind.",
    "a wumpus bellowing somewhere below.",
    "thunder, though you are nowhere near the sky.",
    "faint rustling noises in the walls.",
    "dripping that keeps almost-but-not-quite a rhythm.",
    "something heavy dragging itself down a far corridor.",
    "a child laughing, which is much worse than a scream.",
    "chains, briefly, and then very deliberate silence.",
    "the castle settling its old stone bones.",
    "a flute playing one wrong note over and over.",
    "your own heartbeat, far too loud.",
    "wings -- big ones -- somewhere up in the dark.",
    "a door slam in a level you have not reached yet.",
)

_SMELL = (
    "something frying that you sincerely hope was not a kobold.",
    "ogre, roasting, with notes of regret.",
    "damp stone, old blood, and faint woodsmoke.",
    "a vendor's cookfire, three rooms and one bad idea away.",
    "sulphur, the way a spell smells just before it goes wrong.",
    "mildew, mushrooms, and the ghost of last week's adventurer.",
    "incense, sweet and wrong, drifting from nowhere.",
    "wet dog, though there is certainly no dog down here.",
    "char, brimstone, and somebody else's bad luck.",
    "fresh bread, impossibly, and your stomach betrays you.",
)

_FEEL = (
    "like you're being watched -- and not kindly.",
    "the temperature drop two degrees for no reason at all.",
    "a sudden, baseless certainty that you took a wrong turn.",
    "the weight of the whole castle pressing down overhead.",
    "your hackles rise, though nothing has changed.",
    "a cobweb brush your face. There was no cobweb a moment ago.",
    "oddly homesick for a tavern you have never visited.",
    "the stone hum faintly underfoot, like a held breath.",
    "eyes on the back of your neck. You don't turn around.",
    "very small, and very far from the entrance.",
)

_SEE = (
    "a bat flap past and vanish into the dark.",
    "a frog blink at you from a puddle, then think better of it.",
    "your own shadow lag a half-second behind you.",
    "torchlight glint off something that closes before you can focus.",
    "a rat the size of a hound watch you, then politely leave.",
    "old graffiti: 'TURN BACK' -- the writer clearly did not.",
    "a faded mural of Zot, looking smugger than the dead deserve.",
    "a faint chalk arrow, pointing the way you just came.",
    "dust hang in the air in the exact shape of a person. Then it doesn't.",
    "a discarded sandwich crust. Even down here, somebody ate well.",
)

# Small deadpan beats that don't fit the sense template -- direct nods to
# the original's frog-stepping, sneezing, soap-opera-rerun energy.
_BEATS = (
    "You step on a frog. It does not forgive you.",
    "You sneeze. The echo comes back wrong.",
    "You count your flares again, just to be sure. Still not enough.",
    "A draft riffles a page of someone's abandoned journal: '...should never have come...'",
    "You consider, briefly, the life choices that led you here.",
    "Somewhere, the Orb of Zot is decidedly not in this room.",
    "You whistle a few bars. The dark does not whistle back.",
    "A loose flagstone wobbles underfoot. You leave it for the next fool.",
)

_VERBS = {
    "hear": _HEAR,
    "smell": _SMELL,
    "feel": _FEEL,
    "see": _SEE,
}

# Relative weights for which kind of line to produce.  Standalone
# atmosphere is the most common; the assembled senses fill out the
# middle; the comedic beats are the rare spice (like the original's
# one-in-a-while gags).
_WEIGHTS = (
    ("standalone", 32),
    ("hear", 14),
    ("smell", 10),
    ("feel", 12),
    ("see", 14),
    ("beat", 8),
)


def empty_room_flavor(seed):
    """Return one ambient flavor line for an empty tile.

    Deterministic in ``seed``: the same seed always returns the same
    line, so a tile keeps its flavor across re-renders and only changes
    when the player moves to a tile with a different seed.
    """
    rng = random.Random(seed)
    kinds, weights = zip(*_WEIGHTS)
    kind = rng.choices(kinds, weights=weights, k=1)[0]

    if kind == "standalone":
        return rng.choice(_STANDALONE)
    if kind == "beat":
        return rng.choice(_BEATS)
    # Sense-keyed assembly: "You hear/smell/feel/see <fragment>"
    return "You " + kind + " " + rng.choice(_VERBS[kind])
