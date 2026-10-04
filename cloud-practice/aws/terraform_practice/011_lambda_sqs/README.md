# 011 – Lambda triggered by SQS, code stored in S3

Nothing here is applied automatically. Read, then run it yourself.

## What it builds

```
 you / app ──send──▶  SQS queue ──(event source mapping polls)──▶ Lambda ──▶ CloudWatch logs
                         │ after 3 failed tries
                         ▼
                    dead-letter queue (DLQ)

 S3 artifacts bucket (versioned) ◀── Terraform zips ./src and uploads ── Lambda loads its code from here
```

| File | Purpose |
|---|---|
| `00_versions_and_provider.tf` | aws + archive (zip) + random (unique bucket suffix) providers |
| `variables.tf` | region, names, timeout, batch size, retry count |
| `01_artifacts_bucket.tf` | versioned, private S3 bucket for the deployment zip |
| `02_sqs.tf` | main queue + dead-letter queue + redrive policy |
| `03_iam.tf` | Lambda execution role: logs + SQS read/delete |
| `04_lambda.tf` | zip → S3 → Lambda function → SQS trigger (event source mapping) |
| `src/handler.py` | the Lambda code (processes a batch of messages) |
| `scripts/send_message.py` | dummy producer: sends messages to the queue |
| `scripts/deploy_code.sh` | deploy new code WITHOUT terraform |

## Run it

```
terraform init
terraform plan
terraform apply

pip install boto3                      # for the sender script
$(terraform output -raw send_test_message)               # send 3 good messages
$(terraform output -raw tail_logs)                       # in another terminal: watch Lambda logs
```

Try the failure path (retries, then dead-letter queue):
```
python3 scripts/send_message.py --queue-url "$(terraform output -raw queue_url)" --count 1 --fail
# Lambda logs "FAILED message ..." 3 times (maxReceiveCount), then the message lands in the DLQ:
aws sqs receive-message --queue-url "$(terraform output -raw dlq_url)" --region us-east-1
```

Destroy: `terraform destroy` (the bucket has `force_destroy = true`, so objects are removed too).

## "Do I run terraform again when the code changes?"

**It depends on who owns the code. Two valid models:**

### Model 1 – Terraform owns the code (this folder's default)

```
edit src/handler.py  →  terraform apply
```
- `archive_file` re-zips `src/`; its hash changed → Terraform uploads a new object version to S3 and updates the Lambda.
- `terraform plan` will show `aws_s3_object.code` and `aws_lambda_function.processor` changing.
- Simple, one command, everything in sync. Good for learning and small projects.
- Downside: every code tweak needs Terraform access and a full plan; slower; mixes app releases with infra changes.

### Model 2 – Terraform owns infra, a script/CI owns code (common in real teams)

1. In `04_lambda.tf` uncomment the `lifecycle { ignore_changes = [s3_key, s3_object_version, source_code_hash] }` block.
2. Run `terraform apply` **once** (creates the function, queue, bucket, IAM).
3. From then on, deploy code with:
   ```
   scripts/deploy_code.sh
   ```
   (zip → upload to the artifacts bucket under a timestamped key → `aws lambda update-function-code` → wait). No Terraform involved.
4. Run Terraform again **only when infra changes**: timeout, memory, env vars, batch size, new queues, IAM, trigger settings.

Why teams prefer Model 2: fast deploys, CI/CD can ship code with narrow permissions (no IAM/infra rights), infra changes go through a separate reviewed pipeline, and rollbacks are just "point the function at an older zip".

**Do not mix them carelessly:** if you use `deploy_code.sh` WITHOUT the `ignore_changes` block, the next `terraform apply` sees that the deployed code differs from what `src/` hashes to and redeploys the Terraform-built zip (silently reverting). Pick one model.

### Quick decision table

| What changed | Model 1 | Model 2 |
|---|---|---|
| `src/handler.py` | `terraform apply` | `scripts/deploy_code.sh` |
| Timeout / memory / env vars / batch size | `terraform apply` | `terraform apply` |
| New queue, IAM permission, trigger setting | `terraform apply` | `terraform apply` |
| First-ever creation | `terraform apply` | `terraform apply` (once) |

## How the trigger behaves (worth understanding)

- Lambda's **event source mapping** polls SQS for you (long polling) and invokes the function with **batches** (here up to 5, waiting up to 5 s to fill).
- If the handler **returns** normally, messages in the batch that were not reported as failed are **deleted**.
- With `ReportBatchItemFailures`, the handler returns `{"batchItemFailures": [{"itemIdentifier": id}]}` and **only those** messages become visible again after the **visibility timeout** (180 s here = 6 × the 30 s function timeout).
- After `maxReceiveCount` (3) receives, SQS moves the message to the **DLQ**.
- If the handler **throws** an unhandled exception, the **whole batch** is retried.
- SQS is **at-least-once**: your code must tolerate seeing the same message twice (idempotency).
- Lambda scales out automatically with queue depth (many concurrent invocations); set reserved concurrency / `scaling_config` if the downstream can't take that.

## Cost (approx.; verify)

Everything here is pay-per-use: SQS ~ $0.40 per million requests, Lambda ~ $0.20 per million invocations plus tiny compute (128 MB, arm64), S3 storage for a few KB, CloudWatch logs (7-day retention). A lab costs cents or less (free tiers may cover it). Nothing runs when idle, but polling by the event source mapping counts as SQS requests.

## Production notes (skipped here)

- Encrypt the queue (SSE-SQS/KMS), restrict the bucket policy, S3 lifecycle rule to expire old artifacts.
- Alarm on DLQ depth (`ApproximateNumberOfMessagesVisible > 0`) and Lambda errors/throttles.
- Pin dependencies in a Lambda layer or package them in the zip (this demo uses only the standard library).
- Remote encrypted Terraform state (see `000_bootstrap_state_bucket`).
- FIFO queue if ordering/deduplication matters (then `.fifo` name and message group IDs).
