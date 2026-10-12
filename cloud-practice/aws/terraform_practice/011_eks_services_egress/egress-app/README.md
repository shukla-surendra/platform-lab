# egress-app: test one Deployment's outbound (egress) traffic

A Deployment of 2 Pods that call out every 10 seconds and log what happened. You then add NetworkPolicies one at a time and watch the
log change. Runs in its **own namespace** (`egress-app`), independent of the `lab` namespace in `../labs/`.

**Needs:** the EKS lab applied (`../README.md`) and kubectl pointed at it (`../connect.sh`). **Cost:** nothing extra (no load balancer).
Network policy enforcement comes from the VPC CNI add-on setting in `../04_nodes.tf`.

## Files

| File | What it does |
|---|---|
| `00-namespace.yaml` | Namespace `egress-app` |
| `01-deployment.yaml` | 2 Pods that log `dns=`, `https=` and `egressIP=` every 10 s |
| `02-netpol-default-deny-egress.yaml` | Step 1: block all outbound traffic (DNS too) |
| `03-netpol-allow-dns.yaml` | Step 2: allow DNS to CoreDNS |
| `04-netpol-allow-https.yaml` | Step 3: allow TCP 443 to any IPv4 address |
| `run.sh` | Does all steps for you, with pauses (`--yes` to skip). Refuses to run if kubectl isn't on the EKS lab context |
| `cleanup.sh` | Deletes the namespace |

## Run it

```bash
../connect.sh        # once: point kubectl at the cluster
./run.sh             # or apply the files by hand in the order above
./cleanup.sh
```

By hand: `kubectl apply -f 00-namespace.yaml -f 01-deployment.yaml`, then
`kubectl -n egress-app logs -l app=egress-app --tail=3 --prefix` (add `--max-log-requests=5` if needed). Follow live with `-f`.

## What to expect

| Step | Log line | Why |
|---|---|---|
| 1. Deployed, no policy | `dns=OK https=OK egressIP=<a node's public IP>` | Everything is allowed by default. The two Pods may show different IPs: the IP is the **node's** (public subnets, no NAT) |
| 2. default-deny | `dns=FAILED https=FAILED egressIP=-` | An empty egress list allows nothing, including DNS |
| 3. + allow DNS | `dns=OK https=FAILED` | Names resolve, but port 443 is still blocked |
| 4. + allow HTTPS | `dns=OK https=OK` | Policies are additive: the allowed set is DNS plus 443 |

Policies take a few seconds to apply, so the first log line after a step can still show the old result.

Compare `egressIP` with `kubectl get nodes -o wide` (EXTERNAL-IP column) to see that the internet sees the node, not the Pod.

## Status

Manifests pass `kubectl apply --dry-run=client`, and `run.sh` passes `bash -n`. **Not yet run against the cluster**: the "what to
expect" table is the expected behaviour, not an observed result. Update it after your run.
