# Greeting operator

A second CRD/operator inside this same tutorial, built step by step by hand
(unlike [`webapp-operator`](../webapp-operator), which is a guided
walkthrough of an existing tutorial). Deliberately a smaller use case than
`WebApp` there — one CRD field in, one child object out, no Deployment, no
Service, no external API calls — so the mechanism (schema, reconcile,
ownership, self-healing) stays the entire focus instead of competing with
domain logic. See [`../README.md`](../README.md) for how this compares to
the other two operators in this folder.

## Problem statement

Say you want to declare "show this greeting message for this person" as a
first-class Kubernetes object, and have something keep a `ConfigMap`
(readable by other apps, mountable into Pods) in sync with it automatically.

Without a CRD, this means hand-writing a `ConfigMap` yourself every time:

```yaml
apiVersion: v1
kind: ConfigMap
metadata: {name: alice-greeting}
data:
  greeting: "Hello, Alice!"
```

That works exactly once. The moment the message needs to change, or a
typo needs fixing, or the greeting needs regenerating after someone
deletes the `ConfigMap` by accident — there's no record of *intent*
("this person should have this greeting") anywhere in the cluster, only
the `ConfigMap` itself. Nothing notices if it drifts or disappears.
Kubernetes has no built-in kind for "a named greeting" — the closest is
`ConfigMap`, which is just an inert key/value blob, same gap `qna.md`
already found with `Certificate`s (there's no built-in notion of "a
certificate" either, just a `Secret` to hold the bytes).

## The CRD

`greeting.platformlab.dev/v1alpha1, Kind=Greeting` — same reversed-DNS
group-naming convention as `webapp.platformlab.dev`
(see [`../../docs/02-crd-design.md`](../../docs/02-crd-design.md)), so it
can't collide with a built-in group or another vendor's CRD.

```yaml
apiVersion: greeting.platformlab.dev/v1alpha1
kind: Greeting
metadata:
  name: alice
spec:
  name: Alice
  message: "Hello, {name}! Welcome to the cluster."
```

- `spec.name` (string, required) — who the greeting is for.
- `spec.message` (string, optional, defaults to `"Hello, {name}!"`) — a
  template; `{name}` gets substituted with `spec.name`.
- `status.configMapName` — the `ConfigMap` this `Greeting` produced.
- `status.observedGeneration` — standard drift-detection field: lets
  `kubectl get greeting` distinguish "reconciled the latest spec" from
  "still catching up."

## What the operator does

Watches `Greeting` objects (and the `ConfigMap`s it owns) and, per
`Greeting`, renders the template and creates/updates a `ConfigMap` named
`<greeting-name>-greeting` in the same namespace, with the rendered text
under `data.greeting`. Sets an owner reference from `Greeting` →
`ConfigMap`, so deleting the `Greeting` garbage-collects the `ConfigMap`
too — this project's own code needs no finalizer for that, same reasoning
as `WebApp`. Self-heals: if someone edits or deletes the `ConfigMap`
directly, the operator notices and puts it back.

**Caveat found during live testing (see `../../docs/qna.md`): kopf adds
its own finalizer to every resource it manages regardless — `kubectl get
greeting alice -o jsonpath='{.metadata.finalizers}'` shows
`kopf.zalando.org/KopfFinalizerMarker`.** So a `Greeting` won't fully
delete while the operator pod is down, unlike the Go version where
deletion never depends on the controller being alive.

That's the entire behavior — deliberately. Once this loop is solid, the
same shape (CRD → owned child object → reconcile → self-heal) is exactly
what scales up to `WebApp`'s Deployment+Service, or to a real operator
like cert-manager's `Certificate` → `Secret`.

## How to install the CRD

The schema is hand-written (kopf has no `make manifests` equivalent — see
the comment at the top of [`config/crd/greeting-crd.yaml`](./config/crd/greeting-crd.yaml)):

```bash
kubectl apply -f config/crd/greeting-crd.yaml
kubectl get crd greetings.greeting.platformlab.dev
```

This alone does nothing — same inert-without-a-watcher point as every
other CRD in this tutorial. `kubectl apply -f config/samples/greeting_sample.yaml`
right now would just sit in etcd with no `ConfigMap` ever appearing.

## The operator implementation

[`operator.py`](./operator.py) — same structure as
[`../webapp-operator-python/operator.py`](../webapp-operator-python/operator.py):

1. `@kopf.on.create` / `@kopf.on.update` / `@kopf.on.resume` watch
   `Greeting` objects and call `reconcile`, which delegates to
   `ensure_child`.
2. `ensure_child` renders `spec.message` (substituting `{name}` with
   `spec.name` — `render()`), builds a `V1ConfigMap` named
   `<greeting-name>-greeting`, and applies it via
   `create_namespaced_config_map` (falling back to `patch_...` on a 409).
3. `kopf.adopt(cm)` sets the owner reference, so deleting the `Greeting`
   garbage-collects the `ConfigMap` too — no finalizer needed.
4. `patch.status["configMapName"]` and `patch.status["observedGeneration"]`
   get written back after every reconcile.
5. `@kopf.timer(..., interval=30)` re-runs the same `ensure_child` every 30
   seconds as the self-heal mechanism (same tradeoff as
   `webapp-operator-python`: polling, not event-driven — see
   `../README.md`'s comparison table).

### Run it locally (fastest way to try it — no build/push needed)

```bash
cd operators/greeting-operator
pip install -r requirements.txt
kopf run operator.py --namespace default
```

### Try it

```bash
kubectl apply -f config/samples/greeting_sample.yaml
kubectl get greeting alice
kubectl get configmap alice-greeting -o jsonpath='{.data.greeting}'
# -> Hello, Alice! Welcome to the cluster.

# self-heal check
kubectl delete configmap alice-greeting
# wait up to 30s, then:
kubectl get configmap alice-greeting -o jsonpath='{.data.greeting}'
```

### Deploy it to the cluster (same pattern as `webapp-operator-python`)

```bash
export ACR_LOGIN_SERVER=akscrdlabacr01.azurecr.io
export IMG="${ACR_LOGIN_SERVER}/greeting-operator:v0.1.0"

docker build -t "$IMG" .
az acr login --name "${ACR_LOGIN_SERVER%%.*}"
docker push "$IMG"

kubectl apply -f config/rbac.yaml
sed "s|REPLACE_ME/greeting-operator:v0.1.0|$IMG|" config/deployment.yaml \
  | kubectl apply -f -

kubectl get pods -n greeting-operator-system
kubectl logs -n greeting-operator-system deploy/greeting-operator -f
```

## Plan

1. ~~Problem statement + CRD design~~
2. ~~Hand-write and install the CRD~~
3. ~~Write the Reconcile loop (`operator.py`)~~
4. ~~Deploy manifests (RBAC, Deployment, Dockerfile)~~
5. Test: create a `Greeting`, watch the `ConfigMap` appear, edit/delete it,
   confirm self-healing
6. Cleanup
