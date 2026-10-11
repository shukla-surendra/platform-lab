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

  # Every resource gets these tags: easy to find (and to confirm gone) in the console and CLI
  default_tags {
    tags = {
      Project = "eks-egress-lab"
      Managed = "terraform"
      ttl     = "destroy-after-session" # a reminder to a human; nothing enforces it
    }
  }
}
