# TS2068 Mouse

A mouse interface for the Timex/Sinclair 2068, at the design stage.

The plan is a single-microcontroller card on the expansion bus that does two jobs:

- **Joystick emulation** for existing programs that steer a cursor with the
  joystick (mainly drawing programs). The card drives the DB9 joystick ports
  and watches the bus, so it can line its steps up with each program's
  polling loop.
- **A Kempston-compatible mouse port** (`xxDF`) for new or patched software,
  such as Jon Becker's ZXDesk 2068 port. ZXDesk already contains a Kempston
  mouse driver that the 2068 build disables with a one-byte stub.

Nothing has been built yet.

## Contents

- [docs/architecture.md](docs/architecture.md) covers the hardware findings
  (joystick strobe, port decoding), block diagram, firmware design and ZXDesk notes.
- [docs/joystick-survey.md](docs/joystick-survey.md) measures how 11 TS2068
  drawing programs read the joystick, and proposes the default
  joystick-emulation profiles.
- [tools/joytrace](tools/joytrace/) holds the ZEsarUX scripts used for the
  survey. They log every joystick read a program makes.

## Test software

`examples/` is where the ZXDesk 2068 TAP files go for local testing. They are
Jon Becker's software and aren't included in this repository.
