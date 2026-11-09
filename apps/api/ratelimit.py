"""In-process sliding-window rate limit keyed by client IP (Cloudflare's CF-Connecting-IP when present).

One API process on one box is the deployment, so in-memory is honest here. With more replicas this
moves to Redis (INCR + EXPIRE), which is already in docker-compose.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from resolve.config import get_settings

_hits: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "unknown")


def client_hash(request: Request) -> str:
    salt = get_settings().ip_hash_salt
    return hashlib.sha256((salt + client_ip(request)).encode()).hexdigest()[:16]


def limit(request: Request, per_minute: int | None = None, bucket: str = "default") -> None:
    per_minute = per_minute or get_settings().rate_limit_per_minute
    key = f"{bucket}:{client_ip(request)}"
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= per_minute:
        raise HTTPException(429, "rate limited; try again in a minute", headers={"Retry-After": "60"})
    q.append(now)
