# AWS IAM — Documentation set

Identity and Access Management, from first principles: the four entity
types, how a policy document actually gets evaluated, and the
Users-vs-Roles distinction that everything else in AWS security assumes
you already have straight.

## Study order

1. **[architecture.md](architecture.md)** — *What IAM actually is · Users
   vs Groups vs Roles vs Policies · the two-policy shape of a Role (trust
   vs permission) · how STS/AssumeRole mints temporary credentials · the
   exact policy-evaluation algorithm (explicit deny, same-account vs
   cross-account, permission boundaries).* **Start here.**

## Hands-on

- **[Terraform: IAM](../../terraform/iam/README.md)** — a real Group
  with a custom policy, a User in that group, and a Role with its own
  trust + permission policies pointed at an S3 bucket. Applied and
  verified live: `sts assume-role`, then one call that's allowed and one
  that gets a real `AccessDenied` — proof the policy boundary holds, not
  just a description of it.

## Related

- Already built the Azure side of this same story:
  [`cloud-practice/azure/terraform/function-storage-rbac/README.md`](../../../azure/terraform/function-storage-rbac/README.md)
  is the AWS-IAM-to-Azure-RBAC translation, verified against a real
  least-privilege Azure Function. Worth reading after this once the AWS
  model is solid again — the concepts rhyme, but Azure splits "identity"
  and "what it can do" into two separate resource types where AWS's Role
  bundles them into one.

---
*Convention:* claims tagged **[Documented]** (AWS docs / re:Invent /
whitepapers) or **[Inferred]** (reconstruction from behavior). Hold
Inferred loosely.
