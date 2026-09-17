variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag, and the repository name."
  type        = string
  default     = "aws-mastery-codecommit"
}

variable "default_branch" {
  description = "Branch CodeBuild/CodePipeline will watch by default."
  type        = string
  default     = "main"
}

variable "seed_readme" {
  description = <<-EOT
    If true, shells out to `git` to push an initial README.md so the repo
    isn't empty (CodePipeline's CodeCommit source action fails on a truly
    empty repo). Requires the AWS CodeCommit git credential helper already
    configured locally (see README) — defaults to false so a fresh `apply`
    never hangs on a credential prompt.
  EOT
  type        = bool
  default     = false
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
