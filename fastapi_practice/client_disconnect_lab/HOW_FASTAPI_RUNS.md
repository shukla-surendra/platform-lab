# How a FastAPI app actually runs

Short answer: **FastAPI doesn't run anything by itself.** It's an *ASGI application*, a Python
object with an `async def app(scope, receive, send)` interface. A **server** (uvicorn) owns the
sockets, processes and threads and calls your app for each request.

```
client ──TCP──▶ [gunicorn master]           (optional, process manager only)
                   │ fork
                   ▼
                [worker process]  × N        (one OS process each, separate memory)
                   └─ MainThread: asyncio event loop   ◀── all `async def` endpoints run here
                   └─ AnyIO threadpool (≤40 threads)   ◀── all plain `def` endpoints run here
```

So it's **all three at once:** processes (workers), a single-threaded event loop inside each
process, and a threadpool next to that loop.

## Layer 1: one process, one event loop (`uvicorn app:app`)

- A single OS process with a single **event loop** on `MainThread`. It uses asyncio, or uvloop if
  `uvicorn[standard]` is installed.
- Every `async def` endpoint runs **on that one thread**. Concurrency comes from cooperative
  switching at each `await`, not from parallelism. While one request is `await`ing I/O, the loop
  runs others.
- Uvicorn's protocol code also runs on this loop: parsing HTTP and noticing disconnects.

**Consequence:** a blocking call (`time.sleep`, `requests.get`, a sync DB driver, heavy CPU) inside
`async def` freezes the **whole worker**. Observed with `/blocking`:

```
$ curl localhost:8000/blocking &   # async def + time.sleep(1) x6
$ curl localhost:8000/ping         # trivial endpoint
{"pong":true} ping took 5.46s      # stuck behind /blocking
```

## Layer 2: the threadpool (plain `def` endpoints)

- If you write `def` instead of `async def`, FastAPI runs it with `run_in_threadpool`, which uses
  an **AnyIO worker thread** in the same process. Sync dependencies run there too.
- Default limit: **40 concurrent threads** per process (AnyIO's default limiter). Request #41
  waits for a free thread.
- Because of the GIL, these threads give you concurrency for **blocking I/O**, not CPU
  parallelism.
- Threads can't be cancelled. Once started, a `def` endpoint runs to the end.

Observed (`async` and `sync` running together, same pid):
```
[sync]  pid=53455 thread=AnyIO worker thread step 1/6
[async] pid=53455 thread=MainThread           step 1/6
```

Rule of thumb: `async def` only if everything inside is `await`-able. Otherwise use plain `def`
and let the threadpool absorb the blocking.

## Layer 3: multiple processes (workers)

One process uses roughly one CPU core for Python code. To use more cores you run **N worker
processes**. Each has its own event loop, threadpool and memory: no shared globals and no shared
in-memory cache, and each runs its own `lifespan` startup.

### Option A: `uvicorn --workers N`

```bash
uv run --with fastapi --with uvicorn uvicorn app:app --workers 2
```
Observed process tree:
```
uvicorn(56441)─┬─python(56445)   ← worker 1 ("Started server process [56445]")
               └─python(56446)   ← worker 2
```
The parent binds the socket once, and the workers inherit it. **The kernel** decides which worker
`accept()`s each new connection, so it isn't round-robin. In our run, 6 sequential pings all went
to one worker.

### Option B: gunicorn as process manager + uvicorn workers

```bash
uv run --with fastapi --with uvicorn --with gunicorn \
  gunicorn app:app -w 2 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
```
Observed:
```
[56705] Listening at: http://127.0.0.1:8000 (56705)   ← master: binds, supervises, serves nothing
[56705] Using worker: uvicorn.workers.UvicornWorker
[56706] Booting worker with pid: 56706
[56707] Booting worker with pid: 56707
pings: 5 → pid 56706, 1 → pid 56707
```

- Gunicorn is a **pre-fork process manager**. The master binds the port, forks workers, restarts
  them if they die, and handles signals (graceful reload with `HUP`, scaling with `TTIN`/`TTOU`)
  and worker timeouts.
- Gunicorn **can't speak ASGI** itself. Its default sync workers are WSGI only, so `-k ...UvicornWorker`
  is required. Inside each worker it's exactly Layers 1 and 2 again.
- Some uvicorn releases point you to the separate `uvicorn-worker` package for this class. Use
  whichever your versions support.

### Which one?

| Setup | When |
|---|---|
| `uvicorn app:app` (1 process) | Dev, or **in Kubernetes/containers**: run 1 process per pod and scale with replicas. |
| `uvicorn --workers N` | Bare VM, want multiple cores, simple. |
| `gunicorn -k UvicornWorker -w N` | Bare VM, want a mature process supervisor (timeouts, graceful reloads). |

Common sizing: `N ≈ number of CPU cores` (the old `2×cores+1` rule was for sync WSGI workers).

## How this ties back to client disconnects

Disconnect handling is **per worker** and works the same under every option. The worker's event
loop sees the socket close and marks the request disconnected. Your handler still keeps running
(see [README](README.md)). Multiple workers only change *which* process wastes the work.
