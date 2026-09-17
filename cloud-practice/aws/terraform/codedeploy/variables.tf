variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag, and the CodeDeploy application name."
  type        = string
  default     = "aws-mastery-codedeploy"
}

variable "asg_names" {
  description = "Auto Scaling Group name(s) to deploy onto — pass in autoscaling/'s asg_name output. Empty list = deployment group created with no compute target yet (fill in later)."
  type        = list(string)
  default     = []
}

variable "target_group_name" {
  description = "If set (from alb/'s target group), CodeDeploy also registers/deregisters instances with this ALB target group during a deployment instead of just the ASG's own attachment."
  type        = string
  default     = ""
}

variable "deployment_config_name" {
  description = <<-EOT
    How many instances get the new revision at once:
      CodeDeployDefault.OneAtATime   — safest, slowest (this default)
      CodeDeployDefault.HalfAtATime  — faster, tolerates one bad half
      CodeDeployDefault.AllAtOnce    — fastest, no safety net
  EOT
  type        = string
  default     = "CodeDeployDefault.OneAtATime"
}

variable "auto_rollback_on_failure" {
  description = "If true, a failed deployment automatically rolls back to the last known-good revision."
  type        = bool
  default     = true
}

variable "artifact_bucket_name" {
  description = "If set, reuse an existing S3 bucket for deployment revisions (e.g. codebuild/'s or codepipeline/'s bucket). If empty, this module creates its own."
  type        = string
  default     = ""
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
