locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/batch"
    },
    var.extra_tags,
  )
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "all_in_vpc" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Fargate-type compute environments are driven by a service-linked role
# rather than a role you attach a policy to. NOTE: if this account has
# EVER used AWS Batch before, AWSServiceRoleForBatch already exists and
# this resource's first apply fails with "has been taken in this account"
# — see README for the one-line `terraform import` fix.
resource "aws_iam_service_linked_role" "batch" {
  aws_service_name = "batch.amazonaws.com"
}

resource "aws_security_group" "batch" {
  name        = "${local.name}-sg"
  description = "Batch Fargate jobs: no inbound needed, all outbound (pull image, ship logs)"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-sg" }
}

resource "aws_cloudwatch_log_group" "jobs" {
  name              = "/aws/batch/${local.name}"
  retention_in_days = 14
}

##############################################################################
# Compute environment — MANAGED + FARGATE means AWS Batch provisions and
# tears down the underlying Fargate capacity per-job; there's no EC2 fleet
# to size or patch, similar to ecs-fargate/ but job-oriented instead of
# long-running-service-oriented.
##############################################################################
resource "aws_batch_compute_environment" "this" {
  compute_environment_name = local.name
  type                     = "MANAGED"

  compute_resources {
    type               = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    max_vcpus          = var.max_vcpus
    subnets            = data.aws_subnets.all_in_vpc.ids
    security_group_ids = [aws_security_group.batch.id]
  }

  depends_on = [aws_iam_service_linked_role.batch]
}

resource "aws_batch_job_queue" "this" {
  name     = local.name
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.this.arn
  }
}

##############################################################################
# IAM — execution role (Batch/ECS agent: pull image, ship logs) vs. job role
# (your job's own AWS permissions — empty by default, same split as ecs-fargate/)
##############################################################################
resource "aws_iam_role" "execution" {
  name = "${local.name}-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "job" {
  name = "${local.name}-job-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

##############################################################################
# Job definition
##############################################################################
resource "aws_batch_job_definition" "this" {
  name                  = local.name
  type                  = "container"
  platform_capabilities = ["FARGATE"]

  container_properties = jsonencode({
    image            = var.container_image
    command          = var.command
    executionRoleArn = aws_iam_role.execution.arn
    jobRoleArn       = aws_iam_role.job.arn
    resourceRequirements = [
      { type = "VCPU", value = var.vcpus },
      { type = "MEMORY", value = var.memory_mib },
    ]
    networkConfiguration = {
      assignPublicIp = "ENABLED" # default VPC subnets are public; a real VPC would use a private subnet + NAT instead
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.jobs.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "batch"
      }
    }
  })
}
