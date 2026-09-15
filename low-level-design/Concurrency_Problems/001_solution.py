import threading
import time

# Create a Lock object.
# Only ONE thread can hold this lock at a time.
lock = threading.Lock()

# Shared variable.
# All 10 threads will modify this same variable.
counter = 0


def increment():
    global counter

    # Each thread will increment the counter 1000 times.
    for _ in range(1000):

        # Try to acquire the lock.
        # If another thread already has the lock,
        # this thread WAITS here.
        with lock:

            # Lock has been acquired.
            # No other thread can enter this block now.

            # Read the current value of the shared counter.
            temp = counter

            # Sleep for a tiny amount of time.
            # Normally another thread could run during sleep,
            # BUT because we still hold the lock,
            # that other thread cannot enter the "with lock" block.
            time.sleep(0.00001)

            # Increment our local copy and write it back
            # to the shared counter.
            counter = temp + 1

        # Leaving "with lock" automatically RELEASES the lock.
        # Now another waiting thread can acquire it.


# Create 10 threads.
# Each thread will execute increment().
threads = [
    threading.Thread(target=increment)
    for _ in range(10)
]


# Start all 10 threads.
# They will compete for the lock.
for t in threads:
    t.start()


# Wait for every thread to finish.
for t in threads:
    t.join()


# Each of 10 threads performed 1000 increments.
# 10 × 1000 = 10000
print(counter)