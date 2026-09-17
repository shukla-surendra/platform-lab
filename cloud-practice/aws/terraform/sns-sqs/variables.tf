variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag."
  type        = string
  default     = "aws-mastery-sns-sqs"
}

variable "visibility_timeout_seconds" {
  description = "How long a message is hidden from other consumers after one consumer receives it. Must be >= your consumer's processing time, or another consumer will grab (and duplicate-process) it."
  type        = number
  default     = 30
}

variable "message_retention_seconds" {
  description = "How long an unconsumed message survives in the queue before being dropped (max 14 days)."
  type        = number
  default     = 345600 # 4 days
}

variable "max_receive_count" {
  description = "How many times a message can be received/fail before it's moved to the dead-letter queue instead of retried again."
  type        = number
  default     = 3
}

variable "lambda_function_arn" {
  description = "If set (from lambda/'s output), wire an SQS event source mapping so every message triggers that function. Leave empty to just poll the queue by hand."
  type        = string
  default     = ""
}

variable "lambda_function_name" {
  description = "Required alongside lambda_function_arn — needed for the aws_lambda_permission resource."
  type        = string
  default     = ""
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
