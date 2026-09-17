variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag. The actual bucket name gets a random suffix (S3 bucket names are globally unique across ALL AWS accounts)."
  type        = string
  default     = "aws-mastery-s3"
}

variable "versioning_enabled" {
  description = "Keep every previous version of every object — protects against accidental overwrite/delete, at the cost of storing every version."
  type        = bool
  default     = true
}

variable "enable_lifecycle_rules" {
  description = "Auto-transition noncurrent versions to cheaper storage, then expire them — bounds the storage cost of versioning being on."
  type        = bool
  default     = true
}

variable "noncurrent_version_transition_days" {
  description = "Days before a NONCURRENT (superseded) version moves to STANDARD_IA."
  type        = number
  default     = 30
}

variable "noncurrent_version_expiration_days" {
  description = "Days before a NONCURRENT version is deleted entirely."
  type        = number
  default     = 90
}

variable "enable_static_website" {
  description = "Serve this bucket as a static website (index/error documents). Pairs with cloudfront/ as the origin."
  type        = bool
  default     = false
}

variable "index_document" {
  description = "Static website index document."
  type        = string
  default     = "index.html"
}

variable "error_document" {
  description = "Static website error document."
  type        = string
  default     = "error.html"
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
