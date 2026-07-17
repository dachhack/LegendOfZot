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
import re
import json
import os

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

# Game state (all shared mutable globals)
from . import game_state as gs
from .game_state import (add_log, COLOR_RED, COLOR_GREEN, COLOR_RESET, COLOR_YELLOW)

# Game modules - import all public names for backward compatibility
from .achievements import ACHIEVEMENTS
from .zotle import (initialize_zotle_puzzle)
from .item_templates import *
from .items import *
from .characters import *
from .dungeon import Tower
from .combat import *
from .vendor import *
from .save_system import SaveSystem
from .room_actions import *
from .game_systems import *
from .game_systems import _handle, _trigger_room_interaction
from .version import VERSION, BUILD_NUMBER, CHANGELOG


def _load_screen_image_b64(name):
    """Load a webp screen background and return its base64 data URI.

    Files live at ``wizardscavern/data/screens/<name>.webp``.  Cached
    on first call.
    """
    import base64
    cache = _load_screen_image_b64._cache
    if name in cache:
        return cache[name]
    path = os.path.join(os.path.dirname(__file__), 'data', 'screens', f'{name}.webp')
    try:
        with open(path, 'rb') as fh:
            cache[name] = 'data:image/webp;base64,' + base64.b64encode(fh.read()).decode('ascii')
    except FileNotFoundError:
        cache[name] = ''
    return cache[name]


_load_screen_image_b64._cache = {}


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
                        'player_sprite', 'player_cantrips', 'tourist_depth',
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


# Song data as JSON, embedded into the persistent _musicEngine shell
# (see updateGame) so it isn't re-encoded on every render.
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


def _statbar_format_pair(current, maximum):
    """Format current/maximum as a compact 'cur/max' string with k-suffix
    once values cross 1000 so the overlay stays inside the bar width."""
    if maximum >= 1000:
        cur_str = f"{current//1000}k" if current >= 1000 else str(current)
        max_str = f"{maximum//1000}k"
    else:
        cur_str = str(current)
        max_str = str(maximum)
    return f"{cur_str}/{max_str}"


def health_bar_html(current, maximum, width=70):
    """Compact HTML HP bar — coloured fill + centered text overlay.

    Used on the stats banner where the text-based bar (`[####----]
    999/999`) eats too much horizontal space and forces the line to
    wrap at high stats.  Combat panels still use the text version
    because their JS hooks update textContent in place."""
    if maximum <= 0:
        pct = 0
    else:
        pct = max(0, min(100, (current / maximum) * 100))
    if pct >= 60:
        fill_color = "#4CAF50"  # green
    elif pct >= 30:
        fill_color = "#FFA726"  # orange
    else:
        fill_color = "#E53935"  # red
    label = _statbar_format_pair(current, maximum)
    return (
        f'<span class="statbar" style="width:{width}px;">'
        f'<span class="statbar-fill" style="width:{pct:.0f}%; background:{fill_color};"></span>'
        f'<span class="statbar-text">{label}</span>'
        f'</span>'
    )


def mana_bar_html(current, maximum, width=70):
    """Compact HTML MP bar — same shape as health_bar_html, blue fill."""
    if maximum <= 0:
        return ""
    pct = max(0, min(100, (current / maximum) * 100))
    label = _statbar_format_pair(current, maximum)
    return (
        f'<span class="statbar" style="width:{width}px;">'
        f'<span class="statbar-fill" style="width:{pct:.0f}%; background:#42A5F5;"></span>'
        f'<span class="statbar-text">{label}</span>'
        f'</span>'
    )


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
    0.15 + lvl * 0.06
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


# === Spell icon visual buckets ===========================================
# Each spell's cast animation uses its round-8 sprite (the unique book /
# glyph icon, not the inventory `?` placeholder). The animation style is
# chosen by bucket: projectile, aoe, heal, buff, cleanse, ultimate.

_AOE_SPELLS = frozenset({
    'Inferno', 'Blizzard', 'Earthquake', 'Tsunami', 'Meteor Strike',
    'Chain Lightning', 'Thunder Clap', 'Mass Heal', 'Psychic Scream',
    'Holy Light',
})

_ULTIMATE_SPELLS = frozenset({
    'Time Stop', 'Armageddon', 'Supernova', 'Black Hole',
    'Divine Intervention', 'Perfect Regeneration', 'Ultimate Shield',
})

_CLEANSE_SPELLS = frozenset({
    'Purify', 'Cure Weakness', 'Freedom',
})


def _spell_visual_bucket(spell):
    """Map a spell to one of six animation buckets."""
    if spell is None:
        return None
    name = getattr(spell, 'name', '')
    if name in _ULTIMATE_SPELLS:
        return 'ultimate'
    if name in _AOE_SPELLS:
        return 'aoe'
    if name in _CLEANSE_SPELLS:
        return 'cleanse'
    stype = getattr(spell, 'spell_type', 'damage')
    if stype == 'healing':
        return 'heal'
    if stype == 'remove_status':
        return 'cleanse'
    if stype == 'buff':
        return 'buff'
    return 'projectile'


def generate_spell_icon_visual_js(spell):
    """Animate the spell's round-8 sprite icon during cast.

    Returns a `<script>` tag containing per-bucket animation JS, or '' if
    the spell has no sprite or the bucket is unknown. The script runs
    alongside generate_spell_cast_js (banner+tint) and
    generate_spell_particles_js (per-element particles) — those handle
    the wash and the tail; this one handles the spell's identity.
    """
    if not spell:
        return ''
    try:
        from .sprites.identifiables import get_per_spell_sprite_pid
        from .sprites import get_image_b64
    except Exception:
        return ''
    pid = get_per_spell_sprite_pid(spell)
    if not pid:
        return ''
    img_b64 = get_image_b64(pid)
    if not img_b64:
        return ''

    bucket = _spell_visual_bucket(spell)
    if not bucket:
        return ''

    dtype = _spell_visual_element(spell)
    color = ELEMENT_COLORS.get(dtype, '#FFFFFF')
    glow_color = color
    img_uri = 'data:image/webp;base64,' + img_b64

    # Common scaffold: an <img> overlay positioned over the viewport.
    # Each bucket sets cssText, schedules transitions, and removes itself.
    base = (
        'var img=document.createElement("img");'
        'img.src="' + img_uri + '";'
        'img.style.imageRendering="pixelated";'
    )

    if bucket == 'projectile':
        # Spawn near the bottom-left (player side of the combat panel),
        # animate across to the right (monster side), scaling up and
        # spinning, then fade on impact.
        return (
            '<script>(function(){'
            + base +
            'img.style.cssText="position:fixed;bottom:30%;left:18%;width:56px;height:56px;'
            'image-rendering:pixelated;z-index:99997;opacity:0;'
            'transform:translate(0,0) scale(0.6) rotate(0deg);'
            'transition:all 0.45s cubic-bezier(.5,.05,.95,.7);'
            'filter:drop-shadow(0 0 14px ' + glow_color + ');";'
            'document.body.appendChild(img);'
            'setTimeout(function(){'
            'img.style.opacity="1";'
            'img.style.left="68%";'
            'img.style.transform="translate(0,-40px) scale(1.4) rotate(540deg)";'
            '},40);'
            'setTimeout(function(){'
            'img.style.transition="opacity 0.18s ease-in,transform 0.18s ease-in";'
            'img.style.opacity="0";'
            'img.style.transform="translate(0,-40px) scale(2.2) rotate(540deg)";'
            '},480);'
            'setTimeout(function(){if(img.parentNode)img.parentNode.removeChild(img);},760);'
            '})();</script>'
        )

    if bucket == 'aoe':
        # Big icon flashes center-screen. Existing screen tint + particles
        # cover the rest.
        return (
            '<script>(function(){'
            + base +
            'img.style.cssText="position:fixed;top:38%;left:50%;width:160px;height:160px;'
            'image-rendering:pixelated;z-index:99997;opacity:0;'
            'transform:translate(-50%,-50%) scale(0.5) rotate(0deg);'
            'transition:all 0.22s ease-out;'
            'filter:drop-shadow(0 0 22px ' + glow_color + ');";'
            'document.body.appendChild(img);'
            'setTimeout(function(){'
            'img.style.opacity="0.92";'
            'img.style.transform="translate(-50%,-50%) scale(1.15) rotate(8deg)";'
            '},40);'
            'setTimeout(function(){'
            'img.style.transition="opacity 0.4s ease-in,transform 0.4s ease-in";'
            'img.style.opacity="0";'
            'img.style.transform="translate(-50%,-50%) scale(2.0) rotate(-12deg)";'
            '},420);'
            'setTimeout(function(){if(img.parentNode)img.parentNode.removeChild(img);},900);'
            '})();</script>'
        )

    if bucket == 'heal':
        # Icon descends from above onto the player area (left side of HUD)
        # with a green-gold glow, then fades out gently.
        return (
            '<script>(function(){'
            + base +
            'img.style.cssText="position:fixed;top:-80px;left:24%;width:72px;height:72px;'
            'image-rendering:pixelated;z-index:99997;opacity:0;'
            'transform:translate(-50%,0) rotate(0deg);'
            'transition:all 0.6s cubic-bezier(.25,.1,.25,1);'
            'filter:drop-shadow(0 0 18px #4CFF8C) drop-shadow(0 0 8px #FFD700);";'
            'document.body.appendChild(img);'
            'setTimeout(function(){'
            'img.style.opacity="1";'
            'img.style.top="44%";'
            'img.style.transform="translate(-50%,0) rotate(360deg)";'
            '},40);'
            'setTimeout(function(){'
            'img.style.transition="opacity 0.5s ease-in,transform 0.5s ease-in";'
            'img.style.opacity="0";'
            'img.style.transform="translate(-50%,-40px) scale(0.8) rotate(360deg)";'
            '},800);'
            'setTimeout(function(){if(img.parentNode)img.parentNode.removeChild(img);},1400);'
            '})();</script>'
        )

    if bucket == 'buff':
        # Icon orbits the player area in a half-loop and settles into a
        # pulsing glow before fading.
        return (
            '<script>(function(){'
            + base +
            'img.style.cssText="position:fixed;bottom:32%;left:24%;width:56px;height:56px;'
            'image-rendering:pixelated;z-index:99997;opacity:0;'
            'transform:translate(-50%,0) scale(0.5);'
            'transition:all 0.3s ease-out;'
            'filter:drop-shadow(0 0 14px ' + glow_color + ') drop-shadow(0 0 4px #FFD700);";'
            'document.body.appendChild(img);'
            'setTimeout(function(){'
            'img.style.opacity="1";'
            'img.style.transform="translate(-50%,0) scale(1.1)";'
            '},40);'
            'setTimeout(function(){'
            'img.style.transition="all 0.35s ease-in-out";'
            'img.style.transform="translate(40px,-40px) scale(1)";'
            '},340);'
            'setTimeout(function(){'
            'img.style.transform="translate(-90px,-40px) scale(1)";'
            '},680);'
            'setTimeout(function(){'
            'img.style.transform="translate(-50%,-30px) scale(1.2)";'
            '},1020);'
            'setTimeout(function(){'
            'img.style.transition="opacity 0.4s ease-in,transform 0.4s ease-in";'
            'img.style.opacity="0";'
            'img.style.transform="translate(-50%,0) scale(0.6)";'
            '},1300);'
            'setTimeout(function(){if(img.parentNode)img.parentNode.removeChild(img);},1800);'
            '})();</script>'
        )

    if bucket == 'cleanse':
        # Icon spirals around the player position with a white-gold sparkle
        # filter, briefly inflates, then fades.
        return (
            '<script>(function(){'
            + base +
            'img.style.cssText="position:fixed;bottom:32%;left:24%;width:56px;height:56px;'
            'image-rendering:pixelated;z-index:99997;opacity:0;'
            'transform:translate(-50%,0) rotate(0deg) scale(0.6);'
            'transition:all 0.55s cubic-bezier(.25,.1,.25,1);'
            'filter:drop-shadow(0 0 16px #FFFFFF) drop-shadow(0 0 6px #FFD700);";'
            'document.body.appendChild(img);'
            'setTimeout(function(){'
            'img.style.opacity="1";'
            'img.style.transform="translate(-50%,-40px) rotate(720deg) scale(1.4)";'
            '},40);'
            'setTimeout(function(){'
            'img.style.transition="opacity 0.4s ease-in,transform 0.4s ease-in";'
            'img.style.opacity="0";'
            'img.style.transform="translate(-50%,-80px) rotate(1080deg) scale(0.8)";'
            '},700);'
            'setTimeout(function(){if(img.parentNode)img.parentNode.removeChild(img);},1200);'
            '})();</script>'
        )

    if bucket == 'ultimate':
        # Black wash + huge icon held center-screen for ~0.8s with intense
        # drop-shadow glow, then both fade out.
        return (
            '<script>(function(){'
            'var ovl=document.createElement("div");'
            'ovl.style.cssText="position:fixed;top:0;left:0;right:0;bottom:0;z-index:99996;'
            'background:#000;opacity:0;transition:opacity 0.18s ease-out;pointer-events:none;";'
            'document.body.appendChild(ovl);'
            'setTimeout(function(){ovl.style.opacity="0.8";},40);'
            + base +
            'img.style.cssText="position:fixed;top:50%;left:50%;width:240px;height:240px;'
            'image-rendering:pixelated;z-index:99997;opacity:0;'
            'transform:translate(-50%,-50%) scale(0.2) rotate(0deg);'
            'transition:all 0.35s cubic-bezier(.34,1.56,.64,1);'
            'filter:drop-shadow(0 0 36px ' + glow_color + ') drop-shadow(0 0 12px #FFD700);";'
            'document.body.appendChild(img);'
            'setTimeout(function(){'
            'img.style.opacity="1";'
            'img.style.transform="translate(-50%,-50%) scale(1) rotate(360deg)";'
            '},80);'
            'setTimeout(function(){'
            'img.style.transition="opacity 0.5s ease-in,transform 0.5s ease-in";'
            'ovl.style.transition="opacity 0.5s ease-in";'
            'img.style.opacity="0";'
            'ovl.style.opacity="0";'
            'img.style.transform="translate(-50%,-50%) scale(1.6) rotate(360deg)";'
            '},900);'
            'setTimeout(function(){'
            'if(img.parentNode)img.parentNode.removeChild(img);'
            'if(ovl.parentNode)ovl.parentNode.removeChild(ovl);'
            '},1500);'
            '})();</script>'
        )

    return ''


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
        # Cinematic shake.  Important: do NOT shake #content-area (or
        # any ancestor of the position:fixed strips) -- a transform on
        # an ancestor re-roots fixed-position descendants to it,
        # which would shove the map / chips out of place every time
        # the player crits.  Target the room-panel (which holds the
        # combat box on the combat screen) so only the panel shakes.
        'var scr=document.querySelector(".bottom-pinned-zone .room-panel")'
        '||document.querySelector(".room-panel");'
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

    Phase times come from game_state (single source of truth for the kill
    sequence), so retuning the timeline only touches the constants:
      0-600ms:               Player ATTACK dice tumbles + lands
      600-1000ms:            Monster DEFEND dice tumbles + lands (resolved)
      1300ms:                Monster damage float appears
      DEFEAT_GRAYSCALE_MS:   Sprite fades to grayscale (kill confirmed)
      DEFEAT_OVERLAY_MS:     Flash "MONSTER NAME / DEFEATED" overlay
      DEFEAT_DISMISS_MS:     Panel auto-dismissed by Python timer
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

        # Phase 1: wait for opposed dice + damage float to play

        # Phase 2 (DEFEAT_GRAYSCALE_MS): grayscale + dim the sprite box only (not the text)
        'setTimeout(function(){'
        'var sb=document.getElementById("monster_sprite_box");'
        'if(sb){'
        'sb.style.setProperty("filter","grayscale(100%) brightness(0.35)","important");'
        '}'
        f'}},{gs.DEFEAT_GRAYSCALE_MS});'

        # Phase 3 (DEFEAT_OVERLAY_MS): flash in overlay with monster name + DEFEATED
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
        f'}},{gs.DEFEAT_OVERLAY_MS});'

        '})();</script>'
    )


def generate_sprite_anim_triggers_js(monster_name, monster_dmg, player_dmg,
                                     spell_cast, monster_defeated,
                                     has_dice_rolls=False, has_init_roll=False):
    """Generate JS to trigger procedural sprite animations synced to the combat timeline."""
    if not monster_name:
        return ""
    safe_id = "ms_" + "".join(ch if ch.isalnum() else "_" for ch in monster_name)
    init_offset = 1000 if has_init_roll else 0
    monster_dmg_delay = 1300 + init_offset
    player_dmg_delay = 3200 + init_offset

    triggers = []

    if spell_cast:
        element = _spell_visual_element(spell_cast).lower()
        glow_map = {'fire': '#ff7a3a', 'ice': '#5af0ff', 'frost': '#5af0ff',
                    'poison': '#44ff44', 'healing': '#44ff44', 'holy': '#ffffa0',
                    'necrotic': '#88ff88', 'light': '#ffffa0'}
        gc = glow_map.get(element, '#b46aff')
        triggers.append(
            f'setTimeout(function(){{if(window._sprAnim)window._sprAnim.trigger("{safe_id}",window._sprAnim.CAST,{{glowColor:"{gc}"}});}},100);'
        )
    elif monster_dmg and monster_dmg > 0:
        triggers.append(
            f'setTimeout(function(){{if(window._sprAnim)window._sprAnim.trigger("{safe_id}",window._sprAnim.HIT);}},{monster_dmg_delay});'
        )

    if player_dmg and player_dmg > 0:
        triggers.append(
            f'setTimeout(function(){{if(window._sprAnim)window._sprAnim.trigger("{safe_id}",window._sprAnim.ATTACK);}},{player_dmg_delay - 550});'
        )
        triggers.append(
            f'setTimeout(function(){{if(window._sprAnim)window._sprAnim.trigger("player_sprite",window._sprAnim.HIT);}},{player_dmg_delay});'
        )

    if monster_defeated:
        death_delay = gs.DEFEAT_GRAYSCALE_MS + init_offset
        triggers.append(
            f'setTimeout(function(){{if(window._sprAnim)window._sprAnim.trigger("{safe_id}",window._sprAnim.DEATH);}},{death_delay});'
        )

    if not triggers:
        return ""
    return '<script>(function(){' + ''.join(triggers) + '})();</script>'


# ============================================================
# SPRITE SYSTEM
# Sprite sheets, mappings, and rendering functions
# All sprite data and rendering now in external sprite_data.py
# ============================================================

# Threat-tier visuals for the monster combat panel.  A roguelike's first job
# is honest threat signalling (DCSS color-codes tiles, Brogue glows its
# horrors) -- so deadlier foes get bigger sprites + fiercer, glowing boxes.
# The glow color is fed to the threatPulse keyframe via the --tg CSS var so a
# single animation serves every tier.
#
# loom_px: how far the sprite rises ABOVE its panel.  The combat view packs
# the monster + player boxes into a fixed 200px slot (.room-panel,
# overflow:hidden), so an oversized sprite would clip the player's own box.
# For the rare elite tiers the sprite is anchored to the bottom of a shorter
# slot (sprite_size - loom_px) and a JS overlay paints it over the HUD.
#
# flourish: entrance-drama level (0-4), playing ONCE per fight (token-gated):
#   0 none, 1 pop, 2 rise, 3 surge + soft buzz, 4 SLAM + screen flash + a
#   dramatic vibration pattern -- the bigger the threat, the bigger the reveal.
# Each entry:
#   (sprite_size, border_px, border_color, glow_rgba, pulse_secs,
#    name_color, label, label_color, loom_px, flourish)
_THREAT_TIERS = {
    'trivial':   (50,  1, '#4a4a4a', '',                      0,   '#9e9e9e', '',          '#9e9e9e',  0, 0),
    'normal':    (64,  2, '#666666', '',                      0,   '#F44336', '',          '#F44336',  0, 0),
    'tough':     (74,  2, '#FF9800', 'rgba(255,152,0,0.5)',   0,   '#FFB74D', 'TOUGH',     '#FFB74D',  0, 0),
    'dangerous': (84,  3, '#FF5722', 'rgba(255,87,34,0.6)',   2.0, '#FF7043', 'DANGEROUS', '#FF7043',  0, 1),
    'deadly':    (92,  3, '#FF1744', 'rgba(255,23,68,0.72)',  1.5, '#FF5252', 'DEADLY',    '#FF5252',  0, 1),
    'champion':  (96,  3, '#FFD54F', 'rgba(255,213,79,0.75)', 1.6, '#FFD54F', '',          '#FFD54F',  0, 2),
    'legendary': (120, 3, '#BA68C8', 'rgba(186,104,200,0.8)', 1.4, '#CE93D8', 'LEGENDARY', '#CE93D8', 44, 3),
    'boss':      (150, 4, '#FF1744', 'rgba(255,23,68,0.85)',  1.2, '#FF5252', 'BOSS',      '#FFD54F', 76, 4),
}


def _classify_monster_threat(monster, player=None):
    """Pick a threat tier key for `monster` relative to `player`."""
    props = getattr(monster, 'properties', None) or {}
    if props.get('is_zots_guardian') or props.get('is_platino') or props.get('is_bug_queen'):
        return 'boss'
    if props.get('is_legendary'):
        return 'legendary'
    if props.get('is_champion'):
        return 'champion'
    # Everything else scales with how far the monster outclasses the player.
    diff = 0
    if player is not None:
        diff = getattr(monster, 'level', 1) - getattr(player, 'level', 1)
    if diff <= -4:
        return 'trivial'
    if diff <= 1:
        return 'normal'
    if diff <= 3:
        return 'tough'
    if diff <= 6:
        return 'dangerous'
    return 'deadly'


def get_monster_threat_style(monster, player=None):
    """Difficulty-scaled styling for a monster's combat panel.

    Returns a dict the combat renderers drop straight into the panel HTML:
      tier         - threat tier key (e.g. 'normal', 'champion', 'boss')
      sprite_size  - canvas px for generate_monster_sprite_html()
      panel_css    - border + glow + pulse to inject into #monster_panel style
      name_color   - color for the monster name text
      label_html   - pre-styled threat badge (may be '')
      loom_px      - px the sprite towers above its panel (0 = no loom)
      looming      - bool: this tier mounts the JS over-the-HUD overlay
      slot_css     - style for the sprite's flow slot (caps its layout height
                     so the loom doesn't eat the panel budget below it)
      roompanel_loom_css - style for the fixed-200px .room-panel (combat / flee):
                     bottom-anchors the boxes + overflow:visible (no margin --
                     the overlay is out of flow, so the map never moves)
      growbox_loom_css - style for the spell view's growing container
      row_align    - flex align-items for the monster row ('flex-start' when
                     looming so the text sits up top, clearing the dice)
      flourish     - entrance-drama level 0-4 (see _THREAT_TIERS)
    """
    tier = _classify_monster_threat(monster, player)
    (size, border_px, border_color, glow, pulse,
     name_color, label, label_color, loom_px, flourish) = _THREAT_TIERS[tier]
    panel_css = f"border: {border_px}px solid {border_color};"
    if glow:
        panel_css += f" --tg: {glow}; box-shadow: 0 0 11px var(--tg);"
    if pulse:
        # Inline animation overrides the stylesheet's combatIn entrance, so
        # replay it here alongside the pulse to keep the pop-in.
        panel_css += f" animation: combatIn 250ms ease-out, threatPulse {pulse}s ease-in-out infinite;"
    label_html = ''
    if label:
        label_html = (
            f'<span style="font-size:8px;font-weight:bold;color:{label_color};'
            f'border:1px solid {label_color};border-radius:3px;padding:0 3px;'
            f'margin-left:4px;vertical-align:middle;letter-spacing:0.5px;">{label}</span>'
        )
    slot_css = ''
    roompanel_loom_css = ''
    growbox_loom_css = ''
    row_align = 'center'
    looming = loom_px > 0
    if looming:
        # The sprite renders at full size but only its bottom (size - loom) px
        # take flow height; the rest spills upward out of the slot.  A JS
        # overlay (mounted by generate_monster_sprite_html with loom=True)
        # promotes a copy to a fixed top layer (z-index above the HUD), so the
        # towering part paints OVER the stats bar -- like the spell/damage
        # effects.  Because the overlay is out of flow, NOTHING in the layout
        # moves: the map stays exactly where a normal fight puts it.
        slot_h = max(32, size - loom_px)
        slot_css = f"height:{slot_h}px;width:{size}px;position:relative;overflow:visible;"
        # Bottom-anchor the boxes inside the fixed 200px panel so the in-flow
        # part of the sprite sits snug above the player box (no wasted gap).
        roompanel_loom_css = "display:flex; flex-direction:column; justify-content:flex-end; overflow:visible;"
        growbox_loom_css = "overflow:visible;"
        # With a big sprite, pin the name/HP text to the TOP of the box so the
        # roll dice have clear room below them.
        row_align = 'flex-start'
    return {
        'tier': tier,
        'sprite_size': size,
        'panel_css': panel_css,
        'name_color': name_color,
        'label_html': label_html,
        'loom_px': loom_px,
        'looming': looming,
        'slot_css': slot_css,
        'roompanel_loom_css': roompanel_loom_css,
        'growbox_loom_css': growbox_loom_css,
        'row_align': row_align,
        'flourish': flourish,
    }


def _combat_anim_token():
    """A token that changes only when a NEW monster fight begins.

    Combat re-renders every turn, but the entrance flourish + vibration should
    fire just once.  The JS compares this token to window.__combatAnimTok and
    plays the flourish only when it changed, so re-renders within the same
    fight are static.
    """
    if gs.active_monster is not getattr(gs, '_last_anim_monster', None):
        gs.combat_anim_token = getattr(gs, 'combat_anim_token', 0) + 1
        gs._last_anim_monster = gs.active_monster
    return gs.combat_anim_token


def wrap_monster_loom(sprite_html, threat):
    """Wrap a monster sprite so it towers above its panel for elite tiers.

    For non-loom tiers returns the sprite unchanged.  For loom tiers the sprite
    is anchored to the bottom of a height-capped slot and overflows upward (see
    get_monster_threat_style / _THREAT_TIERS).
    """
    if not sprite_html or not threat.get('loom_px'):
        return sprite_html
    return (
        f'<div style="{threat["slot_css"]}">'
        f'<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);">'
        f'{sprite_html}</div></div>'
    )


def generate_player_sprite_html(race, gender, equipped_armor=None, character_name=None, sprite_pid=None):
    """Wrapper that resolves armor state, then delegates to sprite_data.

    Precedence:
      1. `sprite_pid` (player picked at character creation) — render that
         exact avatar.
      2. `character_name` (auto-pick) — pool is seeded by
         (race, gender, character_name) so a fresh character gets a
         stable-but-unique look.
      3. neither — legacy Player1 16x16 sheet keyed by (race, armor_state)
         for old-save compat.
    """
    if equipped_armor is None or getattr(equipped_armor, 'is_broken', False):
        armor_state = 'none'
    elif is_metal_item(equipped_armor):
        armor_state = 'metal'
    else:
        armor_state = 'nonmetal'
    seed = (race, gender, character_name) if character_name else None
    return _generate_player_sprite_html(race, armor_state, seed=seed, sprite_pid=sprite_pid)

def can_cast_spells(player_character):
    """
    Check if player has the ability to cast spells.
    Returns True if player has: 
    - Max mana > 0 (requires Intelligence > 15)
    - Max spell slots > 0 (requires Intelligence > 15)
    """
    return gs.player_character.max_mana > 0 and gs.player_character.get_max_memorized_spell_slots() > 0


# Shared list-builders for the vendor shop screen. Both the buy/sell view and
# the repair/identify view render the same "Vendor Wares" + "Your Inventory"
# panels; only the player-row tap prefix differs between them.
_INV_PANEL_OPEN = ("<div style='overflow-y: auto; border: 1px solid #444; "
                   "padding: 3px; border-radius: 3px; max-height: 200px;'>")


def _render_tappable_row(html, item_str, cmd_str):
    """Append one inventory row -- tappable when cmd_str is set, else plain."""
    if cmd_str:
        return html + (
            f"<div class='taprow' data-zcmd='{cmd_str}' "
            f"onclick=\"window.__zotTap('{cmd_str}', this)\">"
            f"{item_str}"
            f"</div>"
        )
    return html + f"<div style='margin: 2px 0; padding: 4px 0;'>{item_str}</div>"


def _render_vendor_wares_html():
    """Build the 'Vendor Wares' panel; rows are tappable only in buy mode."""
    sorted_vendor_items = get_sorted_inventory(gs.active_vendor.inventory)
    html = "<h3 style='margin: 0 0 5px 0;'>Vendor Wares</h3>" + _INV_PANEL_OPEN
    if not sorted_vendor_items:
        html += "<div style='margin: 2px 0; padding: 0;'>(Out of stock)</div>"
    else:
        tappable = (gs.vendor_action == 'buy')
        for i, item in enumerate(sorted_vendor_items):
            item_str = format_item_for_display(item, gs.player_character, show_price=True, is_sell_price=False, for_vendor=True)
            html = _render_tappable_row(html, item_str, f"b{i + 1}" if tappable else "")
    return html + "</div>"


def _render_player_inv_html(tap_prefix):
    """Build the 'Your Inventory' panel; rows are tappable when tap_prefix set."""
    sorted_player_items = get_sorted_inventory(gs.player_character.inventory)
    html = "<h3 style='margin: 0 0 5px 0;'>Your Inventory</h3>" + _INV_PANEL_OPEN
    if not sorted_player_items:
        html += "<div style='margin: 2px 0; padding: 0;'>(Empty)</div>"
    else:
        for i, item in enumerate(sorted_player_items):
            item_str = format_item_for_display(item, gs.player_character, show_price=True, is_sell_price=True)
            html = _render_tappable_row(html, item_str, f"{tap_prefix}{i + 1}" if tap_prefix else "")
    return html + "</div>"


def _room_glyph_css(room):
    """Return (glyph, color_css) for one discovered room on the map.

    Shared by both zoom levels so a room always looks the same whether
    it's a 19px overview dot or a 36px tappable tile."""
    content = room.room_type
    if content == '#' and room.properties.get('ore_vein_detected'):
        # Detected ore vein (dwarves, or humans with Stonelore):
        # distinct glyph + amber tint
        return '%', "color: #B8860B;"
    if content == '#':
        return content, "color: #555;"
    if content == '.':
        return content, "color: #888;"
    if content in ['E', 'D', 'U']:
        return content, "color: #4CAF50;"
    if content == 'V':
        return content, "color: #FFD700;"
    if content == 'M':
        # Monster room - red
        if room.properties.get('is_champion'):
            return content, "color: #FF0000; font-weight: bold; text-shadow: 0 0 3px #FF0000;"
        return content, "color: #F44336;"
    if content == 'W':
        # Wandering monster - orange to distinguish from M
        return content, "color: #FF9800;"
    if content == 'C':
        if room.properties.get('is_legendary'):
            return content, "color: #FFD700; font-weight: bold; text-shadow: 0 0 3px #FFD700;"
        return content, "color: #03A9F4;"
    if content == 'A':
        return content, "color: #FFEB3B;"
    if content == 'P':
        if room.properties.get('is_ancient'):
            return content, "color: #00FFFF; font-weight: bold; text-shadow: 0 0 3px #00FFFF;"
        return content, "color: #03A9F4;"
    if content == 'L':
        if room.properties.get('has_codex'):
            return content, "color: #FFD700; font-weight: bold; text-shadow: 0 0 3px #FFD700;"
        return content, "color: #E040FB;"
    if content == 'N':
        if room.properties.get('is_master'):
            return content, "color: #FFD700; font-weight: bold; text-shadow: 0 0 3px #FFD700;"
        return content, "color: #CE93D8;"  # Light purple for locked dungeons (distinct from M red and W orange)
    if content == 'T':
        if room.properties.get('is_cursed'):
            return content, "color: #E040FB; font-weight: bold; text-shadow: 0 0 3px #E040FB;"
        return content, "color: #8B4513;"  # Brown for tombs
    if content == 'G':
        if room.properties.get('has_world_tree'):
            return content, "color: #00FF00; font-weight: bold; text-shadow: 0 0 3px #00FF00;"
        if room.properties.get('is_fey_garden'):
            return content, "color: #FF00FF; font-weight: bold; text-shadow: 0 0 3px #FF00FF;"
        return content, "color: #4CAF50;"  # Green for magical gardens
    if content == 'O':
        return content, "color: #E040FB;"  # Purple for oracle rooms
    if content == 'B':
        return content, "color: #FF8C00;"  # Orange for blacksmith
    if content == 'F':
        return content, "color: #87CEEB;"  # Sky blue for shrine
    if content == 'Q':
        return content, "color: #39FF14;"  # Neon green for alchemist lab
    if content == 'K':
        return content, "color: #CD5C5C;"  # Indian red for war room
    if content == 'X':
        return content, "color: #D4A017;"  # Gold/amber for taxidermist
    if content == 'Z':
        # Puzzle room (Zotle)
        return content, "color: #E040FB; font-weight: bold; text-shadow: 0 0 3px #E040FB;"
    return content, "color: #DDD;"


# Map zoom levels (cycled by the hud chip). Levels 0-1 are player-centered
# viewports; level 2 shows the whole floor. Cell footprints are sized so
# each level fits a 360px phone edge to edge:
#   0 close: 8x8 @ 42px (~358px) -- thumb-sized rooms, the default
#   1 mid:  12x12 @ 27px (~354px) -- tactical view, still tappable
#   2 full: whole floor @ 19px   -- strategic overview
# Tuples: (view_cols, view_rows, cell_px, font_px)
_MAP_ZOOM_LEVELS = (
    (8, 8, 42, 26),
    (12, 12, 27, 18),
)
_FULL_CELL_PX = 19


def _grid_cell_html(room, x, y, is_player, is_target, cell_px, font_px, tappable,
                    frontier=False):
    """Render one map cell. Discovered non-wall cells become tap-to-travel
    targets (cmd 'g:x,y'); modes without travel just swallow the command.

    The cell backgrounds are DRAWN by the procedural cavern renderer on a
    canvas beneath these spans (see cavern_render.py) — spans stay
    transparent and carry only the glyph, the tap handler, and the player
    marker. '.' and '#' glyphs are dropped: the drawn floor and rock
    texture carry that information now.

    `frontier` marks an undiscovered cell adjacent to a known room: it
    stays visually BLANK (fog is fog) but is tappable, so exploration is
    also just "tap where you want to go" (final travel step enters it)."""
    cell_style = (
        f"display: inline-block; width: {cell_px}px; height: {cell_px}px; "
        f"line-height: {cell_px}px; text-align: center; vertical-align: top; "
        f"font-family: monospace; font-size: {font_px}px;"
    )
    content = "&nbsp;"
    tap_attrs = ""
    if room.discovered or is_player:
        content, glyph_css = _room_glyph_css(room)
        cell_style += glyph_css
        if is_player:
            cell_style += "background-color: #DDD; color: #000; font-weight: bold; border-radius: 3px;"
        elif room.room_type == '#':
            content = "&nbsp;"  # the drawn rock field IS the wall
        else:
            if room.room_type == '.':
                content = "&nbsp;"  # the drawn floor IS the room
            else:
                cell_style += ("font-weight: bold; "
                               "text-shadow: 0 1px 2px #000, 0 0 5px #000;")
            if tappable:
                cell_style += "cursor: pointer;"
                tap_attrs = (
                    f" data-zcmd='g:{x},{y}'"
                    f" onclick=\"window.__zotTap('g:{x},{y}', this)\""
                )
        if is_target and not is_player:
            cell_style += "outline: 2px solid #FFD700; outline-offset: -2px;"
    elif frontier and tappable:
        # Undiscovered: blank. No dot, no art -- just a silent tap zone.
        cell_style += "cursor: pointer;"
        tap_attrs = (
            f" data-zcmd='g:{x},{y}'"
            f" onclick=\"window.__zotTap('g:{x},{y}', this)\""
        )
        if is_target:
            cell_style += "outline: 2px solid #FFD700; outline-offset: -2px;"
    return f'<span class="zmap-cell" style="{cell_style}"{tap_attrs}>{content}</span>'


def _is_frontier(floor, x, y):
    """True for an undiscovered cell adjacent to a discovered non-wall room
    — i.e. a place the player can plausibly step next to explore."""
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < floor.cols and 0 <= ny < floor.rows:
            n = floor.grid[ny][nx]
            if n.discovered and n.room_type != floor.wall_char:
                return True
    return False


def _cell_entrance_mask(floor, x, y):
    """Which cardinal neighbours of (x, y) are open (N=1 E=2 S=4 W=8).

    A neighbour counts as open unless it is a KNOWN wall — undiscovered
    neighbours render as an opening into darkness, which doubles as the
    tappable-frontier cue."""
    mask = 0
    for bit, dx, dy in ((1, 0, -1), (2, 1, 0), (4, 0, 1), (8, -1, 0)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < floor.cols and 0 <= ny < floor.rows:
            n = floor.grid[ny][nx]
            if not (n.discovered and n.room_type == floor.wall_char):
                mask |= bit
    return mask


def generate_grid_html(floor, player_x, player_y):
    """Generate the HTML for the dungeon grid/map display.

    Three zoom levels, cycled by gs.map_zoom_level (the map hud chip):

      - 0 close / 1 mid: player-centered viewports (_MAP_ZOOM_LEVELS).
        Every discovered room is a touch target: tapping queues
        tap-to-travel ('g:x,y' -> BFS walk, see process_command). Dim
        chevrons mark edges where the floor continues beyond the view.
      - 2 full: the whole grid at 19px cells. Rooms stay tappable
        (travel works from the overview too), just smaller.
    """
    target = getattr(gs, 'travel_target', None)
    level = getattr(gs, 'map_zoom_level', 0)

    windowed = level < len(_MAP_ZOOM_LEVELS)
    if not windowed:
        view_cols, view_rows = floor.cols, floor.rows
        col0 = row0 = 0
        cell_px, font_px = _FULL_CELL_PX, 15
    else:
        v_cols, v_rows, cell_px, font_px = _MAP_ZOOM_LEVELS[level]
        view_cols = min(v_cols, floor.cols)
        view_rows = min(v_rows, floor.rows)
        col0 = max(0, min(player_x - view_cols // 2, floor.cols - view_cols))
        row0 = max(0, min(player_y - view_rows // 2, floor.rows - view_rows))

    grid_html = (
        '<div style="text-align: center; max-width: 100%; overflow-x: auto; margin: 0 auto;">'
        '<div style="background-color: #222; display: inline-block; padding: 3px; '
        'border-radius: 4px; max-width: 100%; position: relative;">'
        '<canvas id="mapbg" style="position:absolute; left:3px; top:3px; z-index:0;"></canvas>'
    )
    # Spec for the procedural cavern renderer: one entry per DRAWN cell
    # (fog cells are omitted — the container's dark bg shows through).
    # k: 1=floor 2=wall; m: entrance mask; t: room-type letter for the
    # theme color cast; cx/cy: viewport-local col/row.
    cells_spec = []
    for r_idx in range(row0, row0 + view_rows):
        grid_html += f'<div style="height: {cell_px}px; white-space: nowrap;">'
        for c_idx in range(col0, col0 + view_cols):
            room = floor.grid[r_idx][c_idx]
            _is_player_cell = (r_idx, c_idx) == (player_y, player_x)
            if room.discovered or _is_player_cell:
                entry = {'x': c_idx, 'y': r_idx,
                         'cx': c_idx - col0, 'cy': r_idx - row0}
                if room.room_type == floor.wall_char:
                    entry['k'] = 2
                else:
                    entry['k'] = 1
                    entry['m'] = _cell_entrance_mask(floor, c_idx, r_idx)
                    if room.room_type != '.':
                        entry['t'] = room.room_type
                cells_spec.append(entry)
            grid_html += _grid_cell_html(
                room, c_idx, r_idx,
                is_player=_is_player_cell,
                is_target=(target == (c_idx, r_idx)),
                cell_px=cell_px, font_px=font_px, tappable=True,
                frontier=(not room.discovered
                          and _is_frontier(floor, c_idx, r_idx)),
            )
        grid_html += "</div>"
    grid_html += "</div></div>"

    _seed = ((gs.player_character.z if gs.player_character else 0) * 31 + 7)
    draw_js = (
        '<script>(function(){if(window._cavernDraw)window._cavernDraw('
        f'"mapbg",{json.dumps(cells_spec, separators=(",", ":"))},'
        f'{view_cols},{view_rows},{cell_px},{_seed});}})();</script>'
    )

    # Fixed-size slot: the map occupies the SAME footprint at every zoom
    # level (sized for the largest layout), so cycling zoom never shifts
    # the chips/log around it. The grid centers inside the slot.
    return (
        f"<div class='mvslot'>"
        f"<div class='mvframe'><div class='mvmap'>{grid_html}</div></div>"
        f"</div>{draw_js}"
    )



# --------------------------------------------------------------------------------
# 22. UI - TOGA APPLICATION
# --------------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Mode layout dispatch table used by update_button_panel().
#
# Maps prompt_cntl -> callable(self, commands_text) that builds the right
# button layout for that mode.  A sentinel _EMPTY_LAYOUT means the mode
# wants no buttons rendered (e.g., game_loaded_summary — just the big
# tappable "Continue" card in the HTML).
#
# Kept outside the class so it's easy to scan and maintain as new modes
# land.  The callables accept `self` (the app) and the raw commands_text
# string; they pull whatever they need (parsed commands, etc.) themselves.
# ---------------------------------------------------------------------------
_EMPTY_LAYOUT = object()  # sentinel — "render no buttons for this mode"

MODE_LAYOUTS = {
    'intro_story':           lambda self, cmds: self.build_main_menu_layout(),
    'main_menu':              lambda self, cmds: self.build_main_menu_layout(),
    'game_loaded_summary':    _EMPTY_LAYOUT,
    'game_loop':              _EMPTY_LAYOUT,  # in-body tap-to-move + HUD chips
    'save_load_mode':         lambda self, cmds: self.build_save_load_layout({}),
    'player_name':            _EMPTY_LAYOUT,  # body owns the HTML keyboard
    'starting_shop':          _EMPTY_LAYOUT,  # body owns BUY ALL / EXIT chips
    'vendor_shop':            _EMPTY_LAYOUT,  # body owns EXIT chip + tabs
    'puzzle_mode':            _EMPTY_LAYOUT,  # body owns the HTML keyboard + chips
    'zotle_teleporter_mode':  _EMPTY_LAYOUT,  # body owns the HTML numpad
    'combat_mode':            _EMPTY_LAYOUT,  # body owns ATTACK/CAST/INVENTORY/FLEE chips
}

# Modes that hide the entire bottom panel — the body owns all input
# (taps on the map + HUD chips). Reclaiming the ~116px of bottom_panel
# gives the map and log every pixel they can use.
_MODES_NO_BOTTOM_PANEL = frozenset({
    'game_loop', 'player_name', 'puzzle_mode',
    'starting_shop', 'vendor_shop',
    'combat_mode', 'combat_victory',
    'inventory',
    # Splash + intro + character creation + game-over: full-bleed
    # body owns the entire screen, no toga panel needed.
    'splash', 'intro_story', 'main_menu', 'death_screen',
    'game_loaded_summary',
    'player_race', 'player_gender', 'player_sprite', 'player_cantrips',
    'tourist_depth',
    'confirm_quit',
    # Map-view room modes — body owns d-pad + HUD chips via
    # _build_map_hud_and_dpad_html().
    'chest_mode', 'pool_mode', 'library_mode',
    'tomb_mode', 'garden_mode', 'oracle_mode',
    'stairs_up_mode', 'stairs_down_mode',
    'fey_garden_mode', 'dungeon_mode', 'dungeon_unlocked_mode',
    'blacksmith_mode', 'shrine_mode', 'alchemist_mode',
    'war_room_mode', 'taxidermist_mode', 'towel_action_mode',
    # Vendor-style or forced-choice modes (no map d-pad needed but the
    # toga panel is invisible and the body owns all interaction).
    'altar_mode', 'warp_mode',
    # List-picker modes — already render their items as taprows; the
    # toga numpad / command buttons were the only thing in the bottom
    # panel and they're invisible anyway.
    'spell_casting_mode', 'spell_memorization_mode',
    'crafting_mode', 'sell_quantity_mode',
    'journal_mode', 'character_stats_mode', 'stat_allocation_mode',
    'save_load_mode',
    'flare_direction_mode', 'library_read_decision_mode',
    'flee_direction_mode', 'foresight_direction_mode',
    'upgrade_scroll_mode', 'identify_scroll_mode',
    'zotle_teleporter_mode',
    # Orb of Zot endgame — the nested Wizard's Castle owns the whole body.
    'orb_game',
})

# Modes where pressing 'l' triggers the quick-use lantern hotkey.
# These all show "l = lantern" in their hint line today.
_LANTERN_QUICK_USE_MODES = frozenset({
    'game_loop', 'chest_mode', 'pool_mode', 'altar_mode', 'library_mode',
    'stairs_up_mode', 'stairs_down_mode', 'dungeon_mode', 'tomb_mode',
    'garden_mode', 'oracle_mode', 'puzzle_mode',
})

# Modes that need the 0-9 numpad grid rendered.  After the full tap-first
# pass, only the Zotle teleporter still needs it (for x,y,z coord
# entry).  All other filter-style modes drive item selection via
# .taprow cards instead.  Adding a new mode here opts it back in.
_MODES_WITH_NUMPAD = frozenset()

# Modes that need the input_field + SEND + backspace row rendered.
# Text-entry screens only — used to also include zotle_teleporter_mode +
# puzzle_mode + player_name, but those have moved to body-only HTML
# flows.  Empty for now; kept as a frozenset so future modes can opt in.
_MODES_WITH_INPUT_FIELD = frozenset()

# Modes where tap-to-travel (map tap 'g:x,y') is honoured: the map is
# visible AND walking away is part of the room's verb set (the removed
# tap-triangles used to be the touch affordance for exactly that).
# Travel steps call move_player directly — NOT the mode's command
# table, where direction letters double as room verbs ('s' at an altar
# means sacrifice) — and _travel_step closes the room dialogs a manual
# move would have closed.  Everywhere else a map tap is swallowed
# silently — combat, flee, aiming modes (flare/mine/foresight), warp
# y/n prompts, etc.
_TRAVEL_MODES = frozenset({
    'game_loop',
    'chest_mode', 'pool_mode', 'library_mode', 'altar_mode',
    'dungeon_mode', 'dungeon_unlocked_mode', 'tomb_mode',
    'garden_mode', 'fey_garden_mode', 'oracle_mode',
    'blacksmith_mode', 'shrine_mode', 'alchemist_mode',
    'war_room_mode', 'taxidermist_mode', 'shard_vault_mode',
    'towel_action_mode', 'vault_warp_mode',
    'stairs_up_mode', 'stairs_down_mode',
    # Vendors are pathfinding-passable (b486): travel entering a 'V' room
    # flips to the shop view for one step, then walks on out.
    'vendor_shop',
})


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

        # Launch the WebView tap-bridge poll loop.  Item rows in the HTML
        # side call window.__zotTap(cmd) on click; this task drains the
        # queue and feeds commands back into process_command() so players
        # can tap an inventory item instead of typing its number.
        try:
            self.add_background_task(self._poll_webview_bridge)
        except Exception:
            try:
                import asyncio
                self.loop.call_soon(
                    lambda: asyncio.ensure_future(self._poll_webview_bridge())
                )
            except Exception:
                pass

        # Schedule transition from splash to intro after 5 seconds
        import threading
        def _end_splash():
            # Only advance if we're still on the splash. A tap on "Enter the
            # Cavern" cancels this timer, but if the tap and the timer race the
            # timer thread may already be mid-flight -- without this guard a
            # late fire would clobber whatever state the player advanced into
            # (the story page, or even character creation) back to intro_story.
            if gs.prompt_cntl != "splash":
                return
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
        gs.log_line_delays = []

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
                           m_limits=gs.m_limits_val,
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
        gs.curing_kit_stocked = False  # First F9+ vendor stocks the Curing Kit
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
        gs.dwarf_mines_per_floor = {}
        gs.pending_tomb_guardian_reward = None
        
        # Initialize quest tracking for Orb of Zot
        
        gs.runes_obtained = {
            'battle': False, 'treasure': False, 'devotion': False, 'reflection': False,
            'knowledge': False, 'secrets': False, 'eternity': False, 'growth': False
        }
        gs.altar_piety = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0}
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

        # Orb of Zot endgame — fresh run, cavern is open.
        gs.cavern_sealed = False
        gs.orb_escaped = False
        gs.orb_escape_code = None
        gs.orb_game = None
        
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
            placeholder="",
            on_confirm=self.on_input_confirm,
            style=Pack(width=90, margin=2, height=28, font_size=12,
                       background_color='#2a2a2a', color='#EEE')
        )

        # Note: iOS keyboard will be disabled AFTER window is shown
        # See disable_ios_keyboard() method called in startup()

        # Permanent backspace button (always visible)
        self.backspace_button = toga.Button(
            "\u232b",
            on_press=lambda w: self.number_pad_backspace(),
            style=Pack(margin=2, width=44, height=28, font_size=13,
                       background_color='#333', color='#EEE')
        )

        self.submit_button = toga.Button(
            "SEND",
            on_press=self.on_command_submit,
            style=Pack(margin=2, width=64, height=28, font_size=12, font_weight='bold',
                       background_color='#444', color='#FFF')
        )

        # Leading spacer pushes compact input field + buttons to the right edge.
        # When input goes full-width (name entry), input_field flex=1 squeezes this to 0.
        self.input_row_spacer = toga.Box(style=Pack(flex=1))

        self.input_row = toga.Box(
            style=Pack(direction=ROW, margin=2, height=32, background_color='#1a1a1a'),
            children=[
                self.input_row_spacer,
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
            # Append letter to input field, capped at 12 chars to fit the slate.
            current = self.input_field.value or ""
            if len(current) < 12:
                self.input_field.value = current + letter_to_add
            self._haptic('tap')
            # Re-render so the gold name slate in the HTML body updates.
            self.render()
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
            self._haptic('tap')
            # Re-render to show the letter
            self.render()
            return

        # Every command button press gets a light haptic.  Dangerous
        # commands additionally get the 'arm' pulse inside
        # _check_confirm_commit on the first tap.
        self._haptic('tap')
        
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

                except Exception:
                    pass
                    import traceback
                    traceback.print_exc()
                    
        except Exception:
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
                decor = activity.getWindow().getDecorView()
                root = decor.getRootView()
                self._hide_toolbar_recursive(root)
            except Exception:
                pass

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
        """Manage placeholder text on the (now hidden) input_field.

        The toga input_field is no longer rendered for player_name — the
        body owns the typing flow — but we still use input_field.value
        as the source of truth for the typed name.  Do NOT clear it
        here: render() runs every keystroke, and clearing on every
        render would erase the letter the polling intercept just added.
        """
        if gs.prompt_cntl == 'player_name':
            self.input_field.placeholder = "Type your name..."
        else:
            self.input_field.placeholder = ""

    def _move_input_widgets_to(self, target_box, add_to_target=True):
        """Relocate input widgets to target_box (or orphan them if add_to_target=False).

        In numpad filter modes the input_field/⌫/SEND live inside the numpad's
        last row; in other modes they live in input_row. This helper handles
        the reparenting gracefully no matter where the widgets currently are.
        """
        widgets = [self.input_row_spacer, self.input_field,
                   self.backspace_button, self.submit_button]
        # Detach from any current parent.
        for w in widgets:
            parent = getattr(w, 'parent', None)
            if parent is None or parent is target_box:
                continue
            try:
                parent.remove(w)
            except Exception:
                pass
        if not add_to_target:
            return
        # Add (in order) to the target box.
        current_children = list(target_box.children)
        for w in widgets:
            if w not in current_children:
                try:
                    target_box.add(w)
                except Exception:
                    pass

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

        # -------------------------------------------------------------------
        # Per-mode UI surface flags.
        #
        #   wants_numpad      — render the 0-9 digit grid.  After the full
        #                       tap-first pass only the Zotle teleporter
        #                       needs this (x,y,z coord entry).
        #   wants_input_field — render the input_field + SEND + backspace
        #                       row below the button panel.  Text-entry
        #                       modes only.
        #
        # The "numpad inline" layout still fires when BOTH are true AND
        # needs_numbers is set, because build_layout_with_numpad packs
        # the input widgets into the numpad's 4th row.
        # -------------------------------------------------------------------
        wants_numpad = gs.prompt_cntl in _MODES_WITH_NUMPAD
        wants_input_field = gs.prompt_cntl in _MODES_WITH_INPUT_FIELD
        _numpad_inline = wants_numpad and needs_numbers and gs.prompt_cntl not in (
            'player_name', 'puzzle_mode',
            'save_load_mode', 'intro_story', 'main_menu',
            'game_loaded_summary', 'combat_mode',
        )
        if _numpad_inline:
            # Input widgets live inside build_layout_with_numpad's 4th row;
            # input_row itself is collapsed.
            self._move_input_widgets_to(self.input_row, add_to_target=False)
            self.input_row.style.height = 0
        elif wants_input_field:
            # Input widgets live in their dedicated input_row.
            self._move_input_widgets_to(self.input_row, add_to_target=True)
        else:
            # Pure tap-first mode: orphan the input widgets and collapse
            # input_row entirely so the reclaimed ~32px goes to the game
            # view.  Toga is happy having these widgets detached; they'll
            # be re-parented when we land in a text-entry mode.
            self._move_input_widgets_to(self.input_row, add_to_target=False)
            self.input_row.style.height = 0

        # Compact input row buttons (remove Android Material insets that clip text)
        self._compact_android_button(self.submit_button)
        self._compact_android_button(self.backspace_button)
        self._style_android_button(self.submit_button, bg_start='#555555', bg_end='#383838',
                                    pressed_start='#383838', pressed_end='#222222',
                                    border_color='#666666')
        self._style_android_button(self.backspace_button)

        # Adjust panel heights based on the mode + surface flags.  The
        # three QWERTY/numpad text-entry modes keep their old generous
        # heights; pure tap-first modes claw back the ~32px input_row.
        _field_base = dict(margin=2, font_size=12,
                           background_color='#2a2a2a', color='#EEE')
        # Default: command-hint line is the standard ~14px tall; the
        # no-bottom-panel branch below collapses it to 0 when the body
        # owns all input. Reset every render so transitioning out of
        # game_loop restores the label.
        self.commands_label.style.height = 14
        if gs.prompt_cntl in _MODES_NO_BOTTOM_PANEL or gs.prompt_cntl.startswith('journal_'):
            # No bottom panel at all — the HTML body owns all controls
            # (tap-to-move on the map, HUD chips for inventory/lantern).
            # Collapse everything so the web_view claims the full screen.
            self.bottom_panel.style.height = 0
            self.button_panel.style.height = 0
            self.commands_label.style.height = 0
        elif _numpad_inline:
            # Numpad with input inline on the last row; input_row empty.
            # Button panel holds 4 numpad rows × 30px + margins.
            self.bottom_panel.style.height = 132
            self.button_panel.style.height = 128
        elif wants_input_field:
            # Teleporter-style: separate numpad + separate input row.
            self.input_row_spacer.style.flex = 1
            self.input_field.style = Pack(width=90, height=28, **_field_base)
            self.input_row.style.height = 32
            self.bottom_panel.style.height = 158
            self.button_panel.style.height = 98
        else:
            # Pure tap-first mode: 3 rows × 30px command buttons, no
            # input row.  Reclaims the 32px that used to host the
            # input_field + SEND + backspace.
            self.bottom_panel.style.height = 116
            self.button_panel.style.height = 96

        # Mode-specific layout dispatch.  MODE_LAYOUTS (defined below)
        # maps prompt_cntl -> a callable that builds the right button
        # layout.  Three special cases are still resolved in-line:
        #   - inventory with no filter uses a bespoke 3x3 grid; with a
        #     filter it falls through to build_layout_with_numpad.
        #   - game_loaded_summary wants zero buttons; it returns None
        #     from the table, which we treat as "no-op".
        #   - everything else is the generic numpad/no-numpad builder
        #     keyed off needs_numbers.
        # Modes that hide the bottom panel entirely don't need any toga
        # buttons built — bottom_panel.height is already 0.  Skip the
        # inventory special case + the MODE_LAYOUTS dispatch for them.
        if gs.prompt_cntl in _MODES_NO_BOTTOM_PANEL or gs.prompt_cntl.startswith('journal_'):
            return

        if gs.prompt_cntl == 'inventory' and not gs.inventory_filter:
            self.build_inventory_layout()
            return

        layout_fn = MODE_LAYOUTS.get(gs.prompt_cntl)
        if layout_fn is _EMPTY_LAYOUT:
            return  # Mode explicitly wants no buttons rendered.
        if layout_fn is not None:
            layout_fn(self, commands_text)
            return

        # Generic fallback: parse commands out of the hint line and hand
        # off to the appropriate builder.  After the tap-first pass only
        # wants_numpad modes get the digit grid — everything else falls
        # back to the plain 3x3 command-button layout even if the hint
        # line advertises digits (the digit keyboard shortcuts still
        # work for hardware-keyboard players).
        commands = self.parse_commands(commands_text)
        if needs_numbers and wants_numpad:
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

        # Filter (Equip/Eat/Use) is now handled by segmented tabs inside
        # the WebView inventory panel — those Toga buttons are gone.
        # Row layout:
        #   Row 1: Journal | Craft | Spells
        #   Row 2: Exit | -- | Quit
        #   Row 3: -- | Save&Quit | --
        row1 = [
            flex_btn('j', 'Journal'),
            flex_btn('c', 'Craft'),
            flex_btn('m', 'Spells') if can_cast else flex_spacer(),
        ]
        row2 = [
            flex_btn('x', 'Exit'),
            flex_spacer(),
            flex_btn('q', 'Quit') if not in_combat else flex_spacer(),
        ]
        # Save & Quit lives in row 3 (out of combat only — can't save in combat).
        sq_btn = flex_btn('sq', 'Save&Quit') if not in_combat else flex_spacer()
        row3 = [flex_spacer(), sq_btn, flex_spacer()]

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
            df_armed = self._is_armed('df')
            df_label = 'Tap!' if df_armed else 'Heal'
            df_bg = '#8B0000' if df_armed else '#2a3a2a'
            df_fg = '#FFF' if df_armed else '#4CAF50'
            df_btn = toga.Button(
                df_label, on_press=lambda w: self.quick_command('df', 'Heal'),
                style=Pack(width=48, margin=1, font_size=9, font_weight='bold',
                           background_color=df_bg, color=df_fg, height=34))
            self._compact_android_button(df_btn)
            if df_armed:
                self._style_android_button(df_btn, bg_start='#C62828', bg_end='#8B0000',
                                            pressed_start='#8B0000', pressed_end='#5B0000',
                                            border_color='#FF6F6F')
            else:
                self._style_android_button(df_btn, bg_start='#2a3a2a', bg_end='#1a2a1a',
                                            border_color='#4CAF50')
            left_col.add(df_btn)
        # Altar sacrifice button
        if is_altar and 's' in cmd_dict:
            sac_armed = self._is_armed('s')
            sac_label = 'Tap!' if sac_armed else 'Sac'
            sac_bg = '#8B0000' if sac_armed else '#383838'
            sac_fg = '#FFF' if sac_armed else '#FFD700'
            # Armed state auto-submits (single-tap confirm); unarmed state
            # follows the historical behavior of buffering 's' into the
            # input field so it plays nicely with any keyboard chording.
            if sac_armed:
                sac_on_press = lambda w: self.quick_command('s', 'Sac')
            else:
                sac_on_press = lambda w: self.number_pad_input('s')
            sac_btn = toga.Button(
                sac_label, on_press=sac_on_press,
                style=Pack(width=48, margin=1, font_size=10, font_weight='bold',
                           background_color=sac_bg, color=sac_fg, height=34))
            self._compact_android_button(sac_btn)
            if sac_armed:
                self._style_android_button(sac_btn, bg_start='#C62828', bg_end='#8B0000',
                                            pressed_start='#8B0000', pressed_end='#5B0000',
                                            border_color='#FF6F6F')
            else:
                self._style_android_button(sac_btn)
            left_col.add(sac_btn)
        left_col.add(toga.Box(style=Pack(flex=1)))  # bottom spacer

        # Right column: 3x3 numpad + a 4th row that merges [0] with the input
        # widgets (field / backspace / send) inline — reclaims the separate
        # input_row of vertical space.  update_button_panel orphans the input
        # widgets before calling us, so we just re-style and add them to the
        # new numpad row here.
        # Re-style the input widgets to sit flush with the numpad row.
        self.input_field.style = Pack(flex=1, margin=1, height=30, font_size=12,
                                      background_color='#2a2a2a', color='#EEE')
        self.backspace_button.style = Pack(margin=1, width=44, height=30,
                                           font_size=13, background_color='#333',
                                           color='#EEE')
        self.submit_button.style = Pack(margin=1, width=64, height=30,
                                        font_size=12, font_weight='bold',
                                        background_color='#444', color='#FFF')
        self._compact_android_button(self.submit_button)
        self._compact_android_button(self.backspace_button)
        self._style_android_button(self.submit_button, bg_start='#555555', bg_end='#383838',
                                    pressed_start='#383838', pressed_end='#222222',
                                    border_color='#666666')
        self._style_android_button(self.backspace_button)

        numpad_rows = [
            [self.create_numpad_button('1'), self.create_numpad_button('2'), self.create_numpad_button('3')],
            [self.create_numpad_button('4'), self.create_numpad_button('5'), self.create_numpad_button('6')],
            [self.create_numpad_button('7'), self.create_numpad_button('8'), self.create_numpad_button('9')],
            [
                self.create_numpad_button('0'),
                self.input_field,
                self.backspace_button,
                self.submit_button,
            ],
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

    def _build_empty_room_panel_html(self):
        """Placeholder room card for plain floor tiles.

        Special rooms (chest, tomb, pool, etc.) render their own
        room-panel above the map.  When the player is on a plain tile
        the slot would otherwise collapse, jumping the map vertically.
        This returns a thin info card (floor + flavor + lantern fuel)
        so the layout stays stable.

        Flavor line is generated deterministically from the player's
        floor + position (see ``flavor.empty_room_flavor``) so it stays
        consistent until the player moves.
        """
        from .flavor import empty_room_flavor
        ch = gs.player_character
        seed = ch.z * 73856093 ^ ch.x * 19349663 ^ ch.y * 83492791
        flavor = empty_room_flavor(seed)

        # Lantern fuel readout if equipped/owned -- one-liner so it
        # never grows the card much.
        lantern = None
        for item in ch.inventory.items:
            if isinstance(item, Lantern):
                lantern = item
                break
        lantern_line = ""
        if lantern is not None:
            fuel = lantern.fuel_amount
            color = "#4CAF50" if fuel > 5 else ("#FFD700" if fuel > 2 else "#F44336")
            lit = " (lit)" if getattr(lantern, 'is_lit', False) else ""
            lantern_line = (
                f'<div style="margin-top: 6px; color: #BBB; font-size: 13px;">'
                f'Lantern: <span style="color: {color};">fuel {fuel}</span>{lit}'
                f'</div>'
            )

        return (
            '<div class="room-panel" style="width: 100%; padding: 10px 12px; '
            'border: 1px solid #444; border-radius: 4px; background: #1c1c1c;">'
            f'<div style="color: #FFD27A; font-size: 13px; letter-spacing: 1px; '
            f'text-transform: uppercase; margin-bottom: 5px;">'
            f'Floor {ch.z + 1}'
            '</div>'
            f'<div style="color: #DDD; font-size: 14px; line-height: 1.4;">{flavor}</div>'
            f'{lantern_line}'
            '</div>'
        )

    def _build_map_hud_and_dpad_html(self):
        """Return (hud_chips_html, '') for any map-view mode.

        Used by game_loop and the room-interaction modes (chest, pool,
        altar, library, oracle, tomb, garden, etc.).  Movement now
        lives on map-edge tap zones (see generate_grid_html), so the
        d-pad return slot is always empty — kept for backwards
        compatibility with the templates that still interpolate
        {bigdpad_html}.
        """
        from .sprites.identifiables import render_item_icon
        floor = gs.my_tower.floors[gs.player_character.z]
        here = floor.grid[gs.player_character.y][gs.player_character.x]
        lantern_item = next(
            (it for it in gs.player_character.inventory.items if isinstance(it, Lantern)),
            None,
        )

        chips = []
        if here.room_type == 'U':
            chips.append(
                "<div class='hudchip stairs' data-zcmd='u' "
                "onclick=\"window.__zotTap('u', this)\">&#9650; UP</div>"
            )
        elif here.room_type == 'D':
            chips.append(
                "<div class='hudchip stairs' data-zcmd='d' "
                "onclick=\"window.__zotTap('d', this)\">&#9660; DOWN</div>"
            )
        chips.append(
            "<div class='hudchip' data-zcmd='i' "
            "onclick=\"window.__zotTap('i', this)\">INVENTORY</div>"
        )
        # Rest: pass one turn in place (world ticks, monsters move, you don't)
        chips.append(
            "<div class='hudchip' data-zcmd='rest' "
            "onclick=\"window.__zotTap('rest', this)\">REST</div>"
        )
        # Map zoom cycle: close (8x8) -> mid (12x12) -> whole floor.
        # Label names what the NEXT tap does.
        _zoom_labels = {0: "ZOOM OUT", 1: "FULL MAP", 2: "ZOOM IN"}
        zoom_label = _zoom_labels.get(getattr(gs, 'map_zoom_level', 0), "ZOOM IN")
        chips.append(
            f"<div class='hudchip' data-zcmd='zm' "
            f"onclick=\"window.__zotTap('zm', this)\">{zoom_label}</div>"
        )
        if lantern_item is not None:
            # Bigger sprite (size=32) so the lantern is actually readable
            # in the chip.
            lantern_icon = render_item_icon(lantern_item, size=32)
            chips.append(
                f"<div class='hudchip lantern lantern-icon' data-zcmd='l' "
                f"onclick=\"window.__zotTap('l', this)\">{lantern_icon}</div>"
            )
        hud_chips_html = "<div class='hudchips'>" + "".join(chips) + "</div>"
        return hud_chips_html, ""

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
        """Create a larger button for important combat actions.

        If cmd_key is armed for two-tap confirmation, the button flips to
        a red "Tap again!" state so the player sees the pending confirm.
        """
        armed = self._is_armed(cmd_key)
        display_label = 'Tap again!' if armed else cmd_label
        bg_flat = '#8B0000' if armed else '#444'
        text_color = '#FFF'
        btn = toga.Button(
            display_label,
            on_press=lambda w, k=cmd_key, l=cmd_label: self.quick_command(k, l),
            style=Pack(margin=1, font_size=12, font_weight='bold', width=100, height=30,
                       background_color=bg_flat, color=text_color)
        )
        self._compact_android_button(btn)
        if armed:
            self._style_android_button(btn, bg_start='#C62828', bg_end='#8B0000',
                                        pressed_start='#8B0000', pressed_end='#5B0000',
                                        border_color='#FF6F6F')
        else:
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
        self._haptic('tap')

    def number_pad_backspace(self):
        """Handle backspace on number pad."""
        current = self.input_field.value
        if current:
            self.input_field.value = current[:-1]
        self.input_field.focus()
        self._haptic('tap')
    
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
            self._force_quit()
            return

        # Process the command using your existing game logic
        self.process_command(cmd)

        # Check if game should quit (e.g. after death screen)
        if gs.game_should_quit:
            self.render()
            self._force_quit()
            return

        # Re-render the display
        self.render()
        
        # Keep focus on input
        self.input_field.focus()

    async def _poll_webview_bridge(self, *args, **kwargs):
        """Drain tap commands posted from the WebView (tappable item rows).

        The HTML shell exposes window.__zotTap(cmd) which pushes onto
        window.__zotCmds.  We poll every ~120ms, read-and-clear the queue
        via evaluate_javascript, and feed each command into the normal
        process_command()/render() path — same effect as typing the
        command on the numpad and hitting SEND.
        """
        import asyncio
        import json as _json
        # Let startup settle before we start polling
        try:
            await asyncio.sleep(0.5)
        except Exception:
            return
        drain_js = (
            "(function(){"
            "var q=(window.__zotCmds||[]).slice();"
            "window.__zotCmds=[];"
            "return JSON.stringify(q);"
            "})()"
        )
        while True:
            try:
                await asyncio.sleep(0.12)
            except Exception:
                break
            if getattr(gs, 'game_should_quit', False):
                break
            res = None
            try:
                res = self.web_view.evaluate_javascript(drain_js)
                if hasattr(res, '__await__'):
                    res = await res
                elif hasattr(res, 'result'):
                    try:
                        res = res.result
                    except Exception:
                        res = None
            except Exception:
                continue
            if not res:
                continue
            if isinstance(res, bytes):
                try:
                    res = res.decode('utf-8')
                except Exception:
                    continue
            cmds = []
            try:
                cmds = _json.loads(res)
            except Exception:
                try:
                    cmds = _json.loads(_json.loads(res))
                except Exception:
                    cmds = []
            if not cmds:
                continue
            for cmd in cmds:
                if not cmd:
                    continue
                try:
                    cmd_str = str(cmd)
                    # Name-entry HTML controls: backspace and send pseudo-cmds
                    # are handled here so the typed name lives in input_field
                    # and gets submitted as a real command on SEND.
                    if gs.prompt_cntl == 'player_name':
                        if cmd_str == '__nm_bs':
                            current = self.input_field.value or ""
                            self.input_field.value = current[:-1]
                            self._haptic('tap')
                            self.render()
                            continue
                        if cmd_str.startswith('__nm_k_') and len(cmd_str) == 8:
                            # In-body QWERTY letter tap: __nm_k_<a-z>.
                            letter = cmd_str[-1]
                            if letter.isalpha():
                                current = self.input_field.value or ""
                                if len(current) < 12:
                                    self.input_field.value = current + letter.upper()
                                self._haptic('tap')
                                self.render()
                            continue
                        if cmd_str == '__nm_send':
                            cmd_str = (self.input_field.value or "").strip()
                            if not cmd_str:
                                continue
                            self.input_field.value = ""
                    if gs.prompt_cntl == 'zotle_teleporter_mode':
                        if cmd_str.startswith('__tp_d_') and len(cmd_str) == 8:
                            digit = cmd_str[-1]
                            if digit.isdigit():
                                self.input_field.value = (self.input_field.value or "") + digit
                                self._haptic('tap')
                                self.render()
                            continue
                        if cmd_str == '__tp_comma':
                            self.input_field.value = (self.input_field.value or "") + ","
                            self._haptic('tap')
                            self.render()
                            continue
                        if cmd_str == '__tp_bs':
                            cur = self.input_field.value or ""
                            self.input_field.value = cur[:-1]
                            self._haptic('tap')
                            self.render()
                            continue
                        if cmd_str == '__tp_send':
                            cmd_str = (self.input_field.value or "").strip()
                            if not cmd_str:
                                continue
                            self.input_field.value = ""
                    if gs.prompt_cntl == 'puzzle_mode':
                        if cmd_str.startswith('__pz_k_') and len(cmd_str) == 8:
                            # In-body QWERTY letter tap: __pz_k_<a-z>.
                            letter = cmd_str[-1].upper()
                            if letter.isalpha() and gs.zotle_puzzle:
                                for i in range(5):
                                    if not gs.zotle_puzzle['current_guess'][i]:
                                        gs.zotle_puzzle['current_guess'][i] = letter
                                        break
                                self._haptic('tap')
                                self.render()
                            continue
                        if cmd_str == '__pz_bs':
                            if gs.zotle_puzzle:
                                for i in range(4, -1, -1):
                                    if gs.zotle_puzzle['current_guess'][i]:
                                        gs.zotle_puzzle['current_guess'][i] = ''
                                        break
                            self._haptic('tap')
                            self.render()
                            continue
                        if cmd_str == '__pz_send':
                            # Empty cmd to process_puzzle_action submits
                            # the assembled guess (see room_actions.py:3421).
                            cmd_str = ''
                    self.process_command(cmd_str)
                    if getattr(gs, 'game_should_quit', False):
                        return
                    self.render()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Haptic feedback + two-tap commit
    # ------------------------------------------------------------------
    _CONFIRM_WINDOW_SEC = 3.0

    def _force_quit(self):
        """Really terminate the app.

        Toga's main_window.close() doesn't actually kill the process on
        mobile — on Android the Activity finishes but the JVM/Python
        host can linger, and on iOS programmatic exit is typically a
        no-op via close().  We layer platform-native calls plus an
        os._exit(0) fallback so "Quit" always closes the game.
        """
        import sys
        # Android: tell the activity to finishAndRemoveTask so the app
        # disappears from the recents list too, then nuke the JVM.
        if sys.platform == 'android':
            try:
                from android import activity as _android_activity
                try:
                    _android_activity.finishAndRemoveTask()
                except Exception:
                    try:
                        _android_activity.finish()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                from java.lang import System as _JavaSystem
                _JavaSystem.exit(0)
            except Exception:
                pass
        # Toga's own close + app-level exit hooks (run cleanup handlers).
        try:
            self.main_window.close()
        except Exception:
            pass
        try:
            self.exit()
        except Exception:
            pass
        # Last resort: hard terminate the Python process on every platform.
        try:
            import os
            os._exit(0)
        except Exception:
            pass

    def _init_ios_haptics(self):
        """Lazy-init iOS UIFeedbackGenerator instances via rubicon.

        Creates one UIImpactFeedbackGenerator per style (light/medium/heavy)
        plus a UINotificationFeedbackGenerator.  Calling prepare() warms
        the Taptic Engine so the first buzz isn't delayed.
        """
        import sys
        if sys.platform != 'ios':
            return
        if getattr(self, '_ios_haptic_ready', False):
            return
        try:
            from rubicon.objc import ObjCClass
            UIImpactFeedbackGenerator = ObjCClass('UIImpactFeedbackGenerator')
            UINotificationFeedbackGenerator = ObjCClass('UINotificationFeedbackGenerator')
            # UIImpactFeedbackStyle: 0=light, 1=medium, 2=heavy
            self._ios_haptic_light = UIImpactFeedbackGenerator.alloc().initWithStyle_(0)
            self._ios_haptic_medium = UIImpactFeedbackGenerator.alloc().initWithStyle_(1)
            self._ios_haptic_heavy = UIImpactFeedbackGenerator.alloc().initWithStyle_(2)
            self._ios_haptic_notif = UINotificationFeedbackGenerator.alloc().init()
            for g in (self._ios_haptic_light, self._ios_haptic_medium,
                      self._ios_haptic_heavy, self._ios_haptic_notif):
                try:
                    g.prepare()
                except Exception:
                    pass
            self._ios_haptic_ready = True
        except Exception:
            self._ios_haptic_ready = False

    def _haptic(self, pattern='tap'):
        """Fire a haptic buzz.

        iOS path: UIImpactFeedbackGenerator / UINotificationFeedbackGenerator
        via rubicon (WKWebView doesn't expose navigator.vibrate on iOS).
        Android / desktop path: navigator.vibrate() through evaluate_javascript.
        """
        import sys
        if sys.platform == 'ios':
            try:
                self._init_ios_haptics()
                if getattr(self, '_ios_haptic_ready', False):
                    # UINotificationFeedbackType: 0=success, 1=warning, 2=error
                    if pattern == 'tap':
                        self._ios_haptic_light.impactOccurred()
                        self._ios_haptic_light.prepare()
                    elif pattern == 'arm':
                        self._ios_haptic_notif.notificationOccurred_(1)  # warning
                        self._ios_haptic_notif.prepare()
                    elif pattern == 'confirm':
                        self._ios_haptic_notif.notificationOccurred_(0)  # success
                        self._ios_haptic_notif.prepare()
                    elif pattern == 'deny':
                        self._ios_haptic_notif.notificationOccurred_(2)  # error
                        self._ios_haptic_notif.prepare()
                    else:
                        self._ios_haptic_medium.impactOccurred()
                        self._ios_haptic_medium.prepare()
                    return
            except Exception:
                pass  # fall through to JS path

        # Android / desktop: navigator.vibrate via WebView
        patterns = {
            'tap':     '8',              # quick button press
            'arm':     '[30,60,30]',     # "armed, tap again to confirm"
            'confirm': '40',              # solid commit buzz
            'deny':    '[10,40,10,40]',   # denial / error
        }
        p = patterns.get(pattern, '8')
        try:
            js = f"if(window.navigator&&navigator.vibrate)navigator.vibrate({p});"
            res = self.web_view.evaluate_javascript(js)
            _ = res  # fire-and-forget: don't await
        except Exception:
            pass

    def _relative_save_time(self, iso_str):
        """Render a save-timestamp ISO string as a short relative phrase
        ("just now", "5m ago", "3h ago", "2d ago", "3w ago", or finally
        the raw date).  Defensive: falls back to the first 10 chars on
        any parse failure so the UI never breaks on an old / corrupt
        timestamp format."""
        if not iso_str or iso_str == 'Unknown':
            return 'Unknown'
        try:
            from datetime import datetime
            saved = datetime.fromisoformat(iso_str)
            # timestamps are naive local time (datetime.now().isoformat())
            now = datetime.now()
            seconds = int((now - saved).total_seconds())
            if seconds < 0:
                # Clock skew or future timestamp — just show the date.
                return saved.strftime('%Y-%m-%d')
            if seconds < 45:
                return 'just now'
            if seconds < 3600:
                m = max(1, seconds // 60)
                return f"{m}m ago"
            if seconds < 86400:
                h = seconds // 3600
                return f"{h}h ago"
            if seconds < 604800:
                d = seconds // 86400
                return f"{d}d ago"
            if seconds < 2592000:
                w = seconds // 604800
                return f"{w}w ago"
            return saved.strftime('%Y-%m-%d')
        except Exception:
            return iso_str[:10] if isinstance(iso_str, str) else 'Unknown'

    def _is_armed(self, cmd_key):
        """True if cmd_key is currently armed for confirmation.

        Used by button factories to swap label/colour so an armed
        action visually screams "tap again to confirm".
        """
        import time
        if not cmd_key:
            return False
        armed_cmd = getattr(self, '_armed_cmd', None)
        if armed_cmd != str(cmd_key).strip().lower():
            return False
        armed_at = getattr(self, '_armed_at', 0.0)
        if (time.time() - armed_at) > self._CONFIRM_WINDOW_SEC:
            return False
        return True

    def _dangerous_cmd_label(self, cmd):
        """If this command is destructive in the current context, return a
        human label for the confirm prompt; otherwise None."""
        c = (cmd or '').strip().lower()
        # 'q' already has its own y/n confirm flow (confirm_quit prompt).
        if c == 'df':
            return 'Drink potions to full'
        # Flee is NOT armed for two-tap confirm: it's a defensive escape, not
        # an irreversible act, and choosing a flee direction (with FIGHT to
        # cancel) is already a natural confirm. The extra "tap again" made
        # every escape attempt feel like three taps.
        if c == 's' and gs.prompt_cntl == 'altar_mode':
            return 'Sacrifice at the altar'
        # Save-overwrite commands (o1/o2/o3) destroy the existing save in
        # that slot — always ask twice.
        if c in ('o1', 'o2', 'o3') and gs.prompt_cntl == 'save_load_mode':
            return f'Overwrite save slot {c[1]}'
        # Save-delete commands (d1/d2/d3) are irreversible; arm twice too.
        # Available from both in-game save menu and the launch-screen
        # main menu.
        if c in ('d1', 'd2', 'd3') and gs.prompt_cntl in (
            'save_load_mode', 'main_menu', 'intro_story'
        ):
            return f'Delete save slot {c[1]}'
        return None

    def _check_confirm_commit(self, cmd):
        """Two-tap commit gate.

        Returns True when the command should execute now, False to hold
        it back (arming state).  Non-dangerous commands clear any pending
        arm silently so a stray tap elsewhere doesn't surprise-commit the
        next time the user presses a dangerous button.
        """
        import time
        label = self._dangerous_cmd_label(cmd)
        norm = (cmd or '').strip().lower()
        now = time.time()
        armed_cmd = getattr(self, '_armed_cmd', None)
        armed_at = getattr(self, '_armed_at', 0.0)
        # Expire stale arming
        if armed_cmd and (now - armed_at) > self._CONFIRM_WINDOW_SEC:
            armed_cmd = None
            self._armed_cmd = None
        if label is None:
            # Non-dangerous command — clear pending arm
            if armed_cmd:
                self._armed_cmd = None
            return True
        if armed_cmd == norm:
            # Confirmed — execute
            self._armed_cmd = None
            self._haptic('confirm')
            return True
        # Arm it, ask for second tap
        self._armed_cmd = norm
        self._armed_at = now
        add_log(f"{COLOR_YELLOW}Tap again within 3s to confirm: {label}{COLOR_RESET}")
        self._haptic('arm')
        return False

    def process_command(self, cmd):

        # cmd is already passed in and processed by on_command_submit

        if gs.game_should_quit:
            return

        # Orb of Zot endgame owns ALL input while active — the nested
        # Wizard's Castle has its own command vocabulary and must not be
        # intercepted by the global single-key handlers (q/v/m/i/etc.).
        if gs.prompt_cntl == "orb_game":
            from . import orb_game as _orb
            _orb.process_orb_command(self, cmd)
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

        # Two-tap commit gate for destructive commands.  Runs after the
        # special-case modes above (splash / death_screen / confirm_quit)
        # have their own flows, but before the main command dispatch.
        if not self._check_confirm_commit(cmd):
            return

        # Any explicit player input cancels an in-flight tap-to-travel;
        # travel's own steps call move_player directly, never this method,
        # so this only ever fires on real taps/keys.
        gs.travel_target = None

        # Map tap: 'g:<x>,<y>' queues tap-to-travel toward that room.
        # Only honoured in modes with free movement; the map also renders
        # in combat/flee/etc., where a stray tap must do nothing.
        if isinstance(cmd, str) and cmd.startswith('g:'):
            if gs.prompt_cntl in _TRAVEL_MODES:
                try:
                    tx_s, ty_s = cmd[2:].split(',', 1)
                    self._start_travel(int(tx_s), int(ty_s))
                except (ValueError, AttributeError):
                    pass
            return

        # Map zoom cycle (hud chip): close -> mid -> whole floor -> close.
        if cmd == 'zm' and gs.prompt_cntl in _TRAVEL_MODES:
            gs.map_zoom_level = (getattr(gs, 'map_zoom_level', 0) + 1) % 3
            return

        # Rest (hud chip): pass one turn in place — the world ticks, you don't.
        if cmd == 'rest' and gs.prompt_cntl == "game_loop":
            from .game_systems import process_rest_turn
            process_rest_turn(gs.player_character, gs.my_tower)
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

        if cmd == 'm' and gs.prompt_cntl == "game_loop":
            # Dwarf mining: break an adjacent ore-vein wall. No per-floor
            # cap -- a vein is a finite worm, so its length is the limit.
            # Core logic lives in game_systems so the harness shares it.
            from .game_systems import dwarf_adjacent_vein_directions, can_mine_ore
            pc = gs.player_character
            if not can_mine_ore(pc):
                add_log(f"{COLOR_YELLOW}You don't know how to mine ore veins. (Dwarves do; humans can buy the Stonelore skill on the character screen.){COLOR_RESET}")
                return
            if not dwarf_adjacent_vein_directions(pc, gs.my_tower):
                add_log(f"{COLOR_YELLOW}No ore veins adjacent to mine.{COLOR_RESET}")
                return
            add_log(f"{COLOR_CYAN}Which direction to mine? (n/s/e/w, c to cancel){COLOR_RESET}")
            gs.prompt_cntl = "mine_direction_mode"
            return

        if gs.prompt_cntl == "mine_direction_mode":
            if cmd in ['n', 's', 'e', 'w']:
                from .game_systems import process_mine_action
                process_mine_action(gs.player_character, gs.my_tower, cmd)
                gs.prompt_cntl = "game_loop"
                self.render()
            elif cmd == 'c':
                add_log("Mining cancelled.")
                gs.prompt_cntl = "game_loop"
                self.render()
            else:
                add_log("Pick a direction (n/s/e/w) or 'c' to cancel.")
            return

        if cmd == 'i' and gs.prompt_cntl == "game_loop":
            gs.prompt_cntl = "inventory"
            gs.inventory_filter = None
            handle_inventory_menu(gs.player_character, gs.my_tower, "init")
            return

        # Lantern quick-use hotkey.  Allowed in any mode where the hint
        # shows "l = lantern" — game_loop + most single-action rooms.
        # game_loop is special-cased because its caller re-renders; every
        # other mode needs us to render here so the updated fuel level
        # shows up immediately.
        if cmd == 'l' and gs.prompt_cntl in _LANTERN_QUICK_USE_MODES:
            process_lantern_quick_use(gs.player_character, gs.my_tower)
            if gs.prompt_cntl != 'game_loop':
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
                # If the cavern was sealed (Orb of Zot obtained) and not yet
                # escaped, resume the nested Wizard's Castle instead of the
                # normal dungeon loop.
                from . import orb_game as _orb
                if not _orb.resume_orb_if_sealed():
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
            elif cmd == 'cp':
                # Launch the portrait picker, then return to stats screen.
                gs.player_sprite_return_to = "character_stats_mode"
                gs.prompt_cntl = "player_sprite"
            elif cmd == 'p':
                # Stat-point allocation (build 380). Open the spend menu
                # when the player has level-up points waiting. If they
                # don't, the handler logs and bounces back.
                if gs.player_character.unspent_stat_points > 0:
                    gs.prompt_cntl = "stat_allocation_mode"
                else:
                    add_log(f"{COLOR_YELLOW}You have no stat points to spend.{COLOR_RESET}")
            elif cmd.startswith('sk_'):
                # Human "Path of Ambition": buy a special skill with stat
                # points by tapping its row on the character screen. Stays
                # on this screen so the player can keep spending.
                from .game_systems import buy_human_skill
                buy_human_skill(gs.player_character, cmd[3:])
            # Invalid commands are silently ignored - prompt is in placeholder
        elif gs.prompt_cntl == "stat_allocation_mode":
            from .game_systems import process_stat_allocation_action
            process_stat_allocation_action(gs.player_character, gs.my_tower, cmd)
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
        elif gs.prompt_cntl == "player_sprite":
            create_player_character(gs.my_tower, gs.player_character, gs.prompt_cntl, cmd)
        elif gs.prompt_cntl == "tourist_depth":
            create_player_character(gs.my_tower, gs.player_character, gs.prompt_cntl, cmd)
        elif _handle(gs.my_tower, gs.player_character, cmd):
            pass
        else: # This 'else' block means gs.prompt_cntl is "game_loop" or similar map-based interaction.
            if cmd in ['n', 's', 'e', 'w']:
                # move_player returns False for both "hit a wall" and "died
                # from status effects on room entry" — and it can also flip
                # prompt_cntl to death_screen / combat_mode internally. Don't
                # second-guess the result; it already reflects the intent.
                move_player(gs.player_character, gs.my_tower, cmd)

    # ------------------------------------------------------------------
    # Tap-to-travel: tap a discovered room on the map, auto-walk there.
    # ------------------------------------------------------------------
    _TRAVEL_STEP_SEC = 0.22  # pace between auto-steps (fast walk, still readable)

    def _start_travel(self, tx, ty):
        """Validate a map tap and kick off the auto-walk toward (tx, ty)."""
        from .game_systems import find_travel_path
        pc = gs.player_character
        if pc is None or (tx, ty) == (pc.x, pc.y):
            return
        floor = gs.my_tower.floors[pc.z]
        path = find_travel_path(floor, (pc.x, pc.y), (tx, ty))
        if path is None:
            # Fog, a wall, or no safe corridor of plain rooms leads there.
            add_log(f"{COLOR_YELLOW}No clear path there.{COLOR_RESET}")
            return
        gs.travel_target = (tx, ty)
        gs.travel_floor_z = pc.z
        # Step budget: path length + slack. Confusion re-routes every step,
        # so without a cap a badly confused traveller could wander forever.
        gs.travel_steps_left = len(path) + 6
        self._travel_step()

    def _travel_step(self):
        """Walk one room toward gs.travel_target, then reschedule.

        Re-paths every step (BFS is cheap on an 18x21 grid), so warps,
        confusion stumbles, and newly revealed walls self-correct. Stops
        the moment anything interrupts: arrival, a mode change (combat,
        chest, stairs...), a failed move (webbed), floor change, or the
        step budget running out.
        """
        from .game_systems import find_travel_path
        target = getattr(gs, 'travel_target', None)
        if target is None:
            return
        pc = gs.player_character
        if (pc is None
                or gs.prompt_cntl not in _TRAVEL_MODES
                or pc.z != gs.travel_floor_z
                or gs.travel_steps_left <= 0):
            gs.travel_target = None
            return
        if (pc.x, pc.y) == target:
            gs.travel_target = None
            return
        floor = gs.my_tower.floors[pc.z]
        path = find_travel_path(floor, (pc.x, pc.y), target)
        if not path or len(path) < 2:
            gs.travel_target = None
            return
        nx, ny = path[1]
        direction = {(0, -1): 'n', (0, 1): 's', (-1, 0): 'w', (1, 0): 'e'}[
            (nx - pc.x, ny - pc.y)]
        gs.travel_steps_left -= 1
        # Step via move_player DIRECTLY — never through the mode's command
        # table, where direction letters double as room verbs ('s' at an
        # altar means SACRIFICE, 'u' at a dungeon means unlock...). Close
        # the room dialog state whose mode handlers would have closed it
        # on a manual move; walking away always dismisses a dialog.
        gs.altar_action = None
        gs.active_towel_item = None
        gs.vendor_action = None
        moved = move_player(pc, gs.my_tower, direction)
        if (not moved
                or (pc.x, pc.y) == target
                or gs.prompt_cntl not in _TRAVEL_MODES):
            gs.travel_target = None
        self.render()
        if getattr(gs, 'travel_target', None) is not None:
            import threading
            threading.Timer(
                self._TRAVEL_STEP_SEC,
                lambda: self.app.loop.call_soon_threadsafe(self._travel_step),
            ).start()

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
        # Dismiss after the full defeat timeline: opposed ATK exchange +
        # damage float + grayscale (DEFEAT_GRAYSCALE_MS) + DEFEATED flash
        # (DEFEAT_OVERLAY_MS). DEFEAT_DISMISS_MS is the single tunable knob.
        threading.Timer(gs.DEFEAT_DISMISS_MS / 1000.0,
                        lambda: self.app.loop.call_soon_threadsafe(_auto_dismiss)).start()

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
                # Land the victory sting on the kill reveal, not before it.
                # The monster greys out at DEFEAT_GRAYSCALE_MS and the
                # DEFEATED overlay flashes at DEFEAT_OVERLAY_MS; starting the
                # fanfare earlier spoils the result before the final blow lands.
                music_delay_ms = gs.DEFEAT_OVERLAY_MS + init_offset
            elif new_mood == 'death':
                music_delay_ms = 3500 + init_offset
        if mood_changed or gs.music_restart:
            gs.current_music_mood = new_mood
            gs.music_restart = False

        # Extract animation / SFX script bodies (raw JS, no <script> wrapper)
        _active_name = getattr(gs.active_monster, 'name', None) if getattr(gs, 'active_monster', None) else None
        anim_scripts = []
        for raw in (
            generate_spell_cast_js(gs.last_spell_cast),
            generate_spell_icon_visual_js(gs.last_spell_cast),
            generate_spell_particles_js(gs.last_spell_cast),
            generate_dice_roll_js(gs.last_dice_rolls),
            generate_concentration_check_js(gs.last_concentration_roll),
            generate_monster_defeat_js(gs.monster_defeated_anim),
            generate_sprite_anim_triggers_js(
                _active_name, gs.last_monster_damage, gs.last_player_damage,
                gs.last_spell_cast, gs.monster_defeated_anim,
                bool(gs.last_dice_rolls), has_init,
            ),
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
            'statsHtml': getattr(self, '_last_stats_html', '') or '',
            'bodyClass': self._body_class_for_mode(gs.prompt_cntl),
            'logLines': list(gs.log_lines),
            'logDelays': gs.consume_log_delays(),
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
        gs.loot_toast_delay_ms = 0
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

        # ORB OF ZOT ENDGAME — the body owns the entire screen (its own
        # stat strip, minimap, log and tap chips).  Blank the top stats
        # strip and the toga button panel, like splash / death do.
        if gs.prompt_cntl == "orb_game":
            from . import orb_game as _orb
            self._last_stats_html = ""
            html_code = _orb.render_orb_html(self)
            self.update_button_panel("", False)
            return html_code

        # SPLASH SCREEN - Show version and recent changes for 5 seconds
        if gs.prompt_cntl == "splash":
            # Show only the top 3 changelog entries on splash so the
            # artwork (rune archway + torch + descending stairs) is
            # visible in the middle of the screen instead of buried
            # under a tall changes panel.  Full list is still on the
            # intro/main-menu screen.
            changelog_html = ""
            for entry in CHANGELOG[:3]:
                safe_entry = entry.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                # Cap each line at ~120 chars for the splash teaser.
                if len(safe_entry) > 120:
                    safe_entry = safe_entry[:117] + '...'
                changelog_html += f'<div style="color: #DDD; font-size: 10px; margin: 2px 0; padding-left: 8px; border-left: 2px solid #2A4A6A; line-height: 1.35;">{safe_entry}</div>'

            splash_uri = _load_screen_image_b64('splash')
            html_code = f"""
                <div style="position: relative; font-family: monospace; height: 100vh;
                            box-sizing: border-box;
                            background-image: url('{splash_uri}');
                            background-size: cover;
                            background-position: center top;
                            background-repeat: no-repeat;
                            background-color: #000;
                            border-radius: 6px;
                            overflow: hidden;">
                    <!-- Lighter top gradient (lets the archway show through);
                         a stronger gradient at the very bottom so the chip is
                         legible without painting over the artwork. -->
                    <div style="position: absolute; left:0; right:0; top:0; height: 14%;
                                pointer-events: none;
                                background: linear-gradient(180deg, rgba(0,0,0,0.55) 0%,
                                            rgba(0,0,0,0) 100%);"></div>
                    <div style="position: absolute; left:0; right:0; bottom:0; height: 42%;
                                pointer-events: none;
                                background: linear-gradient(180deg, rgba(0,0,0,0) 0%,
                                            rgba(0,0,0,0.78) 60%, rgba(0,0,0,0.95) 100%);"></div>
                    <div style="position: relative; padding: 10px 14px 8px;
                                display: flex; flex-direction: column; align-items: center;
                                text-align: center; height: 100vh; box-sizing: border-box;
                                overflow: hidden;">
                        <div style="font-size: 22px; font-weight: bold; color: #FFD700;
                                    text-shadow: 0 2px 6px #000, 0 0 14px rgba(0,0,0,0.9);
                                    letter-spacing: 1px;">
                            WIZARD'S CAVERN
                        </div>
                        <div style="font-size: 11px; color: #6FD3FF; margin-top: 2px;
                                    text-shadow: 0 1px 4px #000;">
                            v{VERSION} (build {BUILD_NUMBER})
                        </div>
                        <div style="margin-top: 10px; width: 100%; max-width: 360px;
                                    background: rgba(0,0,0,0.55);
                                    border: 1px solid rgba(255,215,0,0.18);
                                    border-radius: 4px; padding: 6px 10px; text-align: left;">
                            <div style="color: #FFD27A; font-size: 10px; margin-bottom: 3px;
                                        text-transform: uppercase; letter-spacing: 1px;">
                                Latest
                            </div>
                            {changelog_html}
                        </div>
                        <div class='taprow altar-act blessing' data-zcmd=' '
                             onclick="window.__zotTap(' ', this)"
                             style='margin-top: auto; margin-bottom: 0; width: 100%; max-width: 360px;'>
                            <div class='aname'>Enter the Cavern</div>
                            <div class='ameta'>Tap to continue (or wait a few seconds)</div>
                        </div>
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
            safe_name = (gs.player_character.name or "Adventurer").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            gameover_uri = _load_screen_image_b64('gameover')

            html_code = f"""
                <div style="font-family: monospace; min-height: 78vh; display: flex;
                            flex-direction: column; align-items: center; padding: 14px 12px;
                            background: #000; border-radius: 6px;">
                    <div style="position: relative; width: 100%; max-width: 520px;
                                aspect-ratio: 1328 / 768; border-radius: 4px; overflow: hidden;
                                background-image: url('{gameover_uri}');
                                background-size: cover; background-position: center;
                                box-shadow: 0 4px 16px rgba(0,0,0,0.8);">
                        <div style="position: absolute; left: 0; right: 0; top: 6%;
                                    text-align: center; font-size: 22px; font-weight: bold;
                                    color: #FF4A4A; letter-spacing: 3px;
                                    text-shadow: 0 2px 6px #000, 0 0 16px rgba(0,0,0,0.95);">
                            GAME OVER
                        </div>
                        <div style="position: absolute; left: 0; right: 0; bottom: 4%;
                                    text-align: center; color: #EEE; font-size: 13px;
                                    text-shadow: 0 1px 4px #000;">
                            <span style="color: #FFD27A;">{safe_name}</span>
                            &mdash; fell on floor {floors_explored}
                        </div>
                    </div>

                    <div style="margin: 14px auto 0; width: 100%; max-width: 360px;
                                text-align: left; font-size: 12px; color: #CCC;
                                background: rgba(0,0,0,0.5);
                                border: 1px solid rgba(255,74,74,0.25);
                                border-radius: 4px; padding: 10px 14px;">
                        <div style="margin: 5px 0;"><b>Final Level:</b> {final_level}</div>
                        <div style="margin: 5px 0;"><b>Deepest Floor:</b> {floors_explored}</div>
                        <div style="margin: 5px 0;"><b>Gold Collected:</b> {final_gold}</div>
                        <div style="margin: 5px 0;"><b>Monsters Slain:</b> {gs.game_stats.get('monsters_killed', 0)}</div>
                        <div style="margin: 5px 0;"><b>Spells Cast:</b> {gs.game_stats.get('spells_cast', 0)}</div>
                    </div>

                    <div class='taprow altar-act reforge' data-zcmd=' '
                         onclick="window.__zotTap(' ', this)"
                         style='margin-top: 12px; width: 100%; max-width: 360px;'>
                        <div class='aname'>Close Game</div>
                        <div class='ameta'>Saves will be wiped &mdash; permadeath is permanent</div>
                    </div>
                </div>
                """
            current_commands_text = "Tap Close"
            self.update_button_panel(current_commands_text, False)
            return html_code

        # Player stats - hide HP/MP during character creation and starting shop
        show_bars = gs.prompt_cntl not in ['splash', 'intro_story', 'player_name', 'player_race', 'player_gender', 'player_sprite', 'player_cantrips', 'tourist_depth', 'starting_shop']

        # Get dynamic title
        player_title = get_player_title(gs.player_character) if show_bars else ""

        # Ultra-compact stats for mobile - optimized for 393px width
        # Include x, y coordinates and player level
        if show_bars:
            hunger_color = get_hunger_color(gs.player_character.hunger)
            player_stats_html = f"""
                <div style="font-family: monospace; font-size: 12px; margin-bottom: 4px; padding: 3px; background: #1a1a1a; border-radius: 2px;">
                    <b>{gs.player_character.name}</b> Lv{gs.player_character.level} | F{gs.player_character.z + 1} ({gs.player_character.x},{gs.player_character.y}) | {gs.player_character.gold}g | {gs.player_character.experience}xp<br>
                    HP:{health_bar_html(_p_display_hp, gs.player_character.max_health, width=70)} MP:{mana_bar_html(gs.player_character.mana, gs.player_character.max_mana, width=70)} <span style="color:{hunger_color};">H:{gs.player_character.hunger}</span>
                </div>
            """
        else:
            player_stats_html = f"""
                <div style="font-family: monospace; font-size: 12px; margin-bottom: 4px; padding: 3px; background: #1a1a1a; border-radius: 2px;">
                    <b>{gs.player_character.name}</b>
                </div>
            """

        # Stash for wrap_html (which renders the fixed top strip with
        # stats + log) and blank the inline copy so 35 per-mode template
        # interpolations stop rendering a duplicate stats bar inside
        # the scrollable content area.
        self._last_stats_html = player_stats_html
        player_stats_html = ""

        if gs.prompt_cntl == "intro_story" or gs.prompt_cntl == "main_menu":
            # MAIN MENU / INTRO STORY SCREEN — tappable slot cards.
            # The big gold NEW GAME card sends 'n' to start fresh; each
            # populated save slot card sends its digit to load.
            saves = SaveSystem.list_saves()
            has_saves = any(not s['empty'] for s in saves)

            save_slots_html = (
                "<div class='taprow save-new' data-zcmd='n' "
                "onclick=\"window.__zotTap('n', this)\">"
                "<div class='sname'>NEW GAME</div>"
                "<div class='smeta'>A fresh descent into the Cavern</div>"
                "</div>"
            )
            if has_saves:
                save_slots_html += (
                    "<div style='color: #888; font-size: 12px; text-align:center; margin: 10px 0 6px 0; letter-spacing:1px;'>"
                    "&mdash; OR CONTINUE &mdash;"
                    "</div>"
                )
                armed_mm = getattr(self, '_armed_cmd', None)
                for save in saves:
                    slot = save['slot']
                    if not save['empty']:
                        info = save['info']
                        rel = self._relative_save_time(info.get('timestamp', 'Unknown'))
                        del_cmd = f"d{slot}"
                        del_armed = (armed_mm == del_cmd)
                        del_cls = 'del-btn armed' if del_armed else 'del-btn'
                        del_label = 'TAP AGAIN TO DELETE' if del_armed else 'Delete'
                        save_slots_html += (
                            f"<div class='taprow save-populated' data-zcmd='{slot}' "
                            f"onclick=\"window.__zotTap('{slot}', this)\">"
                            f"<div class='sname'>Slot {slot}: {info['name']}</div>"
                            f"<div class='smeta'>Level {info['level']} &middot; Floor {info['floor']} &middot; {info['gold']} gold</div>"
                            f"<div class='sdate'>{rel}</div>"
                            f"<span class='slabel'>TAP TO LOAD</span>"
                            f"&nbsp;<span class='{del_cls}' data-zcmd='{del_cmd}' "
                            f"onclick=\"event.stopPropagation(); window.__zotTap('{del_cmd}', this)\">{del_label}</span>"
                            f"</div>"
                        )

            splash_uri = _load_screen_image_b64('splash')
            # Mirror the splash screen layout exactly so the rune-archway
            # artwork doesn't shift when the player taps past the splash:
            # min-height: 100vh, center-top background, thin top + thin
            # bottom gradient with the middle band fully transparent so
            # the archway/torch/stairs are clearly visible behind the
            # lore + save-slot panels.
            html_code = f"""
                        <div id="intro-tap-zone"
                             style="position: relative; font-family: monospace;
                                    font-size: 12px; padding: 0; text-align: center;
                                    cursor: pointer; height: 100vh; box-sizing: border-box;
                                    background-image: url('{splash_uri}');
                                    background-size: cover;
                                    background-position: center top;
                                    background-repeat: no-repeat;
                                    background-color: #000;
                                    border-radius: 6px;
                                    overflow: hidden;"
                             onclick="(function(){{ if(window._musicEngine){{ window._musicEngine.resume(); var s=document.getElementById('music-status'); if(s){{ s.innerHTML='&#9835; MUSIC ON &mdash; press SEND to begin'; s.style.color='#69F0AE'; }} }} }})()"
                             ontouchstart="(function(){{ if(window._musicEngine){{ window._musicEngine.resume(); var s=document.getElementById('music-status'); if(s){{ s.innerHTML='&#9835; MUSIC ON &mdash; press SEND to begin'; s.style.color='#69F0AE'; }} }} }})()">
                            <!-- Top gradient (thin, just enough for title legibility);
                                 bottom gradient (heavier, behind lore + save slots). -->
                            <div style="position: absolute; left:0; right:0; top:0; height: 14%;
                                        pointer-events: none;
                                        background: linear-gradient(180deg, rgba(0,0,0,0.55) 0%,
                                                    rgba(0,0,0,0) 100%);"></div>
                            <div style="position: absolute; left:0; right:0; bottom:0; height: 56%;
                                        pointer-events: none;
                                        background: linear-gradient(180deg, rgba(0,0,0,0) 0%,
                                                    rgba(0,0,0,0.78) 40%, rgba(0,0,0,0.95) 100%);"></div>
                            <div style="position: relative; padding: 10px 14px 8px;
                                        display: flex; flex-direction: column; align-items: center;
                                        text-align: center; height: 100%; box-sizing: border-box;
                                        overflow: hidden;">
                                <div style="font-size: 22px; font-weight: bold; color: #FFD700;
                                            text-shadow: 0 2px 6px #000, 0 0 14px rgba(0,0,0,0.9);
                                            letter-spacing: 1px;">
                                     WIZARD'S CAVERN
                                </div>
                                <div id="music-status" style="font-size: 11px; color: #FFB74D; margin-top: 4px; letter-spacing: 1px;
                                            text-shadow: 0 1px 3px #000;">
                                    &#9835; TAP THIS PANEL TO ENABLE MUSIC
                                </div>
                                <div style="margin-top: auto; width: 100%; max-width: 400px;
                                            font-size: 12px; line-height: 1.5; color: #E8E8E8;
                                            text-align: left;
                                            background: rgba(0,0,0,0.55);
                                            border: 1px solid rgba(255,215,0,0.18);
                                            border-radius: 4px; padding: 8px 12px;
                                            text-shadow: 0 1px 2px #000;">
                                    Many cycles ago, in the kingdom of Medium Earth, the gnomic wizard Zot forged his great ORB OF POWER.
                                    He soon vanished, leaving behind his vast subterranean cavern filled with esurient monsters, fabulous treasures, and the incredible ORB OF ZOT.
                                    The cavern seals behind all who enter &mdash; <span style="color: #FF6A6A;">none have ever emerged.</span>
                                    Claim the ORB OF ZOT and you alone may break the seal, and escape with all the riches you can carry.
                                </div>
                                <div style="border: 1px solid rgba(255,215,0,0.3); border-radius: 5px;
                                            padding: 8px; margin-top: 8px; margin-bottom: 0;
                                            width: 100%; max-width: 350px; flex-shrink: 0;
                                            background: rgba(0,0,0,0.65);
                                            max-height: 50vh; overflow-y: auto;">
                                    {save_slots_html}
                                </div>
                            </div>
                        </div>
                    """
            if has_saves:
                current_commands_text = "Tap New Game or a save slot"
            else:
                current_commands_text = "Tap NEW GAME to begin"

        elif gs.prompt_cntl == "game_loaded_summary":
            # LOADED GAME SUMMARY SCREEN
            loaded_char = gs._pending_load[0] if gs._pending_load else gs.player_character
            gs._pending_load[1] if gs._pending_load else gs.my_tower

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
                                    {generate_player_sprite_html(getattr(loaded_char, 'race', 'human'), getattr(loaded_char, 'gender', 'male'), getattr(loaded_char, 'equipped_armor', None), character_name=getattr(loaded_char, 'name', None), sprite_pid=getattr(loaded_char, 'sprite_pid', None))}
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

                            <div class='taprow altar-act blessing' data-zcmd=' '
                                 onclick="window.__zotTap(' ', this)"
                                 style="margin-top: 20px;">
                                <div class='aname'>Continue Your Adventure</div>
                                <div class='ameta'>Pick up where you left off</div>
                            </div>
                        </div>
                    """
            current_commands_text = "Tap Continue"
        elif gs.prompt_cntl == "save_load_mode":
            # SAVE/LOAD MENU — tappable slot cards.
            # Empty slot: tap to save here.
            # Populated slot: tap the big card to LOAD; tap the small
            # "Overwrite" micro-button to overwrite (two-tap gated).
            saves = SaveSystem.list_saves()
            armed_ovr = getattr(self, '_armed_cmd', None)

            slots_html = ""
            for save in saves:
                slot = save['slot']
                if save['empty']:
                    slots_html += (
                        f"<div class='taprow save-empty' data-zcmd='{slot}' "
                        f"onclick=\"window.__zotTap('{slot}', this)\">"
                        f"<div class='sname'>Slot {slot}: <i>Empty</i></div>"
                        f"<div class='slabel'>TAP TO SAVE HERE</div>"
                        f"</div>"
                    )
                else:
                    info = save['info']
                    timestamp = self._relative_save_time(info.get('timestamp', 'Unknown'))
                    ovr_cmd = f"o{slot}"
                    del_cmd = f"d{slot}"
                    ovr_armed = (armed_ovr == ovr_cmd)
                    del_armed = (armed_ovr == del_cmd)
                    ovr_cls = 'ovr-btn armed' if ovr_armed else 'ovr-btn'
                    del_cls = 'del-btn armed' if del_armed else 'del-btn'
                    ovr_label = 'TAP AGAIN TO OVERWRITE' if ovr_armed else 'Overwrite'
                    del_label = 'TAP AGAIN TO DELETE' if del_armed else 'Delete'
                    # event.stopPropagation so tapping a micro-button
                    # doesn't also trigger the parent LOAD.
                    slots_html += (
                        f"<div class='taprow save-populated' data-zcmd='{slot}' "
                        f"onclick=\"window.__zotTap('{slot}', this)\">"
                        f"<div class='sname'>Slot {slot}: {info['name']}</div>"
                        f"<div class='smeta'>Level {info['level']} &middot; Floor {info['floor']} &middot; {info['gold']} gold</div>"
                        f"<div class='sdate'>Saved: {timestamp}</div>"
                        f"<span class='slabel'>TAP TO LOAD</span>"
                        f"&nbsp;<span class='{ovr_cls}' data-zcmd='{ovr_cmd}' "
                        f"onclick=\"event.stopPropagation(); window.__zotTap('{ovr_cmd}', this)\">{ovr_label}</span>"
                        f"<span class='{del_cls}' data-zcmd='{del_cmd}' "
                        f"onclick=\"event.stopPropagation(); window.__zotTap('{del_cmd}', this)\">{del_label}</span>"
                        f"</div>"
                    )

            # Cancel row pinned at the bottom of the card stack.
            slots_html += (
                "<div class='taprow cancel' data-zcmd='x' "
                "onclick=\"window.__zotTap('x', this)\">"
                "<span class='tapnum'>&times;</span>Cancel</div>"
            )

            html_code = f"""
                        <div style="font-family: monospace; font-size: 12px; padding: 15px;">
                            {achievement_notifications}
                            <h2 style="color: #FFD700; text-align: center; margin-bottom: 15px;">
                                SAVE / LOAD GAME
                            </h2>
                            <div style="border: 2px solid #555; border-radius: 5px; padding: 12px; background: #1a1a1a;">
                                {slots_html}
                            </div>
                        </div>
                    """
            current_commands_text = "Tap a slot | x = cancel"

        elif gs.prompt_cntl == "player_name":
            # PLAYER NAME INPUT SCREEN — big gold slate showing the typed
            # name with a blinking cursor, plus tappable BACKSPACE / SEND
            # cards. Includes an HTML QWERTY keyboard because the toga
            # button_panel renders invisible on some devices (iOS-style
            # browsers, certain Android skins) — the body-only flow
            # works everywhere because taprows render reliably.
            typed = (self.input_field.value or "").upper()
            max_len = 13
            slot_html = ""
            for i in range(max_len):
                if i < len(typed):
                    ch = typed[i]
                    if not ch.isalpha():
                        ch = "?"
                    slot_html += f"<span class='nm-slot nm-filled'>{ch}</span>"
                elif i == len(typed):
                    slot_html += "<span class='nm-slot nm-cursor'>_</span>"
                else:
                    slot_html += "<span class='nm-slot nm-empty'>_</span>"
            has_name = len(typed) > 0
            # SEND no-ops when empty (handled by the polling-loop intercept),
            # so leave both cards visually active — users were tapping and
            # getting nothing back from the disabled state.
            send_cls = "taprow nm-send"
            bs_cls = "taprow cancel nm-bs"
            if not has_name:
                send_cls += " nm-empty"
                bs_cls += " nm-empty"

            # In-body QWERTY keyboard — letter taps fire __nm_k_<letter>
            # commands routed through the polling intercept so they append
            # to input_field.value and re-render. Layout matches the toga
            # version: 10/9/7 keys per row.
            kbd_rows = [
                ['Q','W','E','R','T','Y','U','I','O','P'],
                ['A','S','D','F','G','H','J','K','L'],
                ['Z','X','C','V','B','N','M'],
            ]
            kbd_html = ""
            for row in kbd_rows:
                row_html = ""
                for letter in row:
                    cmd = f"__nm_k_{letter.lower()}"
                    row_html += (
                        f"<div class='nm-key' data-zcmd='{cmd}' "
                        f"onclick=\"window.__zotTap('{cmd}', this)\">{letter}</div>"
                    )
                kbd_html += f"<div class='nm-kbd-row'>{row_html}</div>"

            html_code = f"""
                <style>
                  .nm-slate {{
                    font-family: 'Courier New', monospace;
                    font-size: 28px; letter-spacing: 6px; font-weight: bold;
                    text-align: center; padding: 22px 8px; margin: 14px 0 10px 0;
                    background: linear-gradient(180deg, #1a1608 0%, #0a0804 100%);
                    border: 2px solid #5a4a1a; border-radius: 6px;
                    box-shadow: 0 0 14px rgba(255,215,0,0.18) inset,
                                0 0 8px rgba(255,215,0,0.10);
                    overflow-x: auto; white-space: nowrap;
                  }}
                  .nm-slot {{ display: inline-block; min-width: 18px; }}
                  .nm-filled {{ color: #FFD700; text-shadow: 0 0 10px rgba(255,215,0,0.7); }}
                  .nm-empty  {{ color: #3a3320; }}
                  .nm-cursor {{ color: #FFD700; animation: nmblink 0.9s steps(2) infinite; }}
                  @keyframes nmblink {{ 50% {{ opacity: 0.15; }} }}
                  .nm-actions {{ display: flex; gap: 8px; margin-top: 6px; }}
                  .nm-actions .taprow {{ flex: 1; margin: 0; text-align: center;
                                          font-weight: bold; letter-spacing: 1.5px;
                                          padding: 12px 8px; font-size: 14px; }}
                  .nm-hint {{ font-size: 11px; color: #888; text-align: center;
                              margin: 2px 0 6px 0; }}
                  .nm-count {{ font-size: 10px; color: #5a5a5a; text-align: center;
                                margin-top: -4px; }}
                  .nm-actions .taprow.nm-empty {{ opacity: 0.55; }}
                  .nm-keyboard {{ margin: 14px 0 4px 0; user-select: none;
                                   -webkit-user-select: none; }}
                  /* Real-keyboard look: uniform key width, top row (10
                     keys) longest, middle (9) and bottom (7) naturally
                     taper inward via justify-content: center. */
                  .nm-kbd-row {{ display: flex; gap: 4px; justify-content: center;
                                   margin: 4px 2px; }}
                  .nm-key {{
                    flex: 0 0 32px;
                    width: 32px;
                    height: 44px;
                    line-height: 42px;
                    background: linear-gradient(180deg, #3a3a3a 0%, #1f1f1f 100%);
                    border: 1px solid #555;
                    border-radius: 5px;
                    color: #EEE;
                    font-family: 'Courier New', monospace;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                    cursor: pointer;
                    -webkit-tap-highlight-color: transparent;
                    box-shadow: 0 1px 0 #0a0a0a inset;
                    transition: transform 60ms ease-out, background 100ms ease-out;
                  }}
                  .nm-key:active {{
                    transform: scale(0.92);
                    background: linear-gradient(180deg, #5a5a5a 0%, #303030 100%);
                    box-shadow: 0 0 8px rgba(255,215,0,0.4),
                                0 1px 0 #0a0a0a inset;
                  }}
                </style>
                <div style="font-family: monospace; font-size: 12px; padding: 10px;">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 6px; color: #FFD700; text-align: center;">
                        CHARACTER CREATION
                    </div>
                    <div style="font-size: 12px; margin-bottom: 2px; color: #FFFFFF; text-align: center;">
                        What is thy name, hero?
                    </div>
                    <div class="nm-slate">{slot_html}</div>
                    <div class="nm-count">{len(typed)}/{max_len}</div>
                    <div class="nm-hint">Tap letters below to type &middot; SEND when ready</div>
                    <div class="nm-actions">
                        <div class="{bs_cls}" data-zcmd="__nm_bs"
                             onclick="window.__zotTap('__nm_bs', this)">&#9003; BACKSPACE</div>
                        <div class="{send_cls}" data-zcmd="__nm_send"
                             onclick="window.__zotTap('__nm_send', this)">SEND &#9654;</div>
                    </div>
                    <div class="nm-keyboard">{kbd_html}</div>
                </div>
                """
            current_commands_text = ""

        elif gs.prompt_cntl == "player_race":
            # PLAYER RACE SELECTION SCREEN — tappable race cards.
            # Inline style overrides bump the chip size + add strengths
            # / weaknesses breakdown so a new player sees what each
            # race actually does. Numbers track the b382 race tunings
            # (HP / stats / cast threshold / Carnivore Diet).
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; padding: 10px;">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #FFD700; text-align: center;">
                        CHARACTER CREATION
                    </div>
                    <div style="font-size: 12px; margin-bottom: 15px; color: #FFFFFF;">
                        <b>{gs.player_character.name}</b>. Really? Oooohkay.
                    </div>
                    <div style="font-size: 14px; margin-bottom: 10px; color: #FFFFFF;">
                        Choose your race:
                    </div>
                    <div class='altar-actions'>
                        <div class='taprow altar-act bless' data-zcmd='h'
                             onclick="window.__zotTap('h', this)"
                             style="padding: 14px 14px; line-height: 1.45;">
                            <div class='aname' style='font-size: 20px;'>Human</div>
                            <div class='ameta' style='font-size: 14px; margin-top: 6px; color: #CCC;'>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Balanced stats (HP 30, ATK 15, all 10s) &middot; Mind Touch cantrip</div>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Versatility: +20% XP and DOUBLE stat points &mdash; the fastest learner</div>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Path of Ambition: a 19-skill point-buy tree &mdash; specialize as a duelist, battlemage, juggernaut, or survivor</div>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Stats vs. skills is your choice &mdash; build any human you want</div>
                                <div style='color: #EF9A9A;'><b>−</b> No innate stat bonuses &mdash; your edge is the skills you choose, not your blood</div>
                            </div>
                        </div>
                        <div class='taprow altar-act mystic' data-zcmd='e'
                             onclick="window.__zotTap('e', this)"
                             style="padding: 14px 14px; line-height: 1.45;">
                            <div class='aname' style='font-size: 20px;'>Elf</div>
                            <div class='ameta' style='font-size: 14px; margin-top: 6px; color: #CCC;'>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> +2 INT, +2 DEX, +1 ATK (start INT 12, DEX 12)</div>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Starts with TWO cantrips: Hold Monster + Mind Touch</div>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Casts at INT 12+ (lowest threshold) &middot; can craft Lembas Wafers</div>
                                <div style='color: #EF9A9A;'><b>−</b> Fragile: HP 20 (-10), STR 9, DEF 4</div>
                            </div>
                        </div>
                        <div class='taprow altar-act forge' data-zcmd='d'
                             onclick="window.__zotTap('d', this)"
                             style="padding: 14px 14px; line-height: 1.45;">
                            <div class='aname' style='font-size: 20px;'>Dwarf</div>
                            <div class='ameta' style='font-size: 14px; margin-top: 6px; color: #CCC;'>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Tank: HP 60 (+30), DEF 7, ATK 17, STR 12</div>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Starts with Battleaxe (+4 ATK) instead of Dagger</div>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Carnivore Diet: +100% nutrition from meat &amp; sausages</div>
                                <div style='color: #8BC34A; margin-bottom: 2px;'><b>+</b> Unlocks dwarven-only sausages (Landjäger, Blutwurst)</div>
                                <div style='color: #EF9A9A;'><b>−</b> -2 DEX, -2 INT &middot; magic gated at INT 21+ (almost never casts)</div>
                            </div>
                        </div>
                    </div>
                </div>
                """
            current_commands_text = "Tap a race"

        elif gs.prompt_cntl == "player_gender":
            # PLAYER GENDER SELECTION SCREEN — tappable gender cards
            # with inclusive subtitle on each ("He can do anything.",
            # etc.). Chips sized to match the player_race screen.
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; padding: 10px;">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #FFD700; text-align: center;">
                        CHARACTER CREATION
                    </div>
                    <div style="font-size: 12px; margin-bottom: 15px; color: #FFFFFF;">
                        You went with <b>{gs.player_character.race.title()}</b>
                    </div>
                    <div style="font-size: 14px; margin-bottom: 10px; color: #FFFFFF;">
                        Choose your gender:
                    </div>
                    <div class='altar-actions'>
                        <div class='taprow altar-act detect' data-zcmd='m'
                             onclick="window.__zotTap('m', this)"
                             style="padding: 14px 14px; line-height: 1.45;">
                            <div class='aname' style='font-size: 20px;'>Male</div>
                            <div class='ameta' style='font-size: 14px; margin-top: 6px; color: #BBB;'>He can do anything.</div>
                        </div>
                        <div class='taprow altar-act offering' data-zcmd='f'
                             onclick="window.__zotTap('f', this)"
                             style="padding: 14px 14px; line-height: 1.45;">
                            <div class='aname' style='font-size: 20px;'>Female</div>
                            <div class='ameta' style='font-size: 14px; margin-top: 6px; color: #BBB;'>She can do anything.</div>
                        </div>
                        <div class='taprow altar-act mystic' data-zcmd='n'
                             onclick="window.__zotTap('n', this)"
                             style="padding: 14px 14px; line-height: 1.45;">
                            <div class='aname' style='font-size: 20px;'>Non-binary</div>
                            <div class='ameta' style='font-size: 14px; margin-top: 6px; color: #BBB;'>They can do anything.</div>
                        </div>
                    </div>
                </div>
                """
            current_commands_text = "Tap a gender"

        elif gs.prompt_cntl == "player_sprite":
            # PORTRAIT PICKER — scrollable grid of race-appropriate
            # avatars. Tap a card -> sends 'sp<n>' which stores the chosen
            # pid and advances to the starting shop. The pool is filtered
            # by gs.player_character.race; if no curated picks exist for
            # that race, falls back to the full _CHARACTERS_POOL.
            from .sprites.characters import get_race_pool
            from .sprites import get_image_b64
            race_pool = get_race_pool(gs.player_character.race)
            tiles = []
            for idx, pid in enumerate(race_pool, start=1):
                img_b64 = get_image_b64(pid)
                if not img_b64:
                    continue
                cmd = f"sp{idx}"
                tiles.append(
                    f"<div class='taprow altar-act' "
                    f"style='display:inline-block;width:80px;margin:4px;padding:6px;"
                    f"text-align:center;vertical-align:top;background:#222;border-radius:6px;' "
                    f"data-zcmd='{cmd}' onclick=\"window.__zotTap('{cmd}', this)\">"
                    f"<canvas id='spk_{idx}' width='64' height='64' "
                    f"style='image-rendering:pixelated;image-rendering:crisp-edges;display:block;margin:0 auto;'></canvas>"
                    f"<script>(function(){{var c=document.getElementById('spk_{idx}');"
                    f"if(!c)return;var ctx=c.getContext('2d');ctx.imageSmoothingEnabled=false;"
                    f"var img=new Image();img.onload=function(){{ctx.drawImage(img,0,0,img.naturalWidth,img.naturalHeight,0,0,64,64);}};"
                    f"img.src='data:image/webp;base64,{img_b64}';}})()</script>"
                    f"</div>"
                )
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; padding: 10px;">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 12px; color: #FFD700; text-align: center;">
                        CHARACTER CREATION
                    </div>
                    <div style="font-size: 12px; margin-bottom: 6px; color: #FFFFFF;">
                        <b>{gs.player_character.race.title()}</b> &middot; <b>{gs.player_character.gender.title()}</b>
                    </div>
                    <div style="font-size: 12px; margin-bottom: 12px; color: #FFFFFF;">
                        Pick your portrait:
                    </div>
                    <div style="max-height: 480px; overflow-y: auto; text-align: center; padding: 4px; border: 1px solid #444; border-radius: 6px;">
                        {''.join(tiles)}
                    </div>
                </div>
                """
            current_commands_text = "Tap a portrait"

        elif gs.prompt_cntl == "player_cantrips":
            # ELF CANTRIP PICKER — build-355. Four 1-MP slot-free
            # cantrips on offer (Mote/Frost Bite/Pebble/Mind Touch).
            # Player taps to toggle, confirms with the bottom button
            # once exactly two are picked.
            from .item_templates import SPELL_TEMPLATES as _ST
            cantrip_pool = [s for s in _ST if getattr(s, 'is_cantrip', False)]
            selected = set(getattr(gs, 'cantrip_selections', []))
            cards = []
            for i, spell in enumerate(cantrip_pool):
                is_picked = i in selected
                border = '2px solid #FFD700' if is_picked else '1px solid #555'
                bg = '#332b00' if is_picked else '#222'
                check = ' [PICKED]' if is_picked else ''
                # Card meta varies by cantrip kind: damage cantrips show
                # power + element, utility cantrips show their cost only
                # so a "power 0" line doesn't appear next to "Light".
                if spell.spell_type == 'damage':
                    meta = f"{spell.mana_cost} MP &middot; {spell.damage_type} &middot; power {spell.base_power}"
                else:
                    meta = f"{spell.mana_cost} MP &middot; utility"
                cmd = f"ct{i+1}"
                cards.append(
                    f"<div class='taprow altar-act' "
                    f"style='display:block;margin:6px 0;padding:8px;background:{bg};"
                    f"border:{border};border-radius:6px;text-align:left;' "
                    f"data-zcmd='{cmd}' onclick=\"window.__zotTap('{cmd}', this)\">"
                    f"<div class='aname'>{spell.name}{check}</div>"
                    f"<div class='ameta'>{spell.description}</div>"
                    f"<div class='ameta' style='color:#9CC;'>{meta}</div>"
                    f"</div>"
                )
            confirm_enabled = (len(selected) == 2)
            confirm_color = '#4CAF50' if confirm_enabled else '#555'
            confirm_text = "Confirm (x)" if confirm_enabled else f"Pick {2 - len(selected)} more"
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; padding: 10px;">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 12px; color: #FFD700; text-align: center;">
                        CANTRIPS
                    </div>
                    <div style="font-size: 12px; margin-bottom: 10px; color: #FFFFFF;">
                        Even an untrained elf carries two minor magics. Pick the pair you've practiced:
                    </div>
                    {''.join(cards)}
                    <div class='taprow altar-act' data-zcmd='x'
                         onclick="window.__zotTap('x', this)"
                         style='display:block;margin-top:10px;padding:10px;background:{confirm_color};
                         border-radius:6px;text-align:center;font-weight:bold;color:#FFF;'>
                        {confirm_text}
                    </div>
                </div>
                """
            current_commands_text = "Pick 2 cantrips"

        elif gs.prompt_cntl == "tourist_depth":
            # TOURIST DEPTH PICKER -- spawn the maxed-out Playtester at
            # F<n> instead of F1. Chips emit 'td<n>' which the
            # game_systems handler intercepts to call
            # plant_player_at_depth(). Presets cover the key tuning
            # bands: F1 (true start), F5 (early), F10/F15 (mid), F20-
            # F30 (the F30-F50-wall stress band the harness probes),
            # F35-F45 (deep), F49 (boss approach), F50 (boss arena).
            depth_presets = [
                (1,  "F1",  "True start. Same as a normal new game; no warp."),
                (5,  "F5",  "Early. First vendor tier, F5 garden / oracle content."),
                (10, "F10", "Mid. Bug-level zone, second vendor wave."),
                (15, "F15", "Mid-deep. Dungeons / tombs / dwarven sausage country."),
                (20, "F20", "Volcanic-tier gear baseline."),
                (25, "F25", "F30-wall stress band -- the b407/b408 plant depth."),
                (30, "F30", "Deep. Death Knight / Demilich / Storm Giant territory."),
                (35, "F35", "Deeper still. Tier 13-14 native horrors appear."),
                (40, "F40", "Near-endgame. Tier-9 vendor stock."),
                (45, "F45", "Pre-boss. Final shard drops."),
                (49, "F49", "One step from the gate. Quest path tested here."),
                (50, "F50", "Boss arena. Zot's Guardian -- god mode lets you cheese it."),
            ]
            chips = []
            for depth, label, blurb in depth_presets:
                cmd = f"td{depth}"
                chips.append(
                    f"<div class='taprow altar-act' data-zcmd='{cmd}' "
                    f"onclick=\"window.__zotTap('{cmd}', this)\" "
                    f"style='display:block;margin:4px 0;padding:10px 12px;"
                    f"line-height:1.35;'>"
                    f"<div class='aname' style='font-size:16px;color:#FFD700;'>{label}</div>"
                    f"<div class='ameta' style='font-size:12px;color:#BBB;'>{blurb}</div>"
                    f"</div>"
                )
            # Endgame test: plant at the boss arena (F50) AND hand the
            # Tourist the Orb of Zot directly, so the sealed-cavern endgame
            # (USE the Orb -> nested Wizard's Castle -> escape) can be
            # exercised without first grinding the Guardian.
            chips.append(
                "<div class='taprow altar-act' data-zcmd='tdorb' "
                "onclick=\"window.__zotTap('tdorb', this)\" "
                "style='display:block;margin:10px 0 4px;padding:10px 12px;"
                "line-height:1.35;border:1px solid rgba(255,210,74,0.5);"
                "background:rgba(58,42,90,0.35);'>"
                "<div class='aname' style='font-size:16px;color:#FFD24A;'>&#10024; ORB IN HAND (F50)</div>"
                "<div class='ameta' style='font-size:12px;color:#BBB;'>"
                "Boss arena, plus the Orb of Zot already in your pack. Open inventory and USE it to dive straight into the Wizard's Castle endgame.</div>"
                "</div>"
            )
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px; padding: 10px;">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px; color: #FFD700; text-align: center;">
                        TOURIST -- STARTING DEPTH
                    </div>
                    <div style="font-size: 12px; margin-bottom: 10px; color: #FFFFFF;">
                        Welcome, <b>Tourist</b>. You are armed to the teeth, infinitely buffed, and on Anthropic's dime. Where would you like to start your tour of the Cavern?
                    </div>
                    <div style="font-size: 11px; margin-bottom: 10px; color: #888; font-style: italic;">
                        F1..F&lt;N-1&gt; are pre-discovered, so you can retreat upstairs to earlier vendors immediately.
                    </div>
                    <div class='altar-actions' style="max-height: 460px; overflow-y: auto; padding-right: 4px;">
                        {''.join(chips)}
                    </div>
                </div>
                """
            current_commands_text = "Tap a depth"

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

                        <div style="border: 1px solid gold; padding: 4px; border-radius: 4px; background: #1a1a1a; max-height: 500px; overflow-y: auto; margin-bottom: 5px;">{achievements_html}</div>

                        <div style="border: 1px solid cyan; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px;">{stats_html}</div>

                        <div class='taprow cancel' data-zcmd='x'
                             onclick="window.__zotTap('x', this)">
                            <span class='tapnum'>&times;</span>Close Achievements
                        </div>
</div>
                    """
            current_commands_text = "Tap Close | x = exit"

        elif gs.prompt_cntl == "starting_shop":
            # STARTING SHOP VIEW - Match regular vendor format
            # Starting shop only offers Buy and Sell (no repair / identify).
            _s_tabs = [
                ('Buy',  'vbuy',  gs.vendor_action == 'buy'),
                ('Sell', 'vsell', gs.vendor_action == 'sell'),
            ]
            starting_tabs_html = "<div class='filtertabs'>"
            for label, cmd, is_active in _s_tabs:
                cls = 'filtertab active' if is_active else 'filtertab'
                starting_tabs_html += (
                    f"<div class='{cls}' data-zcmd='{cmd}' "
                    f"onclick=\"window.__zotTap('{cmd}', this)\">{label}</div>"
                )
            starting_tabs_html += "</div>"

            vendor_html = _render_vendor_wares_html()
            player_inv_html = _render_player_inv_html('s' if gs.vendor_action == 'sell' else '')

            vendor_html = starting_tabs_html + vendor_html

            # HTML shop chips — replace the bottom-panel 'ba' / 'x' toga
            # buttons that render invisible on some devices.
            shop_chips_html = (
                "<div class='hudchips' style='margin-top:8px;'>"
                "<div class='hudchip' data-zcmd='ba' "
                "onclick=\"window.__zotTap('ba', this)\">BUY ALL</div>"
                "<div class='hudchip exit' data-zcmd='x' "
                "onclick=\"window.__zotTap('x', this)\">EXIT</div>"
                "</div>"
            )

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
                    {shop_chips_html}
                </div>
                """
            if gs.vendor_action:
                action_label = {'buy': 'buy', 'sell': 'sell'}.get(gs.vendor_action, gs.vendor_action)
                # Tabs handle mode switching; rows are tappable in the active
                # list; hint shows just the row-select shortcut + exits.
                current_commands_text = f"# = {action_label} item | ba = buy all | x = exit"
            else:
                current_commands_text = "Tap a tab above to begin | ba = buy all | x = exit"

        elif gs.prompt_cntl == "sell_quantity_mode":
            # SELL QUANTITY MODE — tappable quick-quantity buttons.
            item = gs.pending_sell_item
            item_count = getattr(item, 'count', 1) if item else 1
            sell_price_each = (item.calculated_value // 2) if item else 0
            item_name = item.name if item else "item"

            # Build quick-pick buttons: 1, 5, 10 (when applicable), All.
            # Each shows the total gold the player gets for that qty.
            _quick_qtys = []
            for q in (1, 5, 10):
                if q <= item_count:
                    _quick_qtys.append(q)
            qty_buttons_html = "<div class='altar-actions'>"
            for q in _quick_qtys:
                qty_buttons_html += (
                    f"<div class='taprow altar-act offering' data-zcmd='{q}' "
                    f"onclick=\"window.__zotTap('{q}', this)\">"
                    f"<div class='aname'>Sell {q}</div>"
                    f"<div class='ameta'>+{q * sell_price_each} gold</div>"
                    f"</div>"
                )
            qty_buttons_html += (
                f"<div class='taprow altar-act bless' data-zcmd='a' "
                f"onclick=\"window.__zotTap('a', this)\">"
                f"<div class='aname'>Sell All ({item_count})</div>"
                f"<div class='ameta'>+{item_count * sell_price_each} gold</div>"
                f"</div>"
            )
            qty_buttons_html += (
                "<div class='taprow cancel' data-zcmd='c' "
                "onclick=\"window.__zotTap('c', this)\">"
                "<span class='tapnum'>&times;</span>Cancel</div>"
            )
            qty_buttons_html += "</div>"

            quantity_html = f"""
                <div style="border: 2px solid #DAA520; padding: 15px; border-radius: 8px; background: #1a1a1a;">
                    <div style="color: #DAA520; font-weight: bold; font-size: 16px; margin-bottom: 10px; text-align: center;">
                        How many to sell?
                    </div>
                    <div style="color: #FFF; font-size: 12px; margin-bottom: 4px; text-align: center;">
                        <b>{item_name}</b>
                    </div>
                    <div style="color: #888; font-size: 12px; margin-bottom: 8px; text-align: center;">
                        You have: {item_count} &middot; Price each: {sell_price_each}g
                    </div>
                    {qty_buttons_html}
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
            current_commands_text = f"Tap a quantity (1-{item_count} / All / Cancel)"

        elif gs.prompt_cntl == "vendor_shop":
            # SHOP VIEW
            # Segmented vendor tabs [Buy][Sell][Repair][ID] — tabs use
            # the vbuy/vsell/vrep/vid idempotent commands so re-tapping
            # the active tab is a no-op instead of toggling off.
            _v_tabs = [
                ('Buy',    'vbuy', gs.vendor_action == 'buy'),
                ('Sell',   'vsell', gs.vendor_action == 'sell'),
                ('Repair', 'vrep',  gs.vendor_action == 'repair'),
                ('ID',     'vid',   gs.vendor_action == 'identify'),
            ]
            vendor_tabs_html = "<div class='filtertabs'>"
            for label, cmd, is_active in _v_tabs:
                cls = 'filtertab active' if is_active else 'filtertab'
                vendor_tabs_html += (
                    f"<div class='{cls}' data-zcmd='{cmd}' "
                    f"onclick=\"window.__zotTap('{cmd}', this)\">{label}</div>"
                )
            vendor_tabs_html += "</div>"

            # Vendor wares: tappable "buy" targets when buy tab is active.
            vendor_html = _render_vendor_wares_html()
            # Player inventory: tappable when sell/repair/identify is active.
            _player_tap_prefix = {'sell': 's', 'repair': 'r', 'identify': 'id'}.get(gs.vendor_action, '')
            player_inv_html = _render_player_inv_html(_player_tap_prefix)

            # Prepend tabs above the wares list so the player sees them first.
            vendor_html = vendor_tabs_html + vendor_html

            vendor_sprite = generate_room_sprite_html('V', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            # Magic shop gets purple styling
            is_magic = gs.active_vendor.is_magic_shop if hasattr(gs.active_vendor, 'is_magic_shop') else False
            shop_title_color = '#c084fc' if is_magic else '#FFFFFF'
            shop_label = "Ye Olde Magic Shoppe" if is_magic else f"{gs.active_vendor.name}'s Shop"

            # HTML shop chips — vendor_shop omits BUY ALL (starting-shop
            # only feature per vendor.py:451) and just exposes EXIT so
            # the player has a visible way out when toga buttons hide.
            shop_chips_html = (
                "<div class='hudchips' style='margin-top:8px;'>"
                "<div class='hudchip exit' data-zcmd='x' "
                "onclick=\"window.__zotTap('x', this)\">EXIT</div>"
                "</div>"
            )

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
                    {shop_chips_html}
                </div>
                """
            if gs.prompt_cntl == "sell_quantity_mode":
                current_commands_text = "1-9 / a = sell | c = cancel"
            elif gs.vendor_action:
                action_label = {'buy': 'buy', 'sell': 'sell', 'repair': 'repair', 'identify': 'identify'}.get(gs.vendor_action, gs.vendor_action)
                # Tabs above drive the mode; hint shows row shortcut + exit.
                current_commands_text = f"# = {action_label} item | x = exit"
            else:
                current_commands_text = "Tap a tab above to begin | x = exit"



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
                if gs.inventory_filter == 'eat':
                    display_items = [i for i in combat_usable_items if isinstance(i, (Food, Meat))]
                elif gs.inventory_filter == 'use':
                    display_items = [i for i in combat_usable_items if isinstance(i, (Potion, Scroll))]

                # Segmented filter tabs — combat has no Equip tab (can't
                # swap gear mid-fight). 'All' sends 'b' to clear the filter.
                _cbt_tabs = [
                    ('All', 'b',   gs.inventory_filter is None),
                    ('Use', 'u',   gs.inventory_filter == 'use'),
                    ('Eat', 'eat', gs.inventory_filter == 'eat'),
                ]
                combat_tabs_html = "<div class='filtertabs'>"
                for label, cmd, is_active in _cbt_tabs:
                    cls = 'filtertab active' if is_active else 'filtertab'
                    combat_tabs_html += (
                        f"<div class='{cls}' data-zcmd='{cmd}' "
                        f"onclick=\"window.__zotTap('{cmd}', this)\">{label}</div>"
                    )
                combat_tabs_html += "</div>"

                # Build inventory HTML - matching normal inventory style
                player_inv_html = combat_tabs_html
                player_inv_html += "<div style='max-height: 280px; overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px;'>"
                player_inv_html += "<div style='margin: 0; padding: 0;'>"

                if not display_items:
                    player_inv_html += "<div style='margin: 2px 0; padding: 0; color: #888;'>(No matching items)</div>"
                else:
                    # Tap-to-act in combat: filter prefix is 'u' or 'eat'.
                    # No filter => no implicit verb, so rows stay plain text.
                    _tap_prefix = {'use': 'u', 'eat': 'eat'}.get(gs.inventory_filter, '')
                    for i, item in enumerate(display_items):
                        item_str = format_item_for_display(item, gs.player_character, show_price=False)
                        if _tap_prefix:
                            cmd_str = f"{_tap_prefix}{i + 1}"
                            player_inv_html += (
                                f"<div class='taprow' data-zcmd='{cmd_str}' "
                                f"onclick=\"window.__zotTap('{cmd_str}', this)\">"
                                f"{item_str}"
                                f"</div>"
                            )
                        else:
                            player_inv_html += (
                                f"<div style='margin: 2px 0; padding: 4px 0;'>"
                                f"{item_str}"
                                f"</div>"
                            )

                player_inv_html += "</div>"
                player_inv_html += "</div>"

                # HTML inventory chips for combat: BACK / DRINK FULL when
                # filtering, JOURNAL + CLOSE otherwise.
                _cb_chips = []
                if gs.inventory_filter:
                    if (gs.inventory_filter == 'use'
                        and gs.player_character.health < gs.player_character.max_health
                        and any(isinstance(i, Potion) and i.potion_type == 'healing'
                                for i in gs.player_character.inventory.items)):
                        _cb_chips.append(
                            "<div class='hudchip lantern' data-zcmd='df' "
                            "onclick=\"window.__zotTap('df', this)\">DRINK FULL</div>"
                        )
                    _cb_chips.append(
                        "<div class='hudchip' data-zcmd='b' "
                        "onclick=\"window.__zotTap('b', this)\">&larr; BACK</div>"
                    )
                else:
                    _cb_chips.append(
                        "<div class='hudchip' data-zcmd='j' "
                        "onclick=\"window.__zotTap('j', this)\">JOURNAL</div>"
                    )
                    _cb_chips.append(
                        "<div class='hudchip exit' data-zcmd='x' "
                        "onclick=\"window.__zotTap('x', this)\">CLOSE</div>"
                    )
                cb_inv_chips_html = (
                    "<div class='hudchips' style='margin-top:6px;'>"
                    + "".join(_cb_chips) +
                    "</div>"
                )

                # COMBAT LAYOUT - matching normal inventory structure
                html_code = f"""
                        <div style="font-family: monospace; font-size: 12px; width: 100%; max-width: 100vw; overflow-x: auto; box-sizing: border-box;">
                            <div style="min-width: 0; max-width: 100%;">
                                {achievement_notifications}
                                {player_stats_html}
                                <div style="border: 1px solid #4CAF50; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px; overflow-x: auto; max-width: 100%;">{player_inv_html}</div>
                                {cb_inv_chips_html}
                            </div>
                        </div>
                    """

                if gs.inventory_filter:
                    current_commands_text = "# = select | b = back"
                    if gs.inventory_filter == 'use' and gs.player_character.health < gs.player_character.max_health:
                        has_healing = any(isinstance(i, Potion) and i.potion_type == 'healing'
                                          for i in gs.player_character.inventory.items)
                        if has_healing:
                            current_commands_text += " | df = drink full"
                else:
                    # Filter tabs (above) replace the typed u/eat commands.
                    current_commands_text = "j = journal | x = close"


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
                    display_items = [i for i in sorted_items if isinstance(i, (Potion, Scroll, Flare, Lantern, LanternFuel, Treasure, Towel, CookingKit, CuringKit, OrbOfZot))]
                    filter_label = "Usable Items"
                elif gs.inventory_filter == 'equip':
                    display_items = [i for i in sorted_items if isinstance(i, (Weapon, Armor, Towel)) or (isinstance(i, Treasure) and getattr(i, 'treasure_type', '') == 'passive')]
                    filter_label = "Equippable Items"
                elif gs.inventory_filter == 'eat':
                    display_items = [i for i in sorted_items if isinstance(i, (Food, Meat))]
                    filter_label = "Food Items"

                # Segmented filter tabs replace the old [filtered - tap again]
                # hint.  Active tab reflects gs.inventory_filter; tapping a
                # tab sends the corresponding command (b / u / e / eat)
                # through the normal command handler.
                _tabs = [
                    ('All',   'b',   gs.inventory_filter is None),
                    ('Use',   'u',   gs.inventory_filter == 'use'),
                    ('Equip', 'e',   gs.inventory_filter == 'equip'),
                    ('Eat',   'eat', gs.inventory_filter == 'eat'),
                ]
                tabs_html = "<div class='filtertabs'>"
                for label, cmd, is_active in _tabs:
                    cls = 'filtertab active' if is_active else 'filtertab'
                    tabs_html += (
                        f"<div class='{cls}' data-zcmd='{cmd}' "
                        f"onclick=\"window.__zotTap('{cmd}', this)\">{label}</div>"
                    )
                tabs_html += "</div>"

                player_inv_html = tabs_html

                player_inv_html += "<div style='max-height: 295px; overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px;'>"

                player_inv_html += "<div style='margin: 0; padding: 0;'>"

                if not display_items:
                    player_inv_html += "<div style='margin: 2px 0; padding: 0; color: #888;'>(No matching items)</div>"
                else:
                    # Tap-to-act: with a filter active, each row injects the
                    # properly-prefixed command (u1 / e1 / eat1) to Python.
                    # Without a filter we have no implicit verb, so rows
                    # stay non-interactive (user picks a verb button first).
                    _tap_prefix = {'use': 'u', 'equip': 'e', 'eat': 'eat'}.get(gs.inventory_filter, '')
                    _pc = gs.player_character
                    _equipped_accs = set(id(a) for a in getattr(_pc, 'equipped_accessories', []) if a is not None)
                    for i, item in enumerate(display_items):
                        item_str = format_item_for_display(item, gs.player_character, show_price=False)
                        # In the Equip filter, mark currently-equipped rows so
                        # the player sees that tapping will UNEQUIP instead of
                        # a silent no-op.
                        _is_equipped = False
                        if gs.inventory_filter == 'equip':
                            if isinstance(item, Weapon) and _pc.equipped_weapon is item:
                                _is_equipped = True
                            elif isinstance(item, Armor) and _pc.equipped_armor is item:
                                _is_equipped = True
                            elif isinstance(item, Towel) and _pc.equipped_weapon is item:
                                _is_equipped = True
                            elif isinstance(item, Treasure) and id(item) in _equipped_accs:
                                _is_equipped = True
                        if _tap_prefix:
                            cmd_str = f"{_tap_prefix}{i + 1}"
                            if _is_equipped:
                                # Equipped item: row is NOT tappable as a
                                # whole.  An inline UNEQUIP chip on the
                                # right does the toggle (sends e<N>, which
                                # auto-unequips when the slot already
                                # holds this item).
                                player_inv_html += (
                                    f"<div class='taprow equipped' style='cursor: default;'>"
                                    f"{item_str}"
                                    f"<span class='unequip-chip' data-zcmd='{cmd_str}' "
                                    f"onclick=\"event.stopPropagation(); window.__zotTap('{cmd_str}', this)\">UNEQUIP</span>"
                                    f"</div>"
                                )
                            else:
                                player_inv_html += (
                                    f"<div class='taprow' data-zcmd='{cmd_str}' "
                                    f"onclick=\"window.__zotTap('{cmd_str}', this)\">"
                                    f"{item_str}"
                                    f"</div>"
                                )
                        else:
                            player_inv_html += (
                                f"<div style='margin: 2px 0; padding: 4px 0;'>"
                                f"{item_str}"
                                f"</div>"
                            )

                player_inv_html += "</div>"

                player_inv_html += "</div>"

                can_cast = can_cast_spells(gs.player_character)

                if gs.inventory_filter:
                    # Filter active: numpad mode with back button
                    filter_label = {'use': 'Use', 'equip': 'Equip', 'eat': 'Eat'}.get(gs.inventory_filter, gs.inventory_filter)
                    inv_commands = f"# = {filter_label.lower()} item | b = back"
                    # Add "Drink Full" option when in use filter and player has healing potions + is hurt
                    if gs.inventory_filter == 'use' and gs.player_character.health < gs.player_character.max_health:
                        has_healing = any(isinstance(i, Potion) and i.potion_type == 'healing'
                                          for i in gs.player_character.inventory.items)
                        if has_healing:
                            inv_commands += " | df = drink full"
                else:
                    # Main inventory: tap a filter tab (above) to pick items.
                    # Hint shows only the non-tab commands.
                    inv_commands = "c = craft"
                    if can_cast:
                        inv_commands += " | m = spells"
                    inv_commands += " | j = journal | q = quit game | x = exit"

                # HTML inventory chips — replace the toga 3x3 grid (Journal /
                # Craft / Spells / Exit / Quit / Save&Quit) that renders
                # invisible on some devices.
                _inv_chips = []
                if gs.inventory_filter:
                    if (gs.inventory_filter == 'use'
                        and gs.player_character.health < gs.player_character.max_health
                        and any(isinstance(i, Potion) and i.potion_type == 'healing'
                                for i in gs.player_character.inventory.items)):
                        _inv_chips.append(
                            "<div class='hudchip lantern' data-zcmd='df' "
                            "onclick=\"window.__zotTap('df', this)\">DRINK FULL</div>"
                        )
                    if (gs.inventory_filter == 'eat'
                        and any(isinstance(i, Meat) and getattr(i, 'is_rotten', False)
                                for i in gs.player_character.inventory.items)):
                        _inv_chips.append(
                            "<div class='hudchip exit' data-zcmd='dr' "
                            "onclick=\"window.__zotTap('dr', this)\">DROP ROTTEN</div>"
                        )
                    _inv_chips.append(
                        "<div class='hudchip' data-zcmd='b' "
                        "onclick=\"window.__zotTap('b', this)\">&larr; BACK</div>"
                    )
                else:
                    _inv_chips.append(
                        "<div class='hudchip' data-zcmd='c' "
                        "onclick=\"window.__zotTap('c', this)\">CRAFT</div>"
                    )
                    if can_cast:
                        _inv_chips.append(
                            "<div class='hudchip combat-cast' data-zcmd='m' "
                            "onclick=\"window.__zotTap('m', this)\">SPELLS</div>"
                        )
                    _inv_chips.append(
                        "<div class='hudchip' data-zcmd='j' "
                        "onclick=\"window.__zotTap('j', this)\">JOURNAL</div>"
                    )
                    _inv_chips.append(
                        "<div class='hudchip exit' data-zcmd='q' "
                        "onclick=\"window.__zotTap('q', this)\">QUIT</div>"
                    )
                    _inv_chips.append(
                        "<div class='hudchip exit' data-zcmd='x' "
                        "onclick=\"window.__zotTap('x', this)\">CLOSE</div>"
                    )
                inv_chips_html = (
                    "<div class='hudchips inv-bar' style='margin-top:6px;'>"
                    + "".join(_inv_chips) +
                    "</div>"
                )

                html_code = f"""

                        <div style="font-family: monospace; font-size: 12px; width: 100%; max-width: 100vw; overflow-x: auto; box-sizing: border-box;">

                            <div style="min-width: 0; max-width: 100%;">

                                {achievement_notifications}


                                {player_stats_html}

                                {equipment_box_html}

                                <div style="border: 1px solid #4CAF50; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px; overflow-x: auto; max-width: 100%;">{player_inv_html}</div>

                                {inv_chips_html}

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
                getattr(gs.player_character, 'equipped_armor', None),
                character_name=getattr(gs.player_character, 'name', None),
                sprite_pid=getattr(gs.player_character, 'sprite_pid', None),
            )
            unspent_pts = gs.player_character.unspent_stat_points
            if unspent_pts > 0:
                points_html = (
                    f' | <b style="color:#fbbf24;">Unspent Points:</b> {unspent_pts} '
                    f'<span style="color:#94a3b8;">(press p to allocate)</span>'
                )
            else:
                points_html = ""
            stats_html = f"""
                {player_sprite_html}
                <b>Name:</b> {gs.player_character.name} | <b>Level:</b> {gs.player_character.level} ({gs.player_character.experience} XP) |
                <b>Race:</b> {gs.player_character.race} | <b> Class:</b> {gs.player_character.character_class}<br>
                <hr>
                <b>Health:</b> {gs.player_character.health} / {gs.player_character.max_health} |
                <b>Mana:</b> {gs.player_character.mana} / {gs.player_character.max_mana}<br>
                <b>Attack:</b> {gs.player_character.attack} | <b> Defense:</b> {gs.player_character.defense}<br>
                <hr>
                <b>Str:</b> {gs.player_character.strength} | <b>Dex:</b> {gs.player_character.dexterity} | <b>Int:</b> {gs.player_character.intelligence}{points_html}<br>
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

            # Human "Path of Ambition" -- special-skill purchase rows. Only
            # humans see these; each skill costs stat points (shared with
            # STR/DEX/INT allocation, so stats vs. skills is a real choice).
            # Owned skills show a checkmark; affordable ones are tappable;
            # the rest are greyed until the player banks more points.
            skills_html = ""
            if getattr(gs.player_character, 'race', '').lower() == 'human':
                from .game_systems import HUMAN_SKILLS
                _pts = gs.player_character.unspent_stat_points
                _owned = getattr(gs.player_character, 'human_skills', set())
                _rows = ""
                for _key, _sk in sorted(HUMAN_SKILLS.items(), key=lambda kv: kv[1]['order']):
                    if _key in _owned:
                        _rows += (
                            f"<div class='taprow altar-act' style='border-left:3px solid #4CAF50; opacity:0.75;'>"
                            f"<div class='aname' style='color:#4CAF50;'>&#10003; {_sk['name']}</div>"
                            f"<div class='ameta'>{_sk['desc']}</div></div>"
                        )
                    elif _pts >= _sk['cost']:
                        _pts_word = 'pt' if _sk['cost'] == 1 else 'pts'
                        _rows += (
                            f"<div class='taprow altar-act' data-zcmd='sk_{_key}' "
                            f"onclick=\"window.__zotTap('sk_{_key}', this)\" style='border-left:3px solid #fbbf24;'>"
                            f"<div class='aname' style='color:#fbbf24;'>{_sk['name']} &middot; {_sk['cost']} {_pts_word}</div>"
                            f"<div class='ameta'>{_sk['desc']}</div></div>"
                        )
                    else:
                        _pts_word = 'pt' if _sk['cost'] == 1 else 'pts'
                        _rows += (
                            f"<div class='taprow altar-act' style='border-left:3px solid #555; opacity:0.5;'>"
                            f"<div class='aname' style='color:#888;'>{_sk['name']} &middot; {_sk['cost']} {_pts_word} (need points)</div>"
                            f"<div class='ameta'>{_sk['desc']}</div></div>"
                        )
                skills_html = (
                    "<div style='margin-top:6px;'>"
                    "<div style='color:#fbbf24; font-weight:bold; font-size:13px; "
                    "letter-spacing:1px; margin:6px 0 3px 0;'>PATH OF AMBITION &middot; SPECIAL SKILLS</div>"
                    f"{_rows}</div>"
                )

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}

                    <div style="border: 1px solid #444; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px;">{stats_html}</div>

                    <div class='taprow altar-act' data-zcmd='cp'
                         onclick="window.__zotTap('cp', this)">
                        <div class='aname'>Change Portrait</div>
                        <div class='ameta'>Pick a new avatar from the gallery</div>
                    </div>
                    {(f'''
                    <div class='taprow altar-act' data-zcmd='p' style='border-left: 3px solid #fbbf24;'
                         onclick="window.__zotTap('p', this)">
                        <div class='aname' style='color:#fbbf24;'>Allocate Stat Points ({gs.player_character.unspent_stat_points})</div>
                        <div class='ameta'>Spend level-up points on STR / DEX / INT</div>
                    </div>
                    ''') if gs.player_character.unspent_stat_points > 0 else ''}
                    {skills_html}
                    <div class='taprow cancel' data-zcmd='x'
                         onclick="window.__zotTap('x', this)">
                        <span class='tapnum'>&times;</span>Back to Inventory
                    </div>
</div>
                """
            base_cmds = "Tap Back | cp = change portrait | x = inventory"
            if gs.player_character.unspent_stat_points > 0:
                base_cmds = f"p = allocate ({gs.player_character.unspent_stat_points} pts) | {base_cmds}"
            current_commands_text = base_cmds

        elif gs.prompt_cntl == "stat_allocation_mode":
            # Stat-point allocation panel (build 380). Reuses the stats
            # HTML from character_stats_mode above so the player sees
            # their current stat values while spending. a/d/i spend a
            # point; x backs out.
            current_commands_text = "a = +STR | d = +DEX | i = +INT | x = back"

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
                    recipes_html += f"<div style='color: {tier_color}; font-weight: bold; font-size: 13px; margin: 8px 0 4px 0; letter-spacing: 1px;'>TIER {tier} &middot; {tier_names[tier]}</div>"

                    for recipe_name, recipe_data in by_tier[tier]:
                        crafted_item = recipe_data['result']()
                        ingredients_text = ", ".join([f"{count}x {name}" for name, count in recipe_data['ingredients']])
                        ration_cost = recipe_data.get('ration_cost', 0)
                        if ration_cost > 0:
                            ingredients_text += f", {ration_cost}x Rations"

                        cmd_str = f"{recipe_counter}"
                        recipes_html += (
                            f"<div class='taprow recipe' data-zcmd='{cmd_str}' "
                            f"onclick=\"window.__zotTap('{cmd_str}', this)\" "
                            f"style='border-left: 3px solid {tier_color};'>"
                            f"<div class='rname' style='color:{tier_color};'>"
                            f"{recipe_name}"
                            f"</div>"
                            f"<div class='rmeta'>Needs: {ingredients_text}</div>"
                            f"<div class='rdesc'>{crafted_item.description}</div>"
                            f"</div>"
                        )
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
            
            cancel_html = (
                "<div class='taprow cancel' data-zcmd='x' "
                "onclick=\"window.__zotTap('x', this)\">"
                "<span class='tapnum'>&times;</span>Back to Inventory</div>"
            )
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
                    <div style="text-align: center; margin-top: 8px; color: #DDD; font-size: 12px;">
                        Tap a recipe to craft &middot; Craftable: {len(craftable)}
                    </div>
                    {cancel_html}
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div class="room-panel" style="width: 100%;">{crafting_html}</div>
                </div>
            """
            current_commands_text = "Tap a recipe to craft | x = back"
            needs_numbers = True

        elif gs.prompt_cntl == "spell_memorization_mode":
            # SPELL MEMORIZATION MENU VIEW

            all_spells = gs.player_character.get_spell_inventory()
            max_slots = gs.player_character.get_max_memorized_spell_slots()
            used_slots = gs.player_character.get_used_spell_slots()

            # Segmented tabs: [Memorize] [Forget] [Cast].  Idempotent —
            # bare m/f/c already SET the sub-action (no toggle-off) so
            # tapping the active tab is harmless.  'Cast' invokes
            # self-targeted spells out of combat (healing, cleanses,
            # buffs); damage/debuff_target spells are greyed out.
            _mem_tabs = [
                ('Memorize', 'm', gs.spell_memo_action == 'memorize'),
                ('Forget',   'f', gs.spell_memo_action == 'forget'),
                ('Cast',     'c', gs.spell_memo_action == 'cast'),
            ]
            memo_tabs_html = "<div class='filtertabs'>"
            for label, cmd, is_active in _mem_tabs:
                cls = 'filtertab active' if is_active else 'filtertab'
                memo_tabs_html += (
                    f"<div class='{cls}' data-zcmd='{cmd}' "
                    f"onclick=\"window.__zotTap('{cmd}', this)\">{label}</div>"
                )
            memo_tabs_html += "</div>"

            # Available spells HTML — tappable when Memorize tab is active
            available_spells_html = "<h3>Spells in Inventory</h3>"
            available_spells_html += "<div style='max-height: 280px; overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px;'>"
            _can_memorize = (gs.spell_memo_action == 'memorize')
            if not all_spells:
                available_spells_html += "<p>You have no spell scrolls in your inventory.</p>"
            else:
                for i, spell in enumerate(all_spells):
                    identified = is_item_identified(spell)
                    display_name = get_item_display_name(spell)
                    is_memorized = spell in gs.player_character.memorized_spells
                    marker = " <span class='eqbadge'>MEM</span>" if is_memorized else ""

                    if identified:
                        slots_needed = gs.player_character.get_spell_slots(spell)
                        spell_info = f"<b>{display_name}</b>{marker}<br>"
                        spell_info += "<span style='margin-left:22px; font-size:10px; color:#CE93D8;'>"
                        spell_info += f"L{spell.level} | {spell.mana_cost} MP | "
                        spell_info += f"{slots_needed} slot{'s' if slots_needed > 1 else ''} | "
                        spell_info += f"{spell.spell_type}</span>"
                    else:
                        spell_info = f"<b>{display_name}</b> <span style='color: #888;'>[?]</span>"

                    body = f"{spell_info}"
                    if _can_memorize and not is_memorized:
                        cmd_str = f"m{i + 1}"
                        available_spells_html += (
                            f"<div class='taprow spell' data-zcmd='{cmd_str}' "
                            f"onclick=\"window.__zotTap('{cmd_str}', this)\">{body}</div>"
                        )
                    else:
                        row_cls = 'taprow spell disabled' if _can_memorize and is_memorized else 'taprow spell disabled'
                        # No filter active OR already memorized => non-tappable
                        if _can_memorize and is_memorized:
                            available_spells_html += (
                                f"<div class='{row_cls}'>{body}"
                                f"<span class='tapnote'>Already memorized</span></div>"
                            )
                        else:
                            available_spells_html += (
                                f"<div style='margin: 2px 0; padding: 4px;'>{body}</div>"
                            )
            available_spells_html += "</div>"

            # Memorized spells HTML with progress bar — tappable when Forget is active
            memorized_html = f"""
                <h3>Spell Slots: {used_slots}/{max_slots}</h3>
                <div style="background-color: #333; padding: 3px; border-radius: 3px; margin-bottom: 5px;">
                    <div style="background-color: #4CAF50; width: {(used_slots / max_slots) * 100 if max_slots > 0 else 0}%; height: 20px; border-radius: 2px;"></div>
                </div>
                <b>Available Slots:</b> {max_slots - used_slots}<br>
                <hr>
                <h3>Currently Memorized</h3>
                """

            _can_forget = (gs.spell_memo_action == 'forget')
            _can_cast_ooc = (gs.spell_memo_action == 'cast')
            # spell_types that make sense without a monster target — must stay
            # in sync with _OUT_OF_COMBAT_SAFE in combat.py.
            _ooc_safe_types = {'healing', 'remove_status', 'add_status_effect'}
            _current_mana = gs.player_character.mana
            if gs.player_character.memorized_spells:
                for i, spell in enumerate(gs.player_character.memorized_spells):
                    slots_used = gs.player_character.get_spell_slots(spell)
                    # Cast-tab rows show the MP cost + effect summary
                    if _can_cast_ooc:
                        if spell.spell_type == 'healing':
                            detail = f"Heal {spell.base_power}+Int/2 HP"
                        elif spell.spell_type == 'remove_status':
                            detail = f"Cleanse {spell.status_effect_name or '(self)'}"
                        elif spell.spell_type == 'add_status_effect':
                            detail = f"Buff: {spell.status_effect_name or '(self)'}"
                        else:
                            detail = f"{spell.spell_type} (combat only)"
                        body = (
                            f""
                            f"<b>{spell.name}</b> ({spell.mana_cost} MP)<br>"
                            f"<span style='margin-left:22px; font-size:10px; color:#CE93D8;'>"
                            f"Lvl {spell.level} | {detail}</span>"
                        )
                    else:
                        body = (
                            f""
                            f"<b>{spell.name}</b> "
                            f"<span style='color:#CE93D8; font-size:10px;'>"
                            f"({slots_used} slot{'s' if slots_used > 1 else ''})</span>"
                        )
                    if _can_forget:
                        cmd_str = f"f{i + 1}"
                        memorized_html += (
                            f"<div class='taprow spell' data-zcmd='{cmd_str}' "
                            f"onclick=\"window.__zotTap('{cmd_str}', this)\">{body}</div>"
                        )
                    elif _can_cast_ooc:
                        if spell.spell_type not in _ooc_safe_types:
                            memorized_html += (
                                f"<div class='taprow spell disabled'>{body}"
                                f"<span class='tapnote'>Combat only</span></div>"
                            )
                        elif _current_mana < spell.mana_cost:
                            memorized_html += (
                                f"<div class='taprow spell disabled'>{body}"
                                f"<span class='tapnote'>Not enough MP</span></div>"
                            )
                        else:
                            cmd_str = f"c{i + 1}"
                            memorized_html += (
                                f"<div class='taprow spell' data-zcmd='{cmd_str}' "
                                f"onclick=\"window.__zotTap('{cmd_str}', this)\">{body}</div>"
                            )
                    else:
                        memorized_html += (
                            f"<div style='margin: 2px 0; padding: 4px;'>{body}</div>"
                        )
            else:
                memorized_html += "<p><i>No spells memorized</i></p>"

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}

                    {memo_tabs_html}

                    <div style="border: 1px solid green; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px;">{memorized_html}</div>

                    <div style="border: 1px solid blue; padding: 4px; border-radius: 4px; background: #1a1a1a; margin-bottom: 5px;">{available_spells_html}</div>

                    <div class='hudchips' style='margin-top:6px;'>
                        <div class='hudchip exit' data-zcmd='x'
                             onclick="window.__zotTap('x', this)">EXIT</div>
                    </div>
</div>
                """
            if gs.spell_memo_action:
                action_label = {'memorize': 'memorize', 'forget': 'forget', 'cast': 'cast'}.get(gs.spell_memo_action, gs.spell_memo_action)
                current_commands_text = f"# = {action_label} spell | x = exit"
            else:
                current_commands_text = "Tap a tab above to begin | x = exit"

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

            _jcats = [
                ('1', 'Weapons',     weapons_found,     weapons_total,     '#FF6F00'),
                ('2', 'Armor',       armor_found,       armor_total,       '#4CAF50'),
                ('3', 'Potions',     potions_found,     potions_total,     '#E91E63'),
                ('4', 'Scrolls',     scrolls_found,     scrolls_total,     '#E040FB'),
                ('5', 'Spells',      spells_found,      spells_total,      '#2196F3'),
                ('6', 'Treasures',   treasures_found,   treasures_total,   '#FFD700'),
                ('7', 'Utilities',   utilities_found,   utilities_total,   '#607D8B'),
                ('8', 'Ingredients', ingredients_found, ingredients_total, '#8BC34A'),
            ]
            jcats_html = "<div class='jcat-grid'>"
            for num, name, found, total, color in _jcats:
                jcats_html += (
                    f"<div class='taprow jcat' data-zcmd='{num}' "
                    f"onclick=\"window.__zotTap('{num}', this)\" "
                    f"style='border-color:{color};'>"
                    f"<div class='jname' style='color:{color};'>{name}</div>"
                    f"<div class='jprog'>{found}/{total}</div>"
                    f"</div>"
                )
            jcats_html += "</div>"

            journal_html = f"""
                <h3> Adventurer's Journal</h3>
                <div style="padding: 3px; border-radius: 3px; margin-bottom: 15px;">
                    <div style="background-color: #4CAF50; width: {completion_pct}%; height: 20px; border-radius: 2px; text-align: center; line-height: 20px; color: #000; font-weight: bold;">
                        {total_found}/{total_items} Items Discovered ({completion_pct}%)
                    </div>
                </div>
                {jcats_html}
                <div class='jcat-grid'>
                    <div class='taprow jcat' data-zcmd='a'
                         onclick="window.__zotTap('a', this)"
                         style='border-color:#FFD700;'>
                        <div class='jname' style='color:#FFD700;'>Achievements</div>
                        <div class='jprog'>view unlocks &amp; rewards</div>
                    </div>
                    <div class='taprow jcat' data-zcmd='s'
                         onclick="window.__zotTap('s', this)"
                         style='border-color:#4FC3F7;'>
                        <div class='jname' style='color:#4FC3F7;'>Stats</div>
                        <div class='jprog'>character details</div>
                    </div>
                </div>
                <div class='taprow cancel' data-zcmd='x'
                     onclick="window.__zotTap('x', this)">
                    <span class='tapnum'>&times;</span>Back to Inventory
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}

                    <div style="border: 1px solid gold; padding: 10px; max-height: 500px; overflow-y: auto;">
                        {journal_html}
                    </div>
                    <div class='hudchips' style='margin-top:8px;'>
                        <div class='hudchip' data-zcmd='t'
                             onclick="window.__zotTap('t', this)">{ 'Aa-' if gs.large_text_mode else 'Aa+' }</div>
                        <div class='hudchip' data-zcmd='v'
                             onclick="window.__zotTap('v', this)">{ 'VOL-' if gs.music_enabled else 'VOL+' }</div>
                        <div class='hudchip lantern' data-zcmd='g'
                             onclick="window.__zotTap('g', this)">SAVE</div>
                        <div class='hudchip exit' data-zcmd='x'
                             onclick="window.__zotTap('x', this)">BACK</div>
                    </div>
</div>
                """
            text_label = "Aa-" if gs.large_text_mode else "Aa+"
            music_label = "vol-" if gs.music_enabled else "vol+"
            current_commands_text = f"Tap a category or Achievements | t = {text_label} | v = {music_label} | g = save | x = back"

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
                            entry_html += """
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
                    entry_html = """
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

                    <div class='taprow cancel' data-zcmd='b'
                         onclick="window.__zotTap('b', this)"
                         style='margin-top: 10px;'>
                        <span class='tapnum'>&larr;</span>Back to Journal
                    </div>
                </div>
                """
            text_label = "Aa-" if gs.large_text_mode else "Aa+"
            music_label = "vol-" if gs.music_enabled else "vol+"
            current_commands_text = "Tap Back | x = close journal"

        elif gs.prompt_cntl == "spell_casting_mode":
            # SPELL CASTING - Compact: Combat panels + spell list (no map)
            # Map is hidden to give spell list room on mobile screens.

            # Generate pixel art sprite for the monster
            threat = get_monster_threat_style(gs.active_monster, gs.player_character)
            gs.combat_threat_style = threat
            _anim_tok = _combat_anim_token()
            monster_sprite_html = wrap_monster_loom(generate_monster_sprite_html(gs.active_monster.name, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z), size=threat['sprite_size'], loom=threat['looming'], flourish=threat['flourish'], anim_token=_anim_tok), threat)

            # Compact Monster Info (same as combat_mode compact style)
            monster_html = f"""
                <div id="monster_panel" data-fight="{_anim_tok}" style="position:relative; padding: 3px; border-radius: 3px; {threat['panel_css']} margin-bottom: 4px;">
                    <div style="display:flex; align-items:{threat['row_align']}; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{monster_sprite_html}</div>
                        <div>
                            <div style="color: {threat['name_color']}; font-weight: bold; font-size: 12px; margin-bottom: 2px;">{gs.active_monster.name}{threat['label_html']}</div>
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
                getattr(gs.player_character, 'equipped_armor', None),
                character_name=getattr(gs.player_character, 'name', None),
                sprite_pid=getattr(gs.player_character, 'sprite_pid', None),
            )
            player_combat_html = f"""
                <div id="player_panel" data-fight="{_anim_tok}" style="position:relative; padding: 3px; border-radius: 3px; border: 2px solid #666;{low_hp_pulse_style}">
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

            # Spells List — tappable modal.  Rows are taprows that send the
            # bare spell number (process_spell_casting_action reads an int).
            # Insufficient-mana rows stay non-interactive and greyed out.
            available_spells = gs.player_character.memorized_spells
            spells_html = '<div style="padding: 4px; border-radius: 4px; border: 2px solid #E040FB; max-height: 45vh; overflow-y: auto;">'
            spells_html += '<div style="color: #E040FB; font-weight: bold; font-size: 13px; margin-bottom: 4px;"> Cast Spell</div>'

            if not available_spells:
                spells_html += '<div style="color: #F44336; font-size: 12px;">No spells memorized!</div>'
            else:
                for i, spell in enumerate(available_spells):
                    can_cast = gs.player_character.mana >= spell.mana_cost
                    charge_turns = get_spell_charge_turns(spell)
                    charge_tag = ""
                    if charge_turns > 0:
                        charge_tag = f' <span style="color:#CE93D8;">[{charge_turns}T]</span>'

                    if spell.spell_type == 'damage':
                        detail = f'{spell.damage_type} | Pwr {spell.base_power}'
                    elif spell.spell_type == 'healing':
                        detail = f'Heal {spell.base_power} HP'
                    elif spell.spell_type in ['add_status_effect', 'remove_status']:
                        detail = f'{spell.status_effect_name}'
                    elif spell.spell_type == 'debuff_target':
                        detail = f'{spell.status_effect_name}'
                    else:
                        detail = ''

                    body = (
                        f""
                        f"<b>{spell.name}</b> ({spell.mana_cost} MP){charge_tag}<br>"
                        f"<span style='margin-left:22px; font-size:10px; color:#CE93D8;'>"
                        f"Lvl {spell.level} | {detail}</span>"
                    )
                    if can_cast:
                        cmd_str = f"{i + 1}"
                        spells_html += (
                            f"<div class='taprow spell' data-zcmd='{cmd_str}' "
                            f"onclick=\"window.__zotTap('{cmd_str}', this)\">{body}</div>"
                        )
                    else:
                        spells_html += (
                            f"<div class='taprow spell disabled'>{body}"
                            f"<span class='tapnote'>Not enough MP</span></div>"
                        )

                # Cancel row so the player can back out without typing 'x'
                spells_html += (
                    "<div class='taprow spell cancel' data-zcmd='x' "
                    "onclick=\"window.__zotTap('x', this)\">"
                    "<span class='tapnum'>&times;</span>Cancel</div>"
                )

            spells_html += '</div>'

            # Layout: Compact combat panels + spell list (no map — all visible)
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}

                    <div style="width: 100%; max-width: 300px; margin: 0 auto 4px auto; {threat['growbox_loom_css']}">
                        {monster_html}
                        {player_combat_html}
                    </div>

                    {spells_html}
                    {generate_damage_float_js(gs.active_monster.name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal, gs.last_monster_damage_badge, gs.last_player_damage_badge, _spell_element, _spell_level)}
                    {generate_hp_drain_js(gs.active_monster.health, gs.active_monster.max_health, gs.player_character.health, gs.player_character.max_health, gs.last_monster_damage, gs.last_player_damage, gs.last_player_heal, bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}

                </div>
                """
            current_commands_text = "Tap a spell to cast | x = cancel"

        elif gs.prompt_cntl == "combat_mode":
            # COMBAT VIEW WITH MAP - 3 Column Layout

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Generate pixel art sprite for the monster
            threat = get_monster_threat_style(gs.active_monster, gs.player_character)
            gs.combat_threat_style = threat
            _anim_tok = _combat_anim_token()
            monster_sprite_html = wrap_monster_loom(generate_monster_sprite_html(gs.active_monster.name, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z), size=threat['sprite_size'], loom=threat['looming'], flourish=threat['flourish'], anim_token=_anim_tok), threat)

            # Compact Monster Info
            monster_html = f"""
                <div id="monster_panel" data-fight="{_anim_tok}" style="position:relative; padding: 3px; border-radius: 3px; {threat['panel_css']} margin-bottom: 4px;">
                    <div style="display:flex; align-items:{threat['row_align']}; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{monster_sprite_html}</div>
                        <div>
                            <div style="color: {threat['name_color']}; font-weight: bold; font-size: 12px; margin-bottom: 2px;">{gs.active_monster.name}{threat['label_html']}</div>
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
            player_display = f"{gs.player_character.name} {player_title}"
            
            # Combat layout: Map | Combat Info | (empty space for consistency)
            # Generate combat commands based on spell capability
            can_cast = can_cast_spells(gs.player_character)
            combat_commands = "a = attack | f = flee | i = inventory"
            if can_cast:
                combat_commands += " | c = cast spell"

            # Channeling indicator — overlays the right-side dice slot
            # inside player_panel.  No dice are rolling while the player
            # concentrates, so we reuse that real-estate instead of
            # adding a separate row that pushes the map down.
            channeling_overlay = ""
            if gs.spell_charging:
                ch = gs.spell_charging
                spell_name = ch['spell'].name
                turns_left = ch['turns_remaining']
                total_turns = ch['total_turns']
                filled = total_turns - turns_left
                bar_segments = ''.join(
                    f'<span style="color:#E040FB;">{"*" if i < filled else "."}</span>'
                    for i in range(total_turns)
                )
                channeling_overlay = f"""
                    <div style="position:absolute; right:4px; top:50%; transform:translateY(-50%);
                                width:150px; padding:4px 6px; border:2px solid #E040FB;
                                border-radius:4px; background:rgba(224,64,251,0.12);
                                animation: channelPulse 1.5s ease-in-out infinite;
                                z-index: 6; text-align: center;">
                        <div style="color: #E040FB; font-weight: bold; font-size: 10px; line-height: 1.1;">
                            CHANNELING
                        </div>
                        <div style="color: #CE93D8; font-size: 9px; line-height: 1.1; margin-top: 1px;
                                    overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                            {spell_name}
                        </div>
                        <div style="font-size: 10px; color: #E040FB; margin-top: 2px; letter-spacing: 1px;">
                            [{bar_segments}]
                        </div>
                        <div style="font-size: 8px; color: #CE93D8; margin-top: 1px;">
                            {turns_left} turn{'s' if turns_left != 1 else ''} left
                        </div>
                    </div>
                """
                combat_commands = "any key = continue channeling"

            # Compact Player Combat Info
            player_sprite_html_combat = generate_player_sprite_html(
                getattr(gs.player_character, 'race', 'human'),
                getattr(gs.player_character, 'gender', 'male'),
                getattr(gs.player_character, 'equipped_armor', None),
                character_name=getattr(gs.player_character, 'name', None),
                sprite_pid=getattr(gs.player_character, 'sprite_pid', None),
            )
            player_combat_html = f"""
                <div id="player_panel" data-fight="{_anim_tok}" style="position:relative; padding: 3px; border-radius: 3px; border: 2px solid #666;{low_hp_pulse_style}">
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
                    {channeling_overlay}
                </div>
                    </div>

                </div>
                """

            # HTML combat action chips — replace the toga C/A/F/I buttons
            # that render invisible on some devices.  Channeling pauses the
            # action panel ("any key = continue") so we hide chips then
            # and show the channeling progress instead.  During dice-roll
            # / monster-defeat animations the chips are momentarily faded
            # out by JS (see updateGame in wrap_html) so the player can't
            # double-tap mid-resolution -- but they always RENDER so the
            # subsequent re-render after animation finds them in place.
            combat_chips_html = ""
            if not gs.spell_charging:
                _chips = [
                    "<div class='hudchip combat-attack' data-zcmd='a' "
                    "onclick=\"window.__zotTap('a', this)\">ATTACK</div>"
                ]
                if can_cast:
                    _chips.append(
                        "<div class='hudchip combat-cast' data-zcmd='c' "
                        "onclick=\"window.__zotTap('c', this)\">CAST</div>"
                    )
                _chips.append(
                    "<div class='hudchip' data-zcmd='i' "
                    "onclick=\"window.__zotTap('i', this)\">INVENTORY</div>"
                )
                _chips.append(
                    "<div class='hudchip exit' data-zcmd='f' "
                    "onclick=\"window.__zotTap('f', this)\">FLEE</div>"
                )
                combat_chips_html = (
                    "<div class='hudchips' style='margin-top:6px;'>"
                    + "".join(_chips) +
                    "</div>"
                )

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}

                    <div class="bottom-pinned-zone">
                        <div class="room-panel" style="width: 100%; {threat['roompanel_loom_css']}">
                            {monster_html}
                            {player_combat_html}
                        </div>
                        {grid_html}
                        {combat_chips_html}
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
            # Reuse the threat styling from the fight so the defeated foe keeps
            # its size + fierce box during the victory/defeat animation.
            _v_threat = getattr(gs, 'combat_threat_style', None) or {}
            # Reuse the fight's anim token (read, don't bump: active_monster is
            # already None) so the panels don't replay their entrance pop when
            # the view flips from combat to victory.
            _anim_tok = getattr(gs, 'combat_anim_token', 0)
            # Cap the defeated sprite so it fits the box without clipping -- the
            # defeat grayscale runs on this in-flow canvas, so we don't mount
            # the over-the-HUD overlay on the victory frame.
            _v_size = min(_v_threat.get('sprite_size', 64), 96)
            _v_panel_css = _v_threat.get('panel_css', 'border: 2px solid #666;')
            _v_name_color = _v_threat.get('name_color', '#F44336')
            _v_label_html = _v_threat.get('label_html', '')
            _v_panel_loom = ''
            monster_sprite_html = generate_monster_sprite_html(victory_name, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z), size=_v_size)

            # Killing-blow HP bar: render the PRE-round HP and let
            # generate_hp_drain_js drop it to zero at the damage-float
            # moment (1.3s), matching the attack animation — otherwise the
            # empty bar spoils the kill before the dice even land.
            # active_monster is already cleared here, so max HP comes from
            # the pre-round snapshot. Kills without a damage number (e.g.
            # status-effect deaths) have no drain scheduled, so show the
            # empty bar immediately.
            _v_max_hp = getattr(gs, 'pre_round_monster_max_hp', None) or 1
            if gs.last_monster_damage > 0 and getattr(gs, 'pre_round_monster_hp', None):
                _v_hp_bar = health_bar(gs.pre_round_monster_hp, _v_max_hp, width=10)
            else:
                _v_hp_bar = health_bar(0, _v_max_hp, width=10)

            # Show last damage dealt
            dmg_text = ""
            if gs.last_monster_damage > 0:
                dmg_text = f'<div style="font-size: 9px; color: #FF5252; font-weight: bold;">-{gs.last_monster_damage} HP</div>'

            monster_html = f"""
                <div id="monster_panel" data-fight="{_anim_tok}" style="position:relative; padding: 3px; border-radius: 3px; {_v_panel_css} margin-bottom: 4px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div id="monster_sprite_box" style="flex-shrink:0; transition: filter 0.6s ease-out;">{monster_sprite_html}</div>
                        <div id="monster_info_box">
                            <div style="color: {_v_name_color}; font-weight: bold; font-size: 12px; margin-bottom: 2px;">{victory_name}{_v_label_html}</div>
                            <div style="font-size: 9px;"><span class="monster-hp-bar">{_v_hp_bar}</span></div>
                            {dmg_text}
                    <div id="monster_init_dice" style="position:absolute;right:100px;top:50%;transform:translateY(-50%) scale(1.55);transform-origin:right center;width:58px;height:44px;z-index:5;"></div><div id="monster_dice" style="position:absolute;right:4px;top:50%;transform:translateY(-50%) scale(1.3);transform-origin:right center;width:68px;height:52px;display:flex;gap:4px;"><div id="monster_def_dice" style="position:relative;width:32px;height:52px;"></div><div id="monster_atk_dice" style="position:relative;width:32px;height:52px;"></div></div>
                </div>
                    </div>
                    
                </div>
                """

            player_title = get_player_title(gs.player_character)
            player_display = f"{gs.player_character.name} {player_title}"
            player_sprite_html_combat = generate_player_sprite_html(
                getattr(gs.player_character, 'race', 'human'),
                getattr(gs.player_character, 'gender', 'male'),
                getattr(gs.player_character, 'equipped_armor', None),
                character_name=getattr(gs.player_character, 'name', None),
                sprite_pid=getattr(gs.player_character, 'sprite_pid', None),
            )
            player_combat_html = f"""
                <div id="player_panel" data-fight="{_anim_tok}" style="position:relative; padding: 3px; border-radius: 3px; border: 2px solid #666;{low_hp_pulse_style}">
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
                    {player_stats_html}

                    <div class="bottom-pinned-zone">
                        <div class="room-panel" style="width: 100%; {_v_panel_loom}">
                            {monster_html}
                            {player_combat_html}
                        </div>
                        {grid_html}
                        <div id='victory_continue' class='taprow altar-act bless' data-zcmd=' '
                             onclick="window.__zotTap(' ', this)"
                             style="margin-top: 8px; opacity: 0; transition: opacity 0.4s ease-out;">
                            <div class='aname'>Victory! Continue</div>
                            <div class='ameta'>Tap anywhere or wait for auto-dismiss</div>
                        </div>
                    </div>
                    <script>(function(){{var vc=document.getElementById("victory_continue");if(vc){{setTimeout(function(){{vc.style.opacity="1";}},{gs.DEFEAT_OVERLAY_MS});}}}})();</script>
                    {generate_damage_float_js(victory_name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal, gs.last_monster_damage_badge, gs.last_player_damage_badge, _spell_element, _spell_level)}
                    {generate_hp_drain_js(0, _v_max_hp, gs.player_character.health, gs.player_character.max_health, gs.last_monster_damage, gs.last_player_damage, gs.last_player_heal, bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}
                </div>
                """
            gs.monster_defeated_anim = victory_name
            current_commands_text = "Tap Continue or wait"

            # Schedule auto-dismiss after animations finish (~2.8s)
            self._schedule_victory_dismiss()

        elif gs.prompt_cntl == "flee_direction_mode":
            # FLEE DIRECTION SELECTION VIEW

            # Generate map HTML (same as combat view)
            floor = gs.my_tower.floors[gs.player_character.z]

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Generate pixel art sprite for the monster
            threat = get_monster_threat_style(gs.active_monster, gs.player_character)
            gs.combat_threat_style = threat
            _anim_tok = _combat_anim_token()
            monster_sprite_html = wrap_monster_loom(generate_monster_sprite_html(gs.active_monster.name, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z), size=threat['sprite_size'], loom=threat['looming'], flourish=threat['flourish'], anim_token=_anim_tok), threat)

            # Monster info (still there, but you're fleeing)
            monster_html = f"""
                <div id="monster_panel" data-fight="{_anim_tok}" style="position:relative; padding: 4px; border-radius: 4px; {threat['panel_css']} margin-bottom: 5px;">
                    <div style="display:flex; align-items:{threat['row_align']}; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{monster_sprite_html}</div>
                        <div>
                            <div style="color: {threat['name_color']}; font-weight: bold; font-size: 15px; margin-bottom: 4px;">Fleeing from {gs.active_monster.name}{threat['label_html']}</div>
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
                getattr(gs.player_character, 'equipped_armor', None),
                character_name=getattr(gs.player_character, 'name', None),
                sprite_pid=getattr(gs.player_character, 'sprite_pid', None),
            )
            player_combat_html = f"""
                <div id="player_panel" data-fight="{_anim_tok}" style="position:relative; padding: 4px; border-radius: 4px; border: 2px solid #666;{low_hp_pulse_style}">
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

            flee_dpad = """
                <div class='dpad'>
                    <div class='dpad-slot empty'></div>
                    <div class='taprow dpad-dir' data-zcmd='n' onclick="window.__zotTap('n', this)">N</div>
                    <div class='dpad-slot empty'></div>
                    <div class='taprow dpad-dir' data-zcmd='w' onclick="window.__zotTap('w', this)">W</div>
                    <div class='taprow dpad-cancel' data-zcmd='c' onclick="window.__zotTap('c', this)">FIGHT</div>
                    <div class='taprow dpad-dir' data-zcmd='e' onclick="window.__zotTap('e', this)">E</div>
                    <div class='dpad-slot empty'></div>
                    <div class='taprow dpad-dir' data-zcmd='s' onclick="window.__zotTap('s', this)">S</div>
                    <div class='dpad-slot empty'></div>
                </div>
            """
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}


                    <div class="bottom-pinned-zone">
                        <div class="room-panel" style="width: 100%; {threat['roompanel_loom_css']}">
                            {monster_html}
                            {player_combat_html}
                            <div style="text-align:center; color:#F44336; font-weight:bold; margin-top:8px;">Flee which way?</div>
                        </div>
                        {grid_html}
                        {flee_dpad}
                    </div>

                    {generate_damage_float_js(gs.active_monster.name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal, gs.last_monster_damage_badge, gs.last_player_damage_badge, _spell_element, _spell_level)}
                    {generate_hp_drain_js(gs.active_monster.health, gs.active_monster.max_health, gs.player_character.health, gs.player_character.max_health, gs.last_monster_damage, gs.last_player_damage, gs.last_player_heal, bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}

                </div>
                """
            current_commands_text = "Tap a direction or FIGHT to cancel"

        elif gs.prompt_cntl == "foresight_direction_mode":
            # FORESIGHT DIRECTION VIEW (similar to flee but for scroll)

            # Generate map HTML (reuse existing map generation code)
            floor = gs.my_tower.floors[gs.player_character.z]

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Scroll info panel
            scroll_html = """
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
                    {player_stats_html}

                    <div class="bottom-pinned-zone">
                        <div class="room-panel" style="width: 100%;">
                            {scroll_html}
                            {player_info_html}
                            <div style="margin-top: 8px; text-align:center; color:#E040FB; font-weight:bold;">
                                Choose your direction of sight
                            </div>
                        </div>
                        {grid_html}
                        <div class='dpad'>
                            <div class='dpad-slot empty'></div>
                            <div class='taprow dpad-dir' data-zcmd='n' onclick="window.__zotTap('n', this)">N</div>
                            <div class='dpad-slot empty'></div>
                            <div class='taprow dpad-dir' data-zcmd='w' onclick="window.__zotTap('w', this)">W</div>
                            <div class='taprow dpad-cancel' data-zcmd='c' onclick="window.__zotTap('c', this)">CANCEL</div>
                            <div class='taprow dpad-dir' data-zcmd='e' onclick="window.__zotTap('e', this)">E</div>
                            <div class='dpad-slot empty'></div>
                            <div class='taprow dpad-dir' data-zcmd='s' onclick="window.__zotTap('s', this)">S</div>
                            <div class='dpad-slot empty'></div>
                        </div>
                    </div>
                </div>
                """
            current_commands_text = "Tap a direction or Cancel"

        elif gs.prompt_cntl == "chest_mode":
            # CHEST VIEW - Simplified 2 columns: Map | Chest Info

            # Check for lantern
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()

            # Determine chest variant for sprite
            current_floor_c = gs.my_tower.floors[gs.player_character.z]
            room_c = current_floor_c.grid[gs.player_character.y][gs.player_character.x]
            chest_variant = 'legendary' if room_c.properties.get('is_legendary') else None
            chest_sprite = generate_room_sprite_html('C', variant=chest_variant, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            # Chest info box - simple and clean
            chest_html = f"""
               <div style="
                            border: 2px solid #555;
                            border-radius: 3px;
                            padding: 8px;
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
                    
                    <div class='altar-actions'>
                        <div class='taprow altar-act loot' data-zcmd='o'
                             onclick="window.__zotTap('o', this)">
                            <div class='aname'>Open the Chest</div>
                            <div class='ameta'>Claim whatever treasures it holds</div>
                        </div>
                    </div>
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}

                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{chest_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
</div>
                """
            # Build chest commands with lantern if available
            current_commands_text = "Tap to open | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "altar_mode":
            # ALTAR VIEW.  Two distinct layouts:
            #
            # 1. Default (gs.altar_action != 'sacrifice'):
            #    Room-panel + map shape.  God header + piety bar + 2
            #    action chips (Pray / Sacrifice).  Pray's subtitle shows
            #    the current-tier reward inline.  Map stays anchored
            #    below for movement.
            #
            # 2. Sacrifice picker (gs.altar_action == 'sacrifice'):
            #    Full-screen vendor-style item picker.  Map is hidden so
            #    the inventory list has the whole content area to itself.
            #    BACK chip returns to the default altar view.

            gods = gs.active_altar_state.get('gods', {})
            blessed_id = gs.active_altar_state.get('blessed_id', 1)
            blessed_god = gods.get(blessed_id, {})
            altar_sprite = generate_room_sprite_html('A', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            if gs.altar_action == 'sacrifice':
                # ---------- SACRIFICE PICKER (full-screen, no map) ----------
                sorted_items = get_sorted_inventory(gs.player_character.inventory)
                sacrificeable = [it for it in sorted_items if not isinstance(it, (Rune, Shard))]
                inv_html = ""
                if not sacrificeable:
                    inv_html = "<div style='color:#888; font-size:12px; padding:8px; text-align:center;'>(Nothing to sacrifice)</div>"
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
                        # Highlight items that match this god's preference
                        from .room_actions import _altar_gods
                        gd = _altar_gods()[blessed_id]
                        match_glyph = ""
                        if gd['item_type'] is None:
                            match_glyph = ""  # Loki accepts anything
                        elif gd['item_type'] == 'sealed' and getattr(item, 'is_sealed', False):
                            match_glyph = " <span style='color:#4CAF50;'>✓</span>"
                        elif gd['item_type'] is not None and gd['item_type'] != 'sealed' and isinstance(item, gd['item_type']):
                            match_glyph = " <span style='color:#4CAF50;'>✓</span>"
                        cmd_str = f"s{i + 1}"
                        inv_html += (
                            f"<div class='taprow' data-zcmd='{cmd_str}' "
                            f"onclick=\"window.__zotTap('{cmd_str}', this)\">"
                            f"{item_str}{match_glyph}{sealed_tag}{buc_tag}"
                            f"</div>"
                        )

                html_code = f"""
                    <div style="font-family: monospace; font-size: 12px; display: flex; flex-direction: column; max-height: 100%; overflow: hidden;">
                        {achievement_notifications}
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                            <div style="flex-shrink:0;">{altar_sprite}</div>
                            <div style="flex:1;">
                                <div style="font-size: 14px; font-weight: bold; color: {blessed_god.get('color','#DDD')};">
                                    Sacrifice to {blessed_god.get('symbol','?')} {blessed_god.get('name','Unknown')}
                                </div>
                                <div style="font-size: 10px; color: #AAA;">
                                    Craves: <b style="color:#FFD700;">{blessed_god.get('item_label','?')}</b> &middot; <span style='color:#4CAF50;'>✓</span> = match
                                </div>
                            </div>
                        </div>
                        {player_stats_html}
                        <div style="color: #DDD; font-size: 11px; font-weight: bold; margin: 6px 0 4px 0;">Tap an item to offer:</div>
                        <div style="border: 1px solid #555; padding: 4px; border-radius: 3px; max-height: calc(100vh - 280px); overflow-y: auto;">
                            {inv_html}
                        </div>
                        <div class='hudchips' style='margin-top:8px;'>
                            <div class='hudchip exit' data-zcmd='cancel'
                                 onclick="window.__zotTap('cancel', this)">&larr; BACK</div>
                            <div class='hudchip' data-zcmd='i'
                                 onclick="window.__zotTap('i', this)">INVENTORY</div>
                        </div>
                    </div>
                """
                current_commands_text = "Tap matching item to sacrifice | BACK to return"

            else:
                # ---------- DEFAULT ALTAR VIEW (room-panel + map) ----------
                # Two action chips: Pray (claim current tier reward) and
                # Sacrifice (open the picker to feed piety).  The Pray
                # chip's subtitle shows the current-tier reward inline.
                floor = gs.my_tower.floors[gs.player_character.z]
                grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
                hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()

                action_cards_html = (
                    "<div class='altar-actions dual' style='margin-top:6px;'>"
                    "<div class='taprow altar-act blessing' data-zcmd='pray' "
                    "onclick=\"window.__zotTap('pray', this)\">"
                    f"<div class='aname'>Pray</div>"
                    f"<div class='ameta'>claim blessing</div>"
                    "</div>"
                    "<div class='taprow altar-act sacrifice' data-zcmd='sac' "
                    "onclick=\"window.__zotTap('sac', this)\">"
                    "<div class='aname'>Sacrifice</div>"
                    f"<div class='ameta'>offer {blessed_god.get('item_label','?').lower()}</div>"
                    "</div>"
                    "</div>"
                )

                altar_html = f"""
                    <div style="border: 2px solid #555; border-radius: 3px; padding: 8px 10px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                            <div style="flex-shrink:0;">{altar_sprite}</div>
                            <div style="flex:1; min-width:0;">
                                <div style="font-size: 15px; font-weight: bold; color: {blessed_god.get('color','#DDD')}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                                    {blessed_god.get('symbol','?')} {blessed_god.get('name','Unknown')}
                                </div>
                                <div style="font-size: 11px; color: #AAA;">
                                    {blessed_god.get('title','')} &middot; craves <b style="color:#FFD700;">{blessed_god.get('item_label','?')}</b>
                                </div>
                            </div>
                        </div>
                        {action_cards_html}
                    </div>
                """

                html_code = f"""
                    <div style="font-family: monospace; font-size: 12px;">
                        {achievement_notifications}
                        {player_stats_html}
                        <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                            <div class="bottom-pinned-zone">
                              <div class="room-panel" style="width: 100%;">{altar_html}</div>
                              <div>{grid_html}</div>
                              {hud_chips_html}
                              {bigdpad_html}
                            </div>
                        </div>
                    </div>
                """
                current_commands_text = "Tap Pray or Sacrifice | n/s/e/w = step away"

        elif gs.prompt_cntl == "pool_mode":
            # POOL VIEW - Simplified: Map | Pool Info
            
            # Check for lantern
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break

            current_floor = gs.my_tower.floors[gs.player_character.z]
            room = current_floor.grid[gs.player_character.y][gs.player_character.x]
            pool_info = room.properties.get('pool_info', {})

            pool_info.get('name', 'Mysterious Pool')
            pool_info.get('symbol', '')
            pool_info.get('color', '#00CED1')
            pool_info.get('description', 'A basin of water.')

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()

            # Pool sprite - check for ancient waters variant
            pool_variant = 'ancient' if room.properties.get('is_ancient') else None
            pool_sprite = generate_room_sprite_html('P', variant=pool_variant, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            # Pool info box - simple and clean
            pool_html = f"""
                <div style="
                            border: 2px solid #555;
                            border-radius: 3px;
                            padding: 8px;
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

            # Decision prompt — tappable
            pool_html += """
                <div class='altar-actions'>
                    <div class='taprow altar-act mystic' data-zcmd='dr'
                         onclick="window.__zotTap('dr', this)">
                        <div class='aname'>Drink from the Basin</div>
                        <div class='ameta'>Effects unknown until you drink&hellip;</div>
                    </div>
                </div>
                """

            pool_html += '</div>'

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{pool_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
</div>
                """
            # Build pool commands with lantern if available
            current_commands_text = "Tap to drink | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "warp_mode":
            # WARP MODE - 2 columns: Map | Warp Info

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            # Warp is a forced binary choice (Resist / Enter), no movement —
            # but the hud-chips helper still gives us INVENTORY / LANTERN /
            # STAIRS chips that stay useful when relevant.
            hud_chips_html, _bigdpad_warp = self._build_map_hud_and_dpad_html()
            
            # Check if this is a vault warp
            room = floor.grid[gs.player_character.y][gs.player_character.x]
            is_vault_warp = room.properties.get('vault_warp', False)
            
            vault_warning = ""
            if is_vault_warp:
                vault_warning = (
                    '<div style="color:#F44336; font-size:11px; font-weight:bold; margin-top:2px;">'
                    '⚠ Vault energy &mdash; may seal you in.'
                    '</div>'
                )

            # Warp info box + binary tap choice.  Stacked (not dual)
            # so Resist/Enter sit on top of each other -- the warp is a
            # narrative beat and benefits from the more deliberate
            # vertical pace.
            warp_sprite = generate_room_sprite_html('W', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))
            warp_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 6px 8px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <div style="flex-shrink:0;">{warp_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.3;">
                             A swirling portal pulls at you. Reality bends.
                        </div>
                    </div>
                    {vault_warning}
                    <div class='altar-actions' style='margin-top:4px;'>
                        <div class='taprow altar-act blessing' data-zcmd='y'
                             onclick="window.__zotTap('y', this)">
                            <div class='aname'>Resist the Warp</div>
                            <div class='ameta'>INT check &mdash; stay here if you pass</div>
                        </div>
                        <div class='taprow altar-act mystic' data-zcmd='n'
                             onclick="window.__zotTap('n', this)">
                            <div class='aname'>Enter the Portal</div>
                            <div class='ameta'>step in willingly, wherever it leads</div>
                        </div>
                    </div>
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{warp_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                        </div>
                    </div>
                </div>
                """
            current_commands_text = "Tap Resist or Enter"

        elif gs.prompt_cntl == "stairs_up_mode":
            # STAIRS UP MODE - 2 columns: Map | Stairs Info
            
            # Check for lantern
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break
            
            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()

            # Stairs info box
            stairs_sprite = generate_room_sprite_html('U', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))
            stairs_html = f"""
                <div style="
                            border: 2px solid #555;
                            border-radius: 3px;
                            padding: 8px;
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
                    
                    <div class='altar-actions'>
                        <div class='taprow altar-act blessing' data-zcmd='u'
                             onclick="window.__zotTap('u', this)">
                            <div class='aname'>Ascend the Stairs</div>
                            <div class='ameta'>Climb upward toward the surface</div>
                        </div>
                    </div>
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{stairs_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
</div>
                """
            # Build stairs up commands with lantern if available
            current_commands_text = "Tap to ascend | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "stairs_down_mode":
            # STAIRS DOWN MODE - 2 columns: Map | Stairs Info
            
            # Check for lantern
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break
            
            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()

            # Stairs info box
            stairs_down_sprite = generate_room_sprite_html('D', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))
            stairs_html = f"""
                <div style="
                            border: 2px solid #555;
                            border-radius: 3px;
                            padding: 8px;
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
                    
                    <div class='altar-actions'>
                        <div class='taprow altar-act reforge' data-zcmd='d'
                             onclick="window.__zotTap('d', this)">
                            <div class='aname'>Descend Deeper</div>
                            <div class='ameta'>Venture into the darkness below</div>
                        </div>
                    </div>
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{stairs_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
</div>
                """
            # Build stairs down commands with lantern if available
            current_commands_text = "Tap to descend | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "library_mode":
            # LIBRARY VIEW - 2 columns: Map | Library Info

            # Check for lantern
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()

            # Get library info from room
            current_room = floor.grid[gs.player_character.y][gs.player_character.x]
            coords_key = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            has_searched = coords_key in gs.searched_libraries

            # Library sprite - check for codex variant
            lib_variant = 'codex' if current_room.properties.get('has_codex') else None
            library_sprite = generate_room_sprite_html('L', variant=lib_variant, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            # Library body — tappable Rummage card when unsearched,
            # muted info pill once searched.
            if has_searched:
                lib_body = (
                    '<div class="roominfo">Already rummaged &mdash; the shelves are bare.</div>'
                )
            else:
                lib_body = (
                    '<div style="color: #DAA520; font-size: 12px; margin: 4px 0 8px 0; font-style: italic;">'
                    'Hidden knowledge awaits discovery&hellip;'
                    '</div>'
                    "<div class='altar-actions'>"
                    "<div class='taprow altar-act offering' data-zcmd='r' "
                    "onclick=\"window.__zotTap('r', this)\">"
                    "<div class='aname'>Rummage for Books</div>"
                    "<div class='ameta'>Search the shelves for spell scrolls and lore</div>"
                    "</div>"
                    "</div>"
                )

            library_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                        <div style="flex-shrink:0;">{library_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.4;">
                             Towering shelves filled with dusty tomes surround you. The air is thick with the scent of old parchment and forgotten knowledge.
                        </div>
                    </div>
                    {lib_body}
                </div>
                """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}

                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{library_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
</div>
                """
            # Build library commands with lantern if available
            current_commands_text = "Tap Rummage | i = inventory" if not has_searched else "i = inventory"
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
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
            coords = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            has_key = coords in gs.dungeon_keys
            
            # Build action prompt based on key status
            if has_key:
                action_html = (
                    "<div class='altar-actions'>"
                    "<div class='taprow altar-act unlock' data-zcmd='u' "
                    "onclick=\"window.__zotTap('u', this)\">"
                    "<div class='aname'>Unlock the Dungeon</div>"
                    "<div class='ameta'>Use your key to break the seal</div>"
                    "</div>"
                    "</div>"
                )
            else:
                action_html = (
                    "<div class='roominfo' style='color:#FF6B6B;'>"
                    "Find the key &mdash; defeat monsters on this floor."
                    "</div>"
                )

            # Check if master dungeon variant
            room_d = floor.grid[gs.player_character.y][gs.player_character.x]
            dng_variant = 'master' if room_d.properties.get('is_master') else None
            dungeon_sprite = generate_room_sprite_html('N', variant=dng_variant, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            dungeon_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 8px 10px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                        <div style="flex-shrink:0;">{dungeon_sprite}</div>
                        <div style="color: #DDD; font-size: 13px; line-height: 1.3;">
                            A heavy iron door bars your way. Ancient runes glow faintly on its surface.
                        </div>
                    </div>
                    <div style="margin-bottom: 6px;">
                        <span style="color: #4CAF50; font-size: 13px; font-weight: bold;">[LOCKED]</span>
                        <span style="color: #BBB; font-size: 11px;"> a monster on this floor holds the key&hellip;</span>
                    </div>
                    {action_html}
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{dungeon_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            # Only show unlock command if player has key
            if has_key:
                current_commands_text = "Tap Unlock | i = inventory"
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
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
            coords = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            already_looted = coords in gs.looted_dungeons
            
            if already_looted:
                loot_body = "<div class='roominfo'>Already Looted &mdash; the chamber is bare.</div>"
            else:
                # Command is 'r' (rummage) — the old HTML said 'l' which was
                # a documentation bug; the handler always wanted 'r'.
                loot_body = (
                    "<div class='altar-actions'>"
                    "<div class='taprow altar-act loot' data-zcmd='r' "
                    "onclick=\"window.__zotTap('r', this)\">"
                    "<div class='aname'>Rummage for Treasure</div>"
                    "<div class='ameta'>Claim your reward</div>"
                    "</div>"
                    "</div>"
                )
            dungeon_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 8px 10px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column;">
                    <div style="color: #DDD; font-size: 13px; line-height: 1.3; margin-bottom: 8px;">
                        The iron door stands open. {'The chamber has been emptied.' if already_looted else 'Treasures glint in the darkness within.'}
                    </div>
                    {loot_body}
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{dungeon_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            if not already_looted:
                current_commands_text = "Tap Rummage | i = inventory"
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
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
            coords = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            already_looted = coords in gs.looted_tombs
            
            # Get tomb variant
            room_t = floor.grid[gs.player_character.y][gs.player_character.x]
            tomb_variant = 'cursed' if room_t.properties.get('is_cursed') else None
            tomb_sprite = generate_room_sprite_html('T', variant=tomb_variant, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            # Build tomb body — binary choice (raid vs pay respects) when
            # unplundered, muted info pill once already looted.
            if already_looted:
                tomb_body = (
                    '<div class="roominfo">This tomb has already been raided.</div>'
                )
            else:
                tomb_body = (
                    "<div class='altar-actions dual' style='margin-top:6px;'>"
                    "<div class='taprow altar-act reforge' data-zcmd='r' "
                    "onclick=\"window.__zotTap('r', this)\">"
                    "<div class='aname'>Raid Tomb</div>"
                    "<div class='ameta'>treasure &middot; risk a guardian</div>"
                    "</div>"
                    "<div class='taprow altar-act blessing' data-zcmd='p' "
                    "onclick=\"window.__zotTap('p', this)\">"
                    "<div class='aname'>Pay Respects</div>"
                    "<div class='ameta'>honour &middot; quiet blessing</div>"
                    "</div>"
                    "</div>"
                )

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">
                              <div style="border: 2px solid #555; border-radius: 3px; padding: 6px 8px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column;">
                                  <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                                      <div style="flex-shrink:0;">{tomb_sprite}</div>
                                      <div style="color: #DDD; font-size: 12px; line-height: 1.3;">
                                          An ancient tomb lies before you, its stone lid cracked with age.
                                          <span style="color:#C8A96E; font-style:italic;"> The dead are watching.</span>
                                      </div>
                                  </div>
                                  {tomb_body}
                              </div>
                          </div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            if not already_looted:
                current_commands_text = "Tap Raid or Pay Respects | i = inventory"
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
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
            coords = (gs.player_character.x, gs.player_character.y, gs.player_character.z)
            already_harvested = coords in gs.harvested_gardens
            
            garden_sprite = generate_room_sprite_html('G', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            if already_harvested:
                garden_body = "<div class='roominfo'>Already Harvested &mdash; the garden lies barren.</div>"
            else:
                garden_body = (
                    "<div class='altar-actions'>"
                    "<div class='taprow altar-act blessing' data-zcmd='h' "
                    "onclick=\"window.__zotTap('h', this)\">"
                    "<div class='aname'>Harvest Ingredients</div>"
                    "<div class='ameta'>Gather potion components from the magical plants</div>"
                    "</div>"
                    "</div>"
                )
            garden_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                        <div style="flex-shrink:0;">{garden_sprite}</div>
                        <div style="color: #DDD; font-size: 12px;">
                            {'The garden lies barren, its magical plants already harvested.' if already_harvested else 'A lush magical garden blooms with glowing flowers, shimmering herbs, and crystalline plants. The air hums with arcane energy.'}
                        </div>
                    </div>
                    {garden_body}
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{garden_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            if not already_harvested:
                current_commands_text = "Tap to harvest | i = inventory"
            else:
                current_commands_text = "i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "fey_garden_mode":
            # FEY GARDEN VIEW - Special UI
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()

            # Get turns remaining
            turns_left = gs.ephemeral_gardens.get(gs.player_character.z, {}).get('turns_remaining', '?')

            fey_sprite = generate_room_sprite_html('G', variant='fey_garden', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

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

                            <div class='altar-actions'>
                                <div class='taprow altar-act devotion' data-zcmd='h'
                                     onclick="window.__zotTap('h', this)">
                                    <div class='aname'>Harvest Fey Ingredients</div>
                                    <div class='ameta'>Rare exotic flora &middot; {turns_left} turns remaining</div>
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
                            {player_stats_html}
                            <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                                <div class="bottom-pinned-zone">
                                  <div class="room-panel" style="width: 100%;">{fey_html}</div>
                                  <div>{grid_html}</div>
                                  {hud_chips_html}
                                  {bigdpad_html}
                                </div>
                            </div>
                        </div>
                    """
            current_commands_text = "Tap to harvest fey garden | i = inventory | n/s/e/w = move"

        elif gs.prompt_cntl == "oracle_mode":
            # ORACLE VIEW - Mystical mirror with quest hints
            
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break
            
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()

            oracle_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 8px 10px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                        <div style="flex-shrink:0;">{generate_room_sprite_html('O', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.3;">
                            A mystical mirror rippling with arcane energy. Glimpses of destiny dance within.
                        </div>
                    </div>
                    <div class='altar-actions dual' style='margin-top:6px;'>
                        <div class='taprow altar-act mystic' data-zcmd='g'
                             onclick="window.__zotTap('g', this)">
                            <div class='aname'>Gaze</div>
                            <div class='ameta'>quest hints</div>
                        </div>
                        <div class='taprow altar-act offering' data-zcmd='pantheon'
                             onclick="window.__zotTap('pantheon', this)">
                            <div class='aname'>Pantheon</div>
                            <div class='ameta'>piety with each god</div>
                        </div>
                    </div>
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{oracle_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            current_commands_text = "Tap Gaze or Pantheon | i = inventory"
            if has_lantern:
                current_commands_text += " | l = lantern"
            current_commands_text += " | n/s/e/w = move"

        elif gs.prompt_cntl == "blacksmith_mode":
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
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

            def _smith_card(cmd, cls, title, meta, enabled):
                if enabled:
                    return (
                        f"<div class='taprow altar-act {cls}' data-zcmd='{cmd}' "
                        f"onclick=\"window.__zotTap('{cmd}', this)\">"
                        f"<div class='aname'>{title}</div>"
                        f"<div class='ameta'>{meta}</div>"
                        f"</div>"
                    )
                return (
                    f"<div class='taprow altar-act {cls} disabled'>"
                    f"<div class='aname'>{title}</div>"
                    f"<div class='ameta'>{meta}</div>"
                    f"</div>"
                )

            w_repairable = bool(weapon and weapon.durability < weapon.max_durability)
            a_repairable = bool(armor  and armor.durability  < armor.max_durability)
            w_reforgeable = bool(weapon and not rfw_done)
            a_reforgeable = bool(armor  and not rfa_done)

            smith_cards = "<div class='altar-actions'>"
            smith_cards += _smith_card(
                '1', 'forge', 'Repair Weapon',
                f"{w_repair_cost}g &middot; restore {weapon.name}" if w_repairable
                    else ('Already at full durability' if weapon else 'No weapon equipped'),
                w_repairable)
            smith_cards += _smith_card(
                '2', 'forge', 'Repair Armor',
                f"{a_repair_cost}g &middot; restore {armor.name}" if a_repairable
                    else ('Already at full durability' if armor else 'No armor equipped'),
                a_repairable)
            smith_cards += _smith_card(
                '3', 'reforge', 'Reforge Weapon',
                f"{reforge_cost}g &middot; gamble: re-roll base ATK" if w_reforgeable
                    else ('Already reforged here' if rfw_done else 'No weapon equipped'),
                w_reforgeable)
            smith_cards += _smith_card(
                '4', 'reforge', 'Reforge Armor',
                f"{reforge_cost}g &middot; gamble: re-roll base DEF" if a_reforgeable
                    else ('Already reforged here' if rfa_done else 'No armor equipped'),
                a_reforgeable)
            smith_cards += "</div>"

            smith_sprite = generate_room_sprite_html('B', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))
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
                    {smith_cards}
                    <div style="color:#888; font-size:11px; margin-top:10px;">Gold: {gs.player_character.gold}g</div>
                </div>
            """
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{smith_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            current_commands_text = "Tap a service | i = inventory | n/s/e/w = move"

        elif gs.prompt_cntl == "shrine_mode":
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
            room = floor.grid[gs.player_character.y][gs.player_character.x]
            used = room.properties.get('shrine_used', False)
            shrine_sprite = generate_room_sprite_html('F', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            if used:
                shrine_body = (
                    "<div class='roominfo'>The shrine lies silent. "
                    "The spirit has passed on.</div>"
                )
            else:
                shrine_body = (
                    "<div class='altar-actions dual' style='margin-top:6px;'>"
                    "<div class='taprow altar-act blessing' data-zcmd='p' "
                    "onclick=\"window.__zotTap('p', this)\">"
                    "<div class='aname'>Pray</div>"
                    "<div class='ameta'>free &middot; bless / hint / silence</div>"
                    "</div>"
                    "<div class='taprow altar-act offering' data-zcmd='o' "
                    "onclick=\"window.__zotTap('o', this)\">"
                    "<div class='aname'>Offering</div>"
                    "<div class='ameta'>50g &middot; potion / scroll</div>"
                    "</div>"
                    "</div>"
                )
            shrine_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 6px 8px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <div style="flex-shrink:0;">{shrine_sprite}</div>
                        <div style="flex:1; min-width:0;">
                            <div style="color: #CCC; font-size: 13px; font-weight: bold;">
                                SHRINE OF THE FALLEN
                            </div>
                            <div style="color: #BBB; font-size: 11px; font-style: italic;">
                                Names scratched into stone.
                            </div>
                        </div>
                    </div>
                    {shrine_body}
                </div>
            """
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{shrine_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            if used:
                current_commands_text = "i = inventory | n/s/e/w = move"
            else:
                current_commands_text = "Tap Pray or Offering | i = inventory | n/s/e/w = move"

        elif gs.prompt_cntl == "alchemist_mode":
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
            room = floor.grid[gs.player_character.y][gs.player_character.x]
            uses_left = room.properties.get('alch_uses', 3)
            potions = [item for item in gs.player_character.inventory.items if isinstance(item, Potion)]
            combining = room.properties.get('alch_combining', False)

            # Body varies by state:
            # - spent              -> info pill
            # - idle (not combining) -> "Combine Two Potions" action card
            # - combining           -> JS-side 2-tap picker on potion rows +
            #                          cancel card; the handler accepts a
            #                          single "X Y" command so we synthesise
            #                          that on the second tap.
            if uses_left <= 0:
                alch_body = '<div class="roominfo">The apparatus is spent. No more combinations here.</div>'
            elif not combining:
                alch_body = (
                    "<div class='altar-actions'>"
                    "<div class='taprow altar-act mystic' data-zcmd='c' "
                    "onclick=\"window.__zotTap('c', this)\">"
                    "<div class='aname'>Combine Two Potions</div>"
                    "<div class='ameta'>10% botch chance &middot; pick any two from your pack</div>"
                    "</div>"
                    "</div>"
                )
            else:
                # Inline the 2-tap picker helper.  On each render the shell
                # re-executes inline <script> tags, which also resets
                # __alchFirst so an old selection doesn't bleed across
                # turns.
                alch_js = """
                <script>
                  window.__alchFirst = null;
                  window.__alchSelect = function(idx, el) {
                    try {
                      if (window.__alchFirst === null) {
                        window.__alchFirst = idx;
                        el.classList.add('armed');
                      } else if (window.__alchFirst === idx) {
                        window.__alchFirst = null;
                        el.classList.remove('armed');
                      } else {
                        var combined = window.__alchFirst + ' ' + idx;
                        window.__alchFirst = null;
                        document.querySelectorAll('.taprow.potion-pick.armed').forEach(function(r){
                            r.classList.remove('armed');
                        });
                        window.__zotTap(combined, el);
                      }
                    } catch(e) {}
                  };
                </script>
                """
                picker_html = (
                    "<div style='color:#FF9800; font-size:12px; margin:8px 0 4px 0;'>"
                    "Pick TWO potions &mdash; tap the first, then tap the second to combine."
                    "</div>"
                )
                if not potions:
                    picker_html += "<div class='roominfo'>No potions in your pack to combine.</div>"
                else:
                    for i, p in enumerate(potions, 1):
                        picker_html += (
                            f"<div class='taprow spell potion-pick' "
                            f"onclick=\"window.__alchSelect({i}, this)\">"
                            f"{p.name}"
                            f"</div>"
                        )
                picker_html += (
                    "<div class='taprow cancel' data-zcmd='x' "
                    "onclick=\"window.__zotTap('x', this)\">"
                    "<span class='tapnum'>&times;</span>Cancel Combining</div>"
                )
                alch_body = alch_js + picker_html

            alch_sprite = generate_room_sprite_html('Q', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))
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
                        Uses remaining: {uses_left} &middot; Potions in pack: {len(potions)}
                    </div>
                    {alch_body}
                </div>
            """
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{alch_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            if combining:
                current_commands_text = "Tap two potions to combine | x = cancel | n/s/e/w = move"
            elif uses_left <= 0:
                current_commands_text = "Spent | i = inventory | n/s/e/w = move"
            else:
                current_commands_text = "Tap Combine | i = inventory | n/s/e/w = move"

        elif gs.prompt_cntl == "war_room_mode":
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
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

            # Two action cards.  Each is tappable when usable, greyed
            # with a contextual tapnote otherwise (already-used, active,
            # or — for raid — no-op while the raid is already running).
            intel_card = (
                "<div class='taprow altar-act detect disabled'>"
                "<div class='aname'>Intel</div>"
                "<div class='ameta'>Already used here</div>"
                "<span class='tapnote'>spent</span></div>"
            ) if intel_used else (
                "<div class='taprow altar-act detect' data-zcmd='1' "
                "onclick=\"window.__zotTap('1', this)\">"
                "<div class='aname'>Intel</div>"
                "<div class='ameta'>Free &middot; reveal all rooms on the next floor</div>"
                "</div>"
            )
            if raid_used:
                raid_card = (
                    "<div class='taprow altar-act reforge disabled'>"
                    "<div class='aname'>Raid Mode</div>"
                    "<div class='ameta'>Already used here</div>"
                    "<span class='tapnote'>spent</span></div>"
                )
            elif raid_active:
                raid_card = (
                    f"<div class='taprow altar-act reforge disabled'>"
                    f"<div class='aname'>Raid Mode</div>"
                    f"<div class='ameta'>Active &middot; {raid_turns} turns remaining</div>"
                    f"<span class='tapnote'>running</span></div>"
                )
            else:
                raid_card = (
                    f"<div class='taprow altar-act reforge' data-zcmd='2' "
                    f"onclick=\"window.__zotTap('2', this)\">"
                    f"<div class='aname'>Raid Mode</div>"
                    f"<div class='ameta'>{raid_cost}g &middot; +50% XP / +25% monster ATK for 10 turns</div>"
                    f"</div>"
                )

            war_sprite = generate_room_sprite_html('K', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))
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
                    <div class='altar-actions'>
                        {intel_card}
                        {raid_card}
                    </div>
                    <div style="color:#888; font-size:11px; margin-top:10px;">Gold: {gs.player_character.gold}g</div>
                </div>
            """
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{war_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            current_commands_text = "Tap a service | i = inventory | n/s/e/w = move"

        elif gs.prompt_cntl == "taxidermist_mode":
            # TAXIDERMIST VIEW
            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
            room = floor.grid[gs.player_character.y][gs.player_character.x]

            is_bug_tax = room.properties.get('is_bug_taxidermist', False)
            collection_status = get_collection_status(gs.player_character)
            # Filter collections: bug taxidermist shows only bug collections, regular shows only non-bug
            collection_status = [(name, data, pieces, complete) for name, data, pieces, complete in collection_status
                                 if bool(data.get('is_bug')) == is_bug_tax]
            get_player_trophies(gs.player_character)
            completable = [(name, data) for (name, data, pieces, complete) in collection_status
                           if complete and not room.properties.get(f'completed_{name}')]
            [name for (name, data, pieces, complete) in collection_status
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

            # Completable collections — each a tappable card that sends
            # the matching digit to process_taxidermist_action.
            complete_html = ""
            for idx, (cname, cdata) in enumerate(completable, 1):
                complete_html += (
                    f"<div class='taprow altar-act offering' data-zcmd='{idx}' "
                    f"onclick=\"window.__zotTap('{idx}', this)\">"
                    f"<div class='aname'>Turn in {cname}</div>"
                    f"<div class='ameta'>{cdata['reward_name']}</div>"
                    f"</div>"
                )
            if not complete_html:
                complete_html = "<div class='roominfo'>No collections ready to turn in.</div>"
            else:
                complete_html = f"<div class='altar-actions'>{complete_html}</div>"

            # Sell-all / exit action cards (always available).
            trophy_count_peek = sum(getattr(t,'count',1) for t in gs.player_character.inventory.items if isinstance(t, Trophy))
            trophy_val_peek = sum(t.value * getattr(t,'count',1) for t in gs.player_character.inventory.items if isinstance(t, Trophy))
            tail_html = "<div class='altar-actions'>"
            if trophy_count_peek > 0:
                tail_html += (
                    f"<div class='taprow altar-act bless' data-zcmd='s' "
                    f"onclick=\"window.__zotTap('s', this)\">"
                    f"<div class='aname'>Sell All Trophies</div>"
                    f"<div class='ameta'>{trophy_count_peek} piece(s) &middot; +{trophy_val_peek} gold</div>"
                    f"</div>"
                )
            tail_html += (
                "<div class='taprow cancel' data-zcmd='x' "
                "onclick=\"window.__zotTap('x', this)\">"
                "<span class='tapnum'>&times;</span>Leave Taxidermist</div>"
            )
            tail_html += "</div>"

            trophy_count = sum(getattr(t,'count',1) for t in gs.player_character.inventory.items if isinstance(t, Trophy))
            trophy_val = sum(t.value * getattr(t,'count',1) for t in gs.player_character.inventory.items if isinstance(t, Trophy))

            tax_sprite = generate_room_sprite_html('X', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))
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
                    {complete_html}
                    {tail_html}
                </div>"""

            html_code = f"""
                <div style='font-family: monospace; font-size: 12px;'>
                    {achievement_notifications}
                    {player_stats_html}
                    <div style='display: flex; flex-direction: column; align-items: center; gap: 10px;'>
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style='width: 100%;'>{tax_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>"""
            current_commands_text = "Tap a collection or Sell All | i = inventory | n/s/e/w = move"

        elif gs.prompt_cntl == "towel_action_mode":
            # TOWEL ACTION VIEW

            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)
            hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()

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
            
            # Grey out Wipe Face / Wipe Hands when the player doesn't
            # actually have the status effects they'd cure — prevents the
            # "did anything happen?" silent-no-op trap.
            _pc_effects = gs.player_character.status_effects
            _face_curable = ('Blinded', 'Cream Pie', 'Venom Blind', 'Flash Blind')
            _face_active = [e for e in _face_curable if e in _pc_effects]
            _hands_active = [e for e in ('Slippery Hands', 'Greasy') if e in _pc_effects]

            if _face_active:
                face_card = (
                    "<div class='taprow altar-act blessing' data-zcmd='2' "
                    "onclick=\"window.__zotTap('2', this)\">"
                    "<div class='aname'>Wipe Face</div>"
                    f"<div class='ameta'>Cure {', '.join(e.lower() for e in _face_active)}</div>"
                    "</div>"
                )
            else:
                face_card = (
                    "<div class='taprow altar-act blessing disabled'>"
                    "<div class='aname'>Wipe Face</div>"
                    "<div class='ameta'>Nothing to wipe off — your face is clear</div>"
                    "<span class='tapnote'>not needed</span></div>"
                )

            if _hands_active:
                hands_card = (
                    "<div class='taprow altar-act offering' data-zcmd='3' "
                    "onclick=\"window.__zotTap('3', this)\">"
                    "<div class='aname'>Wipe Hands</div>"
                    f"<div class='ameta'>Cure {', '.join(e.lower() for e in _hands_active)}</div>"
                    "</div>"
                )
            else:
                hands_card = (
                    "<div class='taprow altar-act offering disabled'>"
                    "<div class='aname'>Wipe Hands</div>"
                    "<div class='ameta'>Nothing to wipe off — your hands are dry</div>"
                    "<span class='tapnote'>not needed</span></div>"
                )

            towel_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 12px;">
                    <div style="color: #CCC; font-weight: bold; font-size: 12px; margin-bottom: 8px;">
                        [TOWEL] Towel{towel_wetness}
                    </div>
                    <div style="color: #DDD; font-size: 12px; margin-bottom: 10px;">
                        What do you want to do with the towel?
                    </div>
                    <div class='altar-actions'>
                        <div class='taprow altar-act mystic' data-zcmd='1'
                             onclick="window.__zotTap('1', this)">
                            <div class='aname'>Wear Over Face</div>
                            <div class='ameta'>Blind yourself &mdash; protection from gaze attacks</div>
                        </div>
                        {face_card}
                        {hands_card}
                        <div class='taprow cancel' data-zcmd='c'
                             onclick="window.__zotTap('c', this)">
                            <span class='tapnum'>&times;</span>Cancel
                        </div>
                    </div>
                </div>
            """
            
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="bottom-pinned-zone">
                          <div class="room-panel" style="width: 100%;">{towel_html}</div>
                          <div>{grid_html}</div>
                          {hud_chips_html}
                          {bigdpad_html}
                        </div>
                    </div>
                </div>
            """
            current_commands_text = "Tap an action | c = cancel"
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
                    current_row_html += '<div style="width: 40px; height: 40px; background: #121213; border: 2px solid #3a3a3c; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; color: #FFF; border-radius: 4px;"></div>'
            current_row_html += '</div>'

            guess_count = len(gs.zotle_puzzle['guesses']) if gs.zotle_puzzle else 0

            # In-body QWERTY keyboard with Wordle-style letter coloring.
            # keyboard_used maps letters to their best-known status; we
            # tint each key accordingly so the player sees at a glance
            # which letters are eliminated / present / nailed.
            kbd_used = (gs.zotle_puzzle or {}).get('keyboard_used', {}) or {}
            kbd_rows = [
                ['Q','W','E','R','T','Y','U','I','O','P'],
                ['A','S','D','F','G','H','J','K','L'],
                ['Z','X','C','V','B','N','M'],
            ]
            pz_kbd_html = ""
            for row in kbd_rows:
                row_html = ""
                for letter in row:
                    cmd = f"__pz_k_{letter.lower()}"
                    status = kbd_used.get(letter, '')
                    cls = "pz-key"
                    if status == 'correct':
                        cls += " pz-correct"
                    elif status == 'present':
                        cls += " pz-present"
                    elif status == 'absent':
                        cls += " pz-absent"
                    row_html += (
                        f"<div class='{cls}' data-zcmd='{cmd}' "
                        f"onclick=\"window.__zotTap('{cmd}', this)\">{letter}</div>"
                    )
                pz_kbd_html += f"<div class='pz-kbd-row'>{row_html}</div>"

            # Action chips: ENTER (submits 5-letter guess), BACKSPACE,
            # LEAVE (back to game_loop). ENTER dims when guess incomplete.
            full_guess = ''.join(current_guess)
            enter_cls = "hudchip" if len(full_guess) == 5 else "hudchip nm-empty"
            pz_actions_html = (
                "<div class='hudchips' style='margin: 8px 4px;'>"
                "<div class='hudchip exit' data-zcmd='__pz_bs' "
                "onclick=\"window.__zotTap('__pz_bs', this)\">&#9003; BACKSPACE</div>"
                f"<div class='{enter_cls}' data-zcmd='__pz_send' "
                "onclick=\"window.__zotTap('__pz_send', this)\">ENTER &#9654;</div>"
                "<div class='hudchip exit' data-zcmd='x' "
                "onclick=\"window.__zotTap('x', this)\">LEAVE</div>"
                "</div>"
            )

            # Dialog/instructions in the room box
            zotle_sprite = generate_room_sprite_html('Z', seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))
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
                        Guesses: {guess_count}
                    </div>
                </div>
            """

            html_code = f"""
                <style>
                  .pz-kbd-row {{ display: flex; gap: 4px; justify-content: center;
                                   margin: 4px 2px; }}
                  .pz-key {{
                    flex: 1 1 0;
                    min-width: 0;
                    max-width: 38px;
                    height: 44px;
                    line-height: 42px;
                    background: linear-gradient(180deg, #3a3a3a 0%, #1f1f1f 100%);
                    border: 1px solid #555;
                    border-radius: 5px;
                    color: #EEE;
                    font-family: 'Courier New', monospace;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                    cursor: pointer;
                    -webkit-tap-highlight-color: transparent;
                    box-shadow: 0 1px 0 #0a0a0a inset;
                    transition: transform 60ms ease-out, background 100ms ease-out;
                  }}
                  .pz-key:active {{
                    transform: scale(0.92);
                    background: linear-gradient(180deg, #5a5a5a 0%, #303030 100%);
                  }}
                  .pz-key.pz-correct {{
                    background: linear-gradient(180deg, #538d4e 0%, #386033 100%);
                    border-color: #6db263; color: #FFF;
                  }}
                  .pz-key.pz-present {{
                    background: linear-gradient(180deg, #b59f3b 0%, #806f25 100%);
                    border-color: #d4bc52; color: #FFF;
                  }}
                  .pz-key.pz-absent {{
                    background: linear-gradient(180deg, #2a2a2c 0%, #161618 100%);
                    border-color: #3a3a3c; color: #555;
                  }}
                </style>
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="padding: 8px;">
                        {puzzle_html}
                    </div>
                    {pz_actions_html}
                    <div style="margin-top:6px;">{pz_kbd_html}</div>
                </div>
            """
            current_commands_text = ""
            needs_numbers = False

        elif gs.prompt_cntl == "zotle_teleporter_mode":
            # ZOTLE TELEPORTER VIEW - Compact display for mobile

            floor = gs.my_tower.floors[gs.player_character.z]
            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Calculate valid coordinate ranges
            len(gs.my_tower.floors)
            typed_coords = (self.input_field.value or "").strip()

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
                    <div class="tp-slate">{typed_coords or '&nbsp;'}</div>
                </div>
            """

            # HTML numpad for the teleporter so the bottom toga numpad
            # stops being a problem.  Digits append, comma separates
            # x,y,z, BACKSPACE clears last char, SEND submits, CANCEL
            # backs out.
            tp_keys = [
                ('1','2','3'),
                ('4','5','6'),
                ('7','8','9'),
                (',','0','__tp_bs'),
            ]
            tp_pad_html = "<div class='tp-pad'>"
            for row in tp_keys:
                for k in row:
                    if k == '__tp_bs':
                        tp_pad_html += (
                            "<div class='tp-key tp-bs' data-zcmd='__tp_bs' "
                            "onclick=\"window.__zotTap('__tp_bs', this)\">&#9003;</div>"
                        )
                    else:
                        cmd = f"__tp_d_{k}" if k != ',' else "__tp_comma"
                        tp_pad_html += (
                            f"<div class='tp-key' data-zcmd='{cmd}' "
                            f"onclick=\"window.__zotTap('{cmd}', this)\">{k}</div>"
                        )
            tp_pad_html += "</div>"
            tp_actions_html = (
                "<div class='hudchips' style='margin-top:8px;'>"
                "<div class='hudchip' data-zcmd='__tp_send' "
                "onclick=\"window.__zotTap('__tp_send', this)\">TELEPORT &#9654;</div>"
                "<div class='hudchip exit' data-zcmd='c' "
                "onclick=\"window.__zotTap('c', this)\">CANCEL</div>"
                "</div>"
            )

            html_code = f"""
                <style>
                  .tp-slate {{
                    font-family: 'Courier New', monospace; font-size: 22px;
                    letter-spacing: 4px; font-weight: bold; color: #FFD700;
                    text-align: center; padding: 10px; margin: 10px 0 0 0;
                    background: linear-gradient(180deg, #1a1608 0%, #0a0804 100%);
                    border: 2px solid #5a4a1a; border-radius: 6px;
                    min-height: 32px;
                  }}
                  .tp-pad {{ display: grid;
                              grid-template-columns: repeat(3, 64px);
                              grid-template-rows: repeat(4, 56px);
                              gap: 6px; justify-content: center;
                              margin: 12px auto 4px auto; }}
                  .tp-key {{
                    background: linear-gradient(180deg, #3a3a3a 0%, #1f1f1f 100%);
                    border: 1px solid #555; border-radius: 6px;
                    color: #EEE; font-family: 'Courier New', monospace;
                    font-size: 22px; font-weight: bold;
                    line-height: 54px; text-align: center;
                    cursor: pointer;
                    -webkit-tap-highlight-color: transparent;
                    box-shadow: 0 1px 0 #0a0a0a inset;
                    transition: transform 60ms ease-out, background 100ms ease-out;
                  }}
                  .tp-key:active {{ transform: scale(0.92);
                                     background: linear-gradient(180deg, #5a5a5a 0%, #303030 100%); }}
                  .tp-key.tp-bs {{ color: #FF8A80; border-color: #6a3a3a; }}
                </style>
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    {player_stats_html}
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
                        <div class="room-panel" style="width: 100%;">{teleporter_html}</div>
                        <div>{grid_html}</div>
                    </div>
                    {tp_pad_html}
                    {tp_actions_html}
                </div>
            """
            current_commands_text = "0-9 = digits | , = comma | c = cancel"
            needs_numbers = True

        elif gs.prompt_cntl == "library_read_decision_mode":
            # LIBRARY READ DECISION - Keep map and library visible with grimoire prompt
            
            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Get found spell from room
            current_room = floor.grid[gs.player_character.y][gs.player_character.x]
            found_spell = current_room.properties.get('found_spell')
            
            # Library sprite
            current_room = floor.grid[gs.player_character.y][gs.player_character.x]
            lib_variant = 'codex' if current_room.properties.get('has_codex') else None
            library_sprite = generate_room_sprite_html('L', variant=lib_variant, seed=(gs.player_character.x, gs.player_character.y, gs.player_character.z))

            # Spell info line — compact one-liner that includes the
            # INT-gated reveal when the player can decipher it.
            spell_info = ""
            if found_spell:
                if gs.player_character.intelligence >= 20:
                    spell_info = f'<div style="color: #DAA520; font-size: 12px; margin-top: 4px;"><b>{found_spell.name}</b> <span style="color: #AAA;">({found_spell.mana_cost} MP)</span></div>'
                else:
                    spell_info = '<div style="color: #888; font-size: 10px; margin-top: 4px; font-style: italic;">Arcane symbols&hellip; hard to decipher.</div>'

            # Library info box with grimoire decision — tappable Yes/No
            # in a 2-col grid so both buttons fit inside the 200px slot.
            library_html = f"""
                <div style="border: 2px solid #555; border-radius: 3px; padding: 6px 8px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <div style="flex-shrink:0;">{library_sprite}</div>
                        <div style="color: #DDD; font-size: 12px; line-height: 1.3;">
                            You found a grimoire among the dusty shelves!
                        </div>
                    </div>
                    {spell_info}
                    <div class='altar-actions dual' style='margin-top: 6px;'>
                        <div class='taprow altar-act offering' data-zcmd='y'
                             onclick="window.__zotTap('y', this)">
                            <div class='aname'>Read</div>
                            <div class='ameta'>decipher it</div>
                        </div>
                        <div class='taprow altar-act purify' data-zcmd='n'
                             onclick="window.__zotTap('n', this)">
                            <div class='aname'>Leave</div>
                            <div class='ameta'>return to shelf</div>
                        </div>
                    </div>
                </div>
            """

            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}

                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div class="room-panel" style="width: 100%;">{library_html}</div>
                        <div>{grid_html}</div>
                    </div>
</div>
            """
            current_commands_text = "Tap Read or Leave it"

        else:
            # MAP VIEW (for game_loop, confirm_quit, etc.)
            show_map = gs.prompt_cntl in ["game_loop", "confirm_quit", "flare_direction_mode", "upgrade_scroll_mode", "identify_scroll_mode"]

            grid_html = ""
            lantern_info_html = ""  # ADD THIS

            if show_map:
                floor = gs.my_tower.floors[gs.player_character.z]

                # ADD LANTERN INFO DISPLAY
                if gs.prompt_cntl == "game_loop":
                    lantern = None
                    for item in gs.player_character.inventory.items:
                        if isinstance(item, Lantern):
                            lantern = item
                            break

                    if lantern:
                        min(100, (lantern.fuel_amount / 10) * 100)

                        lantern_info_html = ""

                # Grid Container
                grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Inline scroll picker overlay: upgrade_scroll_mode +
            # identify_scroll_mode both present a numbered inventory
            # subset.  Render the list as tappable taprow cards beneath
            # the map so the player never has to type a number.
            scroll_picker_html = ""
            if gs.prompt_cntl == "upgrade_scroll_mode":
                scroll_name = gs.active_scroll_item.name if gs.active_scroll_item else "Scroll"
                # Same tier-to-max-level logic as items.py:2069+.
                _tier_levels = [
                    ("Eternal", 35), ("Cosmic", 30), ("Celestial", 25),
                    ("Divine", 20), ("Mythic", 17), ("Epic", 14),
                    ("Superior", 10), ("Greater", 6),
                ]
                max_up_level = 3
                for _tier, _lvl in _tier_levels:
                    if _tier in scroll_name:
                        max_up_level = _lvl
                        break
                up_items = [i for i in gs.player_character.inventory.items
                             if isinstance(i, (Weapon, Armor))]
                scroll_picker_html = (
                    f"<div style='text-align:center; color:#E040FB; font-weight:bold; margin-top:8px;'>"
                    f"{scroll_name}"
                    f"</div>"
                    f"<div style='text-align:center; color:#CE93D8; font-size:10px; margin-bottom:4px;'>"
                    f"Can upgrade items up to +{max_up_level}"
                    f"</div>"
                )
                if not up_items:
                    scroll_picker_html += "<div class='roominfo'>No weapons or armor to upgrade.</div>"
                else:
                    for idx, item in enumerate(up_items, 1):
                        item_display = item.get_display_name() if hasattr(item, 'get_display_name') else item.name
                        maxed = item.upgrade_level >= max_up_level
                        if maxed:
                            scroll_picker_html += (
                                f"<div class='taprow spell disabled'>"
                                f"{item_display}"
                                f"<span class='tapnote'>MAX for this scroll</span></div>"
                            )
                        else:
                            scroll_picker_html += (
                                f"<div class='taprow spell' data-zcmd='{idx}' "
                                f"onclick=\"window.__zotTap('{idx}', this)\">"
                                f"{item_display}</div>"
                            )
                scroll_picker_html += (
                    "<div class='taprow cancel' data-zcmd='c' "
                    "onclick=\"window.__zotTap('c', this)\">"
                    "<span class='tapnum'>&times;</span>Cancel Upgrade</div>"
                )
            elif gs.prompt_cntl == "identify_scroll_mode":
                # List unidentified Potion / Scroll / Spell / Weapon / Armor.
                _ident_items = []
                for itm in gs.player_character.inventory.items:
                    if isinstance(itm, (Potion, Scroll, Spell, Weapon, Armor)):
                        if not is_item_identified(itm):
                            _ident_items.append(itm)
                scroll_picker_html = (
                    "<div style='text-align:center; color:#E040FB; font-weight:bold; margin-top:8px;'>"
                    "Scroll of Identify"
                    "</div>"
                    "<div style='text-align:center; color:#CE93D8; font-size:10px; margin-bottom:4px;'>"
                    "Reveal the true name + stats of one item"
                    "</div>"
                )
                if not _ident_items:
                    scroll_picker_html += "<div class='roominfo'>Nothing unidentified in your inventory.</div>"
                else:
                    for idx, itm in enumerate(_ident_items, 1):
                        disp = get_item_display_name(itm) if 'get_item_display_name' in globals() else itm.name
                        scroll_picker_html += (
                            f"<div class='taprow spell' data-zcmd='{idx}' "
                            f"onclick=\"window.__zotTap('{idx}', this)\">"
                            f"{disp}</div>"
                        )
                scroll_picker_html += (
                    "<div class='taprow cancel' data-zcmd='c' "
                    "onclick=\"window.__zotTap('c', this)\">"
                    "<span class='tapnum'>&times;</span>Cancel Identify</div>"
                )

            # Inline Yes/No tap cards for the confirm_quit dialog so the
            # player never has to type y/n.  Rendered over the map view
            # (confirm_quit is in show_map above).
            confirm_quit_html = ""
            if gs.prompt_cntl == "confirm_quit":
                confirm_quit_html = """
                    <div style="text-align:center; color:#FFD700; font-weight:bold; margin-top:10px; font-size:14px;">
                        Quit the game?
                    </div>
                    <div class='altar-actions' style='max-width: 280px; margin-left:auto; margin-right:auto;'>
                        <div class='taprow altar-act reforge' data-zcmd='y'
                             onclick="window.__zotTap('y', this)">
                            <div class='aname'>Yes, Quit</div>
                            <div class='ameta'>Close the app (remember to save first)</div>
                        </div>
                        <div class='taprow altar-act blessing' data-zcmd='n'
                             onclick="window.__zotTap('n', this)">
                            <div class='aname'>No, Keep Playing</div>
                            <div class='ameta'>Back to the adventure</div>
                        </div>
                    </div>
                """

            # Inline d-pad for modes that need a direction pick during the
            # map view (currently flare_direction_mode — foresight and flee
            # have their own dedicated render blocks above).
            dpad_overlay_html = ""
            if gs.prompt_cntl == "flare_direction_mode":
                dpad_overlay_html = """
                    <div style="text-align:center; color:#FFD700; font-weight:bold; margin-top:8px;">
                        Shine the flare which way?
                    </div>
                    <div class='dpad'>
                        <div class='dpad-slot empty'></div>
                        <div class='taprow dpad-dir' data-zcmd='n' onclick="window.__zotTap('n', this)">N</div>
                        <div class='dpad-slot empty'></div>
                        <div class='taprow dpad-dir' data-zcmd='w' onclick="window.__zotTap('w', this)">W</div>
                        <div class='taprow dpad-cancel' data-zcmd='c' onclick="window.__zotTap('c', this)">CANCEL</div>
                        <div class='taprow dpad-dir' data-zcmd='e' onclick="window.__zotTap('e', this)">E</div>
                        <div class='dpad-slot empty'></div>
                        <div class='taprow dpad-dir' data-zcmd='s' onclick="window.__zotTap('s', this)">S</div>
                        <div class='dpad-slot empty'></div>
                    </div>
                """

            # HUD chips + d-pad — replace the bottom-panel INVENTORY/LANTERN
            # buttons and movement d-pad with HTML widgets that render
            # reliably on every device.
            hud_chips_html = ""
            bigdpad_html = ""
            empty_room_html = ""
            if gs.prompt_cntl == "game_loop":
                hud_chips_html, bigdpad_html = self._build_map_hud_and_dpad_html()
                # Empty-room placeholder card.  Keeps the layout stable
                # when the player isn't standing on a special tile --
                # the room-panel slot is always filled, so the map's
                # vertical position never shifts.
                empty_room_html = self._build_empty_room_panel_html()

            html_code = f"""
                <div style="font-family: monospace; font-size: 16px;">
                    {achievement_notifications}
                    {lantern_info_html}
                    <div class="bottom-pinned-zone">
                        {empty_room_html}
                        {grid_html}
                        {hud_chips_html}
                        {bigdpad_html}
                        {dpad_overlay_html}
                        {scroll_picker_html}
                        {confirm_quit_html}
                    </div>
                </div>
                """
            # Check if player has a lantern
            has_lantern = False
            for item in gs.player_character.inventory.items:
                if isinstance(item, Lantern):
                    has_lantern = True
                    break

            # DYNAMIC COMMAND TEXT GENERATION
            if gs.prompt_cntl == "game_loop":
                # Check what room player is on
                current_floor = gs.my_tower.floors[gs.player_character.z]
                current_room = current_floor.grid[gs.player_character.y][gs.player_character.x]

                base_commands = "tap a room = walk there | i = inventory"

                # Add lantern command if player has one
                if has_lantern:
                    base_commands += " | l = lantern"

                # Add mine command for dwarves standing next to an ore vein
                # (with mining charges left on this floor)
                from .game_systems import dwarf_mining_available
                if dwarf_mining_available(gs.player_character, gs.my_tower):
                    base_commands += " | m = mine"

                # Add stairs commands if on stairs
                if current_room.room_type == 'U':
                    current_commands_text = "tap a room = walk | u = up | i = inventory"
                    if has_lantern:
                        current_commands_text += " | l = lantern"
                elif current_room.room_type == 'D':
                    current_commands_text = "tap a room = walk | d = down | i = inventory"
                    if has_lantern:
                        current_commands_text += " | l = lantern"
                else:
                    current_commands_text = base_commands

            elif gs.prompt_cntl == "mine_direction_mode":
                current_commands_text = "n/s/e/w = mine direction | c = cancel"
            elif gs.prompt_cntl == "confirm_quit":
                current_commands_text = "Tap Yes or Keep Playing"
            elif gs.prompt_cntl == "chest_mode":
                current_commands_text = "o = open | i = inventory"
                if has_lantern:
                    current_commands_text += " | l = lantern"
                current_commands_text += " | n/s/e/w = move"
            elif gs.prompt_cntl == "pool_mode":
                current_commands_text = "dr = drink | i = inventory"
                if has_lantern:
                    current_commands_text += " | l = lantern"
                current_commands_text += " | n/s/e/w = move"
            elif gs.prompt_cntl == "altar_mode":
                if gs.altar_action:
                    current_commands_text = "# = sacrifice item | b = back"
                else:
                    current_commands_text = "s = sacrifice | d = detect | b = bless | u = purify | i = inventory | x = exit"
            elif gs.prompt_cntl == "warp_mode":
                current_commands_text = "y = resist | n = enter"
            elif gs.prompt_cntl == "flare_direction_mode":
                current_commands_text = "Tap a direction or Cancel"
            elif gs.prompt_cntl == "library_mode":
                current_commands_text = "r = rummage for books | i = inventory"
                if has_lantern:
                    current_commands_text += " | l = lantern"
                current_commands_text += " | n/s/e/w = move"
            elif gs.prompt_cntl == "library_read_decision_mode":
                current_commands_text = "Tap Read or Leave it"
            elif gs.prompt_cntl == "upgrade_scroll_mode":
                current_commands_text = "Tap an item to upgrade | c = cancel"
            elif gs.prompt_cntl == "identify_scroll_mode":
                current_commands_text = "Tap an item to identify | c = cancel"
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

        # Loot toasts overlay — fixed-position floating banners for items
        # the player just acquired. Empty when the queue is empty / all
        # toasts have expired.
        try:
            from .sprites.loot_toast import render_loot_toasts_html
            toast_html = render_loot_toasts_html()
        except Exception:
            toast_html = ''
        if toast_html:
            html_code = toast_html + html_code

        return html_code
    
    @staticmethod
    def _body_class_for_mode(prompt_cntl):
        """Body class string for the current prompt_cntl.

        ``full-bleed`` applies to splash, intro/main-menu, character
        creation, death and the game-loaded summary -- screens that
        own the whole viewport and would clash with the fixed
        stats+log top strip.  Everything else (gameplay, room modes,
        combat, vendor, etc.) gets the empty class so the strip shows.
        """
        full_bleed = {
            'splash', 'intro_story', 'main_menu', 'death_screen',
            'player_name', 'player_race', 'player_gender',
            'player_sprite', 'tourist_depth',
            'starting_shop', 'game_loaded_summary',
            'orb_game',
        }
        return 'full-bleed' if prompt_cntl in full_bleed else ''

    def wrap_html(self, content, log_lines=[]):
        """Wrap HTML content in a full document with mobile-optimized styling and fixed log."""
        # Convert log_lines to JavaScript-safe format
        import json
        log_lines_json = json.dumps(gs.log_lines)
        log_delays_json = json.dumps(gs.consume_log_delays())

        from .sprite_animator import generate_animator_js
        _sprite_animator_js = generate_animator_js()
        from .cavern_render import cavern_renderer_js
        _cavern_renderer_js = cavern_renderer_js()

        # Stats bar lives in the fixed top strip alongside the log.
        # Stash is set in generate_html() right after player_stats_html
        # is built.  On full-bleed screens (splash/intro/death) the
        # strip would clash with the backdrop, so we mark the body and
        # let CSS hide it (also keeps the live-update path in sync).
        stats_html = getattr(self, '_last_stats_html', '') or ''
        body_class = self._body_class_for_mode(gs.prompt_cntl)

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
                /* Bundled pixel font for retro chip styling (Press Start 2P,
                   OFL-licensed, latin subset embedded so it works offline in
                   the APK webview -- no network fetch). */
                @font-face {{
                    font-family: 'PressStart';
                    font-style: normal;
                    font-weight: 400;
                    font-display: swap;
                    src: url("data:font/woff2;base64,d09GMgABAAAAABJgAA0AAAAASFgAABILAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGhYcgzwGYACEbBEICvB00n4Lg0QAATYCJAOGdAQgBYRKB4ReG7k2IxE1HRM1iOA/JWg2xvD6obMqmE5SN4m6JErQGe1cnR7tTm21roiCRXGDph2W57zlE2hWfkyCDRZhurA4QpJZeJ7fH3Xufd9jvYGwAJrkBDcnoU4JS7aJ6zQ4wEsveVcau6YSMNkW5dRZkKLO7kl2gJ99Pu1cgBXilsXzxNXe312wJuAISuQ69LpAmygPOJGMosbv9O8fKPBxUDdsnCIs31VPLCJq8pmJK+q+O4R4UVF6lcpGGsmA+ctVGunAV3/7FmaFSTNZmPJ92eQtKF2y1Rr6/y1N6Yx01bXAVlgCUKk8KMZpgFl/5u/37Gi0sVYrvVtZ7nK74tp2Vme/ldxrAoNKh86llIYaDKq0FUKDyIWF4gAe22ycgtZjjJuJs/Vp39+v74B3YB+yQ62hxBJjrLUTa+Sy99Pd99cEAbEAQLyFMgwBkam6oK3xU+ciNfPcvhE6mZDmqLkWqDD0n1OuQAhC9KYOn4NBoU/niabLNmzGoo/+xw1ug9G9ztasWoJO56Zl61ETp6VJm7R+cvD8ZkwUIyroOEAERD5UKipJnfOhLrSmENhSWc6QqDOfQyh0tj+jiuXZ/8PnSYaaAyFm4rtroNK5XussnBuyoeJ5zoC6dKczmSccloW4oypBxUAoF5sxFQLcirAInR1MZjcgX4k1EysGSJ2M5k6neut6/27mwJd9UgEBelYHgCn+hjJAKlssT6Nb+z7hmPbscWyAorp5AYB5SJwFuA5AnyFHrMaflApHNJ7x+9UCg5cKiFNPUZr/iKRY64ru6S29YxCbarNtvi2yZbbLjsVGDlfh+VP9sQ79ByCOJUFJRyTFKnpWsDWbaXOvr/N7If+vgBkAhrjBYK4NDee34PsV+L4WIZYBuvuPvincl783AAKgATDVFSAXRr6c3JrN/3HGVa0aLTpwRps+/SqsqTWkSYca7bZt2tLsNLxYcRIkYXPIYUecwAHDhRsvUeIkSJIiTYEiJcpU9ajU66pOd6nRo8+QMQuWrFhz5MSZKzceAgQJFiJMuBix4sRL0uWybrvmNJi3bMGKK86547xUI/YMu+CeS3YUKXbTvrOq3FIozagypcq1IHN5Ir5QjHhpmDBjwe6oY45jwEMQH37CBKwTIk+GLDkqxITSok6DDk3adBkwZ8KUGQe27Ngz4s6HJy9+vG3wFS1CpCgJAiUS4W/QgElTJiDk/98A4AcAuQPyAZJ2ACkvAB6oAIABACppDAYfuDIBBwdtvWyhIRj9eiPiRtE2zhO4kUR6xplwhByIGdHEfl2lnhqraTbpW3ibCwPlFbCkAFDqFEs+ouId4rDYFIx3Rgp1JviWVtp0gLoZoOHhudAa3lXMO58l1rNuCTB3bALXXGnb/nuVbib5zIAjGHU0I+vqIX3dp0pfZIhBAJldd9NXY27Td77KTu2odNh1bNd/MmxWU60SgwDYrbYVsG5SAHPc3OnXRDqZZx5AN4/b+QP23IQU1ololz89jHe+3vpcMkt0lwM/573pXzp9PbXfizZscl0ELXO3a1UbZW84hcdS+ygg252g2kqvjynC9Zz5uT51374IQGxoIViy+r1aO2cyM1kuabuu5YAzwR0QDOVNMNfejiJ58vbRAC0ACLPuM673tXdTiQJqCKUJCSkIhFMSVoRCcGriaPVLaSFOCpqoMooEDSlcYkRUz4XwkApimZR+FhfXwZA7MYXyScHaPDaFYc9ss7gM5ZYs1QwfQMYZkEJYRVaGwLrE3ZDOqopH0WKhrKYyn5jgFnBKR8aVHwy1EDwOxPWwMKq6LAwr4eYDjbhnmEePgsSAzHtLsGN2LkSLRIgzniTDyUNzR6G8Ek9CE6wMyORehlJUVkKLRUvDhjbMGHMpCvC6v2xgNRXAwggUCRJ7PYSgTV5RpEvG1kdpwglup8CaTjp0/tZdr1688A6jRiAAYkX2jYaGI2yEUED4agQ4JpDdlCU2KgqlAuYHCKlez0mlj0QvcpGO1NK3dCvyfsXpVCbst9GllNVsQ/m0ecUNbEvtYUVwoaaijNyRgJRbfvMoDLqOhDUhD6bAXNSUZNyJX5IekmQF0UTzLC7AZFlcCQmxLmpK1rQZ1SDkaC+d0IVasLlKGNSTvKgXcxoCTsoYtZLGBXO0cUdZAhJxAg+O4C9r2GC83qogpN6xJx2xIGwwFrEk9VR+tHKBggk6U1LmwfkF1dp8yUJX3ga9eH9YtsMWX5wQqUZ21yGWFNq9ajBoEVsoSz36d5cSzFLbAJZ5HBsmU2S1hKJbU3Wc79U6Nu0xgKAelp0Z4jqLRPumclG2eKPlL+r190iKNpW7y5sA7cqgGMvWIEl+SE0N0tmH8mlGSxpVQE9Urd3YqVrA4oAp+2BKXB2A9K0eTRqj3WAoGXskoL132wA2/MvgLLOL0yqYLSBZEKCPLV8PkjVdB1SZ2IaBQd0U2Dakfm5sFl48kBeNEFPjhuqccG1xKdLMwtZahGBvKKj6sjd4NlQ2UZAigsnBtsxkmBAUrlaQNUGBWoRSctWWPDeHg9iWFt953iW8s41nKaqZgHL5RcUdtBmY0DFS28bLdxTjSGv0Ny4ptkZdtFbyxfXlBPJDC4Ka2InUcWZ417DMcPZAbTE6gjA8DIy0MWAeNVYPa4tlrhwoNDFkIcAYzAytW7JuIRhZsd7KzTSi50qCGnCvLdArficHWmmiCSHD/ERsIt1qdKQoYJHWYU6i20IBgh6JxJBmjvp7VLIwpFuZVnPEYIUCAskhO76ejxt9JGFxxlGRPKmMLhhBMW5gFMreRedqpVDNopuVpA5k2WxxghipqIfCBeIQRbeLoJs/OepnCw3rhRJpLwo3B29Qq6EQM9waX0tDbZe40xbbQ8/Qa5GCtQc+yGI3ByXFWSYyj81HTC3W1zqV4c3rHdDDtnUb32qt2mopLZvM3ZEnvGTljav/AAf3pR20pETliLUD5zAcEqZRuQ9zKv2DmWBzQez4zdVKH+VrRaAdiE1/2ETrXlpfGErt8QoFgzpPFunNUSa4VWFHgoo0idkyGesoICEQZhHswBR91la3rV3gEjWmUsVVpknJ6pmHX/KmF43M4y/mWPbQU4884NT8oSZ5LwGogx9eW6Gg7lmG/eALtL62Cp9ZUfqamgDfQ7nZ8bGexsAjpAPQHi/0A1pEaFHLboEV7d7dlF4Wbk7rt4KwRSduRJ4z0D893esysc4j7AYVAWuIKyXUddVmqQXZGi4jTAKLOSCwevool+taG4JeINVM5C9/6RKRoAwBZkHGFI/KetWPFCwGXCty3kllWldUY5t/MES0hG3Ha/tc6iFbK775b3PmP/6oxozEvPtWJK7CZJoPNvFwsXLq6RSsjK/OMOpSWGfdXTUUFhBOgAJILasEIC5mwLtlTPxoSoULOiJOa+8v6Dv5BrFchoD8fhVln2F87NH/B/mdN+WJ4DnP9UwOEZPJK3/7wNukPDMoq25+jO5DwuuANDPcW1YujJBA9wCSgw/8hen1aZwisQxxavv9nRFeeQ92LxUGPVGqmTPyNfIsbV5bpsOY5Zn7Cg7jmCvvKM055v3uQzHXQLfeJrTPa109NFJ030JNeFlVetcMGlNOVKhvhUzlCtCsKDcCRJFpo5FhHNpN3SVrrjbYoI4HLifJ0rYu4Qb3LM/gr95bjW2mvJxLSMwkrwkCVPbopYjpdwP9xOkFMwa5FkCOe25XVib8XSGvVIU5K1FfIlZ6K1l9nWjBqt8PSMTirPC+1WzipXQWgAeIBGev81ZJnSRzIe9URfVr8idW4VjoLi+ZiXaEr/9mAzAS/Epx1d5AgoU39Q0OqJTKc64NLg31Kbw++PLxlBz11UYvg93MTzlOTfCrms73QWn0HAWZlactcaDAjplYhAX1YEZdo8rBS/IHZ4oHSETVB+rHBwqhStc6AMQk5XmS6yhCfQXDgrAKDHX7EMzXxdeuOGcWDvl+QyTWUV8wt7se4jmo3csmwcjmsUUkxaa+ZH57WZEEC3kbDqgAReeRoFq6CoesJJ6pB6YvQVcBI0VeS3R9p8NLwpdzcbpV3PvfOwhKDol+mGS4O9MwFVeFDXm0AYvD7dgFnYOG3jRV9XiF4FecuOnM8CRU2vpkopbhKx7KfarCpzaTBFlfv/kfJxMN61HC6Xr3REx7WKz1hnFoxwCTW0XLpk0fPXYC1ErjyY/nY9l+Uvt5rkq6dNytY3UsitNePuss4/wnPo8xLKo75akhjLhUPAjjblOpnjfObJI5bvxrdCKY6sI/XycSypfTlSJWcI2PPdg3Xn7OwgjEJh4Y1AejzXCCNtAGaV4nk8eI9z9dXXZARXv7WVklkuvtdphJvRTe0U/xAawWvJyG+RLhGZ0ZFQvz4wgiRfMWkEFuhqeQSccJ5XPBW6YYaQv3qURhivQHhS7J91v2gf+6vPLp79wn47pD1rAckkBiNknOOtbOcYZNonH8SE14tzCdXq2skwcM4mu+UmA+hdubYq/yYFyppJZRX+l5LYV9teDdwZwji+o8AlhWkZsGcQ4YCKMIcGUs6tn8b3Vqj7pi7T67hgd/hShh7hbiYPL0FbuZrb3NaOSleDv2iNecJ0otEvBme7gEwrPYXLSXB37EQEt6DzeEeMkZzjZDR/roZl7PmFX4Hq4fu+9foRncGLo0G1y/iKBLOV/JVrvYj7o1K4r7I4mcsGHwlcXdB0BecrCv2L0r70MMFtGq82yPHwR3CGswxYG/cFaU3rrO4wfB8PP/weaL4HI+jpG83mzQTuLUxB9R14tT8IYJdK/XpC9//2S8K8KHqVj0ESnA+bUYGqY6X3E26L0SM9pa7svsLqooBnhBXsNCjeUndRMo6jx4+7VE0+hjASzwqLDJtGNnUQ4fMWQdebCuCD1XNWMCOuVaNxUhM+4zhH7IfZyPv0hisvibkEXok2mXsfeoI7UvSpznoaMuFDb06f8mAKK2w6lIRDx+F2Gcqyno9hWf5vWbX0x4JiajeI+I/7O6FU68x7ya9w7jfpykm+RvKierpLT/0+5NErUBjlaKu4vcpfux/sh5u+RCfDvt6mtKBeg497nU+xiWEy5rM8Pc99z+Oz7DlPj1MF8j3UgBCcwwsdV3p6jz34Vzb4NQN0uU0xWnpZabXKxZU0dAgauXK2RlmbNGfke9MM7qZ/jC2LKtrTNm6XcnkalivUfIprI24lDRtCxMz0vEURAh4IJlZM7rf4weA+qG0a0cn/xAGWxegACD3pvs54un8q/L9AHwuoH993c8rOp/+yvqRXiCTxEKYPDmtAJAZ43UB2QlyP7rXi+xmH7AtffY69Cf+A8Ul8e/Ac4U/SEfNxVPdx9g09ixNkUj8M3RGN/e1Y5rjgNArt1er3NCr+F9oyeSUJB4dwZSwUCXe63ZRo78IlVqTKX+RRDwgwIaJUi1qQV+rcBKOFKFwMdQQVNErndTVLzvU4zhuqY4asRNcWVzmeKpIKPibRWwWgxNiKBEfN1o3qIEqorR4WKiVUhU4aXy761rTo8Ji1T54pNEsxbDU5QYUiyIsuLLX6yQnbITHUXVV7gwGGliJJzIPom1GuuvB4tG/9Yo0+bIii5lKTbYe/4NtYWLkJiHir+AsHxToANjUzDfXhMhasNwQXx57zs0xUIH5BEi+xbgLZyPRBqSssN9lYID0FcMQSIw8QKjZUZ0dDZVnHb6wOjtgKPTjKdQaQfO1Ruu9aCDodm85ujr8QNIgTJKnLTPyyhvYyrw4uOD30sCfB045TRBQoSJOOOsc84TJUY8uIwpP3/tCy7yd1mlcROkvX0/4bnkKbjiqgDX3rrYUcVrqnQEvk+hgrwzVAfdVDfU94qBiPy9k0iGjBgzcV2MOPFi32komwf/hoZK8C8nUbIUSTqlmmTtHRu27BSy5yBNhkzp73G8PxdvLHG1YVOrNsxYsL4rIt+z+O8NQTzx6fWFr3yD1gjb8rGjdw/ebURJuHQhiORjosWNBzUaqMV6ZgpDyNwxZM26XTNmzZm3EwrHrSIl4oS6UBPvJwswnDhU89QTGoLESTzFKE7LU6xIiWzuXtAMvSQKI6XuuaGMtlvuuln9r0HXdUyWb9ruhCy7+LEb1zRIjFb0m6WapAeP0slL4P+AdTi6pEmqsbXJbM/BtTy3bt20a8fmEN5Rqw//PeH1K/5x23Oq8rId2wcRFUqN1gYA") format('woff2');
                }}
                /* Lock the document root to the viewport. Without this the
                   html element is the implicit scroll container, and mobile
                   WebView 100vh quirks let it overflow by a sliver -- enough
                   to paint the global ::-webkit-scrollbar (the stray 8px grey
                   bar on the right of full-bleed screens like the splash).
                   #content-area still scrolls internally; inner lists keep
                   their own bars. */
                html {{
                    height: 100vh;
                    max-width: 100vw;
                    overflow: hidden;
                }}
                body {{
                    background-color: #1a1a1a;
                    color: #ffffff;
                    font-family: 'Courier New', monospace;
                    margin: 0;
                    padding: 0;
                    font-size: 13px;
                    line-height: 1.3;
                    overflow-x: hidden;
                    overflow-y: hidden;
                    height: 100vh;
                    max-width: 100vw;
                    width: 100%;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                    display: flex;
                    flex-direction: column;
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

                /* Loot toast popups — floating banners at top-right that
                   announce items the player just acquired. */
                #loot-toasts {{
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    z-index: 9999;
                    display: flex;
                    flex-direction: column;
                    gap: 5px;
                    pointer-events: none;
                    max-width: 280px;
                }}
                .loot-toast {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    background: rgba(20, 20, 20, 0.94);
                    border: 1px solid #FFD700;
                    border-radius: 5px;
                    padding: 6px 10px;
                    font-family: monospace;
                    color: #FFD700;
                    font-size: 12px;
                    line-height: 1.2;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.5);
                    /* 'both' so a positive animation-delay (a combat-kill
                       toast waiting out its reveal delay) holds the 0%
                       keyframe — opacity 0 — instead of flashing visible. */
                    animation: lootFade 4s linear both;
                    max-width: 100% !important;
                }}
                .loot-toast-text {{
                    flex: 1;
                    word-break: break-word;
                }}
                @keyframes lootFade {{
                    0%   {{ opacity: 0; transform: translateX(20px); }}
                    8%   {{ opacity: 1; transform: translateX(0); }}
                    85%  {{ opacity: 1; transform: translateX(0); }}
                    100% {{ opacity: 0; transform: translateX(20px); }}
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
                
                /* Stats bar pinned at the top of the viewport.  Glance-
                   only info (HP/MP/level/floor/coords) -- not a tap
                   target, so it doesn't compete with the map for
                   thumb space. */
                #top-strip {{
                    flex: 0 0 auto;
                    z-index: 1000;
                    background-color: #1a1a1a;
                    border-bottom: 2px solid #444;
                    padding: 0 4px;
                }}
                #title-bar {{
                    background-color: #1a1a1a;
                    color: #03A9F4;
                    padding: 3px 6px 0 6px;
                    font-family: monospace;
                    font-size: 12px;
                    font-weight: bold;
                    line-height: 1.2;
                }}
                #title-bar .title-build {{
                    color: #666;
                    font-size: 10px;
                    font-weight: normal;
                }}
                #stats-bar {{
                    background-color: #1a1a1a;
                    color: #EEE;
                    padding: 2px 6px 4px 6px;
                    font-family: monospace;
                    font-size: 12px;
                    line-height: 1.3;
                }}

                /* Compact HTML HP / MP bars used on the stats banner.
                   Coloured fill + centered numerical overlay; takes
                   ~70px instead of the ~150px the text-based [#####]
                   bar consumed at width=10, so the line fits
                   without wrapping even at 999/999 stats. */
                .statbar {{
                    display: inline-block;
                    height: 13px;
                    border: 1px solid #444;
                    border-radius: 2px;
                    position: relative;
                    background: #2a2a2a;
                    vertical-align: middle;
                    margin: 0 4px 0 2px;
                    overflow: hidden;
                    font-size: 10px;
                    line-height: 13px;
                    box-sizing: border-box;
                }}
                .statbar-fill {{
                    position: absolute;
                    left: 0; top: 0; bottom: 0;
                    transition: width 0.3s ease;
                }}
                .statbar-text {{
                    position: relative;
                    z-index: 2;
                    width: 100%;
                    text-align: center;
                    color: #FFF;
                    font-weight: bold;
                    text-shadow: 0 0 2px #000, 0 0 2px #000, 0 0 2px #000;
                    display: block;
                }}
                #stats-bar > div {{
                    margin-bottom: 0 !important;
                }}

                /* Log pinned at the BOTTOM of the viewport.  Recent
                   events scroll past here while the map+chips above
                   stay stable. */
                /* Log pinned to a fixed 130px so it stays the same
                   size in every view (map, inventory, vendor, picker,
                   etc.).  Previously flex: 1 1 auto, which made the
                   log balloon in inventory mode where content-area is
                   ~230px shorter than in map mode. */
                #game-log {{
                    flex: 0 0 130px;
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

                /* Content-area sits between the top-strip and the
                   pinned log and takes the remaining vertical space.
                   On views with shorter content (inventory, vendor)
                   that means there's some empty area below the
                   content; on map view content fills it (room-panel +
                   map + chips). */
                #content-area {{
                    flex: 1 1 auto;
                    padding: 0;
                    overflow-y: auto;
                    min-height: 0;
                    /* Keep touch-scroll for tall views but drop the visible
                       bar — on the combat screen the 200px panel + map + chips
                       slightly overflow and the styled 8px track looked like a
                       stray UI element. Inner lists (inventory/vendor) keep
                       their own bars. */
                    scrollbar-width: none;
                }}
                #content-area::-webkit-scrollbar {{ width: 0; height: 0; display: none; }}

                /* Combat cards: stat lines flush-left. Without this they
                   inherit text-align:center from .bottom-pinned-zone and each
                   line (name / Lv / bars / A:D:) centres raggedly in its
                   column. */
                #monster_panel, #player_panel {{ text-align: left; }}

                /* Full-bleed screens (splash, intro, death, character
                   creation) hide both bars so backdrop art fills the
                   viewport. */
                body.full-bleed #top-strip {{ display: none; }}
                body.full-bleed #game-log {{ display: none; }}
                body.full-bleed #content-area {{
                    flex: 1 1 auto;
                    padding: 0;
                    max-height: 100%;
                    overflow-y: auto;
                }}

                /* Room interaction panel slot.  All room panels share
                   a min-height so the map below them sits at the
                   same vertical position regardless of which panel
                   is showing (empty floor, chest, tomb, pool, etc.).
                   max-height + overflow-y: auto keeps tall panels
                   (combat victory monster + player, library text,
                   vendor lists) from pushing the map up the screen
                   -- the panel scrolls internally instead. */
                /* Uniform fixed-size interaction box.  Every game-mode
                   panel (chest, pool, altar, library, smith, shrine,
                   garden, combat, etc.) renders into the same 200px
                   slot.  200px is sized for combat (monster card +
                   player card stacked) with the new bumped fonts;
                   simpler rooms have a little empty space — that's
                   the trade-off for a uniform silhouette. */
                .room-panel {{
                    min-height: 200px;
                    max-height: 200px;
                    height: 200px;
                    overflow: hidden;
                    box-sizing: border-box;
                }}

                /* Container that stacks the room-panel + map + action
                   chips, lives inside #content-area at its natural
                   flow position.  No padding / border so the map can
                   sit flush against the room-panel above and the
                   chips can sit flush against the log below. */
                .bottom-pinned-zone {{
                    position: static;
                    z-index: 500;
                    background: #1a1a1a;
                    padding: 0;
                    text-align: center;
                }}
                body.full-bleed .bottom-pinned-zone {{ display: none; }}

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

                /* Threat pulse for the monster panel: stronger foes throb a
                   glowing aura.  Color comes from the per-tier --tg var so one
                   keyframe covers every tier (see get_monster_threat_style). */
                @keyframes threatPulse {{
                    0%, 100% {{ box-shadow: 0 0 7px var(--tg); }}
                    50%      {{ box-shadow: 0 0 22px var(--tg), 0 0 9px var(--tg); }}
                }}

                /* Tier-scaled monster ENTRANCE flourishes (fired once per fight
                   by generate_monster_sprite_html).  transform-origin is set
                   inline to bottom-center so the creature rises from its feet. */
                @keyframes flourishPop {{
                    0%   {{ opacity: 0; transform: scale(0.82); }}
                    100% {{ opacity: 1; transform: scale(1); }}
                }}
                @keyframes flourishRise {{
                    0%   {{ opacity: 0; transform: translateY(14px) scale(0.9); }}
                    70%  {{ opacity: 1; transform: translateY(-3px) scale(1.05); }}
                    100% {{ opacity: 1; transform: translateY(0) scale(1); }}
                }}
                @keyframes flourishSurge {{
                    0%   {{ opacity: 0; transform: translateY(22px) scale(0.7); }}
                    60%  {{ opacity: 1; transform: translateY(0) scale(1.07); }}
                    100% {{ opacity: 1; transform: scale(1); }}
                }}
                @keyframes flourishSlam {{
                    0%   {{ opacity: 0; transform: translateY(34px) scale(0.5); }}
                    50%  {{ opacity: 1; transform: translateY(-6px) scale(1.12); }}
                    72%  {{ transform: translateY(0) scale(0.96); }}
                    100% {{ transform: scale(1); }}
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

                /* ===== TAPPABLE INVENTORY / MENU ROWS ===== */
                /* Fat touch target, visible affordance, press feedback.
                   Any element with class="taprow" becomes a finger-friendly
                   button. data-zcmd attribute carries the command string
                   that should be injected to Python on tap. */
                .taprow {{
                    display: block;
                    margin: 3px 0;
                    padding: 8px 10px;
                    border: 1px solid #2a3a2a;
                    border-radius: 4px;
                    background: linear-gradient(180deg, #1e2a1e 0%, #162016 100%);
                    color: #DDD;
                    cursor: pointer;
                    user-select: none;
                    -webkit-user-select: none;
                    -webkit-tap-highlight-color: transparent;
                    transition: transform 60ms ease-out, background 120ms ease-out,
                                border-color 120ms ease-out, box-shadow 120ms ease-out;
                    box-shadow: 0 1px 0 #0a0a0a inset;
                }}
                .taprow:active {{
                    transform: scale(0.98);
                    background: linear-gradient(180deg, #2a4a2a 0%, #1a301a 100%);
                    border-color: #4CAF50;
                    box-shadow: 0 0 8px rgba(76,175,80,0.45),
                                0 1px 0 #0a0a0a inset;
                }}
                .taprow .tapnum {{
                    color: #4CAF50;
                    font-weight: bold;
                    margin-right: 6px;
                    min-width: 14px;
                    display: inline-block;
                }}
                .taprow.armed {{
                    background: linear-gradient(180deg, #3a5a3a 0%, #1a301a 100%);
                    border-color: #8BC34A;
                    box-shadow: 0 0 10px rgba(139,195,74,0.6);
                }}
                /* Equipped items in the Equip list: gold border + "tap to
                   remove" affordance so the unequip action is obvious. */
                .taprow.equipped {{
                    background: linear-gradient(180deg, #2a2418 0%, #18140c 100%);
                    border-color: #FFD700;
                    box-shadow: 0 0 6px rgba(255,215,0,0.35) inset;
                }}
                .taprow.equipped .tapnum {{
                    color: #FFD700;
                }}
                .eqbadge {{
                    display: inline-block;
                    margin-left: 8px;
                    padding: 1px 6px;
                    font-size: 9px;
                    font-weight: bold;
                    color: #1a1a1a;
                    background: #FFD700;
                    border-radius: 8px;
                    vertical-align: middle;
                    letter-spacing: 0.3px;
                }}
                /* UNEQUIP chip rendered next to an equipped item row -- a
                   small red pill that's the only tappable element on
                   the row (the row itself is non-tappable so the player
                   can't accidentally unequip by mis-tapping the item
                   name). */
                .unequip-chip {{
                    float: right;
                    margin-top: 4px;
                    padding: 7px 8px;
                    font-family: 'PressStart', monospace;
                    font-size: 7px;
                    line-height: 1.5;
                    font-weight: bold;
                    letter-spacing: 0;
                    color: #e0906a;
                    background: linear-gradient(180deg, #56382c 0%, #2c1c16 100%);
                    border: 2px solid #0c0a08;
                    border-radius: 3px;
                    text-shadow: 0 1px 0 #060504;
                    box-shadow: inset 2px 2px 0 rgba(150,96,72,0.45),
                                inset -2px -2px 0 rgba(0,0,0,0.55);
                    cursor: pointer;
                    user-select: none;
                    -webkit-user-select: none;
                    -webkit-tap-highlight-color: transparent;
                    transition: transform 60ms ease-out, filter 120ms ease-out;
                }}
                .unequip-chip:active {{
                    transform: translateY(1px);
                    filter: brightness(1.18);
                }}
                /* Spell cast modal rows: purple/magenta theme. */
                .taprow.spell {{
                    background: linear-gradient(180deg, #2a1a3a 0%, #1a0e24 100%);
                    border-color: #5a3a7a;
                    color: #E1BEE7;
                }}
                .taprow.spell:active {{
                    background: linear-gradient(180deg, #4a2a6a 0%, #2a1a3a 100%);
                    border-color: #E040FB;
                    box-shadow: 0 0 10px rgba(224,64,251,0.5),
                                0 1px 0 #0a0a0a inset;
                }}
                .taprow.spell .tapnum {{
                    color: #E040FB;
                }}
                /* Disabled: grey out and kill interactivity. */
                .taprow.disabled {{
                    opacity: 0.45;
                    cursor: not-allowed;
                    pointer-events: none;
                    filter: grayscale(0.6);
                }}
                .tapnote {{
                    display: inline-block;
                    margin-left: 8px;
                    padding: 1px 6px;
                    font-size: 9px;
                    font-weight: bold;
                    color: #bbb;
                    background: #3a1a1a;
                    border-radius: 8px;
                    vertical-align: middle;
                }}
                /* Cancel-row variant: muted red tint. */
                .taprow.cancel {{
                    background: linear-gradient(180deg, #2a1a1a 0%, #1a0e0e 100%);
                    border-color: #6a3a3a;
                    color: #D0A0A0;
                    text-align: center;
                    font-weight: bold;
                    letter-spacing: 1px;
                    margin-top: 6px;
                }}
                .taprow.cancel:active {{
                    background: linear-gradient(180deg, #4a2a2a 0%, #2a1a1a 100%);
                    border-color: #FF5252;
                    box-shadow: 0 0 8px rgba(255,82,82,0.5);
                }}
                .taprow.cancel .tapnum {{
                    color: #FF8A80;
                }}
                /* HUD chips for game_loop — replace bottom-panel
                   INVENTORY / LANTERN / STAIRS buttons with tappable
                   pills sitting just under the map. */
                .hudchips {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: center;
                    gap: 6px;
                    margin: 6px 4px 4px 4px;
                    transition: opacity 0.2s ease-out;
                }}
                /* Faded + un-tappable while a dice / defeat animation
                   is mid-flight so the player can't queue an action
                   during the resolution window.  Class is toggled by
                   the JS shell in wrap_html. */
                .hudchips.animating {{
                    opacity: 0.35;
                    pointer-events: none;
                }}
                /* Inventory chip row: 5 chips (CRAFT / SPELLS /
                   JOURNAL / QUIT / CLOSE) when spells are available.
                   At default chip sizing (~80-90px each) that
                   overflows ~360px-wide phones, so tighten the chip
                   padding + font here.  flex-wrap: nowrap keeps them
                   on a single row. */
                .hudchips.inv-bar {{
                    flex-wrap: nowrap;
                    overflow-x: auto;
                    gap: 4px;
                }}
                .hudchips.inv-bar .hudchip {{
                    padding: 9px 9px;
                    font-size: 8px;
                    min-height: 38px;
                    border-radius: 3px;
                    letter-spacing: 0;
                }}
                .hudchip {{
                    display: inline-flex;
                    align-items: center;
                    padding: 12px 14px;
                    min-height: 44px;
                    box-sizing: border-box;
                    /* Hybrid retro+dungeon chip: square-ish corners, pixel
                       bevel (light top-left / dark bottom-right inset),
                       carved-stone fill, engraved Press Start 2P text. */
                    border-radius: 3px;
                    background: linear-gradient(180deg, #484438 0%, #28251d 100%);
                    border: 2px solid #0c0a08;
                    color: #c4b486;
                    font-family: 'PressStart', monospace;
                    font-size: 9px;
                    line-height: 1.5;
                    font-weight: bold;
                    letter-spacing: 0;
                    cursor: pointer;
                    user-select: none;
                    -webkit-user-select: none;
                    -webkit-tap-highlight-color: transparent;
                    text-shadow: 0 1px 0 #060504;
                    box-shadow: inset 2px 2px 0 rgba(120,110,92,0.55),
                                inset -2px -2px 0 rgba(0,0,0,0.55);
                    transition: transform 60ms ease-out, filter 120ms ease-out;
                    flex-shrink: 0;
                }}
                /* Icon-only chips: drop the trailing 4px canvas margin
                   and tighten padding so the (now 32px) sprite fills
                   the chip with just a little breathing room. */
                .hudchip.lantern-icon {{
                    padding: 4px 6px;
                }}
                .hudchip.lantern-icon canvas {{
                    margin-right: 0 !important;
                    vertical-align: middle;
                }}
                /* Press: flip the bevel (dark TL / light BR) so the chip
                   reads as pushed-in, plus a quick brightness pop. Works
                   uniformly across every colour variant below. */
                .hudchip:active {{
                    transform: translateY(1px);
                    filter: brightness(1.18);
                    box-shadow: inset -2px -2px 0 rgba(120,110,92,0.55),
                                inset 2px 2px 0 rgba(0,0,0,0.55);
                }}
                /* Colour variants keep their identity but as muted carved
                   stone slabs (dark border, colour lives in the engraved
                   text + a tinted fill). */
                .hudchip.lantern {{
                    background: linear-gradient(180deg, #4a3a14 0%, #241c08 100%);
                    border-color: #0c0a08;
                    color: #FFD27A;
                }}
                .hudchip.stairs {{
                    background: linear-gradient(180deg, #2c4a22 0%, #16280f 100%);
                    border-color: #0c0a08;
                    color: #a6e07a;
                }}
                .hudchip.exit {{
                    background: linear-gradient(180deg, #56382c 0%, #2c1c16 100%);
                    border-color: #0c0a08;
                    color: #e0906a;
                }}
                .hudchip.combat-attack {{
                    background: linear-gradient(180deg, #5a2820 0%, #2c1210 100%);
                    border-color: #0c0a08;
                    color: #ff7a5a;
                }}
                .hudchip.combat-cast {{
                    background: linear-gradient(180deg, #403850 0%, #241e2c 100%);
                    border-color: #0c0a08;
                    color: #ba96e0;
                }}
                /* Map cells: transparent tap/glyph layer OVER the
                   procedurally drawn cavern canvas (cavern_render.py). */
                .zmap-cell {{
                    -webkit-tap-highlight-color: transparent;
                    -webkit-user-select: none;
                    user-select: none;
                    position: relative;
                    z-index: 1;
                }}
                /* Map slot — a FIXED footprint shared by all three zoom
                   levels (sized for the tallest layout: close 8x8@42px
                   ≈ 348px), so cycling zoom never reflows the chips or
                   log around the map. The grid centers inside it. */
                .mvslot {{
                    height: 352px;
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                /* Map frame — centers the grid horizontally on screen.
                   Tap-to-move: every discovered room in the zoomed
                   viewport is a tap-to-travel target (see
                   generate_grid_html); .armed flashes briefly on tap. */
                .mvframe {{
                    display: block;
                    width: fit-content;
                    max-width: 100%;
                    margin: 0 auto;
                }}
                .mvmap {{
                    position: relative;
                }}
                .zmap-cell.armed {{
                    filter: brightness(1.8);
                }}
                /* Altar action cards: stack of tall taprows, each with a
                   coloured title + muted meta line, rendered ABOVE the
                   sacrifice item list.  Detect=cyan, Bless=gold, Purify=
                   pale violet, Devotion=divine gold. */
                .altar-actions {{
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                    margin: 4px 0 8px 0;
                }}
                /* Compact 2x3 grid for altar_mode action chips
                   (Detect / Bless / Purify / Sacrifice / Devotion) +
                   1 filler when devotion isn't shown.  240px panel
                   slot fits larger labels comfortably. */
                .altar-actions.compact {{
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                    gap: 4px;
                    margin: 6px 0 0 0;
                }}
                .altar-actions.compact .taprow.altar-act {{
                    padding: 6px 6px;
                    line-height: 1.2;
                }}
                .altar-actions.compact .taprow.altar-act .aname {{
                    font-size: 13px;
                }}
                .altar-actions.compact .taprow.altar-act .ameta {{
                    font-size: 10px;
                    margin-top: 2px;
                }}
                /* Dual side-by-side variant for binary-choice room
                   panels (grimoire decision, shrine pray/offering,
                   tomb raid/respect).  Two columns instead of stacked
                   so both options fit inside the 200px room-panel
                   without clipping. */
                .altar-actions.dual {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 4px;
                    margin: 4px 0 0 0;
                }}
                .altar-actions.dual .taprow.altar-act {{
                    padding: 6px 8px;
                    line-height: 1.2;
                }}
                .altar-actions.dual .taprow.altar-act .aname {{
                    font-size: 13px;
                }}
                .altar-actions.dual .taprow.altar-act .ameta {{
                    font-size: 10px;
                    margin-top: 2px;
                }}
                .taprow.altar-act.sacrifice {{
                    background: linear-gradient(180deg, #2a1a1f 0%, #18101a 100%);
                    border-color: #9a5a7a;
                }}
                .taprow.altar-act.sacrifice .aname {{ color: #F48FB1; }}
                .taprow.altar-act {{
                    padding: 8px 10px;
                    line-height: 1.3;
                }}
                .taprow.altar-act .aname {{
                    font-weight: bold;
                    font-size: 14px;
                    letter-spacing: 0.3px;
                }}
                .taprow.altar-act .ameta {{
                    font-size: 12px;
                    color: #AAA;
                    margin-top: 3px;
                }}
                .taprow.altar-act.detect {{
                    background: linear-gradient(180deg, #13272e 0%, #0c1a1f 100%);
                    border-color: #4a7a8a;
                }}
                .taprow.altar-act.detect .aname {{ color: #4FC3F7; }}
                .taprow.altar-act.bless {{
                    background: linear-gradient(180deg, #2a2418 0%, #18140c 100%);
                    border-color: #8a7a4a;
                }}
                .taprow.altar-act.bless .aname {{ color: #FFD700; }}
                .taprow.altar-act.purify {{
                    background: linear-gradient(180deg, #2a1a2e 0%, #18101f 100%);
                    border-color: #8a5a9a;
                }}
                .taprow.altar-act.purify .aname {{ color: #CE93D8; }}
                .taprow.altar-act.devotion {{
                    background: linear-gradient(180deg, #3a2a0e 0%, #1f1506 100%);
                    border-color: #FFC107;
                    box-shadow: 0 0 10px rgba(255,193,7,0.25) inset;
                }}
                .taprow.altar-act.devotion .aname {{ color: #FFC107; }}
                .taprow.altar-act.devotion .ameta {{ color: #C8A857; }}
                /* Additional NPC-room action-card variants reusing the
                   altar-act layout.  Colours chosen to match each room's
                   theme so the player can tell them apart at a glance. */
                .taprow.altar-act.forge {{
                    background: linear-gradient(180deg, #2e1a0e 0%, #1a0e06 100%);
                    border-color: #8a5a22;
                }}
                .taprow.altar-act.forge .aname {{ color: #FF9800; }}
                .taprow.altar-act.reforge {{
                    background: linear-gradient(180deg, #2a1e0e 0%, #180e06 100%);
                    border-color: #B71C1C;
                    box-shadow: 0 0 6px rgba(229,57,53,0.25) inset;
                }}
                .taprow.altar-act.reforge .aname {{ color: #E53935; }}
                .taprow.altar-act.mystic {{
                    background: linear-gradient(180deg, #1f1430 0%, #110820 100%);
                    border-color: #7e57c2;
                    box-shadow: 0 0 8px rgba(186,104,200,0.2) inset;
                }}
                .taprow.altar-act.mystic .aname {{ color: #BA68C8; }}
                .taprow.altar-act.blessing {{
                    background: linear-gradient(180deg, #0e2a1e 0%, #08180e 100%);
                    border-color: #4caf50;
                }}
                .taprow.altar-act.blessing .aname {{ color: #81C784; }}
                .taprow.altar-act.offering {{
                    background: linear-gradient(180deg, #2a2412 0%, #181308 100%);
                    border-color: #c9a02b;
                }}
                .taprow.altar-act.offering .aname {{ color: #FFCA28; }}
                .taprow.altar-act.unlock {{
                    background: linear-gradient(180deg, #0e2a18 0%, #08180c 100%);
                    border-color: #4caf50;
                    box-shadow: 0 0 8px rgba(76,175,80,0.3) inset;
                }}
                .taprow.altar-act.unlock .aname {{ color: #66BB6A; }}
                .taprow.altar-act.loot {{
                    background: linear-gradient(180deg, #2a200a 0%, #1a1206 100%);
                    border-color: #FFC107;
                    box-shadow: 0 0 10px rgba(255,193,7,0.3) inset;
                }}
                .taprow.altar-act.loot .aname {{ color: #FFD54F; }}
                /* Crafting recipe rows: reuse the taprow base with a
                   denser layout (name / ingredients / description). */
                .taprow.recipe {{
                    background: linear-gradient(180deg, #1f1025 0%, #120818 100%);
                    padding: 8px 10px;
                    line-height: 1.3;
                }}
                .taprow.recipe:active {{
                    background: linear-gradient(180deg, #3a1a45 0%, #1f0e28 100%);
                    box-shadow: 0 0 10px rgba(224,64,251,0.5),
                                0 1px 0 #0a0a0a inset;
                }}
                .taprow.recipe .rname {{
                    font-weight: bold;
                    font-size: 13px;
                    letter-spacing: 0.3px;
                }}
                .taprow.recipe .rmeta {{
                    margin-top: 2px;
                    font-size: 10px;
                    color: #BBB;
                }}
                .taprow.recipe .rdesc {{
                    margin-top: 2px;
                    font-size: 10px;
                    color: #888;
                    font-style: italic;
                }}

                /* Journal category cards: 2-column grid of tappable tiles. */
                .jcat-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 6px;
                    margin: 6px 0;
                }}
                .taprow.jcat {{
                    padding: 10px 8px;
                    text-align: center;
                    line-height: 1.3;
                }}
                .taprow.jcat .jname {{
                    font-weight: bold;
                    font-size: 13px;
                }}
                .taprow.jcat .jprog {{
                    font-size: 10px;
                    color: #AAA;
                    margin-top: 2px;
                }}

                /* ===== DIRECTION PICKER D-PAD =====
                   Cross-shaped 3x3 grid: N top, W/center-cancel/E
                   middle, S bottom.  Used by flee / flare / foresight
                   direction modes. */
                .dpad {{
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                    grid-template-rows: auto auto auto;
                    gap: 4px;
                    margin: 10px 0;
                    max-width: 240px;
                    margin-left: auto;
                    margin-right: auto;
                }}
                .dpad .dpad-slot {{
                    min-height: 44px;
                }}
                .dpad .dpad-slot.empty {{
                    background: transparent;
                    border: none;
                }}
                .taprow.dpad-dir {{
                    padding: 10px 0;
                    text-align: center;
                    font-size: 16px;
                    font-weight: bold;
                    letter-spacing: 1px;
                    color: #DDD;
                    background: linear-gradient(180deg, #2a2a2a 0%, #1a1a1a 100%);
                    border-color: #4a4a4a;
                }}
                .taprow.dpad-dir:active {{
                    background: linear-gradient(180deg, #3a4a3a 0%, #1a2a1a 100%);
                    border-color: #4CAF50;
                    box-shadow: 0 0 8px rgba(76,175,80,0.45);
                }}
                .taprow.dpad-cancel {{
                    padding: 8px 0;
                    text-align: center;
                    font-size: 11px;
                    font-weight: bold;
                    color: #FF8A80;
                    background: #2a1010;
                    border-color: #8a3a3a;
                }}
                .taprow.dpad-cancel:active {{
                    background: #5a1a1a;
                    border-color: #FF5252;
                }}

                /* Shared "locked / already used" info pill used by rooms
                   when the action isn't available — muted grey, no tap. */
                .roominfo {{
                    padding: 8px 10px;
                    margin: 4px 0;
                    border: 1px dashed #444;
                    border-radius: 4px;
                    background: #1a1a1a;
                    color: #888;
                    font-size: 11px;
                    font-style: italic;
                }}

                /* ===== SAVE / LOAD SLOT CARDS ===== */
                /* Populated slot: cyan border, character summary, tap = LOAD.
                   Inner .ovr-btn taps OVERWRITE (dangerous, two-tap gated). */
                .taprow.save-populated {{
                    background: linear-gradient(180deg, #0e1e2a 0%, #0a1520 100%);
                    border-color: #4FC3F7;
                    padding: 10px 12px;
                    position: relative;
                }}
                .taprow.save-populated .sname {{
                    color: #4FC3F7;
                    font-weight: bold;
                    font-size: 13px;
                }}
                .taprow.save-populated .smeta {{
                    color: #AAA;
                    font-size: 10px;
                    margin-top: 3px;
                }}
                .taprow.save-populated .sdate {{
                    color: #666;
                    font-size: 9px;
                    margin-top: 2px;
                }}
                .taprow.save-populated .slabel {{
                    display: inline-block;
                    margin-top: 6px;
                    padding: 2px 7px;
                    font-size: 9px;
                    font-weight: bold;
                    color: #1a1a1a;
                    background: #4FC3F7;
                    border-radius: 7px;
                    letter-spacing: 0.5px;
                }}
                /* Empty slot: dimmer, amber "save here" tint. */
                .taprow.save-empty {{
                    background: linear-gradient(180deg, #22221a 0%, #18180e 100%);
                    border-color: #554a22;
                    padding: 14px 12px;
                    color: #888;
                }}
                .taprow.save-empty .sname {{
                    color: #AAA;
                    font-size: 12px;
                }}
                .taprow.save-empty .slabel {{
                    display: inline-block;
                    margin-top: 6px;
                    padding: 2px 7px;
                    font-size: 9px;
                    font-weight: bold;
                    color: #1a1a1a;
                    background: #FFC107;
                    border-radius: 7px;
                    letter-spacing: 0.5px;
                }}
                /* New Game card (main menu): bold gold treatment. */
                .taprow.save-new {{
                    background: linear-gradient(180deg, #2a2210 0%, #1a1408 100%);
                    border-color: #FFD700;
                    padding: 14px;
                    text-align: center;
                    box-shadow: 0 0 10px rgba(255,215,0,0.25) inset;
                }}
                .taprow.save-new .sname {{
                    color: #FFD700;
                    font-weight: bold;
                    font-size: 14px;
                    letter-spacing: 1px;
                }}
                .taprow.save-new .smeta {{
                    color: #A78B5A;
                    font-size: 10px;
                    margin-top: 4px;
                }}
                /* Inner overwrite micro-button on populated slots. */
                .ovr-btn {{
                    display: inline-block;
                    margin-top: 8px;
                    padding: 4px 10px;
                    font-size: 10px;
                    font-weight: bold;
                    color: #FFB74D;
                    background: #2a1f10;
                    border: 1px solid #8a6a2a;
                    border-radius: 4px;
                    cursor: pointer;
                    user-select: none;
                    -webkit-user-select: none;
                    -webkit-tap-highlight-color: transparent;
                    transition: background 120ms ease-out, transform 60ms ease-out;
                }}
                .ovr-btn:active {{
                    transform: scale(0.96);
                    background: #5a3a1a;
                    border-color: #FFA500;
                }}
                .ovr-btn.armed {{
                    background: #8B0000;
                    border-color: #FF6F6F;
                    color: #FFF;
                    box-shadow: 0 0 8px rgba(255,82,82,0.6);
                }}
                /* Delete micro-button on populated slots: red from the
                   start so the "destructive" framing is obvious before
                   you even arm it.  Armed state intensifies. */
                .del-btn {{
                    display: inline-block;
                    margin-top: 8px;
                    margin-left: 6px;
                    padding: 4px 10px;
                    font-size: 10px;
                    font-weight: bold;
                    color: #FF8A80;
                    background: #2a1010;
                    border: 1px solid #8a3a3a;
                    border-radius: 4px;
                    cursor: pointer;
                    user-select: none;
                    -webkit-user-select: none;
                    -webkit-tap-highlight-color: transparent;
                    transition: background 120ms ease-out, transform 60ms ease-out;
                }}
                .del-btn:active {{
                    transform: scale(0.96);
                    background: #5a1a1a;
                    border-color: #FF5252;
                }}
                .del-btn.armed {{
                    background: #8B0000;
                    border-color: #FF6F6F;
                    color: #FFF;
                    box-shadow: 0 0 10px rgba(255,82,82,0.7);
                }}

                /* ===== SEGMENTED FILTER TABS =====
                   Pill-style bar showing the current inventory filter.
                   Tapping a tab sets the filter directly (no more typing
                   'u' / 'e' / 'eat').  Active tab highlights green. */
                /* Filter tabs share the hybrid carved-stone look. The
                   selected tab reads as pushed-in (inverted bevel) and
                   glows rune-green. */
                .filtertabs {{
                    display: flex;
                    gap: 3px;
                    margin: 0 0 6px 0;
                    padding: 3px;
                    background: #1b1916;
                    border: 1px solid #0c0a08;
                    border-radius: 4px;
                }}
                .filtertab {{
                    flex: 1;
                    text-align: center;
                    padding: 8px 3px;
                    font-family: 'PressStart', monospace;
                    font-size: 8px;
                    line-height: 1.5;
                    font-weight: bold;
                    letter-spacing: 0;
                    color: #b0a47c;
                    background: linear-gradient(180deg, #46423a 0%, #28251f 100%);
                    border: 2px solid #0c0a08;
                    border-radius: 3px;
                    text-shadow: 0 1px 0 #060504;
                    box-shadow: inset 2px 2px 0 rgba(116,106,90,0.5),
                                inset -2px -2px 0 rgba(0,0,0,0.5);
                    cursor: pointer;
                    user-select: none;
                    -webkit-user-select: none;
                    -webkit-tap-highlight-color: transparent;
                    transition: filter 120ms ease-out, transform 60ms ease-out;
                }}
                .filtertab:active {{
                    transform: translateY(1px);
                    filter: brightness(1.15);
                }}
                .filtertab.active {{
                    background: linear-gradient(180deg, #324a2c 0%, #1c2a1a 100%);
                    color: #c8fa9c;
                    border-color: #0c0a08;
                    box-shadow: inset 2px 2px 0 rgba(20,44,18,0.9),
                                inset -2px -2px 0 rgba(120,200,110,0.4);
                }}
            </style>
            <script>
                {_sprite_animator_js}
            </script>
            <script>
                {_cavern_renderer_js}
            </script>
        </head>
        <body class="{body_class}">
            <script>
                // ===== Python <-> WebView tap bridge =====
                // Item rows (and any other .taprow) call window.__zotTap(cmd)
                // on click.  Commands queue up in window.__zotCmds and are
                // drained by a Python background task that polls via
                // evaluate_javascript().  A short debounce on each row
                // prevents double-fire from accidental re-taps.
                window.__zotCmds = window.__zotCmds || [];
                window.__zotTap = function(cmd, el) {{
                    try {{
                        if (!cmd) return;
                        var now = Date.now();
                        if (el && el.__lastTap && (now - el.__lastTap) < 350) {{
                            return;  // debounce rapid re-taps on same row
                        }}
                        if (el) {{
                            el.__lastTap = now;
                            el.classList.add('armed');
                            setTimeout(function(){{
                                try {{ el.classList.remove('armed'); }} catch(e){{}}
                            }}, 180);
                        }}
                        window.__zotCmds.push(String(cmd));
                        if (navigator && navigator.vibrate) {{
                            try {{ navigator.vibrate(8); }} catch(e) {{}}
                        }}
                    }} catch(e) {{}}
                }};

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
                        // Drop any monster loom overlays from the previous
                        // screen (they live on <body>, outside content-area, so
                        // the innerHTML swap won't remove them).  The new
                        // content's sprite script re-mounts one if still in a
                        // loom fight.
                        var _lo = document.querySelectorAll('.loom-overlay');
                        for (var _i = 0; _i < _lo.length; _i++) _lo[_i].remove();
                        // Prune dead sprite animators before swapping content
                        if (window._sprAnim) window._sprAnim.cleanup();
                        ca.innerHTML = p.contentHtml;
                        // Combat panels re-render every round, which would
                        // restart their combatIn entrance and blink the boxes.
                        // Replay the entrance only when a NEW fight starts
                        // (data-fight token changes); within the same fight,
                        // jump the animations past the entrance so the panels
                        // stay solid. The negative delay merely phase-shifts
                        // the infinite pulse animations, so those keep going.
                        var _mp = document.getElementById('monster_panel');
                        var _pp = document.getElementById('player_panel');
                        var _ftok = (_mp && _mp.getAttribute('data-fight')) ||
                                    (_pp && _pp.getAttribute('data-fight'));
                        if (_ftok) {{
                            if (window.__combatEnterTok === _ftok) {{
                                if (_mp) _mp.style.animationDelay = '-2500ms';
                                if (_pp) _pp.style.animationDelay = '-2500ms';
                            }} else {{
                                window.__combatEnterTok = _ftok;
                            }}
                        }}
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
                    // Update stats bar in the fixed top strip
                    if (p.statsHtml !== undefined) {{
                        var sb = document.getElementById('stats-bar');
                        if (sb) sb.innerHTML = p.statsHtml;
                    }}
                    // Toggle body class so the top strip + padding hide
                    // on splash/intro/death and show during gameplay.
                    if (p.bodyClass !== undefined) {{
                        document.body.className = p.bodyClass;
                    }}
                    // Update log. Per-line reveal delays hold back the new
                    // combat-result lines until their animation resolves;
                    // chips always RENDER server-side and animateCombatChips
                    // fades them during the roll so they can't be double-tapped.
                    if (p.logLines !== undefined) {{
                        window.logLines = p.logLines;
                        window.logDelays = p.logDelays || [];
                        window.hasDiceRolls = !!p.hasDiceRolls;
                        window.hasInitRoll = !!p.hasInitRoll;
                        if (typeof updateLog === 'function') updateLog();
                        if (typeof animateCombatChips === 'function') animateCombatChips();
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
            <div id="top-strip">
                <div id="title-bar">Wizard's Cavern <span class="title-build">b{BUILD_NUMBER}</span></div>
                <div id="stats-bar">{stats_html}</div>
            </div>
            <div id="content-area">
                {content}
            </div>
            <div id="game-log"></div>
            <script>
                // Embed log lines + per-line reveal delays from Python
                window.logLines = {log_lines_json};
                window.logDelays = {log_delays_json};
                window.hasDiceRolls = {'true' if gs.last_dice_rolls else 'false'};
                window.hasInitRoll = {'true' if (gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)) else 'false'};
                window._logToken = 0;

                // Render the log, holding back any line flagged with a reveal
                // delay until that delay elapses. Lines already on screen stay
                // put; only the new combat-result lines fade in once their
                // animation (a dice exchange or the defeat overlay) resolves,
                // so the log never spoils a roll or a kill. Replaces the old
                // "blank the whole log" hack.
                function updateLog() {{
                    var ld = document.getElementById('game-log');
                    if (!ld || !window.logLines) return;
                    var token = ++window._logToken;
                    var lines = window.logLines, delays = window.logDelays || [];
                    function renderUpTo(maxD) {{
                        if (token !== window._logToken) return;  // superseded by a newer render
                        var html = [];
                        for (var i = 0; i < lines.length; i++) {{
                            if ((delays[i] || 0) <= maxD) html.push(lines[i]);
                        }}
                        ld.innerHTML = html.join('<br>');
                        ld.scrollTop = ld.scrollHeight;
                    }}
                    renderUpTo(0);
                    var seen = {{}};
                    for (var i = 0; i < lines.length; i++) {{
                        var d = delays[i] || 0;
                        if (d > 0 && !seen[d]) {{
                            seen[d] = 1;
                            (function(dd) {{ setTimeout(function() {{ renderUpTo(dd); }}, dd); }})(d);
                        }}
                    }}
                }}

                // Fade combat chips during the dice/defeat animation so they
                // can't be double-tapped before the result resolves.
                function animateCombatChips() {{
                    if (!window.hasDiceRolls) return;
                    var bars = document.querySelectorAll('.hudchips');
                    for (var ci = 0; ci < bars.length; ci++) bars[ci].classList.add('animating');
                    var delay = window.hasInitRoll ? 1000 : 3300;
                    setTimeout(function() {{
                        var b = document.querySelectorAll('.hudchips');
                        for (var ci = 0; ci < b.length; ci++) b[ci].classList.remove('animating');
                    }}, delay);
                }}
                window.addEventListener('load', function() {{ updateLog(); animateCombatChips(); }});
            </script>
            {generate_spell_cast_js(gs.last_spell_cast)}
            {generate_spell_icon_visual_js(gs.last_spell_cast)}
            {generate_spell_particles_js(gs.last_spell_cast)}
            {generate_dice_roll_js(gs.last_dice_rolls)}
            {generate_concentration_check_js(gs.last_concentration_roll)}
            {generate_monster_defeat_js(gs.monster_defeated_anim)}
            {generate_sprite_anim_triggers_js(getattr(gs.active_monster, 'name', None) if getattr(gs, 'active_monster', None) else None, gs.last_monster_damage, gs.last_player_damage, gs.last_spell_cast, gs.monster_defeated_anim, bool(gs.last_dice_rolls), bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}
            {music_js}
            {generate_sfx_js(gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_heal, gs.last_monster_damage_badge, gs.last_player_damage_badge, gs.last_player_status, gs.last_monster_status, gs.last_spell_cast, gs.last_concentration_roll, gs.monster_defeated_anim, gs.sfx_event, gs.music_enabled, bool(gs.last_dice_rolls), bool(gs.last_dice_rolls and any(r[3] == 'INIT' for r in gs.last_dice_rolls)))}
        </body>
        </html>
        """
        # Clear one-shot animation flags after rendering
        gs.monster_defeated_anim = None
        gs.loot_toast_delay_ms = 0
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

