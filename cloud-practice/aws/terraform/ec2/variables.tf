variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix / tag."
  type        = string
  default     = "aws-mastery-ec2"
}

variable "instance_type" {
  description = "EC2 instance type. t3.micro is Free-Tier eligible in most accounts."
  type        = string
  default     = "t3.micro"
}

variable "availability_zone" {
  description = "AZ to launch into (must have a default subnet)."
  type        = string
  default     = "us-east-1a"
}

variable "allowed_ssh_cidr" {
  description = <<-EOT
    CIDR allowed to reach port 22. Left as 0.0.0.0/0 makes the lab easy but is
    NOT a production pattern — in prod this is your VPN/bastion CIDR, never
    the whole internet. SSM Session Manager (used by default here) avoids
    needing SSH open at all; only widen this if you actually need key-based SSH.
  EOT
  type        = string
  default     = "0.0.0.0/0"
}

variable "install_web_server" {
  description = "If true, user_data installs and starts a simple httpd landing page (opens port 80)."
  type        = bool
  default     = true
}

variable "associate_eip" {
  description = "Attach a static Elastic IP instead of relying on the ephemeral public IP."
  type        = bool
  default     = false
}

variable "root_volume_size_gib" {
  description = "Root (gp3) volume size."
  type        = number
  default     = 8
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
