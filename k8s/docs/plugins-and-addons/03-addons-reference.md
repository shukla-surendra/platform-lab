# 3. Add-ons — the full ecosystem list

Broader than `02-plugin-interfaces-reference.md` on purpose — includes
everything commonly called an "add-on," whether or not it implements a
formal plugin interface. The **Mechanism** column is the point: most of
these are CRD+operator, not plugins.

| Add-on | Category | Mechanism | What it does |
|---|---|---|---|
| CoreDNS | DNS | Plain `Deployment`, no CRD | In-cluster DNS for Service/Pod names — on almost every cluster by default. |
| metrics-server | Metrics | **Aggregated API server** (not a CRD, not a plugin — Option B in `../api-server/03-api-model-and-extensibility.md`) | Serves live CPU/memory metrics (`kubectl top`), backing the core `HorizontalPodAutoscaler`. |
| NGINX Ingress Controller / Traefik / HAProxy Ingress | Ingress | Plain `Deployment` watching built-in `Ingress` objects | Implements the routing rules a core `Ingress` object only *describes*. |
| Istio / Linkerd | Service mesh | CRD + operator (`VirtualService`, `DestinationRule`, `Gateway`) + a mutating webhook injecting the sidecar | Traffic routing/mTLS/observability between Pods. Already in the "famous pairs" table, `aks_crd_operator/docs/qna.md`. |
| cert-manager | Certificates | CRD + operator (`Certificate`, `Issuer`/`ClusterIssuer`) | This repo's own running example for "why a CRD is required at all" — full walkthrough in `aks_crd_operator/docs/qna.md`. |
| Prometheus Operator | Monitoring | CRD + operator (`Prometheus`, `ServiceMonitor`, `PrometheusRule`, `Alertmanager`) | Declarative scrape/alerting config instead of hand-edited Prometheus YAML. |
| Grafana / Loki / Tempo | Observability | Plain `Deployment`s (this repo's own `k8s/k8s_observability/`) or CRD-based (Grafana Operator) depending on install method | Dashboards / logs / traces. |
| Argo CD / Flux | GitOps | CRD + operator (`Application`/`AppProject`; `HelmRelease`/`Kustomization`) | Continuously reconciles cluster state against a Git repo. |
| Velero | Backup | CRD + operator (`Backup`, `Restore`, `Schedule`) | Cluster/volume backup and restore. |
| Cluster Autoscaler / Karpenter | Node autoscaling | Karpenter: CRD + operator (`NodePool`, `NodeClaim` — already documented in `aks_crd_operator/docs/qna.md`, including why its controller is invisible on AKS). Cluster Autoscaler: plain `Deployment`, no CRD, watches unschedulable Pods + cloud-provider node-group APIs directly. | Provisions/removes nodes based on Pod scheduling pressure. |
| OPA Gatekeeper / Kyverno | Policy | CRD + operator *and* a validating (Kyverno: also mutating) admission webhook | Cluster-wide policy enforcement beyond what RBAC/schema validation can express — the exact "webhook validation" case flagged in `aks_crd_operator/docs/02-crd-design.md`. |
| Sealed Secrets / External Secrets Operator | Secrets management | CRD + operator (`SealedSecret`; `ExternalSecret`) | Keep secret material out of plain `Secret` objects committed to Git, or synced from an external vault. |
| KEDA | Event-driven autoscaling | CRD + operator (`ScaledObject`, `ScaledJob`) | Scale on external signals (queue depth, Kafka lag) instead of just CPU/memory. |
| Kubernetes Dashboard | UI | Plain `Deployment`, no CRD | Web UI over the standard API — no different access than `kubectl` under the hood. |

## The pattern across this table

Reading down the **Mechanism** column: the overwhelming majority of daily
add-ons are **CRD + operator**, the exact same mechanism this repo builds
from scratch in `aks_crd_operator/`. A genuine plugin-interface add-on
(CNI/CSI/CRI/device-plugin, `02-plugin-interfaces-reference.md`) is
actually the *less* common shape once you're past the handful of
lowest-level infrastructure concerns — see
`04-relation-to-crd-and-operator.md` for why that split exists at all.
