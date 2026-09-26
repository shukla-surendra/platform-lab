variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag. The bucket name gets a random suffix (S3 bucket names are globally unique across ALL AWS accounts)."
  type        = string
  default     = "aws-mastery-s3-kms"
}

variable "kms_deletion_window_days" {
  description = "Waiting period (7-30 days) between scheduling the key for deletion and it actually being destroyed. During this window the key is unusable but recoverable — everything encrypted with it is unreadable if you let it lapse."
  type        = number
  default     = 7

  validation {
    condition     = var.kms_deletion_window_days >= 7 && var.kms_deletion_window_days <= 30
    error_message = "kms_deletion_window_days must be between 7 and 30."
  }
}

variable "enable_key_rotation" {
  description = "Rotate the key's backing material automatically every year. Old material is kept, so existing objects still decrypt — no re-encryption needed."
  type        = bool
  default     = true
}

variable "key_admin_arns" {
  description = "IAM principal ARNs allowed to MANAGE the key (rotate, disable, schedule deletion, edit policy) but not use it to encrypt/decrypt. Empty = only the account root (and IAM policies) administer it."
  type        = list(string)
  default     = []
}

variable "key_user_arns" {
  description = "IAM principal ARNs allowed to USE the key (Encrypt/Decrypt/GenerateDataKey) via the key policy. Empty = access is granted only through IAM policies in the account (the key policy delegates to IAM via the root statement)."
  type        = list(string)
  default     = []
}

variable "versioning_enabled" {
  description = "Keep every previous version of every object."
  type        = bool
  default     = true
}

variable "enable_lifecycle_rules" {
  description = "Transition noncurrent versions to STANDARD_IA, then expire them — bounds the cost of versioning."
  type        = bool
  default     = true
}

variable "noncurrent_version_transition_days" {
  description = "Days before a NONCURRENT version moves to STANDARD_IA."
  type        = number
  default     = 30
}

variable "noncurrent_version_expiration_days" {
  description = "Days before a NONCURRENT version is deleted entirely."
  type        = number
  default     = 90
}

variable "force_destroy" {
  description = "Let `terraform destroy` delete the bucket even if it still holds objects/versions. Leave false for anything you care about."
  type        = bool
  default     = false
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
