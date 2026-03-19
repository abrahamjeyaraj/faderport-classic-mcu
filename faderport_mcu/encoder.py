"""
Pan encoder debounce and direction hysteresis filter.

The FaderPort's rotary encoder is notoriously noisy — it frequently sends
spurious direction changes and burst events.  This filter (derived from
Ardour's approach) applies:

1. Time-based debounce: reject events within 10 ms of the last accepted event.
2. Direction hysteresis: within a 100 ms window, require 3 consecutive deltas
   in the new direction before accepting a direction change.
"""

import time


class EncoderFilter:
    DEBOUNCE_S = 0.010        # 10 ms minimum between accepted events
    HYSTERESIS_WINDOW_S = 0.100  # 100 ms window for direction change
    HYSTERESIS_COUNT = 3      # consecutive same-direction events to confirm

    def __init__(self) -> None:
        self._last_time: float = 0.0
        self._last_direction: int = 0   # +1 CW, -1 CCW
        self._consecutive: int = 0
        self._window_start: float = 0.0

    def process(self, pitch_bend_value: int) -> int | None:
        """Process a raw pitch-bend value from the encoder.

        Args:
            pitch_bend_value: 14-bit MIDI pitch bend (0-16383).
                              < 8192 → clockwise, >= 8192 → counter-clockwise.

        Returns:
            +1 for clockwise, -1 for counter-clockwise, or None if rejected.
        """
        now = time.monotonic()

        # Debounce: reject if too soon after last accepted event
        if (now - self._last_time) < self.DEBOUNCE_S:
            return None

        # Determine direction
        direction = -1 if pitch_bend_value >= 8192 else 1

        # Same direction as last accepted → accept immediately
        if direction == self._last_direction:
            self._last_time = now
            return direction

        # Direction changed — apply hysteresis
        if (now - self._window_start) > self.HYSTERESIS_WINDOW_S:
            # Start a new hysteresis window
            self._window_start = now
            self._consecutive = 1
            return None

        # Within the window, count consecutive same-direction events
        self._consecutive += 1
        if self._consecutive >= self.HYSTERESIS_COUNT:
            # Confirmed direction change
            self._last_direction = direction
            self._last_time = now
            self._consecutive = 0
            return direction

        return None
