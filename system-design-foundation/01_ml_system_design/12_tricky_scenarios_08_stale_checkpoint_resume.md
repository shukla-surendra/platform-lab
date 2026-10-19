# 8. Stale Checkpoint After Preemption

**Primary topic:** [Distributed Training & Ray/Ray Serve](07_distributed_training_serving.md)

## The Situation

A multi-day distributed training job runs on spot/preemptible instances. After a
preemption event, the job automatically resumed — but the loss curve shows a sudden
regression at the resume point, as if training jumped backward. The job "recovered
successfully" according to the orchestration logs.

## First Questions to Ask

- Is checkpointing synchronized across all workers (a barrier before writing), or does
  each worker checkpoint independently on its own schedule?
- What exactly does "resumed successfully" mean in the logs — that a checkpoint was found
  and loaded, or that training continued without error? (These are different claims.)
- Were all workers preempted simultaneously, or was it a partial preemption (some workers
  survived, others restarted)?
- Does the checkpoint include optimizer state (momentum, etc.), or weights only?

## Likely Root Causes (ranked)

1. **An inconsistent (non-barriered) checkpoint** — if workers checkpoint independently
   without a synchronization barrier, a checkpoint taken mid-flight can capture different
   workers at different training steps. Resuming from this mismatched state effectively
   restarts some workers' progress while others are ahead — the training process as a
   whole moves *backward* in aggregate, exactly matching the observed loss-curve jump.
   This is the failure mode the
   [distributed training tutorial](07_distributed_training_serving.md#checkpointing-at-scale)
   calls out directly as the reason checkpoint barriers exist.
2. **Optimizer state not checkpointed (weights-only checkpoint).** If only model weights
   were saved and optimizer state (momentum, Adam's per-parameter statistics) was not,
   resuming effectively restarts the optimizer from scratch even though weights are
   preserved — this produces a genuine, if smaller, training disruption at every resume,
   distinguishable from #1 by *not* depending on partial-preemption timing.
3. **A partial preemption resumed surviving workers against a checkpoint meant for a full
   restart**, effectively mixing "fresh from checkpoint" state with "continued in-memory"
   state across different workers inconsistently.

## Diagnostic Path

1. **Check whether the checkpointing implementation includes an explicit synchronization
   barrier** across all workers before writing — read the actual checkpoint code/config,
   don't assume based on "it usually works."
2. **Inspect the specific checkpoint that was loaded on resume** — compare the training
   step number recorded by each worker's shard of that checkpoint; a mismatch directly
   confirms root cause #1.
3. **Confirm what the checkpoint actually contains** — weights only, or weights +
   optimizer state + step counter. Missing optimizer state is a straightforward file/
   config inspection.
4. **Check whether the preemption was full or partial** via the orchestration/cluster
   event logs for that incident specifically — correlate which workers were actually
   restarted versus continued running.

## The Fix

- **Immediate mitigation**: restart the training job from the last *confirmed-consistent*
  checkpoint (verify step-number consistency across all workers' shards before resuming),
  accepting the lost progress since that point rather than trusting the corrupted resume.
- **Long-term fix**: implement (or fix) a synchronization barrier that pauses all workers
  at the same step before any checkpoint write begins, ensure the checkpoint format
  includes optimizer state and an explicit step counter validated on load, and add an
  automated consistency check on checkpoint load (reject and fall back to an older
  checkpoint if worker-shard step numbers don't match) rather than trusting any found
  checkpoint blindly.

## Prevention

The systemic lesson: **"a checkpoint exists and was loaded" is not the same claim as "the
checkpoint is consistent."** Training on interruptible capacity makes checkpoint
correctness a first-class engineering requirement, not an edge case — see the
spot-instance checkpointing discussion in the
[distributed training tutorial](07_distributed_training_serving.md#checkpointing-at-scale).
An automated load-time consistency check is cheap insurance against exactly this incident
recurring silently.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Claim-precision framing (the default for this scenario):** "'A checkpoint was loaded
  and training resumed' is a different claim from 'the checkpoint was consistent.' I'd
  push on that distinction immediately — the orchestration logs proved the first, not the
  second, and the loss curve is telling you the second one was false."
- **Mechanism-first (good for explaining the backward jump):** "If workers checkpoint
  independently without a barrier, you can capture different workers at different steps —
  resuming from that mismatched state effectively restarts some workers' progress while
  others are ahead, which is exactly why the aggregate loss curve moves backward."
- **Insurance framing (good for the prevention discussion):** "The actual fix isn't just a
  barrier — it's an automated consistency check at load time that rejects a checkpoint with
  mismatched worker-shard step numbers, rather than trusting any found checkpoint blindly."

### Vocabulary Builder

- **barrier synchronization** (n. phrase) — forcing every worker to reach the same point
  before any of them proceeds; the mechanism that makes a checkpoint internally consistent.
- **momentum state** (n. phrase) — the per-parameter statistics an optimizer like Adam
  carries beyond raw weights; losing it on resume causes a smaller, silent disruption
  distinct from a full inconsistent-checkpoint jump.
- **"…is not the same claim as…"** — a reusable template for separating a status message
  from the stronger guarantee it's often mistaken for.

---

**Previous:** [7. Multi-GPU Training Plateau](12_tricky_scenarios_07_distributed_training_plateau.md)  |  **Next:** [9. GitOps Rollout, Wrong Predictions](12_tricky_scenarios_09_gitops_rollout_wrong_predictions.md)
