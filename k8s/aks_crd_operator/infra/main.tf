terraform {
  required_providers {
    azurerm = {
      source = "hashicorp/azurerm"
    }
  }
}

provider "azurerm" {
  features {}
}

# 1. Resource Group -- kept separate from k8s/aks_setup's rg-aks-dev so this
#    lab's cluster/ACR can be torn down independently.
resource "azurerm_resource_group" "aks" {
  name     = "rg-aks-crd-lab"
  location = "Central India"
}

# 2. Vnet + subnet -- single subnet is enough for a one-node-pool dev cluster.
resource "azurerm_virtual_network" "aks" {
  name                = "vnet-aks-crd-lab"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  address_space       = ["10.10.0.0/16"]
}

resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = azurerm_resource_group.aks.name
  virtual_network_name = azurerm_virtual_network.aks.name
  address_prefixes     = ["10.10.1.0/24"]
}

# 3. AKS -- one system-pool node is enough to run the operator Pod plus a
#    couple of WebApp-managed Deployments; scale node_count up if you plan to
#    create several WebApp CRs at once.
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-crd-lab"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = "aks-crd-lab"

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
    network_plugin = "azure"
    service_cidr   = "10.11.0.0/16"
    dns_service_ip = "10.11.0.10"
  }

  identity {
    type = "SystemAssigned"
  }
}

# 4. ACR -- holds the operator's own image (controller-manager). Registry
#    names must be globally unique and alphanumeric-only, so change the
#    suffix if this one is already taken.
resource "azurerm_container_registry" "acr" {
  name                = "akscrdlabacr01"
  resource_group_name = azurerm_resource_group.aks.name
  location            = azurerm_resource_group.aks.location
  sku                 = "Basic"
}

# 5. Let AKS nodes pull the operator image from ACR without an imagePullSecret.
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "resource_group" {
  value = azurerm_resource_group.aks.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}
