output "dns_name" {
  value       = aws_lb.this.dns_name
  description = "Public DNS name — curl this directly."
}

output "target_group_arn" {
  value       = aws_lb_target_group.this.arn
  description = "Pass into autoscaling/'s target_group_arn variable to attach instances."
}

output "security_group_id" {
  value       = aws_security_group.alb.id
  description = "Reference this from an instance/ASG security group's ingress instead of 0.0.0.0/0."
}

output "next_steps" {
  value = <<-EOT
    1. curl http://${aws_lb.this.dns_name}   (502 until real targets are registered/healthy)
    2. Pass target_group_arn (${aws_lb_target_group.this.arn}) into autoscaling/'s target_group_arn.
    3. Check target health: aws elbv2 describe-target-health --target-group-arn ${aws_lb_target_group.this.arn}
  EOT
}
