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
  name     = "rg-aks-services-demo"
  location = "Central India"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 2. The cluster -- deliberately the smallest thing that can host Services:
# one pool, one node, Free control-plane tier. The point of this module is
# NOT the cluster, it's what Kubernetes Service objects turn into on the
# Azure side (see manifests/ and README.md), so everything else stays bare.
resource "azurerm_kubernetes_cluster" "demo" {
  name                = "aks-svc-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = "akssvc${random_string.suffix.result}"
  sku_tier            = "Free"

  default_node_pool {
    name       = "system"
    node_count = 1
    # Standard_B2s is not on this subscription's allowlist in Central India;
    # Standard_B2s_v2 is (same finding as ../aks-minimal/).
    vm_size = "Standard_B2s_v2"

    # AKS fills these in server-side (max_surge 10%). Declared explicitly so
    # every `terraform plan` doesn't show a perpetual "remove upgrade_settings"
    # in-place change.
    upgrade_settings {
      max_surge = "10%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  # Made explicit because it is exactly what this experiment is about:
  # - load_balancer_sku = "standard": AKS provisions ONE Azure Standard Load
  #   Balancer named "kubernetes" in the node resource group at cluster
  #   creation, used for the nodes' outbound internet traffic
  #   (outbound_type = "loadBalancer").
  # - Every `type: LoadBalancer` Service then REUSES that same LB -- the
  #   cloud-controller-manager adds a new public IP + frontend IP config +
  #   rules to it rather than creating a new Load Balancer resource.
  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    load_balancer_sku   = "standard"
    outbound_type       = "loadBalancer"
  }

  node_provisioning_profile {
    mode = "Manual"
  }
}

# 3. Container registry for app images deployed onto this cluster (see
# DEPLOY_GRIDWORK.md). Basic is the cheapest tier (~US$0.17/day) and has
# everything needed here; images are built INSIDE ACR with `az acr build`,
# so no local Docker/cross-arch build is required.
resource "azurerm_container_registry" "acr" {
  name                = "akssvc${random_string.suffix.result}acr"
  resource_group_name = azurerm_resource_group.aks.name
  location            = azurerm_resource_group.aks.location
  sku                 = "Basic"
  admin_enabled       = false
}

# 4. Let the nodes pull from it. Image pulls are done by the kubelet, so the
# role goes to the KUBELET identity (the user-assigned "<cluster>-agentpool"
# identity in the MC_ group -- see AZURE_RESOURCES.md), not the cluster's own
# system-assigned identity. Same thing `az aks update --attach-acr` does,
# but kept in Terraform so it's destroyed with everything else.
resource "azurerm_role_assignment" "kubelet_acr_pull" {
  scope                            = azurerm_container_registry.acr.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.demo.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

output "resource_group_name" {
  value = azurerm_resource_group.aks.name
}

output "cluster_name" {
  value = azurerm_kubernetes_cluster.demo.name
}

output "node_resource_group" {
  description = "Where the Azure Load Balancer + public IPs created for Services actually live (MC_... group)."
  value       = azurerm_kubernetes_cluster.demo.node_resource_group
}

output "acr_name" {
  value = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}
