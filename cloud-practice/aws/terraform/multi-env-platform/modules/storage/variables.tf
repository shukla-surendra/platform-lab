variable "name" {
  type = string
}

variable "suffix" {
  type        = string
  description = "Uniqueness suffix (e.g. AWS account id)"
}

variable "versioning" {
  type    = bool
  default = true
}

variable "force_destroy" {
  type    = bool
  default = false
}

variable "noncurrent_retention_days" {
  type    = number
  default = 30
}
