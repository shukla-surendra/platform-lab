# Terraform workspaces, from zero — with one Lambda

Two small lessons. Each deploys **one Lambda** (+ its IAM role) to your AWS account.
Lesson 1 teaches what a workspace *is*. Lesson 2 shows how a **production release** works.

> Nothing here has been applied for you. The "you should see" blocks are what
> Terraform normally prints; your IDs/ARNs will differ. Cost is ~$0 (an idle Lambda is free).
> Both lessons use *local* state to keep it simple; real teams use an S3 backend
> (see `../multi-env-workspaces`).

**Lessons:** `01-one-lambda` (what a workspace is) → `02-release-flow` (production release) →
`03-ec2` (EC2, local state) → `04-ec2-s3-backend` (S3 backend).
**Reference:** [`CONCEPTS.md`](CONCEPTS.md): backend paths, where workspace info lives, what goes in git.

---------------------------------------------------------------------------

## The one idea

```
Terraform = CODE  +  STATE
              |         |
         what you want  what Terraform believes exists
```

A **workspace is just a separate STATE file for the same code.** That's all.

```
        same main.tf
       /     |      \
 workspace  workspace  workspace
   dev        qa        prod
     |         |          |
  state-A   state-B    state-C     <- three independent notebooks
     |         |          |
  lambda-dev lambda-qa  lambda-prod   <- three independent real Lambdas
```

`terraform apply` in workspace `dev` only reads/writes state-A, so it can never touch prod's Lambda.
Inside the code, `terraform.workspace` holds the current name, which you use to name things.

---------------------------------------------------------------------------

## Lesson 1 — `01-one-lambda/`  (workspace = separate state)

```bash
cd 01-one-lambda
terraform init
terraform workspace list          # * default
terraform workspace new dev       # creates + switches
terraform apply                   # type yes
```
You should see: `Apply complete! 3 added...` and `function_name = "wsdemo-dev-hello"`.

Now the key moment — create a second environment from the SAME code:
```bash
terraform workspace new prod
terraform plan
```
You should see **`Plan: 3 to add`** (role, policy attachment, function), *not* "no changes".
Prod's state is empty, so Terraform plans to build everything. Dev's Lambda is untouched.
```bash
terraform apply
aws lambda list-functions --query "Functions[?starts_with(FunctionName,'wsdemo-')].FunctionName"
```
You should see both `wsdemo-dev-hello` and `wsdemo-prod-hello`.

Look at the state files (this is the "separate notebook" idea made visible):
```bash
ls terraform.tfstate.d/           # dev  prod
terraform workspace show          # prod
terraform workspace select dev
terraform state list              # dev's resources only
```

Invoke each one:
```bash
aws lambda invoke --function-name wsdemo-dev-hello  /dev/stdout
aws lambda invoke --function-name wsdemo-prod-hello /dev/stdout
```
→ `"hello from dev"` / `"hello from prod"`.

**Try to break it:** `terraform workspace select dev && terraform destroy` removes only the dev Lambda.
**Clean up:** destroy in *each* workspace (`select prod && destroy`, `select dev && destroy`).
A workspace with live resources can't be deleted; `terraform workspace delete` after destroying.

What lesson 1 does NOT answer: dev and prod are identical except for the name.
Real prod needs different memory, log level, version… and a controlled way to release.

---------------------------------------------------------------------------

## Lesson 2 — `02-release-flow/`  (how a production release works)

Adds three things on top of lesson 1:

1. **`vars/<env>.tfvars`**: per-env settings (memory, log level, `app_version`).
2. **Lambda versions + alias `live`**: each code change publishes an immutable version;
   `live` points at the version that is "released".
3. **A `check` block**: errors if the workspace and tfvars file don't match.

### The golden rule

> **A workspace picks the STATE. A tfvars file picks the SETTINGS. You must pass both, and they must match.**

```bash
terraform workspace select dev  &&  terraform apply -var-file=vars/dev.tfvars
terraform workspace select prod &&  terraform apply -var-file=vars/prod.tfvars
```
(Makefile equivalent below.) Wrong combo? e.g. workspace `prod` + `vars/dev.tfvars` →
the `check` block warns `Workspace 'prod' but tfvars says 'dev'`. Try it with `plan`.

### Do it once

```bash
cd ../02-release-flow
terraform init
for e in dev qa prod; do
  terraform workspace select $e || terraform workspace new $e
  terraform apply -auto-approve -var-file=vars/$e.tfvars
done
```
Check the differences (same code, different settings):
```bash
aws lambda get-function-configuration --function-name wsdemo2-dev-hello  --query '[MemorySize,Environment.Variables]'
aws lambda get-function-configuration --function-name wsdemo2-prod-hello --query '[MemorySize,Environment.Variables]'
```
dev: 128 MB, `LOG_LEVEL=DEBUG`, version 1.1.0 · prod: 512 MB, `WARN`, version 1.0.0.

### "Release to production" — what actually happens

There is no special "release" command in Terraform. A release is **a reviewed change that
finally gets applied in the prod workspace**. Typical flow:

```
 1. Edit code (src/handler.py) / settings on a branch
 2. PR  ──► pipeline runs `plan` for dev/qa/prod, reviewers read the plan
 3. Merge to main
 4. Pipeline applies  dev  (workspace dev,  vars/dev.tfvars)   ← automatic
 5. Pipeline applies  qa   (workspace qa,   vars/qa.tfvars)    ← automatic, tests run
 6. Pipeline PAUSES for human approval
 7. Pipeline applies  prod (workspace prod, vars/prod.tfvars)  ← the "release"
 8. Tag the commit (v1.1.0) so you know what prod runs
```
Prod is "released" when its tfvars/code says so. Hands-on version:

**Step A — change the code** (edit `src/handler.py`, e.g. add `"deployed": True` to the return dict),
then deploy to dev only:
```bash
terraform workspace select dev
terraform plan -var-file=vars/dev.tfvars     # shows: function updated, new version, alias moves
terraform apply -var-file=vars/dev.tfvars
```
Prod is **unaffected** — verify: `select prod && plan -var-file=vars/prod.tfvars` still says
it would update code too (same `src/`!). This is an important gotcha:

> Workspaces share ONE copy of the code. The moment you merge new code to main, *every*
> workspace's next plan shows that change. Prod doesn't change until someone **applies** in prod,
> which the pipeline holds behind an approval. So the code in Git is "latest", and each env's
> state tells you what is actually deployed.

**Step B — release to prod:** save a plan, have it reviewed, then apply exactly that plan:
```bash
terraform workspace select prod
terraform plan  -var-file=vars/prod.tfvars -out=tfplan   # reviewer reads this
terraform apply tfplan                                   # applies exactly what was reviewed
aws lambda get-alias --function-name wsdemo2-prod-hello --name live   # FunctionVersion moved to 2
```

**Step C — rollback:** `git revert` the change (or `git checkout v1.0.0 -- src`), re-run
the prod apply: the alias moves back. For an instant rollback you can also point the alias at
the previous version number in the console, then fix Terraform afterwards.

### Makefile you'd use day to day
```make
ENV ?= dev
plan:  ; terraform workspace select $(ENV) && terraform plan  -var-file=vars/$(ENV).tfvars -out=tfplan
apply: ; terraform apply tfplan
```

### Why many teams eventually prefer folders for prod
Because of the gotcha above: with workspaces, dev and prod share the *same* code at all times,
so you can't run "new code in dev, old code in prod" for days, you'd have to hold back the merge.
With folders + versioned modules, prod can pin `module v1.0.0` while dev uses `v1.1.0`.
Workspaces are great when "same code everywhere, promote by applying in order" is acceptable.

### Clean up
```bash
for e in dev qa prod; do terraform workspace select $e && terraform destroy -auto-approve -var-file=vars/$e.tfvars; done
```
