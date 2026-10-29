#!/bin/zsh
cd ${0:a:h}
phase=$1; inject=$2
while IFS='|' read name settle keys; do
  [[ -z $name || $name == \#* ]] && continue
  for attempt in 1 2; do
    pkill -f 'zesarux --noconfigfile' 2>/dev/null; sleep 1
    /Applications/zesarux.app/Contents/MacOS/zesarux --noconfigfile --machine TS2068 --vo null --ao null --nowelcomemessage --enable-remoteprotocol --remoteprotocol-port 10123 --quickexit > zes.log 2>&1 &
    for i in {1..10}; do nc -z 127.0.0.1 10123 2>/dev/null && break; sleep 1; done
    python3 trace.py ${PROGS:-$PWD/progs}/$name.tap $PWD/runs/${name}_$phase 5 $settle "$keys" $inject 2>/dev/null && break
    echo "retry $name"
  done
  python3 parse.py runs/${name}_$phase.log 2>&1 | tail -1
done < programs.txt
pkill -f 'zesarux --noconfigfile' 2>/dev/null
