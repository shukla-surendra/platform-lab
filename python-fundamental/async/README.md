# Async in Python, in small steps

10 tiny scripts, one idea each, built on everyday stories (breakfast, pizza, bank counters).
Every script is short and has its **real output pasted at the bottom**, so you can read it
without running it.

```bash
cd python-fundamental/async
python3 01_why_async.py        # Python 3.11+
```

## First: what is an event loop?

**An event loop is a to-do list plus one worker who keeps going around it.**

Think of **one waiter in a restaurant**:

```
   Table 1: takes the order → sends it to the kitchen → (food is cooking, nothing to do here)
   Table 2: takes the order → sends it to the kitchen → (cooking...)
   Table 3: pours water
   Table 1: kitchen says "ready!" → serves the food
   ...
```

- The waiter **never stands still waiting for one table's food**. Whenever a table is
  *waiting*, the waiter goes to another table.
- There is only **one waiter** (one thread), yet all the tables make progress.
- In Python: the waiter is the **event loop**, the tables are your **async functions**, and
  "my food is cooking, go serve someone else" is **`await`**.

The whole loop, in plain Python ([03_event_loop_by_hand.py](03_event_loop_by_hand.py)):

```python
todo = [job("Tea", 3), job("Toast", 2), job("Eggs", 1)]

while todo:                    # <-- this IS the event loop
    current = todo.pop(0)      # take the next job
    try:
        next(current)          # let it work until it pauses
        todo.append(current)   # not done yet: back of the line
    except StopIteration:
        pass                   # done: remove it
```

asyncio's real loop does the same thing. It also knows *why* each job is waiting (a timer, a
network reply), so it only comes back when that job can actually continue.

**When the waiter gets stuck:** if one table makes the waiter stand still (`time.sleep`,
a slow normal function, heavy maths), **every** table waits. See
[08_blocking_mistake.py](08_blocking_mistake.py).

## The scripts (go in order)

| File | Story | You learn |
|---|---|---|
| [01_why_async.py](01_why_async.py) | tea + toast | normal way 5s, async way 3s: why async exists |
| [02_calling_does_not_run.py](02_calling_does_not_run.py) | recipe card | calling an `async def` gives a paused job; `asyncio.run` runs it |
| [03_event_loop_by_hand.py](03_event_loop_by_hand.py) | tea, toast, eggs | **an event loop in 6 lines**, no asyncio |
| [04_await_means_your_turn.py](04_await_means_your_turn.py) | tea + toast again | `await` = "give someone else a turn". No await → no turns |
| [05_create_task.py](05_create_task.py) | food-court token | start something in the background, collect it later |
| [06_gather_many.py](06_gather_many.py) | 5 downloads | one by one 5s, `gather` 1s |
| [07_timeout.py](07_timeout.py) | slow website | stop waiting after N seconds |
| [08_blocking_mistake.py](08_blocking_mistake.py) | a ticking clock | `time.sleep` freezes everything; `asyncio.to_thread` fixes it |
| [09_semaphore.py](09_semaphore.py) | bank with 2 counters | only N at a time |
| [10_queue.py](10_queue.py) | chef → counter → waiter | handing work from one job to another |

## Four words to remember

| Word | Plain meaning |
|---|---|
| `async def` | a function that is allowed to pause |
| `await` | "pause me here until this is ready; serve someone else meanwhile" |
| event loop | the one waiter going around all the paused jobs |
| task | a job you started that runs in the background (`asyncio.create_task`) |

Questions asked while learning: [doubt.md](doubt.md).
Earlier notes: [`../000_async.py`](../000_async.py) (generator vs coroutine), `../001_async.py`, `../002_async.py`.
How FastAPI uses all this: [`../../fastapi-practice/doubt.md`](../../fastapi-practice/doubt.md).
