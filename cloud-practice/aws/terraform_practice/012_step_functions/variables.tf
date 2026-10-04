variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  description = "Prefix for resource names"
  type        = string
  default     = "sfn-lab"
}
