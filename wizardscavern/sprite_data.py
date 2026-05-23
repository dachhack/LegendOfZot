# sprite_data.py - Wizard's Cavern sprite rendering entry points.
#
# Thin wrapper module exposing three rendering helpers that the rest of
# the game imports:
#   - generate_monster_sprite_html(monster_name, seed=None)
#   - generate_room_sprite_html(room_type, variant=None, seed=None)
#   - generate_player_sprite_html(race, armor_state='none', seed=None,
#                                 sprite_pid=None)
#
# All sprite data lives in `wizardscavern.sprites` (per-category modules
# + the canonical pool at `wizardscavern/data/canonical_pool_full.pkl`).
# This file used to contain ~24 MB of base64 sheet data and inline maps;
# that was deleted once every render path migrated to the new pool.
#
# ASCII only - no Unicode, emojis, or special characters.


def _resolve_new_monster_key(monster_name, cat_map):
    """Match a (potentially decorated) monster name against the sprite map.

    Tries: as-is, with whitespace and '~' garbage trimmed, then a multi-word
    trailing-tail match in title / upper / raw casings (catches decorated
    boss names like " ELITE UNDEAD SPECTER" -> "Specter" and the
    leading-space legendaries like " TREASURE GOLEM"), then a per-word
    title-case match.

    Returns the matched key in `cat_map`, or None.
    """
    if monster_name in cat_map:
        return monster_name

    stripped = monster_name.strip().lstrip('~').strip()
    if stripped in cat_map:
        return stripped

    parts = stripped.split()
    if not parts:
        return None

    # Multi-word trailing-tail (longest first) — catches " UNDEAD DEATH
    # KNIGHT" -> "Death Knight" and the leading-space legendaries like
    # " TREASURE GOLEM".
    for length in range(len(parts), 0, -1):
        tail = parts[-length:]
        for variant in (
            ' '.join(w.title() for w in tail),
            ' '.join(w.upper() for w in tail),
            ' '.join(tail),
        ):
            if variant in cat_map:
                return variant

    for word in parts:
        word_title = word.title()
        if word_title in cat_map:
            return word_title

    return None


# ============================================================================
# MONSTER SPRITE
# ============================================================================

def generate_monster_sprite_html(monster_name, seed=None):
    """Render a 64x64 canvas for a monster.

    Looks up `monster_name` in the round-8 monster map (with name
    resolution for decorated boss names), picks a deterministic variant
    from the seed, and renders the pre-rendered webp from the canonical pool.

    Returns an HTML string, or '' if the monster has no sprite.
    """
    try:
        from .sprites import monsters as _msprites
        from .sprites import get_named_variant, get_image_b64
    except Exception:
        return ''

    cat_map = _msprites._MONSTERS_MAP
    base_name = _resolve_new_monster_key(monster_name, cat_map)
    if base_name is None:
        return ''

    variant = get_named_variant(cat_map, base_name, seed=(seed if seed is not None else base_name))
    if variant is None:
        return ''
    pid, _vi = variant
    img_b64 = get_image_b64(pid)
    if not img_b64:
        return ''

    safe_id = "ms_" + "".join(ch if ch.isalnum() else "_" for ch in monster_name)
    SIZE = 64
    img_uri = "data:image/webp;base64," + img_b64
    return (
        f'<div id="{safe_id}_wrap" style="position:relative;display:inline-block;overflow:visible;">'
        f'<canvas id="{safe_id}" width="{SIZE}" height="{SIZE}" '
        f'style="image-rendering:pixelated;image-rendering:crisp-edges;'
        f'display:block;margin:2px auto;"></canvas>'
        f'<script>(function(){{'
        f'var c=document.getElementById("{safe_id}");if(!c)return;'
        f'var ctx=c.getContext("2d");ctx.imageSmoothingEnabled=false;'
        f'var img=new Image();'
        f'img.onload=function(){{ctx.drawImage(img,0,0,img.naturalWidth,img.naturalHeight,0,0,{SIZE},{SIZE});}};'
        f'img.src="{img_uri}";'
        f'}})()</script>'
        f'</div>'
    )


# ============================================================================
# ROOM SPRITE
# ============================================================================

def generate_room_sprite_html(room_type, variant=None, seed=None):
    """Render a 48x48 canvas for a room type or special variant.

    `seed` (typically the room's (x, y, z)) selects which of the 3
    variants for that slot to show — same coords always render the same
    sprite, different rooms in the dungeon spread across the variants.

    Returns an HTML string, or '' if the room has no sprite (e.g. 'M'
    monster rooms render the monster sprite instead).
    """
    try:
        from .sprites.room_pool import get_room_pids, get_variant_pids
        from .sprites import get_image_b64
        from .sprites.pool import _stable_seed
    except Exception:
        return ''

    if variant:
        pids = get_variant_pids(variant)
    else:
        pids = get_room_pids(room_type)
    if not pids:
        return ''

    seed_key = seed if seed is not None else (room_type, variant)
    pid = pids[_stable_seed(seed_key) % len(pids)]
    img_b64 = get_image_b64(pid)
    if not img_b64:
        return ''

    safe_id = "rs_" + room_type + ("_" + variant if variant else "")
    SIZE = 48
    img_uri = "data:image/webp;base64," + img_b64
    return (
        f'<canvas id="{safe_id}" width="{SIZE}" height="{SIZE}" '
        f'style="image-rendering:pixelated;image-rendering:crisp-edges;'
        f'display:block;margin:2px auto;"></canvas>'
        f'<script>(function(){{'
        f'var c=document.getElementById("{safe_id}");if(!c)return;'
        f'var ctx=c.getContext("2d");ctx.imageSmoothingEnabled=false;'
        f'var img=new Image();'
        f'img.onload=function(){{ctx.drawImage(img,0,0,img.naturalWidth,img.naturalHeight,0,0,{SIZE},{SIZE});}};'
        f'img.src="{img_uri}";'
        f'}})()</script>'
    )


# ============================================================================
# PLAYER SPRITE
# ============================================================================

def generate_player_sprite_html(race, armor_state='none', seed=None, sprite_pid=None):
    """Render a 64x64 canvas for the player avatar.

    Precedence:
      1. `sprite_pid` — render that exact avatar (player picked it at
         character creation).
      2. `seed` — pick deterministically from the round-8 character pool
         (typically seed=(race, gender, character_name)).
      3. Neither — return ''.

    The `armor_state` argument is ignored; armor no longer changes the
    sprite (it used to in the legacy 16x16 sheet path).
    """
    try:
        from .sprites import characters as _csprites
        from .sprites import get_generic_variant, get_image_b64
    except Exception:
        return ''

    pid = sprite_pid
    if pid is None:
        if seed is None:
            return ''
        # Filter by race so the auto-picked avatar matches what the
        # in-game character-creation picker (app.py:5849) shows for
        # this race. Before this fix, the seed-based fallback drew
        # from the full _CHARACTERS_POOL (a dwarf could get an
        # elf-looking portrait, etc.) which broke the visual link
        # between the playtest report and what a player launching
        # this seed in the actual game would see.
        from .sprites.characters import get_race_pool
        pool = get_race_pool(race) if race else _csprites._CHARACTERS_POOL
        if not pool:
            return ''
        pid = get_generic_variant(pool, seed=seed)
    if not pid:
        return ''
    img_b64 = get_image_b64(pid)
    if not img_b64:
        return ''

    SIZE = 64
    img_uri = "data:image/webp;base64," + img_b64
    return (
        '<div id="player_sprite_wrap" style="position:relative;display:inline-block;overflow:visible;">'
        f'<canvas id="player_sprite" width="{SIZE}" height="{SIZE}"'
        ' style="image-rendering:pixelated;image-rendering:crisp-edges;'
        'display:block;margin:4px auto;"></canvas>'
        '<script>(function(){'
        'var c=document.getElementById("player_sprite");'
        'if(!c)return;'
        'var ctx=c.getContext("2d");ctx.imageSmoothingEnabled=false;'
        'var img=new Image();'
        f'img.onload=function(){{ctx.drawImage(img,0,0,img.naturalWidth,img.naturalHeight,0,0,{SIZE},{SIZE});}};'
        f'img.src="{img_uri}";'
        '})()'
        '</script>'
        '</div>'
    )
