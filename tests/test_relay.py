"""Tests for FiringRelay."""
import pytest
from unittest.mock import MagicMock, call
from src.hardware.relay import FiringRelay
from src.config import RELAY_PIN


@pytest.fixture
def gpio():
    g = MagicMock()
    g.BCM = 11
    g.IN = 1
    g.OUT = 0
    return g


@pytest.fixture
def relay(gpio):
    r = FiringRelay(gpio_module=gpio)
    r._gpio.setmode(r._gpio.BCM)
    r._gpio.setup(RELAY_PIN, r._gpio.IN)
    return r


def test_start_sets_pin_as_input(gpio):
    r = FiringRelay(gpio_module=gpio)
    r.start()
    gpio.setup.assert_called_with(RELAY_PIN, gpio.IN)


def test_fire_once_pulses_output_then_input(relay, gpio):
    relay.fire_once()
    calls = gpio.setup.call_args_list
    output_call = call(RELAY_PIN, gpio.OUT)
    input_call  = call(RELAY_PIN, gpio.IN)
    assert output_call in calls
    assert input_call  in calls


def test_fire_burst_fires_burst_count_times(relay, gpio):
    from src.config import BURST_COUNT
    relay.fire_burst()
    output_calls = [c for c in gpio.setup.call_args_list if c == call(RELAY_PIN, gpio.OUT)]
    assert len(output_calls) == BURST_COUNT


def test_stop_releases_pin(relay, gpio):
    relay.stop()
    gpio.setup.assert_called_with(RELAY_PIN, gpio.IN)
    gpio.cleanup.assert_called_with(RELAY_PIN)
