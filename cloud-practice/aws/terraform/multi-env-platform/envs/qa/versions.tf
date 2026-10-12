terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }

  # Each env has its OWN state file => blast radius is one environment.
  # Native S3 locking (use_lockfile) – no DynamoDB table needed on TF >= 1.10.
  backend "s3" {
    bucket       = "REPLACE_WITH_STATE_BUCKET" # output of bootstrap/
    key          = "qa/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
