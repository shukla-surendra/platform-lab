# services-demo

Hands-on companion to [`docs/service-types.md`](../docs/service-types.md). One shared
Deployment, five Services in front of it — apply them one at a time and see exactly how
each `type` changes reachability. Every Pod serves its own hostname on `/`, so `curl`ing a
Service repeatedly shows the load-balancing (or lack of it) directly in the response body.

Assumes a running `minikube` cluster (`minikube status`).

## Setup

```bash
kubectl apply -f 00-deployment.yaml
kubectl get pods -l app=web-backend -o wide
```

Three `web-backend` Pods, each running `nginx:alpine` with its hostname baked into
`index.html`.

## Part 1 — `ClusterIP` (the default)

```bash
kubectl apply -f 01-clusterip.yaml
kubectl get svc web-clusterip
```

Only reachable from inside the cluster. Prove the load-balancing from a throwaway Pod:

```bash
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  sh -c "for i in 1 2 3 4 5 6; do curl -s http://web-clusterip; done"
```

Expect a mix of hostnames across the six requests — one ClusterIP, traffic spread across
all three Pods behind it.

## Part 2 — `NodePort`

```bash
kubectl apply -f 02-nodeport.yaml
kubectl get svc web-nodeport
# PORT(S)  80:3XXXX/TCP  <- the auto-assigned high port
```

Everything `ClusterIP` gives you, plus the same port opened on **every node's** IP:

```bash
minikube service web-nodeport --url
curl "$(minikube service web-nodeport --url)"
```

Run the `curl` a few times — same load-balancing as Part 1, just reachable from outside
the cluster now via a node IP instead of only from inside.

## Part 3 — `LoadBalancer`

```bash
kubectl apply -f 03-loadbalancer.yaml
kubectl get svc web-loadbalancer
# EXTERNAL-IP stays <pending> - no cloud provider to hand out a real one
```

minikube can simulate a cloud load balancer with a tunnel (needs a separate terminal,
keeps running):

```bash
minikube tunnel
```

With the tunnel active, `EXTERNAL-IP` fills in and the Service is reachable directly:

```bash
kubectl get svc web-loadbalancer
curl http://<EXTERNAL-IP>
```

On a real cloud cluster (EKS/GKE/AKS) this same manifest provisions an actual external
load balancer with a public IP/DNS name — no `minikube tunnel` involved, that step only
exists because a laptop isn't a cloud provider.

## Part 4 — Headless Service (`clusterIP: None`)

```bash
kubectl apply -f 04-headless.yaml
```

Compare DNS resolution for the headless Service against the ClusterIP one from Part 1,
from inside the cluster:

```bash
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- \
  sh -c "nslookup web-clusterip; echo ---; nslookup web-headless"
```

`web-clusterip` resolves to one virtual IP. `web-headless` resolves to **three** IPs — one
per Pod, no load-balancing IP in between. This is the mechanism StatefulSets rely on to
give each replica a stable, individually-addressable DNS name.

## Part 5 — `ExternalName`

```bash
kubectl apply -f 05-externalname.yaml
```

No selector, no endpoints, nothing proxied — just a DNS alias:

```bash
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- \
  nslookup web-external.default.svc.cluster.local
```

Resolves as a CNAME to `example.com` instead of a Pod IP. This is how you give an
in-cluster name to something that lives outside the cluster (a managed database, a
legacy host) so app code always talks to a `.svc.cluster.local` name, whether the real
thing is in-cluster or not.

## Cleanup

```bash
kubectl delete -f 05-externalname.yaml
kubectl delete -f 04-headless.yaml
kubectl delete -f 03-loadbalancer.yaml
kubectl delete -f 02-nodeport.yaml
kubectl delete -f 01-clusterip.yaml
kubectl delete -f 00-deployment.yaml

# if you started one in Part 3:
# Ctrl-C the `minikube tunnel` terminal
```

## Command & flag glossary

Explains every `kubectl` command/flag used above, in the order they first appear.

| Command / flag | Means |
|---|---|
| `kubectl apply -f <file>` | Create (or update) whatever's described in that YAML file. Safe to re-run — it converges the cluster to match the file instead of erroring if the thing already exists. |
| `kubectl get pods` | List Pods. `kubectl get svc`/`kubectl get deploy` etc. work the same way — `get <resource-type>` lists that type. `svc` is just the short name for `services` (`kubectl api-resources` lists every short name). |
| `-l app=web-backend` | **L**abel filter — only show things whose `labels` include `app: web-backend`. Every Pod from `00-deployment.yaml` carries that label (see `spec.template.metadata.labels`), so this narrows `get pods` down to just this demo's Pods instead of every Pod in the namespace. |
| `-o wide` | **O**utput format `wide` — the normal columns (`NAME`, `READY`, `STATUS`...) plus a few extra, notably `IP` and `NODE`. Plain `kubectl get pods` doesn't show a Pod's IP; `-o wide` does. |
| `kubectl run curl-test --image=curlimages/curl ...` | Start one throwaway Pod named `curl-test` from the given container image — a quick way to get a shell *inside* the cluster to test in-cluster-only things like `ClusterIP`, without deploying a whole app for it. |
| `--rm` | Delete this Pod automatically once it exits. Without it, `curl-test` would sit around afterward as a stopped Pod you'd have to clean up by hand. |
| `-it` | Attach your terminal to it interactively (`-i` keeps stdin open, `-t` allocates a terminal) so you see the command's output live, the same as running it locally. |
| `--restart=Never` | Run it as a plain one-shot Pod instead of wrapping it in a Deployment (`kubectl run`'s default). A one-shot Pod is allowed to exit `0` and be done; a Deployment would treat that exit as a crash and keep restarting it. |
| `-- sh -c "..."` | Everything after the bare `--` is the command to run *inside* that container, instead of being a flag to `kubectl` itself. `sh -c "..."` runs the quoted string as a shell command (needed here because it's a `for` loop, not a single binary + args). |
| `minikube service <name> --url` | minikube-specific helper: for a `NodePort`/`LoadBalancer` Service, print the URL that's actually reachable from your host machine (works out the right IP/port even when Docker networking on macOS means the node isn't directly reachable). |
| `minikube tunnel` | minikube-specific helper: opens a network route from your host to the cluster and starts assigning real IPs to `LoadBalancer` Services, simulating what a cloud provider would otherwise do. Keeps running in the foreground — it's what fills in `EXTERNAL-IP` in Part 3. |
| `nslookup <name>` | Ask DNS "what does this name resolve to?" Used here from inside the cluster to see *how many* IPs a Service name returns — one (ClusterIP), several (headless), or a CNAME (ExternalName) — which is the whole point of Parts 4 and 5. |
| `kubectl delete -f <file>` | The inverse of `apply` — remove exactly what that file describes. |

## Reference

| File | Service `type` | Reachable from | Load-balanced |
|---|---|---|---|
| `01-clusterip.yaml` | `ClusterIP` (default) | Inside cluster only | Yes |
| `02-nodeport.yaml` | `NodePort` | Inside cluster + any node IP | Yes |
| `03-loadbalancer.yaml` | `LoadBalancer` | Inside cluster + external LB IP (cloud, or `minikube tunnel`) | Yes |
| `04-headless.yaml` | `ClusterIP: None` | Inside cluster only, resolves to Pod IPs directly | No — client picks |
| `05-externalname.yaml` | `ExternalName` | DNS alias only, no Pods involved | N/A |
