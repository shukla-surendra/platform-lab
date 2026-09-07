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
resource "azurerm_resource_group" "aci" {
  name     = "rg-aci-demo"
  location = "Central India"
}

# 2. The DNS label (aci-demo-xxxxxx.centralindia.azurecontainer.io) must be
# globally unique across all of Azure Container Instances, not just your
# subscription -- hence the random suffix.
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# 3. Container Group -- the single deployable unit in ACI (one or more
# containers that share a network namespace/lifecycle, closer to a
# Kubernetes Pod than to a standalone `docker run`). No cluster, no nodes
# to manage -- this is Azure's "just run a container" service, the
# lightweight alternative to AKS for a single workload.
resource "azurerm_container_group" "demo" {
  name                = "aci-demo"
  resource_group_name = azurerm_resource_group.aci.name
  location            = azurerm_resource_group.aci.location
  os_type             = "Linux"
  ip_address_type     = "Public"
  dns_name_label      = "aci-demo-${random_string.suffix.result}"

  container {
    name   = "nginx"
    image  = "mcr.microsoft.com/azuredocs/aci-helloworld:latest"
    cpu    = "0.5"
    memory = "0.5"

    ports {
      port     = 80
      protocol = "TCP"
    }
  }
}

output "fqdn" {
  value = azurerm_container_group.demo.fqdn
}

output "ip_address" {
  value = azurerm_container_group.demo.ip_address
}
