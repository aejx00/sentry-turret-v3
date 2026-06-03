"""Autonomous engagement loop — detect → track → acquire → fire."""
from __future__ import annotations

import threading
import time
from typing import Optional

from src.config import PATROL_PAN_MAX, PATROL_PAN_MIN, PATROL_STEP, PATROL_TILT_CENTER
from src.control.fire_control import FireController
from src.control.state import FireMode, OperatingMode, SystemState
from src.hardware.audio import AudioPlayer
from src.hardware.camera import Camera
from src.hardware.servo import ServoController
from src.utils.logging_config import get_logger
from src.vision.detector import FaceDetector
from src.vision.recognizer import FaceRecognizer
from src.vision.tracker import FaceTracker

log = get_logger(__name__)

_LOOP_HZ = 15
_LOOP_SLEEP = 1.0 / _LOOP_HZ
# Haar cascades drop frames intermittently; require this many consecutive
# no-detection frames before declaring the target truly lost.
_LOST_FRAMES_THRESHOLD = 8


class AutonomousController:
    def __init__(
        self,
        state: SystemState,
        camera: Camera,
        servo: ServoController,
        detector: FaceDetector,
        recognizer: FaceRecognizer,
        tracker: FaceTracker,
        fire_ctrl: FireController,
        audio: AudioPlayer,
    ) -> None:
        self._state = state
        self._camera = camera
        self._servo = servo
        self._detector = detector
        self._recognizer = recognizer
        self._tracker = tracker
        self._fire_ctrl = fire_ctrl
        self._audio = audio

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._was_tracking = False
        self._lost_frames = 0
        self._patrol_dir = 1  # 1 = sweep right, -1 = sweep left

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="autonomous")
        self._thread.start()
        log.info("Autonomous controller started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        log.info("Autonomous controller stopped")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            start = time.monotonic()
            mode = self._state.mode
            if mode == OperatingMode.AUTONOMOUS:
                self._tick(patrol_sweep=False)
            elif mode == OperatingMode.PATROL:
                self._tick(patrol_sweep=True)
            elapsed = time.monotonic() - start
            time.sleep(max(0.0, _LOOP_SLEEP - elapsed))

    def _tick(self, patrol_sweep: bool) -> None:
        frame = self._camera.get_frame()
        if frame is None:
            return

        faces = self._detector.detect(frame)

        if not faces:
            self._lost_frames += 1
            if self._lost_frames >= _LOST_FRAMES_THRESHOLD and self._was_tracking:
                self._reset_tracking()
            if patrol_sweep:
                self._do_patrol_sweep()
            return

        self._lost_frames = 0

        # Classify every detected face
        hostile_faces = []
        safe_faces = []
        for rect in faces:
            roi = self._detector.extract_roi(frame, rect)
            name, conf = self._recognizer.predict(roi)
            if self._recognizer.is_safe(name):
                safe_faces.append((rect, name))
            else:
                hostile_faces.append((rect, name, conf))

        if not hostile_faces:
            # Only safe individuals visible
            self._state.tracking = True
            self._state.target_acquired = False
            self._state.target_rect = None
            self._state.target_name = safe_faces[0][1] if safe_faces else None
            self._was_tracking = True
            return

        # Pick the largest-area hostile face as primary target
        target_rect, target_name, target_conf = max(
            hostile_faces, key=lambda t: t[0][2] * t[0][3]
        )

        if not self._was_tracking:
            log.info("Hostile target detected (conf=%.1f) — engaging", target_conf)
            detect_sound = self._recognizer.get_detect_sound(target_name) or "targeting"
            self._audio.play(detect_sound)

        # Apply per-profile fire mode override
        profile_fm = self._recognizer.get_fire_mode(target_name)
        if profile_fm:
            try:
                self._state.fire_mode = FireMode(profile_fm)
            except ValueError:
                pass

        pan_d, tilt_d = self._tracker.compute_deltas(target_rect)
        self._servo.move(pan_d, tilt_d)
        pan, tilt = self._servo.position
        self._state.pan = pan
        self._state.tilt = tilt
        self._state.tracking = True
        self._state.target_acquired = self._tracker.acquired
        self._state.target_rect = target_rect
        self._state.target_name = target_name
        self._was_tracking = True

        if self._tracker.acquired and self._state.fire_ready:
            self._fire_ctrl.attempt_fire()

    def _do_patrol_sweep(self) -> None:
        pan, _ = self._servo.position
        new_pan = pan + PATROL_STEP * self._patrol_dir
        if new_pan >= PATROL_PAN_MAX:
            new_pan = PATROL_PAN_MAX
            self._patrol_dir = -1
        elif new_pan <= PATROL_PAN_MIN:
            new_pan = PATROL_PAN_MIN
            self._patrol_dir = 1
        self._servo.set_pan(new_pan)
        self._servo.set_tilt(PATROL_TILT_CENTER)
        self._state.pan = new_pan
        self._state.tilt = PATROL_TILT_CENTER

    def _reset_tracking(self) -> None:
        log.info("Target lost — mission complete")
        self._audio.play("mission_complete")
        self._tracker.reset()
        self._state.tracking = False
        self._state.target_acquired = False
        self._state.target_rect = None
        self._state.target_name = None
        self._was_tracking = False
