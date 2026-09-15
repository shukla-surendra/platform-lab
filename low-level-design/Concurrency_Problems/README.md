# Concurrency Correctness Problems

A worked-example series following the [Hello Interview LLD Concurrency
path](https://www.hellointerview.com/learn/low-level-design/concurrency/intro)
(Introduction → **Correctness** → Coordination → Scarcity). Each issue
gets a buggy version, a fixed version, a learning doc, and an
automated test proving the bug and the fix.

## Layout

Each issue `N` follows the same shape:

| File | Purpose |
|---|---|
| `NNN_<topic>.md` | Learning content: what the problem is, why it happens, how to spot it, how to fix it |
| `NNN_problem.py` | Minimal code that reproduces the issue |
| `NNN_solution.py` | Same code, fixed |
| `NNN_test.py` | Automated proof that `_problem.py` breaks and `_solution.py` doesn't (issues 1-2 only — see note below) |

## Issues covered so far

| # | Category | Topic | Doc | Pattern |
|---|---|---|---|---|
| 1 | Correctness | Race Condition / Lost Update | [001_python_concurrency_correctness.md](./001_python_concurrency_correctness.md) | Read-Modify-Write on shared state without a lock |
| 2 | Correctness | Check-Then-Act | [002_check_then_act.md](./002_check_then_act.md) | Decision (`if`) and mutation split across two unprotected steps |
| 3 | Coordination | Producer/Consumer handoff | [003_coordination.md](./003_coordination.md) | Busy-waiting instead of sleeping until notified (`Condition`) |
| 4 | Scarcity | Limited resource pool | [004_scarcity.md](./004_scarcity.md) | Busy-waiting for a free slot instead of blocking on a `Semaphore` |

> Issues 3-4 ship without a `_test.py` (by request) — they're not
> corruption bugs like 1-2, so verification here is "read the code +
> run the demo + watch the printed CPU/spin cost," not an automated
> pass/fail assertion. You can add tests for these the same way as
> 1-2 if you want them later (e.g. assert `max_active <= POOL_SIZE`
> under load, or count spin iterations across runs).

## Running the demos

No dependencies needed — everything uses the standard library
(`threading`):

```bash
python3 001_problem.py    # usually prints something < 10000
python3 001_solution.py   # always prints 10000

python3 002_problem.py    # can print "successful bookings: 2" for 1 seat
python3 002_solution.py   # always prints "successful bookings: 1"

python3 003_problem.py    # correct output, but spins/burns CPU while waiting
python3 003_solution.py   # same output, sleeps (0% CPU) while waiting

python3 004_problem.py    # correct output, but prints millions of wasted spin iterations
python3 004_solution.py   # same output, zero spin iterations (blocks on a Semaphore)
```

## A meta-lesson worth calling out

If you add automated tests back for issues 1-2, it's worth using two
*different* strategies depending on the bug shape:

- **Probabilistic**, for issue 1's lost-update: reproduce the race
  with `time.sleep()` to widen the window, then run the scenario a
  few times and check the bug shows up in at least one of them —
  there's no injection point to force the exact interleaving without
  changing the source.
- **Deterministic**, for issue 2's check-then-act: `002_problem.py`'s
  `TicketBooth.book()` exposes a no-op-by-default `_after_check` hook
  at the exact point where the race lives. A test can pass a
  `threading.Barrier` through that hook to force the bad interleaving
  on every single run — 0% or 100% flaky, never "sometimes."

When you can add a harmless injection point, prefer the deterministic
style — it turns a "usually reproduces" bug demo into a real
regression test that won't rot.

## Next up

Following the site's curriculum order (Correctness → Coordination →
Scarcity → applied problems):

```text
1. Race Condition / Lost Update   ✅ done  (Correctness)
2. Check-Then-Act                 ✅ done  (Correctness)
3. Producer/Consumer handoff      ✅ done  (Coordination)
4. Limited resource pool          ✅ done  (Scarcity)
5. Deadlock (locks acquired out of order)
6. Producer/Consumer at scale (multiple producers/consumers, shutdown signaling)
7. Applied: Parking Lot / Elevator (combines correctness + scarcity)
```
