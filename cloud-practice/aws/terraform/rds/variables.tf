variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag, and the DB identifier."
  type        = string
  default     = "aws-mastery-rds"
}

variable "engine_version" {
  description = "PostgreSQL major.minor version."
  type        = string
  default     = "16.4"
}

variable "instance_class" {
  description = "db.t3.micro is Free-Tier eligible in most accounts."
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage_gib" {
  description = "Initial storage size (gp3)."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Default database name created inside the instance."
  type        = string
  default     = "appdb"
}

variable "master_username" {
  description = "Master username."
  type        = string
  default     = "dbadmin"
}

variable "multi_az" {
  description = "Standby replica in a second AZ, synchronous replication, automatic failover. Roughly doubles cost."
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Automated backup retention (0 disables automated backups entirely)."
  type        = number
  default     = 7
}

variable "skip_final_snapshot" {
  description = "true = destroy leaves NOTHING behind (convenient for a lab). false (the prod default) forces a final snapshot on destroy so data survives an accidental terraform destroy."
  type        = bool
  default     = true
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
