output "alarm_topic_arn" {
  value       = aws_sns_topic.alarms.arn
  description = "Subscribe anything else you want notified (another Lambda, a Slack webhook via SNS-to-Lambda) to this topic."
}

output "dashboard_url" {
  value       = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.this.dashboard_name}"
  description = "Direct link to the dashboard in the console."
}

output "next_steps" {
  value = <<-EOT
    1. Open the dashboard: see the dashboard_url output above.
    2. If alarm_email was set: check that inbox and CONFIRM the SNS subscription (unconfirmed subscriptions never deliver).
    3. Force an alarm to fire, e.g. for the Lambda one: invoke the function with a payload that makes it throw, then watch aws cloudwatch describe-alarms --alarm-names ${local.name}-lambda-errors move ALARM -> OK as errors stop.
    4. List every alarm this module created: aws cloudwatch describe-alarms --alarm-name-prefix ${local.name}
  EOT
}
