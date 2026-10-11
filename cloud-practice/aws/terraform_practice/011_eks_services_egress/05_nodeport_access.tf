# OPTIONAL, OFF BY DEFAULT. For the NodePort exercise only.
# Nodes are on public IPs, but their security group does not accept the NodePort range (30000-32767) from the internet.
# Setting var.allow_nodeport_from_cidr to YOUR address opens that range for you alone, so you can reach
# http://<node-public-ip>:30080 from your laptop. Remove it afterwards (set it back to null and apply, or just destroy).
#
# This uses the cluster's PRIMARY security group, which managed node groups use by default. Check that it is the one
# on your nodes:  aws ec2 describe-instances --region us-east-1 --filters Name=tag:eks:cluster-name,Values=eks-egress-lab \
#                   --query "Reservations[].Instances[].SecurityGroups[].GroupId"
resource "aws_vpc_security_group_ingress_rule" "nodeport_from_me" {
  count = var.allow_nodeport_from_cidr == null ? 0 : 1

  security_group_id = aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
  description       = "NodePort range, lab only, from one address"
  ip_protocol       = "tcp"
  from_port         = 30000
  to_port           = 32767
  cidr_ipv4         = var.allow_nodeport_from_cidr
}
