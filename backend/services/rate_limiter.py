from __future__ import annotations

import asyncio
from collections import deque

class AsyncRateLimiter:

    def __init__(self, max_calls: int = 12, period_seconds: float = 60.0) -> None:
        self.max_calls: int = max_calls
        self.period_seconds: float = period_seconds
        self._timestamps: deque[float] = deque()

    async def acquire(self) -> None:
        now = asyncio.get_event_loop().time()

        while self._timestamps and now - self._timestamps[0] > self.period_seconds:
            self._timestamps.popleft()

        if len(self._timestamps) >= self.max_calls:
            sleep_time = self.period_seconds - (now - self._timestamps[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        now = asyncio.get_event_loop().time()
        self._timestamps.append(now)
