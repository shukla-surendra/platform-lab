# ---------------------------------------------------------------------------
# STEP 3: The EKS cluster (the control plane)
# ---------------------------------------------------------------------------
# This creates ONLY the control plane: API server, etcd, scheduler, controller
# manager. AWS runs these in its own account across multiple AZs. You pay about
# $0.10/hour (~$73/month) for it whether or not you have any nodes.
# There is nowhere to run pods yet: that is STEP 4.

resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  version  = var.kubernetes_version
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids = aws_subnet.public[*].id

    # API endpoint access:
    #   public  = reachable from the internet (restricted by public_access_cidrs)
    #   private = reachable from inside the VPC
    endpoint_public_access  = true
    endpoint_private_access = true

    # LAB ONLY: open to everyone (still needs valid AWS credentials to use).
    # Better: restrict to your IP, e.g. ["203.0.113.5/32"].
    public_access_cidrs = ["0.0.0.0/0"]
  }

  # How people/roles are granted access to the cluster:
  #   API                = EKS "access entries" (modern, managed via AWS API)
  #   CONFIG_MAP         = old aws-auth ConfigMap
  #   API_AND_CONFIG_MAP = both
  access_config {
    authentication_mode = "API"

    # Whoever runs `terraform apply` automatically becomes cluster admin.
    # Without this you could create a cluster you cannot log into.
    bootstrap_cluster_creator_admin_permissions = true
  }

  # Wait for the policy attachment first, otherwise the control plane cannot
  # use its role yet and creation can fail / delete can hang.
  depends_on = [aws_iam_role_policy_attachment.cluster_policy]
}
