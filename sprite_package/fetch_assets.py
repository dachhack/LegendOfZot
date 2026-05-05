"""
Verify the assets bundle is unpacked correctly.

Usage:
    python3 fetch_assets.py [--assets-dir DIR]

Checks for the unpacked assets bundle (in_game/, reserve/, picker/) and verifies
counts against the manifests. The default location is `assets/sprites/`,
adjacent to this repo's root.

This script does NOT download anything. The assets bundle is hosted separately
(GitHub Releases, S3, Google Drive, wherever the user put it) and must be
unpacked into the assets/sprites/ directory before running this verifier.

After unpacking, the structure should be:
    assets/sprites/
        in_game/                 (1283 PNGs across 18 categories)
        reserve/                 (3968 PNGs across 17 categories)
        picker/                  (room_picker.html + build script)

The verifier counts PNGs per category and compares to libraries/<cat>_library.json.
Mismatches print a warning but don't fail.
"""
import argparse
import json
import sys
from pathlib import Path


def count_pngs(p: Path) -> int:
    if not p.exists():
        return 0
    return sum(1 for _ in p.rglob("*.png"))


def main():
    ap = argparse.ArgumentParser(description="Verify unpacked assets bundle")
    ap.add_argument("--assets-dir", default="assets/sprites",
                    help="Where the assets bundle is unpacked (default: assets/sprites)")
    ap.add_argument("--repo-dir", default=".",
                    help="Path to the repo root containing libraries/ (default: .)")
    args = ap.parse_args()

    assets = Path(args.assets_dir).resolve()
    repo = Path(args.repo_dir).resolve()

    if not assets.exists():
        print(f"❌ assets dir not found: {assets}")
        print()
        print("Fetch the assets bundle from where it's hosted (GitHub Releases,")
        print("Google Drive, S3, wherever the project README points you), unzip")
        print(f"into: {assets}")
        sys.exit(1)

    print(f"Checking {assets}\n")

    # Top-level dirs we expect
    required = {
        "in_game": "in-game sprites (named + generic)",
        "reserve": "reserve sprites (kept but not in-game)",
    }
    optional = {
        "picker": "picker tool (future-rounds use)",
    }
    missing = []
    for d, desc in required.items():
        path = assets / d
        if path.exists():
            # in_game has both by_category/ and by_item/ which contain duplicate PNGs.
            # Count only by_category/ for the canonical sprite count.
            count_path = path / "by_category" if (path / "by_category").exists() else path
            n = count_pngs(count_path)
            print(f"✓ {d:9}  {n:5d} PNGs       — {desc}")
        else:
            print(f"❌ {d:9}  missing            — {desc}")
            missing.append(d)
    for d, desc in optional.items():
        path = assets / d
        if path.exists():
            files = list(path.rglob("*.html")) + list(path.rglob("*.py"))
            print(f"✓ {d:9}  {len(files)} files       — {desc}")
        else:
            print(f"  {d:9}  (skipped, optional) — {desc}")

    if missing:
        print()
        print(f"Missing required directories: {missing}")
        print("The assets bundle was not fully unpacked here.")
        sys.exit(1)

    # Detailed check: count per-category PNGs against library counts
    print()
    print("Per-category check (in_game vs libraries):")
    libraries_dir = repo / "libraries"
    if not libraries_dir.exists():
        print(f"  (libraries/ not found at {libraries_dir} — skipping per-category cross-check)")
    else:
        for lib_file in sorted(libraries_dir.glob("*_library.json")):
            cat = lib_file.stem.replace("_library", "")
            lib = json.loads(lib_file.read_text())
            chosen = len(lib.get("chosen", []))
            reserve = len(lib.get("reserve", []))

            # Count PNGs in by_category
            cat_dir = assets / "in_game" / "by_category" / cat
            in_game_count = count_pngs(cat_dir) if cat_dir.exists() else 0

            res_dir = assets / "reserve" / cat
            reserve_count = count_pngs(res_dir) if res_dir.exists() else 0

            in_game_status = "✓" if in_game_count == chosen else "⚠"
            reserve_status = "✓" if reserve_count == reserve else "⚠"
            print(f"  {cat:14}  in_game {in_game_status} {in_game_count:>4}/{chosen:>4}  reserve {reserve_status} {reserve_count:>5}/{reserve:>5}")

    print()
    print("Assets bundle looks unpacked and ready.")
    print("Next: run `python3 code/promote_all_sprites.py --include-reserve --pool canonical_pool_full.pkl --package . --in-game-dir assets/sprites/in_game --reserve-dir assets/sprites/reserve` to build the pool.")


if __name__ == "__main__":
    main()
