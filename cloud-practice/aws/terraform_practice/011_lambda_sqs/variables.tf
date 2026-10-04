variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  description = "Prefix used in resource names"
  type        = string
  default     = "sqs-lambda-lab"
}

variable "lambda_timeout_seconds" {
  description = "Max run time of one Lambda invocation"
  type        = number
  default     = 30
}

variable "batch_size" {
  description = "How many SQS messages Lambda receives per invocation"
  type        = number
  default     = 5
}

variable "max_receive_count" {
  description = "Failed processing attempts before a message moves to the dead-letter queue"
  type        = number
  default     = 3
}
