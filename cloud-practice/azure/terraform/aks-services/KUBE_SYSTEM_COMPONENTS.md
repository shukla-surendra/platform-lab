# What's Running in a Fresh AKS Cluster (`kube-system`)

Right after `terraform apply`, before you deploy anything,
`kubectl get all -A` lists **14 pods, 3 Services, 11 DaemonSets and 5
Deployments**. AKS installs and manages all of them. None come from this
module. This doc explains each one, plus why `kubectl get all` and
`kubectl get all -A` show such different things.

Captured from the real cluster (`aks-svc-lf508l`, K8s 1.35.8, one
`Standard_B2s_v2` Linux node, Azure CNI Overlay). Images are from
`mcr.microsoft.com`.

## `kubectl get all` vs `kubectl get all -A`

| Command | Scope | On this fresh cluster |
|---|---|---|
| `kubectl get all` | **Only the current namespace** (from your kubeconfig context, `default` unless you've set one) | 1 object: `service/kubernetes` |
| `kubectl get all -n kube-system` | Only `kube-system` | 39 objects: everything AKS installed |
| `kubectl get all -A` (= `--all-namespaces`) | **Every namespace** | 40 objects, which is both of the above |

`-A` doesn't show "more kinds" of objects. It shows the **same kinds across
all namespaces**, and adds a `NAMESPACE` column. Namespaces partition the
cluster, and nearly every kubectl read command is namespace-scoped by
default, so without `-A` or `-n` you only see one namespace.

```bash
kubectl config view --minify -o jsonpath='{..namespace}'   # current default namespace (empty = "default")
kubectl config set-context --current --namespace=kube-system   # change it (then `get all` shows kube-system)
```

### "all" isn't really all

`all` is a **category**: a fixed list of resource kinds that opt into it.
On this cluster:

```bash
$ kubectl api-resources --categories=all -o name
pods  replicationcontrollers  services  daemonsets.apps  deployments.apps
replicasets.apps  statefulsets.apps  horizontalpodautoscalers.autoscaling
cronjobs.batch  jobs.batch
```

So `get all` (with or without `-A`) **never shows** ConfigMaps, Secrets,
ServiceAccounts, Ingresses, PVCs/PVs, Roles/RoleBindings, NetworkPolicies,
EndpointSlices, CRDs or custom resources. For example, even the "empty"
`default` namespace contains:

```
serviceaccount/default        <- auto-created in every namespace
configmap/kube-root-ca.crt    <- cluster CA, auto-published to every namespace
```

and `kubectl get cm,secret,sa -A` returns 70 objects that `get all -A`
never listed. To really see everything in a namespace:

```bash
kubectl api-resources --verbs=list --namespaced -o name \
  | xargs -n1 kubectl get -n kube-system --ignore-not-found --show-kind
```

## What is *not* in the list: the control plane

There are no `kube-apiserver`, `etcd`, `kube-scheduler` or
`kube-controller-manager` pods. On AKS the **control plane is run by Azure**
outside your cluster and subscription (see [`AZURE_RESOURCES.md`](AZURE_RESOURCES.md)).
You only see it as the API endpoint. On kubeadm/minikube you'd see those as
static pods in `kube-system`.

## DaemonSets: one pod on every (matching) node

| DaemonSet | Pods | What it does | Host network |
|---|---|---|---|
| **`kube-proxy`** | 1 | Programs iptables rules on the node so Service ClusterIPs (e.g. `10.0.0.1`, `10.0.0.10`) route to real endpoints. The standard upstream component | yes |
| **`azure-cns`** | 1 (2 containers: `cns-container`, `cni-telemetry-sidecar`) | **Azure Container Networking Service**. Works with the Azure CNI plugin to give pods IPs from the overlay pod CIDR `10.244.0.0/16` and to program node routing | yes |
| **`azure-ip-masq-agent`** | 1 | Controls **SNAT/masquerading**. Traffic from pods to anything outside the pod/VNet ranges is rewritten to the node IP (`10.224.0.4`), so it can leave through the `kubernetes` LB's outbound IP. Traffic within the cluster keeps the pod IP | yes |
| **`cloud-node-manager`** | 1 | The node-side part of the Azure cloud provider. Labels and annotates the Node object with Azure facts (instance type, zone, region, provider ID) and updates node addresses | yes |
| **`csi-azuredisk-node`** | 1 (3 containers) | **Azure Disk CSI driver**, node plugin. Attaches/mounts Azure Managed Disks into pods for `PersistentVolumeClaim`s (storage classes `managed-csi`, `managed-csi-premium`, `default`) | yes |
| **`csi-azurefile-node`** | 1 (4 containers) | **Azure Files CSI driver**, node plugin. Mounts SMB/NFS Azure File shares (storage classes `azurefile-csi*`). Used for `ReadWriteMany` volumes | yes |

Each CSI pod bundles `node-driver-registrar` (registers the driver with the
kubelet) and `liveness-probe` alongside the driver itself.

### The Windows DaemonSets showing `DESIRED 0`

`azure-cns-win`, `cloud-node-manager-windows`, `csi-azuredisk-node-win`,
`csi-azurefile-node-win`, `windows-kube-proxy-initializer`

These are the Windows versions of the above. They're installed on every
cluster, but their node affinity requires `kubernetes.io/os In [windows]`:

```bash
$ kubectl get ds azure-cns-win -n kube-system \
    -o jsonpath='{.spec.template.spec.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[0].matchExpressions}'
[... {"key":"kubernetes.io/os","operator":"In","values":["windows"]}]
```

With no Windows node pool, 0 nodes match, so `DESIRED 0`. If you add a
Windows pool they start automatically. **This is normal, not a failure.**

## Deployments: cluster-wide services

| Deployment | Replicas | What it does | Fronted by |
|---|---|---|---|
| **`coredns`** | 2 | **Cluster DNS**. Resolves `svc.namespace.svc.cluster.local` names and forwards everything else to Azure DNS. Every pod's `/etc/resolv.conf` points at it | `service/kube-dns` → `10.0.0.10:53` UDP+TCP |
| **`coredns-autoscaler`** | 1 | `cluster-proportional-autoscaler`: resizes `coredns` based on the cluster's node/core count. It's why there are 2 CoreDNS replicas even on 1 node (the minimum) | – |
| **`metrics-server`** | 2 (containers: `metrics-server`, `metrics-server-vpa`) | Scrapes CPU/memory from each kubelet and serves the `metrics.k8s.io` API. Powers **`kubectl top`** and the **HorizontalPodAutoscaler**. `metrics-server-vpa` (addon-resizer) adjusts its own resource requests as the cluster grows | `service/metrics-server` → `10.0.6.36:443` |
| **`konnectivity-agent`** | 2 | Keeps a tunnel **from the node out to the Azure-managed API server**. The API server can't reach into your VNet directly, so `kubectl logs/exec/port-forward/attach` and webhook calls travel back through this tunnel to the kubelet | – |
| **`konnectivity-agent-autoscaler`** | 1 | Another `cluster-proportional-autoscaler`, this time scaling `konnectivity-agent` with cluster size | – |

## Services

| Service | Namespace | ClusterIP | Points to |
|---|---|---|---|
| `kubernetes` | default | `10.0.0.1:443` | The API server (see [`DEFAULT_KUBERNETES_SERVICE.md`](DEFAULT_KUBERNETES_SERVICE.md)) |
| `kube-dns` | kube-system | `10.0.0.10:53` | `coredns` pods. The name is kept from the old kube-dns add-on for compatibility |
| `metrics-server` | kube-system | `10.0.6.36:443` | `metrics-server` pods |

All three are ClusterIP only, so none of them creates anything in Azure.

## ReplicaSets with `0 0 0`

```
replicaset.apps/konnectivity-agent-7fd7ff6678   0   0   0   45m   <- original
replicaset.apps/konnectivity-agent-687c85f8b    2   2   2   18m   <- current
replicaset.apps/metrics-server-7b48c76bfd       0   0   0   45m   <- original
replicaset.apps/metrics-server-7c4d5d8fdb       2   2   2   43m   <- current
```

Each change to a Deployment's pod template creates a new ReplicaSet and scales
the old one to 0. AKS reconfigured these two add-ons after cluster creation
(for example, the addon-resizer changing metrics-server's requests), and the
old ReplicaSets are kept as rollout history (`revisionHistoryLimit`) so the
change can be rolled back. **Normal, not leftovers to clean up.**

## Two kinds of pod IPs

```
kube-proxy / azure-cns / ip-masq / cloud-node-manager / csi-*   10.224.0.4   hostNetwork: true
coredns / metrics-server / konnectivity-agent / autoscalers     10.244.0.x   pod network (overlay)
```

The DaemonSets manage the node itself (iptables, routes, mounts), so they
run in the **node's network namespace** and show the node IP from the VNet
subnet. Everything else is an ordinary pod with an overlay IP from
`10.244.0.0/16`.

## Resource footprint

`kubectl top pods -n kube-system` at idle: about **25m CPU and 570 Mi memory**
in total for all 14 pods. Heaviest are `csi-azurefile-node` (123 Mi),
`cloud-node-manager` (84 Mi), `azure-cns` (82 Mi) and `coredns` (73 Mi).
On a 2 vCPU / 8 GiB node, this plus the kubelet/OS reservation is why
*allocatable* is noticeably less than the VM size.

## Rules of thumb

- **Everything in `kube-system` is AKS-managed.** Don't edit or delete it. AKS
  reconciles it back, and it breaks the cluster until then.
- All of these pods run at priority class `system-node-critical` (metrics-server:
  `system-cluster-critical`), so they're the last to be evicted under pressure.
- Your own workloads belong in `default` or, better, your own namespace
  (`kubectl create ns demo`). Use `kubectl get all -n demo` to see just yours.
- Use `-A` when you're asking "what is running in this cluster?". Leave it off when
  you're asking "what is in the namespace I'm working in?".
