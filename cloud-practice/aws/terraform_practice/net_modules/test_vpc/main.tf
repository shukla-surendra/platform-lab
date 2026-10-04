# ===========================================================================
# Shared lab module: ONE small VPC + ONE test instance
# ===========================================================================
# Used by the peering (014) and transit gateway (015) demos so the interesting
# part of each lesson (the connectivity) is not buried in boilerplate.
#
# LAB SHORTCUT: the subnet is public (IGW + public IP) ONLY so the SSM agent
# can reach AWS and you can run test commands without keys or open ports.
# The traffic under test uses the instances' PRIVATE IPs and the private routes.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "name" {
  type = string
}

variable "cidr" {
  type = string
}

variable "az" {
  type = string
}

variable "allowed_ingress_cidrs" {
  description = "Who may reach the test web server (port 80) and ping the instance"
  type        = list(string)
}

variable "instance_type" {
  type    = string
  default = "t4g.nano"
}

# Amazon Linux 2023 (arm64): SSM agent preinstalled, python3 available
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

resource "aws_vpc" "this" {
  cidr_block           = var.cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = var.name }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = var.name }
}

resource "aws_subnet" "this" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.cidr, 8, 0)
  availability_zone       = var.az
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name}-subnet" }
}

resource "aws_route_table" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = var.name }

  # internet route only for SSM; peering/TGW routes are added by the demos
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
}

resource "aws_route_table_association" "this" {
  subnet_id      = aws_subnet.this.id
  route_table_id = aws_route_table.this.id
}

resource "aws_security_group" "this" {
  name        = "${var.name}-sg"
  description = "Test instance: HTTP and ping from allowed CIDRs"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTP from allowed CIDRs"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_ingress_cidrs
  }

  ingress {
    description = "ICMP from allowed CIDRs"
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = var.allowed_ingress_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- SSM access (same pattern as lesson 008) ---
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.name}-ssm-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "this" {
  name = "${var.name}-ssm-profile"
  role = aws_iam_role.this.name
}

resource "aws_instance" "this" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.this.id
  vpc_security_group_ids = [aws_security_group.this.id]
  iam_instance_profile   = aws_iam_instance_profile.this.name

  metadata_options {
    http_tokens = "required"
  }

  # Tiny web server on port 80 that says who it is: the test target
  user_data = <<-EOF
    #!/bin/bash
    mkdir -p /srv/www
    echo "hello from ${var.name}" > /srv/www/index.html
    cat > /etc/systemd/system/hello-web.service <<'UNIT'
    [Unit]
    Description=hello web
    After=network.target
    [Service]
    ExecStart=/usr/bin/python3 -m http.server 80 --directory /srv/www
    Restart=always
    [Install]
    WantedBy=multi-user.target
    UNIT
    systemctl daemon-reload
    systemctl enable --now hello-web
  EOF

  tags = { Name = "${var.name}-instance" }
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "cidr" {
  value = var.cidr
}

output "subnet_id" {
  value = aws_subnet.this.id
}

output "route_table_id" {
  value = aws_route_table.this.id
}

output "instance_id" {
  value = aws_instance.this.id
}

output "private_ip" {
  value = aws_instance.this.private_ip
}
