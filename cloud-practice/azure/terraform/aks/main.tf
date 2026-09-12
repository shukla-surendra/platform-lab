terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    random  = { source = "hashicorp/random" }
  }
}

provider "azurerm" {
  features {}
}

# 1. Resource Group
resource "azurerm_resource_group" "aks" {
  name     = "rg-aks-demo"
  location = "Central India"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. The cluster. Deliberately the cheapest real AKS cluster that still
# works: 1 node, the smallest AKS-supported VM size, Free control-plane
# tier (no financially-backed uptime SLA -- "Standard" tier adds one for
# roughly $0.10/hour and is what a real deployment would pick).
# SystemAssigned identity means Azure manages the cluster's own service
# principal for you -- no separate app registration/secret to create
# and rotate.
resource "azurerm_kubernetes_cluster" "demo" {
  name                = "aks-demo-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = "aksdemo${random_string.suffix.result}"
  sku_tier            = "Free"

  default_node_pool {
    name       = "system"
    node_count = 1
    vm_size    = "Standard_B2s_v2"
  }

  identity {
    type = "SystemAssigned"
  }

  # Required by this provider version even when unused -- "Manual" means
  # node pools are exactly what's declared below (this demo's
  # default_node_pool), not AKS's newer Karpenter-based auto-provisioning
  # mode ("Auto").
  node_provisioning_profile {
    mode = "Manual"
  }
}

output "resource_group_name" {
  value = azurerm_resource_group.aks.name
}

output "cluster_name" {
  value = azurerm_kubernetes_cluster.demo.name
}

# The AKS control plane itself lives in a Microsoft-managed subscription,
# not this resource group -- but the *node pool's* actual VMs, disks, NICs,
# load balancers, etc. land in a second, auto-created resource group
# ("MC_<rg>_<cluster>_<region>"). This output is that group's name --
# worth knowing it exists so `az group list` post-apply isn't a surprise.
output "node_resource_group" {
  value = azurerm_kubernetes_cluster.demo.node_resource_group
}

output "kube_config" {
  value     = azurerm_kubernetes_cluster.demo.kube_config_raw
  sensitive = true
}
