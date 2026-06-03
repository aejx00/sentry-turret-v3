"""IMX477 HQ Camera — picamera2 (libcamera) primary, OpenCV V4L2 fallback."""
from __future__ import annotations

import threading
from typing import Optional
import numpy as np

from src.config import FRAME_WIDTH, FRAME_HEIGHT, FRAME_FPS
from src.utils.logging_config import get_logger

log = get_logger(__name__)


class Camera:
    """Thread-safe camera wrapper.

    Tries picamera2 first (required on Pi Bookworm with libcamera);
    falls back to OpenCV V4L2 on other platforms.
    Picamera2 is imported lazily so an ABI/import error does not crash
    the whole application at startup.
    """

    def __init__(self, index: int = 0) -> None:
        self._index = index
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._picam = None
        self._cap = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._try_start_picamera2():
            backend = "picamera2"
        else:
            self._start_opencv()
            backend = "opencv-v4l2"
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="camera-capture"
        )
        self._thread.start()
        log.info("Camera capture thread started (backend=%s)", backend)

    def stop(self) -> None:
        log.info("Stopping camera")
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._picam:
            self._picam.stop()
            self._picam.close()
            self._picam = None
        if self._cap:
            self._cap.release()
            self._cap = None

    # ------------------------------------------------------------------
    # Frame access
    # ------------------------------------------------------------------

    def get_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def read_jpeg(self, quality: int = 70) -> Optional[bytes]:
        import cv2

        frame = self.get_frame()
        if frame is None:
            return None
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes() if ok else None

    # ------------------------------------------------------------------
    # Backend init
    # ------------------------------------------------------------------

    def _try_start_picamera2(self) -> bool:
        try:
            from picamera2 import Picamera2
        except Exception as exc:
            log.warning("picamera2 unavailable (%s) — falling back to OpenCV V4L2", exc)
            return False

        log.info("Opening IMX477 via picamera2 at %dx%d@%d", FRAME_WIDTH, FRAME_HEIGHT, FRAME_FPS)
        try:
            self._picam = Picamera2()
            cfg = self._picam.create_video_configuration(
                main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "BGR888"},
                controls={"FrameRate": float(FRAME_FPS)},
            )
            self._picam.configure(cfg)
            self._picam.start()
            return True
        except Exception as exc:
            log.error("picamera2 init failed: %s", exc)
            self._picam = None
            return False

    def _start_opencv(self) -> None:
        import cv2

        log.info("Opening camera index=%d via OpenCV V4L2 at %dx%d@%d",
                 self._index, FRAME_WIDTH, FRAME_HEIGHT, FRAME_FPS)
        self._cap = cv2.VideoCapture(self._index, cv2.CAP_V4L2)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, FRAME_FPS)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera at index {self._index}")

    # ------------------------------------------------------------------
    # Capture loop
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        while self._running:
            frame = self._read_frame()
            if frame is None:
                continue
            with self._lock:
                self._latest_frame = frame

    def _read_frame(self) -> Optional[np.ndarray]:
        if self._picam is not None:
            try:
                return self._picam.capture_array("main")
            except Exception as exc:
                log.error("picamera2 capture error: %s", exc)
                return None
        if self._cap is not None:
            ret, frame = self._cap.read()
            if not ret:
                log.warning("Camera read failed — skipping frame")
                return None
            return frame
        return None
