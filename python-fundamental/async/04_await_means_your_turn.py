"""
asyncio HAS THE SAME LOOP BUILT IN.

In 03 we wrote the loop ourselves and used `yield` to pause.
With asyncio, `await` is the pause, and asyncio.run() is the loop.

Important: a job ONLY gives up its turn at an `await`.
No await = it keeps the waiter to itself until it's done.
"""
import asyncio


async def job(name, steps, take_turns):
    for i in range(1, steps + 1):
        print(f"  {name}: step {i}")
        if take_turns:
            await asyncio.sleep(0)  # "pause me, give someone else a turn"


async def main(take_turns):
    await asyncio.gather(job("Tea", 3, take_turns), job("Toast", 2, take_turns))


print("WITH await (they take turns):")
asyncio.run(main(take_turns=True))

print("WITHOUT await (Tea hogs the loop until it's done):")
asyncio.run(main(take_turns=False))


"""
OUTPUT (python3 04_await_means_your_turn.py):

WITH await (they take turns):
  Tea: step 1
  Toast: step 1
  Tea: step 2
  Toast: step 2
  Tea: step 3
WITHOUT await (Tea hogs the loop until it's done):
  Tea: step 1
  Tea: step 2
  Tea: step 3
  Toast: step 1
  Toast: step 2
"""
