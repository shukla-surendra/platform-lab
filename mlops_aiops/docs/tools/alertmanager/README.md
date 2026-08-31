# Alertmanager

**Category:** observability / monitoring (alert routing)

## What it is

The component that turns "a metric crossed a threshold" into "the right
person got paged." Prometheus's own job stops at *evaluating* alerting
rules — a PromQL expression like `drift_detected == 1` either matches or
it doesn't, on a schedule, per rule. Prometheus doesn't know what a Slack
channel is, doesn't deduplicate two nodes firing the same underlying
problem, and doesn't know that three related alerts should be batched into
one notification instead of three. Alertmanager is the separate process
that receives already-fired alerts over Prometheus's alert-push protocol
and does all of that: deduplicating, grouping related alerts together,
routing each group to the right receiver (Slack, PagerDuty, email, a
generic webhook) via a tree of matchers, and silencing/inhibiting alerts on
demand. Prometheus evaluates; Alertmanager decides who hears about it and
how often.

## What it's used for

- **Routing** — a `route` tree matches alert labels (e.g. `severity:
  critical` -> PagerDuty, `severity: warning` -> Slack) and picks a
  receiver, falling through to a default route if nothing more specific
  matches.
- **Grouping** — alerts sharing labels (`group_by: [alertname, cluster]`)
  get batched into one notification instead of paging once per firing
  alert, which matters when one root cause trips many rules at once.
- **Timing controls** — `group_wait` (how long to wait for more alerts to
  join a group before the first notification), `group_interval` (how often
  to re-notify a growing group), `repeat_interval` (how often to re-send an
  unresolved alert that hasn't changed) — these exist because "notify
  instantly on every evaluation" would be far too noisy for anything with a
  short scrape interval.
- **Silencing/inhibition** — mute a known issue temporarily, or suppress a
  lower-severity alert automatically when a related higher-severity one is
  already firing (e.g. don't page on every pod's alerts when the whole node
  is already down).

## Deployment

Most commonly installed bundled inside the **`kube-prometheus-stack`** Helm
chart alongside Prometheus and [Grafana](../grafana/README.md) — the
three come up together with Alertmanager pre-wired as Prometheus's alert
receiver. It's also published as its own standalone chart
(`prometheus-community/alertmanager`) for setups that want Prometheus,
Alertmanager, and Grafana as independently versioned/installed pieces
instead of one bundle — used this way in
[`k8s/k8s_observability/practice/streaming-drift-detection/05-dashboards-alerts/`](../../../../k8s/k8s_observability/practice/streaming-drift-detection/05-dashboards-alerts/),
where Prometheus lives in a different chart
([`04-metrics-export/`](../../../../k8s/k8s_observability/practice/streaming-drift-detection/04-metrics-export/))
than Alertmanager and Grafana do — `kube-prometheus-stack`'s all-in-one
bundling would have put Alertmanager in the wrong stage of that project's
5-stage pipeline split (see that project's README for the full reasoning).
Cross-chart, Prometheus just needs Alertmanager's address in its own config
(`alerting.alertmanagers`); nothing about that wiring requires them to be
installed by the same chart.

## Alertmanager vs. Grafana's built-in alerting

Grafana can also evaluate rules and route alerts entirely on its own
(**Grafana-managed alerting**, unified in modern Grafana versions),
querying any of its datasources — not just Prometheus — and routing
through Grafana's own notification policies, without Alertmanager in the
loop at all. The two aren't mutually exclusive: a Grafana Alertmanager
datasource (pointed at a real Alertmanager instance) lets Grafana's UI
*display and silence* alerts that Prometheus + Alertmanager already own the
routing for, which is a different thing from Grafana evaluating and routing
them itself. Which one owns evaluation+routing for a given rule is a
one-time choice per rule, not a layered pipeline — picking Prometheus-rule +
Alertmanager keeps alerting logic next to the PromQL that triggers it
instead of splitting it into a second system.

## Related

[Prometheus](../prometheus/README.md), [Grafana](../grafana/README.md).
