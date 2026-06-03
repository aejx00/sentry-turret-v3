"""Shared, thread-safe system state."""
from __future__ import annotations

import json
import os
import threading
import time
from enum import Enum
from typing import Optional, Tuple

from src.config import AMMO_PERSIST_PATH, FIRE_COOLDOWN, MAGAZINE_CAPACITY
from src.utils.logging_config import get_logger

log = get_logger(__name__)


class OperatingMode(str, Enum):
    AUTONOMOUS = "autonomous"
    MANUAL = "manual"
    REGISTRATION = "registration"
    PATROL = "patrol"


class FireMode(str, Enum):
    SEMI = "semi"
    BURST = "burst"
    FULL_AUTO = "full_auto"


class SystemState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mode = OperatingMode.MANUAL
        self._fire_mode = FireMode.SEMI
        self._armed = False
        self._ammo = MAGAZINE_CAPACITY
        self._pan = 375
        self._tilt = 375
        self._target_name: Optional[str] = None
        self._tracking = False
        self._target_acquired = False
        self._is_firing = False
        self._target_rect: Optional[Tuple[int, int, int, int]] = None
        self._last_fire_time: float = 0.0
        self._fire_cooldown: float = FIRE_COOLDOWN

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    @property
    def mode(self) -> OperatingMode:
        with self._lock:
            return self._mode

    @mode.setter
    def mode(self, value: OperatingMode) -> None:
        with self._lock:
            self._mode = value

    # ------------------------------------------------------------------
    # Fire mode
    # ------------------------------------------------------------------

    @property
    def fire_mode(self) -> FireMode:
        with self._lock:
            return self._fire_mode

    @fire_mode.setter
    def fire_mode(self, value: FireMode) -> None:
        with self._lock:
            self._fire_mode = value

    # ------------------------------------------------------------------
    # Safety arm
    # ------------------------------------------------------------------

    @property
    def armed(self) -> bool:
        with self._lock:
            return self._armed

    @armed.setter
    def armed(self, value: bool) -> None:
        with self._lock:
            self._armed = value

    # ------------------------------------------------------------------
    # Ammo
    # ------------------------------------------------------------------

    @property
    def ammo(self) -> int:
        with self._lock:
            return self._ammo

    def consume_ammo(self, count: int = 1) -> bool:
        with self._lock:
            if self._ammo < count:
                return False
            self._ammo -= count
            return True

    def reload(self) -> None:
        with self._lock:
            self._ammo = MAGAZINE_CAPACITY

    def save_ammo(self) -> None:
        try:
            os.makedirs(os.path.dirname(AMMO_PERSIST_PATH), exist_ok=True)
            with open(AMMO_PERSIST_PATH, "w") as f:
                json.dump({"ammo": self._ammo}, f)
            log.debug("Ammo state saved: %d", self._ammo)
        except Exception as exc:
            log.warning("Could not save ammo state: %s", exc)

    def load_ammo(self) -> None:
        try:
            with open(AMMO_PERSIST_PATH) as f:
                data = json.load(f)
            ammo = int(data.get("ammo", MAGAZINE_CAPACITY))
            with self._lock:
                self._ammo = max(0, min(ammo, MAGAZINE_CAPACITY))
            log.info("Restored ammo count: %d", self._ammo)
        except FileNotFoundError:
            log.info("No ammo persist file — starting with full magazine")
        except Exception as exc:
            log.warning("Could not load ammo state: %s", exc)

    # ------------------------------------------------------------------
    # Servo position
    # ------------------------------------------------------------------

    @property
    def pan(self) -> int:
        with self._lock:
            return self._pan

    @pan.setter
    def pan(self, value: int) -> None:
        with self._lock:
            self._pan = value

    @property
    def tilt(self) -> int:
        with self._lock:
            return self._tilt

    @tilt.setter
    def tilt(self, value: int) -> None:
        with self._lock:
            self._tilt = value

    # ------------------------------------------------------------------
    # Target tracking
    # ------------------------------------------------------------------

    @property
    def target_name(self) -> Optional[str]:
        with self._lock:
            return self._target_name

    @target_name.setter
    def target_name(self, value: Optional[str]) -> None:
        with self._lock:
            self._target_name = value

    @property
    def tracking(self) -> bool:
        with self._lock:
            return self._tracking

    @tracking.setter
    def tracking(self, value: bool) -> None:
        with self._lock:
            self._tracking = value

    @property
    def target_acquired(self) -> bool:
        with self._lock:
            return self._target_acquired

    @target_acquired.setter
    def target_acquired(self, value: bool) -> None:
        with self._lock:
            self._target_acquired = value

    @property
    def is_firing(self) -> bool:
        with self._lock:
            return self._is_firing

    @is_firing.setter
    def is_firing(self, value: bool) -> None:
        with self._lock:
            self._is_firing = value

    @property
    def target_rect(self) -> Optional[Tuple[int, int, int, int]]:
        with self._lock:
            return self._target_rect

    @target_rect.setter
    def target_rect(self, value: Optional[Tuple[int, int, int, int]]) -> None:
        with self._lock:
            self._target_rect = value

    # ------------------------------------------------------------------
    # Fire cooldown
    # ------------------------------------------------------------------

    def record_fire(self) -> None:
        with self._lock:
            self._last_fire_time = time.monotonic()

    @property
    def fire_ready(self) -> bool:
        with self._lock:
            return time.monotonic() - self._last_fire_time >= self._fire_cooldown

    @property
    def cooldown_remaining(self) -> float:
        with self._lock:
            return max(0.0, self._fire_cooldown - (time.monotonic() - self._last_fire_time))

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "mode": self._mode.value,
                "fire_mode": self._fire_mode.value,
                "armed": self._armed,
                "ammo": self._ammo,
                "pan": self._pan,
                "tilt": self._tilt,
                "target": self._target_name,
                "tracking": self._tracking,
                "target_acquired": self._target_acquired,
                "is_firing": self._is_firing,
                "cooldown_remaining": round(
                    max(0.0, self._fire_cooldown - (time.monotonic() - self._last_fire_time)), 1
                ),
            }
