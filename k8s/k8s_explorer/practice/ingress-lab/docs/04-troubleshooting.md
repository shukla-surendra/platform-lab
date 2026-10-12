# 4. Troubleshooting Ingress (local and general)

Work from the outside in. The first three checks fix most problems.

| # | Question | Command | Healthy |
|---|---|---|---|
| 1 | Is a controller installed and running? | `kubectl get ingressclass` and `kubectl -n ingress-nginx get pods` | A class `nginx`; the controller Pod `1/1 Running` |
| 2 | Does the Ingress name that class? | `kubectl -n <ns> get ingress` | `CLASS nginx` (or no class, with a default class present) |
| 3 | Are there warnings on the Ingress? | `kubectl -n <ns> describe ingress <name>` | Backends listed with Pod IPs; no errors under Events |
| 4 | Does the backend Service have endpoints? | `kubectl -n <ns> get endpointslice -l kubernetes.io/service-name=<svc>` | Pod IPs listed (empty means a selector mismatch or no ready Pods) |
| 5 | Is the Service in the **same namespace** as the Ingress? | `kubectl -n <ns> get svc` | Yes |
| 6 | Does the Service port match the Ingress backend port? | `kubectl -n <ns> get svc <svc>` | The `number` in the Ingress equals the Service `port` |
| 7 | Do you send the right **Host** header? | `curl -H "Host: shop.local" ...` | The same host string as in the rule |
| 8 | Does the Pod itself answer? | `kubectl port-forward pod/<pod> 8081:80` then `curl localhost:8081` | A reply |

| Symptom | Likely cause |
|---|---|
| `404 Not Found` from the controller | No rule matched: wrong `Host` header, wrong path, or the Ingress is in a different class |
| `404` that comes from the **app** (not nginx's default page) | The rule matched and reached the app, but the app has no such path. Check `pathType` and whether you need a rewrite |
| `503 Service Temporarily Unavailable` | The Service has **no ready endpoints** (selector mismatch, Pods not ready) |
| `502 Bad Gateway` | The controller reached a Pod but it closed the connection or answered badly (wrong port, app crash, HTTP vs HTTPS mismatch) |
| `ADDRESS` stays empty | On cloud: the load balancer is not provisioned (controller missing, IAM, subnet tags). Locally on minikube it can stay empty or show the node IP |
| Ingress created but "nothing happens" | No controller, or `ingressClassName` points at a class that doesn't exist |
| Works with `curl -H Host:` but not in the browser | The name doesn't resolve on your machine. Add an `/etc/hosts` entry, and remember the port-forward port (`:8080`) |
| `admission webhook ... denied the request` (the webhook is named `validate.nginx.ingress.kubernetes.io` as far as I recall) | The controller's webhook rejected the Ingress (invalid or conflicting rule). Read the message: it names the problem. Also appears if the controller Pod is not ready yet |
| Rule added but old behavior persists | The controller reloads on change, which takes a moment. Retry after a few seconds (the lab scripts wait and retry) |

## Useful read-only commands

```bash
kubectl -n ingress-nginx logs deploy/ingress-nginx-controller --tail=30      # requests and errors
kubectl -n ingress-nginx exec deploy/ingress-nginx-controller -- nginx -T | grep -A25 "server_name shop.local"
kubectl -n <ns> get events --sort-by=.lastTimestamp | tail
```
