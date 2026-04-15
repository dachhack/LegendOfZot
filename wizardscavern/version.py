"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 80
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "FIX: Music actually doesn't reset now (removed bad fallback path)",
    "Android: use native evaluateJavascript directly for reliability",
    "REFACTOR: WebView no longer reloads on every button press",
    "AudioContext lives forever in the shell, music truly continuous",
    "FIX: Victory music starts at 1.8s (right after death SFX)",
    "FIX: Death music starts at 3.5s (right after player damage)",
    "FIX: Dice labels no longer overlap (ATK/DEF short forms + clip)",
    "CHIPTUNE SFX + music! NES-style square/noise synthesis throughout",
]
