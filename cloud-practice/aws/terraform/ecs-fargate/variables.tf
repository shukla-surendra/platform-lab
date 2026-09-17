variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag."
  type        = string
  default     = "aws-mastery-ecs"
}

variable "container_image" {
  description = "Image to run. Defaults to a public demo image so this applies with zero other modules; point it at ecr/'s repository_url:tag for your own image."
  type        = string
  default     = "public.ecr.aws/docker/library/httpd:2.4"
}

variable "container_port" {
  description = "Port the container listens on."
  type        = number
  default     = 80
}

variable "cpu" {
  description = "Fargate task vCPU units (256 = .25 vCPU). Must be a valid (cpu, memory) Fargate pair."
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate task memory in MiB. Must be a valid (cpu, memory) Fargate pair."
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Number of task copies the service keeps running."
  type        = number
  default     = 2
}

variable "target_group_arn" {
  description = "If set (from alb/'s output), register tasks with this ALB target group instead of assigning each task a public IP."
  type        = string
  default     = ""
}

variable "assign_public_ip" {
  description = "Give each task a public IP directly (only relevant with no load balancer — set false once you attach target_group_arn)."
  type        = bool
  default     = true
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
