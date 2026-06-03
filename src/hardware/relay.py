"""GPIO firing relay — GPIO 21 BCM with input/output toggle workaround."""
from __future__ import annotations

import threading
import time
from src.config import RELAY_PIN, SEMI_AUTO_DELAY, FULL_AUTO_DELAY, BURST_COUNT
from src.utils.logging_config import get_logger

log = get_logger(__name__)

# The relay hardware requires toggling the pin between OUTPUT (fires) and
# INPUT (idle) rather than driving HIGH/LOW, due to a hardware quirk on
# this specific relay module.
_FIRE_MODE = "OUTPUT"
_IDLE_MODE = "INPUT"


class FiringRelay:
    """Controls the dart firing relay on GPIO 21 (BCM)."""

    def __init__(self, gpio_module=None) -> None:
        self._gpio = gpio_module  # injected for testing
        self._lock = threading.Lock()
        self._firing = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._gpio is None:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
        log.info("Setting up relay on GPIO BCM %d", RELAY_PIN)
        self._gpio.setmode(self._gpio.BCM)
        self._gpio.setup(RELAY_PIN, self._gpio.IN)  # start idle

    def stop(self) -> None:
        log.info("Releasing relay GPIO")
        if self._gpio:
            self._gpio.setup(RELAY_PIN, self._gpio.IN)
            self._gpio.cleanup(RELAY_PIN)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fire_once(self) -> None:
        """Fire a single dart (semi-auto)."""
        with self._lock:
            self._pulse()

    def fire_burst(self) -> None:
        """Fire a burst of BURST_COUNT darts."""
        with self._lock:
            for _ in range(BURST_COUNT):
                self._pulse()
                time.sleep(SEMI_AUTO_DELAY)

    def fire_full_auto(self, shots: int) -> None:
        """Fire continuously for `shots` rounds."""
        with self._lock:
            for _ in range(shots):
                self._pulse()
                time.sleep(FULL_AUTO_DELAY)

    @property
    def is_firing(self) -> bool:
        return self._firing

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _pulse(self) -> None:
        """Toggle pin to OUTPUT (fire) then back to INPUT (idle)."""
        log.debug("Relay pulse: OUTPUT → INPUT")
        self._firing = True
        self._gpio.setup(RELAY_PIN, self._gpio.OUT)
        time.sleep(0.05)
        self._gpio.setup(RELAY_PIN, self._gpio.IN)
        self._firing = False
