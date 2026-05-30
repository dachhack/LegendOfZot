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

def generate_monster_sprite_html(monster_name, seed=None, size=64, loom=False, flourish=0, anim_token=0):
    """Render a square canvas for a monster (default 64x64).

    Looks up `monster_name` in the round-8 monster map (with name
    resolution for decorated boss names), picks a deterministic variant
    from the seed, and renders the pre-rendered webp from the canonical pool.

    `size` lets the combat screen scale the sprite up for tougher foes so
    the threat reads at a glance (see get_monster_threat_style in app.py).

    `loom=True` (elite tiers) additionally mounts a fixed-position copy of the
    sprite on a top layer (class "loom-overlay", z-index above the HUD) so the
    oversized creature paints OVER the stats bar instead of being clipped by
    #content-area -- the same fixed-overlay trick as the spell/damage effects.
    Being out of flow, it never moves the layout (the map stays put).  The
    overlay is cleaned up by updateGame() on every re-render.

    `flourish` (0-4) plays a tier-scaled entrance animation on the sprite (the
    overlay when looming, else the in-flow canvas): pop / rise / surge / SLAM,
    with a soft buzz at 3 and a dramatic vibration + screen flash at 4.  It
    fires once per fight -- `anim_token` (bumped server-side when a new monster
    appears) is compared to window.__combatAnimTok so re-renders stay static.

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
    try:
        SIZE = int(size)
    except (TypeError, ValueError):
        SIZE = 64
    SIZE = max(32, min(SIZE, 160))
    img_uri = "data:image/webp;base64," + img_b64
    # When looming, the same image is cloned into a fixed top-layer canvas
    # positioned over the in-flow canvas, so it escapes the #content-area clip
    # and paints over the HUD without disturbing layout.
    loom_js = ''
    if loom:
        loom_js = (
            'var r=c.getBoundingClientRect();'
            'var ov=document.createElement("canvas");'
            'ov.className="loom-overlay";'
            'ov.width=' + str(SIZE) + ';ov.height=' + str(SIZE) + ';'
            'ov.style.cssText="image-rendering:pixelated;position:fixed;pointer-events:none;'
            'z-index:1200;left:"+r.left+"px;top:"+r.top+"px;";'
            'var octx=ov.getContext("2d");octx.imageSmoothingEnabled=false;'
            'octx.drawImage(img,0,0,img.naturalWidth,img.naturalHeight,0,0,' + str(SIZE) + ',' + str(SIZE) + ');'
            'document.body.appendChild(ov);'
        )
    # Tier-scaled entrance flourish, fired once per fight (anim_token gate).
    flourish_js = ''
    if flourish and flourish > 0:
        _anim = {1: ('flourishPop', 320), 2: ('flourishRise', 380),
                 3: ('flourishSurge', 520), 4: ('flourishSlam', 720)}.get(flourish, ('flourishPop', 320))
        _target = 'ov' if loom else 'c'
        _vib = ''
        if flourish >= 4:
            _vib = 'if(navigator.vibrate){navigator.vibrate([0,55,45,95,45,170]);}'
        elif flourish == 3:
            _vib = 'if(navigator.vibrate){navigator.vibrate(45);}'
        _flash = ''
        if flourish >= 4:
            _flash = (
                'var _fl=document.createElement("div");'
                '_fl.style.cssText="position:fixed;inset:0;z-index:1190;pointer-events:none;'
                'background:radial-gradient(circle at 20% 32%,rgba(255,45,45,0.4),rgba(255,45,45,0) 62%);'
                'opacity:1;transition:opacity 640ms ease-out;";'
                'document.body.appendChild(_fl);'
                'requestAnimationFrame(function(){_fl.style.opacity="0";});'
                'setTimeout(function(){if(_fl&&_fl.parentNode)_fl.parentNode.removeChild(_fl);},700);'
            )
        flourish_js = (
            'var _ft=' + str(anim_token) + ';'
            'if(window.__combatAnimTok!==_ft){window.__combatAnimTok=_ft;'
            'var _tg=' + _target + ';'
            'if(_tg){_tg.style.transformOrigin="bottom center";'
            '_tg.style.animation="' + _anim[0] + ' ' + str(_anim[1]) + 'ms cubic-bezier(.2,.85,.25,1.15) both";}'
            + _vib + _flash +
            '}'
        )
    from .sprites.pool import render_sprite_canvas
    return render_sprite_canvas(
        safe_id, SIZE, img_uri, "display:block;margin:2px auto;",
        onload_extra=f"{loom_js}{flourish_js}", wrap_id=safe_id,
        wrap_style="position:relative;display:inline-block;overflow:visible;")


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
    from .sprites.pool import render_sprite_canvas
    return render_sprite_canvas(
        safe_id, SIZE, img_uri, "display:block;margin:2px auto;")


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
    from .sprites.pool import render_sprite_canvas
    return render_sprite_canvas(
        "player_sprite", SIZE, img_uri, "display:block;margin:4px auto;",
        wrap_id="player_sprite",
        wrap_style="position:relative;display:inline-block;overflow:visible;")
