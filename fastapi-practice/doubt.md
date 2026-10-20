# Doubts — FastAPI Q&A

A running log of questions that came up while learning, newest at the bottom.
Each answer starts with a **short answer**, then the reasoning, then proof where we ran something.
Deeper explanations are in [docs/](docs/).

**Glossary**

| Word | Plain meaning |
|---|---|
| Process | A running program with its own memory. Has a `pid`. |
| Thread | A line of execution *inside* a process. Threads share the process's memory. |
| Event loop | One loop on one thread that keeps asking the OS "which sockets are ready?" and runs the code waiting on them. |
| Coroutine | A function defined with `async def`. It can **pause** at each `await` and resume later from the same spot. |
| Task (asyncio) | A lightweight "to-do item" the event loop runs. Very cheap to create: no OS process or thread. |
| Worker | One uvicorn process serving requests. `--workers 4` = 4 processes. |

---

## Q1. When uvicorn gets a request, does it create a new process or thread, or handle it in the same process? How?

**Short answer:** **Neither a new process nor a new thread.** By default, uvicorn is **one process
with one main thread**. Every request is handled inside that same process, as a new **asyncio
Task** on the **event loop**. A Task is just a Python object, not an OS process or thread, so
creating one is very cheap.

### How it works, step by step

```
                  one uvicorn process (pid 40785)
┌──────────────────────────────────────────────────────────────┐
│ MainThread: event loop                                       │
│                                                              │
│   "OS, which sockets have something for me?"  (kqueue/epoll) │
│        │                                                     │
│        ├─ new connection  → make a protocol object for it    │
│        ├─ request bytes   → parse HTTP → create Task-3       │
│        ├─ request bytes   → parse HTTP → create Task-4       │
│        └─ Task-3 awaits DB → switch to Task-4 …              │
│                                                              │
│ AnyIO threadpool (only used for plain `def` endpoints)       │
│   thread 1, thread 2, … up to 40 (made when needed, REUSED)  │
└──────────────────────────────────────────────────────────────┘
```

1. At startup, uvicorn opens the listening socket and starts **one event loop** on the main thread.
2. The loop asks the operating system (kqueue on macOS, epoll on Linux) which sockets are ready.
   The OS does the waiting. Python doesn't need a thread per connection just to sit and wait.
3. When a request's bytes arrive, uvicorn parses the HTTP and creates an **asyncio Task** that runs
   your FastAPI app for that request.
4. Many Tasks are in progress at once. Whenever one hits an `await` (DB call, HTTP call, sleep),
   the loop switches to another Task. That's how one thread serves many requests.

### Where threads and processes *do* come in

| Situation | What happens |
|---|---|
| `async def` endpoint | Runs as a Task on the **MainThread**. No thread is created. |
| plain `def` endpoint | The Task hands your function to the **AnyIO threadpool**. Threads are created only when needed (max 40), then **reused** for later requests. You never get a new thread per request. |
| `uvicorn --workers 4` | 4 processes are created **once at startup**, not per request. The OS decides which process accepts each new connection. Inside each process, it's the same picture as above. |

So the counts look like this:
- **processes**: fixed at startup (1 by default)
- **threads**: 1 main thread + a reusable pool of up to 40
- **Tasks**: one per request

### Proof (ran it, 2026-10-20)

A tiny app that prints `pid`, thread name, Task name, and how many threads exist. Three batches
of 3 concurrent requests: one batch to an `async def` endpoint, then two batches to a `def` endpoint:

```
[async] pid=40785 thread=MainThread task=Task-3 threads_alive=1
[async] pid=40785 thread=MainThread task=Task-4 threads_alive=1
[async] pid=40785 thread=MainThread task=Task-5 threads_alive=1
[sync]  pid=40785 thread=AnyIO worker thread task=- threads_alive=2
[sync]  pid=40785 thread=AnyIO worker thread task=- threads_alive=3
[sync]  pid=40785 thread=AnyIO worker thread task=- threads_alive=4
[sync]  pid=40785 thread=AnyIO worker thread task=- threads_alive=4   ← 2nd batch:
[sync]  pid=40785 thread=AnyIO worker thread task=- threads_alive=4     threads reused,
[sync]  pid=40785 thread=AnyIO worker thread task=- threads_alive=4     count stays 4
```

What this shows:
- **Same `pid` everywhere**, so no new process was created.
- `async def` requests: 3 different Tasks, all on `MainThread`, and the process still has only 1 thread.
- `def` requests: the first batch grew the pool to 3 worker threads. The second batch **reused** them.

### Compare with older server models

| Model | Per request | Example |
|---|---|---|
| Process per request | fork a new process (slow, heavy) | old CGI |
| Thread per request/connection | a thread for each connection | classic Tomcat, Flask `threaded=True` |
| **Event loop + Tasks** | a cheap Task object | **uvicorn / FastAPI**, Node.js, nginx |

That's why one uvicorn process can hold thousands of waiting requests: a waiting Task costs only a
few KB of memory, while a waiting thread costs an OS thread with its own stack.

More: [docs/01](docs/01-request-lifecycle-and-concurrency.md), [docs/02](docs/02-processes-threads-event-loop.md).

---

## Q2. Isn't an "asyncio Task on the event loop" just a thread? If not, how does it work?

**Short answer:** **No, a Task is not a thread.** A thread is managed by the **operating system**,
which can pause it at *any* moment and switch to another thread. A Task is a **plain Python
object** that wraps a coroutine (an `async def` function that can pause). The OS doesn't even know
Tasks exist. Only one Task runs at a time on the single event-loop thread, and it gives control
back **only when it reaches an `await`**. This is called *cooperative* multitasking. Threads use
*preemptive* multitasking: the OS decides when to switch.

### Analogy

- **Threads** = several cooks in one kitchen. A manager (the OS) can tap any cook on the shoulder
  at any moment: "stop, let someone else use the stove".
- **Tasks** = **one cook** juggling many dishes. The cook puts rice on to boil (`await`), and
  *while it boils* chops vegetables for another dish. Nobody interrupts the cook. The cook
  switches only at natural waiting points. If the cook spends 2 minutes kneading dough without
  stopping (no `await`), every other dish waits.

### What a Task actually is

```python
async def handle_request():
    user = await db.get_user(1)      # ← pause point 1
    orders = await db.get_orders(1)  # ← pause point 2
    return {"user": user, "orders": orders}
```

Calling `handle_request()` doesn't run it. It creates a **coroutine object**, a paused function
that remembers its local variables and which line it stopped at. A **Task** is that coroutine plus
a little bookkeeping: whether it's done, its result, and who is waiting for it. All of this is just
memory on the heap, a few KB per Task, while each thread needs its own stack (often 512 KB to 8 MB)
and an OS scheduler entry.

### What the event loop does (simplified)

```python
ready = [task1, task2, task3]          # Tasks that can run right now
while True:
    for task in ready:
        task.step()                    # run it until its next `await` that has to wait
                                       # → it pauses and registers "wake me when X is ready"
    ready = []
    events = os_select(timeout)        # ONE call to the OS: "which sockets/timers are ready?"
    for e in events:
        ready.append(e.waiting_task)   # wake the Tasks whose data arrived
```

So "switching Tasks" means the loop calls `.step()` on a different Python object. There's no
OS context switch and no new thread. The only waiting that happens in the OS is the single
`os_select` call (kqueue on macOS, epoll on Linux), which watches *all* sockets at once.

### Thread vs Task side by side

| | OS thread | asyncio Task |
|---|---|---|
| Who creates/schedules it | the operating system | the Python event loop |
| When does it switch | **any time** (OS interrupts it) | **only at `await`** |
| Cost each | OS stack + kernel structures (heavy) | a Python object (few KB) |
| How many is realistic | hundreds to a few thousand | tens or hundreds of thousands |
| A `while True` / `time.sleep` inside it | blocks only that thread | **blocks every Task on the loop** |
| Race conditions | can happen between *any* two lines | only possible across an `await` |

### Proof (ran it, 2026-10-20)

Demo 1: 10,000 Tasks that each `await asyncio.sleep(1)`:

```
10,000 tasks alive, OS threads = 1
all 10,000 done in 1.04s
```
10,000 concurrent "requests" ran on **one OS thread** and finished in ~1s total, not 10,000s,
because they all waited at the same time.

Demo 2: a `talker` Task that prints every 0.5s (with `await`), running next to a `hog` Task that
busy-loops for 2s **without any `await`**:

```
t= 0.0s talker step 0
t= 0.0s hog: starts 2s busy loop, no await
t= 2.0s hog: done
t= 2.0s talker step 1      ← should have been at 0.5s!
t= 2.5s talker step 2
```
Nobody interrupted the hog, so the talker was stuck for 2s. With **threads**, the OS (and
Python's GIL switch interval, ~5 ms) would have interrupted the hog, and the talker would have
printed on time. This is exactly why `time.sleep()` or heavy CPU inside an `async def` endpoint
freezes the whole FastAPI worker.

### So why does FastAPI still have a threadpool?

Because some code **can't** `await`: `requests.get`, sync DB drivers, `time.sleep`. Inside a Task
that code would hog the loop like the demo above. For plain `def` endpoints, FastAPI runs them on a
real thread from the pool, so the OS can switch away from them and the loop thread stays free.

Demo script: [`doubt_demos/q2_tasks_vs_threads.py`](doubt_demos/q2_tasks_vs_threads.py) (`python3 doubt_demos/q2_tasks_vs_threads.py`). More:
[docs/01 §2](docs/01-request-lifecycle-and-concurrency.md#2-where-your-code-runs-decides-everything).

---

## Q3. How many requests can uvicorn handle? How many workers do we need? What if one request is slow or uses a lot of CPU?

**Short answer:** There's no fixed number. It depends on **what each request spends its time
doing**:

| Request spends its time... | What limits one worker | Fix |
|---|---|---|
| **Waiting** on I/O, with `async def` + `await` | almost nothing: thousands in flight are fine (limit is downstream DB/API, memory, open sockets) | nothing, or more workers for the per-request Python overhead |
| **Waiting** in a plain `def` (blocking library) | the **40-thread pool** | raise the thread limit, or switch to an async library |
| **Computing** (CPU) | **one CPU core per worker**. Max ≈ `1 / CPU-seconds-per-request` requests/sec | more workers/pods, a process pool, or a job queue |

**Worker rule of thumb:** on a VM, **workers ≈ number of CPU cores**. In Kubernetes, use **1 worker
per pod** and scale the number of pods. More workers than cores doesn't add CPU capacity.

### Two different numbers people mean by "how many requests"

- **Throughput** = requests finished **per second**.
- **Concurrency** = requests **in progress at the same moment**.

They're linked by **Little's law**: `in-flight = throughput × latency`.
For example, 200 req/s where each takes 0.5s means about **100 requests in flight** at any moment.
An async worker handles 100 in flight easily if they are *waiting*. If they are *computing*, it can't.

### Proof (ran it, 2026-10-20, MacBook with 12 cores, `uvicorn[standard]`)

Demo: [`doubt_demos/q3_capacity/`](doubt_demos/q3_capacity/RUN.md). Each endpoint does a different
kind of work.

**1. Raw speed of a trivial endpoint** (`/hello`, measured with `ab`, keep-alive, 100 concurrent clients):

| Workers | Requests/sec |
|---|---|
| 1 | ~16,400 |
| 4 | ~31,900 |

This is the upper ceiling. Real endpoints with DB calls, Pydantic validation and JSON are usually
**hundreds to a few thousand req/s per worker**. 4 workers didn't give 4× because the load tool,
the network stack and the OS share the same machine.

**2. 1000 requests that each *wait* 0.5s** (`async def` + `await asyncio.sleep(0.5)`), 1 worker:
```
ab -n 1000 -c 1000 /io   → all 1000 done in ~1.1s, 0 failed
```
One worker, one thread, 1000 requests in flight. Waiting is cheap.
(A Python httpx client took ~6s for the same test. The slow part was the *client* opening 1000
connections, not the server. Benchmark with a proper tool like `ab`, `wrk`, `hey` or `oha`.)

**3. 100 requests that each *block* 0.5s** in a plain `def` (`time.sleep`), 1 worker:
```
100 x /sync-io -> all done in 1.61s
```
The 40-thread pool processed them in 3 rounds: 40 + 40 + 20 → 3 × 0.5s ≈ 1.5s.

**4. CPU-heavy: 8 requests, each burns 0.3s of CPU** inside `async def`:

| Setup | 8 × `/cpu` finished in | `/ping` while they ran |
|---|---|---|
| 1 worker, CPU work on the event loop | **2.41s** (8 × 0.3, one after another) | **2307 ms**: the whole worker was frozen |
| 4 workers | 1.51s, requests split `5 / 2 / 1` across workers | 2 ms (landed on a free worker, so this time it was lucky) |
| 1 worker + `ProcessPoolExecutor(4)` (`/cpu-offload`) | **0.73s** | **1 ms**: the loop stayed free |

What this shows:
- CPU work in a request **freezes everything else in that worker**, even health checks. In
  Kubernetes that can mean failed liveness probes and pod restarts.
- More workers help, but the OS decides which worker gets each connection (here `5 / 2 / 1`,
  not even). A fast request can still end up queued behind a slow one in a busy worker.
- Sending the CPU work to a **separate process** kept the server responsive and finished fastest.

### What to do when a single request is slow

**Slow because it's *waiting*** (slow DB, slow external API, LLM call):
- Use `async def` + async clients. The worker keeps serving others while it waits.
- Always set **timeouts** on outgoing calls (`httpx.AsyncClient(timeout=...)`,
  `asyncio.wait_for(...)`). Uvicorn has no per-request timeout of its own.
- Watch the **downstream limit**. 1000 waiting requests can mean 1000 DB queries, and a DB pool
  of 10 will queue them anyway.

**Slow because it's *computing*** (image processing, pandas, model inference, big JSON):

| Work takes... | Do this |
|---|---|
| a few ms | fine inline |
| tens of ms to ~1s | `run_in_executor(ProcessPoolExecutor)`, or `asyncio.to_thread` if the library releases the GIL (numpy, torch, many C libs) |
| seconds or more | **job queue** (Celery / RQ / Arq / Kafka): return `202 Accepted` + a job id, and the client polls or gets a webhook |
| a lot of it, steadily | a separate service / pods sized for CPU (e.g. a model server), scaled on its own |

**Protect the server either way:**
- `uvicorn --limit-concurrency N`: past N in-flight requests, return **503** instead of
  slowing everyone down.
- `--timeout-keep-alive`: close idle connections.
- `--limit-max-requests N`: restart a worker after N requests (works around memory leaks).
- Gunicorn `--timeout`: kills and restarts a worker that's stuck (with `UvicornWorker`).
- Put a timeout at the load balancer/ingress too.

### Sizing recipe: how many workers or pods?

1. Measure **CPU time per request** (not wall time). Example: 20 ms.
2. One worker (≈ one core) can then do about `1 / 0.020 = 50 req/s` at 100% CPU. Plan for ~70%:
   **~35 req/s per worker**.
3. Target 500 req/s → `500 / 35 ≈ 15 workers` → e.g. 15 pods × 1 worker (1 CPU each), or
   4 VMs × 4 workers.
4. Check memory: **each worker is a full copy of the app**. If the app loads a 2 GB ML model,
   4 workers = 8 GB.
5. Load test (`wrk`/`hey`/`oha`/`locust`), look at **p95/p99 latency**, not just the average, and
   adjust.

More: [docs/02 — workers, uvicorn vs gunicorn](docs/02-processes-threads-event-loop.md#layer-3-multiple-processes-workers).
