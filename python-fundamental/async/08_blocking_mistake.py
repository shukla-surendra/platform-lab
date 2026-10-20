"""
THE #1 MISTAKE: BLOCKING THE LOOP.

A clock ticks every half second while a 2-second job runs.

time.sleep(2)            -> the waiter stands frozen: the clock STOPS ticking.
await asyncio.sleep(2)   -> the waiter is free: the clock keeps ticking.

If you must call slow normal code (requests.get, a sync DB driver...), hand it to a
helper thread: await asyncio.to_thread(slow_function)
"""
import asyncio
import time


async def clock():
    start = time.time()
    for i in range(4):
        print(f"  tick {i} at {time.time() - start:.1f}s")  # should be 0.0, 0.5, 1.0, 1.5
        await asyncio.sleep(0.5)


async def bad_job():
    time.sleep(2)  # blocks the whole loop


async def good_job():
    await asyncio.to_thread(time.sleep, 2)  # runs in a helper thread, loop stays free


async def main(job):
    await asyncio.gather(clock(), job())


print("BAD  (time.sleep inside async):")
asyncio.run(main(bad_job))
print("GOOD (asyncio.to_thread):")
asyncio.run(main(good_job))


"""
OUTPUT (python3 08_blocking_mistake.py):

BAD  (time.sleep inside async):
  tick 0 at 0.0s
  tick 1 at 2.0s
  tick 2 at 2.5s
  tick 3 at 3.0s
GOOD (asyncio.to_thread):
  tick 0 at 0.0s
  tick 1 at 0.5s
  tick 2 at 1.0s
  tick 3 at 1.5s
"""
