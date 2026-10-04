terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

data "aws_vpc" "default" {
  default = true
}

# Ubuntu 22.04 ships with the SSM agent preinstalled (snap)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# 1. Role the EC2 service is allowed to assume
resource "aws_iam_role" "ssm" {
  name = "ec2-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# 2. AWS-managed policy that lets the SSM agent talk to Systems Manager
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# 3. Instance profile = the wrapper that attaches a role to an EC2 instance
resource "aws_iam_instance_profile" "ssm" {
  name = "ec2-ssm-profile"
  role = aws_iam_role.ssm.name
}

# No ingress at all: no port 22, no port 80. Outbound only (agent -> SSM over 443).
resource "aws_security_group" "ssm" {
  name        = "ssm-only-sg"
  description = "No inbound; outbound only for SSM agent"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "ssm" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro"
  iam_instance_profile   = aws_iam_instance_profile.ssm.name
  vpc_security_group_ids = [aws_security_group.ssm.id]

  # Default VPC subnets have an internet gateway; the public IP lets the
  # agent reach SSM endpoints. Nobody connects *to* this IP.
  associate_public_ip_address = true

  metadata_options {
    http_tokens = "required" # IMDSv2
  }

  tags = {
    Name = "SSMInstance"
  }
}

output "instance_id" {
  value = aws_instance.ssm.id
}

output "connect" {
  value = "aws ssm start-session --target ${aws_instance.ssm.id} --region us-east-1"
}
