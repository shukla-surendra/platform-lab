# 07 · Lock down a three-tier app

**The idea:** Combining deny-all, DNS, and per-tier allow rules leaves only the app's intended paths open.

This example is **self-contained**: it creates its own namespaces, and doesn't need any other example.

```
np-07-outside/client ──▶ web:80 ──▶ api:80 ──▶ db:6379

every other path is blocked, in both directions
```

## Files

| File | What it is |
|---|---|
| `app.yaml` | np-07-app (web, api, db) and np-07-outside (client) |
| `policy.yaml` | five policies in one file: deny all, allow DNS, and one each for web, api and db |
| `demo.sh` | Runs the whole example and checks each result |
| `index.html` | The same content as this README, as a web page |

## Run it

```bash
cd 07_three_tier_app
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
   np-07-outside/client -> web:80               ok        ok        ✓
   np-07-outside/client -> api:80               ok        ok        ✓
   np-07-outside/client -> db:6379              ok        ok        ✓
   np-07-app/web -> api:80                      ok        ok        ✓
   np-07-app/web -> db:6379                     ok        ok        ✓
   np-07-app/api -> db:6379                     ok        ok        ✓
   np-07-app/db -> api:80                       ok        ok        ✓

== Step 2: apply the full lockdown
   $ kubectl apply -f policy.yaml
   connection                                   expected  result   
   np-07-outside/client -> web:80               ok        ok        ✓
   np-07-outside/client -> api:80               BLOCKED   BLOCKED   ✓
   np-07-outside/client -> db:6379              BLOCKED   BLOCKED   ✓
   np-07-app/web -> api:80                      ok        ok        ✓
   np-07-app/web -> db:6379                     BLOCKED   BLOCKED   ✓
   np-07-app/api -> db:6379                     ok        ok        ✓
   np-07-app/db -> api:80                       BLOCKED   BLOCKED   ✓
```

## How the policy works

- Policy 1 denies **both** ingress and egress for every pod in the app namespace.
- Policy 2 allows DNS for every pod (see example 06 for why).
- Policies 3–5 open exactly one path each. A connection needs **egress** allowed on the sender *and* **ingress** allowed on the receiver: for example, web → api needs web's egress rule (policy 3) and api's ingress rule (policy 4).
- `web → db` is blocked: web can only reach the database through api.

## Try this

List the policies with `kubectl get netpol -n np-07-app`, then read one in plain words with `kubectl describe netpol api -n np-07-app`.

## Run it by hand instead of demo.sh

```bash
kubectl apply -f app.yaml
kubectl -n np-07-app wait --for=condition=Ready pod --all
kubectl -n np-07-outside wait --for=condition=Ready pod --all
# test a connection yourself, for example:
kubectl -n np-07-app exec db -- nc -z -w 2 api 80 && echo ok || echo BLOCKED
kubectl apply -f policy.yaml
# wait ~30 seconds, then test again
```

[Back to all examples](../README.md)
