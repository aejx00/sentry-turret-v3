"""Tests for FaceDetector."""
import numpy as np
import pytest
from src.vision.detector import FaceDetector


@pytest.fixture
def detector():
    d = FaceDetector()
    d.start()
    return d


def test_detect_returns_list(detector, blank_frame):
    faces = detector.detect(blank_frame)
    assert isinstance(faces, list)


def test_detect_returns_rects(detector, blank_frame):
    faces = detector.detect(blank_frame)
    assert len(faces) >= 1
    x, y, w, h = faces[0]
    assert all(isinstance(v, int) for v in (x, y, w, h))


def test_extract_roi_returns_grayscale(detector, blank_frame):
    rect = (50, 50, 80, 80)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    roi = detector.extract_roi(frame, rect)
    assert roi.ndim == 2  # grayscale

def test_detect_no_faces(detector, blank_frame):
    import sys
    cv2 = sys.modules["cv2"]
    import numpy as np
    cv2.CascadeClassifier.return_value.detectMultiScale.return_value = np.array([])
    faces = detector.detect(blank_frame)
    assert faces == []
    # restore
    cv2.CascadeClassifier.return_value.detectMultiScale.return_value = np.array([[100, 100, 80, 80]])
