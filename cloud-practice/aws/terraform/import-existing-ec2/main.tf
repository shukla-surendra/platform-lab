##############################################################################
# Locals + lookups
##############################################################################
locals {
  name = var.project
  tags = merge(
    {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
      Module      = "aws/terraform/import-existing-ec2"
    },
    var.extra_tags,
  )
}

# Same default-VPC pattern as ../ec2/ -- scripts/create-manual-ec2.sh
# launches into the default VPC too, so this lookup finds the real subnet.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "in_az" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = [var.availability_zone]
  }
}

##############################################################################
# aws_security_group.imported
#
# Cleaned-up version of what `generate-config-out` drafts for the SG that
# scripts/create-manual-ec2.sh creates. Deleted from the raw draft: `id`,
# `arn`, `owner_id`, `name_prefix` (null, conflicts with `name`), and the
# generator's per-rule `security_group_rule` computed blocks in favor of the
# plain `ingress`/`egress` blocks actually used to create it.
##############################################################################
resource "aws_security_group" "imported" {
  name        = "${local.name}-sg"
  description = "Imported: SSH access for the manually-created practice instance"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  egress {
    description = "all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-sg" }
}

##############################################################################
# aws_instance.imported
#
# Cleaned-up version of the `generate-config-out` draft. Deleted from the
# raw draft: every computed-only attribute the generator includes but that
# isn't valid/safe to set by hand -- arn, instance_state, primary_network_interface_id,
# private_dns, public_dns, public_ip, private_ip, network_interface{} blocks,
# credit_specification (left at its account default), capacity_reservation_specification,
# and the root_block_device's device_name/volume_id/tags (computed once created).
#
# KEPT deliberately, because they're the arguments that actually describe
# "what this box is" and matter for drift detection: ami, instance_type,
# subnet_id, vpc_security_group_ids, root_block_device sizing/encryption, tags.
##############################################################################
resource "aws_instance" "imported" {
  ami                    = var.ami_id     # see variables.tf -- MUST match the real instance exactly (ForceNew)
  private_ip             = var.private_ip # ditto -- ForceNew, pin it to the real value (see README)
  instance_type          = var.instance_type
  availability_zone      = var.availability_zone
  subnet_id              = data.aws_subnets.in_az.ids[0]
  vpc_security_group_ids = [aws_security_group.imported.id]

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  tags = { Name = local.name }
}

##############################################################################
# aws_eip.imported -- THIS is the mechanism that actually preserves a
# public IP in Terraform: an Elastic IP is a standalone resource. Setting
# `instance = aws_instance.imported.id` associates it; if the instance is
# ever replaced (e.g. someone changes `ami_id`), Terraform re-associates
# the SAME EIP with the new instance's id as an in-place update on
# aws_eip.imported -- the EIP itself, and its public IP, never changes.
#
# Cleaned up from the generate-config-out draft the same way as the other
# two resources: dropped `id`, `public_ip` (computed, this is the OUTPUT of
# the resource, not an input), `private_ip` (computed, redundant with the
# one already set on aws_instance), `network_interface`/`association_id`
# (computed).
##############################################################################
resource "aws_eip" "imported" {
  domain   = "vpc"
  instance = aws_instance.imported.id

  tags = { Name = "${local.name}-eip" }
}
