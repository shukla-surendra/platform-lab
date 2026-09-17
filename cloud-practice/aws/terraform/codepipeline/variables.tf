variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag, and the pipeline name."
  type        = string
  default     = "aws-mastery-codepipeline"
}

variable "source_type" {
  description = "CODECOMMIT (push-triggered via EventBridge) or GITHUB (via an already-authorized CodeStar Connection)."
  type        = string
  default     = "CODECOMMIT"

  validation {
    condition     = contains(["CODECOMMIT", "GITHUB"], var.source_type)
    error_message = "source_type must be CODECOMMIT or GITHUB."
  }
}

variable "codecommit_repository_name" {
  description = "Repository name from the codecommit/ module's output. Required if source_type = CODECOMMIT."
  type        = string
  default     = ""
}

variable "branch_name" {
  description = "Branch this pipeline watches."
  type        = string
  default     = "main"
}

variable "codestar_connection_arn" {
  description = "ARN of an authorized CodeStar Connection (console-only setup — see codebuild/'s README). Required if source_type = GITHUB."
  type        = string
  default     = ""
}

variable "github_full_repository_id" {
  description = "\"<org>/<repo>\" — required if source_type = GITHUB."
  type        = string
  default     = ""
}

variable "codebuild_project_name" {
  description = "CodeBuild project name from the codebuild/ module's output."
  type        = string
}

variable "codedeploy_application_name" {
  description = "CodeDeploy application name from the codedeploy/ module's output."
  type        = string
}

variable "codedeploy_deployment_group_name" {
  description = "CodeDeploy deployment group name from the codedeploy/ module's output."
  type        = string
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
