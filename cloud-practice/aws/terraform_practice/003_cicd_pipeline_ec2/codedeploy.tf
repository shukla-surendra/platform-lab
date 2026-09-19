# STEP 3 — teach AWS how to deploy onto the Step 1 instance.

resource "aws_iam_role" "codedeploy" {
  name = "${local.name}-codedeploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "codedeploy.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# AWS-managed policy — covers every EC2/ASG describe+modify permission
# CodeDeploy needs internally.
resource "aws_iam_role_policy_attachment" "codedeploy" {
  role       = aws_iam_role.codedeploy.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole"
}

resource "aws_codedeploy_app" "app" {
  name             = local.name
  compute_platform = "Server" # EC2/On-Premises — not ECS, not Lambda
}

resource "aws_codedeploy_deployment_group" "app" {
  app_name               = aws_codedeploy_app.app.name
  deployment_group_name  = "${local.name}-dg"
  service_role_arn       = aws_iam_role.codedeploy.arn
  deployment_config_name = "CodeDeployDefault.AllAtOnce" # one instance in this exercise — OneAtATime vs AllAtOnce is moot until there's more than one

  # Targets by TAG, never by instance ID — that's what lets the underlying
  # instance be replaced later without touching this resource.
  ec2_tag_set {
    ec2_tag_filter {
      key   = "Name"
      type  = "KEY_AND_VALUE"
      value = local.name # MUST match ec2.tf's aws_instance.target tags.Name
    }
  }

  deployment_style {
    deployment_option = "WITHOUT_TRAFFIC_CONTROL" # no load balancer in this exercise
    deployment_type   = "IN_PLACE"
  }

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE"]
  }
}
