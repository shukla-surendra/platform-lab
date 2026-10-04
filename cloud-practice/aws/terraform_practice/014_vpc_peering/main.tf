# ===========================================================================
# 014 – VPC peering demo: A <-> B <-> C   (A and C are NOT peered with each other)
# ===========================================================================
#   VPC A 10.10.0.0/16  <== peering ==>  VPC B 10.20.0.0/16  <== peering ==>  VPC C 10.30.0.0/16
#
# Learning goals:
#   1. A peering connection alone does nothing: you also need ROUTES on both sides
#      (and security groups that allow the traffic).
#   2. Peering is NOT transitive: A can reach B, B can reach C, A still cannot reach C.
#
# Experiments via variables (see README):
#   enable_routes=false          -> peering exists, no routes -> everything blocked
#   try_transitive_route=true    -> add A->C / C->A routes via B anyway -> still blocked

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

variable "enable_routes" {
  description = "Add the routes that make the peerings usable. false = peering with no routes."
  type        = bool
  default     = true
}

variable "try_transitive_route" {
  description = "Also add A<->C routes via B to prove that peering is not transitive"
  type        = bool
  default     = false
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = "peering-lab"
      Managed = "terraform"
    }
  }
}

locals {
  cidr_a = "10.10.0.0/16"
  cidr_b = "10.20.0.0/16"
  cidr_c = "10.30.0.0/16"

  # security groups allow any lab VPC; the lesson is routing, not SGs
  lab_supernet = "10.0.0.0/8"
}

module "vpc_a" {
  source                = "../net_modules/test_vpc"
  name                  = "peer-a"
  cidr                  = local.cidr_a
  az                    = var.az
  allowed_ingress_cidrs = [local.lab_supernet]
}

module "vpc_b" {
  source                = "../net_modules/test_vpc"
  name                  = "peer-b"
  cidr                  = local.cidr_b
  az                    = var.az
  allowed_ingress_cidrs = [local.lab_supernet]
}

module "vpc_c" {
  source                = "../net_modules/test_vpc"
  name                  = "peer-c"
  cidr                  = local.cidr_c
  az                    = var.az
  allowed_ingress_cidrs = [local.lab_supernet]
}

# ---------------------------------------------------------------------------
# Peering connections (same account + same region, so auto_accept works)
# ---------------------------------------------------------------------------
# Requester = vpc_id, accepter = peer_vpc_id. In one account/region Terraform can
# accept it for you. Cross-account/region needs a separate accepter resource.
resource "aws_vpc_peering_connection" "a_b" {
  vpc_id      = module.vpc_a.vpc_id
  peer_vpc_id = module.vpc_b.vpc_id
  auto_accept = true
  tags        = { Name = "peer-a-b" }
}

resource "aws_vpc_peering_connection" "b_c" {
  vpc_id      = module.vpc_b.vpc_id
  peer_vpc_id = module.vpc_c.vpc_id
  auto_accept = true
  tags        = { Name = "peer-b-c" }
}

# ---------------------------------------------------------------------------
# Routes: "to reach that VPC's CIDR, send traffic through the peering connection"
# Needed in BOTH directions (each VPC must know the way back).
# ---------------------------------------------------------------------------
resource "aws_route" "a_to_b" {
  count                     = var.enable_routes ? 1 : 0
  route_table_id            = module.vpc_a.route_table_id
  destination_cidr_block    = local.cidr_b
  vpc_peering_connection_id = aws_vpc_peering_connection.a_b.id
}

resource "aws_route" "b_to_a" {
  count                     = var.enable_routes ? 1 : 0
  route_table_id            = module.vpc_b.route_table_id
  destination_cidr_block    = local.cidr_a
  vpc_peering_connection_id = aws_vpc_peering_connection.a_b.id
}

resource "aws_route" "b_to_c" {
  count                     = var.enable_routes ? 1 : 0
  route_table_id            = module.vpc_b.route_table_id
  destination_cidr_block    = local.cidr_c
  vpc_peering_connection_id = aws_vpc_peering_connection.b_c.id
}

resource "aws_route" "c_to_b" {
  count                     = var.enable_routes ? 1 : 0
  route_table_id            = module.vpc_c.route_table_id
  destination_cidr_block    = local.cidr_b
  vpc_peering_connection_id = aws_vpc_peering_connection.b_c.id
}

# ---------------------------------------------------------------------------
# Transitive experiment: A->C goes to peering a_b, C->A goes to peering b_c.
# The packet arrives at B and is DROPPED: a peering only carries traffic whose
# source or destination is one of its two VPCs; B never forwards between peerings.
# ---------------------------------------------------------------------------
resource "aws_route" "a_to_c_via_b" {
  count                     = var.try_transitive_route ? 1 : 0
  route_table_id            = module.vpc_a.route_table_id
  destination_cidr_block    = local.cidr_c
  vpc_peering_connection_id = aws_vpc_peering_connection.a_b.id
}

resource "aws_route" "c_to_a_via_b" {
  count                     = var.try_transitive_route ? 1 : 0
  route_table_id            = module.vpc_c.route_table_id
  destination_cidr_block    = local.cidr_a
  vpc_peering_connection_id = aws_vpc_peering_connection.b_c.id
}

# ---------------------------------------------------------------------------
# Outputs used by scripts/test_peering.sh
# ---------------------------------------------------------------------------
output "a_instance_id" { value = module.vpc_a.instance_id }
output "b_instance_id" { value = module.vpc_b.instance_id }
output "c_instance_id" { value = module.vpc_c.instance_id }
output "a_ip" { value = module.vpc_a.private_ip }
output "b_ip" { value = module.vpc_b.private_ip }
output "c_ip" { value = module.vpc_c.private_ip }
output "routes_enabled" { value = var.enable_routes }
