"""Procedural cavern renderer (b493).

Replaces the b490-492 pre-painted tile sheet with an algorithm: the map
background is DRAWN into a <canvas> behind the tap grid, at device
resolution, seeded per cell -- infinite variety, crisp on any screen,
pixel-exact entrance matching, and ~5KB of JS instead of ~500KB of
embedded tile images.

Per render, generate_grid_html emits a small JSON spec (cell kind /
entrance mask / theme letter) plus a call to window._cavernDraw. The
inline script re-executes on every updateGame content swap, so the
canvas redraws in step with the DOM.

Drawing model per cell:
  wall  -- dense field of shaded rock blobs (replaces the old flat '#')
  floor -- warm speckled dirt, rock ring along CLOSED sides only, an
           entrance gap in the ring toward each open neighbour; themed
           rooms get a subtle color cast mixed into the floor
  fog   -- untouched (the container's dark background shows through)

Debris (b495): plain floors are decorated with hand-painted pixel-art
props (bones, rubble, webs, mushrooms...) preloaded from
wizardscavern/sprites/cavern_props.py -- see drawDebris below.
"""


def cavern_renderer_js():
    """The renderer, injected once into the HTML shell."""
    return _CAVERN_JS


_CAVERN_JS = r"""
// ═══ Procedural cavern renderer ═══
(function() {
"use strict";

function mulberry32(a) {
  return function() {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    var t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function cellRng(x, y, salt) {
  return mulberry32(((x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)) >>> 0);
}

var FLOOR_BASE = [[110,81,56],[104,73,47],[117,87,60]];
var ROCK_FILL = ['#5a5350','#615a55','#544e4b','#6a625c'];
var ROCK_EDGE = '#2b2724', ROCK_HI = 'rgba(200,190,175,0.30)';
// theme color casts, mixed into the floor base (r,g,b, strength 0-1)
var THEME = { C:[255,190,60,.20], P:[60,140,255,.26], A:[190,80,255,.20],
  L:[230,64,251,.13], T:[140,140,190,.18], G:[70,220,90,.20],
  W:[255,120,30,.18], N:[200,150,255,.15], V:[255,215,0,.15],
  U:[120,255,140,.12], D:[120,255,140,.12], O:[220,70,250,.15],
  B:[255,110,40,.18], F:[130,200,235,.15], Q:[60,255,60,.15],
  K:[230,90,90,.15], Z:[224,64,251,.18], M:[255,60,60,.10], E:[120,255,140,.12] };

function mix(base, cast) {
  if (!cast) return 'rgb(' + base[0] + ',' + base[1] + ',' + base[2] + ')';
  var s = cast[3];
  return 'rgb(' + Math.round(base[0]*(1-s)+cast[0]*s) + ',' +
                  Math.round(base[1]*(1-s)+cast[1]*s) + ',' +
                  Math.round(base[2]*(1-s)+cast[2]*s) + ')';
}

function rock(ctx, cx, cy, r, rng) {
  var n = 7 + (rng() * 3 | 0), pts = [];
  for (var i = 0; i < n; i++) {
    var a = (i / n) * Math.PI * 2;
    var rr = r * (0.75 + rng() * 0.5);
    pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr * 0.88]);
  }
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (i = 1; i < n; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
  ctx.fillStyle = ROCK_FILL[rng() * ROCK_FILL.length | 0];
  ctx.fill();
  ctx.strokeStyle = ROCK_EDGE;
  ctx.lineWidth = Math.max(0.8, r * 0.14);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(cx - r * 0.25, cy - r * 0.3, r * 0.45, Math.PI * 0.7, Math.PI * 1.9);
  ctx.strokeStyle = ROCK_HI;
  ctx.lineWidth = Math.max(0.8, r * 0.2);
  ctx.stroke();
}

function drawFloor(ctx, px, py, s, rng, theme) {
  var cast = THEME[theme] || null;
  ctx.fillStyle = mix(FLOOR_BASE[rng() * FLOOR_BASE.length | 0], cast);
  ctx.fillRect(px, py, s, s);
  var n = (s * s) / 46;
  for (var i = 0; i < n; i++) {
    ctx.fillStyle = rng() < 0.62 ? 'rgba(35,22,12,0.5)' : 'rgba(190,150,100,0.28)';
    var d = 1 + rng() * (s * 0.06);
    ctx.fillRect(px + rng() * s, py + rng() * s, d, d);
  }
}

// ── Debris: hand-painted pixel-art props stamped onto plain floors ──
// Images preloaded once at shell init by cavern_props_js()
// (wizardscavern/sprites/cavern_props.py) into window._cavernPropImgs.
var PROP_GROUPS = [
  ['rubble', 16], ['bones', 11], ['pottery', 10], ['mushrooms', 8],
  ['moss', 8], ['wood', 8], ['dust', 7], ['web', 6], ['skulls', 5],
  ['cloth', 4], ['chains', 4], ['stalag', 4], ['crystals', 3],
  ['goo', 3], ['skeleton', 3], ['bricks', 3]];
var PROP_TOTAL = 0;
for (var _pi = 0; _pi < PROP_GROUPS.length; _pi++) PROP_TOTAL += PROP_GROUPS[_pi][1];

function drawDebris(ctx, px, py, s, rng, theme) {
  if (theme && theme !== 'M' && theme !== 'E') return;  // themed rooms carry their own story
  if (rng() > 0.42) return;                             // most floors stay bare
  // Consume ALL randomness up front so the not-yet-loaded early return
  // below can't shift the sequence between first draw and redraw.
  var r = rng() * PROP_TOTAL, g = PROP_GROUPS[0][0];
  for (var i = 0; i < PROP_GROUPS.length; i++) {
    r -= PROP_GROUPS[i][1];
    if (r <= 0) { g = PROP_GROUPS[i][0]; break; }
  }
  var pick = rng(), sizeJ = rng(), jx = rng(), jy = rng(),
      qx = rng(), qy = rng(), flip = rng() < 0.5;
  var imgs = window._cavernPropImgs;
  if (!imgs || !imgs[g] || !imgs[g].length) return;
  var im = imgs[g][pick * imgs[g].length | 0];
  if (!im.complete || !im.naturalWidth) return;         // preloader redraws when ready
  var maxD = s * (0.50 + sizeJ * 0.16);
  var sc = Math.min(maxD / im.naturalWidth, maxD / im.naturalHeight);
  var w = im.naturalWidth * sc, h = im.naturalHeight * sc;
  var x, y;
  if (g === 'web') {
    // webs cling to a corner
    x = qx < 0.5 ? px + s * 0.02 : px + s - w - s * 0.02;
    y = qy < 0.5 ? py + s * 0.02 : py + s - h - s * 0.02;
  } else {
    // off-center so the glyph zone (cell center) stays clean
    var ax = (qx < 0.5 ? 0.30 : 0.70) + (jx - 0.5) * 0.14;
    var ay = (qy < 0.5 ? 0.32 : 0.68) + (jy - 0.5) * 0.14;
    x = Math.max(px + 1, Math.min(px + s - w - 1, px + s * ax - w / 2));
    y = Math.max(py + 1, Math.min(py + s - h - 1, py + s * ay - h / 2));
  }
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  if (flip && g !== 'web') {
    ctx.translate(x + w / 2, 0); ctx.scale(-1, 1); ctx.translate(-(x + w / 2), 0);
  }
  ctx.globalAlpha = 0.96;
  ctx.drawImage(im, x, y, w, h);
  ctx.restore();
}

function drawRing(ctx, px, py, s, mask, rng) {
  var r = s * 0.135;
  function row(x0, y0, x1, y1, open) {
    var steps = Math.max(4, Math.round(s / (r * 1.5)));
    for (var i = 0; i <= steps; i++) {
      var t = i / steps;
      if (open && t > 0.30 && t < 0.70) continue;
      var jx = (rng() - 0.5) * r * 0.8, jy = (rng() - 0.5) * r * 0.8;
      rock(ctx, x0 + (x1 - x0) * t + jx, y0 + (y1 - y0) * t + jy,
           r * (0.8 + rng() * 0.45), rng);
    }
  }
  row(px, py, px + s, py, !!(mask & 1));
  row(px, py + s, px + s, py + s, !!(mask & 4));
  row(px, py, px, py + s, !!(mask & 8));
  row(px + s, py, px + s, py + s, !!(mask & 2));
}

function drawWall(ctx, px, py, s, rng) {
  ctx.fillStyle = '#2e2a27';
  ctx.fillRect(px, py, s, s);
  var r = s * 0.16;
  for (var gy = 0; gy < 4; gy++)
    for (var gx = 0; gx < 4; gx++)
      rock(ctx, px + (gx + 0.5) * s / 4 + (rng() - 0.5) * r,
           py + (gy + 0.5) * s / 4 + (rng() - 0.5) * r,
           r * (0.75 + rng() * 0.4), rng);
  ctx.fillStyle = 'rgba(0,0,0,0.30)';
  ctx.fillRect(px, py, s, s);
}

// Replay the latest draw once all prop images finish decoding (first
// paint can beat the async Image loads; every draw is deterministic).
window._cavernRedrawAll = function() {
  var a = window._cavernLastDraw;
  if (a && document.getElementById(a[0])) {
    window._cavernDraw(a[0], a[1], a[2], a[3], a[4], a[5]);
  }
};

// cells: [{x,y,cx,cy,k,m,t}] k: 0=fog 1=floor 2=wall; cx/cy = viewport col/row
window._cavernDraw = function(canvasId, cells, cols, rows, cellPx, seed) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;
  window._cavernLastDraw = [canvasId, cells, cols, rows, cellPx, seed];
  var dpr = Math.min(3, window.devicePixelRatio || 1);
  canvas.width = Math.round(cols * cellPx * dpr);
  canvas.height = Math.round(rows * cellPx * dpr);
  canvas.style.width = (cols * cellPx) + 'px';
  canvas.style.height = (rows * cellPx) + 'px';
  var ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  var i, c;
  // pass 1: solid wall texture
  for (i = 0; i < cells.length; i++) {
    c = cells[i];
    if (c.k === 2) drawWall(ctx, c.cx * cellPx, c.cy * cellPx, cellPx, cellRng(c.x, c.y, seed));
  }
  // pass 2: floors + debris
  for (i = 0; i < cells.length; i++) {
    c = cells[i];
    if (c.k === 1) {
      drawFloor(ctx, c.cx * cellPx, c.cy * cellPx, cellPx, cellRng(c.x, c.y, seed + 1), c.t);
      drawDebris(ctx, c.cx * cellPx, c.cy * cellPx, cellPx, cellRng(c.x, c.y, seed + 3), c.t);
    }
  }
  // pass 3: rock rings (drawn after all floors so ring rocks may
  // overlap into neighbouring cells without being painted over)
  for (i = 0; i < cells.length; i++) {
    c = cells[i];
    if (c.k === 1) drawRing(ctx, c.cx * cellPx, c.cy * cellPx, cellPx, c.m, cellRng(c.x, c.y, seed + 2));
  }
  // single soft vignette over the whole map (depth without per-cell seams)
  var w = cols * cellPx, h = rows * cellPx;
  var g = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.35,
                                   w / 2, h / 2, Math.max(w, h) * 0.75);
  g.addColorStop(0, 'rgba(0,0,0,0)');
  g.addColorStop(1, 'rgba(0,0,0,0.28)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
};
})();
"""
