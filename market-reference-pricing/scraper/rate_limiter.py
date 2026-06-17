import time
import threading
from collections import deque


class RateLimiter:
    """
    Thread-safe sliding-window rate limiter, scoped per domain.
    Default: 5 requests / 60-second window (configurable).
    """

    def __init__(self, requests_per_minute: int = 5):
        self.requests_per_minute = requests_per_minute
        self._lock = threading.Lock()
        self._timestamps: dict[str, deque] = {}

    def wait(self, domain: str) -> None:
        """Block until a new request to `domain` is within the rate limit, then register it."""
        while True:
            sleep_for = 0.0
            with self._lock:
                now = time.monotonic()
                window = 60.0

                if domain not in self._timestamps:
                    self._timestamps[domain] = deque()

                ts = self._timestamps[domain]
                # Expire records outside the rolling window
                while ts and now - ts[0] >= window:
                    ts.popleft()

                if len(ts) < self.requests_per_minute:
                    ts.append(now)
                    return  # Within budget — caller may proceed

                # Must wait until the oldest request exits the window
                sleep_for = window - (now - ts[0]) + 0.05

            time.sleep(sleep_for)  # Release lock while sleeping
