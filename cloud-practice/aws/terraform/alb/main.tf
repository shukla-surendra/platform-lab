locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/alb"
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

##############################################################################
# Security group — the ALB itself only needs 80 open to the internet;
# instances behind it should restrict THEIR security group to only this one.
##############################################################################
resource "aws_security_group" "alb" {
  name        = "${local.name}-sg"
  description = "ALB: HTTP in from anywhere, all out"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
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
# Load balancer + target group + listener
##############################################################################
resource "aws_lb" "this" {
  name               = local.name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.all_in_vpc.ids

  tags = { Name = local.name }
}

resource "aws_lb_target_group" "this" {
  name        = "${local.name}-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "instance"

  health_check {
    path                = var.health_check_path
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 15
    timeout             = 5
    matcher             = "200-399"
  }

  # Lets CodeDeploy/ASG replace instances behind this TG without the ALB
  # cutting them off mid-request.
  deregistration_delay = 30

  tags = { Name = "${local.name}-tg" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
}
