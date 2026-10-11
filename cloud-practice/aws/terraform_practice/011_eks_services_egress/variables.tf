variable "region" {
  description = "AWS region. Your AWS CLI default may be a different region: always pass --region when checking this lab."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Cluster name (also used to name and tag related resources). Different from the 010 project's 'eks-lab' so the two never collide."
  type        = string
  default     = "eks-egress-lab"
}

variable "kubernetes_version" {
  description = <<-EOT
    Kubernetes version. 1.36 was the EKS default and in STANDARD support when this was written
    (checked with: aws eks describe-cluster-versions --region us-east-1). Versions in EXTENDED support cost much more per cluster-hour.
  EOT
  type        = string
  default     = "1.36"
}

variable "vpc_cidr" {
  type    = string
  default = "10.30.0.0/16"
}

variable "azs" {
  description = "Two Availability Zones (EKS needs subnets in at least 2)."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "One CIDR per AZ, same order as var.azs"
  type        = list(string)
  default     = ["10.30.1.0/24", "10.30.2.0/24"]
}

variable "node_instance_types" {
  description = <<-EOT
    Several SIMILAR sizes (2 vCPU / 4 GiB). For Spot this matters: if one type has no Spot capacity, the node group can use another.
    A single type is the weak point of a Spot plan.
  EOT
  type        = list(string)
  default     = ["t3.medium", "t3a.medium", "t2.medium"]
}

variable "capacity_type" {
  description = "SPOT (cheap, can be reclaimed by AWS) or ON_DEMAND (steady). The node group replaces reclaimed Spot nodes itself; no Karpenter needed."
  type        = string
  default     = "SPOT"

  validation {
    condition     = contains(["SPOT", "ON_DEMAND"], var.capacity_type)
    error_message = "capacity_type must be SPOT or ON_DEMAND."
  }
}

variable "node_desired_size" {
  description = "2 nodes lets you see per-node egress IPs and NodePort on each node. Use 1 to save a little more."
  type        = number
  default     = 2
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 2
}

variable "node_disk_size_gb" {
  description = "Root disk per node. Small is enough here."
  type        = number
  default     = 20
}

variable "allow_nodeport_from_cidr" {
  description = <<-EOT
    OFF by default (null): the nodes' security group does not accept NodePort traffic from the internet.
    For the NodePort exercise, set it to YOUR address only, e.g.  -var 'allow_nodeport_from_cidr=203.0.113.7/32'
    (find it with: curl -s https://checkip.amazonaws.com). Never use 0.0.0.0/0.
  EOT
  type        = string
  default     = null
}
