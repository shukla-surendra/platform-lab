# daemonset-sidecar-demo

Hands-on companion to the DaemonSet section of
[`docs/workload-types.md`](../../docs/workload-types.md) and to
[`docs/sidecar-containers.md`](../../docs/sidecar-containers.md) — a real Helm chart, two workload
patterns, **three from-scratch local images** (no registry, no pull, nothing borrowed).

Assumes a running, **multi-node** `minikube` cluster (`minikube status` — this repo's default
profile has 2+ nodes; the DaemonSet's whole point needs more than one to be visible at all).

## What problem does it solve?

Two patterns that look similar on paper (both put "extra" containers on nodes/pods) but solve
opposite problems, easy to conflate if you've only read about them:

- **DaemonSet**: one Pod, cloned automatically onto **every node** — the unit of replication is
  the *node*, not a chosen count. Used for node-level agents (this cluster's own `kube-proxy`
  and CNI are DaemonSets already, per `workload-types.md`).
- **Sidecar**: a **second container inside one Pod**, sharing that Pod's network/volumes with
  the main container. The unit here is "helper for this specific workload," not "one per node."

This project builds one small, purpose-built local image for each pattern (plus a second image
for the sidecar's *partner*, since a sidecar demo needs something to be a sidecar *to*) and
verifies both against a real cluster.

## Build

```bash
./build-images.sh
```

**`--all` is mandatory, not a nice-to-have**: `minikube image build` defaults to loading an
image onto the control-plane node *only*. Skip `--all` on a multi-node cluster and the
DaemonSet's Pod on every other node sits in `ImagePullBackOff` forever — confirmed the hard way
building `../toy-controller/` earlier in this repo, which is exactly why `build-images.sh`
loops with `--all` on all three images rather than assuming single-node.

| Image | Role | What it actually does |
|---|---|---|
| `node-reporter:local` | DaemonSet container | Loops forever printing `node=<name> time=<now>`, reading its own node name from the Downward API |
| `hit-counter:local` | Sidecar demo — main container | Appends a timestamped line to `/var/log/app/events.log` every 5s |
| `log-tailer:local` | Sidecar demo — the sidecar | `tail -F`s that same file (shared `emptyDir`) and re-prints each line prefixed `[log-tailer] forwarded:` |

`values.yaml` sets `imagePullPolicy: Never` on all three — the actual mechanism that makes
"local image, no registry" work: it tells the kubelet not to attempt a pull at all, just use
whatever's already in that node's local image store.

## Install (and re-install, and upgrade) — one command either way

```bash
helm lint .
helm upgrade --install demo . -n daemonset-sidecar-demo --create-namespace
```

`upgrade --install` rather than plain `install`: Helm checks whether a release named `demo`
already exists in that namespace and does the right thing either way — installs it fresh if
not, upgrades the existing one in place if so. Plain `helm install` would instead **error**
("cannot re-use a name") the second time you ran it against an unmodified namespace, forcing an
uninstall first even for a trivial change — `upgrade --install` is the actual command real
CI/CD pipelines and GitOps tooling run on every deploy, exactly because it doesn't need to know
in advance whether this is the first deploy or the fiftieth.

A dedicated namespace (not `default`) — same "give every demo its own blast radius" convention
as `../identity-to-rbac-demo/` and `../admission-webhook-demo/` elsewhere in this repo.
`--create-namespace` only matters on the *first* run (there's nothing to create on later ones);
it means this one command is the whole install, no separate `kubectl create namespace` step.

**Verified this is a real upgrade, not just a no-op re-run** — same command, with an actual
value change:

```bash
helm upgrade --install demo . -n daemonset-sidecar-demo --create-namespace \
  --set sidecarApp.replicaCount=2
```

```
Release "demo" has been upgraded. Happy Helming!
...
REVISION: 3
STATUS: deployed
...
demo deployed:
  - DaemonSet demo-node-reporter — one pod per node, automatically
  - Deployment demo-hit-counter — 2 replica(s), 2 containers each (app + sidecar)
```

```bash
kubectl get deployment demo-hit-counter -n daemonset-sidecar-demo
```

```
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
demo-hit-counter   2/2     2            2           2m55s
```

Went from 1 replica to 2, for real — `REVISION` incrementing (`helm history demo -n
daemonset-sidecar-demo` shows every past revision) and `kubectl rollout status` confirming the
actual Deployment scaled are two independent proofs it wasn't just Helm relabeling the same
state.

## Ready — confirming it, not just assuming it

```bash
kubectl rollout status daemonset/demo-node-reporter -n daemonset-sidecar-demo --timeout=60s
kubectl rollout status deployment/demo-hit-counter -n daemonset-sidecar-demo --timeout=60s
```

Real output:

```
daemon set "demo-node-reporter" successfully rolled out
deployment "demo-hit-counter" successfully rolled out
```

`rollout status` blocks until the workload controller itself reports done — the DaemonSet's
version specifically waits for a Pod to exist and be Ready on *every* matching node, not just
"some Pods somewhere," which a plain `kubectl get pods` glance can't distinguish from "still
scheduling." For confirming every Pod across both workloads at once instead of checking each
controller separately:

```bash
kubectl wait --for=condition=Ready pod -l 'app in (node-reporter,hit-counter)' \
  -n daemonset-sidecar-demo --timeout=60s
```

```
pod/demo-hit-counter-7d587fd798-b4xlw condition met
pod/demo-node-reporter-r59pg condition met
pod/demo-node-reporter-vwlsq condition met
```

Three Pods, matching 1 sidecar replica + 2 DaemonSet nodes exactly.

## Which Pod is which? Read it straight off `kubectl get all`

```bash
kubectl get all -n daemonset-sidecar-demo
```

Real output:

```
NAME                                    READY   STATUS    RESTARTS   AGE
pod/demo-hit-counter-7d587fd798-9tfgn   2/2     Running   0          50m
pod/demo-node-reporter-n6phj            1/1     Running   0          50m
pod/demo-node-reporter-z4z82            1/1     Running   0          50m

NAME                                DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
daemonset.apps/demo-node-reporter   2         2         2       2            2           <none>          50m

NAME                               READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/demo-hit-counter   1/1     1            1           50m

NAME                                          DESIRED   CURRENT   READY   AGE
replicaset.apps/demo-hit-counter-7d587fd798   1         1         1       50m
```

Four *different kinds* of object in one listing, easy to mistake for "four things running" at a
glance. Only the `pod/...` rows are actually Pods — three of them, matching what
`kubectl wait` already confirmed above. `daemonset.apps/...`, `deployment.apps/...`, and
`replicaset.apps/...` are controllers: objects that supervise Pods, not Pods themselves. None of
them run a container.

**Is a ReplicaSet a Pod?** No. The Deployment doesn't create Pods directly — it creates a
ReplicaSet, and the ReplicaSet creates the Pod(s):

```
Deployment (demo-hit-counter)
    │  creates
    ▼
ReplicaSet (demo-hit-counter-7d587fd798)
    │  creates
    ▼
Pod (demo-hit-counter-7d587fd798-9tfgn)
```

Proof, straight from the Pod's own metadata — its `ownerReferences` field names exactly who
created it:

```bash
kubectl get pod demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo \
  -o jsonpath='{.metadata.ownerReferences[0]}'
```

```
{"apiVersion":"apps/v1","kind":"ReplicaSet","name":"demo-hit-counter-7d587fd798", ...}
```

Same check on a DaemonSet Pod — no ReplicaSet in the chain at all, the DaemonSet owns it
directly:

```bash
kubectl get pod demo-node-reporter-n6phj -n daemonset-sidecar-demo \
  -o jsonpath='{.metadata.ownerReferences[0]}'
```

```
{"apiVersion":"apps/v1","kind":"DaemonSet","name":"demo-node-reporter", ...}
```

That's *why* Deployment Pod names carry an extra hash segment that DaemonSet Pod names don't —
`demo-hit-counter-`**`7d587fd798`**`-9tfgn` vs. `demo-node-reporter-n6phj`. The hash is the
ReplicaSet's own name, embedded in every Pod name it creates. It exists so a **rolling update**
is possible at all: on a new image, the Deployment creates a *second*, new-hash ReplicaSet and
shifts replica count from the old one to the new one gradually, so old and new Pods can
coexist mid-rollout. A DaemonSet has no such indirection — there's no "gradual shift between two
versions," just the one Pod per node, so it skips the ReplicaSet layer entirely.

**The fast, no-`ownerReferences`-needed tells**, once you know what to look for:

| Signal | DaemonSet Pod | Sidecar (Deployment) Pod |
|---|---|---|
| `READY` column | `1/1` — one container | `2/2` — two containers, that's the sidecar |
| Name shape | `<name>-<suffix>` — one segment after the name | `<name>-<replicaset-hash>-<suffix>` — two segments |
| `NODE` column, across all its Pods | One Pod per *distinct* node, never two on the same node | However many `replicaCount` says, can land anywhere (even repeat a node) |
| Can it be scaled? | `kubectl scale daemonset ... --replicas=N` → `Error from server (NotFound): the server could not find the requested resource` — DaemonSets don't have a `/scale` subresource at all | `kubectl scale deployment ... --replicas=N` works normally |

That last row is the strongest proof of all, because it's not just reading a label — it's the
API server itself confirming DaemonSets structurally can't be scaled the way Deployments can;
"one per node" isn't a number you're allowed to override.

## Verified — DaemonSet: exactly one Pod per node, zero `replicas` field

```bash
kubectl get daemonset demo-node-reporter -n daemonset-sidecar-demo
```

```
NAME                 DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
demo-node-reporter   2         2         2       2            2           <none>          25s
```

Real output on this repo's 2-node cluster — **2**, matching node count exactly, with no
`replicas:` field anywhere in `templates/daemonset.yaml` (there isn't one in the DaemonSet API
at all — this is the scheduler/DaemonSet-controller's job, not something you configure a count
for).

```bash
kubectl logs -l app=node-reporter --prefix --tail=2 -n daemonset-sidecar-demo
```

```
[pod/demo-node-reporter-r59pg/node-reporter] [node-reporter] node=minikube time=2026-08-30T15:44:34Z
[pod/demo-node-reporter-r59pg/node-reporter] [node-reporter] node=minikube time=2026-08-30T15:44:44Z
[pod/demo-node-reporter-vwlsq/node-reporter] [node-reporter] node=minikube-m02 time=2026-08-30T15:44:34Z
[pod/demo-node-reporter-vwlsq/node-reporter] [node-reporter] node=minikube-m02 time=2026-08-30T15:44:44Z
```

Same image, both pods — each one correctly reports a *different* node name, entirely from the
Downward API (`fieldRef: spec.nodeName` in `daemonset.yaml`), not from anything baked into the
image at build time.

## Verified — sidecar: the finding that isn't obvious until you look

```bash
kubectl logs deploy/demo-hit-counter -c hit-counter --tail=3 -n daemonset-sidecar-demo
```

```
(empty)
```

```bash
kubectl logs deploy/demo-hit-counter -c log-tailer --tail=3 -n daemonset-sidecar-demo
```

```
[log-tailer] forwarded: 2026-08-30T15:44:34Z event #3 from demo-hit-counter-7d587fd798-b4xlw
[log-tailer] forwarded: 2026-08-30T15:44:39Z event #4 from demo-hit-counter-7d587fd798-b4xlw
[log-tailer] forwarded: 2026-08-30T15:44:44Z event #5 from demo-hit-counter-7d587fd798-b4xlw
```

The empty output from `hit-counter` **is the actual point, not a bug** — confirmed by exec'ing
into that exact container and reading the file directly:

```bash
kubectl exec deploy/demo-hit-counter -c hit-counter -n daemonset-sidecar-demo -- cat /var/log/app/events.log
```

```
2026-08-30T15:44:39Z event #4 from demo-hit-counter-7d587fd798-b4xlw
2026-08-30T15:44:44Z event #5 from demo-hit-counter-7d587fd798-b4xlw
2026-08-30T15:44:49Z event #6 from demo-hit-counter-7d587fd798-b4xlw
```

The data is real and present — it's just on disk, not stdout, and `kubectl logs` only ever
captures a container's stdout/stderr stream. **This is the actual reason log-shipping sidecars
exist** (Promtail in `../rust-api-observability-stack/`, Fluent Bit, this project's tiny
`log-tailer`): plenty of real applications write to a log file because that's simpler/legacy
behavior, and a sidecar reading that file and re-emitting it to its own stdout is what makes
`kubectl logs`/any container-log-based pipeline able to see it at all — without touching the
main application's code or image.

## Cleanup

```bash
helm uninstall demo -n daemonset-sidecar-demo
kubectl delete namespace daemonset-sidecar-demo
```

Both steps matter — `helm uninstall` removes the release's own objects (the DaemonSet,
Deployment); it doesn't touch the namespace itself, since `--create-namespace` at install time
doesn't hand Helm ownership of the namespace object to clean up later.

## Reference

| File | Role |
|---|---|
| `build-images.sh` | Builds all 3 images on every node (`--all`) |
| `images/node-reporter/` | DaemonSet container source |
| `images/hit-counter/`, `images/log-tailer/` | The sidecar pair — app + log shipper |
| `templates/daemonset.yaml` | The DaemonSet, Downward API `NODE_NAME` |
| `templates/deployment.yaml` | The Deployment with both sidecar containers + shared `emptyDir` |
