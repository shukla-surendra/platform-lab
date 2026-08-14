# Ray, Getting Started

Part of [`README.md`](README.md), but written for a different reader. The README goes deep on
mechanism, measured trade-offs, and when *not* to use Ray. **Start here if you have never used
Ray before.** It assumes you can write basic Python (functions, classes, loops) and nothing
else.

Every example below is a complete, copy-pasteable script. Run them in order — each section adds
one idea on top of the last.

Verified against Ray 2.56.1 in local mode (`ray.init(num_cpus=4)`).

## Setup

```bash
pip install "ray>=2.40"
python --version   # Ray 2.x needs Python 3.9+
```

Create a file and run it:

```bash
python hello_ray.py
```

## 1. The one-sentence version

**Ray runs your Python functions on other CPU cores (or other machines) and gives you the
results back.**

That is the whole product at the Core level. Everything else — hyperparameter search (Ray
Tune), model serving (Ray Serve), distributed training (Ray Train) — is built on top of this
same idea.

## 2. Three words to learn

| Term | Plain meaning |
|------|---------------|
| **Driver** | Your main Python script — the code you run with `python hello_ray.py`. It submits work and collects results. |
| **Worker** | A separate process Ray starts to actually run your remote functions. On a laptop, these are extra processes on the same machine. |
| **ObjectRef** (future) | A handle to a result that is not ready yet. You get one back immediately when you call `.remote(...)`. Call `ray.get(...)` when you want the actual value. |

You do not manage workers yourself. `ray.init()` starts them; `ray.shutdown()` stops them.

## 3. What the process looks like

```
Your script (driver)
    │
    │  slow_square.remote(3)  ──►  scheduler picks a free worker
    │                                    │
    │                                    ▼
    │                              worker runs slow_square(3)
    │                                    │
    │  ray.get(ref)  ◄── ObjectRef ──────┘
    │       │
    ▼       ▼
   prints 9
```

Ray also keeps a shared **object store** in memory. When many tasks need the same large input,
you put it in the store once (`ray.put`) and pass a lightweight reference — covered in section 6.

## 4. Your first program

Save this as `hello_ray.py` and run it:

```python
import ray

ray.init(num_cpus=4)   # start a tiny local "cluster" using 4 CPU cores

@ray.remote
def slow_square(x):
    return x * x

# .remote() does NOT run the function here — it schedules it and returns a future
future = slow_square.remote(5)

# ray.get() blocks until the worker finishes and returns the real value
print(ray.get(future))   # 25

ray.shutdown()           # stop worker processes — do this when you're done
```

```
25
```

The only new syntax: decorate with `@ray.remote`, call with `.remote(...)` instead of `(...)`,
and unwrap with `ray.get(...)`.

## 5. Why bother: run many tasks in parallel

Same sleep-and-square example as the README, stripped to the pattern:

```python
import ray, time

ray.init(num_cpus=4)

def slow_square_seq(x):
    time.sleep(0.5)
    return x * x

@ray.remote
def slow_square(x):
    time.sleep(0.5)
    return x * x

# Sequential — one after another
t0 = time.perf_counter()
seq_results = [slow_square_seq(x) for x in range(8)]
print(f"sequential: {time.perf_counter() - t0:.2f}s")

# Parallel — submit all 8, then wait once
t0 = time.perf_counter()
futures = [slow_square.remote(x) for x in range(8)]
results = ray.get(futures)
print(f"parallel:   {time.perf_counter() - t0:.2f}s")
print(results)

ray.shutdown()
```

```
sequential: 4.03s
parallel:   1.03s
[0, 1, 4, 9, 16, 25, 36, 49]
```

**Pattern to memorize:**

1. `@ray.remote` on the function
2. `[fn.remote(arg) for ...]` to submit work (returns a list of ObjectRefs)
3. `ray.get(futures)` to collect all results

Work between steps 2 and 3 runs in parallel. With 4 CPUs and 8 half-second tasks, expect
roughly 4× speedup, not 8× — each core runs two tasks back to back.

## 6. Share large data once with `ray.put`

If four tasks all need the same big list, passing the list directly to each `.remote()` call
copies it four times. Put it in the object store once instead:

```python
import ray

ray.init(num_cpus=4)

big_list = list(range(1_000_000))
shared_ref = ray.put(big_list)   # store once, get back a lightweight reference

@ray.remote
def sum_range(data_ref, start, end):
    return sum(data_ref[start:end])

futures = [
    sum_range.remote(shared_ref, i * 250_000, (i + 1) * 250_000)
    for i in range(4)
]
print(sum(ray.get(futures)))   # sum of 0..999999

ray.shutdown()
```

```
499999500000
```

Rule of thumb: **`ray.put()` once, pass the ref to every task that needs it.** For NumPy
arrays, Ray can often share memory without copying — see the README's object-store section
for that version.

## 7. Actors: one worker that remembers state

A plain `@ray.remote` function forgets everything between calls. An **actor** is a
`@ray.remote` **class** — one long-lived worker with its own memory:

```python
import ray

ray.init(num_cpus=4)

@ray.remote
class Counter:
    def __init__(self):
        self.value = 0

    def increment(self, amount=1):
        self.value += amount
        return self.value

    def read(self):
        return self.value

counter = Counter.remote()   # starts one dedicated worker with a Counter inside

futures = [counter.increment.remote(1) for _ in range(10)]
print(ray.get(futures))              # [1, 2, 3, ..., 10]
print(ray.get(counter.read.remote()))  # 10

ray.shutdown()
```

```
[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
10
```

Ray runs **one actor method at a time** on its worker, in submission order. That is why the
counter reaches 10 without you writing any locks. Use actors when tasks need shared mutable
state (a loaded model, a cache, a parameter server). Use plain tasks when each call is
independent.

## 8. See what Ray is doing (dashboard)

After `ray.init(...)`, Ray prints a local dashboard URL, usually:

```
http://127.0.0.1:8265
```

Open it in a browser while a script is running (or right after). You will see workers, running
tasks, and memory use. This is the fastest way to build intuition when something looks stuck
or slower than expected.

## 9. Always clean up

```python
ray.shutdown()
```

Call this when your script finishes. Without it, worker processes can linger and confuse the
next run. In notebooks, restart the kernel or call `ray.shutdown()` before re-running
`ray.init()`.

If you see `Ray already initialized`, either shutdown first or pass
`ray.init(ignore_reinit_error=True)`.

## 10. Three mistakes beginners hit

**1. Calling the function normally by accident**

```python
slow_square(5)          # runs locally in the driver — not distributed
slow_square.remote(5)   # correct — runs on a worker
```

**2. Forgetting `ray.get`**

```python
future = slow_square.remote(5)
print(future)           # ObjectRef(...), not 25
print(ray.get(future))  # 25
```

**3. Using Ray when each task is tiny**

If one task takes microseconds (e.g. predicting a single row with a small model), the cost of
*scheduling* the task can exceed the work itself. Ray slows down. The README has a measured
example where an actor pool was **2× slower** than a plain loop — read that section before
Ray-ifying fast, small workloads.

Other common errors:

| Symptom | Likely cause |
|---------|--------------|
| `PicklingError` / cannot serialize | The function closed over a non-picklable object (open file, lambda, local class). Pass data as arguments instead. |
| Tasks never finish | Not enough CPUs (`num_cpus` too low) or deadlock waiting on `ray.get` inside a task that the same worker should run. |
| Slower than expected | Tasks too small, or data copied to every task instead of `ray.put` once. |

## 11. Local laptop vs real cluster

Everything above uses **local mode**: one machine, several worker processes. The code stays
the same on a cluster — only how you start Ray changes:

```bash
# On a head node (once):
ray start --head

# On worker machines (once each):
ray start --address='ray://HEAD_NODE_IP:10001'

# In your Python script — connect instead of ray.init(num_cpus=4):
ray.init(address="auto")
```

You do not need a cluster to learn Ray Core. Local mode is enough through section 10.

## 12. What to read next

| If you want… | Go to… |
|--------------|--------|
| Mechanism depth, real speedup numbers, when *not* to use Ray | [`README.md`](README.md) |
| Hyperparameter search at scale | [Ray Tune docs](https://docs.ray.io/en/latest/tune/index.html) |
| Model serving | [Ray Serve docs](https://docs.ray.io/en/latest/serve/index.html) |
| Distributed training | [Ray Train docs](https://docs.ray.io/en/latest/train/train.html) |
| ML system design context (Train/Tune/Serve vs Kubeflow/KServe) | [`07_distributed_training_serving.md`](../../../../fundamentals/system_design_foundation/01_ml_system_design/07_distributed_training_serving.md) |

You now know the two Ray Core primitives — **tasks** (`@ray.remote` functions) and **actors**
(`@ray.remote` classes) — plus **`ray.put`** for shared data. That is the foundation everything
else in the Ray ecosystem builds on.
