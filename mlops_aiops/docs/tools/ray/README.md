# Ray

**Category:** distributed compute framework (general-purpose Python parallelism — tasks and
stateful actors — not a data-processing-specific engine)

**New to Ray?** Start with [`getting-started.md`](getting-started.md) — short sections, one
idea at a time, complete runnable scripts. This file goes deeper: real benchmarks, object-store
mechanics, and when Ray makes things *slower*.

## What it is, and the problem it actually solves

Python's standard parallelism tools stop at one machine: `multiprocessing` and
`concurrent.futures` spread work across the cores of a single box, and even that has real
friction (pickling every argument across process boundaries, no shared memory without
explicit setup, no story at all for "now run this across five machines"). [Spark](../spark/README.md)
solves the multi-machine problem, but by design at the cost of a specific, constrained shape:
computation expressed as DataFrame/SQL-style transformations over structured data.

Ray solves a different, narrower-sounding but broader-reaching problem: **take an ordinary
Python function or class, and run it — unmodified in spirit, decorated in practice — on any
core of any machine in a cluster, coordinated automatically.** No DataFrame API to learn, no
JVM, no requirement that the work even be data-processing shaped at all — a Monte Carlo
simulation, a batch of independent model-training runs, a pool of stateful services, an
arbitrary recursive task graph. This is why Ray is the substrate underneath much of the
modern distributed Python ML ecosystem (it's what Ray Train/Tune/Serve — and, separately,
frameworks like modern distributed hyperparameter search and RLHF training pipelines — are
actually built on) rather than a competing single tool in that space.

Everything below was actually run against Ray 2.40.0 in local mode (`num_cpus=4`) on this
machine — every number is real, including the ones that don't flatter Ray, which matters
more here than in most tool docs, because knowing exactly when *not* to reach for this is as
important as knowing how to use it.

## The core primitive: tasks (`@ray.remote` functions)

```python
import ray, time

ray.init(num_cpus=4)

def slow_square(x):
    time.sleep(0.5)
    return x * x

@ray.remote
def slow_square_remote(x):
    time.sleep(0.5)
    return x * x

t0 = time.perf_counter()
seq_results = [slow_square(x) for x in range(8)]
seq_time = time.perf_counter() - t0

t0 = time.perf_counter()
futures = [slow_square_remote.remote(x) for x in range(8)]
par_results = ray.get(futures)
par_time = time.perf_counter() - t0

print(f"sequential: {seq_time:.2f}s")
print(f"parallel:   {par_time:.2f}s")
print(f"speedup:    {seq_time/par_time:.2f}x")
```
```
sequential: 4.02s
parallel:   1.05s
speedup:    3.82x
```

The mechanism: `@ray.remote` turns an ordinary function into one whose `.remote(...)` call
**doesn't run the function at all** — it immediately returns a **future** (an `ObjectRef`)
and schedules the actual execution on any available worker process, anywhere in the cluster.
`ray.get(futures)` is the explicit point where the calling code blocks and waits for results
— everything between submitting the futures and calling `ray.get` runs fully in parallel.
With 4 CPUs and 8 independent half-second tasks, the real ceiling is 4x (each core running 2
tasks in sequence); `3.82x` is genuine, honest overhead (task scheduling, result collection)
accounted for, not a rounding trick.

## The object store: `ray.put` and why it matters for large data

```python
import numpy as np

big_array = np.random.rand(2_000_000)   # ~16MB
big_ref = ray.put(big_array)             # put it in Ray's shared-memory object store ONCE

@ray.remote
def sum_slice(data_ref, start, end):
    return float(np.sum(data_ref[start:end]))

futures = [sum_slice.remote(big_ref, i*500_000, (i+1)*500_000) for i in range(4)]
print(sum(ray.get(futures)))
```
```
999861.75
```

Passing `big_array` directly to four separate `.remote()` calls would serialize and copy the
full 16MB array **once per task** — four full copies. `ray.put()` places the object in Ray's
shared-memory object store a single time and returns a lightweight reference; every task that
receives that reference reads the *same* underlying memory (zero-copy, via Apache Arrow/Plasma
under the hood, for NumPy arrays and similar types) rather than each getting — and paying to
receive — its own copy. This is the direct, mechanical reason large shared inputs (a big
NumPy array, a loaded model, a large lookup table) should be `ray.put()` once and passed by
reference, not passed as a raw Python argument to every task that needs it.

## The other core primitive: actors (stateful, unlike tasks)

A plain `@ray.remote` function is **stateless** — every call is independent, with no memory
of any previous call. An **actor** is a `@ray.remote`-decorated *class*: each instance is a
long-lived worker process holding its own private state between calls.

```python
@ray.remote
class Counter:
    def __init__(self):
        self.value = 0
    def increment(self, amount=1):
        self.value += amount
        return self.value
    def get(self):
        return self.value

counter = Counter.remote()
incs = [counter.increment.remote(1) for _ in range(10)]
print(ray.get(incs))
print(ray.get(counter.get.remote()))
```
```
[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
10
```

Every call lands `1, 2, 3, ..., 10` in order, with no explicit lock anywhere in this code —
because **Ray runs each actor's method calls one at a time, in submission order, on a single
dedicated worker process for that actor's entire lifetime.** This is what makes an actor a
genuinely safe place to hold mutable state that many callers touch concurrently: the
single-threaded execution model rules out the race condition a naive shared-state object
would have under real concurrent access, without the caller ever writing a lock. This is the
building block behind anything that needs distributed, addressable, stateful services — a
parameter server, a shared cache, a pool of loaded models (below), a coordination point for a
multi-step pipeline.

## Use case 1: parallel hyperparameter / model search

The problem this solves: [`../scikit-learn/README.md`](../scikit-learn/README.md#cross-validation-and-hyperparameter-search-as-library-calls)'s
`GridSearchCV` already parallelizes across cores on one machine (`n_jobs=-1`) — but it's
still bound to that one machine's core count, and it's specifically shaped for scikit-learn's
own estimator interface. The moment a search needs to span **multiple machines**, or the
"configurations" being tried aren't even a scikit-learn grid at all (different model
*architectures*, different frameworks, a mix of scikit-learn and XGBoost trials in the same
sweep), a general-purpose task primitive is the more flexible tool:

```python
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier

X, y = load_breast_cancer(return_X_y=True)
X_ref, y_ref = ray.put(X), ray.put(y)

configs = [
    {"n_estimators": 100, "max_depth": 3}, {"n_estimators": 100, "max_depth": 5},
    {"n_estimators": 100, "max_depth": 7}, {"n_estimators": 200, "max_depth": 3},
    {"n_estimators": 200, "max_depth": 5}, {"n_estimators": 200, "max_depth": 7},
    {"n_estimators": 300, "max_depth": 5}, {"n_estimators": 300, "max_depth": 7},
]

@ray.remote
def evaluate_config(X, y, config):
    model = RandomForestClassifier(random_state=42, **config)
    scores = cross_val_score(model, X, y, cv=5)
    return config, scores.mean()

futures = [evaluate_config.remote(X_ref, y_ref, c) for c in configs]
results = ray.get(futures)
best = max(results, key=lambda r: r[1])
print("best config:", best)
```
```
sequential:   4.80s
ray parallel: 2.67s
speedup:      1.80x
best config: ({'n_estimators': 300, 'max_depth': 7}, 0.9631113181183046)
```

A real, if modest, `1.8x` speedup here (less than the 4-core ceiling — some configurations
genuinely take longer than others, and `RandomForestClassifier`'s own internal computation
competes for the same CPU cores Ray is scheduling onto). **Ray Tune** (built on Ray Core, not
covered hands-on here) is the purpose-built higher-level library for exactly this job at real
scale — adding smarter search strategies (early-stopping bad trials, Bayesian search) on top
of the same underlying task-distribution mechanism shown directly above.

## Use case 2: general-purpose distributed compute (not ML-specific)

Ray isn't an ML tool that happens to have a general API — it's a general distributed-compute
framework that ML tooling happens to be built on. A Monte Carlo simulation — estimating π by
sampling random points, a canonical embarrassingly-parallel numerical workload with no ML or
data-processing framing at all — makes that breadth concrete:

```python
import random

@ray.remote
def estimate_pi_chunk(n_samples, seed):
    rng = random.Random(seed)
    inside = 0
    for _ in range(n_samples):
        x, y = rng.random(), rng.random()
        if x*x + y*y <= 1.0:
            inside += 1
    return inside

n_chunks, samples_per_chunk = 8, 2_000_000
futures = [estimate_pi_chunk.remote(samples_per_chunk, s) for s in range(n_chunks)]
total_inside = sum(ray.get(futures))
pi_estimate = 4 * total_inside / (n_chunks * samples_per_chunk)
print(pi_estimate)
```
```
sequential:   pi≈3.14164  time=1.20s
ray parallel: pi≈3.14164  time=0.37s
speedup:      3.25x
```

A strong, genuine `3.25x` speedup — each chunk here does 2 million iterations of real CPU
work, comfortably long enough to make the per-task scheduling/communication overhead
negligible by comparison. This is the general shape of *any* problem that decomposes into
independent, computationally substantial chunks: risk simulation, large-scale scientific
computing, synthetic data generation, brute-force search over a large parameter space —
genuinely not ML-specific, which is the point.

## When Ray does *not* help — a real, measured example

This is the part worth taking as seriously as the two wins above. A tempting-looking use
case: a pool of actors, each holding a loaded model, serving prediction requests in parallel
instead of one process handling them one at a time.

```python
model = RandomForestClassifier(n_estimators=200, random_state=42).fit(X, y)
requests = [X[i % len(X)].reshape(1, -1) for i in range(200)]

@ray.remote
class ModelServer:
    def __init__(self, model):
        self.model = model
    def predict(self, row):
        return self.model.predict(row)[0]

pool = [ModelServer.remote(model) for _ in range(4)]
futures = [pool[i % 4].predict.remote(r) for i, r in enumerate(requests)]
ray.get(futures)
```
```
sequential (1 process):        0.492s for 200 requests
ray actor pool (4 replicas):   1.025s for 200 requests
speedup:                       0.48x   <- SLOWER than just calling model.predict() in a loop
```

**Ray made this workload more than twice as slow.** The reason is directly measurable, not
mysterious: each individual prediction is genuinely tiny work (a fitted `RandomForestClassifier`
predicting one row takes microseconds — it's already fast, vectorized C code), while every
single `.remote()` call to an actor pays a real, fixed cost — cross-process scheduling,
argument serialization, a round trip through Ray's internal scheduler — that runs in the
**low milliseconds**. When the actual work per call is smaller than the dispatch overhead of
*making* that call, distributing it can only make things slower, no matter how many workers
are available. Batching the 200 requests into 4 larger calls (one array of 50 rows per actor,
instead of 200 individual single-row calls) helps, but at this small a total workload
(4,000 predictions total, in a follow-up test), a single process calling `model.predict()`
once on the whole batch — already internally vectorized and already fast — still beat the
batched-actor version outright, because shipping a 200-tree forest's serialized state to each
of 4 actors costs more than the prediction work saved.

**The rule this implies, stated plainly**: Ray (like any distributed system) has a real,
non-zero per-task dispatch cost, and it only pays for itself once the work being distributed
is large enough — either because each individual chunk is genuinely CPU-heavy (the Monte
Carlo case above), or because the *total* volume is large enough that even small per-item
work adds up to something worth parallelizing, or because the workload's memory/compute
footprint doesn't fit on one machine at all regardless of speed. A workload that's already
fast and already fits comfortably in one process is a workload Ray should not be reached for
— distributing it adds real overhead in exchange for nothing.

## Alternatives

| Tool | How it differs |
|---|---|
| **[Apache Spark](../spark/README.md)** | DataFrame/SQL-shaped distributed computation, JVM-based, with a purpose-built optimizer (Catalyst) for exactly that shape of workload — the right tool when the problem *is* structured, large-scale data transformation. Ray has no equivalent query optimizer because it has no fixed computation shape to optimize — it runs arbitrary Python task graphs instead. |
| **Dask** | Python-native (no JVM), with both a pandas/NumPy-like distributed-collections API *and* a lower-level task-graph API similar in spirit to Ray's — closer to Ray than Spark is, and often compared directly against it. Dask's collections API (distributed DataFrame/array) is more mature for data-processing-shaped work; Ray's actor model (genuinely stateful, long-lived distributed objects) has no direct Dask equivalent, which is the more common deciding factor when the workload needs persistent distributed state, not just parallel computation. |
| **`concurrent.futures` / `multiprocessing`** (Python standard library) | Single-machine only, no actor/stateful-service model, no cluster story at all — the right choice whenever the workload's parallelism need is genuinely bounded to one machine's cores, since it adds zero extra dependencies or operational complexity. The overhead-vs-benefit lesson above applies here even more directly: pure Python multiprocessing has lower per-task dispatch overhead than Ray, so for small-workload, single-machine cases, it's usually still the better default. |
| **Celery** | A distributed *task queue* built for a different primary use case — asynchronous background jobs in a web application (send an email, process an uploaded file), backed by a message broker (Redis/RabbitMQ — see [`../redis/README.md`](../redis/README.md), [`../rabbitmq/README.md`](../rabbitmq/README.md)) for durability and retry semantics. Celery is optimized for many independent, often long-running, fire-and-forget jobs with delivery guarantees; Ray is optimized for tight, often synchronous, high-throughput parallel/distributed *compute* with a shared object store and direct actor addressing — genuinely different design centers, not simply "old vs. new." |
| **Kubernetes Jobs/CronJobs** | Infrastructure-level parallelism — each unit of work is a full pod, with Kubernetes' own scheduler placing it — appropriate for coarse-grained, independent, often long-running batch jobs, but with much higher per-unit overhead (a new pod, not a Python function call) than Ray's in-process task/actor model, and no shared object store or in-process actor addressing at all. |

## The broader Ray ecosystem

Ray Core (tasks + actors + the object store, everything above) is the foundation the rest of
Ray's libraries are built on, not a separate product from them:

- **Ray Train** — wraps the data/model-parallelism patterns for distributed deep learning
  training on top of Ray Core.
- **Ray Tune** — hyperparameter search at scale, built on the same task-distribution
  mechanism as the hyperparameter-search example above, adding smarter search algorithms and
  early stopping.
- **Ray Serve** — a model-serving layer built on Ray actors, specifically addressing the
  "pool of stateful model replicas handling requests" shape shown (and shown *failing* at
  small scale) above — at real production request volume and with real model inference cost
  per request, the same actor-pool pattern genuinely pays off the way it didn't in this
  doc's deliberately small, deliberately fast example.
- **Ray Data** — distributed data loading/preprocessing pipelines, Ray's answer to the
  data-processing-shaped workloads Spark specializes in, built on Ray Core's task model
  rather than a Catalyst-style query optimizer.

All four are covered at the conceptual/architectural level (parallelism strategies, gradient
sync, the reference training-job architecture, trade-offs against Kubeflow/KServe) in
[`07_distributed_training_serving.md`](../../../../fundamentals/system_design_foundation/01_ml_system_design/07_distributed_training_serving.md)
— this doc is deliberately the layer beneath that one: the actual Ray Core primitives (tasks,
actors, the object store) those higher-level libraries are themselves built out of, verified
hands-on rather than described architecturally.

## Relationship to other tools in this repo

- **[Apache Spark](../spark/README.md)** — the data-processing-shaped alternative; see
  `distributed-ml-with-mllib.md` there for Spark's own ML story, a genuinely different
  distribution model (histogram/gradient aggregation across DataFrame partitions) than Ray's
  task/actor model.
- **[scikit-learn](../scikit-learn/README.md)** — the model-training code actually run
  inside Ray tasks in the hyperparameter-search example above; Ray adds the distribution
  layer, not a replacement for the modeling library itself.
- **[XGBoost](../xgboost/README.md)** — has its own native distributed training support
  (including a Ray integration, `xgboost_ray`) for training a *single* large boosted-tree
  model across a cluster — a different problem than this doc's "run many independent trials
  in parallel," worth knowing exists for genuinely large single-model training jobs.
- **[Redis](../redis/README.md)** — Ray's object store is conceptually adjacent (shared,
  fast, in-memory data access across processes) but purpose-built for Ray's own task/actor
  scheduling, not a general-purpose cache/data-structure server the way Redis is; the two
  solve related-looking but distinct problems.
- **[KubeRay](../kuberay/README.md)** — everything above runs in local mode
  (`ray.init(num_cpus=4)` on one machine). KubeRay is the separate tool (a Kubernetes
  operator) for running an actual multi-node Ray *cluster* — the head/worker topology this
  doc never touches — on Kubernetes, with the cluster itself expressed as a CRD.
