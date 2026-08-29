# KubeRay

**Category:** Kubernetes operator (turns a distributed-compute cluster into a declarative
custom resource)

**Looking for where vLLM fits into this?** See
[`conversation.md`](conversation.md) — the vLLM → Ray → KubeRay → Kubernetes layering,
including the specific mechanism (`distributed_executor_backend`) that decides whether
vLLM needs Ray at all. This doc covers KubeRay itself.

## What it is, and the problem it actually solves

[Ray](../ray/README.md) needs more than one process to be a real cluster: a **head** process
(the scheduler, the GCS metadata store, the dashboard) that workers register with, and any
number of **worker** processes doing the actual task/actor execution. Standing that up on
Kubernetes by hand means writing and babysitting your own Pods/Services/StatefulSets, wiring
the head's address into every worker, and reimplementing scale-up/scale-down yourself whenever
load changes — none of which is Kubernetes-native or reusable.

KubeRay is the operator that closes that gap: it defines a `RayCluster` **custom resource**
(head spec + one or more worker-group specs, each with its own replica count, image, and
resource requests) and runs a **reconcile loop** — watch the CR, create/update/delete the
actual Pods and Services needed to match it, and keep doing that forever. Two more CRDs build
on the same primitive: `RayJob` (submit-a-job-then-tear-the-cluster-down, for batch/training
jobs) and `RayService` (a `RayCluster` plus zero-downtime rolling updates, for long-lived
serving). This is the same control-loop pattern as KServe's `InferenceService` or a Kubeflow
`Pipeline` — a domain-specific abstraction layered on top of core Kubernetes primitives,
rather than a special-cased deployment script.

## Autoscaling — two loops working together, not one

KubeRay itself doesn't decide *when* to add a Ray worker — **Ray's own autoscaler**, running
inside the head Pod, watches actual task/actor resource demand and decides that. What KubeRay
adds is the Kubernetes-side half: when Ray's autoscaler asks for more capacity, KubeRay is
the thing that turns that ask into an actual new worker Pod (bounded by
`minReplicas`/`maxReplicas` on the worker group), and removes the Pod again when Ray reports
a worker idle. Two autoscalers, two different jobs: Ray decides workload-level need, KubeRay
executes the Kubernetes-level Pod lifecycle.

## Usage (verified locally on minikube)

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm install kuberay-operator kuberay/kuberay-operator --version 1.7.0 \
  --namespace kuberay --create-namespace
```

A minimal `RayCluster` (1 head, 1 worker, autoscaling bounded 1-2 workers):

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: raycluster-demo
  namespace: kuberay
spec:
  rayVersion: "2.40.0"
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray:2.40.0
            resources:
              requests: { cpu: "500m", memory: "1Gi" }
              limits: { cpu: "1", memory: "2Gi" }
            ports:
              - containerPort: 6379
                name: gcs
              - containerPort: 8265
                name: dashboard
  workerGroupSpecs:
    - groupName: small-group
      replicas: 1
      minReplicas: 1
      maxReplicas: 2
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray:2.40.0
              resources:
                requests: { cpu: "500m", memory: "1Gi" }
                limits: { cpu: "1", memory: "2Gi" }
```

```bash
kubectl apply -f raycluster.yaml
kubectl -n kuberay get raycluster raycluster-demo -o wide   # operator's view: DESIRED/AVAILABLE workers, STATUS

# Ray's own view of the cluster (read-only CLI, safe to run):
kubectl -n kuberay exec -it <head-pod> -- ray status

# dashboard: Overview/Cluster/Nodes tabs work reliably; Jobs tab does not (see below)
kubectl -n kuberay port-forward svc/raycluster-demo-head-svc 8265:8265
```

Full runnable copy (with a troubleshooting log) lives at
[`k8s_explorer/kuberay-demo/`](../../../../k8s_explorer/kuberay-demo/README.md).

**Gotchas worth knowing:**
- Head and worker must run the *same* Ray version. A mismatch fails at worker
  registration (the worker Pod comes up healthy, but never joins the cluster), which
  looks like a networking problem if version isn't the first thing checked.
- Never `kubectl exec` a Python script directly into a head/worker container to talk
  to Ray (e.g. `kubectl exec ... python my_script.py`). On this local setup that
  reliably crashed the raylet (`dashboard_agent` and the raylet fate-share; one
  dying kills the other) and cascaded into a crash loop. `kubectl exec ... ray
  status` (a built-in read-only command) is fine — it's *running your own script
  inside the container* that's the problem.
- Job submission (`ray job submit`, the SDK, and raw `POST /api/jobs/`) failed
  consistently in local testing — reproduced on Ray 2.9.3 and 2.40.0, with head and
  worker on the same node and on different nodes — with `ServerDisconnectedError` /
  HTTP 500. The dashboard's job HTTP head proxies submission internally to the
  `JobAgent` process in the same pod; agent-side logs show it getting as far as its
  own `ray.init()` call and then dying with zero exception logged anywhere,
  consistent with a native-level crash rather than an application bug. Everything
  else (cluster status, dashboard Overview/Cluster tabs, the operator's
  reconciliation) worked correctly throughout — this looks specific to the
  job-submission code path in this environment, not a broader cluster problem. Full
  writeup in the demo's `INSTALL-KUBERAY.md`.

## Runs fine on Mac local

No GPU or cloud account needed — minikube (docker driver) is enough; the whole demo above
(operator + 1 head + 1 worker) requests 1.5 CPU / 3Gi total. The only prerequisite is Docker
Desktop actually running (and not mid-auto-update — an update-triggered VM restart SIGKILLs
every running container, including minikube's nodes, which reads like a cluster crash but
isn't) before `minikube start`.

## Alternatives / adjacent tools

| Tool | How it differs |
|---|---|
| **Plain Kubernetes Jobs/CronJobs** | Coarse-grained, one-Pod-per-unit-of-work batch execution — no shared object store, no in-process actor addressing, no autoscaling tied to actual workload demand the way Ray's own autoscaler provides. |
| **Kubeflow Training Operator** | Purpose-built CRDs for specific ML training frameworks (`PyTorchJob`, `TFJob`) rather than a general-purpose distributed-compute cluster; narrower scope than what a `RayCluster` can run. |
| **`ray up` (Ray's own cluster launcher, non-Kubernetes)** | Provisions cloud VMs directly (AWS/GCP/Azure) without Kubernetes at all — the right choice for a team not already standardized on Kubernetes; KubeRay is the choice when the cluster needs to live alongside other Kubernetes-managed workloads and use the same RBAC/networking/observability stack. |

## Relationship to other tools in this repo

- **[Ray](../ray/README.md)** — KubeRay is the deployment/orchestration layer; the actual
  tasks/actors/object-store primitives it schedules onto the cluster are Ray Core itself,
  covered in depth (local-mode, hands-on) in that doc.
