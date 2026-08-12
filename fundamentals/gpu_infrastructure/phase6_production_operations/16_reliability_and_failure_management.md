# Reliability & Failure Management: XID Errors and the REPAIR Stage, in Detail

Part of [Phase 6 — Production Operations](../README.md#phase-6-production-operations).
Builds on [`15_gpu_fleet_lifecycle.md`](15_gpu_fleet_lifecycle.md)'s REPAIR stage — this
chapter is that stage's actual mechanism: how a hardware or driver-level failure is
detected in the first place, what the detection signal actually looks like, and how
detection turns into automated action rather than a human noticing something is wrong.

## Clarify

Every failure mode named across Phases 2-5 of this track shares a specific, deliberate
shape: **silent degradation, not a crash** — a suboptimal NVLink path, an RDMA fallback,
a misrouted MoE batch. This chapter is about the *other* failure category this track
hasn't yet covered: **hardware genuinely breaking** — a failing GPU, a corrupted memory
cell, a driver crash — which, unlike silent degradation, usually *does* announce itself,
through a specific, well-defined signal: the **XID error**. The skill this chapter builds
is knowing that signal exists, what it looks like, and what a mature fleet does with it
automatically, rather than discovering XID errors for the first time during a real
incident.

## Core Concepts

### XID errors — NVIDIA's structured hardware/driver error-reporting mechanism

An **XID error** is a specific, numbered error code the NVIDIA driver logs to the kernel
log (`dmesg`, or the Windows Event Log) when it detects a GPU-level fault — anything from
a recoverable software-level hiccup to a genuine hardware failure requiring physical
replacement. Unlike the silent-degradation failures this track has repeatedly warned
about, an XID error is an explicit, structured signal — the driver is telling the
operator something specific went wrong, with a code that maps to a documented cause.

```
dmesg output, real XID error example:
  NVRM: Xid (PCI:0000:07:00): 79, pid=12345, GPU has fallen off the bus

# XID 79 specifically means the GPU stopped responding to the PCIe bus
# entirely — a serious hardware-level fault, not a software-recoverable
# one. Other XID codes cover a wide range of severity:
#   XID 13 — graphics engine exception (often software-triggered,
#            frequently recoverable without hardware replacement)
#   XID 48 — double-bit ECC error (memory corruption detected — HBM
#            hardware fault, per 03_gpu_architecture.md's HBM chapter)
#   XID 63/64 — row-remapping events (a specific HBM self-healing
#               mechanism reaching its limit — see below)
#   XID 79 — GPU fallen off the bus (severe — usually requires physical
#            intervention, node reboot at minimum)
```

**Why this matters as a distinct diagnostic category from everything earlier in this
track**: the failure modes in Phases 2-3 (degraded NVLink, RDMA fallback) require
*comparing* a measurement against a baseline (`nccl-tests`) to notice anything is wrong at
all — there's no error message. XID errors are the opposite case: the driver already knows
something is wrong and says so explicitly. A mature fleet's monitoring has to watch for
*both* categories, because they require genuinely different detection strategies —
proactive benchmarking for the silent class, log/event watching for the XID class.

### Row remapping — HBM's own self-healing mechanism, and why it matters operationally

A detail worth knowing specifically because it changes how an XID error should be
interpreted: modern NVIDIA GPUs (Ampere/Hopper-class) support **row remapping** — when
HBM detects a failing memory row (from
[`03_gpu_architecture.md`](../phase2_gpu_fundamentals/03_gpu_architecture.md#hbm-why-gpu-memory-bandwidth-not-just-capacity-is-the-real-budget)'s
HBM chapter), the GPU can automatically remap that row to spare capacity, transparently,
without requiring hardware replacement — a real, hardware-level self-healing mechanism.
XID 63/64 specifically signal this happened. **The operational nuance**: an occasional
row-remapping event is expected, healthy behavior over a GPU's lifetime, not itself an
incident — but a GPU accumulating row-remapping events at a high *rate* is exhausting its
spare capacity and is a genuine leading indicator that physical replacement will be
needed soon. This is the concrete difference between "log it and move on" and "flag this
node for planned replacement" — both triggered by the same XID code family, distinguished
by frequency/rate, not presence alone.

### From detection to automated action — the actual REPAIR pipeline

```
DCGM (already covered in 04_cuda_ecosystem.md) doesn't just expose
utilization metrics — it actively monitors for XID errors and other
health signals as part of its diagnostics functionality, and can be
configured to:

  1. DETECT — XID error appears in dmesg / DCGM health check fails
  2. CLASSIFY — is this severity "drain and investigate" (e.g. a
     single recoverable XID) or "immediate removal" (e.g. XID 79,
     GPU fallen off the bus)?
  3. DRAIN — the node is marked unschedulable (Kubernetes: cordon +
     drain: existing workloads are allowed to complete or checkpoint
     and are rescheduled elsewhere; NEW workloads are not placed here)
     — this is the direct mechanism behind the REPAIR stage's first
     step in 15_gpu_fleet_lifecycle.md
  4. REMEDIATE — automated remediation (driver reset, node reboot) for
     recoverable classes; a ticket/alert for a human for hardware-
     replacement-required classes
  5. RE-VALIDATE — nccl-tests + DCGM health check, per
     15_gpu_fleet_lifecycle.md's VALIDATE-after-REPAIR discipline,
     BEFORE the node returns to the scheduling pool
```

**The specific automation maturity spectrum worth naming in an interview answer**: a
fleet can sit anywhere from "a human watches dmesg logs" (doesn't scale, per
`15_gpu_fleet_lifecycle.md`'s deep-dive) to "DCGM health checks automatically cordon and
drain a node the moment a severe XID appears, paging a human only for the
hardware-replacement-required cases" — the second is what "automated remediation" in this
track's roadmap concretely means, not a vague aspiration.

## Deep-Dive: why draining, not immediately killing, matters for the workloads this track has already covered

This connects directly back to a constraint established early in this track: recall
[`aws-production-architecture.md`'s autoscaling section](../../system_design_foundation/01_ml_system_design/13_large_model_multi_gpu_inference/aws-production-architecture.md#autoscaling-by-node-group-not-by-pod)
— a tensor-parallel group is useless with a partial set of GPUs. If a node hosting one
GPU of an 8-GPU TP group is abruptly killed rather than drained, the *entire* TP group's
job fails immediately, not just that one GPU's share of work. Draining — letting current
work complete or checkpoint before removing capacity — is what prevents a single
hardware fault from cascading into a full job failure for every other GPU in that job's
group, whether that job is a serving deployment or (per
[`21_fsdp_deepspeed_zero.md`](../phase7_advanced_training_infra/21_fsdp_deepspeed_zero.md))
a large training run relying on periodic checkpointing to survive exactly this kind of
event.

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Fully automated detection-to-drain pipeline | Fast response, scales to fleet size, minimizes blast radius of a hardware fault | Requires careful classification logic — an overly aggressive auto-drain policy can pull healthy nodes out of service on false positives |
| Manual (human-reviewed) response to every XID event | Lower risk of false-positive drains | Doesn't scale; response time lags real-time at fleet size, per `15_gpu_fleet_lifecycle.md`'s scale argument |
| Ignoring low-severity/recoverable XID events entirely | Less operational noise | Misses the row-remapping-rate signal that predicts upcoming hardware failure — a real, avoidable surprise instead of a planned replacement |

## Failure Modes to Raise Proactively

- **Treating all XID errors as equally severe** — as shown above, XID 13 and XID 79 imply
  very different responses; a blanket policy (always page a human, or always ignore)
  misses the actual signal each code carries.
- **Killing rather than draining a node hosting part of a distributed job** — directly
  causes the cascading-failure pattern named in the deep-dive, turning a single GPU's
  hardware fault into a full job failure.
- **Not tracking row-remapping event rate over time** — a single event is normal;
  treating every event identically (either always alarming or always ignoring) misses the
  actual leading indicator this mechanism provides for planned hardware replacement.

## Make It Yours

- If you have `dmesg` access to any machine with an NVIDIA GPU, search for "Xid" in the
  log — even an empty result is worth confirming, since it establishes what a
  healthy baseline actually looks like before ever needing to recognize an abnormal one.
- Next time DCGM's health-check capabilities come up (in `mlops_aiops/` or elsewhere in
  this workspace), check specifically whether XID-error monitoring is configured, not
  just utilization/throughput dashboards — the distinction this chapter draws between
  the two failure categories.

## Practice Questions

1. Why do XID errors require a fundamentally different detection strategy than the
   NVLink-degradation or RDMA-fallback failures named in Phases 2-3 of this track?
2. A GPU logs an XID 63 (row-remapping event) once in six months of operation — is this
   itself an incident? What would make it one?
3. Why does draining rather than immediately killing a node matter specifically for a
   tensor-parallel serving deployment, in terms of the blast radius of a single GPU's
   hardware fault?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "XID errors are NVIDIA's structured, numbered error codes
logged when the driver detects a GPU-level fault — unlike the silent-degradation failures
elsewhere in this track, they're an explicit signal, not something you have to benchmark
to notice. A mature fleet's REPAIR pipeline detects these (often via DCGM), classifies
severity, drains the affected node so in-flight distributed work isn't killed abruptly,
remediates or escalates to a human, and re-validates with nccl-tests before the node
returns to the scheduling pool."

**The follow-up-proof version**: be ready to name a specific XID code and its meaning
(GPU fallen off the bus, double-bit ECC error, row remapping) rather than describing "XID
errors" generically — and be ready to explain why row-remapping *rate*, not presence
alone, is the actual leading indicator worth alerting on.

**Vocabulary builder**: *XID error* (NVIDIA's structured GPU fault error code), *row
remapping* (HBM's hardware self-healing mechanism for failing memory cells), *cordon and
drain* (the Kubernetes-native mechanism for removing a node from scheduling without
abruptly killing running work), *blast radius* (how much of a system a single failure
actually affects — the concept draining is designed to minimize).
