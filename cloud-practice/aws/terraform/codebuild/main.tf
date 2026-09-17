locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/codebuild"
    },
    var.extra_tags,
  )

  create_bucket = var.artifact_bucket_name == ""
  bucket_name   = local.create_bucket ? aws_s3_bucket.artifacts[0].bucket : var.artifact_bucket_name
}

resource "random_id" "suffix" {
  count       = local.create_bucket ? 1 : 0
  byte_length = 4
}

##############################################################################
# Artifact bucket (only if the caller didn't pass one in)
##############################################################################
resource "aws_s3_bucket" "artifacts" {
  count  = local.create_bucket ? 1 : 0
  bucket = "${local.name}-artifacts-${random_id.suffix[0].hex}"
}

resource "aws_s3_bucket_versioning" "artifacts" {
  count  = local.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.artifacts[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  count  = local.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.artifacts[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

##############################################################################
# CloudWatch Logs group for the build output
##############################################################################
resource "aws_cloudwatch_log_group" "build" {
  name              = "/aws/codebuild/${local.name}"
  retention_in_days = 14
}

##############################################################################
# IAM role — least-privilege-ish: logs, artifact bucket, and (if CODECOMMIT)
# git pull permission
##############################################################################
resource "aws_iam_role" "codebuild" {
  name = "${local.name}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "codebuild.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "codebuild" {
  name = "${local.name}-codebuild-policy"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = [
          "${aws_cloudwatch_log_group.build.arn}:*",
        ]
      },
      {
        Sid      = "ArtifactBucket"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:GetBucketAcl", "s3:GetBucketLocation"]
        Resource = ["arn:aws:s3:::${local.bucket_name}", "arn:aws:s3:::${local.bucket_name}/*"]
      },
      ],
      var.source_type == "CODECOMMIT" ? [{
        Sid      = "CodeCommitPull"
        Effect   = "Allow"
        Action   = ["codecommit:GitPull"]
        Resource = ["arn:aws:codecommit:${var.region}:*:${local.name}"]
      }] : []
    )
  })
}

##############################################################################
# The CodeBuild project itself
##############################################################################
resource "aws_codebuild_project" "this" {
  name          = local.name
  description   = "Managed by Terraform — the build stage of the CI/CD lab."
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 15

  artifacts {
    type      = var.source_type == "NO_SOURCE" ? "NO_ARTIFACTS" : "S3"
    location  = var.source_type == "NO_SOURCE" ? null : local.bucket_name
    packaging = var.source_type == "NO_SOURCE" ? null : "ZIP"
  }

  environment {
    compute_type    = var.compute_type
    image           = var.build_image
    type            = "LINUX_CONTAINER"
    privileged_mode = var.privileged_mode
  }

  source {
    type      = var.source_type
    buildspec = var.buildspec
    location = (
      var.source_type == "CODECOMMIT" ? var.codecommit_clone_url :
      var.source_type == "GITHUB" ? var.github_repo_url :
      null
    )
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.build.name
    }
  }

  tags = local.tags
}
