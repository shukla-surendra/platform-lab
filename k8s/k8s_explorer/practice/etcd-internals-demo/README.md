# etcd-internals-demo

Companion to [`docs/cluster-architecture.md`](../../docs/cluster-architecture.md), which maps
`kube-apiserver`/`etcd`/`kube-scheduler`/`kube-controller-manager` as boxes on a diagram. This
project opens the etcd box: every `kubectl` object you've ever created in this repo is,
underneath, one key in a single key-value store — this proves it directly, against the real
etcd backing this repo's shared minikube cluster, not a toy instance.

Assumes a running `minikube` cluster (`minikube status`) with its default single-node etcd
(`kubectl get pods -n kube-system -l component=etcd`).

## What problem does it solve?

`docs/crds-and-operators.md` and `toy-controller/` both describe controllers as "watch an
object, reconcile." It's easy to read that and picture the watch as some Kubernetes-specific
notification bus. It's actually much flatter than that: **etcd's own native watch feature**,
proxied through the API server. There's no separate eventing system — the informer pattern
those two projects build on is a direct consequence of etcd being a watchable KV store, not an
abstraction layered artificially on top of one. This project watches the *raw etcd key* directly
(bypassing the Kubernetes API entirely) to make that concrete.

## Setup

```bash
chmod +x etcdctl.sh   # if not already executable
./etcdctl.sh version
```

`etcdctl.sh` runs `etcdctl` **inside** the real `etcd-minikube` pod, using the same mTLS client
cert the kube-apiserver itself is configured with (`--cert-file`/`--key-file` in that pod's own
command args) — this is talking to etcd exactly the way the only other real client normally
does.

## Verified — a Kubernetes object is one key in etcd, nothing more

```bash
kubectl create configmap etcd-demo-cm --from-literal=hello=world
./etcdctl.sh get /registry/configmaps/default/etcd-demo-cm
```

Real output (binary-ish protobuf, but readable enough to see exactly what it is):

```
/registry/configmaps/default/etcd-demo-cm
k8s
v1	ConfigMap...etcd-demo-cm default...
...
helloworld
```

The key path itself is the whole scheme: `/registry/<resource-type>/<namespace>/<name>` (cluster-
scoped resources drop the namespace segment). `kubectl create` didn't invoke any special
storage logic — the API server validated/defaulted the object, then serialized it (protobuf,
the `k8s` magic prefix visible at the very start of the value) and wrote it to exactly this key.
There's no separate database, index, or object store underneath Kubernetes; this key-value pair
**is** the ConfigMap.

## Verified — the watch mechanism, one layer below informers

`toy-controller/`'s `watch_namespaces()` calls the Kubernetes watch API. That API is itself a
proxy in front of etcd's own native `Watch` RPC — provable by watching the raw key directly,
with no Kubernetes API in the loop at all:

```bash
./etcdctl.sh watch /registry/configmaps/default/etcd-demo-cm &
kubectl label configmap etcd-demo-cm demo=updated --overwrite
kubectl delete configmap etcd-demo-cm
```

Real captured output — two raw etcd events, `PUT` then `DELETE`, for a single `kubectl label`
and a single `kubectl delete`:

```
PUT
/registry/configmaps/default/etcd-demo-cm
k8s
v1	ConfigMap...
...
demoupdated...
kubectl-label...
helloworld

DELETE
/registry/configmaps/default/etcd-demo-cm
```

`kubectl label` produced a `PUT` (an update, not a special "label changed" event type — etcd has
no concept of Kubernetes fields, only whole-value writes) carrying the *entire* updated object,
including a `kubectl-label` field-manager entry (server-side apply's ownership tracking, also
just more bytes in the same value). `kubectl delete` produced a bare `DELETE`, no object body.
This is the entire event vocabulary a `SharedInformer` is built on: `PUT` and `DELETE`, nothing
richer — "this changed" plus the full new value, or "this is gone." Everything an informer
appears to know about *what* changed between two versions of an object, it actually computes
itself by diffing two full `PUT` payloads client-side; etcd never sends a diff.

## Verified — real raft state, not a diagram

```bash
./etcdctl.sh endpoint status -w table
```

Real output:

```
+------------------------+------------------+---------+-----------------+---------+--------+-----------------------+-------+-----------+------------+-----------+------------+--------------------+
|        ENDPOINT        |        ID        | VERSION | STORAGE VERSION | DB SIZE | IN USE | PERCENTAGE NOT IN USE | QUOTA | IS LEADER | IS LEARNER | RAFT TERM | RAFT INDEX | RAFT APPLIED INDEX |
+------------------------+------------------+---------+-----------------+---------+--------+-----------------------+-------+-----------+------------+-----------+------------+--------------------+
| https://127.0.0.1:2379 | aec36adc501070cc |   3.6.4 |           3.6.0 |   23 MB |  10 MB |                   57% |   0 B |      true |      false |         6 |     433232 |             433232 |
+------------------------+------------------+---------+-----------------+---------+--------+-----------------------+-------+-----------+------------+-----------+------------+--------------------+
```

`RAFT TERM`/`RAFT INDEX` are real raft consensus counters, even on this single-member cluster —
every write (every `kubectl apply`, every controller's reconcile-triggered patch, across this
entire repo's demos) increments `RAFT INDEX` by at least one, because every write is a raft log
entry that must be committed before etcd acknowledges it, member count of one or not. `IS LEADER:
true` here is trivial (a 1-node raft cluster is always its own leader), but the field is the same
one that matters for real quorum questions on a multi-member cluster — see "What this doesn't
cover" below.

## Verified — what's actually in this cluster's etcd, by volume

```bash
./etcdctl.sh get /registry --prefix --keys-only > /tmp/allkeys.txt
wc -l /tmp/allkeys.txt
sed -n 's#^/registry/\([a-z.]*\)/.*#\1#p' /tmp/allkeys.txt | sort | uniq -c | sort -rn | head -10
```

Real output, this cluster, right now — **2,080 total keys**:

```
 486 events
  85 clusterroles
  67 clusterrolebindings
  55 serviceaccounts
  44 configmaps
  39 monitoring.coreos.com
  35 services
  32 pods
  21 secrets
  17 endpointslices
  15 rolebindings
```

Worth remembering as a real production fact, not just a curiosity: `events` is the largest
category by a wide margin — a quarter of everything in this etcd. Kubernetes `Event` objects
(the ones behind `kubectl describe`'s "Events:" section, and every `FailedScheduling`/
`SuccessfulCreate` seen in this repo's other demos) are ordinary etcd-backed objects with a short
TTL, and their write volume is exactly why production clusters commonly run **a second, separate
etcd instance dedicated to Events** (`--etcd-servers-overrides=/events#https://...`) — so a burst
of event churn can't compete for write bandwidth/compaction with the actually-critical cluster
state (Pods, Secrets, RBAC) sharing the main etcd instance.

## What this doesn't cover (the honest boundary)

- **Quorum loss / multi-member raft failover** — this cluster's etcd is a single member
  (`member list` above shows exactly one). A real demonstration of "kill the raft leader, watch
  a new one get elected, watch writes block until quorum is restored" needs an actual multi-member
  etcd (e.g. a `kubeadm`-built control plane with 3+ stacked or external etcd members —
  `aws-kubeadm-cluster/` in this repo is real infrastructure but wasn't set up with etcd HA in
  mind either). Documented as a gap, not simulated.
- **Compaction/defragmentation** — `DB SIZE` vs. `IN USE` above (23MB vs 10MB, 57% "not in use")
  is itself evidence of etcd's append-only MVCC storage accumulating old revisions until
  compacted; this project observes that fact but doesn't walk through running a compaction/
  defrag cycle by hand.
- **etcd snapshot/restore** (disaster recovery) — a real, common production procedure
  (`etcdctl snapshot save`/`restore`), not attempted here to avoid touching this shared cluster's
  actual data directory.

## Cleanup

```bash
rm -f /tmp/allkeys.txt
kubectl get configmap etcd-demo-cm 2>/dev/null && kubectl delete configmap etcd-demo-cm
```

(The demo `ConfigMap` was already deleted as part of the watch demo above — this is only needed
if you stopped partway through.)

## Reference

| File | Role |
|---|---|
| `etcdctl.sh` | Runs `etcdctl` inside the real `etcd-minikube` pod with its own mTLS client cert |
