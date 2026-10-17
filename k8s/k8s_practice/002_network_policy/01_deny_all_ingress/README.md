# 01 · Deny all incoming traffic

**The idea:** One policy with an empty pod selector blocks every incoming connection to every pod in a namespace.

This example is **self-contained**: it creates its own namespaces, and doesn't need any other example.

```
namespace np-01

  client ──✗──▶ web:80

after policy.yaml: nothing can connect IN to any pod in np-01
```

## Files

| File | What it is |
|---|---|
| `app.yaml` | namespace np-01, a web server (nginx) and a client pod |
| `policy.yaml` | the deny-all policy |
| `demo.sh` | Runs the whole example and checks each result |
| `index.html` | The same content as this README, as a web page |

## Run it

```bash
cd 01_deny_all_ingress
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
   np-01/client -> web:80                       ok        ok        ✓

== Step 2: apply the deny-all policy
   $ kubectl apply -f policy.yaml
   connection                                   expected  result   
   np-01/client -> web:80                       BLOCKED   BLOCKED   ✓
```

## How the policy works

- `podSelector: {}` selects **every pod** in the namespace.
- `policyTypes: [Ingress]` says this policy controls **incoming** traffic.
- There's no `ingress:` list, so **nothing** is allowed in.
- This is the usual first policy in a namespace: block everything, then allow only what's needed.

## Try this

Delete the policy (`kubectl delete -f policy.yaml`), wait about 30 seconds, and the client can connect again. Deleting a policy immediately restores the default: allow everything.

## Run it by hand instead of demo.sh

```bash
kubectl apply -f app.yaml
kubectl -n np-01 wait --for=condition=Ready pod --all
# test a connection yourself, for example:
kubectl -n np-01 exec client -- nc -z -w 2 web 80 && echo ok || echo BLOCKED
kubectl apply -f policy.yaml
# wait ~30 seconds, then test again
```

[Back to all examples](../README.md)
