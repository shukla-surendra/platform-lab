# Operating Systems, Part 6: Inter-Process Communication (IPC)

[Part 1](01_processes_and_threads.md) established that processes are isolated by design —
one process cannot simply read another's memory. This part covers the mechanisms the
kernel provides so isolated processes can still cooperate deliberately, and closes out the
[`os_concepts/`](README.md) track by bridging into cross-*machine* communication, covered
starting in [`system_design_foundation`'s Part
3](../system_design_foundation/00_prerequisite_concepts/03_communication_and_resilience.md).

## The Core Design Question: Isolation Was the Point — So How Do You Opt Back In?

Every IPC mechanism is really answering the same question differently: *how much
throughput versus how much safety/structure do you want when two isolated processes need
to exchange data?* The mechanisms below are ordered roughly along that axis, from
"kernel mediates every byte" (safe, structured, slower) to "kernel gets out of the way
after setup" (fast, but you own the safety yourself).

## The Mechanisms

- **Pipes.** An in-kernel byte stream connecting two processes, almost always set up
  between a parent and its children (an unnamed pipe is inherited across `fork()`, tying
  back to [Part 1's copy-on-write discussion](01_processes_and_threads.md#a-concrete-worked-example-fork-and-copy-on-write)).
  What a shell's `|` operator wires up directly. One-directional, ordered, byte-stream — no
  message boundaries, just like a TCP socket at the byte level.
- **Named pipes (FIFOs).** The same idea as a pipe, but given a name in the filesystem so
  unrelated processes (no parent/child relationship) can open and use it.
- **Message queues.** Kernel-managed, discrete messages rather than an undifferentiated
  byte stream — the kernel preserves message boundaries and can support priority ordering.
  Useful when structure matters more than raw throughput.
- **Shared memory.** The fastest mechanism, and structurally different from the others: the
  kernel maps the *same physical frames* into both processes' page tables (the same
  primitive from [Part 3](03_virtual_memory_and_paging.md#why-this-matters-in-practice) —
  multiple page table entries pointing at one physical frame). After that one-time setup,
  reading/writing shared memory is a plain memory access with **no kernel involvement at
  all** — no syscall, no data copy through the kernel. That speed is exactly why it's the
  most dangerous mechanism: the kernel isn't mediating access, so nothing stops two
  processes from corrupting shared data the same way two unsynchronized threads would (see
  [Part 4](04_concurrency_locks_and_deadlock.md)) — shared memory needs its own
  cross-process synchronization (a semaphore or a mutex placed *in* the shared region
  itself), which is a strictly harder problem than in-process locking because you can't
  assume both sides are even alive.
- **Sockets.** The general-purpose mechanism — works for two processes on the same machine
  (a Unix domain socket) *or* two processes on different machines entirely (a TCP/UDP
  socket over the network), with the same API either way. This is the deliberate on-ramp
  into distributed systems: everything from here forward in this repo — RPC, message
  queues at the distributed-systems scale, load balancers — is sockets plus a protocol
  layered on top, covered starting in [`system_design_foundation`'s Part
  3](../system_design_foundation/00_prerequisite_concepts/03_communication_and_resilience.md).
- **Signals.** Not a data-transfer mechanism at all — a narrow, asynchronous notification
  ("something happened": `SIGKILL`, `SIGTERM`, `SIGCHLD`) delivered to a process, which can
  install a handler or take the OS's default action (usually terminate). Worth knowing as
  categorically different from the others: signals carry almost no payload, they interrupt
  a process's normal control flow rather than being read/written like a stream.

## Why This Matters in Practice

**"Why is shared memory so much faster than a pipe for large data?"** A pipe requires the
kernel to copy data from the writing process's buffer into a kernel buffer, then copy it
again out to the reading process — two copies, both crossing the user/kernel boundary from
[Part 5](05_context_switching_and_kernel_boundary.md#the-kerneluser-boundary-a-different-kind-of-switch).
Shared memory requires zero copies after setup — both processes are reading/writing the
same physical frames directly. This is the same "avoid the kernel round trip on the hot
path" idea behind zero-copy networking techniques at the distributed-systems scale — one
mechanism, recurring at every layer.

**Choosing a mechanism is choosing where safety comes from.** A message queue or pipe gets
safety "for free" from the kernel serializing access — you can't get a torn/partial message
because the kernel enforces message or stream discipline. Shared memory gets you speed but
makes you responsible for that same safety yourself, with the same tools ([Part 4](04_concurrency_locks_and_deadlock.md))
used for in-process synchronization, just harder to apply correctly across process
boundaries. This mirrors [Part 4's lock-granularity trade-off](04_concurrency_locks_and_deadlock.md#why-this-matters-in-practice)
almost exactly: more structure and kernel mediation costs throughput; less costs you having
to get the synchronization right yourself.

**Why this is the natural bridge to distributed systems.** A socket between two processes
on the same machine and a socket between two processes on different machines use
*literally the same interface* — `connect()`, `send()`, `recv()`. Everything that makes
distributed systems hard (partial failure, unbounded latency, no shared clock — the
material starting in [`system_design_foundation`'s Part
3](../system_design_foundation/00_prerequisite_concepts/03_communication_and_resilience.md))
isn't a difference in the *mechanism* of talking to another process — it's what changes
once that other process is no longer guaranteed to be reachable, alive, or fast, the way a
same-machine IPC call implicitly assumes it can be.

## Quick Self-Check

- Why does shared memory require zero kernel involvement after setup, while a pipe requires
  data to be copied twice?
- Why is shared memory simultaneously the fastest and the most dangerous IPC mechanism?
- What's categorically different about a signal compared to every other mechanism in this
  doc?
- Why does a Unix domain socket and a TCP socket sharing the same API matter for how you'd
  reason about scaling a same-machine design into a distributed one?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Trade-off framing (the default):** "I wouldn't list IPC mechanisms as unrelated
  options — I'd frame them on one axis: how much the kernel mediates versus how much
  throughput you get. Pipes and message queues get safety from kernel mediation at the cost
  of copying data through the kernel twice; shared memory skips both copies and the kernel
  entirely after setup, which is exactly why it's fast and exactly why it's dangerous
  without your own synchronization."
- **Mechanism framing (good for 'why is shared memory fast'):** "I'd connect it back to
  paging — shared memory isn't a special kernel feature bolted on separately, it's the same
  primitive as copy-on-write `fork()`: multiple page table entries, possibly in different
  processes, pointing at one physical frame. Reading and writing it afterward is a plain
  memory access, not a syscall."
- **Bridge-to-distributed-systems framing (good for closing out the whole track):** "I'd
  point out that sockets already generalize across the same-machine/different-machine line
  — same API either way. What makes distributed systems categorically harder isn't a new
  communication mechanism, it's that the other side is no longer guaranteed to be
  reachable, alive, or fast, which is the whole subject of the fallacies-of-distributed-computing
  material this bridges into."

### Vocabulary Builder

- **zero-copy** (adj. phrase) — a data path that avoids copying data through an
  intermediate kernel buffer; shared memory achieves this after setup, pipes don't.
- **message boundary** (n. phrase) — the property of message queues (preserved) versus
  pipes/streams (not preserved — just an undifferentiated byte stream).
- **Unix domain socket** (n. phrase) — a same-machine socket using the standard socket API
  without going through the network stack; the structural link between local IPC and
  networked communication.
- **signal** (n.) — an asynchronous, near-payload-free notification delivered to a process,
  categorically different from every data-transfer IPC mechanism.
- **"…the kernel mediates, or you do"** — a compact phrase for the safety-versus-throughput
  choice every IPC mechanism makes.

---

**Previous:** [Part 5: Context Switching & the Kernel/User Boundary](05_context_switching_and_kernel_boundary.md)  |  **Next:** [Part 7: The Boot Process — Power-On to Kernel](07_boot_process_power_on_to_kernel.md)
