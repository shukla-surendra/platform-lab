# Problem 1: "Pod IPs keep changing"

This folder only **creates and shows the problem**. The fix is in the sibling folder
[`../solution1-clusterip`](../solution1-clusterip).

**The two folders are independent.** Each has its own backend, its own namespace (`problem1` here,
`solution1` there), and its own `cleanup.sh`. You can run either one first, or both at the same time.

Names and IPs in your output will differ from the examples below. Compare the **pattern**, not the exact values.

## Quick way: run it with a script

If typing the commands one by one is hard to follow, run the script instead. It does every step below
for you, prints what is happening and what to look for, and **pauses between steps** so you can read.

```bash
cd k8s/k8s_explorer/practice/services-problems/problem1-clusterip
./run-problem.sh            # pauses at each step (press Enter to continue)
./run-problem.sh --yes      # no pauses, runs straight through
./cleanup.sh                # removes everything when you are done
```

The rest of this README explains the same steps by hand, so you can see what each command does.
Use the script first, then read the matching part below.

## The problem in one picture

```
caller ──saved IP 10.244.0.28──> Pod A
                                  │
                          Pod A dies, the Deployment creates a replacement
                          with a NEW IP  ──>  the caller's saved IP points at nothing
```

## Files

| File | What it is |
|---|---|
| `00-backend.yaml` | The namespace and a Deployment: **3 Pods** of a web server that replies `Hello from <pod name>` |
| `run-problem.sh` | Runs Parts 1 and 2 for you, step by step (`--yes` skips the pauses) |
| `cleanup.sh` | Deletes the `problem1` namespace and everything in it (does not touch `solution1`) |

The broken caller is created with a command in Part 2, because it needs a Pod IP that only exists on your cluster.

## Part 0: See what you have

```bash
kubectl get nodes                       # your cluster is up
```

## Part 1: Create the backend

```bash
kubectl apply -f 00-backend.yaml
kubectl -n problem1 get pods -o wide
```

You should see **3 Pods**, each with its **own IP** (the `IP` column):

```
NAME                       READY   STATUS    IP
backend-5f474dccb9-79bkx   1/1     Running   10.244.0.28
backend-5f474dccb9-kvb5p   1/1     Running   10.244.0.26
backend-5f474dccb9-mln2z   1/1     Running   10.244.0.27
```

**What to understand:** there is no single address for "the backend". There are three, and each is a
Pod IP.

Why `-n problem1`? Kubernetes groups things into namespaces. Everything here lives in `problem1`, so every
command needs `-n problem1` to look there.

### 1b. Check that the backend answers

The Pods are `Running` and `1/1` ready, but does the web server answer? Test it before building on it.

**You can't call a Pod IP from your own laptop.** Pod IPs only exist *inside* the cluster, so this times out:

```bash
curl -m 3 http://10.244.0.42      # from your Mac: no answer
```

The test has to run **from a Pod inside the cluster**. Copy one value from the `IP` column of
`kubectl -n problem1 get pods -o wide`, and run a throwaway Pod that calls it:

```bash
kubectl -n problem1 run test --image=busybox:1.36 --rm -it --restart=Never -- wget -qO- http://10.244.0.42
```

(Replace the IP with yours.) Expected:

```
Hello from backend-5f474dccb9-8lgbl
pod "test" deleted from problem1 namespace
```

What each part means:

| Part | Meaning |
|---|---|
| `kubectl -n problem1 run test` | Start one Pod named `test` in the `problem1` namespace |
| `--image=busybox:1.36` | A tiny image that has `wget` |
| `--rm` | Delete the Pod when it finishes |
| `-it` | Attach your terminal so you see the output |
| `--restart=Never` | A one-off Pod, not a Deployment that restarts it |
| `-- wget -qO- http://...` | The command to run inside the Pod. `-q` quiet, `-O-` print the reply to the screen |

The reply names the Pod that answered. If you see `Hello from backend-...`, the backend works.

## Part 2: Replicate the problem

### 2a. Make a caller that saves one Pod's IP

This simulates an app whose config says "the backend is at 10.244.0.28".

```bash
# pick the first backend Pod and remember its name and IP
# (TARGET_POD is used again in 2b, so keep working in this same terminal tab)
TARGET_POD=$(kubectl -n problem1 get pods -l app=backend -o jsonpath='{.items[0].metadata.name}')
TARGET_IP=$(kubectl -n problem1 get pod $TARGET_POD -o jsonpath='{.status.podIP}')
echo "saving: $TARGET_POD  $TARGET_IP"

# start a caller that calls that IP every 2 seconds
kubectl -n problem1 run caller-pod-ip --image=busybox:1.36 --restart=Never -- sh -c \
  "while true; do if out=\$(wget -T 2 -qO- http://$TARGET_IP); then echo \"\$(date +%T) OK     \$out\"; else echo \"\$(date +%T) FAILED calling $TARGET_IP\"; fi; sleep 2; done"
```

Wait about 10 seconds, then read what the caller prints:

```bash
kubectl -n problem1 logs caller-pod-ip
```

```
16:45:43 OK     Hello from backend-5f474dccb9-79bkx
16:45:45 OK     Hello from backend-5f474dccb9-79bkx
```

It works, and **always the same Pod answers**, because the caller talks to one IP.

> Tip: `kubectl -n problem1 logs -f caller-pod-ip` follows the log live. Press Ctrl+C to stop.

### 2b. Kill that Pod

```bash
kubectl -n problem1 delete pod $TARGET_POD
kubectl -n problem1 get pods -o wide
```

The Deployment is told "keep 3 Pods", so it **immediately creates a replacement**, with a different name and a **different IP**:

```
backend-5f474dccb9-fbbtv   Running   10.244.0.30     <- NEW Pod, NEW IP
backend-5f474dccb9-kvb5p   Running   10.244.0.26
backend-5f474dccb9-mln2z   Running   10.244.0.27
```

(The old IP `10.244.0.28` is gone.)

### 2c. The problem

```bash
kubectl -n problem1 logs caller-pod-ip | tail -4
```

```
wget: download timed out
16:46:21 FAILED calling 10.244.0.28
wget: download timed out
16:46:25 FAILED calling 10.244.0.28
```

**This is the problem.** Three healthy Pods are running right now, but the caller is stuck calling an IP
that no longer exists. Nothing is broken in the backend. The caller just has no way to know the IP
changed.

> In real life this is every restart, rolling update, node failure, or scale event.

## If something looks off

| Symptom | Cause and fix |
|---|---|
| `$TARGET_POD` or `$TARGET_IP` is empty | You opened a new terminal tab (variables are per tab). Re-run the three lines at the top of 2a |
| `pods "caller-pod-ip" already exists` | An earlier attempt is still there. `kubectl -n problem1 delete pod caller-pod-ip`, then run 2a again |
| `kubectl logs caller-pod-ip` is empty | The image is still pulling or the Pod just started. Wait a few seconds. Check `kubectl -n problem1 get pods` |
| Caller shows `FAILED` straight away, before you deleted anything | The IP in `$TARGET_IP` is wrong or stale. Delete the caller and redo 2a |
| `curl` from your Mac to a Pod IP times out | Expected: Pod IPs are inside the cluster. Test from a Pod (Part 1b) |
| `Error from server (NotFound): namespaces "problem1" not found` | Part 1 wasn't applied. `kubectl apply -f 00-backend.yaml` |
| `namespace problem1 is being terminated` on apply | A previous cleanup is still finishing. Wait until `kubectl get ns problem1` says NotFound |

## What you should now understand

1. A Deployment keeps the **number** of Pods right, but gives every new Pod a **new IP**.
2. Anything that saved a Pod IP breaks the moment that Pod is replaced.
3. The backend was never broken. The **caller** has no way to find the new IP.

## Next

The fix is in [`../solution1-clusterip`](../solution1-clusterip). It is self-contained: it builds its own
backend, so you do **not** need to keep this lab running.

Clean up this lab when you are done: `./cleanup.sh` (or `kubectl delete namespace problem1`)
