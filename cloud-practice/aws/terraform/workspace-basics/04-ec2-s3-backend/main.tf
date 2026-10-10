terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }

  # Workspace name is NOT written here. Terraform builds the path itself:
  #   dev  -> env/dev/ec2/terraform.tfstate
  #   qa   -> env/qa/ec2/terraform.tfstate
  backend "s3" {
    bucket               = "tfstate-680143075966-us-east-1"
    key                  = "ec2/terraform.tfstate"
    workspace_key_prefix = "env"
    region               = "us-east-1"
    encrypt              = true
    use_lockfile         = true
  }
}

provider "aws" {
  region = "us-east-1"

  # Every resource gets these tags automatically -> easy to see which env owns what
  default_tags {
    tags = {
      Environment = terraform.workspace
      ManagedBy   = "terraform"
    }
  }
}

# ---------------------------------------------------------------
# Per-workspace settings live in ONE map, keyed by workspace name.
# terraform.workspace picks the matching entry.
# ---------------------------------------------------------------
locals {
  settings = {
    dev = {
      instance_type = "t3.micro"
      volume_size   = 8
    }
    qa = {
      instance_type = "t3.micro"
      volume_size   = 8
    }
    prod = {
      instance_type = "t3.small"
      volume_size   = 20
    }
  }

  # Fails with a clear error if you are in a workspace not listed above (e.g. "default").
  config = local.settings[terraform.workspace]
}

# Latest Amazon Linux 2023 AMI (AWS publishes the current id in SSM)
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# Use the account's default VPC/subnet to keep this lesson about workspaces, not networking
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "web" {
  name        = "wsdemo-${terraform.workspace}-sg"
  description = "No inbound; outbound only"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_egress_rule" "all_out" {
  security_group_id = aws_security_group.web.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = local.config.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.web.id]

  root_block_device {
    volume_size = local.config.volume_size
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  tags = {
    Name = "wsdemo-${terraform.workspace}-app" # -> wsdemo-dev-app, wsdemo-prod-app
  }
}

output "workspace" {
  value = terraform.workspace
}

output "instance_id" {
  value = aws_instance.app.id
}

output "instance_type" {
  value = aws_instance.app.instance_type
}
