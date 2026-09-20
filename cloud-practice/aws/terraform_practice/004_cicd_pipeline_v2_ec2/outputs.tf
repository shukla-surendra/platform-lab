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

output "pipeline_name" {
  value       = aws_codepipeline.app.name
  description = "For: aws codepipeline get-pipeline-state --name <this>"
}

output "next_steps" {
  value = <<-EOT
    1. Push app-sample/ to the repo on branch ${var.branch_name} (see README.md "First push").
    2. Watch: aws codepipeline get-pipeline-state --name ${aws_codepipeline.app.name} --region ${var.region}
    3. Approve at the Approval stage (console, or put-approval-result — see README.md).
    4. curl http://${aws_instance.target.public_ip}/
    5. Run with a value:
         aws codepipeline start-pipeline-execution --name ${aws_codepipeline.app.name} --region ${var.region} \
           --variables name=DEPLOY_NOTE,value="hello"
    6. terraform destroy when done.
  EOT
}
