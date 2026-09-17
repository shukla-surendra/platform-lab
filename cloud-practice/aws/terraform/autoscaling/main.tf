locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/autoscaling"
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

data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

##############################################################################
# Security group + IAM (SSM only, no SSH key — same pattern as ec2/)
##############################################################################
resource "aws_security_group" "this" {
  name        = "${local.name}-sg"
  description = "ASG instances: HTTP in, all out"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # in real life: restrict to the ALB's security group instead
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-sg" }
}

resource "aws_iam_role" "instance" {
  name = "${local.name}-instance-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# CodeDeploy needs the CodeDeploy agent on the box and permission for the
# agent to pull deployment bundles from S3 — attach it here so this ASG is
# ready to be a codedeploy/ target with no extra role wiring.
resource "aws_iam_role_policy_attachment" "s3_read_only" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_instance_profile" "instance" {
  name = "${local.name}-instance-profile"
  role = aws_iam_role.instance.name
}

##############################################################################
# Launch template — installs httpd + the CodeDeploy agent at boot
##############################################################################
resource "aws_launch_template" "this" {
  name_prefix   = "${local.name}-"
  image_id      = data.aws_ssm_parameter.al2023.value
  instance_type = var.instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.instance.name
  }

  vpc_security_group_ids = [aws_security_group.this.id]

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = 8
      volume_type = "gp3"
      encrypted   = true
    }
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    dnf -y install httpd ruby wget
    echo "<h1>${local.name} — $(hostname) — v1</h1>" > /var/www/html/index.html
    systemctl enable --now httpd

    # CodeDeploy agent (Amazon Linux 2023 uses the same installer as AL2)
    cd /tmp
    wget -q https://aws-codedeploy-${var.region}.s3.${var.region}.amazonaws.com/latest/install
    chmod +x ./install
    ./install auto
    systemctl enable --now codedeploy-agent
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags          = merge(local.tags, { Name = local.name })
  }
}

##############################################################################
# Auto Scaling Group
##############################################################################
resource "aws_autoscaling_group" "this" {
  name                = local.name
  min_size            = var.min_size
  max_size            = var.max_size
  desired_capacity    = var.desired_capacity
  vpc_zone_identifier = data.aws_subnets.all_in_vpc.ids
  health_check_type   = local.attach_to_lb ? "ELB" : "EC2"
  target_group_arns   = local.attach_to_lb ? [var.target_group_arn] : []

  launch_template {
    id      = aws_launch_template.this.id
    version = "$Latest"
  }

  # CodeDeploy's in-place deployments need this: it lets CodeDeploy
  # temporarily suspend the ASG's own launch/terminate actions while it
  # replaces instances one at a time, then hand control back.
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
    }
  }

  tag {
    key                 = "Name"
    value               = local.name
    propagate_at_launch = true
  }
}

##############################################################################
# Target-tracking scaling policy (optional)
##############################################################################
resource "aws_autoscaling_policy" "cpu_target_tracking" {
  count                  = var.enable_target_tracking ? 1 : 0
  name                   = "${local.name}-cpu-target-tracking"
  autoscaling_group_name = aws_autoscaling_group.this.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = var.target_cpu_percent
  }
}
