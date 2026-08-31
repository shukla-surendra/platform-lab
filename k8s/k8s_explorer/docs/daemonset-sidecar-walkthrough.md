# DaemonSet & Sidecar — Real Doubts, Answered Live

Companion to [`../practice/daemonset-sidecar-demo/`](../practice/daemonset-sidecar-demo) and to
[`workload-types.md`](./workload-types.md#daemonset-exactly-one-pod-per-node) /
[`sidecar-containers.md`](./sidecar-containers.md). That project's README documents the
*mechanism*; this page documents the actual **questions that came up exploring the real,
running deployment** — genuine points of confusion, resolved against real `kubectl` output on
a live cluster, not a scripted teaching narrative. Growing over time as more come up.

Everything below is real: a `helm upgrade --install demo . -n daemonset-sidecar-demo
--create-namespace` was actually running, and every command/output pair here was actually run
against it.

## "I don't know what is sidecar and what is daemonset"

The concept, before any `kubectl` at all:

**DaemonSet — "put exactly one copy of this on every machine, automatically."** Not "how many
copies do I want" (that's a Deployment's job — pick a number). A DaemonSet has no number. Every
node gets exactly one; a new node joining tomorrow gets one too, with zero action from anyone;
a node leaving takes its copy with it. Real-world version: a company's antivirus/monitoring
agent — IT doesn't say "install 50 copies," they say "every laptop gets one," and it follows new
laptops as they join. Same idea, for Kubernetes nodes instead of laptops.

**Sidecar — "a second helper container riding along in the same Pod as your main one."** Not a
separate Kubernetes object — just a second entry in one Pod's container list. The two containers
share that Pod: same disk (via a shared volume), same network address (`localhost` between
them). The main container has no idea the sidecar exists; it just does its job normally.
Real-world version: a conference speaker and their live interpreter standing next to them — the
speaker just talks normally, not thinking about translation at all; the interpreter listens to
that same speech and produces something extra for someone else, without the speaker's job ever
changing.

Mapped onto this project's two real, running examples: `demo-node-reporter` is the DaemonSet —
one copy per node, the "every machine gets one" idea made real. `demo-hit-counter` is the
sidecar pair — `hit-counter` writes to a file not knowing anything's listening, `log-tailer`
reads that same file and echoes it elsewhere, the "interpreter" that makes the data visible via
`kubectl logs` without `hit-counter` ever changing.

## "Okay so three pods" — but what were they, exactly?

```bash
kubectl get pods -n daemonset-sidecar-demo
```

```
NAME                                READY   STATUS    RESTARTS   AGE
demo-hit-counter-7d587fd798-9tfgn   2/2     Running   0          50m
demo-node-reporter-n6phj            1/1     Running   0          50m
demo-node-reporter-z4z82            1/1     Running   0          50m
```

- `demo-node-reporter-n6phj` and `demo-node-reporter-z4z82` — the DaemonSet's two Pods, one per
  node.
- `demo-hit-counter-7d587fd798-9tfgn` — the sidecar Pod, `2/2` because it holds two containers.

## "I see three pods running, I don't know what is what"

Same list as above — the fix isn't a different command, it's knowing which columns to read. See
the two sections below (READY, and the name-shape tell) for exactly what to look at.

## "Is a ReplicaSet a Pod?"

No. This came up because `kubectl get all` shows a `replicaset.apps/...` row alongside the
`pod/...` rows, in the same listing:

```bash
kubectl get all -n daemonset-sidecar-demo
```

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

Four different *kinds* of object in one listing — easy to read as "four things running." Only
the `pod/...` rows are Pods (three, matching the first question above). The other three rows are
**controllers**: they supervise Pods, they don't run containers themselves.

The Deployment doesn't create Pods directly — it creates a ReplicaSet, and the ReplicaSet
creates the Pod:

```
Deployment (demo-hit-counter)  →  creates  →  ReplicaSet (demo-hit-counter-7d587fd798)  →  creates  →  Pod
```

Proof, straight from the Pod's own metadata:

```bash
kubectl get pod demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo \
  -o jsonpath='{.metadata.ownerReferences[0]}'
```
```
{"apiVersion":"apps/v1","kind":"ReplicaSet","name":"demo-hit-counter-7d587fd798", ...}
```

Same check on a DaemonSet Pod — no ReplicaSet in the chain at all:

```bash
kubectl get pod demo-node-reporter-n6phj -n daemonset-sidecar-demo \
  -o jsonpath='{.metadata.ownerReferences[0]}'
```
```
{"apiVersion":"apps/v1","kind":"DaemonSet","name":"demo-node-reporter", ...}
```

**Why the extra layer exists at all**: it's what makes a rolling update possible. On a new image,
the Deployment creates a *second*, new-hash ReplicaSet and shifts replica count from the old one
to the new one gradually — old and new Pods coexist mid-rollout. A DaemonSet has no such
"gradual shift between two versions" concept (there's no replica count to shift), so it skips the
ReplicaSet layer and owns its Pods directly.

**Where the hash in the Pod name comes from, now it's obvious**: `demo-hit-counter-`
**`7d587fd798`**`-9tfgn` — that middle segment is the ReplicaSet's own name, embedded in every
Pod name it creates. `demo-node-reporter-n6phj` has no such segment, because there's no
ReplicaSet in its chain to embed.

## "I don't understand the READY part"

`READY` means something different depending on *which* `kubectl get` you're reading — same
column header, two different units being counted.

**On `kubectl get pods`: containers ready in *this one Pod* / total containers in that Pod.**
Nothing to do with replicas.

```
demo-node-reporter-n6phj            1/1   ← 1 container total, 1 ready
demo-hit-counter-7d587fd798-9tfgn   2/2   ← 2 containers total, 2 ready
```

**On `kubectl get daemonset` / `kubectl get deployment`: Pods ready / Pods desired.** A
completely different unit — whole Pods, one level up:

```bash
kubectl get daemonset demo-node-reporter -n daemonset-sidecar-demo
```
```
NAME                 DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE
demo-node-reporter   2         2         2       2            2
```

`READY: 2` here means "2 Pods out of 2 desired," not "2 containers." Reading a controller's
`READY` as if it were a Pod's `READY` (or vice versa) is exactly the trap — same word, different
thing counted.

## "So what are the two containers here?"

Asked about `demo-hit-counter-7d587fd798-9tfgn` specifically, once its `2/2` was understood as
"two containers":

```bash
kubectl get pod demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo \
  -o jsonpath='{.spec.containers[*].name}'
```
```
hit-counter log-tailer
```

- **`hit-counter`** — the "main" container. Writes a timestamped line to
  `/var/log/app/events.log` every 5s. Has no idea a sidecar exists.
- **`log-tailer`** — the sidecar. Tails that same file (shared `emptyDir`) and re-prints each
  line to its own stdout.

Proof they're separate, independently-inspectable containers — `-c` is *required* the moment a
Pod has more than one:

```bash
kubectl logs demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo -c hit-counter
# → empty. It writes to a file, not stdout - see daemonset-sidecar-demo/README.md's
#   "the finding that isn't obvious until you look" section for why that's the actual point.

kubectl logs demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo -c log-tailer
# → [log-tailer] forwarded: ...   one line per line hit-counter wrote to the shared file
```

## "kubectl logs -f" on the sidecar pod, without `-c` — what actually happens?

Ran without specifying which container, on the real cluster:

```bash
kubectl logs -f demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo
```
```
Defaulted container "hit-counter" out of: hit-counter, log-tailer
```
...then nothing, sitting there following an empty stream (Ctrl-C to exit).

Not an error, and not a hang — both are correct. `kubectl logs` on a multi-container Pod without
`-c` doesn't refuse to run; it silently **defaults to the first container listed in the Pod
spec** (`hit-counter` is listed first in `templates/deployment.yaml`) and tells you which one it
picked, right there in that "Defaulted container" line. It then genuinely printed nothing,
because — same fact as the "two containers" section above — `hit-counter` writes to a file, not
stdout, so there's truly nothing on its stream to follow. Pointing `-c` at the other container
instead gets real streaming output:

```bash
kubectl logs -f demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo -c log-tailer
```

## "How to see node name"

Two independent ways to answer "which node is this Pod on," confirming each other:

**1. Ask Kubernetes** — add `-o wide` to see the `NODE` column `kubectl get pods` hides by
default:

```bash
kubectl get pods -n daemonset-sidecar-demo -o wide
```
```
NAME                                READY   STATUS    ...   IP            NODE
demo-hit-counter-7d587fd798-9tfgn   2/2     Running   ...   10.244.1.14   minikube-m02
demo-node-reporter-n6phj            1/1     Running   ...   10.244.1.15   minikube-m02
demo-node-reporter-z4z82            1/1     Running   ...   10.244.0.10   minikube
```

Confirms the DaemonSet behavior directly: `n6phj` on `minikube-m02`, `z4z82` on `minikube` — two
different nodes, one Pod each.

**2. Ask the Pod itself** — `node-reporter`'s whole job is printing its own node name from
*inside* the container:

```bash
kubectl logs -l app=node-reporter -n daemonset-sidecar-demo --prefix --tail=2
```
```
[pod/demo-node-reporter-n6phj/node-reporter] [node-reporter] node=minikube-m02 time=...
[pod/demo-node-reporter-z4z82/node-reporter] [node-reporter] node=minikube time=...
```

It knows this via the Downward API (`NODE_NAME` env var, populated from `spec.nodeName` in
`daemonset-sidecar-demo/templates/daemonset.yaml`) — the same identical image runs on both
nodes and reports something different on each, purely from what Kubernetes tells it about
itself at Pod-start time, not from anything baked in at build time.

## "I don't understand what these pods do, how to connect and test them, how to see sidecar and daemonset, what's so unique about them"

Four questions in one — answered in order, each one live-tested, not just described.

**What each pod actually does, one line each:**

- `node-reporter` (DaemonSet, 2 pods) — prints its own node name + timestamp every 10s. Nothing else.
- `hit-counter` (sidecar pod, main container) — writes a line to a file every 5s, unaware anything else exists.
- `log-tailer` (sidecar pod, sidecar container) — watches that file, echoes new lines to its own stdout.

**Connect and test them directly:**

```bash
kubectl exec demo-node-reporter-z4z82 -n daemonset-sidecar-demo -- env | grep NODE_NAME
```
```
NODE_NAME=minikube
```

```bash
kubectl exec demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo -c hit-counter -- tail -3 /var/log/app/events.log
kubectl exec demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo -c log-tailer  -- tail -3 /var/log/app/events.log
```
```
2026-08-30T16:56:49Z event #512 from demo-hit-counter-7d587fd798-9tfgn
2026-08-30T16:56:54Z event #513 from demo-hit-counter-7d587fd798-9tfgn
2026-08-30T16:56:59Z event #514 from demo-hit-counter-7d587fd798-9tfgn
```

Identical output from both `-c` flags — real proof the two containers share one actual file, not
two separate copies each container thinks is its own.

**How to spot which is which** — already covered above (READY column, name-hash tell). Nothing
new here, just: `1/1` + no hash = DaemonSet pod; `2/2` + hash segment = the sidecar pod.

**What's genuinely unique about each, proven, not just asserted:**

DaemonSet — a deleted Pod's replacement comes back on the *same node*, never a different one:

```bash
kubectl get pod demo-node-reporter-n6phj -n daemonset-sidecar-demo -o jsonpath='{.spec.nodeName}'
```
```
minikube-m02
```
```bash
kubectl delete pod demo-node-reporter-n6phj -n daemonset-sidecar-demo
kubectl get pods -n daemonset-sidecar-demo -o wide -l app=node-reporter
```
```
demo-node-reporter-5lv5q   1/1   Running   ...   minikube-m02   ← new Pod, SAME node
demo-node-reporter-z4z82   1/1   Running   ...   minikube
```

A Deployment's replacement Pod can land on *any* schedulable node (that's the point of
interchangeable replicas). A DaemonSet's replacement is guaranteed back on the exact node it
disappeared from — because the DaemonSet controller's actual job is "keep one Pod running on
*this specific node*," not "keep N Pods running somewhere."

Sidecar — tried to prove independent-container restart with `kubectl exec ... -c log-tailer --
kill -9 1` and hit a real wall instead: it **did not kill the process** (`ps` afterward showed
the same PID 1 still running, `restartCount` stayed `0`). Reason, a genuine Linux/container
internals fact, not a test bug: **PID 1 inside a container has special kernel-level immunity to
unhandled signals — even `SIGKILL` — unless it explicitly traps that signal.** Worth remembering
next time "just `kill -9` it" doesn't behave the way it would outside a container.

## "Why do we use sidecar? Do all containers share something? What happens when one container gets killed?"

Three real questions, answered live — full production-use-case list and the shared-vs-not table
live in [`sidecar-containers.md`](./sidecar-containers.md#what-sidecars-share-with-the-main-container-and-what-they-dont),
this section is the "what happened when actually tested" version.

**Why**, briefly: log shipping (exactly this demo), service mesh proxies (Envoy/Istio), config
sync (this repo's real `grafana-sc-dashboard` example), ambassador/local-proxy patterns — all the
same mechanism, different job.

**Share**: only network (`localhost`) and any volume you explicitly mount into both. Not
filesystem, not process tree, not env vars — those are independent per container.

**Killed one container, for real** — first attempt (`kubectl exec ... -c log-tailer -- kill -9
1`) silently did nothing: PID 1 inside a container is immune to unhandled signals, even
`SIGKILL` (real Linux PID-namespace behavior, not a test bug). Second attempt, correctly this
time — stopped it at the container-runtime level instead:

```bash
minikube ssh -n minikube-m02 -- "sudo crictl ps | grep log-tailer"    # find the container id
minikube ssh -n minikube-m02 -- "sudo crictl stop <container-id>"
```

```bash
kubectl get pod demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}: restarts={.restartCount} started={.state.running.startedAt}{"\n"}{end}'
```

Before → after:
```
hit-counter: restarts=0 started=2026-08-30T15:56:47Z    (unchanged, both times)
log-tailer:  restarts=0 started=2026-08-30T15:56:47Z  →  restarts=1 started=2026-08-30T17:15:06Z
```

`hit-counter` never noticed — its event file kept counting up with no gap right through the
moment `log-tailer` restarted. Pod stayed `Running` the whole time, same name, never recreated.
Only the one container that actually died came back; everything else in the Pod was unaffected.

## "So unless there's pod-level activity, a killed container revives itself without affecting the sidecar" — and how do we actually know which container IS the sidecar?

Close, one refinement: it's the **kubelet** restarting the dead container (per `restartPolicy`),
not the container reviving on its own. Two tiers, worth keeping distinct:

- **Container-level death** (crash, OOM, a runtime-level stop like the test above) → kubelet
  restarts *only that container*, same Pod, same node. Siblings untouched.
- **Pod-level events** — `kubectl delete pod`, node eviction/drain, node failure — take
  *everything* in the Pod down together, no exceptions. A Pod dying takes its whole container
  set with it; a container dying is routine and contained.

**Which container is "main" vs. "sidecar"?** Checked the real pod spec directly:

```bash
kubectl get pod demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo -o jsonpath='{.spec.containers[*].name}'
```
```
hit-counter log-tailer
```
```bash
kubectl get pod demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo -o jsonpath='{.spec.initContainers}'
```
```
(empty)
```

Both containers are just entries in the same flat `.spec.containers` list — **nothing in the
Kubernetes API marks either one as "the sidecar"** for this (plain, pre-1.29) style. It's purely
naming/architectural convention: `log-tailer` sounds like a helper, `hit-counter` sounds like the
actual workload, and whichever one a `Service` would route to is almost certainly the main one.
The one case where Kubernetes *does* know formally: a native sidecar (1.29+) lives in
`spec.initContainers` with `restartPolicy: Always` — that empty result above is the honest
answer for this demo's style, not a missing feature; see `sidecar-containers.md`'s "Native
sidecar containers" section for the form that *is* API-visible.

## Quick reference — every command from this page, in one place

```bash
kubectl get pods -n daemonset-sidecar-demo                      # 3 Pods
kubectl get all -n daemonset-sidecar-demo                       # + the 3 controllers behind them
kubectl get pods -n daemonset-sidecar-demo -o wide               # + NODE column
kubectl get pod <pod> -n daemonset-sidecar-demo \
  -o jsonpath='{.metadata.ownerReferences[0]}'                    # who created this Pod
kubectl get pod <pod> -n daemonset-sidecar-demo \
  -o jsonpath='{.spec.containers[*].name}'                        # containers inside one Pod
kubectl logs <pod> -n daemonset-sidecar-demo -c <container>       # one container's logs
kubectl logs -l app=node-reporter -n daemonset-sidecar-demo --prefix   # all DaemonSet Pods at once
kubectl scale daemonset demo-node-reporter -n daemonset-sidecar-demo --replicas=5
  # → Error: the server could not find the requested resource
  # (DaemonSets have no /scale subresource - "one per node" isn't overridable)
```
