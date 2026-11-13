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

def text_geom(s, x, y_base, cap_h, center=True, track=0.0, font=None):
    f = TTFont(font or FONT)
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

# ================================================================ TWO DOGS + TREE: the board IS the silhouette
S = 85.0 / 99.0               # the scene is drawn in a 100 mm design space, then scaled so the board fits 85 x 85 mm
dvec = (-0.58, 0.81)          # direction light travels (from the star, down-left)
BASE_Y = 89.8                 # where paws and trunk meet the ground strip

def place(g, sc, dx):
    g = affinity.scale(g, sc, sc, origin=(45.0, 89.8))
    return affinity.translate(g, dx, 0)

# black dog: bigger, behind and to the left.  yellow dog: in front, nearer the tree.
B = dict(sc=1.0, dx=-6.6)
Y = dict(sc=0.86, dx=7.0)
# ---- guide dog jackets (drawn once in the dog's own coordinates, then placed on both Labs)
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
jk_raw = Polygon([(27.0, 55.8), (13.0, 72.0), (16.5, 77.6), (27.5, 78.2), (36.0, 73.4), (38.6, 63.0), (34.0, 58.2)]).buffer(-2.5, join_style=1).buffer(2.5, join_style=1).intersection(dog)
strap_raw = unary_union([stroke([(36.8, 65.0), (42.4, 66.6)], 1.5, smooth=False), stroke([(31.0, 77.0), (33.6, 81.6), (37.4, 83.0)], 1.3)]).intersection(dog).difference(jk_raw)
def text_on_path(txt, line, cap_h, font, track=0.08):
    """Lay glyphs along a LineString baseline (centred), each rotated to the local tangent."""
    f = TTFont(font); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    upm = f["head"].unitsPerEm; sc = cap_h / (f["OS/2"].sCapHeight or 0.7 * upm)
    glyphs, total = [], 0.0
    for ch in txt:
        g = gs[cmap[ord(ch)]]
        fp = FlatPen(gs); g.draw(fp)
        geo = Polygon()
        for c in fp.contours:
            geo = geo.symmetric_difference(Polygon([(px * sc, -py * sc) for px, py in c]).buffer(0))
        w = g.width * sc
        glyphs.append((geo, w)); total += w + track * cap_h
    total -= track * cap_h
    pos = line.length - total - 1.4      # sit toward the shoulder end of the jacket
    out = []
    for geo, w in glyphs:
        mid = pos + w / 2
        p0, p1 = line.interpolate(mid - 0.3), line.interpolate(mid + 0.3)
        th = math.atan2(p1.y - p0.y, p1.x - p0.x)
        c, sn = math.cos(th), math.sin(th)
        pm = line.interpolate(mid)
        # glyph is centred on its advance, rotated to the tangent, then moved to the path point
        out.append(affinity.affine_transform(affinity.translate(geo, -w / 2, 0), [c, -sn, sn, c, pm.x, pm.y]))
        pos += w + track * cap_h
    return unary_union(out)
JK_WORD = os.environ.get("JK_WORD", "BCAGD")
_back = LineString(catmull([(16.6, 78.4), (18.6, 72.6), (21.2, 67.8), (24.6, 63.2), (27.6, 58.2)], closed=False))
_base = _back.offset_curve(5.4)
if not dog.contains(_base.interpolate(0.5, normalized=True)):
    _base = _back.offset_curve(-5.4)
if _base.coords[0][1] < _base.coords[-1][1]:
    _base = LineString(list(_base.coords)[::-1])     # read from the rump up toward the head
jk_text_raw = text_on_path(JK_WORD, _base, 3.0, SANS)
print("JACKET", [round(v,1) for v in jk_raw.bounds], "TEXT", [round(v,1) for v in jk_text_raw.bounds], "fits", jk_raw.buffer(-0.6).contains(jk_text_raw))
dog_dark = dog_dark.difference(jk_raw.buffer(0.3))
bdog, bdark = place(dog, **B), place(dog_dark, **B)
bjk, bjk_text, bstrap = place(jk_raw, **B), place(jk_text_raw, **B), place(strap_raw, **B)
yjk, yjk_text, ystrap = place(jk_raw, **Y), place(jk_text_raw, **Y), place(strap_raw, **Y)
ydog, ydark, ytag = place(dog, **Y), place(dog_dark, **Y), place(tag, **Y)

# ---- tree + star + hanging eyelet
TX = float(os.environ.get("TX", 62.45))
STAR_C = (TX, 13.6)
tiers = [(21.0, 35.5, 12.0), (27.5, 49.0, 17.5), (37.5, 63.0, 22.5), (49.5, 77.0, 27.0)]
tier_polys = []
for k, (ya, yb, hw) in enumerate(tiers):
    n = 5 + k
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
trunk = box(TX - 3.0, 74.0, TX + 3.0, BASE_Y + 1)
neck = box(TX - 2.6, STAR_C[1], TX + 2.6, 26.0)
star_board = star(*STAR_C, 7.0, 3.9)
HOLE_C, HOLE_R = (TX, 4.2), 1.5 / S   # 3 mm hanging hole at final size
eye_tab = circle(*HOLE_C, 3.6)
tree = unary_union(tier_polys + [trunk, neck])

# ---- ground strip that ties it all together (USB-C goes on its flat bottom edge)
ground = box(1.5, BASE_Y - 1.2, 98.5, 99.6).buffer(1.5, join_style=1).buffer(-1.5, join_style=1)
ground = box(1.5, BASE_Y - 1.2, 98.5, 99.6).buffer(-1.6, join_style=1).buffer(1.6, join_style=1)

# ---- small white dog (original scruffy mutt with a tied-on antler), sitting in front of the yellow dog
WX, WS = float(os.environ.get('WX', 49.5)), 1.0
def wl(pts):   # local (x right, y down, base at y=22) -> board
    return [(WX + x * WS, BASE_Y - (22 - y) * WS) for x, y in pts]
wbody = smooth_poly(wl([(13.6, 3.3), (11.6, 2.9), (9.8, 3.9), (8.8, 3.0), (7.8, 1.5), (7.0, 2.7), (5.8, 3.9), (5.1, 6.0),
                        (5.3, 8.6), (4.6, 11.2), (3.4, 14.2), (2.5, 17.2), (2.1, 20.2), (2.6, 22.0), (9.0, 22.0), (11.6, 22.0), (11.9, 20.9),
                        (10.4, 20.3), (9.7, 16.2), (9.6, 12.6), (10.0, 10.6), (9.5, 8.7), (9.8, 7.3), (11.3, 6.4), (13.0, 5.3), (14.1, 4.3)]))
wtail = stroke(wl([(2.6, 19.6), (1.2, 17.6), (0.6, 15.0), (1.3, 13.4)]), 1.0)
wantler = unary_union([stroke(wl([(7.2, 2.6), (6.6, -0.8), (6.9, -4.6)]), 0.8), stroke(wl([(6.7, -1.2), (4.6, -3.0)]), 0.7, smooth=False),
                       stroke(wl([(6.8, -2.8), (8.9, -4.4)]), 0.7, smooth=False), stroke(wl([(4.9, -2.7), (4.6, -4.4)]), 0.6, smooth=False)])
wdog = unary_union([wbody, wtail, wantler])
wdark = unary_union([
    stroke(wl([(6.9, 3.4), (5.9, 5.6), (5.5, 8.4), (6.2, 10.4), (7.2, 9.0), (7.5, 6.2), (7.6, 4.2)]), 0.3),   # long droopy ear
    circle(*wl([(9.5, 4.9)])[0], 0.42),                                                                    # eye
    circle(*wl([(13.6, 3.9)])[0], 0.62),                                                                   # nose
    stroke(wl([(13.0, 5.1), (11.6, 5.8)]), 0.25, smooth=False),                                            # mouth
    stroke(wl([(5.2, 8.9), (7.4, 9.9), (9.6, 9.0)]), 0.5),                                                 # collar
    stroke(wl([(6.4, 1.9), (7.9, 2.9)]), 0.3, smooth=False),                                               # string holding the antler
    stroke(wl([(4.0, 15.0), (6.4, 16.2), (7.2, 19.0), (6.6, 21.2), (8.6, 21.4)]), 0.3),                    # haunch
    stroke(wl([(8.4, 14.0), (8.5, 21.6)]), 0.28, smooth=False),                                            # front leg
])

# ---- wrapped present, bottom right: the CR2032 holder sits behind it on the back as the counterweight
PX0, PX1, PY0 = 68.5, 97.0, 71.0      # 24.5 x 24.5 mm at final size, room for an SMD CR2032 holder
BAT_C = ((PX0 + PX1) / 2, 86.0)
BT = PY0 + 0.8                      # top rim of the box
LID_ANG, LID_P = 15.0, (PX1 + 1.5, BT)   # lid is askew: hinged on the right corner, pushed up on the left by the puppy
def LROT(g):
    return affinity.rotate(g, LID_ANG, origin=LID_P)
BX, KY = 84.8, BT - 4.0 - 1.4       # bow knot (on the lid, before the lid is tilted)
def _loop(sg, k=0.8):
    return smooth_poly([(BX + sg * k * x, KY + k * y) for x, y in [(0.6, 0.2), (3.2, -4.4), (7.6, -5.0), (9.4, -2.2), (8.4, 1.0), (4.0, 1.2)]])
lid = LROT(box(PX0 - 1.5, BT - 4.0, PX1 + 1.5, BT))
bow_loops = LROT(unary_union([_loop(1), _loop(-1)]))
bow_knot = LROT(box(BX - 1.5, KY - 1.6, BX + 1.5, KY + 1.8).buffer(0.6, join_style=1))
bow = unary_union([bow_loops, bow_knot])
_lip = LROT(Point(PX0 - 1.5, BT)).coords[0]           # raised left corner of the lid
gap = Polygon([LID_P, _lip, (PX0, BT)])               # dark opening between the box and the lifted lid
# puppy tail poking out behind the lid, mid-wag
_tp = catmull([(94.6, BT - 2.0), (93.8, BT - 7.0), (94.2, BT - 11.6), (95.8, BT - 15.2), (96.6, BT - 17.2)], closed=False, n=8)
ptail = unary_union([Point(p).buffer(2.1 - 0.9 * i / (len(_tp) - 1)) for i, p in enumerate(_tp)])
# puppy peeking out from under the lifted lid: face in the opening, floppy ears, two paws hooked over the rim
HX, LID_T = 74.4, BT
HY = BT - 2.9
phead = unary_union([circle(HX, HY, 5.0),
                     smooth_poly([(HX - 3.0, HY - 4.2), (HX - 5.8, HY - 3.4), (HX - 6.6, HY + 0.6), (HX - 5.4, HY + 2.6), (HX - 3.8, HY + 0.4)]),
                     smooth_poly([(HX + 3.0, HY - 4.2), (HX + 5.8, HY - 3.4), (HX + 6.6, HY + 0.6), (HX + 5.4, HY + 2.6), (HX + 3.8, HY + 0.4)])])
phead = phead.intersection(box(0, 0, 100, BT + 0.6))
ppaws = unary_union([box(HX - 4.9, BT - 0.9, HX - 3.1, BT + 1.2).buffer(0.45, join_style=1), box(HX + 3.1, BT - 0.9, HX + 4.9, BT + 1.2).buffer(0.45, join_style=1)])
present = unary_union([box(PX0, BT, PX1, 99.6), gap, lid, bow, ptail, phead])

raw = unary_union([bdog, ydog, wdog, tree, star_board, eye_tab, ground, present])
# make it routable: inside corners get >= 1 mm radius, and slivers thinner than 1.6 mm are removed
outline = raw.buffer(1.0 / S, join_style=1).buffer(-1.0 / S, join_style=1)
outline = outline.buffer(-0.8 / S, join_style=1).buffer(0.8 / S, join_style=1)
outline = max(polys(outline), key=lambda p: p.area)
outline = Polygon(outline.exterior)          # no internal cut-outs except the hanging hole
hole = circle(*HOLE_C, HOLE_R)
board = outline.difference(hole)
safe_cu = board.buffer(-0.5 / S)                 # copper keep-back from the edge
safe_silk = board.buffer(-0.35 / S)
# ---- balance: where does it hang?  FR4 1.6 mm ~ 2.96 mg/mm2; CR2032 ~3.0 g + SMD holder ~1.5 g
M_BOARD = board.area * S * S * 0.00296
M_BAT = float(os.environ.get('MBAT', 4.5))
cx = (board.centroid.x * M_BOARD + BAT_C[0] * M_BAT) / (M_BOARD + M_BAT)
cy = (board.centroid.y * M_BOARD + BAT_C[1] * M_BAT) / (M_BOARD + M_BAT)
tilt = math.degrees(math.atan2(cx - HOLE_C[0], cy - HOLE_C[1]))
OFFSET_MM = (cx - HOLE_C[0]) * S
print(f"BALANCE TX={TX} board={M_BOARD:.1f}g bat={M_BAT}g com=({cx:.2f},{cy:.2f}) hole_x={HOLE_C[0]} offset={OFFSET_MM:+.2f}mm(final) tilt={tilt:+.2f}deg bare_board_x={board.centroid.x:.2f}")
print("board bounds", [round(v, 2) for v in outline.bounds])

# ---- LEDs: D1..D9 climb the tree, D10 is the heart of the star
occl = unary_union([bdog, ydog, wdog, present]).buffer(1.6)
_ok_zone = safe_cu.buffer(-0.25 / S)
def _valid(x, y, placed):
    pad = box(x - 1.5 / S, y - 0.75 / S, x + 1.5 / S, y + 0.75 / S)
    keep = box(x - 2.2 / S, y - 1.0 / S, x + 2.2 / S, y + 1.0 / S)
    if not _ok_zone.contains(pad) or occl.intersects(keep):
        return False
    return all(abs(x - px) > 5.4 / S or abs(y - py) > 3.6 / S for px, py in placed)
LEDS = []
for dx, y in [(3.5, 58.5), (6.5, 48.5), (-2.5, 40.5), (0.5, 30.5)]:      # four on the tree, bottom to top
    best = None
    for i in range(-16, 17):
        for j in range(-12, 13):
            x, yy = TX + dx + i * 0.25, y + j * 0.25
            dd = (i * 0.25) ** 2 + (j * 0.25) ** 2
            if (best is None or dd < best[0]) and _valid(x, yy, LEDS):
                best = (dd, x, yy)
    if best is None:
        print("LED NO ROOM", dx, y); best = (0, TX + dx, y)
    LEDS.append((round(best[1], 2), round(best[2], 2)))
N_TREE = len(LEDS)
LEDS.append(STAR_C)                                              # D5: the star
_pp = lambda p, kw: place(Point(p), **kw).coords[0]
LEDS.append(_pp((37.4, 45.4), B))                                # D6: black Lab's eye
LEDS.append(_pp((37.4, 45.4), Y))                                # D7: yellow Lab's eye
LEDS.append(wl([(7.3, 13.2)])[0])                                # D8: white dog, on its chest like a glowing bell
LEDS.append((HX - 2.0, HY - 0.3)); LEDS.append((HX + 2.0, HY - 0.3))   # D9, D10: the puppy's eyes
LED_ROT = [0] * N_TREE + [0, 0, 0, 90, 90, 90]
LED_NAME = ["tree"] * N_TREE + ["star", "black Lab eye", "yellow Lab eye", "white dog chest", "puppy left eye", "puppy right eye"]
def _lbox(x, y, rot, hx, hy):
    return box(x - hx, y - hy, x + hx, y + hy) if rot == 0 else box(x - hy, y - hx, x + hy, y + hx)
# clear area per LED: generous on the tree, tight on the dogs so the faces survive
led_keep = unary_union([_lbox(x, y, r, (2.2 if i <= N_TREE else 1.85) / S, (1.0 if i <= N_TREE else 0.9) / S) for i, ((x, y), r) in enumerate(zip(LEDS, LED_ROT))])
for (x, y), r in zip(LEDS, LED_ROT):
    if not safe_cu.contains(_lbox(x, y, r, 1.5 / S, 0.75 / S)): print("LED OFF BOARD", x, y)
led_outline = unary_union([box(x - 1.0, y - 0.625, x + 1.0, y + 0.625).exterior.buffer(0.05) for x, y in LEDS])

# ---- YELLOW DOG: gold, with engraved black details and a hatched shadow down its back
hatch = []
for k in range(-140, 140):
    c = k * 0.95
    px, py = -dvec[1], dvec[0]
    o = (30 + c * dvec[0], 60 + c * dvec[1])
    hatch.append(LineString([(o[0] - px * 90, o[1] - py * 90), (o[0] + px * 90, o[1] + py * 90)]).buffer(0.24, cap_style=2))
hatch = unary_union(hatch)
gapw = wdog.buffer(0.7)
yin = ydog.intersection(safe_cu)
yshade = yin.difference(affinity.translate(yin, 3.4, -0.8)).intersection(box(0, 0, 100, BASE_Y - 3.0))   # side facing away from the star
ygold = unary_union([yin.difference(yshade), yshade.intersection(hatch)]).difference(ydark)
ygold = unary_union([ygold.difference(yjk.buffer(0.15)).difference(ystrap.buffer(0.15)), ytag.difference(circle(*ytag.centroid.coords[0], 0.3))]).difference(gapw)
_yj = yjk.intersection(safe_silk).buffer(-0.35)
yjk_silk = unary_union([_yj.difference(_yj.buffer(-0.28)), yjk_text])

# ---- BLACK DOG: black mask. White engraved lines, and a thin gold rim where the star light catches it
gapy = ydog.buffer(0.9)                     # dark halo that separates the dogs
bvis = bdog.intersection(safe_cu).difference(gapy)
brim = bvis.difference(affinity.translate(bvis, dvec[0] * 1.0, dvec[1] * 1.0))
brim = brim.intersection(box(0, 0, 100, BASE_Y - 2.0))
# gold glint in the eye and on the collar tag
b_eye = place(circle(37.4, 45.4, 0.85), **B)
b_tag = place(tag, **B)
b_eye_gold = b_eye.difference(affinity.translate(b_eye, -0.35, 0.45).buffer(-0.1))
bgold = unary_union([brim.difference(bdark.buffer(0.1)).difference(bjk.buffer(0.4)).difference(bstrap.buffer(0.3)), b_eye, b_tag.difference(circle(*b_tag.centroid.coords[0], 0.3))]).difference(gapy)
bsilk = bdark.difference(b_eye.buffer(0.3)).difference(place(ring(37.4, 58.4, 1.25, 0.32), **B)).intersection(bdog.buffer(-0.6)).difference(gapy)
bsilk = bsilk.difference(place(circle(46.9, 40.7, 2.2), **B))
_bj = bjk.buffer(-0.3)
bsilk = bsilk.union(_bj.difference(bjk_text.buffer(0.03)).difference(_bj.buffer(-0.7).difference(_bj.buffer(-1.0)).difference(bjk_text.buffer(0.7)))).union(bstrap.buffer(-0.25))
bsilk = bsilk.union(place(ring(37.4, 45.4, 1.15, 0.25), **B)).union(place(ring(37.4, 58.4, 1.3, 0.25), **B)).difference(gapy)

# ---- TREE: black, white edge lines on every tier, heavier where the top of a tier catches the light
tree_lines = []
for p in tier_polys:
    q = p.intersection(board).buffer(-0.7)
    tree_lines.append(q.buffer(0.0).difference(q.buffer(-0.3)))
    tree_lines.append(q.difference(affinity.translate(q, 0, 1.0)))
tr = trunk.intersection(board).buffer(-0.7)
tree_lines.append(tr.difference(tr.buffer(-0.3)).difference(unary_union(tier_polys)).intersection(box(0, 0, 100, BASE_Y - 1.4)))
tree_silk = unary_union(tree_lines)
# upper tiers sit in front of lower ones: clear the lines of a lower tier where an upper tier covers it
for i in range(len(tier_polys) - 1, 0, -1):
    pass
cover = unary_union([bdog, ydog, wdog, present]).buffer(0.8)
tl = []
for p in tier_polys:                         # top tier first
    q = p.intersection(board).buffer(-0.7)
    lines = unary_union([q.difference(q.buffer(-0.3)), q.difference(affinity.translate(q, 0, 1.0))])
    tl.append(lines.difference(cover))
    cover = cover.union(p.buffer(0.5))
tree_silk = unary_union(tl + [tree_lines[-1].difference(cover)])
# small gold bauble cap above each tree LED
bauble_gold = unary_union([unary_union([box(x - 0.7, y - 2.55, x + 0.7, y - 1.85), stroke([(x - 0.35, y - 2.55), (x, y - 3.2), (x + 0.35, y - 2.55)], 0.25, smooth=False)]) for x, y in LEDS[:N_TREE]])

# ---- STAR + eyelet: gold
star_gold = star(*STAR_C, 6.2, 3.3).difference(circle(*STAR_C, 2.8))
eyelet = ring(*HOLE_C, HOLE_R + 1.0, 0.9)

# ---- GROUND: lit snow line, the dogs' shadows, lettering
gtop = BASE_Y + 1.2
snow = box(4.0, gtop, 94.0, gtop + 1.5)
shadows = unary_union([
    Polygon([(bdog.bounds[0] + 4, gtop - 1), (bdog.bounds[2] - 6, gtop - 1), (bdog.bounds[2] - 16, gtop + 3), (bdog.bounds[0] - 8, gtop + 3)]),
    Polygon([(ydog.bounds[0] + 6, gtop - 1), (ydog.bounds[2] - 2, gtop - 1), (ydog.bounds[2] - 10, gtop + 3), (ydog.bounds[0] - 2, gtop + 3)]),
    Polygon([(TX - 3, gtop - 1), (TX + 3, gtop - 1), (TX - 3, gtop + 3), (TX - 9, gtop + 3)]),
])
snow = box(4.0, gtop + 0.3, 96.0, gtop + 0.7)
snow = box(4.0, gtop + 0.3, PX0 - 3.0, gtop + 0.7)
CAPTION = "No More Silent Nights"
_cap = 3.9
while True:
    text = text_geom(CAPTION, (1.5 + PX0) / 2 - 0.5, 97.3, _cap)
    if text.bounds[2] - text.bounds[0] <= PX0 - 1.5 - 7.0: break
    _cap -= 0.1
print("caption cap height (final mm)", round(_cap * S, 2))
# white dog: solid white silk with black engraved details, gold bell on the collar
wsilk = wdog.intersection(safe_silk).difference(wdark)
wbell = circle(*wl([(8.6, 10.6)])[0], 0.6)
# present: gold ribbon + bow, white outline
pbox = box(PX0, PY0 + 0.8, PX1, 99.6).intersection(safe_cu)
# bow: gold loops with dark centres so they read as loops, a knot, and two short ribbon ends, all riding on the tilted lid
_holes = LROT(unary_union([affinity.scale(_loop(sg), 0.42, 0.42, origin=(BX + sg * 4.35, KY - 1.5)) for sg in (1, -1)]))
_ends = LROT(unary_union([Polygon([(BX - 1.2, KY + 1.4), (BX + 0.6, KY + 1.4), (BX - 3.4, KY + 8.6), (BX - 4.5, KY + 7.0), (BX - 6.2, KY + 7.8)]),
                          Polygon([(BX + 1.2, KY + 1.4), (BX - 0.6, KY + 1.4), (BX + 3.4, KY + 8.6), (BX + 4.5, KY + 7.0), (BX + 6.2, KY + 7.8)])]))
_knotline = bow_knot.buffer(0.35).difference(bow_knot.buffer(-0.05))
bow_gold = unary_union([bow_loops.difference(_holes), _ends]).difference(_knotline).union(bow_knot.buffer(-0.05))
lid_band = LROT(box(PX0 - 1.5, BT - 3.3, PX1 + 1.5, BT - 0.7))
vband = box(BX - 1.5, BT, BX + 1.5, 99.6)
ribbon = unary_union([vband.difference(_ends.buffer(0.35)).difference(lid.buffer(0.35)), lid_band.difference(bow.buffer(0.35)).difference(_ends.buffer(0.35)), bow_gold,
                      ]).intersection(safe_cu)
pin = box(PX0, BT, PX1, 99.6).intersection(board).buffer(-0.8)
psilk = pin.difference(pin.buffer(-0.35)).difference(ribbon.buffer(0.3)).difference(ppaws.buffer(0.35)).difference(lid.buffer(0.3)).difference(_ends.buffer(0.3))
_ticks = unary_union([stroke([(_tp[i][0] - 0.9, _tp[i][1] + 0.5), (_tp[i][0] + 0.5, _tp[i][1] - 0.5)], 0.3, smooth=False) for i in range(6, len(_tp) - 5, 5)])

# yellow Lab puppy: gold head, ears and paws with dark engraved features
_pdark = unary_union([
    circle(HX - 1.8, HY - 0.3, 0.66), circle(HX + 1.8, HY - 0.3, 0.66),                                # eyes
    smooth_poly([(HX - 1.2, HY + 1.1), (HX + 1.2, HY + 1.1), (HX + 0.8, HY + 2.1), (HX, HY + 2.4), (HX - 0.8, HY + 2.1)]),   # nose
    stroke([(HX - 3.5, HY - 3.0), (HX - 4.2, HY - 1.0), (HX - 3.9, HY + 1.4)], 0.38),                     # ear edges
    stroke([(HX + 3.5, HY - 3.0), (HX + 4.2, HY - 1.0), (HX + 3.9, HY + 1.4)], 0.38),
])
_toes = unary_union([stroke([(HX + sx + dx, BT + 0.2), (HX + sx + dx, BT + 1.7)], 0.25, smooth=False) for sx in (-4.0, 4.0) for dx in (-0.4, 0.4)])
_front = unary_union([lid.buffer(0.45), bow.buffer(0.45), _ends.buffer(0.45)])     # things in front of the puppy
puppy_gold = unary_union([phead.difference(box(0, BT - 0.3, 100, 100)).difference(ppaws.buffer(0.4)).difference(_pdark).difference(_front),
                          ppaws.difference(_toes),
                          ptail.difference(_front).difference(gap.buffer(0.3)).difference(box(0, BT - 0.3, 100, 100)).difference(_ticks.buffer(0.05))])
peye_gold = unary_union([circle(HX - 1.6, HY - 0.5, 0.2), circle(HX + 2.0, HY - 0.5, 0.2)]).difference(_front)

bat_guide = ring(*BAT_C, 10.0, 0.1).union(LineString([(BAT_C[0] - 2, BAT_C[1]), (BAT_C[0] + 2, BAT_C[1])]).buffer(0.05)).union(LineString([(BAT_C[0], BAT_C[1] - 2), (BAT_C[0], BAT_C[1] + 2)]).buffer(0.05))

# ================================================================ assemble
gold_open = unary_union([ygold, bgold.difference(gapw), star_gold, eyelet, bauble_gold, ribbon, wbell, puppy_gold.intersection(safe_cu), peye_gold]).intersection(safe_cu).difference(led_keep)
gold_open = gold_open.buffer(-0.07).buffer(0.07)
copper = gold_open.buffer(0.15).intersection(board.buffer(-0.4)).difference(led_keep.buffer(-0.1))
# the yellow dog is one solid copper shape (details are mask over copper)
copper = unary_union([copper, yin.difference(led_keep).difference(gapw)])
gold_open = gold_open.intersection(copper.buffer(-0.1))

sil_all = unary_union([bsilk.difference(gapw), yjk_silk.difference(gapw), tree_silk, snow, text, wsilk, psilk])
sil_all = sil_all.difference(gold_open.buffer(0.25)).difference(led_keep).difference(bauble_gold.buffer(0.4)).intersection(safe_silk)
sil_all = sil_all.buffer(-0.075).buffer(0.075)

# ---------------------------------------------------------------- scale to the final 85 x 85 mm board
_b = outline.bounds
_dx = (85.0 - (_b[2] - _b[0]) * S) / 2 - _b[0] * S
_dy = (85.0 - (_b[3] - _b[1]) * S) / 2 - _b[1] * S
def fin(g):
    return affinity.translate(affinity.scale(g, S, S, origin=(0, 0)), _dx, _dy)
def finp(p):
    return (p[0] * S + _dx, p[1] * S + _dy)
outline, hole, copper, gold_open, sil_all = fin(outline), fin(hole), fin(copper), fin(gold_open), fin(sil_all)
LEDS = [finp(p) for p in LEDS]
BAT_C, HOLE_C = finp(BAT_C), finp(HOLE_C)
cx, cy = finp((cx, cy))
led_outline = unary_union([_lbox(x, y, r, 1.0, 0.625).exterior.buffer(0.05) for (x, y), r in zip(LEDS, LED_ROT)])
bat_guide = ring(*BAT_C, 10.0, 0.1).union(LineString([(BAT_C[0] - 2, BAT_C[1]), (BAT_C[0] + 2, BAT_C[1])]).buffer(0.05)).union(LineString([(BAT_C[0], BAT_C[1] - 2), (BAT_C[0], BAT_C[1] + 2)]).buffer(0.05))
print("FINAL bounds", [round(v, 2) for v in outline.bounds], "hole", [round(v, 2) for v in HOLE_C], "com", round(cx, 2), round(cy, 2))
# manufacturability at final size: thinnest features
for nm, g in [("mask", gold_open), ("silk", sil_all)]:
    thin = g.difference(g.buffer(-0.06).buffer(0.06))
    print(nm, "area thinner than 0.12 mm:", round(thin.area, 3), "mm2")

# ---------------------------------------------------------------- write SVGs
HDR = '<?xml version="1.0" encoding="UTF-8"?>\n<!-- {c} | 85 x 85 mm, origin top-left, 1 unit = 1 mm. Import into KiCad at X=0 Y=0, scale 1.0 -->\n<svg xmlns="http://www.w3.org/2000/svg" width="85mm" height="85mm" viewBox="0 0 85 85">\n'

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


edge_lines = [ring_d(outline.simplify(0.01).exterior.coords), ring_d(hole.exterior.coords)]
write("01_Edge.Cuts.svg", "Edge.Cuts: board outline = silhouette of two dogs + tree + star on a ground strip, and a 3 mm hanging hole. Outlines only",
      "\n".join(f'<path d="{d_}" fill="none" stroke="#000" stroke-width="0.1"/>' for d_ in edge_lines))
write("02_F.Cu.svg", "F.Cu: copper under the gold art (ENIG). Filled shapes = copper", fill_paths(copper))
write("03_F.Mask.svg", "F.Mask: filled shapes = solder mask OPENINGS = exposed ENIG gold", fill_paths(gold_open))
write("04_F.Silkscreen.svg", "F.Silkscreen: black dog line work, tree edges, snow line and caption (white legend, clear of the 10 LEDs)", fill_paths(sil_all))
write("05_User.Drawings_LED_guide.svg", "User.Drawings: 10 LED positions (0805 outlines, F.Cu) and the CR2032 cell position (20 mm circle, holder goes on B.Cu)",
      fill_paths(bat_guide.union(led_outline).union(unary_union([LineString([(x - 1.6, y), (x + 1.6, y)]).buffer(0.05).union(LineString([(x, y - 1.6), (x, y + 1.6)]).buffer(0.05)) for x, y in LEDS]))))
with open(os.path.join(OUT, "_leds.txt"), "w") as f:
    f.write("# ref, x_mm, y_mm, rotation_deg (F.Cu, origin = top-left of the 85 x 85 mm box)\n")
    for i, (x, y) in enumerate(LEDS):
        f.write(f"D{i+1}, {x:.2f}, {y:.2f}, {LED_ROT[i]}   # {LED_NAME[i]}\n")
    f.write(f"BT1 (CR2032 holder centre, B.Cu), {BAT_C[0]:.2f}, {BAT_C[1]:.2f}, 0\n")
    f.write(f"# hanging hole {HOLE_C[0]:.2f}, {HOLE_C[1]:.2f}; centre of mass with battery {cx:.2f}, {cy:.2f}\n")

MASK, GOLD, GOLD_HI, SILK = "#121214", "#d9b14a", "#f0d27a", "#efeee8"
def colored(g, c):
    out = []
    for p in polys(g.simplify(0.01)):
        dd = ring_d(p.exterior.coords) + "".join(" " + ring_d(i.coords) for i in p.interiors)
        out.append(f'<path d="{dd}" fill="{c}" fill-rule="evenodd"/>')
    return "\n".join(out)
board_d = ring_d(outline.exterior.coords) + " " + ring_d(hole.exterior.coords)
def led_svg(x, y, on, rot=0):
    return f'<g transform="rotate({rot} {x} {y})">' + _led_svg(x, y, on) + '</g>'
def _led_svg(x, y, on):
    g = f'<circle cx="{x}" cy="{y}" r="6" fill="url(#ledglow)"/>' if on else ""
    if on and y > 20: g = g.replace('r="6"', 'r="4"')
    g += f'<rect x="{x-1.45}" y="{y-0.7}" width="0.75" height="1.4" fill="#cfcfcf"/><rect x="{x+0.7}" y="{y-0.7}" width="0.75" height="1.4" fill="#cfcfcf"/>'
    g += f'<rect x="{x-0.7}" y="{y-0.62}" width="1.4" height="1.24" fill="{"#fff6d8" if on else "#e8e2c8"}" stroke="#9a9070" stroke-width="0.08"/>'
    return g
def preview(lit, name):
    body = "".join(led_svg(x, y, i in lit, LED_ROT[i]) for i, (x, y) in enumerate(LEDS))
    with open(os.path.join(OUT, name), "w") as f:
        f.write(f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="-2 -2 89 89">
<defs>
 <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2a2a30"/><stop offset="1" stop-color="{MASK}"/></linearGradient>
 <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GOLD_HI}"/><stop offset="0.55" stop-color="{GOLD}"/><stop offset="1" stop-color="#a8822c"/></linearGradient>
 <radialGradient id="ledglow"><stop offset="0" stop-color="#fff3c4" stop-opacity="0.95"/><stop offset="0.35" stop-color="#ffd76a" stop-opacity="0.45"/><stop offset="1" stop-color="#ffcc40" stop-opacity="0"/></radialGradient>
 <filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="0.9"/></filter>
</defs>
<rect x="-2" y="-2" width="104" height="104" fill="#d9d5cc"/>
<path d="{board_d}" fill="#000" opacity="0.35" filter="url(#sh)" transform="translate(0.9,1.1)" fill-rule="evenodd"/>
<path d="{board_d}" fill="url(#sheen)" fill-rule="evenodd" stroke="#000" stroke-width="0.2"/>
{colored(gold_open, "url(#gold)")}
{colored(sil_all, SILK)}
{body}
</svg>''')
preview([], "preview.svg")
preview([N_TREE], "preview_lit.svg")
preview(range(len(LEDS)), "preview_all_lit.svg")
print("ok", len(no_holes(copper)), len(no_holes(gold_open)), len(no_holes(sil_all)))
