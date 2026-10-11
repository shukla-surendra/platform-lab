# Solution 2: a NodePort Service opens a way in from outside

Fixes the problem shown in [`../problem2-nodeport`](../problem2-nodeport): a ClusterIP is unreachable from outside.

**This folder is independent.** It creates its own backend in its own namespace (`solution2`), so you do
not need to run the problem first, and the two can even run at the same time.

## Quick way: run it with a script

```bash
cd k8s/k8s_explorer/practice/services-problems/solution2-nodeport
./run-solution.sh           # pauses at each step (press Enter to continue)
./run-solution.sh --yes     # no pauses, runs straight through
./cleanup.sh                # removes everything when you are done
```

Needs Docker running (it plays "a client outside the cluster"; see the problem README, Step 3).
The sections below explain the same steps by hand.

## The fix in one picture

```
 OUTSIDE                         NODE (192.168.49.2)                  INSIDE the cluster
 ┌──────────┐   http://node-ip:30080   ┌────────────────┐       ┌─────────────────────────────┐
 │  client  │ ───────────────────────> │ port 30080     │ ────> │ Service backend-svc         │
 └──────────┘                          │ (forwarding    │       │  ├──> Pod  ├──> Pod  └─> Pod │
                                       │  rule, on every│       └─────────────────────────────┘
                                       │  node)         │
                                       └────────────────┘
```

A NodePort Service **builds on** a ClusterIP: it still has the ClusterIP and in-cluster name, and it adds a
port that is opened on **every node**.

## Files

| File | What it is |
|---|---|
| `00-backend.yaml` | The namespace `solution2` and 3 backend Pods |
| `01-service-clusterip.yaml` | The "before": a plain ClusterIP Service `backend-svc` |
| `02-service-nodeport.yaml` | **The fix**: the same Service with `type: NodePort` |
| `run-solution.sh` | Runs everything below for you (`--yes` skips the pauses) |
| `cleanup.sh` | Deletes the `solution2` namespace (does not touch `problem2`) |

Every command below uses `-n solution2` because everything lives in that namespace.

## What the script does, step by step

### Step 1: Backend and the "before" Service

```bash
kubectl apply -f 00-backend.yaml
kubectl apply -f 01-service-clusterip.yaml
kubectl -n solution2 get svc backend-svc
```

```
NAME          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)
backend-svc   ClusterIP   10.96.68.150   <none>        80/TCP
```

### Step 2: Confirm it fails from outside

```bash
NODE_IP=$(minikube ip)
docker run --rm --network minikube busybox:1.36 wget -T 3 -qO- http://$NODE_IP:30080
# wget: can't connect to remote host (192.168.49.2): Connection refused
```

Nothing is forwarding port 30080 yet.

### Step 3: THE FIX. Change `type` to NodePort

Read `02-service-nodeport.yaml`. The important lines:

```yaml
spec:
  type: NodePort          # was ClusterIP
  selector:
    app: backend
  ports:
  - port: 80              # the Service's own port, for callers inside the cluster
    targetPort: 80        # the container's port
    nodePort: 30080       # the port opened on EVERY node (must be 30000-32767)
```

Leave `nodePort` out and Kubernetes picks a free port from that range. We pin it so the README stays predictable.

```bash
kubectl apply -f 02-service-nodeport.yaml        # "service/backend-svc configured": updated in place
kubectl -n solution2 get svc backend-svc
```

```
NAME          TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)
backend-svc   NodePort   10.96.68.150   <none>        80:30080/TCP
```

Two things to notice:
- `PORT(S)` is `80:30080/TCP`, read as **`service port : node port`**.
- `CLUSTER-IP` is **the same** as before. The Service was changed in place, and it kept its ClusterIP.

### Step 4: Call it from OUTSIDE

```bash
docker run --rm --network minikube busybox:1.36 wget -T 3 -qO- http://$NODE_IP:30080
```

12 requests from outside came back 4 / 4 / 4 across the three Pods:

```
   4 Hello from backend-5f474dccb9-fww82
   4 Hello from backend-5f474dccb9-qwtpt
   4 Hello from backend-5f474dccb9-zqqq9
```

(Right after you apply the change, kube-proxy needs a moment to program the new rule, so the first call
can fail. The script waits and retries.)

### Step 5: Callers inside still work

```bash
kubectl -n solution2 run t --image=busybox:1.36 --rm -it --restart=Never -- wget -qO- http://backend-svc
```

Unchanged. NodePort **adds** a way in; it doesn't remove the ClusterIP.

### Step 6: How it works

`kube-proxy`, running on the node, added forwarding rules in the chain `KUBE-NODEPORTS`:

```bash
minikube ssh "sudo iptables -t nat -S KUBE-NODEPORTS | grep solution2/backend-svc"
```

I checked with `ss -ltn` on the node: **no process listens on 30080**. A node port is a forwarding rule,
not a server. (This node's iptables output doesn't print the port number inside the rule, so the
proof that the rule works is Step 4.)

### Step 7: Kill a Pod while calling from outside

20 requests from outside while a backend Pod was deleted: all 20 got replies, from the remaining and the
replacement Pods. The Service updates its Pod list on its own, as in lesson 1.

### Step 8: What NodePort does NOT solve

- Clients must know **a node's IP** and a **high port** (30000-32767), not a name and port 80.
- If that node's IP changes, or that one node dies, a client pointed at it has no automatic failover to another node.
- Every Service needs its own port from a small range.
- You are exposing the **nodes** themselves.

That is what the next lesson, **LoadBalancer**, addresses.

## How to access the NodePort (and why it can look "not accessible")

The Service works, but **where you call it from decides which address works.** All results below were measured
on a minikube cluster using the Docker driver on macOS (Docker Desktop).

### Which route works from where

| You call from | Address | Works? | Why |
|---|---|---|---|
| A Pod in the cluster | `http://backend-svc` | Yes | Cluster DNS, ClusterIP |
| Inside the node (`minikube ssh`) | `http://localhost:30080` | Yes | You are on the node |
| A client on the node's Docker network | `http://<node-ip>:30080` | Yes | Can reach the node IP, like another machine on the LAN |
| **Your Mac** | `http://<node-ip>:30080` (e.g. `192.168.49.2`) | **No** | Docker Desktop keeps the node network inside its VM; the Mac has no route to it |
| **Your Mac** | `http://localhost:30080` | **No** | Nothing on your Mac listens on 30080. The node port lives on the node, not on your laptop |
| **Your Mac**, via the minikube tunnel | `http://127.0.0.1:<random port>` | **Yes, while the terminal stays open** | minikube forwards a local port to the Service |

This is a limit of **Docker Desktop on macOS**, not of NodePort. On a real cluster, or on Linux with the
Docker driver, `http://<node-ip>:30080` works directly from any machine that can reach the node.

### From your Mac: the tunnel

```bash
minikube service backend-svc -n solution2 --url
```

It prints a local address, for example:

```
http://127.0.0.1:49962
! Because you are using a Docker driver on darwin, the terminal needs to be open to run it.
```

1. **Leave that terminal open.** Ctrl+C or closing it kills the address immediately.
2. Use the printed address in a **second** terminal or a browser tab. It is **not** `30080`; the port is random each time you start the tunnel.

```bash
curl http://127.0.0.1:49962        # run it a few times: different Pod names answer
```

I ran this: 4 requests returned `Hello from backend-...` from three different Pods.

### From inside the node or the node's network (the "real" NodePort path, port 30080)

```bash
# on the node itself
minikube ssh "curl -s http://localhost:30080"

# from a client on the node's network (this is what the lesson script does)
docker run --rm --network minikube busybox:1.36 wget -qO- http://$(minikube ip):30080
```

### With more than one node: the port is open on every node

With a second node (`minikube-m03`, `192.168.49.4`) the same port answered on **both** nodes, even though
all three backend Pods were running on the first node:

```
NodePort via minikube     (192.168.49.2):30080 -> Hello from backend-...
NodePort via minikube-m03 (192.168.49.4):30080 -> Hello from backend-...
```

A request that lands on a node with no local backend Pod is forwarded across to a Pod on another node.
That is what "NodePort opens the port on **every** node" means, and it is also why NodePort can add an extra hop
(and why `externalTrafficPolicy: Local` exists: see `../../services-demo/problems/07-external-traffic-policy.yaml`).

To list your nodes and their IPs:

```bash
kubectl get nodes -o wide
```

### Troubleshooting: "I can't reach it"

Work down this list. It goes from the Service outward.

| # | Check | Command | Healthy result |
|---|---|---|---|
| 1 | Is the Service a NodePort? | `kubectl -n solution2 get svc backend-svc` | `TYPE NodePort`, `PORT(S) 80:30080/TCP` |
| 2 | Does it have endpoints? | `kubectl -n solution2 get endpointslice` | 3 Pod IPs listed |
| 3 | Are the Pods ready? | `kubectl -n solution2 get pods` | `1/1 Running` |
| 4 | Does it work from the node? | `minikube ssh "curl -s localhost:30080"` | `Hello from backend-...` |
| 5 | Does it work from the node's network? | the `docker run ... wget` command above | `Hello from backend-...` |
| 6 | Are you calling from your Mac? | | Then you need the tunnel; direct node IPs don't work on Docker Desktop |
| 7 | Is the tunnel terminal still open? | `pgrep -fl "minikube service"` | A process is listed |

| Symptom | Likely cause |
|---|---|
| Works in steps 4 and 5, but not from your Mac | Expected on macOS. Use the tunnel |
| Browser worked, then stopped | The tunnel terminal was closed or Ctrl+C'd. Start it again; it will print a **new** port |
| `localhost:30080` or `<node-ip>:30080` times out on your Mac | Same: no route from the Mac. Use the tunnel's address |
| Connection refused on `<node-ip>:30080` from the node network | The Service is still ClusterIP, or you used the wrong `nodePort`. Check step 1 |
| Timeout at step 5 right after `kubectl apply` | kube-proxy needs a few seconds to program the rule. Retry |
| Step 2 shows no endpoints | The Service `selector` does not match the Pod labels, or no Pod is ready (see lesson 1) |
| `Error from server (NotFound)` | The lab was cleaned up. `kubectl apply -f .` in this folder re-creates it |

### Apply everything in this folder at once

```bash
kubectl apply -f .
```

This applies the files in alphabetical order: `00-backend.yaml` (namespace and Pods), then
`01-service-clusterip.yaml` (the Service as ClusterIP), then `02-service-nodeport.yaml` (the same Service changed
to NodePort). The last file wins, so you end with `NodePort`. The output shows `service/backend-svc created`
then `service/backend-svc configured`. To skip the "before" step:
`kubectl apply -f 00-backend.yaml -f 02-service-nodeport.yaml`.

## How NodePort and ClusterIP relate (common misunderstandings)

### Misunderstanding 1: "NodePort forwards the request to the ClusterIP"

Not quite. The request is **not** sent to the ClusterIP address as a middle hop. The NodePort and the ClusterIP
are two separate **entrances** into the same Service logic. This is the rule layout on the node (kube-proxy in
iptables mode, checked on this minikube cluster; the hash suffixes will differ on yours):

```
Entrance A (NodePort):   KUBE-NODEPORTS ──> KUBE-EXT-5B3W... ──┐
                                                               ├──> KUBE-SVC-5B3W...  ──> picks 1 of 3 Pods
Entrance B (ClusterIP):  KUBE-SERVICES (dst <ClusterIP>) ──────┘     (1/3, 1/2, rest)     and rewrites the
                                                                      destination to the Pod IP, e.g. 10.244.0.102:80
```

- `KUBE-NODEPORTS` hands the packet to `KUBE-EXT-...`, which marks it for masquerade and jumps to `KUBE-SVC-...`.
- `KUBE-SERVICES` matches the **ClusterIP** as the destination and jumps to the **same** `KUBE-SVC-...` chain.
- `KUBE-SVC-...` picks one Pod at random and sends the traffic **straight to the Pod IP**.

You can look at it yourself:

```bash
minikube ssh "sudo iptables -t nat -S KUBE-NODEPORTS | grep solution2"
minikube ssh "sudo iptables -t nat -S KUBE-SERVICES | grep solution2"
```

### The test: remove the ClusterIP entrance, and the NodePort keeps working

I deleted only the ClusterIP rule from `KUBE-SERVICES` on the node and left the NodePort rule alone.

| After deleting the ClusterIP rule | Result |
|---|---|
| Outside client → `<node-ip>:30080` | **Still works** |
| On the node → `localhost:30080` | **Still works** |
| On the node → `<ClusterIP>:80` | `NO REPLY` (the entrance is gone) |
| A Pod → `<ClusterIP>:80` | **Still answered. I do not know why.** Don't draw conclusions from this one |

What this shows: the NodePort entrance does **not** go through the ClusterIP entrance. It does not show why the Pod
case behaved differently, and I did not investigate it.

kube-proxy did **not** put the single deleted rule back on its own, so I restored the node by restarting kube-proxy:

```bash
kubectl -n kube-system rollout restart ds/kube-proxy
```

After that the ClusterIP answered from the node and from a Pod, and the NodePort answered from outside.
Don't hand-edit iptables rules on a cluster you care about. kube-proxy owns them.

### How they are connected, and how they are not

| Level | Together or independent? |
|---|---|
| The Service **object** | Together. One Service has a ClusterIP **and** a node port; `type: NodePort` includes both |
| The **Pod list** (EndpointSlice) | Together. Both entrances use the same list |
| The **load-balancing chain** (`KUBE-SVC-...`) | Together. Both entrances jump into it |
| The **entrance rules** | **Independent.** Neither passes through the other |
| The **packet path** | No hand-off. The NodePort packet is never sent to the ClusterIP address |

An analogy: two doors into the same lobby. Locking one door does not affect the other, and both lead to the same
reception desk. This describes kube-proxy in iptables mode. IPVS, nftables and CNIs that replace kube-proxy
(for example Cilium) implement it differently.

### Misunderstanding 2: "NodePort handles Pod IP changes, so I don't need ClusterIP"

Handling Pod IP changes is the **Service's** job, in every type:

- The Service finds Pods by label and keeps a live list of them (the EndpointSlice).
- It updates that list when Pods are replaced.
- It spreads requests across the Pods.

| Type | Handles Pod IP changes? | Who can call it |
|---|---|---|
| ClusterIP | Yes | Callers inside the cluster |
| NodePort | **Yes, the same way** | Inside, **plus** anyone who can reach a node's IP |
| LoadBalancer | **Yes, the same way** | All of the above, **plus** an external load balancer address |

```
                    handles Pod IP changes (same machinery in every type)
                       ┌───────────────────────────────────────────┐
 ClusterIP entrance ──>│                                           │
 NodePort entrance  ──>│  Service: selector → EndpointSlice → Pods │
                       └───────────────────────────────────────────┘
        ^ the types differ only in which entrances exist
```

- A NodePort Service **still has a ClusterIP**: it was the same before and after switching types in Step 3.
- You may never use the ClusterIP address if you only call the node port. But the **Service** is what makes Pod
  replacement invisible, and that is what lesson 1 demonstrated. Step 7 above shows it: a Pod was deleted while
  20 requests came in through the node port, and all 20 got replies.
- Removing the ClusterIP **rule** did not break the NodePort (the test above). The ClusterIP **address** is not
  needed for the node port. The **Service** is.

> **Summary.** A Service solves "Pod IPs change". ClusterIP, NodePort and LoadBalancer are three ways to **reach** a
> Service, each adding a wider entrance. NodePort does not replace ClusterIP: it is a ClusterIP Service with an
> extra port opened on the nodes.

This is why the lessons go in this order: lesson 1 stable address for changing Pods (every type needs it),
lesson 2 a way in from outside, lesson 3 a stable, managed external address (LoadBalancer).

### Detail: "opens a port on the node"

- It is **every address** on the node (all its IPs), and on **every node**, not one specific IP. It is the node's own
  address (an EC2 private or public IP, a VM IP), not necessarily "physical".
- Nothing **listens** on that port. I checked with `ss -ltn` on the node: no process on 30080. It is a forwarding
  rule that kube-proxy sets up, not a server.

## On a real cluster (for example EKS)

The Docker Desktop limit above is specific to minikube on macOS. On EKS the nodes are EC2 instances on a real
network, and `http://<node-ip>:<nodePort>` is the normal way to reach a NodePort. Three things decide whether it works.
(I have not checked an EKS cluster for this. It is general knowledge: confirm against your own setup.)

| Needs | Detail |
|---|---|
| A reachable node IP | The node's **private IP** works from inside the VPC, or over a VPN, Direct Connect or bastion host. A **public IP** exists only if the node is in a public subnet and was given one. `kubectl get nodes -o wide` shows `INTERNAL-IP` and `EXTERNAL-IP` |
| A security group rule | An inbound rule on the **node security group** for the node port (30080, or 30000-32767) from your source. Default EKS setups do not open this to the internet or your laptop, so without a rule the call times out |
| A network path | The node's subnet needs a route from where you call. A node in a private subnet is not reachable from your laptop without a VPN, SSM port forwarding or a bastion |

```
minikube on macOS:   Mac ──X──> node IP        (needs the minikube tunnel)
EKS:                 client ──> <node IP>:30080
                              works if: IP reachable + security group allows 30080 + a route exists
```

Why NodePort is rare in production on EKS:
- Clients would need node IPs, and nodes are replaced (scaling, upgrades, spot interruptions), so those IPs change.
- A client pointed at one node has no failover if that node dies.
- It means opening high ports on your nodes.
- `type: LoadBalancer` on EKS creates an AWS load balancer with a stable DNS name and health checks and keeps node IPs
  private. That is the next lesson.

## What you should now understand

1. `type: NodePort` opens **the same port on every node** (30000-32767) and forwards it to the Service.
2. It is a **superset of ClusterIP**: it keeps the ClusterIP, the in-cluster name, and the load balancing across Pods.
3. `PORT(S) 80:30080` means `service port : node port`.
4. A node port is a **forwarding rule** set by kube-proxy, not a process.
5. Clients outside use `http://<node-ip>:<nodePort>`.
6. NodePort and ClusterIP are **two entrances into the same Service**. NodePort does not forward to the ClusterIP, and removing the ClusterIP's rule does not break the node port.
7. **Handling Pod IP changes is the Service's job in every type.** NodePort adds a way in; it does not replace what ClusterIP showed in lesson 1.

### Check yourself

- Which of these still works after changing to NodePort: `http://backend-svc` from a Pod, `http://<ClusterIP>` from a Pod, `http://<node-ip>:30080` from outside?
- What happens if you leave out the `nodePort:` line? (Try it, then run `kubectl -n solution2 get svc`.)
- Why would a real production site not want its users to type `http://<node-ip>:30080`?

## Cleanup

```bash
./cleanup.sh        # or: kubectl delete namespace solution2
```

## Next: Problem 3

NodePort works but is awkward: a node IP, a high port, no failover. What if you want **one clean, stable
address**, like a real website? That's **LoadBalancer**.
