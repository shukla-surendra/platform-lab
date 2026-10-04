output "state_machine_arn" {
  value = aws_sfn_state_machine.order.arn
}

output "alias_arn" {
  description = "Start executions on this, not on the raw state machine ARN"
  value       = aws_sfn_alias.live.arn
}

output "latest_version_arn" {
  value = aws_sfn_state_machine.order.state_machine_version_arn
}

output "start_valid_execution" {
  value = "aws stepfunctions start-execution --region ${var.region} --state-machine-arn ${aws_sfn_alias.live.arn} --input '{\"order_id\":\"o-1\",\"amount\":25}'"
}
