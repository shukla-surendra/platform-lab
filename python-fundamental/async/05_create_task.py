"""
create_task = PLACE AN ORDER AND GET A TOKEN.

At a food court you order a pizza, get a token, and go buy a drink.
The pizza is cooking WHILE you shop. Later you show the token and collect it.

    order = asyncio.create_task(...)   -> place the order (starts in the background)
    pizza = await order                -> wait at the counter to collect it

Notice in the output: the kitchen starts only after "me: ordered...". A task begins
the first time main() pauses (its first `await`) and gives the loop a free moment.
"""
import asyncio
import time

start = time.time()


def say(msg):
    print(f"{time.time() - start:.0f}s  {msg}")


async def cook_pizza():
    say("kitchen: pizza goes in the oven")
    await asyncio.sleep(3)
    say("kitchen: pizza is ready")
    return "pizza"


async def main():
    order = asyncio.create_task(cook_pizza())  # order placed, token in hand
    say("me: ordered, now going to buy a drink")
    await asyncio.sleep(1)
    say("me: got my drink, going to the counter")
    food = await order  # wait for the pizza
    say(f"me: eating {food}")


asyncio.run(main())


"""
OUTPUT (python3 05_create_task.py):

0s  me: ordered, now going to buy a drink
0s  kitchen: pizza goes in the oven
1s  me: got my drink, going to the counter
3s  kitchen: pizza is ready
3s  me: eating pizza
"""
