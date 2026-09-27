# The `kubernetes` Service You Didn't Create

On a brand-new cluster, before you deploy anything:

```
$ kubectl get all
NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
service/kubernetes   ClusterIP   10.0.0.1     <none>        443/TCP   44m
```

Nobody created this with `kubectl`, Terraform or the manifests in this
module. **Every Kubernetes cluster has it** (AKS, EKS, GKE, minikube, kind).
It's how workloads inside the cluster reach the **API server**.

## Who created it

The **API server itself**, when it starts. A controller built into the API
server makes sure this Service exists in the `default` namespace and keeps its
endpoints pointing at the API server's own address. Its labels show
where it came from:

```yaml
metadata:
  name: kubernetes
  namespace: default
  labels:
    component: apiserver
    provider: kubernetes
```

Its age matches the cluster's age, which confirms it's part of the cluster
rather than something deployed later.

## What it does

It gives pods a **stable, in-cluster address for the Kubernetes API**:

| Way to reach it | Value |
|---|---|
| ClusterIP | `10.0.0.1:443`, always the **first IP of the Service CIDR** (`10.0.0.0/16` here) |
| DNS | `kubernetes.default.svc.cluster.local` (or just `kubernetes.default` / `kubernetes`) |
| Env vars injected into every pod | `KUBERNETES_SERVICE_HOST=10.0.0.1`, `KUBERNETES_SERVICE_PORT=443` |

Anything that talks to the Kubernetes API from inside a pod uses it: client
libraries (`client-go`, the Python `kubernetes` client in "in-cluster config"
mode), operators and controllers, CoreDNS (to watch Services/EndpointSlices),
metrics-server, ingress controllers, Argo CD and so on.

## Where it actually points

It's a Service **without a pod selector**. Its endpoints aren't pods. The API
server writes its own address into the EndpointSlice:

```
$ kubectl get endpointslices -l kubernetes.io/service-name=kubernetes
NAME         ADDRESSTYPE   PORTS   ENDPOINTS      AGE
kubernetes   IPv4          443     4.188.113.64   45m

$ nslookup akssvclf508l-s161qh2r.hcp.centralindia.azmk8s.io
Address: 4.188.113.64
```

The endpoint is the **public IP of the AKS-managed API server** (the same
FQDN in your kubeconfig, see [`CONNECT_KUBECTL.md`](CONNECT_KUBECTL.md)).
So both paths end at the same control plane:

```
kubectl on laptop ──► akssvclf508l-...azmk8s.io:443 ─┐
                                                     ├──► API server (4.188.113.64, Azure-managed)
pod in cluster ─────► 10.0.0.1:443 ── kube-proxy ────┘
                     (Service "kubernetes")
```

kube-proxy on the node rewrites `10.0.0.1:443` to `4.188.113.64:443`, the
same way it handles any other ClusterIP Service.

## Verified from inside a pod

```bash
kubectl run apitest --rm -i --restart=Never --image=curlimages/curl:8.10.1 -q --command -- sh -c '
  echo KUBERNETES_SERVICE_HOST=$KUBERNETES_SERVICE_HOST
  nslookup kubernetes.default.svc.cluster.local | tail -2
  curl -s -o /dev/null -w "unauth /version -> %{http_code}\n" -k https://kubernetes.default.svc/version
  T=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  curl -s -k -H "Authorization: Bearer $T" https://kubernetes.default.svc/api/v1/namespaces/default/pods \
    -o /dev/null -w "sa token list pods -> %{http_code}\n"'
```

```
KUBERNETES_SERVICE_HOST=10.0.0.1
Address: 10.0.0.1
unauth /version -> 401
sa token list pods -> 403
```

What that shows:

- **The address is reachable from any pod**: the env var and DNS both resolve to `10.0.0.1`.
- **Being able to reach it doesn't mean being allowed in.** Anonymous requests get `401`
  (AKS disables anonymous auth). The pod's auto-mounted `default`
  ServiceAccount token gets **authenticated** but is **forbidden** (`403`),
  because it has no RBAC permissions. To give a workload API access, you create a
  ServiceAccount + Role/ClusterRole + RoleBinding for it. For workloads that
  don't need the API, set `automountServiceAccountToken: false`.

## Things to know

- **Don't delete or edit it.** The API server recreates or reconciles it within
  seconds, and in-cluster clients that depend on it fail until it does.
- **It creates nothing in Azure.** It's a ClusterIP Service, so the
  `kubernetes` Azure Load Balancer in the node resource group is unrelated despite the
  shared name. See [`AZURE_RESOURCES.md`](AZURE_RESOURCES.md).
- **`10.0.0.1` is reserved** for it. That's why ClusterIPs you get start elsewhere
  in the range (e.g. `10.0.205.251` in the experiment), and why CoreDNS is
  pinned to `10.0.0.10`.
- **`kubectl get all` only shows the `default` namespace.** Use `-A` to see the rest.

## The other built-in objects on a fresh cluster

```
$ kubectl get ns
default           kube-node-lease   kube-public   kube-system

$ kubectl get svc -A
NAMESPACE     NAME             TYPE        CLUSTER-IP   PORT(S)
default       kubernetes       ClusterIP   10.0.0.1     443/TCP         <- API server (this doc)
kube-system   kube-dns         ClusterIP   10.0.0.10    53/UDP,53/TCP   <- CoreDNS: cluster DNS for every pod
kube-system   metrics-server   ClusterIP   10.0.6.36    443/TCP         <- serves `kubectl top` data
```

| Namespace | Purpose |
|---|---|
| `default` | Where things go when you don't specify a namespace. Holds the `kubernetes` Service |
| `kube-system` | Cluster add-ons: CoreDNS, kube-proxy, CNI, CSI drivers, metrics-server, konnectivity-agent |
| `kube-public` | Readable by everyone. Holds the `cluster-info` ConfigMap used for bootstrapping |
| `kube-node-lease` | One Lease object per node, updated as a heartbeat so the control plane can tell the node is alive |

All of these are created by Kubernetes/AKS, not by this module. None of
them are Azure resources.
