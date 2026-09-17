variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag."
  type        = string
  default     = "aws-mastery-cloudwatch"
}

variable "alarm_email" {
  description = "If set, an email subscription is added to the alarm topic (you must confirm it via the email AWS sends)."
  type        = string
  default     = ""
}

variable "asg_name" {
  description = "If set (from autoscaling/'s output), create a CPU-high alarm + add it to the dashboard."
  type        = string
  default     = ""
}

variable "asg_cpu_alarm_threshold" {
  description = "Average CPU % that triggers the ASG alarm."
  type        = number
  default     = 80
}

variable "lambda_function_name" {
  description = "If set (from lambda/'s output), create an error-count alarm + add it to the dashboard."
  type        = string
  default     = ""
}

variable "lambda_error_alarm_threshold" {
  description = "Error count (over one evaluation period) that triggers the Lambda alarm."
  type        = number
  default     = 1
}

variable "alb_arn_suffix" {
  description = "If set (the part of alb/'s aws_lb ARN after 'loadbalancer/' — see README for how to extract it), create a 5xx-rate alarm + add it to the dashboard."
  type        = string
  default     = ""
}

variable "alb_5xx_alarm_threshold" {
  description = "Count of 5xx responses (over one evaluation period) that triggers the ALB alarm."
  type        = number
  default     = 5
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
