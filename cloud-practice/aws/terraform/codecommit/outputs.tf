output "repository_name" {
  value       = aws_codecommit_repository.this.repository_name
  description = "Repository name (also its ARN's suffix)."
}

output "clone_url_http" {
  value       = aws_codecommit_repository.this.clone_url_http
  description = "HTTPS clone URL (needs the git credential helper — see README)."
}

output "clone_url_ssh" {
  value       = aws_codecommit_repository.this.clone_url_ssh
  description = "SSH clone URL (needs an SSH public key uploaded to your IAM user)."
}

output "next_steps" {
  value = <<-EOT
    1. One-time git credential setup (HTTPS):
         git config --global credential.helper '!aws codecommit credential-helper $@'
         git config --global credential.UseHttpPath true
    2. Clone + push:
         git clone ${aws_codecommit_repository.this.clone_url_http}
    3. Set the default branch once it has a commit:
         aws codecommit update-default-branch --repository-name ${aws_codecommit_repository.this.repository_name} --default-branch-name ${var.default_branch}
    4. Point codebuild/ or codepipeline/'s source stage at this repository_name.
  EOT
}
