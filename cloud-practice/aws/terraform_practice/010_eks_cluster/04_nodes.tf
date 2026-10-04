# ---------------------------------------------------------------------------
# STEP 4: Worker nodes (managed node group)
# ---------------------------------------------------------------------------
# A managed node group is an Auto Scaling Group of EC2 instances that AWS
# creates, joins to the cluster, patches and replaces for you.
# Pods (your containers) run on these nodes. You pay for the EC2 instances.

resource "aws_eks_node_group" "default" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "default"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = aws_subnet.public[*].id

  instance_types = var.node_instance_types
  ami_type       = "AL2023_x86_64_STANDARD" # Amazon Linux 2023, EKS-optimized
  capacity_type  = "ON_DEMAND"              # "SPOT" is cheaper but can be reclaimed

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  # During node upgrades, replace at most 1 node at a time
  update_config {
    max_unavailable = 1
  }

  # The node role needs ALL three policies before nodes boot, or they fail to join.
  depends_on = [
    aws_iam_role_policy_attachment.node_worker,
    aws_iam_role_policy_attachment.node_cni,
    aws_iam_role_policy_attachment.node_ecr,
  ]
}

# ---------------------------------------------------------------------------
# STEP 5: Core add-ons
# ---------------------------------------------------------------------------
# Add-ons are the system components every cluster needs:
#   vpc-cni    : gives each pod a real VPC IP address
#   kube-proxy : implements Services (virtual IPs) on each node
#   coredns    : in-cluster DNS (my-service.my-namespace.svc.cluster.local)
# EKS installs defaults automatically; declaring them here lets Terraform
# manage versions. OVERWRITE adopts the ones EKS already created.

resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "vpc-cni"
  resolve_conflicts_on_create = "OVERWRITE"
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "kube-proxy"
  resolve_conflicts_on_create = "OVERWRITE"
}

# CoreDNS is itself a pod, so it needs nodes to run on: create it after the node group
resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = "coredns"
  resolve_conflicts_on_create = "OVERWRITE"

  depends_on = [aws_eks_node_group.default]
}
