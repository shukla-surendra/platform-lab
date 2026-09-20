variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix for every resource this creates. Differs from 003's default so both can coexist."
  type        = string
  default     = "cicd-practice-v2"
}

variable "branch_name" {
  description = "Branch the push trigger (EventBridge) and the Source stage watch."
  type        = string
  default     = "main"
}

variable "instance_type" {
  description = "EC2 deploy-target instance type."
  type        = string
  default     = "t3.micro"
}
