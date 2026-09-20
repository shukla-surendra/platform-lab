# CI/CD Pipeline → EC2 — full implementation

> **Status (2026-09-20): applied, run end to end, then destroyed. Superseded by
> [`../004_cicd_pipeline_v2_ec2`](../004_cicd_pipeline_v2_ec2/)** (a V2 pipeline with the
> fixes below built in). Read **[`LEARNINGS.md`](LEARNINGS.md)** for everything this
> exercise taught. This folder is kept as the V1 reference.
>
> **Corrections to the original version of this README:**
> - It claimed the module was "verified against real AWS (`terraform plan`: 20
>   resources, 0 errors)". A `plan` verifies neither IAM nor runtime behavior — the first
>   real run failed three ways. Those are fixed in this folder's `codebuild.tf` /
>   `ec2.tf`, and the pipeline now includes an Approval stage.
> - Its cost estimate (~$1.50–1.60 for 2 days, "dominated by CodePipeline's flat $1")
>   was wrong — see the corrected "Cost" section below.

A CodeCommit → CodeBuild → [Approval] → CodeDeploy → CodePipeline (**V1**)
setup that deploys a simple app onto a single EC2 instance every time you
push. See `STEP_BY_STEP.md` if you'd rather build it yourself, one stage at
a time, instead of using this as-is.

> ⚠️ **Real cost while it's up** — mainly the EC2 instance. See "Cost" below.
> `terraform destroy` when you're done.

## Architecture

```
git push
   │
   ▼
CodeCommit (repo)  ──polled──▶  CodePipeline
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              Source stage     Build stage       Deploy stage
              (pulls repo)     (CodeBuild runs    (CodeDeploy copies
                                buildspec.yml,      files, runs
                                produces a zip)     appspec.yml hooks)
                                                          │
                                                          ▼
                                                   EC2 instance
                                                   (tagged Name=<project>,
                                                    running httpd +
                                                    the CodeDeploy agent)
```

## What it creates

```
ec2.tf          Security Group, IAM role+profile (SSM), EC2 instance (httpd + CodeDeploy agent via user_data)
codecommit.tf   CodeCommit repository
codedeploy.tf   IAM role, CodeDeploy application, deployment group (targets the instance by Name tag)
codebuild.tf    S3 artifact bucket, IAM role, CodeBuild project (reads buildspec.yml from the repo)
codepipeline.tf S3 artifact bucket, IAM role, the 3-stage pipeline (Source -> Build -> Deploy)
outputs.tf      IPs/names/URLs + a next_steps runbook
```

## Usage

```bash
cd 003_cicd_pipeline_ec2
cp terraform.tfvars.example terraform.tfvars   # set allowed_ssh_cidr to your IP/32
terraform init
terraform apply
terraform output next_steps
```

### First push (the pipeline has nothing to build until you do this)
```bash
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true

git clone "$(terraform output -raw clone_url_http)" app-repo
cp -r appspec-sample/* app-repo/
cd app-repo
git add . && git commit -m "initial" && git push
cd ..
```
CodePipeline polls for changes roughly once a minute (`PollForSourceChanges
= "true"` in `codepipeline.tf`) — within a minute of that push, watch it
run:
```bash
watch aws codepipeline get-pipeline-state --name "$(terraform output -raw pipeline_name)"
```
Once the Deploy stage shows `Succeeded`:
```bash
curl "http://$(terraform output -raw instance_public_ip)/"
```

### Every push after that is automatic
```bash
cd app-repo
echo "<p>v2 — $(date -u)</p>" >> index.html
git add . && git commit -m "v2" && git push
# no manual step — Source -> Build -> Deploy runs on its own
```

## Cost

| Resource | Driver | Approx. cost |
|---|---|---|
| EC2 `t3.micro` | Hourly while running | Free Tier: $0 (750 hrs/mo, 12 mo). Off Free Tier: ~$0.0104/hr (~$0.50 for 2 days, ~$7.50/mo if left running) |
| CodePipeline (V1) | $1.00 per *active* pipeline/month (existed > 30 days **and** had a code change that month), not prorated | **$0 for the first 30 days after creation**; one free active V1 pipeline/month |
| CodeBuild | Per build-minute | ~$0.005/min × ~1 min/build → pennies/month for occasional pushes. First 100 min/mo free for 12 mo |
| CodeDeploy (EC2/On-Prem) | — | **Always $0** — only the underlying EC2 instance costs anything |
| CodeCommit | — | $0 at this scale (free tier: 5 users, 10GB, 10k API calls/mo) |
| S3 (2 buckets) | Storage + requests | ~$0 — a few KB of zipped source |

**2-day test, account past Free Tier: roughly $0.50**, almost all of it the
EC2 instance (~$0.0104/hr). Per AWS's pricing page a V1 pipeline is free for
its first 30 days, so the CodePipeline charge only appears if you keep the
pipeline past 30 days and push code through it. Prices are as read from AWS's
pricing page on 2026-09-20 — check your own bill (Cost Explorer lags ~24h, so it
can't confirm anything on day one). See `LEARNINGS.md` §9 and
`../004_cicd_pipeline_v2_ec2/` for V2 pricing.

## Things to try (mini-labs)

1. Push a change and watch each stage individually in the console
   (CodePipeline → your pipeline) — note the timestamp each stage
   started vs. finished; Build usually takes longer than Deploy for
   this trivial app.
2. Break `appspec-sample/buildspec.yml` (e.g. add a command that
   `exit 1`s) and push — watch the pipeline stop at Build and never
   reach Deploy. Fix it and push again; note you do NOT need to
   `terraform apply` anything to fix an app-level bug, only a `git push`.
3. Break `appspec-sample/scripts/validate_service.sh` (e.g. `curl` a
   path that 404s) and push — with `auto_rollback_configuration.enabled
   = true` in `codedeploy.tf`, watch CodeDeploy detect the failed hook
   and roll back automatically instead of leaving the instance broken.
4. Switch `PollForSourceChanges` to `"false"` in `codepipeline.tf` and
   add the EventBridge push-trigger (see `STEP_BY_STEP.md` Step 6, or
   the fully-built version in `cloud-practice/aws/terraform/codepipeline/main.tf`)
   — compare push-to-pipeline-start latency (seconds vs. up to a minute).

## Troubleshooting

1. **Pipeline stuck at Source** → repo is empty (you haven't done the
   "First push" above yet), or the pipeline role's CodeCommit
   permissions are wrong. `aws codecommit get-branch --repository-name
   <name> --branch-name main`.
2. **Pipeline stuck/failed at Build** → `aws logs tail
   /aws/codebuild/<project> --follow` — the buildspec's own error is
   almost always there.
3. **Pipeline stuck/failed at Deploy** → `aws deploy get-deployment
   --deployment-id <id>`, then check
   `/var/log/aws/codedeploy-agent/codedeploy-agent.log` on the instance
   over SSM (`aws ssm start-session --target <instance_id>`) — a failed
   `appspec.yml` lifecycle hook's actual error shows up there, not in
   the pipeline console.
4. **"No instances found for deployment"** → the deployment group's tag
   filter (`codedeploy.tf`'s `ec2_tag_set`) doesn't match the instance's
   actual `Name` tag, or the CodeDeploy agent isn't running yet
   (`sudo systemctl status codedeploy-agent` over SSM — it can take a
   minute after instance launch to finish installing).

## Deliberately minimal

- Single EC2 instance, no load balancer, `AllAtOnce` deployment — fine
  for one instance, meaningless once there's more than one (see
  `cloud-practice/aws/terraform/autoscaling/` + `alb/` for the
  multi-instance version).
- `PollForSourceChanges = "true"` (up to ~1 minute delay) instead of
  push-triggered — see mini-lab 4.
- CodeDeploy's IAM statement in `codepipeline.tf` uses `Resource = "*"`
  — a good follow-up exercise to scope down once the pipeline works
  end to end.
