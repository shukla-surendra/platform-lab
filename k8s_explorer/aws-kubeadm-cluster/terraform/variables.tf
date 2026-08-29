variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short name used to prefix/tag every resource, so this stack is easy to find and easy to confirm fully destroyed."
  type        = string
  default     = "kubeadm-poc"
}

variable "allowed_ssh_cidr" {
  description = <<-EOT
    Your own IP, as a /32 CIDR (e.g. "203.0.113.7/32") — find it with `curl -s ifconfig.me`.
    Deliberately has NO default: opening SSH to 0.0.0.0/0 on a real AWS account is a
    mistake worth being forced to actively avoid, not something to default your way past.
  EOT
  type        = string

  validation {
    condition     = can(cidrhost(var.allowed_ssh_cidr, 0)) && endswith(var.allowed_ssh_cidr, "/32")
    error_message = "allowed_ssh_cidr must be a single-IP /32 CIDR, e.g. 203.0.113.7/32 — not a range and not 0.0.0.0/0."
  }
}

variable "instance_type" {
  description = <<-EOT
    kubeadm's preflight check requires >= 2 vCPU and >= 2 GiB RAM on EVERY node
    (control-plane AND workers) — t3.small is the real minimum, not t3.micro.
    See docs/CONCEPTS.md for why this check exists and what it's protecting against.
  EOT
  type        = string
  default     = "t3.small"
}

variable "worker_count" {
  description = "Number of worker nodes, in addition to the one control-plane node."
  type        = number
  default     = 2
}

variable "root_volume_gb" {
  description = "Root EBS volume size per node. 20 GB covers containerd + pulled images comfortably for a POC; the default 8 GB Ubuntu ships with is tight once several images are pulled."
  type        = number
  default     = 20
}
