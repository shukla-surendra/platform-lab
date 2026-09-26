# Terraform: SageMaker + Glue ETL — raw CSV → curated Parquet → notebook

A small end-to-end data-prep pipeline: a **Glue PySpark job** cleans and
validates raw order data, writes **partitioned Parquet**, a **crawler**
registers it in the Glue Data Catalog, and a **SageMaker notebook instance**
(with a role scoped to the same bucket) reads the curated data for
exploration/training. Optionally encrypts everything with the CMK from
`../s3-kms`.

> ⚠️ **Cost:** the Glue job bills per DPU-hour (2 × G.1X ≈ 2 DPU, 1-minute
> minimum; a sample run costs cents). The **notebook instance bills hourly
> while InService** (ml.t3.medium ≈ $0.05/hr) — stop it when idle, or set
> `create_notebook_instance = false`. S3 and the catalog are negligible at
> this scale. `plan` is free.

## What it creates

```
S3 data lake bucket (private, versioned, SSE-S3 or SSE-KMS)
 ├── raw/orders/        ← sample_orders.csv uploaded here (input)
 ├── scripts/           ← etl_job.py
 ├── curated/orders/    ← Parquet partitioned by order_date (output)
 ├── rejected/orders/   ← rows that failed validation, with reject_reason
 └── tmp/               ← Glue temp dir (expires after 7 days)

Glue
 ├── IAM role (AWSGlueServiceRole + scoped S3/KMS access)
 ├── Catalog database
 ├── ETL job (Glue 4.0, 2 × G.1X, bookmarks on, 30-min timeout)
 ├── Crawler → table curated_orders
 ├── Trigger: crawler runs after each SUCCEEDED job run
 ├── Trigger: optional cron schedule for the job
 └── Security configuration (only when kms_key_arn is set)

SageMaker
 ├── Execution role (AmazonSageMakerFullAccess for the lab + scoped S3/Glue/KMS)
 └── Notebook instance (optional, ml.t3.medium)
```

## What the ETL job does (`scripts/etl_job.py`)
1. Reads `raw/orders/*.csv` with **job bookmarks** (re-runs only see new files).
2. Trims/normalises strings, casts `quantity`, `unit_price`, `order_ts`.
3. Rejects rows with a missing key, non-positive quantity/price or a bad timestamp; keeps the latest row per `order_id`, rejecting older duplicates.
4. Adds `total_amount`, `order_date`, `order_hour`, `is_high_value`.
5. Writes good rows to `curated/` (append, partitioned by `order_date`) and bad rows to `rejected/` as JSON.

The sample CSV deliberately contains a duplicate order, a missing ID, a
negative quantity and an unparseable timestamp so you can see all four
reject paths.

## Files
| File | Purpose |
|---|---|
| `versions.tf` | Provider pins + default tags |
| `variables.tf` | Glue sizing, bookmarks, schedule, notebook, optional KMS key |
| `main.tf` | Bucket, script upload, Glue role/job/crawler/triggers, SageMaker role/notebook |
| `outputs.tf` | Names/paths + a `next_steps` runbook |
| `scripts/etl_job.py` | The Glue PySpark job |
| `data/sample_orders.csv` | Sample input, uploaded to `raw/orders/` |

## Usage
```bash
cd aws/terraform/sagemaker-glue-etl
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
terraform output next_steps      # copy/paste the run commands
terraform destroy                # also stops the notebook meter
```

### With the KMS bucket from `../s3-kms`
```bash
# in s3-kms/
terraform output -raw kms_key_arn
# in sagemaker-glue-etl/terraform.tfvars
kms_key_arn = "arn:aws:kms:us-east-1:<account>:key/<id>"
```
The `s3-kms` key policy delegates to IAM, so the roles created here work
without editing that key's policy. If you instead use a key whose policy does
*not* delegate to IAM, add the Glue and SageMaker role ARNs to its
`key_user_arns`.

## Things to try (mini-labs)
1. Run the job, then `aws s3 ls --recursive` `curated/` and `rejected/` — confirm the four bad rows landed in `rejected/` with reasons.
2. Run the job **again** immediately: the bookmark sees no new files, so it logs "nothing to do" and curated data is not duplicated. Now set `enable_job_bookmark = false`, apply and re-run to watch duplicates accumulate — that is what bookmarks prevent.
3. Upload a second CSV to `raw/orders/` with new dates and re-run: a new `order_date=` partition appears and the crawler updates the table.
4. In the notebook: `pd.read_parquet("s3://<bucket>/curated/orders/")`, then build a simple model (e.g. predict `is_high_value`) and launch a SageMaker training job with `sagemaker_role_arn`.
5. Set `schedule_cron` and apply to see a scheduled trigger; check the job's CloudWatch logs (`/aws-glue/jobs/`) and the Glue job metrics.
6. Set `kms_key_arn`, re-apply, and `head-object` a curated file to see `aws:kms` with your key.

## Deliberately minimal
- Notebook instance runs with direct internet access, no VPC/private networking, no idle-shutdown lifecycle script.
- `AmazonSageMakerFullAccess` on the SageMaker role is for the lab; scope it down for anything real.
- Single job, no Glue workflow/orchestration, no data-quality rules, no Athena workgroup.
- Changing `kms_key_arn` on an existing deployment only affects new objects; already-written objects keep their old encryption.
