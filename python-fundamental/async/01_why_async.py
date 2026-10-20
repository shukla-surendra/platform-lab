"""
WHY ASYNC?  Think of making breakfast.

Tea needs 3 seconds to boil. Toast needs 2 seconds in the toaster.
You don't stand and stare at the kettle: you switch the kettle on,
then put the bread in the toaster while it boils.

"Start something, and while it WAITS, do something else" = async.
"""
import asyncio
import time


# ---- normal way: wait for each thing to finish before starting the next ----
def make_tea_normal():
    time.sleep(3)  # stand and stare at the kettle
    return "tea"


def make_toast_normal():
    time.sleep(2)
    return "toast"


# ---- async way: while one thing waits, start the other ----
async def make_tea():
    await asyncio.sleep(3)  # kettle is boiling... go do something else
    return "tea"


async def make_toast():
    await asyncio.sleep(2)
    return "toast"


async def breakfast():
    return await asyncio.gather(make_tea(), make_toast())  # start both


start = time.time()
print(make_tea_normal(), make_toast_normal(), f"-> normal way took {time.time() - start:.0f}s")

start = time.time()
print(*asyncio.run(breakfast()), f"-> async way took {time.time() - start:.0f}s")


"""
OUTPUT (python3 01_why_async.py):

tea toast -> normal way took 5s
tea toast -> async way took 3s
"""
