variable "location" {
  description = "Azure region. Central India is where the earlier AKS labs ran; Standard_B2s_v2 is available there."
  type        = string
  default     = "Central India"
}

variable "name_prefix" {
  description = "Prefix for resource names. A random suffix is added so re-creating the lab never collides."
  type        = string
  default     = "aks-egress"
}

variable "vm_size" {
  description = "Node VM size. B2s_v2 = 2 vCPU / 8 GiB burstable, the cheap size the earlier labs used."
  type        = string
  default     = "Standard_B2s_v2"
}

variable "node_count" {
  description = "Number of nodes. 1 is enough for every exercise in README.md; 2 only if you want to see Pods spread across nodes."
  type        = number
  default     = 1
}

variable "enable_network_policy" {
  description = "Use Azure CNI powered by Cilium so NetworkPolicy (including EGRESS rules) is enforced. Set false to fall back to a plain overlay with no policy engine."
  type        = bool
  default     = true
}

variable "outbound_ip_count" {
  description = "How many public IPs the cluster's load balancer uses for OUTBOUND (egress) traffic. 1 = one stable egress IP."
  type        = number
  default     = 1
}
