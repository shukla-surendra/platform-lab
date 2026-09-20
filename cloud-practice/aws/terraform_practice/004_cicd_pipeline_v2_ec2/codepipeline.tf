# Wires Source -> Build -> Approval -> Deploy together. V2 pipeline.
#
# What V2 adds over 003's V1 (see 003_cicd_pipeline_ec2/LEARNINGS.md):
#   - pipeline-level `variable` blocks, overridable per run and referenced as
#     #{variables.NAME} in action configuration
#   - execution_mode (SUPERSEDED / QUEUED / PARALLEL)
#   - per-action-minute billing instead of a flat monthly fee

resource "random_id" "pipeline_bucket_suffix" {
  byte_length = 4
}

# force_destroy: 003's buckets were non-empty at teardown, so `terraform
# destroy` failed with BucketNotEmpty until emptied by hand. Artifacts here
# are disposable build output, so let destroy delete them.
resource "aws_s3_bucket" "pipeline_artifacts" {
  bucket        = "${local.name}-pipeline-${random_id.pipeline_bucket_suffix.hex}"
  force_destroy = true
}

resource "aws_iam_role" "pipeline" {
  name = "${local.name}-pipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "codepipeline.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# CodePipeline doesn't run your code — it calls StartBuild/CreateDeployment on
# the other services, so it needs "go" permission on each stage's service plus
# the artifact bucket, not the permissions those services need internally.
resource "aws_iam_role_policy" "pipeline" {
  name = "${local.name}-pipeline-policy"
  role = aws_iam_role.pipeline.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ArtifactBucket"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:GetBucketVersioning"]
        Resource = [aws_s3_bucket.pipeline_artifacts.arn, "${aws_s3_bucket.pipeline_artifacts.arn}/*"]
      },
      {
        Sid    = "CodeCommit"
        Effect = "Allow"
        Action = [
          "codecommit:GetBranch", "codecommit:GetCommit", "codecommit:UploadArchive",
          "codecommit:GetUploadArchiveStatus", "codecommit:CancelUploadArchive",
        ]
        Resource = [aws_codecommit_repository.app.arn]
      },
      {
        Sid      = "CodeBuild"
        Effect   = "Allow"
        Action   = ["codebuild:BatchGetBuilds", "codebuild:StartBuild"]
        Resource = [aws_codebuild_project.app.arn]
      },
      {
        Sid    = "CodeDeploy"
        Effect = "Allow"
        Action = [
          "codedeploy:CreateDeployment", "codedeploy:GetApplication", "codedeploy:GetApplicationRevision",
          "codedeploy:GetDeployment", "codedeploy:GetDeploymentConfig", "codedeploy:RegisterApplicationRevision",
        ]
        Resource = ["*"] # kept as in 003 so the only differences are V2 features + bug fixes; scoping this down is a follow-up
      },
    ]
  })
}

resource "aws_codepipeline" "app" {
  name           = local.name
  role_arn       = aws_iam_role.pipeline.arn
  pipeline_type  = "V2"
  execution_mode = "SUPERSEDED" # a newer run replaces older ones waiting at a stage; alternatives: QUEUED, PARALLEL

  artifact_store {
    location = aws_s3_bucket.pipeline_artifacts.bucket
    type     = "S3"
  }

  # Pipeline-level variables — V2 only. Override per run with:
  #   aws codepipeline start-pipeline-execution --name <p> --variables name=DEPLOY_NOTE,value="..."
  variable {
    name          = "DEPLOY_NOTE"
    default_value = "none"
    description   = "Free-text note stamped into the deployed page by buildspec.yml."
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeCommit"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        RepositoryName       = aws_codecommit_repository.app.repository_name
        BranchName           = var.branch_name
        PollForSourceChanges = "false" # push-triggered via the EventBridge rule below
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
        ProjectName = aws_codebuild_project.app.name

        # Pipeline variable -> CodeBuild environment variable.
        EnvironmentVariables = jsonencode([
          { name = "DEPLOY_NOTE", value = "#{variables.DEPLOY_NOTE}", type = "PLAINTEXT" },
        ])
      }
    }
  }

  # Manual gate — the pipeline pauses until someone approves or rejects.
  # Stage order in this file IS execution order. Unactioned approvals expire
  # after 7 days and count as a failure. Manual approval is not billed in V2.
  stage {
    name = "Approval"

    action {
      name     = "ApproveDeploy"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"

      configuration = {
        CustomData = "Build succeeded for ${local.name}. Approve to deploy to the EC2 target, or reject to stop this run."
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
        ApplicationName     = aws_codedeploy_app.app.name
        DeploymentGroupName = aws_codedeploy_deployment_group.app.deployment_group_name
      }
    }
  }
}

# --- Push trigger -----------------------------------------------------------
# V2's `trigger` block (branch/tag/path filters) can't be used with CodeCommit:
# the CreatePipeline API's only allowed trigger providerType is
# "CodeStarSourceConnection" (GitHub etc.). So a push starts the pipeline the
# classic way: an EventBridge rule on CodeCommit's branch-updated event.
# Measured: push at 11:52:22 -> execution started 11:52:38 (~16s).

resource "aws_iam_role" "events" {
  name = "${local.name}-events-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "events" {
  name = "${local.name}-events-policy"
  role = aws_iam_role.events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["codepipeline:StartPipelineExecution"]
      Resource = [aws_codepipeline.app.arn]
    }]
  })
}

resource "aws_cloudwatch_event_rule" "push" {
  name        = "${local.name}-push"
  description = "Start the pipeline when ${var.branch_name} is created or updated in the repo."

  event_pattern = jsonencode({
    source        = ["aws.codecommit"]
    "detail-type" = ["CodeCommit Repository State Change"]
    resources     = [aws_codecommit_repository.app.arn]
    detail = {
      event         = ["referenceCreated", "referenceUpdated"]
      referenceType = ["branch"]
      referenceName = [var.branch_name]
    }
  })
}

resource "aws_cloudwatch_event_target" "push" {
  rule     = aws_cloudwatch_event_rule.push.name
  arn      = aws_codepipeline.app.arn
  role_arn = aws_iam_role.events.arn
}
