# Services, ClusterIPs and Nodes: How One Node Serves Many Service IPs

Question this answers:

> I have **one node**, but `kubectl get svc -n gridwork` shows several
> ClusterIP Services. Can a node have multiple ClusterIPs?

**A node doesn't "have" ClusterIPs at all.** A ClusterIP isn't assigned to
any node, VM or network interface. It's a **virtual IP** that exists only as
**packet-rewriting rules** that kube-proxy writes on **every** node. So
the number of Services has nothing to do with the number of nodes. One node can
handle thousands of them. The evidence below was captured on this cluster's single node
(`aks-system-31524237-vmss000000`) with gridwork deployed
([`DEPLOY_GRIDWORK.md`](DEPLOY_GRIDWORK.md)).

## What's in the `gridwork` namespace

```
$ kubectl get svc -n gridwork
NAME                       TYPE           CLUSTER-IP     EXTERNAL-IP     PORT(S)
gridwork-backend           ClusterIP      10.0.162.81    <none>          8000/TCP
gridwork-frontend          NodePort       10.0.212.134   <none>          80:30932/TCP
gridwork-frontend-public   LoadBalancer   10.0.174.219   98.70.243.116   80:30757/TCP
gridwork-postgres          ClusterIP      None           <none>          5432/TCP
gridwork-redis             ClusterIP      10.0.138.6     <none>          6379/TCP
```

| Service | Type | ClusterIP | Routes to (EndpointSlice) | Who calls it |
|---|---|---|---|---|
| `gridwork-backend` | ClusterIP | `10.0.162.81` | backend pod `10.244.0.88:8000` | nginx in the frontend pod (`/api/`) |
| `gridwork-redis` | ClusterIP | `10.0.138.6` | redis pod `10.244.0.57:6379` | backend |
| `gridwork-postgres` | ClusterIP, **headless** | `None` | postgres pod `10.244.0.53:5432` | backend, migration Job |
| `gridwork-frontend` | NodePort | `10.0.212.134` | frontend pod `10.244.0.135:80` | nothing external here (the chart's minikube default) |
| `gridwork-frontend-public` | LoadBalancer | `10.0.174.219` | frontend pod `10.244.0.135:80` | the internet via `98.70.243.116` |

That's **three Services of type ClusterIP**, but **four ClusterIPs**, because the
Service types build on each other:

```
ClusterIP      = virtual IP inside the cluster
NodePort       = ClusterIP + a port (30000-32767) opened on EVERY node
LoadBalancer   = NodePort  + a cloud LB frontend/public IP that sends to those node ports
```

So `gridwork-frontend` (NodePort) and `gridwork-frontend-public`
(LoadBalancer) each get a ClusterIP too. Two Services can also select the
**same pods**: both frontend Services point at `10.244.0.135`.

Every pod here runs on the same one node, each with its own pod IP:

```
$ kubectl get pods -n gridwork -o wide
gridwork-backend-...    10.244.0.88    aks-system-31524237-vmss000000
gridwork-frontend-...   10.244.0.135   aks-system-31524237-vmss000000
gridwork-postgres-0     10.244.0.53    aks-system-31524237-vmss000000
gridwork-redis-...      10.244.0.57    aks-system-31524237-vmss000000
```

## Evidence 1: no interface on the node owns a ClusterIP

From a node shell (`kubectl debug node/<node> --profile=sysadmin ...` then `chroot /host`):

```
$ ip -4 -o addr
lo   127.0.0.1/8
eth0 10.224.0.4/16            <- the node's only real IP (from the VNet subnet)

$ ip -4 addr | grep -E "10\.0\.(162|138|212|174)\."
(nothing)                     <- none of the Service IPs is on any interface
```

A ClusterIP never answers ARP and you can't ping it (it only matches the Service's
TCP/UDP ports). It only "exists" when a packet is addressed to it.

## Evidence 2: it's iptables rules written by kube-proxy

```
$ curl -s localhost:10249/proxyMode
iptables
```

Every Service becomes a line in the `KUBE-SERVICES` chain of the `nat` table
(one per ClusterIP:port):

```
-A KUBE-SERVICES -d 10.0.162.81/32  --dport 8000 "gridwork/gridwork-backend cluster IP"            -j KUBE-SVC-VPEGULW6KJEZTDUP
-A KUBE-SERVICES -d 10.0.138.6/32   --dport 6379 "gridwork/gridwork-redis cluster IP"              -j KUBE-SVC-X4CZGVCWDR2B4RTQ
-A KUBE-SERVICES -d 10.0.212.134/32 --dport 80   "gridwork/gridwork-frontend cluster IP"           -j KUBE-SVC-KIFZGMICNWO6U5RW
-A KUBE-SERVICES -d 10.0.174.219/32 --dport 80   "gridwork/gridwork-frontend-public:http cluster IP" -j KUBE-SVC-GWRZBZCFXSXHZE7G
-A KUBE-SERVICES -d 98.70.243.116/32 --dport 80  "gridwork/gridwork-frontend-public:http loadbalancer IP" -j KUBE-EXT-GWRZBZCFXSXHZE7G
```

Following the backend's chain down to the pod:

```
KUBE-SVC-VPEGULW6KJEZTDUP  "gridwork/gridwork-backend -> 10.244.0.88:8000"  -j KUBE-SEP-UP542Y36CC6SSQK4
KUBE-SEP-UP542Y36CC6SSQK4  -p tcp  -j DNAT --to-destination 10.244.0.88:8000
```

So a packet to `10.0.162.81:8000` gets its destination **rewritten (DNAT)** to
the backend pod's real IP, on whichever node the packet started from.
With 3 backend replicas there'd be 3 `KUBE-SEP-*` entries and the
`KUBE-SVC-*` chain would pick one at random (probability rules). That's the
"load balancing" a ClusterIP does.

NodePorts are the same idea, keyed on node port instead of IP:

```
-A KUBE-NODEPORTS --dport 30932 "gridwork/gridwork-frontend"             -j KUBE-EXT-KIFZGMICNWO6U5RW
-A KUBE-NODEPORTS --dport 30757 "gridwork/gridwork-frontend-public:http" -j KUBE-EXT-GWRZBZCFXSXHZE7G
```

Note: **no rule exists for `gridwork-postgres`**, because headless Services get no
ClusterIP and so no iptables rules (next section).

## Where ClusterIPs come from

They're allocated by the **API server** from the cluster's **service CIDR**,
`10.0.0.0/16` on this cluster (see [`AZURE_RESOURCES.md`](AZURE_RESOURCES.md)).
That's 65,536 addresses shared by the whole cluster, regardless of node count.

| Range | Used for | Example |
|---|---|---|
| `10.224.0.0/16` (VNet subnet) | Node IPs (real Azure NICs) | node `10.224.0.4` |
| `10.244.0.0/16` (overlay pod CIDR) | Pod IPs | backend pod `10.244.0.88` |
| `10.0.0.0/16` (service CIDR) | ClusterIPs (virtual, no NIC anywhere) | `10.0.162.81` |

Special ones: `10.0.0.1` = the `kubernetes` API Service
([`DEFAULT_KUBERNETES_SERVICE.md`](DEFAULT_KUBERNETES_SERVICE.md)),
`10.0.0.10` = `kube-dns`.

## Why Services exist at all

- **Pod IPs change and ClusterIPs don't.** During the gridwork upgrade, the
  backend pod was replaced and got a new pod IP. nginx never noticed, because it
  calls `gridwork-backend` → `10.0.162.81`, and kube-proxy just updated the
  DNAT target.
- **Stable DNS names.** The backend connects to `gridwork-redis` and
  `gridwork-postgres` by name. The chart never hard-codes an IP.
- **Load spreading across replicas.** One ClusterIP, N pods behind it.
- Kubernetes also injects env vars for Services that existed when a pod started:

  ```
  GRIDWORK_BACKEND_SERVICE_HOST=10.0.162.81
  GRIDWORK_BACKEND_SERVICE_PORT=8000
  ```

## Headless Services (`ClusterIP: None`): Postgres

```
$ nslookup gridwork-backend.gridwork.svc.cluster.local
Address: 10.0.162.81          <- normal Service: DNS returns the virtual ClusterIP

$ nslookup gridwork-postgres.gridwork.svc.cluster.local
Address: 10.244.0.53          <- headless: DNS returns the POD IP directly

$ nslookup gridwork-postgres-0.gridwork-postgres.gridwork.svc.cluster.local
Address: 10.244.0.53          <- and each StatefulSet pod gets its own stable name
```

No virtual IP, no kube-proxy rules, no load balancing: the client connects
straight to the pod. StatefulSets use this because each replica (e.g.
`postgres-0` primary, `postgres-1` replica) is a distinct identity that clients must be able to address
individually. Load-balancing across them would be wrong.

## Related: namespaced vs. cluster-scoped

```
$ kubectl get nodes -n gridwork     # same output as without -n
```

Nodes are **cluster-scoped**, so `-n` is silently ignored. Services,
pods and Deployments are **namespaced**, but pods from every namespace are
scheduled onto the same shared nodes. Check any kind with:

```bash
kubectl api-resources --namespaced=false    # nodes, namespaces, persistentvolumes, storageclasses, clusterroles, ...
```

## Reproduce

```bash
kubectl get svc,endpointslices -n gridwork
kubectl get pods -n gridwork -o wide

# node shell (a privileged debug pod; delete it afterwards)
kubectl debug node/$(kubectl get nodes -o name | head -1 | cut -d/ -f2) -it \
  --profile=sysadmin --image=mcr.microsoft.com/cbl-mariner/busybox:2.0
chroot /host
ip -4 -o addr
curl -s localhost:10249/proxyMode
iptables-save -t nat | grep gridwork
exit
kubectl get pods -o name | grep node-debugger | xargs kubectl delete

# DNS: normal vs headless
kubectl exec -n gridwork deploy/gridwork-frontend -- nslookup gridwork-backend
kubectl exec -n gridwork deploy/gridwork-frontend -- nslookup gridwork-postgres
```
