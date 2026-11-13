#!/usr/bin/env python3
"""Labrador noir Christmas ornament: generates KiCad-importable layer SVGs + preview SVG.
1 SVG unit = 1 mm, origin = top-left of the 100 x 100 mm bounding box."""
import math, os, sys
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union, split
from shapely import affinity
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
FONT = os.path.join(os.path.dirname(__file__), "fonts", "frak.ttf")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- helpers
def catmull(pts, closed=True, n=12):
    """Smooth Catmull-Rom spline through pts."""
    P = list(pts)
    out = []
    N = len(P)
    rng = range(N) if closed else range(N - 1)
    for i in rng:
        p0 = P[(i - 1) % N] if closed or i > 0 else P[0]
        p1 = P[i]
        p2 = P[(i + 1) % N]
        p3 = P[(i + 2) % N] if closed or i + 2 < N else P[-1]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    if not closed:
        out.append(P[-1])
    return out

def smooth_poly(pts):
    return Polygon(catmull(pts)).buffer(0)

def stroke(pts, w, smooth=True, cap=1):
    line = LineString(catmull(pts, closed=False) if smooth and len(pts) > 2 else pts)
    return line.buffer(w / 2, cap_style=cap, join_style=1, quad_segs=8)

def circle(cx, cy, r):
    return Point(cx, cy).buffer(r, quad_segs=32)

def ring(cx, cy, r, w):
    return circle(cx, cy, r + w / 2).difference(circle(cx, cy, r - w / 2))

def star(cx, cy, ro, ri, n=5, rot=-90):
    pts = []
    for i in range(2 * n):
        r = ro if i % 2 == 0 else ri
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return Polygon(pts)

def sparkle(cx, cy, r, w=0.18):
    """4-point twinkle star"""
    return star(cx, cy, r, r * w * 1.6, n=4, rot=-90)

def polys(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    out = []
    for p in getattr(g, "geoms", []):
        out += polys(p)
    return out

def no_holes(g, minarea=1e-4):
    """Split polygons with holes into hole-free pieces (KiCad imports these cleanly)."""
    out = []
    stack = polys(g)
    while stack:
        p = stack.pop()
        if p.area < minarea:
            continue
        if not p.interiors:
            out.append(p)
            continue
        hx = Polygon(p.interiors[0]).representative_point().x
        b = p.bounds
        cutter = LineString([(hx, b[1] - 1), (hx, b[3] + 1)])
        pieces = split(p, cutter)
        stack += [q for q in polys(pieces)]
    return out

# ---------------------------------------------------------------- text (Fraktur outlines)
class FlatPen(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.contours, self.cur = [], []
    def _moveTo(self, p):
        self.cur = [p]
    def _lineTo(self, p):
        self.cur.append(p)
    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for k in range(1, 9):
            t = k / 8; u = 1 - t
            self.cur.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0], u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for k in range(1, 7):
            t = k / 6; u = 1 - t
            self.cur.append((u*u*p0[0]+2*u*t*p1[0]+t*t*p2[0], u*u*p0[1]+2*u*t*p1[1]+t*t*p2[1]))
    def _closePath(self):
        if len(self.cur) > 2:
            self.contours.append(self.cur)
        self.cur = []
    _endPath = _closePath

def text_geom(s, x, y_base, cap_h, center=True, track=0.0):
    f = TTFont(FONT)
    gs = f.getGlyphSet(); cmap = f.getBestCmap()
    upm = f["head"].unitsPerEm
    capref = f["OS/2"].sCapHeight or 0.7 * upm
    sc = cap_h / capref
    pen_x = 0; shapes = []
    for ch in s:
        gn = cmap.get(ord(ch))
        if gn is None:
            continue
        g = gs[gn]
        fp = FlatPen(gs); g.draw(fp)
        geo = Polygon()
        for c in fp.contours:
            pc = Polygon([(pen_x + px, -py) for px, py in c]).buffer(0)
            geo = geo.symmetric_difference(pc)
        shapes.append(geo)
        pen_x += g.width + track * upm
    t = unary_union(shapes)
    t = affinity.scale(t, sc, sc, origin=(0, 0))
    w = pen_x * sc - track * upm * sc
    dx = x - w / 2 if center else x
    return affinity.translate(t, dx, y_base)

# ---------------------------------------------------------------- board outline
CX, CY, R = 50.0, 55.0, 45.0
body = circle(CX, CY, R)
# gothic finial cap: pointed arch crown
cap_pts = [(41.5, 13.5), (41.5, 9.0), (43.0, 6.2), (46.0, 3.6), (50.0, 0.6), (54.0, 3.6), (57.0, 6.2), (58.5, 9.0), (58.5, 13.5)]
cap = Polygon(cap_pts).buffer(0.8, join_style=1).buffer(-0.8, join_style=1)
cap = cap.union(box(41.5, 9.0, 58.5, 13.5))
outline = unary_union([body, cap]).buffer(-1.0, join_style=1).buffer(1.0, join_style=1)  # fillet the junction
outline = unary_union([outline, body]).difference(box(0, 99.4, 100, 101))
HOLE_C, HOLE_R = (50.0, 7.2), 1.75  # 3.5 mm hanging hole
hole = circle(*HOLE_C, HOLE_R)

# ---------------------------------------------------------------- gold (ENIG) art: copper + mask opening
# Labrador, sitting, facing right, head tilted up toward the star
dog_pts = [
    (47.6, 40.4),  # nose tip (front of square muzzle)
    (45.6, 39.6), (43.2, 40.4), (41.0, 41.8),  # top of muzzle
    (39.4, 42.2),  # stop
    (37.6, 41.4), (34.8, 41.6), (32.2, 43.2), (30.4, 46.2),  # broad skull
    (29.6, 50.0), (29.0, 54.0),  # back of head / neck
    (27.4, 58.6), (24.6, 63.2), (21.2, 67.8),  # back
    (18.6, 72.6), (17.0, 77.8), (16.8, 82.4),  # rump
    (15.8, 85.8), (13.4, 87.0), (11.4, 88.0), (11.0, 89.0), (12.6, 89.6), (15.0, 89.6),  # tail on ground
    (20.0, 89.8), (28.0, 89.8),  # base, hind paw
    (33.4, 89.8), (34.6, 88.6), (35.6, 89.8),
    (41.0, 89.8), (44.6, 89.6), (45.0, 88.0), (43.6, 86.8), (41.2, 86.2),  # front paw
    (40.6, 80.0), (40.6, 72.0),  # front leg
    (41.6, 66.0), (41.4, 60.4),  # chest
    (40.4, 55.4), (40.6, 52.2),  # throat
    (41.6, 49.6), (43.2, 48.0), (45.0, 46.8),  # jowl / jaw
    (46.8, 45.2), (47.9, 43.4), (48.1, 41.8),  # chin + square muzzle front
]
dog = smooth_poly(dog_pts)

# dark (mask-covered) detail lines inside the dog
d = []
d.append(stroke([(34.0, 44.0), (32.0, 46.6), (30.8, 50.6), (30.8, 54.6), (32.4, 56.2), (34.0, 54.6), (35.2, 50.6), (35.6, 46.6)], 0.45))  # ear outline
d.append(circle(37.4, 45.4, 0.85))  # eye
d.append(stroke([(35.8, 44.2), (37.4, 43.7), (38.9, 44.3)], 0.3))  # brow
d.append(smooth_poly([(45.4, 39.6), (47.0, 39.4), (48.3, 40.3), (48.2, 41.9), (46.8, 42.2), (45.6, 41.4)]))  # nose
d.append(stroke([(47.0, 43.4), (45.6, 44.6), (43.6, 46.2), (42.4, 47.0)], 0.32))  # mouth
d.append(stroke([(43.8, 41.6), (42.2, 42.8)], 0.25, smooth=False))  # muzzle crease
d.append(stroke([(29.4, 56.0), (32.6, 57.0), (36.4, 56.8), (40.6, 55.6)], 0.95))  # collar
d.append(stroke([(20.6, 71.0), (25.2, 72.2), (28.6, 76.2), (29.4, 81.4), (28.0, 86.0), (30.4, 88.0), (34.0, 88.4)], 0.42))  # haunch + hind paw
d.append(stroke([(37.0, 70.0), (37.4, 78.0), (37.2, 86.8), (38.0, 89.6)], 0.38, smooth=True))  # front leg split
d.append(stroke([(41.2, 87.4), (41.6, 89.6)], 0.3, smooth=False))  # toes
d.append(stroke([(43.0, 87.0), (43.2, 89.4)], 0.3, smooth=False))
# engraved shadow hatching along the back (noir shading)
for i, (x0, y0) in enumerate([(24.5, 61.5), (22.8, 64.2), (21.0, 67.0), (19.4, 69.8), (18.1, 72.8), (17.4, 75.8), (17.0, 78.8), (16.9, 81.8)]):
    L = 2.6 if i % 2 == 0 else 1.8
    d.append(stroke([(x0 + 0.1, y0), (x0 + L, y0 + 0.9)], 0.3, smooth=False))
for (x0, y0) in [(30.4, 60.0), (29.0, 62.6), (31.6, 63.4)]:
    d.append(stroke([(x0, y0), (x0 + 1.6, y0 + 0.6)], 0.28, smooth=False))
d.append(ring(37.4, 58.4, 1.25, 0.32))  # tag rim
d.append(stroke([(37.4, 56.8), (37.4, 57.3)], 0.3, smooth=False))  # tag ring
dog_dark = unary_union(d)
tag = circle(37.4, 58.4, 0.95)  # gold collar tag
dog_gold = unary_union([dog.difference(dog_dark), tag.difference(circle(37.4, 58.4, 0.3))])
# fit the dog inside the frame: scale about the front paw and drop it onto the snow
def place(g):
    g = affinity.scale(g, 0.82, 0.82, origin=(45.0, 89.8))
    return affinity.translate(g, 3.0, -6.6)
dog, dog_gold, tag = place(dog), place(dog_gold), place(tag)
dog_dark = place(dog_dark)
dog_tag = tag

# ================================================================ NOIR SCENE
# One light source: the star on the tree. Everything else is silhouette and hard shadow.
RI = 42.2                     # inner frame radius
inner = circle(CX, CY, RI - 0.9)
STAR_C = (64.0, 20.6)
GROUND_Y = 83.2

# ---- star (gold) with a gold halo ring
tree_star = star(*STAR_C, 6.2, 3.3).buffer(0.2, join_style=2).buffer(-0.2, join_style=1)
star_gold = tree_star
# lens-flare cross: four long needle glints
for ang, L in [(0, 12.0), (90, 7.4), (180, 12.0), (270, 5.4), (45, 3.6), (135, 3.6), (225, 3.6), (315, 3.6)]:
    t = math.radians(ang)
    tip = (STAR_C[0] + L * math.cos(t), STAR_C[1] + L * math.sin(t))
    nx, ny = -math.sin(t) * 0.35, math.cos(t) * 0.35
    star_gold = star_gold.union(Polygon([(STAR_C[0] + nx, STAR_C[1] + ny), tip, (STAR_C[0] - nx, STAR_C[1] - ny)]))
star_gold = star_gold.intersection(circle(CX, CY, RI - 1.6)).difference(circle(*STAR_C, 2.8))

# ---- tree: black silhouette, outlined in silk, rim-lit from the star above
TX = 64.0
tiers = [(24.6, 37.5, 7.0), (30.0, 48.5, 10.5), (38.5, 60.5, 14.0), (48.0, 73.5, 17.5)]
tier_polys = []
for k, (ya, yb, hw) in enumerate(tiers):
    n = 4 + k
    pts = [(TX, ya), (TX + hw * 0.22, ya + (yb - ya) * 0.40), (TX + hw * 0.50, ya + (yb - ya) * 0.75),
           (TX + hw * 0.80, ya + (yb - ya) * 0.96), (TX + hw * 1.10, yb + 3.4)]
    for i in range(n, 0, -1):
        xr = TX - hw + 2 * hw * i / n
        xl = TX - hw + 2 * hw * (i - 1) / n
        xm = (xr + xl) / 2
        drop = lambda x: yb + 3.0 * ((x - TX) / hw) ** 2 - 0.6
        pts += [(xm, drop(xm) - 2.6), (xl, drop(xl) + 0.8)]
    pts[-1] = (TX - hw * 1.10, yb + 3.4)
    pts += [(TX - hw * 0.80, ya + (yb - ya) * 0.96), (TX - hw * 0.50, ya + (yb - ya) * 0.75), (TX - hw * 0.22, ya + (yb - ya) * 0.40)]
    tier_polys.append(Polygon(pts).buffer(0))
trunk = box(TX - 2.0, 72.0, TX + 2.0, GROUND_Y + 0.4)
tree = unary_union(tier_polys + [trunk])
# silk outline of the whole silhouette, plus a heavier rim where each tier's top catches the star light
tree_edge = tree.buffer(0.2).difference(tree.buffer(-0.2))
tree_rim = []
for p in tier_polys:
    lit = p.difference(affinity.translate(p, 0, 1.1))  # top-facing edges only
    tree_rim.append(lit)
tree_rim = unary_union(tree_rim).intersection(tree)
# a couple of baubles that catch the light: gold crescents (lit from above), the rest of the ball is in shadow
# ---- 10 LEDs (0805, top side): D1-D9 climb the tree as baubles, D10 sits in the heart of the star.
# The 4017 lights them one at a time, so the light climbs the tree and ends on the star.
LEDS = [(56.8, 68.6), (71.2, 68.6), (64.0, 64.4), (59.4, 57.4), (68.6, 57.4), (64.0, 51.4),
        (61.0, 44.6), (67.0, 44.6), (64.0, 34.2), STAR_C]
led_keep = unary_union([box(x - 2.4, y - 1.1, x + 2.4, y + 1.1) for x, y in LEDS])  # pads + via room: no silk / art copper inside
# a small gold hanger cap above each tree LED, so every LED reads as a bauble
bauble_gold = unary_union([unary_union([box(x - 0.7, y - 2.55, x + 0.7, y - 1.85), stroke([(x - 0.35, y - 2.55), (x, y - 3.2), (x + 0.35, y - 2.55)], 0.25, smooth=False)]) for x, y in LEDS[:9]])
bauble_cut = bauble_gold.buffer(0.4)
led_outline = unary_union([box(x - 1.0, y - 0.625, x + 1.0, y + 0.625).exterior.buffer(0.05) for x, y in LEDS])

# ---- light beams: hard-edged shafts falling from the star down-left onto the dog
beams = []
a0, a1 = 104.0, 166.0
a = a0
widths = [3.0, 1.0, 4.2, 0.7, 3.6, 1.4, 5.0, 0.8, 3.4, 1.2, 4.4, 0.9, 3.0, 1.6]
gaps = [0.9, 1.4, 0.7, 1.6, 0.8, 1.2, 0.7, 1.5, 0.9, 1.1, 0.8, 1.4, 1.0]
i = 0
while a < a1 and i < len(widths):
    w = widths[i]
    r0, r1 = 7.5, 90.0
    t0, t1 = math.radians(a), math.radians(a + w)
    S = STAR_C
    beams.append(Polygon([(S[0] + r0 * math.cos(t0), S[1] + r0 * math.sin(t0)), (S[0] + r1 * math.cos(t0), S[1] + r1 * math.sin(t0)),
                          (S[0] + r1 * math.cos(t1), S[1] + r1 * math.sin(t1)), (S[0] + r0 * math.cos(t1), S[1] + r0 * math.sin(t1))]))
    a += w + (gaps[i] if i < len(gaps) else 2)
    i += 1
beams = unary_union(beams).intersection(inner).intersection(box(0, 0, 100, GROUND_Y))
# fade: beams start thin near the star (taper by clipping with a circle-grown cone)
beams = beams.difference(circle(*STAR_C, 7.5))
# dust / snow motes in the light: knocked-out specks inside the beams only
import random
random.seed(1225)
motes = []
for _ in range(140):
    x, y = random.uniform(8, 60), random.uniform(28, GROUND_Y)
    motes.append(circle(x, y, random.choice([0.18, 0.22, 0.28])))
beams = beams.difference(unary_union(motes))

# ---- ground: black, except a pool of light on the snow where the beams land
pool = Polygon(catmull([(6, GROUND_Y + 0.2), (20, GROUND_Y - 0.4), (36, GROUND_Y - 0.6), (52, GROUND_Y + 0.2), (46, GROUND_Y + 3.6), (24, GROUND_Y + 4.4), (10, GROUND_Y + 3.0)])).buffer(0)
pool = pool.union(box(6, GROUND_Y - 0.2, 52, GROUND_Y + 0.6))
horizon = stroke([(9, GROUND_Y + 0.1), (30, GROUND_Y - 0.5), (52, GROUND_Y + 0.1), (72, GROUND_Y - 0.3), (92, GROUND_Y + 0.2)], 0.35)
lit_ground = unary_union([pool, beams.buffer(0)]).intersection(inner)
# the dog's long shadow, thrown away from the star across the lit snow
dog_base_l, dog_base_r = (16.0, GROUND_Y), (40.6, GROUND_Y)
shadow = Polygon([(18.0, GROUND_Y - 0.2), (41.0, GROUND_Y - 0.2), (30.0, GROUND_Y + 6.0), (4.0, GROUND_Y + 6.0)])
tree_shadow = Polygon([(TX - 2.4, GROUND_Y - 0.2), (TX + 2.4, GROUND_Y - 0.2), (TX - 4.0, GROUND_Y + 6), (TX - 12, GROUND_Y + 6)])

# ---- dog: black silhouette against the beams, gold rim light on the star-facing edges
dvec = (-0.58, 0.81)  # direction from the star toward the dog (light travel)
rim = dog.difference(affinity.translate(dog, dvec[0] * 3.4, dvec[1] * 3.4))
# engraved half-tone: hatched band falling off into shadow
band = dog.intersection(affinity.translate(dog, dvec[0] * 3.4, dvec[1] * 3.4)).difference(affinity.translate(dog, dvec[0] * 6.0, dvec[1] * 6.0))
hatch = []
for k in range(-120, 120):
    c = k * 0.95
    # lines perpendicular-ish to the light: run along (dvec rotated 90deg)
    px, py = -dvec[1], dvec[0]
    o = (30 + c * dvec[0], 60 + c * dvec[1])
    w = 0.42
    hatch.append(LineString([(o[0] - px * 80, o[1] - py * 80), (o[0] + px * 80, o[1] + py * 80)]).buffer(w / 2, cap_style=2))
hatch = unary_union(hatch)
head_zone = dog.intersection(Polygon([(33.0, 36.0), (52.0, 36.0), (52.0, 53.4), (33.0, 55.6)]))
face = head_zone.difference(affinity.translate(dog, dvec[0] * 7.0, dvec[1] * 7.0))
dog_lit = unary_union([rim, face, band.intersection(hatch)])
# only keep features facing the light (drop slivers along the bottom) and cut the dark details through the lit areas
dog_lit = dog_lit.intersection(box(0, 0, 100, GROUND_Y - 0.6)).difference(dog_dark)
eye_glint = circle(*affinity.translate(affinity.scale(Point(37.6, 45.0), 0.82, 0.82, origin=(45.0, 89.8)), 3.0, -6.6).coords[0], 0.32)
tag_glint = dog_tag.difference(affinity.translate(dog_tag, dvec[0] * 0.8, dvec[1] * 0.8))
dog_gold = unary_union([dog_lit, eye_glint, tag_glint]).buffer(-0.08).buffer(0.08)

# ---- frame: thin double ring with iron thorns, and a gothic arch over the cap
frame = [ring(CX, CY, RI, 0.55), ring(CX, CY, RI - 1.1, 0.2)]
for i in range(48):
    ang = math.radians(i * 7.5)
    L = 1.6 if i % 2 == 0 else 0.9
    x0, y0 = CX + (RI - 1.1) * math.cos(ang), CY + (RI - 1.1) * math.sin(ang)
    x1, y1 = CX + (RI - 1.1 - L) * math.cos(ang), CY + (RI - 1.1 - L) * math.sin(ang)
    nx, ny = -math.sin(ang) * 0.3, math.cos(ang) * 0.3
    frame.append(Polygon([(x0 + nx, y0 + ny), (x1, y1), (x0 - nx, y0 - ny)]))
frame = unary_union(frame)
# a few cold stars, far from the light
sky = unary_union([sparkle(18, 40, 0.9), sparkle(27, 26, 0.7), sparkle(85, 44, 0.8), sparkle(80, 30, 0.6), circle(36, 20, 0.25), circle(88, 58, 0.25), circle(12, 58, 0.25)])

# ---- cap: black, outlined lancet in silk, gold eyelet around the hanging hole
cap_in = cap.intersection(outline).buffer(-0.9).difference(box(0, 12.0, 100, 100))
cap_line = cap_in.buffer(0.15).difference(cap_in.buffer(-0.15))
eyelet = ring(*HOLE_C, HOLE_R + 1.2, 1.2)

# ---- text: Fraktur in silk on black, under the ground
text = text_geom("Silent Night", CX, 92.6, 4.0)

# ================================================================ assemble
board = outline.difference(hole)
gold_open = unary_union([dog_gold, star_gold, bauble_gold, eyelet])
copper = gold_open.buffer(0.15).intersection(board.buffer(-0.5))
copper = copper.difference(unary_union([box(x - 2.6, y - 1.3, x + 2.6, y + 1.3) for x, y in LEDS]))
copper = copper.difference(circle(*STAR_C, 2.8))
gold_open = gold_open.intersection(copper.buffer(-0.1))

light = unary_union([beams, lit_ground]).difference(tree.buffer(0.3)).difference(dog.buffer(0.35)).difference(shadow).difference(tree_shadow)
sil_all = unary_union([light, horizon.difference(dog.buffer(0.35)), tree_edge, tree_rim, frame, sky, cap_line, text])
sil_all = sil_all.difference(bauble_cut).difference(led_keep).difference(copper.buffer(0.25)).intersection(board.buffer(-0.3))
sil_all = sil_all.buffer(-0.075).buffer(0.075)
# ---------------------------------------------------------------- write SVGs
HDR = '<?xml version="1.0" encoding="UTF-8"?>\n<!-- {c} | 100 x 100 mm, origin top-left, 1 unit = 1 mm. Import into KiCad at X=0 Y=0, scale 1.0 -->\n<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100">\n'

def ring_d(coords):
    c = list(coords)
    return "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in c[:-1]) + " Z"

def fill_paths(g, color="#000"):
    out = []
    for p in no_holes(g.simplify(0.01)):
        out.append(f'<path d="{ring_d(p.exterior.coords)}" fill="{color}"/>')
    return "\n".join(out)

def write(name, comment, body):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(HDR.format(c=comment) + body + "\n</svg>\n")

edge_lines = [ring_d(outline.simplify(0.005).exterior.coords), ring_d(hole.exterior.coords)]
write("01_Edge.Cuts.svg", "Edge.Cuts: ornament outline (90 mm disc + gothic cap, flat at the bottom for USB-C) and 3.5 mm hanging hole, outlines only",
      "\n".join(f'<path d="{d_}" fill="none" stroke="#000" stroke-width="0.1"/>' for d_ in edge_lines))
write("02_F.Cu.svg", "F.Cu: copper under the gold art (ENIG). Filled shapes = copper. Grown 0.15 mm past the mask openings", fill_paths(copper))
write("03_F.Mask.svg", "F.Mask: filled shapes = solder mask OPENINGS = exposed ENIG gold", fill_paths(gold_open))
write("05_User.Drawings_LED_guide.svg", "User.Drawings: 10 LED positions (0805 body outlines). Place D1..D10 on F.Cu at these centres", fill_paths(led_outline.union(unary_union([LineString([(x-1.6,y),(x+1.6,y)]).buffer(0.05).union(LineString([(x,y-1.6),(x,y+1.6)]).buffer(0.05)) for x,y in LEDS]))))
with open(os.path.join(OUT, "_leds.txt"), "w") as f:
    f.write("# ref, x_mm, y_mm, rotation_deg (F.Cu, origin = board top-left)\n")
    for i, (x, y) in enumerate(LEDS):
        f.write(f"D{i+1}, {x:.2f}, {y:.2f}, 0\n")
write("04_F.Silkscreen.svg", "F.Silkscreen: light beams, lit snow (clear of the 10 LEDs), tree outline, frame and Silent Night text (white legend)", fill_paths(sil_all))

# ---------------------------------------------------------------- preview (colours)
MASK, GOLD, GOLD_HI, SILK, COV = "#121214", "#d9b14a", "#f0d27a", "#efeee8", "#2a2620"
def colored(g, c, extra=""):
    paths = []
    for p in polys(g.simplify(0.01)):
        dd = ring_d(p.exterior.coords) + "".join(" " + ring_d(i.coords) for i in p.interiors)
        paths.append(f'<path d="{dd}" fill="{c}" fill-rule="evenodd" {extra}/>')
    return "\n".join(paths)

board_d = ring_d(outline.exterior.coords) + " " + ring_d(hole.exterior.coords)
def led_svg(x, y, on):
    g = ""
    if on:
        g += f'<circle cx="{x}" cy="{y}" r="6" fill="url(#ledglow)"/>'
    g += f'<rect x="{x-1.45}" y="{y-0.7}" width="0.75" height="1.4" fill="#cfcfcf"/><rect x="{x+0.7}" y="{y-0.7}" width="0.75" height="1.4" fill="#cfcfcf"/>'
    g += f'<rect x="{x-0.7}" y="{y-0.62}" width="1.4" height="1.24" fill="{'#fff6d8' if on else '#e8e2c8'}" stroke="#9a9070" stroke-width="0.08"/>'
    return g
def preview(lit, name):
    body = "".join(led_svg(x, y, i in lit) for i, (x, y) in enumerate(LEDS))
    prev = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="-2 -2 104 104">
<defs>
 <radialGradient id="sheen" cx="0.42" cy="0.38" r="0.75"><stop offset="0" stop-color="#26262b"/><stop offset="1" stop-color="{MASK}"/></radialGradient>
 <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GOLD_HI}"/><stop offset="0.55" stop-color="{GOLD}"/><stop offset="1" stop-color="#a8822c"/></linearGradient>
 <radialGradient id="ledglow"><stop offset="0" stop-color="#fff3c4" stop-opacity="0.95"/><stop offset="0.35" stop-color="#ffd76a" stop-opacity="0.45"/><stop offset="1" stop-color="#ffcc40" stop-opacity="0"/></radialGradient>
 <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.2"/></filter>
</defs>
<rect x="-2" y="-2" width="104" height="104" fill="#e9e6df"/>
<path d="{board_d}" fill="url(#sheen)" fill-rule="evenodd" stroke="#000" stroke-width="0.25"/>
{colored(gold_open, "url(#gold)")}
<g opacity="0.35" filter="url(#glow)">{colored(star_gold, GOLD_HI)}</g>
{colored(sil_all, SILK)}
{body}
</svg>'''
    with open(os.path.join(OUT, name), "w") as f:
        f.write(prev)
preview([], "preview.svg")
preview([9], "preview_lit.svg")
print("ok", len(no_holes(copper)), len(no_holes(gold_open)), len(no_holes(sil_all)))
