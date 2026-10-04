# ClusterIP explained (restructured from the questions that came up)

Companion to `KUBERNETES_SERVICE_TYPES.md`. This file is organised by the doubts, in the order that makes them clear. The lab values (`172.20.100.11`, `10.20.x.x`) are from the EKS lab run; the A -> B -> C example in section 8 is illustrative and was not run.

## 1. The one-sentence version

A ClusterIP Service gives a **group of pods one stable name/address** that other pods inside the cluster use; it **forwards** each connection to one of the healthy pods behind it.

## 2. The problem it solves

Pods are temporary. Their IPs change when they restart, reschedule or scale. If pod A stored pod B's IP, it would break the next time B restarted, and A would not know about new B pods when you scale up.

A Service sits in front and hides this:

```
caller  ->  hello:80   (the Service: stable name + IP)
                |
                |  Service picks one healthy pod
                v
        10.20.2.158  or  10.20.1.240   (real pod IPs, change over time)
```

## 3. Doubt: "It has an IP and a DNS name, but what does it actually *do*?"

The IP and DNS name are only the **address**. The job is **forwarding**:

1. The Service tracks pods matching its `selector` (`app=hello`) that are **Ready**: the **Endpoints**.
2. **kube-proxy** on every node programs forwarding rules (iptables/IPVS) from the Service IP to those pod IPs.
3. When a pod sends traffic to the Service IP, the node rewrites the destination to a real pod IP.
4. As pods come and go, the rules are updated automatically. Pods failing their readiness probe are skipped.

Analogy: a company's main phone number. The number never changes (the ClusterIP); the call is routed to whichever employee is free (the pods).

## 4. Doubt: "What kind of IP is it? Is it private?"

Private, but **virtual**.

| Address | Example | Real or virtual |
|---|---|---|
| Pod IP | `10.20.2.158` | Real: VPC address |
| Node IP | `10.20.1.212` | Real: the EC2 instance |
| Service ClusterIP | `172.20.100.11` | Virtual: only forwarding rules |

- It comes from the **Service CIDR** (`172.20.0.0/16`), separate from the VPC range (`10.20.0.0/16`).
- It is not on any machine or network interface; AWS doesn't know about it; nothing answers on it, so **you can't ping it**.
- Stays the same for the Service's lifetime. Recreate the Service and it may change, so use the **DNS name** in apps.

## 5. Doubt: "Who can access it?"

- **Pods inside the cluster** (the main purpose): frontend -> backend, app -> database, cross-namespace via `hello.demo`.
- **Worker nodes** (kube-proxy rules exist there).
- Cluster components: ingress controllers, monitoring, service meshes.
- **You, indirectly**, with `kubectl port-forward svc/hello 8080:80` (tunnels through the API server).

Cannot: your laptop directly, the internet, or VPC resources that aren't part of the cluster (no route to the Service range).

So yes: **ClusterIP is for communication between pods inside the cluster.**

## 6. Doubt: "Does it work like a load balancer?"

Same job, different place:

| | ClusterIP | LoadBalancer (AWS) |
|---|---|---|
| What it is | Forwarding rules on every node | A real Classic LB with its own DNS name |
| Reachable from | Inside the cluster only | The internet |
| Cost | Free | ~$0.025/hr |
| Health check | Pod readiness probe | AWS health check on the NodePort |

They're layers, not alternatives:

```
internet -> AWS LB -> node:30238 (NodePort) -> ClusterIP rules -> pod
```

## 7. Doubt: "How does it decide which pod gets the request?"

- **Candidates**: pods matching the selector and passing readiness.
- **Choice**: kube-proxy picks **randomly per connection** (iptables mode, the usual default incl. EKS). IPVS mode can do round robin / least connections.
- **Per connection, not per request**: once a TCP connection is set up, conntrack keeps it on the same pod.
- No awareness of how busy a pod is. Lab result: 14 vs 9 requests, roughly even, not exact.
- Long-lived connections (keep-alive, gRPC, DB) can be uneven; one client holding one connection hits one pod.
- `sessionAffinity: ClientIP` pins a client IP to one pod (off by default).
- Smarter routing (least-loaded, per-request, retries) is the job of an Ingress controller or service mesh.

## 8. Doubt: "How does a frontend know the backend's name? How many Services do I need?" (A <-> B <-> C)

**A Service belongs to the receiving side**, not to a pair of servers. One Service per group of pods that something calls.

```
A  ->  B  ->  C
```

| Service | Selects | Used by |
|---|---|---|
| `server-b` | B pods | A calls B |
| `server-c` | C pods | B calls C |
| (none for A) | | needed only if something calls A, e.g. an Ingress/LoadBalancer for users |

- A -> B -> C needs **2 ClusterIP Services**; 3 if A is also called by something.
- If C also calls B, nothing changes: `server-b` already exists and **doesn't care who the caller is**.
- **One Service for both B and C**: no. The selector picks one set of pods; callers would randomly get B or C.
- One Service can expose **several ports** (e.g. 80 and 9090) and any TCP/UDP protocol, not just HTTP.

**How does A learn B's name?** Kubernetes doesn't tell it. You choose the Service name in YAML and **configure it in A**, usually as an environment variable (`BACKEND_URL=http://server-b`) or config. CoreDNS resolves `server-b` (same namespace) or `server-b.<namespace>` (other namespace) to the ClusterIP.

Illustrative YAML (not run):

```yaml
apiVersion: v1
kind: Service
metadata: { name: server-b, namespace: demo }
spec:
  selector: { app: server-b }      # matches the B pods' label
  ports: [{ port: 80, targetPort: 8080 }]
---
apiVersion: v1
kind: Service
metadata: { name: server-c, namespace: demo }
spec:
  selector: { app: server-c }
  ports: [{ port: 80, targetPort: 8080 }]
---
# In A's Deployment:  env: BACKEND_URL=http://server-b
# In B's Deployment:  env: DOWNSTREAM_URL=http://server-c
```

## 9. Cheat sheet

| Question | Answer |
|---|---|
| What does ClusterIP do? | Forwards traffic from a stable name/IP to healthy pods |
| Is the IP real? | No, virtual (rules on nodes); not pingable |
| Who uses it? | Pods inside the cluster |
| Like a load balancer? | Yes, internal only, free, no separate machine |
| How does it pick a pod? | Random per connection (iptables), among Ready pods |
| Who needs a Service? | Whoever receives calls |
| A -> B -> C needs? | 2 Services (`server-b`, `server-c`) |
| How does A find B? | A DNS name you configure, e.g. `http://server-b` |
| Need access from outside? | Add NodePort / LoadBalancer / Ingress on top |

## 10. Commands

```
kubectl -n demo get pods -o wide       # pod IPs (VPC range)
kubectl get nodes -o wide              # node IPs
kubectl -n demo get svc                # ClusterIPs (Service range)
kubectl -n demo get endpoints hello    # pod IPs the Service forwards to
kubectl -n demo run tmp --rm -it --image=busybox --restart=Never -- wget -qO- hello
```
