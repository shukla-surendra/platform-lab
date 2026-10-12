# Service problems: what the five types don't cover

Each file is one **problem** and the Service feature that solves it. Use them after the five
type demos in `../`. Full explanation and the output observed on a real cluster:
[`docs/services-investigation.md`](../../../docs/services-investigation.md).

Prerequisite: `kubectl apply -f ../00-deployment.yaml` (the `web-backend` Pods several files point at).

| File | Try | Expect |
|---|---|---|
| `01-selector-mismatch.yaml` | `kubectl describe svc web-broken` | `Endpoints:` empty: the selector has a typo |
| `02-readiness-gating.yaml` | `kubectl describe svc gated`, then `kubectl exec <pod> -- touch /usr/share/nginx/html/ready` | No endpoints until a Pod becomes ready; then only that Pod appears. Never restarted |
| `03-multiport-named-ports.yaml` | From a test Pod: `wget -qO- http://multiport:9100` | `metrics: ok`, though the container listens on 8081 (found by port name) |
| `04-selectorless-endpointslice.yaml` | See the header comment (needs `sed` to fill `POD_IP`) | A Service with no selector forwards to the IP you wrote. Retry once if the first call is refused |
| `05-session-affinity.yaml` | 12 `wget`s to `web-sticky` vs `web-clusterip` | Sticky: all from one Pod. Plain: spread across three |
| `06-statefulset-headless.yaml` | `nslookup db-0.db.default.svc.cluster.local` | A stable name per Pod, still valid after the Pod is replaced with a new IP |
| `07-external-traffic-policy.yaml` | `kubectl get svc web-local -o yaml \| grep externalTrafficPolicy` | `Local`. Behavior differs only with 2+ working nodes |

Quick in-cluster test shell: `kubectl run t --image=busybox:1.36 --rm -it --restart=Never -- sh`

## Cleanup

```bash
kubectl delete -f . --ignore-not-found
kubectl delete svc legacy-backend --ignore-not-found
kubectl delete endpointslice legacy-backend-manual --ignore-not-found
```
