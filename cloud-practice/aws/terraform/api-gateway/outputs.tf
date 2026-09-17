output "api_endpoint" {
  value       = aws_apigatewayv2_api.this.api_endpoint
  description = "Base HTTPS URL. Everything after it is forwarded to Lambda unchanged."
}

output "api_id" {
  value       = aws_apigatewayv2_api.this.id
  description = "API ID."
}

output "next_steps" {
  value = <<-EOT
    1. curl ${aws_apigatewayv2_api.this.api_endpoint}/
    2. curl ${aws_apigatewayv2_api.this.api_endpoint}/anything/at/all   (the {proxy+} catch-all route)
    3. curl -X POST -d '{"hello":"world"}' ${aws_apigatewayv2_api.this.api_endpoint}/echo
    4. Tail access logs: aws logs tail /aws/apigateway/${aws_apigatewayv2_api.this.name} --follow
  EOT
}
