# Deliberately minimal: one VPC, one public subnet, one Internet Gateway. No NAT Gateway
# at all — every node gets a public IP and reaches the internet directly via the IGW for
# package/image pulls. This is the #1 lever that keeps this stack cheap (a NAT Gateway
# alone runs ~$32+/month regardless of traffic — see the sibling cloud-practice/aws/
# terraform/vpc module, which defaults to including one). Fine for a lab; a real cluster
# would put nodes in a private subnet behind a NAT (or no direct internet egress at all).

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "this" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.project}-vpc" }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${var.project}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = "10.42.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = { Name = "${var.project}-public" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = { Name = "${var.project}-public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
