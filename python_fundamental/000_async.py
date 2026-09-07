# Subroutine = a function that runs from start to finish when called.
# Coroutine = a function that can pause and later resume from where it left off.
# A coroutine can suspend its execution and give control back to whoever called it, then resume later.
"""
Subroutine  → Normal function; runs from start to finish.

Generator   → Uses `yield`; can pause and resume using `next()`.
              `yield` pauses execution and preserves state.

Coroutine   → Uses `async def` and `await`; can suspend and resume
              asynchronously, typically managed by an event loop.

Key idea: Both generators and coroutines can pause and resume,
but `yield` → Generator, while `await` → Coroutine.
"""

def my_coroutine():
    print("Step 1")
    yield
    print("Step 2")
    yield
    print("Step 3")

c = my_coroutine()

try:
    while True:
        next(c)
except StopIteration:
    print("Coroutine finished")


c_c = my_coroutine()

next(c_c)   # Step 1
next(c_c)   # Step 2
next(c_c)   # Step 3
"""
Traceback (most recent call last):
  File "/Users/surendrashukla/projects/2026/platform-lab/python_fundamental/000_async.py", line 23, in <module>
    next(c_c)   # Step 3
    ^^^^^^^^^
StopIteration
"""