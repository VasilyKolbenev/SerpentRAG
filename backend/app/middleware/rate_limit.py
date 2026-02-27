"""
Application-level rate limiting middleware.

Uses in-memory sliding window counter per IP. Works without external dependencies.
For distributed deployments behind a load balancer, consider Redis-based rate limiting.

Default limits (per minute):
  /query, /query/stream   — 30 req/min
  /compare                — 10 req/min
  /advisor/chat           — 15 req/min
  /documents/upload       — 20 req/min
  everything else         — 60 req/min
"""

import logging
import time
from collections import defaultdict
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("serpent.rate_limit")

# path prefix → (max_requests, window_seconds)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/query/stream": (30, 60),
    "/api/query": (30, 60),
    "/api/compare": (10, 60),
    "/api/advisor/chat": (15, 60),
    "/api/documents/upload": (20, 60),
}

DEFAULT_LIMIT = (60, 60)  # 60 req/min


class _SlidingWindow:
    """Thread-safe sliding window rate limiter."""

    __slots__ = ("_buckets", "_window")

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._window = 300  # keep timestamps for max 5 min

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check and record a request. Returns True if allowed."""
        now = time.monotonic()
        cutoff = now - window_seconds
        timestamps = self._buckets[key]

        # Prune expired timestamps
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        if len(timestamps) >= max_requests:
            return False

        timestamps.append(now)

        # Periodic cleanup of stale keys (every ~100 checks)
        if len(self._buckets) > 10000:
            self._cleanup(now)

        return True

    def _cleanup(self, now: float) -> None:
        """Remove empty buckets to prevent memory growth."""
        cutoff = now - self._window
        stale = [k for k, v in self._buckets.items() if not v or v[-1] < cutoff]
        for k in stale:
            del self._buckets[k]


_limiter = _SlidingWindow()


def _get_client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For or direct connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _match_limit(path: str) -> tuple[int, int]:
    """Find the rate limit rule matching the request path."""
    for prefix, limit in RATE_LIMITS.items():
        if path.startswith(prefix):
            return limit
    return DEFAULT_LIMIT


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter per IP address."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Skip health check and static
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Only rate-limit mutating or expensive endpoints
        if method == "OPTIONS":
            return await call_next(request)

        client_ip = _get_client_ip(request)
        max_requests, window = _match_limit(path)
        key = f"{client_ip}:{path}"

        if not _limiter.is_allowed(key, max_requests, window):
            logger.warning(
                "Rate limit exceeded",
                extra={"client_ip": client_ip, "path": path},
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={"Retry-After": str(window)},
            )

        return await call_next(request)
