# Terraform Complete Reference

> A concise, practical reference from basics to enterprise practice — tool-general (not AWS-only), with AWS used for concrete examples.

> **Learning Terraform from scratch?** Start with the step-by-step course
> [`aws/terraform-zero-to-hero/`](../aws/terraform-zero-to-hero/) (25 lessons, from the basics to internals
> and interview prep), and come back here as a quick reference.

This is a cross-cutting reference, not a service module. It complements the runnable per-service Terraform under [`aws/terraform/`](../aws/terraform/) (VPC, EBS, EFS, SageMaker, Bedrock).

## Contents

| # | File | What's inside |
|---|------|---------------|
| 1 | [Fundamentals](01-fundamentals.md) | What Terraform is, architecture, lifecycle, project files, the command set, how a run works internally. Start here. |
| 2 | [State & backends](02-state-and-backends.md) | Why state exists, local vs remote, S3 backend config, locking (`use_lockfile`), one-vs-many states, state commands, the dependency graph. |
| 3 | [Project structure](03-project-structure.md) | Root vs child modules, module design, repo layouts (monorepo vs per-project), environment strategy, workspaces, team ownership, an enterprise case study. |
| 4 | [Variables, CI/CD & operations](04-variables-cicd-and-operations.md) | **Variable precedence / how values get overridden**, a real **CI/CD pipeline (GitHub Actions YAML)**, drift detection, importing resources, troubleshooting, the pre-deploy checklist. |
| 5 | [Internals & tool comparison](05-internals-and-comparison.md) | How Terraform works internally, how it talks to AWS (Core ↔ provider plugin), execution model, Terraform vs CloudFormation vs CDK, use cases, case studies, interview Q&A. |

## How to read this

- **New to Terraform:** 1 → 2 → 3 in order.
- **"How do pipelines and variable overrides actually work?"** → [file 4](04-variables-cicd-and-operations.md).
- **Interview / concept refresh:** [file 5](05-internals-and-comparison.md) (ends with a Q&A bank).
