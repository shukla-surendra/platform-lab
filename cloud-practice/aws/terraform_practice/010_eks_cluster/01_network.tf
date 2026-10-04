# ---------------------------------------------------------------------------
# STEP 1: Network (VPC)
# ---------------------------------------------------------------------------
# A cluster lives inside a VPC. Control plane ENIs and worker nodes both need
# subnets, and EKS requires subnets in >= 2 AZs for control-plane availability.
#
# COST-SAVING CHOICE FOR A LAB: only PUBLIC subnets, nodes get public IPs, so
# there is NO NAT gateway (~$33/month each). In production you would put nodes
# in PRIVATE subnets behind NAT gateways. See README "Production differences".

resource "aws_vpc" "this" {
  cidr_block = var.vpc_cidr

  # Both are required so nodes can resolve the cluster's private API endpoint name
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.cluster_name}-vpc" }
}

# Internet gateway: the door between the VPC and the internet
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${var.cluster_name}-igw" }
}

# One public subnet per AZ (count loops over the AZ list)
resource "aws_subnet" "public" {
  count = length(var.azs)

  vpc_id            = aws_vpc.this.id
  availability_zone = var.azs[count.index]
  cidr_block        = var.public_subnet_cidrs[count.index]

  # Nodes launched here get a public IP, so they can pull images / reach EKS
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cluster_name}-public-${var.azs[count.index]}"

    # Tells Kubernetes' AWS load-balancer controller: "internet-facing load
    # balancers may use this subnet"
    "kubernetes.io/role/elb" = "1"

    # Marks the subnet as usable by this cluster
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}

# Route table: send all non-local traffic (0.0.0.0/0) to the internet gateway
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = { Name = "${var.cluster_name}-public-rt" }
}

# Attach the route table to each subnet
resource "aws_route_table_association" "public" {
  count = length(var.azs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
