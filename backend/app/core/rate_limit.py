"""In-memory sliding-window rate limiter.

Keys (client addresses) live only in process memory, expire with the window,
and are never logged. A single-instance deployment is assumed; a shared store
(e.g. Redis) is needed for multiple replicas.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable

Clock = Callable[[], float]


class SlidingWindowLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float = 60.0,
        *,
        max_keys: int = 50_000,
        clock: Clock = time.monotonic,
    ) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.limit = limit
        self.window = window_seconds
        self.max_keys = max_keys
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> tuple[bool, int]:
        """Record a request. Returns ``(allowed, retry_after_seconds)``."""
        now = self._clock()
        cutoff = now - self.window
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                if len(self._hits) >= self.max_keys:
                    self._prune(cutoff)
                hits = deque()
                self._hits[key] = hits
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, math.ceil(hits[0] + self.window - now))
                return False, retry_after
            hits.append(now)
            return True, 0

    def _prune(self, cutoff: float) -> None:
        stale = [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]
        for key in stale:
            del self._hits[key]
        if len(self._hits) >= self.max_keys:
            # Still full: drop the oldest-active keys to bound memory.
            oldest = sorted(self._hits, key=lambda k: self._hits[k][-1])
            for key in oldest[: len(self._hits) - self.max_keys + 1]:
                del self._hits[key]
