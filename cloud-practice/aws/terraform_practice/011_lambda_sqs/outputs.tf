output "artifacts_bucket" {
  value = aws_s3_bucket.artifacts.id
}

output "queue_url" {
  value = aws_sqs_queue.main.url
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "lambda_name" {
  value = aws_lambda_function.processor.function_name
}

output "send_test_message" {
  value = "python3 scripts/send_message.py --queue-url ${aws_sqs_queue.main.url} --count 3"
}

output "tail_logs" {
  value = "aws logs tail /aws/lambda/${aws_lambda_function.processor.function_name} --follow --region ${var.region}"
}
