output "instance_id" {
  value       = aws_instance.this.id
  description = "EC2 instance ID."
}

output "public_ip" {
  value       = var.associate_eip ? aws_eip.this[0].public_ip : aws_instance.this.public_ip
  description = "Public IP (static EIP if enabled, else the ephemeral one)."
}

output "security_group_id" {
  value       = aws_security_group.this.id
  description = "Security group attached to the instance."
}

output "next_steps" {
  value = <<-EOT
    1. Connect (no SSH key needed): aws ssm start-session --target ${aws_instance.this.id}
    2. If install_web_server = true: curl http://${var.associate_eip ? try(aws_eip.this[0].public_ip, "") : aws_instance.this.public_ip}
    3. Stop billing for compute without destroying the volume: aws ec2 stop-instances --instance-ids ${aws_instance.this.id}
    4. Clean up everything: terraform destroy
  EOT
}
