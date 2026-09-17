output "pipeline_name" {
  value       = aws_codepipeline.this.name
  description = "Pipeline name."
}

output "pipeline_arn" {
  value       = aws_codepipeline.this.arn
  description = "Pipeline ARN."
}

output "artifact_bucket" {
  value       = aws_s3_bucket.artifacts.bucket
  description = "S3 bucket holding inter-stage artifacts."
}

output "next_steps" {
  value = <<-EOT
    1. Watch it run: aws codepipeline get-pipeline-state --name ${aws_codepipeline.this.name}
    2. Trigger manually (skip waiting for a push): aws codepipeline start-pipeline-execution --name ${aws_codepipeline.this.name}
    3. Push a commit to the ${var.branch_name} branch of your source repo and watch Source -> Build -> Deploy light up automatically.
    4. Console: CodePipeline > ${aws_codepipeline.this.name} shows the visual stage-by-stage timeline.
  EOT
}
