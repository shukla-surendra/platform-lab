import threading

# ============================================================
# CORRECTNESS ISSUE #2: Check-Then-Act
# ============================================================
#
# Scenario: a movie ticket booth has a limited number of seats.
# Before selling a seat, we CHECK that seats are still available,
# then we ACT by decrementing the count.
#
# These are two separate steps, so another thread can slip in
# between the CHECK and the ACT.


class TicketBooth:
    def __init__(self, available_seats: int):
        self.available_seats = available_seats

    def book(self, _after_check=None) -> bool:
        """
        Try to book one seat.

        `_after_check` is a test-only hook. It is called right after
        the CHECK and right before the ACT, so tests can force two
        threads to interleave at exactly the dangerous point instead
        of hoping a race shows up by luck (see 002_test.py).
        """
        if self.available_seats > 0:          # ⚠️ CHECK
            if _after_check is not None:
                _after_check()

            # ⚠️ CORRECTNESS PROBLEM:
            # Another thread could have already booked the last seat
            # in the gap between our CHECK and our ACT below.
            # We still go ahead and decrement — possibly below zero.
            self.available_seats -= 1          # ⚠️ ACT
            return True
        return False


if __name__ == "__main__":
    # Only 1 seat left, but 5 people try to book it at the same time.
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

    # Expected: only 1 booking should ever succeed for 1 seat.
    # Actual: on a bad interleaving, more than one booking can
    # succeed, and available_seats can go negative.
