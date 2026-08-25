# 05-dashboards-alerts

Grafana (one dashboard, `Drift Overview`, tracking `drift_score` and
`drift_detected` from `04-metrics-export`'s Prometheus) plus a standalone
Alertmanager. Stage 5 of [`../`](../) — the human-facing end of the
pipeline.

**Status: scaffolded, not installed.** Both dependency versions (`grafana`
12.11.2, `alertmanager` 1.42.0) are pinned to versions already confirmed
real (grafana matches the already-verified pin in
[`../../trace-stack/Chart.yaml`](../../trace-stack/Chart.yaml); alertmanager
confirmed live against its own `Chart.yaml` on GitHub). Values have not been
diffed against either chart's schema yet.

## Why the alert *rule* isn't defined here

Alertmanager only routes alerts that already fired — it doesn't evaluate
PromQL. Evaluating `drift_detected == 1` and deciding when that becomes a
firing alert is Prometheus's job, which means the rule itself has to live
in `04-metrics-export`'s Prometheus config
([`../04-metrics-export/values.yaml`](../04-metrics-export/values.yaml)'s
`prometheus.serverFiles.alerting_rules.yml`), not here — this chart's
Prometheus is the plain community chart, with no `PrometheusRule` CRD a
different chart could contribute rules through the way
`kube-prometheus-stack` allows. What this chart owns instead: **routing**
(Alertmanager's `config.route`/`config.receivers`) and **visualization**
(the dashboard) — the two things that are genuinely about presenting an
already-computed signal to a human, which is what "dashboards & alerts"
means here.

## No real receiver wired up yet

`alertmanager.config.receivers` is just `null` — there's no Slack
webhook/PagerDuty key/email server on a practice cluster to route to.
`FeatureDriftDetected` firing will show up in Alertmanager's own UI and in
Grafana's Alertmanager datasource, but won't notify anyone until a real
receiver replaces the `null` one. Confirm the alert actually reaches
Alertmanager first (`kubectl port-forward svc/alertmanager 9093:9093`,
check `/api/v2/alerts`) before spending time on receiver config.

## Install

```bash
helm dependency build .
helm install dashboards-alerts . -n drift-detection --create-namespace
```

## Related

- [`../README.md`](../README.md) — the full pipeline.
- [`../04-metrics-export/`](../04-metrics-export/) — where the alert rule
  itself actually lives, and why.
- [`../../mlops_aiops/docs/tools/grafana/README.md`](../../mlops_aiops/docs/tools/grafana/README.md).
