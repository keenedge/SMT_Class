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
outline = unary_union([outline, body])
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

# star on top of the tree
STAR_C = (64.0, 21.0)
tree_star = star(*STAR_C, 5.2, 2.2)
tree_star = tree_star.buffer(0.25, join_style=2).buffer(-0.25, join_style=1)
star_core = star(*STAR_C, 2.0, 0.9)  # dark inner star -> gothic outlined look
star_gold = tree_star.difference(star_core.buffer(0.0))

# cap finial in gold, with a dark gothic trefoil
cap_gold = cap.intersection(outline).buffer(-0.7)
cap_gold = cap_gold.difference(circle(*HOLE_C, HOLE_R + 0.9))
cap_gold = cap_gold.difference(box(0, 12.2, 100, 100))
cap_dark = unary_union([ring(*HOLE_C, HOLE_R + 1.6, 0.35)])
cap_gold = cap_gold.difference(cap_dark)

# ---------------------------------------------------------------- tree (silkscreen) + gold baubles
TX = 64.0
tiers = [  # (apex y, base y, half width at base)
    (25.0, 37.5, 7.0),
    (30.5, 48.5, 10.5),
    (39.0, 60.5, 14.0),
    (48.5, 73.5, 17.5),
]
tree = []
garl = []
for k, (ya, yb, hw) in enumerate(tiers):
    n = 4 + k  # spikes along the hem
    pts = [(TX, ya), (TX + hw * 0.22, ya + (yb - ya) * 0.40), (TX + hw * 0.50, ya + (yb - ya) * 0.75), (TX + hw * 0.80, ya + (yb - ya) * 0.96), (TX + hw * 1.08, yb + 3.2)]
    for i in range(n, 0, -1):
        xr = TX - hw + 2 * hw * i / n
        xl = TX - hw + 2 * hw * (i - 1) / n
        xm = (xr + xl) / 2
        drop = lambda x: yb + 3.0 * ((x - TX) / hw) ** 2 - 0.6
        pts += [(xm, drop(xm) - 2.4), (xl, drop(xl) + 0.6)]
    pts[-1] = (TX - hw * 1.08, yb + 3.2)
    pts += [(TX - hw * 0.80, ya + (yb - ya) * 0.96), (TX - hw * 0.50, ya + (yb - ya) * 0.75), (TX - hw * 0.22, ya + (yb - ya) * 0.40)]
    tree.append(Polygon(pts).buffer(0))
    # sagging garland swag across the tier (dark line)
    yg = ya + (yb - ya) * 0.66
    xg = hw * 0.62
    garl.append(stroke([(TX - xg - 1.5, yg - 2.2), (TX - xg * 0.3, yg + 0.9), (TX + xg * 0.5, yg + 0.2), (TX + xg + 1.5, yg - 2.6)], 0.45))
tree_body = unary_union(tree)
trunk = box(TX - 2.2, 73.0, TX + 2.2, 82.5)
tree_sil = unary_union([tree_body, trunk]).difference(unary_union(garl))

baubles = [(61.6, 34.8, 0.9), (67.4, 32.0, 0.75), (58.0, 44.6, 1.1), (69.0, 46.6, 1.1),
           (55.0, 56.0, 1.25), (64.6, 57.6, 1.05), (73.0, 55.0, 1.2), (51.6, 69.2, 1.35), (61.6, 70.6, 1.2),
           (71.8, 68.8, 1.25), (66.6, 41.0, 0.7)]
bauble_gold = unary_union([circle(x, y, r) for x, y, r in baubles])

# ---------------------------------------------------------------- night sky, rays, frame, snow (silkscreen)
sil = []
RI = 41.6  # inner frame radius
sil.append(ring(CX, CY, RI, 0.7))
sil.append(ring(CX, CY, RI - 1.3, 0.25))
# gothic pointed-arch tracery: small lancet arches around the frame
for i in range(36):
    a = math.radians(i * 10)
    x, y = CX + (RI - 0.65) * math.cos(a), CY + (RI - 0.65) * math.sin(a)
    sil.append(circle(x, y, 0.45))
# rays of light from the star (long / short alternating)
rays = []
for i in range(28):
    ang = math.radians(i * 360 / 28 + 6)
    L = 13.0 if i % 2 == 0 else 8.0
    r0 = 7.4
    p0 = (STAR_C[0] + r0 * math.cos(ang), STAR_C[1] + r0 * math.sin(ang))
    p1 = (STAR_C[0] + (r0 + L) * math.cos(ang), STAR_C[1] + (r0 + L) * math.sin(ang))
    w0 = 0.55 if i % 2 == 0 else 0.4
    # tapered ray
    nx, ny = -math.sin(ang), math.cos(ang)
    rays.append(Polygon([(p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2), (p1[0] + nx * 0.1, p1[1] + ny * 0.1), (p1[0] - nx * 0.1, p1[1] - ny * 0.1), (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2)]))
rays = unary_union(rays).intersection(circle(CX, CY, RI - 2.4))
sil.append(ring(*STAR_C, 6.6, 0.3))
# twinkles + falling snow
for (x, y, r) in [(22, 30, 1.6), (33, 22, 1.1), (16, 46, 0.9), (84, 36, 1.3), (80, 52, 0.8), (44, 28, 0.8), (27, 38, 0.7), (85, 66, 0.9)]:
    sil.append(sparkle(x, y, r))
import random
random.seed(1225)
flakes = []
while len(flakes) < 70:
    x, y = random.uniform(9, 91), random.uniform(18, 84)
    if Point(x, y).distance(Point(CX, CY)) > RI - 3 or Point(x, y).distance(Point(*STAR_C)) < 7.5:
        continue
    flakes.append(circle(x, y, random.choice([0.2, 0.25, 0.32])))
sky = unary_union(flakes)
# moon: thin crescent, upper left
moon = circle(27.0, 30.0, 4.6).difference(circle(29.2, 28.6, 4.1))
sil.append(moon)
rays = rays.difference(moon.convex_hull.buffer(1.5))

# snow drift ground, with knock-out Fraktur text
ground_top = catmull([(4, 82.0), (14, 83.6), (28, 83.6), (44, 83.4), (58, 82.0), (72, 82.2), (86, 80.6), (96, 79.6)], closed=False)
snow = Polygon(ground_top + [(96, 100), (4, 100)]).intersection(circle(CX, CY, RI - 0.35))
text = text_geom("Silent Night", CX, 91.6, 4.4)
snow = snow.difference(text.buffer(0.15))
# long noir shadow of the dog, thrown down-left by the star's light
shadow = Polygon(catmull([(41.0, 83.6), (30.0, 84.2), (20.0, 85.0), (12.0, 85.2), (18.0, 85.9), (30.0, 85.7), (40.0, 85.2)])).buffer(0)
snow = snow.difference(shadow)

sil_all = unary_union(sil + [tree_sil, rays, sky, snow])

# ---------------------------------------------------------------- assemble layers
gold_open = unary_union([dog_gold, star_gold, bauble_gold, cap_gold])  # mask openings (what you see as gold)
copper = unary_union([dog.buffer(0.15), tree_star.buffer(0.15), bauble_gold.buffer(0.15), cap_gold.buffer(0.15), tag.buffer(0.15)])
# keep copper 0.5 mm off the board edge and hanging hole
board = outline.difference(hole)
copper = copper.intersection(board.buffer(-0.5))
gold_open = gold_open.intersection(copper.buffer(-0.1))
# silk must not land on gold, and keep 0.25 mm off the edge
sil_all = sil_all.difference(copper.buffer(0.25)).intersection(board.buffer(-0.3))
# drop silk specks too small to print (< 0.15 mm features)
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
write("01_Edge.Cuts.svg", "Edge.Cuts: ornament outline (90 mm disc + gothic cap) and 3.5 mm hanging hole, outlines only",
      "\n".join(f'<path d="{d_}" fill="none" stroke="#000" stroke-width="0.1"/>' for d_ in edge_lines))
write("02_F.Cu.svg", "F.Cu: copper under the gold art (ENIG). Filled shapes = copper. Grown 0.15 mm past the mask openings", fill_paths(copper))
write("03_F.Mask.svg", "F.Mask: filled shapes = solder mask OPENINGS = exposed ENIG gold", fill_paths(gold_open))
write("04_F.Silkscreen.svg", "F.Silkscreen: tree, star rays, moon, snow, frame and Silent Night text (white legend)", fill_paths(sil_all))

# ---------------------------------------------------------------- preview (colours)
MASK, GOLD, GOLD_HI, SILK, COV = "#121214", "#d9b14a", "#f0d27a", "#efeee8", "#2a2620"
def colored(g, c, extra=""):
    paths = []
    for p in polys(g.simplify(0.01)):
        dd = ring_d(p.exterior.coords) + "".join(" " + ring_d(i.coords) for i in p.interiors)
        paths.append(f'<path d="{dd}" fill="{c}" fill-rule="evenodd" {extra}/>')
    return "\n".join(paths)

board_d = ring_d(outline.exterior.coords) + " " + ring_d(hole.exterior.coords)
prev = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="-2 -2 104 104">
<defs>
 <radialGradient id="sheen" cx="0.42" cy="0.38" r="0.75"><stop offset="0" stop-color="#2b2b30"/><stop offset="1" stop-color="{MASK}"/></radialGradient>
 <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GOLD_HI}"/><stop offset="0.55" stop-color="{GOLD}"/><stop offset="1" stop-color="#a8822c"/></linearGradient>
 <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.2"/></filter>
</defs>
<rect x="-2" y="-2" width="104" height="104" fill="#e9e6df"/>
<path d="{board_d}" fill="url(#sheen)" fill-rule="evenodd" stroke="#000" stroke-width="0.25"/>
{colored(copper.difference(gold_open), COV)}
{colored(gold_open, "url(#gold)")}
<g opacity="0.35" filter="url(#glow)">{colored(star_gold, GOLD_HI)}</g>
{colored(sil_all, SILK)}
</svg>'''
with open(os.path.join(OUT, "preview.svg"), "w") as f:
    f.write(prev)
print("ok", len(no_holes(copper)), len(no_holes(gold_open)), len(no_holes(sil_all)))
