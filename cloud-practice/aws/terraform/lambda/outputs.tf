output "function_name" {
  value       = aws_lambda_function.this.function_name
  description = "Lambda function name."
}

output "function_arn" {
  value       = aws_lambda_function.this.arn
  description = "Pass into api-gateway/'s lambda_function_arn variable."
}

output "invoke_arn" {
  value       = aws_lambda_function.this.invoke_arn
  description = "The ARN API Gateway's integration needs (includes the /invocations suffix)."
}

output "function_url" {
  value       = try(aws_lambda_function_url.this[0].function_url, null)
  description = "Public HTTPS endpoint (null unless enable_function_url = true)."
}

output "next_steps" {
  value = <<-EOT
    1. Invoke directly: aws lambda invoke --function-name ${aws_lambda_function.this.function_name} --payload '{}' /tmp/out.json && cat /tmp/out.json
    2. If enable_function_url: curl "$(terraform output -raw function_url)"
    3. Watch logs: aws logs tail /aws/lambda/${aws_lambda_function.this.function_name} --follow
    4. Edit src/index.py and re-apply — Terraform re-zips and redeploys automatically (source_code_hash changes).
  EOT
}
