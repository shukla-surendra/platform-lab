locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/ecs-fargate"
    },
    var.extra_tags,
  )
  attach_to_lb = var.target_group_arn != ""
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

##############################################################################
# Cluster + log group
##############################################################################
resource "aws_ecs_cluster" "this" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "tasks" {
  name              = "/ecs/${local.name}"
  retention_in_days = 14
}

##############################################################################
# Security group — container port from the ALB (if attached) or the internet
##############################################################################
resource "aws_security_group" "service" {
  name        = "${local.name}-sg"
  description = "ECS service: container port in, all out"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Container port"
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # restrict to the ALB's SG once attached, in a real deployment
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-sg" }
}

##############################################################################
# IAM — task EXECUTION role (ECS agent: pull image, ship logs) vs. task role
# (your application's own AWS permissions, e.g. reading from S3/DynamoDB —
# empty here on purpose, add policies as your app actually needs them).
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

resource "aws_iam_role" "task" {
  name = "${local.name}-task-role"
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
# Task definition + service
##############################################################################
resource "aws_ecs_task_definition" "this" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = local.name
    image     = var.container_image
    essential = true
    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.tasks.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "this" {
  name            = local.name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  # Rolling deployment: ECS's native equivalent of CodeDeploy's OneAtATime —
  # replaces tasks gradually and only proceeds while the minimum stays healthy.
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 50

  network_configuration {
    subnets          = data.aws_subnets.all_in_vpc.ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = local.attach_to_lb ? false : var.assign_public_ip
  }

  dynamic "load_balancer" {
    for_each = local.attach_to_lb ? [1] : []
    content {
      target_group_arn = var.target_group_arn
      container_name   = local.name
      container_port   = var.container_port
    }
  }
}
