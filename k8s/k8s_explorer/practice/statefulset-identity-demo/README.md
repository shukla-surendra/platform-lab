# statefulset-identity-demo

Hands-on companion to the StatefulSet section of
[`docs/workload-types.md`](../../docs/workload-types.md) and to the fuller
[`docs/statefulset-walkthrough.md`](../../docs/statefulset-walkthrough.md) — a real Helm chart,
one custom local image, **no registry**.

Assumes a running, **multi-node** `minikube` cluster (`minikube status`).

## What problem does it solve, that a Deployment can't?

`workload-types.md` already notes this repo's other StatefulSet (`full-stack-app`'s Postgres)
runs at `replicas: 1`, so the interesting guarantees — ordered creation, per-replica stable DNS,
one-PVC-per-ordinal that *reattaches on restart* — never actually get exercised. This demo runs
**3 replicas** specifically to make all of that visible and verifiable, not just described.

A Deployment gives every replica an interchangeable identity: delete one, a fresh Pod appears
with a new random name and (if it had a PVC at all) a shared or fresh volume — fine for a
stateless web server, wrong for anything that needs *this specific replica* to keep *this
specific disk* across restarts (a database node, a Kafka broker, anything that shards data by
replica). A StatefulSet is the object that makes that guarantee real.

## Build

```bash
./build-images.sh
```

Same `--all` requirement as `../daemonset-sidecar-demo/` — a Pod can land on either node here,
so both need the image locally or the scheduler might pick the one that doesn't have it.

| Image | What it does |
|---|---|
| `identity-server:local` | Every 5s, appends `pod=<own-name> time=<now>` to `/data/identity.log` on its own PersistentVolume, and serves that same directory over HTTP via busybox's built-in `httpd` (port 8080) |

`POD_NAME` comes from the Downward API (`metadata.name`), same mechanism `daemonset-sidecar-demo`
uses for `NODE_NAME` — one image, no per-replica config baked in.

## Install

```bash
helm upgrade --install demo . -n statefulset-identity-demo --create-namespace
```

## Verified — ordered creation, predictable names, one PVC per ordinal

```bash
kubectl rollout status statefulset/demo-identity -n statefulset-identity-demo --timeout=60s
```

Real output — note it waits for each Pod before starting the next, not all three at once:

```
Waiting for 3 pods to be ready...
Waiting for 2 pods to be ready...
Waiting for 2 pods to be ready...
Waiting for 1 pods to be ready...
Waiting for 1 pods to be ready...
partitioned roll out complete: 3 new pods have been updated...
```

```bash
kubectl get pods -n statefulset-identity-demo -l app=identity-server -o wide
```

```
NAME                READY   STATUS    RESTARTS   AGE   IP           NODE
demo-identity-0     1/1     Running   0          28s   10.244.1.4   minikube-m02
demo-identity-1     1/1     Running   0          2s    10.244.0.4   minikube
demo-identity-2     1/1     Running   0          1s    10.244.1.5   minikube-m02
```

`-0`, `-1`, `-2` — predictable, no ReplicaSet-style random hash (see
`../daemonset-sidecar-demo/README.md`'s ownerReferences proof for why Deployment Pods get one and
these don't: there's no ReplicaSet in a StatefulSet's chain either, it owns its Pods directly).

```bash
kubectl get pvc -n statefulset-identity-demo
```

```
NAME                   STATUS   VOLUME                       CAPACITY   ACCESS MODES
data-demo-identity-0   Bound    pvc-73cd9c78-...              50Mi       RWO
data-demo-identity-1   Bound    pvc-748f8643-...              50Mi       RWO
data-demo-identity-2   Bound    pvc-ced41c8e-...              50Mi       RWO
```

Three **separate** PVCs, named `data-<statefulset-pod-name>` — this is `volumeClaimTemplates` in
`templates/statefulset.yaml` doing its job; the field doesn't exist at all on a Deployment spec.

## Verified — stable per-replica DNS (a real gotcha included)

```bash
kubectl exec demo-identity-0 -n statefulset-identity-demo -- \
  nslookup demo-identity-1.demo-identity-headless
```

```
** server can't find demo-identity-1.demo-identity-headless: NXDOMAIN
```

**Looks like a failure, isn't one** — this is busybox's minimal `nslookup` not applying
Kubernetes' search-domain expansion (`/etc/resolv.conf` inside the Pod does have
`search statefulset-identity-demo.svc.cluster.local svc.cluster.local cluster.local` and
`ndots:5`, which should expand a short name like this — busybox's resolver just doesn't apply it
the way glibc/musl-with-getent would). The DNS record itself is real; the full FQDN proves it:

```bash
kubectl exec demo-identity-0 -n statefulset-identity-demo -- \
  nslookup demo-identity-1.demo-identity-headless.statefulset-identity-demo.svc.cluster.local
```

```
Name:	demo-identity-1.demo-identity-headless.statefulset-identity-demo.svc.cluster.local
Address: 10.244.0.4
```

`10.244.0.4` matches `demo-identity-1`'s actual Pod IP from the listing above exactly — this is
what `clusterIP: None` on the headless Service in `templates/service.yaml` buys you: a normal
Service's DNS name resolves to one virtual IP that load-balances across every replica; this
resolves to *one specific replica*, addressable by ordinal. Meaningless for a stateless app,
essential for talking to (say) a specific database primary.

## Verified — the actual point: a deleted Pod's replacement reattaches to the SAME PVC

```bash
kubectl exec demo-identity-1 -n statefulset-identity-demo -- wget -qO- http://localhost:8080/identity.log
```

```
pod=demo-identity-1 time=2026-09-01T04:20:15Z
pod=demo-identity-1 time=2026-09-01T04:20:20Z
pod=demo-identity-1 time=2026-09-01T04:20:25Z
```

```bash
kubectl delete pod demo-identity-1 -n statefulset-identity-demo
kubectl wait --for=condition=Ready pod/demo-identity-1 -n statefulset-identity-demo --timeout=60s
kubectl exec demo-identity-1 -n statefulset-identity-demo -- wget -qO- http://localhost:8080/identity.log
```

```
pod=demo-identity-1 time=2026-09-01T04:20:15Z
pod=demo-identity-1 time=2026-09-01T04:20:20Z
...
pod=demo-identity-1 time=2026-09-01T04:21:20Z
pod=demo-identity-1 time=2026-09-01T04:21:22Z   <- gap here: the ~2s the Pod was down
pod=demo-identity-1 time=2026-09-01T04:21:27Z
```

The pre-delete lines are **still there** — the replacement Pod (same name, brand-new container,
brand-new filesystem for everything *except* `/data`) reattached to
`pvc-748f8643-...`, the exact same PersistentVolumeClaim, confirmed identical:

```bash
kubectl get pvc data-demo-identity-1 -n statefulset-identity-demo
```

```
NAME                   STATUS   VOLUME                                     AGE
data-demo-identity-1   Bound    pvc-748f8643-5177-47e5-909b-6c909875181f   75s
```

A Deployment replica has no equivalent guarantee to break here — there's no `volumeClaimTemplates`
field for it to reattach through in the first place.

## Verified — scale-down deletes in *reverse* order, and PVCs survive it

```bash
kubectl scale statefulset demo-identity -n statefulset-identity-demo --replicas=2
kubectl get events -n statefulset-identity-demo --sort-by='.lastTimestamp' | grep -i delet
```

```
SuccessfulDelete   statefulset/demo-identity   delete Pod demo-identity-2 in StatefulSet demo-identity successful
```

Only `-2` (the highest ordinal) gets deleted — `-0` and `-1` are untouched. Scale-up would create
`-2` again before anything past it, same ordering rule in reverse.

```bash
kubectl get pvc data-demo-identity-2 -n statefulset-identity-demo
```

```
NAME                   STATUS   VOLUME                       AGE
data-demo-identity-2   Bound    pvc-ced41c8e-...              90s
```

**The PVC is not deleted along with the Pod** — StatefulSet's default retention policy keeps a
replica's disk around even after scaling down, specifically so scaling back up doesn't mean
starting that replica's data from zero:

```bash
kubectl scale statefulset demo-identity -n statefulset-identity-demo --replicas=3
kubectl wait --for=condition=Ready pod/demo-identity-2 -n statefulset-identity-demo --timeout=60s
kubectl exec demo-identity-2 -n statefulset-identity-demo -- wget -qO- http://localhost:8080/identity.log
```

First line is from **before** the scale-down/scale-up cycle — the same disk, never recreated:

```
pod=demo-identity-2 time=2026-09-01T04:20:16Z
...
pod=demo-identity-2 time=2026-09-01T04:21:41Z
```

## Cleanup

```bash
helm uninstall demo -n statefulset-identity-demo
kubectl delete namespace statefulset-identity-demo
```

Note what `helm uninstall` does *not* do: it deletes the StatefulSet and Service, but by design
does **not** delete the PVCs it created via `volumeClaimTemplates` — those are only removed here
because the second command deletes the whole namespace. In a real cluster, deleting the
StatefulSet while deliberately keeping its PVCs (e.g. before a redeploy) is the normal,
expected behavior, not a leak.

## Reference

| File | Role |
|---|---|
| `build-images.sh` | Builds the image on all nodes (`--all`) |
| `images/identity-server/` | Appends to `/data/identity.log`, serves it via busybox `httpd` |
| `templates/statefulset.yaml` | The StatefulSet, `volumeClaimTemplates`, Downward API `POD_NAME` |
| `templates/service.yaml` | The headless Service (`clusterIP: None`) that gives per-replica DNS |
