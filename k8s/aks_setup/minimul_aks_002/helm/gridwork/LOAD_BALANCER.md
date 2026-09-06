# The AKS Load Balancer — what it is, why it's always there, what it costs

Follow-up to `ARCHITECTURE.md`, which showed the `kubernetes` Standard Load
Balancer sitting between the public IP and `gridwork-frontend`. This answers
the questions that came up looking at it: does AKS always have one, is it
billed, what is it actually for, and how does a Public IP end up attached to
it.

## Does AKS always create a Load Balancer?

Yes — and this cluster is proof of it. The `kubernetes` Load Balancer in
`MC_rg-aks-dev_aks-dev_centralindia` already existed (it's one of the
resources `minimul_aks_managed_rg.md` documented) **before** this project
ever created a `type: LoadBalancer` Service. AKS creates it at cluster
*creation* time, not the first time you ask for one.

Why: by default, every AKS cluster's `outboundType` is `loadBalancer` — the
mechanism nodes use to reach the internet at all (pulling images from a
registry, calling external APIs, NTP, DNS to the outside world) is **SNAT
through this same Load Balancer**, not a direct route. Confirmed directly
against this cluster in the previous investigation: the first frontend IP
config (`0aa1caf7-...`) has an `outboundRules` entry and *no*
`loadBalancingRules` at all — that's the auto-created egress path, unrelated
to anything this project deployed. Only the second config
(`acba11bf...`, carrying `pip-aks-dev-ingress`) has a `loadBalancingRules`
entry, and that one *did* only appear after `gridwork-frontend` became
`type: LoadBalancer`.

So: **one Load Balancer always exists, for egress.** Inbound rules get added
to that same LB, one per `LoadBalancer` Service you create — it doesn't
spawn a second Load Balancer per Service.

## Is it charged?

Yes, and this is a real difference from the Basic SKU. Two separate things
are billed, and it's worth knowing both exist even though this doc won't
quote exact rates (they vary by region and change over time — check the
Azure pricing page or your subscription's cost view for current numbers):

- **The Load Balancer itself** — Standard SKU bills based on the number of
  configured rules (load-balancing rules + outbound rules) and the data
  processed through it. Basic SKU (the old default, still used only if you
  explicitly ask for it) has no such charge, but Basic SKU also can't be used
  with AKS's default outbound type on current versions, doesn't support
  availability zones, and Microsoft has been retiring it — Standard being
  the billed option is effectively no longer optional for a modern cluster.
- **The Public IP itself, separately** — `pip-aks-dev-ingress` (Standard SKU,
  Static allocation) is its own billable resource, charged per hour simply
  for existing and being reserved, regardless of whether any traffic is
  flowing through it. This is *why* `PUBLIC_EXPOSURE_PLAN.md`'s closing
  section flagged reserving a static IP as something to do deliberately, not
  by default — an ephemeral IP that Azure auto-assigns and later releases
  doesn't sit around racking up charges the way a permanently reserved one
  does the whole time your cluster exists, even powered down between demos.

Net effect for this project specifically: from the moment the cluster was
created, you were already paying for one Load Balancer (egress-only). Adding
`gridwork-frontend` as `type: LoadBalancer` didn't add a *second* LB charge —
it added one more rule to the existing one, plus the separate, new cost of
the static Public IP you reserved on top of it.

## What is this Load Balancer's actual job? (the two-layer picture)

It does exactly one thing: **Layer 4 (TCP/UDP) balancing across VM
instances** — the AKS nodes (VMSS), not pods. This is the same distinction
that came up when you asked "when I have 2 nodes, why one cluster IP" earlier
in this project — the Load Balancer and `kube-proxy` are two different
layers solving two different problems:

1. **Azure Load Balancer** (this doc) — picks *which node* a packet arriving
   at the Public IP gets sent to. It only knows about VMSS instances and
   health probes; it has no concept of "pod" at all.
2. **kube-proxy**, running on whichever node the packet lands on — takes it
   from there and DNATs it to an actual pod IP, based on the Service's
   endpoint list, which may well be a pod running on a *different* node than
   the one the Azure LB happened to pick.

So a request's real path is: `Public IP → Azure LB → some node's kube-proxy
iptables rules → the actual pod`, and the pod could be on a totally
different physical VM than whichever one Azure's LB routed the connection
to first. The Azure LB is doing "spread traffic across machines"; Kubernetes
is doing "get it to the right container" — two separate jobs, layered.

The **egress side** is the same mechanism run in reverse for the frontend IP
config that has no rules of its own: every node's outbound internet traffic
gets source-NAT'd through the Load Balancer's outbound rule so it appears to
come from one of the cluster's public IPs, rather than nodes needing their
own individual public IPs.

## How does a Public IP actually get attached to it?

Two different paths, and this cluster has one example of each, right now:

**Path 1 — Azure creates one for you (the default, no annotation).** When a
Service is `type: LoadBalancer` with no IP-pinning annotation, AKS's cloud
provider (running as part of the control plane) auto-provisions a brand-new
Public IP, adds a new `frontendIPConfiguration` to the existing `kubernetes`
LB referencing that new IP, adds a `loadBalancingRule` tying
`{that frontend config, port}` to the backend pool (the node VMSS) plus a
health probe, and reports the resulting IP back onto the Service's
`status.loadBalancer.ingress` field, which is what `kubectl get svc` reads.
This is exactly how the *original* egress IP got created too — nobody
requested it explicitly, AKS provisioned it as part of cluster setup because
`outboundType: loadBalancer` needed one.

**Path 2 — you tell it to reuse a specific, already-existing IP (what
`gridwork-frontend` does).** The
`service.beta.kubernetes.io/azure-load-balancer-ipv4: "20.219.56.230"`
annotation on the Service (`templates/frontend.yaml`) tells the same cloud
provider controller: don't create a new IP, attach *this* one instead. It
still goes through the identical mechanical steps — new frontend IP config,
new rule, new health probe — the only difference is which Public IP resource
gets referenced in that frontend config. This only works because:

- The IP (`azurerm_public_ip.ingress` in `infra/main.tf`) was deliberately
  created inside `MC_rg-aks-dev_aks-dev_centralindia` — the same resource
  group Path 1 would have used automatically. Point the annotation at an IP
  living in a *different* resource group and it additionally needs
  `service.beta.kubernetes.io/azure-load-balancer-resource-group` set, or the
  controller won't find it.
- The IP's SKU (Standard) matches the Load Balancer's SKU (Standard) —
  Azure won't attach a Basic IP to a Standard LB or vice versa.
- The IP's allocation is `Static`, not `Dynamic` — a `Dynamic` IP can change
  address on its own, which would defeat the entire point of pinning one.

Verified directly against this cluster's actual Azure state (not just
inferred from the chart): `pip-aks-dev-ingress` shows up as the
`publicIPAddress.id` on frontend config `acba11bf52ca442f887e1a7960fb87ea`,
which carries the `loadBalancingRules` entry `acba11bf...-TCP-80` — the exact
rule forwarding port 80 to the frontend pods.
