# Bootstrapping minikube on Linux — from a bare machine to a running cluster

Command-by-command notes for standing up a cluster on a Linux box from scratch (Docker not
yet installed, no `kubectl`, no `minikube`). [`local-cluster-setup.md`](./local-cluster-setup.md)
compares local-cluster *options* on macOS (minikube vs. Docker Desktop vs. kind vs. k3d) and
assumes one is already installed via Homebrew — this doc is the Linux/systemd install path
underneath one of those options, plus what each step is actually doing on the machine.

For what the components this creates (`kube-apiserver`, `etcd`, `kubelet`, ...) actually do,
see [`cluster-architecture.md`](./cluster-architecture.md) — this doc is about getting them
running, not what they're for.

## 1. Get a container runtime running: Docker

```bash
sudo systemctl enable --now docker
```

| Piece | Meaning |
|---|---|
| `sudo` | Run as administrator — starting/enabling a system service requires root. |
| `systemctl` | The CLI for `systemd`, the service manager that starts/stops/monitors daemons on most modern Linux distros. |
| `enable` | Register `docker` to start automatically on every future boot (writes a symlink under `/etc/systemd/system/`). Without this, Docker would need to be started by hand after every reboot. |
| `--now` | Also start it *immediately*, instead of only taking effect on the next reboot — `enable` alone just registers it. |
| `docker` | The systemd unit name for the Docker daemon. |

**What actually happens:** `systemctl` asks `systemd` (PID 1) to launch `dockerd` (the Docker
daemon). `dockerd` starts listening on `/var/run/docker.sock` — a Unix socket, not a network
port — which is what every `docker` CLI command and, critically, minikube's `--driver=docker`
talks to. If `dockerd` isn't running, minikube has nothing to create node containers *in* —
`minikube start --driver=docker` fails immediately.

```bash
sudo usermod -aG docker $USER
```

Adds your user to the `docker` group so you can run `docker`/`minikube` commands without
prefixing every one with `sudo` (group membership is what the socket's permissions check
against). `-a` = append (don't remove existing groups), `-G` = the group(s) to add. **Takes
effect on your next login/shell**, not immediately — group membership is read when a session
starts, so an already-open terminal won't see it until you log out and back in (or run
`newgrp docker` as a shortcut).

## 2. Install the CLIs

### minikube

```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

`curl -L` follows redirects (the "latest" URL 302s to a versioned file), `-O` saves it under
its original filename instead of dumping to stdout. `install` (not just `cp`) copies the
binary, sets it executable (`chmod +x` behavior baked in), and places it on `/usr/local/bin`,
which is already on `$PATH` on most distros — that combination is why `install` is preferred
over a plain copy for CLI binaries.

### kubectl

```bash
sudo snap install kubectl --classic
```

`kubectl` is just an HTTPS client — every command it runs serializes to a REST call against
`kube-apiserver`, authenticated using whatever's in `~/.kube/config` (see the context section
in [`local-cluster-setup.md`](./local-cluster-setup.md#understanding-kubectl-context)).
`--classic` disables snap's usual sandboxing — required here because `kubectl` needs to read
files anywhere on the filesystem (kubeconfig, manifests you point it at), not just its own
snap directory.

## 3. Create the cluster

```bash
minikube start --driver=docker --nodes 2
```

Creates one control-plane node and one worker node, **each as its own Docker container**
(that's what `--driver=docker` means — vs. a VM driver like vfkit/hyperkit/virtualbox on
other platforms). See [`cluster-architecture.md`](./cluster-architecture.md) for what runs on
each: `kube-apiserver`/`etcd`/`kube-scheduler`/`kube-controller-manager` on the control-plane
node, `kubelet`/`kube-proxy`/the container runtime on every node including workers.

## 4. Verify it

```bash
kubectl get nodes
```

Lists `Node` objects as stored in the API server — `kubectl` never talks to a node directly,
it only ever reads/writes objects through `kube-apiserver`. `STATUS=Ready` means that node's
`kubelet` is checked in and healthy; a node stuck `NotReady` means the API server hasn't heard
a recent heartbeat from that node's kubelet.

```bash
minikube status
```

Unlike `kubectl get nodes` (API-server's view), this checks minikube's own view of the host:
is the VM/container up, is `kubelet` running inside it, is the API server responding, is your
kubeconfig pointed at it correctly. Useful when `kubectl` itself is failing to connect and you
need to know which layer is actually down.

```bash
kubectl get pods -n kube-system
```

Lists the cluster's own system Pods — the control-plane components above aren't magic, they
run as ordinary Pods in the `kube-system` namespace:

| Pod | Job |
|---|---|
| `etcd-*` | The state store — see [`cluster-architecture.md`](./cluster-architecture.md#control-plane). |
| `kube-apiserver-*` | Front door for every request, including `kubectl` itself. |
| `kube-scheduler-*` | Assigns unscheduled Pods to Nodes. |
| `kube-controller-manager-*` | Runs the reconciliation loops (Deployment → ReplicaSet → Pod, etc). |
| `kube-proxy-*` | Programs the Service load-balancing rules on every node — see [`service-types.md`](./service-types.md). |
| `coredns-*` | Cluster DNS — resolves Service names like `web-clusterip` to an IP. |
| `storage-provisioner` | minikube-specific — backs the default `StorageClass` with `hostPath` volumes; see [`storage-and-persistence.md`](./storage-and-persistence.md). |

## 5. Scaling the cluster itself (nodes, not Pods)

```bash
minikube node add
```

Adds one more worker node/container to the **already-running** cluster — useful for testing
things that only show up with more than one node, e.g. the pod anti-affinity scenario in
[`pod-and-node-affinity.md`](./pod-and-node-affinity.md) (worked hands-on in
[`affinity-demo/`](../affinity-demo)'s Part 3b).

```bash
minikube delete
minikube start --nodes 3
```

`minikube delete` tears down the *entire* profile — every node container, its state, gone.
There's no "resize an existing cluster's node *count* down" or "change CPU/memory of an
existing profile" operation; those are set at `minikube start` time and are immutable
afterward (see Common Errors below). Getting a 3-node cluster from a 2-node one this way means
delete-then-recreate, not a live resize.

## Contexts (quick reference)

```bash
kubectl config current-context
kubectl config get-contexts
kubectl config use-context minikube
kubectl config set-context --current --namespace=test
```

`use-context` switches which cluster/user/namespace triple `kubectl` targets by default;
`set-context --current --namespace=test` changes only the namespace half of *that* context,
leaving cluster/user alone. Full explanation of what a context actually is (and a real
incident where one silently went stale) is in
[`local-cluster-setup.md`](./local-cluster-setup.md#understanding-kubectl-context) — worth
reading before you're debugging a "wrong cluster" mistake at 2am.

## Common errors

**`Profile "minikube" not found`** — no cluster exists yet under that profile name. Run
`minikube start` (add `-p <name>` for a non-default profile).

**Can't change `--cpus`/`--memory` on an existing cluster** — these are baked into the
profile at `minikube start` time, not live-adjustable settings. The only fix is
`minikube delete` (or `-p <profile>`) and `minikube start --cpus=... --memory=...` again.

## Recommended next steps in this repo

Rather than a generic checklist, these already exist here and build on each other:

1. [`sample-nginx/`](../sample-nginx) — a Deployment, exposing it, adding an Ingress.
2. [`services-demo/`](../services-demo) — every Service `type` (`ClusterIP`, `NodePort`,
   `LoadBalancer`, headless, `ExternalName`) side by side, whose README includes a command/
   flag glossary for exactly this kind of "what does this flag mean" question.
3. [`affinity-demo/`](../affinity-demo) — node/pod affinity and anti-affinity, including the
   multi-node scenario `minikube node add` (above) sets up for.
4. [`configmaps-and-secrets.md`](./configmaps-and-secrets.md) and
   [`probes-and-health-checks.md`](./probes-and-health-checks.md) — rounds out config and
   rollout-safety basics before moving to [`eks-setup.md`](./eks-setup.md) for a real cloud
   cluster.
