# ---------------------------------------------------------------------------
# Inputs: change these without touching the resource code
# ---------------------------------------------------------------------------

variable "region" {
  description = "AWS region for everything"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster (also used to name/tag related resources)"
  type        = string
  default     = "eks-lab"
}

variable "kubernetes_version" {
  description = <<-EOT
    Kubernetes version. Pick one in STANDARD support: versions that fall into
    EXTENDED support cost much more per cluster-hour.
    Check: aws eks describe-cluster-versions --region us-east-1
  EOT
  type        = string
  default     = "1.36"
}

variable "vpc_cidr" {
  description = "IP range of the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "azs" {
  description = "Two Availability Zones. EKS requires subnets in at least 2 AZs."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "One CIDR per AZ, in the same order as var.azs"
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "node_instance_types" {
  description = "EC2 types for worker nodes"
  type        = list(string)
  default     = ["t3.small"]
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 2
}
