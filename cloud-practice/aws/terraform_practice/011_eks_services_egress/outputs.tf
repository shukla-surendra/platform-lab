output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "kubeconfig_command" {
  description = "Run this to add the cluster to your ~/.kube/config"
  value       = "aws eks update-kubeconfig --name ${aws_eks_cluster.this.name} --region ${var.region}"
}

output "region" {
  description = "Pass this to every aws command when checking the lab (your CLI default may differ)."
  value       = var.region
}

output "verify_clean_commands" {
  description = "Run these AFTER terraform destroy. Every one should return nothing."
  value = join("\n", [
    "aws eks list-clusters --region ${var.region}",
    "aws elb describe-load-balancers --region ${var.region} --query 'LoadBalancerDescriptions[].LoadBalancerName'",
    "aws elbv2 describe-load-balancers --region ${var.region} --query 'LoadBalancers[].LoadBalancerName'",
    "aws ec2 describe-instances --region ${var.region} --filters Name=instance-state-name,Values=running,pending --query 'Reservations[].Instances[].InstanceId'",
    "aws ec2 describe-addresses --region ${var.region} --query 'Addresses[].PublicIp'",
    "aws ec2 describe-vpcs --region ${var.region} --filters Name=tag:Project,Values=eks-egress-lab --query 'Vpcs[].VpcId'",
  ])
}
