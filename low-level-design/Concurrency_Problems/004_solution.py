import threading
import time

# ============================================================
# FIX for SCARCITY ISSUE #4: threading.Semaphore
# ============================================================
#
# A Semaphore is a counter with two operations:
#   acquire() — wait until the counter is > 0, then decrement it
#   release() — increment the counter, waking a waiter if any
#
# Unlike a Lock (which allows only 1 holder), a Semaphore(N)
# allows up to N holders at a time — exactly the shape of "10
# connections shared by 100 requests". Threads blocked in
# acquire() sleep efficiently; they use no CPU while waiting.

POOL_SIZE = 10
NUM_REQUESTS = 100


class ConnectionPool:
    def __init__(self, size: int):
        self.connections = [f"conn-{i}" for i in range(size)]
        self.lock = threading.Lock()
        # One permit per physical connection.
        self.available = threading.Semaphore(size)

    def acquire(self) -> str:
        # Blocks here — with zero CPU usage — until a permit is
        # free. No spinning, no polling.
        self.available.acquire()
        with self.lock:
            return self.connections.pop()

    def release(self, conn: str):
        with self.lock:
            self.connections.append(conn)
        # Return the permit. If another thread is blocked in
        # acquire(), this wakes exactly one of them.
        self.available.release()


if __name__ == "__main__":
    pool = ConnectionPool(POOL_SIZE)
    active = 0
    max_active = 0
    active_lock = threading.Lock()

    def handle_request():
        global active, max_active
        conn = pool.acquire()

        with active_lock:
            active += 1
            max_active = max(max_active, active)

        time.sleep(0.05)  # simulate doing work with the connection

        with active_lock:
            active -= 1

        pool.release(conn)

    threads = [threading.Thread(target=handle_request) for _ in range(NUM_REQUESTS)]

    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - start

    print(f"pool size: {POOL_SIZE}, requests: {NUM_REQUESTS}")
    print(f"max concurrent connections in use: {max_active} (never exceeds {POOL_SIZE})")
    print(f"elapsed: {elapsed:.2f}s")
    print(
        "Same throttling guarantee as the busy-waiting version, "
        "but the 90 waiting requests were asleep, not spinning."
    )

    # NOTE: a plain Semaphore trusts every caller to release()
    # exactly once per acquire(). Release too many times (a bug,
    # e.g. a double release() on an exception path) and the
    # semaphore's internal counter goes above the real pool size,
    # silently letting more concurrent users in than you meant to
    # allow. threading.BoundedSemaphore raises a ValueError on that
    # extra release() instead of silently corrupting the limit —
    # prefer it whenever release() isn't trivially paired with
    # acquire() (e.g. it happens in a different function/thread).
