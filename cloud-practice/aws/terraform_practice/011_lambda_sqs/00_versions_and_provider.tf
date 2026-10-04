terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive" # zips the Lambda source folder
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random" # unique suffix for the globally-unique bucket name
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = var.project
      Managed = "terraform"
    }
  }
}
