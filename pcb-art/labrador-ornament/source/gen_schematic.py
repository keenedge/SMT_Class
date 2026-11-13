from lib import *
import uuid as U, re
def nu(): return str(U.uuid4())
def clone(src_ref, ref, X, Y, rot=None, value=None, footprint=None, lib=None):
    l,x0,y0,r0,blk=INST[src_ref]
    rot=r0 if rot is None else rot
    dx,dy=X-x0,Y-y0
    def sh(m):
        return f"(at {float(m.group(1))+dx:.3f} {float(m.group(2))+dy:.3f}{m.group(3)})"
    b=re.sub(r'\(at ([-\d.]+) ([-\d.]+)((?: \d+)?)\)',sh,blk)
    b=re.sub(r'\(uuid "[^"]+"\)',lambda m:f'(uuid "{nu()}")',b)
    b=re.sub(r'(\(property "Reference" ")[^"]+',lambda m:m.group(1)+ref,b)
    b=re.sub(r'(\(reference ")[^"]+',lambda m:m.group(1)+ref,b)
    if value: b=re.sub(r'(\(property "Value" ")[^"]*',lambda m:m.group(1)+value,b)
    if footprint: b=re.sub(r'(\(property "Footprint" ")[^"]*',lambda m:m.group(1)+footprint,b)
    if lib: b=b.replace(f'(lib_id "{l}")',f'(lib_id "{lib}")')
    # symbol rotation: first "(at X Y rot)" is the symbol's own
    b=re.sub(r'\(at ([-\d.]+) ([-\d.]+) \d+\)',lambda m:f'(at {m.group(1)} {m.group(2)} {rot})',b,count=1)
    return b+'\n', (l if not lib else lib)
PINS['Device:D']=PINS['Device:LED']
out=[]; labels=[]; wires=[]; ncs=[]
placed={}
def place(src,ref,X,Y,rot=None,**kw):
    t,lib=clone(src,ref,X,Y,rot,**kw)
    out.append(t); placed[ref]=(lib,X,Y,INST[src][3] if rot is None else rot)
def P(ref,num,i=0):
    lib,X,Y,r=placed[ref]; return pinpos(lib,num,X,Y,r,i)
def label(name,pt,ang=0):
    just = 'right' if ang==180 else 'left'
    labels.append(f'''\t(label "{name}"
\t\t(at {pt[0]:.2f} {pt[1]:.2f} {ang})
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify {just} bottom)
\t\t)
\t\t(uuid "{nu()}")
\t)
''')
def wire(a,b):
    wires.append(f'''\t(wire
\t\t(pts
\t\t\t(xy {a[0]:.2f} {a[1]:.2f}) (xy {b[0]:.2f} {b[1]:.2f})
\t\t)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type default)
\t\t)
\t\t(uuid "{nu()}")
\t)
''')
def nc(pt): ncs.append(f'\t(no_connect\n\t\t(at {pt[0]:.2f} {pt[1]:.2f})\n\t\t(uuid "{nu()}")\n\t)\n')
# ---- existing blocks kept in place
for ref,val in [("U1","TLC555CD"),("U2","74HC4017"),("J1",None),("R1",None),("R2",None),("C1",None),("C2",None),("R13",None),("R14",None)]:
    l,x,y,r,_=INST[ref]; place(ref,ref,x,y,r,value=val)
# pins -> labels
def side(pt, ref, num):   # label angle from pin side relative to symbol origin
    lib,X,Y,r=placed[ref]
    return 180 if pt[0]<X-0.1 else (0 if pt[0]>X+0.1 else (90 if pt[1]<Y else 270))
def L(ref,num,name,i=0):
    pt=P(ref,num,i); ang=side(pt,ref,num)
    label(name,pt,ang)
# 555
L("U1","1","GND"); L("U1","8","VDD"); L("U1","4","VDD"); L("U1","2","TRIG"); L("U1","6","TRIG"); L("U1","7","DISCH"); L("U1","3","CLK"); nc(P("U1","5"))
L("R1","1","VDD"); L("R1","2","DISCH"); L("R2","1","DISCH"); L("R2","2","TRIG"); L("C1","1","TRIG"); L("C1","2","GND"); L("C2","1","VDD"); L("C2","2","GND")
# 4017
L("U2","16","VDD"); L("U2","8","GND"); L("U2","13","GND"); L("U2","15","GND"); L("U2","14","CLK"); nc(P("U2","12")); nc(P("U2","9"))
for pin,net in [("3","Q0"),("2","Q1"),("4","Q2"),("7","Q3"),("10","Q4"),("1","Q5"),("5","Q6"),("6","Q7"),("11","Q9")]: L("U2",pin,net)
# USB
L("J1","A9","VDD"); L("J1","A12","GND"); L("J1","SH","GND"); L("J1","A5","CC1"); L("J1","B5","CC2")
L("R13","1","CC1"); L("R13","2","GND"); L("R14","1","CC2"); L("R14","2","GND")
# power symbols + flags co-located with the labels
for lib,nm,pt in [("power:VDD","VDD",(250.0,25.0)),("power:GND","GND",(250.0,40.0))]:
    pass
# LED rows: (resistor ref, LED ref, net)
ROWS=[("R3","D1","Q0"),("R4","D2","Q0"),("R5","D3","Q1"),("R6","D4","Q1"),("R7","D5","Q2"),("R8","D6","Q3"),("R9","D7","Q4"),("R10","D8","STAR"),("R11","D9","EYES"),("R12","D10","EYES")]
for k,(rr,dd,net) in enumerate(ROWS):
    y=35+7.62*k
    place("R3",rr,195.0,y,90,value="1k")
    place("D1",dd,212.0,y,180)
    L(rr,"1",net); wire(P(rr,"2"),P(dd,"2")); L(dd,"1","GND")
# diode-OR: Q5,Q6 -> STAR ; Q7,Q9 -> EYES
for k,(dn,a,b) in enumerate([("D11","Q5","STAR"),("D12","Q6","STAR"),("D13","Q7","EYES"),("D14","Q9","EYES")]):
    y=118+7.62*k
    place("D1",dn,205.0,y,180,value="1N4148",footprint="Diode_SMD:D_0805_2012Metric",lib="Device:D")
    L(dn,"2",a); L(dn,"1",b)

for ref,src,pt in [("#PWR04","#PWR04",(158.75,45.72)),("#PWR05","#PWR05",(158.75,93.98)),("#FLG01","#FLG01",(158.75,45.72)),("#FLG02","#FLG02",(158.75,93.98))]:
    place(src,ref,pt[0],pt[1])
NOTE = "10-stage sequence (4017 outputs): Q0 tree group 1 (D1,D2) | Q1 group 2 (D3,D4) | Q2 group 3 (D5) | Q3 group 4 (D6) | Q4 group 5 (D7) | Q5,Q6 star (D8) | Q7 puppy eyes (D9,D10) | Q8 all off | Q9 puppy eyes. 5 V USB only. U1 must be a CMOS 555 (TLC555) and U2 a 74HC4017."
labels.append(f'\t(text "{NOTE}"\n\t\t(exclude_from_sim no)\n\t\t(at 120 20 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left)\n\t\t)\n\t\t(uuid "{nu()}")\n\t)\n')
open('out_body.txt','w').write(''.join(out)+''.join(labels)+''.join(wires)+''.join(ncs))
print(len(out),len(labels),len(wires),len(ncs))

D_SYM=LIB[LIB.index('\t\t(symbol "Device:LED"'):]
D_SYM=D_SYM[:match(D_SYM,D_SYM.index('(symbol'))]
D_SYM=D_SYM.replace('Device:LED','Device:D').replace('LED_0_1','D_0_1').replace('LED_1_1','D_1_1').replace('"Light emitting diode"','"Diode"').replace('"LED"','"D"')
for _ in range(2):
    i=D_SYM.index('\t\t\t\t(polyline'); D_SYM=D_SYM[:i]+D_SYM[match(D_SYM,i+4)+1:]
lib_end=LIB.rstrip()
LIB2=lib_end[:-1].rstrip()+'\n'+D_SYM.rstrip('\n')+'\n\t)'
head=s[:LI].replace('(rev "0.0.1")','(rev "0.1.0")')
tail=s[s.index('\t(sheet_instances'):]
body=''.join(out)+''.join(labels)+''.join(wires)+''.join(ncs)
open('/root/SMT_Class/smt_tree.kicad_sch','w').write(head+LIB2+'\n'+body+tail)
print('written')
