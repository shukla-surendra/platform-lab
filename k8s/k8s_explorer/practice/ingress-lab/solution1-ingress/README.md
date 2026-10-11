# Solution 1: one Ingress, one entrance, many apps

Fixes the problem shown in [`../problem1-port-sprawl`](../problem1-port-sprawl).

**This folder is independent.** It builds its own apps in its own namespace (`ingress-s1`), so you do not need to run
the problem first. It **does** need an ingress controller in the cluster (see below).

## Needs the ingress controller

```bash
minikube addons enable ingress
kubectl get ingressclass          # shows: nginx
```
More about what this installs and how to reach it from macOS: [`../docs/02-enable-on-minikube.md`](../docs/02-enable-on-minikube.md).
`run-solution.sh` checks for it and tells you how to enable it if it is missing.

> The controller (`ingress-nginx`) was announced as retired by the Kubernetes project. The Ingress rules you write
> here work the same with other controllers. See [`../docs/01-concepts.md`](../docs/01-concepts.md).

## Quick way: run it with a script

```bash
cd k8s/k8s_explorer/practice/ingress-lab/solution1-ingress
./run-solution.sh           # pauses at each step (press Enter)
./run-solution.sh --yes     # no pauses
./cleanup.sh                # removes the lab (not the controller)
```
Needs Docker running. The steps below explain the same thing by hand.

## Using it by hand (without the script)

### Apply everything at once

```bash
cd k8s/k8s_explorer/practice/ingress-lab/solution1-ingress
kubectl apply -f .
```

This applies every YAML file in the folder, in alphabetical order:

```
namespace/ingress-s1 created           \
deployment.apps/shop created            |  00-apps.yaml          the three apps + ClusterIP Services
service/shop-svc created                |
... (blog, api)                        /
ingress.networking.k8s.io/site created        01-ingress.yaml          Ingress "site": shop.local, blog.local
deployment.apps/docs created           \  02-new-app.yaml          the docs app
service/docs-svc created               /
ingress.networking.k8s.io/site configured     03-ingress-with-docs.yaml  the SAME Ingress "site", now with docs.local
```

`01-ingress.yaml` and `03-ingress-with-docs.yaml` both define the Ingress named `site`. Applied in order, the last one wins,
so you end with **three hosts**: `shop.local, blog.local, docs.local`. That is why the output says `created`, then `configured`.
To skip the "before" step, apply `00-apps.yaml`, `02-new-app.yaml` and `03-ingress-with-docs.yaml` only.

Check it (checked after exactly this `kubectl apply -f .`: all 8 Pods `1/1 Running`, and the Ingress had an `ADDRESS`):

```bash
kubectl -n ingress-s1 get pods,svc,ingress
```
```
NAME                             CLASS   HOSTS                              ADDRESS        PORTS
ingress.networking.k8s.io/site   nginx   shop.local,blog.local,docs.local   192.168.49.2   80
```
`ADDRESS` is the node the controller runs on. It can take a few seconds to appear after you apply.

### Call it from your Mac

Your Mac can't reach the node IP (Docker Desktop on macOS), and an Ingress routes by **host name**, so you need two things:
a way to reach the controller, and the host name. Use **two terminals**.

**Terminal 1: open the door and leave it running**

```bash
kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8080:80
```

It prints `Forwarding from 127.0.0.1:8080 -> 80`. If you close the terminal or press Ctrl+C, the calls below stop working.

**Terminal 2: call each app by choosing the host with a `Host:` header**

```bash
curl -H "Host: shop.local" http://127.0.0.1:8080/
curl -H "Host: blog.local" http://127.0.0.1:8080/
curl -H "Host: docs.local" http://127.0.0.1:8080/
curl -H "Host: shop.local" http://127.0.0.1:8080/api
curl -o /dev/null -w "%{http_code}\n" -H "Host: other.local" http://127.0.0.1:8080/
```

Output (tested, from a Mac, right after the `kubectl apply -f .` above):

```
shop.local       -> shop app, answered by pod shop-5f466fcf75-72wfb
blog.local       -> blog app, answered by pod blog-6d9c989579-4n76q
docs.local       -> docs app, answered by pod docs-5c85c8f99b-x4588
shop.local/api   -> api app, answered by pod api-cbbc54d9f-n6cz4
other.local      -> HTTP 404        (no rule matches this host)
```

The address is always `127.0.0.1:8080`. **Only the `Host:` header and the path choose the app.** That is the point of an Ingress.
Run a request a few times: the Pod name changes, because the Service spreads requests over the app's two Pods.

Instead of a header, `curl --resolve` makes curl treat the name as if DNS knew it:
```bash
curl --resolve blog.local:8080:127.0.0.1 http://blog.local:8080/
```

### Use a browser

1. Keep the port-forward from Terminal 1 running.
2. Add this line to `/etc/hosts` (needs sudo), so the names resolve to your own machine:
   ```
   127.0.0.1  shop.local blog.local docs.local
   ```
3. Open `http://shop.local:8080`, `http://blog.local:8080`, `http://docs.local:8080`, `http://shop.local:8080/api`.
   The `:8080` is the port-forward port. The browser sends `Host: shop.local:8080`, and the controller matches on the name without the port.
4. Remove the `/etc/hosts` line when you are finished.

I did not test the browser steps. The `curl` ones were tested. Other ways to reach the controller (`minikube tunnel`, a client on the
node's network) are in [`../docs/02-enable-on-minikube.md`](../docs/02-enable-on-minikube.md).

### Things to try

```bash
# watch the controller handle your requests (keep this running in a third terminal, then call the apps)
kubectl -n ingress-nginx logs deploy/ingress-nginx-controller --tail=10 -f

# kill a Pod while you keep calling shop.local: the entrance keeps answering
kubectl -n ingress-s1 delete pod -l app=shop

# read the rules the Ingress holds, and any events
kubectl -n ingress-s1 describe ingress site

# change a rule (for example rename docs.local in 03-ingress-with-docs.yaml), re-apply, and call the new name
kubectl apply -f 03-ingress-with-docs.yaml

# see what the controller wrote for a host
kubectl -n ingress-nginx exec deploy/ingress-nginx-controller -- nginx -T | grep -A12 "## start server docs.local"
```

### If a call does not work

| Symptom | Likely cause |
|---|---|
| `curl: (7) Failed to connect to 127.0.0.1 port 8080` | The port-forward terminal is closed or stopped. Start Terminal 1 again |
| `404 Not Found` for a host you expect to work | The `Host:` header doesn't match a rule (typo, or you left it out), or the Ingress isn't applied. Check `kubectl -n ingress-s1 get ingress` |
| `503 Service Temporarily Unavailable` | The backend has no ready Pods. `kubectl -n ingress-s1 get pods` and `get endpointslice` |
| Right after `apply`, a new host still gives 404 | The controller needs a few seconds to reload. Retry |
| Browser can't find `shop.local` | The `/etc/hosts` line is missing, or you forgot `:8080` |
| The port-forward died by itself | It stops if the controller Pod restarts. Start it again |

More in [`../docs/04-troubleshooting.md`](../docs/04-troubleshooting.md).

## The fix in one picture

```
 client ─ Host: shop.local ─────────┐
 client ─ Host: shop.local /api ────┼──> ingress controller (nginx, port 80) ──reads──> Ingress "site"
 client ─ Host: blog.local ─────────┘            │
                                   ┌─────────────┼────────────┐
                                   v             v            v
                               shop-svc      blog-svc      api-svc     (ClusterIP: not exposed on their own)
```

## Files

| File | What it is |
|---|---|
| `00-apps.yaml` | Namespace `ingress-s1`, three apps (shop, blog, api), each with a **ClusterIP** Service |
| `01-ingress.yaml` | **The fix:** one Ingress with the routing rules |
| `02-new-app.yaml` | A 4th app (`docs`), added later |
| `03-ingress-with-docs.yaml` | The same Ingress plus one rule for `docs.local` |
| `run-solution.sh` | Runs everything below for you |
| `cleanup.sh` | Deletes the `ingress-s1` namespace (not the controller, not `ingress-p1`) |

Every command uses `-n ingress-s1`.

## What the script does, step by step

### Step 1: Three apps with ClusterIP Services

```bash
kubectl apply -f 00-apps.yaml
kubectl -n ingress-s1 get svc
```
`TYPE ClusterIP`, no node ports. Nothing is reachable from outside yet.

### Step 2: Before the Ingress: the controller knows no rules

The controller is up and listening, but with no rules it answers `404 Not Found` to everything.

### Step 3: THE FIX: one Ingress

Read `01-ingress.yaml`. The important lines:

```yaml
spec:
  ingressClassName: nginx          # which controller implements this
  rules:
  - host: shop.local
    http:
      paths:
      - path: /api                 # shop.local/api  -> api-svc
        pathType: Prefix
        backend: {service: {name: api-svc, port: {number: 80}}}
      - path: /                    # shop.local/     -> shop-svc
        pathType: Prefix
        backend: {service: {name: shop-svc, port: {number: 80}}}
  - host: blog.local               # blog.local/     -> blog-svc
    http:
      paths:
      - path: /
        pathType: Prefix
        backend: {service: {name: blog-svc, port: {number: 80}}}
```
```bash
kubectl apply -f 01-ingress.yaml
kubectl -n ingress-s1 get ingress site
```
```
NAME   CLASS   HOSTS                   ADDRESS   PORTS   AGE
site   nginx   shop.local,blog.local             80      0s
```

### Step 4: Call the apps through the ONE entrance

Same address every time. Only the **Host header** and the **path** change (a browser sends the Host header for you):

```
shop.local/       ->  HTTP/1.1 200 OK  shop app, answered by pod shop-...
shop.local/api    ->  HTTP/1.1 200 OK  api app, answered by pod api-...
blog.local/       ->  HTTP/1.1 200 OK  blog app, answered by pod blog-...
unknown.local/    ->  HTTP/1.1 404 Not Found       <- no rule matches
```

By hand, from your Mac, using a port-forward to the controller (tested, no sudo):
```bash
kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8080:80      # keep it open
curl -H "Host: shop.local" http://127.0.0.1:8080/
curl -H "Host: shop.local" http://127.0.0.1:8080/api
curl -H "Host: blog.local" http://127.0.0.1:8080/
```

### Step 5: How it works: the controller turned the Ingress into nginx config

The controller is an nginx that **watches Ingress objects and rewrites its own config**. The script shows the part it
wrote for `shop.local`:

```
server_name shop.local ;
location /api/ { ... sends to backend: "ingress-s1-api-svc-80" }
location = /api { ... sends to backend: "ingress-s1-api-svc-80" }
location /      { ... sends to backend: "ingress-s1-shop-svc-80" }
```

And which Pods it sends to. **The controller uses the Pod IPs, not the Service's ClusterIP** (observed):

```
ingress-s1-api-svc-80  -> 10.244.1.16:80, 10.244.0.117:80      <- the api Pods' real IPs
ingress-s1-shop-svc-80 -> 10.244.1.17:80, 10.244.0.116:80      <- the shop Pods' real IPs
```

An **Ingress is not a proxy.** It's a set of rules. The controller does the proxying. The Service still matters: its
live Pod list is where the controller gets the backends from.

### Step 6: Kill a Pod: the entrance keeps working

15 requests to `shop.local` while a shop Pod was deleted: 15 replies, no failures. Same Service behavior as in the earlier lessons.

### Step 7: Add a 4th app by changing only the Ingress

```bash
kubectl apply -f 02-new-app.yaml                  # the docs Deployment + a ClusterIP Service
kubectl apply -f 03-ingress-with-docs.yaml        # the same Ingress "site" + one rule: docs.local -> docs-svc
```
`docs.local` now answers through the **same entrance**. No new port, no new load balancer, and the other apps are untouched.

### Step 8: What an Ingress does not do

- It needs an **ingress controller**. An Ingress object alone does nothing.
- It is for **HTTP/HTTPS**. Plain TCP/UDP needs a LoadBalancer (or a controller-specific feature).
- The controller itself needs an **entrance**. On a cloud, that is one LoadBalancer in front of it (or, with the AWS
  Load Balancer Controller, an ALB it creates). See [`../docs/03-aws-eks.md`](../docs/03-aws-eks.md).
- Names like `shop.local` must resolve to the entrance. Locally: Host header, `curl --resolve`, or `/etc/hosts`.

## What you should now understand

1. An **Ingress** is routing rules (host and path → Service). A **controller** makes them real.
2. One entrance serves **many apps**. Adding an app means adding a rule, not a port.
3. Backends are ordinary **ClusterIP** Services. They do not need to be exposed themselves.
4. The controller proxies **straight to the Pods**, using the Service's live Pod list.
5. Unmatched hosts/paths get a default **404**.

### Check yourself
- Change `pathType: Prefix` on `/api` to `Exact` and call `shop.local/api/x`. What happens, and why?
- What would happen if `api-svc` lived in a different namespace than the Ingress?
- Why does a request to `blog.local` with no Ingress rule for it get a 404 from nginx, not a connection error?

## Cleanup

```bash
./cleanup.sh        # or: kubectl delete namespace ingress-s1
```

## Next

TLS (HTTPS) on the Ingress, path rewrites, and the AWS version: see [`../docs/`](../docs).
