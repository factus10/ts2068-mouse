# usage: trace.py tap outfile secs settle "keys" inject
# keys: space-separated list of 9-hex ui-io-port states, each held 0.4s then released (e.g. ENTER = ffffffffffff feff00)
import socket,time,sys,os
from zrcp import cmd
PORT=int(os.environ.get('ZPORT','10123'))
LOG=os.environ.get('ZLOG',os.path.join(os.path.dirname(os.path.abspath(__file__)),'zes.log'))
REL='ffffffffffffffff00'
ROWS=[["SH","Z","X","C","V"],["A","S","D","F","G"],["Q","W","E","R","T"],["1","2","3","4","5"],["0","9","8","7","6"],["P","O","I","U","Y"],["ENTER","L","K","J","H"],["SPACE","SYM","M","N","B"]]
def keyhex(name):
    b=[0xff]*8
    for part in name.split('+'):
        for r,row in enumerate(ROWS):
            if part.upper() in row: b[r]&=~(1<<row.index(part.upper()))
    return ''.join('%02x'%x for x in b)+'00'
def C(s,c,w=0.15): return cmd(s,c,w)
def main(tap,out,secs,settle,keys,inject):
    s=socket.create_connection(("127.0.0.1",PORT));time.sleep(0.3);s.recv(4096)
    for i in range(1,11): C(s,"set-breakpoint %d"%i)
    C(s,"disable-breakpoints"); C(s,"set-ui-io-ports "+REL)
    C(s,"hard-reset-cpu",4)
    C(s,"smartload "+tap,1); time.sleep(settle)
    for k in keys.split():
        if k.startswith('w'): time.sleep(float(k[1:])); continue
        if not all(c in '0123456789abcdef' for c in k) or len(k)!=18: k=keyhex(k)
        C(s,"set-ui-io-ports "+k,0.4); C(s,"set-ui-io-ports "+REL,0.6)
    time.sleep(1)
    cond="INFIRED=1 AND PRA&FFH=F6H"
    C(s,"enable-breakpoints")
    if inject:
        C(s,"set-breakpoint 1 %s AND PRA&0300H"%cond); C(s,"set-breakpointaction 1 set-register A=%s"%inject)
    C(s,"set-breakpoint 9 1=1"); C(s,"set-breakpointaction 9 reset-tstatp",0.3); C(s,"set-breakpoint 9")
    acts=["prints R","printe PRA","printe TSTATESP","printe PC"]
    for i,a in enumerate(acts,2):
        C(s,"set-breakpoint %d %s"%(i,cond)); C(s,"set-breakpointaction %d %s"%(i,a))
    wc="OUTFIRED=1 AND PWA&FFH=F5H"
    for i,a in enumerate(["prints W","printe PWV","printe TSTATESP"],6):
        C(s,"set-breakpoint %d %s"%(i,wc)); C(s,"set-breakpointaction %d %s"%(i,a))
    start=os.path.getsize(LOG)
    time.sleep(secs)
    for i in range(1,11): C(s,"set-breakpoint %d"%i)
    C(s,"disable-breakpoints"); time.sleep(0.5)
    C(s,"save-screen "+out+".bmp",0.5)
    with open(LOG,'rb') as f: f.seek(start); data=f.read()
    open(out+'.log','wb').write(data)
if __name__=="__main__":
    a=sys.argv; main(a[1],a[2],float(a[3]),float(a[4]),a[5] if len(a)>5 else "",a[6] if len(a)>6 else "")
