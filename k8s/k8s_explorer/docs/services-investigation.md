# Services: what problem each one solves, and what actually happens underneath

Companion to [`service-types.md`](service-types.md) (the five types explained) and the manifests in
[`practice/services-demo/`](../practice/services-demo) and
[`practice/services-demo/problems/`](../practice/services-demo/problems).

Everything marked **observed** was run on a local minikube cluster (Kubernetes v1.34.0, Docker driver,
`kube-proxy` in iptables mode). Anything not marked observed is from general knowledge.

## The root problem: Pods are disposable

A Pod's IP changes every time it is replaced, and a Deployment has several Pods. Nothing can depend on
a Pod IP. A **Service** is a stable name and virtual IP in front of a changing set of Pods, chosen by
**label selector**.

```
client ──> Service (stable name + IP) ──> EndpointSlice (the live list of ready Pod IPs) ──> Pod
```

Three objects do the work:

| Object | Role |
|---|---|
| **Service** | The stable name, virtual IP, ports, and the label selector |
| **EndpointSlice** | The live list of Pod IPs behind it, with `ready` flags. Maintained by the control plane |
| **kube-proxy** (on every node) | Turns Service + EndpointSlices into node-level forwarding rules |

## What problem each type solves

| Type | Problem it solves | Reach | Typical use | Limits |
|---|---|---|---|---|
| **ClusterIP** | Callers need a stable address and load balancing across changing Pods | Inside the cluster | Service-to-service calls (API → backend → database) | Not reachable from outside |
| **NodePort** | Need to reach a Service from outside **with no cloud load balancer** | `<any node IP>:<30000-32767>` | Local clusters, quick demos, bare metal | High ports, node IPs change, the client must choose a node; no health-based failover |
| **LoadBalancer** | Need **one stable public address** with health checking, without exposing node IPs | Cloud-provided external IP/DNS | Production internet-facing services | One cloud load balancer per Service (cost); `<pending>` forever without a cloud provider or tunnel |
| **Headless** (`clusterIP: None`) | Clients need the **individual Pods**, not one random one | DNS returns all Pod IPs | StatefulSets, databases, peer discovery, client-side load balancing | No virtual IP, no load balancing by Kubernetes |
| **ExternalName** | Give an in-cluster name to something **outside** the cluster that has a DNS name | DNS alias (CNAME) only | Managed database, SaaS API, migrating a dependency into or out of the cluster | CNAME only: no port mapping, no health checks; Host/TLS name mismatches are your problem |

They build on each other: a NodePort Service **also has a ClusterIP**, and a LoadBalancer Service
**also has a NodePort and a ClusterIP**.

For HTTP, one LoadBalancer per Service gets expensive, so one **Ingress / Gateway** (a single
LoadBalancer in front of many HTTP Services, routing by host and path) usually replaces many LoadBalancers.

## Problems the five types don't cover

Manifests for these are in `practice/services-demo/problems/`.

| Problem | Feature | File |
|---|---|---|
| "The Service exists but nothing answers" | Selector must match **Pod labels**; check the EndpointSlice | `01-selector-mismatch.yaml` |
| Traffic hits Pods that aren't ready | **Readiness probes** remove Pods from endpoints without restarting them | `02-readiness-gating.yaml` |
| An app exposes several ports; port numbers shouldn't be hard-coded | **Multi-port** Services and **named** `targetPort` | `03-multiport-named-ports.yaml` |
| Give a name to an **IP** (VM, on-prem host), not a DNS name | **Selectorless** Service + hand-written EndpointSlice | `04-selectorless-endpointslice.yaml` |
| In-memory per-client state breaks across Pods | `sessionAffinity: ClientIP` | `05-session-affinity.yaml` |
| Replicas aren't interchangeable (primary vs replicas) | **StatefulSet + headless**: stable DNS per Pod | `06-statefulset-headless.yaml` |
| Extra hop and lost client IP with NodePort/LoadBalancer | `externalTrafficPolicy: Local` | `07-external-traffic-policy.yaml` |

## What I observed

### 1. A ClusterIP is a forwarding rule on every node (observed)

`web-clusterip` got virtual IP `10.104.45.41`. There is no process listening on that IP. `kube-proxy`
wrote iptables rules on the node:

```
KUBE-SERVICES      -d 10.104.45.41/32 ...          -> KUBE-SVC-PF753...    (match the virtual IP)
KUBE-SVC-PF753...  statistic random probability 0.333 -> KUBE-SEP-...(pod 10.244.0.4)
                   statistic random probability 0.500 -> KUBE-SEP-...(pod 10.244.0.5)
                   (remaining traffic)                -> KUBE-SEP-...(pod 10.244.0.6)
KUBE-SEP-...       DNAT --to-destination 10.244.0.4:80
```

- Load balancing is **random selection per new connection** (1/3, then 1/2 of the rest, then the remainder
  = equal thirds). It is not round-robin, and it is per connection, not per request.
- 12 requests came back 3 / 4 / 5 across the three Pods: random, close to even.
- The "Service IP" is virtual. Pinging it doesn't work, but TCP ports you declared do.

### 2. The EndpointSlice is the real backend list (observed)

```
NAME                  ENDPOINTS
web-clusterip-4c7hv   10.244.0.4,10.244.0.5,10.244.0.6
```

Each endpoint has `ready`, `serving` and `terminating` conditions and a `targetRef` to its Pod. Only
**ready** endpoints get forwarding rules. `web-external` (ExternalName) has **no** EndpointSlice at all,
because nothing is proxied.

### 3. DNS is how clients find Services (observed)

| Lookup | Result |
|---|---|
| `web-clusterip` | One A record: `10.104.45.41` (the virtual IP) |
| `web-headless` | **Three** A records, one per Pod |
| `web-external.default.svc.cluster.local` | `canonical name = example.com`, then example.com's IPs: a CNAME |
| `db-1.db.default.svc.cluster.local` | The one Pod's IP (StatefulSet + headless) |

Short names (`web-clusterip`) work only because the Pod's DNS search path includes its own namespace;
cross-namespace use `name.namespace` or the full `name.namespace.svc.cluster.local`.

Pods also get environment variables (`WEB_CLUSTERIP_SERVICE_HOST=10.104.45.41`,
`..._SERVICE_PORT=80`) for Services that **existed when the Pod started**. DNS has no such ordering
problem, so prefer DNS.

### 4. Selector typo → empty endpoints (observed)

```
Selector:   app=web-backnd        <- typo
Endpoints:  (empty)
```

The Service was created fine, with a ClusterIP and DNS name, and its EndpointSlice was empty. This is
the most common "Service doesn't work" cause. First check: `kubectl get endpointslice -l kubernetes.io/service-name=<svc>`
(or `kubectl describe svc <svc>` and read `Endpoints`).

### 5. Readiness gates traffic (observed)

Two Pods were `Running` but `0/1` ready. The EndpointSlice listed both with
`"ready": false, "serving": false`, and `describe svc` showed **no** `Endpoints`. After creating the
ready file in one Pod, `describe svc` showed exactly that one Pod's IP. The Pod was never restarted:
**liveness restarts, readiness only removes from traffic.**

### 6. Named ports (observed)

`multiport` exposed `http 80 → targetPort http` and `metrics 9100 → targetPort metrics`. Clients used
`:9100` while the container listens on `8081`. The Service resolved the port **by name**, so the container's
number can change without touching the Service.

### 7. Session affinity (observed)

| Service | 12 requests |
|---|---|
| `web-clusterip` | 4 / 5 / 3 across three Pods |
| `web-sticky` (`ClientIP`) | **12 / 0 / 0**: all to one Pod |

### 8. StatefulSet + headless: stable names, changing IPs (observed)

`db-0`, `db-1`, `db-2` each resolved to their own Pod IP (`db-N.db`). After deleting `db-1`, its IP
changed (`10.244.0.13 → 10.244.0.24`) and **`db-1.db` resolved to the new IP**. That is the guarantee
a ClusterIP can't give: a name for one specific replica.

### 9. Selectorless Service + manual EndpointSlice (observed)

`legacy-backend` had `Selector: <none>`, yet it forwarded to the IP I wrote into the EndpointSlice
(`Endpoints: 10.244.0.5:80`) and returned a response.

Two surprises while testing:

- **The first request failed with "Connection refused", the retry worked.** The EndpointSlice and
  rules existed moments later (I checked the iptables chain), so the likeliest cause is a short delay
  between creating a Service and `kube-proxy` programming it. In scripts, wait or retry briefly after
  creating a Service.
- **Pointing a Service at `nodeIP:NodePort` is refused** (observed, three attempts after waiting),
  although a Pod calling `nodeIP:30531` **directly** works. A NodePort is not a listening socket; it is
  a NAT rule. My explanation, which fits what I saw but which I did not prove in the packet path, is that
  NAT rules are applied once per connection, so a packet already rewritten by the Service's rule is not
  matched by the NodePort rule. Point selectorless Services at real listening addresses.

### 10. What I could not demonstrate

- **LoadBalancer:** `EXTERNAL-IP` stayed `<pending>`. Making it real needs `minikube tunnel` (a
  separate terminal, and it asks for sudo). Not run.
- **NodePort across nodes and `externalTrafficPolicy: Local`:** the second node never joined (see below),
  so every Pod ran on one node. The rules for `web-local` differ from `web-nodeport` (the `Local` policy
  has its own `KUBE-EXT-...` chain), but the cross-node behavior (the extra hop, source IP) is untested.

## Cluster state found while investigating

`minikube profile list` reported **2 nodes** (one profile, not two clusters), but `kubectl get nodes`
showed **1**. The worker `minikube-m02` was running as a container but its kubelet was crash-looping
(**812 restarts**, `failed to load kubelet config file /var/lib/kubelet/config.yaml`), meaning the
worker never completed joining the cluster. I did not repair it. Options: `minikube node delete m02`
then `minikube node add --worker`, or recreate the profile with `minikube start --nodes 2`.

## Debugging checklist: "my Service doesn't work"

1. `kubectl get svc <name> -o wide` — right type, ports, selector?
2. `kubectl get endpointslice -l kubernetes.io/service-name=<name>` — any endpoints? If empty: the selector
   doesn't match Pod labels (`kubectl get pods --show-labels`), or no Pod is **ready**.
3. `kubectl get pods` — Running **and** READY?
4. Right port? `port` is what clients use, `targetPort` is what the container listens on.
5. From a Pod in the cluster: `nslookup <name>` then `wget -qO- http://<name>:<port>`.
6. Hit the Pod directly (`kubectl port-forward pod/<pod> 8080:80`): if that works, the problem is the Service layer.
7. NodePort/LoadBalancer: node firewall or security group allows the port? Cloud LB health checks passing?
8. NetworkPolicy blocking the traffic? (`kubectl get networkpolicy -A`)
9. `kube-proxy` healthy? (`kubectl -n kube-system get pods -l k8s-app=kube-proxy`)
10. Just created it and it fails once? Retry after a few seconds.

## Command cheat sheet

```bash
kubectl get svc -o wide
kubectl describe svc <name>                       # selector + Endpoints at a glance
kubectl get endpointslice -l kubernetes.io/service-name=<name> -o yaml
kubectl get pods -l app=<label> -o wide --show-labels
minikube ssh "sudo iptables -t nat -S | grep <svc-name>"      # the actual forwarding rules
kubectl -n kube-system logs ds/kube-proxy | grep -i proxier   # which mode kube-proxy uses
kubectl run t --image=busybox:1.36 --rm -it --restart=Never -- sh   # a shell inside the cluster
```
