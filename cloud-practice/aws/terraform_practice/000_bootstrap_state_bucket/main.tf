# Bootstrap — the S3 bucket that holds remote Terraform state for the other
# modules in terraform_practice/.
#
# This module deliberately uses LOCAL state: it can't store its own state in
# a bucket that doesn't exist yet. Apply it once, then point other modules'
# `backend "s3"` block at the bucket name from `terraform output`.

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

variable "region" {
  description = "AWS region for the state bucket."
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Prefix for the bucket name; a random suffix is appended so the name is globally unique."
  type        = string
  default     = "platform-lab-tfstate"
}

provider "aws" {
  region = var.region
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "${var.name_prefix}-${random_id.suffix.hex}"

  # State is the only record of what Terraform built — a stray `destroy`
  # here would orphan everything. Empty the bucket by hand if you really
  # mean to remove it.
  lifecycle {
    prevent_destroy = true
  }
}

# Versioning lets you recover a previous state file after a bad apply.
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# State can contain secrets in plaintext — never public.
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Refuse any non-TLS access to the bucket.
resource "aws_s3_bucket_policy" "tls_only" {
  bucket = aws_s3_bucket.tfstate.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.tfstate.arn, "${aws_s3_bucket.tfstate.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.tfstate]
}

# Old state versions and lock files don't need to live forever.
resource "aws_s3_bucket_lifecycle_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    id     = "expire-old-state-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  depends_on = [aws_s3_bucket_versioning.tfstate]
}

output "bucket_name" {
  value       = aws_s3_bucket.tfstate.bucket
  description = "Use as `bucket` in other modules' backend \"s3\" block."
}

output "region" {
  value       = var.region
  description = "Use as `region` in other modules' backend \"s3\" block."
}

output "backend_snippet" {
  value       = <<-EOT
    terraform {
      backend "s3" {
        bucket       = "${aws_s3_bucket.tfstate.bucket}"
        key          = "<module-name>/terraform.tfstate"
        region       = "${var.region}"
        encrypt      = true
        use_lockfile = true # S3-native locking (Terraform >= 1.10) — no DynamoDB table needed
      }
    }
  EOT
  description = "Paste into a module's versions.tf, changing `key`."
}
