import threading
import time

counter = 0


def increment():
    global counter

    for _ in range(1000):

        # Read shared state
        temp = counter
        # ⚠️ RACE CONDITION:
        # Another thread can also read counter at the same time.
        # Both threads may get the SAME value.

        time.sleep(0.00001)
        # ⚠️ This makes the race easier to reproduce.
        # While this thread is sleeping, another thread can read counter.

        counter = temp + 1
        # ⚠️ CORRECTNESS PROBLEM:
        # We may overwrite another thread's update.
        #
        # Example:
        #   Thread A reads counter = 5
        #   Thread B reads counter = 5
        #   Thread A writes counter = 6
        #   Thread B writes counter = 6
        #
        # Two increments happened, but counter increased only by 1.
        # This is called a "lost update".


# Create 10 threads.
# Each thread tries to increment counter 1000 times.
threads = [
    threading.Thread(target=increment)
    for _ in range(10)
]


# Start all threads.
for t in threads:
    t.start()


# Wait for all threads to finish.
for t in threads:
    t.join()


# Expected:
#   10 threads × 1000 increments = 10,000
#
# Actual:
#   Usually LESS than 10,000 because of the race condition.
#
# Therefore, the race condition causes a correctness problem.
print(counter)