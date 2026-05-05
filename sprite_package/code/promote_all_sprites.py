"""
Unified sprite promotion script.

Reads the per-category sprite_data_*.py snippets and the in_game/ + reserve/
PNG renders, and promotes them to the canonical pool. Idempotent: re-running
overwrites existing entries with the same pids.

Usage from your repo root:
    python3 promote_all_sprites.py [--pool path/to/canonical_pool_full.pkl] \
                                   [--package path/to/wizards_cavern_sprites] \
                                   [--include-reserve] [--dry-run] [--categories CAT [CAT ...]]

What it does:
    1. Loads canonical pool (creates a new one if --pool doesn't exist).
    2. For each category in `code/sprite_data_<cat>.py`:
       a. For named categories: walks _<CAT>_MAP[item_name] = [(pid, vi), ...]
          and promotes each pid + its image from in_game/by_category/<cat>/
          into the pool with `category: <cat>`, `game_data` populated.
       b. For generic categories: walks _<CAT>_POOL = [pid, ...] and promotes
          each pid as `category: <cat>` with `game_data.item_name = None`.
       c. For rooms: special-cased — uses sprite_data_rooms.py's _ROOM_MAP and
          _VARIANT_MAP (sheet, row, col) tuples; slices from source_sheets/.
    3. If --include-reserve, also promotes reserve/<cat>/*.png for every category.
    4. Writes pool back unless --dry-run.

This is the "merge the package back into your pool" step. After this, your
canonical_pool_full.pkl is fully refreshed.
"""

import argparse
import base64
import importlib.util
import io
import json
import pickle
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. pip install Pillow", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# Helpers
# ============================================================================

def load_module_from_file(path):
    """Dynamically import a sprite_data_<cat>.py snippet."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def png_to_b64(path):
    """Read a PNG, convert to base64 webp at 80% quality (matches pool conventions)."""
    im = Image.open(path).convert("RGBA")
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=80, method=4)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ============================================================================
# Per-category promotion logic
# ============================================================================

def promote_named_category(category, package_dir, pool, by_pid_files):
    """Walks _<CAT>_MAP from sprite_data_<cat>.py and promotes."""
    snippet_path = package_dir / "code" / f"sprite_data_{category}.py"
    if not snippet_path.exists():
        print(f"  skip {category}: no sprite_data_{category}.py")
        return 0
    mod = load_module_from_file(snippet_path)
    map_var_name = f"_{category.upper()}_MAP"
    item_map = getattr(mod, map_var_name, None)
    if item_map is None:
        print(f"  skip {category}: snippet has no {map_var_name}")
        return 0

    n = 0
    for item_name, variants in item_map.items():
        for variant in variants:
            # Each variant: (pid, variant_index) for non-rooms
            pid, variant_index = variant[0], variant[1]
            if pid not in by_pid_files:
                print(f"  WARN {category}/{pid}: PNG not found in package")
                continue
            png_path = by_pid_files[pid]
            try:
                b64 = png_to_b64(png_path)
            except Exception as e:
                print(f"  WARN {category}/{pid}: png read failed: {e}")
                continue
            pool[pid] = {
                "pid": pid,
                "cat": category,
                "img_b64": b64,
                "sheet": None,  # original sheet info preserved in library if needed
                "src_label": None,
                "game_data": {
                    "item_name": item_name,
                    "category": category,
                    "variant_index": variant_index,
                },
                "status": "in-game",
            }
            n += 1
    return n


def promote_generic_category(category, package_dir, pool, by_pid_files):
    """Walks _<CAT>_POOL and promotes."""
    snippet_path = package_dir / "code" / f"sprite_data_{category}.py"
    if not snippet_path.exists():
        print(f"  skip {category}: no sprite_data_{category}.py")
        return 0
    mod = load_module_from_file(snippet_path)
    pool_var_name = f"_{category.upper()}_POOL"
    pid_list = getattr(mod, pool_var_name, None)
    if pid_list is None:
        print(f"  skip {category}: snippet has no {pool_var_name}")
        return 0

    n = 0
    for variant_index, pid in enumerate(pid_list):
        if pid not in by_pid_files:
            print(f"  WARN {category}/{pid}: PNG not found in package")
            continue
        try:
            b64 = png_to_b64(by_pid_files[pid])
        except Exception as e:
            print(f"  WARN {category}/{pid}: png read failed: {e}")
            continue
        pool[pid] = {
            "pid": pid,
            "cat": category,
            "img_b64": b64,
            "sheet": None,
            "src_label": None,
            "game_data": {
                "item_name": None,
                "category": category,
                "variant_index": variant_index,
            },
            "status": "in-game",
        }
        n += 1
    return n


def promote_rooms(package_dir, pool):
    """Rooms uses (sheet_id, row, col) — slice from source_sheets/."""
    snippet_path = package_dir / "code" / "sprite_data_rooms.py"
    if not snippet_path.exists():
        print("  skip rooms: no sprite_data_rooms.py")
        return 0
    mod = load_module_from_file(snippet_path)

    # The rooms snippet has _SHEET_NATIVE_CELL, _ROOM_MAP, _VARIANT_MAP
    sheet_native = getattr(mod, "_SHEET_NATIVE_CELL", {})
    room_map = getattr(mod, "_ROOM_MAP", {})
    variant_map = getattr(mod, "_VARIANT_MAP", {})

    sheet_files = {
        "S8A": "S8A_Doors_Floors1.png", "S8B": "S8B_Doors_Floors2.png",
        "S8C": "S8C_Doors_Floors3.png", "S8D": "S8D_Doors_Floors4.png",
        "S8E": "S8E_Doors_Floors5.png", "S8F": "S8F_Doors_Floors6.png",
        "S8G": "S8G_Misc1.png", "S8H": "S8H_Misc2.png", "S8I": "S8I_Misc3.png",
        "S8J": "S8J.png", "S8K": "S8K.png", "S8L": "S8L.png", "S8M": "S8M.png",
    }
    sheets_dir = package_dir / "source_sheets"
    src_cache = {}

    def slice_to_b64(sheet_id, row, col):
        if sheet_id not in src_cache:
            src_cache[sheet_id] = Image.open(sheets_dir / sheet_files[sheet_id]).convert("RGBA")
        native = sheet_native[sheet_id]
        tile = src_cache[sheet_id].crop((col*native, row*native, (col+1)*native, (row+1)*native))
        tile = tile.resize((96, 96), Image.NEAREST)
        buf = io.BytesIO()
        tile.save(buf, format="WEBP", quality=80, method=4)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    n = 0
    rm_id = 0
    pid_seen = {}  # (sheet, row, col) → pid (so duplicate cells get same RM id)

    def emit(slot_key, sheet, row, col, variant_index, source_dict):
        nonlocal rm_id, n
        key = (sheet, row, col)
        if key in pid_seen:
            pid = pid_seen[key]
        else:
            rm_id += 1
            pid = f"RM{rm_id:04d}"
            pid_seen[key] = pid
            try:
                b64 = slice_to_b64(sheet, row, col)
            except Exception as e:
                print(f"  WARN rooms/{pid}: slice failed: {e}")
                return
            pool[pid] = {
                "pid": pid,
                "cat": "rooms",
                "img_b64": b64,
                "sheet": sheet,
                "src_label": f"r{row:02d}c{col:02d}",
                "game_data": {
                    "item_name": slot_key,
                    "category": "rooms",
                    "variant_index": variant_index,
                    **source_dict,
                },
                "status": "in-game",
            }
            n += 1

    for slot_key, variants in room_map.items():
        for variant_index, (sheet, row, col) in enumerate(variants):
            emit(slot_key, sheet, row, col, variant_index, {"slot_kind": "base"})
    for slot_key, variants in variant_map.items():
        for variant_index, (sheet, row, col) in enumerate(variants):
            emit(slot_key, sheet, row, col, variant_index, {"slot_kind": "variant"})

    return n


def promote_reserve(reserve_dir, pool):
    """Walk <reserve_dir>/<cat>/*.png + manifest.json to get pid→file mapping; promote."""
    n = 0
    reserve_dir = Path(reserve_dir)
    if not reserve_dir.exists():
        return 0
    for cat_dir in sorted(reserve_dir.iterdir()):
        if not cat_dir.is_dir():
            continue
        manifest_path = cat_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        m = json.load(manifest_path.open())
        for spr in m["sprites"]:
            pid = spr["pid"]
            png_path = cat_dir / spr["filename"]
            if not png_path.exists():
                continue
            try:
                b64 = png_to_b64(png_path)
            except Exception:
                continue
            pool[pid] = {
                "pid": pid,
                "cat": cat_dir.name,
                "img_b64": b64,
                "sheet": spr.get("sheet"),
                "src_label": spr.get("src_label"),
                "status": "reserve",
                "marked": spr.get("marked"),
            }
            n += 1
    return n


# ============================================================================
# Index PNG files by pid for fast lookup
# ============================================================================

def index_in_game_pngs(in_game_dir):
    """Walk <in_game_dir>/by_category/<cat>/<pid>_*.png and build pid → path."""
    by_pid = {}
    by_cat_dir = Path(in_game_dir) / "by_category"
    if not by_cat_dir.exists():
        return by_pid
    pid_pattern = re.compile(r"^([A-Z]+\d+)_")
    for cat_dir in by_cat_dir.iterdir():
        if not cat_dir.is_dir():
            continue
        for png in cat_dir.glob("*.png"):
            m = pid_pattern.match(png.name)
            if m:
                by_pid[m.group(1)] = png
    return by_pid


# ============================================================================
# Main
# ============================================================================

NAMED_CATS = ["weapons", "armors", "accessories", "bug_armors", "foods", "ingredients",
              "lanterns", "monsters", "runes", "shards", "towels", "treasures", "trophies"]
GENERIC_CATS = ["characters", "potions", "scrolls", "spells"]


def main():
    ap = argparse.ArgumentParser(description="Promote sprites from package into canonical pool")
    ap.add_argument("--pool", default="canonical_pool_full.pkl")
    ap.add_argument("--package", default=".",
                    help="Path to repo bundle root (containing code/, source_sheets/, libraries/)")
    ap.add_argument("--in-game-dir", default=None,
                    help="Path to unpacked in_game/ assets (default: <package>/in_game OR assets/sprites/in_game)")
    ap.add_argument("--reserve-dir", default=None,
                    help="Path to unpacked reserve/ assets (default: <package>/reserve OR assets/sprites/reserve)")
    ap.add_argument("--include-reserve", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--categories", nargs="+",
                    help="Only promote these categories (default: all)")
    args = ap.parse_args()

    pool_path = Path(args.pool)
    package_dir = Path(args.package)

    # Resolve in_game / reserve dirs. Try, in order:
    #   1. Explicit CLI flag
    #   2. <package>/in_game (legacy combined-package layout)
    #   3. assets/sprites/in_game (split layout — assets bundle unpacked there)
    def resolve_assets_dir(cli_value, name):
        if cli_value:
            return Path(cli_value)
        primary = package_dir / name
        if primary.exists():
            return primary
        fallback = Path("assets/sprites") / name
        if fallback.exists():
            return fallback
        return primary  # nonexistent, will be reported

    in_game_dir = resolve_assets_dir(args.in_game_dir, "in_game")
    reserve_dir = resolve_assets_dir(args.reserve_dir, "reserve")

    # Load (or create empty) pool
    if pool_path.exists():
        print(f"Loading pool: {pool_path}")
        with open(pool_path, "rb") as f:
            pool = pickle.load(f)
        print(f"  pool entries: {len(pool)}")
    else:
        print(f"Creating new pool at {pool_path}")
        pool = {}

    initial_size = len(pool)
    pid_files = index_in_game_pngs(in_game_dir)
    print(f"In-game assets:  {in_game_dir}  ({len(pid_files)} PNGs)")
    if args.include_reserve:
        print(f"Reserve assets:  {reserve_dir}")

    cats_to_run = args.categories or (NAMED_CATS + GENERIC_CATS + ["rooms"])

    # Named
    for cat in [c for c in cats_to_run if c in NAMED_CATS]:
        n = promote_named_category(cat, package_dir, pool, pid_files)
        print(f"  named/{cat:14}  promoted {n}")

    # Generic
    for cat in [c for c in cats_to_run if c in GENERIC_CATS]:
        n = promote_generic_category(cat, package_dir, pool, pid_files)
        print(f"  generic/{cat:11}  promoted {n}")

    # Rooms
    if "rooms" in cats_to_run:
        n = promote_rooms(package_dir, pool)
        print(f"  rooms             promoted {n}")

    # Reserve
    if args.include_reserve:
        n = promote_reserve(reserve_dir, pool)
        print(f"  reserve (all)     promoted {n}")

    final_size = len(pool)
    print(f"\nPool: {initial_size} → {final_size} entries (Δ {final_size - initial_size:+d})")

    if args.dry_run:
        print("DRY RUN — pool not written.")
        return

    print(f"Writing pool back to {pool_path}")
    with open(pool_path, "wb") as f:
        pickle.dump(pool, f)
    print("Done.")


if __name__ == "__main__":
    main()
