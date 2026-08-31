# log-stack

A thin wrapper chart around the upstream `grafana/loki-stack` chart, tuned for this
repo's local `minikube` cluster. One `helm install` gives you all three pieces of a
logging pipeline together:

1. **A demo app** — a busybox loop writing JSON log lines to stdout every 2s
   (`templates/demo-app-deployment.yaml`). No `/metrics`, no Service — nothing
   Loki-specific about it.
2. **Promtail** (DaemonSet, one pod per node), tailing every container's stdout on its
   node and shipping it to Loki — the demo app needed zero changes for this to happen.
3. **Loki** storing it, **Grafana** querying Loki.

Logs only — no Prometheus, no metrics. For metrics, see
[`../metrics-stack/`](../metrics-stack/) instead.

## Where this is installed

- **Cluster:** `minikube` profile
- **Namespace:** `log-stack` (dedicated, so it can be installed/removed as one unit) —
  the verified install below actually ran in `default`, alongside `metrics-stack`; see
  that chart's README for why the docs and the actual install can diverge on names.
- **Release name:** `log-stack`
- **Method:** local chart wrapping `grafana/loki-stack` (Helm), not raw manifests/kustomize

## Install

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm dependency build .   # first time only; fetches loki-stack into charts/

helm install log-stack . \
  --namespace log-stack \
  --create-namespace
```

## Upgrade

```bash
helm upgrade --install log-stack . --namespace log-stack --create-namespace
```

**Always repeat every `--set` you installed with** — Helm does not remember them.

## Access Grafana

```bash
kubectl get pods -n log-stack -l app.kubernetes.io/name=grafana
minikube service log-stack-grafana -n log-stack --url
# or: kubectl -n log-stack port-forward svc/log-stack-grafana 3000:80
```

Login: `admin` / `admin`. The Loki datasource is pinned to `uid: loki`
(`values.yaml`'s `loki-stack.loki.datasource.uid`) rather than left to Grafana's
auto-generated one — that's what lets `dashboards/demo-app-logs.json` reference a fixed
`"datasource": {"type": "loki", "uid": "loki"}` and actually resolve. Leaving this
unpinned is a real failure mode: every log panel renders empty with no error anywhere
to explain why (same class of bug documented for the Prometheus/Grafana pairing in
[`../metrics-stack/README.md`](../metrics-stack/README.md)).

## The demo app and its dashboard

```bash
kubectl -n log-stack logs -l app=demo-app,release=log-stack -f
```

The `release=log-stack` half of that selector matters as soon as more than one of
these charts share a namespace (they do on this cluster's actual install — see
"Where this is installed" above): `metrics-stack` and `trace-stack` both ship a demo
app with this same `app=demo-app` label, and `kubectl logs -l app=demo-app` alone
matches pods across all of them, not just this release's own.

```json
{"level":"INFO","msg":"heartbeat 31","ts":"2026-08-24T11:03:34Z"}
{"level":"ERROR","msg":"heartbeat 30","ts":"2026-08-24T11:03:32Z"}
```

Every 10th line is `ERROR`, every 5th (non-10th) is `WARN`, verified live by querying
Loki directly:

```bash
kubectl -n log-stack port-forward svc/log-stack-loki 3100:3100
curl -sG http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={app="demo-app"} | json | level="ERROR"'
```

Open Grafana → **Dashboards** → **"log-stack — demo app logs"** for four panels built
on that: error-line count, total-line count (proves the pipeline is moving lines at
all), log rate by level, and a live log stream with a Level filter. Or query ad hoc in
**Explore** → **Loki**:

```logql
{app="demo-app"}
{app="demo-app"} | json | level="ERROR"
```

These LogQL queries filter on Loki's `app` label only, which Promtail derives straight
from the pod's `app` label — the `release` label added above to fix the Kubernetes-level
selector bug isn't threaded through to Loki (that would mean overriding Promtail's own
`relabel_configs`, not done here). In practice this is low-risk: the other releases'
demo apps either emit nothing to stdout or nothing shaped like this app's JSON lines, so
`| json | level=...` filtering mostly excludes them anyway — but it's a real gap, not a
guarantee, if `metrics-stack`'s or `trace-stack`'s demo app ever starts logging JSON with
a `level` field of its own.

## A real gotcha, verified live on this exact install

`values.yaml`'s `promtail.config.snippets.pipelineStages` **must match the cluster's
container runtime** — `docker: {}` here, because this cluster's nodes report
`docker://...` (`kubectl get node -o jsonpath='{.items[0].status.nodeInfo.containerRuntimeVersion}'`).
Get it wrong (e.g. `cri: {}`, upstream's own default) and logs still arrive in Loki and
look fine in the Live stream panel — but `| json` parses the container runtime's
*wrapper* around the line instead of the line itself, so `level` is always empty and
every level-filtered panel (three of the four on this dashboard) silently reads zero,
with nothing anywhere indicating why. Confirmed the reverse on this install: the query
above returned real `ERROR` lines, so the stage is unwrapping correctly.

**Also observed on this install**: one `promtail` DaemonSet pod
(on the `minikube-m02` node specifically) crash-looped with
`error creating promtail" error="failed to make file target manager: too many open
files"` — an inotify/file-descriptor limit on that specific node (this is a WSL2
minikube host), not a chart misconfiguration. The other two nodes' Promtail pods came
up healthy, including the one on the same node as the demo app, so log shipping for
this chart's own demo app was unaffected — but a pod scheduled onto `minikube-m02`
would have a gap in its logs until that node's limit is raised
(`sysctl fs.inotify.max_user_instances`, on the node/VM, not something this chart
controls).

## Uninstall

```bash
helm uninstall log-stack -n log-stack
kubectl delete namespace log-stack   # helm uninstall does not remove a --create-namespace'd namespace
```
