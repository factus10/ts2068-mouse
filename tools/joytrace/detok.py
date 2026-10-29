import sys
T="RND INKEY$ PI FN POINT SCREEN$ ATTR AT TAB VAL$ CODE VAL LEN SIN COS TAN ASN ACS ATN LN EXP INT SQR SGN ABS PEEK IN USR STR$ CHR$ NOT BIN OR AND <= >= <> LINE THEN TO STEP DEF FN CAT FORMAT MOVE ERASE OPEN # CLOSE # MERGE VERIFY BEEP CIRCLE INK PAPER FLASH BRIGHT INVERSE OVER OUT LPRINT LLIST STOP READ DATA RESTORE NEW BORDER CONTINUE DIM REM FOR GO TO GO SUB INPUT LOAD LIST LET PAUSE NEXT POKE PRINT PLOT RUN SAVE RANDOMIZE IF CLS DRAW CLEAR RETURN COPY".split()
X={0x7b:'ON ERR',0x7c:'STICK',0x7d:'SOUND',0x7e:'FREE',0x7f:'RESET'}  # TS2068 extra keywords (assumed)
def blocks(p):
    d=open(p,'rb').read();i=0;out=[]
    while i<len(d):
        n=d[i]|d[i+1]<<8; out.append(d[i+2:i+2+n]); i+=2+n
    return out
def listing(prog):
    i=0
    while i+4<=len(prog):
        ln=prog[i]<<8|prog[i+1]; L=prog[i+2]|prog[i+3]<<8; body=prog[i+4:i+4+L]; i+=4+L
        s='';j=0
        while j<len(body):
            c=body[j]
            if c==0x0e: j+=6; continue
            if c==0x0d: break
            if c>=0xa5: s+=' '+T[c-0xa5].replace(' ',' ')+' '
            elif c in X: s+=' '+X[c]+' '
            elif 32<=c<0x7b: s+=chr(c)
            elif c>=0x80: s+='\\x%02x'%c
            j+=1
        yield ln,s
for p in sys.argv[1:]:
    bl=blocks(p)
    for k,b in enumerate(bl):
        if b[0]==0 and len(b)==19 and b[1]==0:
            vars_off=b[16]|b[17]<<8
            prog=bl[k+1][1:-1][:vars_off]
            print('#####',p, b[2:12].decode('latin1'))
            for ln,s in listing(prog): print(ln,s)
