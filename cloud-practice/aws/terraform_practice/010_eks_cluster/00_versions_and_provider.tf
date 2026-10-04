# ---------------------------------------------------------------------------
# STEP 0: Terraform + provider setup
# ---------------------------------------------------------------------------
# Terraform needs to know WHICH provider (plugin) talks to AWS, and which
# version. `terraform init` downloads it. Nothing is created in AWS here.

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region

  # Every resource created by this provider gets these tags automatically.
  # Handy for finding / cleaning up lab resources in the console.
  default_tags {
    tags = {
      Project = "eks-lab"
      Managed = "terraform"
    }
  }
}
