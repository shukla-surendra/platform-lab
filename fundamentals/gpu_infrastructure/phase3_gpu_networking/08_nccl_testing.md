# NCCL Testing: Proving the Fabric Works Before Trusting It With a Training Run

Part of [Phase 3 — GPU Networking](../README.md#phase-3-gpu-networking). Closes out Phase
3 — builds on
[`06_nccl_and_collective_communication.md`](06_nccl_and_collective_communication.md) (the
operations being tested) and
[`07_rdma_roce_infiniband.md`](07_rdma_roce_infiniband.md) (the fabric being validated).
Everything in those two chapters was "here's what should happen" — this chapter is "here's
how you prove it actually is happening, on this specific cluster, today."

## Clarify

Every failure mode named in Phases 2-3 so far shares one shape: **the system keeps
running, just slower, with no error** — a degraded NVLink path, a fallback from RDMA to
TCP, a suboptimal NCCL algorithm choice. None of these throw an exception. A training job
launched onto a cluster with one of these problems will complete, produce a correct model,
and simply take longer and cost more than it should — often for weeks, undetected, because
nothing failed. `nccl-tests` exists specifically to catch this class of problem
*before* a real, expensive job is the first thing to notice it.

## Core Concepts

### `nccl-tests` — what it actually is

`nccl-tests` (NVIDIA's own open-source benchmark suite, not a training framework) runs the
same collective operations named in
[`06_nccl_and_collective_communication.md`](06_nccl_and_collective_communication.md#the-collective-operations-precisely-defined)
— all-reduce, all-gather, reduce-scatter, broadcast — at increasing message sizes, and
reports the achieved bandwidth and latency for each. It does no actual training-relevant
work; its only output is a bandwidth/latency number, sized against the theoretical maximum
the hardware advertises. It is the load-test equivalent of "does this network deliver the
throughput its spec sheet promises," applied to the specific operations NCCL actually
performs, not generic `iperf`-style point-to-point throughput.

```bash
# The canonical single-node sanity check, run across all 8 GPUs:
./build/all_reduce_perf -b 8M -e 8G -f 2 -g 8

#   -b 8M   starting message size (8 megabytes)
#   -e 8G   ending message size (8 gigabytes) — sweeping across sizes
#           matters because small-message latency and large-message
#           bandwidth stress genuinely different parts of the path
#   -f 2    multiply message size by 2 each step
#   -g 8    use 8 GPUs

# The multi-node version launches via MPI or a job scheduler, spanning
# nodes so the cross-node RDMA/EFA path from 07_rdma_roce_infiniband.md
# is what's actually being exercised, not just intra-node NVLink.
```

### Reading the output against a known baseline — the actual skill

The output is a table of message size vs. achieved bandwidth (in GB/s) and latency (in
microseconds). The number alone means nothing without a reference point — the actual
skill is comparing the achieved bandwidth at large message sizes against the hardware's
theoretical ceiling:

```
Expected (healthy) result, 8× H100 intra-node (NVSwitch), large messages:
  Achieved bus bandwidth approaching ~370-450 GB/s per-GPU-pair-equivalent
  (NCCL's "bus bandwidth" metric already accounts for the all-reduce
  algorithm's inherent 2x-ish data-movement overhead vs. raw link speed —
  it is NOT the same number as the raw ~900GB/s NVLink figure from
  05_nvlink_nvswitch_topology.md, and comparing against that raw number
  directly is a common, avoidable misread of the tool's own output)

Degraded result, same hardware, misconfigured topology:
  Achieved bandwidth well below that range, at large message sizes
  specifically (small-message latency can look fine even when large-
  message bandwidth is badly degraded, since they stress different
  things) — this is the signature of a link running at a lower speed
  than expected, or NCCL having fallen back to a suboptimal algorithm
  or transport (06_nccl_and_collective_communication.md's failure mode).
```

**Why this connects directly to `NCCL_DEBUG=INFO`**: a degraded `nccl-tests` number tells
you *that* something is wrong; running the same test with `NCCL_DEBUG=INFO` set is how you
find out *what* — the transport-selection log lines from
[`06_nccl_and_collective_communication.md`](06_nccl_and_collective_communication.md#checking-nccl-is-actually-using-the-fast-path-nccl_debug)
are the diagnostic step that follows a bad `nccl-tests` result, not a separate,
unconnected tool.

### Where this fits in a fleet's actual lifecycle

`nccl-tests` isn't a one-time install-verification step — it's a recurring gate at
several distinct points, each catching a different failure:

- **New node provisioning** — before a newly provisioned node joins the scheduling pool,
  running `nccl-tests` intra-node confirms NVLink/NVSwitch is healthy on that specific
  physical machine (hardware varies unit to unit — a spec sheet describes the model, not
  the individual unit).
- **New node-pair/cluster validation** — running it across a candidate multi-node group
  confirms the RDMA/EFA fabric and cluster placement group setup (from
  `07_rdma_roce_infiniband.md`) are actually delivering the expected cross-node
  bandwidth *for that specific placement*, not just that the instances individually have
  EFA enabled.
- **Ongoing fleet health / regression detection** — periodic re-runs catch degradation
  over time (a NIC firmware regression, a switch-level issue introduced by unrelated
  infrastructure changes) before it silently erodes every job's throughput.
- **Post-incident verification** — after any hardware replacement or network-layer
  change, before returning a node to the scheduling pool, confirming the fix actually
  restored expected bandwidth rather than trusting that the replacement alone was
  sufficient.

This is the concrete implementation of the **validate** step named (without detail) in
[`00_mental_model_and_roadmap.md`'s stack diagram](../00_mental_model_and_roadmap.md) and
in the fleet lifecycle this track's Phase 6 will cover in depth — `nccl-tests` is
specifically *what* gets run at that step, not an abstract placeholder for "some check
happens here."

## Deep-Dive: why message-size sweeping, not a single number, is the actual test

A single-message-size test would miss real, distinct failure classes:

- **Small messages** — dominated by **latency** (fixed per-call overhead: kernel launch,
  synchronization), not bandwidth. A problem here (unusually high latency at small sizes)
  often points to a software/driver-layer issue — an unexpectedly slow code path being
  taken for setup/teardown — rather than a raw link-speed problem.
- **Large messages** — dominated by **bandwidth** (how fast bytes actually move once the
  transfer is underway). A problem here specifically, with small-message latency still
  normal, is the classic signature of a link running below its rated speed, or a fallback
  to a slower transport for large-transfer offload — exactly the class of problem the
  worked example in `nccl-tests`'s "degraded result" above describes.

Sweeping across sizes is how the tool distinguishes these two failure classes from a
single run, rather than needing two separate targeted tests.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Run `nccl-tests` at every node-provisioning step | Catches per-unit hardware variance before it reaches production workloads | Adds provisioning-pipeline time; needs a maintained expected-baseline reference per instance type |
| Run only occasionally / only on incident | Lower operational overhead | Degradation can silently persist for weeks between checks, costing real compute-hours before being caught |
| Compare against a fleet-wide historical baseline vs. the vendor spec sheet | Catches gradual fleet-wide drift a spec-sheet comparison alone would miss | Requires storing and maintaining that baseline over time — its own small piece of infrastructure |

## Failure Modes to Raise Proactively

- **Comparing NCCL's reported "bus bandwidth" directly against the raw NVLink spec
  number** — as shown above, NCCL's bus-bandwidth metric already accounts for the
  all-reduce algorithm's inherent data-movement overhead; a naive raw-spec comparison
  makes a healthy result look artificially degraded, and would prompt chasing a problem
  that doesn't exist.
- **Only checking large-message bandwidth, or only checking small-message latency** — as
  the deep-dive shows, these catch genuinely different failure classes; checking only one
  half of the sweep misses the other.
- **Treating a passing `nccl-tests` run at provisioning time as permanent** — hardware and
  firmware degrade over time; a one-time pass doesn't substitute for the recurring
  fleet-health re-runs named above.

## Make It Yours

- If you ever provision or gain access to a multi-GPU instance, run `all_reduce_perf`
  yourself and compare the reported bus bandwidth against the instance type's known-good
  range (not the raw NVLink spec number) — the exact distinction the failure mode above
  warns against getting wrong.
- Next time `NCCL_DEBUG=INFO` output is inspected (from the prior chapter's exercise),
  pair it with an `nccl-tests` run on the same nodes — practice using the two together as
  a diagnose-then-confirm pair rather than as separate, unrelated tools.

## Practice Questions

1. Why does a healthy `nccl-tests` result report a "bus bandwidth" number lower than the
   raw NVLink spec, and why is that not itself a sign of a problem?
2. A cluster shows normal small-message latency but degraded large-message bandwidth in
   `nccl-tests` — what class of problem does that point toward, and what's the next
   diagnostic step?
3. Why does `nccl-tests` belong at multiple distinct points in a fleet's lifecycle
   (provisioning, cluster validation, ongoing health checks, post-incident) rather than
   as a single one-time verification?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "`nccl-tests` runs the actual collective operations — 
all-reduce, all-gather, and so on — across a range of message sizes and reports achieved
bandwidth and latency against the hardware's theoretical ceiling. It exists because
network and interconnect degradation in a GPU cluster usually doesn't throw an error —
the job still runs, just slower — so this is how you catch that before an expensive
training or serving job is the first thing to notice."

**The follow-up-proof version**: be ready to explain why the tool sweeps message sizes
rather than running one fixed size — small messages expose latency/software-path
problems, large messages expose bandwidth/link-speed problems — and why the reported
"bus bandwidth" metric isn't directly comparable to a raw interconnect spec number.

**Vocabulary builder**: *bus bandwidth* (NCCL's algorithm-aware bandwidth metric, distinct
from raw link speed), *baseline* (a known-good reference range for a given instance type,
maintained over time, that a given run's result is compared against), *regression
detection* (catching degradation between two points in time via repeated measurement,
distinct from one-time pass/fail validation).
