# Problem 2: "A ClusterIP only works INSIDE the cluster"

This folder only **creates and shows the problem**. The fix is in the sibling folder
[`../solution2-nodeport`](../solution2-nodeport).

**The two folders are independent.** Each has its own backend, its own namespace (`problem2` here,
`solution2` there), and its own `cleanup.sh`. You can run either one first, or both at the same time.

Names and IPs in your output will differ from the examples below. Compare the **pattern**, not the exact values.

Lesson 1 gave callers *inside* the cluster a stable address (a ClusterIP Service). This lesson is about
everyone *outside* it: a browser, a mobile app, another team's server.

## Quick way: run it with a script

```bash
cd k8s/k8s_explorer/practice/services-problems/problem2-nodeport
./run-problem.sh            # pauses at each step (press Enter to continue)
./run-problem.sh --yes      # no pauses, runs straight through
./cleanup.sh                # removes everything when you are done
```

Needs Docker running (it is used to play "a client outside the cluster", explained in Step 3).
The rest of this README explains the same steps by hand.

## The problem in one picture

```
 OUTSIDE the cluster                         INSIDE the cluster
 ┌──────────────┐                 ┌──────────────────────────────────────────┐
 │ browser,     │   ──── X ────>  │  Service backend-svc (ClusterIP 10.x.x.x)│
 │ other server │   no route in   │      ├──> Pod   ├──> Pod   └──> Pod      │
 └──────────────┘                 └──────────────────────────────────────────┘
                                   callers INSIDE can use the Service fine
```

## Files

| File | What it is |
|---|---|
| `00-backend.yaml` | The namespace `problem2`, a Deployment of **3 Pods**, and a plain ClusterIP Service `backend-svc` |
| `run-problem.sh` | Runs the steps below for you (`--yes` skips the pauses) |
| `cleanup.sh` | Deletes the `problem2` namespace (does not touch `solution2`) |

Every command below uses `-n problem2` because everything lives in that namespace.

## What the script does, step by step

### Step 1: Create the backend and the Service

```bash
kubectl apply -f 00-backend.yaml
kubectl -n problem2 get pods -o wide
kubectl -n problem2 get svc backend-svc
```

```
NAME          TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)
backend-svc   ClusterIP   10.97.66.142    <none>        80/TCP
```

`EXTERNAL-IP <none>` already hints at it: nothing here is meant to be reachable from outside.

### Step 2: Callers INSIDE the cluster work

```bash
kubectl -n problem2 run t --image=busybox:1.36 --rm -it --restart=Never -- \
  sh -c 'for i in 1 2 3 4 5 6; do wget -qO- http://backend-svc; done'
```

You get `Hello from backend-...` with different Pod names. Inside the cluster, the Service does its job.

### Step 3: Callers OUTSIDE the cluster do not

**Who is "outside"?** On a Mac with minikube's Docker driver, the node is a container, and your laptop can't
reach its IP at all. So the script plays "a client outside the cluster" with a throwaway Docker container
on the **same Docker network as the node**. It can reach the node's IP, like another machine on the same
LAN, but it is **not a Pod** and knows nothing about Kubernetes.

```bash
NODE_IP=$(minikube ip)
CLUSTER_IP=$(kubectl -n problem2 get svc backend-svc -o jsonpath='{.spec.clusterIP}')
POD_IP=$(kubectl -n problem2 get pods -l app=backend -o jsonpath='{.items[0].status.podIP}')

# one request from an outside client (3 second timeout)
docker run --rm --network minikube busybox:1.36 wget -T 3 -qO- http://$CLUSTER_IP
```

What I saw trying four different addresses from outside:

| Try | Result | Why |
|---|---|---|
| `http://<ClusterIP>` | `download timed out` | A virtual IP that exists only as forwarding rules inside the cluster's nodes |
| `http://<Pod IP>` | `download timed out` | On the cluster's private Pod network, not routable from outside (and it changes anyway) |
| `http://<node IP>` (port 80) | `Connection refused` | The node is reachable, but nothing listens on port 80 on the node |
| `http://backend-svc` | `bad address 'backend-svc'` | Service names are cluster DNS. Outside, nothing resolves them |

### Step 4: The problem

The backend is healthy, and the Service works for callers inside. But **nothing outside can reach it**.
A ClusterIP is for traffic that starts inside the cluster. We need a way in: **a port on the node itself**.

## What you should now understand

1. A ClusterIP is reachable **only from inside** the cluster.
2. The Pod IPs and the ClusterIP are on private, cluster-internal networks.
3. The node's own IP **is** reachable from outside, but only on ports something is actually forwarding.
4. Service names (`backend-svc`) only resolve **inside** the cluster.

### Check yourself

- Why does the request to the node IP say "connection refused" while the ClusterIP request "times out"?
  (Hint: one of them reaches a machine that has no listener; the other reaches nothing at all.)
- If a Service has `EXTERNAL-IP <none>`, what does that tell you?

## Next

The fix is in [`../solution2-nodeport`](../solution2-nodeport). It is self-contained: it builds its own
backend, so you do **not** need to keep this lab running.

Clean up this lab when you are done: `./cleanup.sh` (or `kubectl delete namespace problem2`)
