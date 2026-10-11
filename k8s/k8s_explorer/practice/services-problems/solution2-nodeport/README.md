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

### Try it from your Mac browser

Docker Desktop on macOS can't reach the node IP directly, so minikube makes a tunnel for you:

```bash
minikube service backend-svc -n solution2 --url
# prints something like http://127.0.0.1:53124 . Open it in a browser. Keep this terminal open.
```

This is a minikube convenience on macOS. It is not how NodePort works elsewhere, where you'd use `http://<node-ip>:30080`.

## What you should now understand

1. `type: NodePort` opens **the same port on every node** (30000-32767) and forwards it to the Service.
2. It is a **superset of ClusterIP**: it keeps the ClusterIP, the in-cluster name, and the load balancing across Pods.
3. `PORT(S) 80:30080` means `service port : node port`.
4. A node port is a **forwarding rule** set by kube-proxy, not a process.
5. Clients outside use `http://<node-ip>:<nodePort>`.

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
