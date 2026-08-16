# AWS Service Quotas — Documentation set

Triggered by a real `VcpuLimitExceeded` hitting a first-ever GPU instance launch —
not a hypothetical topic. Read in order.

## Study order

1. **[architecture.md](architecture.md)** — *Why a quota caps a vCPU-metric, not an
   instance count · why GPU/accelerator families default to `0` on every fresh
   account · the full CLI request-and-poll lifecycle, with real request IDs and
   API output · On-Demand vs Spot as separate quotas · per-region scoping.*
   **Start here.**
2. **[troubleshooting.md](troubleshooting.md)** — three real errors from one
   session, in the order they actually occurred: missing `ec2:*` permissions,
   missing `servicequotas:*` permissions (a *different* IAM namespace — having one
   doesn't imply the other) plus the IAM-propagation-delay trap that looks like a
   failed fix but isn't, and finally the actual `VcpuLimitExceeded` root cause that
   no IAM policy can fix.

Quick recall: **[../../cheatsheets/service-quotas.md](../../cheatsheets/service-quotas.md)**.

## Not yet written
- `best-practices.md` — proactive quota management (CloudWatch alarms on quota
  utilization, requesting ahead of a known scale-up, `AWS Trusted Advisor`'s quota
  checks).
- `interview.md` — this topic doesn't usually get its own interview question, but
  "how do you handle X-limit-exceeded in production" is a common systems-design
  probe this would answer directly.
- Console-driven request flow (the grounding session used the CLI end-to-end).
- P/Inf/Trn family-specific quota codes.

---
*Convention:* claims tagged **[Documented]** (AWS docs / API behavior observed
directly) or **[Inferred]** (reconstruction from behavior). Hold Inferred loosely.
