# Model Card: recsys-ranker

## Purpose
Ranks product recommendations shown on the home page and post-purchase upsell surface. Not on
the checkout critical path -- a bad ranking loses some engagement, it doesn't block a purchase.

## Criticality
Medium. Drift or latency degradation here should generally not auto-page on-call outside business
hours; `medium` severity is usually correct unless error rate climbs above 5%, which indicates a
genuine serving failure rather than a ranking-quality issue.

## Inputs
Highest QPS of any deployed model (~940 QPS baseline) and shares `host-infer-01` with
`fraud-detection`. A capacity or latency issue on this host can look like a `recsys-ranker`
problem when the actual pressure is coming from `fraud-detection` traffic, or vice versa --
check both models' status before concluding either one individually is the cause of shared-host
pressure.

## Deployment
Currently at v4, retrained most recently via `pl-model-retrain` on a 90-day window (AUC 0.902 at
last retrain). Baseline latency p95 ~120ms, higher than the other two models by design (ranking
involves more candidates per request than a single fraud score).

## Known failure modes
- Latency spikes correlated with shared-host pressure from `fraud-detection`, not its own load.
- Because it's not customer-blocking, degradation here is easy to under-prioritize -- but a
  ranking model that's silently bad for days has real, if less visible, revenue impact.
