locals {
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/s3-kms"
    },
    var.extra_tags,
  )
}

data "aws_caller_identity" "current" {}

resource "random_id" "suffix" {
  byte_length = 4
}

##############################################################################
# Customer-managed KMS key (CMK)
#
# Versus SSE-S3 (s3/): you own the key policy, get a CloudTrail record of
# every Decrypt/GenerateDataKey call, can disable the key to instantly cut
# off access to all data, and can grant/deny per principal. Cost: $1/month
# per key + a small per-request charge (largely erased by bucket keys below).
##############################################################################
data "aws_iam_policy_document" "key" {
  # Without this statement nobody (not even the account) could ever fix the
  # key policy, and IAM policies would have no effect on the key. Granting the
  # root principal is what DELEGATES access decisions to IAM.
  statement {
    sid       = "EnableIamPolicies"
    actions   = ["kms:*"]
    resources = ["*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }

  dynamic "statement" {
    for_each = length(var.key_admin_arns) > 0 ? [1] : []
    content {
      sid = "KeyAdministrators"
      actions = [
        "kms:Create*",
        "kms:Describe*",
        "kms:Enable*",
        "kms:List*",
        "kms:Put*",
        "kms:Update*",
        "kms:Revoke*",
        "kms:Disable*",
        "kms:Get*",
        "kms:Delete*",
        "kms:TagResource",
        "kms:UntagResource",
        "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion",
      ]
      resources = ["*"]
      principals {
        type        = "AWS"
        identifiers = var.key_admin_arns
      }
    }
  }

  dynamic "statement" {
    for_each = length(var.key_user_arns) > 0 ? [1] : []
    content {
      sid = "KeyUsers"
      actions = [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey",
      ]
      resources = ["*"]
      principals {
        type        = "AWS"
        identifiers = var.key_user_arns
      }
    }
  }
}

resource "aws_kms_key" "this" {
  description             = "${var.project} — SSE-KMS key for the ${var.project} bucket"
  enable_key_rotation     = var.enable_key_rotation
  deletion_window_in_days = var.kms_deletion_window_days
  policy                  = data.aws_iam_policy_document.key.json
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.project}"
  target_key_id = aws_kms_key.this.key_id
}

##############################################################################
# Bucket — private, versioned, default-encrypted with the CMK
##############################################################################
resource "aws_s3_bucket" "this" {
  bucket        = "${var.project}-${random_id.suffix.hex}"
  force_destroy = var.force_destroy
}

# ACLs off; the bucket owner owns every object regardless of who uploaded it.
resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = var.versioning_enabled ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.this.arn
    }
    # One data key is reused for many objects instead of one KMS call per
    # object — cuts KMS request cost/throttling by up to ~99%. The tradeoff
    # is CloudTrail shows bucket-level rather than per-object KMS events.
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  count  = var.enable_lifecycle_rules ? 1 : 0
  bucket = aws_s3_bucket.this.id

  rule {
    id     = "noncurrent-version-cleanup"
    status = "Enabled"

    filter {}

    noncurrent_version_transition {
      noncurrent_days = var.noncurrent_version_transition_days
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Lifecycle rules need versioning configured first on a versioned bucket.
  depends_on = [aws_s3_bucket_versioning.this]
}

##############################################################################
# Bucket policy — guardrails that hold even if an IAM policy is too generous
##############################################################################
data "aws_iam_policy_document" "bucket" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.this.arn, "${aws_s3_bucket.this.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  # "IfExists" on purpose: an upload that OMITS the encryption headers is
  # fine (the bucket default applies the CMK); an upload that EXPLICITLY asks
  # for AES256 (SSE-S3) or a different KMS key is rejected.
  statement {
    sid       = "DenyWrongEncryptionAlgorithm"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.this.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEqualsIfExists"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["aws:kms"]
    }
  }

  # NOTE: this compares the header string literally, so callers that pass an
  # alias or bare key ID via --sse-kms-key-id are denied — pass the key ARN
  # (see the `kms_key_arn` output) or omit the header and use the default.
  statement {
    sid       = "DenyWrongKmsKey"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.this.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEqualsIfExists"
      variable = "s3:x-amz-server-side-encryption-aws-kms-key-id"
      values   = [aws_kms_key.this.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "this" {
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.bucket.json

  # Avoids a race between the public-access-block and policy updates.
  depends_on = [aws_s3_bucket_public_access_block.this]
}

##############################################################################
# Ready-made IAM policy for any role/user that should read+write this bucket.
# Attach it yourself (e.g. to a Lambda/Glue/EC2 role) — it is only rendered
# as an output here, nothing is attached.
##############################################################################
data "aws_iam_policy_document" "consumer" {
  statement {
    sid       = "ListBucket"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.this.arn]
  }
  statement {
    sid       = "ReadWriteObjects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload"]
    resources = ["${aws_s3_bucket.this.arn}/*"]
  }
  statement {
    sid       = "UseTheKey"
    actions   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
    resources = [aws_kms_key.this.arn]
  }
}
