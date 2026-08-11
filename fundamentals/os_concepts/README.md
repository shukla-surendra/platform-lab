# Operating Systems Interview Prep

Core OS fundamentals as asked at top-tier companies — usually a 30-45 minute
"CS fundamentals" round (common at Google, Meta, Amazon, Microsoft, and most
infra-heavy teams elsewhere) that sits alongside the coding round rather than
replacing it. The bar isn't reciting textbook definitions; it's being able to
explain *why* a mechanism exists (what problem it solves, what breaks without
it) and reason about a concrete scenario ("what happens if two threads
increment the same counter without a lock").

Each doc follows the same first-principles structure as
[`system_design_foundation/00_prerequisite_concepts/`](../system_design_foundation/00_prerequisite_concepts/01_performance_and_scale.md):
problem → mechanism → why it matters practically, with a worked example, a
**Quick Self-Check**, and an **Articulate It** section for how to say it out
loud in an interview.

## How to use this

1. Read in order — later docs assume earlier ones (concurrency assumes you
   already know what a thread is; context switching assumes you know what a
   process's state consists of).
2. Each doc ends with **Quick Self-Check** questions — answer them out loud,
   unscripted, before moving on. If you can't, re-read the mechanism section,
   don't just reread the definition.
3. These are conceptual primers, not coding problems — there's no
   `solution.py` here. If a topic below has a natural coding companion, it's
   cross-linked from that doc (e.g. concurrency primitives link to problems
   that use locks).

## Topics (in suggested order)

| # | Doc | Topic |
|---|-----|-------|
| 1 | [`01_processes_and_threads.md`](01_processes_and_threads.md) | Processes vs. Threads |
| 2 | [`02_cpu_scheduling.md`](02_cpu_scheduling.md) | CPU Scheduling |
| 3 | [`03_virtual_memory_and_paging.md`](03_virtual_memory_and_paging.md) | Virtual Memory & Paging |
| 4 | [`04_concurrency_locks_and_deadlock.md`](04_concurrency_locks_and_deadlock.md) | Concurrency: Race Conditions, Locks & Deadlock |
| 5 | [`05_context_switching_and_kernel_boundary.md`](05_context_switching_and_kernel_boundary.md) | Context Switching & the Kernel/User Boundary |
| 6 | [`06_interprocess_communication.md`](06_interprocess_communication.md) | Inter-Process Communication (IPC) |
| 7 | [`07_boot_process_power_on_to_kernel.md`](07_boot_process_power_on_to_kernel.md) | The Boot Process: Power-On to Kernel |
| 8 | [`08_disk_layout_gpt_and_boot_entries.md`](08_disk_layout_gpt_and_boot_entries.md) | Disk Layout: GPT, the ESP & Boot Entries |

Parts 7-8 are a pair — 7 is the boot *sequence*, 8 is the disk *structures* that
sequence depends on. Read 7 first.

## Why these topics

This is the set that actually recurs across FAANG-style loops, not an
exhaustive undergrad-OS syllabus:

- **Processes vs. threads** and **concurrency** show up constantly as
  "design a thread-safe cache" or "what's the difference between X and Y"
  warm-up questions.
- **CPU scheduling** and **context switching** are where "why is my
  multi-threaded code slower than expected" debugging questions live.
- **Virtual memory & paging** underpins nearly every "why did this process
  get OOM-killed" or "what is a page fault" question, and is a direct
  prerequisite for understanding the container/cgroups material that shows
  up in infra-adjacent system design rounds.
- **IPC** is the connective tissue question once a candidate has established
  they understand processes — "how would two processes on the same machine
  talk to each other" — and bridges naturally into the distributed-systems
  material in [`system_design_foundation/`](../system_design_foundation/README.md).

- **Boot sequence and disk layout** (Parts 7-8) are the odd pair out, and worth
  being honest about: they're rarely asked directly in a general SWE loop. They
  earn their place for two other reasons. First, they're the mechanical
  explanation for questions that *are* asked constantly in infra rounds — why a
  container starts in milliseconds and a VM in tens of seconds, what a machine
  image actually contains, where cold-start latency goes. Second, they're the
  concrete instance of bootstrapping and chain-of-trust, which recur well
  beyond boot. Treat them as supporting material for infra-flavoured loops
  (VMware, Adobe, cloud-platform teams), not as core fundamentals-round prep.

Device drivers and filesystem internals remain out of scope — closer to a
systems/kernel-specialist track than a general fundamentals round.
