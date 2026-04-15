"""
Auto-generated version info. BUILD_NUMBER is incremented by pre-commit hook.
CHANGELOG is populated from recent git log entries.
"""

VERSION = "0.1.2"
BUILD_NUMBER = 80
# NOTE: Keep this list short (~8 entries). Remove old ones as new ones land.
CHANGELOG = [
    "FIX: Music plays now! Bootstrap fires immediately, not on 'load' event",
    "iOS: allow audio without user gesture (no security warning, just config)",
    "FIX: Music doesn't reset (removed bad render fallback path)",
    "Android: use native evaluateJavascript directly for reliability",
    "REFACTOR: WebView no longer reloads on every button press",
    "FIX: Victory music starts at 1.8s, death music at 3.5s",
    "FIX: Dice labels no longer overlap (ATK/DEF short forms + clip)",
    "CHIPTUNE SFX + music! NES-style square/noise synthesis throughout",
]
