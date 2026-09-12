# Node Anatomy: Everything Present on a Bare AKS Node, Explained

Everything below exists on this cluster's nodes **with zero workloads
deployed** — no add-ons enabled beyond AKS's own defaults, nothing
applied by hand. This is what AKS itself needs just to make a node a
working member of the cluster at all. All of it gathered live via
`kubectl debug node` (see [`debugging.md`](debugging.md)).

This module now runs **two node pools, one node each** — a tainted
`system` pool and an untainted `user` pool (see `main.tf` and the
README's "Two node pools" section) — so "a node" below means either one
unless a section specifically compares them.

## The node itself

```
Ubuntu 24.04.4 LTS, kernel 6.8.0-1065-azure
2 vCPU, 7.8Gi RAM (990Mi used, 6.8Gi available — mostly buff/cache)
0B swap
```

`Standard_B2s_v2` — matches `main.tf`'s `vm_size`. No swap is normal and
deliberate for Kubernetes nodes: kubelet actively disables/refuses to
run with swap enabled by default, since swap breaks the memory-limit
guarantees cgroups are supposed to enforce for pods.

## Pods (via `crictl ps`) — the complete default footprint

Nothing here was deployed by this module or by hand; this is AKS's own
`kube-system` machinery. Grouped by **why each one exists as a
DaemonSet vs. a Deployment** — that distinction determines whether it's
guaranteed to be on *every* node or just somewhere in the cluster.

### DaemonSets — one instance per node, mandatory, not optional

Each of these needs its own local instance because it acts on *this
node's own* traffic, storage, or hardware — a single cluster-wide
instance couldn't do the job:

- **`kube-proxy`** — programs the node's `iptables` (or IPVS) rules that
  implement every Kubernetes Service. Watches the API server for
  Service/Endpoint changes and continuously rewrites these rules so
  traffic to a Service's ClusterIP load-balances to a real pod IP behind
  it. (`iptables -t nat -L KUBE-SERVICES` is how you'd inspect its
  handiwork directly — see `debugging.md` for the permission caveat hit
  trying exactly that.)
- **`azure-cns`** (2 containers: `cns-container`, `cni-telemetry-sidecar`)
  — Azure's own IPAM daemon, matching this node's actual CNI config
  (`"ipam": {"type": "azure-cns"}` in `/etc/cni/net.d/15-azure-swift-overlay.conflist`).
  Pre-allocates a pool of pod IPs on this node so a new pod gets one
  instantly from local state, instead of a slow per-pod round-trip to
  Azure's network control plane on every pod creation. The telemetry
  sidecar just ships CNI diagnostics back to Microsoft.
- **`csi-azuredisk-node`** (3 containers: `azuredisk`,
  `node-driver-registrar`, `liveness-probe`) — the Container Storage
  Interface driver for Azure Managed Disks, the block storage behind
  most `PersistentVolume`s on AKS (e.g. for StatefulSets).
  `node-driver-registrar` registers this driver with kubelet's plugin
  registry so kubelet knows to call it for mount/unmount;
  `liveness-probe` is a sidecar kubelet polls to confirm the driver
  itself hasn't wedged.
- **`csi-azurefile-node`** (4 containers: `azurefile`,
  `node-driver-registrar`, `liveness-probe`, `azfilesrefresh`) — same
  idea, for Azure Files (SMB/NFS share) volumes instead of block disks.
  `azfilesrefresh` periodically refreshes the storage account
  credentials/tokens this driver uses.
- **`azure-ip-masq-agent`** — configures SNAT/IP-masquerade rules so pod
  traffic leaving toward anything outside the cluster's private CIDR
  gets rewritten to the node's own IP first. Without this, pod IPs
  (only routable *inside* the cluster's overlay network) would be
  unreachable by anything external — the internet, a peered VNet, etc.
  Also defines which internal ranges should stay un-masqueraded.
- **`cloud-node-manager`** — Azure's node-scoped piece of the cloud
  controller manager. Syncs each Kubernetes `Node` object with the real
  Azure VM/VMSS instance behind it: region/zone labels, instance-type
  labels, removing the `Node` object when the underlying VM is deleted.
  The seam that lets plain Kubernetes understand Azure-specific concepts
  without baking Azure code into kubelet itself.

### Deployments — a handful of replicas spread across the cluster

Not guaranteed one-per-node — this node happens to be running these
right now; the other node might run different replicas of the same
Deployments, or none, depending on the scheduler:

- **`coredns`** — the cluster's internal DNS server. Every pod's lookup
  of a Kubernetes Service name (`my-svc.default.svc.cluster.local`)
  resolves here, to that Service's ClusterIP.
- **`coredns-autoscaler`** — watches cluster size (node count/CPU) and
  scales CoreDNS's own replica count up/down to match, so DNS capacity
  keeps pace with the cluster automatically (the Cluster Proportional
  Autoscaler pattern).
- **`konnectivity-agent`** — opens a persistent outbound tunnel from
  this node to the API server (which lives in Microsoft's own managed
  subscription, not yours). This is the actual mechanism that lets the
  control plane reach into your node network for `kubectl exec`,
  `kubectl logs`, and — directly relevant given how you're reading this
  — `kubectl debug node` itself, all *without* your nodes needing a
  public IP or the control plane needing a direct route into your VNet.
- **`konnectivity-agent-autoscaler`** — same proportional-scaling idea as
  the CoreDNS autoscaler, but for the number of `konnectivity-agent`
  replicas needed as the cluster grows.
- **`metrics-server`** (2 containers: `metrics-server`,
  `metrics-server-vpa`) — aggregates CPU/memory usage from every
  kubelet's own metrics into the `metrics.k8s.io` API, what
  `kubectl top nodes`/`kubectl top pods` actually reads from. The second
  container, `metrics-server-vpa`, is a Vertical Pod Autoscaler sidecar
  that watches metrics-server's *own* resource usage over time and
  auto-tunes its CPU/memory requests — AKS tuning its own add-on rather
  than shipping one fixed guess.

(A `node-debugger-*` pod also shows up in `crictl ps` any time you're
actually running a debug session — that's the ephemeral session itself,
not part of the node's permanent footprint. See `debugging.md` for
cleaning those up.)

## `system` pool vs. `user` pool — confirmed live, not hypothetical

Two different eras of this cluster produced two different versions of
this comparison, both real:

**Before the taint existed** (a single untainted 2-node pool): the
DaemonSet list matched exactly on both nodes, as guaranteed, but the
Deployment pods split arbitrarily — `metrics-server`'s 2 replicas both
happened to land on one node, none on the other, purely by scheduler
choice.

**After splitting into `system` (tainted `CriticalAddonsOnly=true:NoSchedule`)
and `user` (untainted) pools** — the split stopped being arbitrary and
became deterministic, driven by tolerations:

| Kind | `system` node | `user` node | Why |
|---|---|---|---|
| DaemonSets (`kube-proxy`, `azure-cns`, `csi-azuredisk-node`, `csi-azurefile-node`, `azure-ip-masq-agent`, `cloud-node-manager`) | ✅ | ✅ | Tolerate every taint unconditionally — every node needs its own networking/storage agent regardless of workload policy |
| `coredns` (both replicas), `coredns-autoscaler`, `konnectivity-agent` (both replicas), `konnectivity-agent-autoscaler`, `metrics-server` (both replicas + `metrics-server-vpa`) | ✅ all of them | ❌ none | AKS's own control-plane Deployments carry a toleration for `CriticalAddonsOnly` specifically — the one taint this pool sets |
| Anything you deploy yourself with no toleration (proved with a plain `nginx:alpine` test deployment) | ❌ | ✅ | No matching toleration — the taint excludes it, same as any ordinary workload |

Same underlying "Deployments aren't guaranteed to spread across nodes"
fact as before — but once a taint is involved, *which* node a
Deployment can land on stops being arbitrary scheduler behavior and
becomes a direct, provable consequence of whether that specific pod's
spec carries a matching toleration.

## systemd services actually running

```
containerd.service   loaded active running   containerd container runtime
kubelet.service      loaded active running   Kubelet
```

Just these two, confirmed live. Every pod above is a *client* of
`containerd` (via the CRI) and is itself *managed* by `kubelet` — there's
no separate "Docker" anywhere on a modern AKS node; containerd talks to
the container runtime directly, and kubelet is the one process that
turns "what pods should run here" (from the API server) into actual
containerd calls.

## Filesystem layout that matters

```
/etc/kubernetes/
├── azure.json        # cloud-provider config (subscription/tenant IDs, etc.)
├── certs/            # node's own TLS certs for talking to the API server
├── manifests/         # static pod manifests, if any
└── volumeplugins/

/var/lib/kubelet/
├── pods/                          # one directory per running pod -- real volume mounts, secrets as plain files
├── plugins/, plugins_registry/    # where CSI drivers register themselves (azuredisk, azurefile above)
├── device-plugins/
├── checkpoints/, cpu_manager_state, memory_manager_state   # kubelet's own resource-management state
├── credential-provider/, credential-provider-config.yaml   # how kubelet fetches registry pull credentials
├── bootstrap-kubeconfig, kubeconfig                         # how kubelet itself authenticates to the API server
└── pki/

/etc/cni/net.d/
└── 15-azure-swift-overlay.conflist    # the one CNI config file -- Azure CNI, transparent mode, azure-cns IPAM
```

## Binaries available for debugging, confirmed present

```
/usr/bin/crictl       # CRI client -- talk to containerd directly, bypass the k8s API
/usr/bin/ctr          # lower-level containerd CLI, even more raw than crictl
/usr/sbin/iptables    # inspect kube-proxy's Service routing rules (needs --profile=general, see debugging.md)
/usr/sbin/ip          # node network interfaces/routes
/usr/bin/ss           # listening sockets on the node
/usr/bin/journalctl   # read any systemd unit's logs, including kubelet's
/usr/bin/systemctl    # check/control systemd units on the node
```

## What this adds up to

A "bare" AKS node is never actually bare — even before you deploy a
single workload, every node is already running the 6 DaemonSets (a DNS
IPAM agent, two storage drivers, a Service-routing engine, a
cloud-provider sync agent, a NAT/masquerade agent) plus 2 systemd
services, on a 2-vCPU node. The `system` node carries meaningfully more
on top of that (CoreDNS, the API-server tunnel, metrics-server and their
autoscalers — the components AKS itself decided must tolerate its own
taint); the `user` node stays that much sparser specifically *because*
the taint keeps it that way, ready for whatever you actually deploy.
Worth having actually seen once, rather than taking "a Kubernetes node"
as a black box.
