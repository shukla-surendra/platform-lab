# GPU Fleet Lifecycle Management: The Nine Stages, Named and Grounded

Part of [Phase 6 — Production Operations](../README.md#phase-6-production-operations).
Opens Phase 6. This chapter is the organizing structure for the rest of the phase — every
later Phase 6 chapter (reliability, observability, capacity planning, storage, security)
slots into one or more of the nine stages named here, and this chapter is where the
components already built in Phases 2-4 (GPU Operator, DCGM, `nccl-tests`) get assembled
into the recurring operational loop a real fleet runs continuously, not just once.

## Clarify

"Fleet lifecycle management" sounds abstract until it's stated as nine concrete,
nameable stages a physical GPU node moves through, repeatedly, over its operational life
— not a metaphor, an actual sequence with real tooling at each step, most of which this
track has already built in earlier chapters without naming the stage it belonged to. This
chapter is that naming.

## Core Concepts

### The nine stages

```
1. PROVISION   — a new physical/virtual GPU node is brought up (bare
                  metal, or a cloud instance launch)
2. REGISTER    — the node joins the cluster's inventory/scheduling pool
                  (Kubernetes node registration, or a Slurm partition
                  addition, per 11_slurm_vs_kubernetes.md)
3. CONFIGURE   — driver, CUDA toolkit, container runtime, NCCL/EFA
                  setup — the GPU Operator's job
                  (09_gpu_operator_and_device_plugin.md)
4. VALIDATE    — nccl-tests intra-node AND cross-node
                  (08_nccl_testing.md) — confirm the node's actual
                  hardware performs to spec BEFORE trusting it with
                  real workloads, not after
5. SCHEDULE    — the node becomes eligible for workload placement —
                  device plugin advertises capacity, gang-scheduling-
                  aware schedulers (Kueue/Volcano, per
                  10_gpu_scheduling_mig_sharing.md) place jobs onto it
6. MONITOR     — DCGM + Prometheus continuously track health/
                  utilization (04_cuda_ecosystem.md's monitoring stack,
                  detailed further in 17_observability_for_gpu_fleets.md)
7. OPTIMIZE    — utilization/cost data feeds capacity-planning decisions
                  (18_capacity_planning_and_finops.md) — right-sizing,
                  MIG/time-slicing adjustments, workload placement tuning
8. REPAIR      — a detected failure (XID error, degraded NVLink,
                  hardware fault — 16_reliability_and_failure_management.md)
                  triggers draining and remediation
9. RETIRE      — end of hardware life, or a generational replacement —
                  node is decommissioned, removed from inventory
```

**Why this is a loop, not a line**: a node that completes REPAIR doesn't jump to RETIRE —
it re-enters at VALIDATE (confirm the fix actually worked, the same discipline named in
[`08_nccl_testing.md`'s post-incident verification](../phase3_gpu_networking/08_nccl_testing.md#where-this-fits-in-a-fleets-actual-lifecycle))
before returning to SCHEDULE. A node under active use continuously cycles through
MONITOR → OPTIMIZE without ever leaving SCHEDULE. The nine stages are states a node
moves between repeatedly over months or years, not a one-time onboarding checklist.

### Where each earlier chapter's tooling actually lives in this loop

This is the direct payoff of the roadmap's cross-referencing discipline — nothing here
is new tooling, it's naming which lifecycle stage each already-covered tool operates at:

| Stage | Tool from this track |
|---|---|
| CONFIGURE | GPU Operator (driver, toolkit, device plugin, DCGM, GFD) — [`09`](../phase4_kubernetes_gpu/09_gpu_operator_and_device_plugin.md) |
| VALIDATE | `nccl-tests` (intra-node and cross-node) — [`08`](../phase3_gpu_networking/08_nccl_testing.md) |
| SCHEDULE | Device plugin + Kueue/Volcano gang scheduling — [`10`](../phase4_kubernetes_gpu/10_gpu_scheduling_mig_sharing.md) |
| MONITOR | DCGM + dcgm-exporter + Prometheus — [`04`](../phase2_gpu_fundamentals/04_cuda_ecosystem.md), deepened in [`17`](17_observability_for_gpu_fleets.md) |
| OPTIMIZE | Utilization data → MIG/time-slicing tuning, capacity decisions — [`18`](18_capacity_planning_and_finops.md) |
| REPAIR | XID-error-triggered draining and remediation — [`16`](16_reliability_and_failure_management.md) |

### Why VALIDATE has to happen at both PROVISION-time and after REPAIR

A subtle but consequential detail this stage list makes explicit: skipping VALIDATE after
REPAIR (trusting that a hardware swap or driver reinstall "should have fixed it") is
exactly how a degraded node re-enters the scheduling pool silently under-performing — the
same "everything works, just slower, no error" failure class named throughout Phases 2-3
(NVLink topology issues, RDMA fallback to TCP), now framed as a lifecycle-process gap
rather than a one-time technical mistake. **The fix is procedural, not technical**: REPAIR
must always route back through VALIDATE before SCHEDULE, as a hard gate, not an optional
best practice.

## Deep-Dive: what "fleet-scale" actually changes about each stage

Every stage above is trivial for one node and genuinely hard at fleet scale — naming
*why* fleet scale changes each stage is the actual signal in a system-design answer about
this topic:

- **PROVISION at scale** — needs to be automated (infrastructure-as-code, not manual
  per-node setup) simply because manual provisioning doesn't scale past a handful of
  nodes without becoming the bottleneck itself.
- **CONFIGURE at scale** — this is precisely why the GPU Operator's Kubernetes-native,
  DaemonSet-based approach
  ([`09_gpu_operator_and_device_plugin.md`](../phase4_kubernetes_gpu/09_gpu_operator_and_device_plugin.md#the-nvidia-gpu-operator-bundling-the-whole-stack-as-kubernetes-managed-components))
  matters — manual per-node driver installation doesn't scale, and drift between nodes
  (different driver versions on different machines) is a fleet-scale-specific failure
  mode a single-node setup never surfaces.
- **VALIDATE at scale** — needs a maintained baseline (per
  [`08_nccl_testing.md`'s trade-offs](../phase3_gpu_networking/08_nccl_testing.md#trade-offs))
  because "does this look right" stops being answerable by eyeballing a single result
  once there are hundreds of nodes to compare against.
- **MONITOR at scale** — raw per-node dashboards don't scale to human attention; this is
  why fleet-scale monitoring needs aggregation, alerting thresholds, and anomaly
  detection rather than a human watching N individual `nvidia-smi` outputs — the subject
  of [`17_observability_for_gpu_fleets.md`](17_observability_for_gpu_fleets.md).
- **REPAIR at scale** — needs automated detection-to-draining pipelines (rather than a
  human noticing a problem and manually intervening) simply because the volume of
  hardware events (a fleet of thousands of GPUs has meaningfully frequent individual
  hardware faults, even if each GPU is individually reliable) makes manual response
  unsustainable — the subject of
  [`16_reliability_and_failure_management.md`](16_reliability_and_failure_management.md).

## Trade-offs

| Choice | Upside | Cost |
|---|---|---|
| Fully automated lifecycle pipeline (IaC provisioning, automated CONFIGURE/VALIDATE, automated REPAIR triggers) | Scales to fleet size, consistent, fast recovery | Meaningful upfront engineering investment to build the automation itself |
| Manual/semi-manual lifecycle management | Lower upfront tooling investment | Doesn't scale past a small fleet; human-driven REPAIR is slower and more error-prone at volume |
| Skipping VALIDATE after REPAIR to save time | Faster time-to-return-to-service | Risks silently reintroducing a degraded node into the scheduling pool — the exact failure this chapter's deep-dive warns against |

## Failure Modes to Raise Proactively

- **Treating fleet lifecycle as a one-time onboarding process rather than a continuous
  loop** — a node that's provisioned once and never re-validated after a repair, or never
  re-monitored for drift, is exactly how the "silent degradation" failure mode recurs
  across this track's chapters, at the process level rather than the technical level.
- **Skipping VALIDATE specifically after REPAIR** — named explicitly above as the single
  most consequential procedural gap; a hardware fix that "should have worked" isn't
  confirmed until it's actually re-tested.
- **Building MONITOR without a path into OPTIMIZE and REPAIR** — collecting metrics that
  no automated (or human) process actually acts on is observability theater; the loop only
  functions if MONITOR's output actually drives the next stage.

## Make It Yours

- Take any GPU-related tool or process you've already worked with in this workspace
  (`k8n_explorer/`, `mlops_aiops/`) and place it explicitly on this nine-stage map —
  practice naming which lifecycle stage it operates at, the same exercise this chapter's
  cross-reference table performs for this track's own earlier chapters.

## Practice Questions

1. Why must REPAIR route back through VALIDATE before a node returns to SCHEDULE, rather
   than returning directly to SCHEDULE once the physical fix is applied?
2. Name three lifecycle stages that are trivial for a single GPU machine but become
   genuinely hard specifically at fleet scale — and explain what specifically changes at
   scale for each.
3. A fleet has excellent MONITOR tooling (comprehensive DCGM/Prometheus dashboards) but no
   automated REPAIR triggers — what's the practical consequence of that gap?

## Articulate It: Interview Framing & Vocabulary

**The 30-second version**: "A GPU fleet's lifecycle has nine recurring stages — provision,
register, configure, validate, schedule, monitor, optimize, repair, retire — and it's a
loop, not a line: a repaired node re-enters at validate before returning to schedule,
not directly. Most of the actual tooling — the GPU Operator for configure, nccl-tests for
validate, DCGM for monitor — already exists at the single-node level; what makes fleet
scale hard is that each stage needs to be automated and consistent across potentially
thousands of nodes, not manually verified one at a time."

**The follow-up-proof version**: be ready to name which specific tool from earlier in this
track operates at each stage, rather than describing the lifecycle abstractly — this is
the difference between reciting a framework and demonstrating it's grounded in real,
checkable mechanisms.

**Vocabulary builder**: *drift* (nodes in a fleet silently diverging in configuration over
time — the failure IaC-based CONFIGURE and consistent VALIDATE both guard against),
*draining* (removing a node from the scheduling pool without killing currently-running
work abruptly, the first step of REPAIR), *baseline* (the known-good reference a VALIDATE
result is compared against, reused from `08_nccl_testing.md`).
