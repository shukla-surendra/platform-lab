# Managing infra and Lambda code: the standard way

Companion to `README.md`. What was **verified in this lab** is marked *(verified)*; everything else is general knowledge, so check current docs before relying on it.

## 1. The core idea: infra and code have different lifecycles

| | Infrastructure | Application code |
|---|---|---|
| Examples | queue, bucket, IAM, function settings, trigger | `handler.py` |
| Changes | rarely, deliberately | many times a day |
| Needs | broad permissions (IAM, SQS, S3...), review | narrow permission: update one function |
| Tool | **Terraform** | **CI/CD pipeline** (script, GitHub Actions, CodePipeline...) |

Standard practice in real teams: **Terraform creates and owns the infrastructure; a separate pipeline ships code.** Terraform runs when infra changes, the pipeline runs when code changes. Putting both in one `terraform apply` (Model 1) is fine for learning and small projects, but couples every code tweak to a full infra plan.

## 2. The two models (this folder supports both)

### Model 1: Terraform owns the code (default in `04_lambda.tf`)

```
edit src/handler.py  ->  terraform apply
```
`archive_file` re-zips `src/` -> hash changes -> new S3 object version -> Lambda updated. One command, everything in sync.

### Model 2: Terraform owns infra, a pipeline owns code

1. Uncomment in `04_lambda.tf`:
   ```hcl
   lifecycle { ignore_changes = [s3_key, s3_object_version, source_code_hash] }
   ```
2. `terraform apply` once (creates everything, including a first version of the code).
3. Ship code with `scripts/deploy_code.sh` (zip -> upload to S3 -> `aws lambda update-function-code` -> wait).
4. Run Terraform again only for infra changes (timeout, memory, env vars, batch size, IAM, new queues).

Do not mix them carelessly: using the script **without** `ignore_changes` makes the next `terraform apply` redeploy whatever `src/` hashes to, silently reverting the pipeline's deploy.

| Change | Model 1 | Model 2 |
|---|---|---|
| `src/handler.py` | `terraform apply` | `scripts/deploy_code.sh` / CI |
| Timeout, memory, env, batch size | `terraform apply` | `terraform apply` |
| New queue / IAM / trigger setting | `terraform apply` | `terraform apply` |

## 3. A typical CI pipeline for Model 2 (illustrative, not run)

```
on push to main (paths: src/**):
  1. lint + unit tests
  2. build: zip src/ (plus pinned dependencies)
  3. upload zip to S3:  lambda/processor-<git-sha>.zip     (immutable key per commit)
  4. aws lambda update-function-code --s3-bucket ... --s3-key lambda/processor-<git-sha>.zip --publish
  5. smoke test (send a test message, check logs / metrics)
  6. (optional) shift an alias to the new version

on push to main (paths: *.tf):
  terraform fmt/validate -> plan (review) -> apply (approval)
```
CI's IAM role for code deploys needs only: `s3:PutObject` on the artifacts bucket and `lambda:UpdateFunctionCode` (plus `lambda:PublishVersion`, `lambda:UpdateAlias` if used) on that function: no IAM or infra rights.

## 4. Versions, aliases and rollback (standard practice, not implemented here)

- `publish = true` on the function (or `--publish` in the CLI) creates an **immutable numbered version** for every code change.
- An **alias** (e.g. `live`) points at a version. Point the SQS trigger and callers at the **alias**, not `$LATEST`.
- **Deploy** = publish a new version and move the alias. **Rollback** = move the alias back (seconds, no rebuild).
- With CodeDeploy you can shift traffic gradually (canary / linear). Less relevant for an SQS-triggered worker, but standard for APIs.
- Keep old zips in the versioned bucket (add an S3 lifecycle rule to expire them eventually).

## 5. "Data in Terraform reads from AWS, so how does `data "archive_file"` create a zip?"

Short answer: **a data source means "compute or look up a value at plan time". It is not limited to reading AWS.** `archive_file` is a data source from the **archive provider** (not the AWS provider): it computes a zip from local files and returns its hash. The zip file on disk is a side effect.

### What I verified in this lab

- *(verified)* After apply, `build/processor.zip` exists locally (753 bytes) containing `handler.py`.
- *(verified)* In state, `data.archive_file.lambda` holds only metadata: `output_path`, `output_size`, `output_md5`, `output_base64sha256`, `source_dir`, `type`. **The zip itself is not in state.**
- *(verified)* I deleted the zip and ran `terraform plan -refresh-only`: the output showed `data.archive_file.lambda: Reading... Read complete` and `build/processor.zip` was **recreated**. So the zip is **rebuilt during plan/refresh**, every time.
- *(verified)* Zip entries get a fixed timestamp (`01-01-2049`), so identical content gives an identical hash on every machine (reproducible builds).
- *(verified)* The provider documentation says the archive is "built during the terraform plan, so you must persist the archive through to the terraform apply".

### Data source vs resource: the real distinction

| | `data` | `resource` |
|---|---|---|
| Purpose | Read/compute a value | Create, update, delete something |
| Recorded for lifecycle | No (re-read each plan) | Yes, tracked and destroyed |
| `terraform destroy` | Nothing to destroy | Deletes it |

Many data sources compute locally and never call AWS:

| Data source | What it does |
|---|---|
| `archive_file` | Zip files locally |
| `aws_iam_policy_document` | Builds IAM policy JSON locally (used in `03_iam.tf`) |
| `local_file` | Reads a local file |
| `external` | Runs a program and reads its JSON output |
| `http` | Fetches a URL |
| `terraform_remote_state` | Reads another stack's outputs |

Data sources that **do** read AWS: `aws_ami`, `aws_vpc`, `aws_caller_identity`, `aws_subnets`...

### Nuance: the provider also has a *resource* form

*(verified in the provider schema)* `hashicorp/archive` exposes **both** a `data "archive_file"` and a `resource "archive_file"`. The data source is what almost everyone uses (and what this lab uses). I have not tested the resource form here; check the provider docs for its current behaviour and recommendation before choosing it.

### Gotchas with `archive_file`

- **Plan and apply in different CI jobs/machines**: the zip is built at plan time. If apply runs on a fresh runner, the file must be rebuilt or passed along (artifact), or the upload fails.
- It zips only files; it does **not** run `pip install` or build steps. Dependencies must already be inside the source dir.
- Plan needs the source present: `terraform plan` on a machine without `src/` fails.
- The zip lives in `build/` (git-ignored), not in state.
- Hash drives change detection: edit any file in `src/` -> new hash -> redeploy (Model 1).

## 6. Other ways to package and deploy the code

| Approach | How | When to use | Verified here? |
|---|---|---|---|
| `archive_file` data source (this lab) | Zip `src/` at plan time | Small, no/simple dependencies | **Yes, run** |
| Build step with `terraform_data` + `local-exec` | Run `pip install -t ...`/build scripts, then zip; `triggers_replace` on a file hash | Need to install dependencies from Terraform | Syntax validated only |
| `external` data source | Script prints JSON (e.g. hash of a built artifact) | Custom build logic returning values | Syntax validated only |
| Build in CI, Terraform just references the artifact | Pipeline uploads `processor-<sha>.zip`; Terraform takes the S3 key/version as a variable, or Model 2 | Standard for teams | Script path tested |
| Community module (`terraform-aws-modules/lambda/aws`) | Module packages (including dependencies) and deploys | Want less boilerplate | Not tried |
| Container image Lambda | Build Docker image, push to ECR, `package_type = "Image"` | Large dependencies (>250 MB unzipped), custom runtimes | Not tried |
| Lambda layers | Dependencies in a separate layer, small function zip | Share libs across functions | Not tried |
| SAM / CDK / Serverless Framework | Tools that package and deploy functions | Function-centric projects | Not tried |

Guidance: **start with `archive_file`** for simple handlers; move to **CI-built artifacts (Model 2)** once code changes often or has dependencies; use **containers** when size or native dependencies demand it.

## 7. Recommended next steps for this lab

1. Switch to Model 2 (uncomment `ignore_changes`), run `terraform apply`, change `handler.py`, deploy with `scripts/deploy_code.sh`, confirm `terraform plan` shows no change.
2. Add `publish = true` + an alias `live`, point the event source mapping at the alias, practise rollback by moving the alias.
3. Add a dependency (e.g. `requests`) and compare packaging with a `terraform_data` build step versus a CI build.
4. Add alarms: DLQ depth > 0 and Lambda errors.
