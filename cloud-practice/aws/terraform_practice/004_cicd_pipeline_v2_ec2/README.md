# V2 CI/CD pipeline → EC2

> **Status (2026-09-20): applied, verified end to end, then destroyed.** The code
> here is the working reference. To run it again, first re-apply
> `../000_bootstrap_state_bucket` (it makes a *new* bucket — put its name in
> `versions.tf`). The whole story is in [`../JOURNEY.md`](../JOURNEY.md).

CodeCommit → CodeBuild → **manual approval** → CodeDeploy → one EC2 instance,
as a **V2** CodePipeline. Successor to `003_cicd_pipeline_ec2` (V1); read
[`../003_cicd_pipeline_ec2/LEARNINGS.md`](../003_cicd_pipeline_ec2/LEARNINGS.md)
for why every difference below exists. Applied and verified end to end against real
AWS on 2026-09-20 (push → run → approve → deploy → `curl`).

> ⚠️ Real cost while it's up — mainly the `t3.micro` (~$0.0104/hr off Free Tier).
> `terraform destroy` when done. See "Cost" below.

```
git push (branch main)
   │  EventBridge rule (~16s)
   ▼
CodePipeline V2 ── Source ─▶ Build ─▶ Approval ─▶ Deploy ──▶ EC2 (tag Name=<project>)
                              ▲           (human)
       run-time variables ────┘ DEPLOY_NOTE → CodeBuild env var → index.html
```

## Usage

Prerequisite: apply `../000_bootstrap_state_bucket` first (the remote-state bucket
named in `versions.tf`). The CLI user needs permissions for CodeCommit, CodeBuild,
CodeDeploy, CodePipeline, EventBridge, IAM, EC2, S3, CloudWatch Logs and SSM.

```bash
cd 004_cicd_pipeline_v2_ec2
terraform init
terraform apply          # 24 resources; variables all have defaults
```

### First push (the repo starts empty — the pipeline has nothing to build until you do this)

Uses per-repo git config, so your global git config is untouched. Copy
`app-sample/` (its scripts are already `+x`; keep it that way — git must record
mode `100755`).

```bash
export AWS_DEFAULT_REGION=us-east-1
git -c credential.helper= -c 'credential.helper=!aws codecommit credential-helper $@' \
    -c credential.UseHttpPath=true clone "$(terraform output -raw clone_url_http)" app-repo
cd app-repo
git config --local credential.helper ''
git config --local --add credential.helper '!aws codecommit credential-helper $@'
git config --local credential.UseHttpPath true
git checkout -b main
cp -r ../app-sample/. .
git add . && git commit -m "initial" && git push -u origin main
```

The pipeline's automatic first run (at creation, on the empty repo) **fails at
Source — expected.** The push starts a real one within seconds.

### Approve

The run stops at **Approval**. Console: CodePipeline → pipeline → Approval → Review. CLI:

```bash
P=cicd-practice-v2; R=us-east-1
TOKEN=$(aws codepipeline get-pipeline-state --name $P --region $R \
  --query 'stageStates[?stageName==`Approval`].actionStates[0].latestExecution.token' --output text)
# the token appears a moment after the stage goes InProgress — make sure it's a UUID
aws codepipeline put-approval-result --region $R --pipeline-name $P \
  --stage-name Approval --action-name ApproveDeploy --token "$TOKEN" \
  --result 'summary=looks good,status=Approved'      # status=Rejected to stop the run
```

⚠️ No commas inside `summary=` — the CLI shorthand splits on them.

### Run with a value (the V2 feature)

```bash
aws codepipeline start-pipeline-execution --name cicd-practice-v2 --region us-east-1 \
  --variables name=DEPLOY_NOTE,value="hello"
# after approval:
curl "http://$(terraform output -raw instance_public_ip)/"     # "Deploy note hello"
```

### Run a specific commit (e.g. from another branch)

The branch itself **cannot** be a run-time variable (AWS: "Variables at the pipeline
level cannot be used in source actions"), but a commit can be overridden:

```bash
aws codepipeline start-pipeline-execution --name cicd-practice-v2 --region us-east-1 \
  --source-revisions actionName=Source,revisionType=COMMIT_ID,revisionValue=<sha>
```

Pushing a branch other than `main` starts nothing (the EventBridge rule matches only
`var.branch_name`).

### Watching a run from a script

`get-pipeline-state` shows each stage's *latest* execution, which may be an older
one. Track the run by ID — `get-pipeline-execution --pipeline-execution-id <id>` —
or you'll see stale `Succeeded`s.

## What it creates (24 resources)

```
ec2.tf          Security Group (HTTP only), IAM role+profile (SSM + read pipeline bucket), EC2 instance (httpd + CodeDeploy agent)
codecommit.tf   CodeCommit repository
codedeploy.tf   IAM role, CodeDeploy app, deployment group (targets the instance by Name tag)
codebuild.tf    CloudWatch log group, IAM role, CodeBuild project (CODEPIPELINE source/artifacts)
codepipeline.tf S3 artifact bucket (force_destroy), IAM role, V2 pipeline w/ variable + approval, EventBridge rule/target/role
outputs.tf      IP, ids, clone URL, next_steps
app-sample/     The app that goes into the CodeCommit repo (NOT part of the Terraform)
```

## What differs from 003

| | 003 (V1) | 004 (V2) |
|---|---|---|
| Pipeline type | V1 (Terraform default) | `V2`, `execution_mode = SUPERSEDED` |
| Run-time values | none | `DEPLOY_NOTE` variable → CodeBuild env var |
| Trigger | polling | EventBridge on the CodeCommit branch (~16s) |
| Manual approval | added later | built in |
| CodeBuild source/output | CODECOMMIT + its own S3 bucket (never used by the pipeline) | `CODEPIPELINE`, no extra bucket |
| CodeBuild logs | role couldn't create the log group → build failed | log group created in Terraform |
| CodeBuild / instance ↔ pipeline bucket | missing → Build and Deploy failed | granted |
| Hook-script permissions | `644` → risk of failing | `755` |
| SSH ingress | `0.0.0.0/0` on a key-less instance | removed (use SSM) |
| Instance type | hardcoded `t3.micro` | `instance_type` variable |
| Bucket teardown | `destroy` failed until emptied by hand | `force_destroy = true` |
| Remote state | local | S3 (`use_lockfile`) |

Trade-off of `CODEPIPELINE`-type CodeBuild: `aws codebuild start-build` no longer works
standalone — builds run from the pipeline.

## Cost

| Resource | Driver | Approx. |
|---|---|---|
| EC2 `t3.micro` | hourly while running | Free Tier $0; else ~$0.0104/hr (~$0.50/2 days) |
| CodePipeline V2 | $0.002 per action-execution-minute; 100 free min/month; **manual approval not billed** | ~$0.01 per run → $0 within the free minutes |
| CodeBuild | per build-minute | fractions of a cent per run |
| CodeDeploy (EC2) | — | always $0 |
| CodeCommit, S3, EventBridge, Logs | — | ~$0 at this scale |

Prices are as read from AWS's pricing pages on 2026-09-20 — check your own bill.

## Teardown

```bash
terraform destroy
```

Deletes the CodeCommit repo permanently (with its history) and the artifact bucket's
contents. `../000_bootstrap_state_bucket` is deliberately left alone.

## Follow-ups

Scope the pipeline role's `codedeploy:*` off `Resource = "*"`; SNS email for the
approval stage; try `QUEUED` / `PARALLEL` execution modes; a GitHub + CodeConnections
source to use real V2 trigger filters (branches, tags, paths).
