# Postmortem: fraud-detection AUC drop, 2026-03-11

## Summary
`fraud-detection` v3's live AUC dropped from a 0.91 baseline to 0.79 over six hours. On-call
initially assumed classic feature drift and scheduled a retrain. The actual cause was a failed
`pl-feature-refresh` run twelve hours earlier that went unnoticed because the pipeline failure
did not, by itself, page anyone -- only the resulting model degradation did.

## Timeline
- 02:14 -- `pl-feature-refresh` fails silently (upstream `warehouse.transactions` table stale).
  No alert fires; pipeline failures were not yet wired to the on-call rotation.
- 02:14 - 08:00 -- `fraud-detection` continues serving on increasingly stale features. Prediction
  quality degrades gradually as the feature values drift further from the live transaction
  pattern.
- 08:03 -- AUC monitor fires. On-call checks `check_data_drift` and `check_model_drift`, sees
  drifted features, and starts a retrain under the assumption of genuine distribution shift.
- 09:40 -- Retrain completes on the same stale features (feature refresh was still broken),
  producing a new model version that is no better than the one it replaced.
- 10:15 -- Someone finally checks `pl-feature-refresh` status directly and finds it failed at
  02:14. Feature refresh is fixed and re-run.
- 11:05 -- A second retrain on fresh features restores AUC to 0.90.

## Root cause
A stale feature pipeline masquerading as model drift. The drift checks correctly reported
drifted features, but the drift was an artifact of stale inputs, not a real distribution shift in
customer behavior -- retraining on the same stale inputs could never have fixed it.

## Lessons / what changed
1. **Always check the upstream feature pipeline's status before diagnosing drift as "the model
   needs retraining."** This is now the second step in the model-drift runbook, not an
   afterthought.
2. A retrain triggered without first confirming fresh inputs wastes the retrain and delays the
   real fix -- in this incident, by about two hours.
3. Pipeline failures now notify the same channel as model-quality alerts, so a stale-feature
   root cause surfaces before someone spends an hour chasing the wrong fix.
