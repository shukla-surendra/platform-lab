# Python Concurrency — Scarcity

Issue #4 in the series. Read
[`003_coordination.md`](./003_coordination.md) first — scarcity
problems reuse the "don't busy-wait" lesson from coordination, applied
to a different situation.

---

# 1. What makes this different from coordination

Coordination (issue #3) was about **handoff**: a producer has
something, a consumer wants it, and one side occasionally has to
wait for the other because of timing.

Scarcity is about **capacity**:

> You have 10 database connections. 100 requests want one at the
> same time. There is no amount of good timing that fixes this —
> only 10 requests can ever be served *at once*, full stop. The
> other 90 must queue up and wait their turn.

The shape of the code ends up similar (something waits), but the
reason is different: it's not "nothing to do yet," it's "too many
threads want a scarce resource right now."

---

# 2. The naive (bad) way: busy-waiting for a free slot

```python
def acquire(self) -> str:
    while True:
        with self.lock:
            if self.connections:
                return self.connections.pop()
        # none free — spin and check again
```

This correctly **never hands out more than 10 connections at once**
— that invariant holds no matter what. The problem is the other 90
requests, at any given moment, are stuck in a `while True` spin loop,
burning CPU as fast as the interpreter allows.

Run [`004_problem.py`](./004_problem.py): with a pool of 10 serving
100 requests, it prints something like:

```text
max concurrent connections in use: 10 (never exceeds 10)
spin iterations wasted while waiting: 1,957,679
```

Two million wasted loop iterations, just to make 90 threads politely
wait their turn. That's CPU the machine could have spent doing
anything else — including making the connections currently in use
finish faster.

---

# 3. The fix: `threading.Semaphore`

A **semaphore** is a counter with two operations:

- **`acquire()`** — if the counter is `> 0`, decrement it and
  proceed immediately. If it's `0`, **sleep (0% CPU) until another
  thread calls `release()`**.
- **`release()`** — increment the counter. If any thread is sleeping
  in `acquire()`, wake exactly one of them.

A `Lock` is really just `Semaphore(1)` — at most one holder. A
`Semaphore(N)` generalizes that to "at most N holders at a time,"
which is exactly the shape of a connection pool:

```python
self.available = threading.Semaphore(size)  # one permit per connection

def acquire(self) -> str:
    self.available.acquire()   # sleeps here if all 10 permits are taken
    with self.lock:
        return self.connections.pop()

def release(self, conn: str):
    with self.lock:
        self.connections.append(conn)
    self.available.release()   # hand the permit back, wakes one waiter
```

```text
10 permits total

Requests 1-10  ──► acquire() succeeds immediately ──► using connections
Requests 11-100 ──► acquire() blocks, 0% CPU, asleep

Request #3 finishes ──► release() ──► one sleeping request wakes and proceeds
```

Run [`004_solution.py`](./004_solution.py) — same throttling
guarantee (`max concurrent connections in use: 10`), zero spin
iterations, because there's no polling loop at all.

---

# 4. A sharp edge: `Semaphore` trusts you

A plain `Semaphore`'s counter can go *above* its starting value if
`release()` is called more times than `acquire()` — e.g. a bug where
an exception path releases twice, or two different code paths each
think they're responsible for releasing the same permit. That
silently raises your effective concurrency limit above what you
intended, with no error.

```python
sem = threading.BoundedSemaphore(10)
...
sem.release()  # called one extra time by mistake
# ValueError: Semaphore released too many times
```

`threading.BoundedSemaphore` is a drop-in replacement that raises
`ValueError` instead of silently corrupting the limit. Prefer it
whenever `acquire()`/`release()` aren't trivially paired in the same
few lines (e.g. release happens in a different function, a callback,
or on a different thread than the acquire).

---

# 5. Semaphore vs. Lock vs. Condition — when to reach for which

| Primitive | Answers the question | Typical use |
|---|---|---|
| `Lock` | "Can I be the *only* one in here right now?" | Protecting a critical section (issues #1, #2) |
| `Condition` | "Is the specific thing I'm waiting for true *yet*?" | Producer/consumer handoff (issue #3) |
| `Semaphore` | "Is there *capacity* left for one more of me?" | Throttling concurrent access to N interchangeable resources (issue #4) |

A useful gut check: if the resource is a single shared *value* that
must not be corrupted → `Lock`. If threads are waiting on each other
to *produce or change something* → `Condition`. If threads are
competing for a *limited count* of otherwise-identical slots →
`Semaphore`.

---

# 6. Spotting scarcity problems in an interview

Ask:

1. Is there a **fixed, finite number** of something (connections,
   worker threads, API rate-limit tokens, parking spots)?
2. Can the number of things that *want* it exceed that number at
   once?
3. When it's exhausted, how does the excess demand wait — spin, or
   sleep on a semaphore (or an equivalent blocking primitive)?

Real-world shapes: database connection pools, thread pools, rate
limiters (N requests per second), a fixed set of parking spots
(this exact problem shows up as "Parking Lot" in the hellointerview
applied-problems list), API concurrency caps.

---

# 7. What's next

```text
1. Race Condition / Lost Update   ✅
2. Check-Then-Act                 ✅
3. Coordination (Condition)       ✅
4. Scarcity (Semaphore)           ✅  you are here
5. Deadlock                       ← what happens when locks are acquired out of order
6. Producer/Consumer at scale     ← multiple producers/consumers, graceful shutdown
```
