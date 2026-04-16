#!/usr/bin/env python3
"""
Wizard's Cavern - Toga Version
A text-based dungeon crawler built with Toga and WebView for HTML rendering.

This file contains the UI layer (WizardsCavernApp class) and entry point.
Game logic is split across module files:
  - game_state.py: Shared mutable globals and utility functions
  - achievements.py: Achievement system
  - zotle.py: Zotle puzzle system
  - item_templates.py: Item/template data
  - items.py: Item classes and identification system
  - characters.py: Character, Monster, Inventory, StatusEffect classes
  - dungeon.py: Room, Floor, Tower classes and dungeon generation
  - combat.py: Combat system
  - vendor.py: Vendor system
  - save_system.py: Save/load system
  - room_actions.py: Room interaction handlers
  - game_systems.py: Vault, treasure, crafting, movement, stairs, etc.
"""

# Standard library imports
import random
import math
import re
import textwrap
from collections import deque
import json
import os
from datetime import datetime

# Toga framework
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

# Sprite and game data
from .sprite_data import (
    generate_monster_sprite_html,
    generate_room_sprite_html,
    generate_player_sprite_html as _generate_player_sprite_html,
)
from .game_data import (
    MONSTER_TEMPLATES,
    MONSTER_SPAWN_FLOOR_RANGE,
    MONSTER_EVOLUTION_TIERS,
    TROPHY_DROPS,
    TAXIDERMIST_COLLECTIONS,
)

# Game state (all shared mutable globals)
from . import game_state as gs
from .game_state import (add_log, print_to_output, normal_int_range, get_article,
                        COLOR_RED, COLOR_GREEN, COLOR_RESET, COLOR_PURPLE,
                        COLOR_BLUE, COLOR_CYAN, COLOR_YELLOW, COLOR_GREY, BOLD, UNDERLINE)

# Game modules - import all public names for backward compatibility
from .achievements import Achievement, ACHIEVEMENTS, check_achievements
from .zotle import (scramble_word_for_zotle, check_zotle_guess, initialize_zotle_puzzle,
                   format_zotle_guess_html, should_spawn_puzzle_room, spawn_puzzle_room_on_floor)
from .item_templates import *
from .items import *
from .characters import *
from .dungeon import Room, Floor, Tower, is_wall_at_coordinate
from .combat import *
from .vendor import *
from .save_system import SaveSystem
from .room_actions import *
from .game_systems import *
from .game_systems import _handle, _trigger_room_interaction, _execute_warp
from .version import VERSION, BUILD_NUMBER, CHANGELOG

def _extract_script_body(html_str):
    """Extract concatenated bodies of all <script> tags from a string.

    Used by _render_update() to convert the existing animation/SFX
    generators (which return '<script>...</script>' strings) into raw
    JS that can be passed to evaluate_javascript().  innerHTML doesn't
    auto-execute embedded scripts, so we strip the wrapper and re-execute
    the body via document.createElement('script').
    """
    if not html_str:
        return ''
    bodies = re.findall(
        r'<script[^>]*>(.*?)</script>', html_str, re.DOTALL
    )
    return '\n'.join(b for b in bodies if b.strip())


def get_audio_mood(prompt_cntl):
    """Map game state to a music mood.

    Only 5 major moods so music restarts only at significant transitions:
      menu    — splash, character creation, intro shop
      explore — all dungeon activity (movement, vendors, altars, inventory...)
      combat  — active combat and spell casting
      victory — just won a fight
      death   — game over
    """
    if prompt_cntl in ('splash', 'intro_story', 'main_menu',
                        'player_name', 'player_race', 'player_gender',
                        'starting_shop', 'game_loaded_summary',
                        'save_load_mode', 'load_pending', 'confirm_quit'):
        return 'menu'
    if prompt_cntl in ('combat_mode', 'spell_casting_mode',
                        'spell_memorization_mode', 'flee_direction_mode'):
        return 'combat'
    if prompt_cntl == 'combat_victory':
        return 'victory'
    if prompt_cntl == 'death_screen':
        return 'death'
    # Everything else: dungeon, vendors, altars, chests, inventory, puzzles
    return 'explore'


def generate_inline_music_js(mood, start_step, enabled, start_delay_ms=0):
    """Generate a self-contained <script> tag that plays the given mood.

    This injects a fresh AudioContext + sequencer into the main game
    page on every render.

    start_step lets us resume at the position the music *would* be at
    if it had been playing continuously, so back-to-back renders feel
    like one uninterrupted song.

    start_delay_ms delays the entire music start — used when transitioning
    to victory/death mood so the kill/damage animation finishes before
    the new theme begins.
    """
    if not enabled:
        return ""
    return """
    <script>
    (function() {
        var MOOD = '__MOOD__';
        var START_STEP = __START_STEP__;
        var START_DELAY_MS = __START_DELAY_MS__;
        function startMusicEngine() {
        try {
            var AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) return;
            var ctx = new AC();
            // Try to resume on any user click anywhere
            var resumeOnClick = function() {
                if (ctx.state === 'suspended') ctx.resume();
            };
            window.addEventListener('click', resumeOnClick, {passive:true,once:false});
            window.addEventListener('touchstart', resumeOnClick, {passive:true,once:false});
            var master = ctx.createGain();
            master.gain.value = 0;
            master.connect(ctx.destination);
            master.gain.linearRampToValueAtTime(0.0, ctx.currentTime + 0.05);
            master.gain.linearRampToValueAtTime(0.25, ctx.currentTime + 0.4);

            var songs = __SONGS_JSON__;
            var MOOD_ALIASES = {shop:'explore', mystery:'explore', deep:'explore', garden:'explore'};
            MOOD = MOOD_ALIASES[MOOD] || MOOD;
            var song = songs[MOOD] || songs.explore;
            var stepSec = 60 / (song.bpm * 2);
            var totalSteps = 64;
            var currentStep = ((START_STEP % totalSteps) + totalSteps) % totalSteps;

            var nLen = ctx.sampleRate;
            var nBuf = ctx.createBuffer(1, nLen, ctx.sampleRate);
            var nd = nBuf.getChannelData(0);
            for (var i = 0; i < nLen; i++) nd[i] = Math.random() * 2 - 1;
            var VOL = { pulse1: 0.08, pulse2: 0.06, triangle: 0.12, noise: 0.07 };

            function playNote(freq, dur, type, vol) {
                if (!freq || freq <= 0) return;
                var osc = ctx.createOscillator();
                osc.type = type; osc.frequency.value = freq;
                osc.detune.value = (Math.random() * 16) - 8;
                var g = ctx.createGain();
                var now = ctx.currentTime;
                var len = dur * stepSec;
                g.gain.setValueAtTime(vol, now);
                g.gain.setValueAtTime(vol * 0.8, now + len * 0.75);
                g.gain.linearRampToValueAtTime(0.001, now + len * 0.95);
                osc.connect(g); g.connect(master);
                osc.start(now); osc.stop(now + len);
            }
            function playNoiseHit(filterFreq, dur) {
                var src = ctx.createBufferSource();
                src.buffer = nBuf;
                var filt = ctx.createBiquadFilter();
                if (filterFreq < 500) {
                    filt.type = 'lowpass';
                    filt.frequency.value = filterFreq * (0.9 + Math.random() * 0.2);
                } else {
                    filt.type = 'bandpass';
                    filt.frequency.value = filterFreq * (0.85 + Math.random() * 0.3);
                    filt.Q.value = 1 + Math.random() * 2;
                }
                var g = ctx.createGain();
                var now = ctx.currentTime;
                var len = Math.min(dur * stepSec, 0.15);
                g.gain.setValueAtTime(VOL.noise, now);
                g.gain.exponentialRampToValueAtTime(0.001, now + len);
                src.connect(filt); filt.connect(g); g.connect(master);
                src.start(now); src.stop(now + len + 0.01);
            }
            function tick() {
                var channels = ['pulse1', 'pulse2', 'triangle', 'noise'];
                for (var c = 0; c < channels.length; c++) {
                    var ch = channels[c];
                    var pattern = song[ch];
                    if (!pattern) continue;
                    for (var n = 0; n < pattern.length; n++) {
                        if (pattern[n][0] === currentStep) {
                            var freq = pattern[n][1];
                            var dur = pattern[n][2];
                            if (ch === 'noise') playNoiseHit(freq, dur);
                            else if (ch === 'triangle') playNote(freq, dur, 'triangle', VOL.triangle);
                            else playNote(freq, dur, 'square', VOL[ch]);
                        }
                    }
                }
                currentStep = (currentStep + 1) % totalSteps;
            }
            setInterval(tick, stepSec * 1000);
        } catch(e) {}
        }  // end startMusicEngine
        if (START_DELAY_MS > 0) {
            setTimeout(startMusicEngine, START_DELAY_MS);
        } else {
            startMusicEngine();
        }
    })();
    </script>
    """.replace('__MOOD__', mood).replace(
        '__START_STEP__', str(int(start_step) % 64)
    ).replace(
        '__START_DELAY_MS__', str(int(start_delay_ms))
    ).replace('__SONGS_JSON__', _MUSIC_SONGS_JSON)


# Song data extracted as JSON so generate_inline_music_js doesn't have
# to re-encode it on every render.
_MUSIC_SONGS_JSON = json.dumps({
    'explore': {
        'bpm': 110,
        'pulse1': [[0,262,2],[3,311,1],[4,392,3],[8,349,1],[9,311,1],[10,294,2],[12,262,2],[16,233,2],[19,262,1],[20,311,3],[24,294,1],[25,262,1],[26,233,2],[28,262,4],[32,392,2],[34,349,1],[35,311,1],[36,294,2],[38,262,2],[40,311,3],[44,392,1],[45,440,1],[46,392,2],[48,349,2],[50,311,1],[51,294,1],[52,262,3],[56,233,2],[58,262,1],[59,294,1],[60,262,4]],
        'pulse2': [[4,311,2],[12,196,2],[20,262,2],[28,196,4],[36,233,2],[44,311,2],[52,196,2],[60,233,4]],
        'triangle': [[0,131,4],[4,104,4],[8,117,4],[12,98,4],[16,104,4],[20,156,4],[24,117,4],[28,131,4],[32,131,4],[36,156,4],[40,117,4],[44,104,4],[48,98,4],[52,117,4],[56,104,4],[60,131,4]],
        'noise': [[0,8000,1],[2,8000,1],[4,8000,1],[6,8000,1],[8,150,1],[10,8000,1],[12,8000,1],[14,8000,1],[16,8000,1],[18,8000,1],[20,8000,1],[22,8000,1],[24,150,1],[26,8000,1],[28,8000,1],[30,8000,1],[32,8000,1],[34,8000,1],[36,8000,1],[38,8000,1],[40,150,1],[42,8000,1],[44,8000,1],[46,8000,1],[48,8000,1],[50,8000,1],[52,8000,1],[54,8000,1],[56,150,1],[58,3000,1],[60,8000,1],[62,8000,1]]
    },
    'combat': {
        'bpm': 140,
        'pulse1': [[0,440,1],[1,330,1],[2,440,1],[3,523,2],[6,494,1],[7,440,1],[8,392,2],[10,330,1],[11,294,1],[12,330,2],[14,262,1],[15,294,1],[16,440,1],[17,330,1],[18,440,1],[19,523,2],[22,587,1],[23,523,1],[24,440,2],[26,392,1],[27,330,1],[28,294,2],[30,330,2],[32,523,1],[33,440,1],[34,523,1],[35,587,2],[38,523,1],[39,440,1],[40,392,1],[41,330,1],[42,294,1],[43,330,1],[44,440,2],[46,523,2],[48,587,2],[50,523,1],[51,440,1],[52,392,2],[54,330,1],[55,294,1],[56,262,2],[58,294,1],[59,330,1],[60,440,2],[62,392,2]],
        'pulse2': [[0,220,1],[2,220,1],[4,175,1],[6,175,1],[8,196,1],[10,196,1],[12,165,1],[14,165,1],[16,220,1],[18,220,1],[20,175,1],[22,175,1],[24,196,1],[26,196,1],[28,165,1],[30,131,1],[32,262,1],[34,262,1],[36,220,1],[38,220,1],[40,196,1],[42,196,1],[44,220,1],[46,220,1],[48,262,1],[50,262,1],[52,196,1],[54,196,1],[56,165,1],[58,165,1],[60,220,1],[62,220,1]],
        'triangle': [[0,110,2],[4,87,2],[8,98,2],[12,82,2],[16,110,2],[20,87,2],[24,98,2],[28,131,2],[32,131,2],[36,110,2],[40,98,2],[44,87,2],[48,131,2],[52,110,2],[56,82,2],[60,110,2]],
        'noise': [[0,150,1],[2,3000,1],[4,150,1],[6,3000,1],[8,150,1],[10,3000,1],[12,150,1],[14,3000,1],[16,150,1],[18,3000,1],[20,150,1],[22,3000,1],[24,150,1],[26,3000,1],[28,150,1],[30,3000,1],[32,150,1],[34,3000,1],[36,150,1],[38,3000,1],[40,150,1],[41,150,1],[42,3000,1],[44,150,1],[46,3000,1],[48,150,1],[50,3000,1],[52,150,1],[54,3000,1],[56,150,1],[57,150,1],[58,3000,1],[60,150,1],[62,3000,1]]
    },
    'victory': {
        'bpm': 130,
        'pulse1': [[0,262,2],[2,330,2],[4,392,2],[6,523,4],[12,494,1],[13,440,1],[14,392,2],[16,330,2],[18,392,2],[20,440,2],[22,523,6],[28,659,2],[30,523,2],[32,659,2],[34,523,2],[36,440,2],[38,392,2],[40,440,2],[42,523,2],[44,659,4],[48,523,2],[50,440,2],[52,392,2],[54,523,2],[56,659,3],[60,784,4]],
        'pulse2': [[0,196,2],[4,262,2],[6,330,4],[16,262,2],[20,330,2],[22,392,6],[32,392,2],[36,330,2],[38,262,4],[48,330,2],[52,262,2],[54,330,6]],
        'triangle': [[0,131,4],[4,175,4],[8,196,4],[12,131,4],[16,131,4],[20,175,4],[24,196,4],[28,131,4],[32,175,4],[36,196,4],[40,131,4],[44,175,4],[48,196,4],[52,131,4],[56,175,4],[60,131,4]],
        'noise': [[0,150,1],[1,8000,1],[2,3000,1],[3,8000,1],[4,150,1],[5,8000,1],[6,3000,1],[7,8000,1],[8,150,1],[10,3000,1],[12,150,1],[14,3000,1],[16,150,1],[17,8000,1],[18,3000,1],[20,150,1],[22,3000,1],[24,150,1],[26,3000,1],[28,150,1],[30,3000,1],[32,150,1],[33,8000,1],[34,3000,1],[35,8000,1],[36,150,1],[38,3000,1],[40,150,1],[41,8000,1],[42,3000,1],[44,150,1],[46,3000,1],[48,150,1],[49,8000,1],[50,3000,1],[52,150,1],[54,3000,1],[56,150,1],[58,3000,1],[60,150,1],[62,3000,1]]
    },
    'death': {
        'bpm': 70,
        'pulse1': [[0,349,3],[4,311,3],[8,277,3],[12,262,3],[16,233,4],[22,277,2],[24,311,3],[28,233,4],[32,277,3],[36,262,3],[40,233,3],[44,277,3],[48,311,4],[54,277,2],[56,262,3],[60,233,4]],
        'pulse2': [[0,233,8],[8,185,8],[16,156,8],[24,175,8],[32,175,8],[40,156,8],[48,185,8],[56,156,8]],
        'triangle': [[0,117,8],[8,139,8],[16,117,8],[24,87,8],[32,139,8],[40,117,8],[48,139,8],[56,117,8]],
        'noise': [[0,4000,1],[16,4000,1],[32,4000,1],[48,4000,1]]
    },
    'menu': {
        'bpm': 90,
        'pulse1': [[0,294,2],[2,349,2],[4,440,3],[8,392,1],[9,349,1],[10,294,2],[12,262,2],[14,294,2],[16,349,2],[18,440,2],[20,523,3],[24,440,1],[25,392,1],[26,349,2],[28,294,4],[32,349,2],[34,440,2],[36,523,3],[40,440,1],[41,392,1],[42,349,2],[44,294,2],[46,349,2],[48,440,2],[50,523,2],[52,587,3],[56,523,1],[57,440,1],[58,392,2],[60,349,4]],
        'pulse2': [[4,294,2],[12,220,2],[20,349,2],[28,220,4],[36,349,2],[44,262,2],[52,392,2],[60,262,4]],
        'triangle': [[0,147,4],[4,175,4],[8,196,4],[12,131,4],[16,147,4],[20,175,4],[24,196,4],[28,147,4],[32,175,4],[36,196,4],[40,147,4],[44,131,4],[48,175,4],[52,196,4],[56,147,4],[60,147,4]],
        'noise': [[0,8000,1],[4,8000,1],[8,8000,1],[12,8000,1],[16,8000,1],[20,8000,1],[24,8000,1],[28,8000,1],[32,8000,1],[36,8000,1],[40,8000,1],[44,8000,1],[48,8000,1],[52,8000,1],[56,8000,1],[60,8000,1]]
    }
})


def build_audio_player_html():
    """Persistent audio player HTML — loaded ONCE into the hidden audio
    WebView so the AudioContext lives forever across game renders.

    Exposes:
      - window.setMood(mood, enabled) — switch active song
      - window.setMusicEnabled(on)     — mute/unmute on the fly
      - window.audioReady              — true once initialized

    Gesture policy is bypassed at the platform level (see startup() —
    setMediaPlaybackRequiresUserGesture(false) on Android,
    mediaTypesRequiringUserActionForPlayback = 0 on iOS).
    """
    return """<!DOCTYPE html>
<html>
<head><meta charset='UTF-8'></head>
<body style='margin:0;padding:0;background:#000;'>
<script>
(function() {
    var SONGS = """ + _MUSIC_SONGS_JSON + """;
    var MOOD_ALIASES = {shop:'explore', mystery:'explore', deep:'explore', garden:'explore'};
    var ctx = null, master = null, noiseBuf = null;
    var currentMood = null, currentSong = null;
    var stepSec = 0.3, currentStep = 0, tickHandle = null;
    var enabled = true;
    var totalSteps = 64;
    var VOL = { pulse1: 0.08, pulse2: 0.06, triangle: 0.12, noise: 0.07 };
    var pendingMood = null, pendingEnabled = true;

    function initCtx() {
        if (ctx) return true;
        try {
            var AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) return false;
            ctx = new AC();
            master = ctx.createGain();
            master.gain.value = 0.25;
            master.connect(ctx.destination);
            var nLen = ctx.sampleRate;
            noiseBuf = ctx.createBuffer(1, nLen, ctx.sampleRate);
            var nd = noiseBuf.getChannelData(0);
            for (var i = 0; i < nLen; i++) nd[i] = Math.random() * 2 - 1;
            return true;
        } catch(e) { return false; }
    }

    function playNote(freq, dur, type, vol) {
        if (!freq || freq <= 0 || !enabled) return;
        try {
            var osc = ctx.createOscillator();
            osc.type = type; osc.frequency.value = freq;
            osc.detune.value = (Math.random() * 16) - 8;
            var g = ctx.createGain();
            var now = ctx.currentTime;
            var len = dur * stepSec;
            g.gain.setValueAtTime(vol, now);
            g.gain.setValueAtTime(vol * 0.8, now + len * 0.75);
            g.gain.linearRampToValueAtTime(0.001, now + len * 0.95);
            osc.connect(g); g.connect(master);
            osc.start(now); osc.stop(now + len);
        } catch(e) {}
    }

    function playNoiseHit(filterFreq, dur) {
        if (!enabled) return;
        try {
            var src = ctx.createBufferSource();
            src.buffer = noiseBuf;
            var filt = ctx.createBiquadFilter();
            if (filterFreq < 500) {
                filt.type = 'lowpass';
                filt.frequency.value = filterFreq * (0.9 + Math.random() * 0.2);
            } else {
                filt.type = 'bandpass';
                filt.frequency.value = filterFreq * (0.85 + Math.random() * 0.3);
                filt.Q.value = 1 + Math.random() * 2;
            }
            var g = ctx.createGain();
            var now = ctx.currentTime;
            var len = Math.min(dur * stepSec, 0.15);
            g.gain.setValueAtTime(VOL.noise, now);
            g.gain.exponentialRampToValueAtTime(0.001, now + len);
            src.connect(filt); filt.connect(g); g.connect(master);
            src.start(now); src.stop(now + len + 0.01);
        } catch(e) {}
    }

    function tick() {
        if (!currentSong || !enabled) return;
        var channels = ['pulse1', 'pulse2', 'triangle', 'noise'];
        for (var c = 0; c < channels.length; c++) {
            var ch = channels[c];
            var pattern = currentSong[ch];
            if (!pattern) continue;
            for (var n = 0; n < pattern.length; n++) {
                if (pattern[n][0] === currentStep) {
                    var freq = pattern[n][1];
                    var dur = pattern[n][2];
                    if (ch === 'noise') playNoiseHit(freq, dur);
                    else if (ch === 'triangle') playNote(freq, dur, 'triangle', VOL.triangle);
                    else playNote(freq, dur, 'square', VOL[ch]);
                }
            }
        }
        currentStep = (currentStep + 1) % totalSteps;
    }

    window.setMood = function(mood, musicEnabled) {
        if (!initCtx()) {
            // Queue for retry
            pendingMood = mood;
            pendingEnabled = musicEnabled;
            return;
        }
        enabled = (musicEnabled !== false);
        if (ctx.state === 'suspended') {
            try { ctx.resume(); } catch(e) {}
        }
        mood = MOOD_ALIASES[mood] || mood;
        if (mood === currentMood) return;
        currentMood = mood;
        currentSong = SONGS[mood] || SONGS.explore;
        stepSec = 60 / (currentSong.bpm * 2);
        currentStep = 0;
        if (tickHandle) clearInterval(tickHandle);
        tickHandle = setInterval(tick, stepSec * 1000);
    };

    window.setMusicEnabled = function(on) {
        enabled = !!on;
        if (master) {
            try {
                var target = enabled ? 0.25 : 0;
                master.gain.setTargetAtTime(target, ctx.currentTime, 0.05);
            } catch(e) {}
        }
    };

    window.stopMusic = function() {
        if (tickHandle) { clearInterval(tickHandle); tickHandle = null; }
        currentSong = null;
        currentMood = null;
    };

    // Resume audio on any gesture this frame ever receives
    function tryResume() {
        if (ctx && ctx.state === 'suspended') {
            try { ctx.resume(); } catch(e) {}
        }
        // Also process pending mood request if any
        if (pendingMood) {
            var m = pendingMood, e = pendingEnabled;
            pendingMood = null;
            window.setMood(m, e);
        }
    }
    window.addEventListener('click', tryResume, {passive:true});
    window.addEventListener('touchstart', tryResume, {passive:true});

    // Mark ready so Python can detect that the page loaded
    window.audioReady = true;
})();
</script>
</body>
</html>"""


def generate_sfx_js(monster_dmg, player_dmg, player_blocked, player_heal,
                     monster_badge, player_badge, player_status, monster_status,
                     spell_cast, concentration_roll, monster_defeated,
                     sfx_event, music_enabled, has_dice_rolls=False, has_init_roll=False):
    """Generate one-shot procedural sound effects via Web Audio API.

    SFX are grouped by timing to sync with animations:
    - Spell SFX fires with spell banner (~100ms)
    - "Hit monster" SFX fires with monster damage float/shake (~1300ms)
    - "Hit player" SFX fires with player damage float/shake (~3200ms)
    - Non-combat SFX (chest, buy, etc.) fires immediately
    """
    if not music_enabled:
        return ""

    # Match the timeline from generate_damage_float_js.  The damage floats
    # and panel shakes ALWAYS land at these offsets regardless of whether
    # dice were rolled — spells, status-effect damage, and channeled
    # attacks all still show their damage float at MONSTER_DMG_DELAY (1.3s)
    # and PLAYER_DMG_DELAY (3.2s).  So SFX (including monster_death) must
    # fire at the same delays so the sound lands WITH the visual impact.
    # Previously this gated the delay on has_dice_rolls, which caused
    # monster_death SFX to fire immediately on spell kills while the
    # damage float waited until 1.3s — death SFX played before the hit.
    init_offset = 1000 if has_init_roll else 0
    monster_hit_delay = 1300 + init_offset
    player_hit_delay = 3200 + init_offset
    spell_delay_ms = 100 if spell_cast else 0

    # Categorize effects by timing
    effects = []              # immediate (non-combat)
    monster_hit_effects = []  # synced with monster damage shake
    player_hit_effects = []   # synced with player damage shake
    spell_effects = []        # synced with spell banner

    # --- "Hit monster" effects (sync with monster panel shake) ---
    if monster_dmg and monster_dmg > 0 and not spell_cast:
        if monster_badge == 'CRIT':
            monster_hit_effects.append('crit_hit')
        else:
            monster_hit_effects.append('weapon_hit')

    if monster_status:
        monster_hit_effects.append('status_inflict')

    if monster_defeated:
        monster_hit_effects.append('monster_death')

    # --- "Hit player" effects (sync with player panel shake) ---
    if player_dmg and player_dmg > 0:
        if player_badge == 'FUMBLE':
            player_hit_effects.append('fumble')
        else:
            player_hit_effects.append('player_hurt')

    if player_blocked:
        player_hit_effects.append('block')

    if player_heal and player_heal > 0:
        player_hit_effects.append('heal')

    if player_status:
        player_hit_effects.append('status_inflict')

    # --- Spell effects (sync with spell banner) ---
    if spell_cast:
        element = getattr(spell_cast, 'element', 'arcane') if spell_cast else None
        if element:
            spell_effects.append(f'spell_{element.lower()}')
        else:
            spell_effects.append('spell_arcane')

    if concentration_roll:
        passed = concentration_roll[4] if len(concentration_roll) > 4 else True
        if not passed:
            spell_effects.append('spell_fizzle')

    # --- Misc events (immediate) ---
    if sfx_event:
        effects.append(sfx_event)

    # Initiative roll: brief pre-battle cue — fires as soon as the combat
    # view mounts, before any attack/defend dice tumble.
    if has_init_roll:
        effects.append('init_roll')

    all_effects = effects + monster_hit_effects + player_hit_effects + spell_effects
    if not all_effects:
        return ""

    return f"""
    <script>
    (function() {{
        var immediateEffects = {json.dumps(effects)};
        var monsterHitEffects = {json.dumps(monster_hit_effects)};
        var playerHitEffects = {json.dumps(player_hit_effects)};
        var spellEffects = {json.dumps(spell_effects)};
        var monsterHitDelayMs = {monster_hit_delay};
        var playerHitDelayMs = {player_hit_delay};
        var spellDelayMs = {spell_delay_ms};
        try {{
            var AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) return;
            var ctx = new AC();

            var sfxMaster = ctx.createGain();
            sfxMaster.gain.value = 0.35;
            sfxMaster.connect(ctx.destination);

            // Variation helpers
            function vary(val, pct) {{
                return val * (1 + (Math.random() * 2 - 1) * pct);
            }}
            function pick(arr) {{ return arr[Math.floor(Math.random() * arr.length)]; }}

            // Shared noise buffer for NES-style noise channel
            var nBufLen = ctx.sampleRate;
            var nBuf = ctx.createBuffer(1, nBufLen, ctx.sampleRate);
            var nD = nBuf.getChannelData(0);
            for (var i = 0; i < nBufLen; i++) nD[i] = Math.random() * 2 - 1;

            // NES noise hit: kick (lowpass), snare (bandpass), hat (highpass)
            function noiseHit(filterFreq, duration, gain, startTime, type) {{
                duration = vary(duration, 0.12);
                gain = vary(gain, 0.1);
                var src = ctx.createBufferSource();
                src.buffer = nBuf;
                var filt = ctx.createBiquadFilter();
                filt.type = type || (filterFreq < 500 ? 'lowpass' : 'bandpass');
                filt.frequency.value = vary(filterFreq, 0.15);
                filt.Q.value = filterFreq < 500 ? 1 : vary(3, 0.3);
                var g = ctx.createGain();
                g.gain.setValueAtTime(gain, startTime);
                g.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
                src.connect(filt);
                filt.connect(g);
                g.connect(sfxMaster);
                src.start(startTime);
                src.stop(startTime + duration + 0.01);
            }}

            // Square wave pitch sweep (classic NES SFX)
            function sqSweep(startFreq, endFreq, duration, gain, startTime) {{
                startFreq = vary(startFreq, 0.1);
                endFreq = vary(endFreq, 0.1);
                duration = vary(duration, 0.1);
                gain = vary(gain, 0.1);
                var osc = ctx.createOscillator();
                osc.type = 'square';
                osc.frequency.setValueAtTime(startFreq, startTime);
                osc.frequency.exponentialRampToValueAtTime(Math.max(endFreq, 20), startTime + duration);
                osc.detune.value = (Math.random() * 16) - 8;
                var g = ctx.createGain();
                g.gain.setValueAtTime(gain, startTime);
                g.gain.setValueAtTime(gain * 0.6, startTime + duration * 0.7);
                g.gain.linearRampToValueAtTime(0.001, startTime + duration);
                osc.connect(g);
                g.connect(sfxMaster);
                osc.start(startTime);
                osc.stop(startTime + duration + 0.01);
            }}

            // Square wave blip (fixed pitch, instant on/off like NES)
            function sqBlip(freq, duration, gain, startTime) {{
                freq = vary(freq, 0.08);
                duration = vary(duration, 0.1);
                gain = vary(gain, 0.1);
                var osc = ctx.createOscillator();
                osc.type = 'square';
                osc.frequency.value = freq;
                osc.detune.value = (Math.random() * 16) - 8;
                var g = ctx.createGain();
                g.gain.setValueAtTime(gain, startTime);
                g.gain.setValueAtTime(gain * 0.6, startTime + duration * 0.8);
                g.gain.linearRampToValueAtTime(0.001, startTime + duration);
                osc.connect(g);
                g.connect(sfxMaster);
                osc.start(startTime);
                osc.stop(startTime + duration + 0.01);
            }}

            // Triangle blip (for bass/softer tones)
            function triBlip(freq, duration, gain, startTime) {{
                freq = vary(freq, 0.08);
                duration = vary(duration, 0.1);
                gain = vary(gain, 0.1);
                var osc = ctx.createOscillator();
                osc.type = 'triangle';
                osc.frequency.value = freq;
                var g = ctx.createGain();
                g.gain.setValueAtTime(gain, startTime);
                g.gain.linearRampToValueAtTime(0.001, startTime + duration);
                osc.connect(g);
                g.connect(sfxMaster);
                osc.start(startTime);
                osc.stop(startTime + duration + 0.01);
            }}

            // Chiptune arpeggio (square wave rapid notes)
            function chipArp(freqs, noteLen, gain, startTime) {{
                for (var i = 0; i < freqs.length; i++) {{
                    var jitter = (Math.random() * 0.008) - 0.004;
                    sqBlip(freqs[i], noteLen * 1.4, gain, startTime + i * noteLen + jitter);
                }}
            }}

            // Play a list of effects at a given base time
            function playEffects(effectList, baseTime) {{
            var offset = 0;
            for (var i = 0; i < effectList.length; i++) {{
                var fx = effectList[i];
                var st = baseTime + offset;

                switch(fx) {{
                    // === COMBAT ===
                    case 'weapon_hit':
                        // NES sword slash: fast square pitch drop + noise
                        sqSweep(pick([800, 900, 1000]), pick([150, 200, 250]), 0.08, 0.25, st);
                        noiseHit(pick([2000, 2500, 3000]), 0.06, 0.3, st);
                        break;

                    case 'crit_hit':
                        // Big impact: two-stage sweep + heavy noise
                        sqSweep(pick([1200, 1400, 1600]), pick([200, 250, 300]), 0.12, 0.35, st);
                        sqBlip(pick([1800, 2000, 2200]), 0.04, 0.2, st + 0.03);
                        noiseHit(pick([2500, 3000]), 0.1, 0.4, st);
                        noiseHit(150, 0.08, 0.25, st + 0.04);
                        break;

                    case 'player_hurt':
                        // Damage: descending square buzz
                        sqSweep(pick([500, 600, 700]), pick([80, 100, 120]), 0.15, 0.25, st);
                        noiseHit(pick([400, 500]), 0.08, 0.2, st + 0.02);
                        break;

                    case 'fumble':
                        // Sad whiff: slow descending square
                        sqSweep(pick([400, 450, 500]), pick([60, 80, 100]), 0.3, 0.15, st);
                        sqSweep(pick([300, 350]), pick([40, 50]), 0.2, 0.1, st + 0.1);
                        break;

                    case 'block':
                        // Metallic ting: high square blips
                        sqBlip(pick([2000, 2200, 2400]), 0.03, 0.3, st);
                        sqBlip(pick([1500, 1700, 1900]), 0.04, 0.2, st + 0.03);
                        noiseHit(pick([6000, 8000]), 0.03, 0.2, st);
                        break;

                    case 'monster_death':
                        // Multi-step descending: classic RPG enemy defeat
                        sqSweep(pick([600, 700, 800]), pick([80, 100]), 0.12, 0.2, st);
                        sqSweep(pick([300, 400]), pick([50, 60]), 0.15, 0.2, st + 0.1);
                        sqSweep(pick([150, 200]), pick([30, 40]), 0.2, 0.15, st + 0.2);
                        noiseHit(150, 0.15, 0.3, st + 0.05);
                        break;

                    case 'heal':
                        // Zelda-style ascending chime
                        var hS = pick([0.95, 1.0, 1.05]);
                        chipArp([392*hS, 494*hS, 587*hS, 784*hS], 0.06, 0.2, st);
                        triBlip(784*hS, 0.3, 0.15, st + 0.24);
                        break;

                    case 'status_inflict':
                        // Wobbling square (poison/debuff feel)
                        sqSweep(pick([500, 550, 600]), pick([200, 250]), 0.2, 0.15, st);
                        sqBlip(pick([300, 350, 400]), 0.08, 0.1, st + 0.1);
                        break;

                    // === SPELLS (element-specific, all chiptune) ===
                    case 'spell_fire':
                        // Rapid noise crackle + rising square
                        noiseHit(pick([1500, 2000, 2500]), 0.15, 0.35, st);
                        noiseHit(pick([3000, 4000]), 0.1, 0.2, st + 0.04);
                        sqSweep(pick([200, 250, 300]), pick([600, 800, 1000]), 0.2, 0.15, st);
                        break;

                    case 'spell_ice':
                        // High crystalline square blips
                        sqBlip(pick([1800, 2000, 2200]), 0.06, 0.2, st);
                        sqBlip(pick([2400, 2600, 2800]), 0.05, 0.15, st + 0.04);
                        sqBlip(pick([3000, 3200]), 0.04, 0.12, st + 0.08);
                        noiseHit(pick([8000, 10000]), 0.08, 0.15, st + 0.03);
                        break;

                    case 'spell_lightning':
                        // Sharp crack: fast noise + high square drop
                        noiseHit(pick([8000, 10000, 12000]), 0.03, 0.5, st);
                        sqSweep(pick([3000, 4000, 5000]), pick([200, 300]), 0.08, 0.35, st);
                        noiseHit(pick([2000, 3000]), 0.12, 0.25, st + 0.03);
                        break;

                    case 'spell_holy':
                        // Ascending major arpeggio + sustain
                        var hoS = pick([0.94, 1.0, 1.06]);
                        chipArp([523*hoS, 659*hoS, 784*hoS, 1047*hoS], 0.06, 0.2, st);
                        sqBlip(1047*hoS, 0.25, 0.15, st + 0.24);
                        break;

                    case 'spell_darkness': case 'spell_shadow':
                        // Low rumbling square + noise
                        sqSweep(pick([120, 140, 160]), pick([40, 50, 60]), 0.35, 0.25, st);
                        noiseHit(pick([200, 300]), 0.2, 0.2, st + 0.03);
                        sqBlip(pick([80, 90, 100]), 0.15, 0.15, st + 0.15);
                        break;

                    case 'spell_poison': case 'spell_acid':
                        // Bubbling: alternating square blips
                        var pF = pick([300, 350, 400]);
                        sqBlip(pF, 0.05, 0.15, st);
                        sqBlip(pF * 0.8, 0.05, 0.12, st + 0.06);
                        sqBlip(pF * 1.1, 0.05, 0.15, st + 0.12);
                        sqBlip(pF * 0.75, 0.05, 0.12, st + 0.18);
                        noiseHit(pick([600, 800]), 0.1, 0.1, st + 0.05);
                        break;

                    case 'spell_arcane':
                        // Quick square arpeggio up-down
                        var aF = pick([600, 660, 720]);
                        sqBlip(aF, 0.04, 0.2, st);
                        sqBlip(aF * 1.33, 0.04, 0.18, st + 0.04);
                        sqBlip(aF * 1.5, 0.04, 0.15, st + 0.08);
                        sqBlip(aF * 1.33, 0.04, 0.12, st + 0.12);
                        break;

                    case 'spell_earth':
                        // Low thud: triangle bass + noise
                        triBlip(pick([60, 70, 80]), 0.2, 0.3, st);
                        noiseHit(150, 0.12, 0.35, st);
                        sqSweep(pick([200, 250]), pick([80, 100]), 0.15, 0.15, st + 0.05);
                        break;

                    case 'spell_wind': case 'spell_air':
                        // Whoosh: noise sweep + rising square
                        noiseHit(pick([3000, 4000, 5000]), 0.25, 0.3, st, 'highpass');
                        sqSweep(pick([400, 500, 600]), pick([1200, 1500, 1800]), 0.2, 0.1, st);
                        break;

                    case 'spell_water':
                        // Splash: noise + warbling square
                        noiseHit(pick([2000, 2500]), 0.12, 0.25, st);
                        sqBlip(pick([800, 900, 1000]), 0.06, 0.15, st + 0.03);
                        sqBlip(pick([600, 700]), 0.06, 0.12, st + 0.08);
                        sqBlip(pick([900, 1000]), 0.05, 0.1, st + 0.13);
                        break;

                    case 'spell_force': case 'spell_psychic':
                        // Square ping-pong
                        var fF = pick([400, 440, 490]);
                        sqSweep(fF, fF * 2, 0.1, 0.25, st);
                        sqSweep(fF * 2, fF, 0.1, 0.2, st + 0.1);
                        sqBlip(fF * 1.5, 0.06, 0.15, st + 0.2);
                        break;

                    case 'spell_fizzle':
                        // Sad descending square + noise puff
                        sqSweep(pick([600, 700, 800]), pick([80, 100, 120]), 0.35, 0.2, st);
                        noiseHit(pick([400, 500]), 0.15, 0.15, st + 0.1);
                        break;

                    // === EXPLORATION / UI ===
                    case 'chest_open':
                        // Zelda chest jingle
                        var cS = pick([0.95, 1.0, 1.05]);
                        chipArp([523*cS, 659*cS, 784*cS, 1047*cS, 1319*cS], 0.055, 0.2, st);
                        sqBlip(1319*cS, 0.2, 0.15, st + 0.28);
                        break;

                    case 'level_up':
                        // Classic RPG fanfare arpeggio
                        var lS = pick([0.95, 1.0, 1.05]);
                        chipArp([262*lS, 330*lS, 392*lS, 523*lS, 659*lS, 784*lS], 0.07, 0.22, st);
                        sqBlip(784*lS, 0.35, 0.18, st + 0.42);
                        triBlip(131*lS, 0.4, 0.15, st + 0.42);
                        break;

                    case 'achievement':
                        // Bright fanfare + high sustain
                        var aS = pick([0.95, 1.0, 1.05]);
                        chipArp([523*aS, 659*aS, 784*aS, 1047*aS], 0.06, 0.2, st);
                        sqBlip(1047*aS, 0.2, 0.18, st + 0.24);
                        sqBlip(1319*aS, 0.25, 0.15, st + 0.34);
                        break;

                    case 'buy':
                        // Mario-style coin: two quick square pips ascending
                        var bF = pick([750, 800, 860]);
                        sqBlip(bF, 0.04, 0.2, st);
                        sqBlip(bF * 1.5, 0.08, 0.18, st + 0.04);
                        break;

                    case 'sell':
                        // Reverse coin: descending pips
                        var sF = pick([1100, 1200, 1300]);
                        sqBlip(sF, 0.04, 0.2, st);
                        sqBlip(sF * 0.67, 0.08, 0.18, st + 0.04);
                        break;

                    case 'init_roll':
                        // Pre-battle cue: single bell-like triangle tone
                        // with a short airy noise "fwoosh" — signals combat
                        // is about to start, distinct from any hit SFX.
                        triBlip(pick([660, 700, 740]), 0.35, 0.22, st);
                        triBlip(pick([988, 1046, 1108]), 0.3, 0.14, st + 0.05);
                        noiseHit(pick([4000, 5000]), 0.12, 0.18, st, 'highpass');
                        break;
                }}
                offset += 0.05;
            }}
            }}

            // Immediate effects (chest, buy, sell, achievement, level up)
            var t = ctx.currentTime + 0.05;
            if (immediateEffects.length) playEffects(immediateEffects, t);

            // Spell effects (synced with spell banner appearance)
            if (spellEffects.length) {{
                setTimeout(function() {{
                    playEffects(spellEffects, ctx.currentTime);
                }}, spellDelayMs);
            }}

            // Monster hit effects (synced with monster panel shake)
            if (monsterHitEffects.length) {{
                if (monsterHitDelayMs > 0) {{
                    setTimeout(function() {{
                        playEffects(monsterHitEffects, ctx.currentTime);
                    }}, monsterHitDelayMs);
                }} else {{
                    playEffects(monsterHitEffects, t);
                }}
            }}

            // Player hit effects (synced with player panel shake)
            if (playerHitEffects.length) {{
                if (playerHitDelayMs > 0) {{
                    setTimeout(function() {{
                        playEffects(playerHitEffects, ctx.currentTime);
                    }}, playerHitDelayMs);
                }} else {{
                    playEffects(playerHitEffects, t + 0.2);
                }}
            }}

        }} catch(e) {{
            // Web Audio not available — silent fallback
        }}
    }})();
    </script>
    """


def health_bar(current, maximum, width=20):
    filled = int((current / maximum) * width) if maximum > 0 else 0
    filled = min(filled, width)  # Cap at width
    bar = "[" + "#" * filled + "-" * (width - filled) + "]"
    # Abbreviate large numbers to keep display compact
    if maximum >= 1000:
        cur_str = f"{current//1000}k" if current >= 1000 else str(current)
        max_str = f"{maximum//1000}k"
    else:
        cur_str = str(current)
        max_str = str(maximum)
    return f"{bar} {cur_str}/{max_str}"

def mana_bar(current, maximum, width=20):
    if maximum == 0:
        return " "
    filled = int((current / maximum) * width)
    filled = min(filled, width)  # Cap at width
    bar = "[" + "#" * filled + "-" * (width - filled) + "]"
    # Abbreviate large numbers to keep display compact
    if maximum >= 1000:
        cur_str = f"{current//1000}k" if current >= 1000 else str(current)
        max_str = f"{maximum//1000}k"
    else:
        cur_str = str(current)
        max_str = str(maximum)
    return f"{bar} {cur_str}/{max_str}"


def generate_hp_drain_js(monster_cur_hp, monster_max_hp, player_cur_hp, player_max_hp,
                          monster_dmg, player_dmg, player_heal, has_init_roll):
    """Schedule HP bar text updates to land at the damage-float timing.

    The combat views render HP bars with pre-round HP so the bar
    doesn't drop until the damage animation plays.  This helper emits
    a script that swaps the bar innerHTML to the post-round HP at
    MONSTER_DMG_DELAY (1.3s) / PLAYER_DMG_DELAY (3.2s) — the same
    moment the damage float appears and the panel shakes.

    The HP bar <span> tags in the combat templates need matching IDs:
      #monster_hp_bar  (in monster_combat_html)
      #player_hp_bar   (in player_combat_html)
    """
    if not (monster_dmg or player_dmg or player_heal):
        return ""
    init_offset = 1000 if has_init_roll else 0
    m_delay = 1300 + init_offset
    p_delay = 3200 + init_offset
    # Compute post-damage bars in both sizes used across templates.
    m_bar_10 = health_bar(monster_cur_hp, monster_max_hp, width=10)
    p_bar_10 = health_bar(player_cur_hp, player_max_hp, width=10)
    p_bar_15 = health_bar(player_cur_hp, player_max_hp, width=15)
    parts = [
        '<script>(function(){'
        'function up(sel,h){var es=document.querySelectorAll(sel);'
        'for(var i=0;i<es.length;i++)es[i].innerHTML=h;}'
    ]
    if monster_dmg > 0:
        parts.append(
            f'setTimeout(function(){{up(".monster-hp-bar",{json.dumps(m_bar_10)});}},{m_delay});'
        )
    if player_dmg > 0 or player_heal > 0:
        parts.append(
            f'setTimeout(function(){{'
            f'up(".player-hp-bar",{json.dumps(p_bar_10)});'
            f'up(".player-hp-bar-wide",{json.dumps(p_bar_15)});'
            f'}},{p_delay});'
        )
    parts.append('})();</script>')
    return ''.join(parts)


def generate_damage_float_js(monster_name, monster_dmg, player_dmg, player_blocked=False,
                              player_status=None, monster_status=None, player_heal=0,
                              monster_badge=None, player_badge=None, spell_element=None,
                              spell_level=0):
    """Generate floating damage/heal/status text above combat sprites.

    Injects absolutely-positioned divs into the sprite wrapper elements.
    Uses a JS-driven animation loop (requestAnimationFrame) so it works
    reliably in Toga/WKWebView without requiring <style> blocks in <body>.

    monster_badge / player_badge: optional short string (e.g. "HUNTER!",
    "HOLY +8", "RAID!", "HALVED!") floated in small yellow text right
    before the damage number.
    """
    monster_canvas_id = "ms_" + "".join(ch if ch.isalnum() else "_" for ch in monster_name)

    # --- Determine player text / color ---
    if player_dmg > 0:
        p_text = f"-{player_dmg}"
        p_color = "#FF5252"
    elif player_blocked:
        p_text = "Blocked"
        p_color = "#69F0AE"
    elif player_heal > 0:
        p_text = f"+{player_heal}"
        p_color = "#69F0AE"
    elif player_status:
        p_text = str(player_status).replace('"', '').replace("'", '').replace('<', '').replace('>', '')[:12]
        p_color = "#FFB74D"
    else:
        p_text = None
        p_color = None

    # --- Determine monster text / color ---
    if monster_dmg > 0:
        m_text = f"-{monster_dmg}"
        # Use element color if a spell was cast, otherwise standard red
        m_color = ELEMENT_COLORS.get(spell_element, "#FF5252") if spell_element else "#FF5252"
    elif monster_status:
        m_text = str(monster_status).replace('"', '').replace("'", '').replace('<', '').replace('>', '')[:12]
        m_color = "#FFB74D"
    else:
        m_text = None
        m_color = None

    # --- Secondary heal float (when player both heals AND takes damage) ---
    h_text = None
    h_color = None
    if player_heal > 0 and player_dmg > 0:
        h_text = f"+{player_heal}"
        h_color = "#69F0AE"

    # Nothing to show
    if m_text is None and p_text is None:
        return ""

    # Build JS calls for each float.  The showFloat function:
    #  1. Creates a div with all styles inline
    #  2. Appends it to the wrapper (which has position:relative)
    #  3. Animates it upward with fading via requestAnimationFrame
    #  4. delay_ms parameter staggers multiple notifications
    # -----------------------------------------------------------------
    # SEQUENCED OPPOSED-DICE COMBAT TIMELINE
    # (matches generate_dice_roll_js):
    #   0ms     Player ATTACK dice tumbles
    #   600ms   Monster DEFEND dice tumbles
    #   1000ms  Both rolls landed
    #   1300ms  Monster damage float appears (exchange resolved)
    #   1900ms  Monster ATTACK dice tumbles
    #   2500ms  Player DEFEND dice tumbles
    #   2900ms  Both rolls landed
    #   3200ms  Player damage float appears
    # -----------------------------------------------------------------
    # Damage float delays shift when initiative dice are also showing
    _init_offset = 1000 if (gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)) else 0
    MONSTER_DMG_DELAY = 1300 + _init_offset  # After player attack exchange resolves
    PLAYER_DMG_DELAY  = 3200 + _init_offset  # After monster attack exchange resolves

    def _escape(s):
        return str(s).replace('"', '').replace("'", '').replace('<', '').replace('>', '')[:18]

    float_calls = []
    # Badge floats appear 150ms BEFORE the damage number, slightly offset
    if monster_badge and m_text:
        bx = _escape(monster_badge)
        float_calls.append(
            f'showFloat("{monster_canvas_id}_wrap","{bx}","#FFD54F",-20,{MONSTER_DMG_DELAY - 150});'
        )
    # Haptic patterns — fired at the SAME delay as the panel shake so
    # the phone buzz lands exactly when the damage number appears.
    # Normal hits don't vibrate (would be too much on every attack);
    # only crits and high-level spells (L3+) get haptic feedback.
    def _vibe_pattern(badge, is_hit_spell):
        if badge == 'CRIT':
            return '[80,40,180]'       # strong two-buzz for crits
        if is_hit_spell and spell_level >= 4:
            return '[120,60,80,40,180]'  # dramatic pulse for L4-5 spells
        if is_hit_spell and spell_level >= 3:
            return '[100]'             # single buzz for L3 spells
        return None

    if m_text:
        # Shake the monster panel only on actual damage (not status effects)
        if monster_dmg > 0:
            float_calls.append(f'shakePanel("monster_panel",{MONSTER_DMG_DELAY});')
            _vm = _vibe_pattern(monster_badge, spell_element is not None)
            if _vm:
                float_calls.append(
                    f'setTimeout(function(){{try{{if(navigator.vibrate)navigator.vibrate({_vm});}}catch(e){{}}}},{MONSTER_DMG_DELAY});'
                )
        float_calls.append(
            f'showFloat("{monster_canvas_id}_wrap","{m_text}","{m_color}",0,{MONSTER_DMG_DELAY});'
        )
    if player_badge and p_text:
        bx = _escape(player_badge)
        float_calls.append(
            f'showFloat("player_sprite_wrap","{bx}","#FFD54F",-20,{PLAYER_DMG_DELAY - 150});'
        )
    if p_text:
        # Shake the player panel only on actual damage (not blocks/heals/status)
        if player_dmg > 0:
            float_calls.append(f'shakePanel("player_panel",{PLAYER_DMG_DELAY});')
            _vp = _vibe_pattern(player_badge, False)
            if _vp:
                float_calls.append(
                    f'setTimeout(function(){{try{{if(navigator.vibrate)navigator.vibrate({_vp});}}catch(e){{}}}},{PLAYER_DMG_DELAY});'
                )
        float_calls.append(
            f'showFloat("player_sprite_wrap","{p_text}","{p_color}",0,{PLAYER_DMG_DELAY});'
        )
    if h_text:
        float_calls.append(
            f'showFloat("player_sprite_wrap","{h_text}","{h_color}",24,{PLAYER_DMG_DELAY + 200});'
        )

    js = (
        '<script>(function(){'
        # -----------------------------------------------------------------
        # showFloat(wrapperID, text, color, xOffset, delayMs)
        #
        # TUNING KNOBS (search for these values to adjust):
        #   FLOAT_TOTAL_FRAMES  - total animation frames (~60fps).
        #                         Higher = longer on screen. Current: 40
        #   FLOAT_PX_PER_FRAME  - pixels moved upward each frame.
        #                         Lower = slower rise. Current: 1.2
        #   delayMs             - ms before this float starts animating.
        #                         Set via FLOAT_DELAY_MS in Python above.
        # -----------------------------------------------------------------
        'function showFloat(wid,txt,clr,ox,delayMs){'
        'setTimeout(function(){'
        'var w=document.getElementById(wid);'
        'if(!w)return;'
        'var e=document.createElement("div");'
        'e.textContent=txt;'
        'var s=e.style;'
        's.position="absolute";'
        's.left=(w.offsetWidth/2+ox)+"px";'
        's.top="0px";'
        's.color=clr;'
        's.fontSize="16px";'
        's.fontWeight="bold";'
        's.fontFamily="monospace";'
        's.pointerEvents="none";'
        's.zIndex="99999";'
        's.whiteSpace="nowrap";'
        's.textShadow="0 0 4px #000,0 0 4px #000";'
        's.transform="translateX(-50%)";'
        's.transition="none";'
        's.overflow="visible";'
        's.maxWidth="none";'
        'w.appendChild(e);'
        'var f=0;'
        'var total=40;'     # FLOAT_TOTAL_FRAMES - raise to keep text visible longer
        'var pxPerFrame=1.2;'  # FLOAT_PX_PER_FRAME - lower = slower rise
        'function step(){'
        'f++;'
        'e.style.top=(-f*pxPerFrame)+"px";'
        'e.style.opacity=""+(1-f/total);'
        'if(f<total){requestAnimationFrame(step);}'
        'else if(e.parentNode){e.parentNode.removeChild(e);}'
        '}'
        'requestAnimationFrame(step);'
        '},delayMs||0);'
        '}'
        # shakePanel(panelId, delayMs) — kinetic impact feedback on damage
        'function shakePanel(pid,delayMs){'
        'setTimeout(function(){'
        'var p=document.getElementById(pid);'
        'if(!p)return;'
        'p.style.animation="none";'
        'void p.offsetWidth;'  # force reflow so animation restarts
        'p.style.animation="panelShake 0.35s ease-out";'
        '},delayMs||0);'
        '}'
        + ''.join(float_calls)
        + '})();</script>'
    )
    return js


def _spell_visual_element(spell):
    """Derive the visual element type for a spell's animations.

    Damage spells use their damage_type directly. Buff/debuff/heal spells
    map to thematically appropriate visual elements:
      attack_boost → Fire (orange), defense_boost → Holy (gold),
      heal_over_time → Healing (green), time_stop → Ice (frozen),
      remove_status → Light (cleansing), healing → Healing.
    """
    if not spell:
        return 'Physical'
    stype = getattr(spell, 'spell_type', '')
    if stype == 'healing':
        return 'Healing'
    elif stype in ('add_status_effect', 'debuff_target'):
        etype = getattr(spell, 'status_effect_type', '')
        return {'attack_boost': 'Fire', 'defense_boost': 'Holy',
                'damage_reduction': 'Holy', 'heal_over_time': 'Healing',
                'paralysis': 'Ice', 'time_stop': 'Ice'}.get(etype, 'Light')
    elif stype == 'remove_status':
        return 'Light'
    return getattr(spell, 'damage_type', 'Physical')


# ============================================================
# ELEMENT COLOR MAP — used for spell damage floats, banners, and screen tints
# ============================================================
ELEMENT_COLORS = {
    'Fire': '#FF6B35',
    'Ice': '#4FC3F7',
    'Lightning': '#FFD740',
    'Wind': '#FFD740',       # same as Lightning (air element)
    'Water': '#29B6F6',
    'Earth': '#8D6E63',
    'Light': '#FFF9C4',
    'Holy': '#FFD700',
    'Darkness': '#CE93D8',
    'Shadow': '#CE93D8',
    'Psionic': '#E040FB',
    'Demonic': '#FF1744',
    'Poison': '#76FF03',      # toxic neon green
    'Acid': '#76FF03',
    'Physical': '#FF5252',
    'Healing': '#69F0AE',
}

# Element screen tint colors (used for brief flash overlay)
ELEMENT_TINTS = {
    'Fire': 'rgba(255,107,53,0.25)',
    'Ice': 'rgba(79,195,247,0.25)',
    'Lightning': 'rgba(255,255,255,0.4)',   # bright white flash
    'Wind': 'rgba(255,215,64,0.2)',
    'Water': 'rgba(41,182,246,0.2)',
    'Earth': 'rgba(141,110,99,0.2)',
    'Light': 'rgba(255,249,196,0.3)',
    'Holy': 'rgba(255,215,0,0.3)',
    'Darkness': 'rgba(206,147,216,0.25)',
    'Shadow': 'rgba(206,147,216,0.25)',
    'Psionic': 'rgba(224,64,251,0.25)',
    'Demonic': 'rgba(255,23,68,0.25)',
    'Poison': 'rgba(118,255,3,0.25)',
    'Acid': 'rgba(118,255,3,0.25)',
    'Healing': 'rgba(105,240,174,0.2)',
}


def generate_spell_cast_js(spell):
    """Generate spell casting animation: banner + screen tint.

    Plays BEFORE the damage/healing float sequence.

    Layer 2 — Banner: the spell name flashes across the combat area in the
    element's color with letter-spacing and glow. Fades in, holds, fades out.

    Layer 3 — Screen tint: a brief color wash over #content-area matching
    the spell's element. Lightning is a sharp white flash, fire is a warm
    orange wash, ice is cool blue, etc.
    """
    if not spell:
        return ""
    name = spell.name.replace('"', '').replace("'", '').replace('<', '').replace('>', '')
    dtype = _spell_visual_element(spell)
    color = ELEMENT_COLORS.get(dtype, '#FFFFFF')
    tint = ELEMENT_TINTS.get(dtype, 'rgba(255,255,255,0.15)')
    # Lightning gets a shorter, sharper flash
    # Scale visual intensity with spell level (0-5)
    lvl = getattr(spell, 'level', 0)
    # Banner font scales: 14px at L0, up to 28px at L5
    banner_size = 14 + lvl * 3
    # Banner letter spacing scales: 4px at L0, up to 10px at L5
    banner_spacing = 4 + lvl
    # Extra glow layers for high-level spells
    banner_glow = '0 0 12px ' + color + ',0 0 4px #000'
    if lvl >= 2:
        banner_glow += ',0 0 24px ' + color
    if lvl >= 4:
        banner_glow += ',0 0 48px ' + color + ',0 0 64px ' + color
    # Banner hold time: 0.4s at L0, 0.9s at L5
    banner_hold = 400 + lvl * 100
    # Screen tint intensity scales with level
    tint_base_opacity = 0.15 + lvl * 0.06
    tint_duration = '120' if dtype in ('Lightning', 'Wind') else str(300 + lvl * 60)

    # NOTE: haptic on high-level spells is triggered by
    # generate_damage_float_js at the moment of damage panel shake,
    # not at spell-banner appearance, so the buzz lands with the impact.

    return (
        '<script>(function(){'
        # Layer 2: Spell name banner (scaled with level)
        'var bn=document.createElement("div");'
        'bn.style.cssText="position:fixed;top:38%;left:50%;transform:translate(-50%,-50%) scale(0.7);'
        'z-index:99999;text-align:center;pointer-events:none;opacity:0;'
        'font-family:monospace;font-size:' + str(banner_size) + 'px;font-weight:bold;'
        'letter-spacing:' + str(banner_spacing) + 'px;'
        'text-transform:uppercase;'
        'color:' + color + ';'
        'text-shadow:' + banner_glow + ';";'
        'bn.textContent="' + name + '";'
        'document.body.appendChild(bn);'
        # Animate: scale up + fade in, hold, fade out
        'bn.style.transition="opacity 0.3s ease-out,transform 0.3s ease-out";'
        'setTimeout(function(){bn.style.opacity="1";bn.style.transform="translate(-50%,-50%) scale(1)";},50);'
        'setTimeout(function(){'
        'bn.style.transition="opacity 0.4s ease-in,transform 0.4s ease-in";'
        'bn.style.opacity="0";'
        'bn.style.transform="translate(-50%,-50%) scale(1.1) translateY(-10px)";'
        '},' + str(banner_hold) + ');'
        'setTimeout(function(){if(bn.parentNode)bn.parentNode.removeChild(bn);},1100);'

        # Layer 3: Screen tint flash
        # Screen tint: level scales max opacity from 0.6 (L0) to 1.0 (L5)
        'var tint=document.createElement("div");'
        'tint.style.cssText="position:fixed;top:0;left:0;right:0;bottom:0;'
        'z-index:99998;pointer-events:none;'
        'background:' + tint + ';opacity:0;transition:opacity 0.15s ease-out;";'
        'document.body.appendChild(tint);'
        'setTimeout(function(){tint.style.opacity="' + str(min(1.0, 0.6 + lvl * 0.08)) + '";},100);'
        'setTimeout(function(){tint.style.transition="opacity 0.3s ease-in";tint.style.opacity="0";'
        '},' + tint_duration + ');'
        'setTimeout(function(){if(tint.parentNode)tint.parentNode.removeChild(tint);},800);'

        # Layer 3b: L4+ screen distortion via CSS filters (brief, dramatic)
        + (
        'var ca=document.getElementById("content-area");'
        'if(ca&&' + str(lvl) + '>=4){'
        'setTimeout(function(){'
        'ca.style.transition="filter 0.1s";'
        + {
            'Fire': 'ca.style.filter="sepia(1) brightness(1.5)";',            # scorched amber
            'Demonic': 'ca.style.filter="sepia(1) saturate(3) hue-rotate(330deg)";',  # blood red hellscape
            'Ice': 'ca.style.filter="brightness(1.8) saturate(0.2)";',        # frozen white-out
            'Water': 'ca.style.filter="blur(2px) brightness(0.8)";',          # underwater murk
            'Holy': 'ca.style.filter="brightness(2) contrast(0.5)";',         # blinding divine light
            'Light': 'ca.style.filter="brightness(2) contrast(0.5)";',
            'Earth': 'ca.style.filter="blur(3px)";',                          # earthquake blur
            'Darkness': 'ca.style.filter="invert(1) brightness(0.8)";',       # void flash
            'Shadow': 'ca.style.filter="invert(1) brightness(0.8)";',
            'Psionic': 'ca.style.filter="hue-rotate(180deg)";',               # psychedelic
            'Poison': 'ca.style.filter="hue-rotate(90deg) saturate(2)";',       # toxic green shift
            'Acid': 'ca.style.filter="hue-rotate(90deg) saturate(2)";',
            'Lightning': 'ca.style.filter="brightness(2.5)";',                # white-out flash
            'Wind': 'ca.style.filter="brightness(2.5)";',
        }.get(dtype, 'ca.style.filter="saturate(2)";')                    # default: oversaturate
        + 'setTimeout(function(){ca.style.filter="none";},200);'
        '},300);}'
        if lvl >= 4 else ''
        )

        + '})();</script>'
    )


def generate_spell_particles_js(spell):
    """Generate element-specific particle effects via a temporary canvas overlay.

    Creates a full-screen canvas, spawns particles with per-element physics,
    animates them via requestAnimationFrame, and removes the canvas when done.
    Canvas rendering is dramatically faster than DOM particles on mobile.

    Scales dramatically with spell level:
      L0: 20-30 particles, small, 1 burst
      L3: 50-70 particles, medium, 2 bursts
      L5: 80-120 particles, large glow, 3 bursts (Armageddon-tier)
    """
    if not spell:
        return ""
    dtype = _spell_visual_element(spell)
    color = ELEMENT_COLORS.get(dtype, '#FFFFFF')

    lvl = getattr(spell, 'level', 0)

    # Base configs per element (count, speed, style)
    configs = {
        'Fire':      (20, 3.0, 'rise'),
        'Ice':       (18, 2.0, 'fall'),
        'Lightning': (25, 7.0, 'burst'),
        'Wind':      (22, 6.0, 'burst'),
        'Water':     (18, 3.5, 'splash'),
        'Earth':     (15, 4.5, 'shatter'),
        'Holy':      (20, 1.5, 'radiate'),
        'Light':     (20, 1.5, 'radiate'),
        'Darkness':  (18, 2.5, 'implode'),
        'Shadow':    (18, 2.5, 'implode'),
        'Psionic':   (18, 2.0, 'spiral'),
        'Poison':    (22, 3.0, 'splash'),
        'Acid':      (22, 3.0, 'splash'),
        'Demonic':   (20, 4.0, 'burst'),
        'Healing':   (18, 2.0, 'rise'),
        'Physical':  (15, 4.0, 'burst'),
    }
    base_count, base_speed, style = configs.get(dtype, (20, 3.0, 'burst'))

    # Scale with spell level: L0 = base, L5 = ~3x particles, 1.5x speed, bigger glow
    count = int(base_count * (1 + lvl * 0.4))    # L0=20, L3=44, L5=60
    speed = base_speed * (1 + lvl * 0.1)          # L0=3.0, L5=4.5
    glow_mult = 1 + lvl * 0.5                     # glow radius multiplier
    sz_min = 2 + lvl * 0.5                         # L0=2, L5=4.5
    sz_max = 4 + lvl * 1.0                         # L0=4, L5=9 (big chunky particles!)
    life_bonus = lvl * 4                            # longer-lived particles at high levels
    # Multi-burst: L0-2 = 1 burst, L3-4 = 2 bursts, L5 = 3 bursts
    num_bursts = 1 + (1 if lvl >= 3 else 0) + (1 if lvl >= 5 else 0)
    burst_delay = 250                               # ms between bursts

    target_id = 'player_panel' if dtype == 'Healing' else 'monster_panel'

    return (
        '<script>(function(){'
        'var numBursts=' + str(num_bursts) + ';'
        'var burstDelay=' + str(burst_delay) + ';'

        'for(var burst=0;burst<numBursts;burst++){'
        '(function(burstIdx){'
        'setTimeout(function(){'
        'var tgt=document.getElementById("' + target_id + '");'
        'if(!tgt)return;'
        'var rect=tgt.getBoundingClientRect();'
        'var cx=rect.left+rect.width/2;'
        'var cy=rect.top+rect.height/2;'

        # Create full-screen canvas overlay (one per burst)
        'var cvs=document.createElement("canvas");'
        'cvs.width=window.innerWidth;cvs.height=window.innerHeight;'
        'cvs.style.cssText="position:fixed;top:0;left:0;z-index:99997;pointer-events:none;";'
        'document.body.appendChild(cvs);'
        'var ctx=cvs.getContext("2d");'

        # Parse the element color to RGB for canvas drawing
        'var tc=document.createElement("div");tc.style.color="' + color + '";'
        'document.body.appendChild(tc);'
        'var cs=getComputedStyle(tc).color;document.body.removeChild(tc);'
        'var rgb=cs.match(/\\d+/g).map(Number);'

        # Spawn particles — scaled with level
        'var particles=[];'
        'var count=' + str(count) + ';'
        'var spd=' + str(speed) + ';'
        'var sty="' + style + '";'
        'var elem="' + dtype + '";'
        'var szMin=' + str(sz_min) + ',szMax=' + str(sz_max) + ';'
        'var glowMult=' + str(glow_mult) + ';'
        'var lifeBonus=' + str(life_bonus) + ';'
        'for(var i=0;i<count;i++){'
        'var angle=Math.random()*Math.PI*2;'
        'var v=spd*(0.5+Math.random());'
        'var px=cx,py=cy,vx,vy;'
        'var sz=szMin+Math.random()*(szMax-szMin);'
        # Level-scaled spawn spread: particles scatter from a wider area at higher levels
        'var spread=' + str(10 + lvl * 12) + ';'

        'if(sty==="rise"){px=cx+(Math.random()-0.5)*spread;vx=(Math.random()-0.5)*3;vy=-v;}'
        'else if(sty==="fall"){px=cx+(Math.random()-0.5)*spread*1.5;py=cy-spread*0.5-Math.random()*20;vx=(Math.random()-0.5)*2;vy=v*0.7;}'
        'else if(sty==="burst"){vx=Math.cos(angle)*v;vy=Math.sin(angle)*v;}'
        'else if(sty==="splash"){vx=Math.cos(angle)*v;vy=Math.sin(angle)*v*0.5+1;}'
        'else if(sty==="shatter"){vx=Math.cos(angle)*v;vy=Math.sin(angle)*v*0.3+2;}'
        'else if(sty==="radiate"){vx=Math.cos(angle)*v*0.6;vy=Math.sin(angle)*v*0.6;}'
        'else if(sty==="implode"){'
        'var d=30+Math.random()*50;px=cx+Math.cos(angle)*d;py=cy+Math.sin(angle)*d;'
        'vx=-Math.cos(angle)*v*0.8;vy=-Math.sin(angle)*v*0.8;}'
        'else if(sty==="spiral"){'
        'var r=10+Math.random()*25;px=cx+Math.cos(angle)*r;py=cy+Math.sin(angle)*r;'
        'vx=Math.cos(angle+1.5)*v;vy=Math.sin(angle+1.5)*v;}'
        'else{vx=Math.cos(angle)*v;vy=Math.sin(angle)*v;}'

        'var grav=(sty==="splash"||sty==="shatter")?0.15:0;'
        # Generate random crystal vertices for ice/earth (4-6 pointed shards)
        'var verts=null;'
        'if(elem==="Ice"||elem==="Earth"){'
        'var nv=4+Math.floor(Math.random()*3);'
        'verts=[];'
        'for(var vi=0;vi<nv;vi++){'
        'var va=vi/nv*Math.PI*2+Math.random()*0.5;'
        'var vr=0.5+Math.random()*0.8;'  # random radius multiplier per vertex
        'verts.push({a:va,r:vr});'
        '}}'
        'particles.push({x:px,y:py,ox:cx,oy:cy,vx:vx,vy:vy,sz:sz,life:0,max:22+lifeBonus+Math.floor(Math.random()*20),grav:grav,verts:verts,prevX:px,prevY:py});'
        '}'

        # Animate on canvas
        'var running=true;'
        'function frame(){'
        'ctx.clearRect(0,0,cvs.width,cvs.height);'
        'var alive=0;'
        'for(var i=0;i<particles.length;i++){'
        'var p=particles[i];'
        'if(p.life>=p.max)continue;'
        'alive++;p.life++;'
        'p.vx*=0.97;p.vy+=p.grav;'
        'p.x+=p.vx;p.y+=p.vy;'
        'var alpha=1-p.life/p.max;'
        'var clr="rgba("+rgb[0]+","+rgb[1]+","+rgb[2]+","+alpha+")";'
        'ctx.shadowBlur=p.sz*3*glowMult;'
        'ctx.shadowColor="rgba("+rgb[0]+","+rgb[1]+","+rgb[2]+","+alpha*0.6+")";'

        # ===== LIGHTNING: zig-zag bolts =====
        'if((elem==="Lightning"||elem==="Wind")&&p.life<p.max*0.7){'
        'ctx.beginPath();ctx.moveTo(p.ox,p.oy);'
        'var dx=p.x-p.ox,dy=p.y-p.oy;'
        'var segs=4+Math.floor(Math.random()*3);'
        'for(var s=1;s<=segs;s++){var t=s/segs;var j=(1-t)*12*glowMult;'
        'ctx.lineTo(p.ox+dx*t+(Math.random()-0.5)*j,p.oy+dy*t+(Math.random()-0.5)*j);}'
        'ctx.strokeStyle=clr;ctx.lineWidth=p.sz*0.6;ctx.stroke();'
        'ctx.beginPath();ctx.arc(p.x,p.y,p.sz*0.5,0,Math.PI*2);'
        'ctx.fillStyle="rgba(255,255,255,"+alpha*0.8+")";ctx.fill();'

        # ===== FIRE: circle + ember trail =====
        '}else if(elem==="Fire"||elem==="Demonic"){'
        'ctx.beginPath();ctx.moveTo(p.prevX,p.prevY);ctx.lineTo(p.x,p.y);'
        'ctx.strokeStyle="rgba("+rgb[0]+","+rgb[1]+","+rgb[2]+","+alpha*0.4+")";'
        'ctx.lineWidth=p.sz*0.8;ctx.stroke();'
        'ctx.beginPath();ctx.arc(p.x,p.y,p.sz,0,Math.PI*2);ctx.fillStyle=clr;ctx.fill();'

        # ===== ICE / EARTH: random crystal/rock shards =====
        '}else if(p.verts){'
        'ctx.beginPath();'
        'for(var vi=0;vi<p.verts.length;vi++){'
        'var vt=p.verts[vi];var vx2=p.x+Math.cos(vt.a)*p.sz*vt.r;var vy2=p.y+Math.sin(vt.a)*p.sz*vt.r;'
        'if(vi===0)ctx.moveTo(vx2,vy2);else ctx.lineTo(vx2,vy2);}'
        'ctx.closePath();ctx.fillStyle=clr;ctx.fill();'
        'if(elem==="Ice"){ctx.strokeStyle="rgba(255,255,255,"+alpha*0.5+")";ctx.lineWidth=0.5;ctx.stroke();}'

        # ===== HOLY / LIGHT: starburst rays =====
        '}else if(elem==="Holy"||elem==="Light"){'
        'var rl=p.sz*1.5;'
        'ctx.strokeStyle=clr;ctx.lineWidth=1;'
        'for(var ri=0;ri<4;ri++){var ra=ri*Math.PI/4+p.life*0.1;'
        'ctx.beginPath();ctx.moveTo(p.x-Math.cos(ra)*rl,p.y-Math.sin(ra)*rl);'
        'ctx.lineTo(p.x+Math.cos(ra)*rl,p.y+Math.sin(ra)*rl);ctx.stroke();}'
        'ctx.beginPath();ctx.arc(p.x,p.y,p.sz*0.4,0,Math.PI*2);'
        'ctx.fillStyle="rgba(255,255,255,"+alpha*0.9+")";ctx.fill();'

        # ===== DARKNESS: void tendril (curved trail) =====
        '}else if(elem==="Darkness"||elem==="Shadow"){'
        'ctx.beginPath();ctx.moveTo(p.prevX,p.prevY);'
        'var cpx=p.prevX+(p.x-p.prevX)*0.5+(Math.random()-0.5)*10;'
        'var cpy=p.prevY+(p.y-p.prevY)*0.5+(Math.random()-0.5)*10;'
        'ctx.quadraticCurveTo(cpx,cpy,p.x,p.y);'
        'ctx.strokeStyle=clr;ctx.lineWidth=p.sz*0.7;ctx.stroke();'
        'ctx.beginPath();ctx.arc(p.x,p.y,p.sz*0.6,0,Math.PI*2);ctx.fillStyle=clr;ctx.fill();'

        # ===== PSIONIC: expanding ring outlines =====
        '}else if(elem==="Psionic"){'
        'var ringR=p.sz+p.life*0.5;'
        'ctx.beginPath();ctx.arc(p.x,p.y,ringR,0,Math.PI*2);'
        'ctx.strokeStyle=clr;ctx.lineWidth=1.5;ctx.stroke();'

        # ===== HEALING: plus/cross shapes =====
        '}else if(elem==="Healing"){'
        'var cl=p.sz*1.2;'
        'ctx.strokeStyle=clr;ctx.lineWidth=p.sz*0.5;'
        'ctx.beginPath();ctx.moveTo(p.x-cl,p.y);ctx.lineTo(p.x+cl,p.y);ctx.stroke();'
        'ctx.beginPath();ctx.moveTo(p.x,p.y-cl);ctx.lineTo(p.x,p.y+cl);ctx.stroke();'

        # ===== WATER: teardrop trail (like fire but with gravity) =====
        '}else if(elem==="Water"){'
        'ctx.beginPath();ctx.moveTo(p.prevX,p.prevY);ctx.lineTo(p.x,p.y);'
        'ctx.strokeStyle="rgba("+rgb[0]+","+rgb[1]+","+rgb[2]+","+alpha*0.3+")";'
        'ctx.lineWidth=p.sz;ctx.lineCap="round";ctx.stroke();ctx.lineCap="butt";'
        'ctx.beginPath();ctx.arc(p.x,p.y,p.sz*0.8,0,Math.PI*2);ctx.fillStyle=clr;ctx.fill();'

        # ===== DEFAULT: standard glowing circle =====
        '}else{'
        'ctx.beginPath();ctx.arc(p.x,p.y,p.sz,0,Math.PI*2);ctx.fillStyle=clr;ctx.fill();'
        '}'

        # Save previous position for trails, clear shadow
        'p.prevX=p.x;p.prevY=p.y;'
        'ctx.shadowBlur=0;'
        '}'
        'if(alive>0)requestAnimationFrame(frame);'
        'else if(cvs.parentNode)cvs.parentNode.removeChild(cvs);'
        '}'
        'requestAnimationFrame(frame);'

        '},400+burstIdx*burstDelay);'  # 400ms base + stagger per burst
        '})(burst);'
        '}'  # end burst loop
        '})();</script>'
    )


def generate_dice_roll_js(dice_rolls):
    """Generate animated 3D opposed dice rolls inside combat panels.

    dice_rolls: list of (player_roll, monster_roll, player_wins, label, sides) tuples.
    Each entry produces TWO dice: one in the player panel, one in the monster panel.
    The winning dice glows green, the losing dice glows red.

    Sequenced timeline (per round):
      0ms     Player ATTACK dice tumbles (orange label, player panel)
      600ms   Monster DEFEND dice tumbles (blue label, monster panel)
      1900ms  Monster ATTACK dice tumbles (orange label, monster panel)
      2500ms  Player DEFEND dice tumbles (blue label, player panel)

    FLEE uses the same format but sequenced as a single exchange:
      0ms     Player FLEE dice tumbles (yellow label, player panel)
      600ms   Monster CATCH dice tumbles (red label, monster panel)
    """
    if not dice_rolls:
        return ""

    # Each tuple: (player_roll, monster_roll, player_wins, label, sides, p_mod, m_mod)
    # Older tuples without modifiers get 0/0 defaults.
    def _pack(r):
        p_mod = r[5] if len(r) > 5 else 0
        m_mod = r[6] if len(r) > 6 else 0
        return f'[{r[0]},{r[1]},{1 if r[2] else 0},"{r[3]}",{r[4]},{p_mod},{m_mod}]'
    roll_data_js = ",".join(_pack(r) for r in dice_rolls)

    js = (
        '<script>(function(){'
        'var rolls=[' + roll_data_js + '];'

        # Polygon clip-paths per die type (d20 hex, d12 pent, d8 diamond...)
        'var shapes={'
        '20:"polygon(50% 0%,93% 25%,93% 75%,50% 100%,7% 75%,7% 25%)",'
        '12:"polygon(50% 0%,100% 38%,82% 100%,18% 100%,0% 38%)",'
        '8:"polygon(50% 0%,100% 50%,50% 100%,0% 50%)",'
        '6:"none",'
        '4:"polygon(50% 0%,100% 100%,0% 100%)"'
        '};'
        'var radii={20:"2px",12:"2px",8:"0",6:"3px",4:"0"};'

        # Helper: create and animate a single dice with optional modifier.
        # The dice shows the TOTAL (raw + mod); the bottom label shows the breakdown.
        # Wraps are absolute-positioned to fill the container so multiple dice
        # (ATK then DEF in same slot) occupy the SAME spot instead of stacking.
        # revealMs: absolute time when win/lose colors are revealed (both dice
        #           in a pair share the same reveal time so neither spoils the result).
        'function makeDice(containerId,rawVal,mod,winner,labelText,labelColor,sides,delayMs,revealMs){'
        'var container=document.getElementById(containerId);'
        'if(!container)return;'

        'var wrap=document.createElement("div");'
        # INIT dice use a horizontal layout (dice on left, INIT/d20 labels
        # stacked on the right) so they don't tower vertically over the
        # combat panels. All other dice keep the compact vertical stack.
        'var isInit=(labelText==="INIT");'
        'wrap.style.cssText="position:absolute;left:0;right:0;top:0;bottom:0;'
        'display:flex;flex-direction:"+(isInit?"row":"column")+";'
        'align-items:center;justify-content:center;'
        'gap:"+(isInit?"3px":"0")+";'
        'opacity:0;transition:opacity 0.2s;overflow:visible;";'

        # Top label: short action verb. Modifier breakdown is in the bottom
        # label ("15+6"), so we don't repeat it here. We also clip overflow
        # so adjacent dice labels can't bleed into each other.
        'var SHORT={ATTACK:"ATK",DEFEND:"DEF",CATCH:"CAT",FLEE:"FLEE",INIT:"INIT"};'
        'var shortLabel=SHORT[labelText]||labelText;'
        'var top=document.createElement("div");'
        'top.style.cssText="font-size:7px;font-weight:bold;font-family:monospace;'
        'margin-bottom:1px;letter-spacing:0.5px;white-space:nowrap;'
        'overflow:hidden;text-overflow:clip;max-width:32px;text-align:center;'
        'color:"+labelColor+";";'
        'top.textContent=shortLabel;'

        # The dice
        'var sz=28;'
        'var dice=document.createElement("div");'
        'var clip=shapes[sides]||shapes[20];'
        'var rad=radii[sides]||"2px";'
        'dice.style.cssText='
        '"width:"+sz+"px;height:"+sz+"px;'
        'display:flex;align-items:center;justify-content:center;'
        'font-size:13px;font-weight:bold;font-family:monospace;'
        'color:#FFF;background:#444;margin:0 auto;'
        'text-shadow:0 0 3px #000;'
        'border:2px solid #777;border-radius:"+rad+";'
        'perspective:120px;";'
        'if(clip!=="none")dice.style.clipPath=clip;'
        'dice.textContent="";'

        # Bottom label: shows raw + mod breakdown (e.g., "15+3") or plain "d20"
        'var dlbl=document.createElement("div");'
        'dlbl.style.cssText="font-size:7px;color:#888;font-family:monospace;margin-top:1px;";'
        'dlbl.textContent="d"+sides;'

        # Assemble: INIT uses row layout (dice | labelCol), others use the
        # original column layout (top / dice / dlbl).
        'if(isInit){'
        'var labelCol=document.createElement("div");'
        'labelCol.style.cssText="display:flex;flex-direction:column;align-items:flex-start;";'
        'top.style.marginBottom="0";'
        'dlbl.style.marginTop="0";'
        'labelCol.appendChild(top);'
        'labelCol.appendChild(dlbl);'
        'wrap.appendChild(dice);'
        'wrap.appendChild(labelCol);'
        '}else{'
        'wrap.appendChild(top);'
        'wrap.appendChild(dice);'
        'wrap.appendChild(dlbl);'
        '}'

        'container.appendChild(wrap);'

        # Tumble animation
        'setTimeout(function(){'
        'wrap.style.opacity="1";'
        'var frame=0;var total=8;var flicker;'
        'flicker=setInterval(function(){'
        'frame++;'
        'if(frame<total){'
        'dice.textContent=Math.floor(Math.random()*sides)+1;'
        'var rx=(Math.random()*360-180);'
        'var ry=(Math.random()*360-180);'
        'dice.style.transform="perspective(120px) rotateX("+rx+"deg) rotateY("+ry+"deg)";'
        'dice.style.borderColor="#999";'
        '}else{'
        'clearInterval(flicker);'
        # Land: show the number but stay NEUTRAL grey — don't reveal win/lose yet
        'var total_val=rawVal+mod;'
        'dice.textContent=total_val;'
        'if(mod>0){dlbl.textContent=rawVal+"+"+mod;}'
        'dice.style.transform="perspective(120px) rotateX(0) rotateY(0)";'
        'dice.style.borderColor="#AAA";dice.style.color="#DDD";'
        'dice.style.background="#3a3a3a";'
        '}'
        '},45);'
        '},delayMs);'

        # Reveal phase: after both dice have landed, show win/lose colors
        'setTimeout(function(){'
        # CRIT only applies to ATTACK rolls (and FLEE, which is an attack-style roll).
        # Defense nat-20s are just successful dodges, not crits.
        'var canCrit=(labelText==="ATTACK"||labelText==="FLEE");'
        'var isCrit=(rawVal===sides && winner && canCrit);'
        'var isFumble=(rawVal===1 && !winner);'
        'dice.style.transition="border-color 0.25s,color 0.25s,background 0.25s,box-shadow 0.25s";'
        'if(isCrit){'
        'dice.style.borderColor="#FFD700";'
        'dice.style.color="#FFD700";'
        'dice.style.background="#3a2e00";'
        'dice.style.boxShadow="0 0 16px #FFD700,0 0 32px #FFD700";'
        'dice.style.animation="critPulse 0.5s ease-out";'
        'top.textContent="CRIT!";'
        'top.style.color="#FFD700";'
        'top.style.textShadow="0 0 6px #FFD700";'
        'var scr=document.getElementById("content-area");'
        'if(scr){'
        'scr.style.animation="none";'
        'void scr.offsetWidth;'
        'scr.style.animation="screenShake 0.5s ease-out";'
        '}'
        # NOTE: haptic on crit is triggered by generate_damage_float_js
        # at the same instant as the damage panel shake (~1300ms), which
        # is the visually impactful moment, not the dice reveal.
        '}else if(isFumble){'
        'dice.style.borderColor="#555";'
        'dice.style.color="#888";'
        'dice.style.background="#181818";'
        'dice.style.boxShadow="0 0 4px #333";'
        'dice.style.animation="fumbleShake 0.4s ease-out";'
        'top.textContent="MISS!";'
        'top.style.color="#666";'
        '}else if(winner){'
        'dice.style.borderColor="#69F0AE";dice.style.color="#69F0AE";'
        'dice.style.background="#2a3a2a";'
        'dice.style.boxShadow="0 0 6px #69F0AE";'
        '}else{'
        'dice.style.borderColor="#FF5252";dice.style.color="#FF5252";'
        'dice.style.background="#3a2a2a";'
        'dice.style.boxShadow="0 0 6px #FF5252";'
        '}'
        # Fade out after brief hold
        'setTimeout(function(){'
        'wrap.style.transition="opacity 0.5s";wrap.style.opacity="0";'
        'setTimeout(function(){if(wrap.parentNode)wrap.parentNode.removeChild(wrap);},500);'
        '},1800);'
        '},revealMs);'
        '}'

        # Process each opposed-roll entry.
        # Dice slot layout is MIRRORED between panels so each exchange is a
        # vertical column pair:
        #
        #                   LEFT slot         RIGHT slot
        #   monster_dice    monster_def_dice  monster_atk_dice
        #   player_dice     player_atk_dice   player_def_dice
        #
        #   Phase 1 (player ATK): P-ATK + M-DEF -> both light up LEFT column
        #   Phase 2 (monster ATK): M-ATK + P-DEF -> both light up RIGHT column
        #   FLEE:                 P-FLEE + M-CATCH -> LEFT column
        # Check if an INIT roll is present — if so, shift combat dice forward
        'var hasInit=rolls.some(function(r){return r[3]==="INIT";});'
        'var initOffset=hasInit?1000:0;'  # 1s delay after initiative dice settle

        'rolls.forEach(function(r){'
        'var pRoll=r[0],mRoll=r[1],playerWins=r[2],label=r[3],sides=r[4],pMod=r[5],mMod=r[6];'
        # Winner is whoever has higher total (raw + mod)
        'var pHigher=((pRoll+pMod)>(mRoll+mMod));'

        # revealMs = when second dice lands + 200ms beat (tumble ~360ms)
        'if(label==="ATK"){'
        # Player attacks first, monster defends. Reveal after monster dice lands.
        'var rv=initOffset+600+360+200;'
        'makeDice("player_atk_dice",pRoll,pMod,pHigher,"ATTACK","#FF8A65",sides,initOffset+0,rv);'
        'makeDice("monster_def_dice",mRoll,mMod,!pHigher,"DEFEND","#64B5F6",sides,initOffset+600,rv);'
        '}else if(label==="DEF"){'
        # Monster attacks, player defends. Reveal after player dice lands.
        'var rv=initOffset+2500+360+200;'
        'makeDice("monster_atk_dice",mRoll,mMod,!pHigher,"ATTACK","#FF8A65",sides,initOffset+1900,rv);'
        'makeDice("player_def_dice",pRoll,pMod,pHigher,"DEFEND","#64B5F6",sides,initOffset+2500,rv);'
        '}else if(label==="FLEE"){'
        # Flee pair. Reveal after monster CATCH dice lands.
        'var rv=600+360+200;'
        'makeDice("player_atk_dice",pRoll,pMod,pHigher,"FLEE","#FFD54F",sides,0,rv);'
        'makeDice("monster_def_dice",mRoll,mMod,!pHigher,"CATCH","#FF8A65",sides,600,rv);'
        '}else if(label==="INIT"){'
        # Initiative: render in the DEDICATED left-side init slots
        # (monster_init_dice / player_init_dice), which are bigger
        # (48x72) and positioned apart from the right-side ATK/DEF
        # slots so they don't share space.  Purple color.
        'var rv=200+360+200;'
        'makeDice("player_init_dice",pRoll,pMod,pHigher,"INIT","#CE93D8",sides,0,rv);'
        'makeDice("monster_init_dice",mRoll,mMod,!pHigher,"INIT","#CE93D8",sides,200,rv);'
        # "INITIATIVE!" banner — positioned just above the combat panels
        # (top:42% instead of 30%) so it sits close to the dice rather
        # than floating up in the map area.
        'var ib=document.createElement("div");'
        'ib.style.cssText="position:fixed;top:42%;left:50%;'
        'transform:translate(-50%,-50%) scale(0.7);'
        'z-index:99997;text-align:center;pointer-events:none;opacity:0;'
        'font-family:monospace;font-size:18px;font-weight:bold;'
        'letter-spacing:6px;text-transform:uppercase;'
        'color:#CE93D8;'
        'text-shadow:0 0 10px #CE93D8,0 0 3px #000;";'
        'ib.textContent="INITIATIVE!";'
        'document.body.appendChild(ib);'
        'ib.style.transition="opacity 0.25s ease-out,transform 0.25s ease-out";'
        'setTimeout(function(){ib.style.opacity="1";ib.style.transform="translate(-50%,-50%) scale(1)";},40);'
        'setTimeout(function(){ib.style.transition="opacity 0.4s ease-in,transform 0.4s ease-in";'
        'ib.style.opacity="0";ib.style.transform="translate(-50%,-50%) scale(1.05) translateY(-6px)";},700);'
        'setTimeout(function(){if(ib.parentNode)ib.parentNode.removeChild(ib);},1200);'
        # Tiny haptic tick on the initiative moment
        'try{if(navigator.vibrate)navigator.vibrate(40);}catch(e){}'
        '}'

        '});'
        '})();</script>'
    )
    return js


def generate_concentration_check_js(conc_roll):
    """Generate a single d20 concentration check dice animation.

    conc_roll: (raw_roll, modifier, total, dc, passed)
    Shows a single d20 in the player panel with CONC label, glowing
    green on pass or red on fail. On failure, plays a fizzle overlay.
    """
    if not conc_roll:
        return ""
    raw_roll, modifier, total, dc, passed = conc_roll
    win_js = 1 if passed else 0
    # Reuse the makeDice infrastructure from dice rolls
    label_color = '#69F0AE' if passed else '#FF5252'
    result_label = 'HELD!' if passed else 'FIZZLE!'

    js = (
        '<script>(function(){'
        # Create a single dice in the player ATK slot
        'var container=document.getElementById("player_atk_dice");'
        'if(!container)return;'

        'var wrap=document.createElement("div");'
        'wrap.style.cssText="position:absolute;left:0;right:0;top:0;bottom:0;'
        'display:flex;flex-direction:column;align-items:center;justify-content:center;'
        'opacity:0;transition:opacity 0.2s;overflow:visible;";'

        # Top label
        'var top=document.createElement("div");'
        'top.style.cssText="font-size:7px;font-weight:bold;font-family:monospace;'
        'margin-bottom:1px;letter-spacing:0.5px;white-space:nowrap;'
        f'color:{label_color};";'
        f'top.textContent="CONC +{modifier}";'
        'wrap.appendChild(top);'

        # The dice
        'var sz=28;'
        'var dice=document.createElement("div");'
        'dice.style.cssText='
        '"width:"+sz+"px;height:"+sz+"px;'
        'display:flex;align-items:center;justify-content:center;'
        'font-size:13px;font-weight:bold;font-family:monospace;'
        'color:#FFF;background:#444;margin:0 auto;'
        'text-shadow:0 0 3px #000;'
        'border:2px solid #777;border-radius:2px;'
        'clip-path:polygon(50% 0%,93% 25%,93% 75%,50% 100%,7% 75%,7% 25%);'
        'perspective:120px;";'
        'dice.textContent="";'
        'wrap.appendChild(dice);'

        # Bottom label: shows DC
        'var dlbl=document.createElement("div");'
        'dlbl.style.cssText="font-size:7px;color:#888;font-family:monospace;margin-top:1px;";'
        f'dlbl.textContent="DC {dc}";'
        'wrap.appendChild(dlbl);'

        'container.appendChild(wrap);'

        # Tumble animation (delayed to play after monster attack dice)
        'setTimeout(function(){'
        'wrap.style.opacity="1";'
        'var frame=0;var total=8;var flicker;'
        'flicker=setInterval(function(){'
        'frame++;'
        'if(frame<total){'
        'dice.textContent=Math.floor(Math.random()*20)+1;'
        'var rx=(Math.random()*360-180);'
        'var ry=(Math.random()*360-180);'
        'dice.style.transform="perspective(120px) rotateX("+rx+"deg) rotateY("+ry+"deg)";'
        '}else{'
        'clearInterval(flicker);'
        f'dice.textContent={total};'
        f'if({modifier}>0){{dlbl.textContent="{raw_roll}+{modifier} vs DC {dc}";}}'
        'dice.style.transform="perspective(120px) rotateX(0) rotateY(0)";'
        f'if({win_js}){{'
        'dice.style.borderColor="#69F0AE";dice.style.color="#69F0AE";'
        'dice.style.background="#2a3a2a";'
        'dice.style.boxShadow="0 0 6px #69F0AE";'
        f'top.textContent="{result_label}";'
        'top.style.color="#69F0AE";'
        '}else{'
        'dice.style.borderColor="#FF5252";dice.style.color="#FF5252";'
        'dice.style.background="#3a2a2a";'
        'dice.style.boxShadow="0 0 6px #FF5252";'
        f'top.textContent="{result_label}";'
        'top.style.color="#FF5252";'
        'top.style.textShadow="0 0 6px #FF5252";'
    )

    # Fizzle overlay on failure
    if not passed:
        js += (
            # Screen flash red + "FIZZLE!" banner
            'var fz=document.createElement("div");'
            'fz.style.cssText="position:fixed;top:38%;left:50%;transform:translate(-50%,-50%) scale(0.7);'
            'z-index:99999;text-align:center;pointer-events:none;opacity:0;'
            'font-family:monospace;font-size:22px;font-weight:bold;'
            'letter-spacing:6px;text-transform:uppercase;'
            'color:#FF5252;text-shadow:0 0 12px #FF5252,0 0 4px #000;";'
            'fz.textContent="FIZZLE!";'
            'document.body.appendChild(fz);'
            'setTimeout(function(){fz.style.transition="opacity 0.3s";fz.style.opacity="1";'
            'fz.style.transform="translate(-50%,-50%) scale(1)";},50);'
            'setTimeout(function(){fz.style.transition="opacity 0.4s";fz.style.opacity="0";},800);'
            'setTimeout(function(){if(fz.parentNode)fz.parentNode.removeChild(fz);},1300);'
            # Red screen tint
            'var tint=document.createElement("div");'
            'tint.style.cssText="position:fixed;inset:0;background:rgba(255,50,50,0.15);'
            'z-index:99998;pointer-events:none;opacity:0;transition:opacity 0.15s;";'
            'document.body.appendChild(tint);'
            'setTimeout(function(){tint.style.opacity="1";},50);'
            'setTimeout(function(){tint.style.opacity="0";},400);'
            'setTimeout(function(){if(tint.parentNode)tint.parentNode.removeChild(tint);},600);'
        )

    js += (
        '}'  # close else (fail styling)
        'setTimeout(function(){'
        'wrap.style.transition="opacity 0.5s";wrap.style.opacity="0";'
        'setTimeout(function(){if(wrap.parentNode)wrap.parentNode.removeChild(wrap);},500);'
        '},1800);'
        '}'  # close landed frame
        '},45);'  # close setInterval
        '},3200);'  # delay: after monster attack dice sequence
        '})();</script>'
    )
    return js


def generate_monster_defeat_js(monster_name):
    """Generate a sequenced monster defeat animation inside the combat panel.

    Combat sequence on a kill (matches dice/damage timing):
      0-600ms:    Player ATTACK dice tumbles + lands
      600-1000ms: Monster DEFEND dice tumbles + lands (exchange resolved)
      1300ms:     Monster damage float appears
      2100ms:     Sprite fades to grayscale (kill confirmed)
      2700ms:     Flash "MONSTER NAME / DEFEATED" overlay
      4500ms:     Panel auto-dismissed by Python timer
    """
    if not monster_name:
        return ""
    safe_name = monster_name.replace('"', '\\"').replace("'", "\\'").replace('<', '').replace('>', '')
    return (
        '<script>(function(){'
        # Haptic on kills is handled by generate_damage_float_js only when
        # the badge is CRIT or the spell is high-level — normal kills stay
        # quiet so buzzes land only on the big moments.
        'var mp=document.getElementById("monster_panel");'
        'if(!mp)return;'
        # Cancel CSS entrance animation that might conflict
        'mp.style.animation="none";'

        # Phase 1 (0-2100ms): wait for opposed dice + damage float to play

        # Phase 2 (2100ms): grayscale + dim the sprite box only (not the text)
        'setTimeout(function(){'
        'var sb=document.getElementById("monster_sprite_box");'
        'if(sb){'
        'sb.style.setProperty("filter","grayscale(100%) brightness(0.35)","important");'
        '}'
        '},2100);'

        # Phase 3 (2700ms): flash in overlay with monster name + DEFEATED
        'setTimeout(function(){'
        'var ov=document.createElement("div");'
        'ov.style.cssText="position:absolute;left:0;right:0;top:0;bottom:0;'
        'display:flex;flex-direction:column;align-items:center;justify-content:center;'
        'background:rgba(0,0,0,0.55);border-radius:3px;'
        'pointer-events:none;opacity:0;transform:scale(0.85);'
        'transition:opacity 0.3s ease-out,transform 0.3s ease-out;";'

        'var txt=document.createElement("div");'
        'txt.style.cssText="font-family:monospace;font-size:15px;font-weight:bold;'
        'color:#F44336;text-shadow:0 0 8px #F44336,0 0 16px #F44336;margin-bottom:4px;";'
        'txt.textContent="' + safe_name + '";'
        'ov.appendChild(txt);'

        'var sub=document.createElement("div");'
        'sub.style.cssText="font-family:monospace;font-size:12px;font-weight:bold;color:#69F0AE;'
        'text-shadow:0 0 6px #69F0AE,0 0 12px #69F0AE;letter-spacing:3px;";'
        'sub.textContent="DEFEATED";'
        'ov.appendChild(sub);'

        'mp.appendChild(ov);'
        # Trigger entrance: opacity 0 -> 1, scale 0.85 -> 1
        'requestAnimationFrame(function(){'
        'ov.style.opacity="1";'
        'ov.style.transform="scale(1)";'
        '});'
        '},2700);'

        '})();</script>'
    )


# ============================================================
# SPRITE SYSTEM
# Sprite sheets, mappings, and rendering functions
# All sprite data and rendering now in external sprite_data.py
# ============================================================

def get_evolution_tier_style(monster):
    """Return (border_color, tier_label_html) for evolution tier display."""
    tier = monster.properties.get('evolution_tier', '') if hasattr(monster, 'properties') else ''
    if tier == 'Hardened':
        return '#8B7355', '<span style="color:#8B7355;font-size:11px;font-weight:bold;">[Hardened]</span>'
    elif tier == 'Savage':
        return '#A0522D', '<span style="color:#A0522D;font-size:11px;font-weight:bold;">[Savage]</span>'
    elif tier == 'Dread':
        return '#7B68AE', '<span style="color:#7B68AE;font-size:11px;font-weight:bold;">[Dread]</span>'
    elif tier == 'Mythic':
        return '#B8962E', '<span style="color:#B8962E;font-size:11px;font-weight:bold;">[Mythic]</span>'
    return '', ''  # Normal: no border, no label


def generate_player_sprite_html(race, gender, equipped_armor=None):
    """Wrapper that resolves armor state, then delegates to sprite_data."""
    if equipped_armor is None or getattr(equipped_armor, 'is_broken', False):
        armor_state = 'none'
    elif is_metal_item(equipped_armor):
        armor_state = 'metal'
    else:
        armor_state = 'nonmetal'
    return _generate_player_sprite_html(race, armor_state)

def can_cast_spells(player_character):
    """
    Check if player has the ability to cast spells.
    Returns True if player has: 
    - Max mana > 0 (requires Intelligence > 15)
    - Max spell slots > 0 (requires Intelligence > 15)
    """
    return gs.player_character.max_mana > 0 and gs.player_character.get_max_memorized_spell_slots() > 0

def generate_grid_html(floor, player_x, player_y):
    """Generate the HTML for the dungeon grid/map display."""
    highlight_coords = (player_y, player_x)
    grid_html = '<div style="text-align: center; max-width: 100%; overflow-x: auto; margin: 0 auto;"><div style="background-color: #222; display: inline-block; padding: 2px; border-radius: 2px; max-width: 100%;">'

    for r_idx in range(floor.rows):
        grid_html += '<div style="height: 17px; white-space: nowrap;">'
        for c_idx in range(floor.cols):
            room = floor.grid[r_idx][c_idx]
            cell_style = "display: inline-block; width: 17px; height: 17px; line-height: 17px; text-align: center; vertical-align: top; font-family: monospace; font-size: 13px;"
            content = "&nbsp;"

            if room.discovered or (r_idx, c_idx) == highlight_coords:
                content = room.room_type
                if content == '#':
                    cell_style += "color: #555;"
                elif content == '.':
                    cell_style += "color: #888;"
                elif content in ['E', 'D', 'U']:
                    cell_style += "color: #4CAF50;"
                elif content == 'V':
                    cell_style += "color: #FFD700;"
                elif content == 'M':
                    # Monster room - red
                    if room.properties.get('is_champion'):
                        cell_style += "color: #FF0000; font-weight: bold; text-shadow: 0 0 3px #FF0000;"
                    else:
                        cell_style += "color: #F44336;"
                elif content == 'W':
                    # Wandering monster - orange to distinguish from M
                    cell_style += "color: #FF9800;"
                elif content == 'C':
                    # Check if this is a legendary chest
                    if room.properties.get('is_legendary'):
                        cell_style += "color: #FFD700; font-weight: bold; text-shadow: 0 0 3px #FFD700;"
                    else:
                        cell_style += "color: #03A9F4;"
                elif content == 'A':
                    cell_style += "color: #FFEB3B;"
                elif content == 'P':
                    # Check if this is ancient waters
                    if room.properties.get('is_ancient'):
                        cell_style += "color: #00FFFF; font-weight: bold; text-shadow: 0 0 3px #00FFFF;"
                    else:
                        cell_style += "color: #03A9F4;"
                elif content == 'L':
                    # Check if this has the Codex
                    if room.properties.get('has_codex'):
                        cell_style += "color: #FFD700; font-weight: bold; text-shadow: 0 0 3px #FFD700;"
                    else:
                        cell_style += "color: #E040FB;"
                elif content == 'N':
                    # Check if this is a master dungeon
                    if room.properties.get('is_master'):
                        cell_style += "color: #FFD700; font-weight: bold; text-shadow: 0 0 3px #FFD700;"
                    else:
                        cell_style += "color: #CE93D8;"  # Light purple for locked dungeons (distinct from M red and W orange)
                elif content == 'T':
                    # Check if this is a cursed tomb
                    if room.properties.get('is_cursed'):
                        cell_style += "color: #E040FB; font-weight: bold; text-shadow: 0 0 3px #E040FB;"
                    else:
                        cell_style += "color: #8B4513;"  # Brown for tombs
                elif content == 'G':
                    # Check if this is a world tree or fey garden
                    if room.properties.get('has_world_tree'):
                        cell_style += "color: #00FF00; font-weight: bold; text-shadow: 0 0 3px #00FF00;"
                    elif room.properties.get('is_fey_garden'):
                        cell_style += "color: #FF00FF; font-weight: bold; text-shadow: 0 0 3px #FF00FF;"
                    else:
                        cell_style += "color: #4CAF50;"  # Green for magical gardens
                elif content == 'O':
                    cell_style += "color: #E040FB;"  # Purple for oracle rooms
                elif content == 'B':
                    cell_style += "color: #FF8C00;"  # Orange for blacksmith
                elif content == 'F':
                    cell_style += "color: #87CEEB;"  # Sky blue for shrine
                elif content == 'Q':
                    cell_style += "color: #39FF14;"  # Neon green for alchemist lab
                elif content == 'K':
                    cell_style += "color: #CD5C5C;"  # Indian red for war room
                elif content == 'X':
                    cell_style += "color: #D4A017;"  # Gold/amber for taxidermist
                elif content == 'X':
                    cell_style += "color: #D2691E;"  # Saddle brown for taxidermist
                elif content == 'Z':
                    # Puzzle room (Zotle)
                    cell_style += "color: #E040FB; font-weight: bold; text-shadow: 0 0 3px #E040FB;"
                else:
                    cell_style += "color: #DDD;"

                if (r_idx, c_idx) == highlight_coords:
                    cell_style += "background-color: #DDD; color: #000; font-weight: bold; border-radius: 2px;"

            grid_html += f'<span style="{cell_style}">{content}</span>'
        grid_html += "</div>"
    grid_html += "</div></div>"
    return grid_html



# --------------------------------------------------------------------------------
# 22. UI - TOGA APPLICATION
# --------------------------------------------------------------------------------

class WizardsCavernApp(toga.App):
    def startup(self):
        """Initialize and display the application."""
        
        # Set save directory to platform-appropriate data path
        import sys
        if sys.platform in ('ios', 'android'):
            gs.SAVE_DIRECTORY = str(self.paths.data / "saves")

        # Initialize game state
        self.init_game_state()
        
        # Create main window with mobile phone dimensions
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Set window size for desktop; on mobile this is ignored (fullscreen)
        import sys
        if sys.platform not in ('ios', 'android'):
            self.main_window.size = (393, 852)
            try:
                self.main_window.resizable = False
            except AttributeError:
                pass
        
        # Build UI
        main_box = self.build_ui()
        self.main_window.content = main_box
        
        # Show window
        self.main_window.show()

        # The persistent hidden audio_view approach didn't pan out:
        #   - Bypassing the Android user-gesture policy via
        #     setMediaPlaybackRequiresUserGesture(false) triggers a security
        #     warning to the user.
        #   - Without the bypass, the AudioContext stays suspended forever
        #     in the 0x0 hidden frame.
        # Until we can do incremental DOM updates (so the main WebView stops
        # reloading on every button press), we use inline music injection.
        # The audio_view widget is kept in the layout but loads an empty
        # placeholder.
        self._audio_view_active = False
        try:
            self.audio_view.set_content("", "<html><body></body></html>")
        except Exception:
            pass

        # iOS WKWebView config: allow audio playback without a user gesture.
        # Without this, the AudioContext stays suspended even though scripts
        # execute fine.  iOS does NOT show a security warning for this
        # (unlike Android's setMediaPlaybackRequiresUserGesture).
        import sys
        if sys.platform == 'ios':
            try:
                cfg = self.web_view._impl.native.configuration
                cfg.mediaTypesRequiringUserActionForPlayback = 0
                cfg.allowsInlineMediaPlayback = True
            except Exception:
                pass

        # Start with splash screen
        gs.prompt_cntl = "splash"

        # Initial render
        self.render()

        # Schedule transition from splash to intro after 5 seconds
        import threading
        def _end_splash():
            gs.prompt_cntl = "intro_story"
            try:
                self.render()
            except Exception:
                pass
        self._splash_timer = threading.Timer(5.0, _end_splash)
        self._splash_timer.daemon = True
        self._splash_timer.start()

        # CRITICAL: Disable native keyboard AFTER window is shown
        # This must happen after the native widgets are fully initialized
        self.disable_ios_keyboard()
        self.disable_android_keyboard()
        # Schedule a delayed pass to fix Android UI after views are fully laid out
        self._schedule_android_ui_fixes()
    
    def init_game_state(self):
        """Initialize all game objects and state variables."""

        # Initialize a boolean variable game_should_quit = False before the main while True game loop.
        gs.game_should_quit = False

        gs.prompt_cntl = ""

        gs.log_lines = []
        
        # Track if current mode needs numbers (for button behavior)
        self.current_needs_numbers = False


        # Intro will be shown in HTML, not log
        gs.prompt_cntl = "intro_story"
        gs.previous_prompt_cntl = ""
        
        # REAL GAME INITIALIZATION (from cavern12__3_.py)
        
        # Initialize the item identification system (shuffles cryptic names)
        initialize_identification_system()
        
        # Create the Tower
        gs.my_tower = Tower()
        
        # Generate the first floor with proper carving and room population
        gs.my_tower.add_floor(gs.specified_chars, gs.required_chars, gs.grid_rows, gs.grid_cols, gs.wall_char, gs.floor_char,
                           p_limits=gs.p_limits_val, c_limits=gs.c_limits_val, w_limits=gs.w_limits_val, 
                           a_limits=gs.a_limits_val, l_limits=gs.l_limits_val, dungeon_limits=gs.dungeon_limits_val, t_limits=gs.t_limits_val, garden_limits=gs.garden_limits_val, o_limits=gs.o_limits_val,
                           b_limits=gs.b_limits_val, f_limits=gs.f_limits_val, q_limits=gs.q_limits_val, k_limits=gs.k_limits_val, x_limits=gs.x_limits_val)
        
        # Player starting position (entrance is at 1,1)
        ch_x, ch_y = 1, 1
        
        # Create the player character
        gs.player_character = Character(
            name="Adventurer", health=1, attack=1, defense=1, strength=1, dexterity=1, intelligence=1,
            x=ch_x, y=ch_y, z=0
        )
        gs.player_character.gold = 500  # Give starting gold
        gs.player_character.memorized_spells = []
        
        # Mark the starting room as discovered
        gs.my_tower.floors[0].grid[ch_y][ch_x].discovered = True
        
        # Initialize other globals
        gs.encountered_monsters = {}  # Dictionary keyed by (x, y, z) coordinates
        gs.encountered_vendors = {}   # Dictionary keyed by (x, y, z) coordinates
        gs.active_vendor = None
        gs.active_monster = None
        gs.shop_message = ""
        gs.lets_go = False
        gs.active_flare_item = None
        gs.newly_unlocked_achievements = []
        gs.curing_kit_stocked = False  # Reset so next vendor on floors 1-10 stocks it
        import random as _rnd
        gs.curing_kit_floor = _rnd.randint(0, 9)  # Random floor 1-10 (0-indexed)
        gs.achievement_notification_timer = 0
        
        # Initialize dungeon and tomb tracking
        gs.dungeon_keys = {}
        gs.unlocked_dungeons = {}
        gs.looted_dungeons = {}
        gs.looted_tombs = {}
        gs.harvested_gardens = {}
        gs.harvested_fey_floors = set()
        gs.haunted_floors = {}
        gs.ephemeral_gardens = {}
        gs.pending_tomb_guardian_reward = None
        
        # Initialize quest tracking for Orb of Zot
        
        gs.runes_obtained = {
            'battle': False, 'treasure': False, 'devotion': False, 'reflection': False,
            'knowledge': False, 'secrets': False, 'eternity': False, 'growth': False
        }
        gs.shards_obtained = {
            'battle': False, 'treasure': False, 'devotion': False, 'reflection': False,
            'knowledge': False, 'secrets': False, 'eternity': False, 'growth': False
        }
        gs.rune_progress = {
            'monsters_killed_total': 0,
            'chests_opened_total': 0,
            'pools_drunk_total': 0,
            'spells_learned_total': 0,
            'unique_spells_memorized': set(),
            'dungeons_unlocked_total': 0,
            'tombs_looted_total': 0,
            'gardens_harvested_total': 0
        }
        gs.champion_monster_available = False
        gs.legendary_chest_available = False
        gs.ancient_waters_available = False
        gs.codex_available = False
        gs.master_dungeon_available = False
        gs.cursed_tomb_available = False
        gs.world_tree_available = False
        gs.gate_to_floor_50_unlocked = False
        
        gs.game_stats = {
            'monsters_killed': 0,
            'max_floor_reached': 0,
            'spells_learned': 0,
            'spells_cast': 0,
            'times_poisoned': 0,
            'chests_opened': 0,
            'dungeons_looted': 0,
            'tombs_looted': 0,
            'gardens_harvested': 0
        }
        gs.html_cache = ""
        
        # Initialize Zotle puzzle system
        gs.zotle_puzzle = initialize_zotle_puzzle()
        gs.active_zotle_teleporter = False
    
    def build_ui(self):
        """Build the user interface - mobile-optimized layout with dynamic buttons and number pad."""
        
        # ====================================================================
        # MOBILE-OPTIMIZED LAYOUT WITH DYNAMIC BUTTON INTERFACE
        # ====================================================================
        
        # Game display area (scrollable) - will contain log at bottom in HTML
        # Constrain width to mobile dimensions
        self.web_view = toga.WebView(
            style=Pack(flex=1)
        )

        # Hidden audio WebView — persists across game renders.
        # Music AudioContext stays alive so we get truly continuous playback.
        # Mood changes are driven by evaluate_javascript() calls on this view.
        self.audio_view = toga.WebView(
            style=Pack(height=0, width=0, flex=0)
        )
        
        # ====================================================================
        # BUTTON PANEL - Command display + Three rows for 8-column grid
        # ====================================================================
        
        # Command display label (shows available commands above buttons)
        self.command_display = toga.Label(
            "",
            style=Pack(
                margin=2,
                font_size=9,
                color="#888",
                text_align='center',
            )
        )
        
        # Create button containers that will be dynamically populated
        # Each row can hold 8 buttons (4 left for commands, 4 right for numbers)
        self.button_row_1 = toga.Box(
            style=Pack(direction=ROW, margin=0, background_color='#1a1a1a')
        )
        self.button_row_2 = toga.Box(
            style=Pack(direction=ROW, margin=0, background_color='#1a1a1a')
        )
        self.number_pad_box = toga.Box(  # Using as row 3
            style=Pack(direction=ROW, margin=0, background_color='#1a1a1a')
        )
        
        # Container for button rows (always visible, fixed height to keep input row stable)
        self.button_panel = toga.Box(
            style=Pack(direction=COLUMN, background_color="#1a1a1a", height=94),
            children=[
                #self.command_display,
                self.button_row_1,
                self.button_row_2,
                self.number_pad_box,
            ]
        )
        
        # ====================================================================
        # TEXT INPUT AREA - with permanent backspace button
        # ====================================================================
        
        self.input_field = toga.TextInput(
            placeholder="Type command...",
            on_confirm=self.on_input_confirm,
            style=Pack(flex=1, margin=2, height=40, font_size=12,
                       background_color='#2a2a2a', color='#EEE')
        )

        # Note: iOS keyboard will be disabled AFTER window is shown
        # See disable_ios_keyboard() method called in startup()

        # Permanent backspace button (always visible)
        self.backspace_button = toga.Button(
            "\u232b",
            on_press=lambda w: self.number_pad_backspace(),
            style=Pack(margin=2, width=50, height=36, font_size=13,
                       background_color='#333', color='#EEE')
        )

        self.submit_button = toga.Button(
            "SEND",
            on_press=self.on_command_submit,
            style=Pack(margin=2, width=70, height=36, font_size=13, font_weight='bold',
                       background_color='#444', color='#FFF')
        )
        
        self.input_row = toga.Box(
            style=Pack(direction=ROW, margin=2, height=40, background_color='#1a1a1a'),
            children=[
                self.input_field,
                self.backspace_button,
                self.submit_button
            ]
        )
        
        # ====================================================================
        # BOTTOM PANEL - Buttons + Input
        # ====================================================================
        
        # Commands hint label - single line, no wrapping
        self.commands_label = toga.Label(
            "",
            style=Pack(margin=(0, 5), font_size=9, color="#AAA", height=14)
        )
        
        self.bottom_panel = toga.Box(
            style=Pack(
                direction=COLUMN,
                background_color="#1a1a1a",
                height=208,
                flex=0,
            ),
            children=[
                self.commands_label,
                self.button_panel,
                self.input_row,
                toga.Box(style=Pack(height=6, background_color='#1a1a1a')),
            ]
        )

        # Main container (scrollable game + fixed bottom)
        # Constrain to mobile width
        main_box = toga.Box(
            style=Pack(
                direction=COLUMN,
                flex=1,
                background_color='#1a1a1a'
            ),
            children=[
                self.web_view,
                self.audio_view,    # hidden (0 height), persists audio ctx
                self.bottom_panel,
            ]
        )
        
        return main_box
    
    def quick_command(self, cmd, label=None):
        """Handle button press for commands."""
        
        # Special handling for QWERTY keyboard letters during name entry
        if gs.prompt_cntl == 'player_name' and len(cmd) == 1 and cmd.isalpha():
            # Use the label (which has correct case) if provided, otherwise use cmd
            letter_to_add = label if label else cmd
            # Append letter to input field
            current = self.input_field.value or ""
            self.input_field.value = current + letter_to_add
            # DON'T focus - prevents keyboard popup!
            return
        
        # Special handling for QWERTY keyboard letters during Zotle puzzle
        if gs.prompt_cntl == 'puzzle_mode' and len(cmd) == 1 and cmd.isalpha():
            letter = cmd.upper()
            # Add letter directly to zotle_puzzle current_guess
            if gs.zotle_puzzle:
                for i in range(5):
                    if not gs.zotle_puzzle['current_guess'][i]:
                        gs.zotle_puzzle['current_guess'][i] = letter
                        break
            # Re-render to show the letter
            self.render()
            return
        
        # Commands that always submit immediately:
        # - Movement: n/s/e/w
        # - Simple commands in non-number modes
        
        is_movement = cmd in ['n', 's', 'e', 'w']
        
        # Commands that need numbers appended
        # Vendor b/s/r/id and spell memo m/f now submit immediately to set
        # sub-action state, then numpad appears for item selection.
        # No commands need number suffix anymore — all submit immediately.
        is_vendor_mode = gs.prompt_cntl in ['vendor_shop', 'starting_shop']
        needs_number_suffix = False

        # Special case: 'e' in inventory means equip (not east movement)
        # Override is_movement for 'e' when in inventory/needs_numbers mode
        if cmd == 'e' and self.current_needs_numbers:
            is_movement = False

        # Special case: 's' in vendor mode means sell (not south movement)
        if cmd == 's' and is_vendor_mode:
            is_movement = False

        # All commands now submit immediately (no prefix-and-wait pattern)
        if needs_number_suffix and not is_movement:
            # Append command to input field, user will type number and press send
            self.input_field.value = cmd
            # Don't focus if readonly (will trigger keyboard)
            if not self.input_field.readonly:
                self.input_field.focus()
        else:
            # Submit command immediately
            self.input_field.value = cmd
            self.on_command_submit(None)
    
    def disable_ios_keyboard(self):
        """Disable iOS keyboard completely - use button keyboard instead."""
        import sys
        if sys.platform != 'ios':
            return
        try:
            # Access native iOS implementation
            if hasattr(self.input_field, '_impl') and hasattr(self.input_field._impl, 'native'):
                native_field = self.input_field._impl.native
                
                try:
                    from rubicon.objc import ObjCClass
                    UIView = ObjCClass('UIView')
                    
                    # Create empty UIView to replace keyboard
                    empty_view = UIView.alloc().init()
                    native_field.inputView = empty_view
                    
                    # Also prevent keyboard from showing on tap
                    # Set tintColor to clear to hide cursor
                    UIColor = ObjCClass('UIColor')
                    native_field.tintColor = UIColor.clearColor

                except Exception as e:
                    pass
                    import traceback
                    traceback.print_exc()
                    
        except Exception as e:
            pass
    
    def disable_android_keyboard(self):
        """Disable Android soft keyboard, remove input underline, hide action bar."""
        import sys
        if sys.platform != 'android':
            return
        try:
            from android import activity

            # Hide the green action bar / toolbar
            try:
                action_bar = activity.getSupportActionBar()
                if action_bar:
                    action_bar.hide()
            except Exception:
                pass
            try:
                action_bar = activity.getActionBar()
                if action_bar:
                    action_bar.hide()
            except Exception:
                pass
            # Also try finding and hiding the toolbar view directly
            try:
                from android.view import View
                decor = activity.getWindow().getDecorView()
                root = decor.getRootView()
                self._hide_toolbar_recursive(root)
            except Exception:
                pass

            from android.view.inputmethod import InputMethodManager
            if hasattr(self.input_field, '_impl') and hasattr(self.input_field._impl, 'native'):
                native_field = self.input_field._impl.native
                native_field.setShowSoftInputOnFocus(False)
                # Remove the Material Design underline
                from android.graphics.drawable import ColorDrawable
                from android.graphics import Color
                bg = ColorDrawable(Color.parseColor("#2a2a2a"))
                native_field.setBackground(bg)
                native_field.setBackgroundDrawable(bg)
                # Also clear the tint that draws the colored underline
                try:
                    from java.lang import Class
                    # Use ViewCompat to clear background tint
                    from androidx.core.view import ViewCompat
                    ViewCompat.setBackgroundTintList(native_field, None)
                except Exception:
                    try:
                        native_field.setBackgroundTintList(None)
                    except Exception:
                        pass
                imm = activity.getSystemService(activity.INPUT_METHOD_SERVICE)
                if imm:
                    imm.hideSoftInputFromWindow(native_field.getWindowToken(), 0)
        except Exception:
            pass

    def _hide_toolbar_recursive(self, view):
        """Walk the Android view tree and hide any Toolbar or ActionBar views."""
        try:
            from android.view import View, ViewGroup
            class_name = view.getClass().getName()
            if 'Toolbar' in class_name or 'ActionBar' in class_name:
                view.setVisibility(View.GONE)
                return
            if isinstance(view, ViewGroup):
                for i in range(view.getChildCount()):
                    self._hide_toolbar_recursive(view.getChildAt(i))
        except Exception:
            pass

    def _schedule_android_ui_fixes(self):
        """Post delayed UI fixes so they run after Android finishes laying out views."""
        import sys
        if sys.platform != 'android':
            return
        try:
            from android import activity
            decor = activity.getWindow().getDecorView()

            class Fixer:
                def __init__(self, app):
                    self.app = app
                def run(self):
                    self.app._apply_android_ui_fixes()

            fixer = Fixer(self)
            # Post to the UI thread's message queue so it runs after layout
            from java import dynamic_proxy
            from java.lang import Runnable

            class RunnableProxy(dynamic_proxy(Runnable)):
                def __init__(self, callback):
                    super().__init__()
                    self.callback = callback
                def run(self):
                    self.callback()

            decor.postDelayed(RunnableProxy(fixer.run), 500)
        except Exception:
            pass

    def _apply_android_ui_fixes(self):
        """Apply UI fixes after Android views are fully laid out."""
        import sys
        if sys.platform != 'android':
            return
        try:
            from android import activity
            from android.view import View

            # Hide toolbar
            decor = activity.getWindow().getDecorView()
            self._hide_toolbar_recursive(decor)

            # Fix input underline
            if hasattr(self.input_field, '_impl') and hasattr(self.input_field._impl, 'native'):
                native_field = self.input_field._impl.native
                from android.graphics.drawable import ColorDrawable
                from android.graphics import Color
                bg = ColorDrawable(Color.parseColor("#2a2a2a"))
                native_field.setBackground(bg)
                try:
                    native_field.setBackgroundTintList(None)
                except Exception:
                    pass
        except Exception:
            pass

    def set_input_visibility(self):
        """Manage keyboard visibility by focusing input when needed."""
        
        # Only show keyboard during character name entry
        if gs.prompt_cntl == 'player_name':
            self.input_field.placeholder = "Type your name..."
            self.input_field.value = ""
        else:
            # Just clear placeholder
            self.input_field.placeholder = ""

    def update_button_panel(self, commands_text, needs_numbers=False):
        """..."""

        # Store needs_numbers state for quick_command behavior
        self.current_needs_numbers = needs_numbers

        # Update command display label
        self.command_display.text = commands_text if commands_text else ""

        # Clear existing buttons and restore standard 3-row COLUMN layout
        self.button_row_1.clear()
        self.button_row_2.clear()
        self.number_pad_box.clear()
        self.button_panel.clear()
        self.button_panel.style.direction = COLUMN
        self.button_panel.add(self.button_row_1)
        self.button_panel.add(self.button_row_2)
        self.button_panel.add(self.number_pad_box)

        # Compact input row buttons (remove Android Material insets that clip text)
        self._compact_android_button(self.submit_button)
        self._compact_android_button(self.backspace_button)
        self._style_android_button(self.submit_button, bg_start='#555555', bg_end='#383838',
                                    pressed_start='#383838', pressed_end='#222222',
                                    border_color='#666666')
        self._style_android_button(self.backspace_button)

        # Adjust panel heights based on mode
        if gs.prompt_cntl in ('player_name', 'puzzle_mode'):
            # QWERTY keyboard: 3 rows × 34px keys + margins
            self.bottom_panel.style.height = 200
            self.button_panel.style.height = 114
        elif needs_numbers:
            # Numpad layout: 4 rows × 24px compact keys
            self.bottom_panel.style.height = 170
            self.button_panel.style.height = 98
        else:
            # Normal: 3 rows × 30px buttons
            self.bottom_panel.style.height = 145
            self.button_panel.style.height = 96

        # Special case: Intro/Main menu - show save slots if saves exist, otherwise empty
        if gs.prompt_cntl in ['intro_story', 'main_menu']:
            self.build_main_menu_layout()
            return

        # Special case: Game loaded summary - just empty buttons, use Send
        if gs.prompt_cntl == 'game_loaded_summary':
            return

        # Special case: Save/Load menu
        if gs.prompt_cntl == 'save_load_mode':
            self.build_save_load_layout({})
            return

        # Special case: QWERTY keyboard for name entry
        if gs.prompt_cntl == 'player_name':
            self.build_qwerty_keyboard_layout()
            return

        # Special case: QWERTY keyboard for Zotle puzzle
        if gs.prompt_cntl == 'puzzle_mode':
            self.build_qwerty_keyboard_layout()
            return

        # Special case: Zotle Teleporter - number pad with comma
        if gs.prompt_cntl == 'zotle_teleporter_mode':
            self.build_teleporter_layout()
            return

        # Special case: Combat mode - custom layout with C, A, spacer, F
        if gs.prompt_cntl == 'combat_mode':
            commands = self.parse_commands(commands_text)
            cmd_dict = {key: label for key, label in commands}
            self.build_combat_layout(cmd_dict)
            return

        # Special case: Inventory (no filter) — explicit 3x3 grid layout
        if gs.prompt_cntl == 'inventory' and not gs.inventory_filter:
            self.build_inventory_layout()
            return

        # Parse commands from text
        commands = self.parse_commands(commands_text)

        # Build layout based on mode
        if needs_numbers:
            self.build_layout_with_numpad(commands)
        else:
            self.build_layout_no_numpad(commands)

    def build_main_menu_layout(self):
        """
        Build main menu layout - show load slots if saves exist.

        Row 1: [.][.][.]  [.][.][.]  [1][2][3]  (load slots on right if saves exist)
        Row 2: [.][.][.]  [.][.][.]  [.][.][.]
        Row 3: [.][.][.]  [.][.][.]  [.][.][.]

        User presses Send to start new game, or 1/2/3 to load.
        """
        # Check if any saves exist
        saves = SaveSystem.list_saves()
        has_saves = any(not s['empty'] for s in saves)

        if has_saves:
            # Show load buttons for existing saves on the right
            slot_buttons = []
            for save in saves:
                slot = save['slot']
                if not save['empty']:
                    slot_buttons.append(self.create_button(str(slot), str(slot)))
                else:
                    slot_buttons.append(self.create_spacer())
            # Ensure exactly 3 slot buttons
            while len(slot_buttons) < 3:
                slot_buttons.append(self.create_spacer())
            row1 = [self.create_spacer() for _ in range(6)] + slot_buttons[:3]
        else:
            row1 = [self.create_spacer() for _ in range(9)]

        row2 = [self.create_spacer() for _ in range(9)]
        row3 = [self.create_spacer() for _ in range(9)]

        for btn in row1:
            self.button_row_1.add(btn)
        for btn in row2:
            self.button_row_2.add(btn)
        for btn in row3:
            self.number_pad_box.add(btn)

    def build_combat_layout(self, cmd_dict):
        """
        Build combat layout with C (cast), A (attack), spacer, F (flee).
        
        Layout:
        Row 1: [.][.][.] [C][A][.][F][.][.]  (C only if can cast)
        Row 2: [.][.][.] [I][.][.][.][.][Q]
        Row 3: [.][.][.] [.][.][.][.][.][.]
        """
        has_cast = 'c' in cmd_dict
        
        # Left side empty (no d-pad in combat)
        right_row1 = [self.create_spacer() for _ in range(3)]
        right_row2 = [self.create_spacer() for _ in range(3)]
        right_row3 = [self.create_spacer() for _ in range(3)]
        
        # Right side: Combat commands
        # Row 1: [C][A][spacer][F][spacer][spacer] or [spacer][A][spacer][F][spacer][spacer]
        if has_cast:
            left_row1 = [
                self.create_big_button('a', 'Attack'),
                self.create_big_button('c', 'Cast'),
                self.create_spacer(),
                self.create_spacer(),
                self.create_big_button('f', 'Flee'),
                self.create_spacer(),
            ]
        else:
            left_row1 = [
                self.create_big_button('a', 'Attack'),
                self.create_spacer(),
                self.create_spacer(),
                self.create_spacer(),
                self.create_big_button('f', 'Flee'),
                self.create_spacer(),
            ]

        # Row 2: [Inventory][spacers]
        left_row2 = [
            self.create_big_button('i', 'Inventory') if 'i' in cmd_dict else self.create_spacer(),
            self.create_spacer(),
            self.create_spacer(),
            self.create_spacer(),
            self.create_spacer(),
            self.create_spacer(),
        ]
        
        # Row 3: All spacers
        left_row3 = [self.create_spacer() for _ in range(6)]
        
        # Add to rows
        for btn in left_row1 + right_row1:
            self.button_row_1.add(btn)
        for btn in left_row2 + right_row2:
            self.button_row_2.add(btn)
        for btn in left_row3 + right_row3:
            self.number_pad_box.add(btn)

    def build_layout_no_numpad(self, commands):
        """
        D-pad on left, command buttons in columns from bottom-right going up.
        New columns added to the left when a column fills (3 buttons max).

        Layout: [D-PAD (3 cols)] [fillers] [CMD cols right-aligned]
        """
        cmd_dict = {key: label for key, label in commands}
        # Movement directions have single-char uppercase labels (N/S/E/W) from "n/s/e/w = move"
        # Non-movement uses of n/s/e/w (like "n = no") have longer labels (No, Enter, etc.)
        move_keys = {k for k, label in commands if k in ('n', 's', 'e', 'w') and len(label) == 1}
        has_movement = bool(move_keys)

        # === LEFT SIDE: D-PAD (cross/plus shape with arrow symbols) ===
        if has_movement:
            dpad_row1 = [
                self.create_dpad_spacer(),
                self.create_dpad_button('n', '\u25B2') if 'n' in move_keys else self.create_dpad_spacer(),
                self.create_dpad_spacer(),
            ]
            dpad_row2 = [
                self.create_dpad_button('w', '\u25C4') if 'w' in move_keys else self.create_dpad_spacer(),
                self.create_dpad_center(),
                self.create_dpad_button('e', '\u25BA') if 'e' in move_keys else self.create_dpad_spacer(),
            ]
            dpad_row3 = [
                self.create_dpad_spacer(),
                self.create_dpad_button('s', '\u25BC') if 's' in move_keys else self.create_dpad_spacer(),
                self.create_dpad_spacer(),
            ]
        else:
            dpad_row1 = [self.create_dpad_spacer() for _ in range(3)]
            dpad_row2 = [self.create_dpad_spacer() for _ in range(3)]
            dpad_row3 = [self.create_dpad_spacer() for _ in range(3)]

        # === RIGHT SIDE: COMMANDS (columns, bottom-right going up then left) ===
        # Only exclude actual movement keys from command buttons (not n=no, etc.)

        # Priority order (first = bottom-right, most important)
        priority = ['l', 'i', 'q', 'o', 'dr', 'g', 'r', 'u', 'd', 'p', 'h', 'c',
                     'y', 'n', 'x', 'a', 'f', 'b', 'm', 'j',
                     '1', '2', '3', '4', '5', '6', '7', '8', '9']

        cmds_to_place = []
        placed = set()
        for pkey in priority:
            if pkey in cmd_dict and pkey not in move_keys and pkey not in placed:
                cmds_to_place.append((pkey, cmd_dict[pkey]))
                placed.add(pkey)
        for k, v in cmd_dict.items():
            if k not in move_keys and k not in placed:
                cmds_to_place.append((k, v))

        # Build columns (max 3 per column, bottom to top)
        # columns[0] = rightmost column
        columns = []
        for i in range(0, len(cmds_to_place), 3):
            columns.append(cmds_to_place[i:i+3])

        num_cols = len(columns)
        cmd_row1 = []
        cmd_row2 = []
        cmd_row3 = []

        # Build left-to-right: leftmost column first (= last in columns list)
        for col_idx in range(num_cols - 1, -1, -1):
            col = columns[col_idx]
            cmd_row3.append(self.create_button(col[0][0], col[0][1]) if len(col) > 0 else self.create_spacer())
            cmd_row2.append(self.create_button(col[1][0], col[1][1]) if len(col) > 1 else self.create_spacer())
            cmd_row1.append(self.create_button(col[2][0], col[2][1]) if len(col) > 2 else self.create_spacer())

        if has_movement:
            for btn in dpad_row1 + [self.create_spacer()] + cmd_row1:
                self.button_row_1.add(btn)
            for btn in dpad_row2 + [self.create_spacer()] + cmd_row2:
                self.button_row_2.add(btn)
            for btn in dpad_row3 + [self.create_spacer()] + cmd_row3:
                self.number_pad_box.add(btn)
        elif len(cmds_to_place) <= 4:
            # Few buttons, no D-pad: arrange all in a single centered row
            row_buttons = [self.create_button(k, v) for k, v in cmds_to_place]
            for btn in [self.create_spacer()] + row_buttons + [self.create_spacer()]:
                self.number_pad_box.add(btn)
        else:
            # No D-pad: center the command buttons in columns
            for btn in [self.create_spacer()] + cmd_row1 + [self.create_spacer()]:
                self.button_row_1.add(btn)
            for btn in [self.create_spacer()] + cmd_row2 + [self.create_spacer()]:
                self.button_row_2.add(btn)
            for btn in [self.create_spacer()] + cmd_row3 + [self.create_spacer()]:
                self.number_pad_box.add(btn)

    def build_inventory_layout(self):
        """Explicit 3x3 grid for inventory (no filter active).

        Row 1: Equip | Eat   | Use
        Row 2: Journal| Craft | Spells (if can cast, else spacer)
        Row 3: Exit  | spacer| Quit

        All cells use flex=1 so columns align perfectly across rows.
        """
        can_cast = False
        try:
            from .game_systems import can_cast_spells
            can_cast = can_cast_spells(gs.player_character)
        except Exception:
            pass

        in_combat = gs.active_monster and gs.active_monster.is_alive() if gs.active_monster else False

        def flex_btn(key, label):
            btn = toga.Button(
                label,
                on_press=lambda w, k=key, l=label: self.quick_command(k, l),
                style=Pack(flex=1, margin=1, font_size=11, height=30,
                           background_color='#383838', color='#EEE')
            )
            self._compact_android_button(btn)
            self._style_android_button(btn)
            return btn

        def flex_spacer():
            return toga.Box(style=Pack(flex=1, height=30))

        row1 = [flex_btn('e', 'Equip'), flex_btn('eat', 'Eat'), flex_btn('u', 'Use')]
        row2 = [
            flex_btn('j', 'Journal'),
            flex_btn('c', 'Craft'),
            flex_btn('m', 'Spells') if can_cast else flex_spacer(),
        ]
        row3 = [
            flex_btn('x', 'Exit'),
            flex_spacer(),
            flex_btn('q', 'Quit') if not in_combat else flex_spacer(),
        ]

        for btn in row1:
            self.button_row_1.add(btn)
        for btn in row2:
            self.button_row_2.add(btn)
        for btn in row3:
            self.number_pad_box.add(btn)

    def build_layout_with_numpad(self, commands):
        """
        Two-column layout: back button on the left, 3x3 numpad centered.
        Bigger buttons than before; the numpad dominates because that's what
        the player taps most in filter modes.
        """
        cmd_dict = {key: label for key, label in commands}
        is_altar = gs.prompt_cntl == 'altar_mode'

        # Separate numpad keys from command keys
        numpad_keys = set(str(i) for i in range(10))

        # Find the back/exit command for the left-side button
        back_key = None
        back_label = None
        for k in ['b', 'x', 'c']:
            if k in cmd_dict and k not in numpad_keys:
                back_key = k
                back_label = cmd_dict[k]
                break

        # Left column: back button vertically centered
        left_col = toga.Box(style=Pack(direction=COLUMN, width=52))
        left_col.add(toga.Box(style=Pack(flex=1)))  # top spacer
        if back_key:
            back_btn = toga.Button(
                back_label,
                on_press=lambda w, ck=back_key, cl=back_label: self.quick_command(ck, cl),
                style=Pack(width=48, margin=1, font_size=10,
                           background_color='#383838', color='#EEE', height=34)
            )
            self._compact_android_button(back_btn)
            self._style_android_button(back_btn)
            left_col.add(back_btn)
        # "Drink Full" button when available
        if 'df' in cmd_dict:
            df_btn = toga.Button(
                'Heal', on_press=lambda w: self.quick_command('df', 'Heal'),
                style=Pack(width=48, margin=1, font_size=9, font_weight='bold',
                           background_color='#2a3a2a', color='#4CAF50', height=34))
            self._compact_android_button(df_btn)
            self._style_android_button(df_btn, bg_start='#2a3a2a', bg_end='#1a2a1a',
                                        border_color='#4CAF50')
            left_col.add(df_btn)
        # Altar sacrifice button
        if is_altar and 's' in cmd_dict:
            sac_btn = toga.Button(
                'Sac', on_press=lambda w: self.number_pad_input('s'),
                style=Pack(width=48, margin=1, font_size=10, font_weight='bold',
                           background_color='#383838', color='#FFD700', height=34))
            self._compact_android_button(sac_btn)
            self._style_android_button(sac_btn)
            left_col.add(sac_btn)
        left_col.add(toga.Box(style=Pack(flex=1)))  # bottom spacer

        # Right column: numpad with bigger buttons (3x3 + bottom row with 0)
        numpad_rows = [
            [self.create_numpad_button('1'), self.create_numpad_button('2'), self.create_numpad_button('3')],
            [self.create_numpad_button('4'), self.create_numpad_button('5'), self.create_numpad_button('6')],
            [self.create_numpad_button('7'), self.create_numpad_button('8'), self.create_numpad_button('9')],
            [toga.Box(style=Pack(flex=1)), self.create_numpad_button('0'), toga.Box(style=Pack(flex=1))],
        ]

        # Altar: special devotion rune button 9
        if is_altar:
            can_offer = (
                not gs.runes_obtained.get('devotion', False) and
                gs.player_character is not None and
                gs.player_character.gold >= gs.rune_progress_reqs.get('gold_obtained', 500) and
                gs.player_character.health >= gs.rune_progress_reqs.get('player_health_obtained', 50)
            )
            if can_offer:
                numpad_rows[2][2] = toga.Button(
                    '9', on_press=lambda w: self.number_pad_input('9'),
                    style=Pack(flex=1, margin=1, font_size=13, font_weight='bold',
                               color='#FFD700', height=30, background_color='#2a2a2a'))

        right_col = toga.Box(style=Pack(direction=COLUMN, flex=1))
        for row_btns in numpad_rows:
            row_box = toga.Box(style=Pack(direction=ROW, margin=0, flex=1))
            for btn in row_btns:
                row_box.add(btn)
            right_col.add(row_box)

        # Replace standard 3-row layout with two-column ROW layout
        self.button_panel.clear()
        self.button_panel.style.direction = ROW
        self.button_panel.add(left_col)
        self.button_panel.add(toga.Box(style=Pack(width=4)))  # gap
        self.button_panel.add(right_col)

    def build_teleporter_layout(self):
        """
        Teleporter: comma and cancel on left, 4-row numpad on right.
        """
        # Left column: comma and cancel buttons in 3 rows
        left_col = toga.Box(style=Pack(direction=COLUMN, flex=1))
        for row_btns in [[self.create_spacer()], [self.create_numpad_button(',')], [self.create_button('c', 'C')]]:
            row_box = toga.Box(style=Pack(direction=ROW, margin=0, flex=1))
            for btn in row_btns:
                row_box.add(btn)
            left_col.add(row_box)

        # Right column: 4-row phone-style numpad
        right_col = toga.Box(style=Pack(direction=COLUMN))
        for row_btns in [
            [self.create_numpad_button('1', compact=True), self.create_numpad_button('2', compact=True), self.create_numpad_button('3', compact=True)],
            [self.create_numpad_button('4', compact=True), self.create_numpad_button('5', compact=True), self.create_numpad_button('6', compact=True)],
            [self.create_numpad_button('7', compact=True), self.create_numpad_button('8', compact=True), self.create_numpad_button('9', compact=True)],
            [self.create_numpad_button('0', compact=True)],
        ]:
            row_box = toga.Box(style=Pack(direction=ROW, margin=0))
            for btn in row_btns:
                row_box.add(btn)
            right_col.add(row_box)

        self.button_panel.clear()
        self.button_panel.style.direction = ROW
        self.button_panel.add(left_col)
        self.button_panel.add(right_col)

    def build_save_load_layout(self, cmd_dict):
        """
        Build save/load menu layout.

        Row 1: [fillers] [1][2][3]
        Row 2: [fillers] [O1][O2][O3]
        Row 3: [X] [fillers]
        """
        row1 = self.build_row([], [self.create_button('1', '1'), self.create_button('2', '2'), self.create_button('3', '3')])
        row2 = self.build_row([], [self.create_button('o1', 'O1'), self.create_button('o2', 'O2'), self.create_button('o3', 'O3')])
        row3 = self.build_row([self.create_button('x', 'X')], [])

        for btn in row1: self.button_row_1.add(btn)
        for btn in row2: self.button_row_2.add(btn)
        for btn in row3: self.number_pad_box.add(btn)

    def toggle_keyboard_case(self, widget):
        """Toggle between uppercase and lowercase keyboard."""
        self.keyboard_uppercase = not self.keyboard_uppercase
        # Rebuild the keyboard with new case
        self.update_button_panel(self.command_display.text, needs_numbers=False)

    def zotle_backspace(self, widget):
        """Remove the last entered letter from the Zotle current guess."""
        if gs.zotle_puzzle and 'current_guess' in gs.zotle_puzzle:
            for i in range(4, -1, -1):
                if gs.zotle_puzzle['current_guess'][i]:
                    gs.zotle_puzzle['current_guess'][i] = ''
                    break
        self.render()
    
    def build_qwerty_keyboard_layout(self):
        """
        Build QWERTY keyboard layout for name entry.

        Row 1: [Q][W][E][R][T][Y][U][I][O][P]
        Row 2: [.][A][S][D][F][G][H][J][K][L][.]
        Row 3: [\u21e7][Z][X][C][V][B][N][M][.]

        Backspace and Send buttons are in the input row at the bottom
        """
        # Determine case based on shift state
        if not hasattr(self, 'keyboard_uppercase'):
            self.keyboard_uppercase = True  # Start with uppercase

        # Row 1: Q W E R T Y U I O P (10 buttons - full top row!)
        row1_letters = ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P']
        if self.keyboard_uppercase:
            row1 = [self.create_keyboard_button(letter.lower(), letter) for letter in row1_letters]
        else:
            row1 = [self.create_keyboard_button(letter.lower(), letter.lower()) for letter in row1_letters]

        # Row 2: A S D F G H J K L (9 buttons, centered with half-spacers on both sides)

        row2_letters = ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L']

        row2 = [self.create_half_spacer()]  # Left half spacer
        if self.keyboard_uppercase:
            row2.extend([self.create_keyboard_button(letter.lower(), letter) for letter in row2_letters])
        else:
            row2.extend([self.create_keyboard_button(letter.lower(), letter.lower()) for letter in row2_letters])
        row2.append(self.create_half_spacer())  # Right half spacer for centering

        # Row 3: Shift + Z X C V B N M + trailing spacer
        row3_letters = ['Z', 'X', 'C', 'V', 'B', 'N', 'M']
        # Shift button: highlighted when uppercase is active
        shift_bg = '#666' if self.keyboard_uppercase else '#333'
        shift_color = '#FFF' if self.keyboard_uppercase else '#999'
        shift_button = toga.Button(
            "\u21e7",
            on_press=self.toggle_keyboard_case,
            style=Pack(width=38, margin=1, padding=0, font_size=11,
                       background_color=shift_bg, color=shift_color, height=34)
        )
        self._compact_android_button(shift_button)
        self._style_android_button(shift_button)
        row3 = [shift_button]
        if self.keyboard_uppercase:
            row3.extend([self.create_keyboard_button(letter.lower(), letter) for letter in row3_letters])
        else:
            row3.extend([self.create_keyboard_button(letter.lower(), letter.lower()) for letter in row3_letters])
        # Add backspace button (only active during puzzle mode)
        if gs.prompt_cntl == 'puzzle_mode':
            backspace_button = toga.Button(
                '<-',
                on_press=self.zotle_backspace,
                style=Pack(flex=1, margin=0, padding=0, font_size=13, font_weight='bold',
                           background_color='#333', color='#EEE', height=34)
            )
            row3.append(backspace_button)
        row3.append(toga.Box(style=Pack(flex=1, height=34)))  # Trailing spacer

        # Add to button rows
        for btn in row1:
            self.button_row_1.add(btn)
        for btn in row2:
            self.button_row_2.add(btn)
        for btn in row3:
            self.number_pad_box.add(btn)
    
    def create_keyboard_button(self, cmd_key, cmd_label):
        """Create a keyboard button for QWERTY layout (fits 10 per row)."""
        btn = toga.Button(
            cmd_label,
            on_press=lambda w, k=cmd_key, l=cmd_label: self.quick_command(k, l),
            style=Pack(flex=1, margin=1, padding=0, font_size=12,
                       background_color='#333', color='#EEE', height=34)
        )
        self._compact_android_button(btn)
        self._style_android_button(btn, corner_dp=4)
        return btn

    def _compact_android_button(self, btn):
        """Remove Android Material button internal padding, elevation, and minimum sizes."""
        import sys
        if sys.platform != 'android':
            return
        try:
            if hasattr(btn, '_impl') and hasattr(btn._impl, 'native'):
                native = btn._impl.native
                native.setPadding(4, 0, 4, 0)
                native.setMinWidth(0)
                native.setMinimumWidth(0)
                native.setMinHeight(0)
                native.setMinimumHeight(0)
                # Remove Material insets (top/bottom padding added by MaterialButton)
                native.setInsetTop(0)
                native.setInsetBottom(0)
                # Remove elevation/shadow which adds vertical space between buttons
                native.setStateListAnimator(None)
                native.setElevation(0)
        except Exception:
            pass

    def _style_android_button(self, btn, bg_start='#484848', bg_end='#303030',
                               pressed_start='#2a2a2a', pressed_end='#1a1a1a',
                               border_color='#5a5a5a', corner_dp=6):
        """Apply rounded gradient background with pressed state to Android button."""
        import sys
        if sys.platform != 'android':
            return
        try:
            if not (hasattr(btn, '_impl') and hasattr(btn._impl, 'native')):
                return
            native = btn._impl.native

            from android.graphics.drawable import GradientDrawable, StateListDrawable
            from android.graphics import Color

            density = native.getContext().getResources().getDisplayMetrics().density
            corner_px = float(int(corner_dp * density))
            border_px = max(1, int(1 * density))

            def make_drawable(top_hex, bot_hex):
                gd = GradientDrawable()
                gd.setCornerRadius(corner_px)
                gd.setStroke(border_px, Color.parseColor(border_color))
                # Try gradient first, fall back to solid color
                try:
                    gd.setOrientation(GradientDrawable.Orientation.TOP_BOTTOM)
                    gd.setColors([Color.parseColor(top_hex), Color.parseColor(bot_hex)])
                except Exception:
                    gd.setColor(Color.parseColor(top_hex))
                return gd

            normal = make_drawable(bg_start, bg_end)
            pressed = make_drawable(pressed_start, pressed_end)

            sld = StateListDrawable()
            # android.R.attr.state_pressed = 16842919
            sld.addState([16842919], pressed)
            sld.addState([], normal)

            native.setBackground(sld)
            native.setElevation(float(int(density)))
        except Exception:
            pass
    
    def fill_row(self, cmd_dict, priority, num_buttons):
        """Fill a row with buttons based on priority list."""
        buttons = []
        used_keys = set()
        
        for key in priority:
            if key in cmd_dict and len(buttons) < num_buttons:
                buttons.append(self.create_button(key, cmd_dict[key]))
                used_keys.add(key)
        
        # Fill remaining with other commands
        for key, label in cmd_dict.items():
            if key not in used_keys and len(buttons) < num_buttons:
                buttons.append(self.create_button(key, label))
                used_keys.add(key)
        
        # Fill remaining with spacers
        while len(buttons) < num_buttons:
            buttons.append(self.create_spacer())
        
        return buttons
    
    def create_button(self, cmd_key, cmd_label):
        """Create a command button with rounded gradient styling."""
        btn = toga.Button(
            cmd_label,
            on_press=lambda w, k=cmd_key, l=cmd_label: self.quick_command(k, l),
            style=Pack(margin=1, font_size=11, width=95,
                       background_color='#383838', color='#EEE', height=30)
        )
        self._compact_android_button(btn)
        self._style_android_button(btn)
        return btn

    def create_big_button(self, cmd_key, cmd_label):
        """Create a larger button for important combat actions."""
        btn = toga.Button(
            cmd_label,
            on_press=lambda w, k=cmd_key, l=cmd_label: self.quick_command(k, l),
            style=Pack(margin=1, font_size=12, font_weight='bold', width=100, height=30,
                       background_color='#444', color='#FFF')
        )
        self._compact_android_button(btn)
        self._style_android_button(btn, bg_start='#555555', bg_end='#383838',
                                    pressed_start='#383838', pressed_end='#222222',
                                    border_color='#666666')
        return btn

    def create_numpad_button(self, number, compact=False):
        """Create a number pad button. Compact mode uses shorter height for 4-row layout."""
        h = 24 if compact else 30
        fs = 11 if compact else 13
        btn = toga.Button(
            number,
            on_press=lambda w, n=number: self.number_pad_input(n),
            style=Pack(margin=1, font_size=fs, font_weight='bold', flex=1,
                       color='#4CAF50', height=h, background_color='#2a2a2a')
        )
        self._compact_android_button(btn)
        self._style_android_button(btn, bg_start='#333333', bg_end='#222222',
                                    pressed_start='#1a1a1a', pressed_end='#111111',
                                    border_color='#444444')
        return btn

    def create_spacer(self):
        """Create an empty spacer that fills remaining space."""
        return toga.Box(style=Pack(flex=1, height=30))
    def create_dpad_button(self, cmd_key, arrow_label):
        """Create a D-pad directional button with arrow symbol and controller styling."""
        btn = toga.Button(
            arrow_label,
            on_press=lambda w, k=cmd_key: self.quick_command(k, cmd_key.upper()),
            style=Pack(margin=0, font_size=13, font_weight='bold', width=44,
                       background_color='#2a2a2a', color='#AAA', height=30)
        )
        self._compact_android_button(btn)
        self._style_android_button(btn, bg_start='#3a3a3a', bg_end='#222222',
                                    pressed_start='#222222', pressed_end='#111111',
                                    border_color='#4a4a4a', corner_dp=8)
        return btn

    def create_dpad_center(self):
        """Create the center piece of the D-pad cross."""
        return toga.Box(style=Pack(width=44, height=30, background_color='#222'))

    def create_dpad_spacer(self):
        """Create an invisible corner spacer for D-pad cross shape."""
        return toga.Box(style=Pack(width=44, height=30, background_color='#1a1a1a'))
    def create_filler(self):
        """Create a small gap between button groups."""
        return toga.Box(style=Pack(width=2))
    def create_half_spacer(self):
        """Create a half-width spacer for keyboard offset."""
        return toga.Box(style=Pack(margin=1, width=18))

    def build_row(self, left_buttons, right_buttons):
        """Build a row with left-aligned commands, expanding gap, right-aligned numpad."""
        widgets = list(left_buttons)
        widgets.append(toga.Box(style=Pack(flex=3)))  # expanding gap
        widgets.extend(right_buttons)
        return widgets
    
    def parse_commands(self, commands_text):
        """
        Parse command string into list of (key, label) tuples.
        
        Example: "a = attack | f = flee" -> [('a', 'A'), ('f', 'F')]
        Special: "n/s/e/w = move" -> [('n', 'N'), ('s', 'S'), ('e', 'E'), ('w', 'W')]
        Special: "1-8 = pray" -> [('1', '1'), ('2', '2'), ... ('8', '8')]
        """
        if not commands_text:
            return []
        
        commands = []
        parts = commands_text.split('|')
        
        for part in parts:
            part = part.strip()
            if '=' in part:
                key, label = part.split('=', 1)
                key = key.strip()
                label = label.strip()
                
                # Special case: Handle "n/s/e/w = move" or "n/s/w/e = move" etc.
                if '/' in key and any(dir in key.split('/') for dir in ['n', 's', 'e', 'w']):
                    # Split into individual direction commands
                    directions = key.split('/')
                    for direction in directions:
                        direction = direction.strip()
                        if direction in ['n', 's', 'e', 'w']:
                            commands.append((direction, direction.upper()))
                    continue
                
                # Special case: Handle number ranges like "1-8"
                if '-' in key and key.replace('-', '').replace(' ', '').isdigit():
                    # Parse range like "1-8"
                    parts_range = key.split('-')
                    if len(parts_range) == 2:
                        try:
                            start = int(parts_range[0].strip())
                            end = int(parts_range[1].strip())
                            for num in range(start, end + 1):
                                commands.append((str(num), str(num)))
                            continue
                        except ValueError:
                            pass  # Fall through to normal processing
                
                # Special case: Handle "p1-p8" or "p1-p9" format for altar prayers
                if '-' in key and key.startswith('p') and key[1:].replace('-', '').replace('p', '').isdigit():
                    # Parse range like "p1-p8" -> adds 'p' command and numbers 1-8
                    parts_range = key.split('-')
                    if len(parts_range) == 2:
                        try:
                            start = int(parts_range[0].strip()[1:])  # Remove 'p' prefix
                            end = int(parts_range[1].strip()[1:])    # Remove 'p' prefix
                            commands.append(('p', 'P'))  # Add the pray command
                            for num in range(start, end + 1):
                                commands.append((str(num), str(num)))
                            continue
                        except ValueError:
                            pass  # Fall through to normal processing
                
                # Extract command from patterns like "b#" or "u#" or "b [number]"
                # Remove # symbol or take first word before space
                if '#' in key:
                    actual_cmd = key.replace('#', '').strip()
                elif ' ' in key:
                    actual_cmd = key.split()[0]
                else:
                    actual_cmd = key
                
                # Use full descriptive label for button text
                btn_label = label.strip().capitalize() if len(label) > 1 else actual_cmd.upper()
                
                commands.append((actual_cmd, btn_label))
        
        return commands
    
    
    def number_pad_input(self, char):
        """Handle number pad input."""
        self.input_field.value += char
        self.input_field.focus()
    
    def number_pad_backspace(self):
        """Handle backspace on number pad."""
        current = self.input_field.value
        if current:
            self.input_field.value = current[:-1]
        self.input_field.focus()
    
    def on_input_confirm(self, widget):
        """Handle Send button or Enter key press in input field."""
        # Enter was pressed - process the command
        self.on_command_submit(widget)
    
    def on_command_submit(self, widget):
        """Handle command submission from input field."""
        
        # Get command
        cmd = self.input_field.value.strip().lower()
        self.input_field.value = ""
        
        # Check if game should quit
        if gs.game_should_quit:
            self.main_window.close()
            return
        
        # Process the command using your existing game logic
        self.process_command(cmd)

        # Check if game should quit (e.g. after death screen)
        if gs.game_should_quit:
            self.render()
            self.main_window.close()
            return

        # Re-render the display
        self.render()
        
        # Keep focus on input
        self.input_field.focus()
    
    def process_command(self, cmd):

        # cmd is already passed in and processed by on_command_submit
        
        if gs.game_should_quit:
            return

        # Handle splash screen - any input skips to intro
        if gs.prompt_cntl == "splash":
            if hasattr(self, '_splash_timer'):
                self._splash_timer.cancel()
            gs.prompt_cntl = "intro_story"
            return

        # Handle death screen - any key closes the game and deletes save
        if gs.prompt_cntl == "death_screen":
            add_log("Thanks for playing Wizard's Cavern!")
            # Delete save files on death (permadeath)
            for slot in range(1, gs.MAX_SAVE_SLOTS + 1):
                SaveSystem.delete_save(slot)
            add_log(f"{COLOR_RED}Your save files have been deleted. Death is permanent in the Cavern.{COLOR_RESET}")
            gs.game_should_quit = True
            return

        if gs.prompt_cntl == "confirm_quit":
            if cmd == 'y':
                add_log("You have quit the game. Goodbye!")
                gs.game_should_quit = True
                return
            elif cmd == 'n':
                gs.prompt_cntl = gs.previous_prompt_cntl
                add_log("Resuming game...")
                return
            else:
                add_log("Are you sure you want to quit? (y/n)")
                return

        if cmd == 'q':
            gs.previous_prompt_cntl = gs.prompt_cntl
            gs.prompt_cntl = "confirm_quit"
            add_log("Are you sure you want to quit? (y/n)")
            return

        if cmd == 'v':
            gs.music_enabled = not gs.music_enabled
            state = "on" if gs.music_enabled else "off"
            add_log(f"Music toggled {state}.")
            return

        if cmd == 'i' and gs.prompt_cntl == "game_loop":
            gs.prompt_cntl = "inventory"
            gs.inventory_filter = None
            handle_inventory_menu(gs.player_character, gs.my_tower, "init")
            return

        # ADD THIS NEW BLOCK FOR LANTERN
        if cmd == 'l' and gs.prompt_cntl == "game_loop":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            return

        # Allow lantern use in chest mode
        if cmd == 'l' and gs.prompt_cntl == "chest_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in pool mode
        if cmd == 'l' and gs.prompt_cntl == "pool_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in altar mode
        if cmd == 'l' and gs.prompt_cntl == "altar_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in library mode
        if cmd == 'l' and gs.prompt_cntl == "library_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in stairs_up_mode
        if cmd == 'l' and gs.prompt_cntl == "stairs_up_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in stairs_down_mode
        if cmd == 'l' and gs.prompt_cntl == "stairs_down_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in altar mode
        if cmd == 'l' and gs.prompt_cntl == "altar_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in library mode
        if cmd == 'l' and gs.prompt_cntl == "library_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in dungeon mode
        if cmd == 'l' and gs.prompt_cntl == "dungeon_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in tomb mode
        if cmd == 'l' and gs.prompt_cntl == "tomb_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in garden mode
        if cmd == 'l' and gs.prompt_cntl == "garden_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in oracle mode
        if cmd == 'l' and gs.prompt_cntl == "oracle_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        # Allow lantern use in puzzle mode
        if cmd == 'l' and gs.prompt_cntl == "puzzle_mode":
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            self.render()
            return

        if gs.prompt_cntl == "flare_direction_mode":
            if cmd in ['n', 's', 'e', 'w']:
                if gs.active_flare_item:
                    target_x, target_y = gs.player_character.x, gs.player_character.y
                    if cmd == 'n':
                        target_y -= 1
                    elif cmd == 's':
                        target_y += 1
                    elif cmd == 'w':
                        target_x -= 1
                    elif cmd == 'e':
                        target_x += 1

                    current_floor = gs.my_tower.floors[gs.player_character.z]
                    if 0 <= target_x < current_floor.cols and 0 <= target_y < current_floor.rows and \
                       current_floor.grid[target_y][target_x].room_type != current_floor.wall_char:
                        target_room = current_floor.grid[target_y][target_x]
                        if not target_room.discovered:
                            target_room.discovered = True
                            add_log(f"The flare reveals the room at ({target_x}, {target_y}) on Floor {gs.player_character.z + 1}.")
                            discover_txt = room_discover_descriptions[target_room.room_type]
                            add_log(f"Your flare briefly illuminates the next room. {discover_txt}.")
                        else:
                            add_log("That room was already discovered.")
                    else:
                        add_log("Cannot shine the flare into a wall! Choose another direction or 'c' to cancel). ")

                    if gs.active_flare_item.count < 1:
                        gs.player_character.inventory.remove_item(gs.active_flare_item.name)
                        gs.active_flare_item = None
                        add_log("You are out of flares.")
                    else:
                        add_log(f"Flares remaining: {gs.active_flare_item.count}")

                gs.prompt_cntl = "game_loop"
            elif cmd == 'c':
                add_log("Flare not shined in any specific direction, just lit and admired.")
                if gs.active_flare_item and gs.active_flare_item.count < 1:
                    gs.player_character.inventory.remove_item(gs.active_flare_item.name)
                gs.active_flare_item = None
                gs.prompt_cntl = "game_loop"
            else:
                add_log("Invalid direction. Please enter n, s, e, w, or c to cancel.")
            self.render()
            return

        if gs.prompt_cntl == "upgrade_scroll_mode":
            process_upgrade_scroll_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "identify_scroll_mode":
            process_identify_scroll_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "game_loaded_summary":
            # Player pressed Send to start their loaded game
            if gs._pending_load:
                gs.player_character = gs._pending_load[0]
                gs.my_tower = gs._pending_load[1]
                gs._pending_load = None
                gs.prompt_cntl = "game_loop"
                add_log(f"{COLOR_GREEN}Welcome back, {gs.player_character.name}!{COLOR_RESET}")
                _trigger_room_interaction(gs.player_character, gs.my_tower)
            else:
                add_log(f"{COLOR_RED}No pending load data found!{COLOR_RESET}")
                gs.prompt_cntl = "inventory"
                handle_inventory_menu(gs.player_character, gs.my_tower, "init")
        elif gs.prompt_cntl == "starting_shop":
            handle_starting_shop(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "sell_quantity_mode":
            process_sell_quantity(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "vendor_shop":
            handle_vendor_shop(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "inventory":
            handle_inventory_menu(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "character_stats_mode":
            if cmd == 'x':
                gs.prompt_cntl = "inventory"
                handle_inventory_menu(gs.player_character, gs.my_tower, "init")
            # Invalid commands are silently ignored - prompt is in placeholder
        elif gs.prompt_cntl == "chest_mode":
            process_chest_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "spell_casting_mode": # New condition for spell casting
            process_spell_casting_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "combat_victory":
            # Any input dismisses victory screen early and transitions to room
            gs.victory_monster_name = None
            _trigger_room_interaction(gs.player_character, gs.my_tower)
        elif gs.prompt_cntl == "combat_mode": # This block needs to be after spell_casting_mode for 'c' to work
            process_combat_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "spell_memorization_mode":
            process_spell_memorization_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "crafting_mode":
            process_crafting_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "stairs_up_mode":
            process_stairs_up_action(gs.player_character, gs.my_tower, cmd, gs.floor_params)
        elif gs.prompt_cntl == "stairs_down_mode":
            process_stairs_down_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "journal_mode":  # ADD THIS
            process_journal_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl.startswith("journal_"):  # ADD THIS
            category = gs.prompt_cntl.replace("journal_", "")
            process_journal_category(gs.player_character, gs.my_tower, category, cmd)
        elif gs.prompt_cntl == "library_mode":
            process_library_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "library_book_selection_mode":  # ADD THIS
            process_library_book_selection(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "library_read_decision_mode":  # ADD THIS
            process_library_read_decision(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "blacksmith_mode":
            process_blacksmith_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "shrine_mode":
            process_shrine_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "alchemist_mode":
            process_alchemist_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "war_room_mode":
            process_war_room_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "taxidermist_mode":
            process_taxidermist_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "flee_direction_mode":
            process_flee_direction_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "foresight_direction_mode":  # ADD THIS BLOCK
            process_foresight_direction_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "vault_warp_mode":
            process_vault_warp_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "upgrade_scroll_mode":
            process_upgrade_scroll_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "achievements_mode":
            if cmd == 'x':
                gs.prompt_cntl = "inventory"
                handle_inventory_menu(gs.player_character, gs.my_tower, "init")
            # Invalid commands are silently ignored - prompt is in placeholder
        elif gs.prompt_cntl == "puzzle_mode":
            process_puzzle_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "zotle_teleporter_mode":
            process_zotle_teleporter_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "save_load_mode":
            process_save_load_action(gs.player_character, gs.my_tower, cmd)
        elif gs.prompt_cntl == "load_pending":
            if gs._pending_load:
                gs.player_character = gs._pending_load[0]
                gs.my_tower = gs._pending_load[1]
                gs._pending_load = None
            gs.prompt_cntl = "game_loop"
            _trigger_room_interaction(gs.player_character, gs.my_tower)
        elif gs.prompt_cntl == "main_menu":
            process_main_menu_action(cmd)
        elif gs.prompt_cntl == "player_name":
            create_player_character(gs.my_tower, gs.player_character, gs.prompt_cntl, cmd)
        elif gs.prompt_cntl == "player_race":
            create_player_character(gs.my_tower, gs.player_character, gs.prompt_cntl, cmd)
        elif gs.prompt_cntl == "player_gender":
            create_player_character(gs.my_tower, gs.player_character, gs.prompt_cntl, cmd)
        elif _handle(gs.my_tower, gs.player_character, cmd):
            pass
        else: # This 'else' block means gs.prompt_cntl is "game_loop" or similar map-based interaction.
            if cmd in ['n', 's', 'e', 'w']:
                 moved = move_player(gs.player_character, gs.my_tower, cmd)
                 if not moved:
                     gs.prompt_cntl = "game_loop" # If movement failed, explicitly revert to game_loop.

    def _schedule_initiative_strike(self):
        """Auto-fire monster's initiative attack after init dice animation plays."""
        import threading
        def _auto_strike():
            if gs.prompt_cntl == "combat_mode" and gs.monster_initiative_pending:
                self.process_command('_init_strike')
                self.render()
        # 1.8s: init dice tumble (0-360ms) + reveal (760ms) + hold (800ms)
        threading.Timer(1.8, lambda: self.app.loop.call_soon_threadsafe(_auto_strike)).start()

    def _schedule_victory_dismiss(self):
        """Auto-dismiss combat victory screen after animations finish."""
        import threading
        def _auto_dismiss():
            if gs.prompt_cntl == "combat_victory":
                gs.victory_monster_name = None
                _trigger_room_interaction(gs.player_character, gs.my_tower)
                self.render()
        # 4.5s total: opposed ATK exchange (0-1.0s) + damage (1.3-1.9s) +
        # grayscale (2.1-2.7s) + DEFEATED flash (2.7-4.5s)
        threading.Timer(4.5, lambda: self.app.loop.call_soon_threadsafe(_auto_dismiss)).start()

    def render(self):
        """Render the game state to the display.

        First call: full set_content (loads the shell, audio engine, and
        initial content). Subsequent calls: incremental DOM update via
        evaluate_javascript('updateGame(...)') so the AudioContext and
        all persistent JS state survive across renders.
        """
        self.set_input_visibility()
        if not getattr(self, '_first_render_done', False):
            self._render_initial()
        else:
            self._render_update()

    def _render_initial(self):
        """First render: full set_content with shell + initial content."""
        html_content = self.generate_html()
        full_html = self.wrap_html(html_content, gs.log_lines)
        import sys
        if sys.platform == 'android':
            self.web_view._impl.native.loadDataWithBaseURL(
                None, full_html, "text/html", "utf-8", None
            )
        else:
            self.web_view.set_content("", full_html)
        self._first_render_done = True

    def _render_update(self):
        """Subsequent renders: incremental update via evaluate_javascript.

        Builds a JSON payload (content HTML, log lines, animation/SFX
        scripts, music mood) and hands it to window.updateGame() in the
        already-loaded shell. The audio engine and other persistent state
        are untouched.
        """
        import json as _json
        html_content = self.generate_html()

        # Compute music state
        new_mood = get_audio_mood(gs.prompt_cntl)
        mood_changed = (new_mood != gs.current_music_mood)
        has_init = bool(gs.last_dice_rolls and
                        any(r[3] == 'INIT' for r in gs.last_dice_rolls))
        init_offset = 1000 if has_init else 0
        music_delay_ms = 0
        if mood_changed and gs.last_dice_rolls:
            if new_mood == 'victory':
                music_delay_ms = 1800 + init_offset
            elif new_mood == 'death':
                music_delay_ms = 3500 + init_offset
        if mood_changed or gs.music_restart:
            gs.current_music_mood = new_mood
            gs.music_restart = False

        # Extract animation / SFX script bodies (raw JS, no <script> wrapper)
        anim_scripts = []
        for raw in (
            generate_spell_cast_js(gs.last_spell_cast),
            generate_spell_particles_js(gs.last_spell_cast),
            generate_dice_roll_js(gs.last_dice_rolls),
            generate_concentration_check_js(gs.last_concentration_roll),
            generate_monster_defeat_js(gs.monster_defeated_anim),
            generate_sfx_js(
                gs.last_monster_damage, gs.last_player_damage,
                gs.last_player_blocked, gs.last_player_heal,
                gs.last_monster_damage_badge, gs.last_player_damage_badge,
                gs.last_player_status, gs.last_monster_status,
                gs.last_spell_cast, gs.last_concentration_roll,
                gs.monster_defeated_anim, gs.sfx_event,
                gs.music_enabled, bool(gs.last_dice_rolls), has_init,
            ),
        ):
            body = _extract_script_body(raw)
            if body:
                anim_scripts.append(body)

        payload = {
            'contentHtml': html_content,
            'logLines': list(gs.log_lines),
            'hasDiceRolls': bool(gs.last_dice_rolls),
            'hasInitRoll': has_init,
            'scripts': anim_scripts,
            'mood': new_mood if mood_changed else None,
            'musicEnabled': bool(gs.music_enabled),
            'musicDelayMs': music_delay_ms,
        }

        # Fire-and-forget JS evaluation. We deliberately do NOT fall back
        # to _render_initial() on failure — that would reload the page
        # and destroy the AudioContext, which is exactly what this whole
        # refactor exists to prevent.
        # On Android, use the native WebView's evaluateJavascript() directly
        # (bypassing Toga's awaitable wrapper which can be flaky in
        # fire-and-forget mode).  On other platforms, use Toga's API.
        import sys
        js = 'if(window.updateGame){updateGame(' + _json.dumps(payload) + ');}'
        try:
            if sys.platform == 'android':
                self.web_view._impl.native.evaluateJavascript(js, None)
            else:
                self.web_view.evaluate_javascript(js)
        except Exception:
            # Quiet-skip — the next render will catch up.  Music keeps playing.
            pass

        # Clear one-shot flags (mirrors what wrap_html does on first render)
        gs.monster_defeated_anim = None
        gs.last_dice_rolls = []
        gs.last_spell_cast = None
        gs.last_concentration_roll = None
        gs.sfx_event = None
        # Clear combat SFX flags so they don't re-fire on the next render
        gs.last_monster_damage = 0
        gs.last_player_damage = 0
        gs.last_player_blocked = False
        gs.last_player_heal = 0
        gs.last_monster_damage_badge = None
        gs.last_player_damage_badge = None
        gs.last_player_status = None
        gs.last_monster_status = None
    
    def generate_html(self):
        """
        Generate HTML content for the game display.

        This should be your existing render() function logic from cavern12.
        Copy all the HTML generation code here.
        """

        # Pre-round HP: in combat views, show health bars at their pre-damage values
        # so the bar doesn't drop until the damage animation plays.
        # Falls back to current HP if no snapshot exists (non-combat views).
        _combat_views = ('combat_mode', 'spell_casting_mode', 'combat_victory')
        if gs.prompt_cntl in _combat_views and getattr(gs, 'pre_round_monster_hp', None) is not None:
            _m_display_hp = gs.pre_round_monster_hp
        else:
            _m_display_hp = gs.active_monster.health if gs.active_monster else 0
        if gs.prompt_cntl in _combat_views and getattr(gs, 'pre_round_player_hp', None) is not None:
            _p_display_hp = gs.pre_round_player_hp
        else:
            _p_display_hp = gs.player_character.health if gs.player_character else 0

        # Low-HP pulse uses display HP (not current) so it doesn't spoil the animation
        low_hp_pulse_style = ""
        try:
            hp_for_pulse = _p_display_hp if gs.prompt_cntl in _combat_views else (gs.player_character.health if gs.player_character else 100)
            if gs.player_character and hp_for_pulse < (gs.player_character.max_health // 4):
                low_hp_pulse_style = " animation: lowHPPulse 1s ease-in-out infinite;"
        except Exception:
            pass

        # Spell element for coloring damage floats and triggering spell animations.
        _spell = getattr(gs, 'last_spell_cast', None)
        _spell_element = _spell_visual_element(_spell) if _spell else None
        _spell_level = getattr(_spell, 'level', 0) if _spell else 0

        # CREATE ACHIEVEMENT NOTIFICATION HTML - MINIMAL VERSION
        achievement_notifications = ""
        if gs.newly_unlocked_achievements:
            # Just show the most recent achievement in a single line
            ach = gs.newly_unlocked_achievements[-1]
            gold_text = f' (+{ach.reward_gold}g)' if ach.reward_gold > 0 else ''
            achievement_notifications = f"""
                  <div style="background: rgba(255, 215, 0, 0.1);
                            color: #FFD700;
                            padding: 6px 10px;
                            margin-bottom: 8px;
                            border-radius: 3px;
                            border-left: 2px solid #FFD700;
                            font-size: 12px;">
                     Achievement Unlocked: <b>{ach.name}</b>{gold_text}
                  </div>
                  """

            # Show up to 3 most recent achievements
        for ach in gs.newly_unlocked_achievements[-3:]:
            achievement_notifications += f"""
                    <div style="margin: 5px 0; padding: 4px; border-radius: 4px;">
                         <span style="font-size: 16px;">{ach.name}</span> - {ach.description}
                        {f'<span style="color: #006400; margin-left: 10px;">(+{ach.reward_gold} gold)</span>' if ach.reward_gold > 0 else ''}
                    </div>
                    """

        achievement_notifications += "</div>"

        html_code = ""
        current_commands_text = ""

        # SPLASH SCREEN - Show version and recent changes for 5 seconds
        if gs.prompt_cntl == "splash":
            changelog_html = ""
            for entry in CHANGELOG[:8]:
                # Escape HTML in commit messages
                safe_entry = entry.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                changelog_html += f'<div style="color: #AAA; font-size: 11px; margin: 3px 0; padding-left: 10px; border-left: 2px solid #444;">{safe_entry}</div>'

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; padding: 20px; text-align: center;
                            display: flex; flex-direction: column; justify-content: center; min-height: 60vh;">
                    <div style="font-size: 24px; font-weight: bold; margin-bottom: 8px; color: #FFD700;">
                        WIZARD'S CAVERN
                    </div>
                    <div style="font-size: 14px; color: #4FC3F7; margin-bottom: 30px;">
                        v{VERSION} (build {BUILD_NUMBER})
                    </div>
                    <div style="text-align: left; max-width: 340px; margin: 0 auto;">
                        <div style="color: #888; font-size: 11px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;">
                            Recent Changes
                        </div>
                        {changelog_html}
                    </div>
                </div>
            """
            current_commands_text = ""
            self.update_button_panel(current_commands_text, False)
            return html_code

        # DEATH SCREEN - Show gravestone and final stats
        if gs.prompt_cntl == "death_screen":
            # Calculate final stats
            floors_explored = gs.player_character.z + 1
            final_level = gs.player_character.level
            final_gold = gs.player_character.gold
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; text-align: center; padding: 20px;">
                    <div style="font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #FF4444;">
                         GAME OVER 
                    </div>
                    
                    <div style="font-size: 18px; margin: 30px auto; max-width: 300px; color: #888;">
                        <pre style="color: #666; line-height: 1.2;">
    ___________
   /           \\
  /    R.I.P.   \\
 |    In Peace   |
 | {gs.player_character.name:^13}|
 |               |
 | Fell on Lv {floors_explored}|
 |               |
  
                        </pre>
                    </div>
                    
                    <div style="margin: 30px auto; max-width: 350px; text-align: left; font-size: 12px; color: #CCC;">
                        <div style="margin: 8px 0;"><b>Final Level:</b> {final_level}</div>
                        <div style="margin: 8px 0;"><b>Deepest Floor:</b> {floors_explored}</div>
                        <div style="margin: 8px 0;"><b>Gold Collected:</b> {final_gold}</div>
                        <div style="margin: 8px 0;"><b>Monsters Slain:</b> {gs.game_stats.get('monsters_killed', 0)}</div>
                        <div style="margin: 8px 0;"><b>Spells Cast:</b> {gs.game_stats.get('spells_cast', 0)}</div>
                    </div>
                    
                    <div style="margin-top: 40px; color: #888; font-size: 12px;">
                        Press Send to close...
                    </div>
                </div>
                """
            current_commands_text = "Press Send to close"
            self.update_button_panel(current_commands_text, False)
            return html_code

        # Player stats - hide HP/MP during character creation and starting shop
        show_bars = gs.prompt_cntl not in ['splash', 'intro_story', 'player_name', 'player_race', 'player_gender', 'starting_shop']

        # Get dynamic title
        player_title = get_player_title(gs.player_character) if show_bars else ""

        # Ultra-compact stats for mobile - optimized for 393px width
        # Include x, y coordinates and player level
        if show_bars:
            hunger_color = get_hunger_color(gs.player_character.hunger)
            player_stats_html = f"""
                <div style="font-family: monospace; font-size: 12px; margin-bottom: 4px; padding: 3px; background: #1a1a1a; border-radius: 2px;">
                    <b>{gs.player_character.name}</b> Lv{gs.player_character.level} | F{gs.player_character.z + 1} ({gs.player_character.x},{gs.player_character.y}) | {gs.player_character.gold}g | {gs.player_character.experience}xp<br>
                    HP:<span class="player-hp-bar">{health_bar(_p_display_hp, gs.player_character.max_health, width=10)}</span> MP:{mana_bar(gs.player_character.mana, gs.player_character.max_mana, width=10)} | <span style="color:{hunger_color};">H:{gs.player_character.hunger}</span>
                </div>
            """
        else:
            player_stats_html = f"""
                <div style="font-family: monospace; font-size: 12px; margin-bottom: 4px; padding: 3px; background: #1a1a1a; border-radius: 2px;">
                    <b>{gs.player_character.name}</b>
                </div>
            """

        if gs.prompt_cntl == "intro_story" or gs.prompt_cntl == "main_menu":
            # MAIN MENU / INTRO STORY SCREEN
            saves = SaveSystem.list_saves()
            has_saves = any(not s['empty'] for s in saves)

            # Build save slots HTML
            save_slots_html = ""
            if has_saves:
                save_slots_html = """
                            <div style="border-top: 1px solid #444; padding-top: 15px; margin-top: 10px;">
                                <div style="color: #888; font-size: 12px; margin-bottom: 10px;">- OR CONTINUE -</div>
                        """
                for save in saves:
                    slot = save['slot']
                    if not save['empty']:
                        info = save['info']
                        save_slots_html += f"""
                                    <div style="padding: 8px; margin: 5px 0; border: 1px solid #4FC3F7; border-radius: 4px; background: #222; text-align: left;">
                                        <div style="color: #4FC3F7; font-size: 12px;">
                                            Press '{slot}' to load: <span style="color: #FFF;">{info['name']}</span>
                                        </div>
                                        <div style="color: #888; font-size: 12px;">
                                            Level {info['level']} | Floor {info['floor']} | {info['gold']} Gold
                                        </div>
                                    </div>
                                """
                save_slots_html += "</div>"

            html_code = f"""
                        <div id="intro-tap-zone" style="font-family: monospace; font-size: 12px; padding: 10px; text-align: center; cursor: pointer;"
                             onclick="(function(){{ if(window._musicEngine){{ window._musicEngine.resume(); var s=document.getElementById('music-status'); if(s){{ s.innerHTML='&#9835; MUSIC ON &mdash; press SEND to begin'; s.style.color='#69F0AE'; }} }} }})()"
                             ontouchstart="(function(){{ if(window._musicEngine){{ window._musicEngine.resume(); var s=document.getElementById('music-status'); if(s){{ s.innerHTML='&#9835; MUSIC ON &mdash; press SEND to begin'; s.style.color='#69F0AE'; }} }} }})()">
                            <div style="font-size: 22px; font-weight: bold; margin-bottom: 12px; color: #FFD700;">
                                 WIZARD'S CAVERN
                            </div>
                            <div id="music-status" style="font-size: 11px; color: #FFB74D; margin-bottom: 18px; letter-spacing: 1px;">
                                &#9835; TAP THIS PANEL TO ENABLE MUSIC
                            </div>
                            <div style="font-size: 12px; line-height: 1.6; margin-bottom: 30px; color: #CCCCCC; text-align: left; max-width: 400px; margin-left: auto; margin-right: auto;">
                                Many cycles ago, in the kingdom of Medium Earth, the gnomic wizard Zot forged his great ORB OF POWER.
                                <br><br>
                                He soon vanished, leaving behind his vast subterranean cavern filled with esurient monsters, fabulous treasures, and the incredible ORB OF ZOT.
                                <br><br>
                                From that time hence, many a bold venturer has ventured into the wizard's cavern. As of now, NONE has ever emerged victoriously!
                                <br><br>
                                <span style="color: #FF4444;">Beware!!</span>
                            </div>

                            <div style="border: 2px solid #555; border-radius: 5px; padding: 15px; margin: 20px auto; max-width: 350px; background: #1a1a1a;">
                                <div style="color: #4FC3F7; font-size: 12px; margin-bottom: 15px;">
                                    Press Send to start a <span style="color: #4FC3F7;">NEW GAME</span>
                                </div>
                                {save_slots_html}
                            </div>
                        </div>
                    """
            if has_saves:
                current_commands_text = "Send = New Game | 1-3 = Load"
            else:
                current_commands_text = "Send to begin"

        elif gs.prompt_cntl == "game_loaded_summary":
            # LOADED GAME SUMMARY SCREEN
            loaded_char = gs._pending_load[0] if gs._pending_load else gs.player_character
            loaded_tower = gs._pending_load[1] if gs._pending_load else gs.my_tower

            # Count unlocked achievements
            unlocked_count = sum(1 for a in ACHIEVEMENTS if a.unlocked)
            total_achievements = len(ACHIEVEMENTS)

            # Count runes and shards
            runes_count = sum(1 for v in gs.runes_obtained.values() if v)
            shards_count = sum(1 for v in gs.shards_obtained.values() if v)

            # Build equipment display
            weapon_name = loaded_char.equipped_weapon.name if loaded_char.equipped_weapon else "None"
            armor_name = loaded_char.equipped_armor.name if loaded_char.equipped_armor else "None"

            # Build stats display
            stats_html = f"""
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin: 10px 0;">
                            <div style="color: #F44336;">STR: {loaded_char.strength}</div>
                            <div style="color: #2196F3;">INT: {loaded_char.intelligence}</div>
                            <div style="color: #4CAF50;">DEX: {loaded_char.dexterity}</div>
                            <div style="color: #FF9800;">ATK: {loaded_char.attack}</div>
                            <div style="color: #E040FB;">DEF: {loaded_char.defense}</div>
                            <div style="color: #FFD700;">Gold: {loaded_char.gold}</div>
                        </div>
                    """

            # Build progress display
            progress_html = f"""
                        <div style="margin: 10px 0; padding: 8px; background: #1a1a1a; border-radius: 4px;">
                            <div style="color: #888; font-size: 12px; margin-bottom: 5px;">PROGRESS</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 3px; font-size: 12px;">
                                <div>Monsters Slain: <span style="color: #F44336;">{gs.game_stats.get('monsters_killed', 0)}</span></div>
                                <div>Chests Opened: <span style="color: #FFD700;">{gs.game_stats.get('chests_opened', 0)}</span></div>
                                <div>Spells Learned: <span style="color: #E040FB;">{gs.game_stats.get('spells_learned', 0)}</span></div>
                                <div>Gold Collected: <span style="color: #FFD700;">{gs.game_stats.get('total_gold_collected', 0)}</span></div>
                            </div>
                        </div>
                    """

            # Quest progress
            quest_html = ""
            if runes_count > 0 or shards_count > 0:
                quest_html = f"""
                        <div style="margin: 10px 0; padding: 8px; background: #1a1a1a; border-radius: 4px;">
                            <div style="color: #888; font-size: 12px; margin-bottom: 5px;">QUEST ITEMS</div>
                            <div style="font-size: 12px;">
                                <div>Runes: <span style="color: #4FC3F7;">{runes_count}/8</span></div>
                                <div>Shards: <span style="color: #BA68C8;">{shards_count}/8</span></div>
                            </div>
                        </div>
                        """

            html_code = f"""
                        <div style="font-family: monospace; font-size: 12px; padding: 15px; text-align: center;">
                            <div style="font-size: 18px; font-weight: bold; color: #4CAF50; margin-bottom: 5px;">
                                GAME LOADED
                            </div>
                            <div style="font-size: 12px; color: #666; margin-bottom: 15px;">
                                Welcome back, adventurer!
                            </div>

                            <div style="border: 2px solid #4FC3F7; border-radius: 8px; padding: 15px; background: #111; text-align: left;">
                                <!-- Character Header -->
                                <div style="text-align: center; margin-bottom: 10px;">
                                    {generate_player_sprite_html(getattr(loaded_char, 'race', 'human'), getattr(loaded_char, 'gender', 'male'), getattr(loaded_char, 'equipped_armor', None))}
                                    <div style="font-size: 20px; font-weight: bold; color: #FFD700;">
                                        {loaded_char.name}
                                    </div>
                                    <div style="font-size: 12px; color: #888;">
                                        Level {loaded_char.level} {loaded_char.race.capitalize()} {loaded_char.character_class}
                                    </div>
                                </div>

                                <!-- Health/Mana Bars -->
                                <div style="margin: 10px 0;">
                                    <div style="font-size: 12px; margin-bottom: 3px;">
                                        HP: <span style="color: #4CAF50;">{loaded_char.health}/{loaded_char.max_health}</span>
                                    </div>
                                    <div style="background: #333; border-radius: 3px; height: 8px; overflow: hidden;">
                                        <div style="background: linear-gradient(90deg, #4CAF50, #8BC34A); height: 100%; width: {int(loaded_char.health / loaded_char.max_health * 100)}%;"></div>
                                    </div>
                                </div>
                                <div style="margin: 10px 0;">
                                    <div style="font-size: 12px; margin-bottom: 3px;">
                                        MP: <span style="color: #2196F3;">{loaded_char.mana}/{loaded_char.max_mana}</span>
                                    </div>
                                    <div style="background: #333; border-radius: 3px; height: 8px; overflow: hidden;">
                                        <div style="background: linear-gradient(90deg, #2196F3, #03A9F4); height: 100%; width: {int(loaded_char.mana / max(1, loaded_char.max_mana) * 100)}%;"></div>
                                    </div>
                                </div>

                                <!-- Location -->
                                <div style="text-align: center; margin: 10px 0; padding: 8px; background: #222; border-radius: 4px;">
                                    <div style="color: #FF9800; font-size: 12px;">
                                        Floor {loaded_char.z + 1}
                                    </div>
                                    <div style="color: #666; font-size: 12px;">
                                        Position: ({loaded_char.x}, {loaded_char.y})
                                    </div>
                                </div>

                                <!-- Stats Grid -->
                                {stats_html}

                                <!-- Equipment -->
                                <div style="margin: 10px 0; padding: 8px; background: #1a1a1a; border-radius: 4px;">
                                    <div style="color: #888; font-size: 12px; margin-bottom: 5px;">EQUIPMENT</div>
                                    <div style="font-size: 12px;">
                                        <div>Weapon: <span style="color: #FF5722;">{weapon_name}</span></div>
                                        <div>Armor: <span style="color: #607D8B;">{armor_name}</span></div>
                                    </div>
                                </div>

                                <!-- Progress -->
                                {progress_html}

                                <!-- Quest Items -->
                                {quest_html}

                                <!-- Achievements -->
                                <div style="text-align: center; margin-top: 10px; padding: 8px; background: #1a1a1a; border-radius: 4px;">
                                    <div style="color: #FFD700; font-size: 12px;">
                                        Achievements: {unlocked_count}/{total_achievements}
                                    </div>
                                </div>
                            </div>

                            <div style="margin-top: 20px; color: #4FC3F7; font-size: 12px;">
                                Press Send to continue your adventure!
                            </div>
                        </div>
                    """
            current_commands_text = "Press Send to continue"
        elif gs.prompt_cntl == "save_load_mode":
            # SAVE/LOAD MENU
            saves = SaveSystem.list_saves()

            slots_html = ""
            for save in saves:
                slot = save['slot']
                if save['empty']:
                    slots_html += f"""
                                <div style="padding: 12px; margin: 8px 0; border: 1px solid #333; border-radius: 4px; background: #222;">
                                    <div style="color: #888; font-size: 12px;">
                                        <span style="color: #666;">Slot {slot}:</span> Empty
                                    </div>
                                    <div style="color: #4FC3F7; font-size: 12px; margin-top: 5px;">
                                        Press '{slot}' to SAVE here
                                    </div>
                                </div>
                            """
                else:
                    info = save['info']
                    timestamp = info['timestamp'][:10] if info['timestamp'] != 'Unknown' else 'Unknown'
                    slots_html += f"""
                                <div style="padding: 12px; margin: 8px 0; border: 1px solid #4FC3F7; border-radius: 4px; background: #222;">
                                    <div style="color: #4FC3F7; font-size: 12px; font-weight: bold;">
                                        Slot {slot}: {info['name']}
                                    </div>
                                    <div style="color: #AAA; font-size: 12px; margin-top: 5px;">
                                        Level {info['level']} | Floor {info['floor']} | {info['gold']} Gold
                                    </div>
                                    <div style="color: #666; font-size: 12px; margin-top: 3px;">
                                        Saved: {timestamp}
                                    </div>
                                    <div style="color: #888; font-size: 12px; margin-top: 8px; border-top: 1px solid #333; padding-top: 8px;">
                                        Press '{slot}' to <span style="color: #4FC3F7;">LOAD</span> | 
                                        Press 'o{slot}' to <span style="color: #FFA500;">OVERWRITE</span>
                                    </div>
                                </div>
                            """

            html_code = f"""
                        <div style="font-family: monospace; font-size: 12px; padding: 15px;">
                            {achievement_notifications}
                            <h2 style="color: #FFD700; text-align: center; margin-bottom: 15px;">
                                SAVE / LOAD GAME
                            </h2>
                            <div style="border: 2px solid #555; border-radius: 5px; padding: 15px; background: #1a1a1a;">
                                {slots_html}
                            </div>
                            <div style="text-align: center; margin-top: 15px; color: #888; font-size: 12px;">
                                Press 'x' to cancel
                            </div>
                        </div>
                    """
            current_commands_text = "1-3 = save/load | o1-o3 = overwrite | x = cancel"

        elif gs.prompt_cntl == "player_name":
            # PLAYER NAME INPUT SCREEN
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; padding: 10px;">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #FFD700; text-align: center;">
                        CHARACTER CREATION
                    </div>
                    <div style="font-size: 12px; margin-bottom: 10px; color: #FFFFFF;">
                        What is your hero's name?
                    </div>
                    <div style="font-size: 12px; color: #888888; margin-top: 20px;">
                        Use the letter buttons below to type your name, then press SEND...
                    </div>
                </div>
                """
            current_commands_text = "Use letter buttons below"

        elif gs.prompt_cntl == "player_race":
            # PLAYER RACE SELECTION SCREEN
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; padding: 10px;">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #FFD700; text-align: center;">
                        CHARACTER CREATION
                    </div>
                    <div style="font-size: 12px; margin-bottom: 15px; color: #FFFFFF;">
                        <b>{gs.player_character.name}</b>. Really? Oooohkay.
                    </div>
                    <div style="font-size: 12px; margin-bottom: 10px; color: #FFFFFF;">
                        Choose your race:
                    </div>
                    <div style="margin-left: 20px; font-size: 12px; line-height: 1.8;">
                        <div><b>H</b> - Human (Balanced stats)</div>
                        <div><b>E</b> - Elf (+Dex, +Int, -Str, -Health)</div>
                        <div><b>D</b> - Dwarf (+Str, +Def, +Health, -Dex, -Int)</div>
                    </div>
                </div>
                """
            current_commands_text = "H = Human | E = Elf | D = Dwarf"

        elif gs.prompt_cntl == "player_gender":
            # PLAYER GENDER SELECTION SCREEN
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; padding: 10px;">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #FFD700; text-align: center;">
                        CHARACTER CREATION
                    </div>
                    <div style="font-size: 12px; margin-bottom: 15px; color: #FFFFFF;">
                        You went with <b>{gs.player_character.race.title()}</b>
                    </div>
                    <div style="font-size: 12px; margin-bottom: 10px; color: #FFFFFF;">
                        Choose your gender:
                    </div>
                    <div style="margin-left: 20px; font-size: 12px; line-height: 1.8;">
                        <div><b>M</b> - Male</div>
                        <div><b>F</b> - Female</div>
                        <div><b>N</b> - Non-binary</div>
                    </div>
                </div>
                """
            current_commands_text = "M = Male | F = Female | N = Non-binary"

        elif gs.prompt_cntl == "achievements_mode":
            # ACHIEVEMENTS VIEW

            # Calculate statistics
            total_achievements = len(ACHIEVEMENTS)
            unlocked_count = sum(1 for a in ACHIEVEMENTS if a.unlocked)
            completion_percent = int((unlocked_count / total_achievements) * 100) if total_achievements > 0 else 0

            # Group achievements by category
            categories = {}
            for achievement in ACHIEVEMENTS:
                if achievement.category not in categories:
                    categories[achievement.category] = []
                categories[achievement.category].append(achievement)

            # Category display names and colors
            category_info = {
                'combat': (' Combat', '#FF6F00'),
                'exploration': (' Exploration', '#2196F3'),
                'magic': (' Magic', '#E040FB'),
                'survival': (' Survival', '#4CAF50'),
                'collection': (' Collection', '#FF9800'),
                'development': (' Development', '#00BCD4'),
            }

            achievements_html = f"""
                    <h3>Achievements ({unlocked_count}/{total_achievements})</h3>
                    <div style="padding: 3px; border-radius: 3px; margin-bottom: 5px;">
                        <div style="width: {completion_percent}%; height: 20px; border-radius: 2px; text-align: center; line-height: 20px; color: #000; font-weight: bold;">
                            {completion_percent}%
                        </div>
                    </div>
                    """

            # Display achievements by category
            for cat_id in ['combat', 'exploration', 'magic', 'survival', 'collection', 'development']:
                if cat_id in categories:
                    cat_name, cat_color = category_info[cat_id]
                    cat_achievements = categories[cat_id]
                    cat_unlocked = sum(1 for a in cat_achievements if a.unlocked)

                    achievements_html += f"""
                        <div style="margin-bottom: 15px; border: 1px solid {cat_color}; padding: 3px; border-radius: 3px;">
                            <h4 style="color: {cat_color}; margin: 5px 0;">{cat_name} ({cat_unlocked}/{len(cat_achievements)})</h4>
                        """

                    for achievement in cat_achievements:
                        if achievement.unlocked:
                            unlock_icon = ""
                            text_color = "#FFD700"
                            opacity = "1.0"
                        else:
                            unlock_icon = ""
                            text_color = "#666"
                            opacity = "0.6"

                        achievements_html += f"""
                            <div style="opacity: {opacity}; padding: 3px; margin: 3px 0; border-radius: 2px;">
                                <div style="color: {text_color};">{unlock_icon} <b>{achievement.name}</b></div>
                                <div style="font-size: 12px; color: #AAA; margin-left: 20px;">{achievement.description}</div>
                                {f'<div style="font-size: 12px; color: #4CAF50; margin-left: 20px;">Reward: {achievement.reward_gold} gold</div>' if achievement.reward_gold > 0 else ''}
                            </div>
                            """

                    achievements_html += "</div>"

            # Stats summary
            stats_html = f"""
                    <h3>Your Statistics</h3>
                    <div style="background-color: #222; padding: 10px; border-radius: 3px; font-size: 12px;">
                        <b>Combat:</b><br>
                         Monsters Killed: {gs.game_stats.get('monsters_killed', 0)}<br>
                         Flawless Kills: {gs.game_stats.get('full_health_kills', 0)}<br>
                         Defeated Higher Level: {gs.game_stats.get('defeated_higher_level', 0)}<br>
                        <br>
                        <b>Magic:</b><br>
                         Spells Learned: {gs.game_stats.get('spells_learned', 0)}<br>
                         Spells Cast: {gs.game_stats.get('spells_cast', 0)}<br>
                         Grimoires Read: {gs.game_stats.get('grimoires_read', 0)}<br>
                         Spell Backfires: {gs.game_stats.get('spell_backfires', 0)}<br>
                        <br>
                        <b>Exploration:</b><br>
                         Max Floor: {gs.game_stats.get('max_floor_reached', 0)}<br>
                         Chests Opened: {gs.game_stats.get('chests_opened', 0)}<br>
                         Vendors Visited: {gs.game_stats.get('vendors_visited', 0)}<br>
                         Altars Used: {gs.game_stats.get('altars_used', 0)}/7<br>
                        <br>
                        <b>Wealth:</b><br>
                         Total Gold Collected: {gs.game_stats.get('total_gold_collected', 0)}<br>
                    </div>
                    """

            html_code = f"""
                    <div style="font-family: monospace; font-size: 12px;">
                        {achievement_notifications}
                        <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>

                        <div style="border: 1px solid gold; padding: 4px; border-radius: 4px; background: #1a1a1a; max-height: 500px; overflow-y: auto; margin-bottom: 5px;">{achievements_html}</div>
                        
                        <div style="border: 1px solid cyan; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px;">{stats_html}</div>
</div>
                    """
            current_commands_text = "x = exit"

        elif gs.prompt_cntl == "starting_shop":
            # STARTING SHOP VIEW - Match regular vendor format
            sorted_vendor_items = get_sorted_inventory(gs.active_vendor.inventory)
            vendor_html = "<h3 style='margin: 0 0 5px 0;'>Vendor Wares</h3>"
            vendor_html += "<div style='overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px; max-height: 200px;'>"
            if not sorted_vendor_items:
                vendor_html += "<div style='margin: 2px 0; padding: 0;'>(Out of stock)</div>"
            else:
                for i, item in enumerate(sorted_vendor_items):
                    # Vendors know what items are - show real names (for_vendor=True)
                    item_str = format_item_for_display(item, gs.player_character, show_price=True, is_sell_price=False, for_vendor=True)
                    vendor_html += f"<div style='margin: 2px 0; padding: 0;'><b>{i + 1}.</b> {item_str}</div>"
            vendor_html += "</div>"

            sorted_player_items = get_sorted_inventory(gs.player_character.inventory)
            player_inv_html = "<h3 style='margin: 0 0 5px 0;'>Your Inventory</h3>"
            player_inv_html += "<div style='overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px; max-height: 200px;'>"
            if not sorted_player_items:
                player_inv_html += "<div style='margin: 2px 0; padding: 0;'>(Empty)</div>"
            else:
                for i, item in enumerate(sorted_player_items):
                    # Player inventory shows cryptic names for unidentified items
                    item_str = format_item_for_display(item, gs.player_character, show_price=True, is_sell_price=True)
                    player_inv_html += f"<div style='margin: 2px 0; padding: 0;'><b>{i + 1}.</b> {item_str}</div>"
            player_inv_html += "</div>"

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; display: flex; flex-direction: column; max-height: 100%; overflow: hidden;">
                    {achievement_notifications}
                    <div style="margin-bottom: 5px;">
                        <div style="font-size: 16px; font-weight: bold;">{gs.active_vendor.name}'s Shop</div>
                        <div style="color: #DAA520; font-size: 12px; margin-top: 2px;">{gs.shop_message}</div>
                    </div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; gap: 5px; flex: 1; min-height: 0; overflow: hidden;">
                        <div style="border: 1px solid grey; padding: 3px;">{vendor_html}</div>
                        <div style="border: 1px solid grey; padding: 3px;">{player_inv_html}</div>
                    </div>
                </div>
                """
            if gs.vendor_action:
                action_label = {'buy': 'buy', 'sell': 'sell'}.get(gs.vendor_action, gs.vendor_action)
                current_commands_text = f"# = {action_label} item | b = back"
            else:
                current_commands_text = "b = buy | s = sell | ba = buy all | x = exit"

        elif gs.prompt_cntl == "sell_quantity_mode":
            # SELL QUANTITY MODE - Show "How many?" prompt
            item = gs.pending_sell_item
            item_count = getattr(item, 'count', 1) if item else 1
            sell_price_each = (item.calculated_value // 2) if item else 0
            item_name = item.name if item else "item"
            
            quantity_html = f"""
                <div style="border: 2px solid #DAA520; padding: 15px; border-radius: 8px; background: #1a1a1a; text-align: center;">
                    <div style="color: #DAA520; font-weight: bold; font-size: 16px; margin-bottom: 10px;">
                        How many to sell?
                    </div>
                    <div style="color: #FFF; font-size: 12px; margin-bottom: 8px;">
                        <b>{item_name}</b>
                    </div>
                    <div style="color: #888; font-size: 12px; margin-bottom: 8px;">
                        You have: {item_count} | Price each: {sell_price_each}g
                    </div>
                    <div style="color: #4CAF50; font-size: 12px;">
                        Enter 1-{item_count}, 'a' for all, or 'c' to cancel
                    </div>
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; display: flex; flex-direction: column;">
                    {achievement_notifications}
                    <div style="font-size: 16px; font-weight: bold; margin-bottom: 5px;">{gs.active_vendor.name}'s Shop</div>
                    {player_stats_html}
                    <div style="padding: 20px;">
                        {quantity_html}
                    </div>
                </div>
            """
            current_commands_text = "1-9 = quantity | a = all | c = cancel"

        elif gs.prompt_cntl == "vendor_shop":
            # SHOP VIEW
            sorted_vendor_items = get_sorted_inventory(gs.active_vendor.inventory)
            vendor_html = "<h3 style='margin: 0 0 5px 0;'>Vendor Wares</h3>"
            vendor_html += "<div style='overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px; max-height: 200px;'>"
            if not sorted_vendor_items:
                vendor_html += "<div style='margin: 2px 0; padding: 0;'>(Out of stock)</div>"
            else:
                for i, item in enumerate(sorted_vendor_items):
                    # Vendors know what items are - show real names (for_vendor=True)
                    item_str = format_item_for_display(item, gs.player_character, show_price=True, is_sell_price=False, for_vendor=True)
                    vendor_html += f"<div style='margin: 2px 0; padding: 0;'><b>{i + 1}.</b> {item_str}</div>"
            vendor_html += "</div>"

            sorted_player_items = get_sorted_inventory(gs.player_character.inventory)
            player_inv_html = "<h3 style='margin: 0 0 5px 0;'>Your Inventory</h3>"
            player_inv_html += "<div style='overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px; max-height: 200px;'>"
            if not sorted_player_items:
                player_inv_html += "<div style='margin: 2px 0; padding: 0;'>(Empty)</div>"
            else:
                for i, item in enumerate(sorted_player_items):
                    # Player inventory shows cryptic names for unidentified items
                    item_str = format_item_for_display(item, gs.player_character, show_price=True, is_sell_price=True)
                    player_inv_html += f"<div style='margin: 2px 0; padding: 0;'><b>{i + 1}.</b> {item_str}</div>"
            player_inv_html += "</div>"

            vendor_sprite = generate_room_sprite_html('V')

            # Magic shop gets purple styling
            is_magic = gs.active_vendor.is_magic_shop if hasattr(gs.active_vendor, 'is_magic_shop') else False
            shop_title_color = '#c084fc' if is_magic else '#FFFFFF'
            shop_label = "Ye Olde Magic Shoppe" if is_magic else f"{gs.active_vendor.name}'s Shop"

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; display: flex; flex-direction: column; max-height: 100%; overflow: hidden;">
                    {achievement_notifications}
                    <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{vendor_sprite}</div>
                        <div>
                            <div style="font-size: 16px; font-weight: bold; color: {shop_title_color};">{shop_label}</div>
                            {'<div style="font-size: 12px; color: #a78bfa;">Proprietor: ' + gs.active_vendor.name + '</div>' if is_magic else ''}
                            <div style="color: #DAA520; margin-top: 2px;">{gs.shop_message}</div>
                        </div>
                    </div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; gap: 5px; flex: 1; min-height: 0; overflow: hidden;">
                        <div style="border: 1px solid grey; padding: 3px;">{vendor_html}</div>
                        <div style="border: 1px solid grey; padding: 3px;">{player_inv_html}</div>
                    </div>
                </div>
                """
            if gs.prompt_cntl == "sell_quantity_mode":
                current_commands_text = "1-9 / a = sell | c = cancel"
            elif gs.vendor_action:
                action_label = {'buy': 'buy', 'sell': 'sell', 'repair': 'repair', 'identify': 'identify'}.get(gs.vendor_action, gs.vendor_action)
                current_commands_text = f"# = {action_label} item | b = back"
            else:
                current_commands_text = "b = buy | s = sell | r = repair | id = identify | x = exit"



        elif gs.prompt_cntl == "inventory":

            # INVENTORY VIEW - Adapts to combat context

            # Initialize variable to prevent UnboundLocalError
            equipment_box_html = ""

            # Check if we're in combat inventory mode
            in_combat = gs.active_monster and gs.active_monster.is_alive()

            if in_combat:
                # COMBAT INVENTORY - Only show combat-usable items
                # Potions: all usable in combat
                # Scrolls: only spell_scroll, protection, restoration (combat-relevant)
                
                # Filter to only combat-usable items
                sorted_items = get_sorted_inventory(gs.player_character.inventory)
                combat_usable_items = []
                combat_scroll_types = ['spell_scroll', 'protection', 'restoration']
                for item in sorted_items:
                    if isinstance(item, Potion):
                        combat_usable_items.append(item)
                    elif isinstance(item, (Food, Meat)):
                        combat_usable_items.append(item)
                    elif isinstance(item, Scroll) and item.scroll_type in combat_scroll_types:
                        combat_usable_items.append(item)
                
                # Apply filter in combat too
                display_items = combat_usable_items
                combat_filter_label = "Combat Items"
                if gs.inventory_filter == 'eat':
                    display_items = [i for i in combat_usable_items if isinstance(i, (Food, Meat))]
                    combat_filter_label = "Food Items"
                elif gs.inventory_filter == 'use':
                    display_items = [i for i in combat_usable_items if isinstance(i, (Potion, Scroll))]
                    combat_filter_label = "Usable Items"

                combat_filter_indicator = ""
                if gs.inventory_filter:
                    combat_filter_indicator = f" <span style='color: #4FC3F7; font-size: 10px;'>[filtered]</span>"

                # Build inventory HTML - matching normal inventory style
                player_inv_html = f"<h3>{combat_filter_label}{combat_filter_indicator}</h3>"
                player_inv_html += "<div style='max-height: 280px; overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px;'>"
                player_inv_html += "<div style='margin: 0; padding: 0;'>"

                if not display_items:
                    player_inv_html += "<div style='margin: 2px 0; padding: 0; color: #888;'>(No matching items)</div>"
                else:
                    for i, item in enumerate(display_items):
                        item_str = format_item_for_display(item, gs.player_character, show_price=False)
                        player_inv_html += f"<div style='margin: 2px 0; padding: 0;'><b>{i + 1}.</b> {item_str}</div>"

                player_inv_html += "</div>"
                player_inv_html += "</div>"

                # COMBAT LAYOUT - matching normal inventory structure
                html_code = f"""
                        <div style="font-family: monospace; font-size: 12px; width: 100%; max-width: 100vw; overflow-x: auto; box-sizing: border-box;">
                            <div style="min-width: 0; max-width: 100%;">
                                {achievement_notifications}
                                <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                                {player_stats_html}
                                <div style="border: 1px solid #4CAF50; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px; overflow-x: auto; max-width: 100%;">{player_inv_html}</div>
                            </div>
                        </div>
                    """

                if gs.inventory_filter:
                    current_commands_text = "# = select | b = back"
                    if gs.inventory_filter == 'use' and player_character.health < player_character.max_health:
                        has_healing = any(isinstance(i, Potion) and i.potion_type == 'healing'
                                          for i in player_character.inventory.items)
                        if has_healing:
                            current_commands_text += " | df = drink full"
                else:
                    current_commands_text = "u = use | eat = eat | j = journal | x = close"


            else:

                # NON-COMBAT (Normal) INVENTORY VIEW

                # === EQUIPMENT BOX ===

                # Get equipped weapon info
                weapon_name = ""
                weapon_html = "<span style='color: #666;'>None</span>"
                if gs.player_character.equipped_weapon:
                    w = gs.player_character.equipped_weapon
                    weapon_name = w.get_display_name() if hasattr(w, 'get_display_name') else w.name
                    weapon_stats = f"Atk +{w.attack_bonus}"
                    if w.elemental_strength and w.elemental_strength[0] != "None":
                        weapon_stats += f" | {', '.join(w.elemental_strength)}"
                    weapon_html = f"<span style='color: #FFF;'>{weapon_name}</span> <span style='color: #888; font-size: 9px;'>({weapon_stats})</span>"

                # Get equipped armor info
                armor_name = ""
                armor_html = "<span style='color: #666;'>None</span>"
                if gs.player_character.equipped_armor:
                    a = gs.player_character.equipped_armor
                    armor_name = a.get_display_name() if hasattr(a, 'get_display_name') else a.name
                    armor_stats = f"Def +{a.defense_bonus}"
                    if a.elemental_strength and a.elemental_strength[0] != "None":
                        armor_stats += f" | {', '.join(a.elemental_strength)}"
                    armor_html = f"<span style='color: #FFF;'>{armor_name}</span> <span style='color: #888; font-size: 9px;'>({armor_stats})</span>"

                # Get equipped accessories info

                accessories_lines = []

                equipped_accessories = getattr(gs.player_character, 'equipped_accessories', [None, None, None, None])

                for i, acc in enumerate(equipped_accessories):

                    if acc:

                        accessories_lines.append(f"<span style='color: #FFF;'>{acc.name}</span>")

                    else:

                        accessories_lines.append("<span style='color: #666;'>Empty</span>")

                equipment_box_html = f"""
                        <div style="max-height: 200px; overflow-y: auto; border: 1px solid #555; padding: 4px; border-radius: 4px; margin-bottom: 2px; background: #1a1a1a;">
                            <div style="color: #FFD700; font-weight: bold; font-size: 12px; margin-bottom: 1px;">EQUIPPED</div>
                            <div style="font-size: 12px; line-height: 1.4;">
                                <div><span style='color: #FF6F00;'>Weapon:</span> {weapon_html}</div>
                                <div><span style='color: #4CAF50;'>Armor:</span>  {armor_html}</div>
                                <div><span style='color: #E040FB;'>Acc 1:</span>  {accessories_lines[0]}</div>
                                <div><span style='color: #E040FB;'>Acc 2:</span>  {accessories_lines[1]}</div>
                                <div><span style='color: #E040FB;'>Acc 3:</span>  {accessories_lines[2]}</div>
                                <div><span style='color: #E040FB;'>Acc 4:</span>  {accessories_lines[3]}</div>
                            </div>
                        </div>
                    """

                sorted_items = get_sorted_inventory(gs.player_character.inventory)

                # Apply inventory filter
                display_items = sorted_items
                filter_label = "Your Inventory"
                if gs.inventory_filter == 'use':
                    display_items = [i for i in sorted_items if isinstance(i, (Potion, Scroll, Flare, Lantern, LanternFuel, Treasure, Towel, CookingKit, CuringKit))]
                    filter_label = "Usable Items"
                elif gs.inventory_filter == 'equip':
                    display_items = [i for i in sorted_items if isinstance(i, (Weapon, Armor, Towel)) or (isinstance(i, Treasure) and getattr(i, 'treasure_type', '') == 'passive')]
                    filter_label = "Equippable Items"
                elif gs.inventory_filter == 'eat':
                    display_items = [i for i in sorted_items if isinstance(i, (Food, Meat))]
                    filter_label = "Food Items"

                filter_indicator = ""
                if gs.inventory_filter:
                    filter_indicator = f" <span style='color: #4FC3F7; font-size: 10px;'>[filtered - tap again to show all]</span>"

                player_inv_html = f"<h3>{filter_label}{filter_indicator}</h3>"

                player_inv_html += "<div style='max-height: 295px; overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px;'>"

                player_inv_html += "<div style='margin: 0; padding: 0;'>"

                if not display_items:
                    player_inv_html += "<div style='margin: 2px 0; padding: 0; color: #888;'>(No matching items)</div>"
                else:
                    for i, item in enumerate(display_items):
                        item_str = format_item_for_display(item, gs.player_character, show_price=False)
                        player_inv_html += f"<div style='margin: 2px 0; padding: 0;'><b>{i + 1}.</b> {item_str}</div>"

                player_inv_html += "</div>"

                player_inv_html += "</div>"

                can_cast = can_cast_spells(gs.player_character)

                if gs.inventory_filter:
                    # Filter active: numpad mode with back button
                    filter_label = {'use': 'Use', 'equip': 'Equip', 'eat': 'Eat'}.get(gs.inventory_filter, gs.inventory_filter)
                    inv_commands = f"# = {filter_label.lower()} item | b = back"
                    # Add "Drink Full" option when in use filter and player has healing potions + is hurt
                    if gs.inventory_filter == 'use' and player_character.health < player_character.max_health:
                        has_healing = any(isinstance(i, Potion) and i.potion_type == 'healing'
                                          for i in player_character.inventory.items)
                        if has_healing:
                            inv_commands += " | df = drink full"
                else:
                    # Main inventory: centered command buttons, no numpad
                    inv_commands = "u = use | e = equip | eat = eat | c = craft"
                    if can_cast:
                        inv_commands += " | m = spells"
                    inv_commands += " | j = journal | q = quit game | x = exit"

                html_code = f"""

                        <div style="font-family: monospace; font-size: 12px; width: 100%; max-width: 100vw; overflow-x: auto; box-sizing: border-box;">

                            <div style="min-width: 0; max-width: 100%;">

                                {achievement_notifications}

                                <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>

                                {player_stats_html}

                                {equipment_box_html}

                                <div style="border: 1px solid #4CAF50; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px; overflow-x: auto; max-width: 100%;">{player_inv_html}</div>

                            </div>

                        </div>

                    """

                current_commands_text = inv_commands

        elif gs.prompt_cntl == "character_stats_mode":
            # CHARACTER STATS SCREEN
            # Build stats_html (same as inventory stats)
            
            # Spell Slots HTML - only show if player can cast spells
            can_cast = can_cast_spells(gs.player_character)
            spell_slots_html = ""
            
            if can_cast:
                max_slots = gs.player_character.get_max_memorized_spell_slots()
                used_slots = gs.player_character.get_used_spell_slots()
                spell_slots_html = f"""
                    <h3>Spell Slots</h3>
                    <b>Used:</b> {used_slots}/{max_slots}<br>
                    <b>Available:</b> {max_slots - used_slots}<br>
                    <hr>
                    <b>Memorized Spells:</b><br>
                    """
                if gs.player_character.memorized_spells:
                    spell_slots_html += "<ul style='margin: 5px 0; padding-left: 20px;'>"
                    for spell in gs.player_character.memorized_spells:
                        slots_used = gs.player_character.get_spell_slots(spell)
                        spell_slots_html += f"<div style='margin: 2px 0; padding: 0;'>{spell.name} ({slots_used} slot{'s' if slots_used > 1 else ''})</div>"
                    spell_slots_html += "</div>"
                else:
                    spell_slots_html += "<i>(None)</i><br>"

            ## Character Stats HTML
            player_sprite_html = generate_player_sprite_html(
                getattr(gs.player_character, 'race', 'human'),
                getattr(gs.player_character, 'gender', 'male'),
                getattr(gs.player_character, 'equipped_armor', None)
            )
            stats_html = f"""
                {player_sprite_html}
                <b>Name:</b> {gs.player_character.name} | <b>Level:</b> {gs.player_character.level} ({gs.player_character.experience} XP) |
                <b>Race:</b> {gs.player_character.race} | <b> Class:</b> {gs.player_character.character_class}<br>
                <hr>
                <b>Health:</b> {gs.player_character.health} / {gs.player_character.max_health} |
                <b>Mana:</b> {gs.player_character.mana} / {gs.player_character.max_mana}<br>
                <b>Attack:</b> {gs.player_character.attack} | <b> Defense:</b> {gs.player_character.defense}<br>
                <hr>
                <b>Str:</b> {gs.player_character.strength} | <b>Dex:</b> {gs.player_character.dexterity} | <b>Int:</b> {gs.player_character.intelligence}<br>
                <hr>
                """

            # Add Elemental Resistances section
            if gs.player_character.elemental_strengths:
                stats_html += f"""
                <div style="padding: 3px; border-radius: 3px; margin-bottom: 5px;">
                    <b style="color: #4CAF50;">[RESIST]:</b><br>
                    <span style="color: #DDD; font-size: 12px;">{', '.join(gs.player_character.elemental_strengths)}</span>
                </div>
                """
            else:
                stats_html += """
                <div style="padding: 3px; border-radius: 3px; margin-bottom: 5px;">
                    <b style="color: #888;">[RESIST]:</b> <span style="color: #888; font-size: 12px;">None</span>
                </div>
                """

            # Add Elemental Weaknesses section
            if gs.player_character.elemental_weaknesses:
                stats_html += f"""
                <div style="padding: 3px; border-radius: 3px; margin-bottom: 5px;">
                    <b style="color: #F44336;">[WEAK]:</b><br>
                    <span style="color: #DDD; font-size: 12px;">{', '.join(gs.player_character.elemental_weaknesses)}</span>
                </div>
                """
            else:
                stats_html += """
                <div style="padding: 3px; border-radius: 3px; margin-bottom: 5px;">
                    <b style="color: #888;">[WEAK]:</b> <span style="color: #888; font-size: 12px;">None</span>
                </div>
                """

            stats_html += "<hr>"
            stats_html += spell_slots_html
            
            # Add Accessories section
            stats_html += """<hr><b>Equipped Accessories:</b><br>"""
            has_accessories = False
            for i, acc in enumerate(gs.player_character.equipped_accessories):
                if acc:
                    has_accessories = True
                    stats_html += f"""<div style="color: #FFD700; font-size: 12px;">{i+1}. {acc.name}</div>"""
                    if acc.passive_effect:
                        stats_html += f"""<div style="color: #00CED1; font-size: 9px; margin-left: 10px;">- {acc.passive_effect}</div>"""
            if not has_accessories:
                stats_html += """<span style="color: #888; font-size: 12px;">(None equipped)</span>"""
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    
                    <div style="border: 1px solid #444; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px;">{stats_html}</div>
</div>
                """
            current_commands_text = "x = back to inventory"

        elif gs.prompt_cntl == "crafting_mode":
            # CRAFTING MENU VIEW - Full HTML display
            available_recipes = get_available_recipes(gs.player_character)
            craftable = [r for r in available_recipes if r[2]]
            close = [r for r in available_recipes if not r[2]]
            
            # Count ingredients
            ingredient_counts = {}
            for item in gs.player_character.inventory.items:
                if isinstance(item, Ingredient):
                    ingredient_counts[item.name] = ingredient_counts.get(item.name, 0) + 1
            # Count rations
            ration_count = 0
            for item in gs.player_character.inventory.items:
                if isinstance(item, Food) and item.name == "Rations":
                    ration_count += getattr(item, 'count', 1)

            # Build ingredients display
            ingredients_html = "<div style='margin-bottom: 10px;'>"
            ingredients_html += "<div style='color: #4CAF50; font-weight: bold; font-size: 16px; margin-bottom: 5px;'>Your Ingredients:</div>"
            if ingredient_counts:
                ing_list = ", ".join([f"{count}x {name}" for name, count in sorted(ingredient_counts.items())])
                ingredients_html += f"<div style='color: #DDD; font-size: 15px;'>{ing_list}</div>"
            else:
                ingredients_html += "<div style='color: #BBB; font-size: 15px; font-style: italic;'>No ingredients. Harvest from Garden rooms!</div>"
            if ration_count > 0:
                ingredients_html += f"<div style='color: #88FF88; font-size: 15px;'>{ration_count}x Rations</div>"
            ingredients_html += "</div>"
            
            # Build craftable recipes HTML
            recipes_html = ""
            if craftable:
                # Group by tier
                by_tier = {}
                for recipe_name, recipe_data, can_craft, _ in craftable:
                    tier = recipe_data.get('tier', 1)
                    if tier not in by_tier:
                        by_tier[tier] = []
                    by_tier[tier].append((recipe_name, recipe_data))
                
                tier_colors = {1: '#4CAF50', 2: '#03A9F4', 3: '#FFD700', 4: '#E040FB', 5: '#F44336'}
                tier_names = {1: 'Basic', 2: 'Intermediate', 3: 'Advanced', 4: 'Legendary', 5: 'Ultimate'}
                
                recipe_counter = 1
                for tier in sorted(by_tier.keys()):
                    tier_color = tier_colors.get(tier, '#888')
                    recipes_html += f"<div style='color: {tier_color}; font-weight: bold; font-size: 16px; margin: 8px 0 4px 0; border-bottom: 1px solid {tier_color};'>TIER {tier} - {tier_names[tier]}</div>"
                    
                    for recipe_name, recipe_data in by_tier[tier]:
                        crafted_item = recipe_data['result']()
                        ingredients_text = ", ".join([f"{count}x {name}" for name, count in recipe_data['ingredients']])
                        ration_cost = recipe_data.get('ration_cost', 0)
                        if ration_cost > 0:
                            ingredients_text += f", {ration_cost}x Rations"

                        recipes_html += f"""
                            <div style='padding: 6px; margin: 4px 0; background: rgba(255,255,255,0.05); border-radius: 3px; border-left: 3px solid {tier_color};'>
                                <div style='color: #FFD700; font-weight: bold; font-size: 16px;'>{recipe_counter}. {recipe_name}</div>
                                <div style='color: #DDD; font-size: 15px;'>Needs: {ingredients_text}</div>
                                <div style='color: #EEE; font-size: 15px; font-style: italic;'>{crafted_item.description}</div>
                            </div>
                        """
                        recipe_counter += 1
            else:
                recipes_html = "<div style='color: #CCC; font-style: italic; padding: 10px; font-size: 15px;'>No recipes available. Collect more ingredients!</div>"
            
            # Build close recipes HTML
            close_html = ""
            if close:
                close_html = "<div style='margin-top: 10px; padding-top: 8px; border-top: 1px solid #444;'>"
                close_html += "<div style='color: #DDD; font-size: 15px; margin-bottom: 5px;'>Almost Craftable:</div>"
                for recipe_name, recipe_data, _, missing in close[:3]:
                    missing_text = ", ".join([f"{count}x {name}" for name, count in missing])
                    tier = recipe_data.get('tier', 1)
                    close_html += f"<div style='color: #BBB; font-size: 14px;'>T{tier} {recipe_name} - <span style='color: #F44336;'>Need: {missing_text}</span></div>"
                if len(close) > 3:
                    close_html += f"<div style='color: #AAA; font-size: 14px;'>...and {len(close) - 3} more</div>"
                close_html += "</div>"
            
            crafting_html = f"""
                <div style="border: 2px solid #E040FB; border-radius: 4px; padding: 10px; background: #1a1a1a;">
                    <div style="color: #E040FB; font-weight: bold; font-size: 18px; text-align: center; margin-bottom: 8px;">
                        CRAFTING
                    </div>
                    {ingredients_html}
                    <div style="max-height: 500px; overflow-y: auto;">
                        {recipes_html}
                    </div>
                    {close_html}
                    <div style="text-align: center; margin-top: 8px; color: #DDD; font-size: 15px;">
                        Craftable: {len(craftable)} | Enter number to craft
                    </div>
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div class="room-panel" style="width: 100%;">{crafting_html}</div>
                </div>
            """
            current_commands_text = "# = craft | x = back to inventory"
            needs_numbers = True

        elif gs.prompt_cntl == "spell_memorization_mode":
            # SPELL MEMORIZATION MENU VIEW

            all_spells = gs.player_character.get_spell_inventory()
            max_slots = gs.player_character.get_max_memorized_spell_slots()
            used_slots = gs.player_character.get_used_spell_slots()

            # Available spells HTML
            available_spells_html = "<h3>Spells in Inventory</h3>"
            available_spells_html += "<div style='max-height: 280px; overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px;'>"
            available_spells_html += "<ul style='margin: 0; padding-left: 20px;'>"
            if not all_spells:
                available_spells_html += "<p>You have no spell scrolls in your inventory.</p>"
            else:
                available_spells_html += "<ul>"
                for i, spell in enumerate(all_spells):
                    identified = is_item_identified(spell)
                    display_name = get_item_display_name(spell)
                    is_memorized = spell in gs.player_character.memorized_spells
                    color = "#888" if is_memorized else "#FFF"
                    marker = " <span style='color: #4CAF50;'>[MEM]</span>" if is_memorized else ""

                    if identified:
                        slots_needed = gs.player_character.get_spell_slots(spell)
                        spell_info = f"<b>{display_name}</b>{marker}<br>"
                        spell_info += f"&nbsp;&nbsp;L{spell.level} | "
                        spell_info += f"{spell.mana_cost} MP | "
                        spell_info += f"{slots_needed} slot{'s' if slots_needed > 1 else ''}<br>"
                        spell_info += f"&nbsp;&nbsp;Type: {spell.spell_type}"
                    else:
                        spell_info = f"<b>{display_name}</b> <span style='color: #888;'>[?]</span>"

                    available_spells_html += f"<li style='color: {color}; margin-bottom: 5px;'><b>{i + 1}.</b> {spell_info}</li>"
                available_spells_html += "</ul>"
            available_spells_html += "</div>"

            # Memorized spells HTML with progress bar
            memorized_html = f"""
                <h3>Spell Slots: {used_slots}/{max_slots}</h3>
                <div style="background-color: #333; padding: 3px; border-radius: 3px; margin-bottom: 5px;">
                    <div style="background-color: #4CAF50; width: {(used_slots / max_slots) * 100 if max_slots > 0 else 0}%; height: 20px; border-radius: 2px;"></div>
                </div>
                <b>Available Slots:</b> {max_slots - used_slots}<br>
                <hr>
                <h3>Currently Memorized</h3>
                """

            if gs.player_character.memorized_spells:
                memorized_html += "<ul>"
                for i, spell in enumerate(gs.player_character.memorized_spells):
                    slots_used = gs.player_character.get_spell_slots(spell)
                    memorized_html += f"<li><b>{i + 1}.</b> {spell.name} ({slots_used} slot{'s' if slots_used > 1 else ''})</li>"
                memorized_html += "</ul>"
            else:
                memorized_html += "<p><i>No spells memorized</i></p>"

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>

                    <div style="border: 1px solid green; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px;">{memorized_html}</div>
                    
                    <div style="border: 1px solid blue; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px;">{available_spells_html}</div>
</div>
                """
            if gs.spell_memo_action:
                action_label = {'memorize': 'memorize', 'forget': 'forget'}.get(gs.spell_memo_action, gs.spell_memo_action)
                current_commands_text = f"# = {action_label} spell | b = back"
            else:
                current_commands_text = "m = memorize | f = forget | x = exit"

        elif gs.prompt_cntl == "journal_mode":
            # JOURNAL MAIN MENU

            # Count discovered vs total in each category
            weapons_found = len(gs.discovered_items['weapons'])
            weapons_total = len(WEAPON_TEMPLATES)

            armor_found = len(gs.discovered_items['armor'])
            armor_total = len(ARMOR_TEMPLATES)

            potions_found = len(gs.discovered_items['potions'])
            potions_total = len(POTION_TEMPLATES)

            scrolls_found = len(gs.discovered_items['scrolls'])
            scrolls_total = len(SCROLL_TEMPLATES)

            spells_found = len(gs.discovered_items['spells'])
            spells_total = len(SPELL_TEMPLATES)

            treasures_found = len(gs.discovered_items['treasures'])
            treasures_total = len(TREASURE_TEMPLATES)

            utilities_found = len(gs.discovered_items['utilities'])
            utilities_total = len(UTILITY_TEMPLATES)

            ingredients_found = len(gs.discovered_items['ingredients'])
            ingredients_total = len(INGREDIENT_TEMPLATES)

            total_found = weapons_found + armor_found + potions_found + scrolls_found + spells_found + treasures_found + utilities_found + ingredients_found
            total_items = weapons_total + armor_total + potions_total + scrolls_total + spells_total + treasures_total + utilities_total + ingredients_total
            completion_pct = int((total_found / total_items) * 100) if total_items > 0 else 0

            journal_html = f"""
                <h3> Adventurer's Journal</h3>
                <div style="padding: 3px; border-radius: 3px; margin-bottom: 15px;">
                    <div style=""background-color: #4CAF50; width: {completion_pct}%; height: 20px; border-radius: 2px; text-align: center; line-height: 20px; color: #000; font-weight: bold;">
                        {total_found}/{total_items} Items Discovered ({completion_pct}%)
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 2px; width: 100%; ">
                    <div style="border: 2px solid #FF6F00; padding: 2px; border-radius: 2px;">
                        <b style="color: #FF6F00;">1.  Weapons ({weapons_found}/{weapons_total})</b><br>
                        <span style="font-size: 12px; color: #DDD;">Swords, axes, and instruments of combat</span>
                    </div>

                    <div style="border: 2px solid #4CAF50; padding: 2px; border-radius: 2px;">
                        <b style="color: #4CAF50;">2.  Armor ({armor_found}/{armor_total})</b><br>
                        <span style="font-size: 12px; color: #DDD;">Protective gear and defensive equipment</span>
                    </div>

                    <div style="border: 2px solid #E91E63; padding: 2px; border-radius: 2px;">
                        <b style="color: #E91E63;">3.  Potions ({potions_found}/{potions_total})</b><br>
                        <span style="font-size: 12px; color: #DDD;">Elixirs, brews, and magical drinks</span>
                    </div>

                    <div style="border: 2px solid #E040FB; padding: 2px; border-radius: 2px;">
                        <b style="color: #E040FB;">4.  Scrolls ({scrolls_found}/{scrolls_total})</b><br>
                        <span style="font-size: 12px; color: #DDD;">Ancient parchments with mystical powers</span>
                    </div>

                    <div style="border: 2px solid #2196F3; padding: 2px; border-radius: 2px;">
                        <b style="color: #2196F3;">5.  Spells ({spells_found}/{spells_total})</b><br>
                        <span style="font-size: 12px; color: #DDD;">Arcane knowledge and magical incantations</span>
                    </div>

                    <div style="border: 2px solid #FFD700; padding: 2px; border-radius: 2px;">
                        <b style="color: #FFD700;">6.  Treasures ({treasures_found}/{treasures_total})</b><br>
                        <span style="font-size: 12px; color: #DDD;">Rare artifacts and precious items</span>
                    </div>

                    <div style="border: 2px solid #607D8B; padding: 2px; border-radius: 2px;">
                        <b style="color: #607D8B;">7.  Utilities ({utilities_found}/{utilities_total})</b><br>
                        <span style="font-size: 12px; color: #DDD;">Tools, lights, food and practical equipment</span>
                    </div>

                    <div style="border: 2px solid #8BC34A; padding: 2px; border-radius: 2px;">
                        <b style="color: #8BC34A;">8.  Ingredients ({ingredients_found}/{ingredients_total})</b><br>
                        <span style="font-size: 12px; color: #DDD;">Herbs, reagents and alchemical materials</span>
                    </div>
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>

                    <div style="border: 1px solid gold; padding: 10px; max-height: 500px; overflow-y: auto;">
                        {journal_html}
                    </div>
</div>
                """
            text_label = "Aa-" if gs.large_text_mode else "Aa+"
            music_label = "vol-" if gs.music_enabled else "vol+"
            current_commands_text = f"1-8 = category | s = stats | a = achvs | t = {text_label} | v = {music_label} | g = save | x = back"

        elif gs.prompt_cntl.startswith("journal_"):
            # JOURNAL CATEGORY VIEW
            category = gs.prompt_cntl.replace("journal_", "")

            # Get the appropriate template list and discovered set
            template_map = {
                'weapons': (WEAPON_TEMPLATES, gs.discovered_items['weapons'], '', '#FF6F00'),
                'armor': (ARMOR_TEMPLATES, gs.discovered_items['armor'], '', '#4CAF50'),
                'potions': (POTION_TEMPLATES, gs.discovered_items['potions'], '', '#E91E63'),
                'scrolls': (SCROLL_TEMPLATES, gs.discovered_items['scrolls'], '', '#E040FB'),
                'spells': (SPELL_TEMPLATES, gs.discovered_items['spells'], '', '#2196F3'),
                'treasures': (TREASURE_TEMPLATES, gs.discovered_items['treasures'], '', '#FFD700'),
                'utilities': (UTILITY_TEMPLATES, gs.discovered_items['utilities'], '', '#607D8B'),
                'ingredients': (INGREDIENT_TEMPLATES, gs.discovered_items['ingredients'], '', '#8BC34A')
            }

            if category not in template_map:
                category = 'weapons'  # Fallback

            templates, discovered_set, icon, color = template_map[category]
            category_name = category.capitalize()

            # Build entries HTML
            entries_html = ""
            for item_template in templates:
                is_discovered = item_template.name in discovered_set

                if is_discovered:
                    # Show full details
                    entry_html = f"""
                        <div style="border-left: 3px solid {color}; padding: 4px; margin: 5px 0; border-radius: 3px;">
                            <div style="color: {color}; font-weight: bold; font-size: 12px;">{icon} {item_template.name}</div>
                            <div style="color: #DDD; font-size: 12px; margin-top: 3px;">{item_template.description}</div>
                        """

                    # Add type-specific stats
                    if isinstance(item_template, Weapon):
                        entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Attack:</b> {item_template._base_attack_bonus} |
                                <b>Value:</b> {item_template.value}g
                            </div>
                            """
                        if item_template.elemental_strength[0] != "None":
                            entry_html += f"""
                                <div style="color: #64B5F6; font-size: 12px;">
                                    <b>Element:</b> {', '.join(item_template.elemental_strength)}
                                </div>
                                """

                    elif isinstance(item_template, Armor):
                        entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Defense:</b> {item_template._base_defense_bonus} |
                                <b>Value:</b> {item_template.value}g
                            </div>
                            """
                        if item_template.elemental_strength[0] != "None":
                            entry_html += f"""
                                <div style="color: #64B5F6; font-size: 12px;">
                                    <b>Element:</b> {', '.join(item_template.elemental_strength)}
                                </div>
                                """

                    elif isinstance(item_template, Potion):
                        entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Type:</b> {item_template.potion_type} |
                                <b>Value:</b> {item_template.value}g
                            </div>
                            """
                        if item_template.effect_magnitude > 0:
                            entry_html += f"""
                                <div style="color: #4CAF50; font-size: 12px;">
                                    <b>Effect:</b> {item_template.effect_magnitude}
                                    {f'for {item_template.duration} turns' if item_template.duration > 0 else ''}
                                </div>
                                """

                    elif isinstance(item_template, Scroll):
                        entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Type:</b> {item_template.scroll_type} |
                                <b>Value:</b> {item_template.value}g
                            </div>
                            <div style="color: #E040FB; font-size: 12px; font-style: italic;">
                                {item_template.effect_description}
                            </div>
                            """

                    elif isinstance(item_template, Spell):
                        slots_needed = 1 if item_template.level == 0 else (2 if item_template.level <= 2 else 3)
                        entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Mana:</b> {item_template.mana_cost} |
                                <b>Slots:</b> {slots_needed}
                            </div>
                            """
                        if item_template.spell_type == 'damage':
                            entry_html += f"""
                                <div style="color: #F44336; font-size: 12px;">
                                    <b>Damage:</b> {item_template.base_power} {item_template.damage_type}
                                </div>
                                """
                        elif item_template.spell_type == 'healing':
                            entry_html += f"""
                                <div style="color: #4CAF50; font-size: 12px;">
                                    <b>Healing:</b> {item_template.base_power} HP
                                </div>
                                """

                    elif isinstance(item_template, Treasure):
                        entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Type:</b> {item_template.treasure_type}
                            </div>
                            """
                        if item_template.gold_value > 0:
                            entry_html += f"""
                                <div style="color: #FFD700; font-size: 12px;">
                                    <b>Gold Value:</b> {item_template.gold_value}g
                                </div>
                                """
                        if item_template.is_unique:
                            entry_html += f"""
                                <div style="color: #FF69B4; font-size: 12px; font-weight: bold;">
                                     UNIQUE TREASURE 
                                </div>
                                """

                    else:  # Utilities and Ingredients
                        if isinstance(item_template, Food):
                            entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Nutrition:</b> +{item_template.nutrition} |
                                <b>Value:</b> {item_template.value}g
                            </div>
                            """
                        elif isinstance(item_template, CookingKit):
                            entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Value:</b> {item_template.value}g
                            </div>
                            <div style="color: #FF9800; font-size: 12px;">Cooks all raw meat. Reusable.</div>
                            """
                        elif isinstance(item_template, Ingredient):
                            rarity = 'Common' if item_template.level <= 1 else ('Uncommon' if item_template.level <= 2 else ('Rare' if item_template.level <= 4 else 'Legendary'))
                            rarity_color = {'Common': '#9E9E9E', 'Uncommon': '#4CAF50', 'Rare': '#2196F3', 'Legendary': '#FF69B4'}[rarity]
                            entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Type:</b> {item_template.ingredient_type} |
                                <b>Value:</b> {item_template.value}g
                            </div>
                            <div style="color: {rarity_color}; font-size: 12px;"><b>{rarity}</b></div>
                            """
                        else:
                            entry_html += f"""
                            <div style="color: #888; font-size: 12px; margin-top: 5px;">
                                <b>Level:</b> {item_template.level} |
                                <b>Value:</b> {item_template.value}g
                            </div>
                            """

                    entry_html += "</div>"

                else:
                    # Show as undiscovered
                    entry_html = f"""
                        <div style="border-left: 3px solid #333; padding: 4px; margin: 5px 0; border-radius: 3px; opacity: 0.5;">
                            <div style="color: #555; font-weight: bold; font-size: 12px;"> ???</div>
                            <div style="color: #555; font-size: 12px; margin-top: 3px; font-style: italic;">Not yet discovered</div>
                        </div>
                        """

                entries_html += entry_html

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; display: flex; flex-direction: column;">
                    {achievement_notifications}
                    <div style="font-size: 16px; font-weight: bold; margin-bottom: 5px; color: {color};">{icon} {category_name}</div>
                    {player_stats_html}

                    <div style="border: 2px solid {color}; padding: 10px; max-height: 500px; overflow-y: auto;">
                        {entries_html}
                    </div>

                    <div style="margin-top: 10px;">
                        Commands: <b>b</b> to go back | <b>x</b> to close journal
                    </div>
                </div>
                """
            text_label = "Aa-" if gs.large_text_mode else "Aa+"
            music_label = "vol-" if gs.music_enabled else "vol+"
            current_commands_text = f"b = back | s = stats | a = achvs | t = {text_label} | v = {music_label} | g = save | x = close"

        elif gs.prompt_cntl == "spell_casting_mode":
            # SPELL CASTING - Compact: Combat panels + spell list (no map)
            # Map is hidden to give spell list room on mobile screens.

            # Generate pixel art sprite for the monster
            monster_sprite_html = generate_monster_sprite_html(gs.active_monster.name)
            evo_border_color, evo_tier_label = get_evolution_tier_style(gs.active_monster)

            # Compact Monster Info (same as combat_mode compact style)
            evo_border_style = f"border: 2px solid {evo_border_color};" if evo_border_color else "border: 2px solid #666;"
            evo_name_color = evo_border_color if evo_border_color else "#F44336"
            monster_html = f"""
                <div id="monster_panel" style="position:relative; padding: 3px; border-radius: 3px; {evo_border_style} margin-bottom: 4px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{monster_sprite_html}</div>
                        <div>
                            <div style="color: {evo_name_color}; font-weight: bold; font-size: 12px; margin-bottom: 2px;">{gs.active_monster.name} {evo_tier_label}</div>
                            <div style="font-size: 9px; margin-bottom: 2px;">Lv {gs.active_monster.level}</div>
                            <div style="font-size: 9px;"><span class="monster-hp-bar">{health_bar(_m_display_hp, gs.active_monster.max_health, width=10)}</span></div>
                            {f'<div style="font-size: 8px; color: #FFB74D; margin-top: 2px;">{", ".join(gs.active_monster.elemental_weakness)}</div>' if gs.active_monster.elemental_weakness else ''}
                            {f'<div style="font-size: 8px; color: #64B5F6; margin-top: 1px;">{", ".join(gs.active_monster.elemental_strength)}</div>' if gs.active_monster.elemental_strength else ''}
                    <div id="monster_init_dice" style="position:absolute;right:100px;top:50%;transform:translateY(-50%) scale(1.55);transform-origin:right center;width:58px;height:44px;z-index:5;"></div><div id="monster_dice" style="position:absolute;right:4px;top:50%;transform:translateY(-50%) scale(1.3);transform-origin:right center;width:68px;height:52px;display:flex;gap:4px;"><div id="monster_def_dice" style="position:relative;width:32px;height:52px;"></div><div id="monster_atk_dice" style="position:relative;width:32px;height:52px;"></div></div>
                </div>
                    </div>
                    
                </div>
                """

            # Compact Player Combat Info (mana emphasized for spell selection)
            player_sprite_html_combat = generate_player_sprite_html(
                getattr(gs.player_character, 'race', 'human'),
                getattr(gs.player_character, 'gender', 'male'),
                getattr(gs.player_character, 'equipped_armor', None)
            )
            player_combat_html = f"""
                <div id="player_panel" style="position:relative; padding: 3px; border-radius: 3px; border: 2px solid #666;{low_hp_pulse_style}">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:2px;">
                        <div style="flex-shrink:0;">{player_sprite_html_combat}</div>
                        <div>
                            <div style="color: #4CAF50; font-weight: bold; font-size: 12px; margin-bottom: 2px;"> {gs.player_character.name}</div>
                            <div style="font-size: 9px; margin-bottom: 1px;"><span class="player-hp-bar">{health_bar(_p_display_hp, gs.player_character.max_health, width=10)}</span></div>
                            <div style="font-size: 9px; margin-bottom: 2px;">{mana_bar(gs.player_character.mana, gs.player_character.max_mana, width=10)}</div>
                            <div style="font-size: 8px;">A:{gs.player_character.attack} D:{gs.player_character.defense} Int:{gs.player_character.intelligence}</div>
                    <div id="player_init_dice" style="position:absolute;right:100px;top:50%;transform:translateY(-50%) scale(1.55);transform-origin:right center;width:58px;height:44px;z-index:5;"></div><div id="player_dice" style="position:absolute;right:4px;top:50%;transform:translateY(-50%) scale(1.3);transform-origin:right center;width:68px;height:52px;display:flex;gap:4px;"><div id="player_atk_dice" style="position:relative;width:32px;height:52px;"></div><div id="player_def_dice" style="position:relative;width:32px;height:52px;"></div></div>
                </div>
                    </div>
                    
                </div>
                """

            # Spells List
            available_spells = gs.player_character.memorized_spells
            spells_html = '<div style="padding: 4px; border-radius: 4px; border: 2px solid #E040FB; max-height: 45vh; overflow-y: auto;">'
            spells_html += '<div style="color: #E040FB; font-weight: bold; font-size: 13px; margin-bottom: 4px;"> Cast Spell</div>'

            if not available_spells:
                spells_html += '<div style="color: #F44336; font-size: 12px;">No spells memorized!</div>'
            else:
                for i, spell in enumerate(available_spells):
                    can_cast = gs.player_character.mana >= spell.mana_cost
                    color = "#4CAF50" if can_cast else "#888"
                    charge_turns = get_spell_charge_turns(spell)
                    charge_tag = ""
                    if charge_turns > 0:
                        charge_tag = f' <span style="color:#CE93D8;">[{charge_turns}T]</span>'

                    spell_line = f'<div style="color: {color}; font-size: 11px; margin-bottom: 4px; padding: 3px; border-radius: 2px;">'
                    spell_line += f'<b>{i + 1}. {spell.name}</b> ({spell.mana_cost} MP){charge_tag}<br>'
                    spell_line += f'&nbsp;&nbsp;Lvl {spell.level} | '

                    if spell.spell_type == 'damage':
                        spell_line += f'{spell.damage_type} | Pwr {spell.base_power}'
                    elif spell.spell_type == 'healing':
                        spell_line += f'Heal {spell.base_power} HP'
                    elif spell.spell_type in ['add_status_effect', 'remove_status']:
                        spell_line += f'{spell.status_effect_name}'
                    elif spell.spell_type == 'debuff_target':
                        spell_line += f'{spell.status_effect_name}'

                    spell_line += '</div>'
                    spells_html += spell_line

            spells_html += '</div>'

            # Layout: Compact combat panels + spell list (no map — all visible)
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}

                    <div style="width: 100%; max-width: 300px; margin: 0 auto 4px auto;">
                        {monster_html}
                        {player_combat_html}
                    </div>

                    {spells_html}
                    {generate_damage_float_js(gs.active_monster.name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal, gs.last_monster_damage_badge, gs.last_player_damage_badge, _spell_element, _spell_level)}
                    {generate_hp_drain_js(gs.active_monster.health, gs.active_monster.max_health, gs.player_character.health, gs.player_character.max_health, gs.last_monster_damage, gs.last_player_damage, gs.last_player_heal, bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}

                </div>
                """
            current_commands_text = "#  = cast spell | x = cancel"

        elif gs.prompt_cntl == "combat_mode":
            # COMBAT VIEW WITH MAP - 3 Column Layout

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            highlight_coords = (gs.player_character.y, gs.player_character.x)

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Generate pixel art sprite for the monster
            monster_sprite_html = generate_monster_sprite_html(gs.active_monster.name)
            evo_border_color, evo_tier_label = get_evolution_tier_style(gs.active_monster)

            # Compact Monster Info
            evo_border_style = f"border: 2px solid {evo_border_color};" if evo_border_color else "border: 2px solid #666;"
            evo_name_color = evo_border_color if evo_border_color else "#F44336"
            monster_html = f"""
                <div id="monster_panel" style="position:relative; padding: 3px; border-radius: 3px; {evo_border_style} margin-bottom: 4px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{monster_sprite_html}</div>
                        <div>
                            <div style="color: {evo_name_color}; font-weight: bold; font-size: 12px; margin-bottom: 2px;">{gs.active_monster.name} {evo_tier_label}</div>
                            <div style="font-size: 9px; margin-bottom: 2px;">Lv {gs.active_monster.level}</div>
                            <div style="font-size: 9px;"><span class="monster-hp-bar">{health_bar(_m_display_hp, gs.active_monster.max_health, width=10)}</span></div>
                            {f'<div style="font-size: 8px; color: #FFB74D; margin-top: 2px;">{", ".join(gs.active_monster.elemental_weakness)}</div>' if gs.active_monster.elemental_weakness else ''}
                            {f'<div style="font-size: 8px; color: #64B5F6; margin-top: 1px;">{", ".join(gs.active_monster.elemental_strength)}</div>' if gs.active_monster.elemental_strength else ''}
                    <div id="monster_init_dice" style="position:absolute;right:100px;top:50%;transform:translateY(-50%) scale(1.55);transform-origin:right center;width:58px;height:44px;z-index:5;"></div><div id="monster_dice" style="position:absolute;right:4px;top:50%;transform:translateY(-50%) scale(1.3);transform-origin:right center;width:68px;height:52px;display:flex;gap:4px;"><div id="monster_def_dice" style="position:relative;width:32px;height:52px;"></div><div id="monster_atk_dice" style="position:relative;width:32px;height:52px;"></div></div>
                </div>
                    </div>
                    
                </div>
                """

            # Build player display name with title from get_player_title function
            player_title = get_player_title(gs.player_character)
            player_display = f"{gs.player_character.name} the {player_title}"
            
            # Compact Player Combat Info
            player_sprite_html_combat = generate_player_sprite_html(
                getattr(gs.player_character, 'race', 'human'),
                getattr(gs.player_character, 'gender', 'male'),
                getattr(gs.player_character, 'equipped_armor', None)
            )
            player_combat_html = f"""
                <div id="player_panel" style="position:relative; padding: 3px; border-radius: 3px; border: 2px solid #666;{low_hp_pulse_style}">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:2px;">
                        <div style="flex-shrink:0;">{player_sprite_html_combat}</div>
                        <div>
                            <div style="color: #4CAF50; font-weight: bold; font-size: 12px; margin-bottom: 2px;"> {player_display}</div>
                            <div style="font-size: 9px; margin-bottom: 1px;"><span class="player-hp-bar">{health_bar(_p_display_hp, gs.player_character.max_health, width=10)}</span></div>
                            <div style="font-size: 9px; margin-bottom: 2px;">{mana_bar(gs.player_character.mana, gs.player_character.max_mana, width=10)}</div>
                            <div style="font-size: 8px;">A:{gs.player_character.attack} D:{gs.player_character.defense}</div>
                            {f'<div style="font-size: 8px; color: #64B5F6; margin-top: 2px;"> {", ".join(gs.player_character.elemental_strengths)}</div>' if gs.player_character.elemental_strengths else ''}
                            {f'<div style="font-size: 8px; color: #FFB74D; margin-top: 1px;"> {", ".join(gs.player_character.elemental_weaknesses)}</div>' if gs.player_character.elemental_weaknesses else ''}
                            {f'<div style="font-size: 8px; color: #FDD835; margin-top: 1px;">{", ".join(gs.player_character.status_effects.keys())}</div>' if gs.player_character.status_effects else ''}
                    <div id="player_init_dice" style="position:absolute;right:100px;top:50%;transform:translateY(-50%) scale(1.55);transform-origin:right center;width:58px;height:44px;z-index:5;"></div><div id="player_dice" style="position:absolute;right:4px;top:50%;transform:translateY(-50%) scale(1.3);transform-origin:right center;width:68px;height:52px;display:flex;gap:4px;"><div id="player_atk_dice" style="position:relative;width:32px;height:52px;"></div><div id="player_def_dice" style="position:relative;width:32px;height:52px;"></div></div>
                </div>
                    </div>
                    
                </div>
                """

            # Combat layout: Map | Combat Info | (empty space for consistency)
            # Generate combat commands based on spell capability
            can_cast = can_cast_spells(gs.player_character)
            combat_commands = "a = attack | f = flee | i = inventory"
            if can_cast:
                combat_commands += " | c = cast spell"

            # Channeling indicator — shown when player is mid-channel
            channeling_html = ""
            if gs.spell_charging:
                ch = gs.spell_charging
                spell_name = ch['spell'].name
                turns_left = ch['turns_remaining']
                total_turns = ch['total_turns']
                # Progress bar: filled segments for completed turns
                filled = total_turns - turns_left
                bar_segments = ''.join(
                    f'<span style="color:#E040FB;">{"*" if i < filled else "."}</span>'
                    for i in range(total_turns)
                )
                channeling_html = f"""
                <div style="padding: 6px; border: 2px solid #E040FB; border-radius: 4px; margin-top: 4px;
                            background: rgba(224,64,251,0.08); animation: channelPulse 1.5s ease-in-out infinite;">
                    <div style="color: #E040FB; font-weight: bold; font-size: 12px; margin-bottom: 2px;">
                        CHANNELING: {spell_name}
                    </div>
                    <div style="font-size: 10px; color: #CE93D8;">
                        [{bar_segments}] {turns_left} turn{'s' if turns_left != 1 else ''} remaining
                    </div>
                    <div style="font-size: 9px; color: #888; margin-top: 2px;">
                        Concentration: d20 + INT/{gs.player_character.intelligence // 4}
                    </div>
                </div>
                """
                combat_commands = "any key = continue channeling"

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}


                    <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                        <div>{grid_html}</div>
                        <div style="width: 100%; max-width: 300px;">
                            {monster_html}
                            {player_combat_html}
                            {channeling_html}
                        </div>
                    </div>
                    {generate_damage_float_js(gs.active_monster.name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal, gs.last_monster_damage_badge, gs.last_player_damage_badge, _spell_element, _spell_level)}
                    {generate_hp_drain_js(gs.active_monster.health, gs.active_monster.max_health, gs.player_character.health, gs.player_character.max_health, gs.last_monster_damage, gs.last_player_damage, gs.last_player_heal, bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}

                </div>
                """
            current_commands_text = combat_commands

            # Schedule monster initiative auto-attack after init dice animation
            if gs.monster_initiative_pending:
                self._schedule_initiative_strike()

        elif gs.prompt_cntl == "combat_victory":
            # VICTORY VIEW - shows combat panels with defeat animation, auto-dismisses

            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            victory_name = gs.victory_monster_name or "Monster"
            monster_sprite_html = generate_monster_sprite_html(victory_name)

            # Show last damage dealt
            dmg_text = ""
            if gs.last_monster_damage > 0:
                dmg_text = f'<div style="font-size: 9px; color: #FF5252; font-weight: bold;">-{gs.last_monster_damage} HP</div>'

            monster_html = f"""
                <div id="monster_panel" style="position:relative; padding: 3px; border-radius: 3px; border: 2px solid #666; margin-bottom: 4px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div id="monster_sprite_box" style="flex-shrink:0; transition: filter 0.6s ease-out;">{monster_sprite_html}</div>
                        <div id="monster_info_box">
                            <div style="color: #F44336; font-weight: bold; font-size: 12px; margin-bottom: 2px;">{victory_name}</div>
                            <div style="font-size: 9px;">{health_bar(0, 1, width=10)}</div>
                            {dmg_text}
                    <div id="monster_init_dice" style="position:absolute;right:100px;top:50%;transform:translateY(-50%) scale(1.55);transform-origin:right center;width:58px;height:44px;z-index:5;"></div><div id="monster_dice" style="position:absolute;right:4px;top:50%;transform:translateY(-50%) scale(1.3);transform-origin:right center;width:68px;height:52px;display:flex;gap:4px;"><div id="monster_def_dice" style="position:relative;width:32px;height:52px;"></div><div id="monster_atk_dice" style="position:relative;width:32px;height:52px;"></div></div>
                </div>
                    </div>
                    
                </div>
                """

            player_title = get_player_title(gs.player_character)
            player_display = f"{gs.player_character.name} the {player_title}"
            player_sprite_html_combat = generate_player_sprite_html(
                getattr(gs.player_character, 'race', 'human'),
                getattr(gs.player_character, 'gender', 'male'),
                getattr(gs.player_character, 'equipped_armor', None)
            )
            player_combat_html = f"""
                <div id="player_panel" style="position:relative; padding: 3px; border-radius: 3px; border: 2px solid #666;{low_hp_pulse_style}">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:2px;">
                        <div style="flex-shrink:0;">{player_sprite_html_combat}</div>
                        <div>
                            <div style="color: #4CAF50; font-weight: bold; font-size: 12px; margin-bottom: 2px;"> {player_display}</div>
                            <div style="font-size: 9px; margin-bottom: 1px;"><span class="player-hp-bar">{health_bar(_p_display_hp, gs.player_character.max_health, width=10)}</span></div>
                            <div style="font-size: 9px; margin-bottom: 2px;">{mana_bar(gs.player_character.mana, gs.player_character.max_mana, width=10)}</div>
                            <div style="font-size: 8px;">A:{gs.player_character.attack} D:{gs.player_character.defense}</div>
                    <div id="player_init_dice" style="position:absolute;right:100px;top:50%;transform:translateY(-50%) scale(1.55);transform-origin:right center;width:58px;height:44px;z-index:5;"></div><div id="player_dice" style="position:absolute;right:4px;top:50%;transform:translateY(-50%) scale(1.3);transform-origin:right center;width:68px;height:52px;display:flex;gap:4px;"><div id="player_atk_dice" style="position:relative;width:32px;height:52px;"></div><div id="player_def_dice" style="position:relative;width:32px;height:52px;"></div></div>
                </div>
                    </div>
                    
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                        <div>{grid_html}</div>
                        <div style="width: 100%; max-width: 300px;">
                            {monster_html}
                            {player_combat_html}
                        </div>
                    </div>
                    {generate_damage_float_js(victory_name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal, gs.last_monster_damage_badge, gs.last_player_damage_badge, _spell_element, _spell_level)}
                    {generate_hp_drain_js(0, 1, gs.player_character.health, gs.player_character.max_health, gs.last_monster_damage, gs.last_player_damage, gs.last_player_heal, bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}
                </div>
                """
            gs.monster_defeated_anim = victory_name
            current_commands_text = ""

            # Schedule auto-dismiss after animations finish (~2.8s)
            self._schedule_victory_dismiss()

        elif gs.prompt_cntl == "flee_direction_mode":
            # FLEE DIRECTION SELECTION VIEW

            # Generate map HTML (same as combat view)
            floor = gs.my_tower.floors[gs.player_character.z]
            highlight_coords = (gs.player_character.y, gs.player_character.x)

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Generate pixel art sprite for the monster
            monster_sprite_html = generate_monster_sprite_html(gs.active_monster.name)
            evo_border_color, evo_tier_label = get_evolution_tier_style(gs.active_monster)

            # Monster info (still there, but you're fleeing)
            evo_border_style = f"border: 2px solid {evo_border_color};" if evo_border_color else "border: 2px solid #666;"
            evo_name_color = evo_border_color if evo_border_color else "#F44336"
            monster_html = f"""
                <div id="monster_panel" style="position:relative; padding: 4px; border-radius: 4px; {evo_border_style} margin-bottom: 5px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{monster_sprite_html}</div>
                        <div>
                            <div style="color: {evo_name_color}; font-weight: bold; font-size: 15px; margin-bottom: 4px;">Fleeing from {gs.active_monster.name} {evo_tier_label}</div>
                            <div style="font-size: 12px; margin-bottom: 3px;">Level {gs.active_monster.level}</div>
                            <div style="font-size: 12px;">{health_bar(gs.active_monster.health, gs.active_monster.max_health, width=15)}</div>
                    <div id="monster_init_dice" style="position:absolute;right:100px;top:50%;transform:translateY(-50%) scale(1.55);transform-origin:right center;width:58px;height:44px;z-index:5;"></div><div id="monster_dice" style="position:absolute;right:4px;top:50%;transform:translateY(-50%) scale(1.3);transform-origin:right center;width:68px;height:52px;display:flex;gap:4px;"><div id="monster_def_dice" style="position:relative;width:32px;height:52px;"></div><div id="monster_atk_dice" style="position:relative;width:32px;height:52px;"></div></div>
                </div>
                    </div>
                    
                </div>
                """

            # Player info
            player_sprite_html_combat = generate_player_sprite_html(
                getattr(gs.player_character, 'race', 'human'),
                getattr(gs.player_character, 'gender', 'male'),
                getattr(gs.player_character, 'equipped_armor', None)
            )
            player_combat_html = f"""
                <div id="player_panel" style="position:relative; padding: 4px; border-radius: 4px; border: 2px solid #666;{low_hp_pulse_style}">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{player_sprite_html_combat}</div>
                        <div>
                            <div style="color: #4CAF50; font-weight: bold; font-size: 15px; margin-bottom: 4px;"> {gs.player_character.name}</div>
                            <div style="font-size: 12px; margin-bottom: 2px;"><span class="player-hp-bar-wide">{health_bar(_p_display_hp, gs.player_character.max_health, width=15)}</span></div>
                            <div style="font-size: 12px; margin-bottom: 4px;">{mana_bar(gs.player_character.mana, gs.player_character.max_mana, width=15)}</div>
                            <div style="font-size: 12px; color: #FFD700;">Escaped combat!</div>
                    <div id="player_init_dice" style="position:absolute;right:100px;top:50%;transform:translateY(-50%) scale(1.55);transform-origin:right center;width:58px;height:44px;z-index:5;"></div><div id="player_dice" style="position:absolute;right:4px;top:50%;transform:translateY(-50%) scale(1.3);transform-origin:right center;width:68px;height:52px;display:flex;gap:4px;"><div id="player_atk_dice" style="position:relative;width:32px;height:52px;"></div><div id="player_def_dice" style="position:relative;width:32px;height:52px;"></div></div>
                </div>
                    </div>
                    
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}


                    <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                        <div>{grid_html}</div>
                        <div style="width: 100%; max-width: 300px;">
                            {monster_html}
                            {player_combat_html}
                        </div>
                    </div>

                    {generate_damage_float_js(gs.active_monster.name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal, gs.last_monster_damage_badge, gs.last_player_damage_badge, _spell_element, _spell_level)}
                    {generate_hp_drain_js(gs.active_monster.health, gs.active_monster.max_health, gs.player_character.health, gs.player_character.max_health, gs.last_monster_damage, gs.last_player_damage, gs.last_player_heal, bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}

                </div>
                """
            current_commands_text = "n/s/e/w = flee direction | c = cancel"

        elif gs.prompt_cntl == "foresight_direction_mode":
            # FORESIGHT DIRECTION VIEW (similar to flee but for scroll)

            # Generate map HTML (reuse existing map generation code)
            floor = gs.my_tower.floors[gs.player_character.z]
            highlight_coords = (gs.player_character.y, gs.player_character.x)

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Scroll info panel
            scroll_html = f"""
                <div style="padding: 10px; border-radius: 4px; border: 2px solid #E040FB; margin-bottom: 5px;">
                    <div style="color: #E040FB; font-weight: bold; font-size: 15px; margin-bottom: 6px;"> Scroll of Foresight</div>
                    <div style="font-size: 12px; color: #DDD; margin-bottom: 8px;">
                        Ancient runes swirl on the parchment, ready to reveal the path ahead.
                    </div>
                    <div style="font-size: 12px; color: #FFD700; padding: 6px; border-radius: 3px;">
                         This scroll will reveal 3 columns or rows in your chosen direction, showing all rooms from here to the edge of the map.
                    </div>
                </div>
                """

            # Player info
            player_info_html = f"""
                <div style="padding: 4px; border-radius: 4px; border: 2px solid #4CAF50;">
                    <div style="color: #4CAF50; font-weight: bold; font-size: 15px; margin-bottom: 4px;"> {gs.player_character.name}</div>
                    <div style="font-size: 12px; margin-bottom: 2px;"><span class="player-hp-bar-wide">{health_bar(_p_display_hp, gs.player_character.max_health, width=15)}</span></div>
                    <div style="font-size: 12px; color: #DDD;">Position: ({gs.player_character.x}, {gs.player_character.y})</div>
                    <div style="font-size: 12px; color: #DDD;">Floor: {gs.player_character.z + 1}</div>
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                        <div>{grid_html}</div>
                        <div style="width: 100%; max-width: 300px;">
                            {scroll_html}
                            {player_info_html}
                        </div>
                    </div>

                    <div style="margin-top: 8px; font-size: 12px; padding: 10px; border-radius: 3px; border: 2px solid #E040FB;">
                        <b style="color: #E040FB;">Choose your direction of sight:</b><br>
                        <div style="margin-top: 6px; color: #DDD;">
                            <b>n</b> = North (reveal 3 columns upward)<br>
                            <b>s</b> = South (reveal 3 columns downward)<br>
                            <b>e</b> = East (reveal 3 rows rightward)<br>
                            <b>w</b> = West (reveal 3 rows leftward)<br>
                            <b>c</b> = Cancel (keep the scroll)
                        </div>
                    </div>
                </div>
                """
            current_commands_text = "n/s/e/w = direction | c = cancel"

        elif gs.prompt_cntl == "chest_mode":
            # CHEST VIEW - Simplified 2 columns: Map | Chest Info

            # Check for lantern
            has_lantern = False
            lantern_fuel = 0
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    lantern_fuel = item.fuel_amount
                    break

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            highlight_coords = (gs.player_character.y, gs.player_character.x)

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Determine chest variant for sprite
            current_floor_c = gs.my_tower.floors[gs.player_character.z]
            room_c = current_floor_c.grid[gs.player_character.y][gs.player_character.x]
            chest_variant = 'legendary' if room_c.properties.get('is_legendary') else None
            chest_sprite = generate_room_sprite_html('C', variant=chest_variant)

            # Chest info box - simple and clean
            chest_html = f"""
               <div style="
                            border: 2px solid #555;
                            border-radius: 3px;
                            padding: 12px;
                            max-height: 300px;
                            overflow-y: auto;
                            ">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{chest_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.4;">
                             An ornate chest sits before you, its lock broken and inviting. What treasures might it hold?
                        </div>
                    </div>
                    
                    <div style="padding-top: 10px; border-top: 1px solid #555;">
                        <div style="color: #FFD700; font-size: 12px; font-weight: bold; margin-bottom: 4px;"> Chest Stats</div>
                        <div style="color: #DDD; font-size: 12px; margin: 3px 0;">Chests Opened: {gs.game_stats.get('chests_opened', 0)}</div>
                    </div>
                    
                    <div style="padding: 6px; margin-top: 10px; border-radius: 3px;">
                        <div style="color: #FFD700; font-size: 12px; font-weight: bold;"> Ready to open?</div>
                        <div style="color: #DDD; font-size: 9px; margin-top: 2px; font-style: italic;">Press 'o' to discover what's inside...</div>
                    </div>
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>

                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{chest_html}</div>
                    </div>
</div>
                """
            # Build chest commands with lantern if available
            current_commands_text = "o = open | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "altar_mode":
            # ALTAR VIEW - Vendor-style full interaction (no map)

            gods = gs.active_altar_state.get('gods', {})
            blessed_id = gs.active_altar_state.get('blessed_id', 1)
            blessed_god = gods.get(blessed_id, {})

            # Get hunch god info for display
            current_floor = gs.my_tower.floors[gs.player_character.z]
            room = current_floor.grid[gs.player_character.y][gs.player_character.x]
            hunch_god_id = room.properties.get('hunch_god_id', blessed_id)
            hunch_god = gods.get(hunch_god_id, blessed_god)

            # Generic spirit flavor text - no hints about which god
            import random as _rnd
            spirit_whispers = [
                "...place your offering upon the stone... and pray...",
                "...the altar hums with ancient power...",
                "...something watches... waiting for a gift...",
                "...do you dare part with your possessions, mortal?...",
                "...the air grows thick with divine presence...",
                "...choose wisely... or do not choose at all...",
                "...a faint pulse echoes from deep within the stone...",
                "...the gods are always hungry...",
            ]
            whisper = _rnd.choice(spirit_whispers)

            # Build sacrificeable inventory list (no Runes/Shards)
            sorted_items = get_sorted_inventory(gs.player_character.inventory)
            sacrificeable = [it for it in sorted_items if not isinstance(it, (Rune, Shard))]

            inv_html = ""
            if not sacrificeable:
                inv_html = "<div style='color:#888; font-size:12px;'>(Nothing to sacrifice)</div>"
            else:
                for i, item in enumerate(sacrificeable):
                    item_str = format_item_for_display(item, gs.player_character, show_price=False)
                    sealed_tag = " <span style='color:#E040FB;'>[SEALED]</span>" if getattr(item, 'is_sealed', False) else ""
                    buc_tag = ""
                    if getattr(item, 'buc_known', False):
                        if item.buc_status == 'blessed':
                            buc_tag = " <span style='color:#FFD700;'>[BLESSED]</span>"
                        elif item.buc_status == 'cursed':
                            buc_tag = " <span style='color:#F44336;'>[CURSED]</span>"
                    inv_html += f"<div style='margin:2px 0; font-size:12px;'><b>{i+1}.</b> {item_str}{sealed_tag}{buc_tag}</div>"

            devotion_hint = ""
            if not gs.runes_obtained.get('devotion', False) and gs.player_character is not None:
                gold_req = gs.rune_progress_reqs.get('gold_obtained', 500)
                hp_req = gs.rune_progress_reqs.get('player_health_obtained', 50)
                if gs.player_character.gold >= gold_req and gs.player_character.health >= hp_req:
                    devotion_hint = (
                        "<div style='color:#FFD700; font-size:11px; margin-top:5px; border-top:1px solid #555; padding-top:4px;'>"
                        "[9] Offer " + str(gold_req) + " gold + " + str(hp_req) + " HP to all gods - Rune of Devotion"
                        "</div>"
                    )

            altar_sprite = generate_room_sprite_html('A')

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; display: flex; flex-direction: column; max-height: 100%; overflow: hidden;">
                    {achievement_notifications}
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{altar_sprite}</div>
                        <div>
                            <div style="font-size: 16px; font-weight: bold; color: {hunch_god.get('color','#DDD')};">
                                {hunch_god.get('symbol','?')} {hunch_god.get('name','Unknown')}
                            </div>
                            <div style="font-size: 10px; color: #AAA;">{hunch_god.get('title','')}</div>
                        </div>
                    </div>
                    {player_stats_html}
                    <div style="margin-bottom: 5px; color: {hunch_god.get('color','#9370DB')}; font-style: italic; font-size: 10px;">
                        A spirit voice whispers: "{whisper}"
                    </div>
                    <div style="color: #AAA; font-size: 9px; margin-bottom: 5px;">
                        INT {gs.player_character.intelligence} intuition | Hungers for: <b style="color:#FFD700;">{hunch_god.get('item_label','?')}</b>
                        | <span style="color:#888;">Right offering = reward | Wrong = displeasure</span>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 5px; flex: 1; min-height: 0; overflow: hidden;">
                        <div style="border: 1px solid #555; padding: 3px;">
                            <h3 style='margin: 0 0 5px 0; color: #DDD;'>Sacrifice an Item</h3>
                            <div style='overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px; max-height: 400px;'>
                                {inv_html}
                            </div>
                            {devotion_hint}
                        </div>
                    </div>
                </div>
                """
            if gs.altar_action:
                current_commands_text = "# = sacrifice item | b = back"
            else:
                current_commands_text = "s = sacrifice | d = detect | b = bless | u = purify | i = inventory | x = exit"

        elif gs.prompt_cntl == "pool_mode":
            # POOL VIEW - Simplified: Map | Pool Info
            
            # Check for lantern
            has_lantern = False
            lantern_fuel = 0
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    lantern_fuel = item.fuel_amount
                    break

            current_floor = gs.my_tower.floors[gs.player_character.z]
            room = current_floor.grid[gs.player_character.y][gs.player_character.x]
            pool_info = room.properties.get('pool_info', {})

            pool_name = pool_info.get('name', 'Mysterious Pool')
            pool_symbol = pool_info.get('symbol', '')
            pool_color = pool_info.get('color', '#00CED1')
            pool_desc = pool_info.get('description', 'A basin of water.')
            unknown_pool_desc = "An unknown but powerful basin of water lies here."

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            highlight_coords = (gs.player_character.y, gs.player_character.x)

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Pool sprite - check for ancient waters variant
            pool_variant = 'ancient' if room.properties.get('is_ancient') else None
            pool_sprite = generate_room_sprite_html('P', variant=pool_variant)

            # Pool info box - simple and clean
            pool_html = f"""
                <div style="
                            border: 2px solid #555;
                            border-radius: 3px;
                            padding: 12px;
                            max-height: 300px;
                            overflow-y: auto;
                            ">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{pool_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.4;">
                             A basin of strange liquid fills this chamber. The water's surface ripples with otherworldly energy. Its true nature remains hidden until tasted.
                        </div>
                    </div>
                """

            # Add insight if player has analyzed it
            if 'insight_shown' in room.properties:
                insight_text = room.properties.get('insight_text', '')
                insight_color = room.properties.get('insight_color', '#DDD')
                pool_html += f"""
                    <div style="margin-top: 8px; padding: 6px; border-left: 3px solid {insight_color}; border-radius: 3px;">
                        <div style="color: {insight_color}; font-size: 12px;"> Intuition (INT {gs.player_character.intelligence})</div>
                        <div style="color: #DDD; font-size: 12px; margin-top: 2px;">{insight_text}</div>
                    </div>
                    """

            # Show active status effects if any (important for pools since they can cause effects)
            if gs.player_character.status_effects:
                pool_html += '<div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #555;">'
                pool_html += '<div style="color: #FFD700; font-size: 12px; font-weight: bold; margin-bottom: 3px;"> Active Effects</div>'
                for effect_name, effect in gs.player_character.status_effects.items():
                    pool_html += f'<div style="color: #DDD; font-size: 12px; margin: 2px 0;"> {effect_name} ({effect.duration} turns)</div>'
                pool_html += '</div>'

            # Decision prompt
            pool_html += '''
                <div style="padding: 6px; margin-top: 10px; border-radius: 3px;">
                    <div style="color: #00CED1; font-size: 12px; font-weight: bold;"> Drink from the basin?</div>
                    <div style="color: #DDD; font-size: 9px; margin-top: 2px; font-style: italic;">Effects unknown until you drink...</div>
                </div>
                '''

            pool_html += '</div>'

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{pool_html}</div>
                    </div>
</div>
                """
            # Build pool commands with lantern if available
            current_commands_text = "dr = drink | i = inventory"
            if has_lantern:
                current_commands_text += f" | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "warp_mode":
            # WARP MODE - 2 columns: Map | Warp Info
            
            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            
            # Check if this is a vault warp
            room = floor.grid[gs.player_character.y][gs.player_character.x]
            is_vault_warp = room.properties.get('vault_warp', False)
            
            vault_warning = ""
            if is_vault_warp:
                vault_warning = """
                    <div style="padding: 6px; margin-top: 8px; border-radius: 3px; border-left: 3px solid #F44336;">
                        <div style="color: #F44336; font-size: 12px; font-weight: bold;">Warning!</div>
                        <div style="color: #DDD; font-size: 9px; margin-top: 2px;">This portal pulses with vault energy. You may be drawn to a sealed chamber with no escape!</div>
                    </div>
                """
            
            # Warp info box
            warp_sprite = generate_room_sprite_html('W')
            warp_html = f"""
                <div style="
                            border: 2px solid #555;
                            border-radius: 3px;
                            padding: 12px;
                            max-height: 300px;
                            overflow-y: auto;
                            ">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{warp_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.4;">
                             A swirling portal of magical energy appears before you! Reality bends and warps around its edges. You feel an irresistible pull drawing you toward the depths...
                        </div>
                    </div>
                    {vault_warning}
                    <div style="padding: 6px; margin-top: 10px; border-radius: 3px;">
                        <div style="color: #E040FB; font-size: 12px; font-weight: bold;">What do you do?</div>
                        <div style="color: #4CAF50; font-size: 9px; margin-top: 4px;"><b>Y</b> = Try to resist the warp (INT check)</div>
                        <div style="color: #F44336; font-size: 9px; margin-top: 2px;"><b>N</b> = Enter the portal willingly</div>
                    </div>
                </div>
                """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{warp_html}</div>
                    </div>

                    <div style="margin-top: 8px; padding: 4px; border-radius: 3px; font-size: 12px;">
                        <b>y = resist | n = enter</b>
                    </div>
                </div>
                """
            current_commands_text = "y = resist | n = enter"

        elif gs.prompt_cntl == "stairs_up_mode":
            # STAIRS UP MODE - 2 columns: Map | Stairs Info
            
            # Check for lantern
            has_lantern = False
            lantern_fuel = 0
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    lantern_fuel = item.fuel_amount
                    break
            
            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            
            # Stairs info box
            stairs_sprite = generate_room_sprite_html('U')
            stairs_html = f"""
                <div style="
                            border: 2px solid #555;
                            border-radius: 3px;
                            padding: 12px;
                            max-height: 300px;
                            overflow-y: auto;
                            ">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{stairs_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.4;">
                             Stone stairs spiral upward, leading back toward the surface. The air feels lighter here, as if escape is within reach.
                        </div>
                    </div>
                    
                    <div style="padding-top: 10px; border-top: 1px solid #555;">
                        <div style="color: #4CAF50; font-size: 12px; font-weight: bold; margin-bottom: 4px;"> Current Depth</div>
                        <div style="color: #DDD; font-size: 12px; margin: 3px 0;">Floor: {gs.player_character.z + 1}</div>
                    </div>
                    
                    <div style="padding: 6px; margin-top: 10px; border-radius: 3px; border-left: 3px solid #555;">
                        <div style="color: #4CAF50; font-size: 12px; font-weight: bold;"> Ascend the stairs?</div>
                        <div style="color: #DDD; font-size: 9px; margin-top: 2px; font-style: italic;">Press 'u' to climb upward...</div>
                    </div>
                </div>
                """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{stairs_html}</div>
                    </div>
</div>
                """
            # Build stairs up commands with lantern if available
            current_commands_text = "u = up | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "stairs_down_mode":
            # STAIRS DOWN MODE - 2 columns: Map | Stairs Info
            
            # Check for lantern
            has_lantern = False
            lantern_fuel = 0
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    lantern_fuel = item.fuel_amount
                    break
            
            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            
            # Stairs info box
            stairs_down_sprite = generate_room_sprite_html('D')
            stairs_html = f"""
                <div style="
                            border: 2px solid #555;
                            border-radius: 3px;
                            padding: 12px;
                            max-height: 300px;
                            overflow-y: auto;
                            ">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{stairs_down_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.4;">
                             Dark stairs descend into the unknown depths below. The air grows colder and heavier as darkness beckons from the depths.
                        </div>
                    </div>
                    
                    <div style="padding-top: 10px; border-top: 1px solid #555;">
                        <div style="color: #F44336; font-size: 12px; font-weight: bold; margin-bottom: 4px;"> Current Depth</div>
                        <div style="color: #DDD; font-size: 12px; margin: 3px 0;">Floor: {gs.player_character.z + 1}</div>
                        <div style="color: #FFA500; font-size: 9px; margin-top: 4px;"> Danger increases with depth</div>
                    </div>
                    
                    <div style="padding: 6px; margin-top: 10px; border-radius: 3px; border-left: 3px solid #555;">
                        <div style="color: #F44336; font-size: 12px; font-weight: bold;"> Descend deeper?</div>
                        <div style="color: #DDD; font-size: 9px; margin-top: 2px; font-style: italic;">Press 'd' to venture into the darkness...</div>
                    </div>
                </div>
                """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{stairs_html}</div>
                    </div>
</div>
                """
            # Build stairs down commands with lantern if available
            current_commands_text = "d = down | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "library_mode":
            # LIBRARY VIEW - 2 columns: Map | Library Info

            # Check for lantern
            has_lantern = False
            lantern_fuel = 0
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    lantern_fuel = item.fuel_amount
                    break

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            highlight_coords = (gs.player_character.y, gs.player_character.x)

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Get library info from room
            current_room = floor.grid[gs.player_character.y][gs.player_character.x]
            coords_key = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            has_searched = coords_key in gs.searched_libraries

            # Library sprite - check for codex variant
            lib_variant = 'codex' if current_room.properties.get('has_codex') else None
            library_sprite = generate_room_sprite_html('L', variant=lib_variant)

            # Library info box - simple and clean
            if has_searched:
                lib_status = '<div style="color: #888; font-size: 12px; margin-top: 4px;">You have already rummaged through this library.</div>'
            else:
                lib_status = '<div style="color: #DAA520; font-size: 12px; margin-top: 4px;">Hidden knowledge awaits discovery...</div>'

            library_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{library_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.4;">
                             Towering shelves filled with dusty tomes surround you. The air is thick with the scent of old parchment and forgotten knowledge.
                        </div>
                    </div>
                    {lib_status}
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>

                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{library_html}</div>
                    </div>
</div>
                """
            # Build library commands with lantern if available
            current_commands_text = "r = rummage for books | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "dungeon_mode":
            # DUNGEON VIEW - Locked dungeon with key
            
            # Check for lantern
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break
            
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            coords = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            has_key = coords in gs.dungeon_keys
            
            # Build action prompt based on key status
            if has_key:
                action_html = '<div style="padding: 6px; margin-top: 10px; border-radius: 3px;"><div style="color: #4CAF50; font-size: 12px; font-weight: bold;">Unlock the dungeon?</div><div style="color: #DDD; font-size: 12px; margin-top: 2px;">Press u to use your key...</div></div>'
            else:
                action_html = '<div style="padding: 6px; margin-top: 10px; border-radius: 3px;"><div style="color: #FF6B6B; font-size: 12px; font-weight: bold;">Find the key!</div><div style="color: #DDD; font-size: 9px; margin-top: 2px;">Defeat monsters on this floor to find it...</div></div>'

            # Check if master dungeon variant
            room_d = floor.grid[gs.player_character.y][gs.player_character.x]
            dng_variant = 'master' if room_d.properties.get('is_master') else None
            dungeon_sprite = generate_room_sprite_html('N', variant=dng_variant)

            dungeon_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                        <div style="flex-shrink:0;">{dungeon_sprite}</div>
                        <div style="color: #DDD; font-size: 12px;">
                            A heavy iron door bars your way. Ancient runes glow faintly on its surface.
                        </div>
                    </div>
                    {'<div style="padding: 6px; margin-bottom: 8px; border-radius: 3px;"><div style="color: #4CAF50; font-size: 12px;">[LOCKED] Locked</div><div style="color: #DDD; font-size: 9px; margin-top: 2px;">A monster on this floor holds the key...</div></div>'}
                    {action_html}
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{dungeon_html}</div>
                    </div>
                </div>
            """
            # Only show unlock command if player has key
            if has_key:
                current_commands_text = "u = unlock | i = inventory"
            else:
                current_commands_text = "i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "dungeon_unlocked_mode":
            # DUNGEON VIEW - Unlocked, ready to loot
            
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break
            
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            coords = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            already_looted = coords in gs.looted_dungeons
            
            dungeon_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="color: #DDD; font-size: 12px; margin-bottom: 8px;">
                        The iron door stands open. {'The chamber has been emptied.' if already_looted else 'Treasures glint in the darkness within.'}
                    </div>
                    {('<div style="padding: 6px; margin-bottom: 8px; border-radius: 3px; border-left: 3px solid #888;"><div style="color: #888; font-size: 12px;">Already Looted</div></div>' if already_looted else '<div style="padding: 6px; margin-top: 10px; border-radius: 3px; border-left: 3px solid #555;"><div style="color: #4CAF50; font-size: 12px; font-weight: bold;">Claim your reward?</div><div style="color: #DDD; font-size: 9px; margin-top: 2px;">Press &apos;l&apos; to loot the dungeon...</div></div>')}
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{dungeon_html}</div>
                    </div>
                </div>
            """
            if not already_looted:
                current_commands_text = "r = rummage | i = inventory"
            else:
                current_commands_text = "i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern" if not already_looted else " | a = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "tomb_mode":
            # TOMB VIEW - Show log content with choices
            
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break
            
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            coords = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            already_looted = coords in gs.looted_tombs
            
            # Get tomb variant
            room_t = floor.grid[gs.player_character.y][gs.player_character.x]
            tomb_variant = 'cursed' if room_t.properties.get('is_cursed') else None
            tomb_sprite = generate_room_sprite_html('T', variant=tomb_variant)

            # Build tomb status text
            if already_looted:
                tomb_status = '<div style="color: #888; font-size: 12px; margin-top: 4px;">This tomb has already been raided.</div>'
            else:
                tomb_status = '<div style="color: #C8A96E; font-size: 12px; margin-top: 4px;">You could <b>raid</b> it for treasure... or <b>pay respects</b> to the dead.</div>'

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%; padding: 8px; border: 1px solid #666; border-radius: 3px;">
                            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                                <div style="flex-shrink:0;">{tomb_sprite}</div>
                                <div style="color: #DDD; font-size: 12px;">An ancient tomb lies before you, its stone lid cracked with age.</div>
                            </div>
                            {tomb_status}
                        </div>
                    </div>
                </div>
            """
            if not already_looted:
                current_commands_text = "r = raid | p = pay respects | i = inventory"
            else:
                current_commands_text = "i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "garden_mode":
            # MAGICAL GARDEN VIEW - Harvest ingredients
            
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break
            
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            coords = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            already_harvested = coords in gs.harvested_gardens
            
            garden_sprite = generate_room_sprite_html('G')

            garden_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                        <div style="flex-shrink:0;">{garden_sprite}</div>
                        <div style="color: #DDD; font-size: 12px;">
                            {'The garden lies barren, its magical plants already harvested.' if already_harvested else 'A lush magical garden blooms with glowing flowers, shimmering herbs, and crystalline plants. The air hums with arcane energy.'}
                        </div>
                    </div>
                    {('<div style="padding: 6px; margin-bottom: 8px; border-radius: 3px;"><div style="color: #888; font-size: 12px;">Already Harvested</div></div>' if already_harvested else '<div style="padding: 6px; margin-top: 10px; border-radius: 3px;"><div style="color: #66BB6A; font-size: 12px; font-weight: bold;">Harvest ingredients?</div><div style="color: #DDD; font-size: 9px; margin-top: 2px;">Press &apos;h&apos; to gather potion components...</div></div>')}
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{garden_html}</div>
                    </div>
                </div>
            """
            if not already_harvested:
                current_commands_text = "h = harvest | i = inventory"
            else:
                current_commands_text = "i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "fey_garden_mode":
            # FEY GARDEN VIEW - Special UI
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Get turns remaining
            turns_left = gs.ephemeral_gardens.get(gs.player_character.z, {}).get('turns_remaining', '?')

            fey_sprite = generate_room_sprite_html('G', variant='fey_garden')

            fey_html = f"""
                        <div style="border: 2px solid #555; border-radius: 5px; padding: 15px;">
                            <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px; border-bottom: 1px solid #555; padding-bottom: 10px;">
                                <div style="flex-shrink:0;">{fey_sprite}</div>
                                <span style="font-size: 18px; font-weight: bold; color: #E1BEE7; text-shadow: 0 0 5px #E040FB;">* FEY GARDEN *</span>
                            </div>

                            <div style="color: #E1BEE7; font-size: 12px; margin-bottom: 12px; font-style: italic; text-align: center;">
                                "The air shimmers with magic from the realm between worlds..."
                            </div>

                            <div style="padding: 10px; border-radius: 4px; border-left: 3px solid #555; margin-bottom: 15px;">
                                <div style="color: #F3E5F5; font-size: 12px;">
                                    Exotic flora blooms here that cannot be found in the mortal realm.
                                    <br><br>
                                    <span style="color: #FF4081;">This garden will vanish in <strong>{turns_left}</strong> turns!</span>
                                </div>
                            </div>

                            <div style="display: flex; gap: 10px; justify-content: center;">
                                <div style="padding: 8px 15px; border-radius: 4px; border: 1px solid #555; color: #FFF; font-weight: bold; font-size: 12px;">
                                    [ H ] Harvest Ingredients
                                </div>
                            </div>
                            <div style="text-align: center; margin-top: 8px; font-size: 12px; color: #B39DDB;">
                                (Move N/S/E/W to leave)
                            </div>
                        </div>
                    """

            # Combine into main layout (similar to other modes)
            html_code = f"""
                        <div style="font-family: monospace; font-size: 12px;">
                            {achievement_notifications}
                            <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                            {player_stats_html}
                            <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                                <div>{grid_html}</div>
                                <div class="room-panel" style="width: 100%;">{fey_html}</div>
                            </div>
                        </div>
                    """
            current_commands_text = "h = harvest | i = inventory | n/s/e/w = move"

        elif gs.prompt_cntl == "oracle_mode":
            # ORACLE VIEW - Mystical mirror with quest hints
            
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break
            
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            
            oracle_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                        <div style="flex-shrink:0;">{generate_room_sprite_html('O')}</div>
                        <div style="color: #DDD; font-size: 12px;">
                            A mystical mirror stands before you, its silvered surface rippling with arcane energy. Swirling mists dance within, showing glimpses of your destiny.
                        </div>
                    </div>
                    
                    <div style="padding: 6px; margin-top: 10px; border-radius: 3px; border-left: 3px solid #555;">
                        <div style="color: #BA68C8; font-size: 12px; font-weight: bold;">Gaze into the Oracle?</div>
                        <div style="color: #DDD; font-size: 9px; margin-top: 2px;">Press 'g' to seek guidance on your quest...</div>
                    </div>
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{oracle_html}</div>
                    </div>
                </div>
            """
            current_commands_text = "g = gaze | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "blacksmith_mode":
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            room = floor.grid[gs.player_character.y][gs.player_character.x]
            weapon = gs.player_character.equipped_weapon
            armor  = gs.player_character.equipped_armor
            floor_level = gs.player_character.z
            reforge_cost = 200 + floor_level * 10

            def item_dur_str(item):
                if not item: return "none"
                pct = int(item.durability / item.max_durability * 100) if item.max_durability > 0 else 100
                col = "#4CAF50" if pct > 60 else ("#FF9800" if pct > 25 else "#F44336")
                return f"<span style='color:{col}'>{item.durability}/{item.max_durability} ({pct}%)</span>"

            w_repair_cost = max(1, int(get_repair_cost(weapon) * 0.80)) if weapon else 0
            a_repair_cost = max(1, int(get_repair_cost(armor)  * 0.80)) if armor  else 0
            rfw_done = room.properties.get('reforged_weapon', False)
            rfa_done = room.properties.get('reforged_armor',  False)

            smith_sprite = generate_room_sprite_html('B')
            smith_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                        <div style="flex-shrink:0;">{smith_sprite}</div>
                        <div style="color: #CCC; font-size: 13px; font-weight: bold; margin-bottom: 4px;">[B] BLACKSMITH</div>
                    </div>
                    <div style="color: #DDD; font-size: 12px; margin-bottom: 10px; font-style: italic;">
                        "I can fix what's broken and roll the dice on what's dull."
                    </div>
                    <div style="color: #CCC; font-size: 12px; margin-bottom: 8px;">
                        Weapon: {weapon.name if weapon else 'none'} -- Durability: {item_dur_str(weapon)}<br>
                        Armor:  {armor.name  if armor  else 'none'} -- Durability: {item_dur_str(armor)}
                    </div>
                    <div style="font-size: 12px; color: #DDD;">
                        <div style="margin-bottom: 4px;">{'<span style="color:#888">[1] Weapon (perfect)</span>' if not weapon or weapon.durability >= weapon.max_durability else f'[1] Repair weapon -- {w_repair_cost}g'}</div>
                        <div style="margin-bottom: 4px;">{'<span style="color:#888">[2] Armor (perfect)</span>'  if not armor  or armor.durability  >= armor.max_durability  else f'[2] Repair armor  -- {a_repair_cost}g'}</div>
                        <div style="margin-bottom: 4px;">{'<span style="color:#888">[3] Reforge weapon (done)</span>' if rfw_done or not weapon else f'[3] Reforge weapon -- {reforge_cost}g (gamble: re-roll base ATK)'}</div>
                        <div>{'<span style="color:#888">[4] Reforge armor (done)</span>'  if rfa_done or not armor  else f'[4] Reforge armor  -- {reforge_cost}g (gamble: re-roll base DEF)'}</div>
                    </div>
                    <div style="color:#888; font-size:11px; margin-top:10px;">Gold: {gs.player_character.gold}g</div>
                </div>
            """
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{smith_html}</div>
                    </div>
                </div>
            """
            current_commands_text = "1=repair weapon | 2=repair armor | 3=reforge weapon | 4=reforge armor | i=inventory | n/s/e/w=move"

        elif gs.prompt_cntl == "shrine_mode":
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            room = floor.grid[gs.player_character.y][gs.player_character.x]
            used = room.properties.get('shrine_used', False)
            shrine_sprite = generate_room_sprite_html('F')

            shrine_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                        <div style="flex-shrink:0;">{shrine_sprite}</div>
                        <div>
                            <div style="color: #CCC; font-size: 13px; font-weight: bold; margin-bottom: 4px;">
                                SHRINE OF THE FALLEN
                            </div>
                            <div style="color: #DDD; font-size: 12px; font-style: italic;">
                                Names scratched into stone. Someone fought hard here.
                            </div>
                        </div>
                    </div>
                    {'<div style="color:#888; font-size:12px;">The shrine lies silent. The spirit has passed on.</div>' if used else '<div style="font-size: 12px; color: #DDD;"><div style="margin-bottom: 4px;">[p] Pray -- 33% blessing / 33% map hint / 33% silence</div><div>[o] Leave offering -- 50g for guaranteed potion or scroll</div></div><div style="color:#888; font-size:11px; margin-top:8px;">Gold: ' + str(gs.player_character.gold) + 'g</div>'}
                </div>
            """
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{shrine_html}</div>
                    </div>
                </div>
            """
            current_commands_text = "p=pray | o=leave offering (50g) | i=inventory | n/s/e/w=move"

        elif gs.prompt_cntl == "alchemist_mode":
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            room = floor.grid[gs.player_character.y][gs.player_character.x]
            uses_left = room.properties.get('alch_uses', 3)
            potions = [item for item in gs.player_character.inventory.items if isinstance(item, Potion)]
            combining = room.properties.get('alch_combining', False)

            potion_list_html = ""
            if combining:
                potion_list_html = "<div style='color:#FF9800; font-size:12px; margin-top:6px;'>Choose two potions -- enter numbers like: 1 2</div>"
                for i, p in enumerate(potions, 1):
                    potion_list_html += f"<div style='color:#DDD; font-size:12px;'>{i}. {p.name}</div>"

            alch_sprite = generate_room_sprite_html('Q')
            alch_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                        <div style="flex-shrink:0;">{alch_sprite}</div>
                        <div style="color: #CCC; font-size: 13px; font-weight: bold; margin-bottom: 4px;">[Q] ALCHEMIST'S LAB</div>
                    </div>
                    <div style="color: #DDD; font-size: 12px; margin-bottom: 8px; font-style: italic;">
                        "Two become one. Results... variable."
                    </div>
                    <div style="color: #CCC; font-size: 12px; margin-bottom: 8px;">
                        Uses remaining: {uses_left} | Potions in pack: {len(potions)}
                    </div>
                    {'<div style="color:#888; font-size:12px;">The apparatus is spent.</div>' if uses_left <= 0 else
                     '<div style="font-size:12px; color:#DDD;">[c] Combine two potions (10% botch chance)</div>'}
                    {potion_list_html}
                </div>
            """
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{alch_html}</div>
                    </div>
                </div>
            """
            current_commands_text = "c=combine potions | i=inventory | n/s/e/w=move"

        elif gs.prompt_cntl == "war_room_mode":
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            room = floor.grid[gs.player_character.y][gs.player_character.x]
            floor_level = gs.player_character.z
            raid_cost = 100 + floor_level * 5
            intel_used = room.properties.get('intel_used', False)
            raid_used  = room.properties.get('raid_used',  False)
            raid_active = floor.properties.get('raid_mode_active', False)
            raid_turns  = floor.properties.get('raid_turns_left', 0)

            raid_status = ""
            if raid_active:
                raid_status = f"<div style='color:#F44336; font-size:12px; font-weight:bold; margin-bottom:6px;'>[RAID MODE ACTIVE -- {raid_turns} turns remaining]</div>"

            war_sprite = generate_room_sprite_html('K')
            war_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                        <div style="flex-shrink:0;">{war_sprite}</div>
                        <div style="color: #CCC; font-size: 13px; font-weight: bold; margin-bottom: 4px;">[K] WAR ROOM</div>
                    </div>
                    <div style="color: #DDD; font-size: 12px; margin-bottom: 8px; font-style: italic;">
                        Maps still pinned to the walls. Someone planned an assault here.
                    </div>
                    {raid_status}
                    <div style="font-size: 12px; color: #DDD;">
                        <div style="margin-bottom: 4px;">{'<span style="color:#888">[1] Intel (already used)</span>' if intel_used else '[1] Intel (free) -- reveal all rooms on next floor'}</div>
                        <div>{'<span style="color:#888">[2] Raid mode (already used)</span>' if raid_used else ('[2] Raid mode -- already active' if raid_active else f'[2] Raid mode -- {raid_cost}g | +50% XP, +25% monster ATK for 10 turns')}</div>
                    </div>
                    <div style="color:#888; font-size:11px; margin-top:10px;">Gold: {gs.player_character.gold}g</div>
                </div>
            """
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{war_html}</div>
                    </div>
                </div>
            """
            current_commands_text = "1=intel | 2=raid mode | i=inventory | n/s/e/w=move"

        elif gs.prompt_cntl == "taxidermist_mode":
            # TAXIDERMIST VIEW
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            room = floor.grid[gs.player_character.y][gs.player_character.x]

            is_bug_tax = room.properties.get('is_bug_taxidermist', False)
            collection_status = get_collection_status(gs.player_character)
            # Filter collections: bug taxidermist shows only bug collections, regular shows only non-bug
            collection_status = [(name, data, pieces, complete) for name, data, pieces, complete in collection_status
                                 if bool(data.get('is_bug')) == is_bug_tax]
            trophies = get_player_trophies(gs.player_character)
            completable = [(name, data) for (name, data, pieces, complete) in collection_status
                           if complete and not room.properties.get(f'completed_{name}')]
            already_done = [name for (name, data, pieces, complete) in collection_status
                            if room.properties.get(f'completed_{name}')]

            # Build collection rows
            rows_html = ""
            for cname, cdata, pieces_have, complete in collection_status:
                done = room.properties.get(f'completed_{cname}')
                have_count = sum(1 for p in cdata['pieces'] if pieces_have.get(p, 0) >= 1)
                total = len(cdata['pieces'])
                if done:
                    status_color = '#888'
                    status_txt = '[COLLECTED]'
                elif complete:
                    status_color = '#4CAF50'
                    status_txt = '[READY]'
                else:
                    status_color = '#FF9800'
                    status_txt = f'{have_count}/{total}'
                pieces_detail = ', '.join(
                    f"<span style='color:{'#4CAF50' if pieces_have.get(p,0)>=1 else '#F44336'}'>{p}</span>"
                    for p in cdata['pieces']
                )
                rows_html += f"""
                    <div style='margin-bottom:6px; padding:5px; border-left:3px solid {status_color};'>
                        <span style='color:{status_color}; font-weight:bold; font-size:12px;'>{cname} {status_txt}</span>
                        <div style='font-size:11px; color:#CCC; margin-top:2px;'>{pieces_detail}</div>
                        <div style='font-size:11px; color:#AAA; margin-top:1px;'>{cdata['reward_name']}: {cdata['reward_desc'][:60]}...</div>
                    </div>"""

            # Completable list with numbers
            complete_html = ""
            for idx, (cname, cdata) in enumerate(completable, 1):
                complete_html += f"<div style='color:#4CAF50; font-size:12px; margin-bottom:2px;'>[{idx}] Turn in {cname} -> {cdata['reward_name']}</div>"
            if not complete_html:
                complete_html = "<div style='color:#888; font-size:12px;'>No collections ready to turn in.</div>"

            trophy_count = sum(getattr(t,'count',1) for t in gs.player_character.inventory.items if isinstance(t, Trophy))
            trophy_val = sum(t.value * getattr(t,'count',1) for t in gs.player_character.inventory.items if isinstance(t, Trophy))

            tax_sprite = generate_room_sprite_html('X')
            tax_title = "BUG TAXIDERMIST" if is_bug_tax else "TAXIDERMIST"
            tax_html = f"""
                <div style='border:2px solid #555; border-radius:3px; padding:12px;'>
                    <div style='display:flex; align-items:center; gap:8px; margin-bottom:6px;'>
                        <div style='flex-shrink:0;'>{tax_sprite}</div>
                        <div style='color:#CCC; font-size:13px; font-weight:bold; margin-bottom:4px;'>{tax_title}</div>
                    </div>
                    <div style='color:#CCC; font-size:11px; font-style:italic; margin-bottom:8px;'>
                        You have {trophy_count} trophy piece(s) worth {trophy_val}g if sold.
                    </div>
                    <div style='margin-bottom:8px;'>{rows_html}</div>
                    <div style='border-top:1px solid #555; padding-top:6px;'>
                        {complete_html}
                    </div>
                    <div style='color:#888; font-size:11px; margin-top:6px;'>
                        s = sell all trophies for gold | i = inventory | x = exit
                    </div>
                </div>"""

            html_code = f"""
                <div style='font-family: monospace; font-size: 12px;'>
                    {achievement_notifications}
                    <div style='font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;'>Wizard's Cavern</div>
                    {player_stats_html}
                    <div style='display: flex; flex-direction: column; align-items: center; gap: 10px;'>
                        <div>{grid_html}</div>
                        <div class="room-panel" style='width: 100%;'>{tax_html}</div>
                    </div>
                </div>"""
            current_commands_text = "#=turn in collection | s=sell trophies | i=inventory | x=exit"

        elif gs.prompt_cntl == "towel_action_mode":
            # TOWEL ACTION VIEW
            
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            
            towel_wetness = ""
            if gs.active_towel_item:
                # Handle both Towel objects and generic Items that are towels
                if hasattr(gs.active_towel_item, '_get_wetness_description'):
                    wetness_desc = gs.active_towel_item._get_wetness_description()
                    towel_wetness = f" ({wetness_desc})"
                elif hasattr(gs.active_towel_item, 'wetness'):
                    wetness = gs.active_towel_item.wetness
                    if wetness == 0:
                        towel_wetness = " (dry)"
                    elif wetness <= 2:
                        towel_wetness = " (moist)"
                    elif wetness <= 4:
                        towel_wetness = " (damp)"
                    elif wetness <= 6:
                        towel_wetness = " (wet)"
                    else:
                        towel_wetness = " (soaking)"
            
            towel_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="color: #CCC; font-weight: bold; font-size: 12px; margin-bottom: 8px;">
                        [TOWEL] Towel{towel_wetness}
                    </div>
                    <div style="color: #DDD; font-size: 12px; margin-bottom: 10px;">
                        What do you want to do with the towel?
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <div style="padding: 6px; border-radius: 3px;">
                            <span style="color: #FFD700;">1.</span> <span style="color: #CCC;">Wear over face (blind yourself - protection from gaze)</span>
                        </div>
                        <div style="padding: 6px; border-radius: 3px;">
                            <span style="color: #FFD700;">2.</span> <span style="color: #CCC;">Wipe face (cure face-based blindness)</span>
                        </div>
                        <div style="padding: 6px; border-radius: 3px;">
                            <span style="color: #FFD700;">3.</span> <span style="color: #CCC;">Wipe hands (cure slippery hands)</span>
                        </div>
                        <div style="padding: 6px; border-radius: 3px;">
                            <span style="color: #FFD700;">4.</span> <span style="color: #888;">Cancel</span>
                        </div>
                    </div>
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{towel_html}</div>
                    </div>
                </div>
            """
            current_commands_text = "1-4 = choose action | c = cancel"
            needs_numbers = True

        elif gs.prompt_cntl == "puzzle_mode":
            # ZOTLE PUZZLE VIEW - Wordle-style interface (no map, like inventory)
            
            # Build previous guesses display (like Wordle rows)
            guesses_html = ""
            if gs.zotle_puzzle and gs.zotle_puzzle['guesses']:
                for guess, results in gs.zotle_puzzle['guesses']:
                    row_html = '<div style="display: flex; justify-content: center; gap: 4px; margin: 4px 0;">'
                    for letter, status in results:
                        if status == 'correct':
                            bg_color = '#538d4e'  # Green
                        elif status == 'present':
                            bg_color = '#b59f3b'  # Yellow
                        else:
                            bg_color = '#3a3a3c'  # Grey
                        row_html += f'<div style="width: 40px; height: 40px; background: {bg_color}; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; color: #FFF; border-radius: 4px;">{letter}</div>'
                    row_html += '</div>'
                    guesses_html += row_html
            
            # Current input row (empty boxes or current guess letters)
            current_guess = gs.zotle_puzzle.get('current_guess', ['', '', '', '', '']) if gs.zotle_puzzle else ['', '', '', '', '']
            current_row_html = '<div style="display: flex; justify-content: center; gap: 4px; margin: 4px 0;">'
            for i in range(5):
                letter = current_guess[i] if i < len(current_guess) else ''
                if letter:
                    current_row_html += f'<div style="width: 40px; height: 40px; background: #121213; border: 2px solid #565758; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; color: #FFF; border-radius: 4px;">{letter}</div>'
                else:
                    current_row_html += f'<div style="width: 40px; height: 40px; background: #121213; border: 2px solid #3a3a3c; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; color: #FFF; border-radius: 4px;"></div>'
            current_row_html += '</div>'
            
            guess_count = len(gs.zotle_puzzle['guesses']) if gs.zotle_puzzle else 0
            
            # Dialog/instructions in the room box
            zotle_sprite = generate_room_sprite_html('Z')
            dialog_html = f"""
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                    <div style="flex-shrink:0;">{zotle_sprite}</div>
                    <div>
                        <div style="color: #CCC; font-weight: bold; font-size: 14px; margin-bottom: 4px;">
                            ZOTLE - ZOT'S WORD PUZZLE
                        </div>
                        <div style="color: #DDD; font-size: 11px;">
                            A shimmering phantom of the great wizard Zot appears!
                        </div>
                    </div>
                </div>
                <div style="color: #DDD; font-size: 10px; margin-bottom: 4px; text-align: center;">
                    "Guess the 5-letter word!"
                </div>
                <div style="color: #CCC; font-size: 10px; margin-bottom: 8px; text-align: center;">
                    "Hint: It's a word that describes YOU!"
                </div>
                <div style="color: #888; font-size: 9px; margin-bottom: 8px; text-align: center;">
                    <span style="color: #538d4e;">Green</span> = Correct |
                    <span style="color: #b59f3b;">Yellow</span> = Wrong spot |
                    <span style="color: #3a3a3c;">Grey</span> = Not in word
                </div>
            """
            
            puzzle_html = f"""
                <div style="border: 2px solid #555; padding: 10px; border-radius: 4px;">
                    {dialog_html}
                    
                    <div style="padding: 8px; background: #0a0a0a; border-radius: 3px; margin-bottom: 8px;">
                        {guesses_html}
                        {current_row_html}
                    </div>
                    
                    <div style="text-align: center; color: #888; font-size: 12px;">
                        Guesses: {guess_count} | Type letters, then press Send
                    </div>
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="padding: 8px;">
                        {puzzle_html}
                    </div>
                </div>
            """
            current_commands_text = "Type letters then Send | x = leave"
            needs_numbers = False

        elif gs.prompt_cntl == "zotle_teleporter_mode":
            # ZOTLE TELEPORTER VIEW - Compact display for mobile
            
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            
            # Calculate valid coordinate ranges
            max_floors = len(gs.my_tower.floors)
            
            teleporter_html = f"""
                <div style="border: 2px solid #555; padding: 8px; border-radius: 6px;">
                    <div style="color: #CCC; font-weight: bold; font-size: 13px; text-align: center; margin-bottom: 4px;">
                        ZOT'S DIMENSIONAL KEY
                    </div>
                    <div style="display: flex; justify-content: center; gap: 12px; color: #FFF; font-size: 12px; margin: 4px 0;">
                        <span>Now: <span style="color: #CCC;">{gs.player_character.x},{gs.player_character.y},{gs.player_character.z + 1}</span></span>
                    </div>
                    <div style="color: #DDD; font-size: 11px; text-align: center; margin-top: 4px;">
                        Enter: <span style="color: #CCC;">x,y,z</span> (e.g. 7,7,3)
                    </div>
                    <div style="color: #FF6B6B; font-size: 9px; text-align: center; margin-top: 2px;">
                        Cannot teleport into walls!
                    </div>
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{teleporter_html}</div>
                    </div>
                </div>
            """
            current_commands_text = "0-9 = digits | , = comma | c = cancel"
            needs_numbers = True

        elif gs.prompt_cntl == "library_read_decision_mode":
            # LIBRARY READ DECISION - Keep map and library visible with grimoire prompt
            
            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            highlight_coords = (gs.player_character.y, gs.player_character.x)

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Get found spell from room
            current_room = floor.grid[gs.player_character.y][gs.player_character.x]
            found_spell = current_room.properties.get('found_spell')
            
            # Library sprite
            current_room = floor.grid[gs.player_character.y][gs.player_character.x]
            lib_variant = 'codex' if current_room.properties.get('has_codex') else None
            library_sprite = generate_room_sprite_html('L', variant=lib_variant)

            # Spell info line
            spell_info = ""
            if found_spell:
                if gs.player_character.intelligence >= 20:
                    spell_info = f'<div style="color: #DAA520; font-size: 12px; margin-top: 6px; padding-top: 6px; border-top: 1px solid #555;"><b>{found_spell.name}</b> <span style="color: #AAA;">({found_spell.mana_cost} MP)</span></div>'
                else:
                    spell_info = '<div style="color: #888; font-size: 9px; margin-top: 6px; padding-top: 6px; border-top: 1px solid #555; font-style: italic;">The arcane symbols are difficult to decipher...</div>'

            # Library info box with grimoire decision
            library_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{library_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.4;">
                            You found a grimoire among the dusty shelves!
                        </div>
                    </div>
                    {spell_info}
                    <div style="padding-top: 6px; margin-top: 6px; border-top: 1px solid #555;">
                        <div style="color: #DAA520; font-size: 12px; font-weight: bold;">Attempt to read this grimoire?</div>
                        <div style="color: #DDD; font-size: 9px; margin-top: 2px; font-style: italic;">Reading may succeed or fail based on your intelligence...</div>
                    </div>
                </div>
            """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>

                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div>{grid_html}</div>
                        <div class="room-panel" style="width: 100%;">{library_html}</div>
                    </div>
</div>
            """
            current_commands_text = "y = read grimoire | n = discard"

        else:
            # MAP VIEW (for game_loop, confirm_quit, etc.)
            show_map = gs.prompt_cntl in ["game_loop", "confirm_quit", "flare_direction_mode", "upgrade_scroll_mode"]

            grid_html = ""
            lantern_info_html = ""  # ADD THIS

            if show_map:
                floor = gs.my_tower.floors[gs.player_character.z]
                highlight_coords = (gs.player_character.y, gs.player_character.x)

                # ADD LANTERN INFO DISPLAY
                if gs.prompt_cntl == "game_loop":
                    lantern = None
                    for item in gs.player_character.inventory.items:
                        if isinstance(item, Lantern):
                            lantern = item
                            break

                    if lantern:
                        fuel_color = "#4CAF50" if lantern.fuel_amount > 5 else (
                            "#FFD700" if lantern.fuel_amount > 2 else "#F44336")
                        fuel_bar_pct = min(100, (lantern.fuel_amount / 10) * 100)

                        lantern_info_html = ""

                # Grid Container
                grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            html_code = f"""
                <div style="font-family: monospace; font-size: 16px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}
                    {lantern_info_html}
                    {grid_html}
                    <hr>
                    
                    <div style="height: 150px; overflow-y: auto; color: #EEE; padding: 3px; font-family: monospace; font-size: 12px;">
                </div>
                """
            # Check if player has a lantern
            has_lantern = False
            lantern_fuel = 0
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    lantern_fuel = item.fuel_amount
                    break

            # DYNAMIC COMMAND TEXT GENERATION
            if gs.prompt_cntl == "game_loop":
                # Check what room player is on
                current_floor = gs.my_tower.floors[gs.player_character.z]
                current_room = current_floor.grid[gs.player_character.y][gs.player_character.x]

                base_commands = "n/s/e/w = move | i = inventory"

                # Add lantern command if player has one
                if has_lantern:
                    base_commands += f" | l = lantern"


                # Add stairs commands if on stairs
                if current_room.room_type == 'U':
                    current_commands_text = "n/s/e/w = move | u = up | i = inventory"
                    if has_lantern:
                        current_commands_text += f" | l = lantern"
                elif current_room.room_type == 'D':
                    current_commands_text = "n/s/e/w = move | d = down | i = inventory"
                    if has_lantern:
                        current_commands_text += f" | l = lantern"
                else:
                    current_commands_text = base_commands

            elif gs.prompt_cntl == "confirm_quit":
                current_commands_text = "y = yes | n = no"
            elif gs.prompt_cntl == "chest_mode":
                current_commands_text = "o = open | i = inventory"
                if has_lantern:
                    current_commands_text += f" | l = lantern"
                current_commands_text += " | n/s/e/w = move"
            elif gs.prompt_cntl == "pool_mode":
                current_commands_text = "dr = drink | i = inventory"
                if has_lantern:
                    current_commands_text += f" | l = lantern"
                current_commands_text += " | n/s/e/w = move"
            elif gs.prompt_cntl == "altar_mode":
                if gs.altar_action:
                    current_commands_text = "# = sacrifice item | b = back"
                else:
                    current_commands_text = "s = sacrifice | d = detect | b = bless | u = purify | i = inventory | x = exit"
            elif gs.prompt_cntl == "warp_mode":
                current_commands_text = "y = resist | n = enter"
            elif gs.prompt_cntl == "flare_direction_mode":
                current_commands_text = "Shine the flare in a direction (n, s, e, w, or c to cancel): "
            elif gs.prompt_cntl == "library_mode":
                current_commands_text = "r = rummage for books | i = inventory"
                if has_lantern:
                    current_commands_text += f" | l = lantern"
                current_commands_text += " | n/s/e/w = move"
            elif gs.prompt_cntl == "library_read_decision_mode":
                current_commands_text = "y = read grimoire | n = discard"
            elif gs.prompt_cntl == "upgrade_scroll_mode":
                current_commands_text = "Select item number to upgrade | c = cancel"
            elif gs.prompt_cntl == "identify_scroll_mode":
                current_commands_text = "Select item number to identify | c = cancel"
            else:
                current_commands_text = ""

        # Single-line command hint - no wrapping
        wrapped_commands = current_commands_text if current_commands_text else ""
        self.commands_label.text = wrapped_commands
        
        # Keep placeholder empty to avoid duplication with commands label
        self.input_field.placeholder = ""
        
        # Update button panel dynamically
        # Determine if number pad is needed
        # Modes that ALWAYS need numpad:
        _always_numpad = {
            'spell_casting_mode', 'journal_mode',
            'crafting_mode', 'upgrade_scroll_mode', 'identify_scroll_mode',
            'sell_quantity_mode', 'taxidermist_mode',
        }
        # Modes that need numpad only when a sub-selection is active:
        if gs.prompt_cntl in _always_numpad:
            needs_numbers = True
        elif gs.prompt_cntl == 'inventory':
            needs_numbers = gs.inventory_filter is not None
        elif gs.prompt_cntl == 'vendor_shop':
            needs_numbers = getattr(gs, 'vendor_action', None) is not None
        elif gs.prompt_cntl == 'starting_shop':
            needs_numbers = getattr(gs, 'vendor_action', None) is not None
        elif gs.prompt_cntl == 'spell_memorization_mode':
            needs_numbers = getattr(gs, 'spell_memo_action', None) is not None
        elif gs.prompt_cntl == 'altar_mode':
            needs_numbers = getattr(gs, 'altar_action', None) is not None
        else:
            needs_numbers = False
        
        self.update_button_panel(current_commands_text, needs_numbers)

        # Auto-clear notifications after 5 renders (5 user actions)
        if gs.newly_unlocked_achievements:
            gs.achievement_notification_timer += 1
            if gs.achievement_notification_timer > 2:
                gs.newly_unlocked_achievements.clear()
                gs.achievement_notification_timer = 0
        return html_code
    
    def wrap_html(self, content, log_lines=[]):
        """Wrap HTML content in a full document with mobile-optimized styling and fixed log."""
        # Convert log_lines to JavaScript-safe format
        import json
        log_lines_json = json.dumps(gs.log_lines)

        # Large text mode: scale all HTML content via CSS zoom
        zoom_css = "zoom: 1.3;" if gs.large_text_mode else ""

        # Embed song data for the persistent music engine in the shell
        music_songs_json = _MUSIC_SONGS_JSON

        # Music: bootstrap the persistent _musicEngine in the shell.
        # We deliberately fire setMood IMMEDIATELY (no 'load' event wait) —
        # iOS WKWebView only honours autoplay during page-load script
        # execution.  Once 'load' fires, the autoplay window has closed
        # and the AudioContext stays suspended.
        new_mood = get_audio_mood(gs.prompt_cntl)
        gs.current_music_mood = new_mood
        gs.music_restart = False
        enabled_js = 'true' if gs.music_enabled else 'false'
        music_js = (
            "<script>"
            "if (window._musicEngine) {"
            f" _musicEngine.setMood('{new_mood}', {enabled_js}, 0);"
            "}"
            "</script>"
        )

        result = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <style>
                body {{
                    background-color: #1a1a1a;
                    color: #ffffff;
                    font-family: 'Courier New', monospace;
                    margin: 0;
                    padding: 4px;
                    font-size: 13px;
                    line-height: 1.3;
                    overflow-x: hidden;
                    max-width: 100vw;
                    width: 100%;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                    {zoom_css}
                }}
                
                /* Prevent all content from expanding beyond viewport */
                * {{
                    max-width: 100%;
                    box-sizing: border-box;
                    overflow-wrap: break-word;
                    word-wrap: break-word;
                }}
                
                /* Specifically constrain any boxes or divs */
                div, span, pre, table {{
                    max-width: calc(100vw - 8px) !important;  /* Body width minus padding */
                }}
                
                /* Only the main content area needs overflow hidden, not inner divs.
                   Applying overflow-x:hidden to all divs prevents damage float
                   animations from showing above sprites. */
                #content-area {{
                    overflow-x: hidden;
                }}
                
                /* Carve-out: sprite wrapper divs need overflow:visible for float animations */
                div[id$="_wrap"] {{
                    overflow: visible !important;
                    max-width: none !important;
                    position: relative;
                }}
                /* Carve-out: float text elements must not be clipped */
                div[id$="_wrap"] > div {{
                    overflow: visible !important;
                    max-width: none !important;
                }}
                
                /* Mobile-optimized - aggressive size reduction */
                h1, h2, h3 {{
                    margin: 4px 0 3px 0;
                    font-size: 15px;
                }}

                h4 {{
                    margin: 3px 0 2px 0;
                    font-size: 13px;
                }}
                
                /* Compact padding on all bordered elements */
                div[style*="border"] {{
                    padding: 4px !important;
                }}
                
                /* Fixed log at bottom of viewport */
                #game-log {{
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: 90px;
                    background-color: #111;
                    color: #EEE;
                    padding: 5px;
                    font-family: monospace;
                    font-size: 11px;
                    overflow-y: auto;
                    border-top: 2px solid #444;
                    z-index: 1000;
                    line-height: 1.2;
                }}
                
                /* Scrollable content area - add padding at bottom for log */
                #content-area {{
                    padding-bottom: 85px; /* Space for fixed log */
                }}
                
                /* Tighter line spacing */
                br {{
                    line-height: 0.8;
                }}
                
                /* Make dungeon map compact */
                pre {{
                    font-size: 12px;
                    overflow-x: auto;
                    margin: 2px 0;
                    padding: 4px;
                }}
                
                /* Ensure text wraps properly */
                * {{
                    word-wrap: break-word;
                    max-width: 100%;
                }}
                
                /* Scrollbar styling */
                ::-webkit-scrollbar {{
                    width: 8px;
                }}
                
                ::-webkit-scrollbar-track {{
                    background: #333;
                }}
                
                ::-webkit-scrollbar-thumb {{
                    background: #666;
                    border-radius: 4px;
                }}
                
                ::-webkit-scrollbar-thumb:hover {{
                    background: #888;
                }}
                
                /* Make sure dungeon map doesn't overflow */
                .dungeon-map {{
                    overflow-x: auto;
                    white-space: nowrap;
                }}

                /* Constrain room interaction panels to prevent outer scrolling */
                .room-panel {{
                    max-height: calc(100vh - 340px);
                    overflow-y: auto;
                    -webkit-overflow-scrolling: touch;
                }}

                /* ===== TRANSITION ANIMATIONS ===== */

                /* No page-level fade — movement/lantern should feel instant */

                /* Room interaction panels: fade + slide up */
                .room-panel {{
                    animation: panelSlideIn 300ms ease-out;
                }}
                @keyframes panelSlideIn {{
                    from {{ opacity: 0; transform: translateY(12px); }}
                    to   {{ opacity: 1; transform: translateY(0); }}
                }}

                /* Combat panels: fade + subtle scale pop */
                #monster_panel {{
                    animation: combatIn 250ms ease-out;
                }}
                #player_panel {{
                    animation: combatIn 250ms ease-out 80ms both;
                }}
                @keyframes combatIn {{
                    from {{ opacity: 0; transform: scale(0.95); }}
                    to   {{ opacity: 1; transform: scale(1); }}
                }}

                /* Panel shake on damage impact */
                @keyframes panelShake {{
                    0%, 100% {{ transform: translateX(0); }}
                    15% {{ transform: translateX(-5px); }}
                    30% {{ transform: translateX(5px); }}
                    45% {{ transform: translateX(-4px); }}
                    60% {{ transform: translateX(3px); }}
                    75% {{ transform: translateX(-2px); }}
                }}

                /* Full screen shake on CRIT — bigger amplitude, diagonal travel */
                @keyframes screenShake {{
                    0%, 100% {{ transform: translate(0, 0); }}
                    10% {{ transform: translate(-7px, -3px); }}
                    20% {{ transform: translate(7px, 3px); }}
                    30% {{ transform: translate(-6px, 2px); }}
                    40% {{ transform: translate(6px, -2px); }}
                    50% {{ transform: translate(-4px, 1px); }}
                    60% {{ transform: translate(4px, -1px); }}
                    70% {{ transform: translate(-2px, 0); }}
                    80% {{ transform: translate(2px, 0); }}
                }}

                /* Low-HP pulse for the player panel: red heartbeat warning */
                @keyframes lowHPPulse {{
                    0%, 100% {{
                        box-shadow: 0 0 4px rgba(255, 82, 82, 0.3);
                        border-color: #8a3a3a;
                    }}
                    50% {{
                        box-shadow: 0 0 18px rgba(255, 82, 82, 0.85), 0 0 6px rgba(255, 82, 82, 0.6) inset;
                        border-color: #FF5252;
                    }}
                }}

                /* Critical hit burst on a winning nat-max dice */
                @keyframes critPulse {{
                    0%   {{ transform: scale(1) rotate(0deg); filter: brightness(1); }}
                    30%  {{ transform: scale(1.5) rotate(-8deg); filter: brightness(2.5); }}
                    60%  {{ transform: scale(1.2) rotate(4deg); filter: brightness(1.8); }}
                    100% {{ transform: scale(1) rotate(0deg); filter: brightness(1); }}
                }}

                /* Fumble wobble on a losing nat-1 dice */
                @keyframes fumbleShake {{
                    0%, 100% {{ transform: rotate(0deg); }}
                    20% {{ transform: rotate(-12deg); }}
                    40% {{ transform: rotate(12deg); }}
                    60% {{ transform: rotate(-8deg); }}
                    80% {{ transform: rotate(5deg); }}
                }}

                /* Spell channeling pulse on the channeling indicator */
                @keyframes channelPulse {{
                    0%, 100% {{ border-color: #E040FB; box-shadow: 0 0 4px rgba(224,64,251,0.3); }}
                    50% {{ border-color: #CE93D8; box-shadow: 0 0 12px rgba(224,64,251,0.6); }}
                }}

                /* Game log: no animation (fixed, persistent) */
                #game-log {{
                    animation: none;
                }}
            </style>
        </head>
        <body>
            <script>
                // Lightweight Timeline sequencer — replaces nested setTimeout chains.
                // Usage: new Timeline().wait(300).do(fn1).wait(600).do(fn2).play();
                window.Timeline = function() {{
                    this._steps = [];
                }};
                Timeline.prototype.wait = function(ms) {{
                    this._steps.push({{type:'wait', ms:ms}});
                    return this;
                }};
                Timeline.prototype.do = function(fn) {{
                    this._steps.push({{type:'do', fn:fn}});
                    return this;
                }};
                Timeline.prototype.play = function() {{
                    var t = 0;
                    for (var i = 0; i < this._steps.length; i++) {{
                        var s = this._steps[i];
                        if (s.type === 'wait') {{ t += s.ms; }}
                        else if (s.type === 'do') {{
                            (function(fn, delay) {{
                                setTimeout(fn, delay);
                            }})(s.fn, t);
                        }}
                    }}
                }};

                // === Persistent music engine ===
                // Lives in the shell so the AudioContext survives all
                // _render_update() calls (which use evaluate_javascript
                // and never reload the page).
                window._musicEngine = (function() {{
                    var SONGS = {music_songs_json};
                    var ALIASES = {{shop:'explore', mystery:'explore', deep:'explore', garden:'explore'}};
                    var ctx = null, master = null, noiseBuf = null;
                    var currentMood = null, currentSong = null;
                    var stepSec = 0.3, currentStep = 0, tickHandle = null;
                    var enabled = true, totalSteps = 64;
                    var VOL = {{ pulse1: 0.08, pulse2: 0.06, triangle: 0.12, noise: 0.07 }};

                    function ensureCtx() {{
                        if (ctx) return true;
                        try {{
                            var AC = window.AudioContext || window.webkitAudioContext;
                            if (!AC) return false;
                            ctx = new AC();
                            master = ctx.createGain();
                            master.gain.value = 0.25;
                            master.connect(ctx.destination);
                            var nLen = ctx.sampleRate;
                            noiseBuf = ctx.createBuffer(1, nLen, ctx.sampleRate);
                            var nd = noiseBuf.getChannelData(0);
                            for (var i = 0; i < nLen; i++) nd[i] = Math.random() * 2 - 1;
                            return true;
                        }} catch(e) {{ return false; }}
                    }}
                    function playNote(freq, dur, type, vol) {{
                        if (!freq || freq <= 0 || !enabled) return;
                        try {{
                            var osc = ctx.createOscillator();
                            osc.type = type; osc.frequency.value = freq;
                            osc.detune.value = (Math.random() * 16) - 8;
                            var g = ctx.createGain();
                            var now = ctx.currentTime;
                            var len = dur * stepSec;
                            g.gain.setValueAtTime(vol, now);
                            g.gain.setValueAtTime(vol * 0.8, now + len * 0.75);
                            g.gain.linearRampToValueAtTime(0.001, now + len * 0.95);
                            osc.connect(g); g.connect(master);
                            osc.start(now); osc.stop(now + len);
                        }} catch(e) {{}}
                    }}
                    function playNoiseHit(filterFreq, dur) {{
                        if (!enabled) return;
                        try {{
                            var src = ctx.createBufferSource();
                            src.buffer = noiseBuf;
                            var filt = ctx.createBiquadFilter();
                            if (filterFreq < 500) {{
                                filt.type = 'lowpass';
                                filt.frequency.value = filterFreq * (0.9 + Math.random() * 0.2);
                            }} else {{
                                filt.type = 'bandpass';
                                filt.frequency.value = filterFreq * (0.85 + Math.random() * 0.3);
                                filt.Q.value = 1 + Math.random() * 2;
                            }}
                            var g = ctx.createGain();
                            var now = ctx.currentTime;
                            var len = Math.min(dur * stepSec, 0.15);
                            g.gain.setValueAtTime(VOL.noise, now);
                            g.gain.exponentialRampToValueAtTime(0.001, now + len);
                            src.connect(filt); filt.connect(g); g.connect(master);
                            src.start(now); src.stop(now + len + 0.01);
                        }} catch(e) {{}}
                    }}
                    function tick() {{
                        if (!currentSong || !enabled) return;
                        var channels = ['pulse1', 'pulse2', 'triangle', 'noise'];
                        for (var c = 0; c < channels.length; c++) {{
                            var ch = channels[c];
                            var pattern = currentSong[ch];
                            if (!pattern) continue;
                            for (var n = 0; n < pattern.length; n++) {{
                                if (pattern[n][0] === currentStep) {{
                                    var f = pattern[n][1], d = pattern[n][2];
                                    if (ch === 'noise') playNoiseHit(f, d);
                                    else if (ch === 'triangle') playNote(f, d, 'triangle', VOL.triangle);
                                    else playNote(f, d, 'square', VOL[ch]);
                                }}
                            }}
                        }}
                        currentStep = (currentStep + 1) % totalSteps;
                    }}
                    return {{
                        setMood: function(mood, isEnabled, delayMs) {{
                            if (!ensureCtx()) return;
                            enabled = (isEnabled !== false);
                            if (ctx.state === 'suspended') {{
                                try {{ ctx.resume(); }} catch(e) {{}}
                            }}
                            mood = ALIASES[mood] || mood;
                            if (mood === currentMood) return;
                            var swap = function() {{
                                currentMood = mood;
                                currentSong = SONGS[mood] || SONGS.explore;
                                stepSec = 60 / (currentSong.bpm * 2);
                                currentStep = 0;
                                if (tickHandle) clearInterval(tickHandle);
                                tickHandle = setInterval(tick, stepSec * 1000);
                            }};
                            if (delayMs > 0) {{
                                if (tickHandle) {{ clearInterval(tickHandle); tickHandle = null; }}
                                currentSong = null;
                                setTimeout(swap, delayMs);
                            }} else {{
                                swap();
                            }}
                        }},
                        setEnabled: function(on) {{
                            enabled = !!on;
                            if (master && ctx) {{
                                try {{
                                    master.gain.setTargetAtTime(on ? 0.25 : 0, ctx.currentTime, 0.05);
                                }} catch(e) {{}}
                            }}
                        }},
                        ctxState: function() {{ return ctx ? ctx.state : 'none'; }},
                        resume: function() {{
                            if (!ensureCtx()) return;
                            if (ctx.state === 'suspended') {{
                                try {{ ctx.resume(); }} catch(e) {{}}
                            }}
                            // If we have a queued mood with no song playing yet,
                            // re-trigger setMood now that we've got a gesture.
                            if (currentMood && !currentSong) {{
                                var m = currentMood;
                                currentMood = null;
                                this.setMood(m, enabled, 0);
                            }}
                        }},
                        // Suspend the AudioContext entirely so playback halts
                        // AND the browser frees CPU/battery.  Called on
                        // visibilitychange=hidden (app backgrounded, phone
                        // locked, etc.).  resume() picks up where it left off.
                        pause: function() {{
                            if (!ctx) return;
                            if (ctx.state === 'running') {{
                                try {{ ctx.suspend(); }} catch(e) {{}}
                            }}
                        }}
                    }};
                }})();

                // Resume music context on first user interaction (gesture
                // policy compliance — works because the audio engine and
                // game UI now share the same WebView frame).
                document.addEventListener('click', function() {{
                    try {{ if (window._musicEngine) window._musicEngine.resume(); }} catch(e) {{}}
                }}, {{passive:true,capture:true}});
                document.addEventListener('touchstart', function() {{
                    try {{ if (window._musicEngine) window._musicEngine.resume(); }} catch(e) {{}}
                }}, {{passive:true,capture:true}});

                // Pause music when the app goes to background, resume on
                // return.  Fires when the user switches apps, locks the
                // phone, or otherwise sends the WebView to the background.
                document.addEventListener('visibilitychange', function() {{
                    if (!window._musicEngine) return;
                    try {{
                        if (document.visibilityState === 'hidden') {{
                            window._musicEngine.pause();
                        }} else if (document.visibilityState === 'visible') {{
                            window._musicEngine.resume();
                        }}
                    }} catch(e) {{}}
                }});

                // === updateGame: incremental DOM update used by render_update ===
                // Replaces content-area innerHTML, re-executes inline scripts
                // (innerHTML doesn't auto-run them), updates log, runs the
                // animation/SFX scripts, and switches music mood.
                window.updateGame = function(p) {{
                    var ca = document.getElementById('content-area');
                    if (ca && p.contentHtml !== undefined) {{
                        ca.innerHTML = p.contentHtml;
                        // Re-execute inline <script> tags from new content
                        var inner = ca.querySelectorAll('script');
                        for (var i = 0; i < inner.length; i++) {{
                            try {{
                                var ns = document.createElement('script');
                                ns.textContent = inner[i].textContent;
                                document.body.appendChild(ns);
                                document.body.removeChild(ns);
                            }} catch(e) {{}}
                        }}
                    }}
                    // Update log
                    if (p.logLines !== undefined) {{
                        window.logLines = p.logLines;
                        window.hasDiceRolls = !!p.hasDiceRolls;
                        window.hasInitRoll = !!p.hasInitRoll;
                        var ld = document.getElementById('game-log');
                        if (window.hasDiceRolls && ld) {{
                            ld.style.opacity = '0';
                            var delay = window.hasInitRoll ? 1000 : 3300;
                            setTimeout(function() {{
                                if (typeof updateLog === 'function') updateLog();
                                ld.style.transition = 'opacity 0.3s';
                                ld.style.opacity = '1';
                            }}, delay);
                        }} else {{
                            if (typeof updateLog === 'function') updateLog();
                            if (ld) ld.style.opacity = '1';
                        }}
                    }}
                    // Run animation / SFX scripts from payload
                    if (p.scripts) {{
                        for (var j = 0; j < p.scripts.length; j++) {{
                            try {{
                                var s = document.createElement('script');
                                s.textContent = p.scripts[j];
                                document.body.appendChild(s);
                                document.body.removeChild(s);
                            }} catch(e) {{}}
                        }}
                    }}
                    // Music mood
                    if (p.mood && window._musicEngine) {{
                        window._musicEngine.setMood(p.mood, p.musicEnabled !== false, p.musicDelayMs || 0);
                    }} else if (window._musicEngine && p.musicEnabled !== undefined) {{
                        window._musicEngine.setEnabled(!!p.musicEnabled);
                    }}
                }};
            </script>
            <div id="content-area">
                {content}
            </div>
            <div id="game-log"></div>
            <script>
                // Embed log lines from Python
                window.logLines = {log_lines_json};
                window.hasDiceRolls = {'true' if gs.last_dice_rolls else 'false'};
                window.hasInitRoll = {'true' if (gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)) else 'false'};

                // Update log content and auto-scroll to bottom
                function updateLog() {{
                    var logDiv = document.getElementById('game-log');
                    if (logDiv && window.logLines) {{
                        logDiv.innerHTML = window.logLines.join('<br>');
                        logDiv.scrollTop = logDiv.scrollHeight;
                    }}
                }}
                // Delay log when dice are rolling so results aren't spoiled.
                // Log stays hidden until after the reveal animation finishes.
                if (window.hasDiceRolls) {{
                    var logDiv = document.getElementById('game-log');
                    if (logDiv) logDiv.style.opacity = '0';
                    // Reveal delay: ATK reveal ~1160ms, DEF reveal ~3060ms, init ~760ms
                    var delay = window.hasInitRoll ? 1000 : 3300;
                    window.addEventListener('load', function() {{
                        setTimeout(function() {{
                            updateLog();
                            var ld = document.getElementById('game-log');
                            if (ld) {{ ld.style.transition = 'opacity 0.3s'; ld.style.opacity = '1'; }}
                        }}, delay);
                    }});
                }} else {{
                    window.addEventListener('load', updateLog);
                }}
            </script>
            {generate_spell_cast_js(gs.last_spell_cast)}
            {generate_spell_particles_js(gs.last_spell_cast)}
            {generate_dice_roll_js(gs.last_dice_rolls)}
            {generate_concentration_check_js(gs.last_concentration_roll)}
            {generate_monster_defeat_js(gs.monster_defeated_anim)}
            {music_js}
            {generate_sfx_js(gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_heal, gs.last_monster_damage_badge, gs.last_player_damage_badge, gs.last_player_status, gs.last_monster_status, gs.last_spell_cast, gs.last_concentration_roll, gs.monster_defeated_anim, gs.sfx_event, gs.music_enabled, bool(gs.last_dice_rolls), bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}
        </body>
        </html>
        """
        # Clear one-shot animation flags after rendering
        gs.monster_defeated_anim = None
        gs.last_dice_rolls = []
        gs.last_spell_cast = None
        gs.last_concentration_roll = None
        gs.sfx_event = None
        # Clear combat SFX flags too — these are set at the start of a combat
        # turn and were previously only reset by the NEXT combat turn, so they
        # lingered across renders in game_loop and re-fired SFX on every
        # button press (e.g., weapon hit replaying after a combat victory).
        gs.last_monster_damage = 0
        gs.last_player_damage = 0
        gs.last_player_blocked = False
        gs.last_player_heal = 0
        gs.last_monster_damage_badge = None
        gs.last_player_damage_badge = None
        gs.last_player_status = None
        gs.last_monster_status = None
        return result
    

    
    @staticmethod
    def strip_ansi(text):
        """Remove ANSI color codes from text."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)


# --------------------------------------------------------------------------------
# 23. ENTRY POINT
# --------------------------------------------------------------------------------

def main():
    """Create and run the Toga application."""
    return WizardsCavernApp(
        'Wizard\'s Cavern',
        'com.example.wizardscavern'
    )


if __name__ == '__main__':
    main().main_loop()

