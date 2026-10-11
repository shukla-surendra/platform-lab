terraform {
required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "cluster_name" {
  description = "The name of the EKS cluster"
  type        = string
  default     = "my-eks-cluster"
}

# A "data" block READS or BUILDS something, it creates nothing in AWS. This one builds a JSON policy document in memory
# (read it as `data.aws_iam_policy_document.eks_assume.json`, which is what the IAM role below uses).
# This particular policy is a TRUST policy: it says WHO is allowed to use the role (not what the role can do).
data "aws_iam_policy_document" "eks_assume" {
  statement {
    # The permission being granted: "assume this role", i.e. get temporary credentials for it.
    actions = ["sts:AssumeRole"]

    # WHO may do that.
    principals {
      type        = "Service"                  # an AWS service, not a user or another account
      identifiers = ["eks.amazonaws.com"]      # the EKS service: so the EKS control plane can act as this role
    }
    # (effect defaults to "Allow")
  }
}
# Result, in plain words: "the EKS service is allowed to assume this role".
# The role's PERMISSIONS come separately: aws_iam_role_policy_attachment attaches AmazonEKSClusterPolicy to it.
# Without this trust policy, EKS could not use the role and cluster creation would fail.

resource "aws_iam_role" "cluster" {
  name               = "${var.cluster_name}-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.eks_assume.json
}
resource "aws_iam_role_policy_attachment" "cluster_policy" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_eks_cluster" "my_eks_cluster" {
  name = var.cluster_name
  version  = "1.35"
  role_arn = aws_iam_role.cluster.arn
  vpc_config {
    subnet_ids = ["subnet-00117487146742c23", "subnet-0ddd28a9cc6a2f624"] # Replace with your actual subnet IDs
  }

  # Lets you grant console/kubectl access with access entries (below). CONFIG_MAP -> API_AND_CONFIG_MAP is one-way.
  access_config {
    authentication_mode = "API_AND_CONFIG_MAP"
  }
}

# The IAM user/role you are signed in with in the AWS console. Find it: console top-right menu, or `aws sts get-caller-identity`.
variable "console_principal_arn" {
  description = "ARN of the IAM user/role used in the console. Null = no extra access entry."
  type        = string
  default     = null
}

resource "aws_eks_access_entry" "console" {
  count         = var.console_principal_arn == null ? 0 : 1
  cluster_name  = aws_eks_cluster.my_eks_cluster.name
  principal_arn = var.console_principal_arn
}

resource "aws_eks_access_policy_association" "console_admin" {
  count         = var.console_principal_arn == null ? 0 : 1
  cluster_name  = aws_eks_cluster.my_eks_cluster.name
  principal_arn = var.console_principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  access_scope {
    type = "cluster"
  }
  depends_on = [aws_eks_access_entry.console]
}

# ---- Node group: the cluster above has no worker nodes until this exists ----
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

resource "aws_iam_role_policy_attachment" "node_worker" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "node_cni" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "node_ecr" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_eks_node_group" "primary" {
  cluster_name    = aws_eks_cluster.my_eks_cluster.name
  node_group_name = "primary"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = ["subnet-00117487146742c23", "subnet-0ddd28a9cc6a2f624"] # same subnets as the cluster
  capacity_type   = "SPOT"
  instance_types  = ["t3.medium"]

  scaling_config {
    desired_size = 1
    min_size     = 1
    max_size     = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_worker,
    aws_iam_role_policy_attachment.node_cni,
    aws_iam_role_policy_attachment.node_ecr,
  ]
}

resource "aws_eks_node_group" "secondary" {
  cluster_name    = aws_eks_cluster.my_eks_cluster.name
  node_group_name = "secondary"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = ["subnet-00117487146742c23", "subnet-0ddd28a9cc6a2f624"] # same subnets as the cluster
  capacity_type   = "SPOT"
  instance_types  = ["t3.medium"]

  scaling_config {
    desired_size = 1
    min_size     = 1
    max_size     = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_worker,
    aws_iam_role_policy_attachment.node_cni,
    aws_iam_role_policy_attachment.node_ecr,
  ]
}