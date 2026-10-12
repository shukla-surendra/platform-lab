variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "az_count" {
  type = number
}

variable "enable_nat" {
  type = bool
}

variable "force_destroy" {
  type = bool
}

variable "noncurrent_retention_days" {
  type = number
}
