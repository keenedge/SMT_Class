import re, json, uuid as U, sys, os, math
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import affinity
OUTD = sys.argv[1]; DEST = sys.argv[2]
OX, OY = 100.0, 60.0
orig = open('/tmp/orig.kicad_pcb').read()
def match(s, i):
    d = 0
    for j in range(i, len(s)):
        if s[j] == '(': d += 1
        elif s[j] == ')':
            d -= 1
            if d == 0: return j + 1
def nu(): return str(U.uuid4())
fp0 = orig.index('\n\t(footprint "') + 1
header = orig[:fp0]
FP = {}
pos = fp0
while True:
    m = re.compile(r'\t\(footprint "([^"]+)"').match(orig, pos)
    if not m: break
    e = match(orig, pos + 1)
    blk = orig[pos:e]
    ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
    FP[ref] = (m.group(1), blk)
    pos = e
    while orig[pos] in '\n\t ': pos += 1
    pos -= 1
print(len(FP), 'footprints in the original')
# schematic symbol uuids
sch = open('/root/SMT_Class/smt_tree.kicad_sch').read()
SU = {}
for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "[^"]+"\)', sch):
    blk = sch[m.start() + 1:match(sch, m.start() + 1)]
    ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
    SU[ref] = re.search(r'\n\t\t\(uuid "([^"]+)"\)', blk).group(1)
# ---------------- netlist (from the generated schematic)
sys.path.insert(0, 'sch')
NETS = {}
def N(name, *pins):
    for p in pins: NETS[p] = name
N('GND', *[('D%d' % i, '1') for i in range(1, 11)], ('C1', '2'), ('C2', '2'), ('R13', '2'), ('R14', '2'), ('U1', '1'), ('U2', '8'), ('U2', '13'), ('U2', '15'),
  ('J1', 'A12'), ('J1', 'B12'), ('J1', 'SH'))
N('VDD', ('C2', '1'), ('J1', 'A9'), ('J1', 'B9'), ('R1', '1'), ('U1', '4'), ('U1', '8'), ('U2', '16'))
N('/TRIG', ('C1', '1'), ('R2', '2'), ('U1', '2'), ('U1', '6'))
N('/CLK', ('U1', '3'), ('U2', '14'))
N('/DISCH', ('R1', '2'), ('R2', '1'), ('U1', '7'))
N('/CC1', ('J1', 'A5'), ('R13', '1')); N('/CC2', ('J1', 'B5'), ('R14', '1'))
for q, pin, loads in [('Q0', '3', [('R3', '1'), ('R4', '1')]), ('Q1', '2', [('R5', '1'), ('R6', '1')]), ('Q2', '4', [('R7', '1')]), ('Q3', '7', [('R8', '1')]),
                      ('Q4', '10', [('R9', '1')]), ('Q5', '1', [('D11', '2')]), ('Q6', '5', [('D12', '2')]), ('Q7', '6', [('D13', '2')]), ('Q9', '11', [('D14', '2')])]:
    N('/' + q, ('U2', pin), *loads)
N('/STAR', ('D11', '1'), ('D12', '1'), ('R10', '1')); N('/EYES', ('D13', '1'), ('D14', '1'), ('R11', '1'), ('R12', '1'))
for rr, dd in [('R3', 'D1'), ('R4', 'D2'), ('R5', 'D3'), ('R6', 'D4'), ('R7', 'D5'), ('R8', 'D6'), ('R9', 'D7'), ('R10', 'D8'), ('R11', 'D9'), ('R12', 'D10')]:
    N(f'Net-({dd}-A)', (rr, '2'), (dd, '2'))
# ---------------- placement
leds = {}
for l in open(os.path.join(OUTD, '_leds.txt')):
    m = re.match(r'(D\d+), ([\d.]+), ([\d.]+), (\d+)', l)
    if m: leds[m.group(1)] = (float(m.group(2)), float(m.group(3)), int(m.group(4)))
pj = json.load(open(os.path.join(OUTD, 'parts.json')))
PL = {}
for r, (x, y, rot) in leds.items(): PL[r] = (x, y, rot)
for p in pj['parts']: PL[p[0]] = (p[2], p[3], p[6])
PL['J1'] = (pj['usb'][0], pj['usb'][1], 0)
VAL = {'U1': 'TLC555CD', 'U2': '74HC4017', 'R1': '10k', 'R2': '2M', 'C1': '100n', 'C2': '100n', 'R13': '5k1', 'R14': '5k1'}
for i in range(3, 13): VAL['R%d' % i] = '1k'
for i in range(11, 15): VAL['D%d' % i] = '1N4148'
SRC = {r: r for r in FP}
for d in ('D11', 'D12', 'D13', 'D14'): SRC[d] = 'R3'
def build(ref):
    name, blk = FP[SRC[ref]]
    x, y, rot = PL[ref]
    X, Y = x + OX, y + OY
    if ref.startswith('D') and int(ref[1:]) >= 11:
        name = 'Diode_SMD:D_0805_2012Metric'
        blk = blk.replace('Resistor_SMD:R_0805_2012Metric', name).replace('Resistor SMD 0805', 'Diode SMD 0805').replace('R_0805_2012Metric', 'D_0805_2012Metric').replace('Resistor_SMD.3dshapes', 'Diode_SMD.3dshapes')
        blk = blk.replace('(tags "resistor")', '(tags "diode")')
    # footprint own (at)
    blk = re.sub(r'(\n\t\t\(at )[-\d.]+ [-\d.]+(?: [-\d.]+)?\)', lambda m: f'{m.group(1)}{X:.3f} {Y:.3f}{" %g" % rot if rot else ""})', blk, count=1)
    # text angles inside properties / fp_text follow the footprint rotation
    def fixtext(m):
        return re.sub(r'\(at ([-\d.]+) ([-\d.]+)(?: [-\d.]+)?\)', lambda a: f'(at {a.group(1)} {a.group(2)} {rot})', m.group(0), count=1)
    blk = re.sub(r'\n\t\t\((?:property|fp_text) [^\n]*\n\t\t\t\(at [^\n]*\)', fixtext, blk)
    blk = re.sub(r'(\(property "Reference" ")[^"]+', lambda m: m.group(1) + ref, blk)
    blk = re.sub(r'(\(property "Value" ")[^"]*', lambda m: m.group(1) + VAL.get(ref, 'LED' if ref.startswith('D') else ''), blk) if ref in VAL or ref.startswith('D') else blk
    # reference text off the (white) silkscreen
    blk = re.sub(r'(\(property "Reference" "[^"]*"\n\t\t\t\(at [^\n]*\n\t\t\t\(layer )"F.SilkS"', r'\1"F.Fab"', blk)
    blk = re.sub(r'\(uuid "[^"]+"\)', lambda m: f'(uuid "{nu()}")', blk)
    blk = re.sub(r'\(path "/[^"]*"\)', f'(path "/{SU[ref]}")', blk)
    # pad nets
    def padfix(m):
        pb = m.group(0)
        num = re.search(r'\(pad "([^"]+)"', pb).group(1)
        net = NETS.get((ref, num))
        pb = re.sub(r'\n\t\t\t\(net "[^"]*"\)', '', pb)
        if net: pb = pb.replace('\n\t\t\t(pinfunction', f'\n\t\t\t(net "{net}")\n\t\t\t(pinfunction', 1) if '(pinfunction' in pb else pb.replace('\n\t\t\t(pintype', f'\n\t\t\t(net "{net}")\n\t\t\t(pintype', 1)
        return pb
    out = []; i = 0
    while True:
        j = blk.find('\n\t\t(pad "', i)
        if j < 0: out.append(blk[i:]); break
        out.append(blk[i:j + 1]); e = match(blk, j + 1)
        out.append(padfix(type('M', (), {'group': lambda self, k, b=blk[j + 1:e]: b})()))
        i = e
    blk = ''.join(out)
    return blk
fps = ''.join(build(r) + '\n' for r in sorted(PL, key=lambda r: (r[0], int(re.sub(r'\D', '', r)))))
# ---------------- art layers
def poly_from_svg(fn):
    t = open(os.path.join(OUTD, fn)).read()
    res = []
    for d in re.findall(r'<path d="([^"]+)"', t):
        pts = [(float(a), float(b)) for a, b in re.findall(r'([-\d.]+),([-\d.]+)', d)]
        res.append(pts)
    return res
def gr(pts, layer, fill, w=0):
    xy = ' '.join(f'(xy {x + OX:.4f} {y + OY:.4f})' for x, y in pts)
    return f'\t(gr_poly\n\t\t(pts\n\t\t\t{xy}\n\t\t)\n\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type solid)\n\t\t)\n\t\t(fill {"yes" if fill else "no"})\n\t\t(layer "{layer}")\n\t\t(uuid "{nu()}")\n\t)\n'
art = ''
for fn, layer, fill, w in [('01_Edge.Cuts.svg', 'Edge.Cuts', False, 0.1), ('02_F.Cu.svg', 'F.Cu', True, 0), ('03_F.Mask.svg', 'F.Mask', True, 0), ('04_F.Silkscreen.svg', 'F.SilkS', True, 0)]:
    pp = poly_from_svg(fn)
    print(fn, len(pp), 'polygons')
    art += ''.join(gr(p, layer, fill, w) for p in pp)
body = header + fps + art + ')\n'
open(DEST, 'w').write(body)
print('written', DEST, len(body))
d = 0
for ch in body:
    d += (ch == '(') - (ch == ')')
print('paren balance', d)
