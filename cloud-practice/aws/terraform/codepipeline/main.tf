locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/codepipeline"
    },
    var.extra_tags,
  )
}

resource "random_id" "suffix" {
  byte_length = 4
}

##############################################################################
# Artifact bucket — every stage's output lands here for the next stage to pick up
##############################################################################
resource "aws_s3_bucket" "artifacts" {
  bucket = "${local.name}-artifacts-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

##############################################################################
# IAM role — CodePipeline itself doesn't run your code; it just calls
# StartBuild/CreateDeployment on the projects you already built, so it
# needs read/write on the artifact bucket plus "go" permission on each
# stage's service, NOT the permissions those services need internally
# (those live in codebuild/'s and codedeploy/'s OWN roles).
##############################################################################
resource "aws_iam_role" "pipeline" {
  name = "${local.name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "codepipeline.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "pipeline" {
  name = "${local.name}-policy"
  role = aws_iam_role.pipeline.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Sid    = "ArtifactBucket"
        Effect = "Allow"
        Action = [
          "s3:GetObject", "s3:GetObjectVersion", "s3:PutObject",
          "s3:GetBucketVersioning", "s3:GetBucketLocation",
        ]
        Resource = [aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"]
      },
      {
        Sid      = "CodeBuild"
        Effect   = "Allow"
        Action   = ["codebuild:BatchGetBuilds", "codebuild:StartBuild"]
        Resource = ["arn:aws:codebuild:${var.region}:*:project/${var.codebuild_project_name}"]
      },
      {
        Sid    = "CodeDeploy"
        Effect = "Allow"
        Action = [
          "codedeploy:CreateDeployment", "codedeploy:GetApplication", "codedeploy:GetApplicationRevision",
          "codedeploy:GetDeployment", "codedeploy:GetDeploymentConfig", "codedeploy:RegisterApplicationRevision",
        ]
        Resource = ["*"] # CodeDeploy's fine-grained ARNs are awkward across app/deployment-group/config; scope down in a real prod role
      },
      ],
      var.source_type == "CODECOMMIT" ? [{
        Sid      = "CodeCommit"
        Effect   = "Allow"
        Action   = ["codecommit:GetBranch", "codecommit:GetCommit", "codecommit:UploadArchive", "codecommit:GetUploadArchiveStatus", "codecommit:CancelUploadArchive"]
        Resource = ["arn:aws:codecommit:${var.region}:*:${var.codecommit_repository_name}"]
        }] : [{
        Sid      = "CodeStarConnection"
        Effect   = "Allow"
        Action   = ["codestar-connections:UseConnection"]
        Resource = [var.codestar_connection_arn]
      }]
    )
  })
}

##############################################################################
# The pipeline: Source -> Build -> Deploy
##############################################################################
resource "aws_codepipeline" "this" {
  name     = local.name
  role_arn = aws_iam_role.pipeline.arn

  artifact_store {
    location = aws_s3_bucket.artifacts.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = var.source_type == "CODECOMMIT" ? "CodeCommit" : "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = var.source_type == "CODECOMMIT" ? {
        RepositoryName       = var.codecommit_repository_name
        BranchName           = var.branch_name
        PollForSourceChanges = "false" # EventBridge rule below triggers on push instead of polling
        } : {
        ConnectionArn    = var.codestar_connection_arn
        FullRepositoryId = var.github_full_repository_id
        BranchName       = var.branch_name
      }
    }
  }

  stage {
    name = "Build"

    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      version          = "1"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]

      configuration = {
        ProjectName = var.codebuild_project_name
      }
    }
  }

  stage {
    name = "Deploy"

    action {
      name            = "Deploy"
      category        = "Deploy"
      owner           = "AWS"
      provider        = "CodeDeploy"
      version         = "1"
      input_artifacts = ["build_output"]

      configuration = {
        ApplicationName     = var.codedeploy_application_name
        DeploymentGroupName = var.codedeploy_deployment_group_name
      }
    }
  }

  tags = local.tags
}

##############################################################################
# Push-triggered instead of polled: EventBridge rule on CodeCommit
# referenceUpdated -> starts the pipeline execution directly.
##############################################################################
resource "aws_iam_role" "eventbridge" {
  count = var.source_type == "CODECOMMIT" ? 1 : 0
  name  = "${local.name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge" {
  count = var.source_type == "CODECOMMIT" ? 1 : 0
  name  = "${local.name}-eventbridge-policy"
  role  = aws_iam_role.eventbridge[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "codepipeline:StartPipelineExecution"
      Resource = aws_codepipeline.this.arn
    }]
  })
}

resource "aws_cloudwatch_event_rule" "on_push" {
  count       = var.source_type == "CODECOMMIT" ? 1 : 0
  name        = "${local.name}-on-push"
  description = "Starts ${local.name} whenever ${var.branch_name} is pushed to ${var.codecommit_repository_name}."

  event_pattern = jsonencode({
    source        = ["aws.codecommit"]
    "detail-type" = ["CodeCommit Repository State Change"]
    resources     = ["arn:aws:codecommit:${var.region}:*:${var.codecommit_repository_name}"]
    detail = {
      event         = ["referenceCreated", "referenceUpdated"]
      referenceType = ["branch"]
      referenceName = [var.branch_name]
    }
  })
}

resource "aws_cloudwatch_event_target" "start_pipeline" {
  count    = var.source_type == "CODECOMMIT" ? 1 : 0
  rule     = aws_cloudwatch_event_rule.on_push[0].name
  arn      = aws_codepipeline.this.arn
  role_arn = aws_iam_role.eventbridge[0].arn
}
