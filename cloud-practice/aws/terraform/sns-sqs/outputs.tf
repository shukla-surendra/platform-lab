output "topic_arn" {
  value       = aws_sns_topic.this.arn
  description = "Publish here — every subscriber (this queue, and any future ones) receives a copy."
}

output "queue_url" {
  value       = aws_sqs_queue.this.id
  description = "Main queue URL (SQS API calls use the URL, not the ARN)."
}

output "queue_arn" {
  value       = aws_sqs_queue.this.arn
  description = "Main queue ARN."
}

output "dlq_url" {
  value       = aws_sqs_queue.dlq.id
  description = "Dead-letter queue URL — check here for messages that failed max_receive_count times."
}

output "lambda_execution_role_policy_needed" {
  value = local.wire_lambda ? jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
      Resource = aws_sqs_queue.this.arn
    }]
  }) : null
  description = "If lambda_function_arn is set: attach this exact policy to the Lambda's OWN execution role (aws_iam_role.lambda in the lambda/ module) — this module can't reach into that module's state to do it for you."
}

output "next_steps" {
  value = <<-EOT
    1. Publish a message: aws sns publish --topic-arn ${aws_sns_topic.this.arn} --message '{"hello":"world"}'
    2. Receive it: aws sqs receive-message --queue-url ${aws_sqs_queue.this.id}
    3. Force a DLQ trip: receive the same message max_receive_count times WITHOUT deleting it, then check: aws sqs receive-message --queue-url ${aws_sqs_queue.dlq.id}
    4. If lambda_function_arn was set, attach the policy in output `lambda_execution_role_policy_needed` to the function's execution role, THEN publish again and watch the function invoke automatically.
  EOT
}
