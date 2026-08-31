# Getting logs and metrics out of an app with no logging or metrics code

Worked example: [`rust-sqlite-api`](../../public_docker_images/rust-api) (the pod is still
named `rust-sqlite-api-0` on this cluster from before the rename — see
[`rust-sqlite-api-stack`](../../rust-sqlite-api-stack)). As of image `1.0.0` it exposes **no
`/metrics` endpoint at all** — that layer was deliberately removed. The question this
answers: can Grafana still show something useful for it, and does an app need to expose
anything for that to work?

**Short answer: logs need nothing from the app beyond writing to stdout, which every app
already does. Metrics need either something from the app (even indirectly, via its
existing logs) or something that observes the app from outside — infra-level tools that
work identically for any container, code unseen.**

## Logs: zero code required, always

This is not a workaround — it is the standard container logging model. A container's
stdout/stderr *is* its log stream; the runtime captures it to a file on the node
regardless of what the app does or does not know about logging frameworks:

```
app writes to stdout (println!, printf, a logger — anything)
        │
        ▼
container runtime captures it → /var/log/pods/<ns>_<pod>_<uid>/<container>/0.log
        │
        ▼
Promtail (DaemonSet, tails that file) → Loki → Grafana
```

No `/logs` endpoint, no log-shipping library, no code change — this chart's Promtail
already tails every pod in the cluster this way (see the parent chart's own
`README.md` §"How logs actually reach Grafana" for the five things that *can* still go
wrong in that pipeline). Structured JSON logs make the content more useful once it
arrives, but even a plain `println!` line would show up.

## Infra metrics: also zero code, verified live

Two components already deployed by `kube-prometheus-stack` (this chart's dependency)
watch every pod on the cluster from outside, with no cooperation from the app:

| Source | What it reports | How it sees the pod |
|---|---|---|
| **cAdvisor** (built into kubelet, one per node) | CPU, memory, network, filesystem — per container | Reads the container's cgroup directly |
| **kube-state-metrics** | Restart count, pod phase, resource requests/limits, age | Reads Kubernetes object state via the API server |

Confirmed against the actual `rust-sqlite-api-0` pod on this cluster, which exposes
nothing itself:

```bash
$ kubectl -n observability port-forward svc/rsa-kube-prometheus-stack-prometheus 9091:9090

$ curl -sG localhost:9091/api/v1/query \
    --data-urlencode 'query=container_cpu_usage_seconds_total{pod=~"rsa-rust-sqlite.*"}'
# → real series, labelled by node/pod, sourced entirely from cAdvisor

$ curl -sG localhost:9091/api/v1/query \
    --data-urlencode 'query=kube_pod_container_status_restarts_total{pod=~"rsa-rust-sqlite.*"}'
# → {"rsa-rust-sqlite-api-0": "0"} — real, from kube-state-metrics
```

This is enough for the health-of-the-process story — is it up, is it restarting, is it
using more memory than expected — without the app doing anything. It cannot tell you
anything about what the app is *doing* (request rate, error rate, latency), because
cAdvisor and kube-state-metrics only see the container from the outside, not its traffic.

## Request-level metrics without a `/metrics` endpoint: derived from logs

`rust-api` has no metrics endpoint, but it does log one structured line per HTTP request
— not because anyone built that for metrics, but as a side effect of `tower_http`'s
request-tracing middleware (`TraceLayer`, already present for the log-generation story).
That line carries `method`, `uri`, `status`, and `latency`. Loki's query language,
**LogQL**, can turn matching log lines into a genuine Prometheus-shaped time series —
Grafana renders a `count_over_time`/`rate`/`quantile_over_time` LogQL query in exactly
the same panel type as a PromQL one.

Verified live against real traffic already in Loki from this session:

```bash
# requests/sec, purely from access-log lines — no app metric exists for this
$ curl -sG localhost:3100/loki/api/v1/query --data-urlencode \
    'query=sum(rate({app="rust-sqlite-api"} |= "on_response" [10m]))'
# → 0.3

# status-code breakdown, same source
$ curl -sG localhost:3100/loki/api/v1/query --data-urlencode \
    'query=sum by (fields_status) (count_over_time({app="rust-sqlite-api"} |= "on_response" | json [30m]))'
# → {"200": "539"}
```

### The gotcha: `unwrap` needs a bare number, and tower_http doesn't give you one

Latency percentiles need LogQL's `unwrap`, which extracts a numeric value from a field
to aggregate over (`quantile_over_time`, `avg_over_time`, etc.). The naive query fails:

```bash
$ curl -sG localhost:3100/loki/api/v1/query_range --data-urlencode \
    'query=quantile_over_time(0.95, {app="rust-sqlite-api"} |= "on_response" | json | unwrap fields_latency [10m])'
# → 400 Bad Request: SampleExtractionErr
#   fields_latency="0 ms" — "0 ms" is not a number
```

`tower_http` Debug-formats its `Latency` as `"0 ms"` — a string, with a space before the
unit. LogQL *does* have a unit-aware conversion, `unwrap duration_seconds(field)`, built
exactly for values like `"500ms"` or `"1.2s"` — but it uses Go's `time.ParseDuration`
grammar underneath, which requires **no space** between the number and the unit. `"0 ms"`
fails that parser for the same reason `"0ms"` would succeed. The fix is a `label_format`
stage that strips the space before unwrapping:

```bash
$ curl -sG localhost:3100/loki/api/v1/query_range --data-urlencode \
    'query=quantile_over_time(0.95, {app="rust-sqlite-api"} |= "on_response" | json
       | label_format fields_latency=`{{ .fields_latency | replace " " "" }}`
       | unwrap duration_seconds(fields_latency) [10m])'
# → 200 OK, real matrix data
```

Confirmed working, not assumed — this exact 400 was reproduced and then fixed live
against the pod on this cluster. Worth knowing before wiring a latency panel: the field
existing and looking numeric in the raw log line is not the same as LogQL being able to
parse it, and the error message names the mechanism precisely enough to fix without
guessing (`SampleExtractionErr` on that specific label).

## What this *can't* do: domain metrics

Log- and infra-derived metrics answer "is it up, is it busy, is it slow, what's its
error rate" — the RED metrics (Rate, Errors, Duration) that apply to any HTTP service.
They cannot answer anything the app alone knows the meaning of: "how many orders were
placed," "cache hit ratio," "queue depth by tenant." Nothing observing a container from
outside — cAdvisor, kube-state-metrics, or a log-line parser — can invent a business
concept the app never wrote down anywhere, in any form. That is the one real case
`/metrics` (or some other reporting mechanism) is *necessary* for, not merely convenient.

## The other family: eBPF and service-mesh auto-instrumentation

Log-derived metrics still depend on the app happening to log something useful, which
`rust-api` does only because `tower_http` was already there for a different reason. A
different tool family gets request-level metrics for *any* HTTP/gRPC service without
even that — by observing traffic at the kernel or proxy layer instead of parsing text:

- **eBPF auto-instrumentation** (Grafana **Beyla**, Pixie) — attaches to the running
  process via eBPF probes on syscalls/kernel network events, derives RED metrics for
  HTTP/gRPC traffic with no code change and no restart. This is the direct answer to
  "services which extract these without modifying code" when the app doesn't even log
  the request.
- **Service mesh sidecar** (Istio/Linkerd's Envoy) — every request is proxied through a
  sidecar container injected into the pod; the proxy reports RED metrics for whatever
  passes through it. Zero app code changes, but it is an infrastructure change (inject a
  proxy into every pod), heavier to operate than the log- or eBPF-based approaches.

Neither is deployed on this cluster — noted here as the answer to "is there a tool for
this" rather than as something verified live, unlike everything above it.

## Practical answer

**No, an application does not need a `/metrics` or `/logs` endpoint to show up in
Grafana.** What it needs depends on what you want to see:

| Want to see | Needs from the app | Already true here |
|---|---|---|
| Logs | Writes to stdout | Yes — every container does this by default |
| Is it up / restarting / using memory | Nothing | Yes — cAdvisor + kube-state-metrics, zero setup |
| Request rate / status / latency | Logs *something* structured per request | Yes, incidentally — `tower_http` tracing |
| Business-specific counters | The app must report them, somehow | No — this is the one real gap |
