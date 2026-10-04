# net_modules: shared pieces for the networking demos (014, 015, 016)

```
net_modules/
├── test_vpc/          module: one VPC + one subnet + one test instance (tiny web server, SSM access)
└── scripts/lib.sh     test helpers: ssm_wait_online, ssm_exec, check, summary
```

`014_vpc_peering` and `015_transit_gateway` use `../net_modules/test_vpc`. `016_vpc_endpoints` is self-contained (it needs a private subnet without an internet gateway) but uses `lib.sh` for its tests. Don't move the lesson folders without fixing the relative paths.

## The test approach

Each demo creates instances you never SSH into. Tests run **on the instances through SSM Run Command**:

```
your laptop ──aws ssm send-command──▶ instance A ──curl http://<private IP of B>──▶ instance B
                                         ◀── output (200 or timeout) ──
```

`check "A -> B" <from-instance-id> <target-ip> <reachable|blocked>` prints PASS/FAIL against an expectation, so a test script both documents and verifies the intended behaviour. Prerequisites: AWS CLI v2, python3, credentials with `ssm:SendCommand`/`ssm:GetCommandInvocation`, and the instances registered with SSM (the scripts wait for it).

*(verified)* `lib.sh` logic was exercised against a stubbed `aws` command under both bash and zsh (PASS, PASS, and a deliberate FAIL with exit code 1). It has not run against real instances yet.

# Which connectivity tool, when?

| Need | Use | Lesson |
|---|---|---|
| Connect **two** VPCs, simple, free | **VPC peering** | 014 |
| Connect **many** VPCs / accounts, transitive, segmentation, or VPN/Direct Connect hub | **Transit Gateway** | 015 |
| Reach an **AWS service** (S3, DynamoDB) privately, free | **Gateway endpoint** | 016 |
| Reach any other AWS service (or a partner/own service) privately | **Interface endpoint (PrivateLink)** | 016 |
| Expose **one service** to other VPCs/accounts without joining networks | **PrivateLink endpoint service** (NLB behind it) | not covered |
| Give private instances general internet access | **NAT gateway** | see lesson 010 notes |
| Connect on-premises | **Site-to-Site VPN / Direct Connect** (often into a TGW) | not covered |

## Peering vs Transit Gateway vs PrivateLink: the key difference

- **Peering and TGW connect networks**: instances in one VPC can reach (almost) anything in the other, subject to routes and security groups. CIDRs must not overlap.
- **PrivateLink / endpoints expose a service**, not a network: consumers get an IP for that one service; overlapping CIDRs are fine and there is no route to the rest of the provider's VPC.

## Order of experiments

1. 014 peering: see that routes are needed and that peering is not transitive.
2. 015 transit gateway: see the transitive version, plus segmentation.
3. 016 endpoints: see private access to AWS services with no internet.

Run them **one at a time and destroy each before the next** (`terraform destroy`) so costs stay in cents; 015 (~$0.15/hr for three attachments) and 016 (~$0.03/hr for interface endpoints) are the ones that bill noticeably.

## Cost summary *(approximate; verify current pricing)*

| Demo | While running |
|---|---|
| 014 peering | 3 × t4g.nano ≈ $0.013/hr; peering free; cross-AZ/region data only |
| 015 transit gateway | ≈ $0.15/hr attachments + $0.013/hr instances + ~$0.02/GB processed |
| 016 endpoints | ≈ $0.03/hr interface endpoints + $0.004/hr instance; gateway endpoint free |
