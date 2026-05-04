# ASI

A collection of Python test and control tools developed at ASI. This repo should remain private, as a personal reference for past work.

---

## Projects

### Relay Tester

*Version 1.0*

A Tkinter GUI application for cycling an ONTRAK relay device (Line Reactor Runner). Configurable ON/OFF durations, number of cycles, and relay output selection (K0/K1). Useful for endurance and life testing of line reactor relays.

**Key features:**
- Connect/disconnect to ONTRAK USB relay
- Set ON duration, OFF duration, and total cycle count
- Visual status indicators per relay output
- Runs test in a background thread with interrupt support

**Configuration:** `Relay Tester/config.ini` (geometry, font size)

---

### Timber Production Tester

*Version 1.0*

A Tkinter GUI application for automating Timber Motor Production Validation. Communicates with two ASI controllers (DUT and BRK) over TTL serial to run a standardised production test sequence and log results to CSV.

**Test sequence:**
1. Connect to DUT & BRK controllers
2. Pre-test motor discovery (modes 1 & 2)
3. Unloaded run
4. Loaded rundown
5. Post-test motor discovery (modes 1 & 2)
6. Disconnect

**Key features:**
- Configurable pass/fail windows for motor discovery, unloaded run, and rundown
- Configurable 5-minute test timeout
- Results logged to `Timber Production Summary [Date].csv`
- Supports firmware 6.014–6.026; additional firmware dictionaries can be added to `TimberProductionTester/Dictionary/`

**Configuration:** `TimberProductionTester/config.ini` (COM ports, save destination, pass/fail windows, test parameters)

See [`TimberProductionTester/README.md`](TimberProductionTester/README.md) for full details.

---

### Dyno v2

*Version 0.7.2*

A Tkinter GUI controller for the ASI DynoModule — a dynamometer test bench. Interfaces with an ASI motor controller (CAN/TTL), a Yokogawa WT1806 power analyser, and an ABB ACS800 drive used as the brake load. Supports scripted test runs, live plotting, and email alerts.

**Key features:**
- CAN communication via PCAN (PCANBasic)
- ABB ACS800 brake drive control
- Yokogawa WT1806 power meter integration
- PID-based load control (`simple_pid`)
- Live data plotting with matplotlib (2D & 3D / tricontour maps)
- Rolling log files (`logs/std-*.log`)
- Dockerised environment (`Dockerfile`)
- Scripted test support (`dyno-v2/dyno_v2/TestScript/`)
- XML-based ASI object dictionary and ABB parameter files

**Configuration:** `dyno-v2/config.ini`
