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

// ── Debris kit: little stories on the floor ──
var BONE = '#cfc4a8', BONE_EDGE = '#4a4136';

function propBone(ctx, x, y, len, ang, rng) {
  ctx.save();
  ctx.translate(x, y); ctx.rotate(ang);
  var w = Math.max(1.2, len * 0.16);
  ctx.strokeStyle = BONE_EDGE; ctx.lineWidth = w + 1.6; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(-len / 2, 0); ctx.lineTo(len / 2, 0); ctx.stroke();
  ctx.strokeStyle = BONE; ctx.lineWidth = w;
  ctx.beginPath(); ctx.moveTo(-len / 2, 0); ctx.lineTo(len / 2, 0); ctx.stroke();
  ctx.fillStyle = BONE;
  var k = w * 0.85;
  [[-len/2, -k*0.6], [-len/2, k*0.6], [len/2, -k*0.6], [len/2, k*0.6]].forEach(function(p) {
    ctx.beginPath(); ctx.arc(p[0], p[1], k, 0, 7); ctx.fill();
  });
  ctx.restore();
}

function propSkull(ctx, x, y, r, rng) {
  ctx.fillStyle = BONE_EDGE;
  ctx.beginPath(); ctx.arc(x, y, r + 1.2, 0, 7); ctx.fill();
  ctx.fillStyle = BONE;
  ctx.beginPath(); ctx.arc(x, y - r * 0.15, r, 0, 7); ctx.fill();
  ctx.fillRect(x - r * 0.55, y + r * 0.3, r * 1.1, r * 0.55);
  ctx.fillStyle = '#241d15';
  ctx.beginPath(); ctx.arc(x - r * 0.38, y - r * 0.15, r * 0.26, 0, 7); ctx.fill();
  ctx.beginPath(); ctx.arc(x + r * 0.38, y - r * 0.15, r * 0.26, 0, 7); ctx.fill();
}

function propCrack(ctx, x, y, s, rng) {
  ctx.strokeStyle = 'rgba(20,12,6,0.75)';
  ctx.lineWidth = Math.max(1, s * 0.022);
  ctx.beginPath();
  var a = rng() * Math.PI * 2, cx = x, cy = y;
  ctx.moveTo(cx, cy);
  for (var i = 0; i < 4; i++) {
    a += (rng() - 0.5) * 1.4;
    cx += Math.cos(a) * s * (0.08 + rng() * 0.08);
    cy += Math.sin(a) * s * (0.08 + rng() * 0.08);
    ctx.lineTo(cx, cy);
  }
  ctx.stroke();
}

function propWeb(ctx, px, py, s, corner, rng) {
  // corner: 0 TL, 1 TR, 2 BR, 3 BL
  var cx = (corner === 1 || corner === 2) ? px + s : px;
  var cy = (corner >= 2) ? py + s : py;
  var a0 = [0, Math.PI / 2, Math.PI, Math.PI * 1.5][corner];
  ctx.strokeStyle = 'rgba(215,215,225,0.34)';
  ctx.lineWidth = Math.max(0.7, s * 0.012);
  var R = s * (0.24 + rng() * 0.1);
  for (var ring = 1; ring <= 3; ring++) {
    ctx.beginPath(); ctx.arc(cx, cy, R * ring / 3, a0, a0 + Math.PI / 2); ctx.stroke();
  }
  for (var i = 0; i <= 3; i++) {
    var a = a0 + (i / 3) * Math.PI / 2;
    ctx.beginPath(); ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); ctx.stroke();
  }
}

function propMoss(ctx, x, y, s, rng) {
  for (var i = 0; i < 9; i++) {
    ctx.fillStyle = rng() < 0.5 ? 'rgba(76,150,60,0.55)' : 'rgba(105,180,80,0.45)';
    var r = s * (0.02 + rng() * 0.03);
    ctx.beginPath();
    ctx.arc(x + (rng() - 0.5) * s * 0.24, y + (rng() - 0.5) * s * 0.2, r, 0, 7);
    ctx.fill();
  }
}

function propShrooms(ctx, x, y, s, rng) {
  var n = 1 + (rng() * 3 | 0);
  for (var i = 0; i < n; i++) {
    var mx = x + (rng() - 0.5) * s * 0.2, my = y + (rng() - 0.5) * s * 0.18;
    var r = s * (0.035 + rng() * 0.03);
    ctx.fillStyle = '#d8cbb2';
    ctx.fillRect(mx - r * 0.22, my, r * 0.44, r * 1.1);
    ctx.fillStyle = rng() < 0.6 ? '#c14b32' : '#c9903a';
    ctx.beginPath(); ctx.arc(mx, my, r, Math.PI, 0); ctx.fill();
    ctx.fillStyle = 'rgba(255,240,220,0.8)';
    ctx.beginPath(); ctx.arc(mx - r * 0.3, my - r * 0.4, r * 0.16, 0, 7); ctx.fill();
  }
}

function propPebbles(ctx, x, y, s, rng) {
  for (var i = 0; i < 3 + (rng() * 3 | 0); i++) {
    rock(ctx, x + (rng() - 0.5) * s * 0.28, y + (rng() - 0.5) * s * 0.24,
         s * (0.02 + rng() * 0.025), rng);
  }
}

function propPuddle(ctx, x, y, s, rng) {
  ctx.fillStyle = 'rgba(30,50,80,0.55)';
  ctx.beginPath();
  ctx.ellipse(x, y, s * (0.1 + rng() * 0.06), s * (0.06 + rng() * 0.04), rng(), 0, 7);
  ctx.fill();
  ctx.strokeStyle = 'rgba(160,200,255,0.35)';
  ctx.lineWidth = Math.max(0.7, s * 0.012);
  ctx.beginPath();
  ctx.ellipse(x - s * 0.02, y - s * 0.015, s * 0.05, s * 0.025, rng(), Math.PI * 1.1, Math.PI * 1.8);
  ctx.stroke();
}

// Off-center anchor so the glyph zone (cell center) stays clean
function propSpot(px, py, s, rng) {
  var qx = rng() < 0.5 ? 0.30 : 0.70, qy = rng() < 0.5 ? 0.32 : 0.68;
  return [px + s * (qx + (rng() - 0.5) * 0.12), py + s * (qy + (rng() - 0.5) * 0.12)];
}

function drawDebris(ctx, px, py, s, rng, theme) {
  if (theme && theme !== 'M' && theme !== 'E') return;  // themed rooms carry their own story
  if (rng() > 0.42) return;                             // most floors stay bare
  var roll = rng(), p = propSpot(px, py, s, rng);
  if (roll < 0.26)      propPebbles(ctx, p[0], p[1], s, rng);
  else if (roll < 0.42) propCrack(ctx, p[0], p[1], s, rng);
  else if (roll < 0.56) propMoss(ctx, p[0], p[1], s, rng);
  else if (roll < 0.70) {
    propBone(ctx, p[0], p[1], s * (0.14 + rng() * 0.08), rng() * Math.PI, rng);
    if (rng() < 0.5) propBone(ctx, p[0] + s * 0.05, p[1] + s * 0.04,
                              s * (0.11 + rng() * 0.06), rng() * Math.PI, rng);
  }
  else if (roll < 0.80) {
    propSkull(ctx, p[0], p[1], s * (0.07 + rng() * 0.03), rng);
    if (rng() < 0.6) propBone(ctx, p[0] + s * 0.1, p[1] + s * 0.06,
                              s * 0.12, rng() * Math.PI, rng);
  }
  else if (roll < 0.88) propWeb(ctx, px, py, s, rng() * 4 | 0, rng);
  else if (roll < 0.95) propShrooms(ctx, p[0], p[1], s, rng);
  else                  propPuddle(ctx, p[0], p[1], s, rng);
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

// cells: [{x,y,cx,cy,k,m,t}] k: 0=fog 1=floor 2=wall; cx/cy = viewport col/row
window._cavernDraw = function(canvasId, cells, cols, rows, cellPx, seed) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;
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
