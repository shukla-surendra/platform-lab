variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag, and the table name."
  type        = string
  default     = "aws-mastery-dynamodb"
}

variable "hash_key" {
  description = "Partition key name."
  type        = string
  default     = "pk"
}

variable "range_key" {
  description = "Sort key name. Empty string = no sort key (simple primary key instead of composite)."
  type        = string
  default     = "sk"
}

variable "billing_mode" {
  description = "PAY_PER_REQUEST (scales automatically, pay per request — the sane default for spiky/unknown traffic) or PROVISIONED (fixed RCU/WCU, cheaper ONLY at sustained high, predictable throughput)."
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "enable_point_in_time_recovery" {
  description = "Continuous backups letting you restore to any point in the last 35 days — the DynamoDB equivalent of RDS automated backups."
  type        = bool
  default     = true
}

variable "enable_ttl" {
  description = "If true, items with a numeric ttl_attribute_name in the past are automatically deleted by DynamoDB at no extra cost."
  type        = bool
  default     = true
}

variable "ttl_attribute_name" {
  description = "Attribute holding a Unix epoch (seconds) after which the item expires."
  type        = string
  default     = "expires_at"
}

variable "enable_stream" {
  description = "Turn on a DynamoDB Stream (change feed) — the trigger source for the sns-sqs/'s optional Lambda-on-table-change pattern."
  type        = bool
  default     = false
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
