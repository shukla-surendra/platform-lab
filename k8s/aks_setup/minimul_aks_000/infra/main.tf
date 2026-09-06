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
    vm_size        = "Standard_D4s_v5"
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