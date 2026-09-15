variable "project_id" {
  description = "GCP project id to target."
  type        = string
  default     = "llm-training-dev"
}

variable "region" {
  description = "Region for the bucket."
  type        = string
  default     = "us-central1"
}
