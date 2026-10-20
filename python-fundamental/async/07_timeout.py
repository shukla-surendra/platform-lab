"""
TIMEOUT = DON'T WAIT FOREVER.

A website takes 5 seconds to answer. We're only willing to wait 2.
asyncio.timeout(2) cancels the waiting job after 2 seconds and raises TimeoutError.
"""
import asyncio
import time


async def slow_website():
    await asyncio.sleep(5)
    return "the page"


async def main():
    start = time.time()
    try:
        async with asyncio.timeout(2):
            page = await slow_website()
            print("got", page)
    except TimeoutError:
        print(f"gave up after {time.time() - start:.0f}s")


asyncio.run(main())


"""
OUTPUT (python3 07_timeout.py):

gave up after 2s
"""
