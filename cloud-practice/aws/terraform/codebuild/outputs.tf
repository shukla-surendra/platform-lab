output "project_name" {
  value       = aws_codebuild_project.this.name
  description = "CodeBuild project name."
}

output "project_arn" {
  value       = aws_codebuild_project.this.arn
  description = "ARN — what codepipeline/'s build stage references."
}

output "service_role_arn" {
  value       = aws_iam_role.codebuild.arn
  description = "IAM role CodeBuild assumes."
}

output "artifact_bucket" {
  value       = local.bucket_name
  description = "S3 bucket build output lands in (self-created unless artifact_bucket_name was passed in)."
}

output "next_steps" {
  value = <<-EOT
    1. Run it once by hand:  aws codebuild start-build --project-name ${aws_codebuild_project.this.name}
    2. Watch logs live:      aws logs tail ${aws_cloudwatch_log_group.build.name} --follow
    3. Check the build's status/artifacts in the console under CodeBuild > Build projects.
    4. Wire this project's name (${aws_codebuild_project.this.name}) into codepipeline/'s build stage.
  EOT
}
