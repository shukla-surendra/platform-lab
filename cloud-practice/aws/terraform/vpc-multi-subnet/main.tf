##############################################################################
# Locals — naming, tagging, and computed subnet CIDRs.
##############################################################################
locals {
  name = "${var.project}-${var.environment}"

  tags = merge(
    {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
      Module      = "aws/terraform/vpc-multi-subnet"
    },
    var.extra_tags,
  )

  # One public + one private /24 (by default) per AZ, carved from the VPC CIDR.
  # Public subnets occupy the low block (.0, .1, ...), private the next block
  # offset by length(azs) so the ranges never overlap.
  public_subnet_cidrs  = [for i, az in var.azs : cidrsubnet(var.vpc_cidr, var.public_subnet_newbits, i)]
  private_subnet_cidrs = [for i, az in var.azs : cidrsubnet(var.vpc_cidr, var.private_subnet_newbits, i + length(var.azs))]

  nat_count = var.single_nat_gateway ? 1 : length(var.azs)
}

##############################################################################
# VPC + Internet Gateway
##############################################################################
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = var.enable_dns_hostnames

  tags = { Name = local.name }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${local.name}-igw" }
}

##############################################################################
# Subnets — one public + one private per AZ
##############################################################################
resource "aws_subnet" "public" {
  count                   = length(var.azs)
  vpc_id                  = aws_vpc.this.id
  availability_zone       = var.azs[count.index]
  cidr_block              = local.public_subnet_cidrs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name}-public-${var.azs[count.index]}"
    Tier = "public"
  }
}

resource "aws_subnet" "private" {
  count             = length(var.azs)
  vpc_id            = aws_vpc.this.id
  availability_zone = var.azs[count.index]
  cidr_block        = local.private_subnet_cidrs[count.index]

  tags = {
    Name = "${local.name}-private-${var.azs[count.index]}"
    Tier = "private"
  }
}

##############################################################################
# NAT Gateways (+ Elastic IPs) — live in the public subnets, give private
# subnets outbound-only internet access.
##############################################################################
resource "aws_eip" "nat" {
  count  = local.nat_count
  domain = "vpc"
  tags   = { Name = "${local.name}-nat-eip-${count.index}" }
}

resource "aws_nat_gateway" "this" {
  count         = local.nat_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  depends_on    = [aws_internet_gateway.this]

  tags = { Name = "${local.name}-nat-${count.index}" }
}

##############################################################################
# Route tables
#   public  : shared, default route -> IGW
#   private : one per AZ, default route -> that AZ's NAT GW (or the single one)
##############################################################################

# --- Public ---
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${local.name}-public-rt" }
}

resource "aws_route" "public_default" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# --- Private ---
resource "aws_route_table" "private" {
  count  = length(var.azs)
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${local.name}-private-rt-${var.azs[count.index]}" }
}

resource "aws_route" "private_default" {
  count                  = length(var.azs)
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[var.single_nat_gateway ? 0 : count.index].id
}

resource "aws_route_table_association" "private" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
