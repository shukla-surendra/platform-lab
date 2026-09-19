# STEP 1 — the deploy target.

locals {
  name = var.project

  codedeploy_agent_install = <<-EOF
    #!/bin/bash
    dnf -y install ruby wget httpd
    systemctl enable --now httpd
    cd /tmp
    wget -q https://aws-codedeploy-${var.region}.s3.${var.region}.amazonaws.com/latest/install
    chmod +x ./install
    ./install auto
    systemctl enable --now codedeploy-agent
  EOF
}

# Self-contained pattern used throughout cloud-practice/aws/terraform/:
# default VPC, latest AL2023 AMI via SSM parameter (no hardcoded AMI IDs).
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

resource "aws_security_group" "target" {
  name        = "${local.name}-target-sg"
  description = "CI/CD deploy target: SSH (restricted) + HTTP, all out"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

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

  tags = { Name = "${local.name}-target-sg" }
}

resource "aws_iam_role" "target" {
  name = "${local.name}-target-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Lets you `aws ssm start-session` into the box with no key pair and no
# open port 22 required.
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.target.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "target" {
  name = "${local.name}-target-profile"
  role = aws_iam_role.target.name
}

resource "aws_instance" "target" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = "t3.micro"
  subnet_id              = data.aws_subnets.all_in_vpc.ids[0]
  vpc_security_group_ids = [aws_security_group.target.id]
  iam_instance_profile   = aws_iam_instance_profile.target.name
  user_data              = local.codedeploy_agent_install

  # codedeploy.tf's deployment group targets EXACTLY this tag — change one,
  # change the other, or deployments start failing with "no instances
  # found for deployment."
  tags = { Name = local.name }
}
