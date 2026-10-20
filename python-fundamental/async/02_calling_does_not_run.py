"""
CALLING AN async FUNCTION DOES NOT RUN IT.

It hands you a "paused job" (called a coroutine), like a recipe card.
Nothing is cooked until someone actually follows the card.
asyncio.run(...) is that someone.
"""
import asyncio


async def say_hello():
    print("hello!")


job = say_hello()
print("I called say_hello() and got back:", job)  # notice: no "hello!" yet

asyncio.run(job)  # NOW it runs


"""
OUTPUT (python3 02_calling_does_not_run.py):

I called say_hello() and got back: <coroutine object say_hello at 0x106d2b880>
hello!
"""
