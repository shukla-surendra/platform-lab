variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag."
  type        = string
  default     = "aws-mastery-batch"
}

variable "container_image" {
  description = "Image the job runs. Defaults to a public image so this applies with zero other modules; point it at ecr/'s repository_url:tag for your own."
  type        = string
  default     = "public.ecr.aws/docker/library/busybox:latest"
}

variable "command" {
  description = "Container command/args (list form, like ECS/Docker's CMD)."
  type        = list(string)
  default     = ["sh", "-c", "echo Job started at $(date -u); sleep 10; echo Job finished at $(date -u)"]
}

variable "vcpus" {
  description = "Fargate vCPU units for one job (e.g. \"0.25\", \"0.5\", \"1\")."
  type        = string
  default     = "0.25"
}

variable "memory_mib" {
  description = "Fargate memory (MiB) for one job. Must be a valid (vcpu, memory) Fargate pair."
  type        = string
  default     = "512"
}

variable "max_vcpus" {
  description = "Ceiling on TOTAL vCPUs running across all concurrent jobs in this compute environment — Batch queues extra jobs instead of running them once this is hit."
  type        = number
  default     = 4
}

variable "use_fargate_spot" {
  description = "FARGATE_SPOT runs jobs on spare capacity at up to ~70% off, but AWS can reclaim it mid-job (Batch automatically retries on a SPOT interruption) — a good fit for retriable batch work, a bad fit for anything that can't tolerate a restart."
  type        = bool
  default     = false
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
