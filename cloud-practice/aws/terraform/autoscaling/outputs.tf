output "asg_name" {
  value       = aws_autoscaling_group.this.name
  description = "Auto Scaling Group name — what codedeploy/'s deployment group targets."
}

output "launch_template_id" {
  value       = aws_launch_template.this.id
  description = "Launch template ID."
}

output "security_group_id" {
  value       = aws_security_group.this.id
  description = "Security group attached to every instance in the ASG."
}

output "next_steps" {
  value = <<-EOT
    1. Watch instances launch: aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names ${aws_autoscaling_group.this.name}
    2. Force a scale-out to see it happen live: aws autoscaling set-desired-capacity --auto-scaling-group-name ${aws_autoscaling_group.this.name} --desired-capacity ${var.max_size} --honor-cooldown
    3. Wire this ASG name into codedeploy/'s deployment_group_asg_names variable.
    4. If load-balanced: pass this module's target_group_arn from alb/'s output BEFORE first apply (health_check_type flips to ELB).
  EOT
}
