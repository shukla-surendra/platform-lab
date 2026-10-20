"""
gather = DO MANY WAITING THINGS AT ONCE.

Downloading 5 files where each takes 1 second of waiting on the network.
One after another: 5 seconds. All at once with gather: about 1 second.
Results come back in the same order you asked for them.
"""
import asyncio
import time


async def download(name):
    await asyncio.sleep(1)  # waiting on the network
    return f"{name} done"


async def one_by_one():
    return [await download(f"file{i}") for i in range(1, 6)]


async def all_at_once():
    return await asyncio.gather(*(download(f"file{i}") for i in range(1, 6)))


start = time.time()
asyncio.run(one_by_one())
print(f"one by one:  {time.time() - start:.0f}s")

start = time.time()
results = asyncio.run(all_at_once())
print(f"all at once: {time.time() - start:.0f}s  {results}")


"""
OUTPUT (python3 06_gather_many.py):

one by one:  5s
all at once: 1s  ['file1 done', 'file2 done', 'file3 done', 'file4 done', 'file5 done']
"""
