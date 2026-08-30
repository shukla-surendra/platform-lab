# Memray

**Category:** observability / debugging (Python memory profiler)

## What it is, and the problem it actually solves

Python's built-in `tracemalloc` only sees allocations made **through Python's own
allocator** — plain Python objects. In real ML/data workloads, most memory isn't
allocated that way at all: a NumPy array, a pandas DataFrame's backing buffer, a
PyTorch tensor — these are allocated by **C-level `malloc`/`calloc`/`mmap` calls
inside native extensions**, which `tracemalloc` is structurally blind to. So the
common real failure mode — "this training job's RSS keeps climbing and none of my
Python-level profiling shows why" — is exactly the case `tracemalloc` can't help
with, because the leak isn't in Python-tracked memory at all.

Memray (Bloomberg, open-source) closes that gap by hooking allocation calls at the
**C level**, underneath both Python's own allocator and any native extension's
direct `malloc` calls. That means it sees NumPy/pandas/PyTorch allocations the same
way it sees plain Python object allocations — one consistent view of everything a
process actually allocated, not just the subset that happened to go through
Python's own bookkeeping.

## What it's used for

- **Memory flame graphs** — same visual idea as a CPU-profiler flame graph, except
  each frame's width is bytes allocated (and still held) at that call site rather
  than time spent. The widest surviving frame is usually the leak.
- **Leak detection mode** — walks the reference chain backward from an unfreed
  allocation to find what's actually holding it alive (a growing cache, an
  unclosed buffer/file handle, a circular reference).
- **Live attach** — `memray attach <pid>` profiles an already-running process,
  useful for a long-lived service where restarting it under a profiler would lose
  the state that's actually reproducing the leak.
- Relatively low overhead compared to naive allocation tracing, since it hooks at
  the allocator level rather than instrumenting every object access.

Typical real scenario this fits: an inference server or training job whose RSS
grows monotonically over hours, where the actual leak is inside a C-extension's
internal caching (a common pattern in libraries wrapping native code) — invisible
to `tracemalloc`, visible to Memray's flame graph as a fat frame that never shrinks
across the run.

## Alternatives

| Tool | How it differs |
|---|---|
| **`tracemalloc`** (Python stdlib) | Only sees Python-allocator memory — blind to native-extension (`malloc`) allocations. Zero extra dependency, fine for pure-Python leak hunting; not enough for NumPy/pandas/PyTorch-heavy code. |
| **`objgraph`** | Visualizes Python *object reference graphs* (what's referencing what), not raw memory bytes — complementary to Memray rather than a substitute: objgraph tells you *why* an object is still referenced, Memray tells you *how much memory* and *where it was allocated*. |
| **`py-spy`** | A CPU/wall-time sampling profiler (flame graphs of time, not memory) — same "attach to a live process" convenience as Memray, different axis being measured. |
| **Valgrind / `massif`** | Much deeper (works on any native process, not Python-aware), but far higher overhead and no Python-frame-aware output — Memray is the Python-native answer to the same class of problem. |

## Usage

```bash
pip install memray

# run a script under Memray, producing a binary capture file
memray run -o output.bin train.py

# turn that capture into a flame graph (HTML)
memray flamegraph output.bin

# attach to an already-running process by PID instead of wrapping a fresh run
memray attach <pid>

# leak-detection view specifically
memray flamegraph --leaks output.bin
```

Not yet run hands-on against anything in this repo — logged from a conceptual
discussion. A natural place to reach for it here: the Ray Serve deployments under
[`../../../../k8s_explorer/kuberay-demo/`](../../../../k8s_explorer/kuberay-demo/README.md)
(`serve_model.py`) if a long-running replica's memory ever needs diagnosing, since
that's exactly the "native-extension-heavy long-running Python process" shape
Memray is built for (scikit-learn's `RandomForestClassifier` holding native tree
structures under the hood).
