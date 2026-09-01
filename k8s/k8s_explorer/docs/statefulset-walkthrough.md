# StatefulSet — stable identity, walked through on a real cluster

Companion to [`../practice/statefulset-identity-demo/`](../practice/statefulset-identity-demo)
and to [`workload-types.md`](./workload-types.md#statefulset-replicas-with-stable-identity),
which already covers the concept but flags that this repo's other StatefulSet (`full-stack-app`'s
Postgres) runs at `replicas: 1`, so the interesting guarantees are never actually exercised.
Everything below is real: `helm upgrade --install demo . -n statefulset-identity-demo
--create-namespace` was actually run against a live 2-node minikube cluster, 3 replicas, and
every command/output pair here comes from that run.

## The problem, first — why not just use a Deployment?

A Deployment's whole design assumes every replica is interchangeable: no replica has an
identity worth preserving, so deleting one and getting back a fresh Pod with a new random name
and (at best) a shared or brand-new volume is not just acceptable, it's the point — that's what
makes rolling updates and horizontal scaling simple.

That assumption breaks the moment a replica's *identity* carries meaning: a database node that
owns a specific shard, a broker that other nodes address by name, anything where "replica #1
specifically" needs to keep being replica #1 — same name, same disk — across restarts,
reschedules, and node failures. StatefulSet is the object built for exactly that case, and it
does it with three concrete mechanisms, not just a naming convention:

1. **Predictable, stable Pod names** — `<name>-0`, `<name>-1`, `<name>-2`, not a random
   ReplicaSet-style hash.
2. **One PersistentVolumeClaim per ordinal**, created from `volumeClaimTemplates` — a field that
   does not exist on a Deployment's spec at all — that a replacement Pod for the same ordinal
   always reattaches to.
3. **A headless Service** (`clusterIP: None`) giving each replica its own resolvable DNS name,
   so something can address *that specific replica* instead of "any of them."

The rest of this page proves each one against a real cluster, plus a fourth behavior
(ordering) that falls out of how the controller reconciles all of this.

## Setup

```bash
cd practice/statefulset-identity-demo
./build-images.sh
helm upgrade --install demo . -n statefulset-identity-demo --create-namespace
kubectl rollout status statefulset/demo-identity -n statefulset-identity-demo --timeout=60s
```

```
Waiting for 3 pods to be ready...
Waiting for 2 pods to be ready...
Waiting for 2 pods to be ready...
Waiting for 1 pods to be ready...
Waiting for 1 pods to be ready...
partitioned roll out complete: 3 new pods have been updated...
```

That output is itself the first proof: `rollout status` reports the ready count going
**3 → 2 → 1**, meaning the controller is bringing Pods up one at a time and waiting for each to
become Ready before starting the next — the default `OrderedReady` pod management policy. A
Deployment scaling to 3 replicas creates all 3 Pods essentially simultaneously; there is no
such thing as "Pod 2 waits for Pod 1" there.

## Guarantee 1 — predictable names, one PVC per ordinal

```bash
kubectl get pods -n statefulset-identity-demo -l app=identity-server -o wide
```

```
NAME                READY   STATUS    RESTARTS   AGE   IP           NODE
demo-identity-0     1/1     Running   0          28s   10.244.1.4   minikube-m02
demo-identity-1     1/1     Running   0          2s    10.244.0.4   minikube
demo-identity-2     1/1     Running   0          1s    10.244.1.5   minikube-m02
```

```bash
kubectl get pvc -n statefulset-identity-demo
```

```
NAME                   STATUS   VOLUME              CAPACITY   ACCESS MODES
data-demo-identity-0   Bound    pvc-73cd9c78-...     50Mi       RWO
data-demo-identity-1   Bound    pvc-748f8643-...     50Mi       RWO
data-demo-identity-2   Bound    pvc-ced41c8e-...     50Mi       RWO
```

`data-<pod-name>` naming is automatic — `volumeClaimTemplates` in `statefulset.yaml` names the
template `data`, and the controller appends each Pod's own name to produce the PVC name.

## Guarantee 2 — per-replica DNS via the headless Service

```bash
kubectl exec demo-identity-0 -n statefulset-identity-demo -- \
  nslookup demo-identity-1.demo-identity-headless.statefulset-identity-demo.svc.cluster.local
```

```
Name:	demo-identity-1.demo-identity-headless.statefulset-identity-demo.svc.cluster.local
Address: 10.244.0.4
```

`10.244.0.4` is exactly `demo-identity-1`'s own Pod IP from the listing above — this resolves to
*one specific replica*, not a load-balanced virtual IP the way a normal (non-headless) Service's
DNS name would. That's what `clusterIP: None` in `templates/service.yaml` buys: without it, a
Service's DNS name always round-robins across every matching Pod, which is fine for a stateless
backend and meaningless for "I need to talk to replica 1's database specifically."

**Gotcha worth knowing**: the short form (`demo-identity-1.demo-identity-headless`, relying on
`/etc/resolv.conf`'s search-domain expansion) returns `NXDOMAIN` under busybox's minimal
`nslookup`, even though the record genuinely exists — confirmed by the full FQDN above resolving
correctly. Don't read a short-name failure as "the DNS record doesn't exist" without also trying
the full FQDN; busybox's resolver is the limitation here, not Kubernetes DNS.

## Guarantee 3 — the one that actually matters: a replacement Pod keeps the same disk

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
pod=demo-identity-1 time=2026-09-01T04:21:22Z
pod=demo-identity-1 time=2026-09-01T04:21:27Z
```

Everything from before the delete is **still there**; only a ~2s gap marks where the container
was actually down. The replacement Pod got a brand-new container filesystem for everything
except `/data` — that one path reattached to `pvc-748f8643-...`, the identical PVC, verified:

```bash
kubectl get pvc data-demo-identity-1 -n statefulset-identity-demo
```

```
NAME                   STATUS   VOLUME                                     AGE
data-demo-identity-1   Bound    pvc-748f8643-5177-47e5-909b-6c909875181f   75s
```

This is the actual reason StatefulSet exists rather than just being cosmetic naming — a
Deployment replica has nothing equivalent to reattach *through*, since `volumeClaimTemplates`
isn't a field it has.

## Guarantee 4 — scaling is ordered too, and PVCs outlive a scale-down

```bash
kubectl scale statefulset demo-identity -n statefulset-identity-demo --replicas=2
kubectl get events -n statefulset-identity-demo --sort-by='.lastTimestamp' | grep -i delet
```

```
SuccessfulDelete   statefulset/demo-identity   delete Pod demo-identity-2 in StatefulSet demo-identity successful
```

Only the **highest** ordinal (`-2`) gets removed — `-0` and `-1` are untouched. Scaling back up
reverses this: the controller recreates `-2` before it would ever create a hypothetical `-3`.

```bash
kubectl get pvc data-demo-identity-2 -n statefulset-identity-demo
```

```
NAME                   STATUS   VOLUME              AGE
data-demo-identity-2   Bound    pvc-ced41c8e-...     90s
```

The PVC is **not** deleted along with the Pod — by default, StatefulSet keeps a scaled-down
replica's disk around, so scaling back up doesn't mean that replica starts from zero data:

```bash
kubectl scale statefulset demo-identity -n statefulset-identity-demo --replicas=3
kubectl wait --for=condition=Ready pod/demo-identity-2 -n statefulset-identity-demo --timeout=60s
kubectl exec demo-identity-2 -n statefulset-identity-demo -- wget -qO- http://localhost:8080/identity.log
```

First line is from **before** the scale-down happened — proof the disk was never recreated:

```
pod=demo-identity-2 time=2026-09-01T04:20:16Z
...
pod=demo-identity-2 time=2026-09-01T04:21:41Z
```

## Quick-reference: what actually distinguishes this from a Deployment

| | Deployment | StatefulSet |
|---|---|---|
| Pod name | `<name>-<replicaset-hash>-<suffix>` | `<name>-<ordinal>` |
| Creation order | All replicas roughly simultaneously | One at a time, `OrderedReady` by default |
| Scale-down order | No defined order | Highest ordinal first |
| Storage | Shared/no PVC, or none | One PVC per ordinal, reattaches on Pod replace |
| DNS | One name, load-balanced across all replicas | One name per replica via a headless Service |
| Owns Pods via | A ReplicaSet (see `daemonset-sidecar-walkthrough.md`'s ownerReferences proof) | Directly — no ReplicaSet in the chain |

## Cleanup

```bash
helm uninstall demo -n statefulset-identity-demo
kubectl delete namespace statefulset-identity-demo
```

`helm uninstall` deliberately does **not** delete the PVCs `volumeClaimTemplates` created —
that's by design (a redeploy shouldn't silently lose data), which is why cleaning up a demo
namespace needs the explicit namespace delete too, same as `daemonset-sidecar-demo`.
