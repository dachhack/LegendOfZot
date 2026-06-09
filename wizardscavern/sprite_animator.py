"""
Procedural sprite animation engine (JavaScript).

Generates the JS that powers time-based sprite transforms in the WebView.
Each monster/player sprite animates from its single static image using
squash/stretch, sway, lunge, flash, and particle overlays -- no new frames.

The engine is injected once into the HTML shell (wrap_html) and individual
sprites register via onload_extra in their canvas render calls.
"""

# ── Per-monster "feel" tag ──────────────────────────────────────────────
# Drives amplitude/speed multipliers on the shared animation routines.
# Monsters not listed here default to 'default'.
MONSTER_FEEL = {
    # heavy -- slow, low bob (golems, bosses, large creatures)
    'Stone Golem': 'heavy', 'Iron Golem': 'heavy', 'Clay Golem': 'heavy',
    'Flesh Golem': 'heavy', 'Golem': 'heavy',
    'Dragon': 'heavy', 'Red Dragon': 'heavy', 'Black Dragon': 'heavy',
    'Blue Dragon': 'heavy', 'Green Dragon': 'heavy', 'White Dragon': 'heavy',
    'Ancient Dragon': 'heavy', 'Dragon Turtle': 'heavy',
    'Balor': 'heavy', 'Tarrasque': 'heavy', 'Beholder': 'heavy',
    'Purple Worm': 'heavy', 'Behir': 'heavy', 'Hydra': 'heavy',
    'Hill Giant': 'heavy', 'Fire Giant': 'heavy', 'Frost Giant': 'heavy',
    'Storm Giant': 'heavy', 'Cloud Giant': 'heavy', 'Stone Giant': 'heavy',
    'Ogre': 'heavy', 'Troll': 'heavy', 'Ettin': 'heavy',
    'Umber Hulk': 'heavy', 'Bulette': 'heavy',
    "Zot's Guardian": 'heavy',

    # skittery -- fast, jittery (bugs, imps, small creatures)
    'Giant Spider': 'skittery', 'Phase Spider': 'skittery',
    'Giant Ant': 'skittery', 'Giant Centipede': 'skittery',
    'Giant Scorpion': 'skittery', 'Giant Rat': 'skittery',
    'Giant Beetle': 'skittery', 'Carrion Crawler': 'skittery',
    'Rust Monster': 'skittery', 'Stirge': 'skittery',
    'Imp': 'skittery', 'Quasit': 'skittery', 'Mephit': 'skittery',
    'Goblin': 'skittery', 'Kobold': 'skittery',
    'Pseudodragon': 'skittery', 'Pixie': 'skittery',

    # floaty -- slow hover, no foot-plant (ghosts, flying, ethereal)
    'Ghost': 'floaty', 'Specter': 'floaty', 'Wraith': 'floaty',
    'Shadow': 'floaty', 'Banshee': 'floaty', 'Phantom': 'floaty',
    'Will-o-Wisp': 'floaty', 'Air Elemental': 'floaty',
    'Fire Elemental': 'floaty', 'Water Elemental': 'floaty',
    'Djinni': 'floaty', 'Efreeti': 'floaty',
    'Beholder': 'floaty',
}

# ── Per-spell glow config ───────────────────────────────────────────────
SPELL_GLOW = {
    'fire':   '#ff7a3a',
    'frost':  '#5af0ff',
    'poison': '#44ff44',
    'arcane': '#b46aff',
    'holy':   '#ffffa0',
    'necrotic': '#88ff88',
}


def get_monster_feel(monster_name):
    """Return the feel tag for a monster (used by Python-side config)."""
    stripped = monster_name.strip().lstrip('~').strip()
    parts = stripped.split()
    for length in range(len(parts), 0, -1):
        tail = ' '.join(w.title() for w in parts[-length:])
        if tail in MONSTER_FEEL:
            return MONSTER_FEEL[tail]
    return 'default'


def generate_animator_js():
    """Return the full JS animation engine to embed in the HTML shell."""
    return _ANIMATOR_JS


def generate_register_js(canvas_id, feel='default'):
    """Return JS to register a canvas with the animator after its image loads."""
    return (
        f"if(window._sprAnim){{window._sprAnim.register('{canvas_id}',img,'{feel}');}}"
    )


_ANIMATOR_JS = r"""
// ═══════════════════════════════════════════════════════════════════════
// SpriteAnimator — procedural animation from static sprites
// ═══════════════════════════════════════════════════════════════════════
(function() {
"use strict";

// ── Easing ──
function easeInOutQuad(t) {
    return t < 0.5 ? 2*t*t : 1 - (-2*t+2)*(-2*t+2)/2;
}

// ── Feel multipliers ──
var FEEL = {
    'default':  { amp: 1.0, spd: 1.0, hover: false },
    'heavy':    { amp: 0.6, spd: 0.7, hover: false },
    'skittery': { amp: 1.3, spd: 1.6, hover: false },
    'floaty':   { amp: 1.0, spd: 0.8, hover: true  }
};

// ── Behaviors ──
var BH_IDLE = 0, BH_WALK = 1, BH_ATTACK = 2, BH_HIT = 3,
    BH_DEATH = 4, BH_CAST = 5;

// ── Particle ──
function Particle(x, y, vx, vy, life, color, size) {
    this.x = x; this.y = y; this.vx = vx; this.vy = vy;
    this.life = life; this.maxLife = life;
    this.color = color; this.size = size || 2;
}

// ── Sprite entry ──
function SpriteEntry(canvasId, img, feel) {
    this.canvasId = canvasId;
    this.img = img;
    this.feel = FEEL[feel] || FEEL['default'];
    this.behavior = BH_IDLE;
    this.prevBehavior = BH_IDLE;
    this.t = 0;
    this.actionStart = 0;
    this.actionDur = 0;
    this.alive = true;
    this.deathHold = false;
    this.particles = [];
    this.glowColor = null;
    this.castBurstDone = false;
    // Cached tint canvas (same size as sprite)
    this._tintCanvas = null;
    this._tintColor = null;
}

SpriteEntry.prototype.startAction = function(bh, t, dur, opts) {
    if (this.deathHold && bh !== BH_IDLE) return;
    this.prevBehavior = this.behavior;
    this.behavior = bh;
    this.actionStart = t;
    this.actionDur = dur;
    this.castBurstDone = false;
    if (opts && opts.glowColor) this.glowColor = opts.glowColor;
    if (bh === BH_DEATH) this.deathHold = false;
};

SpriteEntry.prototype.getTintCanvas = function(color) {
    var w = this.img.naturalWidth || this.img.width;
    var h = this.img.naturalHeight || this.img.height;
    if (!w || !h) return null;
    if (this._tintCanvas && this._tintColor === color) return this._tintCanvas;
    var tc = document.createElement('canvas');
    tc.width = w; tc.height = h;
    var tctx = tc.getContext('2d');
    tctx.drawImage(this.img, 0, 0);
    tctx.globalCompositeOperation = 'source-in';
    tctx.fillStyle = color;
    tctx.fillRect(0, 0, w, h);
    this._tintCanvas = tc;
    this._tintColor = color;
    return tc;
};

// ── Animator singleton ──
function SpriteAnimator() {
    this.sprites = {};
    this._raf = null;
    this._startTime = null;
    this._running = false;
}

SpriteAnimator.prototype.register = function(canvasId, img, feel) {
    var entry = new SpriteEntry(canvasId, img, feel);
    this.sprites[canvasId] = entry;
    if (!this._running) this._start();
    return entry;
};

SpriteAnimator.prototype.cleanup = function() {
    var keys = Object.keys(this.sprites);
    for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        var el = document.getElementById(k);
        if (!el) {
            delete this.sprites[k];
        }
    }
};

SpriteAnimator.prototype.trigger = function(canvasId, behavior, opts) {
    var s = this.sprites[canvasId];
    if (!s) return;
    var t = this._now();
    var dur;
    switch (behavior) {
        case BH_ATTACK: dur = 0.55; break;
        case BH_HIT:    dur = 0.45; break;
        case BH_DEATH:  dur = 1.0;  break;
        case BH_CAST:   dur = 1.05; break;
        default:        dur = 0;    break;
    }
    s.startAction(behavior, t, dur, opts);
};

SpriteAnimator.prototype.setLoop = function(canvasId, behavior) {
    var s = this.sprites[canvasId];
    if (!s || s.deathHold) return;
    s.behavior = behavior;
    s.prevBehavior = behavior;
};

SpriteAnimator.prototype._now = function() {
    if (this._startTime === null) return 0;
    return (performance.now() - this._startTime) / 1000;
};

SpriteAnimator.prototype._start = function() {
    this._running = true;
    this._startTime = performance.now();
    var self = this;
    function loop() {
        self._raf = requestAnimationFrame(loop);
        self._tick();
    }
    loop();
};

SpriteAnimator.prototype._tick = function() {
    var t = this._now();
    var keys = Object.keys(this.sprites);
    var anyAlive = false;
    for (var i = 0; i < keys.length; i++) {
        var s = this.sprites[keys[i]];
        var canvas = document.getElementById(s.canvasId);
        if (!canvas) { delete this.sprites[keys[i]]; continue; }
        anyAlive = true;
        this._drawSprite(s, canvas, t);
    }
    if (!anyAlive) {
        cancelAnimationFrame(this._raf);
        this._running = false;
    }
};

SpriteAnimator.prototype._drawSprite = function(s, canvas, t) {
    var ctx = canvas.getContext('2d');
    var W = canvas.width, H = canvas.height;
    var iw = s.img.naturalWidth || s.img.width;
    var ih = s.img.naturalHeight || s.img.height;
    if (!iw || !ih) return;

    var scaleX = W / iw, scaleY = H / ih;
    var anchorX = iw / 2, anchorY = ih;

    // Compute transform params
    var offsetX = 0, offsetY = 0, rot = 0, sx = 1, sy = 1, alpha = 1;
    var tintAlpha = 0, tintColor = '#ffffff';
    var amp = s.feel.amp, spd = s.feel.spd;

    var bh = s.behavior;
    var isOneShot = (bh >= BH_ATTACK);

    if (isOneShot && s.actionDur > 0) {
        var elapsed = t - s.actionStart;
        var p = Math.min(elapsed / s.actionDur, 1.0);
        if (p >= 1.0 && bh !== BH_DEATH) {
            // One-shot finished, return to previous loop
            s.behavior = s.prevBehavior;
            s.deathHold = false;
            bh = s.behavior;
            isOneShot = false;
        } else if (p >= 1.0 && bh === BH_DEATH) {
            s.deathHold = true;
        }

        if (isOneShot) {
            switch (bh) {
                case BH_ATTACK:
                    if (p < 0.25) {
                        var k = easeInOutQuad(p / 0.25);
                        offsetX = -6 * k * amp;
                        sy = 1 - 0.14 * k * amp;
                        sx = 1 + 0.14 * k * amp;
                    } else if (p < 0.5) {
                        var k = easeInOutQuad((p - 0.25) / 0.25);
                        offsetX = (-6 + 24 * k) * amp;
                        sy = 1 + 0.18 * k * amp;
                        sx = 1 - 0.18 * k * amp;
                    } else {
                        var k = easeInOutQuad((p - 0.5) / 0.5);
                        offsetX = 18 * (1 - k) * amp;
                    }
                    break;

                case BH_HIT:
                    offsetX = Math.sin(p * 55) * 5 * (1 - p) * amp;
                    sy = 1 - 0.12 * (1 - p) * amp;
                    sx = 2 - sy;
                    tintAlpha = Math.max(0, 1 - p / 0.4);
                    tintColor = '#ffffff';
                    break;

                case BH_DEATH:
                    var ep = easeInOutQuad(p);
                    rot = ep * 1.45;
                    offsetY = ep * 6 * amp;
                    alpha = 1 - ep * 0.82;
                    sy = 1 - ep * 0.1;
                    sx = 1;
                    break;

                case BH_CAST:
                    var gc = s.glowColor || '#b46aff';
                    tintColor = gc;
                    if (p < 0.55) {
                        var k = easeInOutQuad(p / 0.55);
                        sy = 1 - 0.08 * k * amp;
                        sx = 2 - sy;
                        offsetX = Math.sin(t * 42) * 1.2 * k * amp;
                        offsetY = 2 * k * amp;
                        tintAlpha = 0.55 * k * (0.7 + 0.3 * Math.sin(t * 16));
                        // Spiral-in particles
                        if (Math.random() < 0.3 * k) {
                            var angle = Math.random() * Math.PI * 2;
                            var r = 44 + Math.random() * 22;
                            var bodyCenter = -ih * 0.45;
                            s.particles.push(new Particle(
                                anchorX + Math.cos(angle) * r,
                                anchorY + bodyCenter + Math.sin(angle) * r,
                                -Math.cos(angle) * (38 + Math.random() * 26),
                                -Math.sin(angle) * (38 + Math.random() * 26),
                                0.5 + Math.random() * 0.3,
                                gc, 2
                            ));
                        }
                    } else if (p < 0.72) {
                        var k = easeInOutQuad((p - 0.55) / 0.17);
                        sy = 1 + 0.16 * k * amp;
                        sx = 2 - sy;
                        offsetY = -7 * k * amp;
                        tintAlpha = 0.9 * (0.7 + 0.3 * Math.sin(t * 16));
                        // Burst particles (once)
                        if (!s.castBurstDone) {
                            s.castBurstDone = true;
                            var bodyCenter = -ih * 0.45;
                            for (var j = 0; j < 20; j++) {
                                var angle = (j / 20) * Math.PI * 2;
                                var vel = 88 + Math.random() * 46;
                                s.particles.push(new Particle(
                                    anchorX, anchorY + bodyCenter,
                                    Math.cos(angle) * vel,
                                    Math.sin(angle) * vel,
                                    0.4 + Math.random() * 0.3,
                                    gc, 3
                                ));
                            }
                        }
                    } else {
                        var k = easeInOutQuad((p - 0.72) / 0.28);
                        // Settle back to idle
                        sy = 1 + 0.16 * (1 - k) * amp;
                        sx = 2 - sy;
                        offsetY = -7 * (1 - k) * amp;
                        tintAlpha = 0.9 * (1 - k);
                    }
                    break;
            }
        }
    }

    // Loop behaviors
    if (!isOneShot) {
        var st = t * spd;
        switch (bh) {
            case BH_IDLE:
                var breathe = Math.sin(st * 2.2);
                sy = 1 + 0.045 * breathe * amp;
                sx = 1 - 0.045 * breathe * amp;
                offsetY = -1.5 * breathe * amp;
                // Floaty hover
                if (s.feel.hover) {
                    offsetY += Math.sin(st * 1.1) * 3;
                }
                break;
            case BH_WALK:
                var hop = Math.abs(Math.sin(st * 7));
                offsetY = -7 * hop * amp;
                rot = 0.07 * Math.sin(st * 7) * amp;
                sy = 1 + (hop - 0.5) * 0.08 * amp;
                sx = 2 - sy;
                if (s.feel.hover) {
                    offsetY += Math.sin(st * 1.1) * 3;
                }
                break;
        }
    }

    // ── Update particles ──
    var dt = 1 / 60; // approximate
    for (var pi = s.particles.length - 1; pi >= 0; pi--) {
        var part = s.particles[pi];
        part.x += part.vx * dt;
        part.y += part.vy * dt;
        part.life -= dt;
        if (part.life <= 0) {
            s.particles.splice(pi, 1);
        }
    }

    // ── Draw ──
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.imageSmoothingEnabled = false;

    // Transform: translate to floor → pixel scale → offset → rotate → squash/stretch → anchor
    ctx.translate(W / 2, H);           // floor position (center-bottom of canvas)
    // offsetX/offsetY in sprite-space pixels, scale to canvas
    ctx.translate(offsetX * scaleX, offsetY * scaleY);
    ctx.rotate(rot);
    ctx.scale(sx, sy);
    ctx.translate(-anchorX * scaleX, -anchorY * scaleY);

    ctx.drawImage(s.img, 0, 0, iw, ih, 0, 0, W, H);

    // ── Tint overlay (additive) ──
    if (tintAlpha > 0.01) {
        var tc = s.getTintCanvas(tintColor);
        if (tc) {
            ctx.globalCompositeOperation = 'lighter';
            ctx.globalAlpha = tintAlpha * alpha;
            ctx.drawImage(tc, 0, 0, iw, ih, 0, 0, W, H);
        }
    }

    ctx.restore();

    // ── Particles (world-space, additive) ──
    if (s.particles.length > 0) {
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        for (var pi = 0; pi < s.particles.length; pi++) {
            var part = s.particles[pi];
            var pa = part.life / part.maxLife;
            ctx.globalAlpha = pa * 0.8;
            ctx.fillStyle = part.color;
            var px = part.x * scaleX;
            var py = (part.y) * scaleY + H; // anchor-relative to canvas
            ctx.fillRect(px - part.size/2, py - part.size/2, part.size, part.size);
        }
        ctx.restore();
    }
};

// ── Global instance ──
window._sprAnim = new SpriteAnimator();

// Expose behavior constants for trigger calls
window._sprAnim.IDLE = BH_IDLE;
window._sprAnim.WALK = BH_WALK;
window._sprAnim.ATTACK = BH_ATTACK;
window._sprAnim.HIT = BH_HIT;
window._sprAnim.DEATH = BH_DEATH;
window._sprAnim.CAST = BH_CAST;

})();
"""
