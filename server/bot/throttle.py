"""Simple in-memory per-user rate limiter for bot code lookups."""

import time
from collections import defaultdict


class RateLimiter:
    """Allow at most `limit` calls per `window_seconds` per user_id."""

    def __init__(self, limit: int = 5, window_seconds: float = 60.0) -> None:
        self._limit = limit
        self._window = window_seconds
        self._timestamps: dict[int, list[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        ts = self._timestamps[user_id]
        # Remove timestamps outside the window
        self._timestamps[user_id] = [t for t in ts if t > cutoff]
        if len(self._timestamps[user_id]) >= self._limit:
            return False
        self._timestamps[user_id].append(now)
        return True
