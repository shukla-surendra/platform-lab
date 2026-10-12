# Worker nodes: a managed node group on SPOT capacity.
# - The node group is an Auto Scaling group. If AWS reclaims a Spot node, the group launches a replacement by itself
#   (EKS uses EC2 Capacity Rebalancing for Spot managed node groups). No Karpenter or termination handler needed.
# - It only works while Spot capacity exists, so several similar instance types are listed.
resource "aws_eks_node_group" "default" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "default"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = aws_subnet.public[*].id

  instance_types = var.node_instance_types
  ami_type       = "AL2023_x86_64_STANDARD"
  capacity_type  = var.capacity_type
  disk_size      = var.node_disk_size_gb

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_worker,
    aws_iam_role_policy_attachment.node_cni,
    aws_iam_role_policy_attachment.node_ecr,
  ]
}

# ---------------------------------------------------------------------------
# Core add-ons
# ---------------------------------------------------------------------------
# vpc-cni: gives each Pod a real VPC IP. enableNetworkPolicy turns on its built-in NetworkPolicy enforcement, which is
#          what makes the egress NetworkPolicy exercises work (setting name checked against the add-on's own schema:
#          aws eks describe-addon-configuration --addon-name vpc-cni ...).
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "vpc-cni"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  configuration_values = jsonencode({
    enableNetworkPolicy = "true" # a string-typed boolean in the schema
  })
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "kube-proxy"
  resolve_conflicts_on_create = "OVERWRITE"
}

# CoreDNS runs as Pods, so it needs nodes first
resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "coredns"
  resolve_conflicts_on_create = "OVERWRITE"

  depends_on = [aws_eks_node_group.default]
}
