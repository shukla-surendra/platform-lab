# Problem 1: "Every app needs its own port" (port sprawl)

This folder only **creates and shows the problem**. The fix is in [`../solution1-ingress`](../solution1-ingress).

**The two folders are independent.** Each has its own namespace (`ingress-p1` here, `ingress-s1` there) and its own
`cleanup.sh`. You can run either one first. This problem lab does not need the ingress controller at all.

Names and IPs in your output will differ from the examples. Compare the **pattern**.

## Quick way: run it with a script

```bash
cd k8s/k8s_explorer/practice/ingress-lab/problem1-port-sprawl
./run-problem.sh            # pauses at each step (press Enter)
./run-problem.sh --yes      # no pauses
./cleanup.sh                # removes the lab
```

## The problem in one picture

```
 client ──> http://<node-ip>:30101 ──> shop-svc ──> shop Pods
 client ──> http://<node-ip>:30102 ──> blog-svc ──> blog Pods       three entrances, three port numbers,
 client ──> http://<node-ip>:30103 ──> api-svc  ──> api Pods        no names, no paths
```

## Files

| File | What it is |
|---|---|
| `00-apps.yaml` | Namespace `ingress-p1`; three apps (shop, blog, api), 2 Pods each; each Service is `NodePort` with its own pinned port |
| `run-problem.sh` | Runs the steps below |
| `cleanup.sh` | Deletes the `ingress-p1` namespace (does not touch the ingress controller or `ingress-s1`) |

## What the script does

### Step 1: Create three apps, each with its own NodePort

```bash
kubectl apply -f 00-apps.yaml
kubectl -n ingress-p1 get svc
```
```
NAME       TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)
api-svc    NodePort   10.98.206.125    <none>        80:30103/TCP
blog-svc   NodePort   10.107.180.132   <none>        80:30102/TCP
shop-svc   NodePort   10.97.56.194     <none>        80:30101/TCP
```

### Step 2: It works, if the client knows the node IP and the right port

Called from a client on the node's network (see the NodePort lessons for why):
```
shop  -> http://192.168.49.2:30101 : shop app, answered by pod shop-...
blog  -> http://192.168.49.2:30102 : blog app, answered by pod blog-...
api   -> http://192.168.49.2:30103 : api app, answered by pod api-...
```

### Step 3: The pain points

1. **A 4th app needs a 4th port.** Ports come from one shared range (30000-32767). Reusing one fails:
   ```
   The Service "docs-svc" is invalid: spec.ports[0].nodePort: Invalid value: 30101: provided port is already allocated
   ```
2. **No names.** Users want `shop.example.com`, not an IP and a port.
3. **No path routing.** You cannot say "everything under `/api` goes to the api app" on one address.
4. **Clients must know a node's IP**, and nodes come and go. Every app is exposed on **every** node.
5. **HTTPS, authentication, rate limits, redirects** would have to be done inside every app: nothing sits in front.

### Step 4: The problem

Not that it's broken. It works, but it's **port sprawl**. We want **one entrance** that routes by host name and path.
That is what an Ingress does.

## What you should now understand

1. Exposing apps one by one with NodePort (or one LoadBalancer each) gives one entrance **per app**.
2. Ports are limited and shared; names and paths are not available at the Service level.
3. We need something that understands **HTTP host names and paths** and sits in front of all the apps.

### Check yourself
- What happens to the number of ports you manage if you add 20 more apps?
- With a `LoadBalancer` Service per app instead of `NodePort`, what would each app cost you on a cloud?

## Next

[`../solution1-ingress`](../solution1-ingress). Self-contained: it builds its own apps.
Clean up this lab when done: `./cleanup.sh` (or `kubectl delete namespace ingress-p1`).
