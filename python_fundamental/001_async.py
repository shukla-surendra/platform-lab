import asyncio

async def my_coroutine():
    print("Step 1")

    await asyncio.sleep(1)   # Pause here

    print("Step 2")

    await asyncio.sleep(1)   # Pause again

    print("Step 3")

print("Starting coroutine...")
asyncio.run(my_coroutine())
print("Coroutine finished.")




import asyncio

async def task(name):
    print(f"{name}: Step 1")

    await asyncio.sleep(1)

    print(f"{name}: Step 2")

    await asyncio.sleep(1)

    print(f"{name}: Step 3")


async def main():
    await asyncio.gather(
        task("A"),
        task("B")
    )

print("Starting tasks...")
asyncio.run(main())

"""
A: Step 1
B: Step 1

# A and B are both sleeping for 1 second

A: Step 2
B: Step 2

# Both sleep again

A: Step 3
B: Step 3
"""