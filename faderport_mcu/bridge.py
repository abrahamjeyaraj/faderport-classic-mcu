"""
Bridge orchestrator — wires the FaderPort and MCU virtual port together,
translating messages bidirectionally.
"""

import logging

from .encoder import EncoderFilter
from .faderport import FaderPort
from .mappings import (
    FP_BTN_BANK,
    FP_BTN_OUTPUT,
    FP_BTN_SHIFT,
    FP_PRESS_TO_LED,
    FP_SHIFT_TO_MCU,
    FP_TO_MCU,
    FP_TO_MCU_BANK_DEFAULT,
    MCU_CURSOR_DOWN,
    MCU_CURSOR_UP,
    MCU_TO_FP_LED,
)
from .mcu import McuPort

log = logging.getLogger(__name__)


class Bridge:
    """Bidirectional translator between FaderPort native protocol and MCU."""

    def __init__(self) -> None:
        self.fp = FaderPort()
        self.mcu = McuPort()
        self.encoder_filter = EncoderFilter()

        # Modifier state
        self._shift_held = False
        self._fader_touched = False
        self._master_mode = False  # Output: fader controls master ch9

        # MCU Select LEDs (0x18-0x1F) tell us which channel is selected
        self._selected_channel = 0  # 0-7, tracks which MCU channel is active
        self.MASTER_CHANNEL = 8

        # Cache fader positions for all 9 MCU channels (0-7 + master)
        # None = unknown (don't move fader), int = known position
        self._fader_cache: list[int | None] = [None] * 9

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, port_hint: str = "FaderPort") -> bool:
        """Connect to hardware, create virtual port, wire callbacks."""
        if not self.fp.connect(port_hint):
            return False
        if not self.mcu.open():
            self.fp.disconnect()
            return False

        # Wire FaderPort → MCU callbacks
        self.fp.on_button = self._fp_button
        self.fp.on_fader = self._fp_fader
        self.fp.on_encoder = self._fp_encoder
        self.fp.on_fader_touch = self._fp_fader_touch

        # Wire MCU → FaderPort callbacks
        self.mcu.on_led = self._mcu_led
        self.mcu.on_fader = self._mcu_fader

        # Initialize FaderPort into native mode
        self.fp.initialize()

        # Request fader positions from DAW by sending touch/release for all channels
        # This makes the DAW send back current fader values to populate our cache
        import time
        time.sleep(1.0)  # Wait for DAW handshake to complete
        log.info("Requesting initial fader positions from DAW...")
        for ch in range(9):  # channels 0-7 + master (8)
            self.mcu.send_fader_touch(ch, True)
            time.sleep(0.02)
            self.mcu.send_fader_touch(ch, False)
            time.sleep(0.02)

        log.info("Bridge started — FaderPort ↔ MCU translation active")
        return True

    def stop(self) -> None:
        """Shut down cleanly."""
        self.fp.disconnect()
        self.mcu.close()
        log.info("Bridge stopped")

    # ------------------------------------------------------------------
    # FaderPort → MCU  (hardware → DAW)
    # ------------------------------------------------------------------

    def _fp_button(self, press_id: int, pressed: bool) -> None:
        """Translate a FaderPort button event to MCU."""
        # Track Shift state
        if press_id == FP_BTN_SHIFT:
            self._shift_held = pressed
            log.debug("Shift %s", "held" if pressed else "released")
            return  # Shift is not forwarded to the DAW

        # Output button = toggle master fader mode
        # Fader instantly controls Master (MCU ch9) without scrolling.
        # Press again to return fader to current track.
        if press_id == FP_BTN_OUTPUT:
            if not pressed:
                return
            self._master_mode = not self._master_mode
            output_led = FP_PRESS_TO_LED.get(FP_BTN_OUTPUT)
            if output_led is not None:
                self.fp.set_led(output_led, self._master_mode)
            log.info("Master mode %s — fader controls %s",
                     "ON" if self._master_mode else "OFF",
                     "Master" if self._master_mode else "current track")
            return

        # Check shift-modified mappings first
        if self._shift_held and press_id in FP_SHIFT_TO_MCU:
            mcu_note = FP_SHIFT_TO_MCU[press_id]
            log.debug("FP btn %d (shifted) → MCU note 0x%02X %s",
                      press_id, mcu_note, "ON" if pressed else "OFF")
            self.mcu.send_button(mcu_note, pressed)
            return

        # Bank button default (unshifted)
        if press_id == FP_BTN_BANK:
            log.debug("FP Bank → MCU Bank Left %s", "ON" if pressed else "OFF")
            self.mcu.send_button(FP_TO_MCU_BANK_DEFAULT, pressed)
            return

        # Standard button mapping
        mcu_note = FP_TO_MCU.get(press_id)
        if mcu_note is not None:
            log.debug("FP btn %d → MCU note 0x%02X %s",
                      press_id, mcu_note, "ON" if pressed else "OFF")
            self.mcu.send_button(mcu_note, pressed)

        else:
            log.debug("FP btn %d has no MCU mapping (ignored)", press_id)

    @property
    def _active_channel(self) -> int:
        """Return the MCU channel the fader is currently controlling."""
        return self.MASTER_CHANNEL if self._master_mode else self._selected_channel

    def _fp_fader(self, value_14bit: int) -> None:
        """Forward fader position to DAW as MCU Pitch Bend."""
        self.mcu.send_fader(self._active_channel, value_14bit)

    def _fp_encoder(self, pitch_bend_raw: int) -> None:
        """Filter and forward encoder rotation as MCU V-Pot CC."""
        direction = self.encoder_filter.process(pitch_bend_raw)
        if direction is not None:
            self.mcu.send_vpot(0, direction)

    def _fp_fader_touch(self, touched: bool) -> None:
        """Forward fader touch state to DAW."""
        self._fader_touched = touched
        ch = self._active_channel
        self.mcu.send_fader_touch(ch, touched)
        log.debug("Fader %s (ch %d)", "touched" if touched else "released", ch)

    # ------------------------------------------------------------------
    # MCU → FaderPort  (DAW → hardware)
    # ------------------------------------------------------------------

    def _mcu_led(self, mcu_note: int, on: bool) -> None:
        """Translate MCU LED command to FaderPort LED."""
        # Track Select button LEDs (0x18-0x1F) to know selected channel
        if 0x18 <= mcu_note <= 0x1F and on:
            old_ch = self._selected_channel
            self._selected_channel = mcu_note - 0x18
            if self._selected_channel != old_ch:
                log.info("Selected channel changed: %d → %d",
                         old_ch, self._selected_channel)
                # Move physical fader to cached position of new channel
                if not self._master_mode and not self._fader_touched:
                    cached = self._fader_cache[self._selected_channel]
                    if cached is not None:
                        self.fp.set_fader(cached)
                        log.info("Fader moved to cached position %d for ch %d",
                                 cached, self._selected_channel)
                    else:
                        log.info("No cached position for ch %d (waiting for DAW)",
                                 self._selected_channel)

        led_id = MCU_TO_FP_LED.get(mcu_note)
        if led_id is not None:
            self.fp.set_led(led_id, on)
            log.debug("MCU LED 0x%02X → FP LED %d %s",
                      mcu_note, led_id, "ON" if on else "OFF")
        else:
            log.debug("MCU LED 0x%02X has no FP LED mapping (ignored)", mcu_note)

    def _mcu_fader(self, channel: int, value_14bit: int) -> None:
        """Cache fader position and move physical fader if it's the active channel."""
        # Cache the position for this channel
        if 0 <= channel <= 8:
            self._fader_cache[channel] = value_14bit

        # Only move the physical fader if this is the active channel
        active = self._active_channel
        if channel != active:
            return

        if self._fader_touched:
            log.debug("Fader motor suppressed (user touching fader)")
            return

        self.fp.set_fader(value_14bit)
