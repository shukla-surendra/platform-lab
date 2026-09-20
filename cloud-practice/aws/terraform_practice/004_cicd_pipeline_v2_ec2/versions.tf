terraform {
  required_version = ">= 1.10" # use_lockfile (S3-native state locking) needs 1.10+

  # Bucket comes from 000_bootstrap_state_bucket — apply that first.
  # Backend blocks can't reference variables, so the name is literal here.
  # NOTE: that bucket was destroyed on 2026-09-20 (see ../JOURNEY.md). Re-running
  # 000 creates a NEW bucket with a new random suffix — paste its name below.
  backend "s3" {
    bucket       = "platform-lab-tfstate-69a2e7e4"
    key          = "004_cicd_pipeline_v2_ec2/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.region
}
