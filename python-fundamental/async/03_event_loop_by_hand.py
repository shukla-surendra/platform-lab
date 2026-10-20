"""
WHAT IS AN EVENT LOOP?

A to-do list, and a loop that keeps going around it:
    "Next job: do a little of your work... you're waiting now? OK, back of the line. Next!"

It's like one waiter serving many tables: take an order at table 1, and while the
kitchen cooks it, go to table 2. One waiter (one thread), many tables (jobs).

Here we build one with plain Python, no asyncio.
`yield` means "pause me here, give someone else a turn".
"""


def job(name, steps):
    for i in range(1, steps + 1):
        print(f"{name}: step {i}")
        yield  # pause: "I'm waiting for something, serve someone else"
    print(f"{name}: finished")


todo = [job("Tea", 3), job("Toast", 2), job("Eggs", 1)]  # the to-do list

while todo:  # <-- THIS loop is the event loop
    current = todo.pop(0)  # take the next job from the front
    try:
        next(current)  # let it run until its next pause
        todo.append(current)  # not finished: back of the line
    except StopIteration:
        pass  # finished: drop it from the list


"""
OUTPUT (python3 03_event_loop_by_hand.py):

Tea: step 1
Toast: step 1
Eggs: step 1
Tea: step 2
Toast: step 2
Eggs: finished
Tea: step 3
Toast: finished
Tea: finished
"""
