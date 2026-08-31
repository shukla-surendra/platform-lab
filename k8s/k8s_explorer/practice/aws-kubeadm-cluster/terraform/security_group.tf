# One security group, shared by every node. Intentionally permissive between cluster
# members (a self-referencing "allow all" rule) rather than enumerating every port
# Kubernetes actually needs — this is a lab-scope tradeoff, made explicit rather than
# accidental. A production cluster would instead open exactly:
#   6443/tcp        kube-apiserver
#   2379-2380/tcp   etcd client/peer (control-plane only)
#   10250/tcp       kubelet API
#   10251/tcp       kube-scheduler
#   10259/tcp       kube-controller-manager
#   30000-32767/tcp NodePort service range
#   8472/udp        Flannel VXLAN overlay (or your CNI's equivalent)
# See docs/CONCEPTS.md for what each of these actually does.

resource "aws_security_group" "cluster" {
  name        = "${var.project}-cluster"
  description = "kubeadm POC — SSH from one IP, everything open between cluster nodes"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${var.project}-cluster-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.cluster.id
  description       = "SSH, from your IP only"
  cidr_ipv4         = var.allowed_ssh_cidr
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
}

resource "aws_vpc_security_group_ingress_rule" "intra_cluster" {
  security_group_id            = aws_security_group.cluster.id
  description                  = "All traffic between cluster nodes (API server, etcd, kubelet, CNI overlay — see file header)"
  referenced_security_group_id = aws_security_group.cluster.id
  ip_protocol                  = "-1"
}

resource "aws_vpc_security_group_ingress_rule" "nodeport_from_you" {
  security_group_id = aws_security_group.cluster.id
  description       = "NodePort range, from your IP only — lets README.md's smoke test curl a worker's public IP directly"
  cidr_ipv4         = var.allowed_ssh_cidr
  ip_protocol       = "tcp"
  from_port         = 30000
  to_port           = 32767
}

resource "aws_vpc_security_group_egress_rule" "all_outbound" {
  security_group_id = aws_security_group.cluster.id
  description       = "Unrestricted egress — needed to reach apt/container registries with no NAT Gateway in the path"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
