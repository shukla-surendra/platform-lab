# 03 · Allow one port only

**The idea:** A policy can open one port on a pod and keep its other ports closed.

This example is **self-contained**: it creates its own namespaces, and doesn't need any other example.

```
namespace np-03

  client ──✓──▶ server:80    (website)
  client ──✗──▶ server:8080  (admin page)
```

## Files

| File | What it is |
|---|---|
| `app.yaml` | namespace np-03, a server with two ports (80 and 8080) and a client |
| `policy.yaml` | the server accepts traffic on port 80 only |
| `demo.sh` | Runs the whole example and checks each result |
| `index.html` | The same content as this README, as a web page |

## Run it

```bash
cd 03_allow_one_port
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
   np-03/client -> server:80                    ok        ok        ✓
   np-03/client -> server:8080                  ok        ok        ✓

== Step 2: allow only port 80
   $ kubectl apply -f policy.yaml
   connection                                   expected  result   
   np-03/client -> server:80                    ok        ok        ✓
   np-03/client -> server:8080                  BLOCKED   BLOCKED   ✓
```

## How the policy works

- The rule has a `ports:` list but **no** `from:`, so the source can be anyone.
- Only TCP port 80 is listed, so port 8080 is blocked.
- `from` and `ports` combine: a rule with both means "these sources, on these ports".
- Ports are the **pod's** ports (`containerPort`), not the Service's. Here they happen to be the same.

## Try this

Add `- {protocol: TCP, port: 8080}` under `ports:`, apply it again, and the admin port opens.

## Run it by hand instead of demo.sh

```bash
kubectl apply -f app.yaml
kubectl -n np-03 wait --for=condition=Ready pod --all
# test a connection yourself, for example:
kubectl -n np-03 exec client -- nc -z -w 2 server 8080 && echo ok || echo BLOCKED
kubectl apply -f policy.yaml
# wait ~30 seconds, then test again
```

[Back to all examples](../README.md)
