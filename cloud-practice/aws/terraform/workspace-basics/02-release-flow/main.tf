terraform {
  required_version = ">= 1.5"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.80" }
    archive = { source = "hashicorp/archive", version = "~> 2.4" }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "environment" { type = string }
variable "app_version" { type = string }
variable "memory_size" { type = number }
variable "log_level" { type = string }

# Safety net: refuses to run if workspace and tfvars file disagree.
check "workspace_matches_tfvars" {
  assert {
    condition     = terraform.workspace == var.environment
    error_message = "Workspace '${terraform.workspace}' but tfvars says '${var.environment}'. Wrong -var-file?"
  }
}

locals {
  name = "wsdemo2-${var.environment}"
}

data "archive_file" "zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/build/lambda.zip"
}

resource "aws_iam_role" "lambda" {
  name = "${local.name}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "hello" {
  function_name    = "${local.name}-hello"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.zip.output_path
  source_code_hash = data.archive_file.zip.output_base64sha256
  memory_size      = var.memory_size
  publish          = true # every code change creates an immutable numbered version

  environment {
    variables = {
      ENVIRONMENT = var.environment
      APP_VERSION = var.app_version
      LOG_LEVEL   = var.log_level
    }
  }
}

# Callers use the alias "live". A release = alias moves to the new version.
resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = aws_lambda_function.hello.function_name
  function_version = aws_lambda_function.hello.version
}

output "function_name" { value = aws_lambda_function.hello.function_name }
output "live_version" { value = aws_lambda_alias.live.function_version }
