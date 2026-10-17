# 02 · Allow traffic from one pod only

**The idea:** A policy can let in traffic only from pods with a certain label, and block every other pod.

This example is **self-contained**: it creates its own namespaces, and doesn't need any other example.

```
namespace np-02

  frontend (app=frontend) ──✓──▶ api:80
  stranger (app=stranger) ──✗──▶ api:80
```

## Files

| File | What it is |
|---|---|
| `app.yaml` | namespace np-02, an api server and two clients: frontend and stranger |
| `policy.yaml` | api accepts traffic only from pods labelled app=frontend |
| `demo.sh` | Runs the whole example and checks each result |
| `index.html` | The same content as this README, as a web page |

## Run it

```bash
cd 02_allow_from_one_pod
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
   np-02/frontend -> api:80                     ok        ok        ✓
   np-02/stranger -> api:80                     ok        ok        ✓

== Step 2: allow only frontend -> api
   $ kubectl apply -f policy.yaml
   connection                                   expected  result   
   np-02/frontend -> api:80                     ok        ok        ✓
   np-02/stranger -> api:80                     BLOCKED   BLOCKED   ✓
```

## How the policy works

- The top-level `podSelector` picks **who is protected**: pods labelled `app: api`.
- `from.podSelector` picks **who may come in**: pods labelled `app: frontend`, in the same namespace.
- As soon as a policy selects the api pod, everything *not* listed is blocked for it. That's why `stranger` is shut out without a separate deny-all policy.
- Pods are matched by **label**, not by name. Any new pod labelled `app: frontend` gets in too.

## Try this

Give the stranger the right label: `kubectl -n np-02 label pod stranger app=frontend --overwrite`. Within about 30 seconds it can reach the api.

## Run it by hand instead of demo.sh

```bash
kubectl apply -f app.yaml
kubectl -n np-02 wait --for=condition=Ready pod --all
# test a connection yourself, for example:
kubectl -n np-02 exec stranger -- nc -z -w 2 api 80 && echo ok || echo BLOCKED
kubectl apply -f policy.yaml
# wait ~30 seconds, then test again
```

[Back to all examples](../README.md)
