# python_fundamental

Core Python concepts, worked through as standalone numbered scripts —
currently focused on async/concurrency. `uv`-managed (Python 3.12+).

| Script | Covers |
|---|---|
| [`000_async.py`](./000_async.py) | Subroutine vs. generator (`yield`) vs. coroutine (`async`/`await`) — the conceptual distinction, before any event loop is involved. |
| [`001_async.py`](./001_async.py) | A coroutine that actually suspends/resumes via `asyncio.sleep`, run with `asyncio.run(...)`. |
| [`002_async.py`](./002_async.py) | The event loop itself — why it's not a thread, and how it switches between tasks on one thread instead of spawning one per task. |

Run any of them directly:

```bash
uv run python 000_async.py
```

`src/python_fundamental/` is the default `uv init` package scaffold
(a `main()` stub wired to the `python-fundamental` console script) — not
yet used for anything; the real content lives in the numbered scripts above.
