# ===========================================================================
# SERVICES STACK  -  owned by the DEVELOPER / service team
# ===========================================================================
# This is the file a developer edits to add an endpoint: one module block per
# route. They never touch the API, stage, logging or throttling (platform's job).
#
# Apply this AFTER the platform stack. Re-run it whenever routes or function
# settings change (or only when infra-ish things change if code is shipped by CI;
# see ../OWNERSHIP.md).

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "api_name" {
  description = "Name of the platform's API (used to find its published parameters)"
  type        = string
  default     = "demo-http-api"
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = "apigw-lab"
      Managed = "terraform"
      Owner   = "orders-team"
    }
  }
}

# The platform's published contract: we only need these two values
data "aws_ssm_parameter" "api_id" {
  name = "/platform/${var.api_name}/api_id"
}

data "aws_ssm_parameter" "execution_arn" {
  name = "/platform/${var.api_name}/execution_arn"
}

# ---------- Route 1: GET /hello ----------
module "hello" {
  source = "../modules/lambda_route"

  api_id            = data.aws_ssm_parameter.api_id.value
  api_execution_arn = data.aws_ssm_parameter.execution_arn.value

  function_name = "apigw-lab-hello"
  route_key     = "GET /hello"
  source_dir    = "${path.module}/src/hello"
}

# ---------- Route 2: POST /orders ----------
module "orders" {
  source = "../modules/lambda_route"

  api_id            = data.aws_ssm_parameter.api_id.value
  api_execution_arn = data.aws_ssm_parameter.execution_arn.value

  function_name = "apigw-lab-orders"
  route_key     = "POST /orders"
  source_dir    = "${path.module}/src/orders"
  environment   = { ORDER_PREFIX = "ord" }
}

locals {
  base_url = "https://${data.aws_ssm_parameter.api_id.value}.execute-api.${var.region}.amazonaws.com"
}

output "hello_url" {
  value = "${local.base_url}/hello"
}

output "orders_url" {
  value = "${local.base_url}/orders"
}
