# kube-state-metrics

**Category:** observability / monitoring (Kubernetes object state, Kubernetes/EKS)

## What it is

Kubernetes' own API server already knows everything about the state of every object —
`kubectl get deployment` shows you `3/3` ready, `kubectl get pod` shows you `Running`
with `2` restarts. But that's a point-in-time answer to a question you type by hand; it
is not a metric a dashboard can graph over time or an alert can fire on. kube-state-metrics
is a small service that **watches the API server** (the same watch mechanism every
controller uses) and re-exposes what it sees as plain Prometheus metrics — `kube_pod_status_phase`,
`kube_pod_container_status_restarts_total`, `kube_deployment_status_replicas_available`,
and hundreds more, one metric per object-state field it tracks.

It's a **separate Deployment** (unlike [cAdvisor](../cadvisor/README.md), which is built
into every kubelet) — one pod, reading from the API server, with no per-node component
needed since the API server already has cluster-wide state.

## What it's used for

- "Is this Deployment actually at its desired replica count" as a metric, not a manual
  `kubectl get` check — `kube_deployment_status_replicas_available` vs.
  `kube_deployment_spec_replicas`.
- Restart counts (`kube_pod_container_status_restarts_total`) — the number that turns
  into "Restarts (1h)" panels and crash-loop alerts, with **zero app instrumentation**:
  the app never has to report its own restarts, because the kubelet already reports them
  to the API server as part of normal pod status, and kube-state-metrics just relays it.
- Object-existence/scheduling facts that have no other metric source at all —
  `kube_pod_container_status_running` (is this container's phase actually Running,
  labeled by pod/namespace/container), `kube_node_status_condition`, `kube_pod_status_unschedulable`.

## kube-state-metrics vs. cAdvisor — two different questions

Both get lumped together as "the metrics you get for free, no app changes needed" —
but they answer genuinely different questions from genuinely different data sources:

| | [cAdvisor](../cadvisor/README.md) | kube-state-metrics |
|---|---|---|
| Question it answers | How much CPU/memory is this container *actually using* | What *state* is this Kubernetes object in |
| Data source | Linux cgroup accounting, read by the kubelet | The Kubernetes API server (object status fields) |
| Where it runs | Built into every kubelet (one per node) | One separate Deployment, cluster-wide |
| Example metric | `container_cpu_usage_seconds_total` | `kube_pod_container_status_restarts_total` |
| `container` label reliability | Not guaranteed — can be empty (pod-slice aggregate) on some clusters, see cAdvisor's doc | Reliable — comes straight from the API server's own object fields |

## Usage — verified live against this repo's cluster

Deployed via [`k8s_observability/metrics-stack/`](../../../../k8s_observability/metrics-stack/)
(bundled by `kube-prometheus-stack`, on by default), queried building the
[`demo-app` Grafana dashboard](../../../../k8s_observability/metrics-stack/dashboards/demo-app.json):

```promql
count(kube_pod_container_status_running{namespace=~"$namespace", container="demo-app"} == 1)
sum(increase(kube_pod_container_status_restarts_total{namespace=~"$namespace", container="demo-app"}[1h]))
```

Both filter on `container="demo-app"` directly and work fine — unlike the cAdvisor
queries on the same dashboard, which had to fall back to matching on `pod=~"..."`
instead (see [cAdvisor's doc](../cadvisor/README.md#usage--verified-live-against-this-repos-cluster)
for why).

## Related

[Prometheus](../prometheus/README.md) scrapes it like any other target;
[Grafana](../grafana/README.md) is what turns its metrics into panels.
[`kube-prometheus-stack`](../prometheus/README.md#deployment) deploys it automatically
alongside Prometheus/Grafana/Alertmanager/node-exporter — nothing here needs enabling by
hand on a standard install.
