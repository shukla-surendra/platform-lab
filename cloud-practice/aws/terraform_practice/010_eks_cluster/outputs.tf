output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  description = "URL of the Kubernetes API server"
  value       = aws_eks_cluster.this.endpoint
}

output "kubeconfig_command" {
  description = "Run this to add the cluster to your ~/.kube/config"
  value       = "aws eks update-kubeconfig --name ${aws_eks_cluster.this.name} --region ${var.region}"
}
