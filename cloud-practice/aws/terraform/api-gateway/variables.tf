variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag, and the API name."
  type        = string
  default     = "aws-mastery-apigw"
}

variable "lambda_function_name" {
  description = "Function name from the lambda/ module's output — required."
  type        = string
}

variable "lambda_invoke_arn" {
  description = "invoke_arn from the lambda/ module's output — required."
  type        = string
}

variable "throttling_burst_limit" {
  description = "Max concurrent requests allowed to burst above the steady-state rate."
  type        = number
  default     = 20
}

variable "throttling_rate_limit" {
  description = "Steady-state requests/second allowed before 429s."
  type        = number
  default     = 10
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
