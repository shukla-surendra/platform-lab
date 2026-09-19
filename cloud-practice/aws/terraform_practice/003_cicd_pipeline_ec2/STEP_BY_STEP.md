# How this pipeline is built, stage by stage

The `.tf` files in this folder are **fully implemented** — a single
`terraform apply` creates all 20 resources across every file in one
shot (see `README.md` for that "just run it" path). This doc instead
walks through *why* each file exists, **in the order it was designed
and would be tested if you built it incrementally** — each "test"
below still works today, running it just verifies one piece in
isolation rather than gating whether you're allowed to write the next
file. Deleting one file at a time and rewriting it from these
explanations (checking yourself against the real file) is the best way
to actually learn the wiring instead of just reading it.

A fully-working, non-scaffolded reference for each individual piece
also exists at `cloud-practice/aws/terraform/ec2/`, `codecommit/`,
`codebuild/`, `codedeploy/`, and `codepipeline/`, if you want to compare
a leaner single-purpose version of each against this all-in-one one.

## Architecture

```
You: git push
   │
   ▼
CodeCommit (repo)  ──polled ~1x/min──▶  CodePipeline starts
                                             │
                           ┌─────────────────┼─────────────────┐
                           ▼                 ▼                 ▼
                    Source stage       Build stage       Deploy stage
                    (pulls the repo)   (CodeBuild:       (CodeDeploy:
                                        runs buildspec,   copies files to
                                        produces an       the EC2 instance,
                                        artifact zip)     runs appspec.yml
                                                          lifecycle hooks)
                                                               │
                                                               ▼
                                                        EC2 instance
                                                        (tagged so CodeDeploy
                                                         knows to target it)
```
(Polling, not an EventBridge push-trigger, is what's actually
implemented — see Step 6 for the push-triggered upgrade.)

Six moving pieces, in the order they were designed and would be tested:
1. **EC2 instance** — the deploy target. Needs the CodeDeploy agent
   running and a tag CodeDeploy can find it by.
2. **CodeCommit** — the source repo.
3. **CodeDeploy** (application + deployment group) — knows HOW to deploy
   (which instance, which lifecycle hooks) but doesn't trigger itself.
4. **CodeBuild** — turns source into a build artifact.
5. **CodePipeline** — wires 2→4→3 together and reacts to pushes.
6. **A sample app** (`appspec-sample/`, already written for you — this
   isn't the Terraform-learning part) that CodeDeploy actually deploys.

## Step 0 — before touching Terraform

```bash
cd 003_cicd_pipeline_ec2
cp terraform.tfvars.example terraform.tfvars   # edit region/project/CIDRs
terraform init
```

## Step 1 — `ec2.tf`: get a target instance up FIRST, test it alone

`ec2.tf` creates: a security group (SSH from your IP, HTTP open — no
other inbound port needed, CodeDeploy talks to the instance via its
agent, not a listening port), an IAM role + instance profile (needs
`AmazonSSMManagedInstanceCore` so you can shell in without a key pair —
see `002_ec2_instace_creation_pem/` for why a `.pem` isn't the only way
in), and the instance itself with `user_data` that installs `httpd` and
the CodeDeploy agent.

**Test this piece in isolation** (if you already ran the one-shot
`terraform apply` from `README.md`, skip the `-target` and just run the
`ssm`/`systemctl` lines against your real `instance_id` output):
```bash
terraform apply -target=aws_instance.target -target=aws_iam_instance_profile.target
aws ssm start-session --target <instance_id from output>
sudo systemctl status codedeploy-agent    # should be "active (running)"
```
If the agent isn't running, CodeDeploy will fail with "no instances found
for deployment" later, and you'll have no idea why — confirm this now
while it's the only thing that could be wrong.

## Step 2 — `codecommit.tf`: the source repo

One resource: `terraform apply -target=aws_codecommit_repository.app`
(or the full apply — either way, push something into it. An empty repo
will make Step 5's pipeline fail on its very first run):
```bash
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
git clone <clone_url_http output>
cd <repo-name>
cp -r ../appspec-sample/* .
git add . && git commit -m "initial" && git push
cd ..
```

## Step 3 — `codedeploy.tf`: teach AWS how to deploy onto your instance

`codedeploy.tf` creates: an IAM role (with the AWS-managed
`AWSCodeDeployRole` policy attached — no need to write that permission
set by hand), an `aws_codedeploy_app`, and a
`aws_codedeploy_deployment_group` that targets the Step 1 instance **by
its `Name` tag**, not by instance ID (deployment groups target
tags/ASGs, never a specific instance ID — that's what lets you swap the
instance later without touching this resource).

**Test this piece in isolation — deploy BY HAND, no pipeline yet:**
```bash
terraform apply -target=aws_codedeploy_deployment_group.app
cd <repo-name> && zip -r ../revision.zip . && cd ..
aws s3 mb s3://<your-name>-cicd-practice-revisions   # any throwaway bucket you own — NOT one this Terraform manages
aws s3 cp revision.zip s3://<that-bucket>/revision.zip
aws deploy create-deployment \
  --application-name <from output> \
  --deployment-group-name <from output> \
  --s3-location bucket=<that-bucket>,key=revision.zip,bundleType=zip
aws deploy get-deployment --deployment-id <id from above>   # watch it reach Succeeded
curl http://<instance public ip>/                            # see the sample app's page
```
Getting a manual deployment green BEFORE wiring CodePipeline means that
if the pipeline fails later, you already know CodeDeploy itself isn't
the problem — you've narrowed the search space by one entire stage.

## Step 4 — `codebuild.tf`: turn source into a build artifact

`codebuild.tf` creates its own S3 bucket for build output — separate
from the throwaway bucket you just used for the manual deployment
above, and separate again from Step 5's pipeline artifact bucket. Three
buckets, three distinct jobs (manual deployment input, CodeBuild output,
inter-stage pipeline artifacts) — keeping them distinct is what makes
Step 5's wiring click into place instead of feeling arbitrary. Also
created here: an IAM role (logs + S3 + the CodeCommit git-pull
permission), and the
`aws_codebuild_project` itself, pointed at the Step 2 repo with
`source_type = "CODECOMMIT"` and no inline `buildspec` — it reads
`buildspec.yml` from the repo root, which you pushed in Step 2.

**Test this piece in isolation:**
```bash
terraform apply -target=aws_codebuild_project.app
aws codebuild start-build --project-name <from output>
aws logs tail /aws/codebuild/<project-name> --follow   # watch it succeed
```

## Step 5 — `codepipeline.tf`: wire it all together

This is the actual point of the exercise — everything before this file
was setup. `codepipeline.tf` creates its own S3 artifact bucket, an IAM
role (statements for S3, `codebuild:StartBuild`,
`codedeploy:CreateDeployment`, and CodeCommit — read each `Sid` in the
policy and confirm it maps to exactly one thing CodePipeline calls,
nothing more), and the `aws_codepipeline` resource itself with three
`stage` blocks:

- **Source**: `provider = "CodeCommit"`, references Step 2's repo.
  `output_artifacts = ["source_output"]`.
- **Build**: `provider = "CodeBuild"`, references Step 4's project.
  `input_artifacts = ["source_output"]`, `output_artifacts =
  ["build_output"]` — the names MUST match between stages; this is how
  one stage's output becomes the next stage's input.
- **Deploy**: `provider = "CodeDeploy"`, references Step 3's app +
  deployment group. `input_artifacts = ["build_output"]`.

**Test — the real end-to-end run:**
```bash
terraform apply
aws codepipeline get-pipeline-state --name <from output>
# then push a real change:
cd <repo-name>
echo "<p>v2</p>" >> index.html
git add . && git commit -m "v2" && git push
# watch it happen with zero manual steps:
watch aws codepipeline get-pipeline-state --name <from output>
curl http://<instance public ip>/    # see v2 show up, untouched by hand
```

## Step 6 (optional) — push-triggered instead of polling

By default `PollForSourceChanges` (if you left it `true`) means
CodePipeline checks for new commits roughly once a minute. For a push to
trigger it immediately instead, add an `aws_cloudwatch_event_rule`
matching CodeCommit's `referenceUpdated` event + an
`aws_cloudwatch_event_target` pointed at the pipeline's ARN — the
working version of this exact wiring is in
`cloud-practice/aws/terraform/codepipeline/main.tf` if you want to see
it after attempting it yourself.

## When something fails

See `README.md`'s "Troubleshooting" section — kept in one place rather
than duplicated here.
