# Tricky MLOps Scenarios

Fourteen scenario-debugging problems — each a realistic, ambiguous production situation as
it would actually be reported to you (a Slack message, a dashboard anomaly, an angry
stakeholder), not a clean textbook question. This is where the trade-off vocabulary and
failure modes from the eleven tutorials in this section get exercised under the kind of
ambiguity a real incident actually has.

## Why This Format

Design-round questions test whether you can *build* a system. These test whether you can
*reason about one that's already broken* — arguably the harder and more senior skill, and
the one staff+ interview loops increasingly probe directly. Each scenario is structured the
same way:

1. **The Situation** — what you'd actually be told, often vague or slightly misleading
2. **First Questions to Ask** — what you'd clarify before touching anything, since acting
   on an assumption is the most common way candidates go down the wrong path
3. **Likely Root Causes** — ranked hypotheses, not just one "correct" answer
4. **Diagnostic Path** — the concrete steps you'd take to confirm or rule out each
   hypothesis
5. **The Fix** — immediate mitigation vs. the actual long-term fix (these are often
   different, and conflating them is a real interview tell)
6. **Prevention** — the systemic lesson, linked back to the tutorial covering the relevant
   design pattern

## How to Practice These

- **Read only "The Situation" first.** Stop. Say your clarifying questions out loud before
  reading further — this is the step most people skip, and it's the one that separates a
  senior answer from a junior one.
- **Commit to a ranked list of hypotheses before reading "Likely Root Causes."** Compare
  your reasoning, not just your final answer.
- **A given scenario often has more than one contributing cause** — real incidents usually
  do. Resist the urge to stop investigating after finding the first plausible cause.

## The Scenarios

| # | Scenario | Primary Topic |
|---|---|---|
| 1 | [Regional Feature Staleness](12_tricky_scenarios_01_regional_feature_staleness.md) | Feature Store |
| 2 | [Canary Passed, P1 Two Days Later](12_tricky_scenarios_02_canary_passed_p1_later.md) | Model Serving |
| 3 | [Silent Drift, No Alert](12_tricky_scenarios_03_silent_drift_no_alert.md) | Observability |
| 4 | [Overnight GPU Cost Spike](12_tricky_scenarios_04_gpu_cost_spike.md) | LLM Serving / Cost |
| 5 | [Retrieval Looks Right, Answers Are Wrong](12_tricky_scenarios_05_rag_retrieval_correct_answers_wrong.md) | RAG |
| 6 | [Silently Duplicated Training Data](12_tricky_scenarios_06_duplicate_training_data.md) | Ingestion |
| 7 | [Multi-GPU Training Plateau](12_tricky_scenarios_07_distributed_training_plateau.md) | Distributed Training |
| 8 | [Stale Checkpoint After Preemption](12_tricky_scenarios_08_stale_checkpoint_resume.md) | Distributed Training |
| 9 | [GitOps Rollout, Wrong Predictions](12_tricky_scenarios_09_gitops_rollout_wrong_predictions.md) | GitOps/CI-CD |
| 10 | [Reconstructing Model Lineage for an Audit](12_tricky_scenarios_10_audit_lineage_reconstruction.md) | Governance |
| 11 | [Serving Cost Doubled After a "Routine" Upgrade](12_tricky_scenarios_11_serving_cost_doubled.md) | Cost |
| 12 | [DR Failover Took 8x Longer Than Planned](12_tricky_scenarios_12_dr_failover_slow.md) | Multi-Region/DR |
| 13 | [Eval Passed, Guardrail Bypassed in Production](12_tricky_scenarios_13_eval_passed_guardrail_bypassed.md) | LLMOps |
| 14 | [GPU Sitting Idle 75% of the Time in a Sequential Pipeline](12_tricky_scenarios_14_gpu_underutilized_sequential_pipeline.md) | GPU / Pipeline Architecture |

---

**Previous:** [11. LLMOps: Prompting, Fine-Tuning, Evals & Guardrails](11_llmops.md)  |  **Next:** [1. Regional Feature Staleness](12_tricky_scenarios_01_regional_feature_staleness.md)
