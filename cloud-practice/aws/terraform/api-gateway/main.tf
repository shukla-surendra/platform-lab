locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/api-gateway"
    },
    var.extra_tags,
  )
}

##############################################################################
# HTTP API (API Gateway v2 — cheaper + simpler than the older REST API/v1
# unless you specifically need REST-only features like usage plans/API keys
# or request/response body transformation via VTL templates)
##############################################################################
resource "aws_apigatewayv2_api" "this" {
  name          = local.name
  protocol_type = "HTTP"
}

resource "aws_cloudwatch_log_group" "access_logs" {
  name              = "/aws/apigateway/${local.name}"
  retention_in_days = 14
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default" # the magic stage name that serves at the API's root, no /stage-name prefix
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = var.throttling_burst_limit
    throttling_rate_limit  = var.throttling_rate_limit
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.access_logs.arn
    format = jsonencode({
      requestId          = "$context.requestId"
      ip                 = "$context.identity.sourceIp"
      routeKey           = "$context.routeKey"
      status             = "$context.status"
      integrationLatency = "$context.integrationLatency"
      responseLength     = "$context.responseLength"
    })
  }
}

##############################################################################
# Lambda proxy integration — the entire request (method, path, headers,
# body) is handed to your function as one JSON event, same shape your
# function already returns in lambda/'s src/index.py.
##############################################################################
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "ANY /{proxy+}" # catch-all: every method, every path, forwarded as-is
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "root" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "ANY /" # {proxy+} does NOT match the bare root path — needs its own route
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
