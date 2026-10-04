# ===========================================================================
# 015 – Transit Gateway demo: A, B, C all attach to ONE hub
# ===========================================================================
#            VPC A 10.10.0.0/16 ──┐
#            VPC B 10.20.0.0/16 ──┼── Transit Gateway (the hub / router)
#            VPC C 10.30.0.0/16 ──┘
#
# Compare with lesson 014 (peering): there A and C could NOT talk. Here every
# attached VPC can reach every other one (transitive, via the hub), and adding a
# 4th VPC costs one attachment, not three new peerings.
#
# Learning goals:
#   1. Attachment (VPC <-> TGW), TGW route tables, association and propagation.
#   2. VPC route tables still need a route pointing at the TGW.
#   3. Segmentation: isolate_vpc_c=true gives C its own, empty TGW route table,
#      so C cannot reach anyone and nobody can reach C.

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "az" {
  type    = string
  default = "us-east-1a"
}

variable "isolate_vpc_c" {
  description = "true = VPC C is attached but segmented off (own empty TGW route table)"
  type        = bool
  default     = false
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = "tgw-lab"
      Managed = "terraform"
    }
  }
}

locals {
  lab_supernet = "10.0.0.0/8" # one summary route in each VPC covers all lab VPCs
}

module "vpc_a" {
  source                = "../net_modules/test_vpc"
  name                  = "tgw-a"
  cidr                  = "10.10.0.0/16"
  az                    = var.az
  allowed_ingress_cidrs = [local.lab_supernet]
}

module "vpc_b" {
  source                = "../net_modules/test_vpc"
  name                  = "tgw-b"
  cidr                  = "10.20.0.0/16"
  az                    = var.az
  allowed_ingress_cidrs = [local.lab_supernet]
}

module "vpc_c" {
  source                = "../net_modules/test_vpc"
  name                  = "tgw-c"
  cidr                  = "10.30.0.0/16"
  az                    = var.az
  allowed_ingress_cidrs = [local.lab_supernet]
}

# ---------------------------------------------------------------------------
# The Transit Gateway
# ---------------------------------------------------------------------------
# We DISABLE the default route table association/propagation so the routing is
# explicit and visible in this file (and so segmentation is possible).
resource "aws_ec2_transit_gateway" "this" {
  description                     = "tgw lab"
  default_route_table_association = "disable"
  default_route_table_propagation = "disable"
  dns_support                     = "enable"
  tags                            = { Name = "tgw-lab" }
}

# ---------------------------------------------------------------------------
# Attachments: connect each VPC to the TGW (one subnet per AZ you want served).
# Each attachment creates an ENI in that subnet. Billed per attachment-hour.
# ---------------------------------------------------------------------------
resource "aws_ec2_transit_gateway_vpc_attachment" "a" {
  transit_gateway_id = aws_ec2_transit_gateway.this.id
  vpc_id             = module.vpc_a.vpc_id
  subnet_ids         = [module.vpc_a.subnet_id]

  # We manage association/propagation explicitly below (the TGW defaults are disabled anyway)
  transit_gateway_default_route_table_association = false
  transit_gateway_default_route_table_propagation = false

  tags = { Name = "tgw-a" }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "b" {
  transit_gateway_id = aws_ec2_transit_gateway.this.id
  vpc_id             = module.vpc_b.vpc_id
  subnet_ids         = [module.vpc_b.subnet_id]

  # We manage association/propagation explicitly below (the TGW defaults are disabled anyway)
  transit_gateway_default_route_table_association = false
  transit_gateway_default_route_table_propagation = false

  tags = { Name = "tgw-b" }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "c" {
  transit_gateway_id = aws_ec2_transit_gateway.this.id
  vpc_id             = module.vpc_c.vpc_id
  subnet_ids         = [module.vpc_c.subnet_id]

  # We manage association/propagation explicitly below (the TGW defaults are disabled anyway)
  transit_gateway_default_route_table_association = false
  transit_gateway_default_route_table_propagation = false

  tags = { Name = "tgw-c" }
}

# ---------------------------------------------------------------------------
# TGW route tables
#   ASSOCIATION  = which route table an attachment's OUTGOING traffic is looked up in
#   PROPAGATION  = which route tables LEARN the attachment's CIDR automatically
# "main" is shared by A and B (and by C unless isolated).
# "isolated" is only for C when isolate_vpc_c = true, and stays empty.
# ---------------------------------------------------------------------------
resource "aws_ec2_transit_gateway_route_table" "main" {
  transit_gateway_id = aws_ec2_transit_gateway.this.id
  tags               = { Name = "tgw-main" }
}

resource "aws_ec2_transit_gateway_route_table" "isolated" {
  count              = var.isolate_vpc_c ? 1 : 0
  transit_gateway_id = aws_ec2_transit_gateway.this.id
  tags               = { Name = "tgw-isolated" }
}

# Associations (exactly one per attachment)
resource "aws_ec2_transit_gateway_route_table_association" "a" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.a.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

resource "aws_ec2_transit_gateway_route_table_association" "b" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.b.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

resource "aws_ec2_transit_gateway_route_table_association" "c" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.c.id
  transit_gateway_route_table_id = var.isolate_vpc_c ? aws_ec2_transit_gateway_route_table.isolated[0].id : aws_ec2_transit_gateway_route_table.main.id
}

# Propagations: make "main" learn the CIDRs of A and B (and C unless isolated)
resource "aws_ec2_transit_gateway_route_table_propagation" "a" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.a.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

resource "aws_ec2_transit_gateway_route_table_propagation" "b" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.b.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

resource "aws_ec2_transit_gateway_route_table_propagation" "c" {
  count                          = var.isolate_vpc_c ? 0 : 1
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.c.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

# ---------------------------------------------------------------------------
# VPC side: send all lab traffic (10.0.0.0/8) to the TGW. Without these routes the
# VPCs have no idea the other VPCs exist, even though the TGW is fully set up.
# More specific routes win: each VPC's own CIDR stays "local".
# ---------------------------------------------------------------------------
resource "aws_route" "a_to_tgw" {
  route_table_id         = module.vpc_a.route_table_id
  destination_cidr_block = local.lab_supernet
  transit_gateway_id     = aws_ec2_transit_gateway.this.id
  depends_on             = [aws_ec2_transit_gateway_vpc_attachment.a]
}

resource "aws_route" "b_to_tgw" {
  route_table_id         = module.vpc_b.route_table_id
  destination_cidr_block = local.lab_supernet
  transit_gateway_id     = aws_ec2_transit_gateway.this.id
  depends_on             = [aws_ec2_transit_gateway_vpc_attachment.b]
}

resource "aws_route" "c_to_tgw" {
  route_table_id         = module.vpc_c.route_table_id
  destination_cidr_block = local.lab_supernet
  transit_gateway_id     = aws_ec2_transit_gateway.this.id
  depends_on             = [aws_ec2_transit_gateway_vpc_attachment.c]
}

# ---------------------------------------------------------------------------
# Outputs used by scripts/test_tgw.sh
# ---------------------------------------------------------------------------
output "a_instance_id" { value = module.vpc_a.instance_id }
output "b_instance_id" { value = module.vpc_b.instance_id }
output "c_instance_id" { value = module.vpc_c.instance_id }
output "a_ip" { value = module.vpc_a.private_ip }
output "b_ip" { value = module.vpc_b.private_ip }
output "c_ip" { value = module.vpc_c.private_ip }
output "c_isolated" { value = var.isolate_vpc_c }
output "tgw_id" { value = aws_ec2_transit_gateway.this.id }
output "main_route_table_id" { value = aws_ec2_transit_gateway_route_table.main.id }
