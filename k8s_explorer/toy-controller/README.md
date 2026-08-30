# toy-controller

Hands-on companion to [`docs/crds-and-operators.md`](../docs/crds-and-operators.md) — but where
that page (and `kuberay-demo/`, `kubeflow-pipeline-sample/`, `kargo/` elsewhere in this repo) show
you *installing and using* someone else's operator, this one is the reconcile loop built from
scratch, to prove the mechanism is understood rather than just consumed.

Assumes a running `minikube` cluster (`minikube status`).

## What problem does it solve?

Every operator you've used in this repo — KubeRay creating a `RayCluster`'s Pods, Argo Workflows
running a Kubeflow pipeline's steps — looks like magic from the outside: you create a custom
object, and *something* makes the cluster match it. That something is always the same pattern,
regardless of which operator: **watch for changes, queue the affected object's key, and
reconcile** — re-derive what should exist from the object's current spec and make it so, whether
or not you actually know what triggered this particular reconcile call.

This project implements exactly that pattern against a plain built-in resource (`Namespace`, no
CRD needed) so the mechanism is visible without also having to stand up a CRD, a generated
client, and a full operator framework at the same time.

## The behavior

Any `Namespace` labeled `toy-controller/managed=true` automatically gets:
- a `ResourceQuota` (`toy-quota`) — 10 pods, 1 CPU, 1Gi memory requested max
- a default-deny `NetworkPolicy` (`toy-default-deny`) — no ingress unless something else opens it

This is a real, useful pattern in its own right, not just a teaching toy — it's how you'd enforce
"every namespace a team self-serves gets baseline governance objects automatically," the concrete
form of the "multi-tenancy: namespaces, resource quotas, network policies" line in
`ml-platform-engineer-roadmap.md` §5.

## The mechanism, and why it's built this way

| Piece | What it is here | What it maps to in a real operator (client-go / kubebuilder) |
|---|---|---|
| `watch_namespaces()` | A `watch.Watch().stream(...)` loop over `list_namespace` | A `SharedInformer` |
| `Workqueue` | An in-memory `queue.Queue` + a `set` for key dedup | `workqueue.RateLimitingInterface` |
| `resync_loop()` | Re-enqueues every namespace every 30s regardless of events | The informer's periodic resync |
| `reconcile()` | Re-reads live state from the API server, never trusts the event payload | The `Reconcile(ctx, req)` function every controller-runtime controller implements |
| `worker()`'s retry/backoff | `threading.Timer` with exponential backoff, capped retries | The workqueue's built-in rate-limited requeue |

The one property worth understanding, not just the code: **this is level-triggered, not
edge-triggered.** `reconcile()` takes a namespace *name*, not an event — it doesn't know or care
whether it was called because of an ADDED, a MODIFIED, a resync tick, or a retry after a failure.
It just asks "what should be true for this namespace right now" and makes it true. That's what
makes it self-healing: delete the ResourceQuota by hand, and it comes back on the next resync tick
even though nothing "told" the controller it was deleted (it isn't watching ResourceQuotas at
all — only Namespaces).

## Verified run — local (out-of-cluster)

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python controller.py
```

```bash
kubectl create namespace toy-demo
kubectl label namespace toy-demo toy-controller/managed=true
```

Controller log, real output:

```
2026-08-29 23:23:00,284 INFO ns=toy-demo not managed (label toy-controller/managed != true), skipping
2026-08-29 23:23:00,326 INFO ns=toy-demo created ResourceQuota/toy-quota
2026-08-29 23:23:00,331 INFO ns=toy-demo created NetworkPolicy/toy-default-deny (default-deny ingress)
2026-08-29 23:23:00,331 INFO ns=toy-demo reconciled OK
```

The first line is the `Namespace` ADDED event, before the label existed — correctly skipped, not
crashed. The label triggered a MODIFIED event a few seconds later that reconciled for real.

**Self-healing check** — deleted the ResourceQuota by hand, waited past one 30s resync tick, no
new watch event involved:

```bash
kubectl delete resourcequota toy-quota -n toy-demo
# ...30s later, unprompted...
kubectl get resourcequota -n toy-demo
```

```
NAME        REQUEST                                                 LIMIT   AGE
toy-quota   pods: 0/10, requests.cpu: 0/1, requests.memory: 0/1Gi           20s
```

It came back. The controller logs show `resync: re-enqueued N namespaces` immediately before the
recreate — the scheduled tick, not a coincidence.

## Verified run — in-cluster (the real deployable path)

```bash
# multi-node minikube: image build defaults to the control-plane node only,
# so --all is required or the Deployment's Pod lands on a node without the image
minikube image build --all -t toy-controller:local .

kubectl apply -f rbac.yaml
kubectl apply -f deployment.yaml
kubectl rollout status deployment/toy-controller
```

```
deployment "toy-controller" successfully rolled out
```

Same namespace/label test against the in-cluster Pod produced identical logs — confirms
`load_incluster_config()` (ServiceAccount token + CA cert, no kubeconfig) and the `rbac.yaml`
grants actually work, not just the local-kubeconfig path used above.

**RBAC is intentionally minimal**: `get/list/watch` on namespaces, `get/list/create` (no
`update`/`delete`) on the two managed object types — reconcile only ever creates-if-missing, so
the ClusterRole doesn't grant anything it doesn't use. Worth pointing at directly if this comes up
next to `docs/rbac.md`'s least-privilege discussion.

## Cleanup

```bash
kubectl delete namespace toy-demo
kubectl delete -f deployment.yaml
kubectl delete -f rbac.yaml
```

## Known simplifications (named on purpose, not hidden)

- No finalizer: un-labeling or deleting a managed namespace doesn't retract the ResourceQuota/
  NetworkPolicy (they just get garbage-collected with the namespace itself if it's deleted).
  A real operator that needs cleanup-on-delete would add a finalizer — deliberately left out here
  to keep the core loop legible; it's a separate mechanism, not part of the reconcile pattern.
- Built on the Python `kubernetes` client's `watch` module, not client-go — this is about the
  *pattern*, not client-go fluency. If a target company's stack specifically expects Go/
  kubebuilder experience, the natural next variation is reimplementing this same behavior with
  `controller-runtime`, where most of `Workqueue` above disappears because the framework provides
  it — worth doing once this version is solid, to see exactly what the framework is buying you.

## Reference

| File | Role |
|---|---|
| `controller.py` | The whole controller — informer-equivalent watch loop, workqueue, reconcile, resync |
| `requirements.txt` | Just the `kubernetes` client library |
| `Dockerfile` | Non-root, minimal image for the in-cluster deployment |
| `rbac.yaml` | ServiceAccount + least-privilege ClusterRole/ClusterRoleBinding |
| `deployment.yaml` | Runs the built image in-cluster under that ServiceAccount |
