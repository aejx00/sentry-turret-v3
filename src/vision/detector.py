"""Haar cascade face detector — optimised for Pi 4 performance."""
from __future__ import annotations

from typing import List, Tuple
import numpy as np

from src.config import (
    HAAR_CASCADE_PATH, FACE_SCALE_FACTOR,
    FACE_MIN_NEIGHBORS, FACE_MIN_SIZE,
)
from src.utils.logging_config import get_logger

log = get_logger(__name__)

FaceRect = Tuple[int, int, int, int]  # x, y, w, h


class FaceDetector:
    def __init__(self, cascade_path: str = HAAR_CASCADE_PATH) -> None:
        self._cascade_path = cascade_path
        self._classifier = None

    def start(self) -> None:
        import cv2

        self._classifier = cv2.CascadeClassifier(self._cascade_path)
        if self._classifier.empty():
            raise RuntimeError(f"Failed to load Haar cascade from {self._cascade_path}")
        log.info("Face detector loaded: %s", self._cascade_path)

    def detect(self, frame: np.ndarray) -> List[FaceRect]:
        import cv2

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)  # improves detection in variable lighting
        faces = self._classifier.detectMultiScale(
            gray,
            scaleFactor=FACE_SCALE_FACTOR,
            minNeighbors=FACE_MIN_NEIGHBORS,
            minSize=FACE_MIN_SIZE,
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        result: List[FaceRect] = []
        if len(faces):
            result = [tuple(f) for f in faces]  # type: ignore[misc]
        log.debug("Detected %d face(s)", len(result))
        return result

    def extract_roi(self, frame: np.ndarray, rect: FaceRect) -> np.ndarray:
        import cv2

        x, y, w, h = rect
        roi = frame[y:y + h, x:x + w]
        return cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
