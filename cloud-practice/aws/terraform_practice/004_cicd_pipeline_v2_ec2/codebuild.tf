# Turns source into a build artifact.
#
# Differences from 003:
#   - source/artifacts type is CODEPIPELINE: the pipeline hands CodeBuild the
#     source and collects the output through ITS artifact bucket. 003 used
#     CODECOMMIT + S3 with a second, separate bucket that the pipeline never
#     actually used. (Trade-off: `aws codebuild start-build` no longer works
#     standalone — builds run from the pipeline.)
#   - the log group is created here, so the role needs no logs:CreateLogGroup.

resource "aws_cloudwatch_log_group" "codebuild" {
  name              = "/aws/codebuild/${local.name}"
  retention_in_days = 7
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
        Resource = [aws_cloudwatch_log_group.codebuild.arn, "${aws_cloudwatch_log_group.codebuild.arn}:*"]
      },
      {
        # Source zip in, build output out — both via the pipeline's bucket.
        Sid      = "PipelineArtifactBucket"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:GetBucketLocation", "s3:GetBucketAcl"]
        Resource = [aws_s3_bucket.pipeline_artifacts.arn, "${aws_s3_bucket.pipeline_artifacts.arn}/*"]
      },
    ]
  })
}

resource "aws_codebuild_project" "app" {
  name         = local.name
  description  = "Build stage — runs buildspec.yml from the repo root."
  service_role = aws_iam_role.codebuild.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"
  }

  source {
    type = "CODEPIPELINE"
    # No `buildspec` argument -> reads buildspec.yml from the source root.
  }

  depends_on = [aws_cloudwatch_log_group.codebuild]
}
