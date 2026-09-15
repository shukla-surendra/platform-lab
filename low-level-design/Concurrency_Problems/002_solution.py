import threading

# ============================================================
# FIX for CORRECTNESS ISSUE #2: Check-Then-Act
# ============================================================
#
# The fix is to make CHECK and ACT happen as a single atomic
# unit, protected by a lock. No other thread can slip in between
# them while the lock is held.


class TicketBooth:
    def __init__(self, available_seats: int):
        self.available_seats = available_seats
        self.lock = threading.Lock()

    def book(self, _after_check=None) -> bool:
        with self.lock:
            if self.available_seats > 0:      # CHECK
                if _after_check is not None:
                    _after_check()

                # Safe: no other thread can be inside this block
                # at the same time, so the seat count can't be
                # decremented past what was actually available.
                self.available_seats -= 1      # ACT
                return True
            return False


if __name__ == "__main__":
    booth = TicketBooth(available_seats=1)
    results = []

    def customer():
        results.append(booth.book())

    threads = [threading.Thread(target=customer) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successful_bookings = results.count(True)

    print(f"available_seats ended at: {booth.available_seats}")
    print(f"successful bookings: {successful_bookings}")

    # Always exactly 1 booking succeeds, and available_seats
    # never goes below 0, no matter how the threads are scheduled.
