# TS2068 Mouse Interface — Architecture Draft

Status: draft, October 2026. Nothing has been built or tested on hardware yet.

## Goals

1. **Legacy mode.** Existing TS2068 programs that steer a pointer with the
   joystick (mainly drawing programs) work with a mouse without modification.
2. **Native mode.** New or patched software reads real mouse movement and buttons
   through a Kempston-mouse-compatible port. ZXDesk 2068 already contains this
   driver (see [ZXDesk notes](#zxdesk-2068)).
3. One device, one microcontroller, powered from the 2068.

## Findings: how the 2068 joystick port really works

Source: *TS2068 Technical Manual*, §2.1.7, Fig. 2.1.7‑1 and Table 2.4.4‑1;
Alvin Albrecht's port map.

| DB9 pin | Signal                      |
|---------|-----------------------------|
| 1       | Up                          |
| 2       | Down                        |
| 3       | Left                        |
| 4       | Right                       |
| 5       | not used                    |
| 6       | Button                      |
| 7       | +5 V                        |
| 8       | **Read strobe** (A8 left, A9 right) |
| 9       | GND                         |

- The joysticks are AY‑3‑8912 I/O port A (register 14). Software writes `0Eh` to
  port `F5h`, then reads `F6h`. On that read, A8 high selects the left stick and
  A9 high selects the right stick; selecting both ORs them together. Bits:
  0 up, 1 down, 2 left, 3 right, 7 fire, all active low.
- Each connector's pin 8 is pulled low by a transistor (Q8 left, Q7 right).
  **That transistor's base is driven straight from A8/A9 through a resistor.
  It is not gated by `IORQ`, `RD` or the `F6h` decode.** Each direction pin
  goes back to a register‑14 bit through an isolation diode. A joystick switch
  connects a direction pin to pin 8, so the bit reads 0 only while pin 8 is low.

**Consequence: pin 8 is not a usable poll signal.** It follows A8/A9 on every
bus cycle, including opcode fetches, data accesses and refresh cycles. During
refresh, A8–A15 carry the I register. So it toggles at bus speed and can't
tell the device when a program actually read the joystick. The device has to
watch the expansion bus to see real polls. That is one reason to build legacy
and native modes into one bus‑attached device.

**Consequence for driving the lines:** the device should behave like a joystick:
an isolated switch from each direction pin to **pin 8**, not to GND. Pulling a
pin to GND would also work, but because the left and right diode sets share the
same register bits, the move would show up on reads of *either* stick.

## Findings: port decoding

The 2068's internal I/O ports (Technical Manual Table 2.1.13‑1):

| Port | Use | Decode |
|------|-----|--------|
| `FFh` | Display/interrupt/EXROM control | full low byte |
| `FEh` | Keyboard, tape, border | A0 = 0 (Spectrum compatible) |
| `FBh` | TS2040 printer | A7 = 1, A2 = 0 |
| `F6h`/`F5h` | AY data/register (joysticks) | full low byte |
| `F4h` | Bank switching (HSR) | full low byte |

The Kempston mouse ports have low byte `DFh` (A7=1, A5=0, A2=1, A0=1), and the
Kempston joystick port has `1Fh`. Neither matches anything in that table. The
device will decode the **full low byte** anyway, so it can share the bus with
other peripherals. It then uses A8–A10 the way the original Kempston mouse does.

| Port    | A10 A9 A8 | Returns |
|---------|-----------|---------|
| `FBDFh` | 0 1 1     | X counter (8‑bit, wraps) |
| `FFDFh` | 1 1 1     | Y counter (8‑bit, wraps) |
| `FADFh` | 0 1 0     | Buttons: D0 right, D1 left, D2 middle, active low; D4–D7 wheel (K‑Mouse extension, optional) |
| `xx1Fh` | —         | Kempston joystick (optional, for Spectrum‑mode software) |

The Y direction differs between sources: MAME and K‑Mouse docs say the counter
grows moving down, while other references say up. ZXDesk has its own "Invert Y"
setting. Make Y polarity a device setting, default to what ZXDesk expects, and
confirm against real hardware or an emulator.

## Block diagram

```
  USB mouse ──┐                         TS2068 expansion bus (2x32 edge)
  PS/2 mouse ─┤                          A0–A15, D0–D7, /IORQ, /MREQ, /RD, /WR, /M1, +5V, GND
              ▼                                   │
     ┌──────────────────┐   level-shift/buffer    │
     │  MCU (RP2350B)   │◄──── address/control ───┤  (inputs, 5 V → 3.3 V)
     │                  │◄───► data bus ──────────┤  (74LVC245/74HCT245, OE from MCU)
     │  core 0: mouse   │                         │
     │  core 1: logic   │
     │  PIO: bus engine │── 5 lines ─► 2× switch array ─► DB9 to left + right joystick ports
     └──────────────────┘              (opto or 74HC4066, pins 1–4,6 ↔ pin 8)
```

### Hardware blocks

**Microcontroller.** RP2350B (48 GPIO) on a module such as the Pimoroni PGA2350
or a WeAct RP2350B core board. Detecting BASIC passes (see legacy mode) means
watching the whole bus: A0–A15 (16), D0–D7 (8), /IORQ, /RD, /WR, /MREQ, /M1
(5), data buffer enable/direction (2), five joystick outputs (5; both DB9
ports run in parallel) and PS/2 (2) = 38. That leaves room for LEDs, a config
button and a debug UART. The RP2040 (30 GPIO) is out.

- PIO state machines handle the bus. They watch /IORQ and /RD, compare the low
  address byte, and either drive the data bus (Kempston reads) or just report
  the event (joystick reads, `F5h` writes).
- USB host for a USB mouse, via native USB or PIO‑USB with TinyUSB. PS/2 is
  handled by a small PIO program, so old mice work too.

**Bus interface.** A Z80 `IN` at 3.528 MHz holds /IORQ and /RD active for
roughly 2.5 T‑states (T2, the automatic wait state, then T3), about 700 ns.
That is plenty for PIO, which runs at 6.7–8 ns per instruction.
- Inputs: the RP2350 datasheet lists 5 V‑tolerant GPIO, but this needs
  checking against the exact module and IOVDD setup. Otherwise use
  74LVC245/74LVC541 buffers powered at 3.3 V (5 V‑tolerant inputs).
- Data bus: always through a 74LVC245 (or 74HCT245 with suitable thresholds),
  with direction and output‑enable driven by the PIO. The device must only
  drive the bus during a matched read, and must release it before the end of
  T3.
- The interrupt acknowledge cycle (/IORQ with /M1) has /RD high, so gating on
  /RD is enough. /M1 isn't needed.

**Joystick output.** Five optocouplers (PC817 or similar), or a 74HC4066 powered
from joystick pin 7. Each one switches a direction/fire pin to pin 8. This
behaves exactly like a mechanical joystick, so the 2068 can't tell the
difference, and it keeps the bus card electrically separate from the joystick
port's ground. **Two** DB9 cables go to the left and right ports. Each port
has its own strobe (pin 8), so each port gets its own set of five switches,
driven from the same five MCU lines (or ten lines, so a profile can limit
output to one port). By default both ports are driven in parallel, because
some programs read only the right port (Draw, Joystick) and others read both.

**Power.** From the bus +5 V. Budget: MCU about 30 mA, USB mouse up to 100 mA,
buffers a few mA. The 2068's 5 V budget for expansion cards still needs
checking. A USB mouse may need its own current limit or polyfuse.

## Firmware

### Shared state

- `mx, my`: 8‑bit wrapping counters (Kempston native mode).
- `buttons`: left/right/middle, plus a 4‑bit wheel counter.
- `jx, jy`: signed accumulators for joystick emulation, in mouse counts.
- `ay_reg`: last value written to `F5h` (watched on the bus), so joystick
  polls are only counted when register 14 is selected.

### Native mode (Kempston)

The mouse task adds deltas to `mx`/`my` and updates `buttons`. The PIO bus
engine looks up the current byte on every matched read. No timing tricks are
needed; this is how the original Kempston interface works.

### Legacy mode (joystick emulation)

Based on [the drawing‑program survey](joystick-survey.md). Legacy programs
move the cursor a fixed (sometimes accelerating) number of pixels on each
*pass* of their main loop that sees a direction held. The device's job is to
hold the direction for the right number of passes.

A BASIC program makes 2–13 `STICK` reads per pass, about 5.5 ms apart. That's
the same spacing as machine‑code poll periods, so read timing can't find pass
boundaries. Instead:

1. **Read classification.** The bus engine keeps the address of the last /M1
   opcode fetch. A joystick read whose `IN` was fetched from ROM `$2914` (with
   the home ROM mapped) is a BASIC `STICK` read. Anything else is a
   machine‑code read.
2. **BASIC passes.** The bus engine watches memory writes to PPC/SUBPPC
   (`5C45h`–`5C47h`). If the interpreter writes a line/statement at or before
   the position of the last `STICK` read, a new pass has started. The device
   updates the joystick lines **right then, before that pass's first read**,
   and holds them until the next boundary.
3. **Machine‑code polls.** Reads within about 1 ms of each other count as
   one poll (Draw 512 reads both sticks back to back). The lines are updated
   right after each poll.
4. **Using up steps.** At each boundary, every asserted direction takes
   `step` counts off its accumulator, and the lines are recomputed for the
   next pass. Accumulators are **capped** (start at ~0.5 s of passes), so the
   cursor stops when the mouse stops. BASIC programs only move about
   6–24 px/s.
5. **Hold modes** (per profile): *level* (most programs); *pulse* for
   auto‑repeat programs like Draw 512, where only a change of input steps
   immediately; *≥2 polls per step* for debounced programs like Multi‑Draw.
6. **Diagonals** can be turned off per profile (Multi‑Draw uses diagonals as
   menu commands).
7. **Buttons:** left → fire (pin 6), either held as a level or as a one‑pass
   pulse. The right button is a modifier for switching profiles and adjusting
   scale.

Profiles hold: scale (mouse counts per step), hold mode, diagonals on/off,
fire mode, backlog cap, Y polarity and which port(s) to drive. They live in
flash. The device picks *BASIC‑px* automatically when it sees ROM `STICK`
reads and *MC‑poll* otherwise. The survey lists the starting presets.

### Spectrum mode extra

When the 2068 runs Spectrum software (through an emulator cartridge), Kempston
joystick reads at `1Fh` can be served from the same accumulators. That makes
Spectrum joystick drawing programs work as well.

## ZXDesk 2068

Source: Jon Becker's [ts2068 repository](https://github.com/jon0x0/ts2068/tree/main/ZXDesk2068)
(MIT). In `src/zxdesk.asm`, `MouseInit` has an `IFDEF TS2068` block that
clears `MouseOn` and returns ("Native baseline uses keyboard and built-in
joysticks"). The Spectrum detection code after it is unchanged. So the clean
way to get mouse support is a build option that skips that early return
(something to suggest to Jon), not a binary patch.

From disassembling `examples/zxdesk2068.tap` (code loads at 27648, entry 33280),
which matches the source:

- The Kempston mouse detection (`$84AA`) and polling (`$8573`) code is all
  there. It reads `FBDF`/`FFDF`/`FADF`, reads each port twice, and limits each
  move to ±64.
- The 2068 port stubs out detection at `$84A5`: `xor a / ld ($B2D4),a / ret`.
  Changing the `RET` at **`$84A9`** to `NOP` lets execution fall through into
  the real detection code. This still needs testing. The `-512` build needs the
  same patch at a different address, which hasn't been located yet.
- Joystick entry points were redirected to `$A226`/`$A236`, which read AY
  register 14 with `BC = 03F6h` (both sticks selected).

## Open questions

1. 2068 expansion‑bus 5 V current budget for a card with a USB mouse.
2. Kempston Y polarity: confirm what ZXDesk expects with "Invert Y" off.
3. RP2350 5 V tolerance on the chosen module, or which buffers to use.
4. Does any 2068 hardware respond to undecoded port reads? If something
   drives the bus on `xxDFh` reads, the device would conflict with it.
   Test with a real machine.
5. ~~Survey of target legacy programs~~ Done in emulation, see
   [joystick-survey.md](joystick-survey.md). Still needs checking on real
   hardware.
6. Emulator to develop in before hardware: ZEsarUX (TS2068 + Kempston mouse)
   for native mode. Joystick emulation timing can only be checked on real
   hardware or a logic analyser.

## Sources

- TS2068 Technical Manual (2nd ed., Time Designs, 1986), §2.1.7, §2.1.13,
  §2.4.4: <https://k1.spdns.de/Vintage/Sinclair/82/Timex%20Sinclair%202068/Tech%20Specs%20and%20Repair/Timex%20Sinclair%202068%20-%20Technical%20Manual.pdf>
- Alvin Albrecht, TS2068 port map: <https://k1.spdns.de/Vintage/Sinclair/82/Timex%20Sinclair%202068/Tech%20Specs%20and%20Repair/port%20map.txt>
- Reading the Joysticks: <https://www.timexsinclair.com/article/reading-the-joysticks/index.html>
- TS2068 Joystick Operation: <https://www.timexsinclair.com/article/ts2068-joystick-operation/>
- Kempston Mouse Interface port decoding: <https://k1.spdns.de/Vintage/Sinclair/82/Peripherals/Mouse%20Interfaces/Kempston%20Mouse%20Interface>
- MAME Kempston mouse driver: <https://git.redump.net/mame/tree/src/devices/bus/spectrum/kempmouse.cpp>
- K‑Mouse Turbo docs (wheel extension, axis direction): <https://velesoft.speccy.cz/kmturbo2008-cz.htm>
