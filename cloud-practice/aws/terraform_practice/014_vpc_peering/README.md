# 014 – VPC peering: A <-> B <-> C (and why A cannot reach C)

Checked so far *(verified)*: `terraform validate` passes; the test helpers were exercised against a stubbed `aws` CLI (PASS/FAIL logic). **Not applied in AWS yet**: the instance/route behaviour below is what the design should produce and is what you will confirm tomorrow.

```
 VPC A 10.10.0.0/16 ◀══ peering a-b ══▶ VPC B 10.20.0.0/16 ◀══ peering b-c ══▶ VPC C 10.30.0.0/16
   instance + web                          instance + web                         instance + web
              └────────────────────── A and C are NOT connected ──────────────────────┘
```

Each VPC has one tiny instance (t4g.nano, Amazon Linux 2023) running a web server on port 80 that answers `hello from peer-X`. You test by running `curl` **from one instance to another's private IP**, through SSM (no keys, no open SSH).

Shared building blocks live in `../net_modules/` (a one-VPC-one-instance module + test helpers).

## What this teaches

| Concept | Where to see it |
|---|---|
| A peering connection is a 1:1 link between two VPCs | `aws_vpc_peering_connection` (`auto_accept` works in one account + one region) |
| It does nothing until **routes** exist on **both** sides | `aws_route.a_to_b`, `b_to_a`, `b_to_c`, `c_to_b` |
| Security groups must also allow the traffic | `allowed_ingress_cidrs` in the module |
| **Not transitive**: A->B and B->C does not give A->C | tests 5 and 6 below |
| CIDRs must not overlap | the three CIDRs are different on purpose |

## Run

```
terraform init
terraform plan
terraform apply          # ~2-3 min
./scripts/test_peering.sh
```

Expected output (default settings):

```
PASS  A -> B   expected reachable got reachable (http 200)
PASS  B -> A   expected reachable got reachable
PASS  B -> C   expected reachable got reachable
PASS  C -> B   expected reachable got reachable
PASS  A -> C   expected blocked   got blocked   (http 000)   <- not transitive
PASS  C -> A   expected blocked   got blocked
```
A blocked check takes about 5 seconds (curl timeout) each.

## Experiments (change one variable, re-apply, re-run the test script)

| Experiment | Command | Expected |
|---|---|---|
| Peering without routes | `terraform apply -var enable_routes=false` | everything blocked (the test script adapts its expectations) |
| Prove non-transitivity | `terraform apply -var try_transitive_route=true` | A<->C routes added via B, **still blocked**: B never forwards between two peerings |
| Back to normal | `terraform apply` | |

Also look in the console: VPC -> Peering connections (status `Active`), and each route table's routes (`pcx-...` targets).

## Debugging checklist (when "peering doesn't work")

1. Peering status `Active` (accepted)?
2. Route in **both** route tables, destination = the **other** VPC's CIDR?
3. Security groups allow the source CIDR on the port (and NACLs, if customised)?
4. CIDRs overlap? (peering cannot be created)
5. Trying to go through a third VPC? Peering is not transitive; use a Transit Gateway (lesson 015).

## Cost *(approximate; verify)*

The peering connection itself is free. You pay for data transfer between AZs or regions (same-AZ traffic inside a region is free), 3 × t4g.nano (~$0.004/hr each) and nothing else. **Destroy when done**: `terraform destroy`.

## Notes

- The instances sit in **public** subnets with public IPs only so the SSM agent can reach AWS. The traffic under test uses **private IPs** and the peering routes (more specific than the default route).
- If `ssm_wait_online` times out, the instance hasn't registered with SSM yet (give it a few minutes) or lacks outbound internet.
