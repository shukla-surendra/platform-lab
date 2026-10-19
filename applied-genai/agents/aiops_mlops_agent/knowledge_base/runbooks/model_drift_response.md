# Runbook: Model Drift / Performance Degradation

## When to use this runbook
An alert fires when either `check_data_drift` reports one or more drifted features (drift score
above 0.3) or `check_model_drift` reports an AUC delta worse than -0.05 against the 30-day
baseline. Both checks are per model version.

## Triage steps
1. Pull `get_model_status` for current latency, error rate, and QPS -- confirm the model is
   actually serving degraded predictions, not just showing a noisy offline metric.
2. Run both `check_data_drift` and `check_model_drift` for the deployed version. Data drift
   without performance drift is often a leading indicator (retrain proactively); performance
   drift without data drift usually means a downstream labeling or feature-pipeline bug rather
   than genuine distribution shift.
3. Check `pl-feature-refresh` pipeline status. A stale feature refresh is the single most common
   root cause of a sudden AUC drop that looks like drift but isn't -- rule this out before
   assuming the model itself needs retraining.

## Decision guide
- **Confidence high, feature-pipeline healthy, AUC delta worse than -0.10**: roll back to the
  previous deployed version immediately (`rollback_model`), then trigger a retrain
  (`trigger_retrain`) on current data. Rollback restores serving quality in seconds; retraining
  on the drifted distribution takes hours, so do both, in that order.
- **Confidence moderate, AUC delta between -0.05 and -0.10, feature pipeline healthy**: trigger a
  retrain without rolling back -- a small, gradual degradation is often better served by refreshing
  training data than reverting to an older, differently-biased version.
- **Feature pipeline stale/failed**: fix the pipeline first (see the pipeline-failure runbook).
  Do not roll back or retrain the model until upstream data is confirmed fresh -- retraining on
  stale features just reproduces the problem.
- **Low confidence / ambiguous signal**: escalate to a human rather than auto-remediate. A wrong
  automatic rollback on a healthy model is expensive (lost improvement from the newer version);
  a wrong retrain trigger is comparatively cheap (wasted compute, no serving impact).

## Escalation
File an incident ticket with severity `critical` if the model serves a customer-facing surface
(fraud-detection, checkout-facing ranking) and AUC delta exceeds -0.10. Otherwise `high` is
sufficient. Always include the feature drift scores and AUC delta in the ticket summary so a
human reviewer doesn't have to re-run the checks.
