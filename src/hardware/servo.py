"""PCA9685 PWM servo driver — pan/tilt control."""
from __future__ import annotations

import threading
from src.config import (
    PCA9685_ADDRESS, PCA9685_FREQUENCY,
    SERVO_PAN_CHANNEL, SERVO_TILT_CHANNEL,
    SERVO_CENTER, SERVO_MIN, SERVO_MAX,
)
from src.utils.logging_config import get_logger

log = get_logger(__name__)


class ServoController:
    """Controls pan (ch0) and tilt (ch1) via PCA9685 at I2C 0x40."""

    def __init__(self, i2c_bus=None) -> None:
        self._lock = threading.Lock()
        self._pan = SERVO_CENTER
        self._tilt = SERVO_CENTER
        self._pca = None
        self._i2c_bus = i2c_bus  # injected for testing

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        import board
        import busio
        from adafruit_pca9685 import PCA9685

        log.info("Initialising PCA9685 at I2C 0x%02X, freq=%dHz", PCA9685_ADDRESS, PCA9685_FREQUENCY)
        i2c = self._i2c_bus or busio.I2C(board.SCL, board.SDA)
        self._pca = PCA9685(i2c, address=PCA9685_ADDRESS)
        self._pca.frequency = PCA9685_FREQUENCY
        self.center()

    def stop(self) -> None:
        log.info("Centering servos and stopping PCA9685")
        self.center()
        if self._pca:
            self._pca.deinit()
            self._pca = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def center(self) -> None:
        self._set(SERVO_PAN_CHANNEL, SERVO_CENTER)
        self._set(SERVO_TILT_CHANNEL, SERVO_CENTER)
        with self._lock:
            self._pan = SERVO_CENTER
            self._tilt = SERVO_CENTER
        log.debug("Servos centred at PWM %d", SERVO_CENTER)

    def set_pan(self, value: int) -> None:
        value = self._clamp(value)
        with self._lock:
            self._pan = value
        self._set(SERVO_PAN_CHANNEL, value)
        log.debug("Pan → %d", value)

    def set_tilt(self, value: int) -> None:
        value = self._clamp(value)
        with self._lock:
            self._tilt = value
        self._set(SERVO_TILT_CHANNEL, value)
        log.debug("Tilt → %d", value)

    def move(self, pan_delta: int, tilt_delta: int) -> None:
        with self._lock:
            new_pan = self._clamp(self._pan + pan_delta)
            new_tilt = self._clamp(self._tilt + tilt_delta)
        self.set_pan(new_pan)
        self.set_tilt(new_tilt)

    @property
    def position(self) -> tuple[int, int]:
        with self._lock:
            return self._pan, self._tilt

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clamp(self, value: int) -> int:
        clamped = max(SERVO_MIN, min(SERVO_MAX, value))
        if clamped != value:
            log.warning("PWM %d out of range [%d, %d] — clamped to %d", value, SERVO_MIN, SERVO_MAX, clamped)
        return clamped

    def _set(self, channel: int, pwm: int) -> None:
        if self._pca is None:
            return
        # PCA9685 duty cycle: value / 4096 of 20ms period
        self._pca.channels[channel].duty_cycle = int(pwm * 65535 / 4096)
