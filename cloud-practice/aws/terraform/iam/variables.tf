variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag."
  type        = string
  default     = "aws-mastery-iam"
}
