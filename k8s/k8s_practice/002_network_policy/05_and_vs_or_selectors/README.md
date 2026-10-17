# 05 · AND vs OR selectors

**The idea:** One extra "-" in the YAML turns a narrow rule (AND) into a much wider one (OR).

This example is **self-contained**: it creates its own namespaces, and doesn't need any other example.

```
                                AND policy   OR policy
np-05-other/client  (role=client)   ✓           ✓
np-05-other/random  (no role)       ✗           ✓   any pod in np-05-other
np-05-app/local     (role=client)   ✗           ✓   role=client in np-05-app
```

## Files

| File | What it is |
|---|---|
| `app.yaml` | np-05-app (web server and a 'local' client) and np-05-other (a 'client' and a 'random' pod) |
| `policy-and.yaml` | AND version: namespace np-05-other AND label role=client |
| `policy-or.yaml` | OR version: same selectors, one extra "-" |
| `demo.sh` | Runs the whole example and checks each result |
| `index.html` | The same content as this README, as a web page |

## Run it

```bash
cd 05_and_vs_or_selectors
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
   np-05-other/client -> web:80                 ok        ok        ✓
   np-05-other/random -> web:80                 ok        ok        ✓
   np-05-app/local -> web:80                    ok        ok        ✓

== Step 2: AND policy (one list item)
   $ kubectl apply -f policy-and.yaml
   connection                                   expected  result   
   np-05-other/client -> web:80                 ok        ok        ✓
   np-05-other/random -> web:80                 BLOCKED   BLOCKED   ✓
   np-05-app/local -> web:80                    BLOCKED   BLOCKED   ✓

== Step 3: OR policy (two list items)
   $ kubectl apply -f policy-or.yaml
   connection                                   expected  result   
   np-05-other/client -> web:80                 ok        ok        ✓
   np-05-other/random -> web:80                 ok        ok        ✓
   np-05-app/local -> web:80                    ok        ok        ✓
```

## How the policy works

- **AND**: `namespaceSelector` and `podSelector` are in the **same** list item. A pod must match both.
- **OR**: each selector is its **own** list item (its own `-`). A pod matching either one gets in.
- In the OR form, a `podSelector` on its own means "pods with this label *in the policy's own namespace*". That's why `np-05-app/local` gets in.
- Both files use the same policy name, so applying the OR file **replaces** the AND one.

## Try this

Compare the two files with `diff policy-and.yaml policy-or.yaml`. The only real difference is one `-`.

## Run it by hand instead of demo.sh

```bash
kubectl apply -f app.yaml
kubectl -n np-05-app wait --for=condition=Ready pod --all
kubectl -n np-05-other wait --for=condition=Ready pod --all
# test a connection yourself, for example:
kubectl -n np-05-app exec local -- nc -z -w 2 web 80 && echo ok || echo BLOCKED
kubectl apply -f policy-and.yaml
kubectl apply -f policy-or.yaml
# wait ~30 seconds, then test again
```

[Back to all examples](../README.md)
