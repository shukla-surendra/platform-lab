"""Sliding-window rate limiter using a sorted set: each request is a
member scored by its own timestamp, so counting requests in the last
N seconds is a single ZREMRANGEBYSCORE (evict anything older than the
window) followed by a ZCARD (count what's left).

Run against a Redis instance reachable at REDIS_HOST/REDIS_PORT:
    python3 sliding_window_rate_limiter.py
"""

import os
import time
import uuid

import redis

r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    decode_responses=True,
)

WINDOW_SECONDS = 10
MAX_REQUESTS = 3


def allow_request(user_id: str) -> bool:
    key = f"ratelimit:{user_id}"
    now = time.time()
    window_start = now - WINDOW_SECONDS

    # Evict anything that has aged out of the window, then count what's
    # left - both against the SAME key, so this stays correct even
    # under concurrent callers (each caller's ZADD is its own atomic op).
    r.zremrangebyscore(key, "-inf", window_start)
    current_count = r.zcard(key)

    if current_count >= MAX_REQUESTS:
        return False

    # A unique member per request (timestamp isn't unique enough alone -
    # two requests in the same millisecond would collide and only count
    # as one entry in the set).
    r.zadd(key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
    r.expire(key, WINDOW_SECONDS)  # let Redis clean up an idle key entirely
    return True


if __name__ == "__main__":
    user = "demo-user"
    r.delete(f"ratelimit:{user}")

    print(f"limit: {MAX_REQUESTS} requests per {WINDOW_SECONDS}s\n")
    for i in range(1, 6):
        allowed = allow_request(user)
        status = "ALLOWED" if allowed else "REJECTED (over limit)"
        print(f"  request {i}: {status}")

    assert not allow_request(user), "6th request should still be rejected"
    print("\nrate limiter confirmed working")
