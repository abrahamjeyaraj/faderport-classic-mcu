"""
Mackie Control Universal (MCU) virtual MIDI port handler.

Creates a virtual MIDI device that DAWs (Logic Pro, Cubase, etc.) can
connect to.  The DAW believes it is talking to a Mackie Control surface.

Responsibilities:
- Create virtual MIDI in/out ports ("FaderPort MCU")
- Send MCU messages to the DAW (button presses, fader, V-Pot, fader touch)
- Parse incoming MCU messages from the DAW (LED feedback, fader motor)
"""

import logging
from typing import Callable

import rtmidi

from .mappings import MCU_CC, MCU_NOTE_ON, MCU_PITCHBEND

log = logging.getLogger(__name__)

VIRTUAL_PORT_NAME = "FaderPort MCU"

# MCU SysEx manufacturer ID and device IDs
MCU_SYSEX_HEADER = [0xF0, 0x00, 0x00, 0x66, 0x14]  # Mackie Control main unit
MCU_SYSEX_END = 0xF7

# MCU SysEx command types
MCU_SYSEX_DEVICE_QUERY = 0x00       # Host → device: "are you there?"
MCU_SYSEX_HOST_CONNECTION = 0x01    # Host → device: connection request
MCU_SYSEX_HOST_CONN_REPLY = 0x02   # Device → host: connection reply
MCU_SYSEX_HOST_CONN_CONFIRM = 0x03 # Host → device: confirmed
MCU_SYSEX_VERSION_REPLY = 0x1B     # Device → host: version

# Serial number / challenge response (7 bytes — can be any values)
MCU_SERIAL = [0x46, 0x50, 0x4D, 0x43, 0x55, 0x30, 0x31]  # "FPMCU01" in ASCII


class McuPort:
    """Virtual MIDI port that speaks Mackie Control Universal protocol."""

    # Callbacks — set after construction
    on_led: Callable[[int, bool], None] | None = None       # (note, on)
    on_fader: Callable[[int, int], None] | None = None      # (channel, value_14bit)
    on_vpot_led: Callable[[int, int], None] | None = None   # (vpot_num, ring_value)
    on_display: Callable[[int, str], None] | None = None    # (position, text)

    def __init__(self) -> None:
        self._midi_in: rtmidi.MidiIn | None = None
        self._midi_out: rtmidi.MidiOut | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def open(self) -> bool:
        """Create the virtual MIDI ports."""
        try:
            self._midi_in = rtmidi.MidiIn()
            self._midi_in.open_virtual_port(VIRTUAL_PORT_NAME)
            self._midi_in.ignore_types(sysex=False, timing=True, active_sense=True)
            self._midi_in.set_callback(self._midi_callback)

            self._midi_out = rtmidi.MidiOut()
            self._midi_out.open_virtual_port(VIRTUAL_PORT_NAME)

            log.info("Virtual MIDI port '%s' created", VIRTUAL_PORT_NAME)

            # Initiate MCU handshake — some DAWs (Cubase) expect the
            # controller to send the Host Connection Query first
            self._initiate_handshake()

            return True
        except Exception:
            log.exception("Failed to create virtual MIDI port")
            return False

    def _initiate_handshake(self) -> None:
        """Send MCU Host Connection Query to the DAW.

        The MCU protocol handshake:
        1. Controller → Host: Host Connection Query (cmd 0x01) with serial number
        2. Host → Controller: Host Connection Reply (cmd 0x02) echoing serial
        3. Controller → Host: Host Connection Confirmation (cmd 0x03)
        """
        import time
        time.sleep(0.5)  # Give DAW time to set up its MIDI port
        query = MCU_SYSEX_HEADER + [0x01] + MCU_SERIAL + [MCU_SYSEX_END]
        log.info("Sending MCU Host Connection Query to DAW...")
        self._send(query)

    def close(self) -> None:
        """Close the virtual MIDI ports."""
        if self._midi_in:
            self._midi_in.close_port()
        if self._midi_out:
            self._midi_out.close_port()
        log.info("Virtual MIDI port closed")

    # ------------------------------------------------------------------
    # Output to DAW
    # ------------------------------------------------------------------

    def send_button(self, mcu_note: int, pressed: bool) -> None:
        """Send a button press/release to the DAW.

        MCU buttons are Note On, channel 1, velocity 7F (press) or 00 (release).
        """
        msg = [MCU_NOTE_ON, mcu_note & 0x7F, 0x7F if pressed else 0x00]
        log.info("MCU OUT button: note=0x%02X %s → %s",
                 mcu_note, "ON" if pressed else "OFF",
                 " ".join(f"{b:02X}" for b in msg))
        self._send(msg)

    def send_fader(self, channel: int, value_14bit: int) -> None:
        """Send a fader position to the DAW.

        MCU faders use Pitch Bend, one channel per fader.
        Channel 0 = fader 1, channel 8 = master fader.
        """
        value_14bit = max(0, min(16383, value_14bit))
        lsb = value_14bit & 0x7F
        msb = (value_14bit >> 7) & 0x7F
        self._send([MCU_PITCHBEND | (channel & 0x0F), lsb, msb])

    def send_fader_touch(self, channel: int, touched: bool) -> None:
        """Send fader touch/release to the DAW."""
        note = 0x68 + (channel & 0x07)
        self._send([MCU_NOTE_ON, note, 0x7F if touched else 0x00])

    def send_vpot(self, vpot_num: int, direction: int) -> None:
        """Send a V-Pot encoder turn to the DAW.

        Args:
            vpot_num: V-Pot index (0-7).
            direction: +1 for clockwise, -1 for counter-clockwise.
        """
        cc_num = 0x10 + (vpot_num & 0x07)
        value = 0x01 if direction > 0 else 0x41
        self._send([MCU_CC, cc_num, value])

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle_sysex(self, message: list[int]) -> None:
        """Respond to MCU SysEx handshake messages from the DAW."""
        # Universal Identity Request: F0 7E 7F 06 01 F7
        # Cubase and other DAWs send this first to discover the device
        if len(message) >= 6 and message[1:5] == [0x7E, 0x7F, 0x06, 0x01]:
            log.info("Universal Identity Request received — sending MCU identity")
            # Reply as Mackie Control: manufacturer 00 00 66, family 14 00, model 01 00
            identity = [
                0xF0, 0x7E, 0x7F, 0x06, 0x02,  # Identity Reply header
                0x00, 0x00, 0x66,                 # Manufacturer: Mackie
                0x14, 0x00,                       # Family: Mackie Control
                0x01, 0x00,                       # Model
                0x01, 0x00, 0x00, 0x00,           # Version
                0xF7
            ]
            self._send(identity)
            # Also send Host Connection Query to initiate MCU handshake
            import time
            time.sleep(0.1)
            query = MCU_SYSEX_HEADER + [0x01] + MCU_SERIAL + [MCU_SYSEX_END]
            log.info("Sending MCU Host Connection Query...")
            self._send(query)
            return

        # MCU-specific SysEx: F0 00 00 66 14 <cmd> ... F7
        if len(message) < 7:
            log.debug("SysEx too short: %s", [hex(b) for b in message])
            return

        # Check MCU header
        if message[1:5] != [0x00, 0x00, 0x66, 0x14]:
            log.debug("Non-MCU SysEx: %s", [hex(b) for b in message])
            return

        cmd = message[5]

        if cmd == MCU_SYSEX_DEVICE_QUERY:
            # Logic-style: Host asks "are you there?" → we respond with connection query
            log.info("MCU device query received — sending Host Connection Query")
            reply = MCU_SYSEX_HEADER + [0x01] + MCU_SERIAL + [MCU_SYSEX_END]
            self._send(reply)

        elif cmd == 0x01:
            # Host Connection Query from host (unusual but handle it)
            log.info("MCU Host Connection Query from DAW — sending reply")
            challenge = list(message[6:13]) if len(message) >= 13 else MCU_SERIAL
            reply = MCU_SYSEX_HEADER + [MCU_SYSEX_HOST_CONN_REPLY] + challenge + [MCU_SYSEX_END]
            self._send(reply)

        elif cmd == MCU_SYSEX_HOST_CONN_REPLY:
            # DAW replied to our Host Connection Query — send confirmation
            log.info("MCU Host Connection Reply received — sending confirmation")
            challenge = list(message[6:13]) if len(message) >= 13 else MCU_SERIAL
            reply = MCU_SYSEX_HEADER + [MCU_SYSEX_HOST_CONN_CONFIRM] + challenge + [MCU_SYSEX_END]
            self._send(reply)
            log.info("MCU handshake complete!")

        elif cmd == MCU_SYSEX_HOST_CONN_CONFIRM:
            log.info("MCU host connection confirmed by DAW!")

        elif cmd == 0x1A:
            # Version request — reply with version string
            log.info("MCU version request — sending version reply")
            version = [0x56, 0x31, 0x2E, 0x30]  # "V1.0"
            reply = MCU_SYSEX_HEADER + [MCU_SYSEX_VERSION_REPLY] + version + [MCU_SYSEX_END]
            self._send(reply)

        elif cmd == 0x12:
            # Display update: byte 6 = position, bytes 7+ = ASCII text
            if len(message) >= 8:
                position = message[6]
                text = "".join(chr(b) for b in message[7:-1] if 0x20 <= b < 0x7F)
                if self.on_display:
                    self.on_display(position, text)

        else:
            log.debug("MCU SysEx cmd 0x%02X: %s", cmd, [hex(b) for b in message])

    def _midi_callback(self, event: tuple, data: object = None) -> None:
        """Handle incoming MIDI from the DAW."""
        message, _delta_time = event
        if not message:
            return

        # Log ALL raw incoming MIDI from DAW
        log.debug("MCU RAW IN: %s", " ".join(f"{b:02X}" for b in message))

        status = message[0]

        # SysEx → MCU handshake
        if status == 0xF0:
            log.info("MCU SysEx IN: %s", " ".join(f"{b:02X}" for b in message))
            self._handle_sysex(list(message))
            return

        status_type = status & 0xF0
        channel = status & 0x0F

        # Note On → LED feedback
        if status_type == 0x90 and len(message) >= 3:
            note = message[1]
            velocity = message[2]
            if self.on_led:
                self.on_led(note, velocity > 0)
            return

        # Pitch Bend → fader motor command
        if status_type == 0xE0 and len(message) >= 3:
            value = (message[2] << 7) | message[1]
            if self.on_fader:
                self.on_fader(channel, value)
            return

        # CC → V-Pot LED ring (informational, could display on FP's LEDs)
        if status_type == 0xB0 and len(message) >= 3:
            cc_num = message[1]
            value = message[2]
            if 0x30 <= cc_num <= 0x37 and self.on_vpot_led:
                self.on_vpot_led(cc_num - 0x30, value)
            return

    def _send(self, message: list[int]) -> None:
        """Send a MIDI message to the DAW."""
        if self._midi_out:
            self._midi_out.send_message(message)
