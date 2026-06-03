"""PID-style face tracker — computes servo deltas to centre target in frame."""
from __future__ import annotations

from typing import Optional, Tuple
import numpy as np

from src.config import (
    FRAME_WIDTH, FRAME_HEIGHT,
    SERVO_CENTER, SERVO_MIN, SERVO_MAX,
    PID_KP, PID_KI, PID_KD,
)
from src.utils.logging_config import get_logger

log = get_logger(__name__)

FaceRect = Tuple[int, int, int, int]


class PIDController:
    def __init__(self, kp: float = PID_KP, ki: float = PID_KI, kd: float = PID_KD) -> None:
        self.kp, self.ki, self.kd = kp, ki, kd
        self._integral = 0.0
        self._prev_error = 0.0

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, error: float) -> float:
        self._integral += error
        derivative = error - self._prev_error
        self._prev_error = error
        return self.kp * error + self.ki * self._integral + self.kd * derivative


class FaceTracker:
    """Converts face rect → servo PWM adjustments via two PID controllers."""

    def __init__(self) -> None:
        self._pan_pid = PIDController()
        self._tilt_pid = PIDController()
        self._cx = FRAME_WIDTH // 2
        self._cy = FRAME_HEIGHT // 2
        self._acquired = False

    def reset(self) -> None:
        self._pan_pid.reset()
        self._tilt_pid.reset()
        self._acquired = False

    @property
    def acquired(self) -> bool:
        return self._acquired

    def compute_deltas(self, face: FaceRect) -> Tuple[int, int]:
        """Return (pan_delta, tilt_delta) PWM integers to move towards face centre."""
        x, y, w, h = face
        face_cx = x + w // 2
        face_cy = y + h // 2

        error_x = face_cx - self._cx   # positive → face is right → increase PWM → pan right
        error_y = self._cy - face_cy   # positive → face is above → tilt up

        pan_delta = int(self._pan_pid.compute(error_x))
        tilt_delta = int(self._tilt_pid.compute(error_y))

        if abs(error_x) < 15 and abs(error_y) < 15:
            if not self._acquired:
                self._acquired = True
                log.info("Target acquired — centred (err_x=%d, err_y=%d)", error_x, error_y)
        else:
            self._acquired = False

        log.debug("Tracker err=(%d,%d) → delta=(%d,%d)", error_x, error_y, pan_delta, tilt_delta)
        return pan_delta, tilt_delta

    def largest_face(self, faces: list) -> Optional[FaceRect]:
        if not faces:
            return None
        return max(faces, key=lambda r: r[2] * r[3])
