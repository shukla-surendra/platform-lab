variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag, and the function name."
  type        = string
  default     = "aws-mastery-lambda"
}

variable "runtime" {
  description = "Lambda runtime. Matches the handler in src/index.py by default."
  type        = string
  default     = "python3.12"
}

variable "handler" {
  description = "module.function the runtime invokes."
  type        = string
  default     = "index.handler"
}

variable "memory_size" {
  description = "MB of memory (also scales proportional CPU/network — this is Lambda's ONE sizing knob)."
  type        = number
  default     = 128
}

variable "timeout" {
  description = "Max seconds before Lambda kills the invocation."
  type        = number
  default     = 10
}

variable "environment_variables" {
  description = "Environment variables passed to the function."
  type        = map(string)
  default     = {}
}

variable "enable_function_url" {
  description = "If true, expose a public HTTPS Function URL — the fastest way to invoke over HTTP with zero API Gateway setup."
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for this function's log group."
  type        = number
  default     = 14
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
