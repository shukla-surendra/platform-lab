# Distributed Training

A comprehensive look at how distributed computing powers modern AI development, why it has
become essential for state-of-the-art models, and how the three major frameworks (PyTorch,
TensorFlow, Horovod) actually implement it under the hood.

---

## Part 1: Why Distributed Training Is Needed

### The Scale of Modern AI

Model size has grown by roughly three orders of magnitude per "era":

| Era | Typical parameter count | Example |
|---|---|---|
| Early neural networks | Millions | LeNet, early CNNs |
| Current production models | Billions | GPT-3 (175B), LLaMA-2 (70B) |
| Frontier research models | Trillions (dense-equivalent, often via mixture-of-experts) | GPT-4-class, Gemini-class models |

Today's models are also trained on **petabytes** of data spanning text, images, video, and
code. Put a number on what that means for a single GPU: training a 175B-parameter model on a
single accelerator — even ignoring that it wouldn't fit in memory at all — would take an
estimated several **years** of continuous compute. Distributed training isn't an optimization
you bolt on later; it is the only reason frontier models can be trained within a useful
timeframe at all.

> **Q: Is "distributed training" the same thing as "using a GPU cluster"?**
> **A:** Not quite — a cluster is the *hardware* (many machines, each with one or more GPUs,
> connected by a network). Distributed training is the *software strategy* that decides how a
> single training job's work gets split across that hardware, and how the pieces stay in sync.
> You can have a cluster sitting idle with no distributed training running on it, and you can
> (less usefully) attempt distributed training across a network too slow to make it worthwhile.
> The rest of this doc is about that second part — the software strategy.

### The Limits of Single-GPU Training

**Memory ceiling.** A single high-end datacenter GPU — an NVIDIA H100, for example — ships
with roughly **80GB of HBM3 memory** (some NVL variants push to ~94GB). A 175B-parameter model
like GPT-3 needs far more than that just to hold its weights in FP16 (175B params × 2 bytes ≈
350GB), before even accounting for optimizer state, activations, and gradients, which
routinely multiply that footprint by 4-8×. One GPU is structurally incapable of holding the
model, independent of how fast that GPU is.

**Processing bottlenecks.** Even for models that *do* fit, a single GPU means a single stream
of forward/backward passes — no parallel throughput, and long wall-clock time per epoch on
large datasets.

**Reliability concerns.** A training run that takes weeks or months has no redundancy on a
single GPU: one hardware fault (VRAM error, overheating, a driver crash) loses the entire run
unless checkpointing is separately in place.

> **Q: If memory is the real blocker for huge models, why do people also parallelize small
> models that easily fit on one GPU?**
> **A:** Because "fits in memory" and "trains fast enough to be useful" are two different
> constraints. A model that fits comfortably on one GPU can still take weeks to converge on a
> large dataset — that's a *compute-time* problem, solved by data parallelism (Part 3), not a
> *memory* problem, solved by model parallelism. The two failure modes call for different
> tools, which is exactly why "parallelism" isn't one technique but a family of them.

### Why Scale Training Across GPUs?

- **Accelerated training** — reduce wall-clock time from weeks to days, which directly
  determines how many experiments a research team can run per quarter.
- **Model capacity** — distributing parameters across devices is the *only* way to train a
  model larger than any single GPU's memory.
- **Fault tolerance** — a cluster with redundancy can continue (or resume quickly) when an
  individual node fails, instead of losing the entire run.

Distributed training has become an **industry necessity** for competitive LLMs, computer
vision systems, and multimodal AI — not a nice-to-have optimization reserved for a handful of
the largest labs.

---

## Part 2: Parallelism in Training — The Core Strategies

Three broad strategies exist, and real systems typically combine them rather than picking just
one:

1. **Data Parallelism (DP)** — split the *batch* across GPUs; every GPU holds a full copy of
   the model.
2. **Model Parallelism (MP)** — split the *model itself* across GPUs; each GPU holds only part
   of the model's layers/parameters.
3. **Pipeline Parallelism** — a specific way of *scheduling* model-parallel execution so
   different GPUs work on different micro-batches concurrently, like stations on an assembly
   line, instead of sitting idle while waiting for their turn in a purely sequential chain.

> **Q: If model parallelism already splits the model across GPUs, what does pipeline
> parallelism add on top of that?**
> **A:** Plain model parallelism (Part 3 covers this in depth) has an idle-GPU problem: while
> GPU 2 is waiting for GPU 1 to finish layers 1-4, GPU 2 does nothing. Pipeline parallelism
> fixes this by feeding in the *next* micro-batch to GPU 1 as soon as it hands off the current
> one to GPU 2 — so at steady state, every GPU is busy on a different micro-batch
> simultaneously, the same way an assembly line keeps every station working on a different car
> at the same time rather than one car moving through an empty line one station at a time.

Modern training frameworks combine these approaches to scale from **1 to 1,000+ GPUs**,
adapting the mix to the model's architecture and the hardware actually available.

---

## Part 3: Compute vs. Communication Tradeoff

The fundamental equation governing every distributed training design:

```
Effective Training Speed = Raw Compute Throughput − Communication Overhead
```

- **More GPUs** → more raw compute power, in principle.
- **More GPUs** also means **more synchronization** — every GPU's gradients (in data
  parallelism) or activations (in model parallelism) have to be exchanged over the network, and
  that exchange takes real time.
- **Optimal design** balances the two: adding the 1001st GPU only helps if the extra compute it
  contributes exceeds the extra communication cost of keeping it synchronized with everyone
  else.

> **Q: Concretely, why does communication cost grow as you add GPUs, instead of staying
> constant?**
> **A:** In the simplest (naive) synchronization scheme, every GPU needs to exchange data with
> every other GPU, and the total amount of gradient data that must move across the network
> scales with both the model size *and* the GPU count. Efficient collective-communication
> algorithms (AllReduce, covered in Part 6) reduce this from a naive all-to-all pattern down to
> something closer to linear in GPU count rather than quadratic — but the underlying cost never
> disappears, it's only made asymptotically cheaper. This is exactly why the interconnect
> hardware matters as much as the algorithm.

High-speed interconnects and efficient algorithms are what keep the "communication overhead"
term in that equation small enough that adding GPUs still pays off:

- **NVLink** — NVIDIA's proprietary GPU-to-GPU interconnect, far faster than standard
  PCIe, used within a single server/node.
- **InfiniBand** — a high-throughput, low-latency network fabric used *between* nodes in a
  cluster.
- **AllReduce** — the collective-communication algorithm (detailed in Part 6) that
  synchronizes gradients across GPUs without funneling everything through one central
  bottleneck.
- **ZeRO (Zero Redundancy Optimizer)** — a memory- and communication-efficient way to shard
  optimizer state, gradients, and parameters across GPUs instead of redundantly replicating
  them everywhere (mentioned again in Part 3's model-parallelism section below).

### Distributed Training in Practice

Frontier AI training runs are not a niche extreme case — they represent where the entire
field's compute budget is actually going. Illustrative, order-of-magnitude GPU-cluster scale
by workload type (approximate, since exact figures are rarely disclosed publicly):

| Workload | Illustrative cluster scale |
|---|---|
| Frontier LLM pretraining (GPT-4-class, Gemini-class) | Tens of thousands of GPUs |
| Large multimodal/frontier models generally | 10,000–30,000+ GPUs for a single training run |
| Vision Transformers (large-scale) | Hundreds to low thousands of GPUs |
| RL for robotics | Hundreds of GPUs, often across many shorter parallel runs |

Even computer vision and reinforcement-learning systems — historically smaller-scale than
LLMs — now routinely need multi-node clusters to hit state-of-the-art results. Distributed
training is, at this point, the only viable path to a competitive AI system.

### Benefits Beyond Raw Scale

- **Fault tolerance** — distributed checkpoints (Part 7) provide resilience against hardware
  failure during runs that last weeks.
- **Resource flexibility** — mixing CPU, GPU, and TPU nodes based on availability and
  workload shape.
- **Team collaboration** — multiple research teams can run experiments in parallel on shared
  cluster infrastructure, rather than queuing for one machine.

The net effect is a shorter **time-to-market** for AI products — a business advantage on top
of the purely technical one.

---

## Part 4: Challenges of Distributed Training

Three recurring problems show up regardless of which framework or parallelism strategy is
used:

1. **Communication bottlenecks** — gradient synchronization can become the dominant cost,
   especially as GPU count grows.
2. **The straggler problem** — training speed is capped by the *slowest* participating node,
   because most synchronization schemes require every GPU to finish its step before anyone
   proceeds to the next one.
3. **Debugging complexity** — a bug that only reproduces "sometimes, on some subset of 800
   GPUs" is fundamentally harder to trace than a single-process bug.

> **Q: What actually causes a node to become a "straggler" — is it always a slower GPU?**
> **A:** A slower GPU model is the obvious cause, but in practice stragglers more often come
> from **uneven work distribution** (one GPU got a batch with longer sequences, so its forward
> pass simply takes longer), **transient contention** (another job sharing the same physical
> network switch), or **thermal throttling** (a GPU quietly reducing its own clock speed to stay
> within temperature limits, invisible unless you're specifically monitoring for it). This is
> why straggler mitigation in production systems includes not just "buy identical hardware" but
> active monitoring and, in some systems, redundant/backup computation for the slowest
> stragglers.

Orchestration platforms — **Kubernetes, Slurm, Ray** — are essential for scheduling and
managing these jobs, but they add their own operational complexity on top of the ML-specific
challenges above. Getting good at distributed training therefore requires real depth in both
**ML engineering** and **distributed systems** — neither alone is sufficient.

---

## Part 5: Data Parallelism vs. Model Parallelism (Deep Dive)

### Why Parallelism Matters

**The challenge:** modern deep learning models routinely exceed what a single GPU can hold in
memory or process in reasonable time, forcing a choice of distributed strategy.

**The solution:** parallelism strategies unlock scaling across many GPUs — but which strategy
is correct depends on:

- **Model size** — does it fit on one GPU at all?
- **Dataset size** — is the bottleneck data volume or model size?
- **Infrastructure** — what interconnect speed and GPU count is actually available?

Many production systems use a **hybrid** of both (see Part 4's introduction to pipeline
parallelism, and the "Advanced Techniques" note under Model Parallelism below).

### What Is Data Parallelism?

Data Parallelism splits the **dataset** across GPUs while every GPU keeps a **complete,
identical copy of the model**. Each GPU:

- Holds a full model replica.
- Processes a different mini-batch of data in parallel with the others.
- Synchronizes its computed gradients with every other replica via **AllReduce** before
  updating weights.

This is the default, most common strategy in frameworks like **PyTorch DDP** and TensorFlow's
`MirroredStrategy`.

#### Data Parallelism Workflow

1. **Split & distribute** — divide one mini-batch into N smaller sub-batches, one per GPU.
2. **Parallel computation** — each GPU runs a full forward and backward pass independently, on
   its own sub-batch.
3. **Gradient synchronization** — an AllReduce operation sums (and averages) the gradients
   computed by all N GPUs.
4. **Model update** — every GPU applies the *same* synchronized gradient to its own local
   copy of the weights.
5. **Repeat** for the next batch, until the epoch completes.

> **Q: If every GPU ends the step with the same averaged gradient, why bother keeping N
> separate model copies at all — couldn't there just be one shared copy?**
> **A:** Because "shared" would mean a network round-trip on every single parameter read
> during the forward pass, for every GPU, every step — vastly more communication than
> AllReduce's single synchronization point per step. Keeping N full local copies means each
> GPU's forward/backward pass is completely local and fast; the *only* cross-GPU communication
> needed is the one gradient-sync step at the end. That's the whole reason data parallelism
> scales as well as it does — computation stays local, only a compact summary (the gradient)
> crosses the network.

**Scales efficiently for medium/large datasets with moderately-sized models.**

#### Strengths of Data Parallelism

- **Implementation simplicity** — modern frameworks (PyTorch DDP, TF `MirroredStrategy`) wrap
  this pattern behind a high-level API requiring minimal code changes to an existing
  single-GPU script.
- **Near-linear scaling** — with a fast interconnect and large enough batch sizes, adding GPUs
  produces close to proportional speedup.
- **Model compatibility** — no restructuring of the model's architecture is needed; DP wraps
  around an existing model unchanged.
- **Hardware optimization** — pairs well with **NCCL + NVLink** clusters, which are built
  specifically to make the AllReduce step fast.

#### Weaknesses of Data Parallelism

- **Memory constraint** — the *entire* model must still fit on a single GPU, since every
  replica is a full copy. This is the hard ceiling data parallelism alone cannot break.
- **Straggler problem** — see Part 4; the whole step waits on the slowest GPU.
- **Communication bottleneck** — AllReduce's cost grows with model size (more parameters =
  more gradient data to synchronize each step).
- **Diminishing returns at extreme scale** — beyond roughly 1,000+ GPUs, communication
  overhead starts eating into the gains from additional compute.
- **Batch-size tuning** — data parallelism's larger *effective* batch size (sub-batch × GPU
  count) can hurt convergence/generalization if the learning rate isn't scaled to compensate —
  a well-known interaction that catches teams off guard the first time they scale up GPU count.

> **Q: So data parallelism alone can never train a model bigger than one GPU's memory, no
> matter how many GPUs are added?**
> **A:** Correct — that's precisely the gap model parallelism exists to close. Adding more
> GPUs under pure data parallelism adds more *copies* of the same model, which helps with
> training *speed*, not model *size*. If the model itself doesn't fit on one GPU, data
> parallelism alone is the wrong tool regardless of GPU count — you need model parallelism, or
> a hybrid, instead.

### What Is Model Parallelism?

Instead of replicating the model, **model parallelism splits the model itself** across
multiple GPUs:

- Each GPU holds specific layers or components, not the whole network.
- Data flows sequentially: forward pass through GPU 1's layers, then GPU 2's, and so on.
- Required whenever **model size exceeds a single GPU's memory** — this is the scenario data
  parallelism structurally cannot solve.

This approach is what makes it possible to train modern large language models — GPT, PaLM,
LLaMA-class architectures — with parameter counts running into the hundreds of billions or
trillions.

#### Model Parallelism Workflow

1. **Layer distribution** — partition the model's layers across available GPUs (e.g. layers
   1-4 on GPU 1, layers 5-8 on GPU 2).
2. **Sequential forward pass** — input flows through GPU 1's layers, and the resulting
   *activations* (not the raw input) are transferred to GPU 2 to continue.
3. **Continue the chain** — this repeats until the final layer, on the last GPU, produces the
   output.
4. **Backward pass** — backpropagation reverses the same sequence, with *gradients* flowing
   backward through the same chain of GPUs.
5. **Memory optimization** — activation checkpointing discards intermediate activations during
   the forward pass and recomputes them during the backward pass instead of storing all of
   them, trading extra compute for significantly reduced memory use.

> **Q: What exactly gets sent over the network in model parallelism, if not the whole model?**
> **A:** Only the **activations** at each layer boundary (forward pass) and their
> **gradients** (backward pass) — not the model weights themselves, which stay put on
> whichever GPU owns that layer. This is the opposite of data parallelism, where the *weights'
> gradients* are what crosses the network and the *activations* stay entirely local to each
> GPU. Recognizing this activations-vs-gradients distinction is the fastest way to reason about
> which strategy's communication cost scales with what.

**Enables training of trillion-parameter models that are simply impossible under data
parallelism alone**, since no single GPU is ever asked to hold the full model.

#### Strengths of Model Parallelism

- **Enables ultra-large models** — breaks through the single-GPU memory barrier entirely,
  which is the central reason it exists.
- **Memory efficiency** — each GPU only needs to hold its own assigned slice of the model.
- **Pipeline integration** — combines naturally with pipeline parallelism (Part 2) to keep
  GPUs busy instead of idling in the sequential chain.
- **Advanced sharding techniques** — supports **ZeRO (Zero Redundancy Optimizer)** and
  **FSDP (Fully Sharded Data Parallel)**, which shard optimizer state, gradients, and even
  parameters across GPUs to squeeze out further memory savings beyond naive layer-splitting.

#### Weaknesses of Model Parallelism

- **Implementation complexity** — significantly harder to implement and debug correctly than
  data parallelism.
- **Partitioning challenges** — deciding *where* to split the model requires careful analysis;
  a bad split can leave one GPU doing far more work than another.
- **Communication overhead** — activations have to move between devices on every forward and
  backward pass, which can saturate the interconnect if not managed carefully.
- **Load balancing** — an uneven split leaves some GPUs waiting idle for busier ones to catch
  up.
- **Increased wall-clock time** — the inherently sequential nature of naive model parallelism
  (without pipelining) tends to *increase* total training time unless carefully optimized.

### Key Takeaways: Data vs. Model Parallelism

| | Data Parallelism | Model Parallelism |
|---|---|---|
| What's split | The data/batch | The model itself |
| What's replicated | The full model, on every GPU | Nothing — each GPU holds a distinct slice |
| Implementation | Simple | Complex |
| Scaling behavior | Efficient, near-linear (to a point) | Powerful but sequential/harder to balance |
| Hard limit it solves | Training *speed* | Model *size* |
| Best for | Medium-sized models, large datasets | Billion-plus-parameter models |

**Modern best practice:** most state-of-the-art systems use a **hybrid** — combining data,
model, and pipeline parallelism simultaneously — because real frontier models are constrained
by *both* memory and training-time at once. The right mix depends on the specific model
architecture, dataset, and hardware available; there is no universal default.

---

## Part 6: PyTorch Distributed Training

### Why Distributed Training in PyTorch?

Single-GPU training in PyTorch runs into the same three walls as any framework:

- **Model size limitations** — larger models exceed one GPU's memory.
- **Training speed constraints** — slower convergence on large, complex datasets.
- **Research & production scalability** — enterprise-grade AI work demands multi-node
  capability from the start, not as an afterthought.

### PyTorch Distributed Architecture

- **`torch.distributed`** — the core package providing the low-level primitives (process
  groups, collective operations like AllReduce) that everything else builds on.
- **`DistributedDataParallel` (DDP)** — the industry-standard, high-level API for data-parallel
  training, built on top of `torch.distributed`.
- **RPC framework** — enables parameter-server-style architectures and more advanced pipeline
  parallelism patterns, for cases DDP alone doesn't cover.

This stack works across single- or multi-node clusters, with a choice of communication
backend depending on hardware:

| Backend | Best for | Notes |
|---|---|---|
| **NCCL** (NVIDIA Collective Communications Library) | NVIDIA GPU-to-GPU communication | Fastest option; the default choice for deep learning on NVIDIA hardware |
| **Gloo** | CPU or GPU, general-purpose | More flexible, less specialized than NCCL; a solid fallback |
| **MPI** (Message Passing Interface) | HPC / research clusters | Common in legacy and research-oriented HPC environments |

> **Q: Given NCCL is fastest, is there ever a real reason to pick Gloo or MPI instead?**
> **A:** Yes — NCCL requires NVIDIA GPUs and the NCCL library specifically; it isn't an option
> at all for CPU-only training or mixed CPU/GPU setups, where Gloo is the practical choice.
> MPI shows up mainly when a team is already standardized on an existing HPC/Slurm-based
> cluster with MPI tooling in place, where matching the existing infrastructure outweighs
> NCCL's raw speed advantage. In short: NCCL is the default *when NVIDIA GPUs are the whole
> picture*; the other two exist for the cases where they aren't.

### Distributed Data Parallel (DDP)

DDP is PyTorch's flagship distributed-training paradigm. It:

- Replicates the entire model across every participating GPU.
- Gives each GPU a distinct subset of the current mini-batch to process.
- Uses an AllReduce operation to synchronize gradients across all replicas.
- Maintains computational efficiency at scale — critically, it overlaps gradient
  communication with the ongoing backward pass computation, rather than waiting for the full
  backward pass to finish before starting any communication.
- Is significantly more efficient than PyTorch's older, now-legacy `DataParallel` module
  (which used a single-process, multi-thread design with a central GPU bottleneck — DDP's
  multi-process, decentralized design is what replaced it).

This makes DDP the **industry standard for multi-GPU training in PyTorch**.

#### DDP Workflow

1. **Initialize the process group** — `dist.init_process_group()` establishes communication
   between all participating processes.
2. **Wrap the model in DDP** — `DistributedDataParallel(model, device_ids=[rank])`.
3. **Configure data sampling** — `DistributedSampler` ensures each process/GPU sees a distinct,
   non-overlapping slice of the dataset each epoch.
4. **Train with automatic gradient sync** — forward and backward passes trigger DDP's
   automatic gradient synchronization behind the scenes; no manual AllReduce call needed.
5. **Save distributed checkpoints** — checkpoint-saving must be coordinated (usually only rank
   0 writes to disk) so multiple processes don't race to write the same file.

#### Example: DDP on a Single Node

```python
import torch
import torch.distributed as dist
import torch.multiprocessing as mp

def train(rank, world_size):
    # Initialize process group
    dist.init_process_group("nccl", rank=rank, world_size=world_size)

    # Create model and move it to this process's GPU
    model = MyModel().to(rank)

    # Wrap model in DDP
    ddp_model = torch.nn.parallel.DistributedDataParallel(
        model, device_ids=[rank]
    )

    # ... training loop goes here ...

# Launch 4 processes, one per GPU
mp.spawn(train, args=(4,), nprocs=4, join=True)
```

This automatically handles gradient synchronization across all 4 GPUs — no manual AllReduce
call is needed anywhere in the training loop.

> **Q: What does `rank` actually mean here, and why is it used as both a process ID and a
> GPU index?**
> **A:** `rank` is simply "which process am I, out of `world_size` total processes" (0, 1, 2,
> 3 for 4 processes). The convention of also using it as the GPU index (`.to(rank)`,
> `device_ids=[rank]`) only works because this example launches exactly one process per GPU —
> process 0 owns GPU 0, process 1 owns GPU 1, and so on. In more complex multi-node setups,
> rank (a process's global identity across the whole cluster) and the local GPU index on that
> specific machine are tracked as two separate numbers (`rank` vs. `local_rank`), because
> "process 5 out of 32" doesn't tell you which of the 8 GPUs on its particular node it should
> use.

### Multi-Node Training with DDP

Scaling beyond a single machine adds four more requirements:

- **Communication initialization** — `init_method` needs a way for all nodes to find each
  other: a TCP address, a shared filesystem path, or environment variables.
- **Node coordination** — each node runs multiple processes, typically one per GPU on that
  node.
- **Network optimization** — high-speed interconnects (InfiniBand between nodes, NVLink within
  a node) become essential once gradient synchronization has to cross physical machines.
- **Fault tolerance** — regular checkpointing (Part 7) is what lets a multi-node run recover
  from a single node failure instead of restarting from scratch.

Done correctly, this is what lets a training job scale to hundreds or thousands of GPUs.

### Common Challenges

- **Process synchronization issues** — if process groups aren't initialized identically and
  correctly across every node, the result is a deadlock, not a clean error.
- **Communication overhead** — gradient synchronization cost grows as node count increases,
  the same compute-vs-communication tension from Part 3.
- **Hyperparameter adaptation** — learning rate and effective batch size both need re-tuning
  when scaling GPU count, or convergence quality can silently degrade.
- **Distributed debugging complexity** — a bug that only appears on one of many processes is
  exponentially harder to isolate than a single-process bug.

### Best Practices

- **Backend selection** — use **NCCL** for GPU workloads; it's substantially faster than the
  alternatives for deep learning.
- **CUDA optimization** — set `torch.backends.cudnn.benchmark = True` to let cuDNN
  auto-tune convolution kernels for the specific input sizes being used.
- **GPU binding** — pin each process to exactly one GPU via `device_ids=[rank]`, avoiding
  contention between processes for the same device.
- **Mixed precision** — Automatic Mixed Precision (AMP) reduces both compute and the volume of
  data that needs to be communicated during gradient sync.
- **Monitoring** — track training with **TensorBoard + Prometheus** for visibility across
  every node, not just the one you happen to be logged into.

### Key Takeaways

1. **Master DDP** — it's the default, industry-standard entry point for PyTorch distributed
   training.
2. **Optimize backend choice** — NCCL for GPU, Gloo for CPU, MPI for HPC-standardized clusters.
3. **Scale horizontally** — multi-node training requires real cluster orchestration and
   network tuning, not just more `nproc_per_node`.
4. **Apply best practices** — mixed precision, correctly-scaled batch sizes, and continuous
   performance monitoring.
5. **Distribute everything** — PyTorch's distributed ecosystem is built to scale from one GPU
   to thousands with the same core API.

---

## Part 7: TensorFlow Multi-GPU Training

### Why TensorFlow Multi-GPU Training?

The same underlying pressures apply regardless of framework:

- **Resource efficiency** — large models and datasets require parallel processing to train in
  a reasonable amount of time.
- **Built-in solutions** — TensorFlow ships comprehensive distribution strategies directly in
  the core library, not as a bolt-on.
- **Scalability** — the same API surface scales from single-GPU, to multi-GPU, to multi-node,
  with minimal code changes at each step.

Multi-GPU training enables faster convergence and larger batch sizes, and at this point is
close to essential for any enterprise-scale AI pipeline.

### Distribution Strategies in TensorFlow

All strategies below share a **unified API** (`tf.distribute.Strategy`), so switching between
them typically requires changing only which strategy object is instantiated, not rewriting
the training loop.

| Strategy | Scope | Best for |
|---|---|---|
| **MirroredStrategy** | Single machine, multiple GPUs | 2–8 GPUs on one node |
| **MultiWorkerMirroredStrategy** | Multiple machines | 10–100 GPUs across a cluster |
| **ParameterServerStrategy** | Distributed, asynchronous | Very large sparse models (recommenders, embeddings), 1000s of devices |
| **TPUStrategy** | Google Cloud TPUs | Tensor-heavy workloads on TPU hardware specifically |

> **Q: MirroredStrategy and MultiWorkerMirroredStrategy sound like the same idea at different
> scales — is there a meaningful mechanical difference, or is it purely "how many machines"?**
> **A:** Mechanically they're doing the same thing conceptually (synchronous replication +
> AllReduce), but `MultiWorkerMirroredStrategy` has to solve a problem `MirroredStrategy`
> never faces: workers on separate physical machines need an explicit way to discover each
> other over the network (`TF_CONFIG`, shown below) and the collective-communication layer has
> to work across machine boundaries, not just across GPUs on one motherboard's PCIe/NVLink
> fabric. So it's "the same idea, plus cluster discovery and cross-machine collective ops" —
> not a fundamentally different algorithm.

### MirroredStrategy — Single Node, Multi-GPU

**How it works:**

- Synchronous training across every GPU on one machine.
- Creates an exact model replica on each available GPU.
- Automatically splits the input batch across devices.
- Gradients are reduced (summed) and averaged across replicas.
- The identical update is then applied to every model copy.

**Best for:** setups with 2–8 GPUs in a single machine. MirroredStrategy keeps every replica's
weights identical while handling gradient synchronization behind the scenes.

#### Example: MirroredStrategy

```python
import tensorflow as tf

# Create a MirroredStrategy
strategy = tf.distribute.MirroredStrategy()

# Create the model inside the strategy's scope
with strategy.scope():
    model = create_model()
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

# Train as usual — distribution happens automatically
model.fit(dataset, epochs=5)
```

This code distributes training across every available GPU with no further configuration.
The key line is `strategy.scope()` — it ensures every model variable created inside it is
built with distribution-awareness from the start (so TensorFlow knows to replicate it and
synchronize its gradients), rather than being created as a plain single-device variable.

### MultiWorkerMirroredStrategy — Multi-Node

**Key characteristics:**

- Extends `MirroredStrategy`'s synchronous replication across **multiple servers**.
- Uses collective-communication operations (conceptually the same family as AllReduce) for
  cross-machine gradient synchronization.
- Every worker runs an identical model replica.
- Requires the **`TF_CONFIG`** environment variable so each worker knows the full cluster
  topology and its own role in it.

**Best for:** cloud or on-premise clusters with roughly 10–100 GPUs spread across multiple
machines.

#### Example: Multi-Worker Setup

Each worker needs its own `TF_CONFIG`, differing only in `task.index`:

```json
// Worker 0's TF_CONFIG:
{
  "cluster": {
    "worker": ["host1:12345", "host2:23456"]
  },
  "task": {"type": "worker", "index": 0}
}
```

1. **Cluster definition** — `TF_CONFIG` lists every worker's network address.
2. **Automatic synchronization** — TensorFlow handles the gradient-communication details once
   the cluster topology is known.
3. **Cloud integration** — this pattern works directly with Kubernetes, Google Cloud, AWS, and
   Azure cluster orchestration.

### ParameterServerStrategy

**Architecture:**

- **Asynchronous** training across distributed workers — unlike the synchronous strategies
  above, workers don't wait for each other on every step.
- Dedicated **parameter servers** store and update the model's variables.
- Workers compute gradients locally and push updates to the parameter servers, rather than
  synchronizing directly with each other.
- Optimized for very large **sparse** models — recommendation systems and embedding tables in
  particular, where most of the parameter space is touched by only a small fraction of any
  given batch.

**Scalability:** efficiently scales to **thousands** of GPUs/CPUs across a large cluster,
precisely because it doesn't need every worker to synchronize with every other worker on
every step.

> **Q: If asynchronous training doesn't need everyone to wait for each other, why isn't
> ParameterServerStrategy just always better than the synchronous strategies?**
> **A:** Asynchrony trades away a guarantee: workers can push gradient updates computed from an
> *older* version of the parameters than what's currently on the server (a "stale gradient"),
> because nothing forces every worker to be in lockstep. For dense models this staleness can
> measurably hurt convergence quality. It works well specifically for sparse models because
> any one worker's batch usually only touches a small, mostly-disjoint slice of the total
> parameter space (a few embedding rows out of millions) — so the odds of two workers'
> updates actually colliding and causing meaningful staleness are much lower than for a dense
> model where every worker touches every parameter, every step.

### Challenges in TensorFlow Multi-GPU Training

- **Communication overhead** — data transfer between GPUs/nodes becomes the bottleneck as
  scale increases, same as in PyTorch.
- **Fault tolerance** — worker or node failures disrupt training and require an explicit
  restart/recovery mechanism.
- **Hyperparameter tuning** — learning rates and batch sizes need re-adjustment for
  distributed training, exactly as with PyTorch DDP.
- **Complex setup** — correctly configuring `TF_CONFIG` and cluster topology is a common
  source of setup-time bugs.

Monitoring **scaling efficiency** (how close actual speedup is to the theoretical N×) is
critical to confirm the added hardware is actually being used effectively, not just present.

### Best Practices

- **Compilation optimization** — the **XLA compiler** fuses kernels together, reducing memory
  transfers and improving throughput.
- **Precision management** — mixed precision (FP16/BF16) reduces memory footprint and
  increases throughput.
- **Hardware management** — pin GPUs to specific workers for balanced, predictable resource
  utilization.
- **Performance analysis** — the **TensorBoard Profiler** identifies bottlenecks in the data
  pipeline and compute graph.

Always benchmark scaling efficiency before moving a configuration to production.

### Key Takeaways

- TensorFlow offers multiple distribution strategies, each optimized for a different hardware
  shape.
- **Deployment guide:** `MirroredStrategy` for a single multi-GPU machine;
  `MultiWorkerMirroredStrategy` + `ParameterServerStrategy` for multi-node scaling.
- Built-in, high-level APIs mean minimal code changes are needed to go from single-GPU to
  distributed training.

---

## Part 8: Horovod and AllReduce Explained

### Why Horovod?

Horovod is an open-source framework, originally created by **Uber**, built specifically to
simplify multi-GPU/multi-node training:

- Integrates with **TensorFlow, PyTorch, and MXNet** through one consistent API.
- Built around the **AllReduce** collective-communication algorithm for gradient
  synchronization.
- Scales from **1 to 1,000+ GPUs** with minimal changes to an existing training script.

### The Challenge Horovod Solves

- **Compute problem:** each GPU independently computes gradients on its own data partition —
  this part is easy and embarrassingly parallel.
- **Communication challenge:** those gradients must be synchronized across every GPU without
  creating a bottleneck.
- **Horovod's answer:** use AllReduce for **decentralized**, efficient communication, avoiding
  the central-bottleneck problem that traditional parameter-server architectures run into as
  scale grows.

### What Is AllReduce?

AllReduce is a collective-communication operation that:

- Sums a value (here, gradients) contributed by **every** GPU in the cluster.
- Distributes the **identical** summed result back to every one of those GPUs.
- Ensures every model replica ends the step with exactly the same, fully synchronized weights.
- Does this **without** routing all traffic through one central server — which is exactly what
  eliminates the bottleneck a naive parameter-server design would hit.

> **Q: Isn't summing everything at one place and broadcasting it back functionally identical
> to a parameter server — what's actually decentralized about that?**
> **A:** The *result* is the same (everyone ends up with the same sum); the *mechanism* to get
> there is what differs. A parameter server design has one (or a small few) designated
> machine(s) that every worker sends data *to* and receives updates *from* — that machine's
> network bandwidth is a hard ceiling on total throughput, and it's a single point of failure.
> Ring-AllReduce (below) instead has every GPU exchange data only with its two ring neighbors,
> in multiple rounds, so no single machine ever needs to receive data from all N-1 others at
> once — the aggregation work and the bandwidth demand are spread evenly across every
> participant instead of concentrated in one place.

#### Worked Example

1. **Step 1 — local computation:** 4 GPUs each independently compute their own gradients:
   `g₁, g₂, g₃, g₄`.
2. **Step 2 — sum all gradients:** the AllReduce operation combines them:
   `G = g₁ + g₂ + g₃ + g₄`.
3. **Step 3 — broadcast the result:** the identical sum `G` is distributed back to all 4 GPUs.
4. **Step 4 — weight update:** every GPU updates its local weights using the same `G`, keeping
   all four replicas in sync.

### Horovod's Architecture: Ring-AllReduce

Horovod implements **Ring-AllReduce**, a specific, bandwidth-efficient way of performing the
AllReduce operation above:

- GPUs are logically arranged in a **ring** (GPU 1 → GPU 2 → GPU 3 → ... → back to GPU 1).
- Each GPU communicates **only with its immediate neighbors** in the ring — never with every
  other GPU directly.
- Gradients are broken into chunks and exchanged in multiple small steps around the ring,
  rather than being sent as one giant transfer.
- Communication is designed to **overlap with computation**, so the network isn't sitting idle
  while the GPU computes, or vice versa.
- The result: bandwidth is used close to optimally, with no single node ever acting as a
  central bottleneck.

This architecture works the same way whether it's running across GPUs within one node or
across many nodes in a cluster.

> **Q: Why a ring specifically, and not some other topology (a tree, say)?**
> **A:** A ring guarantees every GPU sends and receives exactly the same, evenly-balanced
> amount of data per round — no GPU is ever a "hub" handling more traffic than its neighbors.
> This is what lets Ring-AllReduce's total communication cost per GPU stay effectively constant
> as GPU count grows (rather than growing with N, as a naive centralized scheme would), which
> is the specific property that lets Horovod claim near-linear scaling out to very large GPU
> counts.

### Using Horovod in Training

#### PyTorch Integration Example

```python
import horovod.torch as hvd

hvd.init()
torch.cuda.set_device(hvd.local_rank())

model = model.to(hvd.local_rank())
optimizer = optim.Adam(model.parameters())

optimizer = hvd.DistributedOptimizer(
    optimizer,
    named_parameters=model.named_parameters(),
)

hvd.broadcast_parameters(model.state_dict(), root_rank=0)
```

With just these few lines wrapped around an existing single-GPU script, the training loop
becomes fully distributed-ready. `hvd.broadcast_parameters` is what ensures every process
starts from the exact same initial weights, before any training step runs.

### Benefits of Horovod

- **Simplicity** — minimal changes needed to an existing training script.
- **Framework-agnostic** — works across TensorFlow, PyTorch, and MXNet with one API.
- **Efficiency** — Ring-AllReduce maximizes bandwidth utilization.
- **Scalability** — near-linear scaling as GPUs are added.
- **Adoption** — strong community and enterprise support.

### Limitations of Horovod

- **Infrastructure requirements** — needs high-speed interconnects (NVLink/InfiniBand) to
  actually realize its efficiency advantage; on slower networks the benefit shrinks.
- **Data parallelism only** — Horovod addresses data parallelism specifically, not model
  parallelism — large models that don't fit on one GPU still need a separate strategy (Part 5)
  layered on top.
- **Debugging complexity** — tracing an issue across hundreds of GPUs remains hard regardless
  of framework.
- **Competes directly with PyTorch's native DDP** — for pure-PyTorch shops, DDP is often the
  simpler, equally-capable default (see comparison below).

### Horovod vs. DDP

| | PyTorch DDP | Horovod |
|---|---|---|
| Integration | Tightly built into PyTorch | Framework-agnostic, external library |
| Best fit | Pure-PyTorch workflows | Mixed TensorFlow/PyTorch/MXNet environments |
| Speed (pure PyTorch) | Often faster, given native integration | Comparable, with added abstraction overhead |
| Dependencies | None beyond PyTorch itself | Requires the separate Horovod library/build |
| Best for | PyTorch-only teams | Heterogeneous clusters running multiple frameworks |

The right choice depends on infrastructure and framework mix — many enterprises with diverse
ML stacks still prefer Horovod specifically *because* of its cross-framework flexibility, even
where DDP alone would be marginally faster for the PyTorch-only portion of their workloads.

### Key Takeaways

1. **AllReduce is the foundation** of efficient, decentralized gradient synchronization.
2. **Ring-AllReduce is Horovod's specific implementation**, maximizing bandwidth via
   peer-to-peer, neighbor-only communication.
3. **Minimal code changes** are needed to make an existing script distributed.
4. **Best suited** for large-scale infrastructure running a diverse mix of ML frameworks.

---

## Part 9: Fault Tolerance in Distributed Training

### Why Fault Tolerance Matters

Once training spans hundreds to thousands of GPUs:

- Failures become **inevitable**, not merely possible — at that scale, some component fails
  often enough that "if" becomes "when."
- Without proper fault tolerance, a single failure forces the **entire job to restart from
  scratch**.
- That dramatically increases both training cost and time-to-model.

### Types of Failures

| Category | Examples |
|---|---|
| **Hardware** | GPU overheating, VRAM corruption, power fluctuations, disk failures |
| **Software** | Memory leaks, CUDA driver bugs, framework deadlocks, OOM exceptions |
| **Network** | Node-to-node communication failures, intermittent packet loss, bandwidth saturation, NIC failures |
| **Scheduler/cluster** | Kubernetes pod evictions, Slurm job preemptions, resource contention, planned maintenance downtime |

Each category needs its own specific handling strategy — there's no single fix that covers
all four.

### Checkpointing

The foundation of fault tolerance in ML training:

- Periodically save **model weights + optimizer state** to durable storage.
- On failure, training resumes from the last saved checkpoint instead of from scratch.
- Common formats: PyTorch's **`.pt`**, TensorFlow's **`.ckpt`**.
- The core tradeoff: checkpointing more frequently reduces how much work is lost on failure,
  but adds I/O overhead to every checkpoint interval — checkpointing too rarely risks losing
  hours of compute; checkpointing too often can meaningfully slow down the run itself.

This is the **industry-standard** practice for LLMs, computer vision, and any other
compute-intensive training workload. Checkpoint files themselves can range from **megabytes to
terabytes**, depending on model size.

> **Q: How do teams actually decide the checkpoint interval, in practice?**
> **A:** By weighing the checkpoint's write cost (how long saving takes, and how much it stalls
> the training step) against the expected cost of *not* having a recent checkpoint when a
> failure hits — which itself depends on how failure-prone the cluster has been recently. A
> common pattern is to checkpoint every N minutes or every K steps (whichever is more
> frequent), tuned so checkpoint I/O stays a small single-digit percentage of total training
> time, and to make individual checkpoints *incremental* (only changed shards, not a full model
> dump) specifically so this interval can be tightened without paying full I/O cost every time.

### Elastic Training

- **Dynamic adaptation** — the training job automatically adjusts to however many GPUs/nodes
  are currently available.
- **Resizable jobs** — resources can be added or removed *while training is actively running*.
- **Failure resilience** — an individual node failing doesn't force a full restart; the job
  simply continues with the remaining, healthy nodes.

Technologies enabling this: **PyTorch Elastic (TorchElastic)**, **Horovod Elastic**, **Ray
Train**, **DeepSpeed Elastic**.

### Gradient & State Synchronization Under Failure

A concrete illustration of what happens when one node in a 4-node AllReduce group fails
mid-step:

- **GPU Node A** — computes gradients, participates in AllReduce normally.
- **GPU Node B** — computes gradients, participates in AllReduce normally.
- **GPU Node C** — failure detected; enters its recovery path instead of participating.
- **GPU Node D** — computes gradients; AllReduce (now adapted to the remaining healthy nodes)
  ensures the surviving nodes stay consistent with each other.
- **Checkpoint & recovery** — Node C's state is restored via a combination of the last
  checkpoint and a resync against the currently-running nodes, then rejoins.

**Critical components this depends on:**

- Gradient consistency across the surviving nodes.
- Optimizer state synchronization (not just model weights — momentum buffers, Adam's moment
  estimates, etc. all need to stay consistent too).
- AllReduce-aware checkpointing, so a checkpoint taken mid-training is actually consistent
  across all replicas, not a mismatched snapshot.

**What makes this harder in practice:**

- **Sharded optimizers** (ZeRO, FSDP) — since optimizer state itself is split across GPUs,
  recovering one failed GPU means reconstructing *its specific shard*, not just any generic
  copy.
- **Model & pipeline parallelism** — a failed GPU here doesn't just lose a data replica, it
  loses a specific, non-redundant *slice of the model* that nothing else has a copy of, making
  recovery structurally harder than under pure data parallelism.
- **Resync speed at scale** — the more nodes involved, the longer a full resync after a
  failure takes, which is itself a cost that has to be weighed against checkpoint frequency.

### Infrastructure-Level Fault Tolerance

- **Kubernetes** — pod auto-restarts plus rescheduling policies bring a failed pod back
  automatically.
- **Slurm** — job retries plus checkpoint-aware continuation.
- **Cluster managers generally** — automatic task reassignment combined with ongoing GPU
  health monitoring, so a degrading (not yet failed) GPU can be proactively drained.

The key point: infrastructure-level fault tolerance (the orchestrator restarting a pod) has to
work **in concert** with the ML framework's own checkpoint logic — a restarted pod that doesn't
know how to resume from a checkpoint is no better than one that never restarted at all.

### Fault Tolerance in Practice

- **OpenAI-style GPT training** — regular checkpointing every few hours, distributed across
  multiple data centers with redundant storage.
- **Google DeepMind-style TPU training** — elastic training across thousands of TPUs with
  sophisticated checkpoint orchestration.
- **Netflix-style ML pipelines** — auto-healing pipelines built on Kubernetes and
  container-based recovery.
- **Financial services** — compliance-critical AI systems where fault tolerance is a
  *regulatory* requirement, not just an engineering nicety.

**Without proper fault tolerance, weeks of training can be lost overnight** — this is the
single sentence that justifies all of the above infrastructure investment.

### Remaining Challenges in Fault Tolerance

- **Storage bottlenecks** — checkpoint files reaching gigabytes-to-terabytes create real I/O
  and storage-capacity challenges of their own.
- **Model-parallelism complexity** — elastic training becomes significantly harder once the
  model itself (not just the data) is sharded across GPUs.
- **Restart overhead** — a poorly-sharded job faces high overhead recovering from a failure,
  even with checkpoints in place.
- **Performance-vs-safety tradeoff** — every fault-tolerance mechanism (checkpointing,
  redundancy, health checks) costs some amount of steady-state performance; there is no
  zero-cost version of this.

This remains an **active area of research and infrastructure engineering** — there is no
single, fully solved answer yet, especially at the largest scales.

### Best Practices

- **Automate checkpointing** — versioned cloud storage (S3/GCS) with consistent naming
  conventions, not manual/ad-hoc saves.
- **Incremental checkpoints** — save only *changed* weights/shards instead of a full model
  dump each time, to reduce I/O cost per checkpoint.
- **Test recovery flows** — deliberately validate that failure recovery actually works
  *before* relying on it in a production training run, not the first time a real failure
  happens.
- **Multi-level resilience** — combine elastic training with cluster-level failover, rather
  than relying on either alone.

Always budget extra cost and time specifically for resilience — it is not free, and treating
it as an afterthought is how weeks of compute get lost.

### Key Takeaways

- **100% failure rate at scale** — at large enough scale, failures are guaranteed, not merely
  possible.
- **Up to a 10× cost impact** — training costs can grow by an order of magnitude without
  proper fault tolerance in place.
- **Three core strategies** — checkpointing, elastic training, and infrastructure-level
  resilience form the foundation of any real defense.
- **Infrastructure and ML frameworks must cooperate** — neither alone is sufficient.
- **Prevention costs less than recovery** — the recurring theme across every section above.

---

## Part 10: Hands-On Lab — DDP Training ResNet-18 on CIFAR-10

**Goal:** Train ResNet-18 on the CIFAR-10 dataset using PyTorch's Distributed Data Parallel
(DDP) across multiple GPUs.
**Time:** ~90 minutes.
**Tools:** Python, PyTorch, a CUDA-enabled system with 2+ GPUs.

> **Q: Why CIFAR-10 and ResNet-18 specifically for a distributed-training exercise, instead of
> a bigger, more "realistic" model?**
> **A:** Because the point of this lab is to observe the *distributed-training mechanics*
> (process groups, `DistributedSampler`, gradient sync) working correctly — not to train a
> state-of-the-art model. A small model and dataset mean each epoch finishes in seconds, so you
> can iterate on the DDP setup itself quickly, and any bug in the distributed wiring shows up
> immediately rather than after a multi-hour wait. The same code pattern scales directly to a
> much larger model later.

### Step 1: Verify Your Environment

Check GPU availability:

```bash
nvidia-smi
```

Confirm at least **2 GPUs** are listed.

Check that PyTorch sees CUDA correctly:

```python
import torch
print(torch.cuda.device_count())   # should be >= 2
print(torch.cuda.is_available())   # should be True
```

### Step 2: Set Up the CIFAR-10 Dataset

```python
import torch
import torchvision
import torchvision.transforms as transforms

transform = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.RandomCrop(32, padding=4),
    transforms.ToTensor(),
])

trainset = torchvision.datasets.CIFAR10(
    root='./data', train=True, download=True, transform=transform
)
testset = torchvision.datasets.CIFAR10(
    root='./data', train=False, download=True, transform=transforms.ToTensor()
)
```

### Step 3: Define the ResNet-18 Model

```python
import torchvision.models as models
import torch.nn as nn

def build_model():
    model = models.resnet18(weights=None, num_classes=10)
    return model
```

### Step 4: Write the Full DDP Training Script

Create `train_ddp.py`, combining everything above into a single distributed-aware script:

```python
import os
import torch
import torch.distributed as dist
import torch.multiprocessing as mp
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import torchvision.models as models
from torch.nn.parallel import DistributedDataParallel as DDP


def setup(rank, world_size):
    dist.init_process_group("nccl", rank=rank, world_size=world_size)
    torch.cuda.set_device(rank)


def cleanup():
    dist.destroy_process_group()


def train(rank, world_size):
    setup(rank, world_size)

    transform = transforms.Compose([transforms.ToTensor()])
    trainset = torchvision.datasets.CIFAR10(
        root='./data', train=True, download=True, transform=transform
    )
    train_sampler = torch.utils.data.distributed.DistributedSampler(
        trainset, num_replicas=world_size, rank=rank
    )
    trainloader = torch.utils.data.DataLoader(
        trainset, batch_size=128, sampler=train_sampler
    )

    model = models.resnet18(weights=None, num_classes=10).to(rank)
    model = DDP(model, device_ids=[rank])

    criterion = nn.CrossEntropyLoss().to(rank)
    optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9)

    for epoch in range(2):  # kept short for this demo
        train_sampler.set_epoch(epoch)
        running_loss = 0.0
        for inputs, labels in trainloader:
            inputs, labels = inputs.to(rank), labels.to(rank)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        print(f"[GPU {rank}] Epoch {epoch + 1}, Loss: {running_loss / len(trainloader)}")

    cleanup()


def main():
    world_size = torch.cuda.device_count()
    mp.spawn(train, args=(world_size,), nprocs=world_size, join=True)


if __name__ == "__main__":
    main()
```

> **Q: What does `DistributedSampler` actually do, and why call `train_sampler.set_epoch(epoch)`
> every epoch?**
> **A:** `DistributedSampler` is what turns "one dataset" into "N non-overlapping slices, one
> per rank" — without it, every GPU would iterate over the *entire* dataset independently,
> silently multiplying the effective batch size and wasting most of the parallelism this whole
> exercise exists to gain. `set_epoch(epoch)` reshuffles which examples go to which rank each
> epoch, using the epoch number to seed that shuffle — skipping it means every rank sees the
> exact same slice of data in the exact same order on every single epoch, which hurts training
> quality in exactly the way skipping shuffling would in ordinary single-GPU training.

### Step 5: Launch Distributed Training

```bash
python -m torch.distributed.run --nproc_per_node=2 train_ddp.py
```

- `--nproc_per_node=2` launches training across 2 GPUs (adjust to match how many are
  available).
- Each GPU runs its own independent process, per the script above.

Expected output: **parallel loss logs, one line per GPU, per epoch.**

### Step 6: Monitor GPU Utilization

In a separate terminal:

```bash
watch -n 1 nvidia-smi
```

Confirm multiple processes are actively using the GPUs — this is the direct, visible
confirmation that training is genuinely running in parallel, not just launched in parallel.

### Step 7: Evaluate the Trained Model

Save a checkpoint from only one process (to avoid every rank racing to write the same file):

```python
if rank == 0:  # only one process saves
    torch.save(model.state_dict(), "resnet_ddp.pth")
```

Load it back for evaluation:

```python
model = models.resnet18(weights=None, num_classes=10)
model.load_state_dict(torch.load("resnet_ddp.pth"))
model.eval()
```

### Step 8: Clean Up

Kill any lingering training processes if needed:

```bash
pkill -f train_ddp.py
```

This frees GPU memory held by any process that didn't exit cleanly.
