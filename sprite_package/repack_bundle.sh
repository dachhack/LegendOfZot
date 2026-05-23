#!/usr/bin/env bash
# Repack the locally-unpacked assets/sprites/ tree into the canonical
# wc_sprites_assets.zip layout (the one published as the
# sprite-assets-v1 GitHub Release).
#
# Run AFTER apply_picks.py has migrated PNGs from reserve/ to in_game/.
# The output zip is ready to drag-and-drop onto the release page,
# replacing the existing asset.
#
# Usage:
#   bash sprite_package/repack_bundle.sh [output.zip]
#
# Default output path is ./wc_sprites_assets.zip at the repo root.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ASSETS_DIR="${REPO_ROOT}/assets/sprites"
OUT="${1:-${REPO_ROOT}/wc_sprites_assets.zip}"

if [[ ! -d "${ASSETS_DIR}" ]]; then
  cat >&2 <<EOF
ERROR: assets bundle not found at ${ASSETS_DIR}
Unpack the sprite-assets-v1 release first:
  curl -L -o /tmp/wc.zip \\
      https://github.com/dachhack/LegendOfZot/releases/download/sprite-assets-v1/wc_sprites_assets.zip
  mkdir -p /tmp/unpack && unzip -q /tmp/wc.zip -d /tmp/unpack
  mkdir -p ${REPO_ROOT}/assets
  mv /tmp/unpack/wc_sprites_assets ${ASSETS_DIR}
EOF
  exit 2
fi

# The release zip uses wc_sprites_assets/ as the top-level prefix.
# Stage a symlink so we don't have to rename the live directory.
STAGING="$(mktemp -d)"
trap 'rm -rf "${STAGING}"' EXIT
ln -s "${ASSETS_DIR}" "${STAGING}/wc_sprites_assets"

echo "Packing ${ASSETS_DIR} -> ${OUT}..."
( cd "${STAGING}" && zip -qr --symlinks "${OUT}" wc_sprites_assets/ )

SIZE=$(du -h "${OUT}" | cut -f1)
FILES=$(unzip -l "${OUT}" | tail -1 | awk '{print $2}')
echo "Done: ${OUT} (${SIZE}, ${FILES} files)"
echo
echo "Next step: publish to the GitHub Release"
echo "  https://github.com/dachhack/LegendOfZot/releases/tag/sprite-assets-v1"
echo "  Edit release -> delete existing wc_sprites_assets.zip asset"
echo "  -> drag the new one in -> Update release"
