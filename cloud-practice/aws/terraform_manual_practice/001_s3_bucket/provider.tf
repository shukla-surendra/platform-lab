
# Tested On Terraform 1.16.4.
# Configure the AWS Provider | Terraform 0.12 and earlier | mixes version with configuration
# as of 1.16.4 this still work but gives deprication and removal warning
#│ Terraform 0.13 and earlier allowed provider version constraints inside the provider configuration block, but
#│ that is now deprecated and will be removed in a future version of Terraform. To silence this warning, move
#│ the provider version constraint into the required_providers block.
#provider "aws" {
#  version = "~> 6.0"
#  region  = "us-east-1"
#}

# new way from 1.13
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = "us-east-1"
}

