import sys,collections
CLK=3528000
def parse(fn):
    L=[l.strip() for l in open(fn,encoding='latin1')]
    ev=[];i=0
    while i<len(L):
        try:
            if L[i]=='R': ev.append(('R',int(L[i+1]),int(L[i+2]),int(L[i+3]))); i+=4; continue
            if L[i]=='W': ev.append(('W',int(L[i+1]),int(L[i+2]),0)); i+=3; continue
        except (ValueError,IndexError): pass
        i+=1
    # keep joystick reads: AY reg 14 selected, A8 or A9 set
    reg=None; reads=[]
    for k,a,t,pc in ev:
        if k=='W': reg=a
        elif reg==14 and (a>>8)&3: reads.append((a,t,pc))
    return reads,ev
def unwrap(t):
    # TSTATESP occasionally resets mid-run; splice segments by assuming a median-sized gap at the break
    out=[t[0]];g=[]
    for a,b in zip(t,t[1:]):
        d=b-a
        if d<0: d=sorted(g)[len(g)//2] if g else 0
        g.append(d); out.append(out[-1]+d)
    return out
def summarize(fn):
    r,ev=parse(fn)
    if len(r)<2: print(fn,'joystick reads:',len(r)); return None
    t=unwrap([x[1] for x in r]); dur=(t[-1]-t[0])/CLK
    hi=collections.Counter(a>>8 for a,_,_ in r); pcs=collections.Counter(pc for *_,pc in r)
    print(f"{fn}: reads={len(r)} span={dur:.2f}s rate={len(r)/dur:.1f}/s sticks={dict(hi)} pcs={ {hex(k):v for k,v in pcs.most_common(5)} }")
    return r
if __name__=="__main__":
    for f in sys.argv[1:]: summarize(f)
