"""Tests for SystemState."""
import pytest
from src.control.state import FireMode, OperatingMode, SystemState
from src.config import MAGAZINE_CAPACITY


@pytest.fixture
def state():
    return SystemState()


def test_default_mode_is_manual(state):
    assert state.mode == OperatingMode.MANUAL


def test_default_not_armed(state):
    assert state.armed is False


def test_default_ammo_full(state):
    assert state.ammo == MAGAZINE_CAPACITY


def test_arm_disarm(state):
    state.armed = True
    assert state.armed is True
    state.armed = False
    assert state.armed is False


def test_consume_ammo_decrements(state):
    assert state.consume_ammo(1) is True
    assert state.ammo == MAGAZINE_CAPACITY - 1


def test_consume_ammo_fails_when_empty(state):
    state.consume_ammo(MAGAZINE_CAPACITY)
    assert state.consume_ammo(1) is False


def test_reload_refills(state):
    state.consume_ammo(4)
    state.reload()
    assert state.ammo == MAGAZINE_CAPACITY


def test_mode_switch(state):
    state.mode = OperatingMode.AUTONOMOUS
    assert state.mode == OperatingMode.AUTONOMOUS


def test_snapshot_contains_all_keys(state):
    snap = state.snapshot()
    for key in ("mode", "fire_mode", "armed", "ammo", "pan", "tilt", "target", "tracking"):
        assert key in snap


def test_fire_mode_switch(state):
    state.fire_mode = FireMode.BURST
    assert state.fire_mode == FireMode.BURST
