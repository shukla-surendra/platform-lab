# ===========================================================================
# 016 – VPC endpoints demo: a PRIVATE instance with no internet at all
# ===========================================================================
#   VPC 10.50.0.0/16
#   └─ private subnet (NO internet gateway, NO NAT gateway, instance has NO public IP)
#        instance ── Gateway endpoint ──▶ S3                 (free)
#                └─── Interface endpoints ──▶ SSM (3 of them)  (so you can still manage it)
#
# Learning goals:
#   1. INTERFACE endpoint = private ENIs + private DNS name for an AWS service (billed).
#   2. GATEWAY endpoint (S3, DynamoDB only) = a route-table entry to a prefix list (free).
#   3. Endpoint POLICY = a resource policy on the endpoint itself (limits what can be done through it).
#   4. Private DNS: the normal service hostname now resolves to a PRIVATE IP.
#
# Experiment: create_interface_endpoints=false -> the instance can no longer be
# reached through SSM (no route to AWS APIs), but S3 through the gateway endpoint still works.

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
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

variable "create_interface_endpoints" {
  description = "false = no SSM endpoints (instance becomes unreachable via SSM)"
  type        = bool
  default     = true
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = "endpoints-lab"
      Managed = "terraform"
    }
  }
}

locals {
  cidr = "10.50.0.0/16"
}

# ---------------------------------------------------------------------------
# Network: private only. No IGW, no NAT, no 0.0.0.0/0 route.
# ---------------------------------------------------------------------------
resource "aws_vpc" "this" {
  cidr_block = local.cidr

  # REQUIRED for interface endpoints' private DNS to work
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "endpoints-lab" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(local.cidr, 8, 0)
  availability_zone = var.az
  tags              = { Name = "endpoints-lab-private" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "endpoints-lab-private" }
  # deliberately empty: only the implicit local route (and the S3 endpoint route added below)
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

# ---------------------------------------------------------------------------
# S3 buckets: one the endpoint policy ALLOWS, one it DENIES (to prove the policy)
# ---------------------------------------------------------------------------
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "allowed" {
  bucket        = "endpoints-lab-allowed-${random_id.suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket" "denied" {
  bucket        = "endpoints-lab-denied-${random_id.suffix.hex}"
  force_destroy = true
}

resource "aws_s3_object" "allowed" {
  bucket  = aws_s3_bucket.allowed.id
  key     = "test.txt"
  content = "reachable through the gateway endpoint\n"
}

resource "aws_s3_object" "denied" {
  bucket  = aws_s3_bucket.denied.id
  key     = "test.txt"
  content = "the instance role may read this, the endpoint policy does not\n"
}

# ---------------------------------------------------------------------------
# GATEWAY endpoint for S3 (free). Adds a route in the route table:
#   destination = S3 prefix list (pl-xxxx), target = vpce-xxxx
# S3's hostname still resolves to PUBLIC IPs; the route is what keeps the traffic
# on the AWS network.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "s3_endpoint_policy" {
  statement {
    sid     = "OnlyTheAllowedBucket"
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      aws_s3_bucket.allowed.arn,
      "${aws_s3_bucket.allowed.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
  policy            = data.aws_iam_policy_document.s3_endpoint_policy.json
  tags              = { Name = "endpoints-lab-s3" }
}

# ---------------------------------------------------------------------------
# INTERFACE endpoints for SSM (billed per hour per AZ + per GB).
# SSM needs all three to work: ssm, ssmmessages, ec2messages.
# Each creates an ENI with a private IP in our subnet; "private DNS" makes the
# normal hostname (ssm.us-east-1.amazonaws.com) resolve to that private IP.
# ---------------------------------------------------------------------------
resource "aws_security_group" "endpoints" {
  name        = "endpoints-lab-vpce-sg"
  description = "HTTPS from inside the VPC to the interface endpoints"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [local.cidr]
  }
}

resource "aws_vpc_endpoint" "ssm" {
  for_each = var.create_interface_endpoints ? toset(["ssm", "ssmmessages", "ec2messages"]) : toset([])

  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private.id]
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true
  tags                = { Name = "endpoints-lab-${each.key}" }
}

# ---------------------------------------------------------------------------
# The private instance
# ---------------------------------------------------------------------------
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "instance" {
  name               = "endpoints-lab-instance-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# The ROLE may read BOTH buckets. So when the denied one fails, the cause is
# the ENDPOINT policy, not IAM: two independent layers of control.
data "aws_iam_policy_document" "s3_read" {
  statement {
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      aws_s3_bucket.allowed.arn, "${aws_s3_bucket.allowed.arn}/*",
      aws_s3_bucket.denied.arn, "${aws_s3_bucket.denied.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "s3_read" {
  name   = "read-both-lab-buckets"
  role   = aws_iam_role.instance.id
  policy = data.aws_iam_policy_document.s3_read.json
}

resource "aws_iam_instance_profile" "instance" {
  name = "endpoints-lab-instance-profile"
  role = aws_iam_role.instance.name
}

resource "aws_security_group" "instance" {
  name        = "endpoints-lab-instance-sg"
  description = "No inbound; outbound only"
  vpc_id      = aws_vpc.this.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "private" {
  ami                         = data.aws_ssm_parameter.al2023.value
  instance_type               = "t4g.nano"
  subnet_id                   = aws_subnet.private.id
  vpc_security_group_ids      = [aws_security_group.instance.id]
  iam_instance_profile        = aws_iam_instance_profile.instance.name
  associate_public_ip_address = false

  metadata_options {
    http_tokens = "required"
  }

  tags = { Name = "endpoints-lab-private-instance" }

  # SSM must be reachable (endpoints) before the agent starts registering
  depends_on = [aws_vpc_endpoint.ssm]
}

# ---------------------------------------------------------------------------
# Outputs used by scripts/test_endpoints.sh
# ---------------------------------------------------------------------------
output "instance_id" { value = aws_instance.private.id }
output "allowed_bucket" { value = aws_s3_bucket.allowed.id }
output "denied_bucket" { value = aws_s3_bucket.denied.id }
output "route_table_id" { value = aws_route_table.private.id }
output "s3_endpoint_id" { value = aws_vpc_endpoint.s3.id }
output "interface_endpoints" { value = var.create_interface_endpoints }
