# The journey: CI/CD pipeline to EC2 with Terraform

One session, 2026-09-20. Took a finished-looking Terraform module for a CodePipeline →
EC2 deployment, actually ran it, found out it didn't work, fixed it, rebuilt it as a V2
pipeline, poked at what V2 can and can't do, started on HTTPS, then tore everything down.

This is the narrative. The detailed V1 lessons are in
[`003_cicd_pipeline_ec2/LEARNINGS.md`](003_cicd_pipeline_ec2/LEARNINGS.md); the working V2
code is in [`004_cicd_pipeline_v2_ec2/`](004_cicd_pipeline_v2_ec2/). For what CodeBuild and
CodeDeploy are good for beyond this one pipeline, see
[`CODEBUILD_CODEDEPLOY_USECASES.md`](CODEBUILD_CODEDEPLOY_USECASES.md). Everything below was
observed against real AWS unless marked **(not tested)** or **(inferred)**.

## TL;DR

| Module | What | Outcome |
|---|---|---|
| `000_bootstrap_state_bucket` | S3 bucket for remote Terraform state | built, used, **destroyed** |
| `003_cicd_pipeline_ec2` | V1 pipeline: CodeCommit → CodeBuild → (Approval) → CodeDeploy → EC2 | ran end to end after 2 bug fixes, **destroyed** |
| `004_cicd_pipeline_v2_ec2` | V2 pipeline, same flow, fixes built in, run-time variables, push trigger | verified end to end, **destroyed** |
| HTTPS on the site | TLS certificate on the raw public IP | investigated and trialed; **not implemented** |

Total AWS spend for the session: well under a dollar. The two `t3.micro` instances ran
**77 min (V1) + 47 min (V2) ≈ 2 hours** (launch/terminate times read from EC2; the two
overlapped for ~20 min) ≈ **$0.02** at on-demand rates, plus a handful of sub-cent CodeBuild
runs. *(Computed from run times, not from the bill — Cost Explorer lags about a day, and
the CodePipeline charge question in §5 was never settled by data.)*

Nothing is left running. Verified afterwards with explicit counts: 0 buckets, pipelines,
repos, CodeBuild projects, CodeDeploy apps, IAM roles, EventBridge rules, log groups,
security groups, instances or Elastic IPs matching this work.

## Timeline

### 1. "Deploy this" — plus a remote-state bucket

The module was 20 resources across EC2, CodeCommit, CodeBuild, CodeDeploy and CodePipeline,
with a README claiming it was "verified against real AWS (`terraform plan`: 20 resources,
0 errors)".

- Built `000_bootstrap_state_bucket` (local state; versioned, encrypted, private, TLS-only,
  `prevent_destroy`) and pointed `003` at it with an `s3` backend and native locking
  (`use_lockfile`, Terraform ≥ 1.10). Bucket name uses a random suffix, not the account
  ID, because the repo is on GitHub.
- `terraform apply`: **18 of 20 created, then `AccessDeniedException`** on CodeBuild and
  CodeDeploy. The CLI user had no permissions for CodePipeline's three services. `plan`
  had passed because plan doesn't check IAM.
- The first diagnosis was incomplete — I looked at the user's attached policies but not
  its group's. Corrected by asking AWS's policy simulator (`implicitDeny`), which agreed with
  the error. The user then granted admin, and `apply` resumed and created the last 5.

### 2. Conceptual detour: infra code vs app code

Clarified that there are two kinds of code with two lifecycles: the `.tf` files (infra,
applied by hand, never seen by the pipeline) and `appspec-sample/` (app code, pushed to the
**CodeCommit** repo, the only thing the pipeline watches). The GitHub repo and the
CodeCommit repo are different things. The empty CodeCommit repo was expected — Terraform
creates the repo, not its contents.

### 3. First real run: two more bugs

Pushed the sample app (per-repo git config, no global changes) and watched the pipeline:

1. **Build failed at `QUEUED`** — role couldn't create the CloudWatch log group. Fixed by
   creating the group in Terraform.
2. **Build failed at `DOWNLOAD_SOURCE`** — when CodePipeline drives CodeBuild, source and
   output move through the *pipeline's* artifact bucket, which the CodeBuild role couldn't
   read. Fixed, and preemptively fixed the mirror-image problem for the EC2 instance role
   (the CodeDeploy agent downloads from that same bucket).
3. Also caught before commit: the hook scripts weren't executable (`644`); set `755`.

Third run: Source ✓ Build ✓ Deploy ✓, `curl` returned the page, `plan` showed no drift.
Lesson: **`plan` verifies nothing about IAM or runtime.**

### 4. Approval stage, instance types, V1 vs V2

- Added a manual **Approval** stage between Build and Deploy; test run parked at the gate.
- Answered "what instance type?": EC2 `t3.micro`, CodeBuild `BUILD_GENERAL1_SMALL`; the
  pipeline itself has none.
- Explained V1 vs V2. The pipeline had been **V1** only because Terraform's default is V1
  and nothing set otherwise.

### 5. The cost disagreement

I first said the pipeline costs $1/month, and the README claimed a 2-day test costs
$1.50–1.60. Fetching AWS's pricing page showed V1 is "$1.00 per active pipeline per month",
active meaning *older than 30 days*, and "**free for the first 30 days after creation**".
The user disputed "free"; Cost Explorer showed $0.00 but can't settle it on day one (billing
lags ~24 h). Outcome: docs corrected to say what the pricing page states and to tell the
reader to check their own bill. **Left unresolved by data** — no bill covering this exists.

### 6. Build V2 in a separate module

`004` = 003 + fixes + V2 features, its own state key and names so both could coexist:
V2 pipeline; a `DEPLOY_NOTE` pipeline variable flowing into CodeBuild; an EventBridge push
trigger instead of polling; `CODEPIPELINE`-type CodeBuild (dropping a bucket that never held
an object); SSH rule removed; `instance_type` variable; `force_destroy` on the artifact bucket.
Applied 24 resources, pushed the app, and it worked first time.

Then tested the open questions from earlier, empirically:

| Question | Result |
|---|---|
| Push → pipeline start latency | ~16 s via EventBridge |
| Pass a value at run time | **Works** — `--variables` → CodeBuild env var → rendered in page |
| Branch name as a run-time variable | **Rejected by AWS**: *"Variables at the pipeline level cannot be used in source actions."* |
| Run a commit from another branch | **Works** with `--source-revisions` (commit ID, not branch); pushing a non-watched branch triggered nothing |
| V2 `trigger` filters for CodeCommit | **Not possible** — the API's only allowed `providerType` is `CodeStarSourceConnection` |

### 7. Tear down V1

Inspected first: the CodeCommit repo had one branch and one commit (mine) — nothing to lose.
The destroy plan was 22 resources with zero references to V2. The V1 pipeline bucket had to
be emptied by hand (no `force_destroy` — fixed in V2). Verified against AWS afterward.

### 8. HTTPS on the raw IP (investigated, not shipped)

See the next section. Interrupted by "destroy everything and document this journey".

### 9. Tear down everything

V2 (24 resources; `force_destroy` cleared the artifact bucket unaided), then the state
bucket. See "Teardown" below.

## The TLS investigation

**Ask:** put a TLS certificate on the website, on the raw public IP (no domain exists in the
account — checked Route 53, registered domains, ACM and Elastic IPs; all empty).

Findings:

- **ACM can't do this.** It issues certificates for domain names, and can't attach to a
  bare EC2 instance anyway (only to load balancers / CloudFront).
- **A trusted cert on a bare IP is possible now.** Let's Encrypt made IP-address
  certificates **generally available on 2026-01-15** (an earlier July 2025 article said
  staging-only — stale). Constraints:
  - `shortlived` profile only → **~6-day certs**, so auto-renewal is mandatory (systemd
    timer + a `--deploy-hook` that reloads the web server).
  - Challenge types: `http-01` and `tls-alpn-01` only — no DNS validation.
  - Certbot needs **≥ 5.4** for the `--webroot` authenticator with `--ip-address`.
    Certbot's Apache and nginx plugins **don't support IPs yet**, so `mod_ssl` has to be
    wired by hand (point `ssl.conf` at `/etc/letsencrypt/live/<ip>/`).
  - The IP must be stable for the cert's life. An auto-assigned EC2 public IP changes on
    stop/start → use an **Elastic IP** (same hourly cost as the auto-assigned public IPv4).
- **What the trial found:** on Amazon Linux 2023, `pip install certbot` resolved to
  **4.2.0**, which rejects `--ip-address`. Cause, confirmed on the instance: AL2023's
  default `python3` is **3.9.25**, and every certbot 5.x release requires Python ≥ 3.10 —
  pip's own message said so. AL2023's repos do offer `python3.11`, `3.12`, `3.13`, so a venv
  built on one of those should get certbot 5.x **(the fix itself was not run)**.
- **Design that would have gone into Terraform (never applied):** an `aws_eip` allocated
  before the instance; user data via `templatefile` (Python 3.11+ venv, certbot ≥ 5.4,
  `mod_ssl`); wait until the instance metadata's `public-ipv4` equals the EIP *before*
  requesting the cert (otherwise failed validations burn Let's Encrypt's rate limit);
  test against `--staging` first; add port 443 to the security group; set
  `user_data_replace_on_change = true` (user data only runs at first boot, so the instance
  must be replaced, then redeployed through the pipeline).

Options that would have needed a domain (the user hadn't picked one): CloudFront with the
default `*.cloudfront.net` certificate needs *no* domain and no renewal — arguably the
easier path — or ACM + CloudFront/ALB with a real domain; or a self-signed cert (browser
warning). **Nothing from this section reached the repo's Terraform.**

## Mistakes worth remembering (mine and the code's)

- **The README's "verified" claim was unearned** — a `plan` was presented as proof. It was
  the root cause of every runtime bug above.
- **The cost claim was wrong** and stated confidently before I'd read the pricing page.
- **Incomplete IAM check** — looked at user policies, forgot the group.
- **An 8-minute dead poll:** the CLI's `--result` shorthand splits on commas, so an approval
  summary containing one was silently not submitted; my loop then waited on a gate nobody
  had approved. The docs now warn about it.
- **Stale-status polling:** `get-pipeline-state` shows each stage's *latest* execution, which
  may be an older run, so "Deploy=Succeeded" was already true. Track the execution ID.
- **Approval token race:** the token isn't available the instant the stage goes InProgress.
- **Self-approvals:** to verify Deploy on stacks I had just built, I approved two of my own
  test runs and rejected a third (to stop a feature-branch commit deploying). Disclosed at
  the time.
- **A guess that turned out right, but was a guess:** a code comment claimed V2 triggers
  don't work with CodeCommit before I'd checked; I then verified it against the API help
  and rewrote the comment to cite it.

## Teardown record

Order matters because state lives in the bucket that's destroyed last:

1. **003 (V1)** — 22 resources. The pipeline bucket held 10 artifact objects and had no
   `force_destroy`, so it was emptied first (`BucketNotEmpty` otherwise). Destroying the
   CodeCommit repo **permanently deletes it and its history**.
2. **004 (V2)** — 24 resources; `force_destroy = true` meant no manual emptying.
3. **000 (state bucket)** — needed three extra steps: temporarily lift `prevent_destroy`;
   delete **all 57 object versions and delete markers** (versioned bucket — plain
   `aws s3 rm --recursive` isn't enough; the pile was mostly `.tflock` lock-file versions and
   old state); then `terraform destroy`. `prevent_destroy = true` was restored in the code
   afterwards. Both modules' states were confirmed at 0 resources before their history was
   deleted.

Verified with explicit counts (not by trusting Terraform's output), and the account's four
pre-existing buckets were confirmed untouched.

## What's left

**In the repo (uncommitted at time of writing):** `000_bootstrap_state_bucket/`,
`003_cicd_pipeline_ec2/` (with fixes, approval stage, `LEARNINGS.md`), `004_cicd_pipeline_v2_ec2/`,
and this file. The `terraform.tfstate`, `.terraform/` directories and `*.tfvars` are
gitignored. The `versions.tf` files still name the destroyed bucket — re-bootstrapping
makes a new one, so update the literal name.

**Outside the repo:** the CLI user was granted `AdministratorAccess` during the session — that
was the user's own change and remains in place; worth removing.

## To do it again

1. `000_bootstrap_state_bucket`: `terraform init && terraform apply`; copy the bucket name
   into `004/versions.tf`.
2. `004_cicd_pipeline_v2_ec2`: `terraform init && terraform apply`; follow its README to
   push `app-sample/`, approve, and `curl`.
3. `terraform destroy` in `004` when finished. Leave `000` up if you'll build more, but
   remember it needs the manual teardown described above.

## Follow-ups not done

Scope the pipeline role's `codedeploy:*` off `Resource = "*"`; SNS notification for the
approval stage; `QUEUED` / `PARALLEL` execution modes; split 004 into foundation / target /
pipeline states; a GitHub + CodeConnections source to use real V2 trigger filters; and
finishing HTTPS (Python 3.11+ certbot on an Elastic IP, or CloudFront if a domain-free,
zero-renewal route is preferred).
