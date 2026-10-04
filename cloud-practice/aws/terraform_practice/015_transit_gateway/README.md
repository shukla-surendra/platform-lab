# 015 – Transit Gateway: one hub, three VPCs, transitive routing

Checked so far *(verified)*: `terraform validate` passes; test helpers exercised against a stubbed `aws` CLI. **Not applied in AWS yet**; behaviour below is the intended outcome to confirm tomorrow. One thing to watch when you apply is called out under "Things to watch".

```
   VPC A 10.10.0.0/16 ──attachment──┐
   VPC B 10.20.0.0/16 ──attachment──┼──▶  Transit Gateway  (route table "main")
   VPC C 10.30.0.0/16 ──attachment──┘
```

Compare with lesson 014: with peering, A and C could not talk. Here every attached VPC reaches every other one **through the hub**, and a 4th VPC costs one attachment instead of 3 new peerings.

## What this teaches

| Concept | Resource |
|---|---|
| The hub | `aws_ec2_transit_gateway` |
| **Attachment**: connects a VPC (via a subnet per AZ) | `aws_ec2_transit_gateway_vpc_attachment` |
| **TGW route table**: the hub's own routing | `aws_ec2_transit_gateway_route_table` |
| **Association**: which TGW route table an attachment's traffic uses | `..._route_table_association` (exactly one per attachment) |
| **Propagation**: which TGW route tables *learn* an attachment's CIDR automatically | `..._route_table_propagation` |
| VPC routes still needed: send lab traffic to the TGW | `aws_route.*_to_tgw` (`10.0.0.0/8 -> tgw`) |
| **Segmentation** with separate route tables | `isolate_vpc_c = true` |

Default TGW association/propagation is **disabled** on purpose, so all routing is explicit in the code.

## Run

```
terraform init
terraform plan
terraform apply        # attachments take 1-3 min each
./scripts/test_tgw.sh
```

Expected (default, full mesh): the script first prints the TGW route table (three CIDRs learned by propagation), then six PASS lines, including A->C and C->A (blocked in lesson 014).

## Experiment: segmentation

```
terraform apply -var isolate_vpc_c=true
./scripts/test_tgw.sh
```
C now has its own, empty TGW route table: A<->B still PASS; every test involving C is expected `blocked` (and the script expects that). Reverting: `terraform apply`.

## Peering vs Transit Gateway (what you should be able to say after this)

| | Peering (014) | Transit Gateway (015) |
|---|---|---|
| Topology | 1:1 links, full mesh needs n(n-1)/2 | hub and spoke, n attachments |
| Transitive | **No** | **Yes** (controlled by TGW route tables) |
| Segmentation | via routes and SGs only | TGW route tables (isolate groups) |
| Routing | static routes per VPC per peer | one route to the TGW; hub learns CIDRs by propagation |
| Cost | peering free (data transfer only) | per attachment-hour + per GB processed |
| Also connects | VPCs only | VPN, Direct Connect, other regions (peering of TGWs) |
| Limits | few peers is simple, many is unmanageable | scales to many VPCs/accounts (share with RAM) |

## Cost *(approximate; verify)*: this one is not free

About **$0.05 per attachment-hour** (×3 ≈ $0.15/hr ≈ $3.60/day) plus about **$0.02 per GB** processed, plus 3 × t4g.nano. Destroy the same day: `terraform destroy` (TGW and attachments take a few minutes to delete).

## Things to watch when you apply (not verified)

- Attachments are created with `transit_gateway_default_route_table_association/propagation = false` because associations are managed explicitly. If the provider complains about those arguments or the associations fail, check the provider docs for the current behaviour with a TGW that has defaults disabled.
- VPC routes depend on the attachment being `available`; the code has `depends_on`, but re-running `apply` fixes a transient ordering error.
- If a test fails, look at: TGW route table contents (the script prints it), VPC route tables (`10.0.0.0/8 -> tgw-...`), security groups.
