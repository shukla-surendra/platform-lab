"""
QUEUE = A HANDOFF BETWEEN JOBS.

A chef puts finished dishes on the counter (put).
A waiter picks them up and serves them (get).
They work at their own speed; the counter (queue) sits between them.
"""
import asyncio


async def chef(counter):
    for dish in ["soup", "pasta", "cake"]:
        await asyncio.sleep(0.5)  # cooking
        print(f"chef:   {dish} is ready")
        await counter.put(dish)
    await counter.put(None)  # "no more dishes tonight"


async def waiter(counter):
    while (dish := await counter.get()) is not None:  # wait for the next dish
        print(f"waiter: serving {dish}")


async def main():
    counter = asyncio.Queue()
    await asyncio.gather(chef(counter), waiter(counter))


asyncio.run(main())


"""
OUTPUT (python3 10_queue.py):

chef:   soup is ready
waiter: serving soup
chef:   pasta is ready
waiter: serving pasta
chef:   cake is ready
waiter: serving cake
"""
