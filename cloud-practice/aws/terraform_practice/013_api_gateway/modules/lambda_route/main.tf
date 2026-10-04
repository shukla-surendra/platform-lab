# ===========================================================================
# MODULE lambda_route  -  written by the platform team, USED by developers
# ===========================================================================
# Wraps all the boilerplate needed to put one Lambda behind one route:
#   Lambda + execution role + log group + API integration + route + invoke permission.
# Developers supply only: function name, route, code folder.
# The platform team bakes the standards in once (runtime, arm64, log retention,
# least-privilege permission scoped to THIS route, tags).

locals {
  method = split(" ", var.route_key)[0]
  path   = split(" ", var.route_key)[1]

  # '/items/{id}' -> '/items/*' for the permission ARN
  path_for_arn = replace(local.path, "/\\{[^}]+\\}/", "*")
}

# Zip the developer's code folder
data "archive_file" "code" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.root}/build/${var.function_name}.zip"
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Each function gets its OWN role (no shared role = no shared blast radius)
resource "aws_iam_role" "this" {
  name               = "${var.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 7
}

resource "aws_lambda_function" "this" {
  function_name    = var.function_name
  role             = aws_iam_role.this.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = var.handler
  memory_size      = var.memory_size
  timeout          = var.timeout
  filename         = data.archive_file.code.output_path
  source_code_hash = data.archive_file.code.output_base64sha256

  dynamic "environment" {
    for_each = length(var.environment) > 0 ? [1] : []
    content {
      variables = var.environment
    }
  }

  depends_on = [aws_iam_role_policy_attachment.logs, aws_cloudwatch_log_group.this]
}

# Integration: "when this route is hit, call this Lambda" (proxy, payload format 2.0)
resource "aws_apigatewayv2_integration" "this" {
  api_id                 = var.api_id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.this.invoke_arn
  payload_format_version = "2.0"
}

# Route: the URL + method that triggers the integration
resource "aws_apigatewayv2_route" "this" {
  api_id    = var.api_id
  route_key = var.route_key
  target    = "integrations/${aws_apigatewayv2_integration.this.id}"
}

# Permission: API Gateway may invoke THIS function, only for THIS route.
# Without it the route returns 500 even though everything else is wired.
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowInvokeFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_execution_arn}/*/${local.method}${local.path_for_arn}"
}
