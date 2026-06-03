"""USB speaker WAV playback — plays random clip from state-mapped subdirectory."""
from __future__ import annotations

import os
import random
import subprocess
import threading
from src.config import AUDIO_BASE_DIR, AUDIO_STATE_DIRS
from src.utils.logging_config import get_logger

log = get_logger(__name__)


class AudioPlayer:
    """Plays random WAV files for system state events (non-blocking)."""

    def __init__(self) -> None:
        self._muted = False

    @property
    def muted(self) -> bool:
        return self._muted

    def toggle_mute(self) -> bool:
        self._muted = not self._muted
        log.info("Audio %s", "muted" if self._muted else "unmuted")
        return self._muted

    def play(self, state: str) -> None:
        if self._muted:
            log.debug("Audio muted — skipping state '%s'", state)
            return
        subdir = AUDIO_STATE_DIRS.get(state)
        if not subdir:
            log.warning("Unknown audio state: %s", state)
            return
        path = os.path.join(AUDIO_BASE_DIR, subdir)
        wavs = [f for f in os.listdir(path) if f.lower().endswith(".wav")] if os.path.isdir(path) else []
        if not wavs:
            log.debug("No WAV files found in %s", path)
            return
        chosen = os.path.join(path, random.choice(wavs))
        log.info("Playing audio [%s]: %s", state, chosen)
        threading.Thread(target=self._play, args=(chosen,), daemon=True, name=f"audio-{state}").start()

    def _play(self, filepath: str) -> None:
        try:
            subprocess.run(["aplay", filepath], check=True, capture_output=True)
        except FileNotFoundError:
            log.warning("aplay not found — cannot play %s", filepath)
        except subprocess.CalledProcessError as exc:
            log.error("aplay failed for %s: %s", filepath, exc.stderr)
