# Observability Quick Reference — Copy/Paste Commands

Keep this open in a second terminal while you work through the scenarios.

---

## Setup & Deployment

```bash
cd ~/projects/2026/platform-lab/k8s_explorer/rust-api-observability-stack

# First time only
helm dependency build

# Deploy
helm install rsa . -n observability --create-namespace

# Wait for everything to come up
kubectl -n observability get pods -w

# Port-forwards (run in separate terminals)
kubectl -n observability port-forward svc/rsa-grafana 3000:80
kubectl -n observability port-forward svc/rsa-rust-api 8080:8080

# Verify API is up
curl http://localhost:8080/healthz
```

---

## Generate Traffic

```bash
# Burst of logs
curl -X POST 'http://localhost:8080/debug/logstorm?count=100&tag=test'

# Random mixed-level logs (better for dashboards)
curl -X POST 'http://localhost:8080/debug/random-logs'

# Slow requests (test latency)
for i in {1..20}; do 
  curl -s 'http://localhost:8080/delay?seconds=1' &
done
wait

# Proof query (verify log pipeline)
# Run this, then check Grafana for the verify query result
curl -X POST 'http://localhost:8080/debug/logstorm?count=50&tag=proof'
# In Grafana Explore → Loki:
# sum(count_over_time({app="rust-api"} |= "proof" | json [5m]))
```

---

## Kubernetes Commands

```bash
# Restart the app pod
kubectl -n observability delete pod -l app=rust-api

# Check pod status
kubectl -n observability get pods

# Describe pod (shows events + resource limits)
kubectl -n observability describe pod -l app=rust-api

# View logs
kubectl -n observability logs -l app=rust-api --tail=50
kubectl -n observability logs -l app=rust-api --previous  # If pod crashed

# Exec into pod
kubectl -n observability exec -it <pod-name> -- /bin/sh

# Scale deployment
kubectl -n observability scale deployment rsa-rust-api --replicas=3

# Check what's actually running
kubectl -n observability get all
```

---

## Grafana Dashboards (Direct Links)

Assuming you port-forwarded to localhost:3000, and logged in (admin/admin):

```
http://localhost:3000/d/rust-api-health
http://localhost:3000/d/rust-api-logs
http://localhost:3000/explore?datasource=Prometheus
http://localhost:3000/explore?datasource=Loki
```

---

## PromQL Queries (Prometheus)

Paste these into Grafana Explore → Prometheus datasource

```promql
# Pod CPU usage (% of limit)
rate(container_cpu_usage_seconds_total{pod=~"rsa.*", container="rust-api"}[1m])

# Pod memory (bytes)
container_memory_usage_bytes{pod=~"rsa.*", container="rust-api"}

# Memory as percentage of limit
container_memory_usage_bytes{pod=~"rsa.*", container="rust-api"} / container_spec_memory_limit_bytes * 100

# Pod restart count
kube_pod_container_status_restarts_total{pod=~"rsa.*", container="rust-api"}

# Pod up/down status
up{pod=~"rsa.*"}

# CPU throttling (if limited)
rate(container_cpu_cfs_throttled_seconds_total{pod=~"rsa.*"}[5m])
```

---

## LogQL Queries (Loki)

Paste these into Grafana Explore → Loki datasource

```logql
# All logs from rust-api
{app="rust-api"}

# ERROR level only
{app="rust-api"} | json | level="ERROR"

# Specific status code
{app="rust-api"} | json | fields_status="500"

# High latency requests (parse latency field)
{app="rust-api"} | json | fields_latency != ""

# Count errors in last 5m
count_over_time({app="rust-api"} | json | level="ERROR" [5m])

# Request rate (rate of any log line)
rate({app="rust-api"}[1m])

# Status code breakdown
sum by (fields_status) (rate({app="rust-api"} | json [1m]))

# Logs with specific tag
{app="rust-api"} |= "proof"

# Parse JSON and filter
{app="rust-api"} | json | level!="INFO"

# Multi-line (e.g., stack traces)
{app="rust-api"} | json | level="ERROR" | pattern "<_> error: <msg>"
```

---

## Prometheus Alert Rule (Example)

If you see the PrometheusRule template in the Helm chart:

```yaml
# Alert: High CPU
- alert: HighCPU
  expr: rate(container_cpu_usage_seconds_total{pod=~"rsa.*"}[5m]) > 0.80
  for: 5m
  annotations:
    summary: "Pod CPU > 80% for 5 minutes"

# Alert: High memory
- alert: HighMemory
  expr: container_memory_usage_bytes{pod=~"rsa.*"} / container_spec_memory_limit_bytes > 0.90
  for: 2m
  annotations:
    summary: "Pod memory > 90% of limit"

# Alert: Pod crash looping
- alert: CrashLooping
  expr: rate(kube_pod_container_status_restarts_total{pod=~"rsa.*"}[15m]) > 0
  for: 5m
  annotations:
    summary: "Pod is restarting repeatedly"

# Alert: High error rate
- alert: HighErrorRate
  expr: sum(rate({app="rust-api"} | json | level="ERROR" [5m])) > 10
  for: 2m
  annotations:
    summary: "Error rate > 10 errors/sec"
```

---

## Debugging Checklist

**If a dashboard panel is empty:**

1. Verify the data source:
   - Click panel → Edit → check datasource name (should be "Prometheus" or "Loki")
   - Run the query directly in Explore to see if it returns data

2. Verify labels match your pod:
   - `{pod=~"rsa.*"}` assumes pod name starts with "rsa"
   - Check actual pod name: `kubectl -n observability get pods`
   - If pod name is different, update the query

3. Verify data actually exists:
   - In Explore, run: `{pod=~".*"} | count()` (Loki) or `up{}` (Prometheus)
   - Should return non-empty results

**If the API is not responding:**

```bash
# Port-forward is running?
kubectl -n observability port-forward svc/rsa-rust-api 8080:8080

# Pod is actually running?
kubectl -n observability get pods

# Logs show any errors?
kubectl -n observability logs -l app=rust-api

# Try directly from inside cluster
kubectl -n observability run debug --image=curlimages/curl -it --rm -- curl http://rsa-rust-api:8080/healthz
```

**If Prometheus has no metrics:**

```bash
# Metrics endpoint should exist
curl http://localhost:8080/metrics   # (this one doesn't, rust-api has no /metrics)

# But node metrics and pod metrics still come from cAdvisor/kube-state-metrics
# Check if those are scraped:
kubectl -n observability logs -l app.kubernetes.io/name=prometheus | grep "scraped"
```

**If Loki has no logs:**

```bash
# Are logs actually being written to stdout?
kubectl -n observability logs -l app=rust-api

# Is Promtail running?
kubectl -n observability get pods -l app=promtail

# Is Promtail forwarding logs?
kubectl -n observability logs -l app=promtail | grep "sent batch"

# Direct curl to Loki's API
kubectl -n observability port-forward svc/rsa-loki 3100:3100
curl -s 'http://localhost:3100/loki/api/v1/query?query={app="rust-api"}' | jq .
```

---

## Grafana UI Tips

**Create a custom panel (for scenarios):**

1. Dashboard → + (top right) → Panel
2. Set datasource: Prometheus (for metrics) or Loki (for logs)
3. Write your query
4. Set visualization type (Graph, Table, etc.)
5. Save

**Variable dropdowns (for filtering):**

- Dashboard settings → Variables
- Create variable: `{app="$app"}` to filter by app name
- In panels, reference as `$app`

**Set dashboard refresh rate:**

- Top right: Refresh button
- Set to "30s" or "5s" if you want live updates during scenarios

---

## Cleanup

```bash
# Delete the release
helm uninstall rsa -n observability

# Delete the namespace
kubectl delete namespace observability

# Verify it's gone
kubectl get namespaces
```

---

## One-liner incident investigations

```bash
# "My pod crashed, when did it happen?"
kubectl -n observability describe pod -l app=rust-api | grep -A5 "Last State"

# "How many restarts?"
kubectl -n observability get pod -l app=rust-api -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}'

# "What's the most recent error in logs?"
kubectl -n observability logs -l app=rust-api --tail=50 | grep ERROR | tail -1

# "Is the pod in a crash loop?"
kubectl -n observability get events --sort-by='.lastTimestamp' | tail -10

# "What resource limits are set?"
kubectl -n observability get pod -l app=rust-api -o jsonpath='{.items[0].spec.containers[0].resources}'

# "Check if node has pressure"
kubectl describe nodes | grep -A5 "Conditions:"
```

---

## My mental checklist during incidents

1. **Metrics first** → "Did something change?" (CPU, memory, request rate)
2. **Logs second** → "Why did it change?" (errors, status codes, stack traces)
3. **Traces third** → "Where did the time go?" (cross-service latency)
4. **K8s fourth** → "Why is the pod limited?" (resource limits, node pressure, eviction)

Don't jump straight to logs. Metrics tell you *if* there's a problem; logs tell you *why*.

