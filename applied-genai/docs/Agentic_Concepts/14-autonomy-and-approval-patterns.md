# Appendix: Autonomy Levels and Approval Patterns

Every agent with a mutating tool eventually raises the same question: does it get to act on its
own, or does a human have to approve first? There's no single right answer — production systems
sit at different points on a spectrum, and where a *specific action* sits depends on factors that
have nothing to do with how good the model is.

## The spectrum of autonomy

Analogous to self-driving car levels — most production agents sit somewhere in the middle, not at
either extreme:

| Level | Behavior | Example |
|---|---|---|
| **L0 — Advisory only** | Agent diagnoses and recommends; a human executes everything | An agent that posts "here's likely root cause + suggested fix" to Slack and does nothing else |
| **L1 — Propose, human approves** | Agent prepares the exact action; a human approves or denies it | `../devops_sre_agent` and `../databricks_autopilot_agent` — see [where this repo actually stands](#where-this-repos-projects-stand) below |
| **L2 — Auto-act within bounded scope** | Agent acts on its own, but only inside pre-approved limits (specific resources, rate limits, resources tagged "safe") | Kubernetes' Cluster Autoscaler — adds/removes nodes autonomously, but only within a min/max bound someone configured |
| **L3 — Fully autonomous, audited after the fact** | Agent acts immediately; humans review logs/alerts, not individual actions | A fraud-detection system auto-blocking transactions above a risk score |

## What actually determines the level

- **Reversibility.** Restarting a crashed pod costs nothing to undo; deleting a database table
  does. Kubernetes' liveness-probe restarts are L3 *precisely because* they're cheap and
  reversible — this is also why `handle_transient`'s auto-retry in `../databricks_autopilot_agent`
  is a reasonable candidate for full autonomy even though `handle_oom`'s cluster resize (costs
  money, affects capacity) is not.
- **Blast radius.** Scaling one canary instance vs. resizing every cluster in prod. Same action
  type, very different autonomy comfort level depending on scope.
- **Confidence.** `../databricks_autopilot_agent`'s `diagnose_root_cause` node emits a
  `confidence` field precisely so this is actionable: a production version would auto-act above a
  threshold and force human review below it, rather than treating every model output as equally
  trustworthy — see that project's [Reliability notes](../../databricks_autopilot_agent/README.md#reliability-notes-read-this)
  for a concrete case where confidence (0.75 vs 0.95+) tracked correctness.
- **Cost of delay vs. cost of a mistake.** A payment-fraud agent has milliseconds to decide (can't
  wait for a human), so it leans autonomous with tight guardrails (hard position/dollar limits)
  instead of approval gates. An incident-response agent usually has minutes, so a Slack approval
  step costs little relative to the risk of a wrong automated action.

## Real-world examples across domains

- **Stripe Radar (fraud).** Three-tier confidence gating: auto-allow below a risk score, auto-block
  above another, hold the middle band for human review. Confidence-threshold routing, not a single
  yes/no.
- **Dependabot / Renovate (CI/CD).** Auto-merges patch/minor dependency bumps if tests pass; opens
  a PR for major version bumps and waits for a human to click merge. Reversibility (`git revert`)
  plus blast radius (a major bump can break things) drives the split.
- **AWS Systems Manager Automation.** Runbooks can include an explicit approval step — the
  automation pauses, pings an SNS topic/Slack, and only proceeds once someone approves. L1 as a
  first-class platform feature, not something bolted on.
- **Algorithmic trading.** Heavily L2: the model decides trades autonomously in real time, but
  hard-coded circuit breakers and position limits — not the model's judgment — are the actual
  safety floor. The lesson: the *policy layer* enforcing limits should be separate code the model
  can't talk its way around, not another prompt instruction (see
  [Chapter 13's guardrails section](13-trusted-tools-landscape.md#guardrails-and-safety)).
- **Content moderation.** Auto-removing content matching a known-bad hash (near-zero false-positive
  tolerance) is L3; borderline cases queue for a human moderator — again, confidence driving the
  split.
- **Kubernetes self-healing.** Restarting a crashed container is, and always has been, fully
  autonomous — worth noting because it's a reminder that autonomy isn't inherently scarier just
  because an LLM is now in the loop; the reversibility/blast-radius calculus is the same one ops
  teams have always used for scripted automation.

## Mechanisms for implementing this

- **Dry-run / plan-then-apply.** The blunt but effective version: mutating tools check a flag and
  report what they *would* do instead of doing it. This is what
  [`../devops_sre_agent`](../../devops_sre_agent/README.md#safety-model-read-by-default-mutate-only-with---apply)
  and [`../databricks_autopilot_agent`](../../databricks_autopilot_agent/README.md#safety-model-read-by-default-mutate-only-with---apply)
  both do, modeled on Terraform's `plan`/`apply` split.
- **`interrupt()` for a real approval pause.** [Chapter 5](05-memory-and-persistence.md#human-in-the-loop-with-interrupt)
  covers the LangGraph mechanism: a node calls `interrupt(...)`, execution halts and surfaces the
  proposed action to whatever's driving the graph (a UI, a Slack bot), and `Command(resume=...)`
  continues exactly where it left off once a human responds. This is the difference between L0
  ("the agent's dry-run text happens to look like a question") and true L1 (the graph structurally
  cannot proceed past that node without an answer).
  - **Ideal, higher-effort next step** if you wanted `databricks_autopilot_agent`'s `handle_oom`
    or `handle_transient` to actually pause and wait for a real approval rather than just checking
    `config.APPLY_CHANGES` once at process start.
- **Confidence-threshold routing.** Route to L1 (approval-gated) below a confidence threshold and
  L2 (auto-act) above it, rather than treating every diagnosis identically — the natural next step
  for `diagnose_root_cause`'s `confidence` field.
- **Per-action risk tiers.** Different actions in the same system sit at different levels — see
  the gap called out below.
- **Circuit breakers / rate limits.** A hard cap ("no more than N mutating actions per hour")
  independent of what the model decides, so a broken diagnosis loop can't cause unbounded damage
  even at L2/L3.

## Where this repo's projects stand

Both `../devops_sre_agent` and `../databricks_autopilot_agent` currently implement the simplest
possible version of L1: one global flag (`config.APPLY_CHANGES`, set once from `--apply` at
process start) gates *every* mutating tool identically. That's honest and safe for a demo, but not
how a real production system would do it — two concrete gaps, in order of how much they'd matter
in practice:

1. **No per-action tiers.** Restarting a single EC2 instance and resizing a fleet-wide ECS service
   are gated by the same flag today, even though they have very different blast radii. A more
   realistic version would let some actions (e.g. `handle_transient`'s bounded auto-retry) run at
   L2 while others (`handle_oom`'s cluster resize) stay at L1 regardless of the global flag.
2. **No real approval mechanism.** `--apply` is decided once, before any event is even seen — it
   can't ask a question. Swapping the dry-run check inside `handle_oom` for an `interrupt()` call
   (per [Chapter 5](05-memory-and-persistence.md#human-in-the-loop-with-interrupt)) would let the
   daemon actually pause on a specific proposed action and resume once approved, instead of every
   run being decided in advance by one flag.

Neither gap is a defect in the demos — a global dry-run flag is the right amount of complexity for
teaching the pattern — but it's the reason to reach for `interrupt()` and confidence-threshold
routing before running anything resembling this against real infrastructure.

Next: nothing numbered comes after this — it's the second appendix, alongside
[Chapter 13](13-trusted-tools-landscape.md). Both exist to be revisited whenever a new project's
architecture needs deciding, not read once and forgotten.
