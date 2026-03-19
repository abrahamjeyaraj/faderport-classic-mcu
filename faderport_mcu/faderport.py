"""
Native FaderPort protocol handler.

Manages the real MIDI connection to the physical FaderPort hardware:
- Device discovery and connection
- SysEx initialization handshake → native mode activation
- Parsing incoming MIDI (buttons, fader, encoder, fader touch)
- Sending LED commands and fader motor positions
"""

import logging
import time
from typing import Callable

import rtmidi

from .mappings import (
    ALL_LED_IDS,
    FP_AFTERTOUCH,
    FP_CC,
    FP_PITCHBEND,
    FP_BTN_FADERTOUCH,
    NATIVE_MODE_ON,
    SYSEX_INQUIRY,
)

log = logging.getLogger(__name__)


class FaderPort:
    """Interface to the physical PreSonus FaderPort (original/legacy)."""

    # Callbacks — set these after construction
    on_button: Callable[[int, bool], None] | None = None
    on_fader: Callable[[int], None] | None = None           # 14-bit value
    on_encoder: Callable[[int], None] | None = None         # raw pitch bend
    on_fader_touch: Callable[[bool], None] | None = None

    def __init__(self) -> None:
        self._midi_in: rtmidi.MidiIn | None = None
        self._midi_out: rtmidi.MidiOut | None = None
        self._fader_msb: int = 0
        self._connected = False

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, port_name_hint: str = "FaderPort") -> bool:
        """Find and connect to the FaderPort MIDI ports."""
        self._midi_in = rtmidi.MidiIn()
        self._midi_out = rtmidi.MidiOut()

        in_port = self._find_port(self._midi_in, port_name_hint)
        out_port = self._find_port(self._midi_out, port_name_hint)

        if in_port is None or out_port is None:
            log.error("FaderPort not found. Available ports:")
            for i, name in enumerate(self._midi_in.get_ports()):
                log.error("  IN  [%d] %s", i, name)
            for i, name in enumerate(self._midi_out.get_ports()):
                log.error("  OUT [%d] %s", i, name)
            return False

        log.info("Opening FaderPort IN port %d, OUT port %d", in_port, out_port)
        self._midi_in.open_port(in_port)
        self._midi_out.open_port(out_port)

        # Allow SysEx messages through
        self._midi_in.ignore_types(sysex=False, timing=True, active_sense=True)

        # Register the callback
        self._midi_in.set_callback(self._midi_callback)

        self._connected = True
        return True

    def disconnect(self) -> None:
        """Clean up MIDI connections."""
        if self._connected:
            self._all_leds_off()
            # Send native mode off (velocity 0)
            self._send([0x91, 0x00, 0x00])
        if self._midi_in:
            self._midi_in.close_port()
        if self._midi_out:
            self._midi_out.close_port()
        self._connected = False
        log.info("FaderPort disconnected")

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Perform the SysEx handshake and enter native mode."""
        if not self._connected:
            return

        log.info("Sending SysEx device inquiry...")
        self._send(SYSEX_INQUIRY)
        time.sleep(0.1)  # Give device time to respond

        log.info("Activating native mode...")
        self._send(NATIVE_MODE_ON)
        time.sleep(0.05)

        self._all_leds_off()
        log.info("FaderPort initialized in native mode")

    # ------------------------------------------------------------------
    # Output: LEDs and fader motor
    # ------------------------------------------------------------------

    def set_led(self, led_id: int, on: bool) -> None:
        """Turn a FaderPort LED on or off.

        Args:
            led_id: The LED identifier (from FP_PRESS_TO_LED mapping).
            on: True to light, False to extinguish.
        """
        self._send([FP_AFTERTOUCH, led_id & 0x7F, 0x01 if on else 0x00])

    def set_fader(self, value_14bit: int) -> None:
        """Move the motorized fader to a position.

        The FaderPort accepts 10-bit resolution (0-1023) via CC#0 + CC#32.
        Input is 14-bit (0-16383) and will be scaled down.
        """
        value_10 = (value_14bit * 1023) // 16383
        msb = (value_10 >> 7) & 0x7F
        lsb = value_10 & 0x7F
        # Must send as two separate messages (per Ardour source)
        self._send([FP_CC, 0x00, msb])
        self._send([FP_CC, 0x20, lsb])

    # ------------------------------------------------------------------
    # Internal MIDI handling
    # ------------------------------------------------------------------

    def _midi_callback(self, event: tuple, data: object = None) -> None:
        """Called by rtmidi on the background thread for each incoming message."""
        message, _delta_time = event
        if not message:
            return

        status = message[0]
        status_type = status & 0xF0  # Strip channel bits

        # Log ALL raw incoming MIDI
        log.debug("FP RAW IN: %s", " ".join(f"{b:02X}" for b in message))

        # SysEx — identity reply (informational, we don't gate on it)
        if status == 0xF0:
            log.info("FP SysEx: %s", " ".join(f"{b:02X}" for b in message))
            return

        # Aftertouch → button press/release or fader touch
        if status_type == 0xA0 and len(message) >= 3:
            note = message[1]
            value = message[2]

            if note == FP_BTN_FADERTOUCH:
                touched = value > 0
                log.info("FP fader touch: %s (raw=0x%02X)", "TOUCH" if touched else "RELEASE", value)
                if self.on_fader_touch:
                    self.on_fader_touch(touched)
            else:
                pressed = value > 0
                log.info("FP button %d: %s (raw=0x%02X)", note, "PRESS" if pressed else "RELEASE", value)
                if self.on_button:
                    self.on_button(note, pressed)
            return

        # CC → fader position (14-bit across CC#0 and CC#32)
        if status_type == 0xB0 and len(message) >= 3:
            cc_num = message[1]
            value = message[2]

            if cc_num == 0x00:
                self._fader_msb = value
            elif cc_num == 0x20:
                full_value = (self._fader_msb << 7) | value
                if self.on_fader:
                    self.on_fader(full_value)
            else:
                log.debug("FP CC#%d = %d (unhandled)", cc_num, value)
            return

        # Pitch Bend → pan encoder
        if status_type == 0xE0 and len(message) >= 3:
            pb_value = (message[2] << 7) | message[1]
            if self.on_encoder:
                self.on_encoder(pb_value)
            return

        log.debug("FP unhandled status: 0x%02X", status)

    def _send(self, message: list[int]) -> None:
        """Send a MIDI message to the FaderPort."""
        if self._midi_out:
            self._midi_out.send_message(message)

    def _all_leds_off(self) -> None:
        """Turn off every LED on the FaderPort."""
        for led_id in ALL_LED_IDS:
            self.set_led(led_id, False)

    @staticmethod
    def _find_port(midi_io: rtmidi.MidiIn | rtmidi.MidiOut,
                   hint: str) -> int | None:
        """Find a MIDI port whose name contains the hint string."""
        hint_lower = hint.lower()
        for i, name in enumerate(midi_io.get_ports()):
            if hint_lower in name.lower():
                return i
        return None
