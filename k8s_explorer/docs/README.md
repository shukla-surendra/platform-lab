# Kubernetes docs

Working notes and explainers, basic to advanced, grounded in the actual charts/manifests and
live cluster in this repo wherever possible. Run `make docs-serve` from the repo root for a
browsable site (search, dark mode).

## Basics

- [`kubernetes-fundamentals.md`](./kubernetes-fundamentals.md) — container runtimes/CRI, Pod
  vs Deployment vs ReplicaSet, everyday `kubectl` commands.
- [`cluster-architecture.md`](./cluster-architecture.md) — control plane vs. node components,
  the watch-reconcile pattern everything else is built on.
- [`configmaps-and-secrets.md`](./configmaps-and-secrets.md) — non-sensitive vs. sensitive
  config, why Secrets aren't real encryption, the config-reload gotcha.
- [`storage-and-persistence.md`](./storage-and-persistence.md) — Volume vs PV vs PVC vs
  StorageClass, `volumeClaimTemplates`, what backs storage on minikube vs. EKS.
- [`minikube-linux-bootstrap.md`](./minikube-linux-bootstrap.md) — installing Docker/minikube/
  `kubectl` on a bare Linux box and bringing up a multi-node cluster, command by command
  (what `systemctl enable --now` actually does, `kube-system` Pods explained, scaling nodes,
  common first-run errors).

## Networking & Access

- [`accessing-pods-and-services.md`](./accessing-pods-and-services.md) — `kubectl port-forward`
  vs. the production way (Service + Ingress), worked through with `sample-nginx/`.
- [`service-types.md`](./service-types.md) — `ClusterIP`/`NodePort`/`LoadBalancer`/headless/
  `ExternalName` compared, plus everyday `kubectl` usage (expose, patch, troubleshoot no
  endpoints); worked hands-on with [`services-demo/`](../services-demo).
- [`multiple-services-same-port.md`](./multiple-services-same-port.md) — why N services all
  listening on the same port (e.g. 8080) don't conflict, and the few places port reuse
  actually does (same-Pod containers, `hostPort`, explicit `NodePort` — cross-namespace too).
- [`network-policies.md`](./network-policies.md) — default-open networking, allow-list
  NetworkPolicy semantics, and why enforcement depends on the CNI.

## Workloads & Reliability

- [`workload-types.md`](./workload-types.md) — Deployment vs StatefulSet vs DaemonSet vs Job
  vs CronJob, and when each one is the right choice.
- [`probes-and-health-checks.md`](./probes-and-health-checks.md) — liveness vs readiness vs
  startup probes, and why a missing readiness probe breaks rollouts.
- [`resource-management.md`](./resource-management.md) — requests/limits, LimitRange,
  ResourceQuota, HorizontalPodAutoscaler, PodDisruptionBudget, and how they interact.
- [`pod-and-node-affinity.md`](./pod-and-node-affinity.md) — node affinity, pod affinity/
  anti-affinity, required vs. preferred, and why affinity (placement) is a different axis from
  HPA/KEDA scaling (replica count); worked hands-on with [`affinity-demo/`](../affinity-demo).

## Security

- [`rbac.md`](./rbac.md) — ServiceAccount/Role/RoleBinding/ClusterRole, least-privilege in
  practice, checking effective permissions with `kubectl auth can-i`.

## Advanced

- [`crds-and-operators.md`](./crds-and-operators.md) — how CustomResourceDefinitions +
  controllers work, with KServe/Kargo/Argo Workflows as real examples already on this cluster.
- [`helm-vs-kustomize.md`](./helm-vs-kustomize.md) — templating + release tracking vs.
  overlay/patch on plain YAML, and why this repo uses both.
- [`metrics-and-logs-without-instrumentation.md`](./metrics-and-logs-without-instrumentation.md) —
  does an app need a `/metrics` or logging endpoint to appear in Grafana? No — worked example
  against `rust-api`, which has neither: log capture is automatic (stdout), infra metrics come
  from cAdvisor/kube-state-metrics with zero app changes, and request-level RED metrics can be
  computed from existing access-log lines via LogQL (with a real `unwrap` gotcha, verified live).

## Observability Practice

A guided, hands-on session against [`../rust-api-observability-stack/`](../rust-api-observability-stack/)
(Prometheus + Grafana + Loki via Helm) — deploy it, read the actual PromQL/LogQL each panel
runs, then break it on purpose and diagnose from the dashboards. Builds on
[`metrics-and-logs-without-instrumentation.md`](./metrics-and-logs-without-instrumentation.md)
and [`grafana-dashboard-provisioning.md`](./grafana-dashboard-provisioning.md) above — read
those first if the "how does data get here with zero app instrumentation" question isn't
already answered.

- [`observability-practice-walkthrough.md`](./observability-practice-walkthrough.md) — the
  session itself, six parts: mental model → deploy → read the queries → break it and diagnose
  → talk through incident scenarios out loud → (optional) swap in a Python/FastAPI service.
- [`observability-quick-reference.md`](./observability-quick-reference.md) — copy/paste
  `kubectl`/`helm` commands, PromQL, LogQL, and a debugging checklist for when a panel is
  empty or a query returns nothing. Keep this open in a second terminal during the session.
- [`observability-mental-models.md`](./observability-mental-models.md) — the diagrams and
  incident-diagnosis decision tree (metrics → logs → traces → K8s events) to be able to draw
  and narrate from memory, plus an interview script template.
- [`examples/observability-scenarios.sh`](./examples/observability-scenarios.sh) — runnable
  simulations of 8 failure modes (high latency, crash loop, memory pressure, error spike,
  traffic spike, silent failure, node pressure, cascading failure) to diagnose against the
  dashboards instead of hand-crafting `curl` commands.

## Cloud

- [`eks-setup.md`](./eks-setup.md) — standing up and running Amazon EKS end to end: networking
  prerequisites, `eksctl` cluster creation, IRSA, the AWS Load Balancer Controller, EBS/EFS
  storage, node/pod autoscaling, observability, and cleanup/cost control. Reference tutorial,
  not verified live like the rest of this folder — no AWS account/credentials in this
  environment.

## Install logs

For what broke and how it was fixed installing specific components on this cluster, see the
`INSTALL-*.md` files next to each project: `kserve-inference/INSTALL-KSERVE.md`,
`kargo/INSTALL-KARGO.md`, `kubeflow-pipeline-sample/INSTALL-KUBEFLOW.md`.
