# Workload types: Deployment, StatefulSet, DaemonSet, Job, CronJob

All five ultimately create Pods; the difference is the *identity and lifecycle guarantee* each
one gives those Pods. Grounded in real workloads already in this repo.

Hands-on companions for the Job/CronJob sections below: [`job-demo/`](../practice/job-demo) — three
manifests covering run-to-completion, retry via `backoffLimit`, and parallel fan-out via
`completions`/`parallelism` — and [`cronjob-demo/`](../practice/cronjob-demo), a scheduled CronJob built
on top of it. Both include `kubectl` commands to watch it happen live.

## Deployment — identical, interchangeable replicas

Covered in depth in [`kubernetes-fundamentals.md`](./kubernetes-fundamentals.md). The default
choice: any replica can be replaced by a fresh one with a new name/IP and nothing downstream
cares (`full-stack-app`'s frontend and backend are both Deployments).

### ReplicaSet — the object actually doing the work underneath

You almost never create one directly (Deployment does it for you — see
[`../daemonset-sidecar-walkthrough.md`](./daemonset-sidecar-walkthrough.md#is-a-replicaset-a-pod)
for the real, live-verified `ownerReferences` proof of the Deployment → ReplicaSet → Pod chain),
but it's worth being explicit about *why* this extra layer exists instead of Deployment just
managing Pods directly. Five real production needs, each one a genuine capability that would be
lost without it:

1. **Self-healing when a Pod dies for reasons that have nothing to do with your code** — an OOM
   kill, a node losing power, a spot instance getting reclaimed mid-run. The ReplicaSet's whole
   reconcile loop is "does actual replica count match desired," so a Pod disappearing for *any*
   reason gets a replacement within seconds, with no on-call page needed. This is the same
   reconcile-loop mechanism [`../practice/toy-controller/`](../practice/toy-controller) builds by hand for a
   Namespace's `ResourceQuota` — a ReplicaSet is that same pattern, applied to Pod replica count.
2. **Rolling updates without downtime.** This is the actual reason the ReplicaSet layer exists at
   all rather than Deployment editing Pods in place: on a new image, Deployment creates a
   *second*, new-hash ReplicaSet and shifts replica count from the old one to the new one
   gradually — old and new Pods coexist mid-rollout, so traffic never drops to zero. Without a
   separate addressable object per "version," there'd be nothing to gradually shift between.
3. **HorizontalPodAutoscaler-driven scaling under real traffic.** HPA never touches Pods
   directly — it edits the Deployment's `replicas:` field, and the ReplicaSet is what actually
   reconciles that into real Pods. A Black Friday traffic spike pushing CPU past a threshold
   turns into "20 more Pods, created within seconds" purely because this reconciliation exists;
   see [`resource-management.md`](./resource-management.md) for the HPA side of this.
4. **Zero-downtime node maintenance.** Cordoning and draining a node for a Kubernetes upgrade or
   hardware replacement evicts every Pod on it. The ReplicaSet notices desired-vs-actual drift
   immediately and reschedules replacements onto surviving nodes — the *service* keeps its full
   replica count the whole time, even though individual Pods are actively churning underneath.
5. **High availability across failure domains, combined with anti-affinity.** Spread 3 replicas
   across 3 AZs with pod anti-affinity (see [`pod-and-node-affinity.md`](./pod-and-node-affinity.md),
   worked hands-on in [`../practice/affinity-demo/`](../practice/affinity-demo)) and lose a whole AZ — 2 replicas
   keep serving, and once capacity returns, the ReplicaSet is what actually creates the missing
   replica again. Anti-affinity only decides *where* replacements can go; the ReplicaSet is what
   notices one is needed and creates it.
6. **What progressive-delivery tooling (Argo Rollouts, Flagger, canary releases) is built on.**
   A canary controller shifts traffic gradually from an old ReplicaSet's Pods to a new one's —
   only possible because ReplicaSets are separate, individually-addressable objects a controller
   can point a fraction of traffic at, not because Deployment has any special canary feature of
   its own.

## StatefulSet — replicas with stable identity

```yaml
# full-stack-app/charts/database/templates/statefulset.yaml
spec:
  serviceName: {{ include "database.fullname" . }}
  replicas: 1
  volumeClaimTemplates:
    - metadata: {name: data}
      spec: {accessModes: ["ReadWriteOnce"], resources: {requests: {storage: ...}}}
```

Used for the Postgres database. What a StatefulSet guarantees that a Deployment doesn't:

- **Stable, predictable Pod names**: `<name>-0`, `<name>-1`, ... (not a random suffix) — and
  each keeps that name across restarts/rescheduling.
- **A PVC per replica** (via `volumeClaimTemplates`, see
  [`storage-and-persistence.md`](./storage-and-persistence.md)) that follows that specific
  ordinal, not a shared volume — replica `-0` always reattaches to the same disk.
  A Deployment has no such concept; if you gave multiple Deployment replicas a shared PVC, they'd
  all be fighting over the same disk (and it'd need to be RWX, which most cloud block storage
  isn't).
- **Ordered, sequential rollout/scaling** by default (`0` before `1` before `2`, and scale-down
  in reverse) — relevant for things like a replicated database where node `0` needs to be up
  before `1` joins.
- A **headless Service** (`clusterIP: None`, set via `serviceName`) gives each replica its own
  stable DNS name (`<pod>.<service>.<namespace>.svc.cluster.local`), so clients can address a
  *specific* replica instead of "any of them" — meaningless for a stateless web server, essential
  for e.g. talking to a database's primary specifically.

This repo's Postgres uses `replicas: 1`, so a lot of that (ordered rollout, per-replica DNS)
isn't really exercised — the reason it's still a StatefulSet and not a Deployment is the
per-replica PVC guarantee: even at one replica, that guarantee is what makes the data volume
Postgres owns be *the same* volume across every restart.

For all four guarantees actually exercised and verified against a real 3-replica cluster —
ordered creation, per-replica DNS, a deleted Pod reattaching to its same PVC, reverse-order
scale-down — see [`statefulset-walkthrough.md`](./statefulset-walkthrough.md) and its hands-on
companion [`../practice/statefulset-identity-demo/`](../practice/statefulset-identity-demo).

## DaemonSet — exactly one Pod per node

This cluster already runs some — real, verified, not hypothetical:

```bash
kubectl get daemonset -A
```
```
NAMESPACE     NAME         DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
kube-system   kindnet      2         2         2       2            2          <none>
kube-system   kube-proxy   2         2         2       2            2          kubernetes.io/os=linux
```

Used for node-level agents: anything that needs to run on *every* node, automatically added/
removed as nodes join/leave, rather than a chosen replica count. Try it hands-on in
[`daemonset-sidecar-demo/`](../practice/daemonset-sidecar-demo) — no `replicas` field at all (there isn't
one on the DaemonSet spec), a real 2-node cluster produces exactly 2 Pods, and each one learns
which node it landed on via the Downward API rather than any per-node image/config.

### Real production use cases — why this workload type has to exist

Every one of these needs the same guarantee: *exactly* one per node, not "roughly enough,"
because missing even a single node breaks something in a way a higher replica count on other
nodes can't compensate for.

1. **CNI networking — `kindnet` above, on this exact cluster.** Every node needs its own CNI
   plugin Pod to set up Pod networking on that node specifically. Without it, no Pod scheduled
   there gets a network at all — this isn't optional infrastructure, it's the thing that makes
   the node usable for scheduling anything.
2. **Service routing — `kube-proxy` above, same cluster.** [`../practice/kube-proxy-packet-path-demo/`](../practice/kube-proxy-packet-path-demo)
   traced exactly what this Pod does: program the `iptables`/IPVS rules that turn a ClusterIP
   into a real Pod IP. A node without its own kube-proxy Pod can't route Service traffic at all —
   again, per-node, not a cluster-wide replica count that could be satisfied by Pods elsewhere.
3. **Log collection (Fluentd/Fluent Bit/Promtail).** Container logs live on each node's *local*
   disk (`/var/log/containers/`) — a collector has to run where the logs physically are. A
   DaemonSet guarantees coverage without anyone needing to know the node count in advance or
   manually deploying N collectors to N nodes as the cluster scales.
4. **Node-level metrics (`node-exporter`).** Needs to scrape *that node's* CPU/memory/disk
   directly. Two on one node double-counts; zero on a node makes it invisible to monitoring —
   DaemonSet is the only workload type that gives the "exactly one, everywhere" guarantee
   natively rather than as something you have to engineer.
5. **Runtime security/compliance agents** (Falco, CrowdStrike, Aqua) watching syscalls on every
   node for intrusion detection. Compliance requirements typically demand *all* nodes covered,
   not "most" — a Deployment with `replicas: 10` on a 12-node cluster gives no guarantee which
   2 nodes are uncovered, or that it stays that way as nodes are added.
6. **CSI storage node-plugins.** The component that actually mounts/unmounts a volume onto a
   given node has to run on that node — [`eks-setup.md`](./eks-setup.md)'s EBS CSI driver ships
   its node-level component as a DaemonSet for exactly this reason; a Pod requesting a volume on
   a node with no CSI node-plugin there just sits stuck.
7. **GPU device plugins** — [`../practice/gpu-scheduling-demo/`](../practice/gpu-scheduling-demo) covers the
   scheduling side of this; the real NVIDIA/AMD device plugin that *advertises* those extended
   resources to the kubelet runs as a DaemonSet, one per GPU-equipped node, because GPU discovery
   is inherently local to whatever hardware is physically in that node.

## Job — run to completion, once

```yaml
# full-stack-app/templates/migration-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  annotations:
    helm.sh/hook: post-install,pre-upgrade
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          command: ["sh", "-c", "... psql ... INSERT INTO demo_items ..."]
```

Runs the DB schema/seed migration exactly once per install/upgrade (note `restartPolicy: Never`
— a Job's Pod isn't restarted in place on failure, the **Job controller** creates a new Pod, up
to `backoffLimit` attempts). The `helm.sh/hook` annotations aren't a Kubernetes concept — they're
Helm's mechanism for running this Job at a specific point in the install/upgrade lifecycle
(after install, before upgrade) rather than as a normal templated resource.

Try it hands-on in [`job-demo/`](../practice/job-demo) — including what a failed attempt and a parallel
fan-out actually look like in `kubectl get pods`, not just in the YAML.

## CronJob — a Job, on a schedule

```yaml
# full-stack-app/templates/backup-cronjob.yaml
spec:
  schedule: "0 2 * * *"          # standard cron syntax
  concurrencyPolicy: Forbid       # don't start a new run if the previous is still going
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec: { ... same shape as a Job ... }
```

The CronJob controller creates a new `Job` object (which then creates Pods, same as any Job) at
each scheduled tick. `concurrencyPolicy: Forbid` matters here specifically because it's a
database backup — two overlapping `pg_dump` runs racing against each other is worse than a
missed run. Trigger one on demand for testing without waiting for the schedule:

```bash
kubectl create job --from=cronjob/<release>-db-backup manual-backup-1 -n <namespace>
```

Try it hands-on in [`cronjob-demo/`](../practice/cronjob-demo).

## Choosing between them

| Need | Use |
|---|---|
| Stateless, interchangeable replicas | Deployment |
| Stable identity / one-volume-per-replica (databases, brokers) | StatefulSet |
| One Pod per node (agents, log/metrics shippers) | DaemonSet |
| Run once, to completion (migrations, batch processing) | Job |
| Run on a schedule | CronJob |

## Quick reference

```bash
kubectl get deploy,sts,ds,job,cronjob -n <namespace>
kubectl rollout status deployment/<name>
kubectl rollout status statefulset/<name>
kubectl logs job/<name>
```
