# Amazon VPC — Complete documentation set

The full deep-dive on Amazon VPC, from first principles to production. Read in this order; each builds on the last.

## Study order

1. **[architecture.md](architecture.md)** — *Why VPC exists · the two-networks mental model · internal architecture* (Mapping Service, Nitro data plane, Blackfoot edge, distributed stateful SGs). **Start here** — the overlay/substrate model is the key that unlocks everything else.
2. **[networking.md](networking.md)** — *Building blocks · routing · packet flow* for every path (intra-VPC, IGW, NAT, endpoints, peering, TGW) · DNS. Pairs with the runnable **[Terraform 3-tier VPC](../../terraform/vpc/README.md)**.
3. **[internals.md](internals.md)** — *How AWS built it*: ENI deep-dive, Mapping Service, Hyperplane, Nitro, BGP/route propagation, and the distributed-systems algorithms (CAP, consistent hashing, quorum, ownership model).
4. **[security.md](security.md)** — *Security Groups vs NACLs internals · VPC Flow Logs · IAM/endpoint policies · encryption · threat models* (SSRF/IMDS, exfiltration, lateral movement).
5. **[best-practices.md](best-practices.md)** — *CIDR/subnet/multi-account design · real production architectures · cost optimization · monitoring* (CloudWatch, Config, CloudTrail, GuardDuty).
6. **[troubleshooting.md](troubleshooting.md)** — *The connectivity chain · Reachability Analyzer · Flow Log queries · the dozen common failures and their fixes.*
7. **[interview.md](interview.md)** — *Junior → principal Q&A, scenarios, incident drills.*
8. **[cross-cloud-comparison.md](cross-cloud-comparison.md)** — *Where GCP and Azure
   diverge from the AWS model* (GCP VPC is global with regional subnets; Azure VNet is
   regional but subnets aren't AZ-pinned) · Cloud NAT / Azure NAT Gateway / Private Service
   Connect / Private Endpoint as the equivalents of IGW/NAT GW/VPC Endpoints · peering
   non-transitivity verified as universal across all three. Read after Module 2 — assumes
   the AWS routing model from `networking.md`.

## Quick reference
- **[VPC cheatsheet](../../cheatsheets/vpc.md)** — one-page recall.

## Practice
- **[Terraform: 3-tier VPC](../../terraform/vpc/README.md)** — runnable, heavily commented, builds the canonical multi-AZ design (NAT Gateway included by default).
- **[Tutorial: The NAT Gateway Decision](tutorial-nat-gateway-decision.md)** — read after Module 2. Not new theory — applies `networking.md` §3c and `best-practices.md` §7 to a real either/or choice, worked through on two real VPCs already in this repo that land on opposite answers: the 3-tier module above (NAT by default) versus [`k8s/k8s_explorer/aws-kubeadm-cluster`](../../../../k8s/k8s_explorer/practice/aws-kubeadm-cluster/)'s cluster VPC (no NAT at all, and why that's the right call there specifically).

## Gates (self-test)
- [Module 1 gate](../../quizzes/vpc/module-1-gate.md) · [Module 2 gate](../../quizzes/vpc/module-2-gate.md). Each doc also ends with an inline **Self-check**.

---
*Convention:* every internal claim is tagged **[Documented]** (AWS docs / re:Invent / patents / whitepapers) or **[Inferred]** (reconstruction from behavior). Hold Inferred parts loosely.
