# Runbook: CI/CD & Data Pipeline Failure Triage

## When to use this runbook
`get_pipeline_run` reports `last_status: failed` for `pl-daily-etl`, `pl-feature-refresh`, or
`pl-model-retrain`.

## Reading the failure logs
`last_logs` almost always identifies one of four categories -- match on these substrings before
deciding an action:

- **`freshness SLA` / `last modified`** -> upstream source data is stale. This is not a bug in
  the pipeline itself; retrying immediately will fail again with the same error. Wait for the
  upstream source to refresh, or escalate to the upstream data owner. Do not retry blindly.
- **`column ... not found` / `schema`** -> upstream schema drift. Retrying will fail identically.
  Roll back the pipeline to its last known-good config (`rollback_deployment`) only if the
  pipeline itself changed; if the *source* schema changed, this needs a code fix (new column
  mapping) that no automated action here can make -- escalate.
- **`heap space` / `OOM` / `killed by YARN`** -> the job ran out of memory, usually from a data
  volume spike, not a code defect. Retrying with the same resources usually fails the same way.
  Escalate for a resource bump; do not just retry.
- **`connection reset` / `network`** with no schema or freshness complaint -> transient
  infrastructure blip. This is the one category safe to retry automatically (`retry_pipeline`) --
  the underlying data and code are fine, the failure was environmental.

## Decision guide
- **Transient (network/connection)**: retry immediately, once. If the retry also fails, treat as
  a different, unknown category and escalate rather than retrying again.
- **Upstream stale / schema drift / OOM**: do not retry. Either roll back to last known-good
  (if the pipeline's own config/artifact is suspect) or escalate to a human -- none of these three
  are fixed by simply running the same job again.
- **Downstream blast radius**: `pl-feature-refresh` failing affects every model that reads those
  features (see model cards) -- treat its failures as higher severity than `pl-daily-etl` alone,
  since a stale feature refresh can masquerade as model drift days later.

## Escalation
`critical` if `pl-feature-refresh` or `pl-model-retrain` fails for a reason other than transient
(the failure blocks or corrupts a model-facing pipeline). `high` for `pl-daily-etl` non-transient
failures. Transient failures that succeed on retry don't need a ticket at all.
