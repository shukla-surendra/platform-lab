"""Single-instance distributed lock: SET key value NX PX ttl acquires
the lock atomically (NX = only if absent, PX = auto-expiring, so a
crashed holder can't wedge the lock forever). Release is a
compare-and-delete via a Lua script, not a plain DEL - see the comment
below for why that distinction is the entire point.

This is the single-Redis-instance version. See this repo's
../../../fundamentals/system_design_foundation/00_prerequisite_concepts/25_redis_as_a_system_design_primitive.md
for why the multi-instance version (Redlock) is genuinely contested,
and why a fencing token is the fix production systems actually reach
for instead of trusting mutual exclusion on the lock alone.

Run against a Redis instance reachable at REDIS_HOST/REDIS_PORT:
    python3 distributed_lock.py
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

# Only deletes the key if its value still matches the token we set -
# without this check, holder A could time out, holder B could acquire
# the same lock, and then A's delayed release would delete B's live
# lock. Must run as a single atomic Lua script, not a
# GET-then-compare-then-DEL from Python, or the same race reappears one
# level up.
_RELEASE_SCRIPT = r.register_script(
    """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    else
        return 0
    end
    """
)


def acquire_lock(name: str, ttl_ms: int = 5000) -> str | None:
    token = uuid.uuid4().hex
    acquired = r.set(f"lock:{name}", token, nx=True, px=ttl_ms)
    return token if acquired else None


def release_lock(name: str, token: str) -> bool:
    return bool(_RELEASE_SCRIPT(keys=[f"lock:{name}"], args=[token]))


if __name__ == "__main__":
    r.delete("lock:job-42")

    token_a = acquire_lock("job-42")
    print(f"holder A acquired: {token_a is not None}")

    token_b = acquire_lock("job-42")
    print(f"holder B acquired while A holds it: {token_b is not None}  (must be False)")
    assert token_b is None

    # Holder B correctly can't release a lock it never held.
    released_wrong = release_lock("job-42", "not-a-real-token")
    print(f"holder B releasing with the WRONG token: {released_wrong}  (must be False)")
    assert not released_wrong

    released_right = release_lock("job-42", token_a)
    print(f"holder A releasing with its OWN token: {released_right}  (must be True)")
    assert released_right

    token_c = acquire_lock("job-42")
    print(f"holder C acquires after A released: {token_c is not None}  (must be True)")
    assert token_c is not None

    print("\ndistributed lock confirmed working")
