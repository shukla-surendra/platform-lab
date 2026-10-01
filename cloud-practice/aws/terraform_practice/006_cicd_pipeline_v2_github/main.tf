# Minimal CodePipeline V2: GitHub (via CodeConnection) -> CodeBuild.
# Read README.md for the setup steps and the flow.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "github_repo" {
  description = "GitHub repo as owner/name, e.g. surendra/pipeline-dummy-repo"
  type        = string
}

variable "branch" {
  type    = string
  default = "main"
}

locals {
  name = "gh-pipeline-v2"
}

# 1. GitHub connection. Created as PENDING — you must click
#    "Update pending connection" once in the console to authorize GitHub.
resource "aws_codestarconnections_connection" "github" {
  name          = local.name
  provider_type = "GitHub"
}

# 2. S3 bucket where the pipeline passes artifacts between stages
#    (Source zips the repo here, Build reads it from here).
resource "aws_s3_bucket" "artifacts" {
  bucket_prefix = "${local.name}-"
  force_destroy = true
}

# 3. CodeBuild: runs buildspec.yml from the repo.
resource "aws_iam_role" "codebuild" {
  name = "${local.name}-codebuild"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "codebuild.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "codebuild" {
  role = aws_iam_role.codebuild.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "*" },
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = "${aws_s3_bucket.artifacts.arn}/*" },
    ]
  })
}

resource "aws_codebuild_project" "build" {
  name         = local.name
  service_role = aws_iam_role.codebuild.arn

  source { type = "CODEPIPELINE" } # source comes from the pipeline, buildspec.yml from the repo root
  artifacts { type = "CODEPIPELINE" }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/amazonlinux-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"
  }
}

# 4. CodePipeline: only needs permission to use the connection, start the
#    build, and read/write the artifact bucket.
resource "aws_iam_role" "pipeline" {
  name = "${local.name}-pipeline"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "codepipeline.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "pipeline" {
  role = aws_iam_role.pipeline.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["codestar-connections:UseConnection", "codeconnections:UseConnection"], Resource = aws_codestarconnections_connection.github.arn },
      { Effect = "Allow", Action = ["codebuild:StartBuild", "codebuild:BatchGetBuilds"], Resource = aws_codebuild_project.build.arn },
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:GetBucketVersioning"], Resource = [aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"] },
    ]
  })
}

resource "aws_codepipeline" "this" {
  name          = local.name
  role_arn      = aws_iam_role.pipeline.arn
  pipeline_type = "V2"

  artifact_store {
    type     = "S3"
    location = aws_s3_bucket.artifacts.bucket
  }

  # V2-only: start on push to the branch (no webhook/EventBridge to manage).
  trigger {
    provider_type = "CodeStarSourceConnection"
    git_configuration {
      source_action_name = "Source"
      push {
        branches { includes = [var.branch] }
      }
    }
  }

  stage {
    name = "Source"
    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]
      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.github.arn
        FullRepositoryId = var.github_repo
        BranchName       = var.branch
      }
    }
  }

  stage {
    name = "Build"
    action {
      name            = "Build"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = "1"
      input_artifacts = ["source_output"]
      configuration   = { ProjectName = aws_codebuild_project.build.name }
    }
  }

  # Manual gate: the pipeline pauses here until someone clicks Approve/Reject
  # in the console. Unanswered approvals expire after 7 days (= failed run).
  # No IAM needed on the pipeline role — the human approving needs
  # codepipeline:PutApprovalResult.
  stage {
    name = "Approval"
    action {
      name     = "Approve"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"
      configuration = {
        CustomData = "Build passed. Approve to continue, reject to stop this run."
      }
    }
  }
}

output "connection_status" {
  value = aws_codestarconnections_connection.github.connection_status
}

output "pipeline_url" {
  value = "https://us-east-1.console.aws.amazon.com/codesuite/codepipeline/pipelines/${aws_codepipeline.this.name}/view"
}
