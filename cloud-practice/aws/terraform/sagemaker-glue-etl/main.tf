##############################################################################
# Locals
##############################################################################
locals {
  name        = var.project
  db_name     = "${replace(var.project, "-", "_")}_db"
  kms_enabled = var.kms_key_arn != ""

  raw_path      = "s3://${aws_s3_bucket.data.bucket}/raw/orders/"
  curated_path  = "s3://${aws_s3_bucket.data.bucket}/curated/orders/"
  rejected_path = "s3://${aws_s3_bucket.data.bucket}/rejected/orders/"
  script_key    = "scripts/etl_job.py"

  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/sagemaker-glue-etl"
    },
    var.extra_tags,
  )
}

resource "random_id" "suffix" {
  byte_length = 4
}

##############################################################################
# Data lake bucket — one bucket, prefixes per zone:
#   raw/       landing zone (CSV in)
#   curated/   Glue output (partitioned Parquet) — what SageMaker reads
#   rejected/  rows the job refused, kept for inspection
#   scripts/   the Glue job script
#   tmp/       Glue temp dir
##############################################################################
resource "aws_s3_bucket" "data" {
  bucket        = "${local.name}-${random_id.suffix.hex}"
  force_destroy = var.force_destroy
}

resource "aws_s3_bucket_ownership_controls" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = local.kms_enabled ? "aws:kms" : "AES256"
      kms_master_key_id = local.kms_enabled ? var.kms_key_arn : null
    }
    bucket_key_enabled = local.kms_enabled
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "expire-glue-temp"
    status = "Enabled"
    filter {
      prefix = "tmp/"
    }
    expiration {
      days = 7
    }
  }

  rule {
    id     = "cleanup-noncurrent-and-multipart"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.data]
}

# The ETL script and sample input ship with the repo; etag makes Terraform
# re-upload whenever the file content changes.
resource "aws_s3_object" "etl_script" {
  bucket = aws_s3_bucket.data.id
  key    = local.script_key
  source = "${path.module}/scripts/etl_job.py"
  etag   = filemd5("${path.module}/scripts/etl_job.py")
}

resource "aws_s3_object" "sample_data" {
  count  = var.upload_sample_data ? 1 : 0
  bucket = aws_s3_bucket.data.id
  key    = "raw/orders/sample_orders.csv"
  source = "${path.module}/data/sample_orders.csv"
  etag   = filemd5("${path.module}/data/sample_orders.csv")
}

##############################################################################
# Glue — IAM role (used by the job AND the crawler)
##############################################################################
data "aws_iam_policy_document" "glue_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue" {
  name               = "${local.name}-glue-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

# Managed policy: Glue catalog access, CloudWatch Logs, and the basics a job needs.
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

data "aws_iam_policy_document" "glue_data" {
  statement {
    sid       = "ListBucket"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.data.arn]
  }
  statement {
    sid       = "ReadWriteDataLake"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.data.arn}/*"]
  }

  dynamic "statement" {
    for_each = local.kms_enabled ? [1] : []
    content {
      sid       = "UseDataKey"
      actions   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
      resources = [var.kms_key_arn]
    }
  }
}

resource "aws_iam_role_policy" "glue_data" {
  name   = "data-lake-access"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue_data.json
}

##############################################################################
# Glue — Data Catalog database, security configuration, job, crawler
##############################################################################
resource "aws_glue_catalog_database" "this" {
  name        = local.db_name
  description = "Tables produced by ${local.name} (raw + curated orders)."
}

# Tells Glue to encrypt what the job writes to S3 with the CMK. Only created
# when a key is supplied.
resource "aws_glue_security_configuration" "this" {
  count = local.kms_enabled ? 1 : 0
  name  = "${local.name}-sec"

  encryption_configuration {
    s3_encryption {
      s3_encryption_mode = "SSE-KMS"
      kms_key_arn        = var.kms_key_arn
    }
    cloudwatch_encryption {
      cloudwatch_encryption_mode = "DISABLED"
    }
    job_bookmarks_encryption {
      job_bookmarks_encryption_mode = "DISABLED"
    }
  }
}

resource "aws_glue_job" "etl" {
  name              = "${local.name}-orders-etl"
  description       = "Cleans raw orders CSV into partitioned Parquet; diverts bad rows to rejected/."
  role_arn          = aws_iam_role.glue.arn
  glue_version      = var.glue_version
  worker_type       = var.glue_worker_type
  number_of_workers = var.glue_number_of_workers
  timeout           = var.glue_job_timeout_minutes
  max_retries       = 0

  security_configuration = one(aws_glue_security_configuration.this[*].name)

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_bucket.data.bucket}/${local.script_key}"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--job-bookmark-option"              = var.enable_job_bookmark ? "job-bookmark-enable" : "job-bookmark-disable"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-glue-datacatalog"          = "true"
    "--TempDir"                          = "s3://${aws_s3_bucket.data.bucket}/tmp/"
    "--raw_path"                         = local.raw_path
    "--curated_path"                     = local.curated_path
    "--rejected_path"                    = local.rejected_path
  }

  depends_on = [aws_s3_object.etl_script]
}

# Crawls the curated Parquet and registers/updates a partitioned table
# (curated_orders) in the catalog so Athena / SageMaker can query it by name.
resource "aws_glue_crawler" "curated" {
  name          = "${local.name}-curated-crawler"
  database_name = aws_glue_catalog_database.this.name
  role          = aws_iam_role.glue.arn
  table_prefix  = "curated_"

  security_configuration = one(aws_glue_security_configuration.this[*].name)

  s3_target {
    path = local.curated_path
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
}

# After every successful ETL run, refresh the catalog (new partitions appear).
resource "aws_glue_trigger" "crawl_after_etl" {
  name = "${local.name}-crawl-after-etl"
  type = "CONDITIONAL"

  predicate {
    conditions {
      job_name = aws_glue_job.etl.name
      state    = "SUCCEEDED"
    }
  }

  actions {
    crawler_name = aws_glue_crawler.curated.name
  }
}

resource "aws_glue_trigger" "schedule" {
  count    = var.schedule_cron != "" ? 1 : 0
  name     = "${local.name}-schedule"
  type     = "SCHEDULED"
  schedule = var.schedule_cron

  actions {
    job_name = aws_glue_job.etl.name
  }
}

##############################################################################
# SageMaker — execution role + notebook instance (reads the curated zone)
##############################################################################
data "aws_iam_policy_document" "sagemaker_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["sagemaker.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sagemaker" {
  name               = "${local.name}-sagemaker-role"
  assume_role_policy = data.aws_iam_policy_document.sagemaker_assume.json
}

# NOTE: AmazonSageMakerFullAccess is broad — fine for a lab, not for prod
# (same trade-off as ../sagemaker). The inline policy below is what actually
# scopes this role to THIS project's data.
resource "aws_iam_role_policy_attachment" "sagemaker_full" {
  role       = aws_iam_role.sagemaker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

data "aws_iam_policy_document" "sagemaker_data" {
  statement {
    sid       = "ListBucket"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.data.arn]
  }
  statement {
    sid       = "ReadWriteDataLake"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.data.arn}/*"]
  }
  statement {
    sid = "ReadGlueCatalog"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartition",
      "glue:GetPartitions",
    ]
    resources = ["*"]
  }

  dynamic "statement" {
    for_each = local.kms_enabled ? [1] : []
    content {
      sid = "UseDataKey"
      actions = [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey",
        "kms:DescribeKey",
        "kms:CreateGrant", # needed to attach a KMS-encrypted volume to the notebook
      ]
      resources = [var.kms_key_arn]
    }
  }
}

resource "aws_iam_role_policy" "sagemaker_data" {
  name   = "data-lake-access"
  role   = aws_iam_role.sagemaker.id
  policy = data.aws_iam_policy_document.sagemaker_data.json
}

resource "aws_sagemaker_notebook_instance" "this" {
  count = var.create_notebook_instance ? 1 : 0

  name                   = "${local.name}-notebook"
  role_arn               = aws_iam_role.sagemaker.arn
  instance_type          = var.notebook_instance_type
  volume_size            = var.notebook_volume_size_gb
  kms_key_id             = local.kms_enabled ? var.kms_key_arn : null
  root_access            = "Disabled"
  platform_identifier    = "notebook-al2-v2"
  direct_internet_access = "Enabled"

  depends_on = [
    aws_iam_role_policy.sagemaker_data,
    aws_iam_role_policy_attachment.sagemaker_full,
  ]
}
