terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
    }
  }
}

provider "azurerm" {
  features {}
}


# 1. Resource Group
resource "azurerm_resource_group" "aks" {
  name     = "rg-aks-dev"
  location = "Central India"
}

# 2. Vnet virtual Network
resource "azurerm_virtual_network" "aks" {
  name                = "vnet-aks-dev"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  address_space       = ["10.0.0.0/16"]
}

# 3. Subnet
resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = azurerm_resource_group.aks.name
  virtual_network_name = azurerm_virtual_network.aks.name
  address_prefixes     = ["10.0.1.0/24"]
}
# 4. AKS
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-dev"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = "aks-dev"

  default_node_pool {
    name           = "system"
    vm_size        = "Standard_D2s_v5"
    node_count     = 1
    vnet_subnet_id = azurerm_subnet.aks.id
  }

  node_provisioning_profile {
    mode = "Auto"
  }

  network_profile {
    network_plugin    = "azure"
    service_cidr   = "10.1.0.0/16"
    dns_service_ip = "10.1.0.10"
  }

  identity {
    type = "SystemAssigned"
  }
}

# 5. ACR
resource "azurerm_container_registry" "acr" {
  name                = "aksdevacr123"
  resource_group_name = azurerm_resource_group.aks.name
  location            = azurerm_resource_group.aks.location
  sku                 = "Basic"
}

# 6.  A separate User Node Pool
resource "azurerm_kubernetes_cluster_node_pool" "user" {

  name = "userpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size    = "Standard_D2s_v5"
  node_count = 1
  vnet_subnet_id = azurerm_subnet.aks.id

}

# 7. Allow AKS nodes to pull images from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}

# 8. Static Public IP for the future ingress/LoadBalancer Service
#    (see helm/gridwork/PUBLIC_EXPOSURE_PLAN.md). Created directly in AKS's
#    own auto-managed node resource group (MC_rg-aks-dev_aks-dev_...) since
#    that's where Kubernetes' cloud-controller-manager creates LoadBalancer
#    IPs by default -- matching that means the Kubernetes Service only needs
#    a `loadBalancerIP` annotation, not also the
#    "azure-load-balancer-resource-group" one to point it elsewhere.
#    Reserving it here means it survives a helm uninstall/reinstall of
#    whatever Service ends up requesting it, instead of getting handed a new
#    IP each time.
data "azurerm_resource_group" "aks_node_rg" {
  name = azurerm_kubernetes_cluster.aks.node_resource_group
}

resource "azurerm_public_ip" "ingress" {
  name                = "pip-aks-dev-ingress"
  resource_group_name = data.azurerm_resource_group.aks_node_rg.name
  location            = data.azurerm_resource_group.aks_node_rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
}

output "ingress_public_ip" {
  value = azurerm_public_ip.ingress.ip_address
}
