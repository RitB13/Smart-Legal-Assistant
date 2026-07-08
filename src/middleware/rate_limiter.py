"""
Simple in-memory IP-based rate limiter for auth endpoints.

Design:
- No external dependencies — uses only the Python standard library.
- Sliding window: tracks request timestamps per IP within a rolling time window.
- Thread-safe: uses threading.Lock (FastAPI runs with a thread pool for sync routes
  and an event loop for async routes; a plain Lock is safe in both cases).
- Automatic cleanup: entries are pruned on each check so memory stays bounded.

Usage (in app.py):
    from src.middleware.rate_limiter import RateLimiter
    rate_limiter = RateLimiter(max_requests=5, window_seconds=60)

    @app.post("/auth/login")
    async def login(request: Request, ...):
        rate_limiter.check(request)  # raises HTTP 429 if over limit
        ...
"""

import logging
from collections import defaultdict
from threading import Lock
from time import monotonic
from typing import Dict, List

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding-window rate limiter keyed by client IP address.

    Args:
        max_requests:   Maximum requests allowed per IP within the window.
        window_seconds: Length of the sliding window in seconds.
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract the real client IP, honouring X-Forwarded-For when present
        (set by nginx / cloud load balancers).
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def check(self, request: Request) -> None:
        """
        Check whether the request is within the rate limit.

        Raises:
            HTTPException 429 if the IP has exceeded the allowed request rate.
        """
        ip = self._get_client_ip(request)
        now = monotonic()
        window_start = now - self.window_seconds

        with self._lock:
            # Prune timestamps outside the current window
            self._store[ip] = [t for t in self._store[ip] if t > window_start]

            if len(self._store[ip]) >= self.max_requests:
                logger.warning(
                    f"[RATE_LIMIT] IP {ip} exceeded {self.max_requests} requests "
                    f"in {self.window_seconds}s — request blocked"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Too many requests. You may make at most {self.max_requests} "
                        f"requests per {self.window_seconds} seconds. "
                        "Please wait before trying again."
                    ),
                    headers={"Retry-After": str(self.window_seconds)},
                )

            self._store[ip].append(now)
