# Service Quotas Cheatsheet

One-page recall. Full detail in [`../docs/service-quotas/`](../docs/service-quotas/README.md).

## Mental model
- A quota caps a **usage metric** (often "sum of vCPUs across running instances in
  a family group"), not a raw resource count. **4 vCPU quota = one `xlarge`, not
  "4 instances."**
- **Every fresh account: `0` vCPU limit on GPU/accelerator families (G, P, VT,
  Inf, Trn)** — anti-abuse default, not a bug or account-specific restriction.
  First GPU launch ever = budget for a quota-increase step in the critical path.

## The G/VT quota that gates `g4/g5/g6/vt1` instances
```
Quota code:  L-DB2E81BA
Quota name:  Running On-Demand G and VT instances
Metric:      vCPUs, summed, currently RUNNING instances only (stopped = free)
Scope:       per account, PER REGION
```

## IAM — two separate namespaces, easy to have one without the other
| Need | Policy |
|---|---|
| Launch/manage EC2 | `AmazonEC2FullAccess` (or scoped) |
| Read/request quota changes | `ServiceQuotasFullAccess` (or scoped) — **not implied by EC2 access** |

`ec2:Describe*` succeeding (AMI lookup, subnet lookup) is **not** evidence
`ec2:RunInstances`/`Create*` will work — often comes free from an unrelated
FullAccess policy (e.g. CloudFormation bundles broad Describe*).

## The 3-command flow
```bash
# 1. find the code
aws service-quotas list-service-quotas --service-code ec2 --region <r> \
  --query "Quotas[?contains(QuotaName,'G and VT')].[QuotaName,QuotaCode,Value]"

# 2. request (size to what you need, not the max)
aws service-quotas request-service-quota-increase \
  --service-code ec2 --quota-code L-DB2E81BA --desired-value 4 --region <r>

# 3. poll (PENDING -> CASE_OPENED -> CASE_CLOSED = approved, despite the name)
aws service-quotas get-requested-service-quota-change \
  --request-id <id> --query 'RequestedQuota.Status' --output text
```

## Traps
- **IAM propagation delay** after attaching a policy can look identical to "the
  attach failed." Poll with backoff (`until ... || sleep 10`), don't conclude
  failure from one immediate retry.
- **PENDING is not a client-side problem.** Nothing to retry/fix — it's an AWS
  review queue. Minutes to ~24-48h for a first small GPU request; move on and
  poll later.
- **On-Demand and Spot are separate quotas.** Fixing one doesn't fix the other —
  switching pricing models can hit the wall again under a different quota code.
- **Per-region.** Approved in `us-east-1` ≠ approved anywhere else. New region,
  new request, every time, for the first GPU launch there.
- `Adjustable: false` in `get-service-quota` output = hard ceiling, don't bother
  requesting.
