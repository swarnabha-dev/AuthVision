import time
from typing import Dict
from threading import Lock

# Simple in-memory rate limiter. Not distributed; ok for single-process dev.
class RateLimiter:
    def __init__(self, calls: int = 60, period: int = 60):
        self.calls = calls
        self.period = period
        self.storage: Dict[str, list] = {}
        self.lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self.lock:
            q = self.storage.setdefault(key, [])
            # pop outdated
            while q and q[0] <= now - self.period:
                q.pop(0)
            if len(q) >= self.calls:
                return False
            q.append(now)
            return True


default_limiter = RateLimiter(calls=60, period=60)

def require_rate_limit(key: str):
    def _inner():
        if not default_limiter.allow(key):
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="Too many requests")

    return _inner
