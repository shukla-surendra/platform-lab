provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.project
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  name = "${var.project}-${var.environment}"
}

module "network" {
  source     = "../../modules/network"
  name       = local.name
  cidr       = var.vpc_cidr
  az_count   = var.az_count
  enable_nat = var.enable_nat
}

module "storage" {
  source                    = "../../modules/storage"
  name                      = local.name
  suffix                    = data.aws_caller_identity.current.account_id
  force_destroy             = var.force_destroy
  noncurrent_retention_days = var.noncurrent_retention_days
}
