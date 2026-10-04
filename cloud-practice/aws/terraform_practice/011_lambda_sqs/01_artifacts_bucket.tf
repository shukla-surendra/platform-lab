# ---------------------------------------------------------------------------
# STEP 1: S3 bucket that holds the Lambda deployment package (the .zip)
# ---------------------------------------------------------------------------
# Lambda can load its code from S3. Keeping every build here gives you a
# history of deployable artifacts.

# S3 bucket names are global; add a random suffix so the name is unique
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.project}-artifacts-${random_id.suffix.hex}"

  # LAB ONLY: lets `terraform destroy` delete the bucket even if it has objects
  force_destroy = true
}

# Versioning: every upload of the same key keeps the old version.
# Lambda is pointed at a specific object VERSION, so a new upload = new version.
resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Never public
resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
