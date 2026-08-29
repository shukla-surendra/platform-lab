# Tutorial: The NAT Gateway Decision, Worked Through on Two Real VPCs

> Part of the AWS Mastery track. See [PROGRESS.md](../../../PROGRESS.md).
> **Epistemics:** **[Documented]** = AWS docs / re:Invent / whitepapers · **[Inferred]** = reconstruction from behavior + standard designs.
> **Prereq:** [architecture.md](architecture.md) (the two-networks model) and
> [networking.md](networking.md) §3c (NAT Gateway packet flow) — this tutorial doesn't
> re-derive the mechanism, it applies it to an actual decision. [best-practices.md](best-practices.md)
> §7 already covers NAT's cost profile in depth; this is the "which side of that tradeoff
> do I actually pick, right now, for this VPC" companion piece.

Every other doc in this set explains NAT Gateway *mechanism* and *cost*. This one answers
the question that actually matters when you sit down to write `network.tf`: **do I need
one at all?** — worked through on two real Terraform VPCs that already exist in this repo
and land on opposite answers, on purpose.

## The decision, as a table

| | Public subnet + public IP + tight SG | Private subnet + NAT Gateway |
| --- | --- | --- |
| Outbound internet access | Yes, direct via IGW | Yes, via NAT's SNAT |
| Inbound reachability | **Structurally possible** — blocked only by your security group rules (a config you could get wrong) | **Structurally impossible** — the instance has no public IP at all, no rule to misconfigure |
| Cost | $0 beyond the public-IPv4-address charge (~$0.005/hr each, since Feb 2024) | NAT GW hourly (~$0.045/hr) + per-GB processed — [best-practices.md §7](best-practices.md) has the full breakdown |
| Fits | Short-lived sandboxes, bastion hosts, anything that's *supposed* to be reachable | Anything long-lived where "no inbound, ever" should be a property of the network, not a firewall rule you have to trust |

The two examples below are this table, made concrete.

## Example 1: `terraform/vpc/` — chooses NAT, because it's modeling production

[`../../terraform/vpc/variables.tf`](../../terraform/vpc/variables.tf) defaults
`single_nat_gateway = true` — this module provisions a NAT Gateway **by default**, with
its own variable specifically to choose between one-per-AZ (prod: no cross-AZ egress
charges, survives an AZ loss) and one-shared (dev: cheaper, single-AZ failure domain).
That variable existing at all tells you the module's whole shape: it's modeling a
tiered VPC (public/app/data subnets) where app and data tiers are **never** supposed to
be reachable from the internet — NAT is there because that "never" needs to be a real
network property, not a security-group promise.

## Example 2: `k8s_explorer/aws-kubeadm-cluster/terraform/` — skips NAT entirely, because it's a sandbox

[`../../../../k8s_explorer/aws-kubeadm-cluster/terraform/network.tf`](../../../../k8s_explorer/aws-kubeadm-cluster/terraform/network.tf)
has no `aws_nat_gateway` resource at all. Every node sits in one public subnet with
`map_public_ip_on_launch = true`, and the route table sends `0.0.0.0/0` straight to the
Internet Gateway:

```
Public subnet (this example)                 Private subnet + NAT (the other example)
┌──────────────────────────┐                  ┌─────────────────────────┐
│ EC2, has a public IP     │──▶ IGW ──▶ Internet   │ EC2, private IP only   │──▶ NAT GW ──▶ IGW ──▶ Internet
│ reachable both ways      │◀──              │ no inbound possible     │◀──
└──────────────────────────┘                  └─────────────────────────┘
```

**Why this is the right call here, not a shortcut**: the whole point of that stack is a
throwaway kubeadm cluster you SSH into directly, spin up for a session, and
`terraform destroy` when done. There's no "data tier" needing structural isolation — the
entire cluster *is* meant to be directly reachable by exactly one person. What actually
protects it is
[`security_group.tf`](../../../../k8s_explorer/aws-kubeadm-cluster/terraform/security_group.tf):
SSH (22) and the NodePort range (30000-32767) are both scoped to a single `/32` — your
own IP, passed in as a required Terraform variable with no default, specifically so you
can't accidentally apply this with `0.0.0.0/0`. That's the config-could-be-wrong side of
the table above, being carried consciously, in exchange for real savings on a stack meant
to live for hours, not months.

## The cost difference, in real numbers for this exact comparison

Running the kubeadm-cluster's 3 nodes with no NAT: **≈ $0.08/hour** total (compute +
public-IPv4 charges only — see that project's own `README.md` for the full breakdown).
Adding a single shared NAT Gateway to that same stack would add ~$0.045/hr baseline
*regardless of whether any node ever sends a byte through it* — for a 3-node sandbox torn
down after a few hours, that's paying a fixed penalty for an isolation property nothing
in the stack actually needed.

This is exactly [best-practices.md §7](best-practices.md)'s "NAT Gateway is the #1 hidden
cost" point, but seen from the other direction: the fix isn't always a gateway endpoint or
consolidating NAT GWs — sometimes the fix is noticing you don't need inbound isolation at
all for *this particular* VPC, and a public subnet plus a correctly-scoped security group
is a legitimate, cheaper answer to the actual requirement.

## Self-check

1. Both `terraform/vpc/` and the kubeadm-cluster VPC give instances *outbound* internet
   access. What's the one thing NAT Gateway adds that a plain Internet Gateway + public IP
   doesn't?
2. The kubeadm-cluster's security group opens the NodePort range to your `/32` IP. If you
   ran `terraform apply` with `allowed_ssh_cidr = "0.0.0.0/0"` instead, what would actually
   become reachable from the entire internet, and is a NAT Gateway relevant to fixing that?
3. You're asked to add a data tier (RDS, say) to the kubeadm-cluster stack. Would you keep
   the public-subnet-only design, or is this the point where the "private subnet + NAT"
   side of the table above becomes the right call? Justify it in terms of what property
   you'd now need structurally guaranteed, not just cost.
