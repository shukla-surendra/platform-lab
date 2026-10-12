# 2. Enabling and using Ingress on minikube

Everything here was done on minikube (Docker driver, macOS, 2 nodes, Kubernetes v1.34.0). Where something was not
tested, it says so.

## What you need

| Need | Why |
|---|---|
| A running minikube cluster | `minikube status` |
| The **ingress addon** | Installs an ingress controller. Without it an Ingress does nothing |
| Docker running | The lesson scripts use a throwaway container as an "outside" client |
| Internet access, once | The addon pulls its images from `registry.k8s.io` |

## Enable it

```bash
minikube addons enable ingress
kubectl -n ingress-nginx get pods          # wait for the controller to be Running and 1/1 ready
kubectl get ingressclass                   # shows: nginx   k8s.io/ingress-nginx
```

To remove it later: `minikube addons disable ingress`.

## What the addon installed (observed)

```
namespace ingress-nginx
  deployment/ingress-nginx-controller        1 replica, image registry.k8s.io/ingress-nginx/controller:v1.13.2
      ports: http 80 (hostPort 80), https 443 (hostPort 443), webhook 8443
      args:  --controller-class=k8s.io/ingress-nginx  --watch-ingress-without-class=true  --election-id=ingress-nginx-leader
  service/ingress-nginx-controller           NodePort  80:31658/TCP, 443:31256/TCP   (node ports are random)
  service/ingress-nginx-controller-admission ClusterIP 443/TCP    (the validating webhook)
  2 completed Jobs (admission-create, admission-patch) that set up the webhook certificate
ingressclass/nginx                           controller k8s.io/ingress-nginx, marked as the DEFAULT class
```

Things to notice:
- The controller listens on **`hostPort` 80 and 443 of the node it runs on**. That is how minikube makes it reachable
  without a cloud load balancer. It is a single replica on one node, so this is a development setup, not a
  high-availability one.
- `--watch-ingress-without-class=true` plus the default IngressClass means an Ingress with **no** class is picked up too.
- Before any Ingress rule exists, the controller answers `404 Not Found` on port 80 (checked).
- On a 2-node cluster, Pods on **either** node are reachable: the controller forwards to Pod IPs across nodes
  (observed: backend lists had Pod IPs from both `10.244.0.x` and `10.244.1.x`).

## The macOS problem (same as NodePort)

On Docker Desktop with the Docker driver, your Mac cannot reach the node's IP (`minikube ip` = `192.168.49.2`),
so you cannot just open `http://192.168.49.2`. Options:

### Option 1: `kubectl port-forward` to the controller (tested, no sudo)

```bash
kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8080:80      # keep this terminal open
```

In another terminal, send the **Host** header yourself, because Ingress routes by it:

```bash
curl -H "Host: shop.local" http://127.0.0.1:8080/
curl -H "Host: shop.local" http://127.0.0.1:8080/api
curl -H "Host: blog.local" http://127.0.0.1:8080/
curl -H "Host: unknown.local" -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/    # 404
```

Or let curl pretend DNS knows the name (the same effect as an `/etc/hosts` entry, but only for that command):

```bash
curl --resolve blog.local:8080:127.0.0.1 http://blog.local:8080/
```

All of these returned the right app when I ran them. For a **browser**, add the names to `/etc/hosts`:

```
127.0.0.1  shop.local blog.local docs.local
```
then open `http://shop.local:8080` (the `:8080` is the port-forward port; nginx matches the host name without the port).
I did not test the browser step itself.

### Option 2: `minikube tunnel` (what minikube itself recommends; not tested here)

After `minikube addons enable ingress`, minikube prints: *"please run `minikube tunnel` and your ingress resources
would be available at 127.0.0.1"*. As far as I know the tunnel needs to stay running in an open terminal and may ask
for your sudo password (it binds ports 80/443 on your Mac). Then:

```bash
curl -H "Host: shop.local" http://127.0.0.1/
```
I did not run the tunnel, because it asks for sudo interactively.

### Option 3: a client on the node's network (what the lesson scripts do)

```bash
docker run --rm --network minikube busybox:1.36 \
  wget -qO- --header "Host: shop.local" http://$(minikube ip)/
```

This reaches the controller's `hostPort 80` on the node. It is a stand-in for "a machine on the same network as the node".
If the controller runs on a node other than the one `minikube ip` returns, use that node's IP instead:
`kubectl -n ingress-nginx get pod -l app.kubernetes.io/component=controller -o wide`. The scripts look it up for you.

## Names like `shop.local`

An Ingress matches the **Host header**. Locally, nothing resolves `shop.local`, so you either send the header by hand
(`curl -H`), use `curl --resolve`, or add `/etc/hosts` entries. On a real cluster you create **DNS records** pointing at
the load balancer (Route 53, Cloudflare, ...). There is also an `ingress-dns` addon for minikube; I did not use it.

## Checking it

| Check | Command | Healthy result |
|---|---|---|
| Controller running | `kubectl -n ingress-nginx get pods` | `ingress-nginx-controller-...  1/1 Running` |
| Class exists | `kubectl get ingressclass` | `nginx` |
| Your Ingress | `kubectl -n <ns> get ingress` | `CLASS nginx`, your hosts, `ADDRESS` filled in after a few seconds |
| Rules understood | `kubectl -n <ns> describe ingress <name>` | Each host/path shows its backend with Pod IPs; no errors under Events |
| Config generated | `kubectl -n ingress-nginx exec deploy/ingress-nginx-controller -- nginx -T \| grep -A15 "server_name shop.local"` | A `server` block with your locations |
| Backends the controller knows | `kubectl -n ingress-nginx exec deploy/ingress-nginx-controller -- wget -qO- http://127.0.0.1:10246/configuration/backends` | JSON listing your Pod IPs |

## Run the labs

```bash
cd k8s/k8s_explorer/practice/ingress-lab/problem1-port-sprawl && ./run-problem.sh      # the problem
cd ../solution1-ingress && ./run-solution.sh                                           # the fix (needs the addon)
```
Each is independent and has its own `cleanup.sh`. Cleaning up a lab does **not** remove the ingress controller.
