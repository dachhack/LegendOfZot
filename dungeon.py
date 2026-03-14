"""Dungeon generation and structure classes for Wizard's Cavern."""
import random
from collections import deque
import game_state as gs
from game_state import (
    add_log, COLOR_GREEN, COLOR_RESET, COLOR_YELLOW, COLOR_GREY,
    COLOR_RED, COLOR_PURPLE, COLOR_CYAN,
)


def is_wall_at_coordinate(current_floor, r, c):
    # Ensure coordinates are within bounds
    if not (0 <= r < current_floor.rows and 0 <= c < current_floor.cols):
        #print_to_output("Out of bounds")
        return True

    return current_floor.grid[r][c].room_type == gs.wall_char

def new_grid(grid_rows, grid_cols, wall_char):
    return [[wall_char for _ in range(gs.grid_cols)] for _ in range(gs.grid_rows)]

def count_room_cells(grid, floor_char):
    room_cell_count = 0
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == floor_char:
                room_cell_count += 1
    return room_cell_count

def does_path_not_exist(start_r, start_c, end_r, end_c, grid, floor_char):
    rows = len(grid)
    cols = len(grid[0])
    visited = set()
    queue = deque([(start_r, start_c)])
    visited.add((start_r, start_c))

    if not (0 <= start_r < rows and 0 <= start_c < cols and grid[start_r][start_c] == floor_char):
        return True
    if not (0 <= end_r < rows and 0 <= end_c < cols and grid[end_r][end_c] == floor_char):
        return True

    while queue:
        r, c = queue.popleft()

        if (r, c) == (end_r, end_c):
            return False

        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for dr, dc in directions:
            nr, nc = r + dr, c + dc

            if 0 <= nr < rows and 0 <= nc < cols and \
               grid[nr][nc] == floor_char and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc))

    return True


# --------------------------------------------------------------------------------
# 6. DUNGEON GENERATION
# --------------------------------------------------------------------------------

def drunk_carve(current_row=0, current_col=0, num_steps=1, grid=[], grid_rows_param=0, grid_cols_param=0, floor_char_param='.'):
  for _ in range(num_steps):
      # Ensure current_row/col are within bounds before marking as floor
      if 0 <= current_row < grid_rows_param and 0 <= current_col < grid_cols_param:
          grid[current_row][current_col] = floor_char_param
      else:
          # If initial current_row/col are out of bounds, try to find a valid starting point
          # or handle this edge case. For now, we'll let it proceed with best effort.
          pass

      direction = random.randint(0, 3)
      new_row, new_col = current_row, current_col

      if direction == 0:
          new_row -= 1
      elif direction == 1:
          new_row += 1
      elif direction == 2:
          new_col -= 1
      elif direction == 3:
          new_col += 1

      if 1 <= new_row < (grid_rows_param-1) and 1 <= new_col < (grid_cols_param-1):
          current_row, current_col = new_row, new_col
  return grid

def carve_grid(grid_rows_param, grid_cols_param, grid, floor_char_param, top_steps=0, bottom_steps=0, center_steps=0):
   # Ensure start/end points are valid before carving
   start_r, start_c = 1, 1
   end_r, end_c = grid_rows_param - 2, grid_cols_param - 2

   # Adjust start/end points if they are out of bounds for very small grids
   if start_r < 0: start_r = 0
   if start_c < 0: start_c = 0
   if end_r >= grid_rows_param: end_r = grid_rows_param - 1
   if end_c >= grid_cols_param: end_c = grid_cols_param - 1
   if end_r < 0: end_r = 0 # Handle 0 or 1 row grids
   if end_c < 0: end_c = 0 # Handle 0 or 1 col grids


   grid = drunk_carve(start_r, start_c, top_steps, grid, grid_rows_param, grid_cols_param, floor_char_param)
   grid = drunk_carve(end_r, end_c, bottom_steps, grid, grid_rows_param, grid_cols_param, floor_char_param)

   count=0
   # Only check path if start and end are valid and distinct
   if 0 <= start_r < grid_rows_param and 0 <= start_c < grid_cols_param and \
      0 <= end_r < grid_rows_param and 0 <= end_c < grid_cols_param and \
      (start_r, start_c) != (end_r, end_c):
       while does_path_not_exist(start_r, start_c, end_r, end_c, grid, floor_char_param) and count<4:
         grid = drunk_carve(int(grid_rows_param/2), int(grid_cols_param/2), 75, grid, grid_rows_param, grid_cols_param, floor_char_param)
         count+=1

   maxed = count<4

   return grid, maxed


# --------------------------------------------------------------------------------
# 7. DUNGEON STRUCTURE (Room, Floor, Tower)
# --------------------------------------------------------------------------------

class Room:
    def __init__(self, room_type, properties=None):
        self.room_type = room_type
        self.properties = properties if properties is not None else {}
        self.discovered = False

    def discover(self):
        """Mark room as discovered. Returns True if newly discovered, False if already known."""
        if not self.discovered:
            self.discovered = True
            return True
        return False

    def __repr__(self):
        return f"Room(type='{self.room_type}', properties={self.properties})"


class Floor:
    def __init__(self, rows, cols, wall_char='#', floor_char='.'):
        self.rows = rows
        self.cols = cols
        self.wall_char = wall_char
        self.floor_char = floor_char
        self.grid = [] # Will hold a rows x cols grid of Room objects
        self.properties = {}  # Floor-level flags (e.g. raid_mode_active)

    def generate_carved_layout(self, wall_char, floor_char,
                                 top_steps=0, bottom_steps=0, center_steps=0):
        temp_char_grid = new_grid(self.rows, self.cols, wall_char)

        while True:
          carved_grid, maxed_attempts = carve_grid(self.rows, self.cols, temp_char_grid, floor_char,
                                                  top_steps, bottom_steps, center_steps)
          if maxed_attempts:
            break

        return carved_grid

    def populate_rooms(self, carved_layout_grid, specified_chars_for_fill, required_chars_to_place_randomly,
                       wall_char, floor_char, forced_placement_char=None, forced_placement_coords=None,
                       p_limits=(0, 100), c_limits=(0, 100), w_limits=(0, 100), a_limits=(0, 100), l_limits=(0, 100), dungeon_limits=(0, 100), t_limits=(0, 100), garden_limits=(0, 100), o_limits=(0, 100), m_limits=(0, 100),
                       b_limits=(0,0), f_limits=(0,0), q_limits=(0,0), k_limits=(0,0), x_limits=(0,0)):
        self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        available_floor_cells_initial = []

        for r in range(self.rows):
            for c in range(self.cols):
                char = carved_layout_grid[r][c]
                if char == wall_char:
                    self.grid[r][c] = Room(wall_char)
                elif char == floor_char:
                    available_floor_cells_initial.append((r, c))

        available_floor_cells_for_random = [coord for coord in available_floor_cells_initial if self.grid[coord[0]][coord[1]] is None]

        # Initialize counters for limited characters
        char_counts_map = {'P': 0, 'C': 0, 'W': 0, 'A': 0, 'L': 0, 'N': 0, 'T': 0, 'G': 0, 'O': 0, 'M': 0, 'B': 0, 'F': 0, 'Q': 0, 'K': 0, 'X': 0}
        chagarden_limits_map = {'P': p_limits, 'C': c_limits, 'W': w_limits, 'A': a_limits, 'L': l_limits, 'N': dungeon_limits, 'T': t_limits, 'G': garden_limits, 'O': o_limits, 'M': m_limits, 'B': b_limits, 'F': f_limits, 'Q': q_limits, 'K': k_limits, 'X': x_limits}
        priority_chars = ['P', 'C', 'W', 'A', 'L', 'N', 'T', 'G', 'O', 'M', 'B', 'F', 'Q', 'K', 'X']


        # Handle forced placement (Entrance 'E' or Downstairs 'D')
        if forced_placement_char and forced_placement_coords:
            r, c = forced_placement_coords
            if 0 <= r < self.rows and 0 <= c < self.cols and carved_layout_grid[r][c] == floor_char:
                self.grid[r][c] = Room(forced_placement_char)
                if (r, c) in available_floor_cells_for_random:
                    available_floor_cells_for_random.remove((r, c))
                # Update count if forced char is one of the limited types
                if forced_placement_char in char_counts_map:
                    char_counts_map[forced_placement_char] += 1
            else:
                #add_log(f"{COLOR_YELLOW}Warning: Forced placement coordinates {forced_placement_coords} for '{forced_placement_char}' is not a floor cell or out of bounds. Attempting to find alternative.{COLOR_RESET}")
                found_alt = False
                for alt_r, alt_c in list(available_floor_cells_for_random):
                    if self.grid[alt_r][alt_c] is None:
                        self.grid[alt_r][alt_c] = Room(forced_placement_char)
                        available_floor_cells_for_random.remove((alt_r, alt_c))
                        found_alt = True
                        # Update count if forced char is one of the limited types
                        if forced_placement_char in char_counts_map:
                            char_counts_map[forced_placement_char] += 1
                        break
                if not found_alt:
                    raise ValueError(f"{COLOR_YELLOW}Could not find a valid floor cell for forced placement of '{forced_placement_char}'.{COLOR_RESET}")

        # Place explicitly required_chars (U,V) into distinct *random* available floor cells
        random.shuffle(available_floor_cells_for_random)

        for char_type in required_chars_to_place_randomly:
            if available_floor_cells_for_random:
                r, c = available_floor_cells_for_random.pop(0)
                self.grid[r][c] = Room(char_type)
                # Update count if this char is one of the limited types
                if char_type in char_counts_map:
                    char_counts_map[char_type] += 1
            else:
                add_log(f"{COLOR_YELLOW}Warning: Not enough *empty* floor cells to place required character {char_type}.{COLOR_RESET}")

        # Prioritize placing characters to meet minimum requirements for P, C, W, A
        cells_to_process_for_min_fill = list(available_floor_cells_for_random)
        random.shuffle(cells_to_process_for_min_fill)

        for char_to_fill in priority_chars:
            min_count, _ = chagarden_limits_map[char_to_fill]
            while char_counts_map[char_to_fill] < min_count and cells_to_process_for_min_fill:
                r, c = cells_to_process_for_min_fill.pop(0)
                if self.grid[r][c] is None: # Only place if cell is empty
                    self.grid[r][c] = Room(char_to_fill)
                    char_counts_map[char_to_fill] += 1
                    # Remove from original available_floor_cells_for_random as well
                    if (r, c) in available_floor_cells_for_random:
                        available_floor_cells_for_random.remove((r, c))

        # Re-initialize available_floor_cells_for_random based on current empty spots
        available_floor_cells_for_random = [coord for coord in available_floor_cells_initial if self.grid[coord[0]][coord[1]] is None]
        random.shuffle(available_floor_cells_for_random)

        # Fill the remaining empty floor cells with random specified_chars respecting max limits
        excluded_from_fill = set(required_chars_to_place_randomly + [wall_char])
        if forced_placement_char:
            excluded_from_fill.add(forced_placement_char)

        for r, c in available_floor_cells_for_random: # Iterate over remaining empty cells
            if self.grid[r][c] is None: # Double-check if cell is still empty (should be)
                valid_fill_options = []
                for char in specified_chars_for_fill:
                    if char not in excluded_from_fill:
                        if char in priority_chars:
                            if char_counts_map[char] < chagarden_limits_map[char][1]: # Check max limit dynamically
                                valid_fill_options.append(char)
                        else:
                            valid_fill_options.append(char)

                if not valid_fill_options:
                    chosen_char = floor_char # Fallback if all other fill options reached max
                else:
                    chosen_char = random.choice(valid_fill_options)

                self.grid[r][c] = Room(chosen_char)
                if chosen_char in char_counts_map:
                    char_counts_map[chosen_char] += 1

        # Final check: Ensure all cells are filled
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] is None:
                    self.grid[r][c] = Room(floor_char)

    def print_floor(self, highlight_coords=None):
        for r_idx in range(self.rows):
            row_out=""
            for c_idx in range(self.cols):
                room = self.grid[r_idx][c_idx]
                if room.discovered or (r_idx, c_idx) == highlight_coords:
                    char_to_print = room.room_type
                    if char_to_print == '#':
                      char_to_print = f"{COLOR_GREY}#{COLOR_RESET}";
                else:
                    char_to_print = ' ' # Fog of war character
                cell_str = f"[{char_to_print}]" if highlight_coords == (r_idx, c_idx) else f" {char_to_print} "
                row_out+=cell_str
            #add_log(row_out)

    def print_floor_debug(self):
        """Prints the floor layout showing all room types, ignoring fog of war."""
        for r_idx in range(self.rows):
            for c_idx in range(self.cols):
                room = self.grid[r_idx][c_idx]
                char_to_print = room.room_type
                output = f" {char_to_print} "
                #add_log(output, end="")
            #add_log()

    def __repr__(self):
        grid_str_list = []
        for row in self.grid:
            row_str = " ".join([room.room_type for room in row])
            grid_str_list.append(row_str)
        return "Floor(\n" + "\n".join(grid_str_list) + "\n)"

class Tower:
    def __init__(self, start_coords=(0,0)):
        self.floors = []
        self.start_coords=start_coords

    def add_floor(self, specified_chars, required_chars, grid_rows, grid_cols,
                  wall_char, floor_char,
                  top_steps=75, bottom_steps=75, center_steps=75,
                  p_limits=(0, 100), c_limits=(0, 100), w_limits=(0, 100), a_limits=(0, 100), l_limits=(0, 100), dungeon_limits=(0, 100), t_limits=(0, 100), garden_limits=(0, 100), o_limits=(0, 100), m_limits=(0, 100),
                  b_limits=(0,0), f_limits=(0,0), q_limits=(0,0), k_limits=(0,0), x_limits=(0,0)):
        # Late imports to avoid circular dependencies
        from game_systems import generate_vault_on_floor
        from zotle import should_spawn_puzzle_room, spawn_puzzle_room_on_floor
        from item_templates import MAGIC_SHOP_MIN_FLOOR, MAGIC_SHOP_CHANCE

        new_floor = Floor(gs.grid_rows, gs.grid_cols, wall_char, floor_char)

        carved_layout_grid = new_floor.generate_carved_layout(
            wall_char, floor_char, top_steps, bottom_steps, center_steps
        )

        forced_placement_char = None
        forced_placement_coords = None

        # ORACLE ROOMS: Spawn on every other floor (even floors: 2, 4, 6, 8...)
        # Floor number is len(self.floors) + 1 (since we haven't appended yet)
        floor_number = len(self.floors) + 1
        if floor_number % 2 == 0:  # Even floors get 1 oracle room guaranteed
            actual_o_limits = (1, 1)
        else:  # Odd floors get no oracle rooms
            actual_o_limits = (0, 0)

        # BLACKSMITH (B): floors 5-50
        actual_b_limits = b_limits if floor_number >= 5 else (0, 0)

        # SHRINE OF THE FALLEN (F): floors 1-20 only
        actual_f_limits = f_limits if floor_number <= 20 else (0, 0)

        # ALCHEMIST'S LAB (Q): floors 12-40
        actual_q_limits = q_limits if 12 <= floor_number <= 40 else (0, 0)

        # WAR ROOM (K): floors 20-50
        actual_k_limits = k_limits if floor_number >= 20 else (0, 0)

        # TAXIDERMIST (X): floors 10-45
        actual_x_limits = x_limits if 10 <= floor_number <= 45 else (0, 0)

        # FIX: Handle required_chars differently for first floor vs subsequent floors
        if not self.floors:  # First floor
            # First floor needs D and V, but not E (forced) or U (doesn't exist yet)
            required_for_random_placement = [char for char in gs.required_chars if char not in ['E', 'U']]
        else:  # Subsequent floors
            # Subsequent floors need D and V, but not U (forced)
            required_for_random_placement = [char for char in gs.required_chars if char not in ['U']]

        current_fill_pool = [char for char in gs.specified_chars if char not in ['E', 'D', 'U']]
        if floor_char not in current_fill_pool:
            current_fill_pool.append(floor_char)


        if not self.floors: # First floor
            forced_placement_char = 'E'

            # Use the tower's start_coords for 'E' if it's a valid floor cell
            if 0 <= self.start_coords[0] < gs.grid_rows and 0 <= self.start_coords[1] < gs.grid_cols and carved_layout_grid[self.start_coords[0]][self.start_coords[1]] == floor_char:
                forced_placement_coords = self.start_coords
            else:
                # Fallback to finding the first available floor cell if start_coords is invalid
                for r in range(gs.grid_rows):
                    for c in range(gs.grid_cols):
                        if carved_layout_grid[r][c] == floor_char:
                            forced_placement_coords = (r, c)
                            break
                    if forced_placement_coords:
                        break
            if not forced_placement_coords:
                raise ValueError("Could not find a floor cell to place the entrance 'E'.")
            #add_log(f"Generated first floor with 'E' at {forced_placement_coords}.")
            #required_for_random_placement.append('U')
        else: # Subsequent floors
            forced_placement_char = 'U'

            # Place 'U' at start_coords (matching where we'd enter from previous floor's 'D')
            if 0 <= self.start_coords[0] < gs.grid_rows and 0 <= self.start_coords[1] < gs.grid_cols and carved_layout_grid[self.start_coords[0]][self.start_coords[1]] == floor_char:
                forced_placement_coords = self.start_coords
            else:
                # Fallback to finding the first available floor cell if start_coords is invalid
                for r in range(gs.grid_rows):
                    for c in range(gs.grid_cols):
                        if carved_layout_grid[r][c] == floor_char:
                            forced_placement_coords = (r, c)
                            break
                    if forced_placement_coords:
                        break
            if not forced_placement_coords:
                raise ValueError("Could not find a floor cell to place the upstairs 'U'.")
            #required_for_random_placement.append('U')

        new_floor.populate_rooms(carved_layout_grid,
                             current_fill_pool,
                             required_for_random_placement,
                             wall_char, floor_char,
                             forced_placement_char=forced_placement_char,
                             forced_placement_coords=forced_placement_coords,
                             p_limits=p_limits,
                             c_limits=c_limits,
                             w_limits=w_limits,
                             a_limits=a_limits,
                             l_limits=l_limits,
                             dungeon_limits=dungeon_limits,
                             t_limits=t_limits,
                             garden_limits=garden_limits,
                             o_limits=actual_o_limits,
                             m_limits=m_limits,
                             b_limits=actual_b_limits,
                             f_limits=actual_f_limits,
                             q_limits=actual_q_limits,
                             k_limits=actual_k_limits,
                             x_limits=actual_x_limits)

        # 50% spawn chance for B/F/Q/K: remove the room if the coin flip fails
        for room_char in ('B', 'F', 'Q', 'K', 'X'):
            if random.random() < 0.50:
                for r in range(new_floor.rows):
                    for c in range(new_floor.cols):
                        if new_floor.grid[r][c] and new_floor.grid[r][c].room_type == room_char:
                            new_floor.grid[r][c].room_type = '.'
                            break

        # Check if this is Floor 50 - create boss arena instead of normal floor
        if len(self.floors) == 49:  # 0-indexed, so floor 49 is the 50th floor
            self.create_floor_50_boss_arena(new_floor)
        else:
            if generate_vault_on_floor(new_floor, len(self.floors)):
                add_log(f"{COLOR_PURPLE}A hidden vault chamber has been carved into this floor...{COLOR_RESET}")

            # BUG LEVEL: Spawn Zot's Shrinking Bug Level on floors 8-15
            # Only one bug level per game, triggered by random chance
            if self._should_create_bug_level(floor_number):
                self._create_bug_level(new_floor, floor_number)

            # Setup special room mechanics for dungeons and tombs
            self.setup_dungeons_and_tombs(new_floor, len(self.floors))

            # Spawn puzzle room on ~50% of floors (Zotle)
            if gs.zotle_puzzle is not None and should_spawn_puzzle_room(len(self.floors), gs.zotle_puzzle):
                if spawn_puzzle_room_on_floor(new_floor, len(self.floors)):
                    add_log(f"{COLOR_PURPLE}You sense a mysterious presence on this floor...{COLOR_RESET}")

            # Platino: hidden boss on floor 42 if player has sold to 40+ unique vendors
            if len(self.floors) == 42:
                vendors_sold = len(gs.game_stats.get('vendors_sold_to', set()))
                if vendors_sold >= 40:
                    # Find an empty room for Platino
                    empty_rooms = []
                    for r in range(new_floor.rows):
                        for c in range(new_floor.cols):
                            if new_floor.grid[r][c].room_type == '.':
                                empty_rooms.append((r, c))
                    if empty_rooms:
                        pr, pc = random.choice(empty_rooms)
                        new_floor.grid[pr][pc].room_type = 'M'
                        new_floor.grid[pr][pc].properties['is_platino'] = True
                        add_log(f"{COLOR_PURPLE}Something ancient stirs on this floor...{COLOR_RESET}")

            # Ye Olde Magic Shoppe: rare chance on floors 20+
            current_floor_num = len(self.floors)
            if current_floor_num >= MAGIC_SHOP_MIN_FLOOR and random.random() < MAGIC_SHOP_CHANCE:
                # Find an empty room to place the magic shop
                empty_rooms = []
                for r in range(new_floor.rows):
                    for c in range(new_floor.cols):
                        if new_floor.grid[r][c] and new_floor.grid[r][c].room_type == '.':
                            empty_rooms.append((r, c))
                if empty_rooms:
                    mr, mc = random.choice(empty_rooms)
                    new_floor.grid[mr][mc].room_type = 'V'
                    new_floor.grid[mr][mc].properties['is_magic_shop'] = True
                    add_log(f"{COLOR_PURPLE}You sense arcane commerce somewhere on this floor...{COLOR_RESET}")

        self.floors.append(new_floor)

    def create_floor_50_boss_arena(self, floor):
        """Create the special Floor 50 boss arena with Zot's Guardian"""
        add_log("")
        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        add_log(f"{COLOR_RED}*** YOU HAVE REACHED FLOOR 50! ***{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        add_log(f"{COLOR_YELLOW}The final chamber... Zot's Guardian awaits!{COLOR_RESET}")
        add_log("")

        # Mark all rooms as special boss floor
        for r in range(floor.rows):
            for c in range(floor.cols):
                room = floor.grid[r][c]
                if room and room.room_type == '.':
                    # Convert center area to boss arena
                    if r == floor.rows // 2 and c == floor.cols // 2:
                        room.room_type = 'M'  # Boss monster room
                        room.properties['is_boss_arena'] = True
                        room.properties['has_zots_guardian'] = True

    def setup_dungeons_and_tombs(self, floor, floor_number):
        """
        Setup special mechanics for dungeons and tombs on a floor.
        - Assign dungeon keys to specific monsters
        - Surround tombs with undead monsters
        """
        dungeon_rooms = []
        tomb_rooms = []
        monster_rooms = []

        # Find all dungeons, tombs, and monsters on this floor
        for r in range(floor.rows):
            for c in range(floor.cols):
                room = floor.grid[r][c]
                if room.room_type == 'N':
                    dungeon_rooms.append((c, r, floor_number))
                elif room.room_type == 'T':
                    tomb_rooms.append((c, r, floor_number))
                elif room.room_type == 'M':
                    monster_rooms.append((c, r))

        # Assign keys to monsters for each dungeon
        available_monsters = list(monster_rooms)
        random.shuffle(available_monsters)

        for dungeon_coords in dungeon_rooms:
            if available_monsters:
                # Assign this dungeon's key to a specific monster
                monster_pos = available_monsters.pop(0)
                dungeon_room = floor.grid[dungeon_coords[1]][dungeon_coords[0]]
                # Store which monster has this dungeon's key
                dungeon_room.properties['key_holder'] = monster_pos

        # Surround tombs with undead monsters
        for tomb_x, tomb_y, tomb_z in tomb_rooms:
            # Check all adjacent non-wall cells
            adjacent_positions = [
                (tomb_x - 1, tomb_y),  # West
                (tomb_x + 1, tomb_y),  # East
                (tomb_x, tomb_y - 1),  # North
                (tomb_x, tomb_y + 1),  # South
            ]

            for adj_x, adj_y in adjacent_positions:
                if 0 <= adj_x < floor.cols and 0 <= adj_y < floor.rows:
                    adj_room = floor.grid[adj_y][adj_x]
                    # Only place on floor tiles (empty rooms)
                    if adj_room.room_type == '.':
                        # Convert to undead monster
                        adj_room.room_type = 'M'
                        adj_room.properties['undead_guardian'] = True
                        adj_room.properties['tomb_location'] = (tomb_x, tomb_y, tomb_z)

    def _should_create_bug_level(self, floor_number):
        """Determine if this floor should be a bug level.
        One bug level per game, appears on floors 8-15 with 40% chance per floor."""
        # Only spawn on floors 8-15
        if floor_number < 8 or floor_number > 15:
            return False
        # Only one bug level per game
        if gs.bug_level_floors:
            return False
        # 40% chance per eligible floor (guarantees it shows up in that range)
        if gs.PLAYTEST:
            return floor_number == 8  # Always spawn on floor 8 in playtest
        return random.random() < 0.40

    def _create_bug_level(self, floor, floor_number):
        """Transform a floor into Zot's Shrinking Bug Level.
        Replaces all monster rooms with bug monsters and places the Bug Queen."""
        from game_data import BUG_MONSTER_TEMPLATES

        floor_index = floor_number - 1  # Convert to 0-indexed
        gs.bug_level_floors[floor_index] = True
        floor.properties['is_bug_level'] = True

        # Strip rooms that don't fit the bug hive theme.
        # Keep: U (stairs up), D (stairs down), C (chests), M (monsters), . (empty), # (walls)
        # Convert everything else to bug monsters or empty floors.
        rooms_to_bugs = {'W', 'V', 'A', 'N', 'T'}    # Warps, vendors, altars, dungeons, tombs -> bugs
        rooms_to_empty = {'P', 'L', 'G', 'O', 'B', 'F', 'Q', 'K', 'X', 'Z'}  # Pools, libraries, etc -> empty
        for r in range(floor.rows):
            for c in range(floor.cols):
                room = floor.grid[r][c]
                if room.room_type in rooms_to_bugs:
                    room.room_type = 'M'
                    room.properties['is_bug_monster'] = True
                elif room.room_type in rooms_to_empty:
                    room.room_type = '.'

        # Find all monster rooms and empty rooms
        monster_rooms = []
        empty_rooms = []
        for r in range(floor.rows):
            for c in range(floor.cols):
                room = floor.grid[r][c]
                if room.room_type == 'M':
                    monster_rooms.append((r, c))
                elif room.room_type == '.':
                    empty_rooms.append((r, c))

        # Mark all existing monster rooms as bug monsters
        for r, c in monster_rooms:
            floor.grid[r][c].properties['is_bug_monster'] = True

        # NOTE: The Bug Queen is NOT placed during floor creation.
        # She spawns dynamically after all other bug monsters are defeated,
        # appearing to avenge her fallen swarm. See _check_bug_queen_spawn()
        # in combat.py.

        # Place a Growth Mushroom in a chest on this floor (backup way to restore size)
        chest_rooms = []
        for r in range(floor.rows):
            for c in range(floor.cols):
                if floor.grid[r][c].room_type == 'C':
                    chest_rooms.append((r, c))
        if chest_rooms:
            cr, cc = random.choice(chest_rooms)
            floor.grid[cr][cc].properties['has_growth_mushroom'] = True

        add_log("")
        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        add_log(f"{COLOR_RED}*** ZOT'S MISCHIEF ***{COLOR_RESET}")
        add_log(f"{COLOR_PURPLE}============================================================{COLOR_RESET}")
        add_log(f"{COLOR_CYAN}You sense strange magic on this floor...{COLOR_RESET}")
        add_log(f"{COLOR_YELLOW}The air buzzes with the sound of enormous insects!{COLOR_RESET}")
        add_log("")

    def __repr__(self):
        return f"Tower(number_of_floors={len(self.floors)})"
