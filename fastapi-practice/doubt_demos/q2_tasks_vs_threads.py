"""Doubt Q2: a Task is not a thread.

Run: python3 doubt_demos/q2_tasks_vs_threads.py
1) 10,000 Tasks run on ONE OS thread.
2) A Task that never awaits (hog) blocks every other Task: no preemption.
"""
import asyncio, threading, time
T0 = time.perf_counter()

async def waiter(i):
    await asyncio.sleep(1)

async def demo_many():
    t0 = time.perf_counter()
    tasks = [asyncio.create_task(waiter(i)) for i in range(10_000)]
    await asyncio.sleep(0)
    print(f"10,000 tasks alive, OS threads = {threading.active_count()}")
    await asyncio.gather(*tasks)
    print(f"all 10,000 done in {time.perf_counter()-t0:.2f}s")

async def talker(name):
    for i in range(3):
        print(f"  t={time.perf_counter()-T0:4.1f}s {name} step {i}")
        await asyncio.sleep(0.5)          # gives control back to the loop

async def hog():
    print(f"  t={time.perf_counter()-T0:4.1f}s hog: starts 2s busy loop, no await")
    end = time.time() + 2
    while time.time() < end: pass       # never awaits -> never gives control back
    print(f"  t={time.perf_counter()-T0:4.1f}s hog: done")

async def demo_no_preemption():
    await asyncio.gather(talker("talker"), hog())

asyncio.run(demo_many())
print("talker + hog:"); T0 = time.perf_counter()
asyncio.run(demo_no_preemption())
