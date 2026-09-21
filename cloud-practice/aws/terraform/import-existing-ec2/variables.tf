variable "region" {
  description = "AWS region the pre-existing instance lives in."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short name used to prefix/namespace resources and tags."
  type        = string
  default     = "import-practice-ec2"
}

variable "environment" {
  description = "Environment name. Used in tags."
  type        = string
  default     = "dev"
}

variable "availability_zone" {
  description = "AZ the manually-created instance is in (must have a default subnet)."
  type        = string
  default     = "us-east-1a"
}

variable "instance_id" {
  description = <<-EOT
    ID of the ALREADY-EXISTING EC2 instance to bring under Terraform
    management (e.g. "i-0123456789abcdef0"), printed by
    scripts/create-manual-ec2.sh. Do NOT invent one -- the instance must
    exist before terraform is ever run against it.
  EOT
  type        = string
}

variable "security_group_id" {
  description = <<-EOT
    ID of the ALREADY-EXISTING security group attached to that instance
    (e.g. "sg-0123456789abcdef0"), also printed by
    scripts/create-manual-ec2.sh.
  EOT
  type        = string
}

variable "ami_id" {
  description = <<-EOT
    AMI ID the existing instance is ACTUALLY running. `ami` is a
    ForceNew argument on aws_instance -- if this doesn't exactly match the
    real instance, `terraform plan` won't show "No changes", it'll show a
    destructive REPLACE. Find the real value with:
      aws ec2 describe-instances --instance-ids <id> \
        --query 'Reservations[0].Instances[0].ImageId' --output text
    or just read it out of generated.tf, don't retype it from memory.
  EOT
  type        = string
}

variable "instance_type" {
  description = "Instance type of the existing instance (t3.micro is Free-Tier eligible)."
  type        = string
  default     = "t3.micro"
}

variable "private_ip" {
  description = <<-EOT
    Primary private IP the existing instance is ACTUALLY using (e.g.
    "10.0.1.23"), printed by scripts/create-manual-ec2.sh. `private_ip` is
    a ForceNew argument on aws_instance, same trap as `ami_id` above -- get
    it from the real instance (`aws ec2 describe-instances ... --query
    'Reservations[0].Instances[0].PrivateIpAddress'`), never guess it, or
    the first apply after import will destroy and recreate the box.
  EOT
  type        = string
}

variable "eip_allocation_id" {
  description = <<-EOT
    Allocation ID (e.g. "eipalloc-0123456789abcdef0") of the Elastic IP
    scripts/create-manual-ec2.sh associates with the instance. This is
    what actually makes the instance's public IP durable -- an EIP survives
    instance replacement (Terraform re-associates it), unlike the default
    ephemeral public IP, which is just a computed attribute and cannot be
    "preserved" by Terraform at all. See README "Preserving IP addresses".
  EOT
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach port 22 on the imported security group."
  type        = string
  default     = "0.0.0.0/0"
}

variable "extra_tags" {
  description = "Additional tags merged into the default tag set."
  type        = map(string)
  default     = {}
}
