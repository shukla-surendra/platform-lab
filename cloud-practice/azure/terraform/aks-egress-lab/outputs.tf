output "resource_group_name" {
  value = azurerm_resource_group.aks.name
}

output "cluster_name" {
  value = azurerm_kubernetes_cluster.lab.name
}

output "node_resource_group" {
  description = "The second resource group AKS creates (MC_...): the load balancer, public IPs and VMs live here. Check it after destroy."
  value       = azurerm_kubernetes_cluster.lab.node_resource_group
}

output "get_credentials" {
  description = "Run this to point kubectl at the cluster."
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.aks.name} --name ${azurerm_kubernetes_cluster.lab.name} --overwrite-existing"
}

output "egress_public_ip_ids" {
  description = "Azure resource IDs of the public IP(s) used for OUTBOUND traffic. Resolve to an address with: az network public-ip show --ids <id> --query ipAddress -o tsv"
  value       = azurerm_kubernetes_cluster.lab.network_profile[0].load_balancer_profile[0].effective_outbound_ips
}
