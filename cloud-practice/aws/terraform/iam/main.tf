##############################################################################
# Locals + lookups
##############################################################################
locals {
  name = var.project
  tags = {
    Project   = var.project
    ManagedBy = "terraform"
    Module    = "aws/terraform/iam"
  }
}

data "aws_caller_identity" "current" {}

##############################################################################
# The resource everything below is scoped to -- one S3 bucket, so the
# group's and the role's permissions can be compared side by side against
# the exact same target.
##############################################################################
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_s3_bucket" "demo" {
  bucket = "${local.name}-${random_string.suffix.result}"
}

resource "aws_s3_bucket_public_access_block" "demo" {
  bucket                  = aws_s3_bucket.demo.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# A real object so the group's read-only policy has something to
# GetObject/ListBucket against immediately after apply.
resource "aws_s3_object" "seed" {
  bucket       = aws_s3_bucket.demo.id
  key          = "seed.txt"
  content      = "seeded by terraform apply\n"
  content_type = "text/plain"
}

##############################################################################
# Group path: Group -> (attached) Policy, User -> (member of) Group.
# The User never gets a policy directly -- this is the "assign permissions
# via groups, not individual users" pattern in practice, not just as advice.
##############################################################################
data "aws_iam_policy_document" "developer_readonly" {
  statement {
    sid       = "ReadOneBucket"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.demo.arn, "${aws_s3_bucket.demo.arn}/*"]
  }
}

resource "aws_iam_policy" "developer_readonly" {
  name        = "${local.name}-developer-readonly"
  description = "Read-only (GetObject + ListBucket) on the demo bucket. Nothing else."
  policy      = data.aws_iam_policy_document.developer_readonly.json
}

resource "aws_iam_group" "developers" {
  name = "${local.name}-developers"
}

resource "aws_iam_group_policy_attachment" "developers_readonly" {
  group      = aws_iam_group.developers.name
  policy_arn = aws_iam_policy.developer_readonly.arn
}

# Deliberately no aws_iam_access_key resource for this user -- see
# README.md "Why no access keys for this user." The group/policy wiring
# is still fully real and inspectable via `aws iam` even without minting
# long-lived credentials to prove it.
resource "aws_iam_user" "demo_user" {
  name = "${local.name}-demo-user"
}

resource "aws_iam_group_membership" "developers" {
  name  = "${local.name}-developers-membership"
  group = aws_iam_group.developers.name
  users = [aws_iam_user.demo_user.name]
}

##############################################################################
# Role path: a Role with its own two policies (trust + permission),
# deliberately narrower and DIFFERENT in shape from the group's policy --
# write-only, not read-only -- so assuming it and testing both an
# allowed and a denied call proves the boundary is real, not just declared.
#
# Trust policy: who can become this role. Trusts the identity currently
# running `terraform apply` (whatever IAM User/Role that is), purely so
# this same session can immediately `sts assume-role` it for verification
# -- a real deployment would trust a specific Role/service/account instead
# of "whoever happened to apply this."
##############################################################################
data "aws_iam_policy_document" "uploader_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = [data.aws_caller_identity.current.arn]
    }
  }
}

resource "aws_iam_role" "uploader" {
  name                 = "${local.name}-uploader"
  assume_role_policy   = data.aws_iam_policy_document.uploader_trust.json
  max_session_duration = 3600
}

# Permission policy: what the role can do once assumed. PutObject only --
# no s3:GetObject at all, so a read attempt with this role's temporary
# credentials is a genuine AccessDenied, not a contrived one.
data "aws_iam_policy_document" "uploader_permission" {
  statement {
    sid       = "WriteOnly"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.demo.arn}/*"]
  }
}

resource "aws_iam_policy" "uploader_permission" {
  name        = "${local.name}-uploader-permission"
  description = "Write-only (PutObject) on the demo bucket. No read, no list, no delete."
  policy      = data.aws_iam_policy_document.uploader_permission.json
}

resource "aws_iam_role_policy_attachment" "uploader" {
  role       = aws_iam_role.uploader.name
  policy_arn = aws_iam_policy.uploader_permission.arn
}
