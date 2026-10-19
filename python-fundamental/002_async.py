"""
# Event Loop
# The event loop is the manager that runs and coordinates coroutines.

Event loop is NOT a thread

This is a common interview point.

Usually:

One Thread
    │
    ▼
Event Loop
    │
    ├── Task A
    ├── Task B
    └── Task C

The event loop can efficiently switch between tasks without creating a thread for every task.

However, CPU-heavy work is different; async doesn't magically make CPU-bound Python code parallel.


asyncio.run(my_coroutine())

asyncio.run() starts the event loop for you.
asyncio.run(my_coroutine())
        │
        ▼
Create Event Loop
        │
        ▼
Run my_coroutine()
        │
        ▼
Coroutine hits await
        │
        ▼
Event Loop waits / runs other tasks
        │
        ▼
Coroutine becomes ready
        │
        ▼
Resume coroutine
        │
        ▼
Coroutine finishes
        │
        ▼
Event Loop closes
"""

import asyncio

async def main():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

asyncio.run(main())

# You don't explicitly create or start the event loop.

"""
asyncio.run() essentially handles:

loop = create_event_loop()
loop.run_until_complete(main())
loop.close()
"""