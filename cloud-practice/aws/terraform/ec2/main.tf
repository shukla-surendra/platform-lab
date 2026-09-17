##############################################################################
# Locals + lookups
##############################################################################
locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/ec2"
    },
    var.extra_tags,
  )

  web_user_data = <<-EOF
    #!/bin/bash
    dnf -y install httpd
    echo "<h1>${var.project} — served by $(hostname)</h1>" > /var/www/html/index.html
    systemctl enable --now httpd
  EOF
}

# Self-contained: use the account's default VPC + a default subnet in the
# chosen AZ, same pattern as the ebs/ module. In a real deployment you'd
# pass in a VPC module's subnet ID instead.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "in_az" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = [var.availability_zone]
  }
}

# Latest Amazon Linux 2023 AMI via the public SSM parameter — no hardcoded AMI IDs
# to go stale or differ by region.
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

##############################################################################
# Security group
##############################################################################
resource "aws_security_group" "this" {
  name        = "${local.name}-sg"
  description = "EC2 demo: SSH (restricted) + HTTP (if web server enabled)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  dynamic "ingress" {
    for_each = var.install_web_server ? [1] : []
    content {
      description = "HTTP"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  egress {
    description = "all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-sg" }
}

##############################################################################
# IAM role — SSM Session Manager access, no SSH key required to connect
##############################################################################
resource "aws_iam_role" "ssm" {
  name = "${local.name}-ssm-role"

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
  role       = aws_iam_role.ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm" {
  name = "${local.name}-ssm-profile"
  role = aws_iam_role.ssm.name
}

##############################################################################
# EC2 instance
##############################################################################
resource "aws_instance" "this" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  availability_zone      = var.availability_zone
  subnet_id              = data.aws_subnets.in_az.ids[0]
  vpc_security_group_ids = [aws_security_group.this.id]
  iam_instance_profile   = aws_iam_instance_profile.ssm.name

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size_gib
    encrypted   = true
  }

  user_data = var.install_web_server ? local.web_user_data : null

  tags = { Name = local.name }
}

resource "aws_eip" "this" {
  count    = var.associate_eip ? 1 : 0
  instance = aws_instance.this.id
  domain   = "vpc"
  tags     = { Name = "${local.name}-eip" }
}
