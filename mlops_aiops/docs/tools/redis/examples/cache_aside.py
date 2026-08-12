"""Cache-aside pattern: check the cache first, fall through to the
"slow" source on a miss, populate the cache before returning.

Run against a Redis instance reachable at REDIS_HOST/REDIS_PORT:
    python3 cache_aside.py
"""

import os
import time

import redis

r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    decode_responses=True,
)

CACHE_TTL_SECONDS = 30


def slow_lookup(user_id: int) -> str:
    """Stands in for a slow database call or network fetch."""
    time.sleep(0.3)
    return f"user-{user_id}-profile-data"


def get_user_profile(user_id: int) -> str:
    cache_key = f"cache:user:{user_id}"

    cached = r.get(cache_key)
    if cached is not None:
        print(f"  HIT  {cache_key}")
        return cached

    print(f"  MISS {cache_key} -> falling through to slow_lookup()")
    value = slow_lookup(user_id)
    r.set(cache_key, value, ex=CACHE_TTL_SECONDS)
    return value


if __name__ == "__main__":
    r.delete("cache:user:42")  # start clean for the demo

    start = time.monotonic()
    get_user_profile(42)  # miss - pays the slow_lookup cost
    first = time.monotonic() - start

    start = time.monotonic()
    get_user_profile(42)  # hit - served straight from Redis
    second = time.monotonic() - start

    print(f"\nfirst call (miss): {first:.3f}s")
    print(f"second call (hit): {second:.3f}s")
    assert second < first / 2, "the cached call should be dramatically faster"
    print("cache-aside pattern confirmed working")
