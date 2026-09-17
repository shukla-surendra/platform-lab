output "job_queue_name" {
  value       = aws_batch_job_queue.this.name
  description = "Submit jobs against this queue."
}

output "job_definition_name" {
  value       = aws_batch_job_definition.this.name
  description = "Job definition to submit."
}

output "next_steps" {
  value = <<-EOT
    1. Submit a job: aws batch submit-job --job-name manual-test --job-queue ${aws_batch_job_queue.this.name} --job-definition ${aws_batch_job_definition.this.name}
    2. Watch it move SUBMITTED -> RUNNABLE -> STARTING -> RUNNING -> SUCCEEDED: aws batch describe-jobs --jobs <job-id from step 1>
    3. Tail its logs: aws logs tail ${aws_cloudwatch_log_group.jobs.name} --follow
    4. List everything queued/running: aws batch list-jobs --job-queue ${aws_batch_job_queue.this.name} --job-status RUNNING
  EOT
}
