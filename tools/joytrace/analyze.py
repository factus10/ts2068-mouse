import sys,math,statistics as st,glob
from parse import parse,unwrap,CLK
def split(gaps):
    # Otsu threshold on log gaps
    lg=sorted(math.log(g) for g in gaps if g>0)
    best=(None,-1)
    for i in range(1,len(lg)):
        a,b=lg[:i],lg[i:]
        if not a or not b: continue
        w=len(a)*len(b)*(st.mean(a)-st.mean(b))**2
        if w>best[1]: best=((lg[i-1]+lg[i])/2,w)
    return math.exp(best[0]) if best[0] is not None else None
def ms(t): return t/CLK*1000
rows=[]
for name in sys.argv[1:]:
    for ph in ['idle','right','upright']:
        try: r,_=parse(f'runs/{name}_{ph}.log')
        except FileNotFoundError: continue
        if len(r)<10: rows.append((name,ph,len(r))); continue
        t=unwrap([x[1] for x in r]); g=[b-a for a,b in zip(t,t[1:])]
        thr=split(g); intra=[x for x in g if x<thr]; inter=[x for x in g if x>=thr]
        groups=[];cur=1
        for x in g:
            if x<thr: cur+=1
            else: groups.append(cur);cur=1
        groups.append(cur)
        sep=min(inter)/max(intra) if intra and inter else float('nan')
        rows.append((name,ph,len(r),f"{ms(st.median(g)):.1f}",f"{ms(max(intra)) if intra else 0:.1f}",f"{ms(min(inter)) if inter else 0:.1f}",f"{sep:.1f}",st.median(groups) if groups else 0,f"{min(groups)}-{max(groups)}",f"{ms(st.median([a+b for a,b in zip(g,g)])):.0f}" ,f"{len(r)/ (len(groups)) :.1f}", f"{ms((t[-1]-t[0])/len(groups)):.0f}"))
print("name phase reads medgap_ms max_intra_ms min_inter_ms sep reads/burst(med) range _ mean_reads/burst burst_period_ms")
for row in rows: print(*row)
