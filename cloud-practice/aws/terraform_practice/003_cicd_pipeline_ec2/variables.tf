# Given complete on purpose — the learning point of this exercise is wiring
# resources together, not guessing variable syntax. Reference these as
# var.<name> in the TODOs you fill in across the other files.

variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix for every resource this creates."
  type        = string
  default     = "cicd-practice"
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach port 22 on the EC2 target. Set to YOUR_IP/32."
  type        = string
  default     = "0.0.0.0/0"
}

variable "branch_name" {
  description = "Branch CodeBuild/CodePipeline watches."
  type        = string
  default     = "main"
}
