# kuberay-demo

A minimal KubeRay setup: the KubeRay operator plus one `RayCluster` custom resource
(1 head + 1 worker), run on local minikube to see the operator pattern itself, not
just a Ray workload.

## What KubeRay actually is

Ray needs a head process (scheduler + GCS metadata store + dashboard) and worker
processes that register with it — normally you'd hand-roll that topology with
StatefulSets/Services yourself. KubeRay is a Kubernetes operator that turns "head +
workers" into a CRD (`RayCluster`) and reconciles it: create the CR, the operator
creates the head Pod/Service and worker Pods, watches them, and (if autoscaling is
on) adds/removes worker Pods based on Ray's own autoscaler signaling resource demand
back to the operator. Same operator pattern as KServe (`InferenceService` →
controller reconciles) or Kubeflow Pipelines — a domain-specific control loop on top
of core Kubernetes primitives.

`raycluster.yaml` here deliberately sets `minReplicas: 1` / `maxReplicas: 2` on the
worker group so the autoscaling path exists but doesn't fire under idle load — the
point of this demo is seeing the reconcile loop and dashboard, not load-testing
autoscaling. Both head and worker are pinned to the same node (`nodeSelector:
kubernetes.io/hostname: minikube`) — see [`INSTALL-KUBERAY.md`](./INSTALL-KUBERAY.md)
for why.

## Install

For how the operator got installed locally (and what broke along the way), see
[`INSTALL-KUBERAY.md`](./INSTALL-KUBERAY.md).

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm install kuberay-operator kuberay/kuberay-operator --version 1.7.0 \
  --namespace kuberay --create-namespace

kubectl apply -f raycluster.yaml
kubectl -n kuberay get pods -l ray.io/cluster=raycluster-demo
```

## See it working

```bash
# operator's view of the cluster: DESIRED/AVAILABLE workers, STATUS
kubectl -n kuberay get raycluster raycluster-demo -o wide

# dashboard: Overview/Cluster tabs (nodes, resources) — this is what actually works reliably
kubectl -n kuberay port-forward svc/raycluster-demo-head-svc 8265:8265
open http://localhost:8265
```

`kubectl get raycluster ... -o wide` is the operator's view. The dashboard's
Overview/Cluster/Nodes tabs are the Ray-native view of the same cluster and are
reliable in this setup. **The Jobs tab and job submission are not** — see the
"Known limitation" section below before expecting a job to show up there.

Avoid `kubectl exec ... python some_script.py` directly inside the head/worker
containers to talk to Ray — in this setup it reliably knocks the raylet into a
crash loop (see `INSTALL-KUBERAY.md`). Use `ray job submit` from outside the
cluster instead (when it works — see below).

## Mac local: yes, this runs fine

No GPU, no cloud account needed. On minikube (docker driver) with 3 nodes × 12 CPU
allocatable, the whole thing (operator + head + 1 worker) requests 1.5 CPU / 3Gi and
comfortably fits on a single node. The only local prerequisite is Docker Desktop
actually running before `minikube start` — see the troubleshooting doc for what
happens when it isn't.

## Known limitation: job submission doesn't work here

`ray job submit` (CLI, SDK, or raw `POST /api/jobs/`) consistently fails with
`ServerDisconnectedError` / HTTP 500 on this local setup, reproduced on both Ray
2.9.3 and 2.40.0, with head+worker on the same node and on different nodes. The
dashboard's job HTTP head (`job_head.py`, port 8265) proxies submission internally
to the `JobAgent` (port 52365, same pod). Agent-side logs show the `JobAgent`
successfully calling `ray.init()` to connect to its own cluster — then nothing:
no exception, no traceback, the connection just dies. That points to the `JobAgent`
process itself crashing at the native/C++ level (a raylet-extension crash inside an
already-running asyncio event loop, not a Python-level bug), not something fixable
by touching this repo's YAML or docs. `ray status`, the dashboard's Overview/Cluster
tabs, and the KubeRay operator's own reconciliation all work correctly throughout —
only the job-submission code path is affected.

If you need to actually run something on the cluster, `ray.init(address="auto")`
from a plain Python script — connecting via the Ray client port (10001, exposed in
`raycluster.yaml`) from *outside* the container — is the one path not yet confirmed
broken; `kubectl exec`-ing a script directly inside the head container is confirmed
**broken** (crashes the raylet, see the troubleshooting doc).

## Teardown

```bash
kubectl delete -f raycluster.yaml
helm uninstall kuberay-operator -n kuberay
kubectl delete namespace kuberay
```
