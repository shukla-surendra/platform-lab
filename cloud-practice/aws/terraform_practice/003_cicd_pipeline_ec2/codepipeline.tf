# STEP 5 — wire Source -> Build -> Deploy together.

resource "random_id" "pipeline_bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "pipeline_artifacts" {
  bucket = "${local.name}-pipeline-${random_id.pipeline_bucket_suffix.hex}"
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

# CodePipeline itself doesn't run your code — it just calls
# StartBuild/CreateDeployment on resources already built in the other
# files, so it needs "go" permission on each stage's service PLUS the
# artifact bucket, NOT the permissions those services need internally
# (that's codebuild.tf's and codedeploy.tf's OWN roles).
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
        Resource = ["*"] # CodeDeploy's ARNs span app/deployment-group/config — a good follow-up exercise to scope this down
      },
    ]
  })
}

resource "aws_codepipeline" "app" {
  name     = local.name
  role_arn = aws_iam_role.pipeline.arn

  artifact_store {
    location = aws_s3_bucket.pipeline_artifacts.bucket
    type     = "S3"
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
        PollForSourceChanges = "true" # simplest to start; see README.md's push-triggered upgrade for the no-polling version
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
      input_artifacts  = ["source_output"] # MUST match Source's output_artifacts name
      output_artifacts = ["build_output"]

      configuration = {
        ProjectName = aws_codebuild_project.app.name
      }
    }
  }

  # Manual gate — the pipeline pauses here until someone approves or rejects
  # (console, or `aws codepipeline put-approval-result`). Stage order in this
  # file IS execution order, so this must stay between Build and Deploy.
  # Unactioned approvals expire after 7 days and count as a failure.
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
      input_artifacts = ["build_output"] # MUST match Build's output_artifacts name

      configuration = {
        ApplicationName     = aws_codedeploy_app.app.name
        DeploymentGroupName = aws_codedeploy_deployment_group.app.deployment_group_name
      }
    }
  }
}
