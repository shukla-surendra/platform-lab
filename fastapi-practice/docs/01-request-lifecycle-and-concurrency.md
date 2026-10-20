# How FastAPI handles a request, and how concurrency works

Short answer: **every request becomes one asyncio Task on a single event-loop thread.**
Whether requests run "at the same time" depends on *where your code runs* and *whether it
`await`s*.

Next: [02 — processes, threads and the event loop](02-processes-threads-event-loop.md) covers
workers, uvicorn vs gunicorn, and what was observed in the labs.

## 1. The life of one request

FastAPI doesn't open sockets itself. Uvicorn (the ASGI server) does that work and calls
FastAPI once for each request.

```
curl ──TCP──▶ uvicorn (event loop)
                │ 1. accept connection, parse HTTP bytes
                │ 2. build `scope` (method, path, headers…)
                │ 3. create an asyncio Task → await app(scope, receive, send)
                ▼
             Starlette middleware stack (CORS, your middlewares…)
                ▼
             Router: match path + method → your endpoint
                ▼
             FastAPI: resolve Depends(), read body, validate with Pydantic
                ▼
             YOUR FUNCTION runs  ← async def: on the loop / def: in a thread
                ▼
             validate return value (response_model) → JSON → send() bytes back
```

"Concurrency" means how many of these Tasks can make progress at the same time.

## 2. Where your code runs decides everything

| You write | Runs on | 100 requests arrive at once |
|---|---|---|
| `async def` + `await` I/O (httpx, asyncpg, `asyncio.sleep`) | the event-loop thread | All 100 progress together. Each `await` hands the thread to another request. |
| `async def` + blocking call (`time.sleep`, `requests`, sync DB driver) | the event-loop thread | **Disaster.** Requests run one at a time and even `/health` waits. |
| plain `def` | the AnyIO threadpool (40 threads) | 40 run at once and the other 60 wait for a free thread. The loop stays free. |
| CPU-heavy work (either kind) | one core, because of the GIL | Threads and async don't help. You need **more processes**. |

**The rule: `await` is the only point where a request gives up the thread.** If an
`async def` function goes a long time without awaiting, nothing else in that worker runs
during that time.

The "disaster" row was measured in
[client_disconnect_lab](../client_disconnect_lab/README.md): while `/blocking` ran
`time.sleep` inside `async def`, a trivial `/ping` took 5.46s.

## 3. The three layers of concurrency

```
Processes (uvicorn --workers N / k8s replicas)   → real parallelism, uses N cores
  └─ Event loop (1 thread per process)           → thousands of concurrent waiting I/O requests
  └─ Threadpool (40 threads per process)         → handles blocking/sync code without freezing the loop
```

Choosing by workload:

- **I/O-bound** (calling DBs, APIs, LLMs): use `async def` with async libraries. One worker
  can hold thousands of in-flight requests.
- **Sync library you can't avoid:** use plain `def`, or inside `async def` call
  `await asyncio.to_thread(blocking_fn, arg)`.
- **CPU-bound** (image processing, big pandas jobs, model inference): add workers or
  processes, or send the work to a job queue and return a job id.

## 4. Gotchas

1. **Dependencies follow the same rule.** A `def get_db()` dependency runs in the
   threadpool, and an `async def` dependency runs on the loop.
2. **Global state.** Within one worker, all requests share module globals.
   - With `def` endpoints these are real threads, so a shared counter needs a lock.
   - With `async def`, nothing can interleave between two `await`s, which makes it safer.
   - **Across workers nothing is shared**, so an in-memory cache or counter has different
     values in each process.
3. **40-thread ceiling.** If a slow sync DB call takes 2s, the 41st `def` request waits even
   when the CPU is idle. You can raise the limit in `lifespan`:
   ```python
   import anyio
   anyio.to_thread.current_default_thread_limiter().total_tokens = 100
   ```
4. **Disconnects don't cancel your handler.** The work keeps running after the client leaves.
   See [client_disconnect_lab](../client_disconnect_lab/README.md).
5. **Big payloads.** Pydantic validation and JSON encoding are CPU work. Parsing a 50 MB body
   blocks every other request in that worker.
6. **Backpressure.** uvicorn's `--limit-concurrency N` returns 503 instead of queueing without
   limit. `--timeout-keep-alive` controls how long idle connections stay open.

## 5. Mental model in one line

> The event loop is one waiter serving many tables. `await` is the waiter walking away while
> the kitchen cooks. A blocking call is the waiter standing still at one table. Threads are
> extra helper waiters (max 40). Workers are separate restaurants.

## Decision cheat-sheet

| Your endpoint does... | Write it as |
|---|---|
| Only `await`-able I/O | `async def` |
| Calls a sync/blocking library | `def` (or `await asyncio.to_thread(...)` inside `async def`) |
| Heavy CPU | either one, but scale with **workers**, or offload to a queue |
| Mix of async I/O + one blocking call | `async def` + `asyncio.to_thread` for the blocking part |
