variable "region" {
  description = "AWS region (CloudFront is global, but its S3 bucket policy resource needs a home region for the provider)."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag."
  type        = string
  default     = "aws-mastery-cloudfront"
}

variable "origin_bucket_name" {
  description = "bucket_name output from the s3/ module — required."
  type        = string
}

variable "origin_bucket_arn" {
  description = "bucket_arn output from the s3/ module — required (used in the bucket policy)."
  type        = string
}

variable "origin_bucket_regional_domain_name" {
  description = "bucket_regional_domain_name output from the s3/ module — required."
  type        = string
}

variable "default_root_object" {
  description = "Object served at the distribution's bare root path."
  type        = string
  default     = "index.html"
}

variable "price_class" {
  description = "PriceClass_100 (NA+EU only, cheapest) / _200 (+ Asia) / _All (+ South America/Australia, priciest)."
  type        = string
  default     = "PriceClass_100"
}

variable "default_ttl_seconds" {
  description = "How long CloudFront caches an object with no explicit Cache-Control header from the origin."
  type        = number
  default     = 3600
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
