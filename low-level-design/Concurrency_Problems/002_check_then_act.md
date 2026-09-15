# Python Concurrency — Check-Then-Act

This is issue #2 in the series. If you haven't read
[`001_python_concurrency_correctness.md`](./001_python_concurrency_correctness.md)
(issue #1: race condition / lost update) yet, read that first — this
one builds directly on the same vocabulary (race condition, critical
section, lock).

---

# 1. The pattern

A **check-then-act** bug happens whenever code does this:

```text
CHECK something
  ↓
ACT based on what was checked
```

as **two separate steps**, without protecting them as one unit.

Example — a ticket booth with 1 seat left:

```python
if available_seats > 0:      # CHECK
    available_seats -= 1     # ACT
```

This looks completely fine when you read it top to bottom.
It is *not* fine when two threads run it at the same time.

---

# 2. How it breaks

```text
available_seats = 1

Thread A                         Thread B

CHECK available_seats > 0
→ True
                                  CHECK available_seats > 0
                                  → True

ACT: available_seats -= 1
→ available_seats = 0
                                  ACT: available_seats -= 1
                                  → available_seats = -1
```

Both threads saw `available_seats = 1` during their CHECK.
Both proceeded to ACT.

Result: **2 people booked a seat that only existed once**, and the
count went negative.

---

# 3. Why this is a different bug from "lost update"

Issue #1 (lost update) was about a **write clobbering another write**:

```text
temp = counter      # READ
counter = temp + 1  # WRITE  ← this overwrites someone else's write
```

Issue #2 (check-then-act) is about a **decision made on stale
information**:

```text
if available_seats > 0:   # decision made HERE
    available_seats -= 1  # but the world may have changed by HERE
```

Both are race conditions. Both are caused by shared mutable state
without synchronization. But the *shape* of the bug is different, so
it's worth being able to name each one separately in an interview —
naming the pattern is what tells the interviewer you've seen this
before.

---

# 4. The fix: make CHECK + ACT atomic

Wrap both steps in the same lock, so no other thread can observe the
state in between:

```python
with lock:
    if available_seats > 0:      # CHECK
        available_seats -= 1     # ACT
```

```text
Thread A
   ↓
🔒 acquire lock
   ↓
CHECK available_seats > 0  → True
   ↓
ACT: available_seats -= 1
   ↓
🔓 release lock

Thread B (was waiting for the lock)
   ↓
🔒 acquire lock
   ↓
CHECK available_seats > 0  → False   (Thread A already took it)
   ↓
(no ACT — booking correctly rejected)
   ↓
🔓 release lock
```

Now the seat can never be oversold, no matter how the scheduler
interleaves the threads.

See [`002_problem.py`](./002_problem.py) (buggy) and
[`002_solution.py`](./002_solution.py) (fixed).

---

# 5. The interesting part: how do you *test* this reliably?

This is the part that trips people up. `001_problem.py` reproduces
its bug using `time.sleep()` to widen the danger window — that works,
but it's still a matter of probability: the scheduler *usually*
interleaves the threads badly, but there's no hard guarantee.

For check-then-act, we can do better, because the bug lives at one
exact point: the gap between CHECK and ACT. So `002_problem.py`'s
`TicketBooth.book()` accepts an injectable hook that runs at exactly
that gap:

```python
def book(self, _after_check=None) -> bool:
    if self.available_seats > 0:      # CHECK
        if _after_check is not None:
            _after_check()
        self.available_seats -= 1     # ACT
        return True
    return False
```

The test (`002_test.py`) passes a `threading.Barrier(2)` as that hook.
A `Barrier(2)` blocks each thread until *both* threads have called
`.wait()`. That forces this exact interleaving, every single time:

```text
Thread A: CHECK → True → wait at barrier ⏸
Thread B: CHECK → True → wait at barrier ⏸
          (both arrived) → barrier releases both →
Thread A: ACT
Thread B: ACT
```

This turns a "sometimes flaky, sometimes not" test into one that
fails 0% or 100% of the time. **Deterministic reproduction beats
probabilistic reproduction** — prefer it whenever you can add an
injection point without changing production behavior (the hook is a
no-op unless a test supplies it).

> ⚠️ Don't reuse the same barrier trick against the *fixed*
> (locked) version — the second thread would block trying to
> acquire the lock and never even reach the barrier, so the test
> would just hang. For the fixed version, the right test is
> "throw a lot of concurrent load at it and assert the invariant
> always holds" (see `TestCheckThenActSolution` in `002_test.py`) —
> a correct lock-protected critical section is correct *regardless*
> of interleaving, so there's nothing left to force.

---

# 6. Spotting check-then-act bugs in an interview

Ask the same three questions as issue #1, plus one more specific to
this shape:

1. Is there shared mutable state? (`available_seats`, `balance`, `stock`, …)
2. Can multiple threads reach it at the same time?
3. Is there a decision (`if`) followed by a mutation, where the two
   are not protected by the same lock?

Common real-world shapes of this bug:

```python
if not cache.has(key):          # CHECK
    cache.set(key, compute())   # ACT — compute() might run twice

if balance >= amount:           # CHECK
    balance -= amount           # ACT — can overdraw

if queue.qsize() < max_size:    # CHECK
    queue.put(item)             # ACT — queue can exceed max_size

if not os.path.exists(path):    # CHECK
    create_file(path)           # ACT — TOCTOU bug, also a security issue
```

---

# 7. What's next

```text
1. Race condition / Lost Update   ← issue #1
2. Check-Then-Act                 ← issue #2, you are here
3. Critical Section (formalized)
4. Lock / Mutex (RLock, deadlock)
5. Atomicity (atomic types, compare-and-swap)
6. Deadlock
7. Coordination (Condition, Event)
8. Semaphore (scarcity/throttling)
9. Producer / Consumer
```
