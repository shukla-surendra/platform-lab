# Kubernetes NetworkPolicy examples

Seven **independent** examples. Each folder is complete on its own: it creates its own namespaces,
has its own app, policy, test script, README and web page, and needs nothing from the other folders.
Run any one, in any order.

| # | Example | The idea |
|---|---|---|
| 01 | [Deny all incoming traffic](01_deny_all_ingress/) | One policy with an empty pod selector blocks every incoming connection to every pod in a namespace. |
| 02 | [Allow traffic from one pod only](02_allow_from_one_pod/) | A policy can let in traffic only from pods with a certain label, and block every other pod. |
| 03 | [Allow one port only](03_allow_one_port/) | A policy can open one port on a pod and keep its other ports closed. |
| 04 | [Allow traffic from another namespace](04_allow_from_another_namespace/) | A policy can let in traffic from a whole namespace, selected by its labels. |
| 05 | [AND vs OR selectors](05_and_vs_or_selectors/) | One extra "-" in the YAML turns a narrow rule (AND) into a much wider one (OR). |
| 06 | [Deny outgoing traffic, then allow DNS](06_deny_egress_and_dns/) | Blocking outgoing traffic also blocks DNS lookups, so egress lockdowns almost always need a DNS rule. |
| 07 | [Lock down a three-tier app](07_three_tier_app/) | Combining deny-all, DNS, and per-tier allow rules leaves only the app's intended paths open. |

Every folder works the same way:

```bash
cd 01_deny_all_ingress
./demo.sh           # create the app, test, apply the policy, test again
./demo.sh cleanup   # delete what this example created
```

Each folder also has an `index.html`: open [`index.html`](index.html) here for a clickable overview.

## What a NetworkPolicy is

By default, **every pod can connect to every other pod**, in any namespace. A NetworkPolicy is a firewall
rule for pods: it picks pods by label and says which connections may come **in** (ingress) or go **out** (egress).

Rules worth remembering:

1. A pod that no policy selects allows everything.
2. Once a policy selects a pod for ingress (or egress), that direction is **deny by default** for the pod: only what some policy allows gets through.
3. Policies only **allow**. There are no deny rules, and several policies on one pod add up.
4. A connection needs egress allowed on the sender **and** ingress allowed on the receiver (when each has policies).
5. Replies to an allowed connection are allowed automatically.

## Before you start

Policies are enforced by the cluster's network plugin (CNI). If it doesn't support them, Kubernetes accepts
the YAML and nothing changes. This minikube cluster uses **kindnet**, which enforces them. Calico and Cilium do too.

```bash
kubectl -n kube-system get pods | grep -iE 'kindnet|calico|cilium'
```

## Troubleshooting

- **A result says `✗ unexpected` even after 90 seconds.** On this cluster, kindnet occasionally stopped
  applying policy changes on a node. Restarting it fixed this (a DaemonSet recreates it straight away):
  `kubectl -n kube-system delete pod -l app=kindnet`. Then run `./demo.sh` again.
- **Pods stay Pending.** Check `kubectl get nodes`, and that images can be pulled (`kubectl describe pod ...`).

## Clean up everything

```bash
for d in 0*/; do (cd "$d" && ./demo.sh cleanup); done
```
