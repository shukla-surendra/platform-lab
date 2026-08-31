# Sidecar containers

A sidecar is a **second container in the same Pod** that helps the main container without being
part of the application's own code. This repo already runs one for real — Grafana's dashboard/
datasource sidecar in [`grafana-log-viewer`](../grafana-log-viewer), covered end-to-end in
[`grafana-dashboard-provisioning.md`](./grafana-dashboard-provisioning.md). This page is the
general concept; that page is the worked example.

For the specific, most common sidecar shape — a **log-shipping sidecar** reading whatever the
main container already writes to disk — see [`daemonset-sidecar-demo/`](../daemonset-sidecar-demo)
instead: two from-scratch local images sharing one `emptyDir`, with a real, load-bearing finding
that isn't obvious until you see it — `kubectl logs` on the *main* container comes back
completely empty, because it writes to a file, not stdout. The sidecar reading that file is the
only reason the data is visible via `kubectl logs` at all.

## For beginners: what's a Pod, a container, and a "sidecar"?

If "Pod" and "container" are still a little fuzzy, start here before the technical sections below.

**A container** is a packaged-up program — your app plus everything it needs to run (code,
libraries, runtime) — bundled so it runs the same way anywhere. Think of it as a shipping
container: whatever's inside, it has a standard shape that any ship, truck, or crane can handle.

**A Pod** is Kubernetes' way of running one or more containers together as a single unit. Most of
the time a Pod has exactly one container, and "Pod" and "container" feel interchangeable. But
Kubernetes never schedules a bare container by itself — it always schedules a Pod, even if that
Pod happens to wrap just one container.

Picture a Pod as **one hotel room**. Containers inside it are like people sharing that room:

- They share the same **address** (network) — like roommates sharing one street address and
  phone line, containers in a Pod share one IP address and can reach each other over `localhost`.
- They can share the same **stuff in the room** (storage) — a shared `volume` is like a shared
  desk both roommates can put papers on and both can read from.
- They **check in and check out together** — the Pod is created and destroyed as a whole; you
  don't get to evict one roommate while the room itself stays booked (native sidecars, below,
  bend this slightly, but the Pod is still the unit Kubernetes manages).

Now, **a sidecar** is just a name for a *helper* roommate — one who isn't the guest the room was
booked for, but who makes the main guest's stay work better:

- The main container is the guest: it's *why* the room exists (your actual application).
- The sidecar is like room service or a personal assistant riding along: it doesn't do the
  guest's job, but it quietly handles something around it — collecting the guest's trash
  (logs), watching the door and screening visitors (network proxy), or restocking the minibar
  from a separate supply (syncing config/secrets in from outside).

The literal analogy the name comes from: a **motorcycle sidecar**. The motorcycle (main
container) still drives and steers; the sidecar (helper container) rides attached to it,
along for the same journey, carrying something extra. It doesn't work without the motorcycle,
and it never was the motorcycle.

Concretely, in this repo: the `grafana` container in `grafana-log-viewer` is the "motorcycle" —
it serves the actual Grafana UI. Riding alongside it is a `grafana-sc-dashboard` container (the
"sidecar") whose only job is to notice when you've added a new dashboard `ConfigMap` and drop
its JSON onto a shared folder so Grafana picks it up — Grafana itself never talks to Kubernetes
at all; the sidecar does that on its behalf. See
[`grafana-dashboard-provisioning.md`](./grafana-dashboard-provisioning.md) for the full trace of
that, including live `kubectl` output.

That's the whole concept. Everything below is the same idea, formalized.

## Why put a helper in the same Pod instead of its own Deployment?

Because a sidecar's whole value is being *inseparable* from the container it helps — same
network, same volumes, same up/down lifecycle. If the log shipper and the app were separate
Pods, the shipper would need some other way to find the app's logs (a shared PVC across Pods,
extra networking) and could be scheduled onto a different Node entirely. Putting them in one
Pod makes "always co-located, always sharing files/network" true by construction rather than
something you have to engineer.

## What sidecars share with the main container — and what they don't

| Shared resource | Mechanism |
|---|---|
| Network | Same Pod IP — containers reach each other over `localhost:<port>` |
| Storage | Common `volumes:` entries, mounted into both containers' `volumeMounts` — and *only* the ones you explicitly declare |
| Lifecycle | Historically: created/destroyed together. With native sidecars (below): ordered but still tied to the Pod |

Everything else is **independent per container**, easy to assume is shared and isn't:
filesystem/image (each container's own root filesystem, unrelated to the other unless a volume
is mounted into both), process tree (each container gets its own PID 1 and its own PID
namespace, unless `shareProcessNamespace: true` is set on the Pod spec), environment variables,
and resource requests/limits.

## What happens when one container gets killed?

Verified against [`../daemonset-sidecar-demo/`](../daemonset-sidecar-demo)'s real running Pod —
stopped the `log-tailer` container directly at the container-runtime level (`crictl stop` on the
node, not a signal from inside — a signal doesn't work here: PID 1 inside a container is immune
to unhandled signals, *even* `SIGKILL`, a real documented Linux PID-namespace behavior, confirmed
empirically when `kubectl exec ... -c log-tailer -- kill -9 1` did nothing at all):

```bash
kubectl get pod demo-hit-counter-7d587fd798-9tfgn -n daemonset-sidecar-demo \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}: restarts={.restartCount} started={.state.running.startedAt}{"\n"}{end}'
```

Before:
```
hit-counter: restarts=0 started=2026-08-30T15:56:47Z
log-tailer: restarts=0 started=2026-08-30T15:56:47Z
```

After stopping only `log-tailer`'s container:
```
hit-counter: restarts=0 started=2026-08-30T15:56:47Z
log-tailer: restarts=1 started=2026-08-30T17:15:06Z
```

- **Only `log-tailer` restarted** — new timestamp, `restartCount` incremented.
- **`hit-counter` was completely untouched** — identical `restartCount` and start time as before.
- **The Pod itself never left `Running`, never got recreated** — same name, same age; the Pod-level
  `RESTARTS` column is just the sum across its containers, not proof the Pod was reborn.
- **`hit-counter` never even noticed** — its event file kept incrementing with no gap right through
  the exact moment `log-tailer` was killed and restarted.

The rule this proves: **kubelet supervises each container in a Pod independently.** One crashing
(a real crash, an OOM, or this test's runtime-level stop) only restarts *that* container, per the
Pod's `restartPolicy` — the Pod's identity, IP, and every sibling container are unaffected. This
is the actual practical reason sidecars are considered safe to add: a buggy log shipper
crash-looping doesn't take the real application down with it.

## Common use cases

| Pattern | What it does | Example |
|---|---|---|
| Config/secret sync | Watches the K8s API for labeled resources, writes matches to a shared volume | `grafana-sc-dashboard` in this repo's [`grafana-log-viewer`](../grafana-log-viewer) — see [`grafana-dashboard-provisioning.md`](./grafana-dashboard-provisioning.md) |
| Logging | Tails the app's log files from a shared volume, ships them elsewhere | Fluent Bit/Filebeat sidecar shipping to Loki |
| Service mesh proxy | Intercepts all in/out traffic for mTLS, retries, metrics | Envoy (Istio), Linkerd's proxy |
| Ambassador | Proxies outbound calls on the main container's behalf | Local proxy fronting an external DB/API |
| Adapter | Normalizes the main container's output into a format something else expects | Metrics-format translator sitting in front of a scraper |

Ambassador and adapter are really just sidecars with a specific job description — the mechanism
(second container, shared network/volumes) is identical in all five rows above.

## Native sidecar containers (Kubernetes 1.29+)

Before 1.29, a "sidecar" was just an ordinary entry in `containers:` — Kubernetes had no concept
of ordering, so a logging sidecar could be killed before the main container finished writing its
last log line, or a proxy sidecar might not be ready yet when the main container's first request
came in.

Kubernetes 1.29 made sidecars a first-class idea via `initContainers` with
`restartPolicy: Always`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-sidecar
spec:
  initContainers:
    - name: logging-sidecar
      image: fluent/fluent-bit
      restartPolicy: Always   # <- this is what makes it a sidecar, not a one-shot init container
      volumeMounts:
        - name: logs
          mountPath: /var/log/app
  containers:
    - name: app
      image: myapp:latest
      volumeMounts:
        - name: logs
          mountPath: /var/log/app
  volumes:
    - name: logs
      emptyDir: {}
```

What that buys you over a plain `containers:` entry:

- **Starts first, and must be ready before the main container starts** — no more racing a proxy
  or log shipper against the app's first request.
- **Keeps running for the Pod's life**, restarting on its own if it crashes (unlike a normal init
  container, which runs once to completion and exits).
- **Stops last**, in reverse order, when the Pod terminates — so it can flush a final batch of
  logs/metrics before going away.
- **Plays correctly with `Job`** — the Job is considered complete once the main container exits,
  even if the sidecar (still `restartPolicy: Always`) is technically still running.

Grafana's `k8s-sidecar` image (used in `grafana-log-viewer`, per the chart's own defaults) still
runs as a regular `containers:` entry rather than this native form — it's a long-running watch
loop, so the old ordering gap matters less there, but it's the kind of container that would be a
strong candidate for the native form if the upstream chart adopted it.

## Sidecar vs. init container vs. ambassador/adapter

| | Runs for | Purpose |
|---|---|---|
| Init container (plain) | Until it exits, before app containers start | One-time setup (e.g. wait-for-dependency, migrate) — no ongoing role |
| Sidecar (native, `restartPolicy: Always`) | The whole Pod lifetime | Ongoing helper alongside the app |
| Sidecar (plain `containers:` entry) | The whole Pod lifetime, no start/stop ordering guarantee | Same as above, pre-1.29 style |
| Ambassador | Same as sidecar | A sidecar specialized for proxying outbound network calls |
| Adapter | Same as sidecar | A sidecar specialized for reshaping the app's output |

## Quick reference

```bash
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].name}'       # list containers in a Pod
kubectl logs <pod> -c <sidecar-container-name>                       # sidecar's own logs
kubectl exec <pod> -c <sidecar-container-name> -- <cmd>               # shell into just the sidecar
kubectl get pod <pod> -o jsonpath='{.spec.initContainers[*].name}'   # native sidecars show up here, not .spec.containers
```

## Summary

| Concept | One-line meaning |
|---|---|
| Pod | The Kubernetes unit that groups one or more containers sharing network + storage |
| Container | A packaged app/process running inside a Pod |
| Sidecar | A helper container in the same Pod, riding alongside the main one |
| Native sidecar (1.29+) | A sidecar declared via `initContainers` + `restartPolicy: Always`, with real startup/shutdown ordering |
| Ambassador / adapter | Sidecars specialized for proxying / reshaping traffic, respectively |

Worked, verified-on-a-live-cluster example: [`grafana-dashboard-provisioning.md`](./grafana-dashboard-provisioning.md).
