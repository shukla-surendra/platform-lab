# CodeBuild and CodeDeploy — practical use cases

A working reference for *what these two services are actually good for*, beyond the one
pipeline we built. Companion to [`JOURNEY.md`](JOURNEY.md) and
[`003_cicd_pipeline_ec2/LEARNINGS.md`](003_cicd_pipeline_ec2/LEARNINGS.md).

**How to read the labels**

- ✅ **Built and run here** — observed working against real AWS on 2026-09-20 (V2 module,
  `004_cicd_pipeline_v2_ec2/`).
- 📘 **Reference pattern** — standard usage, written from general knowledge, **not run in
  this repo**. Snippets are starting points; test before relying on them. Placeholders
  like `<account-id>` and `<region>` are yours to fill in.

---

## 1. The one-paragraph mental model

| | **CodeBuild** | **CodeDeploy** |
|---|---|---|
| Job | Runs **a script in a clean, disposable container**, then throws it away | **Puts a built artifact onto running compute** and manages the rollout |
| Input | Source (zip/repo) + a `buildspec.yml` | A revision (zip/image/Lambda version) + an `appspec.yml` |
| Output | Files (artifacts), images, reports, logs, exit code | A finished, validated deployment — or an automatic rollback |
| Knows about your servers? | No — it's just a container | Yes — instances, ASGs, ECS services, Lambda aliases |
| Billing shape | Per build-minute × compute size | See §5 — not verified |

Rule of thumb: **CodeBuild = "run this command somewhere clean." CodeDeploy = "roll this
onto those targets safely."** They're independent — CodeBuild is useful with no CodeDeploy at
all, and the reverse.

---

## 2. CodeBuild use cases

CodeBuild is best understood as a **serverless job runner** that happens to be great at CI.
Anything that's "run commands, with an IAM role, pay per minute" fits.

### 2.1 Build and test an application ✅
The classic. `buildspec.yml` phases: `install` → `pre_build` → `build` → `post_build`,
then `artifacts:` says what to keep.

**What we ran:** a deliberately trivial build (stamp a timestamp and a run-time variable
into `index.html`) whose `artifacts: files: '**/*'` fed CodeDeploy — see
`004_cicd_pipeline_v2_ec2/app-sample/buildspec.yml`.

Real-world version 📘:

```yaml
version: 0.2
env:
  variables:
    NODE_ENV: test
phases:
  install:
    runtime-versions:
      nodejs: 20                   # pick a version your build image actually supports
    commands:
      - npm ci
  pre_build:
    commands:
      - npm run lint
  build:
    commands:
      - npm test -- --reporters=default --reporters=jest-junit
      - npm run build
reports:
  unit-tests:
    files: ['junit.xml']
    file-format: JUNITXML          # shows up as a Test Report in the console
artifacts:
  base-directory: dist
  files: ['**/*']
cache:
  paths: ['node_modules/**/*']     # needs a cache configured on the project
```

Why it's practical: a fresh container per build means "works on my machine" bugs show up
immediately; failing tests fail the build, which stops the pipeline before Deploy.

### 2.2 Build a Docker image and push to ECR 📘
The most common CodeBuild job in container shops. The project needs
`privileged_mode = true` in its `environment` block (Docker-in-Docker), and the role needs
ECR push permissions.

```yaml
version: 0.2
env:
  variables:
    IMAGE_REPO: my-app
    AWS_ACCOUNT_ID: "<account-id>"        # not provided by CodeBuild — define it
phases:
  pre_build:
    commands:
      - REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
      - aws ecr get-login-password | docker login --username AWS --password-stdin $REGISTRY
      - TAG=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c1-7)   # short commit SHA
  build:
    commands:
      - docker build -t $REGISTRY/$IMAGE_REPO:$TAG .
  post_build:
    commands:
      - docker push $REGISTRY/$IMAGE_REPO:$TAG
      - printf '{"ImageURI":"%s"}' $REGISTRY/$IMAGE_REPO:$TAG > imageDetail.json
artifacts:
  files: [imageDetail.json]
```

Tag with the commit SHA, not `latest` — every deployed image is then traceable to a commit
and rollbacks are exact.

### 2.3 Run Terraform (an *infrastructure* pipeline) 📘
This is the concrete answer to the "keep infra and app deployment separate" question from
the session: **infra can be automated too — through its own pipeline and role**, not the app's.

Two-stage shape: a **plan** build → a manual **Approval** stage → an **apply** build.
Approval is the stage we built and tested (✅ the Approval mechanics, 📘 the Terraform part).

```yaml
# buildspec-plan.yml
version: 0.2
env:
  variables:
    TF_VERSION: "<pin a version>"
phases:
  install:
    commands:
      - curl -sSLo /tmp/tf.zip https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip
      - unzip -o /tmp/tf.zip -d /usr/local/bin
  build:
    commands:
      - terraform init -input=false
      - terraform plan -input=false -out=tfplan
artifacts:
  files: ['tfplan', '**/*.tf', '.terraform.lock.hcl']
```

The apply build runs `terraform apply -input=false tfplan` against **exactly the plan a
human approved** — that's the point of splitting them. Practical cautions:
- The build role needs broad permissions; scope it to the resources in that module, and keep
  it separate from any app pipeline's role.
- State must be remote with locking (we used S3 + `use_lockfile`), or two runs can collide.
- Pin the Terraform version — a floating one makes "the plan I approved" and "the apply I ran"
  potentially different tools.
- The plan file contains secrets in plaintext if your resources do; treat the artifact bucket
  accordingly.

### 2.4 Static website: build, sync to S3, invalidate CDN 📘
```yaml
phases:
  build:
    commands:
      - npm ci && npm run build
  post_build:
    commands:
      - aws s3 sync dist/ s3://<site-bucket>/ --delete
      - aws cloudfront create-invalidation --distribution-id <dist-id> --paths '/*'
```
No CodeDeploy needed — the "deployment" is the `s3 sync`. A good example of CodeBuild doing
the deploy itself when the target is a bucket.

### 2.5 Package serverless code 📘
Build Lambda zips or layers (or `sam build`) with the *right* OS and architecture — dependencies
with native code must be built for Lambda's runtime, which your laptop often isn't.
Pairs with CodeDeploy's Lambda traffic shifting (§3.4).

### 2.6 Pull-request validation 📘
Trigger a build per PR (webhook for GitHub, EventBridge for CodeCommit), run lint + tests +
`terraform validate`/`plan`, report pass/fail back on the PR. Cheap because it's
pay-per-minute and idle when nobody's pushing.

### 2.7 Security and quality gates 📘
Run scanners as build steps — dependency audit, container image scan, IaC scanning
(`checkov`, `tfsec`), secret detection — and let a non-zero exit code fail the build. Cheap
place to enforce policy because every change already passes through it.

### 2.8 Scheduled or on-demand jobs (not CI at all) 📘
Because it's just "a container with an IAM role and a timeout," CodeBuild runs
one-off work: database migrations, report generation, data backfills, cleanup scripts,
nightly exports. Trigger from EventBridge Scheduler or `aws codebuild start-build`.
Long timeouts are supported (check the current maximum), which Lambda can't match.

> **Trade-off we hit:** our V2 project used `CODEPIPELINE` source/artifacts, which means
> `aws codebuild start-build` **doesn't work standalone** on it. For job-runner use,
> configure the project with a real source (or none) instead.

### 2.9 Build inside your VPC 📘
Give the project a VPC config so a build can reach **private** resources — run integration
tests against a private database, hit an internal API, pull from a private package repo.
Needs subnets with NAT (or endpoints) for outbound access to AWS services.

### 2.10 Secrets and configuration in builds 📘
Never bake secrets into the buildspec or repo. Pull them at build time:

```yaml
env:
  parameter-store:
    DB_URL: /my-app/test/db_url
  secrets-manager:
    API_KEY: my-app/test:api_key       # secret-id:json-key
```

Also ✅ pipeline-level **variables**: in V2 we passed a `DEPLOY_NOTE` from a run-time variable
into CodeBuild's `EnvironmentVariables`, and it appeared in the deployed page.

### CodeBuild practical notes (things we hit, and standard ones)

- ✅ **A log group must exist** (or the role must be able to create it) — otherwise the build
  fails at `QUEUED`. We create it in Terraform.
- ✅ **Behind CodePipeline, source and output travel through the pipeline's artifact
  bucket** — the CodeBuild role needs access to *that* bucket, not just its own.
- ✅ The buildspec defaults to `buildspec.yml` at the **root of the source**; override with the
  project's `buildspec` argument.
- ✅ `artifacts:` decides what the next stage receives. Too narrow → downstream stages are
  missing files (e.g. `appspec.yml`).
- 📘 Compute size sets both speed and price; start with the smallest and only size up if builds
  are slow. Caching (`cache:`) is usually the bigger win than a larger instance.
- 📘 Builds are ephemeral: anything not in `artifacts:` or pushed somewhere is gone.

---

## 3. CodeDeploy use cases

CodeDeploy answers: **"how do I release safely to things that are already running?"** It has
three compute platforms, each with its own deployment styles.

### 3.1 In-place deployment to EC2 ✅
What we built. The **CodeDeploy agent** on each instance pulls the revision from S3 and runs
the `appspec.yml` lifecycle hooks; the deployment group finds instances **by tag**.

```yaml
version: 0.0
os: linux
files:
  - source: /index.html
    destination: /var/www/html
hooks:
  BeforeInstall:    [{ location: scripts/stop_server.sh,      timeout: 30 }]
  AfterInstall:     [{ location: scripts/set_permissions.sh,  timeout: 30 }]
  ApplicationStart: [{ location: scripts/start_server.sh,     timeout: 30 }]
  ValidateService:  [{ location: scripts/validate_service.sh, timeout: 30 }]
```

EC2 hook order: `ApplicationStop → DownloadBundle → BeforeInstall → Install → AfterInstall →
ApplicationStart → ValidateService` (plus `BeforeBlockTraffic`/`AfterBlockTraffic`/
`BeforeAllowTraffic`/`AfterAllowTraffic` when behind a load balancer).

**`ValidateService` is the important one** — a script that fails (e.g. `curl -f` the health
endpoint) marks the deployment failed and triggers rollback. Ours was one line:
`curl -sf http://localhost/ >/dev/null`.

Things that broke or nearly broke for us:
- ✅ **The instance role needs read access to the revision bucket** (the agent downloads from
  S3 with the instance's credentials) — the pipeline's artifact bucket, in our case.
- ✅ **Hook scripts must be executable** in git (`100755`).
- ✅ **The tag on the instance must match the deployment group's filter**, or you get "no
  instances found for deployment".
- ✅ **The agent must be installed and running** (we installed it via user data).
- ✅ Auto-rollback on `DEPLOYMENT_FAILURE` was configured, not exercised.

### 3.2 Rolling deployment behind a load balancer (zero-downtime) 📘
For a fleet, don't update everything at once. Deployment configurations control the pace:
`CodeDeployDefault.OneAtATime`, `HalfAtATime`, `AllAtOnce` (or a custom min-healthy-hosts).
With an ALB/target group attached, CodeDeploy **deregisters each instance, updates it,
health-checks it, and re-registers it** — users never hit a half-updated box.
We used `AllAtOnce` because one instance makes the choice moot.

### 3.3 Blue/green for EC2 (Auto Scaling group) 📘
CodeDeploy launches a **new** ASG (copy of the current one) with the new revision, shifts
the load balancer to it, then terminates the old one after a wait. Rollback = shift traffic
back. Trades extra capacity for a clean, fast rollback and no in-place mutation.

### 3.4 Lambda: canary and linear traffic shifting 📘
Publish a new function version, then shift an **alias** gradually. Configs like
`CodeDeployDefault.LambdaCanary10Percent5Minutes` or `LambdaLinear10PercentEvery1Minute`.
Pre/post-traffic hook Lambdas run smoke tests; **CloudWatch alarms** can abort and roll back
automatically. Common through SAM's `DeploymentPreference`.

```yaml
version: 0.0
Resources:
  - MyFunction:
      Type: AWS::Lambda::Function
      Properties:
        Name: my-function
        Alias: live
        CurrentVersion: "1"
        TargetVersion: "2"
Hooks:
  - BeforeAllowTraffic: pre-traffic-check-fn
  - AfterAllowTraffic: post-traffic-check-fn
```

### 3.5 ECS: blue/green with an ALB 📘
Stand up the new task set beside the old, shift the listener in canary/linear steps
(`CodeDeployDefault.ECSCanary10Percent5Minutes`, `ECSLinear10PercentEvery1Minutes`,
`ECSAllAtOnce`), test on a separate test listener before any prod traffic, roll back by
shifting back. Hooks here are Lambda functions.

```yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: "arn:aws:ecs:<region>:<account-id>:task-definition/my-task:3"
        LoadBalancerInfo:
          ContainerName: "app"
          ContainerPort: 8080
```

### 3.6 Automatic rollback on alarms 📘
Beyond "the deployment script failed," tie the deployment group to **CloudWatch alarms**
(5xx rate, latency, error count). If an alarm fires mid-rollout, CodeDeploy stops and rolls
back without a human. Configured on the deployment group's alarm/rollback settings.
Ours only rolled back on outright failure.

### 3.7 On-premises and hybrid servers 📘
Register non-EC2 machines with the same agent and target them by tag. Useful when part of a
fleet lives in a data centre and you want one deployment tool for both.

### 3.8 Distributing config or agents, not just apps 📘
Anything that's "get these files onto these servers, then run these commands, and verify":
config bundles, monitoring agents, certificate rollouts, OS-level patches for long-lived hosts.

### When *not* to reach for CodeDeploy
In-place EC2 deployment suits **long-lived servers** ("pets"). If you can, containers
(ECS/EKS) or immutable AMIs with instance refresh remove most of the need for in-place
mutation. Reach for CodeDeploy when you specifically need managed traffic shifting, hooks
and rollback on EC2/Lambda/ECS.

---

## 4. Putting them together — four shapes that recur

| Pattern | Flow | Status |
|---|---|---|
| **Classic EC2** | CodeCommit → CodeBuild (build/test → zip) → *Approval* → CodeDeploy (in-place) → EC2 | ✅ built end to end |
| **Containers** | Repo → CodeBuild (build image → ECR) → CodeDeploy ECS blue/green | 📘 |
| **Serverless** | Repo → CodeBuild (`sam build`, package) → CodeDeploy Lambda canary + alarms | 📘 |
| **Infrastructure** | Repo → CodeBuild `terraform plan` → *Approval* → CodeBuild `terraform apply` (no CodeDeploy) | 📘 (Approval ✅) |

Two things worth noticing:
1. **CodeDeploy is optional.** The static-site and Terraform patterns deploy from inside
   CodeBuild. Use CodeDeploy when the *rollout strategy* (traffic shifting, health gating,
   rollback) is the hard part.
2. **The `artifacts:` block and the `appspec.yml` are the contract between the two.**
   CodeBuild decides what's in the revision; CodeDeploy expects `appspec.yml` at its root.
   Get that wrong and Deploy fails with "appspec missing," not a build error.

---

## 5. Cost

- **CodeBuild:** billed per build-minute, by compute type. Our `BUILD_GENERAL1_SMALL` builds
  ran about a minute each; we didn't measure exact spend. Free-tier terms exist — check the
  pricing page.
- **CodeDeploy:** **not verified.** Fetching AWS's CodeDeploy pricing page returned no rates.
  The original `003` README asserted "EC2/On-Prem is always $0" — that claim was never
  verified either. Check the pricing page or the Pricing Calculator before relying on it,
  especially for on-premises instances.
- **The dominant cost in our experiment was the EC2 instance**, not either service
  (~$0.02 over about 2 hours; see `JOURNEY.md`).

---

## 6. Choosing quickly

| I want to… | Use |
|---|---|
| Compile/test on every push | CodeBuild |
| Build and publish a container image | CodeBuild (+ ECR) |
| Run a script on a schedule with an IAM role | CodeBuild |
| Run Terraform in CI with a human gate | CodeBuild ×2 + Approval |
| Release to a fleet without downtime | CodeDeploy (rolling / blue-green) |
| Canary a Lambda or ECS service with auto-rollback | CodeDeploy |
| Just copy static files to S3 | CodeBuild alone (`s3 sync`) — CodeDeploy not needed |
| Ship to one dev box, don't care about rollback | Either, or skip both — a script over SSM may be enough |
