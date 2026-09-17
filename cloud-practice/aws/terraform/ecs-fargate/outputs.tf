output "cluster_name" {
  value       = aws_ecs_cluster.this.name
  description = "ECS cluster name."
}

output "service_name" {
  value       = aws_ecs_service.this.name
  description = "ECS service name."
}

output "task_definition_arn" {
  value       = aws_ecs_task_definition.this.arn
  description = "Latest task definition ARN (a new revision is created every time container_image/cpu/memory changes)."
}

output "next_steps" {
  value = <<-EOT
    1. Watch tasks come up: aws ecs describe-services --cluster ${aws_ecs_cluster.this.name} --services ${aws_ecs_service.this.name}
    2. Tail logs: aws logs tail ${aws_cloudwatch_log_group.tasks.name} --follow
    3. Force a new deployment (re-pull the same image tag, e.g. after pushing `latest` again): aws ecs update-service --cluster ${aws_ecs_cluster.this.name} --service ${aws_ecs_service.this.name} --force-new-deployment
    4. Scale: aws ecs update-service --cluster ${aws_ecs_cluster.this.name} --service ${aws_ecs_service.this.name} --desired-count 4
  EOT
}
