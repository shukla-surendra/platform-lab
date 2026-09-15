import threading
import time

# ============================================================
# COORDINATION ISSUE #3: Busy-Waiting Producer/Consumer
# ============================================================
#
# A producer adds tasks to a shared queue. A consumer removes and
# processes them. The queue has a fixed capacity (backpressure):
# the producer must slow down when it's full, and the consumer
# must wait when it's empty.
#
# This version is not incorrect — items are never lost or
# duplicated — but it coordinates badly: both sides "wait" by
# spinning in a tight loop, repeatedly re-checking the condition
# instead of sleeping until something actually changes.


class BoundedQueue:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items = []
        self.lock = threading.Lock()

    def put(self, item):
        while True:
            with self.lock:
                if len(self.items) < self.capacity:
                    self.items.append(item)
                    return
            # ⚠️ BUSY-WAITING:
            # Queue is full. Instead of sleeping until a slot opens
            # up, we release the lock and immediately loop back to
            # check again. This thread spins as fast as the CPU
            # allows, burning a full core doing nothing useful.

    def get(self):
        while True:
            with self.lock:
                if self.items:
                    return self.items.pop(0)
            # ⚠️ Same problem: spin instead of sleeping until an
            # item is actually available.


if __name__ == "__main__":
    queue = BoundedQueue(capacity=3)
    produced = []
    consumed = []

    def producer():
        for i in range(10):
            queue.put(i)
            produced.append(i)
            time.sleep(0.05)  # producer is faster than consumer can drain

    def consumer():
        for _ in range(10):
            item = queue.get()
            consumed.append(item)
            time.sleep(0.2)  # slow consumer forces the queue to fill up

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
        "Correct, but both threads spent large chunks of that time "
        "spinning in a while-True loop burning CPU instead of "
        "sleeping. Watch CPU usage (e.g. `top`) while this runs."
    )
