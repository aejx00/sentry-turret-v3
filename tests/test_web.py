"""Tests for FastAPI web endpoints."""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.control.state import FireMode, OperatingMode, SystemState
from src.web.app import create_app


@pytest.fixture
def client():
    state      = SystemState()
    camera     = MagicMock()
    camera.get_frame.return_value = None
    servo      = MagicMock()
    servo.position = (375, 375)
    detector   = MagicMock()
    detector.detect.return_value = []
    recognizer = MagicMock()
    recognizer.list_profiles.return_value = ["Alice"]
    fire_ctrl  = MagicMock()
    fire_ctrl.attempt_fire.return_value = True
    audio      = MagicMock()
    audio.muted = False

    app = create_app(state, camera, servo, detector, recognizer, fire_ctrl, audio)
    return TestClient(app, raise_server_exceptions=True), state, servo, fire_ctrl, audio


def test_index_returns_200(client):
    c, *_ = client
    r = c.get("/")
    assert r.status_code == 200


def test_status_endpoint(client):
    c, state, *_ = client
    r = c.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert "mode" in data
    assert "armed" in data
    assert "ammo" in data


def test_set_mode_autonomous(client):
    c, state, *_ = client
    r = c.post("/api/mode", data={"mode": "autonomous"})
    assert r.status_code == 200
    assert state.mode == OperatingMode.AUTONOMOUS


def test_set_mode_invalid(client):
    c, *_ = client
    r = c.post("/api/mode", data={"mode": "invalid"})
    assert r.status_code == 400


def test_arm_endpoint(client):
    c, state, _, _, audio = client
    r = c.post("/api/arm")
    assert r.status_code == 200
    assert state.armed is True
    audio.play.assert_called_with("armed")


def test_disarm_endpoint(client):
    c, state, _, _, audio = client
    state.armed = True
    r = c.post("/api/disarm")
    assert r.status_code == 200
    assert state.armed is False
    audio.play.assert_called_with("disarmed")


def test_fire_endpoint_blocked_without_arm(client):
    c, state, _, fire_ctrl, _ = client
    fire_ctrl.attempt_fire.return_value = False
    r = c.post("/api/fire")
    assert r.status_code == 200
    assert r.json()["fired"] is False


def test_reload_endpoint(client):
    c, state, *_ = client
    state.consume_ammo(4)
    r = c.post("/api/reload")
    assert r.status_code == 200
    from src.config import MAGAZINE_CAPACITY
    assert r.json()["ammo"] == MAGAZINE_CAPACITY


def test_pan_tilt_endpoint(client):
    c, state, servo, *_ = client
    r = c.post("/api/pan_tilt", data={"pan": "400", "tilt": "300"})
    assert r.status_code == 200
    servo.set_pan.assert_called_with(400)
    servo.set_tilt.assert_called_with(300)


def test_set_fire_mode(client):
    c, state, *_ = client
    r = c.post("/api/fire_mode", data={"fire_mode": "burst"})
    assert r.status_code == 200
    assert state.fire_mode == FireMode.BURST


def test_register_page(client):
    c, *_ = client
    r = c.get("/register")
    assert r.status_code == 200
    assert b"Alice" in r.content
