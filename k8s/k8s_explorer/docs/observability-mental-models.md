# Observability Mental Models — Interview Ready

**These are the diagrams and concepts you should be able to draw and explain from memory in an interview.**

---

## Model 1: The Three Pillars of Observability

```
                    OBSERVABILITY
                         │
            ┌────────────┼────────────┐
            │            │            │
         METRICS        LOGS         TRACES
            │            │            │
     "What changed?"  "Why changed?" "Where was time?"
            │            │            │
         Numeric       Text/JSON      Spans
        Time series    Events       Request path
            │            │            │
         Counter       Level        Latency
         Gauge        Fields       Service calls
       Histogram   Structured     Dependencies
```

**Explain at interview:**
- "Metrics tell me *that* something happened"
- "Logs tell me *why*"
- "Traces tell me *where* the time went across services"
- "I use all three to diagnose production incidents"

---

## Model 2: The Observability Stack on Kubernetes

```
┌─────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Application │  │   Application│  │  Application│  (Pods)    │
│  │  Container   │  │   Container  │  │   Container │           │
│  │              │  │              │  │              │           │
│  │ logs stdout  │  │ logs stdout  │  │  logs stdout│           │
│  │ /metrics     │  │  /metrics    │  │  /metrics   │           │
│  │ OTEL spans   │  │  OTEL spans  │  │ OTEL spans  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│      │                  │                  │                    │
│      └──────────────────┼──────────────────┘                    │
│                         │                                       │
│         ┌───────────────┼───────────────┐                       │
│         │               │               │                       │
│      Kubelet        Kubelet           Kubelet                   │
│    (on each node)   (on each node)   (on each node)             │
│         │               │               │                       │
│    ┌────┴────┐      ┌────┴────┐      ┌────┴────┐              │
│    │ cAdvisor │      │ cAdvisor│      │ cAdvisor│              │
│    │ (metrics)│      │(metrics)│      │(metrics)│              │
│    └────┬────┘      └────┬────┘      └────┬────┘              │
│         │                │                │                    │
│    ┌────┴────────────────┴────────────────┴───┐                │
│    │  node-exporter (on each node)            │                │
│    │  → exports node-level metrics            │                │
│    └────┬────────────────────────────────────┘                │
│         │                                                       │
│  ┌──────┴─────────────────────────────────────┐               │
│  │  kube-state-metrics (cluster-wide)         │               │
│  │  → K8s object status (Pod, Deployment...)  │               │
│  └──────┬─────────────────────────────────────┘               │
│         │                                                       │
│  ┌──────┴──────────────────────────────────────┐              │
│  │  Log collection (Promtail / Fluent Bit)     │              │
│  │  (DaemonSet — one per node)                 │              │
│  │  → reads /var/log/containers/               │              │
│  │  → parses runtime envelope (docker JSON)    │              │
│  │  → attaches labels (namespace, pod, node)   │              │
│  └──────┬──────────────────────────────────────┘              │
│         │                                                       │
│    ┌────┴──────────────────────────────────────┐              │
│    │  OTEL Collector (Deployment or Agent)     │              │
│    │  → receives spans from SDKs               │              │
│    │  → batches and exports                    │              │
│    └────┬──────────────────────────────────────┘              │
│         │                                                       │
└─────────┼───────────────────────────────────────────────────────┘
          │
    ┌─────┴────────────────┬──────────────────┬──────────────────┐
    │                      │                  │                  │
    ▼                      ▼                  ▼                  ▼
┌──────────┐        ┌──────────┐       ┌──────────┐        ┌──────────┐
│Prometheus│        │   Loki   │       │ Tempo/   │        │  Jaeger  │
│ (metrics)│        │  (logs)  │       │ Jaeger   │        │ (traces) │
│          │        │          │       │ (traces) │        │          │
│Time-     │        │Label-    │       │Trace     │        │Request   │
│series DB │        │indexed   │       │block DB  │        │path DB   │
│(EBS PVC) │        │chunk store       │(S3)      │        │(S3)      │
│          │        │(S3)      │       │          │        │          │
└────┬─────┘        └────┬─────┘       └────┬─────┘        └────┬─────┘
     │                   │                   │                  │
     └───────────────────┼───────────────────┼──────────────────┘
                         │
                         ▼
                    ┌─────────────┐
                    │  Grafana    │
                    │  Dashboards │
                    │  Alerts     │
                    │  Explore    │
                    └─────────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
            ▼            ▼            ▼
        ┌────────┐  ┌────────┐  ┌──────────┐
        │Slack   │  │ Email  │  │PagerDuty │
        │        │  │        │  │          │
        └────────┘  └────────┘  └──────────┘
```

**Explain at interview:**
1. "Applications run in pods; they log to stdout and expose `/metrics` endpoints"
2. "Kubelet and system agents (cAdvisor, node-exporter, kube-state-metrics) expose infrastructure metrics"
3. "Log shippers (Promtail, Fluent Bit) read logs from the node filesystem and forward to Loki"
4. "Prometheus scrapes metrics endpoints every 15-30 seconds"
5. "OTEL SDK in the app sends traces to a collector; collector batches and forwards to a backend (Tempo/Jaeger)"
6. "All three backends are queried by Grafana, which is the single pane of glass"

---

## Model 3: Incident Diagnosis Flow

```
INCIDENT: "The service is slow"
    │
    ▼
┌──────────────────────────────────────────┐
│ STEP 1: Check METRICS (Prometheus)       │
├──────────────────────────────────────────┤
│ ├─ Request rate: is traffic up?          │
│ ├─ CPU: is pod maxed out?                │
│ ├─ Memory: climbing or stable?           │
│ ├─ Network I/O: spikes?                  │
│ └─ Pod restarts: incrementing?           │
└──────────────────────────────────────────┘
    │
    ├─ High CPU + high latency?
    │  └─ → Go to LOGS
    │
    ├─ Low CPU + high latency?
    │  └─ → Something blocking (I/O, lock, network)
    │
    ├─ Memory growing?
    │  └─ → Potential leak, check LOGS for allocation patterns
    │
    └─ High restart rate?
       └─ → Pod crashing, check LOGS
    │
    ▼
┌──────────────────────────────────────────┐
│ STEP 2: Check LOGS (Loki)                │
├──────────────────────────────────────────┤
│ ├─ Filter by level=ERROR                 │
│ ├─ Search for "timeout", "unavailable"   │
│ ├─ Check status codes (500, 503, etc.)   │
│ ├─ Look for stack traces                 │
│ └─ Correlation/request IDs               │
└──────────────────────────────────────────┘
    │
    ├─ Database errors?
    │  └─ → DB is slow or down
    │
    ├─ Queue timeout?
    │  └─ → Message broker is backed up
    │
    ├─ External service timeout?
    │  └─ → Dependency is slow
    │
    └─ Application error?
       └─ → Go to TRACES
    │
    ▼
┌──────────────────────────────────────────┐
│ STEP 3: Check TRACES (Tempo/Jaeger)      │
├──────────────────────────────────────────┤
│ ├─ Single request trace: where is time?  │
│ ├─ DB query span: X ms                   │
│ ├─ Cache hit/miss: Y ms                  │
│ ├─ External call: Z ms                   │
│ └─ Total latency: X + Y + Z              │
└──────────────────────────────────────────┘
    │
    ├─ Most time in DB?
    │  └─ → DB optimization, indexing, connection pool
    │
    ├─ Most time in cache?
    │  └─ → Cache configuration, eviction policy
    │
    └─ Most time in external service?
       └─ → That service's problem, escalate
    │
    ▼
┌──────────────────────────────────────────┐
│ STEP 4: Check KUBERNETES (Events)        │
├──────────────────────────────────────────┤
│ ├─ kubectl describe node                 │
│ ├─ kubectl describe pod                  │
│ ├─ kubectl get events                    │
│ ├─ Resource limits hit?                  │
│ └─ Node pressure (disk, memory, CPU)?    │
└──────────────────────────────────────────┘
    │
    ├─ CPU throttling?
    │  └─ → Increase CPU limit or increase node capacity
    │
    ├─ OOMKilled?
    │  └─ → Memory leak or limit too low
    │
    └─ Pending pod?
       └─ → Not enough cluster resources
    │
    ▼
ROOT CAUSE FOUND ✓
→ Take action → monitor recovery
```

---

## Model 4: The Metrics You Need to Know

```
┌──────────────────────────────────────────────────────────────┐
│           PROMETHEUS METRICS YOU SHOULD KNOW                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ APPLICATION METRICS (from /metrics endpoint)                │
│ ├─ counter_requests_total                                   │
│ │  └─ Use: alerts on "too many errors", request rate       │
│ ├─ gauge_active_connections                                │
│ │  └─ Use: understand load, connection pool saturation     │
│ └─ histogram_request_duration_seconds                       │
│    └─ Use: latency percentiles (p50, p95, p99)             │
│                                                              │
│ KUBERNETES / INFRASTRUCTURE METRICS                         │
│ ├─ container_cpu_usage_seconds_total                       │
│ │  └─ CPU consumed by pod, rate it                         │
│ ├─ container_memory_usage_bytes                            │
│ │  └─ Current memory, compare to limit                     │
│ ├─ container_memory_limit_bytes                            │
│ │  └─ Memory limit configured on pod                       │
│ ├─ kube_pod_container_status_restarts_total                │
│ │  └─ Restart counter, alert if incrementing               │
│ ├─ kube_pod_status_phase                                   │
│ │  └─ Pod phase (Running, Pending, Failed, etc.)           │
│ ├─ container_fs_usage_bytes                                │
│ │  └─ Disk usage in container                              │
│ ├─ node_load1                                              │
│ │  └─ Node load average                                    │
│ ├─ up                                                       │
│ │  └─ "Is this scrape target responding?" (1=yes, 0=no)   │
│ └─ scrape_duration_seconds                                 │
│    └─ How long did the scrape take?                        │
│                                                              │
│ WHAT TO ALERT ON                                           │
│ ├─ High error rate: ratio of 5xx to total requests        │
│ ├─ High latency: p99 > threshold                           │
│ ├─ High CPU: rate(...) > 0.80 for 5m                       │
│ ├─ High memory: usage > limit * 0.90 for 2m                │
│ ├─ Pod restarts: restarts_total increasing                │
│ ├─ Pod down: up == 0                                       │
│ ├─ Scrape failure: up == 0 OR scrape_duration > 30s        │
│ └─ Disk full: fs_usage > 85% of capacity                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Model 5: LogQL (Loki Query Language)

```
┌─────────────────────────────────────────────────────────────┐
│           LOGQL QUERY BUILDING BLOCKS                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ BASIC: Select logs by label                               │
│ ├─ {app="my-app"}                                         │
│ │  └─ All logs from the app named "my-app"               │
│ ├─ {namespace="prod", severity="ERROR"}                  │
│ │  └─ ERROR logs in prod namespace                       │
│ └─ {job=~"api.*"}  (regex)                                │
│    └─ All jobs starting with "api"                       │
│                                                             │
│ FILTER: Lines containing text                             │
│ ├─ {app="api"} |= "error"                                │
│ │  └─ Lines containing the word "error"                  │
│ ├─ {app="api"} != "health_check"                          │
│ │  └─ Lines NOT containing "health_check"                │
│ └─ {app="api"} |~ "ERROR|FATAL"  (regex)                 │
│    └─ Lines matching pattern ERROR or FATAL              │
│                                                             │
│ PARSE: Extract JSON fields                                │
│ ├─ {app="api"} | json                                    │
│ │  └─ Parse JSON, flattens nested as field_name          │
│ └─ {app="api"} | json | level="ERROR"                    │
│    └─ Parsed JSON, then filter on level field            │
│                                                             │
│ AGGREGATE: Count/sum/rate                                 │
│ ├─ count_over_time({app="api"} [5m])                     │
│ │  └─ Total log lines in last 5 min                      │
│ ├─ sum(count_over_time(...) [5m])                         │
│ │  └─ Total count (useful when multiple pods)            │
│ ├─ rate({app="api"}[1m])                                 │
│ │  └─ Log lines per second (rate of logs)                │
│ └─ sum by (status) (count_over_time(...) [5m])           │
│    └─ Count grouped by status field                      │
│                                                             │
│ COMMON QUERIES                                            │
│ ├─ {app="api"} | json | level="ERROR"                    │
│ │  └─ All ERROR logs (parsed JSON)                       │
│ ├─ {app="api"} | json | status_code=~"5.."               │
│ │  └─ All server errors (5xx)                            │
│ ├─ {app="api"} | json | latency_ms > 1000                │
│ │  └─ Requests taking > 1 second                         │
│ ├─ sum(rate({app="api"} | json [1m])) by (level)        │
│ │  └─ Request rate broken down by log level              │
│ └─ count_over_time({app="api"} |= "error" [5m])          │
│    └─ Total error lines in last 5 minutes                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Model 6: The Alert Pipeline

```
┌───────────────────────┐
│  Prometheus Alert Rule│  (e.g., CPU > 80% for 5m)
└───────────┬───────────┘
            │
            ├─ Rule evaluates every 15s
            ├─ IF condition true FOR 5m
            │
            ▼
┌───────────────────────────────────────────┐
│ Alert fires (state=FIRING)                │
│ ├─ Labels: severity=critical, service=api│
│ ├─ Annotations: summary, description      │
│ └─ Timestamp                              │
└───────────┬───────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────┐
│ Alertmanager receives alert               │
│ ├─ Deduplicates (same alert, multiple pods)
│ ├─ Groups by labels                       │
│ ├─ Applies routing rules                  │
│ │  └─ If severity=critical → send to page │
│ │  └─ If severity=warning → send to Slack │
│ └─ (Can silence alerts manually)          │
└───────────┬───────────────────────────────┘
            │
            ▼
        ┌───────────────────┐
        │ Notification      │
        │ ├─ Slack message  │
        │ ├─ Email          │
        │ ├─ PagerDuty call │
        │ └─ SMS/voice      │
        └───────────────────┘
            │
            ▼
        On-call engineer responds
        Logs into cluster, investigates
        (using the diagnosis flow from Model 3)
```

---

## Interview Script Template

**Use this structure when asked about observability:**

1. **Clarify scope:** "Are you asking about metrics, logs, traces, or the full stack?"

2. **Draw the stack:** (use Model 2) "Applications run on Kubernetes. Prometheus scrapes metrics, logs ship via Promtail to Loki, traces go via OTEL SDK to Tempo. Grafana is the UI."

3. **Explain the pillars:** (use Model 1) "Metrics tell me *that* something changed, logs tell me *why*, traces tell me *where* the time went. All three are needed for complete observability."

4. **Incident diagnosis:** (use Model 3) "When there's an incident, I follow a top-down approach: check metrics first to see what changed, then logs to understand why, then traces for cross-service latency, then K8s events if it's infrastructure."

5. **Example:** "If latency doubles, I'd check: Is CPU maxed? Is request rate up? If CPU is low but latency is high, something's blocking me (I/O, lock, network). I'd then check logs for errors or timeouts."

6. **Tradeoffs:** "We chose Prometheus + Grafana + Loki because it's self-hosted, portable, and works everywhere. Cost is operational (managing the stack), but it scales and isn't vendor-locked."

---

## Quick Decision Tree

**"Which tool should I use?"**

```
Do I need to...
│
├─ Alert on a numeric threshold?
│  └─ → Prometheus (metrics) + Alertmanager
│
├─ Find all ERROR logs in the last hour?
│  └─ → Loki (logs) + LogQL query
│
├─ Understand latency across services?
│  └─ → Tempo (traces) + trace UI
│
├─ Check if a pod crashed?
│  └─ → Prometheus (pod restart counter) + kubectl events
│
├─ Debug a specific user's request?
│  └─ → Logs (correlation ID) + traces (if available)
│
├─ Is this really a problem or false alarm?
│  └─ → Logs (context) + node metrics (is the node overcommitted?)
│
└─ Show status to management?
   └─ → Grafana dashboard (metrics + logs together)
```

