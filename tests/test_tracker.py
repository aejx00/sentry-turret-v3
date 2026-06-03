"""Tests for FaceTracker and PIDController."""
import pytest
from src.vision.tracker import FaceTracker, PIDController
from src.config import FRAME_WIDTH, FRAME_HEIGHT


@pytest.fixture
def tracker():
    return FaceTracker()


def test_pid_proportional_response():
    pid = PIDController(kp=1.0, ki=0.0, kd=0.0)
    assert pid.compute(10.0) == pytest.approx(10.0)


def test_pid_accumulates_integral():
    pid = PIDController(kp=0.0, ki=1.0, kd=0.0)
    pid.compute(5.0)
    result = pid.compute(5.0)
    assert result == pytest.approx(10.0)


def test_pid_reset_clears_state():
    pid = PIDController(kp=0.0, ki=1.0, kd=0.0)
    pid.compute(100.0)
    pid.reset()
    assert pid.compute(0.0) == pytest.approx(0.0)


def test_compute_deltas_centred_face(tracker):
    cx, cy = FRAME_WIDTH // 2, FRAME_HEIGHT // 2
    # Face exactly at centre → very small delta
    face = (cx - 10, cy - 10, 20, 20)
    pan_d, tilt_d = tracker.compute_deltas(face)
    assert abs(pan_d) <= 2
    assert abs(tilt_d) <= 2


def test_acquired_when_centred(tracker):
    cx, cy = FRAME_WIDTH // 2, FRAME_HEIGHT // 2
    face = (cx - 5, cy - 5, 10, 10)
    tracker.compute_deltas(face)
    assert tracker.acquired


def test_not_acquired_when_off_centre(tracker):
    face = (0, 0, 50, 50)  # far top-left
    tracker.compute_deltas(face)
    assert not tracker.acquired


def test_largest_face_picks_biggest(tracker):
    faces = [(0, 0, 30, 30), (100, 100, 80, 80), (200, 200, 20, 20)]
    biggest = tracker.largest_face(faces)
    assert biggest == (100, 100, 80, 80)


def test_largest_face_none_when_empty(tracker):
    assert tracker.largest_face([]) is None
