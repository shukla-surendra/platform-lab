# Python Concurrency — Coordination

Issue #3 in the series. Read
[`001_python_concurrency_correctness.md`](./001_python_concurrency_correctness.md)
and [`002_check_then_act.md`](./002_check_then_act.md) first — this
issue is a different *category* of problem from issues #1 and #2, not
a harder version of the same one.

---

# 1. Correctness vs. Coordination — a different kind of bug

Issues #1 and #2 were about threads **corrupting shared state**: a
lost update, an oversold seat. The fix in both cases was the same
shape — take a lock so only one thread touches the state at a time.

Coordination problems are different. Nothing gets corrupted. The
threads correctly agree on the data. The problem is *how they wait
for each other*:

> A **producer** adds work to a queue. A **consumer** removes and
> processes it. If the queue is **empty**, the consumer has nothing
> to do — it must wait. If the queue is **full**, the producer can't
> add more — it must wait too.

Both of those are correct requirements. The question is: *how* do
you wait?

---

# 2. The naive (bad) way: busy-waiting

```python
def get(self):
    while True:
        with self.lock:
            if self.items:
                return self.items.pop(0)
        # queue was empty — loop back and check again
```

This is not a race condition. It will never return a duplicate or
lost item. But look at what it's *doing* while there's nothing to
consume: spinning in a tight loop, acquiring and releasing a lock
thousands of times a second, checking a condition that hasn't
changed. That's called **busy-waiting**, and it's wasteful in two
concrete ways:

1. **It burns a full CPU core** doing nothing, for as long as the
   thread is waiting. Run [`003_problem.py`](./003_problem.py) and
   watch `top`/Activity Monitor while it runs — one core pegs near
   100% even though the program is "waiting."
2. **It steals CPU time from threads that are doing real work** — on
   a machine with limited cores, a spinning waiter directly slows
   down the producer/consumer it's supposedly waiting for.

Scale this up: 90 idle consumers each spinning while waiting for
work is 90 cores' worth of wasted cycles, for nothing.

---

# 3. The fix: `threading.Condition`

A **condition variable** lets a thread say *"put me to sleep — using
no CPU — until someone tells me the thing I'm waiting for just
happened."*

Two operations matter:

- **`wait()`** — releases the lock and sleeps. Uses ~0 CPU. Only
  wakes up when another thread calls `notify()` (or `notify_all()`)
  on the same condition — it doesn't poll in a loop internally.
- **`notify()`** — wakes up one thread that's sleeping in `wait()`
  on this condition, so it can re-check its condition and proceed.

```python
def get(self):
    with self.not_empty:
        while not self.items:
            self.not_empty.wait()   # sleeps here, 0% CPU, until notified
        item = self.items.pop(0)
        self.not_full.notify()      # wake a producer that was waiting for room
        return item
```

```text
Consumer                              Producer

with not_empty:
  while not items:
    wait() ──────── sleeping, 0% CPU ────────┐
                                              │
                                       with not_full:
                                         items.append(x)
                                         not_empty.notify() ──┐
                                                               │
    (woken up) ◄──────────────────────────────────────────────┘
  item = items.pop(0)
  not_full.notify()
  return item
```

See the full bounded queue in
[`003_solution.py`](./003_solution.py).

---

# 4. Why `while`, not `if`?

```python
while not self.items:
    self.not_empty.wait()
```

Always re-check the condition in a loop after waking up, never
assume it's true just because you were notified. Two reasons:

- **Spurious wakeups.** A thread can wake from `wait()` without any
  `notify()` at all (an OS/implementation detail). If you don't
  re-check, you might proceed on stale state.
- **Stolen notifications.** With more than one consumer, two
  consumers might both wake up for a single item that was added, but
  only one of them will actually find `self.items` non-empty by the
  time it reacquires the lock — the other must go back to sleep.

`while` handles both cases for free; `if` doesn't.

---

# 5. Why two `Condition` objects sharing one lock?

```python
self.lock = threading.Lock()
self.not_full = threading.Condition(self.lock)
self.not_empty = threading.Condition(self.lock)
```

`put()` and `get()` both mutate `self.items`, so they must be
mutually exclusive with each other — hence one shared lock. But a
producer waiting for "not full" and a consumer waiting for "not
empty" are waiting on *different questions*, so `notify()` on one
doesn't wake threads waiting on the other unnecessarily. Two
condition objects over the same lock gives you that separation.

---

# 6. In real code: `queue.Queue`

You wouldn't hand-roll `BoundedQueue` in production Python — the
standard library's `queue.Queue` already implements exactly this
pattern (a `Condition`-protected deque) internally:

```python
import queue

q = queue.Queue(maxsize=3)
q.put(item)   # blocks efficiently if full
q.get()       # blocks efficiently if empty
```

Building it by hand here is the point of a **low-level design**
interview: the interviewer already knows `queue.Queue` exists and
wants to see that you know *what it's doing underneath* and can
reproduce it with `Lock` + `Condition`.

---

# 7. Spotting coordination problems in an interview

Ask:

1. Does one thread produce/prepare something that another thread
   consumes/waits for?
2. What does the waiting thread do while there's nothing to do —
   does it poll in a loop, or sleep until notified?
3. If it polls: how tight is the loop, and how many threads could be
   polling at once? (That's your busy-waiting cost.)

If you see a `while True: ... time.sleep(tiny_amount)` loop
guarding access to shared state, that's very likely a coordination
problem dressed up as "it works fine."

---

# 8. What's next

```text
1. Race Condition / Lost Update   ✅
2. Check-Then-Act                 ✅
3. Coordination (Condition)       ✅  you are here
4. Scarcity (Semaphore)           ← next: limited resources, not just handoff
5. Deadlock
6. Producer/Consumer at scale (multiple producers/consumers, shutdown signaling)
```
