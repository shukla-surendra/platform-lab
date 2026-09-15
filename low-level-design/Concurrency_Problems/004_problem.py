import threading
import time

# ============================================================
# SCARCITY ISSUE #4: Busy-Waiting for a Limited Resource
# ============================================================
#
# You have 10 database connections but 100 concurrent requests
# want one. At most 10 requests can be "in flight" at a time; the
# other 90 must wait their turn.
#
# This version never hands out more connections than exist — that
# part is correct — but the way requests wait for a free connection
# is wasteful: they spin in a loop, repeatedly re-checking for a
# free connection instead of sleeping until one is released.

POOL_SIZE = 10
NUM_REQUESTS = 100

spin_iterations = 0
spin_lock = threading.Lock()


class ConnectionPool:
    def __init__(self, size: int):
        self.connections = [f"conn-{i}" for i in range(size)]
        self.lock = threading.Lock()

    def acquire(self) -> str:
        global spin_iterations
        while True:
            with self.lock:
                if self.connections:
                    return self.connections.pop()
            # ⚠️ BUSY-WAITING:
            # No connection free. Instead of sleeping until one is
            # released, we immediately loop back and check again.
            # With 90 requests waiting on only 10 connections, this
            # wastes an enormous number of CPU cycles doing nothing.
            with spin_lock:
                spin_iterations += 1

    def release(self, conn: str):
        with self.lock:
            self.connections.append(conn)


if __name__ == "__main__":
    pool = ConnectionPool(POOL_SIZE)
    active = 0
    max_active = 0
    active_lock = threading.Lock()

    def handle_request():
        global max_active, active
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
    print(f"spin iterations wasted while waiting: {spin_iterations:,}")
    print(
        "The limit was respected, but getting there burned CPU on "
        "busy polling instead of blocking efficiently."
    )
