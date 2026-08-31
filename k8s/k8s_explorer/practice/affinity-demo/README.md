# affinity-demo

Hands-on companion to [`docs/pod-and-node-affinity.md`](../docs/pod-and-node-affinity.md).
Plain manifests (no Helm) — apply them one at a time, watch what the scheduler actually does,
`kubectl describe` the result, then move to the next one. Everything here uses `nginx:alpine` as
a throwaway workload; the point is scheduling behavior, not the app.

Assumes a running `minikube` cluster (`minikube status`). Parts 1, 2 and 4 work fine on the
default single-node cluster. Part 3 is more interesting with more than one node — instructions
for adding nodes are inline.

## Part 1 — Node affinity: `required`

Label the node so it matches the Pod's rule, then apply:

```bash
kubectl label node minikube disk=ssd
kubectl apply -f 01-node-affinity-required.yaml
kubectl get pod ssd-required -o wide
```

`ssd-required` should be `Running` on `minikube`. Now prove the rule is actually load-bearing —
delete the Pod and remove the label it depends on:

```bash
kubectl delete -f 01-node-affinity-required.yaml
kubectl label node minikube disk-
kubectl apply -f 01-node-affinity-required.yaml
kubectl get pod ssd-required
```

This time it sticks in `Pending`. Confirm why:

```bash
kubectl describe pod ssd-required | grep -A3 Events
# 0/1 nodes are available: 1 node(s) didn't match Pod's node affinity/selector.
```

Put the label back so later steps aren't affected by this experiment:

```bash
kubectl label node minikube disk=ssd
```

## Part 2 — Node affinity: `preferred`

`zone-preferred` asks (softly) for a node labeled `zone=us-east`. No node in this cluster has
that label — a `required` rule would leave it `Pending`, but `preferred` just falls back:

```bash
kubectl apply -f 02-node-affinity-preferred.yaml
kubectl get pod zone-preferred -o wide
# Running anyway — no error, no Pending, the soft rule was simply skipped.
```

## Part 3 — Pod affinity and anti-affinity

### 3a. Pod affinity — co-locate frontend with backend

```bash
kubectl apply -f 03-pod-affinity-backend.yaml
kubectl apply -f 04-pod-affinity-frontend.yaml
kubectl get pods -l 'demo in (pod-affinity)' -o wide
```

`frontend` lands on whichever node the `backend` Pod is already on — on a single-node cluster
this isn't a visible difference, but it's the same rule that matters once there's more than one
node.

### 3b. Pod anti-affinity — spread `web` across nodes

```bash
kubectl apply -f 05-pod-anti-affinity-web.yaml
kubectl get pods -l app=web -o wide
```

**On the default single-node cluster**, expect 1 Pod `Running` and 2 stuck `Pending` — this is
the sharp edge called out in the doc: `requiredDuringScheduling` anti-affinity can't place two
Pods that both refuse to share a node. Confirm it:

```bash
kubectl describe pod -l app=web | grep -A3 Events
# 0/1 nodes are available: 1 node(s) didn't match pod anti-affinity rules.
```

To see the rule actually do its job, give the cluster more nodes:

```bash
minikube node add
minikube node add
kubectl get nodes
```

Then force a fresh scheduling decision for all 3 replicas:

```bash
kubectl delete -f 05-pod-anti-affinity-web.yaml
kubectl apply -f 05-pod-anti-affinity-web.yaml
kubectl get pods -l app=web -o wide
```

All 3 should now be `Running`, one per node — losing any single node now costs exactly one
replica instead of the whole app.

## Part 4 — `IgnoredDuringExecution`, proven live

Affinity rules are only checked at schedule time. Prove a running Pod is never re-evaluated
against a rule it currently satisfies:

```bash
kubectl get pod ssd-required -o wide          # confirm it's Running, note its node
kubectl label node minikube disk-              # remove the label the Pod's rule depends on
kubectl get pod ssd-required                   # still Running — nothing evicted it
```

Kubernetes checked the rule exactly once, when it scheduled the Pod. It does not watch for label
drift afterward. Put the label back when done:

```bash
kubectl label node minikube disk=ssd
```

## Cleanup

```bash
kubectl delete -f 01-node-affinity-required.yaml
kubectl delete -f 02-node-affinity-preferred.yaml
kubectl delete -f 03-pod-affinity-backend.yaml
kubectl delete -f 04-pod-affinity-frontend.yaml
kubectl delete -f 05-pod-anti-affinity-web.yaml
kubectl label node minikube disk- zone- 2>/dev/null

# only if you added extra nodes in Part 3b:
minikube node delete minikube-m03
minikube node delete minikube-m02
```

## Reference

| File | Demonstrates |
|---|---|
| `01-node-affinity-required.yaml` | `nodeAffinity` — hard requirement, `Pending` if unmatched |
| `02-node-affinity-preferred.yaml` | `nodeAffinity` — soft preference, falls back silently |
| `03-pod-affinity-backend.yaml` / `04-pod-affinity-frontend.yaml` | `podAffinity` — co-locate on the same node |
| `05-pod-anti-affinity-web.yaml` | `podAntiAffinity` — spread replicas across nodes |
