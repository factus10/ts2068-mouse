# Survey: How TS2068 Drawing Programs Read the Joystick

Status: October 2026. Measured in ZEsarUX 13 with [tools/joytrace](../tools/joytrace/),
backed up by reading the listings and disassembly. Nothing has been checked on
real hardware yet.

## Method

Each program was loaded headless in ZEsarUX three times: no input, right held,
and up+right held. Every joystick read was logged (`IN` from `F6h` with AY
register 14 selected) with its port address (A8 = left stick, A9 = right), a
cumulative t‑state count and PC. Joystick input was faked by changing register
A right after the `IN`. Step sizes and polling logic come from the BASIC
listings and machine‑code disassembly. 11 programs were traced.

## What `STICK` does

From the TS2068 home ROM at `$2902`: `STICK(f, j)` writes `0Eh` to `F5h`,
then runs `IN A,(C)` with **B = j** (1 = left/A8, 2 = right/A9). It then
returns either the four direction bits (f = 1) or the fire bit (f = 2). So:

- **Every `STICK` call is one port read**, including fire‑button checks.
- Directions are 1 up, 2 down, 4 left, 8 right; diagonals are sums (5, 6, 9, 10).
- `STICK(1,2)` / `STICK(2,2)` read the **right** port. Several programs use it.

## Results

| Program | Kind | Port | Reads per pass | Pass rate while moving | Step | Max cursor speed | Notes |
|---|---|---|---|---|---|---|---|
| Doodle (Riley) | BASIC | L | 9 | ~6/s | 4 px | ~24 px/s | Fire clears the screen |
| Color Plot | BASIC | L (+R) | 10 | ~6.6/s | 1 px | ~7 px/s | Diagonals tested twice per line |
| Laurie | BASIC | L | 1 idle, 10 moving | ~8.6/s | 1 px | ~9 px/s | Fire *toggles* draw/erase each pass; no edge clamp |
| Joystick | BASIC | **R** | 13 | ~9.3/s | 1 char (8 px) | ~74 px/s | Character‑cell cursor |
| Quad Draw (Wahl) | BASIC | L | 2 | ~11/s | 1 px | ~11 px/s | 4‑way mirrored plot |
| Paint (Rheesware) / PAINTsinc | BASIC | L | 2–3 | ~14/s | 1 px (keys give 2 or 3) | ~14 px/s | Draws while fire held |
| Draw (Christianson) | BASIC | **R** | ~13 | ~6/s | 1 px | ~6 px/s | Wraps at screen edges |
| arcSCRATCH | MC | L | 1 per poll | 125/s | 1 px | ~125 px/s | `IN A,(F6h)` + delay loop (speed byte at 65116) |
| Draw 512 (McBrine) | MC | L+R+Kempston `1F`+keys | 2 per poll | ~100/s | 1 px (512 wide) | ~100 px/s | **Auto‑repeat**: 1 step, then 32‑poll (~320 ms) delay, then 1 px/poll |
| Multi‑Draw 2068 (Ward) | MC | L | 1 per ~81 ms while held | ~6 steps/s | 1 cell | ~6 cells/s | Needs 2 identical reads per step; **diagonals are commands** |
| ZXDesk 2068 (joystick fallback) | MC | L+R (`03F6h`) | 1 per frame (HALT) | 60/s | 1→2→3→5→7 px | ~420 px/s | Accelerates every 8 frames held; native mode uses the Kempston mouse |

"Pass" means one trip around the program's main loop. Pass rates are derived
from read counts and the number of reads per pass in each listing. BASIC
timings are CPU‑bound, so they should be close to a real 2068. Frame‑synced
code runs about 17% slow in ZEsarUX (see the tools README).

Not surveyed:
- Zebra Painter only scanned the keyboard on its menu.
- TechDraw and PIX‑FX needed more navigation than the scripted runs did.
- Easy Draw is keyboard only.
- No loadable copies were found of the Artworx editor or Pixel Sketch & Graphic Editor.
- Draw II didn't load.

## Findings that shape the firmware

### 1. BASIC programs read several times per pass, so "one step per read" is wrong

A `STICK` statement takes about 5.5 ms of interpreter time, and BASIC loops
test each direction with its own `IF STICK(...)=n`. One pass makes 2–13 reads.
If the device used up a step on every read, the cursor would overshoot by
2–13×. Machine‑code programs, on the other hand, usually read once per poll.

Timing can't tell these apart. Reads inside a BASIC pass are ~5.5 ms apart,
which is the same range as machine‑code poll periods (8–16 ms). A fixed
"debounce window" either merges real machine‑code polls or splits BASIC
passes.

**Proposal: detect BASIC passes from the interpreter itself.** The device is
on the bus anyway, so it can:

- watch memory writes to the system variables **PPC** (`5C45h`, current line)
  and **SUBPPC** (`5C47h`, statement), and
- remember the (line, statement) of the last ROM `STICK` read.

When the interpreter writes a line/statement **at or before** the last read
position, a new pass has started. That covers every loop shape in the survey:
`GO TO` back to the top, `GO SUB` movement routines, early `GO TO` out of a
clamp, and two `STICK` calls in one line (Paint line 40). The device updates
the direction lines **at that moment, before the pass's first read**, and
holds them for the whole pass.

A read is a ROM `STICK` read if the opcode fetch for its `IN` came from
`$2914` in the home ROM. Any other read is machine code: each one, or each
group of reads within about 1 ms (Draw 512 reads both sticks back to back),
counts as one poll. The device updates the lines right after it.

This needs the full address bus (A0–A15), /MREQ and /M1 on top of what the
Kempston ports need. See [architecture.md](architecture.md).

### 2. Behaviour while held varies: level, auto‑repeat, debounce

- **Level** (most programs): every pass that sees a direction moves one step.
  Hold the direction for exactly *n* passes.
- **Auto‑repeat** (Draw 512): the first step happens on the *change*. Holding
  waits about 320 ms, then repeats every poll. For small moves, **pulse**
  (pressed, released, pressed...), which gives a step every 2 polls (~50 px/s)
  with no delay. Switch to holding only when the backlog is bigger than the
  repeat delay is worth.
- **Debounced cells** (Multi‑Draw): a step needs the same value on 2
  consecutive reads, about 160 ms. Hold each step for 2+ polls.

### 3. Some programs treat diagonals as commands

In Multi‑Draw, down‑left/down‑right move a menu selector and up‑left/up‑right
*run menu functions*. A diagonal mouse move must never show up as a diagonal
there. Its profile needs **orthogonal only**: x and y steps take turns.

### 4. Fire semantics differ

- **Level:** Paint draws while fire is held; Draw selects endpoints.
- **Toggle each pass:** Laurie flips draw/erase on every pass where fire is
  pressed, so holding fire flickers.
- **Destructive:** Doodle clears the screen on fire.

Default: left button = fire, held as a level. Per‑profile option: a click
asserts fire for **exactly one pass**.

### 5. Both joystick ports are used

Draw and Joystick read only the right port. Color Plot reads the left and also
checks the right. ZXDesk and Draw 512 read both. **Drive both DB9 ports in
parallel by default**; a profile can restrict to one. Draw 512 also reads the
Kempston joystick port `1Fh`, so answering `1Fh` covers it without a cable.

### 6. BASIC programs are slow, so cap the backlog

At 6–14 passes per second and 1 px per step, most BASIC programs move the
cursor at about 6–24 px/s. A quick mouse flick across the screen would take
10–40 s to play out, and the cursor would keep moving long after the hand
stopped. The accumulator must be **capped** (start at about 0.5 s of passes)
so the cursor stops when the mouse stops. Combined with a per‑profile scale
(mouse counts per step), the mouse becomes a precise slow pointer, not a fast
one. That's the realistic goal for BASIC programs.

## Proposed default profiles

| Profile | Used for | Pass detection | Hold mode | Diagonals | Fire | Default scale |
|---|---|---|---|---|---|---|
| **BASIC‑px** (default) | Doodle, Color Plot, Laurie, Quad Draw, Paint/PAINTsinc, Draw | PPC rewind | level | yes | level | 1 step per ~4 counts |
| **BASIC‑cell** | Joystick, other character‑cell cursors | PPC rewind | level | yes | level | 1 step per ~24 counts |
| **MC‑poll** | arcSCRATCH, ZXDesk fallback, unknown MC | per poll (1 ms group) | level | yes | level | 1 step per ~2 counts |
| **MC‑repeat** | Draw 512 | per poll | pulse, hold if backlog > ~40 | yes | level | 1 step per ~2 counts |
| **MC‑cell‑debounced** | Multi‑Draw | per poll | ≥2 polls per step | **no** | level | 1 step per ~24 counts |

Common to all profiles: backlog cap ~0.5 s of passes, both ports driven, and
Y polarity setting.

Auto‑selection: on the first read, if the `IN` was fetched from ROM `$2914`,
use **BASIC‑px**; otherwise use **MC‑poll**. The other profiles are chosen by
hand (button chord or DIP switch) and could be remembered per program later.

## Open questions

1. Check pass rates on a real 2068 against these emulator numbers (60 Hz vs
   ZEsarUX's 50 Hz timing for frame‑synced code).
2. Can the RP2350's PIO watch every /M1 fetch and every write to
   `5C45h`–`5C47h` at 3.5 MHz without missing cycles? Probably yes, but
   it needs a prototype.
3. Programs that switch to the EXROM or a DOCK cartridge while reading the
   stick: the "`IN` at `$2914`" test assumes the home ROM is mapped
   (HSR = 0).
4. Survey the rest: TechDraw, PIX‑FX, Zebra Painter's drawing mode, and
   Artworx / Pixel Sketch if loadable copies turn up.

## Sources

- Program descriptions and listings: timexsinclair.com archive pages for
  [Draw](https://timexsinclair.com/computer_media/draw/index.html),
  [PAINTsinc](https://timexsinclair.com/computer_media/paintsinc/index.html),
  [Doodle](https://www.timexsinclair.com/computer_media/doodle/),
  [Color Plot](https://timexsinclair.com/computer_media/color-plot/index.html),
  [Joystick](https://timexsinclair.com/computer_media/joystick/index.html),
  [Arcscratch](https://timexsinclair.com/computer_media/arcscratch/index.html),
  [Pixel Sketch and Graphic Editor](https://timexsinclair.com/computer_media/pixel-sketch-and-graphic-editor).
- Program files: the user's local TS2068 archive and the
  [Timex Sinclair software archive](https://archive.org/details/timex-sinclair-software-archive)
  on archive.org.
- `STICK` implementation: TS2068 home ROM, `$2902`–`$2931`.
- Multi‑Draw notes (Gary E. Ward) shipped with the Multi‑Draw 2068 archive.
