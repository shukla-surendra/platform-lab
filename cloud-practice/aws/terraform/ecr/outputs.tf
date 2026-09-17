output "repository_url" {
  value       = aws_ecr_repository.this.repository_url
  description = "docker push/pull target, e.g. <account>.dkr.ecr.<region>.amazonaws.com/<name>"
}

output "repository_arn" {
  value       = aws_ecr_repository.this.arn
  description = "Pass into an ECS task execution role's policy (ecr:GetDownloadUrlForLayer, ecr:BatchGetImage)."
}

output "next_steps" {
  value = <<-EOT
    1. Authenticate Docker:
         aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${aws_ecr_repository.this.repository_url}
    2. Build, tag, push:
         docker build -t ${aws_ecr_repository.this.repository_url}:v1 .
         docker push ${aws_ecr_repository.this.repository_url}:v1
    3. See the vulnerability scan: aws ecr describe-image-scan-findings --repository-name ${aws_ecr_repository.this.name} --image-id imageTag=v1
    4. Wire repository_url into ecs-fargate/'s container_image variable.
  EOT
}
