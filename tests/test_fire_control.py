"""Tests for FireController."""
import pytest
from unittest.mock import MagicMock
from src.control.fire_control import FireController
from src.control.state import FireMode, SystemState
from src.config import MAGAZINE_CAPACITY


@pytest.fixture
def mocks():
    state  = SystemState()
    relay  = MagicMock()
    audio  = MagicMock()
    return state, relay, audio


@pytest.fixture
def fc(mocks):
    state, relay, audio = mocks
    return FireController(state, relay, audio), state, relay, audio


def test_fire_blocked_when_not_armed(fc):
    ctrl, state, relay, _ = fc
    state.armed = False
    assert ctrl.attempt_fire() is False
    relay.fire_once.assert_not_called()


def test_fire_works_when_armed(fc):
    ctrl, state, relay, _ = fc
    state.armed = True
    assert ctrl.attempt_fire() is True
    relay.fire_once.assert_called_once()


def test_engaging_sound_plays_only_on_full_magazine(fc):
    ctrl, state, relay, audio = fc
    state.armed = True
    ctrl.attempt_fire()  # first shot — full mag
    audio.play.assert_called_with("engaging")
    audio.reset_mock()
    ctrl.attempt_fire()  # second shot — not full mag
    engaging_calls = [c for c in audio.play.call_args_list if c.args == ("engaging",)]
    assert len(engaging_calls) == 0


def test_engaging_sound_plays_again_after_reload(fc):
    ctrl, state, relay, audio = fc
    state.armed = True
    ctrl.attempt_fire()  # depletes one
    state.reload()
    audio.reset_mock()
    ctrl.attempt_fire()  # full mag again
    audio.play.assert_called_with("engaging")


def test_fire_consumes_ammo(fc):
    ctrl, state, relay, _ = fc
    state.armed = True
    ctrl.attempt_fire()
    assert state.ammo == MAGAZINE_CAPACITY - 1


def test_fire_blocked_when_out_of_ammo(fc):
    ctrl, state, relay, audio = fc
    state.armed = True
    state.consume_ammo(MAGAZINE_CAPACITY)
    assert ctrl.attempt_fire() is False
    relay.fire_once.assert_not_called()
    audio.play.assert_called_with("out_of_ammo")


def test_burst_mode_fires_burst(fc):
    ctrl, state, relay, _ = fc
    state.armed = True
    state.fire_mode = FireMode.BURST
    ctrl.attempt_fire()
    relay.fire_burst.assert_called_once()


def test_out_of_ammo_plays_sound(fc):
    ctrl, state, relay, audio = fc
    state.armed = True
    state.consume_ammo(MAGAZINE_CAPACITY - 1)  # 1 left
    ctrl.attempt_fire()
    audio.play.assert_any_call("out_of_ammo")
