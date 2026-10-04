# ===========================================================================
# PLATFORM STACK  -  owned by DevOps / platform team
# ===========================================================================
# Creates the shared "road": the API itself, its stage, logging, throttling,
# CORS and a published contract (SSM parameters) that service teams build on.
# It contains NO routes and NO Lambdas: those belong to the service teams.
#
# Apply this FIRST, once. It changes rarely.

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "api_name" {
  type    = string
  default = "demo-http-api"
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = "apigw-lab"
      Managed = "terraform"
      Owner   = "platform-team"
    }
  }
}

# ---------- 1. The API (HTTP API = API Gateway v2) ----------
resource "aws_apigatewayv2_api" "this" {
  name          = var.api_name
  protocol_type = "HTTP"

  # Org-wide browser policy is a platform decision. Tighten allow_origins in real life.
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
  }
}

# ---------- 2. Access logs (platform standard) ----------
resource "aws_cloudwatch_log_group" "access" {
  name              = "/aws/apigateway/${var.api_name}"
  retention_in_days = 14
}

# ---------- 3. The stage ----------
# "$default" stage + auto_deploy = true: whenever a team adds/changes a route or
# integration, API Gateway publishes it automatically. THIS is why service teams
# can add routes without the platform team redeploying anything.
# (With the older REST API / v1 you must create an explicit deployment.)
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.access.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      integrationErr = "$context.integrationErrorMessage"
    })
  }

  # Default throttling for every route: protects backends from a runaway client
  default_route_settings {
    throttling_burst_limit = 50
    throttling_rate_limit  = 25
  }
}

# ---------- 4. The contract with service teams ----------
# Service stacks read these instead of sharing Terraform state. Changing the
# platform later (new API, new account) does not break teams as long as these
# names keep meaning the same thing.
resource "aws_ssm_parameter" "api_id" {
  name  = "/platform/${var.api_name}/api_id"
  type  = "String"
  value = aws_apigatewayv2_api.this.id
}

resource "aws_ssm_parameter" "execution_arn" {
  name  = "/platform/${var.api_name}/execution_arn"
  type  = "String"
  value = aws_apigatewayv2_api.this.execution_arn
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.this.api_endpoint
}

output "api_id" {
  value = aws_apigatewayv2_api.this.id
}
