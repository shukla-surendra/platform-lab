# trace-stack

A wrapper chart combining two **independent** upstream charts — `tempo` and `grafana`
(unlike `metrics-stack`/`log-stack`, neither bundles the other) — tuned for this repo's
local `minikube` cluster. One `helm install` gives you all three pieces of a tracing
pipeline together:

1. **A demo app** — `ghcr.io/grafana/xk6-client-tracing`, a synthetic trace generator
   (`templates/demo-app-deployment.yaml`), sending a realistic multi-service trace
   (`shop-backend → auth-service → article-service → postgres`, plus a cart-service
   flow) over OTLP/gRPC on a loop. Traces don't exist for free the way logs (any pod's
   stdout) or basic metrics (cAdvisor/kube-state-metrics) do — something has to
   actually emit spans, so this exists purely to have real ones to look at.
2. **Tempo**, receiving them via its built-in OTLP receiver (`:4317` gRPC, `:4318`
   HTTP — on by default in this chart, nothing to enable).
3. **Grafana**, with a Tempo datasource wired up by hand in `values.yaml` (no sidecar
   here — see "Two independent charts" below).

Traces only — no Prometheus, no Loki. For metrics see [`../metrics-stack/`](../metrics-stack/),
for logs [`../log-stack/`](../log-stack/).

## A note on chart provenance

Both `grafana/tempo` and `grafana/grafana` (the charts at `grafana.github.io/helm-charts`)
are **deprecated** — Grafana Labs migrated its Helm chart hosting to
`grafana-community/helm-charts`, with a stated cutoff of 2026-01-30, before this chart
was written. `Chart.yaml` pulls both from the new location instead
(`grafana-community.github.io/helm-charts`) — verified live: the old repo's charts
still install and work, but there's no reason to start a new chart on a deprecated
source when the migrated one already exists. (`metrics-stack`'s `kube-prometheus-stack`
dependency and `log-stack`'s `loki-stack` dependency were **not** re-pointed —
`kube-prometheus-stack` isn't deprecated at all, and `loki-stack`'s replacement on the
new host, `grafana-community/loki`, is a structurally different chart — Loki only, no
bundled Promtail/Grafana — not a drop-in swap. See `log-stack/README.md` for that
tradeoff.)

## Two independent charts, not one bundling the other

`kube-prometheus-stack` bundles Grafana; `loki-stack` bundles Grafana. `tempo` does
**not** bundle Grafana — it's Tempo alone. That changes how this chart has to wire the
datasource: instead of a subchart's own sidecar auto-provisioning it, `values.yaml`'s
`grafana.datasources` block writes the Tempo datasource config directly, with
`{{ .Release.Name }}-tempo` templated in by hand (confirmed the `grafana` chart passes
this block through `tpl`, so that resolves correctly rather than being emitted as
literal Go-template text).

**Two different ports on the same Tempo, easy to swap by mistake:** `:3200` is Tempo's
query HTTP API — what Grafana's datasource `url` points at. `:4317`/`:4318` are the
OTLP receivers — what the demo app's `ENDPOINT` env var points at. Point Grafana at
`:4317` (or the demo app at `:3200`) and neither errors loudly — Grafana's datasource
just fails health checks, or the demo app's OTLP export times out — both structured to
look like "something upstream is being flaky" rather than "wrong port."

## Where this is installed

- **Cluster:** `minikube` profile
- **Namespace:** `trace-stack` (dedicated) — the verified install below actually ran
  in `default`, alongside `metrics-stack` and `log-stack`; see those charts' READMEs
  for why the docs and the actual install can diverge on names.
- **Release name:** `trace-stack`
- **Method:** local chart wrapping `grafana-community/tempo` + `grafana-community/grafana`
  (Helm), not raw manifests/kustomize

## Install

```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo update

helm dependency build .   # first time only; fetches tempo + grafana into charts/

helm install trace-stack . \
  --namespace trace-stack \
  --create-namespace
```

## Upgrade

```bash
helm upgrade --install trace-stack . --namespace trace-stack --create-namespace
```

## Access Grafana

```bash
kubectl get pods -n trace-stack -l app.kubernetes.io/name=grafana
minikube service trace-stack-grafana -n trace-stack --url
# or: kubectl -n trace-stack port-forward svc/trace-stack-grafana 3000:80
```

Login: `admin` / `admin`.

## The demo app, and finding a trace

```bash
kubectl -n trace-stack logs -l app=demo-app,release=trace-stack -f
```

The `release=trace-stack` half of that selector matters as soon as more than one of
these charts share a namespace (they do on this cluster's actual install): `metrics-stack`
and `log-stack` both ship a demo app with the same `app=demo-app` label — see
[`../metrics-stack/README.md`](../metrics-stack/README.md) for a real bug this caused
(a Service routing to the wrong release's pod) before every chart's demo app got a
`release` label added.

In Grafana: **Explore** → **Tempo** → **Search** tab → Service Name = `shop-backend`
(or `auth-service` / `article-service` / `postgres` / `cart-service`) → **Run query**
→ click any trace to see the full span tree. Verified live by pulling one trace
directly from Tempo's API — real multi-service structure, not a flat single span:

```
shop-backend   | list-articles     (root)
shop-backend   | authenticate
shop-backend   | fetch-articles
auth-service   | authenticate
article-service| list-articles
article-service| select-articles
postgres       | query-articles
```

Or query Tempo directly, bypassing Grafana:

```bash
kubectl -n trace-stack port-forward svc/trace-stack-tempo 3200:3200
curl -s "http://localhost:3200/api/search?tags=service.name%3Dshop-backend&limit=3"
```

## Uninstall

```bash
helm uninstall trace-stack -n trace-stack
kubectl delete namespace trace-stack   # helm uninstall does not remove a --create-namespace'd namespace
```
