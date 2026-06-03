"""Thread-safe rolling engagement log."""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import List

MAX_LOG_ENTRIES = 100


@dataclass
class EngagementEntry:
    timestamp: str
    target: str
    ammo_remaining: int
    fired: bool
    fire_mode: str


class EngagementLog:
    def __init__(self, maxlen: int = MAX_LOG_ENTRIES) -> None:
        self._lock = threading.Lock()
        self._entries: deque = deque(maxlen=maxlen)

    def record(self, target: str, ammo_remaining: int, fired: bool, fire_mode: str) -> None:
        entry = EngagementEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            target=target,
            ammo_remaining=ammo_remaining,
            fired=fired,
            fire_mode=fire_mode,
        )
        with self._lock:
            self._entries.appendleft(entry)

    def to_list(self) -> List[dict]:
        with self._lock:
            return [
                {
                    "timestamp": e.timestamp,
                    "target": e.target,
                    "ammo": e.ammo_remaining,
                    "fired": e.fired,
                    "mode": e.fire_mode,
                }
                for e in self._entries
            ]
