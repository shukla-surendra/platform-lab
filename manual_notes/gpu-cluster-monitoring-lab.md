# Lab: Monitor a GPU Cluster with Prometheus

A practical, end-to-end lab for monitoring a Kubernetes GPU cluster with Prometheus,
Grafana dashboards, and basic alerts. You'll deploy NVIDIA's DCGM Exporter to expose
GPU metrics, scrape them with Prometheus, visualize them in Grafana, and add alert
rules on top.

*(Refactored from a raw "Lab 112" note — original numbered steps preserved, formatting
and a few hard-won caveats added. See
[`../k8s_observability/metrics-stack/`](../k8s_observability/metrics-stack/) for this
exact `kube-prometheus-stack` chart already deployed and verified live in this repo,
and
[`../mlops_aiops/docs/observability-gpu-monitoring-dcgm-triton.md`](../mlops_aiops/docs/observability-gpu-monitoring-dcgm-triton.md)
for the DCGM/Prometheus mental model this lab puts into practice.)*

## 0. What you'll build

```text
GPU Nodes
   │
   ▼
DCGM Exporter (DaemonSet)  ── exposes GPU metrics on :9400
   │
   ▼
Prometheus  ── scrapes DCGM Exporter + node-exporter + kube-state-metrics
   │
   ├──▶ Grafana        ── dashboards
   └──▶ Alertmanager   ── routes alert rules (bundled with the stack)
```

- GPU nodes each run **DCGM Exporter** as a DaemonSet, exposing GPU metrics on port
  `9400`.
- **Prometheus** scrapes those metrics alongside the standard cluster metrics
  (node-exporter for host CPU/memory, kube-state-metrics for Kubernetes object state).
- **Grafana** visualizes everything.
- **Alertmanager** (bundled with the stack) routes the alert rules this lab adds.

## 1. Prerequisites

- A Kubernetes cluster with at least one NVIDIA GPU node (drivers installed).
- `kubectl` and `helm` configured for the cluster.
- The NVIDIA device plugin installed on GPU nodes (commonly required for the
  scheduler to see GPUs as an allocatable resource at all).
- Cluster-admin privileges.

If the cluster isn't GPU-ready yet, install the NVIDIA device plugin first:

```bash
helm repo add nvidia https://nvidia.github.io/k8s-device-plugin
helm repo update

kubectl create ns gpu-operator --dry-run=client -o yaml | kubectl apply -f -
helm install nvidia-device-plugin nvidia/k8s-device-plugin -n gpu-operator
```

## 2. Create a dedicated namespace

Keep everything from this lab in one place, so it can be inspected and torn down as a
unit:

```bash
kubectl create namespace monitoring
```

## 3. Install Prometheus, Grafana, and friends (`kube-prometheus-stack`)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring
```

This one chart deploys Prometheus, Grafana, Alertmanager, node-exporter, and
kube-state-metrics together. **Why this route:** it's the fastest way to a
production-worthy Prometheus stack that also ships the CRDs (`ServiceMonitor`,
`PrometheusRule`) used in steps 6 and 10 — those CRDs are what make scraping and
alerting *declarative* (an object in the cluster) rather than something you'd
otherwise hand-edit into Prometheus's own config file.

## 4. Label the GPU nodes

Schedule the DCGM Exporter DaemonSet only where GPUs actually exist:

```bash
# Replace <node-name> with each GPU node's actual name
kubectl label nodes <node-name> gpu=true
```

**Why:** without a node selector, the DaemonSet would attempt to schedule a
GPU-monitoring pod onto every node in the cluster, including ones with no GPU to
monitor. If the cluster already has GPU labels from somewhere else (e.g. Node Feature
Discovery), use those instead and adjust the `nodeSelector` in step 5's YAML to match.

## 5. Deploy the NVIDIA DCGM Exporter (DaemonSet)

This exposes per-node, per-GPU metrics — utilization, memory, temperature, power, ECC
errors, clocks.

`dcgm-exporter.yaml`:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: monitoring
  labels:
    app: dcgm-exporter
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
    spec:
      nodeSelector:
        gpu: "true"
      hostPID: false
      hostNetwork: false
      tolerations:
        - effect: NoSchedule
          operator: Exists
        - effect: NoExecute
          operator: Exists
      containers:
        - name: dcgm-exporter
          # Pin to a known-good tag in real use — ':latest' is shown here only for
          # simplicity, and means an unannounced upstream change can silently alter
          # what this DaemonSet actually runs on the next pod restart.
          image: nvcr.io/nvidia/k8s/dcgm-exporter:latest
          imagePullPolicy: IfNotPresent
          ports:
            - name: metrics
              containerPort: 9400
          securityContext:
            privileged: true
          env:
            - name: DCGM_EXPORTER_KUBERNETES
              value: "true"
          volumeMounts:
            # Provides per-pod GPU accounting when available (useful with MIG)
            - name: pod-resources
              mountPath: /var/lib/kubelet/pod-resources
              readOnly: true
      volumes:
        - name: pod-resources
          hostPath:
            path: /var/lib/kubelet/pod-resources
            type: Directory
---
apiVersion: v1
kind: Service
metadata:
  name: dcgm-exporter
  namespace: monitoring
  labels:
    app: dcgm-exporter
spec:
  clusterIP: None  # headless — see "why" below
  selector:
    app: dcgm-exporter
  ports:
    - name: metrics
      port: 9400
      targetPort: metrics
```

Apply it:

```bash
kubectl apply -f dcgm-exporter.yaml
kubectl -n monitoring get pods -l app=dcgm-exporter -o wide
```

**Why a headless Service (`clusterIP: None`)?** A normal `ClusterIP` Service would
give Prometheus one virtual IP that kube-proxy load-balances across every DCGM
Exporter pod — Prometheus would see *one* scrape target and get whichever pod's data
happened to answer that request, not all of them. Headless means Prometheus discovers
each individual DaemonSet pod as its own scrape target instead, so every node's GPU
metrics are actually collected — not just one node's, sampled at random.

## 6. Tell Prometheus to scrape it (`ServiceMonitor`)

`dcgm-servicemonitor.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dcgm-exporter
  namespace: monitoring
  labels:
    release: monitoring    # must match the Helm release name from step 3
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  namespaceSelector:
    matchNames: ["monitoring"]
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
```

```bash
kubectl apply -f dcgm-servicemonitor.yaml
```

**Why a `ServiceMonitor`, and why the `release: monitoring` label specifically:**
`kube-prometheus-stack` watches for these CRDs and dynamically rewrites Prometheus's
scrape config as they're added — no manual `prometheus.yml` editing. But by default
the chart's Prometheus is configured to select *only* `ServiceMonitor` objects
carrying its own Helm release name as a `release` label (this is
`serviceMonitorSelectorNilUsesHelmValues: true`, the chart's own default) — a
`ServiceMonitor` missing that label is silently ignored: Prometheus stays healthy, the
target simply never appears, with no error surfaced anywhere. Since step 3 installed
the chart under the release name `monitoring`, `release: monitoring` here is what
satisfies that selector — change one, and the other has to change with it.

**No app to instrument required beyond this:** unlike an application `/metrics`
endpoint you'd have to add to your own code, DCGM Exporter already speaks
Prometheus's format natively — the `ServiceMonitor` is the only wiring needed.

## 7. Sanity-check: see the raw GPU metrics

Port-forward to any DCGM Exporter pod and curl its `/metrics` endpoint directly —
bypassing Prometheus entirely, to confirm the exporter itself is producing real data
before troubleshooting anything further up the chain:

```bash
POD=$(kubectl -n monitoring get pod -l app=dcgm-exporter -o jsonpath='{.items[0].metadata.name}')
kubectl -n monitoring port-forward pod/$POD 9400:9400
# in another terminal:
curl -s localhost:9400/metrics | head -n 40
```

Expect to see metrics like `DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_GPU_TEMP`,
`DCGM_FI_DEV_FB_USED`, each labeled with GPU index, GPU UUID, MIG instance (if
applicable), and node.

## 8. Open the Prometheus UI and run some PromQL

Find the Prometheus Service name:

```bash
kubectl -n monitoring get svc | grep prometheus
```

> **A real gotcha, worth knowing before you hardcode a Service name into a script:**
> `kube-prometheus-stack`'s own Prometheus Service name is built from the Helm release
> name and gets truncated by the chart's fullname template to fit Kubernetes' 63-char
> DNS-label limit — the exact truncation point depends on how long the release name
> is, so `monitoring-kube-prometheus-prometheus` (the "obvious" name) may or may not
> be exactly right depending on chart version and release name. The **reliable** name
> to port-forward to instead is `prometheus-operated` — a fixed Service the
> Prometheus Operator itself creates directly, independent of the Helm release name
> entirely. Verified against a real install of this same chart in
> [`k8s_observability/metrics-stack/README.md`](../k8s_observability/metrics-stack/README.md).

```bash
kubectl -n monitoring port-forward svc/prometheus-operated 9090:9090
# if that Service doesn't exist on your chart version, fall back to whatever
# `kubectl get svc | grep prometheus` actually printed above
```

Open `http://localhost:9090` → **Graph**, and try these queries (adjust label names if
your DCGM Exporter build uses different metric prefixes — see the note in step 9):

```promql
# GPU utilization (%)
avg by (instance, gpu) (DCGM_FI_DEV_GPU_UTIL)
```

```promql
# Memory utilization (%)
100 * (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL)
```

```promql
# GPU temperature (°C)
max by (instance, gpu) (DCGM_FI_DEV_GPU_TEMP)
```

```promql
# Power draw (W)
avg by (instance, gpu) (DCGM_FI_DEV_POWER_USAGE)
```

If these return nothing, check:

- The `ServiceMonitor`'s `metadata.labels.release` actually matches the Helm release
  name (`monitoring`, from step 3) — this is the single most common reason a
  `ServiceMonitor` is silently ignored, per the explanation in step 6.
- The DCGM Exporter Service's port name (`metrics`) matches the `ServiceMonitor`'s
  `endpoints[].port` value exactly — these are matched by *name*, not by number.

## 9. Access Grafana and build a GPU dashboard

Get the Grafana admin password (decoding the Secret the chart created) and
port-forward:

```bash
kubectl -n monitoring get secret monitoring-grafana -o jsonpath="{.data.admin-password}" | base64 -d; echo

kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80
```

Open `http://localhost:3000`, log in as `admin` with the password above.

Build a quick GPU dashboard: **new Dashboard → Add Panel**, and use the same four
queries from step 8, one per panel:

| Panel | Query |
|---|---|
| GPU Util (%) | `avg by (instance, gpu) (DCGM_FI_DEV_GPU_UTIL)` |
| FB Memory (%) | `100 * (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL)` |
| Temperature (°C) | `max by (instance, gpu) (DCGM_FI_DEV_GPU_TEMP)` |
| Power (W) | `avg by (instance, gpu) (DCGM_FI_DEV_POWER_USAGE)` |

Add a repeating variable on `instance` and/or `gpu` if you want per-node/per-GPU
drilldown — one templated panel that repeats per label value, instead of one hardcoded
panel per GPU.

**Note:** some DCGM Exporter builds prefix these metric names differently (e.g.
`nvidia_dcgm_...` instead of `DCGM_FI_DEV_...`). Grafana's query-editor autocomplete
against the live Prometheus datasource is the fastest way to confirm the actual names
in your environment — the `/metrics` output from step 7 is the ground truth, not
whatever a particular guide (including this one) assumes.

## 10. Add alert rules (`PrometheusRule`)

`gpu-alerts.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gpu-alerts
  namespace: monitoring
  labels:
    release: monitoring   # same reason as the ServiceMonitor in step 6
spec:
  groups:
    - name: gpu.rules
      rules:
        - alert: GPUScrapeMissing
          expr: up{job="dcgm-exporter"} == 0
          for: 10m
          labels: { severity: warning }
          annotations:
            summary: "DCGM exporter scrape failing"
            description: "Prometheus cannot scrape DCGM exporter targets for 10m."

        - alert: GPUHighTemperature
          expr: max by (instance, gpu) (DCGM_FI_DEV_GPU_TEMP) > 80
          for: 5m
          labels: { severity: warning }
          annotations:
            summary: "GPU temperature high (>80°C)"
            description: "Instance {{ $labels.instance }} GPU {{ $labels.gpu }} too hot."

        - alert: GPUMemoryPressure
          expr: 100 * (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL) > 90
          for: 10m
          labels: { severity: warning }
          annotations:
            summary: "GPU memory > 90% for 10m"
            description: "Sustained memory pressure on {{ $labels.instance }} GPU {{ $labels.gpu }}."

        - alert: GPUECCErrorsSpike
          expr: rate(DCGM_FI_DEV_ECC_SBE_VOL_TOTAL[5m]) > 0
          for: 5m
          labels: { severity: critical }
          annotations:
            summary: "ECC single-bit errors increasing"
            description: "ECC SBE rate > 0 on {{ $labels.instance }} GPU {{ $labels.gpu }}."
```

```bash
kubectl apply -f gpu-alerts.yaml
```

`up{job="dcgm-exporter"}` in the first rule works because the `job` label Prometheus
attaches defaults to the *Service* name (`dcgm-exporter`, from step 5) when a
`ServiceMonitor` doesn't override it with its own `jobLabel` — worth knowing before
renaming either the Service or this alert expression independently of the other.

**Wire up notifications:** edit Alertmanager's config, either directly in the chart's
Helm values or via the `alertmanager` Secret, to actually route these to Slack, email,
PagerDuty, etc. — without that, alerts fire and sit in Alertmanager's UI, visible but
silent to anyone not actively watching it.

## 11. (Optional) Attribute GPU usage to Pods/Namespaces

Because step 5 mounted `/var/lib/kubelet/pod-resources`, newer DCGM Exporter builds
can label samples with `pod`, `namespace`, and `container` — giving per-tenant
visibility into GPU usage, which matters especially with MIG (Multi-Instance GPU)
where several workloads share one physical GPU. In Grafana, add panels grouped by
`namespace`/`pod` to see *who* is actually using the GPUs, not just how busy the
hardware is in aggregate.

## 12. Troubleshooting checklist

| Symptom | Check |
|---|---|
| **No metrics in Prometheus** | `ServiceMonitor`'s `label release: monitoring` matches the Helm release name; the Service's port name is `metrics` and matches the `ServiceMonitor`'s `endpoints[].port` exactly (see step 6). |
| **Exporter `CrashLoopBackOff`** | Confirm the GPU driver is actually present on the node (`nvidia-smi`, via a debug pod or SSH). Confirm `securityContext.privileged: true` is set — DCGM Exporter needs privileged access to read GPU telemetry. |
| **MIG visibility issues** | Confirm MIG mode and driver/DCGM support match. If using MIG, confirm the `pod-resources` hostPath is mounted as shown in step 5. |
| **Grafana panels empty** | Confirm the Prometheus datasource is selected (should be the one the chart provisioned automatically); use PromQL autocomplete in the query editor to confirm the actual metric names — see the naming-prefix note in step 9. |

## 13. Clean up

```bash
kubectl -n monitoring delete -f gpu-alerts.yaml
kubectl -n monitoring delete -f dcgm-servicemonitor.yaml
kubectl -n monitoring delete -f dcgm-exporter.yaml
helm -n monitoring uninstall monitoring
kubectl delete ns monitoring
```

`helm uninstall` does **not** remove the CRDs (`ServiceMonitor`, `PrometheusRule`,
etc.) the chart installed in step 3 — by design, so it doesn't delete objects that
might still be referenced elsewhere. Only remove those separately
(`kubectl get crd | grep monitoring.coreos.com`) if nothing else on the cluster
depends on them.

## What you should see at the end

- Prometheus's **Targets** page shows each GPU node's DCGM Exporter as `UP`.
- Grafana dashboards show GPU utilization, memory %, temperature, and power, broken
  out per node/GPU.
- Alerts fire if temperature crosses the threshold, memory is saturated, or a
  DCGM Exporter target stops being scraped.
