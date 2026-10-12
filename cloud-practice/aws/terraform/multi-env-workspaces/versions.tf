terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }

  # ONE backend block for ALL envs. Terraform stores each workspace's state at:
  #   <workspace_key_prefix>/<workspace>/<key>  =>  env/dev/terraform.tfstate
  backend "s3" {
    bucket               = "REPLACE_WITH_STATE_BUCKET"
    key                  = "terraform.tfstate"
    workspace_key_prefix = "env"
    region               = "us-east-1"
    encrypt              = true
    use_lockfile         = true
  }
}
