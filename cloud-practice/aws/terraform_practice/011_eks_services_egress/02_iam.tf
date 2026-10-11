# ---------------------------------------------------------------------------
# STEP 2: IAM roles (two of them, for two different actors)
# ---------------------------------------------------------------------------
# An IAM role has two parts:
#   - TRUST policy:       WHO may assume the role (here: an AWS service)
#   - PERMISSION policies: WHAT the role may do once assumed

# ---------- 2a. Cluster role: used by the EKS control plane ----------
# The control plane (managed by AWS) must call the EC2/ELB APIs in YOUR account
# (create ENIs, security group rules, load balancers...). It does that by
# assuming this role.

data "aws_iam_policy_document" "eks_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster" {
  name               = "${var.cluster_name}-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.eks_assume.json
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# ---------- 2b. Node role: used by the worker EC2 instances ----------
# Each worker node (EC2) runs the kubelet, which must register the node with
# the cluster, pull images from ECR, and the VPC CNI plugin must manage pod IPs.

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = "${var.cluster_name}-node-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

# Lets the kubelet join the cluster and describe EC2 info
resource "aws_iam_role_policy_attachment" "node_worker" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

# Lets the VPC CNI plugin attach IPs/ENIs for pods
resource "aws_iam_role_policy_attachment" "node_cni" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

# Lets nodes pull container images from ECR
resource "aws_iam_role_policy_attachment" "node_ecr" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}
