# 9. GitOps Rollout, Wrong Predictions

**Primary topic:** [GitOps & CI/CD for ML](09_gitops_ml_cicd.md)

## The Situation

A model update passed every CI gate (data validation, model quality threshold,
integration tests) and was merged. ArgoCD synced the change cleanly — no sync errors, no
drift detected. Within an hour, the model is serving noticeably wrong predictions in
production. Staging, which uses the identical Git-declared configuration, looks fine.

## First Questions to Ask

- Is "identical configuration" actually verified, or assumed — are staging and production
  pointed at the exact same config values, or do they use environment-specific overlays
  (Kustomize/Helm values) that could differ?
- Does the model artifact reference (image tag, model registry version) resolve to the
  *same* concrete artifact in both environments, or could a mutable tag (like `:latest`)
  have resolved differently at different sync times?
- Are there any environment-specific secrets or config (API keys, feature-store endpoints,
  a different online-store replica) that the model depends on at runtime?
- Did staging traffic actually exercise the same input distribution as production, or is
  staging traffic synthetic/limited in a way that wouldn't surface this?

## Likely Root Causes (ranked)

1. **A mutable artifact reference resolved differently between environments.** If the
   deployment manifest references a model by a mutable tag (`:latest`, or a "current"
   alias) rather than an immutable version/digest, ArgoCD syncing "the same Git config"
   in both environments can still deploy *different actual artifacts* if that mutable tag
   was repointed between the two syncs — this is a classic GitOps anti-pattern: the Git
   state was declaratively identical, but the referenced artifact wasn't pinned, so
   "identical config" didn't mean "identical deployment."
2. **Environment-specific config divergence** (a Kustomize overlay or Helm values
   difference) pointing production at a different upstream dependency than staging — e.g.
   a different online feature-store endpoint, a different embedding-model version, or a
   different secret — that wasn't caught because the *model config itself* matched, even
   though a *runtime dependency* it relies on differed.
3. **Staging traffic isn't representative of production input distribution**, so the
   actual bug (which depends on specific input characteristics) simply never gets
   exercised in staging regardless of configuration parity.

## Diagnostic Path

1. **Resolve the exact deployed artifact in both environments** — not the tag/reference in
   the manifest, but the actual immutable digest/version currently running — and confirm
   whether they match. This single check either confirms or eliminates root cause #1
   immediately.
2. **Diff the full effective configuration** (post-overlay, not just the base manifest)
   between staging and production — this catches environment-specific divergence that
   "the Git config looks the same" would miss, since overlays are exactly designed to
   differ per environment.
3. **Compare the actual runtime dependencies** the model calls (feature-store endpoint,
   embedding service version, any downstream API) between environments — a working model
   with a misconfigured dependency looks identical in ArgoCD's sync status, since ArgoCD
   only reconciles what's declared in Git, not runtime behavior.
4. **Sample production inputs causing wrong predictions** and replay them against staging
   directly — if staging reproduces the bug given the same input, it confirms a runtime
   environment difference rather than a staging-traffic representativeness gap.

## The Fix

- **Immediate mitigation**: roll back via the same GitOps mechanism (revert the merge,
  let ArgoCD reconcile back) rather than a manual patch, to preserve the audit trail per
  the [GitOps tutorial](09_gitops_ml_cicd.md#failure-modes-to-raise-proactively).
- **Long-term fix**: pin all model/artifact references to immutable digests or explicit
  version numbers, never mutable tags — and add an environment-config-parity check to CI
  that diffs the *effective* (post-overlay) configuration between staging and production,
  flagging unexpected divergence before merge, not after an incident reveals it.

## Prevention

The systemic lesson: **"ArgoCD says synced" only guarantees Git-declared state matches
live state — it says nothing about whether that declared state actually resolves to the
same real-world artifact/dependencies across environments.** Immutable references and
explicit environment-parity checks are what actually close this gap; drift detection alone
doesn't. See the reconciliation-loop discussion in the
[GitOps tutorial](09_gitops_ml_cicd.md#argocds-reconciliation-loop).

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Scope-of-guarantee framing (the default for this scenario):** "'ArgoCD says synced'
  only guarantees Git-declared state matches live state — it says nothing about whether
  that declared state resolves to the same real-world artifact across environments. That
  gap is exactly where this bug lives."
- **Mutable-reference framing (good for explaining the core mechanism):** "A mutable tag
  means 'identical Git config' doesn't mean 'identical deployment' — the tag can point to
  different actual content depending on when each environment happened to sync. I'd pin
  every model reference to an immutable digest specifically to close this gap."
- **Layered-diff framing (good for the diagnostic walkthrough):** "I wouldn't stop at 'the
  manifests match' — I'd diff the *effective*, post-overlay configuration, and separately
  resolve the actual deployed artifact digest in both environments, because either layer
  can diverge while the other looks identical."

### Vocabulary Builder

- **mutable vs. immutable reference** (adj. phrase) — a pointer that can silently change
  what it resolves to (`:latest`) versus one that always resolves to the exact same
  artifact (a digest or explicit version).
- **effective configuration** (n. phrase) — the final, post-overlay config actually
  applied, as opposed to the base manifest, which can look identical while the effective
  result differs.
- **"…looks identical in sync status, since it only reconciles what's declared"** — a
  precise way to name the limits of a reconciliation guarantee without dismissing its
  value.

---

**Previous:** [8. Stale Checkpoint After Preemption](12_tricky_scenarios_08_stale_checkpoint_resume.md)  |  **Next:** [10. Reconstructing Model Lineage for an Audit](12_tricky_scenarios_10_audit_lineage_reconstruction.md)
