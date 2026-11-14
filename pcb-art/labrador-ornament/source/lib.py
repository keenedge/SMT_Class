import re, math, uuid
SRC='/tmp/orig.kicad_sch'
s=open(SRC).read()
def match(s,i):
    d=0
    for j in range(i,len(s)):
        if s[j]=='(':d+=1
        elif s[j]==')':
            d-=1
            if d==0:return j+1
LI=s.index('\t(lib_symbols'); LJ=match(s,LI); LIB=s[LI:LJ]
PINS={}
for m in re.finditer(r'\n\t\t\(symbol "([^"]+)"\n',LIB):
    k=match(LIB,m.start()+1); blk=LIB[m.start():k]; d={}
    for p in re.finditer(r'\(pin (\w+) (\w+)\n\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\n\s*\(length ([\d.]+)\)(?:\s*\(hide yes\))?\n\s*\(name "([^"]*)"[\s\S]*?\(number "([^"]*)"',blk):
        d.setdefault(p.group(8),[]).append((float(p.group(3)),float(p.group(4)),int(p.group(5))))
    PINS[m.group(1)]=d
def pinpos(lib,num,X,Y,rot,i=0):
    x,y,a=PINS[lib][num][i]
    t=math.radians(rot); c,sn=round(math.cos(t)),round(math.sin(t))
    rx,ry=x*c-y*sn, x*sn+y*c
    return (round(X+rx,2), round(Y-ry,2))
# instance blocks
INST={}
for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "([^"]+)"\)\n\t\t\(at ([-\d.]+) ([-\d.]+) (\d+)\)',s):
    k=match(s,m.start()+1); blk=s[m.start()+1:k]
    ref=re.search(r'\(property "Reference" "([^"]+)"',blk).group(1)
    INST[ref]=(m.group(1),float(m.group(2)),float(m.group(3)),int(m.group(4)),blk)
WIRES=[(float(a),float(b),float(c),float(d)) for a,b,c,d in re.findall(r'\(wire\n\s*\(pts\n\s*\(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)',s)]
