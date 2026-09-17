locals {
  name = var.project
  tags = merge(
    {
      Project   = var.project
      ManagedBy = "terraform"
      Module    = "aws/terraform/cloudwatch"
    },
    var.extra_tags,
  )

  watch_asg    = var.asg_name != ""
  watch_lambda = var.lambda_function_name != ""
  watch_alb    = var.alb_arn_suffix != ""

  dashboard_widgets = concat(
    local.watch_asg ? [{
      type   = "metric"
      x      = 0
      y      = 0
      width  = 12
      height = 6
      properties = {
        title   = "ASG Average CPU %"
        region  = var.region
        metrics = [["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", var.asg_name]]
        stat    = "Average"
        period  = 300
      }
    }] : [],
    local.watch_lambda ? [{
      type   = "metric"
      x      = 12
      y      = 0
      width  = 12
      height = 6
      properties = {
        title  = "Lambda Errors + Invocations"
        region = var.region
        metrics = [
          ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_function_name],
          ["AWS/Lambda", "Errors", "FunctionName", var.lambda_function_name],
        ]
        stat   = "Sum"
        period = 300
      }
    }] : [],
    local.watch_alb ? [{
      type   = "metric"
      x      = 0
      y      = 6
      width  = 12
      height = 6
      properties = {
        title  = "ALB 5xx + Request Count"
        region = var.region
        metrics = [
          ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", var.alb_arn_suffix],
          ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", var.alb_arn_suffix],
        ]
        stat   = "Sum"
        period = 300
      }
    }] : [],
  )
}

##############################################################################
# Alarm notification topic
##############################################################################
resource "aws_sns_topic" "alarms" {
  name = "${local.name}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

##############################################################################
# Alarms — each one only exists if its target resource was passed in
##############################################################################
resource "aws_cloudwatch_metric_alarm" "asg_cpu_high" {
  count               = local.watch_asg ? 1 : 0
  alarm_name          = "${local.name}-asg-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = var.asg_cpu_alarm_threshold
  alarm_description   = "Average CPU across ${var.asg_name} exceeded ${var.asg_cpu_alarm_threshold}% for 2 consecutive 5-minute periods."
  dimensions = {
    AutoScalingGroupName = var.asg_name
  }
  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count               = local.watch_lambda ? 1 : 0
  alarm_name          = "${local.name}-lambda-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.lambda_error_alarm_threshold
  alarm_description   = "${var.lambda_function_name} logged >= ${var.lambda_error_alarm_threshold} error(s) in a 5-minute period."
  dimensions = {
    FunctionName = var.lambda_function_name
  }
  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  count               = local.watch_alb ? 1 : 0
  alarm_name          = "${local.name}-alb-5xx"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alb_5xx_alarm_threshold
  alarm_description   = "ALB ${var.alb_arn_suffix} returned >= ${var.alb_5xx_alarm_threshold} 5xx response(s) in a 5-minute period."
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }
  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
}

##############################################################################
# Dashboard — one view combining whichever resources were wired in
##############################################################################
resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = local.name
  dashboard_body = jsonencode({ widgets = local.dashboard_widgets })
}
