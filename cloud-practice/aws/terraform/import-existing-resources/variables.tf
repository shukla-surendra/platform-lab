variable "region" {
  description = "AWS region the pre-existing resource lives in."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short name used to prefix/namespace resources and tags."
  type        = string
  default     = "import-practice"
}

variable "environment" {
  description = "Environment name. Used in tags."
  type        = string
  default     = "dev"
}

variable "bucket_name" {
  description = <<-EOT
    Name of the ALREADY-EXISTING S3 bucket to bring under Terraform
    management. Create it out-of-band first (see scripts/create-manual-bucket.sh)
    -- do NOT invent a name here and expect Terraform to create it; the whole
    point of this module is that the bucket already exists before `terraform`
    is ever run against it.
  EOT
  type        = string
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
