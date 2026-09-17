locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/codedeploy"
    },
    var.extra_tags,
  )

  create_bucket = var.artifact_bucket_name == ""
  bucket_name   = local.create_bucket ? aws_s3_bucket.revisions[0].bucket : var.artifact_bucket_name
}

resource "random_id" "suffix" {
  count       = local.create_bucket ? 1 : 0
  byte_length = 4
}

##############################################################################
# Revision bucket (only if the caller didn't pass one in)
##############################################################################
resource "aws_s3_bucket" "revisions" {
  count  = local.create_bucket ? 1 : 0
  bucket = "${local.name}-revisions-${random_id.suffix[0].hex}"
}

resource "aws_s3_bucket_versioning" "revisions" {
  count  = local.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.revisions[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

##############################################################################
# IAM role — the AWS-managed AWSCodeDeployRole policy covers EC2/ASG/ELB
# read+modify permissions CodeDeploy needs to orchestrate a deployment.
##############################################################################
resource "aws_iam_role" "codedeploy" {
  name = "${local.name}-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "codedeploy.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "codedeploy_managed" {
  role       = aws_iam_role.codedeploy.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole"
}

##############################################################################
# Application + Deployment Group
##############################################################################
resource "aws_codedeploy_app" "this" {
  name             = local.name
  compute_platform = "Server" # EC2/On-Premises — for containers use "ECS", for Lambda use "Lambda"
}

resource "aws_codedeploy_deployment_group" "this" {
  app_name              = aws_codedeploy_app.this.name
  deployment_group_name = "${local.name}-dg"
  service_role_arn      = aws_iam_role.codedeploy.arn

  deployment_config_name = var.deployment_config_name
  autoscaling_groups     = var.asg_names

  deployment_style {
    deployment_option = var.target_group_name != "" ? "WITH_TRAFFIC_CONTROL" : "WITHOUT_TRAFFIC_CONTROL"
    deployment_type   = "IN_PLACE"
  }

  dynamic "load_balancer_info" {
    for_each = var.target_group_name != "" ? [1] : []
    content {
      target_group_info {
        name = var.target_group_name
      }
    }
  }

  auto_rollback_configuration {
    enabled = var.auto_rollback_on_failure
    events  = var.auto_rollback_on_failure ? ["DEPLOYMENT_FAILURE"] : []
  }

  # OneAtATime/HalfAtATime/AllAtOnce (deployment_config_name) already caps
  # HOW MANY instances get the new revision concurrently. This block adds a
  # separate ceiling on how many can be simultaneously UNHEALTHY before
  # CodeDeploy stops the whole deployment outright.
  alarm_configuration {
    enabled = false # wire a CloudWatch alarm ARN here in a real deployment (see cloudwatch/)
  }
}
