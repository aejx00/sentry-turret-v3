"""Tests for ServoController."""
import pytest
from src.hardware.servo import ServoController
from src.config import SERVO_CENTER, SERVO_MIN, SERVO_MAX


@pytest.fixture
def servo(mock_pca):
    ctrl = ServoController()
    ctrl._pca = mock_pca  # bypass hardware init
    ctrl._pan = SERVO_CENTER
    ctrl._tilt = SERVO_CENTER
    return ctrl


def test_initial_position_is_center(servo):
    assert servo.position == (SERVO_CENTER, SERVO_CENTER)


def test_set_pan_within_range(servo):
    servo.set_pan(400)
    assert servo.position[0] == 400


def test_set_tilt_within_range(servo):
    servo.set_tilt(300)
    assert servo.position[1] == 300


def test_pan_clamps_above_max(servo):
    servo.set_pan(SERVO_MAX + 100)
    assert servo.position[0] == SERVO_MAX


def test_pan_clamps_below_min(servo):
    servo.set_pan(SERVO_MIN - 50)
    assert servo.position[0] == SERVO_MIN


def test_tilt_clamps_above_max(servo):
    servo.set_tilt(SERVO_MAX + 1)
    assert servo.position[1] == SERVO_MAX


def test_move_adds_delta(servo):
    servo.set_pan(375)
    servo.set_tilt(375)
    servo.move(20, -20)
    assert servo.position == (395, 355)


def test_move_clamps_result(servo):
    servo.set_pan(SERVO_MAX - 5)
    servo.set_tilt(SERVO_MIN + 5)
    servo.move(100, -100)
    assert servo.position == (SERVO_MAX, SERVO_MIN)


def test_center_resets_position(servo):
    servo.set_pan(500)
    servo.set_tilt(200)
    servo.center()
    assert servo.position == (SERVO_CENTER, SERVO_CENTER)
