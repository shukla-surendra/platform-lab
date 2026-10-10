terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }

  # The bucket already exists (looked up below, not created here), so it is safe
  # to store this folder's state in it. Separate key from 04-ec2-s3-backend so the
  # two folders never share state:
  #   dev  -> env/dev/04a-ec2/terraform.tfstate
  #   prod -> env/prod/04a-ec2/terraform.tfstate
  backend "s3" {
    bucket               = "tfstate-680143075966-us-east-1"
    key                  = "04a-ec2/terraform.tfstate"
    workspace_key_prefix = "env"
    region               = "us-east-1"
    encrypt              = true
    use_lockfile         = true
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Environment = terraform.workspace
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  # Account id makes the name globally unique without you inventing one
  bucket_name = "tfstate-${data.aws_caller_identity.current.account_id}-us-east-1"
}

# The bucket already exists (created outside Terraform), so we only look it up.
data "aws_s3_bucket" "state" {
  bucket = local.bucket_name
}

output "bucket_name" {
  value = data.aws_s3_bucket.state.bucket
}

# ---------------------------------------------------------------
# EC2 with per-workspace settings, keyed by workspace name.
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

  # Fails with a clear error in a workspace not listed above (e.g. "default").
  config = local.settings[terraform.workspace]
}

data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "app" {
  name        = "s3be-${terraform.workspace}-sg"
  description = "No inbound; outbound only"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_egress_rule" "all_out" {
  security_group_id = aws_security_group.app.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = local.config.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.app.id]

  root_block_device {
    volume_size = local.config.volume_size
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  tags = {
    Name = "s3be-${terraform.workspace}-app"
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
