# FaderPort MCU Bridge

**Make your legacy PreSonus FaderPort work with any DAW.**

A lightweight MIDI bridge that translates the original PreSonus FaderPort's native protocol into Mackie Control Universal (MCU), enabling it to work with Logic Pro, Cubase, Ableton Live, Reaper, and any other MCU-compatible DAW.

> The original FaderPort (Classic, ~2008) uses a proprietary protocol and only officially supports Pro Tools and Studio One. PreSonus dropped support years ago. This bridge gives it a second life.

[![Download](https://img.shields.io/badge/Download-$4.99-blue?style=for-the-badge)](https://abrahamjeyaraj.gumroad.com/l/fjsbct)

![macOS menu bar](https://img.shields.io/badge/macOS-menu%20bar%20app-blue)
![Binary size](https://img.shields.io/badge/binary-115KB-green)
![Memory](https://img.shields.io/badge/RAM-~6MB-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## Features

- **Cross-DAW** — Works with Logic Pro, Cubase, and any MCU-compatible DAW
- **Motorized fader** — Bidirectional: moves when you switch tracks, sends position to DAW
- **Fader touch sense** — Motor stops when you touch the fader
- **Transport controls** — Play, Stop, Record, Rewind, Fast Forward, Loop
- **Track navigation** — Left/Right buttons navigate tracks one at a time
- **Pan encoder** — With debounce and direction hysteresis for the noisy encoder
- **Mute / Solo / Rec Arm** — Per-channel controls
- **Master fader mode** — Output button toggles between track and master fader
- **LED feedback** — DAW controls FaderPort button LEDs
- **Fader position caching** — Remembers positions for all 8 MCU channels
- **macOS menu bar app** — Runs silently in the background with a native tray icon
- **Tiny footprint** — 115KB binary, ~6MB RAM

## Supported Hardware

- **PreSonus FaderPort** (original/classic, single motorized fader, ~2008)
  - USB Vendor ID: `0x0194`, Product ID: `0x0001`
  - NOT the FaderPort V2, FaderPort 8, or FaderPort 16 (those have built-in MCU mode)

## Button Mapping

| FaderPort Button | MCU Function |
|---|---|
| **Fader** | Channel volume (motorized, bidirectional) |
| **Pan encoder** | V-Pot with debounce/hysteresis |
| **Play / Stop / Rewind / FFwd** | Transport |
| **Rec Enable** | Record |
| **Loop** | Cycle |
| **Mute / Solo / Rec** | Channel mute/solo/arm |
| **Left / Right** | Track navigation (1 track at a time) |
| **Shift+Left / Shift+Right** | Bank jump (8 tracks) |
| **Bank** | Bank Left (Shift+Bank = Bank Right) |
| **Output** | Toggle Master fader mode |
| **Undo** | Undo |
| **Mix** | Global View |
| **Proj** | Edit Channel Settings (Cubase) |
| **Trns** | Edit Instrument (Cubase) |
| **Punch** | Replace |

## Quick Start

### Install from DMG (recommended)

1. **Download** the DMG from [Gumroad](https://abrahamjeyaraj.gumroad.com/l/fjsbct)
2. **Open** the DMG and drag `FaderPortMCU` to a folder (e.g., `/Applications` or your Desktop)
3. **Copy** `librtmidi.7.dylib` to the **same folder** as `FaderPortMCU`
4. **Connect** your FaderPort Classic via USB
5. **Launch** `FaderPortMCU` — a mixer icon (☰) appears in your menu bar
6. If macOS blocks it: **System Settings > Privacy & Security > Open Anyway**

### Set up your DAW

**Logic Pro:**
1. Go to **Logic Pro > Control Surfaces > Setup**
2. Click **New > Install** → select **Mackie Control**
3. Set MIDI Input to **"FaderPort MCU"**
4. Set MIDI Output to **"FaderPort MCU"**

**Cubase:**
1. Go to **Studio > Studio Setup**
2. Click **+ Add Device** → select **Mackie Control**
3. Set MIDI Input to **"FaderPort MCU"**
4. Set MIDI Output to **"FaderPort MCU"**
5. Go to **MIDI Port Setup** → **uncheck** "In All MIDI Inputs" for both FaderPort MCU and FaderPort

**Other DAWs (Reaper, Ableton, etc.):**
- Add a Mackie Control / MCU control surface
- Set MIDI input and output to **"FaderPort MCU"**

> **Tip:** Start FaderPortMCU **before** opening your DAW for the smoothest connection.

### Build from source

```bash
cd cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(sysctl -n hw.ncpu)

# Menu bar app
./build/faderport_tray

# CLI version
./build/faderport_mcu_cli --verbose
```

## Building from Source

### Requirements

- C++17 compiler (Clang, GCC, MSVC)
- CMake 3.14+
- RtMidi (fetched automatically by CMake)

### macOS

```bash
cd cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(sysctl -n hw.ncpu)
```

Produces:
- `build/faderport_mcu_cli` — Command-line version
- `build/faderport_tray` — macOS menu bar app

## How It Works

```
┌──────────┐    Native Protocol     ┌──────────────┐   MCU Protocol    ┌──────────┐
│ FaderPort │ ◄── USB MIDI ───────► │  Bridge App  │ ◄─ Virtual MIDI ─► │   DAW    │
│ (Hardware)│                       │              │                    │          │
└──────────┘                        └──────────────┘                    └──────────┘
```

1. Connects to the physical FaderPort via USB MIDI
2. Sends SysEx handshake to enter native mode
3. Creates a virtual MIDI port ("FaderPort MCU") that speaks MCU
4. Translates messages bidirectionally in real-time

### Key Protocol Details

- FaderPort buttons send Aftertouch (`A0`) with `0x01`=press, `0x00`=release (not `0x7F`)
- Button press IDs differ from LED IDs (a PreSonus design quirk)
- Fader sends 14-bit CC#0+CC#32, receives 10-bit (asymmetric resolution)
- Pan encoder uses Pitch Bend, requires debouncing for noisy hardware
- MCU handshake supports both Logic (device query) and Cubase (identity request) patterns

## Protocol References

- [Mackie Control Protocol](https://github.com/NicoG60/TouchMCU/blob/main/doc/mackie_control_protocol.md)
- [Ardour FaderPort surface control](https://github.com/Ardour/ardour/tree/master/libs/surfaces/faderport)
- [PreSonus FaderPort Classic Packet Messaging](https://support.presonus.com/hc/en-us/articles/360005060871)

## License

MIT — see [LICENSE](LICENSE)

## Author

Abraham Jeyaraj
