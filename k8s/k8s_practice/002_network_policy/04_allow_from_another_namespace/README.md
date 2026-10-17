# 04 · Allow traffic from another namespace

**The idea:** A policy can let in traffic from a whole namespace, selected by its labels.

This example is **self-contained**: it creates its own namespaces, and doesn't need any other example.

```
np-04-trusted/client   ──✓──▶ np-04-app/web:80
np-04-untrusted/client ──✗──▶ np-04-app/web:80
```

## Files

| File | What it is |
|---|---|
| `app.yaml` | three namespaces: np-04-app (web server), np-04-trusted and np-04-untrusted (a client each) |
| `policy.yaml` | web accepts traffic only from namespace np-04-trusted |
| `demo.sh` | Runs the whole example and checks each result |
| `index.html` | The same content as this README, as a web page |

## Run it

```bash
cd 04_allow_from_another_namespace
./demo.sh           # create the app, test, apply the policy, test again
./demo.sh cleanup   # delete everything this example created
```

`demo.sh` tests each connection, then applies the policy and tests again. Network rules can take a few
seconds to apply, so it retries for up to 90 seconds until the results match what's expected.

## What you'll see

Real output from this cluster:

```
== Step 1: no policy
   connection                                   expected  result   
   np-04-trusted/client -> web:80               ok        ok        ✓
   np-04-untrusted/client -> web:80             ok        ok        ✓

== Step 2: allow only namespace np-04-trusted
   $ kubectl apply -f policy.yaml
   connection                                   expected  result   
   np-04-trusted/client -> web:80               ok        ok        ✓
   np-04-untrusted/client -> web:80             BLOCKED   BLOCKED   ✓
```

## How the policy works

- `namespaceSelector` selects **namespaces** by label, and allows every pod in them.
- Kubernetes automatically labels every namespace with `kubernetes.io/metadata.name: `, so you can select one by name without adding labels.
- Both clients are identical pods with the same labels. Only their namespace differs.
- A common real use: allow traffic from your ingress controller's namespace (for example `ingress-nginx`).

## Try this

See the automatic labels with `kubectl get ns --show-labels | grep np-04`.

## Run it by hand instead of demo.sh

```bash
kubectl apply -f app.yaml
kubectl -n np-04-app wait --for=condition=Ready pod --all
kubectl -n np-04-trusted wait --for=condition=Ready pod --all
kubectl -n np-04-untrusted wait --for=condition=Ready pod --all
# test a connection yourself, for example:
kubectl -n np-04-untrusted exec client -- nc -z -w 2 web.np-04-app 80 && echo ok || echo BLOCKED
kubectl apply -f policy.yaml
# wait ~30 seconds, then test again
```

[Back to all examples](../README.md)
