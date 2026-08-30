# Kubernetes Observability Practice — Today's Walkthrough

**Finish line by tonight:** Deploy a FastAPI/Rust API service on K8s with Prometheus + Grafana + Loki, then walk through incident scenarios until you can diagnose problems without cheat sheets.

**Your existing assets:**
- [`../rust-api-observability-stack/`](../rust-api-observability-stack/) — complete Helm chart, ready to deploy
- `mlops_aiops/docs/observability-on-eks.md` — architecture/tool decisions
- `mlops_aiops/docs/production-logging-guidelines.md` — logging best practices
- `mlops_aiops/docs/observability-terminology.md` — vocabulary

**Don't build anything new today. Deploy the existing chart, break it, and practice diagnosing.**

---

## Part 1: Mental Model (30 min)

### The flow you need to see in your head

```
User Request
    │
    ▼
┌─────────────────────────────────────────┐
│        K8s Cluster                      │
│  ┌─────────────────────────────────┐    │
│  │ FastAPI Pod                     │    │
│  │ ├── logs → stdout               │    │
│  │ ├── /metrics → Prometheus       │    │
│  │ └── request traces → OTEL       │    │
│  └─────────────────────────────────┘    │
│           │      │       │               │
│           │      │       └─ (if added)   │
│  Kubelet  │      │                       │
│  ├─logs→  │      ├─scrape                │
│  │        │      │                       │
│  │    Promtail   Prometheus              │
│  │        │         │                    │
│  ▼        ▼         ▼                    │
│  node-logs  Loki   TSDB                  │
└─────────────────────────────────────────┘
    │         │        │
    │         │        └─ metrics
    │         └─ logs
    └─ (raw node metrics)
        │         │        │
        ▼         ▼        ▼
┌─────────────────────────────────────────┐
│         Grafana (one pane)              │
│  ├─ Dashboards (Prometheus metrics)     │
│  ├─ Logs panel (Loki queries)           │
│  └─ Alerts (Prometheus rules → Manager) │
└─────────────────────────────────────────┘
```

**Read these, in order (15 min total):**

1. `mlops_aiops/docs/observability-on-eks.md` — sections "Quick answer" + "How it fits together on EKS"
   - **Focus on the diagram.** Read it as three pipelines: metrics, logs, traces.
   - Your question: "Which tool is responsible for *getting the data here*?"
   - Answer: Prometheus scrapes metrics, Promtail ships logs, OTel collectors ship traces.

2. `mlops_aiops/docs/observability-terminology.md` — just the first three sections
   - **You only need:** metric vs log vs trace (the *definition*, not every variant).
   - Counter = "how many total," Gauge = "current value," Histogram = "bucketed distribution"

3. `mlops_aiops/docs/production-logging-guidelines.md` — skim the "What to log" section
   - **You need:** why `print("status=ok")` is bad; why structured JSON is better.

**Mental model checkpoint:** Close these docs. Draw the three pipelines from memory. If you can draw them and label "Prometheus," "Promtail," "Grafana," you've got the model.

---

## Part 2: Deploy and Instrument (45 min)

### Prerequisite: Do you have `minikube` or `kind` running?

```bash
# If not, start it (macOS/Homebrew)
minikube start --cpus=4 --memory=8192 --disk-size=20g

# Verify
kubectl cluster-info
kubectl get nodes
```

### Deploy the Helm chart

```bash
cd ~/projects/2026/platform-lab/k8s_explorer/rust-api-observability-stack

# First time only: fetch dependencies
helm dependency build

# Deploy everything: app + Prometheus + Grafana + Loki
helm install rsa . -n observability --create-namespace

# Wait for pods to come up (should be quick, ~30s)
kubectl -n observability get pods -w
```

When all pods are `Running`:

```bash
# Port-forward Grafana (port 3000)
kubectl -n observability port-forward svc/rsa-grafana 3000:80

# In another terminal: port-forward the API (port 8080)
kubectl -n observability port-forward svc/rsa-rust-api 8080:8080
```

Open:
- **Grafana**: http://localhost:3000 (admin / admin)
- **API**: http://localhost:8080 (should see a landing page with endpoints)

### Generate some traffic

In a third terminal:

```bash
# Feed the log pipeline real logs
curl -X POST 'http://localhost:8080/debug/logstorm?count=100&tag=test-run-1'

# Wait ~5 seconds, then check Grafana:
# - Go to http://localhost:3000
# - Left sidebar → Dashboards → "rust-api — health & requests"
# - Top row should show CPU/Memory metrics, bottom row should show request activity
```

**What you're looking at:**
- **Top row (Prometheus):** Pod CPU, memory, restart count — **infrastructure metrics**
- **Bottom row (Loki):** Request rate, status codes, latency — **application logs queried as metrics**

The logs dashboard:
- Left sidebar → Dashboards → "rust-api — logs"
- Filter by level (ERROR, WARN, INFO) and namespace
- You should see the 100 log lines you just sent

**Checkpoint:** You've deployed a working observability stack. Take a screenshot of both dashboards.

---

## Part 3: Read the Queries (20 min)

**Don't skip this.** You need to see *how* the dashboards work, not just stare at them.

### Click into the health & requests dashboard

Look at the "Request Rate" panel:

- Click the three-dot menu → "Edit"
- You'll see a LogQL query, not a Prometheus one:
  ```
  sum(rate({app="rust-api"} |= "status" | json | fields_status=~".*" [1m]))
  ```
- This is Loki + `json` parsing. It's saying: "From every log line in the `rust-api` app, extract the JSON, find lines with a `status` field, and give me the rate"
- Click outside to close the editor

Look at the "Pod CPU" panel:

- Edit it → you'll see a Prometheus query:
  ```
  rate(container_cpu_usage_seconds_total{pod=~"rsa.*", container="rust-api"}[1m])
  ```
- This is Prometheus `container_*` metrics (from cAdvisor, already scraped on every node)

Look at the logs dashboard's "ERROR by Level" panel:

- Edit → LogQL query:
  ```
  sum by (level) (count_over_time({app="rust-api"} | json | level!="INFO" [5m]))
  ```
- This is "count all JSON logs where level is not INFO, grouped by level"

**Checkpoint:** You understand that:
- Prometheus queries have `container_*` and `node_*` metrics scraped from `/metrics` endpoints
- Loki queries parse JSON from logs and do field-level filtering
- Both feed Grafana dashboards

---

## Part 4: Break It and Diagnose (45 min)

The scenarios below are also scripted — run them straight from
[`examples/observability-scenarios.sh`](examples/observability-scenarios.sh) instead of
copy/pasting if you'd rather trigger them with one command:

```bash
./examples/observability-scenarios.sh high-latency
./examples/observability-scenarios.sh crash-loop
./examples/observability-scenarios.sh all       # all 8 in sequence
```

### Scenario 1: "Why are my API requests slow?"

**Setup:** Introduce latency into the API

```bash
curl -X POST 'http://localhost:8080/debug/random-logs'
```

Then in another terminal, hammer it with requests:

```bash
for i in {1..50}; do 
  curl -s 'http://localhost:8080/delay?seconds=0.5' &
done
wait
```

**Now diagnose in Grafana:**

1. Open the health & requests dashboard
2. Look at the panels: CPU went up? Memory stable? Request rate spiked?
3. Check the Logs dashboard: any ERROR lines? What status codes?
4. Go to Explore (left sidebar) → Select "loki" datasource
5. Query: `{app="rust-api"} | json | fields_latency != ""` (show only log lines that have a latency field)
6. Scan the latency values — are they all showing `X ms`?

**What you're practicing:**
- Metrics tell you *that something changed* (CPU, request rate)
- Logs tell you *why* (error messages, status codes, specific request details)

**Incident question:** "Request latency doubled. Is it the API code, or is Kubernetes throttling it?"
- Answer: Look at CPU gauge. If CPU is at 100% AND request latency went up, it's the API code (or Prometheus scrape load). If CPU is 10% and latency is high, the pod might be waiting on something external (database, queue, etc.).

---

### Scenario 2: "Pod crashed. When did it happen?"

**Setup:** Force a pod restart

```bash
kubectl -n observability delete pod -l app=rust-api
```

Watch Grafana's health & requests dashboard:
- **Pod restarts counter** (top row, right) — it went from 0 → 1
- **Request rate** (bottom row, left) — dipped to zero for ~10s during the restart
- **Logs dashboard** — you'll see heartbeat lines stop, then resume

**What you're looking at:**
- **Metric (restart counter):** Fast, tells you *it happened*
- **Logs (heartbeat + request lines):** Tell you *when* it happened and *why* (if there's an error before it crashed)

**Incident question:** "My pod is crashing in a loop. What happened?"
- Answer: Check `kubectl logs` for the last exit message, AND look at the metrics: are restarts incrementing every ~30s? That's the loop. Are logs showing errors before each restart? That's the root cause.

---

### Scenario 3: "Memory is climbing. Is it a leak?"

**Setup:** No setup needed, but let's look at the memory panel.

Open health & requests dashboard → top-right panel is "Memory Usage"

**What to look for:**
1. Is the line flat? Then it's not a leak.
2. Does it climb steadily over minutes? Then there's a leak (or traffic is genuinely growing).
3. Does it spike then plateau? That's normal JVM / Rust allocation patterns.

To simulate a memory climb (on the actual API):

```bash
# This endpoint would allocate large objects in a real app
# For now, just observe the normal pattern:
curl 'http://localhost:8080/healthz' -v
```

Then in Grafana Explore → prometheus data source:

```
container_memory_usage_bytes{pod=~"rsa.*", container="rust-api"}
```

You're looking at the actual bytes used by the container.

**Incident question:** "Memory usage hit the pod's limit. What's consuming it?"
- Answer (the full answer, which you'll build toward): Check metrics first (is memory actually climbing?). If yes, check the application logs for allocation patterns. If this is a real app with a `/metrics` endpoint, also check Prometheus metrics like `go_memstats_heap_alloc_bytes` (Go) or `py_process_resident_memory_bytes` (Python) — application-level memory counters are more granular than container metrics.

---

## Part 5: Incident Scenarios (30 min)

### Scenario A: Service degradation (from your hypothetical)

**Setup:**

```bash
# Simulate a storm of requests (without the actual simulation, just imagine it)
curl -X POST 'http://localhost:8080/debug/random-logs'
```

**Your job:** Walk through this aloud without notes:

> "The OCR service is processing 10,000 documents/hour. Suddenly processing latency doubles. Walk me through how you would investigate it."

**Your answer should mention, in order:**

1. **Metrics first (Prometheus):**
   - "I check the request-rate graph. Is traffic actually doubled, or same?"
   - "I check CPU/memory. If CPU is maxed, the pod is bottlenecked. If CPU is low, something else is blocking (I/O, lock contention, external service)."
   - "If memory is climbing, there's a leak or a queue building up."

2. **Logs second (Loki):**
   - "I query for ERROR level logs in the last 5 minutes. Are there failures?"
   - "I check the request status codes. Are they 200, or are 500s spiking?"
   - "I look for stack traces or specific error messages that narrow it down."

3. **If still unclear, trace third (OTEL, if implemented):**
   - "If there's cross-service latency, I trace a single request. Did it spend 2s in the DB, 500ms in a cache miss, etc.?"

4. **K8s infrastructure fourth:**
   - "Is the pod resource-limited? Check `kubectl describe pod` — does it show CPU throttling, OOMKilled events, or node pressure?"
   - "Are other pods on the node fighting for resources?"

**You're demonstrating:** Methodical top-down diagnosis, not random dashboard clicking.

---

### Scenario B: Pod crash loop

```bash
# Simulate by injecting bad config
kubectl -n observability set env deployment/rsa-rust-api RUST_LOG="invalid-log-level"
```

**Your job:** Answer (aloud, 2 min):

> "A pod keeps restarting. It restarts, stays up for ~3 seconds, then crashes. How do you find out why?"

**Expected answer:**

1. "First, I check the metrics dashboard to confirm the restart pattern."
2. "I get logs: `kubectl logs -n observability -l app=rust-api --tail=50`"
3. "If the logs are empty or unhelpful, I check the previous container's logs: `kubectl logs -n observability -l app=rust-api --previous`"
4. "If both are empty, I check events: `kubectl describe pod -n observability -l app=rust-api`"
5. "The events will show why the container exited (OOMKilled, exit code 1, etc.)"

---

### Scenario C: Silent failure

```bash
# Simulate an endpoint that fails silently (high status code but no logs)
# For now, just query for non-2xx status codes:
```

In Grafana Explore → loki data source:

```
{app="rust-api"} | json | fields_status!="200"
```

This shows all requests that didn't return 200. In a real app, you'd see things like 503, 500, etc.

**Your job:** Answer (aloud, 2 min):

> "Users report that some requests are failing, but you don't see any errors in the app logs. Where do you look next?"

**Expected answer:**

1. "I check if the failures are logged at all. Do the log lines exist, or is there just silence?"
2. "If they're logged but not ERROR level, I might need to lower the log level temporarily."
3. "If there are log lines, I check the `error` or `exception` field in the JSON."
4. "If there's really no error info, I check the HTTP status code returned — 5xx means server-side, 4xx might be client-side or a bad request."
5. "If I still have no detail, I trace a single request (if tracing is set up)."

---

## Part 6: FastAPI → Rust → Python (Choose your real app)

Once you're comfortable with the Rust stack, you have two paths:

### Option A: Adapt the Rust chart to Python/FastAPI

The existing chart is templated. You'd:

1. Change the image to a Python/FastAPI app
2. Ensure the app writes JSON logs to stdout (same pattern as the Rust app)
3. Re-deploy — everything else stays the same (Prometheus, Grafana, Loki, Promtail)

This is **low-effort** because the observability plumbing doesn't change.

### Option B: Build a Python/FastAPI app with OpenTelemetry

If you want to add distributed tracing (traces, not just logs/metrics):

1. Instrument the FastAPI app with OpenTelemetry SDK
2. Deploy an OTel Collector to receive spans
3. Point the collector at Tempo (trace backend)
4. Add Tempo as a Grafana datasource

The [`rust-api-observability-stack`](../rust-api-observability-stack/) doesn't include Tempo yet, but the docs on OTEL are in `mlops_aiops/docs/observability-otel-collector-and-datadog.md`.

---

## Finishing the day: The test

**You should be able to answer all of these without notes:**

1. **Metrics:** "Prometheus is scraping pod CPU usage. Where does that metric come from?" (Answer: cAdvisor, running in kubelet, exposes `/metrics`, Prometheus scrapes it)

2. **Logs:** "Why is `RUST_LOG=info` better than `print("status=ok")`?" (Answer: structured JSON lets you filter by field; print() goes to unindexed text)

3. **Traces:** "I want to know if my request spent more time in the database or the cache. What tool do I use?" (Answer: distributed tracing / OpenTelemetry, not metrics or logs)

4. **K8s:** "A pod is using 90% of its memory limit. How do I know if it's a real leak or just normal allocation?" (Answer: Check if the line is climbing over time; if flat or sawtooth pattern, it's normal. Also check `/metrics` if the app exports memory stats.)

5. **Alerting:** "Write a Prometheus alert rule that fires when CPU is > 80% for 5 minutes." (Answer: `ALERT HighCPU IF rate(container_cpu_usage_seconds_total[5m]) > 0.80 FOR 5m`)

6. **Incident:** "Your service is 30% slower. Walk me through the diagnosis." (Answer: Check metrics → logs → traces → K8s events, in that order, stopping when you find the root cause)

---

## Cleanup

When you're done:

```bash
helm uninstall rsa -n observability
kubectl delete namespace observability
```

---

## Resources you've already got

- Full architecture guide: `mlops_aiops/docs/observability-on-eks.md`
- Terminology: `mlops_aiops/docs/observability-terminology.md`
- Production logging: `mlops_aiops/docs/production-logging-guidelines.md`
- Working Helm chart: [`../rust-api-observability-stack/`](../rust-api-observability-stack/)
- Public Docker image: `surendrashukla29/rust-api:1.0.0` (no build step needed)

---

## Time budget

| Part | Time | Activity |
|---|---|---|
| 1. Mental Model | 30 min | Read docs, draw the flow, verify you understand the three pipelines |
| 2. Deploy | 45 min | `helm install`, port-forward, generate traffic, check dashboards |
| 3. Query Deep Dive | 20 min | Click into panels, read LogQL + PromQL, understand data sources |
| 4. Break & Diagnose | 45 min | 3 scenarios (latency, crash, memory), practice diagnosis |
| 5. Incident Scripts | 30 min | Answer 3 scenarios aloud, refine your mental model |
| 6. Closing | 10 min | Verify you can answer all 6 test questions |
| **Total** | **~3 hours** | |

---

## Interview-level understanding

By the end, you should be able to:

1. **Draw the observability stack from memory** (K8s → data sources → storage → Grafana)
2. **Explain why each tool exists** (Prometheus for metrics, Loki for logs, OTel for traces)
3. **Diagnose a production incident** using metrics + logs + K8s events (without cheat sheets)
4. **Write a PromQL query** that would alert on a real problem
5. **Understand the tradeoffs** (self-hosted vs. CloudWatch vs. SaaS cost)
6. **Connect this to your EKS experience** (you know K8s + AWS, this is the observability layer on top)

That's interview-ready for Google/Stripe/Amazon roles that touch infrastructure.

