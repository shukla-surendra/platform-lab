import threading
import time

# ============================================================
# FIX for COORDINATION ISSUE #3: threading.Condition
# ============================================================
#
# A Condition variable lets a thread sleep ("wait") until another
# thread tells it something changed ("notify"), instead of
# repeatedly polling. While a thread is waiting, it holds NO lock
# and uses NO CPU — the OS wakes it up only when notified.


class BoundedQueue:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items = []
        self.lock = threading.Lock()
        # Both conditions share the SAME underlying lock. That's
        # required: put() and get() both touch self.items, so they
        # need to be mutually exclusive with each other too.
        self.not_full = threading.Condition(self.lock)
        self.not_empty = threading.Condition(self.lock)

    def put(self, item):
        with self.not_full:
            while len(self.items) >= self.capacity:
                # Releases the lock and sleeps here — efficiently,
                # using zero CPU — until another thread calls
                # not_full.notify(). Re-checking in a `while` (not
                # `if`) guards against spurious wakeups and against
                # another producer sneaking in first after a wakeup.
                self.not_full.wait()
            self.items.append(item)
            # Tell any consumer blocked in get() that there's now
            # something to read.
            self.not_empty.notify()

    def get(self):
        with self.not_empty:
            while not self.items:
                self.not_empty.wait()
            item = self.items.pop(0)
            # Tell any producer blocked in put() that there's now
            # room for another item.
            self.not_full.notify()
            return item


if __name__ == "__main__":
    queue = BoundedQueue(capacity=3)
    produced = []
    consumed = []

    def producer():
        for i in range(10):
            queue.put(i)
            produced.append(i)
            time.sleep(0.05)

    def consumer():
        for _ in range(10):
            item = queue.get()
            consumed.append(item)
            time.sleep(0.2)

    t_producer = threading.Thread(target=producer)
    t_consumer = threading.Thread(target=consumer)

    start = time.perf_counter()
    t_producer.start()
    t_consumer.start()
    t_producer.join()
    t_consumer.join()
    elapsed = time.perf_counter() - start

    print(f"produced: {produced}")
    print(f"consumed: {consumed}")
    print(f"elapsed: {elapsed:.2f}s")
    print(
        "Same timing, same correctness, but both threads are "
        "asleep (0% CPU) whenever they'd otherwise be blocked, "
        "instead of spinning."
    )

    # In real Python code you would normally just use the
    # standard library's queue.Queue, which implements exactly
    # this pattern internally:
    #
    #   import queue
    #   q = queue.Queue(maxsize=3)
    #   q.put(item)   # blocks efficiently if full
    #   q.get()       # blocks efficiently if empty
    #
    # Building BoundedQueue by hand here is what you'd be expected
    # to do in a low-level design interview, where the interviewer
    # wants to see that you understand what queue.Queue is doing
    # underneath.
