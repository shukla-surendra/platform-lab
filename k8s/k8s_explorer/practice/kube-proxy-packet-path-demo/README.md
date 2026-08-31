# kube-proxy-packet-path-demo

Companion to [`docs/service-types.md`](../../docs/service-types.md), which covers what a `ClusterIP`
*is* and how to use one. This project answers the question that doc doesn't: when something
`curl`s a `ClusterIP`, what actually moves the packet to a real Pod — is there a proxy process
in the middle, a load balancer, what? Traced end to end against this repo's real minikube
cluster, all the way down to the literal `iptables` rules on the node.

Assumes a running, multi-node `minikube` cluster (`minikube status` — this repo's default
profile has 3 nodes).

## What problem does it solve?

"kube-proxy" sounds like a process traffic actually flows *through* — a reverse proxy, like
nginx or Envoy. **It isn't, in the default (iptables) mode.** kube-proxy is better understood as
a **control-plane component that only programs `iptables` rules** — it watches Services/
EndpointSlices and writes NAT rules to match, then gets entirely out of the way. The actual
packet forwarding happens inside the Linux kernel's netfilter/conntrack machinery, at line rate,
with zero userspace proxy process ever touching the packet. That's the single most
counter-intuitive fact about Kubernetes networking this demo exists to make concrete.

## Setup

```bash
kubectl apply -f app.yaml   # a 1-replica nginx Deployment + its ClusterIP Service
kubectl get svc packet-path-demo
```

## Verified — the full path, one hop at a time

**1. DNS resolves the Service name to its ClusterIP** — via CoreDNS, not kube-proxy at all
(a separate mechanism, easy to conflate):

```bash
kubectl run dns-check --rm -i --restart=Never --image=busybox:1.36 -- \
  nslookup packet-path-demo.default.svc.cluster.local
```

```
Server:		10.96.0.10
Address:	10.96.0.10:53

Name:	packet-path-demo.default.svc.cluster.local
Address: 10.111.146.105
```

**2. The ClusterIP itself isn't a real address anything listens on** — it's purely a NAT target.
Real proof, on the node:

```bash
minikube ssh -- "sudo iptables -t nat -L KUBE-SERVICES -n | grep 10.111.146.105"
```

```
KUBE-SVC-M4QR4FTZVPGIT4PY  tcp  --  0.0.0.0/0  10.111.146.105  /* default/packet-path-demo cluster IP */
```

Every packet to `10.111.146.105:80`, from any pod on this node, gets redirected into a
per-Service chain (`KUBE-SVC-M4QR4FTZVPGIT4PY`) before it ever reaches a socket.

**3. The `KUBE-SVC` chain is where load-balancing across replicas actually happens** — with one
endpoint:

```bash
minikube ssh -- "sudo iptables -t nat -L KUBE-SVC-M4QR4FTZVPGIT4PY -n"
```

```
KUBE-MARK-MASQ  tcp  -- !10.244.0.0/16  10.111.146.105  /* default/packet-path-demo cluster IP */
KUBE-SEP-F27BMHVRQPV4COSB  all  --  0.0.0.0/0  0.0.0.0/0  /* default/packet-path-demo -> 10.244.2.93:80 */
```

**4. The `KUBE-SEP` chain is the literal DNAT to a real Pod IP** — "SEP" is kube-proxy's own
term for a Service EndPoint:

```bash
minikube ssh -- "sudo iptables -t nat -L KUBE-SEP-F27BMHVRQPV4COSB -n"
```

```
KUBE-MARK-MASQ  all  --  10.244.2.93  0.0.0.0/0  /* default/packet-path-demo */
DNAT       tcp  --  0.0.0.0/0     0.0.0.0/0  /* default/packet-path-demo */ tcp to:10.244.2.93:80
```

That `DNAT ... to:10.244.2.93:80` is the entire mechanism. `10.244.2.93` is the real Pod IP
(`kubectl get pod -o wide` confirms it) — the ClusterIP was never anything but a rewrite target.

## Verified — kube-proxy's actual load-balancing algorithm

```bash
kubectl scale deployment packet-path-demo --replicas=2
# wait for the second Pod to go Ready
minikube ssh -- "sudo iptables -t nat -L KUBE-SVC-M4QR4FTZVPGIT4PY -n"
```

Real output, with 2 ready endpoints:

```
KUBE-MARK-MASQ  tcp  -- !10.244.0.0/16  10.111.146.105  /* cluster IP */
KUBE-SEP-MZAXH7IP2SUFW23U  ...  /* -> 10.244.1.8:80 */ statistic mode random probability 0.50000000000
KUBE-SEP-F27BMHVRQPV4COSB  ...  /* -> 10.244.2.93:80 */
```

This **is** kube-proxy's load balancer, in full: a cascading list of rules, each one a coin flip
(`statistic mode random probability 1/N_remaining`) on whether *this* rule claims the packet,
falling through to the next if not. With 2 endpoints it's a straight 50/50; with 3 it'd be
`probability 0.333...` then `0.5` then the last one unconditional — each rule's probability is
relative to what's left, not the original N, so the math works out even. There is no consistent
hashing, no least-connections, no health-aware weighting in this default mode — it's uniform
random per new connection (a new random pick happens per NAT-table lookup, which in practice
means per new TCP connection, since conntrack pins an established connection to whichever
endpoint it already picked).

## What changes in IPVS mode (not this cluster, worth knowing)

This cluster's kube-proxy runs in the **iptables** mode shown above (confirmed:
`kubectl get cm kube-proxy -n kube-system -o jsonpath='{.data.config\.conf}'` shows an empty
`mode:` field, which defaults to iptables on Linux). The alternative, **IPVS mode**, replaces
this whole probabilistic iptables chain with a real in-kernel load balancer (`ipvsadm`-managed
virtual server), supporting actual algorithms (round-robin, least-connection, weighted) and
scaling better past a few thousand Services, where iptables' linear rule-chain lookup starts
costing real latency. Same conceptual job (DNAT to a real Pod IP), different and more capable
implementation underneath.

## Cleanup

```bash
kubectl delete -f app.yaml
```

## Reference

| File | Role |
|---|---|
| `app.yaml` | The nginx Deployment + ClusterIP Service used to trace the path above |
