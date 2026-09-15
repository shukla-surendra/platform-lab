# Python Concurrency — Correctness Problems

This note is written in simple language and uses small Python examples.

The main goal is to understand **why concurrency can produce wrong results**, not just memorize definitions.

---

# 1. What is concurrency?

Concurrency means multiple pieces of work are making progress during the same period of time.

With Python threads, you might have:

```text
Thread 1 ────────────────>
Thread 2 ────────────────>
Thread 3 ────────────────>
```

These threads may access the **same data**.

That shared data is where problems can happen.

---

# 2. The main problem: shared mutable state

Suppose we have:

```python
counter = 0
```

And multiple threads do:

```python
counter += 1
```

All threads are modifying the **same variable**.

This is called:

> **Shared mutable state**

- **Shared** → multiple threads can access it.
- **Mutable** → its value can change.

Shared mutable state is not automatically bad.

The problem occurs when multiple threads access it without proper synchronization.

---

# 3. Race Condition

A **race condition** happens when the result depends on the timing/interleaving of threads.

Imagine:

```python
counter = 5
```

Two threads want to increment it.

Conceptually:

```text
Thread A                  Thread B

READ counter → 5
                          READ counter → 5

WRITE counter → 6
                          WRITE counter → 6
```

Two increments were attempted.

You might expect:

```text
5 → 6 → 7
```

But we got:

```text
5 → 6
```

Thread B overwrote Thread A's update.

This is a **race condition**.

---

# 4. Why `counter += 1` can be dangerous

This:

```python
counter += 1
```

looks like one operation.

Conceptually, think of it as:

```python
temp = counter
temp = temp + 1
counter = temp
```

So there is:

```text
READ
  ↓
MODIFY
  ↓
WRITE
```

Another thread can interfere between these steps.

That is why we call this a:

> **Read-Modify-Write operation**

---

# 5. Read-Modify-Write Race

Consider:

```python
temp = counter       # READ

time.sleep(0.00001)  # allow another thread to run

counter = temp + 1   # WRITE
```

Suppose:

```text
counter = 10
```

Now two threads run.

```text
Thread A                    Thread B

temp = counter
temp = 10

                            temp = counter
                            temp = 10

counter = 11
                            counter = 11
```

Expected:

```text
12
```

Actual:

```text
11
```

One update was lost.

This is called a:

> **Lost update**

The lost update is the **correctness problem**.

---

# 6. Correctness Problem

A correctness problem simply means:

> **The program produces the wrong result because concurrent operations interfered with each other.**

In our example:

```text
10
 ↓
Thread A +1
Thread B +1
 ↓
Expected = 12
Actual   = 11
```

So:

```text
Race condition
      ↓
Lost update
      ↓
Wrong result
      ↓
Correctness problem
```

---

# 7. A complete example

Here is the example without a lock:

```python
import threading
import time

counter = 0


def increment():
    global counter

    for _ in range(1000):

        temp = counter       # READ

        time.sleep(0.00001)  # make thread switching easier to observe

        counter = temp + 1   # WRITE


threads = [
    threading.Thread(target=increment)
    for _ in range(10)
]


for t in threads:
    t.start()


for t in threads:
    t.join()


print(counter)
```

We have:

```text
10 threads
×
1000 increments
=
10000 expected
```

But the result can be much smaller because updates are lost.

---

# 8. Critical Section

A **critical section** is the part of code where shared data is accessed/modified and therefore needs protection.

In our example:

```python
temp = counter
counter = temp + 1
```

is the critical section.

Think:

```text
        CRITICAL SECTION
              ↓
    ┌────────────────────┐
    │ read counter       │
    │ modify counter     │
    │ write counter      │
    └────────────────────┘
```

We want only one thread at a time inside this section.

---

# 9. Lock

A **lock** provides exactly this protection.

Think of a lock like a room with one key.

```text
           🔑
        Lock key
           │
     ┌─────┴─────┐
     │           │
 Thread A     Thread B
     │           │
   enters       waits
```

Thread A gets the lock.

Thread B has to wait.

When Thread A finishes, it releases the lock.

Then Thread B can enter.

---

# 10. Fixing the race condition with a Lock

```python
import threading
import time

counter = 0
lock = threading.Lock()


def increment():
    global counter

    for _ in range(1000):

        with lock:
            temp = counter

            time.sleep(0.00001)

            counter = temp + 1


threads = [
    threading.Thread(target=increment)
    for _ in range(10)
]


for t in threads:
    t.start()


for t in threads:
    t.join()


print(counter)
```

Now:

```text
10 threads
×
1000 increments
=
10000
```

The important part is:

```python
with lock:
    ...
```

Only one thread can execute that section at a time.

---

# 11. What does `with lock` actually do?

This:

```python
with lock:
    counter += 1
```

is conceptually similar to:

```python
lock.acquire()

try:
    counter += 1
finally:
    lock.release()
```

The advantage of `with` is that Python releases the lock automatically, even if an exception happens.

---

# 12. Check-Then-Act Problem

Another common concurrency problem is:

> **Check something, then act based on what you checked.**

Example:

```python
if balance >= 100:
    balance -= 100
```

Looks fine.

But imagine two threads.

Initial balance:

```text
balance = 100
```

Both threads try to withdraw 100.

```text
Thread A                    Thread B

check balance >= 100
YES
                            check balance >= 100
                            YES

withdraw 100
balance = 0

                            withdraw 100
                            balance = -100
```

Both threads saw the balance as sufficient.

But only one withdrawal should have been allowed.

This is called a:

> **Check-Then-Act race condition**

---

# 13. Why Check-Then-Act is dangerous

The problem is that these are two separate actions:

```text
CHECK
  ↓
ACT
```

Another thread can change the state between them.

Example:

```python
if stock > 0:       # CHECK
    stock -= 1      # ACT
```

Two threads can both see:

```text
stock = 1
```

Then both buy the last item.

---

# 14. Fixing Check-Then-Act

Protect the whole operation:

```python
with lock:

    if stock > 0:
        stock -= 1
```

Now:

```text
Thread A
   ↓
🔒 acquire
   ↓
check stock
   ↓
decrease stock
   ↓
🔓 release

Thread B
   ↓
wait
   ↓
🔒 acquire
   ↓
check stock again
```

Thread B sees the updated state.

---

# 15. Atomicity

A useful word in concurrency is:

> **Atomic**

An operation is atomic when other threads cannot observe/interfere with it halfway through.

For example, conceptually:

```text
READ → MODIFY → WRITE
```

We want this whole sequence to behave like:

```text
┌─────────────────────────┐
│ READ → MODIFY → WRITE   │
│                         │
│   treated as ONE unit   │
└─────────────────────────┘
```

A lock can provide this kind of protection.

---

# 16. The Big Picture

The concepts connect like this:

```text
Multiple Threads
       │
       ↓
Shared Mutable State
       │
       ↓
Unsynchronized Access
       │
       ↓
Race Condition
       │
       ├───────────────┐
       ↓               ↓
Read-Modify-Write   Check-Then-Act
       │               │
       ↓               ↓
Lost Update        Invalid Decision
       │               │
       └───────┬───────┘
               ↓
       Correctness Problem
               │
               ↓
             Lock
```

---

# 17. Three questions to ask in an interview

Whenever you see concurrent code, ask:

### Question 1

**Is there shared mutable state?**

Example:

```python
counter
balance
stock
users
orders
```

If yes, continue investigating.

### Question 2

**Can multiple threads access it at the same time?**

If yes, there may be a concurrency problem.

### Question 3

**Is the operation protected/atomic?**

Look for:

```python
with lock:
```

or another synchronization mechanism.

---

# 18. Easy mental model

Remember this:

```text
SHARED DATA
    +
MULTIPLE THREADS
    +
NO SYNCHRONIZATION
    =
POSSIBLE RACE CONDITION
```

And:

```text
RACE CONDITION
      ↓
BAD INTERLEAVING
      ↓
WRONG RESULT
      ↓
CORRECTNESS PROBLEM
```

---

# 19. What to learn next

After understanding this section, learn these in order:

```text
1. Race condition             ← YOU ARE HERE
       ↓
2. Read-Modify-Write
       ↓
3. Check-Then-Act
       ↓
4. Critical Section
       ↓
5. Lock / Mutex
       ↓
6. Atomicity
       ↓
7. Deadlock
       ↓
8. Coordination
       ↓
9. Semaphore
       ↓
10. Producer / Consumer
```

Do **not** try to memorize the terminology first.

Instead, for every example ask:

> **"What can another thread do between these two lines?"**

That question will help you spot most basic concurrency correctness problems.
