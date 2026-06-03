"""Fire control — mediates between state, relay and ammo counter."""
from __future__ import annotations

from typing import Optional

from src.config import MAGAZINE_CAPACITY
from src.control.state import FireMode, SystemState
from src.hardware.audio import AudioPlayer
from src.hardware.relay import FiringRelay
from src.utils.logging_config import get_logger

log = get_logger(__name__)


class FireController:
    def __init__(
        self,
        state: SystemState,
        relay: FiringRelay,
        audio: AudioPlayer,
        engagement_log=None,
    ) -> None:
        self._state = state
        self._relay = relay
        self._audio = audio
        self._log = engagement_log

    def attempt_fire(self) -> bool:
        """
        Attempt to fire.  Returns True if shots were fired.
        Checks: safety armed, ammo remaining.
        """
        if not self._state.armed:
            log.warning("Fire attempt denied — safety not armed")
            return False

        fire_mode = self._state.fire_mode
        shots_needed = self._shots_for_mode(fire_mode)
        full_mag = self._state.ammo == MAGAZINE_CAPACITY

        if not self._state.consume_ammo(shots_needed):
            log.warning("Out of ammo (%d needed, %d remaining)", shots_needed, self._state.ammo)
            self._audio.play("out_of_ammo")
            if self._log:
                target = self._state.target_name or "hostile"
                self._log.record(target, self._state.ammo, False, fire_mode.value)
            return False

        log.info("FIRING — mode=%s shots=%d ammo_remaining=%d", fire_mode.value, shots_needed, self._state.ammo)
        if full_mag:
            self._audio.play("engaging")

        self._state.is_firing = True

        if fire_mode == FireMode.SEMI:
            self._relay.fire_once()
        elif fire_mode == FireMode.BURST:
            self._relay.fire_burst()
        elif fire_mode == FireMode.FULL_AUTO:
            self._relay.fire_full_auto(shots_needed)

        self._state.is_firing = False
        self._state.record_fire()

        if self._log:
            target = self._state.target_name or "hostile"
            self._log.record(target, self._state.ammo, True, fire_mode.value)

        if self._state.ammo == 0:
            self._audio.play("out_of_ammo")

        return True

    def _shots_for_mode(self, mode: FireMode) -> int:
        from src.config import BURST_COUNT
        mapping = {
            FireMode.SEMI: 1,
            FireMode.BURST: BURST_COUNT,
            FireMode.FULL_AUTO: 1,
        }
        return mapping[mode]
