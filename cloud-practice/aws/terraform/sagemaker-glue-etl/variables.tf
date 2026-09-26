variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag. The bucket name gets a random suffix (S3 bucket names are globally unique across ALL AWS accounts). Lowercase letters, digits and hyphens only."
  type        = string
  default     = "aws-mastery-sm-glue"
}

variable "kms_key_arn" {
  description = "Optional customer-managed KMS key ARN (e.g. the kms_key_arn output of ../s3-kms). When set: the bucket uses SSE-KMS, Glue writes are encrypted with it via a security configuration, the notebook's ML volume is encrypted with it, and both roles get key permissions. Empty = SSE-S3 (AES256)."
  type        = string
  default     = ""
}

variable "force_destroy" {
  description = "Let `terraform destroy` delete the bucket even if it holds data. Defaults to true because everything in it is reproducible from the sample data + job."
  type        = bool
  default     = true
}

variable "upload_sample_data" {
  description = "Upload data/sample_orders.csv to raw/orders/ so the job has something to process out of the box."
  type        = bool
  default     = true
}

# --- Glue ---------------------------------------------------------------

variable "glue_version" {
  description = "Glue runtime version (Spark/Python). 4.0 = Spark 3.3 / Python 3.10; 5.0 = Spark 3.5 / Python 3.11."
  type        = string
  default     = "4.0"
}

variable "glue_worker_type" {
  description = "Glue worker type. G.1X = 4 vCPU / 16 GB, 1 DPU."
  type        = string
  default     = "G.1X"
}

variable "glue_number_of_workers" {
  description = "Number of workers (minimum 2). Glue bills per DPU-hour, so keep this small for a lab."
  type        = number
  default     = 2

  validation {
    condition     = var.glue_number_of_workers >= 2
    error_message = "Glue requires at least 2 workers."
  }
}

variable "glue_job_timeout_minutes" {
  description = "Hard stop for a run — the guard against a stuck job billing forever."
  type        = number
  default     = 30
}

variable "enable_job_bookmark" {
  description = "Job bookmarks: on re-runs, only process raw files not seen by a previous successful run (incremental ETL)."
  type        = bool
  default     = true
}

variable "schedule_cron" {
  description = "Optional Glue cron schedule for the ETL job, e.g. \"cron(0 2 * * ? *)\" for 02:00 UTC daily. Empty = run on demand only."
  type        = string
  default     = ""
}

# --- SageMaker ----------------------------------------------------------

variable "create_notebook_instance" {
  description = "Create a SageMaker notebook instance wired to the curated data. It bills per hour while InService — stop it (or set this false) when idle."
  type        = bool
  default     = true
}

variable "notebook_instance_type" {
  description = "Notebook instance type."
  type        = string
  default     = "ml.t3.medium"
}

variable "notebook_volume_size_gb" {
  description = "Notebook EBS volume size in GB."
  type        = number
  default     = 5
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
