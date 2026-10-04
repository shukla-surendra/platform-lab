terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

locals {
  my_numbers = [1, 2, 3, 4, 5]
  max_number = max(local.my_numbers...)
  environments = ["sandbox","dev", "qa", "stage", "ml-stage", "prod", "ml-prod"]
  joined_envs = join("-", local.environments)
  list1 = ["a", "b"]
  list2 = ["c", "d"]
  # concat() = combine multiple lists into one list.
  combined = concat(local.list1, local.list2)
}

output "math_expressions" {
  value = {
    max_number = local.max_number
    joined_envs = local.joined_envs
    combined = local.combined
  }
}