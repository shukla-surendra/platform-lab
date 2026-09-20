# V1 pipeline — what we learned

Retrospective on `003_cicd_pipeline_ec2` (a **V1** CodePipeline: CodeCommit →
CodeBuild → [Approval] → CodeDeploy → one EC2 instance). Applied and run
end to end on 2026-09-20, then destroyed and replaced by
[`004_cicd_pipeline_v2_ec2`](../004_cicd_pipeline_v2_ec2/), which carries every
fix below and adds V2 features.

Everything here was observed running against real AWS, unless marked
**(not tested)**. For the whole story across all modules — including the V2 build,
the TLS investigation and the final teardown — see [`../JOURNEY.md`](../JOURNEY.md).

---

## 1. `terraform plan` is not proof it works

The original README said "verified against real AWS (`terraform plan`: 20
resources, 0 errors)". It was not verified. **`plan` doesn't check IAM
permissions and doesn't run the pipeline.** The first real run failed three
separate ways (sections 3–5), none of which `plan` could see.

> Verify by *running* the thing: push, watch every stage go green, `curl` the
> result, then re-run `terraform plan` and confirm no drift.

## 2. Remote state needs a bootstrap, and the bootstrap can't use remote state

- State lives in an S3 bucket created by its own tiny module
  (`000_bootstrap_state_bucket/`) that keeps **local** state — it can't store
  state in a bucket that doesn't exist yet. Back up that local state file.
- `backend "s3"` blocks **can't reference variables**, so the bucket name is
  literal in `versions.tf`.
- **S3-native locking** (`use_lockfile = true`, Terraform ≥ 1.10) replaces the
  old DynamoDB lock table. Bump `required_version` to match.
- Bucket hardening used: versioning (recover a bad state), AES256 encryption,
  all public access blocked, TLS-only bucket policy, 90-day expiry of old
  versions, `prevent_destroy`.
- **Privacy:** the bucket name uses a random suffix, not the AWS account ID —
  this repo is on GitHub.

## 3. Permissions: the failure is at `apply`, and partial applies are safe

- The CLI user had EC2/IAM/S3/SSM/CodeCommit access but **nothing for
  CodeBuild, CodeDeploy or CodePipeline**. `plan` passed; `apply` created 18 of
  20 resources, then failed with `AccessDeniedException`.
- The error text says *"no identity-based policy allows the … action"* — that
  wording means an **implicit deny** (nothing grants it), as opposed to an
  explicit deny from an SCP or permission boundary, which is worded differently.
- Check before you apply, instead of guessing from policy names:
  `aws iam simulate-principal-policy --policy-source-arn <user-arn> --action-names codebuild:CreateProject codedeploy:CreateApplication codepipeline:CreatePipeline`
- Look at **group** policies too, not just the user's directly attached ones.
- A failed apply is **resumable**: state was saved to S3 with the 18 created
  resources; after the permissions were fixed, `apply` created only the
  remaining 5.

## 4. Runtime bugs the code shipped with

Both are fixed in `codebuild.tf` / `ec2.tf` here and built into 004.

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | Build fails at `QUEUED`: *not authorized to perform `logs:CreateLogGroup`* | The role could write log streams, but the log group `/aws/codebuild/<project>` didn't exist and CodeBuild couldn't create it | Create the `aws_cloudwatch_log_group` in Terraform (also cleans up on `destroy`) |
| 2 | Build fails at `DOWNLOAD_SOURCE`: *s3:GetObject AccessDenied* | When **CodePipeline** runs CodeBuild, source and output travel through the **pipeline's** artifact bucket. The role only had the project's *own* bucket | Grant the CodeBuild role read/write on the pipeline bucket |
| 3 | *(would have hit at Deploy — fixed preemptively)* | The **CodeDeploy agent on the instance** downloads the build output from that same bucket using the **instance** role, which only had SSM | Grant the instance role `s3:GetObject` on the pipeline bucket |

**The design insight behind #2 and #3:** the pipeline's artifact bucket is the
hub — every stage reads from or writes to it. The separate
`codebuild_artifacts` bucket in 003 ended with **0 objects**: it was never
used once CodePipeline drove the build. 004 sets CodeBuild's source/artifacts
type to `CODEPIPELINE` and drops that bucket. (Trade-off: `aws codebuild
start-build` no longer works standalone.)

## 5. The app repo has its own gotchas

- **An empty repo makes the first pipeline run fail** at Source. Expected —
  Terraform creates the repo, not its contents. Push first.
- **Hook scripts must be executable in git** (`100755`). The sample's scripts
  were `644`; CodeDeploy runs them directly. `chmod +x` before committing.
- The pipeline watches a specific branch. A fresh `git init` may default to
  `master`; push `HEAD:main`.
- `aws codecommit credential-helper` works per-repo (`git config --local`), so
  there's no need to touch global git config.
- CodeCommit was closed to accounts created after 2024-07-25; if create fails
  with an access error, that's why.

## 6. Infra code vs app code

- **Two kinds of code, two lifecycles.** The `.tf` files are *infra code*: applied
  by hand from a laptop with `terraform apply`, never seen by the pipeline. The
  `appspec-sample/` contents are *app code*: pushed to **CodeCommit**, which is the
  only repo the pipeline watches. The GitHub repo and the CodeCommit repo are
  different things.
- The convention is separate lifecycles, permissions and pipelines — not "infra is
  never automated". Infra can go through its own pipeline (plan on PR, apply on
  merge); it just shouldn't ride the app pipeline, or app pushes could change IAM.
- 003 puts EC2 + pipeline + roles in **one** state as a learning shortcut. A real
  layout splits foundation / target infra / pipeline into separate states, with an
  app repo containing only code + `buildspec.yml` / `appspec.yml`.

## 7. Manual approval stage

- A stage of `category = "Approval"`, `provider = "Manual"`. Stage order in the
  `.tf` file **is** execution order — it must sit between Build and Deploy.
- Unactioned approvals expire after **7 days** and count as a failure.
- Approve/reject:
  `aws codepipeline put-approval-result --pipeline-name … --stage-name Approval --action-name ApproveDeploy --token <token> --result 'summary=…,status=Approved'`
- **CLI gotchas we hit:**
  - `--result` uses shorthand syntax, so a **comma inside `summary=`** splits the
    value and fails validation. Avoid commas (or use JSON).
  - The approval **token isn't available the instant the stage flips to
    `InProgress`** — poll until it matches a UUID before submitting.
- Nothing notifies anyone that a run is waiting. For that, add an SNS topic +
  email subscription and pass it as `NotificationArn` **(not done here)**.
- Admin access isn't required to approve; the approver only needs
  `codepipeline:PutApprovalResult`.

## 8. Watching pipelines from scripts: track the execution ID

`get-pipeline-state` reports each stage's **latest** execution, which can be an
*older* run. During a new run, later stages still show the previous run's
`Succeeded` until the new run reaches them. Polling for "Deploy=Succeeded"
returned instantly on stale data. Filter on
`latestExecution.pipelineExecutionId`, or poll `get-pipeline-execution` for the
specific ID.

## 9. Cost — and a correction

- The original README claimed a 2-day test costs ~$1.50–1.60, "almost entirely"
  CodePipeline's flat $1, "sunk for the month". **That was wrong as written.**
  AWS's pricing page states: V1 is $1.00 per *active* pipeline per month, where
  active means *existed for more than 30 days* and had a code change that month,
  and **"Pipelines are free for the first 30 days after creation"**; not prorated;
  one free active V1 pipeline per month.
- So a 2-day V1 test's CodePipeline cost is ~$0. If you keep it past 30 days and
  push code through it, it's $1/month.
- Real cost of a short test is the **EC2 instance**: `t3.micro` ≈ $0.0104/hr
  (~$0.50 for 2 days) off Free Tier. CodeBuild `BUILD_GENERAL1_SMALL` is
  per-build-minute, fractions of a cent here. CodeDeploy on EC2 is free.
- Cost Explorer lags ~24h, so a brand-new pipeline shows $0.00 regardless — it
  can't confirm or refute a pricing claim on day one. Check the actual bill.
- Sizes used: EC2 `t3.micro` (2 vCPU, 1 GiB); CodeBuild `BUILD_GENERAL1_SMALL`
  (2 vCPU, 3 GiB), the smallest standard tier. CodePipeline itself has no
  instance type.

## 10. V1 vs V2

| | V1 | V2 |
|---|---|---|
| Runtime input | none — config is fixed | pipeline-level **variables**, overridable per run |
| Triggers | polling or EventBridge | + pipeline-level triggers with filters (**connection sources only**) |
| Execution modes | `SUPERSEDED` only | `SUPERSEDED`, `QUEUED`, `PARALLEL` |
| Pricing | $1 / active pipeline / month (first 30 days free) | $0.002 / action-execution-minute, 100 free min/month; manual approval not billed |
| Also | | commit-ID source override, stage rollback/retry |

`pipeline_type` defaults to **V1** in Terraform if you don't set it — the 003
pipeline was V1 only because nothing said otherwise.

### Answers to "what if I need values or a branch name at run time?" — all tested on V2

- **Values — works.** Declare `variable {}` blocks on the pipeline, reference as
  `#{variables.NAME}` in action config, override with
  `aws codepipeline start-pipeline-execution --variables name=NAME,value=…`.
  We passed one through Build as a CodeBuild env var and saw it rendered in the
  deployed page. The run records it under `resolvedValue`.
- **Branch as a variable — does NOT work.** AWS rejects it at `UpdatePipeline`:
  *"Variables at the pipeline level cannot be used in source actions."*
- **Workaround — run any commit at run time.**
  `--source-revisions actionName=Source,revisionType=COMMIT_ID,revisionValue=<sha>`.
  We ran a commit from an un-watched `feature` branch and the execution's
  `revisionId` matched it. It takes a commit ID, not a branch name.
- **V2 `trigger` filters don't cover CodeCommit.** The API's only allowed trigger
  `providerType` is `CodeStarSourceConnection`. For CodeCommit, use an EventBridge
  rule (004 does): measured ~16s from push to execution start. Pushing a branch the
  rule doesn't match started nothing.
- **V2 + `PollForSourceChanges`:** 004 sets it to `"false"` and relies on
  EventBridge. Polling under V2 was **not tested**.

## 11. Teardown

- Non-empty S3 buckets make `terraform destroy` fail with `BucketNotEmpty`. 003's
  buckets had no `force_destroy`, so the pipeline bucket was emptied first. 004 sets
  `force_destroy = true` on its (disposable) artifact bucket.
- Destroying the `aws_codecommit_repository` **permanently deletes the repo and its
  history**. Fine for a sample app; not fine for real code.
- `000_bootstrap_state_bucket` has `prevent_destroy` on purpose — it outlives the
  modules whose state it holds. (It was eventually destroyed too, once nothing
  used it; that needs the safeguard lifted and **every object version** deleted —
  see `../JOURNEY.md`.)

## 12. Smaller things

- The CLI's default region (`ap-south-1` here) differed from the module's
  (`us-east-1`). Pass `--region` on every `aws codepipeline / codebuild / logs`
  command, or you'll see "not found".
- 003 opened SSH (22) to `0.0.0.0/0` on an instance with **no key pair** — it did
  nothing. Session Manager (`AmazonSSMManagedInstanceCore`) is the way in; 004 drops
  the rule.
- CodeDeploy's `Resource = "*"` in the pipeline role is left as a follow-up to
  scope down.
- Tag-based targeting: the deployment group finds the instance by its `Name` tag, so
  the instance can be replaced without touching CodeDeploy — but the tag in
  `ec2.tf` and `codedeploy.tf` must match, or you get "no instances found".

## What to try next

- Scope the pipeline role's CodeDeploy permissions to the specific app / group.
- SNS notification for the approval stage.
- `QUEUED` and `PARALLEL` execution modes.
- Split 004 into foundation / target / pipeline states.
- A GitHub + CodeConnections source, to use real V2 triggers with branch/tag/path
  filters.
