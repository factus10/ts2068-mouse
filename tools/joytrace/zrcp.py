import socket,sys,time
def cmd(s,c,wait=0.3):
    s.sendall((c+"\n").encode()); time.sleep(wait); out=b""
    s.settimeout(0.5)
    try:
        while True:
            d=s.recv(65536)
            if not d: break
            out+=d
            if out.rstrip().endswith(b"command>"): break
    except socket.timeout: pass
    return out.decode('latin1')
if __name__=="__main__":
    s=socket.create_connection(("127.0.0.1",int(sys.argv[1])));time.sleep(0.3);s.recv(4096)
    for c in sys.argv[2:]: print(cmd(s,c))
