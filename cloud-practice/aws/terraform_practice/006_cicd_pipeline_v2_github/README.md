# 006 — Minimal CodePipeline V2 connected to GitHub

The smallest working pipeline: **GitHub push → CodePipeline V2 → CodeBuild → Manual Approval**.
Everything is in one file, `main.tf`. `dummy-repo/` holds the files you push to GitHub.

## The flow

```
 you: git push (main)
        │
        ▼
 ┌──────────────┐  GitHub App webhook   ┌──────────────────────────────┐
 │ GitHub repo  │ ────────────────────▶ │ CodeConnection (GitHub)      │
 │ (dummy-repo) │                       │ AWS's authorized link to     │
 └──────────────┘                       │ your GitHub account          │
                                        └──────────────┬───────────────┘
                                                       │ V2 trigger matches branch "main"
                                                       ▼
 ┌──────────────────────────── CodePipeline V2 ────────────────────────────┐
 │  Stage 1: Source                         Stage 2: Build                 │
 │  pulls the commit via the connection ─▶  CodeBuild runs buildspec.yml   │
 │  zips it to S3 as "source_output"        from that zip                  │
 │                                                  │                      │
 │                                                  ▼                      │
 │                                          Stage 3: Approval              │
 │                                          pipeline PAUSES until a human  │
 │                                          clicks Approve / Reject        │
 └──────────────────────────────┬──────────────────────────────────────────┘
                                │
                     S3 artifact bucket (hand-off between stages)
                                │
                     CloudWatch Logs (build output you can read)
```

| Resource in `main.tf`                | Why it exists |
|--------------------------------------|---------------|
| `aws_codestarconnections_connection` | Lets AWS read your GitHub repo and receive push events. |
| `aws_s3_bucket.artifacts`            | Stages don't talk directly — they pass zips through this bucket. |
| `aws_codebuild_project` + IAM role   | The machine that runs `buildspec.yml`; role allows logs + S3. |
| `aws_codepipeline` + IAM role        | The orchestrator; role allows *use connection*, *start build*, *S3*. |
| `stage "Approval"` (Manual)          | Human gate. In a real pipeline a Deploy stage would follow it. |
| `trigger { ... }` block              | **V2-only.** Start on push to `main` — no webhook or EventBridge rule to manage. |

## Setup (one time)

**1. Create the dummy GitHub repo** (empty, e.g. `pipeline-dummy-repo`), then push the files:

```bash
cd dummy-repo
git init -b main
git add . && git commit -m "init"
git remote add origin git@github.com:<your-user>/pipeline-dummy-repo.git
git push -u origin main
```

**2. Apply Terraform**

```bash
cd ..                                   # back to 006_cicd_pipeline_v2_github
cp terraform.tfvars.example terraform.tfvars   # set github_repo = "<your-user>/pipeline-dummy-repo"
terraform init
terraform apply
```

Output shows `connection_status = "PENDING"`. That's expected — Terraform **cannot**
finish the GitHub OAuth handshake; a human must.

**3. Activate the connection (manual, once)**

AWS Console → *Developer Tools → Settings → Connections* → `gh-pipeline-v2`
→ **Update pending connection** → *Install a new app* (installs the "AWS Connector
for GitHub" app on your account; give it access to the dummy repo) → **Connect**.
Status becomes **Available**.

**4. Run it**

The first run right after `apply` fails at Source because the connection was still
PENDING. Now either click **Release change** in the console, or just push:

```bash
cd dummy-repo
echo "version 2" > app.txt
git commit -am "trigger" && git push
```

Open `pipeline_url` from the outputs → Source ✅ → Build ✅ → click the Build
action's *Details* to see the `echo`/`cat app.txt` output → Approval shows
**Waiting for approval** → click **Review** → *Approve* (run succeeds) or *Reject*
(run marked failed).

## Things to try

- Push to another branch → pipeline does **not** start (trigger filters on `main`).
- Push twice quickly while a run waits at Approval → V2's default `SUPERSEDED`
  mode lets the newer run replace the older waiting one.
- Break `buildspec.yml` (e.g. `exit 1`) → Build stage fails, logs show why.

## Cleanup

```bash
terraform destroy
```

Cost while idle is ~$0 (V2 bills per action-minute; the S3 bucket is tiny).
Optionally uninstall the "AWS Connector for GitHub" app in GitHub → Settings → Applications.
