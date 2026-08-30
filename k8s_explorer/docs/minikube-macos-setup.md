# Bootstrapping a fresh multi-node minikube on macOS — the real journey

Companion to [`local-cluster-setup.md`](./local-cluster-setup.md) (the options/reference page)
and [`minikube-linux-bootstrap.md`](./minikube-linux-bootstrap.md) (the same journey on bare
Linux). This one is macOS-specific and narrower: standing up a **2-node** cluster from a
completely clean slate — no prior minikube profile, Docker Desktop's own Kubernetes explicitly
off — command by command, with the real output from actually doing it.

## Why Docker Desktop's own Kubernetes has to be off first

macOS only runs one Docker daemon (Docker Desktop's), and both minikube's `docker` driver and
Docker Desktop's own Kubernetes (`kind` or `kubeadm` mode — see
[`local-cluster-setup.md`](./local-cluster-setup.md#kind-vs-kubeadm-the-provisioner-choice))
use that same daemon underneath. They aren't mutually exclusive in principle, but running both
at once is unnecessary resource contention on a laptop for zero benefit when the goal is one
clean cluster — so: Docker Desktop → Settings → Kubernetes → **Enable Kubernetes unchecked**
before starting anything below. Docker Desktop *itself* (the daemon) still needs to be running —
minikube's `docker` driver depends on it — only its own Kubernetes feature needs to be off.

```bash
docker info >/dev/null 2>&1 && echo "docker daemon: running" || echo "docker daemon: NOT running"
```

If that prints "NOT running," start Docker Desktop and wait for the daemon before continuing —
`minikube start` with the `docker` driver will otherwise fail outright with a connection error
to the Docker socket.

## Starting from a genuinely clean slate

```bash
minikube delete            # if any prior profile exists
minikube status             # confirm nothing's left
```

```
* Profile "minikube" not found. Run "minikube profile list" to view all profiles.
  To start a cluster, run: "minikube start"
```

`docker ps -a --filter "name=minikube"` returning nothing confirms it at the container level
too — no stray `minikube`/`minikube-m02`/`minikube-m03` containers left over from a previous
cluster.

## The one flag that actually matters here: `--driver=docker`

[`local-cluster-setup.md`](./local-cluster-setup.md#minikube-driver-types) already documents
why, from a real incident on this exact machine: on Apple Silicon, minikube's **default**
driver is `vfkit` (one VM per node via Apple's Virtualization framework), and multi-node
clusters on `vfkit` are flaky — see the
[2026-07-28 incident](./incidents.md#2026-07-28-multi-node-minikube-worker-fails-to-join-vfkit-no-route-to-host)
where a worker node failed to join with "no route to host." The fix isn't a retry — it's not
using `vfkit` for multi-node at all. `docker` driver nodes are containers on one Docker bridge
network (`192.168.49.x`), which is reliable container-to-container networking rather than
inter-VM routing.

**Never let `minikube start --nodes=N` auto-pick a driver on this machine — always pass
`--driver=docker` explicitly** when N > 1.

## Creating the cluster

```bash
minikube start --nodes=2 --driver=docker
```

Real output, this run:

```
* minikube v1.37.0 on Darwin 26.6.2 (arm64)
* Using the docker driver based on user configuration
* Using Docker Desktop driver with root privileges
* Starting "minikube" primary control-plane node in "minikube" cluster
* Pulling base image v0.0.48 ...
* Configuring CNI (Container Networking Interface) ...
* Verifying Kubernetes components...
  - Using image gcr.io/k8s-minikube/storage-provisioner:v5
* Enabled addons: storage-provisioner, default-storageclass

* Starting "minikube-m02" worker node in "minikube" cluster
* Pulling base image v0.0.48 ...
* Found network options:
  - NO_PROXY=192.168.49.2
  - env NO_PROXY=192.168.49.2
* Verifying Kubernetes components...

! /usr/local/bin/kubectl is version 1.36.1, which may have incompatibilities with Kubernetes 1.34.0.
  - Want kubectl v1.34.0? Try 'minikube kubectl -- get pods -A'
* Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default
```

Two things worth noticing, both consistent with what `local-cluster-setup.md` predicted:

- **No "no route to host" anywhere** — the exact failure mode the `vfkit` incident hit never
  showed up here, because the driver is different, not because the flag doesn't matter anymore.
- **The kubectl version-skew warning is harmless** — `kubectl` (1.36.1, this machine's Homebrew
  install) being newer than the cluster's Kubernetes (1.34.0) is within Kubernetes' supported
  skew policy (kubectl within one minor version either direction); it's a heads-up, not an error,
  and every command below worked fine despite it.

## Verifying it

```bash
kubectl get nodes -o wide
```

```
NAME           STATUS   ROLES           AGE   VERSION   INTERNAL-IP    EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION    CONTAINER-RUNTIME
minikube       Ready    control-plane   22s   v1.34.0   192.168.49.2   <none>        Ubuntu 22.04.5 LTS   7.0.12-linuxkit   docker://28.4.0
minikube-m02   Ready    <none>          5s    v1.34.0   192.168.49.3   <none>        Ubuntu 22.04.5 LTS   7.0.12-linuxkit   docker://28.4.0
```

Both `192.168.49.x` — the docker-driver bridge subnet, not `192.168.64.x` (vfkit's `vmnet`
range from `local-cluster-setup.md`'s own worked example). That address range alone is a fast
way to sanity-check *which* driver a running cluster actually used, without needing
`minikube profile list`.

```bash
minikube profile list
```

```
┌──────────┬────────┬─────────┬──────────────┬─────────┬────────┬───────┬────────────────┬────────────────────┐
│ PROFILE  │ DRIVER │ RUNTIME │      IP      │ VERSION │ STATUS │ NODES │ ACTIVE PROFILE │ ACTIVE KUBECONTEXT │
├──────────┼────────┼─────────┼──────────────┼─────────┼────────┼───────┼────────────────┼────────────────────┤
│ minikube │ docker │ docker  │ 192.168.49.2 │ v1.34.0 │ OK     │ 2     │ *              │ *                  │
└──────────┴────────┴─────────┴──────────────┴─────────┴────────┴───────┴────────────────┴────────────────────┘
```

`kubectl config current-context` returning `minikube` confirms `minikube start` also wired up
the kubeconfig automatically — no manual `minikube update-context` needed here, unlike the
stale-context scenario `local-cluster-setup.md` walks through (that one only happens when a
profile's kubeconfig entry gets removed independently of the cluster itself, not on a fresh
`start`).

## What's running, on a genuinely empty cluster

```bash
kubectl get pods -A
```

Only `kube-system` pods — `etcd`, `kube-apiserver`, `kube-controller-manager`, `kube-scheduler`,
`coredns`, `kube-proxy` (×2, one per node), `kindnet` (×2), `storage-provisioner`. These are
Kubernetes' own control-plane and networking components, not leftover workloads — a cluster
with *zero* pods isn't a smaller cluster, it's not a working cluster at all. See
[`cluster-architecture.md`](./cluster-architecture.md) for what each of these actually does, and
[`etcd-internals-demo/`](../etcd-internals-demo) to look inside the etcd one directly.

## Next steps in this repo

This 2-node cluster is a clean base for anything else in `k8s_explorer/` that assumes a running
minikube — most demos only need 1 node, but the ones that specifically exercise cross-node
behavior (`kube-proxy-packet-path-demo/`'s load-balancing-across-endpoints demo,
`gpu-scheduling-demo/`'s node-targeted resource patch, `affinity-demo/`) are the ones where a
2nd node actually matters rather than being incidental.
