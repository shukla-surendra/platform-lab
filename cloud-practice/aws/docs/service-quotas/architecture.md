# AWS Service Quotas — mechanism, and why a brand-new GPU launch fails at 0

> **Epistemics:** claims tagged **[Documented]** (AWS docs / API behavior observed
> directly) or **[Inferred]** (reconstruction from behavior). Hold Inferred parts
> more loosely.

Triggered by a real launch failure, not a hypothetical: `terraform apply` on a
`g6.xlarge` (an EC2 GPU instance) failed with

```
VcpuLimitExceeded: You have requested more vCPU capacity than your current vCPU
limit of 0 allows for the instance bucket that the specified instance type
belongs to.
```

on an AWS account that had **never launched a GPU instance before** — no wrongdoing,
no misconfiguration, no IAM problem at that point. This is the default state of
every fresh account for this instance family, and the mechanism behind it is worth
understanding on its own, not just patching around.

## Mental model

**A quota is a ceiling on a *metric*, not on a resource type directly.** Service
Quotas doesn't ask "can I create this thing" — it asks "after this action, will a
tracked *usage metric* exceed its current *limit*." For EC2 instance families, the
tracked metric is almost never "instance count." It's **total vCPUs summed across
every currently-running instance in that family group, per account, per region.**

That distinction matters immediately: a quota of `4` doesn't mean "4 instances." It
means "4 vCPUs, total, running, right now, across the whole family group." One
`g6.xlarge` (4 vCPUs) uses the entire quota. Launch a second one — even a tiny
one — while the first is running, and it fails the same way, for the same reason,
even though "instance count" never comes up anywhere in the quota's name or
definition.

```
                    ┌─────────────────────────────────────┐
                    │   "Running On-Demand G and VT        │
                    │    instances" quota — one number,    │
                    │    account+region scoped             │
                    └───────────────┬───────────────────────┘
                                    │ caps
                                    ▼
        sum of vCPUs, across ALL running instances, in EITHER family:
        ┌──────────────────────┐        ┌──────────────────────┐
        │   G family (GPU)     │        │   VT family (video)  │
        │  G4, G5, G6, G6e...  │   +    │  VT1 (Xilinx media   │
        │  ML/inference/       │        │  transcoding accel)  │
        │  graphics workloads  │        │                      │
        └──────────────────────┘        └──────────────────────┘
```
**[Documented]** AWS groups G and VT into one shared quota bucket rather than a
quota per instance type — historically, both families draw from overlapping
accelerator-hardware capacity pools, so AWS quotas the pool, not each SKU
individually.

## Why it starts at `0`, specifically for accelerator families

**[Documented]** Every new (or GPU-history-free) AWS account defaults to a **`0`
vCPU limit** on every accelerator instance family — G, P (also GPU), VT, Inf/Trn
(AWS's own inference/training silicon) — not just G/VT. This is stated AWS policy,
not a bug or an account-specific restriction: GPU capacity is the instance category
most commonly targeted for unauthorized use (crypto-mining on a compromised or
free-trial account being the canonical case AWS cites), so AWS requires an explicit,
often manually-reviewed increase before **any** instance in these families can
launch — including a single `t`-shirt-sized one for a legitimate side project.
Nothing about a specific account's configuration triggers this; it's the starting
line for everyone.

Practically, this means: **the very first time you ever try to launch a GPU
instance in a fresh account, budget for this step being in the critical path.**
It's not something Terraform, IAM, or any client-side tooling can route around —
it's an AWS-side gate that has to be cleared before `RunInstances` will succeed at
all, regardless of how correct everything else is.

## Requesting an increase — the actual CLI walkthrough

Two separate AWS-managed IAM policies are involved, and it's easy to have one
without the other (this is exactly what happened in the session this doc is
grounded in — see `troubleshooting.md`):

- `AmazonEC2FullAccess` (or narrower) — lets you launch/manage EC2 resources
- `ServiceQuotasFullAccess` (or narrower) — lets you **read and request changes to
  quotas at all**. Having full EC2 access does *not* imply Service Quotas access;
  they're entirely separate IAM namespaces (`ec2:*` vs `servicequotas:*`).

**1. Find the exact quota code.** Quota names are searchable, but the code is what
every other API call needs:

```bash
aws service-quotas list-service-quotas --service-code ec2 --region us-east-1 \
  --query "Quotas[?contains(QuotaName, 'G and VT') || contains(QuotaName, 'Running On-Demand G')].[QuotaName,QuotaCode,Value]" \
  --output table
```

**2. Confirm the current value** (this is what a `VcpuLimitExceeded` at launch
already told you indirectly — `0` — but worth checking directly before requesting):

```bash
aws service-quotas get-service-quota --service-code ec2 --quota-code L-DB2E81BA --region us-east-1
```

```json
{
  "Quota": {
    "QuotaName": "Running On-Demand G and VT instances",
    "Value": 0.0,
    "Adjustable": true,
    "UsageMetric": {
      "MetricDimensions": { "Class": "G/OnDemand", "Resource": "vCPU", "Service": "EC2" }
    },
    "QuotaAppliedAtLevel": "ACCOUNT"
  }
}
```

`"Adjustable": true` matters — some quotas are hard ceilings AWS won't move at all;
this confirms it's a request-and-wait situation, not a dead end.

**3. Request the increase**, sized to what you actually need — not the biggest
number available. One `g6.xlarge` needs 4 vCPUs, so request 4, not 32:

```bash
aws service-quotas request-service-quota-increase \
  --service-code ec2 --quota-code L-DB2E81BA \
  --desired-value 4 --region us-east-1
```

```json
{
  "RequestedQuota": {
    "Id": "28ed8b9b4bdb40d58ced84603ca83cdcKlXNdke1",
    "DesiredValue": 4.0,
    "Status": "PENDING"
  }
}
```

**4. Poll for approval** using the returned request ID:

```bash
aws service-quotas get-requested-service-quota-change \
  --request-id 28ed8b9b4bdb40d58ced84603ca83cdcKlXNdke1 \
  --query 'RequestedQuota.Status' --output text
```

`PENDING` → `CASE_OPENED` (AWS support is actively reviewing) → `CASE_CLOSED`
(approved — despite the name, this means success, not rejection). **[Inferred]**
For a first-ever small GPU request like this (4 vCPUs, one instance's worth), this
commonly resolves in minutes to a few hours; it is not guaranteed instant the way
most non-accelerator quota increases are, and can occasionally take up to 24-48h for
accounts with zero billing/usage history. There is nothing to retry or fix while
`PENDING` — it's genuinely an AWS-side review queue, not a client-side problem.

**5. Once approved, nothing else needs to change.** Retry the exact same launch —
`RunInstances` (or `terraform apply`) — and it succeeds against the new limit.

## Scoping — the two axes that trip people up

- **Per region.** This quota is evaluated **per AWS region**, independently. An
  approved increase in `us-east-1` does nothing for `eu-west-2` — a fresh request is
  needed there too, the first time you launch a GPU instance in any new region.
- **On-Demand vs Spot are separate quotas entirely**, not two views of the same
  number. `Running On-Demand G and VT instances` (`L-DB2E81BA`) is unrelated to
  `All G and VT Spot Instance Requests` (a different quota code) — switching a
  workload from on-demand to spot pricing can hit this exact same wall again under a
  different quota, even in a region and account where on-demand already works.

## Not yet covered

- Requesting via the Service Quotas **console** (vs. CLI) — the flow above is CLI
  end-to-end since that's what the triggering session used.
- The Spot-specific quota code and its own request flow.
- P/Inf/Trn family quotas (same `0`-default mechanism, different quota codes) —
  relevant if this account ever needs `p4d`/`p5`/Trainium/Inferentia instances.
