output "instance_public_ip" {
  value       = aws_instance.target.public_ip
  description = "curl this once a deployment succeeds."
}

output "instance_id" {
  value       = aws_instance.target.id
  description = "For SSM: aws ssm start-session --target <this>"
}

output "clone_url_http" {
  value       = aws_codecommit_repository.app.clone_url_http
  description = "git clone this (needs the CodeCommit credential helper — see README.md)."
}

output "codebuild_project" {
  value       = aws_codebuild_project.app.name
  description = "For manual builds: aws codebuild start-build --project-name <this>"
}

output "codedeploy_app" {
  value       = aws_codedeploy_app.app.name
  description = "CodeDeploy application name."
}

output "codedeploy_group" {
  value       = aws_codedeploy_deployment_group.app.deployment_group_name
  description = "CodeDeploy deployment group name."
}

output "pipeline_name" {
  value       = aws_codepipeline.app.name
  description = "For: aws codepipeline get-pipeline-state --name <this>"
}

output "next_steps" {
  value = <<-EOT
    1. Set up git credentials + push the sample app (see README.md "First push"):
         git config --global credential.helper '!aws codecommit credential-helper $@'
         git config --global credential.UseHttpPath true
         git clone ${aws_codecommit_repository.app.clone_url_http}
    2. Watch the pipeline run: aws codepipeline get-pipeline-state --name ${aws_codepipeline.app.name}
    3. curl http://${aws_instance.target.public_ip}/ once Deploy succeeds.
    4. terraform destroy when done — see README.md's cost section.
  EOT
}
