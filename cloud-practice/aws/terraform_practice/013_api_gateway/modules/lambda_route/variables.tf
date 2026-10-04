variable "api_id" {
  description = "ID of the shared HTTP API (from the platform stack)"
  type        = string
}

variable "api_execution_arn" {
  description = "Execution ARN of the shared HTTP API (from the platform stack)"
  type        = string
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "route_key" {
  description = "HTTP method and path, e.g. 'GET /hello' or 'POST /orders'"
  type        = string

  validation {
    condition     = can(regex("^(GET|POST|PUT|PATCH|DELETE) /", var.route_key))
    error_message = "route_key must look like 'GET /path'."
  }
}

variable "source_dir" {
  description = "Folder containing the function code"
  type        = string
}

variable "handler" {
  description = "Python handler, file.function"
  type        = string
  default     = "handler.lambda_handler"
}

variable "memory_size" {
  type    = number
  default = 128
}

variable "timeout" {
  type    = number
  default = 10
}

variable "environment" {
  description = "Environment variables for the function"
  type        = map(string)
  default     = {}
}
