"""
Zotle Puzzle System

A Wordle-style word puzzle integrated into the dungeon.
Players encounter puzzle rooms ('Z') on floors and must guess a scrambled 5-letter word.
"""

import random

from . import game_state as gs
from .game_state import add_log, COLOR_GREEN, COLOR_RESET, COLOR_YELLOW


def scramble_word_for_zotle(word):
    """
    Scramble a word for Zotle:
    1. Take a 5-letter word
    2. Scramble 3 of the letters (keep 2 in place)
    3. Reverse the entire word
    Returns the scrambled word
    """
    word = word.upper()
    word_list = list(word)

    # Choose 3 random positions to scramble
    positions = list(range(5))
    scramble_positions = random.sample(positions, 3)

    # Get the letters at those positions
    letters_to_scramble = [word_list[i] for i in scramble_positions]

    # Shuffle those letters
    random.shuffle(letters_to_scramble)

    # Put them back
    for i, pos in enumerate(scramble_positions):
        word_list[pos] = letters_to_scramble[i]

    # Reverse the entire word
    word_list.reverse()

    return ''.join(word_list)


def check_zotle_guess(guess, target_word):
    """
    Check a guess against the target word (Wordle-style).
    Returns a list of tuples: (letter, status)
    where status is 'correct' (green), 'present' (yellow), or 'absent' (grey)

    NOTE: For Zotle, target_word is the SCRAMBLED word - players must figure out
    both the letters AND their scrambled arrangement!
    """
    guess = guess.upper()
    target = target_word.upper()

    results = []
    target_letters = list(target)

    # First pass: mark correct letters
    for i, letter in enumerate(guess):
        if i < len(target) and letter == target[i]:
            results.append((letter, 'correct'))
            target_letters[i] = None  # Mark as used
        else:
            results.append((letter, None))  # Placeholder

    # Second pass: mark present/absent letters
    for i, (letter, status) in enumerate(results):
        if status is None:
            if letter in target_letters:
                results[i] = (letter, 'present')
                # Remove first occurrence to prevent double-counting
                target_letters[target_letters.index(letter)] = None
            else:
                results[i] = (letter, 'absent')

    return results


def initialize_zotle_puzzle():
    """Initialize a new Zotle puzzle for a game."""
    original_word = random.choice(gs.ZOTLE_WORDS)
    scrambled = scramble_word_for_zotle(original_word)

    return {
        'original_word': original_word,
        'scrambled_word': scrambled,
        'guesses': [],
        'current_guess': ['', '', '', '', ''],  # Current letter input (5 slots)
        'keyboard_used': {},  # Track which letters have been used and their status (dict: letter -> status)
        'solved': False,
        'failed_floors': set()
    }


def format_zotle_guess_html(guess, results):
    """Format a guess with colored results for HTML display."""
    formatted = ""
    for letter, status in results:
        if status == 'correct':
            formatted += f"<span style='color: #4CAF50; font-weight: bold;'>[{letter}]</span>"
        elif status == 'present':
            formatted += f"<span style='color: #FFD700;'>[{letter}]</span>"
        else:  # absent
            formatted += f"<span style='color: #666;'>[{letter}]</span>"
    return formatted


def should_spawn_puzzle_room(floor_number, zotle_puzzle_state):
    """
    Determine if a puzzle room should spawn on this floor.
    - 50% chance per floor (100% in PLAYTEST mode)
    - Only if puzzle not already solved
    - Not on floors where player already failed
    """
    if zotle_puzzle_state is None:
        return False

    if zotle_puzzle_state['solved']:
        return False

    if floor_number in zotle_puzzle_state['failed_floors']:
        return False

    # Always spawn in PLAYTEST mode
    if gs.PLAYTEST:
        return True

    return random.random() < 0.5


def spawn_puzzle_room_on_floor(floor, floor_number):
    """
    Find a suitable room and convert it to a puzzle room.
    Returns True if successful, False otherwise.
    """
    # Find all empty rooms (not walls, entrance, exits, vendors, etc.)
    suitable_rooms = []
    for r in range(floor.rows):
        for c in range(floor.cols):
            room = floor.grid[r][c]
            if room.room_type == '.':  # Empty room
                suitable_rooms.append((r, c))

    if not suitable_rooms:
        return False

    # Pick a random suitable room
    r, c = random.choice(suitable_rooms)
    room = floor.grid[r][c]

    # Convert to puzzle room (using 'Z' for Zotle)
    room.room_type = 'Z'
    room.properties['is_puzzle_room'] = True

    return True
