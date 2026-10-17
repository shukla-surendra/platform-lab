# 06 · Deny outgoing traffic, then allow DNS

**The idea:** Blocking outgoing traffic also blocks DNS lookups, so egress lockdowns almost always need a DNS rule.

This example is **self-contained**: it creates its own namespaces, and doesn't need any other example.

```
namespace np-06                     no policy   deny egress   + allow DNS
  client -> DNS lookup of "web"       ✓            ✗             ✓
  client -> web:80                    ✓            ✗             ✗
```

## Files

| File | What it is |
|---|---|
| `app.yaml` | namespace np-06, a web server and a client |
| `policy-deny-egress.yaml` | the client may not open any outgoing connection |
| `policy-allow-dns.yaml` | add-on: the client may query cluster DNS |
| `demo.sh` | Runs the whole example and checks each result |
| `index.html` | The same content as this README, as a web page |

## Run it

```bash
cd 06_deny_egress_and_dns
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
   np-06/client -> DNS lookup of web            ok        ok        ✓
   np-06/client -> web's IP:80                  ok        ok        ✓

== Step 2: deny all outgoing traffic from client
   $ kubectl apply -f policy-deny-egress.yaml
   connection                                   expected  result   
   np-06/client -> DNS lookup of web            BLOCKED   BLOCKED   ✓
   np-06/client -> web's IP:80                  BLOCKED   BLOCKED   ✓

== Step 3: also allow DNS
   $ kubectl apply -f policy-allow-dns.yaml
   connection                                   expected  result   
   np-06/client -> DNS lookup of web            ok        ok        ✓
   np-06/client -> web's IP:80                  BLOCKED   BLOCKED   ✓
```

## How the policy works

- `policyTypes: [Egress]` controls **outgoing** traffic: connections the selected pod opens.
- A DNS lookup is an outgoing connection to CoreDNS in `kube-system` on port 53. Blocking egress breaks it, and apps then fail with "could not resolve host", which doesn't look like a firewall problem.
- Policies **add up**: the DNS policy allows port 53 on top of the deny, while everything else stays blocked.
- The TCP test connects to web's **IP address**, so it shows the connection is still blocked even after DNS works.

## Try this

Allow the client to reach web too: add a third policy with `egress: [{to: [{podSelector: {matchLabels: {app: web}}}], ports: [{port: 80}]}]`.

## Run it by hand instead of demo.sh

```bash
kubectl apply -f app.yaml
kubectl -n np-06 wait --for=condition=Ready pod --all
# test a connection yourself, for example:
kubectl -n np-06 exec client -- nc -z -w 2 web 80 && echo ok || echo BLOCKED
kubectl apply -f policy-deny-egress.yaml
kubectl apply -f policy-allow-dns.yaml
# wait ~30 seconds, then test again
```

[Back to all examples](../README.md)
