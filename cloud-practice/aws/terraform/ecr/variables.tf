variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag, and the repository name."
  type        = string
  default     = "aws-mastery-ecr"
}

variable "scan_on_push" {
  description = "Run Amazon ECR's basic vulnerability scan automatically on every push."
  type        = bool
  default     = true
}

variable "image_tag_mutability" {
  description = "MUTABLE lets you overwrite a tag like `latest`. IMMUTABLE (prod recommendation) rejects a re-push of an existing tag, forcing every build to produce a unique tag."
  type        = string
  default     = "IMMUTABLE"
}

variable "max_image_count" {
  description = "Lifecycle policy: keep only the N most recent images (per tag prefix `untagged` / all) — keeps storage cost and clutter bounded."
  type        = number
  default     = 10
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
