# The deploy target.

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

# Default VPC + latest AL2023 AMI via SSM parameter (no hardcoded AMI IDs).
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

# No SSH rule (003 had one, open to the world, on an instance with no key
# pair — it did nothing). Shell access is via SSM Session Manager instead.
resource "aws_security_group" "target" {
  name        = "${local.name}-target-sg"
  description = "CI/CD deploy target: HTTP in, all out"
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

# `aws ssm start-session` into the box — no key pair, no open port 22.
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.target.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# The CodeDeploy agent downloads the build output from the pipeline's
# artifact bucket using THIS role. Without it the Deploy stage fails with an
# S3 AccessDenied on the revision download (003 hit exactly this).
resource "aws_iam_role_policy" "target_pipeline_artifacts" {
  name = "${local.name}-target-pipeline-artifacts"
  role = aws_iam_role.target.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadPipelineArtifacts"
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:GetObjectVersion"]
      Resource = ["${aws_s3_bucket.pipeline_artifacts.arn}/*"]
    }]
  })
}

resource "aws_iam_instance_profile" "target" {
  name = "${local.name}-target-profile"
  role = aws_iam_role.target.name
}

resource "aws_instance" "target" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.all_in_vpc.ids[0]
  vpc_security_group_ids = [aws_security_group.target.id]
  iam_instance_profile   = aws_iam_instance_profile.target.name
  user_data              = local.codedeploy_agent_install

  # codedeploy.tf's deployment group targets EXACTLY this tag — change one,
  # change the other, or deployments fail with "no instances found."
  tags = { Name = local.name }
}
