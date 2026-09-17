variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag."
  type        = string
  default     = "aws-mastery-asg"
}

variable "instance_type" {
  description = "EC2 instance type used by the launch template."
  type        = string
  default     = "t3.micro"
}

variable "min_size" {
  description = "Minimum number of instances."
  type        = number
  default     = 1
}

variable "max_size" {
  description = "Maximum number of instances."
  type        = number
  default     = 3
}

variable "desired_capacity" {
  description = "Starting/steady-state instance count."
  type        = number
  default     = 2
}

variable "target_group_arn" {
  description = "If set, attach the ASG to this ALB target group (from the alb/ module) for load-balanced health checks. Leave empty to run without a load balancer."
  type        = string
  default     = ""
}

variable "enable_target_tracking" {
  description = "If true, add a target-tracking scaling policy on average CPU utilization instead of a fixed desired_capacity."
  type        = bool
  default     = true
}

variable "target_cpu_percent" {
  description = "Target average CPU % the scaling policy tries to hold."
  type        = number
  default     = 50
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
