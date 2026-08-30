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

**Update:** Ray Client (`ray://`, port 10001) from outside the container was also
tested and is **also broken** — same underlying crash, different front door. Every
path tried that spawns a new worker process on this raylet (`kubectl exec`, the
Jobs API, Ray Client) hits it; `rayjob.yaml` in this folder (the `RayJob` CRD —
the Kubernetes-native way to invoke a job from outside the cluster, see
[`INSTALL-KUBERAY.md`](./INSTALL-KUBERAY.md)) is untested but would be expected to
hit the same wall, since it still ultimately goes through the same job-execution
code path inside the cluster. There is currently no confirmed-working way to run
a job or a Serve deployment on *this specific* minikube/KubeRay setup — see
"Real workload examples," below, for where that actually got proven out instead.

## Real workload examples: a real training job + a real serving endpoint

`train_job.py` and `serve_model.py` are a genuine (if small) ML platform workflow,
not a toy — real dataset (sklearn's breast-cancer set), real distributed
hyperparameter search across 8 configs as parallel Ray tasks, real 5-fold
cross-validation, a real held-out test accuracy (96.5%), and a real HTTP
prediction endpoint serving that trained model.

Because of the limitation above, these are proven out against **native Ray
running directly on the Mac** (no Kubernetes/minikube involved at all) rather
than this folder's `RayCluster` — same Ray version (2.40.0), same code, just a
different cluster underneath, chosen specifically because it isn't affected by
the bug:

```bash
# one-time: start a local Ray head (dashboard at :8265)
.venv/bin/ray start --head --dashboard-host=0.0.0.0 --dashboard-port=8265 --port=6379

# train: submitted via the real Jobs API (not kubectl exec, not `python train_job.py`
# directly) so the driver logs actually show up under the dashboard's Jobs tab —
# this is also what the dashboard's own "Driver logs are only available when
# submitting jobs via the Job Submission API..." message is telling you.
RAY_ADDRESS='http://127.0.0.1:8265' .venv/bin/ray job submit \
  --working-dir . --submission-id train-breast-cancer \
  -- .venv/bin/python train_job.py

# serve the model that job just trained
.venv/bin/python serve_model.py

curl -X POST http://localhost:8010/predict -H "Content-Type: application/json" \
  -d '{"features": [17.99, 10.38, 122.8, 1001, 0.1184, 0.2776, 0.3001, 0.1471, \
                     0.2419, 0.0787, 1.095, 0.9053, 8.589, 153.4, 0.0064, 0.049, \
                     0.0537, 0.0159, 0.03, 0.0062, 25.38, 17.33, 184.6, 2019, \
                     0.1622, 0.6656, 0.7119, 0.2654, 0.4601, 0.1189]}'
# -> {"prediction": "malignant", "probabilities": {...}, "model_test_accuracy": 0.9649}
```

One real gotcha worth keeping: `ray job submit --working-dir .` runs the job from
a **sandboxed copy** of that directory (uploaded as a package to the cluster), not
this actual folder — `train_job.py` saves `model.joblib` to a hardcoded absolute
path for exactly this reason, since a path relative to `__file__` would land
inside that ephemeral sandbox instead. `serve_model.py` doesn't have this problem
since it's run directly, not through the Jobs API.

`entrypoint: python train_job.py` (system `python`, no venv) also fails with
`command not found` — the job supervisor spawns the entrypoint via a bare shell,
which doesn't inherit this venv's `PATH`. Use the venv's full python path in the
entrypoint instead.

## Teardown

```bash
kubectl delete -f raycluster.yaml
helm uninstall kuberay-operator -n kuberay
kubectl delete namespace kuberay
```
