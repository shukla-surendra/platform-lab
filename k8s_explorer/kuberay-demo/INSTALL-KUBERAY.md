# Installing KubeRay locally — what we hit

## 1. `minikube status` / `kubectl get nodes` refused the connection

```
Cannot connect to the Docker daemon at unix:///Users/.../docker/run/docker.sock.
Is the docker daemon running?
```

**Why:** Docker Desktop wasn't running. minikube's `docker` driver runs cluster nodes
as containers on the host's Docker daemon — no daemon, no cluster, regardless of what
`minikube profile list` shows as the last-known state.

**Fix:** `open -a Docker`, then poll `docker info` until it succeeds before touching
minikube at all.

## 2. Cluster died mid-install, right after the operator's `helm install` returned

```
kubectl get pods -n kuberay
The connection to the server 127.0.0.1:<port> was refused
```

`docker ps -a` showed all three minikube containers `Exited (137)` (SIGKILL) seconds
after they'd been reported `Ready`.

**Why:** Docker Desktop auto-updated itself in the background right after being
launched (client version moved 29.6.1 → 29.7.2 mid-session) and restarted its Linux
VM to apply it — which SIGKILLed every container running inside, including all three
minikube nodes. This is a Docker Desktop behavior, not a minikube or KubeRay issue;
it's easy to misread as a cluster crash caused by the install itself.

**Fix:** `minikube start` again once `docker info` is healthy. The KubeRay operator's
Helm release survives (it's cluster state, not local state) — the operator Pod came
back on its own once the cluster did.

## 3. Which Ray/KubeRay versions

- KubeRay operator + CRDs: chart `kuberay/kuberay-operator` `1.7.0` (latest stable on
  the `kuberay-helm` repo at the time).
- Ray image: `rayproject/ray:2.40.0` for both head and worker (moved off `2.9.3`, see
  §6) — pin head and worker to the *same* Ray version; a mismatch fails at worker
  registration, not at pod startup, so it looks like a networking problem if you
  don't check versions first.

## 4. `kubectl exec ... python some_script.py` inside the head pod crashes the raylet

Running a Ray script by `kubectl exec`-ing straight into the head container
(`ray.init(address="auto")` then submitting tasks) reliably triggered:

```
raylet.err: The raylet exited immediately because one Ray agent failed,
  agent_name = dashboard_agent/<pid>
```

...followed by the driver process itself failing with a node-IP mismatch error
(`Connected to GCS at X, found raylets at Y, but none match this node's IP X`).
Every time this happened, the container then crash-looped a few more times before
stabilizing (or not).

**Why:** unclear at the C++ level — the `dashboard_agent` and the local raylet
"fate-share" (one dying kills the other), and something about a driver invoked this
way (rather than through Ray's own job-submission path) triggers that. Not
conclusively root-caused; treat it as a hard "don't do this" rather than a fixable
config issue.

**Fix:** never `kubectl exec` a Python script directly into a Ray container. Use
`kubectl cp` to place a script on the pod (safe — it's just a file write, no Ray code
runs) and drive it via the Jobs API/CLI from outside, or connect via the Ray client
port (10001) from a script running outside the cluster entirely.

## 5. Readiness/liveness probe flapping under host CPU load

KubeRay's default probes on both containers are tight:

```
wget --tries 1 -T 2 -q -O- http://localhost:52365/api/local_raylet_healthz | grep success
```

That inner `-T 2` (2-second) timeout has no slack. Any time the Mac was under real
CPU load nearby — `minikube addons enable metrics-server` pulling an image, a local
`pip install`, even a `kubectl exec` running concurrently — the wget inside the
container missed that window and kubelet logged `Unhealthy` events, occasionally
tipping into full container restarts (`Back-off restarting failed container`,
exit code 1, reason `Error`).

**Why:** minikube's docker driver runs every node as a container inside Docker
Desktop's Linux VM, sharing the same CPU cores as everything else on the host. A
2-second exec-probe timeout that's fine on a dedicated node is not generous on a
personal laptop doing other things at the same time.

**Fix:** none applied in `raycluster.yaml` (the default operator probes are used
as-is) — just be aware that running heavy commands (image pulls, `pip install`,
`kubectl exec`) *while* the cluster is mid-startup or under test is what causes the
flapping, not the cluster itself. Give it a minute of quiet after `kubectl apply`
before judging it stable.

## 6. Job submission (`ray job submit` / REST `/api/jobs/`) doesn't work here

Confirmed broken on **both** Ray 2.9.3 and 2.40.0, with head+worker scheduled on the
same minikube node and on different nodes (ruling out cross-node CNI networking as
the cause). Every attempt — CLI, and a raw REST `POST /api/jobs/` — fails the same
way:

```
RuntimeError: Request failed with status code 500: ...
aiohttp.client_exceptions.ServerDisconnectedError: Server disconnected
```

Tracing it: the dashboard's job HTTP head (`job_head.py`, port 8265) receives the
submit request fine, uploads the working-dir package fine, then internally proxies
the actual job creation to the `JobAgent` (port 52365, same pod). The `JobAgent`'s
own log (`dashboard_agent.log`) shows it getting as far as calling `ray.init()` to
connect to its own cluster (`Connected to Ray cluster` is the last line logged) —
and then nothing. No exception, no traceback anywhere in `dashboard_agent.log`,
`raylet.err`, or the (empty) `agent-*.err`/`agent-*.out` files. The pod itself stays
`1/1 Running` throughout — this isn't a container crash, just that one request
silently dying mid-handler.

**Why:** best guess, not confirmed — the `JobAgent.submit_job` handler calls
`ray.init()` *from inside its own already-running asyncio event loop*, which is an
unusual thing to do (a driver connecting to a cluster from inside a process that's
already part of that cluster). A crash with zero Python-level exception logged is
consistent with a native/C++-level crash (segfault) in the raylet extension at that
point, rather than an application bug reachable from the YAML or the client side.
Given it reproduces identically across 2 Ray versions and both single- and
multi-node topology, this looks like an environment-specific interaction (this
specific minikube/Docker-Desktop/docker-driver combination) rather than a Ray
release bug.

**Not a fix, but not blocking either:** everything except job submission works —
`kubectl get raycluster -o wide`, the dashboard's Overview/Cluster/Nodes tabs, and
`kubectl exec ... ray status` (a read-only CLI command, safe unlike running a script)
all correctly reflect the live cluster. If this is worth resolving later, the next
useful data point would be watching the `JobAgent` process (not the raylet) with
`strace`/a debugger at the moment of the crash — not attempted here, out of scope
for a first pass at this demo.

## Real EKS difference

Locally, `minikube start` gives every node the full host's CPU/memory as
"allocatable," so resource requests barely register. On a real cluster, size
`headGroupSpec`/`workerGroupSpecs` requests deliberately (the head especially — GCS
plus the dashboard need real memory under load) and consider a dedicated node pool /
taint so Ray workers don't compete with unrelated workloads for scheduling.
