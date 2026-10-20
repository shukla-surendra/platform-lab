# Doubts — Python async Q&A

Questions asked while learning, newest at the bottom. Short answer first, then the
explanation in plain words. FastAPI-specific questions are in
[`../../fastapi-practice/doubt.md`](../../fastapi-practice/doubt.md).

---

## Q1. What is an event loop?

**Short answer:** a to-do list of paused jobs, plus **one worker** who keeps going around the
list, letting each job do a bit of work until it has to wait, then moving on to the next job.

**Analogy: one waiter, many tables.** The waiter takes table 1's order and sends it to the
kitchen. While it cooks, the waiter doesn't stand there. They go to table 2. When table 1's
food is ready, they come back and serve it. One waiter, all tables progressing.

| Restaurant | Python |
|---|---|
| the waiter | the event loop (one thread) |
| a table | an `async def` function |
| "food is cooking, I'll come back" | `await` |
| the waiter frozen at one table | a blocking call (`time.sleep`, heavy maths) inside `async def` |

**In code:** the loop is literally this ([03_event_loop_by_hand.py](03_event_loop_by_hand.py)):

```python
while todo:
    current = todo.pop(0)      # next job
    try:
        next(current)          # run it until it pauses
        todo.append(current)   # back of the line
    except StopIteration:
        pass                   # finished
```

Output: the jobs take turns (`Tea step 1, Toast step 1, Eggs step 1, Tea step 2, ...`).

**What asyncio adds:** its loop also knows *what* each job is waiting for (a timer, a network
reply), asks the operating system "tell me when any of these are ready", and only wakes the
jobs that can continue. `asyncio.run(main())` creates that loop, runs `main`, and closes it.

**The one rule that follows:** a job only gives the waiter back at an `await`. Code with no
`await` (like `time.sleep(2)`) keeps the waiter frozen and every other job waits
([08_blocking_mistake.py](08_blocking_mistake.py): the clock stopped ticking for 2s).
