variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short name used to prefix/namespace resources and tags."
  type        = string
  default     = "vpc-multi-subnet"
}

variable "environment" {
  description = "Environment name (dev/staging/prod). Used in tags."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "Primary CIDR block for the VPC."
  type        = string
  default     = "10.10.0.0/16"
}

variable "azs" {
  description = "Availability Zones to spread subnets across. One public + one private subnet is created per AZ, so length(azs) >= 2 gives at least 2 public and 2 private subnets."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_newbits" {
  description = "Bits added to the VPC prefix to size each public /subnet (cidrsubnet newbits)."
  type        = number
  default     = 8
}

variable "private_subnet_newbits" {
  description = "Bits added to the VPC prefix to size each private /subnet (cidrsubnet newbits)."
  type        = number
  default     = 8
}

variable "single_nat_gateway" {
  description = <<-EOT
    true  = ONE NAT Gateway shared by all AZs (cheaper; single-AZ egress failure
            domain + cross-AZ data charges). Good for dev/practice.
    false = ONE NAT Gateway PER AZ (prod default: HA, no cross-AZ egress $).
  EOT
  type        = bool
  default     = true
}

variable "enable_dns_hostnames" {
  description = "Enable DNS hostnames in the VPC."
  type        = bool
  default     = true
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
