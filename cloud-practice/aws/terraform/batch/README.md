# Terraform: AWS Batch — Fargate compute environment, queue, job definition

Creates an AWS Batch setup that runs jobs on Fargate (no EC2 fleet to
size or patch): a managed compute environment, a job queue, and a job
definition. Runs a trivial `busybox` sleep-and-echo job by default so it
applies with **zero other modules**; point `container_image` at
`ecr/`'s `repository_url` for your own batch workload.

**Batch vs. `ecs-fargate/`:** ECS Fargate is for a **long-running
service** (a web server that should always have N copies up). Batch is
for **run-to-completion jobs** (a nightly ETL script, a video transcode,
a data-processing task) that start, do work, exit, and shouldn't be
"kept running" the way a service is.

> ⚠️ **Pay only while a job actually runs** — Fargate compute
> environments provision capacity per-job and tear it down after, unlike
> `ecs-fargate/`'s always-on service. Run `terraform destroy` when done
> experimenting.

## What it creates

```
IAM Service-Linked Role (AWSServiceRoleForBatch — see the import note below)
Security Group (no inbound, all outbound)
CloudWatch Log Group (/aws/batch/<project>)
Compute Environment (MANAGED, FARGATE or FARGATE_SPOT)
Job Queue (priority 1, points at the compute environment)
IAM Role: execution (pull image + ship logs)
IAM Role: job (your job's own AWS permissions — empty by default)
Job Definition (container, platform_capabilities = FARGATE)
```

## ⚠️ If `terraform apply` fails on the service-linked role
If this AWS account has ever used Batch before,
`AWSServiceRoleForBatch` already exists and creating it again fails.
Fix once with:
```bash
terraform import aws_iam_service_linked_role.batch \
  "$(aws iam get-role --role-name AWSServiceRoleForBatch --query Role.Arn --output text)"
```

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pin + default tags |
| `variables.tf` | Image/command, job sizing, Spot toggle |
| `main.tf` | Service-linked role, SG, log group, compute env, queue, roles, job def |
| `outputs.tf` | Queue/job-definition names + a `next_steps` runbook |

## Usage
```bash
cd aws/terraform/batch
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
aws batch submit-job --job-name manual-test --job-queue "$(terraform output -raw job_queue_name)" --job-definition "$(terraform output -raw job_definition_name)"
```

## Things to try (mini-labs)
1. Submit a job, then `describe-jobs` repeatedly — watch it walk `SUBMITTED → RUNNABLE → STARTING → RUNNING → SUCCEEDED` and tail its logs the moment it's `RUNNING`.
2. Submit 5 jobs at once (loop the `submit-job` command) with `max_vcpus` left low — watch some sit `RUNNABLE` (queued, waiting for capacity) while others run, then drain as capacity frees up.
3. Change `command` to `exit 1` and resubmit — the job shows `FAILED`, and (unlike Lambda/ECS) Batch does NOT auto-retry unless you add a `retry_strategy` block to the job definition.
4. Flip `use_fargate_spot = true`, re-`apply`, resubmit — functionally identical output, at a lower price point, with a (rare, for a 10-second job) chance of interruption.

## Deliberately minimal
- No `retry_strategy` (add `attempts` to the job definition for automatic
  retry on failure), no array jobs (running the same definition N times
  as a batch, e.g. "process files 1 through 1000"), no job dependencies.
