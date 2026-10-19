# 10. Reconstructing Model Lineage for an Audit

**Primary topic:** [Cost, Security & Multi-Region Governance](10_cost_security_multiregion.md)

## The Situation

A compliance auditor requests: "show me exactly which model version produced the
decision for customer X's application on a specific date three months ago, what data it
was trained on, and who approved it for production." Your team can identify the model
version from serving logs, but reconstructing the rest turns into a multi-day scramble
across several disconnected systems.

## First Questions to Ask

(These are as much about the state of your systems as the specific incident.)

- Are serving logs retained long enough to cover the requested date, and do they log the
  exact model version (not just "the current model") per prediction?
- Does the model registry retain full lineage — which training run, which data version,
  which feature definitions — for a model version from three months ago, or does that
  metadata get pruned/overwritten over time?
- Is there a single system of record for "who approved this promotion," or is that
  information scattered across Slack messages, PR approvals, and tribal knowledge?
- Was the training data itself versioned in a way that's still queryable three months
  later, or could the underlying data have since changed/been deleted?

## Likely Root Causes (ranked — really, "likely gaps")

This scenario is less about a single root cause and more about **which lineage link is
actually broken** — walk through each link in the chain explicitly:

1. **Serving logs don't capture model version per prediction**, only "which endpoint" —
   if multiple model versions could have served that endpoint over time (e.g. mid-canary),
   reconstructing the *exact* version for a specific historical prediction may be
   impossible after the fact if this wasn't logged at request time.
2. **The model registry's retention policy prunes old lineage metadata**, treating it as
   operational logging rather than a compliance record — three-month-old lineage may
   simply no longer exist if retention wasn't deliberately set with audit requirements in
   mind.
3. **"Who approved promotion" was never a structured, queryable record** — if promotion
   approval happened via ad-hoc Slack approval or verbal sign-off rather than a
   structured gate (a required PR approval, a recorded sign-off step in the promotion
   pipeline), there's no system of record to query, only human memory.
4. **Training data itself is mutable/non-versioned** — if the underlying data warehouse
   table was simply updated in place rather than versioned (Delta Lake/Unity Catalog
   time-travel, or an equivalent), "what data trained this model" may not be
   reconstructable even if the *reference* to a data version exists, because that version
   no longer corresponds to any retrievable actual data.

## Diagnostic Path (in this scenario, this doubles as the audit-response process)

1. **Start from the serving log** — extract the exact model version (or best-available
   granularity) that served the prediction in question.
2. **Query the model registry for that version's recorded lineage** — training run ID,
   data version reference, feature definition version, and promotion approval record, to
   the extent each still exists.
3. **For each link that's missing or insufficiently granular, document that explicitly**
   as a finding — an honest "we can identify the model version but not the exact approver"
   is a far better audit response than either guessing or spending days reconstructing
   from Slack archaeology.
4. **Attempt data reconstruction** via the data warehouse's time-travel/versioning
   feature if available — if the data was mutable and unversioned, this step will
   conclude that exact reconstruction isn't possible, which is itself the finding to
   report.

## The Fix

- **Immediate mitigation**: assemble the best-available answer from whatever records do
  exist, explicitly flagging any gaps rather than presenting incomplete reconstruction as
  complete.
- **Long-term fix**: this scenario's real fix is architectural, not a one-time
  reconstruction effort — (1) log exact model version per prediction at serving time, not
  just endpoint identity, (2) set model-registry lineage retention explicitly for
  compliance timeframes, not default operational-log retention, (3) make promotion
  approval a structured, logged step in the promotion pipeline itself (a required
  approval gate recorded in the registry), and (4) use a versioned/immutable data layer
  (Delta Lake time-travel, DVC-tracked datasets) so "what data trained this" is always
  reconstructable, not dependent on the underlying table never having changed.

## Prevention

The systemic lesson: **lineage and audit-readiness must be designed in from the start as
a first-class requirement, not reconstructed retroactively from operational logs that
were never meant to serve that purpose.** Every tutorial's discussion of the model
registry ties back to exactly this: the registry earns its keep specifically at moments
like this one. See the lineage discussion in the
[feature store tutorial](03_feature_store_model_promotion.md#model-registry-mlflow-unity-catalog)
and the governance section of the
[cost/security tutorial](10_cost_security_multiregion.md#security-compliance-in-ml-pipelines).

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Chain-of-links framing (the default for this scenario):** "I wouldn't look for one root
  cause here — I'd walk the lineage chain link by link and report exactly which link is
  broken: serving-log granularity, registry retention, approval record-keeping, or data
  versioning. Each is independently fixable, and conflating them hides which one actually
  failed."
- **Honesty-over-completeness framing (good for the audit-response discussion):** "An
  honest 'we can identify the model version but not the exact approver' is a far better
  answer than either guessing or spending days on Slack archaeology to manufacture false
  completeness."
- **Design-in-from-the-start framing (good for the systemic lesson):** "Audit-readiness has
  to be a first-class requirement from day one, not something reconstructed retroactively
  from operational logs that were never meant to serve that purpose — this incident is what
  happens when it's treated as the latter."

### Vocabulary Builder

- **system of record** (n. phrase) — the single authoritative source for a fact (e.g. who
  approved a promotion), as opposed to information scattered across informal channels.
- **retroactively** (adv.) — after the fact, attempting to reconstruct something that
  should have been captured at the time. *"Lineage shouldn't be reconstructed
  retroactively — it should be captured at promotion time."*
- **"…is itself the finding to report"** — useful for framing a discovered gap (missing
  data, missing approval record) as a legitimate deliverable of an investigation, not a
  failure to complete it.

---

**Previous:** [9. GitOps Rollout, Wrong Predictions](12_tricky_scenarios_09_gitops_rollout_wrong_predictions.md)  |  **Next:** [11. Serving Cost Doubled After a "Routine" Upgrade](12_tricky_scenarios_11_serving_cost_doubled.md)
