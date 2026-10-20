"""
SEMAPHORE = ONLY N AT A TIME.

A bank has 2 counters and 6 customers. Each customer takes 1 second.
Everyone arrives at once, but only 2 can be served at the same time.

Real use: "call this API at most 10 at a time" so you don't overload it.
"""
import asyncio
import time

start = time.time()
counters = asyncio.Semaphore(2)  # 2 counters


async def customer(n):
    async with counters:  # wait here until a counter is free
        print(f"{time.time() - start:.0f}s  customer {n} at a counter")
        await asyncio.sleep(1)


async def main():
    await asyncio.gather(*(customer(n) for n in range(1, 7)))


asyncio.run(main())


"""
OUTPUT (python3 09_semaphore.py):

0s  customer 1 at a counter
0s  customer 2 at a counter
1s  customer 3 at a counter
1s  customer 4 at a counter
2s  customer 5 at a counter
2s  customer 6 at a counter
"""
