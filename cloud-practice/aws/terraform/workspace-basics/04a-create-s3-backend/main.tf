terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  # No backend block on purpose: this folder creates the bucket, so it
  # can't store its own state there yet. It uses local state.
}

provider "aws" {
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}

locals {
  # Account id makes the name globally unique without you inventing one
  bucket_name = "tfstate-${data.aws_caller_identity.current.account_id}-us-east-1"
}

resource "aws_s3_bucket" "state" {
  bucket = local.bucket_name
}

# Keep old versions of state files so a bad apply can be recovered
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# State files must never be public
resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_name" {
  description = "Paste this into the backend block in ../04-ec2-s3-backend/main.tf"
  value       = aws_s3_bucket.state.id
}
