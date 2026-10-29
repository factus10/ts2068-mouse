# joytrace

Logs every TS2068 joystick read (`IN` from port `F6h` with AY register 14
selected) while a program runs in ZEsarUX. It was used for
[docs/joystick-survey.md](../../docs/joystick-survey.md).

The scripts drive ZEsarUX 13 through its remote protocol (ZRCP). They use
breakpoint actions to print the port address, a cumulative t-state count and
PC on every read. Another breakpoint action fakes joystick input by setting
register A after the `IN`. That only works for `IN A,(n)`/`IN A,(C)`; ZEsarUX
doesn't show 2068 joystick input through ZRCP.

```
PROGS=/path/to/taps ./batch.sh idle            # no input
PROGS=/path/to/taps ./batch.sh right F7H       # hold right (active-low byte)
PROGS=/path/to/taps ./batch.sh upright F6H     # hold up+right
python3 analyze.py doodle colorplot ...        # burst/period summary
python3 -I detok.py prog.tap                   # rough BASIC listing (2068 token table not exact)
```

`programs.txt` lists each program as `name|settle-seconds|keys`. Keys use
names (`ENTER`, `SPACE`, `R`, `N`...) and `wN` waits N seconds. `batch.sh`
starts a fresh emulator for each run because ZEsarUX sometimes segfaults with
heavy breakpoint output.

Caveats:
- ZEsarUX's TS2068 runs about 69,900 t-states per frame (Spectrum-style
  50 Hz). A real 2068 runs at 60 Hz, so anything synced to the frame
  (HALT, PAUSE, FRAMES) runs about 17% slower here than on hardware.
- `TSTATESP` sometimes resets mid-run; `parse.py` bridges the jump.
