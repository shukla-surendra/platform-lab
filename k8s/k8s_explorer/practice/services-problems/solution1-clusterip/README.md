# Solution 1: a ClusterIP Service fixes "Pod IPs keep changing"

Fixes the problem shown in [`../problem1-clusterip`](../problem1-clusterip).

**This folder is independent.** It creates its own backend in its own namespace (`solution1`), so you do
not need to run the problem first, and the two can even run at the same time.
It also starts the "saved Pod IP" caller from the problem, so you can see **broken and fixed side by side**.

## Quick way: run it with a script

```bash
cd k8s/k8s_explorer/practice/services-problems/solution1-clusterip
./run-solution.sh           # pauses at each step (press Enter to continue)
./run-solution.sh --yes     # no pauses, runs straight through
./cleanup.sh                # removes everything when you are done
```

The sections below explain the same steps by hand. Use the script first, then read the matching part.

## The fix in one picture

```
caller ──"backend-svc"──> Service (fixed IP + name)
                           │ looks up Pods by LABEL, keeps a live list
                           ├──> Pod B
                           ├──> Pod C
                           └──> Pod D (the replacement, picked up automatically)
```

## Files

| File | What it is |
|---|---|
| `00-backend.yaml` | The namespace `solution1` and 3 backend Pods (same app as the problem) |
| `01-service-clusterip.yaml` | **The fix**: a Service named `backend-svc` |
| `02-caller-via-service.yaml` | **The fixed caller**: calls the Service name instead of a Pod IP |
| `run-solution.sh` | Runs everything below for you (`--yes` skips the pauses) |
| `cleanup.sh` | Deletes the `solution1` namespace (does not touch `problem1`) |

Every command below uses `-n solution1` because everything lives in that namespace.

## What the script does, step by step

### Step 1: Create the backend

```bash
kubectl apply -f 00-backend.yaml
kubectl -n solution1 get pods -o wide
```

3 Pods, each with its own IP.

### Step 2: Start the OLD kind of caller (saved Pod IP), for comparison

```bash
TARGET_POD=$(kubectl -n solution1 get pods -l app=backend -o jsonpath='{.items[0].metadata.name}')
TARGET_IP=$(kubectl -n solution1 get pod $TARGET_POD -o jsonpath='{.status.podIP}')
kubectl -n solution1 run caller-pod-ip --image=busybox:1.36 --restart=Never -- sh -c \
  "while true; do if out=\$(wget -T 2 -qO- http://$TARGET_IP); then echo \"\$(date +%T) OK     \$out\"; else echo \"\$(date +%T) FAILED calling $TARGET_IP\"; fi; sleep 2; done"
kubectl -n solution1 logs caller-pod-ip
```

It works for now, always answered by the same Pod.

### Step 3: THE FIX. Create the Service

Read `01-service-clusterip.yaml` first. The important lines:

```yaml
spec:
  type: ClusterIP        # reachable only inside the cluster (the default)
  selector:
    app: backend         # "send traffic to every Pod that has the label app=backend"
  ports:
  - port: 80             # callers use backend-svc:80
    targetPort: 80       # the container listens on 80
```

The Service **does not know any Pod IPs in advance**. It watches Pods with the label `app=backend` and keeps
a live list. The Pods got that label from the Deployment (`00-backend.yaml`, under `template.metadata.labels`).

```bash
kubectl apply -f 01-service-clusterip.yaml
kubectl -n solution1 get svc backend-svc
```

```
NAME          TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)
backend-svc   ClusterIP   10.110.4.15     <none>        80/TCP
```

`CLUSTER-IP` is the Service's **stable address**; it does not change when Pods change.
`EXTERNAL-IP <none>` means it is not reachable from outside the cluster (that is NodePort's job, next lesson).

### Step 4: See which Pods the Service found (this is how you CHECK a Service)

```bash
kubectl -n solution1 get endpointslice -l kubernetes.io/service-name=backend-svc \
  -o jsonpath='{range .items[0].endpoints[*]}{.addresses[0]}{"  "}{.targetRef.name}{"\n"}{end}'
kubectl -n solution1 get pods -o wide
```

The Service's list and `get pods` show the **same 3 Pod IPs**. The EndpointSlice is the Service's live list of
Pods. **When a Service "doesn't work", this list is the first thing to check.**
You can also use `kubectl -n solution1 describe svc backend-svc` and read the `Endpoints:` line.

### Step 5: Start a caller that uses the Service NAME

```bash
kubectl apply -f 02-caller-via-service.yaml
sleep 10
kubectl -n solution1 logs caller-service
```

```
17:22:54 OK     Hello from backend-5f474dccb9-vb4dx
17:22:56 OK     Hello from backend-5f474dccb9-vb4dx
17:23:00 OK     Hello from backend-5f474dccb9-pn249
```

**Different Pods answer.** The Service spreads connections across all 3. The caller only wrote
`http://backend-svc`. The name works because the cluster's DNS maps `backend-svc` to the Service IP.

### Step 6: Kill the Pod the old caller saved

```bash
kubectl -n solution1 delete pod $TARGET_POD
sleep 14
kubectl -n solution1 get pods -o wide        # a replacement with a NEW IP
```

Check the Service's list again (Step 4): the dead Pod's IP is gone and the replacement's IP is in it.
**The Service updated its own list. The caller needed no change.**

### Step 7: Compare the two callers

```bash
kubectl -n solution1 logs caller-service | grep -c FAILED       # 0
kubectl -n solution1 logs caller-pod-ip | tail -3               # FAILED calling <old IP>
```

In my run, `caller-service` had **23 OK and 0 FAILED**, and `caller-pod-ip` had `FAILED calling 10.244.0.67`.

Creating the Service did not fix the saved-IP caller. **The fix is that the caller uses the Service.**

## What you should now understand

1. Pod IPs are **temporary**. Anything that depends on one will break.
2. A Service is a **stable IP and name** in front of Pods.
3. It finds Pods by **label** (`selector` in the Service must match `labels` on the Pods).
4. It keeps a **live list** (EndpointSlice) and updates it as Pods come and go.
5. It **spreads** connections across the Pods.
6. `type: ClusterIP` means: **inside the cluster only.**

### Check yourself

- If you change the Service selector to `app: backnd` (typo), what would the EndpointSlice show, and what would happen to `caller-service`? (Try it: `kubectl -n solution1 edit svc backend-svc`, then read the logs.)
- What do the Service's `port` and `targetPort` each mean?
- Why did the Service keep working while `caller-pod-ip` did not?

## Cleanup

```bash
./cleanup.sh        # or: kubectl delete namespace solution1
```

## Next: Problem 2

ClusterIP only works **inside** the cluster. What if something **outside** (your laptop's browser) needs
to reach the backend? That's **NodePort**.
