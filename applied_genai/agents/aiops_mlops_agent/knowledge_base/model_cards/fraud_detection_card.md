# Model Card: fraud-detection

## Purpose
Scores incoming payment transactions for fraud risk in real time on the checkout path. A high
score blocks or step-up-authenticates a transaction before it completes.

## Criticality
Customer- and revenue-facing: false negatives cost chargebacks directly; false positives block
legitimate purchases and cost conversion. Treat drift or degradation on this model as at least
`high` severity, `critical` if AUC delta exceeds -0.10 or error rate rises sharply.

## Inputs
Reads engineered features from `pl-feature-refresh` (transaction amount, account tenure, device
fingerprint, recent transaction velocity). It has no independent data path -- a stale or failed
feature refresh degrades this model's predictions even though the model artifact itself hasn't
changed. See the fraud-detection drift postmortem for a real incident caused by exactly this.

## Deployment
Currently at v3, with v2 retained as `previous_version` for fast rollback. Baseline AUC ~0.91,
target error rate below 0.01, target p95 latency below 60ms.

## Known failure modes
- Feature staleness masquerading as data drift (see postmortem, 2026-03-11).
- Elevated latency under high QPS (checkout traffic spikes correlate with `host-infer-01`
  pressure since this model shares serving infrastructure with `recsys-ranker`).
