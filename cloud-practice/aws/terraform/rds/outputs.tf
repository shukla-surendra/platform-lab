output "endpoint" {
  value       = aws_db_instance.this.endpoint
  description = "host:port to connect to."
}

output "secret_arn" {
  value       = aws_secretsmanager_secret.db.arn
  description = "Secrets Manager secret holding username/password/host/port/dbname as JSON."
}

output "security_group_id" {
  value       = aws_security_group.db.id
  description = "Attach this to any EC2/Lambda/ECS security group that needs to reach the database (add it as a source, not by opening 5432 wider)."
}

output "next_steps" {
  value = <<-EOT
    1. Fetch credentials: aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.db.name} --query SecretString --output text | jq .
    2. Connect from something INSIDE the VPC (e.g. ec2/'s instance via SSM port-forwarding — this SG blocks the public internet on purpose):
         psql "host=${aws_db_instance.this.address} port=${aws_db_instance.this.port} dbname=${var.db_name} user=${var.master_username} sslmode=require"
    3. Check automated backups: aws rds describe-db-snapshots --db-instance-identifier ${aws_db_instance.this.identifier}
    4. Try a manual failover test (if multi_az = true): aws rds reboot-db-instance --db-instance-identifier ${aws_db_instance.this.identifier} --force-failover
  EOT
}
