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


def generate_damage_float_js(monster_name, monster_dmg, player_dmg, player_blocked=False,
                              player_status=None, monster_status=None, player_heal=0):
    """Generate floating damage/heal/status text above combat sprites.

    Injects absolutely-positioned divs into the sprite wrapper elements.
    Uses a JS-driven animation loop (requestAnimationFrame) so it works
    reliably in Toga/WKWebView without requiring <style> blocks in <body>.
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
        m_color = "#FF5252"
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
    # TUNING: Change FLOAT_DELAY_MS to adjust the gap (in milliseconds)
    #         between successive floating notifications.
    #         0 = all appear at once, 400 = 0.4s stagger, etc.
    # -----------------------------------------------------------------
    FLOAT_DELAY_MS = 400
    float_calls = []
    delay_idx = 0
    if m_text:
        float_calls.append(
            f'showFloat("{monster_canvas_id}_wrap","{m_text}","{m_color}",0,{delay_idx * FLOAT_DELAY_MS});'
        )
        delay_idx += 1
    if p_text:
        float_calls.append(
            f'showFloat("player_sprite_wrap","{p_text}","{p_color}",0,{delay_idx * FLOAT_DELAY_MS});'
        )
        delay_idx += 1
    if h_text:
        float_calls.append(
            f'showFloat("player_sprite_wrap","{h_text}","{h_color}",24,{delay_idx * FLOAT_DELAY_MS});'
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
        + ''.join(float_calls)
        + '})();</script>'
    )
    return js


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
            style=Pack(direction=COLUMN, background_color="#1a1a1a"),
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
            style=Pack(flex=1, margin=2, height=30, background_color='#2a2a2a', color='#EEE')
        )

        # Note: iOS keyboard will be disabled AFTER window is shown
        # See disable_ios_keyboard() method called in startup()

        # Permanent backspace button (always visible)
        self.backspace_button = toga.Button(
            "\u232b",
            on_press=lambda w: self.number_pad_backspace(),
            style=Pack(margin=2, width=45, height=30, font_size=14,
                       background_color='#333', color='#EEE')
        )

        self.submit_button = toga.Button(
            "Send",
            on_press=self.on_command_submit,
            style=Pack(margin=2, width=80, height=30, font_size=14,
                       background_color='#444', color='#FFF')
        )
        
        self.input_row = toga.Box(
            style=Pack(direction=ROW, margin=2, background_color='#1a1a1a'),
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
                flex=0,
            ),
            children=[
                self.commands_label,
                self.button_panel,
                self.input_row,
                toga.Box(style=Pack(height=30, background_color='#1a1a1a')),
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
        
        # Commands that need numbers appended (u3, e5, b1, s2, etc.)
        # In vendor modes, b/s/ba need to wait for item numbers
        is_vendor_mode = gs.prompt_cntl in ['vendor_shop', 'starting_shop']
        is_spell_memorization_mode = gs.prompt_cntl == 'spell_memorization_mode'
        needs_number_suffix = (cmd in ['u', 'e'] and self.current_needs_numbers) or \
                              (cmd in ['b', 's', 'r', 'id'] and is_vendor_mode) or \
                              (cmd in ['m', 'f'] and is_spell_memorization_mode)
        
        # Special case: 'ba' (buy all) in starting shop - needs send but no number
        is_buy_all = cmd == 'ba' and gs.prompt_cntl == 'starting_shop'
        
        # Special case: 'e' in inventory means equip (not east movement)
        # Override is_movement for 'e' when in inventory/needs_numbers mode
        if cmd == 'e' and self.current_needs_numbers:
            is_movement = False
        
        # Special case: 's' in vendor mode means sell (not south movement)
        if cmd == 's' and is_vendor_mode:
            is_movement = False
        
        # In modes that need numbers (inventory, vendor, etc.), certain commands wait for number/send
        # All other commands (c, m, x, i, etc.) submit immediately
        if (needs_number_suffix or is_buy_all) and not is_movement:
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

        # Adjust bottom_panel height based on mode (label + buttons + input + 30px nav spacer)
        if gs.prompt_cntl in ('player_name', 'puzzle_mode'):
            # QWERTY keyboard: 3 rows × 38px = 114 + 14 + 34 + 30 = 192
            self.bottom_panel.style.height = 192
        elif needs_numbers:
            # Numpad layout: 4 rows × 26px = 104 + 14 + 34 + 30 = 182
            self.bottom_panel.style.height = 182
        else:
            # Normal: 3 rows × 30px = 90 + 14 + 34 + 30 = 168
            self.bottom_panel.style.height = 168

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
                self.create_big_button('a', 'Atk'),  # Attack
                self.create_big_button('c', 'Cst'),  # Cast
                self.create_spacer(),
                self.create_spacer(),# Spacer between A and F
                self.create_big_button('f', 'Fle'),  # Flee
                self.create_spacer(),
            ]
        else:
            left_row1 = [
                self.create_big_button('a', 'Atk'),  # Attack
                self.create_spacer(),              # No cast available
                self.create_spacer(),              # Spacer between A and F
                self.create_spacer(),
                self.create_big_button('f', 'Fle'),  # Flee
                self.create_spacer(),
            ]

        # Row 2: [I][spacers]
        left_row2 = [
            self.create_button('i', 'Inv') if 'i' in cmd_dict else self.create_spacer(),
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
        has_movement = any(k in cmd_dict for k in ['n', 's', 'e', 'w'])

        # === LEFT SIDE: D-PAD (cross/plus shape with arrow symbols) ===
        if has_movement:
            dpad_row1 = [
                self.create_dpad_spacer(),
                self.create_dpad_button('n', '\u25B2') if 'n' in cmd_dict else self.create_dpad_spacer(),
                self.create_dpad_spacer(),
            ]
            dpad_row2 = [
                self.create_dpad_button('w', '\u25C4') if 'w' in cmd_dict else self.create_dpad_spacer(),
                self.create_dpad_center(),
                self.create_dpad_button('e', '\u25BA') if 'e' in cmd_dict else self.create_dpad_spacer(),
            ]
            dpad_row3 = [
                self.create_dpad_spacer(),
                self.create_dpad_button('s', '\u25BC') if 's' in cmd_dict else self.create_dpad_spacer(),
                self.create_dpad_spacer(),
            ]
        else:
            dpad_row1 = [self.create_dpad_spacer() for _ in range(3)]
            dpad_row2 = [self.create_dpad_spacer() for _ in range(3)]
            dpad_row3 = [self.create_dpad_spacer() for _ in range(3)]

        # === RIGHT SIDE: COMMANDS (columns, bottom-right going up then left) ===
        dpad_keys = {'n', 's', 'e', 'w'}

        # Priority order (first = bottom-right, most important)
        priority = ['l', 'i', 'q', 'o', 'dr', 'g', 'r', 'u', 'd', 'p', 'h', 'c',
                     'y', 'x', 'a', 'f', 'b', 'm', 'j',
                     '1', '2', '3', '4', '5', '6', '7', '8', '9']

        cmds_to_place = []
        placed = set()
        for pkey in priority:
            if pkey in cmd_dict and pkey not in dpad_keys and pkey not in placed:
                cmds_to_place.append((pkey, cmd_dict[pkey]))
                placed.add(pkey)
        for k, v in cmd_dict.items():
            if k not in dpad_keys and k not in placed:
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

        for btn in dpad_row1 + [self.create_spacer()] + cmd_row1:
            self.button_row_1.add(btn)
        for btn in dpad_row2 + [self.create_spacer()] + cmd_row2:
            self.button_row_2.add(btn)
        for btn in dpad_row3 + [self.create_spacer()] + cmd_row3:
            self.number_pad_box.add(btn)

    def build_layout_with_numpad(self, commands):
        """
        Two-column layout: command buttons on left (3 rows), numpad on right (4 rows).
        Both columns fit within the same panel height.
        """
        cmd_dict = {key: label for key, label in commands}
        is_altar = gs.prompt_cntl == 'altar_mode'

        # Separate numpad keys from command keys
        numpad_keys = set(str(i) for i in range(10))

        # Priority order (first = bottom-left, most accessible)
        priority = ['x', 'c', 'i', 'a', 's', 'b', 'r', 'u', 'e',
                     'm', 'f', 'j', 'g', 'id', 'ba']

        cmds_to_place = []
        placed = set()
        for pkey in priority:
            if pkey in cmd_dict and pkey not in numpad_keys and pkey not in placed:
                cmds_to_place.append((pkey, cmd_dict[pkey]))
                placed.add(pkey)
        for k, v in cmd_dict.items():
            if k not in numpad_keys and k not in placed:
                cmds_to_place.append((k, v))

        # Build columns (max 3 per column, bottom to top)
        columns = []
        for i in range(0, len(cmds_to_place), 3):
            columns.append(cmds_to_place[i:i+3])

        num_cols = len(columns)
        cmd_row1 = []
        cmd_row2 = []
        cmd_row3 = []

        for col in columns:
            if len(col) > 0:
                k, v = col[0]
                if is_altar and k == 's':
                    cmd_row3.append(toga.Button(
                        'Sac', on_press=lambda w: self.number_pad_input('s'),
                        style=Pack(flex=1, margin=1, font_size=11, font_weight='bold', width=37)))
                else:
                    cmd_row3.append(self.create_button(k, v))
            else:
                cmd_row3.append(self.create_spacer())
            cmd_row2.append(self.create_button(col[1][0], col[1][1]) if len(col) > 1 else self.create_spacer())
            cmd_row1.append(self.create_button(col[2][0], col[2][1]) if len(col) > 2 else self.create_spacer())

        # Left column: command buttons in 3 rows
        left_col = toga.Box(style=Pack(direction=COLUMN, flex=1))
        for row_btns in [cmd_row1, cmd_row2, cmd_row3]:
            row_box = toga.Box(style=Pack(direction=ROW, margin=0, flex=1))
            for btn in row_btns:
                row_box.add(btn)
            left_col.add(row_box)

        # Right column: 4-row phone-style numpad (compact buttons)
        numpad_rows = [
            [self.create_numpad_button('1', compact=True), self.create_numpad_button('2', compact=True), self.create_numpad_button('3', compact=True)],
            [self.create_numpad_button('4', compact=True), self.create_numpad_button('5', compact=True), self.create_numpad_button('6', compact=True)],
            [self.create_numpad_button('7', compact=True), self.create_numpad_button('8', compact=True), self.create_numpad_button('9', compact=True)],
            [self.create_numpad_button('0', compact=True)],
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
                    style=Pack(flex=1, margin=0, font_size=11, font_weight='bold', color='#FFD700', height=26, width=55))

        right_col = toga.Box(style=Pack(direction=COLUMN))
        for row_btns in numpad_rows:
            row_box = toga.Box(style=Pack(direction=ROW, margin=0))
            for btn in row_btns:
                row_box.add(btn)
            right_col.add(row_box)

        # Replace standard 3-row layout with two-column ROW layout
        self.button_panel.clear()
        self.button_panel.style.direction = ROW
        self.button_panel.add(left_col)
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
        Row 2: [.][A][S][D][F][G][H][J][K][L]
        Row 3: [.][Z][X][C][V][B][N][M][.][\u21e7]
        
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
        
        # Row 2: A S D F G H J K L (9 buttons)

        row2_letters = ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L']

        row2 = [self.create_half_spacer()]  # Start with half spacer
        if self.keyboard_uppercase:
            row2.extend([self.create_keyboard_button(letter.lower(), letter) for letter in row2_letters])
        else:
            row2.extend([self.create_keyboard_button(letter.lower(), letter.lower()) for letter in row2_letters])
        
        # Row 3: Shift + Z X C V B N M + backspace/spacer + Shift (10 items to match row 1)
        row3_letters = ['Z', 'X', 'C', 'V', 'B', 'N', 'M']
        # Create shift button
        shift_label = "\u21e7" if self.keyboard_uppercase else "\u21e7"
        shift_button = toga.Button(
            shift_label,
            on_press=self.toggle_keyboard_case,
            style=Pack(flex=1, margin=0, padding=0, font_size=13, font_weight='bold',
                       background_color='#444', color='#FFF', height=38)
        )
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
                           background_color='#333', color='#EEE', height=38)
            )
            row3.append(backspace_button)
        else:
            row3.append(toga.Box(style=Pack(flex=1, height=38)))
        row3.append(toga.Box(style=Pack(flex=1, height=38)))

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
            style=Pack(flex=1, margin=0, padding=0, font_size=13,
                       background_color='#333', color='#EEE', height=38)
        )
        self._compact_android_button(btn)
        return btn

    def _compact_android_button(self, btn):
        """Remove Android Material button internal padding and minimum width."""
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
                # Remove Material insets
                native.setInsetTop(0)
                native.setInsetBottom(0)
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
        """Create a command button."""
        btn = toga.Button(
            cmd_label,
            on_press=lambda w, k=cmd_key, l=cmd_label: self.quick_command(k, l),
            style=Pack(margin=0, font_size=11, width=55,
                       background_color='#333', color='#EEE', height=30)
        )
        self._compact_android_button(btn)
        return btn

    def create_big_button(self, cmd_key, cmd_label):
        """Create a larger button for important combat actions."""
        btn = toga.Button(
            cmd_label,
            on_press=lambda w, k=cmd_key, l=cmd_label: self.quick_command(k, l),
            style=Pack(margin=0, font_size=13, font_weight='bold', width=65, height=34,
                       background_color='#444', color='#FFF')
        )
        self._compact_android_button(btn)
        return btn

    def create_numpad_button(self, number, compact=False):
        """Create a number pad button. Compact mode uses shorter height for 4-row layout."""
        h = 26 if compact else 34
        fs = 11 if compact else 12
        btn = toga.Button(
            number,
            on_press=lambda w, n=number: self.number_pad_input(n),
            style=Pack(margin=0, font_size=fs, font_weight='bold', width=55,
                       color='#4CAF50', height=h, background_color='#2a2a2a')
        )
        self._compact_android_button(btn)
        return btn

    def create_spacer(self):
        """Create an empty spacer that fills remaining space."""
        return toga.Box(style=Pack(flex=1, height=30))
    def create_dpad_button(self, cmd_key, arrow_label):
        """Create a D-pad directional button with arrow symbol and controller styling."""
        btn = toga.Button(
            arrow_label,
            on_press=lambda w, k=cmd_key: self.quick_command(k, cmd_key.upper()),
            style=Pack(margin=0, font_size=14, font_weight='bold', width=50,
                       background_color='#2a2a2a', color='#AAA', height=30)
        )
        self._compact_android_button(btn)
        return btn

    def create_dpad_center(self):
        """Create the center piece of the D-pad cross."""
        return toga.Box(style=Pack(width=50, height=30, background_color='#222'))

    def create_dpad_spacer(self):
        """Create an invisible corner spacer for D-pad cross shape."""
        return toga.Box(style=Pack(width=50, height=30, background_color='#1a1a1a'))
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
                
                # Use first 3 chars of descriptive label for button text
                btn_label = label[:3].capitalize() if len(label) > 1 else actual_cmd.upper()
                
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

        if cmd == 'i' and gs.prompt_cntl == "game_loop":
            gs.prompt_cntl = "inventory"
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

    def render(self):
        """
        Render the game state to the display.
        
        For WebView approach: Generate HTML and set it in the WebView
        For Text approach: Generate plain text and set it in the MultilineTextInput
        """
        # Update input field visibility based on mode
        self.set_input_visibility()
        
        
        # Generate HTML using your existing render() function logic
        html_content = self.generate_html()
        
        # Update WebView with log lines
        full_html = self.wrap_html(html_content, gs.log_lines)
        # Workaround for Toga Android bug #2242: set_content uses loadData()
        # which breaks on '#' chars in CSS. Use loadDataWithBaseURL() instead.
        import sys
        if sys.platform == 'android':
            self.web_view._impl.native.loadDataWithBaseURL(
                None, full_html, "text/html", "utf-8", None
            )
        else:
            self.web_view.set_content("", full_html)
    
    def generate_html(self):
        """
        Generate HTML content for the game display.
        
        This should be your existing render() function logic from cavern12.
        Copy all the HTML generation code here.
        """

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
                    HP:{health_bar(gs.player_character.health, gs.player_character.max_health, width=10)} MP:{mana_bar(gs.player_character.mana, gs.player_character.max_mana, width=10)} | <span style="color:{hunger_color};">H:{gs.player_character.hunger}</span>
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
                        <div style="font-family: monospace; font-size: 12px; padding: 10px; text-align: center;">
                            <div style="font-size: 22px; font-weight: bold; margin-bottom: 20px; color: #FFD700;">
                                 WIZARD'S CAVERN 
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
            current_commands_text = "b# = buy | s# = sell | r# = repair | ba = buyall | x = exit"

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
                            <div style="color: #DAA520; font-size: 12px; margin-top: 2px;">{gs.shop_message}</div>
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
            else:
                current_commands_text = "b# = buy | s# = sell | r# = repair | id# = identify | x = exit"



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
                
                # Build inventory HTML - matching normal inventory style
                player_inv_html = "<h3>Combat Items</h3>"
                player_inv_html += "<div style='max-height: 280px; overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px;'>"
                player_inv_html += "<div style='margin: 0; padding: 0;'>"

                if not combat_usable_items:
                    player_inv_html += "<div style='margin: 2px 0; padding: 0; color: #888;'>(No usable items)</div>"
                else:
                    for i, item in enumerate(combat_usable_items):
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

                current_commands_text = "u# = use | j = jrnl | x = back"


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

                player_inv_html = "<h3>Your Inventory</h3>"

                player_inv_html += "<div style='max-height: 295px; overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px;'>"

                player_inv_html += "<div style='margin: 0; padding: 0;'>"

                sorted_items = get_sorted_inventory(gs.player_character.inventory)

                if not sorted_items:

                    player_inv_html += "<div style='margin: 2px 0; padding: 0;'>(Empty)</div>"

                else:

                    # Reuse the rendering logic from the previous response or your existing code

                    for i, item in enumerate(sorted_items):
                        item_str = format_item_for_display(item, gs.player_character, show_price=False)

                        player_inv_html += f"<div style='margin: 2px 0; padding: 0;'><b>{i + 1}.</b> {item_str}</div>"

                player_inv_html += "</div>"

                player_inv_html += "</div>"

                can_cast = can_cast_spells(gs.player_character)

                inv_commands = "u# = use | e# = eqp | c = cft"

                if can_cast:
                    inv_commands += " | m = spells"

                inv_commands += " | j = jrnl | q = quit | x = exit"

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
            ingredients_html += "<div style='color: #4CAF50; font-weight: bold; margin-bottom: 5px;'>Your Ingredients:</div>"
            if ingredient_counts:
                ing_list = ", ".join([f"{count}x {name}" for name, count in sorted(ingredient_counts.items())])
                ingredients_html += f"<div style='color: #CCC; font-size: 14px;'>{ing_list}</div>"
            else:
                ingredients_html += "<div style='color: #AAA; font-size: 14px; font-style: italic;'>No ingredients. Harvest from Garden rooms!</div>"
            if ration_count > 0:
                ingredients_html += f"<div style='color: #88FF88; font-size: 14px;'>{ration_count}x Rations</div>"
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
                    recipes_html += f"<div style='color: {tier_color}; font-weight: bold; margin: 8px 0 4px 0; border-bottom: 1px solid {tier_color};'>TIER {tier} - {tier_names[tier]}</div>"
                    
                    for recipe_name, recipe_data in by_tier[tier]:
                        crafted_item = recipe_data['result']()
                        ingredients_text = ", ".join([f"{count}x {name}" for name, count in recipe_data['ingredients']])
                        ration_cost = recipe_data.get('ration_cost', 0)
                        if ration_cost > 0:
                            ingredients_text += f", {ration_cost}x Rations"

                        recipes_html += f"""
                            <div style='padding: 6px; margin: 4px 0; background: rgba(255,255,255,0.05); border-radius: 3px; border-left: 3px solid {tier_color};'>
                                <div style='color: #FFD700; font-weight: bold; font-size: 14px;'>{recipe_counter}. {recipe_name}</div>
                                <div style='color: #CCC; font-size: 14px;'>Needs: {ingredients_text}</div>
                                <div style='color: #DDD; font-size: 14px; font-style: italic;'>{crafted_item.description}</div>
                            </div>
                        """
                        recipe_counter += 1
            else:
                recipes_html = "<div style='color: #AAA; font-style: italic; padding: 10px; font-size: 14px;'>No recipes available. Collect more ingredients!</div>"
            
            # Build close recipes HTML
            close_html = ""
            if close:
                close_html = "<div style='margin-top: 10px; padding-top: 8px; border-top: 1px solid #444;'>"
                close_html += "<div style='color: #CCC; font-size: 14px; margin-bottom: 5px;'>Almost Craftable:</div>"
                for recipe_name, recipe_data, _, missing in close[:3]:
                    missing_text = ", ".join([f"{count}x {name}" for name, count in missing])
                    tier = recipe_data.get('tier', 1)
                    close_html += f"<div style='color: #AAA; font-size: 13px;'>T{tier} {recipe_name} - <span style='color: #F44336;'>Need: {missing_text}</span></div>"
                if len(close) > 3:
                    close_html += f"<div style='color: #999; font-size: 13px;'>...and {len(close) - 3} more</div>"
                close_html += "</div>"
            
            crafting_html = f"""
                <div style="border: 2px solid #E040FB; border-radius: 4px; padding: 10px; background: #1a1a1a;">
                    <div style="color: #E040FB; font-weight: bold; font-size: 16px; text-align: center; margin-bottom: 8px;">
                        CRAFTING
                    </div>
                    {ingredients_html}
                    <div style="max-height: 300px; overflow-y: auto;">
                        {recipes_html}
                    </div>
                    {close_html}
                    <div style="text-align: center; margin-top: 8px; color: #CCC; font-size: 14px;">
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
            current_commands_text = "m# = memorize | f# = forget | x = exit"

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

                <div style="display: flex; flex-direction: column; gap: 2px; width: 50%; ">
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
            current_commands_text = f"1-8 = category | s = stats | a = achv | t = {text_label} | g = save | x = back"

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
            current_commands_text = f"b = back | s = stats | a = achv | t = {text_label} | g = save | x = close"

        elif gs.prompt_cntl == "spell_casting_mode":
            # SPELL CASTING - 3 Column: Map | Combat | Spells

            # Generate map HTML
            floor = gs.my_tower.floors[gs.player_character.z]
            highlight_coords = (gs.player_character.y, gs.player_character.x)

            grid_html = generate_grid_html(floor, gs.player_character.x, gs.player_character.y)

            # Generate pixel art sprite for the monster
            monster_sprite_html = generate_monster_sprite_html(gs.active_monster.name)
            evo_border_color, evo_tier_label = get_evolution_tier_style(gs.active_monster)

            # Monster Info
            evo_border_style = f"border: 2px solid {evo_border_color};" if evo_border_color else "border: 2px solid #666;"
            evo_name_color = evo_border_color if evo_border_color else "#F44336"
            monster_html = f"""
                <div style="padding: 4px; border-radius: 4px; {evo_border_style} margin-bottom: 5px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{monster_sprite_html}</div>
                        <div>
                            <div style="color: {evo_name_color}; font-weight: bold; font-size: 15px; margin-bottom: 4px;">{gs.active_monster.name} {evo_tier_label}</div>
                            <div style="font-size: 12px; margin-bottom: 3px;">Level {gs.active_monster.level}</div>
                            <div style="font-size: 12px;">{health_bar(gs.active_monster.health, gs.active_monster.max_health, width=15)}</div>
                            {f'<div style="font-size: 12px; color: #FFB74D; margin-top: 3px;">Weak: {", ".join(gs.active_monster.elemental_weakness)}</div>' if gs.active_monster.elemental_weakness else ''}
                            {f'<div style="font-size: 12px; color: #64B5F6; margin-top: 2px;">Resist: {", ".join(gs.active_monster.elemental_strength)}</div>' if gs.active_monster.elemental_strength else ''}
                        </div>
                    </div>
                </div>
                """

            # Player Combat Info
            player_sprite_html_combat = generate_player_sprite_html(
                getattr(gs.player_character, 'race', 'human'),
                getattr(gs.player_character, 'gender', 'male'),
                getattr(gs.player_character, 'equipped_armor', None)
            )
            player_combat_html = f"""
                <div style="padding: 4px; border-radius: 4px; border: 2px solid #666;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{player_sprite_html_combat}</div>
                        <div>
                            <div style="color: #4CAF50; font-weight: bold; font-size: 15px; margin-bottom: 4px;"> {gs.player_character.name}</div>
                            <div style="font-size: 12px; margin-bottom: 2px;">{health_bar(gs.player_character.health, gs.player_character.max_health, width=15)}</div>
                            <div style="font-size: 12px; margin-bottom: 4px;">{mana_bar(gs.player_character.mana, gs.player_character.max_mana, width=15)}</div>
                            <div style="font-size: 12px;">Atk: {gs.player_character.attack} | Def: {gs.player_character.defense}</div>
                            <div style="font-size: 12px; margin-top: 2px;">Int: {gs.player_character.intelligence} (boosts spells)</div>
                            {f'<div style="font-size: 9px; color: #64B5F6; margin-top: 3px;">Resist: {", ".join(gs.player_character.elemental_strengths)}</div>' if gs.player_character.elemental_strengths else ''}
                            {f'<div style="font-size: 9px; color: #FFB74D; margin-top: 2px;">Weak: {", ".join(gs.player_character.elemental_weaknesses)}</div>' if gs.player_character.elemental_weaknesses else ''}
                        </div>
                    </div>
                </div>
                """

            # Spells List
            available_spells = gs.player_character.memorized_spells
            spells_html = '<div style="padding: 4px; border-radius: 4px; border: 2px solid #E040FB;">'
            spells_html += '<div style="color: #E040FB; font-weight: bold; font-size: 15px; margin-bottom: 6px;"> Cast Spell</div>'

            if not available_spells:
                spells_html += '<div style="color: #F44336; font-size: 12px;">No spells memorized!</div>'
            else:
                for i, spell in enumerate(available_spells):
                    can_cast = gs.player_character.mana >= spell.mana_cost
                    color = "#4CAF50" if can_cast else "#888"

                    spell_line = f'<div style="color: {color}; font-size: 12px; margin-bottom: 6px; padding: 4px; border-radius: 2px;">'
                    spell_line += f'<b>{i + 1}. {spell.name}</b> ({spell.mana_cost} MP)<br>'
                    spell_line += f'&nbsp;&nbsp;Lvl {spell.level} | '

                    if spell.spell_type == 'damage':
                        spell_line += f'{spell.damage_type} | Pwr {spell.base_power}'
                    elif spell.spell_type == 'healing':
                        spell_line += f'Heal {spell.base_power} HP'
                    elif spell.spell_type in ['add_status_effect', 'remove_status']:
                        spell_line += f'{spell.status_effect_name}'

                    spell_line += '</div>'
                    spells_html += spell_line

            spells_html += '</div>'

            # Layout: Map | Combat Info | Spell Menu
            html_code = f"""
                <div style="font-family: monospace; font-size: 12px;">
                    {achievement_notifications}
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px; color: #03A9F4;">Wizard's Cavern</div>
                    {player_stats_html}

                    <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <div>{grid_html}</div>
                        <div style="width: 100%; max-width: 300px;">
                            {monster_html}
                            {player_combat_html}
                        </div>
                    </div>
                    
                    <div class="room-panel" style="width: 100%;">{spells_html}</div>
                    {generate_damage_float_js(gs.active_monster.name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal)}
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
                <div style="padding: 3px; border-radius: 3px; {evo_border_style} margin-bottom: 4px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{monster_sprite_html}</div>
                        <div>
                            <div style="color: {evo_name_color}; font-weight: bold; font-size: 12px; margin-bottom: 2px;">{gs.active_monster.name} {evo_tier_label}</div>
                            <div style="font-size: 9px; margin-bottom: 2px;">Lv {gs.active_monster.level}</div>
                            <div style="font-size: 9px;">{health_bar(gs.active_monster.health, gs.active_monster.max_health, width=10)}</div>
                            {f'<div style="font-size: 8px; color: #FFB74D; margin-top: 2px;">{", ".join(gs.active_monster.elemental_weakness)}</div>' if gs.active_monster.elemental_weakness else ''}
                            {f'<div style="font-size: 8px; color: #64B5F6; margin-top: 1px;">{", ".join(gs.active_monster.elemental_strength)}</div>' if gs.active_monster.elemental_strength else ''}
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
                <div style="padding: 3px; border-radius: 3px; border: 2px solid #666;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:2px;">
                        <div style="flex-shrink:0;">{player_sprite_html_combat}</div>
                        <div>
                            <div style="color: #4CAF50; font-weight: bold; font-size: 12px; margin-bottom: 2px;"> {player_display}</div>
                            <div style="font-size: 9px; margin-bottom: 1px;">{health_bar(gs.player_character.health, gs.player_character.max_health, width=10)}</div>
                            <div style="font-size: 9px; margin-bottom: 2px;">{mana_bar(gs.player_character.mana, gs.player_character.max_mana, width=10)}</div>
                            <div style="font-size: 8px;">A:{gs.player_character.attack} D:{gs.player_character.defense}</div>
                            {f'<div style="font-size: 8px; color: #64B5F6; margin-top: 2px;"> {", ".join(gs.player_character.elemental_strengths)}</div>' if gs.player_character.elemental_strengths else ''}
                            {f'<div style="font-size: 8px; color: #FFB74D; margin-top: 1px;"> {", ".join(gs.player_character.elemental_weaknesses)}</div>' if gs.player_character.elemental_weaknesses else ''}
                            {f'<div style="font-size: 8px; color: #FDD835; margin-top: 1px;">{", ".join(gs.player_character.status_effects.keys())}</div>' if gs.player_character.status_effects else ''}
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
                    {generate_damage_float_js(gs.active_monster.name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal)}
                </div>
                """
            current_commands_text = combat_commands

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
                <div style="padding: 4px; border-radius: 4px; {evo_border_style} margin-bottom: 5px;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{monster_sprite_html}</div>
                        <div>
                            <div style="color: {evo_name_color}; font-weight: bold; font-size: 15px; margin-bottom: 4px;">Fleeing from {gs.active_monster.name} {evo_tier_label}</div>
                            <div style="font-size: 12px; margin-bottom: 3px;">Level {gs.active_monster.level}</div>
                            <div style="font-size: 12px;">{health_bar(gs.active_monster.health, gs.active_monster.max_health, width=15)}</div>
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
                <div style="padding: 4px; border-radius: 4px; border: 2px solid #666;">
                    <div style="display:flex; align-items:center; gap:6px; margin-bottom:3px;">
                        <div style="flex-shrink:0;">{player_sprite_html_combat}</div>
                        <div>
                            <div style="color: #4CAF50; font-weight: bold; font-size: 15px; margin-bottom: 4px;"> {gs.player_character.name}</div>
                            <div style="font-size: 12px; margin-bottom: 2px;">{health_bar(gs.player_character.health, gs.player_character.max_health, width=15)}</div>
                            <div style="font-size: 12px; margin-bottom: 4px;">{mana_bar(gs.player_character.mana, gs.player_character.max_mana, width=15)}</div>
                            <div style="font-size: 12px; color: #FFD700;">Escaped combat!</div>
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

                    {generate_damage_float_js(gs.active_monster.name, gs.last_monster_damage, gs.last_player_damage, gs.last_player_blocked, gs.last_player_status, gs.last_monster_status, gs.last_player_heal)}
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
                    <div style="font-size: 12px; margin-bottom: 2px;">{health_bar(gs.player_character.health, gs.player_character.max_health, width=15)}</div>
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
                    cursed_tag = " <span style='color:#F44336;'>[CURSED]</span>" if getattr(item, 'is_cursed', False) else ""
                    inv_html += f"<div style='margin:2px 0; font-size:12px;'><b>{i+1}.</b> {item_str}{cursed_tag}</div>"

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
                            <div style='overflow-y: auto; border: 1px solid #444; padding: 3px; border-radius: 3px; max-height: 200px;'>
                                {inv_html}
                            </div>
                            {devotion_hint}
                        </div>
                    </div>
                </div>
                """
            current_commands_text = "s# = sacrifice | i = inventory | x = exit"

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
            current_commands_text = "u = go up | i = inventory"
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
            current_commands_text = "d = go down | i = inventory"
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
                    current_commands_text = "n/s/e/w = move | u = go up | i = inventory"
                    if has_lantern:
                        current_commands_text += f" | l = lantern"
                elif current_room.room_type == 'D':
                    current_commands_text = "n/s/e/w = move | d = go down | i = inventory"
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
                current_commands_text = "s# = sacrifice | i = inventory | x = exit"
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
        needs_numbers = gs.prompt_cntl in [
            'inventory',
            'vendor_shop',
            'starting_shop',
            'altar_mode',
            'spell_memorization_mode',
            'spell_casting_mode',
            'journal_mode',
            'crafting_mode',
            'upgrade_scroll_mode',
            'identify_scroll_mode',
            'sell_quantity_mode',
            'taxidermist_mode',
        ]
        
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

        return f"""
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
            </style>
        </head>
        <body>
            <div id="content-area">
                {content}
            </div>
            <div id="game-log"></div>
            <script>
                // Embed log lines from Python
                window.logLines = {log_lines_json};
                
                // Update log content and auto-scroll to bottom
                function updateLog() {{
                    var logDiv = document.getElementById('game-log');
                    if (logDiv && window.logLines) {{
                        logDiv.innerHTML = window.logLines.join('<br>');
                        logDiv.scrollTop = logDiv.scrollHeight;
                    }}
                }}
                // Call on page load
                window.addEventListener('load', updateLog);
            </script>
        </body>
        </html>
        """
    

    
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

