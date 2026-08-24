# cAdvisor

**Category:** observability / monitoring (container resource metrics, Kubernetes/EKS)

## What it is

Without cAdvisor, "how much CPU/memory is this container actually using right now" is
not a question Kubernetes answers for you directly — the kernel tracks resource usage
per **cgroup** (the Linux mechanism that isolates and limits a container's CPU/memory in
the first place), but that's raw kernel accounting, not an HTTP metric anyone can scrape.
cAdvisor (**C**ontainer **Advisor**, originally a standalone Google project, now built
directly into the **kubelet**) is the piece that reads those cgroup stats on every node
and turns them into Prometheus-format metrics — `container_cpu_usage_seconds_total`,
`container_memory_working_set_bytes`, `container_network_*`, `container_fs_*` — exposed
over HTTP at `https://<node>:10250/metrics/cadvisor`.

It ships baked into every kubelet — there's nothing separate to install or deploy. The
only thing you configure is whether something scrapes that endpoint.

## What it's used for

- Per-pod/per-container CPU and memory graphs with **zero application instrumentation**
  — the container never has to expose its own `/metrics` endpoint for this data to
  exist, because cAdvisor is reading it from the kernel's own cgroup accounting, not
  from anything the app does.
- The data source behind `kubectl top pod`/`kubectl top node` (via `metrics-server`,
  which itself aggregates cAdvisor's numbers) and behind every "CPU/Memory usage" panel
  in a Kubernetes Grafana dashboard.
- What a `resources.limits.memory` OOMKill or CPU throttling actually shows up as in a
  time series — cAdvisor is the thing that would have shown the climb beforehand.

## How it gets scraped (kube-prometheus-stack)

`kube-prometheus-stack` ships a `kubelet` `ServiceMonitor` with **three** separate
scrape endpoints on the same kubelet, each a different metrics path:

| Endpoint | What it returns |
|---|---|
| `/metrics` | The kubelet's own internal metrics (its request latency, pod-sync duration, etc.) |
| `/metrics/cadvisor` | cAdvisor's container resource metrics — the ones this doc is about |
| `/metrics/probes` | Liveness/readiness/startup probe results as metrics |

All three show up in Prometheus's target list as separate entries under the same
`serviceMonitor/<ns>/<release>-kube-promethe-kubelet/{0,1,2}` job (index `1` is
`/metrics/cadvisor`), one target per node.

## Usage — verified live against this repo's cluster

Deployed via [`k8s_observability/metrics-stack/`](../../../../k8s_observability/metrics-stack/)
(a `kube-prometheus-stack` install), queried building the
[`demo-app` Grafana dashboard](../../../../k8s_observability/metrics-stack/dashboards/demo-app.json):

```promql
sum(rate(container_cpu_usage_seconds_total{namespace=~"$namespace", pod=~".*demo-app.*"}[5m])) by (pod)
sum(container_memory_working_set_bytes{namespace=~"$namespace", pod=~".*demo-app.*"}) by (pod)
```

**A real gotcha hit building that dashboard:** on this cluster, cAdvisor reports a
single-container pod's usage with an **empty `container` label** — the series is a
pod-level cgroup-slice aggregate (`id: /kubepods.slice/.../kubepods-burstable-pod<uid>.slice`),
not the per-container breakdown you'd get on a cluster where cAdvisor also emits the
finer-grained per-container cgroup series. A query filtered on `container="demo-app"`
against `container_cpu_usage_seconds_total` silently returns **zero results** — not an
error, just an empty panel that looks like "no traffic" instead of "wrong label". The
fix was matching on `pod=~"..."` instead of `container="..."` for the cAdvisor-sourced
metrics specifically (`kube_pod_container_status_running` and
`kube_pod_container_status_restarts_total`, both from **kube-state-metrics** rather than
cAdvisor, do carry a reliable `container` label — see
[`kube-state-metrics`](../kube-state-metrics/README.md) for why that's a different data
source with different label guarantees).

## Related

[`../../observability-prometheus-and-cadvisor.md`](../../observability-prometheus-and-cadvisor.md) —
a broader mental-model walkthrough (Prometheus pull model, TSDB, `remote_write`,
Kubernetes service discovery) this doc's cAdvisor section is one piece of.

[`kube-state-metrics`](../kube-state-metrics/README.md) is the other half of "metrics
about pods with zero app instrumentation" — cAdvisor answers *how much resource is this
container using*, kube-state-metrics answers *what state is this Kubernetes object in*
(running/restarted/desired-vs-available replicas). [Prometheus](../prometheus/README.md)
scrapes both; a `kube-prometheus-stack` install wires up both by default.
