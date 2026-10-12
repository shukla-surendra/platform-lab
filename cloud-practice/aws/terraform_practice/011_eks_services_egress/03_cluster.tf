# The EKS control plane (managed by AWS). It is billed per hour while it exists.
resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  version  = var.kubernetes_version
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = aws_subnet.public[*].id
    endpoint_public_access  = true # so kubectl works from your laptop
    endpoint_private_access = true
    public_access_cidrs     = ["0.0.0.0/0"] # tighten to your IP for anything beyond a short lab
  }

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true # you (the creator) become cluster admin
  }

  depends_on = [aws_iam_role_policy_attachment.cluster_policy]
}
