"""
Entry point for the FaderPort-to-MCU bridge.

Usage:
    python -m faderport_mcu [--port HINT] [--list-ports] [--verbose]
"""

import argparse
import logging
import signal
import sys
import time

import rtmidi


def list_ports() -> None:
    """Print all available MIDI ports."""
    midi_in = rtmidi.MidiIn()
    midi_out = rtmidi.MidiOut()

    print("MIDI Input Ports:")
    for i, name in enumerate(midi_in.get_ports()):
        print(f"  [{i}] {name}")

    print("\nMIDI Output Ports:")
    for i, name in enumerate(midi_out.get_ports()):
        print(f"  [{i}] {name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FaderPort-to-MCU MIDI Bridge — "
                    "Makes the legacy PreSonus FaderPort work with Logic Pro, Cubase, etc."
    )
    parser.add_argument(
        "--port", default="FaderPort",
        help="Substring to match in MIDI port name (default: 'FaderPort')"
    )
    parser.add_argument(
        "--list-ports", action="store_true",
        help="List available MIDI ports and exit"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.list_ports:
        list_ports()
        return

    # Import here to avoid import errors if rtmidi is missing
    from .bridge import Bridge

    bridge = Bridge()

    # Clean shutdown on Ctrl+C
    def shutdown(signum, frame):
        print("\nShutting down...")
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("FaderPort MCU Bridge v0.1.0")
    print("=" * 40)

    if not bridge.start(port_hint=args.port):
        print("\nFailed to start bridge. Is the FaderPort connected?")
        print("Run with --list-ports to see available MIDI devices.")
        sys.exit(1)

    print(f"\nBridge active! Virtual MIDI port: 'FaderPort MCU'")
    print("In your DAW, select 'FaderPort MCU' as a Mackie Control surface.")
    print("Press Ctrl+C to stop.\n")

    # Keep alive — rtmidi callbacks run on background threads
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
