# STEP 4 — turn source into a build artifact.

resource "random_id" "codebuild_bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "codebuild_artifacts" {
  bucket = "${local.name}-codebuild-${random_id.codebuild_bucket_suffix.hex}"
}

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
    Statement = [
      {
        Sid      = "Logs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = ["arn:aws:logs:${var.region}:*:log-group:/aws/codebuild/${local.name}:*"]
      },
      {
        Sid      = "ArtifactBucket"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:GetBucketLocation"]
        Resource = [aws_s3_bucket.codebuild_artifacts.arn, "${aws_s3_bucket.codebuild_artifacts.arn}/*"]
      },
      {
        Sid      = "CodeCommitPull"
        Effect   = "Allow"
        Action   = ["codecommit:GitPull"]
        Resource = [aws_codecommit_repository.app.arn]
      },
    ]
  })
}

resource "aws_codebuild_project" "app" {
  name         = local.name
  description  = "Build stage — runs buildspec.yml from the repo root."
  service_role = aws_iam_role.codebuild.arn

  artifacts {
    type      = "S3"
    location  = aws_s3_bucket.codebuild_artifacts.bucket
    packaging = "ZIP"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"
  }

  source {
    type     = "CODECOMMIT"
    location = aws_codecommit_repository.app.clone_url_http
    # No `buildspec` argument -> reads buildspec.yml from the repo root
    # (appspec-sample/buildspec.yml, once you've pushed it — see README.md).
  }
}
